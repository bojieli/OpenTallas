#!/bin/bash
# DIE-RECHECK-1 (DO_NOT_COUNT): S81 clock-only die GRT + landing arrivals for one ot_clk kit variant, DS85 CLKDIE recipe
# (scripts copied from epyc8 die-s81-85/clkdie/scripts, read-only inputs: DS85 per-type clock views + bind copy).
#   post_kit.sh VARIANT       (kit in s81/ck_VARIANT/kit)
set -uo pipefail
V=$1
W=/srv/opentallas-scratch2/claude/die-recheck-1
S=$W/s81/ds85_scripts
DS=/srv/opentallas-scratch2/claude/die-s81-85/clkdie
PLAN=$W/src/physical/die_plan/s81/plan_h2_2249.json
TOOLS=$W/src/tools/die_plan
K=$W/s81/ck_$V/kit
C=$W/s81/clock_$V
R=$W/s81/route_$V
O=$W/s81/out_$V
mkdir -p $R $O
$S/pyrun $S/ds85_clockdir.py $K/clock $C > $O/clockdir.json || exit 11
$S/pyrun $S/ds85_combo.py $K $C $R --plan $PLAN --tools $TOOLS > $O/combo.json || exit 12
image=openroad/orfs:asap7lock
docker image inspect "$image" --format '{{.Id}}' > "$R/route_image.txt"
for c in TT FF; do
  docker run --rm --name recheck1-s81-$V-$c --memory=128g --cpus=16 \
    -v "$K:/work:ro" -v "$C:/clock:ro" -v "$R:/out" \
    -e CORNER=$c -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM "$image" \
    bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -no_init -exit -threads 16 /out/combo.tcl' \
    > "$R/combo_$c.log" 2>&1 &
done
wait
grep -h OT_DONE "$R"/combo_*.log
$S/pyrun $S/ds85_arrivals.py --plan $PLAN --bind $DS/bindcopy/bind_clock_landings.json --route $R \
  --tree $K/clock/tree.json --types $DS/types $DS/types_cts --tools $TOOLS --out $O/arrivals.json \
  --detail $O/arrivals_detail.json > $O/arrivals.log 2>&1 || exit 13
$S/pyrun $S/landing_phase_sign_aa94bf3064.py $DS/bindcopy --arrivals $O/arrivals.json --out $O/lps.json \
  --tsv $O/lps.tsv > $O/lps.log 2>&1 || exit 14
$S/pyrun $S/ds85_report.py $O/lps.json $O/arrivals_detail.json $O/report.json > $O/report.log 2>&1 || exit 15
# die related-pair STA (12.4a / 12.25 / 12.24b nominal), declared budgets + plan per-tap core insertion (no kits)
PR=$W/s81/proof_$V; mkdir -p $PR
for c in TT FF; do python3 -s $TOOLS/trial_tap_arrivals.py $K/clock/tree.json $R/arr_$c.txt $c $PR/tap_arrivals_$c.json --physical-paths || exit 16; done
( cd $TOOLS && python3 -s die_sta_related.py $PR --plan $PLAN --out $W/s81/sta_$V --corner TT --corner FF --core-insertion declared ) > $W/s81/sta_$V.log 2>&1 || exit 17
python3 -I $W/scripts/s81_metrics.py $PLAN $R $O $K/clock/tree.json --label $V > $O/metrics.log 2>&1 || exit 18
echo POST_DONE $V
