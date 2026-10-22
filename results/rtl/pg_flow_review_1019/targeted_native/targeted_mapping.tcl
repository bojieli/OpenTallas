source /source/native_pg_binding.tcl
read_db /clone/source_order_clone.odb
set block [ord::get_db_block]
set master [[lindex [$block getInsts] 0] getMaster]
set a [odb::dbInst_create $block $master pg_target_a]
set b [odb::dbInst_create $block $master pg_target_b]
set targets [list $a $b]
proc compare_target_whole {label block instances} {
  set begin [clock milliseconds]
  set target [ot_pg_prepare_targets $block $instances]
  set targeted_ms [expr {[clock milliseconds]-$begin}]
  set begin [clock milliseconds]
  set whole [ot_pg_prepare $block]
  set whole_ms [expr {[clock milliseconds]-$begin}]
  set selected [dict create]
  foreach inst $instances {
    foreach row [ot_pg_master_census $inst] {
      lassign $row mt term why
      set key [list [$inst getName] [$mt getName]]
      if {[dict exists $whole $key]} {dict set selected $key [dict get $whole $key]}
    }
  }
  if {[dict size $target] != [dict size $selected]} {error TARGET_CARDINALITY}
  dict for {key net} $selected {
    if {![dict exists $target $key] || [dict get $target $key] ne $net} {error "TARGET_NATIVE_MAP_MISMATCH $key"}
  }
  puts "TARGET_WHOLE_NATIVE_EQUAL $label terms=[dict size $target] targeted_ms=$targeted_ms whole_ms=$whole_ms"
  return $target
}
proc refuse {label body pattern} {
  if {![catch {uplevel 1 $body} reason] || ![string match $pattern $reason]} {error "TARGET_CONTROL_MISSING $label $reason"}
  puts "EXPECTED_TARGET_REFUSAL $label $reason"
}
compare_target_whole canonical $block $targets
# Native domain declarations and exact native region membership, arbitrary rail names.
foreach rule [$block getGlobalConnects] {odb::dbGlobalConnect_destroy $rule}
foreach name {pd_core_07 pd_io_13 pd_ret_09} {
 set net [odb::dbNet_create $block $name]
 $net setSigType [expr {$name eq "pd_ret_09" ? "GROUND" : "POWER"}]
}
foreach inst $targets region_name {pd_region_A pd_region_B} rail {pd_core_07 pd_io_13} {
 set region [odb::dbRegion_create $block $region_name]
 $region addInst $inst
 add_global_connection -net $rail -region $region_name -inst_pattern .* -pin_pattern {^VDD$} -power
 add_global_connection -net pd_ret_09 -region $region_name -inst_pattern .* -pin_pattern {^VSS$} -ground
}
set map [compare_target_whole arbitrary_regions $block $targets]
foreach inst $targets rail {pd_core_07 pd_io_13} {
 set key [list [$inst getName] VDD]
 if {[[dict get $map $key] getName] ne $rail} {error REGION_SELECTION_WRONG}
}
set unknown [odb::dbInst_create $block $master pg_target_unknown_region]
refuse missing_region {ot_pg_bind_before_protect [ot_pg_prepare_targets $block [list $unknown]] $unknown} {*OT_PG_UNKNOWN_DOMAIN*}
add_global_connection -net pd_io_13 -inst_pattern .* -pin_pattern {^VDD$} -power
refuse overlap_target {ot_pg_prepare_targets $block $targets} {*OT_PG_AMBIGUOUS_DOMAIN*}
refuse overlap_whole {ot_pg_prepare $block} {*OT_PG_AMBIGUOUS_DOMAIN*}
foreach rule [$block getGlobalConnects] {if {[$rule getRegion] eq "NULL"} {odb::dbGlobalConnect_destroy $rule}}
add_global_connection -net pd_core_07 -inst_pattern {^pg_target_a$} -pin_pattern {^VDD$} -power
refuse unsupported_instance_pattern {ot_pg_prepare_targets $block $targets} {*OT_PG_TARGET_UNSUPPORTED_INSTANCE_PATTERN*}
foreach rule [$block getGlobalConnects] {if {[$rule getInstPattern] ne ".*"} {odb::dbGlobalConnect_destroy $rule}}
# OpenDB's public constructor creates complete native ITerms. Proxy the lookup
# only to test refusal of absent/stale cardinality while retaining native MTerms.
set ::real_target $a
set ::real_term [$a findITerm VDD]
proc target_proxy {method args} {
 if {$method eq "findITerm" && [lindex $args 0] eq "VDD"} {
   if {$::proxy_mode eq "missing"} {return NULL}
   return target_term_proxy
 }
 return [$::real_target $method {*}$args]
}
proc target_term_proxy {method args} {
 if {$method eq "getSigType"} {return SIGNAL}
 return [$::real_term $method {*}$args]
}
foreach mode {missing changed} reason {OT_PG_MISSING_ITERM OT_PG_ITERM_TYPE_MISMATCH} {
 set ::proxy_mode $mode
 refuse $mode {ot_pg_prepare_targets $block [list target_proxy]} "*$reason*"
}
puts TARGETED_NATIVE_MAPPING_REVIEW_PASS
exit
