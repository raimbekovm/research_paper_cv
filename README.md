<h1 align="center">
  <br>
  AirVision
  <br>
</h1>

<h4 align="center">Image-Based PM2.5 Estimation Using Urban Webcams</h4>

<p align="center">
  <a href="https://github.com/raimbekovm/airvision/actions/workflows/ci.yml">
    <img src="https://github.com/raimbekovm/airvision/actions/workflows/ci.yml/badge.svg" alt="CI">
  </a>
  <a href="https://www.python.org/downloads/">
    <img src="https://img.shields.io/badge/python-3.8%2B-blue.svg" alt="Python 3.8+">
  </a>
  <a href="https://opensource.org/licenses/MIT">
    <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License: MIT">
  </a>
  <a href="https://github.com/psf/black">
    <img src="https://img.shields.io/badge/code%20style-black-000000.svg" alt="Code style: black">
  </a>
</p>

<p align="center">
  <a href="#key-features">Key Features</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#usage">Usage</a> •
  <a href="#methodology">Methodology</a> •
  <a href="#contributing">Contributing</a>
</p>

---

## Overview

**AirVision** is a research project for estimating air pollution (PM2.5) levels in Bishkek, Kyrgyzstan using computer vision and multimodal machine learning. We develop a low-cost air quality monitoring system using publicly available urban webcams.

**Target:** Scopus Q4 publication in Environmental Monitoring / Computer Vision / Machine Learning

### Key Innovation

Unlike traditional approaches requiring proximity between camera and sensor, we leverage the physical principle that **atmospheric visibility integrates PM2.5 along the entire line of sight (5-10 km)**. During winter thermal inversion in Bishkek, PM2.5 is spatially homogeneous at city scale, enabling panoramic cameras to effectively measure city-average pollution regardless of sensor distance.

---

## Key Features

- **Low-cost monitoring** — Uses existing public webcam infrastructure
- **Multimodal ML** — Combines visual features with meteorological data
- **Physics-based approach** — Grounded in atmospheric visibility theory
- **Automated collection** — Continuous data pipeline with quality filtering
- **Extensible** — Easy to add new cameras and data sources

---

## Quick Start

```bash
# Clone and setup
git clone https://github.com/raimbekovm/airvision.git
cd airvision

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
make install-dev

# Configure API keys
cp .env.example .env
# Edit .env with your API keys (see docs/API_KEYS_GUIDE.md)

# Test single capture
python src/capture_frame.py

# Start data collection
make collect
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         AirVision Pipeline                          │
└─────────────────────────────────────────────────────────────────────┘
                                   │
          ┌────────────────────────┼────────────────────────┐
          ▼                        ▼                        ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│   Data Sources   │    │   Data Sources   │    │   Data Sources   │
│    (Webcams)     │    │    (PM2.5 API)   │    │   (Weather API)  │
│                  │    │                  │    │                  │
│ • bishkek_pano   │    │ • IQAir          │    │ • OpenWeatherMap │
│ • sovmin         │    │ • OpenAQ         │    │ • Open-Meteo     │
│ • kt_center      │    │                  │    │                  │
└────────┬─────────┘    └────────┬─────────┘    └────────┬─────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Data Collection Layer                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │   Frame     │  │   Quality   │  │    PM2.5    │  │   Weather   │ │
│  │  Capture    │  │  Filtering  │  │   Fetcher   │  │   Fetcher   │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Dataset (Synchronized)                       │
│                                                                      │
│   ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐         │
│   │  Image  │ +  │  PM2.5  │ +  │ Weather │ +  │Metadata │         │
│   │ (1080p) │    │ (µg/m³) │    │  (T,H,W)│    │  (time) │         │
│   └─────────┘    └─────────┘    └─────────┘    └─────────┘         │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           Model Training                             │
│                                                                      │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐           │
│  │   Baseline    │  │  Image-Only   │  │  Multimodal   │           │
│  │  (Weather →   │  │  (CNN →       │  │  (CNN+MLP →   │           │
│  │    PM2.5)     │  │    PM2.5)     │  │    PM2.5)     │           │
│  └───────────────┘  └───────────────┘  └───────────────┘           │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
                        ┌──────────────────┐
                        │   PM2.5 Estimate │
                        │   + Uncertainty  │
                        └──────────────────┘
```

---

## Project Structure

