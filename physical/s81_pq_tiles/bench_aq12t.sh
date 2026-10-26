#!/usr/bin/env bash
# T_AQ lockstep bench (Verilator): bash physical/s81_pq_tiles/bench_aq12t.sh <outdir> [+define+OT_AQ12T_MUT_RA]
set -eu
O=${1:?outdir}; shift; DEF=${1:-}; mkdir -p "$O"
P=physical/s81_pq_xrv/pinned/rtl
F="physical/s81_pq_tiles/tb/tb_aq12t_eq.sv physical/s81_pq_tiles/rtl/ot_dsrom_aq12t.sv $P/hdc/v41x/ot_dsrom_aq12m.sv
   $P/hdc/ot_hdc_fp32_f12.sv $P/hdc/ot_hdc_fp32_mul_lat.sv $P/hdc/ot_hdc_fastfp_lat_f12.sv $P/hdc/ot_hdc_sfu.sv
   $P/hdc/ot_hdc_fp32_add_lat.sv $P/hdc/ot_hdc_delay.sv $P/hdc/ot_hdc_fastfp.sv $P/hdc/ot_hdc_prefix.sv
   $P/v41rom/ot_v41_kreg.sv $P/common/ot_prefix.sv rtl/lib/ot_rst_relay.sv
   physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v"
verilator --binary -j 16 --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_aq12t_eq $DEF -Mdir "$O/obj" $F > "$O/build.log" 2>&1 || { tail -20 "$O/build.log"; echo "AQ12T_EQ FAIL build"; exit 1; }
"$O/obj/Vtb_aq12t_eq" +NCYC=${NCYC:-40000} | tee "$O/run.log" | grep -E "AQ12T_EQ|MISMATCH" | head -8
grep -q "^AQ12T_EQ PASS" "$O/run.log"
