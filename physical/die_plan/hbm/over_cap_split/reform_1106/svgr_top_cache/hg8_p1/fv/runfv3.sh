#!/bin/bash
cd /fv
for s in match match0 match_mut; do yosys -p "script /fv/$s.ys" > /fv/$s.log 2>&1; echo "$s rc $? $(grep -E "Induction step proven|SUCCESS|FAIL|failed|Temporal induction" /fv/$s.log | tail -2 | tr "\n" " ")"; done
