#!/bin/bash
# run_link_ep.sh <src root> <out dir> <label> [-G overrides...] [-D mutant defines]: Verilator 5 build + run of
# tb_s81ph_link_ep (CLAUDE S81-PH collective).  Prints the PASS/FAIL line into <out>/<label>.log.
set -u
S=$1; O=$2; L=$3; shift 3
mkdir -p $O/$L
cd $O/$L
verilator --binary -j 4 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-PINCONNECTEMPTY --top-module tb_s81ph_link_ep "$@" \
  $S/rtl/dsrom_sys/s81_ph/test/tb_s81ph_link_ep.sv $S/rtl/dsrom_sys/s81_ph/ot_s81ph_link_ep.sv \
  $S/rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv $S/rtl/dsrom_sys/ot_dsrom_link_ct.sv $S/rtl/dsrom_sys/ot_dsrom_link_chan.sv \
  $S/rtl/link/ot_link_crc32.sv $S/physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v \
  --Mdir obj > build.log 2>&1 || { echo "BUILD_FAIL" > ../$L.log; exit 1; }
/usr/bin/time -v ./obj/Vtb_s81ph_link_ep > ../$L.log 2> time.log
grep -E "Maximum resident|Elapsed" time.log >> ../$L.log
