#!/bin/bash
# HARD-QC-FORMS-1: private chain for a type with unsigned child cores, using the kit wave provisional-view step (KW-PROV-1).
# usage: run_prov.sh TAG TYPE ROUTED_DIR     (bind_TAG must exist; ROUTED_DIR = a copy of a wave item's prov/routed)
# kit-rtl on the bound plan -> prov_view.py make (overlay plan with provisional child views) -> gen..route on the overlay.
# DO_NOT_COUNT; a kit built on provisional views is never a sign-off.
cd /; P=/srv/opentallas-scratch2/claude/hard-qc-forms-1/pipe; TAG=$1; T=$2; RD=$3; W=$P/runs/$TAG/$T; L=$P/logs/prov_${TAG}_$T.out; exec >> $L 2>&1
BP=$P/tree/physical/die_plan/qwen_compute/plan_of_record/zz_bind_$TAG.json
export AUTO_HOST=1 BUILD_HOST=${BUILD_HOST:-epyc4}
echo "PROV_START $TAG $T $(date '+%F %T')"
bash $P/chain_qc.sh $TAG $T $BP $P/bind_$TAG rtl rtl || { echo "PROV_END FAIL rtl"; exit 1; }
PV=$P/provw/$TAG/$T; rm -rf $PV; mkdir -p $PV; cp -a $RD $PV/routed; cp $P/tree/tools/autopilot/prov_view.py $PV/   # outside W: ot-run --stage refuses the overlay plan folder (absolute links)
(cd $P/tree && nice -n 19 python3 -I $PV/prov_view.py make --plan $BP --type $T --out $PV --src $P/tree --routed $PV/routed --rtl $W/rtl) > $PV/make.log 2>&1; echo "PROV_MAKE rc=$?"
grep '^PROV_JSON ' $PV/make.log | tail -1 | cut -c11- > $PV/prov.json
OV=$(python3 -I -c 'import json,sys
try: j=json.load(open(sys.argv[1]))
except Exception: j={}
print(j.get("overlay_plan") or "" if j.get("ok") else "")' $PV/prov.json)
[ -n "$OV" ] || { echo "PROV_END FAIL prov_view (see $PV/make.log)"; tail -5 $PV/make.log; exit 2; }
echo "PROV_OVERLAY $OV"; cut -c1-800 $PV/prov.json
ALLOW_PLAN_MISMATCH=1 bash $P/chain_qc.sh $TAG $T $OV $P/bind_$TAG gen route; echo "PROV_END rc=$? $(date '+%F %T')"
