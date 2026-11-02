#!/bin/bash
set -euo pipefail
cd native
for mutant in MUT_NO_RELOC MUT_PAYLOAD MUT_BEAT; do
 if ./obj/Vtb +"$mutant" > "$mutant.control.log" 2>&1; then
  echo "UNCAUGHT_MUTANT $mutant";exit 1
 fi
 if ! /usr/bin/grep -q ROPE_NATIVE_MISMATCH "$mutant.control.log"; then
  echo "UNEXPECTED_MUTANT_FAILURE $mutant";exit 1
 fi
done
printf '%s\n' PASS_LITERAL_AND_NATIVE_ROPE > ../controls.status
