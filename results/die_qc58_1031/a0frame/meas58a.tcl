# DIE-QC-58A (read-only): clock-pin arrival of the input face registers (ot_face_flops.txt) on the V3 CTS ODB, one corner
set c $::env(CORNER)
foreach f [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*RVT_${c}_nldm_*] { read_liberty $f }
foreach f [glob /work/macros/*_[string tolower $c].lib] { read_liberty $f }
read_db $::env(ODB)
read_sdc $::env(SDC)
source /work/setRC_rcx.tcl
set_propagated_clock [all_clocks]
estimate_parasitics -placement
proc arr {pin} { set p [get_pins $pin]; foreach prop {arrival_max_rise max_rise_arrival} { if {![catch {get_property $p $prop} v]} { return $v } }; return "" }
set ins {}; foreach p [all_inputs] { dict set ins [get_full_name $p] 1 }
set fh [open $::env(FACE) r]; set o [open $::env(OUT) w]
puts $o "inst\tport\tdir_in\tck_arr"
while {[gets $fh l] >= 0} {
  set w [split $l "\t"]; set i [string map {\\ {}} [lindex $w 0]]; set pt [lindex $w 4]
  set pn [regsub {\[.*} $pt {}]
  set isin [expr {[llength [get_ports -quiet $pt]] && [get_property [get_ports $pt] direction] eq "input"}]
  set a ""; catch { set a [arr "$i/CLK"] }
  puts $o "$i\t$pt\t$isin\t$a"
}
close $o
# all register clock pins (body) for the face/body split
set o [open $::env(OUT).allregs w]
foreach r [all_registers -clock_pins] { puts $o "[get_full_name $r]\t[arr [get_full_name $r]]" }
close $o
