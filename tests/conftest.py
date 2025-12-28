"""
Pytest configuration and fixtures for AirVision tests.
"""

import os
import tempfile
from pathlib import Path
from typing import Generator

import numpy as np
import pytest


@pytest.fixture
def sample_image() -> np.ndarray:
    """Create a sample test image."""
    # Create a 1080p RGB image with some variation
    image = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
    return image


@pytest.fixture
def sample_frame_bright() -> np.ndarray:
    """Create a bright test frame (simulating daytime)."""
    image = np.ones((1080, 1920, 3), dtype=np.uint8) * 180
    # Add some variation
    image[:540, :, :] = 200  # Brighter sky area
    return image


@pytest.fixture
def sample_frame_dark() -> np.ndarray:
    """Create a dark test frame (simulating nighttime)."""
    image = np.ones((1080, 1920, 3), dtype=np.uint8) * 30
    return image


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_camera_config() -> dict:
    """Create a mock camera configuration."""
    return {
        "name": "Test Camera",
        "url": "http://example.com/stream",
        "location": {"lat": 42.87, "lon": 74.59},
        "direction": "north",
        "active": True,
    }


@pytest.fixture
def sample_pm25_data() -> dict:
    """Create sample PM2.5 data."""
    return {
        "timestamp": "2024-12-28T12:00:00",
        "pm25": 85.5,
        "source": "test_sensor",
        "location": {"lat": 42.87, "lon": 74.59},
    }


@pytest.fixture
def sample_weather_data() -> dict:
    """Create sample weather data."""
    return {
        "timestamp": "2024-12-28T12:00:00",
        "temperature": -5.0,
        "humidity": 75,
        "pressure": 1020,
        "wind_speed": 2.5,
        "visibility": 5000,
    }


@pytest.fixture(autouse=True)
def set_test_env():
    """Set environment variables for testing."""
    os.environ["AIRVISION_TEST_MODE"] = "1"
    yield
    os.environ.pop("AIRVISION_TEST_MODE", None)
