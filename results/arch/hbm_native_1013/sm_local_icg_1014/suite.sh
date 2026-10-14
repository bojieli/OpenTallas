#!/bin/bash
set -euo pipefail
bash eg_run.sh split
bash wg_run.sh split
for c in tt ff ss; do bash phase_run.sh split "$c"; done
set +e
bash eg_run.sh mut
mrc=$?
bash phase_run.sh mut ss
prc=$?
set -e
if [[ $mrc -eq 0 || $prc -eq 0 ]]; then echo MUTANT_UNDETECTED; exit 1; fi
printf 'LOCAL_ICG_SUITE_PASS exact_mutant_rc=%s phase_mutant_rc=%s\n' "$mrc" "$prc"
