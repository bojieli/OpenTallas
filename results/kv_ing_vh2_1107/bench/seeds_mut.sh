#!/bin/bash
# usage: repo root cwd; writes ../bench_out/{seeds,full,mut}.txt
cd /srv/opentallas-scratch2/claude/kving8/wt
R=results/kv_ing_vh2_1107/bench/run_ing4.sh; O=../bench; L=../bench_out; mkdir -p $L
: > $L/seeds.txt
for pm in 0 1 2 3; do for s in $(seq 1 12); do
  r=$(REUSE=1 bash $R $O form +seed=$s +pm=$pm +nd=60 2>&1 | tail -2 | tr '\n' ' '); echo "pm$pm s$s $r" >> $L/seeds.txt
done; done
: > $L/full.txt
for pm in 1 2 0; do r=$(REUSE=1 bash $R $O form +seed=7 +pm=$pm +full=1 +nd=60 2>&1 | tail -2 | tr '\n' ' '); echo "full pm$pm $r" >> $L/full.txt; done
muts=$(grep -oE '^ m_[a-z0-9]+\)' $R | tr -d ' )')
: > $L/mut.txt
one(){ m=$1; R=$2; O=$3; L=$4
  for pm in 0 1 2 3; do for s in 1 2 3 4; do
    r=$(REUSE=1 timeout 300 bash $R $O $m +seed=$s +pm=$pm +nd=60 2>&1); rc=$?
    if echo "$r" | grep -q 'BUILD FAIL\|SUBST FAIL'; then echo "$m BUILDERR $(echo "$r"|head -2|tr '\n' ' '|cut -c1-160)" >> $L/mut.txt; return; fi
    if ! echo "$r" | tail -1 | grep -qx PASS; then echo "$m DETECTED pm$pm s$s rc=$rc: $(echo "$r" | grep -vE 'PROGRAM' | head -1 | cut -c1-110)" >> $L/mut.txt; rm -rf $O/o_$m $O/src_$m; return; fi
  done; done
  echo "$m SURVIVE" >> $L/mut.txt; rm -rf $O/o_$m $O/src_$m
}
export -f one
echo $muts | tr ' ' '\n' | nice xargs -P 6 -I{} bash -c "one {} $R $O $L"
echo DONE >> $L/mut.txt
