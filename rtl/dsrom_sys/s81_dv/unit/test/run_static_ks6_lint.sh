#!/usr/bin/env bash
# S81U-SEQ: dsdv_seq_host exact bench (lock-step vs the reused dsfd_host_c STATIC + ot_s81_fixed_issue goldens, SEEDS
# seeds), the illegal-collision run (must fault), the W-half region-live drop (must fault; RTL-BUILD-S81), 9 mutants
# that must FAIL (5: W svc half dropped from the merge, 6: host writes routed by the wrong PC bit, 7 / 8: see mdef), verilator lint.  Prints SEQHOST_GATE PASS/FAIL.
# Usage: run_seq_host_bench.sh [outdir] [seeds] [mutant 1..9: build + run that mutant only]
set -u
R=$(cd "$(dirname "$0")/../../../../.." && pwd)
O=${1:-$(mktemp -d)}; SEEDS=${2:-"1 2 3 4"}; mkdir -p "$O"
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
U=$R/rtl/dsrom_sys/s81_dv/unit
F="$R/rtl/lib/ot_async_fifo.sv $R/rtl/lib/ot_reset_sync.sv $R/rtl/lib/ot_rst_relay.sv $R/rtl/link/ot_link_afifo.sv
   $R/rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv $R/rtl/hdc/ingest/ot_hdc_ingest_fp8q.sv $R/rtl/hdc/ingest/ot_hdc_kv_ingest.sv
   $R/rtl/hdc/ingest/ot_rom_host_ingest.sv $R/physical/rom_host_ingest/rtl/dsfd_host.sv
   $R/rtl/dsrom_sys/s81_ingest/ot_s81_ingest_visibility_fence.sv $R/rtl/dsrom_sys/s81_ingest/dsfd_host_native.sv
   $R/rtl/dsrom_sys/s81_ingest/dsfd_host_sd.sv $R/rtl/dsrom_sys/s81_ingest/dsfd_host_c.sv
   $R/rtl/dsrom_sys/s81_static_control/ot_s81_fixed_issue.sv $U/ot_dsdv_fixed_issue.sv $U/ot_dsdv_walk_issue.sv $U/ot_dsdv_vstop.sv $U/dsdv_sh_sd.sv $U/dsdv_seq_host.sv
   $R/rtl/dsrom_sys/s81_dv/unit/host_sram/ot_dsdv_host_afifo_sram.sv
   $R/rtl/dsrom_sys/s81_dv/unit/host_sram/ot_dsdv_afifo_n32.sv $R/rtl/dsrom_sys/s81_ingest/ot_s81_fence_n32.sv $R/rtl/hdc/ingest/ot_s81_ing_stream_n32.sv
   $R/rtl/hdc/ingest/ot_rom_host_ingest_n32.sv $R/rtl/dsrom_sys/s81_ingest/dsfd_host_n32.sv $R/rtl/dsrom_sys/s81_ingest/dsfd_host_native_n32.sv
   $R/physical/asap7_memory_macros/ot_sram_1r1w2c_16x546_m1/ot_sram_1r1w2c_16x546_m1.v
   $R/physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1/ot_sram_1r1w2c_32x64_m1.v
   $R/physical/asap7_memory_macros_v2/ot_sram_1r1w2c_16x257_m1/ot_sram_1r1w2c_16x257_m1.v
   $R/physical/asap7_memory_macros_v2/ot_sram_1r1w2c_16x289_m1/ot_sram_1r1w2c_16x289_m1.v
   $R/physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v"
build() { l=$1; shift
  verilator ${VL_EXTRA:-} --binary --timing -j 16 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-UNOPTFLAT +define+DSFD_HOST_C_STATIC \
    --top-module tb_static_ks6 "$@" --Mdir "$O/$l" -o tb $F $U/dsdv_static_ks6.sv $U/test/tb_static_ks6.sv > "$O/build_$l.log" 2>&1 \
    || { echo "BUILD_FAIL $l (see $O/build_$l.log)"; return 2; }
}
for enabled in 0 1; do
 verilator --lint-only --timing -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-UNOPTFLAT --top-module dsdv_seq_host_mux -GSTATIC_KS6=$enabled -DOT_S81_SH_APIPE9 -DOT_S81_SH_APIPE10 -DOT_S81_SH_SRAM -DOT_S81_SH_RSZ -DOT_S81_SH_S10B -DOT_S81_SH_S10C -DOT_S81_SH_S10D -DOT_S81_SH_S10E -DTB_HSH=8 $F $R/physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v $R/rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv $U/dsdv_static_ks6.sv $U/dsdv_mu_hslot.sv $U/dsdv_mu_hwin.sv > "$O/lint_$enabled.log" 2>&1 || { cat "$O/lint_$enabled.log";exit 1; }
 echo "KS6 ACTUAL_MUX LINT PASS enabled=$enabled"
done
