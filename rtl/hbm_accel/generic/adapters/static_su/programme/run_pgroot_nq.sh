#!/usr/bin/env bash
# HBM-BIND B2 (2026-10-24): ot_hbm_su_programme_root_h5 PARTS gate (iverilog). PARTS 4 (default, vs the unchanged base h5)
# and PARTS 2 (B2 su_prog) MUT 0 must PASS; MUT 1..4 must FAIL at both.
#   run_pgroot_nq.sh OUT [BASE=origin/claude/hbm-bind-1024r]   (PGROOT_REF_SV=<base file> instead of git show)
set -uo pipefail
out=$(realpath -m "${1:?out}"); base=${2:-origin/claude/hbm-bind-1024r}; mkdir -p "$out"
d=$(cd "$(dirname "$0")" && pwd); r=$(cd "$d/../../../../../.." && pwd); fail=0
rel=rtl/hbm_accel/generic/adapters/static_su/programme/ot_hbm_su_programme_root_h5.sv
if [ -n "${PGROOT_REF_SV:-}" ]; then cp "$PGROOT_REF_SV" "$out/ref_raw.sv"; else git -C "$d" show "$base:$rel" > "$out/ref_raw.sv" || { echo "no base"; exit 2; }; fi
sed -E 's/\bot_hbm_su_programme_(root5|root_h5)\b/ot_hbm_su_programme_\1_ref/g' "$out/ref_raw.sv" > "$out/ref.sv"
for p in 4 2; do
 for m in 0 1 2 3 4; do
  iverilog -g2012 -Ptb_hbm_su_programme_root_h5_nq.P=$p -Ptb_hbm_su_programme_root_h5_nq.MUT=$m -o "$out/s_${p}_$m" \
   -s tb_hbm_su_programme_root_h5_nq "$d/tb_hbm_su_programme_root_h5_nq.sv" "$d/ot_hbm_su_programme_root_h5.sv" "$out/ref.sv" \
   "$r/rtl/lib/ot_rst_relay.sv" > "$out/build_${p}_$m.log" 2>&1 || { echo "BUILD_FAIL P=$p MUT=$m"; cat "$out/build_${p}_$m.log"; exit 2; }
  vvp -n "$out/s_${p}_$m" > "$out/run_${p}_$m.log"; v=$(grep -E '^SU_PGROOT_NQ' "$out/run_${p}_$m.log"); echo "PARTS=$p MUT=$m $v"
  if [ $m = 0 ]; then echo "$v" | grep -q ' PASS ' || fail=1; else echo "$v" | grep -Eq ' FAIL checks=[0-9]+ errors=[1-9]' || fail=1; fi
 done
done
[ $fail = 0 ] && echo "SU_PGROOT_NQ_GATE PASS" || { echo "SU_PGROOT_NQ_GATE FAIL"; exit 1; }
