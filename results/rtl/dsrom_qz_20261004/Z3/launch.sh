#!/bin/bash
# DSROM q-element QX route Z3 (2026-10-04, after Z2's post-GRT SS -118.8 ps in the word walker):
# results/rtl/dsrom_qy_20261004/launch.sh on ot_v41_rom_elem_q_qx_w10 with QX = 1 (walker step in one-hot form, zero
# added cycles).  Every other input (frame, SDC, I/O budgets, ROUTING_LAYER_ADJUSTMENT 0.22, hold corners) is unchanged.
# DSROM q-element QY route (2026-10-04, design-owner decision after Z1): results/rtl/dsrom_qz_20261004/launch.sh on
# ot_v41_rom_elem_q_qy_w10 (QZ = 1, QY = 1: zero added data cycles, L = 2; fault port +2 cycles), the corrected FF
# output hold budget (-0.322 ns, derivation in physical/abi3/dsrom_qy_elem_io.sdc), and ROUTING_LAYER_ADJUSTMENT 0.22
# (platform default 0.25; Z1 GRT-0116 left 6 overflow gcells on M5/M7).  Die and core area unchanged.
# DSROM q-element QZ physical run (2026-10-04): results/rtl/dsrom_qpipe_20261003/launch.sh (frame C, hook, SDC,
# multicycle, PDN, I/O delays, SS WC 0.833 ns, 60 / 25 ps, ADDER_MAP off, macro track gate) on ot_v41_rom_elem_q_qz_w10
# with QZ = 1 (zero added cycles over QPIPE R_cap0, L = 2), plus multi-corner hold repair (--hold-corners WC,BC:
# repair_timing fixes hold at FF as well as SS; R_cap0 repaired hold at SS only).  No constraint is changed.
# usage: WT=<pinned worktree> RUN=<name> [STOP=cts|finish] launch.sh   (CAP is fixed at 0)
# Original header:
# DSROM q-element QPIPE physical runs (2026-10-03).  usage: WT=<pinned worktree> RUN=<name> CAP=<0|1> [STOP=cts|finish] launch.sh
# Frame C (510.84 x 126.9 um, the q-frame baseline), its track-aligned macro hook, SDC / multicycle / PDN / I/O delays
# identical to the QTIMING screens (results/rtl/dsrom_qtiming_20261003/launch_screen.sh) and the q-frame routes,
# SS (ORFS WC) 0.833 ns, 60 ps setup / 25 ps hold uncertainty, ADDER_MAP_FILE disabled (driver default), launched
# through the macro track-alignment gate (tools/run_abi3_physical_aligned.py --macro-track-gate).
set -e
: "${WT:?pinned worktree}" "${RUN:?run name}"
CAP=0
J=/srv/opentallas-scratch/claude/dsrom-qtclose/jobs/$RUN
mkdir -p $J
cd $WT
test -z "$(git status --porcelain)" || { echo "worktree not clean"; exit 2; }
STOP=${STOP:-finish}
SRCS=""
for s in rtl/v41rom/ot_v41_rom_elem_q_qx_w10.sv rtl/v41rom/ot_v41_rom_elem_qx_w10.sv rtl/v41rom/ot_v41_kreg.sv \
  rtl/v41rom/ot_v41_chain3.sv rtl/v41rom/ot_v41_rom_elem_w10.sv \
  rtl/v41rom/ot_v41_bterm.sv rtl/v41rom/ot_v41_chain.sv rtl/v41rom/ot_v41_segtree.sv rtl/v41rom/ot_v41_bf16_lanes.sv \
  rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_cg.sv \
  rtl/proto/ot_fp32_add_rne_pipe.sv physical/asap7_memory_macros/ot_rom_8192x274_m8/ot_rom_8192x274_m8_bb.v \
  rtl/v41rom/ot_v41_fadd.sv rtl/common/ot_prefix.sv rtl/v41rom/ot_v41_bterm2_w10.sv rtl/v41rom/ot_v41_chain2.sv \
  rtl/v41rom/ot_v41_segtree2.sv rtl/v41rom/ot_v41_bf16_lanes2.sv rtl/v41rom/ot_v41_bterm3_w10.sv rtl/v41rom/ot_v41_segtree3.sv \
  physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8_bb.v; do SRCS="$SRCS --source $s"; done
exec python3 tools/run_abi3_physical_aligned.py --macro-track-gate --macro-track-gate-record $J/macro_gate.json \
 --persistent-workdir $J/work --launch-receipt $J/receipt.json \
 --view asap7 --top ot_v41_rom_elem_q_qx_w10 $SRCS \
 --clock-period-ns 0.833 --clock-uncertainty-ns 0.06 --io-delay-fraction 0.2 --stages pnr \
 --die-area 0 0 510.84 126.9 --core-area 0 0.27 510.84 126.63 --place-density 0.6 --macro-place-halo 2 2 \
 --pin-region "^(p|busy|fault|xs_q1|xs_e1).*=top:136.08-374.76" --pin-region "^(clk|rst|cfg|go|xs_v|xs_p|xs_b|xs_sv|xs_q0|xs_e0).*=bottom:136.08-374.76" \
 --max-transition-ns 0.32 --slew-margin-percent 40 --hold-margin-ns 0.0 \
 --step-tcl POST_MACRO_PLACE=physical/abi3/dsrom_qtiming_C_place.tcl --step-tcl POST_DETAIL_PLACE=physical/abi3/check_pg_before_route.tcl \
 --orfs-var PDN_TCL=/src/tools/chip_assembly/tcl/pdn_w10_elem_m7_ir.tcl --nickname-tag dsrom_qx_${RUN}_20261004 \
 --output $J/out --sdc-append physical/abi3/dsrom_qy_elem_io.sdc \
 --macro-view ot_rom_4096x274_m8=physical/asap7_memory_macros/ot_rom_4096x274_m8 \
 --param MTP=1 --param EARLY=1 --param NB=2 --param FAST=1 --param PP=1 --param QTIMING_FIX=1 \
 --param QPIPE=1 --param QP_XS=1 --param QP_CAP=$CAP --param QP_P1=1 --param QP_CSAM=10 \
 --param QZ=1 --param QZ_NS=8 --param QZ_NE=4 --param QY=1 --param QX=1 --orfs-var ROUTING_LAYER_ADJUSTMENT=0.22 --hold-corners WC,BC \
 --pnr-stop-after $STOP --orfs-corner WC --clock-uncertainty-hold-ns 0.025 \
 --core-input-delay-min-ns 0.36 --core-input-delay-max-ns 0.727 --output-delay-min-ns -0.322 --output-delay-max-ns -0.193 > $J/launch.log 2>&1
