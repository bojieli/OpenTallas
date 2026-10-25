# PATH-S81/ENG3 zero-wire TT estimate on a synth netlist: worst paths FROMPAT flops -> TOPAT flops (regexp on cell names)
set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach f [lsort [glob $L/asap7sc7p5t_*_RVT_TT_nldm_*.lib*]] { read_liberty $f }
foreach f [glob -nocomplain /k/macros/*_tt.lib] { read_liberty $f }
read_verilog $::env(NET)
link_design dsdv_eng_rr_e
read_sdc /k/constraint.sdc
foreach {tag fp tp} $::env(PAIRS) {
  set fr {}; set to {}
  foreach c [all_registers -cells] { set n [get_full_name $c]
    if {[regexp $fp $n]} { lappend fr [get_pins $n/CLK] }
    if {[regexp $tp $n]} { lappend to [get_pins $n/D] } }
  puts "== $tag from [llength $fr] to [llength $to]"
  if {[llength $fr] == 0 || [llength $to] == 0} continue
  set sl {}
  foreach p [find_timing_paths -path_delay max -from $fr -to $to -group_path_count 5000 -endpoint_path_count 1] { lappend sl [get_property $p slack] }
  set sl [lsort -real $sl]
  puts "SLACK $tag n=[llength $sl] worst=[format %.1f [lindex $sl 0]] median=[format %.1f [lindex $sl [expr {[llength $sl]/2}]]]"
  report_checks -path_delay max -from $fr -to $to -fields {fanout} -digits 1
}
