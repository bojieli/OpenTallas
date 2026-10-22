#!/bin/bash
# S81-RATE3: FSEQ benches of the TOPO+PROP compiled phases; usage fseq3.sh FRAME BUILD OP P
set -u
D=/srv/opentallas-scratch/claude/s81-rate3; cd $D/root
export OT_XS_QPAIRS=12 OT_XS_GU_MERGE=1 OT_XS_CAL_SEGMENT=1 OT_XS_TOPO=1 OT_XS_PROP=${PROP:-1} PYTHONDONTWRITEBYTECODE=1
timeout 5400 python3 $D/fseq3.py $D/out/fseq3${TAGSUF:-} "$@"
