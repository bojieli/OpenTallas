#!/bin/bash
set -u
L=/srv/opentallas-scratch2/claude/head-die-r/nf15e_e10
P=$L/stage/prep_f1; O=$L/gates_f1
[ ! -e $L/hr3/F1_ATTEMPTED ] || { echo already attempted; exit 79; }; date -Is > $L/hr3/F1_ATTEMPTED
cp -a $L/stage/prep_r2 $P || exit 1
mkdir -p "$O"; cd "$L/code"
python3 -I $L/hr3/compose_f1.py > "$O/compose.log" 2>&1; rc=$?; tail -3 "$O/compose.log" | cut -c1-900; echo COMPOSE_RC=$rc; [ $rc = 0 ] || exit 1
python3 -I tools/s81_head/head_native_release_receipt.py --plan "$P/source_plan.json" --proof-dir /srv/opentallas-scratch2/claude/head-die-r/native_release_proof --out "$L/native_receipt_f1" > "$O/receipt.log" 2>&1
echo RECEIPT_RC=$?
python3 -I tools/s81_head/head_wave_kit_rtl.py export --plan "$P/source_plan.json" --out "$L/kit_rtl_f1" --type hd_lep0N > "$O/kit_rtl.log" 2>&1
echo KIT_RTL_RC=$?
python3 -I tools/s81_head/head_die_portbind.py "$P/source_plan.json" --clock-landing "$P/source_sidecar.json" --out ../gates_f1/bind > "$O/bind.log" 2>&1
B=$?; echo BIND_RC=$B
if [ "$B" = 0 ]; then
python3 -I tools/s81_head/head_gen_cohort.py "$P" "$O/bind/gen" --json "$O/cohort.json" > "$O/cohort.log" 2>&1
echo COHORT_RC=$?
python3 -I tools/die_plan/gen_lane_latcheck.py "$P/source_plan.json" --rtl "$P/published" --rtl "$O/bind/gen" --landings "$O/bind/gen/gen_clock_landings.json" --fixed-in-core --tsv "$O/latcheck.tsv" --json "$O/latcheck.json" > "$O/latcheck.log" 2>&1
echo LATCHECK_RC=$?
fi
python3 -I tools/die_plan/check.py "$P/source_plan.json" --native-reset-receipt "$L/native_receipt_f1/native_release_receipt.json" --out "$O/g0" --quiet > "$O/g0.log" 2>&1
echo G0_RC=$?
for f in receipt kit_rtl bind cohort latcheck g0; do echo "== $f: $(tail -1 $O/$f.log 2>/dev/null | cut -c1-400)"; done
echo F1_DONE
