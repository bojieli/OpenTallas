#!/bin/bash
# S81-ECO-1: after KIT's route run ends, routed LEC (kit RTL vs 6_final.v) with the R19 lec.py via ot-run
#   lec_after.sh KIT MEM
K=$1; MEM=${2:-16}; E=/srv/opentallas-scratch2/claude/s81-eco-1-1027
until grep -q "^ot-run: RAN\|NOT RUN" $K.otrun.log 2>/dev/null; do sleep 60; done
F=$(ls $K/run/results/asap7/*/base/6_final.v 2>/dev/null | head -1)
[ -n "$F" ] || { echo "no 6_final.v; route failed $(date)" > $K.lec_after.log; exit 1; }
~/.local/bin/ot-run --mem $MEM --threads 4 --dir $K -- python3 -I $E/tool/tools/die_plan/lec.py $K --netlist $F --out $K/lec_routed --jobs 4 --image openroad/orfs:asap7lock --mem $MEM > $K.lec_after.log 2>&1
echo "rc $? $(date)" >> $K.lec_after.log
