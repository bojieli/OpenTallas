#!/bin/bash
# S81-ROMOPT-C: k-class layout search; usage ksearch.sh KSLOT FRAME OP OUTJSON [args]
set -u
L=/srv/opentallas-scratch/claude/s81-romopt-c; cd $L/root; K=$1; FR=$2; OP=$3; OUT=$4; shift 4
export OT_XS_QPAIRS=12 OT_XS_GU_MERGE=1 OT_XS_CAL_SEGMENT=1 OT_XS_TOPO=1 OT_XS_PROP=1 OT_XS_KSLOT=$K PYTHONDONTWRITEBYTECODE=1 HDC_V41_ARITH=chunk8
export OT_XS_KSLOT_LAYOUTS=/nonexistent
timeout 14000 python3 tools/s81_dv/layer_prog/kslot_search.py --frame $FR --op $OP --fixtures /srv/opentallas-scratch/claude/s81-calpipe/fixtures/L0 \
  --die-src /srv/opentallas-scratch/claude/toksim-s81b-fwoa/dieref --out $OUT "$@"
