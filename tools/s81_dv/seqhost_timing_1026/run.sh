#!/bin/bash
# Run ONLY through ot-run. Arguments: fresh output directory, seqhost|bk.
set -euo pipefail
O=$(realpath -m "$1"); U=${2:-seqhost}
ROOT=$(git rev-parse --show-toplevel)
case "$U" in seqhost) TOP=dsdv_hostb_seqhost_mux; TB=tb_seqhost_timing;; bk) TOP=dsdv_bk_sel_vmtx; TB=tb_bk_timing;; *) exit 2;; esac
python3 "$ROOT/tools/s81_dv/seqhost_timing_1026/prepare.py" "$O/source" "$TOP" "${3:-physical/die_plan/s81/bind/asbuilt_b178_coll.json}"
git rev-parse HEAD > "$O/source_commit.txt"
cd "$O/source"
mkdir run
"$HOME/.local/opentallas-tools/bin/verilator" --binary --timing -Wno-fatal -Wno-WIDTH -Wno-PINMISSING -Wno-TIMESCALEMOD \
 --top-module "$TB" --build-jobs "${JOBS:-4}" -MAKEFLAGS 'OPT_FAST=-O1 OPT_SLOW=-O0' --Mdir run/obj -f defines.f -f files.f >run/build.log 2>&1
"run/obj/V$TB" >run/base.log 2>&1
grep -E '^SEQ_|^BK_|^PASS|^FAIL' run/base.log
grep -q '^PASS' run/base.log
"run/obj/V$TB" +mut_payload=1 >run/mut_payload.log 2>&1
grep -q '^FAIL' run/mut_payload.log
if [ "$U" = seqhost ]; then
 for phase in 1 2 3; do
  "run/obj/V$TB" +phase=$phase >run/mut_phase$phase.log 2>&1
  grep -q '^FAIL' run/mut_phase$phase.log
 done
 CHECKER=check.py
else
 CHECKER=check_bk.py
fi
python3 "$ROOT/tools/s81_dv/seqhost_timing_1026/$CHECKER" --log run/base.log --sources source_record.json --out "$O/receipt.json"
if python3 "$ROOT/tools/s81_dv/seqhost_timing_1026/$CHECKER" --log run/base.log --sources source_record.json --out "$O/invalid_shifted.json" --expect-shift 1 >run/mut_timing.log 2>&1; then
 exit 3
fi
grep -q TIMING_RECEIPT_MUTANT_CAUGHT run/mut_timing.log
