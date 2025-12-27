# Camera Specifications for Research Paper

This document contains detailed technical specifications of webcams used in the PM2.5 estimation study.

## Camera Locations and Viewing Directions

### 1. Bishkek Panorama ⭐ PRIMARY CAMERA
**Camera ID:** `bishkek_panorama`
**Coordinates:** 42.799197°N, 74.645485°E
**Elevation:** High elevation point
**Viewing Direction:** ~330° (Northwest)
**Field of View:** Panoramic, very wide angle
**Resolution:** 1920×1080

**Characteristics:**
- **Best camera for PM2.5 estimation**
- Overlooks entire city with extensive horizon visibility
- Clear view of atmospheric haze at various distances
- Minimal foreground obstruction
- Captures both near-field (buildings) and far-field (mountains/horizon) features
- Ideal for visibility-based air quality assessment

**Visible Features:**
- City buildings at multiple distances
- Mountains on horizon (when visible)
- Sky occupies large portion of frame
- Haze gradient clearly visible

---

### 2. Sovmin (Residential District) ⭐ HIGH QUALITY
**Camera ID:** `sovmin`
**Coordinates:** 42.804394°N, 74.587977°E
**Elevation:** High elevation point
**Viewing Direction:** ~45° (Northeast)
**Field of View:** Wide, elevated perspective
**Resolution:** 1920×1080

**Characteristics:**
- Overlooks residential neighborhoods
- Good depth perception with buildings at varying distances
- Clear haze visibility in mid-field and far-field
- High vantage point provides unobstructed view
- Represents typical residential air quality

**Visible Features:**
- Low-rise residential buildings (foreground)
- High-rise apartments (mid-field)
- Distant buildings in haze (far-field)
- Sky and horizon visible

---

### 3. KT Center (Rotating Camera) 🔄 WITH FILTERING
**Camera ID:** `kt_center`
**Coordinates:** 42.874689°N, 74.612241°E
**Viewing Direction:** Variable (rotating, 360° coverage)
**Field of View:** Changes with rotation
**Resolution:** 1920×1080
**Quality Filter:** Yes (~75% frame acceptance rate)

**Characteristics:**
- PTZ (Pan-Tilt-Zoom) camera with programmed rotation pattern
- Captures multiple city perspectives
- Automatic quality filtering removes:
  - Frames during rotation (motion blur)
  - Downward-facing views (insufficient sky)
  - Low-contrast scenes
  - Poorly lit or overexposed frames
- Only sharp, useful frames with clear city views are retained

**Filtering Criteria:**
- Brightness: 50-250 (8-bit scale)
- Contrast: ≥30 (std deviation)
- Sharpness: ≥50 (Laplacian variance)
- Sky ratio: ≥30% in upper third of frame

**Usage Note:**
For dataset consistency, each saved frame should be analyzed independently rather than assuming temporal continuity.

---

### 4. Ala-Too Square Camera 2
**Camera ID:** `ala_too_square_2`
**Coordinates:** 42.875767°N, 74.604619°E
**Viewing Direction:** ~90° (East)
**Field of View:** Horizontal, wide angle along roadway
**Resolution:** 1920×1080

**Characteristics:**
- Views along major road/boulevard
- Buildings visible in background
- Some foreground obstruction (road, square)
- Moderate suitability for haze detection
- Good as supplementary camera

**Visible Features:**
- Road and plaza in foreground
- Buildings at mid-distance
- Trees and urban landscape
- Partial horizon visibility

---

## Excluded Camera

### ❌ Ala-Too Square Camera 1 (NOT RECOMMENDED)
**Camera ID:** `ala_too_square`
**Coordinates:** 42.875576°N, 74.603629°E
**Viewing Direction:** 10-12° N (downward angle)
**Viewing Angle:** Downward-facing

**Reason for Exclusion:**
- Camera points downward at plaza
- Excessive foreground (square, decorations, people)
- Limited horizon/sky visibility
- Insufficient depth of field for haze assessment
- Not suitable for atmospheric visibility analysis

---

## Camera Selection Rationale

For PM2.5 estimation via image analysis, cameras must meet these criteria:

1. **Horizon Visibility:** At least 30% of frame should show sky/horizon
2. **Depth Range:** Objects visible at multiple distances (near, mid, far)
3. **Atmospheric Features:** Clear view of haze gradient
4. **Minimal Foreground:** Limited obstruction in foreground
5. **Fixed Viewpoint:** Consistent perspective (except rotating camera with filtering)

### Recommended Dataset Composition:
- **Primary:** Bishkek Panorama (highest quality, most suitable)
- **Secondary:** Sovmin (residential area perspective)
- **Supplementary:** KT Center (filtered frames), Ala-Too Square 2

---

## Technical Considerations for Research Paper

### Spatial Coverage
Cameras cover different parts of Bishkek:
- **North city:** Sovmin
- **South city:** Panorama (highest point)
- **Central:** KT Center, Ala-Too Square 2
- **Altitude range:** Cameras at different elevations provide varying atmospheric path lengths

### Multi-Perspective Advantages
1. Different viewing angles reduce bias from localized conditions
2. Multiple cameras enable cross-validation of PM2.5 estimates
3. Varying FOVs capture different aspects of atmospheric visibility

### Limitations
1. Cameras and PM2.5 sensors may be spatially separated (distance TBD)
2. Different viewing directions may observe different air masses
3. Rotating camera introduces temporal inconsistency

### For Methodology Section
When describing data collection methodology, include:
- Exact coordinates of each camera
- Viewing direction (azimuth in degrees)
- Field of view characteristics
- Elevation/height above ground (if available)
- Distance to nearest PM2.5 monitoring station
- Explanation of rotating camera filtering process

---

**Document Version:** 1.0
**Last Updated:** 2025-12-27
**Status:** Ready for paper integration
