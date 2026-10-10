#!/bin/bash
# CLAUDE S81-PH coll v2 exact gate: tb_s81ph_coll_sys (4-die TP4 group of dsfd_sp_collective vs four C8 engines
# built with RANK 0..3; transaction-level: every reduce word / gather beat in order per die, pass-through flits in
# order) on the tiled slab (default) or the v1 flat slab (-DS81PH_COLL_V1).  Run from the repo root.
#   run_coll_bench.sh <out dir> <label> [-G.. / -D..]      -> <out>/<label>.log; exit 0 iff PASS
set -u
O=$1; L=$2; shift 2
S=$(pwd); mkdir -p $O/$L
P=$S/rtl/dsrom_sys/s81_ph
( cd $O/$L && verilator --binary -j 8 --timing -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-PINCONNECTEMPTY -Wno-MULTIDRIVEN -Wno-UNOPTFLAT \
  -Wno-PINMISSING -DOT_S81PH_PLL_MODEL --top-module tb_s81ph_coll_sys "$@" \
  $P/test/tb_s81ph_coll_sys.sv $P/dsfd_sp_collective.sv $P/coll/dsfd_coll_ck.sv $P/coll/dsfd_coll_core.sv $P/coll/dsfd_coll_split.sv \
  $P/coll/ot_s81ph_coll_lane.sv $P/coll/ot_s81ph_skid2.sv $P/coll/ot_s81ph_ckbuf.sv \
  $P/ot_s81ph_coll_core.sv $P/ot_s81ph_coll_rstc.sv $P/ot_s81_pll_bb.sv $P/ot_s81ph_link_ep.sv $P/ot_s81ph_link_gbx.sv \
  $P/ot_s81ph_mem1r1w.sv $P/ot_s81ph_rfifo.sv \
  $S/rtl/rom/ot_w15_rom_oneshot_px_acceptedpop.sv $S/rtl/link/ot_fifo_sram_fwft.sv $S/rtl/hdc/ot_hdc_fastfp.sv \
  $S/rtl/proto/ot_fp32_add_rne_pipe.sv $S/rtl/link/ot_link_crc32.sv $S/rtl/dsrom_sys/ot_dsrom_link_chan.sv \
  $S/physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v \
  $S/physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v \
  --Mdir obj > build.log 2>&1 ) || { echo "BUILD_FAIL" > $O/$L.log; tail -30 $O/$L/build.log >> $O/$L.log; cat $O/$L.log; exit 2; }
$O/$L/obj/Vtb_s81ph_coll_sys > $O/$L.log 2>&1
grep -E "CYCLES|TB_S81PH_COLL_SYS" $O/$L.log | tail -3
grep -q "TB_S81PH_COLL_SYS PASS" $O/$L.log
