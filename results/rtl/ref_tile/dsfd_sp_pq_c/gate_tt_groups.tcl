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
read_db $base/4_cts.odb
create_clock -name core_clk -period 833.333 [get_ports clk]
set_propagated_clock [all_clocks]
estimate_parasitics -placement
set ins [dict create ot_dsrom_aq12t 463.1 ot_pqc_t_bc 162.9 ot_pqc_t_ctl16 192.2 ot_pqc_t_ix 159.8 ot_pqc_t_qb 180.7 ot_pqc_t_ret 174.8 ot_pqc_t_xin 117.8]
sta::worst_slack_cmd max
foreach c [get_cells u_*] {
  set m [get_property $c ref_name]
  if {![dict exists $ins $m]} continue
  set p [get_pins [get_full_name $c]/clk]
  set a [get_property $p arrival_max_rise]
  puts [format "CKPIN %-8s %-16s pin %.1f leaf %.1f" [get_full_name $c] $m $a [expr {$a + [dict get $ins $m]}]]
}
# raw data arrival at outputs / latest allowed arrival at inputs, relative to the common leaf time L
set_input_delay 0 -clock core_clk [all_inputs -no_clocks]
set_output_delay 0 -clock core_clk [all_outputs]
set grp [dict create]
foreach p [find_timing_paths -path_delay max -group_path_count 12000 -endpoint_path_count 1 -sort_by_slack] {
  set sp [get_full_name [get_property $p startpoint]]; set ep [get_full_name [get_property $p endpoint]]
  set s [get_property $p slack]
  if {[llength [get_ports -quiet $ep]]} { set k "OUT [regsub {\[\d+\]} $ep {}]" } elseif {[llength [get_ports -quiet $sp]]} { set k "IN  [regsub {\[\d+\]} $sp {}]" } else { set k "INT [regsub {/.*} $sp {}]->[regsub {/.*} $ep {}]" }
  if {![dict exists $grp $k] || $s < [lindex [dict get $grp $k] 0]} { dict set grp $k [list $s 0 0 $sp $ep] }
}
dict for {k v} $grp { lassign $v s a r sp ep; puts [format "GRP %-34s slack %8.1f arrival %8.1f required %8.1f  %s -> %s" $k $s $a $r $sp $ep] }
