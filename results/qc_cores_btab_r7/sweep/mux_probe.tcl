read_db /work/run/results/asap7/kq_qfd_dv_s8x_btab_mif0r5/base/3_place.odb
set b [ord::get_db_block]; set u [$b getDbUnitsPerMicron]
# bank of each macro-pin flop: nearest SRAM by y
set banks {}
foreach i [$b getInsts] { if {[[$i getMaster] isBlock]} { set bb [$i getBBox]; lappend banks [list [$i getName] [$bb yMin] [$bb yMax]] } }
proc bankof {y} { global banks; set best ""; set bd 1e18; foreach t $banks { lassign $t n lo hi; set c [expr {($lo+$hi)/2.0}]; if {abs($y-$c)<$bd} {set bd [expr {abs($y-$c)}]; set best $n} }; return $best }
set f [open /work/run/results/asap7/kq_qfd_dv_s8x_btab_mif0r5/base/ot_macro_pin_flops.txt]; set mpf [dict create]
foreach n [split [read $f] "\n"] { if {$n eq ""} continue; set i [$b findInst $n]; if {$i eq "NULL"} continue; dict set mpf $n [bankof [lindex [$i getLocation] 1]] }
close $f
set f [open /work/run/results/asap7/kq_qfd_dv_s8x_btab_mif0r5/base/r5_e_logic.txt]; set mem [split [string trim [read $f]] "\n"]; close $f
set o [open /p/mux_probe.tsv w]
puts $o "inst\tmaster\tx\ty\tin_banks\tin_flop_y\tout_sinks\tout_x\tout_y"
foreach n $mem {
  set i [$b findInst $n]; set loc [$i getLocation]
  set bks {}; set fys {}; set ox {}; set oy {}; set ons {}
  foreach it [$i getITerms] {
    set net [$it getNet]; if {$net eq "NULL"} continue
    if {[$it isInputSignal]} {
      # trace back <=3 hops through INV/BUF
      set cur $net
      for {set h 0} {$h < 4} {incr h} {
        set drv ""
        foreach jt [$cur getITerms] { if {[$jt isOutputSignal]} { set drv [$jt getInst] } }
        if {$drv eq ""} break
        if {[dict exists $mpf [$drv getName]]} { lappend bks [dict get $mpf [$drv getName]]; lappend fys [format %.1f [expr {[lindex [$drv getLocation] 1]/double($u)}]]; break }
        if {![regexp {^(INV|BUF|HB)} [[$drv getMaster] getName]]} { lappend bks "c:[[$drv getMaster] getName]"; break }
        set nxt ""; foreach jt [$drv getITerms] { if {[$jt isInputSignal] && [$jt getNet] ne "NULL"} { set nxt [$jt getNet] } }
        if {$nxt eq ""} break; set cur $nxt
      }
    } elseif {[$it isOutputSignal]} {
      foreach jt [$net getITerms] { if {[$jt isInputSignal]} { set j [$jt getInst]; lappend ons "[[$j getMaster] getName]"; lappend ox [format %.1f [expr {[lindex [$j getLocation] 0]/double($u)}]]; lappend oy [format %.1f [expr {[lindex [$j getLocation] 1]/double($u)}]] } }
      foreach bt [$net getBTerms] { lappend ons "PORT:[$bt getName]" }
    }
  }
  puts $o "$n\t[[$i getMaster] getName]\t[format %.2f [expr {[lindex $loc 0]/double($u)}]]\t[format %.2f [expr {[lindex $loc 1]/double($u)}]]\t[join $bks ,]\t[join $fys ,]\t[join $ons ,]\t[join $ox ,]\t[join $oy ,]"
}
close $o
puts DONE
