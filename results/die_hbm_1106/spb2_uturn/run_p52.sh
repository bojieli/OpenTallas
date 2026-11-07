#!/bin/bash
# DIE-HBM-82-SPB d44v part 52 replay (plan-owner approved DIE-HBM-82): q_spb2 L1278x3 / L1280x6 U-turn corridors below the xcal row.
# Run from the repo root on a tree whose d44v holds every part before 52:  RR=<scratch dir> bash results/die_hbm_1106/spb2_uturn/run_p52.sh
set -e; export PYTHONDONTWRITEBYTECODE=1
RR=${RR:?scratch dir}; F=results/die_hbm_1106/spb2_uturn
rm -rf $RR; mkdir -p $RR
POR=$(python3 -I results/die_hbm_1106/street_p43/mat_por.py . $RR/mat)
python3 $F/mk_uturn.py $POR $RR/new.json $RR/ledger.json | tee $RR/mk.log
python3 -I $F/fin_p52.py $RR
# kit-local application to an already generated q_spb2 kit (same bytes gen_phys writes for these two slots):
#   python3 $F/kit_patch.py $RR/new.json <KIT> L1278x3,L1280x6
