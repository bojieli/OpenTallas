#!/bin/bash
# DIE-HBM-82-G0C d44v part 43 replay from the repo root of the base commit: results/die_hbm_1106/street_p43/replay_p43.sh
set -e; export PYTHONDONTWRITEBYTECODE=1
P=results/die_hbm_1106/street_p43
T=$(mktemp -d); trap 'rm -rf $T' EXIT
POR=$(python3 -I $P/mat_por.py . $T)
python3 -I $P/mk_p43.py $POR physical/die_plan/hbm/plan_of_record/d44v $P/ledger_p43.json
python3 -I $P/fin_p43.py .
