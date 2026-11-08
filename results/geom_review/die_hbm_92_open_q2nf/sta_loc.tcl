foreach f [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*RVT_TT_nldm_*] { if {![string match *FAKE* $f]} { read_liberty $f } }
foreach f [glob /k/macros/*_tt.lib] { read_liberty $f }
read_db /k/run/results/asap7/hbc_ot_q2nf_rest/base/3_place.odb
read_sdc /k/run/results/asap7/hbc_ot_q2nf_rest/base/3_place.sdc
source /k/setRC_rcx.tcl
estimate_parasitics -placement
set block [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
proc loc {iname} {
  global block dbu
  set i [$block findInst $iname]
  if {$i == "NULL"} { return "?" }
  set b [$i getBBox]
  return [format "%.1f,%.1f %s" [expr {([$b xMin]+[$b xMax])/2.0/$dbu}] [expr {([$b yMin]+[$b yMax])/2.0/$dbu}] [[$i getMaster] getName]]
}
set out [open /o/paths_loc.txt w]
foreach ep {
 {u_fcore.u_x.u_body.g_q2.n_u_fj.u_fj.u.u_program.g_fsram.u_flow/addr_in[2]}
 {u_fcore.u_x.u_body.g_q2.n_u_fj.u_fj.u.u_program.g_fsram.u_flow/ce_in}
 {u_fcore.u_x.u_body.g_link[1].u_link.u_ctl.u.u_core.u_codec.p_tx_v$_DFF_PN0_/D}
 {u_fcore.u_x._55067_[1042]$_DFFE_PP_/D}
 {u_fcore.u_x._46183_[0]$_DFFE_PP_/D}
} {
  set paths [find_timing_paths -path_delay max -to [get_pins $ep] -group_path_count 1]
  foreach p $paths {
    puts $out "=== $ep slack [get_property $p slack]"
    foreach pt [get_property $p points] {
      set pin [get_property $pt pin]
      set nm [get_full_name $pin]
      set inst [get_full_name [get_cells -of_objects $pin]]
      puts $out [format "%8.1f %s @ %s" [get_property $pt arrival] $nm [loc $inst]]
    }
  }
}
close $out
