# GENERATED (CLAUDE S81-RERUN): POST_MACRO_PLACE hook of the S81 frame block
source /src/physical/common/ot_macro_track_snap.tcl
set ::_blk [ord::get_db_block]; set ::_dbu [ot_mts::get_dbu]; set ::_sg [ot_mts::site_grid]
set _blk $::_blk; set _dbu $::_dbu; set _sg $::_sg
proc ot_find {nm} { global _blk; set i [$_blk findInst $nm]; if {$i eq "NULL"} { error "no inst $nm" }; return $i }
proc fplace {nm x y o} { global _blk _dbu _sg; set i [ot_find $nm]; set m [$i getMaster]
  lassign $_sg gx gw gy gh; set r [ot_mts::rule $m $o]
  lassign [dict get $r x] Px Sx; lassign [dict get $r y] Py Sy
  set px [expr {double([ot_mts::snap_axis [expr {round($x*$_dbu)}] $gx $gw $Px $Sx "$nm x"])/$_dbu}]
  set py [expr {double([ot_mts::snap_axis [expr {round($y*$_dbu)}] $gy $gh $Py $Sy "$nm y"])/$_dbu}]
  $i setPlacementStatus PLACED; $i setOrient $o; $i setLocation [expr {round($px*$_dbu)}] [expr {round($py*$_dbu)}]; $i setPlacementStatus FIRM }
