#!/bin/bash
# tools/die_plan tests, base (main 352bbd4c89a) vs tip (CLAND patch), same partial tree; compare failure sets
W=/srv/opentallas-scratch2/claude/qct10/cland; cd $W
rm -rf tb; mkdir tb; cd tb; for f in ../tools_352bbd.tgz ../t/cf.tgz ../t/rc.tgz; do tar xzf $f; done; cd $W
for v in t tb; do (cd $W/$v/tools/die_plan && timeout 3000 python3 -m pytest -q -p no:cacheprovider --continue-on-collection-errors -o addopts="" . > $W/pytest_$v.txt 2>&1; echo "rc $?" >> $W/pytest_$v.txt) & done; wait
for v in t tb; do grep -E "^(FAILED|ERROR) " $W/pytest_$v.txt | sed 's/ - .*//' | sort > $W/fail_$v.txt; tail -1 $W/pytest_$v.txt; done
echo TIP-ONLY; comm -23 $W/fail_t.txt $W/fail_tb.txt; echo BASE-ONLY; comm -13 $W/fail_t.txt $W/fail_tb.txt
