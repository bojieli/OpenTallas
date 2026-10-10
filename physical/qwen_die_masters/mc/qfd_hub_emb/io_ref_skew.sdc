# die-context boundary per domain, referenced to the propagated arrival L at a register of that domain's tree:
# 0.2 T outside + 150 ps (die wire to another region; 90 ps for the --intra domains), hold allowance 50 ps
# PINFLOP-REF (drive-0849 2026-10-10, coordinator class-1 fix: 39 hold floods at CTS/GRT): the IO reference register used
# to be the FIRST register of the design / clock (an arbitrary tree position), so the input min delay sat far from the
# capture flops' clock and CTS / GRT hold repair flooded (ehash / core18 / kvwq closed only after naming the input pin
# flops by hand).  When the block has a REGISTERED input boundary -- input ports reaching register D pins directly or
# through <= 2 buffers ("pin flops") -- the reference is the pin flop of MEDIAN clock arrival.  No pin flops -> the
# previous reference.  An explicit matching OT_REF_GLOB keeps priority; OT_REF_PINFLOP=0 opts out.
proc ot_pf_clks {ports} {
  set seen [dict create]; set out {}
  foreach port $ports {
    set nets [get_nets -quiet [get_full_name $port]]
    for {set hop 0} {$hop < 3 && [llength $nets]} {incr hop} {
      set next {}
      foreach n $nets {
        foreach pin [get_pins -quiet -of_objects $n] {
          if {[string first / [get_full_name $pin]] < 0} { continue }
          if {[get_property $pin direction] ne "input"} { continue }
          set c [get_cells -quiet -of_objects $pin]
          if {![llength $c]} { continue }
          set fn [get_full_name $c]
          set ck [get_pins -quiet "$fn/CLK"]
          if {[llength $ck]} {
            if {[get_property $pin lib_pin_name] ne "CLK" && ![dict exists $seen $fn]} { dict set seen $fn 1; lappend out $ck }
          } elseif {[regexp {^(BUF|HB)} [get_property $c ref_name]]} {
            foreach op [get_pins -quiet -of_objects $c] {
              if {[get_property $op direction] eq "output"} { lappend next [get_nets -quiet -of_objects $op] }
            }
          }
        }
      }
      set nets $next
    }
  }
  return $out
}
proc ot_pf_ref {ports} {
  if {[info exists ::env(OT_REF_PINFLOP)] && $::env(OT_REF_PINFLOP) eq "0"} { return {} }
  catch {sta::worst_slack_cmd max}   ;# arrivals need an updated timing graph (as the QDM reference reads below)
  set pf {}
  foreach p [ot_pf_clks $ports] {
    set a [get_property $p arrival_max_rise]
    if {[string is double -strict $a]} { lappend pf [list $a $p] }
  }
  if {![llength $pf]} { return {} }
  set pf [lsort -real -index 0 $pf]
  set m [lindex $pf [expr {[llength $pf] / 2}]]
  puts "QDM PINFLOP reference: [llength $pf] input pin flops, median arrival [lindex $m 0] (range [lindex [lindex $pf 0] 0] .. [lindex [lindex $pf end] 0])"
  return [lindex $m 1]
}
set ot_hk [expr {[info exists ::env(OT_IO_HOLD_SKEW)] ? $::env(OT_IO_HOLD_SKEW) : 50}]
sta::worst_slack_cmd max
unset_input_delay [all_inputs]
unset_output_delay [all_outputs]
foreach {clk sk ins outs} {
  ck 150 {x3_v x3_d[*] x3_tag[*] ar_cr ea_v ea_kind ea_addr[*]} {l0_o[*] l1_o[*] l2_o[*] l3_o[*] x3_cr ar_v ar_d[*] fault fault_cause[*] ea_cr eq_v eq_d[*] emb_ready emb_fault emb_fault_code[*]}
  fck0 150 {l0_i[*]} {}
  fck1 150 {l1_i[*]} {}
  fck2 150 {l2_i[*]} {}
  fck3 150 {l3_i[*]} {}
} {
  set ref {}
  if {[llength $ins]} { set ref [ot_pf_ref [get_ports $ins]] }
  if {![llength $ref]} { set ref [lindex [all_registers -clock $clk -clock_pins] 0] }
  set lmax [get_property $ref arrival_max_rise]; set lmin [get_property $ref arrival_min_rise]
  set T [get_property [get_clocks $clk] period]
  puts "QDM $clk ref [get_full_name $ref] L max $lmax min $lmin skew $sk"
  if {[llength $ins]} {
    set_input_delay  [expr {0.2*$T + $lmax + $sk}] -max -clock $clk [get_ports $ins]
    set_input_delay  [expr {$lmin - ([info exists ::env(OT_IO_IN_HOLD_SKEW)] ? $::env(OT_IO_IN_HOLD_SKEW) : 0)}]       -min -clock $clk [get_ports $ins] }
  if {[llength $outs]} {
    set_output_delay [expr {0.2*$T - $lmax + $sk}] -max -clock $clk [get_ports $outs]
    set_output_delay [expr {-$lmin - $ot_hk}]      -min -clock $clk [get_ports $outs] }
}
set_false_path -from [get_ports {rst_n}]
