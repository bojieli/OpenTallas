#!/bin/bash
# S81-CALPIPE 10-20: the die compiler's pipelined field calendars.  TAG MODE [args]
#   MODE die  : xs_field_calendar.py die (every layer class, all multi-phase field ops, layer image, MU check)
#   MODE dvc  : dv_layer_compile.py --layer L (lower_placed / lower_placed_bf emit prog/xs/<id>.calendar.json)
set -u
D=/srv/opentallas-scratch/claude/s81-calpipe; R=$D/root; T=$1; M=$2; shift 2
O=$D/out/$T; [ -e $O ] && { echo REFUSE_EXISTING_OUT; exit 2; }; mkdir -p $D/out; cd $R
DS=/srv/opentallas-scratch/claude/toksim-s81b-fwoa/dieref
if [ $M = die ]; then
  timeout 7200 python3 tools/s81_dv/layer_prog/xs_field_calendar.py die --fixtures-root $D/fixtures --die-src $DS --out $O \
    --mu-cal $D/mu/calendar_ar_cal1.json $D/mu/calendar_mtp_cal1.json "$@" > $O.log 2>&1; echo "FCAL $T rc=$?"; grep -E "XS_FIELD" $O.log | cut -c1-600
else
  L=$1; shift
  timeout 7200 python3 tools/s81_dv/dv_layer_compile.py --layer $L --out $O --die-src $DS --fixtures $D/fixtures/$L "$@" > $O.log 2>&1
  echo "DVC $T rc=$? $(ls $O/prog/xs/ 2>/dev/null | grep -c 'calendar.json') calendar records"; tail -2 $O.log
  for c in $O/prog/xs/*.calendar.json; do python3 -c "import json;c=json.load(open('$c'));print('DVC_CAL',c.get('layer'),c.get('op',c.get('ops')),c['mode'],c['period'],'phases',c['nphases'],'static',c['static']['PASS'],'span',c['predicted_span'])"; done
fi
echo FCAL_DONE $T
