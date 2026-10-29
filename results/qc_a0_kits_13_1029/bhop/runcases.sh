#!/bin/bash
# wait for the two builds then run the bench cases (mut0 PASS; 7, 8 must FAIL; 1 sanity FAIL)
R=/srv/opentallas-scratch2/claude/qc-a0-kits-13-1029/bhop; W=/srv/opentallas-scratch2/claude/wt/qc-a0-kits-13
while systemctl --user is-active -q qca0k13-bhop-build-nl || systemctl --user is-active -q qca0k13-bhop-build-nk; do sleep 20; done
cd $W
for t in nl nk; do cat $R/build_$t.out; for m in 0 7 8 1 2 3 4 5 6 9; do
  echo "== $t mut$m"; timeout 600 systemd-run --user --wait --quiet --unit=qca0k13-bhop-run-$t-m$m -p MemoryMax=16G --working-directory=$W \
    bash -c "tools/qwen_romleaf/a0core/icg/run.sh $R/b_$t mut$m +ICG_MUT=$m > $R/b_$t/sum_mut$m.txt 2>&1"; cat $R/b_$t/sum_mut$m.txt | grep -v "Maximum\|Elapsed"
done; done
