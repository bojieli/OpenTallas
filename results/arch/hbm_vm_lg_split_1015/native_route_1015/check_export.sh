#!/bin/bash
set -euo pipefail
base=/srv/opentallas-scratch/codex/lg-native-route-1015
cd "$base/src"
python3 tools/tt_views/view_export.py --orfs-dir "$base/routes/lg_native_route_1015/work/orfs" --name ot_hbm_vm_lg_static_bank --out "$base/views_checked/ot_hbm_vm_lg_static_bank" --interface-sdc "$PWD/physical/ref_tile/vm_lg_bank_hc_static_1015/signoff.sdc" --corners ss,ff,tt --post-sdc "$PWD/physical/ref_tile/vm_lg_bank_hc_static_1015/signoff.sdc" --post-sdc "$PWD/physical/common_flow/io_ref_routed.sdc" --expect-tt 276.32 --expect-ff 24.95 --require-check --signal-max-layer M5 --pg-max-layer M5 --signal-audit-tcl "$PWD/tools/ref_tile/signal_layer_audit.tcl" > "$base/export_checked.log" 2>&1
