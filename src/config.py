"""
Configuration management for AirVision project.

Provides a centralized configuration system using YAML files
with support for environment variable overrides.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

import yaml
from dotenv import load_dotenv


class Config:
    """
    Configuration manager for AirVision project.

    Loads configuration from YAML files and supports
    environment variable overrides.

    Example:
        >>> config = Config.load("configs/default.yaml")
        >>> print(config.collection.interval_minutes)
        30
    """

    def __init__(self, config_dict: Dict[str, Any]):
        """
        Initialize configuration from dictionary.

        Args:
            config_dict: Configuration dictionary
        """
        self._config = config_dict
        self._load_env_overrides()

    def _load_env_overrides(self) -> None:
        """Load environment variables and override config values."""
        load_dotenv()

        # Map environment variables to config paths
        env_mappings = {
            "AIRVISION_DATA_DIR": ("collection", "output_dir"),
            "AIRVISION_LOG_LEVEL": ("logging", "level"),
            "AIRVISION_INTERVAL": ("collection", "interval_minutes"),
        }

        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                self._set_nested(config_path, value)

    def _set_nested(self, path: tuple, value: Any) -> None:
        """Set a nested configuration value."""
        current = self._config
        for key in path[:-1]:
            current = current.setdefault(key, {})

        # Type conversion
        original = current.get(path[-1])
        if isinstance(original, int):
            value = int(value)
        elif isinstance(original, float):
            value = float(value)
        elif isinstance(original, bool):
            value = value.lower() in ("true", "1", "yes")

        current[path[-1]] = value

    def __getattr__(self, name: str) -> Any:
        """
        Access configuration values as attributes.

        Args:
            name: Configuration key

        Returns:
            Configuration value or nested Config object
        """
        if name.startswith("_"):
            return super().__getattribute__(name)

        value = self._config.get(name)
        if value is None:
            raise AttributeError(f"Configuration key '{name}' not found")

        if isinstance(value, dict):
            return Config(value)
        return value

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value with optional default.

        Args:
            key: Configuration key (supports dot notation: "model.training.batch_size")
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default

        return value

    def to_dict(self) -> Dict[str, Any]:
        """Return configuration as dictionary."""
        return self._config.copy()

    @classmethod
    def load(cls, config_path: Union[str, Path]) -> "Config":
        """
        Load configuration from YAML file.

        Args:
            config_path: Path to YAML configuration file

        Returns:
            Config instance

        Raises:
            FileNotFoundError: If config file doesn't exist
        """
        config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            config_dict = yaml.safe_load(f)

        return cls(config_dict)

    @classmethod
    def get_default(cls) -> "Config":
        """
        Load default configuration.

        Returns:
            Config instance with default settings
        """
        project_root = Path(__file__).parent.parent
        default_path = project_root / "configs" / "default.yaml"
        return cls.load(default_path)


# Global configuration instance
_config: Optional[Config] = None


def get_config(config_path: Optional[Union[str, Path]] = None) -> Config:
    """
    Get configuration instance (singleton pattern).

    Args:
        config_path: Optional path to configuration file.
                     If None, loads default configuration.

    Returns:
        Configuration instance
    """
    global _config

    if _config is None or config_path is not None:
        if config_path is not None:
            _config = Config.load(config_path)
        else:
            _config = Config.get_default()

    return _config
