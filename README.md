# Image-Based PM2.5 Estimation for Bishkek Using Urban Webcams

Research project for estimating air pollution (PM2.5) levels in Bishkek, Kyrgyzstan using computer vision and multimodal machine learning.

**Target:** Scopus Q4 publication in Environmental Monitoring / Computer Vision / Machine Learning

---

## Overview

This project develops a low-cost air quality monitoring system using publicly available urban webcams. By analyzing atmospheric visibility (haze, contrast, depth perception) combined with meteorological data, we estimate PM2.5 concentration levels without expensive sensor networks.

### Key Innovation

Unlike traditional approaches requiring proximity between camera and sensor, we leverage the physical principle that **atmospheric visibility integrates PM2.5 along the entire line of sight (5-10 km)**. During winter thermal inversion in Bishkek, PM2.5 is spatially homogeneous at city scale, enabling panoramic cameras to effectively measure city-average pollution regardless of sensor distance.

### Scientific Contribution

- Low-cost PM2.5 monitoring for resource-constrained cities
- Multimodal deep learning (visual + meteorological features)
- Physical understanding of visibility-PM2.5 relationship
- First application for Central Asian urban environment
- Comparative analysis: baseline vs image-only vs multimodal models

---

## Installation

### Prerequisites

- Python 3.8+
- pip package manager
- Git

### Setup

```bash
# Clone repository
git clone https://github.com/raimbekovm/research_paper_cv.git
cd research_paper_cv

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### API Keys Setup

Get free API keys for PM2.5 data:

1. **OpenWeatherMap** (recommended, 1000 calls/day)
   - Register: https://openweathermap.org/api
   - Get API key from dashboard

2. **IQAir** (backup, 1000 calls/month)
   - Register: https://www.iqair.com/air-pollution-data-api
   - Choose Community Edition (free)

3. Create `.env` file:
```bash
cp .env.example .env
nano .env  # Add your API keys
```

See detailed instructions: `docs/API_KEYS_GUIDE.md`

---

## Project Structure

```
research_paper_cv/
├── src/                          # Source code
│   ├── camera_config.py          # Camera configurations (3 recommended)
│   ├── capture_frame.py          # Single camera frame capture
│   ├── collect_data.py           # Multi-camera data collection
│   ├── fetch_pm25_data.py        # PM2.5 and weather data (IQAir, OpenWeatherMap)
│   ├── frame_quality.py          # Quality filtering for rotating camera
│   ├── find_sensors.py           # PM2.5 sensor locations and distances
│   ├── check_feasibility.py      # Project feasibility analysis
│   └── baseline_model.py         # Baseline ML model (weather → PM2.5)
├── data/                         # Data directory (gitignored)
│   ├── images/                   # Captured frames (organized by camera)
│   ├── pm25/                     # PM2.5 measurements (JSON)
│   ├── weather/                  # Weather data
│   ├── metadata/                 # Collection metadata
│   └── sensor_locations.json     # PM2.5 sensor coordinates and analysis
├── docs/                         # Documentation
│   ├── camera_locations.txt      # Camera coordinates and specifications
│   ├── camera_specifications.md  # Detailed camera characteristics
│   ├── API_KEYS_GUIDE.md         # Step-by-step API setup guide
│   ├── PHYSICS_VISIBILITY_PM25.md # Physical basis of visibility-PM2.5 relation
│   └── CRITICAL_FINDINGS_2025-12-27_CORRECTED.md # Camera selection analysis
├── .env.example                  # API keys template
├── requirements.txt              # Python dependencies
├── PROJECT_INFO.md               # Internal project documentation (not in git)
└── README.md                     # This file
```

---

## Webcam Cameras

We use **3 recommended webcams** selected by visual quality criteria rather than sensor proximity.

### Selection Criteria

1. **Panoramic field of view** - captures city-scale atmospheric haze
2. **Depth of field** - distant objects visible at 5-10 km
3. **Sky visibility** - >30% of frame for atmospheric transparency assessment
4. **Minimal foreground obstruction**

### Recommended Cameras

| Camera | Visual Quality | Depth | Sky | Sensor Distance | Status |
|--------|---------------|-------|-----|-----------------|--------|
| **bishkek_panorama** | 10/10 | 10+ km | 50% | 7.24 km | Primary |
| **sovmin** | 9/10 | 5+ km | 40% | 5.07 km | Secondary |
| **kt_center** | 7/10 | varies | 30% | 0.01 km | Supplementary |

**Primary Camera** - Bishkek Panorama
- Coordinates: 42.799197°N, 74.645485°E
- Resolution: 1920×1080
- Viewing direction: ~330° NW
- Ideal panoramic view of entire city with excellent atmospheric haze visibility

**Secondary Camera** - Sovmin
- Coordinates: 42.804394°N, 74.587977°E
- Resolution: 1920×1080
- Viewing direction: ~45° NE
- Panoramic view of southern residential district

**Supplementary Camera** - KT Center (rotating)
- Coordinates: 42.874689°N, 74.612241°E
- Resolution: 1920×1080
- Auto quality filtering (~75% frames accepted)
- Closest to PM2.5 sensor (10 meters)

**Source:** [Kyrgyztelekom Live Streams](https://online.kt.kg)

**Rationale:** See `docs/PHYSICS_VISIBILITY_PM25.md` for detailed physical justification of camera selection approach.

---

## Usage

### 1. Test Data Collection

Test PM2.5 data fetch (requires API keys in `.env`):

```bash
python src/fetch_pm25_data.py
```

Expected output:
```
PM2.5: 39.9 µg/m³ (AQI: 112)
Temperature: 1°C
Humidity: 79%
```

### 2. Test Camera Capture

Capture single frame from all recommended cameras:

```bash
python src/collect_data.py --cameras bishkek_panorama sovmin kt_center --duration 0.1
```

### 3. Start Continuous Collection

Collect data every hour during daylight (8:00-18:00):

```bash
python src/collect_data.py \
    --cameras bishkek_panorama sovmin kt_center \
    --daylight-start 8 \
    --daylight-end 18 \
    --interval 60 \
    --duration 4320  # 180 days (~6 months)
