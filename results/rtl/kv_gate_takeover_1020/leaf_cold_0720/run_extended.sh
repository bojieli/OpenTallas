#!/bin/bash
set -euo pipefail
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
verilator --version > version.txt
mkdir -p positive
verilator --binary --timing --public-flat-rw --x-initial unique --x-assign unique -Wno-fatal -Wno-BLKANDNBLK --top-module tb --Mdir positive/build -j 8 tb_extended.sv core.sv top.sv > positive/build.log 2>&1
for seed in 17 1020;do
 positive/build/Vtb +SEED=$seed +verilator+rand+reset+2 +verilator+seed+$seed > positive/seed_$seed.log 2>&1
 grep -q LEAF_COLD_PASS positive/seed_$seed.log
 echo "positive_extended seed=$seed PASS" | tee -a status.txt
done
