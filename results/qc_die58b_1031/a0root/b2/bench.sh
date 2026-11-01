#!/bin/bash
# DIE-QC-58B: DIE-QC-16 ICG bench, ICG=1 + ICG_EREG=1 vs ICG=0, tile $1; mutants: 0 design, 12 no early terms (must FAIL), 2 ~me_idle, 3 drain
set -uo pipefail
cd /srv/opentallas-scratch2/claude/wt/die-qc-58b
T=$1; B=/srv/opentallas-scratch2/claude/die-qc-58b/bench/b_$T
ICG=1 EREG=1 bash tools/qwen_romleaf/a0core/icg/build.sh $T $B 16 || { echo BUILD_FAIL; exit 3; }
for m in 0 12 2 3 4; do bash tools/qwen_romleaf/a0core/icg/run.sh $B mut$m +ICG_MUT=$m > $B/sum_mut$m.txt 2>&1 & done; wait
grep -h "A0ICG_PASS\|A0ICG_FAIL\|A0ICG_COUNTS\|ACTIVITY\|Fatal\|Error" $B/sum_mut*.txt
