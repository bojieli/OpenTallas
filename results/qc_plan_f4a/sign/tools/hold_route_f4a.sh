#!/bin/bash
# QC-SU-F4A-SIGN: FF-only data-path hold repair (hold_grt_f4a.tcl) -> DRT -> fill/final RCX/abstract/STA (finish_f4a.sh).
# Keeps the pre-hold GRT DB/guide as 5_1_grt_prehold.odb / route_prehold.guide.  usage: hold_route_f4a.sh KITDIR
set -uo pipefail
K=$(cd "$1" && pwd); H=$(dirname "$0"); H=$(cd "$H" && pwd)
HB=$(ls -d $K/run/results/asap7/*/base); B=/work/run/results/asap7/$(basename $(dirname $HB))/base
[ -f $HB/5_1_grt_prehold.odb ] || { cp $HB/5_1_grt.odb $HB/5_1_grt_prehold.odb; cp $HB/route.guide $HB/route_prehold.guide; }
cp $HB/5_1_grt_prehold.odb $HB/5_1_grt.odb; cp $HB/route_prehold.guide $HB/route.guide
FF=$(sed -n 's/^export OT_VCLK_FF = //p' $K/config.mk)
docker run --rm --name qcf4a-hold-$(basename $K)-$$ --cpus=8 --memory=16g --memory-swap=16g -v "$K":/work -v $H/hold_grt_f4a.tcl:/h.tcl:ro -w /work \
  -e RESULTS_DIR=$B -e OT_RC_CAL=0.8,0.9 -e OT_VCLK_FF=$FF -e OT_HOLD_MARGIN=${OT_HOLD_MARGIN:-15} openroad/orfs:asap7lock \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads 8 -exit /h.tcl" > $K/hold_f4a.log 2>&1 || { echo "hold step failed"; exit 4; }
docker run --rm -v "$K":/work openroad/orfs:asap7lock chown -R $(id -u):$(id -g) /work >/dev/null 2>&1
grep -q "HOLD_F4A_GATE PASS" $K/hold_f4a_gate.txt || { cat $K/hold_f4a_gate.txt; exit 6; }
rm -f $K/run/logs/asap7/*/base/5_2_route.json
$H/drt_f4a.sh $K || exit 7
$H/finish_f4a.sh $K || exit 8
# sign-off with the main tools (63f0898a3: pg + ft_interface checks) and LEC of the routed netlist 6_final.v (main lec.py)
M=/srv/opentallas-scratch2/claude/qc-plan-f4a-1026/main_63f0898a3/tools/die_plan
SIGNOFF_DOCKER=docker python3 -I $M/signoff.py run --run-dir $K/run --kit $K --corners tt,ff --ff-vclk auto --out $K/signoff_main --image openroad/orfs:asap7lock > $K/signoff_main.log 2>&1; so=$?
docker run --rm --memory=24g --memory-swap=24g --cpus=8 -v $K:/work -v $M:/m:ro openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /m/lec.py /work --netlist $B/6_final.v --out /work/lec_final" > $K/lec_final.log 2>&1; lr=$?
docker run --rm -v "$K":/work openroad/orfs:asap7lock chown -R $(id -u):$(id -g) /work >/dev/null 2>&1
echo "CHAIN_DONE signoff rc $so lec rc $lr $(date -Is)" | tee $K/chain_done.txt; grep -E '^SIGNOFF|^  - ' $K/signoff_main.log | head -12; tail -n 2 $K/lec_final.log
exit $so
