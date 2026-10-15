# Native CDC crossing arcs (A4 HBM group A 2026-10-14; pattern of the accepted dsfd_vm_fcn/fcc B8 constraint).
# Routed npin1 w1/w16: FF hold -88/-93 on 548 reg->reg endpoints, ALL two-domain crossings core_clk <-> vm_clk:
# slots -> landed_slots (400) and the first synchroniser flops of the epoch rails / Gray ack / Gray publish counts (148).
# Structure (ot_hbm_native_{bounded,sram}_cdc): ack / pub are Gray counts (and their complement rails) sampled by two
# flops; the 32-bit epochs change only while both sides are drained and are checked rail-against-rail after two flops (an
# incoherent sample is a transient mismatch that blocks, never a value); a landed slot is selected by the consumer only
# after its publication crossed two synchroniser edges, and the source does not rewrite it before the consumer's Gray
# release crossed back.  Constraint of those arcs, and of nothing else (by DESTINATION, the D of a first synchroniser /
# landing flop has no other source than the crossing):
#   source register -> first synchroniser flop : max datapath 0.5 x min period (Gray bus-skew bound), no hold relation
#   slots -> landed_slots                       : max datapath 1.0 x min period - 60 ps, no hold relation
# (OpenSTA has no -datapath_only / set_bus_skew: -ignore_clock_latency + false-path -hold is the same check.)
proc ot_ncdc_arcs {} {
  set t [expr {min([get_property [get_clocks core_clk] period],[get_property [get_clocks vm_clk] period])}]
  set syc {}; set syv {}; set ld {}
  foreach c [all_registers -cells] {
    set b [string trimleft [lindex [split [get_full_name $c] "\["] 0] "\\"]
    if {[lsearch -exact {ack1 ackn1 re1 ren1} $b] >= 0} {
      lappend syc $c
    } elseif {[lsearch -exact {pub1 pubn1 we1 wen1} $b] >= 0} {
      lappend syv $c
    } elseif {$b eq "landed_slots"} {
      lappend ld $c
    }
  }
  # -from the OTHER domain's clock: only the crossing arcs, never the destination's own reset / pin paths
  # (plain variables in the constraint commands: OpenSTA's sdc_file_line list-parses the calling command text)
  set dp [expr {0.5*$t}]; set dm [expr {$t-60.0}]
  set cc [get_clocks core_clk]; set vc [get_clocks vm_clk]
  if {[llength $syc]} {
    set_max_delay -ignore_clock_latency $dp -from $vc -to $syc
    set_false_path -hold -from $vc -to $syc
  }
  if {[llength $syv]} {
    set_max_delay -ignore_clock_latency $dp -from $cc -to $syv
    set_false_path -hold -from $cc -to $syv
  }
  if {[llength $ld]} {
    set_max_delay -ignore_clock_latency $dm -from $cc -to $ld
    set_false_path -hold -from $cc -to $ld
  }
  set sy [concat $syc $syv]
  puts [format "NATIVE_CDC arcs: %d first synchroniser flops (max datapath %.1f ps, no hold), %d landing flops (max datapath %.1f ps, no hold)" [llength $sy] $dp [llength $ld] $dm]
}
ot_ncdc_arcs
