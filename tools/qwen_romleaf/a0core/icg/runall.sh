#!/bin/bash
# launch all ICG bench cases for one tile as capped user units
T=$1; shift; R=/srv/opentallas-scratch2/claude/die-qc16-icg; W=/srv/opentallas-scratch2/claude/wt/die-qc16-icg
for m in "$@"; do
  systemd-run --user --unit=qc16icg-run-$T-m$m -p MemoryMax=16G --working-directory=$W \
    bash -c "tools/qwen_romleaf/a0core/icg/run.sh $R/b_$T mut$m +ICG_MUT=$m > $R/b_$T/sum_mut$m.txt 2>&1"
done
