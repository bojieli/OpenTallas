#!/bin/bash
set -u
mkdir -p out
python3 tools/s81_slice/cap_model.py gen --case real --seed 1 --out out/v_real1 > out/gen.log 2>&1 || { echo GEN_FAILED; tail -5 out/gen.log; exit 4; }
(bash tools/s81_slice/cap_bench.sh out/base out/v_real1 0 > out/base_real1.out 2>&1; echo "rc=$?" >> out/base_real1.out) &
for m in 1 2 3 4; do
  (bash tools/s81_slice/cap_bench.sh out/m$m out/v_real1 $m raw > out/mut${m}_real1_raw.out 2>&1; echo "rc=$?" >> out/mut${m}_real1_raw.out) &
done
wait
tail -n 6 out/*.out
