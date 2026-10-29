# Called only after the unchanged clock is frozen and incremental GRT has begun.
set phy_b [ord::get_db_block]
set phy_master [[ord::get_db] findMaster BUFx2_ASAP7_75t_R]
if {$phy_master eq "NULL"} {error "missing exact BUF master"}
set phy_n0 [llength [$phy_b getInsts]]
set phy_nn0 [llength [$phy_b getNets]]
set phy_before {}; set phy_allowed {}
foreach i [$phy_b getInsts] {
 foreach t [$i getITerms] {
  set nn [$t getNet];set name "";if {$nn ne "NULL"} {set name [$nn getName]}
  dict set phy_before "[$i getName]/[[$t getMTerm] getName]" $name
 }
}
source /work/phy_delay_records.tcl
if {[llength $phy_delay_records]!=1025} {error "bad data/valid port census"}
foreach rec $phy_delay_records {
 lassign $rec port net loads cells
 set bt [$phy_b findBTerm $port];set old [$phy_b findNet $net]
 if {$bt eq "NULL" || $old eq "NULL" || [$bt getNet] ne $old} {error "PHY input binding changed at $port"}
 set ns {}; set bs {}
 foreach c $cells {
  lassign $c name nn x y orient
  if {[$phy_b findInst $name] ne "NULL" || [$phy_b findNet $nn] ne "NULL"} {error "delay identity exists: $name"}
  set i [odb::dbInst_create $phy_b $phy_master $name]
  $i setOrient $orient
  $i setLocation $x $y
  $i setPlacementStatus FIRM
  set n [odb::dbNet_create $phy_b $nn]
  lappend bs $i;lappend ns $n
 }
 foreach ip $loads {
  lassign $ip name pin
  set it [[$phy_b findInst $name] findITerm $pin]
  if {$it eq "NULL" || [$it getNet] ne $old} {error "old input path changed $name/$pin"}
  $it disconnect;$it connect [lindex $ns 1]
  dict set phy_allowed "$name/$pin" [[lindex $ns 1] getName]
 }
 [[lindex $bs 0] findITerm A] connect $old
 [[lindex $bs 0] findITerm Y] connect [lindex $ns 0]
 [[lindex $bs 1] findITerm A] connect [lindex $ns 0]
 [[lindex $bs 1] findITerm Y] connect [lindex $ns 1]
}
if {[llength [$phy_b getInsts]]!=$phy_n0+2050 || [llength [$phy_b getNets]]!=$phy_nn0+2050} {error "wrong inserted cell/net census"}
set phy_bad {}
foreach i [$phy_b getInsts] {
 foreach t [$i getITerms] {
  set key "[$i getName]/[[$t getMTerm] getName]"
  if {![dict exists $phy_before $key]} continue
  set expect [dict get $phy_before $key]
  if {[dict exists $phy_allowed $key]} {set expect [dict get $phy_allowed $key]}
  set nn [$t getNet];set actual "";if {$nn ne "NULL"} {set actual [$nn getName]}
  if {$actual ne $expect} {lappend phy_bad $key}
 }
}
if {[llength $phy_bad]} {error "unplanned old terminal changes: [lrange $phy_bad 0 8]"}
puts "PHY_DELAY_IDENTITY_PASS 1025 paths, 2 BUF each, 2050 new cells/nets; all other terminals/captureFF/clock unchanged"
