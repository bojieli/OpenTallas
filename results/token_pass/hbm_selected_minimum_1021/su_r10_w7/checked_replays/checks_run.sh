#!/bin/bash
set -euo pipefail
sha256sum --check binary.sha256
mkdir -p out
for part in checks_0 checks_1 half0 half1;do
 ./Vtb_hbm_slice +verilator+rand+reset+2 +REPLAY="replay/$part" +CYCLES=10000 > "out/$part.log" 2>&1
 grep -q 'SLICE_PASS' "out/$part.log"
 if grep -q 'SLICE_CHECK_FAIL' "out/$part.log";then exit 3;fi
 grep -E 'SLICE_(SUMMARY|PASS|FAIL)' "out/$part.log"
done
set +e
./Vtb_hbm_slice +verilator+rand+reset+2 +REPLAY=replay/checks_mutant +CYCLES=10000 > out/mutant.log 2>&1
mutant_rc=$?
set -e
echo MUTANT_PROCESS_EXIT=$mutant_rc >> out/mutant.log
grep -q 'SLICE_CHECK_FAIL' out/mutant.log
grep -q '^SLICE_FAIL' out/mutant.log
if grep -q '^SLICE_PASS' out/mutant.log;then echo SOURCE_MUTANT_UNEXPECTED_PASS;exit 4;fi
echo SELECTED_SU_CHECKED_REPLAY_GATE_PASS
