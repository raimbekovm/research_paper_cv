"""
PM2.5 and weather data collection module for AirVision system.

This module provides functionality for fetching air quality (PM2.5) and
meteorological data from multiple API sources for Bishkek, Kyrgyzstan.

Supported APIs:
    - IQAir (requires API key)
    - OpenWeatherMap (requires API key)
    - OpenAQ (no API key required)

Example:
    >>> from src.fetch_pm25_data import PM25Collector, get_current_pm25
    >>> collector = PM25Collector()
    >>> data = collector.fetch_all()
    >>> print(f"PM2.5: {data.pm25} µg/m³")
"""

import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import requests
from dotenv import load_dotenv

from src.utils.io import ensure_dir, save_json
from src.utils.logging import get_logger

# Load environment variables
load_dotenv()

logger = get_logger(__name__)


# =============================================================================
# Exceptions
# =============================================================================


class APIError(Exception):
    """Base exception for API-related errors."""

    pass


class APIConnectionError(APIError):
    """Failed to connect to API endpoint."""

    pass


class APIRateLimitError(APIError):
    """API rate limit exceeded."""

    pass


class APIAuthenticationError(APIError):
    """API authentication failed (invalid or missing key)."""

    pass


# =============================================================================
# Data Classes
# =============================================================================


class DataSource(Enum):
    """Available data sources."""

    IQAIR = "iqair"
    OPENWEATHERMAP = "openweathermap"
    OPENAQ = "openaq"


@dataclass
class Location:
    """Geographic location."""

    latitude: float
    longitude: float
    name: str = "Bishkek"

    @classmethod
    def bishkek(cls) -> "Location":
        """Return Bishkek city center coordinates."""
        return cls(latitude=42.8746, longitude=74.5698, name="Bishkek")


@dataclass
class WeatherData:
    """
    Meteorological data for PM2.5 estimation.

    Includes all factors that influence atmospheric visibility and pollution:
    - Basic weather: temperature, humidity, pressure, wind
    - Visibility factors: clouds, visibility distance
    - Atmospheric conditions: boundary layer height, inversions
    - Solar factors: radiation, UV index
    - Precipitation: rain, snow
    """

    # Basic weather
    temperature: Optional[float] = None  # Celsius
    feels_like: Optional[float] = None  # Celsius (apparent temperature)
    humidity: Optional[float] = None  # Percent
    pressure: Optional[float] = None  # hPa (sea level)
    surface_pressure: Optional[float] = None  # hPa (at surface)

    # Wind
    wind_speed: Optional[float] = None  # m/s
    wind_direction: Optional[float] = None  # Degrees
    wind_gusts: Optional[float] = None  # m/s

    # Visibility and clouds
    visibility: Optional[int] = None  # Meters
    clouds: Optional[int] = None  # Percent

    # Atmospheric conditions (critical for smog!)
    boundary_layer_height: Optional[float] = None  # Meters - key for inversions
    dew_point: Optional[float] = None  # Celsius

    # Solar radiation
    shortwave_radiation: Optional[float] = None  # W/m²
    uv_index: Optional[float] = None

    # Precipitation
    precipitation: Optional[float] = None  # mm
    snowfall: Optional[float] = None  # cm
    rain: Optional[float] = None  # mm

    # Weather condition
    weather_code: Optional[int] = None  # WMO weather code
    weather_description: Optional[str] = None

    # Time factors
    is_day: Optional[bool] = None
    sunrise: Optional[str] = None  # ISO time
    sunset: Optional[str] = None  # ISO time

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            # Basic
            "temperature": self.temperature,
            "feels_like": self.feels_like,
            "humidity": self.humidity,
            "pressure": self.pressure,
            "surface_pressure": self.surface_pressure,
            # Wind
            "wind_speed": self.wind_speed,
            "wind_direction": self.wind_direction,
            "wind_gusts": self.wind_gusts,
            # Visibility
            "visibility": self.visibility,
            "clouds": self.clouds,
            # Atmospheric
            "boundary_layer_height": self.boundary_layer_height,
            "dew_point": self.dew_point,
            # Solar
            "shortwave_radiation": self.shortwave_radiation,
            "uv_index": self.uv_index,
            # Precipitation
            "precipitation": self.precipitation,
            "snowfall": self.snowfall,
            "rain": self.rain,
            # Condition
            "weather_code": self.weather_code,
            "weather_description": self.weather_description,
            # Time
            "is_day": self.is_day,
            "sunrise": self.sunrise,
            "sunset": self.sunset,
        }


