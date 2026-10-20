#!/bin/bash
# TOKSIM-S81C/FSDN 10-19: ffn.down of a REPRESENTATIVE LAYER (L0 | L2 | L14 | L20) on the RELEASE frame RTL (GEN mu4c 19bf4121e:
# u_f_0L00 = col_h9_l4_nx, LK 5).  = toksim_fdown_frame_bench.sh (TOKSIM-S81B/FDOWN) with (a) the layer's own field
# (toksim_fsdn_frame_gen.py --layer: XS_OPS[layer] + BF_OPS[layer], that layer's rank-0 fixture), (b) the FGU +RETIRE bench
# (tb_toksim_fgu_seq.sv @ claude/toksim-s81b-fgu-1019 4cd48a7ab; the exe OBJ is FGU job 4's build of the same sources) and
# +RETIRE=1 on every sequence run.  Per phase: single run + xs_place check (golden segment tree bit-exact, coverage,
# calendar edge-exact, fixture BF16 tie); per expert: phase sequence swept over the go period (toksim_fgu_check.py seq).
# cwd = src root; args: LAYER VEC FIX DIE OUT "PERS" OBJ
set -u
L=$1; VEC=$(realpath -m $2); FIX=$(realpath $3); DIE=$(realpath $4); O=$(realpath -m $5); PERS=$6; OBJ=$(realpath $7)
mkdir -p $O/obj; Q=tools/s81_dv/layer_prog/qf_producer
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
$V --version > $O/verilator.version; cat $O/verilator.version
EXE=$O/obj/Vtb_toksim_fgu_seq; cp $OBJ $EXE; sha256sum $OBJ $EXE > $O/exe.sha256
if [ ! -f $VEC/index.json ]; then
  /usr/bin/time -v -o $O/time_gen.log python3 $Q/toksim_fsdn_frame_gen.py --layer $L --frame u_f_0L00 --fixtures $FIX --die-src $DIE --out $VEC > $O/gen.log 2>&1 \
    || { echo GEN_FAILED; tail -20 $O/gen.log; exit 2; }
fi
tail -1 $O/gen.log
FR=rtl/dsrom_sys/s81_dv/frame_l4
SRCS="$FR/col_h9_l4_nx.sv $FR/col_h9_l4_nx_b.sv rtl/dsrom_sys/s81_dv/land/dsfd_cfifo_crs4.sv rtl/dsrom_sys/s81_dv/land/ot_s81_land.sv rtl/dsrom_sys/s81_dv/frame/dsfd_rly_frame_exact.sv $Q/tb_toksim_fgu_seq.sv"
{ grep -v '^+incdir' tools/s81_dv/frame_bench.f; echo $SRCS | tr ' ' '\n'; } | sort -u | xargs sha256sum > $O/sources.sha256
ls -d $VEC/p* $VEC/m_* | xargs -P 16 -I{} bash -c 'n=$(basename {}); timeout 900 '$EXE' $(sed "s#+OT_ROM_DIR=[^ ]*#+OT_ROM_DIR={}#" {}/ARGS) > '$O'/run_$n.log 2>&1; python3 '$Q'/../xs_place.py check --dir {} --log '$O'/run_$n.log --fixtures '$FIX' > '$O'/check_$n.out 2>&1; echo "$n rc=$? $(tail -1 '$O'/check_$n.out) $(python3 '$Q'/toksim_fgu_check.py single --log '$O'/run_$n.log)"' | sort -V > $O/singles.txt
cat $O/singles.txt
REF=$(grep -m1 -oP '^GO 0 \K\d+' $(ls $O/run_p*.log | head -1))
echo "REF_GO $REF"
for S in $VEC/seq_*; do sn=$(basename $S); read n ph0 K < <(python3 -c "import json;s=json.load(open('$S/seq.json'));print(len(s['phases']),s['phases'][0],s['K'])")
  for P in $PERS; do echo "$sn $P $n $ph0 $K"; done
done | xargs -P 16 -L1 bash -c 'sn=$0; P=$1; n=$2; ph0=$3; K=$4; T=$((200 + n * P + 1500)); timeout 900 '$EXE' +OT_ROM_DIR='$VEC'/$sn +T=$T +K=$K +OPS=4 +PH=$ph0 +NPH=$n +PER=$P +RETIRE=1 > '$O'/run_${sn}_P$P.log 2>&1; python3 '$Q'/toksim_fgu_check.py seq --seq '$VEC'/$sn --vec '$VEC' --log '$O'/run_${sn}_P$P.log --out '$O'/res_${sn}_P$P.json --per $P --ref-go '$REF' --fixtures '$FIX' 2>&1 | tail -1 | sed "s/^/$sn /"' | sort -V > $O/sweep.txt
cat $O/sweep.txt
for f in $O/run_*.log; do gzip -f $f; done
echo TOKSIM_FSDN_BENCH_DONE $L
