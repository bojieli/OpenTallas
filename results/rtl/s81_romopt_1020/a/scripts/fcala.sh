#!/bin/bash
# S81-ROMOPT-A: die field calendars with the release defaults (xs_flags); usage fcala.sh CFG(o1o2|o1) SLICE
set -u
D=/srv/opentallas-scratch/claude/s81-romopt-a; R=$D/root; CFG=$1; SL=$2; shift 2; T=fcal_${CFG}_$SL
O=$D/out/$T; [ -e $O ] && { echo REFUSE_EXISTING_OUT; exit 2; }; cd $R
C=/srv/opentallas-scratch/claude/s81-calpipe; export PYTHONDONTWRITEBYTECODE=1
case $CFG in o1) export OT_XS_QPAIRS=10 OT_XS_COMPACT_TAILS=0;; o1o2nc) export OT_XS_COMPACT_TAILS=0;; o1o2c) export OT_XS_COMPACT_TAILS=1;; esac
python3 -c "import sys; sys.path.insert(0,'tools/s81_dv/layer_prog'); import xs_flags as X; print('ENV', X.describe())"
sha256sum tools/s81_dv/layer_prog/xs_{place,bf,topo,flags,field_calendar,calendar_pack,wqb_die,calendar}.py tools/s81_dv/dv_layer_compile.py
timeout 7200 python3 tools/s81_dv/layer_prog/xs_field_calendar.py die --fixtures-root $C/fixtures \
  --die-src /srv/opentallas-scratch/claude/toksim-s81b-fwoa/dieref --out $O --slice $SL \
  --mu-cal $C/mu/calendar_ar_cal1.json $C/mu/calendar_mtp_cal1.json "$@" > $O.log 2>&1; echo "FCALA $T rc=$?"
grep -E "XS_FIELD|Error|Traceback" $O.log | cut -c1-900; tail -3 $O.log | cut -c1-600
