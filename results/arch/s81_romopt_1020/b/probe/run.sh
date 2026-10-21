#!/bin/bash
# S81-ROMOPT-B: xs_capacity run with the release flags; usage romoptb_run.sh TAG SPEC COMPACT QPAIRS [extra args]
set -u; D=/srv/opentallas-scratch/claude/s81-romopt-b; T=$1; SPEC=$2; CT=$3; QP=$4; shift 4
O=$D/out/$T; [ -e $O ] && { echo REFUSE_EXISTING_OUT; exit 2; }; mkdir -p $D/out; cd $D/root
export OT_XS_QPAIRS=$QP OT_XS_GU_MERGE=1 OT_XS_TOPO=1 OT_XS_PROP=1 OT_XS_CAL_SEGMENT=1 OT_XS_APROJ_TOPO=1 OT_XS_COMPACT_TAILS=$CT OT_XS_CAP_VDEPTH=${VDEPTH:-} PYTHONDONTWRITEBYTECODE=1
env | grep ^OT_XS_ | sort; sha256sum tools/s81_dv/layer_prog/xs_{capacity,place,bf,topo}.py tools/s81_dv/layer_prog/lower_xs.py tools/v41_die_images_w17w10.py
python3 tools/s81_dv/layer_prog/xs_capacity.py run --spec $SPEC --fixtures-root /srv/opentallas-scratch/claude/s81-calpipe/fixtures \
  --die-src /srv/opentallas-scratch/claude/toksim-s81b-fwoa/dieref --out $O "$@" > $O.log 2>&1; rc=$?
grep -E "XS_CAP|Error|Traceback" $O.log | cut -c1-1200; echo "ROMOPTB $T rc=$rc"; exit $rc
