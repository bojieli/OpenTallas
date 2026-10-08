#!/bin/bash
# usage: bench.sh <tag> "<plusargs>" [defines...]
cd $(dirname $0)/src
tag=$1; pa=$2; shift 2
defs=""; for d in "$@"; do defs="$defs +define+$d"; done
mkdir -p ../b_$tag
if [ ! -x ../b_$tag/obj/Vtb_s81ph_col ]; then
timeout 3600 verilator --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb_s81ph_col $defs -Mdir ../b_$tag/obj \
  rtl/common/ot_fwd_link_stage.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v \
  rtl/link/ot_fifo_sram_fwft.sv rtl/dsrom_sys/s81_ph/ot_s81ph_col.sv rtl/dsrom_sys/s81_ph/dsfd_bk_collector.sv \
  rtl/dsrom_sys/s81_ph/test/tb_s81ph_col.sv > ../b_$tag/build.log 2>&1 || { echo BUILD_FAIL > ../b_$tag/rc; exit 1; }
fi
( /usr/bin/time -v timeout 3600 ../b_$tag/obj/Vtb_s81ph_col $pa > ../b_$tag/run.log 2> ../b_$tag/time.log; echo "rc=$?" > ../b_$tag/rc )
