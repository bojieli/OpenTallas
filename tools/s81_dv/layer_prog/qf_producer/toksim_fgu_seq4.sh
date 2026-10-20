#!/bin/bash
# TOKSIM-S81B/FGU 10-19 job 4: rebuild tb_toksim_fgu_seq (+RETIRE row write-back to the spine; build flags = toksim_fgu_bench.sh)
# and run the phase-sequence go-period sweep of BOTH ops with +RETIRE=1 (experts_gu: 24 phases; shared_gu: 4), plus a
# shared_gu +RETIRE=0 control at P 160/200 (must equal job 3 / diag1).  Vectors = job 3's (VEC); cwd = src root.
# args: VEC FIX OUT
set -u
VEC=$(realpath $1); FIX=$(realpath $2); O=$(realpath -m $3); mkdir -p $O; Q=tools/s81_dv/layer_prog/qf_producer
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
$V --version | tee $O/verilator.version
FR=rtl/dsrom_sys/s81_dv/frame_l4; LK=5; LDLY=3
SRCS="$FR/col_h9_l4_nx.sv $FR/col_h9_l4_nx_b.sv rtl/dsrom_sys/s81_dv/land/dsfd_cfifo_crs4.sv rtl/dsrom_sys/s81_dv/land/ot_s81_land.sv rtl/dsrom_sys/s81_dv/frame/dsfd_rly_frame_exact.sv $Q/tb_toksim_fgu_seq.sv"
if [ ! -x $O/obj/Vtb_toksim_fgu_seq ]; then
  /usr/bin/time -v -o $O/time_build.log $V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-lint -Wno-style \
    -Wno-MULTIDRIVEN -DLK=$LK -DTB_FWD_GATE -DTB_LDLY=$LDLY -DFRAME=col_h9_l4_nx_b -DDSFD_PQ_STATIC_X2 -DDSFD_PQ_HAS_BF_X2 \
    --top-module tb_toksim_fgu_seq -Mdir $O/obj -f tools/s81_dv/frame_bench.f $SRCS \
    --build-jobs 16 -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $O/build.log 2>&1 \
    || { echo "BUILD_FAILED"; grep -m8 -E "%Error" $O/build.log; tail -n 4 $O/build.log; exit 3; }
fi; echo BUILD_OK
{ grep -v '^+incdir' tools/s81_dv/frame_bench.f; echo $SRCS | tr ' ' '\n'; } | sort -u | xargs sha256sum > $O/sources.sha256
python3 $Q/toksim_fgu_seqw.py $VEC seq_experts_gu seq_shared_gu
{
 for P in 600 400 300 250 200 180 170 160 155 150 145 140; do echo "seq_experts_gu $P 24 20 1"; done
 for P in 159 157 155 153 151 149 147 145 143 141 160 200; do echo "seq_shared_gu $P 4 16 1"; done
 for P in 160 200; do echo "seq_shared_gu $P 4 16 0"; done
} | xargs -P 16 -L1 bash -c 'sn=$0; P=$1; n=$2; ph0=$3; R=$4; tg=${sn}_P${P}_R$R;
  timeout 900 stdbuf -oL '$O'/obj/Vtb_toksim_fgu_seq +OT_ROM_DIR='$VEC'/$sn +T=1600 +K=5120 +OPS=4 +PH=$ph0 +NPH=$n +PER=$P +RETIRE=$R > '$O'/run_$tg.log 2>&1;
  echo "$tg rc=$? $(python3 '$Q'/toksim_fgu_check.py seq --seq '$VEC'/$sn --vec '$VEC' --fixtures '$FIX' --log '$O'/run_$tg.log --out '$O'/res_$tg.json --per $P --ref-go 63 2>&1 | tail -1)"' | sort -V | tee $O/sweep.txt
echo TOKSIM_FGU_SEQ4_DONE
