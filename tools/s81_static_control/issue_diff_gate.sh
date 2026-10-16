#!/usr/bin/env bash
# c9 n4 issuer differential gate (S-ELEM-PQ 2026-10-15): frozen issuer (frozen copy at bf7c0023f) vs the working
# ot_s81_fixed_issue on randomized legal + perturbed program/job/completion/availability stimulus, every output each
# edge.  PASS = 0 mismatches on every seed; the MUT=1 issuer (issue edge +1) must mismatch.
# Usage: issue_diff_gate.sh OUT [SEEDS]   (frozen reference: rtl/dsrom_sys/s81_static_control/test/ot_s81_fixed_issue_ref_n3.sv)
set -euo pipefail
R=$(cd "$(dirname "$0")/../.." && pwd); O=${1:?out}; N=${2:-8}
defs=();run_extra=()
if [ "${OT_ISSUER_SCANPIPE:-0}" = 1 ];then defs=(-DOT_S81_ISSUE_SCANPIPE);run_extra=(+scanpipe);fi
mkdir -p "$O"; S=$R/rtl/dsrom_sys/s81_static_control
cp "$S/test/ot_s81_fixed_issue_ref_n3.sv" "$O/ref.sv"
iverilog "${defs[@]}" -g2012 -s tb_s81_fixed_issue_diff -o "$O/sim" "$O/ref.sv" "$S/ot_s81_fixed_issue.sv" "$S/test/tb_s81_fixed_issue_diff.sv"
sed 's/ot_s81_fixed_issue #(.STAGE(5))dut/ot_s81_fixed_issue #(.STAGE(5),.MUT(1))dut/' "$S/test/tb_s81_fixed_issue_diff.sv" > "$O/tb_mut.sv"
iverilog "${defs[@]}" -g2012 -s tb_s81_fixed_issue_diff -o "$O/sim_mut" "$O/ref.sv" "$S/ot_s81_fixed_issue.sv" "$O/tb_mut.sv"
for s in $(seq 1 "$N"); do
  p=$((s%2)); mkdir -p "$O/s$s"; python3 "$R/tools/s81_static_control/issue_diff_gen.py" "$R" "$s" "$p" "$O/s$s"
  (cd "$O/s$s" && vvp -n ../sim "${run_extra[@]}" +seed=$s > run.log 2>&1) &
done
mkdir -p "$O/mut"; python3 "$R/tools/s81_static_control/issue_diff_gen.py" "$R" 2 0 "$O/mut"
(cd "$O/mut" && vvp -n ../sim_mut "${run_extra[@]}" +seed=2 > run.log 2>&1) &
wait
grep -h '^DIFF seed' "$O"/s*/run.log
fails=$(grep -L '^DIFF PASS' "$O"/s*/run.log | wc -l)
grep -q '^DIFF FAIL' "$O/mut/run.log" || { echo "ISSUE_DIFF MUTANT_ESCAPED"; exit 1; }
echo "ISSUE_DIFF mutant MUT=1: $(grep -h '^DIFF seed' "$O/mut/run.log")"
[ "$fails" = 0 ] || { echo "ISSUE_DIFF FAIL $fails seeds"; exit 1; }
echo "ISSUE_DIFF GATE PASS seeds=$N mismatches=0 mutant=FAIL"
