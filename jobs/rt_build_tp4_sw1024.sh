#!/bin/bash
# W12b: build-only of the TP-4 product die model at SU width 1,024 (LV 3), same parameters as the SW = 64 TP-4 run.
set -o pipefail
W=$HOME/w12bwork/rt1024_tp4; mkdir -p $W
echo "L0" > $W/dummy_stages.txt
mkdir -p $W/oracle_dummy
python3 tools/qwen_rom_rt_token.py --workdir $W --stages $W/dummy_stages.txt --token-oracle $W/oracle_dummy --preload /dev/null \
  --tp 4 --coll-lat 339 --su-width 1024 --lv 3 --smin 7 --smax 11 --tcut 7 --code-banks 5 --mem-extra 1 \
  --bd 41 --xvm 1 --nws 5 --tws 38 --ord 7 --vflags --unroll-count 4 -fno-dfg --hier-su --build-only --jobs 20 > $W/build.log 2>&1
echo "rc=$?" >> $W/build.log
