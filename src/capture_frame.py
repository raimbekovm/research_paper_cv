"""
Frame capture module for AirVision PM2.5 estimation system.

This module provides functionality for capturing frames from HLS video streams
of urban webcams used for atmospheric visibility analysis.

Example:
    >>> from src.capture_frame import FrameCapture, capture_single_frame
    >>> frame, metadata = capture_single_frame("bishkek_panorama")
    >>> print(f"Captured frame: {frame.shape}")
"""

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import cv2
import numpy as np

from src.camera_config import Camera, get_active_cameras, get_camera
from src.utils.logging import get_logger

logger = get_logger(__name__)


class CaptureError(Exception):
    """Exception raised when frame capture fails."""

    pass


class StreamConnectionError(CaptureError):
    """Exception raised when unable to connect to video stream."""

    pass


class FrameReadError(CaptureError):
    """Exception raised when unable to read frame from stream."""

    pass


@dataclass
class FrameMetadata:
    """
    Metadata for a captured frame.

    Attributes:
        camera_id: Camera identifier
        timestamp: Capture timestamp
        filepath: Path to saved frame (if saved)
        width: Frame width in pixels
        height: Frame height in pixels
        file_size_bytes: Size of saved file (if saved)
    """

    camera_id: str
    timestamp: datetime
    filepath: Optional[Path] = None
    width: int = 0
    height: int = 0
    file_size_bytes: int = 0

    @property
    def resolution(self) -> str:
        """Return resolution as string (e.g., '1920x1080')."""
        return f"{self.width}x{self.height}"


class FrameCapture:
    """
    Frame capture handler for webcam streams.

    This class manages the capture of individual frames from HLS video streams,
    with support for automatic retries and proper resource cleanup.

    Args:
        camera: Camera configuration object
        output_dir: Directory for saving captured frames
        timeout: Connection timeout in seconds
        max_retries: Maximum number of retry attempts

    Example:
        >>> from src.camera_config import get_camera
        >>> camera = get_camera("bishkek_panorama")
        >>> capture = FrameCapture(camera)
        >>> frame, metadata = capture.capture()
    """

    def __init__(
        self,
        camera: Camera,
        output_dir: Union[str, Path] = "data/images",
        timeout: int = 10,
        max_retries: int = 3,
    ):
        self.camera = camera
        self.output_dir = Path(output_dir) / camera.id
        self.timeout = timeout
        self.max_retries = max_retries

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.debug(f"Initialized FrameCapture for {camera.id}")

    def _create_capture(self) -> cv2.VideoCapture:
        """
        Create and configure OpenCV video capture.

        Returns:
            Configured VideoCapture object

        Raises:
            StreamConnectionError: If unable to open stream
        """
        cap = cv2.VideoCapture(self.camera.url)

        # Set capture properties
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if not cap.isOpened():
            raise StreamConnectionError(
                f"Failed to open stream: {self.camera.url}"
            )

        return cap

    def _generate_filename(self, timestamp: datetime) -> Path:
        """Generate filename for captured frame."""
        filename = f"{self.camera.id}_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"
        return self.output_dir / filename

    def capture(
        self,
        save: bool = True,
        quality: int = 95,
    ) -> Tuple[np.ndarray, FrameMetadata]:
        """
        Capture a single frame from the video stream.

        Args:
            save: Whether to save the frame to disk
            quality: JPEG quality for saved frames (1-100)

        Returns:
            Tuple of (frame as numpy array, frame metadata)

        Raises:
            CaptureError: If capture fails after all retries
        """
        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries):
            try:
                return self._capture_attempt(save=save, quality=quality)

            except CaptureError as e:
                last_error = e
                logger.warning(
                    f"Capture attempt {attempt + 1}/{self.max_retries} failed: {e}"
                )

                if attempt < self.max_retries - 1:
                    import time
                    time.sleep(1)  # Brief delay before retry

        raise CaptureError(
            f"Failed to capture frame after {self.max_retries} attempts"
        ) from last_error

    def _capture_attempt(
        self,
        save: bool,
        quality: int,
    ) -> Tuple[np.ndarray, FrameMetadata]:
        """Single capture attempt."""
        cap = None
        try:
            cap = self._create_capture()

            # Read frame
            ret, frame = cap.read()

            if not ret or frame is None:
                raise FrameReadError("Failed to read frame from stream")

            timestamp = datetime.now()

            # Create metadata
            metadata = FrameMetadata(
                camera_id=self.camera.id,
                timestamp=timestamp,
                width=frame.shape[1],
                height=frame.shape[0],
            )

            # Save if requested
            if save:
                filepath = self._generate_filename(timestamp)
                encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
                success = cv2.imwrite(str(filepath), frame, encode_params)

                if not success:
                    raise CaptureError(f"Failed to save frame to {filepath}")

                metadata.filepath = filepath
                metadata.file_size_bytes = filepath.stat().st_size

                logger.info(
                    f"Captured {self.camera.id}: {metadata.resolution}, "
                    f"{metadata.file_size_bytes / 1024:.1f}KB"
                )

            return frame, metadata

        finally:
            if cap is not None:
                cap.release()

    def capture_to_memory(self) -> Tuple[np.ndarray, FrameMetadata]:
        """
        Capture frame without saving to disk.

        Returns:
            Tuple of (frame array, metadata)
        """
        return self.capture(save=False)


