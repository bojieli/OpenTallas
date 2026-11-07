#!/bin/bash
# DIE-HBM-82-SPB d44v part 54 replay (plan-owner approved DIE-HBM-82): lane L3012 pin windows -> max(old, 3.5) um, same centre.
# Run from the repo root on a tree whose d44v holds every part before 54:  RR=<scratch dir> bash results/die_hbm_1106/spb2_uturn/run_p54.sh
set -e; export PYTHONDONTWRITEBYTECODE=1
RR=${RR:?scratch dir}; F=results/die_hbm_1106/spb2_uturn
rm -rf $RR; mkdir -p $RR
POR=$(python3 -I results/die_hbm_1106/street_p43/mat_por.py . $RR/mat)
python3 -I $F/mk_l3012.py $POR $RR/new.json $RR/ledger.json | tee $RR/mk.log
python3 -I $F/fin_p54.py $RR
# kit-local application to an already generated kit of an L3012 type (here q_spb2):
#   python3 -I $F/kit_pin_patch.py <plan before 54> $RR/new.json <KIT> q_spb2 L3012x5_i,L3012x5_o
