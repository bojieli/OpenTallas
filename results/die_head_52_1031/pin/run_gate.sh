#!/bin/bash
# DIE-HEAD-52 helper pin: HEAD 12.25 die gate = sta/run_single.sh form, die_sta_related from claude/dh52-gate-1031 (main bfdc480ffc7 + --ca-write-fall)
# usage: run_gate.sh OUT PLAN [extra flags]
set -u; S=/srv/opentallas-scratch2/claude/die-head-47; R=/srv/opentallas-scratch2/claude/die-head-48; D=$R/sta; V=$S/mt/results/die_head_1027/views
T=/srv/opentallas-scratch2/claude/wt/dh52-gate/tools/die_plan
O=$1; PL=$2; shift 2; rm -rf $O; mkdir -p $O
python3 $T/die_sta_related.py $R/clk_st51/proof_l48w_sth --plan $PL --out $O --corner TT --corner FF --cppr-lca --clock-cell inv --margin-policy nominal --nominal-arrival single --hold-buffers HB4 --core-latency-ff 342 --core-view ot_s81hd_elemA_cv=$V/ot_s81hd_elemA_cv --core-view ot_s81hd_elemB_cv=$V/ot_s81hd_elemB_cv --count-align $R/clk_st51/bind_l48w_dm700.json --count-align-key part --ca-ring $D/ca_ring_hd_tile.json "$@" > $O.log 2>&1; echo rc $? >> $O.log
