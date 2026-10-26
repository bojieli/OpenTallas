#!/usr/bin/env bash
# HBMc/TOKEN2 (10-22): unpatched CONN_EQUIV + collar programme/fault path bench on one GEN die case.
#   collar_gen_check.sh <GEN case dir with die.v> <contract.json> <contract_die_v.py> <bundle root> <OUT>
# --open-zero leaves GEN-open inputs at 0 (nothing is patched from the contract): release-valid when CONN_EQUIV PASS.
set -eu
D=$1; C=$2; CDV=$3; BUNDLE=$4; OUT=$5; G=$(dirname $(readlink -f $0)); mkdir -p $OUT
python3 $G/gen_die_func.py --die $D/die.v --contract $C --cdv $CDV --out $OUT/die_func.v --report $OUT/conn_equiv.json --open-zero | tail -n 1
python3 $G/collar_path_bench.py --die $OUT/die_func.v --contract $C --out $OUT/collar
BUNDLE=$BUNDLE DIR=$OUT/collar $G/run_collar_bench.sh
python3 $G/rowv_align_bench.py --die $OUT/die_func.v --contract $C --out $OUT/rowv && BUNDLE=$BUNDLE DIR=$OUT/rowv $G/run_collar_bench.sh >/dev/null; grep -h "ROWV_ALIGN" $OUT/rowv/run.log
