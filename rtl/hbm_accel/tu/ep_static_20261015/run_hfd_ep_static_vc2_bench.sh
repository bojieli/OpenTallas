#!/bin/bash
# run_hfd_ep_static_vc2_bench.sh <src root> <out dir> [MUT] [NBLK]: the B2 in-band host link -- two hfd_ep_static_vc2
# endpoints + their hfd_ep_host_vc host faces back to back through two REAL ot_pdie_serdes macros (KP4 FEC + rate
# match), 300 ppm, pad bit errors, COLL (calendar) + host (no calendar) both directions (tb_hfd_ep_static_vc2).
# Prints the TB line; exit 0 iff it says PASS.  Verilator >= 5 (--binary --timing).
set -u
SRC=$1; OUT=$2; MUT=${3:-0}; NBLK=${4:-12}; mkdir -p $OUT
E=$SRC/rtl/hbm_accel/tu/ep_static_20261015; L=$SRC/rtl/dsrom_sys/s81_link
# the KP4 decoder is split over ot_s81_kp4_{common,bm,dchn,ddly,dout,dsyn}.sv (+ its 32x546 / 2c 64x546 SRAM leaves) since route 2
F="$E/hfd_ep_static_vc2.sv $E/ot_hep_rx_store.sv $E/tb_hfd_ep_static_vc2.sv $SRC/rtl/qwen_sys/split_20261014/ot_qwen_crc_parallel.sv
   $SRC/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v
   $SRC/physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v
   $SRC/physical/asap7_memory_macros/ot_sram_1r1w2c_64x546_m1/ot_sram_1r1w2c_64x546_m1.v
   $L/ot_s81_kp4_common.sv $L/ot_s81_kp4_bm.sv $L/ot_s81_kp4_dchn.sv $L/ot_s81_kp4_ddly.sv $L/ot_s81_kp4_dout.sv
   $L/ot_s81_kp4_dsyn.sv $L/ot_s81_kp4_enc.sv $L/ot_s81_kp4_dec.sv $L/ot_pdie_serdes.sv"
B=$OUT/m$MUT
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}; [ -x "$V" ] || V=verilator
"$V" --binary --timing -j 8 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-UNOPTFLAT -Wno-MULTIDRIVEN +incdir+$L \
  --top-module tb_hfd_ep_static_vc2 -GMUT=$MUT -GNBLK=$NBLK --Mdir $B -o tb $F > $OUT/build_m$MUT.log 2>&1 || { tail -30 $OUT/build_m$MUT.log; echo "TB_HFD_EP_STATIC_VC2 MUT=$MUT BUILD_FAIL"; exit 2; }
timeout 3600 $B/tb +verilator+seed+7 > $OUT/run_m$MUT.log 2>&1
grep -E "ERR|TB_HFD_EP_STATIC_VC2" $OUT/run_m$MUT.log | tail -4
rm -rf $B
grep -q "^TB_HFD_EP_STATIC_VC2 .* PASS$" $OUT/run_m$MUT.log
