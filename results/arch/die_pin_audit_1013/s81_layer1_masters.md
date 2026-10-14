# Die pin audit: s81_layer1 (contract v14, views origin/main fd5402b7a)

79 masters with a published LEF (44756 instances) of 248 (56660 instances); FIX BY VIEW 2 masters / 1663 inst, FIX BY PIN RE-PLAN 28 masters / 1316 inst, FIX AT DIE 10 masters / 23 inst, ACCEPT 38 masters / 41753 inst.

| master | inst | top layer | pins by face/layer | face pins | blocked above | own-stub OBS | open pockets | slot fit | class |
|---|---:|---|---|---:|---:|---:|---|---|---|
| dsfd_su_t_pin | 4 | M7 (PG M7) | E/M4 2376 E/M6 1728 N/M5 188 S/M5 302 W/M4 2344 W/M6 1760 | 8698 | 0 (0 %) | 0 | - | mismatch: insertion | FIX AT DIE |
| dsfd_su_t_ctl | 1 | M6 (PG M6) | E/M6 29 N/M5 105 S/M5 753 | 887 | 0 (0 %) | 0 | - | fit | ACCEPT |
| ot_s81_hc_crooty | 2 | M7 (PG M7) | E/M4 1 N/M5 4988 S/M5 4990 W/M4 2 | 9981 | 4913 (49.22 %) | 10 | M7 8268 | mismatch: outline, layer, insertion; lint (c) (e) (f) (h) | FIX BY PIN RE-PLAN |
| ot_s81_hc_crooty_w | 2 | M5 (PG M5) | E/M4 2 N/M5 2172 S/M5 2172 | 4346 | 0 (0 %) | 0 | M5 452 | mismatch: outline; lint (e) (h) | FIX AT DIE |
| ot_s81_hc_crootr_f | 2 | M5 (PG M5) | E/M4 2 N/M3 1408 N/M5 1409 S/M3 1464 S/M5 1464 W/M4 1135 | 6882 | 0 (0 %) | 0 | M5 2090 | mismatch: insertion; lint (h) | FIX AT DIE |
| ot_s81_hc_crootr_r | 2 | M5 (PG M5) | E/M4 2 N/M3 1246 N/M5 1246 S/M3 1082 S/M5 1082 W/M4 1082 | 5740 | 0 (0 %) | 0 | M5 1409 | mismatch: insertion; lint (h) | FIX AT DIE |
| ot_s81_hc_crootr_t | 2 | M5 (PG M5) | E/M4 1135 N/M5 2 S/M5 1410 W/M4 1519 | 4066 | 0 (0 %) | 0 | M5 3562 | fit; lint (h) | ACCEPT |
| ot_s81_hc_crootr_w | 2 | M5 (PG M5) | E/M4 2 N/M3 1086 N/M5 1087 S/M3 543 S/M5 543 W/M4 1087 | 4348 | 0 (0 %) | 0 | - | fit | ACCEPT |
| ot_s81_hc_cpin | 1 | M6 (PG M6) | E/M4 1 N/M5 3723 S/M5 3719 W/M4 1 | 7444 | 0 (0 %) | 0 | - | mismatch: outline; lint (e) | FIX AT DIE |
| dsfd_coll_lane_w | 8 | M5 (PG M5) | E/M4 1113 N/M5 3 W/M4 1028 | 2144 | 0 (0 %) | 0 | M5 3316 | mismatch: insertion; lint (h) | FIX AT DIE |
| dsfd_coll_cbr | 2 | M5 (PG M5) | N/M5 1113 S/M5 2 W/M4 1113 | 2228 | 0 (0 %) | 0 | M5 1076 | fit; lint (h) | ACCEPT |
| dsfd_coll_cbf | 1 | M7 (PG M7) | E/M4 14 N/M5 592 S/M5 592 W/M4 2 | 1200 | 0 (0 %) | 0 | - | fit | ACCEPT |
| dsfd_coll_cbq0 | 1 | M5 (PG M5) | E/M4 1 N/M5 422 S/M5 423 W/M4 14 | 860 | 0 (0 %) | 0 | M5 1482 | fit; lint (h) | ACCEPT |
| dsfd_coll_cbq | 4 | M7 (PG M7) | E/M4 1 N/M5 421 S/M5 423 W/M4 1 | 846 | 0 (0 %) | 0 | - | fit | ACCEPT |
| dsfd_coll_ct | 1 | M7 (PG M7) | E/M4 608 E/M6 505 N/M5 2 S/M5 2226 W/M4 729 W/M6 384 | 4454 | 0 (0 %) | 0 | - | mismatch: insertion; lint (e) | FIX AT DIE |
| dsfd_vm_be_sl | 4 | M7 (PG M7) | E/M4 1 N/M7 1297 S/M5 2604 W/M4 75 | 3977 | 1766 (44.41 %) | 15 | M7 1815 | mismatch: names, pin_layer, layer; lint (c) (e) (f) (h) | FIX BY PIN RE-PLAN |
| ot_mtp_p2_prefix_path | 1 | M7 (PG M6) | E/M4 596 N/M5 109 W/M4 1212 | 1917 | 0 (0 %) | 0 | - | mismatch: outline, layer; lint (e) | FIX AT DIE |
| ot_p2h_xport | 1 | M7 (PG M7) | E/M4 671 N/M5 109 W/M4 1210 | 1990 | 0 (0 %) | 0 | - | mismatch: outline, layer, insertion; lint (c) (e) | FIX BY PIN RE-PLAN |
| ot_p2h_head | 1 | M5 (PG M5) | E/M4 703 N/M5 1587 W/M4 776 | 3066 | 0 (0 %) | 0 | M5 4877 | mismatch: insertion; lint (h) | FIX AT DIE |
| ot_p2h_fadd16 | 1 | M7 (PG M7) | N/M5 1027 S/M5 560 | 1587 | 1034 (65.15 %) | 3 | M7 400 | mismatch: outline, layer; lint (c) (e) (f) (h) | FIX BY PIN RE-PLAN |
| dsfd_cfifo | 128 | M7 (PG M7) | N/M5 637 S/M5 638 W/M4 2 | 1277 | 1058 (82.85 %) | 5 | M7 2398 | no slot; lint (f) (h) | FIX BY PIN RE-PLAN |
| dsfd_ctrl | 1 | - | - | - | - | - | - | ERROR no LEF with MACRO dsfd_ctrl in physical/s81_ph_views/assembled/dsfd_ctrl | - |
| dsfd_l2r_vr_512x1__hq_SW | 1 | M7 (PG M7) | N/M5 516 S/M5 4 W/M4 515 | 1035 | 852 (82.32 %) | 6 | M7 121 | no slot; lint (f) (h) | FIX BY PIN RE-PLAN |
| dsfd_l2r_vr_564x1__hx_E | 1 | M7 (PG M7) | S/M5 571 W/M4 568 | 1139 | 760 (66.73 %) | 1 | M7 277 | no slot; lint (f) (h) | FIX BY PIN RE-PLAN |
| dsfd_l2r_vr_564x1__hx_W | 1 | M7 (PG M7) | E/M4 568 S/M5 4 W/M4 567 | 1139 | 697 (61.19 %) | 2 | M7 399 | no slot; lint (f) (h) | FIX BY PIN RE-PLAN |
| dsfd_m2l_raw_512x1__hl_E0 | 1 | M7 (PG M7) | E/M4 513 S/M5 2 W/M4 515 | 1030 | 648 (62.91 %) | 2 | M7 972 | no slot; lint (f) (h) | FIX BY PIN RE-PLAN |
| dsfd_m2l_raw_512x1__hl_E2 | 1 | M7 (PG M7) | E/M4 513 N/M5 515 S/M5 2 | 1030 | 382 (37.09 %) | 0 | M7 956 | no slot; lint (f) (h) | FIX BY PIN RE-PLAN |
| dsfd_m2l_raw_512x1__hl_W1 | 1 | M7 (PG M7) | E/M4 515 S/M5 515 | 1030 | 710 (68.93 %) | 0 | M7 898 | no slot; lint (f) (h) | FIX BY PIN RE-PLAN |
| dsfd_m2l_vr_512x1__hco_SW | 1 | M7 (PG M7) | S/M5 517 W/M4 515 | 1032 | 965 (93.51 %) | 0 | M7 959 | no slot; lint (f) (h) | FIX BY PIN RE-PLAN |
| dsfd_m2l_vr_512x1__hix_SW | 1 | M7 (PG M7) | N/M5 515 S/M5 2 W/M4 515 | 1032 | 1008 (97.67 %) | 1 | M7 1016 | no slot; lint (f) (h) | FIX BY PIN RE-PLAN |
| dsfd_m2l_vr_512x1__hqe_SW | 1 | M7 (PG M7) | E/M4 515 S/M5 517 | 1032 | 750 (72.67 %) | 1 | M7 996 | no slot; lint (f) (h) | FIX BY PIN RE-PLAN |
| dsfd_m2l_vr_68x10__hr_W5 | 1 | M7 (PG M7) | E/M4 976 S/M5 428 | 1404 | 904 (64.39 %) | 2 | M7 1454 | no slot; lint (f) (h) | FIX BY PIN RE-PLAN |
| dsfd_m2l_vr_68x11__hr_E3 | 1 | M7 (PG M7) | S/M5 2 W/M4 1542 | 1544 | 1434 (92.88 %) | 1 | M7 1961 | no slot; lint (f) (h) | FIX BY PIN RE-PLAN |
| dsfd_m2l_vr_68x11__hr_E4 | 1 | M7 (PG M7) | N/M5 781 S/M5 2 W/M4 761 | 1544 | 1273 (82.45 %) | 0 | M7 1375 | no slot; lint (f) (h) | FIX BY PIN RE-PLAN |
| dsfd_m2l_vr_68x11__hr_W1 | 1 | M7 (PG M7) | E/M4 761 S/M5 783 | 1544 | 987 (63.92 %) | 2 | M7 1321 | no slot; lint (f) (h) | FIX BY PIN RE-PLAN |
| dsfd_m2l_vr_68x11__hr_W2 | 1 | M7 (PG M7) | E/M4 761 S/M5 783 | 1544 | 987 (63.92 %) | 2 | M7 1321 | no slot; lint (f) (h) | FIX BY PIN RE-PLAN |
| dsfd_m2l_vr_68x11__hr_W3 | 1 | M7 (PG M7) | E/M4 761 N/M5 781 S/M5 2 | 1544 | 1328 (86.01 %) | 1 | M7 1199 | no slot; lint (f) (h) | FIX BY PIN RE-PLAN |
| dsfd_m2l_vr_68x11__hr_W4 | 1 | M7 (PG M7) | E/M4 1542 S/M5 2 | 1544 | 722 (46.76 %) | 2 | M7 1788 | no slot; lint (f) (h) | FIX BY PIN RE-PLAN |
| dsfd_r2l_vr_1024x1__ha_SW | 1 | M7 (PG M7) | N/M5 1027 S/M5 1029 | 2056 | 1021 (49.66 %) | 0 | M7 946 | no slot; lint (f) (h) | FIX BY PIN RE-PLAN |
| dsfd_r2l_vr_512x1__hcol | 1 | M7 (PG M7) | E/M4 515 S/M5 517 | 1032 | 553 (53.59 %) | 0 | M7 314 | no slot; lint (f) (h) | FIX BY PIN RE-PLAN |
| dsfd_r2l_vr_512x1__hsel | 1 | M7 (PG M7) | E/M4 515 N/M5 515 S/M5 2 | 1032 | 283 (27.42 %) | 4 | M7 320 | no slot; lint (f) (h) | FIX BY PIN RE-PLAN |
| dsfd_rly_15_EN | 234 | M5 (PG M5) | E/M4 15 N/M5 15 S/M5 2 | 32 | 0 (0 %) | 0 | M5 9 | no slot; lint (h) | ACCEPT |
| dsfd_rly_15_SN | 918 | M5 (PG M5) | E/M4 2 N/M5 15 S/M5 15 | 32 | 0 (0 %) | 0 | M5 8 | no slot; lint (h) | ACCEPT |
| dsfd_rly_1_EW | 384 | M5 (PG M5) | E/M4 1 N/M5 2 W/M4 1 | 4 | 0 (0 %) | 0 | - | no slot | ACCEPT |
| dsfd_rly_1_WE | 640 | M5 (PG M5) | E/M4 1 N/M5 2 W/M4 1 | 4 | 0 (0 %) | 0 | - | no slot | ACCEPT |
| dsfd_rly_266_SN | 640 | M5 (PG M5) | E/M4 2 N/M5 266 S/M5 266 | 534 | 0 (0 %) | 0 | M5 58 | no slot; lint (h) | ACCEPT |
| dsfd_rly_266_WE | 640 | M5 (PG M5) | E/M4 266 N/M5 2 W/M4 266 | 534 | 0 (0 %) | 0 | M5 47 | no slot; lint (h) | ACCEPT |
| dsfd_rly_283_SN | 640 | M5 (PG M5) | E/M4 2 N/M5 283 S/M5 283 | 568 | 0 (0 %) | 0 | M5 81 | no slot; lint (h) | ACCEPT |
| dsfd_rly_283_WE | 640 | M5 (PG M5) | E/M4 283 N/M5 2 W/M4 283 | 568 | 0 (0 %) | 0 | M5 41 | no slot; lint (h) | ACCEPT |
| dsfd_rly_2_ES | 640 | M5 (PG M5) | E/M4 2 N/M5 2 S/M5 2 | 6 | 0 (0 %) | 0 | - | no slot | ACCEPT |
| dsfd_rly_2_EW | 640 | M5 (PG M5) | E/M4 2 N/M5 2 W/M4 2 | 6 | 0 (0 %) | 0 | - | no slot | ACCEPT |
| dsfd_rly_2_NE | 290 | M5 (PG M5) | E/M4 2 N/M5 2 S/M5 2 | 6 | 0 (0 %) | 0 | - | no slot | ACCEPT |
| dsfd_rly_2_NS | 1118 | M5 (PG M5) | E/M4 2 N/M5 2 S/M5 2 | 6 | 0 (0 %) | 0 | - | no slot | ACCEPT |
| dsfd_rly_2_NW | 512 | M5 (PG M5) | N/M5 2 S/M5 2 W/M4 2 | 6 | 0 (0 %) | 0 | M5 1 | no slot; lint (h) | ACCEPT |
| dsfd_rly_2_SN | 512 | M5 (PG M5) | E/M4 2 N/M5 2 S/M5 2 | 6 | 0 (0 %) | 0 | - | no slot | ACCEPT |
| dsfd_rly_2_WE | 640 | M5 (PG M5) | E/M4 2 N/M5 2 W/M4 2 | 6 | 0 (0 %) | 0 | - | no slot | ACCEPT |
| dsfd_rly_2_WS | 640 | M5 (PG M5) | N/M5 2 S/M5 2 W/M4 2 | 6 | 0 (0 %) | 0 | M5 1 | no slot; lint (h) | ACCEPT |
| dsfd_rly_54_EW | 640 | M5 (PG M5) | E/M4 54 N/M5 2 W/M4 54 | 110 | 0 (0 %) | 0 | M5 9 | no slot; lint (h) | ACCEPT |
| dsfd_rly_63_ES | 128 | M5 (PG M5) | E/M4 63 N/M5 2 S/M5 63 | 128 | 0 (0 %) | 0 | M5 6 | no slot; lint (h) | ACCEPT |
| dsfd_rly_63_NE | 896 | M5 (PG M5) | E/M4 63 N/M5 63 S/M5 2 | 128 | 0 (0 %) | 0 | M5 6 | no slot; lint (h) | ACCEPT |
| dsfd_rly_63_NS | 3968 | M5 (PG M5) | E/M4 2 N/M5 63 S/M5 63 | 128 | 0 (0 %) | 0 | M5 17 | no slot; lint (h) | ACCEPT |
| dsfd_rly_63_SE | 384 | M5 (PG M5) | E/M4 63 N/M5 2 S/M5 63 | 128 | 0 (0 %) | 0 | M5 12 | no slot; lint (h) | ACCEPT |
| dsfd_rly_63_WE | 7808 | M5 (PG M5) | E/M4 63 N/M5 2 W/M4 63 | 128 | 0 (0 %) | 0 | M5 4 | no slot; lint (h) | ACCEPT |
| dsfd_rly_63_WN | 512 | M5 (PG M5) | N/M5 63 S/M5 2 W/M4 63 | 128 | 0 (0 %) | 0 | M5 5 | no slot; lint (h) | ACCEPT |
| dsfd_rly_63_WS | 3456 | M5 (PG M5) | N/M5 2 S/M5 63 W/M4 63 | 128 | 0 (0 %) | 0 | M5 12 | no slot; lint (h) | ACCEPT |
| dsfd_rly_66_NS | 896 | M5 (PG M5) | E/M4 2 N/M5 66 S/M5 66 | 134 | 0 (0 %) | 0 | M5 11 | no slot; lint (h) | ACCEPT |
| dsfd_rly_66_SN | 512 | M5 (PG M5) | E/M4 2 N/M5 66 S/M5 66 | 134 | 0 (0 %) | 0 | M5 19 | no slot; lint (h) | ACCEPT |
| dsfd_rly_68_EW | 256 | M5 (PG M5) | E/M4 68 N/M5 2 W/M4 68 | 138 | 0 (0 %) | 0 | M5 7 | no slot; lint (h) | ACCEPT |
| dsfd_stnh_512x1 | 598 | M7 (PG M7) | E/M4 513 W/M4 513 | 1026 | 352 (34.31 %) | 1 | M7 6 | no slot; lint (b) (f) (h) | FIX BY PIN RE-PLAN |
| dsfd_stnh_514x1 | 43 | M7 (PG M7) | E/M4 515 W/M4 515 | 1030 | 367 (35.63 %) | 1 | M7 8 | no slot; lint (b) (f) (h) | FIX BY PIN RE-PLAN |
| dsfd_stnh_566x1 | 391 | M7 (PG M7) | E/M4 567 W/M4 567 | 1134 | 396 (34.92 %) | 0 | M7 4 | no slot; lint (b) (f) (h) | FIX BY PIN RE-PLAN |
| dsfd_stnv_512x1 | 383 | M7 (PG M7) | N/M5 513 S/M5 513 | 1026 | 0 (0 %) | 0 | M7 17 | no slot; lint (h) | FIX BY VIEW |
| dsfd_stnv_514x1 | 129 | M7 (PG M7) | N/M5 515 S/M5 515 | 1030 | 68 (6.6 %) | 0 | M7 14 | no slot; lint (f) (h) | FIX BY PIN RE-PLAN |
| dsfd_svc_join | 1 | M7 (PG M7) | E/M4 35 N/M5 11 S/M5 2 W/M4 85 | 133 | 38 (28.57 %) | 4 | M7 266 | no slot; lint (f) (h) | FIX AT DIE |
| ot_hbm3e_phy_v41x_aw30_e8p5 | 1 | M5 (PG M4) | N/M5 22238 | 22238 | 0 (0 %) | 0 | - | no slot; lint (a) (c) | ACCEPT |
| ot_pdie_serdes | 6 | M4 (PG M4) | E/M4 1024 W/M4 1 | 1025 | 0 (0 %) | 0 | - | no slot; lint (a) | ACCEPT |
| ot_pdie_ucie | 2 | M4 (PG M4) | W/M4 1025 | 1025 | 0 (0 %) | 0 | - | no slot; lint (a) | ACCEPT |
| ot_rom_4096x72_m8 | 12547 | M4 (PG M4) | E/M4 43 W/M4 43 | 86 | 0 (0 %) | 0 | - | no slot; lint (a) | ACCEPT |
| ot_v41_rom_elem_q_qxpq_w10 | 1280 | M7 (PG M7) | N/M5 129 S/M5 610 | 739 | 0 (0 %) | 0 | M7 6682 | no slot; lint (h) | FIX BY VIEW |

