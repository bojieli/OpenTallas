# KIT-OPS-6 11-14 (COORD, FABLE-TYPES-S81-LEAF section 1 step 2): the clock tap port pairs of one kit that CARRY DATA, for
# die_sta_related --kit-window-related.  Run in OpenROAD on the bound (pre-CTS or placed) kit database:
#   OT_KTP_TYPE=<type> OT_KTP_OUT=<json> [OT_KTP_DEPTH=8] openroad -exit -no_init kit_tap_related_pairs.tcl
# A pair (p, q) is listed when a register (or hard-core pin) clocked from tap port p reaches the D of one clocked from q through at
# most OT_KTP_DEPTH combinational cells (nets above 512 loads are skipped as clock/reset trees).  Same-port pairs are not listed
# (OpenSTA CRPR credits them).  No netlist or timing change; read-only.
set blk [ord::get_db_block]
set depth [expr {[info exists ::env(OT_KTP_DEPTH)] ? $::env(OT_KTP_DEPTH) : 8}]
set tp [expr {[info exists ::env(OT_KTP_TYPE)] ? $::env(OT_KTP_TYPE) : [$blk getName]}]
# clock tap port of an instance: the port whose net feeds a clock pin of the instance
proc ktp_port {inst} {
 foreach it [$inst getITerms] {
  if {![$it isInputSignal]} continue
  set n [$it getNet]; if {$n eq "NULL"} continue
  set mt [[$it getMTerm] getName]
  if {$mt ni {CLK CLKN} && ![string match {*clk*} [string tolower $mt]] && ![string match {*ck*} [string tolower $mt]]} continue
  foreach bt [$n getBTerms] { return [$bt getName] }
 }
 return ""
}
set port {}
foreach i [$blk getInsts] {
 set m [$i getMaster]
 if {[$m isBlock] || [$m isSequential]} { set p [ktp_port $i]; if {$p ne ""} { dict set port [$i getName] $p } }
}
set pairs [dict create]
dict for {iname p} $port {
 set inst [$blk findInst $iname]
 set front {}
 foreach o [$inst getITerms] { if {[$o isOutputSignal] && [$o getNet] ne "NULL"} { lappend front [$o getNet] } }
 set seen [dict create]
 for {set d 0} {$d <= $depth && [llength $front]} {incr d} {
  set next {}
  foreach net $front {
   if {[dict exists $seen [$net getName]]} continue
   dict set seen [$net getName] 1
   if {[llength [$net getITerms]] > 512} continue
   foreach s [$net getITerms] {
    if {![$s isInputSignal]} continue
    set si [$s getInst]; set sm [$si getMaster]
    if {[$sm isBlock] || [$sm isSequential]} {
     set q [expr {[dict exists $port [$si getName]] ? [dict get $port [$si getName]] : ""}]
     if {$q ne "" && $q ne $p} { dict set pairs [lsort [list $p $q]] 1 }
     continue
    }
    foreach o [$si getITerms] { if {[$o isOutputSignal] && [$o getNet] ne "NULL"} { lappend next [$o getNet] } }
   }
  }
  set front $next
 }
}
set rows {}
dict for {k v} $pairs { lappend rows "\[\"[lindex $k 0]\", \"[lindex $k 1]\"\]" }
set fh [open $::env(OT_KTP_OUT) w]
puts $fh "{\"related_pairs\": {\"$tp\": \[[join [lsort $rows] {, }]\]}}"
close $fh
puts "OT_KTP $tp: [dict size $pairs] data-related tap port pairs of [dict size $port] clocked instances (depth $depth) -> $::env(OT_KTP_OUT)"
