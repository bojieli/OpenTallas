#!/bin/bash
cd /w
for v in gold_0 new_0 new_1 mutA_0 mutB_1; do yosys -q -l /w/w_$v.log /w/w_$v.ys >/dev/null 2>&1; echo "write $v rc=$?"; done
python3 -I /w/strip.py gold_0.json new_0.json new_1.json mutA_0.json mutB_1.json
python3 -I /w/strip.py new_0.json new_1.json mutA_0.json mutB_1.json
for g in new_0 new_1 mutA_0 mutB_1; do yosys -l /w/eq_$g.log /w/eq_$g.ys >/dev/null 2>&1; echo "eq $g rc=$?"; done
chmod -R a+rw /w
