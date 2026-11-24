# Packages nécessaires au pipeline de traitement de l'EHCVM2
install.packages("pacman")
pacman::p_load(
  haven, labelled, readxl, readr, data.table,
  dplyr, tidyr, purrr, stringr, forcats, tibble,
  glue, here,
  rmarkdown, knitr, kableExtra,
  ggplot2, scales, patchwork,
  survey, Hmisc
)