@dataclass
class PM25Reading:
    """Single PM2.5 measurement."""

    value: float  # µg/m³
    aqi: Optional[int] = None  # US AQI (if available)
    source: Optional[DataSource] = None
    location: Optional[str] = None
    timestamp: Optional[datetime] = None
    weather: Optional[WeatherData] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "pm25": self.value,
            "aqi": self.aqi,
            "source": self.source.value if self.source else None,
            "location": self.location,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "weather": self.weather.to_dict() if self.weather else None,
        }


@dataclass
class CollectionResult:
    """Result of data collection from all sources."""

    readings: List[PM25Reading] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    errors: Dict[str, str] = field(default_factory=dict)
    multi_station: Optional["MultiStationData"] = None  # Forward reference

    @property
    def successful_sources(self) -> int:
        """Number of successful data sources."""
        return len(set(r.source for r in self.readings if r.source))

    @property
    def station_count(self) -> int:
        """Number of stations if multi-station data available."""
        return self.multi_station.count if self.multi_station else 1

    @property
    def best_reading(self) -> Optional[PM25Reading]:
        """Return highest priority reading (IQAir > OpenWeatherMap > OpenAQ)."""
        priority = [DataSource.IQAIR, DataSource.OPENWEATHERMAP, DataSource.OPENAQ]
        for source in priority:
            for reading in self.readings:
                if reading.source == source:
                    return reading
        return self.readings[0] if self.readings else None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        result = {
            "timestamp": self.timestamp.isoformat(),
            "readings": [r.to_dict() for r in self.readings],
            "errors": self.errors,
            "successful_sources": self.successful_sources,
        }
        if self.multi_station:
            result["multi_station"] = self.multi_station.to_dict()
        return result


# =============================================================================
# AQI Conversion
# =============================================================================


def aqi_to_pm25(aqi: int) -> float:
    """
    Convert US AQI to PM2.5 concentration (µg/m³).

    Uses EPA (Environmental Protection Agency) breakpoints.

    Args:
        aqi: US Air Quality Index value

    Returns:
        PM2.5 concentration in µg/m³

    Example:
        >>> aqi_to_pm25(50)
        12.0
        >>> aqi_to_pm25(150)
        54.9
    """
    if aqi <= 50:
        return aqi * 12.0 / 50
    elif aqi <= 100:
        return 12.1 + (aqi - 51) * 23.9 / 49
    elif aqi <= 150:
        return 35.5 + (aqi - 101) * 19.4 / 49
    elif aqi <= 200:
        return 55.5 + (aqi - 151) * 94.4 / 49
    elif aqi <= 300:
        return 150.5 + (aqi - 201) * 99.4 / 99
    else:
        return 250.5 + (aqi - 301) * 99.9 / 99


def pm25_to_aqi(pm25: float) -> int:
    """
    Convert PM2.5 concentration to US AQI.

    Args:
        pm25: PM2.5 concentration in µg/m³

    Returns:
        US Air Quality Index value
    """
    if pm25 <= 12.0:
        return int(pm25 * 50 / 12.0)
    elif pm25 <= 35.4:
        return int(51 + (pm25 - 12.1) * 49 / 23.3)
    elif pm25 <= 55.4:
        return int(101 + (pm25 - 35.5) * 49 / 19.9)
    elif pm25 <= 150.4:
        return int(151 + (pm25 - 55.5) * 49 / 94.9)
    elif pm25 <= 250.4:
        return int(201 + (pm25 - 150.5) * 99 / 99.9)
    else:
        return int(301 + (pm25 - 250.5) * 99 / 99.9)


