# Actual source-owned landing bands; release exclusive regions before DPL/CTS.
set ::lpf_blk [ord::get_db_block]
set ::lpf_dbu [$::lpf_blk getDbUnitsPerMicron]
array set ::lpf_g {}
array set ::lpf_n {}
array set ::lpf_c {}
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_lk_0"]
odb::dbBox_create $::lpf_r [expr {round(54.000000*$::lpf_dbu)}] [expr {round(507.600000*$::lpf_dbu)}] [expr {round(145.800000*$::lpf_dbu)}] [expr {round(522.000000*$::lpf_dbu)}]
set ::lpf_g(lk_0) [odb::dbGroup_create $::lpf_r "lp_fence_grp_lk_0"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_lk_1"]
odb::dbBox_create $::lpf_r [expr {round(145.800000*$::lpf_dbu)}] [expr {round(507.600000*$::lpf_dbu)}] [expr {round(237.600000*$::lpf_dbu)}] [expr {round(522.000000*$::lpf_dbu)}]
set ::lpf_g(lk_1) [odb::dbGroup_create $::lpf_r "lp_fence_grp_lk_1"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_lk_2"]
odb::dbBox_create $::lpf_r [expr {round(237.600000*$::lpf_dbu)}] [expr {round(507.600000*$::lpf_dbu)}] [expr {round(329.400000*$::lpf_dbu)}] [expr {round(522.000000*$::lpf_dbu)}]
set ::lpf_g(lk_2) [odb::dbGroup_create $::lpf_r "lp_fence_grp_lk_2"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_lk_3"]
odb::dbBox_create $::lpf_r [expr {round(329.400000*$::lpf_dbu)}] [expr {round(507.600000*$::lpf_dbu)}] [expr {round(421.200000*$::lpf_dbu)}] [expr {round(522.000000*$::lpf_dbu)}]
set ::lpf_g(lk_3) [odb::dbGroup_create $::lpf_r "lp_fence_grp_lk_3"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_lk_4"]
odb::dbBox_create $::lpf_r [expr {round(54.000000*$::lpf_dbu)}] [expr {round(522.000000*$::lpf_dbu)}] [expr {round(145.800000*$::lpf_dbu)}] [expr {round(536.400000*$::lpf_dbu)}]
set ::lpf_g(lk_4) [odb::dbGroup_create $::lpf_r "lp_fence_grp_lk_4"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_lk_5"]
odb::dbBox_create $::lpf_r [expr {round(145.800000*$::lpf_dbu)}] [expr {round(522.000000*$::lpf_dbu)}] [expr {round(237.600000*$::lpf_dbu)}] [expr {round(536.400000*$::lpf_dbu)}]
set ::lpf_g(lk_5) [odb::dbGroup_create $::lpf_r "lp_fence_grp_lk_5"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_lk_6"]
odb::dbBox_create $::lpf_r [expr {round(237.600000*$::lpf_dbu)}] [expr {round(522.000000*$::lpf_dbu)}] [expr {round(329.400000*$::lpf_dbu)}] [expr {round(536.400000*$::lpf_dbu)}]
set ::lpf_g(lk_6) [odb::dbGroup_create $::lpf_r "lp_fence_grp_lk_6"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_lk_7"]
odb::dbBox_create $::lpf_r [expr {round(329.400000*$::lpf_dbu)}] [expr {round(522.000000*$::lpf_dbu)}] [expr {round(421.200000*$::lpf_dbu)}] [expr {round(536.400000*$::lpf_dbu)}]
set ::lpf_g(lk_7) [odb::dbGroup_create $::lpf_r "lp_fence_grp_lk_7"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_lk_8"]
odb::dbBox_create $::lpf_r [expr {round(54.000000*$::lpf_dbu)}] [expr {round(536.400000*$::lpf_dbu)}] [expr {round(145.800000*$::lpf_dbu)}] [expr {round(550.800000*$::lpf_dbu)}]
set ::lpf_g(lk_8) [odb::dbGroup_create $::lpf_r "lp_fence_grp_lk_8"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_lk_9"]
odb::dbBox_create $::lpf_r [expr {round(145.800000*$::lpf_dbu)}] [expr {round(536.400000*$::lpf_dbu)}] [expr {round(237.600000*$::lpf_dbu)}] [expr {round(550.800000*$::lpf_dbu)}]
set ::lpf_g(lk_9) [odb::dbGroup_create $::lpf_r "lp_fence_grp_lk_9"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_lk_10"]
odb::dbBox_create $::lpf_r [expr {round(237.600000*$::lpf_dbu)}] [expr {round(536.400000*$::lpf_dbu)}] [expr {round(329.400000*$::lpf_dbu)}] [expr {round(550.800000*$::lpf_dbu)}]
set ::lpf_g(lk_10) [odb::dbGroup_create $::lpf_r "lp_fence_grp_lk_10"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_lk_11"]
odb::dbBox_create $::lpf_r [expr {round(329.400000*$::lpf_dbu)}] [expr {round(536.400000*$::lpf_dbu)}] [expr {round(421.200000*$::lpf_dbu)}] [expr {round(550.800000*$::lpf_dbu)}]
set ::lpf_g(lk_11) [odb::dbGroup_create $::lpf_r "lp_fence_grp_lk_11"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_lk_rst"]
odb::dbBox_create $::lpf_r [expr {round(432.000000*$::lpf_dbu)}] [expr {round(507.600000*$::lpf_dbu)}] [expr {round(507.600000*$::lpf_dbu)}] [expr {round(550.800000*$::lpf_dbu)}]
set ::lpf_g(lk_rst) [odb::dbGroup_create $::lpf_r "lp_fence_grp_lk_rst"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_sq_0"]
odb::dbBox_create $::lpf_r [expr {round(54.000000*$::lpf_dbu)}] [expr {round(637.200000*$::lpf_dbu)}] [expr {round(145.800000*$::lpf_dbu)}] [expr {round(651.600000*$::lpf_dbu)}]
set ::lpf_g(sq_0) [odb::dbGroup_create $::lpf_r "lp_fence_grp_sq_0"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_sq_1"]
odb::dbBox_create $::lpf_r [expr {round(145.800000*$::lpf_dbu)}] [expr {round(637.200000*$::lpf_dbu)}] [expr {round(237.600000*$::lpf_dbu)}] [expr {round(651.600000*$::lpf_dbu)}]
set ::lpf_g(sq_1) [odb::dbGroup_create $::lpf_r "lp_fence_grp_sq_1"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_sq_2"]
odb::dbBox_create $::lpf_r [expr {round(237.600000*$::lpf_dbu)}] [expr {round(637.200000*$::lpf_dbu)}] [expr {round(329.400000*$::lpf_dbu)}] [expr {round(651.600000*$::lpf_dbu)}]
set ::lpf_g(sq_2) [odb::dbGroup_create $::lpf_r "lp_fence_grp_sq_2"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_sq_3"]
odb::dbBox_create $::lpf_r [expr {round(329.400000*$::lpf_dbu)}] [expr {round(637.200000*$::lpf_dbu)}] [expr {round(421.200000*$::lpf_dbu)}] [expr {round(651.600000*$::lpf_dbu)}]
set ::lpf_g(sq_3) [odb::dbGroup_create $::lpf_r "lp_fence_grp_sq_3"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_sq_4"]
odb::dbBox_create $::lpf_r [expr {round(54.000000*$::lpf_dbu)}] [expr {round(651.600000*$::lpf_dbu)}] [expr {round(145.800000*$::lpf_dbu)}] [expr {round(666.000000*$::lpf_dbu)}]
set ::lpf_g(sq_4) [odb::dbGroup_create $::lpf_r "lp_fence_grp_sq_4"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_sq_5"]
odb::dbBox_create $::lpf_r [expr {round(145.800000*$::lpf_dbu)}] [expr {round(651.600000*$::lpf_dbu)}] [expr {round(237.600000*$::lpf_dbu)}] [expr {round(666.000000*$::lpf_dbu)}]
set ::lpf_g(sq_5) [odb::dbGroup_create $::lpf_r "lp_fence_grp_sq_5"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_sq_6"]
odb::dbBox_create $::lpf_r [expr {round(237.600000*$::lpf_dbu)}] [expr {round(651.600000*$::lpf_dbu)}] [expr {round(329.400000*$::lpf_dbu)}] [expr {round(666.000000*$::lpf_dbu)}]
set ::lpf_g(sq_6) [odb::dbGroup_create $::lpf_r "lp_fence_grp_sq_6"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_sq_7"]
odb::dbBox_create $::lpf_r [expr {round(329.400000*$::lpf_dbu)}] [expr {round(651.600000*$::lpf_dbu)}] [expr {round(421.200000*$::lpf_dbu)}] [expr {round(666.000000*$::lpf_dbu)}]
set ::lpf_g(sq_7) [odb::dbGroup_create $::lpf_r "lp_fence_grp_sq_7"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_sq_8"]
odb::dbBox_create $::lpf_r [expr {round(54.000000*$::lpf_dbu)}] [expr {round(666.000000*$::lpf_dbu)}] [expr {round(145.800000*$::lpf_dbu)}] [expr {round(680.400000*$::lpf_dbu)}]
set ::lpf_g(sq_8) [odb::dbGroup_create $::lpf_r "lp_fence_grp_sq_8"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_sq_9"]
odb::dbBox_create $::lpf_r [expr {round(145.800000*$::lpf_dbu)}] [expr {round(666.000000*$::lpf_dbu)}] [expr {round(237.600000*$::lpf_dbu)}] [expr {round(680.400000*$::lpf_dbu)}]
set ::lpf_g(sq_9) [odb::dbGroup_create $::lpf_r "lp_fence_grp_sq_9"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_sq_10"]
odb::dbBox_create $::lpf_r [expr {round(237.600000*$::lpf_dbu)}] [expr {round(666.000000*$::lpf_dbu)}] [expr {round(329.400000*$::lpf_dbu)}] [expr {round(680.400000*$::lpf_dbu)}]
set ::lpf_g(sq_10) [odb::dbGroup_create $::lpf_r "lp_fence_grp_sq_10"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_sq_11"]
odb::dbBox_create $::lpf_r [expr {round(329.400000*$::lpf_dbu)}] [expr {round(666.000000*$::lpf_dbu)}] [expr {round(421.200000*$::lpf_dbu)}] [expr {round(680.400000*$::lpf_dbu)}]
set ::lpf_g(sq_11) [odb::dbGroup_create $::lpf_r "lp_fence_grp_sq_11"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_sq_12"]
odb::dbBox_create $::lpf_r [expr {round(54.000000*$::lpf_dbu)}] [expr {round(680.400000*$::lpf_dbu)}] [expr {round(145.800000*$::lpf_dbu)}] [expr {round(694.800000*$::lpf_dbu)}]
set ::lpf_g(sq_12) [odb::dbGroup_create $::lpf_r "lp_fence_grp_sq_12"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_sq_13"]
odb::dbBox_create $::lpf_r [expr {round(145.800000*$::lpf_dbu)}] [expr {round(680.400000*$::lpf_dbu)}] [expr {round(237.600000*$::lpf_dbu)}] [expr {round(694.800000*$::lpf_dbu)}]
set ::lpf_g(sq_13) [odb::dbGroup_create $::lpf_r "lp_fence_grp_sq_13"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_sq_14"]
odb::dbBox_create $::lpf_r [expr {round(237.600000*$::lpf_dbu)}] [expr {round(680.400000*$::lpf_dbu)}] [expr {round(329.400000*$::lpf_dbu)}] [expr {round(694.800000*$::lpf_dbu)}]
set ::lpf_g(sq_14) [odb::dbGroup_create $::lpf_r "lp_fence_grp_sq_14"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_sq_15"]
odb::dbBox_create $::lpf_r [expr {round(329.400000*$::lpf_dbu)}] [expr {round(680.400000*$::lpf_dbu)}] [expr {round(421.200000*$::lpf_dbu)}] [expr {round(694.800000*$::lpf_dbu)}]
set ::lpf_g(sq_15) [odb::dbGroup_create $::lpf_r "lp_fence_grp_sq_15"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_sq_16"]
odb::dbBox_create $::lpf_r [expr {round(54.000000*$::lpf_dbu)}] [expr {round(694.800000*$::lpf_dbu)}] [expr {round(145.800000*$::lpf_dbu)}] [expr {round(709.200000*$::lpf_dbu)}]
set ::lpf_g(sq_16) [odb::dbGroup_create $::lpf_r "lp_fence_grp_sq_16"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_sq_17"]
odb::dbBox_create $::lpf_r [expr {round(145.800000*$::lpf_dbu)}] [expr {round(694.800000*$::lpf_dbu)}] [expr {round(237.600000*$::lpf_dbu)}] [expr {round(709.200000*$::lpf_dbu)}]
set ::lpf_g(sq_17) [odb::dbGroup_create $::lpf_r "lp_fence_grp_sq_17"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_sq_18"]
odb::dbBox_create $::lpf_r [expr {round(237.600000*$::lpf_dbu)}] [expr {round(694.800000*$::lpf_dbu)}] [expr {round(329.400000*$::lpf_dbu)}] [expr {round(709.200000*$::lpf_dbu)}]
set ::lpf_g(sq_18) [odb::dbGroup_create $::lpf_r "lp_fence_grp_sq_18"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_sq_19"]
odb::dbBox_create $::lpf_r [expr {round(329.400000*$::lpf_dbu)}] [expr {round(694.800000*$::lpf_dbu)}] [expr {round(421.200000*$::lpf_dbu)}] [expr {round(709.200000*$::lpf_dbu)}]
set ::lpf_g(sq_19) [odb::dbGroup_create $::lpf_r "lp_fence_grp_sq_19"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_sq_20"]
odb::dbBox_create $::lpf_r [expr {round(54.000000*$::lpf_dbu)}] [expr {round(709.200000*$::lpf_dbu)}] [expr {round(145.800000*$::lpf_dbu)}] [expr {round(723.600000*$::lpf_dbu)}]
set ::lpf_g(sq_20) [odb::dbGroup_create $::lpf_r "lp_fence_grp_sq_20"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_sq_rst"]
odb::dbBox_create $::lpf_r [expr {round(432.000000*$::lpf_dbu)}] [expr {round(637.200000*$::lpf_dbu)}] [expr {round(507.600000*$::lpf_dbu)}] [expr {round(723.600000*$::lpf_dbu)}]
set ::lpf_g(sq_rst) [odb::dbGroup_create $::lpf_r "lp_fence_grp_sq_rst"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_vc_0"]
odb::dbBox_create $::lpf_r [expr {round(54.000000*$::lpf_dbu)}] [expr {round(993.600000*$::lpf_dbu)}] [expr {round(145.800000*$::lpf_dbu)}] [expr {round(1022.400000*$::lpf_dbu)}]
set ::lpf_g(vc_0) [odb::dbGroup_create $::lpf_r "lp_fence_grp_vc_0"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_vc_1"]
odb::dbBox_create $::lpf_r [expr {round(145.800000*$::lpf_dbu)}] [expr {round(993.600000*$::lpf_dbu)}] [expr {round(237.600000*$::lpf_dbu)}] [expr {round(1022.400000*$::lpf_dbu)}]
set ::lpf_g(vc_1) [odb::dbGroup_create $::lpf_r "lp_fence_grp_vc_1"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_vc_2"]
odb::dbBox_create $::lpf_r [expr {round(237.600000*$::lpf_dbu)}] [expr {round(993.600000*$::lpf_dbu)}] [expr {round(329.400000*$::lpf_dbu)}] [expr {round(1022.400000*$::lpf_dbu)}]
set ::lpf_g(vc_2) [odb::dbGroup_create $::lpf_r "lp_fence_grp_vc_2"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_vc_3"]
odb::dbBox_create $::lpf_r [expr {round(329.400000*$::lpf_dbu)}] [expr {round(993.600000*$::lpf_dbu)}] [expr {round(421.200000*$::lpf_dbu)}] [expr {round(1022.400000*$::lpf_dbu)}]
set ::lpf_g(vc_3) [odb::dbGroup_create $::lpf_r "lp_fence_grp_vc_3"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_vc_4"]
odb::dbBox_create $::lpf_r [expr {round(54.000000*$::lpf_dbu)}] [expr {round(1022.400000*$::lpf_dbu)}] [expr {round(145.800000*$::lpf_dbu)}] [expr {round(1051.200000*$::lpf_dbu)}]
set ::lpf_g(vc_4) [odb::dbGroup_create $::lpf_r "lp_fence_grp_vc_4"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_vc_5"]
odb::dbBox_create $::lpf_r [expr {round(145.800000*$::lpf_dbu)}] [expr {round(1022.400000*$::lpf_dbu)}] [expr {round(237.600000*$::lpf_dbu)}] [expr {round(1051.200000*$::lpf_dbu)}]
set ::lpf_g(vc_5) [odb::dbGroup_create $::lpf_r "lp_fence_grp_vc_5"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_vc_6"]
odb::dbBox_create $::lpf_r [expr {round(237.600000*$::lpf_dbu)}] [expr {round(1022.400000*$::lpf_dbu)}] [expr {round(329.400000*$::lpf_dbu)}] [expr {round(1051.200000*$::lpf_dbu)}]
set ::lpf_g(vc_6) [odb::dbGroup_create $::lpf_r "lp_fence_grp_vc_6"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_vc_7"]
odb::dbBox_create $::lpf_r [expr {round(329.400000*$::lpf_dbu)}] [expr {round(1022.400000*$::lpf_dbu)}] [expr {round(421.200000*$::lpf_dbu)}] [expr {round(1051.200000*$::lpf_dbu)}]
set ::lpf_g(vc_7) [odb::dbGroup_create $::lpf_r "lp_fence_grp_vc_7"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_vc_8"]
odb::dbBox_create $::lpf_r [expr {round(54.000000*$::lpf_dbu)}] [expr {round(1051.200000*$::lpf_dbu)}] [expr {round(145.800000*$::lpf_dbu)}] [expr {round(1080.000000*$::lpf_dbu)}]
set ::lpf_g(vc_8) [odb::dbGroup_create $::lpf_r "lp_fence_grp_vc_8"]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_vc_rst"]
odb::dbBox_create $::lpf_r [expr {round(432.000000*$::lpf_dbu)}] [expr {round(993.600000*$::lpf_dbu)}] [expr {round(507.600000*$::lpf_dbu)}] [expr {round(1080.000000*$::lpf_dbu)}]
set ::lpf_g(vc_rst) [odb::dbGroup_create $::lpf_r "lp_fence_grp_vc_rst"]
array set ::lpf_own {u_lpl_0_r lk_0 u_lpl_1_r lk_1 u_lpl_2_r lk_2 u_lpl_3_r lk_3 u_lpl_4_r lk_4 u_lpl_5_w lk_5 u_lpl_6_w lk_6 u_lpl_7_w lk_7 u_lpl_8_w lk_8 u_lpl_9_w lk_9 u_lpl_10_w lk_10 u_lpl_11_w lk_11 u_lpr_lk_p lk_rst u_lpr_lk_c0 lk_rst u_lpr_lk_c1 lk_rst u_lpr_lk_c2 lk_rst u_lpr_lk_c3 lk_rst u_lprc_u_l0 lk_rst u_lpl_0_w sq_0 u_lpl_1_w sq_1 u_lpl_2_w sq_2 u_lpl_3_w sq_3 u_lpl_4_w sq_4 u_lpl_5_r sq_5 u_lpl_6_r sq_6 u_lpl_7_r sq_7 u_lpl_8_r sq_8 u_lpl_9_r sq_9 u_lpl_10_r sq_10 u_lpl_11_r sq_11 u_lpl_12_r sq_12 u_lpl_13_r sq_13 u_lpl_14_r sq_14 u_lpl_15_w sq_15 u_lpl_16_w sq_16 u_lpl_17_w sq_17 u_lpl_18_w sq_18 u_lpl_19_w sq_19 u_lpl_20_w sq_20 u_lpr_sq_p sq_rst u_lpr_sq_c0 sq_rst u_lpr_sq_c1 sq_rst u_lpr_sq_c2 sq_rst u_lpr_sq_c3 sq_rst u_lpr_sq_c4 sq_rst u_lpr_sq_c5 sq_rst u_lpr_sq_c6 sq_rst u_lpr_sq_c7 sq_rst u_lprc_u_l1 sq_rst u_lpl_12_w vc_0 u_lpl_13_w vc_1 u_lpl_14_w vc_2 u_lpl_15_r vc_3 u_lpl_16_r vc_4 u_lpl_17_r vc_5 u_lpl_18_r vc_6 u_lpl_19_r vc_7 u_lpl_20_r vc_8 u_lpr_vc_p vc_rst u_lpr_vc_c0 vc_rst u_lpr_vc_c1 vc_rst u_lpr_vc_c2 vc_rst u_lpr_vc_c3 vc_rst u_lprc_u_l2 vc_rst}
proc lpf_seq {m} {
  foreach mt [$m getMTerms] { if {[$mt getSigType] eq "CLOCK"} { return 1 } }
  return 0
}
set ::lpf_reads {}
foreach i [$::lpf_blk getInsts] {
  if {[[$i getMaster] isBlock] || [[$i getMaster] getType] ne "CORE"} continue
  regsub -all {\\} [$i getName] {} n
  if {![regexp {(?:^|[./])(u_lpl_[0-9]+_[wr]|u_lpr_(?:lk|sq|vc)_(?:p|c[0-9]+)|u_lprc_u_l[0-2])[./]} $n -> h]} continue
  if {![info exists ::lpf_own($h)]} { error "LP_FENCE: $n has no landing owner" }
  if {[$i getGroup] ne "NULL"} continue
  set r $::lpf_own($h)
  $::lpf_g($r) addInst $i
  incr ::lpf_n($r)
  if {[string match *_r $h] && [lpf_seq [$i getMaster]]} { lappend ::lpf_reads [list $i $r] }
}
# read-mux cone: walk back from every read-half register's data inputs through ungrouped combinational cells
foreach ir $::lpf_reads {
  lassign $ir i r
  set front [list $i]
  for {set d 0} {$d < 16 && [llength $front]} {incr d} {
    set nxt {}
    foreach x $front {
      foreach it [$x getITerms] {
        if {![$it isInputSignal] || [[$it getMTerm] getSigType] eq "CLOCK"} continue
        set net [$it getNet]
        if {$net eq "NULL" || [$net getSigType] ne "SIGNAL"} continue
        foreach dt [$net getITerms] {
          if {![$dt isOutputSignal]} continue
          set di [$dt getInst]
          set dm [$di getMaster]
          if {[$dm isBlock] || [$dm getType] ne "CORE" || [$di getGroup] ne "NULL" || [lpf_seq $dm]} continue
          $::lpf_g($r) addInst $di
          incr ::lpf_c($r)
          lappend nxt $di
        }
      }
    }
    set front $nxt
  }
}

foreach r {lk_0 lk_1 lk_2 lk_3 lk_4 lk_5 lk_6 lk_7 lk_8 lk_9 lk_10 lk_11 lk_rst sq_0 sq_1 sq_2 sq_3 sq_4 sq_5 sq_6 sq_7 sq_8 sq_9 sq_10 sq_11 sq_12 sq_13 sq_14 sq_15 sq_16 sq_17 sq_18 sq_19 sq_20 sq_rst vc_0 vc_1 vc_2 vc_3 vc_4 vc_5 vc_6 vc_7 vc_8 vc_rst} {
  if {![info exists ::lpf_n($r)] || $::lpf_n($r) < 1} { error "LP_FENCE: region $r got no landing cells" }
  if {![info exists ::lpf_c($r)]} { set ::lpf_c($r) 0 }
  puts "LP_FENCE $r cells=$::lpf_n($r) read_cone=$::lpf_c($r)"
}
