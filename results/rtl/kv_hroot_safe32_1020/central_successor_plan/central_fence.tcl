# Candidate source-bound PRE_GLOBAL_PLACE hook, AFTER existing pin anchors.
# Not connected to any kit; DB-only smoke does not constitute gate approval.
set cf_b [ord::get_db_block]
set cf_u [$cf_b getDbUnitsPerMicron]
if {[$cf_b findRegion ot_hroot_center80] ne "NULL"} {error "HROOT center region already exists; refuse duplicate hook"}
set cf_anchor [dict create]
foreach cf_file {ot_out_flop_at_pins.txt ot_inhold_firm.txt} {
 set cf_path [file join $::env(RESULTS_DIR) $cf_file]
 if {![file exists $cf_path]} {error "HROOT missing native boundary ownership list $cf_path"}
 set cf_f [open $cf_path r]
 foreach cf_n [split [read $cf_f] "\n"] {if {$cf_n ne ""} {dict set cf_anchor $cf_n 1}}
 close $cf_f
}
set cf_pin_count 0
set cf_members {};set cf_area 0.0
set cf_report [open [file join $::env(RESULTS_DIR) ot_hroot_central_members.tsv] w]
puts $cf_report "instance\tmaster\tstatus\townership"
foreach cf_i [$cf_b getInsts] {
 set cf_name [$cf_i getName];set cf_status [$cf_i getPlacementStatus];set cf_m [$cf_i getMaster]
 if {[$cf_m isBlock]} {error "HROOT expected no hard macro, found $cf_name"}
 if {[dict exists $cf_anchor $cf_name]} {
  if {$cf_status ne "FIRM"} {error "HROOT native boundary anchor $cf_name is $cf_status before GPL"}
  incr cf_pin_count;puts $cf_report "$cf_name\t[$cf_m getName]\t$cf_status\tnative_boundary"
 } elseif {$cf_status eq "FIRM"} {
  error "HROOT unowned FIRM functional candidate $cf_name"
 } elseif {$cf_status ni {LOCKED COVER}} {
  if {[$cf_i getGroup] ne "NULL"} {error "HROOT preexisting group on $cf_name; refuse overwrite"}
  lappend cf_members $cf_i
  set cf_area [expr {$cf_area + double([$cf_m getWidth])*[$cf_m getHeight]/$cf_u/$cf_u}]
  puts $cf_report "$cf_name\t[$cf_m getName]\t$cf_status\tcentral_fence"
 } else {puts $cf_report "$cf_name\t[$cf_m getName]\t$cf_status\tphysical_fixed"}
}
close $cf_report
if {$cf_pin_count != [dict size $cf_anchor]} {error "HROOT boundary identity list has absent instances before GPL"}
if {$cf_pin_count < 3000 || [llength $cf_members] < 2500} {error "HROOT implausible incomplete boundary/core classification"}
if {$cf_area > 3840.0} {error "HROOT central80 actual cell area $cf_area exceeds60% capacity"}
set cf_r [odb::dbRegion_create $cf_b ot_hroot_center80]
odb::dbBox_create $cf_r [expr {round(110.12*$cf_u)}] [expr {round(110.12*$cf_u)}] [expr {round(190.12*$cf_u)}] [expr {round(190.12*$cf_u)}]
$cf_r setRegionType INCLUSIVE
set cf_g [odb::dbGroup_create $cf_r ot_hroot_center80_group]
foreach cf_i $cf_members {$cf_g addInst $cf_i}
puts [format "HROOT_CENTER members=%d native_boundary=%d area_um2=%.6f capacity_um2=6400 utilization=%.6f hard_region=(110.12,110.12,190.12,190.12)" [llength $cf_members] $cf_pin_count $cf_area [expr {$cf_area/6400.0}]]
