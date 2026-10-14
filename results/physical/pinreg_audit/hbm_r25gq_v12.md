# Pin-register audit: hbm_r25gq (contract v12, 119dbd59f)

Rule (die statement): the die delivers the clock to each tile's clock pin at `phi - R` (R = mean insertion of the tile's boundary registers, the sign-off reference); a hop A -> B of L um needs `o_A + 0.76 L + s_B <= 833.3 - 60 - 90 = 683.3 ps` (o = clk->pin - R, s = setup@pin + R). Per tile C = o + s and reach = (683.3 - C) / 0.76 against its own kind; the per-side share at 500 um is 151.7 ps. The sign-off SDC (IO 0.2 T outside) proves only o, s <= 516.7 ps each. Hold: L - H >= 100 ps (50 + skew 50).

**PROVISIONAL: 15 of 22 audited views carry no corrected-export record (reexport_1013 / verdict check) after the export-SDC fix (abc334b14); their boundary numbers may be off by tens of ps**

Cells 97: audited 22 (654 instances); VIOLATING 19 {'in_unreg': 14, 'abut': 11, 'min_delay': 12, 'out_unreg': 16, 'spread': 1}; reach-limited only 8; clean 2; reference estimated (no insertion.json) 13; not auditable 75 (234 instances); alias-bound 0.

## Die clock delivery

R spans 154.6 (hfd_hc_tile_xl) .. 632.5 (ot_hcoll_port) ps at TT = 477.9 ps. Compensated entry: each branch carries R_max - R of added delay; OCV 5% on the non-shared 632.5 ps a side = 63.2 ps of the 90 ps die skew on EVERY hop; FF/TT tracking of R 0.801..1.204 = 192.7 ps over the span.

Worst potential pair, setup (available 683.3 ps before wire): compensated 846.2 ps (ot_hgi_dma_back -> ot_hcoll_port, wire left -162.9); COMMON-phase entry 1044.9 ps (ot_hcoll_port -> ot_hgi_coll_tkm_tile, wire left -361.6). Hold (need 100): compensated 38.6 ps (hfd_hc_tile_xl -> hfd_hc_tile_xl); common phase -206.0 ps (hfd_hc_tile_xl -> ot_hcoll_port).

## Tiles (all audited, worst reach first)

