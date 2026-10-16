# Place a scalar BTerm at a GRANTED along-face centre, without place_pin's
# coordinate/shape-offset snapping. The caller must supply a legal actual
# routing-track centre. This helper never changes or repairs a grant.
#
# Usage: source this file, then
#   ot_assigned_pin_exact {data[0]} M5 N 178.188
# Face is N/S/E/W and centre is microns along X for N/S, Y for E/W.
# Existing legal pin dimensions are preserved. For an unplaced BTerm only,
# place_pin seeds its ordinary dimensions; its resulting location is discarded.
# PG BTerms are never removed. The enclosing kit must audit signal spacing,
# PG clearance, all assigned centres and complete port coverage after placement.
proc ot_assigned_pin_exact {name layer face center_um} {
    if {$face ni {N S E W}} {error "ASSIGNED_PIN_EXACT invalid face $face"}
    set block [ord::get_db_block]
    set tech [ord::get_db_tech]
    set units [$block getDbUnitsPerMicron]
    set bt [$block findBTerm $name]
    if {$bt eq "" || $bt eq "NULL"} {error "ASSIGNED_PIN_EXACT missing BTerm $name"}
    if {[$bt getSigType] in {POWER GROUND}} {error "ASSIGNED_PIN_EXACT refuses PG BTerm $name"}
    set tl [$tech findLayer $layer]
    if {$tl eq "" || $tl eq "NULL"} {error "ASSIGNED_PIN_EXACT missing layer $layer"}
    set grid [$block findTrackGrid $tl]
    if {$grid eq "" || $grid eq "NULL"} {error "ASSIGNED_PIN_EXACT no actual track grid for $layer"}
    set tracks [expr {$face in {N S}?[$grid getGridX]:[$grid getGridY]}]
    set target [expr {double($center_um)*$units}]
    set target_int [expr {int(round($target))}]
    if {abs($target-$target_int)>0.0001 || [lsearch -exact $tracks $target_int]<0} {
        error "ASSIGNED_PIN_EXACT $name grant $center_um is not on actual $layer $face track"
    }
    set die [$block getDieArea]
    set lo [expr {$face in {N S}?[$die xMin]:[$die yMin]}]
    set hi [expr {$face in {N S}?[$die xMax]:[$die yMax]}]
    if {$target<=$lo || $target>=$hi} {error "ASSIGNED_PIN_EXACT $name outside face extent"}
    set seeded [expr {[llength [$bt getBPins]]==0}]
    if {$seeded} {
        set x [expr {$face eq "W"?[$die xMin]/double($units):($face eq "E"?[$die xMax]/double($units):$center_um)}]
        set y [expr {$face eq "S"?[$die yMin]/double($units):($face eq "N"?[$die yMax]/double($units):$center_um)}]
        place_pin -pin_name $name -layer $layer -location [list $x $y] -force_to_die_boundary
    }
    set pins [$bt getBPins]
    if {[llength $pins]!=1 || [llength [[lindex $pins 0] getBoxes]]!=1} {
        error "ASSIGNED_PIN_EXACT $name needs one ordinary rectangular seed pin"
    }
    set old [lindex [[lindex $pins 0] getBoxes] 0]
    set seed_center [expr {$face in {N S}?([$old xMin]+[$old xMax])/2.0:([$old yMin]+[$old yMax])/2.0}]
    if {[[$old getTechLayer] getName] ne $layer} {error "ASSIGNED_PIN_EXACT $name seed layer differs from grant"}
    set width [expr {[$old xMax]-[$old xMin]}]
    set height [expr {[$old yMax]-[$old yMin]}]
    if {$face in {N S}} {
        set x0 [expr {$target-$width/2.0}]
        set y0 [expr {$face eq "S"?[$die yMin]:[$die yMax]-$height}]
    } else {
        set x0 [expr {$face eq "W"?[$die xMin]:[$die xMax]-$width}]
        set y0 [expr {$target-$height/2.0}]
    }
    if {abs($x0-round($x0))>0.0001 || abs($y0-round($y0))>0.0001} {
        error "ASSIGNED_PIN_EXACT $name seed shape cannot be centred exactly on granted DBU coordinate"
    }
    set x0 [expr {int(round($x0))}];set y0 [expr {int(round($y0))}]
    foreach bp $pins {odb::dbBPin_destroy $bp}
    set pin [odb::dbBPin_create $bt]
    $pin setPlacementStatus FIRM
    odb::dbBox_create $pin $tl $x0 $y0 [expr {$x0+$width}] [expr {$y0+$height}]
    set actual [lindex [[lindex [$bt getBPins] 0] getBoxes] 0]
    set got [expr {$face in {N S}?([$actual xMin]+[$actual xMax])/2.0:([$actual yMin]+[$actual yMax])/2.0}]
    if {abs($got-$target)>0.0001 || [[$actual getTechLayer] getName] ne $layer ||
        [$actual xMax]-[$actual xMin]!=$width || [$actual yMax]-[$actual yMin]!=$height} {
        error "ASSIGNED_PIN_EXACT actual ODB rectangle differs from grant for $name"
    }
    return [dict create pin $name face $face layer $layer center_um [expr {$got/double($units)}] width_dbu $width height_dbu $height seeded $seeded seed_center_um [expr {$seed_center/double($units)}]]
}
ot_assigned_pin_exact {active} M5 S 13.020
ot_assigned_pin_exact {bank_client[0]} M4 E 29.148
ot_assigned_pin_exact {bank_client[10]} M4 E 30.108
ot_assigned_pin_exact {bank_client[11]} M4 E 30.204
ot_assigned_pin_exact {bank_client[12]} M4 E 30.300
ot_assigned_pin_exact {bank_client[13]} M4 E 30.396
ot_assigned_pin_exact {bank_client[14]} M4 E 30.492
ot_assigned_pin_exact {bank_client[15]} M4 E 30.588
ot_assigned_pin_exact {bank_client[16]} M4 E 30.684
ot_assigned_pin_exact {bank_client[17]} M4 E 30.780
ot_assigned_pin_exact {bank_client[18]} M4 E 30.876
ot_assigned_pin_exact {bank_client[19]} M4 E 30.972
ot_assigned_pin_exact {bank_client[1]} M4 E 29.244
ot_assigned_pin_exact {bank_client[20]} M4 E 31.068
ot_assigned_pin_exact {bank_client[21]} M4 E 31.164
ot_assigned_pin_exact {bank_client[22]} M4 E 31.260
ot_assigned_pin_exact {bank_client[23]} M4 E 31.356
ot_assigned_pin_exact {bank_client[2]} M4 E 29.340
ot_assigned_pin_exact {bank_client[3]} M4 E 29.436
ot_assigned_pin_exact {bank_client[4]} M4 E 29.532
ot_assigned_pin_exact {bank_client[5]} M4 E 29.628
ot_assigned_pin_exact {bank_client[6]} M4 E 29.724
ot_assigned_pin_exact {bank_client[7]} M4 E 29.820
ot_assigned_pin_exact {bank_client[8]} M4 E 29.916
ot_assigned_pin_exact {bank_client[9]} M4 E 30.012
ot_assigned_pin_exact {bank_enable[0]} M4 E 31.452
ot_assigned_pin_exact {bank_enable[1]} M4 E 31.548
ot_assigned_pin_exact {bank_enable[2]} M4 E 31.644
ot_assigned_pin_exact {bank_enable[3]} M4 E 31.740
ot_assigned_pin_exact {bank_enable[4]} M4 E 31.836
ot_assigned_pin_exact {bank_enable[5]} M4 E 31.932
ot_assigned_pin_exact {bank_enable[6]} M4 E 32.028
ot_assigned_pin_exact {bank_enable[7]} M4 E 32.124
ot_assigned_pin_exact {calendar_v} M5 S 13.116
ot_assigned_pin_exact {cfg_addr[0]} M4 W 46.044
ot_assigned_pin_exact {cfg_addr[10]} M4 W 47.004
ot_assigned_pin_exact {cfg_addr[11]} M4 W 47.100
ot_assigned_pin_exact {cfg_addr[1]} M4 W 46.140
ot_assigned_pin_exact {cfg_addr[2]} M4 W 46.236
ot_assigned_pin_exact {cfg_addr[3]} M4 W 46.332
ot_assigned_pin_exact {cfg_addr[4]} M4 W 46.428
ot_assigned_pin_exact {cfg_addr[5]} M4 W 46.524
ot_assigned_pin_exact {cfg_addr[6]} M4 W 46.620
ot_assigned_pin_exact {cfg_addr[7]} M4 W 46.716
ot_assigned_pin_exact {cfg_addr[8]} M4 W 46.812
ot_assigned_pin_exact {cfg_addr[9]} M4 W 46.908
ot_assigned_pin_exact {cfg_data[0]} M4 W 47.196
ot_assigned_pin_exact {cfg_data[100]} M4 W 63.708
ot_assigned_pin_exact {cfg_data[101]} M4 W 63.804
ot_assigned_pin_exact {cfg_data[102]} M4 W 63.900
ot_assigned_pin_exact {cfg_data[103]} M4 W 63.996
ot_assigned_pin_exact {cfg_data[104]} M4 W 64.092
ot_assigned_pin_exact {cfg_data[105]} M4 W 64.188
ot_assigned_pin_exact {cfg_data[106]} M4 W 64.284
ot_assigned_pin_exact {cfg_data[107]} M4 W 64.380
ot_assigned_pin_exact {cfg_data[108]} M4 W 64.476
ot_assigned_pin_exact {cfg_data[109]} M4 W 64.572
ot_assigned_pin_exact {cfg_data[10]} M4 W 48.156
ot_assigned_pin_exact {cfg_data[110]} M4 W 64.668
ot_assigned_pin_exact {cfg_data[111]} M4 W 64.764
ot_assigned_pin_exact {cfg_data[112]} M4 W 64.860
ot_assigned_pin_exact {cfg_data[113]} M4 W 64.956
ot_assigned_pin_exact {cfg_data[114]} M4 W 65.052
ot_assigned_pin_exact {cfg_data[115]} M4 W 65.148
ot_assigned_pin_exact {cfg_data[116]} M4 W 65.244
ot_assigned_pin_exact {cfg_data[117]} M4 W 65.340
ot_assigned_pin_exact {cfg_data[118]} M4 W 65.436
ot_assigned_pin_exact {cfg_data[119]} M4 W 65.532
ot_assigned_pin_exact {cfg_data[11]} M4 W 48.252
ot_assigned_pin_exact {cfg_data[120]} M4 W 65.628
ot_assigned_pin_exact {cfg_data[121]} M4 W 65.724
ot_assigned_pin_exact {cfg_data[122]} M4 W 65.820
ot_assigned_pin_exact {cfg_data[123]} M4 W 65.916
ot_assigned_pin_exact {cfg_data[124]} M4 W 66.012
ot_assigned_pin_exact {cfg_data[125]} M4 W 66.108
ot_assigned_pin_exact {cfg_data[126]} M4 W 66.204
ot_assigned_pin_exact {cfg_data[127]} M4 W 66.300
ot_assigned_pin_exact {cfg_data[128]} M4 W 66.396
ot_assigned_pin_exact {cfg_data[129]} M4 W 66.492
ot_assigned_pin_exact {cfg_data[12]} M4 W 48.348
ot_assigned_pin_exact {cfg_data[130]} M4 W 66.588
ot_assigned_pin_exact {cfg_data[131]} M4 W 66.684
ot_assigned_pin_exact {cfg_data[132]} M4 W 66.780
ot_assigned_pin_exact {cfg_data[133]} M4 W 66.876
ot_assigned_pin_exact {cfg_data[134]} M4 W 66.972
ot_assigned_pin_exact {cfg_data[135]} M4 W 67.068
ot_assigned_pin_exact {cfg_data[136]} M4 W 67.164
ot_assigned_pin_exact {cfg_data[137]} M4 W 67.260
ot_assigned_pin_exact {cfg_data[138]} M4 W 67.356
ot_assigned_pin_exact {cfg_data[139]} M4 W 67.452
ot_assigned_pin_exact {cfg_data[13]} M4 W 48.444
ot_assigned_pin_exact {cfg_data[140]} M4 W 67.548
ot_assigned_pin_exact {cfg_data[141]} M4 W 67.644
ot_assigned_pin_exact {cfg_data[142]} M4 W 67.740
ot_assigned_pin_exact {cfg_data[143]} M4 W 67.836
ot_assigned_pin_exact {cfg_data[144]} M4 W 67.932
ot_assigned_pin_exact {cfg_data[145]} M4 W 68.028
ot_assigned_pin_exact {cfg_data[146]} M4 W 68.124
ot_assigned_pin_exact {cfg_data[147]} M4 W 68.220
ot_assigned_pin_exact {cfg_data[148]} M4 W 26.844
ot_assigned_pin_exact {cfg_data[149]} M4 W 26.940
ot_assigned_pin_exact {cfg_data[14]} M4 W 48.540
ot_assigned_pin_exact {cfg_data[150]} M4 W 27.036
ot_assigned_pin_exact {cfg_data[151]} M4 W 27.132
ot_assigned_pin_exact {cfg_data[152]} M4 W 27.228
ot_assigned_pin_exact {cfg_data[153]} M4 W 27.324
ot_assigned_pin_exact {cfg_data[154]} M4 W 27.420
ot_assigned_pin_exact {cfg_data[155]} M4 W 27.516
ot_assigned_pin_exact {cfg_data[156]} M4 W 27.612
ot_assigned_pin_exact {cfg_data[157]} M4 W 27.708
ot_assigned_pin_exact {cfg_data[158]} M4 W 27.804
ot_assigned_pin_exact {cfg_data[159]} M4 W 27.900
ot_assigned_pin_exact {cfg_data[15]} M4 W 48.636
ot_assigned_pin_exact {cfg_data[160]} M4 W 27.996
ot_assigned_pin_exact {cfg_data[161]} M4 W 28.092
ot_assigned_pin_exact {cfg_data[162]} M4 W 28.188
ot_assigned_pin_exact {cfg_data[163]} M4 W 28.284
ot_assigned_pin_exact {cfg_data[164]} M4 W 28.380
ot_assigned_pin_exact {cfg_data[165]} M4 W 28.476
ot_assigned_pin_exact {cfg_data[166]} M4 W 28.572
ot_assigned_pin_exact {cfg_data[167]} M4 W 28.668
ot_assigned_pin_exact {cfg_data[168]} M4 W 28.764
ot_assigned_pin_exact {cfg_data[169]} M4 W 28.860
ot_assigned_pin_exact {cfg_data[16]} M4 W 48.732
ot_assigned_pin_exact {cfg_data[170]} M4 W 28.956
ot_assigned_pin_exact {cfg_data[171]} M4 W 29.052
ot_assigned_pin_exact {cfg_data[172]} M4 W 29.148
ot_assigned_pin_exact {cfg_data[173]} M4 W 29.244
ot_assigned_pin_exact {cfg_data[174]} M4 W 29.340
ot_assigned_pin_exact {cfg_data[175]} M4 W 29.436
ot_assigned_pin_exact {cfg_data[176]} M4 W 29.532
ot_assigned_pin_exact {cfg_data[177]} M4 W 29.628
ot_assigned_pin_exact {cfg_data[178]} M4 W 29.724
ot_assigned_pin_exact {cfg_data[179]} M4 W 29.820
ot_assigned_pin_exact {cfg_data[17]} M4 W 48.828
ot_assigned_pin_exact {cfg_data[180]} M4 W 39.900
ot_assigned_pin_exact {cfg_data[181]} M4 W 39.996
ot_assigned_pin_exact {cfg_data[182]} M4 W 40.092
ot_assigned_pin_exact {cfg_data[183]} M4 W 40.188
ot_assigned_pin_exact {cfg_data[184]} M4 W 40.284
ot_assigned_pin_exact {cfg_data[185]} M4 W 40.380
ot_assigned_pin_exact {cfg_data[186]} M4 W 40.476
ot_assigned_pin_exact {cfg_data[187]} M4 W 40.572
ot_assigned_pin_exact {cfg_data[188]} M4 W 40.668
ot_assigned_pin_exact {cfg_data[189]} M4 W 40.764
ot_assigned_pin_exact {cfg_data[18]} M4 W 48.924
ot_assigned_pin_exact {cfg_data[190]} M4 W 40.860
ot_assigned_pin_exact {cfg_data[191]} M4 W 40.956
ot_assigned_pin_exact {cfg_data[192]} M4 W 41.052
ot_assigned_pin_exact {cfg_data[193]} M4 W 41.148
ot_assigned_pin_exact {cfg_data[194]} M4 W 41.244
ot_assigned_pin_exact {cfg_data[195]} M4 W 41.340
ot_assigned_pin_exact {cfg_data[196]} M4 W 41.436
ot_assigned_pin_exact {cfg_data[197]} M4 W 41.532
ot_assigned_pin_exact {cfg_data[198]} M4 W 41.628
ot_assigned_pin_exact {cfg_data[199]} M4 W 41.724
ot_assigned_pin_exact {cfg_data[19]} M4 W 49.020
ot_assigned_pin_exact {cfg_data[1]} M4 W 47.292
ot_assigned_pin_exact {cfg_data[200]} M4 W 41.820
ot_assigned_pin_exact {cfg_data[201]} M4 W 41.916
ot_assigned_pin_exact {cfg_data[202]} M4 W 42.012
ot_assigned_pin_exact {cfg_data[203]} M4 W 42.108
ot_assigned_pin_exact {cfg_data[204]} M4 W 42.204
ot_assigned_pin_exact {cfg_data[205]} M4 W 42.300
ot_assigned_pin_exact {cfg_data[206]} M4 W 42.396
ot_assigned_pin_exact {cfg_data[207]} M4 W 42.492
ot_assigned_pin_exact {cfg_data[208]} M4 W 42.588
ot_assigned_pin_exact {cfg_data[209]} M4 W 42.684
ot_assigned_pin_exact {cfg_data[20]} M4 W 55.260
ot_assigned_pin_exact {cfg_data[210]} M4 W 42.780
ot_assigned_pin_exact {cfg_data[211]} M4 W 42.876
ot_assigned_pin_exact {cfg_data[212]} M4 W 20.700
ot_assigned_pin_exact {cfg_data[213]} M4 W 20.796
ot_assigned_pin_exact {cfg_data[214]} M4 W 20.892
ot_assigned_pin_exact {cfg_data[215]} M4 W 20.988
ot_assigned_pin_exact {cfg_data[216]} M4 W 21.084
ot_assigned_pin_exact {cfg_data[217]} M4 W 21.180
ot_assigned_pin_exact {cfg_data[218]} M4 W 21.276
ot_assigned_pin_exact {cfg_data[219]} M4 W 21.372
ot_assigned_pin_exact {cfg_data[21]} M4 W 55.356
ot_assigned_pin_exact {cfg_data[220]} M4 W 21.468
ot_assigned_pin_exact {cfg_data[221]} M4 W 21.564
ot_assigned_pin_exact {cfg_data[222]} M4 W 21.660
ot_assigned_pin_exact {cfg_data[223]} M4 W 21.756
ot_assigned_pin_exact {cfg_data[224]} M4 W 21.852
ot_assigned_pin_exact {cfg_data[225]} M4 W 21.948
ot_assigned_pin_exact {cfg_data[226]} M4 W 22.044
ot_assigned_pin_exact {cfg_data[227]} M4 W 22.140
ot_assigned_pin_exact {cfg_data[228]} M4 W 22.236
ot_assigned_pin_exact {cfg_data[229]} M4 W 22.332
ot_assigned_pin_exact {cfg_data[22]} M4 W 55.452
ot_assigned_pin_exact {cfg_data[230]} M4 W 22.428
ot_assigned_pin_exact {cfg_data[231]} M4 W 22.524
ot_assigned_pin_exact {cfg_data[232]} M4 W 22.620
ot_assigned_pin_exact {cfg_data[233]} M4 W 22.716
ot_assigned_pin_exact {cfg_data[234]} M4 W 22.812
ot_assigned_pin_exact {cfg_data[235]} M4 W 22.908
ot_assigned_pin_exact {cfg_data[236]} M4 W 23.004
ot_assigned_pin_exact {cfg_data[237]} M4 W 23.100
ot_assigned_pin_exact {cfg_data[238]} M4 W 23.196
ot_assigned_pin_exact {cfg_data[239]} M4 W 23.292
ot_assigned_pin_exact {cfg_data[23]} M4 W 55.548
ot_assigned_pin_exact {cfg_data[240]} M4 W 23.388
ot_assigned_pin_exact {cfg_data[241]} M4 W 23.484
ot_assigned_pin_exact {cfg_data[242]} M4 W 23.580
ot_assigned_pin_exact {cfg_data[243]} M4 W 23.676
ot_assigned_pin_exact {cfg_data[244]} M4 W 16.860
ot_assigned_pin_exact {cfg_data[245]} M4 W 16.956
ot_assigned_pin_exact {cfg_data[246]} M4 W 17.052
ot_assigned_pin_exact {cfg_data[247]} M4 W 17.148
ot_assigned_pin_exact {cfg_data[248]} M4 W 17.244
ot_assigned_pin_exact {cfg_data[249]} M4 W 17.340
ot_assigned_pin_exact {cfg_data[24]} M4 W 55.644
ot_assigned_pin_exact {cfg_data[250]} M4 W 17.436
ot_assigned_pin_exact {cfg_data[251]} M4 W 17.532
ot_assigned_pin_exact {cfg_data[252]} M4 W 17.628
ot_assigned_pin_exact {cfg_data[253]} M4 W 17.724
ot_assigned_pin_exact {cfg_data[254]} M4 W 17.820
ot_assigned_pin_exact {cfg_data[255]} M4 W 17.916
ot_assigned_pin_exact {cfg_data[25]} M4 W 55.740
ot_assigned_pin_exact {cfg_data[26]} M4 W 55.836
ot_assigned_pin_exact {cfg_data[27]} M4 W 55.932
ot_assigned_pin_exact {cfg_data[28]} M4 W 56.028
ot_assigned_pin_exact {cfg_data[29]} M4 W 56.124
ot_assigned_pin_exact {cfg_data[2]} M4 W 47.388
ot_assigned_pin_exact {cfg_data[30]} M4 W 56.220
ot_assigned_pin_exact {cfg_data[31]} M4 W 56.316
ot_assigned_pin_exact {cfg_data[32]} M4 W 56.412
ot_assigned_pin_exact {cfg_data[33]} M4 W 56.508
ot_assigned_pin_exact {cfg_data[34]} M4 W 56.604
ot_assigned_pin_exact {cfg_data[35]} M4 W 56.700
ot_assigned_pin_exact {cfg_data[36]} M4 W 56.796
ot_assigned_pin_exact {cfg_data[37]} M4 W 56.892
ot_assigned_pin_exact {cfg_data[38]} M4 W 56.988
ot_assigned_pin_exact {cfg_data[39]} M4 W 57.084
ot_assigned_pin_exact {cfg_data[3]} M4 W 47.484
ot_assigned_pin_exact {cfg_data[40]} M4 W 57.180
ot_assigned_pin_exact {cfg_data[41]} M4 W 57.276
ot_assigned_pin_exact {cfg_data[42]} M4 W 57.372
ot_assigned_pin_exact {cfg_data[43]} M4 W 57.468
ot_assigned_pin_exact {cfg_data[44]} M4 W 57.564
ot_assigned_pin_exact {cfg_data[45]} M4 W 57.660
ot_assigned_pin_exact {cfg_data[46]} M4 W 57.756
ot_assigned_pin_exact {cfg_data[47]} M4 W 57.852
ot_assigned_pin_exact {cfg_data[48]} M4 W 57.948
ot_assigned_pin_exact {cfg_data[49]} M4 W 58.044
ot_assigned_pin_exact {cfg_data[4]} M4 W 47.580
ot_assigned_pin_exact {cfg_data[50]} M4 W 58.140
ot_assigned_pin_exact {cfg_data[51]} M4 W 58.236
ot_assigned_pin_exact {cfg_data[52]} M4 W 59.100
ot_assigned_pin_exact {cfg_data[53]} M4 W 59.196
ot_assigned_pin_exact {cfg_data[54]} M4 W 59.292
ot_assigned_pin_exact {cfg_data[55]} M4 W 59.388
ot_assigned_pin_exact {cfg_data[56]} M4 W 59.484
ot_assigned_pin_exact {cfg_data[57]} M4 W 59.580
ot_assigned_pin_exact {cfg_data[58]} M4 W 59.676
ot_assigned_pin_exact {cfg_data[59]} M4 W 59.772
ot_assigned_pin_exact {cfg_data[5]} M4 W 47.676
ot_assigned_pin_exact {cfg_data[60]} M4 W 59.868
ot_assigned_pin_exact {cfg_data[61]} M4 W 59.964
ot_assigned_pin_exact {cfg_data[62]} M4 W 60.060
ot_assigned_pin_exact {cfg_data[63]} M4 W 60.156
ot_assigned_pin_exact {cfg_data[64]} M4 W 60.252
ot_assigned_pin_exact {cfg_data[65]} M4 W 60.348
ot_assigned_pin_exact {cfg_data[66]} M4 W 60.444
ot_assigned_pin_exact {cfg_data[67]} M4 W 60.540
ot_assigned_pin_exact {cfg_data[68]} M4 W 60.636
ot_assigned_pin_exact {cfg_data[69]} M4 W 60.732
ot_assigned_pin_exact {cfg_data[6]} M4 W 47.772
ot_assigned_pin_exact {cfg_data[70]} M4 W 60.828
ot_assigned_pin_exact {cfg_data[71]} M4 W 60.924
ot_assigned_pin_exact {cfg_data[72]} M4 W 61.020
ot_assigned_pin_exact {cfg_data[73]} M4 W 61.116
ot_assigned_pin_exact {cfg_data[74]} M4 W 61.212
ot_assigned_pin_exact {cfg_data[75]} M4 W 61.308
ot_assigned_pin_exact {cfg_data[76]} M4 W 61.404
ot_assigned_pin_exact {cfg_data[77]} M4 W 61.500
ot_assigned_pin_exact {cfg_data[78]} M4 W 61.596
ot_assigned_pin_exact {cfg_data[79]} M4 W 61.692
ot_assigned_pin_exact {cfg_data[7]} M4 W 47.868
ot_assigned_pin_exact {cfg_data[80]} M4 W 61.788
ot_assigned_pin_exact {cfg_data[81]} M4 W 61.884
ot_assigned_pin_exact {cfg_data[82]} M4 W 61.980
ot_assigned_pin_exact {cfg_data[83]} M4 W 62.076
ot_assigned_pin_exact {cfg_data[84]} M4 W 62.172
ot_assigned_pin_exact {cfg_data[85]} M4 W 62.268
ot_assigned_pin_exact {cfg_data[86]} M4 W 62.364
ot_assigned_pin_exact {cfg_data[87]} M4 W 62.460
ot_assigned_pin_exact {cfg_data[88]} M4 W 62.556
ot_assigned_pin_exact {cfg_data[89]} M4 W 62.652
ot_assigned_pin_exact {cfg_data[8]} M4 W 47.964
ot_assigned_pin_exact {cfg_data[90]} M4 W 62.748
ot_assigned_pin_exact {cfg_data[91]} M4 W 62.844
ot_assigned_pin_exact {cfg_data[92]} M4 W 62.940
ot_assigned_pin_exact {cfg_data[93]} M4 W 63.036
ot_assigned_pin_exact {cfg_data[94]} M4 W 63.132
ot_assigned_pin_exact {cfg_data[95]} M4 W 63.228
ot_assigned_pin_exact {cfg_data[96]} M4 W 63.324
ot_assigned_pin_exact {cfg_data[97]} M4 W 63.420
ot_assigned_pin_exact {cfg_data[98]} M4 W 63.516
ot_assigned_pin_exact {cfg_data[99]} M4 W 63.612
ot_assigned_pin_exact {cfg_data[9]} M4 W 48.060
ot_assigned_pin_exact {cfg_target[0]} M4 W 18.012
ot_assigned_pin_exact {cfg_target[1]} M4 W 18.108
ot_assigned_pin_exact {cfg_target[2]} M4 W 18.204
ot_assigned_pin_exact {cfg_target[3]} M4 W 18.300
ot_assigned_pin_exact {cfg_target[4]} M4 W 18.396
ot_assigned_pin_exact {cfg_target[5]} M4 W 18.492
ot_assigned_pin_exact {cfg_target[6]} M4 W 18.588
ot_assigned_pin_exact {cfg_target[7]} M4 W 18.684
ot_assigned_pin_exact {cfg_v} M4 W 18.780
ot_assigned_pin_exact {client_seq[0]} M4 E 23.004
ot_assigned_pin_exact {client_seq[1]} M4 E 23.100
ot_assigned_pin_exact {client_seq[2]} M4 E 23.196
ot_assigned_pin_exact {client_seq[3]} M4 E 23.292
ot_assigned_pin_exact {client_seq[4]} M4 E 23.388
ot_assigned_pin_exact {client_seq[5]} M4 E 23.484
ot_assigned_pin_exact {client_seq[6]} M4 E 23.580
ot_assigned_pin_exact {client_seq[7]} M4 E 23.676
ot_assigned_pin_exact {client_seq[8]} M4 E 23.772
ot_assigned_pin_exact {client_seq[9]} M4 E 23.868
ot_assigned_pin_exact {clk} M5 S 13.212
ot_assigned_pin_exact {clk_cap} M4 W 18.876
ot_assigned_pin_exact {clk_mem} M4 W 18.972
ot_assigned_pin_exact {clk_tgt} M5 S 13.308
ot_assigned_pin_exact {desc_base[0]} M4 W 19.068
ot_assigned_pin_exact {desc_base[10]} M4 W 13.884
ot_assigned_pin_exact {desc_base[11]} M4 W 13.980
ot_assigned_pin_exact {desc_base[1]} M4 W 19.164
ot_assigned_pin_exact {desc_base[2]} M4 W 19.260
ot_assigned_pin_exact {desc_base[3]} M4 W 19.356
ot_assigned_pin_exact {desc_base[4]} M4 W 19.452
ot_assigned_pin_exact {desc_base[5]} M4 W 19.548
ot_assigned_pin_exact {desc_base[6]} M4 W 19.644
ot_assigned_pin_exact {desc_base[7]} M4 W 19.740
ot_assigned_pin_exact {desc_base[8]} M4 W 19.836
ot_assigned_pin_exact {desc_base[9]} M4 W 13.788
ot_assigned_pin_exact {desc_limit[0]} M4 W 14.076
ot_assigned_pin_exact {desc_limit[10]} M4 W 15.036
ot_assigned_pin_exact {desc_limit[11]} M4 W 15.132
ot_assigned_pin_exact {desc_limit[12]} M4 W 15.228
ot_assigned_pin_exact {desc_limit[1]} M4 W 14.172
ot_assigned_pin_exact {desc_limit[2]} M4 W 14.268
ot_assigned_pin_exact {desc_limit[3]} M4 W 14.364
ot_assigned_pin_exact {desc_limit[4]} M4 W 14.460
ot_assigned_pin_exact {desc_limit[5]} M4 W 14.556
ot_assigned_pin_exact {desc_limit[6]} M4 W 14.652
ot_assigned_pin_exact {desc_limit[7]} M4 W 14.748
ot_assigned_pin_exact {desc_limit[8]} M4 W 14.844
ot_assigned_pin_exact {desc_limit[9]} M4 W 14.940
ot_assigned_pin_exact {desc_loops[0]} M4 W 15.324
ot_assigned_pin_exact {desc_loops[10]} M4 W 16.284
ot_assigned_pin_exact {desc_loops[11]} M4 W 16.380
ot_assigned_pin_exact {desc_loops[12]} M4 W 16.476
ot_assigned_pin_exact {desc_loops[13]} M4 W 16.572
ot_assigned_pin_exact {desc_loops[14]} M4 W 16.668
ot_assigned_pin_exact {desc_loops[15]} M4 W 16.764
ot_assigned_pin_exact {desc_loops[1]} M4 W 15.420
ot_assigned_pin_exact {desc_loops[2]} M4 W 15.516
ot_assigned_pin_exact {desc_loops[3]} M4 W 15.612
ot_assigned_pin_exact {desc_loops[4]} M4 W 15.708
ot_assigned_pin_exact {desc_loops[5]} M4 W 15.804
ot_assigned_pin_exact {desc_loops[6]} M4 W 15.900
ot_assigned_pin_exact {desc_loops[7]} M4 W 15.996
ot_assigned_pin_exact {desc_loops[8]} M4 W 16.092
ot_assigned_pin_exact {desc_loops[9]} M4 W 16.188
ot_assigned_pin_exact {desc_v} M4 W 12.732
ot_assigned_pin_exact {done} M5 S 13.404
ot_assigned_pin_exact {fault} M5 S 13.500
ot_assigned_pin_exact {hub_ring_client[0]} M4 E 23.964
ot_assigned_pin_exact {hub_ring_client[1]} M4 E 24.060
ot_assigned_pin_exact {hub_ring_client[2]} M4 E 24.156
ot_assigned_pin_exact {hub_ring_client[3]} M4 E 24.252
ot_assigned_pin_exact {hub_ring_client[4]} M4 E 24.348
ot_assigned_pin_exact {hub_ring_client[5]} M4 E 24.444
ot_assigned_pin_exact {hub_ring_enable[0]} M4 E 24.540
ot_assigned_pin_exact {hub_ring_enable[1]} M4 E 24.636
ot_assigned_pin_exact {launch_v} M4 W 12.828
ot_assigned_pin_exact {lg_local_read[0]} M4 E 24.732
ot_assigned_pin_exact {lg_local_read[10]} M4 E 25.692
ot_assigned_pin_exact {lg_local_read[11]} M4 E 25.788
ot_assigned_pin_exact {lg_local_read[12]} M4 E 25.884
ot_assigned_pin_exact {lg_local_read[13]} M4 E 25.980
ot_assigned_pin_exact {lg_local_read[14]} M4 E 42.204
ot_assigned_pin_exact {lg_local_read[15]} M4 E 42.300
ot_assigned_pin_exact {lg_local_read[16]} M4 E 42.396
ot_assigned_pin_exact {lg_local_read[17]} M4 E 42.492
ot_assigned_pin_exact {lg_local_read[18]} M4 E 42.588
ot_assigned_pin_exact {lg_local_read[19]} M4 E 42.684
ot_assigned_pin_exact {lg_local_read[1]} M4 E 24.828
ot_assigned_pin_exact {lg_local_read[20]} M4 E 42.780
ot_assigned_pin_exact {lg_local_read[21]} M4 E 42.876
ot_assigned_pin_exact {lg_local_read[22]} M4 E 42.972
ot_assigned_pin_exact {lg_local_read[23]} M4 E 43.068
ot_assigned_pin_exact {lg_local_read[2]} M4 E 24.924
ot_assigned_pin_exact {lg_local_read[3]} M4 E 25.020
ot_assigned_pin_exact {lg_local_read[4]} M4 E 25.116
ot_assigned_pin_exact {lg_local_read[5]} M4 E 25.212
ot_assigned_pin_exact {lg_local_read[6]} M4 E 25.308
ot_assigned_pin_exact {lg_local_read[7]} M4 E 25.404
ot_assigned_pin_exact {lg_local_read[8]} M4 E 25.500
ot_assigned_pin_exact {lg_local_read[9]} M4 E 25.596
ot_assigned_pin_exact {lg_local_write[0]} M4 E 43.164
ot_assigned_pin_exact {lg_local_write[10]} M4 E 44.124
ot_assigned_pin_exact {lg_local_write[11]} M4 E 44.220
ot_assigned_pin_exact {lg_local_write[12]} M4 E 44.316
ot_assigned_pin_exact {lg_local_write[13]} M4 E 44.412
ot_assigned_pin_exact {lg_local_write[14]} M4 E 44.508
ot_assigned_pin_exact {lg_local_write[15]} M4 E 44.604
ot_assigned_pin_exact {lg_local_write[16]} M4 E 44.700
ot_assigned_pin_exact {lg_local_write[17]} M4 E 44.796
ot_assigned_pin_exact {lg_local_write[18]} M4 E 44.892
ot_assigned_pin_exact {lg_local_write[19]} M4 E 44.988
ot_assigned_pin_exact {lg_local_write[1]} M4 E 43.260
ot_assigned_pin_exact {lg_local_write[20]} M4 E 45.084
ot_assigned_pin_exact {lg_local_write[21]} M4 E 45.180
ot_assigned_pin_exact {lg_local_write[22]} M4 E 26.076
ot_assigned_pin_exact {lg_local_write[23]} M4 E 26.172
ot_assigned_pin_exact {lg_local_write[2]} M4 E 43.356
ot_assigned_pin_exact {lg_local_write[3]} M4 E 43.452
ot_assigned_pin_exact {lg_local_write[4]} M4 E 43.548
ot_assigned_pin_exact {lg_local_write[5]} M4 E 43.644
ot_assigned_pin_exact {lg_local_write[6]} M4 E 43.740
ot_assigned_pin_exact {lg_local_write[7]} M4 E 43.836
ot_assigned_pin_exact {lg_local_write[8]} M4 E 43.932
ot_assigned_pin_exact {lg_local_write[9]} M4 E 44.028
ot_assigned_pin_exact {ordinal[0]} M5 S 13.596
ot_assigned_pin_exact {ordinal[10]} M5 S 14.556
ot_assigned_pin_exact {ordinal[11]} M5 S 14.652
ot_assigned_pin_exact {ordinal[12]} M5 S 14.748
ot_assigned_pin_exact {ordinal[13]} M5 S 14.844
ot_assigned_pin_exact {ordinal[14]} M5 S 14.940
ot_assigned_pin_exact {ordinal[15]} M5 S 15.036
ot_assigned_pin_exact {ordinal[16]} M5 S 15.132
ot_assigned_pin_exact {ordinal[17]} M5 S 15.228
ot_assigned_pin_exact {ordinal[18]} M5 S 15.324
ot_assigned_pin_exact {ordinal[19]} M5 S 15.420
ot_assigned_pin_exact {ordinal[1]} M5 S 13.692
ot_assigned_pin_exact {ordinal[20]} M5 S 15.516
ot_assigned_pin_exact {ordinal[21]} M5 S 15.612
ot_assigned_pin_exact {ordinal[22]} M5 S 15.708
ot_assigned_pin_exact {ordinal[23]} M5 S 15.804
ot_assigned_pin_exact {ordinal[24]} M5 S 15.900
ot_assigned_pin_exact {ordinal[25]} M5 S 15.996
ot_assigned_pin_exact {ordinal[26]} M5 S 16.092
ot_assigned_pin_exact {ordinal[27]} M5 S 16.188
ot_assigned_pin_exact {ordinal[28]} M5 S 16.284
ot_assigned_pin_exact {ordinal[29]} M5 S 16.380
ot_assigned_pin_exact {ordinal[2]} M5 S 13.788
ot_assigned_pin_exact {ordinal[30]} M5 S 16.476
ot_assigned_pin_exact {ordinal[31]} M5 S 16.572
ot_assigned_pin_exact {ordinal[3]} M5 S 13.884
ot_assigned_pin_exact {ordinal[4]} M5 S 13.980
ot_assigned_pin_exact {ordinal[5]} M5 S 14.076
ot_assigned_pin_exact {ordinal[6]} M5 S 14.172
ot_assigned_pin_exact {ordinal[7]} M5 S 14.268
ot_assigned_pin_exact {ordinal[8]} M5 S 14.364
ot_assigned_pin_exact {ordinal[9]} M5 S 14.460
ot_assigned_pin_exact {replay_enable} M4 E 26.268
ot_assigned_pin_exact {replay_source} M4 E 26.364
ot_assigned_pin_exact {response_enable[0]} M4 E 26.460
ot_assigned_pin_exact {response_enable[1]} M4 E 26.556
ot_assigned_pin_exact {response_enable[2]} M4 E 26.652
ot_assigned_pin_exact {response_enable[3]} M4 E 26.748
ot_assigned_pin_exact {response_enable[4]} M4 E 26.844
ot_assigned_pin_exact {response_seq[0]} M4 E 26.940
ot_assigned_pin_exact {response_seq[1]} M4 E 27.036
ot_assigned_pin_exact {response_seq[2]} M4 E 27.132
ot_assigned_pin_exact {response_seq[3]} M4 E 27.228
ot_assigned_pin_exact {response_seq[4]} M4 E 27.324
ot_assigned_pin_exact {response_seq[5]} M4 E 27.420
ot_assigned_pin_exact {response_seq[6]} M4 E 27.516
ot_assigned_pin_exact {response_seq[7]} M4 E 27.612
ot_assigned_pin_exact {response_seq[8]} M4 E 27.708
ot_assigned_pin_exact {response_seq[9]} M4 E 27.804
ot_assigned_pin_exact {ring_tx_enable[0]} M4 E 27.900
ot_assigned_pin_exact {ring_tx_enable[1]} M4 E 27.996
ot_assigned_pin_exact {ring_tx_source[0]} M4 E 28.092
ot_assigned_pin_exact {ring_tx_source[1]} M4 E 28.188
ot_assigned_pin_exact {ring_tx_source[2]} M4 E 28.284
ot_assigned_pin_exact {ring_tx_source[3]} M4 E 28.380
ot_assigned_pin_exact {ring_tx_source[4]} M4 E 28.476
ot_assigned_pin_exact {ring_tx_source[5]} M4 E 28.572
ot_assigned_pin_exact {rslot[0]} M4 E 28.668
ot_assigned_pin_exact {rslot[10]} M4 E 32.700
ot_assigned_pin_exact {rslot[11]} M4 E 32.796
ot_assigned_pin_exact {rslot[12]} M4 E 32.892
ot_assigned_pin_exact {rslot[13]} M4 E 32.988
ot_assigned_pin_exact {rslot[14]} M4 E 33.084
ot_assigned_pin_exact {rslot[15]} M4 E 33.180
ot_assigned_pin_exact {rslot[16]} M4 E 33.276
ot_assigned_pin_exact {rslot[17]} M4 E 33.372
ot_assigned_pin_exact {rslot[18]} M4 E 33.468
ot_assigned_pin_exact {rslot[19]} M4 E 33.564
ot_assigned_pin_exact {rslot[1]} M4 E 28.764
ot_assigned_pin_exact {rslot[20]} M4 E 33.660
ot_assigned_pin_exact {rslot[21]} M4 E 33.756
ot_assigned_pin_exact {rslot[22]} M4 E 33.852
ot_assigned_pin_exact {rslot[23]} M4 E 33.948
ot_assigned_pin_exact {rslot[2]} M4 E 28.860
ot_assigned_pin_exact {rslot[3]} M4 E 28.956
ot_assigned_pin_exact {rslot[4]} M4 E 29.052
ot_assigned_pin_exact {rslot[5]} M4 E 32.220
ot_assigned_pin_exact {rslot[6]} M4 E 32.316
ot_assigned_pin_exact {rslot[7]} M4 E 32.412
ot_assigned_pin_exact {rslot[8]} M4 E 32.508
ot_assigned_pin_exact {rslot[9]} M4 E 32.604
ot_assigned_pin_exact {rslot_v[0]} M4 E 34.044
ot_assigned_pin_exact {rslot_v[1]} M4 E 34.140
ot_assigned_pin_exact {rslot_v[2]} M4 E 34.236
ot_assigned_pin_exact {rslot_v[3]} M4 E 34.332
ot_assigned_pin_exact {rslot_v[4]} M4 E 34.428
ot_assigned_pin_exact {rslot_v[5]} M4 E 34.524
ot_assigned_pin_exact {rslot_v[6]} M4 E 34.620
ot_assigned_pin_exact {rslot_v[7]} M4 E 34.716
ot_assigned_pin_exact {rst_n} M4 W 12.924
ot_assigned_pin_exact {tgt[0]} M4 W 13.020
ot_assigned_pin_exact {tgt[1]} M4 W 13.116
ot_assigned_pin_exact {tgt[2]} M4 W 13.212
ot_assigned_pin_exact {tgt[3]} M4 W 13.308
ot_assigned_pin_exact {tgt[4]} M4 W 13.404
ot_assigned_pin_exact {tgt[5]} M4 W 13.500
ot_assigned_pin_exact {tgt[6]} M4 W 13.596
ot_assigned_pin_exact {tgt[7]} M4 W 13.692
ot_assigned_pin_exact {tgt_configured} M5 S 16.668
ot_assigned_pin_exact {tgt_fault} M5 S 16.764
ot_assigned_pin_exact {wslot[0]} M4 E 34.812
ot_assigned_pin_exact {wslot[10]} M4 E 35.772
ot_assigned_pin_exact {wslot[11]} M4 E 35.868
ot_assigned_pin_exact {wslot[12]} M4 E 35.964
ot_assigned_pin_exact {wslot[13]} M4 E 36.060
ot_assigned_pin_exact {wslot[14]} M4 E 36.156
ot_assigned_pin_exact {wslot[15]} M4 E 36.252
ot_assigned_pin_exact {wslot[16]} M4 E 36.348
ot_assigned_pin_exact {wslot[17]} M4 E 36.444
ot_assigned_pin_exact {wslot[18]} M4 E 36.540
ot_assigned_pin_exact {wslot[19]} M4 E 36.636
ot_assigned_pin_exact {wslot[1]} M4 E 34.908
ot_assigned_pin_exact {wslot[20]} M4 E 36.732
ot_assigned_pin_exact {wslot[21]} M4 E 36.828
ot_assigned_pin_exact {wslot[22]} M4 E 36.924
ot_assigned_pin_exact {wslot[23]} M4 E 37.020
ot_assigned_pin_exact {wslot[2]} M4 E 35.004
ot_assigned_pin_exact {wslot[3]} M4 E 35.100
ot_assigned_pin_exact {wslot[4]} M4 E 35.196
ot_assigned_pin_exact {wslot[5]} M4 E 35.292
ot_assigned_pin_exact {wslot[6]} M4 E 35.388
ot_assigned_pin_exact {wslot[7]} M4 E 35.484
ot_assigned_pin_exact {wslot[8]} M4 E 35.580
ot_assigned_pin_exact {wslot[9]} M4 E 35.676
ot_assigned_pin_exact {wslot_v[0]} M4 E 37.116
ot_assigned_pin_exact {wslot_v[1]} M4 E 37.212
ot_assigned_pin_exact {wslot_v[2]} M4 E 37.308
ot_assigned_pin_exact {wslot_v[3]} M4 E 37.404
ot_assigned_pin_exact {wslot_v[4]} M4 E 37.500
ot_assigned_pin_exact {wslot_v[5]} M4 E 37.596
ot_assigned_pin_exact {wslot_v[6]} M4 E 37.692
ot_assigned_pin_exact {wslot_v[7]} M4 E 37.788
