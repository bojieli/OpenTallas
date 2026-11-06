#!/bin/bash
# DIE-HBM-81 d44v part 37 replay (from the repo root of a checkout of the base commit with HBM-GAPS-7 992171836f merged):
#   results/die_hbm_1106/rx_bm3_p37/replay_p37.sh
set -e; export PYTHONDONTWRITEBYTECODE=1
P=results/die_hbm_1106/rx_bm3_p37
python3 -I $P/mk_p37.py physical/die_plan/hbm/plan_of_record/d44v physical/die_plan/hbm/over_cap_split/reform_1106/rx_bm3/gen_hg7
python3 -I $P/fin_p37.py .
