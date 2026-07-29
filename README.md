# Research on Kalimati Market — Kalimati War Effects

This repository contains data, code, and analysis for a reproducible study of how regional wars affected prices and availability at Kalimati Market.

## Quick start

- Place raw data in data/raw/ (do not commit large raw files).
- Create virtual environment and install dependencies from requirements.txt.
- Use the scripts in src/ for reproducible processing and analysis.

## Repository structure

- README.md                 — project overview (this file)
- LICENSE
- .gitignore
- data/
  - raw/                    — untouched source data (place your raw CSVs here)
  - processed/              — cleaned data ready for analysis
  - external/               — reference datasets (conflict event datasets, etc.)
- notebooks/
  - 01_data_cleaning.ipynb
  - 02_exploratory_analysis.ipynb
  - 03_war_impact_analysis.ipynb
- src/
  - __init__.py
  - scrape.py
  - clean.py
  - analysis.py
  - visualize.py
- figures/                  — exported charts/plots
- report/
  - report.md
  - references.bib
- requirements.txt
- docs/
  - README.md

---

For full usage and reproduction instructions, edit this README with dataset sources, authorship, and citation information.
