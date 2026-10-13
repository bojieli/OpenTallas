# Die timing by construction: pin-register audit, ranked (PROVISIONAL)

> **TILE VERDICTS SUPERSEDED (10-13 09:10, el1013-pinreg-audit.log):** `out_over` / `in_over` here judge each side against 0.2 T = 166.7 ps, which is the share the sign-off SDC gives the OUTSIDE, not the tile. The die statement is the pair equation with insertion-compensated clock entry: see `qwen_rom_tp8_compensated.md`, `s81_compensated.md`, `ranked_compensated.md`. The hop tables (> 500 um) and the min-delay / combinational columns stand.

Rule (owner 2026-10-13): register at the pin -> wire <= 500 um -> register at the pin, IO 0.2 T of 833.333 ps (166.7 ps a side). Tool: `tools/hier_contract/pinreg_audit.py`. Every view audited here was exported before the export-SDC fix (main abc334b14), so each number may move by tens of ps: re-run once the views are re-exported.

| die | contract | cells | audited | violating | not auditable (cells / inst) | hops > 500 um (data + reset) | max um |
|---|---|---:|---:|---:|---|---|---:|
| qwen_rom_tp8 | v3 | 44 | 13 | 13 | 31 / 1065 | 265 + 13 | 31115.7 |
| qwen_rom | v6 | 36 | 10 | 10 | 26 / 1571 | 1 + 0 | 500.3 |
| ds_rom_s81_layer1 | v13 | 72 | 44 | 43 | 28 / 128 | 1 + 0 | 503.3 |

