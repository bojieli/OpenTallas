set blk [ord::get_db_block]
set tech [ord::get_db_tech]
foreach sw [[$blk findNet ck_mesh] getSWires] {odb::dbSWire_destroy $sw}
proc V {n} { global tech; set v [$tech findVia $n]; if {$v == "NULL"} { error "via $n missing" }; return $v }
proc LY {n} { global tech; return [$tech findLayer $n] }
set ot_ndr [$blk findNonDefaultRule CONTACT]
if {$ot_ndr == "NULL"} { error "clock NDR missing" }
proc RL {n} { global ot_ndr; return [$ot_ndr getLayerRule [LY $n]] }
proc rnet {nm} { global blk ot_ndr; set n [$blk findNet $nm]; if {$n == "NULL"} { error "missing clock net $nm" }; if {[$n isSpecial]} { $n clearSpecial }; foreach it [$n getITerms] { $it clearSpecial }; $n setSigType CLOCK; $n setNonDefaultRule $ot_ndr; set w [$n getWire]; if {$w != "NULL"} { odb::dbWire_destroy $w }; return [odb::dbWire_create $n] }
proc IT {i p} { global blk; set t [[$blk findInst $i] findITerm $p]; if {$t == "NULL"} { error "no iterm $i/$p" }; return $t }
proc BT {p} { global blk; set t [$blk findBTerm $p]; if {$t == "NULL"} { error "no bterm $p" }; return $t }
set e [odb::dbWireEncoder]
set em_saved_ndr $ot_ndr
if {[$blk findNonDefaultRule ot_explicit_mesh_ndr] == "NULL"} { create_ndr -name ot_explicit_mesh_ndr -width {M8 0.16 M9 0.16} -spacing {M8 0.08 M9 0.08} }
set ot_ndr [$blk findNonDefaultRule ot_explicit_mesh_ndr]
set w [rnet ck_mesh]
$e begin $w
$e newPath [LY M8] FIXED [RL M8]
set emj0 [$e addPoint 220000 3103920]
$e newPath $emj0 FIXED [RL M8]
set emj1 [$e addPoint 257040 3103920]
$e newPath $emj1 FIXED [RL M8]
set emj2 [$e addPoint 300000 3103920]
$e newPath $emj1 FIXED [RL M8]
set emj3 [$e addTechVia [V {VIA89}]]
$e newPath $emj3 FIXED [RL M9]
set emj4 [$e addPoint 257040 3000000]
$e newPath $emj3 FIXED [RL M9]
set emj5 [$e addPoint 257040 3107295]
$e newPath $emj5 FIXED [RL M9]
set emj6 [$e addPoint 257040 3246480]
$e newPath $emj6 FIXED [RL M9]
set emj7 [$e addPoint 257040 3372705]
$e newPath $emj7 FIXED [RL M9]
set emj8 [$e addPoint 257040 3376080]
$e newPath $emj8 FIXED [RL M9]
set emj9 [$e addTechVia [V {VIA89}]]
$e newPath $emj8 FIXED [RL M9]
set emj10 [$e addPoint 257040 3450000]
$e newPath $emj9 FIXED [RL M8]
set emj11 [$e addPoint 220000 3376080]
$e newPath $emj9 FIXED [RL M8]
set emj12 [$e addPoint 300000 3376080]
$e newPath $emj5 FIXED [RL M9]
set jd1 [$e addTechVia [V {VIA89}]]
$e newPath $jd1 FIXED [RL M8]
$e addPoint 257240 3107295
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 257240 3107375
set jd2 [$e addTechVia [V VIA67]]
$e newPath $jd2 FIXED
$e addPoint 257320 3107375
set jd3 [$e addTechVia [V VIA56]]
$e newPath $jd3 FIXED
$e addPoint 257320 3107471
set jd4 [$e addTechVia [V VIA45]]
$e newPath $jd4 FIXED
$e addPoint 257773 3107471
set jd5 [$e addTechVia [V VIA34]]
$e newPath $jd5 FIXED
$e addPoint 257773 3107340
set jd6 [$e addTechVia [V VIA23]]
$e newPath $jd6 FIXED
$e addPoint 257823 3107340
set jd7 [$e addTechVia [V VIA12]]
$e newPath $jd7 FIXED
$e addITerm [IT M0_11 Y]
$e newPath $emj7 FIXED [RL M9]
set jd8 [$e addTechVia [V {VIA89}]]
$e newPath $jd8 FIXED [RL M8]
$e addPoint 257240 3372705
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 257240 3372625
set jd9 [$e addTechVia [V VIA67]]
$e newPath $jd9 FIXED
$e addPoint 257320 3372625
set jd10 [$e addTechVia [V VIA56]]
$e newPath $jd10 FIXED
$e addPoint 257320 3372529
set jd11 [$e addTechVia [V VIA45]]
$e newPath $jd11 FIXED
$e addPoint 257773 3372529
set jd12 [$e addTechVia [V VIA34]]
$e newPath $jd12 FIXED
$e addPoint 257773 3372660
set jd13 [$e addTechVia [V VIA23]]
$e newPath $jd13 FIXED
$e addPoint 257823 3372660
set jd14 [$e addTechVia [V VIA12]]
$e newPath $jd14 FIXED
$e addITerm [IT M0_12 Y]
$e newPath $emj6 FIXED [RL M9]
$e addPoint 257040 3246480
$e addBTerm [BT mesh_contact]
$e end
set ot_ndr $em_saved_ndr
puts "OT_ROUTED_CLOCK nets 1 pin_stairs 2 port_joins 1"
