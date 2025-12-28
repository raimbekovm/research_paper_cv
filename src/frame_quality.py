"""
Frame quality assessment module for AirVision PM2.5 estimation system.

This module provides functionality for assessing the quality of captured frames
and filtering out frames unsuitable for atmospheric visibility analysis.

Quality metrics include:
    - Brightness: Mean pixel intensity
    - Contrast: Standard deviation of pixel intensities
    - Sharpness: Laplacian variance (blur detection)
    - Sky coverage: Percentage of sky visible in frame

Example:
    >>> from src.frame_quality import QualityAssessor, assess_frame_quality
    >>> metrics = assess_frame_quality(frame)
    >>> if metrics.is_valid:
    ...     print("Frame is suitable for analysis")
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple, Union

import cv2
import numpy as np

from src.utils.logging import get_logger

logger = get_logger(__name__)


class RejectionReason(Enum):
    """Reasons for frame rejection."""

    NONE = "OK"
    TOO_DARK = "too_dark"
    TOO_BRIGHT = "too_bright"
    LOW_CONTRAST = "low_contrast"
    BLURRY = "blurry"
    INSUFFICIENT_SKY = "insufficient_sky"


@dataclass
class QualityThresholds:
    """
    Thresholds for frame quality assessment.

    Attributes:
        min_brightness: Minimum mean brightness (0-255)
        max_brightness: Maximum mean brightness (0-255)
        min_contrast: Minimum contrast (std deviation)
        min_sharpness: Minimum sharpness (Laplacian variance)
        min_sky_percentage: Minimum sky coverage percentage (0-100)
    """

    min_brightness: float = 30.0
    max_brightness: float = 250.0
    min_contrast: float = 20.0
    min_sharpness: float = 100.0
    min_sky_percentage: float = 30.0

    @classmethod
    def default(cls) -> "QualityThresholds":
        """Return default thresholds."""
        return cls()

    @classmethod
    def strict(cls) -> "QualityThresholds":
        """Return strict thresholds for high-quality frames."""
        return cls(
            min_brightness=50.0,
            max_brightness=240.0,
            min_contrast=30.0,
            min_sharpness=150.0,
            min_sky_percentage=40.0,
        )

    @classmethod
    def lenient(cls) -> "QualityThresholds":
        """Return lenient thresholds for maximum frame retention."""
        return cls(
            min_brightness=20.0,
            max_brightness=255.0,
            min_contrast=15.0,
            min_sharpness=50.0,
            min_sky_percentage=20.0,
        )


@dataclass
class QualityMetrics:
    """
    Quality metrics for a single frame.

    Attributes:
        brightness: Mean brightness (0-255)
        contrast: Contrast as std deviation
        sharpness: Sharpness as Laplacian variance
        sky_percentage: Estimated sky coverage (0-100)
        is_valid: Whether frame passes quality thresholds
        rejection_reason: Reason for rejection if invalid
    """

    brightness: float
    contrast: float
    sharpness: float
    sky_percentage: float
    is_valid: bool = True
    rejection_reason: RejectionReason = RejectionReason.NONE

    def to_dict(self) -> dict:
        """Convert metrics to dictionary."""
        return {
            "brightness": round(self.brightness, 2),
            "contrast": round(self.contrast, 2),
            "sharpness": round(self.sharpness, 2),
            "sky_percentage": round(self.sky_percentage, 2),
            "is_valid": self.is_valid,
            "rejection_reason": self.rejection_reason.value,
        }


class QualityAssessor:
    """
    Frame quality assessor for atmospheric visibility analysis.

    This class evaluates frames based on multiple quality metrics to determine
    their suitability for PM2.5 estimation from atmospheric visibility.

    Args:
        thresholds: Quality thresholds for frame validation

    Example:
        >>> assessor = QualityAssessor(QualityThresholds.default())
        >>> metrics = assessor.assess(frame)
        >>> print(f"Valid: {metrics.is_valid}, Sky: {metrics.sky_percentage}%")
    """

    def __init__(self, thresholds: Optional[QualityThresholds] = None):
        self.thresholds = thresholds or QualityThresholds.default()
        logger.debug(f"Initialized QualityAssessor with thresholds: {self.thresholds}")

    def assess(self, frame: np.ndarray) -> QualityMetrics:
        """
        Assess quality of a single frame.

        Args:
            frame: BGR image as numpy array (H, W, 3)

        Returns:
            QualityMetrics object with assessment results

        Raises:
            ValueError: If frame is invalid or empty
        """
        if frame is None or frame.size == 0:
            raise ValueError("Invalid frame: empty or None")

        if len(frame.shape) != 3 or frame.shape[2] != 3:
            raise ValueError(f"Invalid frame shape: expected (H, W, 3), got {frame.shape}")

        # Convert to grayscale for analysis
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Calculate metrics
        brightness = self._calculate_brightness(gray)
        contrast = self._calculate_contrast(gray)
        sharpness = self._calculate_sharpness(gray)
        sky_percentage = self._calculate_sky_percentage(gray)

        # Validate against thresholds
        is_valid, rejection_reason = self._validate(
            brightness, contrast, sharpness, sky_percentage
        )

        return QualityMetrics(
            brightness=brightness,
            contrast=contrast,
            sharpness=sharpness,
            sky_percentage=sky_percentage,
            is_valid=is_valid,
            rejection_reason=rejection_reason,
        )

    def _calculate_brightness(self, gray: np.ndarray) -> float:
        """Calculate mean brightness."""
        return float(np.mean(gray))

    def _calculate_contrast(self, gray: np.ndarray) -> float:
        """Calculate contrast as standard deviation."""
        return float(np.std(gray))

    def _calculate_sharpness(self, gray: np.ndarray) -> float:
        """
        Calculate sharpness using Laplacian variance.

        Higher values indicate sharper images.
        """
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        return float(laplacian.var())

    def _calculate_sky_percentage(self, gray: np.ndarray) -> float:
        """
        Estimate sky coverage in upper portion of frame.

        Assumes sky is typically brighter (>100) and in upper third of image.
        """
        height = gray.shape[0]
        upper_region = gray[: height // 3, :]

        # Sky pixels are typically brighter than 100
        sky_threshold = 100
        sky_pixels = np.sum(upper_region > sky_threshold)
        total_pixels = upper_region.size

        return float(sky_pixels / total_pixels * 100)

    def _validate(
        self,
        brightness: float,
        contrast: float,
        sharpness: float,
        sky_percentage: float,
    ) -> Tuple[bool, RejectionReason]:
        """
        Validate metrics against thresholds.

        Returns:
            Tuple of (is_valid, rejection_reason)
        """
        t = self.thresholds

        if brightness < t.min_brightness:
            return False, RejectionReason.TOO_DARK

        if brightness > t.max_brightness:
            return False, RejectionReason.TOO_BRIGHT

        if contrast < t.min_contrast:
            return False, RejectionReason.LOW_CONTRAST

        if sharpness < t.min_sharpness:
            return False, RejectionReason.BLURRY

        if sky_percentage < t.min_sky_percentage:
            return False, RejectionReason.INSUFFICIENT_SKY

        return True, RejectionReason.NONE


# Module-level convenience functions


def assess_frame_quality(
    frame: np.ndarray,
    thresholds: Optional[QualityThresholds] = None,
) -> QualityMetrics:
    """
    Assess quality of a frame.

    Args:
        frame: BGR image as numpy array
        thresholds: Optional quality thresholds

    Returns:
        QualityMetrics with assessment results

    Example:
        >>> metrics = assess_frame_quality(frame)
        >>> print(f"Brightness: {metrics.brightness:.1f}")
    """
    assessor = QualityAssessor(thresholds)
    return assessor.assess(frame)


def filter_low_quality_frames(
    frames: list[np.ndarray],
    thresholds: Optional[QualityThresholds] = None,
) -> list[Tuple[np.ndarray, QualityMetrics]]:
    """
    Filter list of frames, keeping only high-quality ones.

    Args:
        frames: List of BGR images
        thresholds: Optional quality thresholds

    Returns:
        List of (frame, metrics) tuples for valid frames only
    """
    assessor = QualityAssessor(thresholds)
    valid_frames = []

    for frame in frames:
        try:
            metrics = assessor.assess(frame)
            if metrics.is_valid:
                valid_frames.append((frame, metrics))
        except ValueError as e:
            logger.warning(f"Skipping invalid frame: {e}")

    logger.info(f"Filtered frames: {len(valid_frames)}/{len(frames)} passed")
    return valid_frames


def calculate_brightness(frame: np.ndarray) -> float:
    """
    Calculate brightness of a frame.

    Args:
        frame: BGR or grayscale image

    Returns:
        Mean brightness (0-255)
    """
    if len(frame.shape) == 3:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    else:
        gray = frame
    return float(np.mean(gray))


def calculate_contrast(frame: np.ndarray) -> float:
    """
    Calculate contrast of a frame.

    Args:
        frame: BGR or grayscale image

    Returns:
        Contrast as standard deviation
    """
    if len(frame.shape) == 3:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    else:
        gray = frame
    return float(np.std(gray))


# Legacy compatibility aliases
FrameQualityFilter = QualityAssessor
get_default_filter = lambda: QualityAssessor(QualityThresholds.default())
get_strict_filter = lambda: QualityAssessor(QualityThresholds.strict())
get_lenient_filter = lambda: QualityAssessor(QualityThresholds.lenient())


def main():
    """Test quality assessment on sample images."""
    import os

    print("=" * 60)
    print("AirVision Frame Quality Assessment")
    print("=" * 60)

    # Test directories
    test_dirs = [
        "data/images/bishkek_panorama",
        "data/images/sovmin",
        "data/images/kt_center",
        "data/test_images",
    ]

    assessor = QualityAssessor(QualityThresholds.default())

    print(f"\nThresholds:")
    print(f"  Brightness: {assessor.thresholds.min_brightness}-{assessor.thresholds.max_brightness}")
    print(f"  Contrast: >= {assessor.thresholds.min_contrast}")
    print(f"  Sharpness: >= {assessor.thresholds.min_sharpness}")
    print(f"  Sky: >= {assessor.thresholds.min_sky_percentage}%")

    for test_dir in test_dirs:
        if not os.path.exists(test_dir):
            continue

        print(f"\n--- {test_dir} ---")

        valid_count = 0
        total_count = 0

        for filename in sorted(os.listdir(test_dir))[:5]:  # Limit to 5 files
            if not filename.lower().endswith((".jpg", ".jpeg", ".png")):
                continue

            filepath = os.path.join(test_dir, filename)
            frame = cv2.imread(filepath)

            if frame is None:
                continue

            total_count += 1
            metrics = assessor.assess(frame)

            if metrics.is_valid:
                valid_count += 1
                status = "PASS"
            else:
                status = f"FAIL ({metrics.rejection_reason.value})"

            print(f"  {filename}: {status}")
            print(f"    brightness={metrics.brightness:.0f}, "
                  f"contrast={metrics.contrast:.0f}, "
                  f"sky={metrics.sky_percentage:.1f}%")

        if total_count > 0:
            print(f"  Result: {valid_count}/{total_count} passed "
                  f"({valid_count/total_count*100:.0f}%)")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
