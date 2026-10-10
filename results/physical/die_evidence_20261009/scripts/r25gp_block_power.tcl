# die-evidence-2 r25gp-power (2026-10-09): OpenSTA report_power of ONE hardened block at TT 0.70 V / 25 C.
# Inputs (env): PW_ODB, PW_SDC, PW_SPEF ("" = placement-estimated parasitics, for a post-CTS database),
#               PW_MACRO_LIBS (dir searched for <master>/<master>_tt.lib of every block master), PW_OUT (key=value file).
# Libraries: every ASAP7 TT std-cell liberty of the RVT, LVT and SLVT families (a route may carry VT swaps).
# Clock: the route's own SDC (0.833 ns, 1.2 GHz); clock nets toggle every cycle (OpenSTA derives the clock activity
# from the defined clock: 2 transitions per period).
# Activity points (transitions per clock period on every non-clock net, the floorplan's 'peak in-phase' point):
#   a20: set_power_activity -global 0.2 + -input 0.2  (the stated point: every register / internal net at 0.2)
#   a10: the same at 0.1                               (option c)
#   a00: data idle, clock running (0.0)                 (the clocked floor an ICG removes, option a)
set out [open $::env(PW_OUT) w]
proc emit {k v} { global out; puts $out "$k=$v"; puts "PW $k=$v" }
set nldm /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
read_db $::env(PW_ODB)
set block [ord::get_db_block]
set die [$block getDieArea]
emit die_w_um [expr {([$die xMax] - [$die xMin]) / double([$block getDbUnitsPerMicron])}]
emit die_h_um [expr {([$die yMax] - [$die yMin]) / double([$block getDbUnitsPerMicron])}]
foreach f [lsort [glob $nldm/*_TT_*]] {
    if {[string match *SRAM* $f]} { continue }
    read_liberty $f
}
# block (macro) masters: read each one's own TT liberty when present; list the rest (their power is NOT counted)
set macros {}
foreach inst [$block getInsts] {
    set m [$inst getMaster]
    if {[$m isBlock]} { dict incr macros [$m getName] }
}
set missing {}
dict for {name n} $macros {
    set hits [glob -nocomplain $::env(PW_MACRO_LIBS)/$name/${name}_tt.lib]
    if {[llength $hits]} { read_liberty [lindex $hits 0]; emit macro_lib.$name "$n [lindex $hits 0]" } else {
        lappend missing "$name:$n"
    }
}
emit macro_missing_lib [join $missing ,]
read_sdc $::env(PW_SDC)
if {$::env(PW_SPEF) ne ""} {
    read_spef $::env(PW_SPEF)
    emit parasitics spef
} else {
    source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
    estimate_parasitics -placement
    emit parasitics placement-estimated
}
set_cmd_units -time ns -power W
set clk [lindex [all_clocks] 0]
emit clock [get_name $clk]
emit clock_period_ns [get_property $clk period]
emit clocks [llength [all_clocks]]
set nreg 0; foreach c [all_registers -cells] { incr nreg }
emit registers $nreg
set icg 0
foreach inst [$block getInsts] { if {[string match ICG* [[$inst getMaster] getName]]} { incr icg } }
emit icg_cells $icg
emit insts [llength [$block getInsts]]
foreach {tag a} {a20 0.2 a10 0.1 a00 0.0} {
    set_power_activity -global -activity $a
    set_power_activity -input -activity $a
    set dp [sta::design_power [sta::cmd_scene]]
    set k 0
    foreach grp {total sequential combinational clock macro pad} {
        foreach part {internal switching leakage total} {
            emit $tag.$grp.$part [lindex $dp $k]
            incr k
        }
    }
}
close $out
