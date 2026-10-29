# MODEL-CORR-1: dump clock paths (port -> endpoint) of a routed design: per path pin the cell master and STA arrivals,
# per path net every pin (for the spice deck).  env: CORNER, ENDPOINTS (space list), OUT
set C $::env(CORNER)
foreach f [glob /tmp/lib_$C/*.lib] { read_liberty $f }
foreach f [glob /work/macros/*_[string tolower $C].lib] { read_liberty $f }
read_db /work/5_1_grt.odb
read_sdc /work/5_1_grt.sdc
read_spef /work/grt.spef
set_propagated_clock [all_clocks]
report_wns
report_worst_slack -min
set fh [open $::env(OUT) w]
proc pinfo {p} {
  set c [get_cells -of_objects $p]
  set m [get_property $c ref_name]
  return "[get_full_name $p] $m [get_property $p direction]"
}
proc arr {p} {
  set o {}
  foreach k {arrival_max_rise arrival_max_fall arrival_min_rise arrival_min_fall slew_max_rise slew_max_fall slew_min_rise slew_min_fall} {
    lappend o [get_property $p $k]
  }
  return $o
}
set eps $::env(ENDPOINTS)
if {[string match "*DRVLOAD:*" $eps]} {
  set n [string range $eps [expr {[string first DRVLOAD: $eps] + 8}] end]
  set y [get_pins $n/Y]
  set net [get_nets -of_objects $y]
  set ld [lindex [get_pins -of_objects $net -filter "direction==input"] 0]
  set eps [string map [list "DRVLOAD:$n" [get_full_name $ld]] $eps]
}
foreach ep $eps {
  puts $fh "PATH $ep"
  set p [get_pins $ep]
  set guard 0
  while {$guard < 200} {
    incr guard
    puts $fh "PIN [pinfo $p] [arr $p]"
    set net [get_nets -of_objects $p]
    puts $fh "NET [get_full_name $net]"
    foreach q [get_pins -of_objects $net] { puts $fh "NPIN [pinfo $q]" }
    foreach q [get_ports -quiet -of_objects $net] { puts $fh "NPORT [get_full_name $q] [get_property $q direction]" }
    set d [get_pins -quiet -of_objects $net -filter "direction==output"]
    if {$d eq ""} { puts $fh "ROOT [get_full_name [get_ports -of_objects $net]]"; break }
    puts $fh "PIN [pinfo $d] [arr $d]"
    set c [get_cells -of_objects $d]
    set a [get_pins -quiet [get_full_name $c]/A]
    if {$a eq ""} { puts $fh "STOP no A pin on [get_full_name $c]"; break }
    set p $a
  }
  puts $fh "END"
}
close $fh
puts DUMP_DONE
