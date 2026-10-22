#!/bin/bash
# S81-ROMOPT-C: k-class layout search with a stream stretch; usage ksearch_st.sh KSLOT STRETCH_SPEC FRAME OP OUTJSON [args]
set -u
L=/srv/opentallas-scratch/claude/s81-romopt-c; export OT_XS_KSLOT_STRETCH=$2; K=$1; shift 2
exec bash $L/ksearch.sh $K "$@"
