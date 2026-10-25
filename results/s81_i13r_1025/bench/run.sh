#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")"
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
F="--binary --timing --x-initial unique --x-assign unique -j 4 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style --top-module tb"
SRC="dsdv_idx_tx_i13.sv dsdv_idx_l20s.sv dsdv_idx_tree.sv ot_rst_relay.sv"
CASES="dense cam miss duplicate wrongtag skip twosrc wrongq order idorder"
rc=0
"$VL" $F -Mdir obj_r3 $SRC tb_r3.sv > build_r3.log 2>&1 || { tail -30 build_r3.log; exit 2; }
for c in $CASES; do obj_r3/Vtb +CASE=$c +verilator+rand+reset+2 > $c.r3.log; done
python3 check.py r3 > /dev/null || rc=1
"$VL" $F -Mdir obj_s ot_sram_1r1w_1024x256_m2_r2c2.v ot_sram_1r1w_256x256_m2_r2c2.v ot_sram_1r1w_128x256_m1_r2c2.v $SRC tb_sram.sv > build_s.log 2>&1 || { tail -30 build_s.log; exit 2; }
for c in $CASES; do obj_s/Vtb +CASE=$c +verilator+rand+reset+2 > $c.s.log; done
python3 check.py s > /dev/null || rc=1
# mutant 3 (write-time order/duplicate check removed): expect duplicate+order negatives to ESCAPE (mutant caught)
"$VL" $F +define+MUT=3 -Mdir obj_m3 $SRC tb_r3.sv > build_m3.log 2>&1 || { tail -30 build_m3.log; exit 2; }
for c in $CASES; do obj_m3/Vtb +CASE=$c +verilator+rand+reset+2 > $c.m3.log; done
python3 check.py m3 > /dev/null; echo "m3 check exit $? (nonzero = mutant caught)"
cd m && cp ../dsdv_idx_tx_i13.sv ../dsdv_idx_l20s.sv ../dsdv_idx_tree.sv ../ot_rst_relay.sv . && \
"$VL" $F -Mdir obj $SRC tb2.sv > build.log 2>&1 || { tail -30 build.log; exit 2; }
for c in multi samebank; do obj/Vtb +CASE=$c +verilator+rand+reset+2 > $c.log; done
python3 check2.py > /dev/null || rc=1
cd ..
python3 - <<'PY'
import json
for f in ['summary_r3.json','summary_s.json','summary_m3.json','m/summary.json']:
  d=json.load(open(f));print(f,d['verdict'],d['bad'])
  for c,v in d['cases'].items():print('  ',c,{k:v.get(k) for k in ('beats','mismatches','status','fault','issue_to_done','output_span','first_lookup','command_edge','dones')})
PY
exit $rc
