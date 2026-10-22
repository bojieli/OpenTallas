# Shared strict job aggregation. Source after O and X have been set.
pids=()
r() { n=$1; b=$2; g=$3; shift 3
  expected=${EXPECTED_REJECT:-}
  (
    golden=$g; [ -d "$golden" ] || golden="$GD/$g"
    $X run "$O" "$b" "$n" "$golden" "$@" > "$O/$n.txt" 2>&1; run_rc=$?
    echo "EXIT $run_rc" >> "$O/$n.txt"
    python3 tools/xdie_s81_2/mu_check.py "$golden" "$O/$n/run.log" --win "${CHECK_WIN:-2}" --json "$O/$n.chk.json" > "$O/$n.chk.txt" 2>&1; check_rc=$?
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

prepare_mu_su() {
  python3 tools/xdie_s81_2/gen_golden.py --out "$O/su_mu" --gap 100 --dl-model fluid --fluid-guard "${SU_GUARD:-1}" --reserve-mu-tag
}
require_same_sources() {
  # Historical builds without an immutable synthesis/simulation source inventory cannot be causal controls.
  for build in "$1" "$2"; do
    [ -s "$O/$build/sources.sha256" ] || { echo "REFUSED_NO_SOURCE_MANIFEST $build"; return 1; }
  done
  cmp -s "$O/$1/sources.sha256" "$O/$2/sources.sha256" || { echo REFUSED_BASELINE_SOURCE_MISMATCH; return 1; }
  python3 - "$O/$1/build_cmd.txt" "$O/$2/build_cmd.txt" <<'CHECK_BUILD'
import sys
from pathlib import Path
mutants = {'+define+OT_S81SL_LEP_MUT_STALEHD', '+define+OT_S81_LAND_MUT_SEL'}
a, b = [[word for word in Path(p).read_text().split() if word not in mutants] for p in sys.argv[1:]]
if a != b:
    raise SystemExit('REFUSED_BASELINE_BUILD_ARGS_MISMATCH')
CHECK_BUILD

}
