"""
Camera configuration for AirVision PM2.5 estimation system.

This module defines camera configurations for webcams used in atmospheric
visibility analysis and PM2.5 estimation in Bishkek, Kyrgyzstan.

Example:
    >>> from src.camera_config import get_active_cameras, CameraRegistry
    >>> cameras = get_active_cameras()
    >>> for cam_id, cam in cameras.items():
    ...     print(f"{cam_id}: {cam.name}")
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from src.utils.logging import get_logger

logger = get_logger(__name__)


class ViewingAngle(Enum):
    """Camera viewing angle classification."""

    DOWNWARD = "downward"
    HORIZONTAL = "horizontal"
    HORIZONTAL_WIDE = "horizontal-wide"
    ELEVATED_WIDE = "elevated-wide"
    PANORAMIC_WIDE = "panoramic-wide"
    ROTATING = "rotating"


@dataclass
class CameraLocation:
    """Geographic location and orientation of a camera."""

    latitude: float
    longitude: float
    viewing_direction: str  # Compass direction (e.g., "330° NW")
    viewing_angle: ViewingAngle

    @property
    def coordinates(self) -> Tuple[float, float]:
        """Return coordinates as (lat, lon) tuple."""
        return (self.latitude, self.longitude)


@dataclass
class CameraQualityMetrics:
    """Quality metrics for camera suitability in PM2.5 estimation."""

    visual_quality_score: int  # 1-10 scale
    sky_coverage_percent: int  # Estimated sky percentage in frame
    depth_of_field_km: float  # Visible distance in km
    pm25_sensor_distance_km: Optional[float] = None
    nearest_sensor: Optional[str] = None

    def __post_init__(self):
        if not 1 <= self.visual_quality_score <= 10:
            raise ValueError("visual_quality_score must be between 1 and 10")


@dataclass
class Camera:
    """
    Webcam configuration for atmospheric visibility analysis.

    Attributes:
        id: Unique camera identifier
        name: Human-readable camera name
        url: HLS stream URL
        location: Geographic location and orientation
        quality: Quality metrics for PM2.5 estimation
        recommended: Whether camera is recommended for use
        require_quality_filter: Whether frames need quality filtering
        description: Detailed description of camera characteristics
    """

    id: str
    name: str
    url: str
    location: CameraLocation
    quality: CameraQualityMetrics
    recommended: bool = False
    require_quality_filter: bool = False
    description: str = ""

    @property
    def coordinates(self) -> Tuple[float, float]:
        """Return camera coordinates."""
        return self.location.coordinates

    @property
    def is_rotating(self) -> bool:
        """Check if camera is rotating type."""
        return self.location.viewing_angle == ViewingAngle.ROTATING


class CameraRegistry:
    """
    Registry of available cameras for PM2.5 estimation.

    This class manages camera configurations and provides methods
    for querying and filtering cameras based on various criteria.

    Example:
        >>> registry = CameraRegistry()
        >>> active = registry.get_recommended()
        >>> print(f"Found {len(active)} recommended cameras")
    """

    def __init__(self):
        self._cameras: Dict[str, Camera] = {}
        self._initialize_cameras()

    def _initialize_cameras(self) -> None:
        """Initialize camera configurations."""

        # Bishkek Panorama - PRIMARY camera
        self._register(Camera(
            id="bishkek_panorama",
            name="Bishkek Panorama",
            url="https://stream.kt.kg:5443/live/camera28.m3u8",
            location=CameraLocation(
                latitude=42.799197,
                longitude=74.645485,
                viewing_direction="330° NW",
                viewing_angle=ViewingAngle.PANORAMIC_WIDE,
            ),
            quality=CameraQualityMetrics(
                visual_quality_score=10,
                sky_coverage_percent=50,
                depth_of_field_km=10.0,
                pm25_sensor_distance_km=7.24,
                nearest_sensor="Ak-Orgo",
            ),
            recommended=True,
            require_quality_filter=False,
            description=(
                "Ideal panoramic view of entire city. Excellent atmospheric haze "
                "visibility with 50% sky coverage and 10+ km depth. Sensor distance "
                "of 7.24 km is acceptable due to visibility integration along line of sight."
            ),
        ))

        # Sovmin - SECONDARY camera
        self._register(Camera(
            id="sovmin",
            name="Bishkek Sovmin",
            url="https://stream.kt.kg:5443/live/camera33.m3u8",
            location=CameraLocation(
                latitude=42.804394,
                longitude=74.587977,
                viewing_direction="45° NE",
                viewing_angle=ViewingAngle.ELEVATED_WIDE,
            ),
            quality=CameraQualityMetrics(
                visual_quality_score=9,
                sky_coverage_percent=40,
                depth_of_field_km=5.0,
                pm25_sensor_distance_km=5.07,
                nearest_sensor="Ak-Orgo",
            ),
            recommended=True,
            require_quality_filter=False,
            description=(
                "Excellent panoramic view of southern residential district. "
                "Good atmospheric haze visibility with 40% sky and 5+ km depth."
            ),
        ))

        # KT Center - SUPPLEMENTARY camera (rotating)
        self._register(Camera(
            id="kt_center",
            name="Kyrgyztelecom Center",
            url="https://stream.kt.kg:5443/live/camera35.m3u8",
            location=CameraLocation(
                latitude=42.874689,
                longitude=74.612241,
                viewing_direction="variable (rotating)",
                viewing_angle=ViewingAngle.ROTATING,
            ),
            quality=CameraQualityMetrics(
                visual_quality_score=7,
                sky_coverage_percent=30,
                depth_of_field_km=3.0,
                pm25_sensor_distance_km=0.01,
                nearest_sensor="US Embassy Bishkek",
            ),
            recommended=True,
            require_quality_filter=True,
            description=(
                "Rotating camera requiring frame quality filtering (~75% acceptance rate). "
                "Closest to PM2.5 sensor (10m). Mountains visible but many nearby buildings."
            ),
        ))

        # Ala-Too Square - NOT recommended
        self._register(Camera(
            id="ala_too_square",
            name="Ala-Too Square",
            url="https://stream.kt.kg:5443/live/camera25.m3u8",
            location=CameraLocation(
                latitude=42.875576,
                longitude=74.603629,
                viewing_direction="10° N",
                viewing_angle=ViewingAngle.DOWNWARD,
            ),
            quality=CameraQualityMetrics(
                visual_quality_score=3,
                sky_coverage_percent=10,
                depth_of_field_km=0.5,
            ),
            recommended=False,
            require_quality_filter=False,
            description="Downward view of square. Too much foreground, insufficient horizon.",
        ))

        # Ala-Too Square 2 - NOT recommended
        self._register(Camera(
            id="ala_too_square_2",
            name="Ala-Too Square (Camera 2)",
            url="https://stream.kt.kg:5443/live/camera27.m3u8",
            location=CameraLocation(
                latitude=42.875767,
                longitude=74.604619,
                viewing_direction="90° E",
                viewing_angle=ViewingAngle.HORIZONTAL_WIDE,
            ),
            quality=CameraQualityMetrics(
                visual_quality_score=3,
                sky_coverage_percent=15,
                depth_of_field_km=0.5,
                pm25_sensor_distance_km=0.07,
                nearest_sensor="Chuy Avenue",
            ),
            recommended=False,
            require_quality_filter=False,
            description=(
                "Poor visual quality for atmospheric visibility despite close sensor. "
                "Too much foreground (square, road, monument, people)."
            ),
        ))

        logger.info(f"Initialized {len(self._cameras)} cameras")

    def _register(self, camera: Camera) -> None:
        """Register a camera in the registry."""
        self._cameras[camera.id] = camera

    def get(self, camera_id: str) -> Optional[Camera]:
        """
        Get camera by ID.

        Args:
            camera_id: Unique camera identifier

        Returns:
            Camera instance or None if not found
        """
        return self._cameras.get(camera_id)

    def get_all(self) -> Dict[str, Camera]:
        """Get all registered cameras."""
        return self._cameras.copy()

    def get_recommended(self) -> Dict[str, Camera]:
        """Get only recommended cameras."""
        return {k: v for k, v in self._cameras.items() if v.recommended}

    def get_by_quality(self, min_score: int = 7) -> Dict[str, Camera]:
        """
        Get cameras meeting minimum quality threshold.

        Args:
            min_score: Minimum visual quality score (1-10)

        Returns:
            Dictionary of cameras meeting threshold
        """
        return {
            k: v for k, v in self._cameras.items()
            if v.quality.visual_quality_score >= min_score
        }

    def list_ids(self) -> List[str]:
        """Get list of all camera IDs."""
        return list(self._cameras.keys())

    def __len__(self) -> int:
        return len(self._cameras)

    def __iter__(self):
        return iter(self._cameras.values())


# Global registry instance
_registry: Optional[CameraRegistry] = None


def get_registry() -> CameraRegistry:
    """Get the global camera registry instance."""
    global _registry
    if _registry is None:
        _registry = CameraRegistry()
    return _registry


def get_active_cameras() -> Dict[str, Camera]:
    """
    Get dictionary of active (recommended) cameras.

    Returns:
        Dictionary mapping camera IDs to Camera instances
    """
    return get_registry().get_recommended()


def get_camera(camera_id: str) -> Optional[Camera]:
    """
    Get a specific camera by ID.

    Args:
        camera_id: Camera identifier

    Returns:
        Camera instance or None
    """
    return get_registry().get(camera_id)


# Legacy compatibility
CAMERAS = {
    cam_id: {
        "name": cam.name,
        "url": cam.url,
        "coordinates": cam.coordinates,
        "viewing_direction": cam.location.viewing_direction,
        "viewing_angle": cam.location.viewing_angle.value,
        "recommended": cam.recommended,
        "require_quality_filter": cam.require_quality_filter,
        "visual_quality_score": cam.quality.visual_quality_score,
        "pm25_sensor_distance_km": cam.quality.pm25_sensor_distance_km,
        "nearest_sensor": cam.quality.nearest_sensor,
        "description": cam.description,
    }
    for cam_id, cam in get_registry().get_all().items()
}


def get_recommended_cameras() -> Dict[str, dict]:
    """Legacy function: Get recommended cameras as dictionaries."""
    return {k: v for k, v in CAMERAS.items() if v["recommended"]}


if __name__ == "__main__":
    # Demo usage
    registry = get_registry()

    print("=" * 70)
    print("AirVision Camera Registry")
    print("=" * 70)

    for camera in registry:
        status = "RECOMMENDED" if camera.recommended else "not recommended"
        quality = camera.quality.visual_quality_score
        print(f"\n[{camera.id}] {camera.name}")
        print(f"  Status: {status} | Quality: {quality}/10")
        print(f"  Location: {camera.coordinates}")
        print(f"  Direction: {camera.location.viewing_direction}")
        print(f"  Sky coverage: {camera.quality.sky_coverage_percent}%")
        print(f"  Depth: {camera.quality.depth_of_field_km} km")
        if camera.quality.pm25_sensor_distance_km:
            print(f"  Sensor distance: {camera.quality.pm25_sensor_distance_km} km")

    print("\n" + "=" * 70)
    print(f"Total: {len(registry)} cameras | Recommended: {len(registry.get_recommended())}")
    print("=" * 70)
