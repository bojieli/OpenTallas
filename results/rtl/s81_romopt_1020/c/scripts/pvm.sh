#!/bin/bash
# S81-ROMOPT-C: PV cadence measurement; usage pvm.sh KSLOT FRAME PVBUILD OP [PHASES..]
set -u
L=/srv/opentallas-scratch/claude/s81-romopt-c; cd $L/root; K=$1; shift
export OT_XS_QPAIRS=12 OT_XS_GU_MERGE=1 OT_XS_CAL_SEGMENT=1 OT_XS_TOPO=1 OT_XS_PROP=1 OT_XS_KSLOT=$K PYTHONDONTWRITEBYTECODE=1 HDC_V41_ARITH=chunk8
timeout 5400 python3 $L/pvmeasure.py $L/out/pv_k$K${TAGSUF:-} "$@"
