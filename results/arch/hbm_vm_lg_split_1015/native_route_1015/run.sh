#!/bin/bash
set -uo pipefail
base=/srv/opentallas-scratch/codex/lg-native-route-1015
export PATH="$base/bin:$PATH"
export SRC="$base/src"
cd "$SRC"
export OT_TTB_CORNER_MARK="$base/ttb_corner.txt"
python3 tools/closure_loop/tt_overlay.py "$SRC" || exit $?
export OT_CTS_FIX_HOOKS='physical/common_flow/cg_pushdown.tcl physical/common_flow/clk_net_protect.tcl physical/common_flow/link_budget_hook.tcl'
export OT_ORFS_CORNER_OVERRIDE=TC
export HM=0.03 OT_MM_FF_SDC='physical/ref_tile/vm_lg_bank_hc_static_1015/signoff.sdc' OT_PIN_GROUP_MAX=32
sha256sum rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_bank.sv rtl/hbm_accel/generic/vm/static/physical/native_bank_pin_audit.tcl tools/ref_tile/ref_route.sh > "$base/source_hashes.txt"
bash tools/ref_tile/ref_route.sh physical/ref_tile/vm_lg_bank_hc_static_1015/kit.env lg_native_route_1015 "$base/routes"
rc=$?
printf '%s\n' "$rc" > "$base/exit"
exit "$rc"
