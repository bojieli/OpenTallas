# DSROM q-element abstract pin-access check (2026-10-04, S81 die finding xs_q1[151] DRT-0073): the die-level method of
# tools/dsrom_s81_fulldie.py (set_routing_layers M2-M9, pin_access) on the minimum component, one instance of the
# abstract in the die's orientation (N) with a 20 um margin.  env: Q_LEF (abstract), Q_MASTER, OUT_DIR.
set PLAT /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $PLAT/lef/asap7_tech_1x_201209.lef
read_lef $PLAT/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef $::env(Q_LEF)
set master [[ord::get_db] findMaster $::env(Q_MASTER)]
set mw [expr {[$master getWidth] / 1000.0}]; set mh [expr {[$master getHeight] / 1000.0}]
# one-instance netlist: every pin on its own net (pin access is computed per connected instance terminal)
set v [open $::env(OUT_DIR)/pa.v w]
puts $v "module pa_top ();"
set conns {}
array set msb {}
foreach mt [$master getMTerms] {
    if {[$mt getSigType] in {POWER GROUND}} continue
    set n [$mt getName]
    if {[regexp {^(.*)\[([0-9]+)\]$} $n -> b i]} {
        if {![info exists msb($b)] || $i > $msb($b)} { set msb($b) $i }
    } else { set msb($n) -1 }
}
foreach b [lsort [array names msb]] {
    if {$msb($b) >= 0} { puts $v "  wire \[$msb($b):0\] w_$b ;" } else { puts $v "  wire w_$b ;" }
    lappend conns ".$b (w_$b )"
}
puts $v "  $::env(Q_MASTER) u_q ([join $conns {, }]);"
puts $v "endmodule"
close $v
read_verilog $::env(OUT_DIR)/pa.v
link_design pa_top
set W [expr {$mw + 40.0}]; set H [expr {$mh + 40.0}]
initialize_floorplan -die_area "0 0 $W $H" -core_area "0 0 $W $H" -site asap7sc7p5t
source $PLAT/openRoad/make_tracks.tcl
place_inst -name u_q -location {20.16 19.98} -orientation R0 -status FIRM
set_routing_layers -signal M2-M9
puts "OT_PA_MASTER $::env(Q_MASTER) [format %.3f $mw] x [format %.3f $mh] pins=[llength [$master getMTerms]]"
if {[catch {pin_access -verbose 1} err]} { puts "OT_PA FAIL $err" } else { puts "OT_PA DONE" }
