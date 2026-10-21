#!/bin/bash
set -euo pipefail
O=../out_fmem;mkdir -p "$O"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
SRC=(tools/s81_dv/svc_rs/fmem_n32/tb_fmem.sv tools/s81_dv/svc_rs/fmem_n32/fmem_ref.sv rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_att.sv rtl/hdc/v41x/ot_hdc_v41x_kreg.sv physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v)
sha256sum "${SRC[@]}" > "$O/sources.sha256"
"$V" --binary --timing -j 2 -CFLAGS -O1 --top-module tb_fmem -DOT_SVC_FMEM_N32 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --Mdir "$O/obj" "${SRC[@]}" > "$O/build.log" 2>&1
"$O/obj/Vtb_fmem" > "$O/run.log" 2>&1
cat "$O/run.log"
