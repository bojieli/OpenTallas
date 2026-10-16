#!/bin/bash
set -eu
for w in 340 277; do
  iverilog -g2012 -s tb -Ptb.WIDTH=$w -o sim$w golden.sv candidate.sv tb.sv
  vvp sim$w
  iverilog -g2012 -s tb -Ptb.WIDTH=$w -Ptb.MUT=1 -o mut$w golden.sv candidate.sv tb.sv
  if vvp mut$w > mut$w.log 2>&1; then echo "MUTANT SURVIVED $w";exit 1;fi
  grep 'VALID_PAYLOAD mismatch' mut$w.log
  echo "SKID_SPLIT_MUTANT rejected WIDTH=$w"
done
