#!/bin/bash
set -eu
mkdir -p attn_fullopt_classify
cd attn_fullopt_classify
cp /srv/opentallas-scratch/claude/kv-attn3-1020/work_j0/gold1.il gold1.il
/home/ubuntu/.local/opentallas-tools/yosys-0.68/bin/yosys -l fullopt.log -p 'read_rtlil gold1.il; opt -full; wreduce; opt -full; write_json gold_fullopt.json' > fullopt.out 2>&1
