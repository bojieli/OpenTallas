#!/bin/bash
set -e
R=/srv/opentallas-scratch2/claude/codex-head-collect-1030/serdes_reshape
K=$R/eco1b_kit
mkdir -p "$K/firstdrt"
cat > "$K/firstdrt_pre.tcl" <<'TCL'
source /work/clk_freeze.tcl
ot_clk_freeze /work/firstdrt
TCL
cat > "$K/firstdrt_post.tcl" <<'TCL'
ot_clk_dump /work/firstdrt/clk_after_drt.tsv after_drt
TCL
DK=docker
$DK ps >/dev/null 2>&1 || DK='sudo docker'
$DK run --rm --name head-serdes-eco1b-firstdrt-$$ --cpus=8 --memory=32g --memory-swap=32g -v "$K":/work -e HUID=$(id -u) -e HGID=$(id -g) openroad/orfs:asap7lock bash -lc 'set -e
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
cd /OpenROAD-flow-scripts/flow
set +e
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 do-5_2_route PRE_DETAIL_ROUTE_TCL=/work/firstdrt_pre.tcl POST_DETAIL_ROUTE_TCL=/work/firstdrt_post.tcl > /work/firstdrt/run_drt.log 2>&1
rc=$?;echo $rc > /work/firstdrt/drt.rc
if test $rc = 0;then
 python3 -I /work/clk_geom_diff.py /work/firstdrt/clk_freeze_pre.tsv /work/firstdrt/clk_after_drt.tsv --pre-unrouted --json /work/firstdrt/clock_diff.json > /work/firstdrt/clock_diff.log 2>&1
 rc=$?
fi
if test $rc = 0;then
 make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 do-5_3_fillcell do-5_route do-5_route.sdc do-finish > /work/firstdrt/run_finish.log 2>&1
 rc=$?;echo $rc > /work/firstdrt/finish.rc
fi
if test $rc = 0;then
 ODB=/work/run/results/asap7/hbc_ot_s81_kp4_dchn/base/6_final.odb PINS=/work/pins.json OUT=/work/firstdrt/pin_audit.json openroad -python -exit /work/pin_audit_core.py > /work/firstdrt/pin_audit.log 2>&1
 rc=$?
fi
chown -R $HUID:$HGID /work
exit $rc'
rc=$?
if test $rc = 0;then
 SIGNOFF_DOCKER=$DK python3 -I "$K/signoff.py" run --run-dir "$K/run" --kit "$K" --out "$K/signoff_firstdrt" --image openroad/orfs:asap7lock --corners tt,ff > "$K/firstdrt/signoff.log" 2>&1
fi