```
airvision/
├── src/                          # Source code
│   ├── __init__.py               # Package initialization
│   ├── config.py                 # Configuration management
│   ├── camera_config.py          # Camera configurations
│   ├── capture_frame.py          # Frame capture
│   ├── collect_data.py           # Data collection pipeline
│   ├── frame_quality.py          # Quality assessment
│   ├── fetch_pm25_data.py        # PM2.5 data fetching
│   ├── baseline_model.py         # ML baseline models
│   └── utils/                    # Utility functions
│       ├── logging.py
│       └── io.py
├── configs/                      # Configuration files
│   └── default.yaml
├── data/                         # Data directory (gitignored)
│   ├── images/                   # Captured frames
│   ├── pm25/                     # PM2.5 measurements
│   ├── weather/                  # Weather data
│   └── metadata/                 # Collection metadata
├── tests/                        # Test suite
│   ├── conftest.py
│   ├── test_config.py
│   ├── test_frame_quality.py
│   └── test_utils.py
├── docs/                         # Documentation
├── .github/workflows/            # CI/CD
├── Makefile                      # Common commands
├── pyproject.toml                # Project configuration
├── requirements.txt              # Dependencies
└── README.md
```

---

## Webcam Cameras

We use **3 webcams** selected by visual quality criteria:

| Camera | Quality | Depth | Sky Coverage | Status |
|--------|---------|-------|--------------|--------|
| **bishkek_panorama** | 10/10 | 10+ km | 50% | Primary |
| **sovmin** | 9/10 | 5+ km | 40% | Secondary |
| **kt_center** | 7/10 | varies | 30% | Supplementary |

**Source:** [Kyrgyztelekom Live Streams](https://online.kt.kg)

---

## Usage

### Data Collection

```bash
# Start daylight collection (8:00-18:00)
make collect

# Start 24/7 collection
make collect-24h

# Background collection with logging
make collect-background

# Check collection status
make status

# Stop collection
make stop
```

### Development

```bash
# Run tests
make test

# Run tests with coverage
make coverage

# Format code
make format

# Lint code
make lint
```

---

## Methodology

### Model Comparison

| Model | Input | Architecture | Purpose |
|-------|-------|--------------|---------|
| **Baseline** | Weather only | Ridge/RF | Lower bound |
| **Image-Only** | Webcam frames | ResNet-50 | Visual features |
| **Multimodal** | Image + Weather | CNN + MLP | Best performance |

### Evaluation Metrics

- **MAE** — Mean Absolute Error (primary)
- **RMSE** — Root Mean Squared Error
- **R²** — Coefficient of determination

### Physical Basis

Atmospheric visibility follows the Beer-Lambert law:

```
I(d) = I₀ · exp(-β·d)
```

Where extinction coefficient β ∝ PM2.5 concentration. The camera measures **integrated scattering** along the entire line of sight (5-10 km), enabling city-scale pollution estimation.

---

## Configuration

Configuration is managed via YAML files in `configs/`:

```yaml
# configs/default.yaml
collection:
  interval_minutes: 30
  duration_hours: 12
  daylight_only: true

model:
  architecture: "resnet50"
  pretrained: true
  training:
    batch_size: 32
    learning_rate: 0.001
```

Override settings via environment variables:
```bash
export AIRVISION_INTERVAL=15
export AIRVISION_LOG_LEVEL=DEBUG
```

---

## Current Status

### Completed ✓

- [x] Camera configuration (3 cameras)
- [x] Automated frame capture with quality filtering
- [x] PM2.5 data collection (IQAir, OpenWeatherMap APIs)
- [x] Physical justification documented
- [x] Project structure and CI/CD setup

### In Progress ⏳

- [ ] Continuous data collection (winter 2025-2026)

### Pending ⏹

- [ ] Model training (baseline, image-only, multimodal)
- [ ] Ablation studies and interpretability
- [ ] Paper writing for Scopus Q4 submission

---

## API Rate Limits

| API | Free Tier | Our Usage | Status |
|-----|-----------|-----------|--------|
| **OpenWeatherMap** | 1000/day | ~30/day | ✓ OK |
| **IQAir** | 1000/month | ~900/month | ⚠ Tight |

---

## Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
# Setup development environment
make install-dev

# Run pre-commit hooks
pre-commit run --all-files
```

---

## Citation

```bibtex
@article{raimbekov2026airvision,
  title={Image-Based PM2.5 Estimation for Bishkek Using Urban Webcams
         and Multimodal Deep Learning},
  author={Raimbekov, Murat},
  journal={TBD - Scopus Q4},
  year={2026}
}
```

---

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.

---

## Contact

**Murat Raimbekov**

- Email: raimbekov_m@auca.kg
- GitHub: [@raimbekovm](https://github.com/raimbekovm)
- Institution: American University of Central Asia

---

## Acknowledgments

- **Kyrgyztelekom** — Public webcam infrastructure
- **IQAir, OpenWeatherMap** — Air quality and weather APIs
- **AUCA** — Research support

---

<p align="center">
  <i>Last updated: December 28, 2025</i>
</p>
