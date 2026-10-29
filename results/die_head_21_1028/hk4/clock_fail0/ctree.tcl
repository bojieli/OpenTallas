read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f [glob $::env(LIBDIR)/*RVT_$::env(CORNER)_nldm*.lib*] { read_liberty $f }
read_verilog /work/clock/ctree.v
link_design ctree
initialize_floorplan -die_area {0 0 17521.92 17556.48} -core_area {0 0 17521.92 17556.48} -site asap7sc7p5t
source /work/clock/make_tracks.tcl
place_pin -pin_name root -layer M9 -location {8760.960 8779.240} -pin_size {0.04 0.32}
place_pin -pin_name t_sp5_xw_o_shim__clk_t1 -layer M9 -location {8751.840 4098.528} -pin_size {0.04 0.32}
place_pin -pin_name t_sp5__clk_t18 -layer M9 -location {8787.360 4122.912} -pin_size {0.04 0.32}
place_pin -pin_name t_sp4__clk_t10 -layer M9 -location {8787.360 5182.368} -pin_size {0.04 0.32}
place_pin -pin_name t_sp4_xw_o_shim__clk_t1 -layer M9 -location {8751.840 6172.128} -pin_size {0.04 0.32}
place_pin -pin_name t_sp3__clk_t10 -layer M9 -location {8787.360 7255.968} -pin_size {0.04 0.32}
place_pin -pin_name t_sp3_xw_o_shim__clk_t1 -layer M9 -location {8751.840 8245.728} -pin_size {0.04 0.32}
place_pin -pin_name t_sp2__clk_t10 -layer M9 -location {8787.360 9329.568} -pin_size {0.04 0.32}
place_pin -pin_name t_sp2_xw_o_shim__clk_t1 -layer M9 -location {8751.840 10319.328} -pin_size {0.04 0.32}
place_pin -pin_name t_sp1__clk_t10 -layer M9 -location {8787.360 11403.168} -pin_size {0.04 0.32}
place_pin -pin_name t_sp1_xw_o_shim__clk_t1 -layer M9 -location {8751.840 12392.928} -pin_size {0.04 0.32}
place_pin -pin_name t_sp0__clk_t10 -layer M9 -location {8787.360 13476.768} -pin_size {0.04 0.32}
place_pin -pin_name t_sst5__clk_t7 -layer M9 -location {8743.200 1775.136} -pin_size {0.04 0.32}
place_pin -pin_name t_sst5__clk_t11 -layer M9 -location {8743.200 2164.448} -pin_size {0.04 0.32}
place_pin -pin_name t_sst5__clk_t4 -layer M9 -location {8410.272 1656.160} -pin_size {0.04 0.32}
place_pin -pin_name t_sst5__clk_t10 -layer M9 -location {8400.224 2135.072} -pin_size {0.04 0.32}
place_pin -pin_name t_sst5__clk_t3 -layer M9 -location {8059.488 1553.568} -pin_size {0.04 0.32}
place_pin -pin_name t_sst5__clk_t6 -layer M9 -location {8059.488 1775.136} -pin_size {0.04 0.32}
place_pin -pin_name t_sst5__clk -layer M9 -location {8040.032 2122.464} -pin_size {0.04 0.32}
place_pin -pin_name t_sst5__clk_t5 -layer M9 -location {7802.656 1681.312} -pin_size {0.04 0.32}
place_pin -pin_name t_sst5__clk_t2 -layer M9 -location {7708.832 1553.568} -pin_size {0.04 0.32}
place_pin -pin_name t_sst5__clk_t1 -layer M9 -location {7581.088 1347.872} -pin_size {0.04 0.32}
place_pin -pin_name t_sst5__clk_t9 -layer M9 -location {7610.336 2117.088} -pin_size {0.04 0.32}
place_pin -pin_name t_lk_HOST0__clk -layer M9 -location {7318.560 1252.832} -pin_size {0.04 0.32}
place_pin -pin_name t_sst5__clk_t8 -layer M9 -location {7335.840 2104.416} -pin_size {0.04 0.32}
place_pin -pin_name t_sst4__clk_t1 -layer M9 -location {7300.320 2164.448} -pin_size {0.04 0.32}
place_pin -pin_name t_sst4__clk_t2 -layer M9 -location {7025.824 2151.840} -pin_size {0.04 0.32}
place_pin -pin_name t_sst4__clk_t5 -layer M9 -location {6733.728 2104.416} -pin_size {0.04 0.32}
place_pin -pin_name t_sst4__clk -layer M9 -location {6596.128 2151.840} -pin_size {0.04 0.32}
place_pin -pin_name t_sst4__clk_t3 -layer M9 -location {6235.936 2151.840} -pin_size {0.04 0.32}
place_pin -pin_name t_sst4__clk_t4 -layer M9 -location {5892.960 2122.464} -pin_size {0.04 0.32}
place_pin -pin_name t_mesh0S__clk -layer M9 -location {5857.440 2151.840} -pin_size {0.04 0.32}
place_pin -pin_name t_mesh0S__clk_t2 -layer M9 -location {4797.920 1347.808} -pin_size {0.04 0.32}
place_pin -pin_name t_lk_WS0__clk -layer M9 -location {4432.800 1252.832} -pin_size {0.04 0.32}
place_pin -pin_name t_sst2__clk_t4 -layer M9 -location {4414.560 2112.864} -pin_size {0.04 0.32}
place_pin -pin_name t_mesh0S__clk_t1 -layer M9 -location {4450.080 2231.840} -pin_size {0.04 0.32}
place_pin -pin_name t_sst2__clk_t3 -layer M9 -location {4071.584 2231.840} -pin_size {0.04 0.32}
place_pin -pin_name t_sst2__clk -layer M9 -location {3711.392 2231.840} -pin_size {0.04 0.32}
place_pin -pin_name t_sst2__clk_t2 -layer M9 -location {3350.176 2231.840} -pin_size {0.04 0.32}
place_pin -pin_name t_sst1__clk_t8 -layer M9 -location {2971.680 2112.864} -pin_size {0.04 0.32}
place_pin -pin_name t_sst2__clk_t1 -layer M9 -location {3007.200 2334.432} -pin_size {0.04 0.32}
place_pin -pin_name t_sst1__clk_t7 -layer M9 -location {2701.088 2118.048} -pin_size {0.04 0.32}
place_pin -pin_name t_sst1__clk_t2 -layer M9 -location {2676.000 2339.808} -pin_size {0.04 0.32}
place_pin -pin_name t_sst1__clk_t6 -layer M9 -location {2415.392 2120.800} -pin_size {0.04 0.32}
place_pin -pin_name t_sst1__clk_t1 -layer M9 -location {2354.912 2342.432} -pin_size {0.04 0.32}
place_pin -pin_name t_sst1__clk -layer M9 -location {2083.872 1875.616} -pin_size {0.04 0.32}
place_pin -pin_name t_sst1__clk_t9 -layer M9 -location {2139.424 2095.584} -pin_size {0.04 0.32}
place_pin -pin_name t_sst1__clk_t14 -layer M9 -location {2025.568 1618.848} -pin_size {0.04 0.32}
place_pin -pin_name t_sst1__clk_t3 -layer M9 -location {2044.320 2317.152} -pin_size {0.04 0.32}
place_pin -pin_name t_sst1__clk_t11 -layer M9 -location {1981.088 1944.096} -pin_size {0.04 0.32}
place_pin -pin_name t_sst1__clk_t15 -layer M9 -location {1809.568 1347.872} -pin_size {0.04 0.32}
place_pin -pin_name t_sst1__clk_t13 -layer M9 -location {1803.936 1644.256} -pin_size {0.04 0.32}
place_pin -pin_name t_sst1__clk_t12 -layer M9 -location {1862.432 1924.064} -pin_size {0.04 0.32}
place_pin -pin_name t_sst1__clk_t5 -layer M9 -location {1859.232 2223.904} -pin_size {0.04 0.32}
place_pin -pin_name t_sst1__clk_t10 -layer M9 -location {1759.072 1983.328} -pin_size {0.04 0.32}
place_pin -pin_name t_sst1__clk_t4 -layer M9 -location {1756.448 2311.968} -pin_size {0.04 0.32}
place_pin -pin_name t_lk_WS1__clk -layer M9 -location {1547.040 1252.832} -pin_size {0.04 0.32}
place_pin -pin_name t_host__clk_t2 -layer M9 -location {8778.720 1553.568} -pin_size {0.04 0.32}
place_pin -pin_name t_host__clk_t3 -layer M9 -location {8778.720 1775.136} -pin_size {0.04 0.32}
place_pin -pin_name t_host__clk_t6 -layer M9 -location {8778.720 2122.464} -pin_size {0.04 0.32}
place_pin -pin_name t_host__clk_t7 -layer M9 -location {9064.864 2135.072} -pin_size {0.04 0.32}
place_pin -pin_name t_host__clk_t9 -layer M9 -location {9177.440 2540.192} -pin_size {0.04 0.32}
place_pin -pin_name t_sp5__clk_t1 -layer M9 -location {9134.944 2574.752} -pin_size {0.04 0.32}
place_pin -pin_name t_host__clk_t8 -layer M9 -location {9278.816 2239.264} -pin_size {0.04 0.32}
place_pin -pin_name t_host__clk -layer M9 -location {9525.088 2117.088} -pin_size {0.04 0.32}
place_pin -pin_name t_host__clk_t1 -layer M9 -location {9838.240 1347.872} -pin_size {0.04 0.32}
place_pin -pin_name t_host__clk_t5 -layer M9 -location {9864.608 2117.088} -pin_size {0.04 0.32}
place_pin -pin_name t_lk_HOST1__clk -layer M9 -location {10203.360 1252.832} -pin_size {0.04 0.32}
place_pin -pin_name t_host__clk_t4 -layer M9 -location {10186.080 2104.416} -pin_size {0.04 0.32}
place_pin -pin_name t_sst7__clk_t1 -layer M9 -location {10221.600 2164.448} -pin_size {0.04 0.32}
place_pin -pin_name t_sst7__clk_t2 -layer M9 -location {10496.096 2151.840} -pin_size {0.04 0.32}
place_pin -pin_name t_sst7__clk_t5 -layer M9 -location {10788.192 2104.416} -pin_size {0.04 0.32}
place_pin -pin_name t_sst7__clk -layer M9 -location {10925.792 2151.840} -pin_size {0.04 0.32}
place_pin -pin_name t_sst7__clk_t3 -layer M9 -location {11285.984 2151.840} -pin_size {0.04 0.32}
place_pin -pin_name t_sst7__clk_t4 -layer M9 -location {11628.960 2122.464} -pin_size {0.04 0.32}
place_pin -pin_name t_mesh7S__clk -layer M9 -location {11664.480 2151.840} -pin_size {0.04 0.32}
place_pin -pin_name t_mesh7S__clk_t2 -layer M9 -location {12724.000 1347.808} -pin_size {0.04 0.32}
place_pin -pin_name t_lk_ES0__clk -layer M9 -location {13089.120 1252.832} -pin_size {0.04 0.32}
place_pin -pin_name t_sst9__clk_t4 -layer M9 -location {13107.360 2112.864} -pin_size {0.04 0.32}
place_pin -pin_name t_mesh7S__clk_t1 -layer M9 -location {13071.840 2231.840} -pin_size {0.04 0.32}
place_pin -pin_name t_sst9__clk_t3 -layer M9 -location {13450.336 2231.840} -pin_size {0.04 0.32}
place_pin -pin_name t_sst9__clk -layer M9 -location {13810.528 2231.840} -pin_size {0.04 0.32}
place_pin -pin_name t_sst9__clk_t2 -layer M9 -location {14171.744 2231.840} -pin_size {0.04 0.32}
place_pin -pin_name t_sst10__clk_t8 -layer M9 -location {14550.240 2112.864} -pin_size {0.04 0.32}
place_pin -pin_name t_sst9__clk_t1 -layer M9 -location {14514.720 2334.432} -pin_size {0.04 0.32}
place_pin -pin_name t_sst10__clk_t7 -layer M9 -location {14820.832 2118.048} -pin_size {0.04 0.32}
place_pin -pin_name t_sst10__clk_t2 -layer M9 -location {14845.920 2339.808} -pin_size {0.04 0.32}
place_pin -pin_name t_sst10__clk_t6 -layer M9 -location {15106.528 2120.800} -pin_size {0.04 0.32}
place_pin -pin_name t_sst10__clk_t1 -layer M9 -location {15167.008 2342.432} -pin_size {0.04 0.32}
place_pin -pin_name t_sst10__clk -layer M9 -location {15438.048 1875.616} -pin_size {0.04 0.32}
place_pin -pin_name t_sst10__clk_t9 -layer M9 -location {15382.496 2095.584} -pin_size {0.04 0.32}
place_pin -pin_name t_sst10__clk_t14 -layer M9 -location {15496.352 1618.848} -pin_size {0.04 0.32}
place_pin -pin_name t_sst10__clk_t3 -layer M9 -location {15477.600 2317.152} -pin_size {0.04 0.32}
place_pin -pin_name t_sst10__clk_t11 -layer M9 -location {15540.832 1944.096} -pin_size {0.04 0.32}
place_pin -pin_name t_sst10__clk_t15 -layer M9 -location {15712.352 1347.872} -pin_size {0.04 0.32}
place_pin -pin_name t_sst10__clk_t13 -layer M9 -location {15717.984 1644.256} -pin_size {0.04 0.32}
place_pin -pin_name t_sst10__clk_t12 -layer M9 -location {15659.488 1924.064} -pin_size {0.04 0.32}
place_pin -pin_name t_sst10__clk_t5 -layer M9 -location {15662.688 2223.904} -pin_size {0.04 0.32}
place_pin -pin_name t_sst10__clk_t10 -layer M9 -location {15762.848 1983.328} -pin_size {0.04 0.32}
place_pin -pin_name t_sst10__clk_t4 -layer M9 -location {15765.472 2311.968} -pin_size {0.04 0.32}
place_pin -pin_name t_lk_ES1__clk -layer M9 -location {15974.880 1252.832} -pin_size {0.04 0.32}
place_pin -pin_name t_sp5_xw_o_shim__clk -layer M9 -location {8420.192 4098.528} -pin_size {0.04 0.32}
place_pin -pin_name t_sp5_bw_i_shim__clk -layer M9 -location {8419.168 3061.728} -pin_size {0.04 0.32}
place_pin -pin_name t_sp5_bw_i_shim__clk_t1 -layer M9 -location {8087.520 3061.728} -pin_size {0.04 0.32}
place_pin -pin_name t_tW5b0__clk -layer M9 -location {7715.040 2911.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tW5o0__clk -layer M9 -location {7716.000 3948.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tW5b1__clk -layer M9 -location {7006.560 2911.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tW5o1__clk -layer M9 -location {7007.520 3948.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tW5b2__clk -layer M9 -location {6298.080 2911.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tW5o2__clk -layer M9 -location {6299.040 3948.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tW5b3__clk -layer M9 -location {5589.600 2911.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tW5o3__clk -layer M9 -location {5590.560 3948.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tW5b4__clk -layer M9 -location {4881.120 2911.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tW5o4__clk -layer M9 -location {4882.080 3948.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tW5b5__clk -layer M9 -location {4172.640 2911.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tW5o5__clk -layer M9 -location {4173.600 3948.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tW5b6__clk -layer M9 -location {3464.160 2911.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tW5o6__clk -layer M9 -location {3465.120 3948.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tW5b7__clk -layer M9 -location {2755.680 2911.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tW5o7__clk -layer M9 -location {2756.640 3948.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tW5b8__clk -layer M9 -location {2047.200 2911.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tW5o8__clk -layer M9 -location {2048.160 3948.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tW5b9__clk -layer M9 -location {1338.720 2911.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tW5o9__clk -layer M9 -location {1339.680 3948.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tW5b10__clk -layer M9 -location {630.240 2911.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tW5o10__clk -layer M9 -location {631.200 3948.448} -pin_size {0.04 0.32}
place_pin -pin_name t_turnW5a__clk -layer M9 -location {258.720 4079.392} -pin_size {0.04 0.32}
place_pin -pin_name t_turnW5a__clk_t1 -layer M9 -location {212.192 3826.784} -pin_size {0.04 0.32}
place_pin -pin_name t_turnW5b__clk -layer M9 -location {189.600 3284.640} -pin_size {0.04 0.32}
place_pin -pin_name t_turnW5b__clk_t1 -layer M9 -location {189.600 3576.928} -pin_size {0.04 0.32}
place_pin -pin_name t_sp5__clk_t3 -layer M9 -location {8787.360 2956.512} -pin_size {0.04 0.32}
place_pin -pin_name t_sp5__clk_t5 -layer M9 -location {8787.360 3052.576} -pin_size {0.04 0.32}
place_pin -pin_name t_sp5__clk_t8 -layer M9 -location {8787.360 3157.088} -pin_size {0.04 0.32}
place_pin -pin_name t_sp5__clk_t16 -layer M9 -location {8787.360 3996.704} -pin_size {0.04 0.32}
place_pin -pin_name t_sp5__clk_t20 -layer M9 -location {8855.520 4160.992} -pin_size {0.04 0.32}
place_pin -pin_name t_sp5__clk_t21 -layer M9 -location {8855.520 4237.344} -pin_size {0.04 0.32}
place_pin -pin_name t_sp5__clk_t24 -layer M9 -location {8919.264 4613.792} -pin_size {0.04 0.32}
place_pin -pin_name t_sp5__clk_t19 -layer M9 -location {9005.280 4146.208} -pin_size {0.04 0.32}
place_pin -pin_name t_sp5__clk_t4 -layer M9 -location {9005.280 3016.224} -pin_size {0.04 0.32}
place_pin -pin_name t_sp5__clk_t7 -layer M9 -location {9005.280 3150.752} -pin_size {0.04 0.32}
place_pin -pin_name t_sp5__clk_t10 -layer M9 -location {9005.280 3336.672} -pin_size {0.04 0.32}
place_pin -pin_name t_sp5__clk_t11 -layer M9 -location {9005.280 3431.584} -pin_size {0.04 0.32}
place_pin -pin_name t_sp5__clk -layer M9 -location {9005.280 3605.984} -pin_size {0.04 0.32}
place_pin -pin_name t_sp5__clk_t13 -layer M9 -location {9005.280 3732.384} -pin_size {0.04 0.32}
place_pin -pin_name t_sp5__clk_t14 -layer M9 -location {9005.280 3938.208} -pin_size {0.04 0.32}
place_pin -pin_name t_sp5__clk_t22 -layer M9 -location {9119.008 4285.472} -pin_size {0.04 0.32}
place_pin -pin_name t_sp5__clk_t2 -layer M9 -location {9193.888 2903.072} -pin_size {0.04 0.32}
place_pin -pin_name t_sp5__clk_t9 -layer M9 -location {9193.888 3248.672} -pin_size {0.04 0.32}
place_pin -pin_name t_sp5__clk_t12 -layer M9 -location {9200.864 3594.272} -pin_size {0.04 0.32}
place_pin -pin_name t_sp5__clk_t15 -layer M9 -location {9201.120 3939.872} -pin_size {0.04 0.32}
place_pin -pin_name t_sp5__clk_t23 -layer M9 -location {9251.616 4285.472} -pin_size {0.04 0.32}
place_pin -pin_name t_sp5__clk_t25 -layer M9 -location {9204.832 4613.792} -pin_size {0.04 0.32}
place_pin -pin_name t_sp5__clk_t17 -layer M9 -location {9340.320 4089.376} -pin_size {0.04 0.32}
place_pin -pin_name t_sp5_xe_o_shim__clk -layer M9 -location {9374.880 4098.528} -pin_size {0.04 0.32}
place_pin -pin_name t_sp5__clk_t6 -layer M9 -location {9340.320 3061.728} -pin_size {0.04 0.32}
place_pin -pin_name t_sp5_be_i_shim__clk -layer M9 -location {9434.400 3061.728} -pin_size {0.04 0.32}
place_pin -pin_name t_tE5b0__clk -layer M9 -location {9806.880 2911.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tE5o0__clk -layer M9 -location {9805.920 3948.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tE5b1__clk -layer M9 -location {10515.360 2911.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tE5o1__clk -layer M9 -location {10514.400 3948.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tE5b2__clk -layer M9 -location {11223.840 2911.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tE5o2__clk -layer M9 -location {11222.880 3948.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tE5b3__clk -layer M9 -location {11932.320 2911.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tE5o3__clk -layer M9 -location {11931.360 3948.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tE5b4__clk -layer M9 -location {12640.800 2911.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tE5o4__clk -layer M9 -location {12639.840 3948.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tE5b5__clk -layer M9 -location {13349.280 2911.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tE5o5__clk -layer M9 -location {13348.320 3948.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tE5b6__clk -layer M9 -location {14057.760 2911.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tE5o6__clk -layer M9 -location {14056.800 3948.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tE5b7__clk -layer M9 -location {14766.240 2911.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tE5o7__clk -layer M9 -location {14765.280 3948.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tE5b8__clk -layer M9 -location {15474.720 2911.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tE5o8__clk -layer M9 -location {15473.760 3948.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tE5b9__clk -layer M9 -location {16183.200 2911.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tE5o9__clk -layer M9 -location {16182.240 3948.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tE5b10__clk -layer M9 -location {16891.680 2911.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tE5o10__clk -layer M9 -location {16890.720 3948.448} -pin_size {0.04 0.32}
place_pin -pin_name t_turnE5a__clk -layer M9 -location {17263.200 4079.392} -pin_size {0.04 0.32}
place_pin -pin_name t_turnE5a__clk_t1 -layer M9 -location {17309.728 3826.784} -pin_size {0.04 0.32}
place_pin -pin_name t_turnE5b__clk -layer M9 -location {17332.320 3284.640} -pin_size {0.04 0.32}
place_pin -pin_name t_turnE5b__clk_t1 -layer M9 -location {17332.320 3576.928} -pin_size {0.04 0.32}
place_pin -pin_name t_sp4_bw_i_shim__clk -layer M9 -location {8419.168 5135.328} -pin_size {0.04 0.32}
place_pin -pin_name t_sp4_bw_i_shim__clk_t1 -layer M9 -location {8087.520 5135.328} -pin_size {0.04 0.32}
place_pin -pin_name t_tW4b0__clk -layer M9 -location {7715.040 4985.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tW4b1__clk -layer M9 -location {7006.560 4985.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tW4b2__clk -layer M9 -location {6298.080 4985.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tW4b3__clk -layer M9 -location {5589.600 4985.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tW4b4__clk -layer M9 -location {4881.120 4985.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tW4b5__clk -layer M9 -location {4172.640 4985.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tW4b6__clk -layer M9 -location {3464.160 4985.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tW4b7__clk -layer M9 -location {2755.680 4985.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tW4b8__clk -layer M9 -location {2047.200 4985.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tW4b9__clk -layer M9 -location {1338.720 4985.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tW4b10__clk -layer M9 -location {630.240 4985.248} -pin_size {0.04 0.32}
place_pin -pin_name t_turnW4b__clk -layer M9 -location {189.600 5358.240} -pin_size {0.04 0.32}
place_pin -pin_name t_turnW4b__clk_t1 -layer M9 -location {189.600 5650.528} -pin_size {0.04 0.32}
place_pin -pin_name t_sp4__clk_t5 -layer M9 -location {8787.360 5018.656} -pin_size {0.04 0.32}
place_pin -pin_name t_sp4__clk_t8 -layer M9 -location {8899.680 5181.344} -pin_size {0.04 0.32}
place_pin -pin_name t_sp4__clk_t1 -layer M9 -location {8881.440 4648.352} -pin_size {0.04 0.32}
place_pin -pin_name t_sp4__clk_t13 -layer M9 -location {8862.752 5454.880} -pin_size {0.04 0.32}
place_pin -pin_name t_sp4__clk_t6 -layer M9 -location {9005.280 5077.664} -pin_size {0.04 0.32}
place_pin -pin_name t_sp4__clk_t3 -layer M9 -location {8946.208 4904.736} -pin_size {0.04 0.32}
place_pin -pin_name t_sp4__clk_t12 -layer M9 -location {9005.280 5444.384} -pin_size {0.04 0.32}
place_pin -pin_name t_sp4__clk_t14 -layer M9 -location {9005.280 5515.680} -pin_size {0.04 0.32}
place_pin -pin_name t_sp4__clk_t9 -layer M9 -location {9009.120 5182.368} -pin_size {0.04 0.32}
place_pin -pin_name t_sp4__clk_t2 -layer M9 -location {9090.272 4648.352} -pin_size {0.04 0.32}
place_pin -pin_name t_sp4__clk_t4 -layer M9 -location {9193.888 4976.672} -pin_size {0.04 0.32}
place_pin -pin_name t_sp4__clk_t11 -layer M9 -location {9193.888 5322.272} -pin_size {0.04 0.32}
place_pin -pin_name t_sp4__clk_t7 -layer M9 -location {9340.320 5135.328} -pin_size {0.04 0.32}
place_pin -pin_name t_sp4_be_i_shim__clk -layer M9 -location {9434.400 5135.328} -pin_size {0.04 0.32}
place_pin -pin_name t_tE4b0__clk -layer M9 -location {9806.880 4985.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tE4b1__clk -layer M9 -location {10515.360 4985.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tE4b2__clk -layer M9 -location {11223.840 4985.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tE4b3__clk -layer M9 -location {11932.320 4985.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tE4b4__clk -layer M9 -location {12640.800 4985.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tE4b5__clk -layer M9 -location {13349.280 4985.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tE4b6__clk -layer M9 -location {14057.760 4985.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tE4b7__clk -layer M9 -location {14766.240 4985.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tE4b8__clk -layer M9 -location {15474.720 4985.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tE4b9__clk -layer M9 -location {16183.200 4985.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tE4b10__clk -layer M9 -location {16891.680 4985.248} -pin_size {0.04 0.32}
place_pin -pin_name t_turnE4b__clk -layer M9 -location {17332.320 5358.240} -pin_size {0.04 0.32}
place_pin -pin_name t_turnE4b__clk_t1 -layer M9 -location {17332.320 5650.528} -pin_size {0.04 0.32}
place_pin -pin_name t_sp4_xw_o_shim__clk -layer M9 -location {8420.192 6172.128} -pin_size {0.04 0.32}
place_pin -pin_name t_tW4o0__clk -layer M9 -location {7716.000 6022.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tW4o1__clk -layer M9 -location {7007.520 6022.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tW4o2__clk -layer M9 -location {6299.040 6022.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tW4o3__clk -layer M9 -location {5590.560 6022.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tW4o4__clk -layer M9 -location {4882.080 6022.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tW4o5__clk -layer M9 -location {4173.600 6022.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tW4o6__clk -layer M9 -location {3465.120 6022.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tW4o7__clk -layer M9 -location {2756.640 6022.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tW4o8__clk -layer M9 -location {2048.160 6022.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tW4o9__clk -layer M9 -location {1339.680 6022.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tW4o10__clk -layer M9 -location {631.200 6022.048} -pin_size {0.04 0.32}
place_pin -pin_name t_turnW4a__clk -layer M9 -location {258.720 6152.992} -pin_size {0.04 0.32}
place_pin -pin_name t_turnW4a__clk_t1 -layer M9 -location {212.192 5900.384} -pin_size {0.04 0.32}
place_pin -pin_name t_sp4__clk_t22 -layer M9 -location {8787.360 6091.552} -pin_size {0.04 0.32}
place_pin -pin_name t_sp4__clk_t26 -layer M9 -location {8855.520 6216.736} -pin_size {0.04 0.32}
place_pin -pin_name t_sp4__clk -layer M9 -location {8855.520 5727.648} -pin_size {0.04 0.32}
place_pin -pin_name t_sp4__clk_t19 -layer M9 -location {8865.120 6000.416} -pin_size {0.04 0.32}
place_pin -pin_name t_sp4__clk_t28 -layer M9 -location {8855.520 6261.344} -pin_size {0.04 0.32}
place_pin -pin_name t_sp4__clk_t29 -layer M9 -location {8855.520 6303.584} -pin_size {0.04 0.32}
place_pin -pin_name t_sp4__clk_t32 -layer M9 -location {8919.264 6687.392} -pin_size {0.04 0.32}
place_pin -pin_name t_sp4__clk_t24 -layer M9 -location {9005.280 6168.416} -pin_size {0.04 0.32}
place_pin -pin_name t_sp4__clk_t16 -layer M9 -location {9005.280 5723.936} -pin_size {0.04 0.32}
place_pin -pin_name t_sp4__clk_t17 -layer M9 -location {9005.280 5824.288} -pin_size {0.04 0.32}
place_pin -pin_name t_sp4__clk_t18 -layer M9 -location {9005.280 5992.224} -pin_size {0.04 0.32}
place_pin -pin_name t_sp4__clk_t27 -layer M9 -location {9005.280 6255.520} -pin_size {0.04 0.32}
place_pin -pin_name t_sp4__clk_t23 -layer M9 -location {9066.272 6143.456} -pin_size {0.04 0.32}
place_pin -pin_name t_sp4__clk_t20 -layer M9 -location {9117.856 6013.472} -pin_size {0.04 0.32}
place_pin -pin_name t_sp4__clk_t30 -layer M9 -location {9103.712 6303.584} -pin_size {0.04 0.32}
place_pin -pin_name t_sp4__clk_t15 -layer M9 -location {9193.888 5667.872} -pin_size {0.04 0.32}
place_pin -pin_name t_sp4__clk_t31 -layer M9 -location {9218.400 6359.072} -pin_size {0.04 0.32}
place_pin -pin_name t_sp4__clk_t33 -layer M9 -location {9204.832 6687.392} -pin_size {0.04 0.32}
place_pin -pin_name t_sp4__clk_t21 -layer M9 -location {9263.520 6013.472} -pin_size {0.04 0.32}
place_pin -pin_name t_sp4_xe_o_shim__clk -layer M9 -location {9374.880 6172.128} -pin_size {0.04 0.32}
place_pin -pin_name t_sp4__clk_t25 -layer M9 -location {9340.320 6189.088} -pin_size {0.04 0.32}
place_pin -pin_name t_tE4o0__clk -layer M9 -location {9805.920 6022.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tE4o1__clk -layer M9 -location {10514.400 6022.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tE4o2__clk -layer M9 -location {11222.880 6022.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tE4o3__clk -layer M9 -location {11931.360 6022.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tE4o4__clk -layer M9 -location {12639.840 6022.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tE4o5__clk -layer M9 -location {13348.320 6022.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tE4o6__clk -layer M9 -location {14056.800 6022.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tE4o7__clk -layer M9 -location {14765.280 6022.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tE4o8__clk -layer M9 -location {15473.760 6022.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tE4o9__clk -layer M9 -location {16182.240 6022.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tE4o10__clk -layer M9 -location {16890.720 6022.048} -pin_size {0.04 0.32}
place_pin -pin_name t_turnE4a__clk -layer M9 -location {17263.200 6152.992} -pin_size {0.04 0.32}
place_pin -pin_name t_turnE4a__clk_t1 -layer M9 -location {17309.728 5900.384} -pin_size {0.04 0.32}
place_pin -pin_name t_sp3_bw_i_shim__clk -layer M9 -location {8419.168 7208.928} -pin_size {0.04 0.32}
place_pin -pin_name t_sp3_bw_i_shim__clk_t1 -layer M9 -location {8087.520 7208.928} -pin_size {0.04 0.32}
place_pin -pin_name t_tW3b0__clk -layer M9 -location {7715.040 7058.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tW3b1__clk -layer M9 -location {7006.560 7058.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tW3b2__clk -layer M9 -location {6298.080 7058.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tW3b3__clk -layer M9 -location {5589.600 7058.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tW3b4__clk -layer M9 -location {4881.120 7058.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tW3b5__clk -layer M9 -location {4172.640 7058.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tW3b6__clk -layer M9 -location {3464.160 7058.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tW3b7__clk -layer M9 -location {2755.680 7058.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tW3b8__clk -layer M9 -location {2047.200 7058.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tW3b9__clk -layer M9 -location {1338.720 7058.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tW3b10__clk -layer M9 -location {630.240 7058.848} -pin_size {0.04 0.32}
place_pin -pin_name t_turnW3b__clk -layer M9 -location {189.600 7431.840} -pin_size {0.04 0.32}
place_pin -pin_name t_turnW3b__clk_t1 -layer M9 -location {189.600 7724.128} -pin_size {0.04 0.32}
place_pin -pin_name t_sp3__clk_t5 -layer M9 -location {8787.360 7092.256} -pin_size {0.04 0.32}
place_pin -pin_name t_sp3__clk_t8 -layer M9 -location {8899.680 7254.944} -pin_size {0.04 0.32}
place_pin -pin_name t_sp3__clk_t1 -layer M9 -location {8881.440 6721.952} -pin_size {0.04 0.32}
place_pin -pin_name t_sp3__clk_t13 -layer M9 -location {8862.752 7528.480} -pin_size {0.04 0.32}
place_pin -pin_name t_sp3__clk_t6 -layer M9 -location {9005.280 7151.264} -pin_size {0.04 0.32}
place_pin -pin_name t_sp3__clk_t3 -layer M9 -location {8946.208 6978.336} -pin_size {0.04 0.32}
place_pin -pin_name t_sp3__clk_t12 -layer M9 -location {9005.280 7517.984} -pin_size {0.04 0.32}
place_pin -pin_name t_sp3__clk_t14 -layer M9 -location {9005.280 7589.280} -pin_size {0.04 0.32}
place_pin -pin_name t_sp3__clk_t9 -layer M9 -location {9009.120 7255.968} -pin_size {0.04 0.32}
place_pin -pin_name t_sp3__clk_t2 -layer M9 -location {9090.272 6721.952} -pin_size {0.04 0.32}
place_pin -pin_name t_sp3__clk_t4 -layer M9 -location {9193.888 7050.272} -pin_size {0.04 0.32}
place_pin -pin_name t_sp3__clk_t11 -layer M9 -location {9193.888 7395.872} -pin_size {0.04 0.32}
place_pin -pin_name t_sp3__clk_t7 -layer M9 -location {9340.320 7208.928} -pin_size {0.04 0.32}
place_pin -pin_name t_sp3_be_i_shim__clk -layer M9 -location {9434.400 7208.928} -pin_size {0.04 0.32}
place_pin -pin_name t_tE3b0__clk -layer M9 -location {9806.880 7058.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tE3b1__clk -layer M9 -location {10515.360 7058.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tE3b2__clk -layer M9 -location {11223.840 7058.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tE3b3__clk -layer M9 -location {11932.320 7058.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tE3b4__clk -layer M9 -location {12640.800 7058.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tE3b5__clk -layer M9 -location {13349.280 7058.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tE3b6__clk -layer M9 -location {14057.760 7058.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tE3b7__clk -layer M9 -location {14766.240 7058.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tE3b8__clk -layer M9 -location {15474.720 7058.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tE3b9__clk -layer M9 -location {16183.200 7058.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tE3b10__clk -layer M9 -location {16891.680 7058.848} -pin_size {0.04 0.32}
place_pin -pin_name t_turnE3b__clk -layer M9 -location {17332.320 7431.840} -pin_size {0.04 0.32}
place_pin -pin_name t_turnE3b__clk_t1 -layer M9 -location {17332.320 7724.128} -pin_size {0.04 0.32}
place_pin -pin_name t_sp3_xw_o_shim__clk -layer M9 -location {8420.192 8245.728} -pin_size {0.04 0.32}
place_pin -pin_name t_tW3o0__clk -layer M9 -location {7716.000 8095.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tW3o1__clk -layer M9 -location {7007.520 8095.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tW3o2__clk -layer M9 -location {6299.040 8095.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tW3o3__clk -layer M9 -location {5590.560 8095.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tW3o4__clk -layer M9 -location {4882.080 8095.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tW3o5__clk -layer M9 -location {4173.600 8095.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tW3o6__clk -layer M9 -location {3465.120 8095.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tW3o7__clk -layer M9 -location {2756.640 8095.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tW3o8__clk -layer M9 -location {2048.160 8095.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tW3o9__clk -layer M9 -location {1339.680 8095.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tW3o10__clk -layer M9 -location {631.200 8095.648} -pin_size {0.04 0.32}
place_pin -pin_name t_turnW3a__clk -layer M9 -location {258.720 8226.592} -pin_size {0.04 0.32}
place_pin -pin_name t_turnW3a__clk_t1 -layer M9 -location {212.192 7973.984} -pin_size {0.04 0.32}
place_pin -pin_name t_sp3__clk_t22 -layer M9 -location {8787.360 8165.152} -pin_size {0.04 0.32}
place_pin -pin_name t_sp3__clk_t26 -layer M9 -location {8855.520 8290.336} -pin_size {0.04 0.32}
place_pin -pin_name t_sp3__clk -layer M9 -location {8855.520 7801.248} -pin_size {0.04 0.32}
place_pin -pin_name t_sp3__clk_t19 -layer M9 -location {8865.120 8074.016} -pin_size {0.04 0.32}
place_pin -pin_name t_sp3__clk_t28 -layer M9 -location {8855.520 8334.944} -pin_size {0.04 0.32}
place_pin -pin_name t_sp3__clk_t29 -layer M9 -location {8855.520 8377.184} -pin_size {0.04 0.32}
place_pin -pin_name t_sp3__clk_t32 -layer M9 -location {8919.264 8760.992} -pin_size {0.04 0.32}
place_pin -pin_name t_sp3__clk_t24 -layer M9 -location {9005.280 8242.016} -pin_size {0.04 0.32}
place_pin -pin_name t_sp3__clk_t16 -layer M9 -location {9005.280 7797.536} -pin_size {0.04 0.32}
place_pin -pin_name t_sp3__clk_t17 -layer M9 -location {9005.280 7897.888} -pin_size {0.04 0.32}
place_pin -pin_name t_sp3__clk_t18 -layer M9 -location {9005.280 8065.824} -pin_size {0.04 0.32}
place_pin -pin_name t_sp3__clk_t27 -layer M9 -location {9005.280 8329.120} -pin_size {0.04 0.32}
place_pin -pin_name t_sp3__clk_t23 -layer M9 -location {9066.272 8217.056} -pin_size {0.04 0.32}
place_pin -pin_name t_sp3__clk_t20 -layer M9 -location {9117.856 8087.072} -pin_size {0.04 0.32}
place_pin -pin_name t_sp3__clk_t30 -layer M9 -location {9103.712 8377.184} -pin_size {0.04 0.32}
place_pin -pin_name t_sp3__clk_t15 -layer M9 -location {9193.888 7741.472} -pin_size {0.04 0.32}
place_pin -pin_name t_sp3__clk_t31 -layer M9 -location {9218.400 8432.672} -pin_size {0.04 0.32}
place_pin -pin_name t_sp3__clk_t33 -layer M9 -location {9204.832 8760.992} -pin_size {0.04 0.32}
place_pin -pin_name t_sp3__clk_t21 -layer M9 -location {9263.520 8087.072} -pin_size {0.04 0.32}
place_pin -pin_name t_sp3_xe_o_shim__clk -layer M9 -location {9374.880 8245.728} -pin_size {0.04 0.32}
place_pin -pin_name t_sp3__clk_t25 -layer M9 -location {9340.320 8262.688} -pin_size {0.04 0.32}
place_pin -pin_name t_tE3o0__clk -layer M9 -location {9805.920 8095.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tE3o1__clk -layer M9 -location {10514.400 8095.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tE3o2__clk -layer M9 -location {11222.880 8095.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tE3o3__clk -layer M9 -location {11931.360 8095.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tE3o4__clk -layer M9 -location {12639.840 8095.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tE3o5__clk -layer M9 -location {13348.320 8095.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tE3o6__clk -layer M9 -location {14056.800 8095.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tE3o7__clk -layer M9 -location {14765.280 8095.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tE3o8__clk -layer M9 -location {15473.760 8095.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tE3o9__clk -layer M9 -location {16182.240 8095.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tE3o10__clk -layer M9 -location {16890.720 8095.648} -pin_size {0.04 0.32}
place_pin -pin_name t_turnE3a__clk -layer M9 -location {17263.200 8226.592} -pin_size {0.04 0.32}
place_pin -pin_name t_turnE3a__clk_t1 -layer M9 -location {17309.728 7973.984} -pin_size {0.04 0.32}
place_pin -pin_name t_sp2_bw_i_shim__clk -layer M9 -location {8419.168 9282.528} -pin_size {0.04 0.32}
place_pin -pin_name t_sp2_bw_i_shim__clk_t1 -layer M9 -location {8087.520 9282.528} -pin_size {0.04 0.32}
place_pin -pin_name t_tW2b0__clk -layer M9 -location {7715.040 9132.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tW2b1__clk -layer M9 -location {7006.560 9132.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tW2b2__clk -layer M9 -location {6298.080 9132.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tW2b3__clk -layer M9 -location {5589.600 9132.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tW2b4__clk -layer M9 -location {4881.120 9132.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tW2b5__clk -layer M9 -location {4172.640 9132.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tW2b6__clk -layer M9 -location {3464.160 9132.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tW2b7__clk -layer M9 -location {2755.680 9132.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tW2b8__clk -layer M9 -location {2047.200 9132.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tW2b9__clk -layer M9 -location {1338.720 9132.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tW2b10__clk -layer M9 -location {630.240 9132.448} -pin_size {0.04 0.32}
place_pin -pin_name t_turnW2b__clk -layer M9 -location {189.600 9505.440} -pin_size {0.04 0.32}
place_pin -pin_name t_turnW2b__clk_t1 -layer M9 -location {189.600 9797.728} -pin_size {0.04 0.32}
place_pin -pin_name t_sp2__clk_t5 -layer M9 -location {8787.360 9165.856} -pin_size {0.04 0.32}
place_pin -pin_name t_sp2__clk_t8 -layer M9 -location {8899.680 9328.544} -pin_size {0.04 0.32}
place_pin -pin_name t_sp2__clk_t1 -layer M9 -location {8881.440 8795.552} -pin_size {0.04 0.32}
place_pin -pin_name t_sp2__clk_t13 -layer M9 -location {8862.752 9602.080} -pin_size {0.04 0.32}
place_pin -pin_name t_sp2__clk_t6 -layer M9 -location {9005.280 9224.864} -pin_size {0.04 0.32}
place_pin -pin_name t_sp2__clk_t3 -layer M9 -location {8946.208 9051.936} -pin_size {0.04 0.32}
place_pin -pin_name t_sp2__clk_t12 -layer M9 -location {9005.280 9591.584} -pin_size {0.04 0.32}
place_pin -pin_name t_sp2__clk_t14 -layer M9 -location {9005.280 9662.880} -pin_size {0.04 0.32}
place_pin -pin_name t_sp2__clk_t9 -layer M9 -location {9009.120 9329.568} -pin_size {0.04 0.32}
place_pin -pin_name t_sp2__clk_t2 -layer M9 -location {9090.272 8795.552} -pin_size {0.04 0.32}
place_pin -pin_name t_sp2__clk_t4 -layer M9 -location {9193.888 9123.872} -pin_size {0.04 0.32}
place_pin -pin_name t_sp2__clk_t11 -layer M9 -location {9193.888 9469.472} -pin_size {0.04 0.32}
place_pin -pin_name t_sp2__clk_t7 -layer M9 -location {9340.320 9282.528} -pin_size {0.04 0.32}
place_pin -pin_name t_sp2_be_i_shim__clk -layer M9 -location {9434.400 9282.528} -pin_size {0.04 0.32}
place_pin -pin_name t_tE2b0__clk -layer M9 -location {9806.880 9132.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tE2b1__clk -layer M9 -location {10515.360 9132.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tE2b2__clk -layer M9 -location {11223.840 9132.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tE2b3__clk -layer M9 -location {11932.320 9132.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tE2b4__clk -layer M9 -location {12640.800 9132.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tE2b5__clk -layer M9 -location {13349.280 9132.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tE2b6__clk -layer M9 -location {14057.760 9132.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tE2b7__clk -layer M9 -location {14766.240 9132.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tE2b8__clk -layer M9 -location {15474.720 9132.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tE2b9__clk -layer M9 -location {16183.200 9132.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tE2b10__clk -layer M9 -location {16891.680 9132.448} -pin_size {0.04 0.32}
place_pin -pin_name t_turnE2b__clk -layer M9 -location {17332.320 9505.440} -pin_size {0.04 0.32}
place_pin -pin_name t_turnE2b__clk_t1 -layer M9 -location {17332.320 9797.728} -pin_size {0.04 0.32}
place_pin -pin_name t_sp2_xw_o_shim__clk -layer M9 -location {8420.192 10319.328} -pin_size {0.04 0.32}
place_pin -pin_name t_tW2o0__clk -layer M9 -location {7716.000 10169.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tW2o1__clk -layer M9 -location {7007.520 10169.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tW2o2__clk -layer M9 -location {6299.040 10169.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tW2o3__clk -layer M9 -location {5590.560 10169.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tW2o4__clk -layer M9 -location {4882.080 10169.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tW2o5__clk -layer M9 -location {4173.600 10169.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tW2o6__clk -layer M9 -location {3465.120 10169.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tW2o7__clk -layer M9 -location {2756.640 10169.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tW2o8__clk -layer M9 -location {2048.160 10169.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tW2o9__clk -layer M9 -location {1339.680 10169.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tW2o10__clk -layer M9 -location {631.200 10169.248} -pin_size {0.04 0.32}
place_pin -pin_name t_turnW2a__clk -layer M9 -location {258.720 10300.192} -pin_size {0.04 0.32}
place_pin -pin_name t_turnW2a__clk_t1 -layer M9 -location {212.192 10047.584} -pin_size {0.04 0.32}
place_pin -pin_name t_sp2__clk_t22 -layer M9 -location {8787.360 10238.752} -pin_size {0.04 0.32}
place_pin -pin_name t_sp2__clk_t26 -layer M9 -location {8855.520 10363.936} -pin_size {0.04 0.32}
place_pin -pin_name t_sp2__clk -layer M9 -location {8855.520 9874.848} -pin_size {0.04 0.32}
place_pin -pin_name t_sp2__clk_t19 -layer M9 -location {8865.120 10147.616} -pin_size {0.04 0.32}
place_pin -pin_name t_sp2__clk_t28 -layer M9 -location {8855.520 10408.544} -pin_size {0.04 0.32}
place_pin -pin_name t_sp2__clk_t29 -layer M9 -location {8855.520 10450.784} -pin_size {0.04 0.32}
place_pin -pin_name t_sp2__clk_t32 -layer M9 -location {8919.264 10834.592} -pin_size {0.04 0.32}
place_pin -pin_name t_sp2__clk_t24 -layer M9 -location {9005.280 10315.616} -pin_size {0.04 0.32}
place_pin -pin_name t_sp2__clk_t16 -layer M9 -location {9005.280 9871.136} -pin_size {0.04 0.32}
place_pin -pin_name t_sp2__clk_t17 -layer M9 -location {9005.280 9971.488} -pin_size {0.04 0.32}
place_pin -pin_name t_sp2__clk_t18 -layer M9 -location {9005.280 10139.424} -pin_size {0.04 0.32}
place_pin -pin_name t_sp2__clk_t27 -layer M9 -location {9005.280 10402.720} -pin_size {0.04 0.32}
place_pin -pin_name t_sp2__clk_t23 -layer M9 -location {9066.272 10290.656} -pin_size {0.04 0.32}
place_pin -pin_name t_sp2__clk_t20 -layer M9 -location {9117.856 10160.672} -pin_size {0.04 0.32}
place_pin -pin_name t_sp2__clk_t30 -layer M9 -location {9103.712 10450.784} -pin_size {0.04 0.32}
place_pin -pin_name t_sp2__clk_t15 -layer M9 -location {9193.888 9815.072} -pin_size {0.04 0.32}
place_pin -pin_name t_sp2__clk_t31 -layer M9 -location {9218.400 10506.272} -pin_size {0.04 0.32}
place_pin -pin_name t_sp2__clk_t33 -layer M9 -location {9204.832 10834.592} -pin_size {0.04 0.32}
place_pin -pin_name t_sp2__clk_t21 -layer M9 -location {9263.520 10160.672} -pin_size {0.04 0.32}
place_pin -pin_name t_sp2_xe_o_shim__clk -layer M9 -location {9374.880 10319.328} -pin_size {0.04 0.32}
place_pin -pin_name t_sp2__clk_t25 -layer M9 -location {9340.320 10336.288} -pin_size {0.04 0.32}
place_pin -pin_name t_tE2o0__clk -layer M9 -location {9805.920 10169.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tE2o1__clk -layer M9 -location {10514.400 10169.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tE2o2__clk -layer M9 -location {11222.880 10169.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tE2o3__clk -layer M9 -location {11931.360 10169.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tE2o4__clk -layer M9 -location {12639.840 10169.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tE2o5__clk -layer M9 -location {13348.320 10169.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tE2o6__clk -layer M9 -location {14056.800 10169.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tE2o7__clk -layer M9 -location {14765.280 10169.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tE2o8__clk -layer M9 -location {15473.760 10169.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tE2o9__clk -layer M9 -location {16182.240 10169.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tE2o10__clk -layer M9 -location {16890.720 10169.248} -pin_size {0.04 0.32}
place_pin -pin_name t_turnE2a__clk -layer M9 -location {17263.200 10300.192} -pin_size {0.04 0.32}
place_pin -pin_name t_turnE2a__clk_t1 -layer M9 -location {17309.728 10047.584} -pin_size {0.04 0.32}
place_pin -pin_name t_sp1_bw_i_shim__clk -layer M9 -location {8419.168 11356.128} -pin_size {0.04 0.32}
place_pin -pin_name t_sp1_bw_i_shim__clk_t1 -layer M9 -location {8087.520 11356.128} -pin_size {0.04 0.32}
place_pin -pin_name t_tW1b0__clk -layer M9 -location {7715.040 11206.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tW1b1__clk -layer M9 -location {7006.560 11206.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tW1b2__clk -layer M9 -location {6298.080 11206.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tW1b3__clk -layer M9 -location {5589.600 11206.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tW1b4__clk -layer M9 -location {4881.120 11206.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tW1b5__clk -layer M9 -location {4172.640 11206.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tW1b6__clk -layer M9 -location {3464.160 11206.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tW1b7__clk -layer M9 -location {2755.680 11206.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tW1b8__clk -layer M9 -location {2047.200 11206.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tW1b9__clk -layer M9 -location {1338.720 11206.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tW1b10__clk -layer M9 -location {630.240 11206.048} -pin_size {0.04 0.32}
place_pin -pin_name t_turnW1b__clk -layer M9 -location {189.600 11579.040} -pin_size {0.04 0.32}
place_pin -pin_name t_turnW1b__clk_t1 -layer M9 -location {189.600 11871.328} -pin_size {0.04 0.32}
place_pin -pin_name t_sp1__clk_t5 -layer M9 -location {8787.360 11239.456} -pin_size {0.04 0.32}
place_pin -pin_name t_sp1__clk_t8 -layer M9 -location {8899.680 11402.144} -pin_size {0.04 0.32}
place_pin -pin_name t_sp1__clk_t1 -layer M9 -location {8881.440 10869.152} -pin_size {0.04 0.32}
place_pin -pin_name t_sp1__clk_t13 -layer M9 -location {8862.752 11675.680} -pin_size {0.04 0.32}
place_pin -pin_name t_sp1__clk_t6 -layer M9 -location {9005.280 11298.464} -pin_size {0.04 0.32}
place_pin -pin_name t_sp1__clk_t3 -layer M9 -location {8946.208 11125.536} -pin_size {0.04 0.32}
place_pin -pin_name t_sp1__clk_t12 -layer M9 -location {9005.280 11665.184} -pin_size {0.04 0.32}
place_pin -pin_name t_sp1__clk_t14 -layer M9 -location {9005.280 11736.480} -pin_size {0.04 0.32}
place_pin -pin_name t_sp1__clk_t9 -layer M9 -location {9009.120 11403.168} -pin_size {0.04 0.32}
place_pin -pin_name t_sp1__clk_t2 -layer M9 -location {9090.272 10869.152} -pin_size {0.04 0.32}
place_pin -pin_name t_sp1__clk_t4 -layer M9 -location {9193.888 11197.472} -pin_size {0.04 0.32}
place_pin -pin_name t_sp1__clk_t11 -layer M9 -location {9193.888 11543.072} -pin_size {0.04 0.32}
place_pin -pin_name t_sp1__clk_t7 -layer M9 -location {9340.320 11356.128} -pin_size {0.04 0.32}
place_pin -pin_name t_sp1_be_i_shim__clk -layer M9 -location {9434.400 11356.128} -pin_size {0.04 0.32}
place_pin -pin_name t_tE1b0__clk -layer M9 -location {9806.880 11206.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tE1b1__clk -layer M9 -location {10515.360 11206.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tE1b2__clk -layer M9 -location {11223.840 11206.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tE1b3__clk -layer M9 -location {11932.320 11206.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tE1b4__clk -layer M9 -location {12640.800 11206.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tE1b5__clk -layer M9 -location {13349.280 11206.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tE1b6__clk -layer M9 -location {14057.760 11206.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tE1b7__clk -layer M9 -location {14766.240 11206.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tE1b8__clk -layer M9 -location {15474.720 11206.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tE1b9__clk -layer M9 -location {16183.200 11206.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tE1b10__clk -layer M9 -location {16891.680 11206.048} -pin_size {0.04 0.32}
place_pin -pin_name t_turnE1b__clk -layer M9 -location {17332.320 11579.040} -pin_size {0.04 0.32}
place_pin -pin_name t_turnE1b__clk_t1 -layer M9 -location {17332.320 11871.328} -pin_size {0.04 0.32}
place_pin -pin_name t_sp1_xw_o_shim__clk -layer M9 -location {8420.192 12392.928} -pin_size {0.04 0.32}
place_pin -pin_name t_tW1o0__clk -layer M9 -location {7716.000 12242.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tW1o1__clk -layer M9 -location {7007.520 12242.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tW1o2__clk -layer M9 -location {6299.040 12242.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tW1o3__clk -layer M9 -location {5590.560 12242.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tW1o4__clk -layer M9 -location {4882.080 12242.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tW1o5__clk -layer M9 -location {4173.600 12242.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tW1o6__clk -layer M9 -location {3465.120 12242.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tW1o7__clk -layer M9 -location {2756.640 12242.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tW1o8__clk -layer M9 -location {2048.160 12242.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tW1o9__clk -layer M9 -location {1339.680 12242.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tW1o10__clk -layer M9 -location {631.200 12242.848} -pin_size {0.04 0.32}
place_pin -pin_name t_turnW1a__clk -layer M9 -location {258.720 12373.792} -pin_size {0.04 0.32}
place_pin -pin_name t_turnW1a__clk_t1 -layer M9 -location {212.192 12121.184} -pin_size {0.04 0.32}
place_pin -pin_name t_sp1__clk_t22 -layer M9 -location {8787.360 12312.352} -pin_size {0.04 0.32}
place_pin -pin_name t_sp1__clk_t26 -layer M9 -location {8855.520 12437.536} -pin_size {0.04 0.32}
place_pin -pin_name t_sp1__clk -layer M9 -location {8855.520 11948.448} -pin_size {0.04 0.32}
place_pin -pin_name t_sp1__clk_t19 -layer M9 -location {8865.120 12221.216} -pin_size {0.04 0.32}
place_pin -pin_name t_sp1__clk_t28 -layer M9 -location {8855.520 12482.144} -pin_size {0.04 0.32}
place_pin -pin_name t_sp1__clk_t29 -layer M9 -location {8855.520 12524.384} -pin_size {0.04 0.32}
place_pin -pin_name t_sp1__clk_t32 -layer M9 -location {8919.264 12908.192} -pin_size {0.04 0.32}
place_pin -pin_name t_sp1__clk_t24 -layer M9 -location {9005.280 12389.216} -pin_size {0.04 0.32}
place_pin -pin_name t_sp1__clk_t16 -layer M9 -location {9005.280 11944.736} -pin_size {0.04 0.32}
place_pin -pin_name t_sp1__clk_t17 -layer M9 -location {9005.280 12045.088} -pin_size {0.04 0.32}
place_pin -pin_name t_sp1__clk_t18 -layer M9 -location {9005.280 12213.024} -pin_size {0.04 0.32}
place_pin -pin_name t_sp1__clk_t27 -layer M9 -location {9005.280 12476.320} -pin_size {0.04 0.32}
place_pin -pin_name t_sp1__clk_t23 -layer M9 -location {9066.272 12364.256} -pin_size {0.04 0.32}
place_pin -pin_name t_sp1__clk_t20 -layer M9 -location {9117.856 12234.272} -pin_size {0.04 0.32}
place_pin -pin_name t_sp1__clk_t30 -layer M9 -location {9103.712 12524.384} -pin_size {0.04 0.32}
place_pin -pin_name t_sp1__clk_t15 -layer M9 -location {9193.888 11888.672} -pin_size {0.04 0.32}
place_pin -pin_name t_sp1__clk_t31 -layer M9 -location {9218.400 12579.872} -pin_size {0.04 0.32}
place_pin -pin_name t_sp1__clk_t33 -layer M9 -location {9204.832 12908.192} -pin_size {0.04 0.32}
place_pin -pin_name t_sp1__clk_t21 -layer M9 -location {9263.520 12234.272} -pin_size {0.04 0.32}
place_pin -pin_name t_sp1_xe_o_shim__clk -layer M9 -location {9374.880 12392.928} -pin_size {0.04 0.32}
place_pin -pin_name t_sp1__clk_t25 -layer M9 -location {9340.320 12409.888} -pin_size {0.04 0.32}
place_pin -pin_name t_tE1o0__clk -layer M9 -location {9805.920 12242.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tE1o1__clk -layer M9 -location {10514.400 12242.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tE1o2__clk -layer M9 -location {11222.880 12242.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tE1o3__clk -layer M9 -location {11931.360 12242.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tE1o4__clk -layer M9 -location {12639.840 12242.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tE1o5__clk -layer M9 -location {13348.320 12242.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tE1o6__clk -layer M9 -location {14056.800 12242.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tE1o7__clk -layer M9 -location {14765.280 12242.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tE1o8__clk -layer M9 -location {15473.760 12242.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tE1o9__clk -layer M9 -location {16182.240 12242.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tE1o10__clk -layer M9 -location {16890.720 12242.848} -pin_size {0.04 0.32}
place_pin -pin_name t_turnE1a__clk -layer M9 -location {17263.200 12373.792} -pin_size {0.04 0.32}
place_pin -pin_name t_turnE1a__clk_t1 -layer M9 -location {17309.728 12121.184} -pin_size {0.04 0.32}
place_pin -pin_name t_sp0_xw_o_shim__clk_t1 -layer M9 -location {8751.840 14466.528} -pin_size {0.04 0.32}
place_pin -pin_name t_sp0_bw_i_shim__clk -layer M9 -location {8419.168 13429.728} -pin_size {0.04 0.32}
place_pin -pin_name t_sp0_xw_o_shim__clk -layer M9 -location {8420.192 14466.528} -pin_size {0.04 0.32}
place_pin -pin_name t_sp0_bw_i_shim__clk_t1 -layer M9 -location {8087.520 13429.728} -pin_size {0.04 0.32}
place_pin -pin_name t_tW0b0__clk -layer M9 -location {7715.040 13279.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tW0o0__clk -layer M9 -location {7716.000 14316.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tW0b1__clk -layer M9 -location {7006.560 13279.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tW0o1__clk -layer M9 -location {7007.520 14316.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tW0b2__clk -layer M9 -location {6298.080 13279.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tW0o2__clk -layer M9 -location {6299.040 14316.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tW0b3__clk -layer M9 -location {5589.600 13279.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tW0o3__clk -layer M9 -location {5590.560 14316.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tW0b4__clk -layer M9 -location {4881.120 13279.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tW0o4__clk -layer M9 -location {4882.080 14316.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tW0b5__clk -layer M9 -location {4172.640 13279.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tW0o5__clk -layer M9 -location {4173.600 14316.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tW0b6__clk -layer M9 -location {3464.160 13279.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tW0o6__clk -layer M9 -location {3465.120 14316.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tW0b7__clk -layer M9 -location {2755.680 13279.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tW0o7__clk -layer M9 -location {2756.640 14316.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tW0b8__clk -layer M9 -location {2047.200 13279.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tW0o8__clk -layer M9 -location {2048.160 14316.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tW0b9__clk -layer M9 -location {1338.720 13279.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tW0o9__clk -layer M9 -location {1339.680 14316.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tW0b10__clk -layer M9 -location {630.240 13279.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tW0o10__clk -layer M9 -location {631.200 14316.448} -pin_size {0.04 0.32}
place_pin -pin_name t_turnW0a__clk_t1 -layer M9 -location {212.192 14194.784} -pin_size {0.04 0.32}
place_pin -pin_name t_turnW0a__clk -layer M9 -location {258.720 14447.392} -pin_size {0.04 0.32}
place_pin -pin_name t_turnW0b__clk -layer M9 -location {189.600 13652.640} -pin_size {0.04 0.32}
place_pin -pin_name t_turnW0b__clk_t1 -layer M9 -location {189.600 13944.928} -pin_size {0.04 0.32}
place_pin -pin_name t_sp0__clk_t5 -layer M9 -location {8787.360 13313.056} -pin_size {0.04 0.32}
place_pin -pin_name t_sp0__clk_t22 -layer M9 -location {8787.360 14385.952} -pin_size {0.04 0.32}
place_pin -pin_name t_sp0__clk_t8 -layer M9 -location {8899.680 13475.744} -pin_size {0.04 0.32}
place_pin -pin_name t_sp0__clk_t1 -layer M9 -location {8881.440 12942.752} -pin_size {0.04 0.32}
place_pin -pin_name t_sp0__clk_t13 -layer M9 -location {8862.752 13749.280} -pin_size {0.04 0.32}
place_pin -pin_name t_sp0__clk -layer M9 -location {8855.520 14022.048} -pin_size {0.04 0.32}
place_pin -pin_name t_sp0__clk_t19 -layer M9 -location {8865.120 14294.816} -pin_size {0.04 0.32}
place_pin -pin_name t_sp0__clk_t26 -layer M9 -location {8855.520 14511.136} -pin_size {0.04 0.32}
place_pin -pin_name t_sp0__clk_t28 -layer M9 -location {8855.520 14555.744} -pin_size {0.04 0.32}
place_pin -pin_name t_sp0__clk_t29 -layer M9 -location {8855.520 14597.984} -pin_size {0.04 0.32}
place_pin -pin_name t_sp0__clk_t6 -layer M9 -location {9005.280 13372.064} -pin_size {0.04 0.32}
place_pin -pin_name t_sp0__clk_t3 -layer M9 -location {8946.208 13199.136} -pin_size {0.04 0.32}
place_pin -pin_name t_sp0__clk_t12 -layer M9 -location {9005.280 13738.784} -pin_size {0.04 0.32}
place_pin -pin_name t_sp0__clk_t14 -layer M9 -location {9005.280 13810.080} -pin_size {0.04 0.32}
place_pin -pin_name t_sp0__clk_t16 -layer M9 -location {9005.280 14018.336} -pin_size {0.04 0.32}
place_pin -pin_name t_sp0__clk_t17 -layer M9 -location {9005.280 14118.688} -pin_size {0.04 0.32}
place_pin -pin_name t_sp0__clk_t18 -layer M9 -location {9005.280 14286.624} -pin_size {0.04 0.32}
place_pin -pin_name t_sp0__clk_t24 -layer M9 -location {9005.280 14462.816} -pin_size {0.04 0.32}
place_pin -pin_name t_sp0__clk_t27 -layer M9 -location {9005.280 14549.920} -pin_size {0.04 0.32}
place_pin -pin_name t_sp0__clk_t9 -layer M9 -location {9009.120 13476.768} -pin_size {0.04 0.32}
place_pin -pin_name t_sp0__clk_t23 -layer M9 -location {9066.272 14437.856} -pin_size {0.04 0.32}
place_pin -pin_name t_sp0__clk_t2 -layer M9 -location {9090.272 12942.752} -pin_size {0.04 0.32}
place_pin -pin_name t_sp0__clk_t20 -layer M9 -location {9117.856 14307.872} -pin_size {0.04 0.32}
place_pin -pin_name t_sp0__clk_t30 -layer M9 -location {9103.712 14597.984} -pin_size {0.04 0.32}
place_pin -pin_name t_sp0__clk_t4 -layer M9 -location {9193.888 13271.072} -pin_size {0.04 0.32}
place_pin -pin_name t_sp0__clk_t11 -layer M9 -location {9193.888 13616.672} -pin_size {0.04 0.32}
place_pin -pin_name t_sp0__clk_t15 -layer M9 -location {9193.888 13962.272} -pin_size {0.04 0.32}
place_pin -pin_name t_sp0__clk_t31 -layer M9 -location {9218.400 14653.472} -pin_size {0.04 0.32}
place_pin -pin_name t_sp0__clk_t21 -layer M9 -location {9263.520 14307.872} -pin_size {0.04 0.32}
place_pin -pin_name t_sp0__clk_t7 -layer M9 -location {9340.320 13429.728} -pin_size {0.04 0.32}
place_pin -pin_name t_sp0_xe_o_shim__clk -layer M9 -location {9374.880 14466.528} -pin_size {0.04 0.32}
place_pin -pin_name t_sp0__clk_t25 -layer M9 -location {9340.320 14483.488} -pin_size {0.04 0.32}
place_pin -pin_name t_sp0_be_i_shim__clk -layer M9 -location {9434.400 13429.728} -pin_size {0.04 0.32}
place_pin -pin_name t_tE0b0__clk -layer M9 -location {9806.880 13279.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tE0o0__clk -layer M9 -location {9805.920 14316.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tE0b1__clk -layer M9 -location {10515.360 13279.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tE0o1__clk -layer M9 -location {10514.400 14316.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tE0b2__clk -layer M9 -location {11223.840 13279.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tE0o2__clk -layer M9 -location {11222.880 14316.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tE0b3__clk -layer M9 -location {11932.320 13279.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tE0o3__clk -layer M9 -location {11931.360 14316.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tE0b4__clk -layer M9 -location {12640.800 13279.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tE0o4__clk -layer M9 -location {12639.840 14316.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tE0b5__clk -layer M9 -location {13349.280 13279.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tE0o5__clk -layer M9 -location {13348.320 14316.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tE0b6__clk -layer M9 -location {14057.760 13279.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tE0o6__clk -layer M9 -location {14056.800 14316.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tE0b7__clk -layer M9 -location {14766.240 13279.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tE0o7__clk -layer M9 -location {14765.280 14316.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tE0b8__clk -layer M9 -location {15474.720 13279.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tE0o8__clk -layer M9 -location {15473.760 14316.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tE0b9__clk -layer M9 -location {16183.200 13279.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tE0o9__clk -layer M9 -location {16182.240 14316.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tE0b10__clk -layer M9 -location {16891.680 13279.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tE0o10__clk -layer M9 -location {16890.720 14316.448} -pin_size {0.04 0.32}
place_pin -pin_name t_turnE0a__clk_t1 -layer M9 -location {17309.728 14194.784} -pin_size {0.04 0.32}
place_pin -pin_name t_turnE0a__clk -layer M9 -location {17263.200 14447.392} -pin_size {0.04 0.32}
place_pin -pin_name t_turnE0b__clk -layer M9 -location {17332.320 13652.640} -pin_size {0.04 0.32}
place_pin -pin_name t_turnE0b__clk_t1 -layer M9 -location {17332.320 13944.928} -pin_size {0.04 0.32}
place_pin -pin_name t_lep0N__clk -layer M9 -location {8043.360 15612.448} -pin_size {0.04 0.32}
place_pin -pin_name t_lk_WN0__clk -layer M9 -location {7318.560 16303.648} -pin_size {0.04 0.32}
place_pin -pin_name t_nst4__clk_t5 -layer M9 -location {7300.320 15443.616} -pin_size {0.04 0.32}
place_pin -pin_name t_nst4__clk_t11 -layer M9 -location {7300.320 15963.616} -pin_size {0.04 0.32}
place_pin -pin_name t_nst4__clk_t3 -layer M9 -location {6957.344 15228.000} -pin_size {0.04 0.32}
place_pin -pin_name t_nst4__clk_t7 -layer M9 -location {6957.344 15469.664} -pin_size {0.04 0.32}
place_pin -pin_name t_nst4__clk_t10 -layer M9 -location {6957.344 15880.672} -pin_size {0.04 0.32}
place_pin -pin_name t_nst4__clk_t4 -layer M9 -location {6597.152 15324.640} -pin_size {0.04 0.32}
place_pin -pin_name t_nst4__clk -layer M9 -location {6597.152 15844.640} -pin_size {0.04 0.32}
place_pin -pin_name t_nst4__clk_t2 -layer M9 -location {6235.936 15228.000} -pin_size {0.04 0.32}
place_pin -pin_name t_nst4__clk_t6 -layer M9 -location {6235.936 15469.664} -pin_size {0.04 0.32}
place_pin -pin_name t_nst4__clk_t9 -layer M9 -location {6235.936 15880.672} -pin_size {0.04 0.32}
place_pin -pin_name t_nst4__clk_t1 -layer M9 -location {5892.960 15222.048} -pin_size {0.04 0.32}
place_pin -pin_name t_nst3_transit__clk_t4 -layer M9 -location {5857.440 15443.616} -pin_size {0.04 0.32}
place_pin -pin_name t_nst4__clk_t8 -layer M9 -location {5892.960 15742.048} -pin_size {0.04 0.32}
place_pin -pin_name t_nst3_turn__clk_t9 -layer M9 -location {5857.440 15963.616} -pin_size {0.04 0.32}
place_pin -pin_name t_nst3_turn__clk_t3 -layer M9 -location {5597.920 15742.048} -pin_size {0.04 0.32}
place_pin -pin_name t_nst3_turn__clk_t7 -layer M9 -location {5543.776 15911.136} -pin_size {0.04 0.32}
place_pin -pin_name t_nst3_turn__clk_t12 -layer M9 -location {5595.232 16013.920} -pin_size {0.04 0.32}
place_pin -pin_name t_nst3_transit__clk_t3 -layer M9 -location {5514.464 15324.640} -pin_size {0.04 0.32}
place_pin -pin_name t_nst3_turn__clk_t4 -layer M9 -location {5353.568 15791.264} -pin_size {0.04 0.32}
place_pin -pin_name t_nst3_turn__clk_t10 -layer M9 -location {5303.776 16002.528} -pin_size {0.04 0.32}
place_pin -pin_name t_nst3_turn__clk -layer M9 -location {5284.896 15688.608} -pin_size {0.04 0.32}
place_pin -pin_name t_nst3_transit__clk -layer M9 -location {5154.272 15324.640} -pin_size {0.04 0.32}
place_pin -pin_name t_nst3_turn__clk_t6 -layer M9 -location {5176.288 15875.040} -pin_size {0.04 0.32}
place_pin -pin_name t_nst3_turn__clk_t2 -layer M9 -location {5018.976 15717.664} -pin_size {0.04 0.32}
place_pin -pin_name t_nst3_turn__clk_t11 -layer M9 -location {5024.672 16006.752} -pin_size {0.04 0.32}
place_pin -pin_name t_nst3_turn__clk_t5 -layer M9 -location {4862.368 15872.928} -pin_size {0.04 0.32}
place_pin -pin_name t_nst3_transit__clk_t2 -layer M9 -location {4793.056 15324.640} -pin_size {0.04 0.32}
place_pin -pin_name t_nst3_turn__clk_t1 -layer M9 -location {4717.920 15705.888} -pin_size {0.04 0.32}
place_pin -pin_name t_nst3_turn__clk_t8 -layer M9 -location {4695.328 15948.640} -pin_size {0.04 0.32}
place_pin -pin_name t_nst3_turn__clk_t13 -layer M9 -location {4695.328 16208.608} -pin_size {0.04 0.32}
place_pin -pin_name t_lk_WN1__clk -layer M9 -location {4432.800 16303.648} -pin_size {0.04 0.32}
place_pin -pin_name t_nst3_transit__clk_t1 -layer M9 -location {4450.080 15222.048} -pin_size {0.04 0.32}
place_pin -pin_name t_nst2__clk_t4 -layer M9 -location {4414.560 15443.616} -pin_size {0.04 0.32}
place_pin -pin_name t_nst2__clk_t3 -layer M9 -location {4071.584 15324.640} -pin_size {0.04 0.32}
place_pin -pin_name t_nst2__clk -layer M9 -location {3711.392 15324.640} -pin_size {0.04 0.32}
place_pin -pin_name t_nst2__clk_t2 -layer M9 -location {3350.176 15324.640} -pin_size {0.04 0.32}
place_pin -pin_name t_nst2__clk_t1 -layer M9 -location {3007.200 15222.048} -pin_size {0.04 0.32}
place_pin -pin_name t_nst1__clk_t8 -layer M9 -location {2971.680 15443.616} -pin_size {0.04 0.32}
place_pin -pin_name t_nst1__clk_t2 -layer M9 -location {2676.000 15216.672} -pin_size {0.04 0.32}
place_pin -pin_name t_nst1__clk_t7 -layer M9 -location {2701.088 15438.432} -pin_size {0.04 0.32}
place_pin -pin_name t_nst1__clk_t6 -layer M9 -location {2415.392 15435.680} -pin_size {0.04 0.32}
place_pin -pin_name t_nst1__clk_t1 -layer M9 -location {2354.912 15214.048} -pin_size {0.04 0.32}
place_pin -pin_name t_nst1__clk_t9 -layer M9 -location {2139.424 15460.896} -pin_size {0.04 0.32}
place_pin -pin_name t_nst1__clk -layer M9 -location {2083.872 15680.864} -pin_size {0.04 0.32}
place_pin -pin_name t_nst1__clk_t3 -layer M9 -location {2044.320 15239.328} -pin_size {0.04 0.32}
place_pin -pin_name t_nst1__clk_t14 -layer M9 -location {2025.568 15937.632} -pin_size {0.04 0.32}
place_pin -pin_name t_nst1__clk_t11 -layer M9 -location {1981.088 15612.384} -pin_size {0.04 0.32}
place_pin -pin_name t_nst1__clk_t5 -layer M9 -location {1859.232 15332.576} -pin_size {0.04 0.32}
place_pin -pin_name t_nst1__clk_t12 -layer M9 -location {1862.432 15632.416} -pin_size {0.04 0.32}
place_pin -pin_name t_nst1__clk_t13 -layer M9 -location {1803.936 15912.224} -pin_size {0.04 0.32}
place_pin -pin_name t_nst1__clk_t15 -layer M9 -location {1809.568 16208.608} -pin_size {0.04 0.32}
place_pin -pin_name t_nst1__clk_t4 -layer M9 -location {1756.448 15244.512} -pin_size {0.04 0.32}
place_pin -pin_name t_nst1__clk_t10 -layer M9 -location {1759.072 15573.152} -pin_size {0.04 0.32}
place_pin -pin_name t_lk_WN2__clk -layer M9 -location {1547.040 16303.648} -pin_size {0.04 0.32}
place_pin -pin_name t_ctl__clk_t3 -layer M9 -location {8778.720 15103.584} -pin_size {0.04 0.32}
place_pin -pin_name t_ctl__clk_t4 -layer M9 -location {8778.720 15339.616} -pin_size {0.04 0.32}
place_pin -pin_name t_ctl__clk_t6 -layer M9 -location {8778.720 15544.416} -pin_size {0.04 0.32}
place_pin -pin_name t_ctl__clk_t9 -layer M9 -location {8778.720 15815.712} -pin_size {0.04 0.32}
place_pin -pin_name t_ctl__clk_t12 -layer M9 -location {8778.720 16112.032} -pin_size {0.04 0.32}
place_pin -pin_name t_sp0__clk_t32 -layer M9 -location {8919.264 14981.792} -pin_size {0.04 0.32}
place_pin -pin_name t_ctl__clk_t1 -layer M9 -location {8943.712 15016.352} -pin_size {0.04 0.32}
place_pin -pin_name t_ctl__clk_t7 -layer M9 -location {9092.640 15644.256} -pin_size {0.04 0.32}
place_pin -pin_name t_sp0__clk_t33 -layer M9 -location {9204.832 14981.792} -pin_size {0.04 0.32}
place_pin -pin_name t_ctl__clk_t2 -layer M9 -location {9188.128 15016.352} -pin_size {0.04 0.32}
place_pin -pin_name t_ctl__clk -layer M9 -location {9424.352 15644.256} -pin_size {0.04 0.32}
place_pin -pin_name t_ctl__clk_t8 -layer M9 -location {9756.064 15644.256} -pin_size {0.04 0.32}
place_pin -pin_name t_ctl__clk_t11 -layer M9 -location {9719.264 15904.608} -pin_size {0.04 0.32}
place_pin -pin_name t_ctl__clk_t10 -layer M9 -location {9940.832 15885.088} -pin_size {0.04 0.32}
place_pin -pin_name t_ctl__clk_t13 -layer M9 -location {9940.832 16208.672} -pin_size {0.04 0.32}
place_pin -pin_name t_lk_WN3__clk -layer M9 -location {10203.360 16303.648} -pin_size {0.04 0.32}
place_pin -pin_name t_nst7__clk_t1 -layer M9 -location {10221.600 15392.032} -pin_size {0.04 0.32}
place_pin -pin_name t_ctl__clk_t5 -layer M9 -location {10186.080 15404.640} -pin_size {0.04 0.32}
place_pin -pin_name t_nst7__clk_t2 -layer M9 -location {10496.096 15404.640} -pin_size {0.04 0.32}
place_pin -pin_name t_nst7__clk_t5 -layer M9 -location {10788.192 15452.064} -pin_size {0.04 0.32}
place_pin -pin_name t_nst7__clk -layer M9 -location {10925.792 15404.640} -pin_size {0.04 0.32}
place_pin -pin_name t_nst7__clk_t3 -layer M9 -location {11285.984 15404.640} -pin_size {0.04 0.32}
place_pin -pin_name t_mesh7N__clk -layer M9 -location {11664.480 15404.640} -pin_size {0.04 0.32}
place_pin -pin_name t_nst7__clk_t4 -layer M9 -location {11628.960 15434.016} -pin_size {0.04 0.32}
place_pin -pin_name t_mesh7N__clk_t2 -layer M9 -location {12724.000 16208.672} -pin_size {0.04 0.32}
place_pin -pin_name t_lk_EN0__clk -layer M9 -location {13089.120 16303.648} -pin_size {0.04 0.32}
place_pin -pin_name t_mesh7N__clk_t1 -layer M9 -location {13071.840 15324.640} -pin_size {0.04 0.32}
place_pin -pin_name t_nst9__clk_t4 -layer M9 -location {13107.360 15443.616} -pin_size {0.04 0.32}
place_pin -pin_name t_nst9__clk_t3 -layer M9 -location {13450.336 15324.640} -pin_size {0.04 0.32}
place_pin -pin_name t_nst9__clk -layer M9 -location {13810.528 15324.640} -pin_size {0.04 0.32}
place_pin -pin_name t_nst9__clk_t2 -layer M9 -location {14171.744 15324.640} -pin_size {0.04 0.32}
place_pin -pin_name t_nst9__clk_t1 -layer M9 -location {14514.720 15222.048} -pin_size {0.04 0.32}
place_pin -pin_name t_nst10__clk_t8 -layer M9 -location {14550.240 15443.616} -pin_size {0.04 0.32}
place_pin -pin_name t_nst10__clk_t2 -layer M9 -location {14845.920 15216.672} -pin_size {0.04 0.32}
place_pin -pin_name t_nst10__clk_t7 -layer M9 -location {14820.832 15438.432} -pin_size {0.04 0.32}
place_pin -pin_name t_nst10__clk_t6 -layer M9 -location {15106.528 15435.680} -pin_size {0.04 0.32}
place_pin -pin_name t_nst10__clk_t1 -layer M9 -location {15167.008 15214.048} -pin_size {0.04 0.32}
place_pin -pin_name t_nst10__clk_t9 -layer M9 -location {15382.496 15460.896} -pin_size {0.04 0.32}
place_pin -pin_name t_nst10__clk -layer M9 -location {15438.048 15680.864} -pin_size {0.04 0.32}
place_pin -pin_name t_nst10__clk_t3 -layer M9 -location {15477.600 15239.328} -pin_size {0.04 0.32}
place_pin -pin_name t_nst10__clk_t14 -layer M9 -location {15496.352 15937.632} -pin_size {0.04 0.32}
place_pin -pin_name t_nst10__clk_t11 -layer M9 -location {15540.832 15612.384} -pin_size {0.04 0.32}
place_pin -pin_name t_nst10__clk_t5 -layer M9 -location {15662.688 15332.576} -pin_size {0.04 0.32}
place_pin -pin_name t_nst10__clk_t12 -layer M9 -location {15659.488 15632.416} -pin_size {0.04 0.32}
place_pin -pin_name t_nst10__clk_t13 -layer M9 -location {15717.984 15912.224} -pin_size {0.04 0.32}
place_pin -pin_name t_nst10__clk_t15 -layer M9 -location {15712.352 16208.608} -pin_size {0.04 0.32}
place_pin -pin_name t_nst10__clk_t4 -layer M9 -location {15765.472 15244.512} -pin_size {0.04 0.32}
place_pin -pin_name t_nst10__clk_t10 -layer M9 -location {15762.848 15573.152} -pin_size {0.04 0.32}
place_pin -pin_name t_lk_EN1__clk -layer M9 -location {15974.880 16303.648} -pin_size {0.04 0.32}
place_inst -name b0_r -location {8762.580 8779.240} -status PLACED
place_inst -name b0 -location {8760.960 8779.240} -status PLACED
place_inst -name r1_0 -location {8770.600 8592.167} -status PLACED
place_inst -name r1_1 -location {8760.960 8405.095} -status PLACED
place_inst -name r1_2 -location {8760.960 8218.022} -status PLACED
place_inst -name r1_3 -location {8760.960 8030.950} -status PLACED
place_inst -name r1_4 -location {8760.960 7843.877} -status PLACED
place_inst -name r1_5 -location {8770.600 7656.805} -status PLACED
place_inst -name r1_6 -location {8770.600 7469.733} -status PLACED
place_inst -name r1_7 -location {8760.960 7282.660} -status PLACED
place_inst -name r1_8 -location {8760.960 7095.587} -status PLACED
place_inst -name r1_9 -location {8760.960 6908.515} -status PLACED
place_inst -name r1_10 -location {8760.960 6721.443} -status PLACED
place_inst -name r1_11 -location {8770.600 6534.370} -status PLACED
place_inst -name r1_12 -location {8760.960 6347.297} -status PLACED
place_inst -name r1_13 -location {8760.960 6160.225} -status PLACED
place_inst -name r1_14 -location {8760.960 5973.153} -status PLACED
place_inst -name b1 -location {8760.960 5786.080} -status PLACED
place_inst -name r2_0 -location {8770.600 5613.280} -status PLACED
place_inst -name r2_1 -location {8770.600 5440.480} -status PLACED
place_inst -name r2_2 -location {8760.960 5267.680} -status PLACED
place_inst -name r2_3 -location {8760.960 5094.880} -status PLACED
place_inst -name r2_4 -location {8760.960 4922.080} -status PLACED
place_inst -name r2_5 -location {8760.960 4749.280} -status PLACED
place_inst -name r2_6 -location {8770.600 4576.480} -status PLACED
place_inst -name r2_7 -location {8770.600 4403.680} -status PLACED
place_inst -name r2_8 -location {8760.960 4230.880} -status PLACED
place_inst -name r2_9 -location {8760.960 4058.080} -status PLACED
place_inst -name r2_10 -location {8760.960 3885.280} -status PLACED
place_inst -name b2 -location {8760.960 3712.480} -status PLACED
place_inst -name r3_0 -location {8770.600 3539.680} -status PLACED
place_inst -name r3_1 -location {8770.600 3366.880} -status PLACED
place_inst -name r3_2 -location {8760.960 3194.080} -status PLACED
place_inst -name r3_3 -location {8760.960 3021.280} -status PLACED
place_inst -name r3_4 -location {8760.960 2848.480} -status PLACED
place_inst -name b3 -location {8760.960 2675.680} -status PLACED
place_inst -name r4_0 -location {8760.960 2617.070} -status PLACED
place_inst -name b4 -location {8760.960 2558.460} -status PLACED
place_inst -name r5_0 -location {8760.960 2853.536} -status PLACED
place_inst -name r5_1 -location {8760.960 3031.392} -status PLACED
place_inst -name r5_2 -location {8760.960 3209.248} -status PLACED
place_inst -name r5_3 -location {8770.600 3387.104} -status PLACED
place_inst -name r5_4 -location {8770.600 3564.960} -status PLACED
place_inst -name r5_5 -location {8760.960 3742.816} -status PLACED
place_inst -name r5_6 -location {8760.960 3920.672} -status PLACED
place_inst -name b5 -location {8760.960 4098.528} -status PLACED
place_inst -name r6_0 -location {8760.960 3872.522} -status PLACED
place_inst -name r6_1 -location {8760.960 4032.564} -status PLACED
place_inst -name r6_2 -location {8760.960 4192.607} -status PLACED
place_inst -name r6_3 -location {8770.600 4352.649} -status PLACED
place_inst -name r6_4 -location {8770.600 4512.691} -status PLACED
place_inst -name r6_5 -location {8760.960 4672.733} -status PLACED
place_inst -name r6_6 -location {8760.960 4832.775} -status PLACED
place_inst -name r6_7 -location {8760.960 4992.818} -status PLACED
place_inst -name r6_8 -location {8760.960 5152.860} -status PLACED
place_inst -name b6 -location {8760.960 5312.902} -status PLACED
place_inst -name r7_0 -location {8760.960 5224.115} -status PLACED
place_inst -name b7 -location {8760.960 5135.328} -status PLACED
place_inst -name r8_0 -location {8770.600 5456.106} -status PLACED
place_inst -name r8_1 -location {8770.600 5599.311} -status PLACED
place_inst -name r8_2 -location {8760.960 5742.515} -status PLACED
place_inst -name r8_3 -location {8760.960 5885.719} -status PLACED
place_inst -name r8_4 -location {8760.960 6028.924} -status PLACED
place_inst -name b8 -location {8760.960 6172.128} -status PLACED
place_inst -name r9_0 -location {8760.960 5974.455} -status PLACED
place_inst -name r9_1 -location {8760.960 6162.830} -status PLACED
place_inst -name r9_2 -location {8760.960 6349.400} -status PLACED
place_inst -name r9_3 -location {8770.600 6539.581} -status PLACED
place_inst -name r9_4 -location {8760.960 6727.956} -status PLACED
place_inst -name r9_5 -location {8760.960 6916.331} -status PLACED
place_inst -name r9_6 -location {8760.960 7104.706} -status PLACED
place_inst -name r9_7 -location {8760.960 7293.081} -status PLACED
place_inst -name r9_8 -location {8770.600 7481.456} -status PLACED
place_inst -name r9_9 -location {8770.600 7669.831} -status PLACED
place_inst -name r9_10 -location {8760.960 7858.207} -status PLACED
place_inst -name r9_11 -location {8760.960 8046.582} -status PLACED
place_inst -name r9_12 -location {8760.960 8234.957} -status PLACED
place_inst -name b9 -location {8760.960 8423.332} -status PLACED
place_inst -name r10_0 -location {8760.960 8253.111} -status PLACED
place_inst -name r10_1 -location {8760.960 8082.890} -status PLACED
place_inst -name r10_2 -location {8760.960 7912.669} -status PLACED
place_inst -name b10 -location {8760.960 7742.448} -status PLACED
place_inst -name r11_0 -location {8770.600 7609.068} -status PLACED
place_inst -name r11_1 -location {8770.600 7475.688} -status PLACED
place_inst -name r11_2 -location {8760.960 7342.308} -status PLACED
place_inst -name b11 -location {8760.960 7208.928} -status PLACED
place_inst -name r12_0 -location {8760.960 7868.268} -status PLACED
place_inst -name r12_1 -location {8760.960 7994.088} -status PLACED
place_inst -name r12_2 -location {8760.960 8119.908} -status PLACED
place_inst -name b12 -location {8760.960 8245.728} -status PLACED
place_inst -name r13_0 -location {8770.600 8596.112} -status PLACED
place_inst -name r13_1 -location {8760.960 8779.240} -status PLACED
place_inst -name r13_2 -location {8760.960 8941.671} -status PLACED
place_inst -name r13_3 -location {8760.960 9114.451} -status PLACED
place_inst -name r13_4 -location {8760.960 9287.230} -status PLACED
place_inst -name b13 -location {8760.960 9460.010} -status PLACED
place_inst -name r14_0 -location {8760.960 9371.269} -status PLACED
place_inst -name b14 -location {8760.960 9282.528} -status PLACED
place_inst -name r15_0 -location {8770.600 9603.230} -status PLACED
place_inst -name r15_1 -location {8770.600 9746.449} -status PLACED
place_inst -name r15_2 -location {8760.960 9889.669} -status PLACED
place_inst -name r15_3 -location {8760.960 10032.889} -status PLACED
place_inst -name r15_4 -location {8760.960 10176.108} -status PLACED
place_inst -name b15 -location {8760.960 10319.328} -status PLACED
place_inst -name r16_0 -location {8760.960 8964.938} -status PLACED
place_inst -name r16_1 -location {8760.960 9150.636} -status PLACED
place_inst -name r16_2 -location {8760.960 9336.334} -status PLACED
place_inst -name r16_3 -location {8770.600 9522.032} -status PLACED
place_inst -name r16_4 -location {8770.600 9707.730} -status PLACED
place_inst -name r16_5 -location {8760.960 9893.428} -status PLACED
place_inst -name r16_6 -location {8760.960 10079.126} -status PLACED
place_inst -name r16_7 -location {8760.960 10264.824} -status PLACED
place_inst -name r16_8 -location {8760.960 10450.522} -status PLACED
place_inst -name r16_9 -location {8770.600 10636.220} -status PLACED
place_inst -name r16_10 -location {8770.600 10821.918} -status PLACED
place_inst -name r16_11 -location {8760.960 11007.616} -status PLACED
place_inst -name r16_12 -location {8760.960 11193.314} -status PLACED
place_inst -name r16_13 -location {8760.960 11379.011} -status PLACED
place_inst -name r16_14 -location {8770.600 11564.709} -status PLACED
place_inst -name r16_15 -location {8770.600 11750.407} -status PLACED
place_inst -name r16_16 -location {8760.960 11936.105} -status PLACED
place_inst -name r16_17 -location {8760.960 12121.803} -status PLACED
place_inst -name r16_18 -location {8760.960 12307.501} -status PLACED
place_inst -name r16_19 -location {8760.960 12493.199} -status PLACED
place_inst -name r16_20 -location {8770.600 12678.897} -status PLACED
place_inst -name r16_21 -location {8770.600 12864.595} -status PLACED
place_inst -name r16_22 -location {8760.960 13050.293} -status PLACED
place_inst -name r16_23 -location {8760.960 13235.991} -status PLACED
place_inst -name r16_24 -location {8760.960 13421.689} -status PLACED
place_inst -name b16 -location {8760.960 13607.387} -status PLACED
place_inst -name r17_0 -location {8760.960 13435.613} -status PLACED
place_inst -name r17_1 -location {8760.960 13263.839} -status PLACED
place_inst -name r17_2 -location {8760.960 13092.065} -status PLACED
place_inst -name r17_3 -location {8760.960 12926.440} -status PLACED
place_inst -name r17_4 -location {8770.600 12748.517} -status PLACED
place_inst -name r17_5 -location {8760.960 12570.200} -status PLACED
place_inst -name r17_6 -location {8760.960 12404.970} -status PLACED
place_inst -name r17_7 -location {8760.960 12233.196} -status PLACED
place_inst -name r17_8 -location {8760.960 12061.422} -status PLACED
place_inst -name b17 -location {8760.960 11889.648} -status PLACED
place_inst -name r18_0 -location {8770.600 11756.268} -status PLACED
place_inst -name r18_1 -location {8770.600 11622.888} -status PLACED
place_inst -name r18_2 -location {8760.960 11489.508} -status PLACED
place_inst -name b18 -location {8760.960 11356.128} -status PLACED
place_inst -name r19_0 -location {8760.960 12015.468} -status PLACED
place_inst -name r19_1 -location {8760.960 12141.288} -status PLACED
place_inst -name r19_2 -location {8760.960 12267.108} -status PLACED
place_inst -name b19 -location {8760.960 12392.928} -status PLACED
place_inst -name r20_0 -location {8770.600 13780.171} -status PLACED
place_inst -name r20_1 -location {8760.960 13963.240} -status PLACED
place_inst -name r20_2 -location {8760.960 14125.739} -status PLACED
place_inst -name r20_3 -location {8760.960 14298.524} -status PLACED
place_inst -name r20_4 -location {8760.960 14471.308} -status PLACED
place_inst -name b20 -location {8760.960 14644.092} -status PLACED
place_inst -name r21_0 -location {8760.960 14492.297} -status PLACED
place_inst -name r21_1 -location {8760.960 14340.501} -status PLACED
place_inst -name r21_2 -location {8760.960 14188.706} -status PLACED
place_inst -name r21_3 -location {8760.960 14036.910} -status PLACED
place_inst -name r21_4 -location {8770.600 13885.114} -status PLACED
place_inst -name r21_5 -location {8770.600 13733.319} -status PLACED
place_inst -name r21_6 -location {8760.960 13581.523} -status PLACED
place_inst -name b21 -location {8760.960 13429.728} -status PLACED
place_inst -name r22_0 -location {8770.600 14810.048} -status PLACED
place_inst -name r22_1 -location {8759.960 15000.040} -status PLACED
place_inst -name r22_2 -location {8759.960 15141.959} -status PLACED
place_inst -name r22_3 -location {8759.960 15307.914} -status PLACED
place_inst -name r22_4 -location {8760.460 15473.870} -status PLACED
place_inst -name r22_5 -location {8760.360 15639.826} -status PLACED
place_inst -name r22_6 -location {8760.260 15805.781} -status PLACED
place_inst -name r22_7 -location {8760.160 15971.737} -status PLACED
place_inst -name r22_8 -location {8760.060 16137.692} -status PLACED
place_inst -name b22 -location {8759.960 16303.648} -status PLACED
place_inst -name r23_0 -location {8761.960 2362.620} -status PLACED
place_inst -name r23_1 -location {8759.960 2166.780} -status PLACED
place_inst -name r23_2 -location {8759.960 1970.940} -status PLACED
place_inst -name b23 -location {8760.405 1775.100} -status PLACED
place_inst -name r24_0 -location {8761.960 2361.430} -status PLACED
place_inst -name b24 -location {8760.405 2164.400} -status PLACED
place_inst -name r25_0 -location {8761.960 2427.897} -status PLACED
place_inst -name r25_1 -location {8689.818 2202.200} -status PLACED
place_inst -name r25_2 -location {8654.246 2166.772} -status PLACED
place_inst -name r25_3 -location {8618.675 2036.209} -status PLACED
place_inst -name r25_4 -location {8583.104 1905.646} -status PLACED
place_inst -name r25_5 -location {8547.533 1775.083} -status PLACED
place_inst -name r25_6 -location {8511.962 1644.520} -status PLACED
place_inst -name r25_7 -location {8476.390 1513.958} -status PLACED
place_inst -name r25_8 -location {8440.819 1383.395} -status PLACED
place_inst -name b25 -location {8405.248 1252.832} -status PLACED
place_inst -name r26_0 -location {8405.248 1353.674} -status PLACED
place_inst -name r26_1 -location {8405.248 1454.516} -status PLACED
place_inst -name r26_2 -location {8405.248 1555.358} -status PLACED
place_inst -name b26 -location {8405.248 1656.200} -status PLACED
place_inst -name r27_0 -location {8405.248 1399.877} -status PLACED
place_inst -name r27_1 -location {8405.248 1546.921} -status PLACED
place_inst -name r27_2 -location {8405.248 1693.966} -status PLACED
place_inst -name r27_3 -location {8405.248 1841.011} -status PLACED
place_inst -name r27_4 -location {8405.248 1988.055} -status PLACED
place_inst -name b27 -location {8405.248 2135.100} -status PLACED
place_inst -name r28_0 -location {8229.126 1252.832} -status PLACED
place_inst -name b28 -location {8053.003 1252.832} -status PLACED
place_inst -name r29_0 -location {8053.003 1403.216} -status PLACED
place_inst -name b29 -location {8053.003 1553.600} -status PLACED
place_inst -name r30_0 -location {8053.003 1383.399} -status PLACED
place_inst -name r30_1 -location {8053.003 1513.966} -status PLACED
place_inst -name r30_2 -location {8053.003 1644.533} -status PLACED
place_inst -name b30 -location {8053.003 1775.100} -status PLACED
place_inst -name r31_0 -location {8053.003 1397.777} -status PLACED
place_inst -name r31_1 -location {8053.003 1542.721} -status PLACED
place_inst -name r31_2 -location {8053.003 1687.666} -status PLACED
place_inst -name r31_3 -location {8053.003 1832.611} -status PLACED
place_inst -name r31_4 -location {8053.003 1977.555} -status PLACED
place_inst -name b31 -location {8053.003 2122.500} -status PLACED
place_inst -name r32_0 -location {7927.829 1252.832} -status PLACED
place_inst -name b32 -location {7802.656 1252.832} -status PLACED
place_inst -name r33_0 -location {7802.656 1359.949} -status PLACED
place_inst -name r33_1 -location {7802.656 1467.066} -status PLACED
place_inst -name r33_2 -location {7802.656 1574.183} -status PLACED
place_inst -name b33 -location {7802.656 1681.300} -status PLACED
place_inst -name r34_0 -location {7755.744 1252.832} -status PLACED
place_inst -name b34 -location {7708.832 1252.832} -status PLACED
place_inst -name r35_0 -location {7708.832 1403.216} -status PLACED
place_inst -name b35 -location {7708.832 1553.600} -status PLACED
place_inst -name r36_0 -location {7652.272 1252.832} -status PLACED
place_inst -name b36 -location {7595.712 1252.832} -status PLACED
place_inst -name r37_0 -location {7595.712 1300.366} -status PLACED
place_inst -name b37 -location {7595.712 1347.900} -status PLACED
place_inst -name r38_0 -location {7595.712 1396.877} -status PLACED
place_inst -name r38_1 -location {7595.712 1540.921} -status PLACED
place_inst -name r38_2 -location {7595.712 1684.966} -status PLACED
place_inst -name r38_3 -location {7595.712 1829.011} -status PLACED
place_inst -name r38_4 -location {7595.712 1973.055} -status PLACED
place_inst -name b38 -location {7595.712 2117.100} -status PLACED
place_inst -name r39_0 -location {7542.672 1252.832} -status PLACED
place_inst -name b39 -location {7318.240 1252.832} -status PLACED
place_inst -name r40_0 -location {7319.080 1394.760} -status PLACED
place_inst -name r40_1 -location {7319.080 1536.688} -status PLACED
place_inst -name r40_2 -location {7319.080 1678.616} -status PLACED
place_inst -name r40_3 -location {7318.607 1820.544} -status PLACED
place_inst -name r40_4 -location {7318.698 1962.472} -status PLACED
place_inst -name b40 -location {7318.790 2104.400} -status PLACED
place_inst -name r41_0 -location {7319.080 1404.760} -status PLACED
place_inst -name r41_1 -location {7319.080 1556.688} -status PLACED
place_inst -name r41_2 -location {7319.080 1708.616} -status PLACED
place_inst -name r41_3 -location {7319.080 1860.544} -status PLACED
place_inst -name r41_4 -location {7319.080 2012.472} -status PLACED
place_inst -name b41 -location {7317.154 2164.400} -status PLACED
place_inst -name r42_0 -location {7125.240 1252.832} -status PLACED
place_inst -name b42 -location {7025.824 1252.832} -status PLACED
place_inst -name r43_0 -location {7025.824 1329.560} -status PLACED
place_inst -name r43_1 -location {7025.824 1329.560} -status PLACED
place_inst -name r43_2 -location {7025.824 2074.600} -status PLACED
place_inst -name r43_3 -location {7025.824 2074.600} -status PLACED
place_inst -name r43_4 -location {7025.824 2074.600} -status PLACED
place_inst -name b43 -location {7025.824 2151.800} -status PLACED
place_inst -name r44_0 -location {6879.776 1252.832} -status PLACED
place_inst -name b44 -location {6733.728 1252.832} -status PLACED
place_inst -name r45_0 -location {6733.728 1329.560} -status PLACED
place_inst -name r45_1 -location {6733.728 1329.560} -status PLACED
place_inst -name r45_2 -location {6733.728 1329.560} -status PLACED
place_inst -name r45_3 -location {6733.728 2074.600} -status PLACED
place_inst -name r45_4 -location {6733.728 2074.600} -status PLACED
place_inst -name b45 -location {6733.728 2104.400} -status PLACED
place_inst -name r46_0 -location {6664.928 1252.832} -status PLACED
place_inst -name b46 -location {6596.128 1252.832} -status PLACED
place_inst -name r47_0 -location {6596.128 1329.560} -status PLACED
place_inst -name r47_1 -location {6596.128 1329.560} -status PLACED
place_inst -name r47_2 -location {6596.128 2074.600} -status PLACED
place_inst -name r47_3 -location {6596.128 2074.600} -status PLACED
place_inst -name r47_4 -location {6596.128 2074.600} -status PLACED
place_inst -name b47 -location {6596.128 2151.800} -status PLACED
place_inst -name r48_0 -location {6416.032 1252.832} -status PLACED
place_inst -name b48 -location {6235.936 1252.832} -status PLACED
place_inst -name r49_0 -location {6235.936 1329.560} -status PLACED
place_inst -name r49_1 -location {6235.936 1329.560} -status PLACED
place_inst -name r49_2 -location {6235.936 2074.600} -status PLACED
place_inst -name r49_3 -location {6235.936 2074.600} -status PLACED
place_inst -name r49_4 -location {6235.936 2074.600} -status PLACED
place_inst -name b49 -location {6235.936 2151.800} -status PLACED
place_inst -name r50_0 -location {6055.838 1252.832} -status PLACED
place_inst -name b50 -location {5875.740 1252.832} -status PLACED
place_inst -name r51_0 -location {5874.200 1397.777} -status PLACED
place_inst -name r51_1 -location {5874.200 1542.721} -status PLACED
place_inst -name r51_2 -location {5874.200 1687.666} -status PLACED
place_inst -name r51_3 -location {5874.200 1832.611} -status PLACED
place_inst -name r51_4 -location {5874.200 1977.555} -status PLACED
place_inst -name b51 -location {5875.755 2122.500} -status PLACED
place_inst -name r52_0 -location {5874.200 1402.660} -status PLACED
place_inst -name r52_1 -location {5874.200 1552.488} -status PLACED
place_inst -name r52_2 -location {5874.200 1702.316} -status PLACED
place_inst -name r52_3 -location {5874.200 1852.144} -status PLACED
place_inst -name r52_4 -location {5874.200 2001.972} -status PLACED
place_inst -name b52 -location {5874.645 2151.800} -status PLACED
place_inst -name r53_0 -location {5696.103 1252.832} -status PLACED
place_inst -name r53_1 -location {5516.467 1252.832} -status PLACED
place_inst -name r53_2 -location {5336.830 1252.832} -status PLACED
place_inst -name r53_3 -location {5157.193 1252.832} -status PLACED
place_inst -name r53_4 -location {4977.557 1252.832} -status PLACED
place_inst -name b53 -location {4797.920 1252.832} -status PLACED
place_inst -name r54_0 -location {4797.920 1300.316} -status PLACED
place_inst -name b54 -location {4797.920 1347.800} -status PLACED
place_inst -name r55_0 -location {4656.912 1252.832} -status PLACED
place_inst -name b55 -location {4432.480 1252.832} -status PLACED
place_inst -name r56_0 -location {4433.320 1396.177} -status PLACED
place_inst -name r56_1 -location {4433.320 1539.521} -status PLACED
place_inst -name r56_2 -location {4433.320 1682.866} -status PLACED
place_inst -name r56_3 -location {4433.320 1826.211} -status PLACED
place_inst -name r56_4 -location {4433.320 1969.555} -status PLACED
place_inst -name b56 -location {4431.394 2112.900} -status PLACED
place_inst -name r57_0 -location {4433.320 1415.993} -status PLACED
place_inst -name r57_1 -location {4433.320 1579.155} -status PLACED
place_inst -name r57_2 -location {4433.320 1742.316} -status PLACED
place_inst -name r57_3 -location {4432.847 1905.477} -status PLACED
place_inst -name r57_4 -location {4432.938 2068.639} -status PLACED
place_inst -name b57 -location {4433.030 2231.800} -status PLACED
place_inst -name r58_0 -location {4239.480 1252.832} -status PLACED
place_inst -name b58 -location {4071.584 1252.832} -status PLACED
place_inst -name r59_0 -location {4071.584 1329.560} -status PLACED
place_inst -name r59_1 -location {4071.584 1329.560} -status PLACED
place_inst -name r59_2 -location {4071.584 1988.200} -status PLACED
place_inst -name r59_3 -location {4071.584 1988.200} -status PLACED
place_inst -name r59_4 -location {4071.584 2068.639} -status PLACED
place_inst -name b59 -location {4071.584 2231.800} -status PLACED
place_inst -name r60_0 -location {3891.488 1252.832} -status PLACED
place_inst -name b60 -location {3711.392 1252.832} -status PLACED
place_inst -name r61_0 -location {3711.392 1329.560} -status PLACED
place_inst -name r61_1 -location {3711.392 1329.560} -status PLACED
place_inst -name r61_2 -location {3711.392 1988.200} -status PLACED
place_inst -name r61_3 -location {3711.392 1988.200} -status PLACED
place_inst -name r61_4 -location {3711.392 2068.639} -status PLACED
place_inst -name b61 -location {3711.392 2231.800} -status PLACED
place_inst -name r62_0 -location {3530.784 1252.832} -status PLACED
place_inst -name b62 -location {3350.176 1252.832} -status PLACED
place_inst -name r63_0 -location {3350.176 1329.560} -status PLACED
place_inst -name r63_1 -location {3350.176 1329.560} -status PLACED
place_inst -name r63_2 -location {3350.176 1988.200} -status PLACED
place_inst -name r63_3 -location {3350.176 1988.200} -status PLACED
place_inst -name r63_4 -location {3350.176 2068.639} -status PLACED
place_inst -name b63 -location {3350.176 2231.800} -status PLACED
place_inst -name r64_0 -location {3170.078 1252.832} -status PLACED
place_inst -name b64 -location {2989.980 1252.832} -status PLACED
place_inst -name r65_0 -location {2988.440 1396.177} -status PLACED
place_inst -name r65_1 -location {2988.440 1539.521} -status PLACED
place_inst -name r65_2 -location {2988.440 1682.866} -status PLACED
place_inst -name r65_3 -location {2988.440 1826.211} -status PLACED
place_inst -name r65_4 -location {2988.440 1969.555} -status PLACED
place_inst -name b65 -location {2988.885 2112.900} -status PLACED
place_inst -name r66_0 -location {2988.440 1433.093} -status PLACED
place_inst -name r66_1 -location {2988.440 1613.355} -status PLACED
place_inst -name r66_2 -location {2988.440 1793.616} -status PLACED
place_inst -name r66_3 -location {2988.440 1973.877} -status PLACED
place_inst -name r66_4 -location {2989.992 2154.139} -status PLACED
place_inst -name b66 -location {2989.995 2334.400} -status PLACED
place_inst -name r67_0 -location {2839.262 1252.832} -status PLACED
place_inst -name b67 -location {2688.544 1252.832} -status PLACED
place_inst -name r68_0 -location {2688.544 1397.027} -status PLACED
place_inst -name r68_1 -location {2688.544 1541.221} -status PLACED
place_inst -name r68_2 -location {2688.544 1685.416} -status PLACED
place_inst -name r68_3 -location {2688.544 1829.611} -status PLACED
place_inst -name r68_4 -location {2688.544 1973.805} -status PLACED
place_inst -name b68 -location {2688.544 2118.000} -status PLACED
place_inst -name r69_0 -location {2688.544 1433.993} -status PLACED
place_inst -name r69_1 -location {2688.544 1615.155} -status PLACED
place_inst -name r69_2 -location {2688.544 1796.316} -status PLACED
place_inst -name r69_3 -location {2688.544 1977.477} -status PLACED
place_inst -name r69_4 -location {2688.544 2158.639} -status PLACED
place_inst -name b69 -location {2688.544 2339.800} -status PLACED
place_inst -name r70_0 -location {2551.968 1252.832} -status PLACED
place_inst -name b70 -location {2415.392 1252.832} -status PLACED
place_inst -name r71_0 -location {2415.392 1397.493} -status PLACED
place_inst -name r71_1 -location {2415.392 1542.155} -status PLACED
place_inst -name r71_2 -location {2415.392 1686.816} -status PLACED
place_inst -name r71_3 -location {2415.392 1831.477} -status PLACED
place_inst -name r71_4 -location {2415.392 1976.139} -status PLACED
place_inst -name b71 -location {2415.392 2120.800} -status PLACED
place_inst -name r72_0 -location {2385.152 1252.832} -status PLACED
place_inst -name b72 -location {2354.912 1252.832} -status PLACED
place_inst -name r73_0 -location {2354.912 1434.427} -status PLACED
place_inst -name r73_1 -location {2354.912 1616.021} -status PLACED
place_inst -name r73_2 -location {2354.912 1797.616} -status PLACED
place_inst -name r73_3 -location {2354.912 1979.211} -status PLACED
place_inst -name r73_4 -location {2354.912 2160.805} -status PLACED
place_inst -name b73 -location {2354.912 2342.400} -status PLACED
place_inst -name r74_0 -location {2233.280 1252.832} -status PLACED
place_inst -name b74 -location {2111.648 1252.832} -status PLACED
place_inst -name r75_0 -location {2111.648 1408.524} -status PLACED
place_inst -name r75_1 -location {2111.648 1564.216} -status PLACED
place_inst -name r75_2 -location {2111.648 1719.908} -status PLACED
place_inst -name b75 -location {2111.648 1875.600} -status PLACED
place_inst -name r76_0 -location {2111.648 1393.293} -status PLACED
place_inst -name r76_1 -location {2111.648 1533.755} -status PLACED
place_inst -name r76_2 -location {2111.648 1674.216} -status PLACED
place_inst -name r76_3 -location {2111.648 1814.677} -status PLACED
place_inst -name r76_4 -location {2111.648 1955.139} -status PLACED
place_inst -name b76 -location {2111.648 2095.600} -status PLACED
place_inst -name r77_0 -location {2073.296 1252.832} -status PLACED
place_inst -name b77 -location {2034.944 1252.832} -status PLACED
place_inst -name r78_0 -location {2034.944 1435.816} -status PLACED
place_inst -name b78 -location {2034.944 1618.800} -status PLACED
place_inst -name r79_0 -location {2034.944 1430.227} -status PLACED
place_inst -name r79_1 -location {2034.944 1607.621} -status PLACED
place_inst -name r79_2 -location {2034.944 1785.016} -status PLACED
place_inst -name r79_3 -location {2034.944 1962.411} -status PLACED
place_inst -name r79_4 -location {2034.944 2139.805} -status PLACED
place_inst -name b79 -location {2034.944 2317.200} -status PLACED
place_inst -name r80_0 -location {2008.016 1252.832} -status PLACED
place_inst -name b80 -location {1981.088 1252.832} -status PLACED
place_inst -name r81_0 -location {1981.088 1425.649} -status PLACED
place_inst -name r81_1 -location {1981.088 1598.466} -status PLACED
place_inst -name r81_2 -location {1981.088 1771.283} -status PLACED
place_inst -name b81 -location {1981.088 1944.100} -status PLACED
place_inst -name r82_0 -location {1907.440 1252.832} -status PLACED
place_inst -name b82 -location {1833.792 1252.832} -status PLACED
place_inst -name r83_0 -location {1833.792 1300.366} -status PLACED
place_inst -name b83 -location {1833.792 1347.900} -status PLACED
place_inst -name r84_0 -location {1833.792 1448.566} -status PLACED
place_inst -name b84 -location {1833.792 1644.300} -status PLACED
place_inst -name r85_0 -location {1833.792 1420.649} -status PLACED
place_inst -name r85_1 -location {1833.792 1588.466} -status PLACED
place_inst -name r85_2 -location {1833.792 1756.283} -status PLACED
place_inst -name b85 -location {1833.792 1924.100} -status PLACED
place_inst -name r86_0 -location {1833.792 1414.677} -status PLACED
place_inst -name r86_1 -location {1833.792 1576.521} -status PLACED
place_inst -name r86_2 -location {1833.792 1738.366} -status PLACED
place_inst -name r86_3 -location {1833.792 1900.211} -status PLACED
place_inst -name r86_4 -location {1833.792 2062.055} -status PLACED
place_inst -name b86 -location {1833.792 2223.900} -status PLACED
place_inst -name r87_0 -location {1802.293 1252.832} -status PLACED
place_inst -name b87 -location {1770.794 1252.832} -status PLACED
place_inst -name r88_0 -location {1767.535 1435.449} -status PLACED
place_inst -name r88_1 -location {1764.277 1618.066} -status PLACED
place_inst -name r88_2 -location {1761.019 1800.683} -status PLACED
place_inst -name b88 -location {1757.760 1983.300} -status PLACED
place_inst -name r89_0 -location {1768.622 1429.360} -status PLACED
place_inst -name r89_1 -location {1766.449 1605.888} -status PLACED
place_inst -name r89_2 -location {1764.277 1782.416} -status PLACED
place_inst -name r89_3 -location {1762.105 1958.944} -status PLACED
place_inst -name r89_4 -location {1759.932 2135.472} -status PLACED
place_inst -name b89 -location {1757.760 2312.000} -status PLACED
place_inst -name r90_0 -location {1587.000 1252.832} -status PLACED
place_inst -name b90 -location {1547.040 1252.832} -status PLACED
place_inst -name r91_0 -location {8761.960 2390.983} -status PLACED
place_inst -name r91_1 -location {8761.960 2223.507} -status PLACED
place_inst -name r91_2 -location {8761.960 2056.030} -status PLACED
place_inst -name r91_3 -location {8761.960 1888.553} -status PLACED
place_inst -name r91_4 -location {8761.960 1721.077} -status PLACED
place_inst -name b91 -location {8761.515 1553.600} -status PLACED
place_inst -name r92_0 -location {8761.960 2362.620} -status PLACED
place_inst -name r92_1 -location {8761.960 2166.780} -status PLACED
place_inst -name r92_2 -location {8761.960 1970.940} -status PLACED
place_inst -name b92 -location {8761.515 1775.100} -status PLACED
place_inst -name r93_0 -location {8761.960 2449.470} -status PLACED
place_inst -name r93_1 -location {8761.960 2340.480} -status PLACED
place_inst -name r93_2 -location {8761.960 2231.490} -status PLACED
place_inst -name b93 -location {8761.515 2122.500} -status PLACED
place_inst -name r94_0 -location {8791.350 2427.897} -status PLACED
place_inst -name r94_1 -location {8821.741 2297.334} -status PLACED
place_inst -name r94_2 -location {8852.131 2166.772} -status PLACED
place_inst -name r94_3 -location {8882.522 2036.209} -status PLACED
place_inst -name r94_4 -location {8912.912 1905.646} -status PLACED
place_inst -name r94_5 -location {8939.640 1775.083} -status PLACED
place_inst -name r94_6 -location {8973.693 1651.152} -status PLACED
place_inst -name r94_7 -location {9004.083 1500.600} -status PLACED
place_inst -name r94_8 -location {9034.474 1383.395} -status PLACED
place_inst -name b94 -location {9064.864 1252.832} -status PLACED
place_inst -name r95_0 -location {9064.864 1399.877} -status PLACED
place_inst -name r95_1 -location {9064.864 1546.921} -status PLACED
place_inst -name r95_2 -location {9064.864 1704.864} -status PLACED
place_inst -name r95_3 -location {9064.864 1837.560} -status PLACED
place_inst -name r95_4 -location {9064.864 1988.055} -status PLACED
place_inst -name b95 -location {9064.864 2135.100} -status PLACED
place_inst -name r96_0 -location {9110.528 1252.832} -status PLACED
place_inst -name b96 -location {9156.192 1252.832} -status PLACED
place_inst -name r97_0 -location {9156.192 1413.753} -status PLACED
place_inst -name r97_1 -location {9156.192 1574.674} -status PLACED
place_inst -name r97_2 -location {9156.192 1735.595} -status PLACED
place_inst -name r97_3 -location {9156.192 1896.516} -status PLACED
place_inst -name r97_4 -location {9156.192 2057.437} -status PLACED
place_inst -name r97_5 -location {9156.192 2218.358} -status PLACED
place_inst -name r97_6 -location {9156.192 2379.279} -status PLACED
place_inst -name b97 -location {9156.192 2540.200} -status PLACED
place_inst -name r98_0 -location {9156.192 1418.078} -status PLACED
place_inst -name r98_1 -location {9156.192 1583.324} -status PLACED
place_inst -name r98_2 -location {9156.192 1748.570} -status PLACED
place_inst -name r98_3 -location {9156.192 1913.816} -status PLACED
place_inst -name r98_4 -location {9156.192 2079.062} -status PLACED
place_inst -name r98_5 -location {9156.192 2244.308} -status PLACED
place_inst -name r98_6 -location {9156.192 2409.554} -status PLACED
place_inst -name b98 -location {9156.192 2574.800} -status PLACED
place_inst -name r99_0 -location {9217.504 1252.832} -status PLACED
place_inst -name b99 -location {9278.816 1252.832} -status PLACED
place_inst -name r100_0 -location {9278.816 1417.243} -status PLACED
place_inst -name r100_1 -location {9278.816 1581.655} -status PLACED
place_inst -name r100_2 -location {9278.816 1746.066} -status PLACED
place_inst -name r100_3 -location {9278.816 1910.477} -status PLACED
place_inst -name r100_4 -location {9278.816 2074.889} -status PLACED
place_inst -name b100 -location {9278.816 2239.300} -status PLACED
place_inst -name r101_0 -location {9401.952 1252.832} -status PLACED
place_inst -name b101 -location {9525.088 1252.832} -status PLACED
place_inst -name r102_0 -location {9525.088 1396.877} -status PLACED
place_inst -name r102_1 -location {9525.088 1540.921} -status PLACED
place_inst -name r102_2 -location {9525.088 1684.966} -status PLACED
place_inst -name r102_3 -location {9525.088 1829.011} -status PLACED
place_inst -name r102_4 -location {9525.088 1973.055} -status PLACED
place_inst -name b102 -location {9525.088 2117.100} -status PLACED
place_inst -name r103_0 -location {9688.256 1252.832} -status PLACED
place_inst -name b103 -location {9851.424 1252.832} -status PLACED
place_inst -name r104_0 -location {9851.424 1300.366} -status PLACED
place_inst -name b104 -location {9851.424 1347.900} -status PLACED
place_inst -name r105_0 -location {9851.424 1396.877} -status PLACED
place_inst -name r105_1 -location {9851.424 1556.112} -status PLACED
place_inst -name r105_2 -location {9851.424 1664.760} -status PLACED
place_inst -name r105_3 -location {9851.424 1829.011} -status PLACED
place_inst -name r105_4 -location {9851.424 1973.055} -status PLACED
place_inst -name b105 -location {9851.424 2117.100} -status PLACED
place_inst -name r106_0 -location {9979.248 1252.832} -status PLACED
place_inst -name b106 -location {10203.680 1252.832} -status PLACED
place_inst -name r107_0 -location {10202.840 1394.760} -status PLACED
place_inst -name r107_1 -location {10202.840 1536.688} -status PLACED
place_inst -name r107_2 -location {10202.840 1678.616} -status PLACED
place_inst -name r107_3 -location {10203.313 1820.544} -status PLACED
place_inst -name r107_4 -location {10203.222 1962.472} -status PLACED
place_inst -name b107 -location {10203.130 2104.400} -status PLACED
place_inst -name r108_0 -location {10202.840 1404.760} -status PLACED
place_inst -name r108_1 -location {10202.840 1556.688} -status PLACED
place_inst -name r108_2 -location {10202.840 1708.616} -status PLACED
place_inst -name r108_3 -location {10202.840 1860.544} -status PLACED
place_inst -name r108_4 -location {10202.840 2012.472} -status PLACED
place_inst -name b108 -location {10204.766 2164.400} -status PLACED
place_inst -name r109_0 -location {10396.680 1252.832} -status PLACED
place_inst -name b109 -location {10496.096 1252.832} -status PLACED
place_inst -name r110_0 -location {10496.096 1329.560} -status PLACED
place_inst -name r110_1 -location {10496.096 1329.560} -status PLACED
place_inst -name r110_2 -location {10496.096 2074.600} -status PLACED
place_inst -name r110_3 -location {10496.096 2074.600} -status PLACED
place_inst -name r110_4 -location {10496.096 2074.600} -status PLACED
place_inst -name b110 -location {10496.096 2151.800} -status PLACED
place_inst -name r111_0 -location {10642.144 1252.832} -status PLACED
place_inst -name b111 -location {10788.192 1252.832} -status PLACED
place_inst -name r112_0 -location {10788.192 1329.560} -status PLACED
place_inst -name r112_1 -location {10788.192 1329.560} -status PLACED
place_inst -name r112_2 -location {10788.192 1329.560} -status PLACED
place_inst -name r112_3 -location {10788.192 2074.600} -status PLACED
place_inst -name r112_4 -location {10788.192 2074.600} -status PLACED
place_inst -name b112 -location {10788.192 2104.400} -status PLACED
place_inst -name r113_0 -location {10856.992 1252.832} -status PLACED
place_inst -name b113 -location {10925.792 1252.832} -status PLACED
place_inst -name r114_0 -location {10925.792 1329.560} -status PLACED
place_inst -name r114_1 -location {10925.792 1329.560} -status PLACED
place_inst -name r114_2 -location {10925.792 2074.600} -status PLACED
place_inst -name r114_3 -location {10925.792 2074.600} -status PLACED
place_inst -name r114_4 -location {10925.792 2074.600} -status PLACED
place_inst -name b114 -location {10925.792 2151.800} -status PLACED
place_inst -name r115_0 -location {11105.888 1252.832} -status PLACED
place_inst -name b115 -location {11285.984 1252.832} -status PLACED
place_inst -name r116_0 -location {11285.984 1329.560} -status PLACED
place_inst -name r116_1 -location {11285.984 1329.560} -status PLACED
place_inst -name r116_2 -location {11285.984 2074.600} -status PLACED
place_inst -name r116_3 -location {11285.984 2074.600} -status PLACED
place_inst -name r116_4 -location {11285.984 2074.600} -status PLACED
place_inst -name b116 -location {11285.984 2151.800} -status PLACED
place_inst -name r117_0 -location {11466.082 1252.832} -status PLACED
place_inst -name b117 -location {11646.180 1252.832} -status PLACED
place_inst -name r118_0 -location {11647.720 1397.777} -status PLACED
place_inst -name r118_1 -location {11647.720 1542.721} -status PLACED
place_inst -name r118_2 -location {11647.720 1687.666} -status PLACED
place_inst -name r118_3 -location {11647.720 1832.611} -status PLACED
place_inst -name r118_4 -location {11647.720 1977.555} -status PLACED
place_inst -name b118 -location {11646.165 2122.500} -status PLACED
place_inst -name r119_0 -location {11647.720 1402.660} -status PLACED
place_inst -name r119_1 -location {11647.720 1552.488} -status PLACED
place_inst -name r119_2 -location {11647.720 1702.316} -status PLACED
place_inst -name r119_3 -location {11647.720 1852.144} -status PLACED
place_inst -name r119_4 -location {11647.720 2001.972} -status PLACED
place_inst -name b119 -location {11647.275 2151.800} -status PLACED
place_inst -name r120_0 -location {11825.817 1252.832} -status PLACED
place_inst -name r120_1 -location {12005.453 1252.832} -status PLACED
place_inst -name r120_2 -location {12185.090 1252.832} -status PLACED
place_inst -name r120_3 -location {12364.727 1252.832} -status PLACED
place_inst -name r120_4 -location {12544.363 1252.832} -status PLACED
place_inst -name b120 -location {12724.000 1252.832} -status PLACED
place_inst -name r121_0 -location {12724.000 1300.316} -status PLACED
place_inst -name b121 -location {12724.000 1347.800} -status PLACED
place_inst -name r122_0 -location {12865.008 1252.832} -status PLACED
place_inst -name b122 -location {13089.440 1252.832} -status PLACED
place_inst -name r123_0 -location {13088.600 1396.177} -status PLACED
place_inst -name r123_1 -location {13088.600 1539.521} -status PLACED
place_inst -name r123_2 -location {13088.600 1682.866} -status PLACED
place_inst -name r123_3 -location {13088.600 1826.211} -status PLACED
place_inst -name r123_4 -location {13088.600 1969.555} -status PLACED
place_inst -name b123 -location {13090.526 2112.900} -status PLACED
place_inst -name r124_0 -location {13088.600 1415.993} -status PLACED
place_inst -name r124_1 -location {13088.600 1579.155} -status PLACED
place_inst -name r124_2 -location {13088.600 1742.316} -status PLACED
place_inst -name r124_3 -location {13089.073 1905.477} -status PLACED
place_inst -name r124_4 -location {13088.982 2068.639} -status PLACED
place_inst -name b124 -location {13088.890 2231.800} -status PLACED
place_inst -name r125_0 -location {13282.440 1252.832} -status PLACED
place_inst -name b125 -location {13450.336 1252.832} -status PLACED
place_inst -name r126_0 -location {13450.336 1329.560} -status PLACED
place_inst -name r126_1 -location {13450.336 1329.560} -status PLACED
place_inst -name r126_2 -location {13450.336 1988.200} -status PLACED
place_inst -name r126_3 -location {13450.336 1988.200} -status PLACED
place_inst -name r126_4 -location {13450.336 2068.639} -status PLACED
place_inst -name b126 -location {13450.336 2231.800} -status PLACED
place_inst -name r127_0 -location {13630.432 1252.832} -status PLACED
place_inst -name b127 -location {13810.528 1252.832} -status PLACED
place_inst -name r128_0 -location {13810.528 1329.560} -status PLACED
place_inst -name r128_1 -location {13810.528 1329.560} -status PLACED
place_inst -name r128_2 -location {13810.528 1988.200} -status PLACED
place_inst -name r128_3 -location {13810.528 1988.200} -status PLACED
place_inst -name r128_4 -location {13810.528 2068.639} -status PLACED
place_inst -name b128 -location {13810.528 2231.800} -status PLACED
place_inst -name r129_0 -location {13991.136 1252.832} -status PLACED
place_inst -name b129 -location {14171.744 1252.832} -status PLACED
place_inst -name r130_0 -location {14171.744 1329.560} -status PLACED
place_inst -name r130_1 -location {14171.744 1329.560} -status PLACED
place_inst -name r130_2 -location {14171.744 1988.200} -status PLACED
place_inst -name r130_3 -location {14171.744 1988.200} -status PLACED
place_inst -name r130_4 -location {14171.744 2068.639} -status PLACED
place_inst -name b130 -location {14171.744 2231.800} -status PLACED
place_inst -name r131_0 -location {14351.842 1252.832} -status PLACED
place_inst -name b131 -location {14531.940 1252.832} -status PLACED
place_inst -name r132_0 -location {14533.480 1396.177} -status PLACED
place_inst -name r132_1 -location {14533.480 1539.521} -status PLACED
place_inst -name r132_2 -location {14533.480 1682.866} -status PLACED
place_inst -name r132_3 -location {14533.480 1826.211} -status PLACED
place_inst -name r132_4 -location {14533.480 1969.555} -status PLACED
place_inst -name b132 -location {14533.035 2112.900} -status PLACED
place_inst -name r133_0 -location {14533.480 1433.093} -status PLACED
place_inst -name r133_1 -location {14533.480 1613.355} -status PLACED
place_inst -name r133_2 -location {14533.480 1793.616} -status PLACED
place_inst -name r133_3 -location {14533.480 1973.877} -status PLACED
place_inst -name r133_4 -location {14531.927 2154.139} -status PLACED
place_inst -name b133 -location {14531.925 2334.400} -status PLACED
place_inst -name r134_0 -location {14682.658 1252.832} -status PLACED
place_inst -name b134 -location {14833.376 1252.832} -status PLACED
place_inst -name r135_0 -location {14833.376 1397.027} -status PLACED
place_inst -name r135_1 -location {14833.376 1541.221} -status PLACED
place_inst -name r135_2 -location {14833.376 1685.416} -status PLACED
place_inst -name r135_3 -location {14833.376 1829.611} -status PLACED
place_inst -name r135_4 -location {14833.376 1973.805} -status PLACED
place_inst -name b135 -location {14833.376 2118.000} -status PLACED
place_inst -name r136_0 -location {14833.376 1433.993} -status PLACED
place_inst -name r136_1 -location {14833.376 1615.155} -status PLACED
place_inst -name r136_2 -location {14833.376 1796.316} -status PLACED
place_inst -name r136_3 -location {14833.376 1977.477} -status PLACED
place_inst -name r136_4 -location {14833.376 2158.639} -status PLACED
place_inst -name b136 -location {14833.376 2339.800} -status PLACED
place_inst -name r137_0 -location {14969.952 1252.832} -status PLACED
place_inst -name b137 -location {15106.528 1252.832} -status PLACED
place_inst -name r138_0 -location {15106.528 1397.493} -status PLACED
place_inst -name r138_1 -location {15106.528 1542.155} -status PLACED
place_inst -name r138_2 -location {15106.528 1686.816} -status PLACED
place_inst -name r138_3 -location {15106.528 1831.477} -status PLACED
place_inst -name r138_4 -location {15106.528 1976.139} -status PLACED
place_inst -name b138 -location {15106.528 2120.800} -status PLACED
place_inst -name r139_0 -location {15136.768 1252.832} -status PLACED
place_inst -name b139 -location {15167.008 1252.832} -status PLACED
place_inst -name r140_0 -location {15167.008 1434.427} -status PLACED
place_inst -name r140_1 -location {15167.008 1616.021} -status PLACED
place_inst -name r140_2 -location {15167.008 1797.616} -status PLACED
place_inst -name r140_3 -location {15167.008 1979.211} -status PLACED
place_inst -name r140_4 -location {15167.008 2160.805} -status PLACED
place_inst -name b140 -location {15167.008 2342.400} -status PLACED
place_inst -name r141_0 -location {15288.640 1252.832} -status PLACED
place_inst -name b141 -location {15410.272 1252.832} -status PLACED
place_inst -name r142_0 -location {15410.272 1408.524} -status PLACED
place_inst -name r142_1 -location {15410.272 1564.216} -status PLACED
place_inst -name r142_2 -location {15410.272 1719.908} -status PLACED
place_inst -name b142 -location {15410.272 1875.600} -status PLACED
place_inst -name r143_0 -location {15410.272 1393.293} -status PLACED
place_inst -name r143_1 -location {15410.272 1533.755} -status PLACED
place_inst -name r143_2 -location {15410.272 1674.216} -status PLACED
place_inst -name r143_3 -location {15410.272 1814.677} -status PLACED
place_inst -name r143_4 -location {15410.272 1955.139} -status PLACED
place_inst -name b143 -location {15410.272 2095.600} -status PLACED
place_inst -name r144_0 -location {15448.624 1252.832} -status PLACED
place_inst -name b144 -location {15486.976 1252.832} -status PLACED
place_inst -name r145_0 -location {15486.976 1435.816} -status PLACED
place_inst -name b145 -location {15486.976 1618.800} -status PLACED
place_inst -name r146_0 -location {15486.976 1430.227} -status PLACED
place_inst -name r146_1 -location {15486.976 1607.621} -status PLACED
place_inst -name r146_2 -location {15486.976 1785.016} -status PLACED
place_inst -name r146_3 -location {15486.976 1962.411} -status PLACED
place_inst -name r146_4 -location {15486.976 2139.805} -status PLACED
place_inst -name b146 -location {15486.976 2317.200} -status PLACED
place_inst -name r147_0 -location {15513.904 1252.832} -status PLACED
place_inst -name b147 -location {15540.832 1252.832} -status PLACED
place_inst -name r148_0 -location {15540.832 1425.649} -status PLACED
place_inst -name r148_1 -location {15540.832 1598.466} -status PLACED
place_inst -name r148_2 -location {15540.832 1771.283} -status PLACED
place_inst -name b148 -location {15540.832 1944.100} -status PLACED
place_inst -name r149_0 -location {15614.480 1252.832} -status PLACED
place_inst -name b149 -location {15688.128 1252.832} -status PLACED
place_inst -name r150_0 -location {15688.128 1300.366} -status PLACED
place_inst -name b150 -location {15688.128 1347.900} -status PLACED
place_inst -name r151_0 -location {15688.128 1448.566} -status PLACED
place_inst -name b151 -location {15688.128 1644.300} -status PLACED
place_inst -name r152_0 -location {15688.128 1420.649} -status PLACED
place_inst -name r152_1 -location {15688.128 1588.466} -status PLACED
place_inst -name r152_2 -location {15688.128 1756.283} -status PLACED
place_inst -name b152 -location {15688.128 1924.100} -status PLACED
place_inst -name r153_0 -location {15688.128 1414.677} -status PLACED
place_inst -name r153_1 -location {15688.128 1576.521} -status PLACED
place_inst -name r153_2 -location {15688.128 1738.366} -status PLACED
place_inst -name r153_3 -location {15688.128 1900.211} -status PLACED
place_inst -name r153_4 -location {15688.128 2062.055} -status PLACED
place_inst -name b153 -location {15688.128 2223.900} -status PLACED
place_inst -name r154_0 -location {15719.627 1252.832} -status PLACED
place_inst -name b154 -location {15751.126 1252.832} -status PLACED
place_inst -name r155_0 -location {15754.385 1435.449} -status PLACED
place_inst -name r155_1 -location {15757.643 1618.066} -status PLACED
place_inst -name r155_2 -location {15760.901 1800.683} -status PLACED
place_inst -name b155 -location {15764.160 1983.300} -status PLACED
place_inst -name r156_0 -location {15753.298 1429.360} -status PLACED
place_inst -name r156_1 -location {15755.471 1605.888} -status PLACED
place_inst -name r156_2 -location {15757.643 1782.416} -status PLACED
place_inst -name r156_3 -location {15759.815 1958.944} -status PLACED
place_inst -name r156_4 -location {15761.988 2135.472} -status PLACED
place_inst -name b156 -location {15764.160 2312.000} -status PLACED
place_inst -name r157_0 -location {15934.920 1252.832} -status PLACED
place_inst -name b157 -location {15974.880 1252.832} -status PLACED
place_inst -name r158_0 -location {8590.320 4098.528} -status PLACED
place_inst -name b158 -location {8419.680 4098.528} -status PLACED
place_inst -name r159_0 -location {8419.680 3925.723} -status PLACED
place_inst -name r159_1 -location {8419.680 3752.919} -status PLACED
place_inst -name r159_2 -location {8419.680 3595.240} -status PLACED
place_inst -name r159_3 -location {8419.680 3239.000} -status PLACED
place_inst -name r159_4 -location {8419.680 3234.505} -status PLACED
place_inst -name b159 -location {8419.680 3061.700} -status PLACED
place_inst -name r160_0 -location {8253.600 4098.528} -status PLACED
place_inst -name b160 -location {8087.520 4098.528} -status PLACED
place_inst -name r161_0 -location {8087.520 3925.723} -status PLACED
place_inst -name r161_1 -location {8087.520 3752.919} -status PLACED
place_inst -name r161_2 -location {8087.520 3595.240} -status PLACED
place_inst -name r161_3 -location {8068.760 3407.309} -status PLACED
place_inst -name r161_4 -location {8087.520 3234.505} -status PLACED
place_inst -name b161 -location {8087.520 3061.700} -status PLACED
place_inst -name r162_0 -location {8055.240 4098.528} -status PLACED
place_inst -name b162 -location {7715.520 4098.528} -status PLACED
place_inst -name r163_0 -location {7715.520 3900.707} -status PLACED
place_inst -name r163_1 -location {7715.520 3702.885} -status PLACED
place_inst -name r163_2 -location {7715.520 3579.720} -status PLACED
place_inst -name r163_3 -location {7715.520 3289.080} -status PLACED
place_inst -name r163_4 -location {7715.520 3109.421} -status PLACED
place_inst -name b163 -location {7715.520 2911.600} -status PLACED
place_inst -name r164_0 -location {7715.520 4023.464} -status PLACED
place_inst -name b164 -location {7715.520 3948.400} -status PLACED
place_inst -name r165_0 -location {7701.000 4098.528} -status PLACED
place_inst -name r165_1 -location {7362.280 4098.528} -status PLACED
place_inst -name r165_2 -location {7021.560 4098.528} -status PLACED
place_inst -name b165 -location {7007.040 4098.528} -status PLACED
place_inst -name r166_0 -location {7007.040 3900.707} -status PLACED
place_inst -name r166_1 -location {7007.040 3702.885} -status PLACED
place_inst -name r166_2 -location {7007.040 3579.720} -status PLACED
place_inst -name r166_3 -location {7007.040 3289.080} -status PLACED
place_inst -name r166_4 -location {7007.040 3109.421} -status PLACED
place_inst -name b166 -location {7007.040 2911.600} -status PLACED
place_inst -name r167_0 -location {7007.040 4023.464} -status PLACED
place_inst -name b167 -location {7007.040 3948.400} -status PLACED
place_inst -name r168_0 -location {6667.320 4098.528} -status PLACED
place_inst -name r168_1 -location {6653.800 4098.528} -status PLACED
place_inst -name r168_2 -location {6638.280 4098.528} -status PLACED
place_inst -name b168 -location {6298.560 4098.528} -status PLACED
place_inst -name r169_0 -location {6298.560 3900.707} -status PLACED
place_inst -name r169_1 -location {6298.560 3702.885} -status PLACED
place_inst -name r169_2 -location {6298.560 3579.720} -status PLACED
place_inst -name r169_3 -location {6298.560 3289.080} -status PLACED
place_inst -name r169_4 -location {6298.560 3109.421} -status PLACED
place_inst -name b169 -location {6298.560 2911.600} -status PLACED
place_inst -name r170_0 -location {6298.560 4023.464} -status PLACED
place_inst -name b170 -location {6298.560 3948.400} -status PLACED
place_inst -name r171_0 -location {6284.040 4098.528} -status PLACED
place_inst -name r171_1 -location {5945.320 4098.528} -status PLACED
place_inst -name r171_2 -location {5604.600 4098.528} -status PLACED
place_inst -name b171 -location {5590.080 4098.528} -status PLACED
place_inst -name r172_0 -location {5590.080 3900.707} -status PLACED
place_inst -name r172_1 -location {5590.080 3702.885} -status PLACED
place_inst -name r172_2 -location {5590.080 3579.720} -status PLACED
place_inst -name r172_3 -location {5590.080 3289.080} -status PLACED
place_inst -name r172_4 -location {5590.080 3109.421} -status PLACED
place_inst -name b172 -location {5590.080 2911.600} -status PLACED
place_inst -name r173_0 -location {5590.080 4023.464} -status PLACED
place_inst -name b173 -location {5590.080 3948.400} -status PLACED
place_inst -name r174_0 -location {5250.360 4098.528} -status PLACED
place_inst -name r174_1 -location {5236.840 4098.528} -status PLACED
place_inst -name r174_2 -location {5221.320 4098.528} -status PLACED
place_inst -name b174 -location {4881.600 4098.528} -status PLACED
place_inst -name r175_0 -location {4881.600 3900.707} -status PLACED
place_inst -name r175_1 -location {4881.600 3702.885} -status PLACED
place_inst -name r175_2 -location {4881.600 3579.720} -status PLACED
place_inst -name r175_3 -location {4881.600 3289.080} -status PLACED
place_inst -name r175_4 -location {4881.600 3109.421} -status PLACED
place_inst -name b175 -location {4881.600 2911.600} -status PLACED
place_inst -name r176_0 -location {4881.600 4023.464} -status PLACED
place_inst -name b176 -location {4881.600 3948.400} -status PLACED
place_inst -name r177_0 -location {4867.080 4098.528} -status PLACED
place_inst -name r177_1 -location {4528.360 4098.528} -status PLACED
place_inst -name r177_2 -location {4187.640 4098.528} -status PLACED
place_inst -name b177 -location {4173.120 4098.528} -status PLACED
place_inst -name r178_0 -location {4173.120 3900.707} -status PLACED
place_inst -name r178_1 -location {4173.120 3702.885} -status PLACED
place_inst -name r178_2 -location {4173.120 3579.720} -status PLACED
place_inst -name r178_3 -location {4173.120 3289.080} -status PLACED
place_inst -name r178_4 -location {4173.120 3109.421} -status PLACED
place_inst -name b178 -location {4173.120 2911.600} -status PLACED
place_inst -name r179_0 -location {4173.120 4023.464} -status PLACED
place_inst -name b179 -location {4173.120 3948.400} -status PLACED
place_inst -name r180_0 -location {3833.400 4098.528} -status PLACED
place_inst -name r180_1 -location {3819.880 4098.528} -status PLACED
place_inst -name r180_2 -location {3479.160 4098.528} -status PLACED
place_inst -name b180 -location {3464.640 4098.528} -status PLACED
place_inst -name r181_0 -location {3464.640 3900.707} -status PLACED
place_inst -name r181_1 -location {3464.640 3702.885} -status PLACED
place_inst -name r181_2 -location {3464.640 3579.720} -status PLACED
place_inst -name r181_3 -location {3464.640 3289.080} -status PLACED
place_inst -name r181_4 -location {3464.640 3109.421} -status PLACED
place_inst -name b181 -location {3464.640 2911.600} -status PLACED
place_inst -name r182_0 -location {3464.640 4023.464} -status PLACED
place_inst -name b182 -location {3464.640 3948.400} -status PLACED
place_inst -name r183_0 -location {3124.920 4098.528} -status PLACED
place_inst -name r183_1 -location {3109.400 4098.528} -status PLACED
place_inst -name r183_2 -location {2770.680 4098.528} -status PLACED
place_inst -name b183 -location {2756.160 4098.528} -status PLACED
place_inst -name r184_0 -location {2756.160 3900.707} -status PLACED
place_inst -name r184_1 -location {2756.160 3702.885} -status PLACED
place_inst -name r184_2 -location {2756.160 3579.720} -status PLACED
place_inst -name r184_3 -location {2756.160 3289.080} -status PLACED
place_inst -name r184_4 -location {2756.160 3109.421} -status PLACED
place_inst -name b184 -location {2756.160 2911.600} -status PLACED
place_inst -name r185_0 -location {2756.160 4023.464} -status PLACED
place_inst -name b185 -location {2756.160 3948.400} -status PLACED
place_inst -name r186_0 -location {2416.440 4098.528} -status PLACED
place_inst -name r186_1 -location {2402.920 4098.528} -status PLACED
place_inst -name r186_2 -location {2387.400 4098.528} -status PLACED
place_inst -name b186 -location {2047.680 4098.528} -status PLACED
place_inst -name r187_0 -location {2047.680 3900.707} -status PLACED
place_inst -name r187_1 -location {2047.680 3702.885} -status PLACED
place_inst -name r187_2 -location {2047.680 3579.720} -status PLACED
place_inst -name r187_3 -location {2047.680 3289.080} -status PLACED
place_inst -name r187_4 -location {2047.680 3109.421} -status PLACED
place_inst -name b187 -location {2047.680 2911.600} -status PLACED
place_inst -name r188_0 -location {2047.680 4023.464} -status PLACED
place_inst -name b188 -location {2047.680 3948.400} -status PLACED
place_inst -name r189_0 -location {1707.960 4098.528} -status PLACED
place_inst -name r189_1 -location {1694.440 4098.528} -status PLACED
place_inst -name r189_2 -location {1678.920 4098.528} -status PLACED
place_inst -name b189 -location {1339.200 4098.528} -status PLACED
place_inst -name r190_0 -location {1339.200 3900.707} -status PLACED
place_inst -name r190_1 -location {1339.200 3702.885} -status PLACED
place_inst -name r190_2 -location {1339.200 3579.720} -status PLACED
place_inst -name r190_3 -location {1339.200 3289.080} -status PLACED
place_inst -name r190_4 -location {1339.200 3109.421} -status PLACED
place_inst -name b190 -location {1339.200 2911.600} -status PLACED
place_inst -name r191_0 -location {1339.200 4023.464} -status PLACED
place_inst -name b191 -location {1339.200 3948.400} -status PLACED
place_inst -name r192_0 -location {999.480 4098.528} -status PLACED
place_inst -name r192_1 -location {985.960 4098.528} -status PLACED
place_inst -name r192_2 -location {645.240 4098.528} -status PLACED
place_inst -name b192 -location {630.720 4098.528} -status PLACED
place_inst -name r193_0 -location {630.720 3900.707} -status PLACED
place_inst -name r193_1 -location {630.720 3702.885} -status PLACED
place_inst -name r193_2 -location {630.720 3579.720} -status PLACED
place_inst -name r193_3 -location {630.720 3289.080} -status PLACED
place_inst -name r193_4 -location {630.720 3109.421} -status PLACED
place_inst -name b193 -location {630.720 2911.600} -status PLACED
place_inst -name r194_0 -location {630.720 4023.464} -status PLACED
place_inst -name b194 -location {630.720 3948.400} -status PLACED
place_inst -name r195_0 -location {291.000 4098.528} -status PLACED
place_inst -name b195 -location {235.456 4098.528} -status PLACED
place_inst -name r196_0 -location {235.456 3962.664} -status PLACED
place_inst -name b196 -location {235.456 3826.800} -status PLACED
place_inst -name r197_0 -location {212.528 4098.528} -status PLACED
place_inst -name b197 -location {189.600 4098.528} -status PLACED
place_inst -name r198_0 -location {189.600 3962.873} -status PLACED
place_inst -name r198_1 -location {189.600 3827.219} -status PLACED
place_inst -name r198_2 -location {189.600 3691.564} -status PLACED
place_inst -name r198_3 -location {189.600 3555.909} -status PLACED
place_inst -name r198_4 -location {189.600 3420.255} -status PLACED
place_inst -name b198 -location {189.600 3284.600} -status PLACED
place_inst -name r199_0 -location {189.600 3968.121} -status PLACED
place_inst -name r199_1 -location {189.600 3837.714} -status PLACED
place_inst -name r199_2 -location {189.600 3707.307} -status PLACED
place_inst -name b199 -location {189.600 3576.900} -status PLACED
place_inst -name r200_0 -location {8760.960 3908.190} -status PLACED
place_inst -name r200_1 -location {8760.960 3717.852} -status PLACED
place_inst -name r200_2 -location {8770.600 3527.514} -status PLACED
place_inst -name r200_3 -location {8770.600 3337.176} -status PLACED
place_inst -name r200_4 -location {8760.960 3146.838} -status PLACED
place_inst -name b200 -location {8760.960 2956.500} -status PLACED
place_inst -name r201_0 -location {8760.960 3924.207} -status PLACED
place_inst -name r201_1 -location {8760.960 3749.885} -status PLACED
place_inst -name r201_2 -location {8760.960 3595.240} -status PLACED
place_inst -name r201_3 -location {8770.600 3401.243} -status PLACED
place_inst -name r201_4 -location {8760.960 3226.921} -status PLACED
place_inst -name b201 -location {8760.960 3052.600} -status PLACED
place_inst -name r202_0 -location {8760.960 3941.623} -status PLACED
place_inst -name r202_1 -location {8760.960 3784.719} -status PLACED
place_inst -name r202_2 -location {8760.960 3627.814} -status PLACED
place_inst -name r202_3 -location {8770.600 3470.909} -status PLACED
place_inst -name r202_4 -location {8770.600 3314.005} -status PLACED
place_inst -name b202 -location {8760.960 3157.100} -status PLACED
place_inst -name r203_0 -location {8760.960 4047.614} -status PLACED
place_inst -name b203 -location {8760.960 3996.700} -status PLACED
place_inst -name r204_0 -location {8808.240 4098.528} -status PLACED
place_inst -name b204 -location {8855.520 4098.528} -status PLACED
place_inst -name r205_0 -location {8855.520 4129.764} -status PLACED
place_inst -name b205 -location {8855.520 4161.000} -status PLACED
place_inst -name r206_0 -location {8855.520 4167.914} -status PLACED
place_inst -name b206 -location {8855.520 4237.300} -status PLACED
place_inst -name r207_0 -location {8887.392 4098.528} -status PLACED
place_inst -name b207 -location {8919.264 4098.528} -status PLACED
place_inst -name r208_0 -location {8919.264 4227.346} -status PLACED
place_inst -name r208_1 -location {8919.264 4356.164} -status PLACED
place_inst -name r208_2 -location {8919.264 4484.982} -status PLACED
place_inst -name b208 -location {8919.264 4613.800} -status PLACED
place_inst -name r209_0 -location {8962.272 4098.528} -status PLACED
place_inst -name b209 -location {9005.280 4098.528} -status PLACED
place_inst -name r210_0 -location {9005.280 3918.140} -status PLACED
place_inst -name r210_1 -location {9005.280 3737.752} -status PLACED
place_inst -name r210_2 -location {9005.280 3557.364} -status PLACED
place_inst -name r210_3 -location {9005.280 3376.976} -status PLACED
place_inst -name r210_4 -location {9005.280 3196.588} -status PLACED
place_inst -name b210 -location {9005.280 3016.200} -status PLACED
place_inst -name r211_0 -location {9005.280 3940.573} -status PLACED
place_inst -name r211_1 -location {9005.280 3782.619} -status PLACED
place_inst -name r211_2 -location {9005.280 3624.664} -status PLACED
place_inst -name r211_3 -location {9005.280 3466.709} -status PLACED
place_inst -name r211_4 -location {9005.280 3308.755} -status PLACED
place_inst -name b211 -location {9005.280 3150.800} -status PLACED
place_inst -name r212_0 -location {9005.280 3908.071} -status PLACED
place_inst -name r212_1 -location {9005.280 3717.614} -status PLACED
place_inst -name r212_2 -location {9005.280 3527.157} -status PLACED
place_inst -name b212 -location {9005.280 3336.700} -status PLACED
place_inst -name r213_0 -location {9005.280 3931.796} -status PLACED
place_inst -name r213_1 -location {9005.280 3765.064} -status PLACED
place_inst -name r213_2 -location {9005.280 3598.332} -status PLACED
place_inst -name b213 -location {9005.280 3431.600} -status PLACED
place_inst -name r214_0 -location {9005.280 3975.396} -status PLACED
place_inst -name r214_1 -location {9005.280 3852.264} -status PLACED
place_inst -name r214_2 -location {9005.280 3729.132} -status PLACED
place_inst -name b214 -location {9005.280 3606.000} -status PLACED
place_inst -name r215_0 -location {9005.280 3915.464} -status PLACED
place_inst -name b215 -location {9005.280 3732.400} -status PLACED
place_inst -name r216_0 -location {9005.280 4018.364} -status PLACED
place_inst -name b216 -location {9005.280 3938.200} -status PLACED
place_inst -name r217_0 -location {9062.144 4098.528} -status PLACED
place_inst -name b217 -location {9119.008 4098.528} -status PLACED
place_inst -name r218_0 -location {9119.008 4192.014} -status PLACED
place_inst -name b218 -location {9119.008 4285.500} -status PLACED
place_inst -name r219_0 -location {9163.354 4098.528} -status PLACED
place_inst -name b219 -location {9207.701 4098.528} -status PLACED
place_inst -name r220_0 -location {9207.701 3899.290} -status PLACED
place_inst -name r220_1 -location {9207.701 3700.052} -status PLACED
place_inst -name r220_2 -location {9207.701 3500.814} -status PLACED
place_inst -name r220_3 -location {9207.701 3301.576} -status PLACED
place_inst -name r220_4 -location {9207.701 3102.338} -status PLACED
place_inst -name b220 -location {9207.701 2903.100} -status PLACED
place_inst -name r221_0 -location {9207.701 3956.890} -status PLACED
place_inst -name r221_1 -location {9207.701 3815.252} -status PLACED
place_inst -name r221_2 -location {9207.701 3673.614} -status PLACED
place_inst -name r221_3 -location {9207.701 3531.976} -status PLACED
place_inst -name r221_4 -location {9207.701 3390.338} -status PLACED
place_inst -name b221 -location {9207.701 3248.700} -status PLACED
place_inst -name r222_0 -location {9207.701 3972.471} -status PLACED
place_inst -name r222_1 -location {9207.701 3846.414} -status PLACED
place_inst -name r222_2 -location {9207.701 3720.357} -status PLACED
place_inst -name b222 -location {9207.701 3594.300} -status PLACED
place_inst -name r223_0 -location {9207.701 4019.214} -status PLACED
place_inst -name b223 -location {9207.701 3939.900} -status PLACED
place_inst -name r224_0 -location {9207.701 4192.014} -status PLACED
place_inst -name b224 -location {9207.701 4285.500} -status PLACED
place_inst -name r225_0 -location {9207.701 4227.346} -status PLACED
place_inst -name r225_1 -location {9207.701 4356.164} -status PLACED
place_inst -name r225_2 -location {9207.701 4484.982} -status PLACED
place_inst -name b225 -location {9207.701 4613.800} -status PLACED
place_inst -name r226_0 -location {9279.770 4098.528} -status PLACED
place_inst -name b226 -location {9351.840 4098.528} -status PLACED
place_inst -name r227_0 -location {9351.840 3925.723} -status PLACED
place_inst -name r227_1 -location {9351.840 3752.919} -status PLACED
place_inst -name r227_2 -location {9351.840 3580.114} -status PLACED
place_inst -name r227_3 -location {9351.840 3407.309} -status PLACED
place_inst -name r227_4 -location {9351.840 3234.505} -status PLACED
place_inst -name b227 -location {9351.840 3061.700} -status PLACED
place_inst -name r228_0 -location {9393.120 4098.528} -status PLACED
place_inst -name b228 -location {9434.400 4098.528} -status PLACED
place_inst -name r229_0 -location {9434.400 3925.723} -status PLACED
place_inst -name r229_1 -location {9434.400 3752.919} -status PLACED
place_inst -name r229_2 -location {9434.400 3595.240} -status PLACED
place_inst -name r229_3 -location {9453.160 3407.309} -status PLACED
place_inst -name r229_4 -location {9434.400 3234.505} -status PLACED
place_inst -name b229 -location {9434.400 3061.700} -status PLACED
place_inst -name r230_0 -location {9466.680 4098.528} -status PLACED
place_inst -name b230 -location {9806.400 4098.528} -status PLACED
place_inst -name r231_0 -location {9806.400 3900.707} -status PLACED
place_inst -name r231_1 -location {9806.400 3702.885} -status PLACED
place_inst -name r231_2 -location {9806.400 3579.720} -status PLACED
place_inst -name r231_3 -location {9806.400 3289.080} -status PLACED
place_inst -name r231_4 -location {9806.400 3109.421} -status PLACED
place_inst -name b231 -location {9806.400 2911.600} -status PLACED
place_inst -name r232_0 -location {9806.400 4023.464} -status PLACED
place_inst -name b232 -location {9806.400 3948.400} -status PLACED
place_inst -name r233_0 -location {9820.920 4098.528} -status PLACED
place_inst -name r233_1 -location {10159.640 4098.528} -status PLACED
place_inst -name r233_2 -location {10175.160 4098.528} -status PLACED
place_inst -name b233 -location {10514.880 4098.528} -status PLACED
place_inst -name r234_0 -location {10514.880 3900.707} -status PLACED
place_inst -name r234_1 -location {10514.880 3702.885} -status PLACED
place_inst -name r234_2 -location {10514.880 3579.720} -status PLACED
place_inst -name r234_3 -location {10514.880 3289.080} -status PLACED
place_inst -name r234_4 -location {10514.880 3109.421} -status PLACED
place_inst -name b234 -location {10514.880 2911.600} -status PLACED
place_inst -name r235_0 -location {10514.880 4023.464} -status PLACED
place_inst -name b235 -location {10514.880 3948.400} -status PLACED
place_inst -name r236_0 -location {10529.400 4098.528} -status PLACED
place_inst -name r236_1 -location {10868.120 4098.528} -status PLACED
place_inst -name r236_2 -location {10883.640 4098.528} -status PLACED
place_inst -name b236 -location {11223.360 4098.528} -status PLACED
place_inst -name r237_0 -location {11223.360 3900.707} -status PLACED
place_inst -name r237_1 -location {11223.360 3702.885} -status PLACED
place_inst -name r237_2 -location {11223.360 3579.720} -status PLACED
place_inst -name r237_3 -location {11223.360 3289.080} -status PLACED
place_inst -name r237_4 -location {11223.360 3109.421} -status PLACED
place_inst -name b237 -location {11223.360 2911.600} -status PLACED
place_inst -name r238_0 -location {11223.360 4023.464} -status PLACED
place_inst -name b238 -location {11223.360 3948.400} -status PLACED
place_inst -name r239_0 -location {11237.880 4098.528} -status PLACED
place_inst -name r239_1 -location {11576.600 4098.528} -status PLACED
place_inst -name r239_2 -location {11917.320 4098.528} -status PLACED
place_inst -name b239 -location {11931.840 4098.528} -status PLACED
place_inst -name r240_0 -location {11931.840 3900.707} -status PLACED
place_inst -name r240_1 -location {11931.840 3702.885} -status PLACED
place_inst -name r240_2 -location {11931.840 3579.720} -status PLACED
place_inst -name r240_3 -location {11931.840 3289.080} -status PLACED
place_inst -name r240_4 -location {11931.840 3109.421} -status PLACED
place_inst -name b240 -location {11931.840 2911.600} -status PLACED
place_inst -name r241_0 -location {11931.840 4023.464} -status PLACED
place_inst -name b241 -location {11931.840 3948.400} -status PLACED
place_inst -name r242_0 -location {11946.360 4098.528} -status PLACED
place_inst -name r242_1 -location {12285.080 4098.528} -status PLACED
place_inst -name r242_2 -location {12625.800 4098.528} -status PLACED
place_inst -name b242 -location {12640.320 4098.528} -status PLACED
place_inst -name r243_0 -location {12640.320 3900.707} -status PLACED
place_inst -name r243_1 -location {12640.320 3702.885} -status PLACED
place_inst -name r243_2 -location {12640.320 3579.720} -status PLACED
place_inst -name r243_3 -location {12640.320 3289.080} -status PLACED
place_inst -name r243_4 -location {12640.320 3109.421} -status PLACED
place_inst -name b243 -location {12640.320 2911.600} -status PLACED
place_inst -name r244_0 -location {12640.320 4023.464} -status PLACED
place_inst -name b244 -location {12640.320 3948.400} -status PLACED
place_inst -name r245_0 -location {12654.840 4098.528} -status PLACED
place_inst -name r245_1 -location {12993.560 4098.528} -status PLACED
place_inst -name r245_2 -location {13009.080 4098.528} -status PLACED
place_inst -name b245 -location {13348.800 4098.528} -status PLACED
place_inst -name r246_0 -location {13348.800 3900.707} -status PLACED
place_inst -name r246_1 -location {13348.800 3702.885} -status PLACED
place_inst -name r246_2 -location {13348.800 3579.720} -status PLACED
place_inst -name r246_3 -location {13348.800 3289.080} -status PLACED
place_inst -name r246_4 -location {13348.800 3109.421} -status PLACED
place_inst -name b246 -location {13348.800 2911.600} -status PLACED
place_inst -name r247_0 -location {13348.800 4023.464} -status PLACED
place_inst -name b247 -location {13348.800 3948.400} -status PLACED
place_inst -name r248_0 -location {13363.320 4098.528} -status PLACED
place_inst -name r248_1 -location {13704.040 4098.528} -status PLACED
place_inst -name r248_2 -location {13717.560 4098.528} -status PLACED
place_inst -name b248 -location {14057.280 4098.528} -status PLACED
place_inst -name r249_0 -location {14057.280 3900.707} -status PLACED
place_inst -name r249_1 -location {14057.280 3702.885} -status PLACED
place_inst -name r249_2 -location {14057.280 3579.720} -status PLACED
place_inst -name r249_3 -location {14057.280 3289.080} -status PLACED
place_inst -name r249_4 -location {14057.280 3109.421} -status PLACED
place_inst -name b249 -location {14057.280 2911.600} -status PLACED
place_inst -name r250_0 -location {14057.280 4023.464} -status PLACED
place_inst -name b250 -location {14057.280 3948.400} -status PLACED
place_inst -name r251_0 -location {14397.000 4098.528} -status PLACED
place_inst -name r251_1 -location {14410.520 4098.528} -status PLACED
place_inst -name r251_2 -location {14426.040 4098.528} -status PLACED
place_inst -name b251 -location {14765.760 4098.528} -status PLACED
place_inst -name r252_0 -location {14765.760 3900.707} -status PLACED
place_inst -name r252_1 -location {14765.760 3702.885} -status PLACED
place_inst -name r252_2 -location {14765.760 3579.720} -status PLACED
place_inst -name r252_3 -location {14765.760 3289.080} -status PLACED
place_inst -name r252_4 -location {14765.760 3109.421} -status PLACED
place_inst -name b252 -location {14765.760 2911.600} -status PLACED
place_inst -name r253_0 -location {14765.760 4023.464} -status PLACED
place_inst -name b253 -location {14765.760 3948.400} -status PLACED
place_inst -name r254_0 -location {15105.480 4098.528} -status PLACED
place_inst -name r254_1 -location {15119.000 4098.528} -status PLACED
place_inst -name r254_2 -location {15134.520 4098.528} -status PLACED
place_inst -name b254 -location {15474.240 4098.528} -status PLACED
place_inst -name r255_0 -location {15474.240 3900.707} -status PLACED
place_inst -name r255_1 -location {15474.240 3702.885} -status PLACED
place_inst -name r255_2 -location {15474.240 3579.720} -status PLACED
place_inst -name r255_3 -location {15474.240 3289.080} -status PLACED
place_inst -name r255_4 -location {15474.240 3109.421} -status PLACED
place_inst -name b255 -location {15474.240 2911.600} -status PLACED
place_inst -name r256_0 -location {15474.240 4023.464} -status PLACED
place_inst -name b256 -location {15474.240 3948.400} -status PLACED
place_inst -name r257_0 -location {15813.960 4098.528} -status PLACED
place_inst -name r257_1 -location {15827.480 4098.528} -status PLACED
place_inst -name r257_2 -location {15843.000 4098.528} -status PLACED
place_inst -name b257 -location {16182.720 4098.528} -status PLACED
place_inst -name r258_0 -location {16182.720 3900.707} -status PLACED
place_inst -name r258_1 -location {16182.720 3702.885} -status PLACED
place_inst -name r258_2 -location {16182.720 3579.720} -status PLACED
place_inst -name r258_3 -location {16182.720 3289.080} -status PLACED
place_inst -name r258_4 -location {16182.720 3109.421} -status PLACED
place_inst -name b258 -location {16182.720 2911.600} -status PLACED
place_inst -name r259_0 -location {16182.720 4023.464} -status PLACED
place_inst -name b259 -location {16182.720 3948.400} -status PLACED
place_inst -name r260_0 -location {16522.440 4098.528} -status PLACED
place_inst -name r260_1 -location {16535.960 4098.528} -status PLACED
place_inst -name r260_2 -location {16876.680 4098.528} -status PLACED
place_inst -name b260 -location {16891.200 4098.528} -status PLACED
place_inst -name r261_0 -location {16891.200 3900.707} -status PLACED
place_inst -name r261_1 -location {16891.200 3702.885} -status PLACED
place_inst -name r261_2 -location {16891.200 3579.720} -status PLACED
place_inst -name r261_3 -location {16891.200 3289.080} -status PLACED
place_inst -name r261_4 -location {16891.200 3109.421} -status PLACED
place_inst -name b261 -location {16891.200 2911.600} -status PLACED
place_inst -name r262_0 -location {16891.200 4023.464} -status PLACED
place_inst -name b262 -location {16891.200 3948.400} -status PLACED
place_inst -name r263_0 -location {17230.920 4098.528} -status PLACED
place_inst -name b263 -location {17286.464 4098.528} -status PLACED
place_inst -name r264_0 -location {17286.464 3962.664} -status PLACED
place_inst -name b264 -location {17286.464 3826.800} -status PLACED
place_inst -name r265_0 -location {17309.392 4098.528} -status PLACED
place_inst -name b265 -location {17332.320 4098.528} -status PLACED
place_inst -name r266_0 -location {17332.320 3962.873} -status PLACED
place_inst -name r266_1 -location {17332.320 3827.219} -status PLACED
place_inst -name r266_2 -location {17332.320 3691.564} -status PLACED
place_inst -name r266_3 -location {17332.320 3555.909} -status PLACED
place_inst -name r266_4 -location {17332.320 3420.255} -status PLACED
place_inst -name b266 -location {17332.320 3284.600} -status PLACED
place_inst -name r267_0 -location {17332.320 3968.121} -status PLACED
place_inst -name r267_1 -location {17332.320 3837.714} -status PLACED
place_inst -name r267_2 -location {17332.320 3707.307} -status PLACED
place_inst -name b267 -location {17332.320 3576.900} -status PLACED
place_inst -name r268_0 -location {8590.064 5135.328} -status PLACED
place_inst -name b268 -location {8419.168 5135.328} -status PLACED
place_inst -name r269_0 -location {8253.344 5135.328} -status PLACED
place_inst -name b269 -location {8087.520 5135.328} -status PLACED
place_inst -name r270_0 -location {8055.240 5135.328} -status PLACED
place_inst -name b270 -location {7715.040 5135.328} -status PLACED
place_inst -name r271_0 -location {7715.040 5060.264} -status PLACED
place_inst -name b271 -location {7715.040 4985.200} -status PLACED
place_inst -name r272_0 -location {7375.800 5135.328} -status PLACED
place_inst -name r272_1 -location {7360.280 5135.328} -status PLACED
place_inst -name r272_2 -location {7021.560 5135.328} -status PLACED
place_inst -name b272 -location {7006.560 5135.328} -status PLACED
place_inst -name r273_0 -location {7006.560 5060.264} -status PLACED
place_inst -name b273 -location {7006.560 4985.200} -status PLACED
place_inst -name r274_0 -location {6667.320 5135.328} -status PLACED
place_inst -name r274_1 -location {6651.800 5135.328} -status PLACED
place_inst -name r274_2 -location {6313.080 5135.328} -status PLACED
place_inst -name b274 -location {6298.080 5135.328} -status PLACED
place_inst -name r275_0 -location {6298.080 5060.264} -status PLACED
place_inst -name b275 -location {6298.080 4985.200} -status PLACED
place_inst -name r276_0 -location {5958.840 5135.328} -status PLACED
place_inst -name r276_1 -location {5943.320 5135.328} -status PLACED
place_inst -name r276_2 -location {5604.600 5135.328} -status PLACED
place_inst -name b276 -location {5589.600 5135.328} -status PLACED
place_inst -name r277_0 -location {5589.600 5060.264} -status PLACED
place_inst -name b277 -location {5589.600 4985.200} -status PLACED
place_inst -name r278_0 -location {5250.360 5135.328} -status PLACED
place_inst -name r278_1 -location {5234.840 5135.328} -status PLACED
place_inst -name r278_2 -location {4896.120 5135.328} -status PLACED
place_inst -name b278 -location {4881.120 5135.328} -status PLACED
place_inst -name r279_0 -location {4881.120 5060.264} -status PLACED
place_inst -name b279 -location {4881.120 4985.200} -status PLACED
place_inst -name r280_0 -location {4541.880 5135.328} -status PLACED
place_inst -name r280_1 -location {4526.360 5135.328} -status PLACED
place_inst -name r280_2 -location {4187.640 5135.328} -status PLACED
place_inst -name b280 -location {4172.640 5135.328} -status PLACED
place_inst -name r281_0 -location {4172.640 5060.264} -status PLACED
place_inst -name b281 -location {4172.640 4985.200} -status PLACED
place_inst -name r282_0 -location {3833.400 5135.328} -status PLACED
place_inst -name r282_1 -location {3817.880 5135.328} -status PLACED
place_inst -name r282_2 -location {3479.160 5135.328} -status PLACED
place_inst -name b282 -location {3464.160 5135.328} -status PLACED
place_inst -name r283_0 -location {3464.160 5060.264} -status PLACED
place_inst -name b283 -location {3464.160 4985.200} -status PLACED
place_inst -name r284_0 -location {3124.920 5135.328} -status PLACED
place_inst -name r284_1 -location {3109.400 5135.328} -status PLACED
place_inst -name r284_2 -location {2770.680 5135.328} -status PLACED
place_inst -name b284 -location {2755.680 5135.328} -status PLACED
place_inst -name r285_0 -location {2755.680 5060.264} -status PLACED
place_inst -name b285 -location {2755.680 4985.200} -status PLACED
place_inst -name r286_0 -location {2416.440 5135.328} -status PLACED
place_inst -name r286_1 -location {2400.920 5135.328} -status PLACED
place_inst -name r286_2 -location {2062.200 5135.328} -status PLACED
place_inst -name b286 -location {2047.200 5135.328} -status PLACED
place_inst -name r287_0 -location {2047.200 5060.264} -status PLACED
place_inst -name b287 -location {2047.200 4985.200} -status PLACED
place_inst -name r288_0 -location {1707.960 5135.328} -status PLACED
place_inst -name r288_1 -location {1692.440 5135.328} -status PLACED
place_inst -name r288_2 -location {1353.720 5135.328} -status PLACED
place_inst -name b288 -location {1338.720 5135.328} -status PLACED
place_inst -name r289_0 -location {1338.720 5060.264} -status PLACED
place_inst -name b289 -location {1338.720 4985.200} -status PLACED
place_inst -name r290_0 -location {999.480 5135.328} -status PLACED
place_inst -name r290_1 -location {983.960 5135.328} -status PLACED
place_inst -name r290_2 -location {645.240 5135.328} -status PLACED
place_inst -name b290 -location {630.240 5135.328} -status PLACED
place_inst -name r291_0 -location {630.240 5060.264} -status PLACED
place_inst -name b291 -location {630.240 4985.200} -status PLACED
place_inst -name r292_0 -location {616.200 5135.328} -status PLACED
place_inst -name r292_1 -location {291.000 5135.328} -status PLACED
place_inst -name r292_2 -location {291.000 5135.328} -status PLACED
place_inst -name b292 -location {189.600 5135.328} -status PLACED
place_inst -name r293_0 -location {189.600 5246.764} -status PLACED
place_inst -name b293 -location {189.600 5358.200} -status PLACED
place_inst -name r294_0 -location {189.600 5264.121} -status PLACED
place_inst -name r294_1 -location {189.600 5392.914} -status PLACED
place_inst -name r294_2 -location {189.600 5521.707} -status PLACED
place_inst -name b294 -location {189.600 5650.500} -status PLACED
place_inst -name r295_0 -location {8760.960 5077.014} -status PLACED
place_inst -name b295 -location {8760.960 5018.700} -status PLACED
place_inst -name r296_0 -location {8821.125 5135.328} -status PLACED
place_inst -name b296 -location {8881.291 5135.328} -status PLACED
place_inst -name r297_0 -location {8881.291 5013.596} -status PLACED
place_inst -name r297_1 -location {8881.291 4891.864} -status PLACED
place_inst -name r297_2 -location {8881.291 4770.132} -status PLACED
place_inst -name b297 -location {8881.291 4648.400} -status PLACED
place_inst -name r298_0 -location {8881.291 5295.114} -status PLACED
place_inst -name b298 -location {8881.291 5454.900} -status PLACED
place_inst -name r299_0 -location {8935.901 5135.328} -status PLACED
place_inst -name b299 -location {8990.512 5135.328} -status PLACED
place_inst -name r300_0 -location {8990.512 5020.014} -status PLACED
place_inst -name b300 -location {8990.512 4904.700} -status PLACED
place_inst -name r301_0 -location {8990.512 5289.864} -status PLACED
place_inst -name b301 -location {8990.512 5444.400} -status PLACED
place_inst -name r302_0 -location {8990.512 5325.514} -status PLACED
place_inst -name b302 -location {8990.512 5515.700} -status PLACED
place_inst -name r303_0 -location {8999.816 5135.328} -status PLACED
place_inst -name b303 -location {9009.120 5135.328} -status PLACED
place_inst -name r304_0 -location {9049.696 5135.328} -status PLACED
place_inst -name b304 -location {9090.272 5135.328} -status PLACED
place_inst -name r305_0 -location {9090.272 5013.596} -status PLACED
place_inst -name r305_1 -location {9090.272 4891.864} -status PLACED
place_inst -name r305_2 -location {9090.272 4770.132} -status PLACED
place_inst -name b305 -location {9090.272 4648.400} -status PLACED
place_inst -name r306_0 -location {9142.080 5135.328} -status PLACED
place_inst -name b306 -location {9193.888 5135.328} -status PLACED
place_inst -name r307_0 -location {9193.888 5056.014} -status PLACED
place_inst -name b307 -location {9193.888 4976.700} -status PLACED
place_inst -name r308_0 -location {9193.888 5228.814} -status PLACED
place_inst -name b308 -location {9193.888 5322.300} -status PLACED
place_inst -name r309_0 -location {9267.104 5135.328} -status PLACED
place_inst -name b309 -location {9340.320 5135.328} -status PLACED
place_inst -name r310_0 -location {9387.360 5135.328} -status PLACED
place_inst -name b310 -location {9434.400 5135.328} -status PLACED
place_inst -name r311_0 -location {9466.680 5135.328} -status PLACED
place_inst -name b311 -location {9806.880 5135.328} -status PLACED
place_inst -name r312_0 -location {9806.880 5060.264} -status PLACED
place_inst -name b312 -location {9806.880 4985.200} -status PLACED
place_inst -name r313_0 -location {10146.120 5135.328} -status PLACED
place_inst -name r313_1 -location {10161.640 5135.328} -status PLACED
place_inst -name r313_2 -location {10500.360 5135.328} -status PLACED
place_inst -name b313 -location {10515.360 5135.328} -status PLACED
place_inst -name r314_0 -location {10515.360 5060.264} -status PLACED
place_inst -name b314 -location {10515.360 4985.200} -status PLACED
place_inst -name r315_0 -location {10854.600 5135.328} -status PLACED
place_inst -name r315_1 -location {10870.120 5135.328} -status PLACED
place_inst -name r315_2 -location {11208.840 5135.328} -status PLACED
place_inst -name b315 -location {11223.840 5135.328} -status PLACED
place_inst -name r316_0 -location {11223.840 5060.264} -status PLACED
place_inst -name b316 -location {11223.840 4985.200} -status PLACED
place_inst -name r317_0 -location {11563.080 5135.328} -status PLACED
place_inst -name r317_1 -location {11578.600 5135.328} -status PLACED
place_inst -name r317_2 -location {11917.320 5135.328} -status PLACED
place_inst -name b317 -location {11932.320 5135.328} -status PLACED
place_inst -name r318_0 -location {11932.320 5060.264} -status PLACED
place_inst -name b318 -location {11932.320 4985.200} -status PLACED
place_inst -name r319_0 -location {12271.560 5135.328} -status PLACED
place_inst -name r319_1 -location {12287.080 5135.328} -status PLACED
place_inst -name r319_2 -location {12625.800 5135.328} -status PLACED
place_inst -name b319 -location {12640.800 5135.328} -status PLACED
place_inst -name r320_0 -location {12640.800 5060.264} -status PLACED
place_inst -name b320 -location {12640.800 4985.200} -status PLACED
place_inst -name r321_0 -location {12980.040 5135.328} -status PLACED
place_inst -name r321_1 -location {12995.560 5135.328} -status PLACED
place_inst -name r321_2 -location {13334.280 5135.328} -status PLACED
place_inst -name b321 -location {13349.280 5135.328} -status PLACED
place_inst -name r322_0 -location {13349.280 5060.264} -status PLACED
place_inst -name b322 -location {13349.280 4985.200} -status PLACED
place_inst -name r323_0 -location {13688.520 5135.328} -status PLACED
place_inst -name r323_1 -location {13704.040 5135.328} -status PLACED
place_inst -name r323_2 -location {14042.760 5135.328} -status PLACED
place_inst -name b323 -location {14057.760 5135.328} -status PLACED
place_inst -name r324_0 -location {14057.760 5060.264} -status PLACED
place_inst -name b324 -location {14057.760 4985.200} -status PLACED
place_inst -name r325_0 -location {14397.000 5135.328} -status PLACED
place_inst -name r325_1 -location {14412.520 5135.328} -status PLACED
place_inst -name r325_2 -location {14751.240 5135.328} -status PLACED
place_inst -name b325 -location {14766.240 5135.328} -status PLACED
place_inst -name r326_0 -location {14766.240 5060.264} -status PLACED
place_inst -name b326 -location {14766.240 4985.200} -status PLACED
place_inst -name r327_0 -location {15105.480 5135.328} -status PLACED
place_inst -name r327_1 -location {15121.000 5135.328} -status PLACED
place_inst -name r327_2 -location {15459.720 5135.328} -status PLACED
place_inst -name b327 -location {15474.720 5135.328} -status PLACED
place_inst -name r328_0 -location {15474.720 5060.264} -status PLACED
place_inst -name b328 -location {15474.720 4985.200} -status PLACED
place_inst -name r329_0 -location {15813.960 5135.328} -status PLACED
place_inst -name r329_1 -location {15829.480 5135.328} -status PLACED
place_inst -name r329_2 -location {16168.200 5135.328} -status PLACED
place_inst -name b329 -location {16183.200 5135.328} -status PLACED
place_inst -name r330_0 -location {16183.200 5060.264} -status PLACED
place_inst -name b330 -location {16183.200 4985.200} -status PLACED
place_inst -name r331_0 -location {16522.440 5135.328} -status PLACED
place_inst -name r331_1 -location {16537.960 5135.328} -status PLACED
place_inst -name r331_2 -location {16876.680 5135.328} -status PLACED
place_inst -name b331 -location {16891.680 5135.328} -status PLACED
place_inst -name r332_0 -location {16891.680 5060.264} -status PLACED
place_inst -name b332 -location {16891.680 4985.200} -status PLACED
place_inst -name r333_0 -location {16905.720 5135.328} -status PLACED
place_inst -name r333_1 -location {17230.920 5135.328} -status PLACED
place_inst -name r333_2 -location {17230.920 5135.328} -status PLACED
place_inst -name b333 -location {17332.320 5135.328} -status PLACED
place_inst -name r334_0 -location {17332.320 5246.764} -status PLACED
place_inst -name b334 -location {17332.320 5358.200} -status PLACED
place_inst -name r335_0 -location {17332.320 5264.121} -status PLACED
place_inst -name r335_1 -location {17332.320 5392.914} -status PLACED
place_inst -name r335_2 -location {17332.320 5521.707} -status PLACED
place_inst -name b335 -location {17332.320 5650.500} -status PLACED
place_inst -name r336_0 -location {8590.576 6172.128} -status PLACED
place_inst -name b336 -location {8420.192 6172.128} -status PLACED
place_inst -name r337_0 -location {8244.144 6172.128} -status PLACED
place_inst -name r337_1 -location {8068.096 6172.128} -status PLACED
place_inst -name r337_2 -location {7730.040 6172.128} -status PLACED
place_inst -name b337 -location {7716.000 6172.128} -status PLACED
place_inst -name r338_0 -location {7716.000 6097.064} -status PLACED
place_inst -name b338 -location {7716.000 6022.000} -status PLACED
place_inst -name r339_0 -location {7701.000 6172.128} -status PLACED
place_inst -name r339_1 -location {7362.280 6172.128} -status PLACED
place_inst -name r339_2 -location {7346.760 6172.128} -status PLACED
place_inst -name b339 -location {7007.520 6172.128} -status PLACED
place_inst -name r340_0 -location {7007.520 6097.064} -status PLACED
place_inst -name b340 -location {7007.520 6022.000} -status PLACED
place_inst -name r341_0 -location {6992.520 6172.128} -status PLACED
place_inst -name r341_1 -location {6653.800 6172.128} -status PLACED
place_inst -name r341_2 -location {6638.280 6172.128} -status PLACED
place_inst -name b341 -location {6299.040 6172.128} -status PLACED
place_inst -name r342_0 -location {6299.040 6097.064} -status PLACED
place_inst -name b342 -location {6299.040 6022.000} -status PLACED
place_inst -name r343_0 -location {6284.040 6172.128} -status PLACED
place_inst -name r343_1 -location {5945.320 6172.128} -status PLACED
place_inst -name r343_2 -location {5929.800 6172.128} -status PLACED
place_inst -name b343 -location {5590.560 6172.128} -status PLACED
place_inst -name r344_0 -location {5590.560 6097.064} -status PLACED
place_inst -name b344 -location {5590.560 6022.000} -status PLACED
place_inst -name r345_0 -location {5575.560 6172.128} -status PLACED
place_inst -name r345_1 -location {5236.840 6172.128} -status PLACED
place_inst -name r345_2 -location {5221.320 6172.128} -status PLACED
place_inst -name b345 -location {4882.080 6172.128} -status PLACED
place_inst -name r346_0 -location {4882.080 6097.064} -status PLACED
place_inst -name b346 -location {4882.080 6022.000} -status PLACED
place_inst -name r347_0 -location {4867.080 6172.128} -status PLACED
place_inst -name r347_1 -location {4528.360 6172.128} -status PLACED
place_inst -name r347_2 -location {4512.840 6172.128} -status PLACED
place_inst -name b347 -location {4173.600 6172.128} -status PLACED
place_inst -name r348_0 -location {4173.600 6097.064} -status PLACED
place_inst -name b348 -location {4173.600 6022.000} -status PLACED
place_inst -name r349_0 -location {4158.600 6172.128} -status PLACED
place_inst -name r349_1 -location {3819.880 6172.128} -status PLACED
place_inst -name r349_2 -location {3804.360 6172.128} -status PLACED
place_inst -name b349 -location {3465.120 6172.128} -status PLACED
place_inst -name r350_0 -location {3465.120 6097.064} -status PLACED
place_inst -name b350 -location {3465.120 6022.000} -status PLACED
place_inst -name r351_0 -location {3450.120 6172.128} -status PLACED
place_inst -name r351_1 -location {3111.400 6172.128} -status PLACED
place_inst -name r351_2 -location {3095.880 6172.128} -status PLACED
place_inst -name b351 -location {2756.640 6172.128} -status PLACED
place_inst -name r352_0 -location {2756.640 6097.064} -status PLACED
place_inst -name b352 -location {2756.640 6022.000} -status PLACED
place_inst -name r353_0 -location {2741.640 6172.128} -status PLACED
place_inst -name r353_1 -location {2402.920 6172.128} -status PLACED
place_inst -name r353_2 -location {2387.400 6172.128} -status PLACED
place_inst -name b353 -location {2048.160 6172.128} -status PLACED
place_inst -name r354_0 -location {2048.160 6097.064} -status PLACED
place_inst -name b354 -location {2048.160 6022.000} -status PLACED
place_inst -name r355_0 -location {2033.160 6172.128} -status PLACED
place_inst -name r355_1 -location {1694.440 6172.128} -status PLACED
place_inst -name r355_2 -location {1678.920 6172.128} -status PLACED
place_inst -name b355 -location {1339.680 6172.128} -status PLACED
place_inst -name r356_0 -location {1339.680 6097.064} -status PLACED
place_inst -name b356 -location {1339.680 6022.000} -status PLACED
place_inst -name r357_0 -location {1324.680 6172.128} -status PLACED
place_inst -name r357_1 -location {985.960 6172.128} -status PLACED
place_inst -name r357_2 -location {970.440 6172.128} -status PLACED
place_inst -name b357 -location {631.200 6172.128} -status PLACED
place_inst -name r358_0 -location {631.200 6097.064} -status PLACED
place_inst -name b358 -location {631.200 6022.000} -status PLACED
place_inst -name r359_0 -location {291.000 6172.128} -status PLACED
place_inst -name b359 -location {235.456 6172.128} -status PLACED
place_inst -name r360_0 -location {235.456 6036.264} -status PLACED
place_inst -name b360 -location {235.456 5900.400} -status PLACED
place_inst -name r361_0 -location {8760.960 6131.864} -status PLACED
place_inst -name b361 -location {8760.960 6091.600} -status PLACED
place_inst -name r362_0 -location {8809.200 6172.128} -status PLACED
place_inst -name b362 -location {8857.440 6172.128} -status PLACED
place_inst -name r363_0 -location {8857.440 6060.996} -status PLACED
place_inst -name r363_1 -location {8857.440 5949.864} -status PLACED
place_inst -name r363_2 -location {8857.440 5838.732} -status PLACED
place_inst -name b363 -location {8857.440 5727.600} -status PLACED
place_inst -name r364_0 -location {8857.440 6086.264} -status PLACED
place_inst -name b364 -location {8857.440 6000.400} -status PLACED
place_inst -name r365_0 -location {8857.440 6216.714} -status PLACED
place_inst -name b365 -location {8857.440 6261.300} -status PLACED
place_inst -name r366_0 -location {8857.440 6237.864} -status PLACED
place_inst -name b366 -location {8857.440 6303.600} -status PLACED
place_inst -name r367_0 -location {8888.352 6172.128} -status PLACED
place_inst -name b367 -location {8919.264 6172.128} -status PLACED
place_inst -name r368_0 -location {8919.264 6300.946} -status PLACED
place_inst -name r368_1 -location {8919.264 6429.764} -status PLACED
place_inst -name r368_2 -location {8919.264 6558.582} -status PLACED
place_inst -name b368 -location {8919.264 6687.400} -status PLACED
place_inst -name r369_0 -location {8962.272 6172.128} -status PLACED
place_inst -name b369 -location {9005.280 6172.128} -status PLACED
place_inst -name r370_0 -location {9005.280 6060.071} -status PLACED
place_inst -name r370_1 -location {9005.280 5948.014} -status PLACED
place_inst -name r370_2 -location {9005.280 5835.957} -status PLACED
place_inst -name b370 -location {9005.280 5723.900} -status PLACED
place_inst -name r371_0 -location {9005.280 5998.214} -status PLACED
place_inst -name b371 -location {9005.280 5824.300} -status PLACED
place_inst -name r372_0 -location {9005.280 6082.164} -status PLACED
place_inst -name b372 -location {9005.280 5992.200} -status PLACED
place_inst -name r373_0 -location {9005.280 6213.814} -status PLACED
place_inst -name b373 -location {9005.280 6255.500} -status PLACED
place_inst -name r374_0 -location {9050.613 6172.128} -status PLACED
place_inst -name b374 -location {9095.947 6172.128} -status PLACED
place_inst -name r375_0 -location {9095.947 6092.814} -status PLACED
place_inst -name b375 -location {9095.947 6013.500} -status PLACED
place_inst -name r376_0 -location {9095.947 6237.864} -status PLACED
place_inst -name b376 -location {9095.947 6303.600} -status PLACED
place_inst -name r377_0 -location {9150.827 6172.128} -status PLACED
place_inst -name b377 -location {9205.707 6172.128} -status PLACED
place_inst -name r378_0 -location {9205.707 6046.071} -status PLACED
place_inst -name r378_1 -location {9205.707 5920.014} -status PLACED
place_inst -name r378_2 -location {9205.707 5793.957} -status PLACED
place_inst -name b378 -location {9205.707 5667.900} -status PLACED
place_inst -name r379_0 -location {9205.707 6265.614} -status PLACED
place_inst -name b379 -location {9205.707 6359.100} -status PLACED
place_inst -name r380_0 -location {9205.707 6300.946} -status PLACED
place_inst -name r380_1 -location {9205.707 6429.764} -status PLACED
place_inst -name r380_2 -location {9205.707 6558.582} -status PLACED
place_inst -name b380 -location {9205.707 6687.400} -status PLACED
place_inst -name r381_0 -location {9234.613 6172.128} -status PLACED
place_inst -name b381 -location {9263.520 6172.128} -status PLACED
place_inst -name r382_0 -location {9263.520 6092.814} -status PLACED
place_inst -name b382 -location {9263.520 6013.500} -status PLACED
place_inst -name r383_0 -location {9310.020 6172.128} -status PLACED
place_inst -name b383 -location {9356.519 6172.128} -status PLACED
place_inst -name r384_0 -location {9466.680 6172.128} -status PLACED
place_inst -name r384_1 -location {9466.680 6172.128} -status PLACED
place_inst -name r384_2 -location {9791.880 6172.128} -status PLACED
place_inst -name b384 -location {9805.920 6172.128} -status PLACED
place_inst -name r385_0 -location {9805.920 6097.064} -status PLACED
place_inst -name b385 -location {9805.920 6022.000} -status PLACED
place_inst -name r386_0 -location {9820.920 6172.128} -status PLACED
place_inst -name r386_1 -location {10159.640 6172.128} -status PLACED
place_inst -name r386_2 -location {10175.160 6172.128} -status PLACED
place_inst -name b386 -location {10514.400 6172.128} -status PLACED
place_inst -name r387_0 -location {10514.400 6097.064} -status PLACED
place_inst -name b387 -location {10514.400 6022.000} -status PLACED
place_inst -name r388_0 -location {10529.400 6172.128} -status PLACED
place_inst -name r388_1 -location {10868.120 6172.128} -status PLACED
place_inst -name r388_2 -location {10883.640 6172.128} -status PLACED
place_inst -name b388 -location {11222.880 6172.128} -status PLACED
place_inst -name r389_0 -location {11222.880 6097.064} -status PLACED
place_inst -name b389 -location {11222.880 6022.000} -status PLACED
place_inst -name r390_0 -location {11237.880 6172.128} -status PLACED
place_inst -name r390_1 -location {11576.600 6172.128} -status PLACED
place_inst -name r390_2 -location {11592.120 6172.128} -status PLACED
place_inst -name b390 -location {11931.360 6172.128} -status PLACED
place_inst -name r391_0 -location {11931.360 6097.064} -status PLACED
place_inst -name b391 -location {11931.360 6022.000} -status PLACED
place_inst -name r392_0 -location {11946.360 6172.128} -status PLACED
place_inst -name r392_1 -location {12285.080 6172.128} -status PLACED
place_inst -name r392_2 -location {12300.600 6172.128} -status PLACED
place_inst -name b392 -location {12639.840 6172.128} -status PLACED
place_inst -name r393_0 -location {12639.840 6097.064} -status PLACED
place_inst -name b393 -location {12639.840 6022.000} -status PLACED
place_inst -name r394_0 -location {12654.840 6172.128} -status PLACED
place_inst -name r394_1 -location {12993.560 6172.128} -status PLACED
place_inst -name r394_2 -location {13009.080 6172.128} -status PLACED
place_inst -name b394 -location {13348.320 6172.128} -status PLACED
place_inst -name r395_0 -location {13348.320 6097.064} -status PLACED
place_inst -name b395 -location {13348.320 6022.000} -status PLACED
place_inst -name r396_0 -location {13363.320 6172.128} -status PLACED
place_inst -name r396_1 -location {13702.040 6172.128} -status PLACED
place_inst -name r396_2 -location {13717.560 6172.128} -status PLACED
place_inst -name b396 -location {14056.800 6172.128} -status PLACED
place_inst -name r397_0 -location {14056.800 6097.064} -status PLACED
place_inst -name b397 -location {14056.800 6022.000} -status PLACED
place_inst -name r398_0 -location {14071.800 6172.128} -status PLACED
place_inst -name r398_1 -location {14410.520 6172.128} -status PLACED
place_inst -name r398_2 -location {14426.040 6172.128} -status PLACED
place_inst -name b398 -location {14765.280 6172.128} -status PLACED
place_inst -name r399_0 -location {14765.280 6097.064} -status PLACED
place_inst -name b399 -location {14765.280 6022.000} -status PLACED
place_inst -name r400_0 -location {14780.280 6172.128} -status PLACED
place_inst -name r400_1 -location {15119.000 6172.128} -status PLACED
place_inst -name r400_2 -location {15134.520 6172.128} -status PLACED
place_inst -name b400 -location {15473.760 6172.128} -status PLACED
place_inst -name r401_0 -location {15473.760 6097.064} -status PLACED
place_inst -name b401 -location {15473.760 6022.000} -status PLACED
place_inst -name r402_0 -location {15488.760 6172.128} -status PLACED
place_inst -name r402_1 -location {15827.480 6172.128} -status PLACED
place_inst -name r402_2 -location {15843.000 6172.128} -status PLACED
place_inst -name b402 -location {16182.240 6172.128} -status PLACED
place_inst -name r403_0 -location {16182.240 6097.064} -status PLACED
place_inst -name b403 -location {16182.240 6022.000} -status PLACED
place_inst -name r404_0 -location {16197.240 6172.128} -status PLACED
place_inst -name r404_1 -location {16535.960 6172.128} -status PLACED
place_inst -name r404_2 -location {16551.480 6172.128} -status PLACED
place_inst -name b404 -location {16890.720 6172.128} -status PLACED
place_inst -name r405_0 -location {16890.720 6097.064} -status PLACED
place_inst -name b405 -location {16890.720 6022.000} -status PLACED
place_inst -name r406_0 -location {17230.920 6172.128} -status PLACED
place_inst -name b406 -location {17286.464 6172.128} -status PLACED
place_inst -name r407_0 -location {17286.464 6036.264} -status PLACED
place_inst -name b407 -location {17286.464 5900.400} -status PLACED
place_inst -name r408_0 -location {8590.064 7208.928} -status PLACED
place_inst -name b408 -location {8419.168 7208.928} -status PLACED
place_inst -name r409_0 -location {8253.344 7208.928} -status PLACED
place_inst -name b409 -location {8087.520 7208.928} -status PLACED
place_inst -name r410_0 -location {8055.240 7208.928} -status PLACED
place_inst -name b410 -location {7715.040 7208.928} -status PLACED
place_inst -name r411_0 -location {7715.040 7133.864} -status PLACED
place_inst -name b411 -location {7715.040 7058.800} -status PLACED
place_inst -name r412_0 -location {7375.800 7208.928} -status PLACED
place_inst -name r412_1 -location {7360.280 7208.928} -status PLACED
place_inst -name r412_2 -location {7021.560 7208.928} -status PLACED
place_inst -name b412 -location {7006.560 7208.928} -status PLACED
place_inst -name r413_0 -location {7006.560 7133.864} -status PLACED
place_inst -name b413 -location {7006.560 7058.800} -status PLACED
place_inst -name r414_0 -location {6667.320 7208.928} -status PLACED
place_inst -name r414_1 -location {6651.800 7208.928} -status PLACED
place_inst -name r414_2 -location {6313.080 7208.928} -status PLACED
place_inst -name b414 -location {6298.080 7208.928} -status PLACED
place_inst -name r415_0 -location {6298.080 7133.864} -status PLACED
place_inst -name b415 -location {6298.080 7058.800} -status PLACED
place_inst -name r416_0 -location {5958.840 7208.928} -status PLACED
place_inst -name r416_1 -location {5943.320 7208.928} -status PLACED
place_inst -name r416_2 -location {5604.600 7208.928} -status PLACED
place_inst -name b416 -location {5589.600 7208.928} -status PLACED
place_inst -name r417_0 -location {5589.600 7133.864} -status PLACED
place_inst -name b417 -location {5589.600 7058.800} -status PLACED
place_inst -name r418_0 -location {5250.360 7208.928} -status PLACED
place_inst -name r418_1 -location {5234.840 7208.928} -status PLACED
place_inst -name r418_2 -location {4896.120 7208.928} -status PLACED
place_inst -name b418 -location {4881.120 7208.928} -status PLACED
place_inst -name r419_0 -location {4881.120 7133.864} -status PLACED
place_inst -name b419 -location {4881.120 7058.800} -status PLACED
place_inst -name r420_0 -location {4541.880 7208.928} -status PLACED
place_inst -name r420_1 -location {4526.360 7208.928} -status PLACED
place_inst -name r420_2 -location {4187.640 7208.928} -status PLACED
place_inst -name b420 -location {4172.640 7208.928} -status PLACED
place_inst -name r421_0 -location {4172.640 7133.864} -status PLACED
place_inst -name b421 -location {4172.640 7058.800} -status PLACED
place_inst -name r422_0 -location {3833.400 7208.928} -status PLACED
place_inst -name r422_1 -location {3817.880 7208.928} -status PLACED
place_inst -name r422_2 -location {3479.160 7208.928} -status PLACED
place_inst -name b422 -location {3464.160 7208.928} -status PLACED
place_inst -name r423_0 -location {3464.160 7133.864} -status PLACED
place_inst -name b423 -location {3464.160 7058.800} -status PLACED
place_inst -name r424_0 -location {3124.920 7208.928} -status PLACED
place_inst -name r424_1 -location {3109.400 7208.928} -status PLACED
place_inst -name r424_2 -location {2770.680 7208.928} -status PLACED
place_inst -name b424 -location {2755.680 7208.928} -status PLACED
place_inst -name r425_0 -location {2755.680 7133.864} -status PLACED
place_inst -name b425 -location {2755.680 7058.800} -status PLACED
place_inst -name r426_0 -location {2416.440 7208.928} -status PLACED
place_inst -name r426_1 -location {2400.920 7208.928} -status PLACED
place_inst -name r426_2 -location {2062.200 7208.928} -status PLACED
place_inst -name b426 -location {2047.200 7208.928} -status PLACED
place_inst -name r427_0 -location {2047.200 7133.864} -status PLACED
place_inst -name b427 -location {2047.200 7058.800} -status PLACED
place_inst -name r428_0 -location {1707.960 7208.928} -status PLACED
place_inst -name r428_1 -location {1692.440 7208.928} -status PLACED
place_inst -name r428_2 -location {1353.720 7208.928} -status PLACED
place_inst -name b428 -location {1338.720 7208.928} -status PLACED
place_inst -name r429_0 -location {1338.720 7133.864} -status PLACED
place_inst -name b429 -location {1338.720 7058.800} -status PLACED
place_inst -name r430_0 -location {999.480 7208.928} -status PLACED
place_inst -name r430_1 -location {983.960 7208.928} -status PLACED
place_inst -name r430_2 -location {645.240 7208.928} -status PLACED
place_inst -name b430 -location {630.240 7208.928} -status PLACED
place_inst -name r431_0 -location {630.240 7133.864} -status PLACED
place_inst -name b431 -location {630.240 7058.800} -status PLACED
place_inst -name r432_0 -location {616.200 7208.928} -status PLACED
place_inst -name r432_1 -location {291.000 7208.928} -status PLACED
place_inst -name r432_2 -location {291.000 7208.928} -status PLACED
place_inst -name b432 -location {189.600 7208.928} -status PLACED
place_inst -name r433_0 -location {189.600 7320.364} -status PLACED
place_inst -name b433 -location {189.600 7431.800} -status PLACED
place_inst -name r434_0 -location {189.600 7337.721} -status PLACED
place_inst -name r434_1 -location {189.600 7466.514} -status PLACED
place_inst -name r434_2 -location {189.600 7595.307} -status PLACED
place_inst -name b434 -location {189.600 7724.100} -status PLACED
place_inst -name r435_0 -location {8760.960 7150.614} -status PLACED
place_inst -name b435 -location {8760.960 7092.300} -status PLACED
place_inst -name r436_0 -location {8821.125 7208.928} -status PLACED
place_inst -name b436 -location {8881.291 7208.928} -status PLACED
place_inst -name r437_0 -location {8881.291 7087.196} -status PLACED
place_inst -name r437_1 -location {8881.291 6965.464} -status PLACED
place_inst -name r437_2 -location {8881.291 6843.732} -status PLACED
place_inst -name b437 -location {8881.291 6722.000} -status PLACED
place_inst -name r438_0 -location {8881.291 7368.714} -status PLACED
place_inst -name b438 -location {8881.291 7528.500} -status PLACED
place_inst -name r439_0 -location {8935.901 7208.928} -status PLACED
place_inst -name b439 -location {8990.512 7208.928} -status PLACED
place_inst -name r440_0 -location {8990.512 7093.614} -status PLACED
place_inst -name b440 -location {8990.512 6978.300} -status PLACED
place_inst -name r441_0 -location {8990.512 7363.464} -status PLACED
place_inst -name b441 -location {8990.512 7518.000} -status PLACED
place_inst -name r442_0 -location {8990.512 7399.114} -status PLACED
place_inst -name b442 -location {8990.512 7589.300} -status PLACED
place_inst -name r443_0 -location {8999.816 7208.928} -status PLACED
place_inst -name b443 -location {9009.120 7208.928} -status PLACED
place_inst -name r444_0 -location {9049.696 7208.928} -status PLACED
place_inst -name b444 -location {9090.272 7208.928} -status PLACED
place_inst -name r445_0 -location {9090.272 7087.196} -status PLACED
place_inst -name r445_1 -location {9090.272 6965.464} -status PLACED
place_inst -name r445_2 -location {9090.272 6843.732} -status PLACED
place_inst -name b445 -location {9090.272 6722.000} -status PLACED
place_inst -name r446_0 -location {9142.080 7208.928} -status PLACED
place_inst -name b446 -location {9193.888 7208.928} -status PLACED
place_inst -name r447_0 -location {9193.888 7129.614} -status PLACED
place_inst -name b447 -location {9193.888 7050.300} -status PLACED
place_inst -name r448_0 -location {9193.888 7302.414} -status PLACED
place_inst -name b448 -location {9193.888 7395.900} -status PLACED
place_inst -name r449_0 -location {9267.104 7208.928} -status PLACED
place_inst -name b449 -location {9340.320 7208.928} -status PLACED
place_inst -name r450_0 -location {9387.360 7208.928} -status PLACED
place_inst -name b450 -location {9434.400 7208.928} -status PLACED
place_inst -name r451_0 -location {9466.680 7208.928} -status PLACED
place_inst -name b451 -location {9806.880 7208.928} -status PLACED
place_inst -name r452_0 -location {9806.880 7133.864} -status PLACED
place_inst -name b452 -location {9806.880 7058.800} -status PLACED
place_inst -name r453_0 -location {10146.120 7208.928} -status PLACED
place_inst -name r453_1 -location {10161.640 7208.928} -status PLACED
place_inst -name r453_2 -location {10500.360 7208.928} -status PLACED
place_inst -name b453 -location {10515.360 7208.928} -status PLACED
place_inst -name r454_0 -location {10515.360 7133.864} -status PLACED
place_inst -name b454 -location {10515.360 7058.800} -status PLACED
place_inst -name r455_0 -location {10854.600 7208.928} -status PLACED
place_inst -name r455_1 -location {10870.120 7208.928} -status PLACED
place_inst -name r455_2 -location {11208.840 7208.928} -status PLACED
place_inst -name b455 -location {11223.840 7208.928} -status PLACED
place_inst -name r456_0 -location {11223.840 7133.864} -status PLACED
place_inst -name b456 -location {11223.840 7058.800} -status PLACED
place_inst -name r457_0 -location {11563.080 7208.928} -status PLACED
place_inst -name r457_1 -location {11578.600 7208.928} -status PLACED
place_inst -name r457_2 -location {11917.320 7208.928} -status PLACED
place_inst -name b457 -location {11932.320 7208.928} -status PLACED
place_inst -name r458_0 -location {11932.320 7133.864} -status PLACED
place_inst -name b458 -location {11932.320 7058.800} -status PLACED
place_inst -name r459_0 -location {12271.560 7208.928} -status PLACED
place_inst -name r459_1 -location {12287.080 7208.928} -status PLACED
place_inst -name r459_2 -location {12625.800 7208.928} -status PLACED
place_inst -name b459 -location {12640.800 7208.928} -status PLACED
place_inst -name r460_0 -location {12640.800 7133.864} -status PLACED
place_inst -name b460 -location {12640.800 7058.800} -status PLACED
place_inst -name r461_0 -location {12980.040 7208.928} -status PLACED
place_inst -name r461_1 -location {12995.560 7208.928} -status PLACED
place_inst -name r461_2 -location {13334.280 7208.928} -status PLACED
place_inst -name b461 -location {13349.280 7208.928} -status PLACED
place_inst -name r462_0 -location {13349.280 7133.864} -status PLACED
place_inst -name b462 -location {13349.280 7058.800} -status PLACED
place_inst -name r463_0 -location {13688.520 7208.928} -status PLACED
place_inst -name r463_1 -location {13704.040 7208.928} -status PLACED
place_inst -name r463_2 -location {14042.760 7208.928} -status PLACED
place_inst -name b463 -location {14057.760 7208.928} -status PLACED
place_inst -name r464_0 -location {14057.760 7133.864} -status PLACED
place_inst -name b464 -location {14057.760 7058.800} -status PLACED
place_inst -name r465_0 -location {14397.000 7208.928} -status PLACED
place_inst -name r465_1 -location {14412.520 7208.928} -status PLACED
place_inst -name r465_2 -location {14751.240 7208.928} -status PLACED
place_inst -name b465 -location {14766.240 7208.928} -status PLACED
place_inst -name r466_0 -location {14766.240 7133.864} -status PLACED
place_inst -name b466 -location {14766.240 7058.800} -status PLACED
place_inst -name r467_0 -location {15105.480 7208.928} -status PLACED
place_inst -name r467_1 -location {15121.000 7208.928} -status PLACED
place_inst -name r467_2 -location {15459.720 7208.928} -status PLACED
place_inst -name b467 -location {15474.720 7208.928} -status PLACED
place_inst -name r468_0 -location {15474.720 7133.864} -status PLACED
place_inst -name b468 -location {15474.720 7058.800} -status PLACED
place_inst -name r469_0 -location {15813.960 7208.928} -status PLACED
place_inst -name r469_1 -location {15829.480 7208.928} -status PLACED
place_inst -name r469_2 -location {16168.200 7208.928} -status PLACED
place_inst -name b469 -location {16183.200 7208.928} -status PLACED
place_inst -name r470_0 -location {16183.200 7133.864} -status PLACED
place_inst -name b470 -location {16183.200 7058.800} -status PLACED
place_inst -name r471_0 -location {16522.440 7208.928} -status PLACED
place_inst -name r471_1 -location {16537.960 7208.928} -status PLACED
place_inst -name r471_2 -location {16876.680 7208.928} -status PLACED
place_inst -name b471 -location {16891.680 7208.928} -status PLACED
place_inst -name r472_0 -location {16891.680 7133.864} -status PLACED
place_inst -name b472 -location {16891.680 7058.800} -status PLACED
place_inst -name r473_0 -location {16905.720 7208.928} -status PLACED
place_inst -name r473_1 -location {17230.920 7208.928} -status PLACED
place_inst -name r473_2 -location {17230.920 7208.928} -status PLACED
place_inst -name b473 -location {17332.320 7208.928} -status PLACED
place_inst -name r474_0 -location {17332.320 7320.364} -status PLACED
place_inst -name b474 -location {17332.320 7431.800} -status PLACED
place_inst -name r475_0 -location {17332.320 7337.721} -status PLACED
place_inst -name r475_1 -location {17332.320 7466.514} -status PLACED
place_inst -name r475_2 -location {17332.320 7595.307} -status PLACED
place_inst -name b475 -location {17332.320 7724.100} -status PLACED
place_inst -name r476_0 -location {8590.576 8245.728} -status PLACED
place_inst -name b476 -location {8420.192 8245.728} -status PLACED
place_inst -name r477_0 -location {8244.144 8245.728} -status PLACED
place_inst -name r477_1 -location {8068.096 8245.728} -status PLACED
place_inst -name r477_2 -location {7730.040 8245.728} -status PLACED
place_inst -name b477 -location {7716.000 8245.728} -status PLACED
place_inst -name r478_0 -location {7716.000 8170.664} -status PLACED
place_inst -name b478 -location {7716.000 8095.600} -status PLACED
place_inst -name r479_0 -location {7701.000 8245.728} -status PLACED
place_inst -name r479_1 -location {7362.280 8245.728} -status PLACED
place_inst -name r479_2 -location {7346.760 8245.728} -status PLACED
place_inst -name b479 -location {7007.520 8245.728} -status PLACED
place_inst -name r480_0 -location {7007.520 8170.664} -status PLACED
place_inst -name b480 -location {7007.520 8095.600} -status PLACED
place_inst -name r481_0 -location {6992.520 8245.728} -status PLACED
place_inst -name r481_1 -location {6653.800 8245.728} -status PLACED
place_inst -name r481_2 -location {6638.280 8245.728} -status PLACED
place_inst -name b481 -location {6299.040 8245.728} -status PLACED
place_inst -name r482_0 -location {6299.040 8170.664} -status PLACED
place_inst -name b482 -location {6299.040 8095.600} -status PLACED
place_inst -name r483_0 -location {6284.040 8245.728} -status PLACED
place_inst -name r483_1 -location {5945.320 8245.728} -status PLACED
place_inst -name r483_2 -location {5929.800 8245.728} -status PLACED
place_inst -name b483 -location {5590.560 8245.728} -status PLACED
place_inst -name r484_0 -location {5590.560 8170.664} -status PLACED
place_inst -name b484 -location {5590.560 8095.600} -status PLACED
place_inst -name r485_0 -location {5575.560 8245.728} -status PLACED
place_inst -name r485_1 -location {5236.840 8245.728} -status PLACED
place_inst -name r485_2 -location {5221.320 8245.728} -status PLACED
place_inst -name b485 -location {4882.080 8245.728} -status PLACED
place_inst -name r486_0 -location {4882.080 8170.664} -status PLACED
place_inst -name b486 -location {4882.080 8095.600} -status PLACED
place_inst -name r487_0 -location {4867.080 8245.728} -status PLACED
place_inst -name r487_1 -location {4528.360 8245.728} -status PLACED
place_inst -name r487_2 -location {4512.840 8245.728} -status PLACED
place_inst -name b487 -location {4173.600 8245.728} -status PLACED
place_inst -name r488_0 -location {4173.600 8170.664} -status PLACED
place_inst -name b488 -location {4173.600 8095.600} -status PLACED
place_inst -name r489_0 -location {4158.600 8245.728} -status PLACED
place_inst -name r489_1 -location {3819.880 8245.728} -status PLACED
place_inst -name r489_2 -location {3804.360 8245.728} -status PLACED
place_inst -name b489 -location {3465.120 8245.728} -status PLACED
place_inst -name r490_0 -location {3465.120 8170.664} -status PLACED
place_inst -name b490 -location {3465.120 8095.600} -status PLACED
place_inst -name r491_0 -location {3450.120 8245.728} -status PLACED
place_inst -name r491_1 -location {3111.400 8245.728} -status PLACED
place_inst -name r491_2 -location {3095.880 8245.728} -status PLACED
place_inst -name b491 -location {2756.640 8245.728} -status PLACED
place_inst -name r492_0 -location {2756.640 8170.664} -status PLACED
place_inst -name b492 -location {2756.640 8095.600} -status PLACED
place_inst -name r493_0 -location {2741.640 8245.728} -status PLACED
place_inst -name r493_1 -location {2402.920 8245.728} -status PLACED
place_inst -name r493_2 -location {2387.400 8245.728} -status PLACED
place_inst -name b493 -location {2048.160 8245.728} -status PLACED
place_inst -name r494_0 -location {2048.160 8170.664} -status PLACED
place_inst -name b494 -location {2048.160 8095.600} -status PLACED
place_inst -name r495_0 -location {2033.160 8245.728} -status PLACED
place_inst -name r495_1 -location {1694.440 8245.728} -status PLACED
place_inst -name r495_2 -location {1678.920 8245.728} -status PLACED
place_inst -name b495 -location {1339.680 8245.728} -status PLACED
place_inst -name r496_0 -location {1339.680 8170.664} -status PLACED
place_inst -name b496 -location {1339.680 8095.600} -status PLACED
place_inst -name r497_0 -location {1324.680 8245.728} -status PLACED
place_inst -name r497_1 -location {985.960 8245.728} -status PLACED
place_inst -name r497_2 -location {970.440 8245.728} -status PLACED
place_inst -name b497 -location {631.200 8245.728} -status PLACED
place_inst -name r498_0 -location {631.200 8170.664} -status PLACED
place_inst -name b498 -location {631.200 8095.600} -status PLACED
place_inst -name r499_0 -location {291.000 8245.728} -status PLACED
place_inst -name b499 -location {235.456 8245.728} -status PLACED
place_inst -name r500_0 -location {235.456 8109.864} -status PLACED
place_inst -name b500 -location {235.456 7974.000} -status PLACED
place_inst -name r501_0 -location {8760.960 8205.464} -status PLACED
place_inst -name b501 -location {8760.960 8165.200} -status PLACED
place_inst -name r502_0 -location {8809.200 8245.728} -status PLACED
place_inst -name b502 -location {8857.440 8245.728} -status PLACED
place_inst -name r503_0 -location {8857.440 8134.596} -status PLACED
place_inst -name r503_1 -location {8857.440 8023.464} -status PLACED
place_inst -name r503_2 -location {8857.440 7912.332} -status PLACED
place_inst -name b503 -location {8857.440 7801.200} -status PLACED
place_inst -name r504_0 -location {8857.440 8159.864} -status PLACED
place_inst -name b504 -location {8857.440 8074.000} -status PLACED
place_inst -name r505_0 -location {8857.440 8290.314} -status PLACED
place_inst -name b505 -location {8857.440 8334.900} -status PLACED
place_inst -name r506_0 -location {8857.440 8311.464} -status PLACED
place_inst -name b506 -location {8857.440 8377.200} -status PLACED
place_inst -name r507_0 -location {8888.352 8245.728} -status PLACED
place_inst -name b507 -location {8919.264 8245.728} -status PLACED
place_inst -name r508_0 -location {8919.264 8374.546} -status PLACED
place_inst -name r508_1 -location {8919.264 8503.364} -status PLACED
place_inst -name r508_2 -location {8919.264 8632.182} -status PLACED
place_inst -name b508 -location {8919.264 8761.000} -status PLACED
place_inst -name r509_0 -location {8962.272 8245.728} -status PLACED
place_inst -name b509 -location {9005.280 8245.728} -status PLACED
place_inst -name r510_0 -location {9005.280 8133.671} -status PLACED
place_inst -name r510_1 -location {9005.280 8021.614} -status PLACED
place_inst -name r510_2 -location {9005.280 7909.557} -status PLACED
place_inst -name b510 -location {9005.280 7797.500} -status PLACED
place_inst -name r511_0 -location {9005.280 8071.814} -status PLACED
place_inst -name b511 -location {9005.280 7897.900} -status PLACED
place_inst -name r512_0 -location {9005.280 8155.764} -status PLACED
place_inst -name b512 -location {9005.280 8065.800} -status PLACED
place_inst -name r513_0 -location {9005.280 8287.414} -status PLACED
place_inst -name b513 -location {9005.280 8329.100} -status PLACED
place_inst -name r514_0 -location {9050.613 8245.728} -status PLACED
place_inst -name b514 -location {9095.947 8245.728} -status PLACED
place_inst -name r515_0 -location {9095.947 8166.414} -status PLACED
place_inst -name b515 -location {9095.947 8087.100} -status PLACED
place_inst -name r516_0 -location {9095.947 8311.464} -status PLACED
place_inst -name b516 -location {9095.947 8377.200} -status PLACED
place_inst -name r517_0 -location {9150.827 8245.728} -status PLACED
place_inst -name b517 -location {9205.707 8245.728} -status PLACED
place_inst -name r518_0 -location {9205.707 8119.671} -status PLACED
place_inst -name r518_1 -location {9205.707 7993.614} -status PLACED
place_inst -name r518_2 -location {9205.707 7867.557} -status PLACED
place_inst -name b518 -location {9205.707 7741.500} -status PLACED
place_inst -name r519_0 -location {9205.707 8339.214} -status PLACED
place_inst -name b519 -location {9205.707 8432.700} -status PLACED
place_inst -name r520_0 -location {9205.707 8374.546} -status PLACED
place_inst -name r520_1 -location {9205.707 8503.364} -status PLACED
place_inst -name r520_2 -location {9205.707 8632.182} -status PLACED
place_inst -name b520 -location {9205.707 8761.000} -status PLACED
place_inst -name r521_0 -location {9234.613 8245.728} -status PLACED
place_inst -name b521 -location {9263.520 8245.728} -status PLACED
place_inst -name r522_0 -location {9263.520 8166.414} -status PLACED
place_inst -name b522 -location {9263.520 8087.100} -status PLACED
place_inst -name r523_0 -location {9310.020 8245.728} -status PLACED
place_inst -name b523 -location {9356.519 8245.728} -status PLACED
place_inst -name r524_0 -location {9466.680 8245.728} -status PLACED
place_inst -name r524_1 -location {9466.680 8245.728} -status PLACED
place_inst -name r524_2 -location {9791.880 8245.728} -status PLACED
place_inst -name b524 -location {9805.920 8245.728} -status PLACED
place_inst -name r525_0 -location {9805.920 8170.664} -status PLACED
place_inst -name b525 -location {9805.920 8095.600} -status PLACED
place_inst -name r526_0 -location {9820.920 8245.728} -status PLACED
place_inst -name r526_1 -location {10159.640 8245.728} -status PLACED
place_inst -name r526_2 -location {10175.160 8245.728} -status PLACED
place_inst -name b526 -location {10514.400 8245.728} -status PLACED
place_inst -name r527_0 -location {10514.400 8170.664} -status PLACED
place_inst -name b527 -location {10514.400 8095.600} -status PLACED
place_inst -name r528_0 -location {10529.400 8245.728} -status PLACED
place_inst -name r528_1 -location {10868.120 8245.728} -status PLACED
place_inst -name r528_2 -location {10883.640 8245.728} -status PLACED
place_inst -name b528 -location {11222.880 8245.728} -status PLACED
place_inst -name r529_0 -location {11222.880 8170.664} -status PLACED
place_inst -name b529 -location {11222.880 8095.600} -status PLACED
place_inst -name r530_0 -location {11237.880 8245.728} -status PLACED
place_inst -name r530_1 -location {11576.600 8245.728} -status PLACED
place_inst -name r530_2 -location {11592.120 8245.728} -status PLACED
place_inst -name b530 -location {11931.360 8245.728} -status PLACED
place_inst -name r531_0 -location {11931.360 8170.664} -status PLACED
place_inst -name b531 -location {11931.360 8095.600} -status PLACED
place_inst -name r532_0 -location {11946.360 8245.728} -status PLACED
place_inst -name r532_1 -location {12285.080 8245.728} -status PLACED
place_inst -name r532_2 -location {12300.600 8245.728} -status PLACED
place_inst -name b532 -location {12639.840 8245.728} -status PLACED
place_inst -name r533_0 -location {12639.840 8170.664} -status PLACED
place_inst -name b533 -location {12639.840 8095.600} -status PLACED
place_inst -name r534_0 -location {12654.840 8245.728} -status PLACED
place_inst -name r534_1 -location {12993.560 8245.728} -status PLACED
place_inst -name r534_2 -location {13009.080 8245.728} -status PLACED
place_inst -name b534 -location {13348.320 8245.728} -status PLACED
place_inst -name r535_0 -location {13348.320 8170.664} -status PLACED
place_inst -name b535 -location {13348.320 8095.600} -status PLACED
place_inst -name r536_0 -location {13363.320 8245.728} -status PLACED
place_inst -name r536_1 -location {13702.040 8245.728} -status PLACED
place_inst -name r536_2 -location {13717.560 8245.728} -status PLACED
place_inst -name b536 -location {14056.800 8245.728} -status PLACED
place_inst -name r537_0 -location {14056.800 8170.664} -status PLACED
place_inst -name b537 -location {14056.800 8095.600} -status PLACED
place_inst -name r538_0 -location {14071.800 8245.728} -status PLACED
place_inst -name r538_1 -location {14410.520 8245.728} -status PLACED
place_inst -name r538_2 -location {14426.040 8245.728} -status PLACED
place_inst -name b538 -location {14765.280 8245.728} -status PLACED
place_inst -name r539_0 -location {14765.280 8170.664} -status PLACED
place_inst -name b539 -location {14765.280 8095.600} -status PLACED
place_inst -name r540_0 -location {14780.280 8245.728} -status PLACED
place_inst -name r540_1 -location {15119.000 8245.728} -status PLACED
place_inst -name r540_2 -location {15134.520 8245.728} -status PLACED
place_inst -name b540 -location {15473.760 8245.728} -status PLACED
place_inst -name r541_0 -location {15473.760 8170.664} -status PLACED
place_inst -name b541 -location {15473.760 8095.600} -status PLACED
place_inst -name r542_0 -location {15488.760 8245.728} -status PLACED
place_inst -name r542_1 -location {15827.480 8245.728} -status PLACED
place_inst -name r542_2 -location {15843.000 8245.728} -status PLACED
place_inst -name b542 -location {16182.240 8245.728} -status PLACED
place_inst -name r543_0 -location {16182.240 8170.664} -status PLACED
place_inst -name b543 -location {16182.240 8095.600} -status PLACED
place_inst -name r544_0 -location {16197.240 8245.728} -status PLACED
place_inst -name r544_1 -location {16535.960 8245.728} -status PLACED
place_inst -name r544_2 -location {16551.480 8245.728} -status PLACED
place_inst -name b544 -location {16890.720 8245.728} -status PLACED
place_inst -name r545_0 -location {16890.720 8170.664} -status PLACED
place_inst -name b545 -location {16890.720 8095.600} -status PLACED
place_inst -name r546_0 -location {17230.920 8245.728} -status PLACED
place_inst -name b546 -location {17286.464 8245.728} -status PLACED
place_inst -name r547_0 -location {17286.464 8109.864} -status PLACED
place_inst -name b547 -location {17286.464 7974.000} -status PLACED
place_inst -name r548_0 -location {8590.064 9282.528} -status PLACED
place_inst -name b548 -location {8419.168 9282.528} -status PLACED
place_inst -name r549_0 -location {8253.344 9282.528} -status PLACED
place_inst -name b549 -location {8087.520 9282.528} -status PLACED
place_inst -name r550_0 -location {8055.240 9282.528} -status PLACED
place_inst -name b550 -location {7715.040 9282.528} -status PLACED
place_inst -name r551_0 -location {7715.040 9207.464} -status PLACED
place_inst -name b551 -location {7715.040 9132.400} -status PLACED
place_inst -name r552_0 -location {7375.800 9282.528} -status PLACED
place_inst -name r552_1 -location {7360.280 9282.528} -status PLACED
place_inst -name r552_2 -location {7021.560 9282.528} -status PLACED
place_inst -name b552 -location {7006.560 9282.528} -status PLACED
place_inst -name r553_0 -location {7006.560 9207.464} -status PLACED
place_inst -name b553 -location {7006.560 9132.400} -status PLACED
place_inst -name r554_0 -location {6667.320 9282.528} -status PLACED
place_inst -name r554_1 -location {6651.800 9282.528} -status PLACED
place_inst -name r554_2 -location {6313.080 9282.528} -status PLACED
place_inst -name b554 -location {6298.080 9282.528} -status PLACED
place_inst -name r555_0 -location {6298.080 9207.464} -status PLACED
place_inst -name b555 -location {6298.080 9132.400} -status PLACED
place_inst -name r556_0 -location {5958.840 9282.528} -status PLACED
place_inst -name r556_1 -location {5943.320 9282.528} -status PLACED
place_inst -name r556_2 -location {5604.600 9282.528} -status PLACED
place_inst -name b556 -location {5589.600 9282.528} -status PLACED
place_inst -name r557_0 -location {5589.600 9207.464} -status PLACED
place_inst -name b557 -location {5589.600 9132.400} -status PLACED
place_inst -name r558_0 -location {5250.360 9282.528} -status PLACED
place_inst -name r558_1 -location {5234.840 9282.528} -status PLACED
place_inst -name r558_2 -location {4896.120 9282.528} -status PLACED
place_inst -name b558 -location {4881.120 9282.528} -status PLACED
place_inst -name r559_0 -location {4881.120 9207.464} -status PLACED
place_inst -name b559 -location {4881.120 9132.400} -status PLACED
place_inst -name r560_0 -location {4541.880 9282.528} -status PLACED
place_inst -name r560_1 -location {4526.360 9282.528} -status PLACED
place_inst -name r560_2 -location {4187.640 9282.528} -status PLACED
place_inst -name b560 -location {4172.640 9282.528} -status PLACED
place_inst -name r561_0 -location {4172.640 9207.464} -status PLACED
place_inst -name b561 -location {4172.640 9132.400} -status PLACED
place_inst -name r562_0 -location {3833.400 9282.528} -status PLACED
place_inst -name r562_1 -location {3817.880 9282.528} -status PLACED
place_inst -name r562_2 -location {3479.160 9282.528} -status PLACED
place_inst -name b562 -location {3464.160 9282.528} -status PLACED
place_inst -name r563_0 -location {3464.160 9207.464} -status PLACED
place_inst -name b563 -location {3464.160 9132.400} -status PLACED
place_inst -name r564_0 -location {3124.920 9282.528} -status PLACED
place_inst -name r564_1 -location {3109.400 9282.528} -status PLACED
place_inst -name r564_2 -location {2770.680 9282.528} -status PLACED
place_inst -name b564 -location {2755.680 9282.528} -status PLACED
place_inst -name r565_0 -location {2755.680 9207.464} -status PLACED
place_inst -name b565 -location {2755.680 9132.400} -status PLACED
place_inst -name r566_0 -location {2416.440 9282.528} -status PLACED
place_inst -name r566_1 -location {2400.920 9282.528} -status PLACED
place_inst -name r566_2 -location {2062.200 9282.528} -status PLACED
place_inst -name b566 -location {2047.200 9282.528} -status PLACED
place_inst -name r567_0 -location {2047.200 9207.464} -status PLACED
place_inst -name b567 -location {2047.200 9132.400} -status PLACED
place_inst -name r568_0 -location {1707.960 9282.528} -status PLACED
place_inst -name r568_1 -location {1692.440 9282.528} -status PLACED
place_inst -name r568_2 -location {1353.720 9282.528} -status PLACED
place_inst -name b568 -location {1338.720 9282.528} -status PLACED
place_inst -name r569_0 -location {1338.720 9207.464} -status PLACED
place_inst -name b569 -location {1338.720 9132.400} -status PLACED
place_inst -name r570_0 -location {999.480 9282.528} -status PLACED
place_inst -name r570_1 -location {983.960 9282.528} -status PLACED
place_inst -name r570_2 -location {645.240 9282.528} -status PLACED
place_inst -name b570 -location {630.240 9282.528} -status PLACED
place_inst -name r571_0 -location {630.240 9207.464} -status PLACED
place_inst -name b571 -location {630.240 9132.400} -status PLACED
place_inst -name r572_0 -location {616.200 9282.528} -status PLACED
place_inst -name r572_1 -location {291.000 9282.528} -status PLACED
place_inst -name r572_2 -location {291.000 9282.528} -status PLACED
place_inst -name b572 -location {189.600 9282.528} -status PLACED
place_inst -name r573_0 -location {189.600 9393.964} -status PLACED
place_inst -name b573 -location {189.600 9505.400} -status PLACED
place_inst -name r574_0 -location {189.600 9411.321} -status PLACED
place_inst -name r574_1 -location {189.600 9540.114} -status PLACED
place_inst -name r574_2 -location {189.600 9668.907} -status PLACED
place_inst -name b574 -location {189.600 9797.700} -status PLACED
place_inst -name r575_0 -location {8760.960 9224.214} -status PLACED
place_inst -name b575 -location {8760.960 9165.900} -status PLACED
place_inst -name r576_0 -location {8821.125 9282.528} -status PLACED
place_inst -name b576 -location {8881.291 9282.528} -status PLACED
place_inst -name r577_0 -location {8881.291 9160.796} -status PLACED
place_inst -name r577_1 -location {8881.291 9039.064} -status PLACED
place_inst -name r577_2 -location {8881.291 8917.332} -status PLACED
place_inst -name b577 -location {8881.291 8795.600} -status PLACED
place_inst -name r578_0 -location {8881.291 9442.314} -status PLACED
place_inst -name b578 -location {8881.291 9602.100} -status PLACED
place_inst -name r579_0 -location {8935.901 9282.528} -status PLACED
place_inst -name b579 -location {8990.512 9282.528} -status PLACED
place_inst -name r580_0 -location {8990.512 9167.214} -status PLACED
place_inst -name b580 -location {8990.512 9051.900} -status PLACED
place_inst -name r581_0 -location {8990.512 9437.064} -status PLACED
place_inst -name b581 -location {8990.512 9591.600} -status PLACED
place_inst -name r582_0 -location {8990.512 9472.714} -status PLACED
place_inst -name b582 -location {8990.512 9662.900} -status PLACED
place_inst -name r583_0 -location {8999.816 9282.528} -status PLACED
place_inst -name b583 -location {9009.120 9282.528} -status PLACED
place_inst -name r584_0 -location {9049.696 9282.528} -status PLACED
place_inst -name b584 -location {9090.272 9282.528} -status PLACED
place_inst -name r585_0 -location {9090.272 9160.796} -status PLACED
place_inst -name r585_1 -location {9090.272 9039.064} -status PLACED
place_inst -name r585_2 -location {9090.272 8917.332} -status PLACED
place_inst -name b585 -location {9090.272 8795.600} -status PLACED
place_inst -name r586_0 -location {9142.080 9282.528} -status PLACED
place_inst -name b586 -location {9193.888 9282.528} -status PLACED
place_inst -name r587_0 -location {9193.888 9203.214} -status PLACED
place_inst -name b587 -location {9193.888 9123.900} -status PLACED
place_inst -name r588_0 -location {9193.888 9376.014} -status PLACED
place_inst -name b588 -location {9193.888 9469.500} -status PLACED
place_inst -name r589_0 -location {9267.104 9282.528} -status PLACED
place_inst -name b589 -location {9340.320 9282.528} -status PLACED
place_inst -name r590_0 -location {9387.360 9282.528} -status PLACED
place_inst -name b590 -location {9434.400 9282.528} -status PLACED
place_inst -name r591_0 -location {9466.680 9282.528} -status PLACED
place_inst -name b591 -location {9806.880 9282.528} -status PLACED
place_inst -name r592_0 -location {9806.880 9207.464} -status PLACED
place_inst -name b592 -location {9806.880 9132.400} -status PLACED
place_inst -name r593_0 -location {10146.120 9282.528} -status PLACED
place_inst -name r593_1 -location {10161.640 9282.528} -status PLACED
place_inst -name r593_2 -location {10500.360 9282.528} -status PLACED
place_inst -name b593 -location {10515.360 9282.528} -status PLACED
place_inst -name r594_0 -location {10515.360 9207.464} -status PLACED
place_inst -name b594 -location {10515.360 9132.400} -status PLACED
place_inst -name r595_0 -location {10854.600 9282.528} -status PLACED
place_inst -name r595_1 -location {10870.120 9282.528} -status PLACED
place_inst -name r595_2 -location {11208.840 9282.528} -status PLACED
place_inst -name b595 -location {11223.840 9282.528} -status PLACED
place_inst -name r596_0 -location {11223.840 9207.464} -status PLACED
place_inst -name b596 -location {11223.840 9132.400} -status PLACED
place_inst -name r597_0 -location {11563.080 9282.528} -status PLACED
place_inst -name r597_1 -location {11578.600 9282.528} -status PLACED
place_inst -name r597_2 -location {11917.320 9282.528} -status PLACED
place_inst -name b597 -location {11932.320 9282.528} -status PLACED
place_inst -name r598_0 -location {11932.320 9207.464} -status PLACED
place_inst -name b598 -location {11932.320 9132.400} -status PLACED
place_inst -name r599_0 -location {12271.560 9282.528} -status PLACED
place_inst -name r599_1 -location {12287.080 9282.528} -status PLACED
place_inst -name r599_2 -location {12625.800 9282.528} -status PLACED
place_inst -name b599 -location {12640.800 9282.528} -status PLACED
place_inst -name r600_0 -location {12640.800 9207.464} -status PLACED
place_inst -name b600 -location {12640.800 9132.400} -status PLACED
place_inst -name r601_0 -location {12980.040 9282.528} -status PLACED
place_inst -name r601_1 -location {12995.560 9282.528} -status PLACED
place_inst -name r601_2 -location {13334.280 9282.528} -status PLACED
place_inst -name b601 -location {13349.280 9282.528} -status PLACED
place_inst -name r602_0 -location {13349.280 9207.464} -status PLACED
place_inst -name b602 -location {13349.280 9132.400} -status PLACED
place_inst -name r603_0 -location {13688.520 9282.528} -status PLACED
place_inst -name r603_1 -location {13704.040 9282.528} -status PLACED
place_inst -name r603_2 -location {14042.760 9282.528} -status PLACED
place_inst -name b603 -location {14057.760 9282.528} -status PLACED
place_inst -name r604_0 -location {14057.760 9207.464} -status PLACED
place_inst -name b604 -location {14057.760 9132.400} -status PLACED
place_inst -name r605_0 -location {14397.000 9282.528} -status PLACED
place_inst -name r605_1 -location {14412.520 9282.528} -status PLACED
place_inst -name r605_2 -location {14751.240 9282.528} -status PLACED
place_inst -name b605 -location {14766.240 9282.528} -status PLACED
place_inst -name r606_0 -location {14766.240 9207.464} -status PLACED
place_inst -name b606 -location {14766.240 9132.400} -status PLACED
place_inst -name r607_0 -location {15105.480 9282.528} -status PLACED
place_inst -name r607_1 -location {15121.000 9282.528} -status PLACED
place_inst -name r607_2 -location {15459.720 9282.528} -status PLACED
place_inst -name b607 -location {15474.720 9282.528} -status PLACED
place_inst -name r608_0 -location {15474.720 9207.464} -status PLACED
place_inst -name b608 -location {15474.720 9132.400} -status PLACED
place_inst -name r609_0 -location {15813.960 9282.528} -status PLACED
place_inst -name r609_1 -location {15829.480 9282.528} -status PLACED
place_inst -name r609_2 -location {16168.200 9282.528} -status PLACED
place_inst -name b609 -location {16183.200 9282.528} -status PLACED
place_inst -name r610_0 -location {16183.200 9207.464} -status PLACED
place_inst -name b610 -location {16183.200 9132.400} -status PLACED
place_inst -name r611_0 -location {16522.440 9282.528} -status PLACED
place_inst -name r611_1 -location {16537.960 9282.528} -status PLACED
place_inst -name r611_2 -location {16876.680 9282.528} -status PLACED
place_inst -name b611 -location {16891.680 9282.528} -status PLACED
place_inst -name r612_0 -location {16891.680 9207.464} -status PLACED
place_inst -name b612 -location {16891.680 9132.400} -status PLACED
place_inst -name r613_0 -location {16905.720 9282.528} -status PLACED
place_inst -name r613_1 -location {17230.920 9282.528} -status PLACED
place_inst -name r613_2 -location {17230.920 9282.528} -status PLACED
place_inst -name b613 -location {17332.320 9282.528} -status PLACED
place_inst -name r614_0 -location {17332.320 9393.964} -status PLACED
place_inst -name b614 -location {17332.320 9505.400} -status PLACED
place_inst -name r615_0 -location {17332.320 9411.321} -status PLACED
place_inst -name r615_1 -location {17332.320 9540.114} -status PLACED
place_inst -name r615_2 -location {17332.320 9668.907} -status PLACED
place_inst -name b615 -location {17332.320 9797.700} -status PLACED
place_inst -name r616_0 -location {8590.576 10319.328} -status PLACED
place_inst -name b616 -location {8420.192 10319.328} -status PLACED
place_inst -name r617_0 -location {8244.144 10319.328} -status PLACED
place_inst -name r617_1 -location {8068.096 10319.328} -status PLACED
place_inst -name r617_2 -location {7730.040 10319.328} -status PLACED
place_inst -name b617 -location {7716.000 10319.328} -status PLACED
place_inst -name r618_0 -location {7716.000 10244.264} -status PLACED
place_inst -name b618 -location {7716.000 10169.200} -status PLACED
place_inst -name r619_0 -location {7701.000 10319.328} -status PLACED
place_inst -name r619_1 -location {7362.280 10319.328} -status PLACED
place_inst -name r619_2 -location {7346.760 10319.328} -status PLACED
place_inst -name b619 -location {7007.520 10319.328} -status PLACED
place_inst -name r620_0 -location {7007.520 10244.264} -status PLACED
place_inst -name b620 -location {7007.520 10169.200} -status PLACED
place_inst -name r621_0 -location {6992.520 10319.328} -status PLACED
place_inst -name r621_1 -location {6653.800 10319.328} -status PLACED
place_inst -name r621_2 -location {6638.280 10319.328} -status PLACED
place_inst -name b621 -location {6299.040 10319.328} -status PLACED
place_inst -name r622_0 -location {6299.040 10244.264} -status PLACED
place_inst -name b622 -location {6299.040 10169.200} -status PLACED
place_inst -name r623_0 -location {6284.040 10319.328} -status PLACED
place_inst -name r623_1 -location {5945.320 10319.328} -status PLACED
place_inst -name r623_2 -location {5929.800 10319.328} -status PLACED
place_inst -name b623 -location {5590.560 10319.328} -status PLACED
place_inst -name r624_0 -location {5590.560 10244.264} -status PLACED
place_inst -name b624 -location {5590.560 10169.200} -status PLACED
place_inst -name r625_0 -location {5575.560 10319.328} -status PLACED
place_inst -name r625_1 -location {5236.840 10319.328} -status PLACED
place_inst -name r625_2 -location {5221.320 10319.328} -status PLACED
place_inst -name b625 -location {4882.080 10319.328} -status PLACED
place_inst -name r626_0 -location {4882.080 10244.264} -status PLACED
place_inst -name b626 -location {4882.080 10169.200} -status PLACED
place_inst -name r627_0 -location {4867.080 10319.328} -status PLACED
place_inst -name r627_1 -location {4528.360 10319.328} -status PLACED
place_inst -name r627_2 -location {4512.840 10319.328} -status PLACED
place_inst -name b627 -location {4173.600 10319.328} -status PLACED
place_inst -name r628_0 -location {4173.600 10244.264} -status PLACED
place_inst -name b628 -location {4173.600 10169.200} -status PLACED
place_inst -name r629_0 -location {4158.600 10319.328} -status PLACED
place_inst -name r629_1 -location {3819.880 10319.328} -status PLACED
place_inst -name r629_2 -location {3804.360 10319.328} -status PLACED
place_inst -name b629 -location {3465.120 10319.328} -status PLACED
place_inst -name r630_0 -location {3465.120 10244.264} -status PLACED
place_inst -name b630 -location {3465.120 10169.200} -status PLACED
place_inst -name r631_0 -location {3450.120 10319.328} -status PLACED
place_inst -name r631_1 -location {3111.400 10319.328} -status PLACED
place_inst -name r631_2 -location {3095.880 10319.328} -status PLACED
place_inst -name b631 -location {2756.640 10319.328} -status PLACED
place_inst -name r632_0 -location {2756.640 10244.264} -status PLACED
place_inst -name b632 -location {2756.640 10169.200} -status PLACED
place_inst -name r633_0 -location {2741.640 10319.328} -status PLACED
place_inst -name r633_1 -location {2402.920 10319.328} -status PLACED
place_inst -name r633_2 -location {2387.400 10319.328} -status PLACED
place_inst -name b633 -location {2048.160 10319.328} -status PLACED
place_inst -name r634_0 -location {2048.160 10244.264} -status PLACED
place_inst -name b634 -location {2048.160 10169.200} -status PLACED
place_inst -name r635_0 -location {2033.160 10319.328} -status PLACED
place_inst -name r635_1 -location {1694.440 10319.328} -status PLACED
place_inst -name r635_2 -location {1678.920 10319.328} -status PLACED
place_inst -name b635 -location {1339.680 10319.328} -status PLACED
place_inst -name r636_0 -location {1339.680 10244.264} -status PLACED
place_inst -name b636 -location {1339.680 10169.200} -status PLACED
place_inst -name r637_0 -location {1324.680 10319.328} -status PLACED
place_inst -name r637_1 -location {985.960 10319.328} -status PLACED
place_inst -name r637_2 -location {970.440 10319.328} -status PLACED
place_inst -name b637 -location {631.200 10319.328} -status PLACED
place_inst -name r638_0 -location {631.200 10244.264} -status PLACED
place_inst -name b638 -location {631.200 10169.200} -status PLACED
place_inst -name r639_0 -location {291.000 10319.328} -status PLACED
place_inst -name b639 -location {235.456 10319.328} -status PLACED
place_inst -name r640_0 -location {235.456 10183.464} -status PLACED
place_inst -name b640 -location {235.456 10047.600} -status PLACED
place_inst -name r641_0 -location {8760.960 10279.064} -status PLACED
place_inst -name b641 -location {8760.960 10238.800} -status PLACED
place_inst -name r642_0 -location {8809.200 10319.328} -status PLACED
place_inst -name b642 -location {8857.440 10319.328} -status PLACED
place_inst -name r643_0 -location {8857.440 10208.196} -status PLACED
place_inst -name r643_1 -location {8857.440 10097.064} -status PLACED
place_inst -name r643_2 -location {8857.440 9985.932} -status PLACED
place_inst -name b643 -location {8857.440 9874.800} -status PLACED
place_inst -name r644_0 -location {8857.440 10233.464} -status PLACED
place_inst -name b644 -location {8857.440 10147.600} -status PLACED
place_inst -name r645_0 -location {8857.440 10363.914} -status PLACED
place_inst -name b645 -location {8857.440 10408.500} -status PLACED
place_inst -name r646_0 -location {8857.440 10385.064} -status PLACED
place_inst -name b646 -location {8857.440 10450.800} -status PLACED
place_inst -name r647_0 -location {8888.352 10319.328} -status PLACED
place_inst -name b647 -location {8919.264 10319.328} -status PLACED
place_inst -name r648_0 -location {8919.264 10448.146} -status PLACED
place_inst -name r648_1 -location {8919.264 10576.964} -status PLACED
place_inst -name r648_2 -location {8919.264 10705.782} -status PLACED
place_inst -name b648 -location {8919.264 10834.600} -status PLACED
place_inst -name r649_0 -location {8962.272 10319.328} -status PLACED
place_inst -name b649 -location {9005.280 10319.328} -status PLACED
place_inst -name r650_0 -location {9005.280 10207.271} -status PLACED
place_inst -name r650_1 -location {9005.280 10095.214} -status PLACED
place_inst -name r650_2 -location {9005.280 9983.157} -status PLACED
place_inst -name b650 -location {9005.280 9871.100} -status PLACED
place_inst -name r651_0 -location {9005.280 10145.414} -status PLACED
place_inst -name b651 -location {9005.280 9971.500} -status PLACED
place_inst -name r652_0 -location {9005.280 10229.364} -status PLACED
place_inst -name b652 -location {9005.280 10139.400} -status PLACED
place_inst -name r653_0 -location {9005.280 10361.014} -status PLACED
place_inst -name b653 -location {9005.280 10402.700} -status PLACED
place_inst -name r654_0 -location {9050.613 10319.328} -status PLACED
place_inst -name b654 -location {9095.947 10319.328} -status PLACED
place_inst -name r655_0 -location {9095.947 10240.014} -status PLACED
place_inst -name b655 -location {9095.947 10160.700} -status PLACED
place_inst -name r656_0 -location {9095.947 10385.064} -status PLACED
place_inst -name b656 -location {9095.947 10450.800} -status PLACED
place_inst -name r657_0 -location {9150.827 10319.328} -status PLACED
place_inst -name b657 -location {9205.707 10319.328} -status PLACED
place_inst -name r658_0 -location {9205.707 10193.271} -status PLACED
place_inst -name r658_1 -location {9205.707 10067.214} -status PLACED
place_inst -name r658_2 -location {9205.707 9941.157} -status PLACED
place_inst -name b658 -location {9205.707 9815.100} -status PLACED
place_inst -name r659_0 -location {9205.707 10412.814} -status PLACED
place_inst -name b659 -location {9205.707 10506.300} -status PLACED
place_inst -name r660_0 -location {9205.707 10448.146} -status PLACED
place_inst -name r660_1 -location {9205.707 10576.964} -status PLACED
place_inst -name r660_2 -location {9205.707 10705.782} -status PLACED
place_inst -name b660 -location {9205.707 10834.600} -status PLACED
place_inst -name r661_0 -location {9234.613 10319.328} -status PLACED
place_inst -name b661 -location {9263.520 10319.328} -status PLACED
place_inst -name r662_0 -location {9263.520 10240.014} -status PLACED
place_inst -name b662 -location {9263.520 10160.700} -status PLACED
place_inst -name r663_0 -location {9310.020 10319.328} -status PLACED
place_inst -name b663 -location {9356.519 10319.328} -status PLACED
place_inst -name r664_0 -location {9466.680 10319.328} -status PLACED
place_inst -name r664_1 -location {9466.680 10319.328} -status PLACED
place_inst -name r664_2 -location {9791.880 10319.328} -status PLACED
place_inst -name b664 -location {9805.920 10319.328} -status PLACED
place_inst -name r665_0 -location {9805.920 10244.264} -status PLACED
place_inst -name b665 -location {9805.920 10169.200} -status PLACED
place_inst -name r666_0 -location {9820.920 10319.328} -status PLACED
place_inst -name r666_1 -location {10159.640 10319.328} -status PLACED
place_inst -name r666_2 -location {10175.160 10319.328} -status PLACED
place_inst -name b666 -location {10514.400 10319.328} -status PLACED
place_inst -name r667_0 -location {10514.400 10244.264} -status PLACED
place_inst -name b667 -location {10514.400 10169.200} -status PLACED
place_inst -name r668_0 -location {10529.400 10319.328} -status PLACED
place_inst -name r668_1 -location {10868.120 10319.328} -status PLACED
place_inst -name r668_2 -location {10883.640 10319.328} -status PLACED
place_inst -name b668 -location {11222.880 10319.328} -status PLACED
place_inst -name r669_0 -location {11222.880 10244.264} -status PLACED
place_inst -name b669 -location {11222.880 10169.200} -status PLACED
place_inst -name r670_0 -location {11237.880 10319.328} -status PLACED
place_inst -name r670_1 -location {11576.600 10319.328} -status PLACED
place_inst -name r670_2 -location {11592.120 10319.328} -status PLACED
place_inst -name b670 -location {11931.360 10319.328} -status PLACED
place_inst -name r671_0 -location {11931.360 10244.264} -status PLACED
place_inst -name b671 -location {11931.360 10169.200} -status PLACED
place_inst -name r672_0 -location {11946.360 10319.328} -status PLACED
place_inst -name r672_1 -location {12285.080 10319.328} -status PLACED
place_inst -name r672_2 -location {12300.600 10319.328} -status PLACED
place_inst -name b672 -location {12639.840 10319.328} -status PLACED
place_inst -name r673_0 -location {12639.840 10244.264} -status PLACED
place_inst -name b673 -location {12639.840 10169.200} -status PLACED
place_inst -name r674_0 -location {12654.840 10319.328} -status PLACED
place_inst -name r674_1 -location {12993.560 10319.328} -status PLACED
place_inst -name r674_2 -location {13009.080 10319.328} -status PLACED
place_inst -name b674 -location {13348.320 10319.328} -status PLACED
place_inst -name r675_0 -location {13348.320 10244.264} -status PLACED
place_inst -name b675 -location {13348.320 10169.200} -status PLACED
place_inst -name r676_0 -location {13363.320 10319.328} -status PLACED
place_inst -name r676_1 -location {13702.040 10319.328} -status PLACED
place_inst -name r676_2 -location {13717.560 10319.328} -status PLACED
place_inst -name b676 -location {14056.800 10319.328} -status PLACED
place_inst -name r677_0 -location {14056.800 10244.264} -status PLACED
place_inst -name b677 -location {14056.800 10169.200} -status PLACED
place_inst -name r678_0 -location {14071.800 10319.328} -status PLACED
place_inst -name r678_1 -location {14410.520 10319.328} -status PLACED
place_inst -name r678_2 -location {14426.040 10319.328} -status PLACED
place_inst -name b678 -location {14765.280 10319.328} -status PLACED
place_inst -name r679_0 -location {14765.280 10244.264} -status PLACED
place_inst -name b679 -location {14765.280 10169.200} -status PLACED
place_inst -name r680_0 -location {14780.280 10319.328} -status PLACED
place_inst -name r680_1 -location {15119.000 10319.328} -status PLACED
place_inst -name r680_2 -location {15134.520 10319.328} -status PLACED
place_inst -name b680 -location {15473.760 10319.328} -status PLACED
place_inst -name r681_0 -location {15473.760 10244.264} -status PLACED
place_inst -name b681 -location {15473.760 10169.200} -status PLACED
place_inst -name r682_0 -location {15488.760 10319.328} -status PLACED
place_inst -name r682_1 -location {15827.480 10319.328} -status PLACED
place_inst -name r682_2 -location {15843.000 10319.328} -status PLACED
place_inst -name b682 -location {16182.240 10319.328} -status PLACED
place_inst -name r683_0 -location {16182.240 10244.264} -status PLACED
place_inst -name b683 -location {16182.240 10169.200} -status PLACED
place_inst -name r684_0 -location {16197.240 10319.328} -status PLACED
place_inst -name r684_1 -location {16535.960 10319.328} -status PLACED
place_inst -name r684_2 -location {16551.480 10319.328} -status PLACED
place_inst -name b684 -location {16890.720 10319.328} -status PLACED
place_inst -name r685_0 -location {16890.720 10244.264} -status PLACED
place_inst -name b685 -location {16890.720 10169.200} -status PLACED
place_inst -name r686_0 -location {17230.920 10319.328} -status PLACED
place_inst -name b686 -location {17286.464 10319.328} -status PLACED
place_inst -name r687_0 -location {17286.464 10183.464} -status PLACED
place_inst -name b687 -location {17286.464 10047.600} -status PLACED
place_inst -name r688_0 -location {8590.064 11356.128} -status PLACED
place_inst -name b688 -location {8419.168 11356.128} -status PLACED
place_inst -name r689_0 -location {8253.344 11356.128} -status PLACED
place_inst -name b689 -location {8087.520 11356.128} -status PLACED
place_inst -name r690_0 -location {8055.240 11356.128} -status PLACED
place_inst -name b690 -location {7715.040 11356.128} -status PLACED
place_inst -name r691_0 -location {7715.040 11281.064} -status PLACED
place_inst -name b691 -location {7715.040 11206.000} -status PLACED
place_inst -name r692_0 -location {7375.800 11356.128} -status PLACED
place_inst -name r692_1 -location {7360.280 11356.128} -status PLACED
place_inst -name r692_2 -location {7021.560 11356.128} -status PLACED
place_inst -name b692 -location {7006.560 11356.128} -status PLACED
place_inst -name r693_0 -location {7006.560 11281.064} -status PLACED
place_inst -name b693 -location {7006.560 11206.000} -status PLACED
place_inst -name r694_0 -location {6667.320 11356.128} -status PLACED
place_inst -name r694_1 -location {6651.800 11356.128} -status PLACED
place_inst -name r694_2 -location {6313.080 11356.128} -status PLACED
place_inst -name b694 -location {6298.080 11356.128} -status PLACED
place_inst -name r695_0 -location {6298.080 11281.064} -status PLACED
place_inst -name b695 -location {6298.080 11206.000} -status PLACED
place_inst -name r696_0 -location {5958.840 11356.128} -status PLACED
place_inst -name r696_1 -location {5943.320 11356.128} -status PLACED
place_inst -name r696_2 -location {5604.600 11356.128} -status PLACED
place_inst -name b696 -location {5589.600 11356.128} -status PLACED
place_inst -name r697_0 -location {5589.600 11281.064} -status PLACED
place_inst -name b697 -location {5589.600 11206.000} -status PLACED
place_inst -name r698_0 -location {5250.360 11356.128} -status PLACED
place_inst -name r698_1 -location {5234.840 11356.128} -status PLACED
place_inst -name r698_2 -location {4896.120 11356.128} -status PLACED
place_inst -name b698 -location {4881.120 11356.128} -status PLACED
place_inst -name r699_0 -location {4881.120 11281.064} -status PLACED
place_inst -name b699 -location {4881.120 11206.000} -status PLACED
place_inst -name r700_0 -location {4541.880 11356.128} -status PLACED
place_inst -name r700_1 -location {4526.360 11356.128} -status PLACED
place_inst -name r700_2 -location {4187.640 11356.128} -status PLACED
place_inst -name b700 -location {4172.640 11356.128} -status PLACED
place_inst -name r701_0 -location {4172.640 11281.064} -status PLACED
place_inst -name b701 -location {4172.640 11206.000} -status PLACED
place_inst -name r702_0 -location {3833.400 11356.128} -status PLACED
place_inst -name r702_1 -location {3817.880 11356.128} -status PLACED
place_inst -name r702_2 -location {3479.160 11356.128} -status PLACED
place_inst -name b702 -location {3464.160 11356.128} -status PLACED
place_inst -name r703_0 -location {3464.160 11281.064} -status PLACED
place_inst -name b703 -location {3464.160 11206.000} -status PLACED
place_inst -name r704_0 -location {3124.920 11356.128} -status PLACED
place_inst -name r704_1 -location {3109.400 11356.128} -status PLACED
place_inst -name r704_2 -location {2770.680 11356.128} -status PLACED
place_inst -name b704 -location {2755.680 11356.128} -status PLACED
place_inst -name r705_0 -location {2755.680 11281.064} -status PLACED
place_inst -name b705 -location {2755.680 11206.000} -status PLACED
place_inst -name r706_0 -location {2416.440 11356.128} -status PLACED
place_inst -name r706_1 -location {2400.920 11356.128} -status PLACED
place_inst -name r706_2 -location {2062.200 11356.128} -status PLACED
place_inst -name b706 -location {2047.200 11356.128} -status PLACED
place_inst -name r707_0 -location {2047.200 11281.064} -status PLACED
place_inst -name b707 -location {2047.200 11206.000} -status PLACED
place_inst -name r708_0 -location {1707.960 11356.128} -status PLACED
place_inst -name r708_1 -location {1692.440 11356.128} -status PLACED
place_inst -name r708_2 -location {1353.720 11356.128} -status PLACED
place_inst -name b708 -location {1338.720 11356.128} -status PLACED
place_inst -name r709_0 -location {1338.720 11281.064} -status PLACED
place_inst -name b709 -location {1338.720 11206.000} -status PLACED
place_inst -name r710_0 -location {999.480 11356.128} -status PLACED
place_inst -name r710_1 -location {983.960 11356.128} -status PLACED
place_inst -name r710_2 -location {645.240 11356.128} -status PLACED
place_inst -name b710 -location {630.240 11356.128} -status PLACED
place_inst -name r711_0 -location {630.240 11281.064} -status PLACED
place_inst -name b711 -location {630.240 11206.000} -status PLACED
place_inst -name r712_0 -location {616.200 11356.128} -status PLACED
place_inst -name r712_1 -location {291.000 11356.128} -status PLACED
place_inst -name r712_2 -location {291.000 11356.128} -status PLACED
place_inst -name b712 -location {189.600 11356.128} -status PLACED
place_inst -name r713_0 -location {189.600 11467.564} -status PLACED
place_inst -name b713 -location {189.600 11579.000} -status PLACED
place_inst -name r714_0 -location {189.600 11484.921} -status PLACED
place_inst -name r714_1 -location {189.600 11613.714} -status PLACED
place_inst -name r714_2 -location {189.600 11742.507} -status PLACED
place_inst -name b714 -location {189.600 11871.300} -status PLACED
place_inst -name r715_0 -location {8760.960 11297.814} -status PLACED
place_inst -name b715 -location {8760.960 11239.500} -status PLACED
place_inst -name r716_0 -location {8821.125 11356.128} -status PLACED
place_inst -name b716 -location {8881.291 11356.128} -status PLACED
place_inst -name r717_0 -location {8881.291 11234.396} -status PLACED
place_inst -name r717_1 -location {8881.291 11112.664} -status PLACED
place_inst -name r717_2 -location {8881.291 10990.932} -status PLACED
place_inst -name b717 -location {8881.291 10869.200} -status PLACED
place_inst -name r718_0 -location {8881.291 11515.914} -status PLACED
place_inst -name b718 -location {8881.291 11675.700} -status PLACED
place_inst -name r719_0 -location {8935.901 11356.128} -status PLACED
place_inst -name b719 -location {8990.512 11356.128} -status PLACED
place_inst -name r720_0 -location {8990.512 11240.814} -status PLACED
place_inst -name b720 -location {8990.512 11125.500} -status PLACED
place_inst -name r721_0 -location {8990.512 11510.664} -status PLACED
place_inst -name b721 -location {8990.512 11665.200} -status PLACED
place_inst -name r722_0 -location {8990.512 11546.314} -status PLACED
place_inst -name b722 -location {8990.512 11736.500} -status PLACED
place_inst -name r723_0 -location {8999.816 11356.128} -status PLACED
place_inst -name b723 -location {9009.120 11356.128} -status PLACED
place_inst -name r724_0 -location {9049.696 11356.128} -status PLACED
place_inst -name b724 -location {9090.272 11356.128} -status PLACED
place_inst -name r725_0 -location {9090.272 11234.396} -status PLACED
place_inst -name r725_1 -location {9090.272 11112.664} -status PLACED
place_inst -name r725_2 -location {9090.272 10990.932} -status PLACED
place_inst -name b725 -location {9090.272 10869.200} -status PLACED
place_inst -name r726_0 -location {9142.080 11356.128} -status PLACED
place_inst -name b726 -location {9193.888 11356.128} -status PLACED
place_inst -name r727_0 -location {9193.888 11276.814} -status PLACED
place_inst -name b727 -location {9193.888 11197.500} -status PLACED
place_inst -name r728_0 -location {9193.888 11449.614} -status PLACED
place_inst -name b728 -location {9193.888 11543.100} -status PLACED
place_inst -name r729_0 -location {9267.104 11356.128} -status PLACED
place_inst -name b729 -location {9340.320 11356.128} -status PLACED
place_inst -name r730_0 -location {9387.360 11356.128} -status PLACED
place_inst -name b730 -location {9434.400 11356.128} -status PLACED
place_inst -name r731_0 -location {9466.680 11356.128} -status PLACED
place_inst -name b731 -location {9806.880 11356.128} -status PLACED
place_inst -name r732_0 -location {9806.880 11281.064} -status PLACED
place_inst -name b732 -location {9806.880 11206.000} -status PLACED
place_inst -name r733_0 -location {10146.120 11356.128} -status PLACED
place_inst -name r733_1 -location {10161.640 11356.128} -status PLACED
place_inst -name r733_2 -location {10500.360 11356.128} -status PLACED
place_inst -name b733 -location {10515.360 11356.128} -status PLACED
place_inst -name r734_0 -location {10515.360 11281.064} -status PLACED
place_inst -name b734 -location {10515.360 11206.000} -status PLACED
place_inst -name r735_0 -location {10854.600 11356.128} -status PLACED
place_inst -name r735_1 -location {10870.120 11356.128} -status PLACED
place_inst -name r735_2 -location {11208.840 11356.128} -status PLACED
place_inst -name b735 -location {11223.840 11356.128} -status PLACED
place_inst -name r736_0 -location {11223.840 11281.064} -status PLACED
place_inst -name b736 -location {11223.840 11206.000} -status PLACED
place_inst -name r737_0 -location {11563.080 11356.128} -status PLACED
place_inst -name r737_1 -location {11578.600 11356.128} -status PLACED
place_inst -name r737_2 -location {11917.320 11356.128} -status PLACED
place_inst -name b737 -location {11932.320 11356.128} -status PLACED
place_inst -name r738_0 -location {11932.320 11281.064} -status PLACED
place_inst -name b738 -location {11932.320 11206.000} -status PLACED
place_inst -name r739_0 -location {12271.560 11356.128} -status PLACED
place_inst -name r739_1 -location {12287.080 11356.128} -status PLACED
place_inst -name r739_2 -location {12625.800 11356.128} -status PLACED
place_inst -name b739 -location {12640.800 11356.128} -status PLACED
place_inst -name r740_0 -location {12640.800 11281.064} -status PLACED
place_inst -name b740 -location {12640.800 11206.000} -status PLACED
place_inst -name r741_0 -location {12980.040 11356.128} -status PLACED
place_inst -name r741_1 -location {12995.560 11356.128} -status PLACED
place_inst -name r741_2 -location {13334.280 11356.128} -status PLACED
place_inst -name b741 -location {13349.280 11356.128} -status PLACED
place_inst -name r742_0 -location {13349.280 11281.064} -status PLACED
place_inst -name b742 -location {13349.280 11206.000} -status PLACED
place_inst -name r743_0 -location {13688.520 11356.128} -status PLACED
place_inst -name r743_1 -location {13704.040 11356.128} -status PLACED
place_inst -name r743_2 -location {14042.760 11356.128} -status PLACED
place_inst -name b743 -location {14057.760 11356.128} -status PLACED
place_inst -name r744_0 -location {14057.760 11281.064} -status PLACED
place_inst -name b744 -location {14057.760 11206.000} -status PLACED
place_inst -name r745_0 -location {14397.000 11356.128} -status PLACED
place_inst -name r745_1 -location {14412.520 11356.128} -status PLACED
place_inst -name r745_2 -location {14751.240 11356.128} -status PLACED
place_inst -name b745 -location {14766.240 11356.128} -status PLACED
place_inst -name r746_0 -location {14766.240 11281.064} -status PLACED
place_inst -name b746 -location {14766.240 11206.000} -status PLACED
place_inst -name r747_0 -location {15105.480 11356.128} -status PLACED
place_inst -name r747_1 -location {15121.000 11356.128} -status PLACED
place_inst -name r747_2 -location {15459.720 11356.128} -status PLACED
place_inst -name b747 -location {15474.720 11356.128} -status PLACED
place_inst -name r748_0 -location {15474.720 11281.064} -status PLACED
place_inst -name b748 -location {15474.720 11206.000} -status PLACED
place_inst -name r749_0 -location {15813.960 11356.128} -status PLACED
place_inst -name r749_1 -location {15829.480 11356.128} -status PLACED
place_inst -name r749_2 -location {16168.200 11356.128} -status PLACED
place_inst -name b749 -location {16183.200 11356.128} -status PLACED
place_inst -name r750_0 -location {16183.200 11281.064} -status PLACED
place_inst -name b750 -location {16183.200 11206.000} -status PLACED
place_inst -name r751_0 -location {16522.440 11356.128} -status PLACED
place_inst -name r751_1 -location {16537.960 11356.128} -status PLACED
place_inst -name r751_2 -location {16876.680 11356.128} -status PLACED
place_inst -name b751 -location {16891.680 11356.128} -status PLACED
place_inst -name r752_0 -location {16891.680 11281.064} -status PLACED
place_inst -name b752 -location {16891.680 11206.000} -status PLACED
place_inst -name r753_0 -location {16905.720 11356.128} -status PLACED
place_inst -name r753_1 -location {17230.920 11356.128} -status PLACED
place_inst -name r753_2 -location {17230.920 11356.128} -status PLACED
place_inst -name b753 -location {17332.320 11356.128} -status PLACED
place_inst -name r754_0 -location {17332.320 11467.564} -status PLACED
place_inst -name b754 -location {17332.320 11579.000} -status PLACED
place_inst -name r755_0 -location {17332.320 11484.921} -status PLACED
place_inst -name r755_1 -location {17332.320 11613.714} -status PLACED
place_inst -name r755_2 -location {17332.320 11742.507} -status PLACED
place_inst -name b755 -location {17332.320 11871.300} -status PLACED
place_inst -name r756_0 -location {8590.576 12392.928} -status PLACED
place_inst -name b756 -location {8420.192 12392.928} -status PLACED
place_inst -name r757_0 -location {8244.144 12392.928} -status PLACED
place_inst -name r757_1 -location {8068.096 12392.928} -status PLACED
place_inst -name r757_2 -location {7730.040 12392.928} -status PLACED
place_inst -name b757 -location {7716.000 12392.928} -status PLACED
place_inst -name r758_0 -location {7716.000 12317.864} -status PLACED
place_inst -name b758 -location {7716.000 12242.800} -status PLACED
place_inst -name r759_0 -location {7701.000 12392.928} -status PLACED
place_inst -name r759_1 -location {7362.280 12392.928} -status PLACED
place_inst -name r759_2 -location {7346.760 12392.928} -status PLACED
place_inst -name b759 -location {7007.520 12392.928} -status PLACED
place_inst -name r760_0 -location {7007.520 12317.864} -status PLACED
place_inst -name b760 -location {7007.520 12242.800} -status PLACED
place_inst -name r761_0 -location {6992.520 12392.928} -status PLACED
place_inst -name r761_1 -location {6653.800 12392.928} -status PLACED
place_inst -name r761_2 -location {6638.280 12392.928} -status PLACED
place_inst -name b761 -location {6299.040 12392.928} -status PLACED
place_inst -name r762_0 -location {6299.040 12317.864} -status PLACED
place_inst -name b762 -location {6299.040 12242.800} -status PLACED
place_inst -name r763_0 -location {6284.040 12392.928} -status PLACED
place_inst -name r763_1 -location {5945.320 12392.928} -status PLACED
place_inst -name r763_2 -location {5929.800 12392.928} -status PLACED
place_inst -name b763 -location {5590.560 12392.928} -status PLACED
place_inst -name r764_0 -location {5590.560 12317.864} -status PLACED
place_inst -name b764 -location {5590.560 12242.800} -status PLACED
place_inst -name r765_0 -location {5575.560 12392.928} -status PLACED
place_inst -name r765_1 -location {5236.840 12392.928} -status PLACED
place_inst -name r765_2 -location {5221.320 12392.928} -status PLACED
place_inst -name b765 -location {4882.080 12392.928} -status PLACED
place_inst -name r766_0 -location {4882.080 12317.864} -status PLACED
place_inst -name b766 -location {4882.080 12242.800} -status PLACED
place_inst -name r767_0 -location {4867.080 12392.928} -status PLACED
place_inst -name r767_1 -location {4528.360 12392.928} -status PLACED
place_inst -name r767_2 -location {4512.840 12392.928} -status PLACED
place_inst -name b767 -location {4173.600 12392.928} -status PLACED
place_inst -name r768_0 -location {4173.600 12317.864} -status PLACED
place_inst -name b768 -location {4173.600 12242.800} -status PLACED
place_inst -name r769_0 -location {4158.600 12392.928} -status PLACED
place_inst -name r769_1 -location {3819.880 12392.928} -status PLACED
place_inst -name r769_2 -location {3804.360 12392.928} -status PLACED
place_inst -name b769 -location {3465.120 12392.928} -status PLACED
place_inst -name r770_0 -location {3465.120 12317.864} -status PLACED
place_inst -name b770 -location {3465.120 12242.800} -status PLACED
place_inst -name r771_0 -location {3450.120 12392.928} -status PLACED
place_inst -name r771_1 -location {3111.400 12392.928} -status PLACED
place_inst -name r771_2 -location {3095.880 12392.928} -status PLACED
place_inst -name b771 -location {2756.640 12392.928} -status PLACED
place_inst -name r772_0 -location {2756.640 12317.864} -status PLACED
place_inst -name b772 -location {2756.640 12242.800} -status PLACED
place_inst -name r773_0 -location {2741.640 12392.928} -status PLACED
place_inst -name r773_1 -location {2402.920 12392.928} -status PLACED
place_inst -name r773_2 -location {2387.400 12392.928} -status PLACED
place_inst -name b773 -location {2048.160 12392.928} -status PLACED
place_inst -name r774_0 -location {2048.160 12317.864} -status PLACED
place_inst -name b774 -location {2048.160 12242.800} -status PLACED
place_inst -name r775_0 -location {2033.160 12392.928} -status PLACED
place_inst -name r775_1 -location {1694.440 12392.928} -status PLACED
place_inst -name r775_2 -location {1678.920 12392.928} -status PLACED
place_inst -name b775 -location {1339.680 12392.928} -status PLACED
place_inst -name r776_0 -location {1339.680 12317.864} -status PLACED
place_inst -name b776 -location {1339.680 12242.800} -status PLACED
place_inst -name r777_0 -location {1324.680 12392.928} -status PLACED
place_inst -name r777_1 -location {985.960 12392.928} -status PLACED
place_inst -name r777_2 -location {970.440 12392.928} -status PLACED
place_inst -name b777 -location {631.200 12392.928} -status PLACED
place_inst -name r778_0 -location {631.200 12317.864} -status PLACED
place_inst -name b778 -location {631.200 12242.800} -status PLACED
place_inst -name r779_0 -location {291.000 12392.928} -status PLACED
place_inst -name b779 -location {235.456 12392.928} -status PLACED
place_inst -name r780_0 -location {235.456 12257.064} -status PLACED
place_inst -name b780 -location {235.456 12121.200} -status PLACED
place_inst -name r781_0 -location {8760.960 12352.664} -status PLACED
place_inst -name b781 -location {8760.960 12312.400} -status PLACED
place_inst -name r782_0 -location {8809.200 12392.928} -status PLACED
place_inst -name b782 -location {8857.440 12392.928} -status PLACED
place_inst -name r783_0 -location {8857.440 12281.796} -status PLACED
place_inst -name r783_1 -location {8857.440 12170.664} -status PLACED
place_inst -name r783_2 -location {8857.440 12059.532} -status PLACED
place_inst -name b783 -location {8857.440 11948.400} -status PLACED
place_inst -name r784_0 -location {8857.440 12307.064} -status PLACED
place_inst -name b784 -location {8857.440 12221.200} -status PLACED
place_inst -name r785_0 -location {8857.440 12437.514} -status PLACED
place_inst -name b785 -location {8857.440 12482.100} -status PLACED
place_inst -name r786_0 -location {8857.440 12458.664} -status PLACED
place_inst -name b786 -location {8857.440 12524.400} -status PLACED
place_inst -name r787_0 -location {8888.352 12392.928} -status PLACED
place_inst -name b787 -location {8919.264 12392.928} -status PLACED
place_inst -name r788_0 -location {8919.264 12521.746} -status PLACED
place_inst -name r788_1 -location {8919.264 12650.564} -status PLACED
place_inst -name r788_2 -location {8919.264 12779.382} -status PLACED
place_inst -name b788 -location {8919.264 12908.200} -status PLACED
place_inst -name r789_0 -location {8962.272 12392.928} -status PLACED
place_inst -name b789 -location {9005.280 12392.928} -status PLACED
place_inst -name r790_0 -location {9005.280 12280.871} -status PLACED
place_inst -name r790_1 -location {9005.280 12168.814} -status PLACED
place_inst -name r790_2 -location {9005.280 12056.757} -status PLACED
place_inst -name b790 -location {9005.280 11944.700} -status PLACED
place_inst -name r791_0 -location {9005.280 12219.014} -status PLACED
place_inst -name b791 -location {9005.280 12045.100} -status PLACED
place_inst -name r792_0 -location {9005.280 12302.964} -status PLACED
place_inst -name b792 -location {9005.280 12213.000} -status PLACED
place_inst -name r793_0 -location {9005.280 12434.614} -status PLACED
place_inst -name b793 -location {9005.280 12476.300} -status PLACED
place_inst -name r794_0 -location {9050.613 12392.928} -status PLACED
place_inst -name b794 -location {9095.947 12392.928} -status PLACED
place_inst -name r795_0 -location {9095.947 12313.614} -status PLACED
place_inst -name b795 -location {9095.947 12234.300} -status PLACED
place_inst -name r796_0 -location {9095.947 12458.664} -status PLACED
place_inst -name b796 -location {9095.947 12524.400} -status PLACED
place_inst -name r797_0 -location {9150.827 12392.928} -status PLACED
place_inst -name b797 -location {9205.707 12392.928} -status PLACED
place_inst -name r798_0 -location {9205.707 12266.871} -status PLACED
place_inst -name r798_1 -location {9205.707 12140.814} -status PLACED
place_inst -name r798_2 -location {9205.707 12014.757} -status PLACED
place_inst -name b798 -location {9205.707 11888.700} -status PLACED
place_inst -name r799_0 -location {9205.707 12486.414} -status PLACED
place_inst -name b799 -location {9205.707 12579.900} -status PLACED
place_inst -name r800_0 -location {9205.707 12521.746} -status PLACED
place_inst -name r800_1 -location {9205.707 12650.564} -status PLACED
place_inst -name r800_2 -location {9205.707 12779.382} -status PLACED
place_inst -name b800 -location {9205.707 12908.200} -status PLACED
place_inst -name r801_0 -location {9234.613 12392.928} -status PLACED
place_inst -name b801 -location {9263.520 12392.928} -status PLACED
place_inst -name r802_0 -location {9263.520 12313.614} -status PLACED
place_inst -name b802 -location {9263.520 12234.300} -status PLACED
place_inst -name r803_0 -location {9310.020 12392.928} -status PLACED
place_inst -name b803 -location {9356.519 12392.928} -status PLACED
place_inst -name r804_0 -location {9466.680 12392.928} -status PLACED
place_inst -name r804_1 -location {9466.680 12392.928} -status PLACED
place_inst -name r804_2 -location {9791.880 12392.928} -status PLACED
place_inst -name b804 -location {9805.920 12392.928} -status PLACED
place_inst -name r805_0 -location {9805.920 12317.864} -status PLACED
place_inst -name b805 -location {9805.920 12242.800} -status PLACED
place_inst -name r806_0 -location {9820.920 12392.928} -status PLACED
place_inst -name r806_1 -location {10159.640 12392.928} -status PLACED
place_inst -name r806_2 -location {10175.160 12392.928} -status PLACED
place_inst -name b806 -location {10514.400 12392.928} -status PLACED
place_inst -name r807_0 -location {10514.400 12317.864} -status PLACED
place_inst -name b807 -location {10514.400 12242.800} -status PLACED
place_inst -name r808_0 -location {10529.400 12392.928} -status PLACED
place_inst -name r808_1 -location {10868.120 12392.928} -status PLACED
place_inst -name r808_2 -location {10883.640 12392.928} -status PLACED
place_inst -name b808 -location {11222.880 12392.928} -status PLACED
place_inst -name r809_0 -location {11222.880 12317.864} -status PLACED
place_inst -name b809 -location {11222.880 12242.800} -status PLACED
place_inst -name r810_0 -location {11237.880 12392.928} -status PLACED
place_inst -name r810_1 -location {11576.600 12392.928} -status PLACED
place_inst -name r810_2 -location {11592.120 12392.928} -status PLACED
place_inst -name b810 -location {11931.360 12392.928} -status PLACED
place_inst -name r811_0 -location {11931.360 12317.864} -status PLACED
place_inst -name b811 -location {11931.360 12242.800} -status PLACED
place_inst -name r812_0 -location {11946.360 12392.928} -status PLACED
place_inst -name r812_1 -location {12285.080 12392.928} -status PLACED
place_inst -name r812_2 -location {12300.600 12392.928} -status PLACED
place_inst -name b812 -location {12639.840 12392.928} -status PLACED
place_inst -name r813_0 -location {12639.840 12317.864} -status PLACED
place_inst -name b813 -location {12639.840 12242.800} -status PLACED
place_inst -name r814_0 -location {12654.840 12392.928} -status PLACED
place_inst -name r814_1 -location {12993.560 12392.928} -status PLACED
place_inst -name r814_2 -location {13009.080 12392.928} -status PLACED
place_inst -name b814 -location {13348.320 12392.928} -status PLACED
place_inst -name r815_0 -location {13348.320 12317.864} -status PLACED
place_inst -name b815 -location {13348.320 12242.800} -status PLACED
place_inst -name r816_0 -location {13363.320 12392.928} -status PLACED
place_inst -name r816_1 -location {13702.040 12392.928} -status PLACED
place_inst -name r816_2 -location {13717.560 12392.928} -status PLACED
place_inst -name b816 -location {14056.800 12392.928} -status PLACED
place_inst -name r817_0 -location {14056.800 12317.864} -status PLACED
place_inst -name b817 -location {14056.800 12242.800} -status PLACED
place_inst -name r818_0 -location {14071.800 12392.928} -status PLACED
place_inst -name r818_1 -location {14410.520 12392.928} -status PLACED
place_inst -name r818_2 -location {14426.040 12392.928} -status PLACED
place_inst -name b818 -location {14765.280 12392.928} -status PLACED
place_inst -name r819_0 -location {14765.280 12317.864} -status PLACED
place_inst -name b819 -location {14765.280 12242.800} -status PLACED
place_inst -name r820_0 -location {14780.280 12392.928} -status PLACED
place_inst -name r820_1 -location {15119.000 12392.928} -status PLACED
place_inst -name r820_2 -location {15134.520 12392.928} -status PLACED
place_inst -name b820 -location {15473.760 12392.928} -status PLACED
place_inst -name r821_0 -location {15473.760 12317.864} -status PLACED
place_inst -name b821 -location {15473.760 12242.800} -status PLACED
place_inst -name r822_0 -location {15488.760 12392.928} -status PLACED
place_inst -name r822_1 -location {15827.480 12392.928} -status PLACED
place_inst -name r822_2 -location {15843.000 12392.928} -status PLACED
place_inst -name b822 -location {16182.240 12392.928} -status PLACED
place_inst -name r823_0 -location {16182.240 12317.864} -status PLACED
place_inst -name b823 -location {16182.240 12242.800} -status PLACED
place_inst -name r824_0 -location {16197.240 12392.928} -status PLACED
place_inst -name r824_1 -location {16535.960 12392.928} -status PLACED
place_inst -name r824_2 -location {16551.480 12392.928} -status PLACED
place_inst -name b824 -location {16890.720 12392.928} -status PLACED
place_inst -name r825_0 -location {16890.720 12317.864} -status PLACED
place_inst -name b825 -location {16890.720 12242.800} -status PLACED
place_inst -name r826_0 -location {17230.920 12392.928} -status PLACED
place_inst -name b826 -location {17286.464 12392.928} -status PLACED
place_inst -name r827_0 -location {17286.464 12257.064} -status PLACED
place_inst -name b827 -location {17286.464 12121.200} -status PLACED
place_inst -name r828_0 -location {8760.960 13602.523} -status PLACED
place_inst -name r828_1 -location {8770.600 13775.319} -status PLACED
place_inst -name r828_2 -location {8760.960 13963.240} -status PLACED
place_inst -name r828_3 -location {8760.960 14120.909} -status PLACED
place_inst -name r828_4 -location {8760.960 14293.705} -status PLACED
place_inst -name b828 -location {8760.960 14466.500} -status PLACED
place_inst -name r829_0 -location {8590.320 13429.728} -status PLACED
place_inst -name b829 -location {8419.680 13429.728} -status PLACED
place_inst -name r830_0 -location {8419.680 13602.523} -status PLACED
place_inst -name r830_1 -location {8419.680 13607.000} -status PLACED
place_inst -name r830_2 -location {8419.680 13963.240} -status PLACED
place_inst -name r830_3 -location {8419.680 14120.909} -status PLACED
place_inst -name r830_4 -location {8419.680 14293.705} -status PLACED
place_inst -name b830 -location {8419.680 14466.500} -status PLACED
place_inst -name r831_0 -location {8253.600 13429.728} -status PLACED
place_inst -name b831 -location {8087.520 13429.728} -status PLACED
place_inst -name r832_0 -location {8055.240 13429.728} -status PLACED
place_inst -name b832 -location {7715.520 13429.728} -status PLACED
place_inst -name r833_0 -location {7715.520 13354.664} -status PLACED
place_inst -name b833 -location {7715.520 13279.600} -status PLACED
place_inst -name r834_0 -location {7715.520 13577.507} -status PLACED
place_inst -name r834_1 -location {7715.520 13657.080} -status PLACED
place_inst -name r834_2 -location {7715.520 13947.720} -status PLACED
place_inst -name r834_3 -location {7715.520 14020.843} -status PLACED
place_inst -name r834_4 -location {7715.520 14168.621} -status PLACED
place_inst -name b834 -location {7715.520 14316.400} -status PLACED
place_inst -name r835_0 -location {7701.000 13429.728} -status PLACED
place_inst -name r835_1 -location {7362.280 13429.728} -status PLACED
place_inst -name r835_2 -location {7021.560 13429.728} -status PLACED
place_inst -name b835 -location {7007.040 13429.728} -status PLACED
place_inst -name r836_0 -location {7007.040 13354.664} -status PLACED
place_inst -name b836 -location {7007.040 13279.600} -status PLACED
place_inst -name r837_0 -location {7007.040 13577.507} -status PLACED
place_inst -name r837_1 -location {7007.040 13657.080} -status PLACED
place_inst -name r837_2 -location {7007.040 13947.720} -status PLACED
place_inst -name r837_3 -location {7007.040 14020.843} -status PLACED
place_inst -name r837_4 -location {7007.040 14168.621} -status PLACED
place_inst -name b837 -location {7007.040 14316.400} -status PLACED
place_inst -name r838_0 -location {6667.320 13429.728} -status PLACED
place_inst -name r838_1 -location {6653.800 13429.728} -status PLACED
place_inst -name r838_2 -location {6638.280 13429.728} -status PLACED
place_inst -name b838 -location {6298.560 13429.728} -status PLACED
place_inst -name r839_0 -location {6298.560 13354.664} -status PLACED
place_inst -name b839 -location {6298.560 13279.600} -status PLACED
place_inst -name r840_0 -location {6298.560 13577.507} -status PLACED
place_inst -name r840_1 -location {6298.560 13657.080} -status PLACED
place_inst -name r840_2 -location {6298.560 13947.720} -status PLACED
place_inst -name r840_3 -location {6298.560 14020.843} -status PLACED
place_inst -name r840_4 -location {6298.560 14168.621} -status PLACED
place_inst -name b840 -location {6298.560 14316.400} -status PLACED
place_inst -name r841_0 -location {6284.040 13429.728} -status PLACED
place_inst -name r841_1 -location {5945.320 13429.728} -status PLACED
place_inst -name r841_2 -location {5604.600 13429.728} -status PLACED
place_inst -name b841 -location {5590.080 13429.728} -status PLACED
place_inst -name r842_0 -location {5590.080 13354.664} -status PLACED
place_inst -name b842 -location {5590.080 13279.600} -status PLACED
place_inst -name r843_0 -location {5590.080 13577.507} -status PLACED
place_inst -name r843_1 -location {5590.080 13657.080} -status PLACED
place_inst -name r843_2 -location {5590.080 13947.720} -status PLACED
place_inst -name r843_3 -location {5590.080 14020.843} -status PLACED
place_inst -name r843_4 -location {5590.080 14168.621} -status PLACED
place_inst -name b843 -location {5590.080 14316.400} -status PLACED
place_inst -name r844_0 -location {5250.360 13429.728} -status PLACED
place_inst -name r844_1 -location {5236.840 13429.728} -status PLACED
place_inst -name r844_2 -location {5221.320 13429.728} -status PLACED
place_inst -name b844 -location {4881.600 13429.728} -status PLACED
place_inst -name r845_0 -location {4881.600 13354.664} -status PLACED
place_inst -name b845 -location {4881.600 13279.600} -status PLACED
place_inst -name r846_0 -location {4881.600 13577.507} -status PLACED
place_inst -name r846_1 -location {4881.600 13657.080} -status PLACED
place_inst -name r846_2 -location {4881.600 13947.720} -status PLACED
place_inst -name r846_3 -location {4881.600 14020.843} -status PLACED
place_inst -name r846_4 -location {4881.600 14168.621} -status PLACED
place_inst -name b846 -location {4881.600 14316.400} -status PLACED
place_inst -name r847_0 -location {4867.080 13429.728} -status PLACED
place_inst -name r847_1 -location {4528.360 13429.728} -status PLACED
place_inst -name r847_2 -location {4187.640 13429.728} -status PLACED
place_inst -name b847 -location {4173.120 13429.728} -status PLACED
place_inst -name r848_0 -location {4173.120 13354.664} -status PLACED
place_inst -name b848 -location {4173.120 13279.600} -status PLACED
place_inst -name r849_0 -location {4173.120 13577.507} -status PLACED
place_inst -name r849_1 -location {4173.120 13657.080} -status PLACED
place_inst -name r849_2 -location {4173.120 13947.720} -status PLACED
place_inst -name r849_3 -location {4173.120 14020.843} -status PLACED
place_inst -name r849_4 -location {4173.120 14168.621} -status PLACED
place_inst -name b849 -location {4173.120 14316.400} -status PLACED
place_inst -name r850_0 -location {3833.400 13429.728} -status PLACED
place_inst -name r850_1 -location {3819.880 13429.728} -status PLACED
place_inst -name r850_2 -location {3479.160 13429.728} -status PLACED
place_inst -name b850 -location {3464.640 13429.728} -status PLACED
place_inst -name r851_0 -location {3464.640 13354.664} -status PLACED
place_inst -name b851 -location {3464.640 13279.600} -status PLACED
place_inst -name r852_0 -location {3464.640 13577.507} -status PLACED
place_inst -name r852_1 -location {3464.640 13657.080} -status PLACED
place_inst -name r852_2 -location {3464.640 13947.720} -status PLACED
place_inst -name r852_3 -location {3464.640 14020.843} -status PLACED
place_inst -name r852_4 -location {3464.640 14168.621} -status PLACED
place_inst -name b852 -location {3464.640 14316.400} -status PLACED
place_inst -name r853_0 -location {3124.920 13429.728} -status PLACED
place_inst -name r853_1 -location {3109.400 13429.728} -status PLACED
place_inst -name r853_2 -location {2770.680 13429.728} -status PLACED
place_inst -name b853 -location {2756.160 13429.728} -status PLACED
place_inst -name r854_0 -location {2756.160 13354.664} -status PLACED
place_inst -name b854 -location {2756.160 13279.600} -status PLACED
place_inst -name r855_0 -location {2756.160 13577.507} -status PLACED
place_inst -name r855_1 -location {2756.160 13657.080} -status PLACED
place_inst -name r855_2 -location {2756.160 13947.720} -status PLACED
place_inst -name r855_3 -location {2756.160 14020.843} -status PLACED
place_inst -name r855_4 -location {2756.160 14168.621} -status PLACED
place_inst -name b855 -location {2756.160 14316.400} -status PLACED
place_inst -name r856_0 -location {2416.440 13429.728} -status PLACED
place_inst -name r856_1 -location {2402.920 13429.728} -status PLACED
place_inst -name r856_2 -location {2387.400 13429.728} -status PLACED
place_inst -name b856 -location {2047.680 13429.728} -status PLACED
place_inst -name r857_0 -location {2047.680 13354.664} -status PLACED
place_inst -name b857 -location {2047.680 13279.600} -status PLACED
place_inst -name r858_0 -location {2047.680 13577.507} -status PLACED
place_inst -name r858_1 -location {2047.680 13657.080} -status PLACED
place_inst -name r858_2 -location {2047.680 13947.720} -status PLACED
place_inst -name r858_3 -location {2047.680 14020.843} -status PLACED
place_inst -name r858_4 -location {2047.680 14168.621} -status PLACED
place_inst -name b858 -location {2047.680 14316.400} -status PLACED
place_inst -name r859_0 -location {1707.960 13429.728} -status PLACED
place_inst -name r859_1 -location {1694.440 13429.728} -status PLACED
place_inst -name r859_2 -location {1678.920 13429.728} -status PLACED
place_inst -name b859 -location {1339.200 13429.728} -status PLACED
place_inst -name r860_0 -location {1339.200 13354.664} -status PLACED
place_inst -name b860 -location {1339.200 13279.600} -status PLACED
place_inst -name r861_0 -location {1339.200 13577.507} -status PLACED
place_inst -name r861_1 -location {1339.200 13657.080} -status PLACED
place_inst -name r861_2 -location {1339.200 13947.720} -status PLACED
place_inst -name r861_3 -location {1339.200 14020.843} -status PLACED
place_inst -name r861_4 -location {1339.200 14168.621} -status PLACED
place_inst -name b861 -location {1339.200 14316.400} -status PLACED
place_inst -name r862_0 -location {999.480 13429.728} -status PLACED
place_inst -name r862_1 -location {985.960 13429.728} -status PLACED
place_inst -name r862_2 -location {645.240 13429.728} -status PLACED
place_inst -name b862 -location {630.720 13429.728} -status PLACED
place_inst -name r863_0 -location {630.720 13354.664} -status PLACED
place_inst -name b863 -location {630.720 13279.600} -status PLACED
place_inst -name r864_0 -location {630.720 13577.507} -status PLACED
place_inst -name r864_1 -location {630.720 13657.080} -status PLACED
place_inst -name r864_2 -location {630.720 13947.720} -status PLACED
place_inst -name r864_3 -location {630.720 14020.843} -status PLACED
place_inst -name r864_4 -location {630.720 14168.621} -status PLACED
place_inst -name b864 -location {630.720 14316.400} -status PLACED
place_inst -name r865_0 -location {291.000 13429.728} -status PLACED
place_inst -name b865 -location {235.456 13429.728} -status PLACED
place_inst -name r866_0 -location {235.456 13620.996} -status PLACED
place_inst -name r866_1 -location {235.456 13812.264} -status PLACED
place_inst -name r866_2 -location {235.456 14003.532} -status PLACED
place_inst -name b866 -location {235.456 14194.800} -status PLACED
place_inst -name r867_0 -location {235.456 13599.340} -status PLACED
place_inst -name r867_1 -location {235.456 13768.952} -status PLACED
place_inst -name r867_2 -location {235.456 13938.564} -status PLACED
place_inst -name r867_3 -location {235.456 14108.176} -status PLACED
place_inst -name r867_4 -location {235.456 14277.788} -status PLACED
place_inst -name b867 -location {235.456 14447.400} -status PLACED
place_inst -name r868_0 -location {212.528 13429.728} -status PLACED
place_inst -name b868 -location {189.600 13429.728} -status PLACED
place_inst -name r869_0 -location {189.600 13541.164} -status PLACED
place_inst -name b869 -location {189.600 13652.600} -status PLACED
place_inst -name r870_0 -location {189.600 13558.521} -status PLACED
place_inst -name r870_1 -location {189.600 13687.314} -status PLACED
place_inst -name r870_2 -location {189.600 13816.107} -status PLACED
place_inst -name b870 -location {189.600 13944.900} -status PLACED
place_inst -name r871_0 -location {8760.960 13371.414} -status PLACED
place_inst -name b871 -location {8760.960 13313.100} -status PLACED
place_inst -name r872_0 -location {8760.960 13589.107} -status PLACED
place_inst -name r872_1 -location {8770.600 13748.485} -status PLACED
place_inst -name r872_2 -location {8770.600 13907.864} -status PLACED
place_inst -name r872_3 -location {8760.960 14067.243} -status PLACED
place_inst -name r872_4 -location {8760.960 14226.621} -status PLACED
place_inst -name b872 -location {8760.960 14386.000} -status PLACED
place_inst -name r873_0 -location {8813.672 13429.728} -status PLACED
place_inst -name b873 -location {8866.384 13429.728} -status PLACED
place_inst -name r874_0 -location {8866.384 13307.996} -status PLACED
place_inst -name r874_1 -location {8866.384 13186.264} -status PLACED
place_inst -name r874_2 -location {8866.384 13064.532} -status PLACED
place_inst -name b874 -location {8866.384 12942.800} -status PLACED
place_inst -name r875_0 -location {8866.384 13589.514} -status PLACED
place_inst -name b875 -location {8866.384 13749.300} -status PLACED
place_inst -name r876_0 -location {8866.384 13577.796} -status PLACED
place_inst -name r876_1 -location {8866.384 13725.864} -status PLACED
place_inst -name r876_2 -location {8866.384 13873.932} -status PLACED
place_inst -name b876 -location {8866.384 14022.000} -status PLACED
place_inst -name r877_0 -location {8866.384 13573.907} -status PLACED
place_inst -name r877_1 -location {8866.384 13718.085} -status PLACED
place_inst -name r877_2 -location {8866.384 13862.264} -status PLACED
place_inst -name r877_3 -location {8866.384 14006.443} -status PLACED
place_inst -name r877_4 -location {8866.384 14150.621} -status PLACED
place_inst -name b877 -location {8866.384 14294.800} -status PLACED
place_inst -name r878_0 -location {8866.384 13609.957} -status PLACED
place_inst -name r878_1 -location {8866.384 13790.185} -status PLACED
place_inst -name r878_2 -location {8866.384 13970.414} -status PLACED
place_inst -name r878_3 -location {8866.384 14150.643} -status PLACED
place_inst -name r878_4 -location {8866.384 14330.871} -status PLACED
place_inst -name b878 -location {8866.384 14511.100} -status PLACED
place_inst -name r879_0 -location {8866.384 13617.390} -status PLACED
place_inst -name r879_1 -location {8866.384 13805.052} -status PLACED
place_inst -name r879_2 -location {8866.384 13992.714} -status PLACED
place_inst -name r879_3 -location {8866.384 14180.376} -status PLACED
place_inst -name r879_4 -location {8866.384 14368.038} -status PLACED
place_inst -name b879 -location {8866.384 14555.700} -status PLACED
place_inst -name r880_0 -location {8866.384 13624.440} -status PLACED
place_inst -name r880_1 -location {8866.384 13819.152} -status PLACED
place_inst -name r880_2 -location {8866.384 14013.864} -status PLACED
place_inst -name r880_3 -location {8866.384 14208.576} -status PLACED
place_inst -name r880_4 -location {8866.384 14403.288} -status PLACED
place_inst -name b880 -location {8866.384 14598.000} -status PLACED
place_inst -name r881_0 -location {8932.550 13429.728} -status PLACED
place_inst -name b881 -location {8998.716 13429.728} -status PLACED
place_inst -name r882_0 -location {8998.716 13314.414} -status PLACED
place_inst -name b882 -location {8998.716 13199.100} -status PLACED
place_inst -name r883_0 -location {8998.716 13584.264} -status PLACED
place_inst -name b883 -location {8998.716 13738.800} -status PLACED
place_inst -name r884_0 -location {8998.716 13619.914} -status PLACED
place_inst -name b884 -location {8998.716 13810.100} -status PLACED
place_inst -name r885_0 -location {8998.716 13576.871} -status PLACED
place_inst -name r885_1 -location {8998.716 13724.014} -status PLACED
place_inst -name r885_2 -location {8998.716 13871.157} -status PLACED
place_inst -name b885 -location {8998.716 14018.300} -status PLACED
place_inst -name r886_0 -location {8998.716 13601.971} -status PLACED
place_inst -name r886_1 -location {8998.716 13774.214} -status PLACED
place_inst -name r886_2 -location {8998.716 13946.457} -status PLACED
place_inst -name b886 -location {8998.716 14118.700} -status PLACED
place_inst -name r887_0 -location {8998.716 13572.540} -status PLACED
place_inst -name r887_1 -location {8998.716 13715.352} -status PLACED
place_inst -name r887_2 -location {8998.716 13858.164} -status PLACED
place_inst -name r887_3 -location {8998.716 14000.976} -status PLACED
place_inst -name r887_4 -location {8998.716 14143.788} -status PLACED
place_inst -name b887 -location {8998.716 14286.600} -status PLACED
place_inst -name r888_0 -location {8998.716 13601.907} -status PLACED
place_inst -name r888_1 -location {8998.716 13774.085} -status PLACED
place_inst -name r888_2 -location {8998.716 13946.264} -status PLACED
place_inst -name r888_3 -location {8998.716 14118.443} -status PLACED
place_inst -name r888_4 -location {8998.716 14290.621} -status PLACED
place_inst -name b888 -location {8998.716 14462.800} -status PLACED
place_inst -name r889_0 -location {8998.716 13616.423} -status PLACED
place_inst -name r889_1 -location {8998.716 13803.119} -status PLACED
place_inst -name r889_2 -location {8998.716 13989.814} -status PLACED
place_inst -name r889_3 -location {8998.716 14176.509} -status PLACED
place_inst -name r889_4 -location {8998.716 14363.205} -status PLACED
place_inst -name b889 -location {8998.716 14549.900} -status PLACED
place_inst -name r890_0 -location {9018.206 13429.728} -status PLACED
place_inst -name b890 -location {9037.696 13429.728} -status PLACED
place_inst -name r891_0 -location {9037.696 13597.757} -status PLACED
place_inst -name r891_1 -location {9037.696 13765.785} -status PLACED
place_inst -name r891_2 -location {9037.696 13933.814} -status PLACED
place_inst -name r891_3 -location {9037.696 14101.843} -status PLACED
place_inst -name r891_4 -location {9037.696 14269.871} -status PLACED
place_inst -name b891 -location {9037.696 14437.900} -status PLACED
place_inst -name r892_0 -location {9070.822 13429.728} -status PLACED
place_inst -name b892 -location {9103.947 13429.728} -status PLACED
place_inst -name r893_0 -location {9103.947 13307.996} -status PLACED
place_inst -name r893_1 -location {9103.947 13186.264} -status PLACED
place_inst -name r893_2 -location {9103.947 13064.532} -status PLACED
place_inst -name b893 -location {9103.947 12942.800} -status PLACED
place_inst -name r894_0 -location {9103.947 13576.090} -status PLACED
place_inst -name r894_1 -location {9103.947 13722.452} -status PLACED
place_inst -name r894_2 -location {9103.947 13868.814} -status PLACED
place_inst -name r894_3 -location {9103.947 14015.176} -status PLACED
place_inst -name r894_4 -location {9103.947 14161.538} -status PLACED
place_inst -name b894 -location {9103.947 14307.900} -status PLACED
place_inst -name r895_0 -location {9103.947 13624.440} -status PLACED
place_inst -name r895_1 -location {9103.947 13819.152} -status PLACED
place_inst -name r895_2 -location {9103.947 14013.864} -status PLACED
place_inst -name r895_3 -location {9103.947 14208.576} -status PLACED
place_inst -name r895_4 -location {9103.947 14403.288} -status PLACED
place_inst -name b895 -location {9103.947 14598.000} -status PLACED
place_inst -name r896_0 -location {9151.981 13429.728} -status PLACED
place_inst -name b896 -location {9200.016 13429.728} -status PLACED
place_inst -name r897_0 -location {9200.016 13350.414} -status PLACED
place_inst -name b897 -location {9200.016 13271.100} -status PLACED
place_inst -name r898_0 -location {9200.016 13523.214} -status PLACED
place_inst -name b898 -location {9200.016 13616.700} -status PLACED
place_inst -name r899_0 -location {9200.016 13562.871} -status PLACED
place_inst -name r899_1 -location {9200.016 13696.014} -status PLACED
place_inst -name r899_2 -location {9200.016 13829.157} -status PLACED
place_inst -name b899 -location {9200.016 13962.300} -status PLACED
place_inst -name r900_0 -location {9200.016 13582.699} -status PLACED
place_inst -name r900_1 -location {9200.016 13735.671} -status PLACED
place_inst -name r900_2 -location {9200.016 13888.642} -status PLACED
place_inst -name r900_3 -location {9200.016 14041.614} -status PLACED
place_inst -name r900_4 -location {9200.016 14194.585} -status PLACED
place_inst -name r900_5 -location {9200.016 14347.557} -status PLACED
place_inst -name r900_6 -location {9200.016 14500.529} -status PLACED
place_inst -name b900 -location {9200.016 14653.500} -status PLACED
place_inst -name r901_0 -location {9231.768 13429.728} -status PLACED
place_inst -name b901 -location {9263.520 13429.728} -status PLACED
place_inst -name r902_0 -location {9263.520 13576.090} -status PLACED
place_inst -name r902_1 -location {9263.520 13722.452} -status PLACED
place_inst -name r902_2 -location {9263.520 13868.814} -status PLACED
place_inst -name r902_3 -location {9263.520 14015.176} -status PLACED
place_inst -name r902_4 -location {9263.520 14161.538} -status PLACED
place_inst -name b902 -location {9263.520 14307.900} -status PLACED
place_inst -name r903_0 -location {9307.680 13429.728} -status PLACED
place_inst -name b903 -location {9351.840 13429.728} -status PLACED
place_inst -name r904_0 -location {9351.840 13602.523} -status PLACED
place_inst -name r904_1 -location {9351.840 13775.319} -status PLACED
place_inst -name r904_2 -location {9351.840 13948.114} -status PLACED
place_inst -name r904_3 -location {9351.840 14120.909} -status PLACED
place_inst -name r904_4 -location {9351.840 14293.705} -status PLACED
place_inst -name b904 -location {9351.840 14466.500} -status PLACED
place_inst -name r905_0 -location {9351.840 13605.357} -status PLACED
place_inst -name r905_1 -location {9351.840 13780.985} -status PLACED
place_inst -name r905_2 -location {9351.840 13956.614} -status PLACED
place_inst -name r905_3 -location {9351.840 14132.243} -status PLACED
place_inst -name r905_4 -location {9351.840 14307.871} -status PLACED
place_inst -name b905 -location {9351.840 14483.500} -status PLACED
place_inst -name r906_0 -location {9393.120 13429.728} -status PLACED
place_inst -name b906 -location {9434.400 13429.728} -status PLACED
place_inst -name r907_0 -location {9466.680 13429.728} -status PLACED
place_inst -name b907 -location {9806.400 13429.728} -status PLACED
place_inst -name r908_0 -location {9806.400 13354.664} -status PLACED
place_inst -name b908 -location {9806.400 13279.600} -status PLACED
place_inst -name r909_0 -location {9806.400 13577.507} -status PLACED
place_inst -name r909_1 -location {9806.400 13657.080} -status PLACED
place_inst -name r909_2 -location {9806.400 13947.720} -status PLACED
place_inst -name r909_3 -location {9806.400 14020.843} -status PLACED
place_inst -name r909_4 -location {9806.400 14168.621} -status PLACED
place_inst -name b909 -location {9806.400 14316.400} -status PLACED
place_inst -name r910_0 -location {9820.920 13429.728} -status PLACED
place_inst -name r910_1 -location {10159.640 13429.728} -status PLACED
place_inst -name r910_2 -location {10175.160 13429.728} -status PLACED
place_inst -name b910 -location {10514.880 13429.728} -status PLACED
place_inst -name r911_0 -location {10514.880 13354.664} -status PLACED
place_inst -name b911 -location {10514.880 13279.600} -status PLACED
place_inst -name r912_0 -location {10514.880 13577.507} -status PLACED
place_inst -name r912_1 -location {10514.880 13657.080} -status PLACED
place_inst -name r912_2 -location {10514.880 13947.720} -status PLACED
place_inst -name r912_3 -location {10514.880 14020.843} -status PLACED
place_inst -name r912_4 -location {10514.880 14168.621} -status PLACED
place_inst -name b912 -location {10514.880 14316.400} -status PLACED
place_inst -name r913_0 -location {10529.400 13429.728} -status PLACED
place_inst -name r913_1 -location {10868.120 13429.728} -status PLACED
place_inst -name r913_2 -location {10883.640 13429.728} -status PLACED
place_inst -name b913 -location {11223.360 13429.728} -status PLACED
place_inst -name r914_0 -location {11223.360 13354.664} -status PLACED
place_inst -name b914 -location {11223.360 13279.600} -status PLACED
place_inst -name r915_0 -location {11223.360 13577.507} -status PLACED
place_inst -name r915_1 -location {11223.360 13657.080} -status PLACED
place_inst -name r915_2 -location {11223.360 13947.720} -status PLACED
place_inst -name r915_3 -location {11223.360 14020.843} -status PLACED
place_inst -name r915_4 -location {11223.360 14168.621} -status PLACED
place_inst -name b915 -location {11223.360 14316.400} -status PLACED
place_inst -name r916_0 -location {11237.880 13429.728} -status PLACED
place_inst -name r916_1 -location {11576.600 13429.728} -status PLACED
place_inst -name r916_2 -location {11917.320 13429.728} -status PLACED
place_inst -name b916 -location {11931.840 13429.728} -status PLACED
place_inst -name r917_0 -location {11931.840 13354.664} -status PLACED
place_inst -name b917 -location {11931.840 13279.600} -status PLACED
place_inst -name r918_0 -location {11931.840 13577.507} -status PLACED
place_inst -name r918_1 -location {11931.840 13657.080} -status PLACED
place_inst -name r918_2 -location {11931.840 13947.720} -status PLACED
place_inst -name r918_3 -location {11931.840 14020.843} -status PLACED
place_inst -name r918_4 -location {11931.840 14168.621} -status PLACED
place_inst -name b918 -location {11931.840 14316.400} -status PLACED
place_inst -name r919_0 -location {11946.360 13429.728} -status PLACED
place_inst -name r919_1 -location {12285.080 13429.728} -status PLACED
place_inst -name r919_2 -location {12625.800 13429.728} -status PLACED
place_inst -name b919 -location {12640.320 13429.728} -status PLACED
place_inst -name r920_0 -location {12640.320 13354.664} -status PLACED
place_inst -name b920 -location {12640.320 13279.600} -status PLACED
place_inst -name r921_0 -location {12640.320 13577.507} -status PLACED
place_inst -name r921_1 -location {12640.320 13657.080} -status PLACED
place_inst -name r921_2 -location {12640.320 13947.720} -status PLACED
place_inst -name r921_3 -location {12640.320 14020.843} -status PLACED
place_inst -name r921_4 -location {12640.320 14168.621} -status PLACED
place_inst -name b921 -location {12640.320 14316.400} -status PLACED
place_inst -name r922_0 -location {12654.840 13429.728} -status PLACED
place_inst -name r922_1 -location {12993.560 13429.728} -status PLACED
place_inst -name r922_2 -location {13009.080 13429.728} -status PLACED
place_inst -name b922 -location {13348.800 13429.728} -status PLACED
place_inst -name r923_0 -location {13348.800 13354.664} -status PLACED
place_inst -name b923 -location {13348.800 13279.600} -status PLACED
place_inst -name r924_0 -location {13348.800 13577.507} -status PLACED
place_inst -name r924_1 -location {13348.800 13657.080} -status PLACED
place_inst -name r924_2 -location {13348.800 13947.720} -status PLACED
place_inst -name r924_3 -location {13348.800 14020.843} -status PLACED
place_inst -name r924_4 -location {13348.800 14168.621} -status PLACED
place_inst -name b924 -location {13348.800 14316.400} -status PLACED
place_inst -name r925_0 -location {13363.320 13429.728} -status PLACED
place_inst -name r925_1 -location {13704.040 13429.728} -status PLACED
place_inst -name r925_2 -location {13717.560 13429.728} -status PLACED
place_inst -name b925 -location {14057.280 13429.728} -status PLACED
place_inst -name r926_0 -location {14057.280 13354.664} -status PLACED
place_inst -name b926 -location {14057.280 13279.600} -status PLACED
place_inst -name r927_0 -location {14057.280 13577.507} -status PLACED
place_inst -name r927_1 -location {14057.280 13657.080} -status PLACED
place_inst -name r927_2 -location {14057.280 13947.720} -status PLACED
place_inst -name r927_3 -location {14057.280 14020.843} -status PLACED
place_inst -name r927_4 -location {14057.280 14168.621} -status PLACED
place_inst -name b927 -location {14057.280 14316.400} -status PLACED
place_inst -name r928_0 -location {14397.000 13429.728} -status PLACED
place_inst -name r928_1 -location {14410.520 13429.728} -status PLACED
place_inst -name r928_2 -location {14426.040 13429.728} -status PLACED
place_inst -name b928 -location {14765.760 13429.728} -status PLACED
place_inst -name r929_0 -location {14765.760 13354.664} -status PLACED
place_inst -name b929 -location {14765.760 13279.600} -status PLACED
place_inst -name r930_0 -location {14765.760 13577.507} -status PLACED
place_inst -name r930_1 -location {14765.760 13657.080} -status PLACED
place_inst -name r930_2 -location {14765.760 13947.720} -status PLACED
place_inst -name r930_3 -location {14765.760 14020.843} -status PLACED
place_inst -name r930_4 -location {14765.760 14168.621} -status PLACED
place_inst -name b930 -location {14765.760 14316.400} -status PLACED
place_inst -name r931_0 -location {15105.480 13429.728} -status PLACED
place_inst -name r931_1 -location {15119.000 13429.728} -status PLACED
place_inst -name r931_2 -location {15134.520 13429.728} -status PLACED
place_inst -name b931 -location {15474.240 13429.728} -status PLACED
place_inst -name r932_0 -location {15474.240 13354.664} -status PLACED
place_inst -name b932 -location {15474.240 13279.600} -status PLACED
place_inst -name r933_0 -location {15474.240 13577.507} -status PLACED
place_inst -name r933_1 -location {15474.240 13657.080} -status PLACED
place_inst -name r933_2 -location {15474.240 13947.720} -status PLACED
place_inst -name r933_3 -location {15474.240 14020.843} -status PLACED
place_inst -name r933_4 -location {15474.240 14168.621} -status PLACED
place_inst -name b933 -location {15474.240 14316.400} -status PLACED
place_inst -name r934_0 -location {15813.960 13429.728} -status PLACED
place_inst -name r934_1 -location {15827.480 13429.728} -status PLACED
place_inst -name r934_2 -location {15843.000 13429.728} -status PLACED
place_inst -name b934 -location {16182.720 13429.728} -status PLACED
place_inst -name r935_0 -location {16182.720 13354.664} -status PLACED
place_inst -name b935 -location {16182.720 13279.600} -status PLACED
place_inst -name r936_0 -location {16182.720 13577.507} -status PLACED
place_inst -name r936_1 -location {16182.720 13657.080} -status PLACED
place_inst -name r936_2 -location {16182.720 13947.720} -status PLACED
place_inst -name r936_3 -location {16182.720 14020.843} -status PLACED
place_inst -name r936_4 -location {16182.720 14168.621} -status PLACED
place_inst -name b936 -location {16182.720 14316.400} -status PLACED
place_inst -name r937_0 -location {16522.440 13429.728} -status PLACED
place_inst -name r937_1 -location {16535.960 13429.728} -status PLACED
place_inst -name r937_2 -location {16876.680 13429.728} -status PLACED
place_inst -name b937 -location {16891.200 13429.728} -status PLACED
place_inst -name r938_0 -location {16891.200 13354.664} -status PLACED
place_inst -name b938 -location {16891.200 13279.600} -status PLACED
place_inst -name r939_0 -location {16891.200 13577.507} -status PLACED
place_inst -name r939_1 -location {16891.200 13657.080} -status PLACED
place_inst -name r939_2 -location {16891.200 13947.720} -status PLACED
place_inst -name r939_3 -location {16891.200 14020.843} -status PLACED
place_inst -name r939_4 -location {16891.200 14168.621} -status PLACED
place_inst -name b939 -location {16891.200 14316.400} -status PLACED
place_inst -name r940_0 -location {17230.920 13429.728} -status PLACED
place_inst -name b940 -location {17286.464 13429.728} -status PLACED
place_inst -name r941_0 -location {17286.464 13620.996} -status PLACED
place_inst -name r941_1 -location {17286.464 13812.264} -status PLACED
place_inst -name r941_2 -location {17286.464 14003.532} -status PLACED
place_inst -name b941 -location {17286.464 14194.800} -status PLACED
place_inst -name r942_0 -location {17286.464 13599.340} -status PLACED
place_inst -name r942_1 -location {17286.464 13768.952} -status PLACED
place_inst -name r942_2 -location {17286.464 13938.564} -status PLACED
place_inst -name r942_3 -location {17286.464 14108.176} -status PLACED
place_inst -name r942_4 -location {17286.464 14277.788} -status PLACED
place_inst -name b942 -location {17286.464 14447.400} -status PLACED
place_inst -name r943_0 -location {17309.392 13429.728} -status PLACED
place_inst -name b943 -location {17332.320 13429.728} -status PLACED
place_inst -name r944_0 -location {17332.320 13541.164} -status PLACED
place_inst -name b944 -location {17332.320 13652.600} -status PLACED
place_inst -name r945_0 -location {17332.320 13558.521} -status PLACED
place_inst -name r945_1 -location {17332.320 13687.314} -status PLACED
place_inst -name r945_2 -location {17332.320 13816.107} -status PLACED
place_inst -name b945 -location {17332.320 13944.900} -status PLACED
place_inst -name r946_0 -location {8580.810 16303.648} -status PLACED
place_inst -name r946_1 -location {8401.660 16303.648} -status PLACED
place_inst -name r946_2 -location {8222.510 16303.648} -status PLACED
place_inst -name b946 -location {8043.360 16303.648} -status PLACED
place_inst -name r947_0 -location {7867.400 16303.000} -status PLACED
place_inst -name r947_1 -location {7859.160 16134.632} -status PLACED
place_inst -name r947_2 -location {7859.160 15958.024} -status PLACED
place_inst -name r947_3 -location {7859.160 15781.416} -status PLACED
place_inst -name r947_4 -location {8017.352 15763.000} -status PLACED
place_inst -name b947 -location {8043.360 15612.400} -status PLACED
place_inst -name r948_0 -location {7859.525 16303.648} -status PLACED
place_inst -name r948_1 -location {7675.690 16303.648} -status PLACED
place_inst -name r948_2 -location {7542.672 16303.648} -status PLACED
place_inst -name b948 -location {7308.021 16303.648} -status PLACED
place_inst -name r949_0 -location {7319.080 16160.307} -status PLACED
place_inst -name r949_1 -location {7307.481 16016.965} -status PLACED
place_inst -name r949_2 -location {7307.210 15873.624} -status PLACED
place_inst -name r949_3 -location {7306.940 15730.283} -status PLACED
place_inst -name r949_4 -location {7306.670 15586.941} -status PLACED
place_inst -name b949 -location {7306.400 15443.600} -status PLACED
place_inst -name r950_0 -location {7319.080 16133.624} -status PLACED
place_inst -name b950 -location {7306.400 15963.600} -status PLACED
place_inst -name r951_0 -location {7125.240 16303.648} -status PLACED
place_inst -name b951 -location {6957.344 16303.648} -status PLACED
place_inst -name r952_0 -location {6957.344 16086.680} -status PLACED
place_inst -name r952_1 -location {6957.344 15945.099} -status PLACED
place_inst -name r952_2 -location {6957.344 15765.824} -status PLACED
place_inst -name r952_3 -location {6957.344 15586.549} -status PLACED
place_inst -name r952_4 -location {6957.344 15407.275} -status PLACED
place_inst -name b952 -location {6957.344 15228.000} -status PLACED
place_inst -name r953_0 -location {6957.344 16226.920} -status PLACED
place_inst -name r953_1 -location {6957.344 16025.665} -status PLACED
place_inst -name r953_2 -location {6957.344 15886.674} -status PLACED
place_inst -name r953_3 -location {6957.344 15747.683} -status PLACED
place_inst -name r953_4 -location {6957.344 15608.691} -status PLACED
place_inst -name b953 -location {6957.344 15469.700} -status PLACED
place_inst -name r954_0 -location {6957.344 16226.920} -status PLACED
place_inst -name r954_1 -location {6957.344 16086.680} -status PLACED
place_inst -name r954_2 -location {6957.344 15986.437} -status PLACED
place_inst -name b954 -location {6957.344 15880.700} -status PLACED
place_inst -name r955_0 -location {6777.248 16303.648} -status PLACED
place_inst -name b955 -location {6597.152 16303.648} -status PLACED
place_inst -name r956_0 -location {6597.152 16086.680} -status PLACED
place_inst -name r956_1 -location {6597.152 15977.299} -status PLACED
place_inst -name r956_2 -location {6597.152 15814.124} -status PLACED
place_inst -name r956_3 -location {6597.152 15650.949} -status PLACED
place_inst -name r956_4 -location {6597.152 15487.775} -status PLACED
place_inst -name b956 -location {6597.152 15324.600} -status PLACED
place_inst -name r957_0 -location {6597.152 16226.920} -status PLACED
place_inst -name r957_1 -location {6597.152 16074.124} -status PLACED
place_inst -name r957_2 -location {6597.152 15959.362} -status PLACED
place_inst -name b957 -location {6597.152 15844.600} -status PLACED
place_inst -name r958_0 -location {6416.544 16303.648} -status PLACED
place_inst -name b958 -location {6235.936 16303.648} -status PLACED
place_inst -name r959_0 -location {6235.936 16086.680} -status PLACED
place_inst -name r959_1 -location {6235.936 15945.099} -status PLACED
place_inst -name r959_2 -location {6235.936 15765.824} -status PLACED
place_inst -name r959_3 -location {6235.936 15586.549} -status PLACED
place_inst -name r959_4 -location {6235.936 15407.275} -status PLACED
place_inst -name b959 -location {6235.936 15228.000} -status PLACED
place_inst -name r960_0 -location {6235.936 16226.920} -status PLACED
place_inst -name r960_1 -location {6235.936 16025.665} -status PLACED
place_inst -name r960_2 -location {6235.936 15886.674} -status PLACED
place_inst -name r960_3 -location {6235.936 15747.683} -status PLACED
place_inst -name r960_4 -location {6235.936 15608.691} -status PLACED
place_inst -name b960 -location {6235.936 15469.700} -status PLACED
place_inst -name r961_0 -location {6235.936 16226.920} -status PLACED
place_inst -name r961_1 -location {6235.936 16086.680} -status PLACED
place_inst -name r961_2 -location {6235.936 15986.437} -status PLACED
place_inst -name b961 -location {6235.936 15880.700} -status PLACED
place_inst -name r962_0 -location {6055.838 16303.648} -status PLACED
place_inst -name b962 -location {5875.740 16303.648} -status PLACED
place_inst -name r963_0 -location {5874.200 16123.373} -status PLACED
place_inst -name r963_1 -location {5875.745 15943.099} -status PLACED
place_inst -name r963_2 -location {5875.747 15762.824} -status PLACED
place_inst -name r963_3 -location {5875.750 15582.549} -status PLACED
place_inst -name r963_4 -location {5875.753 15402.275} -status PLACED
place_inst -name b963 -location {5875.755 15222.000} -status PLACED
place_inst -name r964_0 -location {5874.200 16160.307} -status PLACED
place_inst -name r964_1 -location {5876.200 16016.965} -status PLACED
place_inst -name r964_2 -location {5874.200 15873.624} -status PLACED
place_inst -name r964_3 -location {5874.200 15730.283} -status PLACED
place_inst -name r964_4 -location {5876.200 15586.941} -status PLACED
place_inst -name b964 -location {5874.645 15443.600} -status PLACED
place_inst -name r965_0 -location {5874.200 16163.236} -status PLACED
place_inst -name r965_1 -location {5875.747 16022.824} -status PLACED
place_inst -name r965_2 -location {5875.751 15882.412} -status PLACED
place_inst -name b965 -location {5875.755 15742.000} -status PLACED
place_inst -name r966_0 -location {5874.200 16133.624} -status PLACED
place_inst -name b966 -location {5874.645 15963.600} -status PLACED
place_inst -name r967_0 -location {5727.358 16303.648} -status PLACED
place_inst -name b967 -location {5578.976 16303.648} -status PLACED
place_inst -name r968_0 -location {5578.976 16163.236} -status PLACED
place_inst -name r968_1 -location {5578.976 16022.824} -status PLACED
place_inst -name r968_2 -location {5578.976 15882.412} -status PLACED
place_inst -name b968 -location {5578.976 15742.000} -status PLACED
place_inst -name r969_0 -location {5578.976 16107.374} -status PLACED
place_inst -name b969 -location {5578.976 15911.100} -status PLACED
place_inst -name r970_0 -location {5578.976 16158.774} -status PLACED
place_inst -name b970 -location {5578.976 16013.900} -status PLACED
place_inst -name r971_0 -location {5546.720 16303.648} -status PLACED
place_inst -name b971 -location {5514.464 16303.648} -status PLACED
place_inst -name r972_0 -location {5514.464 16140.473} -status PLACED
place_inst -name r972_1 -location {5514.464 15977.299} -status PLACED
place_inst -name r972_2 -location {5514.464 15814.124} -status PLACED
place_inst -name r972_3 -location {5514.464 15650.949} -status PLACED
place_inst -name r972_4 -location {5514.464 15487.775} -status PLACED
place_inst -name b972 -location {5514.464 15324.600} -status PLACED
place_inst -name r973_0 -location {5421.568 16303.648} -status PLACED
place_inst -name b973 -location {5328.672 16303.648} -status PLACED
place_inst -name r974_0 -location {5328.672 16175.561} -status PLACED
place_inst -name r974_1 -location {5328.672 16047.474} -status PLACED
place_inst -name r974_2 -location {5328.672 15919.387} -status PLACED
place_inst -name b974 -location {5328.672 15791.300} -status PLACED
place_inst -name r975_0 -location {5328.672 16153.074} -status PLACED
place_inst -name b975 -location {5328.672 16002.500} -status PLACED
place_inst -name r976_0 -location {5306.784 16303.648} -status PLACED
place_inst -name b976 -location {5284.896 16303.648} -status PLACED
place_inst -name r977_0 -location {5284.896 16149.886} -status PLACED
place_inst -name r977_1 -location {5284.896 15996.124} -status PLACED
place_inst -name r977_2 -location {5284.896 15842.362} -status PLACED
place_inst -name b977 -location {5284.896 15688.600} -status PLACED
place_inst -name r978_0 -location {5225.088 16303.648} -status PLACED
place_inst -name b978 -location {5165.280 16303.648} -status PLACED
place_inst -name r979_0 -location {5165.280 16140.473} -status PLACED
place_inst -name r979_1 -location {5165.280 15977.299} -status PLACED
place_inst -name r979_2 -location {5165.280 15814.124} -status PLACED
place_inst -name r979_3 -location {5165.280 15650.949} -status PLACED
place_inst -name r979_4 -location {5165.280 15487.775} -status PLACED
place_inst -name b979 -location {5165.280 15324.600} -status PLACED
place_inst -name r980_0 -location {5165.280 16196.486} -status PLACED
place_inst -name r980_1 -location {5165.280 16089.324} -status PLACED
place_inst -name r980_2 -location {5165.280 15982.162} -status PLACED
place_inst -name b980 -location {5165.280 15875.000} -status PLACED
place_inst -name r981_0 -location {5093.552 16303.648} -status PLACED
place_inst -name b981 -location {5021.824 16303.648} -status PLACED
place_inst -name r982_0 -location {5021.824 16157.161} -status PLACED
place_inst -name r982_1 -location {5021.824 16010.674} -status PLACED
place_inst -name r982_2 -location {5021.824 15864.187} -status PLACED
place_inst -name b982 -location {5021.824 15717.700} -status PLACED
place_inst -name r983_0 -location {5021.824 16155.224} -status PLACED
place_inst -name b983 -location {5021.824 16006.800} -status PLACED
place_inst -name r984_0 -location {4942.096 16303.648} -status PLACED
place_inst -name b984 -location {4862.368 16303.648} -status PLACED
place_inst -name r985_0 -location {4862.368 16195.961} -status PLACED
place_inst -name r985_1 -location {4862.368 16088.274} -status PLACED
place_inst -name r985_2 -location {4862.368 15980.587} -status PLACED
place_inst -name b985 -location {4862.368 15872.900} -status PLACED
place_inst -name r986_0 -location {4827.712 16303.648} -status PLACED
place_inst -name b986 -location {4793.056 16303.648} -status PLACED
place_inst -name r987_0 -location {4793.056 16140.473} -status PLACED
place_inst -name r987_1 -location {4793.056 15977.299} -status PLACED
place_inst -name r987_2 -location {4793.056 15814.124} -status PLACED
place_inst -name r987_3 -location {4793.056 15650.949} -status PLACED
place_inst -name r987_4 -location {4793.056 15487.775} -status PLACED
place_inst -name b987 -location {4793.056 15324.600} -status PLACED
place_inst -name r988_0 -location {4747.958 16303.648} -status PLACED
place_inst -name b988 -location {4702.859 16303.648} -status PLACED
place_inst -name r989_0 -location {4702.859 16154.211} -status PLACED
place_inst -name r989_1 -location {4702.859 16004.774} -status PLACED
place_inst -name r989_2 -location {4702.859 15855.337} -status PLACED
place_inst -name b989 -location {4702.859 15705.900} -status PLACED
place_inst -name r990_0 -location {4702.859 16126.124} -status PLACED
place_inst -name b990 -location {4702.859 15948.600} -status PLACED
place_inst -name r991_0 -location {4702.859 16256.124} -status PLACED
place_inst -name b991 -location {4702.859 16208.600} -status PLACED
place_inst -name r992_0 -location {4656.912 16303.648} -status PLACED
place_inst -name b992 -location {4432.480 16303.648} -status PLACED
place_inst -name r993_0 -location {4432.572 16226.920} -status PLACED
place_inst -name r993_1 -location {4432.663 16226.920} -status PLACED
place_inst -name r993_2 -location {4433.320 15568.280} -status PLACED
place_inst -name r993_3 -location {4433.320 15568.280} -status PLACED
place_inst -name r993_4 -location {4432.938 15402.275} -status PLACED
place_inst -name b993 -location {4433.030 15222.000} -status PLACED
place_inst -name r994_0 -location {4432.299 16226.920} -status PLACED
place_inst -name r994_1 -location {4432.118 16226.920} -status PLACED
place_inst -name r994_2 -location {4431.320 15568.280} -status PLACED
place_inst -name r994_3 -location {4431.320 15568.280} -status PLACED
place_inst -name r994_4 -location {4431.320 15568.280} -status PLACED
place_inst -name b994 -location {4431.394 15443.600} -status PLACED
place_inst -name r995_0 -location {4239.480 16303.648} -status PLACED
place_inst -name b995 -location {4071.584 16303.648} -status PLACED
place_inst -name r996_0 -location {4071.584 16226.920} -status PLACED
place_inst -name r996_1 -location {4071.584 16226.920} -status PLACED
place_inst -name r996_2 -location {4071.584 15568.280} -status PLACED
place_inst -name r996_3 -location {4071.584 15568.280} -status PLACED
place_inst -name r996_4 -location {4071.584 15487.775} -status PLACED
place_inst -name b996 -location {4071.584 15324.600} -status PLACED
place_inst -name r997_0 -location {3891.488 16303.648} -status PLACED
place_inst -name b997 -location {3711.392 16303.648} -status PLACED
place_inst -name r998_0 -location {3711.392 16226.920} -status PLACED
place_inst -name r998_1 -location {3711.392 16226.920} -status PLACED
place_inst -name r998_2 -location {3711.392 15568.280} -status PLACED
place_inst -name r998_3 -location {3711.392 15568.280} -status PLACED
place_inst -name r998_4 -location {3711.392 15487.775} -status PLACED
place_inst -name b998 -location {3711.392 15324.600} -status PLACED
place_inst -name r999_0 -location {3530.784 16303.648} -status PLACED
place_inst -name b999 -location {3350.176 16303.648} -status PLACED
place_inst -name r1000_0 -location {3350.176 16226.920} -status PLACED
place_inst -name r1000_1 -location {3350.176 16226.920} -status PLACED
place_inst -name r1000_2 -location {3350.176 15568.280} -status PLACED
place_inst -name r1000_3 -location {3350.176 15568.280} -status PLACED
place_inst -name r1000_4 -location {3350.176 15487.775} -status PLACED
place_inst -name b1000 -location {3350.176 15324.600} -status PLACED
place_inst -name r1001_0 -location {3170.078 16303.648} -status PLACED
place_inst -name b1001 -location {2989.980 16303.648} -status PLACED
place_inst -name r1002_0 -location {2988.440 16123.373} -status PLACED
place_inst -name r1002_1 -location {2988.440 15943.099} -status PLACED
place_inst -name r1002_2 -location {2988.440 15762.824} -status PLACED
place_inst -name r1002_3 -location {2988.440 15582.549} -status PLACED
place_inst -name r1002_4 -location {2989.992 15402.275} -status PLACED
place_inst -name b1002 -location {2989.995 15222.000} -status PLACED
place_inst -name r1003_0 -location {2988.440 16160.307} -status PLACED
place_inst -name r1003_1 -location {2988.440 16016.965} -status PLACED
place_inst -name r1003_2 -location {2988.440 15873.624} -status PLACED
place_inst -name r1003_3 -location {2988.440 15730.283} -status PLACED
place_inst -name r1003_4 -location {2988.440 15586.941} -status PLACED
place_inst -name b1003 -location {2988.885 15443.600} -status PLACED
place_inst -name r1004_0 -location {2839.262 16303.648} -status PLACED
place_inst -name b1004 -location {2688.544 16303.648} -status PLACED
place_inst -name r1005_0 -location {2688.544 16122.490} -status PLACED
place_inst -name r1005_1 -location {2688.544 15941.332} -status PLACED
place_inst -name r1005_2 -location {2688.544 15760.174} -status PLACED
place_inst -name r1005_3 -location {2688.544 15579.016} -status PLACED
place_inst -name r1005_4 -location {2688.544 15397.858} -status PLACED
place_inst -name b1005 -location {2688.544 15216.700} -status PLACED
place_inst -name r1006_0 -location {2688.544 16159.440} -status PLACED
place_inst -name r1006_1 -location {2688.544 16015.232} -status PLACED
place_inst -name r1006_2 -location {2688.544 15871.024} -status PLACED
place_inst -name r1006_3 -location {2688.544 15726.816} -status PLACED
place_inst -name r1006_4 -location {2688.544 15582.608} -status PLACED
place_inst -name b1006 -location {2688.544 15438.400} -status PLACED
place_inst -name r1007_0 -location {2551.968 16303.648} -status PLACED
place_inst -name b1007 -location {2415.392 16303.648} -status PLACED
place_inst -name r1008_0 -location {2415.392 16158.990} -status PLACED
place_inst -name r1008_1 -location {2415.392 16014.332} -status PLACED
place_inst -name r1008_2 -location {2415.392 15869.674} -status PLACED
place_inst -name r1008_3 -location {2415.392 15725.016} -status PLACED
place_inst -name r1008_4 -location {2415.392 15580.358} -status PLACED
place_inst -name b1008 -location {2415.392 15435.700} -status PLACED
place_inst -name r1009_0 -location {2385.152 16303.648} -status PLACED
place_inst -name b1009 -location {2354.912 16303.648} -status PLACED
place_inst -name r1010_0 -location {2354.912 16122.040} -status PLACED
place_inst -name r1010_1 -location {2354.912 15940.432} -status PLACED
place_inst -name r1010_2 -location {2354.912 15758.824} -status PLACED
place_inst -name r1010_3 -location {2354.912 15577.216} -status PLACED
place_inst -name r1010_4 -location {2354.912 15395.608} -status PLACED
place_inst -name b1010 -location {2354.912 15214.000} -status PLACED
place_inst -name r1011_0 -location {2233.280 16303.648} -status PLACED
place_inst -name b1011 -location {2111.648 16303.648} -status PLACED
place_inst -name r1012_0 -location {2111.648 16163.190} -status PLACED
place_inst -name r1012_1 -location {2111.648 16022.732} -status PLACED
place_inst -name r1012_2 -location {2111.648 15882.274} -status PLACED
place_inst -name r1012_3 -location {2111.648 15741.816} -status PLACED
place_inst -name r1012_4 -location {2111.648 15601.358} -status PLACED
place_inst -name b1012 -location {2111.648 15460.900} -status PLACED
place_inst -name r1013_0 -location {2111.648 16147.961} -status PLACED
place_inst -name r1013_1 -location {2111.648 15992.274} -status PLACED
place_inst -name r1013_2 -location {2111.648 15836.587} -status PLACED
place_inst -name b1013 -location {2111.648 15680.900} -status PLACED
place_inst -name r1014_0 -location {2073.296 16303.648} -status PLACED
place_inst -name b1014 -location {2034.944 16303.648} -status PLACED
place_inst -name r1015_0 -location {2034.944 16126.257} -status PLACED
place_inst -name r1015_1 -location {2034.944 15948.865} -status PLACED
place_inst -name r1015_2 -location {2034.944 15771.474} -status PLACED
place_inst -name r1015_3 -location {2034.944 15594.083} -status PLACED
place_inst -name r1015_4 -location {2034.944 15416.691} -status PLACED
place_inst -name b1015 -location {2034.944 15239.300} -status PLACED
place_inst -name r1016_0 -location {2034.944 16120.624} -status PLACED
place_inst -name b1016 -location {2034.944 15937.600} -status PLACED
place_inst -name r1017_0 -location {2008.016 16303.648} -status PLACED
place_inst -name b1017 -location {1981.088 16303.648} -status PLACED
place_inst -name r1018_0 -location {1981.088 16130.836} -status PLACED
place_inst -name r1018_1 -location {1981.088 15958.024} -status PLACED
place_inst -name r1018_2 -location {1981.088 15785.212} -status PLACED
place_inst -name b1018 -location {1981.088 15612.400} -status PLACED
place_inst -name r1019_0 -location {1907.440 16303.648} -status PLACED
place_inst -name b1019 -location {1833.792 16303.648} -status PLACED
place_inst -name r1020_0 -location {1833.792 16141.807} -status PLACED
place_inst -name r1020_1 -location {1833.792 15979.965} -status PLACED
place_inst -name r1020_2 -location {1833.792 15818.124} -status PLACED
place_inst -name r1020_3 -location {1833.792 15656.283} -status PLACED
place_inst -name r1020_4 -location {1833.792 15494.441} -status PLACED
place_inst -name b1020 -location {1833.792 15332.600} -status PLACED
place_inst -name r1021_0 -location {1833.792 16135.836} -status PLACED
place_inst -name r1021_1 -location {1833.792 15968.024} -status PLACED
place_inst -name r1021_2 -location {1833.792 15800.212} -status PLACED
place_inst -name b1021 -location {1833.792 15632.400} -status PLACED
place_inst -name r1022_0 -location {1833.792 16107.924} -status PLACED
place_inst -name b1022 -location {1833.792 15912.200} -status PLACED
place_inst -name r1023_0 -location {1833.792 16256.124} -status PLACED
place_inst -name b1023 -location {1833.792 16208.600} -status PLACED
place_inst -name r1024_0 -location {1802.293 16303.648} -status PLACED
place_inst -name b1024 -location {1770.794 16303.648} -status PLACED
place_inst -name r1025_0 -location {1768.622 16127.123} -status PLACED
place_inst -name r1025_1 -location {1766.449 15950.599} -status PLACED
place_inst -name r1025_2 -location {1764.277 15774.074} -status PLACED
place_inst -name r1025_3 -location {1762.105 15597.549} -status PLACED
place_inst -name r1025_4 -location {1759.932 15421.025} -status PLACED
place_inst -name b1025 -location {1757.760 15244.500} -status PLACED
place_inst -name r1026_0 -location {1767.535 16121.036} -status PLACED
place_inst -name r1026_1 -location {1764.277 15938.424} -status PLACED
place_inst -name r1026_2 -location {1761.019 15755.812} -status PLACED
place_inst -name b1026 -location {1757.760 15573.200} -status PLACED
place_inst -name r1027_0 -location {1587.000 16303.648} -status PLACED
place_inst -name b1027 -location {1547.040 16303.648} -status PLACED
place_inst -name r1028_0 -location {8760.154 16153.642} -status PLACED
place_inst -name r1028_1 -location {8760.349 16003.636} -status PLACED
place_inst -name r1028_2 -location {8759.960 15853.630} -status PLACED
place_inst -name r1028_3 -location {8759.960 15703.624} -status PLACED
place_inst -name r1028_4 -location {8759.960 15553.618} -status PLACED
place_inst -name r1028_5 -location {8761.960 15403.612} -status PLACED
place_inst -name r1028_6 -location {8761.960 15253.606} -status PLACED
place_inst -name b1028 -location {8761.515 15103.600} -status PLACED
place_inst -name r1029_0 -location {8760.219 16142.973} -status PLACED
place_inst -name r1029_1 -location {8759.960 15982.299} -status PLACED
place_inst -name r1029_2 -location {8759.960 15821.624} -status PLACED
place_inst -name r1029_3 -location {8761.960 15660.949} -status PLACED
place_inst -name r1029_4 -location {8761.960 15500.275} -status PLACED
place_inst -name b1029 -location {8761.515 15339.600} -status PLACED
place_inst -name r1030_0 -location {8760.349 16113.836} -status PLACED
place_inst -name r1030_1 -location {8759.960 15924.024} -status PLACED
place_inst -name r1030_2 -location {8761.960 15734.212} -status PLACED
place_inst -name b1030 -location {8761.515 15544.400} -status PLACED
place_inst -name r1031_0 -location {8760.349 16181.661} -status PLACED
place_inst -name r1031_1 -location {8759.960 16059.674} -status PLACED
place_inst -name r1031_2 -location {8761.960 15937.687} -status PLACED
place_inst -name b1031 -location {8761.515 15815.700} -status PLACED
place_inst -name r1032_0 -location {8759.960 16207.824} -status PLACED
place_inst -name b1032 -location {8761.515 16112.000} -status PLACED
place_inst -name r1033_0 -location {8845.724 16303.648} -status PLACED
place_inst -name b1033 -location {8931.488 16303.648} -status PLACED
place_inst -name r1034_0 -location {8931.488 16138.417} -status PLACED
place_inst -name r1034_1 -location {8931.488 15973.186} -status PLACED
place_inst -name r1034_2 -location {8931.488 15807.955} -status PLACED
place_inst -name r1034_3 -location {8931.488 15642.724} -status PLACED
place_inst -name r1034_4 -location {8931.488 15477.493} -status PLACED
place_inst -name r1034_5 -location {8931.488 15298.680} -status PLACED
place_inst -name r1034_6 -location {8931.488 15108.600} -status PLACED
place_inst -name b1034 -location {8931.488 14981.800} -status PLACED
place_inst -name r1035_0 -location {8931.488 16142.742} -status PLACED
place_inst -name r1035_1 -location {8931.488 15981.836} -status PLACED
place_inst -name r1035_2 -location {8931.488 15820.930} -status PLACED
place_inst -name r1035_3 -location {8931.488 15660.024} -status PLACED
place_inst -name r1035_4 -location {8931.488 15499.118} -status PLACED
place_inst -name r1035_5 -location {8931.488 15298.680} -status PLACED
place_inst -name r1035_6 -location {8931.488 15191.904} -status PLACED
place_inst -name b1035 -location {8931.488 15016.400} -status PLACED
place_inst -name r1036_0 -location {9012.064 16303.648} -status PLACED
place_inst -name b1036 -location {9092.640 16303.648} -status PLACED
place_inst -name r1037_0 -location {9092.640 16138.811} -status PLACED
place_inst -name r1037_1 -location {9092.640 15973.974} -status PLACED
place_inst -name r1037_2 -location {9092.640 15809.137} -status PLACED
place_inst -name b1037 -location {9092.640 15644.300} -status PLACED
place_inst -name r1038_0 -location {9144.560 16303.648} -status PLACED
place_inst -name b1038 -location {9196.480 16303.648} -status PLACED
place_inst -name r1039_0 -location {9196.480 16138.417} -status PLACED
place_inst -name r1039_1 -location {9196.480 15973.186} -status PLACED
place_inst -name r1039_2 -location {9196.480 15807.955} -status PLACED
place_inst -name r1039_3 -location {9196.480 15642.724} -status PLACED
place_inst -name r1039_4 -location {9196.480 15477.493} -status PLACED
place_inst -name r1039_5 -location {9196.480 15312.262} -status PLACED
place_inst -name r1039_6 -location {9196.480 15134.520} -status PLACED
place_inst -name b1039 -location {9196.480 14981.800} -status PLACED
place_inst -name r1040_0 -location {9196.480 16142.742} -status PLACED
place_inst -name r1040_1 -location {9196.480 15981.836} -status PLACED
place_inst -name r1040_2 -location {9196.480 15820.930} -status PLACED
place_inst -name r1040_3 -location {9196.480 15660.024} -status PLACED
place_inst -name r1040_4 -location {9196.480 15499.118} -status PLACED
place_inst -name r1040_5 -location {9196.480 15338.212} -status PLACED
place_inst -name r1040_6 -location {9196.480 15217.824} -status PLACED
place_inst -name b1040 -location {9196.480 15016.400} -status PLACED
place_inst -name r1041_0 -location {9310.416 16303.648} -status PLACED
place_inst -name b1041 -location {9424.352 16303.648} -status PLACED
place_inst -name r1042_0 -location {9424.352 16138.811} -status PLACED
place_inst -name r1042_1 -location {9424.352 15973.974} -status PLACED
place_inst -name r1042_2 -location {9424.352 15809.137} -status PLACED
place_inst -name b1042 -location {9424.352 15644.300} -status PLACED
place_inst -name r1043_0 -location {9581.008 16303.648} -status PLACED
place_inst -name b1043 -location {9737.664 16303.648} -status PLACED
place_inst -name r1044_0 -location {9737.664 16138.811} -status PLACED
place_inst -name r1044_1 -location {9737.664 15973.974} -status PLACED
place_inst -name r1044_2 -location {9737.664 15809.137} -status PLACED
place_inst -name b1044 -location {9737.664 15644.300} -status PLACED
place_inst -name r1045_0 -location {9737.664 16104.124} -status PLACED
place_inst -name b1045 -location {9737.664 15904.600} -status PLACED
place_inst -name r1046_0 -location {9839.248 16303.648} -status PLACED
place_inst -name b1046 -location {9940.832 16303.648} -status PLACED
place_inst -name r1047_0 -location {9940.832 16199.011} -status PLACED
place_inst -name r1047_1 -location {9940.832 16094.374} -status PLACED
place_inst -name r1047_2 -location {9940.832 15989.737} -status PLACED
place_inst -name b1047 -location {9940.832 15885.100} -status PLACED
place_inst -name r1048_0 -location {9940.832 16256.174} -status PLACED
place_inst -name b1048 -location {9940.832 16208.700} -status PLACED
place_inst -name r1049_0 -location {10163.400 16303.648} -status PLACED
place_inst -name b1049 -location {10203.680 16303.648} -status PLACED
place_inst -name r1050_0 -location {10202.840 16151.707} -status PLACED
place_inst -name r1050_1 -location {10202.840 15999.765} -status PLACED
place_inst -name r1050_2 -location {10202.840 15847.824} -status PLACED
place_inst -name r1050_3 -location {10202.840 15695.883} -status PLACED
place_inst -name r1050_4 -location {10202.840 15543.941} -status PLACED
place_inst -name b1050 -location {10204.766 15392.000} -status PLACED
place_inst -name r1051_0 -location {10202.840 16153.807} -status PLACED
place_inst -name r1051_1 -location {10202.840 16003.965} -status PLACED
place_inst -name r1051_2 -location {10202.840 15854.124} -status PLACED
place_inst -name r1051_3 -location {10203.313 15704.283} -status PLACED
place_inst -name r1051_4 -location {10203.222 15554.441} -status PLACED
place_inst -name b1051 -location {10203.130 15404.600} -status PLACED
place_inst -name r1052_0 -location {10396.680 16303.648} -status PLACED
place_inst -name b1052 -location {10496.096 16303.648} -status PLACED
place_inst -name r1053_0 -location {10496.096 16226.920} -status PLACED
place_inst -name r1053_1 -location {10496.096 16226.920} -status PLACED
place_inst -name r1053_2 -location {10496.096 15481.880} -status PLACED
place_inst -name r1053_3 -location {10496.096 15481.880} -status PLACED
place_inst -name r1053_4 -location {10496.096 15481.880} -status PLACED
place_inst -name b1053 -location {10496.096 15404.600} -status PLACED
place_inst -name r1054_0 -location {10642.144 16303.648} -status PLACED
place_inst -name b1054 -location {10788.192 16303.648} -status PLACED
place_inst -name r1055_0 -location {10788.192 16226.920} -status PLACED
place_inst -name r1055_1 -location {10788.192 16226.920} -status PLACED
place_inst -name r1055_2 -location {10788.192 16226.920} -status PLACED
place_inst -name r1055_3 -location {10788.192 15481.880} -status PLACED
place_inst -name r1055_4 -location {10788.192 15481.880} -status PLACED
place_inst -name b1055 -location {10788.192 15452.100} -status PLACED
place_inst -name r1056_0 -location {10856.992 16303.648} -status PLACED
place_inst -name b1056 -location {10925.792 16303.648} -status PLACED
place_inst -name r1057_0 -location {10925.792 16226.920} -status PLACED
place_inst -name r1057_1 -location {10925.792 16226.920} -status PLACED
place_inst -name r1057_2 -location {10925.792 15481.880} -status PLACED
place_inst -name r1057_3 -location {10925.792 15481.880} -status PLACED
place_inst -name r1057_4 -location {10925.792 15481.880} -status PLACED
place_inst -name b1057 -location {10925.792 15404.600} -status PLACED
place_inst -name r1058_0 -location {11105.888 16303.648} -status PLACED
place_inst -name b1058 -location {11285.984 16303.648} -status PLACED
place_inst -name r1059_0 -location {11285.984 16226.920} -status PLACED
place_inst -name r1059_1 -location {11285.984 16226.920} -status PLACED
place_inst -name r1059_2 -location {11285.984 15481.880} -status PLACED
place_inst -name r1059_3 -location {11285.984 15481.880} -status PLACED
place_inst -name r1059_4 -location {11285.984 15481.880} -status PLACED
place_inst -name b1059 -location {11285.984 15404.600} -status PLACED
place_inst -name r1060_0 -location {11466.082 16303.648} -status PLACED
place_inst -name b1060 -location {11646.180 16303.648} -status PLACED
place_inst -name r1061_0 -location {11647.720 16153.807} -status PLACED
place_inst -name r1061_1 -location {11647.720 16003.965} -status PLACED
place_inst -name r1061_2 -location {11647.720 15854.124} -status PLACED
place_inst -name r1061_3 -location {11647.720 15704.283} -status PLACED
place_inst -name r1061_4 -location {11647.720 15554.441} -status PLACED
place_inst -name b1061 -location {11647.275 15404.600} -status PLACED
place_inst -name r1062_0 -location {11647.720 16158.707} -status PLACED
place_inst -name r1062_1 -location {11647.720 16013.765} -status PLACED
place_inst -name r1062_2 -location {11647.720 15868.824} -status PLACED
place_inst -name r1062_3 -location {11647.720 15723.883} -status PLACED
place_inst -name r1062_4 -location {11647.720 15578.941} -status PLACED
place_inst -name b1062 -location {11646.165 15434.000} -status PLACED
place_inst -name r1063_0 -location {11825.817 16303.648} -status PLACED
place_inst -name r1063_1 -location {12005.453 16303.648} -status PLACED
place_inst -name r1063_2 -location {12185.090 16303.648} -status PLACED
place_inst -name r1063_3 -location {12364.727 16303.648} -status PLACED
place_inst -name r1063_4 -location {12544.363 16303.648} -status PLACED
place_inst -name b1063 -location {12724.000 16303.648} -status PLACED
place_inst -name r1064_0 -location {12724.000 16256.174} -status PLACED
place_inst -name b1064 -location {12724.000 16208.700} -status PLACED
place_inst -name r1065_0 -location {12865.008 16303.648} -status PLACED
place_inst -name b1065 -location {13089.440 16303.648} -status PLACED
place_inst -name r1066_0 -location {13088.600 16140.473} -status PLACED
place_inst -name r1066_1 -location {13088.600 15977.299} -status PLACED
place_inst -name r1066_2 -location {13088.600 15814.124} -status PLACED
place_inst -name r1066_3 -location {13089.073 15650.949} -status PLACED
place_inst -name r1066_4 -location {13088.982 15487.775} -status PLACED
place_inst -name b1066 -location {13088.890 15324.600} -status PLACED
place_inst -name r1067_0 -location {13088.600 16160.307} -status PLACED
place_inst -name r1067_1 -location {13088.600 16016.965} -status PLACED
place_inst -name r1067_2 -location {13088.600 15873.624} -status PLACED
place_inst -name r1067_3 -location {13088.600 15730.283} -status PLACED
place_inst -name r1067_4 -location {13088.600 15586.941} -status PLACED
place_inst -name b1067 -location {13090.526 15443.600} -status PLACED
place_inst -name r1068_0 -location {13282.440 16303.648} -status PLACED
place_inst -name b1068 -location {13450.336 16303.648} -status PLACED
place_inst -name r1069_0 -location {13450.336 16226.920} -status PLACED
place_inst -name r1069_1 -location {13450.336 16226.920} -status PLACED
place_inst -name r1069_2 -location {13450.336 15568.280} -status PLACED
place_inst -name r1069_3 -location {13450.336 15568.280} -status PLACED
place_inst -name r1069_4 -location {13450.336 15487.775} -status PLACED
place_inst -name b1069 -location {13450.336 15324.600} -status PLACED
place_inst -name r1070_0 -location {13630.432 16303.648} -status PLACED
place_inst -name b1070 -location {13810.528 16303.648} -status PLACED
place_inst -name r1071_0 -location {13810.528 16226.920} -status PLACED
place_inst -name r1071_1 -location {13810.528 16226.920} -status PLACED
place_inst -name r1071_2 -location {13810.528 15568.280} -status PLACED
place_inst -name r1071_3 -location {13810.528 15568.280} -status PLACED
place_inst -name r1071_4 -location {13810.528 15487.775} -status PLACED
place_inst -name b1071 -location {13810.528 15324.600} -status PLACED
place_inst -name r1072_0 -location {13991.136 16303.648} -status PLACED
place_inst -name b1072 -location {14171.744 16303.648} -status PLACED
place_inst -name r1073_0 -location {14171.744 16226.920} -status PLACED
place_inst -name r1073_1 -location {14171.744 16226.920} -status PLACED
place_inst -name r1073_2 -location {14171.744 15568.280} -status PLACED
place_inst -name r1073_3 -location {14171.744 15568.280} -status PLACED
place_inst -name r1073_4 -location {14171.744 15487.775} -status PLACED
place_inst -name b1073 -location {14171.744 15324.600} -status PLACED
place_inst -name r1074_0 -location {14351.842 16303.648} -status PLACED
place_inst -name b1074 -location {14531.940 16303.648} -status PLACED
place_inst -name r1075_0 -location {14533.480 16123.373} -status PLACED
place_inst -name r1075_1 -location {14533.480 15943.099} -status PLACED
place_inst -name r1075_2 -location {14533.480 15762.824} -status PLACED
place_inst -name r1075_3 -location {14533.480 15582.549} -status PLACED
place_inst -name r1075_4 -location {14531.927 15402.275} -status PLACED
place_inst -name b1075 -location {14531.925 15222.000} -status PLACED
place_inst -name r1076_0 -location {14533.480 16160.307} -status PLACED
place_inst -name r1076_1 -location {14533.480 16016.965} -status PLACED
place_inst -name r1076_2 -location {14533.480 15873.624} -status PLACED
place_inst -name r1076_3 -location {14533.480 15730.283} -status PLACED
place_inst -name r1076_4 -location {14533.480 15586.941} -status PLACED
place_inst -name b1076 -location {14533.035 15443.600} -status PLACED
place_inst -name r1077_0 -location {14682.658 16303.648} -status PLACED
place_inst -name b1077 -location {14833.376 16303.648} -status PLACED
place_inst -name r1078_0 -location {14833.376 16122.490} -status PLACED
place_inst -name r1078_1 -location {14833.376 15941.332} -status PLACED
place_inst -name r1078_2 -location {14833.376 15760.174} -status PLACED
place_inst -name r1078_3 -location {14833.376 15579.016} -status PLACED
place_inst -name r1078_4 -location {14833.376 15397.858} -status PLACED
place_inst -name b1078 -location {14833.376 15216.700} -status PLACED
place_inst -name r1079_0 -location {14833.376 16159.440} -status PLACED
place_inst -name r1079_1 -location {14833.376 16015.232} -status PLACED
place_inst -name r1079_2 -location {14833.376 15871.024} -status PLACED
place_inst -name r1079_3 -location {14833.376 15726.816} -status PLACED
place_inst -name r1079_4 -location {14833.376 15582.608} -status PLACED
place_inst -name b1079 -location {14833.376 15438.400} -status PLACED
place_inst -name r1080_0 -location {14969.952 16303.648} -status PLACED
place_inst -name b1080 -location {15106.528 16303.648} -status PLACED
place_inst -name r1081_0 -location {15106.528 16158.990} -status PLACED
place_inst -name r1081_1 -location {15106.528 16014.332} -status PLACED
place_inst -name r1081_2 -location {15106.528 15869.674} -status PLACED
place_inst -name r1081_3 -location {15106.528 15725.016} -status PLACED
place_inst -name r1081_4 -location {15106.528 15580.358} -status PLACED
place_inst -name b1081 -location {15106.528 15435.700} -status PLACED
place_inst -name r1082_0 -location {15136.768 16303.648} -status PLACED
place_inst -name b1082 -location {15167.008 16303.648} -status PLACED
place_inst -name r1083_0 -location {15167.008 16122.040} -status PLACED
place_inst -name r1083_1 -location {15167.008 15940.432} -status PLACED
place_inst -name r1083_2 -location {15167.008 15758.824} -status PLACED
place_inst -name r1083_3 -location {15167.008 15577.216} -status PLACED
place_inst -name r1083_4 -location {15167.008 15395.608} -status PLACED
place_inst -name b1083 -location {15167.008 15214.000} -status PLACED
place_inst -name r1084_0 -location {15288.640 16303.648} -status PLACED
place_inst -name b1084 -location {15410.272 16303.648} -status PLACED
place_inst -name r1085_0 -location {15410.272 16163.190} -status PLACED
place_inst -name r1085_1 -location {15410.272 16022.732} -status PLACED
place_inst -name r1085_2 -location {15410.272 15882.274} -status PLACED
place_inst -name r1085_3 -location {15410.272 15741.816} -status PLACED
place_inst -name r1085_4 -location {15410.272 15601.358} -status PLACED
place_inst -name b1085 -location {15410.272 15460.900} -status PLACED
place_inst -name r1086_0 -location {15410.272 16147.961} -status PLACED
place_inst -name r1086_1 -location {15410.272 15992.274} -status PLACED
place_inst -name r1086_2 -location {15410.272 15836.587} -status PLACED
place_inst -name b1086 -location {15410.272 15680.900} -status PLACED
place_inst -name r1087_0 -location {15448.624 16303.648} -status PLACED
place_inst -name b1087 -location {15486.976 16303.648} -status PLACED
place_inst -name r1088_0 -location {15486.976 16126.257} -status PLACED
place_inst -name r1088_1 -location {15486.976 15948.865} -status PLACED
place_inst -name r1088_2 -location {15486.976 15771.474} -status PLACED
place_inst -name r1088_3 -location {15486.976 15594.083} -status PLACED
place_inst -name r1088_4 -location {15486.976 15416.691} -status PLACED
place_inst -name b1088 -location {15486.976 15239.300} -status PLACED
place_inst -name r1089_0 -location {15486.976 16120.624} -status PLACED
place_inst -name b1089 -location {15486.976 15937.600} -status PLACED
place_inst -name r1090_0 -location {15513.904 16303.648} -status PLACED
place_inst -name b1090 -location {15540.832 16303.648} -status PLACED
place_inst -name r1091_0 -location {15540.832 16130.836} -status PLACED
place_inst -name r1091_1 -location {15540.832 15958.024} -status PLACED
place_inst -name r1091_2 -location {15540.832 15785.212} -status PLACED
place_inst -name b1091 -location {15540.832 15612.400} -status PLACED
place_inst -name r1092_0 -location {15614.480 16303.648} -status PLACED
place_inst -name b1092 -location {15688.128 16303.648} -status PLACED
place_inst -name r1093_0 -location {15688.128 16141.807} -status PLACED
place_inst -name r1093_1 -location {15688.128 15979.965} -status PLACED
place_inst -name r1093_2 -location {15688.128 15818.124} -status PLACED
place_inst -name r1093_3 -location {15688.128 15656.283} -status PLACED
place_inst -name r1093_4 -location {15688.128 15494.441} -status PLACED
place_inst -name b1093 -location {15688.128 15332.600} -status PLACED
place_inst -name r1094_0 -location {15688.128 16135.836} -status PLACED
place_inst -name r1094_1 -location {15688.128 15968.024} -status PLACED
place_inst -name r1094_2 -location {15688.128 15800.212} -status PLACED
place_inst -name b1094 -location {15688.128 15632.400} -status PLACED
place_inst -name r1095_0 -location {15688.128 16107.924} -status PLACED
place_inst -name b1095 -location {15688.128 15912.200} -status PLACED
place_inst -name r1096_0 -location {15688.128 16256.124} -status PLACED
place_inst -name b1096 -location {15688.128 16208.600} -status PLACED
place_inst -name r1097_0 -location {15719.627 16303.648} -status PLACED
place_inst -name b1097 -location {15751.126 16303.648} -status PLACED
place_inst -name r1098_0 -location {15753.298 16127.123} -status PLACED
place_inst -name r1098_1 -location {15755.471 15950.599} -status PLACED
place_inst -name r1098_2 -location {15757.643 15774.074} -status PLACED
place_inst -name r1098_3 -location {15759.815 15597.549} -status PLACED
place_inst -name r1098_4 -location {15761.988 15421.025} -status PLACED
place_inst -name b1098 -location {15764.160 15244.500} -status PLACED
place_inst -name r1099_0 -location {15754.385 16121.036} -status PLACED
place_inst -name r1099_1 -location {15757.643 15938.424} -status PLACED
place_inst -name r1099_2 -location {15760.901 15755.812} -status PLACED
place_inst -name b1099 -location {15764.160 15573.200} -status PLACED
place_inst -name r1100_0 -location {15934.920 16303.648} -status PLACED
place_inst -name b1100 -location {15974.880 16303.648} -status PLACED
set_wire_rc -signal -resistance 4.335802e-03 -capacitance 1.082436e-01
set_wire_rc -clock -resistance 4.335802e-03 -capacitance 1.082436e-01
estimate_parasitics -placement
create_clock -name vclk -period 833.333
set_driving_cell -lib_cell BUFx24_ASAP7_75t_R -pin Y [get_ports root]
set_input_delay 0 -clock vclk [get_ports root]
set_load 3.0 [all_outputs]
set_output_delay 0 -clock vclk [all_outputs]
set ot_odd [dict create b0_r 1 r1000_0 1 r1000_2 1 r1000_4 1 r1001_0 1 r1002_0 1 r1002_2 1 r1002_4 1 r1003_0 1 r1003_2 1 r1003_4 1 r1004_0 1 r1005_0 1 r1005_2 1 r1005_4 1 r1006_0 1 r1006_2 1 r1006_4 1 r1007_0 1 r1008_0 1 r1008_2 1 r1008_4 1 r1009_0 1 r100_0 1 r100_2 1 r100_4 1 r1010_0 1 r1010_2 1 r1010_4 1 r1011_0 1 r1012_0 1 r1012_2 1 r1012_4 1 r1013_0 1 r1013_2 1 r1014_0 1 r1015_0 1 r1015_2 1 r1015_4 1 r1016_0 1 r1017_0 1 r1018_0 1 r1018_2 1 r1019_0 1 r101_0 1 r1020_0 1 r1020_2 1 r1020_4 1 r1021_0 1 r1021_2 1 r1022_0 1 r1023_0 1 r1024_0 1 r1025_0 1 r1025_2 1 r1025_4 1 r1026_0 1 r1026_2 1 r1027_0 1 r1028_0 1 r1028_2 1 r1028_4 1 r1028_6 1 r1029_0 1 r1029_2 1 r1029_4 1 r102_0 1 r102_2 1 r102_4 1 r1030_0 1 r1030_2 1 r1031_0 1 r1031_2 1 r1032_0 1 r1033_0 1 r1034_0 1 r1034_2 1 r1034_4 1 r1034_6 1 r1035_0 1 r1035_2 1 r1035_4 1 r1035_6 1 r1036_0 1 r1037_0 1 r1037_2 1 r1038_0 1 r1039_0 1 r1039_2 1 r1039_4 1 r1039_6 1 r103_0 1 r1040_0 1 r1040_2 1 r1040_4 1 r1040_6 1 r1041_0 1 r1042_0 1 r1042_2 1 r1043_0 1 r1044_0 1 r1044_2 1 r1045_0 1 r1046_0 1 r1047_0 1 r1047_2 1 r1048_0 1 r1049_0 1 r104_0 1 r1050_0 1 r1050_2 1 r1050_4 1 r1051_0 1 r1051_2 1 r1051_4 1 r1052_0 1 r1053_0 1 r1053_2 1 r1053_4 1 r1054_0 1 r1055_0 1 r1055_2 1 r1055_4 1 r1056_0 1 r1057_0 1 r1057_2 1 r1057_4 1 r1058_0 1 r1059_0 1 r1059_2 1 r1059_4 1 r105_0 1 r105_2 1 r105_4 1 r1060_0 1 r1061_0 1 r1061_2 1 r1061_4 1 r1062_0 1 r1062_2 1 r1062_4 1 r1063_0 1 r1063_2 1 r1063_4 1 r1064_0 1 r1065_0 1 r1066_0 1 r1066_2 1 r1066_4 1 r1067_0 1 r1067_2 1 r1067_4 1 r1068_0 1 r1069_0 1 r1069_2 1 r1069_4 1 r106_0 1 r1070_0 1 r1071_0 1 r1071_2 1 r1071_4 1 r1072_0 1 r1073_0 1 r1073_2 1 r1073_4 1 r1074_0 1 r1075_0 1 r1075_2 1 r1075_4 1 r1076_0 1 r1076_2 1 r1076_4 1 r1077_0 1 r1078_0 1 r1078_2 1 r1078_4 1 r1079_0 1 r1079_2 1 r1079_4 1 r107_0 1 r107_2 1 r107_4 1 r1080_0 1 r1081_0 1 r1081_2 1 r1081_4 1 r1082_0 1 r1083_0 1 r1083_2 1 r1083_4 1 r1084_0 1 r1085_0 1 r1085_2 1 r1085_4 1 r1086_0 1 r1086_2 1 r1087_0 1 r1088_0 1 r1088_2 1 r1088_4 1 r1089_0 1 r108_0 1 r108_2 1 r108_4 1 r1090_0 1 r1091_0 1 r1091_2 1 r1092_0 1 r1093_0 1 r1093_2 1 r1093_4 1 r1094_0 1 r1094_2 1 r1095_0 1 r1096_0 1 r1097_0 1 r1098_0 1 r1098_2 1 r1098_4 1 r1099_0 1 r1099_2 1 r109_0 1 r10_0 1 r10_2 1 r1100_0 1 r110_0 1 r110_2 1 r110_4 1 r111_0 1 r112_0 1 r112_2 1 r112_4 1 r113_0 1 r114_0 1 r114_2 1 r114_4 1 r115_0 1 r116_0 1 r116_2 1 r116_4 1 r117_0 1 r118_0 1 r118_2 1 r118_4 1 r119_0 1 r119_2 1 r119_4 1 r11_0 1 r11_2 1 r120_0 1 r120_2 1 r120_4 1 r121_0 1 r122_0 1 r123_0 1 r123_2 1 r123_4 1 r124_0 1 r124_2 1 r124_4 1 r125_0 1 r126_0 1 r126_2 1 r126_4 1 r127_0 1 r128_0 1 r128_2 1 r128_4 1 r129_0 1 r12_0 1 r12_2 1 r130_0 1 r130_2 1 r130_4 1 r131_0 1 r132_0 1 r132_2 1 r132_4 1 r133_0 1 r133_2 1 r133_4 1 r134_0 1 r135_0 1 r135_2 1 r135_4 1 r136_0 1 r136_2 1 r136_4 1 r137_0 1 r138_0 1 r138_2 1 r138_4 1 r139_0 1 r13_0 1 r13_2 1 r13_4 1 r140_0 1 r140_2 1 r140_4 1 r141_0 1 r142_0 1 r142_2 1 r143_0 1 r143_2 1 r143_4 1 r144_0 1 r145_0 1 r146_0 1 r146_2 1 r146_4 1 r147_0 1 r148_0 1 r148_2 1 r149_0 1 r14_0 1 r150_0 1 r151_0 1 r152_0 1 r152_2 1 r153_0 1 r153_2 1 r153_4 1 r154_0 1 r155_0 1 r155_2 1 r156_0 1 r156_2 1 r156_4 1 r157_0 1 r158_0 1 r159_0 1 r159_2 1 r159_4 1 r15_0 1 r15_2 1 r15_4 1 r160_0 1 r161_0 1 r161_2 1 r161_4 1 r162_0 1 r163_0 1 r163_2 1 r163_4 1 r164_0 1 r165_0 1 r165_2 1 r166_0 1 r166_2 1 r166_4 1 r167_0 1 r168_0 1 r168_2 1 r169_0 1 r169_2 1 r169_4 1 r16_0 1 r16_10 1 r16_12 1 r16_14 1 r16_16 1 r16_18 1 r16_2 1 r16_20 1 r16_22 1 r16_24 1 r16_4 1 r16_6 1 r16_8 1 r170_0 1 r171_0 1 r171_2 1 r172_0 1 r172_2 1 r172_4 1 r173_0 1 r174_0 1 r174_2 1 r175_0 1 r175_2 1 r175_4 1 r176_0 1 r177_0 1 r177_2 1 r178_0 1 r178_2 1 r178_4 1 r179_0 1 r17_0 1 r17_2 1 r17_4 1 r17_6 1 r17_8 1 r180_0 1 r180_2 1 r181_0 1 r181_2 1 r181_4 1 r182_0 1 r183_0 1 r183_2 1 r184_0 1 r184_2 1 r184_4 1 r185_0 1 r186_0 1 r186_2 1 r187_0 1 r187_2 1 r187_4 1 r188_0 1 r189_0 1 r189_2 1 r18_0 1 r18_2 1 r190_0 1 r190_2 1 r190_4 1 r191_0 1 r192_0 1 r192_2 1 r193_0 1 r193_2 1 r193_4 1 r194_0 1 r195_0 1 r196_0 1 r197_0 1 r198_0 1 r198_2 1 r198_4 1 r199_0 1 r199_2 1 r19_0 1 r19_2 1 r1_0 1 r1_10 1 r1_12 1 r1_14 1 r1_2 1 r1_4 1 r1_6 1 r1_8 1 r200_0 1 r200_2 1 r200_4 1 r201_0 1 r201_2 1 r201_4 1 r202_0 1 r202_2 1 r202_4 1 r203_0 1 r204_0 1 r205_0 1 r206_0 1 r207_0 1 r208_0 1 r208_2 1 r209_0 1 r20_0 1 r20_2 1 r20_4 1 r210_0 1 r210_2 1 r210_4 1 r211_0 1 r211_2 1 r211_4 1 r212_0 1 r212_2 1 r213_0 1 r213_2 1 r214_0 1 r214_2 1 r215_0 1 r216_0 1 r217_0 1 r218_0 1 r219_0 1 r21_0 1 r21_2 1 r21_4 1 r21_6 1 r220_0 1 r220_2 1 r220_4 1 r221_0 1 r221_2 1 r221_4 1 r222_0 1 r222_2 1 r223_0 1 r224_0 1 r225_0 1 r225_2 1 r226_0 1 r227_0 1 r227_2 1 r227_4 1 r228_0 1 r229_0 1 r229_2 1 r229_4 1 r22_0 1 r22_2 1 r22_4 1 r22_6 1 r22_8 1 r230_0 1 r231_0 1 r231_2 1 r231_4 1 r232_0 1 r233_0 1 r233_2 1 r234_0 1 r234_2 1 r234_4 1 r235_0 1 r236_0 1 r236_2 1 r237_0 1 r237_2 1 r237_4 1 r238_0 1 r239_0 1 r239_2 1 r23_0 1 r23_2 1 r240_0 1 r240_2 1 r240_4 1 r241_0 1 r242_0 1 r242_2 1 r243_0 1 r243_2 1 r243_4 1 r244_0 1 r245_0 1 r245_2 1 r246_0 1 r246_2 1 r246_4 1 r247_0 1 r248_0 1 r248_2 1 r249_0 1 r249_2 1 r249_4 1 r24_0 1 r250_0 1 r251_0 1 r251_2 1 r252_0 1 r252_2 1 r252_4 1 r253_0 1 r254_0 1 r254_2 1 r255_0 1 r255_2 1 r255_4 1 r256_0 1 r257_0 1 r257_2 1 r258_0 1 r258_2 1 r258_4 1 r259_0 1 r25_0 1 r25_2 1 r25_4 1 r25_6 1 r25_8 1 r260_0 1 r260_2 1 r261_0 1 r261_2 1 r261_4 1 r262_0 1 r263_0 1 r264_0 1 r265_0 1 r266_0 1 r266_2 1 r266_4 1 r267_0 1 r267_2 1 r268_0 1 r269_0 1 r26_0 1 r26_2 1 r270_0 1 r271_0 1 r272_0 1 r272_2 1 r273_0 1 r274_0 1 r274_2 1 r275_0 1 r276_0 1 r276_2 1 r277_0 1 r278_0 1 r278_2 1 r279_0 1 r27_0 1 r27_2 1 r27_4 1 r280_0 1 r280_2 1 r281_0 1 r282_0 1 r282_2 1 r283_0 1 r284_0 1 r284_2 1 r285_0 1 r286_0 1 r286_2 1 r287_0 1 r288_0 1 r288_2 1 r289_0 1 r28_0 1 r290_0 1 r290_2 1 r291_0 1 r292_0 1 r292_2 1 r293_0 1 r294_0 1 r294_2 1 r295_0 1 r296_0 1 r297_0 1 r297_2 1 r298_0 1 r299_0 1 r29_0 1 r2_0 1 r2_10 1 r2_2 1 r2_4 1 r2_6 1 r2_8 1 r300_0 1 r301_0 1 r302_0 1 r303_0 1 r304_0 1 r305_0 1 r305_2 1 r306_0 1 r307_0 1 r308_0 1 r309_0 1 r30_0 1 r30_2 1 r310_0 1 r311_0 1 r312_0 1 r313_0 1 r313_2 1 r314_0 1 r315_0 1 r315_2 1 r316_0 1 r317_0 1 r317_2 1 r318_0 1 r319_0 1 r319_2 1 r31_0 1 r31_2 1 r31_4 1 r320_0 1 r321_0 1 r321_2 1 r322_0 1 r323_0 1 r323_2 1 r324_0 1 r325_0 1 r325_2 1 r326_0 1 r327_0 1 r327_2 1 r328_0 1 r329_0 1 r329_2 1 r32_0 1 r330_0 1 r331_0 1 r331_2 1 r332_0 1 r333_0 1 r333_2 1 r334_0 1 r335_0 1 r335_2 1 r336_0 1 r337_0 1 r337_2 1 r338_0 1 r339_0 1 r339_2 1 r33_0 1 r33_2 1 r340_0 1 r341_0 1 r341_2 1 r342_0 1 r343_0 1 r343_2 1 r344_0 1 r345_0 1 r345_2 1 r346_0 1 r347_0 1 r347_2 1 r348_0 1 r349_0 1 r349_2 1 r34_0 1 r350_0 1 r351_0 1 r351_2 1 r352_0 1 r353_0 1 r353_2 1 r354_0 1 r355_0 1 r355_2 1 r356_0 1 r357_0 1 r357_2 1 r358_0 1 r359_0 1 r35_0 1 r360_0 1 r361_0 1 r362_0 1 r363_0 1 r363_2 1 r364_0 1 r365_0 1 r366_0 1 r367_0 1 r368_0 1 r368_2 1 r369_0 1 r36_0 1 r370_0 1 r370_2 1 r371_0 1 r372_0 1 r373_0 1 r374_0 1 r375_0 1 r376_0 1 r377_0 1 r378_0 1 r378_2 1 r379_0 1 r37_0 1 r380_0 1 r380_2 1 r381_0 1 r382_0 1 r383_0 1 r384_0 1 r384_2 1 r385_0 1 r386_0 1 r386_2 1 r387_0 1 r388_0 1 r388_2 1 r389_0 1 r38_0 1 r38_2 1 r38_4 1 r390_0 1 r390_2 1 r391_0 1 r392_0 1 r392_2 1 r393_0 1 r394_0 1 r394_2 1 r395_0 1 r396_0 1 r396_2 1 r397_0 1 r398_0 1 r398_2 1 r399_0 1 r39_0 1 r3_0 1 r3_2 1 r3_4 1 r400_0 1 r400_2 1 r401_0 1 r402_0 1 r402_2 1 r403_0 1 r404_0 1 r404_2 1 r405_0 1 r406_0 1 r407_0 1 r408_0 1 r409_0 1 r40_0 1 r40_2 1 r40_4 1 r410_0 1 r411_0 1 r412_0 1 r412_2 1 r413_0 1 r414_0 1 r414_2 1 r415_0 1 r416_0 1 r416_2 1 r417_0 1 r418_0 1 r418_2 1 r419_0 1 r41_0 1 r41_2 1 r41_4 1 r420_0 1 r420_2 1 r421_0 1 r422_0 1 r422_2 1 r423_0 1 r424_0 1 r424_2 1 r425_0 1 r426_0 1 r426_2 1 r427_0 1 r428_0 1 r428_2 1 r429_0 1 r42_0 1 r430_0 1 r430_2 1 r431_0 1 r432_0 1 r432_2 1 r433_0 1 r434_0 1 r434_2 1 r435_0 1 r436_0 1 r437_0 1 r437_2 1 r438_0 1 r439_0 1 r43_0 1 r43_2 1 r43_4 1 r440_0 1 r441_0 1 r442_0 1 r443_0 1 r444_0 1 r445_0 1 r445_2 1 r446_0 1 r447_0 1 r448_0 1 r449_0 1 r44_0 1 r450_0 1 r451_0 1 r452_0 1 r453_0 1 r453_2 1 r454_0 1 r455_0 1 r455_2 1 r456_0 1 r457_0 1 r457_2 1 r458_0 1 r459_0 1 r459_2 1 r45_0 1 r45_2 1 r45_4 1 r460_0 1 r461_0 1 r461_2 1 r462_0 1 r463_0 1 r463_2 1 r464_0 1 r465_0 1 r465_2 1 r466_0 1 r467_0 1 r467_2 1 r468_0 1 r469_0 1 r469_2 1 r46_0 1 r470_0 1 r471_0 1 r471_2 1 r472_0 1 r473_0 1 r473_2 1 r474_0 1 r475_0 1 r475_2 1 r476_0 1 r477_0 1 r477_2 1 r478_0 1 r479_0 1 r479_2 1 r47_0 1 r47_2 1 r47_4 1 r480_0 1 r481_0 1 r481_2 1 r482_0 1 r483_0 1 r483_2 1 r484_0 1 r485_0 1 r485_2 1 r486_0 1 r487_0 1 r487_2 1 r488_0 1 r489_0 1 r489_2 1 r48_0 1 r490_0 1 r491_0 1 r491_2 1 r492_0 1 r493_0 1 r493_2 1 r494_0 1 r495_0 1 r495_2 1 r496_0 1 r497_0 1 r497_2 1 r498_0 1 r499_0 1 r49_0 1 r49_2 1 r49_4 1 r4_0 1 r500_0 1 r501_0 1 r502_0 1 r503_0 1 r503_2 1 r504_0 1 r505_0 1 r506_0 1 r507_0 1 r508_0 1 r508_2 1 r509_0 1 r50_0 1 r510_0 1 r510_2 1 r511_0 1 r512_0 1 r513_0 1 r514_0 1 r515_0 1 r516_0 1 r517_0 1 r518_0 1 r518_2 1 r519_0 1 r51_0 1 r51_2 1 r51_4 1 r520_0 1 r520_2 1 r521_0 1 r522_0 1 r523_0 1 r524_0 1 r524_2 1 r525_0 1 r526_0 1 r526_2 1 r527_0 1 r528_0 1 r528_2 1 r529_0 1 r52_0 1 r52_2 1 r52_4 1 r530_0 1 r530_2 1 r531_0 1 r532_0 1 r532_2 1 r533_0 1 r534_0 1 r534_2 1 r535_0 1 r536_0 1 r536_2 1 r537_0 1 r538_0 1 r538_2 1 r539_0 1 r53_0 1 r53_2 1 r53_4 1 r540_0 1 r540_2 1 r541_0 1 r542_0 1 r542_2 1 r543_0 1 r544_0 1 r544_2 1 r545_0 1 r546_0 1 r547_0 1 r548_0 1 r549_0 1 r54_0 1 r550_0 1 r551_0 1 r552_0 1 r552_2 1 r553_0 1 r554_0 1 r554_2 1 r555_0 1 r556_0 1 r556_2 1 r557_0 1 r558_0 1 r558_2 1 r559_0 1 r55_0 1 r560_0 1 r560_2 1 r561_0 1 r562_0 1 r562_2 1 r563_0 1 r564_0 1 r564_2 1 r565_0 1 r566_0 1 r566_2 1 r567_0 1 r568_0 1 r568_2 1 r569_0 1 r56_0 1 r56_2 1 r56_4 1 r570_0 1 r570_2 1 r571_0 1 r572_0 1 r572_2 1 r573_0 1 r574_0 1 r574_2 1 r575_0 1 r576_0 1 r577_0 1 r577_2 1 r578_0 1 r579_0 1 r57_0 1 r57_2 1 r57_4 1 r580_0 1 r581_0 1 r582_0 1 r583_0 1 r584_0 1 r585_0 1 r585_2 1 r586_0 1 r587_0 1 r588_0 1 r589_0 1 r58_0 1 r590_0 1 r591_0 1 r592_0 1 r593_0 1 r593_2 1 r594_0 1 r595_0 1 r595_2 1 r596_0 1 r597_0 1 r597_2 1 r598_0 1 r599_0 1 r599_2 1 r59_0 1 r59_2 1 r59_4 1 r5_0 1 r5_2 1 r5_4 1 r5_6 1 r600_0 1 r601_0 1 r601_2 1 r602_0 1 r603_0 1 r603_2 1 r604_0 1 r605_0 1 r605_2 1 r606_0 1 r607_0 1 r607_2 1 r608_0 1 r609_0 1 r609_2 1 r60_0 1 r610_0 1 r611_0 1 r611_2 1 r612_0 1 r613_0 1 r613_2 1 r614_0 1 r615_0 1 r615_2 1 r616_0 1 r617_0 1 r617_2 1 r618_0 1 r619_0 1 r619_2 1 r61_0 1 r61_2 1 r61_4 1 r620_0 1 r621_0 1 r621_2 1 r622_0 1 r623_0 1 r623_2 1 r624_0 1 r625_0 1 r625_2 1 r626_0 1 r627_0 1 r627_2 1 r628_0 1 r629_0 1 r629_2 1 r62_0 1 r630_0 1 r631_0 1 r631_2 1 r632_0 1 r633_0 1 r633_2 1 r634_0 1 r635_0 1 r635_2 1 r636_0 1 r637_0 1 r637_2 1 r638_0 1 r639_0 1 r63_0 1 r63_2 1 r63_4 1 r640_0 1 r641_0 1 r642_0 1 r643_0 1 r643_2 1 r644_0 1 r645_0 1 r646_0 1 r647_0 1 r648_0 1 r648_2 1 r649_0 1 r64_0 1 r650_0 1 r650_2 1 r651_0 1 r652_0 1 r653_0 1 r654_0 1 r655_0 1 r656_0 1 r657_0 1 r658_0 1 r658_2 1 r659_0 1 r65_0 1 r65_2 1 r65_4 1 r660_0 1 r660_2 1 r661_0 1 r662_0 1 r663_0 1 r664_0 1 r664_2 1 r665_0 1 r666_0 1 r666_2 1 r667_0 1 r668_0 1 r668_2 1 r669_0 1 r66_0 1 r66_2 1 r66_4 1 r670_0 1 r670_2 1 r671_0 1 r672_0 1 r672_2 1 r673_0 1 r674_0 1 r674_2 1 r675_0 1 r676_0 1 r676_2 1 r677_0 1 r678_0 1 r678_2 1 r679_0 1 r67_0 1 r680_0 1 r680_2 1 r681_0 1 r682_0 1 r682_2 1 r683_0 1 r684_0 1 r684_2 1 r685_0 1 r686_0 1 r687_0 1 r688_0 1 r689_0 1 r68_0 1 r68_2 1 r68_4 1 r690_0 1 r691_0 1 r692_0 1 r692_2 1 r693_0 1 r694_0 1 r694_2 1 r695_0 1 r696_0 1 r696_2 1 r697_0 1 r698_0 1 r698_2 1 r699_0 1 r69_0 1 r69_2 1 r69_4 1 r6_0 1 r6_2 1 r6_4 1 r6_6 1 r6_8 1 r700_0 1 r700_2 1 r701_0 1 r702_0 1 r702_2 1 r703_0 1 r704_0 1 r704_2 1 r705_0 1 r706_0 1 r706_2 1 r707_0 1 r708_0 1 r708_2 1 r709_0 1 r70_0 1 r710_0 1 r710_2 1 r711_0 1 r712_0 1 r712_2 1 r713_0 1 r714_0 1 r714_2 1 r715_0 1 r716_0 1 r717_0 1 r717_2 1 r718_0 1 r719_0 1 r71_0 1 r71_2 1 r71_4 1 r720_0 1 r721_0 1 r722_0 1 r723_0 1 r724_0 1 r725_0 1 r725_2 1 r726_0 1 r727_0 1 r728_0 1 r729_0 1 r72_0 1 r730_0 1 r731_0 1 r732_0 1 r733_0 1 r733_2 1 r734_0 1 r735_0 1 r735_2 1 r736_0 1 r737_0 1 r737_2 1 r738_0 1 r739_0 1 r739_2 1 r73_0 1 r73_2 1 r73_4 1 r740_0 1 r741_0 1 r741_2 1 r742_0 1 r743_0 1 r743_2 1 r744_0 1 r745_0 1 r745_2 1 r746_0 1 r747_0 1 r747_2 1 r748_0 1 r749_0 1 r749_2 1 r74_0 1 r750_0 1 r751_0 1 r751_2 1 r752_0 1 r753_0 1 r753_2 1 r754_0 1 r755_0 1 r755_2 1 r756_0 1 r757_0 1 r757_2 1 r758_0 1 r759_0 1 r759_2 1 r75_0 1 r75_2 1 r760_0 1 r761_0 1 r761_2 1 r762_0 1 r763_0 1 r763_2 1 r764_0 1 r765_0 1 r765_2 1 r766_0 1 r767_0 1 r767_2 1 r768_0 1 r769_0 1 r769_2 1 r76_0 1 r76_2 1 r76_4 1 r770_0 1 r771_0 1 r771_2 1 r772_0 1 r773_0 1 r773_2 1 r774_0 1 r775_0 1 r775_2 1 r776_0 1 r777_0 1 r777_2 1 r778_0 1 r779_0 1 r77_0 1 r780_0 1 r781_0 1 r782_0 1 r783_0 1 r783_2 1 r784_0 1 r785_0 1 r786_0 1 r787_0 1 r788_0 1 r788_2 1 r789_0 1 r78_0 1 r790_0 1 r790_2 1 r791_0 1 r792_0 1 r793_0 1 r794_0 1 r795_0 1 r796_0 1 r797_0 1 r798_0 1 r798_2 1 r799_0 1 r79_0 1 r79_2 1 r79_4 1 r7_0 1 r800_0 1 r800_2 1 r801_0 1 r802_0 1 r803_0 1 r804_0 1 r804_2 1 r805_0 1 r806_0 1 r806_2 1 r807_0 1 r808_0 1 r808_2 1 r809_0 1 r80_0 1 r810_0 1 r810_2 1 r811_0 1 r812_0 1 r812_2 1 r813_0 1 r814_0 1 r814_2 1 r815_0 1 r816_0 1 r816_2 1 r817_0 1 r818_0 1 r818_2 1 r819_0 1 r81_0 1 r81_2 1 r820_0 1 r820_2 1 r821_0 1 r822_0 1 r822_2 1 r823_0 1 r824_0 1 r824_2 1 r825_0 1 r826_0 1 r827_0 1 r828_0 1 r828_2 1 r828_4 1 r829_0 1 r82_0 1 r830_0 1 r830_2 1 r830_4 1 r831_0 1 r832_0 1 r833_0 1 r834_0 1 r834_2 1 r834_4 1 r835_0 1 r835_2 1 r836_0 1 r837_0 1 r837_2 1 r837_4 1 r838_0 1 r838_2 1 r839_0 1 r83_0 1 r840_0 1 r840_2 1 r840_4 1 r841_0 1 r841_2 1 r842_0 1 r843_0 1 r843_2 1 r843_4 1 r844_0 1 r844_2 1 r845_0 1 r846_0 1 r846_2 1 r846_4 1 r847_0 1 r847_2 1 r848_0 1 r849_0 1 r849_2 1 r849_4 1 r84_0 1 r850_0 1 r850_2 1 r851_0 1 r852_0 1 r852_2 1 r852_4 1 r853_0 1 r853_2 1 r854_0 1 r855_0 1 r855_2 1 r855_4 1 r856_0 1 r856_2 1 r857_0 1 r858_0 1 r858_2 1 r858_4 1 r859_0 1 r859_2 1 r85_0 1 r85_2 1 r860_0 1 r861_0 1 r861_2 1 r861_4 1 r862_0 1 r862_2 1 r863_0 1 r864_0 1 r864_2 1 r864_4 1 r865_0 1 r866_0 1 r866_2 1 r867_0 1 r867_2 1 r867_4 1 r868_0 1 r869_0 1 r86_0 1 r86_2 1 r86_4 1 r870_0 1 r870_2 1 r871_0 1 r872_0 1 r872_2 1 r872_4 1 r873_0 1 r874_0 1 r874_2 1 r875_0 1 r876_0 1 r876_2 1 r877_0 1 r877_2 1 r877_4 1 r878_0 1 r878_2 1 r878_4 1 r879_0 1 r879_2 1 r879_4 1 r87_0 1 r880_0 1 r880_2 1 r880_4 1 r881_0 1 r882_0 1 r883_0 1 r884_0 1 r885_0 1 r885_2 1 r886_0 1 r886_2 1 r887_0 1 r887_2 1 r887_4 1 r888_0 1 r888_2 1 r888_4 1 r889_0 1 r889_2 1 r889_4 1 r88_0 1 r88_2 1 r890_0 1 r891_0 1 r891_2 1 r891_4 1 r892_0 1 r893_0 1 r893_2 1 r894_0 1 r894_2 1 r894_4 1 r895_0 1 r895_2 1 r895_4 1 r896_0 1 r897_0 1 r898_0 1 r899_0 1 r899_2 1 r89_0 1 r89_2 1 r89_4 1 r8_0 1 r8_2 1 r8_4 1 r900_0 1 r900_2 1 r900_4 1 r900_6 1 r901_0 1 r902_0 1 r902_2 1 r902_4 1 r903_0 1 r904_0 1 r904_2 1 r904_4 1 r905_0 1 r905_2 1 r905_4 1 r906_0 1 r907_0 1 r908_0 1 r909_0 1 r909_2 1 r909_4 1 r90_0 1 r910_0 1 r910_2 1 r911_0 1 r912_0 1 r912_2 1 r912_4 1 r913_0 1 r913_2 1 r914_0 1 r915_0 1 r915_2 1 r915_4 1 r916_0 1 r916_2 1 r917_0 1 r918_0 1 r918_2 1 r918_4 1 r919_0 1 r919_2 1 r91_0 1 r91_2 1 r91_4 1 r920_0 1 r921_0 1 r921_2 1 r921_4 1 r922_0 1 r922_2 1 r923_0 1 r924_0 1 r924_2 1 r924_4 1 r925_0 1 r925_2 1 r926_0 1 r927_0 1 r927_2 1 r927_4 1 r928_0 1 r928_2 1 r929_0 1 r92_0 1 r92_2 1 r930_0 1 r930_2 1 r930_4 1 r931_0 1 r931_2 1 r932_0 1 r933_0 1 r933_2 1 r933_4 1 r934_0 1 r934_2 1 r935_0 1 r936_0 1 r936_2 1 r936_4 1 r937_0 1 r937_2 1 r938_0 1 r939_0 1 r939_2 1 r939_4 1 r93_0 1 r93_2 1 r940_0 1 r941_0 1 r941_2 1 r942_0 1 r942_2 1 r942_4 1 r943_0 1 r944_0 1 r945_0 1 r945_2 1 r946_0 1 r946_2 1 r947_0 1 r947_2 1 r947_4 1 r948_0 1 r948_2 1 r949_0 1 r949_2 1 r949_4 1 r94_0 1 r94_2 1 r94_4 1 r94_6 1 r94_8 1 r950_0 1 r951_0 1 r952_0 1 r952_2 1 r952_4 1 r953_0 1 r953_2 1 r953_4 1 r954_0 1 r954_2 1 r955_0 1 r956_0 1 r956_2 1 r956_4 1 r957_0 1 r957_2 1 r958_0 1 r959_0 1 r959_2 1 r959_4 1 r95_0 1 r95_2 1 r95_4 1 r960_0 1 r960_2 1 r960_4 1 r961_0 1 r961_2 1 r962_0 1 r963_0 1 r963_2 1 r963_4 1 r964_0 1 r964_2 1 r964_4 1 r965_0 1 r965_2 1 r966_0 1 r967_0 1 r968_0 1 r968_2 1 r969_0 1 r96_0 1 r970_0 1 r971_0 1 r972_0 1 r972_2 1 r972_4 1 r973_0 1 r974_0 1 r974_2 1 r975_0 1 r976_0 1 r977_0 1 r977_2 1 r978_0 1 r979_0 1 r979_2 1 r979_4 1 r97_0 1 r97_2 1 r97_4 1 r97_6 1 r980_0 1 r980_2 1 r981_0 1 r982_0 1 r982_2 1 r983_0 1 r984_0 1 r985_0 1 r985_2 1 r986_0 1 r987_0 1 r987_2 1 r987_4 1 r988_0 1 r989_0 1 r989_2 1 r98_0 1 r98_2 1 r98_4 1 r98_6 1 r990_0 1 r991_0 1 r992_0 1 r993_0 1 r993_2 1 r993_4 1 r994_0 1 r994_2 1 r994_4 1 r995_0 1 r996_0 1 r996_2 1 r996_4 1 r997_0 1 r998_0 1 r998_2 1 r998_4 1 r999_0 1 r99_0 1 r9_0 1 r9_10 1 r9_12 1 r9_2 1 r9_4 1 r9_6 1 r9_8 1]
set fh [open /work/clock/arr_$::env(CORNER).txt w]
puts $fh "# OT_EDGES v1 T/N=source rise F/M=source fall (late early), polarity-resolved"
foreach p [get_ports t_*] { set n [get_full_name $p]; set smx [get_property $p slack_max_rise]; set smn [get_property $p slack_min_rise]; puts $fh "T $n [expr {833.333 - $smx}] [expr {$smn}]" }
foreach p [get_ports t_*] { puts $fh "F [get_full_name $p] [expr {833.333 - [get_property $p slack_max_fall]}] [get_property $p slack_min_fall]" }
foreach i [get_cells b*] { set q [get_pins [get_full_name $i]/Y]; if {[dict exists $ot_odd [get_full_name $i]]} { set e fall; set g rise } else { set e rise; set g fall }; puts $fh "N [get_full_name $i] [get_property $q arrival_max_$e] [get_property $q arrival_min_$e]"; puts $fh "M [get_full_name $i] [get_property $q arrival_max_$g] [get_property $q arrival_min_$g]" }
close $fh
report_checks -path_delay max -group_path_count 1 -format full -fields {cap slew fanout}
puts OT_DONE
