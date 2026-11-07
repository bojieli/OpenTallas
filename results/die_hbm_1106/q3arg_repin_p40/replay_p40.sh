#!/bin/bash
# DIE-HBM-82 d44v part 40 replay from the repo root of the base commit: results/die_hbm_1106/q3arg_repin_p40/replay_p40.sh
set -e; export PYTHONDONTWRITEBYTECODE=1
P=results/die_hbm_1106/q3arg_repin_p40
python3 -I $P/mk_p40.py .
python3 -I $P/fin_p40.py .