def capture_single_frame(
    camera_id: str,
    output_dir: Union[str, Path] = "data/images",
    save: bool = True,
) -> Tuple[Optional[np.ndarray], Optional[FrameMetadata]]:
    """
    Capture a single frame from specified camera.

    Args:
        camera_id: Camera identifier
        output_dir: Output directory for saved frames
        save: Whether to save the frame

    Returns:
        Tuple of (frame, metadata) or (None, None) on failure

    Example:
        >>> frame, meta = capture_single_frame("bishkek_panorama")
        >>> if frame is not None:
        ...     print(f"Captured: {meta.resolution}")
    """
    camera = get_camera(camera_id)
    if camera is None:
        logger.error(f"Camera not found: {camera_id}")
        return None, None

    try:
        capture = FrameCapture(camera, output_dir=output_dir)
        return capture.capture(save=save)

    except CaptureError as e:
        logger.error(f"Capture failed for {camera_id}: {e}")
        return None, None


def capture_all_cameras(
    output_dir: Union[str, Path] = "data/images",
    cameras: Optional[Dict[str, Camera]] = None,
) -> Dict[str, Tuple[Optional[np.ndarray], Optional[FrameMetadata]]]:
    """
    Capture frames from all active cameras.

    Args:
        output_dir: Output directory for saved frames
        cameras: Optional dict of cameras (defaults to active cameras)

    Returns:
        Dictionary mapping camera IDs to (frame, metadata) tuples

    Example:
        >>> results = capture_all_cameras()
        >>> for cam_id, (frame, meta) in results.items():
        ...     if meta:
        ...         print(f"{cam_id}: {meta.resolution}")
    """
    if cameras is None:
        cameras = get_active_cameras()

    results = {}
    successful = 0

    logger.info(f"Capturing frames from {len(cameras)} cameras")

    for camera_id, camera in cameras.items():
        try:
            capture = FrameCapture(camera, output_dir=output_dir)
            frame, metadata = capture.capture(save=True)
            results[camera_id] = (frame, metadata)
            successful += 1

        except CaptureError as e:
            logger.error(f"Failed to capture {camera_id}: {e}")
            results[camera_id] = (None, None)

    logger.info(f"Capture complete: {successful}/{len(cameras)} successful")

    return results


def main():
    """Main entry point for frame capture testing."""
    print("=" * 60)
    print("AirVision Frame Capture Test")
    print("=" * 60)

    cameras = get_active_cameras()
    print(f"\nActive cameras: {len(cameras)}")

    for camera_id, camera in cameras.items():
        print(f"\n--- Testing {camera_id} ---")

        try:
            capture = FrameCapture(camera, output_dir="data/test_images")
            frame, metadata = capture.capture()

            print(f"  Status: SUCCESS")
            print(f"  Resolution: {metadata.resolution}")
            print(f"  File: {metadata.filepath}")
            print(f"  Size: {metadata.file_size_bytes / 1024:.1f} KB")

        except CaptureError as e:
            print(f"  Status: FAILED - {e}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
