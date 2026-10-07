#!/bin/bash
# run_coll_sys.sh <src root> <out dir> <label> [-G.. / -D..]: Verilator 5 build + run of tb_s81ph_coll_sys.
set -u
S=$1; O=$2; L=$3; shift 3
mkdir -p $O/$L; cd $O/$L
verilator --binary -j 8 --timing -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-PINCONNECTEMPTY -Wno-MULTIDRIVEN -Wno-UNOPTFLAT \
  -DOT_S81PH_PLL_MODEL --top-module tb_s81ph_coll_sys "$@" \
  $S/rtl/dsrom_sys/s81_ph/test/tb_s81ph_coll_sys.sv $S/rtl/dsrom_sys/s81_ph/dsfd_sp_collective.sv \
  $S/rtl/dsrom_sys/s81_ph/ot_s81ph_coll_core.sv $S/rtl/dsrom_sys/s81_ph/ot_s81ph_coll_rstc.sv \
  $S/rtl/dsrom_sys/s81_ph/ot_s81_pll_bb.sv $S/rtl/dsrom_sys/s81_ph/ot_s81ph_link_ep.sv $S/rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx.sv \
  $S/rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv $S/rtl/dsrom_sys/s81_ph/ot_s81ph_rfifo.sv \
  $S/rtl/rom/ot_w15_rom_oneshot_px_acceptedpop.sv $S/rtl/link/ot_fifo_sram_fwft.sv $S/rtl/hdc/ot_hdc_fastfp.sv \
  $S/rtl/proto/ot_fp32_add_rne_pipe.sv $S/rtl/link/ot_link_crc32.sv $S/rtl/dsrom_sys/ot_dsrom_link_chan.sv \
  $S/physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v \
  $S/physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v \
  --Mdir obj > build.log 2>&1 || { echo "BUILD_FAIL" > ../$L.log; tail -30 build.log >> ../$L.log; exit 1; }
/usr/bin/time -v ./obj/Vtb_s81ph_coll_sys > ../$L.log 2> time.log
grep -E "Maximum resident|Elapsed" time.log >> ../$L.log
