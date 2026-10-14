#!/bin/bash
# The native B2 MTP swap gate, all benches and mutants in parallel: b2_swap_suite.sh OUT_DIR
#   grp  (tb_hgi_b2_swap_grp : resolved beats -> S -> 4 back engines)        MUT 0 PASS, 1 2 3 5 FAIL, 4 THROUGHPUT FAIL
#   rec  (tb_hgi_b2_swap_rec : program records -> ot_hgi_seq -> adapter -> S) MUT 0 PASS, 1 2 3 5 6 7 8 9 FAIL, 4 THROUGHPUT FAIL
#        (3 = S's join, 6 = S's fault report: the adapter repeats neither rule, so both must fail HERE)
#   in   (tb_hgi_b2_swapin_grp: beats -> S -> 4 front engines)                MUT 0 PASS, 1 2 3 FAIL, 4 THROUGHPUT FAIL
set -u
O=$1; D=$(cd "$(dirname "$0")" && pwd); mkdir -p "$O"
for m in 0 1 2 3 4 5;         do ( "$D/run_b2_swap_grp.sh"   "$O/grp$m" $m > "$O/grp$m.out" 2>&1; echo "rc=$?" >> "$O/grp$m.out" ) & done
for m in 0 1 2 3 4 5 6 7 8 9; do ( "$D/run_b2_swap_rec.sh"   "$O/rec$m" $m > "$O/rec$m.out" 2>&1; echo "rc=$?" >> "$O/rec$m.out" ) & done
for m in 0 1 2 3 4;           do ( "$D/run_b2_swapin_grp.sh" "$O/in$m"  $m > "$O/in$m.out"  2>&1; echo "rc=$?" >> "$O/in$m.out" ) & done
wait
for f in "$O"/*.out; do echo "== $(basename "$f" .out): $(grep -E 'PASS|FAIL|rc=' "$f" | tail -3 | cut -c1-260 | tr '\n' '|')"; done
