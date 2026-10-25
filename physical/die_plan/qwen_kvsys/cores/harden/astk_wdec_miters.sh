#!/bin/bash
# PATH-KV-ASTK 10-25: lockstep miters (self-contained, ot-run --stage): old r3 corner kits vs master kit $1 (W1|W2)
set -u
D=$(cd "$(dirname "$0")" && pwd); V=$1; K=$D/$V; M=$D/out_$V; OLD=$D/old
export PATH=$D/bin:$PATH
mkdir -p $M
mk() {  # mutant kit: name file sed-expr
  local n=$1 f=$2 e=$3 d=$M/kit_$1
  rm -rf $d; mkdir -p $d; cp -r $K/rtl $K/config.mk $K/core.json $d/
  sed -i "$e" $d/rtl/$f; cmp -s $d/rtl/$f $K/rtl/$f && { echo "MUTANT $n NOT APPLIED"; exit 3; }
}
mk mlo qkd_astk_leaves.sv 's/lo_n\[j_\] = {zc_n\[1:0\], sg_n, 3.b000} < tc\[9:1\];/lo_n[j_] = {zc_n[1:0], sg_n, 3'"'"'b000} < tq[9:1];/'
mk mzh qkd_astk_static_leaves.sv 's/\.clr(start)/.clr(1'"'"'b0)/'
[ $V = W2 ] && mk mkt qkd_astk_leaves.sv 's/kt_n\[i_\] = ki_ < tc/kt_n[i_] = ki_ <= tc/'
run() {  # name corner strap kit [mutfile]
  local n=$1 c=$2 s=$3 k=$4 mf=${5:-}
  python3 $D/tools/core_miter.py $OLD/$c $k $M/$n --new-mod kv3_astk --no-drops --strap "strap_corner=$s" \
    --bias u_strip_u_strip_u_ctl__aq=0:3000 ${mf:+--new-mod-file $mf} --cycles 60000 > $M/$n.prep.log 2>&1 || { echo "$n PREP FAIL"; tail -3 $M/$n.prep.log; return; }
  ( cd $M/$n && verilator --binary --timing -j 4 -MAKEFLAGS "OBJCACHE=" -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -DSYNTHESIS -Io -In --top-module tb --Mdir obj -f files.f > build.log 2>&1 ) || { echo "$n BUILD FAIL"; grep -m 8 -i "%Error" $M/$n/build.log; return; }
  ( cd $M/$n && docker run --rm --memory=16g -u $(id -u):$(id -g) -v $M:$M -w $M/$n --entrypoint ./obj/Vtb verilator/verilator:v5.032 > sim.log 2>&1 )
  echo "== $V $n: $(grep -E 'CORE MITER' $M/$n/sim.log)"
  rm -rf $M/$n/obj
}
run EN_nom EN "2'b11" $K & run ES_nom ES "2'b10" $K & wait
run WN_nom WN "2'b01" $K & run WS_nom WS "2'b00" $K & wait
run ES_mut_swap ES "2'b10" $K $D/mut_swap.sv & run EN_mut_lo EN "2'b11" $M/kit_mlo & wait
run WS_mut_zh WS "2'b00" $M/kit_mzh & if [ $V = W2 ]; then run WN_mut_kt WN "2'b01" $M/kit_mkt; else run EN_mut_wrongstrap EN "2'b10" $K; fi & wait
