#!/bin/bash
# S81/PORTFIX-DEAD D-MURT: lep_nrt_eq.sh OUTDIR (repo root): ot_s81sl_lep_mu_a_nrt vs ot_s81sl_lep_mu_a lockstep, seeds 1..3 x pv 10/40.
set -u; O=$1; mkdir -p $O
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
L=rtl/dsrom_sys/s81_link; SL=rtl/dsrom_sys/s81_dv/slice
SRCS="rtl/lib/ot_rst_relay_tree3.sv rtl/lib/ot_sram_oldread_wreg.sv rtl/lib/ot_sram_showahead_1r1w.sv
 physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v
 rtl/link/ot_link_crc32.sv rtl/common/ot_link_credit.sv rtl/lib/ot_rst_relay.sv rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv
 rtl/dsrom_sys/s81_ph/ot_s81ph_link_ep.sv rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx.sv rtl/dsrom_sys/s81_ph/ot_s81ph_rfifo.sv
 rtl/dsrom_sys/s81_ph/coll/ot_s81ph_skid2.sv rtl/dsrom_sys/s81_ph/coll/ot_s81ph_ckbuf.sv rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane.sv
 $L/ot_s81_kp4_common.sv $L/ot_s81_kp4_enc.sv $L/ot_s81_kp4_bm.sv $L/ot_s81_kp4_dsyn.sv $L/ot_s81_kp4_ddly.sv $L/ot_s81_kp4_dchn.sv
 $L/ot_s81_kp4_dout.sv $L/ot_s81_kp4_dec.sv $L/ot_pdie_serdes.sv
 physical/asap7_memory_macros/ot_sram_1r1w2c_64x546_m1/ot_sram_1r1w2c_64x546_m1.v
 physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v
 physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v
 physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
 $SL/ot_s81sl_slice_lep.sv $SL/dsdv_mu_land.sv tools/s81_slice/lep_nrt/tb_lep_nrt_eq.sv"
$V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-lint -Wno-style +incdir+$L \
  +define+OT_S81PH_GBX_FMT1 +define+OT_S81PH_EP_PIPE2 --top-module tb_lep_nrt_eq -Mdir $O/obj $SRCS --build-jobs ${J:-8} \
  -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $O/build.log 2>&1 || { grep -m10 %Error $O/build.log; echo BUILD_FAILED; exit 3; }
rc=0
for s in 1 2 3; do for pv in 10 40; do
  l=$($O/obj/Vtb_lep_nrt_eq +seed=$s +pv=$pv | tee $O/run_s${s}_pv$pv.log | grep LEP_NRT_EQ); echo "$l"; echo "$l" | grep -q PASS || rc=1
done; done; exit $rc
