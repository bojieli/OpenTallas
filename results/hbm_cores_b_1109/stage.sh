#!/bin/bash
# DIE-S81-81 stage runner, same container recipe as run_cts_targeted_1113.sh. $1 = kit, $2 = stage (grt|route)
K=$1; S=$2
if [ "$S" = grt ]; then CMDS='$M do-5_1_grt'; else CMDS='$M do-5_2_route && $M do-5_3_fillcell && $M do-5_route && $M do-5_route.sdc && $M do-finish && $M do-generate_abstract; rc=$?; F=$(ls /work/run/results/asap7/*/base/6_final.odb 2>/dev/null | tail -1); if [ -n "$F" ]; then ODB=$F PINS=/work/pins.json OUT=/work/pin_audit.json openroad -python -exit /work/pin_audit.py || rc=1; for c in TT FF; do OT_CORNER=$c DESIGN_NAME=$(sed -n "s/^export DESIGN_NAME = //p" /work/config.mk) ODB=$F SPEF=${F%.odb}.spef openroad -exit /work/corners.tcl > /work/sta_$c.log 2>&1; done; fi; exit $rc'; fi
docker run --rm --name ds81-bf-tgt-$S-$$ --memory 40g --memory-swap 40g --cpus 16 -v "$K:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl >/work/orfs_hold_mm.log 2>&1; M='make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=16'; $CMDS" > "$K/run_${S}_81.log" 2>&1
rc=$?
docker run --rm -v "$K":/work openroad/orfs:asap7lock chown -R $(id -u):$(id -g) /work >/dev/null 2>&1
echo STAGE_RC $S $rc; tail -3 "$K/run_${S}_81.log" | cut -c1-200
if [ "$S" = route ] && [ "$rc" = 0 ]; then SIGNOFF_DOCKER=docker python3 -I "$K/signoff.py" run --run-dir "$K/run" --kit "$K" --corners tt,ff --out "$K/signoff" --image openroad/orfs:asap7lock > "$K/signoff.log" 2>&1; rc=$?; grep -E '^SIGNOFF|^  - ' "$K/signoff.log" | head -12 | cut -c1-200; fi
exit $rc
