#!/bin/bash
# DIE-HBM-82 d44v part 45 replay from the repo root of the base commit: results/die_hbm_1106/clkpin_sites_p45/replay_p45.sh
set -e; export PYTHONDONTWRITEBYTECODE=1
P=results/die_hbm_1106/clkpin_sites_p45
python3 -I $P/mk_p45.py physical/die_plan/hbm/plan_of_record/d44v
python3 -I $P/fin_p45.py .
