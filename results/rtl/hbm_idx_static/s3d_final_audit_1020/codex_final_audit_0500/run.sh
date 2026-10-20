#!/bin/bash
set -eu
D=/srv/opentallas-scratch/claude/closure-loop/hidx_sel_s3d_a-s3da-db0cdd31d
A=$D/codex_final_audit_0500
O=$(find "$D/routes" -path '*/base/6_final.odb' -print -quit)
V=${O%.odb}.v
S=${O%.odb}.spef
sha256sum "$O" "$V" "$S" > "$A/active_before.sha256"
python3 "$A/tools/closure_loop/pg_receipt.py" verify "$O" --spef "$S" --receipt-dir "$A/pg_receipts" --collector "$A/physical/common_flow/audit_native_pg.tcl" > "$A/pg_receipt.log" 2>&1
RELO=${O#$D/}
docker run --rm -v "$D:/job:ro" -v "$A:/audit" openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit -python /audit/native_audit.py "/job/$RELO" /audit/native_odb > "$A/native_odb.log" 2>&1
RELV=${V#$D/}
docker run --rm -v "$D:/job:ro" -v "$A:/audit" openroad/orfs:asap7lock bash -lc 'args=(); for p in /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_TT*; do args+=(--liberty "$p"); done; python3 /audit/tools/ref_tile/native_census.py --netlist "$1" --top ot_hidx_s3_ctl "${args[@]}" --out /audit/native_final.json' _ "/job/$RELV" > "$A/native_final.log" 2>&1
sha256sum -c "$A/active_before.sha256" > "$A/active_after_check.log"
echo AUDIT_DONE