| cell | inst | corner | R ps (src) | clock entry vs phi | + branch delay | boundary spread | o ps (bus) | s ps (bus) | C = o+s | reach um | q_lb | p_lb | L-H | flags | notes |
|---|---:|---|---|---:|---:|---:|---|---|---:|---:|---:|---:|---:|---|---|
| hfd_sm | 32 | ss | 3831.9 (lib mid) | -3831.9 | - | 1104.9 | 624.4 (r) | 1112.5 (x) | 1736.9 | -928.3 | 72.0 | 560.0 | -101.9 | in_unreg abut min_delay | ref_estimated spread_unmeasured |
| hfd_svc_SW_s3 | 2 | ss | 794.5 (lib mid) | -794.5 | - | 248.1 | 652.5 (phy) | 1063.9 (rst) | 1716.4 | -910.2 | 528.5 | 939.9 | -8.5 | out_unreg in_unreg abut min_delay | ref_estimated spread_unmeasured |
| hfd_svc_SE_s5 | 2 | ss | 764.4 (lib mid) | -764.4 | - | 222.4 | 531.5 (phy) | 912.1 (rst) | 1443.6 | -669.8 | 420.3 | 800.9 | 0.4 | out_unreg in_unreg abut min_delay | ref_estimated spread_unmeasured |
| hfd_svc_SW_s0 | 2 | ss | 699.1 (lib mid) | -699.1 | - | 139.2 | 538.7 (phy) | 771.8 (rst) | 1310.5 | -552.6 | 469.1 | 702.2 | 23.0 | out_unreg in_unreg abut min_delay | ref_estimated spread_unmeasured |
| hfd_svc_SE_s0 | 2 | ss | 691.9 (lib mid) | -691.9 | - | 126.1 | 580.9 (phy) | 714.0 (rst) | 1294.9 | -538.8 | 517.8 | 650.9 | 34.8 | out_unreg in_unreg abut min_delay | ref_estimated spread_unmeasured |
| hfd_svc_SE_s8 | 2 | ss | 300.8 (lib mid) | -300.8 | - | 340.9 | 898.0 (phy) | 310.5 (wi) | 1208.5 | -462.7 | 727.5 | 140.0 | -97.9 | out_unreg abut min_delay | ref_estimated spread_unmeasured |
| hfd_svc_SW_s1 | 2 | ss | 947.3 (lib mid) | -947.3 | - | 450.6 | 523.8 (phy) | 526.1 (rst) | 1049.9 | -323.0 | 298.5 | 300.8 | -71.1 | out_unreg in_unreg abut min_delay | ref_estimated spread_unmeasured |
| hfd_svc_SE_s7 | 2 | ss | 520.2 (lib mid) | -520.2 | - | 65.6 | 419.4 (l7) | 388.6 (rst) | 808.0 | -109.8 | 386.5 | 355.8 | 44.3 | out_unreg in_unreg abut min_delay | ref_estimated |
| ot_hcoll_port | 9 | tt | 632.5 (ins.json) | -632.5 | 0.0 | 76.8 | 319.0 (rb_d) | 464.6 (rst_n) | 783.6 | -131.9 | 290.9 | 415.9 | 193.2 | out_unreg in_unreg abut | - |
| ot_hgi_coll_tkm_tile | 32 | tt | 323.1 (ins.json) | -323.1 | 309.4 | 37.9 | 324.5 (up_out) | 416.5 (ins_b) | 741.0 | -75.9 | 301.8 | 401.3 | 128.1 | out_unreg in_unreg abut | - |
| ot_hgi_dma_back | 4 | tt | 395.2 (ins.json) | -395.2 | 237.3 | 186.3 | 381.6 (wd) | 332.9 (vr2r) | 714.5 | -41.0 | 241.6 | 286.6 | 115.3 | out_unreg in_unreg spread abut | - |
| ot_su12_sfu | 64 | tt | 331.5 (ins.json) | -331.5 | 301.0 | 23.4 | 242.2 (kv_waddr) | 417.6 (rst_n) | 659.8 | 31.0 | 230.6 | 405.8 | 122.6 | out_unreg in_unreg | reach_limited |
| hfd_svc_SW_s7 | 2 | ss | 800.6 (lib mid) | -800.6 | - | 70.4 | 370.9 (ks7) | 224.4 (rst) | 595.3 | 77.6 | 335.7 | 189.2 | 42.8 | out_unreg min_delay | reach_limited ref_estimated |
| ot_hgi_seq_be | 1 | tt | 203.5 (ins.json) | -203.5 | 429.0 | 27.0 | 337.4 (be_jl_entry) | 255.1 (db_loff) | 592.5 | 119.5 | 322.0 | 243.5 | 182.4 | out_unreg in_unreg | reach_limited |
| hfd_svc_SW_s4 | 2 | ss | 557.3 (lib mid) | -557.3 | - | 141.9 | 343.4 (eo) | 183.6 (wi) | 527.0 | 137.7 | 272.4 | 112.6 | 34.3 | out_unreg min_delay | reach_limited ref_estimated spread_unmeasured |
| ot_hdc_v41x_idx_hslice | 128 | tt | 200.0 (ins.json) | -200.0 | 432.5 | 41.4 | 263.9 (ko_key) | 215.7 (first) | 479.6 | 268.1 | 239.0 | 199.2 | 169.0 | out_unreg in_unreg | reach_limited |
| hfd_svc_SE_s6 | 2 | ss | 537.1 (lib mid) | -537.1 | - | 90.5 | 269.9 (eo) | 163.2 (rst) | 433.1 | 220.5 | 224.7 | 118.0 | 45.2 | out_unreg min_delay | reach_limited ref_estimated spread_unmeasured |
| hgi_mtp_native | 1 | tt | 256.0 (lib mid) | -256.0 | 376.5 | 38.7 | 184.8 (t_cmdproc) | 210.1 (f_cmdproc) | 394.9 | 379.5 | 165.4 | 190.7 | 138.4 | in_unreg | reach_limited ref_estimated |
| ot_hgi_seq_au | 1 | tt | 232.6 (ins.json) | -232.6 | 399.9 | 20.5 | 213.4 (au_tbl_ok) | 169.7 (fe_s1_n) | 383.1 | 395.0 | 202.4 | 160.2 | 188.6 | - | reach_limited |
| hfd_hc_tile_xl | 352 | tt | 154.6 (lib mid) | -154.6 | 477.9 | 199.3 | 202.6 (bc_out) | -16.4 (acc_in) | 186.2 | 654.1 | 103.0 | -116.0 | 38.6 | min_delay | ref_estimated spread_unmeasured |
| ot_hbm_host_phy | 1 | tt | - (lib mid) | - | - | - | - (None) | - (None) | - | - | - | - | - | - | - |
| ot_pdie_serdes | 9 | ss | - (lib mid) | - | - | - | - (None) | - (None) | - | - | - | - | - | - | - |

