#!/bin/bash
set -u
D=/srv/opentallas-scratch/claude/closure-loop/s81dvbk_hist32_b0r3-hb0r3-bd6f52e8c
A=$D/codex_native_audit
python3 "$A/tools/hier_contract/native_pin_audit.py" --root "$D/src" --view "$D/record/views/ot_s81ph_native_sel_hist_bank" > "$A/pin_audit.json" 2> "$A/pin_audit.err"
echo PIN_AUDIT_RC=$?
docker run --rm -v "$D:/job:ro" -v "$A:/audit" openroad/orfs:asap7lock bash -lc 'N=$(find /job/routes -path "*/base/6_final.v" -print -quit); args=(); for p in /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_TT*; do args+=(--liberty "$p"); done; python3 /audit/tools/ref_tile/native_census.py --netlist "$N" --top ot_s81ph_native_sel_hist_bank "${args[@]}" --out /audit/native_final.json' > "$A/native_final.log" 2>&1
echo FINAL_CENSUS_RC=$?
python3 - "$A" <<'PYC'
import json,sys
from pathlib import Path
a=Path(sys.argv[1]); p=json.loads((a/'pin_audit.json').read_text());n=json.loads((a/'native_final.json').read_text());print('PIN',p.get('pass'),p.get('errors'));print('FINAL_NATIVE',n.get('status'),'max',n.get('max_dynamic_loads'),'viol',len(n.get('violations',[])))
PYC
