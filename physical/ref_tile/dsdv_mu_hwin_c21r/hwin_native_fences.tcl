source /src/physical/ref_tile/dsdv_mu_hwin_c21r/candidate_birth_bind.tcl
# Exact mapped-cell fences; no core, clock, PDN or latency edits.
source /src/physical/ref_tile/dsdv_mu_hwin_c21r/native_cell_fence.tcl
set ::ot_hj_boxes [dict create]
dict set ::ot_hj_boxes CENTRE {2.16 159.84 559.44 206.28}

# Follow every output edge, without a visit/depth cap, to first real FF/macro
# sinks. Existing combinational-cell owners are deliberately NOT terminal seeds.
proc ot_hj_leaf_groups {start} {
 set todo [list $start]; set seen [dict create]; set owners [dict create]
 while {[llength $todo]} {
  set i [lindex $todo end]; set todo [lrange $todo 0 end-1]
  set nm [$i getName]
  if {[dict exists $seen $nm]} {continue}
  dict set seen $nm 1
  if {$i ne $start && [[$i getMaster] isBlock]} {
   set key [string map [list [format %c 92] "" / .] $nm]
   if {![dict exists $::ot_hj_macro_owner $key]} {error "HWIN_BIRTH unknown macro owner $nm"}
   set group [dict get $::ot_hj_macro_owner $key]
   dict set owners $group 1; continue
  }
  if {$i ne $start && [regexp {^DFF} [[$i getMaster] getName]]} {
   set g [$i getGroup]
   if {$g eq "NULL" || ![string match ot_hj_* [$g getName]]} {error "HWIN_BIRTH unknown first FF owner $nm"}
   dict set owners [string range [$g getName] 6 end] 1; continue
  }
  foreach pin [$i getITerms] {
   if {[$pin getIoType] ne "OUTPUT"} {continue}
   set net [$pin getNet]
   if {$net eq "NULL"} {continue}
   foreach bp [$net getBTerms] {if {[$bp getIoType] eq "OUTPUT"} {dict set owners CENTRE 1}}
   foreach sink [$net getITerms] {
    if {[$sink getIoType] eq "INPUT"} {lappend todo [$sink getInst]}
   }
  }
 }
 if {[dict size $owners] == 1} {return [lindex [dict keys $owners] 0]}
 return CENTRE
}
set ::ot_hj_macro_owner [dict create]
set ot_hj_mf [open /src/physical/ref_tile/dsdv_mu_hwin_c21r/native_macro_manifest.tsv r]
while {[gets $ot_hj_mf line]>=0} {
 lassign [split $line "\t"] group key
 if {[dict exists $::ot_hj_macro_owner $key]} {error "HWIN_NATIVE duplicate macro owner $key"}
 dict set ::ot_hj_macro_owner $key $group
}
close $ot_hj_mf
# Exact cf87adad8 preGPL native-stage removals, backed by SOURCE+ODB hashes.
# No wildcard matching or missing functional/FF acceptance is permitted.
set ::ot_hj_removed [dict create]
set ot_hj_rf [open /src/physical/ref_tile/dsdv_mu_hwin_c21r/native_flow_removed_cells.tsv r]
while {[gets $ot_hj_rf line]>=0} {
 lassign [split $line "\t"] key master
 if {$master ni {BUFx2_ASAP7_75t_R BUFx3_ASAP7_75t_R BUFx6f_ASAP7_75t_R TIELOx1_ASAP7_75t_R TIEHIx1_ASAP7_75t_R}} {error "HWIN_NATIVE invalid removed master $master"}
 if {[dict exists $::ot_hj_removed $key]} {error "HWIN_NATIVE duplicate removed identity $key"}
 dict set ::ot_hj_removed $key $master
}
close $ot_hj_rf
proc ot_hj_fences_install {} {
 if {[info exists ::ot_hj_installed]} {return}
 if {![info exists ::env(RESULTS_DIR)]} {error "HWIN_NATIVE missing source RESULTS_DIR"}
 set source_netlist [file join $::env(RESULTS_DIR) 1_2_yosys.v]
 if {![file isfile $source_netlist]} {error "HWIN_NATIVE missing source netlist $source_netlist"}
 set source_hash [lindex [exec sha256sum $source_netlist] 0]
 if {$source_hash ne "4ea21c9bb75a199a0ade71fb740fb740fced289a3c7c83d4ac02a474d89099c2"} {error "HWIN_NATIVE source netlist hash mismatch $source_hash"}
 set b [ord::get_db_block]; set native [dict create]
 foreach i [$b getInsts] {
  if {[[$i getMaster] isBlock]} {continue}
  set key [string map [list [format %c 92] "" / .] [$i getName]]
  if {[dict exists $native $key]} {error "HWIN_NATIVE ambiguous escaped native name $key"}
  dict set native $key [$i getName]
 }
 set groups [dict create];set matched [dict create];set removed_count 0
 set inherited [expr {[$b findGroup ot_hj_CENTRE] ne "NULL"}]
 set f [open /src/physical/ref_tile/dsdv_mu_hwin_c21r/native_cell_manifest.tsv r]
 while {[gets $f line]>=0} {
  lassign [split $line "\t"] group key
  if {![dict exists $native $key]} {
   if {[dict exists $::ot_hj_removed $key]} {incr removed_count;continue}
   error "HWIN_NATIVE missing mapped cell $key"
  }
  set name [dict get $native $key]
  if {[dict exists $matched $name]} {error "HWIN_NATIVE duplicate manifest cell $name"}
  dict set matched $name $group;dict lappend groups $group $name
 }
 close $f
 dict for {group names} $groups {
  if {![dict exists $::ot_hj_boxes $group]} {error "HWIN_NATIVE unknown box $group"}
  if {$inherited} {
   foreach nm $names {
    set old [[$b findInst $nm] getGroup]
    if {$old eq "NULL" || [$old getName] ne "ot_hj_$group"} {error "HWIN_NATIVE inherited ownership mismatch $nm"}
   }
  } else {ot_native_cell_fence ot_hj_$group [dict get $::ot_hj_boxes $group] $names}
 }
 set ::ot_hj_installed 1
 puts "HWIN_NATIVE_MANIFEST cells=[dict size $matched] inherited=$inherited exact_flow_removed=$removed_count"
}
proc ot_hj_assign_births {seed} {
 set b [ord::get_db_block];set births [dict create]
 foreach i [$b getInsts] {
  if {[[$i getMaster] isBlock]} {continue}
  set old [$i getGroup]
  if {$old ne "NULL"} {
   if {![string match ot_hj_* [$old getName]]} {error "HWIN_BIRTH conflicting owner [$i getName]"}
   continue
  }
  set master [[$i getMaster] getName]
  if {[ot_candidate_physical_only $i]} {continue}
  # Physical synthesis may resize/delete old logic or insert buffers/ties.
  # A newly inserted state element or arbitrary gate needs an explicit new model.
  if {[catch {ot_candidate_birth_role $i} detail]} {error "HWIN_BIRTH unmodelled functional cell [$i getName] $master: $detail"}
  set owner [ot_hj_leaf_groups $i]
  if {![dict exists $::ot_hj_boxes $owner]} {error "HWIN_BIRTH bad owner $owner"}
  dict lappend births $owner [$i getName]
 }
 dict for {owner names} $births {
  ot_native_cell_fence_add ot_hj_$owner $names
  if {$seed} {ot_candidate_seed_new ot_hj_$owner [dict get $::ot_hj_boxes $owner] $names}
  puts "HWIN_BIRTH_ASSIGNED owner=$owner cells=[llength $names] seeded=$seed"
 }
 return $births
}
# Actual native legal row capacity inside a region; macro halos/site cuts are
# not counted as usable area. No density credit for an outer rectangle.
proc ot_hj_legal_area {box} {
 set b [ord::get_db_block];set u [[ord::get_db_tech] getDbUnitsPerMicron]
 lassign $box x0 y0 x1 y1
 set area 0.0
 foreach row [$b getRows] {
  set r [$row getBBox]
  set dx [expr {max(0.0,min(double([$r xMax])/$u,$x1)-max(double([$r xMin])/$u,$x0))}]
  set dy [expr {max(0.0,min(double([$r yMax])/$u,$y1)-max(double([$r yMin])/$u,$y0))}]
  set area [expr {$area+$dx*$dy}]
 }
 if {$area<=0} {error "HWIN_NATIVE no legal capacity box=$box"}
 return $area
}
proc ot_hj_fences_check {stage} {
 set b [ord::get_db_block];set u [[ord::get_db_tech] getDbUnitsPerMicron]
 set total 0.0
 dict for {group box} $::ot_hj_boxes {
  ot_native_cell_fence_check ot_hj_$group $box $stage
  set area 0.0
  foreach i [[$b findGroup ot_hj_$group] getInsts] {
   set m [$i getMaster]
   set area [expr {$area+double([$m getWidth])*[$m getHeight]/$u/$u}]
  }
  lassign $box x0 y0 x1 y1
  set legal_region [ot_hj_legal_area $box]
  set density [expr {$area/$legal_region}]
  if {$density>0.60} {error "HWIN_NATIVE_DENSITY above60pct owner=$group density=$density stage=$stage"}
  puts "HWIN_NATIVE_DENSITY owner=$group area_um2=$area density=$density stage=$stage"
 }
 foreach i [$b getInsts] {
  set m [$i getMaster]
  if {[$m isBlock] || [ot_candidate_physical_only $i]} {continue}
  set total [expr {$total+double([$m getWidth])*[$m getHeight]/$u/$u}]
 }
 set legal [ot_hj_legal_area {2.16 159.84 559.44 206.28}]
 if {$legal<=0} {error "HWIN_NATIVE_DENSITY no legal rows"}
 set density [expr {$total/$legal}]
 if {$density>0.60 || ($density<0.40 && ![string match *GPL* $stage] && ![string match *DP* $stage])} {error "HWIN_NATIVE_DENSITY legal_band_outside_stage_budget density=$density stage=$stage"}
 puts "HWIN_NATIVE_DENSITY band_std_area_um2=$total legal_row_area_um2=$legal density=$density stage=$stage"
 ot_native_cell_band_check {2.16 159.84 559.44 206.28} $stage
}

if {![llength [info commands ::ot_hj_global_placement_orig]]} {
 rename global_placement ::ot_hj_global_placement_orig
 proc global_placement {args} {
  ot_candidate_pg_ready placement_call
  ot_hj_fences_install
  ot_hj_assign_births 0
  set result [uplevel 1 [list ::ot_hj_global_placement_orig {*}$args]]
  ot_hj_fences_check GPL
  return $result
 }
 rename detailed_placement ::ot_hj_detailed_placement_orig
 proc detailed_placement {args} {
  ot_candidate_pg_ready placement_call
  ot_hj_fences_install
  ot_hj_assign_births 1
  set result [uplevel 1 [list ::ot_hj_detailed_placement_orig {*}$args]]
  ot_hj_fences_check DP
  return $result
 }
}
