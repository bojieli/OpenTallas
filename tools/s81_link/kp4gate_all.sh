#!/bin/bash
L=/srv/opentallas-scratch2/claude/hard-s81-serdes-1; O=$1; mkdir -p $O
r() { docker run --rm --memory=16g --cpus=8 -v $L/wt:$L/wt:ro -v $L/kp4gate.sh:$L/kp4gate.sh:ro -v $O:$O --entrypoint bash verilator/verilator:v5.032 $L/kp4gate.sh $O "$@" > $O/$1.txt 2>&1; }
docker run --rm -v $L/wt:$L/wt:ro -v $O:$O --entrypoint python3 verilator/verilator:v5.032 $L/wt/tools/s81_link/rs544.py vectors $O/vec.hex --n 16 --seed 5 > /dev/null 2>&1
r base & r synl OT_S81_KP4_SYN_LOCAL OT_S81_KP4_AM_FACE3 & r it2 OT_S81_KP4_SYN_LOCAL OT_S81_KP4_AM_FACE3 OT_S81_KP4_BM_IT2 & r it2_pe OT_S81_KP4_SYN_LOCAL OT_S81_KP4_AM_FACE3 OT_S81_KP4_BM_PE_LOCAL OT_S81_KP4_BM_IT2 & r it2_mut OT_S81_KP4_SYN_LOCAL OT_S81_KP4_AM_FACE3 OT_S81_KP4_BM_IT2 OT_BM_IT2_MUT & r it2_all OT_S81_KP4_SYN_LOCAL OT_S81_KP4_AM_FACE3 OT_S81_KP4_BM_PE_LOCAL OT_S81_KP4_BM_IT2 OT_S81_KP4_ENC_LA OT_S81_RCK_RX_SPCYC OT_S81_RCK_TX_PPCYC &
wait; cat $O/*.txt | cut -c1-300; echo KP4GATE_DONE
