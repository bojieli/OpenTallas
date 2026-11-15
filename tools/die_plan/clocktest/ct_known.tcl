# KIT-OPS-6 lever 7: known-answer design for clock_taps.tcl (grid taps + an EARLY core tap).  Tap ports clk (x=3), clk_t1 (x=37), core tap clk_c0.
# All four flops start on clk.  fa, fb sit near clk; fc near clk_t1; fcore is the "hard core" whose clock pin is hung on clk_c0 (OT_CORE_TAPS).
# Expected: fcore/CLK -> clk_c0's net; fc moves to clk_t1's net (nearest tap); fa, fb stay on clk; log "core tap clk_c0 <- fcore/CLK: 1 clock pin(s)".
set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [glob $P/lef/asap7_tech_1x_201209.lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef] { read_lef $f }
foreach f [glob $P/lib/NLDM/asap7sc7p5t_*_RVT_FF_nldm_*.lib*] { read_liberty $f }
read_verilog /ct/ct_known.v
link_design ct_known
initialize_floorplan -die_area "0 0 40 40" -core_area "2 2 38 38" -site asap7sc7p5t
set blk [ord::get_db_block]
set tech [ord::get_db_tech]
proc ct_pin {blk tech name x y} {
  set bt [$blk findBTerm $name]; set bp [odb::dbBPin_create $bt]
  odb::dbBox_create $bp [$tech findLayer M5] [expr {int($x*1000)}] [expr {int($y*1000)}] [expr {int($x*1000)+100}] [expr {int($y*1000)+100}]
  $bp setPlacementStatus PLACED
}
ct_pin $blk $tech clk 3 20
ct_pin $blk $tech clk_t1 37 20
ct_pin $blk $tech clk_c0 20 38
foreach {n x y} {fa 5 10 fb 6 12 fcore 20 20 fc 34 10} { set i [$blk findInst $n]; $i setLocation [expr {int($x*1000)}] [expr {int($y*1000)}]; $i setPlacementStatus PLACED }
set fh [open /tmp/core_taps.txt w]; puts $fh "clk_c0 fcore CLK 100 120"; close $fh
set ::env(OT_CORE_TAPS) /tmp/core_taps.txt
source /tools/clock_taps.tcl
foreach n {fa fb fc fcore} { puts "CT_NET $n [[[$blk findInst $n] findITerm CLK] getNet] [[[[$blk findInst $n] findITerm CLK] getNet] getName]" }
puts "CT_DONE"
