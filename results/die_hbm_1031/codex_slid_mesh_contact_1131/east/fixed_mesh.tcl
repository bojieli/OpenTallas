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
set emj0 [$e addPoint 230000 136080]
$e newPath $emj0 FIXED [RL M8]
set emj1 [$e addPoint 257040 136080]
$e newPath $emj1 FIXED [RL M8]
set emj2 [$e addPoint 340000 136080]
$e newPath $emj1 FIXED [RL M8]
set emj3 [$e addTechVia [V {VIA89}]]
$e newPath $emj3 FIXED [RL M9]
set emj4 [$e addPoint 257040 135000]
$e newPath $emj3 FIXED [RL M9]
set emj5 [$e addPoint 257040 270000]
$e newPath $emj4 FIXED [RL M9]
set emj6 [$e addTechVia [V {VIA89}]]
$e newPath $emj4 FIXED [RL M9]
set emj7 [$e addPoint 257040 100000]
$e newPath $emj5 FIXED [RL M9]
set emj8 [$e addPoint 257040 403920]
$e newPath $emj6 FIXED [RL M8]
set emj9 [$e addPoint 321840 135000]
$e newPath $emj8 FIXED [RL M9]
set emj10 [$e addTechVia [V {VIA89}]]
$e newPath $emj8 FIXED [RL M9]
set emj11 [$e addPoint 257040 405000]
$e newPath $emj9 FIXED [RL M8]
set emj12 [$e addTechVia [V {VIA89}]]
$e newPath $emj10 FIXED [RL M8]
set emj13 [$e addPoint 230000 403920]
$e newPath $emj10 FIXED [RL M8]
set emj14 [$e addPoint 340000 403920]
$e newPath $emj11 FIXED [RL M9]
set emj15 [$e addTechVia [V {VIA89}]]
$e newPath $emj11 FIXED [RL M9]
set emj16 [$e addPoint 257040 450000]
$e newPath $emj12 FIXED [RL M9]
set emj17 [$e addPoint 321840 132660]
$e newPath $emj15 FIXED [RL M8]
set emj18 [$e addPoint 321840 405000]
$e newPath $emj18 FIXED [RL M8]
set emj19 [$e addTechVia [V {VIA89}]]
$e newPath $emj19 FIXED [RL M9]
set emj20 [$e addPoint 321840 407340]
$e newPath $emj17 FIXED [RL M9]
set jd15 [$e addTechVia [V {VIA89}]]
$e newPath $jd15 FIXED [RL M8]
$e addPoint 321640 132660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 321640 132740
set jd16 [$e addTechVia [V VIA67]]
$e newPath $jd16 FIXED
$e addPoint 321560 132740
set jd17 [$e addTechVia [V VIA56]]
$e newPath $jd17 FIXED
$e addPoint 321560 132836
set jd18 [$e addTechVia [V VIA45]]
$e newPath $jd18 FIXED
$e addPoint 317867 132836
set jd19 [$e addTechVia [V VIA34]]
$e newPath $jd19 FIXED
$e addPoint 317867 132660
set jd20 [$e addTechVia [V VIA23]]
$e newPath $jd20 FIXED
$e addPoint 317817 132660
set jd21 [$e addTechVia [V VIA12]]
$e newPath $jd21 FIXED
$e addITerm [IT M0_0 Y]
$e newPath $emj20 FIXED [RL M9]
set jd22 [$e addTechVia [V {VIA89}]]
$e newPath $jd22 FIXED [RL M8]
$e addPoint 321640 407340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 321640 407420
set jd23 [$e addTechVia [V VIA67]]
$e newPath $jd23 FIXED
$e addPoint 321560 407420
set jd24 [$e addTechVia [V VIA56]]
$e newPath $jd24 FIXED
$e addPoint 321560 407516
set jd25 [$e addTechVia [V VIA45]]
$e newPath $jd25 FIXED
$e addPoint 317867 407516
set jd26 [$e addTechVia [V VIA34]]
$e newPath $jd26 FIXED
$e addPoint 317867 407340
set jd27 [$e addTechVia [V VIA23]]
$e newPath $jd27 FIXED
$e addPoint 317817 407340
set jd28 [$e addTechVia [V VIA12]]
$e newPath $jd28 FIXED
$e addITerm [IT M0_1 Y]
$e newPath $emj5 FIXED [RL M9]
$e addPoint 257040 270000
$e addBTerm [BT mesh_contact]
$e end
set ot_ndr $em_saved_ndr
puts "OT_ROUTED_CLOCK nets 1 pin_stairs 2 port_joins 1"
