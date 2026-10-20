#!/bin/bash
# TOKSIM-S81B/FSMALL 10-19: build the frame bench exe of one RELEASE die frame class (GEN mu4c 19bf4121e die.v masters:
# u_f_0L00/0R00 col_h9_l4_nx lk b6d (LK5), u_f_0L01/0R01 col_h10_l4 lk 492 (LK2), u_f_0L02/0R02 col_h9_MX_l4 lk 249 (LK1),
# u_f_0L03/0R03 col_h9_l4_nx lk 492 (LK2)) on tb_toksim_fgu_seq.sv (TOKSIM-S81B/FGU: tb_s81dv_frame tok2 be4b5013e + +PH
# phase select / go sequence; DUT untouched).  usage: build_seq.sh MASTER LK LDLY NAME  (cwd = src root)
set -u
M=$1; LK=$2; LDLY=$3; O=$(realpath -m ../$4); mkdir -p $O; Q=tools/s81_dv/layer_prog/qf_producer
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
$V --version | tee $O/verilator.version
FR=rtl/dsrom_sys/s81_dv/frame_l4
EXTRA=""; case $M in col_h9_MX_l4) EXTRA="$FR/col_h9_l4.sv";; esac
SRCS="$EXTRA $FR/$M.sv $FR/${M}_b.sv rtl/dsrom_sys/s81_dv/land/dsfd_cfifo_crs4.sv rtl/dsrom_sys/s81_dv/land/ot_s81_land.sv rtl/dsrom_sys/s81_dv/frame/dsfd_rly_frame_exact.sv $Q/tb_toksim_fgu_seq.sv"
/usr/bin/time -v -o $O/time_build.log $V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-lint -Wno-style \
  -Wno-MULTIDRIVEN -DLK=$LK -DTB_FWD_GATE -DTB_LDLY=$LDLY -DFRAME=${M}_b -DDSFD_PQ_STATIC_X2 -DDSFD_PQ_HAS_BF_X2 \
  --top-module tb_toksim_fgu_seq -Mdir $O/obj -f tools/s81_dv/frame_bench.f $SRCS \
  --build-jobs 16 -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $O/build.log 2>&1 \
  || { echo "BUILD_FAILED"; grep -m8 -E "%Error" $O/build.log; tail -n 4 $O/build.log; exit 3; }
{ grep -v '^+incdir' tools/s81_dv/frame_bench.f; echo $SRCS | tr ' ' '\n'; } | sort -u | xargs sha256sum > $O/sources.sha256
ls -la $O/obj/Vtb_toksim_fgu_seq; echo FSMALL_BUILD_OK $4
