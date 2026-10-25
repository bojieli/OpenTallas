#!/bin/bash
# KV-CORES 10-25: DEFAULT closing recipe for a new KV core kit (COORD 00:32): route (run_kit_kv.sh GOAL=route, incl. the
# fail-closed sdc_lint / SELRANGE / raw+ODB face_guard preflight before floorplan), then -- unless the route already says
# SIGNED -- the warm post-route ECO (mk_eco.sh m<N>: MCMM TT+FF setup+hold repair, fanout cap 24, slew margin 20) on the
# routed DB, then signoff.py.  Self-contained for ot-run --stage:
#   VR/<kit>            gen_core_kit_kv.py kit (--out VR)
#   VR/chain/           run_kit_kv.sh corners.tcl pin_audit_core.py + eco/{mk_eco.sh,run_eco.sh,eco_route.tcl,slew_nets.tcl}
#                       + so/tools/die_plan/{signoff,face_guard,sdc_lint}.py      (stage_chain() below fills it)
#   VR/eco_<variant>/   the ECO run (created here)
#   run_kit_chain.sh VR KITNAME ECO_VARIANT [MEM_GB=32] [CPUS=16]      env ECO_ENV="OT_DRV_LAST=1 OT_RETIME_LAST=1 ..."
#   run_kit_chain.sh --stage VR REPO          copy the chain tools from REPO into VR/chain (on the launch host)
set -uo pipefail
if [ "${1:-}" = --stage ]; then
  VR=$2; REPO=$3; H=$REPO/physical/die_plan/qwen_kvsys/cores/harden
  mkdir -p $VR/chain/eco $VR/chain/so/tools/die_plan
  cp $H/run_kit_kv.sh $H/corners.tcl $H/pin_audit_core.py $VR/chain/
  cp $H/eco/mk_eco.sh $H/eco/run_eco.sh $H/eco/eco_route.tcl $H/eco/slew_nets.tcl $VR/chain/eco/
  cp $REPO/tools/die_plan/signoff.py $REPO/tools/die_plan/face_guard.py $REPO/tools/die_plan/sdc_lint.py $VR/chain/so/tools/die_plan/
  cp "$0" $VR/chain/run_kit_chain.sh
  exit 0
fi
VR=$(cd "$1" && pwd); KIT=$VR/$2; V=$3; MEM=${4:-32}; CPUS=${5:-16}; C=$VR/chain
log() { echo "$(date '+%F %T %Z') $*" >> $VR/chain.txt; }
signed() { python3 -c "import json,sys; sys.exit(0 if json.load(open('$1')).get('verdict')=='SIGNED' else 1)" 2>/dev/null; }
log "route start $KIT on $(hostname)"
bash $KIT/run_kit_kv.sh $KIT route $MEM $CPUS; rc=$?
log "route rc=$rc"
signed $KIT/signoff/signoff.json && { log "SIGNED at route"; exit 0; }
RS=$(ls -d $KIT/run/results/asap7/*/base 2>/dev/null | head -1)
if [ ! -f "$RS/5_2_route.odb" ] || [ ! -f "$RS/6_final.spef" ]; then log "no routed DB (preflight/route failure): stop"; exit ${rc:-1}; fi
E=$VR/eco_$V
env ${ECO_ENV:-} bash $C/eco/mk_eco.sh $KIT $E $V $C/so || { log "mk_eco failed"; exit 2; }
log "eco $V start (ECO_ENV='${ECO_ENV:-}')"
bash $C/eco/run_eco.sh $E $CPUS $MEM; rc=$?
log "eco rc=$rc"
signed $E/signoff/signoff.json && { log "SIGNED at eco_$V"; exit 0; }
exit ${rc:-1}
