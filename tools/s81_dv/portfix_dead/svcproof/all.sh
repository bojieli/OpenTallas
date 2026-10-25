#!/bin/bash
cd /srv/opentallas-scratch2/claude/s81-portfix/dead/svcproof
while read _ m; do fm=${m##*_}; e=0; case $m in *pvso_entry*) e=1;; esac
  ./run.sh fm_$fm $fm $e > run_fm_$fm.out 2>&1 &
done < variants.txt
wait
grep -H "VERDICT\|NO_READER(!)" *.check.txt
