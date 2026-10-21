#!/bin/bash
# QW-C3-COLLIO bench8: tb_coll_static_face with R/PEER_R relay pipes (face 1 = mirrored partner); P/R/S0/S2 PLAND D2K1 gold +
# 7 mutants, S1 D2K1 gold regression; Verilator 5.050 on fleet
D=/srv/opentallas-scratch/claude/qw-collio-1020/src8
L=/home/ubuntu/scratch/qw-c3-collio
V=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
run(){ tag=$1; shift; /home/ubuntu/bin/ot-run --mem 32 --threads 8 --dir $D -- bash -c "cd $D && VERILATOR=$V $* " > $L/bench8_$tag.log 2>&1; }
declare -A E=([p]="FACE_FW=546 FACE_PHY=20 FACE_R=5 FACE_PR=5 FACE_L=56" [r]="FACE_FW=514 FACE_PHY=20 FACE_R=5 FACE_PR=5 FACE_L=56" [s0]="FACE_FW=546 FACE_PHY=350 FACE_R=0 FACE_PR=5 FACE_L=381" [s2]="FACE_FW=546 FACE_PHY=349 FACE_R=5 FACE_PR=0 FACE_L=381" [s1]="FACE_L=381")
for f in s1 p r s0 s2; do run ${f}_m0 "PLAND=1 PLD=2 PLK=1 PPH=0 ${E[$f]} SAFE=1 SIM=verilator HARD=1 bash rtl/test/run_coll_static_face.sh /tmp/qwc3_b8/${f}_m0 0" & done
for f in p r s0 s2; do for m in 1 2 3 4 5 6 7; do
  run ${f}_m$m "PLAND=1 PLD=2 PLK=1 PPH=0 ${E[$f]} SAFE=1 SIM=verilator HARD=1 bash rtl/test/run_coll_static_face.sh /tmp/qwc3_b8/${f}_m$m $m" &
done; done
wait
echo ALLDONE > $L/bench8.done
