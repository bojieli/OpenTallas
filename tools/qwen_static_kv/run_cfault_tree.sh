#!/bin/bash
# run_cfault_tree.sh OUT (KVJ-SMALL (c) 2026-10-17): the registered neighbour OR tree of the 128 controller completion
# faults (rtl/qwen_sys/static_kv_20261014/qkd_kv_cfault_tree.sv) -> HOST ctrl_completion_fault.
#   must PASS: STAGES 1 (latency 4) and STAGES 2 (latency 8): 128 single-leaf faults + 64 pairs at exact latency,
#              reset and idle stay 0
#   must FAIL: MUT 1 (leaf 20 dropped), MUT 2 (root node unregistered -> early by one edge)
set -u
O=$1; mkdir -p "$O"
S=rtl/qwen_sys/static_kv_20261014
rc=0
run(){ # tag stages mut expect
  iverilog -g2012 -o "$O/$1" -P tb_kv_cfault_tree.STAGES=$2 -P tb_kv_cfault_tree.MUT=$3 \
    $S/qkd_kv_cfault_tree.sv rtl/test/qwen_static_kv/tb_kv_cfault_tree.sv > "$O/$1.build.log" 2>&1 \
    || { echo "BUILD FAIL $1"; rc=1; return; }
  l=$(vvp -n "$O/$1" 2>&1 | tee "$O/$1.log" | grep -E '^(PASS|FAIL) kv_cfault_tree' | tail -1)
  echo "$1 (must $4): ${l:-no result line}"
  case "$l" in $4*) ;; *) rc=1;; esac
}
run s1 1 0 PASS; run s2 2 0 PASS
run mut1 1 1 FAIL; run mut2 1 2 FAIL; run mut1s2 2 1 FAIL
[ $rc = 0 ] && echo "PASS cfault_tree: latency 4/8 exact on all 128 leaves, 3 mutants caught" || echo "FAIL cfault_tree"
exit $rc
