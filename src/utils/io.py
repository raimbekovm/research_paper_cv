"""I/O utilities for AirVision project."""

import json
from pathlib import Path
from typing import Any, Dict, List, Union


def ensure_dir(path: Union[str, Path]) -> Path:
    """
    Ensure directory exists, create if it doesn't.

    Args:
        path: Directory path

    Returns:
        Path object of the directory
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_json(data: Union[Dict, List], path: Union[str, Path], indent: int = 2) -> None:
    """
    Save data to JSON file.

    Args:
        data: Data to save
        path: Output file path
        indent: JSON indentation level
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)


def load_json(path: Union[str, Path]) -> Union[Dict, List]:
    """
    Load data from JSON file.

    Args:
        path: Input file path

    Returns:
        Loaded data

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    path = Path(path)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
