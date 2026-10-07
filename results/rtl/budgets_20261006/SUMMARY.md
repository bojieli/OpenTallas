# Budget sheets: summary (tools/budgets/budget_sheet.py)

262 hardened masters. Sign-off 833.333 ps, SS 60 / FF 25 ps, accept +15/+15; skew terms intra (clock-plan region bound + 25, <= 90) / inter-region, meso, cross-domain 150 / forwarded-clock hop 0; wire 1.135 ps/um SS; reach 412 um intra, 359 um inter, 491 um forwarded.

| master | kind | dies (instances) | size um | block insertion SS (grade) / target | die entry target SS | ports | max L um | max stages | infeasible | fanout flags |
|---|---|---|---|---|---|---:|---:|---:|---:|---:|
| dsfd_bf | bf | s81_layer:440, s81_layer1:440, s81_head:316 | 1003 x 199 | 816.1 (target) / 816.1 | 289.3..387.4 | 7 | 533 | 2 | 2 | 0 |
| dsfd_bk_collector | band_blk | s81_layer:1, s81_layer1:1, s81_head:1 | 5270 x 881 | 900 (target) / 900 | 3840.3..3862.5 | 5 | 417 | 1 | 0 | 0 |
| dsfd_bk_selector | band_blk | s81_layer:1, s81_layer1:1, s81_head:1 | 5270 x 322 | 900 (target) / 900 | 3838.4..3859.8 | 5 | 415 | 1 | 0 | 0 |
| dsfd_capt_ctl | tile | s81 (in slab dsfd_sp_capture):1 | 86 x 324 | 268 (measured) / 574.7 | 4493.7..4493.7 | 4 | 562 | 2 | 2 | 0 |
| dsfd_capt_grp | tile | s81 (in slab dsfd_sp_capture):8 | 119 x 324 | 599.7 (target) / 599.7 | 4162.0..4162.0 | 4 | 562 | 2 | 2 | 0 |
| dsfd_cfifo | cfifo | s81_layer:128, s81_layer1:128, s81_head:128 | 850 x 47 | 603.8 (target) / 603.8 | 3838.4..4158.0 | 7 | 699 | 2 | 1 | 0 |
| dsfd_coll_ck | tile | s81 (in slab dsfd_sp_collective):1 | 216 x 216 | 616.8 (target) / 616.8 | - | 0 | 0 | 0 | 0 | 0 |
| dsfd_coll_core | tile | s81 (in slab dsfd_sp_collective):1 | 507 x 1361 | 900 (target) / 900 | - | 10 | 443 | 1 | 0 | 0 |
| dsfd_coll_lane_e | tile | s81 (in slab dsfd_sp_collective):4 | 254 x 340 | 684.2 (target) / 684.2 | - | 10 | 443 | 1 | 0 | 0 |
| dsfd_coll_lane_w | tile | s81 (in slab dsfd_sp_collective):4 | 254 x 340 | 684.2 (target) / 684.2 | - | 10 | 443 | 1 | 0 | 0 |
| dsfd_colt_lane | tile | s81 (in slab dsfd_bk_collector):4 | 432 x 130 | 634.7 (target) / 634.7 | 4127.8..4127.8 | 4 | 371 | 1 | 0 | 0 |
| dsfd_colt_mrg | tile | s81 (in slab dsfd_bk_collector):1 | 216 x 151 | 586.3 (target) / 586.3 | 4176.2..4176.2 | 5 | 417 | 1 | 0 | 0 |
| dsfd_ctrl | ctrl | s81_layer:4, s81_layer1:1, s81_head:4 | 8500 x 248 | 900 (target) / 900 | 3840.3..3861.8 | 2 | 9 | 1 | 0 | 0 |
| dsfd_ctrl_ctr | tile | s81 (in slab dsfd_ctrl):1 | 43 x 43 | 467.4 (target) / 467.4 | 4294.4..4294.4 | 3 | 51 | 1 | 0 | 0 |
| dsfd_ctrl_pc | tile | s81 (in slab dsfd_ctrl):32 | 121 x 248 | 580 (target) / 580 | 4181.8..4181.8 | 25 | 144 | 1 | 0 | 0 |
| dsfd_hbglue | hbglue | s81_head:85 | 302 x 151 | 614.9 (target) / 614.9 | 360.4..360.4 | 46 | 744 | 2 | 9 | 0 |
| dsfd_hstnh_1024 | hstn | s81_layer:13, s81_layer1:13, s81_head:13 | 17 x 54 | 456.4 (target) / 456.4 | 1403.4..1422.8 | 2 | 299 | 1 | 0 | 0 |
| dsfd_hstnh_512 | hstn | s81_layer:17, s81_layer1:17, s81_head:17 | 17 x 30 | 449.8 (target) / 449.8 | 960.2..4311.9 | 2 | 214 | 1 | 0 | 0 |
| dsfd_hstnh_576 | hstn | s81_layer:2, s81_layer1:2, s81_head:2 | 17 x 32 | 450.4 (target) / 450.4 | 4123.3..4311.3 | 2 | 235 | 1 | 0 | 0 |
| dsfd_hstnh_692 | hstn | s81_layer:8, s81_layer1:9, s81_head:9 | 17 x 39 | 452.4 (target) / 452.4 | 4287.2..4309.3 | 2 | 194 | 1 | 0 | 0 |
| dsfd_hstnh_761 | hstn | s81_layer:17, s81_layer1:17, s81_head:17 | 17 x 43 | 453.6 (target) / 453.6 | 4286.0..4308.1 | 2 | 193 | 1 | 0 | 0 |
| dsfd_hstnv_1024 | hstn | s81_layer:37, s81_layer1:34, s81_head:34 | 54 x 17 | 456.4 (target) / 456.4 | 1403.4..1422.8 | 2 | 220 | 1 | 0 | 0 |
| dsfd_hstnv_512 | hstn | s81_layer:11, s81_layer1:5, s81_head:5 | 29 x 17 | 449.5 (target) / 449.5 | 1413.1..4312.2 | 2 | 259 | 1 | 0 | 0 |
| dsfd_hstnv_576 | hstn | s81_layer:17, s81_layer1:6, s81_head:6 | 32 x 17 | 450.4 (target) / 450.4 | 4123.3..4311.3 | 2 | 194 | 1 | 0 | 0 |
| dsfd_l2r_vr_512x1__hq_NE | hend | s81_layer:1, s81_head:1 | 65 x 65 | 486 (target) / 486 | 4087.7..4275.7 | 3 | 383 | 1 | 0 | 0 |
| dsfd_l2r_vr_512x1__hq_NW | hend | s81_layer:1, s81_head:1 | 65 x 65 | 486 (target) / 486 | 3856.5..3861.3 | 3 | 384 | 1 | 0 | 0 |
| dsfd_l2r_vr_512x1__hq_SE | hend | s81_layer:1, s81_head:1 | 65 x 65 | 486 (target) / 486 | 4268.8..4275.7 | 3 | 383 | 1 | 0 | 0 |
| dsfd_l2r_vr_512x1__hq_SW | hend | s81_layer:1, s81_layer1:1, s81_head:1 | 65 x 65 | 486 (target) / 486 | 3856.6..4253.6 | 3 | 384 | 1 | 0 | 0 |
| dsfd_l2r_vr_564x1__hx_E | hend | s81_layer:1, s81_layer1:1, s81_head:1 | 70 x 71 | 490.9 (target) / 490.9 | 4082.8..4270.8 | 3 | 382 | 1 | 0 | 0 |
| dsfd_l2r_vr_564x1__hx_W | hend | s81_layer:1, s81_layer1:1, s81_head:1 | 70 x 71 | 490.9 (target) / 490.9 | 3839.9..3861.8 | 3 | 383 | 1 | 0 | 0 |
| dsfd_m2l_raw_512x1__hl_E0 | hend | s81_layer:1, s81_layer1:1, s81_head:1 | 63 x 65 | 485.3 (target) / 485.3 | 4088.4..4276.4 | 2 | 247 | 1 | 0 | 0 |
| dsfd_m2l_raw_512x1__hl_E1 | hend | s81_layer:1, s81_layer1:1, s81_head:1 | 63 x 65 | 485.3 (target) / 485.3 | 4088.4..4276.4 | 2 | 215 | 1 | 0 | 0 |
| dsfd_m2l_raw_512x1__hl_E2 | hend | s81_layer:1, s81_layer1:1, s81_head:1 | 63 x 65 | 485.3 (target) / 485.3 | 4088.4..4276.4 | 2 | 263 | 1 | 0 | 0 |
| dsfd_m2l_raw_512x1__hl_E3 | hend | s81_layer:1, s81_layer1:1, s81_head:1 | 63 x 65 | 485.3 (target) / 485.3 | 4088.4..4276.4 | 2 | 250 | 1 | 0 | 0 |
| dsfd_m2l_raw_512x1__hl_W0 | hend | s81_layer:1, s81_layer1:1, s81_head:1 | 63 x 65 | 485.3 (target) / 485.3 | 3845.5..3862.0 | 2 | 212 | 1 | 0 | 0 |
| dsfd_m2l_raw_512x1__hl_W1 | hend | s81_layer:1, s81_layer1:1, s81_head:1 | 63 x 65 | 485.3 (target) / 485.3 | 3845.5..3862.0 | 2 | 103 | 1 | 0 | 0 |
| dsfd_m2l_raw_512x1__hl_W2 | hend | s81_layer:1, s81_layer1:1, s81_head:1 | 63 x 65 | 485.3 (target) / 485.3 | 3845.5..3862.0 | 2 | 272 | 1 | 0 | 0 |
| dsfd_m2l_raw_512x1__hl_W3 | hend | s81_layer:1, s81_layer1:1, s81_head:1 | 63 x 65 | 485.3 (target) / 485.3 | 3840.3..3862.0 | 2 | 40 | 1 | 0 | 0 |
| dsfd_m2l_vr_512x1__hco_NE | hend | s81_layer:1, s81_head:1 | 63 x 65 | 485.3 (target) / 485.3 | 4271.9..4277.2 | 2 | 190 | 1 | 0 | 0 |
| dsfd_m2l_vr_512x1__hco_NW | hend | s81_layer:1, s81_head:1 | 63 x 65 | 485.3 (target) / 485.3 | 4271.3..4276.5 | 2 | 6 | 1 | 0 | 0 |
| dsfd_m2l_vr_512x1__hco_SE | hend | s81_layer:1, s81_head:1 | 63 x 65 | 485.3 (target) / 485.3 | 4271.9..4277.2 | 2 | 6 | 1 | 0 | 0 |
| dsfd_m2l_vr_512x1__hco_SW | hend | s81_layer:1, s81_layer1:1, s81_head:1 | 63 x 65 | 485.3 (target) / 485.3 | 4255.0..4276.5 | 2 | 190 | 1 | 0 | 0 |
| dsfd_m2l_vr_512x1__hix_NE | hend | s81_layer:1, s81_head:1 | 63 x 65 | 485.3 (target) / 485.3 | 3856.6..3861.8 | 2 | 119 | 1 | 0 | 0 |
| dsfd_m2l_vr_512x1__hix_NW | hend | s81_layer:1, s81_head:1 | 63 x 65 | 485.3 (target) / 485.3 | 4269.3..4274.5 | 2 | 182 | 1 | 0 | 0 |
| dsfd_m2l_vr_512x1__hix_SE | hend | s81_layer:1, s81_head:1 | 63 x 65 | 485.3 (target) / 485.3 | 3856.6..3861.8 | 2 | 220 | 1 | 0 | 0 |
| dsfd_m2l_vr_512x1__hix_SW | hend | s81_layer:1, s81_layer1:1, s81_head:1 | 63 x 65 | 485.3 (target) / 485.3 | 4253.7..4274.5 | 2 | 292 | 1 | 0 | 0 |
| dsfd_m2l_vr_512x1__hqe_NE | hend | s81_layer:1, s81_head:1 | 63 x 65 | 485.3 (target) / 485.3 | 4269.4..4276.5 | 2 | 63 | 1 | 0 | 0 |
| dsfd_m2l_vr_512x1__hqe_NW | hend | s81_layer:1, s81_head:1 | 63 x 65 | 485.3 (target) / 485.3 | 4271.3..4276.5 | 2 | 216 | 1 | 0 | 0 |
| dsfd_m2l_vr_512x1__hqe_SE | hend | s81_layer:1, s81_head:1 | 63 x 65 | 485.3 (target) / 485.3 | 4268.1..4273.4 | 2 | 231 | 1 | 0 | 0 |
| dsfd_m2l_vr_512x1__hqe_SW | hend | s81_layer:1, s81_layer1:1, s81_head:1 | 63 x 65 | 485.3 (target) / 485.3 | 4253.7..4274.5 | 2 | 48 | 1 | 0 | 0 |
| dsfd_m2l_vr_68x10__hr_E0 | hend | s81_layer:1, s81_layer1:1, s81_head:1 | 108 x 110 | 524.5 (target) / 524.5 | 4215.1..4237.2 | 11 | 883 | 2 | 10 | 0 |
| dsfd_m2l_vr_68x10__hr_E5 | hend | s81_layer:1, s81_layer1:1, s81_head:1 | 108 x 110 | 524.5 (target) / 524.5 | 4215.1..4237.2 | 11 | 643 | 2 | 10 | 0 |
| dsfd_m2l_vr_68x10__hr_W0 | hend | s81_layer:1, s81_layer1:1, s81_head:1 | 108 x 110 | 524.5 (target) / 524.5 | 4215.1..4237.2 | 11 | 312 | 1 | 0 | 0 |
| dsfd_m2l_vr_68x10__hr_W5 | hend | s81_layer:1, s81_layer1:1, s81_head:1 | 108 x 110 | 524.5 (target) / 524.5 | 4215.1..4237.2 | 11 | 405 | 1 | 0 | 0 |
| dsfd_m2l_vr_68x11__hr_E1 | hend | s81_layer:1, s81_layer1:1, s81_head:1 | 118 x 119 | 532.4 (target) / 532.4 | 4207.2..4229.3 | 12 | 240 | 1 | 0 | 0 |
| dsfd_m2l_vr_68x11__hr_E2 | hend | s81_layer:1, s81_layer1:1, s81_head:1 | 118 x 119 | 532.4 (target) / 532.4 | 4207.2..4229.3 | 12 | 558 | 2 | 11 | 0 |
| dsfd_m2l_vr_68x11__hr_E3 | hend | s81_layer:1, s81_layer1:1, s81_head:1 | 118 x 119 | 532.4 (target) / 532.4 | 4207.2..4229.3 | 12 | 470 | 1 | 0 | 0 |
| dsfd_m2l_vr_68x11__hr_E4 | hend | s81_layer:1, s81_layer1:1, s81_head:1 | 118 x 119 | 532.4 (target) / 532.4 | 4207.2..4229.3 | 12 | 359 | 1 | 0 | 0 |
| dsfd_m2l_vr_68x11__hr_W1 | hend | s81_layer:1, s81_layer1:1, s81_head:1 | 118 x 119 | 532.4 (target) / 532.4 | 4207.2..4229.3 | 12 | 246 | 1 | 0 | 0 |
| dsfd_m2l_vr_68x11__hr_W2 | hend | s81_layer:1, s81_layer1:1, s81_head:1 | 118 x 119 | 532.4 (target) / 532.4 | 4207.2..4229.3 | 12 | 390 | 1 | 0 | 0 |
| dsfd_m2l_vr_68x11__hr_W3 | hend | s81_layer:1, s81_layer1:1, s81_head:1 | 118 x 119 | 532.4 (target) / 532.4 | 4207.2..4229.3 | 12 | 265 | 1 | 0 | 0 |
| dsfd_m2l_vr_68x11__hr_W4 | hend | s81_layer:1, s81_layer1:1, s81_head:1 | 118 x 119 | 532.4 (target) / 532.4 | 4207.2..4229.3 | 12 | 365 | 1 | 0 | 0 |
| dsfd_node_LLd | node | s81_layer:128, s81_layer1:128, s81_head:111 | 86 x 78 | 500.9 (target) / 500.9 | 604.5..702.6 | 4 | 352 | 1 | 0 | 0 |
| dsfd_node_LLfd | node | s81_layer:898, s81_layer1:898, s81_head:777 | 86 x 78 | 500.9 (target) / 500.9 | 604.5..702.6 | 5 | 466 | 2 | 1 | 0 |
| dsfd_node_LLfu | node | s81_layer:1024, s81_layer1:1024, s81_head:583 | 86 x 78 | 500.9 (target) / 500.9 | 604.5..702.6 | 5 | 466 | 2 | 2 | 0 |
| dsfd_node_NNfd | node | s81_layer:1024, s81_layer1:1024, s81_head:583 | 86 x 78 | 500.9 (target) / 500.9 | 604.5..702.6 | 5 | 312 | 1 | 0 | 0 |
| dsfd_node_NNfu | node | s81_layer:898, s81_layer1:898, s81_head:777 | 86 x 78 | 500.9 (target) / 500.9 | 604.5..702.6 | 5 | 204 | 1 | 0 | 0 |
| dsfd_qbank_N | qbank | s81_layer:1610, s81_layer1:1610, s81_head:1155 | 60 x 6 | 447.1 (target) / 447.1 | 658.3..756.4 | 8 | 774 | 2 | 4 | 0 |
| dsfd_qbank_S | qbank | s81_layer:1610, s81_layer1:1610, s81_head:1155 | 60 x 6 | 447.1 (target) / 447.1 | 658.3..756.4 | 6 | 405 | 1 | 0 | 0 |
| dsfd_r2l_vr_1024x1__ha_NE | hend | s81_layer:1, s81_head:1 | 112 x 112 | 527.1 (target) / 527.1 | 1335.5..1352.1 | 2 | 291 | 1 | 0 | 0 |
| dsfd_r2l_vr_1024x1__ha_NW | hend | s81_layer:1, s81_head:1 | 112 x 112 | 527.1 (target) / 527.1 | 1335.5..1352.1 | 2 | 390 | 1 | 0 | 0 |
| dsfd_r2l_vr_1024x1__ha_SE | hend | s81_layer:1, s81_head:1 | 112 x 112 | 527.1 (target) / 527.1 | 1335.5..1352.1 | 2 | 294 | 1 | 0 | 0 |
| dsfd_r2l_vr_1024x1__ha_SW | hend | s81_layer:1, s81_layer1:1, s81_head:1 | 112 x 112 | 527.1 (target) / 527.1 | 1335.5..1352.1 | 2 | 392 | 1 | 0 | 0 |
| dsfd_r2l_vr_512x1__hcol | hend | s81_layer:1, s81_layer1:1, s81_head:1 | 63 x 65 | 485.3 (target) / 485.3 | 1377.3..1393.9 | 2 | 630 | 2 | 1 | 0 |
| dsfd_r2l_vr_512x1__hsel | hend | s81_layer:1, s81_layer1:1, s81_head:1 | 63 x 65 | 485.3 (target) / 485.3 | 1377.3..1393.9 | 2 | 632 | 2 | 1 | 0 |
| dsfd_rly_15_EN | rly | s81_layer:6, s81_layer1:6, s81_head:20 | 17 x 17 | 444.9 (target) / 444.9 | 530.4..735.1 | 2 | 297 | 1 | 0 | 0 |
| dsfd_rly_15_EW | rly | s81_layer:128, s81_layer1:128, s81_head:128 | 17 x 17 | 444.9 (target) / 444.9 | 530.4..758.6 | 2 | 163 | 1 | 0 | 0 |
| dsfd_rly_15_NS | rly | s81_head:68 | 17 x 17 | 444.9 (target) / 444.9 | 530.4..530.4 | 2 | 393 | 1 | 0 | 0 |
| dsfd_rly_15_SN | rly | s81_layer:790, s81_layer1:790, s81_head:620 | 17 x 17 | 444.9 (target) / 444.9 | 530.4..758.6 | 2 | 297 | 1 | 0 | 0 |
| dsfd_rly_15_WN | rly | s81_layer:356, s81_layer1:356, s81_head:250 | 17 x 17 | 444.9 (target) / 444.9 | 660.5..758.6 | 2 | 239 | 1 | 0 | 0 |
| dsfd_rly_1_ES | rly | s81_layer:198, s81_layer1:198, s81_head:172 | 17 x 17 | 444.9 (target) / 444.9 | 678.7..735.1 | 2 | 562 | 2 | 1 | 0 |
| dsfd_rly_1_EW | rly | s81_layer:545, s81_layer1:545, s81_head:424 | 17 x 17 | 444.9 (target) / 444.9 | 660.5..758.6 | 2 | 286 | 1 | 0 | 0 |
| dsfd_rly_1_NW | rly | s81_layer:99, s81_layer1:99, s81_head:86 | 17 x 17 | 444.9 (target) / 444.9 | 678.7..735.1 | 2 | 562 | 2 | 1 | 0 |
| dsfd_rly_1_SN | rly | s81_layer:312, s81_layer1:312, s81_head:206 | 17 x 17 | 444.9 (target) / 444.9 | 660.5..758.6 | 2 | 375 | 1 | 0 | 0 |
| dsfd_rly_1_WE | rly | s81_head:255 | 17 x 17 | 444.9 (target) / 444.9 | 530.4..530.4 | 2 | 189 | 1 | 0 | 0 |
| dsfd_rly_1_WN | rly | s81_layer:440, s81_layer1:440, s81_head:401 | 17 x 17 | 444.9 (target) / 444.9 | 530.4..758.6 | 2 | 1133 | 3 | 1 | 0 |
| dsfd_rly_266_EN | rly | s81_head:17 | 17 x 19 | 445.8 (target) / 445.8 | 529.5..529.5 | 2 | 146 | 1 | 0 | 0 |
| dsfd_rly_266_ES | rly | s81_head:28 | 17 x 19 | 445.8 (target) / 445.8 | 710.2..734.2 | 2 | 427 | 1 | 0 | 0 |
| dsfd_rly_266_EW | rly | s81_layer:128, s81_layer1:128, s81_head:145 | 17 x 19 | 445.8 (target) / 445.8 | 529.5..757.7 | 2 | 190 | 1 | 0 | 0 |
| dsfd_rly_266_NS | rly | s81_layer:356, s81_layer1:356, s81_head:250 | 17 x 19 | 445.8 (target) / 445.8 | 659.6..757.7 | 2 | 312 | 1 | 0 | 0 |
| dsfd_rly_266_SE | rly | s81_layer:71, s81_layer1:71, s81_head:68 | 17 x 19 | 445.8 (target) / 445.8 | 529.5..757.7 | 2 | 429 | 1 | 0 | 0 |
| dsfd_rly_266_SN | rly | s81_layer:796, s81_layer1:796, s81_head:555 | 17 x 19 | 445.8 (target) / 445.8 | 659.6..757.7 | 2 | 265 | 1 | 0 | 0 |
| dsfd_rly_266_SW | rly | s81_head:28 | 17 x 19 | 445.8 (target) / 445.8 | 710.2..734.2 | 2 | 427 | 1 | 0 | 0 |
| dsfd_rly_266_WE | rly | s81_layer:840, s81_layer1:840, s81_head:555 | 17 x 19 | 445.8 (target) / 445.8 | 659.6..757.7 | 2 | 486 | 2 | 1 | 0 |
| dsfd_rly_266_WN | rly | s81_layer:2, s81_layer1:2, s81_head:80 | 17 x 19 | 445.8 (target) / 445.8 | 529.5..734.2 | 2 | 742 | 2 | 1 | 0 |
| dsfd_rly_266_WS | rly | s81_head:30 | 17 x 19 | 445.8 (target) / 445.8 | 659.6..710.4 | 2 | 532 | 2 | 2 | 0 |
| dsfd_rly_283_EN | rly | s81_head:17 | 17 x 19 | 445.8 (target) / 445.8 | 529.5..529.5 | 2 | 146 | 1 | 0 | 0 |
| dsfd_rly_283_EW | rly | s81_layer:198, s81_layer1:198, s81_head:168 | 17 x 19 | 445.8 (target) / 445.8 | 529.5..757.7 | 2 | 173 | 1 | 0 | 0 |
| dsfd_rly_283_NS | rly | s81_layer:356, s81_layer1:356, s81_head:318 | 17 x 19 | 445.8 (target) / 445.8 | 529.5..757.7 | 2 | 404 | 1 | 0 | 0 |
| dsfd_rly_283_SE | rly | s81_layer:99, s81_layer1:99, s81_head:86 | 17 x 19 | 445.8 (target) / 445.8 | 677.8..734.2 | 2 | 309 | 1 | 0 | 0 |
| dsfd_rly_283_SN | rly | s81_layer:29, s81_layer1:29, s81_head:98 | 17 x 19 | 445.8 (target) / 445.8 | 529.5..757.7 | 2 | 405 | 1 | 0 | 0 |
| dsfd_rly_283_WE | rly | s81_layer:671, s81_layer1:671, s81_head:469 | 17 x 19 | 445.8 (target) / 445.8 | 659.6..757.7 | 2 | 413 | 1 | 0 | 0 |
| dsfd_rly_2_EN | rly | s81_layer:2, s81_layer1:2 | 17 x 17 | 444.9 (target) / 444.9 | 727.9..727.9 | 2 | 141 | 1 | 0 | 0 |
| dsfd_rly_2_ES | rly | s81_layer:1125, s81_layer1:1125, s81_head:805 | 17 x 17 | 444.9 (target) / 444.9 | 660.5..758.6 | 2 | 406 | 1 | 0 | 0 |
| dsfd_rly_2_EW | rly | s81_layer:768, s81_layer1:768, s81_head:555 | 17 x 17 | 444.9 (target) / 444.9 | 660.5..758.6 | 2 | 451 | 2 | 1 | 0 |
| dsfd_rly_2_NE | rly | s81_layer:29, s81_layer1:29 | 17 x 17 | 444.9 (target) / 444.9 | 726.2..758.6 | 2 | 341 | 1 | 0 | 0 |
| dsfd_rly_2_NS | rly | s81_layer:455, s81_layer1:455, s81_head:348 | 17 x 17 | 444.9 (target) / 444.9 | 530.4..758.6 | 2 | 295 | 1 | 0 | 0 |
| dsfd_rly_2_NW | rly | s81_layer:2, s81_layer1:2 | 17 x 17 | 444.9 (target) / 444.9 | 727.9..727.9 | 2 | 451 | 2 | 1 | 0 |
| dsfd_rly_2_SE | rly | s81_layer:99, s81_layer1:99, s81_head:86 | 17 x 17 | 444.9 (target) / 444.9 | 678.7..735.1 | 2 | 105 | 1 | 0 | 0 |
| dsfd_rly_2_SN | rly | s81_layer:358, s81_layer1:358, s81_head:343 | 17 x 17 | 444.9 (target) / 444.9 | 530.4..758.6 | 2 | 397 | 1 | 0 | 0 |
| dsfd_rly_2_WE | rly | s81_layer:796, s81_layer1:796, s81_head:642 | 17 x 17 | 444.9 (target) / 444.9 | 530.4..758.6 | 2 | 215 | 1 | 0 | 0 |
| dsfd_rly_2_WS | rly | s81_layer:866, s81_layer1:866, s81_head:617 | 17 x 17 | 444.9 (target) / 444.9 | 530.4..758.6 | 2 | 417 | 1 | 0 | 0 |
| dsfd_rly_54_EW | rly | s81_layer:770, s81_layer1:770, s81_head:555 | 17 x 17 | 444.9 (target) / 444.9 | 660.5..758.6 | 2 | 285 | 1 | 0 | 0 |
| dsfd_rly_54_WN | rly | s81_layer:440, s81_layer1:440, s81_head:316 | 17 x 17 | 444.9 (target) / 444.9 | 660.5..758.6 | 2 | 276 | 1 | 0 | 0 |
| dsfd_rly_63_NE | rly | s81_layer:869, s81_layer1:869, s81_head:517 | 17 x 17 | 444.9 (target) / 444.9 | 660.5..758.6 | 2 | 774 | 2 | 1 | 0 |
| dsfd_rly_63_NS | rly | s81_layer:1419, s81_layer1:1419, s81_head:1052 | 17 x 17 | 444.9 (target) / 444.9 | 660.5..758.6 | 2 | 750 | 2 | 1 | 0 |
| dsfd_rly_63_SE | rly | s81_layer:46, s81_layer1:46, s81_head:63 | 17 x 17 | 444.9 (target) / 444.9 | 678.7..735.1 | 2 | 750 | 2 | 1 | 0 |
| dsfd_rly_63_SN | rly | s81_layer:1, s81_layer1:1 | 17 x 17 | 444.9 (target) / 444.9 | 758.6..758.6 | 2 | 864 | 2 | 1 | 0 |
| dsfd_rly_63_WE | rly | s81_layer:7933, s81_layer1:7933, s81_head:5626 | 17 x 17 | 444.9 (target) / 444.9 | 660.5..758.6 | 2 | 657 | 2 | 2 | 0 |
| dsfd_rly_63_WN | rly | s81_layer:59, s81_layer1:59, s81_head:48 | 17 x 17 | 444.9 (target) / 444.9 | 704.3..758.6 | 2 | 864 | 2 | 1 | 0 |
| dsfd_rly_63_WS | rly | s81_layer:3465, s81_layer1:3465, s81_head:2436 | 17 x 17 | 444.9 (target) / 444.9 | 660.5..758.6 | 2 | 398 | 1 | 0 | 0 |
| dsfd_rly_66_ES | rly | s81_layer:126, s81_layer1:126, s81_head:111 | 17 x 17 | 444.9 (target) / 444.9 | 660.5..758.6 | 2 | 699 | 2 | 1 | 0 |
| dsfd_rly_66_EW | rly | s81_layer:227, s81_layer1:227, s81_head:150 | 17 x 17 | 444.9 (target) / 444.9 | 660.5..758.6 | 2 | 236 | 1 | 0 | 0 |
| dsfd_rly_66_NE | rly | s81_head:68 | 17 x 17 | 444.9 (target) / 444.9 | 530.4..530.4 | 2 | 274 | 1 | 0 | 0 |
| dsfd_rly_66_NS | rly | s81_layer:896, s81_layer1:896, s81_head:738 | 17 x 17 | 444.9 (target) / 444.9 | 660.5..758.6 | 2 | 686 | 2 | 1 | 0 |
| dsfd_rly_66_NW | rly | s81_layer:29, s81_layer1:29 | 17 x 17 | 444.9 (target) / 444.9 | 735.1..758.6 | 2 | 308 | 1 | 0 | 0 |
| dsfd_rly_66_SN | rly | s81_layer:512, s81_layer1:512, s81_head:361 | 17 x 17 | 444.9 (target) / 444.9 | 660.5..758.6 | 2 | 311 | 1 | 0 | 0 |
| dsfd_rly_66_WE | rly | s81_head:17 | 17 x 17 | 444.9 (target) / 444.9 | 530.4..530.4 | 2 | 166 | 1 | 0 | 0 |
| dsfd_rly_66_WS | rly | s81_layer:2, s81_layer1:2, s81_head:85 | 17 x 17 | 444.9 (target) / 444.9 | 530.4..727.9 | 2 | 554 | 2 | 1 | 0 |
| dsfd_rstg | rstg | s81_layer:384, s81_layer1:384, s81_head:222 | 39 x 35 | 461.7 (target) / 461.7 | 643.7..741.8 | 2 | 211 | 1 | 0 | 0 |
| dsfd_selt_c | tile | s81 (in slab dsfd_bk_selector):1 | 130 x 320 | 606.1 (target) / 606.1 | 4153.7..4153.7 | 6 | 415 | 1 | 0 | 0 |
| dsfd_selt_q | tile | s81 (in slab dsfd_bk_selector):4 | 756 x 160 | 730.7 (target) / 730.7 | 4029.1..4029.1 | 5 | 349 | 1 | 0 | 0 |
| dsfd_sp_capture | hub | s81_layer:1, s81_layer1:1, s81_head:1 | 1015 x 108 | 716.4 (target) / 716.4 | 3857.3..4045.3 | 2 | 210 | 1 | 0 | 0 |
| dsfd_sp_collective | hub | s81_layer:1, s81_layer1:1, s81_head:1 | 1015 x 1369 | 900 (target) / 900 | - | 17 | 443 | 1 | 0 | 0 |
| dsfd_sp_gather | hub | s81_layer:1, s81_layer1:1, s81_head:1 | 1015 x 1369 | 900 (target) / 900 | 3839.6..3861.7 | 14 | 235 | 1 | 0 | 0 |
| dsfd_sp_hc_n | hub | s81_layer:1, s81_layer1:1, s81_head:1 | 1015 x 10837 | 900 (target) / 900 | 962.6..979.2 | 4 | 235 | 1 | 0 | 0 |
| dsfd_sp_hc_s | hub | s81_layer:1, s81_layer1:1, s81_head:1 | 1015 x 7206 | 900 (target) / 900 | 962.6..979.2 | 4 | 228 | 1 | 0 | 0 |
| dsfd_sp_su_n | hub | s81_layer:1, s81_layer1:1, s81_head:1 | 1015 x 6309 | 900 (target) / 900 | 962.6..978.5 | 2 | 201 | 1 | 0 | 0 |
| dsfd_sp_su_s | hub | s81_layer:1, s81_layer1:1, s81_head:1 | 1015 x 6307 | 900 (target) / 900 | 959.8..979.2 | 2 | 201 | 1 | 0 | 0 |
| dsfd_sp_vm | hub | s81_layer:1, s81_layer1:1, s81_head:1 | 1015 x 2620 | 900 (target) / 900 | 962.6..979.2 | 25 | 632 | 2 | 4 | 0 |
| dsfd_sstn_e0c0 | sstn | s81_layer:26, s81_layer1:26, s81_head:12 | 173 x 30 | 492.5 (target) / 492.5 | 656.7..687.5 | 9 | 312 | 1 | 0 | 0 |
| dsfd_sstn_e0c0qt | sstn | s81_layer:99, s81_layer1:99, s81_head:69 | 173 x 30 | 492.5 (target) / 492.5 | 631.1..687.5 | 10 | 413 | 1 | 0 | 0 |
| dsfd_sstn_e0c0sinf | sstn | s81_layer:29, s81_layer1:29, s81_head:25 | 173 x 30 | 492.5 (target) / 492.5 | 612.9..711.0 | 11 | 372 | 1 | 0 | 0 |
| dsfd_sstn_e0c0siqt | sstn | s81_layer:356, s81_layer1:356, s81_head:255 | 173 x 30 | 492.5 (target) / 492.5 | 612.9..711.0 | 11 | 413 | 1 | 0 | 0 |
| dsfd_sstn_e0e1c0c1 | sstn | s81_layer:1, s81_layer1:1, s81_head:30 | 173 x 30 | 492.5 (target) / 492.5 | 612.9..711.0 | 11 | 312 | 1 | 0 | 0 |
| dsfd_sstn_e0e1c0c1qt | sstn | s81_layer:2, s81_layer1:2 | 173 x 30 | 492.5 (target) / 492.5 | 680.3..680.3 | 12 | 413 | 1 | 0 | 0 |
| dsfd_sstn_e0e1c0c1si | sstn | s81_layer:358, s81_layer1:358, s81_head:233 | 173 x 30 | 492.5 (target) / 492.5 | 612.9..711.0 | 12 | 363 | 1 | 0 | 0 |
| dsfd_sstn_e0e1c0c1sinf | sstn | s81_layer:99, s81_layer1:99, s81_head:86 | 173 x 30 | 492.5 (target) / 492.5 | 631.1..687.5 | 13 | 363 | 1 | 0 | 0 |
| dsfd_sstn_e0e1c0c1siqt | sstn | s81_layer:310, s81_layer1:310, s81_head:206 | 173 x 30 | 492.5 (target) / 492.5 | 612.9..711.0 | 13 | 413 | 1 | 0 | 0 |
| dsfd_stnh_1026x1 | stn | s81_layer:76, s81_layer1:7, s81_head:78 | 17 x 56 | 456.9 (target) / 456.9 | - | 2 | 611 | 2 | 1 | 0 |
| dsfd_stnh_512x1 | stn | s81_layer:590, s81_layer1:581, s81_head:583 | 17 x 30 | 449.8 (target) / 449.8 | - | 2 | 980 | 3 | 2 | 0 |
| dsfd_stnh_514x1 | stn | s81_layer:246, s81_layer1:38, s81_head:244 | 17 x 30 | 449.8 (target) / 449.8 | - | 2 | 553 | 2 | 1 | 0 |
| dsfd_stnh_566x1 | stn | s81_layer:385, s81_layer1:386, s81_head:386 | 17 x 32 | 450.4 (target) / 450.4 | - | 2 | 424 | 1 | 0 | 0 |
| dsfd_stnh_70x1 | stn | s81_layer:24, s81_layer1:24, s81_head:24 | 17 x 67 | 459.4 (target) / 459.4 | - | 2 | 479 | 1 | 0 | 0 |
| dsfd_stnh_70x10 | stn | s81_layer:45, s81_layer1:46, s81_head:46 | 17 x 67 | 459.4 (target) / 459.4 | - | 20 | 445 | 1 | 0 | 0 |
| dsfd_stnh_70x11 | stn | s81_layer:38, s81_layer1:40, s81_head:40 | 17 x 73 | 460.8 (target) / 460.8 | - | 22 | 467 | 1 | 0 | 0 |
| dsfd_stnh_70x2 | stn | s81_layer:36, s81_layer1:36, s81_head:36 | 17 x 67 | 459.4 (target) / 459.4 | - | 4 | 412 | 1 | 0 | 0 |
| dsfd_stnh_70x3 | stn | s81_layer:36, s81_layer1:36, s81_head:36 | 17 x 67 | 459.4 (target) / 459.4 | - | 6 | 412 | 1 | 0 | 0 |
| dsfd_stnh_70x4 | stn | s81_layer:36, s81_layer1:36, s81_head:36 | 17 x 67 | 459.4 (target) / 459.4 | - | 8 | 412 | 1 | 0 | 0 |
| dsfd_stnh_70x5 | stn | s81_layer:36, s81_layer1:36, s81_head:36 | 17 x 67 | 459.4 (target) / 459.4 | - | 10 | 412 | 1 | 0 | 0 |
| dsfd_stnh_70x6 | stn | s81_layer:36, s81_layer1:36, s81_head:36 | 17 x 67 | 459.4 (target) / 459.4 | - | 12 | 412 | 1 | 0 | 0 |
| dsfd_stnh_70x7 | stn | s81_layer:36, s81_layer1:36, s81_head:36 | 17 x 67 | 459.4 (target) / 459.4 | - | 14 | 412 | 1 | 0 | 0 |
| dsfd_stnh_70x8 | stn | s81_layer:36, s81_layer1:36, s81_head:36 | 17 x 67 | 459.4 (target) / 459.4 | - | 16 | 412 | 1 | 0 | 0 |
| dsfd_stnh_70x9 | stn | s81_layer:36, s81_layer1:36, s81_head:36 | 17 x 67 | 459.4 (target) / 459.4 | - | 18 | 412 | 1 | 0 | 0 |
| dsfd_stnv_1026x1 | stn | s81_layer:86, s81_layer1:21, s81_head:85 | 55 x 17 | 456.6 (target) / 456.6 | - | 2 | 608 | 2 | 1 | 0 |
| dsfd_stnv_512x1 | stn | s81_layer:238, s81_layer1:177, s81_head:175 | 29 x 17 | 449.5 (target) / 449.5 | - | 2 | 419 | 1 | 0 | 0 |
| dsfd_stnv_514x1 | stn | s81_layer:352, s81_layer1:121, s81_head:351 | 30 x 17 | 449.8 (target) / 449.8 | - | 2 | 555 | 2 | 1 | 0 |
| dsfd_stnv_566x1 | stn | s81_layer:92, s81_layer1:87, s81_head:87 | 32 x 17 | 450.4 (target) / 450.4 | - | 2 | 424 | 1 | 0 | 0 |
| dsfd_stnv_70x10 | stn | s81_layer:73, s81_layer1:71, s81_head:71 | 67 x 17 | 459.4 (target) / 459.4 | - | 20 | 883 | 2 | 10 | 0 |
| dsfd_stnv_70x11 | stn | s81_layer:60, s81_layer1:59, s81_head:59 | 73 x 17 | 460.8 (target) / 460.8 | - | 22 | 558 | 2 | 11 | 0 |
| dsfd_svc | svc | s81_layer:4, s81_layer1:1, s81_head:4 | 8500 x 1577 | 900 (target) / 900 | 3839.0..3861.8 | 5 | 611 | 2 | 3 | 0 |
| dsfd_svc_io | tile | s81 (in slab dsfd_svc):1 | 1080 x 130 | 753.6 (target) / 753.6 | 4008.2..4008.2 | 21 | 611 | 2 | 7 | 0 |
| dsfd_svc_pc | tile | s81 (in slab dsfd_svc):32 | 121 x 43 | 492.6 (target) / 492.6 | 4269.2..4269.2 | 14 | 0 | 1 | 0 | 0 |
| dsfd_svc_stn | tile | s81 (in slab dsfd_svc):30 | 43 x 216 | 513.6 (target) / 513.6 | 4248.2..4248.2 | 14 | 430 | 1 | 0 | 0 |
| dsfd_vm_bg | tile | s81 (in slab dsfd_sp_vm):4 | 1015 x 500 | 900 (target) / 900 | 979.2..979.2 | 18 | 0 | 1 | 0 | 0 |
| hfd_attn_tile | attn_tile | hbm:64 | 1349 x 1350 | 900 (target) / 900 | 2691.4..3116.8 | 8 | 4525 | 11 | 0 | 0 |
| hfd_barrier | spine | hbm:1 | 1400 x 37 | 626 (target) / 626 | 2965.5..2965.5 | 2 | 108 | 1 | 0 | 0 |
| hfd_cdist_r14 | waypoint | hbm:4 | 111 x 216 | 563.9 (target) / 563.9 | 3027.0..3030.8 | 6 | 3724 | 9 | 0 | 0 |
| hfd_cdist_r15 | waypoint | hbm:4 | 68 x 203 | 531.5 (target) / 531.5 | 3059.9..3063.2 | 5 | 3964 | 10 | 0 | 0 |
| hfd_cmdproc | spine | hbm:1 | 1400 x 1404 | 900 (target) / 900 | 2691.5..2691.5 | 14 | 3782 | 6 | 0 | 0 |
| hfd_coll | spine | hbm:1 | 1400 x 1404 | 900 (target) / 900 | - | 19 | 2092 | 4 | 0 | 0 |
| hfd_gath_r10 | waypoint | hbm:2 | 167 x 315 | 628.3 (target) / 628.3 | 2963.1..2963.1 | 5 | 2434 | 6 | 0 | 0 |
| hfd_gath_r24 | waypoint | hbm:2 | 110 x 110 | 525.1 (target) / 525.1 | 3065.8..3065.9 | 4 | 2462 | 6 | 0 | 0 |
| hfd_gath_r25 | waypoint | hbm:2 | 167 x 315 | 628.3 (target) / 628.3 | 2963.1..2965.0 | 5 | 2654 | 6 | 0 | 0 |
| hfd_gath_r8 | waypoint | hbm:8 | 81 x 82 | 500.6 (target) / 500.6 | 3090.3..3094.1 | 3 | 2406 | 6 | 0 | 0 |
| hfd_gath_r9 | waypoint | hbm:2 | 110 x 110 | 525.1 (target) / 525.1 | 3069.6..3069.6 | 4 | 2436 | 6 | 0 | 0 |
| hfd_hc | hub | hbm:4 | 276 x 5530 | 900 (target) / 900 | 853.0..856.6 | 2 | 542 | 1 | 0 | 0 |
| hfd_host_slab | host_slab | hbm:1 | 594 x 16824 | 900 (target) / 900 | - | 0 | 0 | 0 | 0 | 0 |
| hfd_index_q_b0 | hub | hbm:4 | 930 x 970 | 1186 (measured) / 1254 | 2827.7..2830.8 | 4 | 4530 | 11 | 0 | 0 |
| hfd_index_q_b1 | hub | hbm:4 | 930 x 970 | 1132 (measured) / 1154 | 2881.7..2884.8 | 4 | 2 | 1 | 0 | 0 |
| hfd_index_q_b2 | hub | hbm:4 | 930 x 960 | 1309 (measured) / 1402 | 2704.7..2707.8 | 7 | 2056 | 5 | 0 | 0 |
| hfd_index_q_b3 | hub | hbm:4 | 930 x 970 | 1185 (measured) / 1298 | 2828.7..2831.8 | 6 | 348 | 1 | 0 | 0 |
| hfd_index_q_b4 | hub | hbm:4 | 930 x 830 | 900 (target) / 900 | 3113.7..3116.8 | 4 | 2 | 1 | 0 | 0 |
| hfd_index_q_b5 | hub | hbm:4 | 930 x 829 | 1324 (measured) / 1354 | 2689.7..2692.8 | 4 | 4525 | 11 | 0 | 0 |
| hfd_loader | spine | hbm:1 | 1400 x 238 | 900 (target) / 900 | 2691.5..2691.5 | 2 | 1608 | 4 | 0 | 0 |
| hfd_mcast_r5 | waypoint | hbm:4 | 242 x 410 | 702.5 (target) / 702.5 | 2888.4..2888.9 | 4 | 2108 | 5 | 0 | 0 |
| hfd_mcast_r6 | waypoint | hbm:8 | 467 x 121 | 635.6 (target) / 635.6 | 2955.3..2959.1 | 4 | 2108 | 5 | 0 | 0 |
| hfd_mcast_r7 | waypoint | hbm:4 | 467 x 121 | 635.6 (target) / 635.6 | 2955.8..2959.1 | 3 | 1995 | 5 | 0 | 0 |
| hfd_meso_r1 | waypoint | hbm:16 | 398 x 71 | 575.7 (target) / 575.7 | 3015.2..3019.0 | 2 | 1493 | 4 | 0 | 0 |
| hfd_meso_r28 | waypoint | hbm:9 | 63 x 190 | 525 (target) / 525 | 1656.1..1659.5 | 2 | 1614 | 4 | 0 | 0 |
| hfd_meso_r32 | waypoint | hbm:1 | 39 x 285 | 521.5 (target) / 521.5 | 1661.5..1661.5 | 2 | 1547 | 4 | 0 | 0 |
| hfd_meso_r35 | waypoint | hbm:4 | 39 x 285 | 521.5 (target) / 521.5 | 3069.6..3069.6 | 2 | 1625 | 4 | 0 | 0 |
| hfd_meso_r37 | waypoint | hbm:1 | 270 x 41 | 521 (target) / 521 | 3070.5..3070.5 | 2 | 1534 | 4 | 0 | 0 |
| hfd_quant | spine | hbm:1 | 1400 x 359 | 900 (target) / 900 | 856.6..856.6 | 5 | 4775 | 8 | 0 | 0 |
| hfd_router | spine | hbm:1 | 1400 x 326 | 900 (target) / 900 | 2691.5..2691.5 | 10 | 6724 | 11 | 0 | 0 |
| hfd_serdes_slab | serdes_slab | hbm:2 | 2462 x 3657 | 900 (target) / 900 | - | 0 | 0 | 0 | 0 | 0 |
| hfd_sfu | hub | hbm:4 | 399 x 5530 | 900 (target) / 900 | 853.0..856.6 | 4 | 542 | 1 | 0 | 0 |
| hfd_sm | sm | hbm:32 | 2203 x 2074 | 900 (target) / 900 | 2690.9..2694.7 | 5 | 3615 | 9 | 0 | 0 |
| hfd_stn_r0 | waypoint | hbm:16 | 70 x 60 | 486.4 (target) / 486.4 | - | 2 | 1701 | 4 | 0 | 0 |
| hfd_stn_r11 | waypoint | hbm:12 | 49 x 127 | 498.2 (target) / 498.2 | - | 2 | 1685 | 4 | 0 | 0 |
| hfd_stn_r12 | waypoint | hbm:12 | 56 x 65 | 482 (target) / 482 | - | 2 | 1666 | 4 | 0 | 0 |
| hfd_stn_r13 | waypoint | hbm:12 | 64 x 56 | 482 (target) / 482 | - | 2 | 1666 | 4 | 0 | 0 |
| hfd_stn_r16 | waypoint | hbm:24 | 19 x 119 | 471.1 (target) / 471.1 | - | 2 | 2050 | 5 | 0 | 0 |
| hfd_stn_r17 | waypoint | hbm:12 | 116 x 19 | 471 (target) / 471 | - | 2 | 1610 | 4 | 0 | 0 |
| hfd_stn_r18 | waypoint | hbm:8 | 67 x 60 | 485 (target) / 485 | - | 2 | 1672 | 4 | 0 | 0 |
| hfd_stn_r19 | waypoint | hbm:4 | 60 x 67 | 484.8 (target) / 484.8 | - | 2 | 1672 | 4 | 0 | 0 |
| hfd_stn_r2 | waypoint | hbm:16 | 15 x 143 | 469.5 (target) / 469.5 | 3121.4..3125.2 | 2 | 1894 | 5 | 0 | 0 |
| hfd_stn_r20 | waypoint | hbm:8 | 66 x 60 | 484.7 (target) / 484.7 | - | 2 | 1953 | 4 | 0 | 0 |
| hfd_stn_r21 | waypoint | hbm:8 | 60 x 67 | 484.6 (target) / 484.6 | - | 2 | 1671 | 4 | 0 | 0 |
| hfd_stn_r22 | waypoint | hbm:16 | 43 x 73 | 478.5 (target) / 478.5 | - | 2 | 1703 | 4 | 0 | 0 |
| hfd_stn_r23 | waypoint | hbm:8 | 73 x 43 | 478.4 (target) / 478.4 | - | 2 | 1657 | 4 | 0 | 0 |
| hfd_stn_r26 | waypoint | hbm:2 | 126 x 50 | 498.5 (target) / 498.5 | - | 2 | 2478 | 6 | 0 | 0 |
| hfd_stn_r27 | waypoint | hbm:27 | 63 x 63 | 484.5 (target) / 484.5 | - | 2 | 1698 | 4 | 0 | 0 |
| hfd_stn_r29 | waypoint | hbm:2 | 60 x 65 | 484.1 (target) / 484.1 | - | 2 | 1669 | 4 | 0 | 0 |
| hfd_stn_r3 | waypoint | hbm:16 | 15 x 143 | 469.5 (target) / 469.5 | - | 2 | 1579 | 4 | 0 | 0 |
| hfd_stn_r30 | waypoint | hbm:4 | 39 x 78 | 477.8 (target) / 477.8 | - | 2 | 1659 | 4 | 0 | 0 |
| hfd_stn_r31 | waypoint | hbm:6 | 73 x 41 | 477.3 (target) / 477.3 | - | 2 | 1657 | 4 | 0 | 0 |
| hfd_stn_r33 | waypoint | hbm:5 | 39 x 78 | 477.8 (target) / 477.8 | 3113.3..3539.0 | 2 | 2119 | 5 | 0 | 0 |
| hfd_stn_r34 | waypoint | hbm:4 | 73 x 41 | 477.3 (target) / 477.3 | - | 2 | 1648 | 4 | 0 | 0 |
| hfd_stn_r36 | waypoint | hbm:1 | 39 x 78 | 477.8 (target) / 477.8 | - | 2 | 1653 | 4 | 0 | 0 |
| hfd_stn_r4 | waypoint | hbm:20 | 121 x 52 | 498.5 (target) / 498.5 | - | 2 | 2141 | 5 | 0 | 0 |
| hfd_su | hub | hbm:4 | 703 x 5530 | 900 (target) / 900 | 853.0..856.6 | 15 | 6724 | 17 | 0 | 0 |
| hfd_su_full | spine | hbm:1 | 346 x 348 | 730 (target) / 730 | 1023.0..1023.0 | 0 | 0 | 0 | 0 | 0 |
| hfd_su_red | spine | hbm:1 | 1400 x 218 | 900 (target) / 900 | 856.6..856.6 | 0 | 0 | 0 | 0 | 0 |
| hfd_svc_SE_s0 | svc | hbm:2 | 1017 x 259 | 1057 (measured) / 874.1 OVER | 2233.5..2233.5 | 7 | 2467 | 4 | 0 | 0 |
| hfd_svc_SE_s1 | svc | hbm:2 | 1301 x 259 | 879 (measured) / 900 | 2411.5..2411.5 | 7 | 1701 | 3 | 0 | 0 |
| hfd_svc_SE_s2 | svc | hbm:2 | 1062 x 259 | 758 (measured) / 883.8 | 2532.5..2532.5 | 7 | 177 | 1 | 0 | 0 |
| hfd_svc_SE_s3 | svc | hbm:2 | 1382 x 259 | 950 (measured) / 900 | 2340.5..2340.5 | 10 | 2050 | 4 | 0 | 0 |
| hfd_svc_SE_s4 | svc | hbm:2 | 1009 x 259 | 808 (measured) / 872.3 | 2254.5..2254.5 | 7 | 175 | 1 | 0 | 0 |
| hfd_svc_SE_s5 | svc | hbm:2 | 1095 x 259 | 829 (measured) / 890.8 | 2233.5..2233.5 | 7 | 1699 | 3 | 0 | 0 |
| hfd_svc_SE_s6 | svc | hbm:2 | 764 x 259 | 562 (measured) / 814.9 | 2500.5..2500.5 | 5 | 9 | 1 | 0 | 0 |
| hfd_svc_SE_s7 | svc | hbm:2 | 870 x 259 | 631 (measured) / 840.8 | 2431.5..2431.5 | 5 | 175 | 1 | 0 | 0 |
| hfd_svc_SW_s0 | svc | hbm:2 | 1017 x 259 | 874.1 (target) / 874.1 | 2259.4..2259.4 | 7 | 2466 | 4 | 0 | 0 |
| hfd_svc_SW_s1 | svc | hbm:2 | 1306 x 259 | 900 (target) / 900 | 2233.5..2233.5 | 9 | 1952 | 3 | 0 | 0 |
| hfd_svc_SW_s2 | svc | hbm:2 | 1057 x 259 | 882.7 (target) / 882.7 | 2250.8..2250.8 | 7 | 344 | 1 | 0 | 0 |
| hfd_svc_SW_s3 | svc | hbm:2 | 1073 x 259 | 886.1 (target) / 886.1 | 2247.4..2247.4 | 8 | 1700 | 3 | 0 | 0 |
| hfd_svc_SW_s4 | svc | hbm:2 | 786 x 259 | 820.4 (target) / 820.4 | 2312.5..2312.5 | 5 | 9 | 1 | 0 | 0 |
| hfd_svc_SW_s5 | svc | hbm:2 | 1063 x 259 | 884 (target) / 884 | 2248.9..2248.9 | 7 | 344 | 1 | 0 | 0 |
| hfd_svc_SW_s6 | svc | hbm:2 | 1062 x 259 | 883.8 (target) / 883.8 | 2249.1..2249.1 | 7 | 1700 | 3 | 0 | 0 |
| hfd_svc_SW_s7 | svc | hbm:2 | 1136 x 259 | 899.4 (target) / 899.4 | 2233.5..2233.5 | 5 | 346 | 1 | 0 | 0 |
| hfd_vm | spine | hbm:1 | 1400 x 2000 | 900 (target) / 900 | 2691.1..2691.1 | 22 | 3303 | 6 | 0 | 0 |
| ot_dsrom_head_elem_A | hb_elem | s81_head:340 | 275 x 275 | 668.1 (target) / 668.1 | 307.2..307.2 | 10 | 1133 | 3 | 10 | 0 |
| ot_dsrom_head_elem_B | hb_elem | s81_head:85 | 269 x 269 | 662.6 (target) / 662.6 | 312.7..312.7 | 6 | 755 | 2 | 1 | 0 |
| ot_hbm3e_phy_v41x_aw30_e8p5 | phy | s81_layer:4, s81_layer1:1, s81_head:4, hbm:4 | 8500 x 1177 | 900 (target) / 900 | - | 14 | 9 | 1 | 0 | 0 |
| ot_hbm_host_phy | link | hbm:1 | 261 x 1652 | 900 (target) / 900 | 1283.0..1283.0 | 1 | 174 | 1 | 0 | 0 |
| ot_pdie_serdes | link | s81_layer:6, s81_layer1:6, s81_head:6, hbm:9 | 250 x 2250 | 900 (target) / 900 | 1281.1..1284.5 | 3 | 1084 | 3 | 2 | 0 |
| ot_pdie_ucie | link | s81_layer:2, s81_layer1:2, s81_head:2 | 261 x 1652 | 900 (target) / 900 | - | 2 | 830 | 3 | 2 | 0 |
| ot_rom_4096x72_m8 | cfg | s81_layer:14350, s81_layer1:14350, s81_head:10297 | 38 x 63 | 472.3 (target) / 472.3 | 633.1..731.2 | 3 | 333 | 1 | 0 | 0 |
| ot_s81_cfg7_seq | seq | s81_layer:2050, s81_layer1:2050, s81_head:1471 | 35 x 60 | 469.5 (target) / 469.5 | 635.9..734.0 | 19 | 333 | 1 | 0 | 0 |
| ot_s81ph_root_blk | tile | s81 (in slab dsfd_sp_gather):128 | 238 x 238 | 635.5 (target) / 635.5 | 4126.2..4126.2 | 3 | 0 | 1 | 0 | 0 |
| ot_s81ph_root_tile | tile | s81 (in slab dsfd_sp_gather):128 | 237 x 124 | 578.5 (target) / 578.5 | 4183.2..4183.2 | 12 | 1 | 1 | 0 | 0 |
| ot_v41_rom_elem_q_qx_w10 | q | s81_layer:1610, s81_layer1:1610, s81_head:1155 | 511 x 177 | 650 (measured) / 690.2 | 455.4..553.5 | 7 | 15 | 1 | 0 | 0 |

