#!/bin/bash
# DIE-S81-80 bksel SPLIT lock-step proof: vI slice (gold) vs OT_BKQ_SPLIT slice + ot_s81ph_hq_pk2 (gate), + 2 mutants
P=$(cd "$(dirname "$0")" && pwd)
IMG=openroad/orfs:asap7lock
for m in none A B; do
  docker run --rm -m 64g --name ds80-bksplit-eq-$m-$$ -v $P/rtl_gold:/r:ro -v $P/rtl_new:/n:ro -v $P/out:/o -v $P:/p:ro $IMG yosys -q -l /o/prep_$m.log -s /p/prep_$m.ys || { echo "PREP_FAIL $m"; continue; }
  python3 -I $P/ren.py $m $P/out
  docker run --rm -m 64g --name ds80-bksplit-eq2-$m-$$ -v $P/out:/o $IMG yosys -l /o/eq_$m.log -s /o/eq_$m.ys >/dev/null 2>&1; echo "EQ_RC $m $?"
done
