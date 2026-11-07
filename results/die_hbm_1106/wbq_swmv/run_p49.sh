#!/bin/bash
# DIE-HBM-82-EP6 d44v part 49 (plan-owner approved DIE-HBM-82 16:5x): ot_wbq_sw 86.4 -> 155.52 wide (grown WEST) in q_hub_nw/ne q0+q1,
# aq_tree13 u_xl_Q_aqhi 51.84 west (q1), station chains re-planned (station_resite.py, applied only to chains the move touched,
# then ft_nudge.py).  Run from the repo root on a tree whose d44v holds every earlier part:  RR=<scratch dir> bash run_p49.sh
set -e
RR=${RR:?scratch dir}; D=physical/die_plan/hbm/plan_of_record/d44v; F=results/die_hbm_1106/wbq_swmv
export PYTHONDONTWRITEBYTECODE=1
rm -rf $RR; mkdir -p $RR; cp -r $D $RR/p; find $RR/p -name '*.gz' -exec gunzip -f {} +
cp $RR/p/die_plan.json $RR/base.json
python3 -I $F/mk_mv.py $RR/p | tee $RR/mk_mv.log
PYTHONPATH=tools/die_plan:tools python3 tools/die_plan/station_resite.py $RR/p $RR/rs --types q_hub_nw,q_hub_ne --jobs ${JOBS:-16} | tee $RR/resite.log
python3 -I $F/hyb.py $RR/p/die_plan.json $RR/rs/die_plan.json $RR/base.json $RR/hy.json | tee $RR/hyb.log
PYTHONPATH=tools/die_plan:tools python3 tools/die_plan/ft_nudge.py $RR/hy.json $RR/new.json $D/part49_ft_nudge_ledger.json | tee $RR/nudge.log
python3 -I $F/write_p49.py $RR
