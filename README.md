# idol-face-orientation-ssm

R and Stan code for analyzing monthly face-orientation data from idol group promotional photos with a state-space model.

This repository works with monthly averages of `pitch`, `roll`, and `yaw` for each song release. It is designed for an RStudio-based workflow: edit a small configuration block at the top of a script, then run the script with `Source`.

## Overview

- Input data are organized by axis: `pitch`, `roll`, `yaw`
- Each CSV contains monthly summary values by group
- Estimation is done with a non-hierarchical state-space model in Stan
- Plotting is handled separately from model fitting

## Repository Structure

- `data/`: input CSV files
- `run_analysis.R`: model fitting and posterior summary export
- `plot_forecast.R`: plotting from saved forecast CSV files
- `face_orientation_common.R`: shared R functions used by both scripts
- `nonhier_rw_forecast.stan`: Stan model
- `out_rstan_forecast/<axis>/`: model outputs for each axis
- `out_plot/`: exported figures

## Requirements

The scripts assume the following R packages are available:

- `rstan`
- `ggplot2`
- `dplyr`
- `readr`

## Input Data

The input files are:

- `data/ssm_input_pitch.csv`
- `data/ssm_input_roll.csv`
- `data/ssm_input_yaw.csv`

Each file is expected to include at least these columns:

- `group`
- `time`
- `y`
- `se`

## RStudio Workflow

### 1. Run the analysis

Open `run_analysis.R` in RStudio and edit the `cfg <- list(...)` block near the top.

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

Change `axis` to `"roll"` or `"yaw"` when needed, then run the file with `Source`.

### 2. Create plots

Open `plot_forecast.R` in RStudio and edit the `cfg <- list(...)` block.

Typical settings:

```r
cfg <- list(
  axis = "pitch",
  what = "lv",
  x_start = "2010-01-01",
  x_end = "2026-01-01"
)
```

- `axis`: `"pitch"`, `"roll"`, or `"yaw"`
- `what = "lv"`: plot latent state estimates
- `what = "y"`: plot observation-level predictive summaries

Then run the file with `Source`.

## Command-Line Usage

The same scripts can also be run from the command line.

Analysis:

```bash
cd idol-face-orientation-ssm
Rscript run_analysis.R --axis pitch
Rscript run_analysis.R --axis roll
Rscript run_analysis.R --axis yaw
```

Plotting:

```bash
cd idol-face-orientation-ssm
Rscript plot_forecast.R --axis pitch
Rscript plot_forecast.R --axis roll
Rscript plot_forecast.R --axis yaw
```

Examples with additional options:

```bash
Rscript run_analysis.R --axis pitch --cutoff 2026-01-01 --iter 4000 --warmup 2000
Rscript plot_forecast.R --axis pitch --what y --x-start 2010-01-01 --x-end 2026-01-01
```

## Outputs

Analysis results are written to:

- `out_rstan_forecast/pitch/`
- `out_rstan_forecast/roll/`
- `out_rstan_forecast/yaw/`

Plots are written to:

- `out_plot/`

## Notes

- This repository is organized around monthly aggregated data, not individual-level face orientation measurements
- Generated files such as `.rds`, `.pdf`, and `.png` are ignored via `.gitignore`
- If you plan to reproduce the analysis on another machine, install the required R packages first
