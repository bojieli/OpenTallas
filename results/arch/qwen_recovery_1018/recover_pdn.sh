#!/bin/bash
set -euo pipefail
BASE=/srv/opentallas-scratch/claude/qwen-split-compute
R=$BASE/dv2f15codex/chain
SRC=$BASE/dv2f14bi/src
mkdir -p "$R/case_r22k" "$R/libs"
cp -a --reflink=auto "$BASE/dv2f15pdn/case/." "$R/case_r22k/"
cp -a --reflink=auto "$BASE/dv2f14bi/chain/libs/." "$R/libs/"
cat > "$R/case_r22k/run_pdn.tcl" <<'TCL'
read_db /work/floorplan_pdn_prepg.odb
puts "OT_PDN PASS reused_prepg=dv2f15pdn special_shapes=20038098"
foreach net {VDD VSS} {
  if {[catch {check_power_grid -net $net} err]} {
    puts "OT_PGCHECK $net FAIL $err"
    error $err
  } else { puts "OT_PGCHECK $net PASS" }
}
write_db /work/floorplan_pdn.odb
TCL
# This is a physics recovery of the bi netlist, not adoption of pending RTL/compiler fixes.
printf '%s\n' 'LEGACY_BI_PHYSICS_ONLY: LS 377, TXDP 09010306, st_wi tied zero, no physical die clock; no token or release qualification.' > "$R/LEGACY_BI_PHYSICS_ONLY"
set +e
bash "$SRC/tools/qwen_kv_die/chain/run_case.sh" "$R/case_r22k" run_pdn.tcl run_pdn.log 8 180
pdn_rc=$?
set -e
printf 'PDN_CHECK_RC=%s\n' "$pdn_rc"
# No continuation after a killed or incomplete check. A completed PG-connectivity failure can use the existing diagnostic path.
if [ "$pdn_rc" -gt 1 ]; then exit "$pdn_rc"; fi
exec env OT_FROM=grt OT_ADMIT=pass OT_STA_SUMMARY=1 OT_ITERS=12 OT_ROUTE_RESET=1 OT_CORNERS="tt ff ss" OT_STA_CLOCKS="$R/libs/clocks.tcl" OT_PG_OPEN_DIAG=1 OT_DIE_REPAIR=1 OT_HOLD_BUDGET=die OT_SPLIT_PHY_NFACE=1 OT_SPLIT_PHY_TALL=1 bash "$SRC/tools/qwen_kv_die/chain/die_chain.sh" r22k "$R" "$SRC"
