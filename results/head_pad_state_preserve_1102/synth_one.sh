#!/usr/bin/env bash
# Runs inside openroad/orfs:asap7lock. Args: RUN_NAME MODE HOOK(kit|none|cellkeep)
set -euo pipefail
RUN_NAME=$1; MODE=$2; HOOK=$3
export COUPON=/coupon OUT=/out
export RUN_DIR=$OUT/$RUN_NAME RUN_NAME
rm -rf "$RUN_DIR"; mkdir -p "$RUN_DIR/src"
# fresh per-mode copy of the packet fragment: only the PRESERVE_MODE default changes
sed "s/parameter integer PRESERVE_MODE = 0 /parameter integer PRESERVE_MODE = $MODE /" $COUPON/prep/pad_fragment.sv > "$RUN_DIR/src/pad_fragment.sv"
grep -q "PRESERVE_MODE = $MODE " "$RUN_DIR/src/pad_fragment.sv"
# OT_* hook knobs that must be absent in this coupon
unset OT_PIN_REGS OT_RST_LAND OT_KEEP_PIN_REGS OT_KEEP_WIRES OT_RST_COPIES_MAX OT_LANDING_FF OT_FSM_NONE_WIRES || true
test -f /work/ot_keep_regs.reference.tcl  # /work = ro mount of prep/ (hook source path)
EXTRA=()
case $HOOK in
  kit)      EXTRA=(SYNTH_CANONICALIZE_TCL=/work/ot_keep_regs.reference.tcl) ;;
  cellkeep_pkt) export OT_HEAD_PAD_KEEP_PROFILE=1; EXTRA=(SYNTH_CANONICALIZE_TCL=$COUPON/prep/generic_cell_keep_hook.tcl) ;;
  cellkeep) export OT_HEAD_PAD_KEEP_PROFILE=1; EXTRA=(SYNTH_CANONICALIZE_TCL=$COUPON/cell_keep_hook_1102.tcl) ;;
  none)     ;;
  *) echo bad hook; exit 2;;
esac
cd /OpenROAD-flow-scripts/flow
export HOME=/tmp
make DESIGN_CONFIG=$COUPON/config.mk WORK_HOME=$RUN_DIR/flow NUM_CORES=1 "${EXTRA[@]}" synth > "$RUN_DIR/make_synth.log" 2>&1 || { tail -40 "$RUN_DIR/make_synth.log"; exit 1; }
R=$RUN_DIR/flow/results/asap7/$RUN_NAME/base
ls $R
