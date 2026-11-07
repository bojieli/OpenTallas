#!/bin/bash
# DIE-HBM-82 d44v part 50 replay from the repo root of the base commit: results/die_hbm_1106/clkpin_sites_p50/replay_p50.sh
set -e; export PYTHONDONTWRITEBYTECODE=1
P=results/die_hbm_1106/clkpin_sites_p50
python3 -I $P/mk_p50.py physical/die_plan/hbm/plan_of_record/d44v physical/die_plan/hbm/plan_of_record
python3 -I $P/fin_p50.py .
