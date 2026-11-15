# S81-SEAM-RST-1115 form pg (opt-in OT_TAP_RESET_AFFINITY=1): the LAST reset stage of an async clear (any DFF whose Q/QN reaches,
# through inverters/buffers, asynchronous RESETN/SETN pins) takes the clock tap its sinks use.  Launch and capture then share
# one insertion delay (the 283 ps tap-to-tap difference that makes removal fail disappears for that edge).  Clock pin only:
# no data/reset/cell change.  Sourced from clock_taps.tcl after the other affinity passes; sinks' taps are already final.
namespace eval ::ot_tap_rst {
 proc fwd {net depth} {
  # async sink iterms reachable from net through INV*/BUF*/CKINV* cells, plus the count of other loads
  set async {}; set other 0
  foreach it [$net getITerms] {
   if {![$it isInputSignal]} continue
   set inst [$it getInst]; set m [$inst getMaster]; set mn [$m getName]; set pin [[$it getMTerm] getName]
   if {[$m isBlock]} {incr other; continue}
   if {[string match DFF* $mn] && ($pin eq "RESETN" || $pin eq "SETN")} {lappend async $it; continue}
   if {$depth < 4 && ([string match INV* $mn] || [string match BUF* $mn] || [string match CKINV* $mn] || [string match HB* $mn])} {
    foreach o [$inst getITerms] {
     if {[$o isOutputSignal] && [$o getNet] ne "NULL"} {
      lassign [fwd [$o getNet] [expr {$depth+1}]] a b
      set async [concat $async $a]; incr other $b
     }
    }
    continue
   }
   incr other
  }
  return [list $async $other]
 }
 proc run {} {
  global ct_taps
  set blk [ord::get_db_block]
  set dbu [expr {double([[ord::get_db_tech] getDbUnitsPerMicron])}]
  set tapnets {}
  foreach tp $ct_taps {dict set tapnets [[lindex $tp 1] getName] [lindex $tp 0]}
  set moved 0; set cand 0; set same 0; set maxd 0.0
  foreach inst [$blk getInsts] {
   set m [$inst getMaster]
   if {[$m isBlock] || ![string match DFF* [$m getName]]} continue
   set clk {}
   foreach it [$inst getITerms] {if {[[$it getMTerm] getName] in {CLK CLKN}} {set clk $it}}
   if {$clk eq {} || [$clk getNet] eq "NULL" || ![dict exists $tapnets [[$clk getNet] getName]]} continue
   set async {}; set other 0
   foreach it [$inst getITerms] {
    if {[$it isOutputSignal] && [$it getNet] ne "NULL"} {
     lassign [fwd [$it getNet] 0] a b; set async [concat $async $a]; incr other $b
    }
   }
   if {[llength $async] < 2 || [llength $async] < $other} continue
   incr cand
   set cnt {}
   foreach a $async {
    set ck {}
    foreach it [[$a getInst] getITerms] {if {[[$it getMTerm] getName] in {CLK CLKN}} {set ck $it}}
    if {$ck eq {} || [$ck getNet] eq "NULL"} continue
    set nn [[$ck getNet] getName]
    if {[dict exists $tapnets $nn]} {dict incr cnt $nn}
   }
   if {[dict size $cnt] == 0} continue
   set best {}; set bn -1
   dict for {k v} $cnt {if {$v > $bn || ($v == $bn && [string compare $k $best] < 0)} {set best $k; set bn $v}}
   if {$best eq [[$clk getNet] getName]} {incr same; continue}
   set dst [$blk findNet $best]
   $clk disconnect; $clk connect $dst; incr moved
  }
  puts "OT_TAP_RESET candidates $cand moved $moved already_on_sink_tap $same"
 }
}
::ot_tap_rst::run
