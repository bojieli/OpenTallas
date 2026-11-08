#!/bin/bash
# HBM-HARD-6-TOPK vE (11-08): vD geometry (macro table results/die_hbm_1107/topk_vD/vD_macro_placement.json, M6, util 0.30)
# + recipe ev74_pd3w_nq (ingest NQ=1) + drive basis for the measured GRT->RCX gap (SLEW/CAP margin 35 %, max fanout 24,
# setup margin 40 ps at GRT repair) + GRT hold repair scope reg2reg (port hold = NEEDS_PARENT, was 3.3 h of port padding).
# usage: gen_vE.sh <repo> <out dir>
set -e
R=$1; OUT=$2
cd $R
python3 physical/die_plan/hbm_arch_cores/gen_core_kit_hbm_rw.py --views results/die_hbm_1108/topk_vE/core_views.347ae56f82.json --view 'ot_hbm_idx_topk_link_static@fa4a6c51ad35' --out $OUT --clock-pin-entry on --core-macros auto --recipe-key ot_hbm_idx_topk_link_static__ev74_pd3w_nq --util 0.30 --sigmax M6 --macro-placement results/die_hbm_1107/topk_vD/vD_macro_placement.json --macro-inst-fmt 'u_core.u_sto.gm\[{k}\].mem' --tag _vE --slew-margin 35 --max-fanout 24 --orfs-var SETUP_SLACK_MARGIN=40 --orfs-var OT_HOLD_REPAIR_SCOPE=reg2reg
echo GEN_RC $?
