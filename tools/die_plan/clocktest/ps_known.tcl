# KIT-OPS-6 lever 7: known-answer design for pair_skew.tcl: launch flop on tap n0, capture flop two buffers later (n1).
# The related-pair raw skew of (ff_l -> ff_c) must equal the measured CK arrival difference n1 - n0 (self-consistent, no magic number).
set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [glob $P/lef/asap7_tech_1x_201209.lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef] { read_lef $f }
foreach f [glob $P/lib/NLDM/asap7sc7p5t_*_RVT_FF_nldm_*.lib*] { read_liberty $f }
read_verilog /ct/ps_known.v
link_design ps_known
initialize_floorplan -die_area "0 0 40 40" -core_area "2 2 38 38" -site asap7sc7p5t
set blk [ord::get_db_block]; set x 3.0
foreach i [$blk getInsts] { $i setLocation [expr {int($x*1000)}] [expr {int((3.0 + 0.27*[incr n 2])*1000)}]; $i setPlacementStatus PLACED; set x [expr {$x + 3.0}] }
create_clock -name clk -period 833 [get_ports clk]
set_input_delay 0 -clock clk [get_ports d]
source $P/setRC.tcl
estimate_parasitics -placement
set_propagated_clock [all_clocks]
source /common/clock_family.tcl
set ::ot_ps_lib_only 1
source /tools/pair_skew.tcl
unset ::ot_ps_lib_only
ot_ps_zero_unc
set ::ot_ps_method tag
sta::worst_slack_cmd max
sta::worst_slack_cmd min
set R [ot_ps_regs]
lassign [ot_ps_related $R] pairs np nx nd
puts "PS_COUNTS regs=[dict size $R] pairs=$np inter=$nx data=$nd noarr=$::ot_ps_noarr"
dict for {k row} $pairs { puts "PS_PAIR [join $row { }]" }
set a0 [get_property [get_pins ff_l/CLK] arrival_max_rise]
set a1 [get_property [get_pins ff_c/CLK] arrival_max_rise]
puts "PS_ARR launch $a0 capture $a1 diff [expr {$a1-$a0}]"
puts "PS_DONE"
exit
