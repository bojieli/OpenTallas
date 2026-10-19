#!/bin/bash
# run_host_cp_rxs.sh <out dir> [MUT] [NREQ]   (run from the repo root, or set SRC)
# End-to-end bench of the d4g host control plane on the static endpoint (tb_hbm_host_cp_rxs): DUT ot_hbm_host_cp_rxs +
# hfd_ep_static + ot_pdie_ucie on the die, the same endpoint + link on a 300 ppm host, against the CLOSED ot_hbm_host_cp_rx
# fed the same requests.  Verilator >= 5 (--binary --timing).  Prints the TB line; exit 0 iff it says PASS.
set -u
SRC=${SRC:-$(cd "$(dirname "$0")/../../.." && pwd)}
OUT=$1; MUT=${2:-0}; NREQ=${3:-70000}; mkdir -p "$OUT"
H=$SRC/rtl/hbm_accel/host_ep_20261018; P=$SRC/rtl/hbm_accel/generic/collective/p2p; E=$SRC/rtl/hbm_accel/tu/ep_static_20261015
S=$SRC/rtl/hbm_accel/host_static_20261015; L=$SRC/rtl/dsrom_sys/s81_link; Q=$SRC/rtl/qwen_sys/split_20261014
F="$H/tb_hbm_host_cp_rxs.sv $H/ot_hbm_host_cp_rxs.sv $H/ot_hbm_host_link_seq.sv $H/ot_hbm_host_link_capture.sv $H/ot_hbm_host_packet_nc.sv
   $P/ot_hgi_coll_static_seq_ctl.sv $P/ot_hgi_coll_static_pinreg_store.sv $Q/ot_qkvd_d2d_llr.sv $Q/ot_qwen_crc_parallel.sv
   $E/hfd_ep_static.sv $E/ot_hep_rx_store.sv $L/ot_s81_kp4_enc.sv $L/ot_s81_kp4_dec.sv $L/ot_pdie_serdes.sv
   $SRC/rtl/hbm_accel/io_native_20261014/ot_hbm_host_landing256.sv $S/ot_hbm_host_cp_rx.sv $S/ot_hbm_host_packet_static.sv
   $S/ot_hbm_host_static_ingress.sv $SRC/rtl/lib/ot_rst_relay.sv
   $SRC/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v
   $SRC/physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v"
B=$OUT/m$MUT
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}; [ -x "$V" ] || V=verilator
sha256sum $F > "$OUT/sources_m$MUT.sha256"
"$V" --binary --timing -j 8 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-UNOPTFLAT -Wno-MULTIDRIVEN +incdir+$L \
  -DOT_MEM_NO_INIT --top-module tb_hbm_host_cp_rxs -GMUT=$MUT -GNREQ=$NREQ --Mdir $B -o tb $F > "$OUT/build_m$MUT.log" 2>&1 \
  || { tail -30 "$OUT/build_m$MUT.log"; echo "HOST_CP_RXS_FAIL MUT=$MUT BUILD"; exit 2; }
timeout 7200 $B/tb +verilator+seed+7 > "$OUT/run_m$MUT.log" 2>&1
grep -E "FAULT at|HOST_CP_RXS" "$OUT/run_m$MUT.log" | tail -4
rm -rf $B
grep -q "^HOST_CP_RXS_PASS" "$OUT/run_m$MUT.log"
