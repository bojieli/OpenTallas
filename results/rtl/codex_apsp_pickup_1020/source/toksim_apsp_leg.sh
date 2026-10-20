#!/bin/bash
# TOKSIM-S81D/APSP 10-20: the sparse-layer a_proj NODE (a_proj 448 rows + compressor.wkv/wgate + indexer.weights_proj BF16
# rows, all x = attn_norm) of layer L on every frame of slice 0, on the RELEASE frame exes of the die instances
# (TOKSIM-S81C/FSEQ v_* = FSMALL build_seq.sh release 19bf4121e masters + tb_toksim_fgu_seq +RETIRE +PHASE_VM).
#  gen   toksim_apsp_place.py gen (xs_place.compile_frame, ops [attn.cmp_idx]: phase 0 a_proj, phases 1..5 the BF rows)
#  single every phase alone + swap/shift mutants of the first BF phase (xs_place check + scaled weights_proj tie)
#  seq   seq_all (a_proj + BF phases) and seq_bf (BF phases only) swept over a uniform go period, +RETIRE=1 +PHASE_VM=1,
#        toksim_apsp_place.py seqcheck (toksim_fgu_check seq: golden segment tree bit-exact, coverage, one tag,
#        cycle-exact calendar, fixture tie; + the scaled weights_proj tie)
# usage: toksim_apsp_leg.sh L ["PERS"]
set -u
R=/srv/opentallas-scratch/claude/toksim-s81d-apsp; L=$1; PERS=${2:-"200 220 226 228 229 230 231 232 236 240 260 300"}
cd $R/src; Q=tools/s81_dv/layer_prog/qf_producer
FIX=$R/fix/$L; DIE=$R/dieref_t; VR=$R/vec/$L; O=$R/out/$L; mkdir -p $O $VR
FR="u_f_0L00 u_f_0L01 u_f_0L02 u_f_0L03 u_f_0R00 u_f_0R01 u_f_0R02 u_f_0R03"
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
$V --version > $O/verilator.version 2>&1; cat $O/verilator.version
sha256sum $R/exe/*/Vtb_toksim_fgu_seq > $O/exe.sha256
for F in $FR; do echo $F; done | xargs -P 8 -I{} bash -c 'python3 '$Q'/toksim_apsp_place.py gen --layer '$L' --frame {} --fixtures '$FIX' --die-src '$DIE' --out '$VR'/{} > '$O'/gen_{}.log 2>&1; echo "{} gen rc=$? $(tail -n 1 '$O'/gen_{}.log)"' | sort > $O/gen.txt
cat $O/gen.txt
exe_of() { case $1 in u_f_?L00|u_f_?R00) echo $R/exe/v_h9nx_e5/Vtb_toksim_fgu_seq;; u_f_?L01|u_f_?R01) echo $R/exe/v_h10_e2/Vtb_toksim_fgu_seq;;
  u_f_?L02|u_f_?R02) echo $R/exe/v_h9MX_e1/Vtb_toksim_fgu_seq;; u_f_?L03|u_f_?R03) echo $R/exe/v_h9nx_e2/Vtb_toksim_fgu_seq;; esac; }
export -f exe_of; export R Q O VR L
# singles + mutants
for F in $FR; do for d in $VR/$F/p* $VR/$F/m_*; do [ -f $d/ARGS ] && echo "$F $d"; done; done | xargs -P 24 -L 1 bash -c 'F=$0; d=$1; n=$(basename $d); X=$(exe_of $F);
  timeout 900 $X $(cat $d/ARGS) > $O/run_${F}_$n.log 2>&1; rc=$?
  python3 $Q/toksim_apsp_place.py single --dir $d --log $O/run_${F}_$n.log > $O/check_${F}_$n.txt 2>&1; crc=$?
  echo "$F $n rc=$rc check_rc=$crc $(grep -h "XS_PLACE_CHECK\|APSP_SCALED" $O/check_${F}_$n.txt | tr "\n" " ") $(python3 $Q/toksim_fgu_check.py single --log $O/run_${F}_$n.log)"' | sort -V > $O/singles.txt
cat $O/singles.txt
# sequences
for F in $FR; do for S in seq_all seq_bf; do [ -f $VR/$F/$S/seq.json ] && for P in $PERS; do echo "$F $S $P"; done; done; done | xargs -P 32 -L 1 bash -c 'F=$0; S=$1; P=$2; X=$(exe_of $F); SD=$VR/$F/$S;
  read NPH K OPS PH0 <<< $(python3 -c "import json;d=json.load(open(\"$VR/$F/frame.json\"))[\"seqs\"][\"$S\"];print(d[\"nph\"],d[\"K\"],d[\"ops\"],d[\"ph0\"])");
  T=$((NPH * P + 1200)); tg=${F}_${S}_P$P
  timeout 1200 $X +OT_ROM_DIR=$SD +T=$T +K=$K +OPS=$OPS +PH=$PH0 +NPH=$NPH +PER=$P +RETIRE=1 +PHASE_VM=1 > $O/run_$tg.log 2>&1; rc=$?
  echo "APSP $L $F $S P $P rc=$rc $(python3 $Q/toksim_apsp_place.py seqcheck --seq $SD --vec $VR/$F --log $O/run_$tg.log --out $O/res_$tg.json --per $P --ref-go 63 2>&1 | tail -n 1)"' | sort -V > $O/sweep.txt
cat $O/sweep.txt
for f in $O/run_*.log; do gzip -f $f; done
echo TOKSIM_APSP_LEG_DONE $L
