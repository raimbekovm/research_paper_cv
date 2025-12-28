"""Tests for utility modules."""

import json
import logging
from pathlib import Path

import pytest

from src.utils.io import ensure_dir, load_json, save_json
from src.utils.logging import get_logger, setup_logger


class TestIOUtils:
    """Test cases for I/O utilities."""

    def test_ensure_dir_creates_directory(self, temp_dir: Path):
        """Test that ensure_dir creates a new directory."""
        new_dir = temp_dir / "new_directory"
        assert not new_dir.exists()

        result = ensure_dir(new_dir)

        assert new_dir.exists()
        assert result == new_dir

    def test_ensure_dir_existing_directory(self, temp_dir: Path):
        """Test that ensure_dir handles existing directories."""
        result = ensure_dir(temp_dir)
        assert result == temp_dir

    def test_ensure_dir_nested(self, temp_dir: Path):
        """Test creating nested directories."""
        nested_dir = temp_dir / "level1" / "level2" / "level3"
        result = ensure_dir(nested_dir)

        assert nested_dir.exists()
        assert result == nested_dir

    def test_save_json(self, temp_dir: Path):
        """Test saving data to JSON file."""
        data = {"key": "value", "number": 42, "list": [1, 2, 3]}
        file_path = temp_dir / "test.json"

        save_json(data, file_path)

        assert file_path.exists()
        with open(file_path) as f:
            loaded = json.load(f)
        assert loaded == data

    def test_save_json_creates_parent_dirs(self, temp_dir: Path):
        """Test that save_json creates parent directories."""
        data = {"test": "data"}
        file_path = temp_dir / "subdir" / "test.json"

        save_json(data, file_path)

        assert file_path.exists()

    def test_load_json(self, temp_dir: Path):
        """Test loading data from JSON file."""
        data = {"key": "value"}
        file_path = temp_dir / "test.json"

        with open(file_path, "w") as f:
            json.dump(data, f)

        loaded = load_json(file_path)
        assert loaded == data

    def test_load_json_file_not_found(self):
        """Test error when loading non-existent file."""
        with pytest.raises(FileNotFoundError):
            load_json("/nonexistent/file.json")


class TestLoggingUtils:
    """Test cases for logging utilities."""

    def test_setup_logger(self):
        """Test logger setup."""
        logger = setup_logger("test_logger", level=logging.DEBUG)

        assert logger.name == "test_logger"
        assert logger.level == logging.DEBUG
        assert len(logger.handlers) > 0

    def test_setup_logger_with_file(self, temp_dir: Path):
        """Test logger setup with file handler."""
        log_file = temp_dir / "test.log"
        logger = setup_logger("file_logger", log_file=log_file)

        logger.info("Test message")

        assert log_file.exists()
        content = log_file.read_text()
        assert "Test message" in content

    def test_get_logger(self):
        """Test getting logger instance."""
        logger1 = get_logger("my_logger")
        logger2 = get_logger("my_logger")

        assert logger1 is logger2  # Same instance

    def test_logger_format(self, temp_dir: Path):
        """Test custom log format."""
        log_file = temp_dir / "format_test.log"
        custom_format = "%(levelname)s - %(message)s"
        logger = setup_logger(
            "format_logger",
            log_file=log_file,
            format_string=custom_format
        )

        logger.warning("Format test")

        content = log_file.read_text()
        assert "WARNING - Format test" in content
