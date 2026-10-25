# KV-CORES diagnostic: group max-slew violators of a routed core by driving net (fanout, wire cap, worst slew).
# docker: -v BASE:/base:ro -v SDCDIR:/sdc ; env OT_CORNER=TT|FF
set C $::env(OT_CORNER)
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_RVT_${C}_*] { read_liberty $l }
foreach l [glob -nocomplain /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_LVT_${C}_* /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_SLVT_${C}_*] { if {![string match *FAKE* $l]} { read_liberty $l } }
if {[info exists ::env(OT_EXTRA_LIBS)]} { foreach l $::env(OT_EXTRA_LIBS) { read_liberty $l } }
read_db /base/6_final.odb
read_spef /base/6_final.spef
read_sdc /sdc/golden.sdc
set_propagated_clock [all_clocks]
report_check_types -max_slew -violators -max_count 100000 > /tmp/slew.rpt
set f [open /tmp/slew.rpt]; set txt [read $f]; close $f
array set worst {}; array set cnt {}
foreach line [split $txt "\n"] {
  if {[regexp {^(\S+)\s+([0-9.]+)\s+([0-9.]+)\s+(-[0-9.]+) \(VIOLATED\)} $line -> pin lim sl sk]} {
    set p [get_pins -quiet $pin]
    if {![llength $p]} { set p [get_ports -quiet $pin]; set n [get_nets -quiet -of_objects $p] } else { set n [get_nets -quiet -of_objects $p] }
    set nn [expr {[llength $n] ? [get_full_name $n] : "?"}]
    incr cnt($nn)
    if {![info exists worst($nn)] || $sl > $worst($nn)} { set worst($nn) $sl }
  }
}
set blk [ord::get_db_block]
foreach nn [lsort [array names cnt]] {
  set dn [$blk findNet $nn]; set fo "?"; set drv "?"; set len 0
  if {$dn ne "NULL" && $dn ne ""} {
    set fo [expr {[llength [$dn getITerms]] + [llength [$dn getBTerms]] - 1}]
    foreach it [$dn getITerms] { if {[$it isOutputSignal]} { set drv "[[$it getInst] getName]/[[$it getMTerm] getName]([[[$it getInst] getMaster] getName])" } }
    foreach bt [$dn getBTerms] { if {[$bt getIoType] eq "INPUT"} { set drv "PORT:[$bt getName]" } }
  }
  puts "SLEWNET $nn viol=$cnt($nn) worst=$worst($nn) fanout=$fo driver=$drv"
}
puts "SLEWTOTAL [sta::max_slew_violation_count]"
