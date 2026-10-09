#!/usr/bin/env bash
# Exact bench + negative mutants for the centre-aligned forwarded-clock station. Golden must PASS; every mutant FAIL.
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd); ROOT=$(cd "$HERE/../.." && pwd)
RTL=$ROOT/rtl/physical/ot_qwen_link_fwd_cx_tmr.sv
OUT=${1:-$(mktemp -d)}; mkdir -p "$OUT"
run() { # name rtl neg
  iverilog -g2012 -s tb_qwen_link_fwd_cx -Ptb_qwen_link_fwd_cx.NEG=$3 -o "$OUT/$1.vvp" "$2" "$HERE/pair_cx.sv" "$HERE/tb_cx.sv" > "$OUT/$1.compile.log" 2>&1 || { echo "$1 COMPILE_FAIL"; return 2; }
  timeout 600 vvp "$OUT/$1.vvp" > "$OUT/$1.log" 2>&1; local rc=$?
  if grep -q '^PASS cx' "$OUT/$1.log" && [ $rc -eq 0 ]; then echo "$1 PASS"; else echo "$1 FAIL: $(grep -m1 -iE 'fatal|mismatch|leak' "$OUT/$1.log" | cut -c1-120)"; fi
}
mut() { # name sed-expr
  sed "$2" "$RTL" > "$OUT/$1.sv"; cmp -s "$RTL" "$OUT/$1.sv" && { echo "$1 MUTATION_NOT_APPLIED"; return; }
  run "$1" "$OUT/$1.sv" 0
}
{
run golden "$RTL" 0
run neg_wrong_clock "$RTL" 1
mut mut_vote_and 's/assign release_run=(release1\[0\]&release1\[1\]) |/assign release_run=(release1[0]\&release1[1]\&release1[2]) | 1'"'"'b0 \&/'
mut mut_vote_or  's/assign release_run=(release1\[0\]&release1\[1\]) |/assign release_run=release1[0] | release1[1] | release1[2] | 1'"'"'b0 \&/'
mut mut_fwd_noninverted 's/assign y=~a;/assign y=a;/'
mut mut_capture_rising 's/always @(negedge fclk_i) data_q/always @(posedge fclk_i) data_q/'
mut mut_control_rising 's/always @(negedge fclk_i or negedge release_run)/always @(posedge fclk_i or negedge release_run)/'
mut mut_single_chain 's/release1\[rail\]<=release0\[rail\];/release1[rail]<=1;/'
} | tee "$OUT/summary.txt"
pass=$(grep -c ' PASS$' "$OUT/summary.txt"); fail=$(grep -c ' FAIL' "$OUT/summary.txt")
if [ "$(sed -n 1p "$OUT/summary.txt")" = "golden PASS" ] && [ "$pass" -eq 1 ] && [ "$fail" -eq $(( $(wc -l < "$OUT/summary.txt") - 1 )) ]; then echo BENCH_OK; exit 0; else echo BENCH_BAD; exit 1; fi
