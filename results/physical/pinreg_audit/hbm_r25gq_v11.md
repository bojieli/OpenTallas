# Pin-register audit: hbm_r25gq (contract v11, 01d5f16d9)

Rule: clock->pin and pin->flop each <= 166.7 ps (0.2 T), hop <= 500 um, L - H >= 100 ps (50 + skew 50).

**PROVISIONAL: 17 of 17 audited views were exported before the export-SDC fix (abc334b14); their boundary numbers may be off by tens of ps**

Cells 86: audited 17 (607 instances), violating 15 {'out_over': 15, 'in_over': 13, 'min_delay': 13}, not auditable 69 (162 instances), alias-bound 0.

| # | cell | inst | corner | flags | comb bits | out > B bits | worst out ps (bus) | in > B bits | worst in ps (bus) | L min | H max | L-H | binding |
|---|---|---:|---|---|---:|---:|---|---:|---|---:|---:|---:|---|
| 1 | hfd_sm | 32 | ss | out_over in_over min_delay | 0 | 31 | 624.4 (r) | 3262 | 1112.5 (x) | -170.7 | -68.8 | -101.9 | cell / view name |
| 2 | hfd_svc_SW_s3 | 2 | ss | out_over in_over min_delay | 0 | 2979 | 652.5 (phy) | 1678 | 1063.9 (rst) | -5.7 | 2.8 | -8.5 | cell / view name |
| 3 | hfd_svc_SE_s5 | 2 | ss | out_over in_over min_delay | 0 | 1995 | 531.5 (phy) | 962 | 912.1 (rst) | 1.9 | 1.5 | 0.4 | cell / view name |
| 4 | hfd_svc_SE_s8 | 2 | ss | out_over in_over min_delay | 0 | 53 | 898.0 (phy) | 85 | 310.5 (wi) | 0.8 | 98.7 | -97.9 | cell / view name (1 of 4 views) |
| 5 | hfd_svc_SW_s0 | 2 | ss | out_over in_over min_delay | 0 | 2872 | 538.7 (phy) | 3 | 771.8 (rst) | 33.6 | 10.6 | 23.0 | cell / view name |
| 6 | hfd_svc_SE_s0 | 2 | ss | out_over in_over min_delay | 0 | 2872 | 580.9 (phy) | 7 | 714.0 (rst) | 41.9 | 7.1 | 34.8 | cell / view name |
| 7 | hfd_svc_SW_s1 | 2 | ss | out_over in_over min_delay | 0 | 1115 | 523.8 (phy) | 1551 | 526.1 (rst) | -69.9 | 1.2 | -71.1 | cell / view name |
| 8 | hfd_svc_SE_s7 | 2 | ss | out_over in_over min_delay | 0 | 2112 | 419.4 (l7) | 2 | 388.6 (rst) | 59.7 | 15.4 | 44.3 | cell / view name (1 of 2 views) |
| 9 | ot_su12_sfu | 64 | tt | out_over in_over min_delay | 0 | 28 | 249.9 (kv_waddr) | 1 | 380.8 (rst_n) | 86.6 | -9.9 | 96.5 | cell / view name (1 of 6 views) |
| 10 | hfd_svc_SW_s7 | 2 | ss | out_over in_over min_delay | 0 | 1970 | 370.9 (ks7) | 1 | 224.4 (rst) | 58.0 | 15.2 | 42.8 | cell / view name |
| 11 | hfd_svc_SW_s4 | 2 | ss | out_over in_over min_delay | 0 | 1870 | 343.4 (eo) | 144 | 183.6 (wi) | 22.6 | -11.7 | 34.3 | cell / view name (1 of 2 views) |
| 12 | hfd_svc_SE_s6 | 2 | ss | out_over min_delay | 0 | 1240 | 269.9 (eo) | 0 | 163.2 (rst) | 48.3 | 3.1 | 45.2 | cell / view name (1 of 3 views) |
| 13 | ot_hdc_v41x_idx_hslice | 128 | tt | out_over in_over | 0 | 468 | 217.8 (ko_key) | 1 | 168.3 (cs_in) | 80.3 | -41.8 | 122.1 | cell / view name (1 of 7 views) |
| 14 | hgi_mtp_native | 1 | tt | out_over in_over | 0 | 44 | 184.8 (t_cmdproc) | 18 | 210.1 (f_cmdproc) | 90.4 | -48.0 | 138.4 | cell / view name |
| 15 | hfd_hc_tile_xl | 352 | tt | out_over min_delay | 0 | 338 | 202.6 (bc_out) | 0 | -16.4 (acc_in) | 39.6 | 1.0 | 38.6 | cell / view name |

Not auditable (no closed view): hfd_attn_half_hi x32, hfd_attn_half_lo x32, hfd_cmdproc x1, hfd_coll x1, hfd_hc x4, hfd_hc_eng x1, hfd_hgi_am x1, hfd_hgi_idx x1, hfd_hgi_vms_NE x1, hfd_hgi_vms_NW x1, hfd_hgi_vms_SE x1, hfd_hgi_vms_SW x1, hfd_host_slab x1, hfd_idx_score_native_grid x4, hfd_idx_sel_native_qend x1, hfd_lk_ep x9, hfd_loader x1, hfd_quant x1, hfd_serdes_slab x2, hfd_sfu x4, hfd_su x4, hfd_svc_SE_s1 x2, hfd_svc_SE_s2 x2, hfd_svc_SE_s3 x2, hfd_svc_SE_s4 x2, hfd_svc_SW_s2 x2, hfd_svc_SW_s5 x2, hfd_svc_SW_s6 x2, hfd_vm_ne x1, hfd_vm_ne_e_t0 x1, hfd_vm_ne_e_t1 x1, hfd_vm_ne_e_t2 x1, hfd_vm_ne_e_t3 x1, hfd_vm_ne_e_t4 x1, hfd_vm_ne_e_t5 x1, hfd_vm_nw x1, hfd_vm_nw_w_t0 x1, hfd_vm_nw_w_t1 x1, hfd_vm_nw_w_t2 x1, hfd_vm_nw_w_t3 x1, hfd_vm_nw_w_t4 x1, hfd_vm_nw_w_t5 x1, hfd_vm_se x1, hfd_vm_se_e_t0 x1, hfd_vm_se_e_t1 x1, hfd_vm_se_e_t2 x1, hfd_vm_se_e_t3 x1, hfd_vm_se_e_t4 x1, hfd_vm_se_e_t5 x1, hfd_vm_se_w_t0 x1, hfd_vm_se_w_t1 x1, hfd_vm_se_w_t2 x1, hfd_vm_se_w_t3 x1, hfd_vm_se_w_t4 x1, hfd_vm_se_w_t5 x1, hfd_vm_sw x1, hfd_vm_sw_e_t0 x1, hfd_vm_sw_e_t1 x1, hfd_vm_sw_e_t2 x1, hfd_vm_sw_e_t3 x1, hfd_vm_sw_e_t4 x1, hfd_vm_sw_e_t5 x1, hfd_vm_sw_w_t0 x1, hfd_vm_sw_w_t1 x1, hfd_vm_sw_w_t2 x1, hfd_vm_sw_w_t3 x1, hfd_vm_sw_w_t4 x1, hfd_vm_sw_w_t5 x1, ot_hbm3e_phy_v41x_aw30_e8p5 x4

## Hops: no die case given (contract carries placement but no nets)
