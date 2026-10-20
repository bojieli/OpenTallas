# QW-CTLM5 diag: the safe4 hr->core worst path with full clock detail (same load as tools/ref_tile/path_classes.tcl)
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
if {[file exists $base/4_cts.sdc]} { read_sdc $base/4_cts.sdc } else { read_sdc $base/3_place.sdc }
set_propagated_clock [all_clocks]
source $plat/setRC.tcl
estimate_parasitics -placement
set ::ot_ce_corner tt
read_sdc $::env(OT_GATE_SIGNOFF_SDC)
report_checks -from [get_clocks ot_entry_1] -to [get_clocks ot_entry_0] -group_path_count 3 -format full_clock_expanded -fields {fanout cap slew input_pin}
report_checks -from [get_clocks ot_entry_0] -to [get_clocks ot_entry_1] -group_path_count 1 -format full_clock_expanded
foreach pat {u_lpl_5_w* u_lpl_5_r* u_lpl_0_w* u_lpl_0_r* u_go* u_lpl_17_r*} {
  set n 0; set s 0; set mn 1e9; set mx -1e9
  foreach p [get_pins -quiet -hierarchical $pat/CLK] {
    set a [get_property $p arrival_max_rise]
    if {$a eq "" || $a eq "INF"} continue
    incr n; set s [expr {$s+$a}]; if {$a<$mn} {set mn $a}; if {$a>$mx} {set mx $a}
  }
  if {$n} {puts [format "OT_DIAG_CK %s n=%d mean=%.1f min=%.1f max=%.1f" $pat $n [expr {$s/$n}] $mn $mx]}
}
foreach c {u_lpl_5_w.g_chunk[3].u_local u_lpl_5_r.g_chunk[3].u_local} {
  set cells [get_cells -quiet -hierarchical "$c/*"]
  set xs {}; foreach cc $cells { set i [[ord::get_db_block] findInst [get_full_name $cc]]; if {$i ne "NULL"} { lassign [$i getLocation] x y; lappend xs "[expr {$x/1000.0}],[expr {$y/1000.0}]" } }
  puts "OT_DIAG_LOC $c [lrange $xs 0 5]"
}
