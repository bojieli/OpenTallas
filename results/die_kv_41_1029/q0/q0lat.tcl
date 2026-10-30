# DIE-KV-41 q0 routed clock latency probe (TT, 6_final spef). Output: per-FF CLK arrival + xy + leaf driver.
foreach f [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_TT_nldm*.lib*] { read_liberty $f }
foreach f [glob -nocomplain /k/macros/*_tt.lib] { read_liberty $f }
read_db /r/6_final.odb
read_sdc /r/6_final.sdc
read_spef /r/6_final.spef
report_worst_slack -max
report_worst_slack -min
set fh [open /o/q0v3_lat_TT.txt w]
foreach p [get_pins -hierarchical */CLK] {
  set n [get_nets -of_objects $p]
  set d [get_pins -of_objects $n -filter "direction==output"]
  set dn [expr {[llength $d] ? [get_full_name [lindex $d 0]] : "port"}]
  puts $fh "[get_full_name $p] [get_property $p arrival_max_rise] $dn"
}
close $fh
puts OT_DONE
