# S81-PINREG4 native TT probe at CTS (placement RC): launch = clock->output data arrival at each output port minus R
# (R = mean propagated clock arrival at the boundary registers: flops whose D comes from an input port or whose Q drives an
# output port through buffers), plus the hold pad count per output.  Diagnostic; the routed view's native_pin_audit is the gate.
foreach f [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_TT*.lib*] { read_liberty $f }
read_liberty /src/physical/asap7_memory_macros_v2/ot_rom_4096x274_m8/ot_rom_4096x274_m8_tt.lib
read_db /base/4_1_cts.odb
read_sdc /base/4_1_cts.sdc
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
estimate_parasitics -placement
read_sdc /src/physical/s81_bf_hier/signoff_col_hb.sdc
set n 0; set s 0.0
foreach p [get_pins -quiet -hierarchical g_pin.r_*/CLK] {
  set a [get_property $p arrival_max_rise]; if {$a eq "INF"} continue; incr n; set s [expr {$s + $a}]
}
set R [expr {$s / $n}]
puts "PROBE R_pinreg_tt $R n $n"
set worst 0; set wpin ""; set over 0; set cnt 0
foreach port [get_ports -quiet [all_outputs]] {
  sta::redirect_string_begin
  catch {report_checks -to $port -path_delay max -format full -digits 2}
  set r [sta::redirect_string_end]
  if {![regexp {(-?[0-9.]+)\s+data arrival time} $r -> arr]} continue
  set l [expr {$arr - $R}]
  incr cnt
  if {$l > 220} { incr over }
  if {$l > $worst} { set worst $l; set wpin [get_full_name $port] }
}
puts "PROBE launch_max [format %.1f $worst] pin $wpin over220 $over of $cnt"
set hold [sta::worst_slack_cmd min]
puts "PROBE worst_hold_tt [format %.1f $hold]"
# pad cells between each output port and its driving flop (BUF / INV / HB chain)
set blk [ord::get_db_block]; set hist [dict create]
foreach bt [$blk getBTerms] {
  if {[$bt getIoType] ne "OUTPUT" || [$bt getSigType] in {POWER GROUND CLOCK}} continue
  set net [$bt getNet]; set k 0
  while {$net ne "NULL" && $net ne "" && $k < 60} {
    set d ""; foreach t [$net getITerms] { if {[$t isOutputSignal]} { set d [$t getInst]; break } }
    if {$d eq ""} break
    set m [[$d getMaster] getName]
    if {![string match "BUF*" $m] && ![string match "INV*" $m] && ![string match "HB*" $m]} break
    incr k; set net ""
    foreach t [$d getITerms] { if {[$t isInputSignal]} { set net [$t getNet]; break } }
  }
  dict incr hist $k
}
puts "PROBE out_pad_cells_hist [lsort -integer -stride 2 -index 0 $hist]"
