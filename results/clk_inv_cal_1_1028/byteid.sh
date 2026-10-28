#!/bin/bash
# CLK-INV-CAL-1: BUFx24 byte-identity (main tools vs branch tools) on QC trial8 (BUF tree) + trial10 with --clock-cell buf
set -u
M=/srv/opentallas-scratch2/claude/clk-inv-cal-1-1028; B=$M/byteid; mkdir -p $B
W=/srv/opentallas-scratch2/claude/wt/clk-inv-cal-1; MT=$M/main_tools
rm -rf $MT; mkdir -p $MT; (cd $W && git archive origin/main tools/die_plan tools/s81_head | tar -x -C $MT)
CI=/srv/opentallas-scratch2/claude/codex-die-qc-0359-1028/build_inputs; PLAN=$CI/event/qc_k2b_phase12.json
R8=/srv/opentallas-scratch2/claude/die-qc10-1028/ca/t8; R10=/srv/opentallas-scratch2/claude/die-qc11-1028/ca/t10
for v in main new; do T=$([ $v = main ] && echo $MT/tools || echo $W/tools)
  python3 -I $T/s81_head/landed_phase_ocv.py $PLAN $R8/run --tools $T/die_plan --out $B/lpo8_$v.json > $B/lpo8_$v.log 2>&1 &
  F="--sta-proof $R8/proof --sta-plan $PLAN --sta-clock-cal spice --sta-cppr-lca --sta-clock-ocv table --sta-clock-droop shared --sta-droop-regions $R8/proof/droop_regions.json --sta-core-latency-ff 202.5"
  python3 $T/die_plan/count_align_plan.py $R8/grp_spice_xing_lpo.json $F --out $B/plan8_$v.json > $B/plan8_$v.log 2>&1 &
  python3 $T/die_plan/die_sta_related.py $R8/proof --plan $PLAN --out $B/sta8_$v --corner TT --corner FF --clock-ocv table --clock-droop shared --droop-regions $R8/proof/droop_regions.json --core-latency-ff 202.5 --hold-buffers none --cppr-lca --clock-cal spice > $B/sta8_$v.log 2>&1 &
  X=$([ $v = new ] && echo "--clock-cell buf" || echo "")
  python3 $T/die_plan/die_sta_related.py $R10/proof --plan $PLAN --out $B/sta10_$v --corner TT --corner FF --clock-ocv table --clock-droop shared --droop-regions $R10/proof/droop_regions.json --core-latency-ff 202.5 --hold-buffers none --cppr-lca --clock-cal spice --count-align $R10/bind_clock.json --count-align-key region $X > $B/sta10_$v.log 2>&1 &
done; wait
for f in lpo8 plan8; do cmp $B/${f}_main.json $B/${f}_new.json && echo "$f IDENTICAL"; done
for f in sta8 sta10; do for j in $(cd $B/${f}_main && ls *.json); do cmp <(grep -v '"timed_dir"\|"proof"' $B/${f}_main/$j) <(grep -v '"timed_dir"\|"proof"' $B/${f}_new/$j) >/dev/null && echo "$f/$j IDENTICAL" || echo "$f/$j DIFF"; done; done
echo BYTEID DONE $(date)
