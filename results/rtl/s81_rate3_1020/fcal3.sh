#!/bin/bash
# S81-RATE3 10-20: die field calendars with the release compiler options (QPAIRS12 + GU_MERGE + CAL_SEGMENT) and
# OT_XS_TOPO=1 (physical frames per slice); usage fcal3.sh TAG SLICE [extra args]
set -u
D=/srv/opentallas-scratch/claude/s81-rate3; R=$D/root; T=$1; SL=$2; shift 2
O=$D/out/$T; [ -e $O ] && { echo REFUSE_EXISTING_OUT; exit 2; }; mkdir -p $D/out; cd $R
C=/srv/opentallas-scratch/claude/s81-calpipe
export OT_XS_QPAIRS=12 OT_XS_GU_MERGE=1 OT_XS_CAL_SEGMENT=1 OT_XS_TOPO=${TOPO:-1} OT_XS_PROP=${PROP:-0} PYTHONDONTWRITEBYTECODE=1
echo "ENV QPAIRS=$OT_XS_QPAIRS GU_MERGE=$OT_XS_GU_MERGE CAL_SEGMENT=$OT_XS_CAL_SEGMENT TOPO=$OT_XS_TOPO PROP=$OT_XS_PROP slice=$SL"
sha256sum tools/s81_dv/layer_prog/xs_{place,bf,topo,field_calendar,calendar_pack,wqb_die,calendar}.py tools/s81_dv/dv_layer_compile.py
timeout 7200 python3 tools/s81_dv/layer_prog/xs_field_calendar.py die --fixtures-root $C/fixtures \
  --die-src /srv/opentallas-scratch/claude/toksim-s81b-fwoa/dieref --out $O --slice $SL \
  --mu-cal $C/mu/calendar_ar_cal1.json $C/mu/calendar_mtp_cal1.json "$@" > $O.log 2>&1; echo "FCAL3 $T rc=$?"
grep -E "XS_FIELD|Error|Traceback" $O.log | cut -c1-900; tail -3 $O.log | cut -c1-600
