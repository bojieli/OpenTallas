#!/bin/bash
# usage: tg.sh FP ; exact run of the tile-top gate, then all tile-class mutants in parallel (one binary)
FP=$1; R=$(cd $(dirname $0) && pwd); cd $R/src
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
O=$R/tg_$FP
python3 tools/s81_suhc/su_gate.py prep --cases /srv/opentallas-scratch/claude/s81-suhc/su_cases_v2_ildr.pkl --out $O --shape full > $R/$FP.prep.log 2>&1
( time python3 tools/s81_suhc/su_gate.py run --out $O --shape full --hier --tiles --fp $FP ) > $R/$FP.t0.log 2>&1
echo "EXACT_DONE rc=$?" >> $R/$FP.t0.log
if grep -q "^RUN .* pass" $R/$FP.t0.log; then
  for k in $(seq 1 21); do
    ( M=$R/tgm_${FP}_$k; mkdir -p $M; cp -al $O/runs $M/runs; cp $O/runs.json $M/; cp -a $O/tile_tops $M/; for b in $O/build_*; do ln -sfn $b $M/$(basename $b); done
      python3 tools/s81_suhc/su_gate.py run --out $M --shape full --hier --tiles --fp $FP --tmut $k > $R/$FP.t$k.log 2>&1; echo "rc=$?" >> $R/$FP.t$k.log ) &
  done; wait
fi
touch $R/$FP.ALLDONE
