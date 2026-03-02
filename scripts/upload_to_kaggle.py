#!/usr/bin/env python3
"""
Upload AirVision dataset to Kaggle.

This script packages images and metadata for PM2.5 estimation
and uploads them to Kaggle as a dataset.

Usage:
    python scripts/upload_to_kaggle.py --create    # First time
    python scripts/upload_to_kaggle.py --update    # Update existing
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from datetime import datetime


# Configuration
DATASET_SLUG = "muraraimbekov/bishkek-pm25-webcam"
DATASET_TITLE = "Bishkek PM2.5 Webcam Dataset"
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "images"
UPLOAD_DIR = PROJECT_ROOT / "kaggle_upload"


def count_files():
    """Count images and metadata files."""
    cameras = ["bishkek_panorama", "sovmin"]
    counts = {}

    for cam in cameras:
        cam_dir = DATA_DIR / cam
        if cam_dir.exists():
            counts[cam] = len(list(cam_dir.glob("*.jpg")))
        else:
            counts[cam] = 0

    metadata_dir = DATA_DIR / "metadata"
    counts["metadata"] = len(list(metadata_dir.glob("*.json"))) if metadata_dir.exists() else 0

    return counts


def prepare_dataset():
    """Prepare dataset directory for upload using symlinks to save disk space."""
    print("Preparing dataset for upload...")

    # Clean and create upload directory
    if UPLOAD_DIR.exists():
        shutil.rmtree(UPLOAD_DIR)
    UPLOAD_DIR.mkdir(parents=True)

    cameras = ["bishkek_panorama", "sovmin"]
    total_images = 0

    # Symlink image directories (saves ~4GB disk space)
    for cam in cameras:
        src_dir = DATA_DIR / cam
        link_path = UPLOAD_DIR / cam

        if src_dir.exists():
            images = list(src_dir.glob("*.jpg"))
            print(f"  Linking {len(images)} images from {cam}...")
            os.symlink(src_dir.resolve(), link_path)
            total_images += len(images)

    # Symlink metadata
    metadata_src = DATA_DIR / "metadata"
    metadata_link = UPLOAD_DIR / "metadata"

    if metadata_src.exists():
        metadata_files = list(metadata_src.glob("*.json"))
        print(f"  Linking {len(metadata_files)} metadata files...")
        os.symlink(metadata_src.resolve(), metadata_link)

    # Create dataset info
    info = {
        "created": datetime.now().isoformat(),
        "cameras": cameras,
        "total_images": total_images,
        "total_collections": len(metadata_files) if metadata_src.exists() else 0,
        "image_resolution": "1920x1080",
        "data_sources": {
            "pm25": "IQAir (7 stations)",
            "weather": "Open-Meteo"
        }
    }

    with open(UPLOAD_DIR / "dataset_info.json", "w") as f:
        json.dump(info, f, indent=2)

    print(f"\nTotal: {total_images} images prepared")
    return total_images


def create_kaggle_metadata():
    """Create Kaggle dataset metadata file."""
    metadata = {
        "title": DATASET_TITLE,
        "id": DATASET_SLUG,
        "licenses": [{"name": "CC0-1.0"}]
    }

    metadata_path = UPLOAD_DIR / "dataset-metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"Created {metadata_path}")
    return metadata_path


def upload_to_kaggle(create_new: bool = False):
    """Upload dataset to Kaggle."""
    if create_new:
        cmd = ["kaggle", "datasets", "create", "-p", str(UPLOAD_DIR), "--dir-mode", "zip"]
        print("\nCreating new dataset on Kaggle...")
    else:
        cmd = ["kaggle", "datasets", "version", "-p", str(UPLOAD_DIR),
               "-m", f"Update {datetime.now().strftime('%Y-%m-%d %H:%M')}", "--dir-mode", "zip"]
        print("\nUpdating dataset on Kaggle...")

    print(f"Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout)
        if result.returncode != 0:
            print(f"Error: {result.stderr}")
            return False
        return True
    except FileNotFoundError:
        print("Error: kaggle CLI not found. Install with: pip install kaggle")
        return False


def main():
    parser = argparse.ArgumentParser(description="Upload dataset to Kaggle")
    parser.add_argument("--create", action="store_true", help="Create new dataset")
    parser.add_argument("--update", action="store_true", help="Update existing dataset")
    parser.add_argument("--prepare-only", action="store_true", help="Only prepare, don't upload")
    args = parser.parse_args()

    if not args.create and not args.update and not args.prepare_only:
        parser.print_help()
        print("\nCurrent data stats:")
        counts = count_files()
        for name, count in counts.items():
            print(f"  {name}: {count}")
        return

    # Prepare dataset
    prepare_dataset()
    create_kaggle_metadata()

    if args.prepare_only:
        print(f"\nDataset prepared in: {UPLOAD_DIR}")
        print("Run with --create or --update to upload")
        return

    # Upload
    success = upload_to_kaggle(create_new=args.create)

    if success:
        print(f"\nDataset URL: https://www.kaggle.com/datasets/{DATASET_SLUG}")
    else:
        print("\nUpload failed. Check errors above.")


if __name__ == "__main__":
    main()
