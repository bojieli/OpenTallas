#!/bin/bash
# DIE-HBM-81 d44v part 39 replay from the repo root of the base commit: results/die_hbm_1106/svg_track_p39/replay_p39.sh
set -e; export PYTHONDONTWRITEBYTECODE=1
P=results/die_hbm_1106/svg_track_p39
python3 -I $P/mk_p39.py physical/die_plan/hbm/plan_of_record/d44v
python3 -I $P/fin_p39.py .
