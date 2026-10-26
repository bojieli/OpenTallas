#!/bin/bash
# run_ownership_obs.sh OUT (KVJ-F 2026-10-17, stub audit K-4): the ownership calendar with its actual producers
# (qkd_kv_ownership_obs) as kv_static_kvjf_join.py binds them; rtl/test/qwen_static_kv/tb_kv_ownership_obs.sv.
#   must PASS: SCN 0 (two tokens, clean windows, then a drain-guard fault stop), SCN 1 (late es command before the
#              compiled leave -> ownership fault code 4), SCN 2 (HOST busy at the compiled enter -> code 3)
#   must FAIL: MUT 1 (go on every stage_start), 2 (es lanes not observed), 3 (drained ignores guard faults),
#              4 (HOST quiet not synchronised)
set -u
O=$1; mkdir -p "$O"
S=rtl/qwen_sys/static_kv_20261014
rc=0
run(){ # tag scn mut expect
  iverilog -g2012 -o "$O/$1" -P tb_kv_ownership_obs.SCN=$2 -P tb_kv_ownership_obs.MUT=$3 \
    $S/qkd_kv_ownership_obs.sv $S/qkd_static_kv_ownership.sv rtl/test/qwen_static_kv/tb_kv_ownership_obs.sv > "$O/$1.build.log" 2>&1 \
    || { echo "BUILD FAIL $1"; rc=1; return; }
  l=$(vvp -n "$O/$1" 2>&1 | tee "$O/$1.log" | grep -E '^(PASS|FAIL) kv_ownership_obs' | tail -1)
  echo "$1 (must $4): ${l:-no result line}"
  case "$l" in $4*) ;; *) rc=1;; esac
}
run scn0 0 0 PASS; run scn1 1 0 PASS; run scn2 2 0 PASS
for m in 1 2 3 4; do run mut$m 0 $m FAIL; done
[ $rc = 0 ] && echo "PASS ownership_obs: 3 scenarios exact, 4 mutants caught" || echo "FAIL ownership_obs"
exit $rc
