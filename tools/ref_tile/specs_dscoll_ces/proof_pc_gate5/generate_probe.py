import json,pathlib
root=pathlib.Path('/home/ubuntu/wt/s81-cesn-1013')
out=pathlib.Path('/tmp/ces_pc_gate5_probes');out.mkdir(exist_ok=True)
for name in ['dscoll_ces0_pc','dscoll_cesn_pc']:
 s=json.load(open(root/f'tools/ref_tile/specs_dscoll_ces/{name}.json'))
 for corner in ['tt','ff','ss']:
  t=['set base [lindex [glob /work/results/asap7/*/base] 0]', 'set plat /OpenROAD-flow-scripts/flow/platforms/asap7','read_lef $plat/lef/asap7_tech_1x_201209.lef','read_lef $plat/lef/asap7sc7p5t_28_R_1x_220121a.lef']
  for view in sorted({c['view'] for c in s['children']}):t.append('read_lef /src/'+view+'/'+pathlib.Path(view).name+'.lef')
  t.append('foreach f [glob $plat/lib/NLDM/*RVT_'+corner.upper()+'*] {read_liberty $f}')
  for view in sorted({c['view'] for c in s['children']}):t.append('read_liberty /src/'+view+'/'+pathlib.Path(view).name+'_'+corner+'.lib')
  t+=['read_db $base/4_1_cts.odb','read_sdc $base/4_cts.sdc','delete_clock [all_clocks]','source $plat/setRC.tcl','estimate_parasitics -placement',f'set ::ot_ce_corner {corner}',f'read_sdc /src/physical/ref_tile/{name}/signoff.sdc','sta::worst_slack_cmd max']
  t+=[r'''set actual {}
foreach cell [get_cells -quiet -hierarchical *] {
 set m [get_property $cell ref_name]
 if {![dict exists $::ot_ce_counts $m]} continue
 foreach pin [get_pins -quiet -of_objects $cell] {
  set key "$m/[get_property $pin lib_pin_name]"
  if {![dict exists $::ot_ce_refs $key]} continue
  set R [lindex [dict get $::ot_ce_refs $key $::ot_ce_corner] 1]
  set a [get_property $pin arrival_max_rise]
  lappend actual [expr {$a+$R}]
  puts "ACTUAL_PHI [get_full_name $pin] arrival=$a R=$R phi=[expr {$a+$R}]"
 }
}
set ordered [lsort -real $actual]
set spread [expr {[lindex $ordered end]-[lindex $ordered 0]}]
if {[llength $actual]!=10 || $spread>0.001} {error "ACTUAL_PHI_FAIL n=[llength $actual] spread=$spread"}
puts "ACTUAL_PHI_PASS $::ot_ce_corner n=[llength $actual] spread=$spread"
puts "ACTUAL_WNS $::ot_ce_corner setup_ps=[expr {[sta::worst_slack_cmd max]*1e12}] hold_ps=[expr {[sta::worst_slack_cmd min]*1e12}]"
foreach a [get_clocks ot_entry_*] {
 foreach b [get_clocks ot_entry_*] {
  if {$a eq $b} continue
  foreach kind {max min} {
   set paths [find_timing_paths -from $a -to $b -path_delay $kind -group_path_count 1 -endpoint_path_count 1 -sort_by_slack]
   if {![llength $paths]} continue
   set p [lindex $paths 0]
   puts "ACTUAL_PAIR $::ot_ce_corner $kind [get_full_name $a] -> [get_full_name $b] slack=[get_property $p slack] start=[get_full_name [get_property $p startpoint]] end=[get_full_name [get_property $p endpoint]]"
  }
 }
}
report_checks -path_delay min_max -fields {slew cap input nets fanout} -format full_clock_expanded -group_path_count 3
puts "ACTUAL_PROBE_DONE $::ot_ce_corner period833.333 setup150/210 hold100 all_actual_pairs_timed"
exit
''']
  (out/f'{name}_{corner}.tcl').write_text('\n'.join(t)+'\n')
print(out)
