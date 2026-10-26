#!/bin/bash
set -eu
O=$(realpath -m "$1"); M=${2:-0}; mkdir -p "$O"
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version
D=()
if [ "$M" = 1 ]; then D+=(-DOT_S81PH_EP_RXPIPE_MUT); fi
if [ "$M" = 2 ]; then D+=(-DOT_S81PH_OLDREAD_MUT); fi
if [ "$M" = 3 ]; then D+=(-DOT_S81PH_EP_TOREG_MUT); fi
verilator --binary --timing -j 4 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style \
 --top-module tb_coll_safe2_oldread_cycles -GMUT="$M" "${D[@]}" --Mdir "$O/obj" \
 rtl/dsrom_sys/s81_ph/test/tb_coll_safe2_oldread_cycles.sv \
 rtl/dsrom_sys/s81_ph/ot_s81ph_link_ep_safe2.sv rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv rtl/lib/ot_sram_oldread_wreg.sv \
 rtl/dsrom_sys/ot_dsrom_link_chan.sv rtl/link/ot_link_crc32.sv \
 physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v \
 > "$O/build.log" 2>&1
"$O/obj/Vtb_coll_safe2_oldread_cycles" > "$O/run.log"
cat "$O/run.log"
grep -q '^COLL_CYCLES PASS' "$O/run.log"
