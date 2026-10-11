#!/bin/bash
# CLAUDE S81-PH coll v2 exact gate (mtp-colllane-1011: + the dedicated MTP lane with +define+OT_S81PH_COLL_MTPL +define+TB_MTP): tb_s81ph_coll_sys (4-die TP4 group of dsfd_sp_collective vs four C8 engines
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
  $P/coll/dsfd_coll_mtp_lane.sv $P/test/tb_mtp_lane_io.sv $S/rtl/dsrom_sys/mtp/dsfd_coll_mtp_ep.sv \
  $S/rtl/dsrom_sys/mtp/ot_dsrom_mtp_link_rtt.sv $S/rtl/dsrom_sys/mtp/ot_dsrom_mtp_link_pair.sv $S/rtl/dsrom_sys/mtp/rtt/ot_dsrom_mtp_rstsync.sv \
  $P/ctrl_c/dsfd_sp_collective_c.sv $P/coll/dsfd_coll_job.sv $S/rtl/dsrom_sys/s81_ctrl/ot_s81_coll_job.sv $S/rtl/dsrom_sys/s81_ctrl/ot_s81_slab_ep.sv \
  $S/rtl/dsrom_sys/s81_ctrl/ot_s81_engine_adapter.sv $S/rtl/dsrom_sys/s81_ctrl/ot_s81_stage_seq.sv $S/rtl/lib/ot_async_fifo.sv $S/rtl/lib/ot_reset_sync.sv \
  $S/rtl/rom/ot_w15_rom_oneshot_px_acceptedpop.sv $S/rtl/link/ot_fifo_sram_fwft.sv $S/rtl/hdc/ot_hdc_fastfp.sv \
  $S/rtl/proto/ot_fp32_add_rne_pipe.sv $S/rtl/link/ot_link_crc32.sv $S/rtl/common/ot_link_credit.sv $S/rtl/lib/ot_rst_relay.sv $S/rtl/dsrom_sys/ot_dsrom_link_chan.sv \
  $S/physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v \
  $S/physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v \
  $S/physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
  --Mdir obj > build.log 2>&1 ) || { echo "BUILD_FAIL" > $O/$L.log; tail -30 $O/$L/build.log >> $O/$L.log; cat $O/$L.log; exit 2; }
$O/$L/obj/Vtb_s81ph_coll_sys > $O/$L.log 2>&1
grep -E "CYCLES|TB_S81PH_COLL_SYS" $O/$L.log | tail -3
# COLL_MAX_CYCLES (ds-1010 2026-10-10, optional): a PASS that took more than this many DUT cycles fails -- go-back-N
# retransmission keeps a broken endpoint transaction-exact (link EP RXPIPE mutant: PASS at 39,544 vs 3,011 cycles).
if [ -n "${COLL_MAX_CYCLES:-}" ]; then
  c=$(grep -oE "dut_last [0-9]+" $O/$L.log | tail -1 | awk '{print $2}')
  if [ -z "$c" ] || [ "$c" -gt "$COLL_MAX_CYCLES" ]; then echo "TB_S81PH_COLL_SYS FAIL cycles ${c:-none} > bound $COLL_MAX_CYCLES" | tee -a $O/$L.log; exit 1; fi
fi
grep -q "TB_S81PH_COLL_SYS PASS" $O/$L.log
