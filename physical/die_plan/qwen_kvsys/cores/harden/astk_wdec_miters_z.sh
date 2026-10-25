#!/bin/bash
# PATH-KV-ASTK 10-25: ctl Z-sideband coverage (small cal ages via --mask) for the zh replicas: nominal + 2 zh mutants
set -u
D=$(cd "$(dirname "$0")" && pwd); V=${1:-W2}; K=$D/$V; M=$D/out2_$V; OLD=$D/old
export PATH=$D/bin:$PATH
mkdir -p $M
mk() { local n=$1 f=$2 e=$3 d=$M/kit_$1
  rm -rf $d; mkdir -p $d; cp -r $K/rtl $K/config.mk $K/core.json $d/
  sed -i "$e" $d/rtl/$f; cmp -s $d/rtl/$f $K/rtl/$f && { echo "MUTANT $n NOT APPLIED"; exit 3; }; }
mk mzh qkd_astk_static_leaves.sv 's/\.clr(start)/.clr(1'"'"'b0)/'
mk mzi qkd_astk_static_leaves.sv 's/\.inc(!l_pend \&\& z_emit)/.inc(z_emit)/'
run() { local n=$1 c=$2 s=$3 k=$4
  python3 $D/tools/core_miter.py $OLD/$c $k $M/$n --new-mod kv3_astk --no-drops --strap "strap_corner=$s" \
    --bias u_strip_u_strip_u_ctl__aq=0:1500 --mask u_strip_u_strip_u_ctl__cal=003f000f --cycles 60000 > $M/$n.prep.log 2>&1 || { echo "$n PREP FAIL"; tail -3 $M/$n.prep.log; return; }
  ( cd $M/$n && verilator --binary --timing -j 4 -MAKEFLAGS "OBJCACHE=" -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -DSYNTHESIS -Io -In --top-module tb --Mdir obj -f files.f > build.log 2>&1 ) || { echo "$n BUILD FAIL"; grep -m 8 -i "%Error" $M/$n/build.log; return; }
  ( cd $M/$n && docker run --rm --memory=16g -u $(id -u):$(id -g) -v $M:$M -w $M/$n --entrypoint ./obj/Vtb verilator/verilator:v5.032 > sim.log 2>&1 )
  echo "== $V $n: $(grep -E 'CORE MITER' $M/$n/sim.log)"; rm -rf $M/$n/obj; }
run EN_nomZ EN "2'b11" $K & run WS_nomZ WS "2'b00" $K & wait
run EN_mut_zhclr EN "2'b11" $M/kit_mzh & run WS_mut_zhinc WS "2'b00" $M/kit_mzi & wait
