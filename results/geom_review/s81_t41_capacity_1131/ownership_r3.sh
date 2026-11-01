#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-s81-t41-ownership-r3-1546
for V in Anear Bnear; do
 K=/srv/opentallas-scratch2/claude/codex-s81-bound-landing-r2-1131/${V}_corrected/gen/slice_station__t41
 D=$R/$V
 mkdir -p "$D"
 # Exactly the existing kit's assignment settings; no group/radius overrides.
 MAX=$(sed -n 's/^export OT_TAP_MAX_SINKS = //p' "$K/config.mk")
 PITCH=$(sed -n 's/^export OT_TAP_PITCH_UM = //p' "$K/config.mk")
 docker run --rm --user "$(id -u):$(id -g)" --memory=4g --memory-swap=4g --cpus=2 -v "$K:/work:ro" -v "$D:/out" -v "$R/ownership_r3.tcl:/probe.tcl:ro" -e OT_TAP_MAX_SINKS="$MAX" -e OT_TAP_PITCH_UM="$PITCH" -e RESULTS_DIR=/out openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /probe.tcl' > "$D/check.log" 2>&1
 printf '%s_RC0 %s\n' "$V" "$(date -Is)" >> "$R/status"
done
