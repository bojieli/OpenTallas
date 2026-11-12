#!/bin/bash
# bind_r2.sh PLAN OUT : VISLAYOUT2-S81 strict bind of a candidate S81 plan (positions-only delta on plan_h2_2249), same
# source / asbuilt as the bind of record kw43t51/bind8 (src_t51f, asbuilt_f); elaboration files reused from bind8.
set -uo pipefail; cd /
PL=$1; O=$2
S=/srv/opentallas-scratch2/claude/kw43t51/src_t51f; G=/srv/opentallas-scratch2/claude/kw43t51/bind8
ASB=/srv/opentallas-scratch2/claude/type-safe-4/s81p3/asbuilt_f.json
rm -rf $O; mkdir -p $O; for f in asbuilt.json asbuilt.ys asbuilt_lib_stubs.sv asbuilt_sources.json provenance_elab.json; do cp -a $G/$f $O/$f; done
PD=$O.plandir; rm -rf $PD; mkdir -p $PD; for f in $S/physical/die_plan/s81/*; do ln -s "$f" $PD/; done
cp $PL $PD/plan_vl2.json
echo "bind start $(date) plan=$(sha256sum $PD/plan_vl2.json|cut -c1-12)"
s=$(date +%s)
cd $S && OT_NATIVE_RESET_SCOPE=selected timeout -s ABRT 7200 /usr/local/bin/ot-heavy --mem 48 -- python3 -I -X faulthandler tools/die_plan/bind.py bind $PD/plan_vl2.json --out $O --asbuilt $ASB --strict
echo "BIND_RC=$? wall=$(( $(date +%s)-s )) s end $(date)"
python3 -I -c "import json;r=json.load(open('$O/bind_report.json'));e=r['errors'];print('BIND errors',len(e) if isinstance(e,list) else e, str(e)[:600])"
