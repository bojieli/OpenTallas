#!/bin/bash
# TOKSIM-S81C/FSGU 10-19: one layer-class leg on the RELEASE frame RTL (19bf4121e).
#  (1) ffn.experts_gu of frame u_f_0L00 for fixture layer L (toksim_fsgu_gen.py: xs_place.compile_frame of the layer's
#      full field), every phase single + xs_place check (golden segment tree bit-exact, coverage, cycle-exact calendar,
#      fixture BF16 tie), swap/shift mutants, then the phase sequence +RETIRE=1 swept over the go period (toksim_fgu_check seq).
#      exe = FGU job 4 Vtb_toksim_fgu_seq (col_h9_l4_nx_b, LK5, +RETIRE; Verilator 5.050; release blobs 78/78).
#  (2) attn.a_proj (lower_xs phase-0 programme) of the slice's 7 a_proj frames for layer L on FSMALL's release-master
#      frame exes (one per master / lk), lower_xs check per frame.
# usage (cwd anywhere): toksim_fsgu_leg.sh L ["PERS" [GEN_OPS]]   (GEN_OPS ffn.experts_gu for a reduced fixture)
set -u
R=/srv/opentallas-scratch/claude/toksim-s81c-fsgu; L=$1; PERS=${2:-"141 142 143 144 145 146 147 150 160 200"}; GOPS=${3:-}
cd $R/src; Q=tools/s81_dv/layer_prog/qf_producer; LP=tools/s81_dv/layer_prog
O=$R/out/$L; VEC=$R/vec/$L; FIX=$R/fix/$L; DIE=$R/dieref_t; X=$R/exe/fgu_nx_e5/Vtb_toksim_fgu_seq
mkdir -p $O
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
$V --version > $O/verilator.version 2>&1; cat $O/verilator.version
sha256sum $X $R/exe/*/Vtb_toksim_fgu_seq > $O/exe.sha256
# (2) a_proj gens in the background while experts_gu compiles
( for F in u_f_0L00 u_f_0L01 u_f_0L02 u_f_0L03 u_f_0R00 u_f_0R01 u_f_0R02; do echo $F; done | xargs -P 7 -I{} bash -c \
  'python3 '$LP'/lower_xs.py gen --frame {} --out '$VEC'/ap_{} --fixtures '$FIX' --die-src '$DIE' > '$O'/gen_ap_{}.log 2>&1; echo "{} gen rc=$?"' ) > $O/gen_ap.txt 2>&1 &
AP=$!
/usr/bin/time -v -o $O/time_gen.log python3 $Q/toksim_fsgu_gen.py --layer $L --frame u_f_0L00 --fixtures $FIX --die-src $DIE --out $VEC ${GOPS:+--ops $GOPS} > $O/gen.log 2>&1 \
  || { echo GEN_FAILED; tail -20 $O/gen.log; }
tail -1 $O/gen.log
wait $AP; cat $O/gen_ap.txt
for F in u_f_0L00 u_f_0L01 u_f_0L02 u_f_0L03 u_f_0R00 u_f_0R01 u_f_0R02; do echo $F; done | xargs -P 7 -I{} bash -c 'F={};
  case $F in u_f_?L00|u_f_?R00) B=s_h9nx_e5;; u_f_?L01|u_f_?R01) B=s_h10_e2;; u_f_?L02|u_f_?R02) B=s_h9MX_e1;; u_f_?L03|u_f_?R03) B=s_h9nx_e2;; esac
  VD='$VEC'/ap_$F; timeout 900 '$R'/exe/$B/Vtb_toksim_fgu_seq $(sed "s#+OT_ROM_DIR=[^ ]*#+OT_ROM_DIR=$VD#" $VD/ARGS) > '$O'/run_ap_$F.log 2>&1; rc=$?
  python3 '$LP'/lower_xs.py check --dir $VD --log '$O'/run_ap_$F.log > '$O'/check_ap_$F.txt 2>&1; crc=$?
  echo "FSGU_AP '$L' $F exe $B rc=$rc check_rc=$crc $(python3 '$Q'/toksim_fgu_check.py single --log '$O'/run_ap_$F.log) | $(tail -n 1 '$O'/check_ap_$F.txt)"' | sort > $O/aproj.txt
cat $O/aproj.txt
[ -f $VEC/index.json ] || { echo NO_EXPERTS_VECTORS; exit 2; }
python3 $Q/toksim_fgu_seqw.py $VEC seq_experts_gu
ls -d $VEC/p* $VEC/m_* | xargs -P 16 -I{} bash -c 'n=$(basename {}); timeout 900 '$X' $(sed "s#+OT_ROM_DIR=[^ ]*#+OT_ROM_DIR={}#" {}/ARGS) > '$O'/run_$n.log 2>&1; python3 '$LP'/xs_place.py check --dir {} --log '$O'/run_$n.log > '$O'/check_$n.out 2>&1; echo "$n rc=$? $(tail -1 '$O'/check_$n.out) $(python3 '$Q'/toksim_fgu_check.py single --log '$O'/run_$n.log)"' | sort -V > $O/singles.txt
cat $O/singles.txt
REF=$(grep -m1 -oP '^GO 0 \K\d+' $(ls $O/run_p*.log | head -1)); echo "REF_GO $REF"
S=$VEC/seq_experts_gu; n=$(python3 -c "import json;print(len(json.load(open('$S/seq.json'))['phases']))"); ph0=$(python3 -c "import json;print(json.load(open('$S/seq.json'))['phases'][0])")
for P in $PERS; do echo $P; done | xargs -P 16 -I{} bash -c 'P={}; tg=seq_experts_gu_P${P}_R1;
  timeout 900 stdbuf -oL '$X' +OT_ROM_DIR='$S' +T=1600 +K=5120 +OPS=4 +PH='$ph0' +NPH='$n' +PER=$P +RETIRE=1 > '$O'/run_$tg.log 2>&1;
  echo "$tg rc=$? $(python3 '$Q'/toksim_fgu_check.py seq --seq '$S' --vec '$VEC' --fixtures '$FIX' --log '$O'/run_$tg.log --out '$O'/res_$tg.json --per $P --ref-go '$REF' 2>&1 | tail -1)"' | sort -V > $O/sweep.txt
cat $O/sweep.txt
for f in $O/run_*.log; do gzip -f $f; done
echo TOKSIM_FSGU_LEG_DONE $L
