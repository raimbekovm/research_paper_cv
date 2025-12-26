# Image-Based PM2.5 Estimation for Bishkek Using Urban Webcams

Research project for estimating air pollution (PM2.5) levels in Bishkek, Kyrgyzstan using computer vision and multimodal machine learning.

## Project Overview

This project aims to develop a low-cost air quality monitoring system using publicly available urban webcams. By analyzing visual features (haze, contrast, visibility) combined with meteorological data, we estimate PM2.5 concentration levels without expensive sensors.

### Key Features

- Automated frame capture from 4 public webcams in Bishkek
- PM2.5 and weather data collection from multiple APIs
- Multimodal ML approach (CNN for images + MLP for weather data)
- Regression model for PM2.5 prediction
- Designed for Scopus Q4 publication

### Target Journal

Scopus Q4 journal in Computer Vision / Machine Learning / Environmental Monitoring

## Installation

### Prerequisites

- Python 3.8+
- OpenCV
- PyTorch

### Setup

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/research_paper_cv.git
cd research_paper_cv

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Project Structure

```
research_paper_cv/
├── src/                          # Source code
│   ├── camera_config.py          # Camera configurations
│   ├── capture_frame.py          # Single camera frame capture
│   ├── collect_data.py           # Multi-camera data collection
│   └── fetch_pm25_data.py        # PM2.5 and weather data fetching
├── data/                         # Data directory (not committed)
│   ├── images/                   # Captured frames
│   ├── pm25/                     # PM2.5 measurements
│   ├── weather/                  # Weather data
│   └── metadata/                 # Collection metadata
├── docs/                         # Documentation
│   ├── camera_locations.txt      # Camera coordinates
│   └── project_proposal.txt      # Original project proposal
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## Usage

### 1. Test Camera Capture

Capture a single frame from all cameras:

```bash
python src/collect_data.py --mode test
```

### 2. Start Continuous Data Collection

Collect frames every hour during daylight (8:00-18:00):

```bash
python src/collect_data.py --mode continuous --interval 60
```

**Important:** By default, collection runs only during daylight hours (8:00-18:00) because visual haze features are not visible at night.

Options:
- `--interval N`: Capture interval in minutes (default: 60)
- `--duration N`: Duration in hours (omit for infinite)
- `--daylight-start H`: Daylight start hour (default: 8)
- `--daylight-end H`: Daylight end hour (default: 18)
- `--24-7`: Collect 24/7 including night (not recommended)
- `--all-cameras`: Include all cameras (including rotating camera)
- `--output DIR`: Output directory (default: data/images)

**Examples:**

```bash
# Collect every hour during daylight (8:00-18:00)
python src/collect_data.py --mode continuous --interval 60

# Collect with custom daylight hours (winter: shorter days)
python src/collect_data.py --mode continuous --interval 60 --daylight-start 9 --daylight-end 17

# Collect 24/7 (not recommended - nighttime images lack visual features)
python src/collect_data.py --mode continuous --interval 60 --24-7
```

### 3. Collect PM2.5 Data

```bash
python src/fetch_pm25_data.py
```

**Note:** PM2.5 collection requires free API keys:
- [IQAir API](https://www.iqair.com/air-pollution-data-api)
- [OpenWeatherMap API](https://openweathermap.org/api)

## Cameras

We use 5 webcams in Bishkek (4 fixed + 1 rotating with quality filtering):

| Camera ID | Location | Coordinates | Resolution | Filtering |
|-----------|----------|-------------|------------|-----------|
| ala_too_square | Ala-Too Square | 42.875576, 74.603629 | 1280x720 | No |
| ala_too_square_2 | Ala-Too Square (Alt) | 42.875767, 74.604619 | 1920x1080 | No |
| bishkek_panorama | City Panorama | TBD | 1920x1080 | No |
| sovmin | Sovmin District | 42.804394, 74.587977 | 1920x1080 | No |
| kt_center | KT Center (rotating) | 42.874689, 74.612241 | 1920x1080 | Yes (~75% pass) |

**Note:** The rotating camera (kt_center) automatically filters frames by quality (brightness, contrast, sharpness). Only useful frames showing clear city views are saved.

Source: [Kyrgyztelekom Online Cameras](https://online.kt.kg)

## Data Collection Strategy

### Timeline
- **Phase 1 (1-2 months):** Automated image collection (target: 2000-4000 images)
- **Phase 2:** Synchronize with PM2.5 and weather data
- **Phase 3:** Dataset preparation and model training
- **Phase 4:** Paper writing and submission

### Data Synchronization
- Images captured every 1 hour
- PM2.5 measurements synchronized within ±10 minutes
- Weather data (temperature, humidity, wind speed) included

## Methodology

### Approach

1. **Image Feature Extraction:** CNN (ResNet/EfficientNet) pre-trained on ImageNet
2. **Meteorological Features:** Temperature, humidity, wind speed, time of day
3. **Multimodal Fusion:** Combine visual + weather features
4. **Regression Model:** Predict PM2.5 concentration (µg/m³)

### Metrics

- Mean Absolute Error (MAE)
- Root Mean Squared Error (RMSE)
- R² (coefficient of determination)

### Experiments

- Baseline: Weather-only model
- Image-only model
- Multimodal model (image + weather)
- Cross-camera generalization
- Seasonal analysis

## Scientific Contribution

- Low-cost PM2.5 monitoring for resource-constrained cities
- Multimodal approach combining visual and meteorological data
- Analysis of camera-specific vs. generalizable models
- Case study for Central Asian city (Bishkek)

## Current Status

- [x] Camera configuration and testing (5 cameras)
- [x] Automated frame capture system
- [x] Frame quality filtering (for rotating camera)
- [x] Daylight-only collection mode
- [x] PM2.5 data collection framework
- [ ] Continuous data collection (ready to start)
- [ ] Dataset preparation
- [ ] Model training
- [ ] Paper writing

## Important Notes

### Data Privacy
All webcams are publicly available and do not capture identifiable personal information.

### Limitations
- Correlation depends on spatial proximity between camera and PM2.5 sensor
- Visual haze can be affected by humidity/fog (not just PM2.5)
- Rotating cameras (e.g., camera35) excluded due to changing viewpoints
- Nighttime images may have limited visual information

### API Rate Limits
- OpenAQ: No API key required, but rate-limited
- IQAir: Free tier limited to 1000 calls/month
- OpenWeatherMap: Free tier limited to 1000 calls/day

## Future Work

- Real-time PM2.5 estimation dashboard
- Mobile app for public access
- Expansion to other Central Asian cities
- Interpretability analysis (Grad-CAM visualizations)

## Contributing

This is a research project. Contributions, suggestions, and feedback are welcome!

## License

TBD

## Citation

If you use this code or dataset, please cite:

```
[Citation will be added after publication]
```

## Contact

Email: raimbekov_m@auca.kg

## Acknowledgments

- Kyrgyztelekom for providing public webcam streams
- OpenAQ, IQAir, and OpenWeatherMap for open data APIs
