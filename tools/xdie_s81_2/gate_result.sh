# Shared strict job aggregation. Source after O and X have been set.
pids=()
r() { n=$1; b=$2; g=$3; shift 3
  expected=${EXPECTED_REJECT:-}
  (
    $X run "$O" "$b" "$n" "$GD/$g" "$@" > "$O/$n.txt" 2>&1; run_rc=$?
    echo "EXIT $run_rc" >> "$O/$n.txt"
    python3 tools/xdie_s81_2/mu_check.py "$GD/$g" "$O/$n/run.log" --win "${CHECK_WIN:-2}" --json "$O/$n.chk.json" > "$O/$n.chk.txt" 2>&1; check_rc=$?
    echo "EXIT $check_rc" >> "$O/$n.chk.txt"
    if [ -f "$O/$n/run.log" ]; then gzip -kf "$O/$n/run.log"; fi
    if [ -n "$expected" ]; then
      { [ "$run_rc" != 0 ] || [ "$check_rc" != 0 ]; } && grep -Eq "$expected" "$O/$n.txt" "$O/$n.chk.txt"
    else
      [ "$run_rc" = 0 ] && [ "$check_rc" = 0 ]
    fi
  ) & pids+=("$!")
}
finish_jobs() {
  label=$1; ok=1
  for pid in "${pids[@]}"; do wait "$pid" || ok=0; done
  if [ "$ok" = 1 ]; then touch "$O/DONE_$label"; return 0; fi
  touch "$O/DONE_${label}_FAILED"; return 1
}

r_reject() { EXPECTED_REJECT=$1; shift; r "$@"; unset EXPECTED_REJECT; }
