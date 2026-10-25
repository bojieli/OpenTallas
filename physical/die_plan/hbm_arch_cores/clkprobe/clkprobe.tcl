# HBM-CLKSTRUCT 10-25: read-only post-CTS clock-structure probe (FF libs, placement RC, as hold_gate.tcl).
# env: PLIBS ODB SDC PLATFORM_DIR OUT
foreach l [split $::env(PLIBS)] { if {$l ne ""} { read_liberty $l } }
read_db $::env(ODB)
read_sdc $::env(SDC)
set_propagated_clock [get_clocks clk]
source $::env(PLATFORM_DIR)/setRC.tcl
estimate_parasitics -placement
set blk [ord::get_db_block]
set u [$blk getDbUnitsPerMicron]
set O $::env(OUT)
# clock nets: driver -> sinks edges
set fe [open $O/clknets.csv w]
puts $fe "net,drv,dx,dy,sink,sx,sy,smaster"
set fs [open $O/sinks.csv w]
puts $fs "inst,master,x,y,arr_max,arr_min,kind"
foreach n [$blk getNets] {
  if {[$n getSigType] ne "CLOCK"} continue
  set drv ""; set dx 0; set dy 0
  foreach bt [$n getBTerms] { if {[$bt getIoType] eq "INPUT"} { set bb [$bt getBBox]; set drv [$bt getName]; set dx [expr {([$bb xMin]+[$bb xMax])/2.0/$u}]; set dy [expr {([$bb yMin]+[$bb yMax])/2.0/$u}] } }
  foreach it [$n getITerms] {
    if {[$it isOutputSignal]} { set i [$it getInst]; set drv [$i getName]; lassign [$i getLocation] a b; set dx [expr {$a/double($u)}]; set dy [expr {$b/double($u)}] }
  }
  foreach it [$n getITerms] {
    if {[$it isOutputSignal]} continue
    set i [$it getInst]; set m [$i getMaster]
    lassign [$i getLocation] a b
    set sx [expr {$a/double($u)}]; set sy [expr {$b/double($u)}]
    puts $fe "[$n getName],$drv,$dx,$dy,[$i getName],$sx,$sy,[$m getName]"
    set mn [$m getName]
    set kind ""
    if {[$m isBlock]} { set kind macro } elseif {[string match "*DFF*" $mn] || [string match "*DHL*" $mn] || [string match "*DLL*" $mn]} { set kind ff }
    if {$kind ne ""} {
      set p [get_pins -quiet "[$i getName]/[[$it getMTerm] getName]"]
      set amax ""; set amin ""
      if {$p ne ""} { catch {set amax [expr {[get_property $p arrival_max_rise]*1e12}]}; catch {set amin [expr {[get_property $p arrival_min_rise]*1e12}]} }
      puts $fs "[$i getName],$mn,$sx,$sy,$amax,$amin,$kind"
    }
  }
}
close $fe; close $fs
# worst hold paths (reg2reg and port), endpoint-unique
set fh [open $O/hold.csv w]
puts $fh "start,end,slack,startclk,endclk,io"
foreach p [find_timing_paths -path_delay min -group_path_count 20000 -endpoint_path_count 1 -slack_max 0] {
  set sp [get_property $p startpoint]; set ep [get_property $p endpoint]
  set io [expr {[get_property $sp is_port] || [get_property $ep is_port]}]
  set sc ""; set ec ""
  catch {set sc [get_full_name [get_property $p startpoint_clock]]}
  catch {set ec [get_full_name [get_property $p endpoint_clock]]}
  puts $fh "[get_full_name $sp],[get_full_name $ep],[expr {[get_property $p slack]*1e12}],$sc,$ec,$io"
}
close $fh
# a few detailed worst reg2reg reports
report_checks -path_delay min -group_path_count 3 -format full_clock_expanded -fields {fanout cap slew input_pin} > $O/worst_hold.rpt
report_clock_skew -hold >> $O/worst_hold.rpt
puts "CLKPROBE done"
