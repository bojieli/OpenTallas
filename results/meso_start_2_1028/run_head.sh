#!/bin/bash
# MESO-START-2: HEAD sp5 part (DIE-HEAD-5 ival uni_lca form: --sta-proof proof_lca, spice, cppr-lca) with/without --start-skew-clean
set -u
T=/srv/opentallas-scratch2/claude/meso-start-2/tools/die_plan; N=/srv/opentallas-scratch2/claude/nc-headpart; R=/srv/opentallas-scratch2/claude/meso-start-2/head
P=/srv/opentallas-scratch2/claude/die-head-5/ival/proof_lca; J=/srv/opentallas-scratch2/claude/wt/die-head-1/physical/die_plan/s81_head/die_plan.json
V=$1; shift
X="--start-skew 40.9,89.7 --sta-proof $P --sta-plan $J --sta-clock-cal spice --sta-cppr-lca"
python3 $T/count_align_plan.py $N/ca/ocv_dh3_spice.json --mc-chips 2000 $X "$@" --out $R/plan_$V.json > $R/plan_$V.log 2>&1; echo plan rc=$? $V
python3 $T/count_align_bind.py $R/plan_$V.json --out $R/bind_$V.json > $R/bind_$V.log 2>&1; echo bind rc=$? $V
python3 $T/die_sta_related.py $P --plan $J --out $R/sta_$V --corner TT --corner FF --core-latency-ff 202.5 --droop-regions $P/droop_regions.json --count-align $R/bind_$V.json --clock-cal spice --cppr-lca > $R/sta_$V.log 2>&1; echo sta rc=$? $V
grep "COUNT-ALIGN" $R/sta_$V.log
