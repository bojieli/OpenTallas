#!/usr/bin/env bash
# All-tile engram_c prefetch lockstep bench (Verilator): bash physical/s81_engc_tiles/bench_pf.sh <outdir> [+define+OT_ENGC_PB_MUT]
set -eu
O=${1:?outdir}; shift; DEF=${1:-}; mkdir -p "$O"
E=rtl/dsrom_sys/engram
F="physical/s81_engc_tiles/tb/tb_engc_pf_eq.sv $E/ot_dsrom_engram_prefetch_h.sv $E/tiles/ot_engc_pbank.sv $E/tiles/ot_engc_t_ws.sv
   $E/tiles/ot_engc_t_io.sv rtl/v41rom/ot_v41_kreg.sv rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv rtl/lib/ot_reset_sync.sv
   rtl/lib/ot_async_fifo.sv rtl/dsrom_sys/s81_ctrl/ot_s81_engine_adapter.sv rtl/dsrom_sys/s81_ctrl/ot_s81_slab_ep.sv
   physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v"
verilator --binary -j 16 --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_engc_pf_eq $DEF -Mdir "$O/obj" $F > "$O/build.log" 2>&1 || { tail -20 "$O/build.log"; echo "ENGC_PF_EQ FAIL build"; exit 1; }
"$O/obj/Vtb_engc_pf_eq" | tee "$O/run.log" | grep -E "ENGC_PF_EQ|MISMATCH" | head -8
grep -q "^ENGC_PF_EQ PASS" "$O/run.log"
