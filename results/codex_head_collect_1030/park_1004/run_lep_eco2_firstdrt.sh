#!/bin/bash
set -e
R=/srv/opentallas-scratch2/claude/codex-head-collect-1030
K=$R/lep_data_eco2_kit
O=$K/firstdrt
mkdir -p "$O/postroute_lock"
test -s "$O/geom_review.txt"
python3 - "$R/lep_eco2_pairs_v2" "$R/lep_data_eco2" <<'PY'
import json,sys
from pathlib import Path
for c in ('tt','ff'):
 d={}
 for l in (Path(sys.argv[1])/c/'pairs.tsv').read_text().splitlines():
  a=l.split('\t')
  if a[0]=='H':d[a[1]]=a[2:]
 assert int(d['pairs'][0])>0 and int(d['no_clock_arrival'][0])==0,d
 for mode in ('max','min'):
  assert float(d[mode+'_worst'][0])<=80 and float(d[mode+'_verify'][0])==0,d
  assert int(d[mode+'_nopath'][0])==0 and int(d[mode+'_bounded'][0])==0,d
for f in ('clock_diff.json','verify_clock_recipe.json'):
 assert json.load(open(Path(sys.argv[2])/f))['verdict']=='PASS'
PY
cat > "$K/firstdrt_pre.tcl" <<'TCL'
source /work/clk_freeze.tcl
ot_clk_freeze /work/firstdrt
TCL
cat > "$K/firstdrt_post.tcl" <<'TCL'
ot_clk_dump /work/firstdrt/clk_after_drt.tsv after_first_drt
# First routed clock wires become FIXED, byte-identical, before any future data ECO.
ot_clk_freeze /work/firstdrt/postroute_lock
ot_clk_dump /work/firstdrt/clk_after_fixed.tsv first_routed_clock_fixed
TCL
DK=docker
$DK ps >/dev/null 2>&1 || DK='sudo docker'
$DK run --rm --name head-lep-eco2-firstdrt-$$ --cpus=8 --memory=32g --memory-swap=32g -v "$K":/work -v "$R/clock_recipe.py":/clock_recipe.py:ro -e HUID=$(id -u) -e HGID=$(id -g) openroad/orfs:asap7lock bash -lc 'set -e
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
cd /OpenROAD-flow-scripts/flow
ACTION=verify INPUT_ODB=/work/run/results/asap7/hbc_ot_s81hd_lep_pair/base/5_1_grt.odb RECIPE=/work/clock_infra_recipe.json REPORT=/work/firstdrt/verify_before_drt.json openroad -python -exit /clock_recipe.py > /work/firstdrt/verify_before_drt.log 2>&1
set +e
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 do-5_2_route PRE_DETAIL_ROUTE_TCL=/work/firstdrt_pre.tcl POST_DETAIL_ROUTE_TCL=/work/firstdrt_post.tcl > /work/firstdrt/run_drt.log 2>&1
rc=$?;echo $rc > /work/firstdrt/drt.rc
if test $rc = 0;then
 python3 -I /work/clk_geom_diff.py /work/firstdrt/clk_freeze_pre.tsv /work/firstdrt/clk_after_fixed.tsv --pre-unrouted --json /work/firstdrt/clock_diff.json > /work/firstdrt/clock_diff.log 2>&1
 rc=$?
fi
if test $rc = 0;then
 python3 -I /work/clk_geom_diff.py /work/firstdrt/clk_after_drt.tsv /work/firstdrt/clk_after_fixed.tsv --json /work/firstdrt/wire_fixed_diff.json > /work/firstdrt/wire_fixed_diff.log 2>&1
 rc=$?
fi
if test $rc = 0;then
 ACTION=verify INPUT_ODB=/work/run/results/asap7/hbc_ot_s81hd_lep_pair/base/5_2_route.odb RECIPE=/work/clock_infra_recipe.json REPORT=/work/firstdrt/verify_after_drt.json openroad -python -exit /clock_recipe.py > /work/firstdrt/verify_after_drt.log 2>&1
 rc=$?
fi
if test $rc = 0;then
 make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 do-5_3_fillcell do-5_route do-5_route.sdc do-finish > /work/firstdrt/run_finish.log 2>&1
 rc=$?;echo $rc > /work/firstdrt/finish.rc
fi
if test $rc = 0;then
 ODB=/work/run/results/asap7/hbc_ot_s81hd_lep_pair/base/6_final.odb PINS=/work/pins.json OUT=/work/firstdrt/pin_audit.json openroad -python -exit /work/pin_audit_core.py > /work/firstdrt/pin_audit.log 2>&1
 rc=$?
fi
chown -R $HUID:$HGID /work
exit $rc'
if test $? = 0;then
 SIGNOFF_DOCKER=$DK python3 -I "$K/signoff.py" run --run-dir "$K/run" --kit "$K" --out "$K/signoff_firstdrt" --image openroad/orfs:asap7lock --corners tt,ff > "$O/signoff.log" 2>&1
fi
