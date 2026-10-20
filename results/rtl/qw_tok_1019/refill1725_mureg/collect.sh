#!/bin/bash
# REFILL-1725/QWLAYER collector: per cohort/leg: exit code, BAD lines (run_*.sh self-check), PASS/FAIL summary lines.
ssh -o ControlPath=none ot-epyc6 'cd /srv/opentallas-scratch/claude/refill-1725/QWLAYER; for c in ctlm4 sysface3 gen3c; do echo "=== $c $(cat $c/src/SOURCE_COMMIT)"; for f in $c/out/*.out; do l=$(basename $f .out); ex=$(grep -h "^# exit" $f | tail -1); nb=$(grep -c "^BAD " $f); echo "$l | ${ex:-RUNNING} | BAD=$nb | $(grep -h -E "BENCHES: (PASS|FAIL)|SYS_FACE_PASS MUT=0|overall rc|^BAD " $f | head -3 | cut -c1-200 | tr "\n" ";")"; done; done'
