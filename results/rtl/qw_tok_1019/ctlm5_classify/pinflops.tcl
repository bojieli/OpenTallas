# QW-CTLM5 diag: clock arrival of every pin flop, by port, with its location (safe4 CTS db, TT, raw source latency 0)
set base [lindex [glob /work/results/asap7/*/base] 0]
set plat /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $plat/lef/asap7_tech_1x_201209.lef
read_lef $plat/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f [glob -nocomplain /work/objects/asap7/*/base/lib/*.lib $plat/lib/NLDM/*RVT_TT*] { catch {read_liberty $f} }
foreach l [split [exec sh -c "grep -h 'ADDITIONAL_LEFS\\|ADDITIONAL_LIBS' /work/config.mk || true"] "\n"] {
  foreach w [lrange [split $l " ="] 1 end] {
    if {[string match *.lef $w] && [file exists $w]} { catch {read_lef $w} }
    if {[string match *.lib $w] && [file exists $w]} { catch {read_liberty $w} }
  }
}
read_db $base/4_1_cts.odb
read_sdc $base/4_cts.sdc
set_propagated_clock [all_clocks]
foreach c [all_clocks] { if {[llength [get_property $c sources]]} { set_clock_latency -source 0 $c } }
source $plat/setRC.tcl
estimate_parasitics -placement
set blk [ord::get_db_block]
proc loc {inst} { set i [$::blk findInst $inst]; if {$i eq "NULL"} {return "- -"}; lassign [$i getLocation] x y; return "[expr {$x/1000.0}] [expr {$y/1000.0}]" }
foreach p [concat [all_inputs -no_clocks] [all_outputs]] {
  set n [get_full_name $p]
  if {[llength [get_ports -quiet $n]] == 0} continue
  if {[get_property $p direction] eq "input"} {
    set regs [get_fanout -from $p -flat -endpoints_only]
  } else {
    set regs [get_fanin -to $p -flat -startpoints_only]
  }
  foreach r $regs {
    set c [get_cells -quiet -of_objects $r]
    if {![llength $c]} continue
    set ck [get_pins -quiet [get_full_name $c]/CLK]
    if {![llength $ck]} continue
    set a [get_property $ck arrival_max_rise]
    set clks {}; foreach k [get_property $ck clocks] {lappend clks [get_full_name $k]}
    puts "OT_PF $n [get_full_name $c] $clks $a [loc [get_full_name $c]]"
    break
  }
}
