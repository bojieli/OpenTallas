#!/bin/bash
cd /w
for v in gold_r new_r mut_r gold_x new_x; do yosys -q -l /w/w_$v.log /w/w_$v.ys >/dev/null 2>&1; echo "write $v rc=$?"; done
python3 -I /w/strip.py gold_r.json new_r.json mut_r.json gold_x.json new_x.json
for e in gold_r__new_r gold_r__mut_r gold_x__new_x; do yosys -l /w/eq_$e.log /w/eq_$e.ys >/dev/null 2>&1; echo "eq $e rc=$?"; grep "are proven and" /w/eq_$e.log | tail -n 1; done
chmod -R a+rw /w
