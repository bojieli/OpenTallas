#!/bin/bash
set -uo pipefail
cohort_root=$(cd "$(dirname "$0")" && pwd)
cd "$cohort_root"
cohort_plan=physical/die_plan/s81/die_plan.json
cohort_manifest=physical/die_plan/s81/bind/asbuilt_b178_coll.json
python3 -u tools/die_plan/bind.py elab "$cohort_plan" --asbuilt "$cohort_manifest" --out out --mem 32 >elab.log 2>&1
elab_rc=$?
printf "%s\n" "$elab_rc" >elab.exit
if [ "$elab_rc" != 0 ]; then printf "%s\n" "$elab_rc" >gate.exit; exit "$elab_rc"; fi
python3 -u tools/die_plan/bind.py bind "$cohort_plan" --asbuilt "$cohort_manifest" --out out --strict >bind.log 2>&1
bind_rc=$?
printf "%s\n" "$bind_rc" >bind.exit
printf "%s\n" "$bind_rc" >gate.exit
exit "$bind_rc"
