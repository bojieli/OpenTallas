# Regression only. Read a copied preflight ODB; never change source artifacts.
set ::env(RESULTS_DIR) /run/physical_preflight/ownership_tests
file mkdir $::env(RESULTS_DIR)
read_db /run/physical_preflight/host/floorplan.odb
source /src/physical/dscoll_cx/s81_lep_native_band.tcl
set b [ord::get_db_block]
ot_lep_births reopened 0
set n [lindex [ot_lep_nonmacro_names] 0];set i [$b findInst $n];set g [$i getGroup]
$g removeInst $i
if {![catch {ot_lep_manifest missing_owner} why] || ![string match {*missing/conflicting owner*} $why]} {error {missing-owner negative not caught}}
puts "LEP_OWNER_NEGATIVE_PASS $why"
$g addInst $i
set masters {}
foreach lib [[ord::get_db] getLibs] {
 foreach m [$lib getMasters] {
  if {[$m getName] eq "BUFx2_ASAP7_75t_R"} {set master $m}
 }
}
if {![info exists master]} {error {test BUF master missing}}
# Unconnected helper fixture is used ONLY to test native birth bookkeeping.
# It is not a functional source, timing or reach qualification.
set ni [odb::dbInst_create $b $master ot_lep_birth_fixture]
ot_lep_births bookkeeping_fixture 0
if {[[$ni getGroup] getName] ne $::ot_lep_owner || [[ot_lep_prop $ni] getValue] ne "bookkeeping_fixture"} {error {birth not classified}}
if {[ot_lep_prop $i] eq "NULL" || [[ot_lep_prop $i] getValue] ne "source_mapped"} {error {existing source identity changed}}
puts {LEP_BIRTH_BOOKKEEPING_PASS source_identity_preserved}
odb::dbInst_destroy $ni
ot_lep_manifest restored
puts {LEP_OWNERSHIP_TEST_PASS}