## Violating tiles and the fix each needs

1. **hfd_sm** x32 [in_unreg abut min_delay] (cell / view name): input pin register missing or far: 762 bits (x, d), worst x needs 560 ps before the earliest boundary clock = 410 ps over a pin flop: first flop ~361 um (or logic) behind the pin: register at the pin; L - H = -102 ps < 100: pin hold cells at the input pin flops (finishing recipe 2)
2. **hfd_svc_SW_s3** x2 [out_unreg in_unreg abut min_delay] (cell / view name): output pin register missing or far: 2477 bits (phy, wo, eo, l4), worst phy leaves 528 ps after the latest boundary clock = 348 ps over a pin flop (logic, or ~307 um of wire, after the flop): add / move the output register to the pin; input pin register missing or far: 2 bits (rst, e), worst rst needs 940 ps before the earliest boundary clock = 790 ps over a pin flop: control / reset input fans out before its first flop: one pin register, fan-out tree behind it; L - H = -8 ps < 100: pin hold cells at the input pin flops (finishing recipe 2)
3. **hfd_svc_SE_s5** x2 [out_unreg in_unreg abut min_delay] (cell / view name): output pin register missing or far: 34 bits (phy, l6), worst phy leaves 420 ps after the latest boundary clock = 240 ps over a pin flop (logic, or ~212 um of wire, after the flop): add / move the output register to the pin; input pin register missing or far: 1 bits (rst), worst rst needs 801 ps before the earliest boundary clock = 651 ps over a pin flop: control / reset input fans out before its first flop: one pin register, fan-out tree behind it; L - H = 0 ps < 100: pin hold cells at the input pin flops (finishing recipe 2)
4. **hfd_svc_SW_s0** x2 [out_unreg in_unreg abut min_delay] (cell / view name): output pin register missing or far: 175 bits (phy, l1, l0), worst phy leaves 469 ps after the latest boundary clock = 289 ps over a pin flop (logic, or ~255 um of wire, after the flop): add / move the output register to the pin; input pin register missing or far: 1 bits (rst), worst rst needs 702 ps before the earliest boundary clock = 552 ps over a pin flop: control / reset input fans out before its first flop: one pin register, fan-out tree behind it; L - H = 23 ps < 100: pin hold cells at the input pin flops (finishing recipe 2)
5. **hfd_svc_SE_s0** x2 [out_unreg in_unreg abut min_delay] (cell / view name): output pin register missing or far: 210 bits (phy, l0, l1), worst phy leaves 518 ps after the latest boundary clock = 338 ps over a pin flop (logic, or ~298 um of wire, after the flop): add / move the output register to the pin; input pin register missing or far: 1 bits (rst), worst rst needs 651 ps before the earliest boundary clock = 501 ps over a pin flop: control / reset input fans out before its first flop: one pin register, fan-out tree behind it; L - H = 35 ps < 100: pin hold cells at the input pin flops (finishing recipe 2)
6. **hfd_svc_SE_s8** x2 [out_unreg abut min_delay] (cell / view name (1 of 4 views)): output pin register missing or far: 2 bits (phy), worst phy leaves 728 ps after the latest boundary clock = 548 ps over a pin flop (logic, or ~482 um of wire, after the flop): add / move the output register to the pin; L - H = -98 ps < 100: pin hold cells at the input pin flops (finishing recipe 2)
7. **hfd_svc_SW_s1** x2 [out_unreg in_unreg abut min_delay] (cell / view name): output pin register missing or far: 1 bits (phy), worst phy leaves 298 ps after the latest boundary clock = 118 ps over a pin flop (logic, or ~104 um of wire, after the flop): add / move the output register to the pin; input pin register missing or far: 2 bits (rst, q2), worst rst needs 301 ps before the earliest boundary clock = 151 ps over a pin flop: control / reset input fans out before its first flop: one pin register, fan-out tree behind it; L - H = -71 ps < 100: pin hold cells at the input pin flops (finishing recipe 2)
8. **hfd_svc_SE_s7** x2 [out_unreg in_unreg abut min_delay] (cell / view name (1 of 2 views)): output pin register missing or far: 550 bits (l7, phy, ks7, wo), worst l7 leaves 386 ps after the latest boundary clock = 206 ps over a pin flop (logic, or ~182 um of wire, after the flop): add / move the output register to the pin; input pin register missing or far: 1 bits (rst), worst rst needs 356 ps before the earliest boundary clock = 206 ps over a pin flop: control / reset input fans out before its first flop: one pin register, fan-out tree behind it; L - H = 44 ps < 100: pin hold cells at the input pin flops (finishing recipe 2)
9. **ot_hcoll_port** x9 [out_unreg in_unreg abut] (cell / view name): output pin register missing or far: 35 bits (rb_d, ph_tx_v, fault, stall), worst rb_d leaves 291 ps after the latest boundary clock = 111 ps over a pin flop (logic, or ~146 um of wire, after the flop): add / move the output register to the pin; input pin register missing or far: 620 bits (rst_n, ph_rx_flit, qr_din, qp_din), worst rst_n needs 416 ps before the earliest boundary clock = 266 ps over a pin flop: control / reset input fans out before its first flop: one pin register, fan-out tree behind it
10. **ot_hgi_coll_tkm_tile** x32 [out_unreg in_unreg abut] (cell / view name (1 of 3 views)): output pin register missing or far: 88 bits (up_out, tau_o), worst up_out leaves 302 ps after the latest boundary clock = 122 ps over a pin flop (logic, or ~160 um of wire, after the flop): add / move the output register to the pin; input pin register missing or far: 358 bits (ins_b, ins_v, up_in), worst ins_b needs 401 ps before the earliest boundary clock = 251 ps over a pin flop: first flop ~331 um (or logic) behind the pin: register at the pin
11. **ot_hgi_dma_back** x4 [out_unreg in_unreg spread abut] (cell / view name): output pin register missing or far: 3 bits (wd), worst wd leaves 242 ps after the latest boundary clock = 62 ps over a pin flop (logic, or ~81 um of wire, after the flop): add / move the output register to the pin; input pin register missing or far: 109 bits (vr2r, mv_v, wd_cr, mv), worst vr2r needs 287 ps before the earliest boundary clock = 137 ps over a pin flop: first flop ~180 um (or logic) behind the pin: register at the pin; boundary clock spread 186 ps > 80: put the boundary registers on one balanced sub-root (or split the root); every ps is inside o + s (1.3 um of reach per ps)
12. **ot_su12_sfu** x64 [out_unreg in_unreg] (cell / view name (1 of 6 views)): output pin register missing or far: 2 bits (kv_waddr), worst kv_waddr leaves 231 ps after the latest boundary clock = 51 ps over a pin flop (logic, or ~67 um of wire, after the flop): add / move the output register to the pin; input pin register missing or far: 1 bits (rst_n), worst rst_n needs 406 ps before the earliest boundary clock = 256 ps over a pin flop: control / reset input fans out before its first flop: one pin register, fan-out tree behind it
13. **hfd_svc_SW_s7** x2 [out_unreg min_delay] (cell / view name): output pin register missing or far: 714 bits (ks7, l7, phy, wo), worst ks7 leaves 336 ps after the latest boundary clock = 156 ps over a pin flop (logic, or ~137 um of wire, after the flop): add / move the output register to the pin; L - H = 43 ps < 100: pin hold cells at the input pin flops (finishing recipe 2)
14. **ot_hgi_seq_be** x1 [out_unreg in_unreg] (cell / view name): output pin register missing or far: 315 bits (be_jl_entry, d_desc, be_inj_hold, d_sut), worst be_jl_entry leaves 322 ps after the latest boundary clock = 142 ps over a pin flop (logic, or ~187 um of wire, after the flop): add / move the output register to the pin; input pin register missing or far: 9 bits (db_loff, cpl_rdy, hold, db_kernel), worst db_loff needs 244 ps before the earliest boundary clock = 94 ps over a pin flop: first flop ~123 um (or logic) behind the pin: register at the pin
15. **hfd_svc_SW_s4** x2 [out_unreg min_delay] (cell / view name (1 of 2 views)): output pin register missing or far: 628 bits (eo, wo), worst eo leaves 272 ps after the latest boundary clock = 92 ps over a pin flop (logic, or ~81 um of wire, after the flop): add / move the output register to the pin; L - H = 34 ps < 100: pin hold cells at the input pin flops (finishing recipe 2)
16. **ot_hdc_v41x_idx_hslice** x128 [out_unreg in_unreg] (cell / view name (1 of 8 views)): output pin register missing or far: 2 bits (ko_key), worst ko_key leaves 239 ps after the latest boundary clock = 59 ps over a pin flop (logic, or ~78 um of wire, after the flop): add / move the output register to the pin; input pin register missing or far: 2 bits (first, cs_in), worst first needs 199 ps before the earliest boundary clock = 49 ps over a pin flop: control / reset input fans out before its first flop: one pin register, fan-out tree behind it
17. **hfd_svc_SE_s6** x2 [out_unreg min_delay] (cell / view name (1 of 3 views)): output pin register missing or far: 6 bits (eo), worst eo leaves 225 ps after the latest boundary clock = 45 ps over a pin flop (logic, or ~39 um of wire, after the flop): add / move the output register to the pin; L - H = 45 ps < 100: pin hold cells at the input pin flops (finishing recipe 2)
18. **hgi_mtp_native** x1 [in_unreg] (cell / view name): input pin register missing or far: 1 bits (f_cmdproc), worst f_cmdproc needs 191 ps before the earliest boundary clock = 41 ps over a pin flop: first flop ~54 um (or logic) behind the pin: register at the pin
19. **hfd_hc_tile_xl** x352 [min_delay] (cell / view name): L - H = 39 ps < 100: pin hold cells at the input pin flops (finishing recipe 2)

