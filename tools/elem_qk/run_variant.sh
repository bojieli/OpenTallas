#!/bin/bash
# ELEM-QK: run one ASTK/ECTLK variant kit (cwd = kit dir) then main's signoff.py at TT/FF into signoff/
K=$(pwd); T=$(cd "$(dirname "$0")" && pwd)/_tools
bash $K/run_kit_kv.sh $K ${GOAL:-finish} ${MEM:-32} ${CPUS:-8}; echo "kit_rc=$?" > $K/elemqk_rc
python3 $T/tools/die_plan/signoff.py run --run-dir $K/run --kit $K --corners tt,ff --out $K/signoff > $K/signoff.log 2>&1
echo "signoff_rc=$?" >> $K/elemqk_rc; grep -h '^SIGNOFF' $K/signoff.log
