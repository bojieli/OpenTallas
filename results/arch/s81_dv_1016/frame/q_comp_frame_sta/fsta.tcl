# QXPQ-FIX/FSTA (10-18): frame-region STA of the q clock compensation (q_clock_comp_hf1.json).
# env: CORNER (tt|ff) NETDIR (fsta_build.py output) SPEF (0|1) TRUNK (ps, neighbour clock-pin latency) OUT (slack dump)
#      QV QBN QBS SEQ (view dirs)
# 0.833 ns, uncertainty 60 setup / 25 hold (setup judged at TT, hold at FF). The ETM arcs already fold each child's own
# routed insertion (write_timing_model on propagated clocks), so only the frame-level latency is added here.
set c $::env(CORNER)
set nd $::env(NETDIR)
read_liberty $::env(QV)/ot_v41_rom_elem_q_qxpq_w10_${c}.lib
read_liberty $::env(QBN)/dsfd_qbank_N_${c}.lib
read_liberty $::env(QBS)/dsfd_qbank_S_${c}.lib
read_liberty $::env(SEQ)/ot_s81_cfg7_seq_${c}.lib
read_verilog $nd/netlist.v
link_design fsta_top
if {$::env(SPEF)} { read_spef $nd/wire.spef }
# One frame clock on two source ports (fsta_build.py splits the frame clk net): clk_q feeds the q clock pins at the
# region root, clk_n feeds every neighbour clock pin through the shared trunk = per-port source latency TRUNK.
# Propagated mode: OpenSTA then composes port latency + ETM arcs (which fold each child's own routed insertion);
# in ideal mode it would strip each macro's min/max_clock_tree_path from its arcs (ideal = zero insertion), which
# is the wrong model for a boundary-matched compensation check.
create_clock -name clk -period 833 [get_ports {clk_q clk_n}]
set_propagated_clock [all_clocks]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set trunk $::env(TRUNK)
set_clock_latency -source $trunk [get_ports clk_n]
set_clock_latency -source 0 [get_ports clk_q]
puts "FSTA corner $c spef $::env(SPEF) trunk $trunk q_clk_pins [llength [get_pins */clk -filter direction==input]]"
report_checks -path_delay max -format full_clock_expanded -fields {slew cap input_pins} -digits 2
report_checks -path_delay min -format full_clock_expanded -fields {slew cap input_pins} -digits 2
# worst path of each q<->neighbour direction, full clock expansion (proves latency + ETM arc composition)
foreach {nm from to} {
  q_to_qbankN   u_e*  u_bn*
  qbankS_to_q   u_bs* u_e*
  q_to_seq      u_e*  u_s*
  seq_to_q      u_s*  u_e*
  seq_to_qbankS u_s*  u_bs*
} {
  set fp [get_pins -of_objects [get_cells $from] -filter "direction==output"]
  set tp [get_pins -of_objects [get_cells $to] -filter "direction==input"]
  puts "FSTA_GROUP $nm max"
  report_checks -path_delay max -through $fp -to $tp -format full_clock_expanded -digits 2
  puts "FSTA_GROUP $nm min"
  report_checks -path_delay min -through $fp -to $tp -format full_clock_expanded -digits 2
}
# per-endpoint slack dump (every sink pin has exactly one driver pin: fsta_build.py asserts it)
set f [open $::env(OUT) w]
set n 0
foreach p [get_pins -of_objects [get_cells *] -filter "direction==input"] {
  set sm [get_property $p slack_max]
  set sn [get_property $p slack_min]
  if {$sm eq "INF" && $sn eq "INF"} { continue }
  puts $f "[get_full_name $p] $sm $sn"
  incr n
}
close $f
puts "FSTA_DUMP $n endpoints worst_setup [sta::worst_slack_cmd max] worst_hold [sta::worst_slack_cmd min]"
puts "FSTA_DONE"
exit
