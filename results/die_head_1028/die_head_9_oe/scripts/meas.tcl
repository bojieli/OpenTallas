# DIE-HEAD-9 one-entry CTS diagnostic: clock arrivals at flop CK pins and hard-core clock pins (+ SIGNED internal mean)
foreach l $::env(LIBS) { read_liberty $l }
read_db $::env(ODB)
read_sdc $::env(SDC)
set_propagated_clock [all_clocks]
source $::env(RCF)
estimate_parasitics -placement
set c $::env(CORNER)
array set mean {}
set fh [open $::env(CORE_LAT)]; while {[gets $fh l] >= 0} { if {[string match #* $l]} continue; lassign $l i p ps; set mean($i/$p) $ps }; close $fh
set out [open $::env(OUT) w]
foreach k [array names mean] {
  set pin [get_pins $k]
  set a [get_property $pin arrival_max_rise]; set b [get_property $pin arrival_min_rise]
  puts $out "CORE $k $a $b $mean($k)"
}
set n 0
foreach p [all_registers -clock_pins] {
  set inst [get_property $p full_name]
  set a [get_property $p arrival_max_rise]; set b [get_property $p arrival_min_rise]
  if {$a eq "" || [string match *INF* $a]} continue
  puts $out "CK $inst $a $b"; incr n
}
close $out
puts "MEAS $c clock pins $n"
