#!/bin/bash
set -e
R=/srv/opentallas-scratch2/claude/codex-head-collect-1030/hb4_clock_candidate
K=/srv/opentallas-scratch2/claude/codex-head-collect-1030/hb4_dpl2_kit
test -s "$R/verify_candidate_v4.json"
python3 - "$R/verify_candidate_v4.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]));assert r['verdict']=='PASS' and r['unrooted_clock_pins']==0 and r['clock_cells_on_macros']==0 and r['max_center_leg_um']<=220
PY
# Preserve the actual fresh CTS input; the real imported ODB drives the signal GRT.
test ! -e "$K/pre_infra_4_cts.odb"
cp "$K/run/results/asap7/hbc_ot_s81hd_lep_pair/base/4_cts.odb" "$K/pre_infra_4_cts.odb"
cp "$R/4_cts_infra.odb" "$K/run/results/asap7/hbc_ot_s81hd_lep_pair/base/4_cts.odb"
cp "$R/clock_recipe.json" "$K/clock_infra_recipe.json"
mkdir -p "$K/g2_infra"
DK=docker;docker ps >/dev/null 2>&1 || DK='sudo docker'
$DK run --rm --name head-hb4-real-infra-grt-$$ --cpus=8 --memory=32g --memory-swap=32g -v "$K":/work -v /srv/opentallas-scratch2/claude/codex-head-collect-1030/clock_recipe.py:/clock_recipe.py:ro -e HUID=$(id -u) -e HGID=$(id -g) openroad/orfs:asap7lock bash -lc 'set -e;source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1;cd /OpenROAD-flow-scripts/flow
ACTION=verify INPUT_ODB=/work/run/results/asap7/hbc_ot_s81hd_lep_pair/base/4_cts.odb RECIPE=/work/clock_infra_recipe.json REPORT=/work/g2_infra/verify_before_grt.json openroad -python -exit /clock_recipe.py > /work/g2_infra/verify_before_grt.log 2>&1
python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/g2_infra/orfs_hold_mm.log 2>&1
python3 -I /work/kit_modes.py check /work --step grt --session "tc bc" --hold-repair > /work/g2_infra/kit_modes_grt.log 2>&1
set +e
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 grt HOLD_SLACK_MARGIN=10 > /work/g2_infra/run_grt.log 2>&1
rc=$?;echo "$rc" > /work/g2_infra/grt.rc
if test "$rc" = 0;then
 ACTION=verify INPUT_ODB=/work/run/results/asap7/hbc_ot_s81hd_lep_pair/base/5_1_grt.odb RECIPE=/work/clock_infra_recipe.json REPORT=/work/g2_infra/verify_after_grt.json openroad -python -exit /clock_recipe.py > /work/g2_infra/verify_after_grt.log 2>&1
 rc=$?
fi
chown -R $HUID:$HGID /work
exit $rc'
