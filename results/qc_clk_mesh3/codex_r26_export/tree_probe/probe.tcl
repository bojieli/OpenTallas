set d /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $d/lef/asap7_tech_1x_201209.lef
read_lef $d/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f [glob $d/lib/NLDM/*RVT_TT_nldm*.lib*] {read_liberty $f}
read_verilog /w/ctree.v
link_design die_ctree
initialize_floorplan -die_area {0 0 200 40} -core_area {0 0 200 40} -site asap7sc7p5t
make_tracks M8 -x_offset 0.04 -x_pitch 0.08 -y_offset 0.04 -y_pitch 0.08
make_tracks M9 -x_offset 0.04 -x_pitch 0.08 -y_offset 0.04 -y_pitch 0.08
set blk [ord::get_db_block]
set tech [ord::get_db_tech]
create_ndr -name ot_mesh_ndr -width {M8 0.64 M9 0.64} -spacing {M8 0.5 M9 0.5}
place_inst -name ckt_0_0 -location {10.8 10.8} -orient R0 -status FIRM
place_inst -name ckt_0_1 -location {10.8 11.07} -orient R0 -status FIRM
place_inst -name ckt_1_0 -location {60.48 10.8} -orient R0 -status FIRM
place_inst -name ckt_1_1 -location {60.48 11.07} -orient R0 -status FIRM
place_inst -name ckt_2_0 -location {120.42 6.75} -orient R0 -status FIRM
place_inst -name ckt_3_0 -location {10.8 30.24} -orient R0 -status FIRM
place_pin -pin_name t_g3 -layer M8 -location {21.033 32.52} -pin_size {0.04 0.32}
place_pin -pin_name t_g2 -layer M8 -location {130.653 4.6} -pin_size {0.04 0.32}
place_pin -pin_name root -layer M9 -location {2.187 10.92} -pin_size {0.04 0.32}
proc V {n} { global tech; set v [$tech findVia $n]; if {$v == "NULL"} { error "via $n missing" }; return $v }
proc LY {n} { global tech; return [$tech findLayer $n] }
set ot_ndr [$blk findNonDefaultRule ot_mesh_ndr]
if {$ot_ndr == "NULL"} { error "clock NDR missing" }
proc RL {n} { global ot_ndr; return [$ot_ndr getLayerRule [LY $n]] }
proc rnet {nm} { global blk ot_ndr; set n [$blk findNet $nm]; if {$n == "NULL"} { error "missing clock net $nm" }; if {[$n isSpecial]} { $n clearSpecial }; foreach it [$n getITerms] { $it clearSpecial }; $n setSigType CLOCK; $n setNonDefaultRule $ot_ndr; set w [$n getWire]; if {$w != "NULL"} { odb::dbWire_destroy $w }; return [odb::dbWire_create $n] }
proc IT {i p} { global blk; set t [[$blk findInst $i] findITerm $p]; if {$t == "NULL"} { error "no iterm $i/$p" }; return $t }
proc BT {p} { global blk; set t [$blk findBTerm $p]; if {$t == "NULL"} { error "no bterm $p" }; return $t }
set e [odb::dbWireEncoder]
set ot_v89 [$blk findVia ot_via89_arr]
if {$ot_v89 == "NULL"} {
  set ot_v89 [odb::dbVia_create $blk ot_via89_arr]
  odb::dbBox_create $ot_v89 [LY M8] -265 -265 265 265
  odb::dbBox_create $ot_v89 [LY M9] -265 -285 265 285
  odb::dbBox_create $ot_v89 [LY V8] -265 -265 -225 -225
  odb::dbBox_create $ot_v89 [LY V8] -167 -265 -127 -225
  odb::dbBox_create $ot_v89 [LY V8] -69 -265 -29 -225
  odb::dbBox_create $ot_v89 [LY V8] 29 -265 69 -225
  odb::dbBox_create $ot_v89 [LY V8] 127 -265 167 -225
  odb::dbBox_create $ot_v89 [LY V8] 225 -265 265 -225
  odb::dbBox_create $ot_v89 [LY V8] -265 -167 -225 -127
  odb::dbBox_create $ot_v89 [LY V8] -167 -167 -127 -127
  odb::dbBox_create $ot_v89 [LY V8] -69 -167 -29 -127
  odb::dbBox_create $ot_v89 [LY V8] 29 -167 69 -127
  odb::dbBox_create $ot_v89 [LY V8] 127 -167 167 -127
  odb::dbBox_create $ot_v89 [LY V8] 225 -167 265 -127
  odb::dbBox_create $ot_v89 [LY V8] -265 -69 -225 -29
  odb::dbBox_create $ot_v89 [LY V8] -167 -69 -127 -29
  odb::dbBox_create $ot_v89 [LY V8] -69 -69 -29 -29
  odb::dbBox_create $ot_v89 [LY V8] 29 -69 69 -29
  odb::dbBox_create $ot_v89 [LY V8] 127 -69 167 -29
  odb::dbBox_create $ot_v89 [LY V8] 225 -69 265 -29
  odb::dbBox_create $ot_v89 [LY V8] -265 29 -225 69
  odb::dbBox_create $ot_v89 [LY V8] -167 29 -127 69
  odb::dbBox_create $ot_v89 [LY V8] -69 29 -29 69
  odb::dbBox_create $ot_v89 [LY V8] 29 29 69 69
  odb::dbBox_create $ot_v89 [LY V8] 127 29 167 69
  odb::dbBox_create $ot_v89 [LY V8] 225 29 265 69
  odb::dbBox_create $ot_v89 [LY V8] -265 127 -225 167
  odb::dbBox_create $ot_v89 [LY V8] -167 127 -127 167
  odb::dbBox_create $ot_v89 [LY V8] -69 127 -29 167
  odb::dbBox_create $ot_v89 [LY V8] 29 127 69 167
  odb::dbBox_create $ot_v89 [LY V8] 127 127 167 167
  odb::dbBox_create $ot_v89 [LY V8] 225 127 265 167
  odb::dbBox_create $ot_v89 [LY V8] -265 225 -225 265
  odb::dbBox_create $ot_v89 [LY V8] -167 225 -127 265
  odb::dbBox_create $ot_v89 [LY V8] -69 225 -29 265
  odb::dbBox_create $ot_v89 [LY V8] 29 225 69 265
  odb::dbBox_create $ot_v89 [LY V8] 127 225 167 265
  odb::dbBox_create $ot_v89 [LY V8] 225 225 265 265
}
if {[$blk findNonDefaultRule ot_mesh_ndr__16w] == "NULL"} { create_ndr -name ot_mesh_ndr__16w -width {M8 0.64 M9 0.64} -spacing {M8 0.5 M9 0.5} }
set ot_v89_16w [$blk findVia ot_via89_arr_16w]
if {$ot_v89_16w == "NULL"} {
  set ot_v89_16w [odb::dbVia_create $blk ot_via89_arr_16w]
  odb::dbBox_create $ot_v89_16w [LY M8] -265 -265 265 265
  odb::dbBox_create $ot_v89_16w [LY M9] -265 -285 265 285
  odb::dbBox_create $ot_v89_16w [LY V8] -265 -265 -225 -225
  odb::dbBox_create $ot_v89_16w [LY V8] -167 -265 -127 -225
  odb::dbBox_create $ot_v89_16w [LY V8] -69 -265 -29 -225
  odb::dbBox_create $ot_v89_16w [LY V8] 29 -265 69 -225
  odb::dbBox_create $ot_v89_16w [LY V8] 127 -265 167 -225
  odb::dbBox_create $ot_v89_16w [LY V8] 225 -265 265 -225
  odb::dbBox_create $ot_v89_16w [LY V8] -265 -167 -225 -127
  odb::dbBox_create $ot_v89_16w [LY V8] -167 -167 -127 -127
  odb::dbBox_create $ot_v89_16w [LY V8] -69 -167 -29 -127
  odb::dbBox_create $ot_v89_16w [LY V8] 29 -167 69 -127
  odb::dbBox_create $ot_v89_16w [LY V8] 127 -167 167 -127
  odb::dbBox_create $ot_v89_16w [LY V8] 225 -167 265 -127
  odb::dbBox_create $ot_v89_16w [LY V8] -265 -69 -225 -29
  odb::dbBox_create $ot_v89_16w [LY V8] -167 -69 -127 -29
  odb::dbBox_create $ot_v89_16w [LY V8] -69 -69 -29 -29
  odb::dbBox_create $ot_v89_16w [LY V8] 29 -69 69 -29
  odb::dbBox_create $ot_v89_16w [LY V8] 127 -69 167 -29
  odb::dbBox_create $ot_v89_16w [LY V8] 225 -69 265 -29
  odb::dbBox_create $ot_v89_16w [LY V8] -265 29 -225 69
  odb::dbBox_create $ot_v89_16w [LY V8] -167 29 -127 69
  odb::dbBox_create $ot_v89_16w [LY V8] -69 29 -29 69
  odb::dbBox_create $ot_v89_16w [LY V8] 29 29 69 69
  odb::dbBox_create $ot_v89_16w [LY V8] 127 29 167 69
  odb::dbBox_create $ot_v89_16w [LY V8] 225 29 265 69
  odb::dbBox_create $ot_v89_16w [LY V8] -265 127 -225 167
  odb::dbBox_create $ot_v89_16w [LY V8] -167 127 -127 167
  odb::dbBox_create $ot_v89_16w [LY V8] -69 127 -29 167
  odb::dbBox_create $ot_v89_16w [LY V8] 29 127 69 167
  odb::dbBox_create $ot_v89_16w [LY V8] 127 127 167 167
  odb::dbBox_create $ot_v89_16w [LY V8] 225 127 265 167
  odb::dbBox_create $ot_v89_16w [LY V8] -265 225 -225 265
  odb::dbBox_create $ot_v89_16w [LY V8] -167 225 -127 265
  odb::dbBox_create $ot_v89_16w [LY V8] -69 225 -29 265
  odb::dbBox_create $ot_v89_16w [LY V8] 29 225 69 265
  odb::dbBox_create $ot_v89_16w [LY V8] 127 225 167 265
  odb::dbBox_create $ot_v89_16w [LY V8] 225 225 265 265
}
set ot_ndr [$blk findNonDefaultRule ot_mesh_ndr__16w]
set w [rnet root]
$e begin $w
$e newPath [LY M9] FIXED [RL M9]
$e addPoint 2187 10920
$e addBTerm [BT root]
set jt [$e addVia $ot_v89_16w]
$e newPath $jt FIXED [RL M8]
set jhi0 [$e addPoint 10719 10920]
$e newPath $jhi0 FIXED [RL M8]
$e addRect -80 -80 80 80
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
set jtie1 [$e addPoint 10719 10935]
$e newPath $jtie1 FIXED
$e addPoint 10827 10935
$e addRect -16 -36 16 36
set jd1 [$e addTechVia [V VIA67]]
$e newPath $jd1 FIXED
$e addRect -35 -16 35 16
set jd2 [$e addTechVia [V VIA56]]
$e newPath $jd2 FIXED
$e addRect -12 -43 12 43
set jd3 [$e addTechVia [V VIA45]]
$e newPath $jd3 FIXED
$e addRect -43 -12 43 12
set jd4 [$e addTechVia [V VIA34]]
$e newPath $jd4 FIXED
$e addRect -9 -20 9 20
set jd5 [$e addTechVia [V VIA23]]
$e newPath $jd5 FIXED
$e addRect -19 -9 19 9
set jd6 [$e addTechVia [V VIA12]]
$e newPath $jd6 FIXED
$e addITerm [IT ckt_0_0 A]
$e newPath $jtie1 FIXED
set jtu2 [$e addPoint 10719 11205]
$e addPoint 10827 11205
$e addRect -16 -36 16 36
set jd7 [$e addTechVia [V VIA67]]
$e newPath $jd7 FIXED
$e addRect -35 -16 35 16
set jd8 [$e addTechVia [V VIA56]]
$e newPath $jd8 FIXED
$e addRect -12 -43 12 43
set jd9 [$e addTechVia [V VIA45]]
$e newPath $jd9 FIXED
$e addRect -43 -12 43 12
set jd10 [$e addTechVia [V VIA34]]
$e newPath $jd10 FIXED
$e addRect -9 -20 9 20
set jd11 [$e addTechVia [V VIA23]]
$e newPath $jd11 FIXED
$e addRect -19 -9 19 9
set jd12 [$e addTechVia [V VIA12]]
$e newPath $jd12 FIXED
$e addITerm [IT ckt_0_1 A]
$e end
if {[$blk findNonDefaultRule ot_mesh_ndr__4w] == "NULL"} { create_ndr -name ot_mesh_ndr__4w -width {M8 0.16 M9 0.16} -spacing {M8 0.08 M9 0.08} }
set ot_ndr [$blk findNonDefaultRule ot_mesh_ndr__4w]
set w [rnet ckm_w_ckt_0_0]
$e begin $w
$e newPath [LY M1] FIXED
$e addPoint 12393 10935
$e addITerm [IT ckt_0_0 Y]
$e addTechVia [V VIA12]
$e addRect -19 -9 19 9
$e addTechVia [V VIA23]
$e addRect -9 -20 9 20
$e addTechVia [V VIA34]
$e addRect -43 -12 43 12
$e addTechVia [V VIA45]
$e addRect -12 -43 12 43
$e addTechVia [V VIA56]
$e addRect -35 -16 35 16
$e addTechVia [V VIA67]
$e addRect -16 -36 16 36
set jdrv3 [$e addPoint 12285 10935]
$e newPath $jdrv3 FIXED
set jtu4 [$e addPoint 12285 11205]
$e addPoint 11961 11205
$e addRect -16 -36 16 36
set jd13 [$e addTechVia [V VIA67]]
$e newPath $jd13 FIXED
$e addRect -35 -16 35 16
set jd14 [$e addTechVia [V VIA56]]
$e newPath $jd14 FIXED
$e addRect -12 -43 12 43
set jd15 [$e addTechVia [V VIA45]]
$e newPath $jd15 FIXED
$e addRect -43 -12 43 12
set jd16 [$e addTechVia [V VIA34]]
$e newPath $jd16 FIXED
$e addRect -9 -20 9 20
set jd17 [$e addTechVia [V VIA23]]
$e newPath $jd17 FIXED
$e addRect -19 -9 19 9
set jd18 [$e addTechVia [V VIA12]]
$e newPath $jd18 FIXED
$e addITerm [IT ckt_0_1 Y]
$e newPath $jdrv3 FIXED
$e addPoint 12285 13000
set jt [$e addTechVia [V VIA78]]
$e newPath $jt FIXED [RL M8]
$e addRect -80 -80 80 80
$e newPath $jt FIXED [RL M8]
set jhi0 [$e addPoint 60507 13000]
$e newPath $jhi0 FIXED [RL M8]
$e addRect -80 -80 80 80
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
set jtie5 [$e addPoint 60507 11205]
$e newPath $jtie5 FIXED
$e addRect -16 -36 16 36
set jd19 [$e addTechVia [V VIA67]]
$e newPath $jd19 FIXED
$e addRect -35 -16 35 16
set jd20 [$e addTechVia [V VIA56]]
$e newPath $jd20 FIXED
$e addRect -12 -43 12 43
set jd21 [$e addTechVia [V VIA45]]
$e newPath $jd21 FIXED
$e addRect -43 -12 43 12
set jd22 [$e addTechVia [V VIA34]]
$e newPath $jd22 FIXED
$e addRect -9 -20 9 20
set jd23 [$e addTechVia [V VIA23]]
$e newPath $jd23 FIXED
$e addRect -19 -9 19 9
set jd24 [$e addTechVia [V VIA12]]
$e newPath $jd24 FIXED
$e addITerm [IT ckt_1_1 A]
$e newPath $jtie5 FIXED
set jtu6 [$e addPoint 60507 10935]
set jd25 [$e addTechVia [V VIA67]]
$e newPath $jd25 FIXED
$e addRect -35 -16 35 16
set jd26 [$e addTechVia [V VIA56]]
$e newPath $jd26 FIXED
$e addRect -12 -43 12 43
set jd27 [$e addTechVia [V VIA45]]
$e newPath $jd27 FIXED
$e addRect -43 -12 43 12
set jd28 [$e addTechVia [V VIA34]]
$e newPath $jd28 FIXED
$e addRect -9 -20 9 20
set jd29 [$e addTechVia [V VIA23]]
$e newPath $jd29 FIXED
$e addRect -19 -9 19 9
set jd30 [$e addTechVia [V VIA12]]
$e newPath $jd30 FIXED
$e addITerm [IT ckt_1_0 A]
if {[$blk findNonDefaultRule ot_mesh_ndr__8w] == "NULL"} { create_ndr -name ot_mesh_ndr__8w -width {M8 0.32 M9 0.32} -spacing {M8 0.08 M9 0.08} }
set ot_ndr [$blk findNonDefaultRule ot_mesh_ndr__8w]
$e newPath $jdrv3 FIXED
$e addPoint 12285 8760
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED [RL M8]
$e addRect -80 -80 80 80
$e addPoint 12280 8760
set jt [$e addTechVia [V {VIA89}]]
$e newPath $jt FIXED [RL M9]
set jhi0 [$e addPoint 12280 30360]
$e newPath $jhi0 FIXED [RL M9]
set jd31 [$e addTechVia [V {VIA89}]]
$e newPath $jd31 FIXED [RL M8]
$e addPoint 10827 30360 80
$e addRect -80 -80 80 80
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 10827 30375
$e addRect -16 -36 16 36
set jd32 [$e addTechVia [V VIA67]]
$e newPath $jd32 FIXED
$e addRect -35 -16 35 16
set jd33 [$e addTechVia [V VIA56]]
$e newPath $jd33 FIXED
$e addRect -12 -43 12 43
set jd34 [$e addTechVia [V VIA45]]
$e newPath $jd34 FIXED
$e addRect -43 -12 43 12
set jd35 [$e addTechVia [V VIA34]]
$e newPath $jd35 FIXED
$e addRect -9 -20 9 20
set jd36 [$e addTechVia [V VIA23]]
$e newPath $jd36 FIXED
$e addRect -19 -9 19 9
set jd37 [$e addTechVia [V VIA12]]
$e newPath $jd37 FIXED
$e addITerm [IT ckt_3_0 A]
$e end
set ot_ndr [$blk findNonDefaultRule ot_mesh_ndr__16w]
set w [rnet ckm_w_ckt_1_0]
$e begin $w
$e newPath [LY M1] FIXED
$e addPoint 62073 10935
$e addITerm [IT ckt_1_0 Y]
$e addTechVia [V VIA12]
$e addRect -19 -9 19 9
$e addTechVia [V VIA23]
$e addRect -9 -20 9 20
$e addTechVia [V VIA34]
$e addRect -43 -12 43 12
$e addTechVia [V VIA45]
$e addRect -12 -43 12 43
$e addTechVia [V VIA56]
$e addRect -35 -16 35 16
set jdrv7 [$e addTechVia [V VIA67]]
$e newPath $jdrv7 FIXED
set jtu8 [$e addPoint 62073 11205]
set jd38 [$e addTechVia [V VIA67]]
$e newPath $jd38 FIXED
$e addRect -35 -16 35 16
set jd39 [$e addTechVia [V VIA56]]
$e newPath $jd39 FIXED
$e addRect -12 -43 12 43
set jd40 [$e addTechVia [V VIA45]]
$e newPath $jd40 FIXED
$e addRect -43 -12 43 12
set jd41 [$e addTechVia [V VIA34]]
$e newPath $jd41 FIXED
$e addRect -9 -20 9 20
set jd42 [$e addTechVia [V VIA23]]
$e newPath $jd42 FIXED
$e addRect -19 -9 19 9
set jd43 [$e addTechVia [V VIA12]]
$e newPath $jd43 FIXED
$e addITerm [IT ckt_1_1 Y]
$e newPath $jdrv7 FIXED
$e addPoint 62073 10920
set jt [$e addTechVia [V VIA78]]
$e newPath $jt FIXED [RL M8]
$e addRect -80 -80 80 80
$e newPath $jt FIXED [RL M8]
set jhi0 [$e addPoint 120440 10920]
$e newPath $jhi0 FIXED [RL M8]
$e addVia $ot_v89_16w
$e addPoint 120440 6920
set jd44 [$e addVia $ot_v89_16w]
$e newPath $jd44 FIXED [RL M8]
$e addPoint 120447 6920
$e addRect -80 -80 80 80
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 120447 6885
$e addRect -16 -36 16 36
set jd45 [$e addTechVia [V VIA67]]
$e newPath $jd45 FIXED
$e addRect -35 -16 35 16
set jd46 [$e addTechVia [V VIA56]]
$e newPath $jd46 FIXED
$e addRect -12 -43 12 43
set jd47 [$e addTechVia [V VIA45]]
$e newPath $jd47 FIXED
$e addRect -43 -12 43 12
set jd48 [$e addTechVia [V VIA34]]
$e newPath $jd48 FIXED
$e addRect -9 -20 9 20
set jd49 [$e addTechVia [V VIA23]]
$e newPath $jd49 FIXED
$e addRect -19 -9 19 9
set jd50 [$e addTechVia [V VIA12]]
$e newPath $jd50 FIXED
$e addITerm [IT ckt_2_0 A]
$e end
set ot_ndr [$blk findNonDefaultRule ot_mesh_ndr__16w]
set w [rnet t_g3]
$e begin $w
$e newPath [LY M1] FIXED
$e addPoint 12393 30375
$e addITerm [IT ckt_3_0 Y]
$e addTechVia [V VIA12]
$e addRect -19 -9 19 9
$e addTechVia [V VIA23]
$e addRect -9 -20 9 20
$e addTechVia [V VIA34]
$e addRect -43 -12 43 12
$e addTechVia [V VIA45]
$e addRect -12 -43 12 43
$e addTechVia [V VIA56]
$e addRect -35 -16 35 16
set jdrv9 [$e addTechVia [V VIA67]]
$e newPath $jdrv9 FIXED
$e addPoint 12393 32520
set jt [$e addTechVia [V VIA78]]
$e newPath $jt FIXED [RL M8]
$e addRect -80 -80 80 80
$e newPath $jt FIXED [RL M8]
set jhi0 [$e addPoint 21033 32520]
$e addBTerm [BT t_g3]
$e end
set ot_ndr [$blk findNonDefaultRule ot_mesh_ndr__16w]
set w [rnet t_g2]
$e begin $w
$e newPath [LY M1] FIXED
$e addPoint 122013 6885
$e addITerm [IT ckt_2_0 Y]
$e addTechVia [V VIA12]
$e addRect -19 -9 19 9
$e addTechVia [V VIA23]
$e addRect -9 -20 9 20
$e addTechVia [V VIA34]
$e addRect -43 -12 43 12
$e addTechVia [V VIA45]
$e addRect -12 -43 12 43
$e addTechVia [V VIA56]
$e addRect -35 -16 35 16
set jdrv10 [$e addTechVia [V VIA67]]
$e newPath $jdrv10 FIXED
$e addPoint 122013 4600
set jt [$e addTechVia [V VIA78]]
$e newPath $jt FIXED [RL M8]
$e addRect -80 -80 80 80
$e newPath $jt FIXED [RL M8]
set jhi0 [$e addPoint 130653 4600]
$e addBTerm [BT t_g2]
$e end
puts "OT_ROUTED_CLOCK nets 5 pin_stairs 8 port_joins 3"
write_db /w/encoded.odb
puts V2_ENCODER_DONE
