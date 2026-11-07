#!/bin/bash
# DIE-HBM-82-EP6 d44v part 51 replay, from the repo root of a checkout of the base commit with the RTL commit in history:
#   results/die_hbm_1106/wbq_g2/replay_p51.sh RTL_COMMIT
set -e; export PYTHONDONTWRITEBYTECODE=1
P=results/die_hbm_1106/wbq_g2
python3 -I $P/mk_p51.py physical/die_plan/hbm/plan_of_record/d44v
python3 -I $P/fin_p51.py . ${1:?RTL commit}
