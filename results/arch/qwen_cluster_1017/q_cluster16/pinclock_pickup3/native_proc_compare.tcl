read_db routes/gate/work/orfs/results/asap7/opentallas_qfd_c_b16_reg1_asap7_ref_gate/base/3_place.odb
  proc ot_qc_pinreg_cks {bus dir} {
    set out {}; set seen [dict create]
    set pl [get_ports -quiet [format {%s[*]} $bus]]
    if {![llength $pl]} { set pl [get_ports -quiet $bus] }
    foreach port $pl {
      set nets [get_nets -quiet [get_full_name $port]]
      for {set hop 0} {$hop < 4 && [llength $nets]} {incr hop} {
        set next {}
        foreach n $nets {
          foreach pin [get_pins -quiet -of_objects $n] {
            if {[string first / [get_full_name $pin]] < 0} { continue }
            set pd [get_property $pin direction]
            if {($dir eq "in" && $pd ne "input") || ($dir eq "out" && $pd ne "output")} { continue }
            set c [get_cells -quiet -of_objects $pin]
            if {![llength $c]} { continue }
            set fn [get_full_name $c]
            set ck [get_pins -quiet "$fn/ck"]
            if {![llength $ck]} { set ck [get_pins -quiet "$fn/CLK"] }
            if {[llength $ck]} {
              if {![dict exists $seen $fn]} { dict set seen $fn 1; lappend out $ck }
            } elseif {[regexp {^(BUF|HB|INV)} [get_property $c ref_name]]} {
              foreach op [get_pins -quiet -of_objects $c] {
                set od [get_property $op direction]
                if {($dir eq "in" && $od eq "output") || ($dir eq "out" && $od eq "input")} { lappend next [get_nets -quiet -of_objects $op] }
              }
            }
          }
        }
        set nets $next
      }
    }
    return $out
  }
rename ot_qc_pinreg_cks ot_qc_pinreg_cks_old
  proc ot_qc_pinreg_cks {bus dir} {
    set out {}; set seen [dict create]
    set pl [get_ports -quiet [format {%s[*]} $bus]]
    if {![llength $pl]} { set pl [get_ports -quiet $bus] }
    foreach port $pl {
      set nets [get_nets -quiet [get_full_name $port]]
      set visited_nets [dict create]
      while {[llength $nets]} {
        set next {}
        foreach n $nets {
          set nn [get_full_name $n]
          if {[dict exists $visited_nets $nn]} { continue }
          dict set visited_nets $nn 1
          foreach pin [get_pins -quiet -of_objects $n] {
            if {[string first / [get_full_name $pin]] < 0} { continue }
            set pd [get_property $pin direction]
            if {($dir eq "in" && $pd ne "input") || ($dir eq "out" && $pd ne "output")} { continue }
            set c [get_cells -quiet -of_objects $pin]
            if {![llength $c]} { continue }
            set fn [get_full_name $c]
            set ck [get_pins -quiet "$fn/ck"]
            if {![llength $ck]} { set ck [get_pins -quiet "$fn/CLK"] }
            if {[llength $ck]} {
              if {![dict exists $seen $fn]} { dict set seen $fn 1; lappend out $ck }
            } elseif {[regexp {^(BUF|HB|INV)} [get_property $c ref_name]]} {
              foreach op [get_pins -quiet -of_objects $c] {
                set od [get_property $op direction]
                if {($dir eq "in" && $od eq "output") || ($dir eq "out" && $od eq "input")} { lappend next [get_nets -quiet -of_objects $op] }
              }
            }
          }
        }
        set nets $next
      }
    }
    return $out
  }
foreach p {lrst_dn1_rly3_w lrst_dn1_rly6_r} {
 set old [ot_qc_pinreg_cks_old $p in]; set new [ot_qc_pinreg_cks $p in]
 if {[llength $old] != 0 || [llength $new] != 2} { error "PINCLK_REGRESSION $p" }
 puts "NATIVE_PINCLOCK $p OLD_N=[llength $old] NEW_N=[llength $new] CLOCKS=[get_full_name $new]"
}
set old [ot_qc_pinreg_cks_old {la_i[0]} in]; set new [ot_qc_pinreg_cks {la_i[0]} in]
if {[lsort $old] ne [lsort $new] || [llength $new]!=1} { error "PINCLK_DATA_CHANGED" }
puts "NATIVE_DATA_UNCHANGED [get_full_name $new]"
if {[llength [ot_qc_pinreg_cks deliberately_absent in]] != 0} { error "ABSENT_PIN_WAIVED" }
puts "CB16_PINCLOCK_TRANSPARENT_PASS"
exit
