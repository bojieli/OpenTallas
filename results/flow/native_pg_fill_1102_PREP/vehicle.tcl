# Finite native mechanism fixture, not a project physical output.
set case $::env(PG_FILL_CASE)
read_db /work/input.odb
read_lef /work/asap7sc7p5t_28_L_1x_220121a.lef
set b [ord::get_db_block]
set row [lindex [$b getRows] 0];set site [$row getSite]
set sw [$site getWidth];set sh [$site getHeight]
foreach n [$b getNets] {$n setDoNotTouch 0}
foreach i [$b getInsts] {$i setDoNotTouch 0;odb::dbInst_destroy $i}
foreach row [$b getRows] {odb::dbRow_destroy $row}
foreach blockage [$b getBlockages] {odb::dbBlockage_destroy $blockage}
odb::dbRow_create $b ot_fill_row_R $site 0 0 R0 HORIZONTAL 40 $sw
odb::dbRow_create $b ot_fill_row_L $site 0 $sh MX HORIZONTAL 40 $sw
set fixture_area [odb::new_Rect 0 0 [expr {40*$sw}] [expr {2*$sh}]]
$b setCoreArea $fixture_area
$b setDieArea $fixture_area
set masters {BUFx2_ASAP7_75t_R OR4x1_ASAP7_75t_L}
foreach master $masters name {ot_neighbor_R ot_neighbor_L} y [list 0 $sh] orient {R0 MX} {
 set m [[ord::get_db] findMaster $master]
 if {$m eq "NULL"} {error "MISSING_NEIGHBOR $master"}
 set i [odb::dbInst_create $b $m $name];$i setOrient $orient;$i setLocation 0 $y;$i setPlacementStatus PLACED
}
global_connect
source /work/native_pg_binding.tcl
ot_pg_assert_all_native $b [ot_pg_prepare $b]
set rv {FILLERxp5_ASAP7_75t_R FILLER_ASAP7_75t_R DECAPx1_ASAP7_75t_R DECAPx2_ASAP7_75t_R DECAPx4_ASAP7_75t_R DECAPx6_ASAP7_75t_R DECAPx10_ASAP7_75t_R}
set both $rv
foreach m $rv {lappend both [string replace $m end end L]}
set use [expr {$case eq "missing_L" ? $rv : $both}]
foreach m $both {if {[[ord::get_db] findMaster $m] eq "NULL"} {error "MISSING_FILLER $m"}}
set ::env(OT_PG_STRICT) [expr {$case eq "callback" ? 1 : 0}]
set code [catch {
 if {$case eq "callback"} {
  ot_pg_native_birth_eval /work/nativepgbirth.so {
   if {![ot_pg_native_birth_supported filler_placement]} {error REAL_FILLER_CAPABILITY_REFUSED}
   filler_placement $use
  }
 } else {filler_placement $use}
} message options]
if {$case eq "missing_L"} {
 if {!$code || ![string match {*No fillers found for LVTN*} $message]} {error "EXPECTED_LVTN_FAILURE got=$message"}
 puts "EXPECTED_MISSING_L_FILLER_PASS $message"
 exit
}
if {$code} {return -options $options $message}
set geometry {};set opens 0;set count 0
foreach i [$b getInsts] {
 lappend geometry [list [$i getName] [[$i getMaster] getName] [$i getOrient] [$i getLocation] [$i getPlacementStatus] [$i getSourceType] [$i isPhysicalOnly]]
 if {[$i isPhysicalOnly]} {
  incr count
  foreach t [$i getITerms] {if {[[$t getMTerm] getSigType] in {POWER GROUND} && [$t getNet] eq "NULL"} {incr opens}}
 }
}
if {$count==0} {error NO_ACTUAL_FILLER_BIRTHS}
set f [open /work/fill_${case}_geometry.txt {WRONLY CREAT EXCL}];puts $f [join [lsort $geometry] "\n"];close $f
puts "FILL_VEHICLE case=$case physical_fillers=$count opens=$opens"
if {$case eq "callback"} {
 if {$opens!=0} {error CALLBACK_OPEN}
 if {[dict get [ot_native_pg_status] active]} {error CALLBACK_NOT_CLEANED_UP}
 if {![catch {filler_placement $use} refusal] || ![string match *OT_PG_NATIVE_BIRTH_CAPABILITY_REQUIRED* $refusal]} {error INACTIVE_FILLER_ADMITTED}
 ot_pg_assert_all_native $b [ot_pg_prepare $b]
 puts STRICT_FILLER_INACTIVE_REFUSAL_PASS
} elseif {$opens==0} {error CONTROL_MUST_SHOW_OPEN_PG}
write_db /work/fill_${case}.odb
puts FILL_VEHICLE_PASS
exit