fplace e1008 4.320 133.920 R0
fplace c1008_0 4.320 60.480 MY
fplace c1008_1 50.976 60.480 MY
fplace c1008_2 97.632 60.480 MY
fplace c1008_3 144.288 60.480 MY
fplace c1008_4 190.944 60.480 MY
fplace c1008_5 237.600 60.480 MY
fplace c1008_6 284.256 60.480 MY
fplace e1009 524.448 133.920 R0
fplace c1009_0 595.728 60.480 R0
fplace c1009_1 642.384 60.480 R0
fplace c1009_2 689.040 60.480 R0
fplace c1009_3 735.696 60.480 R0
fplace c1009_4 782.352 60.480 R0
fplace c1009_5 829.008 60.480 R0
fplace c1009_6 875.664 60.480 R0
fplace e1010 4.320 414.720 R0
fplace c1010_0 4.320 341.280 MY
fplace c1010_1 50.976 341.280 MY
fplace c1010_2 97.632 341.280 MY
fplace c1010_3 144.288 341.280 MY
fplace c1010_4 190.944 341.280 MY
fplace c1010_5 237.600 341.280 MY
fplace c1010_6 284.256 341.280 MY
fplace c1011_0 4.320 622.080 MY
fplace c1011_1 50.976 622.080 MY
fplace c1011_2 97.632 622.080 MY
fplace c1011_3 144.288 622.080 MY
fplace c1011_4 190.944 622.080 MY
fplace c1011_5 237.600 622.080 MY
fplace c1011_6 284.256 622.080 MY
fplace e1012 524.448 414.720 R0
fplace c1012_0 595.728 341.280 R0
fplace c1012_1 642.384 341.280 R0
fplace c1012_2 689.040 341.280 R0
fplace c1012_3 735.696 341.280 R0
fplace c1012_4 782.352 341.280 R0
fplace c1012_5 829.008 341.280 R0
fplace c1012_6 875.664 341.280 R0
fplace e1013 4.320 976.320 R0
fplace c1013_0 4.320 902.880 MY
fplace c1013_1 50.976 902.880 MY
fplace c1013_2 97.632 902.880 MY
fplace c1013_3 144.288 902.880 MY
fplace c1013_4 190.944 902.880 MY
fplace c1013_5 237.600 902.880 MY
fplace c1013_6 284.256 902.880 MY
fplace e1014 524.448 976.320 R0
fplace c1014_0 595.728 902.880 R0
fplace c1014_1 642.384 902.880 R0
fplace c1014_2 689.040 902.880 R0
fplace c1014_3 735.696 902.880 R0
fplace c1014_4 782.352 902.880 R0
fplace c1014_5 829.008 902.880 R0
fplace c1014_6 875.664 902.880 R0
fplace e1015 4.320 1257.120 R0
fplace c1015_0 4.320 1183.680 MY
fplace c1015_1 50.976 1183.680 MY
fplace c1015_2 97.632 1183.680 MY
fplace c1015_3 144.288 1183.680 MY
fplace c1015_4 190.944 1183.680 MY
fplace c1015_5 237.600 1183.680 MY
fplace c1015_6 284.256 1183.680 MY
fplace c1016_0 4.320 1464.480 MY
fplace c1016_1 50.976 1464.480 MY
fplace c1016_2 97.632 1464.480 MY
fplace c1016_3 144.288 1464.480 MY
fplace c1016_4 190.944 1464.480 MY
fplace c1016_5 237.600 1464.480 MY
fplace c1016_6 284.256 1464.480 MY
fplace e1017 524.448 1257.120 R0
fplace c1017_0 595.728 1183.680 R0
fplace c1017_1 642.384 1183.680 R0
fplace c1017_2 689.040 1183.680 R0
fplace c1017_3 735.696 1183.680 R0
fplace c1017_4 782.352 1183.680 R0
fplace c1017_5 829.008 1183.680 R0
fplace c1017_6 875.664 1183.680 R0
fplace e1018 4.320 1818.720 R0
fplace c1018_0 4.320 1745.280 MY
fplace c1018_1 50.976 1745.280 MY
fplace c1018_2 97.632 1745.280 MY
fplace c1018_3 144.288 1745.280 MY
fplace c1018_4 190.944 1745.280 MY
fplace c1018_5 237.600 1745.280 MY
fplace c1018_6 284.256 1745.280 MY
fplace e1019 524.448 1818.720 R0
fplace c1019_0 595.728 1745.280 R0
fplace c1019_1 642.384 1745.280 R0
fplace c1019_2 689.040 1745.280 R0
fplace c1019_3 735.696 1745.280 R0
fplace c1019_4 782.352 1745.280 R0
fplace c1019_5 829.008 1745.280 R0
fplace c1019_6 875.664 1745.280 R0
fplace c1020_0 4.320 2026.080 MY
fplace c1020_1 50.976 2026.080 MY
fplace c1020_2 97.632 2026.080 MY
fplace c1020_3 144.288 2026.080 MY
fplace c1020_4 190.944 2026.080 MY
fplace c1020_5 237.600 2026.080 MY
fplace c1020_6 284.256 2026.080 MY
fplace e1021 4.320 2380.320 R0
fplace c1021_0 4.320 2306.880 MY
fplace c1021_1 50.976 2306.880 MY
fplace c1021_2 97.632 2306.880 MY
fplace c1021_3 144.288 2306.880 MY
fplace c1021_4 190.944 2306.880 MY
fplace c1021_5 237.600 2306.880 MY
fplace c1021_6 284.256 2306.880 MY
fplace e1022 524.448 2380.320 R0
fplace c1022_0 595.728 2306.880 R0
fplace c1022_1 642.384 2306.880 R0
fplace c1022_2 689.040 2306.880 R0
fplace c1022_3 735.696 2306.880 R0
fplace c1022_4 782.352 2306.880 R0
fplace c1022_5 829.008 2306.880 R0
fplace c1022_6 875.664 2306.880 R0
fplace e1023 4.320 2661.120 R0
fplace c1023_0 4.320 2587.680 MY
fplace c1023_1 50.976 2587.680 MY
fplace c1023_2 97.632 2587.680 MY
fplace c1023_3 144.288 2587.680 MY
fplace c1023_4 190.944 2587.680 MY
fplace c1023_5 237.600 2587.680 MY
fplace c1023_6 284.256 2587.680 MY
fplace e1024 524.448 2661.120 R0
fplace c1024_0 595.728 2587.680 R0
fplace c1024_1 642.384 2587.680 R0
fplace c1024_2 689.040 2587.680 R0
fplace c1024_3 735.696 2587.680 R0
fplace c1024_4 782.352 2587.680 R0
fplace c1024_5 829.008 2587.680 R0
fplace c1024_6 875.664 2587.680 R0
set nb 0; foreach b [$_blk getBlockages] { odb::dbBlockage_destroy $b; incr nb }
puts "OT_FRAME_PLACE macros=[llength [list e1008]] blockages_removed=$nb"
set fence [dict create]
dict set fence s1008 {325.104 59.400 361.800 122.016}
dict set fence s1009 {556.200 59.400 592.896 122.016}
dict set fence s1010 {325.104 340.200 361.800 402.816}
dict set fence e1011 {3.240 694.440 1008.288 895.296}
dict set fence s1011 {325.104 621.000 361.800 683.616}
dict set fence s1012 {556.200 340.200 592.896 402.816}
dict set fence s1013 {325.104 901.800 361.800 964.416}
dict set fence s1014 {556.200 901.800 592.896 964.416}
dict set fence s1015 {325.104 1182.600 361.800 1245.216}
dict set fence e1016 {3.240 1536.840 1008.288 1737.696}
dict set fence s1016 {325.104 1463.400 361.800 1526.016}
dict set fence s1017 {556.200 1182.600 592.896 1245.216}
dict set fence s1018 {325.104 1744.200 361.800 1806.816}
dict set fence s1019 {556.200 1744.200 592.896 1806.816}
dict set fence e1020 {3.240 2098.440 1008.288 2299.296}
dict set fence s1020 {325.104 2025.000 361.800 2087.616}
dict set fence s1021 {325.104 2305.800 361.800 2368.416}
dict set fence s1022 {556.200 2305.800 592.896 2368.416}
dict set fence s1023 {325.104 2586.600 361.800 2649.216}
dict set fence s1024 {556.200 2586.600 592.896 2649.216}
dict set fence t63_0 {363.960 59.400 538.896 91.776}
dict set fence t63_1 {363.960 340.200 538.896 372.576}
dict set fence t63_2 {363.960 621.000 538.896 653.376}
dict set fence t63_3 {363.960 901.800 538.896 934.176}
dict set fence t63_4 {363.960 1182.600 538.896 1214.976}
dict set fence t63_5 {363.960 1463.400 538.896 1495.776}
dict set fence t63_6 {363.960 1744.200 538.896 1776.576}
dict set fence t63_7 {363.960 2025.000 538.896 2057.376}
dict set fence t63_8 {363.960 2305.800 538.896 2338.176}
dict set fence t63_9 {363.960 2586.600 538.896 2618.976}
dict set fence bs1008 {220.968 124.200 283.584 132.816}
dict set fence bn1008 {218.808 312.120 281.424 320.736}
dict set fence bs1009 {741.096 124.200 803.712 132.816}
dict set fence bn1009 {738.936 312.120 801.552 320.736}
dict set fence bs1010 {220.968 405.000 283.584 413.616}
dict set fence bn1010 {218.808 592.920 281.424 601.536}
dict set fence bs1012 {741.096 405.000 803.712 413.616}
dict set fence bn1012 {738.936 592.920 801.552 601.536}
dict set fence bs1013 {220.968 966.600 283.584 975.216}
dict set fence bn1013 {218.808 1154.520 281.424 1163.136}
dict set fence bs1014 {741.096 966.600 803.712 975.216}
dict set fence bn1014 {738.936 1154.520 801.552 1163.136}
dict set fence bs1015 {220.968 1247.400 283.584 1256.016}
dict set fence bn1015 {218.808 1435.320 281.424 1443.936}
dict set fence bs1017 {741.096 1247.400 803.712 1256.016}
dict set fence bn1017 {738.936 1435.320 801.552 1443.936}
dict set fence bs1018 {220.968 1809.000 283.584 1817.616}
dict set fence bn1018 {218.808 1996.920 281.424 2005.536}
dict set fence bs1019 {741.096 1809.000 803.712 1817.616}
dict set fence bn1019 {738.936 1996.920 801.552 2005.536}
dict set fence bs1021 {220.968 2370.600 283.584 2379.216}
dict set fence bn1021 {218.808 2558.520 281.424 2567.136}
dict set fence bs1022 {741.096 2370.600 803.712 2379.216}
dict set fence bn1022 {738.936 2558.520 801.552 2567.136}
dict set fence bs1023 {220.968 2651.400 283.584 2660.016}
dict set fence bn1023 {218.808 2839.320 281.424 2847.936}
dict set fence bs1024 {741.096 2651.400 803.712 2660.016}
dict set fence bn1024 {738.936 2839.320 801.552 2847.936}
dict set fence n63_0 {1043.496 55.080 1132.032 134.976}
dict set fence n63_1 {1043.496 132.840 1132.032 212.736}
dict set fence n63_2 {1043.496 210.600 1132.032 290.496}
dict set fence n63_3 {1043.496 288.360 1132.032 368.256}
dict set fence n63_4 {1043.496 366.120 1132.032 446.016}
dict set fence n63_5 {1043.496 443.880 1132.032 523.776}
dict set fence n63_6 {1043.496 521.640 1132.032 601.536}
dict set fence n63_7 {1043.496 599.400 1132.032 679.296}
dict set fence n63_8 {1043.496 677.160 1132.032 757.056}
dict set fence n63_9 {1043.496 754.920 1132.032 834.816}
dict set fence n63_10 {1043.496 832.680 1132.032 912.576}
dict set fence n63_11 {1043.496 910.440 1132.032 990.336}
dict set fence n63_12 {1043.496 988.200 1132.032 1068.096}
dict set fence n63_13 {1043.496 1065.960 1132.032 1145.856}
dict set fence n63_14 {1043.496 1143.720 1132.032 1223.616}
dict set fence n63_15 {1043.496 1221.480 1132.032 1301.376}
dict set fence n63_16 {1043.496 1299.240 1132.032 1379.136}
dict set fence n63_17 {1043.496 1377.000 1132.032 1456.896}
dict set fence n63_18 {1043.496 1454.760 1132.032 1534.656}
dict set fence n63_19 {1043.496 1532.520 1132.032 1612.416}
dict set fence n63_20 {1043.496 1610.280 1132.032 1690.176}
dict set fence n63_21 {1043.496 1688.040 1132.032 1767.936}
dict set fence n63_22 {1043.496 1765.800 1132.032 1845.696}
dict set fence n63_23 {1043.496 1843.560 1132.032 1923.456}
dict set fence n63_24 {1043.496 1921.320 1132.032 2001.216}
dict set fence n63_25 {1043.496 1999.080 1132.032 2078.976}
dict set fence n63_26 {1043.496 2076.840 1132.032 2156.736}
dict set fence n63_27 {1043.496 2154.600 1132.032 2234.496}
dict set fence n63_28 {1043.496 2232.360 1132.032 2312.256}
dict set fence n63_29 {1043.496 2310.120 1132.032 2390.016}
dict set fence n63_30 {1043.496 2387.880 1132.032 2467.776}
dict set fence n63_31 {1043.496 2465.640 1132.032 2545.536}
dict set fence n63_32 {1043.496 2543.400 1132.032 2623.296}
dict set fence cf63 {327.240 3.240 1179.552 52.896}
dict set fence rg63_0 {1138.536 1085.400 1179.552 1122.096}
dict set fence rg63_1 {1138.536 733.320 1179.552 770.016}
dict set fence rg63_2 {1138.536 383.400 1179.552 420.096}
dict set fence y_es_1008_0 {441.720 383.400 461.136 402.816}
dict set fence y_es_1009_0 {480.600 383.400 500.016 402.816}
dict set fence y_es_1010_0 {441.720 664.200 461.136 683.616}
dict set fence y_es_1012_0 {480.600 664.200 500.016 683.616}
dict set fence y_es_1013_0 {441.720 1225.800 461.136 1245.216}
dict set fence y_es_1014_0 {480.600 1225.800 500.016 1245.216}
dict set fence y_es_1015_0 {441.720 1506.600 461.136 1526.016}
dict set fence y_es_1017_0 {480.600 1506.600 500.016 1526.016}
dict set fence y_es_1018_0 {441.720 2068.200 461.136 2087.616}
dict set fence y_es_1019_0 {480.600 2068.200 500.016 2087.616}
dict set fence y_es_1021_0 {441.720 2629.800 461.136 2649.216}
dict set fence y_es_1022_0 {480.600 2629.800 500.016 2649.216}
dict set fence y_es_1023_0 {420.120 2638.440 439.536 2657.856}
dict set fence y_es_1024_0 {502.200 2638.440 521.616 2657.856}
dict set fence y_xb_63_10_0 {535.464 2634.120 554.880 2655.696}
dict set fence y_rt_63_0a_0 {537.192 325.080 556.608 344.496}
dict set fence y_rt_63_0a_1 {946.296 325.080 965.712 344.496}
dict set fence y_rt_63_0b_0 {537.192 344.520 556.608 363.936}
dict set fence y_rt_63_0b_1 {946.296 344.520 965.712 363.936}
dict set fence y_rt_63_4a_0 {582.984 605.880 602.400 625.296}
dict set fence y_rt_63_4a_1 {925.992 605.880 945.408 625.296}
dict set fence y_rt_63_4b_0 {582.984 625.320 602.400 644.736}
dict set fence y_rt_63_4b_1 {925.992 625.320 945.408 644.736}
dict set fence y_rt_63_6a_0 {847.368 668.520 866.784 687.936}
dict set fence y_rt_63_6b_0 {825.768 668.520 845.184 687.936}
dict set fence y_rt_63_8a_0 {979.128 605.880 998.544 625.296}
dict set fence y_rt_63_8b_0 {979.128 625.320 998.544 644.736}
dict set fence y_rt_63_10a_0 {537.192 1167.480 556.608 1186.896}
dict set fence y_rt_63_10a_1 {989.496 1167.480 1008.912 1186.896}
dict set fence y_rt_63_10b_0 {537.192 1186.920 556.608 1206.336}
dict set fence y_rt_63_10b_1 {989.496 1186.920 1008.912 1206.336}
dict set fence y_rt_63_12a_0 {971.352 1167.480 990.768 1186.896}
dict set fence y_rt_63_12b_0 {984.312 1206.360 1003.728 1225.776}
dict set fence y_rt_63_14a_0 {604.584 1448.280 624.000 1467.696}
dict set fence y_rt_63_14a_1 {969.192 1448.280 988.608 1467.696}
dict set fence y_rt_63_14b_0 {604.584 1467.720 624.000 1487.136}
dict set fence y_rt_63_14b_1 {969.192 1467.720 988.608 1487.136}
dict set fence y_rt_63_16a_0 {789.048 1510.920 808.464 1530.336}
dict set fence y_rt_63_16a_1 {1021.896 1621.080 1041.312 1640.496}
dict set fence y_rt_63_16b_0 {789.048 1491.480 808.464 1510.896}
dict set fence y_rt_63_16b_1 {1021.896 1640.520 1041.312 1659.936}
dict set fence y_rt_63_17a_0 {1134.216 1132.920 1153.632 1152.336}
dict set fence y_rt_63_17b_0 {1021.896 1718.280 1041.312 1737.696}
dict set fence y_rt_63_20a_0 {636.552 2009.880 655.968 2029.296}
dict set fence y_rt_63_20a_1 {1024.056 2009.880 1043.472 2029.296}
dict set fence y_rt_63_20b_0 {636.552 2029.320 655.968 2048.736}
dict set fence y_rt_63_20b_1 {1024.056 2029.320 1043.472 2048.736}
dict set fence y_rt_63_22a_0 {1003.752 2009.880 1023.168 2029.296}
dict set fence y_rt_63_22b_0 {1016.712 2048.760 1036.128 2068.176}
dict set fence y_rt_63_24a_0 {845.208 2072.520 864.624 2091.936}
dict set fence y_rt_63_24b_0 {823.608 2072.520 843.024 2091.936}
dict set fence y_rt_63_26a_0 {538.488 2571.480 557.904 2590.896}
dict set fence y_rt_63_26a_1 {1004.616 2573.640 1024.032 2593.056}
dict set fence y_rt_63_26b_0 {538.488 2590.920 557.904 2610.336}
dict set fence y_rt_63_26b_1 {1004.616 2593.080 1024.032 2612.496}
dict set fence y_rt_63_28a_0 {1064.232 2629.800 1083.648 2649.216}
dict set fence y_rt_63_28b_0 {1025.352 2571.480 1044.768 2590.896}
dict set fence y_rt_63_30a_0 {459.432 2638.440 478.848 2657.856}
dict set fence y_rt_63_30a_1 {929.016 2638.440 948.432 2657.856}
dict set fence y_rt_63_30b_0 {459.432 2619.000 478.848 2638.416}
dict set fence y_rt_63_30b_1 {929.016 2619.000 948.432 2638.416}
dict set fence y_rt_63_32a_0 {1049.112 2832.840 1068.528 2852.256}
dict set fence y_rt_63_32b_0 {1049.112 2813.400 1068.528 2832.816}
dict set fence y_nf_63_0_0 {914.328 85.320 933.744 104.736}
dict set fence y_rr_63_3_0 {802.872 314.280 822.288 333.696}
set regs [dict create]
dict for {nm box} $fence {
  set rg [odb::dbRegion_create $_blk fence_$nm]
  lassign $box a b c d
  odb::dbBox_create $rg [expr {round($a*$_dbu)}] [expr {round($b*$_dbu)}] [expr {round($c*$_dbu)}] [expr {round($d*$_dbu)}]
  dict set regs $nm $rg }
set nf 0; set nfree 0
foreach inst [$_blk getInsts] {
  if {[[$inst getMaster] isBlock]} { continue }
  set n [string map {\\ {}} [$inst getName]]
  set p [lindex [split $n ./] 0]
  if {[dict exists $regs $p]} { [dict get $regs $p] addInst $inst; incr nf } else { incr nfree } }
puts "OT_FRAME_FENCE fenced=$nf free=$nfree regions=[dict size $regs]"
