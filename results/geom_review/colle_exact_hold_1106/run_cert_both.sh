#!/bin/bash
set -euo pipefail
r=/srv/opentallas-scratch2/claude/codex-colle-exact-hold-1106
t=/srv/opentallas-scratch2/claude/codex-bank128-wface/release_bh
for side in ${COLLE_CERT_SIDES:-e w}; do
 k="$r/$side/repair1"
 test -s "$k/clk_geom_diff.json"
 python3 - "$k/clk_geom_diff.json" <<'PY'
import json,sys
p=json.load(open(sys.argv[1]));print('CLOCK_GATE_RECEIPT',p)
if p.get('verdict') not in ('PASS',) and p.get('pass') is not True: raise SystemExit('clock receipt not PASS')
PY
 python3 "$t/tools/die_plan/resign.py" run --kit "$k" --tag flow-20261106-bh-hbm --repo "$t/tag_manifest.json" --tools "$t/tools/die_plan" --out "$r/$side/cert1_bh" --auto --lec-mem 32g --name "codex-colle-$side-exact4" --lane CODEX-BANK128 --note "Exact four near-D noninverting hold buffers on retained COLLE i3. Own E/W pins, declare_clock_pin and all old instance/clock geometries preserved. No RTL/SDC/clock changes. Parent NEEDS_PARENT explicit; normal routed equivalence required."
 done
