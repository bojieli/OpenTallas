#!/bin/bash
set -u
D=/srv/opentallas-scratch/claude/closure-loop/s81dvbk_hist32_b0r3-hb0r3-bd6f52e8c
A=$D/codex_native_audit
O=$(find "$D/routes" -path '*/base/6_final.odb' -print -quit)
S=${O%.odb}.spef
sha256sum "$O" "$S" "${O%.odb}.v" > "$A/active_before.sha256"
python3 "$A/tools/closure_loop/pg_receipt.py" verify "$O" --spef "$S" --receipt-dir "$A/pg_receipts" --collector "$A/physical/common_flow/audit_native_pg.tcl" > "$A/pg_receipt.log" 2>&1
pg_rc=$?; echo PG_RECEIPT_RC=$pg_rc
docker run --rm -v "$D:/job:ro" -v "$A:/audit" openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /audit/dump_hist32_native.tcl > "$A/endpoint_pg_grid.log" 2>&1
grid_rc=$?; echo ENDPOINT_GRID_RC=$grid_rc
docker run --rm -v "$D:/job:ro" -v "$A:/audit" openroad/orfs:asap7lock python3 /audit/analyze_hist32_native.py > "$A/role_reach.log" 2>&1
role_rc=$?; echo ROLE_REACH_RC=$role_rc
sha256sum -c "$A/active_before.sha256" > "$A/active_after_check.log" 2>&1
sha_rc=$?; echo IMMUTABLE_ACTIVE_RC=$sha_rc
cat "$A/role_reach.log"
if [ "$pg_rc" != 0 ] || [ "$grid_rc" != 0 ] || [ "$role_rc" != 0 ] || [ "$sha_rc" != 0 ]; then exit 1; fi
