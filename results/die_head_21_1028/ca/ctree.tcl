read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f [glob $::env(LIBDIR)/*RVT_$::env(CORNER)_nldm*.lib*] { read_liberty $f }
read_verilog /work/clock/ctree.v
link_design ctree
initialize_floorplan -die_area {0 0 17521.92 17556.48} -core_area {0 0 17521.92 17556.48} -site asap7sc7p5t
source /work/clock/make_tracks.tcl
place_pin -pin_name root -layer M9 -location {8760.960 8779.240} -pin_size {0.04 0.32}
place_pin -pin_name t_sp5__clk -layer M9 -location {8761.440 3594.272} -pin_size {0.04 0.32}
place_pin -pin_name t_sp4__clk -layer M9 -location {8761.440 5667.872} -pin_size {0.04 0.32}
place_pin -pin_name t_sp3__clk -layer M9 -location {8761.440 7741.472} -pin_size {0.04 0.32}
place_pin -pin_name t_sp2__clk -layer M9 -location {8761.440 9815.072} -pin_size {0.04 0.32}
place_pin -pin_name t_sp1__clk -layer M9 -location {8761.440 11888.672} -pin_size {0.04 0.32}
place_pin -pin_name t_sp0__clk -layer M9 -location {8761.440 13962.272} -pin_size {0.04 0.32}
place_pin -pin_name t_sst5__clk -layer M9 -location {8043.360 1943.968} -pin_size {0.04 0.32}
place_pin -pin_name t_lk_HOST0__clk -layer M9 -location {7318.560 1252.832} -pin_size {0.04 0.32}
place_pin -pin_name t_sst4__clk -layer M9 -location {6592.800 1944.032} -pin_size {0.04 0.32}
place_pin -pin_name t_mesh0S__clk -layer M9 -location {5157.600 1944.032} -pin_size {0.04 0.32}
place_pin -pin_name t_lk_WS0__clk -layer M9 -location {4432.800 1252.832} -pin_size {0.04 0.32}
place_pin -pin_name t_sst2__clk -layer M9 -location {3714.720 1944.032} -pin_size {0.04 0.32}
place_pin -pin_name t_sst1__clk -layer M9 -location {2271.840 1944.032} -pin_size {0.04 0.32}
place_pin -pin_name t_lk_WS1__clk -layer M9 -location {1547.040 1252.832} -pin_size {0.04 0.32}
place_pin -pin_name t_host__clk -layer M9 -location {9486.240 1943.968} -pin_size {0.04 0.32}
place_pin -pin_name t_lk_HOST1__clk -layer M9 -location {10203.360 1252.832} -pin_size {0.04 0.32}
place_pin -pin_name t_sst7__clk -layer M9 -location {10929.120 1944.032} -pin_size {0.04 0.32}
place_pin -pin_name t_mesh7S__clk -layer M9 -location {12364.320 1944.032} -pin_size {0.04 0.32}
place_pin -pin_name t_lk_ES0__clk -layer M9 -location {13089.120 1252.832} -pin_size {0.04 0.32}
place_pin -pin_name t_sst9__clk -layer M9 -location {13807.200 1944.032} -pin_size {0.04 0.32}
place_pin -pin_name t_sst10__clk -layer M9 -location {15250.080 1944.032} -pin_size {0.04 0.32}
place_pin -pin_name t_lk_ES1__clk -layer M9 -location {15974.880 1252.832} -pin_size {0.04 0.32}
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
place_pin -pin_name t_turnW5b__clk -layer M9 -location {189.600 3075.808} -pin_size {0.04 0.32}
place_pin -pin_name t_turnW5a__clk -layer M9 -location {189.600 4112.608} -pin_size {0.04 0.32}
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
place_pin -pin_name t_turnE5b__clk -layer M9 -location {17332.320 3075.808} -pin_size {0.04 0.32}
place_pin -pin_name t_turnE5a__clk -layer M9 -location {17332.320 4112.608} -pin_size {0.04 0.32}
place_pin -pin_name t_tW4b0__clk -layer M9 -location {7715.040 4985.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tW4o0__clk -layer M9 -location {7716.000 6022.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tW4b1__clk -layer M9 -location {7006.560 4985.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tW4o1__clk -layer M9 -location {7007.520 6022.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tW4b2__clk -layer M9 -location {6298.080 4985.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tW4o2__clk -layer M9 -location {6299.040 6022.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tW4b3__clk -layer M9 -location {5589.600 4985.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tW4o3__clk -layer M9 -location {5590.560 6022.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tW4b4__clk -layer M9 -location {4881.120 4985.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tW4o4__clk -layer M9 -location {4882.080 6022.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tW4b5__clk -layer M9 -location {4172.640 4985.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tW4o5__clk -layer M9 -location {4173.600 6022.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tW4b6__clk -layer M9 -location {3464.160 4985.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tW4o6__clk -layer M9 -location {3465.120 6022.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tW4b7__clk -layer M9 -location {2755.680 4985.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tW4o7__clk -layer M9 -location {2756.640 6022.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tW4b8__clk -layer M9 -location {2047.200 4985.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tW4o8__clk -layer M9 -location {2048.160 6022.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tW4b9__clk -layer M9 -location {1338.720 4985.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tW4o9__clk -layer M9 -location {1339.680 6022.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tW4b10__clk -layer M9 -location {630.240 4985.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tW4o10__clk -layer M9 -location {631.200 6022.048} -pin_size {0.04 0.32}
place_pin -pin_name t_turnW4b__clk -layer M9 -location {189.600 5149.408} -pin_size {0.04 0.32}
place_pin -pin_name t_turnW4a__clk -layer M9 -location {189.600 6186.208} -pin_size {0.04 0.32}
place_pin -pin_name t_tE4b0__clk -layer M9 -location {9806.880 4985.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tE4o0__clk -layer M9 -location {9805.920 6022.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tE4b1__clk -layer M9 -location {10515.360 4985.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tE4o1__clk -layer M9 -location {10514.400 6022.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tE4b2__clk -layer M9 -location {11223.840 4985.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tE4o2__clk -layer M9 -location {11222.880 6022.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tE4b3__clk -layer M9 -location {11932.320 4985.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tE4o3__clk -layer M9 -location {11931.360 6022.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tE4b4__clk -layer M9 -location {12640.800 4985.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tE4o4__clk -layer M9 -location {12639.840 6022.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tE4b5__clk -layer M9 -location {13349.280 4985.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tE4o5__clk -layer M9 -location {13348.320 6022.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tE4b6__clk -layer M9 -location {14057.760 4985.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tE4o6__clk -layer M9 -location {14056.800 6022.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tE4b7__clk -layer M9 -location {14766.240 4985.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tE4o7__clk -layer M9 -location {14765.280 6022.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tE4b8__clk -layer M9 -location {15474.720 4985.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tE4o8__clk -layer M9 -location {15473.760 6022.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tE4b9__clk -layer M9 -location {16183.200 4985.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tE4o9__clk -layer M9 -location {16182.240 6022.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tE4b10__clk -layer M9 -location {16891.680 4985.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tE4o10__clk -layer M9 -location {16890.720 6022.048} -pin_size {0.04 0.32}
place_pin -pin_name t_turnE4b__clk -layer M9 -location {17332.320 5149.408} -pin_size {0.04 0.32}
place_pin -pin_name t_turnE4a__clk -layer M9 -location {17332.320 6186.208} -pin_size {0.04 0.32}
place_pin -pin_name t_tW3b0__clk -layer M9 -location {7715.040 7058.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tW3o0__clk -layer M9 -location {7716.000 8095.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tW3b1__clk -layer M9 -location {7006.560 7058.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tW3o1__clk -layer M9 -location {7007.520 8095.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tW3b2__clk -layer M9 -location {6298.080 7058.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tW3o2__clk -layer M9 -location {6299.040 8095.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tW3b3__clk -layer M9 -location {5589.600 7058.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tW3o3__clk -layer M9 -location {5590.560 8095.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tW3b4__clk -layer M9 -location {4881.120 7058.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tW3o4__clk -layer M9 -location {4882.080 8095.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tW3b5__clk -layer M9 -location {4172.640 7058.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tW3o5__clk -layer M9 -location {4173.600 8095.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tW3b6__clk -layer M9 -location {3464.160 7058.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tW3o6__clk -layer M9 -location {3465.120 8095.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tW3b7__clk -layer M9 -location {2755.680 7058.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tW3o7__clk -layer M9 -location {2756.640 8095.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tW3b8__clk -layer M9 -location {2047.200 7058.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tW3o8__clk -layer M9 -location {2048.160 8095.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tW3b9__clk -layer M9 -location {1338.720 7058.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tW3o9__clk -layer M9 -location {1339.680 8095.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tW3b10__clk -layer M9 -location {630.240 7058.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tW3o10__clk -layer M9 -location {631.200 8095.648} -pin_size {0.04 0.32}
place_pin -pin_name t_turnW3b__clk -layer M9 -location {189.600 7223.008} -pin_size {0.04 0.32}
place_pin -pin_name t_turnW3a__clk -layer M9 -location {189.600 8259.808} -pin_size {0.04 0.32}
place_pin -pin_name t_tE3b0__clk -layer M9 -location {9806.880 7058.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tE3o0__clk -layer M9 -location {9805.920 8095.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tE3b1__clk -layer M9 -location {10515.360 7058.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tE3o1__clk -layer M9 -location {10514.400 8095.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tE3b2__clk -layer M9 -location {11223.840 7058.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tE3o2__clk -layer M9 -location {11222.880 8095.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tE3b3__clk -layer M9 -location {11932.320 7058.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tE3o3__clk -layer M9 -location {11931.360 8095.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tE3b4__clk -layer M9 -location {12640.800 7058.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tE3o4__clk -layer M9 -location {12639.840 8095.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tE3b5__clk -layer M9 -location {13349.280 7058.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tE3o5__clk -layer M9 -location {13348.320 8095.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tE3b6__clk -layer M9 -location {14057.760 7058.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tE3o6__clk -layer M9 -location {14056.800 8095.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tE3b7__clk -layer M9 -location {14766.240 7058.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tE3o7__clk -layer M9 -location {14765.280 8095.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tE3b8__clk -layer M9 -location {15474.720 7058.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tE3o8__clk -layer M9 -location {15473.760 8095.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tE3b9__clk -layer M9 -location {16183.200 7058.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tE3o9__clk -layer M9 -location {16182.240 8095.648} -pin_size {0.04 0.32}
place_pin -pin_name t_tE3b10__clk -layer M9 -location {16891.680 7058.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tE3o10__clk -layer M9 -location {16890.720 8095.648} -pin_size {0.04 0.32}
place_pin -pin_name t_turnE3b__clk -layer M9 -location {17332.320 7223.008} -pin_size {0.04 0.32}
place_pin -pin_name t_turnE3a__clk -layer M9 -location {17332.320 8259.808} -pin_size {0.04 0.32}
place_pin -pin_name t_tW2b0__clk -layer M9 -location {7715.040 9132.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tW2o0__clk -layer M9 -location {7716.000 10169.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tW2b1__clk -layer M9 -location {7006.560 9132.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tW2o1__clk -layer M9 -location {7007.520 10169.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tW2b2__clk -layer M9 -location {6298.080 9132.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tW2o2__clk -layer M9 -location {6299.040 10169.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tW2b3__clk -layer M9 -location {5589.600 9132.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tW2o3__clk -layer M9 -location {5590.560 10169.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tW2b4__clk -layer M9 -location {4881.120 9132.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tW2o4__clk -layer M9 -location {4882.080 10169.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tW2b5__clk -layer M9 -location {4172.640 9132.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tW2o5__clk -layer M9 -location {4173.600 10169.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tW2b6__clk -layer M9 -location {3464.160 9132.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tW2o6__clk -layer M9 -location {3465.120 10169.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tW2b7__clk -layer M9 -location {2755.680 9132.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tW2o7__clk -layer M9 -location {2756.640 10169.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tW2b8__clk -layer M9 -location {2047.200 9132.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tW2o8__clk -layer M9 -location {2048.160 10169.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tW2b9__clk -layer M9 -location {1338.720 9132.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tW2o9__clk -layer M9 -location {1339.680 10169.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tW2b10__clk -layer M9 -location {630.240 9132.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tW2o10__clk -layer M9 -location {631.200 10169.248} -pin_size {0.04 0.32}
place_pin -pin_name t_turnW2b__clk -layer M9 -location {189.600 9296.608} -pin_size {0.04 0.32}
place_pin -pin_name t_turnW2a__clk -layer M9 -location {189.600 10333.408} -pin_size {0.04 0.32}
place_pin -pin_name t_tE2b0__clk -layer M9 -location {9806.880 9132.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tE2o0__clk -layer M9 -location {9805.920 10169.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tE2b1__clk -layer M9 -location {10515.360 9132.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tE2o1__clk -layer M9 -location {10514.400 10169.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tE2b2__clk -layer M9 -location {11223.840 9132.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tE2o2__clk -layer M9 -location {11222.880 10169.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tE2b3__clk -layer M9 -location {11932.320 9132.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tE2o3__clk -layer M9 -location {11931.360 10169.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tE2b4__clk -layer M9 -location {12640.800 9132.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tE2o4__clk -layer M9 -location {12639.840 10169.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tE2b5__clk -layer M9 -location {13349.280 9132.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tE2o5__clk -layer M9 -location {13348.320 10169.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tE2b6__clk -layer M9 -location {14057.760 9132.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tE2o6__clk -layer M9 -location {14056.800 10169.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tE2b7__clk -layer M9 -location {14766.240 9132.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tE2o7__clk -layer M9 -location {14765.280 10169.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tE2b8__clk -layer M9 -location {15474.720 9132.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tE2o8__clk -layer M9 -location {15473.760 10169.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tE2b9__clk -layer M9 -location {16183.200 9132.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tE2o9__clk -layer M9 -location {16182.240 10169.248} -pin_size {0.04 0.32}
place_pin -pin_name t_tE2b10__clk -layer M9 -location {16891.680 9132.448} -pin_size {0.04 0.32}
place_pin -pin_name t_tE2o10__clk -layer M9 -location {16890.720 10169.248} -pin_size {0.04 0.32}
place_pin -pin_name t_turnE2b__clk -layer M9 -location {17332.320 9296.608} -pin_size {0.04 0.32}
place_pin -pin_name t_turnE2a__clk -layer M9 -location {17332.320 10333.408} -pin_size {0.04 0.32}
place_pin -pin_name t_tW1b0__clk -layer M9 -location {7715.040 11206.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tW1o0__clk -layer M9 -location {7716.000 12242.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tW1b1__clk -layer M9 -location {7006.560 11206.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tW1o1__clk -layer M9 -location {7007.520 12242.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tW1b2__clk -layer M9 -location {6298.080 11206.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tW1o2__clk -layer M9 -location {6299.040 12242.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tW1b3__clk -layer M9 -location {5589.600 11206.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tW1o3__clk -layer M9 -location {5590.560 12242.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tW1b4__clk -layer M9 -location {4881.120 11206.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tW1o4__clk -layer M9 -location {4882.080 12242.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tW1b5__clk -layer M9 -location {4172.640 11206.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tW1o5__clk -layer M9 -location {4173.600 12242.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tW1b6__clk -layer M9 -location {3464.160 11206.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tW1o6__clk -layer M9 -location {3465.120 12242.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tW1b7__clk -layer M9 -location {2755.680 11206.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tW1o7__clk -layer M9 -location {2756.640 12242.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tW1b8__clk -layer M9 -location {2047.200 11206.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tW1o8__clk -layer M9 -location {2048.160 12242.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tW1b9__clk -layer M9 -location {1338.720 11206.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tW1o9__clk -layer M9 -location {1339.680 12242.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tW1b10__clk -layer M9 -location {630.240 11206.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tW1o10__clk -layer M9 -location {631.200 12242.848} -pin_size {0.04 0.32}
place_pin -pin_name t_turnW1b__clk -layer M9 -location {189.600 11370.208} -pin_size {0.04 0.32}
place_pin -pin_name t_turnW1a__clk -layer M9 -location {189.600 12407.008} -pin_size {0.04 0.32}
place_pin -pin_name t_tE1b0__clk -layer M9 -location {9806.880 11206.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tE1o0__clk -layer M9 -location {9805.920 12242.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tE1b1__clk -layer M9 -location {10515.360 11206.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tE1o1__clk -layer M9 -location {10514.400 12242.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tE1b2__clk -layer M9 -location {11223.840 11206.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tE1o2__clk -layer M9 -location {11222.880 12242.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tE1b3__clk -layer M9 -location {11932.320 11206.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tE1o3__clk -layer M9 -location {11931.360 12242.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tE1b4__clk -layer M9 -location {12640.800 11206.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tE1o4__clk -layer M9 -location {12639.840 12242.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tE1b5__clk -layer M9 -location {13349.280 11206.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tE1o5__clk -layer M9 -location {13348.320 12242.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tE1b6__clk -layer M9 -location {14057.760 11206.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tE1o6__clk -layer M9 -location {14056.800 12242.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tE1b7__clk -layer M9 -location {14766.240 11206.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tE1o7__clk -layer M9 -location {14765.280 12242.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tE1b8__clk -layer M9 -location {15474.720 11206.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tE1o8__clk -layer M9 -location {15473.760 12242.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tE1b9__clk -layer M9 -location {16183.200 11206.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tE1o9__clk -layer M9 -location {16182.240 12242.848} -pin_size {0.04 0.32}
place_pin -pin_name t_tE1b10__clk -layer M9 -location {16891.680 11206.048} -pin_size {0.04 0.32}
place_pin -pin_name t_tE1o10__clk -layer M9 -location {16890.720 12242.848} -pin_size {0.04 0.32}
place_pin -pin_name t_turnE1b__clk -layer M9 -location {17332.320 11370.208} -pin_size {0.04 0.32}
place_pin -pin_name t_turnE1a__clk -layer M9 -location {17332.320 12407.008} -pin_size {0.04 0.32}
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
place_pin -pin_name t_turnW0b__clk -layer M9 -location {189.600 13443.808} -pin_size {0.04 0.32}
place_pin -pin_name t_turnW0a__clk -layer M9 -location {189.600 14480.608} -pin_size {0.04 0.32}
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
place_pin -pin_name t_turnE0b__clk -layer M9 -location {17332.320 13443.808} -pin_size {0.04 0.32}
place_pin -pin_name t_turnE0a__clk -layer M9 -location {17332.320 14480.608} -pin_size {0.04 0.32}
place_pin -pin_name t_lep0N__clk -layer M9 -location {8043.360 15612.448} -pin_size {0.04 0.32}
place_pin -pin_name t_lk_WN0__clk -layer M9 -location {7318.560 16303.648} -pin_size {0.04 0.32}
place_pin -pin_name t_nst4__clk -layer M9 -location {6600.480 15612.448} -pin_size {0.04 0.32}
place_pin -pin_name t_nst3__clk -layer M9 -location {5157.600 15612.448} -pin_size {0.04 0.32}
place_pin -pin_name t_lk_WN1__clk -layer M9 -location {4432.800 16303.648} -pin_size {0.04 0.32}
place_pin -pin_name t_nst2__clk -layer M9 -location {3714.720 15612.448} -pin_size {0.04 0.32}
place_pin -pin_name t_nst1__clk -layer M9 -location {2271.840 15612.448} -pin_size {0.04 0.32}
place_pin -pin_name t_lk_WN2__clk -layer M9 -location {1547.040 16303.648} -pin_size {0.04 0.32}
place_pin -pin_name t_ctl__clk -layer M9 -location {9486.240 15612.448} -pin_size {0.04 0.32}
place_pin -pin_name t_lk_WN3__clk -layer M9 -location {10203.360 16303.648} -pin_size {0.04 0.32}
place_pin -pin_name t_nst7__clk -layer M9 -location {10929.120 15612.448} -pin_size {0.04 0.32}
place_pin -pin_name t_mesh7N__clk -layer M9 -location {12364.320 15612.448} -pin_size {0.04 0.32}
place_pin -pin_name t_lk_EN0__clk -layer M9 -location {13089.120 16303.648} -pin_size {0.04 0.32}
place_pin -pin_name t_nst9__clk -layer M9 -location {13807.200 15612.448} -pin_size {0.04 0.32}
place_pin -pin_name t_nst10__clk -layer M9 -location {15250.080 15612.448} -pin_size {0.04 0.32}
place_pin -pin_name t_lk_EN1__clk -layer M9 -location {15974.880 16303.648} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b1__clk -layer M9 -location {8763.120 8432.640} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r2_2__clk -layer M9 -location {8763.120 7842.317} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r9_2__clk -layer M9 -location {8763.120 9016.429} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r2_5__clk -layer M9 -location {8763.120 7251.994} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r9_5__clk -layer M9 -location {8763.120 9600.218} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r2_8__clk -layer M9 -location {8763.120 6661.670} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r9_8__clk -layer M9 -location {8763.120 10184.007} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r2_11__clk -layer M9 -location {8763.120 6071.347} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r9_11__clk -layer M9 -location {8763.120 10767.796} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r2_14__clk -layer M9 -location {8763.120 5481.024} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r9_14__clk -layer M9 -location {8763.120 11351.585} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r2_17__clk -layer M9 -location {8763.120 4890.701} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r9_17__clk -layer M9 -location {8763.120 11935.375} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b2__clk -layer M9 -location {8763.120 4497.152} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r9_20__clk -layer M9 -location {8763.120 12519.164} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b9__clk -layer M9 -location {8763.120 12713.760} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r3_2__clk -layer M9 -location {8763.120 3915.421} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r6_2__clk -layer M9 -location {8763.120 5048.897} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r10_2__clk -layer M9 -location {8763.120 12155.356} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r13_2__clk -layer M9 -location {8763.120 13232.160} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r3_5__clk -layer M9 -location {8763.120 3333.689} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r6_6__clk -layer M9 -location {8763.120 5784.557} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r10_5__clk -layer M9 -location {8763.120 11596.951} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r3_8__clk -layer M9 -location {8763.120 2751.957} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r13_6__clk -layer M9 -location {8763.120 13923.360} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b3__clk -layer M9 -location {8763.120 2558.047} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r6_9__clk -layer M9 -location {8763.120 6336.302} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b6__clk -layer M9 -location {8763.120 6703.862} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b10__clk -layer M9 -location {8763.120 10852.412} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r13_9__clk -layer M9 -location {8763.120 14441.760} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r4_2__clk -layer M9 -location {8762.120 2068.591} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r5_2__clk -layer M9 -location {8763.120 3076.159} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b13__clk -layer M9 -location {8763.120 14787.360} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r7_2__clk -layer M9 -location {8763.120 6186.002} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r8_2__clk -layer M9 -location {8763.120 7222.802} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r11_2__clk -layer M9 -location {8763.120 10333.742} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r12_2__clk -layer M9 -location {8763.120 11370.542} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b15__clk -layer M9 -location {8763.120 14998.090} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r4_6__clk -layer M9 -location {8762.245 1415.984} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b4__clk -layer M9 -location {8762.120 1252.832} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r14_3__clk -layer M9 -location {8763.120 14237.301} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r78_2__clk -layer M9 -location {9281.115 3594.272} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r474_2__clk -layer M9 -location {8494.020 15228.474} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r485_2__clk -layer M9 -location {9035.100 15228.474} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b42__clk -layer M9 -location {8072.643 3594.272} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b78__clk -layer M9 -location {9446.760 3594.272} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r16_2__clk -layer M9 -location {8224.670 1252.832} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r29_2__clk -layer M9 -location {9306.830 1252.832} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r150_2__clk -layer M9 -location {9281.115 5667.872} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r222_2__clk -layer M9 -location {9281.115 7741.472} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r294_2__clk -layer M9 -location {9281.115 9815.072} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r366_2__clk -layer M9 -location {9281.115 11888.672} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b16__clk -layer M9 -location {8045.520 1252.832} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b29__clk -layer M9 -location {9488.400 1252.832} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b114__clk -layer M9 -location {8072.643 5667.872} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b150__clk -layer M9 -location {9446.760 5667.872} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b186__clk -layer M9 -location {8072.643 7741.472} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b222__clk -layer M9 -location {9446.760 7741.472} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b258__clk -layer M9 -location {8072.643 9815.072} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b294__clk -layer M9 -location {9446.760 9815.072} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b330__clk -layer M9 -location {8072.643 11888.672} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b366__clk -layer M9 -location {9446.760 11888.672} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r45_2__clk -layer M9 -location {7540.922 3594.756} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r79_2__clk -layer M9 -location {9631.170 3260.040} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r81_2__clk -layer M9 -location {9985.410 3594.756} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r438_2__clk -layer M9 -location {9281.115 13962.272} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r474_6__clk -layer M9 -location {8135.220 15535.653} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r485_6__clk -layer M9 -location {9397.740 15535.653} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r43_3__clk -layer M9 -location {7836.001 3260.040} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b402__clk -layer M9 -location {8072.643 13962.272} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b438__clk -layer M9 -location {9446.760 13962.272} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r18_2__clk -layer M9 -location {7501.920 1252.832} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r117_2__clk -layer M9 -location {7540.922 5668.356} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r151_2__clk -layer M9 -location {9631.170 5333.640} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r153_2__clk -layer M9 -location {9985.410 5668.356} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r189_2__clk -layer M9 -location {7540.922 7741.956} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r223_2__clk -layer M9 -location {9631.170 7407.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r225_2__clk -layer M9 -location {9985.410 7741.956} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r261_2__clk -layer M9 -location {7540.922 9815.556} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r295_2__clk -layer M9 -location {9631.170 9480.840} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r297_2__clk -layer M9 -location {9985.410 9815.556} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r333_2__clk -layer M9 -location {7540.922 11889.156} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r367_2__clk -layer M9 -location {9631.170 11554.440} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r369_2__clk -layer M9 -location {9985.410 11889.156} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b45__clk -layer M9 -location {7009.200 3595.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b81__clk -layer M9 -location {10517.040 3595.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r115_3__clk -layer M9 -location {7836.001 5333.640} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r187_3__clk -layer M9 -location {7836.001 7407.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r259_3__clk -layer M9 -location {7836.001 9480.840} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r331_3__clk -layer M9 -location {7836.001 11554.440} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r405_2__clk -layer M9 -location {7540.922 13962.756} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r439_2__clk -layer M9 -location {9631.170 13628.040} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r441_2__clk -layer M9 -location {9985.410 13962.756} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b117__clk -layer M9 -location {7009.200 5668.840} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b153__clk -layer M9 -location {10517.040 5668.840} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b189__clk -layer M9 -location {7009.200 7742.440} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b225__clk -layer M9 -location {10517.040 7742.440} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b261__clk -layer M9 -location {7009.200 9816.040} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b297__clk -layer M9 -location {10517.040 9816.040} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b333__clk -layer M9 -location {7009.200 11889.640} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b369__clk -layer M9 -location {10517.040 11889.640} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r403_3__clk -layer M9 -location {7836.001 13628.040} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b475__clk -layer M9 -location {7321.260 15612.448} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b486__clk -layer M9 -location {10204.980 15612.448} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r19_2__clk -layer M9 -location {6776.400 1252.832} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r32_2__clk -layer M9 -location {10749.840 1252.832} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r48_2__clk -layer M9 -location {6477.840 3595.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r84_2__clk -layer M9 -location {11048.400 3595.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b19__clk -layer M9 -location {6594.960 1252.832} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b32__clk -layer M9 -location {10931.280 1252.832} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b48__clk -layer M9 -location {6300.720 3595.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b84__clk -layer M9 -location {11225.520 3595.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b405__clk -layer M9 -location {7009.200 13963.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b441__clk -layer M9 -location {10517.040 13963.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r120_2__clk -layer M9 -location {6477.840 5668.840} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r156_2__clk -layer M9 -location {11048.400 5668.840} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r192_2__clk -layer M9 -location {6477.840 7742.440} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r228_2__clk -layer M9 -location {11048.400 7742.440} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r264_2__clk -layer M9 -location {6477.840 9816.040} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r300_2__clk -layer M9 -location {11048.400 9816.040} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r336_2__clk -layer M9 -location {6477.840 11889.640} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r372_2__clk -layer M9 -location {11048.400 11889.640} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b120__clk -layer M9 -location {6300.720 5668.840} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b156__clk -layer M9 -location {11225.520 5668.840} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b192__clk -layer M9 -location {6300.720 7742.440} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b228__clk -layer M9 -location {11225.520 7742.440} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b264__clk -layer M9 -location {6300.720 9816.040} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b300__clk -layer M9 -location {11225.520 9816.040} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b336__clk -layer M9 -location {6300.720 11889.640} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b372__clk -layer M9 -location {11225.520 11889.640} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r21_2__clk -layer M9 -location {6056.760 1252.832} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r34_2__clk -layer M9 -location {11469.480 1252.832} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r51_2__clk -layer M9 -location {5769.360 3595.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r87_2__clk -layer M9 -location {11756.880 3595.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r408_2__clk -layer M9 -location {6477.840 13963.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r444_2__clk -layer M9 -location {11048.400 13963.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b51__clk -layer M9 -location {5592.240 3595.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b87__clk -layer M9 -location {11934.000 3595.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b408__clk -layer M9 -location {6300.720 13963.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b444__clk -layer M9 -location {11225.520 13963.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r123_2__clk -layer M9 -location {5769.360 5668.840} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r159_2__clk -layer M9 -location {11756.880 5668.840} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r195_2__clk -layer M9 -location {5769.360 7742.440} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r231_2__clk -layer M9 -location {11756.880 7742.440} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r267_2__clk -layer M9 -location {5769.360 9816.040} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r303_2__clk -layer M9 -location {11756.880 9816.040} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r339_2__clk -layer M9 -location {5769.360 11889.640} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r375_2__clk -layer M9 -location {11756.880 11889.640} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r21_5__clk -layer M9 -location {5518.560 1252.832} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r34_5__clk -layer M9 -location {12007.680 1252.832} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b123__clk -layer M9 -location {5592.240 5668.840} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b159__clk -layer M9 -location {11934.000 5668.840} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b195__clk -layer M9 -location {5592.240 7742.440} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b231__clk -layer M9 -location {11934.000 7742.440} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b267__clk -layer M9 -location {5592.240 9816.040} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b303__clk -layer M9 -location {11934.000 9816.040} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b339__clk -layer M9 -location {5592.240 11889.640} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b375__clk -layer M9 -location {11934.000 11889.640} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r478_3__clk -layer M9 -location {5881.200 15612.448} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r489_3__clk -layer M9 -location {11649.880 15612.448} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r54_2__clk -layer M9 -location {5060.880 3595.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r90_2__clk -layer M9 -location {12465.360 3595.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r411_2__clk -layer M9 -location {5769.360 13963.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r447_2__clk -layer M9 -location {11756.880 13963.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b21__clk -layer M9 -location {5159.760 1252.832} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b34__clk -layer M9 -location {12366.480 1252.832} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b54__clk -layer M9 -location {4883.760 3595.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b90__clk -layer M9 -location {12642.480 3595.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b411__clk -layer M9 -location {5592.240 13963.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b447__clk -layer M9 -location {11934.000 13963.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r126_2__clk -layer M9 -location {5060.880 5668.840} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r162_2__clk -layer M9 -location {12465.360 5668.840} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r198_2__clk -layer M9 -location {5060.880 7742.440} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r234_2__clk -layer M9 -location {12465.360 7742.440} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r270_2__clk -layer M9 -location {5060.880 9816.040} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r306_2__clk -layer M9 -location {12465.360 9816.040} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r342_2__clk -layer M9 -location {5060.880 11889.640} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r378_2__clk -layer M9 -location {12465.360 11889.640} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b126__clk -layer M9 -location {4883.760 5668.840} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b162__clk -layer M9 -location {12642.480 5668.840} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b198__clk -layer M9 -location {4883.760 7742.440} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b234__clk -layer M9 -location {12642.480 7742.440} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b270__clk -layer M9 -location {4883.760 9816.040} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b306__clk -layer M9 -location {12642.480 9816.040} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b342__clk -layer M9 -location {4883.760 11889.640} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b378__clk -layer M9 -location {12642.480 11889.640} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r36_2__clk -layer M9 -location {12910.080 1252.832} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r57_2__clk -layer M9 -location {4352.400 3595.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r93_2__clk -layer M9 -location {13173.840 3595.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r414_2__clk -layer M9 -location {5060.880 13963.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r450_2__clk -layer M9 -location {12465.360 13963.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b57__clk -layer M9 -location {4175.280 3595.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b93__clk -layer M9 -location {13350.960 3595.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b414__clk -layer M9 -location {4883.760 13963.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b450__clk -layer M9 -location {12642.480 13963.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r129_2__clk -layer M9 -location {4352.400 5668.840} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r165_2__clk -layer M9 -location {13173.840 5668.840} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r201_2__clk -layer M9 -location {4352.400 7742.440} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r237_2__clk -layer M9 -location {13173.840 7742.440} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r273_2__clk -layer M9 -location {4352.400 9816.040} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r309_2__clk -layer M9 -location {13173.840 9816.040} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r345_2__clk -layer M9 -location {4352.400 11889.640} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r381_2__clk -layer M9 -location {13173.840 11889.640} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b129__clk -layer M9 -location {4175.280 5668.840} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b165__clk -layer M9 -location {13350.960 5668.840} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b201__clk -layer M9 -location {4175.280 7742.440} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b237__clk -layer M9 -location {13350.960 7742.440} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b273__clk -layer M9 -location {4175.280 9816.040} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b309__clk -layer M9 -location {13350.960 9816.040} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b345__clk -layer M9 -location {4175.280 11889.640} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b381__clk -layer M9 -location {13350.960 11889.640} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b479__clk -layer M9 -location {4435.500 15612.448} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b490__clk -layer M9 -location {13090.740 15612.448} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r37_2__clk -layer M9 -location {13629.840 1252.832} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r60_2__clk -layer M9 -location {3643.920 3595.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r96_2__clk -layer M9 -location {13882.320 3595.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r417_2__clk -layer M9 -location {4352.400 13963.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r453_2__clk -layer M9 -location {13173.840 13963.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b24__clk -layer M9 -location {3716.880 1252.832} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b37__clk -layer M9 -location {13809.360 1252.832} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b60__clk -layer M9 -location {3466.800 3595.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b96__clk -layer M9 -location {14059.440 3595.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b417__clk -layer M9 -location {4175.280 13963.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b453__clk -layer M9 -location {13350.960 13963.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r132_2__clk -layer M9 -location {3643.920 5668.840} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r168_2__clk -layer M9 -location {13882.320 5668.840} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r204_2__clk -layer M9 -location {3643.920 7742.440} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r240_2__clk -layer M9 -location {13882.320 7742.440} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r276_2__clk -layer M9 -location {3643.920 9816.040} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r312_2__clk -layer M9 -location {13882.320 9816.040} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r348_2__clk -layer M9 -location {3643.920 11889.640} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r384_2__clk -layer M9 -location {13882.320 11889.640} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b132__clk -layer M9 -location {3466.800 5668.840} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b168__clk -layer M9 -location {14059.440 5668.840} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b204__clk -layer M9 -location {3466.800 7742.440} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b240__clk -layer M9 -location {14059.440 7742.440} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b276__clk -layer M9 -location {3466.800 9816.040} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b312__clk -layer M9 -location {14059.440 9816.040} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b348__clk -layer M9 -location {3466.800 11889.640} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b384__clk -layer M9 -location {14059.440 11889.640} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r26_2__clk -layer M9 -location {3175.800 1252.832} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r39_2__clk -layer M9 -location {14350.440 1252.832} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r63_2__clk -layer M9 -location {2935.440 3595.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r99_2__clk -layer M9 -location {14590.800 3595.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r420_2__clk -layer M9 -location {3643.920 13963.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r456_2__clk -layer M9 -location {13882.320 13963.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b63__clk -layer M9 -location {2758.320 3595.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b99__clk -layer M9 -location {14767.920 3595.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b420__clk -layer M9 -location {3466.800 13963.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b456__clk -layer M9 -location {14059.440 13963.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r135_2__clk -layer M9 -location {2935.440 5668.840} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r171_2__clk -layer M9 -location {14590.800 5668.840} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r207_2__clk -layer M9 -location {2935.440 7742.440} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r243_2__clk -layer M9 -location {14590.800 7742.440} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r279_2__clk -layer M9 -location {2935.440 9816.040} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r315_2__clk -layer M9 -location {14590.800 9816.040} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r351_2__clk -layer M9 -location {2935.440 11889.640} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r387_2__clk -layer M9 -location {14590.800 11889.640} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r26_5__clk -layer M9 -location {2634.720 1252.832} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r39_5__clk -layer M9 -location {14891.520 1252.832} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b135__clk -layer M9 -location {2758.320 5668.840} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b171__clk -layer M9 -location {14767.920 5668.840} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b207__clk -layer M9 -location {2758.320 7742.440} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b243__clk -layer M9 -location {14767.920 7742.440} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b279__clk -layer M9 -location {2758.320 9816.040} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b315__clk -layer M9 -location {14767.920 9816.040} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b351__clk -layer M9 -location {2758.320 11889.640} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b387__clk -layer M9 -location {14767.920 11889.640} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r482_3__clk -layer M9 -location {2995.440 15612.448} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r493_3__clk -layer M9 -location {14530.800 15612.448} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r66_2__clk -layer M9 -location {2226.960 3595.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r102_2__clk -layer M9 -location {15299.280 3595.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r423_2__clk -layer M9 -location {2935.440 13963.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r459_2__clk -layer M9 -location {14590.800 13963.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b26__clk -layer M9 -location {2274.000 1252.832} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b39__clk -layer M9 -location {15252.240 1252.832} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b66__clk -layer M9 -location {2049.840 3595.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b102__clk -layer M9 -location {15476.400 3595.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b423__clk -layer M9 -location {2758.320 13963.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b459__clk -layer M9 -location {14767.920 13963.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r138_2__clk -layer M9 -location {2226.960 5668.840} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r174_2__clk -layer M9 -location {15299.280 5668.840} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r210_2__clk -layer M9 -location {2226.960 7742.440} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r246_2__clk -layer M9 -location {15299.280 7742.440} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r282_2__clk -layer M9 -location {2226.960 9816.040} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r318_2__clk -layer M9 -location {15299.280 9816.040} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r354_2__clk -layer M9 -location {2226.960 11889.640} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r390_2__clk -layer M9 -location {15299.280 11889.640} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b138__clk -layer M9 -location {2049.840 5668.840} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b174__clk -layer M9 -location {15476.400 5668.840} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b210__clk -layer M9 -location {2049.840 7742.440} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b246__clk -layer M9 -location {15476.400 7742.440} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b282__clk -layer M9 -location {2049.840 9816.040} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b318__clk -layer M9 -location {15476.400 9816.040} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b354__clk -layer M9 -location {2049.840 11889.640} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b390__clk -layer M9 -location {15476.400 11889.640} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r69_2__clk -layer M9 -location {1518.480 3595.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r105_2__clk -layer M9 -location {16007.760 3595.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r426_2__clk -layer M9 -location {2226.960 13963.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r462_2__clk -layer M9 -location {15299.280 13963.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b69__clk -layer M9 -location {1341.360 3595.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b105__clk -layer M9 -location {16184.880 3595.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b426__clk -layer M9 -location {2049.840 13963.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b462__clk -layer M9 -location {15476.400 13963.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r141_2__clk -layer M9 -location {1518.480 5668.840} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r177_2__clk -layer M9 -location {16007.760 5668.840} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r213_2__clk -layer M9 -location {1518.480 7742.440} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r249_2__clk -layer M9 -location {16007.760 7742.440} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r285_2__clk -layer M9 -location {1518.480 9816.040} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r321_2__clk -layer M9 -location {16007.760 9816.040} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r357_2__clk -layer M9 -location {1518.480 11889.640} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r393_2__clk -layer M9 -location {16007.760 11889.640} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b141__clk -layer M9 -location {1341.360 5668.840} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b177__clk -layer M9 -location {16184.880 5668.840} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b213__clk -layer M9 -location {1341.360 7742.440} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b249__clk -layer M9 -location {16184.880 7742.440} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b285__clk -layer M9 -location {1341.360 9816.040} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b321__clk -layer M9 -location {16184.880 9816.040} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b357__clk -layer M9 -location {1341.360 11889.640} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b393__clk -layer M9 -location {16184.880 11889.640} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b483__clk -layer M9 -location {1549.740 15612.448} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b494__clk -layer M9 -location {15969.480 15612.448} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r72_2__clk -layer M9 -location {810.000 3595.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r108_2__clk -layer M9 -location {16716.240 3595.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r429_2__clk -layer M9 -location {1518.480 13963.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r465_2__clk -layer M9 -location {16007.760 13963.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b72__clk -layer M9 -location {632.880 3595.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b108__clk -layer M9 -location {16893.360 3595.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b429__clk -layer M9 -location {1341.360 13963.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b465__clk -layer M9 -location {16184.880 13963.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r144_2__clk -layer M9 -location {810.000 5668.840} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r180_2__clk -layer M9 -location {16716.240 5668.840} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r216_2__clk -layer M9 -location {810.000 7742.440} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r252_2__clk -layer M9 -location {16716.240 7742.440} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r288_2__clk -layer M9 -location {810.000 9816.040} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r324_2__clk -layer M9 -location {16716.240 9816.040} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r360_2__clk -layer M9 -location {810.000 11889.640} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r396_2__clk -layer M9 -location {16716.240 11889.640} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b144__clk -layer M9 -location {632.880 5668.840} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b180__clk -layer M9 -location {16893.360 5668.840} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b216__clk -layer M9 -location {632.880 7742.440} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b252__clk -layer M9 -location {16893.360 7742.440} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b288__clk -layer M9 -location {632.880 9816.040} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b324__clk -layer M9 -location {16893.360 9816.040} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b360__clk -layer M9 -location {632.880 11889.640} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b396__clk -layer M9 -location {16893.360 11889.640} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r432_2__clk -layer M9 -location {810.000 13963.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_r468_2__clk -layer M9 -location {16716.240 13963.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b75__clk -layer M9 -location {191.760 3595.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b111__clk -layer M9 -location {17334.480 3595.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b432__clk -layer M9 -location {632.880 13963.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b468__clk -layer M9 -location {16893.360 13963.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b147__clk -layer M9 -location {191.760 5668.840} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b183__clk -layer M9 -location {17334.480 5668.840} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b219__clk -layer M9 -location {191.760 7742.440} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b255__clk -layer M9 -location {17334.480 7742.440} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b291__clk -layer M9 -location {191.760 9816.040} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b327__clk -layer M9 -location {17334.480 9816.040} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b363__clk -layer M9 -location {191.760 11889.640} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b399__clk -layer M9 -location {17334.480 11889.640} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b435__clk -layer M9 -location {191.760 13963.240} -pin_size {0.04 0.32}
place_pin -pin_name t_st_b471__clk -layer M9 -location {17334.480 13963.240} -pin_size {0.04 0.32}
place_inst -name b0_r -location {8762.580 8779.240} -status PLACED
place_inst -name b0 -location {8760.960 8779.240} -status PLACED
place_inst -name r1_0 -location {8760.960 8605.940} -status PLACED
place_inst -name b1 -location {8760.960 8432.640} -status PLACED
place_inst -name r2_0 -location {8760.960 8235.866} -status PLACED
place_inst -name r2_1 -location {8760.960 8039.091} -status PLACED
place_inst -name r2_2 -location {8760.960 7842.317} -status PLACED
place_inst -name r2_3 -location {8760.960 7645.542} -status PLACED
place_inst -name r2_4 -location {8760.960 7448.768} -status PLACED
place_inst -name r2_5 -location {8760.960 7251.994} -status PLACED
place_inst -name r2_6 -location {8760.960 7055.219} -status PLACED
place_inst -name r2_7 -location {8760.960 6858.445} -status PLACED
place_inst -name r2_8 -location {8760.960 6661.670} -status PLACED
place_inst -name r2_9 -location {8760.960 6464.896} -status PLACED
place_inst -name r2_10 -location {8760.960 6268.122} -status PLACED
place_inst -name r2_11 -location {8760.960 6071.347} -status PLACED
place_inst -name r2_12 -location {8760.960 5874.573} -status PLACED
place_inst -name r2_13 -location {8760.960 5677.798} -status PLACED
place_inst -name r2_14 -location {8760.960 5481.024} -status PLACED
place_inst -name r2_15 -location {8760.960 5284.250} -status PLACED
place_inst -name r2_16 -location {8760.960 5087.475} -status PLACED
place_inst -name r2_17 -location {8760.960 4890.701} -status PLACED
place_inst -name r2_18 -location {8760.960 4693.926} -status PLACED
place_inst -name b2 -location {8760.960 4497.152} -status PLACED
place_inst -name r3_0 -location {8760.960 4303.242} -status PLACED
place_inst -name r3_1 -location {8760.960 4109.331} -status PLACED
place_inst -name r3_2 -location {8760.960 3915.421} -status PLACED
place_inst -name r3_3 -location {8760.960 3721.510} -status PLACED
place_inst -name r3_4 -location {8760.960 3527.600} -status PLACED
place_inst -name r3_5 -location {8760.960 3333.689} -status PLACED
place_inst -name r3_6 -location {8760.960 3139.779} -status PLACED
place_inst -name r3_7 -location {8760.960 2945.868} -status PLACED
place_inst -name r3_8 -location {8760.960 2751.957} -status PLACED
place_inst -name b3 -location {8760.960 2558.047} -status PLACED
place_inst -name r4_0 -location {8759.960 2394.895} -status PLACED
place_inst -name r4_1 -location {8759.960 2231.743} -status PLACED
place_inst -name r4_2 -location {8759.960 2068.591} -status PLACED
place_inst -name r4_3 -location {8760.460 1905.439} -status PLACED
place_inst -name r4_4 -location {8760.335 1742.288} -status PLACED
place_inst -name r4_5 -location {8760.210 1579.136} -status PLACED
place_inst -name r4_6 -location {8760.085 1415.984} -status PLACED
place_inst -name b4 -location {8759.960 1252.832} -status PLACED
place_inst -name r5_0 -location {8760.960 2730.751} -status PLACED
place_inst -name r5_1 -location {8760.960 2903.455} -status PLACED
place_inst -name r5_2 -location {8760.960 3076.159} -status PLACED
place_inst -name r5_3 -location {8760.960 3248.864} -status PLACED
place_inst -name r5_4 -location {8760.960 3421.568} -status PLACED
place_inst -name b5 -location {8760.960 3594.272} -status PLACED
place_inst -name r6_0 -location {8760.960 4681.067} -status PLACED
place_inst -name r6_1 -location {8760.960 4864.982} -status PLACED
place_inst -name r6_2 -location {8760.960 5048.897} -status PLACED
place_inst -name r6_3 -location {8760.960 5232.812} -status PLACED
place_inst -name r6_4 -location {8760.960 5416.727} -status PLACED
place_inst -name r6_5 -location {8760.960 5600.642} -status PLACED
place_inst -name r6_6 -location {8760.960 5784.557} -status PLACED
place_inst -name r6_7 -location {8760.960 5968.472} -status PLACED
place_inst -name r6_8 -location {8760.960 6152.387} -status PLACED
place_inst -name r6_9 -location {8760.960 6336.302} -status PLACED
place_inst -name r6_10 -location {8760.960 6520.217} -status PLACED
place_inst -name b6 -location {8760.960 6704.132} -status PLACED
place_inst -name r7_0 -location {8760.960 6531.422} -status PLACED
place_inst -name r7_1 -location {8760.960 6358.712} -status PLACED
place_inst -name r7_2 -location {8760.960 6186.002} -status PLACED
place_inst -name r7_3 -location {8760.960 6013.292} -status PLACED
place_inst -name r7_4 -location {8760.960 5840.582} -status PLACED
place_inst -name b7 -location {8760.960 5667.872} -status PLACED
place_inst -name r8_0 -location {8760.960 6877.022} -status PLACED
place_inst -name r8_1 -location {8760.960 7049.912} -status PLACED
place_inst -name r8_2 -location {8760.960 7222.802} -status PLACED
place_inst -name r8_3 -location {8760.960 7395.692} -status PLACED
place_inst -name r8_4 -location {8760.960 7568.582} -status PLACED
place_inst -name b8 -location {8760.960 7741.472} -status PLACED
place_inst -name r9_0 -location {8760.960 8627.236} -status PLACED
place_inst -name r9_1 -location {8760.960 8821.833} -status PLACED
place_inst -name r9_2 -location {8760.960 9016.429} -status PLACED
place_inst -name r9_3 -location {8760.960 9211.025} -status PLACED
place_inst -name r9_4 -location {8760.960 9405.622} -status PLACED
place_inst -name r9_5 -location {8760.960 9600.218} -status PLACED
place_inst -name r9_6 -location {8760.960 9794.815} -status PLACED
place_inst -name r9_7 -location {8760.960 9989.411} -status PLACED
place_inst -name r9_8 -location {8760.960 10184.007} -status PLACED
place_inst -name r9_9 -location {8760.960 10378.604} -status PLACED
place_inst -name r9_10 -location {8760.960 10573.200} -status PLACED
place_inst -name r9_11 -location {8760.960 10767.796} -status PLACED
place_inst -name r9_12 -location {8760.960 10962.393} -status PLACED
place_inst -name r9_13 -location {8760.960 11156.989} -status PLACED
place_inst -name r9_14 -location {8760.960 11351.585} -status PLACED
place_inst -name r9_15 -location {8760.960 11546.182} -status PLACED
place_inst -name r9_16 -location {8760.960 11740.778} -status PLACED
place_inst -name r9_17 -location {8760.960 11935.375} -status PLACED
place_inst -name r9_18 -location {8760.960 12129.971} -status PLACED
place_inst -name r9_19 -location {8760.960 12324.567} -status PLACED
place_inst -name r9_20 -location {8760.960 12519.164} -status PLACED
place_inst -name b9 -location {8760.960 12713.760} -status PLACED
place_inst -name r10_0 -location {8760.960 12527.625} -status PLACED
place_inst -name r10_1 -location {8760.960 12341.490} -status PLACED
place_inst -name r10_2 -location {8760.960 12155.356} -status PLACED
place_inst -name r10_3 -location {8760.960 11969.221} -status PLACED
place_inst -name r10_4 -location {8760.960 11783.086} -status PLACED
place_inst -name r10_5 -location {8760.960 11596.951} -status PLACED
place_inst -name r10_6 -location {8760.960 11410.816} -status PLACED
place_inst -name r10_7 -location {8760.960 11224.682} -status PLACED
place_inst -name r10_8 -location {8760.960 11038.547} -status PLACED
place_inst -name b10 -location {8760.960 10852.412} -status PLACED
place_inst -name r11_0 -location {8760.960 10679.522} -status PLACED
place_inst -name r11_1 -location {8760.960 10506.632} -status PLACED
place_inst -name r11_2 -location {8760.960 10333.742} -status PLACED
place_inst -name r11_3 -location {8760.960 10160.852} -status PLACED
place_inst -name r11_4 -location {8760.960 9987.962} -status PLACED
place_inst -name b11 -location {8760.960 9815.072} -status PLACED
place_inst -name r12_0 -location {8760.960 11025.122} -status PLACED
place_inst -name r12_1 -location {8760.960 11197.832} -status PLACED
place_inst -name r12_2 -location {8760.960 11370.542} -status PLACED
place_inst -name r12_3 -location {8760.960 11543.252} -status PLACED
place_inst -name r12_4 -location {8760.960 11715.962} -status PLACED
place_inst -name b12 -location {8760.960 11888.672} -status PLACED
place_inst -name r13_0 -location {8760.960 12886.560} -status PLACED
place_inst -name r13_1 -location {8760.960 13059.360} -status PLACED
place_inst -name r13_2 -location {8760.960 13232.160} -status PLACED
place_inst -name r13_3 -location {8760.960 13404.960} -status PLACED
place_inst -name r13_4 -location {8760.960 13577.760} -status PLACED
place_inst -name r13_5 -location {8760.960 13750.560} -status PLACED
place_inst -name r13_6 -location {8760.960 13923.360} -status PLACED
place_inst -name r13_7 -location {8760.960 14096.160} -status PLACED
place_inst -name r13_8 -location {8760.960 14268.960} -status PLACED
place_inst -name r13_9 -location {8760.960 14441.760} -status PLACED
place_inst -name r13_10 -location {8760.960 14614.560} -status PLACED
place_inst -name b13 -location {8760.960 14787.360} -status PLACED
place_inst -name r14_0 -location {8760.960 14649.845} -status PLACED
place_inst -name r14_1 -location {8760.960 14512.331} -status PLACED
place_inst -name r14_2 -location {8760.960 14374.816} -status PLACED
place_inst -name r14_3 -location {8760.960 14237.301} -status PLACED
place_inst -name r14_4 -location {8760.960 14099.787} -status PLACED
place_inst -name b14 -location {8760.960 13962.272} -status PLACED
place_inst -name r15_0 -location {8760.960 14892.725} -status PLACED
place_inst -name b15 -location {8760.960 14998.090} -status PLACED
place_inst -name r16_0 -location {8580.810 1252.832} -status PLACED
place_inst -name r16_1 -location {8401.660 1252.832} -status PLACED
place_inst -name r16_2 -location {8222.510 1252.832} -status PLACED
place_inst -name b16 -location {8043.360 1252.832} -status PLACED
place_inst -name r17_0 -location {8043.360 1425.624} -status PLACED
place_inst -name r17_1 -location {8043.360 1598.416} -status PLACED
place_inst -name r17_2 -location {8043.360 1771.208} -status PLACED
place_inst -name b17 -location {8043.360 1944.000} -status PLACED
place_inst -name r18_0 -location {7862.160 1252.832} -status PLACED
place_inst -name r18_1 -location {7680.960 1252.832} -status PLACED
place_inst -name r18_2 -location {7499.760 1252.832} -status PLACED
place_inst -name b18 -location {7318.560 1252.832} -status PLACED
place_inst -name r19_0 -location {7137.120 1252.832} -status PLACED
place_inst -name r19_1 -location {6955.680 1252.832} -status PLACED
place_inst -name r19_2 -location {6774.240 1252.832} -status PLACED
place_inst -name b19 -location {6592.800 1252.832} -status PLACED
place_inst -name r20_0 -location {6592.800 1425.624} -status PLACED
place_inst -name r20_1 -location {6592.800 1598.416} -status PLACED
place_inst -name r20_2 -location {6592.800 1771.208} -status PLACED
place_inst -name b20 -location {6592.800 1944.000} -status PLACED
place_inst -name r21_0 -location {6413.400 1252.832} -status PLACED
place_inst -name r21_1 -location {6234.000 1252.832} -status PLACED
place_inst -name r21_2 -location {6054.600 1252.832} -status PLACED
place_inst -name r21_3 -location {5876.200 1252.832} -status PLACED
place_inst -name r21_4 -location {5695.800 1252.832} -status PLACED
place_inst -name r21_5 -location {5516.400 1252.832} -status PLACED
place_inst -name r21_6 -location {5337.000 1252.832} -status PLACED
place_inst -name b21 -location {5157.600 1252.832} -status PLACED
place_inst -name r22_0 -location {5157.600 1425.624} -status PLACED
place_inst -name r22_1 -location {5157.600 1598.416} -status PLACED
place_inst -name r22_2 -location {5157.600 1771.208} -status PLACED
place_inst -name b22 -location {5157.600 1944.000} -status PLACED
place_inst -name r23_0 -location {4976.400 1252.832} -status PLACED
place_inst -name r23_1 -location {4795.200 1252.832} -status PLACED
place_inst -name r23_2 -location {4614.000 1252.832} -status PLACED
place_inst -name b23 -location {4432.800 1252.832} -status PLACED
place_inst -name r24_0 -location {4253.280 1252.832} -status PLACED
place_inst -name r24_1 -location {4073.760 1252.832} -status PLACED
place_inst -name r24_2 -location {3894.240 1252.832} -status PLACED
place_inst -name b24 -location {3714.720 1252.832} -status PLACED
place_inst -name r25_0 -location {3714.720 1425.624} -status PLACED
place_inst -name r25_1 -location {3714.720 1598.416} -status PLACED
place_inst -name r25_2 -location {3714.720 1771.208} -status PLACED
place_inst -name b25 -location {3714.720 1944.000} -status PLACED
place_inst -name r26_0 -location {3534.360 1252.832} -status PLACED
place_inst -name r26_1 -location {3354.000 1252.832} -status PLACED
place_inst -name r26_2 -location {3173.640 1252.832} -status PLACED
place_inst -name r26_3 -location {2993.280 1252.832} -status PLACED
place_inst -name r26_4 -location {2812.920 1252.832} -status PLACED
place_inst -name r26_5 -location {2632.560 1252.832} -status PLACED
place_inst -name r26_6 -location {2452.200 1252.832} -status PLACED
place_inst -name b26 -location {2271.840 1252.832} -status PLACED
place_inst -name r27_0 -location {2271.840 1425.624} -status PLACED
place_inst -name r27_1 -location {2271.840 1598.416} -status PLACED
place_inst -name r27_2 -location {2271.840 1771.208} -status PLACED
place_inst -name b27 -location {2271.840 1944.000} -status PLACED
place_inst -name r28_0 -location {2090.640 1252.832} -status PLACED
place_inst -name r28_1 -location {1909.440 1252.832} -status PLACED
place_inst -name r28_2 -location {1728.240 1252.832} -status PLACED
place_inst -name b28 -location {1547.040 1252.832} -status PLACED
place_inst -name r29_0 -location {8941.530 1252.832} -status PLACED
place_inst -name r29_1 -location {9123.100 1252.832} -status PLACED
place_inst -name r29_2 -location {9304.670 1252.832} -status PLACED
place_inst -name b29 -location {9486.240 1252.832} -status PLACED
place_inst -name r30_0 -location {9486.240 1425.624} -status PLACED
place_inst -name r30_1 -location {9486.240 1598.416} -status PLACED
place_inst -name r30_2 -location {9486.240 1771.208} -status PLACED
place_inst -name b30 -location {9486.240 1944.000} -status PLACED
place_inst -name r31_0 -location {9665.520 1252.832} -status PLACED
place_inst -name r31_1 -location {9844.800 1252.832} -status PLACED
place_inst -name r31_2 -location {10024.080 1252.832} -status PLACED
place_inst -name b31 -location {10203.360 1252.832} -status PLACED
place_inst -name r32_0 -location {10384.800 1252.832} -status PLACED
place_inst -name r32_1 -location {10566.240 1252.832} -status PLACED
place_inst -name r32_2 -location {10747.680 1252.832} -status PLACED
place_inst -name b32 -location {10929.120 1252.832} -status PLACED
place_inst -name r33_0 -location {10929.120 1425.624} -status PLACED
place_inst -name r33_1 -location {10929.120 1598.416} -status PLACED
place_inst -name r33_2 -location {10929.120 1771.208} -status PLACED
place_inst -name b33 -location {10929.120 1944.000} -status PLACED
place_inst -name r34_0 -location {11108.520 1252.832} -status PLACED
place_inst -name r34_1 -location {11287.920 1252.832} -status PLACED
place_inst -name r34_2 -location {11467.320 1252.832} -status PLACED
place_inst -name r34_3 -location {11647.720 1252.832} -status PLACED
place_inst -name r34_4 -location {11826.120 1252.832} -status PLACED
place_inst -name r34_5 -location {12005.520 1252.832} -status PLACED
place_inst -name r34_6 -location {12184.920 1252.832} -status PLACED
place_inst -name b34 -location {12364.320 1252.832} -status PLACED
place_inst -name r35_0 -location {12364.320 1425.624} -status PLACED
place_inst -name r35_1 -location {12364.320 1598.416} -status PLACED
place_inst -name r35_2 -location {12364.320 1771.208} -status PLACED
place_inst -name b35 -location {12364.320 1944.000} -status PLACED
place_inst -name r36_0 -location {12545.520 1252.832} -status PLACED
place_inst -name r36_1 -location {12726.720 1252.832} -status PLACED
place_inst -name r36_2 -location {12907.920 1252.832} -status PLACED
place_inst -name b36 -location {13089.120 1252.832} -status PLACED
place_inst -name r37_0 -location {13268.640 1252.832} -status PLACED
place_inst -name r37_1 -location {13448.160 1252.832} -status PLACED
place_inst -name r37_2 -location {13627.680 1252.832} -status PLACED
place_inst -name b37 -location {13807.200 1252.832} -status PLACED
place_inst -name r38_0 -location {13807.200 1425.624} -status PLACED
place_inst -name r38_1 -location {13807.200 1598.416} -status PLACED
place_inst -name r38_2 -location {13807.200 1771.208} -status PLACED
place_inst -name b38 -location {13807.200 1944.000} -status PLACED
place_inst -name r39_0 -location {13987.560 1252.832} -status PLACED
place_inst -name r39_1 -location {14167.920 1252.832} -status PLACED
place_inst -name r39_2 -location {14348.280 1252.832} -status PLACED
place_inst -name r39_3 -location {14528.640 1252.832} -status PLACED
place_inst -name r39_4 -location {14709.000 1252.832} -status PLACED
place_inst -name r39_5 -location {14889.360 1252.832} -status PLACED
place_inst -name r39_6 -location {15069.720 1252.832} -status PLACED
place_inst -name b39 -location {15250.080 1252.832} -status PLACED
place_inst -name r40_0 -location {15250.080 1425.624} -status PLACED
place_inst -name r40_1 -location {15250.080 1598.416} -status PLACED
place_inst -name r40_2 -location {15250.080 1771.208} -status PLACED
place_inst -name b40 -location {15250.080 1944.000} -status PLACED
place_inst -name r41_0 -location {15431.280 1252.832} -status PLACED
place_inst -name r41_1 -location {15612.480 1252.832} -status PLACED
place_inst -name r41_2 -location {15793.680 1252.832} -status PLACED
place_inst -name b41 -location {15974.880 1252.832} -status PLACED
place_inst -name r42_0 -location {8588.341 3594.272} -status PLACED
place_inst -name r42_1 -location {8415.721 3594.272} -status PLACED
place_inst -name r42_2 -location {8243.102 3594.272} -status PLACED
place_inst -name b42 -location {8070.483 3594.272} -status PLACED
place_inst -name r43_0 -location {8011.323 3480.493} -status PLACED
place_inst -name r43_1 -location {7952.162 3366.715} -status PLACED
place_inst -name r43_2 -location {7893.002 3260.040} -status PLACED
place_inst -name r43_3 -location {7833.841 3260.040} -status PLACED
place_inst -name r43_4 -location {7774.681 2934.840} -status PLACED
place_inst -name b43 -location {7715.520 2911.600} -status PLACED
place_inst -name r44_0 -location {7894.466 3593.672} -status PLACED
place_inst -name r44_1 -location {7716.174 3593.672} -status PLACED
place_inst -name r44_2 -location {7714.920 3770.709} -status PLACED
place_inst -name b44 -location {7715.520 3948.400} -status PLACED
place_inst -name r45_0 -location {7893.243 3595.240} -status PLACED
place_inst -name r45_1 -location {7716.002 3595.240} -status PLACED
place_inst -name r45_2 -location {7538.762 3594.756} -status PLACED
place_inst -name r45_3 -location {7362.280 3595.240} -status PLACED
place_inst -name r45_4 -location {7184.280 3595.079} -status PLACED
place_inst -name b45 -location {7007.040 3595.240} -status PLACED
place_inst -name r46_0 -location {7007.040 3289.080} -status PLACED
place_inst -name r46_1 -location {7007.040 3253.420} -status PLACED
place_inst -name r46_2 -location {7007.040 3082.510} -status PLACED
place_inst -name b46 -location {7007.040 2911.600} -status PLACED
place_inst -name r47_0 -location {7007.040 3771.820} -status PLACED
place_inst -name b47 -location {7007.040 3948.400} -status PLACED
place_inst -name r48_0 -location {6829.920 3595.240} -status PLACED
place_inst -name r48_1 -location {6653.800 3595.240} -status PLACED
place_inst -name r48_2 -location {6475.680 3595.240} -status PLACED
place_inst -name b48 -location {6298.560 3595.240} -status PLACED
place_inst -name r49_0 -location {6298.560 3289.080} -status PLACED
place_inst -name r49_1 -location {6298.560 3253.420} -status PLACED
place_inst -name r49_2 -location {6298.560 3082.510} -status PLACED
place_inst -name b49 -location {6298.560 2911.600} -status PLACED
place_inst -name r50_0 -location {6298.560 3771.820} -status PLACED
place_inst -name b50 -location {6298.560 3948.400} -status PLACED
place_inst -name r51_0 -location {6121.440 3595.240} -status PLACED
place_inst -name r51_1 -location {5945.320 3595.240} -status PLACED
place_inst -name r51_2 -location {5767.200 3595.240} -status PLACED
place_inst -name b51 -location {5590.080 3595.240} -status PLACED
place_inst -name r52_0 -location {5590.080 3289.080} -status PLACED
place_inst -name r52_1 -location {5590.080 3253.420} -status PLACED
place_inst -name r52_2 -location {5590.080 3082.510} -status PLACED
place_inst -name b52 -location {5590.080 2911.600} -status PLACED
place_inst -name r53_0 -location {5590.080 3771.820} -status PLACED
place_inst -name b53 -location {5590.080 3948.400} -status PLACED
place_inst -name r54_0 -location {5412.960 3595.240} -status PLACED
place_inst -name r54_1 -location {5236.840 3595.240} -status PLACED
place_inst -name r54_2 -location {5058.720 3595.240} -status PLACED
place_inst -name b54 -location {4881.600 3595.240} -status PLACED
place_inst -name r55_0 -location {4881.600 3289.080} -status PLACED
place_inst -name r55_1 -location {4881.600 3253.420} -status PLACED
place_inst -name r55_2 -location {4881.600 3082.510} -status PLACED
place_inst -name b55 -location {4881.600 2911.600} -status PLACED
place_inst -name r56_0 -location {4881.600 3771.820} -status PLACED
place_inst -name b56 -location {4881.600 3948.400} -status PLACED
place_inst -name r57_0 -location {4704.480 3595.240} -status PLACED
place_inst -name r57_1 -location {4528.360 3595.240} -status PLACED
place_inst -name r57_2 -location {4350.240 3595.240} -status PLACED
place_inst -name b57 -location {4173.120 3595.240} -status PLACED
place_inst -name r58_0 -location {4173.120 3289.080} -status PLACED
place_inst -name r58_1 -location {4173.120 3253.420} -status PLACED
place_inst -name r58_2 -location {4173.120 3082.510} -status PLACED
place_inst -name b58 -location {4173.120 2911.600} -status PLACED
place_inst -name r59_0 -location {4173.120 3771.820} -status PLACED
place_inst -name b59 -location {4173.120 3948.400} -status PLACED
place_inst -name r60_0 -location {3996.000 3595.240} -status PLACED
place_inst -name r60_1 -location {3819.880 3595.240} -status PLACED
place_inst -name r60_2 -location {3641.760 3595.240} -status PLACED
place_inst -name b60 -location {3464.640 3595.240} -status PLACED
place_inst -name r61_0 -location {3464.640 3289.080} -status PLACED
place_inst -name r61_1 -location {3464.640 3253.420} -status PLACED
place_inst -name r61_2 -location {3464.640 3082.510} -status PLACED
place_inst -name b61 -location {3464.640 2911.600} -status PLACED
place_inst -name r62_0 -location {3464.640 3771.820} -status PLACED
place_inst -name b62 -location {3464.640 3948.400} -status PLACED
place_inst -name r63_0 -location {3287.520 3595.240} -status PLACED
place_inst -name r63_1 -location {3109.400 3595.240} -status PLACED
place_inst -name r63_2 -location {2933.280 3595.240} -status PLACED
place_inst -name b63 -location {2756.160 3595.240} -status PLACED
place_inst -name r64_0 -location {2756.160 3289.080} -status PLACED
place_inst -name r64_1 -location {2756.160 3253.420} -status PLACED
place_inst -name r64_2 -location {2756.160 3082.510} -status PLACED
place_inst -name b64 -location {2756.160 2911.600} -status PLACED
place_inst -name r65_0 -location {2756.160 3771.820} -status PLACED
place_inst -name b65 -location {2756.160 3948.400} -status PLACED
place_inst -name r66_0 -location {2579.040 3595.240} -status PLACED
place_inst -name r66_1 -location {2402.920 3595.240} -status PLACED
place_inst -name r66_2 -location {2224.800 3595.240} -status PLACED
place_inst -name b66 -location {2047.680 3595.240} -status PLACED
place_inst -name r67_0 -location {2047.680 3289.080} -status PLACED
place_inst -name r67_1 -location {2047.680 3253.420} -status PLACED
place_inst -name r67_2 -location {2047.680 3082.510} -status PLACED
place_inst -name b67 -location {2047.680 2911.600} -status PLACED
place_inst -name r68_0 -location {2047.680 3771.820} -status PLACED
place_inst -name b68 -location {2047.680 3948.400} -status PLACED
place_inst -name r69_0 -location {1870.560 3595.240} -status PLACED
place_inst -name r69_1 -location {1694.440 3595.240} -status PLACED
place_inst -name r69_2 -location {1516.320 3595.240} -status PLACED
place_inst -name b69 -location {1339.200 3595.240} -status PLACED
place_inst -name r70_0 -location {1339.200 3289.080} -status PLACED
place_inst -name r70_1 -location {1339.200 3253.420} -status PLACED
place_inst -name r70_2 -location {1339.200 3082.510} -status PLACED
place_inst -name b70 -location {1339.200 2911.600} -status PLACED
place_inst -name r71_0 -location {1339.200 3771.820} -status PLACED
place_inst -name b71 -location {1339.200 3948.400} -status PLACED
place_inst -name r72_0 -location {1162.080 3595.240} -status PLACED
place_inst -name r72_1 -location {985.960 3595.240} -status PLACED
place_inst -name r72_2 -location {807.840 3595.240} -status PLACED
place_inst -name b72 -location {630.720 3595.240} -status PLACED
place_inst -name r73_0 -location {630.720 3289.080} -status PLACED
place_inst -name r73_1 -location {630.720 3253.420} -status PLACED
place_inst -name r73_2 -location {630.720 3082.510} -status PLACED
place_inst -name b73 -location {630.720 2911.600} -status PLACED
place_inst -name r74_0 -location {630.720 3771.820} -status PLACED
place_inst -name b74 -location {630.720 3948.400} -status PLACED
place_inst -name r75_0 -location {520.440 3595.240} -status PLACED
place_inst -name r75_1 -location {410.160 3595.240} -status PLACED
place_inst -name r75_2 -location {299.880 3595.240} -status PLACED
place_inst -name b75 -location {189.600 3595.240} -status PLACED
place_inst -name r76_0 -location {189.600 3465.380} -status PLACED
place_inst -name r76_1 -location {189.600 3335.520} -status PLACED
place_inst -name r76_2 -location {189.600 3205.660} -status PLACED
place_inst -name b76 -location {189.600 3075.800} -status PLACED
place_inst -name r77_0 -location {189.600 3724.580} -status PLACED
place_inst -name r77_1 -location {189.600 3853.920} -status PLACED
place_inst -name r77_2 -location {189.600 3983.260} -status PLACED
place_inst -name b77 -location {189.600 4112.600} -status PLACED
place_inst -name r78_0 -location {8933.625 3594.272} -status PLACED
place_inst -name r78_1 -location {9106.290 3594.272} -status PLACED
place_inst -name r78_2 -location {9278.955 3594.272} -status PLACED
place_inst -name b78 -location {9451.620 3594.272} -status PLACED
place_inst -name r79_0 -location {9510.750 3480.493} -status PLACED
place_inst -name r79_1 -location {9569.880 3366.715} -status PLACED
place_inst -name r79_2 -location {9629.010 3260.040} -status PLACED
place_inst -name r79_3 -location {9688.140 3260.040} -status PLACED
place_inst -name r79_4 -location {9747.270 2934.840} -status PLACED
place_inst -name b79 -location {9806.400 2911.600} -status PLACED
place_inst -name r80_0 -location {9451.020 3772.545} -status PLACED
place_inst -name r80_1 -location {9453.160 3950.072} -status PLACED
place_inst -name r80_2 -location {9631.239 3950.072} -status PLACED
place_inst -name b80 -location {9806.400 3948.400} -status PLACED
place_inst -name r81_0 -location {9628.830 3595.240} -status PLACED
place_inst -name r81_1 -location {9806.040 3595.240} -status PLACED
place_inst -name r81_2 -location {9983.250 3594.756} -status PLACED
place_inst -name r81_3 -location {10159.640 3595.240} -status PLACED
place_inst -name r81_4 -location {10337.670 3595.079} -status PLACED
place_inst -name b81 -location {10514.880 3595.240} -status PLACED
place_inst -name r82_0 -location {10514.880 3289.080} -status PLACED
place_inst -name r82_1 -location {10514.880 3253.420} -status PLACED
place_inst -name r82_2 -location {10514.880 3082.510} -status PLACED
place_inst -name b82 -location {10514.880 2911.600} -status PLACED
place_inst -name r83_0 -location {10514.880 3771.820} -status PLACED
place_inst -name b83 -location {10514.880 3948.400} -status PLACED
place_inst -name r84_0 -location {10692.000 3595.240} -status PLACED
place_inst -name r84_1 -location {10868.120 3595.240} -status PLACED
place_inst -name r84_2 -location {11046.240 3595.240} -status PLACED
place_inst -name b84 -location {11223.360 3595.240} -status PLACED
place_inst -name r85_0 -location {11223.360 3289.080} -status PLACED
place_inst -name r85_1 -location {11223.360 3253.420} -status PLACED
place_inst -name r85_2 -location {11223.360 3082.510} -status PLACED
place_inst -name b85 -location {11223.360 2911.600} -status PLACED
place_inst -name r86_0 -location {11223.360 3771.820} -status PLACED
place_inst -name b86 -location {11223.360 3948.400} -status PLACED
place_inst -name r87_0 -location {11400.480 3595.240} -status PLACED
place_inst -name r87_1 -location {11576.600 3595.240} -status PLACED
place_inst -name r87_2 -location {11754.720 3595.240} -status PLACED
place_inst -name b87 -location {11931.840 3595.240} -status PLACED
place_inst -name r88_0 -location {11931.840 3289.080} -status PLACED
place_inst -name r88_1 -location {11931.840 3253.420} -status PLACED
place_inst -name r88_2 -location {11931.840 3082.510} -status PLACED
place_inst -name b88 -location {11931.840 2911.600} -status PLACED
place_inst -name r89_0 -location {11931.840 3771.820} -status PLACED
place_inst -name b89 -location {11931.840 3948.400} -status PLACED
place_inst -name r90_0 -location {12108.960 3595.240} -status PLACED
place_inst -name r90_1 -location {12285.080 3595.240} -status PLACED
place_inst -name r90_2 -location {12463.200 3595.240} -status PLACED
place_inst -name b90 -location {12640.320 3595.240} -status PLACED
place_inst -name r91_0 -location {12640.320 3289.080} -status PLACED
place_inst -name r91_1 -location {12640.320 3253.420} -status PLACED
place_inst -name r91_2 -location {12640.320 3082.510} -status PLACED
place_inst -name b91 -location {12640.320 2911.600} -status PLACED
place_inst -name r92_0 -location {12640.320 3771.820} -status PLACED
place_inst -name b92 -location {12640.320 3948.400} -status PLACED
place_inst -name r93_0 -location {12817.440 3595.240} -status PLACED
place_inst -name r93_1 -location {12993.560 3595.240} -status PLACED
place_inst -name r93_2 -location {13171.680 3595.240} -status PLACED
place_inst -name b93 -location {13348.800 3595.240} -status PLACED
place_inst -name r94_0 -location {13348.800 3289.080} -status PLACED
place_inst -name r94_1 -location {13348.800 3253.420} -status PLACED
place_inst -name r94_2 -location {13348.800 3082.510} -status PLACED
place_inst -name b94 -location {13348.800 2911.600} -status PLACED
place_inst -name r95_0 -location {13348.800 3771.820} -status PLACED
place_inst -name b95 -location {13348.800 3948.400} -status PLACED
place_inst -name r96_0 -location {13525.920 3595.240} -status PLACED
place_inst -name r96_1 -location {13704.040 3595.240} -status PLACED
place_inst -name r96_2 -location {13880.160 3595.240} -status PLACED
place_inst -name b96 -location {14057.280 3595.240} -status PLACED
place_inst -name r97_0 -location {14057.280 3289.080} -status PLACED
place_inst -name r97_1 -location {14057.280 3253.420} -status PLACED
place_inst -name r97_2 -location {14057.280 3082.510} -status PLACED
place_inst -name b97 -location {14057.280 2911.600} -status PLACED
place_inst -name r98_0 -location {14057.280 3771.820} -status PLACED
place_inst -name b98 -location {14057.280 3948.400} -status PLACED
place_inst -name r99_0 -location {14234.400 3595.240} -status PLACED
place_inst -name r99_1 -location {14410.520 3595.240} -status PLACED
place_inst -name r99_2 -location {14588.640 3595.240} -status PLACED
place_inst -name b99 -location {14765.760 3595.240} -status PLACED
place_inst -name r100_0 -location {14765.760 3289.080} -status PLACED
place_inst -name r100_1 -location {14765.760 3253.420} -status PLACED
place_inst -name r100_2 -location {14765.760 3082.510} -status PLACED
place_inst -name b100 -location {14765.760 2911.600} -status PLACED
place_inst -name r101_0 -location {14765.760 3771.820} -status PLACED
place_inst -name b101 -location {14765.760 3948.400} -status PLACED
place_inst -name r102_0 -location {14942.880 3595.240} -status PLACED
place_inst -name r102_1 -location {15119.000 3595.240} -status PLACED
place_inst -name r102_2 -location {15297.120 3595.240} -status PLACED
place_inst -name b102 -location {15474.240 3595.240} -status PLACED
place_inst -name r103_0 -location {15474.240 3289.080} -status PLACED
place_inst -name r103_1 -location {15474.240 3253.420} -status PLACED
place_inst -name r103_2 -location {15474.240 3082.510} -status PLACED
place_inst -name b103 -location {15474.240 2911.600} -status PLACED
place_inst -name r104_0 -location {15474.240 3771.820} -status PLACED
place_inst -name b104 -location {15474.240 3948.400} -status PLACED
place_inst -name r105_0 -location {15651.360 3595.240} -status PLACED
place_inst -name r105_1 -location {15827.480 3595.240} -status PLACED
place_inst -name r105_2 -location {16005.600 3595.240} -status PLACED
place_inst -name b105 -location {16182.720 3595.240} -status PLACED
place_inst -name r106_0 -location {16182.720 3289.080} -status PLACED
place_inst -name r106_1 -location {16182.720 3253.420} -status PLACED
place_inst -name r106_2 -location {16182.720 3082.510} -status PLACED
place_inst -name b106 -location {16182.720 2911.600} -status PLACED
place_inst -name r107_0 -location {16182.720 3771.820} -status PLACED
place_inst -name b107 -location {16182.720 3948.400} -status PLACED
place_inst -name r108_0 -location {16359.840 3595.240} -status PLACED
place_inst -name r108_1 -location {16535.960 3595.240} -status PLACED
place_inst -name r108_2 -location {16714.080 3595.240} -status PLACED
place_inst -name b108 -location {16891.200 3595.240} -status PLACED
place_inst -name r109_0 -location {16891.200 3289.080} -status PLACED
place_inst -name r109_1 -location {16891.200 3253.420} -status PLACED
place_inst -name r109_2 -location {16891.200 3082.510} -status PLACED
place_inst -name b109 -location {16891.200 2911.600} -status PLACED
place_inst -name r110_0 -location {16891.200 3771.820} -status PLACED
place_inst -name b110 -location {16891.200 3948.400} -status PLACED
place_inst -name r111_0 -location {17001.480 3595.240} -status PLACED
place_inst -name r111_1 -location {17111.760 3595.240} -status PLACED
place_inst -name r111_2 -location {17222.040 3595.240} -status PLACED
place_inst -name b111 -location {17332.320 3595.240} -status PLACED
place_inst -name r112_0 -location {17332.320 3465.380} -status PLACED
place_inst -name r112_1 -location {17332.320 3335.520} -status PLACED
place_inst -name r112_2 -location {17332.320 3205.660} -status PLACED
place_inst -name b112 -location {17332.320 3075.800} -status PLACED
place_inst -name r113_0 -location {17332.320 3724.580} -status PLACED
place_inst -name r113_1 -location {17332.320 3853.920} -status PLACED
place_inst -name r113_2 -location {17332.320 3983.260} -status PLACED
place_inst -name b113 -location {17332.320 4112.600} -status PLACED
place_inst -name r114_0 -location {8588.341 5667.872} -status PLACED
place_inst -name r114_1 -location {8415.721 5667.872} -status PLACED
place_inst -name r114_2 -location {8243.102 5667.872} -status PLACED
place_inst -name b114 -location {8070.483 5667.872} -status PLACED
place_inst -name r115_0 -location {8011.323 5554.093} -status PLACED
place_inst -name r115_1 -location {7952.162 5440.315} -status PLACED
place_inst -name r115_2 -location {7893.002 5333.640} -status PLACED
place_inst -name r115_3 -location {7833.841 5333.640} -status PLACED
place_inst -name r115_4 -location {7774.681 5008.440} -status PLACED
place_inst -name b115 -location {7715.520 4985.200} -status PLACED
place_inst -name r116_0 -location {7894.466 5667.272} -status PLACED
place_inst -name r116_1 -location {7716.174 5667.272} -status PLACED
place_inst -name r116_2 -location {7714.920 5844.309} -status PLACED
place_inst -name b116 -location {7715.520 6022.000} -status PLACED
place_inst -name r117_0 -location {7893.243 5668.840} -status PLACED
place_inst -name r117_1 -location {7716.002 5668.840} -status PLACED
place_inst -name r117_2 -location {7538.762 5668.356} -status PLACED
place_inst -name r117_3 -location {7362.280 5668.840} -status PLACED
place_inst -name r117_4 -location {7184.280 5668.679} -status PLACED
place_inst -name b117 -location {7007.040 5668.840} -status PLACED
place_inst -name r118_0 -location {7007.040 5362.680} -status PLACED
place_inst -name r118_1 -location {7007.040 5327.020} -status PLACED
place_inst -name r118_2 -location {7007.040 5156.110} -status PLACED
place_inst -name b118 -location {7007.040 4985.200} -status PLACED
place_inst -name r119_0 -location {7007.040 5845.420} -status PLACED
place_inst -name b119 -location {7007.040 6022.000} -status PLACED
place_inst -name r120_0 -location {6829.920 5668.840} -status PLACED
place_inst -name r120_1 -location {6653.800 5668.840} -status PLACED
place_inst -name r120_2 -location {6475.680 5668.840} -status PLACED
place_inst -name b120 -location {6298.560 5668.840} -status PLACED
place_inst -name r121_0 -location {6298.560 5362.680} -status PLACED
place_inst -name r121_1 -location {6298.560 5327.020} -status PLACED
place_inst -name r121_2 -location {6298.560 5156.110} -status PLACED
place_inst -name b121 -location {6298.560 4985.200} -status PLACED
place_inst -name r122_0 -location {6298.560 5845.420} -status PLACED
place_inst -name b122 -location {6298.560 6022.000} -status PLACED
place_inst -name r123_0 -location {6121.440 5668.840} -status PLACED
place_inst -name r123_1 -location {5945.320 5668.840} -status PLACED
place_inst -name r123_2 -location {5767.200 5668.840} -status PLACED
place_inst -name b123 -location {5590.080 5668.840} -status PLACED
place_inst -name r124_0 -location {5590.080 5362.680} -status PLACED
place_inst -name r124_1 -location {5590.080 5327.020} -status PLACED
place_inst -name r124_2 -location {5590.080 5156.110} -status PLACED
place_inst -name b124 -location {5590.080 4985.200} -status PLACED
place_inst -name r125_0 -location {5590.080 5845.420} -status PLACED
place_inst -name b125 -location {5590.080 6022.000} -status PLACED
place_inst -name r126_0 -location {5412.960 5668.840} -status PLACED
place_inst -name r126_1 -location {5236.840 5668.840} -status PLACED
place_inst -name r126_2 -location {5058.720 5668.840} -status PLACED
place_inst -name b126 -location {4881.600 5668.840} -status PLACED
place_inst -name r127_0 -location {4881.600 5362.680} -status PLACED
place_inst -name r127_1 -location {4881.600 5327.020} -status PLACED
place_inst -name r127_2 -location {4881.600 5156.110} -status PLACED
place_inst -name b127 -location {4881.600 4985.200} -status PLACED
place_inst -name r128_0 -location {4881.600 5845.420} -status PLACED
place_inst -name b128 -location {4881.600 6022.000} -status PLACED
place_inst -name r129_0 -location {4704.480 5668.840} -status PLACED
place_inst -name r129_1 -location {4528.360 5668.840} -status PLACED
place_inst -name r129_2 -location {4350.240 5668.840} -status PLACED
place_inst -name b129 -location {4173.120 5668.840} -status PLACED
place_inst -name r130_0 -location {4173.120 5362.680} -status PLACED
place_inst -name r130_1 -location {4173.120 5327.020} -status PLACED
place_inst -name r130_2 -location {4173.120 5156.110} -status PLACED
place_inst -name b130 -location {4173.120 4985.200} -status PLACED
place_inst -name r131_0 -location {4173.120 5845.420} -status PLACED
place_inst -name b131 -location {4173.120 6022.000} -status PLACED
place_inst -name r132_0 -location {3996.000 5668.840} -status PLACED
place_inst -name r132_1 -location {3819.880 5668.840} -status PLACED
place_inst -name r132_2 -location {3641.760 5668.840} -status PLACED
place_inst -name b132 -location {3464.640 5668.840} -status PLACED
place_inst -name r133_0 -location {3464.640 5362.680} -status PLACED
place_inst -name r133_1 -location {3464.640 5327.020} -status PLACED
place_inst -name r133_2 -location {3464.640 5156.110} -status PLACED
place_inst -name b133 -location {3464.640 4985.200} -status PLACED
place_inst -name r134_0 -location {3464.640 5845.420} -status PLACED
place_inst -name b134 -location {3464.640 6022.000} -status PLACED
place_inst -name r135_0 -location {3287.520 5668.840} -status PLACED
place_inst -name r135_1 -location {3109.400 5668.840} -status PLACED
place_inst -name r135_2 -location {2933.280 5668.840} -status PLACED
place_inst -name b135 -location {2756.160 5668.840} -status PLACED
place_inst -name r136_0 -location {2756.160 5362.680} -status PLACED
place_inst -name r136_1 -location {2756.160 5327.020} -status PLACED
place_inst -name r136_2 -location {2756.160 5156.110} -status PLACED
place_inst -name b136 -location {2756.160 4985.200} -status PLACED
place_inst -name r137_0 -location {2756.160 5845.420} -status PLACED
place_inst -name b137 -location {2756.160 6022.000} -status PLACED
place_inst -name r138_0 -location {2579.040 5668.840} -status PLACED
place_inst -name r138_1 -location {2402.920 5668.840} -status PLACED
place_inst -name r138_2 -location {2224.800 5668.840} -status PLACED
place_inst -name b138 -location {2047.680 5668.840} -status PLACED
place_inst -name r139_0 -location {2047.680 5362.680} -status PLACED
place_inst -name r139_1 -location {2047.680 5327.020} -status PLACED
place_inst -name r139_2 -location {2047.680 5156.110} -status PLACED
place_inst -name b139 -location {2047.680 4985.200} -status PLACED
place_inst -name r140_0 -location {2047.680 5845.420} -status PLACED
place_inst -name b140 -location {2047.680 6022.000} -status PLACED
place_inst -name r141_0 -location {1870.560 5668.840} -status PLACED
place_inst -name r141_1 -location {1694.440 5668.840} -status PLACED
place_inst -name r141_2 -location {1516.320 5668.840} -status PLACED
place_inst -name b141 -location {1339.200 5668.840} -status PLACED
place_inst -name r142_0 -location {1339.200 5362.680} -status PLACED
place_inst -name r142_1 -location {1339.200 5327.020} -status PLACED
place_inst -name r142_2 -location {1339.200 5156.110} -status PLACED
place_inst -name b142 -location {1339.200 4985.200} -status PLACED
place_inst -name r143_0 -location {1339.200 5845.420} -status PLACED
place_inst -name b143 -location {1339.200 6022.000} -status PLACED
place_inst -name r144_0 -location {1162.080 5668.840} -status PLACED
place_inst -name r144_1 -location {985.960 5668.840} -status PLACED
place_inst -name r144_2 -location {807.840 5668.840} -status PLACED
place_inst -name b144 -location {630.720 5668.840} -status PLACED
place_inst -name r145_0 -location {630.720 5362.680} -status PLACED
place_inst -name r145_1 -location {630.720 5327.020} -status PLACED
place_inst -name r145_2 -location {630.720 5156.110} -status PLACED
place_inst -name b145 -location {630.720 4985.200} -status PLACED
place_inst -name r146_0 -location {630.720 5845.420} -status PLACED
place_inst -name b146 -location {630.720 6022.000} -status PLACED
place_inst -name r147_0 -location {520.440 5668.840} -status PLACED
place_inst -name r147_1 -location {410.160 5668.840} -status PLACED
place_inst -name r147_2 -location {299.880 5668.840} -status PLACED
place_inst -name b147 -location {189.600 5668.840} -status PLACED
place_inst -name r148_0 -location {189.600 5538.980} -status PLACED
place_inst -name r148_1 -location {189.600 5409.120} -status PLACED
place_inst -name r148_2 -location {189.600 5279.260} -status PLACED
place_inst -name b148 -location {189.600 5149.400} -status PLACED
place_inst -name r149_0 -location {189.600 5798.180} -status PLACED
place_inst -name r149_1 -location {189.600 5927.520} -status PLACED
place_inst -name r149_2 -location {189.600 6056.860} -status PLACED
place_inst -name b149 -location {189.600 6186.200} -status PLACED
place_inst -name r150_0 -location {8933.625 5667.872} -status PLACED
place_inst -name r150_1 -location {9106.290 5667.872} -status PLACED
place_inst -name r150_2 -location {9278.955 5667.872} -status PLACED
place_inst -name b150 -location {9451.620 5667.872} -status PLACED
place_inst -name r151_0 -location {9510.750 5554.093} -status PLACED
place_inst -name r151_1 -location {9569.880 5440.315} -status PLACED
place_inst -name r151_2 -location {9629.010 5333.640} -status PLACED
place_inst -name r151_3 -location {9688.140 5333.640} -status PLACED
place_inst -name r151_4 -location {9747.270 5008.440} -status PLACED
place_inst -name b151 -location {9806.400 4985.200} -status PLACED
place_inst -name r152_0 -location {9451.020 5846.145} -status PLACED
place_inst -name r152_1 -location {9453.160 6023.672} -status PLACED
place_inst -name r152_2 -location {9631.239 6023.672} -status PLACED
place_inst -name b152 -location {9806.400 6022.000} -status PLACED
place_inst -name r153_0 -location {9628.830 5668.840} -status PLACED
place_inst -name r153_1 -location {9806.040 5668.840} -status PLACED
place_inst -name r153_2 -location {9983.250 5668.356} -status PLACED
place_inst -name r153_3 -location {10159.640 5668.840} -status PLACED
place_inst -name r153_4 -location {10337.670 5668.679} -status PLACED
place_inst -name b153 -location {10514.880 5668.840} -status PLACED
place_inst -name r154_0 -location {10514.880 5362.680} -status PLACED
place_inst -name r154_1 -location {10514.880 5327.020} -status PLACED
place_inst -name r154_2 -location {10514.880 5156.110} -status PLACED
place_inst -name b154 -location {10514.880 4985.200} -status PLACED
place_inst -name r155_0 -location {10514.880 5845.420} -status PLACED
place_inst -name b155 -location {10514.880 6022.000} -status PLACED
place_inst -name r156_0 -location {10692.000 5668.840} -status PLACED
place_inst -name r156_1 -location {10868.120 5668.840} -status PLACED
place_inst -name r156_2 -location {11046.240 5668.840} -status PLACED
place_inst -name b156 -location {11223.360 5668.840} -status PLACED
place_inst -name r157_0 -location {11223.360 5362.680} -status PLACED
place_inst -name r157_1 -location {11223.360 5327.020} -status PLACED
place_inst -name r157_2 -location {11223.360 5156.110} -status PLACED
place_inst -name b157 -location {11223.360 4985.200} -status PLACED
place_inst -name r158_0 -location {11223.360 5845.420} -status PLACED
place_inst -name b158 -location {11223.360 6022.000} -status PLACED
place_inst -name r159_0 -location {11400.480 5668.840} -status PLACED
place_inst -name r159_1 -location {11576.600 5668.840} -status PLACED
place_inst -name r159_2 -location {11754.720 5668.840} -status PLACED
place_inst -name b159 -location {11931.840 5668.840} -status PLACED
place_inst -name r160_0 -location {11931.840 5362.680} -status PLACED
place_inst -name r160_1 -location {11931.840 5327.020} -status PLACED
place_inst -name r160_2 -location {11931.840 5156.110} -status PLACED
place_inst -name b160 -location {11931.840 4985.200} -status PLACED
place_inst -name r161_0 -location {11931.840 5845.420} -status PLACED
place_inst -name b161 -location {11931.840 6022.000} -status PLACED
place_inst -name r162_0 -location {12108.960 5668.840} -status PLACED
place_inst -name r162_1 -location {12285.080 5668.840} -status PLACED
place_inst -name r162_2 -location {12463.200 5668.840} -status PLACED
place_inst -name b162 -location {12640.320 5668.840} -status PLACED
place_inst -name r163_0 -location {12640.320 5362.680} -status PLACED
place_inst -name r163_1 -location {12640.320 5327.020} -status PLACED
place_inst -name r163_2 -location {12640.320 5156.110} -status PLACED
place_inst -name b163 -location {12640.320 4985.200} -status PLACED
place_inst -name r164_0 -location {12640.320 5845.420} -status PLACED
place_inst -name b164 -location {12640.320 6022.000} -status PLACED
place_inst -name r165_0 -location {12817.440 5668.840} -status PLACED
place_inst -name r165_1 -location {12993.560 5668.840} -status PLACED
place_inst -name r165_2 -location {13171.680 5668.840} -status PLACED
place_inst -name b165 -location {13348.800 5668.840} -status PLACED
place_inst -name r166_0 -location {13348.800 5362.680} -status PLACED
place_inst -name r166_1 -location {13348.800 5327.020} -status PLACED
place_inst -name r166_2 -location {13348.800 5156.110} -status PLACED
place_inst -name b166 -location {13348.800 4985.200} -status PLACED
place_inst -name r167_0 -location {13348.800 5845.420} -status PLACED
place_inst -name b167 -location {13348.800 6022.000} -status PLACED
place_inst -name r168_0 -location {13525.920 5668.840} -status PLACED
place_inst -name r168_1 -location {13704.040 5668.840} -status PLACED
place_inst -name r168_2 -location {13880.160 5668.840} -status PLACED
place_inst -name b168 -location {14057.280 5668.840} -status PLACED
place_inst -name r169_0 -location {14057.280 5362.680} -status PLACED
place_inst -name r169_1 -location {14057.280 5327.020} -status PLACED
place_inst -name r169_2 -location {14057.280 5156.110} -status PLACED
place_inst -name b169 -location {14057.280 4985.200} -status PLACED
place_inst -name r170_0 -location {14057.280 5845.420} -status PLACED
place_inst -name b170 -location {14057.280 6022.000} -status PLACED
place_inst -name r171_0 -location {14234.400 5668.840} -status PLACED
place_inst -name r171_1 -location {14410.520 5668.840} -status PLACED
place_inst -name r171_2 -location {14588.640 5668.840} -status PLACED
place_inst -name b171 -location {14765.760 5668.840} -status PLACED
place_inst -name r172_0 -location {14765.760 5362.680} -status PLACED
place_inst -name r172_1 -location {14765.760 5327.020} -status PLACED
place_inst -name r172_2 -location {14765.760 5156.110} -status PLACED
place_inst -name b172 -location {14765.760 4985.200} -status PLACED
place_inst -name r173_0 -location {14765.760 5845.420} -status PLACED
place_inst -name b173 -location {14765.760 6022.000} -status PLACED
place_inst -name r174_0 -location {14942.880 5668.840} -status PLACED
place_inst -name r174_1 -location {15119.000 5668.840} -status PLACED
place_inst -name r174_2 -location {15297.120 5668.840} -status PLACED
place_inst -name b174 -location {15474.240 5668.840} -status PLACED
place_inst -name r175_0 -location {15474.240 5362.680} -status PLACED
place_inst -name r175_1 -location {15474.240 5327.020} -status PLACED
place_inst -name r175_2 -location {15474.240 5156.110} -status PLACED
place_inst -name b175 -location {15474.240 4985.200} -status PLACED
place_inst -name r176_0 -location {15474.240 5845.420} -status PLACED
place_inst -name b176 -location {15474.240 6022.000} -status PLACED
place_inst -name r177_0 -location {15651.360 5668.840} -status PLACED
place_inst -name r177_1 -location {15827.480 5668.840} -status PLACED
place_inst -name r177_2 -location {16005.600 5668.840} -status PLACED
place_inst -name b177 -location {16182.720 5668.840} -status PLACED
place_inst -name r178_0 -location {16182.720 5362.680} -status PLACED
place_inst -name r178_1 -location {16182.720 5327.020} -status PLACED
place_inst -name r178_2 -location {16182.720 5156.110} -status PLACED
place_inst -name b178 -location {16182.720 4985.200} -status PLACED
place_inst -name r179_0 -location {16182.720 5845.420} -status PLACED
place_inst -name b179 -location {16182.720 6022.000} -status PLACED
place_inst -name r180_0 -location {16359.840 5668.840} -status PLACED
place_inst -name r180_1 -location {16535.960 5668.840} -status PLACED
place_inst -name r180_2 -location {16714.080 5668.840} -status PLACED
place_inst -name b180 -location {16891.200 5668.840} -status PLACED
place_inst -name r181_0 -location {16891.200 5362.680} -status PLACED
place_inst -name r181_1 -location {16891.200 5327.020} -status PLACED
place_inst -name r181_2 -location {16891.200 5156.110} -status PLACED
place_inst -name b181 -location {16891.200 4985.200} -status PLACED
place_inst -name r182_0 -location {16891.200 5845.420} -status PLACED
place_inst -name b182 -location {16891.200 6022.000} -status PLACED
place_inst -name r183_0 -location {17001.480 5668.840} -status PLACED
place_inst -name r183_1 -location {17111.760 5668.840} -status PLACED
place_inst -name r183_2 -location {17222.040 5668.840} -status PLACED
place_inst -name b183 -location {17332.320 5668.840} -status PLACED
place_inst -name r184_0 -location {17332.320 5538.980} -status PLACED
place_inst -name r184_1 -location {17332.320 5409.120} -status PLACED
place_inst -name r184_2 -location {17332.320 5279.260} -status PLACED
place_inst -name b184 -location {17332.320 5149.400} -status PLACED
place_inst -name r185_0 -location {17332.320 5798.180} -status PLACED
place_inst -name r185_1 -location {17332.320 5927.520} -status PLACED
place_inst -name r185_2 -location {17332.320 6056.860} -status PLACED
place_inst -name b185 -location {17332.320 6186.200} -status PLACED
place_inst -name r186_0 -location {8588.341 7741.472} -status PLACED
place_inst -name r186_1 -location {8415.721 7741.472} -status PLACED
place_inst -name r186_2 -location {8243.102 7741.472} -status PLACED
place_inst -name b186 -location {8070.483 7741.472} -status PLACED
place_inst -name r187_0 -location {8011.323 7627.693} -status PLACED
place_inst -name r187_1 -location {7952.162 7513.915} -status PLACED
place_inst -name r187_2 -location {7893.002 7407.240} -status PLACED
place_inst -name r187_3 -location {7833.841 7407.240} -status PLACED
place_inst -name r187_4 -location {7774.681 7082.040} -status PLACED
place_inst -name b187 -location {7715.520 7058.800} -status PLACED
place_inst -name r188_0 -location {7894.466 7740.872} -status PLACED
place_inst -name r188_1 -location {7716.174 7740.872} -status PLACED
place_inst -name r188_2 -location {7714.920 7917.909} -status PLACED
place_inst -name b188 -location {7715.520 8095.600} -status PLACED
place_inst -name r189_0 -location {7893.243 7742.440} -status PLACED
place_inst -name r189_1 -location {7716.002 7742.440} -status PLACED
place_inst -name r189_2 -location {7538.762 7741.956} -status PLACED
place_inst -name r189_3 -location {7362.280 7742.440} -status PLACED
place_inst -name r189_4 -location {7184.280 7742.279} -status PLACED
place_inst -name b189 -location {7007.040 7742.440} -status PLACED
place_inst -name r190_0 -location {7007.040 7436.280} -status PLACED
place_inst -name r190_1 -location {7007.040 7400.620} -status PLACED
place_inst -name r190_2 -location {7007.040 7229.710} -status PLACED
place_inst -name b190 -location {7007.040 7058.800} -status PLACED
place_inst -name r191_0 -location {7007.040 7919.020} -status PLACED
place_inst -name b191 -location {7007.040 8095.600} -status PLACED
place_inst -name r192_0 -location {6829.920 7742.440} -status PLACED
place_inst -name r192_1 -location {6653.800 7742.440} -status PLACED
place_inst -name r192_2 -location {6475.680 7742.440} -status PLACED
place_inst -name b192 -location {6298.560 7742.440} -status PLACED
place_inst -name r193_0 -location {6298.560 7436.280} -status PLACED
place_inst -name r193_1 -location {6298.560 7400.620} -status PLACED
place_inst -name r193_2 -location {6298.560 7229.710} -status PLACED
place_inst -name b193 -location {6298.560 7058.800} -status PLACED
place_inst -name r194_0 -location {6298.560 7919.020} -status PLACED
place_inst -name b194 -location {6298.560 8095.600} -status PLACED
place_inst -name r195_0 -location {6121.440 7742.440} -status PLACED
place_inst -name r195_1 -location {5945.320 7742.440} -status PLACED
place_inst -name r195_2 -location {5767.200 7742.440} -status PLACED
place_inst -name b195 -location {5590.080 7742.440} -status PLACED
place_inst -name r196_0 -location {5590.080 7436.280} -status PLACED
place_inst -name r196_1 -location {5590.080 7400.620} -status PLACED
place_inst -name r196_2 -location {5590.080 7229.710} -status PLACED
place_inst -name b196 -location {5590.080 7058.800} -status PLACED
place_inst -name r197_0 -location {5590.080 7919.020} -status PLACED
place_inst -name b197 -location {5590.080 8095.600} -status PLACED
place_inst -name r198_0 -location {5412.960 7742.440} -status PLACED
place_inst -name r198_1 -location {5236.840 7742.440} -status PLACED
place_inst -name r198_2 -location {5058.720 7742.440} -status PLACED
place_inst -name b198 -location {4881.600 7742.440} -status PLACED
place_inst -name r199_0 -location {4881.600 7436.280} -status PLACED
place_inst -name r199_1 -location {4881.600 7400.620} -status PLACED
place_inst -name r199_2 -location {4881.600 7229.710} -status PLACED
place_inst -name b199 -location {4881.600 7058.800} -status PLACED
place_inst -name r200_0 -location {4881.600 7919.020} -status PLACED
place_inst -name b200 -location {4881.600 8095.600} -status PLACED
place_inst -name r201_0 -location {4704.480 7742.440} -status PLACED
place_inst -name r201_1 -location {4528.360 7742.440} -status PLACED
place_inst -name r201_2 -location {4350.240 7742.440} -status PLACED
place_inst -name b201 -location {4173.120 7742.440} -status PLACED
place_inst -name r202_0 -location {4173.120 7436.280} -status PLACED
place_inst -name r202_1 -location {4173.120 7400.620} -status PLACED
place_inst -name r202_2 -location {4173.120 7229.710} -status PLACED
place_inst -name b202 -location {4173.120 7058.800} -status PLACED
place_inst -name r203_0 -location {4173.120 7919.020} -status PLACED
place_inst -name b203 -location {4173.120 8095.600} -status PLACED
place_inst -name r204_0 -location {3996.000 7742.440} -status PLACED
place_inst -name r204_1 -location {3819.880 7742.440} -status PLACED
place_inst -name r204_2 -location {3641.760 7742.440} -status PLACED
place_inst -name b204 -location {3464.640 7742.440} -status PLACED
place_inst -name r205_0 -location {3464.640 7436.280} -status PLACED
place_inst -name r205_1 -location {3464.640 7400.620} -status PLACED
place_inst -name r205_2 -location {3464.640 7229.710} -status PLACED
place_inst -name b205 -location {3464.640 7058.800} -status PLACED
place_inst -name r206_0 -location {3464.640 7919.020} -status PLACED
place_inst -name b206 -location {3464.640 8095.600} -status PLACED
place_inst -name r207_0 -location {3287.520 7742.440} -status PLACED
place_inst -name r207_1 -location {3109.400 7742.440} -status PLACED
place_inst -name r207_2 -location {2933.280 7742.440} -status PLACED
place_inst -name b207 -location {2756.160 7742.440} -status PLACED
place_inst -name r208_0 -location {2756.160 7436.280} -status PLACED
place_inst -name r208_1 -location {2756.160 7400.620} -status PLACED
place_inst -name r208_2 -location {2756.160 7229.710} -status PLACED
place_inst -name b208 -location {2756.160 7058.800} -status PLACED
place_inst -name r209_0 -location {2756.160 7919.020} -status PLACED
place_inst -name b209 -location {2756.160 8095.600} -status PLACED
place_inst -name r210_0 -location {2579.040 7742.440} -status PLACED
place_inst -name r210_1 -location {2402.920 7742.440} -status PLACED
place_inst -name r210_2 -location {2224.800 7742.440} -status PLACED
place_inst -name b210 -location {2047.680 7742.440} -status PLACED
place_inst -name r211_0 -location {2047.680 7436.280} -status PLACED
place_inst -name r211_1 -location {2047.680 7400.620} -status PLACED
place_inst -name r211_2 -location {2047.680 7229.710} -status PLACED
place_inst -name b211 -location {2047.680 7058.800} -status PLACED
place_inst -name r212_0 -location {2047.680 7919.020} -status PLACED
place_inst -name b212 -location {2047.680 8095.600} -status PLACED
place_inst -name r213_0 -location {1870.560 7742.440} -status PLACED
place_inst -name r213_1 -location {1694.440 7742.440} -status PLACED
place_inst -name r213_2 -location {1516.320 7742.440} -status PLACED
place_inst -name b213 -location {1339.200 7742.440} -status PLACED
place_inst -name r214_0 -location {1339.200 7436.280} -status PLACED
place_inst -name r214_1 -location {1339.200 7400.620} -status PLACED
place_inst -name r214_2 -location {1339.200 7229.710} -status PLACED
place_inst -name b214 -location {1339.200 7058.800} -status PLACED
place_inst -name r215_0 -location {1339.200 7919.020} -status PLACED
place_inst -name b215 -location {1339.200 8095.600} -status PLACED
place_inst -name r216_0 -location {1162.080 7742.440} -status PLACED
place_inst -name r216_1 -location {985.960 7742.440} -status PLACED
place_inst -name r216_2 -location {807.840 7742.440} -status PLACED
place_inst -name b216 -location {630.720 7742.440} -status PLACED
place_inst -name r217_0 -location {630.720 7436.280} -status PLACED
place_inst -name r217_1 -location {630.720 7400.620} -status PLACED
place_inst -name r217_2 -location {630.720 7229.710} -status PLACED
place_inst -name b217 -location {630.720 7058.800} -status PLACED
place_inst -name r218_0 -location {630.720 7919.020} -status PLACED
place_inst -name b218 -location {630.720 8095.600} -status PLACED
place_inst -name r219_0 -location {520.440 7742.440} -status PLACED
place_inst -name r219_1 -location {410.160 7742.440} -status PLACED
place_inst -name r219_2 -location {299.880 7742.440} -status PLACED
place_inst -name b219 -location {189.600 7742.440} -status PLACED
place_inst -name r220_0 -location {189.600 7612.580} -status PLACED
place_inst -name r220_1 -location {189.600 7482.720} -status PLACED
place_inst -name r220_2 -location {189.600 7352.860} -status PLACED
place_inst -name b220 -location {189.600 7223.000} -status PLACED
place_inst -name r221_0 -location {189.600 7871.780} -status PLACED
place_inst -name r221_1 -location {189.600 8001.120} -status PLACED
place_inst -name r221_2 -location {189.600 8130.460} -status PLACED
place_inst -name b221 -location {189.600 8259.800} -status PLACED
place_inst -name r222_0 -location {8933.625 7741.472} -status PLACED
place_inst -name r222_1 -location {9106.290 7741.472} -status PLACED
place_inst -name r222_2 -location {9278.955 7741.472} -status PLACED
place_inst -name b222 -location {9451.620 7741.472} -status PLACED
place_inst -name r223_0 -location {9510.750 7627.693} -status PLACED
place_inst -name r223_1 -location {9569.880 7513.915} -status PLACED
place_inst -name r223_2 -location {9629.010 7407.240} -status PLACED
place_inst -name r223_3 -location {9688.140 7407.240} -status PLACED
place_inst -name r223_4 -location {9747.270 7082.040} -status PLACED
place_inst -name b223 -location {9806.400 7058.800} -status PLACED
place_inst -name r224_0 -location {9451.020 7919.745} -status PLACED
place_inst -name r224_1 -location {9453.160 8097.272} -status PLACED
place_inst -name r224_2 -location {9631.239 8097.272} -status PLACED
place_inst -name b224 -location {9806.400 8095.600} -status PLACED
place_inst -name r225_0 -location {9628.830 7742.440} -status PLACED
place_inst -name r225_1 -location {9806.040 7742.440} -status PLACED
place_inst -name r225_2 -location {9983.250 7741.956} -status PLACED
place_inst -name r225_3 -location {10159.640 7742.440} -status PLACED
place_inst -name r225_4 -location {10337.670 7742.279} -status PLACED
place_inst -name b225 -location {10514.880 7742.440} -status PLACED
place_inst -name r226_0 -location {10514.880 7436.280} -status PLACED
place_inst -name r226_1 -location {10514.880 7400.620} -status PLACED
place_inst -name r226_2 -location {10514.880 7229.710} -status PLACED
place_inst -name b226 -location {10514.880 7058.800} -status PLACED
place_inst -name r227_0 -location {10514.880 7919.020} -status PLACED
place_inst -name b227 -location {10514.880 8095.600} -status PLACED
place_inst -name r228_0 -location {10692.000 7742.440} -status PLACED
place_inst -name r228_1 -location {10868.120 7742.440} -status PLACED
place_inst -name r228_2 -location {11046.240 7742.440} -status PLACED
place_inst -name b228 -location {11223.360 7742.440} -status PLACED
place_inst -name r229_0 -location {11223.360 7436.280} -status PLACED
place_inst -name r229_1 -location {11223.360 7400.620} -status PLACED
place_inst -name r229_2 -location {11223.360 7229.710} -status PLACED
place_inst -name b229 -location {11223.360 7058.800} -status PLACED
place_inst -name r230_0 -location {11223.360 7919.020} -status PLACED
place_inst -name b230 -location {11223.360 8095.600} -status PLACED
place_inst -name r231_0 -location {11400.480 7742.440} -status PLACED
place_inst -name r231_1 -location {11576.600 7742.440} -status PLACED
place_inst -name r231_2 -location {11754.720 7742.440} -status PLACED
place_inst -name b231 -location {11931.840 7742.440} -status PLACED
place_inst -name r232_0 -location {11931.840 7436.280} -status PLACED
place_inst -name r232_1 -location {11931.840 7400.620} -status PLACED
place_inst -name r232_2 -location {11931.840 7229.710} -status PLACED
place_inst -name b232 -location {11931.840 7058.800} -status PLACED
place_inst -name r233_0 -location {11931.840 7919.020} -status PLACED
place_inst -name b233 -location {11931.840 8095.600} -status PLACED
place_inst -name r234_0 -location {12108.960 7742.440} -status PLACED
place_inst -name r234_1 -location {12285.080 7742.440} -status PLACED
place_inst -name r234_2 -location {12463.200 7742.440} -status PLACED
place_inst -name b234 -location {12640.320 7742.440} -status PLACED
place_inst -name r235_0 -location {12640.320 7436.280} -status PLACED
place_inst -name r235_1 -location {12640.320 7400.620} -status PLACED
place_inst -name r235_2 -location {12640.320 7229.710} -status PLACED
place_inst -name b235 -location {12640.320 7058.800} -status PLACED
place_inst -name r236_0 -location {12640.320 7919.020} -status PLACED
place_inst -name b236 -location {12640.320 8095.600} -status PLACED
place_inst -name r237_0 -location {12817.440 7742.440} -status PLACED
place_inst -name r237_1 -location {12993.560 7742.440} -status PLACED
place_inst -name r237_2 -location {13171.680 7742.440} -status PLACED
place_inst -name b237 -location {13348.800 7742.440} -status PLACED
place_inst -name r238_0 -location {13348.800 7436.280} -status PLACED
place_inst -name r238_1 -location {13348.800 7400.620} -status PLACED
place_inst -name r238_2 -location {13348.800 7229.710} -status PLACED
place_inst -name b238 -location {13348.800 7058.800} -status PLACED
place_inst -name r239_0 -location {13348.800 7919.020} -status PLACED
place_inst -name b239 -location {13348.800 8095.600} -status PLACED
place_inst -name r240_0 -location {13525.920 7742.440} -status PLACED
place_inst -name r240_1 -location {13704.040 7742.440} -status PLACED
place_inst -name r240_2 -location {13880.160 7742.440} -status PLACED
place_inst -name b240 -location {14057.280 7742.440} -status PLACED
place_inst -name r241_0 -location {14057.280 7436.280} -status PLACED
place_inst -name r241_1 -location {14057.280 7400.620} -status PLACED
place_inst -name r241_2 -location {14057.280 7229.710} -status PLACED
place_inst -name b241 -location {14057.280 7058.800} -status PLACED
place_inst -name r242_0 -location {14057.280 7919.020} -status PLACED
place_inst -name b242 -location {14057.280 8095.600} -status PLACED
place_inst -name r243_0 -location {14234.400 7742.440} -status PLACED
place_inst -name r243_1 -location {14410.520 7742.440} -status PLACED
place_inst -name r243_2 -location {14588.640 7742.440} -status PLACED
place_inst -name b243 -location {14765.760 7742.440} -status PLACED
place_inst -name r244_0 -location {14765.760 7436.280} -status PLACED
place_inst -name r244_1 -location {14765.760 7400.620} -status PLACED
place_inst -name r244_2 -location {14765.760 7229.710} -status PLACED
place_inst -name b244 -location {14765.760 7058.800} -status PLACED
place_inst -name r245_0 -location {14765.760 7919.020} -status PLACED
place_inst -name b245 -location {14765.760 8095.600} -status PLACED
place_inst -name r246_0 -location {14942.880 7742.440} -status PLACED
place_inst -name r246_1 -location {15119.000 7742.440} -status PLACED
place_inst -name r246_2 -location {15297.120 7742.440} -status PLACED
place_inst -name b246 -location {15474.240 7742.440} -status PLACED
place_inst -name r247_0 -location {15474.240 7436.280} -status PLACED
place_inst -name r247_1 -location {15474.240 7400.620} -status PLACED
place_inst -name r247_2 -location {15474.240 7229.710} -status PLACED
place_inst -name b247 -location {15474.240 7058.800} -status PLACED
place_inst -name r248_0 -location {15474.240 7919.020} -status PLACED
place_inst -name b248 -location {15474.240 8095.600} -status PLACED
place_inst -name r249_0 -location {15651.360 7742.440} -status PLACED
place_inst -name r249_1 -location {15827.480 7742.440} -status PLACED
place_inst -name r249_2 -location {16005.600 7742.440} -status PLACED
place_inst -name b249 -location {16182.720 7742.440} -status PLACED
place_inst -name r250_0 -location {16182.720 7436.280} -status PLACED
place_inst -name r250_1 -location {16182.720 7400.620} -status PLACED
place_inst -name r250_2 -location {16182.720 7229.710} -status PLACED
place_inst -name b250 -location {16182.720 7058.800} -status PLACED
place_inst -name r251_0 -location {16182.720 7919.020} -status PLACED
place_inst -name b251 -location {16182.720 8095.600} -status PLACED
place_inst -name r252_0 -location {16359.840 7742.440} -status PLACED
place_inst -name r252_1 -location {16535.960 7742.440} -status PLACED
place_inst -name r252_2 -location {16714.080 7742.440} -status PLACED
place_inst -name b252 -location {16891.200 7742.440} -status PLACED
place_inst -name r253_0 -location {16891.200 7436.280} -status PLACED
place_inst -name r253_1 -location {16891.200 7400.620} -status PLACED
place_inst -name r253_2 -location {16891.200 7229.710} -status PLACED
place_inst -name b253 -location {16891.200 7058.800} -status PLACED
place_inst -name r254_0 -location {16891.200 7919.020} -status PLACED
place_inst -name b254 -location {16891.200 8095.600} -status PLACED
place_inst -name r255_0 -location {17001.480 7742.440} -status PLACED
place_inst -name r255_1 -location {17111.760 7742.440} -status PLACED
place_inst -name r255_2 -location {17222.040 7742.440} -status PLACED
place_inst -name b255 -location {17332.320 7742.440} -status PLACED
place_inst -name r256_0 -location {17332.320 7612.580} -status PLACED
place_inst -name r256_1 -location {17332.320 7482.720} -status PLACED
place_inst -name r256_2 -location {17332.320 7352.860} -status PLACED
place_inst -name b256 -location {17332.320 7223.000} -status PLACED
place_inst -name r257_0 -location {17332.320 7871.780} -status PLACED
place_inst -name r257_1 -location {17332.320 8001.120} -status PLACED
place_inst -name r257_2 -location {17332.320 8130.460} -status PLACED
place_inst -name b257 -location {17332.320 8259.800} -status PLACED
place_inst -name r258_0 -location {8588.341 9815.072} -status PLACED
place_inst -name r258_1 -location {8415.721 9815.072} -status PLACED
place_inst -name r258_2 -location {8243.102 9815.072} -status PLACED
place_inst -name b258 -location {8070.483 9815.072} -status PLACED
place_inst -name r259_0 -location {8011.323 9701.293} -status PLACED
place_inst -name r259_1 -location {7952.162 9587.515} -status PLACED
place_inst -name r259_2 -location {7893.002 9480.840} -status PLACED
place_inst -name r259_3 -location {7833.841 9480.840} -status PLACED
place_inst -name r259_4 -location {7774.681 9155.640} -status PLACED
place_inst -name b259 -location {7715.520 9132.400} -status PLACED
place_inst -name r260_0 -location {7894.466 9814.472} -status PLACED
place_inst -name r260_1 -location {7716.174 9814.472} -status PLACED
place_inst -name r260_2 -location {7714.920 9991.509} -status PLACED
place_inst -name b260 -location {7715.520 10169.200} -status PLACED
place_inst -name r261_0 -location {7893.243 9816.040} -status PLACED
place_inst -name r261_1 -location {7716.002 9816.040} -status PLACED
place_inst -name r261_2 -location {7538.762 9815.556} -status PLACED
place_inst -name r261_3 -location {7362.280 9816.040} -status PLACED
place_inst -name r261_4 -location {7184.280 9815.879} -status PLACED
place_inst -name b261 -location {7007.040 9816.040} -status PLACED
place_inst -name r262_0 -location {7007.040 9509.880} -status PLACED
place_inst -name r262_1 -location {7007.040 9474.220} -status PLACED
place_inst -name r262_2 -location {7007.040 9303.310} -status PLACED
place_inst -name b262 -location {7007.040 9132.400} -status PLACED
place_inst -name r263_0 -location {7007.040 9992.620} -status PLACED
place_inst -name b263 -location {7007.040 10169.200} -status PLACED
place_inst -name r264_0 -location {6829.920 9816.040} -status PLACED
place_inst -name r264_1 -location {6653.800 9816.040} -status PLACED
place_inst -name r264_2 -location {6475.680 9816.040} -status PLACED
place_inst -name b264 -location {6298.560 9816.040} -status PLACED
place_inst -name r265_0 -location {6298.560 9509.880} -status PLACED
place_inst -name r265_1 -location {6298.560 9474.220} -status PLACED
place_inst -name r265_2 -location {6298.560 9303.310} -status PLACED
place_inst -name b265 -location {6298.560 9132.400} -status PLACED
place_inst -name r266_0 -location {6298.560 9992.620} -status PLACED
place_inst -name b266 -location {6298.560 10169.200} -status PLACED
place_inst -name r267_0 -location {6121.440 9816.040} -status PLACED
place_inst -name r267_1 -location {5945.320 9816.040} -status PLACED
place_inst -name r267_2 -location {5767.200 9816.040} -status PLACED
place_inst -name b267 -location {5590.080 9816.040} -status PLACED
place_inst -name r268_0 -location {5590.080 9509.880} -status PLACED
place_inst -name r268_1 -location {5590.080 9474.220} -status PLACED
place_inst -name r268_2 -location {5590.080 9303.310} -status PLACED
place_inst -name b268 -location {5590.080 9132.400} -status PLACED
place_inst -name r269_0 -location {5590.080 9992.620} -status PLACED
place_inst -name b269 -location {5590.080 10169.200} -status PLACED
place_inst -name r270_0 -location {5412.960 9816.040} -status PLACED
place_inst -name r270_1 -location {5236.840 9816.040} -status PLACED
place_inst -name r270_2 -location {5058.720 9816.040} -status PLACED
place_inst -name b270 -location {4881.600 9816.040} -status PLACED
place_inst -name r271_0 -location {4881.600 9509.880} -status PLACED
place_inst -name r271_1 -location {4881.600 9474.220} -status PLACED
place_inst -name r271_2 -location {4881.600 9303.310} -status PLACED
place_inst -name b271 -location {4881.600 9132.400} -status PLACED
place_inst -name r272_0 -location {4881.600 9992.620} -status PLACED
place_inst -name b272 -location {4881.600 10169.200} -status PLACED
place_inst -name r273_0 -location {4704.480 9816.040} -status PLACED
place_inst -name r273_1 -location {4528.360 9816.040} -status PLACED
place_inst -name r273_2 -location {4350.240 9816.040} -status PLACED
place_inst -name b273 -location {4173.120 9816.040} -status PLACED
place_inst -name r274_0 -location {4173.120 9509.880} -status PLACED
place_inst -name r274_1 -location {4173.120 9474.220} -status PLACED
place_inst -name r274_2 -location {4173.120 9303.310} -status PLACED
place_inst -name b274 -location {4173.120 9132.400} -status PLACED
place_inst -name r275_0 -location {4173.120 9992.620} -status PLACED
place_inst -name b275 -location {4173.120 10169.200} -status PLACED
place_inst -name r276_0 -location {3996.000 9816.040} -status PLACED
place_inst -name r276_1 -location {3819.880 9816.040} -status PLACED
place_inst -name r276_2 -location {3641.760 9816.040} -status PLACED
place_inst -name b276 -location {3464.640 9816.040} -status PLACED
place_inst -name r277_0 -location {3464.640 9509.880} -status PLACED
place_inst -name r277_1 -location {3464.640 9474.220} -status PLACED
place_inst -name r277_2 -location {3464.640 9303.310} -status PLACED
place_inst -name b277 -location {3464.640 9132.400} -status PLACED
place_inst -name r278_0 -location {3464.640 9992.620} -status PLACED
place_inst -name b278 -location {3464.640 10169.200} -status PLACED
place_inst -name r279_0 -location {3287.520 9816.040} -status PLACED
place_inst -name r279_1 -location {3109.400 9816.040} -status PLACED
place_inst -name r279_2 -location {2933.280 9816.040} -status PLACED
place_inst -name b279 -location {2756.160 9816.040} -status PLACED
place_inst -name r280_0 -location {2756.160 9509.880} -status PLACED
place_inst -name r280_1 -location {2756.160 9474.220} -status PLACED
place_inst -name r280_2 -location {2756.160 9303.310} -status PLACED
place_inst -name b280 -location {2756.160 9132.400} -status PLACED
place_inst -name r281_0 -location {2756.160 9992.620} -status PLACED
place_inst -name b281 -location {2756.160 10169.200} -status PLACED
place_inst -name r282_0 -location {2579.040 9816.040} -status PLACED
place_inst -name r282_1 -location {2402.920 9816.040} -status PLACED
place_inst -name r282_2 -location {2224.800 9816.040} -status PLACED
place_inst -name b282 -location {2047.680 9816.040} -status PLACED
place_inst -name r283_0 -location {2047.680 9509.880} -status PLACED
place_inst -name r283_1 -location {2047.680 9474.220} -status PLACED
place_inst -name r283_2 -location {2047.680 9303.310} -status PLACED
place_inst -name b283 -location {2047.680 9132.400} -status PLACED
place_inst -name r284_0 -location {2047.680 9992.620} -status PLACED
place_inst -name b284 -location {2047.680 10169.200} -status PLACED
place_inst -name r285_0 -location {1870.560 9816.040} -status PLACED
place_inst -name r285_1 -location {1694.440 9816.040} -status PLACED
place_inst -name r285_2 -location {1516.320 9816.040} -status PLACED
place_inst -name b285 -location {1339.200 9816.040} -status PLACED
place_inst -name r286_0 -location {1339.200 9509.880} -status PLACED
place_inst -name r286_1 -location {1339.200 9474.220} -status PLACED
place_inst -name r286_2 -location {1339.200 9303.310} -status PLACED
place_inst -name b286 -location {1339.200 9132.400} -status PLACED
place_inst -name r287_0 -location {1339.200 9992.620} -status PLACED
place_inst -name b287 -location {1339.200 10169.200} -status PLACED
place_inst -name r288_0 -location {1162.080 9816.040} -status PLACED
place_inst -name r288_1 -location {985.960 9816.040} -status PLACED
place_inst -name r288_2 -location {807.840 9816.040} -status PLACED
place_inst -name b288 -location {630.720 9816.040} -status PLACED
place_inst -name r289_0 -location {630.720 9509.880} -status PLACED
place_inst -name r289_1 -location {630.720 9474.220} -status PLACED
place_inst -name r289_2 -location {630.720 9303.310} -status PLACED
place_inst -name b289 -location {630.720 9132.400} -status PLACED
place_inst -name r290_0 -location {630.720 9992.620} -status PLACED
place_inst -name b290 -location {630.720 10169.200} -status PLACED
place_inst -name r291_0 -location {520.440 9816.040} -status PLACED
place_inst -name r291_1 -location {410.160 9816.040} -status PLACED
place_inst -name r291_2 -location {299.880 9816.040} -status PLACED
place_inst -name b291 -location {189.600 9816.040} -status PLACED
place_inst -name r292_0 -location {189.600 9686.180} -status PLACED
place_inst -name r292_1 -location {189.600 9556.320} -status PLACED
place_inst -name r292_2 -location {189.600 9426.460} -status PLACED
place_inst -name b292 -location {189.600 9296.600} -status PLACED
place_inst -name r293_0 -location {189.600 9945.380} -status PLACED
place_inst -name r293_1 -location {189.600 10074.720} -status PLACED
place_inst -name r293_2 -location {189.600 10204.060} -status PLACED
place_inst -name b293 -location {189.600 10333.400} -status PLACED
place_inst -name r294_0 -location {8933.625 9815.072} -status PLACED
place_inst -name r294_1 -location {9106.290 9815.072} -status PLACED
place_inst -name r294_2 -location {9278.955 9815.072} -status PLACED
place_inst -name b294 -location {9451.620 9815.072} -status PLACED
place_inst -name r295_0 -location {9510.750 9701.293} -status PLACED
place_inst -name r295_1 -location {9569.880 9587.515} -status PLACED
place_inst -name r295_2 -location {9629.010 9480.840} -status PLACED
place_inst -name r295_3 -location {9688.140 9480.840} -status PLACED
place_inst -name r295_4 -location {9747.270 9155.640} -status PLACED
place_inst -name b295 -location {9806.400 9132.400} -status PLACED
place_inst -name r296_0 -location {9451.020 9993.345} -status PLACED
place_inst -name r296_1 -location {9453.160 10170.872} -status PLACED
place_inst -name r296_2 -location {9631.239 10170.872} -status PLACED
place_inst -name b296 -location {9806.400 10169.200} -status PLACED
place_inst -name r297_0 -location {9628.830 9816.040} -status PLACED
place_inst -name r297_1 -location {9806.040 9816.040} -status PLACED
place_inst -name r297_2 -location {9983.250 9815.556} -status PLACED
place_inst -name r297_3 -location {10159.640 9816.040} -status PLACED
place_inst -name r297_4 -location {10337.670 9815.879} -status PLACED
place_inst -name b297 -location {10514.880 9816.040} -status PLACED
place_inst -name r298_0 -location {10514.880 9509.880} -status PLACED
place_inst -name r298_1 -location {10514.880 9474.220} -status PLACED
place_inst -name r298_2 -location {10514.880 9303.310} -status PLACED
place_inst -name b298 -location {10514.880 9132.400} -status PLACED
place_inst -name r299_0 -location {10514.880 9992.620} -status PLACED
place_inst -name b299 -location {10514.880 10169.200} -status PLACED
place_inst -name r300_0 -location {10692.000 9816.040} -status PLACED
place_inst -name r300_1 -location {10868.120 9816.040} -status PLACED
place_inst -name r300_2 -location {11046.240 9816.040} -status PLACED
place_inst -name b300 -location {11223.360 9816.040} -status PLACED
place_inst -name r301_0 -location {11223.360 9509.880} -status PLACED
place_inst -name r301_1 -location {11223.360 9474.220} -status PLACED
place_inst -name r301_2 -location {11223.360 9303.310} -status PLACED
place_inst -name b301 -location {11223.360 9132.400} -status PLACED
place_inst -name r302_0 -location {11223.360 9992.620} -status PLACED
place_inst -name b302 -location {11223.360 10169.200} -status PLACED
place_inst -name r303_0 -location {11400.480 9816.040} -status PLACED
place_inst -name r303_1 -location {11576.600 9816.040} -status PLACED
place_inst -name r303_2 -location {11754.720 9816.040} -status PLACED
place_inst -name b303 -location {11931.840 9816.040} -status PLACED
place_inst -name r304_0 -location {11931.840 9509.880} -status PLACED
place_inst -name r304_1 -location {11931.840 9474.220} -status PLACED
place_inst -name r304_2 -location {11931.840 9303.310} -status PLACED
place_inst -name b304 -location {11931.840 9132.400} -status PLACED
place_inst -name r305_0 -location {11931.840 9992.620} -status PLACED
place_inst -name b305 -location {11931.840 10169.200} -status PLACED
place_inst -name r306_0 -location {12108.960 9816.040} -status PLACED
place_inst -name r306_1 -location {12285.080 9816.040} -status PLACED
place_inst -name r306_2 -location {12463.200 9816.040} -status PLACED
place_inst -name b306 -location {12640.320 9816.040} -status PLACED
place_inst -name r307_0 -location {12640.320 9509.880} -status PLACED
place_inst -name r307_1 -location {12640.320 9474.220} -status PLACED
place_inst -name r307_2 -location {12640.320 9303.310} -status PLACED
place_inst -name b307 -location {12640.320 9132.400} -status PLACED
place_inst -name r308_0 -location {12640.320 9992.620} -status PLACED
place_inst -name b308 -location {12640.320 10169.200} -status PLACED
place_inst -name r309_0 -location {12817.440 9816.040} -status PLACED
place_inst -name r309_1 -location {12993.560 9816.040} -status PLACED
place_inst -name r309_2 -location {13171.680 9816.040} -status PLACED
place_inst -name b309 -location {13348.800 9816.040} -status PLACED
place_inst -name r310_0 -location {13348.800 9509.880} -status PLACED
place_inst -name r310_1 -location {13348.800 9474.220} -status PLACED
place_inst -name r310_2 -location {13348.800 9303.310} -status PLACED
place_inst -name b310 -location {13348.800 9132.400} -status PLACED
place_inst -name r311_0 -location {13348.800 9992.620} -status PLACED
place_inst -name b311 -location {13348.800 10169.200} -status PLACED
place_inst -name r312_0 -location {13525.920 9816.040} -status PLACED
place_inst -name r312_1 -location {13704.040 9816.040} -status PLACED
place_inst -name r312_2 -location {13880.160 9816.040} -status PLACED
place_inst -name b312 -location {14057.280 9816.040} -status PLACED
place_inst -name r313_0 -location {14057.280 9509.880} -status PLACED
place_inst -name r313_1 -location {14057.280 9474.220} -status PLACED
place_inst -name r313_2 -location {14057.280 9303.310} -status PLACED
place_inst -name b313 -location {14057.280 9132.400} -status PLACED
place_inst -name r314_0 -location {14057.280 9992.620} -status PLACED
place_inst -name b314 -location {14057.280 10169.200} -status PLACED
place_inst -name r315_0 -location {14234.400 9816.040} -status PLACED
place_inst -name r315_1 -location {14410.520 9816.040} -status PLACED
place_inst -name r315_2 -location {14588.640 9816.040} -status PLACED
place_inst -name b315 -location {14765.760 9816.040} -status PLACED
place_inst -name r316_0 -location {14765.760 9509.880} -status PLACED
place_inst -name r316_1 -location {14765.760 9474.220} -status PLACED
place_inst -name r316_2 -location {14765.760 9303.310} -status PLACED
place_inst -name b316 -location {14765.760 9132.400} -status PLACED
place_inst -name r317_0 -location {14765.760 9992.620} -status PLACED
place_inst -name b317 -location {14765.760 10169.200} -status PLACED
place_inst -name r318_0 -location {14942.880 9816.040} -status PLACED
place_inst -name r318_1 -location {15119.000 9816.040} -status PLACED
place_inst -name r318_2 -location {15297.120 9816.040} -status PLACED
place_inst -name b318 -location {15474.240 9816.040} -status PLACED
place_inst -name r319_0 -location {15474.240 9509.880} -status PLACED
place_inst -name r319_1 -location {15474.240 9474.220} -status PLACED
place_inst -name r319_2 -location {15474.240 9303.310} -status PLACED
place_inst -name b319 -location {15474.240 9132.400} -status PLACED
place_inst -name r320_0 -location {15474.240 9992.620} -status PLACED
place_inst -name b320 -location {15474.240 10169.200} -status PLACED
place_inst -name r321_0 -location {15651.360 9816.040} -status PLACED
place_inst -name r321_1 -location {15827.480 9816.040} -status PLACED
place_inst -name r321_2 -location {16005.600 9816.040} -status PLACED
place_inst -name b321 -location {16182.720 9816.040} -status PLACED
place_inst -name r322_0 -location {16182.720 9509.880} -status PLACED
place_inst -name r322_1 -location {16182.720 9474.220} -status PLACED
place_inst -name r322_2 -location {16182.720 9303.310} -status PLACED
place_inst -name b322 -location {16182.720 9132.400} -status PLACED
place_inst -name r323_0 -location {16182.720 9992.620} -status PLACED
place_inst -name b323 -location {16182.720 10169.200} -status PLACED
place_inst -name r324_0 -location {16359.840 9816.040} -status PLACED
place_inst -name r324_1 -location {16535.960 9816.040} -status PLACED
place_inst -name r324_2 -location {16714.080 9816.040} -status PLACED
place_inst -name b324 -location {16891.200 9816.040} -status PLACED
place_inst -name r325_0 -location {16891.200 9509.880} -status PLACED
place_inst -name r325_1 -location {16891.200 9474.220} -status PLACED
place_inst -name r325_2 -location {16891.200 9303.310} -status PLACED
place_inst -name b325 -location {16891.200 9132.400} -status PLACED
place_inst -name r326_0 -location {16891.200 9992.620} -status PLACED
place_inst -name b326 -location {16891.200 10169.200} -status PLACED
place_inst -name r327_0 -location {17001.480 9816.040} -status PLACED
place_inst -name r327_1 -location {17111.760 9816.040} -status PLACED
place_inst -name r327_2 -location {17222.040 9816.040} -status PLACED
place_inst -name b327 -location {17332.320 9816.040} -status PLACED
place_inst -name r328_0 -location {17332.320 9686.180} -status PLACED
place_inst -name r328_1 -location {17332.320 9556.320} -status PLACED
place_inst -name r328_2 -location {17332.320 9426.460} -status PLACED
place_inst -name b328 -location {17332.320 9296.600} -status PLACED
place_inst -name r329_0 -location {17332.320 9945.380} -status PLACED
place_inst -name r329_1 -location {17332.320 10074.720} -status PLACED
place_inst -name r329_2 -location {17332.320 10204.060} -status PLACED
place_inst -name b329 -location {17332.320 10333.400} -status PLACED
place_inst -name r330_0 -location {8588.341 11888.672} -status PLACED
place_inst -name r330_1 -location {8415.721 11888.672} -status PLACED
place_inst -name r330_2 -location {8243.102 11888.672} -status PLACED
place_inst -name b330 -location {8070.483 11888.672} -status PLACED
place_inst -name r331_0 -location {8011.323 11774.893} -status PLACED
place_inst -name r331_1 -location {7952.162 11661.115} -status PLACED
place_inst -name r331_2 -location {7893.002 11554.440} -status PLACED
place_inst -name r331_3 -location {7833.841 11554.440} -status PLACED
place_inst -name r331_4 -location {7774.681 11229.240} -status PLACED
place_inst -name b331 -location {7715.520 11206.000} -status PLACED
place_inst -name r332_0 -location {7894.466 11888.072} -status PLACED
place_inst -name r332_1 -location {7716.175 11888.072} -status PLACED
place_inst -name r332_2 -location {7714.920 12065.109} -status PLACED
place_inst -name b332 -location {7715.520 12242.800} -status PLACED
place_inst -name r333_0 -location {7893.243 11889.640} -status PLACED
place_inst -name r333_1 -location {7716.002 11889.640} -status PLACED
place_inst -name r333_2 -location {7538.762 11889.156} -status PLACED
place_inst -name r333_3 -location {7362.280 11889.640} -status PLACED
place_inst -name r333_4 -location {7184.280 11889.479} -status PLACED
place_inst -name b333 -location {7007.040 11889.640} -status PLACED
place_inst -name r334_0 -location {7007.040 11583.480} -status PLACED
place_inst -name r334_1 -location {7007.040 11547.820} -status PLACED
place_inst -name r334_2 -location {7007.040 11376.910} -status PLACED
place_inst -name b334 -location {7007.040 11206.000} -status PLACED
place_inst -name r335_0 -location {7007.040 12066.220} -status PLACED
place_inst -name b335 -location {7007.040 12242.800} -status PLACED
place_inst -name r336_0 -location {6829.920 11889.640} -status PLACED
place_inst -name r336_1 -location {6653.800 11889.640} -status PLACED
place_inst -name r336_2 -location {6475.680 11889.640} -status PLACED
place_inst -name b336 -location {6298.560 11889.640} -status PLACED
place_inst -name r337_0 -location {6298.560 11583.480} -status PLACED
place_inst -name r337_1 -location {6298.560 11547.820} -status PLACED
place_inst -name r337_2 -location {6298.560 11376.910} -status PLACED
place_inst -name b337 -location {6298.560 11206.000} -status PLACED
place_inst -name r338_0 -location {6298.560 12066.220} -status PLACED
place_inst -name b338 -location {6298.560 12242.800} -status PLACED
place_inst -name r339_0 -location {6121.440 11889.640} -status PLACED
place_inst -name r339_1 -location {5945.320 11889.640} -status PLACED
place_inst -name r339_2 -location {5767.200 11889.640} -status PLACED
place_inst -name b339 -location {5590.080 11889.640} -status PLACED
place_inst -name r340_0 -location {5590.080 11583.480} -status PLACED
place_inst -name r340_1 -location {5590.080 11547.820} -status PLACED
place_inst -name r340_2 -location {5590.080 11376.910} -status PLACED
place_inst -name b340 -location {5590.080 11206.000} -status PLACED
place_inst -name r341_0 -location {5590.080 12066.220} -status PLACED
place_inst -name b341 -location {5590.080 12242.800} -status PLACED
place_inst -name r342_0 -location {5412.960 11889.640} -status PLACED
place_inst -name r342_1 -location {5236.840 11889.640} -status PLACED
place_inst -name r342_2 -location {5058.720 11889.640} -status PLACED
place_inst -name b342 -location {4881.600 11889.640} -status PLACED
place_inst -name r343_0 -location {4881.600 11583.480} -status PLACED
place_inst -name r343_1 -location {4881.600 11547.820} -status PLACED
place_inst -name r343_2 -location {4881.600 11376.910} -status PLACED
place_inst -name b343 -location {4881.600 11206.000} -status PLACED
place_inst -name r344_0 -location {4881.600 12066.220} -status PLACED
place_inst -name b344 -location {4881.600 12242.800} -status PLACED
place_inst -name r345_0 -location {4704.480 11889.640} -status PLACED
place_inst -name r345_1 -location {4528.360 11889.640} -status PLACED
place_inst -name r345_2 -location {4350.240 11889.640} -status PLACED
place_inst -name b345 -location {4173.120 11889.640} -status PLACED
place_inst -name r346_0 -location {4173.120 11583.480} -status PLACED
place_inst -name r346_1 -location {4173.120 11547.820} -status PLACED
place_inst -name r346_2 -location {4173.120 11376.910} -status PLACED
place_inst -name b346 -location {4173.120 11206.000} -status PLACED
place_inst -name r347_0 -location {4173.120 12066.220} -status PLACED
place_inst -name b347 -location {4173.120 12242.800} -status PLACED
place_inst -name r348_0 -location {3996.000 11889.640} -status PLACED
place_inst -name r348_1 -location {3819.880 11889.640} -status PLACED
place_inst -name r348_2 -location {3641.760 11889.640} -status PLACED
place_inst -name b348 -location {3464.640 11889.640} -status PLACED
place_inst -name r349_0 -location {3464.640 11583.480} -status PLACED
place_inst -name r349_1 -location {3464.640 11547.820} -status PLACED
place_inst -name r349_2 -location {3464.640 11376.910} -status PLACED
place_inst -name b349 -location {3464.640 11206.000} -status PLACED
place_inst -name r350_0 -location {3464.640 12066.220} -status PLACED
place_inst -name b350 -location {3464.640 12242.800} -status PLACED
place_inst -name r351_0 -location {3287.520 11889.640} -status PLACED
place_inst -name r351_1 -location {3109.400 11889.640} -status PLACED
place_inst -name r351_2 -location {2933.280 11889.640} -status PLACED
place_inst -name b351 -location {2756.160 11889.640} -status PLACED
place_inst -name r352_0 -location {2756.160 11583.480} -status PLACED
place_inst -name r352_1 -location {2756.160 11547.820} -status PLACED
place_inst -name r352_2 -location {2756.160 11376.910} -status PLACED
place_inst -name b352 -location {2756.160 11206.000} -status PLACED
place_inst -name r353_0 -location {2756.160 12066.220} -status PLACED
place_inst -name b353 -location {2756.160 12242.800} -status PLACED
place_inst -name r354_0 -location {2579.040 11889.640} -status PLACED
place_inst -name r354_1 -location {2402.920 11889.640} -status PLACED
place_inst -name r354_2 -location {2224.800 11889.640} -status PLACED
place_inst -name b354 -location {2047.680 11889.640} -status PLACED
place_inst -name r355_0 -location {2047.680 11583.480} -status PLACED
place_inst -name r355_1 -location {2047.680 11547.820} -status PLACED
place_inst -name r355_2 -location {2047.680 11376.910} -status PLACED
place_inst -name b355 -location {2047.680 11206.000} -status PLACED
place_inst -name r356_0 -location {2047.680 12066.220} -status PLACED
place_inst -name b356 -location {2047.680 12242.800} -status PLACED
place_inst -name r357_0 -location {1870.560 11889.640} -status PLACED
place_inst -name r357_1 -location {1694.440 11889.640} -status PLACED
place_inst -name r357_2 -location {1516.320 11889.640} -status PLACED
place_inst -name b357 -location {1339.200 11889.640} -status PLACED
place_inst -name r358_0 -location {1339.200 11583.480} -status PLACED
place_inst -name r358_1 -location {1339.200 11547.820} -status PLACED
place_inst -name r358_2 -location {1339.200 11376.910} -status PLACED
place_inst -name b358 -location {1339.200 11206.000} -status PLACED
place_inst -name r359_0 -location {1339.200 12066.220} -status PLACED
place_inst -name b359 -location {1339.200 12242.800} -status PLACED
place_inst -name r360_0 -location {1162.080 11889.640} -status PLACED
place_inst -name r360_1 -location {985.960 11889.640} -status PLACED
place_inst -name r360_2 -location {807.840 11889.640} -status PLACED
place_inst -name b360 -location {630.720 11889.640} -status PLACED
place_inst -name r361_0 -location {630.720 11583.480} -status PLACED
place_inst -name r361_1 -location {630.720 11547.820} -status PLACED
place_inst -name r361_2 -location {630.720 11376.910} -status PLACED
place_inst -name b361 -location {630.720 11206.000} -status PLACED
place_inst -name r362_0 -location {630.720 12066.220} -status PLACED
place_inst -name b362 -location {630.720 12242.800} -status PLACED
place_inst -name r363_0 -location {520.440 11889.640} -status PLACED
place_inst -name r363_1 -location {410.160 11889.640} -status PLACED
place_inst -name r363_2 -location {299.880 11889.640} -status PLACED
place_inst -name b363 -location {189.600 11889.640} -status PLACED
place_inst -name r364_0 -location {189.600 11759.780} -status PLACED
place_inst -name r364_1 -location {189.600 11629.920} -status PLACED
place_inst -name r364_2 -location {189.600 11500.060} -status PLACED
place_inst -name b364 -location {189.600 11370.200} -status PLACED
place_inst -name r365_0 -location {189.600 12018.980} -status PLACED
place_inst -name r365_1 -location {189.600 12148.320} -status PLACED
place_inst -name r365_2 -location {189.600 12277.660} -status PLACED
place_inst -name b365 -location {189.600 12407.000} -status PLACED
place_inst -name r366_0 -location {8933.625 11888.672} -status PLACED
place_inst -name r366_1 -location {9106.290 11888.672} -status PLACED
place_inst -name r366_2 -location {9278.955 11888.672} -status PLACED
place_inst -name b366 -location {9451.620 11888.672} -status PLACED
place_inst -name r367_0 -location {9510.750 11774.893} -status PLACED
place_inst -name r367_1 -location {9569.880 11661.115} -status PLACED
place_inst -name r367_2 -location {9629.010 11554.440} -status PLACED
place_inst -name r367_3 -location {9688.140 11554.440} -status PLACED
place_inst -name r367_4 -location {9747.270 11229.240} -status PLACED
place_inst -name b367 -location {9806.400 11206.000} -status PLACED
place_inst -name r368_0 -location {9451.020 12066.945} -status PLACED
place_inst -name r368_1 -location {9453.160 12244.472} -status PLACED
place_inst -name r368_2 -location {9631.239 12244.472} -status PLACED
place_inst -name b368 -location {9806.400 12242.800} -status PLACED
place_inst -name r369_0 -location {9628.830 11889.640} -status PLACED
place_inst -name r369_1 -location {9806.040 11889.640} -status PLACED
place_inst -name r369_2 -location {9983.250 11889.156} -status PLACED
place_inst -name r369_3 -location {10159.640 11889.640} -status PLACED
place_inst -name r369_4 -location {10337.670 11889.479} -status PLACED
place_inst -name b369 -location {10514.880 11889.640} -status PLACED
place_inst -name r370_0 -location {10514.880 11583.480} -status PLACED
place_inst -name r370_1 -location {10514.880 11547.820} -status PLACED
place_inst -name r370_2 -location {10514.880 11376.910} -status PLACED
place_inst -name b370 -location {10514.880 11206.000} -status PLACED
place_inst -name r371_0 -location {10514.880 12066.220} -status PLACED
place_inst -name b371 -location {10514.880 12242.800} -status PLACED
place_inst -name r372_0 -location {10692.000 11889.640} -status PLACED
place_inst -name r372_1 -location {10868.120 11889.640} -status PLACED
place_inst -name r372_2 -location {11046.240 11889.640} -status PLACED
place_inst -name b372 -location {11223.360 11889.640} -status PLACED
place_inst -name r373_0 -location {11223.360 11583.480} -status PLACED
place_inst -name r373_1 -location {11223.360 11547.820} -status PLACED
place_inst -name r373_2 -location {11223.360 11376.910} -status PLACED
place_inst -name b373 -location {11223.360 11206.000} -status PLACED
place_inst -name r374_0 -location {11223.360 12066.220} -status PLACED
place_inst -name b374 -location {11223.360 12242.800} -status PLACED
place_inst -name r375_0 -location {11400.480 11889.640} -status PLACED
place_inst -name r375_1 -location {11576.600 11889.640} -status PLACED
place_inst -name r375_2 -location {11754.720 11889.640} -status PLACED
place_inst -name b375 -location {11931.840 11889.640} -status PLACED
place_inst -name r376_0 -location {11931.840 11583.480} -status PLACED
place_inst -name r376_1 -location {11931.840 11547.820} -status PLACED
place_inst -name r376_2 -location {11931.840 11376.910} -status PLACED
place_inst -name b376 -location {11931.840 11206.000} -status PLACED
place_inst -name r377_0 -location {11931.840 12066.220} -status PLACED
place_inst -name b377 -location {11931.840 12242.800} -status PLACED
place_inst -name r378_0 -location {12108.960 11889.640} -status PLACED
place_inst -name r378_1 -location {12285.080 11889.640} -status PLACED
place_inst -name r378_2 -location {12463.200 11889.640} -status PLACED
place_inst -name b378 -location {12640.320 11889.640} -status PLACED
place_inst -name r379_0 -location {12640.320 11583.480} -status PLACED
place_inst -name r379_1 -location {12640.320 11547.820} -status PLACED
place_inst -name r379_2 -location {12640.320 11376.910} -status PLACED
place_inst -name b379 -location {12640.320 11206.000} -status PLACED
place_inst -name r380_0 -location {12640.320 12066.220} -status PLACED
place_inst -name b380 -location {12640.320 12242.800} -status PLACED
place_inst -name r381_0 -location {12817.440 11889.640} -status PLACED
place_inst -name r381_1 -location {12993.560 11889.640} -status PLACED
place_inst -name r381_2 -location {13171.680 11889.640} -status PLACED
place_inst -name b381 -location {13348.800 11889.640} -status PLACED
place_inst -name r382_0 -location {13348.800 11583.480} -status PLACED
place_inst -name r382_1 -location {13348.800 11547.820} -status PLACED
place_inst -name r382_2 -location {13348.800 11376.910} -status PLACED
place_inst -name b382 -location {13348.800 11206.000} -status PLACED
place_inst -name r383_0 -location {13348.800 12066.220} -status PLACED
place_inst -name b383 -location {13348.800 12242.800} -status PLACED
place_inst -name r384_0 -location {13525.920 11889.640} -status PLACED
place_inst -name r384_1 -location {13704.040 11889.640} -status PLACED
place_inst -name r384_2 -location {13880.160 11889.640} -status PLACED
place_inst -name b384 -location {14057.280 11889.640} -status PLACED
place_inst -name r385_0 -location {14057.280 11583.480} -status PLACED
place_inst -name r385_1 -location {14057.280 11547.820} -status PLACED
place_inst -name r385_2 -location {14057.280 11376.910} -status PLACED
place_inst -name b385 -location {14057.280 11206.000} -status PLACED
place_inst -name r386_0 -location {14057.280 12066.220} -status PLACED
place_inst -name b386 -location {14057.280 12242.800} -status PLACED
place_inst -name r387_0 -location {14234.400 11889.640} -status PLACED
place_inst -name r387_1 -location {14410.520 11889.640} -status PLACED
place_inst -name r387_2 -location {14588.640 11889.640} -status PLACED
place_inst -name b387 -location {14765.760 11889.640} -status PLACED
place_inst -name r388_0 -location {14765.760 11583.480} -status PLACED
place_inst -name r388_1 -location {14765.760 11547.820} -status PLACED
place_inst -name r388_2 -location {14765.760 11376.910} -status PLACED
place_inst -name b388 -location {14765.760 11206.000} -status PLACED
place_inst -name r389_0 -location {14765.760 12066.220} -status PLACED
place_inst -name b389 -location {14765.760 12242.800} -status PLACED
place_inst -name r390_0 -location {14942.880 11889.640} -status PLACED
place_inst -name r390_1 -location {15119.000 11889.640} -status PLACED
place_inst -name r390_2 -location {15297.120 11889.640} -status PLACED
place_inst -name b390 -location {15474.240 11889.640} -status PLACED
place_inst -name r391_0 -location {15474.240 11583.480} -status PLACED
place_inst -name r391_1 -location {15474.240 11547.820} -status PLACED
place_inst -name r391_2 -location {15474.240 11376.910} -status PLACED
place_inst -name b391 -location {15474.240 11206.000} -status PLACED
place_inst -name r392_0 -location {15474.240 12066.220} -status PLACED
place_inst -name b392 -location {15474.240 12242.800} -status PLACED
place_inst -name r393_0 -location {15651.360 11889.640} -status PLACED
place_inst -name r393_1 -location {15827.480 11889.640} -status PLACED
place_inst -name r393_2 -location {16005.600 11889.640} -status PLACED
place_inst -name b393 -location {16182.720 11889.640} -status PLACED
place_inst -name r394_0 -location {16182.720 11583.480} -status PLACED
place_inst -name r394_1 -location {16182.720 11547.820} -status PLACED
place_inst -name r394_2 -location {16182.720 11376.910} -status PLACED
place_inst -name b394 -location {16182.720 11206.000} -status PLACED
place_inst -name r395_0 -location {16182.720 12066.220} -status PLACED
place_inst -name b395 -location {16182.720 12242.800} -status PLACED
place_inst -name r396_0 -location {16359.840 11889.640} -status PLACED
place_inst -name r396_1 -location {16535.960 11889.640} -status PLACED
place_inst -name r396_2 -location {16714.080 11889.640} -status PLACED
place_inst -name b396 -location {16891.200 11889.640} -status PLACED
place_inst -name r397_0 -location {16891.200 11583.480} -status PLACED
place_inst -name r397_1 -location {16891.200 11547.820} -status PLACED
place_inst -name r397_2 -location {16891.200 11376.910} -status PLACED
place_inst -name b397 -location {16891.200 11206.000} -status PLACED
place_inst -name r398_0 -location {16891.200 12066.220} -status PLACED
place_inst -name b398 -location {16891.200 12242.800} -status PLACED
place_inst -name r399_0 -location {17001.480 11889.640} -status PLACED
place_inst -name r399_1 -location {17111.760 11889.640} -status PLACED
place_inst -name r399_2 -location {17222.040 11889.640} -status PLACED
place_inst -name b399 -location {17332.320 11889.640} -status PLACED
place_inst -name r400_0 -location {17332.320 11759.780} -status PLACED
place_inst -name r400_1 -location {17332.320 11629.920} -status PLACED
place_inst -name r400_2 -location {17332.320 11500.060} -status PLACED
place_inst -name b400 -location {17332.320 11370.200} -status PLACED
place_inst -name r401_0 -location {17332.320 12018.980} -status PLACED
place_inst -name r401_1 -location {17332.320 12148.320} -status PLACED
place_inst -name r401_2 -location {17332.320 12277.660} -status PLACED
place_inst -name b401 -location {17332.320 12407.000} -status PLACED
place_inst -name r402_0 -location {8588.341 13962.272} -status PLACED
place_inst -name r402_1 -location {8415.721 13962.272} -status PLACED
place_inst -name r402_2 -location {8243.102 13962.272} -status PLACED
place_inst -name b402 -location {8070.483 13962.272} -status PLACED
place_inst -name r403_0 -location {8011.323 13848.493} -status PLACED
place_inst -name r403_1 -location {7952.162 13734.715} -status PLACED
place_inst -name r403_2 -location {7893.002 13628.040} -status PLACED
place_inst -name r403_3 -location {7833.841 13628.040} -status PLACED
place_inst -name r403_4 -location {7774.681 13302.840} -status PLACED
place_inst -name b403 -location {7715.520 13279.600} -status PLACED
place_inst -name r404_0 -location {7894.466 13961.672} -status PLACED
place_inst -name r404_1 -location {7716.175 13961.672} -status PLACED
place_inst -name r404_2 -location {7714.920 14138.709} -status PLACED
place_inst -name b404 -location {7715.520 14316.400} -status PLACED
place_inst -name r405_0 -location {7893.243 13963.240} -status PLACED
place_inst -name r405_1 -location {7716.002 13963.240} -status PLACED
place_inst -name r405_2 -location {7538.762 13962.756} -status PLACED
place_inst -name r405_3 -location {7362.280 13963.240} -status PLACED
place_inst -name r405_4 -location {7184.280 13963.079} -status PLACED
place_inst -name b405 -location {7007.040 13963.240} -status PLACED
place_inst -name r406_0 -location {7007.040 13657.080} -status PLACED
place_inst -name r406_1 -location {7007.040 13621.420} -status PLACED
place_inst -name r406_2 -location {7007.040 13450.510} -status PLACED
place_inst -name b406 -location {7007.040 13279.600} -status PLACED
place_inst -name r407_0 -location {7007.040 14139.820} -status PLACED
place_inst -name b407 -location {7007.040 14316.400} -status PLACED
place_inst -name r408_0 -location {6829.920 13963.240} -status PLACED
place_inst -name r408_1 -location {6653.800 13963.240} -status PLACED
place_inst -name r408_2 -location {6475.680 13963.240} -status PLACED
place_inst -name b408 -location {6298.560 13963.240} -status PLACED
place_inst -name r409_0 -location {6298.560 13657.080} -status PLACED
place_inst -name r409_1 -location {6298.560 13621.420} -status PLACED
place_inst -name r409_2 -location {6298.560 13450.510} -status PLACED
place_inst -name b409 -location {6298.560 13279.600} -status PLACED
place_inst -name r410_0 -location {6298.560 14139.820} -status PLACED
place_inst -name b410 -location {6298.560 14316.400} -status PLACED
place_inst -name r411_0 -location {6121.440 13963.240} -status PLACED
place_inst -name r411_1 -location {5945.320 13963.240} -status PLACED
place_inst -name r411_2 -location {5767.200 13963.240} -status PLACED
place_inst -name b411 -location {5590.080 13963.240} -status PLACED
place_inst -name r412_0 -location {5590.080 13657.080} -status PLACED
place_inst -name r412_1 -location {5590.080 13621.420} -status PLACED
place_inst -name r412_2 -location {5590.080 13450.510} -status PLACED
place_inst -name b412 -location {5590.080 13279.600} -status PLACED
place_inst -name r413_0 -location {5590.080 14139.820} -status PLACED
place_inst -name b413 -location {5590.080 14316.400} -status PLACED
place_inst -name r414_0 -location {5412.960 13963.240} -status PLACED
place_inst -name r414_1 -location {5236.840 13963.240} -status PLACED
place_inst -name r414_2 -location {5058.720 13963.240} -status PLACED
place_inst -name b414 -location {4881.600 13963.240} -status PLACED
place_inst -name r415_0 -location {4881.600 13657.080} -status PLACED
place_inst -name r415_1 -location {4881.600 13621.420} -status PLACED
place_inst -name r415_2 -location {4881.600 13450.510} -status PLACED
place_inst -name b415 -location {4881.600 13279.600} -status PLACED
place_inst -name r416_0 -location {4881.600 14139.820} -status PLACED
place_inst -name b416 -location {4881.600 14316.400} -status PLACED
place_inst -name r417_0 -location {4704.480 13963.240} -status PLACED
place_inst -name r417_1 -location {4528.360 13963.240} -status PLACED
place_inst -name r417_2 -location {4350.240 13963.240} -status PLACED
place_inst -name b417 -location {4173.120 13963.240} -status PLACED
place_inst -name r418_0 -location {4173.120 13657.080} -status PLACED
place_inst -name r418_1 -location {4173.120 13621.420} -status PLACED
place_inst -name r418_2 -location {4173.120 13450.510} -status PLACED
place_inst -name b418 -location {4173.120 13279.600} -status PLACED
place_inst -name r419_0 -location {4173.120 14139.820} -status PLACED
place_inst -name b419 -location {4173.120 14316.400} -status PLACED
place_inst -name r420_0 -location {3996.000 13963.240} -status PLACED
place_inst -name r420_1 -location {3819.880 13963.240} -status PLACED
place_inst -name r420_2 -location {3641.760 13963.240} -status PLACED
place_inst -name b420 -location {3464.640 13963.240} -status PLACED
place_inst -name r421_0 -location {3464.640 13657.080} -status PLACED
place_inst -name r421_1 -location {3464.640 13621.420} -status PLACED
place_inst -name r421_2 -location {3464.640 13450.510} -status PLACED
place_inst -name b421 -location {3464.640 13279.600} -status PLACED
place_inst -name r422_0 -location {3464.640 14139.820} -status PLACED
place_inst -name b422 -location {3464.640 14316.400} -status PLACED
place_inst -name r423_0 -location {3287.520 13963.240} -status PLACED
place_inst -name r423_1 -location {3109.400 13963.240} -status PLACED
place_inst -name r423_2 -location {2933.280 13963.240} -status PLACED
place_inst -name b423 -location {2756.160 13963.240} -status PLACED
place_inst -name r424_0 -location {2756.160 13657.080} -status PLACED
place_inst -name r424_1 -location {2756.160 13621.420} -status PLACED
place_inst -name r424_2 -location {2756.160 13450.510} -status PLACED
place_inst -name b424 -location {2756.160 13279.600} -status PLACED
place_inst -name r425_0 -location {2756.160 14139.820} -status PLACED
place_inst -name b425 -location {2756.160 14316.400} -status PLACED
place_inst -name r426_0 -location {2579.040 13963.240} -status PLACED
place_inst -name r426_1 -location {2402.920 13963.240} -status PLACED
place_inst -name r426_2 -location {2224.800 13963.240} -status PLACED
place_inst -name b426 -location {2047.680 13963.240} -status PLACED
place_inst -name r427_0 -location {2047.680 13657.080} -status PLACED
place_inst -name r427_1 -location {2047.680 13621.420} -status PLACED
place_inst -name r427_2 -location {2047.680 13450.510} -status PLACED
place_inst -name b427 -location {2047.680 13279.600} -status PLACED
place_inst -name r428_0 -location {2047.680 14139.820} -status PLACED
place_inst -name b428 -location {2047.680 14316.400} -status PLACED
place_inst -name r429_0 -location {1870.560 13963.240} -status PLACED
place_inst -name r429_1 -location {1694.440 13963.240} -status PLACED
place_inst -name r429_2 -location {1516.320 13963.240} -status PLACED
place_inst -name b429 -location {1339.200 13963.240} -status PLACED
place_inst -name r430_0 -location {1339.200 13657.080} -status PLACED
place_inst -name r430_1 -location {1339.200 13621.420} -status PLACED
place_inst -name r430_2 -location {1339.200 13450.510} -status PLACED
place_inst -name b430 -location {1339.200 13279.600} -status PLACED
place_inst -name r431_0 -location {1339.200 14139.820} -status PLACED
place_inst -name b431 -location {1339.200 14316.400} -status PLACED
place_inst -name r432_0 -location {1162.080 13963.240} -status PLACED
place_inst -name r432_1 -location {985.960 13963.240} -status PLACED
place_inst -name r432_2 -location {807.840 13963.240} -status PLACED
place_inst -name b432 -location {630.720 13963.240} -status PLACED
place_inst -name r433_0 -location {630.720 13657.080} -status PLACED
place_inst -name r433_1 -location {630.720 13621.420} -status PLACED
place_inst -name r433_2 -location {630.720 13450.510} -status PLACED
place_inst -name b433 -location {630.720 13279.600} -status PLACED
place_inst -name r434_0 -location {630.720 14139.820} -status PLACED
place_inst -name b434 -location {630.720 14316.400} -status PLACED
place_inst -name r435_0 -location {520.440 13963.240} -status PLACED
place_inst -name r435_1 -location {410.160 13963.240} -status PLACED
place_inst -name r435_2 -location {299.880 13963.240} -status PLACED
place_inst -name b435 -location {189.600 13963.240} -status PLACED
place_inst -name r436_0 -location {189.600 13833.380} -status PLACED
place_inst -name r436_1 -location {189.600 13703.520} -status PLACED
place_inst -name r436_2 -location {189.600 13573.660} -status PLACED
place_inst -name b436 -location {189.600 13443.800} -status PLACED
place_inst -name r437_0 -location {189.600 14092.580} -status PLACED
place_inst -name r437_1 -location {189.600 14221.920} -status PLACED
place_inst -name r437_2 -location {189.600 14351.260} -status PLACED
place_inst -name b437 -location {189.600 14480.600} -status PLACED
place_inst -name r438_0 -location {8933.625 13962.272} -status PLACED
place_inst -name r438_1 -location {9106.290 13962.272} -status PLACED
place_inst -name r438_2 -location {9278.955 13962.272} -status PLACED
place_inst -name b438 -location {9451.620 13962.272} -status PLACED
place_inst -name r439_0 -location {9510.750 13848.493} -status PLACED
place_inst -name r439_1 -location {9569.880 13734.715} -status PLACED
place_inst -name r439_2 -location {9629.010 13628.040} -status PLACED
place_inst -name r439_3 -location {9688.140 13628.040} -status PLACED
place_inst -name r439_4 -location {9747.270 13302.840} -status PLACED
place_inst -name b439 -location {9806.400 13279.600} -status PLACED
place_inst -name r440_0 -location {9451.020 14140.545} -status PLACED
place_inst -name r440_1 -location {9453.160 14318.072} -status PLACED
place_inst -name r440_2 -location {9631.239 14318.072} -status PLACED
place_inst -name b440 -location {9806.400 14316.400} -status PLACED
place_inst -name r441_0 -location {9628.830 13963.240} -status PLACED
place_inst -name r441_1 -location {9806.040 13963.240} -status PLACED
place_inst -name r441_2 -location {9983.250 13962.756} -status PLACED
place_inst -name r441_3 -location {10159.640 13963.240} -status PLACED
place_inst -name r441_4 -location {10337.670 13963.079} -status PLACED
place_inst -name b441 -location {10514.880 13963.240} -status PLACED
place_inst -name r442_0 -location {10514.880 13657.080} -status PLACED
place_inst -name r442_1 -location {10514.880 13621.420} -status PLACED
place_inst -name r442_2 -location {10514.880 13450.510} -status PLACED
place_inst -name b442 -location {10514.880 13279.600} -status PLACED
place_inst -name r443_0 -location {10514.880 14139.820} -status PLACED
place_inst -name b443 -location {10514.880 14316.400} -status PLACED
place_inst -name r444_0 -location {10692.000 13963.240} -status PLACED
place_inst -name r444_1 -location {10868.120 13963.240} -status PLACED
place_inst -name r444_2 -location {11046.240 13963.240} -status PLACED
place_inst -name b444 -location {11223.360 13963.240} -status PLACED
place_inst -name r445_0 -location {11223.360 13657.080} -status PLACED
place_inst -name r445_1 -location {11223.360 13621.420} -status PLACED
place_inst -name r445_2 -location {11223.360 13450.510} -status PLACED
place_inst -name b445 -location {11223.360 13279.600} -status PLACED
place_inst -name r446_0 -location {11223.360 14139.820} -status PLACED
place_inst -name b446 -location {11223.360 14316.400} -status PLACED
place_inst -name r447_0 -location {11400.480 13963.240} -status PLACED
place_inst -name r447_1 -location {11576.600 13963.240} -status PLACED
place_inst -name r447_2 -location {11754.720 13963.240} -status PLACED
place_inst -name b447 -location {11931.840 13963.240} -status PLACED
place_inst -name r448_0 -location {11931.840 13657.080} -status PLACED
place_inst -name r448_1 -location {11931.840 13621.420} -status PLACED
place_inst -name r448_2 -location {11931.840 13450.510} -status PLACED
place_inst -name b448 -location {11931.840 13279.600} -status PLACED
place_inst -name r449_0 -location {11931.840 14139.820} -status PLACED
place_inst -name b449 -location {11931.840 14316.400} -status PLACED
place_inst -name r450_0 -location {12108.960 13963.240} -status PLACED
place_inst -name r450_1 -location {12285.080 13963.240} -status PLACED
place_inst -name r450_2 -location {12463.200 13963.240} -status PLACED
place_inst -name b450 -location {12640.320 13963.240} -status PLACED
place_inst -name r451_0 -location {12640.320 13657.080} -status PLACED
place_inst -name r451_1 -location {12640.320 13621.420} -status PLACED
place_inst -name r451_2 -location {12640.320 13450.510} -status PLACED
place_inst -name b451 -location {12640.320 13279.600} -status PLACED
place_inst -name r452_0 -location {12640.320 14139.820} -status PLACED
place_inst -name b452 -location {12640.320 14316.400} -status PLACED
place_inst -name r453_0 -location {12817.440 13963.240} -status PLACED
place_inst -name r453_1 -location {12993.560 13963.240} -status PLACED
place_inst -name r453_2 -location {13171.680 13963.240} -status PLACED
place_inst -name b453 -location {13348.800 13963.240} -status PLACED
place_inst -name r454_0 -location {13348.800 13657.080} -status PLACED
place_inst -name r454_1 -location {13348.800 13621.420} -status PLACED
place_inst -name r454_2 -location {13348.800 13450.510} -status PLACED
place_inst -name b454 -location {13348.800 13279.600} -status PLACED
place_inst -name r455_0 -location {13348.800 14139.820} -status PLACED
place_inst -name b455 -location {13348.800 14316.400} -status PLACED
place_inst -name r456_0 -location {13525.920 13963.240} -status PLACED
place_inst -name r456_1 -location {13704.040 13963.240} -status PLACED
place_inst -name r456_2 -location {13880.160 13963.240} -status PLACED
place_inst -name b456 -location {14057.280 13963.240} -status PLACED
place_inst -name r457_0 -location {14057.280 13657.080} -status PLACED
place_inst -name r457_1 -location {14057.280 13621.420} -status PLACED
place_inst -name r457_2 -location {14057.280 13450.510} -status PLACED
place_inst -name b457 -location {14057.280 13279.600} -status PLACED
place_inst -name r458_0 -location {14057.280 14139.820} -status PLACED
place_inst -name b458 -location {14057.280 14316.400} -status PLACED
place_inst -name r459_0 -location {14234.400 13963.240} -status PLACED
place_inst -name r459_1 -location {14410.520 13963.240} -status PLACED
place_inst -name r459_2 -location {14588.640 13963.240} -status PLACED
place_inst -name b459 -location {14765.760 13963.240} -status PLACED
place_inst -name r460_0 -location {14765.760 13657.080} -status PLACED
place_inst -name r460_1 -location {14765.760 13621.420} -status PLACED
place_inst -name r460_2 -location {14765.760 13450.510} -status PLACED
place_inst -name b460 -location {14765.760 13279.600} -status PLACED
place_inst -name r461_0 -location {14765.760 14139.820} -status PLACED
place_inst -name b461 -location {14765.760 14316.400} -status PLACED
place_inst -name r462_0 -location {14942.880 13963.240} -status PLACED
place_inst -name r462_1 -location {15119.000 13963.240} -status PLACED
place_inst -name r462_2 -location {15297.120 13963.240} -status PLACED
place_inst -name b462 -location {15474.240 13963.240} -status PLACED
place_inst -name r463_0 -location {15474.240 13657.080} -status PLACED
place_inst -name r463_1 -location {15474.240 13621.420} -status PLACED
place_inst -name r463_2 -location {15474.240 13450.510} -status PLACED
place_inst -name b463 -location {15474.240 13279.600} -status PLACED
place_inst -name r464_0 -location {15474.240 14139.820} -status PLACED
place_inst -name b464 -location {15474.240 14316.400} -status PLACED
place_inst -name r465_0 -location {15651.360 13963.240} -status PLACED
place_inst -name r465_1 -location {15827.480 13963.240} -status PLACED
place_inst -name r465_2 -location {16005.600 13963.240} -status PLACED
place_inst -name b465 -location {16182.720 13963.240} -status PLACED
place_inst -name r466_0 -location {16182.720 13657.080} -status PLACED
place_inst -name r466_1 -location {16182.720 13621.420} -status PLACED
place_inst -name r466_2 -location {16182.720 13450.510} -status PLACED
place_inst -name b466 -location {16182.720 13279.600} -status PLACED
place_inst -name r467_0 -location {16182.720 14139.820} -status PLACED
place_inst -name b467 -location {16182.720 14316.400} -status PLACED
place_inst -name r468_0 -location {16359.840 13963.240} -status PLACED
place_inst -name r468_1 -location {16535.960 13963.240} -status PLACED
place_inst -name r468_2 -location {16714.080 13963.240} -status PLACED
place_inst -name b468 -location {16891.200 13963.240} -status PLACED
place_inst -name r469_0 -location {16891.200 13657.080} -status PLACED
place_inst -name r469_1 -location {16891.200 13621.420} -status PLACED
place_inst -name r469_2 -location {16891.200 13450.510} -status PLACED
place_inst -name b469 -location {16891.200 13279.600} -status PLACED
place_inst -name r470_0 -location {16891.200 14139.820} -status PLACED
place_inst -name b470 -location {16891.200 14316.400} -status PLACED
place_inst -name r471_0 -location {17001.480 13963.240} -status PLACED
place_inst -name r471_1 -location {17111.760 13963.240} -status PLACED
place_inst -name r471_2 -location {17222.040 13963.240} -status PLACED
place_inst -name b471 -location {17332.320 13963.240} -status PLACED
place_inst -name r472_0 -location {17332.320 13833.380} -status PLACED
place_inst -name r472_1 -location {17332.320 13703.520} -status PLACED
place_inst -name r472_2 -location {17332.320 13573.660} -status PLACED
place_inst -name b472 -location {17332.320 13443.800} -status PLACED
place_inst -name r473_0 -location {17332.320 14092.580} -status PLACED
place_inst -name r473_1 -location {17332.320 14221.920} -status PLACED
place_inst -name r473_2 -location {17332.320 14351.260} -status PLACED
place_inst -name b473 -location {17332.320 14480.600} -status PLACED
place_inst -name r474_0 -location {8671.260 15074.885} -status PLACED
place_inst -name r474_1 -location {8581.560 15151.680} -status PLACED
place_inst -name r474_2 -location {8491.860 15228.474} -status PLACED
place_inst -name r474_3 -location {8402.160 15305.269} -status PLACED
place_inst -name r474_4 -location {8312.460 15382.064} -status PLACED
place_inst -name r474_5 -location {8222.760 15458.859} -status PLACED
place_inst -name r474_6 -location {8133.060 15535.653} -status PLACED
place_inst -name b474 -location {8043.360 15612.448} -status PLACED
place_inst -name r475_0 -location {7862.295 15612.448} -status PLACED
place_inst -name r475_1 -location {7681.230 15612.448} -status PLACED
place_inst -name r475_2 -location {7500.165 15612.448} -status PLACED
place_inst -name b475 -location {7319.100 15612.448} -status PLACED
place_inst -name r476_0 -location {7318.965 15785.236} -status PLACED
place_inst -name r476_1 -location {7318.830 15958.024} -status PLACED
place_inst -name r476_2 -location {7318.695 16130.812} -status PLACED
place_inst -name b476 -location {7318.560 16303.600} -status PLACED
place_inst -name r477_0 -location {7139.445 15612.448} -status PLACED
place_inst -name r477_1 -location {6959.790 15612.448} -status PLACED
place_inst -name r477_2 -location {6780.135 15612.448} -status PLACED
place_inst -name b477 -location {6600.480 15612.448} -status PLACED
place_inst -name r478_0 -location {6420.120 15612.448} -status PLACED
place_inst -name r478_1 -location {6239.760 15612.448} -status PLACED
place_inst -name r478_2 -location {6059.400 15612.448} -status PLACED
place_inst -name r478_3 -location {5879.040 15612.448} -status PLACED
place_inst -name r478_4 -location {5698.680 15612.448} -status PLACED
place_inst -name r478_5 -location {5518.320 15612.448} -status PLACED
place_inst -name r478_6 -location {5337.960 15612.448} -status PLACED
place_inst -name b478 -location {5157.600 15612.448} -status PLACED
place_inst -name r479_0 -location {4976.535 15612.448} -status PLACED
place_inst -name r479_1 -location {4795.470 15612.448} -status PLACED
place_inst -name r479_2 -location {4614.405 15612.448} -status PLACED
place_inst -name b479 -location {4433.340 15612.448} -status PLACED
place_inst -name r480_0 -location {4433.205 15785.236} -status PLACED
place_inst -name r480_1 -location {4433.070 15958.024} -status PLACED
place_inst -name r480_2 -location {4432.935 16130.812} -status PLACED
place_inst -name b480 -location {4432.800 16303.600} -status PLACED
place_inst -name r481_0 -location {4253.685 15612.448} -status PLACED
place_inst -name r481_1 -location {4074.030 15612.448} -status PLACED
place_inst -name r481_2 -location {3894.375 15612.448} -status PLACED
place_inst -name b481 -location {3714.720 15612.448} -status PLACED
place_inst -name r482_0 -location {3534.360 15612.448} -status PLACED
place_inst -name r482_1 -location {3354.000 15612.448} -status PLACED
place_inst -name r482_2 -location {3173.640 15612.448} -status PLACED
place_inst -name r482_3 -location {2993.280 15612.448} -status PLACED
place_inst -name r482_4 -location {2812.920 15612.448} -status PLACED
place_inst -name r482_5 -location {2632.560 15612.448} -status PLACED
place_inst -name r482_6 -location {2452.200 15612.448} -status PLACED
place_inst -name b482 -location {2271.840 15612.448} -status PLACED
place_inst -name r483_0 -location {2090.775 15612.448} -status PLACED
place_inst -name r483_1 -location {1909.710 15612.448} -status PLACED
place_inst -name r483_2 -location {1728.645 15612.448} -status PLACED
place_inst -name b483 -location {1547.580 15612.448} -status PLACED
place_inst -name r484_0 -location {1547.445 15785.236} -status PLACED
place_inst -name r484_1 -location {1547.310 15958.024} -status PLACED
place_inst -name r484_2 -location {1547.175 16130.812} -status PLACED
place_inst -name b484 -location {1547.040 16303.600} -status PLACED
place_inst -name r485_0 -location {8851.620 15074.885} -status PLACED
place_inst -name r485_1 -location {8942.280 15151.680} -status PLACED
place_inst -name r485_2 -location {9032.940 15228.474} -status PLACED
place_inst -name r485_3 -location {9123.600 15305.269} -status PLACED
place_inst -name r485_4 -location {9214.260 15382.064} -status PLACED
place_inst -name r485_5 -location {9304.920 15458.859} -status PLACED
place_inst -name r485_6 -location {9395.580 15535.653} -status PLACED
place_inst -name b485 -location {9486.240 15612.448} -status PLACED
place_inst -name r486_0 -location {9665.385 15612.448} -status PLACED
place_inst -name r486_1 -location {9844.530 15612.448} -status PLACED
place_inst -name r486_2 -location {10023.675 15612.448} -status PLACED
place_inst -name b486 -location {10202.820 15612.448} -status PLACED
place_inst -name r487_0 -location {10202.955 15785.236} -status PLACED
place_inst -name r487_1 -location {10203.090 15958.024} -status PLACED
place_inst -name r487_2 -location {10203.225 16130.812} -status PLACED
place_inst -name b487 -location {10203.360 16303.600} -status PLACED
place_inst -name r488_0 -location {10384.395 15612.448} -status PLACED
place_inst -name r488_1 -location {10565.970 15612.448} -status PLACED
place_inst -name r488_2 -location {10747.545 15612.448} -status PLACED
place_inst -name b488 -location {10929.120 15612.448} -status PLACED
place_inst -name r489_0 -location {11108.520 15612.448} -status PLACED
place_inst -name r489_1 -location {11287.920 15612.448} -status PLACED
place_inst -name r489_2 -location {11467.320 15612.448} -status PLACED
place_inst -name r489_3 -location {11647.720 15612.448} -status PLACED
place_inst -name r489_4 -location {11826.120 15612.448} -status PLACED
place_inst -name r489_5 -location {12005.520 15612.448} -status PLACED
place_inst -name r489_6 -location {12184.920 15612.448} -status PLACED
place_inst -name b489 -location {12364.320 15612.448} -status PLACED
place_inst -name r490_0 -location {12545.385 15612.448} -status PLACED
place_inst -name r490_1 -location {12726.450 15612.448} -status PLACED
place_inst -name r490_2 -location {12907.515 15612.448} -status PLACED
place_inst -name b490 -location {13088.580 15612.448} -status PLACED
place_inst -name r491_0 -location {13088.715 15785.236} -status PLACED
place_inst -name r491_1 -location {13088.850 15958.024} -status PLACED
place_inst -name r491_2 -location {13088.985 16130.812} -status PLACED
place_inst -name b491 -location {13089.120 16303.600} -status PLACED
place_inst -name r492_0 -location {13268.235 15612.448} -status PLACED
place_inst -name r492_1 -location {13447.890 15612.448} -status PLACED
place_inst -name r492_2 -location {13627.545 15612.448} -status PLACED
place_inst -name b492 -location {13807.200 15612.448} -status PLACED
place_inst -name r493_0 -location {13987.560 15612.448} -status PLACED
place_inst -name r493_1 -location {14167.920 15612.448} -status PLACED
place_inst -name r493_2 -location {14348.280 15612.448} -status PLACED
place_inst -name r493_3 -location {14528.640 15612.448} -status PLACED
place_inst -name r493_4 -location {14709.000 15612.448} -status PLACED
place_inst -name r493_5 -location {14889.360 15612.448} -status PLACED
place_inst -name r493_6 -location {15069.720 15612.448} -status PLACED
place_inst -name b493 -location {15250.080 15612.448} -status PLACED
place_inst -name r494_0 -location {15431.145 15612.448} -status PLACED
place_inst -name r494_1 -location {15612.210 15612.448} -status PLACED
place_inst -name r494_2 -location {15793.275 15612.448} -status PLACED
place_inst -name b494 -location {15974.340 15612.448} -status PLACED
place_inst -name r495_0 -location {15974.475 15785.236} -status PLACED
place_inst -name r495_1 -location {15974.610 15958.024} -status PLACED
place_inst -name r495_2 -location {15974.745 16130.812} -status PLACED
place_inst -name b495 -location {15974.880 16303.600} -status PLACED
set_wire_rc -signal -resistance 4.335802e-03 -capacitance 1.082436e-01
set_wire_rc -clock -resistance 4.335802e-03 -capacitance 1.082436e-01
estimate_parasitics -placement
create_clock -name vclk -period 833.333
set_driving_cell -lib_cell BUFx24_ASAP7_75t_R -pin Y [get_ports root]
set_input_delay 0 -clock vclk [get_ports root]
set_load 3.0 [all_outputs]
set_output_delay 0 -clock vclk [all_outputs]
set fh [open /work/clock/arr_$::env(CORNER).txt w]
foreach p [get_ports t_*] { set n [get_full_name $p]; set smx [get_property $p slack_max_rise]; set smn [get_property $p slack_min_rise]; puts $fh "T $n [expr {833.333 - $smx}] [expr {$smn}]" }
foreach i [get_cells b*] { set q [get_pins [get_full_name $i]/Y]; puts $fh "N [get_full_name $i] [get_property $q arrival_max_rise] [get_property $q arrival_min_rise]" }
close $fh
report_checks -path_delay max -group_path_count 1 -format full -fields {cap slew fanout}
puts OT_DONE
