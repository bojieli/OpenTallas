#!/bin/bash
# Gated stage clock spine with synchronised crossings (2026-10-04): route ot_v41_rom_stage_q_pg_cdc_w10 with K elements
# (K = 1: one q-frame C, the element-level vehicle against route R4/R5; K = 4: a 2 x 2 stage of q-frames sharing one
# controller, spine gate and always-on branch), same flow family as results/rtl/rom_stage_spine_gate_20261004/launch.sh.
# usage: WT=<pinned worktree> RUN=<name> K=<1|4> launch.sh
set -e
: "${WT:?pinned worktree}" "${RUN:?run name}" "${K:?elements}"
J=${OT_SPINE_JOB_ROOT:-/srv/opentallas-scratch/claude/spine-cdc/jobs}/$RUN
mkdir -p $J
cd $WT
test -z "$(git status --porcelain)" || { echo "worktree not clean"; exit 2; }
if [ "$K" = 1 ]; then COLS=1; W=510.84; H=126.9; else COLS=2; W=1021.68; H=$(python3 -c "print(round(126.9*($K//2),2))"); fi
CH=$(python3 -c "print(round($H-0.27,2))"); XE=$(python3 -c "print(round($W*0.27,2))"); XF=$(python3 -c "print(round($W*0.73,2))")
REPIN=()
if [ "${OT_SPINE_REPIN_E1:-0}" = 1 ]; then
  [ "$K" = 1 ] || { echo "priced re-pin recipe is E1 K=1 only"; exit 2; }
  python3 - <<'PY'
import hashlib
import json
from pathlib import Path
m = json.loads(Path('results/rtl/rom_stage_spine_cdc_20261004/repin_E1/manifest.json').read_text())
bad = [p for p, h in m['required_rtl_sources'].items()
       if hashlib.sha256(Path(p).read_bytes()).hexdigest() != h]
if bad:
    raise SystemExit('Re-pin boundary calibration source mismatch; do not revert corrected RTL: ' + ', '.join(bad))
if not m.get('current_target_launch_ready', False):
    raise SystemExit('Re-pin not admitted by actual current IO budget: ' + m['status'])
PY
  REPIN=(--step-tcl PRE_IO_PLACEMENT=physical/abi3/rom_stage_cdc_repin_e1.tcl)
fi
export OT_ORFS_NUM_CORES=${OT_ORFS_NUM_CORES:-16}
[ "$OT_ORFS_NUM_CORES" -le 16 ] || { echo "new spine jobs require <=16 make workers"; exit 2; }
SRCS=""
for s in rtl/v41rom/ot_v41_rom_stage_pg_cdc.sv rtl/v41rom/ot_v41_stage_pg_sched.sv \
  rtl/chip/ot_chip_v41_pg_ctrl.sv rtl/v41rom/ot_v41_rom_elem_w10.sv \
  rtl/v41rom/ot_v41_bterm.sv rtl/v41rom/ot_v41_chain.sv rtl/v41rom/ot_v41_segtree.sv rtl/v41rom/ot_v41_bf16_lanes.sv \
  rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_cg.sv \
  rtl/proto/ot_fp32_add_rne_pipe.sv physical/asap7_memory_macros/ot_rom_8192x274_m8/ot_rom_8192x274_m8_bb.v \
  rtl/v41rom/ot_v41_fadd.sv rtl/common/ot_prefix.sv rtl/v41rom/ot_v41_bmul2.sv rtl/v41rom/ot_v41_bterm2_w10.sv \
  rtl/v41rom/ot_v41_chain2.sv rtl/v41rom/ot_v41_segtree2.sv rtl/v41rom/ot_v41_bf16_lanes2.sv \
  physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8_bb.v; do SRCS="$SRCS --source $s"; done
exec python3 tools/run_abi3_physical_aligned.py --macro-track-gate --macro-track-gate-record $J/macro_gate.json \
 --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited \
 --persistent-workdir $J/work --launch-receipt $J/receipt.json \
 --view asap7 --top ot_v41_rom_stage_q_pg_cdc_w10 $SRCS \
 --clock-period-ns 0.833 --clock-uncertainty-ns 0.06 --io-delay-fraction 0.2 --stages pnr \
 --die-area 0 0 $W $H --core-area 0 0.27 $W $CH --place-density 0.6 --macro-place-halo 2 2 \
 --pin-region "^(p|busy|fault|xs_q1|xs_e1|sw_).*=top:$XE-$XF" --pin-region "^(clk|aon_clk|rst|cfg|go|xs_v|xs_p|xs_b|xs_sv|xs_q0|xs_e0|sched).*=bottom:$XE-$XF" \
 --max-transition-ns 0.32 --slew-margin-percent 40 --hold-margin-ns 0.0 \
 --step-tcl POST_MACRO_PLACE=physical/abi3/rom_stage_cdc_place_k$K.tcl --step-tcl POST_DETAIL_PLACE=physical/abi3/check_pg_before_route.tcl "${REPIN[@]}" \
 --orfs-var PDN_TCL=/src/tools/chip_assembly/tcl/pdn_w10_elem_m7_ir.tcl --nickname-tag spine_cdc_${RUN}_20261004 \
 --output $J/out --sdc-append physical/abi3/v41_w10_elem_pp_multicycle.sdc \
 --sdc-append results/rtl/rom_stage_spine_cdc_20261004/cdc_clocks.sdc \
 --macro-view ot_rom_4096x274_m8=physical/asap7_memory_macros/ot_rom_4096x274_m8 \
 --param K=$K --param MTP=1 --param EARLY=1 --param NB=2 --param FAST=1 --param PP=1 \
 --orfs-var ROUTING_LAYER_ADJUSTMENT=0.22 --hold-corners WC,BC \
 --pnr-stop-after ${STOP:-finish} --orfs-corner WC --clock-uncertainty-hold-ns 0.025 \
 --core-input-delay-min-ns 0.36 --core-input-delay-max-ns 0.727 --output-delay-min-ns -0.322 --output-delay-max-ns -0.193 > $J/launch.log 2>&1
