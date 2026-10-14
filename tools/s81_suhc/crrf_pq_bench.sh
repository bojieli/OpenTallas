#!/bin/bash
# Lockstep + composition bench of the pin-register forward column root (crootr_f PQ 1 + 11 x cryys against the v2 form):
#   crrf_pq_bench.sh OUTDIR [MUT] [C]   (MUT 0 exact, 1 / 2 negative controls; C 0 or 2)
# prints "CRRF_PQ PASS" / "CRRF_PQ FAIL" (rtl/dsrom_sys/s81_suhc/test/tb_s81_hc_crrf_pq.sv)
set -e
O=$1; M=${2:-0}; C=${3:-0}; R=$(cd "$(dirname "$0")/../.." && pwd)
[ -x "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" ] && export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
mkdir -p "$O"
D=""; [ "$M" != 0 ] && D="-DOT_S81_HC_CRRF_MUT$M"
verilator --binary --timing -O2 -Wno-fatal -Wno-WIDTH -Wno-MODMISSING --top-module tb_s81_hc_crrf_pq -GC=$C $D -Mdir "$O/obj_m${M}_c$C" -j 4 \
    "$R/rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_crootr.sv" "$R/rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_crooty.sv" \
    "$R/rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_stree.sv" "$R/rtl/hdc/ot_hdc_delay.sv" "$R/rtl/link/ot_fifo_sram_fwft.sv" \
    "$R/physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v" \
    "$R/rtl/dsrom_sys/s81_suhc/test/tb_s81_hc_crrf_pq.sv" > "$O/build_m${M}_c$C.log" 2>&1 || { tail -30 "$O/build_m${M}_c$C.log"; exit 2; }
"$O/obj_m${M}_c$C/Vtb_s81_hc_crrf_pq"
