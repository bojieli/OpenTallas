#!/bin/bash
# PATH-QC-NK diagnostic probe (read-only on the r5d ODB): FF hold classification with the original and the fixed signoff SDC.
set -uo pipefail
D=/srv/opentallas-scratch2/claude/path-qc-nk/diag; B=/srv/opentallas-scratch2/claude/path-qc-nk/r5; W=$B/run/r5/work/orfs
IMAGE=openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
ODB=$(ls $W/results/asap7/*/base/4_cts.odb | head -1); ODB=/work/${ODB#$W/}
for v in ${*:-orig fixed}; do
docker run --rm --name pathqcnk-diag-$v-$$ --cpus=4 --memory=40g --memory-swap=40g -v $B/src:/src:ro -v $W:/work:ro -v $D:/diag \
  -w /diag "$IMAGE" bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
  PLIBS=\"\$(cat /work/plibs.txt)\" ODB=$ODB SDC=/diag/signoff_r5.sdc OUT=/diag/r5_$v PLATFORM_DIR=/OpenROAD-flow-scripts/flow/platforms/asap7 \
  openroad -exit /diag/classify.tcl > /diag/r5_$v.log 2>&1; chmod a+rw /diag/r5_$v*" &
done
wait
grep -h "QDM\|OT_NK_DIAG\|Error" $D/r5_*.log
for v in ${*:-orig fixed}; do python3 $D/summ.py $D/r5_$v; done
