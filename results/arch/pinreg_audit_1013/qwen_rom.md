# Pin-register audit: qwen_rom (contract v6, c23342b9f)

> **TILE VERDICTS SUPERSEDED (10-13 09:10, el1013-pinreg-audit.log):** `out_over` / `in_over` here judge each side against 0.2 T = 166.7 ps, which is the share the sign-off SDC gives the OUTSIDE, not the tile. The die statement is the pair equation with insertion-compensated clock entry: see `qwen_rom_tp8_compensated.md`, `s81_compensated.md`, `ranked_compensated.md`. The hop tables (> 500 um) and the min-delay / combinational columns stand.

Rule: clock->pin and pin->flop each <= 166.7 ps (0.2 T), hop <= 500 um, L - H >= 100 ps (50 + skew 50).

**PROVISIONAL: 10 of 10 audited views were exported before the export-SDC fix (abc334b14); their boundary numbers may be off by tens of ps**

Cells 36: audited 10 (1622 instances), violating 10 {'out_over': 7, 'in_over': 5, 'min_delay': 5}, not auditable 26 (1571 instances), alias-bound 6.

| # | cell | inst | corner | flags | comb bits | out > B bits | worst out ps (bus) | in > B bits | worst in ps (bus) | L min | H max | L-H | binding |
|---|---|---:|---|---|---:|---:|---|---:|---|---:|---:|---:|---|
| 1 | qfd_d2d_rom | 1 | tt | out_over in_over | 0 | 173 | 399.4 (fault_cause) | 1531 | 451.9 (rx_flit) | 73.3 | -73.0 | 146.3 | bind map |
| 2 | qfd_su_cbuf_g | 8 | tt | out_over in_over | 0 | 717 | 221.9 (f_addr) | 502 | 380.7 (grp) | 110.8 | -63.8 | 174.6 | bind map |
| 3 | qfd_tt_up4 | 1 | tt | out_over in_over | 0 | 298 | 189.9 (tt_ty) | 2 | 311.6 (rst_n) | 106.5 | -31.1 | 137.6 | ALIAS (same-family master, candidate only) |
| 4 | qfd_tt_up4_g | 3 | tt | out_over in_over | 0 | 298 | 189.9 (tt_ty) | 2 | 311.6 (rst_n) | 106.5 | -31.1 | 137.6 | ALIAS (same-family master, candidate only) |
| 5 | qfd_crom_g | 8 | tt | out_over in_over | 0 | 152 | 212.1 (crom_q) | 206 | 242.2 (crom_re) | 95.2 | -105.7 | 200.9 | bind map |
| 6 | qfd_chead_e | 32 | tt | out_over min_delay | 0 | 2 | 180.4 (c_d) | 0 | 101.3 (a_d) | 79.7 | -6.7 | 86.4 | ALIAS (same-family master, candidate only) |
| 7 | qfd_chead_w | 32 | tt | out_over min_delay | 0 | 2 | 180.4 (c_d) | 0 | 101.3 (a_d) | 79.7 | -6.7 | 86.4 | ALIAS (same-family master, candidate only) |
| 8 | ot_qkvd_ucie_x64_phy | 1 | tt | min_delay | 0 | 0 | 117.3 (tx_up) | 0 | 143.5 (tx_v) | 90.5 | 58.6 | 31.9 | cell / view name |
| 9 | qfd_cst_n | 768 | tt | min_delay | 0 | 0 | 151.5 (t_d) | 0 | 95.4 (a_d) | 72.2 | -13.3 | 85.5 | ALIAS (same-family master, candidate only) |
| 10 | qfd_cst_s | 768 | tt | min_delay | 0 | 0 | 151.5 (t_d) | 0 | 95.4 (a_d) | 72.2 | -13.3 | 85.5 | ALIAS (same-family master, candidate only) |

Not auditable (no closed view): qfd_ckbump x1, qfd_clkrx x1, qfd_io_collective x1, qfd_io_serdes x1, qfd_io_ucie x1, qfd_io_xfifo x1, qfd_port_tiles_0 x1, qfd_port_tiles_0_f1 x1, qfd_port_tiles_1 x1, qfd_port_tiles_1_f1 x1, qfd_port_tiles_2 x1, qfd_port_tiles_2_f1 x1, qfd_port_tiles_3 x1, qfd_port_tiles_3_f1 x1, qfd_port_tiles_4 x1, qfd_port_tiles_4_f1 x1, qfd_port_tiles_5 x1, qfd_port_tiles_5_f1 x1, qfd_rstsync x1, qfd_seq_su x1, qfd_sp_band_lanes x6, qfd_sp_res_ser x6, qfd_sp_su64_sfu x1, qfd_sp_vector_memory x1, qfd_tile_nk x1536, qfd_tt_ctlm x1

## Hops over 500 um: 1 (1024 bits; 1 data, 0 unrelayed reset nets), max 500.3 um

Source: case /tmp/claude-1000/qd1011/e8/case 6974c79ec --recipe r22ko4 --pdn-rev r5; 13089 instances, 16177 data hops; contract slots placed as the contract 3193 / 3193.

| class | hops | bits | max um | masters |
|---|---:|---:|---:|---|
| n_serdes_rx__r# | 1 | 1024 | 500.3 | qfd_io_xfifo, qfd_rly_1024_EW_53x60 |
