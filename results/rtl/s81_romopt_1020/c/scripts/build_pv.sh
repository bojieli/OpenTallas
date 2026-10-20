#!/bin/bash
# S81-ROMOPT-C 10-20: the RELEASE FSEQ frame exe (toksim-s81c-fseq build_seq.sh, same src2 tree = sources of the v_* release
# exes) with -DTB_PVTRACE (element pv trace, simulation-only bind; DUT untouched).  usage: build_pv.sh MASTER LK LDLY NAME
set -u
M=$1; LK=$2; LDLY=$3; L=/srv/opentallas-scratch/claude/s81-romopt-c; O=$L/$4; mkdir -p $O
cd /srv/opentallas-scratch/claude/toksim-s81c-fseq/src2; Q=tools/s81_dv/layer_prog/qf_producer
V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
$V --version | tee $O/verilator.version
FR=rtl/dsrom_sys/s81_dv/frame_l4
EXTRA=""; case $M in col_h9_MX_l4) EXTRA="$FR/col_h9_l4.sv";; esac
SRCS="$EXTRA $FR/$M.sv $FR/${M}_b.sv rtl/dsrom_sys/s81_dv/land/dsfd_cfifo_crs4.sv rtl/dsrom_sys/s81_dv/land/ot_s81_land.sv rtl/dsrom_sys/s81_dv/frame/dsfd_rly_frame_exact.sv $Q/tb_toksim_fgu_seq.sv"
/usr/bin/time -v -o $O/time_build.log $V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-lint -Wno-style \
  -Wno-MULTIDRIVEN -DLK=$LK -DTB_FWD_GATE -DTB_LDLY=$LDLY -DFRAME=${M}_b -DDSFD_PQ_STATIC_X2 -DDSFD_PQ_HAS_BF_X2 -DTB_PVTRACE \
  --top-module tb_toksim_fgu_seq -Mdir $O/obj -f tools/s81_dv/frame_bench.f $SRCS \
  --build-jobs 16 -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $O/build.log 2>&1 \
  || { echo "BUILD_FAILED"; grep -m8 -E "%Error" $O/build.log; tail -n 4 $O/build.log; exit 3; }
{ grep -v '^+incdir' tools/s81_dv/frame_bench.f; echo $SRCS | tr ' ' '\n'; } | sort -u | xargs sha256sum > $O/sources.sha256
ls -la $O/obj/Vtb_toksim_fgu_seq; echo PV_BUILD_OK $4
