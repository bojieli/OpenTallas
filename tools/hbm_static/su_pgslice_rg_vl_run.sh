#!/bin/bash
# TW-HBM-PGLG 10-19: REGION (landed) LIGHT slice ot_hbm_su_static_pgslice_rg lockstep vs the flat strapped pgslice_lg
# (hard-children d4g configuration) on Verilator (the closure daemon pins 5.050; ot-heavy puts it first on PATH).
# usage: su_pgslice_rg_vl_run.sh OUT [MUT] [EDGES]
set -euo pipefail
cd "$(dirname "$0")/../.."
out=$(realpath -m "$1"); mut=${2:-0}; edges=${3:-1200}; mkdir -p "$out"
S=rtl/hbm_accel/generic/adapters/static_su
T=tb_hbm_su_pgslice_rg
verilator --version
build() {
verilator --binary --timing -j "${OT_THREADS:-8}" -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN --top-module $T \
 +define+OT_HARD_CHILDREN +define+OT_SU_SYNC_RST -GMUT=$mut -GEDGES=$edges --Mdir "$out/obj" -o rg \
 rtl/lib/ot_rst_relay.sv rtl/common/landed_parent/ot_pl_land.sv \
 $S/arithmetic/ot_hbm_su_static_ins.sv $S/arithmetic/ot_hbm_su_static_lane.sv $S/arithmetic/ot_hbm_su_static_lane_pinreg.sv \
 $S/arithmetic/ot_hbm_su_static_kind0_lat4_leaf1_physical.sv \
 $S/arithmetic/ot_hbm_su_static_side.sv $S/data_store/ot_hbm_su_static_data_store.sv $S/data_store/ot_hbm_su_static_pinned_bank.sv \
 $S/data_store/ot_hbm_su_static_bank6_clock_physical.sv \
 $S/ot_hbm_su_static_vm_ports.sv $S/ot_hbm_su_static_vm_bank_leaf_s.sv $S/reduction/ot_hbm_su_red_pretree.sv \
 $S/programme/multirate_bridge.sv $S/top/ot_hbm_su_static_pgslice.sv $S/top/ot_hbm_su_static_pg_lg_tap.sv \
 $S/top/ot_hbm_su_static_pgslice_lg.sv $S/top/ot_hbm_su_static_pg_stream.sv $S/top/ot_hbm_su_pgrg_parts.sv $S/top/lp/ot_hbm_su_static_pgslice_rgf_lp.sv $S/top/ot_hbm_su_static_pgslice_rg.sv \
 rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_pair_tap.sv rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_bank.sv \
 rtl/hdc/v41x/ot_hdc_v41x_sfu.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv \
 rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat.sv \
 rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/v41/ot_hdc_fsqrt.sv \
 rtl/hdc/v41/ot_hdc_fdiv.sv rtl/hdc/v41/ot_hdc_softplus.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v \
 rtl/test/hbm_accel/generic/$T.sv > "$out/build.log" 2>&1
}
# one retry on a PCH race (10-18 rule)
build || { grep -q "pch\|\.gch\|No such file" "$out/build.log" && rm -rf "$out/obj" && build; } || { tail -40 "$out/build.log"; exit 1; }
"$out/obj/rg" | tee "$out/bench.log" | tail -14
