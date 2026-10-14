# Pin-register audit: qwen_rom_tp8 (contract v4, d96a0510a)

Rule (die statement): the die delivers the clock to each tile's clock pin at `phi - R` (R = mean insertion of the tile's boundary registers, the sign-off reference); a hop A -> B of L um needs `o_A + 0.76 L + s_B <= 833.3 - 60 - 90 = 683.3 ps` (o = clk->pin - R, s = setup@pin + R). Per tile C = o + s and reach = (683.3 - C) / 0.76 against its own kind; the per-side share at 500 um is 151.7 ps. The sign-off SDC (IO 0.2 T outside) proves only o, s <= 516.7 ps each. Hold: L - H >= 100 ps (50 + skew 50).

**PROVISIONAL: 1 of 13 audited views carry no corrected-export record (reexport_1013 / verdict check) after the export-SDC fix (abc334b14); their boundary numbers may be off by tens of ps**

Cells 43: audited 13 (1129 instances); VIOLATING 9 {'out_unreg': 4, 'in_unreg': 8, 'abut': 4, 'min_delay': 1}; reach-limited only 8; clean 0; reference estimated (no insertion.json) 4; not auditable 30 (937 instances); alias-bound 2.

## Die clock delivery

R spans 111.6 (qfd_chead_w) .. 570.2 (qfd_io_serdes) ps at TT = 458.6 ps. Compensated entry: each branch carries R_max - R of added delay; OCV 5% on the non-shared 570.2 ps a side = 57.0 ps of the 90 ps die skew on EVERY hop; FF/TT tracking of R 0.801..0.849 = 22.0 ps over the span.

Worst potential pair, setup (available 683.3 ps before wire): compensated 918.4 ps (qkd_kvwq_ctl_bin -> qkd_cdc_wleaf, wire left -235.1); COMMON-phase entry 1177.6 ps (qfd_io_serdes -> qkd_kvwq_leaf_s_w129_m, wire left -494.3). Hold (need 100): compensated 117.1 ps (qfd_io_serdes -> qfd_su_cbuf_g); common phase -184.3 ps (qfd_cst_n -> qfd_io_serdes).

## Tiles (all audited, worst reach first)

| cell | inst | corner | R ps (src) | clock entry vs phi | + branch delay | boundary spread | o ps (bus) | s ps (bus) | C = o+s | reach um | q_lb | p_lb | L-H | flags | notes |
|---|---:|---|---|---:|---:|---:|---|---|---:|---:|---:|---:|---:|---|---|
| qkd_kvwq_ctl_bin | 4 | tt | 379.2 (ins.json) | -379.2 | 191.0 | 64.6 | 464.7 (f0) | 423.7 (rst_n) | 888.4 | -269.8 | 415.5 | 408.3 | 200.4 | out_unreg in_unreg abut | - |
| qkd_ectl | 32 | tt | 436.2 (lib mid) | -436.2 | 134.0 | 52.3 | 427.2 (req_t) | 427.3 (exp_done) | 854.5 | -225.2 | 401.1 | 401.2 | 133.1 | out_unreg in_unreg abut | ref_estimated |
| qkd_cdc_wleaf | 128 | tt | 278.5 (ins.json) | -278.5 | 291.7 | 45.4 | 382.8 (l_data) | 453.7 (h_hand) | 836.5 | -201.5 | 355.1 | 442.3 | 183.8 | out_unreg in_unreg abut | - |
| qfd_io_serdes | 3 | tt | 570.2 (lib mid) | -570.2 | 0.0 | 155.3 | 415.6 (tx_flit) | 339.1 (r_cr) | 754.7 | -93.9 | 338.0 | 261.5 | 161.3 | out_unreg in_unreg abut | ref_estimated spread_unmeasured |
| qfd_su_cbuf_g | 8 | tt | 275.0 (lib mid) | -275.0 | 295.2 | 44.4 | 221.9 (f_addr) | 380.7 (grp) | 602.6 | 106.2 | 199.7 | 358.5 | 161.2 | in_unreg | reach_limited ref_estimated |
| qkd_kvwq_leaf_s_w129_m | 128 | tt | 173.7 (ins.json) | -173.7 | 396.5 | 27.9 | 231.1 (w) | 365.5 (lane) | 596.6 | 114.1 | 219.2 | 349.5 | 179.1 | in_unreg | reach_limited |
| qfd_tt_up4 | 1 | tt | 203.7 (ins.json) | -203.7 | 366.5 | 31.0 | 185.7 (tt_ty) | 353.6 (rst_n) | 539.3 | 189.5 | 168.9 | 339.4 | 173.3 | in_unreg | reach_limited |
| qfd_crom_g | 8 | tt | 343.3 (lib mid) | -343.3 | 226.9 | 82.4 | 212.1 (crom_q) | 242.2 (crom_re) | 454.3 | 301.4 | 170.9 | 201.0 | 200.9 | in_unreg | reach_limited ref_estimated spread_unmeasured |
| qfd_chead_e | 24 | tt | 115.6 (ins.json) | -115.6 | 454.6 | 14.4 | 192.3 (e_d) | 186.6 (w_d) | 378.9 | 400.6 | 186.9 | 177.6 | 157.4 | - | reach_limited |
| qfd_chead_w | 24 | tt | 111.6 (ins.json) | -111.6 | 458.6 | 17.4 | 191.0 (w_d) | 184.9 (e_d) | 375.9 | 404.5 | 181.1 | 177.4 | 152.4 | - | reach_limited |
| qfd_cst_n | 384 | tt | 115.8 (ins.json) | -115.8 | 454.4 | 13.4 | 197.2 (a_d) | 162.5 (b_d) | 359.7 | 425.8 | 191.3 | 155.0 | 144.7 | - | reach_limited |
| qfd_cst_s | 384 | tt | 119.2 (ins.json) | -119.2 | 451.0 | 22.0 | 189.7 (tap_d) | 161.0 (a_d) | 350.7 | 437.7 | 177.8 | 150.9 | 151.5 | - | reach_limited |
| ot_qfd_serdes_112g_x12_phy | 1 | tt | - (lib mid) | - | - | - | 117.3 (tx_up) | 143.5 (tx_v) | 260.8 | 556.0 | 117.3 | 143.5 | 31.9 | min_delay | - |

