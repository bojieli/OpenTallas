#!/bin/bash
set -uo pipefail
cd "$(dirname "$0")"
python3 -u tools/die_plan/bind.py bind physical/die_plan/s81/die_plan.json --asbuilt physical/die_plan/s81/bind/asbuilt_b178_coll.json --out out --strict >bind.log 2>&1
rc=$?; echo $rc > bind.exit; echo $rc > gate.exit; exit $rc
