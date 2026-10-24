# GENERATED-KIT helper (tools/die_plan, CLK-STD 10-23): the routed wire of every clock tap port to its loads.
# The die STA (gen_phys.sta_die_tcl, MODE flat) loses this wire: the partition SPEF net of a tap port hangs off a
# HIERARCHICAL pin, the flat net's driver is the die clk port, so OpenSTA drops the partition part (CP1 r9: clk_t3
# 118 ps in the die vs 158 ps kit-alone; fW_r1_c1_b0/wire115088/A arrival 0 / slew 0).  This script measures, on the
# kit's own routed netlist + SPEF with the tap ports ideal, the arrival (= wire delay) and slew at each load pin of each
# tap port net; the die STA re-applies them (set_assigned_delay -net / set_assigned_transition).
#   env ODB (6_final.odb or 5_route.odb), SPEF (optional; else estimate_parasitics -global_routing / -placement),
#       SDC, OUT (tap_wire.tsv), CORNER (default TT)
set C [expr {[info exists ::env(CORNER)] ? $::env(CORNER) : "TT"}]
set PL /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [glob $PL/lib/NLDM/*_RVT_${C}_*.lib* $PL/lib/NLDM/*_LVT_${C}_*.lib*] {
  if {[string match *FAKE* $f] || [string match *SRAM* $f]} continue
  read_liberty $f
}
if {[info exists ::env(EXTRA_LIBS)]} { foreach f $::env(EXTRA_LIBS) { read_liberty $f } }
read_db $::env(ODB)
read_sdc $::env(SDC)
source $PL/setRC.tcl
if {[info exists ::env(SPEF)] && [file exists $::env(SPEF)]} {
  read_spef $::env(SPEF); set rc spef
} elseif {![catch {estimate_parasitics -global_routing}]} { set rc grt } else { estimate_parasitics -placement; set rc placement }
set_propagated_clock [all_clocks]
report_wns
set blk [ord::get_db_block]
set rows {}
foreach bt [$blk getBTerms] {
  set n [$bt getName]
  if {![regexp {^clk(_t[0-9]+|_c[0-9]+)?$} $n]} continue
  set net [$bt getNet]
  if {$net eq "NULL" || $net eq ""} continue
  foreach it [$net getITerms] {
    if {[[$it getMTerm] getIoType] ne "INPUT"} continue
    lappend rows [list $n "[[$it getInst] getName]/[[$it getMTerm] getName]"]
  }
}
set fh [open $::env(OUT) w]
puts $fh "# tap_wire v1 corner $C rc $rc: port load_pin arr_rise_ps arr_fall_ps slew_rise_ps slew_fall_ps"
foreach r $rows {
  lassign $r port pn
  set p [get_pins -quiet $pn]
  if {$p eq ""} continue
  set v {}
  foreach k {arrival_max_rise arrival_max_fall slew_max_rise slew_max_fall} {
    set a [get_property $p $k]
    if {$a eq "" || $a eq "INF" || $a eq "-INF"} { set a 0 }
    lappend v [format %.3f $a]
  }
  puts $fh "$port $pn [join $v { }]"
}
close $fh
puts "OT_TAP_WIRE [llength $rows] tap loads ($rc) -> $::env(OUT)"
