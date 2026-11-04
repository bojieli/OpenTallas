# prebuild_gate.sh STA step: TT setup, ideal clocks at the planned insertion latency (GATE_CLK_LAT, the kit's OT_VCLK_TT,
# so IO paths see the same budget as after CTS), placement parasitics from the kit RC (none on the synth fallback).
foreach l $::env(GATE_LIBS) { read_liberty $l }
read_db $::env(GATE_ODB)
read_sdc $::env(GATE_SDC)
set stage $::env(GATE_STAGE)
if {$stage ne "synth_zero_wire"} {
  if {$::env(GATE_RC) ne "" && [file exists $::env(GATE_RC)]} { source $::env(GATE_RC) }
  estimate_parasitics -placement
}
foreach c [all_clocks] {
  if {[llength [get_property $c sources]]} { set_clock_latency $::env(GATE_CLK_LAT) $c }
}
set blk [ord::get_db_block]
set n 0; set nm 0; set a 0.0
foreach i [$blk getInsts] {
  set m [$i getMaster]
  if {[$m getType] eq "BLOCK"} { incr nm } else { incr n; set a [expr {$a + [$m getWidth]*[$m getHeight]}] }
}
set dbu [$blk getDbUnitsPerMicron]
puts "GATE cells $n macros $nm stdcell_area_um2 [format %.1f [expr {$a/$dbu/$dbu}]] stage $stage"
proc worst {tag args} {
  set p [find_timing_paths -path_delay max -group_path_count 1 {*}$args]
  if {[llength $p] == 0} { puts "GATE group $tag none"; return }
  # one path per path group (clock groups, async recovery/removal): take the worst over ALL groups
  set x [lindex $p 0]
  foreach y $p { if {[get_property $y slack] < [get_property $x slack]} { set x $y } }
  puts "GATE group $tag slack [format %.1f [get_property $x slack]] start [get_full_name [get_property $x startpoint]] end [get_full_name [get_property $x endpoint]]"
}
puts "GATE period [get_property [lindex [all_clocks] 0] period]"
worst r2r -from [all_registers -clock_pins] -to [all_registers -data_pins]
worst in2reg -from [all_inputs] -to [all_registers -data_pins]
worst reg2out -from [all_registers -clock_pins] -to [all_outputs]
worst in2out -from [all_inputs] -to [all_outputs]
set over [find_timing_paths -path_delay max -group_path_count 200000 -endpoint_path_count 1 -slack_max 250.0 \
  -from [all_registers -clock_pins] -to [all_registers -data_pins]]
puts "GATE r2r_endpoints_stage_over_583 [llength $over]"
puts "GATE_TOP_BEGIN"
report_checks -path_delay max -group_path_count 25 -endpoint_path_count 1 -format end
puts "GATE_TOP_END"
puts "GATE_WORST_BEGIN"
report_checks -path_delay max -fields {fanout} -digits 1
puts "GATE_WORST_END"
# pin_unreg, same definition as tools/autopilot/geom_rules.py pin_reg_metrics (auto_geom METHODOLOGY 1.9): an input
# bit is registered when a flop (or macro) pin is reachable through BUF/INV only; an output bit when it is driven by a
# flop through BUF/INV only. Clock nets and strap_* ports are exempt.
proc pg_kind {inst} {
  set m [$inst getMaster]
  if {[$m getType] eq "BLOCK"} { return M }
  if {[$m isSequential]} { return S }
  if {[regexp {^(BUF|INV|HB)} [$m getName]]} { return B }
  return L
}
set clknets {}
foreach c [all_clocks] { foreach s [get_property $c sources] { catch { lappend clknets [get_full_name [get_nets -of_objects $s]] } } }
set unreg {}; set nreg 0; set nex 0; set nmac 0
foreach bt [$blk getBTerms] {
  set nm [$bt getName]; set net [$bt getNet]
  if {[$bt getSigType] in {POWER GROUND}} { continue }
  if {$net eq "NULL" || [regexp {^strap_} $nm] || [$net getSigType] eq "CLOCK" || [lsearch -exact $clknets [$net getName]] >= 0} { incr nex; continue }
  set hit ""
  if {[$bt getIoType] eq "OUTPUT"} {
    set cur $net; set seen {}
    while {[lsearch -exact $seen $cur] < 0} {
      lappend seen $cur; set drv ""
      foreach it [$cur getITerms] { if {[$it isOutputSignal]} { set drv $it } }
      if {$drv eq ""} { break }
      set k [pg_kind [$drv getInst]]
      if {$k in {S M}} { set hit $k; break }
      if {$k ne "B"} { break }
      set nx ""
      foreach it [[$drv getInst] getITerms] { if {[$it isInputSignal] && [$it getNet] ne "NULL"} { set nx [$it getNet] } }
      if {$nx eq ""} { break }
      set cur $nx
    }
  } else {
    set front [list $net]; set seen [list [$net getName]]
    while {[llength $front] && $hit eq ""} {
      set nf {}
      foreach n $front {
        foreach it [$n getITerms] {
          if {![$it isInputSignal]} { continue }
          set k [pg_kind [$it getInst]]
          if {$k in {S M}} { set hit $k; break }
          if {$k eq "B"} {
            foreach o [[$it getInst] getITerms] {
              if {[$o isOutputSignal] && [$o getNet] ne "NULL" && [lsearch -exact $seen [[$o getNet] getName]] < 0} {
                lappend seen [[$o getNet] getName]; lappend nf [$o getNet] }
            }
          }
        }
        if {$hit ne ""} { break }
      }
      set front $nf
    }
  }
  if {$hit eq "S"} { incr nreg } elseif {$hit eq "M"} { incr nmac } else { lappend unreg $nm }
}
puts "GATE pin_unreg [llength $unreg] registered $nreg to_macro $nmac exempt $nex"
puts "GATE pin_unreg_list [join $unreg { }]"