# =============================================================================
# API Clients
# =============================================================================


class BaseAPIClient(ABC):
    """Abstract base class for API clients."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: int = 10,
        max_retries: int = 3,
    ):
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.location = Location.bishkek()

    @property
    @abstractmethod
    def source(self) -> DataSource:
        """Return the data source identifier."""
        pass

    @property
    @abstractmethod
    def requires_key(self) -> bool:
        """Whether this API requires an API key."""
        pass

    def _make_request(
        self,
        url: str,
        params: Optional[Dict] = None,
    ) -> dict:
        """
        Make HTTP request with retry logic.

        Args:
            url: API endpoint URL
            params: Query parameters

        Returns:
            JSON response as dictionary

        Raises:
            APIConnectionError: If connection fails
            APIRateLimitError: If rate limit exceeded
            APIAuthenticationError: If authentication fails
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                response = requests.get(url, params=params, timeout=self.timeout)

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 401:
                    raise APIAuthenticationError("Invalid API key")
                elif response.status_code == 429:
                    raise APIRateLimitError("Rate limit exceeded")
                else:
                    last_error = APIError(f"HTTP {response.status_code}: {response.text}")

            except requests.RequestException as e:
                last_error = APIConnectionError(f"Connection failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(1)  # Brief delay before retry

        raise last_error

    @abstractmethod
    def fetch(self) -> Optional[PM25Reading]:
        """
        Fetch current PM2.5 data.

        Returns:
            PM25Reading or None if fetch fails
        """
        pass


class IQAirClient(BaseAPIClient):
    """
    IQAir API client for air quality data.

    Get free API key at: https://www.iqair.com/air-pollution-data-api
    """

    BASE_URL = "http://api.airvisual.com/v2/nearest_city"

    @property
    def source(self) -> DataSource:
        return DataSource.IQAIR

    @property
    def requires_key(self) -> bool:
        return True

    def fetch(self) -> Optional[PM25Reading]:
        """Fetch current PM2.5 from IQAir."""
        if not self.api_key:
            logger.warning("IQAir API key not provided")
            return None

        params = {
            "lat": self.location.latitude,
            "lon": self.location.longitude,
            "key": self.api_key,
        }

        try:
            data = self._make_request(self.BASE_URL, params)

            if data.get("status") != "success":
                logger.warning(f"IQAir returned error: {data}")
                return None

            current = data["data"]["current"]
            pollution = current["pollution"]
            weather_data = current["weather"]

            aqi = pollution.get("aqius")
            pm25_conc = pollution.get("p2", {}).get("conc")

            # Convert AQI to concentration if needed
            if pm25_conc is None and aqi is not None:
                pm25_conc = aqi_to_pm25(aqi)

            weather = WeatherData(
                temperature=weather_data.get("tp"),
                humidity=weather_data.get("hu"),
                pressure=weather_data.get("pr"),
                wind_speed=weather_data.get("ws"),
            )

            timestamp_str = pollution.get("ts")
            timestamp = None
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                except ValueError:
                    timestamp = datetime.now()

            logger.info(f"IQAir: PM2.5={pm25_conc:.1f} µg/m³, AQI={aqi}")

            return PM25Reading(
                value=pm25_conc,
                aqi=aqi,
                source=self.source,
                location="Bishkek",
                timestamp=timestamp,
                weather=weather,
            )

        except APIAuthenticationError:
            logger.error("IQAir authentication failed - check API key")
            return None
        except APIError as e:
            logger.error(f"IQAir API error: {e}")
            return None


class OpenWeatherMapClient(BaseAPIClient):
    """
    OpenWeatherMap API client for air quality and weather data.

    Get free API key at: https://openweathermap.org/api
    """

    POLLUTION_URL = "http://api.openweathermap.org/data/2.5/air_pollution"
    WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"

    @property
    def source(self) -> DataSource:
        return DataSource.OPENWEATHERMAP

    @property
    def requires_key(self) -> bool:
        return True

    def fetch(self) -> Optional[PM25Reading]:
        """Fetch current PM2.5 and weather from OpenWeatherMap."""
        if not self.api_key:
            logger.warning("OpenWeatherMap API key not provided")
            return None

        params = {
            "lat": self.location.latitude,
            "lon": self.location.longitude,
            "appid": self.api_key,
        }

        try:
            pollution_data = self._make_request(self.POLLUTION_URL, params)
            weather_data = self._make_request(self.WEATHER_URL, params)

            components = pollution_data["list"][0]["components"]
            main = weather_data["main"]
            wind = weather_data["wind"]

            pm25 = components.get("pm2_5")

            weather = WeatherData(
                temperature=main.get("temp") - 273.15 if main.get("temp") else None,
                humidity=main.get("humidity"),
                pressure=main.get("pressure"),
                wind_speed=wind.get("speed"),
                wind_direction=wind.get("deg"),
                visibility=weather_data.get("visibility"),
                clouds=weather_data.get("clouds", {}).get("all"),
            )

            timestamp = datetime.fromtimestamp(pollution_data["list"][0]["dt"])

            logger.info(f"OpenWeatherMap: PM2.5={pm25} µg/m³, T={weather.temperature:.1f}°C")

            return PM25Reading(
                value=pm25,
                aqi=pm25_to_aqi(pm25) if pm25 else None,
                source=self.source,
                location="Bishkek",
                timestamp=timestamp,
                weather=weather,
            )

        except APIAuthenticationError:
            logger.error("OpenWeatherMap authentication failed - check API key")
            return None
        except APIError as e:
            logger.error(f"OpenWeatherMap API error: {e}")
            return None
        except (KeyError, TypeError) as e:
            logger.error(f"OpenWeatherMap parsing error: {e}")
            return None


# NOTE: OpenAQ sensors in Bishkek are offline (no data since March 2025).
# Using IQAir web scraper instead for multi-station PM2.5 data.

from src.scrape_iqair import IQAirScraper, MultiStationData


class OpenMeteoClient:
    """
    Open-Meteo API client for detailed weather data.

    Free API, no key required: https://open-meteo.com/

    Provides critical atmospheric data for PM2.5 analysis:
    - Boundary layer height (key for thermal inversions)
    - Solar radiation
    - Detailed precipitation data
    - UV index
    """

    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.location = Location.bishkek()

    def fetch(self) -> Optional[WeatherData]:
        """
        Fetch detailed weather data from Open-Meteo.

        Returns:
            WeatherData with atmospheric conditions or None on failure
        """
        params = {
            "latitude": self.location.latitude,
            "longitude": self.location.longitude,
            "current": ",".join([
                "temperature_2m",
                "relative_humidity_2m",
                "apparent_temperature",
                "is_day",
                "precipitation",
                "rain",
                "snowfall",
                "weather_code",
                "cloud_cover",
                "pressure_msl",
                "surface_pressure",
                "wind_speed_10m",
                "wind_direction_10m",
                "wind_gusts_10m",
            ]),
            "hourly": ",".join([
                "boundary_layer_height",
                "shortwave_radiation",
                "uv_index",
                "dew_point_2m",
            ]),
            "daily": "sunrise,sunset",
            "timezone": "Asia/Bishkek",
            "forecast_days": 1,
        }

        try:
            response = requests.get(self.BASE_URL, params=params, timeout=self.timeout)

            if response.status_code != 200:
                logger.warning(f"Open-Meteo API error: {response.status_code}")
                return None

            data = response.json()
            current = data.get("current", {})
            hourly = data.get("hourly", {})
            daily = data.get("daily", {})

            # Get current hour index for hourly data
            current_hour = datetime.now().hour

            # Extract boundary layer height (critical for inversions!)
            blh_list = hourly.get("boundary_layer_height", [])
            boundary_layer = blh_list[current_hour] if current_hour < len(blh_list) else None

            # Solar radiation
            radiation_list = hourly.get("shortwave_radiation", [])
            radiation = radiation_list[current_hour] if current_hour < len(radiation_list) else None

            # UV index
            uv_list = hourly.get("uv_index", [])
            uv_index = uv_list[current_hour] if current_hour < len(uv_list) else None

            # Dew point
            dew_list = hourly.get("dew_point_2m", [])
            dew_point = dew_list[current_hour] if current_hour < len(dew_list) else None

            # Sunrise/sunset
            sunrise = daily.get("sunrise", [None])[0]
            sunset = daily.get("sunset", [None])[0]

            weather = WeatherData(
                temperature=current.get("temperature_2m"),
                feels_like=current.get("apparent_temperature"),
                humidity=current.get("relative_humidity_2m"),
                pressure=current.get("pressure_msl"),
                surface_pressure=current.get("surface_pressure"),
                wind_speed=current.get("wind_speed_10m"),
                wind_direction=current.get("wind_direction_10m"),
                wind_gusts=current.get("wind_gusts_10m"),
                clouds=current.get("cloud_cover"),
                precipitation=current.get("precipitation"),
                rain=current.get("rain"),
                snowfall=current.get("snowfall"),
                weather_code=current.get("weather_code"),
                is_day=current.get("is_day") == 1,
                boundary_layer_height=boundary_layer,
                shortwave_radiation=radiation,
                uv_index=uv_index,
                dew_point=dew_point,
                sunrise=sunrise,
                sunset=sunset,
            )

            logger.info(
                f"Open-Meteo: T={weather.temperature}°C, BLH={boundary_layer}m, "
                f"clouds={weather.clouds}%"
            )

            return weather

        except requests.RequestException as e:
            logger.error(f"Open-Meteo connection error: {e}")
            return None
        except (KeyError, TypeError, IndexError) as e:
            logger.error(f"Open-Meteo parsing error: {e}")
            return None


# =============================================================================
# Main Collector
# =============================================================================


class PM25Collector:
    """
    Multi-source PM2.5 data collector.

    Aggregates data from multiple APIs and web scraping to provide reliable
    air quality measurements for Bishkek, Kyrgyzstan.

    Data sources:
        - IQAir web scraper: 7 stations across Bishkek (primary)
        - IQAir API: backup single-station data
        - Open-Meteo: detailed weather data
        - OpenWeatherMap: visibility data

    Args:
        output_dir: Directory for saving collected data
        iqair_key: IQAir API key (optional, for backup)
        openweather_key: OpenWeatherMap API key (optional)
        use_scraper: Use multi-station web scraper (default: True)

    Example:
        >>> collector = PM25Collector()
        >>> result = collector.fetch_all()
        >>> if result.best_reading:
        ...     print(f"PM2.5: {result.best_reading.value} µg/m³")
    """

    def __init__(
        self,
        output_dir: Union[str, Path] = "data/pm25",
        iqair_key: Optional[str] = None,
        openweather_key: Optional[str] = None,
        use_scraper: bool = True,
    ):
        self.output_dir = Path(output_dir)
        ensure_dir(self.output_dir)

        self.use_scraper = use_scraper

        # Initialize IQAir web scraper for multi-station data (primary)
        self.iqair_scraper = IQAirScraper() if use_scraper else None

        # Initialize IQAir API client as backup
        self.clients = [
            IQAirClient(api_key=iqair_key or os.getenv("IQAIR_API_KEY")),
        ]

        # Initialize Open-Meteo for detailed weather (no API key needed)
        self.meteo_client = OpenMeteoClient()

        # OpenWeatherMap for visibility only (not PM2.5 - their model is inaccurate)
        self.openweather_key = openweather_key or os.getenv("OPENWEATHER_API_KEY")

        source_info = "IQAir scraper (7 stations)" if use_scraper else "IQAir API"
        logger.info(f"Initialized PM25Collector: {source_info} + Open-Meteo (weather)")

    def fetch_all(self, save: bool = True) -> CollectionResult:
        """
        Fetch PM2.5 data from all available sources and detailed weather from Open-Meteo.

        Primary source is IQAir web scraper (7 stations), with API as backup.

        Args:
            save: Whether to save results to JSON files

        Returns:
            CollectionResult with all readings and any errors
        """
        result = CollectionResult()

        # Fetch detailed weather from Open-Meteo
        meteo_weather = self.meteo_client.fetch()

        # Fetch visibility from OpenWeatherMap (they have accurate visibility data)
        visibility = self._fetch_visibility()
        if meteo_weather and visibility:
            meteo_weather.visibility = visibility

        # Primary: Try IQAir web scraper for multi-station data
        multi_station_data = None
        if self.use_scraper and self.iqair_scraper:
            try:
                multi_station_data = self.iqair_scraper.fetch_all_stations()

                if multi_station_data and multi_station_data.count > 0:
                    # Create aggregate reading from all stations
                    reading = PM25Reading(
                        value=multi_station_data.pm25_mean,
                        aqi=int(multi_station_data.aqi_mean),
                        source=DataSource.IQAIR,
                        location="Bishkek (7 stations)",
                        timestamp=multi_station_data.timestamp,
                        weather=meteo_weather,
                    )
                    result.readings.append(reading)

                    # Store detailed station data
                    result.multi_station = multi_station_data

                    logger.info(
                        f"IQAir scraper: {multi_station_data.count} stations, "
                        f"PM2.5 mean={multi_station_data.pm25_mean:.1f}, "
                        f"range=[{multi_station_data.pm25_min:.0f}-{multi_station_data.pm25_max:.0f}]"
                    )
                else:
                    result.errors["iqair_scraper"] = "No stations returned data"

            except Exception as e:
                logger.error(f"IQAir scraper error: {e}")
                result.errors["iqair_scraper"] = str(e)

        # Fallback: Use IQAir API if scraper failed or disabled
        if not result.readings:
            for client in self.clients:
                source_name = client.source.value

                if client.requires_key and not client.api_key:
                    result.errors[source_name] = "API key not configured"
                    continue

                try:
                    reading = client.fetch()
                    if reading:
                        # Use Open-Meteo weather (more complete)
                        if meteo_weather:
                            reading.weather = meteo_weather
                        result.readings.append(reading)
                    else:
                        result.errors[source_name] = "No data returned"

                except Exception as e:
                    logger.exception(f"Error fetching from {source_name}")
                    result.errors[source_name] = str(e)

        # Save results
        if save and result.readings:
            self._save_results(result)

        logger.info(
            f"Collection complete: {len(result.readings)} sources successful, "
            f"{len(result.errors)} errors"
        )

        return result

    def _merge_weather(self, base: Optional[WeatherData], meteo: WeatherData) -> WeatherData:
        """
        Merge weather data from multiple sources.

        Open-Meteo provides more detailed atmospheric data (boundary layer, radiation, etc.)
        while other sources may have visibility data.
        """
        if base is None:
            return meteo

        # Start with Open-Meteo data (most complete)
        merged = WeatherData(
            # Use Open-Meteo for most fields
            temperature=meteo.temperature,
            feels_like=meteo.feels_like,
            humidity=meteo.humidity,
            pressure=meteo.pressure,
            surface_pressure=meteo.surface_pressure,
            wind_speed=meteo.wind_speed,
            wind_direction=meteo.wind_direction,
            wind_gusts=meteo.wind_gusts,
            clouds=meteo.clouds,
            precipitation=meteo.precipitation,
            rain=meteo.rain,
            snowfall=meteo.snowfall,
            weather_code=meteo.weather_code,
            is_day=meteo.is_day,
            sunrise=meteo.sunrise,
            sunset=meteo.sunset,
            # Open-Meteo exclusive
            boundary_layer_height=meteo.boundary_layer_height,
            shortwave_radiation=meteo.shortwave_radiation,
            uv_index=meteo.uv_index,
            dew_point=meteo.dew_point,
            # Use base for visibility (OpenWeatherMap has this)
            visibility=base.visibility,
            # Use base weather description if available
            weather_description=base.weather_description,
        )

        return merged

    def _fetch_visibility(self) -> Optional[int]:
        """Fetch visibility from OpenWeatherMap (meters)."""
        if not self.openweather_key:
            return None

        try:
            url = "https://api.openweathermap.org/data/2.5/weather"
            params = {
                "lat": 42.8746,
                "lon": 74.5698,
                "appid": self.openweather_key,
            }
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                visibility = data.get("visibility")
                if visibility:
                    logger.debug(f"OpenWeatherMap visibility: {visibility}m")
                return visibility
        except Exception as e:
            logger.warning(f"Failed to fetch visibility: {e}")
        return None

    def _save_results(self, result: CollectionResult) -> None:
        """Save collection results to JSON file."""
        timestamp_str = result.timestamp.strftime("%Y%m%d_%H%M%S")
        filepath = self.output_dir / f"pm25_{timestamp_str}.json"
        save_json(result.to_dict(), filepath)
        logger.debug(f"Saved results to {filepath}")


# =============================================================================
# Convenience Functions
# =============================================================================


def get_current_pm25(
    iqair_key: Optional[str] = None,
    openweather_key: Optional[str] = None,
) -> Optional[float]:
    """
    Get current PM2.5 value from best available source.

    Args:
        iqair_key: Optional IQAir API key
        openweather_key: Optional OpenWeatherMap API key

    Returns:
        PM2.5 concentration in µg/m³ or None if unavailable

    Example:
        >>> pm25 = get_current_pm25()
        >>> if pm25:
        ...     print(f"Current PM2.5: {pm25:.1f} µg/m³")
    """
    collector = PM25Collector(
        iqair_key=iqair_key,
        openweather_key=openweather_key,
    )
    result = collector.fetch_all(save=False)

    if result.best_reading:
        return result.best_reading.value
    return None


def get_current_weather() -> Optional[WeatherData]:
    """
    Get current weather data from best available source.

    Returns:
        WeatherData object or None if unavailable
    """
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        logger.warning("OpenWeatherMap API key not configured")
        return None

    client = OpenWeatherMapClient(api_key=api_key)
    reading = client.fetch()

    return reading.weather if reading else None


# =============================================================================
# Main Entry Point
# =============================================================================


def main():
    """Main entry point for PM2.5 data collection."""
    print("=" * 80)
    print("AirVision PM2.5 Data Collection")
    print("=" * 80)

    # Check API keys
    iqair_key = os.getenv("IQAIR_API_KEY")
    openweather_key = os.getenv("OPENWEATHER_API_KEY")

    if not iqair_key or iqair_key.startswith("your_"):
        print("\nWarning: IQAir API key not configured")
        print("  Get free key: https://www.iqair.com/air-pollution-data-api")
        iqair_key = None

    if not openweather_key or openweather_key.startswith("your_"):
        print("\nWarning: OpenWeatherMap API key not configured")
        print("  Get free key: https://openweathermap.org/api")
        openweather_key = None

    # Collect data
    collector = PM25Collector(
        iqair_key=iqair_key,
        openweather_key=openweather_key,
    )

    print("\nFetching data from all sources...")
    result = collector.fetch_all()

    # Print results
    print("\n" + "-" * 80)
    print("RESULTS")
    print("-" * 80)

    for reading in result.readings:
        print(f"\n[{reading.source.value.upper()}]")
        print(f"  PM2.5: {reading.value:.1f} µg/m³")
        if reading.aqi:
            print(f"  AQI: {reading.aqi}")
        if reading.weather:
            w = reading.weather
            if w.temperature:
                print(f"  Temperature: {w.temperature:.1f}°C")
            if w.humidity:
                print(f"  Humidity: {w.humidity}%")
            if w.visibility:
                print(f"  Visibility: {w.visibility}m")

    if result.errors:
        print("\n" + "-" * 80)
        print("ERRORS")
        print("-" * 80)
        for source, error in result.errors.items():
            print(f"  {source}: {error}")

    print("\n" + "=" * 80)
    print(f"Collected {len(result.readings)} readings from {result.successful_sources} sources")
    print("=" * 80)


if __name__ == "__main__":
    main()
