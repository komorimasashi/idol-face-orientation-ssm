# idol-face-orientation-ssm

R, Stan, and Python code for organizing idol group face-orientation data and analyzing monthly `pitch`, `roll`, and `yaw` trends with a state-space model.

This repository is organized around the full workflow from per-person head-pose estimates to the `ssm_input_pitch.csv`, `ssm_input_roll.csv`, and `ssm_input_yaw.csv` files used by the Stan model.

## What This Repository Contains

- Per-image face-orientation estimates exported from 6DRepNet
- A combined CSV across groups and release dates
- Scripts to aggregate individual-level estimates into SSM input files
- R/Stan code for state-space modeling
- Plotting scripts for both KDE-style exploratory plots and SSM output figures

## Repository Structure

- `analysis/`: R and Stan files for the state-space model
- `scripts/`: Python scripts for preprocessing and exploratory plotting
- `data/angle_estimates/`: per-image head-pose CSV files
- `data/combined/`: merged CSV built from per-group angle CSV files
- `data/ssm_inputs/`: aggregated inputs for the Stan model
- `data/raw_images/`: local-only place for raw promotional photos
- `results/`: generated forecasts, figures, and other outputs

## Current Data Layout

At the moment, the repository includes:

- group-level per-image angle CSV files under `data/angle_estimates/`
- a combined file at `data/combined/all_groups_combined.csv`
- SSM-ready inputs in `data/ssm_inputs/`

Raw source images are intentionally not versioned. Put them under `data/raw_images/` only on your local machine if you need to rerun the face-orientation estimation step.

## Workflow

### 1. Estimate per-image angles with 6DRepNet

Script:

- `scripts/estimate_angles_6drepnet.py`

Expected input:

- a folder of face images for one release date, or
- a parent folder containing multiple release-date folders

Expected output:

- one `*_angle.csv` file per release-date folder

Example:

```bash
python scripts/estimate_angles_6drepnet.py data/raw_images/AKB48/ex_akb_20110119 data/angle_estimates/AKB48/ex_akb_20110119_angle.csv
```

Notes:

- this script uses MediaPipe FaceMesh and 6DRepNet
- `roll` is sign-flipped before saving
- raw promotional images are not tracked in Git

### 2. Combine per-group angle CSV files

Script:

- `scripts/combine_angle_csvs.py`

Default behavior:

- reads `data/angle_estimates/*/*_angle.csv`
- writes `data/combined/all_groups_combined.csv`

Example:

```bash
python scripts/combine_angle_csvs.py
```

### 3. Build SSM input files

Script:

- `scripts/build_ssm_inputs.py`

Default behavior:

- reads `data/combined/all_groups_combined.csv`
- writes:
  - `data/ssm_inputs/ssm_input_pitch.csv`
  - `data/ssm_inputs/ssm_input_roll.csv`
  - `data/ssm_inputs/ssm_input_yaw.csv`

Example:

```bash
python scripts/build_ssm_inputs.py --time_mode date
```

### 4. Explore angle distributions with KDE plots

Script:

- `scripts/plot_kde.py`

Default behavior:

- reads `data/angle_estimates/` or a combined CSV
- writes figures to `results/kde/`

Example:

```bash
python scripts/plot_kde.py --combined_csv data/combined/all_groups_combined.csv --legend --fill
```

### 5. Run the state-space model in RStudio

Open `analysis/run_analysis.R` in RStudio and edit the `cfg <- list(...)` block near the top.

Typical settings:

```r
cfg <- list(
  axis = "pitch",
  cutoff = "2026-01-01",
  iter = 2000,
  warmup = 1000,
  chains = 4
)
```

By default, the script reads:

- `../data/ssm_inputs/ssm_input_<axis>.csv`

and writes:

- `../results/forecast/<axis>/`

### 6. Plot the state-space model output in RStudio

Open `analysis/plot_forecast.R` in RStudio and edit the `cfg <- list(...)` block.

Typical settings:

```r
cfg <- list(
  axis = "pitch",
  what = "lv",
  x_start = "2010-01-01",
  x_end = "2026-01-01"
)
```

By default, the script reads:

- `../results/forecast/<axis>/forecast_monthly_<axis>.csv`

and writes:

- `../results/figures/`

## Requirements

### Python

- `pandas`
- `numpy`
- `matplotlib`
- `scikit-learn`
- `opencv-python`
- `mediapipe`
- `sixdrepnet`

Install with:

```bash
pip install -r requirements.txt
```

### R

- `rstan`
- `ggplot2`
- `dplyr`
- `readr`

Install with:

```r
source("install_r_packages.R")
```

## Notes for Public Release

- raw images are excluded from Git
- generated figures and `.rds` files are ignored by `.gitignore`
- this repository is intended to preserve the reproducible data flow from per-image angle estimates to SSM inputs
- groups with name changes are treated as continuous series in the aggregated data
- specifically, Keyakizaka46 and Sakurazaka46 are integrated as `Sakurazaka46`, and Hiragana Keyakizaka46 / Hinatazaka46 are integrated as `Hinatazaka46`
