#!/bin/bash
for h in epyc2 epyc4 epyc5 epyc6; do
( timeout 3000 ssh -n -o ControlPath=none $h "cd / && nice -n15 ionice -c3 python3 -I ~/disk-urgent-3/eval_dirs3.py ~/disk-urgent-3/ot-autoclean-c48.py ~/disk-urgent-3/s3.cands ~/disk-urgent-3/s3.eval.tsv --host $h 2>&1 | tail -3 | cut -c1-200; awk -F'\t' '{print \$2}' ~/disk-urgent-3/s3.eval.tsv | sort | uniq -c | tr '\n' ' '; echo $h" ) &
done
wait
