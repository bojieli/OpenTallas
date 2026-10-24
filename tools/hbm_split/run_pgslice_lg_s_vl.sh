#!/bin/bash
# HBM-P5-RTLB 10-23: pgslice_lg_s split twin (PIN_REG 1 + side split) vs pinned pgslice_lg PIN_REG 1 lock-step (Verilator 5.050; same tb as run_pgslice_lg_s.sh).
# usage: run_pgslice_lg_s_vl.sh OUT QID G [SMUT] [EDGES]
set -euo pipefail
cd "$(dirname "$0")/../.."
out=$(realpath -m "$1"); qid=$2; g=$3; mut=${4:-0}; edges=${5:-1500}; mkdir -p "$out"; tag=q${qid}g${g}m${mut}
S=rtl/hbm_accel/generic/adapters/static_su
T=tb_hbm_su_pgslice_lg_s
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; [ -x "$vl" ] || vl=verilator
obj="$out/obj_$tag"
src="$S/arithmetic/ot_hbm_su_static_ins.sv $S/arithmetic/ot_hbm_su_static_lane.sv $S/arithmetic/ot_hbm_su_static_lane_pinreg.sv $S/arithmetic/ot_hbm_su_static_side.sv $S/arithmetic/ot_hbm_su_static_side_s.sv $S/top/ot_hbm_su_static_pgslice_s.sv $S/top/ot_hbm_su_static_pgslice_lg_s.sv $S/data_store/ot_hbm_su_static_data_store.sv $S/data_store/ot_hbm_su_static_pinned_bank.sv $S/ot_hbm_su_static_vm_ports.sv $S/programme/multirate_bridge.sv $S/top/ot_hbm_su_static_pgslice.sv $S/top/ot_hbm_su_static_pg_lg_tap.sv $S/top/ot_hbm_su_static_pgslice_lg.sv rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_pair_tap.sv rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_bank.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/v41/ot_hdc_fsqrt.sv rtl/hdc/v41/ot_hdc_fdiv.sv rtl/hdc/v41/ot_hdc_softplus.sv physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v rtl/test/hbm_accel/generic/tb_hbm_su_pgslice_lg_s.sv"
sha256sum $src "$0" > "$out/sources_$tag.sha256"
[ -x "$obj/V$T" ] || "$vl" --binary --timing -O1 -j "${JOBS:-16}" -CFLAGS -O0 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN \
  --top-module $T -GSMUT=$mut -GQID=$qid -GG=$g -GEDGES=$edges --Mdir "$obj" $src > "$out/build_$tag.log" 2>&1 || { tail -30 "$out/build_$tag.log"; exit 3; }
"$obj/V$T" > "$out/$tag.log" 2>&1 || true
grep -E "PGSLICE_LG_S|MISMATCH|FAULT RELATION" "$out/$tag.log" | head -8
grep -q "PGSLICE_LG_S PASS" "$out/$tag.log"
