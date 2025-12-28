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
    """Meteorological data."""

    temperature: Optional[float] = None  # Celsius
    humidity: Optional[float] = None  # Percent
    pressure: Optional[float] = None  # hPa
    wind_speed: Optional[float] = None  # m/s
    wind_direction: Optional[float] = None  # Degrees
    visibility: Optional[int] = None  # Meters
    clouds: Optional[int] = None  # Percent

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "temperature": self.temperature,
            "humidity": self.humidity,
            "pressure": self.pressure,
            "wind_speed": self.wind_speed,
            "wind_direction": self.wind_direction,
            "visibility": self.visibility,
            "clouds": self.clouds,
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

    @property
    def successful_sources(self) -> int:
        """Number of successful data sources."""
        return len(set(r.source for r in self.readings if r.source))

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
        return {
            "timestamp": self.timestamp.isoformat(),
            "readings": [r.to_dict() for r in self.readings],
            "errors": self.errors,
            "successful_sources": self.successful_sources,
        }


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


class OpenAQClient(BaseAPIClient):
    """
    OpenAQ API client for air quality data.

    No API key required: https://docs.openaq.org/
    """

    BASE_URL = "https://api.openaq.org/v2/latest"

    @property
    def source(self) -> DataSource:
        return DataSource.OPENAQ

    @property
    def requires_key(self) -> bool:
        return False

    def fetch(self) -> Optional[PM25Reading]:
        """Fetch current PM2.5 from OpenAQ."""
        params = {
            "city": "Bishkek",
            "parameter": "pm25",
            "limit": 100,
        }

        try:
            data = self._make_request(self.BASE_URL, params)
            results = data.get("results", [])

            if not results:
                logger.warning("No OpenAQ data available for Bishkek")
                return None

            # Find most recent reading
            latest_reading = None
            latest_time = None

            for station in results:
                for measurement in station.get("measurements", []):
                    if measurement.get("parameter") == "pm25":
                        try:
                            time_str = measurement.get("lastUpdated")
                            if time_str:
                                meas_time = datetime.fromisoformat(
                                    time_str.replace("Z", "+00:00")
                                )
                                if latest_time is None or meas_time > latest_time:
                                    latest_time = meas_time
                                    latest_reading = {
                                        "value": measurement.get("value"),
                                        "location": station.get("location", "Unknown"),
                                        "timestamp": meas_time,
                                    }
                        except (ValueError, TypeError):
                            continue

            if latest_reading:
                pm25 = latest_reading["value"]
                logger.info(
                    f"OpenAQ: PM2.5={pm25} µg/m³ from {latest_reading['location']}"
                )

                return PM25Reading(
                    value=pm25,
                    aqi=pm25_to_aqi(pm25) if pm25 else None,
                    source=self.source,
                    location=latest_reading["location"],
                    timestamp=latest_reading["timestamp"],
                )

            return None

        except APIError as e:
            logger.error(f"OpenAQ API error: {e}")
            return None


# =============================================================================
# Main Collector
# =============================================================================


class PM25Collector:
    """
    Multi-source PM2.5 data collector.

    Aggregates data from multiple APIs to provide reliable air quality
    measurements for Bishkek, Kyrgyzstan.

    Args:
        output_dir: Directory for saving collected data
        iqair_key: IQAir API key (optional)
        openweather_key: OpenWeatherMap API key (optional)

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
    ):
        self.output_dir = Path(output_dir)
        ensure_dir(self.output_dir)

        # Initialize API clients
        self.clients = [
            IQAirClient(api_key=iqair_key or os.getenv("IQAIR_API_KEY")),
            OpenWeatherMapClient(
                api_key=openweather_key or os.getenv("OPENWEATHER_API_KEY")
            ),
            OpenAQClient(),
        ]

        logger.info(f"Initialized PM25Collector with {len(self.clients)} sources")

    def fetch_all(self, save: bool = True) -> CollectionResult:
        """
        Fetch PM2.5 data from all available sources.

        Args:
            save: Whether to save results to JSON files

        Returns:
            CollectionResult with all readings and any errors
        """
        result = CollectionResult()

        for client in self.clients:
            source_name = client.source.value

            if client.requires_key and not client.api_key:
                result.errors[source_name] = "API key not configured"
                continue

            try:
                reading = client.fetch()
                if reading:
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
