#!/bin/bash
set -eu
for m in 0 1 2 3; do
  iverilog -g2012 -s tb -Ptb.MUT=$m -o sim$m d.sv tb.sv > compile$m.log 2>&1
  if [ "$m" = 0 ]; then vvp sim$m > nominal.log 2>&1
  else if vvp sim$m > mutant$m.log 2>&1; then exit 3; fi
  fi
done
echo PASS
