#!/bin/bash
set -euo pipefail
SRC=/srv/opentallas-scratch2/claude/flow-clock-r9/bd_w60_p2
OUT=/srv/opentallas-scratch2/claude/codex-flow-hold-2249/bd_local16
SO=/srv/opentallas-scratch2/claude/wt/flow-clock-r9
bash "$SO/tools/die_plan/post_route_drv/prd_mk.sh" "$SRC" "$OUT" m10 "$SO"
cat > "$OUT/prd_hook.tcl" <<'TCL'
# Single combinational-data resize; retained routed-RCX what-if predicted +4.20ps vs -3.55ps.
read_spef $::env(RESULTS_DIR)/6_final.spef
source /work/clk_freeze.tcl
ot_clk_freeze
set inst [get_cells -quiet place12022]
if {[llength $inst] != 1 || [get_property $inst ref_name] ne "BUFx10_ASAP7_75t_R"} {error "BD_LOCAL unexpected source master"}
set cell [get_lib_cells -quiet *TT*/BUFx16f_ASAP7_75t_R]
if {[llength $cell] != 1} {error "BD_LOCAL missing unique TT buffer target ($cell)"}
global_route -start_incremental
replace_cell $inst $cell
puts "BD_LOCAL resized place12022 BUFx10 -> BUFx16f, 0 cycles"
detailed_placement
check_placement
global_route -end_incremental
ot_clk_freeze_assert post_grt
estimate_parasitics -global_routing
write_guides $::env(RESULTS_DIR)/route.guide
puts "OT_PRD sink guard: 0 clock-net instance masters restored"
TCL
