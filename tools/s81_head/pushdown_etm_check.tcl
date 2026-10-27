# HEAD-CORE-LAT-R2 c3' pushdown proof (b) (COORD 06:5x): does the extracted timing model (write_timing_model) keep the
# island ft arcs (ft_ck0/1_i->_o, ft_mesh_i->_o, ft_mstrap_i clock -> ft_rst_o) as arcs a die STA propagates the die
# clock through, with the same TT/FF delays as the flat netlist?  Two phases per corner (env OT_CORNER, ODB, OUT):
#   flat: core 4_cts.odb + placement RC, pushdown SDC, ft ports at a fixed slew/load -> arc delays; then write the ETM.
#   etm : tiny top = ETM cell + top create_clock on each ft clock input + a DFF clocked by each ft clock output ->
#         clock arrival at those DFFs via the ETM; compared with flat.  Results -> $OUT/etm_check_<c>.json
set C $::env(OT_CORNER); set c [string tolower $C]; set OUT $::env(OUT)
set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
set libs [lsort [glob $L/asap7sc7p5t_*_RVT_${C}_nldm_*.lib*]]
set mlibs [glob -nocomplain /work/macros/*_${c}.lib]
set SLEW 20.0; set LOAD 4.0
set ft_comb {{ft_ck0_i ft_ck0_o} {ft_ck1_i ft_ck1_o} {ft_mesh_i ft_mesh_o}}

if {$::env(PHASE) eq "flat"} {
  read_db $::env(ODB)
  foreach f $libs { read_liberty $f }
  foreach f $mlibs { read_liberty $f }
  read_sdc /work/constraint_pd.sdc
  source /work/setRC_rcx.tcl
  estimate_parasitics -placement
  set_propagated_clock [get_clocks clk]
  set ins [get_ports {ft_ck0_i ft_ck1_i ft_mesh_i ft_mstrap_i ft_rst_i}]
  set outs [get_ports {ft_ck0_o ft_ck1_o ft_mesh_o ft_rst_o}]
  set_input_transition $SLEW $ins
  set_load $LOAD $outs
  set res {}
  foreach pr $ft_comb {
    lassign $pr a z
    set p [find_timing_paths -unconstrained -from [get_ports $a] -to [get_ports $z] -path_delay max]
    set pts [get_property $p points]; set d [expr {[get_property [lindex $pts end] arrival] - [get_property [lindex $pts 0] arrival]}]
    lappend res [format "\"%s->%s\": %.2f" $a $z $d]
  }
  # clock source -> pin-register insertion (the 12.3 core latency) and clock -> ft_rst_o (reset hop)
  set p [find_timing_paths -unconstrained -from [get_ports ft_mstrap_i] -to [get_ports ft_rst_o] -path_delay max]
  if {$p ne ""} { lappend res [format "\"ft_mstrap_i->ft_rst_o(clk2q)\": %.2f" [expr {[get_property [lindex [get_property $p points] end] arrival] - [get_property [lindex [get_property $p points] 0] arrival]}]] }
  set fh [open $OUT/etm_flat_${c}.json w]; puts $fh "{[join $res {, }]}"; close $fh
  puts "ETM_FLAT $C {[join $res {, }]}"
  write_timing_model -library_name ot_s81hd_elemA_pd_${c} $OUT/ot_s81hd_elemA_pd_${c}.lib
  puts "ETM_WRITTEN $OUT/ot_s81hd_elemA_pd_${c}.lib"
  if {$c eq "tt"} { write_abstract_lef -bloat_occupied_layers $OUT/core_pd.lef; puts "ABSTRACT_WRITTEN $OUT/core_pd.lef" }
} else {
  foreach f $libs { read_liberty $f }
  read_liberty $OUT/ot_s81hd_elemA_pd_${c}.lib
  set cell [get_name [lindex [get_lib_cells ot_s81hd_elemA_pd_${c}/*] 0]]
  set fh [open $OUT/etm_top.v w]
  puts $fh "module etm_top(input k0, input k1, input km, input ks, input r, input d, output o);"
  puts $fh "  wire w0, w1, wm, wr; wire q0, q1, qm;"
  puts $fh "  $cell u_core(.ft_ck0_i(k0), .ft_ck1_i(k1), .ft_mesh_i(km), .ft_mstrap_i(ks), .ft_rst_i(r), .ft_ck0_o(w0), .ft_ck1_o(w1), .ft_mesh_o(wm), .ft_rst_o(wr));"
  puts $fh "  DFFHQNx1_ASAP7_75t_R f0(.CLK(w0), .D(d), .QN(q0));"
  puts $fh "  DFFHQNx1_ASAP7_75t_R f1(.CLK(w1), .D(q0), .QN(q1));"
  puts $fh "  DFFHQNx1_ASAP7_75t_R fm(.CLK(wm), .D(q1), .QN(qm));"
  puts $fh "  assign o = qm;"
  puts $fh "endmodule"
  close $fh
  read_verilog $OUT/etm_top.v
  link_design etm_top
  create_clock -name k0 -period 833 [get_ports k0]
  create_clock -name k1 -period 833 [get_ports k1]
  create_clock -name km -period 833 [get_ports km]
  create_clock -name ks -period 833 [get_ports ks]
  set_propagated_clock [all_clocks]
  set_input_transition $SLEW [get_ports {k0 k1 km ks r}]
  foreach n {w0 w1 wm} { set_load [expr {$LOAD - [get_property [get_lib_pins */DFFHQNx1_ASAP7_75t_R/CLK] capacitance]}] [get_nets $n] }
  set res {}
  foreach {f pin} {f0 CLK f1 CLK fm CLK} {
    set a [get_property [get_pins $f/$pin] arrival_max_rise]
    lappend res [format "\"%s/%s\": %s" $f $pin [expr {$a eq "" ? "null" : [format %.2f $a]}]]
  }
  # does the ETM carry a clock-to-output arc ks -> ft_rst_o ?
  set p [find_timing_paths -unconstrained -through [get_pins u_core/ft_rst_o] -path_delay max]
  lappend res [format "\"rst_o_path\": %s" [expr {$p eq "" ? "false" : "true"}]]
  set fh [open $OUT/etm_top_${c}.json w]; puts $fh "{[join $res {, }]}"; close $fh
  puts "ETM_TOP $C {[join $res {, }]}"
}
