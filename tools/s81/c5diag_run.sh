#!/bin/bash
# c5 congestion diagnosis run (2026-10-13, EPYC4 scratch copy of the c5 / c3 run data): c5diag_run.sh <case>
S=/srv/opentallas-scratch/claude/s81-c5-diag/cong; c=$1
exec ot-heavy --mem 24 -- python3 $S/tools/c5diag_congestion.py --case $S/$c --ov $S/out/$c/gcell_ov.txt --regions $S/out/$c/regions.json --out $S/out/$c/cong.json --cache $S/out/$c \
 --rect su_v13=13780.8,3369.6,15670.8,13392 --rect su_v11=13780.8,3369.6,15670.8,9439.2 --rect su_growth_v11_to_v13=13780.8,9439.2,15670.8,13392 \
 --rect sm_column_v13=13780.8,3391.2,15012,12009.6 --rect hub_W_stack_N_of_su_v13=13942.8,13392,15670.8,21400 \
 --rect vch_all=15670.8,3257.3,17312.4,22745 --rect vch_E_strip_N=16800,14083.2,17312.4,24000 --rect vch_E_strip_S=16800,3257.3,17312.4,14083.2 \
 --rect hc_s_v13=17312.4,14083.2,19128.96,22433 --rect hc_t_v13=17312.4,3680.64,19128.96,12571.2 --rect corridor_v13=17312.4,12571.2,19128.96,14083.2 \
 --rect corridor_v11=17312.4,8618.4,19128.96,10130.4 --rect hc_column_all=17312.4,3257.3,19128.96,22762 --rect hub_E_gap=19128.96,3257.3,19559,22745 \
 --rect hub_W_gap=13424,3257.3,13780.8,22745 --rect ctrl_svc_pinch=6720,960,8160,1920 --rect band_N_hub=13872,22745,19142,24535 --rect band_S_hub=13872,1200,19142,3257.3 \
 --focus 'wq_d=hc_s_wq_d' --focus 'hc_y=hc_y_' --focus 'hc_chains=hc_s_wq_d|hc_y_' --focus 'ctrl_svc=^n_(rq|rd|wd)_SW' --focus 'xlane=^n_x[ab]_#_#$' --focus 'qbank_eb=^n_x[ab]_#_#_e#_eb' \
 --focus 'at_sp_hc_s=ep:sp_hc_s\.' --focus 'at_sp_hc_t=ep:sp_hc_t\.' --focus 'at_sp_su_s=ep:sp_su_s\.' --focus 'at_sp_vm=ep:sp_vm\.' --focus 'at_sp_collective=ep:sp_collective\.'
