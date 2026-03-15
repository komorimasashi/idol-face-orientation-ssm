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

source(file.path(script_dir, "face_orientation_common.R"), local = TRUE)

cfg <- list(
  axis = "pitch",
  csv = NULL,
  out = NULL,
  cutoff = "2026-01-01",
  by = "month",
  ci = 0.95,
  iter = 2000,
  warmup = 1000,
  chains = 4,
  seed = 1234,
  dt_scale = 365.25,
  dt_floor = 1e-6
)

build_args_from_cfg <- function(cfg, script_dir) {
  axis_name <- cfg$axis
  csv_path <- if (is.null(cfg$csv)) {
    file.path("data", paste0("ssm_input_", axis_name, ".csv"))
  } else {
    cfg$csv
  }
  out_path <- if (is.null(cfg$out)) {
    file.path("out_rstan_forecast", axis_name)
  } else {
    cfg$out
  }

  c(
    "--axis", axis_name,
    "--stem", axis_name,
    "--csv", csv_path,
    "--stan", "nonhier_rw_forecast.stan",
    "--out", out_path,
    "--cutoff", as.character(cfg$cutoff),
    "--by", as.character(cfg$by),
    "--ci", as.character(cfg$ci),
    "--iter", as.character(cfg$iter),
    "--warmup", as.character(cfg$warmup),
    "--chains", as.character(cfg$chains),
    "--seed", as.character(cfg$seed),
    "--dt_scale", as.character(cfg$dt_scale),
    "--dt_floor", as.character(cfg$dt_floor)
  )
}

args <- commandArgs(trailingOnly = TRUE)
use_args <- length(args) > 0
run_args <- if (use_args) args else build_args_from_cfg(cfg, script_dir)
axis_name <- get_arg_value(run_args, "--axis", cfg$axis)

run_analysis_main(
  args = run_args,
  defaults = list(
    base_dir = script_dir,
    csv = file.path("data", paste0("ssm_input_", axis_name, ".csv")),
    stan = "nonhier_rw_forecast.stan",
    out = file.path("out_rstan_forecast", axis_name),
    axis = axis_name,
    stem = axis_name
  )
)
