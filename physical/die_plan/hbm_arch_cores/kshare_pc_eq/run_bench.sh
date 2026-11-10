#!/bin/bash
# lockstep bench sweep: MODE 0 (PASS expected), MODE 1/2 negative controls (FAIL expected)
cd $(dirname $0)
for v in v8e478a v700685; do for s in 1 7 42 1009; do for m in 0 1 2; do
  echo "$(timeout 3600 vvp -n bench/$v/tb.vvp +MODE=$m +N=40000 +SEED=$s | grep '^BENCH') seedarg $s"
done; done; done > bench/results.txt 2>&1
echo DONE >> bench/results.txt