Export-SDC: 7 audited cells on corrected views, 15 still pre-fix: physical/hbm_accel_die_views/hcp/tile_xl/view_hm10-pd55/view, physical/hbm_accel_die_views/mtp_hgi, physical/hbm_accel_die_views/phy_bb/ot_hbm_host_phy, physical/hbm_accel_die_views/phy_bb/ot_pdie_serdes, physical/hbm_accel_die_views/sm, physical/hbm_accel_die_views/svc/split/hfd_svc_SE_s0_tt, physical/hbm_accel_die_views/svc/split/hfd_svc_SE_s5_tt, physical/hbm_accel_die_views/svc/split/hfd_svc_SW_s0_tt, physical/hbm_accel_die_views/svc/split/hfd_svc_SW_s1_tt, physical/hbm_accel_die_views/svc/split/hfd_svc_SW_s3_tt, physical/hbm_accel_die_views/svc/split_ps/hfd_svc_SE_s6, physical/hbm_accel_die_views/svc/split_ps/hfd_svc_SE_s7, physical/hbm_accel_die_views/svc/split_ps/hfd_svc_SW_s4, physical/hbm_accel_die_views/svc/split_ps/hfd_svc_SW_s7, physical/hbm_accel_die_views/svc/split_psfc/hfd_svc_SE_s8.

