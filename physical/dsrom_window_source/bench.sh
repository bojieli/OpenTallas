#!/bin/bash
set -euo pipefail
OUT=${1:?output directory}
mkdir -p "$OUT"
python3 - <<'PY'
import sys
sys.path.insert(0, "tools")
from dsrom_window_pipeline_gate import controller_sources
print('source manifest verified', len(controller_sources(True)))
PY
CTL=rtl/dsrom_sys/s81_window_la/recovered_ctl_m2
TB=rtl/dsrom_sys/s81_window_la/tb_recovered_ctl_request_skid.sv
iverilog -g2012 -s tb_recovered_ctl_request_skid -o "$OUT/positive" "$CTL/ot_dsrom_window_source_ctl.sv" "$TB"
vvp "$OUT/positive" > "$OUT/positive.log"
grep -q 'PASS REQUEST_SKID width=339 sent=687 received=687' "$OUT/positive.log"
iverilog -g2012 -s tb_recovered_ctl_request_skid -o "$OUT/mutant" "$CTL/mutant_window_ctl_late_payload.sv" "$CTL/ot_dsrom_window_source_ctl.sv" "$TB"
set +e
vvp "$OUT/mutant" > "$OUT/mutant.log" 2>&1
rc=$?
set -e
test "$rc" = 1
grep -q 'REQUEST_PAYLOAD_MISMATCH transaction=0' "$OUT/mutant.log"
rm "$OUT/positive" "$OUT/mutant"
echo 'PASS source-manifest and production W339 skid positive/mutant'
