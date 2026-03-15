#!/usr/bin/env Rscript

get_script_path <- function() {
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

has_flag <- function(args, key) {
  any(args == key)
}

resolve_path <- function(path, base_dir, must_work = FALSE) {
  if (is.null(path) || identical(path, "")) {
    return(path)
  }

  if (grepl("^(/|[A-Za-z]:[/\\\\]|~)", path)) {
    return(normalizePath(path, winslash = "/", mustWork = must_work))
  }

  normalizePath(file.path(base_dir, path), winslash = "/", mustWork = must_work)
}

summ_ci_mat <- function(mat, ci = 0.95) {
  alpha <- (1 - ci) / 2
  data.frame(
    mean = apply(mat, 2, mean),
    lo = apply(mat, 2, quantile, probs = alpha),
    hi = apply(mat, 2, quantile, probs = 1 - alpha)
  )
}

add_month_grid <- function(df_train, cutoff_date, by_unit = "month") {
  groups <- sort(unique(df_train$group))
  se_rep <- tapply(
    df_train$se,
    df_train$group,
    function(v) median(v[is.finite(v)], na.rm = TRUE)
  )

  grid_list <- list()
  for (g in groups) {
    dmin <- min(df_train$date[df_train$group == g], na.rm = TRUE)
    if (!is.finite(dmin)) {
      next
    }

    start0 <- as.Date(format(dmin, "%Y-%m-01"))
    ds <- seq.Date(from = start0, to = cutoff_date, by = by_unit)
    if (length(ds) == 0) {
      next
    }

    grid_list[[g]] <- data.frame(
      group = g,
      date = ds,
      y = 0,
      se = as.numeric(se_rep[g]),
      is_obs = 0L,
      is_month = 1L,
      stringsAsFactors = FALSE
    )
  }

  df_grid <- if (length(grid_list) > 0) {
    do.call(rbind, grid_list)
  } else {
    df_train[0, c("group", "date", "y", "se", "is_obs"), drop = FALSE]
  }

  df_obs <- df_train
  df_obs$is_month <- 0L

  df_all <- rbind(df_grid, df_obs)
  key <- paste(df_all$group, df_all$date)
  ord <- order(key, -df_all$is_obs)
  df_all <- df_all[ord, , drop = FALSE]

  keep <- !duplicated(key[ord])
  df_keep <- df_all[keep, , drop = FALSE]

  is_month_by_key <- tapply(df_all$is_month, key[ord], max)
  df_keep$is_month <- as.integer(is_month_by_key[paste(df_keep$group, df_keep$date)])
  df_keep
}

make_stan_data <- function(df_long, dt_scale, dt_floor) {
  df_long <- df_long[order(df_long$group, df_long$date), , drop = FALSE]

  groups <- sort(unique(df_long$group))
  gid <- match(df_long$group, groups)

  n_time <- nrow(df_long)
  n_group <- length(groups)

  prev_idx <- integer(n_time)
  is_start <- integer(n_time)
  delta_t <- numeric(n_time)

  last_i <- rep(NA_integer_, n_group)
  last_d <- rep(as.Date(NA), n_group)

  for (t in seq_len(n_time)) {
    g <- gid[t]
    if (is.na(last_i[g])) {
      is_start[t] <- 1L
      prev_idx[t] <- t
      delta_t[t] <- dt_floor
    } else {
      is_start[t] <- 0L
      prev_idx[t] <- last_i[g]
      ddays <- as.numeric(difftime(df_long$date[t], last_d[g], units = "days"))
      dt <- if (dt_scale > 0) ddays / dt_scale else ddays
      delta_t[t] <- max(dt, dt_floor)
    }
    last_i[g] <- t
    last_d[g] <- df_long$date[t]
  }

  list(
    stan_data = list(
      T = as.integer(n_time),
      G = as.integer(n_group),
      grp_id = as.integer(gid),
      y = as.numeric(df_long$y),
      y_se = as.numeric(df_long$se),
      is_obs = as.integer(df_long$is_obs),
      delta_t = as.numeric(delta_t),
      prev_idx = as.integer(prev_idx),
      is_start = as.integer(is_start)
    ),
    df_map = data.frame(
      t = seq_len(n_time),
      group = df_long$group,
      gid = gid,
      date = df_long$date,
      is_obs = df_long$is_obs,
      is_month = df_long$is_month,
      stringsAsFactors = FALSE
    )
  )
}

normalize_group_key <- function(x) {
  x2 <- tolower(trimws(as.character(x)))
  gsub("[^a-z0-9\\+]+", "", x2)
}

to_group_id <- function(k) {
  if (grepl("keyakizaka", k) || grepl("sakurazaka", k)) return("Sakurazaka46")
  if (grepl("nogizaka", k)) return("Nogizaka46")
  if (grepl("hinatazaka", k)) return("Hinatazaka46")
  if (grepl("^akb48$", k)) return("AKB48")
  if (grepl("^ske48$", k)) return("SKE48")
  if (grepl("^nmb48$", k)) return("NMB48")
  if (grepl("^hkt48$", k)) return("HKT48")
  if (grepl("^ngt48$", k)) return("NGT48")
  if (grepl("^stu48$|^sut48$", k)) return("STU48")
  k
}

label_map <- c(
  "Nogizaka46" = "乃木坂46",
  "Hinatazaka46" = "けやき坂46→日向坂46",
  "Sakurazaka46" = "欅坂46→櫻坂46",
  "AKB48" = "AKB48",
  "SKE48" = "SKE48",
  "NMB48" = "NMB48",
  "HKT48" = "HKT48",
  "NGT48" = "NGT48",
  "STU48" = "STU48"
)

group_colors <- c(
  "Nogizaka46" = "#6A3D9A",
  "Hinatazaka46" = "#56B4E9",
  "Sakurazaka46" = "#E78AC3",
  "AKB48" = "#D62728",
  "SKE48" = "#2CA02C",
  "NMB48" = "#8C564B",
  "HKT48" = "#000000",
  "NGT48" = "#1F78B4",
  "STU48" = "#F0E442"
)

default_axis_label <- function(axis, what = "lv") {
  axis_name <- if (nzchar(axis)) {
    paste0(toupper(substr(axis, 1, 1)), substring(axis, 2))
  } else {
    "Axis"
  }

  if (what == "lv") {
    paste0(axis_name, " (degree)")
  } else {
    paste0(axis_name, " (predicted)")
  }
}

date_break_unit <- function(x_start, x_end) {
  span_years <- as.numeric(difftime(x_end, x_start, units = "days")) / 365.25
  if (is.na(span_years) || span_years > 10) {
    "2 years"
  } else if (span_years > 4) {
    "1 year"
  } else {
    "6 months"
  }
}

run_analysis_main <- function(args = commandArgs(trailingOnly = TRUE), defaults = list()) {
  suppressPackageStartupMessages({
    library(rstan)
  })

  base_dir <- defaults$base_dir %||% getwd()
  csv_file <- resolve_path(get_arg_value(args, "--csv", defaults$csv %||% "ssm_input_pitch.csv"), base_dir, must_work = TRUE)
  stan_file <- resolve_path(get_arg_value(args, "--stan", defaults$stan %||% "scripts/nonhier_rw_forecast.stan"), base_dir, must_work = TRUE)
  out_dir <- resolve_path(get_arg_value(args, "--out", defaults$out %||% "out_rstan_forecast"), base_dir, must_work = FALSE)
  axis_name <- get_arg_value(args, "--axis", defaults$axis %||% "pitch")
  out_stem <- get_arg_value(args, "--stem", defaults$stem %||% axis_name)
  cutoff_str <- get_arg_value(args, "--cutoff", defaults$cutoff %||% "2026-01-01")
  by_unit <- get_arg_value(args, "--by", defaults$by %||% "month")
  ci_level <- as.numeric(get_arg_value(args, "--ci", defaults$ci %||% "0.95"))
  iter <- as.integer(get_arg_value(args, "--iter", defaults$iter %||% "2000"))
  warmup <- as.integer(get_arg_value(args, "--warmup", defaults$warmup %||% "1000"))
  chains <- as.integer(get_arg_value(args, "--chains", defaults$chains %||% "4"))
  seed <- as.integer(get_arg_value(args, "--seed", defaults$seed %||% "1234"))
  dt_scale <- as.numeric(get_arg_value(args, "--dt_scale", defaults$dt_scale %||% "365.25"))
  dt_floor <- as.numeric(get_arg_value(args, "--dt_floor", defaults$dt_floor %||% "1e-6"))

  if (!dir.exists(out_dir)) {
    dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
  }

  df <- read.csv(csv_file, stringsAsFactors = FALSE)
  stopifnot(all(c("group", "time", "y", "se") %in% names(df)))

  df$date <- as.Date(df$time)
  cutoff_date <- as.Date(cutoff_str)

  df_train <- df[df$date <= cutoff_date, c("group", "date", "y", "se"), drop = FALSE]
  df_train$is_obs <- 1L

  if (nrow(df_train) == 0) {
    stop("No training rows (date <= cutoff). Check --cutoff and your CSV dates.")
  }

  df_all <- add_month_grid(df_train, cutoff_date = cutoff_date, by_unit = by_unit)
  df_all <- df_all[df_all$date <= cutoff_date, , drop = FALSE]

  obj <- make_stan_data(df_all, dt_scale = dt_scale, dt_floor = dt_floor)
  stan_data <- obj$stan_data
  df_map <- obj$df_map

  rstan_options(auto_write = TRUE)
  options(mc.cores = parallel::detectCores())

  sm <- stan_model(file = stan_file)
  fit <- sampling(
    object = sm,
    data = stan_data,
    iter = iter,
    warmup = warmup,
    chains = chains,
    seed = seed,
    refresh = 200
  )

  fit_path <- file.path(out_dir, paste0("fit_", out_stem, ".rds"))
  saveRDS(fit, file = fit_path)

  post <- rstan::extract(fit)
  level_mat <- post$level_state
  yrep_mat <- post$y_rep

  lv_sum <- summ_ci_mat(level_mat, ci = ci_level)
  yr_sum <- summ_ci_mat(yrep_mat, ci = ci_level)

  res <- cbind(
    df_map,
    lv_mean = lv_sum$mean,
    lv_lo = lv_sum$lo,
    lv_hi = lv_sum$hi,
    y_mean = yr_sum$mean,
    y_lo = yr_sum$lo,
    y_hi = yr_sum$hi
  )

  res <- res[res$date <= cutoff_date, , drop = FALSE]
  res_monthly <- res[res$is_month == 1L, , drop = FALSE]
  res_monthly <- res_monthly[order(res_monthly$group, res_monthly$date), , drop = FALSE]

  out_csv <- file.path(out_dir, paste0("forecast_monthly_", out_stem, ".csv"))
  write.csv(res_monthly, file = out_csv, row.names = FALSE, fileEncoding = "UTF-8")

  cat("[OK] axis: ", axis_name, "\n", sep = "")
  cat("[OK] fit:  ", normalizePath(fit_path, winslash = "/", mustWork = FALSE), "\n", sep = "")
  cat("[OK] csv:  ", normalizePath(out_csv, winslash = "/", mustWork = FALSE), "\n", sep = "")
}

run_plot_main <- function(args = commandArgs(trailingOnly = TRUE), defaults = list()) {
  suppressPackageStartupMessages({
    library(ggplot2)
    library(dplyr)
    library(readr)
  })

  base_dir <- defaults$base_dir %||% getwd()
  axis_name <- get_arg_value(args, "--axis", defaults$axis %||% "pitch")
  forecast_csv <- resolve_path(
    get_arg_value(args, "--csv", defaults$csv %||% "out_rstan_forecast/forecast_monthly_pitch.csv"),
    base_dir,
    must_work = TRUE
  )
  out_dir <- resolve_path(get_arg_value(args, "--out", defaults$out %||% "out_plot"), base_dir, must_work = FALSE)
  what <- get_arg_value(args, "--what", defaults$what %||% "lv")
  file_stem <- get_arg_value(args, "--file-stem", defaults$file_stem %||% paste0("figure_forecast_", axis_name))
  x_start_raw <- get_arg_value(args, "--x-start", defaults$x_start %||% NA_character_)
  x_end_raw <- get_arg_value(args, "--x-end", defaults$x_end %||% NA_character_)
  y_min_raw <- get_arg_value(args, "--y-min", defaults$y_min %||% NA_character_)
  y_max_raw <- get_arg_value(args, "--y-max", defaults$y_max %||% NA_character_)
  width <- as.numeric(get_arg_value(args, "--width", defaults$width %||% "10"))
  height <- as.numeric(get_arg_value(args, "--height", defaults$height %||% "5"))
  dpi <- as.integer(get_arg_value(args, "--dpi", defaults$dpi %||% "600"))
  band_alpha <- as.numeric(get_arg_value(args, "--band-alpha", defaults$band_alpha %||% "0.15"))
  do_band <- !has_flag(args, "--no-band")

  if (!dir.exists(out_dir)) {
    dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
  }

  df <- readr::read_csv(forecast_csv, show_col_types = FALSE) %>%
    mutate(
      group = trimws(as.character(group)),
      date = as.Date(date)
    ) %>%
    arrange(group, date)

  if (what == "lv") {
    need_cols <- c("lv_mean", "lv_lo", "lv_hi")
    miss_cols <- setdiff(need_cols, names(df))
    if (length(miss_cols) > 0) {
      stop("csv is missing columns: ", paste(miss_cols, collapse = ", "))
    }
    df <- df %>% mutate(mu = lv_mean, qlo = lv_lo, qhi = lv_hi)
  } else if (what == "y") {
    need_cols <- c("y_mean", "y_lo", "y_hi")
    miss_cols <- setdiff(need_cols, names(df))
    if (length(miss_cols) > 0) {
      stop("csv is missing columns: ", paste(miss_cols, collapse = ", "))
    }
    df <- df %>% mutate(mu = y_mean, qlo = y_lo, qhi = y_hi)
  } else {
    stop("--what must be 'lv' or 'y'")
  }

  x_start <- if (is.na(x_start_raw) || x_start_raw == "") min(df$date, na.rm = TRUE) else as.Date(x_start_raw)
  x_end <- if (is.na(x_end_raw) || x_end_raw == "") max(df$date, na.rm = TRUE) else as.Date(x_end_raw)
  df <- df %>% filter(date >= x_start, date <= x_end)

  df <- df %>%
    mutate(
      group_key = normalize_group_key(group),
      group_id = vapply(group_key, to_group_id, character(1))
    )

  order_levels <- df %>%
    group_by(group_id) %>%
    summarize(last_mu = mu[which.max(date)], .groups = "drop") %>%
    arrange(desc(last_mu)) %>%
    pull(group_id)

  df <- df %>% mutate(group_id = factor(group_id, levels = unique(order_levels)))

  y_min <- suppressWarnings(as.numeric(y_min_raw))
  y_max <- suppressWarnings(as.numeric(y_max_raw))
  if (!is.finite(y_min) || !is.finite(y_max)) {
    rng <- range(c(df$qlo, df$qhi, df$mu), finite = TRUE)
    pad <- 0.05 * (rng[2] - rng[1] + 1e-9)
    if (!is.finite(y_min)) y_min <- rng[1] - pad
    if (!is.finite(y_max)) y_max <- rng[2] + pad
  }
  y_breaks <- seq(floor(y_min), ceiling(y_max), by = 1)

  paper_theme <- theme_classic(base_size = 11) +
    theme(
      legend.position = "right",
      legend.title = element_blank(),
      axis.line = element_line(linewidth = 0.5),
      axis.text = element_text(size = 10),
      axis.title = element_text(size = 11)
    )

  p <- ggplot(df, aes(x = date, y = mu, color = group_id)) +
    {
      if (do_band && any(is.finite(df$qlo)) && any(is.finite(df$qhi))) {
        geom_ribbon(
          aes(ymin = qlo, ymax = qhi, fill = group_id),
          alpha = band_alpha,
          colour = NA
        )
      }
    } +
    geom_line(linewidth = 0.7, alpha = 0.95) +
    scale_color_manual(values = group_colors, labels = label_map, drop = FALSE) +
    scale_fill_manual(values = group_colors, labels = label_map, drop = FALSE) +
    guides(fill = "none") +
    coord_cartesian(xlim = c(x_start, x_end), ylim = c(y_min, y_max)) +
    scale_x_date(date_breaks = date_break_unit(x_start, x_end), date_labels = "%Y") +
    scale_y_continuous(breaks = y_breaks, minor_breaks = NULL) +
    labs(x = "Year", y = default_axis_label(axis_name, what)) +
    paper_theme

  print(p)

  tag <- if (what == "lv") "latent" else "y"
  out_base <- file.path(out_dir, paste0(file_stem, "_", tag))
  ggsave(paste0(out_base, ".pdf"), p, width = width, height = height)
  ggsave(paste0(out_base, ".png"), p, width = width, height = height, dpi = dpi)

  cat("[OK] axis: ", axis_name, "\n", sep = "")
  cat("[OK] pdf:  ", normalizePath(paste0(out_base, ".pdf"), winslash = "/", mustWork = FALSE), "\n", sep = "")
  cat("[OK] png:  ", normalizePath(paste0(out_base, ".png"), winslash = "/", mustWork = FALSE), "\n", sep = "")
}

`%||%` <- function(x, y) {
  if (is.null(x)) y else x
}
