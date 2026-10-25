#!/bin/bash
set -euo pipefail
mode=$1; out=$2
cd "$(dirname "$0")/../.."
mkdir -p "$out"
python3 tools/s81_static_net/prepare_sstn_split_bench.py "$out"
def=""
case "$mode" in
 pass) ;;
 base_control) def=-DOT_SSTN_BASE_CONTROL_MUT ;;
 base_status_unreg) def=-DOT_SSTN_BASE_STATUS_UNREG_MUT ;;
 payload_bit) def=-DOT_SSTN_PAYLOAD_BIT_MUT ;;
 payload_reset) def=-DOT_SSTN_PAYLOAD_RESET_MUT ;;
 payload_edge) def=-DOT_SSTN_PAYLOAD_EDGE_MUT ;;
 *) exit 2 ;;
esac
iverilog -g2012 $def -s tb -o "$out/sim" "$out/tb.sv" -f "$out/sources.f" > "$out/build.log" 2>&1 || { tail -10 "$out/build.log";exit 2; }
if vvp "$out/sim" > "$out/run.log" 2>&1;then rc=0;else rc=$?;fi
cat "$out/run.log"
if [ "$mode" = pass ];then test "$rc" = 0;grep -q 'SSTN_SPLIT_EXACT PASS' "$out/run.log";else
 if [ "$rc" = 0 ];then echo 'MUTANT INCORRECTLY PASSED';exit 0;fi
 grep -q SSTN_SPLIT_MISMATCH "$out/run.log" || exit 2
 echo "SSTN_SPLIT_MUTANT_REJECTED $mode";exit 1
fi
