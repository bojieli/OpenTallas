#!/bin/bash
cd /
set -euo pipefail
D=/srv/opentallas-scratch2/claude/codex-kv-types-1113/pc_pg
set +e
docker run --rm --name codex-kv-pc-pdn-control-1113 -v "$D:/out" openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /out/pdn_control.tcl > "$D/pdn_control.log" 2>&1
rc=$?
set -e
if [ "$rc" = 0 ] || ! grep -q PDN-0006 "$D/pdn_control.log"; then echo CONTROL_NOT_REPRODUCED_RC=$rc;exit 2;fi
echo BLOATED_PDN_NEGATIVE_CONTROL_REPRODUCED
docker run --rm --name codex-kv-pc-pdn-exact-1113 -v "$D:/out" openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /out/pdn_exact.tcl > "$D/pdn_exact.log" 2>&1
echo EXACT_NATIVE_ONE_TARGET_PDN_PASS
