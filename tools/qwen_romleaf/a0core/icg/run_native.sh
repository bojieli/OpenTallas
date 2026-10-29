#!/bin/bash
# Run an already built selected native source under fleet admission.
# The original conservative controls are reported honestly if they survive.
set -euo pipefail
proof=$(realpath "$1")
summary="$proof/controls.tsv"
test ! -e "$summary" || { echo 'fresh control result required' >&2; exit 2; }
printf 'mutant\tresult\n' > "$summary"
for mutant in 0 7 8 3; do
  log="$proof/run_mut${mutant}.log"
  "$proof/obj/Vtb_a0_icg" +OT_ROM_DIR="$proof/rom" +ICG_MUT="$mutant" > "$log" 2>&1
  if grep -q '^A0ICG_FAIL ' "$log"; then result=CAUGHT
  elif grep -q '^A0ICG_PASS ' "$log"; then result=PASS
  else echo "unqualified simulation mut$mutant" >&2; exit 1
  fi
  if [[ $mutant == 0 ]]; then
    [[ $result == PASS ]] || { cat "$log"; exit 1; }
  elif [[ $mutant == 7 ]]; then
    [[ $result == CAUGHT ]] || { echo 'unsafe main-clock hop control survived' >&2; exit 1; }
  elif [[ $result == PASS ]]; then result=SURVIVED
  fi
  printf '%s\t%s\n' "$mutant" "$result" | tee -a "$summary"
  grep -E '^A0ICG_(SHAPE|COUNTS|PASS|FAIL)' "$log"
done