## Interfaces infeasible as planned (need an architecture / stage change)

| master | port | dir | bits | L um | skew class | stages needed | internal ps as planned | worst instance |
|---|---|---|---:|---:|---|---:|---:|---|
| dsfd_rly_1_WN | o | output | 1 | 1133 | intra | 3 | -653 | s81_head:y_hgo_4_0_2<->g4_0a0 |
| ot_dsrom_head_elem_A | go | input | 1 | 1133 | intra | 3 | -712 | s81_head:g4_0a0<->y_hgo_4_0_2 |
| dsfd_stnh_512x1 | di0 | input | 512 | 980 | fwd-unlinked | 3 | -574 | s81_layer:f_KE1r_1<->lk_E1 |
| ot_pdie_serdes | rx | output | 512 | 980 | fwd-unlinked | 3 | -514 | s81_layer:lk_E1<->f_KE1r_1 |
| ot_pdie_ucie | rx | output | 512 | 830 | fwd-unlinked | 3 | -345 | s81_layer:lk_E0<->f_KE0r_1 |
| dsfd_stnh_512x1 | do0 | output | 512 | 903 | fwd | 2 | -338 | s81_layer1:f_KW2t_39<->lk_W2 |
| ot_pdie_serdes | tx | input | 512 | 903 | fwd | 2 | -397 | s81_layer1:lk_W2<->f_KW2t_39 |
| dsfd_m2l_vr_68x10__hr_E0 | di0 | input | 70 | 883 | fwd | 2 | -374 | s81_layer:hr_E0<->f_rE0_54 |
| dsfd_stnv_70x10 | do0 | output | 70 | 883 | fwd | 2 | -315 | s81_layer:f_rE0_54<->hr_E0 |
| dsfd_m2l_vr_68x10__hr_E0 | di1 | input | 70 | 875 | fwd | 2 | -365 | s81_layer:hr_E0<->f_rE0_54 |
| dsfd_stnv_70x10 | do1 | output | 70 | 875 | fwd | 2 | -306 | s81_layer:f_rE0_54<->hr_E0 |
| dsfd_m2l_vr_68x10__hr_E0 | di2 | input | 70 | 868 | fwd | 2 | -357 | s81_layer:hr_E0<->f_rE0_54 |
| dsfd_stnv_70x10 | do2 | output | 70 | 868 | fwd | 2 | -298 | s81_layer:f_rE0_54<->hr_E0 |
| dsfd_rly_63_SN | i | input | 63 | 864 | intra | 2 | -416 | s81_layer:y_rt_108_28b_2<->y_rt_108_28b_1 |
| dsfd_rly_63_WN | o | output | 63 | 864 | intra | 2 | -357 | s81_layer:y_rt_108_28b_1<->y_rt_108_28b_2 |
| dsfd_m2l_vr_68x10__hr_E0 | di3 | input | 70 | 861 | fwd | 2 | -348 | s81_layer:hr_E0<->f_rE0_54 |
| dsfd_stnv_70x10 | do3 | output | 70 | 861 | fwd | 2 | -289 | s81_layer:f_rE0_54<->hr_E0 |
| dsfd_m2l_vr_68x10__hr_E0 | di4 | input | 70 | 853 | fwd | 2 | -340 | s81_layer:hr_E0<->f_rE0_54 |
| dsfd_stnv_70x10 | do4 | output | 70 | 853 | fwd | 2 | -281 | s81_layer:f_rE0_54<->hr_E0 |
| dsfd_m2l_vr_68x10__hr_E0 | di5 | input | 70 | 846 | fwd | 2 | -332 | s81_layer:hr_E0<->f_rE0_54 |
| dsfd_stnv_70x10 | do5 | output | 70 | 846 | fwd | 2 | -273 | s81_layer:f_rE0_54<->hr_E0 |
| dsfd_m2l_vr_68x10__hr_E0 | di6 | input | 70 | 838 | fwd | 2 | -323 | s81_layer:hr_E0<->f_rE0_54 |
| dsfd_stnv_70x10 | do6 | output | 70 | 838 | fwd | 2 | -264 | s81_layer:f_rE0_54<->hr_E0 |
| dsfd_m2l_vr_68x10__hr_E0 | di7 | input | 70 | 831 | fwd | 2 | -315 | s81_layer:hr_E0<->f_rE0_54 |
| dsfd_stnv_70x10 | do7 | output | 70 | 831 | fwd | 2 | -256 | s81_layer:f_rE0_54<->hr_E0 |
| dsfd_m2l_vr_68x10__hr_E0 | di8 | input | 70 | 824 | fwd | 2 | -306 | s81_layer:hr_E0<->f_rE0_54 |
| dsfd_stnv_70x10 | do8 | output | 70 | 824 | fwd | 2 | -248 | s81_layer:f_rE0_54<->hr_E0 |
| dsfd_m2l_vr_68x10__hr_E0 | di9 | input | 70 | 816 | fwd | 2 | -298 | s81_layer:hr_E0<->f_rE0_54 |
| dsfd_stnv_70x10 | do9 | output | 70 | 816 | fwd | 2 | -239 | s81_layer:f_rE0_54<->hr_E0 |
| dsfd_qbank_N | d_r1 | output | 63 | 774 | intra | 2 | -254 | s81_layer:bn1743<->y_rt_108_28b_0 |
| dsfd_rly_63_NE | i | input | 63 | 774 | intra | 2 | -313 | s81_layer:y_rt_108_28b_0<->bn1743 |
| ot_dsrom_head_elem_B | go | input | 1 | 755 | intra | 2 | -284 | s81_head:g4_1b<->y_hgo_4_1_2 |
| dsfd_rly_63_NS | o | output | 63 | 750 | intra | 2 | -226 | s81_layer:y_rt_3_0b_0<->y_rt_3_0b_1 |
| dsfd_rly_63_SE | i | input | 63 | 750 | intra | 2 | -285 | s81_layer:y_rt_3_0b_1<->y_rt_3_0b_0 |
| dsfd_hbglue | xsa | output | 256 | 744 | intra | 2 | -212 | s81_head:g49_0<->g49_0a0 |
| ot_dsrom_head_elem_A | x | input | 256 | 744 | intra | 2 | -271 | s81_head:g49_0a0<->g49_0 |
| dsfd_qbank_N | i_x1 | input | 266 | 742 | intra | 2 | -275 | s81_layer:bn2048<->y_xb_127_10_1 |
| dsfd_rly_266_WN | o | output | 266 | 742 | intra | 2 | -216 | s81_layer:y_xb_127_10_1<->bn2048 |
| ot_pdie_ucie | tx | input | 512 | 727 | fwd | 2 | -197 | s81_layer1:lk_E0<->f_KE0t_50 |
| dsfd_cfifo | ri | input | 66 | 699 | root | 2 | -228 | s81_layer:cf51<->y_rr_51_3_2 |
| dsfd_rly_66_ES | o | output | 66 | 699 | root | 2 | -169 | s81_layer:y_rr_51_3_2<->cf51 |
| dsfd_rly_66_NS | o | output | 66 | 686 | root | 2 | -152 | s81_head:y_rr_8_2_2<->cf8 |
| dsfd_rly_63_WE | i | input | 63 | 657 | intra | 2 | -179 | s81_layer:y_rt_63_26b_2<->y_rt_63_26b_1 |
| dsfd_rly_63_WE | o | output | 63 | 657 | intra | 2 | -120 | s81_layer:y_rt_63_26b_1<->y_rt_63_26b_2 |
| dsfd_m2l_vr_68x10__hr_E5 | di0 | input | 70 | 643 | fwd | 2 | -102 | s81_layer1:hr_E5<->f_rE5_52 |
| dsfd_m2l_vr_68x10__hr_E5 | di1 | input | 70 | 636 | fwd | 2 | -93 | s81_layer1:hr_E5<->f_rE5_52 |
| dsfd_r2l_vr_512x1__hsel | o | output | 515 | 632 | xdomain | 2 | 98 | s81_head:hsel<->sp_vm |
| dsfd_sp_vm | sel | input | 515 | 632 | xdomain | 2 | -239 | s81_head:sp_vm<->hsel |
| dsfd_r2l_vr_512x1__hcol | o | output | 515 | 630 | xdomain | 2 | 100 | s81_head:hcol<->sp_vm |
| dsfd_sp_vm | col | input | 515 | 630 | xdomain | 2 | -236 | s81_head:sp_vm<->hcol |
| dsfd_m2l_vr_68x10__hr_E5 | di2 | input | 70 | 628 | fwd | 2 | -85 | s81_layer1:hr_E5<->f_rE5_52 |
| dsfd_m2l_vr_68x10__hr_E5 | di3 | input | 70 | 621 | fwd | 2 | -76 | s81_layer1:hr_E5<->f_rE5_52 |
| dsfd_m2l_vr_68x10__hr_E5 | di4 | input | 70 | 613 | fwd | 2 | -68 | s81_layer1:hr_E5<->f_rE5_52 |
| dsfd_stnh_1026x1 | di0 | input | 1026 | 611 | fwd | 2 | -65 | s81_layer:f_aNE_1<->svc_NE |
| dsfd_svc | ad | output | 1026 | 611 | fwd | 2 | -6 | s81_layer:svc_NE<->f_aNE_1 |
| dsfd_svc_io | ad | output | 0 | 611 | fwd | 2 | -6 | IO hub <-> die (slab N-E pin group) [inherits dsfd_svc: s81_layer:svc_NE<->f_aNE_1] [inherits dsfd_svc: s81_layer:svc_NE<->f_aNE_1] [inherits dsfd_svc: s81_layer:svc_NE<->f_aNE_1] [inherits dsfd_svc: s81_layer:svc_NE<->f_aNE_1] [inherits dsfd_svc: s81_layer:svc_NE<->f_aNE_1] |
| dsfd_svc_io | af | output | 0 | 611 | fwd | 2 | -6 | IO hub <-> die (slab N-E pin group) [inherits dsfd_svc: s81_layer:svc_NE<->f_aNE_1] [inherits dsfd_svc: s81_layer:svc_NE<->f_aNE_1] [inherits dsfd_svc: s81_layer:svc_NE<->f_aNE_1] [inherits dsfd_svc: s81_layer:svc_NE<->f_aNE_1] [inherits dsfd_svc: s81_layer:svc_NE<->f_aNE_1] [inherits dsfd_svc: s81_layer:svc_NE<->f_aNE_1] |
| dsfd_svc_io | fault | output | 0 | 611 | fwd | 2 | -6 | IO hub <-> die (slab N-E pin group) [inherits dsfd_svc: s81_layer:svc_NE<->f_aNE_1] [inherits dsfd_svc: s81_layer:svc_NE<->f_aNE_1] [inherits dsfd_svc: s81_layer:svc_NE<->f_aNE_1] [inherits dsfd_svc: s81_layer:svc_NE<->f_aNE_1] [inherits dsfd_svc: s81_layer:svc_NE<->f_aNE_1] [inherits dsfd_svc: s81_layer:svc_NE<->f_aNE_1] [inherits dsfd_svc: s81_layer:svc_NE<->f_aNE_1] |
| dsfd_svc_io | od | output | 0 | 611 | fwd | 2 | -6 | IO hub <-> die (slab N-E pin group) [inherits dsfd_svc: s81_layer:svc_NE<->f_aNE_1] |
| dsfd_svc_io | of | output | 0 | 611 | fwd | 2 | -6 | IO hub <-> die (slab N-E pin group) [inherits dsfd_svc: s81_layer:svc_NE<->f_aNE_1] [inherits dsfd_svc: s81_layer:svc_NE<->f_aNE_1] |
| dsfd_svc_io | xd | output | 0 | 611 | fwd | 2 | -6 | IO hub <-> die (slab N-E pin group) [inherits dsfd_svc: s81_layer:svc_NE<->f_aNE_1] [inherits dsfd_svc: s81_layer:svc_NE<->f_aNE_1] [inherits dsfd_svc: s81_layer:svc_NE<->f_aNE_1] |
| dsfd_svc_io | xf | output | 0 | 611 | fwd | 2 | -6 | IO hub <-> die (slab N-E pin group) [inherits dsfd_svc: s81_layer:svc_NE<->f_aNE_1] [inherits dsfd_svc: s81_layer:svc_NE<->f_aNE_1] [inherits dsfd_svc: s81_layer:svc_NE<->f_aNE_1] [inherits dsfd_svc: s81_layer:svc_NE<->f_aNE_1] |
| dsfd_stnv_1026x1 | di0 | input | 1026 | 608 | fwd | 2 | -62 | s81_layer:f_aSE_1<->svc_SE |
| dsfd_m2l_vr_68x10__hr_E5 | di5 | input | 70 | 606 | fwd | 2 | -60 | s81_layer1:hr_E5<->f_rE5_52 |
| dsfd_m2l_vr_68x10__hr_E5 | di6 | input | 70 | 599 | fwd | 2 | -51 | s81_layer1:hr_E5<->f_rE5_52 |
| dsfd_m2l_vr_68x10__hr_E5 | di7 | input | 70 | 591 | fwd | 2 | -43 | s81_layer1:hr_E5<->f_rE5_52 |
| dsfd_m2l_vr_68x10__hr_E5 | di8 | input | 70 | 584 | fwd | 2 | -34 | s81_layer1:hr_E5<->f_rE5_52 |
| dsfd_m2l_vr_68x10__hr_E5 | di9 | input | 70 | 576 | fwd | 2 | -26 | s81_layer1:hr_E5<->f_rE5_52 |
| dsfd_capt_ctl | f_sb | input | 0 | 562 | intra | 2 | -78 | ctl <-> group tiles in the S channel (no station) |
| dsfd_capt_ctl | t_k | output | 0 | 562 | intra | 2 | -20 | ctl <-> group tiles in the S channel (no station) |
| dsfd_capt_grp | f_k | input | 0 | 562 | intra | 2 | -78 | ctl <-> group tiles in the S channel (no station) |
| dsfd_capt_grp | t_sb | output | 0 | 562 | intra | 2 | -20 | ctl <-> group tiles in the S channel (no station) |
| dsfd_rly_1_ES | i | input | 1 | 562 | intra | 2 | -72 | s81_layer:y_nf_58_0_2<->y_nf_58_0_1 |
| dsfd_rly_1_NW | o | output | 1 | 562 | intra | 2 | -13 | s81_layer:y_nf_58_0_1<->y_nf_58_0_2 |
| dsfd_m2l_vr_68x11__hr_E2 | di0 | input | 70 | 558 | fwd | 2 | -5 | s81_layer:hr_E2<->f_rE2_40 |
| dsfd_m2l_vr_68x11__hr_E2 | di1 | input | 70 | 558 | fwd | 2 | -5 | s81_layer:hr_E2<->f_rE2_40 |
| dsfd_m2l_vr_68x11__hr_E2 | di10 | input | 70 | 558 | fwd | 2 | -5 | s81_layer:hr_E2<->f_rE2_40 |
| dsfd_m2l_vr_68x11__hr_E2 | di2 | input | 70 | 558 | fwd | 2 | -5 | s81_layer:hr_E2<->f_rE2_40 |
| dsfd_m2l_vr_68x11__hr_E2 | di3 | input | 70 | 558 | fwd | 2 | -5 | s81_layer:hr_E2<->f_rE2_40 |
| dsfd_m2l_vr_68x11__hr_E2 | di4 | input | 70 | 558 | fwd | 2 | -5 | s81_layer:hr_E2<->f_rE2_40 |
| dsfd_m2l_vr_68x11__hr_E2 | di5 | input | 70 | 558 | fwd | 2 | -5 | s81_layer:hr_E2<->f_rE2_40 |
| dsfd_m2l_vr_68x11__hr_E2 | di6 | input | 70 | 558 | fwd | 2 | -5 | s81_layer:hr_E2<->f_rE2_40 |
| dsfd_m2l_vr_68x11__hr_E2 | di7 | input | 70 | 558 | fwd | 2 | -5 | s81_layer:hr_E2<->f_rE2_40 |
| dsfd_m2l_vr_68x11__hr_E2 | di8 | input | 70 | 558 | fwd | 2 | -5 | s81_layer:hr_E2<->f_rE2_40 |
| dsfd_m2l_vr_68x11__hr_E2 | di9 | input | 70 | 558 | fwd | 2 | -5 | s81_layer:hr_E2<->f_rE2_40 |
| dsfd_stnv_70x11 | do0 | output | 70 | 558 | fwd | 2 | 54 | s81_layer:f_rE2_40<->hr_E2 |
| dsfd_stnv_70x11 | do1 | output | 70 | 558 | fwd | 2 | 54 | s81_layer:f_rE2_40<->hr_E2 |
| dsfd_stnv_70x11 | do10 | output | 70 | 558 | fwd | 2 | 54 | s81_layer:f_rE2_40<->hr_E2 |
| dsfd_stnv_70x11 | do2 | output | 70 | 558 | fwd | 2 | 54 | s81_layer:f_rE2_40<->hr_E2 |
| dsfd_stnv_70x11 | do3 | output | 70 | 558 | fwd | 2 | 54 | s81_layer:f_rE2_40<->hr_E2 |
| dsfd_stnv_70x11 | do4 | output | 70 | 558 | fwd | 2 | 54 | s81_layer:f_rE2_40<->hr_E2 |
| dsfd_stnv_70x11 | do5 | output | 70 | 558 | fwd | 2 | 54 | s81_layer:f_rE2_40<->hr_E2 |
| dsfd_stnv_70x11 | do6 | output | 70 | 558 | fwd | 2 | 54 | s81_layer:f_rE2_40<->hr_E2 |
| dsfd_stnv_70x11 | do7 | output | 70 | 558 | fwd | 2 | 54 | s81_layer:f_rE2_40<->hr_E2 |
| dsfd_stnv_70x11 | do8 | output | 70 | 558 | fwd | 2 | 54 | s81_layer:f_rE2_40<->hr_E2 |
| dsfd_stnv_70x11 | do9 | output | 70 | 558 | fwd | 2 | 54 | s81_layer:f_rE2_40<->hr_E2 |
| dsfd_stnv_514x1 | di0 | input | 514 | 555 | fwd | 2 | -2 | s81_layer:f_ixNE_1<->svc_NE |
| dsfd_svc | xd | output | 514 | 555 | fwd | 2 | 57 | s81_layer:svc_NE<->f_ixNE_1 |
| dsfd_rly_66_WS | o | output | 66 | 554 | root | 2 | 3 | s81_head:y_hro_41_0_1<->cf41 |
| dsfd_stnh_514x1 | di0 | input | 514 | 553 | fwd | 2 | 1 | s81_layer:f_ixSE_1<->svc_SE |
| dsfd_bf | r1 | output | 63 | 533 | intra | 2 | 20 | s81_layer:e1742<->y_rt_108_26b_0 |
| dsfd_rly_266_WS | o | output | 266 | 532 | intra | 2 | 26 | s81_head:y_xb_61_8_1<->bn713 |
| dsfd_qbank_N | d_r0 | output | 63 | 519 | intra | 2 | 36 | s81_layer:bn2048<->y_rt_127_30a_0 |
| dsfd_bf | r0 | output | 63 | 509 | intra | 2 | 46 | s81_layer:e1742<->y_rt_108_26a_0 |
| dsfd_svc | od | output | 514 | 502 | fwd | 2 | 118 | s81_layer:svc_NE<->f_coNE_1 |
| dsfd_hbglue | bd | output | 32 | 496 | intra | 2 | 69 | s81_head:g109_0<->g109_0a0 |
| ot_dsrom_head_elem_A | bd | input | 32 | 496 | intra | 2 | 10 | s81_head:g109_0a0<->g109_0 |
| dsfd_rly_266_WE | o | output | 266 | 486 | intra | 2 | 73 | s81_layer:y_xb_108_10_1<->bn1743 |
| dsfd_hbglue | a3done | input | 1 | 480 | intra | 2 | 28 | s81_head:g124_0<->g124_0a3 |
| ot_dsrom_head_elem_A | done | output | 1 | 480 | intra | 2 | 87 | s81_head:g124_0a3<->g124_0 |
| dsfd_hbglue | a3flt | input | 1 | 477 | intra | 2 | 32 | s81_head:g56_0<->g56_0a3 |
| ot_dsrom_head_elem_A | flt | output | 1 | 477 | intra | 2 | 91 | s81_head:g56_0a3<->g56_0 |
| dsfd_rly_266_WS | i | input | 266 | 476 | intra | 2 | 30 | s81_head:y_xb_1_8_1<->y_xb_1_8_0 |
| dsfd_hbglue | a3brow | input | 17 | 470 | intra | 2 | 40 | s81_head:g124_0<->g124_0a3 |
| ot_dsrom_head_elem_A | brow | output | 17 | 470 | intra | 2 | 99 | s81_head:g124_0a3<->g124_0 |
| dsfd_hbglue | a3bkey | input | 32 | 470 | intra | 2 | 40 | s81_head:g124_0<->g124_0a3 |
| ot_dsrom_head_elem_A | bkey | output | 32 | 470 | intra | 2 | 99 | s81_head:g124_0a3<->g124_0 |
| dsfd_node_LLfd | a | input | 63 | 466 | intra | 2 | 38 | s81_head:n96_12<->y_rt_96_12a_4 |
| dsfd_node_LLfu | a | input | 63 | 466 | intra | 2 | 36 | s81_layer:n108_12<->y_rt_108_12a_4 |
| dsfd_hbglue | a3bbits | input | 32 | 465 | intra | 2 | 46 | s81_head:g124_0<->g124_0a3 |
| ot_dsrom_head_elem_A | bbits | output | 32 | 465 | intra | 2 | 104 | s81_head:g124_0a3<->g124_0 |
| dsfd_hbglue | r0a3 | output | 17 | 461 | intra | 2 | 110 | s81_head:g124_0<->g124_0a3 |
| ot_dsrom_head_elem_A | row0 | input | 17 | 461 | intra | 2 | 51 | s81_head:g124_0a3<->g124_0 |
| dsfd_hbglue | bv3 | output | 1 | 453 | intra | 2 | 118 | s81_head:g72_0<->g72_0a3 |
| ot_dsrom_head_elem_A | bv | input | 1 | 453 | intra | 2 | 60 | s81_head:g72_0a3<->g72_0 |
| dsfd_qbank_N | d_st | output | 2 | 451 | intra | 2 | 112 | s81_layer:bn1744<->y_es_1744_0 |
| dsfd_rly_2_EW | i | input | 2 | 451 | intra | 2 | 53 | s81_layer:y_es_1744_0<->bn1744 |
| dsfd_rly_2_NW | i | input | 2 | 451 | intra | 2 | 54 | s81_layer:y_es_1024_0<->bn1024 |
| dsfd_node_LLfu | b | input | 63 | 436 | intra | 2 | 71 | s81_layer:n127_26<->y_rt_127_26b_4 |
| dsfd_sp_vm | aSW | input | 1027 | 392 | xdomain | 2 | 34 | s81_layer1:sp_vm<->ha_SW |
| dsfd_sp_vm | aNW | input | 1027 | 390 | xdomain | 2 | 36 | s81_head:sp_vm<->ha_NW |
