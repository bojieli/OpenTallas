set -uo pipefail
vvp() { cat "$fixture"; return "$simrc"; }
run_case() {
  local binary=$1 expected=$2 log="$1.log" result
  if ! vvp -n "$binary" > "$log" 2>&1; then
    cat "$log"
    return 1
  fi
  cat "$log"
  result=$(grep -E '^TB_HBM_SM_VM_WR_Q_T (PASS MUT=[0-4]|FAIL MUT=[0-4] mismatches[+]faults=[0-9]+)$' "$log")
  [[ $(printf '%s\n' "$result" | wc -l) = 1 ]] || return 1
  [[ "$result" == "TB_HBM_SM_VM_WR_Q_T $expected MUT="* ]]
}
fixture=$(mktemp); tmpcase=$(mktemp)
simrc=0
printf '%s\n' 'TB_HBM_SM_VM_WR_Q_T PASS MUT=0' 'file.sv:237: $finish called at 1' > "$fixture"
run_case "$tmpcase" PASS >/dev/null || exit 1
run_case "$tmpcase" FAIL >/dev/null && exit 2
printf '%s\n' 'TB_HBM_SM_VM_WR_Q_T FAIL MUT=0 mismatches+faults=1184' 'file.sv:237: $finish called at 1' > "$fixture"
run_case "$tmpcase" FAIL >/dev/null || exit 3
run_case "$tmpcase" PASS >/dev/null && exit 4
printf '%s\n' 'TB_HBM_SM_VM_WR_Q_T PASS MUT=0' 'TB_HBM_SM_VM_WR_Q_T PASS MUT=0' > "$fixture"
run_case "$tmpcase" PASS >/dev/null && exit 5
printf '%s\n' 'file.sv:237: $finish called at 1' > "$fixture"
run_case "$tmpcase" PASS >/dev/null && exit 6
printf '%s\n' 'TB_HBM_SM_VM_WR_Q_T PASS MUT=0' > "$fixture"
simrc=1
run_case "$tmpcase" PASS >/dev/null && exit 7
rm "$fixture" "$tmpcase" "$tmpcase.log"
echo 'Strict verdict parser: trailing footer accepted; wrong, missing, duplicate and failed-process verdicts rejected'
