"""
Data collection pipeline for AirVision PM2.5 estimation system.

This module provides automated data collection from multiple webcams
with support for daylight-only collection, quality filtering, and
continuous monitoring.

Example:
    >>> from src.collect_data import DataCollector
    >>> collector = DataCollector()
    >>> results = collector.collect_once()

Command-line usage:
    $ python -m src.collect_data --mode continuous --interval 30
"""

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from src.camera_config import Camera, get_active_cameras, get_night_cameras, get_camera, CAMERAS, get_recommended_cameras
from src.frame_quality import QualityAssessor, QualityMetrics, QualityThresholds
from src.fetch_pm25_data import PM25Collector, PM25Reading, WeatherData
from src.utils.logging import get_logger
from src.utils.io import ensure_dir, save_json

logger = get_logger(__name__)


@dataclass
class CollectionConfig:
    """
    Configuration for data collection.

    Attributes:
        output_dir: Base directory for saving images
        interval_minutes: Time between collections
        duration_hours: Total duration (None for infinite)
        daylight_only: Whether to skip nighttime
        daylight_start: Start hour for daylight (0-23)
        daylight_end: End hour for daylight (0-23)
        max_workers: Max threads for parallel capture
        jpeg_quality: JPEG compression quality (1-100)
    """

    output_dir: Path = field(default_factory=lambda: Path("data/images"))
    interval_minutes: int = 30
    duration_hours: Optional[int] = None
    daylight_only: bool = True
    daylight_start: int = 8
    daylight_end: int = 18
    max_workers: int = 5
    jpeg_quality: int = 95


@dataclass
class CaptureResult:
    """Result of a single camera capture attempt."""

    camera_id: str
    camera_name: str
    success: bool
    timestamp: datetime
    filepath: Optional[Path] = None
    resolution: Optional[Tuple[int, int]] = None
    error: Optional[str] = None
    filtered: bool = False
    quality_metrics: Optional[Dict] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "camera_id": self.camera_id,
            "camera_name": self.camera_name,
            "success": self.success,
            "timestamp": self.timestamp.isoformat(),
            "filepath": str(self.filepath) if self.filepath else None,
            "resolution": self.resolution,
            "error": self.error,
            "filtered": self.filtered,
            "quality_metrics": self.quality_metrics,
        }


