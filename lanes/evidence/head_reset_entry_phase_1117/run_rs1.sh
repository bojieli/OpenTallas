#!/bin/bash
# FABLE-FIX-HEAD-RESET rs1: functional gates of the reset entry-phase compose (plan 3210bf1f + rs1 rows), recipe of
# HEAD-R3 hr3/run_f1.sh with this lane's code tree (branch sha in code/SOURCE_SHA).  One attempt per directory.
set -u
R=/srv/opentallas-scratch2/claude/fable-fix-head-reset/rs1
L=/srv/opentallas-scratch2/claude/head-die-r/nf15e_e10
P=$R/prep_rs1; O=$R/gates_rs1
[ ! -e $R/RS1_ATTEMPTED ] || { echo already attempted; exit 79; }; date -Is > $R/RS1_ATTEMPTED
mkdir -p "$O"; cd "$R/code"
echo "code $(cat SOURCE_SHA) plan $(sha256sum $P/source_plan.json | cut -c1-64)"
python3 -I tools/die_plan/schema.py validate "$P/source_plan.json" > "$O/validate.log" 2>&1; echo VALIDATE_RC=$?
python3 -I tools/die_plan/pin_entry_phase.py rows "$P/source_plan.json" "$O/entry_phase_rows.json" > "$O/rows.log" 2>&1; echo ROWS_RC=$?
python3 -I tools/s81_head/head_native_release_receipt.py --plan "$P/source_plan.json" --proof-dir /srv/opentallas-scratch2/claude/head-die-r/native_release_proof --out "$R/native_receipt_rs1" > "$O/receipt.log" 2>&1
echo RECEIPT_RC=$?
python3 -I tools/s81_head/head_wave_kit_rtl.py export --plan "$P/source_plan.json" --out "$R/kit_rtl_rs1" --type hd_tile > "$O/kit_rtl.log" 2>&1
echo KIT_RTL_RC=$?
python3 -I tools/s81_head/head_die_portbind.py "$P/source_plan.json" --clock-landing "$P/source_sidecar.json" --out "$O/bind" > "$O/bind.log" 2>&1
B=$?; echo BIND_RC=$B
if [ "$B" = 0 ]; then
python3 -I tools/s81_head/head_gen_cohort.py "$P" "$O/bind/gen" --json "$O/cohort.json" > "$O/cohort.log" 2>&1
echo COHORT_RC=$?
python3 -I tools/die_plan/gen_lane_latcheck.py "$P/source_plan.json" --rtl "$P/published" --rtl "$O/bind/gen" --landings "$O/bind/gen/gen_clock_landings.json" --fixed-in-core --tsv "$O/latcheck.tsv" --json "$O/latcheck.json" > "$O/latcheck.log" 2>&1
echo LATCHECK_RC=$?
fi
python3 -I tools/die_plan/check.py "$P/source_plan.json" --native-reset-receipt "$R/native_receipt_rs1/native_release_receipt.json" --out "$O/g0" --quiet > "$O/g0.log" 2>&1
echo G0_RC=$?
for f in validate rows receipt kit_rtl bind cohort latcheck g0; do echo "== $f: $(tail -1 $O/$f.log 2>/dev/null | cut -c1-400)"; done
echo RS1_DONE
