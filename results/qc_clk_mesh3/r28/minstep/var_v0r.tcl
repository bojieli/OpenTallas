read_db /tree/routed.odb
set blk [ord::get_db_block]; set tech [ord::get_db_tech]
foreach l {M1 M2 M3} { set tg [$blk findTrackGrid [$tech findLayer $l]]; if {$tg != "NULL"} { odb::dbTrackGrid_destroy $tg } }
make_tracks M1 -x_offset 0.009 -x_pitch 0.036 -y_offset 0.009 -y_pitch 0.036
foreach yo {0.045 0.081 0.117 0.153 0.189 0.225 0.270} { make_tracks M2 -x_offset 0.009 -x_pitch 0.036 -y_offset $yo -y_pitch 0.270 }
make_tracks M3 -x_offset 0.009 -x_pitch 0.036 -y_offset 0.009 -y_pitch 0.036
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

set w [rnet ckm_w_ckt_17717_0]
$e begin $w
$e newPath [LY M1] FIXED
$e addPoint 2200959 11050695
$e addITerm [IT ckt_17717_0 Y]
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
set jtie5835 [$e addTechVia [V VIA67]]
$e newPath $jtie5835 FIXED
$e addPoint 2200959 11049320
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED [RL M8]
$e addRect -80 -80 80 80
$e addPoint 2204440 11049320
set jt [$e addVia $ot_v89]
$e newPath $jtie5835 FIXED
set jtu5836 [$e addPoint 2200959 11050965]
set jd28116 [$e addTechVia [V VIA67]]
$e newPath $jd28116 FIXED
$e addRect -35 -16 35 16
set jd28117 [$e addTechVia [V VIA56]]
$e newPath $jd28117 FIXED
$e addRect -12 -43 12 43
set jd28118 [$e addTechVia [V VIA45]]
$e newPath $jd28118 FIXED
$e addRect -43 -12 43 12
set jd28119 [$e addTechVia [V VIA34]]
$e newPath $jd28119 FIXED
$e addRect -9 -20 9 20
set jd28120 [$e addTechVia [V VIA23]]
$e newPath $jd28120 FIXED
$e addRect -19 -9 19 9
set jd28121 [$e addTechVia [V VIA12]]
$e newPath $jd28121 FIXED
$e addITerm [IT ckt_17717_1 Y]
$e newPath $jt FIXED [RL M9]
set jlo0 [$e addPoint 2204440 10749240]
$e newPath $jlo0 FIXED [RL M9]
set jd28122 [$e addVia $ot_v89]
$e newPath $jd28122 FIXED [RL M8]
$e addPoint 2204253 10749240 80
$e addRect -80 -80 80 80
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
set jtie5837 [$e addPoint 2204253 10748565]
$e newPath $jtie5837 FIXED
$e addRect -16 -36 16 36
set jd28123 [$e addTechVia [V VIA67]]
$e newPath $jd28123 FIXED
$e addRect -35 -16 35 16
set jd28124 [$e addTechVia [V VIA56]]
$e newPath $jd28124 FIXED
$e addRect -12 -43 12 43
set jd28125 [$e addTechVia [V VIA45]]
$e newPath $jd28125 FIXED
$e addRect -43 -12 43 12
set jd28126 [$e addTechVia [V VIA34]]
$e newPath $jd28126 FIXED
$e addRect -9 -20 9 20
set jd28127 [$e addTechVia [V VIA23]]
$e newPath $jd28127 FIXED
$e addRect -19 -9 19 9
set jd28128 [$e addTechVia [V VIA12]]
$e newPath $jd28128 FIXED
$e addITerm [IT ckt_17718_1 A]
$e newPath $jtie5837 FIXED
set jtu5838 [$e addPoint 2204253 10748295]
set jd28129 [$e addTechVia [V VIA67]]
$e newPath $jd28129 FIXED
$e addRect -35 -16 35 16
set jd28130 [$e addTechVia [V VIA56]]
$e newPath $jd28130 FIXED
$e addRect -12 -43 12 43
set jd28131 [$e addTechVia [V VIA45]]
$e newPath $jd28131 FIXED
$e addRect -43 -12 43 12
set jd28132 [$e addTechVia [V VIA34]]
$e newPath $jd28132 FIXED
$e addRect -9 -20 9 20
set jd28133 [$e addTechVia [V VIA23]]
$e newPath $jd28133 FIXED
$e addRect -19 -9 19 9
set jd28134 [$e addTechVia [V VIA12]]
$e newPath $jd28134 FIXED
$e addITerm [IT ckt_17718_0 A]
$e end

drt::check_drc -box {2203000 10748000 2205500 10750500} -output_file /out/v0r.rpt
puts DONE_v0r
