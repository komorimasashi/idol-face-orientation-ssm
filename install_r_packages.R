packages <- c(
  "rstan",
  "ggplot2",
  "dplyr",
  "readr"
)

to_install <- setdiff(packages, rownames(installed.packages()))
if (length(to_install) > 0) {
  install.packages(to_install)
} else {
  message("All required R packages are already installed.")
}
