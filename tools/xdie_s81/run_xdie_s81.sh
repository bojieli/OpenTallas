#!/bin/bash
# run_xdie_s81.sh <outdir> <name> <golden dir> [MODE ep|master] [-G... / +define+... verilator args]   (cwd = repo root)
# TOKEN-XDIE-S81 multi-die collective co-sim (tb_xdie_s81): build + run one configuration under Verilator.
# Lane tile build = the hardened kit's params (physical/ref_tile/dscoll_lane_w_rt spec: GFMT 1, EPPIPE 2) + LCR 1.
# LANE=<file> (env) replaces the lane tile RTL ot_s81ph_coll_lane.sv (kit mutant benches).
# Prints the bench verdict line; exit 0 = "PASS xdie_s81", 1 = FAIL, 3 = build failure.
set -u; O=$1; N=$2; G=$3; MODE=${4:-ep}; shift 4 || shift $#
mkdir -p $O/$N
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
L=rtl/dsrom_sys/s81_link
SRCS="rtl/link/ot_link_crc32.sv rtl/common/ot_link_credit.sv rtl/lib/ot_rst_relay.sv rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv
 rtl/dsrom_sys/s81_ph/ot_s81ph_link_ep.sv rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx.sv rtl/dsrom_sys/s81_ph/ot_s81ph_rfifo.sv
 rtl/dsrom_sys/s81_ph/coll/ot_s81ph_skid2.sv rtl/dsrom_sys/s81_ph/coll/ot_s81ph_ckbuf.sv rtl/dsrom_sys/s81_ph/coll/dsfd_coll_split.sv ${LANE:-rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane.sv}
 $L/ot_s81_kp4_common.sv $L/ot_s81_kp4_enc.sv $L/ot_s81_kp4_bm.sv $L/ot_s81_kp4_dsyn.sv $L/ot_s81_kp4_ddly.sv $L/ot_s81_kp4_dchn.sv
 $L/ot_s81_kp4_dout.sv $L/ot_s81_kp4_dec.sv $L/ot_pdie_serdes.sv
 physical/asap7_memory_macros/ot_sram_1r1w2c_64x546_m1/ot_sram_1r1w2c_64x546_m1.v
 physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v
 physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v
 rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rstop.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_lep.sv
 rtl/test/xdie_s81/xdie_s81.vlt rtl/test/xdie_s81/xdie_s81_ep.sv rtl/test/xdie_s81/tb_xdie_s81.sv"
D="+define+OT_S81PH_GBX_FMT1 +define+OT_S81PH_EP_PIPE2"
if [ $MODE = master ]; then
  D="$D +define+XDIE_MASTER +define+DSFD_PQ_STATIC_X2"
  MAC="physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v physical/asap7_memory_macros_v2/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v"
  CEN="rtl/dsrom_sys/s81_dv/ot_s81dv_norm.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xr.sv
   rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xg.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap.sv
   rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs_ctl.sv rtl/dsrom_sys/s81_static_net/ot_s81_retn_static.sv
   rtl/dsrom_sys/s81_static_control/ot_s81_pq_calendar_reader.sv rtl/dsrom_sys/s81_static_control/ot_s81_pq_calendar_rom.sv
   rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_stream_rom4_sel.sv rtl/dsrom_sys/s81_die_bind/dsfd_sp_pq_n.sv rtl/v41rom/ot_v41_kreg.sv rtl/common/ot_prefix.sv
   rtl/hdc/v41x/ot_hdc_v41x_vec_side.sv rtl/dsrom_sys/engram/mix/ot_s81_engram_mix.sv rtl/dsrom_sys/s81_dv/eng/ot_s81sl_ve.sv
   $(ls rtl/dsrom_sys/s81_dv/eng/ot_s81sl_eg*.sv 2>/dev/null | tr '\n' ' ')"
  SRCS="$(cat physical/hbm_norm_split_20261008/sources.f rtl/dsrom_sys/s81_dv/slice/test/leaf_bench.f | sort -u | tr '\n' ' ') $MAC $CEN $SRCS"
fi
/usr/bin/time -v -o $O/$N/time_build.log $V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-lint -Wno-style \
  +incdir+$L $D "$@" --top-module tb_xdie_s81 -Mdir $O/$N/obj $SRCS --build-jobs ${J:-8} \
  -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $O/$N/build.log 2>&1 \
  || { echo "BUILD_FAILED $N"; grep -m10 -E "%Error" $O/$N/build.log; exit 3; }
grep -E "PINMISSING|PINCONNECTEMPTY|PINNOCONNECT" $O/$N/build.log | grep -v -E "tb_xdie_s81|xdie_s81_ep" | head -8
cp $G/stim.hex $O/$N/stim.hex
NS=$(cat $G/NS)
( cd $O/$N && /usr/bin/time -v -o time_run.log ./obj/Vtb_xdie_s81 +NS=$NS > run.log 2>&1 )
grep -E "^XDIE_STATS|^PASS|^FAIL|^MISMATCH|^LATE" $O/$N/run.log | head -12
grep -q "^PASS xdie_s81" $O/$N/run.log && { echo "BENCH_PASS $N"; exit 0; }; echo "BENCH_FAIL $N"; exit 1