```

**Important:**
- Collection runs only during daylight (visual haze features invisible at night)
- Target: 1500 frames/camera over 5 months = 4500 total frames
- Include winter season (high PM2.5, thermal inversion critical for model)

### 4. Check Project Feasibility

```bash
python src/check_feasibility.py
```

Analyzes:
- Camera-sensor distances and spatial correlation
- Required dataset size estimates
- ML infrastructure readiness

### 5. Find PM2.5 Sensors

```bash
python src/find_sensors.py
```

Locates PM2.5 sensors in Bishkek and calculates distances to cameras.

---

## Data Collection Strategy

### Timeline

- **Phase 1 (5 months):** Continuous data collection (target: 4500 images + synchronized PM2.5)
- **Phase 2 (1 month):** Dataset preparation, filtering, train/val/test split
- **Phase 3 (1-2 months):** Model training (baseline, image-only, multimodal)
- **Phase 4 (2 months):** Analysis, ablation studies, paper writing

### Dataset Targets

| Tier | Frames/Camera | Total Frames | Collection Time | Viability |
|------|---------------|--------------|-----------------|-----------|
| Minimum | 500 | 1500 | 50 days | Marginal |
| **Recommended** | **1500** | **4500** | **150 days (5 months)** | **Good** |
| Ideal | 3000 | 9000 | 300 days (10 months) | Excellent |

**Critical:** Must include winter season (December-February) for high PM2.5 episodes and thermal inversion conditions.

### Data Synchronization

- Images: captured hourly during daylight
- PM2.5: synchronized within ±10 minutes of image timestamp
- Weather: temperature, humidity, wind speed, pressure, visibility
- Metadata: camera ID, coordinates, viewing direction, timestamp

---

## Methodology

### Model Architecture

1. **Baseline Model:** Weather features only → PM2.5
   - Features: temperature, humidity, wind speed, hour, day of year, is_winter
   - Model: Ridge regression / Random Forest
   - Purpose: Establish lower bound performance

2. **Image-Only Model:** CNN → PM2.5
   - Architecture: ResNet-18 or EfficientNet-B0 (ImageNet pretrained)
   - Transfer learning (freeze early layers)
   - Purpose: Evaluate visual features alone

3. **Multimodal Model:** CNN + Weather → PM2.5
   - Visual features from pretrained CNN
   - Weather features from MLP
   - Late fusion: concatenate → regression head
   - Purpose: Best performance combining both modalities

### Evaluation Metrics

- **MAE** (Mean Absolute Error) - primary metric
- **RMSE** (Root Mean Squared Error)
- **R²** (coefficient of determination)

### Experiments

- Baseline vs Image-only vs Multimodal comparison
- Ablation study: which features contribute most?
- Seasonal analysis: winter (high PM2.5) vs summer (low PM2.5)
- Cross-camera validation: generalization across camera viewpoints
- Interpretability: Grad-CAM visualization of visual features

---

## Physical Basis

### Why Distance to Sensor Doesn't Matter for Panoramic Cameras

Traditional assumption: camera and PM2.5 sensor must be co-located (< 100m).

**Our approach:** Visual quality > sensor proximity

**Physical justification:**
1. Atmospheric visibility follows Beer-Lambert law: I(d) = I₀ · exp(-β·d)
2. Extinction coefficient β ∝ PM2.5 concentration
3. Camera measures **integrated scattering** along entire line of sight (5-10 km)
4. Winter thermal inversion in Bishkek creates **city-scale PM2.5 homogeneity** (correlation r > 0.8 at < 10 km)
5. Sensor at any city location represents city-average PM2.5

**Therefore:** Panoramic camera 7 km from sensor can correlate better than narrow-view camera 70 m from sensor, if visual quality superior.

See detailed analysis: `docs/PHYSICS_VISIBILITY_PM25.md`

---

## Current Status

### Completed ✓

- [x] Camera configuration and testing (5 cameras identified, 3 recommended)
- [x] Visual quality analysis and camera selection criteria
- [x] Automated frame capture system with daylight filtering
- [x] Frame quality filtering for rotating camera (~75% acceptance rate)
- [x] PM2.5 sensor location discovery (4 sensors in Bishkek)
- [x] Camera-sensor distance analysis and feasibility check
- [x] PM2.5 data collection implementation (IQAir, OpenWeatherMap APIs)
- [x] API keys obtained and configured
- [x] Physical justification documented (visibility-PM2.5 relationship)
- [x] Baseline model skeleton
- [x] Project feasibility confirmed (3 cameras, 4500 frames target)

### In Progress ⏳

- [ ] OpenWeatherMap API key activation (2-3 hours wait)
- [ ] Full system integration test

### Pending ⏹

- [ ] Continuous data collection (5 months, including winter 2025-2026)
- [ ] Dataset preparation and preprocessing
- [ ] Model training (baseline, image-only, multimodal)
- [ ] Ablation studies and interpretability analysis
- [ ] Paper writing for Scopus Q4 submission

---

## API Rate Limits

| API | Free Tier Limit | Our Usage | Status |
|-----|-----------------|-----------|--------|
| **OpenWeatherMap** | 1000 calls/day | ~30 calls/day (3 cameras × 10 hours) | ✓ Sufficient |
| **IQAir** | 1000 calls/month | ~900 calls/month (3 cameras × 10 hrs × 30 days) | ⚠ Tight but OK |
| OpenAQ | Deprecated (410) | Not used | - |

**Strategy:** Use OpenWeatherMap as primary (better limits), IQAir as backup.

---

## Limitations and Considerations

### Spatial Assumptions

- Approach assumes city-scale PM2.5 homogeneity during winter thermal inversion
- Valid for winter high-pollution episodes (model's primary use case)
- May not hold during summer (strong vertical mixing) or localized sources (traffic, industrial)
- Seasonal performance variation expected

### Data Quality

- Visual haze affected by both PM2.5 and meteorological humidity
- Baseline weather-only model helps isolate PM2.5 contribution
- Nighttime images excluded (no visual features)
- Rotating camera requires quality filtering

### Dataset Size

- 4500 frames modest for deep learning
- Mitigated by transfer learning (ImageNet pretrained models)
- Sufficient for Scopus Q4 publication with proper methodology

---

## Future Work

- Validate spatial correlation assumption using multiple PM2.5 sensors
- Quantify seasonal dependence of visibility-PM2.5 relationship
- Real-time PM2.5 estimation dashboard
- Expansion to other Central Asian cities
- Mobile application for public access
- Long-term monitoring system

---

## Contributing

This is an academic research project. Contributions, suggestions, and feedback welcome via issues or pull requests.

---

## License

MIT License (tentative - to be finalized)

---

## Citation

```bibtex
@article{raimbekov2026pm25bishkek,
  title={Image-Based PM2.5 Estimation for Bishkek Using Urban Webcams and Multimodal Deep Learning},
  author={Raimbekov, M.},
  journal={TBD - Scopus Q4 Environmental/CV journal},
  year={2026}
}
```

---

## Contact

**Author:** Murat Raimbekov
**Email:** raimbekov_m@auca.kg
**Institution:** American University of Central Asia
**GitHub:** https://github.com/raimbekovm/research_paper_cv

---

## Acknowledgments

- **Kyrgyztelekom** for public webcam infrastructure
- **OpenAQ, IQAir, OpenWeatherMap** for open air quality data APIs
- **AUCA** for research support
- Community contributors and reviewers

---

**Last Updated:** December 27, 2025
**Project Status:** Data collection preparation complete, ready to start 5-month collection phase
