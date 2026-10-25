# KITS-SPARE/LB post-CTS clock dump (one corner): every flop's CK arrival (propagated, setRC_rcx placement RC) + location,
# then the FF hold census split in/out/r2r/rst on the corner-bound vclk.  Env: PC (tt|ff) VC PLIBS ODB KIT OUT
foreach l $::env(PLIBS) { read_liberty $l }
read_db $::env(ODB)
read_sdc $::env(KIT)/constraint.sdc
set_clock_latency -source $::env(VC) [get_clocks vclk]
source $::env(KIT)/setRC_rcx.tcl
set_propagated_clock [get_clocks clk]
# clock nets get estimated wire RC only when the clock is already propagated (estimate before propagate drops ~120 ps of clk wire on ve_m)
estimate_parasitics -placement
set blk [ord::get_db_block]; set u [$blk getDbUnitsPerMicron]
set fo [open $::env(OUT) w]
puts $fo "name,x,y,ck"
foreach i [$blk getInsts] {
  if {![string match "*DFF*" [[$i getMaster] getName]]} continue
  set p ""
  set v NA
  catch { set p [get_pins -quiet [$i getName]/CLK] }
  catch { set v [get_property $p arrival_max_rise] }
  lassign [$i getLocation] x y
  puts $fo "[$i getName],[expr {$x/double($u)}],[expr {$y/double($u)}],$v"
}
close $fo
if {$::env(PC) eq "ff"} {
  set cls [dict create in 0 out 0 r2r 0 rst 0]; set ws [dict create in 0 out 0 r2r 0 rst 0]
  foreach pe [find_timing_paths -path_delay min -group_path_count 200000 -endpoint_path_count 1 -slack_max 0] {
    set s [get_property $pe slack]; set sn [get_full_name [get_property $pe startpoint]]; set en [get_full_name [get_property $pe endpoint]]
    if {[string match "*RESETN*" $en] || [string match "*SETN*" $en] || [string match "rst*" $sn]} { set k rst } elseif {[llength [get_ports -quiet $sn]]} { set k in } elseif {[llength [get_ports -quiet $en]]} { set k out } else { set k r2r }
    dict incr cls $k; if {$s < [dict get $ws $k]} { dict set ws $k $s }
  }
  puts "OT_HOLD_CENSUS FF vclk $::env(VC) counts $cls worst $ws"
}
puts "OT_CKDUMP done"
