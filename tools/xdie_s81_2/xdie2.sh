#!/bin/bash
# XDIE-S81-2 (10-19) co-sim driver, cwd = the staged root (tools/xdie_s81_2/stage.sh writes it).
#   bash tools/xdie_s81_2/xdie2.sh build <out> <build> <set cur|asb|mu> [verilator -G / +define+ args]
#   bash tools/xdie_s81_2/xdie2.sh run   <out> <build> <name> <golden dir> [+plusargs]
# Source sets (stage.sh pins every file to a commit, stage/SOURCES.txt lists blob ids):
#   cur = the current die RTL (G8R2 0e6b9b710: rstop, lep, link_ep / gbx / KP4 / ot_pdie_serdes, lane legs = the die's
#         dsfd_dvrlyh relays + dsfd_dvland landings) + the CURRENT lane tile RTL (HF-3 ed9d570ad: tile-top CH_BOARD 700)
#   asb = cur with the lane tile file AS BOUND by G8R2 (0e6b9b710: tile tops without CH_BOARD -> core 400)
#   mu  = cur with the MU lep (origin/main ot_s81sl_slice_lep.sv: ot_s81sl_lep_core / ot_s81sl_lep_mu_ab, MU-S81 kit)
# Verilator = the closure daemon's 5.050 (~/.local/opentallas-tools/verilator-5.050); a build prints BUILD_OK / BUILD_FAILED,
# a run prints the bench verdict line and BENCH_PASS / BENCH_FAIL (exit 0 / 1).
set -u
CMD=$1; O=$2; B=$3; shift 3
V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
[ -x $V ] || { echo "NO_VERILATOR_5050"; exit 4; }
L=rtl/dsrom_sys/s81_link
if [ $CMD = build ]; then
  SET=$1; shift
  LANE=rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane.sv; LEP=rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_lep.sv
  [ $SET = asb ] && LANE=rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane.g8r2.sv
  [ $SET = mu ] && LEP=rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_lep.mu.sv
  SRCS="rtl/link/ot_link_crc32.sv rtl/common/ot_link_credit.sv rtl/lib/ot_rst_relay.sv rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv
   rtl/dsrom_sys/s81_ph/ot_s81ph_link_ep.sv rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx.sv rtl/dsrom_sys/s81_ph/ot_s81ph_rfifo.sv
   rtl/dsrom_sys/s81_ph/coll/ot_s81ph_skid2.sv rtl/dsrom_sys/s81_ph/coll/ot_s81ph_ckbuf.sv $LANE
   $L/ot_s81_kp4_common.sv $L/ot_s81_kp4_enc.sv $L/ot_s81_kp4_bm.sv $L/ot_s81_kp4_dsyn.sv $L/ot_s81_kp4_ddly.sv $L/ot_s81_kp4_dchn.sv
   $L/ot_s81_kp4_dout.sv $L/ot_s81_kp4_dec.sv $L/ot_pdie_serdes.sv
   physical/asap7_memory_macros/ot_sram_1r1w2c_64x546_m1/ot_sram_1r1w2c_64x546_m1.v
   physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v
   physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v
   rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rstop.sv $LEP
   rtl/dsrom_sys/s81_glue/ot_s81_rly.sv rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dv276.sv rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dvh.sv
   rtl/dsrom_sys/s81_dv/land/ot_s81_land.sv rtl/dsrom_sys/s81_dv/land/dsfd_dvland.sv
   rtl/test/xdie_s81_2/xdie_s81_2.vlt rtl/test/xdie_s81_2/xdie_s81_2_ep.sv rtl/test/xdie_s81_2/tb_xdie_s81_2.sv"
  for f in $SRCS; do [ -f $f ] || { echo "BUILD_FAILED $B missing $f"; exit 3; }; done
  mkdir -p $O/$B
  echo "$SET $* | $SRCS" > $O/$B/build_cmd.txt
  /usr/bin/time -v -o $O/$B/time_build.log $V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN \
    -Wno-lint -Wno-style +incdir+$L +define+OT_S81PH_GBX_FMT1 +define+OT_S81PH_EP_PIPE2 "$@" \
    --top-module tb_xdie_s81_2 -Mdir $O/$B/obj $SRCS --build-jobs ${J:-8} \
    -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $O/$B/build.log 2>&1 \
    || { echo "BUILD_FAILED $B"; grep -m12 -E "%Error" $O/$B/build.log; exit 3; }
  grep -E "PINMISSING|PINCONNECTEMPTY|PINNOCONNECT" $O/$B/build.log | grep -v -E "tb_xdie_s81_2|xdie_s81_2_ep" | head -8
  $V --version > $O/$B/verilator_version.txt
  echo "BUILD_OK $B"; exit 0
fi
# run
N=$1; G=$2; shift 2
mkdir -p $O/$N
[ -x $O/$B/obj/Vtb_xdie_s81_2 ] || { echo "NO_BUILD $B"; exit 3; }
cp $G/stim.hex $O/$N/stim.hex; [ -f $G/mu.hex ] && cp $G/mu.hex $O/$N/mu.hex
NS=$(cat $G/NS); NM=$(cat $G/NM 2>/dev/null || echo 0)
cp $O/$B/verilator_version.txt $O/$N/ 2>/dev/null
( cd $O/$N && /usr/bin/time -v -o time_run.log ../$B/obj/Vtb_xdie_s81_2 +NS=$NS +NM=$NM "$@" > run.log 2>&1 )
grep -E "^XDIE2_CFG|^XDIE_STATS|^XDIE_MU|^XDIE_LINK|^PASS|^FAIL|^MISMATCH|^LATE|^TAGBAD" $O/$N/run.log | head -14
grep -q "^PASS xdie_s81" $O/$N/run.log && { echo "BENCH_PASS $N"; exit 0; }; echo "BENCH_FAIL $N"; exit 1
