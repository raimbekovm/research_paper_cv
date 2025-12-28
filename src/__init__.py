"""
AirVision: Image-Based PM2.5 Estimation System

A computer vision framework for estimating air pollution (PM2.5) levels
using urban webcam imagery and multimodal machine learning.

Modules:
    - capture_frame: Frame capture from webcam streams
    - camera_config: Camera configuration and management
    - frame_quality: Image quality assessment and filtering
    - fetch_pm25_data: PM2.5 data collection from sensors
    - collect_data: Automated data collection pipeline
    - baseline_model: ML baseline models for PM2.5 estimation
"""

__version__ = "0.1.0"
__author__ = "Murat Raimbekov"
__email__ = "raimbekovm@example.com"

from .camera_config import CAMERAS, get_active_cameras
from .capture_frame import capture_single_frame, capture_all_cameras
from .frame_quality import assess_frame_quality, filter_low_quality_frames

__all__ = [
    "CAMERAS",
    "get_active_cameras",
    "capture_single_frame",
    "capture_all_cameras",
    "assess_frame_quality",
    "filter_low_quality_frames",
]