| # | die | cell | inst | flags | clk->pin worst ps (bits over) | pin->flop worst ps (bits over) | L-H ps | corner | binding | owner log |
|---|---|---|---:|---|---|---|---:|---|---|---|
| 1 | ds_rom_s81_layer1 | dsfd_m2l_vr_68x11__hr_E3 | 1 | out_over in_over min_delay | 693.5 (758) | 618.9 (124) | 97.1 | ss | census (closed timing, generated_placeholder) | el1011-s81die.log |
| 2 | ds_rom_s81_layer1 | dsfd_m2l_vr_68x11__hr_W4 | 1 | out_over in_over min_delay | 649.3 (755) | 595.8 (74) | 87.7 | ss | census (closed timing, generated_placeholder) | el1011-s81die.log |
| 3 | ds_rom_s81_layer1 | dsfd_m2l_vr_68x11__hr_E4 | 1 | out_over in_over min_delay | 569.3 (756) | 638.2 (53) | 86.1 | ss | census (closed timing, generated_placeholder) | el1011-s81die.log |
| 4 | ds_rom_s81_layer1 | ot_s81_hc_crooty | 2 | out_over in_over min_delay | 596.9 (4694) | 400.9 (381) | 80.2 | ss | cell name | el1013-s81hc.log |
| 5 | ds_rom_s81_layer1 | dsfd_m2l_vr_68x11__hr_W1 | 1 | out_over in_over min_delay | 561.5 (761) | 596.7 (178) | 96.3 | ss | census (closed timing, generated_placeholder) | el1011-s81die.log |
| 6 | ds_rom_s81_layer1 | dsfd_m2l_vr_68x11__hr_W2 | 1 | out_over in_over min_delay | 561.5 (761) | 596.7 (178) | 96.3 | ss | census (closed timing, generated_placeholder) | el1011-s81die.log |
| 7 | ds_rom_s81_layer1 | dsfd_m2l_vr_68x11__hr_W3 | 1 | out_over in_over min_delay | 564.7 (753) | 533.9 (172) | 88.1 | ss | census (closed timing, generated_placeholder) | el1011-s81die.log |
| 8 | ds_rom_s81_layer1 | dsfd_m2l_vr_512x1__hco_SW | 1 | out_over in_over min_delay | 415.6 (511) | 550.6 (7) | 97.7 | ss | census (closed timing, generated_placeholder) | el1011-s81die.log |
| 9 | ds_rom_s81_layer1 | dsfd_m2l_vr_68x10__hr_W5 | 1 | out_over in_over min_delay | 545.2 (666) | 520.2 (51) | 85.5 | ss | census (closed timing, generated_placeholder) | el1011-s81die.log |
| 10 | ds_rom_s81_layer1 | ot_mtp_p2_prefix_path | 1 | out_over in_over | 351.3 (601) | 504.9 (1314) | 174.5 | ss | cell name (1 of 2 views) | el1013-ds-mtp-lead.log |
| 11 | ds_rom_s81_layer1 | dsfd_coll_ct | 1 | out_over in_over | 351.4 (1503) | 496.7 (1115) | 136.1 | tt | cell name (1 of 3 views) | el1011-ds-coll.log |
| 12 | ds_rom_s81_layer1 | dsfd_su_t_ctl | 1 | out_over in_over min_delay | 247.0 (7) | 489.5 (463) | 56.0 | tt | cell name (1 of 2 views) | el1011-s81-suhc-hier-1011.log |
| 13 | qwen_rom | qfd_d2d_rom | 1 | out_over in_over | 399.4 (173) | 451.9 (1531) | 146.3 | tt | bind map | el1011-qwendie.log |
| 14 | ds_rom_s81_layer1 | dsfd_m2l_vr_512x1__hqe_SW | 1 | out_over in_over | 273.5 (26) | 433.5 (2) | 104.8 | tt | census (closed timing, generated_placeholder) | el1011-s81die.log |
| 15 | ds_rom_s81_layer1 | dsfd_r2l_vr_512x1__hsel | 1 | out_over in_over | 432.1 (514) | 294.5 (2) | 112.1 | tt | census (closed timing, generated_placeholder) | el1011-s81die.log |
| 16 | ds_rom_s81_layer1 | dsfd_l2r_vr_564x1__hx_W | 1 | out_over in_over | 429.0 (568) | 372.7 (1) | 126.6 | tt | census (closed timing, generated_placeholder) | el1011-s81die.log |
| 17 | qwen_rom_tp8 | qkd_ectl | 32 | out_over in_over | 427.2 (2276) | 427.3 (455) | 133.1 | tt | ALIAS (same-family master, candidate only) | el1011-q-kvd.log |
| 18 | ds_rom_s81_layer1 | ot_s81_hc_cpin | 1 | out_over in_over | 427.1 (3721) | 418.2 (860) | 146.6 | tt | cell name (1 of 2 views) | el1013-s81hc.log |
| 19 | ds_rom_s81_layer1 | dsfd_r2l_vr_512x1__hcol | 1 | out_over in_over | 416.3 (514) | 298.8 (2) | 110.7 | tt | census (closed timing, generated_placeholder) | el1011-s81die.log |
| 20 | qwen_rom_tp8 | qfd_io_serdes | 3 | out_over in_over | 408.3 (1012) | 346.4 (2071) | 161.3 | tt | bind map | el1011-qwen-tp8.log |
| 21 | ds_rom_s81_layer1 | dsfd_l2r_vr_512x1__hq_SW | 1 | out_over in_over | 401.7 (516) | 174.4 (10) | 115.1 | ss | census (closed timing, generated_placeholder) | el1011-s81die.log |
| 22 | ds_rom_s81_layer1 | dsfd_r2l_vr_1024x1__ha_SW | 1 | out_over in_over min_delay | 182.1 (6) | 394.0 (2) | 96.7 | tt | census (closed timing, generated_placeholder) | el1011-s81die.log |
| 23 | ds_rom_s81_layer1 | dsfd_m2l_vr_512x1__hix_SW | 1 | out_over in_over | 246.0 (57) | 390.9 (2) | 107.7 | tt | census (closed timing, generated_placeholder) | el1011-s81die.log |
| 24 | qwen_rom_tp8 | qfd_su_cbuf_g | 8 | out_over in_over | 221.9 (717) | 380.7 (502) | 174.6 | tt | bind map | el1011-qwen-tp8.log |
| 25 | qwen_rom | qfd_su_cbuf_g | 8 | out_over in_over | 221.9 (717) | 380.7 (502) | 174.6 | tt | bind map | el1011-qwendie.log |
| 26 | ds_rom_s81_layer1 | dsfd_su_t_pin | 4 | out_over in_over | 376.5 (4105) | 330.3 (3163) | 142.1 | tt | cell name (1 of 3 views) | el1011-s81-suhc-hier-1011.log |
| 27 | ds_rom_s81_layer1 | ot_s81_hc_crooty_w | 2 | out_over in_over | 376.4 (2172) | 330.5 (1964) | 207.8 | tt | cell name (1 of 2 views) | el1013-s81hc.log |
| 28 | ds_rom_s81_layer1 | dsfd_coll_lane_w | 8 | out_over in_over min_delay | 347.5 (560) | 371.8 (460) | 39.2 | tt | cell name | el1011-ds-coll.log |
| 29 | ds_rom_s81_layer1 | ot_p2h_head | 1 | out_over in_over min_delay | 366.1 (380) | 304.9 (1308) | 93.5 | tt | cell name | el1013-s81hc.log |
| 30 | ds_rom_s81_layer1 | ot_s81_hc_crootr_t | 2 | out_over in_over | 304.3 (1495) | 343.5 (1190) | 135.7 | tt | contract kit s81hc_crrte_ref | el1013-s81hc.log |
| 31 | ds_rom_s81_layer1 | dsfd_coll_cbr | 2 | out_over in_over | 322.2 (708) | 195.4 (31) | 105.7 | tt | cell name (1 of 3 views) | el1011-ds-coll.log |
| 32 | qwen_rom_tp8 | qkd_kvwq_ctl_bin | 4 | out_over | 318.8 (141) | 139.5 (0) | 128.5 | tt | ALIAS (same-family master, candidate only) | el1011-q-kvd.log |
| 33 | qwen_rom_tp8 | qfd_tt_up4 | 1 | out_over in_over | 189.9 (298) | 311.6 (2) | 137.6 | tt | ALIAS (same-family master, candidate only) | el1011-qwen-tp8.log |
| 34 | qwen_rom_tp8 | qfd_tt_up4_g | 3 | out_over in_over | 189.9 (298) | 311.6 (2) | 137.6 | tt | ALIAS (same-family master, candidate only) | el1011-qwen-tp8.log |
| 35 | qwen_rom | qfd_tt_up4 | 1 | out_over in_over | 189.9 (298) | 311.6 (2) | 137.6 | tt | ALIAS (same-family master, candidate only) | el1011-qwendie.log |
| 36 | qwen_rom | qfd_tt_up4_g | 3 | out_over in_over | 189.9 (298) | 311.6 (2) | 137.6 | tt | ALIAS (same-family master, candidate only) | el1011-qwendie.log |
| 37 | ds_rom_s81_layer1 | dsfd_m2l_raw_512x1__hl_E2 | 1 | out_over | 282.4 (87) | 138.5 (0) | 100.0 | tt | census (closed timing, generated_placeholder) | el1011-s81die.log |
| 38 | ds_rom_s81_layer1 | dsfd_m2l_raw_512x1__hl_W1 | 1 | out_over min_delay | 272.5 (91) | 118.6 (0) | 99.1 | tt | census (closed timing, generated_placeholder) | el1011-s81die.log |
| 39 | ds_rom_s81_layer1 | dsfd_svc_join | 1 | out_over in_over | 199.6 (42) | 261.6 (26) | 120.0 | ss | census (closed timing, generated_placeholder) | el1011-s81die.log |
| 40 | ds_rom_s81_layer1 | dsfd_m2l_raw_512x1__hl_E0 | 1 | out_over min_delay | 260.9 (22) | 105.1 (0) | 95.9 | tt | census (closed timing, generated_placeholder) | el1011-s81die.log |
| 41 | ds_rom_s81_layer1 | ot_p2h_fadd16 | 1 | out_over | 256.5 (283) | 164.4 (0) | None | ss | cell name | el1013-s81hc.log |
| 42 | ds_rom_s81_layer1 | dsfd_l2r_vr_564x1__hx_E | 1 | out_over | 254.5 (566) | 120.9 (0) | 116.1 | tt | census (closed timing, generated_placeholder) | el1011-s81die.log |
| 43 | ds_rom_s81_layer1 | dsfd_coll_cbq0 | 1 | out_over in_over | 247.6 (52) | 184.4 (2) | 147.3 | tt | cell name (1 of 3 views) | el1011-ds-coll.log |
| 44 | ds_rom_s81_layer1 | dsfd_cfifo | 128 | out_over in_over min_delay | 246.7 (515) | 201.9 (1) | 95.1 | tt | census (closed timing, generated_placeholder) | el1011-s81die.log |
| 45 | ds_rom_s81_layer1 | dsfd_vm_be_sl | 4 | out_over in_over | 186.9 (5) | 246.0 (25) | 112.8 | tt | cell name (1 of 6 views) | el1011-ds-vm.log |
| 46 | ds_rom_s81_layer1 | dsfd_coll_cbq | 4 | out_over min_delay | 245.1 (1) | 163.6 (0) | 98.0 | ss | cell name (1 of 3 views) | el1011-ds-coll.log |
| 47 | qwen_rom_tp8 | qfd_crom_g | 8 | out_over in_over | 212.1 (152) | 242.2 (206) | 200.9 | tt | bind map | el1011-qwen-tp8.log |
| 48 | qwen_rom | qfd_crom_g | 8 | out_over in_over | 212.1 (152) | 242.2 (206) | 200.9 | tt | bind map | el1011-qwendie.log |
| 49 | ds_rom_s81_layer1 | ot_p2h_xport | 1 | out_over | 210.2 (271) | 135.6 (0) | None | ss | cell name | el1013-s81hc.log |
| 50 | qwen_rom_tp8 | qfd_chead_e | 24 | out_over min_delay | 180.4 (2) | 101.3 (0) | 86.4 | tt | ALIAS (same-family master, candidate only) | el1011-qwen-tp8.log |
| 51 | qwen_rom_tp8 | qfd_chead_w | 24 | out_over min_delay | 180.4 (2) | 101.3 (0) | 86.4 | tt | ALIAS (same-family master, candidate only) | el1011-qwen-tp8.log |
| 52 | qwen_rom | qfd_chead_e | 32 | out_over min_delay | 180.4 (2) | 101.3 (0) | 86.4 | tt | ALIAS (same-family master, candidate only) | el1011-qwendie.log |
| 53 | qwen_rom | qfd_chead_w | 32 | out_over min_delay | 180.4 (2) | 101.3 (0) | 86.4 | tt | ALIAS (same-family master, candidate only) | el1011-qwendie.log |
| 54 | qwen_rom_tp8 | qkd_kvwq_leaf_s_w129_m | 128 | out_over in_over | 176.8 (49) | 177.1 (1) | 125.5 | tt | cell / view name | el1011-q-kvd.log |
| 55 | qwen_rom_tp8 | ot_qfd_serdes_112g_x12_phy | 1 | min_delay | 117.3 (0) | 143.5 (0) | 31.9 | tt | cell / view name | el1011-qwen-tp8.log |
| 56 | qwen_rom_tp8 | qfd_cst_n | 384 | min_delay | 151.5 (0) | 95.4 (0) | 85.5 | tt | ALIAS (same-family master, candidate only) | el1011-qwen-tp8.log |
| 57 | qwen_rom_tp8 | qfd_cst_s | 384 | min_delay | 151.5 (0) | 95.4 (0) | 85.5 | tt | ALIAS (same-family master, candidate only) | el1011-qwen-tp8.log |
| 58 | qwen_rom | ot_qkvd_ucie_x64_phy | 1 | min_delay | 117.3 (0) | 143.5 (0) | 31.9 | tt | cell / view name | el1011-qwendie.log |
| 59 | qwen_rom | qfd_cst_n | 768 | min_delay | 151.5 (0) | 95.4 (0) | 85.5 | tt | ALIAS (same-family master, candidate only) | el1011-qwendie.log |
| 60 | qwen_rom | qfd_cst_s | 768 | min_delay | 151.5 (0) | 95.4 (0) | 85.5 | tt | ALIAS (same-family master, candidate only) | el1011-qwendie.log |
| 61 | ds_rom_s81_layer1 | dsfd_stnv_512x1 | 383 | min_delay | 115.4 (0) | 28.1 (0) | 41.3 | tt | census (closed timing, generated_placeholder) | el1011-s81die.log |
| 62 | ds_rom_s81_layer1 | dsfd_stnh_566x1 | 391 | min_delay | 117.0 (0) | 31.4 (0) | 43.2 | tt | census (closed timing, generated_placeholder) | el1011-s81die.log |
| 63 | ds_rom_s81_layer1 | dsfd_stnh_512x1 | 598 | min_delay | 116.9 (0) | 28.1 (0) | 44.0 | tt | census (closed timing, generated_placeholder) | el1011-s81die.log |
| 64 | ds_rom_s81_layer1 | dsfd_stnh_514x1 | 43 | min_delay | 115.5 (0) | 29.0 (0) | 44.9 | tt | census (closed timing, generated_placeholder) | el1011-s81die.log |
| 65 | ds_rom_s81_layer1 | dsfd_stnv_514x1 | 129 | min_delay | 117.2 (0) | 28.9 (0) | 45.6 | tt | census (closed timing, generated_placeholder) | el1011-s81die.log |
| 66 | ds_rom_s81_layer1 | dsfd_coll_cbf | 1 | min_delay | 114.2 (0) | 125.3 (0) | 94.9 | tt | cell name | el1011-ds-coll.log |