Not auditable (no closed view): hfd_attn_half_hi x32, hfd_attn_half_lo x32, hfd_cmdproc x1, ot_hgi_seq_split x1, ot_hgi_seq_fe x1, hfd_coll x1, hfd_coll_tkm x1, hfd_hc x4, hfd_hc_eng x1, hfd_hgi_am x1, hfd_hgi_idx x1, hfd_hgi_vms_NE x1, hfd_hgi_vms_NW x1, hfd_hgi_vms_SE x1, hfd_hgi_vms_SW x1, hfd_host_slab x1, hfd_idx_score_native_grid x4, hfd_idx_sel_native_qend x1, hfd_lk_ep x9, hfd_loader x1, hfd_quant x1, ot_hgi_qdq_q_pin4 x1, hfd_serdes_slab x2, hfd_sfu x4, hfd_su x4, ot_hgi_sv_lane2 x64, ot_hgi_sv_head x4, hfd_svc_SE_s1 x2, hfd_svc_SE_s2 x2, hfd_svc_SE_s3 x2, hfd_svc_SE_s4 x2, hfd_svc_SW_s2 x2, hfd_svc_SW_s5 x2, hfd_svc_SW_s6 x2, hfd_vm_ne x1, hfd_vm_ne_e_t0 x1, hfd_vm_ne_e_t1 x1, hfd_vm_ne_e_t2 x1, hfd_vm_ne_e_t3 x1, hfd_vm_ne_e_t4 x1, hfd_vm_ne_e_t5 x1, hfd_vm_nw x1, hfd_vm_nw_w_t0 x1, hfd_vm_nw_w_t1 x1, hfd_vm_nw_w_t2 x1, hfd_vm_nw_w_t3 x1, hfd_vm_nw_w_t4 x1, hfd_vm_nw_w_t5 x1, hfd_vm_se x1, hfd_vm_se_e_t0 x1, hfd_vm_se_e_t1 x1, hfd_vm_se_e_t2 x1, hfd_vm_se_e_t3 x1, hfd_vm_se_e_t4 x1, hfd_vm_se_e_t5 x1, hfd_vm_se_w_t0 x1, hfd_vm_se_w_t1 x1, hfd_vm_se_w_t2 x1, hfd_vm_se_w_t3 x1, hfd_vm_se_w_t4 x1, hfd_vm_se_w_t5 x1, hfd_vm_sw x1, hfd_vm_sw_e_t0 x1, hfd_vm_sw_e_t1 x1, hfd_vm_sw_e_t2 x1, hfd_vm_sw_e_t3 x1, hfd_vm_sw_e_t4 x1, hfd_vm_sw_e_t5 x1, hfd_vm_sw_w_t0 x1, hfd_vm_sw_w_t1 x1, hfd_vm_sw_w_t2 x1, hfd_vm_sw_w_t3 x1, hfd_vm_sw_w_t4 x1, hfd_vm_sw_w_t5 x1, ot_hbm3e_phy_v41x_aw30_e8p5 x4

