#!/bin/bash
set -euo pipefail
cd "${1:?runtime}"
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
for profile in 171:0 173:0 171:1; do
 rt=${profile%:*};bad=${profile#*:};tag=reader_${rt}_${bad}
 verilator --binary --timing -j 2 -Wno-fatal -Wno-lint -Wno-style --top-module tb_idxqreader_n12 -GRT=$rt -GBAD_RT=$bad --Mdir obj_$tag -o tb *.sv *.v > build_$tag.log 2>&1
 if ./obj_$tag/tb > run_$tag.log 2>&1; then
  test "$bad" = 0 || { echo READER_MUTANT_SURVIVED;exit 1; }
  grep IDXQ_READER_PASS run_$tag.log
 else
  test "$bad" = 1 || { tail -8 run_$tag.log;exit 1; }
  grep IDXQ_READER_FAIL run_$tag.log
 fi
done
