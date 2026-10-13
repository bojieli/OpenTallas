# Generated kept strap-stage fences: no child/clock/pin budget change.
set sb [ord::get_db_block]
set su [[ord::get_db_tech] getDbUnitsPerMicron]
set sn 0
set rg [odb::dbRegion_create $sb strap_l0_s0]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(292*$su)}] [expr {round(1236.8*$su)}] [expr {round(308*$su)}] [expr {round(1244.8*$su)}]
set gr [odb::dbGroup_create $sb strap_l0_s0]
$rg addGroup $gr
set nc 0
foreach net [$sb getNets] {
  set nm [string map {\ {}} [$net getName]]
  if {[string first {g_strap[0].u_sr.s0[} $nm] >= 0 } { foreach it [$net getITerms] { set si [$it getInst]; if {[$it isOutputSignal] && [string match *DFF* [[$si getMaster] getName]]} { $gr addInst $si; incr nc; incr sn } } }
}
if {$nc != 26} {error "STRAP_REGION strap_l0_s0: expected 26 DFFs, got $nc"}
set rg [odb::dbRegion_create $sb strap_l0_s1]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(357*$su)}] [expr {round(1096*$su)}] [expr {round(373*$su)}] [expr {round(1104*$su)}]
set gr [odb::dbGroup_create $sb strap_l0_s1]
$rg addGroup $gr
set nc 0
foreach net [$sb getNets] {
  set nm [string map {\ {}} [$net getName]]
  if {[string first {g_strap[0].u_sr.s1[} $nm] >= 0 } { foreach it [$net getITerms] { set si [$it getInst]; if {[$it isOutputSignal] && [string match *DFF* [[$si getMaster] getName]]} { $gr addInst $si; incr nc; incr sn } } }
}
if {$nc != 26} {error "STRAP_REGION strap_l0_s1: expected 26 DFFs, got $nc"}
set rg [odb::dbRegion_create $sb strap_l0_s2]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(357*$su)}] [expr {round(1056*$su)}] [expr {round(373*$su)}] [expr {round(1064*$su)}]
set gr [odb::dbGroup_create $sb strap_l0_s2]
$rg addGroup $gr
set nc 0
foreach net [$sb getNets] {
  set nm [string map {\ {}} [$net getName]]
  if {[string first {g_strap[0].u_sr.s2[} $nm] >= 0 } { foreach it [$net getITerms] { set si [$it getInst]; if {[$it isOutputSignal] && [string match *DFF* [[$si getMaster] getName]]} { $gr addInst $si; incr nc; incr sn } } }
}
if {$nc != 26} {error "STRAP_REGION strap_l0_s2: expected 26 DFFs, got $nc"}
set rg [odb::dbRegion_create $sb strap_l0_s3]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(292*$su)}] [expr {round(1056*$su)}] [expr {round(308*$su)}] [expr {round(1064*$su)}]
set gr [odb::dbGroup_create $sb strap_l0_s3]
$rg addGroup $gr
set nc 0
foreach net [$sb getNets] {
  set nm [string map {\ {}} [$net getName]]
  if {[string first {g_strap[0].u_sr.s3[} $nm] >= 0 } { foreach it [$net getITerms] { set si [$it getInst]; if {[$it isOutputSignal] && [string match *DFF* [[$si getMaster] getName]]} { $gr addInst $si; incr nc; incr sn } } }
}
if {$nc != 26} {error "STRAP_REGION strap_l0_s3: expected 26 DFFs, got $nc"}
set rg [odb::dbRegion_create $sb strap_l0_s4]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(252*$su)}] [expr {round(1029.68*$su)}] [expr {round(268*$su)}] [expr {round(1037.68*$su)}]
set gr [odb::dbGroup_create $sb strap_l0_s4]
$rg addGroup $gr
set nc 0
foreach net [$sb getNets] {
  set nm [string map {\ {}} [$net getName]]
  if {[string first {g_strap[0].u_sr.s4[} $nm] >= 0 } { foreach it [$net getITerms] { set si [$it getInst]; if {[$it isOutputSignal] && [string match *DFF* [[$si getMaster] getName]]} { $gr addInst $si; incr nc; incr sn } } }
}
if {$nc != 26} {error "STRAP_REGION strap_l0_s4: expected 26 DFFs, got $nc"}
set rg [odb::dbRegion_create $sb strap_l1_s0]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(332*$su)}] [expr {round(1236.8*$su)}] [expr {round(348*$su)}] [expr {round(1244.8*$su)}]
set gr [odb::dbGroup_create $sb strap_l1_s0]
$rg addGroup $gr
set nc 0
foreach net [$sb getNets] {
  set nm [string map {\ {}} [$net getName]]
  if {[string first {g_strap[1].u_sr.s0[} $nm] >= 0 } { foreach it [$net getITerms] { set si [$it getInst]; if {[$it isOutputSignal] && [string match *DFF* [[$si getMaster] getName]]} { $gr addInst $si; incr nc; incr sn } } }
}
if {$nc != 26} {error "STRAP_REGION strap_l1_s0: expected 26 DFFs, got $nc"}
set rg [odb::dbRegion_create $sb strap_l1_s1]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(357*$su)}] [expr {round(946*$su)}] [expr {round(373*$su)}] [expr {round(954*$su)}]
set gr [odb::dbGroup_create $sb strap_l1_s1]
$rg addGroup $gr
set nc 0
foreach net [$sb getNets] {
  set nm [string map {\ {}} [$net getName]]
  if {[string first {g_strap[1].u_sr.s1[} $nm] >= 0 } { foreach it [$net getITerms] { set si [$it getInst]; if {[$it isOutputSignal] && [string match *DFF* [[$si getMaster] getName]]} { $gr addInst $si; incr nc; incr sn } } }
}
if {$nc != 26} {error "STRAP_REGION strap_l1_s1: expected 26 DFFs, got $nc"}
set rg [odb::dbRegion_create $sb strap_l1_s2]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(357*$su)}] [expr {round(646*$su)}] [expr {round(373*$su)}] [expr {round(654*$su)}]
set gr [odb::dbGroup_create $sb strap_l1_s2]
$rg addGroup $gr
set nc 0
foreach net [$sb getNets] {
  set nm [string map {\ {}} [$net getName]]
  if {[string first {g_strap[1].u_sr.s2[} $nm] >= 0 } { foreach it [$net getITerms] { set si [$it getInst]; if {[$it isOutputSignal] && [string match *DFF* [[$si getMaster] getName]]} { $gr addInst $si; incr nc; incr sn } } }
}
if {$nc != 26} {error "STRAP_REGION strap_l1_s2: expected 26 DFFs, got $nc"}
set rg [odb::dbRegion_create $sb strap_l1_s3]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(357*$su)}] [expr {round(346*$su)}] [expr {round(373*$su)}] [expr {round(354*$su)}]
set gr [odb::dbGroup_create $sb strap_l1_s3]
$rg addGroup $gr
set nc 0
foreach net [$sb getNets] {
  set nm [string map {\ {}} [$net getName]]
  if {[string first {g_strap[1].u_sr.s3[} $nm] >= 0 } { foreach it [$net getITerms] { set si [$it getInst]; if {[$it isOutputSignal] && [string match *DFF* [[$si getMaster] getName]]} { $gr addInst $si; incr nc; incr sn } } }
}
if {$nc != 26} {error "STRAP_REGION strap_l1_s3: expected 26 DFFs, got $nc"}
set rg [odb::dbRegion_create $sb strap_l1_s4]
$rg setRegionType EXCLUSIVE
odb::dbBox_create $rg [expr {round(252*$su)}] [expr {round(196.0*$su)}] [expr {round(268*$su)}] [expr {round(204.0*$su)}]
set gr [odb::dbGroup_create $sb strap_l1_s4]
$rg addGroup $gr
set nc 0
foreach net [$sb getNets] {
  set nm [string map {\ {}} [$net getName]]
  if {[string first {g_strap[1].u_sr.s4[} $nm] >= 0 } { foreach it [$net getITerms] { set si [$it getInst]; if {[$it isOutputSignal] && [string match *DFF* [[$si getMaster] getName]]} { $gr addInst $si; incr nc; incr sn } } }
}
if {$nc != 26} {error "STRAP_REGION strap_l1_s4: expected 26 DFFs, got $nc"}
if {$sn != 260} {error "STRAP_REGION expected 260 DFFs"}
puts "STRAP_REGION_FENCES 10 DFFS $sn"
