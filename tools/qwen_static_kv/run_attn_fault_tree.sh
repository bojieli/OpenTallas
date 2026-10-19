#!/bin/bash
# run_attn_fault_tree.sh OUT (RTL-BUILD-KV/FAULT 2026-10-18, lanes/RTL-BUILD-KV.md P7): the static KV die's attention
# service-unit fault tree (kv_static_die OT_KV_AFAULT) with the real node / root RTL, tb_qkd_attn_fault_tree.sv.
#   must PASS: MUT 0 (56 single faults, 1,540 pairs, 20k random cycles, 8 held sets: every cycle exact, fixed latency)
#   must FAIL: MUT 1 (node drops its K input), 2 (root pin register skipped), 3 (root drops a chain), 4 (lane map swapped),
#              5 (chain hop bypasses a group), 6 (a node with an extra register stage: latency +1)
# Fleet only (ot-run): iverilog -g2012.
set -u
O=$(readlink -f "$1"); mkdir -p "$O"
SRC="rtl/qwen_sys/static_kv_20261014/qkd_kv_cfault_tree.sv rtl/qwen_sys/static_kv_die_20261017/qkd_attn_fault_root.sv rtl/test/qwen_static_kv/tb_qkd_attn_fault_tree.sv"
rc=0
for m in 0 1 2 3 4 5 6; do
  want=FAIL; [ $m = 0 ] && want=PASS
  if ! iverilog -g2012 -s tb_qkd_attn_fault_tree -P tb_qkd_attn_fault_tree.MUT=$m -o "$O/m$m.sim" $SRC > "$O/mut$m.build.log" 2>&1; then
    echo "BUILD FAIL mut$m"; rc=1; continue; fi
  vvp -n "$O/m$m.sim" > "$O/mut$m.log" 2>&1
  l=$(grep -E '^(PASS|FAIL) attn_fault_tree' "$O/mut$m.log" | tail -1)
  echo "mut$m (must $want): ${l:-no result line}"
  case "$l" in $want*) ;; *) rc=1;; esac
  rm -f "$O/m$m.sim"
done
[ $rc = 0 ] && echo "PASS run_attn_fault_tree: MUT 0 exact, 6 mutants caught" || echo "FAIL run_attn_fault_tree"
exit $rc