## Violating tiles and the fix each needs

1. **qkd_kvwq_ctl_bin** x4 [out_unreg in_unreg abut] (cell / view name): output pin register missing or far: 785 bits (f0, f1, f3, f2), worst f0 leaves 416 ps after the latest boundary clock = 236 ps over a pin flop (logic, or ~310 um of wire, after the flop): add / move the output register to the pin; input pin register missing or far: 1 bits (rst_n), worst rst_n needs 408 ps before the earliest boundary clock = 258 ps over a pin flop: control / reset input fans out before its first flop: one pin register, fan-out tree behind it
2. **qkd_ectl** x32 [out_unreg in_unreg abut] (ALIAS (same-family master, candidate only)): output pin register missing or far: 49 bits (req_t, req_valid, req_v, sc_addr), worst req_t leaves 401 ps after the latest boundary clock = 221 ps over a pin flop (logic, or ~291 um of wire, after the flop): add / move the output register to the pin; input pin register missing or far: 73 bits (exp_done, q_beat_in, t_gf, rsp_data_in), worst exp_done needs 401 ps before the earliest boundary clock = 251 ps over a pin flop: first flop ~331 um (or logic) behind the pin: register at the pin
3. **qkd_cdc_wleaf** x128 [out_unreg in_unreg abut] (cell / view name): output pin register missing or far: 258 bits (l_data, h_cdata, wd_tag, l_sec), worst l_data leaves 355 ps after the latest boundary clock = 175 ps over a pin flop (logic, or ~230 um of wire, after the flop): add / move the output register to the pin; input pin register missing or far: 2 bits (h_hand, h_wcon), worst h_hand needs 442 ps before the earliest boundary clock = 292 ps over a pin flop: first flop ~385 um (or logic) behind the pin: register at the pin
4. **qfd_io_serdes** x3 [out_unreg in_unreg abut] (bind map): output pin register missing or far: 513 bits (tx_flit, r_v), worst tx_flit leaves 338 ps after the latest boundary clock = 158 ps over a pin flop (logic, or ~208 um of wire, after the flop): add / move the output register to the pin; input pin register missing or far: 96 bits (r_cr, c_d, rx_flit, c_v), worst r_cr needs 262 ps before the earliest boundary clock = 112 ps over a pin flop: first flop ~147 um (or logic) behind the pin: register at the pin
5. **qfd_su_cbuf_g** x8 [in_unreg] (bind map): input pin register missing or far: 16 bits (grp, f_fault, f_q), worst grp needs 358 ps before the earliest boundary clock = 208 ps over a pin flop: first flop ~274 um (or logic) behind the pin: register at the pin
6. **qkd_kvwq_leaf_s_w129_m** x128 [in_unreg] (cell / view name (1 of 2 views)): input pin register missing or far: 5 bits (lane, dn), worst lane needs 350 ps before the earliest boundary clock = 200 ps over a pin flop: first flop ~262 um (or logic) behind the pin: register at the pin
7. **qfd_tt_up4** x1 [in_unreg] (ALIAS (same-family master, candidate only)): input pin register missing or far: 2 bits (rst_n, pw), worst rst_n needs 339 ps before the earliest boundary clock = 189 ps over a pin flop: control / reset input fans out before its first flop: one pin register, fan-out tree behind it
8. **qfd_crom_g** x8 [in_unreg] (bind map): input pin register missing or far: 9 bits (crom_re, crom_addr), worst crom_re needs 201 ps before the earliest boundary clock = 51 ps over a pin flop: first flop ~67 um (or logic) behind the pin: register at the pin
9. **ot_qfd_serdes_112g_x12_phy** x1 [min_delay] (cell / view name): L - H = 32 ps < 100: pin hold cells at the input pin flops (finishing recipe 2)

Export-SDC: 12 audited cells on corrected views, 1 still pre-fix: physical/qwen_missing_phy/ot_qfd_serdes_112g_x12_phy.

Not auditable (no closed view): ot_hbm3e_phy x4, qfd_clkrx x1, qfd_io_collective x1, qfd_io_ucie x1, qfd_io_xfifo x1, qfd_port_tiles_0 x1, qfd_port_tiles_0_f1 x1, qfd_port_tiles_1 x1, qfd_port_tiles_1_f1 x1, qfd_port_tiles_2 x1, qfd_port_tiles_2_f1 x1, qfd_seq_su x1, qfd_sp_band_lanes x3, qfd_sp_res_ser x3, qfd_sp_su64_sfu x1, qfd_sp_vector_memory x1, qfd_tile_nk x768, qfd_tt_ctlm x1, qkd_ahub x1, qkd_astk x2, qkd_astk_n x2, qkd_ctrl x2, qkd_ctrl_n x2, qkd_embgw x1, qkd_host x1, qkd_land x2, qkd_land_n x2, qkd_pll x1, qkd_rhead x128, qkd_seq x1

## Hops: no die case given (contract carries placement but no nets)
