source /OpenROAD-flow-scripts/flow/platforms/asap7/liberty_suppressions.tcl
set tt {}; set ff {}
set fh [open /out/libs.txt]; foreach l [split [read $fh] \n] { if {$l eq ""} continue; read_liberty $l
  if {[regexp {_TT_|_tt\.lib} $l]} {lappend tt $l} else {lappend ff $l} }; close $fh
read_db /work/diag_check_2.odb
read_sdc -mode ss /work/diag_check_2.sdc
read_sdc -mode ff /work/diag_check_2.sdc
define_scene WC -mode ss -liberty $tt
define_scene BC -mode ff -liberty $ff
set_mode ss
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
estimate_parasitics -placement
proc rp {name args} { if {[catch {report_checks {*}$args -format full_clock_expanded -fields {slew cap input_pin net fanout} -digits 2 > /out/$name.rpt} why]} { set f [open /out/$name.rpt w]; puts $f "REPORT_ERROR $why"; close $f } }
# 1 raw clock net loads
set f [open /out/clk_net_loads.txt w]
foreach p [get_pins -of_objects [get_nets clk]] { puts $f "[get_full_name $p] [get_property [get_cells -of_objects $p] ref_name]" }
close $f
set icg u.u_cgt.u_cg.u_icg
foreach pn {ENA SE CLK GCLK} { set p [get_pins -quiet $icg/$pn]; puts "ICGPIN $pn [llength $p]" }
rp icg_ena_WC_max -corner WC -path_delay max -to [get_pins $icg/ENA] -group_path_count 3
rp icg_ena_BC_min -corner BC -path_delay min -to [get_pins $icg/ENA] -group_path_count 3
rp cgi_from_WC_max -corner WC -path_delay max -from [get_ports cgi] -group_path_count 3
rp cgi_from_BC_min -corner BC -path_delay min -from [get_ports cgi] -group_path_count 3
rp cgo_to_WC_max -corner WC -path_delay max -to [get_ports cgo] -group_path_count 2
rp cgo_to_BC_min -corner BC -path_delay min -to [get_ports cgo] -group_path_count 2
rp cgoflop_D_WC_max -corner WC -path_delay max -to [get_pins {u.u_cgt.cgo$_DFF_PN1_/D}] -group_path_count 2
rp cgoflop_D_BC_min -corner BC -path_delay min -to [get_pins {u.u_cgt.cgo$_DFF_PN1_/D}] -group_path_count 2
rp worst_WC_max -corner WC -path_delay max -group_path_count 3
rp worst_BC_min -corner BC -path_delay min -group_path_count 3
report_checks -corner WC -path_delay max -format end -group_path_count 20000 -slack_max 0 > /out/end_WC_max.txt
report_checks -corner BC -path_delay min -format end -group_path_count 20000 -slack_max 0 > /out/end_BC_min.txt
# 2 clock arrivals at every register/macro clock pin, both scenes
set f [open /out/clk_arrivals.txt w]
foreach p [all_registers -clock_pins] {
  set n [get_full_name $p]
  set row $n
  foreach sc {WC BC} {
    sta::redirect_string_begin; catch {report_arrival -scene $sc -digits 2 $p}; set r [sta::redirect_string_end]
    set v NA; regexp {\sr\s+(\S+):(\S+)} $r -> lo v
    lappend row $v
  }
  lappend row [get_property [get_cells -of_objects $p] ref_name]
  puts $f $row
}
close $f
report_clock_skew -setup > /out/clock_skew.txt
puts DIAG_DONE
exit
