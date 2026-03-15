#!/usr/bin/env Rscript

get_this_script_path <- function() {
  cmd_args <- commandArgs(trailingOnly = FALSE)
  file_arg <- "--file="
  hit <- grep(file_arg, cmd_args)
  if (length(hit) > 0) {
    return(normalizePath(sub(file_arg, "", cmd_args[hit[1]]), winslash = "/", mustWork = FALSE))
  }
  for (i in rev(seq_len(sys.nframe()))) {
    frame <- sys.frame(i)
    if (!is.null(frame$ofile)) {
      return(normalizePath(frame$ofile, winslash = "/", mustWork = FALSE))
    }
  }
  stop("Could not determine script path.")
}

get_arg_value <- function(args, key, default = NULL) {
  hit <- which(args == key)
  if (length(hit) == 0 || hit[1] == length(args)) {
    return(default)
  }
  args[hit[1] + 1]
}

script_dir <- dirname(get_this_script_path())

source(file.path(script_dir, "monthly_forecast_common.R"), local = TRUE)

cfg <- list(
  axis = "pitch",
  csv = NULL,
  out = "out_plot",
  file_stem = NULL,
  what = "lv",
  x_start = NA_character_,
  x_end = NA_character_,
  y_min = NA_real_,
  y_max = NA_real_,
  width = 10,
  height = 5,
  dpi = 600,
  band_alpha = 0.15,
  no_band = FALSE
)

build_args_from_cfg <- function(cfg) {
  axis_name <- cfg$axis
  csv_path <- if (is.null(cfg$csv)) {
    file.path("out_rstan_forecast", axis_name, paste0("forecast_monthly_", axis_name, ".csv"))
  } else {
    cfg$csv
  }
  file_stem <- if (is.null(cfg$file_stem)) {
    paste0("figure_forecast_", axis_name)
  } else {
    cfg$file_stem
  }

  out <- c(
    "--axis", axis_name,
    "--csv", csv_path,
    "--out", cfg$out,
    "--file-stem", file_stem,
    "--what", as.character(cfg$what),
    "--width", as.character(cfg$width),
    "--height", as.character(cfg$height),
    "--dpi", as.character(cfg$dpi),
    "--band-alpha", as.character(cfg$band_alpha)
  )

  if (!is.na(cfg$x_start)) out <- c(out, "--x-start", as.character(cfg$x_start))
  if (!is.na(cfg$x_end)) out <- c(out, "--x-end", as.character(cfg$x_end))
  if (is.finite(cfg$y_min)) out <- c(out, "--y-min", as.character(cfg$y_min))
  if (is.finite(cfg$y_max)) out <- c(out, "--y-max", as.character(cfg$y_max))
  if (isTRUE(cfg$no_band)) out <- c(out, "--no-band")

  out
}

args <- commandArgs(trailingOnly = TRUE)
use_args <- length(args) > 0
run_args <- if (use_args) args else build_args_from_cfg(cfg)
axis_name <- get_arg_value(run_args, "--axis", cfg$axis)

run_plot_main(
  args = run_args,
  defaults = list(
    base_dir = script_dir,
    axis = axis_name,
    csv = file.path("out_rstan_forecast", axis_name, paste0("forecast_monthly_", axis_name, ".csv")),
    out = "out_plot",
    file_stem = paste0("figure_forecast_", axis_name),
    what = "lv"
  )
)
