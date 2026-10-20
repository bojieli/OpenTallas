#!/usr/bin/env bash
# MU-S81-2/HOSTEP (2026-10-19): host-plane multi-user endpoint ot_s81sl_lep_mu_h (kit s81sl_lepmuh) vs the single-user
# ot_s81sl_lep, Verilator 5.050 (the closure daemon's version).
#   base   tb_s81sl_lep_muh seeds 1 5 (PASS expected)
#   mut    HSTAMP / TAGDROP / LANDCUT (ot_s81sl_lep_core) / KSOFF: each must FAIL ("^FAIL lep_muh")
# Usage (cwd = repo root): run_lep_muh_bench.sh OUTDIR [base|mut|all] [single mutant name]
set -u
O=${1:?outdir}; WHAT=${2:-all}; ONE=${3:-}; mkdir -p "$O"
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
$V --version > $O/verilator_version.txt
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
D="+define+OT_S81PH_GBX_FMT1 +define+OT_S81PH_EP_PIPE2"
TOP=tb_s81sl_lep_muh
build() { n=$1; shift
  $V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-lint -Wno-style +incdir+$L $D "$@" \
    --top-module $TOP -Mdir $O/$n $SRCS $SL/test/tb_s81sl_lep_muh.sv --build-jobs ${J:-8} -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" \
    > $O/build_$n.log 2>&1 || { echo "BUILD_FAILED $n"; grep -m10 %Error $O/build_$n.log; return 2; }
}
bad=0
run() { n=$1; exp=$2
  { cat $O/verilator_version.txt; "$O/$n/V$TOP"; echo "rc=$?"; } > "$O/$n.log" 2>&1; v=$(grep -m1 -E "^(PASS|FAIL) " "$O/$n.log")
  echo "$n: $v"
  case $exp in PASS) echo "$v" | grep -q '^PASS lep_muh' || bad=1 ;; FAIL) echo "$v" | grep -q '^FAIL lep_muh' || { echo "  $n NOT detected"; bad=1; } ;; esac
}
if [ "$WHAT" = base ] || [ "$WHAT" = all ]; then
  for s in 1 5; do build muh_s$s -GSEED=$s && run muh_s$s PASS || bad=1; done
fi
if [ "$WHAT" = mut ] || [ "$WHAT" = all ]; then
  for m in OT_S81SL_LEP_MUT_HSTAMP OT_S81SL_LEP_MUT_TAGDROP OT_S81SL_LEP_MUT_LANDCUT OT_S81SL_LEP_MUT_KSOFF; do
    [ -n "$ONE" ] && [ "$ONE" != "$m" ] && continue
    n=mut_${m##*MUT_}; build $n +define+$m && run $n FAIL || bad=1
  done
fi
[ $bad = 0 ] && echo "LEP_MUH_GATE PASS" || echo "LEP_MUH_GATE FAIL"
exit $bad
