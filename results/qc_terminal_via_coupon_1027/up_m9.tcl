set d /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $d/lef/asap7_tech_1x_201209.lef
read_lef $d/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_verilog /w/ctree.v
link_design coupon
initialize_floorplan -die_area {0 0 30 20} -core_area {0 0 30 20} -site asap7sc7p5t
foreach layer {M5 M8 M9} { make_tracks $layer -x_offset 0.04 -x_pitch 0.08 -y_offset 0.04 -y_pitch 0.08 }
set blk [ord::get_db_block]
set tech [ord::get_db_tech]
create_ndr -name ot_mesh_ndr -width {M8 0.32 M9 0.32} -spacing {M8 0.08 M9 0.08}
place_pin -pin_name root -layer M8 -location {5 5} -pin_size {0.04 0.04}
place_pin -pin_name tap -layer M9 -location {8.0 10.0} -pin_size {0.04 0.04}
proc V {n} { global tech; set v [$tech findVia $n]; if {$v == "NULL"} { error "via $n missing" }; return $v }
proc LY {n} { global tech; return [$tech findLayer $n] }
set ot_ndr [$blk findNonDefaultRule ot_mesh_ndr]
if {$ot_ndr == "NULL"} { error "clock NDR missing" }
proc RL {n} { global ot_ndr; return [$ot_ndr getLayerRule [LY $n]] }
proc rnet {nm} { global blk ot_ndr; set n [$blk findNet $nm]; if {$n == "NULL"} { error "missing clock net $nm" }; if {[$n isSpecial]} { $n clearSpecial }; foreach it [$n getITerms] { $it clearSpecial }; $n setSigType CLOCK; $n setNonDefaultRule $ot_ndr; set w [$n getWire]; if {$w != "NULL"} { odb::dbWire_destroy $w }; return [odb::dbWire_create $n] }
proc IT {i p} { global blk; set t [[$blk findInst $i] findITerm $p]; if {$t == "NULL"} { error "no iterm $i/$p" }; return $t }
proc BT {p} { global blk; set t [$blk findBTerm $p]; if {$t == "NULL"} { error "no bterm $p" }; return $t }
set e [odb::dbWireEncoder]
set em_saved_ndr $ot_ndr
if {[$blk findNonDefaultRule ot_explicit_mesh_ndr] == "NULL"} { create_ndr -name ot_explicit_mesh_ndr -width {M8 0.32 M9 0.32} -spacing {M8 0.08 M9 0.08} }
set ot_ndr [$blk findNonDefaultRule ot_explicit_mesh_ndr]
set w [rnet root]
$e begin $w
$e newPath [LY M8] FIXED [RL M8]
set emj0 [$e addPoint 5000 5000]
$e newPath $emj0 FIXED [RL M8]
set emj1 [$e addPoint 25000 5000]
$e newPath $emj0 FIXED [RL M8]
set emj2 [$e addTechVia [V {VIA89}]]
$e newPath $emj1 FIXED [RL M8]
set emj3 [$e addTechVia [V {VIA89}]]
$e newPath $emj2 FIXED [RL M9]
set emj4 [$e addPoint 5000 10000]
$e newPath $emj3 FIXED [RL M9]
set emj5 [$e addPoint 25000 15000]
$e newPath $emj4 FIXED [RL M9]
set emj6 [$e addTechVia [V {VIA89}]]
$e newPath $emj4 FIXED [RL M9]
set emj7 [$e addPoint 5000 15000]
$e newPath $emj5 FIXED [RL M9]
set emj8 [$e addTechVia [V {VIA89}]]
$e newPath $emj6 FIXED [RL M8]
set emj9 [$e addPoint 8000 10000]
$e newPath $emj7 FIXED [RL M9]
set emj10 [$e addTechVia [V {VIA89}]]
$e newPath $emj8 FIXED [RL M8]
set emch11 [$e addPoint 5000 15000]
$e newPath $emj9 FIXED [RL M8]
set emj11 [$e addTechVia [V {VIA89}]]
$e newPath $emj11 FIXED [RL M9]
$e addPoint 8000 10000
$e addBTerm [BT tap]
$e newPath $emj0 FIXED [RL M8]
$e addPoint 5000 5000
$e addBTerm [BT root]
$e end
set ot_ndr $em_saved_ndr
puts "OT_ROUTED_CLOCK nets 1 pin_stairs 0 port_joins 2"
write_db /w/up_m9.odb
puts VIA_COUPON_DONE
