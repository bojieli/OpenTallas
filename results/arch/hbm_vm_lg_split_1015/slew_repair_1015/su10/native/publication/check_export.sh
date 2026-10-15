#!/bin/bash
set -euo pipefail
base=/srv/opentallas-scratch/codex/lg-su10-slew-repair-1015
src=/srv/opentallas-scratch/codex/lg-su10-native-route-1015/src
cd "$src"
python3 tools/tt_views/view_export.py --orfs-dir "$base/work" --name hfd_vm_lg_su10 --out "$base/views_checked/hfd_vm_lg_su10" --interface-sdc "$src/physical/ref_tile/vm_lg_bank_su10_static_1015/signoff.sdc" --corners ss,ff,tt --post-sdc "$src/physical/ref_tile/vm_lg_bank_su10_static_1015/signoff.sdc" --post-sdc "$src/physical/common_flow/io_ref_routed.sdc" --expect-tt 269.9 --expect-ff 29.9 --require-check --signal-max-layer M5 --pg-max-layer M5 --signal-audit-tcl "$src/tools/ref_tile/signal_layer_audit.tcl" > "$base/export_checked.log" 2>&1
cp "$base/views_checked/hfd_vm_lg_su10/hfd_vm_lg_su10.lef" "$base/views_checked/hfd_vm_lg_su10/hfd_vm_lg_su10.raw.lef"
python3 tools/hier_contract/abstract_pin_stub.py "$base/views_checked/hfd_vm_lg_su10/hfd_vm_lg_su10.lef" "$base/views_checked/hfd_vm_lg_su10/hfd_vm_lg_su10.lef" > "$base/lef_postprocess.log"
python3 tools/hier_contract/child_lint.py "$base/views_checked/hfd_vm_lg_su10/hfd_vm_lg_su10.lef" --libs "$base/views_checked/hfd_vm_lg_su10" --cap M5 --strict-pockets --json > "$base/strict_child_lint.json"
cp "$base/ck_routed.json" "$base/views_checked/hfd_vm_lg_su10/insertion.json"
