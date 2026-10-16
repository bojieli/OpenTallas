#!/bin/bash
set -euo pipefail
mode=$1; out=$2
cd "$(dirname "$0")/../.."
mkdir -p "$out"
def=""
case "$mode" in
 pass) ;;
 input) def=-DOT_RLY4_INPUT_MUT ;;
 output) def=-DOT_RLY4_OUTPUT_MUT ;;
 edge) def=-DOT_RLY4_EDGE_MUT ;;
 reset) def=-DOT_RLY4_RESET_MUT ;;
 *) exit 2 ;;
esac
iverilog -g2012 $def -s tb -o "$out/sim" tools/s81_static_net/tb_rly4.sv rtl/dsrom_sys/s81_glue/test/actual_rly1_reference.sv rtl/dsrom_sys/s81_glue/ot_s81_rly4.sv
if vvp "$out/sim" > "$out/run.log" 2>&1;then rc=0;else rc=$?;fi
cat "$out/run.log"
if [ "$mode" = pass ];then test "$rc" = 0;grep -q 'RLY4_EXACT PASS' "$out/run.log";else
 if [ "$rc" = 0 ];then echo 'MUTANT INCORRECTLY PASSED';exit 0;fi
 grep -q RLY4_MISMATCH "$out/run.log" || exit 2
 echo "RLY4_MUTANT_REJECTED $mode";exit 1
fi
