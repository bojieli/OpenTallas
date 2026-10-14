#!/bin/bash
set -euo pipefail
cd overlay
python3 tools/rtl_qwen_me_partition_gate_w12.py --ref-file tools/qwen_blocks/ot_hdc_matvec_0e8df511.sv --jobs 4 --param GT=16 --param W=4 --param SMIN=3 --param SMAX=4 --param TCUT=3 --param BD=2 --param NWS=1 --param ORD=1 --param TWS=2 --param MEM_EXTRA=1 --param ACC_LAT=7 --param TREE_LAT=7 --param MUL_LAT=8 --param FAST_ISSUE=1 --param KV_PREP=4 --param ROM_PIPE=1 --param LRST=3 --param ARPB=1 --param MPR=1 --param HIER=2 --param ROM_CAP2=1 --param ROM_CAPX=2 --param ANR=1 --param ROM_ARELAY=2 --param SEED=1 --workdir ../bench --result ../result.json
