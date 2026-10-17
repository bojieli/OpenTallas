# Hold path family diagnostic: gate 4_1_cts.odb (post 38.6k hold buffers) -> (A) hold buffers per endpoint family,
# (B) remove RSZ hold buffers -> FF hold slack per (start clock, end clock, start family, end family) under signoff SDC.
set base [lindex [glob /work/results/asap7/*/base] 0]
set plat /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $plat/lef/asap7_tech_1x_201209.lef
read_lef $plat/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f [glob $plat/lib/NLDM/*RVT_FF*] { catch {read_liberty $f} }
read_db $base/4_1_cts.odb
read_sdc $base/4_cts.sdc
set_propagated_clock [all_clocks]
source $plat/setRC.tcl
proc fam {n} { regsub -all {\[[0-9]+\]} $n {[]} n; regsub -all {_[0-9]+_} $n {_N_} n; regsub {\$_[A-Z0-9_]+_$} $n {} n; return $n }  ;# NOTE: first-pass bufs_by_sink tracing stopped at the first non-buffer cell; holdbuf.tcl is the authoritative per-family buffer count
set block [ord::get_db_block]
set hb {}
foreach i [$block getInsts] { if {[string match hold* [$i getName]]} { lappend hb $i } }
puts "HF hold_buffers [llength $hb]"
# forward trace each hold buffer to its sequential/port sinks
set famc [dict create]
foreach i $hb {
  set o [$i findITerm Y]; if {$o eq "NULL"} { foreach t [$i getITerms] { if {[$t isOutputSignal]} {set o $t} } }
  set front [list [$o getNet]]; set seen 0; set sinks {}
  while {[llength $front] && $seen < 200} {
    set n [lindex $front 0]; set front [lrange $front 1 end]; incr seen
    foreach t [$n getITerms] {
      if {![$t isInputSignal]} continue
      set ii [$t getInst]
      if {[string match hold* [$ii getName]] || [string match *BUF* [[$ii getMaster] getName]] && ![[$ii getMaster] isSequential]} {
        foreach t2 [$ii getITerms] { if {[$t2 isOutputSignal] && [$t2 getNet] ne "NULL"} { lappend front [$t2 getNet] } }
      } else { lappend sinks "[fam [$ii getName]]" }
    }
    foreach b [$n getBTerms] { lappend sinks "port:[fam [$b getName]]" }
  }
  foreach s [lsort -unique $sinks] { dict incr famc $s }
}
foreach {k v} [lsort -stride 2 -index 1 -integer -decreasing [dict get $famc]] { puts "HF bufs_by_sink $v $k" }
# remove hold buffers
remove_buffers $hb
estimate_parasitics -placement
set ::ot_ce_corner ff
read_sdc /src/physical/ref_tile/s81coll_cfifo_crs/signoff.sdc
if {[file exists /diag/ff_ioref_last.sdc]} { source /diag/ff_ioref_last.sdc; puts "HF ioref sourced" } else { puts "HF ioref absent" }
foreach c [all_clocks] { puts "HF clk [get_full_name $c] lat_src=[get_property $c is_propagated]" }
set paths [find_timing_paths -path_delay min -group_path_count 30000 -endpoint_path_count 1 -slack_max 30]
puts "HF endpoints_in_margin30 [llength $paths]"
set agg [dict create]
foreach p $paths {
  set s [get_property $p slack]
  set sc [get_property $p startpoint_clock]; set ec [get_property $p endpoint_clock]
  set scn [expr {$sc eq "" ? "-" : [get_full_name $sc]}]; set ecn [expr {$ec eq "" ? "-" : [get_full_name $ec]}]
  set sp [get_property $p startpoint]; set ep [get_property $p endpoint]
  set k "$scn>$ecn [fam [get_full_name $sp]] -> [fam [get_full_name $ep]]"
  if {![dict exists $agg $k]} { dict set agg $k [list 0 0 1e9] }
  lassign [dict get $agg $k] n nv w
  incr n; if {$s < 0} {incr nv}; if {$s < $w} {set w $s}
  dict set agg $k [list $n $nv $w]
}
dict for {k v} $agg { lassign $v n nv w; puts [format "HF fam n=%d viol=%d worst=%.1f %s" $n $nv $w $k] }
report_checks -path_delay min -format full_clock_expanded -digits 2 -to [get_pins -quiet {u_x.u_cross.o[*]$_DFF_PN0_/D}]
report_checks -path_delay min -format full_clock_expanded -digits 2 -to [get_pins -quiet {xa[*]$_DFF_P_/D}]
report_checks -path_delay min -format full_clock_expanded -digits 2 -to [get_pins -quiet {u_x.u_cross.bank*/D}]
