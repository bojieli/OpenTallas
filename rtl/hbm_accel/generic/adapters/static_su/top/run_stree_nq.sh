#!/usr/bin/env bash
# HBM-BIND B2 (2026-10-24): SU scalar tree NLEG gate. For NLEG 4 (default, vs the unchanged base net) and NLEG 2 (B2 root2
# master, vs model + the base 4-leg net restricted to legs 2/3): MUT 0 must PASS, MUT 1..4 must FAIL; plus the existing
# run_stree_lockstep.sh (d4f relay reference) at default must PASS. iverilog.
#   run_stree_nq.sh OUT [BASE_REF=origin/claude/hbm-bind-1024r]
set -uo pipefail
out=$(realpath -m "${1:?out}"); base=${2:-origin/claude/hbm-bind-1024r}; mkdir -p "$out"
d=$(cd "$(dirname "$0")" && pwd); fail=0
rel=rtl/hbm_accel/generic/adapters/static_su/top/ot_hbm_su_stree.sv
if [ -n "${STREE_REF_SV:-}" ]; then cp "$STREE_REF_SV" "$out/ref_raw.sv"; else git -C "$d" show "$base:$rel" > "$out/ref_raw.sv" || { echo "no base $base"; exit 2; }; fi
sed -E 's/\bot_hbm_su_stree_(rsync|leaf|root|leg|net)\b/ot_hbm_su_stree_\1_ref/g' "$out/ref_raw.sv" > "$out/ref.sv"
for nl in 4 2; do
 for m in 0 1 2 3 4; do
  iverilog -g2012 -Ptb_hbm_su_stree_nq.NLEG=$nl -Ptb_hbm_su_stree_nq.MUT=$m -Ptb_hbm_su_stree_nq.NCYC=6000 -o "$out/s_${nl}_$m" \
   -s tb_hbm_su_stree_nq "$d/tb_hbm_su_stree_nq.sv" "$d/ot_hbm_su_stree.sv" "$out/ref.sv" > "$out/build_${nl}_$m.log" 2>&1 \
   || { echo "BUILD_FAIL NLEG=$nl MUT=$m"; cat "$out/build_${nl}_$m.log"; exit 2; }
  vvp -n "$out/s_${nl}_$m" > "$out/run_${nl}_$m.log"; r=$(grep -E '^STREE_NQ' "$out/run_${nl}_$m.log"); echo "NLEG=$nl MUT=$m $r"
  if [ $m = 0 ]; then echo "$r" | grep -q ' PASS ' || fail=1; else echo "$r" | grep -Eq ' FAIL checks=[0-9]+ errors=[1-9]' || fail=1; fi
 done
done
for m in 0 1 2 3 4; do
 bash "$d/run_stree_lockstep.sh" "$out/lockstep_$m" $m 4000 > "$out/lockstep_$m.log" 2>&1
 r=$(grep -E '^STREE (PASS|FAIL)' "$out/lockstep_$m/stree.log"); echo "existing run_stree_lockstep MUT=$m: $r"
 if [ $m = 0 ]; then echo "$r" | grep -q '^STREE PASS' || fail=1; else echo "$r" | grep -q '^STREE FAIL' || fail=1; fi
done
[ $fail = 0 ] && echo "STREE_NQ_GATE PASS" || { echo "STREE_NQ_GATE FAIL"; exit 1; }
