#!/bin/bash
# MU-ADOPT-KV 10-19: all KV-row adoption benches.  usage: run_all_kv.sh ROOT OUT
#  mu: MU 1 PASS benches + MU tile lint; mut: mutants (must FAIL); ex: MU 0 identity on the existing parent benches
#  (tools/qwen_kv_die/kvplan_ci_nc_gate.sh: qkd_static_kv_pc_path_nc at its default MU 0 in lockstep with the original
#  qkd_static_kv_pc_path under the compiled die images, + parent elaboration; tb_qkd_kv_mu_rowoff, the leaf bench).
set -u
R=$(cd "${1:?root}" && pwd); O=${2:?out}; mkdir -p "$O"; O=$(cd "$O" && pwd)
B=$(dirname "$(readlink -f "$0")")
for t in tb_mu_kv_writer_rows tb_mu_kv_pc_path_rows lint_mu_kv_tiles; do "$B/run_mu_kv.sh" "$R" "$O/mu" $t > "$O/s_$t.txt" 2>&1 & done
for m in mw1 mw2 mw3 mk1 mk2 mk3; do "$B/run_mu_kv.sh" "$R" "$O/mut" $m > "$O/s_$m.txt" 2>&1 & done
"$B/run_host_mu.sh" "$R" "$O/ex" tb_qkd_kv_mu_rowoff > "$O/s_ex_rowoff.txt" 2>&1 &
( cd "$R" && bash tools/qwen_kv_die/kvplan_ci_nc_gate.sh "$O/ex/ci_nc" > "$O/ex_ci_nc.log" 2>&1; echo "MU0 kvplan_ci_nc_gate rc=$?: $(tail -1 "$O/ex_ci_nc.log")" ) > "$O/s_ex_ci_nc.txt" 2>&1 &
wait
cat "$O"/s_*.txt | sort > "$O/summary.txt"; cat "$O/summary.txt"
