#!/bin/bash
# KV-CORES 10-25 (rev. after COORD root-merge reject + owner rule 10-25 / KV ruling 5): the closing chain of a KV core kit is
#   route -> signoff -> classify.  NO post-route ECO stage: a run that does not sign off at route goes to visual review and a
#   STRUCTURAL fix (GEOM-REVIEW PASS, rebuild), never a hold-buffer / resize / LVT ECO.  Classification + archive/delete =
#   the AUTOPILOT (enqueue the kit with tools/autopilot/enqueue.py; this script is only for a run the autopilot adopts).
#   run_kit_kv.sh GOAL=route already runs the fail-closed sdc_lint / SELRANGE / raw+ODB face_guard (+ LEC on main) gates
#   before floorplan and signoff.py at the end.  Self-contained for ot-run --stage:
#   VR/<kit>   gen_core_kit_kv.py kit (--out VR)       VR/chain/  run_kit_kv.sh corners.tcl pin_audit_core.py
#                                                                   + so/tools/die_plan/{signoff,face_guard,sdc_lint}.py pair_skew.tcl
#   run_kit_chain.sh VR KITNAME [MEM_GB=32] [CPUS=16]
#   run_kit_chain.sh --stage VR REPO          copy the chain tools from REPO into VR/chain (on the launch host)
set -uo pipefail
if [ "${1:-}" = --stage ]; then
  VR=$2; REPO=$3; H=$REPO/physical/die_plan/qwen_kvsys/cores/harden
  mkdir -p $VR/chain/so/tools/die_plan
  cp $H/run_kit_kv.sh $H/corners.tcl $H/pin_audit_core.py $VR/chain/
  cp $REPO/tools/die_plan/signoff.py $REPO/tools/die_plan/face_guard.py $REPO/tools/die_plan/sdc_lint.py \
     $REPO/tools/die_plan/pair_skew.tcl $VR/chain/so/tools/die_plan/
  cp "$0" $VR/chain/run_kit_chain.sh
  exit 0
fi
VR=$(cd "$1" && pwd); KIT=$VR/$2; MEM=${3:-32}; CPUS=${4:-16}
log() { echo "$(date "+%F %T %Z") $*" >> $VR/chain.txt; }
for f in pair_skew.tcl; do test -f $KIT/$f || cp $VR/chain/so/tools/die_plan/$f $KIT/ 2>/dev/null || true; done
log "route start $KIT on $(hostname)"
bash $KIT/run_kit_kv.sh $KIT route $MEM $CPUS; rc=$?
v=$(python3 -c "import json; print(json.load(open(\"$KIT/signoff/signoff.json\")).get(\"verdict\"))" 2>/dev/null || echo "no signoff.json")
log "route rc=$rc verdict=$v (no ECO stage: NOT SIGNED -> review + structural fix)"
exit $rc
