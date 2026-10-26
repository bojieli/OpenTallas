#!/bin/bash
# eqv.sh OUTDIR GOLD_FRONT GOLD_FILE GATE_FRONT GATE_FILE TOP "PARAMS(k=v ...)"  -> prints EQ / NEQ / ERR
Y=/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys
O=$1; GF=$2; GS=$3; TF=$4; TS=$5; TOP=$6; P="$7"; P2="${8:-$7}"; tag=$(echo "$GF-$(basename $(dirname $GS))-$TF-$(basename $(dirname $TS))-$TOP-$P-vs-$P2" | tr " =" "_-")
rd(){ local P="$3"; if [ $1 = slang ]; then g=""; for kv in $P; do g="$g -G $kv"; done; echo "read_slang $2 --top $TOP $g"; else c=""; for kv in $P; do c="$c -set ${kv%%=*} ${kv#*=}"; done; echo "read_verilog -sv $2; ${c:+chparam$c $TOP;}"; fi; }
$Y -q -l $O/$tag.log -p "$(rd $GF $GS "$P"); hierarchy -top $TOP; prep -flatten -top $TOP; async2sync; rename $TOP gold; design -stash g; $(rd $TF $TS "$P2"); hierarchy -top $TOP; prep -flatten -top $TOP; async2sync; rename $TOP gate; design -stash t; design -copy-from g -as gold gold; design -copy-from t -as gate gate; equiv_make gold gate eq; hierarchy -top eq; equiv_simple -seq 2; equiv_induct -seq 2; equiv_status -assert" >/dev/null 2>&1
rc=$?; u=$(grep -o 'Found [0-9]* unproven' $O/$tag.log | tail -1); e=$(grep -o 'Found [0-9]* \$equiv cells' $O/$tag.log | tail -1)
if [ $rc = 0 ]; then echo "EQ   $tag ($e)"; elif grep -q unproven $O/$tag.log; then echo "NEQ  $tag ($u of $e)"; else echo "ERR  $tag $(grep -m1 ERROR $O/$tag.log)"; fi
