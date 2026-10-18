#!/bin/bash
# S-QA0: reproduce the qfd_tile_nk_tp8-c1 bench rc=1 (retry on a leftover workdir) and run the fixed gate.
cd "$(dirname "$0")/src" || exit 9
P="--ref-file tools/qwen_blocks/ot_hdc_matvec_0e8df511.sv --jobs 8 --param GT=24 --param W=4 --param SMIN=3 --param SMAX=4 --param TCUT=3 --param BD=2 --param NWS=1 --param ORD=1 --param TWS=2 --param MEM_EXTRA=1 --param ACC_LAT=7 --param TREE_LAT=7 --param MUL_LAT=8 --param FAST_ISSUE=1 --param KV_PREP=4 --param ROM_PIPE=1 --param LRST=3 --param ARPB=1 --param MPR=1 --param HIER=2 --param ROM_CAP2=1 --param ROM_CAPX=2 --param ANR=1 --param ROM_ARELAY=2 --param HIER_HARD=1 --param TOREG=1 --param TIDR=1 --param LRR=1"
R=../run; rm -rf $R; mkdir -p $R/bench/tp8_g24_exact_s1   # leftover workdir of a killed first attempt
echo "== original gate on a leftover workdir"
python3 tools/rtl_qwen_me_partition_gate_w12_orig.py $P --param SEED=1 --workdir $R/bench/tp8_g24_exact_s1 --result $R/bench/tp8_g24_exact_s1.json; echo "orig rc=$?"
echo "== fixed gate, same leftover workdir"
python3 tools/rtl_qwen_me_partition_gate_w12.py $P --param SEED=1 --workdir $R/bench/tp8_g24_exact_s1 --result $R/bench/tp8_g24_exact_s1.json; echo "fixed rc=$?"
python3 -c "import json;d=json.load(open('$R/bench/tp8_g24_exact_s1.json'));print(('PASS' if d['status']=='pass' else 'FAIL')+' rom_pipe '+d['verdict']+' | neg '+d['negative_control'])"; echo "verdict rc=$?"
echo "== mutant TMUT=3 (must be rejected)"
python3 tools/rtl_qwen_me_partition_gate_w12.py $P --param SEED=2 --param TMUT=3 --workdir $R/bench/tp8_g24_tmut3 --result $R/bench/tp8_g24_tmut3.json; python3 -c "import json;d=json.load(open('$R/bench/tp8_g24_tmut3.json'));print('MUTVERDICT '+d['verdict'])"
