#!/bin/bash
# xs_slice_bench.sh <outdir> <vecdir>... (cwd = kit / repo root): TOK-S81-GAPS/XS2b -- the die frame master's _l4 successor
# driven by the SLICE X STREAMER ot_s81sl_xs (tb rtl/dsrom_sys/s81_dv/frame/test/tb_s81dv_frame_xs.sv), the w17w10 spine
# path of tools/s81_dv/layer_prog/xs/xs_bench.sh alongside as the lockstep reference.  ONE Verilator build; one run per
# vector dir made by
#   python3 tools/s81_dv/layer_prog/xs_calendar.py gen --vec <xs_place gen vector> --out <vecdir> [--mutant M] [--tags rank]
# Logs <outdir>/run_<vec>.log; check: python3 tools/s81_dv/layer_prog/xs_calendar.py check --dir <vecdir> --log <log>
# Env: MASTER (col_h9), LK (5), LDLY (3), XS_DEFS (extra defines, e.g. -DOT_S81SL_XS_MUT_QSWAP), J (8).  Verilator 5.050.
set -u
O=$(realpath -m $1); shift; mkdir -p $O
MASTER=${MASTER:-col_h9}; LK=${LK:-5}; LDLY=${LDLY:-3}
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
$V --version > $O/verilator.version
FR=rtl/dsrom_sys/s81_dv/frame_l4
TOPF="$FR/${MASTER}_l4_b.sv rtl/dsrom_sys/s81_dv/land/dsfd_cfifo_crs4.sv rtl/dsrom_sys/s81_dv/land/ot_s81_land.sv"
XSF="rtl/dsrom_sys/s81_static_control/ot_s81_pq_calendar_reader.sv rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_stream_rom4_sel.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs_ctl.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs.sv"
SRCS="$FR/${MASTER}_l4.sv $TOPF rtl/dsrom_sys/s81_dv/frame/dsfd_rly_frame_exact.sv $XSF rtl/dsrom_sys/s81_dv/frame/test/tb_s81dv_frame_xs.sv"
if [ ! -x $O/obj/Vtb_s81dv_frame_xs ]; then
  /usr/bin/time -v -o $O/time_build.log $V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-lint -Wno-style \
    -Wno-MULTIDRIVEN -DLK=$LK -DTB_FWD_GATE -DTB_LDLY=$LDLY -DFRAME=${MASTER}_l4_b ${XS_DEFS:-} -DDSFD_PQ_STATIC_X2 -DDSFD_PQ_HAS_BF_X2 \
    --top-module tb_s81dv_frame_xs -Mdir $O/obj -f tools/s81_dv/frame_bench.f $SRCS \
    --build-jobs ${J:-8} -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $O/build.log 2>&1 \
    || { echo "BUILD_FAILED"; grep -m8 -E "%Error" $O/build.log; tail -n 4 $O/build.log; exit 3; }
fi
{ grep -v '^+incdir' tools/s81_dv/frame_bench.f; echo $SRCS | tr ' ' '\n'; } | sort -u | xargs sha256sum > $O/sources.sha256
for VD in "$@"; do
  n=$(basename $VD)
  $O/obj/Vtb_s81dv_frame_xs $(sed "s#+OT_ROM_DIR=[^ ]*#+OT_ROM_DIR=$(realpath $VD)#" $VD/ARGS) > $O/run_$n.log 2>&1
  echo "XSL_RUN $n rc=$? $(grep -m1 '^XSL_LOCKSTEP' $O/run_$n.log) $(grep -m1 '^END' $O/run_$n.log)"
done
echo XSL_BENCH_DONE