class DataCollector:
    """
    Multi-camera data collector for atmospheric visibility analysis.

    This class manages automated data collection from multiple webcams,
    with support for parallel capture, quality filtering, and daylight-only
    collection modes.

    Args:
        cameras: Dictionary of cameras to collect from
        config: Collection configuration

    Example:
        >>> collector = DataCollector()
        >>> results = collector.collect_once()
        >>> print(f"Captured {sum(r.success for r in results)} frames")
    """

    def __init__(
        self,
        cameras: Optional[Dict[str, Camera]] = None,
        config: Optional[CollectionConfig] = None,
    ):
        self.day_cameras = cameras or get_active_cameras()
        self.night_cameras = get_night_cameras()
        self.cameras = self.day_cameras  # Default to day cameras
        self.config = config or CollectionConfig()
        self.quality_assessor = QualityAssessor(QualityThresholds.default())
        self.pm25_collector = PM25Collector(output_dir=self.config.output_dir / "pm25")

        # Create output directories for all cameras
        all_camera_ids = set(self.day_cameras.keys()) | set(self.night_cameras.keys())
        for camera_id in all_camera_ids:
            ensure_dir(self.config.output_dir / camera_id)

        ensure_dir(self.config.output_dir / "metadata")

        logger.info(f"Initialized DataCollector: {len(self.day_cameras)} day cameras, {len(self.night_cameras)} night cameras")

    def is_daylight(self) -> bool:
        """Check if current time is within daylight hours."""
        current_hour = datetime.now().hour
        return self.config.daylight_start <= current_hour < self.config.daylight_end

    def get_current_cameras(self) -> Dict[str, Camera]:
        """Get appropriate cameras for current time of day."""
        if self.is_daylight():
            return self.day_cameras
        else:
            return self.night_cameras

    def fetch_environmental_data(self) -> Optional[dict]:
        """Fetch current PM2.5 and weather data from all stations."""
        try:
            result = self.pm25_collector.fetch_all(save=False)
            if result.best_reading:
                reading = result.best_reading
                env_data = {
                    "pm25": reading.value,
                    "aqi": reading.aqi,
                    "source": reading.source.value if reading.source else None,
                    "weather": reading.weather.to_dict() if reading.weather else None,
                    "timestamp": reading.timestamp.isoformat() if reading.timestamp else None,
                }

                # Include multi-station data if available
                if result.multi_station:
                    ms = result.multi_station
                    env_data["stations"] = {
                        "count": ms.count,
                        "pm25_mean": round(ms.pm25_mean, 1),
                        "pm25_median": round(ms.pm25_median, 1),
                        "pm25_min": round(ms.pm25_min, 1),
                        "pm25_max": round(ms.pm25_max, 1),
                        "pm25_std": round(ms.pm25_std, 1),
                        "weather_iqair": {
                            "temperature": round(ms.temperature_mean, 1) if ms.temperature_mean else None,
                            "humidity": round(ms.humidity_mean, 1) if ms.humidity_mean else None,
                            "wind_speed": round(ms.wind_speed_mean, 1) if ms.wind_speed_mean else None,
                        },
                        "readings": [r.to_dict() for r in ms.readings],
                    }

                return env_data
        except Exception as e:
            logger.warning(f"Failed to fetch environmental data: {e}")
        return None

    def _capture_single(
        self,
        camera_id: str,
        camera: Camera,
        timestamp: datetime,
    ) -> CaptureResult:
        """
        Capture a single frame from one camera.

        Args:
            camera_id: Camera identifier
            camera: Camera configuration
            timestamp: Capture timestamp

        Returns:
            CaptureResult with capture status and metadata
        """
        cap = None
        try:
            # Open video stream
            cap = cv2.VideoCapture(camera.url)

            if not cap.isOpened():
                return CaptureResult(
                    camera_id=camera_id,
                    camera_name=camera.name,
                    success=False,
                    timestamp=timestamp,
                    error="Failed to open stream",
                )

            # Read frame
            ret, frame = cap.read()

            if not ret or frame is None:
                return CaptureResult(
                    camera_id=camera_id,
                    camera_name=camera.name,
                    success=False,
                    timestamp=timestamp,
                    error="Failed to read frame",
                )

            # Quality check for rotating cameras
            quality_metrics = None
            if camera.require_quality_filter:
                metrics = self.quality_assessor.assess(frame)
                quality_metrics = metrics.to_dict()

                if not metrics.is_valid:
                    return CaptureResult(
                        camera_id=camera_id,
                        camera_name=camera.name,
                        success=False,
                        timestamp=timestamp,
                        error=f"Quality filter: {metrics.rejection_reason.value}",
                        filtered=True,
                        quality_metrics=quality_metrics,
                    )

            # Generate filepath
            timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
            filename = f"{camera_id}_{timestamp_str}.jpg"
            filepath = self.config.output_dir / camera_id / filename

            # Save frame
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, self.config.jpeg_quality]
            cv2.imwrite(str(filepath), frame, encode_params)

            return CaptureResult(
                camera_id=camera_id,
                camera_name=camera.name,
                success=True,
                timestamp=timestamp,
                filepath=filepath,
                resolution=(frame.shape[1], frame.shape[0]),
                quality_metrics=quality_metrics,
            )

        except Exception as e:
            logger.exception(f"Error capturing {camera_id}")
            return CaptureResult(
                camera_id=camera_id,
                camera_name=camera.name,
                success=False,
                timestamp=timestamp,
                error=str(e),
            )

        finally:
            if cap is not None:
                cap.release()

    def collect_once(self, fetch_env_data: bool = True) -> Tuple[List[CaptureResult], Optional[dict]]:
        """
        Collect frames from appropriate cameras and environmental data.

        Args:
            fetch_env_data: Whether to fetch PM2.5 and weather data

        Returns:
            Tuple of (capture results, environmental data)
        """
        timestamp = datetime.now()
        results = []

        # Select cameras based on time of day
        current_cameras = self.get_current_cameras()
        is_day = self.is_daylight()
        mode = "day" if is_day else "night"

        logger.info(f"Starting {mode} capture from {len(current_cameras)} cameras")

        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            futures = {
                executor.submit(self._capture_single, cam_id, cam, timestamp): cam_id
                for cam_id, cam in current_cameras.items()
            }

            for future in as_completed(futures):
                result = future.result()
                results.append(result)

                if result.success:
                    logger.info(f"Captured {result.camera_id}: {result.resolution}")
                elif result.filtered:
                    logger.debug(f"Filtered {result.camera_id}: {result.error}")
                else:
                    logger.warning(f"Failed {result.camera_id}: {result.error}")

        successful = sum(1 for r in results if r.success)
        filtered = sum(1 for r in results if r.filtered)
        logger.info(f"Collection complete: {successful}/{len(results)} successful, {filtered} filtered")

        # Fetch environmental data
        env_data = None
        if fetch_env_data:
            env_data = self.fetch_environmental_data()
            if env_data:
                logger.info(f"PM2.5: {env_data['pm25']:.1f} µg/m³ (source: {env_data['source']})")

        return results, env_data

    def _save_metadata(self, results: List[CaptureResult], collection_num: int, env_data: Optional[dict] = None) -> None:
        """Save collection metadata to JSON file."""
        timestamp = datetime.now()
        is_day = self.is_daylight()

        metadata = {
            "collection_number": collection_num,
            "timestamp": timestamp.isoformat(),
            "is_daylight": is_day,
            "mode": "day" if is_day else "night",
            "cameras_total": len(results),
            "cameras_successful": sum(1 for r in results if r.success),
            "cameras_filtered": sum(1 for r in results if r.filtered),
            "results": [r.to_dict() for r in results],
            "pm25": env_data.get("pm25") if env_data else None,
            "aqi": env_data.get("aqi") if env_data else None,
            "pm25_source": env_data.get("source") if env_data else None,
            "weather": env_data.get("weather") if env_data else None,
            "stations": env_data.get("stations") if env_data else None,
        }

        filename = f"collection_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.config.output_dir / "metadata" / filename
        save_json(metadata, filepath)

    def collect_continuous(self) -> None:
        """
        Run continuous data collection.

        Collects data at regular intervals with PM2.5 and weather data.
        Uses all cameras during day, only night-capable cameras at night.
        Runs until duration_hours is reached or interrupted.
        """
        cfg = self.config

        print("=" * 80)
        print("AIRVISION DATA COLLECTION")
        print("=" * 80)
        print(f"Day cameras: {len(self.day_cameras)} | Night cameras: {len(self.night_cameras)}")
        print(f"Interval: {cfg.interval_minutes} minutes")
        print(f"Duration: {cfg.duration_hours or 'infinite'} hours")
        print(f"Output: {cfg.output_dir}")
        print(f"Daylight hours: {cfg.daylight_start}:00 - {cfg.daylight_end}:00")
        print(f"PM2.5 + Weather: enabled")
        print("=" * 80)

        start_time = time.time()
        collection_count = 0

        try:
            while True:
                collection_count += 1
                is_day = self.is_daylight()
                mode = "DAY" if is_day else "NIGHT"
                current_cameras = self.get_current_cameras()

                print(f"\n{'='*80}")
                print(f"Collection #{collection_count} [{mode}] at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"Cameras: {list(current_cameras.keys())}")
                print("=" * 80)

                # Capture from cameras + fetch environmental data
                results, env_data = self.collect_once()
                self._save_metadata(results, collection_count, env_data)

                # Print image results
                successful = sum(1 for r in results if r.success)
                filtered = sum(1 for r in results if r.filtered)

                for r in results:
                    if r.success:
                        qm = r.quality_metrics
                        quality_info = ""
                        if qm:
                            quality_info = f" (brightness={qm['brightness']:.0f}, contrast={qm['contrast']:.0f})"
                        print(f"  [OK] {r.camera_name}: {r.resolution[0]}x{r.resolution[1]}{quality_info}")
                    elif r.filtered:
                        print(f"  [FILTERED] {r.camera_name}: {r.error}")
                    else:
                        print(f"  [FAIL] {r.camera_name}: {r.error}")

                print(f"\nImages: {successful}/{len(results)} successful", end="")
                if filtered:
                    print(f" ({filtered} filtered)")
                else:
                    print()

                # Print environmental data
                if env_data:
                    pm25 = env_data.get('pm25')
                    aqi = env_data.get('aqi')
                    weather = env_data.get('weather') or {}
                    temp = weather.get('temperature')
                    humidity = weather.get('humidity')

                    print(f"PM2.5: {pm25:.1f} µg/m³ (AQI: {aqi})" if pm25 else "PM2.5: N/A")
                    if temp is not None:
                        print(f"Weather: {temp:.1f}°C, {humidity}% humidity")
                else:
                    print("PM2.5: fetch failed")

                # Check duration
                if cfg.duration_hours:
                    elapsed = (time.time() - start_time) / 3600
                    if elapsed >= cfg.duration_hours:
                        print(f"\nCollection complete! Total: {collection_count} collections")
                        break

                # Wait for next interval
                next_time = datetime.fromtimestamp(time.time() + cfg.interval_minutes * 60)
                print(f"\nNext collection at {next_time.strftime('%H:%M:%S')}")
                time.sleep(cfg.interval_minutes * 60)

        except KeyboardInterrupt:
            print(f"\n\nCollection stopped by user. Total: {collection_count} collections")


def main():
    """Main entry point for command-line usage."""
    parser = argparse.ArgumentParser(
        description="AirVision Data Collection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --mode test                    # Single test capture
  %(prog)s --mode continuous --interval 30 --duration 12
  %(prog)s --mode continuous --24-7       # Include nighttime
        """,
    )

    parser.add_argument(
        "--mode",
        choices=["test", "continuous"],
        default="test",
        help="Collection mode (default: test)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Interval between captures in minutes (default: 30)",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=None,
        help="Duration in hours (default: infinite)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/images",
        help="Output directory (default: data/images)",
    )
    parser.add_argument(
        "--daylight-start",
        type=int,
        default=8,
        help="Daylight start hour (default: 8)",
    )
    parser.add_argument(
        "--daylight-end",
        type=int,
        default=18,
        help="Daylight end hour (default: 18)",
    )
    parser.add_argument(
        "--24-7",
        action="store_true",
        dest="all_day",
        help="Collect 24/7 including nighttime",
    )
    parser.add_argument(
        "--all-cameras",
        action="store_true",
        help="Use all cameras including non-recommended",
    )

    args = parser.parse_args()

    # Select cameras
    if args.all_cameras:
        # Convert dict-based CAMERAS to Camera objects
        from src.camera_config import get_registry
        cameras = get_registry().get_all()
        print("Using ALL cameras")
    else:
        cameras = get_active_cameras()
        print("Using recommended cameras only")

    # Create config
    config = CollectionConfig(
        output_dir=Path(args.output),
        interval_minutes=args.interval,
        duration_hours=args.duration,
        daylight_only=not args.all_day,
        daylight_start=args.daylight_start,
        daylight_end=args.daylight_end,
    )

    # Create collector
    collector = DataCollector(cameras=cameras, config=config)

    if args.mode == "test":
        print("\nTEST MODE - Single capture\n")
        results = collector.collect_once()

        print("\nResults:")
        for r in results:
            status = "OK" if r.success else ("FILTERED" if r.filtered else "FAIL")
            print(f"  [{status}] {r.camera_name}")
            if r.filepath:
                print(f"         File: {r.filepath}")
    else:
        collector.collect_continuous()


if __name__ == "__main__":
    main()
