set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach l [glob $P/lib/NLDM/*RVT*TT*.lib*] {read_liberty $l}
foreach l [glob /src/physical/asap7_memory_macros/*/*_tt.lib] {read_liberty $l}
set ::env(RESULTS_DIR) /case/routes/gate/work/orfs/results/asap7/opentallas_dsdv_mu_hwin_capture_1019_asap7_ref_gate/base
read_db $::env(RESULTS_DIR)/1_synth.odb
set b [ord::get_db_block]
set site ""
foreach i [$b getInsts] {
 if {[[$i getMaster] isBlock]} {continue}
 set st [[$i getMaster] getSite]
 if {$st ne "NULL"} {set site [$st getName];break}
}
if {$site eq ""} {error "no native source site"}
initialize_floorplan -die_area {0 0 561.6 388.8} -core_area {2.16 2.16 559.44 386.64} -site $site
source /newkit/place_fixture.tcl
cut_rows -halo_width_x 8.64 -halo_width_y 8.64
source /newkit/hwin_cell_band.tcl

proc snapshot {stage} {
 set b [ord::get_db_block];set f [open /audit/graph_$stage.tsv w]
 set ip 0;set np 0;set bound 0;set unbound 0
 foreach n [$b getNets] {if {[$n isDoNotTouch]} {incr np}}
 foreach i [$b getInsts] {
  if {[$i isDoNotTouch]} {incr ip}
  foreach p [$i getITerms] {
   set m [$p getMTerm];set n [$p getNet]
   set nn [expr {$n eq "NULL" ? "NULL" : [$n getName]}]
   puts $f [join [list [$i getName] [[$i getMaster] getName] [$m getName] [$m getSigType] $nn] "\t"]
   if {[$m getSigType] in {POWER GROUND}} {if {$n eq "NULL"} {incr unbound} else {incr bound}}
  }
 }
 close $f
 set sha [lindex [exec sha256sum /audit/graph_$stage.tsv] 0]
 puts "PG_PROTECTION stage=$stage inst_dnt=$ip net_dnt=$np pg_bound=$bound pg_unbound=$unbound graph=$sha"
 return [list $ip $np $bound $unbound $sha]
}
set initial [snapshot SOURCE]
# Bind the identical canonical five rules before any private hook is loaded.
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDDPE$}
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDDCE$}
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSSE$}
global_connect
set baseline [snapshot BOUND]
if {[lindex $baseline 3]!=0} {error "unbound PG before private hooks"}
foreach stage {PRE_GLOBAL_PLACE_TCL PRE_GLOBAL_PLACE_SKIP_IO_TCL PRE_DETAIL_PLACE_TCL} {
 source /src/physical/ref_tile/dsdv_mu_hwin_c21l/hwin_native_fences.tcl
 ot_hj_fences_install
 ot_hj_assign_births [expr {$stage eq "PRE_DETAIL_PLACE_TCL"}]
 set now [snapshot $stage]
 if {$now ne $baseline} {error "private placement hook changed native graph/PG/protection $stage"}
}
puts "PRIVATE_HOOK_GRAPH_PG_PROTECTION_INVARIANCE_PASS"
write_db /audit/regions_pg_bound.odb
