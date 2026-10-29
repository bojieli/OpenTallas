# S81-CORE-LAT-R13 core_family_slice census: placed clock sinks (GEO format) from a placed core ODB (from R6 dump_geo_core.tcl).
# env ODB OUT CLK [ENTRY "x y" = plan clock entry, default outline centre (12.8a centre entry)]
read_db $::env(ODB)
set b [ord::get_db_block]; set u [[ord::get_db_tech] getDbUnitsPerMicron]
set f [open $::env(OUT) w]
proc um {v} { return [format %.3f [expr {$v / double($::u)}]] }
set d [$b getDieArea]; puts $f "DIE [um [$d xMin]] [um [$d yMin]] [um [$d xMax]] [um [$d yMax]]"
set c [$b getCoreArea]; puts $f "CORE [um [$c xMin]] [um [$c yMin]] [um [$c xMax]] [um [$c yMax]]"
if {[info exists ::env(ENTRY)] && $::env(ENTRY) ne ""} { lassign $::env(ENTRY) ex ey } else {
  set ex [um [expr {([$d xMin]+[$d xMax])/2}]]; set ey [um [expr {([$d yMin]+[$d yMax])/2}]] }
puts $f "PIN ck $ex $ey"
# R14: the declared clock port may be a 1-bit bus (`input [0:0] clk` -> BTerm clk[0]); resolve it exactly, fail closed
set bt [$b findBTerm $::env(CLK)]
if {$bt eq "NULL"} {
  set b0 [$b findBTerm "$::env(CLK)\[0\]"]; set b1 [$b findBTerm "$::env(CLK)\[1\]"]
  if {$b0 ne "NULL" && $b1 eq "NULL"} { set bt $b0 }
}
if {$bt eq "NULL"} { puts "DUMP_GEO_ERROR clock port $::env(CLK) has no BTerm (nor a 1-bit bus $::env(CLK)\[0\])"; exit 2 }
if {[$bt getNet] eq "NULL"} { puts "DUMP_GEO_ERROR clock BTerm [$bt getName] has no net"; exit 2 }
puts "DUMP_GEO_CLKPORT [$bt getName]"
set net [$bt getNet]; set ns 0; set nm 0; set nb 0; set ng 0
# CORES-EARLY-5 opt-in GATED=1 (form C, ICG copies): an RTL clock gate on the core clock net is written as a GATE line
# (not a SINK) and every sink of its gated domain (GCLK net, through placement buffers/inverters) is written with a
# trailing gate=<ICG inst> field (MACRO lines too). Without GATED the output is unchanged.
set gated [expr {[info exists ::env(GATED)] && $::env(GATED) eq "1"}]
proc geo_walk {f net gate} {
  global ns nm nb ng
  set q [list $net]; set seen {}
  while {[llength $q]} {
    set n [lindex $q 0]; set q [lrange $q 1 end]
    foreach it [$n getITerms] {
      if {$gate ne "" && [$it isOutputSignal]} continue
      set i [$it getInst]; set m [$i getMaster]
      set ib [$it getBBox]; set x [um [expr {([$ib xMin]+[$ib xMax])/2}]]; set y [um [expr {([$ib yMin]+[$ib yMax])/2}]]
      set tag [expr {$gate eq "" ? "" : " gate=$gate"}]
      if {[$m isBlock]} {
        set r [$i getBBox]
        puts $f "MACRO [$i getName] [$m getName] [um [$r xMin]] [um [$r yMin]] [um [$r xMax]] [um [$r yMax]] [[$it getMTerm] getName] $x $y$tag"; incr nm; continue
      }
      if {[[$it getMTerm] getSigType] ne "CLOCK" && ![$it isInputSignal]} continue
      if {[string match {*BUF*} [$m getName]] || [string match {*INV*} [$m getName]]} {
        incr nb
        if {$gate ne ""} { foreach ot [$i getITerms] { if {[$ot isOutputSignal] && [$ot getNet] ne "NULL"} { lappend q [$ot getNet] } } }
        continue
      }
      if {[string match {ICG*} [$m getName]]} {
        if {$gate ne ""} { error "DUMP_GEO_ERROR nested clock gate [$i getName] below $gate" }
        if {$::gated} {
          puts $f "GATE [$i getName] [$m getName] $x $y"; incr ng
          set go "NULL"
          foreach ot [$i getITerms] { if {[$ot isOutputSignal]} { set go [$ot getNet] } }
          if {$go eq "NULL"} { error "DUMP_GEO_ERROR clock gate [$i getName] has no output net" }
          geo_walk $f $go [$i getName]
          continue
        }
      }
      puts $f "SINK $x $y [$m getName] [$i getName] [[$it getMTerm] getName]$tag"; incr ns
    }
    if {$gate eq ""} break
  }
}
geo_walk $f $net ""
puts $f "ISLCOUNT 0"
close $f
puts "DUMP_GEO sinks $ns macros $nm skipped_buf $nb[expr {$gated ? " gates $ng" : ""}]"
exit
