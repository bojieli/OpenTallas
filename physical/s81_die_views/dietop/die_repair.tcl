# S81 die-net repeaters (owner ruling 2026-10-16, HANDOFF 0cl: repeaters inside a registered relay hop are normal design;
# the die standard forbids only a missing relay register).  Sourced by dietop_grt_sta.sh when OT_DIE_REPAIR=1, after the
# placed die is loaded and before global route.
#
# Measured basis (H-REACH, claude/sdie-reach-1016, tools/s81/relay_native_pair.py on CLOSED native netlists + routed
# SPEF): an UNBUFFERED die hop is slew-limited at the receiver's first native cell (ot_inhold HB2xp67/A, 260 ps
# set_max_transition of every closed view) at 100-200 um; with repair_design repeaters (BUFx8/BUFx6f ~ every 160 um)
# the per-cycle reach is 600-750 um at TT 833 (setup-limited, FF hold OK from 100 um).  The bound views' ETM input pins
# carry no slew limit and hide the native first cell, so an ETM-driven repair leaves 175-225 um hops unrepeated while
# the native cell fails (measured: rly_63_WE 293 ps, rly_66_SW 332 ps at 200 um).  Hence the native-aware rule here:
#   * every die net longer than OT_DIE_REPAIR_MAX_WIRE (default 175 um) gets repeaters (-max_wire_length), and
#   * the slew / cap limits are the closed views' 260 ps max_transition and the library max_capacitance.
# Clock and reset distribution nets are NOT repeated here (planned clock trees / reset forests own them):
#   n_clk_* n_rst_* n_ck_col_* n_rs_col_* and every net matching OT_DIE_REPAIR_SKIP (Tcl glob list).
# Repeaters: BUFx4 .. BUFx8 only (the measured runs chose ~92 % BUFx8, 8 % BUFx6f), legalised on the die rows
# (GEN's initialize_floorplan -site asap7sc7p5t gives rows over the whole die; macros block their own rows).
# Outputs: /work/die_rep.v (repaired netlist: the die STA reads it instead of /kit/die.v), /work/repaired.odb,
# /work/die_repair.json (counts).  Any failure exits non-zero (a die with unrepaired long nets is not a result).

proc ot_rep_fail {msg} { puts "OT_DIE_REPAIR FAIL $msg"; flush stdout; exit 3 }
set ot_rep_t0 [clock seconds]
set ot_rep_mw [expr {[info exists ::env(OT_DIE_REPAIR_MAX_WIRE)] ? $::env(OT_DIE_REPAIR_MAX_WIRE) : 175}]
set ot_rep_slew [expr {[info exists ::env(OT_DIE_REPAIR_SLEW)] ? $::env(OT_DIE_REPAIR_SLEW) : 260}]
# libraries: the kit's TT view libs (bound closed views + interim pin-registered libs) and the ASAP7 RVT TT cells
if {![file exists /kit/libs_tt.txt]} { ot_rep_fail "no /kit/libs_tt.txt (mount the STA kit at /kit)" }
set ot_rep_n 0
foreach l [split [string trim [read [open /kit/libs_tt.txt]]] "\n"] {
  if {$l eq ""} continue
  if {![file exists $l]} { ot_rep_fail "kit lib missing in the container: $l (mount the source root read-only)" }
  read_liberty $l; incr ot_rep_n
}
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_TT_nldm_*.lib*] { read_liberty $l }
puts "OT_DIE_REPAIR libs kit=$ot_rep_n"
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
set_wire_rc -signal -layer M4
set_max_transition $ot_rep_slew [current_design]
set_dont_use [get_lib_cells -quiet *_ASAP7_75t_R]
unset_dont_use [get_lib_cells {BUFx4_ASAP7_75t_R BUFx4f_ASAP7_75t_R BUFx5_ASAP7_75t_R BUFx6f_ASAP7_75t_R BUFx8_ASAP7_75t_R}]
set ot_rep_skip {n_clk_* n_rst_* n_ck_col_* n_rs_col_*}
if {[info exists ::env(OT_DIE_REPAIR_SKIP)]} { set ot_rep_skip [concat $ot_rep_skip $::env(OT_DIE_REPAIR_SKIP)] }
set ot_rep_dt [get_nets -quiet $ot_rep_skip]
if {[llength $ot_rep_dt]} { set_dont_touch $ot_rep_dt }
puts "OT_DIE_REPAIR skip_nets=[llength $ot_rep_dt] max_wire_um=$ot_rep_mw max_transition_ps=$ot_rep_slew"
set ot_rep_c0 [llength [get_cells -quiet *]]
estimate_parasitics -placement
if {[catch {repair_design -max_wire_length $ot_rep_mw -slew_margin 0 -cap_margin 0} e]} { ot_rep_fail "repair_design: $e" }
set ot_rep_c1 [llength [get_cells -quiet *]]
if {[catch {detailed_placement} e]} { ot_rep_fail "detailed_placement: $e" }
if {[catch {check_placement -verbose} e]} { puts "OT_DIE_REPAIR WARN check_placement: $e" }
write_verilog /work/die_rep.v
write_db /work/repaired.odb
set f [open /work/die_repair.json w]
puts $f "{\"repeaters\": [expr {$ot_rep_c1 - $ot_rep_c0}], \"max_wire_um\": $ot_rep_mw, \"max_transition_ps\": $ot_rep_slew, \"skip_nets\": [llength $ot_rep_dt], \"seconds\": [expr {[clock seconds] - $ot_rep_t0}]}"
close $f
puts "OT_DIE_REPAIR DONE repeaters=[expr {$ot_rep_c1 - $ot_rep_c0}] s=[expr {[clock seconds] - $ot_rep_t0}]"
