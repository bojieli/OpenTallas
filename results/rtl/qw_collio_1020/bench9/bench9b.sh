#!/bin/bash
# QW2-COLL bench9b: S1 D2K1 + D4K2 mutants m1-m7 on BWREG source (src9 = 9a0939353)
D=/srv/opentallas-scratch/claude/qw-collio-1020/src9
L=/home/ubuntu/scratch/qw2-coll
V=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
run(){ tag=$1; shift; /home/ubuntu/bin/ot-run --mem 32 --threads 8 --dir $D -- bash -c "cd $D && VERILATOR=$V $* " > $L/bench9_$tag.log 2>&1; }
for m in 1 2 3 4 5 6 7; do
  run s1_m$m "PLAND=1 PLD=2 PLK=1 PPH=0 FACE_L=381 SAFE=1 SIM=verilator HARD=1 bash rtl/test/run_coll_static_face.sh /tmp/qw2_b9/s1_m$m $m" &
  run s1k2_m$m "PLAND=1 PLD=4 PLK=2 PPH=0 FACE_L=383 SAFE=1 SIM=verilator HARD=1 bash rtl/test/run_coll_static_face.sh /tmp/qw2_b9/s1k2_m$m $m" &
done
wait
echo ALLDONE > $L/bench9b.done
