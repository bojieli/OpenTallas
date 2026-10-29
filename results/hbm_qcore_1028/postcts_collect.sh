#!/bin/bash
set -uo pipefail
cd /srv/opentallas-scratch2/claude/codex-qcore-m7-1029
pids=();names=()
for c in TT FF;do
 docker run --rm --name "codex-qcore-m7-post-$c" --cpus=2 --memory=8g --memory-swap=8g -v "$PWD/kit":/work -w /OpenROAD-flow-scripts/flow -e OT_CORNER="$c" -e ODB=/work/run/results/asap7/hbc_ot_hbm_su_static_qcore_r13/base/4_cts.odb -e PLATFORM_DIR=/OpenROAD-flow-scripts/flow/platforms/asap7 openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /work/postcts_gate.tcl' > "postcts_$c.log" 2>&1 &
 pids+=("$!");names+=("$c")
done
docker run --rm --name codex-qcore-m7-post-hold --cpus=2 --memory=8g --memory-swap=8g -v "$PWD/kit":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
 source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
 qcore_ff_libs=$(make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base print-BC_LIB_FILES 2>/dev/null | sed -n "s/^BC_LIB_FILES *[:=] *//p")
 PLIBS="$qcore_ff_libs" ODB=/work/run/results/asap7/hbc_ot_hbm_su_static_qcore_r13/base/4_cts.odb SDC=/work/run/results/asap7/hbc_ot_hbm_su_static_qcore_r13/base/4_cts.sdc OT_VCLK_TT=250 OT_VCLK_FF=202.5 PLATFORM_DIR=/OpenROAD-flow-scripts/flow/platforms/asap7 LAYER_PARASITICS_FILE=/work/setRC_rcx.tcl openroad -exit /work/hold_gate.tcl
' > postcts_hold.log 2>&1 &
pids+=("$!");names+=(hold)
bash /srv/opentallas-scratch2/claude/hbm-cores-kits-5/aptools/geom_check.sh "$PWD/geom_cts" > postcts_geom.log 2>&1 &
pids+=("$!");names+=(geom)
: > postcts_status.txt
for i in "${!pids[@]}";do
 wait "${pids[$i]}";rc=$?
 echo "${names[$i]} $rc" | tee -a postcts_status.txt
done
echo POSTCTS_COLLECTION_DONE_individual_verdicts_preserved
