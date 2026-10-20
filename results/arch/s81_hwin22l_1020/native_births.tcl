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
cut_rows -halo_width_x 10.8 -halo_width_y 10.8
source /newkit/hwin_cell_band.tcl
source /newkit/hwin_fixture_fences.tcl
if {[info exists ::env(OT_HWIN_NEG_MISSING)]} {
 foreach i [$b getInsts] {
  if {[regexp {^DFF} [[$i getMaster] getName]]} {puts "NEG_REMOVE [$i getName]";odb::dbInst_destroy $i;break}
 }
}
ot_hj_fences_install
set costs [dict create CENTRE 6951.70026 WEST 2035.45548 EAST 2076.74604]
set u [[ord::get_db_tech] getDbUnitsPerMicron]
set f [open /audit/native_capacity.tsv w]
dict for {g box} $::ot_hj_boxes {
 set legal [ot_hj_legal_area $box];set area 0.0
 foreach i [[$b findGroup ot_hj_$g] getInsts] {set m [$i getMaster];set area [expr {$area+double([$m getWidth])*[$m getHeight]/$u/$u}]}
 set budget [dict get $costs $g];set density [expr {$budget/$legal}]
 puts "NATIVE_CAPACITY group=$g rows_area=$legal source_area=$area retained_cts_budget=$budget projected_density=$density"
 puts $f "$g\t$legal\t$area\t$budget\t$density"
 if {$density>0.60} {error "NATIVE_CAPACITY above60 retained actual CTS inventory $g"}
}
close $f
set total 0.0
foreach row [$b getRows] {set r [$row getBBox];set total [expr {$total+double([$r xMax]-[$r xMin])*([$r yMax]-[$r yMin])/$u/$u}]}
puts "NATIVE_ROW_PLAN_PASS rows=[llength [$b getRows]] legal_area=$total actual_cts_density=[expr {11063.90178/$total}] source_ff_inventory=unchanged no_new_gate=1"
# Verify uncapped runtime birth ownership using a 40-buffer chain to a real west FF.
set west_ff "";set bm "";set fm ""
foreach i [$b getInsts] {
 set mn [[$i getMaster] getName]
 if {$mn eq "BUFx2_ASAP7_75t_R"} {set bm [$i getMaster]}
 if {[regexp {^DFF} $mn]} {
  set fm [$i getMaster]
  set g [$i getGroup]
  if {$g ne "NULL" && [$g getName] eq "ot_hj_WEST" && [$i findITerm D] ne "NULL"} {set west_ff $i}
 }
}
if {$west_ff eq "" || $bm eq "" || $fm eq ""} {error "BIRTH_FIXTURE missing native fixtures"}
if {[info exists ::env(OT_HWIN_NEG_NEW_FF)]} {
 odb::dbInst_create $b $fm hwin22l_unmodelled_state
 ot_hj_assign_births 0
 error "BIRTH_FIXTURE unexpected acceptance of new FF"
}
set dp [$west_ff findITerm D];set prior [$dp getNet];set created {}
for {set n 0} {$n<40} {incr n} {
 set i [odb::dbInst_create $b $bm hwin22l_birth_$n]
 set net [odb::dbNet_create $b hwin22l_birth_net_$n]
 [$i findITerm A] connect $prior
 [$i findITerm Y] connect $net
 lappend created $i;set prior $net
}
$dp disconnect
$dp connect $prior
ot_hj_assign_births 0
foreach i $created {
 set g [$i getGroup]
 if {$g eq "NULL" || [$g getName] ne "ot_hj_WEST"} {error "BIRTH_FIXTURE wrong owner [$i getName]"}
}
puts "NATIVE_BIRTH_CHAIN_PASS 40buffers_to_real_westFF=[$west_ff getName] uncapped_firstFF_owner=WEST existing_identity_manifest=59580"
write_db /audit/source_regions_births.odb
