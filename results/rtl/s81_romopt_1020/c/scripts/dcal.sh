#!/bin/bash
# S81-ROMOPT-C: die field calendars (xs_field_calendar die) + k-class static / MU check (xs_kslot_check die) with the
# release compiler options + OT_XS_KSLOT=K; usage dcal.sh K TAG SLICE [extra xs_kslot_check args]
set -u
L=/srv/opentallas-scratch/claude/s81-romopt-c; R=$L/root; K=$1; T=$2; SL=$3; shift 3
C=/srv/opentallas-scratch/claude/s81-calpipe; cd $R
export OT_XS_QPAIRS=12 OT_XS_GU_MERGE=1 OT_XS_CAL_SEGMENT=1 OT_XS_TOPO=1 OT_XS_PROP=1 OT_XS_KSLOT=$K PYTHONDONTWRITEBYTECODE=1 HDC_V41_ARITH=chunk8
echo "ENV QPAIRS=12 GU_MERGE=1 CAL_SEGMENT=1 TOPO=1 PROP=1 KSLOT=$K slice=$SL"
sha256sum tools/s81_dv/layer_prog/xs_{place,bf,topo,field_calendar,calendar_pack,wqb_die,calendar,kslot_check}.py tools/s81_dv/frame_return_plan.py tools/s81_dv/layer_prog/kslot_layouts.json tools/s81_dv/dv_layer_compile.py 2>&1
MU="$C/mu/calendar_ar_cal1.json $C/mu/calendar_mtp_cal1.json"
DS=/srv/opentallas-scratch/claude/toksim-s81b-fwoa/dieref
if [ "${CHECK_ONLY:-0}" != 1 ]; then
timeout 14000 python3 tools/s81_dv/layer_prog/xs_field_calendar.py die --fixtures-root $C/fixtures --die-src $DS --out $L/out/dcal_$T \
  --slice $SL --mu-cal $MU > $L/out/dcal_$T.log 2>&1; echo "DCAL $T rc=$?"
grep -E "XS_FIELD|Error|Traceback" $L/out/dcal_$T.log | cut -c1-900
fi
timeout 14000 python3 tools/s81_dv/layer_prog/xs_kslot_check.py die --fixtures-root $C/fixtures --die-src $DS --out $L/out/kchk_$T \
  --slice $SL --mu-cal $MU "$@" > $L/out/kchk_$T.log 2>&1; echo "KCHK $T rc=$?"
grep -E "XS_KSLOT|Error|Traceback" $L/out/kchk_$T.log | cut -c1-900
