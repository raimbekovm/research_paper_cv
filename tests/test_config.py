"""Tests for configuration module."""

import tempfile
from pathlib import Path

import pytest
import yaml

from src.config import Config, get_config


class TestConfig:
    """Test cases for Config class."""

    def test_load_config_from_file(self, temp_dir: Path):
        """Test loading configuration from YAML file."""
        config_data = {
            "project": {"name": "test", "version": "1.0.0"},
            "collection": {"interval_minutes": 15},
        }

        config_path = temp_dir / "test_config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        config = Config.load(config_path)

        assert config.project.name == "test"
        assert config.project.version == "1.0.0"
        assert config.collection.interval_minutes == 15

    def test_config_file_not_found(self):
        """Test error when config file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            Config.load("/nonexistent/path/config.yaml")

    def test_config_get_method(self, temp_dir: Path):
        """Test get method with dot notation."""
        config_data = {
            "model": {
                "training": {"batch_size": 32, "learning_rate": 0.001}
            }
        }

        config_path = temp_dir / "test_config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        config = Config.load(config_path)

        assert config.get("model.training.batch_size") == 32
        assert config.get("model.training.learning_rate") == 0.001
        assert config.get("nonexistent.key", "default") == "default"

    def test_config_to_dict(self, temp_dir: Path):
        """Test conversion to dictionary."""
        config_data = {"key1": "value1", "key2": {"nested": "value2"}}

        config_path = temp_dir / "test_config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        config = Config.load(config_path)
        result = config.to_dict()

        assert result == config_data

    def test_config_attribute_error(self, temp_dir: Path):
        """Test AttributeError for missing keys."""
        config_data = {"existing_key": "value"}

        config_path = temp_dir / "test_config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        config = Config.load(config_path)

        with pytest.raises(AttributeError):
            _ = config.nonexistent_key