## Hops over 500 um: 3197 (1617680 bits; 2000 data, 1197 unrelayed reset nets), max 4885.6 um

Source: case /tmp/claude-1000/hbmdie12/case_v12 branch claude/hbm-native-die-1013 + generator sha256 d3ca85bdf00558aa r25gqn_v12 PYTHONHASHSEED=0 tools/hbm_accel_die_fp.py grt --k 16 --iters 12 --m45 0.5 --ds-var r25gqn_v12; 39243 instances, 23792 data hops; contract slots placed as the contract 194 / 888.

| class | hops | bits | max um | masters |
|---|---:|---:|---:|---|
| n_rl_sm# | 25 | 6800 | 4885.6 | hfd_gath_r25, hfd_gath_r8, hfd_gath_r9, hfd_sm, hfd_stn_q270E, hfd_stn_q270N |
| n_xl_sm#_t# | 1 | 2064 | 4731.6 | hfd_sm, hfd_stn_qxl2158 |
| n_xl_sm#_t#_r# | 1 | 2064 | 4563.1 | hfd_sm, hfd_stn_qxl5494 |
| n_xl_sm# | 11 | 22704 | 4457.3 | hfd_mcast_r5, hfd_mcast_r7, hfd_sm, hfd_stn_qxl2158, hfd_stn_qxl5404, hfd_stn_qxl5600 |
| n_xl_sm#a | 14 | 14336 | 4299.6 | hfd_mcast_r6a, hfd_sm, hfd_stn_q1024E, hfd_stn_q1024N, hfd_stn_q1024W |
| n_xl_sm#b_t# | 11 | 11440 | 4283.9 | hfd_sm, hfd_stn_q1039E, hfd_stn_q1039N, hfd_stn_q1039S, hfd_stn_q1039W |
| n_xl_sm#b | 13 | 13520 | 4249.4 | hfd_mcast_r6b, hfd_sm, hfd_stn_q1039E, hfd_stn_q1039N, hfd_stn_q1039W |
| n_lkp_S# | 1 | 976 | 4243.3 | hfd_lk_ep, ot_pdie_serdes |
| n_xl_sm#a_t# | 14 | 14336 | 4201.1 | hfd_sm, hfd_stn_q1024E, hfd_stn_q1024N, hfd_stn_q1024S, hfd_stn_q1024W |
| n_xl_sm#b_r# | 5 | 5200 | 4178.1 | hfd_sm, hfd_stn_q1039N, hfd_stn_q1039S |
| n_xl_sm#a_t#_r# | 4 | 4096 | 4173.4 | hfd_sm, hfd_stn_q1024E, hfd_stn_q1024N, hfd_stn_q1024S |
| n_xl_sm#b_t#_r# | 3 | 3120 | 4158.5 | hfd_sm, hfd_stn_q1039S, hfd_stn_q1039W |
| n_xl_sm#a_r# | 2 | 2048 | 3967.9 | hfd_sm, hfd_stn_q1024N |
| n_cl_sm# | 22 | 2464 | 3689.4 | hfd_cdist_r45, hfd_cdist_r46, hfd_sm, hfd_stn_q112E, hfd_stn_q112N, hfd_stn_q112W |
| n_cl_sm#_t#_r# | 5 | 560 | 3679.4 | hfd_sm, hfd_stn_q112E, hfd_stn_q112N, hfd_stn_q112S, hfd_stn_q112W |
| n_cl_sm#_t# | 6 | 672 | 3651.3 | hfd_sm, hfd_stn_q112E, hfd_stn_q112W |
| n_lk_lk_S#_e_t#_r# | 1 | 1120 | 3625.6 | hfd_lk_ep, hfd_stn_q1120N |
| n_idx_score_NE_# | 2 | 1248 | 3620.0 | hfd_idx_score_native_grid, hfd_stn_868, hfd_stn_q610S, hfd_stn_q612S |
| n_lkp_N# | 2 | 1952 | 3483.2 | hfd_lk_ep, ot_pdie_serdes |
| n_hb_vm_su_NE_t# | 1 | 2048 | 3438.4 | hfd_stn_qhb4171, hfd_su |
| n_hb_vm_su_NW_t# | 1 | 2048 | 3417.3 | hfd_stn_qhb4144, hfd_su |
| n_idx_query_NE_e_t#_r# | 1 | 576 | 3391.3 | hfd_idx_score_native_grid, hfd_stn_q571N |
| n_idx_score_credit_NE_e_t#_r# | 1 | 16 | 3322.4 | hfd_idx_score_native_grid, hfd_stn_q1N |
| n_hb_su_NW_vm | 1 | 2048 | 3265.3 | hfd_stn_qhb4145, hfd_su |
| n_hb_su_NE_vm | 1 | 2048 | 3264.8 | hfd_stn_qhb4172, hfd_su |
| n_lkp_S#_# | 6 | 5856 | 3227.6 | hfd_lk_ep, hfd_stn_q974, ot_pdie_serdes |
| n_hc_fused_ne_#_r# | 1 | 160 | 3224.6 | hfd_hc_eng, hfd_stn_q151S |
| n_lk_lk_N#_e_t# | 3 | 3360 | 3203.6 | hfd_lk_ep, hfd_stn_q1120E |
| n_xl_sm#_r# | 3 | 6192 | 3196.7 | hfd_sm, hfd_stn_qxl5403, hfd_stn_qxl5404, hfd_stn_qxl5600 |
| n_wl_sm# | 16 | 17664 | 3115.9 | hfd_sm, hfd_stn_q1099W, hfd_svc_SE_s0, hfd_svc_SE_s2, hfd_svc_SE_s4, hfd_svc_SE_s7 |
| n_lk_lk_N#_e_r# | 1 | 1120 | 3046.8 | hfd_lk_ep, hfd_stn_q1120E |
| n_lkp_N#_# | 4 | 3904 | 3045.4 | hfd_lk_ep, hfd_stn_q974, hfd_stn_q974W, ot_pdie_serdes |
| n_vrc_hce_rdn_#_r# | 1 | 2080 | 2987.4 | hfd_hc_eng, hfd_stn_qvrc6196 |
| n_lk_lk_S#_e | 3 | 3360 | 2973.3 | hfd_lk_ep, hfd_meso_r28, hfd_stn_q1120W |
| n_rq_sm# | 16 | 768 | 2890.1 | hfd_sm, hfd_stn_q44E, hfd_stn_q44N, hfd_svc_SE_s0, hfd_svc_SE_s2, hfd_svc_SE_s4 |
| n_hgi_vmq_coll | 1 | 352 | 2758.3 | hfd_coll, hfd_hgi_vms_SW |
| n_idx_query_NW_e_t#_r# | 1 | 576 | 2652.1 | hfd_idx_score_native_grid, hfd_stn_q571N |
| n_rst_link_rr_link_# | 58 | 928 | 2639.2 | hfd_lk_ep, hfd_rrl, hfd_stn_q1120E |
| n_rst_stream_rr_stream_# | 957 | 15312 | 2621.2 | hfd_attn_half_lo, hfd_cdist_r45, hfd_cdist_r46, hfd_gath_r10, hfd_gath_r24, hfd_gath_r25 |
| n_cl_sm#_r# | 6 | 672 | 2620.7 | hfd_sm, hfd_stn_q112N, hfd_stn_q112S, hfd_stn_q112W |
