#!/bin/bash
# TOKSIM-S81B/FDOWN 10-19: ffn.down (shared FP8 + 6 routed FP4 experts, K 2304) on the RELEASE frame RTL (GEN mu4c
# 19bf4121e: u_f_0L00 = col_h9_l4_nx, LK 5), every down phase of the frame's real rows (L0 rank-0 fixture), golden-checked
# per row (xs_place check: segment-tree node values bit-exact, coverage, calendar edge-exact, fixture BF16 tie), then each
# expert's phase SEQUENCE back to back swept over the go period.  Bench = tb_toksim_fgu_seq.sv (TOKSIM-S81B/FGU, verbatim;
# tb_s81dv_frame + go sequence; DUT untouched).  The exe is built here unless OBJ (a built Vtb_toksim_fgu_seq of the same
# sources) is given.  cwd = src root (release rtl + tok2 tools); args: VEC FIX DIE OUT "PERS" [OBJ]
set -u
VEC=$(realpath -m $1); FIX=$(realpath $2); DIE=$(realpath $3); O=$(realpath -m $4); PERS=${5:-"600 400 300 260 240 224 200 180"}; OBJ=${6:-}
mkdir -p $O; Q=tools/s81_dv/layer_prog/qf_producer
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
$V --version > $O/verilator.version; cat $O/verilator.version
FR=rtl/dsrom_sys/s81_dv/frame_l4; LK=5; LDLY=3
SRCS="$FR/col_h9_l4_nx.sv $FR/col_h9_l4_nx_b.sv rtl/dsrom_sys/s81_dv/land/dsfd_cfifo_crs4.sv rtl/dsrom_sys/s81_dv/land/ot_s81_land.sv rtl/dsrom_sys/s81_dv/frame/dsfd_rly_frame_exact.sv $Q/tb_toksim_fgu_seq.sv"
EXE=$O/obj/Vtb_toksim_fgu_seq
[ -n "$OBJ" ] && [ -x "$OBJ" ] && { mkdir -p $O/obj; cp $OBJ $EXE; echo "EXE_FROM $OBJ"; }
( if [ ! -x $EXE ]; then
  /usr/bin/time -v -o $O/time_build.log $V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-lint -Wno-style \
    -Wno-MULTIDRIVEN -DLK=$LK -DTB_FWD_GATE -DTB_LDLY=$LDLY -DFRAME=col_h9_l4_nx_b -DDSFD_PQ_STATIC_X2 -DDSFD_PQ_HAS_BF_X2 \
    --top-module tb_toksim_fgu_seq -Mdir $O/obj -f tools/s81_dv/frame_bench.f $SRCS \
    --build-jobs 16 -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $O/build.log 2>&1 \
    || { echo "BUILD_FAILED"; grep -m8 -E "%Error" $O/build.log; tail -n 4 $O/build.log; exit 3; }
fi; echo BUILD_OK ) > $O/build.status 2>&1 &
BP=$!
if [ ! -f $VEC/index.json ]; then
  /usr/bin/time -v -o $O/time_gen.log python3 $Q/toksim_fdown_frame_gen.py --frame u_f_0L00 --fixtures $FIX --die-src $DIE --out $VEC > $O/gen.log 2>&1 \
    || { echo GEN_FAILED; tail -20 $O/gen.log; wait $BP; exit 2; }
fi
tail -2 $O/gen.log
wait $BP; cat $O/build.status; grep -q BUILD_OK $O/build.status || exit 3
{ grep -v '^+incdir' tools/s81_dv/frame_bench.f; echo $SRCS | tr ' ' '\n'; } | sort -u | xargs sha256sum > $O/sources.sha256
# single-phase runs (+NPH 1 = the original bench) and their xs_place checks, 16 at a time
ls -d $VEC/p* $VEC/m_* | xargs -P 16 -I{} bash -c 'n=$(basename {}); '$EXE' $(sed "s#+OT_ROM_DIR=[^ ]*#+OT_ROM_DIR={}#" {}/ARGS) > '$O'/run_$n.log 2>&1; python3 '$Q'/../xs_place.py check --dir {} --log '$O'/run_$n.log --fixtures '$FIX' > '$O'/check_$n.out 2>&1; echo "$n rc=$? $(tail -1 '$O'/check_$n.out) $(python3 '$Q'/toksim_fgu_check.py single --log '$O'/run_$n.log)"' | sort -V > $O/singles.txt
cat $O/singles.txt
REF=$(grep -m1 -oP '^GO 0 \K\d+' $(ls $O/run_p*.log | head -1))
echo "REF_GO $REF"
# per-expert phase-sequence sweep (T sized to the sequence: go0 + n PER + 1500)
for S in $VEC/seq_*; do sn=$(basename $S); read n ph0 K < <(python3 -c "import json;s=json.load(open('$S/seq.json'));print(len(s['phases']),s['phases'][0],s['K'])")
  for P in $PERS; do echo "$sn $P $n $ph0 $K"; done
done | xargs -P 16 -L1 bash -c 'sn=$0; P=$1; n=$2; ph0=$3; K=$4; T=$((200 + n * P + 1500)); '$EXE' +OT_ROM_DIR='$VEC'/$sn +T=$T +K=$K +OPS=4 +PH=$ph0 +NPH=$n +PER=$P > '$O'/run_${sn}_P$P.log 2>&1; python3 '$Q'/toksim_fgu_check.py seq --seq '$VEC'/$sn --vec '$VEC' --log '$O'/run_${sn}_P$P.log --out '$O'/res_${sn}_P$P.json --per $P --ref-go '$REF' --fixtures '$FIX' 2>&1 | tail -1 | sed "s/^/$sn /"' | sort -V > $O/sweep.txt
cat $O/sweep.txt
for f in $O/run_*.log; do gzip -f $f; done
echo TOKSIM_FDOWN_BENCH_DONE
