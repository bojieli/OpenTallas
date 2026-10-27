#!/bin/bash
# QC-CORES-2 btab_m0_r8 chain: CTS (mscts_spec_r8 = no-pad sized + trunk) + GRT -> DRT + fill + report (RCX) -> warm hold ECO
# (ELEM-QK recipe b, same as rst3 K0: FF-only data-path hold buffers, 12.4a1) -> signoff.py tt,ff -> main lec.py on the routed
# 6_final.v.  No clock edits after the plan.
set -uo pipefail
K=$(cd "$(dirname "$0")" && pwd); HK=$K/hold_b; S=/srv/opentallas-scratch2/claude/qc-cores/hold/su8_b
LECM=/srv/opentallas-scratch2/claude/qccores1-1027/lec/rst3; IMG=openroad/orfs:asap7lock
st() { echo "R8 $1 $(date -Is)" | tee -a $K/chain_r8.txt; }
M='make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8'
st "start"
docker run --rm --name btr8-cts-$$ --cpus=8 --memory=28g --memory-swap=28g -v "$K":/work -w /OpenROAD-flow-scripts/flow $IMG bash -lc \
  "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; $M do-cts && $M do-5_1_grt; rc=\$?; chown -R $(id -u):$(id -g) /work/run; exit \$rc" > $K/cts_grt.log 2>&1; rc=$?
st "CTS_GRT rc $rc $(grep -h R8_CLKPORT $K/cts_grt.log | tr '\n' ' ') $(cat $K/s5_grt_tt.txt 2>/dev/null)"; [ $rc = 0 ] || exit 3
docker run --rm --name btr8-rt-$$ --cpus=8 --memory=24g --memory-swap=24g -v "$K":/work -w /OpenROAD-flow-scripts/flow $IMG bash -lc \
  "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; rc=0; for t in do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc do-6_1_fill do-6_1_fill.sdc do-6_report; do $M \$t || { rc=\$?; echo STAGE_FAIL \$t rc \$rc; break; }; done; chown -R $(id -u):$(id -g) /work/run; exit \$rc" > $K/route_r8.log 2>&1; rc=$?
st "ROUTE rc $rc $(grep -h 'Number of violations' $K/route_r8.log | tail -1)"; [ $rc = 0 ] || exit 4
RS=$(ls -d $K/run/results/asap7/*/base); NICK=$(basename $(dirname $RS))
rm -rf $HK; mkdir -p $HK; rsync -a --exclude run --exclude signoff --exclude hold_b $K/ $HK/
cp $S/hold_route.tcl $S/variant.env $HK/; rsync -a $S/so/ $HK/so/
printf '# QC-CORES-2 warm hold ECO (ELEM-QK recipe b: FF-only data-path hold buffers, margin 3; 12.4a1)\nexport POST_GLOBAL_ROUTE_TCL = /work/hold_route.tcl\n' >> $HK/config.mk
H=$HK/run/results/asap7/$NICK/base; mkdir -p $H $HK/run/logs/asap7/$NICK/base $HK/run/reports/asap7/$NICK/base $HK/run/objects/asap7/$NICK/base
cp -p $RS/5_2_route.odb $H/4_cts.odb; cp -p $RS/6_final.spef $RS/1_2_yosys.v $RS/clock_period.txt $H/ 2>/dev/null
rsync -a $K/run/objects/asap7/$NICK/base/ $HK/run/objects/asap7/$NICK/base/ 2>/dev/null || true
{ cat $HK/constraint.sdc; echo 'set_propagated_clock [get_clocks clk]'; } > $H/4_cts.sdc
. $HK/variant.env
st "hold start"
docker run --rm --name btr8-hold-$$ --cpus=16 --memory=32g --memory-swap=32g -v "$HK":/work -e OT_HOLD_MARGIN=$OT_HOLD_MARGIN \
  -e OT_HOLD_ALLOW_SETUP=$OT_HOLD_ALLOW_SETUP -e OT_HOLD_MAXBUF=$OT_HOLD_MAXBUF -w /OpenROAD-flow-scripts/flow $IMG bash -lc \
  "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; M='make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=16'; \
   rc=0; for t in do-5_1_grt do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc do-6_1_fill do-6_1_fill.sdc do-6_report; do \$M \$t $ROUTE_CORNERS SKIP_INCREMENTAL_REPAIR=1 || { rc=\$?; echo STAGE_FAIL \$t rc \$rc; break; }; done; \
   chown -R $(id -u):$(id -g) /work; exit \$rc" > $HK/run_hold.log 2>&1; rc=$?
st "hold rc $rc $(grep -h ELEMQK_HOLD $HK/run/logs/asap7/*/base/5_1_grt.log 2>/dev/null | head -1) $(grep -h 'Inserted' $HK/run/logs/asap7/*/base/5_1_grt.log 2>/dev/null | head -1)"; [ $rc = 0 ] || exit 5
SIGNOFF_DOCKER=docker python3 -I $HK/so/tools/die_plan/signoff.py run --run-dir $HK/run --kit $HK --out $HK/signoff --corners tt,ff --image $IMG > $HK/signoff.log 2>&1; so=$?
st "signoff rc $so $(grep -h ^SIGNOFF $HK/signoff.log | head -1)"
docker run --rm -m 24g --cpus 8 -v $HK:/work:ro -v $H:/n:ro -v $LECM:/m:ro -v $K/lec_routed:/o $IMG bash -lc "mkdir -p /o; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /m/lec_main.py /work --netlist /n/6_final.v --out /o" > $K/lec_routed.log 2>&1; lr=$?
st "lec rc $lr $(tail -1 $K/lec_routed.log | cut -c1-200)"
st "CHAIN_DONE"
