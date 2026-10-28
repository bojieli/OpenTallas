#!/bin/bash
# DIE-S81-7: dump_hb (QC-5) on the gate STA form (no --count-align: intra classes only) + hold_hist.py.  usage: hh.sh V
set -u
V=$1; WT=/srv/opentallas-scratch2/claude/wt/die-s81-7; O=/srv/opentallas-scratch2/claude/die-s81-7; PR=$O/proof_$V
PL=/srv/opentallas-scratch2/claude/die-s81-5/plan_s5.json; D=$O/hh_$V; mkdir -p $D
python3 -I $WT/results/die_qc5_1028/scripts/dump_hb.py $WT/tools/die_plan $D/hb.pkl -- $PR --plan $PL --out $D/sta --cppr-lca \
  --clock-ocv table --clock-droop shared --clock-cal spice --droop-regions $PR/droop_regions.json --core-latency-ff 202.5 \
  --hold-buffers HB4 --landing-window-ps 416.5 > $D/sta.log 2>&1; echo DUMP_RC $?
grep -E "intra|SUMMARY" $D/sta.log | cut -c1-300
BASE=$(python3 -c "import json;F=json.load(open('$D/sta/die_sta_related.json'))['corners']['FF']['register'];print(F['clkq_min_nowire_ps']-F['hold_ps']-25.0)")
python3 -I $WT/results/die_s81_7_1028/scripts/hold_hist.py $WT/tools/die_plan $D/hb.pkl $PR $D/hold_hist.json $BASE | cut -c1-3000; echo HH_DONE
