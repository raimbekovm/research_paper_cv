"""
IQAir web scraper for multiple PM2.5 stations in Bishkek.

Scrapes real-time air quality data from IQAir website for 7 stations
across different districts of Bishkek city.
"""

import re
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup

from src.utils.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class StationReading:
    """Single station air quality reading."""

    station_id: str
    station_name: str
    pm25: float  # µg/m³
    aqi: int  # US AQI
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    district: Optional[str] = None
    temperature: Optional[float] = None  # Celsius
    humidity: Optional[float] = None  # Percent
    wind_speed: Optional[float] = None  # km/h
    wind_direction: Optional[int] = None  # Degrees
    timestamp: datetime = field(default_factory=datetime.now)
    url: str = ""

    def to_dict(self) -> dict:
        return {
            "station_id": self.station_id,
            "station_name": self.station_name,
            "pm25": self.pm25,
            "aqi": self.aqi,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "district": self.district,
            "temperature": self.temperature,
            "humidity": self.humidity,
            "wind_speed": self.wind_speed,
            "wind_direction": self.wind_direction,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class MultiStationData:
    """Aggregated data from multiple stations."""

    readings: List[StationReading]
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def count(self) -> int:
        return len(self.readings)

    @property
    def pm25_mean(self) -> float:
        values = [r.pm25 for r in self.readings]
        return statistics.mean(values) if values else 0.0

    @property
    def pm25_median(self) -> float:
        values = [r.pm25 for r in self.readings]
        return statistics.median(values) if values else 0.0

    @property
    def pm25_min(self) -> float:
        values = [r.pm25 for r in self.readings]
        return min(values) if values else 0.0

    @property
    def pm25_max(self) -> float:
        values = [r.pm25 for r in self.readings]
        return max(values) if values else 0.0

    @property
    def pm25_std(self) -> float:
        values = [r.pm25 for r in self.readings]
        return statistics.stdev(values) if len(values) > 1 else 0.0

    @property
    def aqi_mean(self) -> float:
        values = [r.aqi for r in self.readings]
        return statistics.mean(values) if values else 0.0

    # Weather aggregates from all stations
    @property
    def temperature_mean(self) -> Optional[float]:
        values = [r.temperature for r in self.readings if r.temperature is not None]
        return statistics.mean(values) if values else None

    @property
    def humidity_mean(self) -> Optional[float]:
        values = [r.humidity for r in self.readings if r.humidity is not None]
        return statistics.mean(values) if values else None

    @property
    def wind_speed_mean(self) -> Optional[float]:
        values = [r.wind_speed for r in self.readings if r.wind_speed is not None]
        return statistics.mean(values) if values else None

    def to_dict(self) -> dict:
        result = {
            "timestamp": self.timestamp.isoformat(),
            "count": self.count,
            "pm25": {
                "mean": round(self.pm25_mean, 1),
                "median": round(self.pm25_median, 1),
                "min": round(self.pm25_min, 1),
                "max": round(self.pm25_max, 1),
                "std": round(self.pm25_std, 1),
            },
            "aqi_mean": round(self.aqi_mean, 0),
            "weather": {
                "temperature_mean": round(self.temperature_mean, 1) if self.temperature_mean else None,
                "humidity_mean": round(self.humidity_mean, 1) if self.humidity_mean else None,
                "wind_speed_mean": round(self.wind_speed_mean, 1) if self.wind_speed_mean else None,
            },
            "stations": [r.to_dict() for r in self.readings],
        }
        return result


# =============================================================================
# IQAir Scraper
# =============================================================================


class IQAirScraper:
    """
    Scraper for IQAir website to collect PM2.5 data from multiple stations.

    Stations in Bishkek:
        - kok-jar-station: Northern district (Кок-Жар)
        - erkendik-moskovskaya: Central (Эркиндик/Московская)
        - un-house-kyrgyzstan: Central (ООН)
        - swiss-embassy: Central (Швейцарское посольство)
        - home: Western district
        - krasnyi-stroitel: Southern district (Красный Строитель)
        - madiyeva: Eastern district (Мадиева)
    """

    BASE_URL = "https://www.iqair.com/ru/kyrgyzstan/bishkek/bishkek"

    # Station configurations: id -> (name, district, lat, lon)
    STATIONS = {
        "kok-jar-station": ("Kok-Jar Station", "Север", 42.8343, 74.6404),
        "erkendik-moskovskaya": ("Erkendik/Moskovskaya", "Центр", 42.8708, 74.6055),
        "un-house-kyrgyzstan": ("UN House", "Центр", 42.8762, 74.5899),
        "swiss-embassy": ("Swiss Embassy", "Центр", 42.8692, 74.6070),
        "home": ("Home", "Запад", 42.8274, 74.5626),
        "krasnyi-stroitel": ("Krasnyi Stroitel", "Юг", 42.9454, 74.5952),
        "madiyeva": ("Madiyeva", "Восток", 42.8198, 74.6458),
    }

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
    }

    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def _parse_station_page(self, html: str, station_id: str) -> Optional[StationReading]:
        """Parse station page HTML and extract air quality data."""
        soup = BeautifulSoup(html, "html.parser")

        try:
            pm25_value = None
            aqi_value = None
            temperature = None
            humidity = None
            wind_speed = None
            wind_direction = None

            # Find the main AQI card (has aqi-box-shadow-* class)
            aqi_card = soup.find("div", class_=lambda c: c and "aqi-box-shadow-" in c)

            if aqi_card:
                # AQI value: <p class="text-lg font-medium">184</p> inside aqi-legend-bg-* div
                aqi_legend = aqi_card.find("div", class_=lambda c: c and "aqi-legend-bg-" in c)
                if aqi_legend:
                    aqi_p = aqi_legend.find("p", class_="text-lg")
                    if aqi_p:
                        aqi_text = aqi_p.get_text(strip=True)
                        if aqi_text.isdigit():
                            aqi_value = int(aqi_text)

                # PM2.5 value: look for "µg/m³" pattern
                # <p>103<!-- -->&nbsp;µg/m³</p>
                pm25_pattern = soup.find(string=re.compile(r"µg/m³|μg/m³"))
                if pm25_pattern:
                    parent = pm25_pattern.find_parent("p")
                    if parent:
                        text = parent.get_text(strip=True)
                        match = re.search(r"([\d.]+)\s*[µμ]g/m³", text)
                        if match:
                            pm25_value = float(match.group(1))

                # Weather bar at bottom: <div class="...bg-white...">
                weather_bar = aqi_card.find("div", class_=lambda c: c and "bg-white" in c)
                if weather_bar:
                    # All values in <p> tags
                    p_tags = weather_bar.find_all("p")

                    for p in p_tags:
                        text = p.get_text(strip=True)

                        # Temperature: ends with °
                        if text.endswith("°") or "°" in text:
                            temp_match = re.search(r"(-?\d+)", text)
                            if temp_match:
                                temperature = float(temp_match.group(1))

                        # Wind speed: contains km/h
                        elif "km/h" in text:
                            speed_match = re.search(r"([\d.]+)", text)
                            if speed_match:
                                wind_speed = float(speed_match.group(1))

                        # Humidity: ends with %
                        elif text.endswith("%") or "%" in text:
                            humid_match = re.search(r"(\d+)", text)
                            if humid_match:
                                humidity = float(humid_match.group(1))

                    # Wind direction from icon rotation
                    wind_img = weather_bar.find("img", alt=lambda a: a and "wind" in a.lower())
                    if wind_img:
                        style = wind_img.get("style", "")
                        dir_match = re.search(r"rotate[:\s]*(\d+)", style)
                        if dir_match:
                            wind_direction = int(dir_match.group(1))

            # Fallback: find PM2.5 from WHO comparison if not found
            if pm25_value is None:
                who_text = soup.find(string=re.compile(r"([\d.]+)\s*раз"))
                if who_text:
                    match = re.search(r"([\d.]+)\s*раз", str(who_text))
                    if match:
                        pm25_value = round(float(match.group(1)) * 5, 1)

            # Fallback: find AQI from any aqi-bg div
            if aqi_value is None:
                aqi_divs = soup.find_all("div", class_=lambda c: c and "aqi-bg-" in c)
                for div in aqi_divs:
                    p = div.find("p")
                    if p:
                        text = p.get_text(strip=True)
                        if text.isdigit() and 1 <= int(text) <= 500:
                            aqi_value = int(text)
                            break

            if pm25_value is None or aqi_value is None:
                logger.warning(f"Could not parse data for {station_id}: PM2.5={pm25_value}, AQI={aqi_value}")
                return None

            # Get station metadata (name, district, lat, lon)
            station_info = self.STATIONS.get(station_id, (station_id, "Unknown", None, None))
            station_name = station_info[0]
            district = station_info[1]
            lat = station_info[2] if len(station_info) > 2 else None
            lon = station_info[3] if len(station_info) > 3 else None

            return StationReading(
                station_id=station_id,
                station_name=station_name,
                pm25=pm25_value,
                aqi=aqi_value,
                latitude=lat,
                longitude=lon,
                district=district,
                temperature=temperature,
                humidity=humidity,
                wind_speed=wind_speed,
                wind_direction=wind_direction,
                url=f"{self.BASE_URL}/{station_id}",
            )

        except Exception as e:
            logger.error(f"Error parsing {station_id}: {e}")
            return None

    def fetch_station(self, station_id: str) -> Optional[StationReading]:
        """Fetch data from a single station."""
        url = f"{self.BASE_URL}/{station_id}"

        try:
            response = self.session.get(url, timeout=self.timeout)

            if response.status_code != 200:
                logger.warning(f"HTTP {response.status_code} for {station_id}")
                return None

            return self._parse_station_page(response.text, station_id)

        except requests.RequestException as e:
            logger.error(f"Request error for {station_id}: {e}")
            return None

    def fetch_all_stations(self, parallel: bool = True) -> MultiStationData:
        """
        Fetch data from all configured stations.

        Args:
            parallel: Use parallel requests (faster but more connections)

        Returns:
            MultiStationData with readings from all successful stations
        """
        readings = []
        station_ids = list(self.STATIONS.keys())

        if parallel:
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {
                    executor.submit(self.fetch_station, sid): sid
                    for sid in station_ids
                }

                for future in as_completed(futures):
                    station_id = futures[future]
                    try:
                        reading = future.result()
                        if reading:
                            readings.append(reading)
                            logger.debug(f"{station_id}: PM2.5={reading.pm25}, AQI={reading.aqi}")
                    except Exception as e:
                        logger.error(f"Error fetching {station_id}: {e}")
        else:
            for station_id in station_ids:
                reading = self.fetch_station(station_id)
                if reading:
                    readings.append(reading)

        result = MultiStationData(readings=readings)

        if readings:
            logger.info(
                f"IQAir scraped {result.count}/{len(station_ids)} stations: "
                f"PM2.5 mean={result.pm25_mean:.1f}, "
                f"range=[{result.pm25_min:.0f}-{result.pm25_max:.0f}] µg/m³"
            )
        else:
            logger.warning("No stations successfully scraped")

        return result


