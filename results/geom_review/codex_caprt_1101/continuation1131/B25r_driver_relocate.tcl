# PREPARED ONLY / NOT EXECUTED. Run on an OWN continuation copy, never overwrite failed A40.
# Env ODB=current own copy5_1_grt.odb, OT_CORNER=TT, OT_POSTCTS_GRT=1, OUTDIR=new output dir.
source /work/postcts_gate.tcl
set blk [ord::get_db_block]; set u [$blk getDbUnitsPerMicron]
set oldloc {};set oldstatus {}
foreach i [$blk getInsts] {dict set oldloc [$i getName] [$i getLocation];dict set oldstatus [$i getName] [$i getPlacementStatus]}
set movers {clkbuf_7_72__f_clk_regs clkbuf_7_64__f_clk_regs clkload44}
set_routing_layers -signal M2-M5 -clock M2-M5
global_route -start_incremental
foreach i [$blk getInsts] {if {[$i getName] ni $movers && [$i getPlacementStatus] eq "PLACED"} {$i setPlacementStatus FIRM}}
set i [$blk findInst clkbuf_7_72__f_clk_regs]
if {$i eq "NULL"} {error "missing actual planned mover clkbuf_7_72__f_clk_regs"}
set m [$i getMaster]
$i setPlacementStatus PLACED
$i setLocation [expr {round((153.930857143-[$m getWidth]/2.0/$u)*$u)}] [expr {round((26.382857143-[$m getHeight]/2.0/$u)*$u)}]
set i [$blk findInst clkbuf_7_64__f_clk_regs]
if {$i eq "NULL"} {error "missing actual planned mover clkbuf_7_64__f_clk_regs"}
set m [$i getMaster]
$i setPlacementStatus PLACED
$i setLocation [expr {round((135.536625000-[$m getWidth]/2.0/$u)*$u)}] [expr {round((8.977500000-[$m getHeight]/2.0/$u)*$u)}]
set i [$blk findInst clkload44]
if {$i eq "NULL"} {error "missing actual planned mover clkload44"}
set m [$i getMaster]
$i setPlacementStatus PLACED
$i setLocation [expr {round((137.696625000-[$m getWidth]/2.0/$u)*$u)}] [expr {round((9.517500000-[$m getHeight]/2.0/$u)*$u)}]
detailed_placement
check_placement -verbose
foreach i [$blk getInsts] {set n [$i getName];if {$n ni $movers && [dict exists $oldloc $n] && [$i getLocation] ne [dict get $oldloc $n]} {error "unapproved existing-cell move $n"}}
global_connect
global_route -end_incremental -resistance_aware
estimate_parasitics -global_routing
puts "RELOCATION_POST_WNS [sta::time_sta_ui [sta::worst_slack_cmd max]]"
foreach i [$blk getInsts] {set n [$i getName];if {[dict exists $oldstatus $n]} {$i setPlacementStatus [dict get $oldstatus $n]}}
file mkdir $::env(OUTDIR)
write_db $::env(OUTDIR)/5_1_grt.odb
write_sdc $::env(OUTDIR)/5_1_grt.sdc
puts "PREPARED_CLOCK_RELOCATION_DONE"