## Findings per master

- **dsfd_su_t_pin** x4 (physical/ref_tile/dsfd_su_t_pin_rt/views/dsfd_su_t_pin): FIX AT DIE
  - FIX AT DIE: estimated clock insertion 497 ps (dsfd_su_t_pin_tt.lib max_clock_tree_path) vs slot target 250 ps (+-100) (die clock tap level per the clock delivery rule)
- **ot_s81_hc_crooty** x2 (physical/s81_ph_views/hc_hier/routes/s81hc-crooth-673aa90b0-tc-yw-pd40/ot_s81_hc_crooty): FIX BY PIN RE-PLAN
  - FIX BY VIEW: 10 face pins under their own stub OBS (abstract_pin_stub.py moves the stub into the PORT)
  - FIX BY VIEW: 8268 open M7 pockets on a layer the die routes on (abstract_pin_stub.py pocket fill)
  - FIX BY PIN RE-PLAN: 4913 of 9981 face pins covered by the tile's own metal on the layer above (no via access; re-route with the pin keepout hook, reroute_reason evidence_gap / slot_change)
  - FIX BY PIN RE-PLAN: child_lint (c) strap layer M7+ not clear: 16316 OBS on M7, 0 signal pins, PG on M7 (child signals must stop below the parent strap layer, or own M6 as full PG stripes and leave M7 f (the tile's own signals reach its strap layer: re-route under the cap)
  - FIX AT DIE: outline 575.992 x 200 != slot 575.992 x 300.24 (slot change request or a wrapper at the slot outline)
  - ACCEPT: routing cap M7 above the slot layer cap M6 inside a hardened cluster (the cluster's plan owns the layers)
  - FIX AT DIE: estimated clock insertion 494 ps (ot_s81_hc_crooty_tt.lib max_clock_tree_path) vs slot target 250 ps (+-100) (die clock tap level per the clock delivery rule)
- **ot_s81_hc_crooty_w** x2 (physical/ref_tile/s81hc_crywe_ref/views/ot_s81_hc_crooty_w): FIX AT DIE
  - FIX AT DIE: outline 194.4 x 300.24 != slot 195.264 x 300.24 (slot change request or a wrapper at the slot outline)
  - ACCEPT: 452 open M5 pockets: the die does not route on M5 over a tile
- **ot_s81_hc_crootr_f** x2 (physical/ref_tile/s81hc_crrfe_ref/views/ot_s81_hc_crootr_f): FIX AT DIE
  - FIX AT DIE: estimated clock insertion 384 ps (ot_s81_hc_crootr_f_tt.lib max_clock_tree_path) vs slot target 250 ps (+-100) (die clock tap level per the clock delivery rule)
  - ACCEPT: 2090 open M5 pockets: the die does not route on M5 over a tile
- **ot_s81_hc_crootr_r** x2 (physical/ref_tile/s81hc_crrre_ref/views/ot_s81_hc_crootr_r): FIX AT DIE
  - FIX AT DIE: estimated clock insertion 361 ps (ot_s81_hc_crootr_r_tt.lib max_clock_tree_path) vs slot target 250 ps (+-100) (die clock tap level per the clock delivery rule)
  - ACCEPT: 1409 open M5 pockets: the die does not route on M5 over a tile
- **ot_s81_hc_crootr_t** x2 (physical/ref_tile/s81hc_crrte_ref/views/ot_s81_hc_crootr_t): ACCEPT
  - ACCEPT: 3562 open M5 pockets: the die does not route on M5 over a tile
- **ot_s81_hc_cpin** x1 (physical/ref_tile/s81hc_cpin_ref/views/ot_s81_hc_cpin): FIX AT DIE
  - FIX AT DIE: outline 576.72 x 200.88 != slot 575.992 x 200 (slot change request or a wrapper at the slot outline)
- **dsfd_coll_lane_w** x8 (physical/ref_tile/dscoll_lane_w_cxea/views/dsfd_coll_lane_w): FIX AT DIE
  - FIX AT DIE: estimated clock insertion 540 ps (dsfd_coll_lane_w_tt.lib max_clock_tree_path) vs slot target 250 ps (+-100) (die clock tap level per the clock delivery rule)
  - ACCEPT: 3316 open M5 pockets: the die does not route on M5 over a tile
- **dsfd_coll_cbr** x2 (physical/ref_tile/dsfd_coll_cbr_m5/views/dsfd_coll_cbr): ACCEPT
  - ACCEPT: 1076 open M5 pockets: the die does not route on M5 over a tile
- **dsfd_coll_cbq0** x1 (physical/ref_tile/dsfd_coll_cbq0_m5/views/dsfd_coll_cbq0): ACCEPT
  - ACCEPT: 1482 open M5 pockets: the die does not route on M5 over a tile
- **dsfd_coll_ct** x1 (physical/ref_tile/dsfd_coll_ct_rt/views/dsfd_coll_ct): FIX AT DIE
  - FIX AT DIE: estimated clock insertion 699 ps (dsfd_coll_ct_tt.lib max_clock_tree_path) vs slot target 250 ps (+-100) (die clock tap level per the clock delivery rule)
- **dsfd_vm_be_sl** x4 (physical/s81_ph_views/vm_master/views/dsfd_vm_be_sl): FIX BY PIN RE-PLAN
  - FIX BY VIEW: 15 face pins under their own stub OBS (abstract_pin_stub.py moves the stub into the PORT)
  - FIX BY VIEW: 1815 open M7 pockets on a layer the die routes on (abstract_pin_stub.py pocket fill)
  - FIX BY PIN RE-PLAN: 1766 of 3977 face pins covered by the tile's own metal on the layer above (no via access; re-route with the pin keepout hook, reroute_reason evidence_gap / slot_change)
  - FIX BY PIN RE-PLAN: child_lint (c) strap layer M7+ not clear: 3488 OBS on M7, 1297 signal pins, PG on M7 (child signals must stop below the parent strap layer, or own M6 as full PG stripes and leave M7 (the tile's own signals reach its strap layer: re-route under the cap)
  - FIX BY PIN RE-PLAN: child_lint (c) 1297 signal pins above the cap M6 (e.g. o_d[0]) (the tile's own signals reach its strap layer: re-route under the cap)
  - FIX BY PIN RE-PLAN: pins on another face / layer than the slot: N-face pins may land on M7 (slot M3/M5)
  - FIX AT DIE: contract / generator pin names differ from the view: 13 slot pins not in the pin plan (e.g. f_m5s, f_mx, f_v5, f_vx); 4 planned ports the slot does not have (e.g. pm, sflt, sst, xc)
  - ACCEPT: routing cap M7 above the slot layer cap M6 inside a hardened cluster (the cluster's plan owns the layers)
- **ot_mtp_p2_prefix_path** x1 (results/rtl/mtp_p2_rootpipe_20261010/routes/mtp-p2-path-rb4v-a978bdba9-tc-hm20): FIX AT DIE
  - FIX AT DIE: outline 560 x 460 != slot 878.4 x 270 (slot change request or a wrapper at the slot outline)
  - ACCEPT: routing cap M7 above the slot layer cap M6 (closed tile stands; die tracks it blocks: see the legacy-layer table; re-route only under a hot window, reroute_reason die_window)
- **ot_p2h_xport** x1 (physical/s81_ph_views/closed/ot_p2h_xport): FIX BY PIN RE-PLAN
  - FIX BY PIN RE-PLAN: child_lint (c) strap layer M7+ not clear: 7043 OBS on M7, 0 signal pins, PG on M7 (child signals must stop below the parent strap layer, or own M6 as full PG stripes and leave M7 fr (the tile's own signals reach its strap layer: re-route under the cap)
  - FIX AT DIE: outline 403.2 x 211.68 != slot 403.2 x 228.96 (slot change request or a wrapper at the slot outline)
  - ACCEPT: routing cap M7 above the slot layer cap M6 inside a hardened cluster (the cluster's plan owns the layers)
  - FIX AT DIE: estimated clock insertion 439 ps (ot_p2h_xport_tt.lib max_clock_tree_path) vs slot target 250 ps (+-100) (die clock tap level per the clock delivery rule)
- **ot_p2h_head** x1 (physical/ref_tile/p2h_head_ref/views/ot_p2h_head): FIX AT DIE
  - FIX AT DIE: estimated clock insertion 584 ps (ot_p2h_head_tt.lib max_clock_tree_path) vs slot target 250 ps (+-100) (die clock tap level per the clock delivery rule)
  - ACCEPT: 4877 open M5 pockets: the die does not route on M5 over a tile
- **ot_p2h_fadd16** x1 (physical/s81_ph_views/closed/ot_p2h_fadd16): FIX BY PIN RE-PLAN
  - FIX BY VIEW: 3 face pins under their own stub OBS (abstract_pin_stub.py moves the stub into the PORT)
  - FIX BY VIEW: 400 open M7 pockets on a layer the die routes on (abstract_pin_stub.py pocket fill)
  - FIX BY PIN RE-PLAN: 1034 of 1587 face pins covered by the tile's own metal on the layer above (no via access; re-route with the pin keepout hook, reroute_reason evidence_gap / slot_change)
  - FIX BY PIN RE-PLAN: child_lint (c) strap layer M7+ not clear: 1103 OBS on M7, 0 signal pins, PG on M7 (child signals must stop below the parent strap layer, or own M6 as full PG stripes and leave M7 fr (the tile's own signals reach its strap layer: re-route under the cap)
  - FIX AT DIE: outline 216 x 58.32 != slot 150 x 66.15 (slot change request or a wrapper at the slot outline)
  - ACCEPT: routing cap M7 above the slot layer cap M6 inside a hardened cluster (the cluster's plan owns the layers)
- **dsfd_cfifo** x128 (physical/s81_die_views/views_colck/dsfd_cfifo): FIX BY PIN RE-PLAN
  - FIX BY VIEW: 5 face pins under their own stub OBS (abstract_pin_stub.py moves the stub into the PORT)
  - FIX BY VIEW: 2398 open M7 pockets on a layer the die routes on (abstract_pin_stub.py pocket fill)
  - FIX BY PIN RE-PLAN: 1058 of 1277 face pins covered by the tile's own metal on the layer above (no via access; re-route with the pin keepout hook, reroute_reason evidence_gap / slot_change)
- **dsfd_l2r_vr_512x1__hq_SW** x1 (physical/s81_die_views/views/m221pq/dsfd_l2r_vr_512x1__hq_SW): FIX BY PIN RE-PLAN
  - FIX BY VIEW: 6 face pins under their own stub OBS (abstract_pin_stub.py moves the stub into the PORT)
  - FIX BY VIEW: 121 open M7 pockets on a layer the die routes on (abstract_pin_stub.py pocket fill)
  - FIX BY PIN RE-PLAN: 852 of 1035 face pins covered by the tile's own metal on the layer above (no via access; re-route with the pin keepout hook, reroute_reason evidence_gap / slot_change)
- **dsfd_l2r_vr_564x1__hx_E** x1 (physical/s81_die_views/views/m221pq/dsfd_l2r_vr_564x1__hx_E): FIX BY PIN RE-PLAN
  - FIX BY VIEW: 1 face pins under their own stub OBS (abstract_pin_stub.py moves the stub into the PORT)
  - FIX BY VIEW: 277 open M7 pockets on a layer the die routes on (abstract_pin_stub.py pocket fill)
  - FIX BY PIN RE-PLAN: 760 of 1139 face pins covered by the tile's own metal on the layer above (no via access; re-route with the pin keepout hook, reroute_reason evidence_gap / slot_change)
- **dsfd_l2r_vr_564x1__hx_W** x1 (physical/s81_die_views/views/m221pq/dsfd_l2r_vr_564x1__hx_W): FIX BY PIN RE-PLAN
  - FIX BY VIEW: 2 face pins under their own stub OBS (abstract_pin_stub.py moves the stub into the PORT)
  - FIX BY VIEW: 399 open M7 pockets on a layer the die routes on (abstract_pin_stub.py pocket fill)
  - FIX BY PIN RE-PLAN: 697 of 1139 face pins covered by the tile's own metal on the layer above (no via access; re-route with the pin keepout hook, reroute_reason evidence_gap / slot_change)
- **dsfd_m2l_raw_512x1__hl_E0** x1 (physical/s81_die_views/views/m221pq/dsfd_m2l_raw_512x1__hl_E0): FIX BY PIN RE-PLAN
  - FIX BY VIEW: 2 face pins under their own stub OBS (abstract_pin_stub.py moves the stub into the PORT)
  - FIX BY VIEW: 972 open M7 pockets on a layer the die routes on (abstract_pin_stub.py pocket fill)
  - FIX BY PIN RE-PLAN: 648 of 1030 face pins covered by the tile's own metal on the layer above (no via access; re-route with the pin keepout hook, reroute_reason evidence_gap / slot_change)
- **dsfd_m2l_raw_512x1__hl_E2** x1 (physical/s81_die_views/views/m221pq/dsfd_m2l_raw_512x1__hl_E2): FIX BY PIN RE-PLAN
  - FIX BY VIEW: 956 open M7 pockets on a layer the die routes on (abstract_pin_stub.py pocket fill)
  - FIX BY PIN RE-PLAN: 382 of 1030 face pins covered by the tile's own metal on the layer above (no via access; re-route with the pin keepout hook, reroute_reason evidence_gap / slot_change)
- **dsfd_m2l_raw_512x1__hl_W1** x1 (physical/s81_die_views/views/m221pq/dsfd_m2l_raw_512x1__hl_W1): FIX BY PIN RE-PLAN
  - FIX BY VIEW: 898 open M7 pockets on a layer the die routes on (abstract_pin_stub.py pocket fill)
  - FIX BY PIN RE-PLAN: 710 of 1030 face pins covered by the tile's own metal on the layer above (no via access; re-route with the pin keepout hook, reroute_reason evidence_gap / slot_change)
- **dsfd_m2l_vr_512x1__hco_SW** x1 (physical/s81_die_views/views/m221pq/dsfd_m2l_vr_512x1__hco_SW): FIX BY PIN RE-PLAN
  - FIX BY VIEW: 959 open M7 pockets on a layer the die routes on (abstract_pin_stub.py pocket fill)
  - FIX BY PIN RE-PLAN: 965 of 1032 face pins covered by the tile's own metal on the layer above (no via access; re-route with the pin keepout hook, reroute_reason evidence_gap / slot_change)
- **dsfd_m2l_vr_512x1__hix_SW** x1 (physical/s81_die_views/views/m221pq/dsfd_m2l_vr_512x1__hix_SW): FIX BY PIN RE-PLAN
  - FIX BY VIEW: 1 face pins under their own stub OBS (abstract_pin_stub.py moves the stub into the PORT)
  - FIX BY VIEW: 1016 open M7 pockets on a layer the die routes on (abstract_pin_stub.py pocket fill)
  - FIX BY PIN RE-PLAN: 1008 of 1032 face pins covered by the tile's own metal on the layer above (no via access; re-route with the pin keepout hook, reroute_reason evidence_gap / slot_change)
- **dsfd_m2l_vr_512x1__hqe_SW** x1 (physical/s81_die_views/views/m221pq/dsfd_m2l_vr_512x1__hqe_SW): FIX BY PIN RE-PLAN
  - FIX BY VIEW: 1 face pins under their own stub OBS (abstract_pin_stub.py moves the stub into the PORT)
  - FIX BY VIEW: 996 open M7 pockets on a layer the die routes on (abstract_pin_stub.py pocket fill)
  - FIX BY PIN RE-PLAN: 750 of 1032 face pins covered by the tile's own metal on the layer above (no via access; re-route with the pin keepout hook, reroute_reason evidence_gap / slot_change)
- **dsfd_m2l_vr_68x10__hr_W5** x1 (physical/s81_die_views/views/m221pq/dsfd_m2l_vr_68x10__hr_W5): FIX BY PIN RE-PLAN
  - FIX BY VIEW: 2 face pins under their own stub OBS (abstract_pin_stub.py moves the stub into the PORT)
  - FIX BY VIEW: 1454 open M7 pockets on a layer the die routes on (abstract_pin_stub.py pocket fill)
  - FIX BY PIN RE-PLAN: 904 of 1404 face pins covered by the tile's own metal on the layer above (no via access; re-route with the pin keepout hook, reroute_reason evidence_gap / slot_change)
- **dsfd_m2l_vr_68x11__hr_E3** x1 (physical/s81_die_views/views/m221pq/dsfd_m2l_vr_68x11__hr_E3): FIX BY PIN RE-PLAN
  - FIX BY VIEW: 1 face pins under their own stub OBS (abstract_pin_stub.py moves the stub into the PORT)
  - FIX BY VIEW: 1961 open M7 pockets on a layer the die routes on (abstract_pin_stub.py pocket fill)
  - FIX BY PIN RE-PLAN: 1434 of 1544 face pins covered by the tile's own metal on the layer above (no via access; re-route with the pin keepout hook, reroute_reason evidence_gap / slot_change)
- **dsfd_m2l_vr_68x11__hr_E4** x1 (physical/variant_fill/s81-hend-m221pq-hr-E4-a1f23fa0b-mm-vf-hm25/dsfd_m2l_vr_68x11__hr_E4): FIX BY PIN RE-PLAN
  - FIX BY VIEW: 1375 open M7 pockets on a layer the die routes on (abstract_pin_stub.py pocket fill)
  - FIX BY PIN RE-PLAN: 1273 of 1544 face pins covered by the tile's own metal on the layer above (no via access; re-route with the pin keepout hook, reroute_reason evidence_gap / slot_change)
- **dsfd_m2l_vr_68x11__hr_W1** x1 (physical/variant_fill/s81-hend-m221pq-hr-W1-a1f23fa0b-mm-vf-hm25/dsfd_m2l_vr_68x11__hr_W1): FIX BY PIN RE-PLAN
  - FIX BY VIEW: 2 face pins under their own stub OBS (abstract_pin_stub.py moves the stub into the PORT)
  - FIX BY VIEW: 1321 open M7 pockets on a layer the die routes on (abstract_pin_stub.py pocket fill)
  - FIX BY PIN RE-PLAN: 987 of 1544 face pins covered by the tile's own metal on the layer above (no via access; re-route with the pin keepout hook, reroute_reason evidence_gap / slot_change)
- **dsfd_m2l_vr_68x11__hr_W2** x1 (physical/variant_fill/s81-hend-m221pq-hr-W2-a1f23fa0b-mm-vf-hm25/dsfd_m2l_vr_68x11__hr_W2): FIX BY PIN RE-PLAN
  - FIX BY VIEW: 2 face pins under their own stub OBS (abstract_pin_stub.py moves the stub into the PORT)
  - FIX BY VIEW: 1321 open M7 pockets on a layer the die routes on (abstract_pin_stub.py pocket fill)
  - FIX BY PIN RE-PLAN: 987 of 1544 face pins covered by the tile's own metal on the layer above (no via access; re-route with the pin keepout hook, reroute_reason evidence_gap / slot_change)
- **dsfd_m2l_vr_68x11__hr_W3** x1 (physical/variant_fill/s81-hend-m221pq-hr-W3-a1f23fa0b-mm-vf-hm25/dsfd_m2l_vr_68x11__hr_W3): FIX BY PIN RE-PLAN
  - FIX BY VIEW: 1 face pins under their own stub OBS (abstract_pin_stub.py moves the stub into the PORT)
  - FIX BY VIEW: 1199 open M7 pockets on a layer the die routes on (abstract_pin_stub.py pocket fill)
  - FIX BY PIN RE-PLAN: 1328 of 1544 face pins covered by the tile's own metal on the layer above (no via access; re-route with the pin keepout hook, reroute_reason evidence_gap / slot_change)
- **dsfd_m2l_vr_68x11__hr_W4** x1 (physical/variant_fill/s81-hend-m221pq-hr-W4-a1f23fa0b-mm-vf-hm25/dsfd_m2l_vr_68x11__hr_W4): FIX BY PIN RE-PLAN
  - FIX BY VIEW: 2 face pins under their own stub OBS (abstract_pin_stub.py moves the stub into the PORT)
  - FIX BY VIEW: 1788 open M7 pockets on a layer the die routes on (abstract_pin_stub.py pocket fill)
  - FIX BY PIN RE-PLAN: 722 of 1544 face pins covered by the tile's own metal on the layer above (no via access; re-route with the pin keepout hook, reroute_reason evidence_gap / slot_change)
- **dsfd_r2l_vr_1024x1__ha_SW** x1 (physical/s81_die_views/views/m221pq/dsfd_r2l_vr_1024x1__ha_SW): FIX BY PIN RE-PLAN
  - FIX BY VIEW: 946 open M7 pockets on a layer the die routes on (abstract_pin_stub.py pocket fill)
  - FIX BY PIN RE-PLAN: 1021 of 2056 face pins covered by the tile's own metal on the layer above (no via access; re-route with the pin keepout hook, reroute_reason evidence_gap / slot_change)
- **dsfd_r2l_vr_512x1__hcol** x1 (physical/s81_die_views/views/m221pq/dsfd_r2l_vr_512x1__hcol): FIX BY PIN RE-PLAN
  - FIX BY VIEW: 314 open M7 pockets on a layer the die routes on (abstract_pin_stub.py pocket fill)
  - FIX BY PIN RE-PLAN: 553 of 1032 face pins covered by the tile's own metal on the layer above (no via access; re-route with the pin keepout hook, reroute_reason evidence_gap / slot_change)
- **dsfd_r2l_vr_512x1__hsel** x1 (physical/s81_die_views/views/m221pq/dsfd_r2l_vr_512x1__hsel): FIX BY PIN RE-PLAN
  - FIX BY VIEW: 4 face pins under their own stub OBS (abstract_pin_stub.py moves the stub into the PORT)
  - FIX BY VIEW: 320 open M7 pockets on a layer the die routes on (abstract_pin_stub.py pocket fill)
  - FIX BY PIN RE-PLAN: 283 of 1032 face pins covered by the tile's own metal on the layer above (no via access; re-route with the pin keepout hook, reroute_reason evidence_gap / slot_change)
- **dsfd_rly_15_EN** x234 (physical/ref_tile/s81_rly_15_en/views/dsfd_rly_15_EN): ACCEPT
  - ACCEPT: 9 open M5 pockets: the die does not route on M5 over a tile
- **dsfd_rly_15_SN** x918 (physical/ref_tile/s81_rly_15_sn/views/dsfd_rly_15_SN): ACCEPT
  - ACCEPT: 8 open M5 pockets: the die does not route on M5 over a tile
- **dsfd_rly_266_SN** x640 (physical/ref_tile/s81_rly_266_sn/views/dsfd_rly_266_SN): ACCEPT
  - ACCEPT: 58 open M5 pockets: the die does not route on M5 over a tile
- **dsfd_rly_266_WE** x640 (physical/ref_tile/s81_rly_266_we/views/dsfd_rly_266_WE): ACCEPT
  - ACCEPT: 47 open M5 pockets: the die does not route on M5 over a tile
- **dsfd_rly_283_SN** x640 (physical/ref_tile/s81_rly_283_sn/views/dsfd_rly_283_SN): ACCEPT
  - ACCEPT: 81 open M5 pockets: the die does not route on M5 over a tile
- **dsfd_rly_283_WE** x640 (physical/ref_tile/s81_rly_283_we/views/dsfd_rly_283_WE): ACCEPT
  - ACCEPT: 41 open M5 pockets: the die does not route on M5 over a tile
- **dsfd_rly_2_NW** x512 (physical/ref_tile/s81_rly_2_nw/views/dsfd_rly_2_NW): ACCEPT
  - ACCEPT: 1 open M5 pockets: the die does not route on M5 over a tile
- **dsfd_rly_2_WS** x640 (physical/ref_tile/s81_rly_2_ws/views/dsfd_rly_2_WS): ACCEPT
  - ACCEPT: 1 open M5 pockets: the die does not route on M5 over a tile
- **dsfd_rly_54_EW** x640 (physical/ref_tile/s81_rly_54_ew/views/dsfd_rly_54_EW): ACCEPT
  - ACCEPT: 9 open M5 pockets: the die does not route on M5 over a tile
- **dsfd_rly_63_ES** x128 (physical/ref_tile/s81_rly_63_es/views/dsfd_rly_63_ES): ACCEPT
  - ACCEPT: 6 open M5 pockets: the die does not route on M5 over a tile
- **dsfd_rly_63_NE** x896 (physical/ref_tile/s81_rly_63_ne/views/dsfd_rly_63_NE): ACCEPT
  - ACCEPT: 6 open M5 pockets: the die does not route on M5 over a tile
- **dsfd_rly_63_NS** x3968 (physical/ref_tile/s81_rly_63_ns/views/dsfd_rly_63_NS): ACCEPT
  - ACCEPT: 17 open M5 pockets: the die does not route on M5 over a tile
- **dsfd_rly_63_SE** x384 (physical/ref_tile/s81_rly_63_se/views/dsfd_rly_63_SE): ACCEPT
  - ACCEPT: 12 open M5 pockets: the die does not route on M5 over a tile
- **dsfd_rly_63_WE** x7808 (physical/ref_tile/s81_rly_63_we/views/dsfd_rly_63_WE): ACCEPT
  - ACCEPT: 4 open M5 pockets: the die does not route on M5 over a tile
- **dsfd_rly_63_WN** x512 (physical/ref_tile/s81_rly_63_wn/views/dsfd_rly_63_WN): ACCEPT
  - ACCEPT: 5 open M5 pockets: the die does not route on M5 over a tile
- **dsfd_rly_63_WS** x3456 (physical/ref_tile/s81_rly_63_ws/views/dsfd_rly_63_WS): ACCEPT
  - ACCEPT: 12 open M5 pockets: the die does not route on M5 over a tile
- **dsfd_rly_66_NS** x896 (physical/ref_tile/s81_rly_66_ns/views/dsfd_rly_66_NS): ACCEPT
  - ACCEPT: 11 open M5 pockets: the die does not route on M5 over a tile
- **dsfd_rly_66_SN** x512 (physical/ref_tile/s81_rly_66_sn/views/dsfd_rly_66_SN): ACCEPT
  - ACCEPT: 19 open M5 pockets: the die does not route on M5 over a tile
- **dsfd_rly_68_EW** x256 (physical/ref_tile/s81_rly_68_ew/views/dsfd_rly_68_EW): ACCEPT
  - ACCEPT: 7 open M5 pockets: the die does not route on M5 over a tile
- **dsfd_stnh_512x1** x598 (physical/s81_die_views/views/dsfd_stnh_512x1): FIX BY PIN RE-PLAN
  - FIX BY VIEW: 1 face pins under their own stub OBS (abstract_pin_stub.py moves the stub into the PORT)
  - FIX BY VIEW: 6 open M7 pockets on a layer the die routes on (abstract_pin_stub.py pocket fill)
  - FIX BY PIN RE-PLAN: 352 of 1026 face pins covered by the tile's own metal on the layer above (no via access; re-route with the pin keepout hook, reroute_reason evidence_gap / slot_change)
  - FIX BY PIN RE-PLAN: child_lint (b) pg: VDD: 1 full-length stripes on M7 (< 2)
- **dsfd_stnh_514x1** x43 (physical/s81_die_views/views/dsfd_stnh_514x1): FIX BY PIN RE-PLAN
  - FIX BY VIEW: 1 face pins under their own stub OBS (abstract_pin_stub.py moves the stub into the PORT)
  - FIX BY VIEW: 8 open M7 pockets on a layer the die routes on (abstract_pin_stub.py pocket fill)
  - FIX BY PIN RE-PLAN: 367 of 1030 face pins covered by the tile's own metal on the layer above (no via access; re-route with the pin keepout hook, reroute_reason evidence_gap / slot_change)
  - FIX BY PIN RE-PLAN: child_lint (b) pg: VDD: 1 full-length stripes on M7 (< 2)
- **dsfd_stnh_566x1** x391 (physical/s81_die_views/views/dsfd_stnh_566x1): FIX BY PIN RE-PLAN
  - FIX BY VIEW: 4 open M7 pockets on a layer the die routes on (abstract_pin_stub.py pocket fill)
  - FIX BY PIN RE-PLAN: 396 of 1134 face pins covered by the tile's own metal on the layer above (no via access; re-route with the pin keepout hook, reroute_reason evidence_gap / slot_change)
  - FIX BY PIN RE-PLAN: child_lint (b) pg: VDD: 1 full-length stripes on M7 (< 2)
- **dsfd_stnv_512x1** x383 (physical/s81_die_views/views/dsfd_stnv_512x1): FIX BY VIEW
  - FIX BY VIEW: 17 open M7 pockets on a layer the die routes on (abstract_pin_stub.py pocket fill)
- **dsfd_stnv_514x1** x129 (physical/s81_die_views/views/dsfd_stnv_514x1): FIX BY PIN RE-PLAN
  - FIX BY VIEW: 14 open M7 pockets on a layer the die routes on (abstract_pin_stub.py pocket fill)
  - FIX BY PIN RE-PLAN: 68 of 1030 face pins covered by the tile's own metal on the layer above (no via access; re-route with the pin keepout hook, reroute_reason evidence_gap / slot_change)
- **dsfd_svc_join** x1 (physical/s81_ph_views/closed/dsfd_svc_join): FIX AT DIE
  - FIX AT DIE: a better published view of this master exists: bind physical/ref_tile/s81_svcjoin_ref/views/dsfd_svc_join (ACCEPT; top M5, blocked above 0, pockets 279) instead of physical/s81_ph_views/closed/dsfd_svc_join
  - FIX BY VIEW: 4 face pins under their own stub OBS (abstract_pin_stub.py moves the stub into the PORT)
  - FIX BY VIEW: 266 open M7 pockets on a layer the die routes on (abstract_pin_stub.py pocket fill)
  - FIX BY PIN RE-PLAN: 38 of 133 face pins covered by the tile's own metal on the layer above (no via access; re-route with the pin keepout hook, reroute_reason evidence_gap / slot_change)
- **ot_hbm3e_phy_v41x_aw30_e8p5** x1 (physical/asap7_memory_macros/ot_hbm3e_phy_v41x_aw30_e8p5): ACCEPT
  - hard-IP abstract (memory / PHY macro): not judged by the routed-tile lint; pins are the macro's own
- **ot_pdie_serdes** x6 (physical/asap7_v41x_pdie_macros/ot_pdie_serdes): ACCEPT
  - hard-IP abstract (memory / PHY macro): not judged by the routed-tile lint; pins are the macro's own
- **ot_pdie_ucie** x2 (physical/asap7_v41x_pdie_macros/ot_pdie_ucie): ACCEPT
  - hard-IP abstract (memory / PHY macro): not judged by the routed-tile lint; pins are the macro's own
- **ot_rom_4096x72_m8** x12547 (physical/asap7_memory_macros/ot_rom_4096x72_m8): ACCEPT
  - hard-IP abstract (memory / PHY macro): not judged by the routed-tile lint; pins are the macro's own
- **ot_v41_rom_elem_q_qxpq_w10** x1280 (physical/s81_die_views/q_elem_qs5f_efs): FIX BY VIEW
  - FIX BY VIEW: 6682 open M7 pockets on a layer the die routes on (abstract_pin_stub.py pocket fill)

## Masters without a published LEF (not auditable)

dsfd_sp_su_c x1, dsfd_su_t_qn0 x1, dsfd_su_t_qn1 x1, dsfd_su_t_kv0 x1, dsfd_su_t_kv1 x1, dsfd_su_t_qb x4, dsfd_su_t_sw x8, ot_s81_su_sm x8, dsfd_sp_hc_c x1, dsfd_sp_hc_t x1, ot_s81_hc_crooty_y x2, ot_s81_hc_crootr x2, ot_s81_hc_comb x1, ot_s81_hc_cth x64, dsfd_sp_collective_c x1, dsfd_sp_vm x1, dsfd_sp_capture_c x1, dsfd_sp_gather_c x1, dsfd_wfc_stg x1, ot_v41_rom_elem_q_* x1, dsfd_bf x1, dsfd_sp_pq / pqc tiles x1, dsfd_mtp_hrow banks x1, engram_c tiles x1, dsfd_vm_bgq28 x16, dsfd_bk_collector_c x1, dsfd_bk_selector_c x1, dsfd_host_s x1, dsfd_hstnh_1 x39, dsfd_hstnh_1024 x86, dsfd_hstnh_1027 x1, dsfd_hstnh_11 x6, dsfd_hstnh_112 x9, dsfd_hstnh_128 x9, dsfd_hstnh_130 x13, dsfd_hstnh_192 x4, dsfd_hstnh_2 x53, dsfd_hstnh_2100 x7, dsfd_hstnh_2162 x4, dsfd_hstnh_28 x9, dsfd_hstnh_3 x9, dsfd_hstnh_36 x10, dsfd_hstnh_4096 x13, dsfd_hstnh_508 x4, dsfd_hstnh_512 x1, dsfd_hstnh_513 x1, dsfd_hstnh_514 x22, dsfd_hstnh_515 x3, dsfd_hstnh_516 x4, dsfd_hstnh_53 x9, dsfd_hstnh_54 x9, dsfd_hstnh_544 x4, dsfd_hstnh_592 x7, dsfd_hstnh_6 x12, dsfd_hstnh_692 x13, dsfd_hstnh_761 x27, dsfd_hstnh_8 x20, dsfd_hstnh_85 x44, dsfd_hstnh_9 x31, dsfd_hstnv_1 x5, dsfd_hstnv_1024 x42, dsfd_hstnv_1090 x24, dsfd_hstnv_11 x1, dsfd_hstnv_112 x1, dsfd_hstnv_1264 x25, dsfd_hstnv_130 x1, dsfd_hstnv_192 x1, dsfd_hstnv_2 x30, dsfd_hstnv_2100 x15, dsfd_hstnv_2162 x8, dsfd_hstnv_3 x12, dsfd_hstnv_36 x15, dsfd_hstnv_4096 x32, dsfd_hstnv_508 x1, dsfd_hstnv_512 x2, dsfd_hstnv_514 x5, dsfd_hstnv_515 x5, dsfd_hstnv_516 x4, dsfd_hstnv_53 x1, dsfd_hstnv_54 x1, dsfd_hstnv_544 x4, dsfd_hstnv_592 x12, dsfd_hstnv_6 x14, dsfd_hstnv_692 x1, dsfd_hstnv_8 x15, dsfd_hstnv_85 x32, dsfd_hstnv_9 x32, dsfd_l2r_vr_1x1__hs_s4_svcj x1, dsfd_l2r_vr_1x1__hs_s5_bk_selector x1, dsfd_l2r_vr_1x1__hs_s6_bk_collector x1, dsfd_l2r_vr_291x1__hs_hwSW x1, dsfd_l2r_vr_84x1__hs_c4_svcj x1, dsfd_l2r_vr_84x1__hs_c5_bk_selector x1, dsfd_l2r_vr_84x1__hs_c6_bk_collector x1, dsfd_l2r_vr_8x1__hs_d4_svcj x1, dsfd_l2r_vr_8x1__hs_d5_bk_selector x1, dsfd_l2r_vr_8x1__hs_d6_bk_collector x1, dsfd_l2r_vr_8x1__hs_hcSW x1, dsfd_lkck_NE x1, dsfd_lkck_NW x1, dsfd_lkck_SE x3, dsfd_lkck_SW x3, dsfd_m2l_raw_512x1__hl_E1 x1, dsfd_m2l_raw_512x1__hl_E3 x1, dsfd_m2l_raw_512x1__hl_W0 x1, dsfd_m2l_raw_512x1__hl_W2 x1, dsfd_m2l_raw_512x1__hl_W3 x1, dsfd_m2l_vr_1x1__he_s4_svcj x1, dsfd_m2l_vr_1x1__he_s5_bk_selector x1, dsfd_m2l_vr_1x1__he_s6_bk_collector x1, dsfd_m2l_vr_291x1__he_hwSW x1, dsfd_m2l_vr_68x10__hr_E0 x1, dsfd_m2l_vr_68x10__hr_E5 x1, dsfd_m2l_vr_68x10__hr_W0 x1, dsfd_m2l_vr_68x11__hr_E1 x1, dsfd_m2l_vr_68x11__hr_E2 x1, dsfd_m2l_vr_84x1__he_c4_svcj x1, dsfd_m2l_vr_84x1__he_c5_bk_selector x1, dsfd_m2l_vr_84x1__he_c6_bk_collector x1, dsfd_m2l_vr_8x1__he_d4_svcj x1, dsfd_m2l_vr_8x1__he_d5_bk_selector x1, dsfd_m2l_vr_8x1__he_d6_bk_collector x1, dsfd_m2l_vr_8x1__he_hcSW x1, dsfd_node_LLd x128, dsfd_node_LLfd x896, dsfd_node_LLfu x768, dsfd_node_NNfd x768, dsfd_node_NNfu x896, dsfd_pq_root x128, dsfd_qbank_N x1280, dsfd_qbank_S x1280, dsfd_rstg x256, dsfd_rstg_pq66 x128, dsfd_rstg_pq68 x128, dsfd_sp_pq x1, dsfd_sstn_e0c0si x384, dsfd_sstn_e0c0sinf x128, dsfd_sstn_e0e1c0c1_cp1t0 x128, dsfd_sstn_e0e1c0c1si x512, dsfd_stage_seq_c x1, dsfd_stnh_1026x1 x7, dsfd_stnh_10x1 x41, dsfd_stnh_293x1 x11, dsfd_stnh_3x1 x29, dsfd_stnh_70x1 x57, dsfd_stnh_70x10 x53, dsfd_stnh_70x11 x48, dsfd_stnh_70x2 x36, dsfd_stnh_70x3 x36, dsfd_stnh_70x4 x36, dsfd_stnh_70x5 x36, dsfd_stnh_70x6 x36, dsfd_stnh_70x7 x36, dsfd_stnh_70x8 x36, dsfd_stnh_70x9 x36, dsfd_stnh_86x1 x25, dsfd_stnv_1026x1 x26, dsfd_stnv_10x1 x130, dsfd_stnv_256x1 x24, dsfd_stnv_293x1 x43, dsfd_stnv_3x1 x88, dsfd_stnv_566x1 x126, dsfd_stnv_70x1 x16, dsfd_stnv_70x10 x93, dsfd_stnv_70x11 x116, dsfd_stnv_86x1 x89, dsfd_svc_c x1, dsfd_xstg_515 x2, ot_s81_cfg7_seq x1792