# =============================================================================
# Convenience Functions
# =============================================================================


def get_bishkek_pm25() -> Optional[MultiStationData]:
    """
    Get current PM2.5 data from all Bishkek stations.

    Returns:
        MultiStationData with readings from all stations, or None on failure

    Example:
        >>> data = get_bishkek_pm25()
        >>> if data:
        ...     print(f"PM2.5 mean: {data.pm25_mean:.1f} µg/m³")
        ...     print(f"Stations: {data.count}")
    """
    scraper = IQAirScraper()
    return scraper.fetch_all_stations()


# =============================================================================
# Main
# =============================================================================


def main():
    """Test the scraper."""
    print("=" * 70)
    print("IQAir Bishkek Multi-Station Scraper")
    print("=" * 70)

    scraper = IQAirScraper()
    data = scraper.fetch_all_stations()

    print(f"\nScraped {data.count} stations at {data.timestamp.strftime('%H:%M:%S')}")
    print("-" * 70)

    # Sort by PM2.5 descending
    for reading in sorted(data.readings, key=lambda r: r.pm25, reverse=True):
        weather = ""
        if reading.temperature is not None:
            weather += f"T={reading.temperature}°C "
        if reading.humidity is not None:
            weather += f"H={reading.humidity}% "
        if reading.wind_speed is not None:
            weather += f"W={reading.wind_speed}km/h"

        print(f"{reading.station_name:40} PM2.5={reading.pm25:>6.1f}  AQI={reading.aqi:>3}  {weather}")

    print("-" * 70)
    print(f"Statistics:")
    print(f"  Mean:   {data.pm25_mean:.1f} µg/m³")
    print(f"  Median: {data.pm25_median:.1f} µg/m³")
    print(f"  Min:    {data.pm25_min:.1f} µg/m³")
    print(f"  Max:    {data.pm25_max:.1f} µg/m³")
    print(f"  Std:    {data.pm25_std:.1f} µg/m³")
    print("=" * 70)


if __name__ == "__main__":
    main()
