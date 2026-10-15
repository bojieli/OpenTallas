#!/bin/bash
# g4 (r2 bank-half collectors): tile probe exact (all variant tiles at their kit tuples), cncla / cnclb tile mutants,
# NT_K 66 negative, the loop bench (NG 256 exact + m3)
SRC=$1; OUT=$2; mkdir -p $OUT; cd $SRC
CASES=/srv/opentallas-scratch/claude/s81-suhc/su_cases_v2_ildr.pkl
python3 tools/s81_suhc/hc_gate.py prep --cases $CASES --out $OUT --ng 256 > $OUT/prep.log 2>&1 || { echo PREP FAIL; exit 1; }
A="--out $OUT --ng 256 --fp dpi --hier 3 --cnl-pin 1 --chain-step 6 --lane-specialize 1 --ntree 1"
python3 tools/s81_suhc/hc_gate.py run $A --nt-k 67 --tile-probe ot_s81_hc_ctfx_nt,ot_s81_hc_ctfs_nt,ot_s81_hc_cncla,ot_s81_hc_cnclb,ot_s81_hc_cnrsq > $OUT/probe.log 2>&1 &
python3 tools/s81_suhc/hc_gate.py run $A --nt-k 67 --tmax 30000 --tile-mut ot_s81_hc_cncla > $OUT/tm_cncla.log 2>&1 &
python3 tools/s81_suhc/hc_gate.py run $A --nt-k 67 --tmax 30000 --tile-mut ot_s81_hc_cnclb > $OUT/tm_cnclb.log 2>&1 &
python3 tools/s81_suhc/hc_gate.py run $A --nt-k 66 --tmax 30000 > $OUT/k66.log 2>&1 &
python3 tools/s81_suhc/hc_gate.py run $A --nt-k 67 --tmax 30000 --tile-mut ot_s81_hc_ctfs_nt > $OUT/tm_ctfs_nt.log 2>&1 &
python3 tools/s81_suhc/hc_gate.py run $A --nt-k 67 --tmax 30000 --tile-mut ot_s81_hc_ctfx_nt > $OUT/tm_ctfx_nt.log 2>&1 &
bash tools/s81_suhc/hc_ntree_bench.sh $OUT/bench_m0 0 > $OUT/bench_m0.log 2>&1 &
bash tools/s81_suhc/hc_ntree_bench.sh $OUT/bench_m3 3 > $OUT/bench_m3.log 2>&1 &
wait
grep -h "^RUN\|^TILE\|PASS\|FAIL" $OUT/probe.log $OUT/tm_cncla.log $OUT/tm_cnclb.log $OUT/k66.log $OUT/tm_ctfs_nt.log $OUT/tm_ctfx_nt.log $OUT/bench_m0.log $OUT/bench_m3.log
