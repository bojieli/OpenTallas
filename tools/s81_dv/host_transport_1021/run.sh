#!/usr/bin/env bash
# Source-preservation/gap bench, not qualification of the unbuilt HOST(b).
set -euo pipefail
O=${1:?output directory}; mkdir -p "$O"
V=verilator
[ ! -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] || V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
L=rtl/dsrom_sys/s81_link; SL=rtl/dsrom_sys/s81_dv/slice
SRCS="rtl/link/ot_link_crc32.sv rtl/common/ot_link_credit.sv rtl/lib/ot_rst_relay.sv rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv
 rtl/dsrom_sys/s81_ph/ot_s81ph_link_ep.sv rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx.sv rtl/dsrom_sys/s81_ph/ot_s81ph_rfifo.sv
 rtl/dsrom_sys/s81_ph/coll/ot_s81ph_skid2.sv rtl/dsrom_sys/s81_ph/coll/ot_s81ph_ckbuf.sv rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane.sv
 $L/ot_s81_kp4_common.sv $L/ot_s81_kp4_enc.sv $L/ot_s81_kp4_bm.sv $L/ot_s81_kp4_dsyn.sv $L/ot_s81_kp4_ddly.sv $L/ot_s81_kp4_dchn.sv
 $L/ot_s81_kp4_dout.sv $L/ot_s81_kp4_dec.sv $L/ot_pdie_serdes.sv
 physical/asap7_memory_macros/ot_sram_1r1w2c_64x546_m1/ot_sram_1r1w2c_64x546_m1.v
 physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v
 physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v
 physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
 $SL/ot_s81sl_slice_lep.sv $SL/dsdv_mu_land.sv"

"$V" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-lint -Wno-style \
 +incdir+$L +define+OT_S81PH_GBX_FMT1 +define+OT_S81PH_EP_PIPE2 --top-module tb_s81_host_transport \
 -Mdir "$O/obj" $SRCS tools/s81_dv/host_transport_1021/tb_s81_host_transport.sv --build-jobs 4 \
 -MAKEFLAGS 'OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0' > "$O/build.log" 2>&1
"$O/obj/Vtb_s81_host_transport" > "$O/bench.log" 2>&1
cat "$O/bench.log"
grep -q '^PASS lep_host' "$O/bench.log"
