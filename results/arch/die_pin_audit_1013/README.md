# Die pin-readiness audit, 2026-10-13 (both ROM dies)

Owner question: will covered or badly placed pins still break the die route?  Tools: tools/hier_contract/die_pin_audit.py (master tables: child_lint --strict-pockets + slot fit on every published LEF), pin_align.py (bundle alignment; gate in the generators' check step and slot_fit), legacy_layer_cuts.py (die tracks under M6 / M7 tiles).  Per-die detail: <die>_masters.md, <die>_pin_align.json, <die>_legacy_layers.md.

## Answer and limits (read first)

- **Covered pins: yes, they would still break die-region routes on S81, not on the Qwen views that are bindable today.** Qwen TP8: the 9 masters whose own view exists (stations, heads, cdc_wleaf, kvwq leaf / ctl, 1,077 + 4 instances) have 0 face pins blocked from above and 0 own-stub OBS; the 5 other published views are family masters of another outline (new routes are owed anyway). S81: 28 masters / 1,316 instances carry 26,256 face pins under the tile's own metal on the layer above (stations dsfd_stnh_* x1,032, dsfd_cfifo x128, vm_be_sl x4, crooty x2, the m2l / l2r / r2l hub-end masters): child_lint (f) class, DRT-0073 at the cbh parent. The 27 dsfd_rly_* relay tiles (29,184 instances) and the M5 re-routes are clean.
- **Badly placed pins: yes, on both dies, and nothing gated it before today.** Qwen tp8b (main generator): 453 of 14,666 bundles (244,594 bits) have a jog over 20 um that does not fit the channel between the two faces; 1,901 bundles jog over 20 um, 441 are reordered, 812 are u-turns. S81 v14: 7,181 of 115,030 bundles (915,482 bits) fail, 57,921 jog over 20 um, 18,819 reordered, 15,111 u-turns. Nearly all are FIX AT DIE: at least one end is a generated abstract whose pins the generator places (845 of 848 flagged classes on Qwen, 457 of 468 on S81).
- **View fixes applied** (main cf55509c8): pocket fill on 6 S81 abstracts (dsfd_su_t_ctl, ot_s81_hc_cpin, dsfd_coll_cbf, dsfd_coll_cbq, ot_mtp_p2_prefix_path, ot_p2h_xport). Not applied: dsfd_stnv_512x1 (17 M7 pockets; its LEF hash is pinned in results/arch/s81_native_20261013/qualification.json: S81 lead to run abstract_pin_stub.py + view_binding.py) and the q element (6,682 M7 pockets; coordinator 12:25: view kept, die M7 stays off it).
- **Limits.** (1) Both dies were built from the generators on MAIN (Qwen recipe tp8b, S81 s81_layer1_v14.opts + --cfifo-colck); the leads' branches (Qwen relay r8 / contract v5, S81 v15 relays) are newer and were not audited. (2) Pin positions are the generators' pin tables, overlaid with published-view pins only where outline and pin names match (Qwen 6 masters / 25 ports, S81 27 masters / 282 ports; the S81 relay views are 15.12 um while the die model still places 17.256-um relay abstracts, so the relay ends are generated pins). (3) "Blocked from above" is the child_lint (f) test: no via access from the layer above; planar access on the pin's own layer from the channel is not modelled. (4) The S81 legacy-layer scan applies the TP8 cut model to the S81 bus list; S81 has no cut table of its own, so its absolute utilisations (up to 5.9) are not a verdict, only the difference between the columns is. (5) On Qwen the scan flags qkd_rhead x128 (contract: PG / signals M7) as outside the cut model's cluster list: 593 window positions pass 0.60 if the die cannot use M6 / M7 over it; the rhead's own 43.2-um N-S relay channel is not in this model, so this is a check for the die lead, not a measured overflow.
- **Gate.** pin_align: WARN above 20 um / reordered / u-turn; FAIL when a jog above 20 um needs more than 0.60 of the tracks of the channel between the two faces (it then spills onto the die's over-tile tracks, demand no cut table contains), or an abutted pair is off by more than one track. One-ended form in slot_fit: a tile's planned pin range more than 36 um outside its slot span is a mismatch (378 jog wires = 0.60 of a 20-um channel = 36 um of a relay-pitch bus), more than 20 um a note. OT_PIN_ALIGN_GATE=warn|off overrides in the generators.

## qwen_rom_tp8 (contract v4, views origin/main 151c35012)

**Masters**: 14 of 292 masters have a published LEF (1133 of 12180 instances). Face pins blocked from above: 3625 pins on 3 masters; own-stub OBS on 4 masters; open pockets on 10 masters (5 on a die layer >= M6); slot mismatch on 8 masters.

| class | masters | instances | masters |
|---|---:|---:|---|
| FIX BY PIN RE-PLAN | 5 | 52 | qkd_ectl x32, qfd_crom_g x8, qfd_su_cbuf_g x8, qfd_io_serdes x3, qfd_tt_up4 x1 |
| FIX BY VIEW | 0 | 0 |  |
| FIX AT DIE | 1 | 4 | qkd_kvwq_ctl_bin x4 |
| ACCEPT | 8 | 1077 | qfd_cst_n x384, qfd_cst_s x384, qkd_cdc_wleaf x128, qkd_kvwq_leaf_s_w129_m x128, qfd_chead_e x24, qfd_chead_w x24, ot_hbm3e_phy x4, ot_qfd_serdes_112g_x12_phy x1 |

**Pin alignment** (tools/qwen_rom_fulldie_b3r2.py tp8b; pins: generator pin table (tools/die_top_lint.py pin_table); published-view overlay on 6 masters / 25 ports): 14666 bundles / 6568710 bits (0 bits without a pin). Verdict FAIL: FAIL 453, WARN 2444, OK 11769 bundles. Jog > 20 um: 1901 bundles / 756647 bits (max 838.1 um); bit order not preserved: 441 bundles / 142254 bits; kinds straight 12063, uturn 812, area 1639, corner 152; pin-to-pin length mean 300.9 / max 2385.672 um.

Jog distribution of straight bundles (max jog per bundle): <= 1 track um: 8636 bundles / 4053979 bits; <= 5 um: 877 bundles / 328327 bits; <= 20 um: 649 bundles / 329177 bits; <= 36 um: 859 bundles / 278839 bits; <= 100 um: 532 bundles / 218010 bits; > 100 um: 510 bundles / 259798 bits.

Flagged bundle classes: 848 (FIX AT DIE 845, FIX BY PIN RE-PLAN 3).

| driver -> load | kind | bundles | bits | jog max / mean um | gap min um | jog cut max | order | len max um | verdict | class | example |
|---|---|---:|---:|---|---:|---:|---|---:|---|---|---|
| qfd_io_xfifo.o_serdes_rx2 -> qfd_io_collective.sr2 | straight | 1 | 1024 | 371.28 / 371.28 | 4.536 | 7.1643 | preserved 1 | 375.816 | FAIL | FIX AT DIE | serdes_rx2_x io_xfifo -> io_collective |
| qfd_io_collective.s1 -> qfd_io_xfifo.i_serdes_tx1 | straight | 1 | 1024 | 334.032 / 309.48 | 4.536 | 7.1643 | preserved 1 | 338.568 | FAIL | FIX AT DIE | serdes_tx1 io_collective -> io_xfifo |
| qfd_io_collective.s2 -> qfd_io_xfifo.i_serdes_tx2 | straight | 1 | 1024 | 182.496 / 157.944 | 4.536 | 7.1643 | preserved 1 | 187.032 | FAIL | FIX AT DIE | serdes_tx2 io_collective -> io_xfifo |
| qfd_io_xfifo.o_serdes_rx1 -> qfd_io_collective.sr1 | straight | 1 | 1024 | 71.088 / 71.088 | 4.536 | 7.1643 | preserved 1 | 75.624 | FAIL | FIX AT DIE | serdes_rx1_x io_xfifo -> io_collective |
| qfd_io_xfifo.o_serdes_rx -> qfd_io_collective.sr | straight | 1 | 1024 | 70.656 / 70.656 | 4.536 | 7.1643 | preserved 1 | 75.192 | FAIL | FIX AT DIE | serdes_rx_x io_xfifo -> io_collective |
| qfd_rly_530_ES_53x60.b -> qkd_embgw.gq | straight | 1 | 530 | 190.512 / 190.512 | 2.376 | 7.0791 | preserved 1 | 192.888 | FAIL | FIX AT DIE | gq__r2 rly_gq_1 -> embgw |
| qfd_io_xfifo.o_ucie_rx -> qfd_io_collective.ur | straight | 1 | 1024 | 48.096 / 48.096 | 4.536 | 7.0174 | preserved 1 | 52.632 | FAIL | FIX AT DIE | ucie_rx_x io_xfifo -> io_collective |
| qfd_io_collective.s -> qfd_io_xfifo.i_serdes_tx | straight | 1 | 1024 | 63.984 / 39.432 | 4.536 | 4.6666 | preserved 1 | 68.52 | FAIL | FIX AT DIE | serdes_tx io_collective -> io_xfifo |
| qkd_kvwq_leaf_s_w129_m.w -> qkd_cdc_wleaf.wi | straight | 128 | 37120 | 31.896 / 23.047 | 2.298 | 3.8806 | interleaved 128 | 34.194 | FAIL | FIX BY PIN RE-PLAN | ww_ES_0 wleaf_ES_0 -> cdc_ES_0 |
| qkd_ahub.ao -> qkd_seq.ar | straight | 1 | 520 | 43.2 / 43.2 | 4.536 | 3.6381 | preserved 1 | 47.736 | FAIL | FIX AT DIE | ares ahub -> seq |
| qfd_io_collective.cs -> qfd_io_xfifo.i_coll_seq | straight | 1 | 518 | 44.064 / 44.064 | 4.536 | 3.6241 | preserved 1 | 48.6 | FAIL | FIX AT DIE | coll_seq io_collective -> io_xfifo |
| qfd_rly_530_EW_53x60.b -> qfd_rly_530_EW_53x60.a | straight | 193 | 102290 | 174.96 / 8.002 | 4.104 | 2.8841 | preserved 193 | 517.32 | FAIL | FIX AT DIE | emr_ES__r37 rly_emr_ES_36 -> rly_emr_ES_37 |
| qkd_rly_1025.b -> qkd_rly_1025.a | straight | 28 | 28700 | 583.2 / 205.971 | 12.336 | 2.6369 | preserved 28 | 703.536 | FAIL | FIX AT DIE | krs_WS_4__r4 rly_krs_WS_4_3 -> rly_krs_WS_4_4 |
| qfd_rly_540_WS_53x60.b -> qkd_astk_n.aq | straight | 1 | 540 | 98.976 / 60.168 | 6.696 | 2.5593 | reversed 1 | 105.672 | FAIL | FIX AT DIE | aq_EN__r57 rly_aq_EN_56 -> astk_EN |
| qfd_rly_563_SW_53x60.b -> qfd_rly_563_EN_53x60.a | straight | 3 | 1689 | 58.32 / 22.32 | 7.992 | 2.2356 | preserved 3 | 962.712 | FAIL | FIX AT DIE | ap_WN__r22 rly_ap_WN_21 -> rly_ap_WN_22 |
| qfd_io_collective.u -> qfd_io_xfifo.i_ucie_tx | straight | 1 | 1024 | 24.576 / 12.288 | 4.536 | 1.7981 | preserved 1 | 29.112 | FAIL | FIX AT DIE | ucie_tx io_collective -> io_xfifo |
| qfd_io_xfifo.o_ucie_tx -> qfd_io_ucie.c | straight | 1 | 1024 | 24.576 / 12.288 | 4.536 | 1.7981 | preserved 1 | 29.112 | FAIL | FIX AT DIE | ucie_tx_x io_xfifo -> io_ucie |
| qfd_rly_530_NS_53x60.b -> qfd_rly_530_NS_53x60.a | straight | 207 | 109710 | 120.96 / 6.004 | 11.016 | 1.5269 | preserved 207 | 464.616 | FAIL | FIX AT DIE | ing_WN__r11 rly_ing_WN_10 -> rly_ing_WN_11 |
| qkd_rly_1025.b -> qkd_ectl.rs | straight | 8 | 8200 | 311.712 / 108.421 | 22.272 | 1.4605 | preserved 8 | 333.984 | FAIL | FIX AT DIE | krs_ES_5__r12 rly_krs_ES_5_11 -> ectl_ES_5 |
| qfd_rly_530_NW_53x60.b -> qkd_land.ing | straight | 1 | 530 | 32.112 / 19.416 | 8.112 | 1.3106 | preserved 1 | 40.224 | FAIL | FIX AT DIE | ing_WS__r87 rly_ing_WS_86 -> land_WS |
| qfd_rly_563_WE_53x60.b -> qfd_rly_563_WE_53x60.a | straight | 76 | 42788 | 168.48 / 7.873 | 2.808 | 1.2771 | preserved 76 | 510.84 | FAIL | FIX AT DIE | ap_WN__r17 rly_ap_WN_16 -> rly_ap_WN_17 |
| qfd_rly_540_EW_53x60.b -> qfd_rly_540_EW_53x60.a | straight | 68 | 36720 | 69.12 / 3.558 | 17.064 | 1.0043 | preserved 68 | 369.576 | FAIL | FIX AT DIE | aq_WN__r35 rly_aq_WN_34 -> rly_aq_WN_35 |
| qfd_rly_563_SE_53x60.b -> qfd_rly_563_WS_53x60.a | straight | 1 | 563 | 23.76 / 23.76 | 7.992 | 0.9848 | preserved 1 | 31.752 | FAIL | FIX AT DIE | ap_WN__r11 rly_ap_WN_10 -> rly_ap_WN_11 |
| qfd_rly_540_EW_53x60.b -> qfd_rly_540_EN_53x60.a | straight | 5 | 2700 | 21.6 / 14.688 | 7.56 | 0.8974 | preserved 5 | 293.112 | FAIL | FIX AT DIE | aq_EN__r46 rly_aq_EN_45 -> rly_aq_EN_46 |
| qfd_rly_476_SW_53x30.b -> qfd_sp_su64_sfu.si | straight | 1 | 476 | 41.616 / 41.616 | 17.064 | 0.8853 | preserved 1 | 58.68 | FAIL | FIX AT DIE | o4_su_iss__r1 rly_o4_su_iss_0 -> sp_su64_sfu |
| qfd_rly_530_WN_53x60.b -> qfd_rly_530_SE_53x60.a | straight | 3 | 1590 | 394.848 / 148.752 | 0.216 | 0.0436 | preserved 3 | 943.704 | FAIL | FIX AT DIE | emf_EN__r1 rly_emf_EN_0 -> rly_emf_EN_1 |
| qkd_rhead.nb -> qkd_astk.f30 | straight | 2 | 2048 | 357.456 / 259.248 | 0.648 | - | reversed 2 | 358.104 | FAIL | FIX AT DIE | nb_WS_3_0 head_WS_3_0 -> astk_WS |
| qkd_rhead.nb -> qkd_astk.f31 | straight | 2 | 2048 | 357.456 / 259.248 | 0.648 | - | reversed 2 | 358.104 | FAIL | FIX AT DIE | nb_WS_3_1 head_WS_3_1 -> astk_WS |
| qkd_rhead.nb -> qkd_astk.f70 | straight | 2 | 2048 | 357.456 / 259.248 | 0.648 | - | reversed 2 | 358.104 | FAIL | FIX AT DIE | nb_WS_7_0 head_WS_7_0 -> astk_WS |
| qkd_rhead.nb -> qkd_astk.f71 | straight | 2 | 2048 | 357.456 / 259.248 | 0.648 | - | reversed 2 | 358.104 | FAIL | FIX AT DIE | nb_WS_7_1 head_WS_7_1 -> astk_WS |
| qkd_rhead.nb -> qkd_astk_n.f30 | straight | 2 | 2048 | 357.456 / 259.248 | 0.648 | - | reversed 2 | 358.104 | FAIL | FIX AT DIE | nb_WN_3_0 head_WN_3_0 -> astk_WN |
| qkd_rhead.nb -> qkd_astk_n.f31 | straight | 2 | 2048 | 357.456 / 259.248 | 0.648 | - | reversed 2 | 358.104 | FAIL | FIX AT DIE | nb_WN_3_1 head_WN_3_1 -> astk_WN |
| qkd_rhead.nb -> qkd_astk_n.f70 | straight | 2 | 2048 | 357.456 / 259.248 | 0.648 | - | reversed 2 | 358.104 | FAIL | FIX AT DIE | nb_WN_7_0 head_WN_7_0 -> astk_WN |
| qkd_rhead.nb -> qkd_astk_n.f71 | straight | 2 | 2048 | 357.456 / 259.248 | 0.648 | - | reversed 2 | 358.104 | FAIL | FIX AT DIE | nb_WN_7_1 head_WN_7_1 -> astk_WN |
| qkd_rhead.nb -> qkd_astk.f20 | straight | 2 | 2048 | 271.056 / 172.848 | 0.648 | - | reversed 2 | 271.704 | FAIL | FIX AT DIE | nb_WS_2_0 head_WS_2_0 -> astk_WS |
| qkd_rhead.nb -> qkd_astk.f21 | straight | 2 | 2048 | 271.056 / 172.848 | 0.648 | - | reversed 2 | 271.704 | FAIL | FIX AT DIE | nb_WS_2_1 head_WS_2_1 -> astk_WS |
| qkd_rhead.nb -> qkd_astk.f60 | straight | 2 | 2048 | 271.056 / 172.848 | 0.648 | - | reversed 2 | 271.704 | FAIL | FIX AT DIE | nb_WS_6_0 head_WS_6_0 -> astk_WS |
| qkd_rhead.nb -> qkd_astk.f61 | straight | 2 | 2048 | 271.056 / 172.848 | 0.648 | - | reversed 2 | 271.704 | FAIL | FIX AT DIE | nb_WS_6_1 head_WS_6_1 -> astk_WS |
| qkd_rhead.nb -> qkd_astk_n.f20 | straight | 2 | 2048 | 271.056 / 172.848 | 0.648 | - | reversed 2 | 271.704 | FAIL | FIX AT DIE | nb_WN_2_0 head_WN_2_0 -> astk_WN |
| qkd_rhead.nb -> qkd_astk_n.f21 | straight | 2 | 2048 | 271.056 / 172.848 | 0.648 | - | reversed 2 | 271.704 | FAIL | FIX AT DIE | nb_WN_2_1 head_WN_2_1 -> astk_WN |
| qkd_rhead.nb -> qkd_astk_n.f60 | straight | 2 | 2048 | 271.056 / 172.848 | 0.648 | - | reversed 2 | 271.704 | FAIL | FIX AT DIE | nb_WN_6_0 head_WN_6_0 -> astk_WN |
| qkd_rhead.nb -> qkd_astk_n.f61 | straight | 2 | 2048 | 271.056 / 172.848 | 0.648 | - | reversed 2 | 271.704 | FAIL | FIX AT DIE | nb_WN_6_1 head_WN_6_1 -> astk_WN |
| qkd_rhead.nb -> qkd_astk.f32 | straight | 2 | 2048 | 259.2 / 259.2 | 0.648 | - | preserved 2 | 259.848 | FAIL | FIX AT DIE | nb_WS_3_2 head_WS_3_2 -> astk_WS |
| qkd_rhead.nb -> qkd_astk.f33 | straight | 2 | 2048 | 259.2 / 259.2 | 0.648 | - | preserved 2 | 259.848 | FAIL | FIX AT DIE | nb_WS_3_3 head_WS_3_3 -> astk_WS |
| qkd_rhead.nb -> qkd_astk.f72 | straight | 2 | 2048 | 259.2 / 259.2 | 0.648 | - | preserved 2 | 259.848 | FAIL | FIX AT DIE | nb_WS_7_2 head_WS_7_2 -> astk_WS |
| qkd_rhead.nb -> qkd_astk.f73 | straight | 2 | 2048 | 259.2 / 259.2 | 0.648 | - | preserved 2 | 259.848 | FAIL | FIX AT DIE | nb_WS_7_3 head_WS_7_3 -> astk_WS |
| qkd_rhead.nb -> qkd_astk_n.f32 | straight | 2 | 2048 | 259.2 / 259.2 | 0.648 | - | preserved 2 | 259.848 | FAIL | FIX AT DIE | nb_WN_3_2 head_WN_3_2 -> astk_WN |
| qkd_rhead.nb -> qkd_astk_n.f33 | straight | 2 | 2048 | 259.2 / 259.2 | 0.648 | - | preserved 2 | 259.848 | FAIL | FIX AT DIE | nb_WN_3_3 head_WN_3_3 -> astk_WN |
| qkd_rhead.nb -> qkd_astk_n.f72 | straight | 2 | 2048 | 259.2 / 259.2 | 0.648 | - | preserved 2 | 259.848 | FAIL | FIX AT DIE | nb_WN_7_2 head_WN_7_2 -> astk_WN |
| qkd_rhead.nb -> qkd_astk_n.f73 | straight | 2 | 2048 | 259.2 / 259.2 | 0.648 | - | preserved 2 | 259.848 | FAIL | FIX AT DIE | nb_WN_7_3 head_WN_7_3 -> astk_WN |
| qkd_astk.e3o -> qkd_ectl.si | straight | 2 | 1268 | 259.2 / 259.2 | 0.648 | - | preserved 2 | 259.848 | FAIL | FIX AT DIE | eq_WS_3 astk_WS -> ectl_WS_3 |
| qkd_astk.e7o -> qkd_ectl.si | straight | 2 | 1268 | 259.2 / 259.2 | 0.648 | - | preserved 2 | 259.848 | FAIL | FIX AT DIE | eq_WS_7 astk_WS -> ectl_WS_7 |
| qkd_astk_n.e3o -> qkd_ectl.si | straight | 2 | 1268 | 259.2 / 259.2 | 0.648 | - | preserved 2 | 259.848 | FAIL | FIX AT DIE | eq_WN_3 astk_WN -> ectl_WN_3 |
| qkd_astk_n.e7o -> qkd_ectl.si | straight | 2 | 1268 | 259.2 / 259.2 | 0.648 | - | preserved 2 | 259.848 | FAIL | FIX AT DIE | eq_WN_7 astk_WN -> ectl_WN_7 |
| qkd_ectl.so -> qkd_astk.e3i | straight | 2 | 850 | 259.2 / 259.2 | 0.648 | - | preserved 2 | 259.848 | FAIL | FIX AT DIE | el_WS_3 ectl_WS_3 -> astk_WS |
| qkd_ectl.so -> qkd_astk.e7i | straight | 2 | 850 | 259.2 / 259.2 | 0.648 | - | preserved 2 | 259.848 | FAIL | FIX AT DIE | el_WS_7 ectl_WS_7 -> astk_WS |
| qkd_ectl.so -> qkd_astk_n.e3i | straight | 2 | 850 | 259.2 / 259.2 | 0.648 | - | preserved 2 | 259.848 | FAIL | FIX AT DIE | el_WN_3 ectl_WN_3 -> astk_WN |
| qkd_ectl.so -> qkd_astk_n.e7i | straight | 2 | 850 | 259.2 / 259.2 | 0.648 | - | preserved 2 | 259.848 | FAIL | FIX AT DIE | el_WN_7 ectl_WN_7 -> astk_WN |
| qkd_rhead.nb -> qkd_astk.f10 | straight | 2 | 2048 | 184.656 / 87.163 | 0.648 | - | reversed 2 | 185.304 | FAIL | FIX AT DIE | nb_WS_1_0 head_WS_1_0 -> astk_WS |
| qkd_rhead.nb -> qkd_astk.f11 | straight | 2 | 2048 | 184.656 / 87.163 | 0.648 | - | reversed 2 | 185.304 | FAIL | FIX AT DIE | nb_WS_1_1 head_WS_1_1 -> astk_WS |
| ... 788 more classes in qwen_rom_tp8_pin_align.json | | | | | | | | | | | |

**Legacy M6 / M7 tiles** (die-placed, measured view top >= M6): 0 masters / 0 instances, 0 mm2; they block 0 track-mm of die M6 and 0 track-mm of die M7. Cut windows (260 um): 646 positions over 0.6, of which 0 only because legacy tiles hold M6 / M7. Detail: qwen_rom_tp8_legacy_layers.md.

## s81_layer1 (contract v14, views origin/main fd5402b7a)

**Masters**: 79 of 248 masters have a published LEF (44756 of 56660 instances). Face pins blocked from above: 26256 pins on 28 masters; own-stub OBS on 20 masters; open pockets on 57 masters (30 on a die layer >= M6); slot mismatch on 13 masters.

| class | masters | instances | masters |
|---|---:|---:|---|
| FIX BY PIN RE-PLAN | 28 | 1316 | dsfd_stnh_512x1 x598, dsfd_stnh_566x1 x391, dsfd_stnv_514x1 x129, dsfd_cfifo x128, dsfd_stnh_514x1 x43, dsfd_vm_be_sl x4, ot_s81_hc_crooty x2, ot_p2h_xport x1, ot_p2h_fadd16 x1, dsfd_l2r_vr_512x1__hq_SW x1, dsfd_l2r_vr_564x1__hx_E x1, dsfd_l2r_vr_564x1__hx_W x1, dsfd_m2l_raw_512x1__hl_E0 x1, dsfd_m2l_raw_512x1__hl_E2 x1 ... |
| FIX BY VIEW | 2 | 1663 | ot_v41_rom_elem_q_qxpq_w10 x1280, dsfd_stnv_512x1 x383 |
| FIX AT DIE | 10 | 23 | dsfd_coll_lane_w x8, dsfd_su_t_pin x4, ot_s81_hc_crooty_w x2, ot_s81_hc_crootr_f x2, ot_s81_hc_crootr_r x2, ot_s81_hc_cpin x1, dsfd_coll_ct x1, ot_mtp_p2_prefix_path x1, ot_p2h_head x1, dsfd_svc_join x1 |
| ACCEPT | 38 | 41753 | ot_rom_4096x72_m8 x12547, dsfd_rly_63_WE x7808, dsfd_rly_63_NS x3968, dsfd_rly_63_WS x3456, dsfd_rly_2_NS x1118, dsfd_rly_15_SN x918, dsfd_rly_63_NE x896, dsfd_rly_66_NS x896, dsfd_rly_1_WE x640, dsfd_rly_266_SN x640, dsfd_rly_266_WE x640, dsfd_rly_283_SN x640, dsfd_rly_283_WE x640, dsfd_rly_2_ES x640 ... |

**Pin alignment** (tools/dsrom_s81_fulldie.py --gen r8 ; pins: generator pin table (tools/die_top_lint.py pin_table); published-view overlay on 27 masters / 282 ports): 115030 bundles / 7985755 bits (2 bits without a pin). Verdict FAIL: FAIL 7181, WARN 72636, OK 35213 bundles. Jog > 20 um: 57921 bundles / 2537702 bits (max 412.9 um); bit order not preserved: 18819 bundles / 1468560 bits; kinds straight 90411, corner 9508, uturn 15111; pin-to-pin length mean 213.0 / max 717.24 um.

Jog distribution of straight bundles (max jog per bundle): <= 1 track um: 13633 bundles / 1887547 bits; <= 5 um: 9678 bundles / 362445 bits; <= 20 um: 9179 bundles / 804773 bits; <= 36 um: 16713 bundles / 1159449 bits; <= 100 um: 36017 bundles / 1218886 bits; > 100 um: 5191 bundles / 159367 bits.

Flagged bundle classes: 468 (FIX AT DIE 457, FIX BY PIN RE-PLAN 11).

| driver -> load | kind | bundles | bits | jog max / mean um | gap min um | jog cut max | order | len max um | verdict | class | example |
|---|---|---:|---:|---|---:|---:|---|---:|---|---|---|
| dsfd_stnh_293x1.do0 -> dsfd_m2l_vr_291x1__he_hwSW.di0 | straight | 1 | 293 | 28.944 / 28.944 | 1.608 | 5.7827 | preserved 1 | 30.552 | FAIL | FIX AT DIE | hwSW_de f_hwSW_54 -> he_hwSW |
| dsfd_hstnh_2162.dq -> dsfd_hstnh_2162.di | straight | 1 | 2162 | 328.32 / 328.32 | 14.136 | 4.8537 | preserved 1 | 342.456 | FAIL | FIX AT DIE | hb_vm_pq_d0_g1_f_hb_vm_pq_1 g_hb_vm_pq_d0_f_hb_vm_pq_1_0 -> f_hb_vm_pq_1 |
| dsfd_hstnh_1024.dq -> dsfd_sp_hc_c.y_d | straight | 6 | 6144 | 175.872 / 89.504 | 8.472 | 3.8358 | preserved 6 | 305.304 | FAIL | FIX AT DIE | hb_collective_t_hc_y_5120_6143_hc_s_d7_g6_sp_hc_s g_hb_collective_t_hc_y_5120_6143_hc_s_d7_sp_hc_s_5 -> sp_hc_s |
| dsfd_qbank_S.o_x1 -> ot_v41_rom_elem_q_qxpq_w10.x1 | straight | 1280 | 340480 | 26.016 / 20.084 | 2.37 | 3.5619 | interleaved 1280 | 28.386 | FAIL | FIX AT DIE | xb_0_2_e1_eb_g0_e1 bs1 -> e1 |
| dsfd_hstnh_4096.dq -> dsfd_hstnh_4096.di | straight | 8 | 32768 | 380.16 / 47.52 | 46.968 | 2.7676 | preserved 8 | 452.616 | FAIL | FIX AT DIE | hb_hc_s_wq_d_vm_d8_g2_sp_vm g_hb_hc_s_wq_d_vm_d8_sp_vm_1 -> g_hb_hc_s_wq_d_vm_d8_sp_vm_2 |
| dsfd_qbank_S.o_x0 -> ot_v41_rom_elem_q_qxpq_w10.x0 | straight | 1280 | 362240 | 38.736 / 9.581 | 2.37 | 2.4505 | interleaved 1280 | 41.106 | FAIL | FIX AT DIE | xa_0_2_e1_eb_g0_e1 bs1 -> e1 |
| dsfd_m2l_raw_512x1__hl_W2.o -> dsfd_sp_collective_c.rW2 | straight | 1 | 515 | 23.28 / 23.28 | 6.312 | 2.4435 | preserved 1 | 29.592 | FAIL | FIX AT DIE | hl_W2_o hl_W2 -> sp_collective |
| dsfd_hstnh_1024.dq -> dsfd_hstnh_1024.di | straight | 59 | 60416 | 289.44 / 7.176 | 21.048 | 1.544 | preserved 59 | 472.056 | FAIL | FIX AT DIE | hb_collective_t_hc_y_4096_5119_hc_s_d0_g1_f_hb_collective_t_hc_y_4096_5119_hc_s_1 g_hb_collective_t_hc_y_4096_5119_hc_s_d0_f_hb_collective_t_hc_y_4096_5119_hc_s_1_0 -> f_hb_collective_t_hc_y_4096_5119_hc_s_1 |
| ot_pdie_ucie.rx -> dsfd_stnh_512x1.di0 | straight | 2 | 1024 | 400.272 / 200.079 | 5.496 | 1.4378 | preserved 2 | 406.104 | FAIL | FIX BY PIN RE-PLAN | KW0r_d0 lk_W0 -> f_KW0r_1 |
| dsfd_sstn_e0c0sinf.xb -> dsfd_rly_266_SN.i | straight | 128 | 34048 | 57.312 / 44.592 | 6.792 | 1.2429 | preserved 128 | 64.104 | FAIL | FIX AT DIE | xb_0_1_y0 t0_0 -> y_xb_0_1_0 |
| dsfd_sstn_e0c0sinf.xa -> dsfd_rly_283_SN.i | straight | 128 | 36224 | 31.008 / 17.472 | 6.792 | 1.0093 | preserved 128 | 37.8 | FAIL | FIX AT DIE | xa_0_1_y0 t0_0 -> y_xa_0_1_0 |
| dsfd_rly_63_WE.o -> dsfd_rly_63_WE.i | straight | 3712 | 233856 | 38.88 / 7.001 | 1.608 | 0.9801 | preserved 3712 | 296.232 | FAIL | FIX BY PIN RE-PLAN | rt_0_8b_y4 y_rt_0_8b_3 -> y_rt_0_8b_4 |
| dsfd_stnh_512x1.do0 -> ot_pdie_ucie.tx | straight | 2 | 1024 | 400.512 / 200.08 | 8.52 | 0.9275 | preserved 2 | 409.368 | FAIL | FIX BY PIN RE-PLAN | KW0_tx f_KW0t_58 -> lk_W0 |
| dsfd_hstnv_512.dq -> dsfd_sp_gather_c.f_vm | straight | 1 | 512 | 35.472 / 35.472 | 24.024 | 0.6763 | preserved 1 | 59.496 | FAIL | FIX AT DIE | hb_vm_gather_d1_g1_sp_gather g_hb_vm_gather_d1_sp_gather_0 -> sp_gather |
| dsfd_node_NNfu.fo -> dsfd_node_LLfu.fi | straight | 512 | 512 | 7.296 / 7.296 | 0.312 | - | preserved 512 | 7.608 | FAIL | FIX AT DIE | nf_0_23 n0_23 -> n0_22 |
| dsfd_node_LLfd.fo -> dsfd_node_NNfd.fi | straight | 384 | 384 | 7.296 / 7.296 | 0.312 | - | preserved 384 | 7.608 | FAIL | FIX AT DIE | nf_0_20 n0_20 -> n0_19 |
| dsfd_node_LLd.fo -> dsfd_node_NNfd.fi | straight | 128 | 128 | 7.296 / 7.296 | 0.312 | - | preserved 128 | 7.608 | FAIL | FIX AT DIE | nf_0_26 n0_26 -> n0_25 |
| dsfd_node_LLfd.o -> dsfd_node_NNfu.b | straight | 512 | 33792 | 4.704 / 4.704 | 0.312 | - | preserved 512 | 5.016 | FAIL | FIX AT DIE | rt_0_1b n0_2 -> n0_1 |
| dsfd_node_LLfu.o -> dsfd_node_NNfd.a | straight | 256 | 16896 | 4.704 / 4.704 | 0.312 | - | preserved 256 | 5.016 | FAIL | FIX AT DIE | rt_0_5a n0_4 -> n0_5 |
| dsfd_node_LLfd.fo -> dsfd_node_NNfu.fi | straight | 512 | 512 | 3.648 / 3.648 | 0.312 | - | preserved 512 | 3.96 | FAIL | FIX AT DIE | nf_0_24 n0_24 -> n0_23 |
| dsfd_node_NNfu.fo -> dsfd_node_LLfd.fi | straight | 384 | 384 | 3.648 / 3.648 | 0.312 | - | preserved 384 | 3.96 | FAIL | FIX AT DIE | nf_0_17 n0_17 -> n0_16 |
| dsfd_node_LLfu.fo -> dsfd_node_NNfd.fi | straight | 256 | 256 | 3.648 / 3.648 | 0.312 | - | preserved 256 | 3.96 | FAIL | FIX AT DIE | nf_0_22 n0_22 -> n0_21 |
| dsfd_node_NNfd.fo -> dsfd_node_LLfu.fi | straight | 256 | 256 | 3.648 / 3.648 | 0.312 | - | preserved 256 | 3.96 | FAIL | FIX AT DIE | nf_0_19 n0_19 -> n0_18 |
| dsfd_node_LLfu.o -> dsfd_node_NNfu.a | straight | 512 | 33792 | 1.056 / 1.056 | 0.312 | - | preserved 512 | 1.368 | FAIL | FIX AT DIE | rt_0_1a n0_0 -> n0_1 |
| dsfd_node_LLfd.o -> dsfd_node_NNfd.b | straight | 384 | 25344 | 1.056 / 1.056 | 0.312 | - | preserved 384 | 1.368 | FAIL | FIX AT DIE | rt_0_5b n0_6 -> n0_5 |
| dsfd_node_LLd.o -> dsfd_node_NNfd.b | straight | 128 | 8448 | 1.056 / 1.056 | 0.312 | - | preserved 128 | 1.368 | FAIL | FIX AT DIE | rt_0_25b n0_26 -> n0_25 |
| dsfd_stnh_512x1.do0 -> dsfd_m2l_raw_512x1__hl_W2.di0 | straight | 1 | 512 | 5.184 / 5.184 | 1.56 | 2.2174 | preserved 1 | 6.744 | WARN | FIX AT DIE | KW2r_de f_KW2r_53 -> hl_W2 |
| ot_v41_rom_elem_q_qxpq_w10.r1 -> dsfd_qbank_N.e_r1 | straight | 1280 | 80640 | 6.816 / 4.353 | 1.266 | 1.4539 | interleaved 1280 | 8.082 | WARN | FIX AT DIE | rt_0_2b_eb_g0_bn1 e1 -> bn1 |
| ot_v41_rom_elem_q_qxpq_w10.r0 -> dsfd_qbank_N.e_r0 | straight | 1280 | 80640 | 6.912 / 3.806 | 1.266 | 1.2283 | interleaved 1280 | 8.178 | WARN | FIX AT DIE | rt_0_2a_eb_g0_bn1 e1 -> bn1 |
| dsfd_sp_collective_c.t_hc_y -> dsfd_hstnh_1024.di | straight | 8 | 8192 | 412.896 / 152.556 | 59.88 | 0.5427 | preserved 8 | 472.776 | WARN | FIX AT DIE | hb_collective_t_hc_y_7168_8191_hc_s_d0_g0_f_hb_collective_t_hc_y_7168_8191_hc_s_1 sp_collective -> g_hb_collective_t_hc_y_7168_8191_hc_s_d0_f_hb_collective_t_hc_y_7168_8191_hc_s_1_0 |
| dsfd_rly_283_SN.o -> dsfd_bf.x0 | straight | 512 | 144896 | 89.568 / 73.368 | 17.544 | 0.5119 | preserved 512 | 107.112 | WARN | FIX AT DIE | xa_0_1 y_xa_0_1_0 -> e0 |
| dsfd_rly_266_SN.o -> dsfd_bf.x1 | straight | 512 | 136192 | 97.056 / 86.256 | 17.544 | 0.4812 | preserved 512 | 114.6 | WARN | FIX AT DIE | xb_0_3 y_xb_0_3_0 -> e3 |
| dsfd_stnh_512x1.do0 -> dsfd_stnh_512x1.di0 | straight | 548 | 280576 | 246.24 / 2.322 | 33.912 | 0.4791 | preserved 548 | 412.344 | WARN | FIX BY PIN RE-PLAN | KW0r_d1 f_KW0r_1 -> f_KW0r_2 |
| dsfd_hstnh_514.dq -> dsfd_wfc_stg.f_lid | straight | 1 | 513 | 43.632 / 43.632 | 38.712 | 0.4205 | preserved 1 | 82.344 | WARN | FIX AT DIE | hb_collective_wfc_d6_f_lid f_hb_collective_wfc_6 -> sp_wfc |
| ot_s81_cfg7_seq.cfg -> dsfd_qbank_S.i_cfg | straight | 640 | 34560 | 106.92 / 106.92 | 4.632 | 0.37 | preserved 640 | 111.552 | WARN | FIX AT DIE | cfg_1_g0_bs1 s1 -> bs1 |
| dsfd_hstnh_692.dq -> dsfd_hstnh_692.di | straight | 7 | 4844 | 45.36 / 6.48 | 62.088 | 0.3537 | preserved 7 | 192.984 | WARN | FIX AT DIE | hr_W0_o_d1_g0_sp_gather f_hr_W0_o_1 -> g_hr_W0_o_d1_sp_gather_0 |
| dsfd_sp_vm.t_collective -> dsfd_hstnh_592.di | straight | 1 | 592 | 29.376 / 29.376 | 55.56 | 0.3381 | preserved 1 | 84.936 | WARN | FIX AT DIE | hb_vm_collective_d0_g0_f_hb_vm_collective_1 sp_vm -> g_hb_vm_collective_d0_f_hb_vm_collective_1_0 |
| dsfd_sp_collective_c.tdE1 -> dsfd_stnh_512x1.di0 | straight | 1 | 512 | 61.104 / 61.104 | 59.832 | 0.2716 | preserved 1 | 120.936 | WARN | FIX AT DIE | KE1t_d0_g0_f_KE1t_1 sp_collective -> g_KE1t_d0_f_KE1t_1_0 |
| dsfd_stnh_70x1.do0 -> dsfd_stnh_70x11.di9 | straight | 4 | 280 | 178.944 / 120.084 | 9.816 | 0.2263 | preserved 4 | 234.12 | WARN | FIX AT DIE | rE2_d54_9_g1_f_rE2_55 g_rE2_d54_9_f_rE2_55_0 -> f_rE2_55 |
| dsfd_sp_vm.t_wfc -> dsfd_hstnh_516.di | straight | 1 | 516 | 28.848 / 28.848 | 77.16 | 0.2122 | preserved 1 | 106.008 | WARN | FIX AT DIE | hb_vm_wfc_d0_g0_f_hb_vm_wfc_1 sp_vm -> g_hb_vm_wfc_d0_f_hb_vm_wfc_1_0 |
| dsfd_hstnh_85.dq -> dsfd_sp_hc_c.c_cmd | straight | 1 | 85 | 137.952 / 137.952 | 13.224 | 0.204 | preserved 1 | 151.176 | WARN | FIX AT DIE | hb_sseq_hc_s_d8 f_hb_sseq_hc_s_8 -> sp_hc_s |
| dsfd_hstnh_514.dq -> dsfd_hstnh_514.di | straight | 16 | 8224 | 43.2 / 7.155 | 81.528 | 0.2001 | preserved 16 | 197.736 | WARN | FIX AT DIE | hb_collective_wfc_d0_g1_f_hb_collective_wfc_1 g_hb_collective_wfc_d0_f_hb_collective_wfc_1_0 -> f_hb_collective_wfc_1 |
| dsfd_sp_collective_c.tdE2 -> dsfd_stnh_512x1.di0 | straight | 1 | 512 | 59.472 / 59.472 | 81.432 | 0.1995 | preserved 1 | 140.904 | WARN | FIX AT DIE | KE2t_d0_g0_f_KE2t_1 sp_collective -> g_KE2t_d0_f_KE2t_1_0 |
| dsfd_sp_collective_c.tdE3 -> dsfd_stnh_512x1.di0 | straight | 1 | 512 | 32.736 / 32.736 | 81.432 | 0.1995 | preserved 1 | 114.168 | WARN | FIX AT DIE | KE3t_d0_g0_f_KE3t_1 sp_collective -> g_KE3t_d0_f_KE3t_1_0 |
| dsfd_sp_collective_c.tdE0 -> dsfd_stnh_512x1.di0 | straight | 1 | 512 | 23.04 / 23.04 | 81.432 | 0.1875 | preserved 1 | 104.472 | WARN | FIX AT DIE | KE0t_d0_g0_f_KE0t_1 sp_collective -> g_KE0t_d0_f_KE0t_1_0 |
| dsfd_hstnh_761.dq -> dsfd_hstnh_761.di | straight | 16 | 12176 | 45.36 / 2.835 | 64.248 | 0.1585 | preserved 16 | 197.736 | WARN | FIX AT DIE | hr_E4_o_d5 f_hr_E4_o_5 -> f_hr_E4_o_6 |
| dsfd_m2l_raw_512x1__hl_E3.o -> dsfd_hstnv_515.di | straight | 1 | 515 | 33.504 / 33.504 | 103.992 | 0.1572 | preserved 1 | 137.496 | WARN | FIX AT DIE | hl_E3_o_g0_sp_collective hl_E3 -> g_hl_E3_o_sp_collective_0 |
| dsfd_xstg_515.o -> dsfd_hstnh_515.di | straight | 2 | 1030 | 108 / 108 | 105.72 | 0.1546 | preserved 2 | 213.72 | WARN | FIX AT DIE | hix_SW_o_g0_bk_selector xsix_SW -> g_hix_SW_o_bk_selector_0 |
| dsfd_host_s.hw -> dsfd_l2r_vr_291x1__hs_hwSW.i | straight | 1 | 292 | 35.328 / 35.328 | 62.904 | 0.1473 | preserved 1 | 98.232 | WARN | FIX AT DIE | hs_hwSW_i sp_host -> hs_hwSW |
| dsfd_hstnh_592.dq -> dsfd_hstnh_592.di | straight | 5 | 2960 | 66.96 / 13.392 | 129.048 | 0.1456 | preserved 5 | 197.304 | WARN | FIX AT DIE | hb_vm_collective_d0_g1_f_hb_vm_collective_1 g_hb_vm_collective_d0_f_hb_vm_collective_1_0 -> f_hb_vm_collective_1 |
| ot_s81_cfg7_seq.cfg -> dsfd_bf.cfg | straight | 512 | 27648 | 105.24 / 105.24 | 13.224 | 0.1296 | preserved 512 | 118.464 | WARN | FIX AT DIE | cfg_0 s0 -> e0 |
| dsfd_stnh_512x1.do0 -> dsfd_m2l_raw_512x1__hl_W3.di0 | straight | 1 | 512 | 195.264 / 195.264 | 126.84 | 0.1281 | preserved 1 | 322.104 | WARN | FIX AT DIE | KW3r_de f_KW3r_58 -> hl_W3 |
| dsfd_hstnv_592.dq -> dsfd_hstnv_592.di | straight | 11 | 6512 | 35.424 / 3.22 | 162.312 | 0.1157 | preserved 11 | 197.736 | WARN | FIX AT DIE | hb_vm_collective_d6 f_hb_vm_collective_6 -> f_hb_vm_collective_7 |
| dsfd_stnv_566x1.do0 -> dsfd_stnv_566x1.di0 | straight | 118 | 66788 | 34.56 / 0.293 | 153.672 | 0.1153 | preserved 118 | 412.872 | WARN | FIX AT DIE | xEdn_d42 f_xEdn_42 -> f_xEdn_43 |
| dsfd_m2l_raw_512x1__hl_E2.o -> dsfd_hstnv_515.di | straight | 1 | 515 | 163.968 / 163.968 | 144.984 | 0.1127 | preserved 1 | 308.952 | WARN | FIX AT DIE | hl_E2_o_g0_sp_collective hl_E2 -> g_hl_E2_o_sp_collective_0 |
| dsfd_stnv_512x1.do0 -> dsfd_m2l_raw_512x1__hl_W1.di0 | straight | 1 | 512 | 132.384 / 132.384 | 157.896 | 0.1029 | preserved 1 | 290.28 | WARN | FIX AT DIE | KW1r_de f_KW1r_62 -> hl_W1 |
| dsfd_m2l_raw_512x1__hl_E1.o -> dsfd_hstnv_515.di | straight | 1 | 515 | 33.504 / 33.504 | 164.472 | 0.0994 | preserved 1 | 197.976 | WARN | FIX AT DIE | hl_E1_o_g0_sp_collective hl_E1 -> g_hl_E1_o_sp_collective_0 |
| dsfd_stnh_512x1.do0 -> dsfd_m2l_raw_512x1__hl_E1.di0 | straight | 1 | 512 | 41.904 / 41.904 | 170.904 | 0.0951 | preserved 1 | 212.808 | WARN | FIX AT DIE | KE1r_de f_KE1r_70 -> hl_E1 |
| ot_s81_cfg7_seq.a -> ot_rom_4096x72_m8.a | straight | 12544 | 150528 | 36.864 / 36.6 | 4.044 | 0.0942 | preserved 12544 | 368.388 | WARN | FIX AT DIE | ra_0 s0 -> c0_5 |
| dsfd_hstnv_1024.dq -> dsfd_hstnv_1024.di | straight | 2 | 2048 | 60.48 / 60.48 | 384.792 | 0.0845 | preserved 2 | 469.032 | WARN | FIX AT DIE | hb_collective_t_hc_y_7168_8191_hc_s_d0_g3_f_hb_collective_t_hc_y_7168_8191_hc_s_1 g_hb_collective_t_hc_y_7168_8191_hc_s_d0_f_hb_collective_t_hc_y_7168_8191_hc_s_1_2 -> g_hb_collective_t_hc_y_7168_8191_hc_s_d0_f_hb_collective_t_hc_y_7168_8191_hc_s_1_3 |
| ... 408 more classes in s81_layer1_pin_align.json | | | | | | | | | | | |

**Legacy M6 / M7 tiles** (die-placed, measured view top >= M6): 27 masters / 2972 instances, 151.147 mm2; they block 1771235.7 track-mm of die M6 and 1771235.7 track-mm of die M7. Cut windows (260 um): 333 positions over 0.6, of which 11 only because legacy tiles hold M6 / M7. Detail: s81_layer1_legacy_layers.md.

