#!/bin/bash
# KV-CORE-RTL 10-25 am-g-drop lockstep miters (ahub + 4 ASTK cores): nominal + mutants, Verilator 5.032 (docker)
set -u
R=/srv/opentallas-scratch2/claude/kv-cores-1025r; M=$R/am_g_miter
H=/srv/opentallas-scratch2/claude/wt/kv-core-rtl-1025/physical/die_plan/qwen_kvsys/cores/harden
export PATH=$R/bin:$PATH
mkdir -p $M
run() {  # name old new [mutant-wrapper]
  local n=$1 o=$2 nw=$3 mf=${4:-}
  python3 $H/core_miter.py $o $nw $M/$n ${mf:+--new-mod-file $mf} --cycles ${CYC:-20000} > $M/$n.prep.log 2>&1 || { echo "$n PREP FAIL"; tail -3 $M/$n.prep.log; return; }
  ( cd $M/$n && verilator --binary --timing -j 4 -MAKEFLAGS "OBJCACHE=" -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN \
      -DSYNTHESIS -Io -In --top-module tb --Mdir obj -f files.f > build.log 2>&1 ) || { echo "$n BUILD FAIL"; grep -m 8 -i "%Error" $M/$n/build.log; return; }
  ( cd $M/$n && docker run --rm --memory=16g -u $(id -u):$(id -g) -v $M:$M -w $M/$n --entrypoint ./obj/Vtb verilator/verilator:v5.032 > sim.log 2>&1 )
  echo "== $n: $(grep -E 'CORE MITER' $M/$n/sim.log) $(grep -m 2 -E 'MISMATCH|NONZERO' $M/$n/sim.log | tr '\n' ' ')"
}
mk_mut() {  # kit mod mutant out
  python3 -c "import sys; sys.path.insert(0,'$H'); import am_g_drop as A; m=sys.argv[3]; mu=(True if m=='True' else m); open(sys.argv[4],'w').write(A.transform(open(sys.argv[1]).read(), sys.argv[2], mu))" "$1" "$2" "$3" "$4"
}
WHICH=${1:-all}
if [ "$WHICH" = all ] || [ "$WHICH" = ahub ]; then
  O=$R/ahub/r3base/qkd_ahub__604.8x440.64; N=$R/ahub/r3/qkd_ahub__604.8x440.64
  run ahub_nom $O $N
  mk_mut $O/rtl/qkd_ahub.sv qkd_ahub True $M/ahub_mut_map.sv && run ahub_mut_map $O $N $M/ahub_mut_map.sv
fi
for c in ${ASTK:-EN ES WN WS}; do
  [ "$WHICH" = all ] || [ "$WHICH" = astk ] || continue
  O=$R/astk/r3base/kv3_astk_${c}__190.08x181.44; N=$R/astk/r3/kv3_astk_${c}__190.08x181.44
  run astk_${c}_nom $O $N
  if [ "$c" = EN ]; then
    mk_mut $O/rtl/kv3_astk_$c.sv kv3_astk_$c map $M/astk_${c}_mut_map.sv && run astk_${c}_mut_map $O $N $M/astk_${c}_mut_map.sv
    mk_mut $O/rtl/kv3_astk_$c.sv kv3_astk_$c gconst $M/astk_${c}_mut_gconst.sv && run astk_${c}_mut_gconst $O $N $M/astk_${c}_mut_gconst.sv
  fi
done
