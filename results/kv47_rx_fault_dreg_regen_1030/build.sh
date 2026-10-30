#!/bin/bash
# DIE-KV-47-HR 10-30: RX fault_dreg regen kit = Codex rx259 kit (plan 259.2 outline, kit259sw pins incl. the 2 HELD
# pin deltas, rx259_pre_detail fault-site) with ONLY rtl/qkd_hr_core_rx.v swapped. Same chain as rx259:
# synth -> place -> cts -> grt (FF vclk, hold margin 10) -> route -> do-finish -> run_kit_kv.sh post (signoff.py).
set -uo pipefail
K=/srv/opentallas-scratch2/claude/die-kv-47-hr/rx/kit
st(){ echo "$(date "+%F %T %Z") $*" >> $K/kv47_status; }
st start
docker run --rm --name kv47hr-rx-build --cpus 8 --memory 40g --memory-swap 40g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; M="make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8"; rc=0
python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm.log 2>&1 || true
$M synth > /work/kv47_synth.log 2>&1 || rc=$?; echo "synth rc=$rc" >> /work/kv47_status
N=$(ls /work/run/results/asap7/*/base/1_2_yosys.v | tail -1)
if [ $rc = 0 ]; then python3 -I /work/core_preflight.py /work $N --out /work/face_guard.json > /work/face_guard.log 2>&1; echo "face_guard rc=$?" >> /work/kv47_status; fi
if [ $rc = 0 ]; then $M place > /work/kv47_place.log 2>&1 || rc=$?; echo "place rc=$rc" >> /work/kv47_status; fi
if [ $rc = 0 ]; then $M cts > /work/kv47_route.log 2>&1 && OT_VCLK_CORNER=ff $M grt HOLD_SLACK_MARGIN=10 >> /work/kv47_route.log 2>&1 || rc=$?; echo "cts+grt rc=$rc" >> /work/kv47_status; fi
if [ $rc = 0 ]; then $M route >> /work/kv47_route.log 2>&1 && $M do-finish >> /work/kv47_route.log 2>&1 || rc=$?; echo "route+finish rc=$rc" >> /work/kv47_status; fi
chown -R 1000:1000 /work; exit $rc'
rc=$?; st "chain rc=$rc"
if [ $rc = 0 ]; then bash $K/run_kit_kv.sh $K post 32 8 > $K/kv47_post.log 2>&1; st "post rc=$?"; fi
