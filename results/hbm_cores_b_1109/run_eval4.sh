#!/bin/bash
for h in epyc2 epyc4 epyc5 epyc6; do
( timeout 3400 ssh -n -o ControlPath=none $h "cd / && nice -n15 ionice -c3 python3 -I ~/disk-urgent-3/eval_dirs4.py ~/disk-urgent-3/ot-autoclean-c48.py ~/disk-urgent-3/all.cands ~/disk-urgent-3/all.eval.tsv --host $h 2>&1 | tail -2 | cut -c1-200; wc -l ~/disk-urgent-3/all.eval.tsv" ) &
done
wait
echo EVAL4-ALLDONE
