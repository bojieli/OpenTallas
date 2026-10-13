# Pin-register audit: qwen_rom_tp8 (contract v4, f43c2d3cc)

> **TILE VERDICTS SUPERSEDED (10-13 09:10, el1013-pinreg-audit.log):** `out_over` / `in_over` here judge each side against 0.2 T = 166.7 ps, which is the share the sign-off SDC gives the OUTSIDE, not the tile. The die statement is the pair equation with insertion-compensated clock entry: see `qwen_rom_tp8_compensated.md`, `s81_compensated.md`, `ranked_compensated.md`. The hop tables (> 500 um) and the min-delay / combinational columns stand.

Rule: clock->pin and pin->flop each <= 166.7 ps (0.2 T), hop <= 500 um, L - H >= 100 ps (50 + skew 50).

**PROVISIONAL: 6 of 13 audited views carry no corrected-export record (reexport_1013 / verdict check) after the export-SDC fix (abc334b14); their boundary numbers may be off by tens of ps**

Cells 44: audited 13 (1004 instances), violating 13 {'out_over': 12, 'in_over': 9, 'min_delay': 1}, not auditable 31 (1065 instances), alias-bound 4.

| # | cell | inst | corner | flags | comb bits | out > B bits | worst out ps (bus) | in > B bits | worst in ps (bus) | L min | H max | L-H | binding |
|---|---|---:|---|---|---:|---:|---|---:|---|---:|---:|---:|---|
| 1 | qkd_ectl | 32 | tt | out_over in_over | 0 | 2276 | 427.2 (req_t) | 455 | 427.3 (exp_done) | 77.0 | -56.1 | 133.1 | ALIAS (same-family master, candidate only) |
| 2 | qfd_io_serdes | 3 | tt | out_over in_over | 0 | 1012 | 408.3 (tx_flit) | 2071 | 346.4 (r_cr) | 60.8 | -100.5 | 161.3 | bind map |
| 3 | qfd_su_cbuf_g | 8 | tt | out_over in_over | 0 | 717 | 221.9 (f_addr) | 502 | 380.7 (grp) | 110.8 | -63.8 | 174.6 | bind map |
| 4 | qkd_kvwq_leaf_s_w129_m | 128 | tt | out_over in_over | 0 | 585 | 231.1 (w) | 49 | 365.5 (lane) | 115.2 | -63.9 | 179.1 | cell / view name (1 of 2 views) |
| 5 | qfd_tt_up4 | 1 | tt | out_over in_over | 0 | 298 | 189.9 (tt_ty) | 9 | 349.5 (rst_n) | 106.5 | -66.8 | 173.3 | ALIAS (same-family master, candidate only) |
| 6 | qfd_tt_up4_g | 3 | tt | out_over in_over | 0 | 298 | 189.9 (tt_ty) | 9 | 349.5 (rst_n) | 106.5 | -66.8 | 173.3 | ALIAS (same-family master, candidate only) |
| 7 | qkd_kvwq_ctl_bin | 4 | tt | out_over | 0 | 141 | 318.8 (fault) | 0 | 139.5 (kvw_t) | 87.3 | -41.2 | 128.5 | ALIAS (same-family master, candidate only) |
| 8 | qfd_crom_g | 8 | tt | out_over in_over | 0 | 152 | 212.1 (crom_q) | 206 | 242.2 (crom_re) | 95.2 | -105.7 | 200.9 | bind map |
| 9 | qfd_cst_n | 384 | tt | out_over | 0 | 333 | 197.2 (a_d) | 0 | 162.5 (b_d) | 87.8 | -56.9 | 144.7 | cell / view name |
| 10 | qfd_chead_e | 24 | tt | out_over in_over | 0 | 438 | 192.3 (e_d) | 17 | 186.6 (w_d) | 100.8 | -56.6 | 157.4 | cell / view name |
| 11 | qfd_chead_w | 24 | tt | out_over in_over | 0 | 415 | 191.0 (w_d) | 13 | 184.9 (e_d) | 93.5 | -58.9 | 152.4 | cell / view name |
| 12 | qfd_cst_s | 384 | tt | out_over | 0 | 321 | 189.7 (tap_d) | 0 | 161.0 (a_d) | 98.2 | -53.3 | 151.5 | cell / view name |
| 13 | ot_qfd_serdes_112g_x12_phy | 1 | tt | min_delay | 0 | 0 | 117.3 (tx_up) | 0 | 143.5 (tx_v) | 90.5 | 58.6 | 31.9 | cell / view name |

Export-SDC: 7 audited cells on corrected views, 6 still pre-fix: physical/qwen_die_masters/views/qfd_crom_g_a, physical/qwen_die_masters/views/qfd_io_serdes_rxd512, physical/qwen_die_masters/views/qfd_su_cbuf_g_b, physical/qwen_die_masters/views/qkd_ectl_b, physical/qwen_die_masters/views/qkd_kvwq_ctl_bin_h, physical/qwen_missing_phy/ot_qfd_serdes_112g_x12_phy.

Not auditable (no closed view): ot_hbm3e_phy x4, qfd_clkrx x1, qfd_io_collective x1, qfd_io_ucie x1, qfd_io_xfifo x1, qfd_port_tiles_0 x1, qfd_port_tiles_0_f1 x1, qfd_port_tiles_1 x1, qfd_port_tiles_1_f1 x1, qfd_port_tiles_2 x1, qfd_port_tiles_2_f1 x1, qfd_seq_su x1, qfd_sp_band_lanes x3, qfd_sp_res_ser x3, qfd_sp_su64_sfu x1, qfd_sp_vector_memory x1, qfd_tile_nk x768, qfd_tt_ctlm x1, qkd_ahub x1, qkd_astk x2, qkd_astk_n x2, qkd_cdc_wleaf x128, qkd_ctrl x2, qkd_ctrl_n x2, qkd_embgw x1, qkd_host x1, qkd_land x2, qkd_land_n x2, qkd_pll x1, qkd_rhead x128, qkd_seq x1

## Hops: no die case given (contract carries placement but no nets)
