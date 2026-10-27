#!/bin/bash
# QC-CORES-1 10-27: rebuild qfd_dv_s5_su8_rst3 with the lane-0 dead-replica RTL fix, SAME recipe as the retired
# signed view: kits3 base kit (run_kit.sh finish) -> warm hold ECO variant b (ELEM-QK: FF-only, margin 3, maxbuf 40,
# from the completed 5_2_route) -> signoff.py tt,ff -> main lec.py on the routed 6_final.v.
set -uo pipefail
R=$(cd "$(dirname "$0")" && pwd); BK=$R/base; HK=$R/hold_b; S=/srv/opentallas-scratch2/claude/qc-cores/hold/su8_b
st() { echo "RST3K0 $1 $(date -Is)" | tee -a $R/chain.txt; }
st "start base finish"
bash $BK/run_kit.sh $BK finish 32 16 > $R/base_run.out 2>&1; rc=$?
st "base rc $rc $(grep -h ^SIGNOFF $BK/signoff.log 2>/dev/null | head -1)"
RS=$(ls -d $BK/run/results/asap7/*/base); NICK=$(basename $(dirname $RS))
[ -s $RS/5_2_route.odb ] && [ -s $RS/6_final.spef ] || { st "FAIL no base route"; exit 7; }
rm -rf $HK; mkdir -p $HK; rsync -a --exclude run --exclude signoff --exclude views $BK/ $HK/
cp $S/hold_route.tcl $S/variant.env $HK/; rsync -a $S/so/ $HK/so/
printf '# QC-CORES warm hold ECO (ELEM-QK recipe b: FF-only, hold margin 3)\nexport POST_GLOBAL_ROUTE_TCL = /work/hold_route.tcl\n' >> $HK/config.mk
H=$HK/run/results/asap7/$NICK/base; mkdir -p $H $HK/run/logs/asap7/$NICK/base $HK/run/reports/asap7/$NICK/base $HK/run/objects/asap7/$NICK/base
cp -p $RS/5_2_route.odb $H/4_cts.odb; cp -p $RS/6_final.spef $RS/1_2_yosys.v $RS/clock_period.txt $H/
rsync -a $BK/run/objects/asap7/$NICK/base/ $HK/run/objects/asap7/$NICK/base/ 2>/dev/null || true
{ cat $HK/constraint.sdc; echo 'set_propagated_clock [get_clocks clk]'; } > $H/4_cts.sdc
printf '{"source_kit": "%s", "source_route": "%s/5_2_route.odb", "recipe": "ELEM-QK hold_eco b", "margin_ps": 3, "rtl_fix": "QC-CORES-1 lane0 dead replicas"}\n' $BK $RS > $HK/HOLD_ECO.json
. $HK/variant.env
st "hold start"
docker run --rm --name qccores1-rst3hold-$$ --cpus=16 --memory=32g --memory-swap=32g -v "$HK":/work \
  -e HUID=$(id -u) -e HGID=$(id -g) -e OT_HOLD_MARGIN=$OT_HOLD_MARGIN -e OT_HOLD_ALLOW_SETUP=$OT_HOLD_ALLOW_SETUP \
  -e OT_HOLD_MAXBUF=$OT_HOLD_MAXBUF -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
  M='make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=16'; \
  \$M do-route $ROUTE_CORNERS SKIP_INCREMENTAL_REPAIR=1; rc=\$?; if [ \$rc = 0 ]; then \$M do-finish; rc=\$?; fi; \
  F=\$(ls /work/run/results/asap7/*/base/6_final.odb 2>/dev/null | tail -1); \
  if [ -n \"\$F\" ]; then ODB=\$F PINS=/work/pins.json OUT=/work/pin_audit.json openroad -python -exit /work/pin_audit.py; fi; \
  chown -R \$HUID:\$HGID /work; exit \$rc" > $HK/run_hold.log 2>&1; rc=$?
st "hold rc $rc $(grep -h ELEMQK_HOLD $HK/run/logs/asap7/*/base/5_1_grt.log 2>/dev/null | head -1)"
[ $rc = 0 ] || exit 8
SIGNOFF_DOCKER=docker python3 -I $HK/so/tools/die_plan/signoff.py run --run-dir $HK/run --kit $HK --out $HK/signoff --corners tt,ff --image openroad/orfs:asap7lock > $HK/signoff.log 2>&1; so=$?
st "signoff rc $so $(grep -h ^SIGNOFF $HK/signoff.log | head -1)"
docker run --rm -m 24g --cpus 8 -v $HK:/work:ro -v $H:/n:ro -v $R/../lec/rst3:/m:ro -v $R/lec_routed:/o openroad/orfs:asap7lock bash -lc "mkdir -p /o; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /m/lec_main.py /work --netlist /n/6_final.v --out /o" > $R/lec_routed.log 2>&1; lr=$?
st "lec rc $lr $(tail -1 $R/lec_routed.log | cut -c1-200)"
st "CHAIN_DONE"
