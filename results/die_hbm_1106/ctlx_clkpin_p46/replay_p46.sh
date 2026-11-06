#!/bin/bash
# DIE-HBM-82 d44v part 46 replay from the repo root of the base commit (part 45 applied): results/die_hbm_1106/ctlx_clkpin_p46/replay_p46.sh
set -e; export PYTHONDONTWRITEBYTECODE=1
P=results/die_hbm_1106/ctlx_clkpin_p46
python3 -I $P/mk_p46.py .
python3 -I $P/fin_p46.py .
