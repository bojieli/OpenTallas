#!/bin/bash
# ROM stage power gating (2026-10-04): route the power-gated S81 element top ot_v41_rom_elem_q_pg_w10 (PG = 1, the element
# core BF16 = 0, NB = 2, MTP, EARLY, FAST, PP) in the DSROM q-frame C (510.84 x 126.9 um) with the q-frame track-aligned
# macro hook re-rooted (physical/abi3/rom_stage_pg_place.tcl), same SDC/multicycle/PDN/IO budget family as the
# q-element routes, so the gated domain and its always-on side get routed parasitics for gate-level power.
# usage: WT=<pinned worktree> RUN=<name> [STOP=finish] [PGV=1] launch.sh   (PGV=0: the same top ungated, the timing reference)
set -e
: "${WT:?pinned worktree}" "${RUN:?run name}"
J=/srv/opentallas-scratch/claude/rom-stage-pg/jobs/$RUN
mkdir -p $J
cd $WT
test -z "$(git status --porcelain)" || { echo "worktree not clean"; exit 2; }
SRCS=""
for s in rtl/v41rom/ot_v41_rom_elem_q_pg_w10.sv rtl/v41rom/ot_v41_rom_elem_pg_w10.sv rtl/v41rom/ot_v41_rom_pg_ao.sv rtl/v41rom/ot_v41_stage_pg_sched.sv \
  rtl/chip/ot_chip_v41_pg_ctrl.sv rtl/v41rom/ot_v41_rom_elem_w10.sv \
  rtl/v41rom/ot_v41_bterm.sv rtl/v41rom/ot_v41_chain.sv rtl/v41rom/ot_v41_segtree.sv rtl/v41rom/ot_v41_bf16_lanes.sv \
  rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_cg.sv \
  rtl/proto/ot_fp32_add_rne_pipe.sv physical/asap7_memory_macros/ot_rom_8192x274_m8/ot_rom_8192x274_m8_bb.v \
  rtl/v41rom/ot_v41_fadd.sv rtl/common/ot_prefix.sv rtl/v41rom/ot_v41_bmul2.sv rtl/v41rom/ot_v41_bterm2_w10.sv \
  rtl/v41rom/ot_v41_chain2.sv rtl/v41rom/ot_v41_segtree2.sv rtl/v41rom/ot_v41_bf16_lanes2.sv \
  physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8_bb.v; do SRCS="$SRCS --source $s"; done
exec python3 tools/run_abi3_physical_aligned.py --macro-track-gate --macro-track-gate-record $J/macro_gate.json \
 --persistent-workdir $J/work --launch-receipt $J/receipt.json \
 --view asap7 --top ot_v41_rom_elem_q_pg_w10 $SRCS \
 --clock-period-ns 0.833 --clock-uncertainty-ns 0.06 --io-delay-fraction 0.2 --stages pnr \
 --die-area 0 0 510.84 126.9 --core-area 0 0.27 510.84 126.63 --place-density 0.6 --macro-place-halo 2 2 \
 --pin-region "^(p|busy|fault|xs_q1|xs_e1|sw_).*=top:136.08-374.76" --pin-region "^(clk|rst|cfg|go|xs_v|xs_p|xs_b|xs_sv|xs_q0|xs_e0|sched).*=bottom:136.08-374.76" \
 --max-transition-ns 0.32 --slew-margin-percent 40 --hold-margin-ns 0.0 \
 --step-tcl POST_MACRO_PLACE=physical/abi3/rom_stage_pg_place.tcl --step-tcl POST_DETAIL_PLACE=physical/abi3/check_pg_before_route.tcl \
 --orfs-var PDN_TCL=/src/tools/chip_assembly/tcl/pdn_w10_elem_m7_ir.tcl --nickname-tag rom_stage_pg_${RUN}_20261004 \
 --output $J/out --sdc-append physical/abi3/v41_w10_elem_pp_multicycle.sdc \
 --macro-view ot_rom_4096x274_m8=physical/asap7_memory_macros/ot_rom_4096x274_m8 \
 --param MTP=1 --param EARLY=1 --param NB=2 --param FAST=1 --param PP=1 --param PG=${PGV:-1} --param DOM_CG=${DOMCG:-0} \
 --orfs-var ROUTING_LAYER_ADJUSTMENT=0.22 --hold-corners WC,BC \
 --pnr-stop-after ${STOP:-finish} --orfs-corner WC --clock-uncertainty-hold-ns 0.025 \
 --core-input-delay-min-ns 0.36 --core-input-delay-max-ns 0.727 --output-delay-min-ns -0.322 --output-delay-max-ns -0.193 > $J/launch.log 2>&1
