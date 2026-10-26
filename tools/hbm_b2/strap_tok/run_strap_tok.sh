#!/bin/bash
# TOK-HBM 10-25 strap token test (TYPE-REDUCE-3 obligation, COORD 20:37 ruling (1)): every strap_* tie value the HBM
# die plan makes, strap master vs the old constant variant it replaces, Verilator lockstep + strap mutant.
#   tools/hbm_b2/strap_tok/run_strap_tok.sh OUT [PAR]       (heavy: run under ot-run, ~3 GB per parallel bench)
# Rule 3: refuses a dirty tracked tree, records source_commit; all inputs are repo-relative at that commit (plan,
# variants, strap wrappers, kit generator); old kits are regenerated from the repo in OUT/old.
set -u
R=$(git -C "$(dirname "$0")" rev-parse --show-toplevel) || exit 2
OUT=$1; PAR=${2:-6}
git -C "$R" diff --quiet HEAD -- || { echo "REFUSE: dirty tracked tree in $R"; exit 3; }
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd -P)
[ -e "$OUT/summary.json" ] && { echo "REFUSE: $OUT already holds a summary"; exit 3; }
git -C "$R" rev-parse HEAD > "$OUT/source_commit.txt"
H=results/type_reduce3_1025/hbm
cd "$R" || exit 2
python3 -I tools/hbm_b2/strap_tok/plan_ties.py physical/die_plan/hbm_arch/B2n/die_plan.json $H/variants.json "$OUT/ties.json" | tee "$OUT/ties.log" || exit 4
grep -q '"verdict": "PASS"' "$OUT/ties.log" || exit 4
mkdir -p "$OUT/old" "$OUT/logs" "$OUT/bench"
python3 -c "import json;[print(b['old_view']) for b in json.load(open('$OUT/ties.json'))['benches']]" |
  (cd physical/die_plan/hbm_arch_cores && xargs -P "$PAR" -I{} sh -c 'v={}; python3 -E -s gen_core_kit_hbm.py --views views_b2n.json --view "$v" --out '"$OUT"'/old --hold-margin 0 --face-shell on --face-shell-drop off --core-insertion none --clock-taps density > '"$OUT"'/logs/genold_${v%@*}.log 2>&1; echo "genold $v rc=$?"') | tee "$OUT/genold.log"
grep -v 'rc=0$' "$OUT/genold.log" && { echo "FAIL: old kit generation"; exit 5; }
python3 -c "
import json
for b in json.load(open('$OUT/ties.json'))['benches']:
    m,v=b['old_view'].split('@'); print(b['master'], '$OUT/old/%s_%s' % (m, v), ','.join('%s=%s' % kv for kv in sorted(b['straps'].items())), '$OUT/bench/'+b['old_module'])
" > "$OUT/benches.txt"
while read -r M K S D; do python3 $H/gen_bench.py "$M" "$K" "$S" "$D" --cycles 3000 || echo "GENFAIL $D"; done < "$OUT/benches.txt" > "$OUT/genbench.log" 2>&1
grep GENFAIL "$OUT/genbench.log" && { echo "FAIL: bench generation"; exit 6; }
awk '{print $4}' "$OUT/benches.txt" | xargs -P "$PAR" -I{} sh -c 'bash '"$R/$H"'/run_bench.sh {} 8 > {}/run.log 2>&1; echo "bench {} rc=$?"' | tee "$OUT/benchrun.log"
python3 -I tools/hbm_b2/strap_tok/summarize.py "$R" "$OUT"; rc=$?
[ $rc = 0 ] && echo STRAP_TOK_PASS > "$OUT/done" || echo STRAP_TOK_FAIL > "$OUT/done"
exit $rc
