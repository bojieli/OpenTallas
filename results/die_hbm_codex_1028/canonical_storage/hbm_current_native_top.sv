// Generated current native composition candidate. FAIL_CLOSED until native obligations bind.
`default_nettype none
module hbm_current_native_top (hb_ckgen__por_n, hb_ckgen__refclk, hb_dbk_SE__rq, hb_dbk_SW__rq, hcollks_SE_p0__vm_kq, hcollks_SE_p1__vm_kq, hcollks_SE_p2__vm_kq, hcollks_SE_p3__vm_kq, hcollks_SW_p0__vm_kq, hcollks_SW_p1__vm_kq, hcollks_SW_p2__vm_kq, hcollks_SW_p3__vm_kq, hcollrs_SE__vm_rq, hcollrs_SW__vm_rq, hleaf_SE__a_cfg_addr, hleaf_SE__a_cfg_data, hleaf_SE__a_cfg_target, hleaf_SE__a_cfg_v, hleaf_SE__a_desc_base, hleaf_SE__a_desc_limit, hleaf_SE__a_desc_loops, hleaf_SE__a_desc_v, hleaf_SE__a_launch_v, hleaf_SW__a_cfg_addr, hleaf_SW__a_cfg_data, hleaf_SW__a_cfg_target, hleaf_SW__a_cfg_v, hleaf_SW__a_desc_base, hleaf_SW__a_desc_limit, hleaf_SW__a_desc_loops, hleaf_SW__a_desc_v, hleaf_SW__a_launch_v, host_cp_rxs__session, lk_N0__pma_rck, lk_N0__pma_rx, lk_N2__pma_rck, lk_N2__pma_rx, lk_S0__pma_rck, lk_S0__pma_rx, lk_S1__pma_rck, lk_S1__pma_rx, lk_S3__pma_rck, lk_S3__pma_rx, native_required__calendar_NE__rst_n, native_required__calendar_NW__rst_n, native_required__calendar_SE__rst_n, native_required__calendar_SW__rst_n, native_required__hb_idx__s_NE__clear, native_required__hb_idx__s_NE__live_index, native_required__hb_idx__s_NE__live_v, native_required__hb_idx__s_NE__pre_index, native_required__hb_idx__s_NE__pre_v, native_required__hb_idx__s_NE__replay_index, native_required__hb_idx__s_NE__replay_v, native_required__hb_idx__s_NE__rst_n, native_required__hb_idx__s_NW__clear, native_required__hb_idx__s_NW__live_index, native_required__hb_idx__s_NW__live_v, native_required__hb_idx__s_NW__pre_index, native_required__hb_idx__s_NW__pre_v, native_required__hb_idx__s_NW__replay_index, native_required__hb_idx__s_NW__replay_v, native_required__hb_idx__s_NW__rst_n, native_required__hb_idx__s_SE__clear, native_required__hb_idx__s_SE__live_index, native_required__hb_idx__s_SE__live_v, native_required__hb_idx__s_SE__pre_index, native_required__hb_idx__s_SE__pre_v, native_required__hb_idx__s_SE__replay_index, native_required__hb_idx__s_SE__replay_v, native_required__hb_idx__s_SE__rst_n, native_required__hb_idx__s_SW__clear, native_required__hb_idx__s_SW__live_index, native_required__hb_idx__s_SW__live_v, native_required__hb_idx__s_SW__pre_index, native_required__hb_idx__s_SW__pre_v, native_required__hb_idx__s_SW__replay_index, native_required__hb_idx__s_SW__replay_v, native_required__hb_idx__s_SW__rst_n, native_required__u_mu_fused_n4_ne__pad_b, native_required__u_mu_fused_n4_ne__pad_k, native_required__u_mu_fused_n4_ne__rst_n, native_required__u_mu_fused_n4_ne__ua, native_required__u_mu_fused_n4_ne__ub, native_required__u_mu_fused_n4_nw__pad_b, native_required__u_mu_fused_n4_nw__pad_k, native_required__u_mu_fused_n4_nw__rst_n, native_required__u_mu_fused_n4_nw__ua, native_required__u_mu_fused_n4_nw__ub, native_required__u_mu_fused_programme__rst_n, native_required__u_mu_fused_root__rst_n, native_required__vmb_NE0__rst_n, native_required__vmb_NE1__rst_n, native_required__vmb_NE2__rst_n, native_required__vmb_NE3__rst_n, native_required__vmb_NE4__rst_n, native_required__vmb_NE5__rst_n, native_required__vmb_NE6__rst_n, native_required__vmb_NE7__rst_n, native_required__vmb_NW0__rst_n, native_required__vmb_NW1__rst_n, native_required__vmb_NW2__rst_n, native_required__vmb_NW3__rst_n, native_required__vmb_NW4__rst_n, native_required__vmb_NW5__rst_n, native_required__vmb_NW6__rst_n, native_required__vmb_NW7__rst_n, native_required__vmb_SE0__rst_n, native_required__vmb_SE1__rst_n, native_required__vmb_SE2__rst_n, native_required__vmb_SE3__rst_n, native_required__vmb_SE4__rst_n, native_required__vmb_SE5__rst_n, native_required__vmb_SE6__rst_n, native_required__vmb_SE7__rst_n, native_required__vmb_SW0__rst_n, native_required__vmb_SW1__rst_n, native_required__vmb_SW2__rst_n, native_required__vmb_SW3__rst_n, native_required__vmb_SW4__rst_n, native_required__vmb_SW5__rst_n, native_required__vmb_SW6__rst_n, native_required__vmb_SW7__rst_n, native_required__vmm_NW0__rst_n, native_required__vmm_NW1__rst_n, native_required__vmm_NW2__rst_n, native_required__vmm_NW3__rst_n, native_required__vmm_NW4__rst_n, native_required__vmm_NW5__rst_n, native_required__vmm_NW6__rst_n, native_required__vmm_NW7__rst_n, smw_SE__wq_s0, smw_SE__wq_s1, smw_SE__wq_s2, smw_SE__wq_s3, smw_SE__wq_t0, smw_SE__wq_t1, smw_SE__wq_t2, smw_SE__wq_t3, smw_SW__wq_s0, smw_SW__wq_s1, smw_SW__wq_s2, smw_SW__wq_s3, smw_SW__wq_t0, smw_SW__wq_t1, smw_SW__wq_t2, smw_SW__wq_t3, su_SE0__lg_rq, su_SE0__lg_wq, su_SE1__lg_rq, su_SE1__lg_wq, su_SE2__lg_rq, su_SE2__lg_wq, su_SE3__lg_rq, su_SE3__lg_wq, su_SW0__lg_rq, su_SW0__lg_wq, su_SW1__lg_rq, su_SW1__lg_wq, su_SW2__lg_rq, su_SW2__lg_wq, su_SW3__lg_rq, su_SW3__lg_wq, svg_SW0__sm_packet, svg_SW1__sm_packet, svg_SW2__sm_packet, svg_SW3__sm_packet, svg_SW4__sm_packet, svg_SW5__sm_packet, svg_SW6__sm_packet, svg_SW7__sm_packet, vmdel_SE0__dq, vmdel_SE1__dq, vmdel_SE2__dq, vmdel_SE3__dq, vmdel_SE4__dq, vmdel_SE5__dq, vmdel_SE6__dq, vmdel_SE7__dq, vmdel_SW0__dq, vmdel_SW1__dq, vmdel_SW2__dq, vmdel_SW3__dq, vmdel_SW4__dq, vmdel_SW5__dq, vmdel_SW6__dq, vmdel_SW7__dq, xl_SE_ctl__rq, xl_SW_ctl__rq, calendar_NE__ordinal, calendar_NW__ordinal, calendar_SE__active, calendar_SE__calendar_v, calendar_SE__done, calendar_SE__fault, calendar_SE__lg_local_read, calendar_SE__lg_local_write, calendar_SE__ordinal, calendar_SE__tgt_configured, calendar_SE__tgt_fault, calendar_SW__active, calendar_SW__calendar_v, calendar_SW__done, calendar_SW__fault, calendar_SW__lg_local_read, calendar_SW__lg_local_write, calendar_SW__ordinal, calendar_SW__tgt_configured, calendar_SW__tgt_fault, col_sfu_NE__go, col_sfu_NE__rec, col_sfu_NW__go, col_sfu_NW__rec, col_su__go, col_su__rec, epcal_NE__ordinal, epcal_NW__ordinal, hb_ckgen__pll_serial, hb_ckgen__por_serial, hb_quant_NW__program_leaf__ordinal, hb_router_ids__fault, hb_vms_SE__hub_status, hb_vms_SE__mirror_busy, hb_vms_SE__ring_fault, hb_vms_SE__vmstat, hb_vms_SW__hub_status, hb_vms_SW__mirror_busy, hb_vms_SW__ring_fault, hb_vms_SW__vmstat, lk_N0__pma_tck, lk_N0__pma_tx, lk_N2__pma_tck, lk_N2__pma_tx, lk_S0__pma_tck, lk_S0__pma_tx, lk_S1__pma_tck, lk_S1__pma_tx, lk_S3__pma_tck, lk_S3__pma_tx, pgp_NE__busy, sfup_NE__io_ordinal, sfup_NE__programme_ordinal, sfup_NW__io_ordinal, sfup_NW__programme_ordinal, u_mu_fused_n4_ne__da, u_mu_fused_n4_ne__db, u_mu_fused_n4_nw__da, u_mu_fused_n4_nw__db, u_mu_fused_programme__done, vmb_SE0__dq_done, vmb_SE0__kq_done, vmb_SE0__rr0, vmb_SE0__rr1, vmb_SE0__rr2, vmb_SE0__rr3, vmb_SE0__wq_done0, vmb_SE0__wq_done1, vmb_SE1__dq_done, vmb_SE1__kq_done, vmb_SE1__rr0, vmb_SE1__rr1, vmb_SE1__rr2, vmb_SE1__rr3, vmb_SE1__wq_done0, vmb_SE1__wq_done1, vmb_SE2__dq_done, vmb_SE2__kq_done, vmb_SE2__rr0, vmb_SE2__rr1, vmb_SE2__rr2, vmb_SE2__rr3, vmb_SE2__wq_done0, vmb_SE2__wq_done1, vmb_SE3__dq_done, vmb_SE3__kq_done, vmb_SE3__rr0, vmb_SE3__rr1, vmb_SE3__rr2, vmb_SE3__rr3, vmb_SE3__wq_done0, vmb_SE3__wq_done1, vmb_SE4__dq_done, vmb_SE4__kq_done, vmb_SE4__rr0, vmb_SE4__rr1, vmb_SE4__rr2, vmb_SE4__rr3, vmb_SE4__wq_done0, vmb_SE4__wq_done1, vmb_SE5__dq_done, vmb_SE5__kq_done, vmb_SE5__rr0, vmb_SE5__rr1, vmb_SE5__rr2, vmb_SE5__rr3, vmb_SE5__wq_done0, vmb_SE5__wq_done1, vmb_SE6__dq_done, vmb_SE6__kq_done, vmb_SE6__rr0, vmb_SE6__rr1, vmb_SE6__rr2, vmb_SE6__rr3, vmb_SE6__wq_done0, vmb_SE6__wq_done1, vmb_SE7__dq_done, vmb_SE7__kq_done, vmb_SE7__rr0, vmb_SE7__rr1, vmb_SE7__rr2, vmb_SE7__rr3, vmb_SE7__wq_done0, vmb_SE7__wq_done1, vmb_SW0__dq_done, vmb_SW0__kq_done, vmb_SW0__rr0, vmb_SW0__rr1, vmb_SW0__rr2, vmb_SW0__rr3, vmb_SW0__wq_done0, vmb_SW0__wq_done1, vmb_SW1__dq_done, vmb_SW1__kq_done, vmb_SW1__rr0, vmb_SW1__rr1, vmb_SW1__rr2, vmb_SW1__rr3, vmb_SW1__wq_done0, vmb_SW1__wq_done1, vmb_SW2__dq_done, vmb_SW2__kq_done, vmb_SW2__rr0, vmb_SW2__rr1, vmb_SW2__rr2, vmb_SW2__rr3, vmb_SW2__wq_done0, vmb_SW2__wq_done1, vmb_SW3__dq_done, vmb_SW3__kq_done, vmb_SW3__rr0, vmb_SW3__rr1, vmb_SW3__rr2, vmb_SW3__rr3, vmb_SW3__wq_done0, vmb_SW3__wq_done1, vmb_SW4__dq_done, vmb_SW4__kq_done, vmb_SW4__rr0, vmb_SW4__rr1, vmb_SW4__rr2, vmb_SW4__rr3, vmb_SW4__wq_done0, vmb_SW4__wq_done1, vmb_SW5__dq_done, vmb_SW5__kq_done, vmb_SW5__rr0, vmb_SW5__rr1, vmb_SW5__rr2, vmb_SW5__rr3, vmb_SW5__wq_done0, vmb_SW5__wq_done1, vmb_SW6__dq_done, vmb_SW6__kq_done, vmb_SW6__rr0, vmb_SW6__rr1, vmb_SW6__rr2, vmb_SW6__rr3, vmb_SW6__wq_done0, vmb_SW6__wq_done1, vmb_SW7__dq_done, vmb_SW7__kq_done, vmb_SW7__rr0, vmb_SW7__rr1, vmb_SW7__rr2, vmb_SW7__rr3, vmb_SW7__wq_done0, vmb_SW7__wq_done1, vmfc_NE__ordinal, vmfc_NW__ordinal, xl_NE_aqhi__y, xl_NE_aqlo__y, xl_NW_aqhi__y, xl_NW_aqlo__y);
  input wire [0:0] hb_ckgen__por_n;
  input wire [0:0] hb_ckgen__refclk;
  input wire [135:0] hb_dbk_SE__rq;
  input wire [135:0] hb_dbk_SW__rq;
  input wire [561:0] hcollks_SE_p0__vm_kq;
  input wire [561:0] hcollks_SE_p1__vm_kq;
  input wire [561:0] hcollks_SE_p2__vm_kq;
  input wire [561:0] hcollks_SE_p3__vm_kq;
  input wire [561:0] hcollks_SW_p0__vm_kq;
  input wire [561:0] hcollks_SW_p1__vm_kq;
  input wire [561:0] hcollks_SW_p2__vm_kq;
  input wire [561:0] hcollks_SW_p3__vm_kq;
  input wire [135:0] hcollrs_SE__vm_rq;
  input wire [135:0] hcollrs_SW__vm_rq;
  input wire [11:0] hleaf_SE__a_cfg_addr;
  input wire [255:0] hleaf_SE__a_cfg_data;
  input wire [7:0] hleaf_SE__a_cfg_target;
  input wire [0:0] hleaf_SE__a_cfg_v;
  input wire [11:0] hleaf_SE__a_desc_base;
  input wire [12:0] hleaf_SE__a_desc_limit;
  input wire [15:0] hleaf_SE__a_desc_loops;
  input wire [0:0] hleaf_SE__a_desc_v;
  input wire [0:0] hleaf_SE__a_launch_v;
  input wire [11:0] hleaf_SW__a_cfg_addr;
  input wire [255:0] hleaf_SW__a_cfg_data;
  input wire [7:0] hleaf_SW__a_cfg_target;
  input wire [0:0] hleaf_SW__a_cfg_v;
  input wire [11:0] hleaf_SW__a_desc_base;
  input wire [12:0] hleaf_SW__a_desc_limit;
  input wire [15:0] hleaf_SW__a_desc_loops;
  input wire [0:0] hleaf_SW__a_desc_v;
  input wire [0:0] hleaf_SW__a_launch_v;
  input wire [7:0] host_cp_rxs__session;
  input wire [0:0] lk_N0__pma_rck;
  input wire [543:0] lk_N0__pma_rx;
  input wire [0:0] lk_N2__pma_rck;
  input wire [543:0] lk_N2__pma_rx;
  input wire [0:0] lk_S0__pma_rck;
  input wire [543:0] lk_S0__pma_rx;
  input wire [0:0] lk_S1__pma_rck;
  input wire [543:0] lk_S1__pma_rx;
  input wire [0:0] lk_S3__pma_rck;
  input wire [543:0] lk_S3__pma_rx;
  input wire [0:0] native_required__calendar_NE__rst_n;
  input wire [0:0] native_required__calendar_NW__rst_n;
  input wire [0:0] native_required__calendar_SE__rst_n;
  input wire [0:0] native_required__calendar_SW__rst_n;
  input wire [0:0] native_required__hb_idx__s_NE__clear;
  input wire [7:0] native_required__hb_idx__s_NE__live_index;
  input wire [0:0] native_required__hb_idx__s_NE__live_v;
  input wire [7:0] native_required__hb_idx__s_NE__pre_index;
  input wire [0:0] native_required__hb_idx__s_NE__pre_v;
  input wire [7:0] native_required__hb_idx__s_NE__replay_index;
  input wire [0:0] native_required__hb_idx__s_NE__replay_v;
  input wire [0:0] native_required__hb_idx__s_NE__rst_n;
  input wire [0:0] native_required__hb_idx__s_NW__clear;
  input wire [7:0] native_required__hb_idx__s_NW__live_index;
  input wire [0:0] native_required__hb_idx__s_NW__live_v;
  input wire [7:0] native_required__hb_idx__s_NW__pre_index;
  input wire [0:0] native_required__hb_idx__s_NW__pre_v;
  input wire [7:0] native_required__hb_idx__s_NW__replay_index;
  input wire [0:0] native_required__hb_idx__s_NW__replay_v;
  input wire [0:0] native_required__hb_idx__s_NW__rst_n;
  input wire [0:0] native_required__hb_idx__s_SE__clear;
  input wire [7:0] native_required__hb_idx__s_SE__live_index;
  input wire [0:0] native_required__hb_idx__s_SE__live_v;
  input wire [7:0] native_required__hb_idx__s_SE__pre_index;
  input wire [0:0] native_required__hb_idx__s_SE__pre_v;
  input wire [7:0] native_required__hb_idx__s_SE__replay_index;
  input wire [0:0] native_required__hb_idx__s_SE__replay_v;
  input wire [0:0] native_required__hb_idx__s_SE__rst_n;
  input wire [0:0] native_required__hb_idx__s_SW__clear;
  input wire [7:0] native_required__hb_idx__s_SW__live_index;
  input wire [0:0] native_required__hb_idx__s_SW__live_v;
  input wire [7:0] native_required__hb_idx__s_SW__pre_index;
  input wire [0:0] native_required__hb_idx__s_SW__pre_v;
  input wire [7:0] native_required__hb_idx__s_SW__replay_index;
  input wire [0:0] native_required__hb_idx__s_SW__replay_v;
  input wire [0:0] native_required__hb_idx__s_SW__rst_n;
  input wire [0:0] native_required__u_mu_fused_n4_ne__pad_b;
  input wire [5:0] native_required__u_mu_fused_n4_ne__pad_k;
  input wire [0:0] native_required__u_mu_fused_n4_ne__rst_n;
  input wire [270:0] native_required__u_mu_fused_n4_ne__ua;
  input wire [270:0] native_required__u_mu_fused_n4_ne__ub;
  input wire [0:0] native_required__u_mu_fused_n4_nw__pad_b;
  input wire [5:0] native_required__u_mu_fused_n4_nw__pad_k;
  input wire [0:0] native_required__u_mu_fused_n4_nw__rst_n;
  input wire [270:0] native_required__u_mu_fused_n4_nw__ua;
  input wire [270:0] native_required__u_mu_fused_n4_nw__ub;
  input wire [0:0] native_required__u_mu_fused_programme__rst_n;
  input wire [0:0] native_required__u_mu_fused_root__rst_n;
  input wire [0:0] native_required__vmb_NE0__rst_n;
  input wire [0:0] native_required__vmb_NE1__rst_n;
  input wire [0:0] native_required__vmb_NE2__rst_n;
  input wire [0:0] native_required__vmb_NE3__rst_n;
  input wire [0:0] native_required__vmb_NE4__rst_n;
  input wire [0:0] native_required__vmb_NE5__rst_n;
  input wire [0:0] native_required__vmb_NE6__rst_n;
  input wire [0:0] native_required__vmb_NE7__rst_n;
  input wire [0:0] native_required__vmb_NW0__rst_n;
  input wire [0:0] native_required__vmb_NW1__rst_n;
  input wire [0:0] native_required__vmb_NW2__rst_n;
  input wire [0:0] native_required__vmb_NW3__rst_n;
  input wire [0:0] native_required__vmb_NW4__rst_n;
  input wire [0:0] native_required__vmb_NW5__rst_n;
  input wire [0:0] native_required__vmb_NW6__rst_n;
  input wire [0:0] native_required__vmb_NW7__rst_n;
  input wire [0:0] native_required__vmb_SE0__rst_n;
  input wire [0:0] native_required__vmb_SE1__rst_n;
  input wire [0:0] native_required__vmb_SE2__rst_n;
  input wire [0:0] native_required__vmb_SE3__rst_n;
  input wire [0:0] native_required__vmb_SE4__rst_n;
  input wire [0:0] native_required__vmb_SE5__rst_n;
  input wire [0:0] native_required__vmb_SE6__rst_n;
  input wire [0:0] native_required__vmb_SE7__rst_n;
  input wire [0:0] native_required__vmb_SW0__rst_n;
  input wire [0:0] native_required__vmb_SW1__rst_n;
  input wire [0:0] native_required__vmb_SW2__rst_n;
  input wire [0:0] native_required__vmb_SW3__rst_n;
  input wire [0:0] native_required__vmb_SW4__rst_n;
  input wire [0:0] native_required__vmb_SW5__rst_n;
  input wire [0:0] native_required__vmb_SW6__rst_n;
  input wire [0:0] native_required__vmb_SW7__rst_n;
  input wire [0:0] native_required__vmm_NW0__rst_n;
  input wire [0:0] native_required__vmm_NW1__rst_n;
  input wire [0:0] native_required__vmm_NW2__rst_n;
  input wire [0:0] native_required__vmm_NW3__rst_n;
  input wire [0:0] native_required__vmm_NW4__rst_n;
  input wire [0:0] native_required__vmm_NW5__rst_n;
  input wire [0:0] native_required__vmm_NW6__rst_n;
  input wire [0:0] native_required__vmm_NW7__rst_n;
  input wire [280:0] smw_SE__wq_s0;
  input wire [280:0] smw_SE__wq_s1;
  input wire [280:0] smw_SE__wq_s2;
  input wire [280:0] smw_SE__wq_s3;
  input wire [280:0] smw_SE__wq_t0;
  input wire [280:0] smw_SE__wq_t1;
  input wire [280:0] smw_SE__wq_t2;
  input wire [280:0] smw_SE__wq_t3;
  input wire [280:0] smw_SW__wq_s0;
  input wire [280:0] smw_SW__wq_s1;
  input wire [280:0] smw_SW__wq_s2;
  input wire [280:0] smw_SW__wq_s3;
  input wire [280:0] smw_SW__wq_t0;
  input wire [280:0] smw_SW__wq_t1;
  input wire [280:0] smw_SW__wq_t2;
  input wire [280:0] smw_SW__wq_t3;
  input wire [33:0] su_SE0__lg_rq;
  input wire [561:0] su_SE0__lg_wq;
  input wire [33:0] su_SE1__lg_rq;
  input wire [561:0] su_SE1__lg_wq;
  input wire [33:0] su_SE2__lg_rq;
  input wire [561:0] su_SE2__lg_wq;
  input wire [33:0] su_SE3__lg_rq;
  input wire [561:0] su_SE3__lg_wq;
  input wire [33:0] su_SW0__lg_rq;
  input wire [561:0] su_SW0__lg_wq;
  input wire [33:0] su_SW1__lg_rq;
  input wire [561:0] su_SW1__lg_wq;
  input wire [33:0] su_SW2__lg_rq;
  input wire [561:0] su_SW2__lg_wq;
  input wire [33:0] su_SW3__lg_rq;
  input wire [561:0] su_SW3__lg_wq;
  input wire [1098:0] svg_SW0__sm_packet;
  input wire [1098:0] svg_SW1__sm_packet;
  input wire [1098:0] svg_SW2__sm_packet;
  input wire [1098:0] svg_SW3__sm_packet;
  input wire [1098:0] svg_SW4__sm_packet;
  input wire [1098:0] svg_SW5__sm_packet;
  input wire [1098:0] svg_SW6__sm_packet;
  input wire [1098:0] svg_SW7__sm_packet;
  input wire [280:0] vmdel_SE0__dq;
  input wire [280:0] vmdel_SE1__dq;
  input wire [280:0] vmdel_SE2__dq;
  input wire [280:0] vmdel_SE3__dq;
  input wire [280:0] vmdel_SE4__dq;
  input wire [280:0] vmdel_SE5__dq;
  input wire [280:0] vmdel_SE6__dq;
  input wire [280:0] vmdel_SE7__dq;
  input wire [280:0] vmdel_SW0__dq;
  input wire [280:0] vmdel_SW1__dq;
  input wire [280:0] vmdel_SW2__dq;
  input wire [280:0] vmdel_SW3__dq;
  input wire [280:0] vmdel_SW4__dq;
  input wire [280:0] vmdel_SW5__dq;
  input wire [280:0] vmdel_SW6__dq;
  input wire [280:0] vmdel_SW7__dq;
  input wire [135:0] xl_SE_ctl__rq;
  input wire [135:0] xl_SW_ctl__rq;
  output wire [31:0] calendar_NE__ordinal;
  output wire [31:0] calendar_NW__ordinal;
  output wire [0:0] calendar_SE__active;
  output wire [0:0] calendar_SE__calendar_v;
  output wire [0:0] calendar_SE__done;
  output wire [0:0] calendar_SE__fault;
  output wire [23:0] calendar_SE__lg_local_read;
  output wire [23:0] calendar_SE__lg_local_write;
  output wire [31:0] calendar_SE__ordinal;
  output wire [0:0] calendar_SE__tgt_configured;
  output wire [0:0] calendar_SE__tgt_fault;
  output wire [0:0] calendar_SW__active;
  output wire [0:0] calendar_SW__calendar_v;
  output wire [0:0] calendar_SW__done;
  output wire [0:0] calendar_SW__fault;
  output wire [23:0] calendar_SW__lg_local_read;
  output wire [23:0] calendar_SW__lg_local_write;
  output wire [31:0] calendar_SW__ordinal;
  output wire [0:0] calendar_SW__tgt_configured;
  output wire [0:0] calendar_SW__tgt_fault;
  output wire [0:0] col_sfu_NE__go;
  output wire [220:0] col_sfu_NE__rec;
  output wire [0:0] col_sfu_NW__go;
  output wire [220:0] col_sfu_NW__rec;
  output wire [0:0] col_su__go;
  output wire [220:0] col_su__rec;
  output wire [31:0] epcal_NE__ordinal;
  output wire [31:0] epcal_NW__ordinal;
  output wire [0:0] hb_ckgen__pll_serial;
  output wire [0:0] hb_ckgen__por_serial;
  output wire [31:0] hb_quant_NW__program_leaf__ordinal;
  output wire [0:0] hb_router_ids__fault;
  output wire [2:0] hb_vms_SE__hub_status;
  output wire [1:0] hb_vms_SE__mirror_busy;
  output wire [2:0] hb_vms_SE__ring_fault;
  output wire [18:0] hb_vms_SE__vmstat;
  output wire [2:0] hb_vms_SW__hub_status;
  output wire [1:0] hb_vms_SW__mirror_busy;
  output wire [2:0] hb_vms_SW__ring_fault;
  output wire [18:0] hb_vms_SW__vmstat;
  output wire [0:0] lk_N0__pma_tck;
  output wire [543:0] lk_N0__pma_tx;
  output wire [0:0] lk_N2__pma_tck;
  output wire [543:0] lk_N2__pma_tx;
  output wire [0:0] lk_S0__pma_tck;
  output wire [543:0] lk_S0__pma_tx;
  output wire [0:0] lk_S1__pma_tck;
  output wire [543:0] lk_S1__pma_tx;
  output wire [0:0] lk_S3__pma_tck;
  output wire [543:0] lk_S3__pma_tx;
  output wire [0:0] pgp_NE__busy;
  output wire [31:0] sfup_NE__io_ordinal;
  output wire [31:0] sfup_NE__programme_ordinal;
  output wire [31:0] sfup_NW__io_ordinal;
  output wire [31:0] sfup_NW__programme_ordinal;
  output wire [172:0] u_mu_fused_n4_ne__da;
  output wire [172:0] u_mu_fused_n4_ne__db;
  output wire [172:0] u_mu_fused_n4_nw__da;
  output wire [172:0] u_mu_fused_n4_nw__db;
  output wire [0:0] u_mu_fused_programme__done;
  output wire [0:0] vmb_SE0__dq_done;
  output wire [0:0] vmb_SE0__kq_done;
  output wire [256:0] vmb_SE0__rr0;
  output wire [256:0] vmb_SE0__rr1;
  output wire [256:0] vmb_SE0__rr2;
  output wire [256:0] vmb_SE0__rr3;
  output wire [0:0] vmb_SE0__wq_done0;
  output wire [0:0] vmb_SE0__wq_done1;
  output wire [0:0] vmb_SE1__dq_done;
  output wire [0:0] vmb_SE1__kq_done;
  output wire [256:0] vmb_SE1__rr0;
  output wire [256:0] vmb_SE1__rr1;
  output wire [256:0] vmb_SE1__rr2;
  output wire [256:0] vmb_SE1__rr3;
  output wire [0:0] vmb_SE1__wq_done0;
  output wire [0:0] vmb_SE1__wq_done1;
  output wire [0:0] vmb_SE2__dq_done;
  output wire [0:0] vmb_SE2__kq_done;
  output wire [256:0] vmb_SE2__rr0;
  output wire [256:0] vmb_SE2__rr1;
  output wire [256:0] vmb_SE2__rr2;
  output wire [256:0] vmb_SE2__rr3;
  output wire [0:0] vmb_SE2__wq_done0;
  output wire [0:0] vmb_SE2__wq_done1;
  output wire [0:0] vmb_SE3__dq_done;
  output wire [0:0] vmb_SE3__kq_done;
  output wire [256:0] vmb_SE3__rr0;
  output wire [256:0] vmb_SE3__rr1;
  output wire [256:0] vmb_SE3__rr2;
  output wire [256:0] vmb_SE3__rr3;
  output wire [0:0] vmb_SE3__wq_done0;
  output wire [0:0] vmb_SE3__wq_done1;
  output wire [0:0] vmb_SE4__dq_done;
  output wire [0:0] vmb_SE4__kq_done;
  output wire [256:0] vmb_SE4__rr0;
  output wire [256:0] vmb_SE4__rr1;
  output wire [256:0] vmb_SE4__rr2;
  output wire [256:0] vmb_SE4__rr3;
  output wire [0:0] vmb_SE4__wq_done0;
  output wire [0:0] vmb_SE4__wq_done1;
  output wire [0:0] vmb_SE5__dq_done;
  output wire [0:0] vmb_SE5__kq_done;
  output wire [256:0] vmb_SE5__rr0;
  output wire [256:0] vmb_SE5__rr1;
  output wire [256:0] vmb_SE5__rr2;
  output wire [256:0] vmb_SE5__rr3;
  output wire [0:0] vmb_SE5__wq_done0;
  output wire [0:0] vmb_SE5__wq_done1;
  output wire [0:0] vmb_SE6__dq_done;
  output wire [0:0] vmb_SE6__kq_done;
  output wire [256:0] vmb_SE6__rr0;
  output wire [256:0] vmb_SE6__rr1;
  output wire [256:0] vmb_SE6__rr2;
  output wire [256:0] vmb_SE6__rr3;
  output wire [0:0] vmb_SE6__wq_done0;
  output wire [0:0] vmb_SE6__wq_done1;
  output wire [0:0] vmb_SE7__dq_done;
  output wire [0:0] vmb_SE7__kq_done;
  output wire [256:0] vmb_SE7__rr0;
  output wire [256:0] vmb_SE7__rr1;
  output wire [256:0] vmb_SE7__rr2;
  output wire [256:0] vmb_SE7__rr3;
  output wire [0:0] vmb_SE7__wq_done0;
  output wire [0:0] vmb_SE7__wq_done1;
  output wire [0:0] vmb_SW0__dq_done;
  output wire [0:0] vmb_SW0__kq_done;
  output wire [256:0] vmb_SW0__rr0;
  output wire [256:0] vmb_SW0__rr1;
  output wire [256:0] vmb_SW0__rr2;
  output wire [256:0] vmb_SW0__rr3;
  output wire [0:0] vmb_SW0__wq_done0;
  output wire [0:0] vmb_SW0__wq_done1;
  output wire [0:0] vmb_SW1__dq_done;
  output wire [0:0] vmb_SW1__kq_done;
  output wire [256:0] vmb_SW1__rr0;
  output wire [256:0] vmb_SW1__rr1;
  output wire [256:0] vmb_SW1__rr2;
  output wire [256:0] vmb_SW1__rr3;
  output wire [0:0] vmb_SW1__wq_done0;
  output wire [0:0] vmb_SW1__wq_done1;
  output wire [0:0] vmb_SW2__dq_done;
  output wire [0:0] vmb_SW2__kq_done;
  output wire [256:0] vmb_SW2__rr0;
  output wire [256:0] vmb_SW2__rr1;
  output wire [256:0] vmb_SW2__rr2;
  output wire [256:0] vmb_SW2__rr3;
  output wire [0:0] vmb_SW2__wq_done0;
  output wire [0:0] vmb_SW2__wq_done1;
  output wire [0:0] vmb_SW3__dq_done;
  output wire [0:0] vmb_SW3__kq_done;
  output wire [256:0] vmb_SW3__rr0;
  output wire [256:0] vmb_SW3__rr1;
  output wire [256:0] vmb_SW3__rr2;
  output wire [256:0] vmb_SW3__rr3;
  output wire [0:0] vmb_SW3__wq_done0;
  output wire [0:0] vmb_SW3__wq_done1;
  output wire [0:0] vmb_SW4__dq_done;
  output wire [0:0] vmb_SW4__kq_done;
  output wire [256:0] vmb_SW4__rr0;
  output wire [256:0] vmb_SW4__rr1;
  output wire [256:0] vmb_SW4__rr2;
  output wire [256:0] vmb_SW4__rr3;
  output wire [0:0] vmb_SW4__wq_done0;
  output wire [0:0] vmb_SW4__wq_done1;
  output wire [0:0] vmb_SW5__dq_done;
  output wire [0:0] vmb_SW5__kq_done;
  output wire [256:0] vmb_SW5__rr0;
  output wire [256:0] vmb_SW5__rr1;
  output wire [256:0] vmb_SW5__rr2;
  output wire [256:0] vmb_SW5__rr3;
  output wire [0:0] vmb_SW5__wq_done0;
  output wire [0:0] vmb_SW5__wq_done1;
  output wire [0:0] vmb_SW6__dq_done;
  output wire [0:0] vmb_SW6__kq_done;
  output wire [256:0] vmb_SW6__rr0;
  output wire [256:0] vmb_SW6__rr1;
  output wire [256:0] vmb_SW6__rr2;
  output wire [256:0] vmb_SW6__rr3;
  output wire [0:0] vmb_SW6__wq_done0;
  output wire [0:0] vmb_SW6__wq_done1;
  output wire [0:0] vmb_SW7__dq_done;
  output wire [0:0] vmb_SW7__kq_done;
  output wire [256:0] vmb_SW7__rr0;
  output wire [256:0] vmb_SW7__rr1;
  output wire [256:0] vmb_SW7__rr2;
  output wire [256:0] vmb_SW7__rr3;
  output wire [0:0] vmb_SW7__wq_done0;
  output wire [0:0] vmb_SW7__wq_done1;
  output wire [31:0] vmfc_NE__ordinal;
  output wire [31:0] vmfc_NW__ordinal;
  output wire [511:0] xl_NE_aqhi__y;
  output wire [511:0] xl_NE_aqlo__y;
  output wire [511:0] xl_NW_aqhi__y;
  output wire [511:0] xl_NW_aqlo__y;
  wire [614:0] b2_ep1_root__rx_o;
  wire [631:0] b2_ep1_root__tx_o;
  wire [0:0] calendar_NE__active;
  wire [23:0] calendar_NE__bank_client;
  wire [7:0] calendar_NE__bank_enable;
  wire [0:0] calendar_NE__calendar_v;
  wire [9:0] calendar_NE__client_seq;
  wire [0:0] calendar_NE__done;
  wire [0:0] calendar_NE__fault;
  wire [5:0] calendar_NE__hub_ring_client;
  wire [1:0] calendar_NE__hub_ring_enable;
  wire [23:0] calendar_NE__lg_local_read;
  wire [23:0] calendar_NE__lg_local_write;
  wire [0:0] calendar_NE__replay_enable;
  wire [0:0] calendar_NE__replay_source;
  wire [4:0] calendar_NE__response_enable;
  wire [9:0] calendar_NE__response_seq;
  wire [1:0] calendar_NE__ring_tx_enable;
  wire [5:0] calendar_NE__ring_tx_source;
  wire [23:0] calendar_NE__rslot;
  wire [7:0] calendar_NE__rslot_v;
  wire [0:0] calendar_NE__tgt_configured;
  wire [0:0] calendar_NE__tgt_fault;
  wire [23:0] calendar_NE__wslot;
  wire [7:0] calendar_NE__wslot_v;
  wire [0:0] calendar_NW__active;
  wire [23:0] calendar_NW__bank_client;
  wire [7:0] calendar_NW__bank_enable;
  wire [0:0] calendar_NW__calendar_v;
  wire [9:0] calendar_NW__client_seq;
  wire [0:0] calendar_NW__done;
  wire [0:0] calendar_NW__fault;
  wire [5:0] calendar_NW__hub_ring_client;
  wire [1:0] calendar_NW__hub_ring_enable;
  wire [23:0] calendar_NW__lg_local_read;
  wire [23:0] calendar_NW__lg_local_write;
  wire [0:0] calendar_NW__replay_enable;
  wire [0:0] calendar_NW__replay_source;
  wire [4:0] calendar_NW__response_enable;
  wire [9:0] calendar_NW__response_seq;
  wire [1:0] calendar_NW__ring_tx_enable;
  wire [5:0] calendar_NW__ring_tx_source;
  wire [23:0] calendar_NW__rslot;
  wire [7:0] calendar_NW__rslot_v;
  wire [0:0] calendar_NW__tgt_configured;
  wire [0:0] calendar_NW__tgt_fault;
  wire [23:0] calendar_NW__wslot;
  wire [7:0] calendar_NW__wslot_v;
  wire [23:0] calendar_SE__bank_client;
  wire [7:0] calendar_SE__bank_enable;
  wire [9:0] calendar_SE__client_seq;
  wire [5:0] calendar_SE__hub_ring_client;
  wire [1:0] calendar_SE__hub_ring_enable;
  wire [0:0] calendar_SE__replay_enable;
  wire [0:0] calendar_SE__replay_source;
  wire [4:0] calendar_SE__response_enable;
  wire [9:0] calendar_SE__response_seq;
  wire [1:0] calendar_SE__ring_tx_enable;
  wire [5:0] calendar_SE__ring_tx_source;
  wire [23:0] calendar_SE__rslot;
  wire [7:0] calendar_SE__rslot_v;
  wire [23:0] calendar_SE__wslot;
  wire [7:0] calendar_SE__wslot_v;
  wire [23:0] calendar_SW__bank_client;
  wire [7:0] calendar_SW__bank_enable;
  wire [9:0] calendar_SW__client_seq;
  wire [5:0] calendar_SW__hub_ring_client;
  wire [1:0] calendar_SW__hub_ring_enable;
  wire [0:0] calendar_SW__replay_enable;
  wire [0:0] calendar_SW__replay_source;
  wire [4:0] calendar_SW__response_enable;
  wire [9:0] calendar_SW__response_seq;
  wire [1:0] calendar_SW__ring_tx_enable;
  wire [5:0] calendar_SW__ring_tx_source;
  wire [23:0] calendar_SW__rslot;
  wire [7:0] calendar_SW__rslot_v;
  wire [23:0] calendar_SW__wslot;
  wire [7:0] calendar_SW__wslot_v;
  wire [159:0] cic_NE__inj_addr_o;
  wire [1:0] cic_NE__inj_rd_o;
  wire [159:0] cic_NW__inj_addr_o;
  wire [1:0] cic_NW__inj_rd_o;
  wire [0:0] cij_NE__fault;
  wire [511:0] cij_NE__inj_d_r0;
  wire [511:0] cij_NE__inj_d_r1;
  wire [0:0] cij_NW__fault;
  wire [511:0] cij_NW__inj_d_r0;
  wire [511:0] cij_NW__inj_d_r1;
  wire [0:0] col_idx__active;
  wire [0:0] col_idx__fault;
  wire [1:0] col_idx__go;
  wire [768:0] col_idx__prm;
  wire [7:0] col_idx__pw_addr;
  wire [255:0] col_idx__pw_data;
  wire [0:0] col_idx__pw_we;
  wire [0:0] col_idx__ready;
  wire [220:0] col_idx__rec;
  wire [0:0] col_idx__start_v;
  wire [0:0] col_sfu_NE__active;
  wire [0:0] col_sfu_NE__fault;
  wire [255:0] col_sfu_NE__prm;
  wire [13:0] col_sfu_NE__pw_addr;
  wire [255:0] col_sfu_NE__pw_data;
  wire [1:0] col_sfu_NE__pw_we;
  wire [0:0] col_sfu_NE__ready;
  wire [0:0] col_sfu_NE__start_v;
  wire [0:0] col_sfu_NW__active;
  wire [0:0] col_sfu_NW__fault;
  wire [255:0] col_sfu_NW__prm;
  wire [13:0] col_sfu_NW__pw_addr;
  wire [255:0] col_sfu_NW__pw_data;
  wire [1:0] col_sfu_NW__pw_we;
  wire [0:0] col_sfu_NW__ready;
  wire [0:0] col_sfu_NW__start_v;
  wire [0:0] col_su__active;
  wire [0:0] col_su__fault;
  wire [255:0] col_su__prm;
  wire [22:0] col_su__pw_addr;
  wire [255:0] col_su__pw_data;
  wire [0:0] col_su__pw_we;
  wire [0:0] col_su__ready;
  wire [0:0] col_su__start_v;
  wire [10:0] cp_svg_NW0__a_addr;
  wire [255:0] cp_svg_NW0__a_data;
  wire [0:0] cp_svg_NW0__a_we;
  wire [0:0] cp_svg_NW0__active;
  wire [7:0] cp_svg_NW0__b_addr;
  wire [255:0] cp_svg_NW0__b_data;
  wire [0:0] cp_svg_NW0__b_we;
  wire [0:0] cp_svg_NW0__configured;
  wire [0:0] cp_svg_NW0__fault;
  wire [7:0] cp_svg_NW0__run_arg;
  wire [7:0] cp_svg_NW0__run_base;
  wire [8:0] cp_svg_NW0__run_count;
  wire [0:0] cp_svg_NW0__run_v;
  wire [10:0] cp_svg_NW1__a_addr;
  wire [255:0] cp_svg_NW1__a_data;
  wire [0:0] cp_svg_NW1__a_we;
  wire [0:0] cp_svg_NW1__active;
  wire [7:0] cp_svg_NW1__b_addr;
  wire [255:0] cp_svg_NW1__b_data;
  wire [0:0] cp_svg_NW1__b_we;
  wire [0:0] cp_svg_NW1__configured;
  wire [0:0] cp_svg_NW1__fault;
  wire [7:0] cp_svg_NW1__run_arg;
  wire [7:0] cp_svg_NW1__run_base;
  wire [8:0] cp_svg_NW1__run_count;
  wire [0:0] cp_svg_NW1__run_v;
  wire [10:0] cp_svg_NW2__a_addr;
  wire [255:0] cp_svg_NW2__a_data;
  wire [0:0] cp_svg_NW2__a_we;
  wire [0:0] cp_svg_NW2__active;
  wire [7:0] cp_svg_NW2__b_addr;
  wire [255:0] cp_svg_NW2__b_data;
  wire [0:0] cp_svg_NW2__b_we;
  wire [0:0] cp_svg_NW2__configured;
  wire [0:0] cp_svg_NW2__fault;
  wire [7:0] cp_svg_NW2__run_arg;
  wire [7:0] cp_svg_NW2__run_base;
  wire [8:0] cp_svg_NW2__run_count;
  wire [0:0] cp_svg_NW2__run_v;
  wire [10:0] cp_svg_NW3__a_addr;
  wire [255:0] cp_svg_NW3__a_data;
  wire [0:0] cp_svg_NW3__a_we;
  wire [0:0] cp_svg_NW3__active;
  wire [7:0] cp_svg_NW3__b_addr;
  wire [255:0] cp_svg_NW3__b_data;
  wire [0:0] cp_svg_NW3__b_we;
  wire [0:0] cp_svg_NW3__configured;
  wire [0:0] cp_svg_NW3__fault;
  wire [7:0] cp_svg_NW3__run_arg;
  wire [7:0] cp_svg_NW3__run_base;
  wire [8:0] cp_svg_NW3__run_count;
  wire [0:0] cp_svg_NW3__run_v;
  wire [10:0] cp_svg_NW4__a_addr;
  wire [255:0] cp_svg_NW4__a_data;
  wire [0:0] cp_svg_NW4__a_we;
  wire [0:0] cp_svg_NW4__active;
  wire [7:0] cp_svg_NW4__b_addr;
  wire [255:0] cp_svg_NW4__b_data;
  wire [0:0] cp_svg_NW4__b_we;
  wire [0:0] cp_svg_NW4__configured;
  wire [0:0] cp_svg_NW4__fault;
  wire [7:0] cp_svg_NW4__run_arg;
  wire [7:0] cp_svg_NW4__run_base;
  wire [8:0] cp_svg_NW4__run_count;
  wire [0:0] cp_svg_NW4__run_v;
  wire [10:0] cp_svg_NW5__a_addr;
  wire [255:0] cp_svg_NW5__a_data;
  wire [0:0] cp_svg_NW5__a_we;
  wire [0:0] cp_svg_NW5__active;
  wire [7:0] cp_svg_NW5__b_addr;
  wire [255:0] cp_svg_NW5__b_data;
  wire [0:0] cp_svg_NW5__b_we;
  wire [0:0] cp_svg_NW5__configured;
  wire [0:0] cp_svg_NW5__fault;
  wire [7:0] cp_svg_NW5__run_arg;
  wire [7:0] cp_svg_NW5__run_base;
  wire [8:0] cp_svg_NW5__run_count;
  wire [0:0] cp_svg_NW5__run_v;
  wire [10:0] cp_svg_NW6__a_addr;
  wire [255:0] cp_svg_NW6__a_data;
  wire [0:0] cp_svg_NW6__a_we;
  wire [0:0] cp_svg_NW6__active;
  wire [7:0] cp_svg_NW6__b_addr;
  wire [255:0] cp_svg_NW6__b_data;
  wire [0:0] cp_svg_NW6__b_we;
  wire [0:0] cp_svg_NW6__configured;
  wire [0:0] cp_svg_NW6__fault;
  wire [7:0] cp_svg_NW6__run_arg;
  wire [7:0] cp_svg_NW6__run_base;
  wire [8:0] cp_svg_NW6__run_count;
  wire [0:0] cp_svg_NW6__run_v;
  wire [10:0] cp_svg_NW7__a_addr;
  wire [255:0] cp_svg_NW7__a_data;
  wire [0:0] cp_svg_NW7__a_we;
  wire [0:0] cp_svg_NW7__active;
  wire [7:0] cp_svg_NW7__b_addr;
  wire [255:0] cp_svg_NW7__b_data;
  wire [0:0] cp_svg_NW7__b_we;
  wire [0:0] cp_svg_NW7__configured;
  wire [0:0] cp_svg_NW7__fault;
  wire [7:0] cp_svg_NW7__run_arg;
  wire [7:0] cp_svg_NW7__run_base;
  wire [8:0] cp_svg_NW7__run_count;
  wire [0:0] cp_svg_NW7__run_v;
  wire [4:0] ctl_NW_p00__col_bank;
  wire [4:0] ctl_NW_p00__col_col;
  wire [255:0] ctl_NW_p00__col_data;
  wire [31:0] ctl_NW_p00__col_strb;
  wire [0:0] ctl_NW_p00__col_v;
  wire [0:0] ctl_NW_p00__col_we;
  wire [0:0] ctl_NW_p00__k_rdy;
  wire [0:0] ctl_NW_p00__k_wr_done;
  wire [3:0] ctl_NW_p00__kr_beat;
  wire [255:0] ctl_NW_p00__kr_data;
  wire [16:0] ctl_NW_p00__kr_tag;
  wire [0:0] ctl_NW_p00__kr_v;
  wire [5:0] ctl_NW_p00__owner_fault_split;
  wire [0:0] ctl_NW_p00__pc_fault;
  wire [4:0] ctl_NW_p00__row_bank;
  wire [2:0] ctl_NW_p00__row_op;
  wire [18:0] ctl_NW_p00__row_row;
  wire [0:0] ctl_NW_p00__row_v;
  wire [4:0] ctl_NW_p01__col_bank;
  wire [4:0] ctl_NW_p01__col_col;
  wire [255:0] ctl_NW_p01__col_data;
  wire [31:0] ctl_NW_p01__col_strb;
  wire [0:0] ctl_NW_p01__col_v;
  wire [0:0] ctl_NW_p01__col_we;
  wire [0:0] ctl_NW_p01__k_rdy;
  wire [0:0] ctl_NW_p01__k_wr_done;
  wire [3:0] ctl_NW_p01__kr_beat;
  wire [255:0] ctl_NW_p01__kr_data;
  wire [16:0] ctl_NW_p01__kr_tag;
  wire [0:0] ctl_NW_p01__kr_v;
  wire [5:0] ctl_NW_p01__owner_fault_split;
  wire [0:0] ctl_NW_p01__pc_fault;
  wire [4:0] ctl_NW_p01__row_bank;
  wire [2:0] ctl_NW_p01__row_op;
  wire [18:0] ctl_NW_p01__row_row;
  wire [0:0] ctl_NW_p01__row_v;
  wire [4:0] ctl_NW_p02__col_bank;
  wire [4:0] ctl_NW_p02__col_col;
  wire [255:0] ctl_NW_p02__col_data;
  wire [31:0] ctl_NW_p02__col_strb;
  wire [0:0] ctl_NW_p02__col_v;
  wire [0:0] ctl_NW_p02__col_we;
  wire [0:0] ctl_NW_p02__k_rdy;
  wire [0:0] ctl_NW_p02__k_wr_done;
  wire [3:0] ctl_NW_p02__kr_beat;
  wire [255:0] ctl_NW_p02__kr_data;
  wire [16:0] ctl_NW_p02__kr_tag;
  wire [0:0] ctl_NW_p02__kr_v;
  wire [5:0] ctl_NW_p02__owner_fault_split;
  wire [0:0] ctl_NW_p02__pc_fault;
  wire [4:0] ctl_NW_p02__row_bank;
  wire [2:0] ctl_NW_p02__row_op;
  wire [18:0] ctl_NW_p02__row_row;
  wire [0:0] ctl_NW_p02__row_v;
  wire [4:0] ctl_NW_p03__col_bank;
  wire [4:0] ctl_NW_p03__col_col;
  wire [255:0] ctl_NW_p03__col_data;
  wire [31:0] ctl_NW_p03__col_strb;
  wire [0:0] ctl_NW_p03__col_v;
  wire [0:0] ctl_NW_p03__col_we;
  wire [0:0] ctl_NW_p03__k_rdy;
  wire [0:0] ctl_NW_p03__k_wr_done;
  wire [3:0] ctl_NW_p03__kr_beat;
  wire [255:0] ctl_NW_p03__kr_data;
  wire [16:0] ctl_NW_p03__kr_tag;
  wire [0:0] ctl_NW_p03__kr_v;
  wire [5:0] ctl_NW_p03__owner_fault_split;
  wire [0:0] ctl_NW_p03__pc_fault;
  wire [4:0] ctl_NW_p03__row_bank;
  wire [2:0] ctl_NW_p03__row_op;
  wire [18:0] ctl_NW_p03__row_row;
  wire [0:0] ctl_NW_p03__row_v;
  wire [4:0] ctl_NW_p04__col_bank;
  wire [4:0] ctl_NW_p04__col_col;
  wire [255:0] ctl_NW_p04__col_data;
  wire [31:0] ctl_NW_p04__col_strb;
  wire [0:0] ctl_NW_p04__col_v;
  wire [0:0] ctl_NW_p04__col_we;
  wire [0:0] ctl_NW_p04__k_rdy;
  wire [0:0] ctl_NW_p04__k_wr_done;
  wire [3:0] ctl_NW_p04__kr_beat;
  wire [255:0] ctl_NW_p04__kr_data;
  wire [16:0] ctl_NW_p04__kr_tag;
  wire [0:0] ctl_NW_p04__kr_v;
  wire [5:0] ctl_NW_p04__owner_fault_split;
  wire [0:0] ctl_NW_p04__pc_fault;
  wire [4:0] ctl_NW_p04__row_bank;
  wire [2:0] ctl_NW_p04__row_op;
  wire [18:0] ctl_NW_p04__row_row;
  wire [0:0] ctl_NW_p04__row_v;
  wire [4:0] ctl_NW_p05__col_bank;
  wire [4:0] ctl_NW_p05__col_col;
  wire [255:0] ctl_NW_p05__col_data;
  wire [31:0] ctl_NW_p05__col_strb;
  wire [0:0] ctl_NW_p05__col_v;
  wire [0:0] ctl_NW_p05__col_we;
  wire [0:0] ctl_NW_p05__k_rdy;
  wire [0:0] ctl_NW_p05__k_wr_done;
  wire [3:0] ctl_NW_p05__kr_beat;
  wire [255:0] ctl_NW_p05__kr_data;
  wire [16:0] ctl_NW_p05__kr_tag;
  wire [0:0] ctl_NW_p05__kr_v;
  wire [5:0] ctl_NW_p05__owner_fault_split;
  wire [0:0] ctl_NW_p05__pc_fault;
  wire [4:0] ctl_NW_p05__row_bank;
  wire [2:0] ctl_NW_p05__row_op;
  wire [18:0] ctl_NW_p05__row_row;
  wire [0:0] ctl_NW_p05__row_v;
  wire [4:0] ctl_NW_p06__col_bank;
  wire [4:0] ctl_NW_p06__col_col;
  wire [255:0] ctl_NW_p06__col_data;
  wire [31:0] ctl_NW_p06__col_strb;
  wire [0:0] ctl_NW_p06__col_v;
  wire [0:0] ctl_NW_p06__col_we;
  wire [0:0] ctl_NW_p06__k_rdy;
  wire [0:0] ctl_NW_p06__k_wr_done;
  wire [3:0] ctl_NW_p06__kr_beat;
  wire [255:0] ctl_NW_p06__kr_data;
  wire [16:0] ctl_NW_p06__kr_tag;
  wire [0:0] ctl_NW_p06__kr_v;
  wire [5:0] ctl_NW_p06__owner_fault_split;
  wire [0:0] ctl_NW_p06__pc_fault;
  wire [4:0] ctl_NW_p06__row_bank;
  wire [2:0] ctl_NW_p06__row_op;
  wire [18:0] ctl_NW_p06__row_row;
  wire [0:0] ctl_NW_p06__row_v;
  wire [4:0] ctl_NW_p07__col_bank;
  wire [4:0] ctl_NW_p07__col_col;
  wire [255:0] ctl_NW_p07__col_data;
  wire [31:0] ctl_NW_p07__col_strb;
  wire [0:0] ctl_NW_p07__col_v;
  wire [0:0] ctl_NW_p07__col_we;
  wire [0:0] ctl_NW_p07__k_rdy;
  wire [0:0] ctl_NW_p07__k_wr_done;
  wire [3:0] ctl_NW_p07__kr_beat;
  wire [255:0] ctl_NW_p07__kr_data;
  wire [16:0] ctl_NW_p07__kr_tag;
  wire [0:0] ctl_NW_p07__kr_v;
  wire [5:0] ctl_NW_p07__owner_fault_split;
  wire [0:0] ctl_NW_p07__pc_fault;
  wire [4:0] ctl_NW_p07__row_bank;
  wire [2:0] ctl_NW_p07__row_op;
  wire [18:0] ctl_NW_p07__row_row;
  wire [0:0] ctl_NW_p07__row_v;
  wire [4:0] ctl_NW_p08__col_bank;
  wire [4:0] ctl_NW_p08__col_col;
  wire [255:0] ctl_NW_p08__col_data;
  wire [31:0] ctl_NW_p08__col_strb;
  wire [0:0] ctl_NW_p08__col_v;
  wire [0:0] ctl_NW_p08__col_we;
  wire [0:0] ctl_NW_p08__k_rdy;
  wire [0:0] ctl_NW_p08__k_wr_done;
  wire [3:0] ctl_NW_p08__kr_beat;
  wire [255:0] ctl_NW_p08__kr_data;
  wire [16:0] ctl_NW_p08__kr_tag;
  wire [0:0] ctl_NW_p08__kr_v;
  wire [5:0] ctl_NW_p08__owner_fault_split;
  wire [0:0] ctl_NW_p08__pc_fault;
  wire [4:0] ctl_NW_p08__row_bank;
  wire [2:0] ctl_NW_p08__row_op;
  wire [18:0] ctl_NW_p08__row_row;
  wire [0:0] ctl_NW_p08__row_v;
  wire [4:0] ctl_NW_p09__col_bank;
  wire [4:0] ctl_NW_p09__col_col;
  wire [255:0] ctl_NW_p09__col_data;
  wire [31:0] ctl_NW_p09__col_strb;
  wire [0:0] ctl_NW_p09__col_v;
  wire [0:0] ctl_NW_p09__col_we;
  wire [0:0] ctl_NW_p09__k_rdy;
  wire [0:0] ctl_NW_p09__k_wr_done;
  wire [3:0] ctl_NW_p09__kr_beat;
  wire [255:0] ctl_NW_p09__kr_data;
  wire [16:0] ctl_NW_p09__kr_tag;
  wire [0:0] ctl_NW_p09__kr_v;
  wire [5:0] ctl_NW_p09__owner_fault_split;
  wire [0:0] ctl_NW_p09__pc_fault;
  wire [4:0] ctl_NW_p09__row_bank;
  wire [2:0] ctl_NW_p09__row_op;
  wire [18:0] ctl_NW_p09__row_row;
  wire [0:0] ctl_NW_p09__row_v;
  wire [4:0] ctl_NW_p10__col_bank;
  wire [4:0] ctl_NW_p10__col_col;
  wire [255:0] ctl_NW_p10__col_data;
  wire [31:0] ctl_NW_p10__col_strb;
  wire [0:0] ctl_NW_p10__col_v;
  wire [0:0] ctl_NW_p10__col_we;
  wire [0:0] ctl_NW_p10__k_rdy;
  wire [0:0] ctl_NW_p10__k_wr_done;
  wire [3:0] ctl_NW_p10__kr_beat;
  wire [255:0] ctl_NW_p10__kr_data;
  wire [16:0] ctl_NW_p10__kr_tag;
  wire [0:0] ctl_NW_p10__kr_v;
  wire [5:0] ctl_NW_p10__owner_fault_split;
  wire [0:0] ctl_NW_p10__pc_fault;
  wire [4:0] ctl_NW_p10__row_bank;
  wire [2:0] ctl_NW_p10__row_op;
  wire [18:0] ctl_NW_p10__row_row;
  wire [0:0] ctl_NW_p10__row_v;
  wire [4:0] ctl_NW_p11__col_bank;
  wire [4:0] ctl_NW_p11__col_col;
  wire [255:0] ctl_NW_p11__col_data;
  wire [31:0] ctl_NW_p11__col_strb;
  wire [0:0] ctl_NW_p11__col_v;
  wire [0:0] ctl_NW_p11__col_we;
  wire [0:0] ctl_NW_p11__k_rdy;
  wire [0:0] ctl_NW_p11__k_wr_done;
  wire [3:0] ctl_NW_p11__kr_beat;
  wire [255:0] ctl_NW_p11__kr_data;
  wire [16:0] ctl_NW_p11__kr_tag;
  wire [0:0] ctl_NW_p11__kr_v;
  wire [5:0] ctl_NW_p11__owner_fault_split;
  wire [0:0] ctl_NW_p11__pc_fault;
  wire [4:0] ctl_NW_p11__row_bank;
  wire [2:0] ctl_NW_p11__row_op;
  wire [18:0] ctl_NW_p11__row_row;
  wire [0:0] ctl_NW_p11__row_v;
  wire [4:0] ctl_NW_p12__col_bank;
  wire [4:0] ctl_NW_p12__col_col;
  wire [255:0] ctl_NW_p12__col_data;
  wire [31:0] ctl_NW_p12__col_strb;
  wire [0:0] ctl_NW_p12__col_v;
  wire [0:0] ctl_NW_p12__col_we;
  wire [0:0] ctl_NW_p12__k_rdy;
  wire [0:0] ctl_NW_p12__k_wr_done;
  wire [3:0] ctl_NW_p12__kr_beat;
  wire [255:0] ctl_NW_p12__kr_data;
  wire [16:0] ctl_NW_p12__kr_tag;
  wire [0:0] ctl_NW_p12__kr_v;
  wire [5:0] ctl_NW_p12__owner_fault_split;
  wire [0:0] ctl_NW_p12__pc_fault;
  wire [4:0] ctl_NW_p12__row_bank;
  wire [2:0] ctl_NW_p12__row_op;
  wire [18:0] ctl_NW_p12__row_row;
  wire [0:0] ctl_NW_p12__row_v;
  wire [4:0] ctl_NW_p13__col_bank;
  wire [4:0] ctl_NW_p13__col_col;
  wire [255:0] ctl_NW_p13__col_data;
  wire [31:0] ctl_NW_p13__col_strb;
  wire [0:0] ctl_NW_p13__col_v;
  wire [0:0] ctl_NW_p13__col_we;
  wire [0:0] ctl_NW_p13__k_rdy;
  wire [0:0] ctl_NW_p13__k_wr_done;
  wire [3:0] ctl_NW_p13__kr_beat;
  wire [255:0] ctl_NW_p13__kr_data;
  wire [16:0] ctl_NW_p13__kr_tag;
  wire [0:0] ctl_NW_p13__kr_v;
  wire [5:0] ctl_NW_p13__owner_fault_split;
  wire [0:0] ctl_NW_p13__pc_fault;
  wire [4:0] ctl_NW_p13__row_bank;
  wire [2:0] ctl_NW_p13__row_op;
  wire [18:0] ctl_NW_p13__row_row;
  wire [0:0] ctl_NW_p13__row_v;
  wire [4:0] ctl_NW_p14__col_bank;
  wire [4:0] ctl_NW_p14__col_col;
  wire [255:0] ctl_NW_p14__col_data;
  wire [31:0] ctl_NW_p14__col_strb;
  wire [0:0] ctl_NW_p14__col_v;
  wire [0:0] ctl_NW_p14__col_we;
  wire [0:0] ctl_NW_p14__k_rdy;
  wire [0:0] ctl_NW_p14__k_wr_done;
  wire [3:0] ctl_NW_p14__kr_beat;
  wire [255:0] ctl_NW_p14__kr_data;
  wire [16:0] ctl_NW_p14__kr_tag;
  wire [0:0] ctl_NW_p14__kr_v;
  wire [5:0] ctl_NW_p14__owner_fault_split;
  wire [0:0] ctl_NW_p14__pc_fault;
  wire [4:0] ctl_NW_p14__row_bank;
  wire [2:0] ctl_NW_p14__row_op;
  wire [18:0] ctl_NW_p14__row_row;
  wire [0:0] ctl_NW_p14__row_v;
  wire [4:0] ctl_NW_p15__col_bank;
  wire [4:0] ctl_NW_p15__col_col;
  wire [255:0] ctl_NW_p15__col_data;
  wire [31:0] ctl_NW_p15__col_strb;
  wire [0:0] ctl_NW_p15__col_v;
  wire [0:0] ctl_NW_p15__col_we;
  wire [0:0] ctl_NW_p15__k_rdy;
  wire [0:0] ctl_NW_p15__k_wr_done;
  wire [3:0] ctl_NW_p15__kr_beat;
  wire [255:0] ctl_NW_p15__kr_data;
  wire [16:0] ctl_NW_p15__kr_tag;
  wire [0:0] ctl_NW_p15__kr_v;
  wire [5:0] ctl_NW_p15__owner_fault_split;
  wire [0:0] ctl_NW_p15__pc_fault;
  wire [4:0] ctl_NW_p15__row_bank;
  wire [2:0] ctl_NW_p15__row_op;
  wire [18:0] ctl_NW_p15__row_row;
  wire [0:0] ctl_NW_p15__row_v;
  wire [4:0] ctl_NW_p16__col_bank;
  wire [4:0] ctl_NW_p16__col_col;
  wire [255:0] ctl_NW_p16__col_data;
  wire [31:0] ctl_NW_p16__col_strb;
  wire [0:0] ctl_NW_p16__col_v;
  wire [0:0] ctl_NW_p16__col_we;
  wire [0:0] ctl_NW_p16__k_rdy;
  wire [0:0] ctl_NW_p16__k_wr_done;
  wire [3:0] ctl_NW_p16__kr_beat;
  wire [255:0] ctl_NW_p16__kr_data;
  wire [16:0] ctl_NW_p16__kr_tag;
  wire [0:0] ctl_NW_p16__kr_v;
  wire [5:0] ctl_NW_p16__owner_fault_split;
  wire [0:0] ctl_NW_p16__pc_fault;
  wire [4:0] ctl_NW_p16__row_bank;
  wire [2:0] ctl_NW_p16__row_op;
  wire [18:0] ctl_NW_p16__row_row;
  wire [0:0] ctl_NW_p16__row_v;
  wire [4:0] ctl_NW_p17__col_bank;
  wire [4:0] ctl_NW_p17__col_col;
  wire [255:0] ctl_NW_p17__col_data;
  wire [31:0] ctl_NW_p17__col_strb;
  wire [0:0] ctl_NW_p17__col_v;
  wire [0:0] ctl_NW_p17__col_we;
  wire [0:0] ctl_NW_p17__k_rdy;
  wire [0:0] ctl_NW_p17__k_wr_done;
  wire [3:0] ctl_NW_p17__kr_beat;
  wire [255:0] ctl_NW_p17__kr_data;
  wire [16:0] ctl_NW_p17__kr_tag;
  wire [0:0] ctl_NW_p17__kr_v;
  wire [5:0] ctl_NW_p17__owner_fault_split;
  wire [0:0] ctl_NW_p17__pc_fault;
  wire [4:0] ctl_NW_p17__row_bank;
  wire [2:0] ctl_NW_p17__row_op;
  wire [18:0] ctl_NW_p17__row_row;
  wire [0:0] ctl_NW_p17__row_v;
  wire [4:0] ctl_NW_p18__col_bank;
  wire [4:0] ctl_NW_p18__col_col;
  wire [255:0] ctl_NW_p18__col_data;
  wire [31:0] ctl_NW_p18__col_strb;
  wire [0:0] ctl_NW_p18__col_v;
  wire [0:0] ctl_NW_p18__col_we;
  wire [0:0] ctl_NW_p18__k_rdy;
  wire [0:0] ctl_NW_p18__k_wr_done;
  wire [3:0] ctl_NW_p18__kr_beat;
  wire [255:0] ctl_NW_p18__kr_data;
  wire [16:0] ctl_NW_p18__kr_tag;
  wire [0:0] ctl_NW_p18__kr_v;
  wire [5:0] ctl_NW_p18__owner_fault_split;
  wire [0:0] ctl_NW_p18__pc_fault;
  wire [4:0] ctl_NW_p18__row_bank;
  wire [2:0] ctl_NW_p18__row_op;
  wire [18:0] ctl_NW_p18__row_row;
  wire [0:0] ctl_NW_p18__row_v;
  wire [4:0] ctl_NW_p19__col_bank;
  wire [4:0] ctl_NW_p19__col_col;
  wire [255:0] ctl_NW_p19__col_data;
  wire [31:0] ctl_NW_p19__col_strb;
  wire [0:0] ctl_NW_p19__col_v;
  wire [0:0] ctl_NW_p19__col_we;
  wire [0:0] ctl_NW_p19__k_rdy;
  wire [0:0] ctl_NW_p19__k_wr_done;
  wire [3:0] ctl_NW_p19__kr_beat;
  wire [255:0] ctl_NW_p19__kr_data;
  wire [16:0] ctl_NW_p19__kr_tag;
  wire [0:0] ctl_NW_p19__kr_v;
  wire [5:0] ctl_NW_p19__owner_fault_split;
  wire [0:0] ctl_NW_p19__pc_fault;
  wire [4:0] ctl_NW_p19__row_bank;
  wire [2:0] ctl_NW_p19__row_op;
  wire [18:0] ctl_NW_p19__row_row;
  wire [0:0] ctl_NW_p19__row_v;
  wire [4:0] ctl_NW_p20__col_bank;
  wire [4:0] ctl_NW_p20__col_col;
  wire [255:0] ctl_NW_p20__col_data;
  wire [31:0] ctl_NW_p20__col_strb;
  wire [0:0] ctl_NW_p20__col_v;
  wire [0:0] ctl_NW_p20__col_we;
  wire [0:0] ctl_NW_p20__k_rdy;
  wire [0:0] ctl_NW_p20__k_wr_done;
  wire [3:0] ctl_NW_p20__kr_beat;
  wire [255:0] ctl_NW_p20__kr_data;
  wire [16:0] ctl_NW_p20__kr_tag;
  wire [0:0] ctl_NW_p20__kr_v;
  wire [5:0] ctl_NW_p20__owner_fault_split;
  wire [0:0] ctl_NW_p20__pc_fault;
  wire [4:0] ctl_NW_p20__row_bank;
  wire [2:0] ctl_NW_p20__row_op;
  wire [18:0] ctl_NW_p20__row_row;
  wire [0:0] ctl_NW_p20__row_v;
  wire [4:0] ctl_NW_p21__col_bank;
  wire [4:0] ctl_NW_p21__col_col;
  wire [255:0] ctl_NW_p21__col_data;
  wire [31:0] ctl_NW_p21__col_strb;
  wire [0:0] ctl_NW_p21__col_v;
  wire [0:0] ctl_NW_p21__col_we;
  wire [0:0] ctl_NW_p21__k_rdy;
  wire [0:0] ctl_NW_p21__k_wr_done;
  wire [3:0] ctl_NW_p21__kr_beat;
  wire [255:0] ctl_NW_p21__kr_data;
  wire [16:0] ctl_NW_p21__kr_tag;
  wire [0:0] ctl_NW_p21__kr_v;
  wire [5:0] ctl_NW_p21__owner_fault_split;
  wire [0:0] ctl_NW_p21__pc_fault;
  wire [4:0] ctl_NW_p21__row_bank;
  wire [2:0] ctl_NW_p21__row_op;
  wire [18:0] ctl_NW_p21__row_row;
  wire [0:0] ctl_NW_p21__row_v;
  wire [4:0] ctl_NW_p22__col_bank;
  wire [4:0] ctl_NW_p22__col_col;
  wire [255:0] ctl_NW_p22__col_data;
  wire [31:0] ctl_NW_p22__col_strb;
  wire [0:0] ctl_NW_p22__col_v;
  wire [0:0] ctl_NW_p22__col_we;
  wire [0:0] ctl_NW_p22__k_rdy;
  wire [0:0] ctl_NW_p22__k_wr_done;
  wire [3:0] ctl_NW_p22__kr_beat;
  wire [255:0] ctl_NW_p22__kr_data;
  wire [16:0] ctl_NW_p22__kr_tag;
  wire [0:0] ctl_NW_p22__kr_v;
  wire [5:0] ctl_NW_p22__owner_fault_split;
  wire [0:0] ctl_NW_p22__pc_fault;
  wire [4:0] ctl_NW_p22__row_bank;
  wire [2:0] ctl_NW_p22__row_op;
  wire [18:0] ctl_NW_p22__row_row;
  wire [0:0] ctl_NW_p22__row_v;
  wire [4:0] ctl_NW_p23__col_bank;
  wire [4:0] ctl_NW_p23__col_col;
  wire [255:0] ctl_NW_p23__col_data;
  wire [31:0] ctl_NW_p23__col_strb;
  wire [0:0] ctl_NW_p23__col_v;
  wire [0:0] ctl_NW_p23__col_we;
  wire [0:0] ctl_NW_p23__k_rdy;
  wire [0:0] ctl_NW_p23__k_wr_done;
  wire [3:0] ctl_NW_p23__kr_beat;
  wire [255:0] ctl_NW_p23__kr_data;
  wire [16:0] ctl_NW_p23__kr_tag;
  wire [0:0] ctl_NW_p23__kr_v;
  wire [5:0] ctl_NW_p23__owner_fault_split;
  wire [0:0] ctl_NW_p23__pc_fault;
  wire [4:0] ctl_NW_p23__row_bank;
  wire [2:0] ctl_NW_p23__row_op;
  wire [18:0] ctl_NW_p23__row_row;
  wire [0:0] ctl_NW_p23__row_v;
  wire [4:0] ctl_NW_p24__col_bank;
  wire [4:0] ctl_NW_p24__col_col;
  wire [255:0] ctl_NW_p24__col_data;
  wire [31:0] ctl_NW_p24__col_strb;
  wire [0:0] ctl_NW_p24__col_v;
  wire [0:0] ctl_NW_p24__col_we;
  wire [0:0] ctl_NW_p24__k_rdy;
  wire [0:0] ctl_NW_p24__k_wr_done;
  wire [3:0] ctl_NW_p24__kr_beat;
  wire [255:0] ctl_NW_p24__kr_data;
  wire [16:0] ctl_NW_p24__kr_tag;
  wire [0:0] ctl_NW_p24__kr_v;
  wire [5:0] ctl_NW_p24__owner_fault_split;
  wire [0:0] ctl_NW_p24__pc_fault;
  wire [4:0] ctl_NW_p24__row_bank;
  wire [2:0] ctl_NW_p24__row_op;
  wire [18:0] ctl_NW_p24__row_row;
  wire [0:0] ctl_NW_p24__row_v;
  wire [4:0] ctl_NW_p25__col_bank;
  wire [4:0] ctl_NW_p25__col_col;
  wire [255:0] ctl_NW_p25__col_data;
  wire [31:0] ctl_NW_p25__col_strb;
  wire [0:0] ctl_NW_p25__col_v;
  wire [0:0] ctl_NW_p25__col_we;
  wire [0:0] ctl_NW_p25__k_rdy;
  wire [0:0] ctl_NW_p25__k_wr_done;
  wire [3:0] ctl_NW_p25__kr_beat;
  wire [255:0] ctl_NW_p25__kr_data;
  wire [16:0] ctl_NW_p25__kr_tag;
  wire [0:0] ctl_NW_p25__kr_v;
  wire [5:0] ctl_NW_p25__owner_fault_split;
  wire [0:0] ctl_NW_p25__pc_fault;
  wire [4:0] ctl_NW_p25__row_bank;
  wire [2:0] ctl_NW_p25__row_op;
  wire [18:0] ctl_NW_p25__row_row;
  wire [0:0] ctl_NW_p25__row_v;
  wire [4:0] ctl_NW_p26__col_bank;
  wire [4:0] ctl_NW_p26__col_col;
  wire [255:0] ctl_NW_p26__col_data;
  wire [31:0] ctl_NW_p26__col_strb;
  wire [0:0] ctl_NW_p26__col_v;
  wire [0:0] ctl_NW_p26__col_we;
  wire [0:0] ctl_NW_p26__k_rdy;
  wire [0:0] ctl_NW_p26__k_wr_done;
  wire [3:0] ctl_NW_p26__kr_beat;
  wire [255:0] ctl_NW_p26__kr_data;
  wire [16:0] ctl_NW_p26__kr_tag;
  wire [0:0] ctl_NW_p26__kr_v;
  wire [5:0] ctl_NW_p26__owner_fault_split;
  wire [0:0] ctl_NW_p26__pc_fault;
  wire [4:0] ctl_NW_p26__row_bank;
  wire [2:0] ctl_NW_p26__row_op;
  wire [18:0] ctl_NW_p26__row_row;
  wire [0:0] ctl_NW_p26__row_v;
  wire [4:0] ctl_NW_p27__col_bank;
  wire [4:0] ctl_NW_p27__col_col;
  wire [255:0] ctl_NW_p27__col_data;
  wire [31:0] ctl_NW_p27__col_strb;
  wire [0:0] ctl_NW_p27__col_v;
  wire [0:0] ctl_NW_p27__col_we;
  wire [0:0] ctl_NW_p27__k_rdy;
  wire [0:0] ctl_NW_p27__k_wr_done;
  wire [3:0] ctl_NW_p27__kr_beat;
  wire [255:0] ctl_NW_p27__kr_data;
  wire [16:0] ctl_NW_p27__kr_tag;
  wire [0:0] ctl_NW_p27__kr_v;
  wire [5:0] ctl_NW_p27__owner_fault_split;
  wire [0:0] ctl_NW_p27__pc_fault;
  wire [4:0] ctl_NW_p27__row_bank;
  wire [2:0] ctl_NW_p27__row_op;
  wire [18:0] ctl_NW_p27__row_row;
  wire [0:0] ctl_NW_p27__row_v;
  wire [4:0] ctl_NW_p28__col_bank;
  wire [4:0] ctl_NW_p28__col_col;
  wire [255:0] ctl_NW_p28__col_data;
  wire [31:0] ctl_NW_p28__col_strb;
  wire [0:0] ctl_NW_p28__col_v;
  wire [0:0] ctl_NW_p28__col_we;
  wire [0:0] ctl_NW_p28__k_rdy;
  wire [0:0] ctl_NW_p28__k_wr_done;
  wire [3:0] ctl_NW_p28__kr_beat;
  wire [255:0] ctl_NW_p28__kr_data;
  wire [16:0] ctl_NW_p28__kr_tag;
  wire [0:0] ctl_NW_p28__kr_v;
  wire [5:0] ctl_NW_p28__owner_fault_split;
  wire [0:0] ctl_NW_p28__pc_fault;
  wire [4:0] ctl_NW_p28__row_bank;
  wire [2:0] ctl_NW_p28__row_op;
  wire [18:0] ctl_NW_p28__row_row;
  wire [0:0] ctl_NW_p28__row_v;
  wire [4:0] ctl_NW_p29__col_bank;
  wire [4:0] ctl_NW_p29__col_col;
  wire [255:0] ctl_NW_p29__col_data;
  wire [31:0] ctl_NW_p29__col_strb;
  wire [0:0] ctl_NW_p29__col_v;
  wire [0:0] ctl_NW_p29__col_we;
  wire [0:0] ctl_NW_p29__k_rdy;
  wire [0:0] ctl_NW_p29__k_wr_done;
  wire [3:0] ctl_NW_p29__kr_beat;
  wire [255:0] ctl_NW_p29__kr_data;
  wire [16:0] ctl_NW_p29__kr_tag;
  wire [0:0] ctl_NW_p29__kr_v;
  wire [5:0] ctl_NW_p29__owner_fault_split;
  wire [0:0] ctl_NW_p29__pc_fault;
  wire [4:0] ctl_NW_p29__row_bank;
  wire [2:0] ctl_NW_p29__row_op;
  wire [18:0] ctl_NW_p29__row_row;
  wire [0:0] ctl_NW_p29__row_v;
  wire [4:0] ctl_NW_p30__col_bank;
  wire [4:0] ctl_NW_p30__col_col;
  wire [255:0] ctl_NW_p30__col_data;
  wire [31:0] ctl_NW_p30__col_strb;
  wire [0:0] ctl_NW_p30__col_v;
  wire [0:0] ctl_NW_p30__col_we;
  wire [0:0] ctl_NW_p30__k_rdy;
  wire [0:0] ctl_NW_p30__k_wr_done;
  wire [3:0] ctl_NW_p30__kr_beat;
  wire [255:0] ctl_NW_p30__kr_data;
  wire [16:0] ctl_NW_p30__kr_tag;
  wire [0:0] ctl_NW_p30__kr_v;
  wire [5:0] ctl_NW_p30__owner_fault_split;
  wire [0:0] ctl_NW_p30__pc_fault;
  wire [4:0] ctl_NW_p30__row_bank;
  wire [2:0] ctl_NW_p30__row_op;
  wire [18:0] ctl_NW_p30__row_row;
  wire [0:0] ctl_NW_p30__row_v;
  wire [4:0] ctl_NW_p31__col_bank;
  wire [4:0] ctl_NW_p31__col_col;
  wire [255:0] ctl_NW_p31__col_data;
  wire [31:0] ctl_NW_p31__col_strb;
  wire [0:0] ctl_NW_p31__col_v;
  wire [0:0] ctl_NW_p31__col_we;
  wire [0:0] ctl_NW_p31__k_rdy;
  wire [0:0] ctl_NW_p31__k_wr_done;
  wire [3:0] ctl_NW_p31__kr_beat;
  wire [255:0] ctl_NW_p31__kr_data;
  wire [16:0] ctl_NW_p31__kr_tag;
  wire [0:0] ctl_NW_p31__kr_v;
  wire [5:0] ctl_NW_p31__owner_fault_split;
  wire [0:0] ctl_NW_p31__pc_fault;
  wire [4:0] ctl_NW_p31__row_bank;
  wire [2:0] ctl_NW_p31__row_op;
  wire [18:0] ctl_NW_p31__row_row;
  wire [0:0] ctl_NW_p31__row_v;
  wire [1023:0] cxdl_NE0_q__dw_d;
  wire [17:0] cxdl_NE0_q__dw_row;
  wire [1:0] cxdl_NE0_q__dw_v;
  wire [0:0] cxdl_NE0_q__fault;
  wire [523:0] cxdl_NE0_s__b0;
  wire [523:0] cxdl_NE0_s__b1;
  wire [0:0] cxdl_NE0_s__sfault_s;
  wire [7:0] cxdl_NE0_s__v0;
  wire [7:0] cxdl_NE0_s__v1;
  wire [1023:0] cxdl_NE1_q__dw_d;
  wire [17:0] cxdl_NE1_q__dw_row;
  wire [1:0] cxdl_NE1_q__dw_v;
  wire [0:0] cxdl_NE1_q__fault;
  wire [523:0] cxdl_NE1_s__b0;
  wire [523:0] cxdl_NE1_s__b1;
  wire [0:0] cxdl_NE1_s__sfault_s;
  wire [7:0] cxdl_NE1_s__v0;
  wire [7:0] cxdl_NE1_s__v1;
  wire [1023:0] cxdl_NE2_q__dw_d;
  wire [17:0] cxdl_NE2_q__dw_row;
  wire [1:0] cxdl_NE2_q__dw_v;
  wire [0:0] cxdl_NE2_q__fault;
  wire [523:0] cxdl_NE2_s__b0;
  wire [523:0] cxdl_NE2_s__b1;
  wire [0:0] cxdl_NE2_s__sfault_s;
  wire [7:0] cxdl_NE2_s__v0;
  wire [7:0] cxdl_NE2_s__v1;
  wire [1023:0] cxdl_NE3_q__dw_d;
  wire [17:0] cxdl_NE3_q__dw_row;
  wire [1:0] cxdl_NE3_q__dw_v;
  wire [0:0] cxdl_NE3_q__fault;
  wire [523:0] cxdl_NE3_s__b0;
  wire [523:0] cxdl_NE3_s__b1;
  wire [0:0] cxdl_NE3_s__sfault_s;
  wire [7:0] cxdl_NE3_s__v0;
  wire [7:0] cxdl_NE3_s__v1;
  wire [1023:0] cxdl_NW0_q__dw_d;
  wire [17:0] cxdl_NW0_q__dw_row;
  wire [1:0] cxdl_NW0_q__dw_v;
  wire [0:0] cxdl_NW0_q__fault;
  wire [523:0] cxdl_NW0_s__b0;
  wire [523:0] cxdl_NW0_s__b1;
  wire [0:0] cxdl_NW0_s__sfault_s;
  wire [7:0] cxdl_NW0_s__v0;
  wire [7:0] cxdl_NW0_s__v1;
  wire [1023:0] cxdl_NW1_q__dw_d;
  wire [17:0] cxdl_NW1_q__dw_row;
  wire [1:0] cxdl_NW1_q__dw_v;
  wire [0:0] cxdl_NW1_q__fault;
  wire [523:0] cxdl_NW1_s__b0;
  wire [523:0] cxdl_NW1_s__b1;
  wire [0:0] cxdl_NW1_s__sfault_s;
  wire [7:0] cxdl_NW1_s__v0;
  wire [7:0] cxdl_NW1_s__v1;
  wire [1023:0] cxdl_NW2_q__dw_d;
  wire [17:0] cxdl_NW2_q__dw_row;
  wire [1:0] cxdl_NW2_q__dw_v;
  wire [0:0] cxdl_NW2_q__fault;
  wire [523:0] cxdl_NW2_s__b0;
  wire [523:0] cxdl_NW2_s__b1;
  wire [0:0] cxdl_NW2_s__sfault_s;
  wire [7:0] cxdl_NW2_s__v0;
  wire [7:0] cxdl_NW2_s__v1;
  wire [1023:0] cxdl_NW3_q__dw_d;
  wire [17:0] cxdl_NW3_q__dw_row;
  wire [1:0] cxdl_NW3_q__dw_v;
  wire [0:0] cxdl_NW3_q__fault;
  wire [523:0] cxdl_NW3_s__b0;
  wire [523:0] cxdl_NW3_s__b1;
  wire [0:0] cxdl_NW3_s__sfault_s;
  wire [7:0] cxdl_NW3_s__v0;
  wire [7:0] cxdl_NW3_s__v1;
  wire [0:0] cxij_NE_q__fault;
  wire [1023:0] cxij_NE_q__ob0;
  wire [1023:0] cxij_NE_q__ob1;
  wire [1023:0] cxij_NE_s__inj_d;
  wire [0:0] cxij_NE_s__ins_coll;
  wire [31:0] cxij_NE_s__jb0;
  wire [31:0] cxij_NE_s__jb1;
  wire [0:0] cxij_NE_s__sfault_s;
  wire [0:0] cxij_NW_q__fault;
  wire [1023:0] cxij_NW_q__ob0;
  wire [1023:0] cxij_NW_q__ob1;
  wire [1023:0] cxij_NW_s__inj_d;
  wire [0:0] cxij_NW_s__ins_coll;
  wire [31:0] cxij_NW_s__jb0;
  wire [31:0] cxij_NW_s__jb1;
  wire [0:0] cxij_NW_s__sfault_s;
  wire [260:0] cxrc_NE_q__cb0;
  wire [260:0] cxrc_NE_q__cb1;
  wire [0:0] cxrc_NE_q__fault;
  wire [4:0] cxrc_NE_q__rr_wa;
  wire [255:0] cxrc_NE_q__rr_wd;
  wire [0:0] cxrc_NE_q__rr_wv;
  wire [31:0] cxrc_NE_q__sfu_x;
  wire [527:0] cxrc_NE_s__ob0;
  wire [527:0] cxrc_NE_s__ob1;
  wire [267:0] cxrc_NE_s__rb0;
  wire [267:0] cxrc_NE_s__rb1;
  wire [0:0] cxrc_NE_s__rc_coll;
  wire [255:0] cxrc_NE_s__rc_d;
  wire [2:0] cxrc_NE_s__rc_tag;
  wire [0:0] cxrc_NE_s__rc_v;
  wire [0:0] cxrc_NE_s__sfault_s;
  wire [260:0] cxrc_NW_q__cb0;
  wire [260:0] cxrc_NW_q__cb1;
  wire [0:0] cxrc_NW_q__fault;
  wire [4:0] cxrc_NW_q__rr_wa;
  wire [255:0] cxrc_NW_q__rr_wd;
  wire [0:0] cxrc_NW_q__rr_wv;
  wire [31:0] cxrc_NW_q__sfu_x;
  wire [527:0] cxrc_NW_s__ob0;
  wire [527:0] cxrc_NW_s__ob1;
  wire [267:0] cxrc_NW_s__rb0;
  wire [267:0] cxrc_NW_s__rb1;
  wire [0:0] cxrc_NW_s__rc_coll;
  wire [255:0] cxrc_NW_s__rc_d;
  wire [2:0] cxrc_NW_s__rc_tag;
  wire [0:0] cxrc_NW_s__rc_v;
  wire [0:0] cxrc_NW_s__sfault_s;
  wire [0:0] ep_N0__fault;
  wire [10:0] ep_N0__fault_cause;
  wire [2:0] ep_N0__h_cause;
  wire [611:0] ep_N0__h_rx_frame;
  wire [0:0] ep_N0__h_rx_v;
  wire [0:0] ep_N0__h_up;
  wire [0:0] ep_N0__phy_up;
  wire [1:0] ep_N0__rx_block_ready;
  wire [611:0] ep_N0__rx_pin_flit;
  wire [0:0] ep_N0__rx_pin_v;
  wire [511:0] ep_N0__sd_tx;
  wire [0:0] ep_N2__fault;
  wire [10:0] ep_N2__fault_cause;
  wire [0:0] ep_N2__phy_up;
  wire [1:0] ep_N2__rx_block_ready;
  wire [611:0] ep_N2__rx_pin_flit;
  wire [0:0] ep_N2__rx_pin_v;
  wire [511:0] ep_N2__sd_tx;
  wire [0:0] ep_S0__fault;
  wire [10:0] ep_S0__fault_cause;
  wire [0:0] ep_S0__phy_up;
  wire [1:0] ep_S0__rx_block_ready;
  wire [611:0] ep_S0__rx_pin_flit;
  wire [0:0] ep_S0__rx_pin_v;
  wire [511:0] ep_S0__sd_tx;
  wire [0:0] ep_S1__fault;
  wire [10:0] ep_S1__fault_cause;
  wire [0:0] ep_S1__phy_up;
  wire [1:0] ep_S1__rx_block_ready;
  wire [611:0] ep_S1__rx_pin_flit;
  wire [0:0] ep_S1__rx_pin_v;
  wire [511:0] ep_S1__sd_tx;
  wire [0:0] ep_S3__fault;
  wire [10:0] ep_S3__fault_cause;
  wire [0:0] ep_S3__phy_up;
  wire [1:0] ep_S3__rx_block_ready;
  wire [611:0] ep_S3__rx_pin_flit;
  wire [0:0] ep_S3__rx_pin_v;
  wire [511:0] ep_S3__sd_tx;
  wire [0:0] epcal_NE__active;
  wire [0:0] epcal_NE__calendar_v;
  wire [0:0] epcal_NE__done;
  wire [0:0] epcal_NE__fault;
  wire [37:0] epcal_NE__payload;
  wire [0:0] epcal_NE__tgt_configured;
  wire [0:0] epcal_NE__tgt_fault;
  wire [0:0] epcal_NW__active;
  wire [0:0] epcal_NW__calendar_v;
  wire [0:0] epcal_NW__done;
  wire [0:0] epcal_NW__fault;
  wire [56:0] epcal_NW__payload;
  wire [0:0] epcal_NW__tgt_configured;
  wire [0:0] epcal_NW__tgt_fault;
  wire [0:0] fcx_NE__fault;
  wire [0:0] fcx_NW__fault;
  wire [0:0] fl_NE0__fault;
  wire [0:0] fl_NE1__fault;
  wire [0:0] fl_NE2__fault;
  wire [0:0] fl_NE3__fault;
  wire [0:0] fl_NW0__fault;
  wire [0:0] fl_NW1__fault;
  wire [0:0] fl_NW2__fault;
  wire [0:0] fl_NW3__fault;
  wire [0:0] fr_NE__fault;
  wire [0:0] fr_NW__fault;
  wire [0:0] fs_NE__fault;
  wire [0:0] fs_NW__fault;
  wire [0:0] hb_argmax__busy;
  wire [337:0] hb_argmax__cq;
  wire [1:0] hb_argmax__cq_seq;
  wire [0:0] hb_argmax__done;
  wire [0:0] hb_argmax__fault;
  wire [0:0] hb_argmax__nan_flag;
  wire [135:0] hb_argmax__vm_rq;
  wire [0:0] hb_ckgen__pll_hbm;
  wire [0:0] hb_ckgen__pll_stream;
  wire [0:0] hb_ckgen__por_hbm;
  wire [0:0] hb_ckgen__por_stream;
  wire [511:0] hb_coll_NE__ag_d;
  wire [3:0] hb_coll_NE__ag_src;
  wire [5:0] hb_coll_NE__ag_tag;
  wire [1:0] hb_coll_NE__ag_v;
  wire [2179:0] hb_coll_NE__del_flit;
  wire [3:0] hb_coll_NE__del_valid;
  wire [0:0] hb_coll_NE__done;
  wire [0:0] hb_coll_NE__fault;
  wire [15:0] hb_coll_NE__fault_cause;
  wire [0:0] hb_coll_NE__hgi_busy;
  wire [159:0] hb_coll_NE__hgi_del_obase;
  wire [0:0] hb_coll_NE__hgi_done;
  wire [0:0] hb_coll_NE__hgi_fault;
  wire [159:0] hb_coll_NE__hgi_inj_addr;
  wire [31:0] hb_coll_NE__inj_idx;
  wire [1:0] hb_coll_NE__inj_rd;
  wire [255:0] hb_coll_NE__isa_lp_data;
  wire [57:0] hb_coll_NE__isa_ring;
  wire [279:0] hb_coll_NE__pr_ccw_o;
  wire [279:0] hb_coll_NE__pr_cw_o;
  wire [0:0] hb_coll_NE__program_configured;
  wire [0:0] hb_coll_NE__program_fault;
  wire [0:0] hb_coll_NE__program_init_busy;
  wire [1:0] hb_coll_NE__retry_requested;
  wire [255:0] hb_coll_NE__rr_d;
  wire [2:0] hb_coll_NE__rr_tag;
  wire [0:0] hb_coll_NE__rr_v;
  wire [31:0] hb_coll_NE__stat_cycles;
  wire [1223:0] hb_coll_NE__tx_pin_flit;
  wire [1:0] hb_coll_NE__tx_pin_v;
  wire [2247:0] hb_coll_NE__vm_kq;
  wire [135:0] hb_coll_NE__vm_rq;
  wire [511:0] hb_coll_NW__ag_d;
  wire [3:0] hb_coll_NW__ag_src;
  wire [5:0] hb_coll_NW__ag_tag;
  wire [1:0] hb_coll_NW__ag_v;
  wire [2179:0] hb_coll_NW__del_flit;
  wire [3:0] hb_coll_NW__del_valid;
  wire [0:0] hb_coll_NW__done;
  wire [0:0] hb_coll_NW__fault;
  wire [15:0] hb_coll_NW__fault_cause;
  wire [0:0] hb_coll_NW__hgi_busy;
  wire [159:0] hb_coll_NW__hgi_del_obase;
  wire [0:0] hb_coll_NW__hgi_done;
  wire [0:0] hb_coll_NW__hgi_fault;
  wire [159:0] hb_coll_NW__hgi_inj_addr;
  wire [31:0] hb_coll_NW__inj_idx;
  wire [1:0] hb_coll_NW__inj_rd;
  wire [255:0] hb_coll_NW__isa_lp_data;
  wire [57:0] hb_coll_NW__isa_ring;
  wire [279:0] hb_coll_NW__pr_ccw_o;
  wire [279:0] hb_coll_NW__pr_cw_o;
  wire [0:0] hb_coll_NW__program_configured;
  wire [0:0] hb_coll_NW__program_fault;
  wire [0:0] hb_coll_NW__program_init_busy;
  wire [2:0] hb_coll_NW__retry_requested;
  wire [255:0] hb_coll_NW__rr_d;
  wire [2:0] hb_coll_NW__rr_tag;
  wire [0:0] hb_coll_NW__rr_v;
  wire [31:0] hb_coll_NW__stat_cycles;
  wire [0:0] hb_coll_NW__tkx_arg_mode;
  wire [7:0] hb_coll_NW__tkx_cfg_g;
  wire [7:0] hb_coll_NW__tkx_cfg_gbase;
  wire [0:0] hb_coll_NW__tkx_cfg_has_r;
  wire [12:0] hb_coll_NW__tkx_cfg_k;
  wire [11:0] hb_coll_NW__tkx_cfg_n;
  wire [12:0] hb_coll_NW__tkx_cfg_nout;
  wire [39:0] hb_coll_NW__tkx_cfg_obase;
  wire [15:0] hb_coll_NW__tkx_cfg_pf;
  wire [39:0] hb_coll_NW__tkx_cfg_rbase;
  wire [2179:0] hb_coll_NW__tkx_del_flit;
  wire [3:0] hb_coll_NW__tkx_del_slot;
  wire [3:0] hb_coll_NW__tkx_del_valid;
  wire [0:0] hb_coll_NW__tkx_start;
  wire [1835:0] hb_coll_NW__tx_pin_flit;
  wire [2:0] hb_coll_NW__tx_pin_v;
  wire [2247:0] hb_coll_NW__vm_kq;
  wire [135:0] hb_coll_NW__vm_rq;
  wire [0:0] hb_dbk_NE__busy;
  wire [0:0] hb_dbk_NE__cp_active;
  wire [0:0] hb_dbk_NE__cp_configured;
  wire [0:0] hb_dbk_NE__cp_fault;
  wire [0:0] hb_dbk_NE__mv_done;
  wire [0:0] hb_dbk_NE__mv_fault;
  wire [0:0] hb_dbk_NE__mv_src;
  wire [0:0] hb_dbk_NE__quiet;
  wire [135:0] hb_dbk_NE__rq;
  wire [0:0] hb_dbk_NE__wb_fill_bank;
  wire [15:0] hb_dbk_NE__wb_fill_epoch;
  wire [0:0] hb_dbk_NE__wb_fill_start;
  wire [0:0] hb_dbk_NE__wb_reserve_bank;
  wire [31:0] hb_dbk_NE__wb_reserve_base;
  wire [15:0] hb_dbk_NE__wb_reserve_epoch;
  wire [11:0] hb_dbk_NE__wb_reserve_sectors;
  wire [0:0] hb_dbk_NE__wb_reserve_v;
  wire [2311:0] hb_dbk_NE__wd;
  wire [0:0] hb_dbk_NW__busy;
  wire [0:0] hb_dbk_NW__cp_active;
  wire [0:0] hb_dbk_NW__cp_configured;
  wire [0:0] hb_dbk_NW__cp_fault;
  wire [0:0] hb_dbk_NW__mv_done;
  wire [0:0] hb_dbk_NW__mv_fault;
  wire [0:0] hb_dbk_NW__mv_src;
  wire [0:0] hb_dbk_NW__quiet;
  wire [135:0] hb_dbk_NW__rq;
  wire [0:0] hb_dbk_NW__wb_fill_bank;
  wire [15:0] hb_dbk_NW__wb_fill_epoch;
  wire [0:0] hb_dbk_NW__wb_fill_start;
  wire [0:0] hb_dbk_NW__wb_reserve_bank;
  wire [31:0] hb_dbk_NW__wb_reserve_base;
  wire [15:0] hb_dbk_NW__wb_reserve_epoch;
  wire [11:0] hb_dbk_NW__wb_reserve_sectors;
  wire [0:0] hb_dbk_NW__wb_reserve_v;
  wire [2311:0] hb_dbk_NW__wd;
  wire [263:0] hb_idx__ctl__argmax_m;
  wire [337:0] hb_idx__ctl__cq;
  wire [1:0] hb_idx__ctl__cq_seq;
  wire [0:0] hb_idx__ctl__done;
  wire [0:0] hb_idx__ctl__fault;
  wire [2055:0] hb_idx__ctl__index_rr;
  wire [0:0] hb_idx__ctl__ingest_v;
  wire [0:0] hb_idx__ctl__link_clear;
  wire [0:0] hb_idx__ctl__link_emit;
  wire [0:0] hb_idx__ctl__link_flush;
  wire [3:0] hb_idx__ctl__link_group;
  wire [7:0] hb_idx__ctl__sel_addr;
  wire [3:0] hb_idx__ctl__sel_op;
  wire [1:0] hb_idx__ctl__sel_pass;
  wire [0:0] hb_idx__ctl__share_fault;
  wire [0:0] hb_idx__ctl__topk_busy;
  wire [0:0] hb_idx__ctl__topk_done;
  wire [0:0] hb_idx__ctl__topk_fault;
  wire [135:0] hb_idx__ctl__vm_rq;
  wire [0:0] hb_idx__link__fault;
  wire [9:0] hb_idx__link__selected_count;
  wire [2179:0] hb_idx__link__tx;
  wire [3:0] hb_idx__link__tx_v;
  wire [2055:0] hb_idx__nwsh__a_rr;
  wire [2055:0] hb_idx__nwsh__b_rr;
  wire [0:0] hb_idx__nwsh__fault;
  wire [135:0] hb_idx__nwsh__vm_rq;
  wire [1023:0] hb_idx__op_NE__block_data;
  wire [4:0] hb_idx__op_NE__block_head;
  wire [1:0] hb_idx__op_NE__block_number;
  wire [0:0] hb_idx__op_NE__block_v;
  wire [0:0] hb_idx__op_NE__fault;
  wire [15:0] hb_idx__op_NE__head_weight;
  wire [135:0] hb_idx__op_NE__vm_rq;
  wire [1023:0] hb_idx__op_NW__block_data;
  wire [4:0] hb_idx__op_NW__block_head;
  wire [1:0] hb_idx__op_NW__block_number;
  wire [0:0] hb_idx__op_NW__block_v;
  wire [0:0] hb_idx__op_NW__fault;
  wire [15:0] hb_idx__op_NW__head_weight;
  wire [135:0] hb_idx__op_NW__vm_rq;
  wire [1023:0] hb_idx__op_SE__block_data;
  wire [4:0] hb_idx__op_SE__block_head;
  wire [1:0] hb_idx__op_SE__block_number;
  wire [0:0] hb_idx__op_SE__block_v;
  wire [0:0] hb_idx__op_SE__fault;
  wire [15:0] hb_idx__op_SE__head_weight;
  wire [135:0] hb_idx__op_SE__vm_rq;
  wire [1023:0] hb_idx__op_SW__block_data;
  wire [4:0] hb_idx__op_SW__block_head;
  wire [1:0] hb_idx__op_SW__block_number;
  wire [0:0] hb_idx__op_SW__block_v;
  wire [0:0] hb_idx__op_SW__fault;
  wire [15:0] hb_idx__op_SW__head_weight;
  wire [135:0] hb_idx__op_SW__vm_rq;
  wire [0:0] hb_idx__q_NE__fault;
  wire [511:0] hb_idx__q_NE__ql_codes;
  wire [7:0] hb_idx__q_NE__ql_head;
  wire [31:0] hb_idx__q_NE__ql_sc;
  wire [0:0] hb_idx__q_NE__ql_v;
  wire [15:0] hb_idx__q_NE__ql_w;
  wire [0:0] hb_idx__q_NW__fault;
  wire [511:0] hb_idx__q_NW__ql_codes;
  wire [7:0] hb_idx__q_NW__ql_head;
  wire [31:0] hb_idx__q_NW__ql_sc;
  wire [0:0] hb_idx__q_NW__ql_v;
  wire [15:0] hb_idx__q_NW__ql_w;
  wire [0:0] hb_idx__q_SE__fault;
  wire [511:0] hb_idx__q_SE__ql_codes;
  wire [7:0] hb_idx__q_SE__ql_head;
  wire [31:0] hb_idx__q_SE__ql_sc;
  wire [0:0] hb_idx__q_SE__ql_v;
  wire [15:0] hb_idx__q_SE__ql_w;
  wire [0:0] hb_idx__q_SW__fault;
  wire [511:0] hb_idx__q_SW__ql_codes;
  wire [7:0] hb_idx__q_SW__ql_head;
  wire [31:0] hb_idx__q_SW__ql_sc;
  wire [0:0] hb_idx__q_SW__ql_v;
  wire [15:0] hb_idx__q_SW__ql_w;
  wire [0:0] hb_idx__qctl_NE__fault;
  wire [0:0] hb_idx__qctl_NE__frame_start;
  wire [7:0] hb_idx__qctl_NE__key_index;
  wire [0:0] hb_idx__qctl_NE__key_slot;
  wire [11:0] hb_idx__qctl_NE__nq;
  wire [0:0] hb_idx__qctl_NE__query_emit;
  wire [4:0] hb_idx__qctl_NE__query_emit_head;
  wire [6:0] hb_idx__qctl_NE__query_index;
  wire [0:0] hb_idx__qctl_NE__query_slot;
  wire [0:0] hb_idx__qctl_NE__weight_slot;
  wire [0:0] hb_idx__qctl_NW__fault;
  wire [0:0] hb_idx__qctl_NW__frame_start;
  wire [7:0] hb_idx__qctl_NW__key_index;
  wire [0:0] hb_idx__qctl_NW__key_slot;
  wire [11:0] hb_idx__qctl_NW__nq;
  wire [0:0] hb_idx__qctl_NW__query_emit;
  wire [4:0] hb_idx__qctl_NW__query_emit_head;
  wire [6:0] hb_idx__qctl_NW__query_index;
  wire [0:0] hb_idx__qctl_NW__query_slot;
  wire [0:0] hb_idx__qctl_NW__weight_slot;
  wire [0:0] hb_idx__qctl_SE__fault;
  wire [0:0] hb_idx__qctl_SE__frame_start;
  wire [7:0] hb_idx__qctl_SE__key_index;
  wire [0:0] hb_idx__qctl_SE__key_slot;
  wire [11:0] hb_idx__qctl_SE__nq;
  wire [0:0] hb_idx__qctl_SE__query_emit;
  wire [4:0] hb_idx__qctl_SE__query_emit_head;
  wire [6:0] hb_idx__qctl_SE__query_index;
  wire [0:0] hb_idx__qctl_SE__query_slot;
  wire [0:0] hb_idx__qctl_SE__weight_slot;
  wire [0:0] hb_idx__qctl_SW__fault;
  wire [0:0] hb_idx__qctl_SW__frame_start;
  wire [7:0] hb_idx__qctl_SW__key_index;
  wire [0:0] hb_idx__qctl_SW__key_slot;
  wire [11:0] hb_idx__qctl_SW__nq;
  wire [0:0] hb_idx__qctl_SW__query_emit;
  wire [4:0] hb_idx__qctl_SW__query_emit_head;
  wire [6:0] hb_idx__qctl_SW__query_index;
  wire [0:0] hb_idx__qctl_SW__query_slot;
  wire [0:0] hb_idx__qctl_SW__weight_slot;
  wire [0:0] hb_idx__s_NE__fault;
  wire [305:0] hb_idx__s_NE__score;
  wire [0:0] hb_idx__s_NW__fault;
  wire [305:0] hb_idx__s_NW__score;
  wire [0:0] hb_idx__s_SE__fault;
  wire [305:0] hb_idx__s_SE__score;
  wire [0:0] hb_idx__s_SW__fault;
  wire [305:0] hb_idx__s_SW__score;
  wire [0:0] hb_idx__selector__fault;
  wire [2367:0] hb_idx__selector__selected_line;
  wire [3:0] hb_idx__selector__selected_v;
  wire [593:0] hb_idx__xq_N__y;
  wire [593:0] hb_idx__xq_S__y;
  wire [1187:0] hb_idx__xqr__y;
  wire [0:0] hb_quant_NW__hbfd_qdq_split_and__Y;
  wire [0:0] hb_quant_NW__hbfd_qdq_split_or__Y;
  wire [0:0] hb_quant_NW__program_leaf__active;
  wire [47:0] hb_quant_NW__program_leaf__command;
  wire [0:0] hb_quant_NW__program_leaf__command_v;
  wire [0:0] hb_quant_NW__program_leaf__configured;
  wire [0:0] hb_quant_NW__program_leaf__done;
  wire [0:0] hb_quant_NW__program_leaf__fault;
  wire [33:0] hb_quant_NW__quant_NW0_lg__rq_o;
  wire [513:0] hb_quant_NW__quant_NW0_lg__rr_o;
  wire [561:0] hb_quant_NW__quant_NW0_lg__wq_o;
  wire [33:0] hb_quant_NW__quant_NW1_lg__rq_o;
  wire [513:0] hb_quant_NW__quant_NW1_lg__rr_o;
  wire [561:0] hb_quant_NW__quant_NW1_lg__wq_o;
  wire [33:0] hb_quant_NW__quant_NW2_lg__rq_o;
  wire [513:0] hb_quant_NW__quant_NW2_lg__rr_o;
  wire [561:0] hb_quant_NW__quant_NW2_lg__wq_o;
  wire [33:0] hb_quant_NW__quant_NW3_lg__rq_o;
  wire [513:0] hb_quant_NW__quant_NW3_lg__rr_o;
  wire [561:0] hb_quant_NW__quant_NW3_lg__wq_o;
  wire [0:0] hb_quant_NW__quant_NW_xp_ctl__beat_done;
  wire [127:0] hb_quant_NW__quant_NW_xp_ctl__dec_header;
  wire [0:0] hb_quant_NW__quant_NW_xp_ctl__dec_v;
  wire [0:0] hb_quant_NW__quant_NW_xp_ctl__fault;
  wire [0:0] hb_quant_NW__quant_NW_xp_ctl__record_done;
  wire [135:0] hb_quant_NW__quant_NW_xp_ctl__rq;
  wire [2:0] hb_quant_NW__quant_NW_xp_ctl__rsel;
  wire [127:0] hb_quant_NW__quant_NW_xp_ctl__wq_addr;
  wire [63:0] hb_quant_NW__quant_NW_xp_ctl__wq_mask;
  wire [7:0] hb_quant_NW__quant_NW_xp_ctl__wq_v;
  wire [2:0] hb_quant_NW__quant_NW_xp_ctl__wsel;
  wire [255:0] hb_quant_NW__quant_NW_xp_slice_0__rslice__gx_w;
  wire [255:0] hb_quant_NW__quant_NW_xp_slice_0__wslice__wq_w;
  wire [255:0] hb_quant_NW__quant_NW_xp_slice_1__rslice__gx_w;
  wire [255:0] hb_quant_NW__quant_NW_xp_slice_1__wslice__wq_w;
  wire [255:0] hb_quant_NW__quant_NW_xp_slice_2__rslice__gx_w;
  wire [255:0] hb_quant_NW__quant_NW_xp_slice_2__wslice__wq_w;
  wire [255:0] hb_quant_NW__quant_NW_xp_slice_3__rslice__gx_w;
  wire [255:0] hb_quant_NW__quant_NW_xp_slice_3__wslice__wq_w;
  wire [0:0] hb_quant_NW__u_dec__decode_fault;
  wire [0:0] hb_quant_NW__u_dec__fault;
  wire [0:0] hb_quant_NW__u_dec__vo;
  wire [511:0] hb_quant_NW__u_dec__y;
  wire [53:0] hb_router_ids__ids;
  wire [15:0] hb_router_ids__ids_cohort;
  wire [7:0] hb_router_ids__ids_layer;
  wire [0:0] hb_router_ids__ids_v;
  wire [2279:0] hb_vms_NE__bk_pq;
  wire [2207:0] hb_vms_NE__bk_xq;
  wire [2207:0] hb_vms_NE__bk_xq2;
  wire [2223:0] hb_vms_NE__ccw_out;
  wire [2223:0] hb_vms_NE__cw_out;
  wire [2:0] hb_vms_NE__hub_status;
  wire [1:0] hb_vms_NE__mirror_busy;
  wire [2:0] hb_vms_NE__ring_fault;
  wire [18:0] hb_vms_NE__vmstat;
  wire [284:0] hb_vms_NW__b0_pq;
  wire [275:0] hb_vms_NW__b0_xq;
  wire [275:0] hb_vms_NW__b0_xq2;
  wire [284:0] hb_vms_NW__b1_pq;
  wire [275:0] hb_vms_NW__b1_xq;
  wire [275:0] hb_vms_NW__b1_xq2;
  wire [284:0] hb_vms_NW__b2_pq;
  wire [275:0] hb_vms_NW__b2_xq;
  wire [275:0] hb_vms_NW__b2_xq2;
  wire [284:0] hb_vms_NW__b3_pq;
  wire [275:0] hb_vms_NW__b3_xq;
  wire [275:0] hb_vms_NW__b3_xq2;
  wire [284:0] hb_vms_NW__b4_pq;
  wire [275:0] hb_vms_NW__b4_xq;
  wire [275:0] hb_vms_NW__b4_xq2;
  wire [284:0] hb_vms_NW__b5_pq;
  wire [275:0] hb_vms_NW__b5_xq;
  wire [275:0] hb_vms_NW__b5_xq2;
  wire [284:0] hb_vms_NW__b6_pq;
  wire [275:0] hb_vms_NW__b6_xq;
  wire [275:0] hb_vms_NW__b6_xq2;
  wire [284:0] hb_vms_NW__b7_pq;
  wire [275:0] hb_vms_NW__b7_xq;
  wire [275:0] hb_vms_NW__b7_xq2;
  wire [2223:0] hb_vms_NW__ccw_out;
  wire [2223:0] hb_vms_NW__cw_out;
  wire [2:0] hb_vms_NW__hub_status;
  wire [1:0] hb_vms_NW__mirror_busy;
  wire [2:0] hb_vms_NW__ring_fault;
  wire [18:0] hb_vms_NW__vmstat;
  wire [2279:0] hb_vms_SE__bk_pq;
  wire [2207:0] hb_vms_SE__bk_xq;
  wire [2207:0] hb_vms_SE__bk_xq2;
  wire [2223:0] hb_vms_SE__ccw_out;
  wire [2223:0] hb_vms_SE__cw_out;
  wire [284:0] hb_vms_SW__b0_pq;
  wire [275:0] hb_vms_SW__b0_xq;
  wire [275:0] hb_vms_SW__b0_xq2;
  wire [284:0] hb_vms_SW__b1_pq;
  wire [275:0] hb_vms_SW__b1_xq;
  wire [275:0] hb_vms_SW__b1_xq2;
  wire [284:0] hb_vms_SW__b2_pq;
  wire [275:0] hb_vms_SW__b2_xq;
  wire [275:0] hb_vms_SW__b2_xq2;
  wire [284:0] hb_vms_SW__b3_pq;
  wire [275:0] hb_vms_SW__b3_xq;
  wire [275:0] hb_vms_SW__b3_xq2;
  wire [284:0] hb_vms_SW__b4_pq;
  wire [275:0] hb_vms_SW__b4_xq;
  wire [275:0] hb_vms_SW__b4_xq2;
  wire [284:0] hb_vms_SW__b5_pq;
  wire [275:0] hb_vms_SW__b5_xq;
  wire [275:0] hb_vms_SW__b5_xq2;
  wire [284:0] hb_vms_SW__b6_pq;
  wire [275:0] hb_vms_SW__b6_xq;
  wire [275:0] hb_vms_SW__b6_xq2;
  wire [284:0] hb_vms_SW__b7_pq;
  wire [275:0] hb_vms_SW__b7_xq;
  wire [275:0] hb_vms_SW__b7_xq2;
  wire [2223:0] hb_vms_SW__ccw_out;
  wire [547:0] hb_vms_SW__cr;
  wire [2223:0] hb_vms_SW__cw_out;
  wire [513:0] hc_NE0__c_rr;
  wire [1:0] hc_NE0__c_w_done;
  wire [0:0] hc_NE0__fault;
  wire [33:0] hc_NE0__near_rq;
  wire [561:0] hc_NE0__near_wq;
  wire [513:0] hc_NE1__c_rr;
  wire [1:0] hc_NE1__c_w_done;
  wire [0:0] hc_NE1__fault;
  wire [33:0] hc_NE1__near_rq;
  wire [561:0] hc_NE1__near_wq;
  wire [513:0] hc_NE2__c_rr;
  wire [1:0] hc_NE2__c_w_done;
  wire [0:0] hc_NE2__fault;
  wire [33:0] hc_NE2__near_rq;
  wire [561:0] hc_NE2__near_wq;
  wire [513:0] hc_NE3__c_rr;
  wire [1:0] hc_NE3__c_w_done;
  wire [0:0] hc_NE3__fault;
  wire [33:0] hc_NE3__near_rq;
  wire [561:0] hc_NE3__near_wq;
  wire [7:0] hc_NE__bd_nv;
  wire [0:0] hc_NE__bd_ss;
  wire [0:0] hc_NE__bd_v;
  wire [9:0] hc_NE__bd_wa;
  wire [9:0] hc_NE__bd_xa;
  wire [0:0] hc_NE__configured;
  wire [0:0] hc_NE__eng_fault;
  wire [0:0] hc_NE__gather_done;
  wire [31:0] hc_NE__gathered_mix_data;
  wire [2:0] hc_NE__gathered_mix_pos;
  wire [4:0] hc_NE__gathered_mix_row;
  wire [0:0] hc_NE__gathered_mix_v;
  wire [0:0] hc_NE__hcq_fault;
  wire [135:0] hc_NE__lg_rq;
  wire [2247:0] hc_NE__lg_wq;
  wire [0:0] hc_NE__program_active;
  wire [0:0] hc_NE__program_done;
  wire [31:0] hc_NE__ps;
  wire [0:0] hc_NE__ps_f;
  wire [0:0] hc_NE__ps_v;
  wire [0:0] hc_NE__residual_done;
  wire [0:0] hc_NE__rstb_e;
  wire [2:0] hc_NE__rstb_n;
  wire [2:0] hc_NE__rstb_s;
  wire [0:0] hc_NE__rstb_w;
  wire [13:0] hc_NE__wc_e;
  wire [13:0] hc_NE__wc_n;
  wire [13:0] hc_NE__wc_s;
  wire [13:0] hc_NE__wc_w;
  wire [1:0] hc_NE__xb_beat;
  wire [1:0] hc_NE__xb_beat_e;
  wire [1:0] hc_NE__xb_beat_n;
  wire [1:0] hc_NE__xb_beat_s;
  wire [255:0] hc_NE__xb_d0;
  wire [255:0] hc_NE__xb_d1;
  wire [255:0] hc_NE__xb_d2;
  wire [255:0] hc_NE__xb_d3;
  wire [255:0] hc_NE__xb_d4;
  wire [255:0] hc_NE__xb_d5;
  wire [255:0] hc_NE__xb_d6;
  wire [255:0] hc_NE__xb_d7;
  wire [0:0] hc_NE__xb_v;
  wire [0:0] hc_NE__xb_v_e;
  wire [0:0] hc_NE__xb_v_n;
  wire [0:0] hc_NE__xb_v_s;
  wire [513:0] hc_NW0__c_rr;
  wire [1:0] hc_NW0__c_w_done;
  wire [0:0] hc_NW0__fault;
  wire [33:0] hc_NW0__near_rq;
  wire [561:0] hc_NW0__near_wq;
  wire [513:0] hc_NW1__c_rr;
  wire [1:0] hc_NW1__c_w_done;
  wire [0:0] hc_NW1__fault;
  wire [33:0] hc_NW1__near_rq;
  wire [561:0] hc_NW1__near_wq;
  wire [513:0] hc_NW2__c_rr;
  wire [1:0] hc_NW2__c_w_done;
  wire [0:0] hc_NW2__fault;
  wire [33:0] hc_NW2__near_rq;
  wire [561:0] hc_NW2__near_wq;
  wire [513:0] hc_NW3__c_rr;
  wire [1:0] hc_NW3__c_w_done;
  wire [0:0] hc_NW3__fault;
  wire [33:0] hc_NW3__near_rq;
  wire [561:0] hc_NW3__near_wq;
  wire [7:0] hc_NW__bd_nv;
  wire [0:0] hc_NW__bd_ss;
  wire [0:0] hc_NW__bd_v;
  wire [9:0] hc_NW__bd_wa;
  wire [9:0] hc_NW__bd_xa;
  wire [0:0] hc_NW__configured;
  wire [0:0] hc_NW__eng_fault;
  wire [0:0] hc_NW__gather_done;
  wire [31:0] hc_NW__gathered_mix_data;
  wire [2:0] hc_NW__gathered_mix_pos;
  wire [4:0] hc_NW__gathered_mix_row;
  wire [0:0] hc_NW__gathered_mix_v;
  wire [0:0] hc_NW__hcq_fault;
  wire [135:0] hc_NW__lg_rq;
  wire [2247:0] hc_NW__lg_wq;
  wire [0:0] hc_NW__program_active;
  wire [0:0] hc_NW__program_done;
  wire [31:0] hc_NW__ps;
  wire [0:0] hc_NW__ps_f;
  wire [0:0] hc_NW__ps_v;
  wire [0:0] hc_NW__residual_done;
  wire [0:0] hc_NW__rstb_e;
  wire [2:0] hc_NW__rstb_n;
  wire [2:0] hc_NW__rstb_s;
  wire [0:0] hc_NW__rstb_w;
  wire [13:0] hc_NW__wc_e;
  wire [13:0] hc_NW__wc_n;
  wire [13:0] hc_NW__wc_s;
  wire [13:0] hc_NW__wc_w;
  wire [1:0] hc_NW__xb_beat;
  wire [1:0] hc_NW__xb_beat_e;
  wire [1:0] hc_NW__xb_beat_n;
  wire [1:0] hc_NW__xb_beat_s;
  wire [255:0] hc_NW__xb_d0;
  wire [255:0] hc_NW__xb_d1;
  wire [255:0] hc_NW__xb_d2;
  wire [255:0] hc_NW__xb_d3;
  wire [255:0] hc_NW__xb_d4;
  wire [255:0] hc_NW__xb_d5;
  wire [255:0] hc_NW__xb_d6;
  wire [255:0] hc_NW__xb_d7;
  wire [0:0] hc_NW__xb_v;
  wire [0:0] hc_NW__xb_v_e;
  wire [0:0] hc_NW__xb_v_n;
  wire [0:0] hc_NW__xb_v_s;
  wire [0:0] hc_eng__configured;
  wire [0:0] hc_eng__fault;
  wire [0:0] hc_eng__program_active;
  wire [0:0] hc_eng__program_done;
  wire [15:0] hc_eng__qd_nv;
  wire [1:0] hc_eng__qd_ss;
  wire [1:0] hc_eng__qd_v;
  wire [19:0] hc_eng__qd_wa;
  wire [19:0] hc_eng__qd_xa;
  wire [23:0] hc_eng__qi_cnt;
  wire [1:0] hc_eng__qi_kind;
  wire [9:0] hc_eng__qi_lo;
  wire [3:0] hc_eng__qi_slot;
  wire [1:0] hc_eng__qi_v;
  wire [11:0] hc_eng__qi_w;
  wire [19:0] hc_eng__qi_word;
  wire [1535:0] hc_eng__result;
  wire [5:0] hc_eng__result_position;
  wire [1:0] hc_eng__result_v;
  wire [0:0] hcb_NE0__f_out;
  wire [7:0] hcb_NE0__o_nv;
  wire [0:0] hcb_NE0__o_ss;
  wire [0:0] hcb_NE0__o_v;
  wire [9:0] hcb_NE0__o_wa;
  wire [9:0] hcb_NE0__o_xa;
  wire [4096:0] hcb_NE0__s_o;
  wire [4095:0] hcb_NE0__sum_out;
  wire [0:0] hcb_NE0__wfault;
  wire [0:0] hcb_NE1__f_out;
  wire [7:0] hcb_NE1__o_nv;
  wire [0:0] hcb_NE1__o_ss;
  wire [0:0] hcb_NE1__o_v;
  wire [9:0] hcb_NE1__o_wa;
  wire [9:0] hcb_NE1__o_xa;
  wire [4095:0] hcb_NE1__sum_out;
  wire [0:0] hcb_NE1__wfault;
  wire [0:0] hcb_NE2__f_out;
  wire [1:0] hcb_NE2__fa_j_o;
  wire [0:0] hcb_NE2__fa_rst_n_o;
  wire [9:0] hcb_NE2__fa_wa_o;
  wire [0:0] hcb_NE2__fa_wfault_o;
  wire [0:0] hcb_NE2__fa_wv_o;
  wire [1:0] hcb_NE2__fa_xb_beat_o;
  wire [255:0] hcb_NE2__fa_xb_d_o;
  wire [0:0] hcb_NE2__fa_xb_v_o;
  wire [0:0] hcb_NE2__fa_xv_o;
  wire [1:0] hcb_NE2__fb_j_o;
  wire [0:0] hcb_NE2__fb_rst_n_o;
  wire [9:0] hcb_NE2__fb_wa_o;
  wire [0:0] hcb_NE2__fb_wfault_o;
  wire [0:0] hcb_NE2__fb_wv_o;
  wire [1:0] hcb_NE2__fb_xb_beat_o;
  wire [255:0] hcb_NE2__fb_xb_d_o;
  wire [0:0] hcb_NE2__fb_xb_v_o;
  wire [0:0] hcb_NE2__fb_xv_o;
  wire [7:0] hcb_NE2__o_nv;
  wire [0:0] hcb_NE2__o_ss;
  wire [0:0] hcb_NE2__o_v;
  wire [9:0] hcb_NE2__o_wa;
  wire [9:0] hcb_NE2__o_xa;
  wire [4095:0] hcb_NE2__sum_out;
  wire [0:0] hcb_NE2__wfault;
  wire [0:0] hcb_NE3__f_out;
  wire [7:0] hcb_NE3__o_nv;
  wire [0:0] hcb_NE3__o_ss;
  wire [0:0] hcb_NE3__o_v;
  wire [9:0] hcb_NE3__o_wa;
  wire [9:0] hcb_NE3__o_xa;
  wire [4095:0] hcb_NE3__sum_out;
  wire [0:0] hcb_NE3__wfault;
  wire [0:0] hcb_NE4__f_out;
  wire [7:0] hcb_NE4__o_nv;
  wire [0:0] hcb_NE4__o_ss;
  wire [0:0] hcb_NE4__o_v;
  wire [9:0] hcb_NE4__o_wa;
  wire [9:0] hcb_NE4__o_xa;
  wire [4095:0] hcb_NE4__sum_out;
  wire [0:0] hcb_NE4__wfault;
  wire [0:0] hcb_NE5__f_out;
  wire [7:0] hcb_NE5__o_nv;
  wire [0:0] hcb_NE5__o_ss;
  wire [0:0] hcb_NE5__o_v;
  wire [9:0] hcb_NE5__o_wa;
  wire [9:0] hcb_NE5__o_xa;
  wire [4095:0] hcb_NE5__sum_out;
  wire [0:0] hcb_NE5__wfault;
  wire [0:0] hcb_NE6__f_out;
  wire [1:0] hcb_NE6__fa_j_o;
  wire [0:0] hcb_NE6__fa_rst_n_o;
  wire [9:0] hcb_NE6__fa_wa_o;
  wire [0:0] hcb_NE6__fa_wfault_o;
  wire [0:0] hcb_NE6__fa_wv_o;
  wire [1:0] hcb_NE6__fa_xb_beat_o;
  wire [255:0] hcb_NE6__fa_xb_d_o;
  wire [0:0] hcb_NE6__fa_xb_v_o;
  wire [0:0] hcb_NE6__fa_xv_o;
  wire [1:0] hcb_NE6__fb_j_o;
  wire [0:0] hcb_NE6__fb_rst_n_o;
  wire [9:0] hcb_NE6__fb_wa_o;
  wire [0:0] hcb_NE6__fb_wfault_o;
  wire [0:0] hcb_NE6__fb_wv_o;
  wire [1:0] hcb_NE6__fb_xb_beat_o;
  wire [255:0] hcb_NE6__fb_xb_d_o;
  wire [0:0] hcb_NE6__fb_xb_v_o;
  wire [0:0] hcb_NE6__fb_xv_o;
  wire [7:0] hcb_NE6__o_nv;
  wire [0:0] hcb_NE6__o_ss;
  wire [0:0] hcb_NE6__o_v;
  wire [9:0] hcb_NE6__o_wa;
  wire [9:0] hcb_NE6__o_xa;
  wire [4095:0] hcb_NE6__sum_out;
  wire [0:0] hcb_NE6__wfault;
  wire [0:0] hcb_NE7__f_out;
  wire [4095:0] hcb_NE7__sum_out;
  wire [0:0] hcb_NE7__wfault;
  wire [0:0] hcb_NW0__f_out;
  wire [7:0] hcb_NW0__o_nv;
  wire [0:0] hcb_NW0__o_ss;
  wire [0:0] hcb_NW0__o_v;
  wire [9:0] hcb_NW0__o_wa;
  wire [9:0] hcb_NW0__o_xa;
  wire [4096:0] hcb_NW0__s_o;
  wire [4095:0] hcb_NW0__sum_out;
  wire [0:0] hcb_NW0__wfault;
  wire [0:0] hcb_NW1__f_out;
  wire [7:0] hcb_NW1__o_nv;
  wire [0:0] hcb_NW1__o_ss;
  wire [0:0] hcb_NW1__o_v;
  wire [9:0] hcb_NW1__o_wa;
  wire [9:0] hcb_NW1__o_xa;
  wire [4095:0] hcb_NW1__sum_out;
  wire [0:0] hcb_NW1__wfault;
  wire [0:0] hcb_NW2__f_out;
  wire [1:0] hcb_NW2__fa_j_o;
  wire [0:0] hcb_NW2__fa_rst_n_o;
  wire [9:0] hcb_NW2__fa_wa_o;
  wire [0:0] hcb_NW2__fa_wfault_o;
  wire [0:0] hcb_NW2__fa_wv_o;
  wire [1:0] hcb_NW2__fa_xb_beat_o;
  wire [255:0] hcb_NW2__fa_xb_d_o;
  wire [0:0] hcb_NW2__fa_xb_v_o;
  wire [0:0] hcb_NW2__fa_xv_o;
  wire [1:0] hcb_NW2__fb_j_o;
  wire [0:0] hcb_NW2__fb_rst_n_o;
  wire [9:0] hcb_NW2__fb_wa_o;
  wire [0:0] hcb_NW2__fb_wfault_o;
  wire [0:0] hcb_NW2__fb_wv_o;
  wire [1:0] hcb_NW2__fb_xb_beat_o;
  wire [255:0] hcb_NW2__fb_xb_d_o;
  wire [0:0] hcb_NW2__fb_xb_v_o;
  wire [0:0] hcb_NW2__fb_xv_o;
  wire [7:0] hcb_NW2__o_nv;
  wire [0:0] hcb_NW2__o_ss;
  wire [0:0] hcb_NW2__o_v;
  wire [9:0] hcb_NW2__o_wa;
  wire [9:0] hcb_NW2__o_xa;
  wire [4095:0] hcb_NW2__sum_out;
  wire [0:0] hcb_NW2__wfault;
  wire [0:0] hcb_NW3__f_out;
  wire [7:0] hcb_NW3__o_nv;
  wire [0:0] hcb_NW3__o_ss;
  wire [0:0] hcb_NW3__o_v;
  wire [9:0] hcb_NW3__o_wa;
  wire [9:0] hcb_NW3__o_xa;
  wire [4095:0] hcb_NW3__sum_out;
  wire [0:0] hcb_NW3__wfault;
  wire [0:0] hcb_NW4__f_out;
  wire [7:0] hcb_NW4__o_nv;
  wire [0:0] hcb_NW4__o_ss;
  wire [0:0] hcb_NW4__o_v;
  wire [9:0] hcb_NW4__o_wa;
  wire [9:0] hcb_NW4__o_xa;
  wire [4095:0] hcb_NW4__sum_out;
  wire [0:0] hcb_NW4__wfault;
  wire [0:0] hcb_NW5__f_out;
  wire [7:0] hcb_NW5__o_nv;
  wire [0:0] hcb_NW5__o_ss;
  wire [0:0] hcb_NW5__o_v;
  wire [9:0] hcb_NW5__o_wa;
  wire [9:0] hcb_NW5__o_xa;
  wire [4095:0] hcb_NW5__sum_out;
  wire [0:0] hcb_NW5__wfault;
  wire [0:0] hcb_NW6__f_out;
  wire [1:0] hcb_NW6__fa_j_o;
  wire [0:0] hcb_NW6__fa_rst_n_o;
  wire [9:0] hcb_NW6__fa_wa_o;
  wire [0:0] hcb_NW6__fa_wfault_o;
  wire [0:0] hcb_NW6__fa_wv_o;
  wire [1:0] hcb_NW6__fa_xb_beat_o;
  wire [255:0] hcb_NW6__fa_xb_d_o;
  wire [0:0] hcb_NW6__fa_xb_v_o;
  wire [0:0] hcb_NW6__fa_xv_o;
  wire [1:0] hcb_NW6__fb_j_o;
  wire [0:0] hcb_NW6__fb_rst_n_o;
  wire [9:0] hcb_NW6__fb_wa_o;
  wire [0:0] hcb_NW6__fb_wfault_o;
  wire [0:0] hcb_NW6__fb_wv_o;
  wire [1:0] hcb_NW6__fb_xb_beat_o;
  wire [255:0] hcb_NW6__fb_xb_d_o;
  wire [0:0] hcb_NW6__fb_xb_v_o;
  wire [0:0] hcb_NW6__fb_xv_o;
  wire [7:0] hcb_NW6__o_nv;
  wire [0:0] hcb_NW6__o_ss;
  wire [0:0] hcb_NW6__o_v;
  wire [9:0] hcb_NW6__o_wa;
  wire [9:0] hcb_NW6__o_xa;
  wire [4095:0] hcb_NW6__sum_out;
  wire [0:0] hcb_NW6__wfault;
  wire [0:0] hcb_NW7__f_out;
  wire [4095:0] hcb_NW7__sum_out;
  wire [0:0] hcb_NW7__wfault;
  wire [511:0] hcollb_NE__ag_d;
  wire [3:0] hcollb_NE__ag_src;
  wire [5:0] hcollb_NE__ag_tag;
  wire [1:0] hcollb_NE__ag_v;
  wire [279:0] hcollb_NE__ccw_o;
  wire [279:0] hcollb_NE__cw_o;
  wire [0:0] hcollb_NE__fault;
  wire [511:0] hcollb_NW__ag_d;
  wire [3:0] hcollb_NW__ag_src;
  wire [5:0] hcollb_NW__ag_tag;
  wire [1:0] hcollb_NW__ag_v;
  wire [279:0] hcollb_NW__ccw_o;
  wire [279:0] hcollb_NW__cw_o;
  wire [0:0] hcollb_NW__fault;
  wire [0:0] hcollgi_NE__active;
  wire [0:0] hcollgi_NE__configured;
  wire [0:0] hcollgi_NE__done;
  wire [0:0] hcollgi_NE__fault;
  wire [52:0] hcollgi_NE__ld_desc;
  wire [9:0] hcollgi_NE__ld_ev_k;
  wire [0:0] hcollgi_NE__ld_ev_v;
  wire [0:0] hcollgi_NE__ld_fire;
  wire [511:0] hcollgi_NE__ld_p_d;
  wire [1:0] hcollgi_NE__ld_p_v;
  wire [0:0] hcollgi_NE__ra_add_rhs_acc;
  wire [1:0] hcollgi_NE__ra_add_src;
  wire [2:0] hcollgi_NE__ra_add_tag;
  wire [0:0] hcollgi_NE__ra_add_v;
  wire [255:0] hcollgi_NE__ra_lp_data;
  wire [2:0] hcollgi_NE__ra_lp_tag;
  wire [0:0] hcollgi_NE__ra_lp_we;
  wire [0:0] hcollgi_NE__ra_rr_local;
  wire [2:0] hcollgi_NE__ra_rr_local_tag;
  wire [3:0] hcollgi_NE__ra_rx_kind;
  wire [1:0] hcollgi_NE__ra_rx_slot;
  wire [3:0] hcollgi_NE__ra_rx_src;
  wire [5:0] hcollgi_NE__ra_rx_tag;
  wire [0:0] hcollgi_NE__ra_state_add_rhs_acc;
  wire [1:0] hcollgi_NE__ra_state_add_src;
  wire [2:0] hcollgi_NE__ra_state_add_tag;
  wire [0:0] hcollgi_NE__ra_state_read_add;
  wire [0:0] hcollgi_NE__ra_state_read_rr;
  wire [0:0] hcollgi_NE__ra_state_read_tx;
  wire [2:0] hcollgi_NE__ra_state_rr_tag;
  wire [0:0] hcollgi_NE__ra_state_tx_acc;
  wire [2:0] hcollgi_NE__ra_state_tx_tag;
  wire [0:0] hcollgi_NE__ra_tx_acc;
  wire [1:0] hcollgi_NE__ra_tx_dst;
  wire [1:0] hcollgi_NE__ra_tx_forward;
  wire [0:0] hcollgi_NE__ra_tx_gather;
  wire [1:0] hcollgi_NE__ra_tx_inject;
  wire [0:0] hcollgi_NE__ra_tx_result;
  wire [2:0] hcollgi_NE__ra_tx_tag;
  wire [3:0] hcollgi_NE__ra_tx_ttl;
  wire [255:0] hcollgi_NE__rb_lp_data;
  wire [2:0] hcollgi_NE__rb_lp_tag;
  wire [0:0] hcollgi_NE__rb_lp_we;
  wire [3:0] hcollgi_NE__rb_rx_kind;
  wire [1:0] hcollgi_NE__rb_rx_slot;
  wire [3:0] hcollgi_NE__rb_rx_src;
  wire [5:0] hcollgi_NE__rb_rx_tag;
  wire [0:0] hcollgi_NE__rb_state_read_tx;
  wire [2:0] hcollgi_NE__rb_state_tx_tag;
  wire [1:0] hcollgi_NE__rb_tx_forward;
  wire [1:0] hcollgi_NE__rb_tx_inject;
  wire [2:0] hcollgi_NE__rb_tx_tag;
  wire [3:0] hcollgi_NE__rb_tx_ttl;
  wire [0:0] hcollgi_NE__tgt_fault;
  wire [67:0] hcollgi_NE__vm_rq_hi;
  wire [67:0] hcollgi_NE__vm_rq_lo;
  wire [0:0] hcollgi_NW__active;
  wire [0:0] hcollgi_NW__configured;
  wire [0:0] hcollgi_NW__done;
  wire [0:0] hcollgi_NW__fault;
  wire [52:0] hcollgi_NW__ld_desc;
  wire [9:0] hcollgi_NW__ld_ev_k;
  wire [0:0] hcollgi_NW__ld_ev_v;
  wire [0:0] hcollgi_NW__ld_fire;
  wire [511:0] hcollgi_NW__ld_p_d;
  wire [1:0] hcollgi_NW__ld_p_v;
  wire [0:0] hcollgi_NW__ra_add_rhs_acc;
  wire [1:0] hcollgi_NW__ra_add_src;
  wire [2:0] hcollgi_NW__ra_add_tag;
  wire [0:0] hcollgi_NW__ra_add_v;
  wire [255:0] hcollgi_NW__ra_lp_data;
  wire [2:0] hcollgi_NW__ra_lp_tag;
  wire [0:0] hcollgi_NW__ra_lp_we;
  wire [0:0] hcollgi_NW__ra_rr_local;
  wire [2:0] hcollgi_NW__ra_rr_local_tag;
  wire [3:0] hcollgi_NW__ra_rx_kind;
  wire [1:0] hcollgi_NW__ra_rx_slot;
  wire [3:0] hcollgi_NW__ra_rx_src;
  wire [5:0] hcollgi_NW__ra_rx_tag;
  wire [0:0] hcollgi_NW__ra_state_add_rhs_acc;
  wire [1:0] hcollgi_NW__ra_state_add_src;
  wire [2:0] hcollgi_NW__ra_state_add_tag;
  wire [0:0] hcollgi_NW__ra_state_read_add;
  wire [0:0] hcollgi_NW__ra_state_read_rr;
  wire [0:0] hcollgi_NW__ra_state_read_tx;
  wire [2:0] hcollgi_NW__ra_state_rr_tag;
  wire [0:0] hcollgi_NW__ra_state_tx_acc;
  wire [2:0] hcollgi_NW__ra_state_tx_tag;
  wire [0:0] hcollgi_NW__ra_tx_acc;
  wire [1:0] hcollgi_NW__ra_tx_dst;
  wire [1:0] hcollgi_NW__ra_tx_forward;
  wire [0:0] hcollgi_NW__ra_tx_gather;
  wire [1:0] hcollgi_NW__ra_tx_inject;
  wire [0:0] hcollgi_NW__ra_tx_result;
  wire [2:0] hcollgi_NW__ra_tx_tag;
  wire [3:0] hcollgi_NW__ra_tx_ttl;
  wire [255:0] hcollgi_NW__rb_lp_data;
  wire [2:0] hcollgi_NW__rb_lp_tag;
  wire [0:0] hcollgi_NW__rb_lp_we;
  wire [3:0] hcollgi_NW__rb_rx_kind;
  wire [1:0] hcollgi_NW__rb_rx_slot;
  wire [3:0] hcollgi_NW__rb_rx_src;
  wire [5:0] hcollgi_NW__rb_rx_tag;
  wire [0:0] hcollgi_NW__rb_state_read_tx;
  wire [2:0] hcollgi_NW__rb_state_tx_tag;
  wire [1:0] hcollgi_NW__rb_tx_forward;
  wire [1:0] hcollgi_NW__rb_tx_inject;
  wire [2:0] hcollgi_NW__rb_tx_tag;
  wire [3:0] hcollgi_NW__rb_tx_ttl;
  wire [0:0] hcollgi_NW__tgt_fault;
  wire [67:0] hcollgi_NW__vm_rq_hi;
  wire [67:0] hcollgi_NW__vm_rq_lo;
  wire [0:0] hcollgl_NE__fault;
  wire [1123:0] hcollgl_NE__vm_kq_hi;
  wire [1123:0] hcollgl_NE__vm_kq_lo;
  wire [0:0] hcollgl_NW__fault;
  wire [1123:0] hcollgl_NW__vm_kq_hi;
  wire [1123:0] hcollgl_NW__vm_kq_lo;
  wire [0:0] hcollks_NE__fault;
  wire [0:0] hcollks_NE_p0__fault;
  wire [561:0] hcollks_NE_p0__vm_kq;
  wire [0:0] hcollks_NE_p1__fault;
  wire [561:0] hcollks_NE_p1__vm_kq;
  wire [0:0] hcollks_NE_p2__fault;
  wire [561:0] hcollks_NE_p2__vm_kq;
  wire [0:0] hcollks_NE_p3__fault;
  wire [561:0] hcollks_NE_p3__vm_kq;
  wire [0:0] hcollks_NW__fault;
  wire [0:0] hcollks_NW_p0__fault;
  wire [561:0] hcollks_NW_p0__vm_kq;
  wire [0:0] hcollks_NW_p1__fault;
  wire [561:0] hcollks_NW_p1__vm_kq;
  wire [0:0] hcollks_NW_p2__fault;
  wire [561:0] hcollks_NW_p2__vm_kq;
  wire [0:0] hcollks_NW_p3__fault;
  wire [561:0] hcollks_NW_p3__vm_kq;
  wire [2055:0] hcollrs_NE__a_rr;
  wire [2055:0] hcollrs_NE__b_rr;
  wire [0:0] hcollrs_NE__fault;
  wire [135:0] hcollrs_NE__vm_rq;
  wire [2055:0] hcollrs_NW__a_rr;
  wire [2055:0] hcollrs_NW__b_rr;
  wire [0:0] hcollrs_NW__fault;
  wire [135:0] hcollrs_NW__vm_rq;
  wire [11:0] hleaf_NE__a_cfg_addr;
  wire [255:0] hleaf_NE__a_cfg_data;
  wire [7:0] hleaf_NE__a_cfg_target;
  wire [0:0] hleaf_NE__a_cfg_v;
  wire [11:0] hleaf_NE__a_desc_base;
  wire [12:0] hleaf_NE__a_desc_limit;
  wire [15:0] hleaf_NE__a_desc_loops;
  wire [0:0] hleaf_NE__a_desc_v;
  wire [0:0] hleaf_NE__a_launch_v;
  wire [11:0] hleaf_NE__b_cfg_addr;
  wire [255:0] hleaf_NE__b_cfg_data;
  wire [7:0] hleaf_NE__b_cfg_target;
  wire [0:0] hleaf_NE__b_cfg_v;
  wire [11:0] hleaf_NE__b_desc_base;
  wire [12:0] hleaf_NE__b_desc_limit;
  wire [15:0] hleaf_NE__b_desc_loops;
  wire [0:0] hleaf_NE__b_desc_v;
  wire [0:0] hleaf_NE__b_launch_v;
  wire [20:0] hleaf_NE__s_active;
  wire [30:0] hleaf_NE__s_fault;
  wire [20:0] hleaf_NE__s_ready;
  wire [11:0] hleaf_NW__a_cfg_addr;
  wire [255:0] hleaf_NW__a_cfg_data;
  wire [7:0] hleaf_NW__a_cfg_target;
  wire [0:0] hleaf_NW__a_cfg_v;
  wire [11:0] hleaf_NW__a_desc_base;
  wire [12:0] hleaf_NW__a_desc_limit;
  wire [15:0] hleaf_NW__a_desc_loops;
  wire [0:0] hleaf_NW__a_desc_v;
  wire [0:0] hleaf_NW__a_launch_v;
  wire [11:0] hleaf_NW__b_cfg_addr;
  wire [255:0] hleaf_NW__b_cfg_data;
  wire [7:0] hleaf_NW__b_cfg_target;
  wire [0:0] hleaf_NW__b_cfg_v;
  wire [11:0] hleaf_NW__b_desc_base;
  wire [12:0] hleaf_NW__b_desc_limit;
  wire [15:0] hleaf_NW__b_desc_loops;
  wire [0:0] hleaf_NW__b_desc_v;
  wire [0:0] hleaf_NW__b_launch_v;
  wire [19:0] hleaf_NW__s_active;
  wire [31:0] hleaf_NW__s_fault;
  wire [19:0] hleaf_NW__s_ready;
  wire [11:0] host_cp_ingress__cfg_addr;
  wire [255:0] host_cp_ingress__cfg_data;
  wire [7:0] host_cp_ingress__cfg_target;
  wire [0:0] host_cp_ingress__cfg_v;
  wire [11:0] host_cp_ingress__desc_base;
  wire [12:0] host_cp_ingress__desc_limit;
  wire [15:0] host_cp_ingress__desc_loops;
  wire [0:0] host_cp_ingress__desc_v;
  wire [0:0] host_cp_ingress__fault;
  wire [0:0] host_cp_ingress__launch_v;
  wire [31:0] host_cp_ingress__obs_q_d;
  wire [7:0] host_cp_ingress__obs_q_idx;
  wire [0:0] host_cp_ingress__obs_q_v;
  wire [0:0] host_cp_ingress__s_arready;
  wire [0:0] host_cp_ingress__s_awready;
  wire [1:0] host_cp_ingress__s_bresp;
  wire [0:0] host_cp_ingress__s_bvalid;
  wire [31:0] host_cp_ingress__s_rdata;
  wire [0:0] host_cp_ingress__s_rvalid;
  wire [0:0] host_cp_ingress__s_wready;
  wire [0:0] host_cp_rxs__ep_rx_arm_bank;
  wire [0:0] host_cp_rxs__ep_rx_arm_v;
  wire [6:0] host_cp_rxs__ep_rx_block_words;
  wire [0:0] host_cp_rxs__ep_rx_release_bank;
  wire [0:0] host_cp_rxs__ep_rx_release_v;
  wire [0:0] host_cp_rxs__ep_rx_slot_bank;
  wire [5:0] host_cp_rxs__ep_rx_slot_index;
  wire [0:0] host_cp_rxs__ep_rx_slot_v;
  wire [611:0] host_cp_rxs__ep_tx_frame;
  wire [0:0] host_cp_rxs__ep_tx_v;
  wire [0:0] host_cp_rxs__land_fault;
  wire [0:0] host_cp_rxs__link_fault;
  wire [0:0] host_cp_rxs__protocol_fault;
  wire [11:0] host_cp_rxs__s_araddr;
  wire [0:0] host_cp_rxs__s_arvalid;
  wire [11:0] host_cp_rxs__s_awaddr;
  wire [0:0] host_cp_rxs__s_awvalid;
  wire [0:0] host_cp_rxs__s_bready;
  wire [0:0] host_cp_rxs__s_rready;
  wire [31:0] host_cp_rxs__s_wdata;
  wire [3:0] host_cp_rxs__s_wstrb;
  wire [0:0] host_cp_rxs__s_wvalid;
  wire [0:0] host_cp_rxs__seq_fault;
  wire [0:0] host_ep__fault;
  wire [10:0] host_ep__fault_cause;
  wire [0:0] host_ep__phy_up;
  wire [1:0] host_ep__rx_block_ready;
  wire [611:0] host_ep__rx_pin_flit;
  wire [0:0] host_ep__rx_pin_v;
  wire [611:0] host_ep__vc_tx_frame;
  wire [0:0] host_ep__vc_tx_v;
  wire [1:0] host_status__a_cause;
  wire [0:0] host_status__block_ready;
  wire [0:0] host_status__die_fault;
  wire [0:0] host_status__irq;
  wire [0:0] host_status__program_active;
  wire [0:0] host_status__program_fault;
  wire [511:0] lk_N0__rx;
  wire [1:0] lk_N0__st;
  wire [511:0] lk_N2__rx;
  wire [1:0] lk_N2__st;
  wire [511:0] lk_S0__rx;
  wire [1:0] lk_S0__st;
  wire [511:0] lk_S1__rx;
  wire [1:0] lk_S1__st;
  wire [511:0] lk_S3__rx;
  wire [1:0] lk_S3__st;
  wire [31:0] obs_C__r_d;
  wire [7:0] obs_C__r_idx;
  wire [0:0] obs_C__r_v;
  wire [31:0] obs_NE__r_d;
  wire [7:0] obs_NE__r_idx;
  wire [0:0] obs_NE__r_v;
  wire [31:0] obs_NW__r_d;
  wire [7:0] obs_NW__r_idx;
  wire [0:0] obs_NW__r_v;
  wire [2469:0] pgp_NE__command;
  wire [0:0] pgp_NE__done;
  wire [15:0] pgp_NE__edge_index;
  wire [0:0] pgp_NE__fault;
  wire [0:0] pgp_NE__valid;
  wire [0:0] pgp_NW__busy;
  wire [2469:0] pgp_NW__command;
  wire [0:0] pgp_NW__done;
  wire [15:0] pgp_NW__edge_index;
  wire [0:0] pgp_NW__fault;
  wire [0:0] pgp_NW__valid;
  wire [8191:0] phy_NW__dram_rdata;
  wire [31:0] phy_NW__dram_rvalid;
  wire [0:0] refcfg_NE__active;
  wire [0:0] refcfg_NE__fault;
  wire [0:0] refcfg_NE__pc_rst_n;
  wire [0:0] refcfg_NE__ready;
  wire [127:0] refcfg_NE__refresh_reload;
  wire [0:0] refcfg_NW__active;
  wire [0:0] refcfg_NW__fault;
  wire [0:0] refcfg_NW__pc_rst_n;
  wire [0:0] refcfg_NW__ready;
  wire [127:0] refcfg_NW__refresh_reload;
  wire [0:0] sfault_NE__fault;
  wire [6:0] sfault_NE__status;
  wire [0:0] sfault_NW__fault;
  wire [6:0] sfault_NW__status;
  wire [513:0] sfu_NE0__c_rr;
  wire [1:0] sfu_NE0__c_w_done;
  wire [513:0] sfu_NE0__far_rr;
  wire [1:0] sfu_NE0__far_w_done;
  wire [0:0] sfu_NE0__fault;
  wire [33:0] sfu_NE0__near_rq;
  wire [561:0] sfu_NE0__near_wq;
  wire [513:0] sfu_NE1__c_rr;
  wire [1:0] sfu_NE1__c_w_done;
  wire [513:0] sfu_NE1__far_rr;
  wire [1:0] sfu_NE1__far_w_done;
  wire [0:0] sfu_NE1__fault;
  wire [33:0] sfu_NE1__near_rq;
  wire [561:0] sfu_NE1__near_wq;
  wire [513:0] sfu_NE2__c_rr;
  wire [1:0] sfu_NE2__c_w_done;
  wire [513:0] sfu_NE2__far_rr;
  wire [1:0] sfu_NE2__far_w_done;
  wire [0:0] sfu_NE2__fault;
  wire [33:0] sfu_NE2__near_rq;
  wire [561:0] sfu_NE2__near_wq;
  wire [513:0] sfu_NE3__c_rr;
  wire [1:0] sfu_NE3__c_w_done;
  wire [513:0] sfu_NE3__far_rr;
  wire [1:0] sfu_NE3__far_w_done;
  wire [0:0] sfu_NE3__fault;
  wire [33:0] sfu_NE3__near_rq;
  wire [561:0] sfu_NE3__near_wq;
  wire [513:0] sfu_NW0__c_rr;
  wire [1:0] sfu_NW0__c_w_done;
  wire [513:0] sfu_NW0__far_rr;
  wire [1:0] sfu_NW0__far_w_done;
  wire [0:0] sfu_NW0__fault;
  wire [33:0] sfu_NW0__near_rq;
  wire [561:0] sfu_NW0__near_wq;
  wire [513:0] sfu_NW1__c_rr;
  wire [1:0] sfu_NW1__c_w_done;
  wire [513:0] sfu_NW1__far_rr;
  wire [1:0] sfu_NW1__far_w_done;
  wire [0:0] sfu_NW1__fault;
  wire [33:0] sfu_NW1__near_rq;
  wire [561:0] sfu_NW1__near_wq;
  wire [513:0] sfu_NW2__c_rr;
  wire [1:0] sfu_NW2__c_w_done;
  wire [513:0] sfu_NW2__far_rr;
  wire [1:0] sfu_NW2__far_w_done;
  wire [0:0] sfu_NW2__fault;
  wire [33:0] sfu_NW2__near_rq;
  wire [561:0] sfu_NW2__near_wq;
  wire [513:0] sfu_NW3__c_rr;
  wire [1:0] sfu_NW3__c_w_done;
  wire [513:0] sfu_NW3__far_rr;
  wire [1:0] sfu_NW3__far_w_done;
  wire [0:0] sfu_NW3__fault;
  wire [33:0] sfu_NW3__near_rq;
  wire [561:0] sfu_NW3__near_wq;
  wire [0:0] sfucore_NE__fault;
  wire [95:0] sfucore_NE__kv_waddr_e;
  wire [95:0] sfucore_NE__kv_waddr_n;
  wire [95:0] sfucore_NE__kv_waddr_s;
  wire [95:0] sfucore_NE__kv_waddr_w;
  wire [127:0] sfucore_NE__kv_wdata_e;
  wire [127:0] sfucore_NE__kv_wdata_n;
  wire [127:0] sfucore_NE__kv_wdata_s;
  wire [127:0] sfucore_NE__kv_wdata_w;
  wire [3:0] sfucore_NE__kv_we_e;
  wire [3:0] sfucore_NE__kv_we_n;
  wire [3:0] sfucore_NE__kv_we_s;
  wire [3:0] sfucore_NE__kv_we_w;
  wire [135:0] sfucore_NE__local_rq;
  wire [2247:0] sfucore_NE__local_wq;
  wire [3:0] sfucore_NE__ro_v_e;
  wire [3:0] sfucore_NE__ro_v_n;
  wire [3:0] sfucore_NE__ro_v_s;
  wire [3:0] sfucore_NE__ro_v_w;
  wire [127:0] sfucore_NE__ro_x_e;
  wire [127:0] sfucore_NE__ro_x_n;
  wire [127:0] sfucore_NE__ro_x_s;
  wire [127:0] sfucore_NE__ro_x_w;
  wire [95:0] sfucore_NE__vi_addr_e;
  wire [95:0] sfucore_NE__vi_addr_n;
  wire [95:0] sfucore_NE__vi_addr_s;
  wire [95:0] sfucore_NE__vi_addr_w;
  wire [3:0] sfucore_NE__vi_re_e;
  wire [3:0] sfucore_NE__vi_re_n;
  wire [3:0] sfucore_NE__vi_re_s;
  wire [3:0] sfucore_NE__vi_re_w;
  wire [0:0] sfucore_NW__fault;
  wire [95:0] sfucore_NW__kv_waddr_e;
  wire [95:0] sfucore_NW__kv_waddr_n;
  wire [95:0] sfucore_NW__kv_waddr_s;
  wire [95:0] sfucore_NW__kv_waddr_w;
  wire [127:0] sfucore_NW__kv_wdata_e;
  wire [127:0] sfucore_NW__kv_wdata_n;
  wire [127:0] sfucore_NW__kv_wdata_s;
  wire [127:0] sfucore_NW__kv_wdata_w;
  wire [3:0] sfucore_NW__kv_we_e;
  wire [3:0] sfucore_NW__kv_we_n;
  wire [3:0] sfucore_NW__kv_we_s;
  wire [3:0] sfucore_NW__kv_we_w;
  wire [135:0] sfucore_NW__local_rq;
  wire [2247:0] sfucore_NW__local_wq;
  wire [3:0] sfucore_NW__ro_v_e;
  wire [3:0] sfucore_NW__ro_v_n;
  wire [3:0] sfucore_NW__ro_v_s;
  wire [3:0] sfucore_NW__ro_v_w;
  wire [127:0] sfucore_NW__ro_x_e;
  wire [127:0] sfucore_NW__ro_x_n;
  wire [127:0] sfucore_NW__ro_x_s;
  wire [127:0] sfucore_NW__ro_x_w;
  wire [95:0] sfucore_NW__vi_addr_e;
  wire [95:0] sfucore_NW__vi_addr_n;
  wire [95:0] sfucore_NW__vi_addr_s;
  wire [95:0] sfucore_NW__vi_addr_w;
  wire [3:0] sfucore_NW__vi_re_e;
  wire [3:0] sfucore_NW__vi_re_n;
  wire [3:0] sfucore_NW__vi_re_s;
  wire [3:0] sfucore_NW__vi_re_w;
  wire [1741:0] sfup_NE__compiler_control;
  wire [0:0] sfup_NE__fault;
  wire [0:0] sfup_NE__io_active;
  wire [0:0] sfup_NE__io_done;
  wire [470:0] sfup_NE__io_word;
  wire [0:0] sfup_NE__programme_active;
  wire [0:0] sfup_NE__programme_done;
  wire [1741:0] sfup_NW__compiler_control;
  wire [0:0] sfup_NW__fault;
  wire [0:0] sfup_NW__io_active;
  wire [0:0] sfup_NW__io_done;
  wire [470:0] sfup_NW__io_word;
  wire [0:0] sfup_NW__programme_active;
  wire [0:0] sfup_NW__programme_done;
  wire [0:0] sfus_NE__fault;
  wire [31:0] sfus_NE__l00_vi_q;
  wire [31:0] sfus_NE__l01_vi_q;
  wire [31:0] sfus_NE__l02_vi_q;
  wire [31:0] sfus_NE__l03_vi_q;
  wire [31:0] sfus_NE__l04_vi_q;
  wire [31:0] sfus_NE__l05_vi_q;
  wire [31:0] sfus_NE__l06_vi_q;
  wire [31:0] sfus_NE__l07_vi_q;
  wire [31:0] sfus_NE__l08_vi_q;
  wire [31:0] sfus_NE__l09_vi_q;
  wire [31:0] sfus_NE__l10_vi_q;
  wire [31:0] sfus_NE__l11_vi_q;
  wire [31:0] sfus_NE__l12_vi_q;
  wire [31:0] sfus_NE__l13_vi_q;
  wire [31:0] sfus_NE__l14_vi_q;
  wire [31:0] sfus_NE__l15_vi_q;
  wire [0:0] sfus_NW__fault;
  wire [31:0] sfus_NW__l00_vi_q;
  wire [31:0] sfus_NW__l01_vi_q;
  wire [31:0] sfus_NW__l02_vi_q;
  wire [31:0] sfus_NW__l03_vi_q;
  wire [31:0] sfus_NW__l04_vi_q;
  wire [31:0] sfus_NW__l05_vi_q;
  wire [31:0] sfus_NW__l06_vi_q;
  wire [31:0] sfus_NW__l07_vi_q;
  wire [31:0] sfus_NW__l08_vi_q;
  wire [31:0] sfus_NW__l09_vi_q;
  wire [31:0] sfus_NW__l10_vi_q;
  wire [31:0] sfus_NW__l11_vi_q;
  wire [31:0] sfus_NW__l12_vi_q;
  wire [31:0] sfus_NW__l13_vi_q;
  wire [31:0] sfus_NW__l14_vi_q;
  wire [31:0] sfus_NW__l15_vi_q;
  wire [0:0] sm_NW0__fault;
  wire [255:0] sm_NW0__rdata;
  wire [42:0] sm_NW0__request;
  wire [11:0] sm_NW0__rrow;
  wire [0:0] sm_NW0__rv;
  wire [0:0] sm_NW0__schedule_fault;
  wire [0:0] sm_NW1__fault;
  wire [255:0] sm_NW1__rdata;
  wire [42:0] sm_NW1__request;
  wire [11:0] sm_NW1__rrow;
  wire [0:0] sm_NW1__rv;
  wire [0:0] sm_NW1__schedule_fault;
  wire [0:0] sm_NW2__fault;
  wire [255:0] sm_NW2__rdata;
  wire [42:0] sm_NW2__request;
  wire [11:0] sm_NW2__rrow;
  wire [0:0] sm_NW2__rv;
  wire [0:0] sm_NW2__schedule_fault;
  wire [0:0] sm_NW3__fault;
  wire [255:0] sm_NW3__rdata;
  wire [42:0] sm_NW3__request;
  wire [11:0] sm_NW3__rrow;
  wire [0:0] sm_NW3__rv;
  wire [0:0] sm_NW3__schedule_fault;
  wire [0:0] sm_NW4__fault;
  wire [255:0] sm_NW4__rdata;
  wire [42:0] sm_NW4__request;
  wire [11:0] sm_NW4__rrow;
  wire [0:0] sm_NW4__rv;
  wire [0:0] sm_NW4__schedule_fault;
  wire [0:0] sm_NW5__fault;
  wire [255:0] sm_NW5__rdata;
  wire [42:0] sm_NW5__request;
  wire [11:0] sm_NW5__rrow;
  wire [0:0] sm_NW5__rv;
  wire [0:0] sm_NW5__schedule_fault;
  wire [0:0] sm_NW6__fault;
  wire [255:0] sm_NW6__rdata;
  wire [42:0] sm_NW6__request;
  wire [11:0] sm_NW6__rrow;
  wire [0:0] sm_NW6__rv;
  wire [0:0] sm_NW6__schedule_fault;
  wire [0:0] sm_NW7__fault;
  wire [255:0] sm_NW7__rdata;
  wire [42:0] sm_NW7__request;
  wire [11:0] sm_NW7__rrow;
  wire [0:0] sm_NW7__rv;
  wire [0:0] sm_NW7__schedule_fault;
  wire [0:0] smw_NE__active;
  wire [0:0] smw_NE__configured;
  wire [0:0] smw_NE__fault;
  wire [280:0] smw_NE__wq_s0;
  wire [280:0] smw_NE__wq_s1;
  wire [280:0] smw_NE__wq_s2;
  wire [280:0] smw_NE__wq_s3;
  wire [280:0] smw_NE__wq_t0;
  wire [280:0] smw_NE__wq_t1;
  wire [280:0] smw_NE__wq_t2;
  wire [280:0] smw_NE__wq_t3;
  wire [0:0] smw_NW__active;
  wire [0:0] smw_NW__configured;
  wire [0:0] smw_NW__fault;
  wire [280:0] smw_NW__wq_s0;
  wire [280:0] smw_NW__wq_s1;
  wire [280:0] smw_NW__wq_s2;
  wire [280:0] smw_NW__wq_s3;
  wire [280:0] smw_NW__wq_t0;
  wire [280:0] smw_NW__wq_t1;
  wire [280:0] smw_NW__wq_t2;
  wire [280:0] smw_NW__wq_t3;
  wire [15:0] stl_NE__rf_wa;
  wire [63:0] stl_NE__rf_wd;
  wire [1:0] stl_NE__rf_wv;
  wire [40:0] stl_NE__up_o;
  wire [15:0] stl_NW__rf_wa;
  wire [63:0] stl_NW__rf_wd;
  wire [1:0] stl_NW__rf_wv;
  wire [40:0] stl_NW__up_o;
  wire [81:0] str_C__dn0_o;
  wire [81:0] str_C__dn1_o;
  wire [513:0] su_NE0__far_rr;
  wire [1:0] su_NE0__far_w_done;
  wire [0:0] su_NE0__fault;
  wire [1023:0] su_NE0__inj_q;
  wire [0:0] su_NE0__lg_fault;
  wire [33:0] su_NE0__lg_rq;
  wire [561:0] su_NE0__lg_wq;
  wire [31:0] su_NE0__slice_x;
  wire [66:0] su_NE0__tree_o;
  wire [513:0] su_NE1__far_rr;
  wire [1:0] su_NE1__far_w_done;
  wire [0:0] su_NE1__fault;
  wire [1023:0] su_NE1__inj_q;
  wire [0:0] su_NE1__lg_fault;
  wire [33:0] su_NE1__lg_rq;
  wire [561:0] su_NE1__lg_wq;
  wire [31:0] su_NE1__slice_x;
  wire [66:0] su_NE1__tree_o;
  wire [513:0] su_NE2__far_rr;
  wire [1:0] su_NE2__far_w_done;
  wire [0:0] su_NE2__fault;
  wire [1023:0] su_NE2__inj_q;
  wire [0:0] su_NE2__lg_fault;
  wire [33:0] su_NE2__lg_rq;
  wire [561:0] su_NE2__lg_wq;
  wire [31:0] su_NE2__slice_x;
  wire [66:0] su_NE2__tree_o;
  wire [513:0] su_NE3__far_rr;
  wire [1:0] su_NE3__far_w_done;
  wire [0:0] su_NE3__fault;
  wire [1023:0] su_NE3__inj_q;
  wire [0:0] su_NE3__lg_fault;
  wire [33:0] su_NE3__lg_rq;
  wire [561:0] su_NE3__lg_wq;
  wire [31:0] su_NE3__slice_x;
  wire [66:0] su_NE3__tree_o;
  wire [513:0] su_NW0__far_rr;
  wire [1:0] su_NW0__far_w_done;
  wire [0:0] su_NW0__fault;
  wire [1023:0] su_NW0__inj_q;
  wire [0:0] su_NW0__lg_fault;
  wire [33:0] su_NW0__lg_rq;
  wire [561:0] su_NW0__lg_wq;
  wire [31:0] su_NW0__slice_x;
  wire [66:0] su_NW0__tree_o;
  wire [513:0] su_NW1__far_rr;
  wire [1:0] su_NW1__far_w_done;
  wire [0:0] su_NW1__fault;
  wire [1023:0] su_NW1__inj_q;
  wire [0:0] su_NW1__lg_fault;
  wire [33:0] su_NW1__lg_rq;
  wire [561:0] su_NW1__lg_wq;
  wire [31:0] su_NW1__slice_x;
  wire [66:0] su_NW1__tree_o;
  wire [513:0] su_NW2__far_rr;
  wire [1:0] su_NW2__far_w_done;
  wire [0:0] su_NW2__fault;
  wire [1023:0] su_NW2__inj_q;
  wire [0:0] su_NW2__lg_fault;
  wire [33:0] su_NW2__lg_rq;
  wire [561:0] su_NW2__lg_wq;
  wire [31:0] su_NW2__slice_x;
  wire [66:0] su_NW2__tree_o;
  wire [513:0] su_NW3__far_rr;
  wire [1:0] su_NW3__far_w_done;
  wire [0:0] su_NW3__fault;
  wire [1023:0] su_NW3__inj_q;
  wire [0:0] su_NW3__lg_fault;
  wire [33:0] su_NW3__lg_rq;
  wire [561:0] su_NW3__lg_wq;
  wire [31:0] su_NW3__slice_x;
  wire [66:0] su_NW3__tree_o;
  wire [0:0] su_prog__fault;
  wire [31:0] su_prog__r_bank;
  wire [255:0] su_prog__r_data;
  wire [15:0] su_prog__r_len;
  wire [6:0] su_prog__r_row;
  wire [0:0] su_prog__r_start;
  wire [1:0] su_prog__r_we;
  wire [0:0] sucore_NE__fault;
  wire [0:0] sucore_NE__red_rf_v;
  wire [0:0] sucore_NE__red_sv;
  wire [31:0] sucore_NE__red_tag;
  wire [31:0] sucore_NE__red_x;
  wire [35:0] sucore_NE__rf_bcmd;
  wire [127:0] sucore_NE__rf_bword;
  wire [255:0] sucore_NE__rf_dsec;
  wire [0:0] sucore_NW__fault;
  wire [0:0] sucore_NW__red_rf_v;
  wire [0:0] sucore_NW__red_sv;
  wire [31:0] sucore_NW__red_tag;
  wire [31:0] sucore_NW__red_x;
  wire [35:0] sucore_NW__rf_bcmd;
  wire [127:0] sucore_NW__rf_bword;
  wire [255:0] sucore_NW__rf_dsec;
  wire [0:0] svg_NW0__fault;
  wire [119:0] svg_NW0__k_addr;
  wire [15:0] svg_NW0__k_len;
  wire [67:0] svg_NW0__k_tag;
  wire [3:0] svg_NW0__k_v;
  wire [1023:0] svg_NW0__k_wdata;
  wire [3:0] svg_NW0__k_we;
  wire [127:0] svg_NW0__k_wstrb;
  wire [3:0] svg_NW0__kr_rdy;
  wire [0:0] svg_NW0__program_active;
  wire [0:0] svg_NW0__run_done;
  wire [0:0] svg_NW0__running;
  wire [82:0] svg_NW0__sm_command;
  wire [1098:0] svg_NW0__sm_packet;
  wire [0:0] svg_NW1__fault;
  wire [119:0] svg_NW1__k_addr;
  wire [15:0] svg_NW1__k_len;
  wire [67:0] svg_NW1__k_tag;
  wire [3:0] svg_NW1__k_v;
  wire [1023:0] svg_NW1__k_wdata;
  wire [3:0] svg_NW1__k_we;
  wire [127:0] svg_NW1__k_wstrb;
  wire [3:0] svg_NW1__kr_rdy;
  wire [0:0] svg_NW1__program_active;
  wire [0:0] svg_NW1__run_done;
  wire [0:0] svg_NW1__running;
  wire [82:0] svg_NW1__sm_command;
  wire [1098:0] svg_NW1__sm_packet;
  wire [0:0] svg_NW2__fault;
  wire [119:0] svg_NW2__k_addr;
  wire [15:0] svg_NW2__k_len;
  wire [67:0] svg_NW2__k_tag;
  wire [3:0] svg_NW2__k_v;
  wire [1023:0] svg_NW2__k_wdata;
  wire [3:0] svg_NW2__k_we;
  wire [127:0] svg_NW2__k_wstrb;
  wire [3:0] svg_NW2__kr_rdy;
  wire [0:0] svg_NW2__program_active;
  wire [0:0] svg_NW2__run_done;
  wire [0:0] svg_NW2__running;
  wire [82:0] svg_NW2__sm_command;
  wire [1098:0] svg_NW2__sm_packet;
  wire [0:0] svg_NW3__fault;
  wire [119:0] svg_NW3__k_addr;
  wire [15:0] svg_NW3__k_len;
  wire [67:0] svg_NW3__k_tag;
  wire [3:0] svg_NW3__k_v;
  wire [1023:0] svg_NW3__k_wdata;
  wire [3:0] svg_NW3__k_we;
  wire [127:0] svg_NW3__k_wstrb;
  wire [3:0] svg_NW3__kr_rdy;
  wire [0:0] svg_NW3__program_active;
  wire [0:0] svg_NW3__run_done;
  wire [0:0] svg_NW3__running;
  wire [82:0] svg_NW3__sm_command;
  wire [1098:0] svg_NW3__sm_packet;
  wire [0:0] svg_NW4__fault;
  wire [119:0] svg_NW4__k_addr;
  wire [15:0] svg_NW4__k_len;
  wire [67:0] svg_NW4__k_tag;
  wire [3:0] svg_NW4__k_v;
  wire [1023:0] svg_NW4__k_wdata;
  wire [3:0] svg_NW4__k_we;
  wire [127:0] svg_NW4__k_wstrb;
  wire [3:0] svg_NW4__kr_rdy;
  wire [0:0] svg_NW4__program_active;
  wire [0:0] svg_NW4__run_done;
  wire [0:0] svg_NW4__running;
  wire [82:0] svg_NW4__sm_command;
  wire [1098:0] svg_NW4__sm_packet;
  wire [0:0] svg_NW5__fault;
  wire [119:0] svg_NW5__k_addr;
  wire [15:0] svg_NW5__k_len;
  wire [67:0] svg_NW5__k_tag;
  wire [3:0] svg_NW5__k_v;
  wire [1023:0] svg_NW5__k_wdata;
  wire [3:0] svg_NW5__k_we;
  wire [127:0] svg_NW5__k_wstrb;
  wire [3:0] svg_NW5__kr_rdy;
  wire [0:0] svg_NW5__program_active;
  wire [0:0] svg_NW5__run_done;
  wire [0:0] svg_NW5__running;
  wire [82:0] svg_NW5__sm_command;
  wire [1098:0] svg_NW5__sm_packet;
  wire [0:0] svg_NW6__fault;
  wire [119:0] svg_NW6__k_addr;
  wire [15:0] svg_NW6__k_len;
  wire [67:0] svg_NW6__k_tag;
  wire [3:0] svg_NW6__k_v;
  wire [1023:0] svg_NW6__k_wdata;
  wire [3:0] svg_NW6__k_we;
  wire [127:0] svg_NW6__k_wstrb;
  wire [3:0] svg_NW6__kr_rdy;
  wire [0:0] svg_NW6__program_active;
  wire [0:0] svg_NW6__run_done;
  wire [0:0] svg_NW6__running;
  wire [82:0] svg_NW6__sm_command;
  wire [1098:0] svg_NW6__sm_packet;
  wire [0:0] svg_NW7__fault;
  wire [119:0] svg_NW7__k_addr;
  wire [15:0] svg_NW7__k_len;
  wire [67:0] svg_NW7__k_tag;
  wire [3:0] svg_NW7__k_v;
  wire [1023:0] svg_NW7__k_wdata;
  wire [3:0] svg_NW7__k_we;
  wire [127:0] svg_NW7__k_wstrb;
  wire [3:0] svg_NW7__kr_rdy;
  wire [0:0] svg_NW7__program_active;
  wire [0:0] svg_NW7__run_done;
  wire [0:0] svg_NW7__running;
  wire [82:0] svg_NW7__sm_command;
  wire [1098:0] svg_NW7__sm_packet;
  wire [0:0] tkm_SW__busy;
  wire [0:0] tkm_SW__done;
  wire [0:0] tkm_SW__fault;
  wire [31:0] tkm_SW__stat_cycles;
  wire [39:0] tkm_SW__w_addr;
  wire [511:0] tkm_SW__w_data;
  wire [15:0] tkm_SW__w_mask;
  wire [0:0] tkm_SW__w_v;
  wire [270:0] u_mu_fused_n4_ne__uo;
  wire [270:0] u_mu_fused_n4_nw__uo;
  wire [0:0] u_mu_fused_programme__active;
  wire [0:0] u_mu_fused_programme__fault;
  wire [216:0] u_mu_fused_programme__job;
  wire [0:0] u_mu_fused_programme__job_v;
  wire [0:0] u_mu_fused_programme__pb5;
  wire [5:0] u_mu_fused_programme__pk5;
  wire [0:0] u_mu_fused_programme__ready;
  wire [7:0] u_mu_fused_programme__wsc;
  wire [0:0] u_mu_fused_root__busy;
  wire [0:0] u_mu_fused_root__done;
  wire [172:0] u_mu_fused_root__down_ne;
  wire [172:0] u_mu_fused_root__down_nw;
  wire [0:0] u_mu_fused_root__fault;
  wire [18:0] vm_status4__vmstat;
  wire [0:0] vmb_NE0__dq_done;
  wire [275:0] vmb_NE0__eg;
  wire [0:0] vmb_NE0__kq_done;
  wire [265:0] vmb_NE0__pr;
  wire [256:0] vmb_NE0__rr0;
  wire [256:0] vmb_NE0__rr1;
  wire [256:0] vmb_NE0__rr2;
  wire [256:0] vmb_NE0__rr3;
  wire [256:0] vmb_NE0__rr4;
  wire [17:0] vmb_NE0__status;
  wire [0:0] vmb_NE0__wq_done0;
  wire [0:0] vmb_NE0__wq_done1;
  wire [0:0] vmb_NE0__xq2_done;
  wire [0:0] vmb_NE0__xq_done;
  wire [0:0] vmb_NE1__dq_done;
  wire [275:0] vmb_NE1__eg;
  wire [0:0] vmb_NE1__kq_done;
  wire [265:0] vmb_NE1__pr;
  wire [256:0] vmb_NE1__rr0;
  wire [256:0] vmb_NE1__rr1;
  wire [256:0] vmb_NE1__rr2;
  wire [256:0] vmb_NE1__rr3;
  wire [256:0] vmb_NE1__rr4;
  wire [17:0] vmb_NE1__status;
  wire [0:0] vmb_NE1__wq_done0;
  wire [0:0] vmb_NE1__wq_done1;
  wire [0:0] vmb_NE1__xq2_done;
  wire [0:0] vmb_NE1__xq_done;
  wire [0:0] vmb_NE2__dq_done;
  wire [275:0] vmb_NE2__eg;
  wire [0:0] vmb_NE2__kq_done;
  wire [265:0] vmb_NE2__pr;
  wire [256:0] vmb_NE2__rr0;
  wire [256:0] vmb_NE2__rr1;
  wire [256:0] vmb_NE2__rr2;
  wire [256:0] vmb_NE2__rr3;
  wire [256:0] vmb_NE2__rr4;
  wire [17:0] vmb_NE2__status;
  wire [0:0] vmb_NE2__wq_done0;
  wire [0:0] vmb_NE2__wq_done1;
  wire [0:0] vmb_NE2__xq2_done;
  wire [0:0] vmb_NE2__xq_done;
  wire [0:0] vmb_NE3__dq_done;
  wire [275:0] vmb_NE3__eg;
  wire [0:0] vmb_NE3__kq_done;
  wire [265:0] vmb_NE3__pr;
  wire [256:0] vmb_NE3__rr0;
  wire [256:0] vmb_NE3__rr1;
  wire [256:0] vmb_NE3__rr2;
  wire [256:0] vmb_NE3__rr3;
  wire [256:0] vmb_NE3__rr4;
  wire [17:0] vmb_NE3__status;
  wire [0:0] vmb_NE3__wq_done0;
  wire [0:0] vmb_NE3__wq_done1;
  wire [0:0] vmb_NE3__xq2_done;
  wire [0:0] vmb_NE3__xq_done;
  wire [0:0] vmb_NE4__dq_done;
  wire [275:0] vmb_NE4__eg;
  wire [0:0] vmb_NE4__kq_done;
  wire [265:0] vmb_NE4__pr;
  wire [256:0] vmb_NE4__rr0;
  wire [256:0] vmb_NE4__rr1;
  wire [256:0] vmb_NE4__rr2;
  wire [256:0] vmb_NE4__rr3;
  wire [256:0] vmb_NE4__rr4;
  wire [17:0] vmb_NE4__status;
  wire [0:0] vmb_NE4__wq_done0;
  wire [0:0] vmb_NE4__wq_done1;
  wire [0:0] vmb_NE4__xq2_done;
  wire [0:0] vmb_NE4__xq_done;
  wire [0:0] vmb_NE5__dq_done;
  wire [275:0] vmb_NE5__eg;
  wire [0:0] vmb_NE5__kq_done;
  wire [265:0] vmb_NE5__pr;
  wire [256:0] vmb_NE5__rr0;
  wire [256:0] vmb_NE5__rr1;
  wire [256:0] vmb_NE5__rr2;
  wire [256:0] vmb_NE5__rr3;
  wire [256:0] vmb_NE5__rr4;
  wire [17:0] vmb_NE5__status;
  wire [0:0] vmb_NE5__wq_done0;
  wire [0:0] vmb_NE5__wq_done1;
  wire [0:0] vmb_NE5__xq2_done;
  wire [0:0] vmb_NE5__xq_done;
  wire [0:0] vmb_NE6__dq_done;
  wire [275:0] vmb_NE6__eg;
  wire [0:0] vmb_NE6__kq_done;
  wire [265:0] vmb_NE6__pr;
  wire [256:0] vmb_NE6__rr0;
  wire [256:0] vmb_NE6__rr1;
  wire [256:0] vmb_NE6__rr2;
  wire [256:0] vmb_NE6__rr3;
  wire [256:0] vmb_NE6__rr4;
  wire [17:0] vmb_NE6__status;
  wire [0:0] vmb_NE6__wq_done0;
  wire [0:0] vmb_NE6__wq_done1;
  wire [0:0] vmb_NE6__xq2_done;
  wire [0:0] vmb_NE6__xq_done;
  wire [0:0] vmb_NE7__dq_done;
  wire [275:0] vmb_NE7__eg;
  wire [0:0] vmb_NE7__kq_done;
  wire [265:0] vmb_NE7__pr;
  wire [256:0] vmb_NE7__rr0;
  wire [256:0] vmb_NE7__rr1;
  wire [256:0] vmb_NE7__rr2;
  wire [256:0] vmb_NE7__rr3;
  wire [256:0] vmb_NE7__rr4;
  wire [17:0] vmb_NE7__status;
  wire [0:0] vmb_NE7__wq_done0;
  wire [0:0] vmb_NE7__wq_done1;
  wire [0:0] vmb_NE7__xq2_done;
  wire [0:0] vmb_NE7__xq_done;
  wire [0:0] vmb_NW0__dq_done;
  wire [275:0] vmb_NW0__eg;
  wire [0:0] vmb_NW0__kq_done;
  wire [265:0] vmb_NW0__pr;
  wire [256:0] vmb_NW0__rr0;
  wire [256:0] vmb_NW0__rr1;
  wire [256:0] vmb_NW0__rr2;
  wire [256:0] vmb_NW0__rr3;
  wire [256:0] vmb_NW0__rr4;
  wire [17:0] vmb_NW0__status;
  wire [0:0] vmb_NW0__wq_done0;
  wire [0:0] vmb_NW0__wq_done1;
  wire [0:0] vmb_NW0__xq2_done;
  wire [0:0] vmb_NW0__xq_done;
  wire [0:0] vmb_NW1__dq_done;
  wire [275:0] vmb_NW1__eg;
  wire [0:0] vmb_NW1__kq_done;
  wire [265:0] vmb_NW1__pr;
  wire [256:0] vmb_NW1__rr0;
  wire [256:0] vmb_NW1__rr1;
  wire [256:0] vmb_NW1__rr2;
  wire [256:0] vmb_NW1__rr3;
  wire [256:0] vmb_NW1__rr4;
  wire [17:0] vmb_NW1__status;
  wire [0:0] vmb_NW1__wq_done0;
  wire [0:0] vmb_NW1__wq_done1;
  wire [0:0] vmb_NW1__xq2_done;
  wire [0:0] vmb_NW1__xq_done;
  wire [0:0] vmb_NW2__dq_done;
  wire [275:0] vmb_NW2__eg;
  wire [0:0] vmb_NW2__kq_done;
  wire [265:0] vmb_NW2__pr;
  wire [256:0] vmb_NW2__rr0;
  wire [256:0] vmb_NW2__rr1;
  wire [256:0] vmb_NW2__rr2;
  wire [256:0] vmb_NW2__rr3;
  wire [256:0] vmb_NW2__rr4;
  wire [17:0] vmb_NW2__status;
  wire [0:0] vmb_NW2__wq_done0;
  wire [0:0] vmb_NW2__wq_done1;
  wire [0:0] vmb_NW2__xq2_done;
  wire [0:0] vmb_NW2__xq_done;
  wire [0:0] vmb_NW3__dq_done;
  wire [275:0] vmb_NW3__eg;
  wire [0:0] vmb_NW3__kq_done;
  wire [265:0] vmb_NW3__pr;
  wire [256:0] vmb_NW3__rr0;
  wire [256:0] vmb_NW3__rr1;
  wire [256:0] vmb_NW3__rr2;
  wire [256:0] vmb_NW3__rr3;
  wire [256:0] vmb_NW3__rr4;
  wire [17:0] vmb_NW3__status;
  wire [0:0] vmb_NW3__wq_done0;
  wire [0:0] vmb_NW3__wq_done1;
  wire [0:0] vmb_NW3__xq2_done;
  wire [0:0] vmb_NW3__xq_done;
  wire [0:0] vmb_NW4__dq_done;
  wire [275:0] vmb_NW4__eg;
  wire [0:0] vmb_NW4__kq_done;
  wire [265:0] vmb_NW4__pr;
  wire [256:0] vmb_NW4__rr0;
  wire [256:0] vmb_NW4__rr1;
  wire [256:0] vmb_NW4__rr2;
  wire [256:0] vmb_NW4__rr3;
  wire [256:0] vmb_NW4__rr4;
  wire [17:0] vmb_NW4__status;
  wire [0:0] vmb_NW4__wq_done0;
  wire [0:0] vmb_NW4__wq_done1;
  wire [0:0] vmb_NW4__xq2_done;
  wire [0:0] vmb_NW4__xq_done;
  wire [0:0] vmb_NW5__dq_done;
  wire [275:0] vmb_NW5__eg;
  wire [0:0] vmb_NW5__kq_done;
  wire [265:0] vmb_NW5__pr;
  wire [256:0] vmb_NW5__rr0;
  wire [256:0] vmb_NW5__rr1;
  wire [256:0] vmb_NW5__rr2;
  wire [256:0] vmb_NW5__rr3;
  wire [256:0] vmb_NW5__rr4;
  wire [17:0] vmb_NW5__status;
  wire [0:0] vmb_NW5__wq_done0;
  wire [0:0] vmb_NW5__wq_done1;
  wire [0:0] vmb_NW5__xq2_done;
  wire [0:0] vmb_NW5__xq_done;
  wire [0:0] vmb_NW6__dq_done;
  wire [275:0] vmb_NW6__eg;
  wire [0:0] vmb_NW6__kq_done;
  wire [265:0] vmb_NW6__pr;
  wire [256:0] vmb_NW6__rr0;
  wire [256:0] vmb_NW6__rr1;
  wire [256:0] vmb_NW6__rr2;
  wire [256:0] vmb_NW6__rr3;
  wire [256:0] vmb_NW6__rr4;
  wire [17:0] vmb_NW6__status;
  wire [0:0] vmb_NW6__wq_done0;
  wire [0:0] vmb_NW6__wq_done1;
  wire [0:0] vmb_NW6__xq2_done;
  wire [0:0] vmb_NW6__xq_done;
  wire [0:0] vmb_NW7__dq_done;
  wire [275:0] vmb_NW7__eg;
  wire [0:0] vmb_NW7__kq_done;
  wire [265:0] vmb_NW7__pr;
  wire [256:0] vmb_NW7__rr0;
  wire [256:0] vmb_NW7__rr1;
  wire [256:0] vmb_NW7__rr2;
  wire [256:0] vmb_NW7__rr3;
  wire [256:0] vmb_NW7__rr4;
  wire [17:0] vmb_NW7__status;
  wire [0:0] vmb_NW7__wq_done0;
  wire [0:0] vmb_NW7__wq_done1;
  wire [0:0] vmb_NW7__xq2_done;
  wire [0:0] vmb_NW7__xq_done;
  wire [275:0] vmb_SE0__eg;
  wire [265:0] vmb_SE0__pr;
  wire [256:0] vmb_SE0__rr4;
  wire [17:0] vmb_SE0__status;
  wire [0:0] vmb_SE0__xq2_done;
  wire [0:0] vmb_SE0__xq_done;
  wire [275:0] vmb_SE1__eg;
  wire [265:0] vmb_SE1__pr;
  wire [256:0] vmb_SE1__rr4;
  wire [17:0] vmb_SE1__status;
  wire [0:0] vmb_SE1__xq2_done;
  wire [0:0] vmb_SE1__xq_done;
  wire [275:0] vmb_SE2__eg;
  wire [265:0] vmb_SE2__pr;
  wire [256:0] vmb_SE2__rr4;
  wire [17:0] vmb_SE2__status;
  wire [0:0] vmb_SE2__xq2_done;
  wire [0:0] vmb_SE2__xq_done;
  wire [275:0] vmb_SE3__eg;
  wire [265:0] vmb_SE3__pr;
  wire [256:0] vmb_SE3__rr4;
  wire [17:0] vmb_SE3__status;
  wire [0:0] vmb_SE3__xq2_done;
  wire [0:0] vmb_SE3__xq_done;
  wire [275:0] vmb_SE4__eg;
  wire [265:0] vmb_SE4__pr;
  wire [256:0] vmb_SE4__rr4;
  wire [17:0] vmb_SE4__status;
  wire [0:0] vmb_SE4__xq2_done;
  wire [0:0] vmb_SE4__xq_done;
  wire [275:0] vmb_SE5__eg;
  wire [265:0] vmb_SE5__pr;
  wire [256:0] vmb_SE5__rr4;
  wire [17:0] vmb_SE5__status;
  wire [0:0] vmb_SE5__xq2_done;
  wire [0:0] vmb_SE5__xq_done;
  wire [275:0] vmb_SE6__eg;
  wire [265:0] vmb_SE6__pr;
  wire [256:0] vmb_SE6__rr4;
  wire [17:0] vmb_SE6__status;
  wire [0:0] vmb_SE6__xq2_done;
  wire [0:0] vmb_SE6__xq_done;
  wire [275:0] vmb_SE7__eg;
  wire [265:0] vmb_SE7__pr;
  wire [256:0] vmb_SE7__rr4;
  wire [17:0] vmb_SE7__status;
  wire [0:0] vmb_SE7__xq2_done;
  wire [0:0] vmb_SE7__xq_done;
  wire [275:0] vmb_SW0__eg;
  wire [265:0] vmb_SW0__pr;
  wire [256:0] vmb_SW0__rr4;
  wire [17:0] vmb_SW0__status;
  wire [0:0] vmb_SW0__xq2_done;
  wire [0:0] vmb_SW0__xq_done;
  wire [275:0] vmb_SW1__eg;
  wire [265:0] vmb_SW1__pr;
  wire [256:0] vmb_SW1__rr4;
  wire [17:0] vmb_SW1__status;
  wire [0:0] vmb_SW1__xq2_done;
  wire [0:0] vmb_SW1__xq_done;
  wire [275:0] vmb_SW2__eg;
  wire [265:0] vmb_SW2__pr;
  wire [256:0] vmb_SW2__rr4;
  wire [17:0] vmb_SW2__status;
  wire [0:0] vmb_SW2__xq2_done;
  wire [0:0] vmb_SW2__xq_done;
  wire [275:0] vmb_SW3__eg;
  wire [265:0] vmb_SW3__pr;
  wire [256:0] vmb_SW3__rr4;
  wire [17:0] vmb_SW3__status;
  wire [0:0] vmb_SW3__xq2_done;
  wire [0:0] vmb_SW3__xq_done;
  wire [275:0] vmb_SW4__eg;
  wire [265:0] vmb_SW4__pr;
  wire [256:0] vmb_SW4__rr4;
  wire [17:0] vmb_SW4__status;
  wire [0:0] vmb_SW4__xq2_done;
  wire [0:0] vmb_SW4__xq_done;
  wire [275:0] vmb_SW5__eg;
  wire [265:0] vmb_SW5__pr;
  wire [256:0] vmb_SW5__rr4;
  wire [17:0] vmb_SW5__status;
  wire [0:0] vmb_SW5__xq2_done;
  wire [0:0] vmb_SW5__xq_done;
  wire [275:0] vmb_SW6__eg;
  wire [265:0] vmb_SW6__pr;
  wire [256:0] vmb_SW6__rr4;
  wire [17:0] vmb_SW6__status;
  wire [0:0] vmb_SW6__xq2_done;
  wire [0:0] vmb_SW6__xq_done;
  wire [275:0] vmb_SW7__eg;
  wire [265:0] vmb_SW7__pr;
  wire [256:0] vmb_SW7__rr4;
  wire [17:0] vmb_SW7__status;
  wire [0:0] vmb_SW7__xq2_done;
  wire [0:0] vmb_SW7__xq_done;
  wire [1:0] vmdel_NE0__block_ready;
  wire [0:0] vmdel_NE0__busy;
  wire [280:0] vmdel_NE0__dq;
  wire [0:0] vmdel_NE0__fault;
  wire [0:0] vmdel_NE0__full0;
  wire [0:0] vmdel_NE0__full1;
  wire [0:0] vmdel_NE0__pcbad;
  wire [1:0] vmdel_NE1__block_ready;
  wire [0:0] vmdel_NE1__busy;
  wire [280:0] vmdel_NE1__dq;
  wire [0:0] vmdel_NE1__fault;
  wire [0:0] vmdel_NE1__full0;
  wire [0:0] vmdel_NE1__full1;
  wire [0:0] vmdel_NE1__pcbad;
  wire [1:0] vmdel_NE2__block_ready;
  wire [0:0] vmdel_NE2__busy;
  wire [280:0] vmdel_NE2__dq;
  wire [0:0] vmdel_NE2__fault;
  wire [0:0] vmdel_NE2__full0;
  wire [0:0] vmdel_NE2__full1;
  wire [0:0] vmdel_NE2__pcbad;
  wire [1:0] vmdel_NE3__block_ready;
  wire [0:0] vmdel_NE3__busy;
  wire [280:0] vmdel_NE3__dq;
  wire [0:0] vmdel_NE3__fault;
  wire [0:0] vmdel_NE3__full0;
  wire [0:0] vmdel_NE3__full1;
  wire [0:0] vmdel_NE3__pcbad;
  wire [1:0] vmdel_NE4__block_ready;
  wire [0:0] vmdel_NE4__busy;
  wire [280:0] vmdel_NE4__dq;
  wire [0:0] vmdel_NE4__fault;
  wire [0:0] vmdel_NE4__full0;
  wire [0:0] vmdel_NE4__full1;
  wire [0:0] vmdel_NE4__pcbad;
  wire [1:0] vmdel_NE5__block_ready;
  wire [0:0] vmdel_NE5__busy;
  wire [280:0] vmdel_NE5__dq;
  wire [0:0] vmdel_NE5__fault;
  wire [0:0] vmdel_NE5__full0;
  wire [0:0] vmdel_NE5__full1;
  wire [0:0] vmdel_NE5__pcbad;
  wire [1:0] vmdel_NE6__block_ready;
  wire [0:0] vmdel_NE6__busy;
  wire [280:0] vmdel_NE6__dq;
  wire [0:0] vmdel_NE6__fault;
  wire [0:0] vmdel_NE6__full0;
  wire [0:0] vmdel_NE6__full1;
  wire [0:0] vmdel_NE6__pcbad;
  wire [1:0] vmdel_NE7__block_ready;
  wire [0:0] vmdel_NE7__busy;
  wire [280:0] vmdel_NE7__dq;
  wire [0:0] vmdel_NE7__fault;
  wire [0:0] vmdel_NE7__full0;
  wire [0:0] vmdel_NE7__full1;
  wire [0:0] vmdel_NE7__pcbad;
  wire [1:0] vmdel_NW0__block_ready;
  wire [0:0] vmdel_NW0__busy;
  wire [280:0] vmdel_NW0__dq;
  wire [0:0] vmdel_NW0__fault;
  wire [0:0] vmdel_NW0__full0;
  wire [0:0] vmdel_NW0__full1;
  wire [0:0] vmdel_NW0__pcbad;
  wire [1:0] vmdel_NW1__block_ready;
  wire [0:0] vmdel_NW1__busy;
  wire [280:0] vmdel_NW1__dq;
  wire [0:0] vmdel_NW1__fault;
  wire [0:0] vmdel_NW1__full0;
  wire [0:0] vmdel_NW1__full1;
  wire [0:0] vmdel_NW1__pcbad;
  wire [1:0] vmdel_NW2__block_ready;
  wire [0:0] vmdel_NW2__busy;
  wire [280:0] vmdel_NW2__dq;
  wire [0:0] vmdel_NW2__fault;
  wire [0:0] vmdel_NW2__full0;
  wire [0:0] vmdel_NW2__full1;
  wire [0:0] vmdel_NW2__pcbad;
  wire [1:0] vmdel_NW3__block_ready;
  wire [0:0] vmdel_NW3__busy;
  wire [280:0] vmdel_NW3__dq;
  wire [0:0] vmdel_NW3__fault;
  wire [0:0] vmdel_NW3__full0;
  wire [0:0] vmdel_NW3__full1;
  wire [0:0] vmdel_NW3__pcbad;
  wire [1:0] vmdel_NW4__block_ready;
  wire [0:0] vmdel_NW4__busy;
  wire [280:0] vmdel_NW4__dq;
  wire [0:0] vmdel_NW4__fault;
  wire [0:0] vmdel_NW4__full0;
  wire [0:0] vmdel_NW4__full1;
  wire [0:0] vmdel_NW4__pcbad;
  wire [1:0] vmdel_NW5__block_ready;
  wire [0:0] vmdel_NW5__busy;
  wire [280:0] vmdel_NW5__dq;
  wire [0:0] vmdel_NW5__fault;
  wire [0:0] vmdel_NW5__full0;
  wire [0:0] vmdel_NW5__full1;
  wire [0:0] vmdel_NW5__pcbad;
  wire [1:0] vmdel_NW6__block_ready;
  wire [0:0] vmdel_NW6__busy;
  wire [280:0] vmdel_NW6__dq;
  wire [0:0] vmdel_NW6__fault;
  wire [0:0] vmdel_NW6__full0;
  wire [0:0] vmdel_NW6__full1;
  wire [0:0] vmdel_NW6__pcbad;
  wire [1:0] vmdel_NW7__block_ready;
  wire [0:0] vmdel_NW7__busy;
  wire [280:0] vmdel_NW7__dq;
  wire [0:0] vmdel_NW7__fault;
  wire [0:0] vmdel_NW7__full0;
  wire [0:0] vmdel_NW7__full1;
  wire [0:0] vmdel_NW7__pcbad;
  wire [0:0] vmfc_NE__active;
  wire [0:0] vmfc_NE__calendar_v;
  wire [0:0] vmfc_NE__done;
  wire [0:0] vmfc_NE__fault;
  wire [88:0] vmfc_NE__payload;
  wire [0:0] vmfc_NE__tgt_configured;
  wire [0:0] vmfc_NE__tgt_fault;
  wire [0:0] vmfc_NW__active;
  wire [0:0] vmfc_NW__calendar_v;
  wire [0:0] vmfc_NW__done;
  wire [0:0] vmfc_NW__fault;
  wire [88:0] vmfc_NW__payload;
  wire [0:0] vmfc_NW__tgt_configured;
  wire [0:0] vmfc_NW__tgt_fault;
  wire [119:0] vmks_NW0__c_k_addr;
  wire [15:0] vmks_NW0__c_k_len;
  wire [67:0] vmks_NW0__c_k_tag;
  wire [3:0] vmks_NW0__c_k_v;
  wire [1023:0] vmks_NW0__c_k_wdata;
  wire [3:0] vmks_NW0__c_k_we;
  wire [127:0] vmks_NW0__c_k_wstrb;
  wire [3:0] vmks_NW0__c_kr_rdy;
  wire [0:0] vmks_NW0__fault;
  wire [3:0] vmks_NW0__fill_bank;
  wire [1023:0] vmks_NW0__fill_data;
  wire [63:0] vmks_NW0__fill_epoch;
  wire [23:0] vmks_NW0__fill_slot;
  wire [3:0] vmks_NW0__fill_v;
  wire [3:0] vmks_NW0__g_k_rdy;
  wire [3:0] vmks_NW0__g_k_wr_done;
  wire [15:0] vmks_NW0__g_kr_beat;
  wire [1023:0] vmks_NW0__g_kr_data;
  wire [67:0] vmks_NW0__g_kr_tag;
  wire [3:0] vmks_NW0__g_kr_v;
  wire [3:0] vmks_NW0__w_k_rdy;
  wire [3:0] vmks_NW0__w_k_wr_done;
  wire [119:0] vmks_NW1__c_k_addr;
  wire [15:0] vmks_NW1__c_k_len;
  wire [67:0] vmks_NW1__c_k_tag;
  wire [3:0] vmks_NW1__c_k_v;
  wire [1023:0] vmks_NW1__c_k_wdata;
  wire [3:0] vmks_NW1__c_k_we;
  wire [127:0] vmks_NW1__c_k_wstrb;
  wire [3:0] vmks_NW1__c_kr_rdy;
  wire [0:0] vmks_NW1__fault;
  wire [3:0] vmks_NW1__fill_bank;
  wire [1023:0] vmks_NW1__fill_data;
  wire [63:0] vmks_NW1__fill_epoch;
  wire [23:0] vmks_NW1__fill_slot;
  wire [3:0] vmks_NW1__fill_v;
  wire [3:0] vmks_NW1__g_k_rdy;
  wire [3:0] vmks_NW1__g_k_wr_done;
  wire [15:0] vmks_NW1__g_kr_beat;
  wire [1023:0] vmks_NW1__g_kr_data;
  wire [67:0] vmks_NW1__g_kr_tag;
  wire [3:0] vmks_NW1__g_kr_v;
  wire [3:0] vmks_NW1__w_k_rdy;
  wire [3:0] vmks_NW1__w_k_wr_done;
  wire [119:0] vmks_NW2__c_k_addr;
  wire [15:0] vmks_NW2__c_k_len;
  wire [67:0] vmks_NW2__c_k_tag;
  wire [3:0] vmks_NW2__c_k_v;
  wire [1023:0] vmks_NW2__c_k_wdata;
  wire [3:0] vmks_NW2__c_k_we;
  wire [127:0] vmks_NW2__c_k_wstrb;
  wire [3:0] vmks_NW2__c_kr_rdy;
  wire [0:0] vmks_NW2__fault;
  wire [3:0] vmks_NW2__fill_bank;
  wire [1023:0] vmks_NW2__fill_data;
  wire [63:0] vmks_NW2__fill_epoch;
  wire [23:0] vmks_NW2__fill_slot;
  wire [3:0] vmks_NW2__fill_v;
  wire [3:0] vmks_NW2__g_k_rdy;
  wire [3:0] vmks_NW2__g_k_wr_done;
  wire [15:0] vmks_NW2__g_kr_beat;
  wire [1023:0] vmks_NW2__g_kr_data;
  wire [67:0] vmks_NW2__g_kr_tag;
  wire [3:0] vmks_NW2__g_kr_v;
  wire [3:0] vmks_NW2__w_k_rdy;
  wire [3:0] vmks_NW2__w_k_wr_done;
  wire [119:0] vmks_NW3__c_k_addr;
  wire [15:0] vmks_NW3__c_k_len;
  wire [67:0] vmks_NW3__c_k_tag;
  wire [3:0] vmks_NW3__c_k_v;
  wire [1023:0] vmks_NW3__c_k_wdata;
  wire [3:0] vmks_NW3__c_k_we;
  wire [127:0] vmks_NW3__c_k_wstrb;
  wire [3:0] vmks_NW3__c_kr_rdy;
  wire [0:0] vmks_NW3__fault;
  wire [3:0] vmks_NW3__fill_bank;
  wire [1023:0] vmks_NW3__fill_data;
  wire [63:0] vmks_NW3__fill_epoch;
  wire [23:0] vmks_NW3__fill_slot;
  wire [3:0] vmks_NW3__fill_v;
  wire [3:0] vmks_NW3__g_k_rdy;
  wire [3:0] vmks_NW3__g_k_wr_done;
  wire [15:0] vmks_NW3__g_kr_beat;
  wire [1023:0] vmks_NW3__g_kr_data;
  wire [67:0] vmks_NW3__g_kr_tag;
  wire [3:0] vmks_NW3__g_kr_v;
  wire [3:0] vmks_NW3__w_k_rdy;
  wire [3:0] vmks_NW3__w_k_wr_done;
  wire [119:0] vmks_NW4__c_k_addr;
  wire [15:0] vmks_NW4__c_k_len;
  wire [67:0] vmks_NW4__c_k_tag;
  wire [3:0] vmks_NW4__c_k_v;
  wire [1023:0] vmks_NW4__c_k_wdata;
  wire [3:0] vmks_NW4__c_k_we;
  wire [127:0] vmks_NW4__c_k_wstrb;
  wire [3:0] vmks_NW4__c_kr_rdy;
  wire [0:0] vmks_NW4__fault;
  wire [3:0] vmks_NW4__fill_bank;
  wire [1023:0] vmks_NW4__fill_data;
  wire [63:0] vmks_NW4__fill_epoch;
  wire [23:0] vmks_NW4__fill_slot;
  wire [3:0] vmks_NW4__fill_v;
  wire [3:0] vmks_NW4__g_k_rdy;
  wire [3:0] vmks_NW4__g_k_wr_done;
  wire [15:0] vmks_NW4__g_kr_beat;
  wire [1023:0] vmks_NW4__g_kr_data;
  wire [67:0] vmks_NW4__g_kr_tag;
  wire [3:0] vmks_NW4__g_kr_v;
  wire [3:0] vmks_NW4__w_k_rdy;
  wire [3:0] vmks_NW4__w_k_wr_done;
  wire [119:0] vmks_NW5__c_k_addr;
  wire [15:0] vmks_NW5__c_k_len;
  wire [67:0] vmks_NW5__c_k_tag;
  wire [3:0] vmks_NW5__c_k_v;
  wire [1023:0] vmks_NW5__c_k_wdata;
  wire [3:0] vmks_NW5__c_k_we;
  wire [127:0] vmks_NW5__c_k_wstrb;
  wire [3:0] vmks_NW5__c_kr_rdy;
  wire [0:0] vmks_NW5__fault;
  wire [3:0] vmks_NW5__fill_bank;
  wire [1023:0] vmks_NW5__fill_data;
  wire [63:0] vmks_NW5__fill_epoch;
  wire [23:0] vmks_NW5__fill_slot;
  wire [3:0] vmks_NW5__fill_v;
  wire [3:0] vmks_NW5__g_k_rdy;
  wire [3:0] vmks_NW5__g_k_wr_done;
  wire [15:0] vmks_NW5__g_kr_beat;
  wire [1023:0] vmks_NW5__g_kr_data;
  wire [67:0] vmks_NW5__g_kr_tag;
  wire [3:0] vmks_NW5__g_kr_v;
  wire [3:0] vmks_NW5__w_k_rdy;
  wire [3:0] vmks_NW5__w_k_wr_done;
  wire [119:0] vmks_NW6__c_k_addr;
  wire [15:0] vmks_NW6__c_k_len;
  wire [67:0] vmks_NW6__c_k_tag;
  wire [3:0] vmks_NW6__c_k_v;
  wire [1023:0] vmks_NW6__c_k_wdata;
  wire [3:0] vmks_NW6__c_k_we;
  wire [127:0] vmks_NW6__c_k_wstrb;
  wire [3:0] vmks_NW6__c_kr_rdy;
  wire [0:0] vmks_NW6__fault;
  wire [3:0] vmks_NW6__fill_bank;
  wire [1023:0] vmks_NW6__fill_data;
  wire [63:0] vmks_NW6__fill_epoch;
  wire [23:0] vmks_NW6__fill_slot;
  wire [3:0] vmks_NW6__fill_v;
  wire [3:0] vmks_NW6__g_k_rdy;
  wire [3:0] vmks_NW6__g_k_wr_done;
  wire [15:0] vmks_NW6__g_kr_beat;
  wire [1023:0] vmks_NW6__g_kr_data;
  wire [67:0] vmks_NW6__g_kr_tag;
  wire [3:0] vmks_NW6__g_kr_v;
  wire [3:0] vmks_NW6__w_k_rdy;
  wire [3:0] vmks_NW6__w_k_wr_done;
  wire [119:0] vmks_NW7__c_k_addr;
  wire [15:0] vmks_NW7__c_k_len;
  wire [67:0] vmks_NW7__c_k_tag;
  wire [3:0] vmks_NW7__c_k_v;
  wire [1023:0] vmks_NW7__c_k_wdata;
  wire [3:0] vmks_NW7__c_k_we;
  wire [127:0] vmks_NW7__c_k_wstrb;
  wire [3:0] vmks_NW7__c_kr_rdy;
  wire [0:0] vmks_NW7__fault;
  wire [3:0] vmks_NW7__fill_bank;
  wire [1023:0] vmks_NW7__fill_data;
  wire [63:0] vmks_NW7__fill_epoch;
  wire [23:0] vmks_NW7__fill_slot;
  wire [3:0] vmks_NW7__fill_v;
  wire [3:0] vmks_NW7__g_k_rdy;
  wire [3:0] vmks_NW7__g_k_wr_done;
  wire [15:0] vmks_NW7__g_kr_beat;
  wire [1023:0] vmks_NW7__g_kr_data;
  wire [67:0] vmks_NW7__g_kr_tag;
  wire [3:0] vmks_NW7__g_kr_v;
  wire [3:0] vmks_NW7__w_k_rdy;
  wire [3:0] vmks_NW7__w_k_wr_done;
  wire [0:0] vmm_NW0__flt;
  wire [0:0] vmm_NW0__wq_done1;
  wire [0:0] vmm_NW0__wq_done2;
  wire [280:0] vmm_NW0__wq_m;
  wire [0:0] vmm_NW1__flt;
  wire [0:0] vmm_NW1__wq_done1;
  wire [0:0] vmm_NW1__wq_done2;
  wire [280:0] vmm_NW1__wq_m;
  wire [0:0] vmm_NW2__flt;
  wire [0:0] vmm_NW2__wq_done1;
  wire [0:0] vmm_NW2__wq_done2;
  wire [280:0] vmm_NW2__wq_m;
  wire [0:0] vmm_NW3__flt;
  wire [0:0] vmm_NW3__wq_done1;
  wire [0:0] vmm_NW3__wq_done2;
  wire [280:0] vmm_NW3__wq_m;
  wire [0:0] vmm_NW4__flt;
  wire [0:0] vmm_NW4__wq_done1;
  wire [0:0] vmm_NW4__wq_done2;
  wire [280:0] vmm_NW4__wq_m;
  wire [0:0] vmm_NW5__flt;
  wire [0:0] vmm_NW5__wq_done1;
  wire [0:0] vmm_NW5__wq_done2;
  wire [280:0] vmm_NW5__wq_m;
  wire [0:0] vmm_NW6__flt;
  wire [0:0] vmm_NW6__wq_done1;
  wire [0:0] vmm_NW6__wq_done2;
  wire [280:0] vmm_NW6__wq_m;
  wire [0:0] vmm_NW7__flt;
  wire [0:0] vmm_NW7__wq_done1;
  wire [0:0] vmm_NW7__wq_done2;
  wire [280:0] vmm_NW7__wq_m;
  wire [119:0] wbc_NE__o_wbw_base;
  wire [47:0] wbc_NE__o_wbw_total;
  wire [3:0] wbc_NE__o_wbw_v;
  wire [119:0] wbc_NW__o_wbw_base;
  wire [47:0] wbc_NW__o_wbw_total;
  wire [3:0] wbc_NW__o_wbw_v;
  wire [0:0] wbk_NE__fault;
  wire [479:0] wbk_NE__w_k_addr;
  wire [15:0] wbk_NE__w_k_v;
  wire [4095:0] wbk_NE__w_k_wdata;
  wire [11:0] wbk_NE__wa;
  wire [0:0] wbk_NE__wb_ready;
  wire [29:0] wbk_NE__wbw_base;
  wire [11:0] wbk_NE__wbw_total;
  wire [0:0] wbk_NE__wbw_v;
  wire [0:0] wbk_NW__fault;
  wire [479:0] wbk_NW__w_k_addr;
  wire [15:0] wbk_NW__w_k_v;
  wire [4095:0] wbk_NW__w_k_wdata;
  wire [11:0] wbk_NW__wa;
  wire [0:0] wbk_NW__wb_ready;
  wire [29:0] wbk_NW__wbw_base;
  wire [11:0] wbk_NW__wbw_total;
  wire [0:0] wbk_NW__wbw_v;
  wire [0:0] xc_NW0__active;
  wire [108:0] xc_NW0__cmd_ext;
  wire [0:0] xc_NW0__configured;
  wire [0:0] xc_NW0__done;
  wire [0:0] xc_NW0__fault;
  wire [63:0] xc_NW0__kv_desc;
  wire [0:0] xc_NW1__active;
  wire [108:0] xc_NW1__cmd_ext;
  wire [0:0] xc_NW1__configured;
  wire [0:0] xc_NW1__done;
  wire [0:0] xc_NW1__fault;
  wire [63:0] xc_NW1__kv_desc;
  wire [0:0] xc_NW2__active;
  wire [108:0] xc_NW2__cmd_ext;
  wire [0:0] xc_NW2__configured;
  wire [0:0] xc_NW2__done;
  wire [0:0] xc_NW2__fault;
  wire [63:0] xc_NW2__kv_desc;
  wire [0:0] xc_NW3__active;
  wire [108:0] xc_NW3__cmd_ext;
  wire [0:0] xc_NW3__configured;
  wire [0:0] xc_NW3__done;
  wire [0:0] xc_NW3__fault;
  wire [63:0] xc_NW3__kv_desc;
  wire [0:0] xc_NW4__active;
  wire [108:0] xc_NW4__cmd_ext;
  wire [0:0] xc_NW4__configured;
  wire [0:0] xc_NW4__done;
  wire [0:0] xc_NW4__fault;
  wire [63:0] xc_NW4__kv_desc;
  wire [0:0] xc_NW5__active;
  wire [108:0] xc_NW5__cmd_ext;
  wire [0:0] xc_NW5__configured;
  wire [0:0] xc_NW5__done;
  wire [0:0] xc_NW5__fault;
  wire [63:0] xc_NW5__kv_desc;
  wire [0:0] xc_NW6__active;
  wire [108:0] xc_NW6__cmd_ext;
  wire [0:0] xc_NW6__configured;
  wire [0:0] xc_NW6__done;
  wire [0:0] xc_NW6__fault;
  wire [63:0] xc_NW6__kv_desc;
  wire [0:0] xc_NW7__active;
  wire [108:0] xc_NW7__cmd_ext;
  wire [0:0] xc_NW7__configured;
  wire [0:0] xc_NW7__done;
  wire [0:0] xc_NW7__fault;
  wire [63:0] xc_NW7__kv_desc;
  wire [9:0] xl_NE_aqhi__e;
  wire [0:0] xl_NE_aqhi__fault;
  wire [255:0] xl_NE_aqhi__q;
  wire [0:0] xl_NE_aqhi__vo;
  wire [9:0] xl_NE_aqlo__e;
  wire [0:0] xl_NE_aqlo__fault;
  wire [255:0] xl_NE_aqlo__q;
  wire [0:0] xl_NE_aqlo__vo;
  wire [0:0] xl_NE_ctl__active;
  wire [25:0] xl_NE_ctl__bsel;
  wire [1023:0] xl_NE_ctl__c_d;
  wire [0:0] xl_NE_ctl__c_mhi;
  wire [0:0] xl_NE_ctl__c_mlo;
  wire [6:0] xl_NE_ctl__c_wa;
  wire [3:0] xl_NE_ctl__c_wce;
  wire [0:0] xl_NE_ctl__configured;
  wire [6:0] xl_NE_ctl__eg_bqaddr;
  wire [6:0] xl_NE_ctl__eg_bqb;
  wire [0:0] xl_NE_ctl__eg_bqlast;
  wire [0:0] xl_NE_ctl__eg_bqv;
  wire [7:0] xl_NE_ctl__eg_ed5;
  wire [16:0] xl_NE_ctl__eg_ede;
  wire [0:0] xl_NE_ctl__fault;
  wire [2047:0] xl_NE_ctl__l_d_o;
  wire [63:0] xl_NE_ctl__lane_en;
  wire [0:0] xl_NE_ctl__qv_hi;
  wire [0:0] xl_NE_ctl__qv_lo;
  wire [6:0] xl_NE_ctl__r_a;
  wire [7:0] xl_NE_ctl__r_ce;
  wire [15:0] xl_NE_ctl__r_wsel;
  wire [0:0] xl_NE_ctl__rn_o;
  wire [135:0] xl_NE_ctl__rq;
  wire [0:0] xl_NE_ctl__zhi;
  wire [0:0] xl_NE_ctl__zlo;
  wire [9:0] xl_NW_aqhi__e;
  wire [0:0] xl_NW_aqhi__fault;
  wire [255:0] xl_NW_aqhi__q;
  wire [0:0] xl_NW_aqhi__vo;
  wire [9:0] xl_NW_aqlo__e;
  wire [0:0] xl_NW_aqlo__fault;
  wire [255:0] xl_NW_aqlo__q;
  wire [0:0] xl_NW_aqlo__vo;
  wire [0:0] xl_NW_ctl__active;
  wire [25:0] xl_NW_ctl__bsel;
  wire [1023:0] xl_NW_ctl__c_d;
  wire [0:0] xl_NW_ctl__c_mhi;
  wire [0:0] xl_NW_ctl__c_mlo;
  wire [6:0] xl_NW_ctl__c_wa;
  wire [3:0] xl_NW_ctl__c_wce;
  wire [0:0] xl_NW_ctl__configured;
  wire [6:0] xl_NW_ctl__eg_bqaddr;
  wire [6:0] xl_NW_ctl__eg_bqb;
  wire [0:0] xl_NW_ctl__eg_bqlast;
  wire [0:0] xl_NW_ctl__eg_bqv;
  wire [7:0] xl_NW_ctl__eg_ed5;
  wire [16:0] xl_NW_ctl__eg_ede;
  wire [0:0] xl_NW_ctl__fault;
  wire [2047:0] xl_NW_ctl__l_d_o;
  wire [63:0] xl_NW_ctl__lane_en;
  wire [0:0] xl_NW_ctl__qv_hi;
  wire [0:0] xl_NW_ctl__qv_lo;
  wire [6:0] xl_NW_ctl__r_a;
  wire [7:0] xl_NW_ctl__r_ce;
  wire [15:0] xl_NW_ctl__r_wsel;
  wire [0:0] xl_NW_ctl__rn_o;
  wire [135:0] xl_NW_ctl__rq;
  wire [0:0] xl_NW_ctl__zhi;
  wire [0:0] xl_NW_ctl__zlo;
  wire [2047:0] xq_NE_p0_bd__bq_d;
  wire [255:0] xq_NE_p0_bfq0__rwq;
  wire [255:0] xq_NE_p0_bfq1__rwq;
  wire [255:0] xq_NE_p0_bfq2__rwq;
  wire [255:0] xq_NE_p0_bfq3__rwq;
  wire [0:0] xq_NE_p0_eg__x_done;
  wire [6:0] xq_NE_p0_eg__xw_addr;
  wire [2047:0] xq_NE_p0_eg__xw_data;
  wire [0:0] xq_NE_p0_eg__xw_en;
  wire [6:0] xq_NE_p0_eg__xw_grp;
  wire [0:0] xq_NE_p0_eg__xw_last;
  wire [2047:0] xq_NE_p1_bd__bq_d;
  wire [255:0] xq_NE_p1_bfq0__rwq;
  wire [255:0] xq_NE_p1_bfq1__rwq;
  wire [255:0] xq_NE_p1_bfq2__rwq;
  wire [255:0] xq_NE_p1_bfq3__rwq;
  wire [0:0] xq_NE_p1_eg__x_done;
  wire [6:0] xq_NE_p1_eg__xw_addr;
  wire [2047:0] xq_NE_p1_eg__xw_data;
  wire [0:0] xq_NE_p1_eg__xw_en;
  wire [6:0] xq_NE_p1_eg__xw_grp;
  wire [0:0] xq_NE_p1_eg__xw_last;
  wire [2047:0] xq_NW_p0_bd__bq_d;
  wire [255:0] xq_NW_p0_bfq0__rwq;
  wire [255:0] xq_NW_p0_bfq1__rwq;
  wire [255:0] xq_NW_p0_bfq2__rwq;
  wire [255:0] xq_NW_p0_bfq3__rwq;
  wire [0:0] xq_NW_p0_eg__x_done;
  wire [6:0] xq_NW_p0_eg__xw_addr;
  wire [2047:0] xq_NW_p0_eg__xw_data;
  wire [0:0] xq_NW_p0_eg__xw_en;
  wire [6:0] xq_NW_p0_eg__xw_grp;
  wire [0:0] xq_NW_p0_eg__xw_last;
  wire [2047:0] xq_NW_p1_bd__bq_d;
  wire [255:0] xq_NW_p1_bfq0__rwq;
  wire [255:0] xq_NW_p1_bfq1__rwq;
  wire [255:0] xq_NW_p1_bfq2__rwq;
  wire [255:0] xq_NW_p1_bfq3__rwq;
  wire [0:0] xq_NW_p1_eg__x_done;
  wire [6:0] xq_NW_p1_eg__xw_addr;
  wire [2047:0] xq_NW_p1_eg__xw_data;
  wire [0:0] xq_NW_p1_eg__xw_en;
  wire [6:0] xq_NW_p1_eg__xw_grp;
  wire [0:0] xq_NW_p1_eg__xw_last;
  ot_hbm_b2_ep_root_relay b2_ep1_root (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .rx_i({ep_S1__fault[0:0], ep_S1__phy_up[0:0], ep_S1__rx_pin_v[0:0], ep_S1__rx_pin_flit[611:0]}),
    .tx_i({epcal_NW__payload[56:38], hb_coll_NW__tx_pin_v[2:2], hb_coll_NW__tx_pin_flit[1835:1224]}),
    .rx_o(b2_ep1_root__rx_o[614:0]),
    .tx_o(b2_ep1_root__tx_o[631:0])
  );
  hfd_hgi_vm_calendar_f20 calendar_NE (
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_cap(hb_ckgen__pll_stream[0:0]),
    .clk_mem(hb_ckgen__pll_stream[0:0]),
    .clk_tgt(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__calendar_NE__rst_n[0:0]),
    .tgt(8'b01100011),
    .cfg_v(hleaf_NE__a_cfg_v[0:0]),
    .cfg_target(hleaf_NE__a_cfg_target[7:0]),
    .cfg_addr(hleaf_NE__a_cfg_addr[11:0]),
    .cfg_data(hleaf_NE__a_cfg_data[255:0]),
    .desc_v(hleaf_NE__a_desc_v[0:0]),
    .desc_base(hleaf_NE__a_desc_base[11:0]),
    .desc_limit(hleaf_NE__a_desc_limit[12:0]),
    .desc_loops(hleaf_NE__a_desc_loops[15:0]),
    .launch_v(hleaf_NE__a_launch_v[0:0]),
    .tgt_configured(calendar_NE__tgt_configured[0:0]),
    .tgt_fault(calendar_NE__tgt_fault[0:0]),
    .calendar_v(calendar_NE__calendar_v[0:0]),
    .active(calendar_NE__active[0:0]),
    .done(calendar_NE__done[0:0]),
    .fault(calendar_NE__fault[0:0]),
    .ordinal(calendar_NE__ordinal[31:0]),
    .client_seq(calendar_NE__client_seq[9:0]),
    .response_enable(calendar_NE__response_enable[4:0]),
    .response_seq(calendar_NE__response_seq[9:0]),
    .bank_enable(calendar_NE__bank_enable[7:0]),
    .bank_client(calendar_NE__bank_client[23:0]),
    .hub_ring_enable(calendar_NE__hub_ring_enable[1:0]),
    .hub_ring_client(calendar_NE__hub_ring_client[5:0]),
    .rslot_v(calendar_NE__rslot_v[7:0]),
    .wslot_v(calendar_NE__wslot_v[7:0]),
    .rslot(calendar_NE__rslot[23:0]),
    .wslot(calendar_NE__wslot[23:0]),
    .ring_tx_enable(calendar_NE__ring_tx_enable[1:0]),
    .ring_tx_source(calendar_NE__ring_tx_source[5:0]),
    .replay_enable(calendar_NE__replay_enable[0:0]),
    .replay_source(calendar_NE__replay_source[0:0]),
    .lg_local_read(calendar_NE__lg_local_read[23:0]),
    .lg_local_write(calendar_NE__lg_local_write[23:0])
  );
  hfd_hgi_vm_calendar_f20 calendar_NW (
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_cap(hb_ckgen__pll_stream[0:0]),
    .clk_mem(hb_ckgen__pll_stream[0:0]),
    .clk_tgt(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__calendar_NW__rst_n[0:0]),
    .tgt(8'b01100010),
    .cfg_v(hleaf_NW__a_cfg_v[0:0]),
    .cfg_target(hleaf_NW__a_cfg_target[7:0]),
    .cfg_addr(hleaf_NW__a_cfg_addr[11:0]),
    .cfg_data(hleaf_NW__a_cfg_data[255:0]),
    .desc_v(hleaf_NW__a_desc_v[0:0]),
    .desc_base(hleaf_NW__a_desc_base[11:0]),
    .desc_limit(hleaf_NW__a_desc_limit[12:0]),
    .desc_loops(hleaf_NW__a_desc_loops[15:0]),
    .launch_v(hleaf_NW__a_launch_v[0:0]),
    .tgt_configured(calendar_NW__tgt_configured[0:0]),
    .tgt_fault(calendar_NW__tgt_fault[0:0]),
    .calendar_v(calendar_NW__calendar_v[0:0]),
    .active(calendar_NW__active[0:0]),
    .done(calendar_NW__done[0:0]),
    .fault(calendar_NW__fault[0:0]),
    .ordinal(calendar_NW__ordinal[31:0]),
    .client_seq(calendar_NW__client_seq[9:0]),
    .response_enable(calendar_NW__response_enable[4:0]),
    .response_seq(calendar_NW__response_seq[9:0]),
    .bank_enable(calendar_NW__bank_enable[7:0]),
    .bank_client(calendar_NW__bank_client[23:0]),
    .hub_ring_enable(calendar_NW__hub_ring_enable[1:0]),
    .hub_ring_client(calendar_NW__hub_ring_client[5:0]),
    .rslot_v(calendar_NW__rslot_v[7:0]),
    .wslot_v(calendar_NW__wslot_v[7:0]),
    .rslot(calendar_NW__rslot[23:0]),
    .wslot(calendar_NW__wslot[23:0]),
    .ring_tx_enable(calendar_NW__ring_tx_enable[1:0]),
    .ring_tx_source(calendar_NW__ring_tx_source[5:0]),
    .replay_enable(calendar_NW__replay_enable[0:0]),
    .replay_source(calendar_NW__replay_source[0:0]),
    .lg_local_read(calendar_NW__lg_local_read[23:0]),
    .lg_local_write(calendar_NW__lg_local_write[23:0])
  );
  hfd_hgi_vm_calendar_f20 calendar_SE (
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_cap(hb_ckgen__pll_stream[0:0]),
    .clk_mem(hb_ckgen__pll_stream[0:0]),
    .clk_tgt(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__calendar_SE__rst_n[0:0]),
    .tgt(8'b01100001),
    .cfg_v(hleaf_SE__a_cfg_v[0:0]),
    .cfg_target(hleaf_SE__a_cfg_target[7:0]),
    .cfg_addr(hleaf_SE__a_cfg_addr[11:0]),
    .cfg_data(hleaf_SE__a_cfg_data[255:0]),
    .desc_v(hleaf_SE__a_desc_v[0:0]),
    .desc_base(hleaf_SE__a_desc_base[11:0]),
    .desc_limit(hleaf_SE__a_desc_limit[12:0]),
    .desc_loops(hleaf_SE__a_desc_loops[15:0]),
    .launch_v(hleaf_SE__a_launch_v[0:0]),
    .tgt_configured(calendar_SE__tgt_configured[0:0]),
    .tgt_fault(calendar_SE__tgt_fault[0:0]),
    .calendar_v(calendar_SE__calendar_v[0:0]),
    .active(calendar_SE__active[0:0]),
    .done(calendar_SE__done[0:0]),
    .fault(calendar_SE__fault[0:0]),
    .ordinal(calendar_SE__ordinal[31:0]),
    .client_seq(calendar_SE__client_seq[9:0]),
    .response_enable(calendar_SE__response_enable[4:0]),
    .response_seq(calendar_SE__response_seq[9:0]),
    .bank_enable(calendar_SE__bank_enable[7:0]),
    .bank_client(calendar_SE__bank_client[23:0]),
    .hub_ring_enable(calendar_SE__hub_ring_enable[1:0]),
    .hub_ring_client(calendar_SE__hub_ring_client[5:0]),
    .rslot_v(calendar_SE__rslot_v[7:0]),
    .wslot_v(calendar_SE__wslot_v[7:0]),
    .rslot(calendar_SE__rslot[23:0]),
    .wslot(calendar_SE__wslot[23:0]),
    .ring_tx_enable(calendar_SE__ring_tx_enable[1:0]),
    .ring_tx_source(calendar_SE__ring_tx_source[5:0]),
    .replay_enable(calendar_SE__replay_enable[0:0]),
    .replay_source(calendar_SE__replay_source[0:0]),
    .lg_local_read(calendar_SE__lg_local_read[23:0]),
    .lg_local_write(calendar_SE__lg_local_write[23:0])
  );
  hfd_hgi_vm_calendar_f20 calendar_SW (
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_cap(hb_ckgen__pll_stream[0:0]),
    .clk_mem(hb_ckgen__pll_stream[0:0]),
    .clk_tgt(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__calendar_SW__rst_n[0:0]),
    .tgt(8'b01100000),
    .cfg_v(hleaf_SW__a_cfg_v[0:0]),
    .cfg_target(hleaf_SW__a_cfg_target[7:0]),
    .cfg_addr(hleaf_SW__a_cfg_addr[11:0]),
    .cfg_data(hleaf_SW__a_cfg_data[255:0]),
    .desc_v(hleaf_SW__a_desc_v[0:0]),
    .desc_base(hleaf_SW__a_desc_base[11:0]),
    .desc_limit(hleaf_SW__a_desc_limit[12:0]),
    .desc_loops(hleaf_SW__a_desc_loops[15:0]),
    .launch_v(hleaf_SW__a_launch_v[0:0]),
    .tgt_configured(calendar_SW__tgt_configured[0:0]),
    .tgt_fault(calendar_SW__tgt_fault[0:0]),
    .calendar_v(calendar_SW__calendar_v[0:0]),
    .active(calendar_SW__active[0:0]),
    .done(calendar_SW__done[0:0]),
    .fault(calendar_SW__fault[0:0]),
    .ordinal(calendar_SW__ordinal[31:0]),
    .client_seq(calendar_SW__client_seq[9:0]),
    .response_enable(calendar_SW__response_enable[4:0]),
    .response_seq(calendar_SW__response_seq[9:0]),
    .bank_enable(calendar_SW__bank_enable[7:0]),
    .bank_client(calendar_SW__bank_client[23:0]),
    .hub_ring_enable(calendar_SW__hub_ring_enable[1:0]),
    .hub_ring_client(calendar_SW__hub_ring_client[5:0]),
    .rslot_v(calendar_SW__rslot_v[7:0]),
    .wslot_v(calendar_SW__wslot_v[7:0]),
    .rslot(calendar_SW__rslot[23:0]),
    .wslot(calendar_SW__wslot[23:0]),
    .ring_tx_enable(calendar_SW__ring_tx_enable[1:0]),
    .ring_tx_source(calendar_SW__ring_tx_source[5:0]),
    .replay_enable(calendar_SW__replay_enable[0:0]),
    .replay_source(calendar_SW__replay_source[0:0]),
    .lg_local_read(calendar_SW__lg_local_read[23:0]),
    .lg_local_write(calendar_SW__lg_local_write[23:0])
  );
  ot_hgi_coll_inj_copy cic_NE (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .inj_addr_i(hb_coll_NE__hgi_inj_addr[159:0]),
    .inj_rd_i(hb_coll_NE__inj_rd[1:0]),
    .inj_addr_o(cic_NE__inj_addr_o[159:0]),
    .inj_rd_o(cic_NE__inj_rd_o[1:0])
  );
  ot_hgi_coll_inj_copy cic_NW (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .inj_addr_i(hb_coll_NW__hgi_inj_addr[159:0]),
    .inj_rd_i(hb_coll_NW__inj_rd[1:0]),
    .inj_addr_o(cic_NW__inj_addr_o[159:0]),
    .inj_rd_o(cic_NW__inj_rd_o[1:0])
  );
  ot_hgi_coll_inj_idx_join_rg #(.INJLAT(12)) cij_NE (
    .clk_r0(hb_ckgen__pll_stream[0:0]),
    .clk_r1(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .rst_n_r1(hb_ckgen__por_stream[0:0]),
    .inj_rd(cic_NE__inj_rd_o[1:0]),
    .inj_rd_r1(cic_NE__inj_rd_o[1:0]),
    .inj_idx(hb_coll_NE__inj_idx[31:0]),
    .inj_idx_r1(hb_coll_NE__inj_idx[31:0]),
    .inj_addr(cic_NE__inj_addr_o[159:0]),
    .inj_addr_r1(cic_NE__inj_addr_o[159:0]),
    .su_inj_d_r0({cxij_NE_s__inj_d[767:512], cxij_NE_s__inj_d[255:0]}),
    .su_inj_d_r1({cxij_NE_s__inj_d[1023:768], cxij_NE_s__inj_d[511:256]}),
    .idx_tx_v(hb_idx__link__tx_v[3:0]),
    .idx_tx_v_r1(hb_idx__link__tx_v[3:0]),
    .idx_tx_h({hb_idx__link__tx[2179:2147], hb_idx__link__tx[1634:1602], hb_idx__link__tx[1089:1057], hb_idx__link__tx[544:512]}),
    .idx_tx_h_r1({hb_idx__link__tx[2179:2147], hb_idx__link__tx[1634:1602], hb_idx__link__tx[1089:1057], hb_idx__link__tx[544:512]}),
    .idx_tx_r0({hb_idx__link__tx[1890:1635], hb_idx__link__tx[1345:1090], hb_idx__link__tx[800:545], hb_idx__link__tx[255:0]}),
    .idx_tx_r1({hb_idx__link__tx[2146:1891], hb_idx__link__tx[1601:1346], hb_idx__link__tx[1056:801], hb_idx__link__tx[511:256]}),
    .inj_d_r0(cij_NE__inj_d_r0[511:0]),
    .inj_d_r1(cij_NE__inj_d_r1[511:0]),
    .fault(cij_NE__fault[0:0])
  );
  ot_hgi_coll_inj_idx_join_rg #(.INJLAT(12)) cij_NW (
    .clk_r0(hb_ckgen__pll_stream[0:0]),
    .clk_r1(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .rst_n_r1(hb_ckgen__por_stream[0:0]),
    .inj_rd(cic_NW__inj_rd_o[1:0]),
    .inj_rd_r1(cic_NW__inj_rd_o[1:0]),
    .inj_idx(hb_coll_NW__inj_idx[31:0]),
    .inj_idx_r1(hb_coll_NW__inj_idx[31:0]),
    .inj_addr(cic_NW__inj_addr_o[159:0]),
    .inj_addr_r1(cic_NW__inj_addr_o[159:0]),
    .su_inj_d_r0({cxij_NW_s__inj_d[767:512], cxij_NW_s__inj_d[255:0]}),
    .su_inj_d_r1({cxij_NW_s__inj_d[1023:768], cxij_NW_s__inj_d[511:256]}),
    .idx_tx_v(hb_idx__link__tx_v[3:0]),
    .idx_tx_v_r1(hb_idx__link__tx_v[3:0]),
    .idx_tx_h({hb_idx__link__tx[2179:2147], hb_idx__link__tx[1634:1602], hb_idx__link__tx[1089:1057], hb_idx__link__tx[544:512]}),
    .idx_tx_h_r1({hb_idx__link__tx[2179:2147], hb_idx__link__tx[1634:1602], hb_idx__link__tx[1089:1057], hb_idx__link__tx[544:512]}),
    .idx_tx_r0({hb_idx__link__tx[1890:1635], hb_idx__link__tx[1345:1090], hb_idx__link__tx[800:545], hb_idx__link__tx[255:0]}),
    .idx_tx_r1({hb_idx__link__tx[2146:1891], hb_idx__link__tx[1601:1346], hb_idx__link__tx[1056:801], hb_idx__link__tx[511:256]}),
    .inj_d_r0(cij_NW__inj_d_r0[511:0]),
    .inj_d_r1(cij_NW__inj_d_r1[511:0]),
    .fault(cij_NW__fault[0:0])
  );
  ot_hbm_static_cfg_collar_idx256r #(.PAGE_W(1), .NS(1), .NPR(6), .NREC(8), .NGO(2), .NB(2), .NF(5), .XSER(0), .FAN32(1)) col_idx (
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_in(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .tgt(8'b01111000),
    .cfg_v(hleaf_NE__a_cfg_v[0:0]),
    .cfg_target(hleaf_NE__a_cfg_target[7:0]),
    .cfg_addr(hleaf_NE__a_cfg_addr[11:0]),
    .cfg_data(hleaf_NE__a_cfg_data[255:0]),
    .desc_v(hleaf_NE__a_desc_v[0:0]),
    .launch_v(hleaf_NE__a_launch_v[0:0]),
    .c_busy({hb_argmax__busy[0:0], hb_idx__ctl__topk_busy[0:0]}),
    .c_done(hb_idx__ctl__done[0:0]),
    .c_fault({hb_idx__nwsh__fault[0:0], hb_argmax__fault[0:0], hb_idx__ctl__share_fault[0:0], hb_idx__ctl__topk_fault[0:0], hb_idx__ctl__fault[0:0]}),
    .pw_we(col_idx__pw_we[0:0]),
    .pw_addr(col_idx__pw_addr[7:0]),
    .pw_data(col_idx__pw_data[255:0]),
    .prm(col_idx__prm[768:0]),
    .start_v(col_idx__start_v[0:0]),
    .go(col_idx__go[1:0]),
    .rec(col_idx__rec[220:0]),
    .ready(col_idx__ready[0:0]),
    .active(col_idx__active[0:0]),
    .fault(col_idx__fault[0:0])
  );
  ot_hbm_static_cfg_collar #(.PAGE_W(3), .NS(2), .NPR(1), .NREC(0), .NGO(1), .NB(2), .NF(1), .XSER(0)) col_sfu_NE (
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_in(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .tgt(8'b01110111),
    .cfg_v(hleaf_NE__b_cfg_v[0:0]),
    .cfg_target(hleaf_NE__b_cfg_target[7:0]),
    .cfg_addr(hleaf_NE__b_cfg_addr[11:0]),
    .cfg_data(hleaf_NE__b_cfg_data[255:0]),
    .desc_v(hleaf_NE__b_desc_v[0:0]),
    .launch_v(hleaf_NE__b_launch_v[0:0]),
    .c_busy({sfup_NE__io_active[0:0], sfup_NE__programme_active[0:0]}),
    .c_done(sfup_NE__io_done[0:0]),
    .c_fault(sfucore_NE__fault[0:0]),
    .pw_we(col_sfu_NE__pw_we[1:0]),
    .pw_addr(col_sfu_NE__pw_addr[13:0]),
    .pw_data(col_sfu_NE__pw_data[255:0]),
    .prm(col_sfu_NE__prm[255:0]),
    .start_v(col_sfu_NE__start_v[0:0]),
    .go(col_sfu_NE__go[0:0]),
    .rec(col_sfu_NE__rec[220:0]),
    .ready(col_sfu_NE__ready[0:0]),
    .active(col_sfu_NE__active[0:0]),
    .fault(col_sfu_NE__fault[0:0])
  );
  ot_hbm_static_cfg_collar #(.PAGE_W(3), .NS(2), .NPR(1), .NREC(0), .NGO(1), .NB(2), .NF(1), .XSER(0)) col_sfu_NW (
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_in(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .tgt(8'b01110110),
    .cfg_v(hleaf_NW__b_cfg_v[0:0]),
    .cfg_target(hleaf_NW__b_cfg_target[7:0]),
    .cfg_addr(hleaf_NW__b_cfg_addr[11:0]),
    .cfg_data(hleaf_NW__b_cfg_data[255:0]),
    .desc_v(hleaf_NW__b_desc_v[0:0]),
    .launch_v(hleaf_NW__b_launch_v[0:0]),
    .c_busy({sfup_NW__io_active[0:0], sfup_NW__programme_active[0:0]}),
    .c_done(sfup_NW__io_done[0:0]),
    .c_fault(sfucore_NW__fault[0:0]),
    .pw_we(col_sfu_NW__pw_we[1:0]),
    .pw_addr(col_sfu_NW__pw_addr[13:0]),
    .pw_data(col_sfu_NW__pw_data[255:0]),
    .prm(col_sfu_NW__prm[255:0]),
    .start_v(col_sfu_NW__start_v[0:0]),
    .go(col_sfu_NW__go[0:0]),
    .rec(col_sfu_NW__rec[220:0]),
    .ready(col_sfu_NW__ready[0:0]),
    .active(col_sfu_NW__active[0:0]),
    .fault(col_sfu_NW__fault[0:0])
  );
  ot_hbm_static_cfg_collar #(.PAGE_W(12), .NS(1), .NPR(1), .NREC(0), .NGO(1), .NB(2), .NF(1), .XSER(1), .SPARSE_SU(1), .SU_DICT_CAP({32'd1,32'd1,32'd1,32'd1,32'd1,32'd2,32'd13,32'd9,32'd10,32'd3})) col_su (
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_in(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .tgt(8'b01110000),
    .cfg_v(hleaf_NE__a_cfg_v[0:0]),
    .cfg_target(hleaf_NE__a_cfg_target[7:0]),
    .cfg_addr(hleaf_NE__a_cfg_addr[11:0]),
    .cfg_data(hleaf_NE__a_cfg_data[255:0]),
    .desc_v(hleaf_NE__a_desc_v[0:0]),
    .launch_v(hleaf_NE__a_launch_v[0:0]),
    .c_busy({pgp_NW__valid[0:0], pgp_NW__busy[0:0]}),
    .c_done(pgp_NW__done[0:0]),
    .c_fault(su_prog__fault[0:0]),
    .pw_we(col_su__pw_we[0:0]),
    .pw_addr(col_su__pw_addr[22:0]),
    .pw_data(col_su__pw_data[255:0]),
    .prm(col_su__prm[255:0]),
    .start_v(col_su__start_v[0:0]),
    .go(col_su__go[0:0]),
    .rec(col_su__rec[220:0]),
    .ready(col_su__ready[0:0]),
    .active(col_su__active[0:0]),
    .fault(col_su__fault[0:0])
  );
  ot_static_run_target #(.AWA(11), .AWB(8), .RBW(8), .RCW(9), .NA(2), .NF(1), .TGT_PIN(1), .RSYNC(1)) cp_svg_NW0 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .tgt(8'b01010000),
    .cfg_v(hleaf_NW__b_cfg_v[0:0]),
    .cfg_target(hleaf_NW__b_cfg_target[7:0]),
    .cfg_addr(hleaf_NW__b_cfg_addr[11:0]),
    .cfg_data(hleaf_NW__b_cfg_data[255:0]),
    .desc_v(hleaf_NW__b_desc_v[0:0]),
    .desc_base(hleaf_NW__b_desc_base[11:0]),
    .desc_limit(hleaf_NW__b_desc_limit[12:0]),
    .desc_loops(hleaf_NW__b_desc_loops[15:0]),
    .launch_v(hleaf_NW__b_launch_v[0:0]),
    .tgt_active({svg_NW0__program_active[0:0], svg_NW0__running[0:0]}),
    .tgt_fault(svg_NW0__fault[0:0]),
    .a_we(cp_svg_NW0__a_we[0:0]),
    .a_addr(cp_svg_NW0__a_addr[10:0]),
    .a_data(cp_svg_NW0__a_data[255:0]),
    .b_we(cp_svg_NW0__b_we[0:0]),
    .b_addr(cp_svg_NW0__b_addr[7:0]),
    .b_data(cp_svg_NW0__b_data[255:0]),
    .run_v(cp_svg_NW0__run_v[0:0]),
    .run_base(cp_svg_NW0__run_base[7:0]),
    .run_count(cp_svg_NW0__run_count[8:0]),
    .run_arg(cp_svg_NW0__run_arg[7:0]),
    .configured(cp_svg_NW0__configured[0:0]),
    .fault(cp_svg_NW0__fault[0:0]),
    .active(cp_svg_NW0__active[0:0])
  );
  ot_static_run_target #(.AWA(11), .AWB(8), .RBW(8), .RCW(9), .NA(2), .NF(1), .TGT_PIN(1), .RSYNC(1)) cp_svg_NW1 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .tgt(8'b01010001),
    .cfg_v(hleaf_NW__a_cfg_v[0:0]),
    .cfg_target(hleaf_NW__a_cfg_target[7:0]),
    .cfg_addr(hleaf_NW__a_cfg_addr[11:0]),
    .cfg_data(hleaf_NW__a_cfg_data[255:0]),
    .desc_v(hleaf_NW__a_desc_v[0:0]),
    .desc_base(hleaf_NW__a_desc_base[11:0]),
    .desc_limit(hleaf_NW__a_desc_limit[12:0]),
    .desc_loops(hleaf_NW__a_desc_loops[15:0]),
    .launch_v(hleaf_NW__a_launch_v[0:0]),
    .tgt_active({svg_NW1__program_active[0:0], svg_NW1__running[0:0]}),
    .tgt_fault(svg_NW1__fault[0:0]),
    .a_we(cp_svg_NW1__a_we[0:0]),
    .a_addr(cp_svg_NW1__a_addr[10:0]),
    .a_data(cp_svg_NW1__a_data[255:0]),
    .b_we(cp_svg_NW1__b_we[0:0]),
    .b_addr(cp_svg_NW1__b_addr[7:0]),
    .b_data(cp_svg_NW1__b_data[255:0]),
    .run_v(cp_svg_NW1__run_v[0:0]),
    .run_base(cp_svg_NW1__run_base[7:0]),
    .run_count(cp_svg_NW1__run_count[8:0]),
    .run_arg(cp_svg_NW1__run_arg[7:0]),
    .configured(cp_svg_NW1__configured[0:0]),
    .fault(cp_svg_NW1__fault[0:0]),
    .active(cp_svg_NW1__active[0:0])
  );
  ot_static_run_target #(.AWA(11), .AWB(8), .RBW(8), .RCW(9), .NA(2), .NF(1), .TGT_PIN(1), .RSYNC(1)) cp_svg_NW2 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .tgt(8'b01010010),
    .cfg_v(hleaf_NW__b_cfg_v[0:0]),
    .cfg_target(hleaf_NW__b_cfg_target[7:0]),
    .cfg_addr(hleaf_NW__b_cfg_addr[11:0]),
    .cfg_data(hleaf_NW__b_cfg_data[255:0]),
    .desc_v(hleaf_NW__b_desc_v[0:0]),
    .desc_base(hleaf_NW__b_desc_base[11:0]),
    .desc_limit(hleaf_NW__b_desc_limit[12:0]),
    .desc_loops(hleaf_NW__b_desc_loops[15:0]),
    .launch_v(hleaf_NW__b_launch_v[0:0]),
    .tgt_active({svg_NW2__program_active[0:0], svg_NW2__running[0:0]}),
    .tgt_fault(svg_NW2__fault[0:0]),
    .a_we(cp_svg_NW2__a_we[0:0]),
    .a_addr(cp_svg_NW2__a_addr[10:0]),
    .a_data(cp_svg_NW2__a_data[255:0]),
    .b_we(cp_svg_NW2__b_we[0:0]),
    .b_addr(cp_svg_NW2__b_addr[7:0]),
    .b_data(cp_svg_NW2__b_data[255:0]),
    .run_v(cp_svg_NW2__run_v[0:0]),
    .run_base(cp_svg_NW2__run_base[7:0]),
    .run_count(cp_svg_NW2__run_count[8:0]),
    .run_arg(cp_svg_NW2__run_arg[7:0]),
    .configured(cp_svg_NW2__configured[0:0]),
    .fault(cp_svg_NW2__fault[0:0]),
    .active(cp_svg_NW2__active[0:0])
  );
  ot_static_run_target #(.AWA(11), .AWB(8), .RBW(8), .RCW(9), .NA(2), .NF(1), .TGT_PIN(1), .RSYNC(1)) cp_svg_NW3 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .tgt(8'b01010011),
    .cfg_v(hleaf_NW__a_cfg_v[0:0]),
    .cfg_target(hleaf_NW__a_cfg_target[7:0]),
    .cfg_addr(hleaf_NW__a_cfg_addr[11:0]),
    .cfg_data(hleaf_NW__a_cfg_data[255:0]),
    .desc_v(hleaf_NW__a_desc_v[0:0]),
    .desc_base(hleaf_NW__a_desc_base[11:0]),
    .desc_limit(hleaf_NW__a_desc_limit[12:0]),
    .desc_loops(hleaf_NW__a_desc_loops[15:0]),
    .launch_v(hleaf_NW__a_launch_v[0:0]),
    .tgt_active({svg_NW3__program_active[0:0], svg_NW3__running[0:0]}),
    .tgt_fault(svg_NW3__fault[0:0]),
    .a_we(cp_svg_NW3__a_we[0:0]),
    .a_addr(cp_svg_NW3__a_addr[10:0]),
    .a_data(cp_svg_NW3__a_data[255:0]),
    .b_we(cp_svg_NW3__b_we[0:0]),
    .b_addr(cp_svg_NW3__b_addr[7:0]),
    .b_data(cp_svg_NW3__b_data[255:0]),
    .run_v(cp_svg_NW3__run_v[0:0]),
    .run_base(cp_svg_NW3__run_base[7:0]),
    .run_count(cp_svg_NW3__run_count[8:0]),
    .run_arg(cp_svg_NW3__run_arg[7:0]),
    .configured(cp_svg_NW3__configured[0:0]),
    .fault(cp_svg_NW3__fault[0:0]),
    .active(cp_svg_NW3__active[0:0])
  );
  ot_static_run_target #(.AWA(11), .AWB(8), .RBW(8), .RCW(9), .NA(2), .NF(1), .TGT_PIN(1), .RSYNC(1)) cp_svg_NW4 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .tgt(8'b01010100),
    .cfg_v(hleaf_NE__b_cfg_v[0:0]),
    .cfg_target(hleaf_NE__b_cfg_target[7:0]),
    .cfg_addr(hleaf_NE__b_cfg_addr[11:0]),
    .cfg_data(hleaf_NE__b_cfg_data[255:0]),
    .desc_v(hleaf_NE__b_desc_v[0:0]),
    .desc_base(hleaf_NE__b_desc_base[11:0]),
    .desc_limit(hleaf_NE__b_desc_limit[12:0]),
    .desc_loops(hleaf_NE__b_desc_loops[15:0]),
    .launch_v(hleaf_NE__b_launch_v[0:0]),
    .tgt_active({svg_NW4__program_active[0:0], svg_NW4__running[0:0]}),
    .tgt_fault(svg_NW4__fault[0:0]),
    .a_we(cp_svg_NW4__a_we[0:0]),
    .a_addr(cp_svg_NW4__a_addr[10:0]),
    .a_data(cp_svg_NW4__a_data[255:0]),
    .b_we(cp_svg_NW4__b_we[0:0]),
    .b_addr(cp_svg_NW4__b_addr[7:0]),
    .b_data(cp_svg_NW4__b_data[255:0]),
    .run_v(cp_svg_NW4__run_v[0:0]),
    .run_base(cp_svg_NW4__run_base[7:0]),
    .run_count(cp_svg_NW4__run_count[8:0]),
    .run_arg(cp_svg_NW4__run_arg[7:0]),
    .configured(cp_svg_NW4__configured[0:0]),
    .fault(cp_svg_NW4__fault[0:0]),
    .active(cp_svg_NW4__active[0:0])
  );
  ot_static_run_target #(.AWA(11), .AWB(8), .RBW(8), .RCW(9), .NA(2), .NF(1), .TGT_PIN(1), .RSYNC(1)) cp_svg_NW5 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .tgt(8'b01010101),
    .cfg_v(hleaf_NE__a_cfg_v[0:0]),
    .cfg_target(hleaf_NE__a_cfg_target[7:0]),
    .cfg_addr(hleaf_NE__a_cfg_addr[11:0]),
    .cfg_data(hleaf_NE__a_cfg_data[255:0]),
    .desc_v(hleaf_NE__a_desc_v[0:0]),
    .desc_base(hleaf_NE__a_desc_base[11:0]),
    .desc_limit(hleaf_NE__a_desc_limit[12:0]),
    .desc_loops(hleaf_NE__a_desc_loops[15:0]),
    .launch_v(hleaf_NE__a_launch_v[0:0]),
    .tgt_active({svg_NW5__program_active[0:0], svg_NW5__running[0:0]}),
    .tgt_fault(svg_NW5__fault[0:0]),
    .a_we(cp_svg_NW5__a_we[0:0]),
    .a_addr(cp_svg_NW5__a_addr[10:0]),
    .a_data(cp_svg_NW5__a_data[255:0]),
    .b_we(cp_svg_NW5__b_we[0:0]),
    .b_addr(cp_svg_NW5__b_addr[7:0]),
    .b_data(cp_svg_NW5__b_data[255:0]),
    .run_v(cp_svg_NW5__run_v[0:0]),
    .run_base(cp_svg_NW5__run_base[7:0]),
    .run_count(cp_svg_NW5__run_count[8:0]),
    .run_arg(cp_svg_NW5__run_arg[7:0]),
    .configured(cp_svg_NW5__configured[0:0]),
    .fault(cp_svg_NW5__fault[0:0]),
    .active(cp_svg_NW5__active[0:0])
  );
  ot_static_run_target #(.AWA(11), .AWB(8), .RBW(8), .RCW(9), .NA(2), .NF(1), .TGT_PIN(1), .RSYNC(1)) cp_svg_NW6 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .tgt(8'b01010110),
    .cfg_v(hleaf_NE__b_cfg_v[0:0]),
    .cfg_target(hleaf_NE__b_cfg_target[7:0]),
    .cfg_addr(hleaf_NE__b_cfg_addr[11:0]),
    .cfg_data(hleaf_NE__b_cfg_data[255:0]),
    .desc_v(hleaf_NE__b_desc_v[0:0]),
    .desc_base(hleaf_NE__b_desc_base[11:0]),
    .desc_limit(hleaf_NE__b_desc_limit[12:0]),
    .desc_loops(hleaf_NE__b_desc_loops[15:0]),
    .launch_v(hleaf_NE__b_launch_v[0:0]),
    .tgt_active({svg_NW6__program_active[0:0], svg_NW6__running[0:0]}),
    .tgt_fault(svg_NW6__fault[0:0]),
    .a_we(cp_svg_NW6__a_we[0:0]),
    .a_addr(cp_svg_NW6__a_addr[10:0]),
    .a_data(cp_svg_NW6__a_data[255:0]),
    .b_we(cp_svg_NW6__b_we[0:0]),
    .b_addr(cp_svg_NW6__b_addr[7:0]),
    .b_data(cp_svg_NW6__b_data[255:0]),
    .run_v(cp_svg_NW6__run_v[0:0]),
    .run_base(cp_svg_NW6__run_base[7:0]),
    .run_count(cp_svg_NW6__run_count[8:0]),
    .run_arg(cp_svg_NW6__run_arg[7:0]),
    .configured(cp_svg_NW6__configured[0:0]),
    .fault(cp_svg_NW6__fault[0:0]),
    .active(cp_svg_NW6__active[0:0])
  );
  ot_static_run_target #(.AWA(11), .AWB(8), .RBW(8), .RCW(9), .NA(2), .NF(1), .TGT_PIN(1), .RSYNC(1)) cp_svg_NW7 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .tgt(8'b01010111),
    .cfg_v(hleaf_NE__a_cfg_v[0:0]),
    .cfg_target(hleaf_NE__a_cfg_target[7:0]),
    .cfg_addr(hleaf_NE__a_cfg_addr[11:0]),
    .cfg_data(hleaf_NE__a_cfg_data[255:0]),
    .desc_v(hleaf_NE__a_desc_v[0:0]),
    .desc_base(hleaf_NE__a_desc_base[11:0]),
    .desc_limit(hleaf_NE__a_desc_limit[12:0]),
    .desc_loops(hleaf_NE__a_desc_loops[15:0]),
    .launch_v(hleaf_NE__a_launch_v[0:0]),
    .tgt_active({svg_NW7__program_active[0:0], svg_NW7__running[0:0]}),
    .tgt_fault(svg_NW7__fault[0:0]),
    .a_we(cp_svg_NW7__a_we[0:0]),
    .a_addr(cp_svg_NW7__a_addr[10:0]),
    .a_data(cp_svg_NW7__a_data[255:0]),
    .b_we(cp_svg_NW7__b_we[0:0]),
    .b_addr(cp_svg_NW7__b_addr[7:0]),
    .b_data(cp_svg_NW7__b_data[255:0]),
    .run_v(cp_svg_NW7__run_v[0:0]),
    .run_base(cp_svg_NW7__run_base[7:0]),
    .run_count(cp_svg_NW7__run_count[8:0]),
    .run_arg(cp_svg_NW7__run_arg[7:0]),
    .configured(cp_svg_NW7__configured[0:0]),
    .fault(cp_svg_NW7__fault[0:0]),
    .active(cp_svg_NW7__active[0:0])
  );
  ot_hbm_svc_pc_ctrl_leaf_cfg_h9b #(.OREG(1), .KREG(1), .KRREG(1), .RREG(1), .WPAY(1), .QREG(1)) ctl_NW_p00 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(refcfg_NW__pc_rst_n[0:0]),
    .pc_id(5'b00000),
    .refresh_reload(refcfg_NW__refresh_reload[7:0]),
    .k_v(vmks_NW0__c_k_v[0:0]),
    .k_rdy(ctl_NW_p00__k_rdy[0:0]),
    .k_we(vmks_NW0__c_k_we[0:0]),
    .k_addr(vmks_NW0__c_k_addr[29:0]),
    .k_len(vmks_NW0__c_k_len[3:0]),
    .k_tag(vmks_NW0__c_k_tag[16:0]),
    .k_wdata(vmks_NW0__c_k_wdata[255:0]),
    .k_wstrb(vmks_NW0__c_k_wstrb[31:0]),
    .kr_v(ctl_NW_p00__kr_v[0:0]),
    .kr_rdy(vmks_NW0__c_kr_rdy[0:0]),
    .kr_tag(ctl_NW_p00__kr_tag[16:0]),
    .kr_beat(ctl_NW_p00__kr_beat[3:0]),
    .kr_data(ctl_NW_p00__kr_data[255:0]),
    .k_wr_done(ctl_NW_p00__k_wr_done[0:0]),
    .row_v(ctl_NW_p00__row_v[0:0]),
    .row_op(ctl_NW_p00__row_op[2:0]),
    .row_bank(ctl_NW_p00__row_bank[4:0]),
    .row_row(ctl_NW_p00__row_row[18:0]),
    .col_v(ctl_NW_p00__col_v[0:0]),
    .col_we(ctl_NW_p00__col_we[0:0]),
    .col_bank(ctl_NW_p00__col_bank[4:0]),
    .col_col(ctl_NW_p00__col_col[4:0]),
    .col_data(ctl_NW_p00__col_data[255:0]),
    .col_strb(ctl_NW_p00__col_strb[31:0]),
    .dram_rvalid(phy_NW__dram_rvalid[0:0]),
    .dram_rdata(phy_NW__dram_rdata[255:0]),
    .pc_fault(ctl_NW_p00__pc_fault[0:0]),
    .owner_fault_split(ctl_NW_p00__owner_fault_split[5:0])
  );
  ot_hbm_svc_pc_ctrl_leaf_cfg_h9b #(.OREG(1), .KREG(1), .KRREG(1), .RREG(1), .WPAY(1), .QREG(1)) ctl_NW_p01 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(refcfg_NW__pc_rst_n[0:0]),
    .pc_id(5'b00001),
    .refresh_reload(refcfg_NW__refresh_reload[15:8]),
    .k_v(vmks_NW0__c_k_v[1:1]),
    .k_rdy(ctl_NW_p01__k_rdy[0:0]),
    .k_we(vmks_NW0__c_k_we[1:1]),
    .k_addr(vmks_NW0__c_k_addr[59:30]),
    .k_len(vmks_NW0__c_k_len[7:4]),
    .k_tag(vmks_NW0__c_k_tag[33:17]),
    .k_wdata(vmks_NW0__c_k_wdata[511:256]),
    .k_wstrb(vmks_NW0__c_k_wstrb[63:32]),
    .kr_v(ctl_NW_p01__kr_v[0:0]),
    .kr_rdy(vmks_NW0__c_kr_rdy[1:1]),
    .kr_tag(ctl_NW_p01__kr_tag[16:0]),
    .kr_beat(ctl_NW_p01__kr_beat[3:0]),
    .kr_data(ctl_NW_p01__kr_data[255:0]),
    .k_wr_done(ctl_NW_p01__k_wr_done[0:0]),
    .row_v(ctl_NW_p01__row_v[0:0]),
    .row_op(ctl_NW_p01__row_op[2:0]),
    .row_bank(ctl_NW_p01__row_bank[4:0]),
    .row_row(ctl_NW_p01__row_row[18:0]),
    .col_v(ctl_NW_p01__col_v[0:0]),
    .col_we(ctl_NW_p01__col_we[0:0]),
    .col_bank(ctl_NW_p01__col_bank[4:0]),
    .col_col(ctl_NW_p01__col_col[4:0]),
    .col_data(ctl_NW_p01__col_data[255:0]),
    .col_strb(ctl_NW_p01__col_strb[31:0]),
    .dram_rvalid(phy_NW__dram_rvalid[1:1]),
    .dram_rdata(phy_NW__dram_rdata[511:256]),
    .pc_fault(ctl_NW_p01__pc_fault[0:0]),
    .owner_fault_split(ctl_NW_p01__owner_fault_split[5:0])
  );
  ot_hbm_svc_pc_ctrl_leaf_cfg_h9b #(.OREG(1), .KREG(1), .KRREG(1), .RREG(1), .WPAY(1), .QREG(1)) ctl_NW_p02 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(refcfg_NW__pc_rst_n[0:0]),
    .pc_id(5'b00010),
    .refresh_reload(refcfg_NW__refresh_reload[23:16]),
    .k_v(vmks_NW0__c_k_v[2:2]),
    .k_rdy(ctl_NW_p02__k_rdy[0:0]),
    .k_we(vmks_NW0__c_k_we[2:2]),
    .k_addr(vmks_NW0__c_k_addr[89:60]),
    .k_len(vmks_NW0__c_k_len[11:8]),
    .k_tag(vmks_NW0__c_k_tag[50:34]),
    .k_wdata(vmks_NW0__c_k_wdata[767:512]),
    .k_wstrb(vmks_NW0__c_k_wstrb[95:64]),
    .kr_v(ctl_NW_p02__kr_v[0:0]),
    .kr_rdy(vmks_NW0__c_kr_rdy[2:2]),
    .kr_tag(ctl_NW_p02__kr_tag[16:0]),
    .kr_beat(ctl_NW_p02__kr_beat[3:0]),
    .kr_data(ctl_NW_p02__kr_data[255:0]),
    .k_wr_done(ctl_NW_p02__k_wr_done[0:0]),
    .row_v(ctl_NW_p02__row_v[0:0]),
    .row_op(ctl_NW_p02__row_op[2:0]),
    .row_bank(ctl_NW_p02__row_bank[4:0]),
    .row_row(ctl_NW_p02__row_row[18:0]),
    .col_v(ctl_NW_p02__col_v[0:0]),
    .col_we(ctl_NW_p02__col_we[0:0]),
    .col_bank(ctl_NW_p02__col_bank[4:0]),
    .col_col(ctl_NW_p02__col_col[4:0]),
    .col_data(ctl_NW_p02__col_data[255:0]),
    .col_strb(ctl_NW_p02__col_strb[31:0]),
    .dram_rvalid(phy_NW__dram_rvalid[2:2]),
    .dram_rdata(phy_NW__dram_rdata[767:512]),
    .pc_fault(ctl_NW_p02__pc_fault[0:0]),
    .owner_fault_split(ctl_NW_p02__owner_fault_split[5:0])
  );
  ot_hbm_svc_pc_ctrl_leaf_cfg_h9b #(.OREG(1), .KREG(1), .KRREG(1), .RREG(1), .WPAY(1), .QREG(1)) ctl_NW_p03 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(refcfg_NW__pc_rst_n[0:0]),
    .pc_id(5'b00011),
    .refresh_reload(refcfg_NW__refresh_reload[31:24]),
    .k_v(vmks_NW0__c_k_v[3:3]),
    .k_rdy(ctl_NW_p03__k_rdy[0:0]),
    .k_we(vmks_NW0__c_k_we[3:3]),
    .k_addr(vmks_NW0__c_k_addr[119:90]),
    .k_len(vmks_NW0__c_k_len[15:12]),
    .k_tag(vmks_NW0__c_k_tag[67:51]),
    .k_wdata(vmks_NW0__c_k_wdata[1023:768]),
    .k_wstrb(vmks_NW0__c_k_wstrb[127:96]),
    .kr_v(ctl_NW_p03__kr_v[0:0]),
    .kr_rdy(vmks_NW0__c_kr_rdy[3:3]),
    .kr_tag(ctl_NW_p03__kr_tag[16:0]),
    .kr_beat(ctl_NW_p03__kr_beat[3:0]),
    .kr_data(ctl_NW_p03__kr_data[255:0]),
    .k_wr_done(ctl_NW_p03__k_wr_done[0:0]),
    .row_v(ctl_NW_p03__row_v[0:0]),
    .row_op(ctl_NW_p03__row_op[2:0]),
    .row_bank(ctl_NW_p03__row_bank[4:0]),
    .row_row(ctl_NW_p03__row_row[18:0]),
    .col_v(ctl_NW_p03__col_v[0:0]),
    .col_we(ctl_NW_p03__col_we[0:0]),
    .col_bank(ctl_NW_p03__col_bank[4:0]),
    .col_col(ctl_NW_p03__col_col[4:0]),
    .col_data(ctl_NW_p03__col_data[255:0]),
    .col_strb(ctl_NW_p03__col_strb[31:0]),
    .dram_rvalid(phy_NW__dram_rvalid[3:3]),
    .dram_rdata(phy_NW__dram_rdata[1023:768]),
    .pc_fault(ctl_NW_p03__pc_fault[0:0]),
    .owner_fault_split(ctl_NW_p03__owner_fault_split[5:0])
  );
  ot_hbm_svc_pc_ctrl_leaf_cfg_h9b #(.OREG(1), .KREG(1), .KRREG(1), .RREG(1), .WPAY(1), .QREG(1)) ctl_NW_p04 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(refcfg_NW__pc_rst_n[0:0]),
    .pc_id(5'b00100),
    .refresh_reload(refcfg_NW__refresh_reload[39:32]),
    .k_v(vmks_NW1__c_k_v[0:0]),
    .k_rdy(ctl_NW_p04__k_rdy[0:0]),
    .k_we(vmks_NW1__c_k_we[0:0]),
    .k_addr(vmks_NW1__c_k_addr[29:0]),
    .k_len(vmks_NW1__c_k_len[3:0]),
    .k_tag(vmks_NW1__c_k_tag[16:0]),
    .k_wdata(vmks_NW1__c_k_wdata[255:0]),
    .k_wstrb(vmks_NW1__c_k_wstrb[31:0]),
    .kr_v(ctl_NW_p04__kr_v[0:0]),
    .kr_rdy(vmks_NW1__c_kr_rdy[0:0]),
    .kr_tag(ctl_NW_p04__kr_tag[16:0]),
    .kr_beat(ctl_NW_p04__kr_beat[3:0]),
    .kr_data(ctl_NW_p04__kr_data[255:0]),
    .k_wr_done(ctl_NW_p04__k_wr_done[0:0]),
    .row_v(ctl_NW_p04__row_v[0:0]),
    .row_op(ctl_NW_p04__row_op[2:0]),
    .row_bank(ctl_NW_p04__row_bank[4:0]),
    .row_row(ctl_NW_p04__row_row[18:0]),
    .col_v(ctl_NW_p04__col_v[0:0]),
    .col_we(ctl_NW_p04__col_we[0:0]),
    .col_bank(ctl_NW_p04__col_bank[4:0]),
    .col_col(ctl_NW_p04__col_col[4:0]),
    .col_data(ctl_NW_p04__col_data[255:0]),
    .col_strb(ctl_NW_p04__col_strb[31:0]),
    .dram_rvalid(phy_NW__dram_rvalid[4:4]),
    .dram_rdata(phy_NW__dram_rdata[1279:1024]),
    .pc_fault(ctl_NW_p04__pc_fault[0:0]),
    .owner_fault_split(ctl_NW_p04__owner_fault_split[5:0])
  );
  ot_hbm_svc_pc_ctrl_leaf_cfg_h9b #(.OREG(1), .KREG(1), .KRREG(1), .RREG(1), .WPAY(1), .QREG(1)) ctl_NW_p05 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(refcfg_NW__pc_rst_n[0:0]),
    .pc_id(5'b00101),
    .refresh_reload(refcfg_NW__refresh_reload[47:40]),
    .k_v(vmks_NW1__c_k_v[1:1]),
    .k_rdy(ctl_NW_p05__k_rdy[0:0]),
    .k_we(vmks_NW1__c_k_we[1:1]),
    .k_addr(vmks_NW1__c_k_addr[59:30]),
    .k_len(vmks_NW1__c_k_len[7:4]),
    .k_tag(vmks_NW1__c_k_tag[33:17]),
    .k_wdata(vmks_NW1__c_k_wdata[511:256]),
    .k_wstrb(vmks_NW1__c_k_wstrb[63:32]),
    .kr_v(ctl_NW_p05__kr_v[0:0]),
    .kr_rdy(vmks_NW1__c_kr_rdy[1:1]),
    .kr_tag(ctl_NW_p05__kr_tag[16:0]),
    .kr_beat(ctl_NW_p05__kr_beat[3:0]),
    .kr_data(ctl_NW_p05__kr_data[255:0]),
    .k_wr_done(ctl_NW_p05__k_wr_done[0:0]),
    .row_v(ctl_NW_p05__row_v[0:0]),
    .row_op(ctl_NW_p05__row_op[2:0]),
    .row_bank(ctl_NW_p05__row_bank[4:0]),
    .row_row(ctl_NW_p05__row_row[18:0]),
    .col_v(ctl_NW_p05__col_v[0:0]),
    .col_we(ctl_NW_p05__col_we[0:0]),
    .col_bank(ctl_NW_p05__col_bank[4:0]),
    .col_col(ctl_NW_p05__col_col[4:0]),
    .col_data(ctl_NW_p05__col_data[255:0]),
    .col_strb(ctl_NW_p05__col_strb[31:0]),
    .dram_rvalid(phy_NW__dram_rvalid[5:5]),
    .dram_rdata(phy_NW__dram_rdata[1535:1280]),
    .pc_fault(ctl_NW_p05__pc_fault[0:0]),
    .owner_fault_split(ctl_NW_p05__owner_fault_split[5:0])
  );
  ot_hbm_svc_pc_ctrl_leaf_cfg_h9b #(.OREG(1), .KREG(1), .KRREG(1), .RREG(1), .WPAY(1), .QREG(1)) ctl_NW_p06 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(refcfg_NW__pc_rst_n[0:0]),
    .pc_id(5'b00110),
    .refresh_reload(refcfg_NW__refresh_reload[55:48]),
    .k_v(vmks_NW1__c_k_v[2:2]),
    .k_rdy(ctl_NW_p06__k_rdy[0:0]),
    .k_we(vmks_NW1__c_k_we[2:2]),
    .k_addr(vmks_NW1__c_k_addr[89:60]),
    .k_len(vmks_NW1__c_k_len[11:8]),
    .k_tag(vmks_NW1__c_k_tag[50:34]),
    .k_wdata(vmks_NW1__c_k_wdata[767:512]),
    .k_wstrb(vmks_NW1__c_k_wstrb[95:64]),
    .kr_v(ctl_NW_p06__kr_v[0:0]),
    .kr_rdy(vmks_NW1__c_kr_rdy[2:2]),
    .kr_tag(ctl_NW_p06__kr_tag[16:0]),
    .kr_beat(ctl_NW_p06__kr_beat[3:0]),
    .kr_data(ctl_NW_p06__kr_data[255:0]),
    .k_wr_done(ctl_NW_p06__k_wr_done[0:0]),
    .row_v(ctl_NW_p06__row_v[0:0]),
    .row_op(ctl_NW_p06__row_op[2:0]),
    .row_bank(ctl_NW_p06__row_bank[4:0]),
    .row_row(ctl_NW_p06__row_row[18:0]),
    .col_v(ctl_NW_p06__col_v[0:0]),
    .col_we(ctl_NW_p06__col_we[0:0]),
    .col_bank(ctl_NW_p06__col_bank[4:0]),
    .col_col(ctl_NW_p06__col_col[4:0]),
    .col_data(ctl_NW_p06__col_data[255:0]),
    .col_strb(ctl_NW_p06__col_strb[31:0]),
    .dram_rvalid(phy_NW__dram_rvalid[6:6]),
    .dram_rdata(phy_NW__dram_rdata[1791:1536]),
    .pc_fault(ctl_NW_p06__pc_fault[0:0]),
    .owner_fault_split(ctl_NW_p06__owner_fault_split[5:0])
  );
  ot_hbm_svc_pc_ctrl_leaf_cfg_h9b #(.OREG(1), .KREG(1), .KRREG(1), .RREG(1), .WPAY(1), .QREG(1)) ctl_NW_p07 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(refcfg_NW__pc_rst_n[0:0]),
    .pc_id(5'b00111),
    .refresh_reload(refcfg_NW__refresh_reload[63:56]),
    .k_v(vmks_NW1__c_k_v[3:3]),
    .k_rdy(ctl_NW_p07__k_rdy[0:0]),
    .k_we(vmks_NW1__c_k_we[3:3]),
    .k_addr(vmks_NW1__c_k_addr[119:90]),
    .k_len(vmks_NW1__c_k_len[15:12]),
    .k_tag(vmks_NW1__c_k_tag[67:51]),
    .k_wdata(vmks_NW1__c_k_wdata[1023:768]),
    .k_wstrb(vmks_NW1__c_k_wstrb[127:96]),
    .kr_v(ctl_NW_p07__kr_v[0:0]),
    .kr_rdy(vmks_NW1__c_kr_rdy[3:3]),
    .kr_tag(ctl_NW_p07__kr_tag[16:0]),
    .kr_beat(ctl_NW_p07__kr_beat[3:0]),
    .kr_data(ctl_NW_p07__kr_data[255:0]),
    .k_wr_done(ctl_NW_p07__k_wr_done[0:0]),
    .row_v(ctl_NW_p07__row_v[0:0]),
    .row_op(ctl_NW_p07__row_op[2:0]),
    .row_bank(ctl_NW_p07__row_bank[4:0]),
    .row_row(ctl_NW_p07__row_row[18:0]),
    .col_v(ctl_NW_p07__col_v[0:0]),
    .col_we(ctl_NW_p07__col_we[0:0]),
    .col_bank(ctl_NW_p07__col_bank[4:0]),
    .col_col(ctl_NW_p07__col_col[4:0]),
    .col_data(ctl_NW_p07__col_data[255:0]),
    .col_strb(ctl_NW_p07__col_strb[31:0]),
    .dram_rvalid(phy_NW__dram_rvalid[7:7]),
    .dram_rdata(phy_NW__dram_rdata[2047:1792]),
    .pc_fault(ctl_NW_p07__pc_fault[0:0]),
    .owner_fault_split(ctl_NW_p07__owner_fault_split[5:0])
  );
  ot_hbm_svc_pc_ctrl_leaf_cfg_h9b #(.OREG(1), .KREG(1), .KRREG(1), .RREG(1), .WPAY(1), .QREG(1)) ctl_NW_p08 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(refcfg_NW__pc_rst_n[0:0]),
    .pc_id(5'b01000),
    .refresh_reload(refcfg_NW__refresh_reload[71:64]),
    .k_v(vmks_NW2__c_k_v[0:0]),
    .k_rdy(ctl_NW_p08__k_rdy[0:0]),
    .k_we(vmks_NW2__c_k_we[0:0]),
    .k_addr(vmks_NW2__c_k_addr[29:0]),
    .k_len(vmks_NW2__c_k_len[3:0]),
    .k_tag(vmks_NW2__c_k_tag[16:0]),
    .k_wdata(vmks_NW2__c_k_wdata[255:0]),
    .k_wstrb(vmks_NW2__c_k_wstrb[31:0]),
    .kr_v(ctl_NW_p08__kr_v[0:0]),
    .kr_rdy(vmks_NW2__c_kr_rdy[0:0]),
    .kr_tag(ctl_NW_p08__kr_tag[16:0]),
    .kr_beat(ctl_NW_p08__kr_beat[3:0]),
    .kr_data(ctl_NW_p08__kr_data[255:0]),
    .k_wr_done(ctl_NW_p08__k_wr_done[0:0]),
    .row_v(ctl_NW_p08__row_v[0:0]),
    .row_op(ctl_NW_p08__row_op[2:0]),
    .row_bank(ctl_NW_p08__row_bank[4:0]),
    .row_row(ctl_NW_p08__row_row[18:0]),
    .col_v(ctl_NW_p08__col_v[0:0]),
    .col_we(ctl_NW_p08__col_we[0:0]),
    .col_bank(ctl_NW_p08__col_bank[4:0]),
    .col_col(ctl_NW_p08__col_col[4:0]),
    .col_data(ctl_NW_p08__col_data[255:0]),
    .col_strb(ctl_NW_p08__col_strb[31:0]),
    .dram_rvalid(phy_NW__dram_rvalid[8:8]),
    .dram_rdata(phy_NW__dram_rdata[2303:2048]),
    .pc_fault(ctl_NW_p08__pc_fault[0:0]),
    .owner_fault_split(ctl_NW_p08__owner_fault_split[5:0])
  );
  ot_hbm_svc_pc_ctrl_leaf_cfg_h9b #(.OREG(1), .KREG(1), .KRREG(1), .RREG(1), .WPAY(1), .QREG(1)) ctl_NW_p09 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(refcfg_NW__pc_rst_n[0:0]),
    .pc_id(5'b01001),
    .refresh_reload(refcfg_NW__refresh_reload[79:72]),
    .k_v(vmks_NW2__c_k_v[1:1]),
    .k_rdy(ctl_NW_p09__k_rdy[0:0]),
    .k_we(vmks_NW2__c_k_we[1:1]),
    .k_addr(vmks_NW2__c_k_addr[59:30]),
    .k_len(vmks_NW2__c_k_len[7:4]),
    .k_tag(vmks_NW2__c_k_tag[33:17]),
    .k_wdata(vmks_NW2__c_k_wdata[511:256]),
    .k_wstrb(vmks_NW2__c_k_wstrb[63:32]),
    .kr_v(ctl_NW_p09__kr_v[0:0]),
    .kr_rdy(vmks_NW2__c_kr_rdy[1:1]),
    .kr_tag(ctl_NW_p09__kr_tag[16:0]),
    .kr_beat(ctl_NW_p09__kr_beat[3:0]),
    .kr_data(ctl_NW_p09__kr_data[255:0]),
    .k_wr_done(ctl_NW_p09__k_wr_done[0:0]),
    .row_v(ctl_NW_p09__row_v[0:0]),
    .row_op(ctl_NW_p09__row_op[2:0]),
    .row_bank(ctl_NW_p09__row_bank[4:0]),
    .row_row(ctl_NW_p09__row_row[18:0]),
    .col_v(ctl_NW_p09__col_v[0:0]),
    .col_we(ctl_NW_p09__col_we[0:0]),
    .col_bank(ctl_NW_p09__col_bank[4:0]),
    .col_col(ctl_NW_p09__col_col[4:0]),
    .col_data(ctl_NW_p09__col_data[255:0]),
    .col_strb(ctl_NW_p09__col_strb[31:0]),
    .dram_rvalid(phy_NW__dram_rvalid[9:9]),
    .dram_rdata(phy_NW__dram_rdata[2559:2304]),
    .pc_fault(ctl_NW_p09__pc_fault[0:0]),
    .owner_fault_split(ctl_NW_p09__owner_fault_split[5:0])
  );
  ot_hbm_svc_pc_ctrl_leaf_cfg_h9b #(.OREG(1), .KREG(1), .KRREG(1), .RREG(1), .WPAY(1), .QREG(1)) ctl_NW_p10 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(refcfg_NW__pc_rst_n[0:0]),
    .pc_id(5'b01010),
    .refresh_reload(refcfg_NW__refresh_reload[87:80]),
    .k_v(vmks_NW2__c_k_v[2:2]),
    .k_rdy(ctl_NW_p10__k_rdy[0:0]),
    .k_we(vmks_NW2__c_k_we[2:2]),
    .k_addr(vmks_NW2__c_k_addr[89:60]),
    .k_len(vmks_NW2__c_k_len[11:8]),
    .k_tag(vmks_NW2__c_k_tag[50:34]),
    .k_wdata(vmks_NW2__c_k_wdata[767:512]),
    .k_wstrb(vmks_NW2__c_k_wstrb[95:64]),
    .kr_v(ctl_NW_p10__kr_v[0:0]),
    .kr_rdy(vmks_NW2__c_kr_rdy[2:2]),
    .kr_tag(ctl_NW_p10__kr_tag[16:0]),
    .kr_beat(ctl_NW_p10__kr_beat[3:0]),
    .kr_data(ctl_NW_p10__kr_data[255:0]),
    .k_wr_done(ctl_NW_p10__k_wr_done[0:0]),
    .row_v(ctl_NW_p10__row_v[0:0]),
    .row_op(ctl_NW_p10__row_op[2:0]),
    .row_bank(ctl_NW_p10__row_bank[4:0]),
    .row_row(ctl_NW_p10__row_row[18:0]),
    .col_v(ctl_NW_p10__col_v[0:0]),
    .col_we(ctl_NW_p10__col_we[0:0]),
    .col_bank(ctl_NW_p10__col_bank[4:0]),
    .col_col(ctl_NW_p10__col_col[4:0]),
    .col_data(ctl_NW_p10__col_data[255:0]),
    .col_strb(ctl_NW_p10__col_strb[31:0]),
    .dram_rvalid(phy_NW__dram_rvalid[10:10]),
    .dram_rdata(phy_NW__dram_rdata[2815:2560]),
    .pc_fault(ctl_NW_p10__pc_fault[0:0]),
    .owner_fault_split(ctl_NW_p10__owner_fault_split[5:0])
  );
  ot_hbm_svc_pc_ctrl_leaf_cfg_h9b #(.OREG(1), .KREG(1), .KRREG(1), .RREG(1), .WPAY(1), .QREG(1)) ctl_NW_p11 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(refcfg_NW__pc_rst_n[0:0]),
    .pc_id(5'b01011),
    .refresh_reload(refcfg_NW__refresh_reload[95:88]),
    .k_v(vmks_NW2__c_k_v[3:3]),
    .k_rdy(ctl_NW_p11__k_rdy[0:0]),
    .k_we(vmks_NW2__c_k_we[3:3]),
    .k_addr(vmks_NW2__c_k_addr[119:90]),
    .k_len(vmks_NW2__c_k_len[15:12]),
    .k_tag(vmks_NW2__c_k_tag[67:51]),
    .k_wdata(vmks_NW2__c_k_wdata[1023:768]),
    .k_wstrb(vmks_NW2__c_k_wstrb[127:96]),
    .kr_v(ctl_NW_p11__kr_v[0:0]),
    .kr_rdy(vmks_NW2__c_kr_rdy[3:3]),
    .kr_tag(ctl_NW_p11__kr_tag[16:0]),
    .kr_beat(ctl_NW_p11__kr_beat[3:0]),
    .kr_data(ctl_NW_p11__kr_data[255:0]),
    .k_wr_done(ctl_NW_p11__k_wr_done[0:0]),
    .row_v(ctl_NW_p11__row_v[0:0]),
    .row_op(ctl_NW_p11__row_op[2:0]),
    .row_bank(ctl_NW_p11__row_bank[4:0]),
    .row_row(ctl_NW_p11__row_row[18:0]),
    .col_v(ctl_NW_p11__col_v[0:0]),
    .col_we(ctl_NW_p11__col_we[0:0]),
    .col_bank(ctl_NW_p11__col_bank[4:0]),
    .col_col(ctl_NW_p11__col_col[4:0]),
    .col_data(ctl_NW_p11__col_data[255:0]),
    .col_strb(ctl_NW_p11__col_strb[31:0]),
    .dram_rvalid(phy_NW__dram_rvalid[11:11]),
    .dram_rdata(phy_NW__dram_rdata[3071:2816]),
    .pc_fault(ctl_NW_p11__pc_fault[0:0]),
    .owner_fault_split(ctl_NW_p11__owner_fault_split[5:0])
  );
  ot_hbm_svc_pc_ctrl_leaf_cfg_h9b #(.OREG(1), .KREG(1), .KRREG(1), .RREG(1), .WPAY(1), .QREG(1)) ctl_NW_p12 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(refcfg_NW__pc_rst_n[0:0]),
    .pc_id(5'b01100),
    .refresh_reload(refcfg_NW__refresh_reload[103:96]),
    .k_v(vmks_NW3__c_k_v[0:0]),
    .k_rdy(ctl_NW_p12__k_rdy[0:0]),
    .k_we(vmks_NW3__c_k_we[0:0]),
    .k_addr(vmks_NW3__c_k_addr[29:0]),
    .k_len(vmks_NW3__c_k_len[3:0]),
    .k_tag(vmks_NW3__c_k_tag[16:0]),
    .k_wdata(vmks_NW3__c_k_wdata[255:0]),
    .k_wstrb(vmks_NW3__c_k_wstrb[31:0]),
    .kr_v(ctl_NW_p12__kr_v[0:0]),
    .kr_rdy(vmks_NW3__c_kr_rdy[0:0]),
    .kr_tag(ctl_NW_p12__kr_tag[16:0]),
    .kr_beat(ctl_NW_p12__kr_beat[3:0]),
    .kr_data(ctl_NW_p12__kr_data[255:0]),
    .k_wr_done(ctl_NW_p12__k_wr_done[0:0]),
    .row_v(ctl_NW_p12__row_v[0:0]),
    .row_op(ctl_NW_p12__row_op[2:0]),
    .row_bank(ctl_NW_p12__row_bank[4:0]),
    .row_row(ctl_NW_p12__row_row[18:0]),
    .col_v(ctl_NW_p12__col_v[0:0]),
    .col_we(ctl_NW_p12__col_we[0:0]),
    .col_bank(ctl_NW_p12__col_bank[4:0]),
    .col_col(ctl_NW_p12__col_col[4:0]),
    .col_data(ctl_NW_p12__col_data[255:0]),
    .col_strb(ctl_NW_p12__col_strb[31:0]),
    .dram_rvalid(phy_NW__dram_rvalid[12:12]),
    .dram_rdata(phy_NW__dram_rdata[3327:3072]),
    .pc_fault(ctl_NW_p12__pc_fault[0:0]),
    .owner_fault_split(ctl_NW_p12__owner_fault_split[5:0])
  );
  ot_hbm_svc_pc_ctrl_leaf_cfg_h9b #(.OREG(1), .KREG(1), .KRREG(1), .RREG(1), .WPAY(1), .QREG(1)) ctl_NW_p13 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(refcfg_NW__pc_rst_n[0:0]),
    .pc_id(5'b01101),
    .refresh_reload(refcfg_NW__refresh_reload[111:104]),
    .k_v(vmks_NW3__c_k_v[1:1]),
    .k_rdy(ctl_NW_p13__k_rdy[0:0]),
    .k_we(vmks_NW3__c_k_we[1:1]),
    .k_addr(vmks_NW3__c_k_addr[59:30]),
    .k_len(vmks_NW3__c_k_len[7:4]),
    .k_tag(vmks_NW3__c_k_tag[33:17]),
    .k_wdata(vmks_NW3__c_k_wdata[511:256]),
    .k_wstrb(vmks_NW3__c_k_wstrb[63:32]),
    .kr_v(ctl_NW_p13__kr_v[0:0]),
    .kr_rdy(vmks_NW3__c_kr_rdy[1:1]),
    .kr_tag(ctl_NW_p13__kr_tag[16:0]),
    .kr_beat(ctl_NW_p13__kr_beat[3:0]),
    .kr_data(ctl_NW_p13__kr_data[255:0]),
    .k_wr_done(ctl_NW_p13__k_wr_done[0:0]),
    .row_v(ctl_NW_p13__row_v[0:0]),
    .row_op(ctl_NW_p13__row_op[2:0]),
    .row_bank(ctl_NW_p13__row_bank[4:0]),
    .row_row(ctl_NW_p13__row_row[18:0]),
    .col_v(ctl_NW_p13__col_v[0:0]),
    .col_we(ctl_NW_p13__col_we[0:0]),
    .col_bank(ctl_NW_p13__col_bank[4:0]),
    .col_col(ctl_NW_p13__col_col[4:0]),
    .col_data(ctl_NW_p13__col_data[255:0]),
    .col_strb(ctl_NW_p13__col_strb[31:0]),
    .dram_rvalid(phy_NW__dram_rvalid[13:13]),
    .dram_rdata(phy_NW__dram_rdata[3583:3328]),
    .pc_fault(ctl_NW_p13__pc_fault[0:0]),
    .owner_fault_split(ctl_NW_p13__owner_fault_split[5:0])
  );
  ot_hbm_svc_pc_ctrl_leaf_cfg_h9b #(.OREG(1), .KREG(1), .KRREG(1), .RREG(1), .WPAY(1), .QREG(1)) ctl_NW_p14 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(refcfg_NW__pc_rst_n[0:0]),
    .pc_id(5'b01110),
    .refresh_reload(refcfg_NW__refresh_reload[119:112]),
    .k_v(vmks_NW3__c_k_v[2:2]),
    .k_rdy(ctl_NW_p14__k_rdy[0:0]),
    .k_we(vmks_NW3__c_k_we[2:2]),
    .k_addr(vmks_NW3__c_k_addr[89:60]),
    .k_len(vmks_NW3__c_k_len[11:8]),
    .k_tag(vmks_NW3__c_k_tag[50:34]),
    .k_wdata(vmks_NW3__c_k_wdata[767:512]),
    .k_wstrb(vmks_NW3__c_k_wstrb[95:64]),
    .kr_v(ctl_NW_p14__kr_v[0:0]),
    .kr_rdy(vmks_NW3__c_kr_rdy[2:2]),
    .kr_tag(ctl_NW_p14__kr_tag[16:0]),
    .kr_beat(ctl_NW_p14__kr_beat[3:0]),
    .kr_data(ctl_NW_p14__kr_data[255:0]),
    .k_wr_done(ctl_NW_p14__k_wr_done[0:0]),
    .row_v(ctl_NW_p14__row_v[0:0]),
    .row_op(ctl_NW_p14__row_op[2:0]),
    .row_bank(ctl_NW_p14__row_bank[4:0]),
    .row_row(ctl_NW_p14__row_row[18:0]),
    .col_v(ctl_NW_p14__col_v[0:0]),
    .col_we(ctl_NW_p14__col_we[0:0]),
    .col_bank(ctl_NW_p14__col_bank[4:0]),
    .col_col(ctl_NW_p14__col_col[4:0]),
    .col_data(ctl_NW_p14__col_data[255:0]),
    .col_strb(ctl_NW_p14__col_strb[31:0]),
    .dram_rvalid(phy_NW__dram_rvalid[14:14]),
    .dram_rdata(phy_NW__dram_rdata[3839:3584]),
    .pc_fault(ctl_NW_p14__pc_fault[0:0]),
    .owner_fault_split(ctl_NW_p14__owner_fault_split[5:0])
  );
  ot_hbm_svc_pc_ctrl_leaf_cfg_h9b #(.OREG(1), .KREG(1), .KRREG(1), .RREG(1), .WPAY(1), .QREG(1)) ctl_NW_p15 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(refcfg_NW__pc_rst_n[0:0]),
    .pc_id(5'b01111),
    .refresh_reload(refcfg_NW__refresh_reload[127:120]),
    .k_v(vmks_NW3__c_k_v[3:3]),
    .k_rdy(ctl_NW_p15__k_rdy[0:0]),
    .k_we(vmks_NW3__c_k_we[3:3]),
    .k_addr(vmks_NW3__c_k_addr[119:90]),
    .k_len(vmks_NW3__c_k_len[15:12]),
    .k_tag(vmks_NW3__c_k_tag[67:51]),
    .k_wdata(vmks_NW3__c_k_wdata[1023:768]),
    .k_wstrb(vmks_NW3__c_k_wstrb[127:96]),
    .kr_v(ctl_NW_p15__kr_v[0:0]),
    .kr_rdy(vmks_NW3__c_kr_rdy[3:3]),
    .kr_tag(ctl_NW_p15__kr_tag[16:0]),
    .kr_beat(ctl_NW_p15__kr_beat[3:0]),
    .kr_data(ctl_NW_p15__kr_data[255:0]),
    .k_wr_done(ctl_NW_p15__k_wr_done[0:0]),
    .row_v(ctl_NW_p15__row_v[0:0]),
    .row_op(ctl_NW_p15__row_op[2:0]),
    .row_bank(ctl_NW_p15__row_bank[4:0]),
    .row_row(ctl_NW_p15__row_row[18:0]),
    .col_v(ctl_NW_p15__col_v[0:0]),
    .col_we(ctl_NW_p15__col_we[0:0]),
    .col_bank(ctl_NW_p15__col_bank[4:0]),
    .col_col(ctl_NW_p15__col_col[4:0]),
    .col_data(ctl_NW_p15__col_data[255:0]),
    .col_strb(ctl_NW_p15__col_strb[31:0]),
    .dram_rvalid(phy_NW__dram_rvalid[15:15]),
    .dram_rdata(phy_NW__dram_rdata[4095:3840]),
    .pc_fault(ctl_NW_p15__pc_fault[0:0]),
    .owner_fault_split(ctl_NW_p15__owner_fault_split[5:0])
  );
  ot_hbm_svc_pc_ctrl_leaf_cfg_h9b #(.OREG(1), .KREG(1), .KRREG(1), .RREG(1), .WPAY(1), .QREG(1)) ctl_NW_p16 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(refcfg_NE__pc_rst_n[0:0]),
    .pc_id(5'b10000),
    .refresh_reload(refcfg_NE__refresh_reload[7:0]),
    .k_v(vmks_NW4__c_k_v[0:0]),
    .k_rdy(ctl_NW_p16__k_rdy[0:0]),
    .k_we(vmks_NW4__c_k_we[0:0]),
    .k_addr(vmks_NW4__c_k_addr[29:0]),
    .k_len(vmks_NW4__c_k_len[3:0]),
    .k_tag(vmks_NW4__c_k_tag[16:0]),
    .k_wdata(vmks_NW4__c_k_wdata[255:0]),
    .k_wstrb(vmks_NW4__c_k_wstrb[31:0]),
    .kr_v(ctl_NW_p16__kr_v[0:0]),
    .kr_rdy(vmks_NW4__c_kr_rdy[0:0]),
    .kr_tag(ctl_NW_p16__kr_tag[16:0]),
    .kr_beat(ctl_NW_p16__kr_beat[3:0]),
    .kr_data(ctl_NW_p16__kr_data[255:0]),
    .k_wr_done(ctl_NW_p16__k_wr_done[0:0]),
    .row_v(ctl_NW_p16__row_v[0:0]),
    .row_op(ctl_NW_p16__row_op[2:0]),
    .row_bank(ctl_NW_p16__row_bank[4:0]),
    .row_row(ctl_NW_p16__row_row[18:0]),
    .col_v(ctl_NW_p16__col_v[0:0]),
    .col_we(ctl_NW_p16__col_we[0:0]),
    .col_bank(ctl_NW_p16__col_bank[4:0]),
    .col_col(ctl_NW_p16__col_col[4:0]),
    .col_data(ctl_NW_p16__col_data[255:0]),
    .col_strb(ctl_NW_p16__col_strb[31:0]),
    .dram_rvalid(phy_NW__dram_rvalid[16:16]),
    .dram_rdata(phy_NW__dram_rdata[4351:4096]),
    .pc_fault(ctl_NW_p16__pc_fault[0:0]),
    .owner_fault_split(ctl_NW_p16__owner_fault_split[5:0])
  );
  ot_hbm_svc_pc_ctrl_leaf_cfg_h9b #(.OREG(1), .KREG(1), .KRREG(1), .RREG(1), .WPAY(1), .QREG(1)) ctl_NW_p17 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(refcfg_NE__pc_rst_n[0:0]),
    .pc_id(5'b10001),
    .refresh_reload(refcfg_NE__refresh_reload[15:8]),
    .k_v(vmks_NW4__c_k_v[1:1]),
    .k_rdy(ctl_NW_p17__k_rdy[0:0]),
    .k_we(vmks_NW4__c_k_we[1:1]),
    .k_addr(vmks_NW4__c_k_addr[59:30]),
    .k_len(vmks_NW4__c_k_len[7:4]),
    .k_tag(vmks_NW4__c_k_tag[33:17]),
    .k_wdata(vmks_NW4__c_k_wdata[511:256]),
    .k_wstrb(vmks_NW4__c_k_wstrb[63:32]),
    .kr_v(ctl_NW_p17__kr_v[0:0]),
    .kr_rdy(vmks_NW4__c_kr_rdy[1:1]),
    .kr_tag(ctl_NW_p17__kr_tag[16:0]),
    .kr_beat(ctl_NW_p17__kr_beat[3:0]),
    .kr_data(ctl_NW_p17__kr_data[255:0]),
    .k_wr_done(ctl_NW_p17__k_wr_done[0:0]),
    .row_v(ctl_NW_p17__row_v[0:0]),
    .row_op(ctl_NW_p17__row_op[2:0]),
    .row_bank(ctl_NW_p17__row_bank[4:0]),
    .row_row(ctl_NW_p17__row_row[18:0]),
    .col_v(ctl_NW_p17__col_v[0:0]),
    .col_we(ctl_NW_p17__col_we[0:0]),
    .col_bank(ctl_NW_p17__col_bank[4:0]),
    .col_col(ctl_NW_p17__col_col[4:0]),
    .col_data(ctl_NW_p17__col_data[255:0]),
    .col_strb(ctl_NW_p17__col_strb[31:0]),
    .dram_rvalid(phy_NW__dram_rvalid[17:17]),
    .dram_rdata(phy_NW__dram_rdata[4607:4352]),
    .pc_fault(ctl_NW_p17__pc_fault[0:0]),
    .owner_fault_split(ctl_NW_p17__owner_fault_split[5:0])
  );
  ot_hbm_svc_pc_ctrl_leaf_cfg_h9b #(.OREG(1), .KREG(1), .KRREG(1), .RREG(1), .WPAY(1), .QREG(1)) ctl_NW_p18 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(refcfg_NE__pc_rst_n[0:0]),
    .pc_id(5'b10010),
    .refresh_reload(refcfg_NE__refresh_reload[23:16]),
    .k_v(vmks_NW4__c_k_v[2:2]),
    .k_rdy(ctl_NW_p18__k_rdy[0:0]),
    .k_we(vmks_NW4__c_k_we[2:2]),
    .k_addr(vmks_NW4__c_k_addr[89:60]),
    .k_len(vmks_NW4__c_k_len[11:8]),
    .k_tag(vmks_NW4__c_k_tag[50:34]),
    .k_wdata(vmks_NW4__c_k_wdata[767:512]),
    .k_wstrb(vmks_NW4__c_k_wstrb[95:64]),
    .kr_v(ctl_NW_p18__kr_v[0:0]),
    .kr_rdy(vmks_NW4__c_kr_rdy[2:2]),
    .kr_tag(ctl_NW_p18__kr_tag[16:0]),
    .kr_beat(ctl_NW_p18__kr_beat[3:0]),
    .kr_data(ctl_NW_p18__kr_data[255:0]),
    .k_wr_done(ctl_NW_p18__k_wr_done[0:0]),
    .row_v(ctl_NW_p18__row_v[0:0]),
    .row_op(ctl_NW_p18__row_op[2:0]),
    .row_bank(ctl_NW_p18__row_bank[4:0]),
    .row_row(ctl_NW_p18__row_row[18:0]),
    .col_v(ctl_NW_p18__col_v[0:0]),
    .col_we(ctl_NW_p18__col_we[0:0]),
    .col_bank(ctl_NW_p18__col_bank[4:0]),
    .col_col(ctl_NW_p18__col_col[4:0]),
    .col_data(ctl_NW_p18__col_data[255:0]),
    .col_strb(ctl_NW_p18__col_strb[31:0]),
    .dram_rvalid(phy_NW__dram_rvalid[18:18]),
    .dram_rdata(phy_NW__dram_rdata[4863:4608]),
    .pc_fault(ctl_NW_p18__pc_fault[0:0]),
    .owner_fault_split(ctl_NW_p18__owner_fault_split[5:0])
  );
  ot_hbm_svc_pc_ctrl_leaf_cfg_h9b #(.OREG(1), .KREG(1), .KRREG(1), .RREG(1), .WPAY(1), .QREG(1)) ctl_NW_p19 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(refcfg_NE__pc_rst_n[0:0]),
    .pc_id(5'b10011),
    .refresh_reload(refcfg_NE__refresh_reload[31:24]),
    .k_v(vmks_NW4__c_k_v[3:3]),
    .k_rdy(ctl_NW_p19__k_rdy[0:0]),
    .k_we(vmks_NW4__c_k_we[3:3]),
    .k_addr(vmks_NW4__c_k_addr[119:90]),
    .k_len(vmks_NW4__c_k_len[15:12]),
    .k_tag(vmks_NW4__c_k_tag[67:51]),
    .k_wdata(vmks_NW4__c_k_wdata[1023:768]),
    .k_wstrb(vmks_NW4__c_k_wstrb[127:96]),
    .kr_v(ctl_NW_p19__kr_v[0:0]),
    .kr_rdy(vmks_NW4__c_kr_rdy[3:3]),
    .kr_tag(ctl_NW_p19__kr_tag[16:0]),
    .kr_beat(ctl_NW_p19__kr_beat[3:0]),
    .kr_data(ctl_NW_p19__kr_data[255:0]),
    .k_wr_done(ctl_NW_p19__k_wr_done[0:0]),
    .row_v(ctl_NW_p19__row_v[0:0]),
    .row_op(ctl_NW_p19__row_op[2:0]),
    .row_bank(ctl_NW_p19__row_bank[4:0]),
    .row_row(ctl_NW_p19__row_row[18:0]),
    .col_v(ctl_NW_p19__col_v[0:0]),
    .col_we(ctl_NW_p19__col_we[0:0]),
    .col_bank(ctl_NW_p19__col_bank[4:0]),
    .col_col(ctl_NW_p19__col_col[4:0]),
    .col_data(ctl_NW_p19__col_data[255:0]),
    .col_strb(ctl_NW_p19__col_strb[31:0]),
    .dram_rvalid(phy_NW__dram_rvalid[19:19]),
    .dram_rdata(phy_NW__dram_rdata[5119:4864]),
    .pc_fault(ctl_NW_p19__pc_fault[0:0]),
    .owner_fault_split(ctl_NW_p19__owner_fault_split[5:0])
  );
  ot_hbm_svc_pc_ctrl_leaf_cfg_h9b #(.OREG(1), .KREG(1), .KRREG(1), .RREG(1), .WPAY(1), .QREG(1)) ctl_NW_p20 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(refcfg_NE__pc_rst_n[0:0]),
    .pc_id(5'b10100),
    .refresh_reload(refcfg_NE__refresh_reload[39:32]),
    .k_v(vmks_NW5__c_k_v[0:0]),
    .k_rdy(ctl_NW_p20__k_rdy[0:0]),
    .k_we(vmks_NW5__c_k_we[0:0]),
    .k_addr(vmks_NW5__c_k_addr[29:0]),
    .k_len(vmks_NW5__c_k_len[3:0]),
    .k_tag(vmks_NW5__c_k_tag[16:0]),
    .k_wdata(vmks_NW5__c_k_wdata[255:0]),
    .k_wstrb(vmks_NW5__c_k_wstrb[31:0]),
    .kr_v(ctl_NW_p20__kr_v[0:0]),
    .kr_rdy(vmks_NW5__c_kr_rdy[0:0]),
    .kr_tag(ctl_NW_p20__kr_tag[16:0]),
    .kr_beat(ctl_NW_p20__kr_beat[3:0]),
    .kr_data(ctl_NW_p20__kr_data[255:0]),
    .k_wr_done(ctl_NW_p20__k_wr_done[0:0]),
    .row_v(ctl_NW_p20__row_v[0:0]),
    .row_op(ctl_NW_p20__row_op[2:0]),
    .row_bank(ctl_NW_p20__row_bank[4:0]),
    .row_row(ctl_NW_p20__row_row[18:0]),
    .col_v(ctl_NW_p20__col_v[0:0]),
    .col_we(ctl_NW_p20__col_we[0:0]),
    .col_bank(ctl_NW_p20__col_bank[4:0]),
    .col_col(ctl_NW_p20__col_col[4:0]),
    .col_data(ctl_NW_p20__col_data[255:0]),
    .col_strb(ctl_NW_p20__col_strb[31:0]),
    .dram_rvalid(phy_NW__dram_rvalid[20:20]),
    .dram_rdata(phy_NW__dram_rdata[5375:5120]),
    .pc_fault(ctl_NW_p20__pc_fault[0:0]),
    .owner_fault_split(ctl_NW_p20__owner_fault_split[5:0])
  );
  ot_hbm_svc_pc_ctrl_leaf_cfg_h9b #(.OREG(1), .KREG(1), .KRREG(1), .RREG(1), .WPAY(1), .QREG(1)) ctl_NW_p21 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(refcfg_NE__pc_rst_n[0:0]),
    .pc_id(5'b10101),
    .refresh_reload(refcfg_NE__refresh_reload[47:40]),
    .k_v(vmks_NW5__c_k_v[1:1]),
    .k_rdy(ctl_NW_p21__k_rdy[0:0]),
    .k_we(vmks_NW5__c_k_we[1:1]),
    .k_addr(vmks_NW5__c_k_addr[59:30]),
    .k_len(vmks_NW5__c_k_len[7:4]),
    .k_tag(vmks_NW5__c_k_tag[33:17]),
    .k_wdata(vmks_NW5__c_k_wdata[511:256]),
    .k_wstrb(vmks_NW5__c_k_wstrb[63:32]),
    .kr_v(ctl_NW_p21__kr_v[0:0]),
    .kr_rdy(vmks_NW5__c_kr_rdy[1:1]),
    .kr_tag(ctl_NW_p21__kr_tag[16:0]),
    .kr_beat(ctl_NW_p21__kr_beat[3:0]),
    .kr_data(ctl_NW_p21__kr_data[255:0]),
    .k_wr_done(ctl_NW_p21__k_wr_done[0:0]),
    .row_v(ctl_NW_p21__row_v[0:0]),
    .row_op(ctl_NW_p21__row_op[2:0]),
    .row_bank(ctl_NW_p21__row_bank[4:0]),
    .row_row(ctl_NW_p21__row_row[18:0]),
    .col_v(ctl_NW_p21__col_v[0:0]),
    .col_we(ctl_NW_p21__col_we[0:0]),
    .col_bank(ctl_NW_p21__col_bank[4:0]),
    .col_col(ctl_NW_p21__col_col[4:0]),
    .col_data(ctl_NW_p21__col_data[255:0]),
    .col_strb(ctl_NW_p21__col_strb[31:0]),
    .dram_rvalid(phy_NW__dram_rvalid[21:21]),
    .dram_rdata(phy_NW__dram_rdata[5631:5376]),
    .pc_fault(ctl_NW_p21__pc_fault[0:0]),
    .owner_fault_split(ctl_NW_p21__owner_fault_split[5:0])
  );
  ot_hbm_svc_pc_ctrl_leaf_cfg_h9b #(.OREG(1), .KREG(1), .KRREG(1), .RREG(1), .WPAY(1), .QREG(1)) ctl_NW_p22 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(refcfg_NE__pc_rst_n[0:0]),
    .pc_id(5'b10110),
    .refresh_reload(refcfg_NE__refresh_reload[55:48]),
    .k_v(vmks_NW5__c_k_v[2:2]),
    .k_rdy(ctl_NW_p22__k_rdy[0:0]),
    .k_we(vmks_NW5__c_k_we[2:2]),
    .k_addr(vmks_NW5__c_k_addr[89:60]),
    .k_len(vmks_NW5__c_k_len[11:8]),
    .k_tag(vmks_NW5__c_k_tag[50:34]),
    .k_wdata(vmks_NW5__c_k_wdata[767:512]),
    .k_wstrb(vmks_NW5__c_k_wstrb[95:64]),
    .kr_v(ctl_NW_p22__kr_v[0:0]),
    .kr_rdy(vmks_NW5__c_kr_rdy[2:2]),
    .kr_tag(ctl_NW_p22__kr_tag[16:0]),
    .kr_beat(ctl_NW_p22__kr_beat[3:0]),
    .kr_data(ctl_NW_p22__kr_data[255:0]),
    .k_wr_done(ctl_NW_p22__k_wr_done[0:0]),
    .row_v(ctl_NW_p22__row_v[0:0]),
    .row_op(ctl_NW_p22__row_op[2:0]),
    .row_bank(ctl_NW_p22__row_bank[4:0]),
    .row_row(ctl_NW_p22__row_row[18:0]),
    .col_v(ctl_NW_p22__col_v[0:0]),
    .col_we(ctl_NW_p22__col_we[0:0]),
    .col_bank(ctl_NW_p22__col_bank[4:0]),
    .col_col(ctl_NW_p22__col_col[4:0]),
    .col_data(ctl_NW_p22__col_data[255:0]),
    .col_strb(ctl_NW_p22__col_strb[31:0]),
    .dram_rvalid(phy_NW__dram_rvalid[22:22]),
    .dram_rdata(phy_NW__dram_rdata[5887:5632]),
    .pc_fault(ctl_NW_p22__pc_fault[0:0]),
    .owner_fault_split(ctl_NW_p22__owner_fault_split[5:0])
  );
  ot_hbm_svc_pc_ctrl_leaf_cfg_h9b #(.OREG(1), .KREG(1), .KRREG(1), .RREG(1), .WPAY(1), .QREG(1)) ctl_NW_p23 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(refcfg_NE__pc_rst_n[0:0]),
    .pc_id(5'b10111),
    .refresh_reload(refcfg_NE__refresh_reload[63:56]),
    .k_v(vmks_NW5__c_k_v[3:3]),
    .k_rdy(ctl_NW_p23__k_rdy[0:0]),
    .k_we(vmks_NW5__c_k_we[3:3]),
    .k_addr(vmks_NW5__c_k_addr[119:90]),
    .k_len(vmks_NW5__c_k_len[15:12]),
    .k_tag(vmks_NW5__c_k_tag[67:51]),
    .k_wdata(vmks_NW5__c_k_wdata[1023:768]),
    .k_wstrb(vmks_NW5__c_k_wstrb[127:96]),
    .kr_v(ctl_NW_p23__kr_v[0:0]),
    .kr_rdy(vmks_NW5__c_kr_rdy[3:3]),
    .kr_tag(ctl_NW_p23__kr_tag[16:0]),
    .kr_beat(ctl_NW_p23__kr_beat[3:0]),
    .kr_data(ctl_NW_p23__kr_data[255:0]),
    .k_wr_done(ctl_NW_p23__k_wr_done[0:0]),
    .row_v(ctl_NW_p23__row_v[0:0]),
    .row_op(ctl_NW_p23__row_op[2:0]),
    .row_bank(ctl_NW_p23__row_bank[4:0]),
    .row_row(ctl_NW_p23__row_row[18:0]),
    .col_v(ctl_NW_p23__col_v[0:0]),
    .col_we(ctl_NW_p23__col_we[0:0]),
    .col_bank(ctl_NW_p23__col_bank[4:0]),
    .col_col(ctl_NW_p23__col_col[4:0]),
    .col_data(ctl_NW_p23__col_data[255:0]),
    .col_strb(ctl_NW_p23__col_strb[31:0]),
    .dram_rvalid(phy_NW__dram_rvalid[23:23]),
    .dram_rdata(phy_NW__dram_rdata[6143:5888]),
    .pc_fault(ctl_NW_p23__pc_fault[0:0]),
    .owner_fault_split(ctl_NW_p23__owner_fault_split[5:0])
  );
  ot_hbm_svc_pc_ctrl_leaf_cfg_h9b #(.OREG(1), .KREG(1), .KRREG(1), .RREG(1), .WPAY(1), .QREG(1)) ctl_NW_p24 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(refcfg_NE__pc_rst_n[0:0]),
    .pc_id(5'b11000),
    .refresh_reload(refcfg_NE__refresh_reload[71:64]),
    .k_v(vmks_NW6__c_k_v[0:0]),
    .k_rdy(ctl_NW_p24__k_rdy[0:0]),
    .k_we(vmks_NW6__c_k_we[0:0]),
    .k_addr(vmks_NW6__c_k_addr[29:0]),
    .k_len(vmks_NW6__c_k_len[3:0]),
    .k_tag(vmks_NW6__c_k_tag[16:0]),
    .k_wdata(vmks_NW6__c_k_wdata[255:0]),
    .k_wstrb(vmks_NW6__c_k_wstrb[31:0]),
    .kr_v(ctl_NW_p24__kr_v[0:0]),
    .kr_rdy(vmks_NW6__c_kr_rdy[0:0]),
    .kr_tag(ctl_NW_p24__kr_tag[16:0]),
    .kr_beat(ctl_NW_p24__kr_beat[3:0]),
    .kr_data(ctl_NW_p24__kr_data[255:0]),
    .k_wr_done(ctl_NW_p24__k_wr_done[0:0]),
    .row_v(ctl_NW_p24__row_v[0:0]),
    .row_op(ctl_NW_p24__row_op[2:0]),
    .row_bank(ctl_NW_p24__row_bank[4:0]),
    .row_row(ctl_NW_p24__row_row[18:0]),
    .col_v(ctl_NW_p24__col_v[0:0]),
    .col_we(ctl_NW_p24__col_we[0:0]),
    .col_bank(ctl_NW_p24__col_bank[4:0]),
    .col_col(ctl_NW_p24__col_col[4:0]),
    .col_data(ctl_NW_p24__col_data[255:0]),
    .col_strb(ctl_NW_p24__col_strb[31:0]),
    .dram_rvalid(phy_NW__dram_rvalid[24:24]),
    .dram_rdata(phy_NW__dram_rdata[6399:6144]),
    .pc_fault(ctl_NW_p24__pc_fault[0:0]),
    .owner_fault_split(ctl_NW_p24__owner_fault_split[5:0])
  );
  ot_hbm_svc_pc_ctrl_leaf_cfg_h9b #(.OREG(1), .KREG(1), .KRREG(1), .RREG(1), .WPAY(1), .QREG(1)) ctl_NW_p25 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(refcfg_NE__pc_rst_n[0:0]),
    .pc_id(5'b11001),
    .refresh_reload(refcfg_NE__refresh_reload[79:72]),
    .k_v(vmks_NW6__c_k_v[1:1]),
    .k_rdy(ctl_NW_p25__k_rdy[0:0]),
    .k_we(vmks_NW6__c_k_we[1:1]),
    .k_addr(vmks_NW6__c_k_addr[59:30]),
    .k_len(vmks_NW6__c_k_len[7:4]),
    .k_tag(vmks_NW6__c_k_tag[33:17]),
    .k_wdata(vmks_NW6__c_k_wdata[511:256]),
    .k_wstrb(vmks_NW6__c_k_wstrb[63:32]),
    .kr_v(ctl_NW_p25__kr_v[0:0]),
    .kr_rdy(vmks_NW6__c_kr_rdy[1:1]),
    .kr_tag(ctl_NW_p25__kr_tag[16:0]),
    .kr_beat(ctl_NW_p25__kr_beat[3:0]),
    .kr_data(ctl_NW_p25__kr_data[255:0]),
    .k_wr_done(ctl_NW_p25__k_wr_done[0:0]),
    .row_v(ctl_NW_p25__row_v[0:0]),
    .row_op(ctl_NW_p25__row_op[2:0]),
    .row_bank(ctl_NW_p25__row_bank[4:0]),
    .row_row(ctl_NW_p25__row_row[18:0]),
    .col_v(ctl_NW_p25__col_v[0:0]),
    .col_we(ctl_NW_p25__col_we[0:0]),
    .col_bank(ctl_NW_p25__col_bank[4:0]),
    .col_col(ctl_NW_p25__col_col[4:0]),
    .col_data(ctl_NW_p25__col_data[255:0]),
    .col_strb(ctl_NW_p25__col_strb[31:0]),
    .dram_rvalid(phy_NW__dram_rvalid[25:25]),
    .dram_rdata(phy_NW__dram_rdata[6655:6400]),
    .pc_fault(ctl_NW_p25__pc_fault[0:0]),
    .owner_fault_split(ctl_NW_p25__owner_fault_split[5:0])
  );
  ot_hbm_svc_pc_ctrl_leaf_cfg_h9b #(.OREG(1), .KREG(1), .KRREG(1), .RREG(1), .WPAY(1), .QREG(1)) ctl_NW_p26 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(refcfg_NE__pc_rst_n[0:0]),
    .pc_id(5'b11010),
    .refresh_reload(refcfg_NE__refresh_reload[87:80]),
    .k_v(vmks_NW6__c_k_v[2:2]),
    .k_rdy(ctl_NW_p26__k_rdy[0:0]),
    .k_we(vmks_NW6__c_k_we[2:2]),
    .k_addr(vmks_NW6__c_k_addr[89:60]),
    .k_len(vmks_NW6__c_k_len[11:8]),
    .k_tag(vmks_NW6__c_k_tag[50:34]),
    .k_wdata(vmks_NW6__c_k_wdata[767:512]),
    .k_wstrb(vmks_NW6__c_k_wstrb[95:64]),
    .kr_v(ctl_NW_p26__kr_v[0:0]),
    .kr_rdy(vmks_NW6__c_kr_rdy[2:2]),
    .kr_tag(ctl_NW_p26__kr_tag[16:0]),
    .kr_beat(ctl_NW_p26__kr_beat[3:0]),
    .kr_data(ctl_NW_p26__kr_data[255:0]),
    .k_wr_done(ctl_NW_p26__k_wr_done[0:0]),
    .row_v(ctl_NW_p26__row_v[0:0]),
    .row_op(ctl_NW_p26__row_op[2:0]),
    .row_bank(ctl_NW_p26__row_bank[4:0]),
    .row_row(ctl_NW_p26__row_row[18:0]),
    .col_v(ctl_NW_p26__col_v[0:0]),
    .col_we(ctl_NW_p26__col_we[0:0]),
    .col_bank(ctl_NW_p26__col_bank[4:0]),
    .col_col(ctl_NW_p26__col_col[4:0]),
    .col_data(ctl_NW_p26__col_data[255:0]),
    .col_strb(ctl_NW_p26__col_strb[31:0]),
    .dram_rvalid(phy_NW__dram_rvalid[26:26]),
    .dram_rdata(phy_NW__dram_rdata[6911:6656]),
    .pc_fault(ctl_NW_p26__pc_fault[0:0]),
    .owner_fault_split(ctl_NW_p26__owner_fault_split[5:0])
  );
  ot_hbm_svc_pc_ctrl_leaf_cfg_h9b #(.OREG(1), .KREG(1), .KRREG(1), .RREG(1), .WPAY(1), .QREG(1)) ctl_NW_p27 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(refcfg_NE__pc_rst_n[0:0]),
    .pc_id(5'b11011),
    .refresh_reload(refcfg_NE__refresh_reload[95:88]),
    .k_v(vmks_NW6__c_k_v[3:3]),
    .k_rdy(ctl_NW_p27__k_rdy[0:0]),
    .k_we(vmks_NW6__c_k_we[3:3]),
    .k_addr(vmks_NW6__c_k_addr[119:90]),
    .k_len(vmks_NW6__c_k_len[15:12]),
    .k_tag(vmks_NW6__c_k_tag[67:51]),
    .k_wdata(vmks_NW6__c_k_wdata[1023:768]),
    .k_wstrb(vmks_NW6__c_k_wstrb[127:96]),
    .kr_v(ctl_NW_p27__kr_v[0:0]),
    .kr_rdy(vmks_NW6__c_kr_rdy[3:3]),
    .kr_tag(ctl_NW_p27__kr_tag[16:0]),
    .kr_beat(ctl_NW_p27__kr_beat[3:0]),
    .kr_data(ctl_NW_p27__kr_data[255:0]),
    .k_wr_done(ctl_NW_p27__k_wr_done[0:0]),
    .row_v(ctl_NW_p27__row_v[0:0]),
    .row_op(ctl_NW_p27__row_op[2:0]),
    .row_bank(ctl_NW_p27__row_bank[4:0]),
    .row_row(ctl_NW_p27__row_row[18:0]),
    .col_v(ctl_NW_p27__col_v[0:0]),
    .col_we(ctl_NW_p27__col_we[0:0]),
    .col_bank(ctl_NW_p27__col_bank[4:0]),
    .col_col(ctl_NW_p27__col_col[4:0]),
    .col_data(ctl_NW_p27__col_data[255:0]),
    .col_strb(ctl_NW_p27__col_strb[31:0]),
    .dram_rvalid(phy_NW__dram_rvalid[27:27]),
    .dram_rdata(phy_NW__dram_rdata[7167:6912]),
    .pc_fault(ctl_NW_p27__pc_fault[0:0]),
    .owner_fault_split(ctl_NW_p27__owner_fault_split[5:0])
  );
  ot_hbm_svc_pc_ctrl_leaf_cfg_h9b #(.OREG(1), .KREG(1), .KRREG(1), .RREG(1), .WPAY(1), .QREG(1)) ctl_NW_p28 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(refcfg_NE__pc_rst_n[0:0]),
    .pc_id(5'b11100),
    .refresh_reload(refcfg_NE__refresh_reload[103:96]),
    .k_v(vmks_NW7__c_k_v[0:0]),
    .k_rdy(ctl_NW_p28__k_rdy[0:0]),
    .k_we(vmks_NW7__c_k_we[0:0]),
    .k_addr(vmks_NW7__c_k_addr[29:0]),
    .k_len(vmks_NW7__c_k_len[3:0]),
    .k_tag(vmks_NW7__c_k_tag[16:0]),
    .k_wdata(vmks_NW7__c_k_wdata[255:0]),
    .k_wstrb(vmks_NW7__c_k_wstrb[31:0]),
    .kr_v(ctl_NW_p28__kr_v[0:0]),
    .kr_rdy(vmks_NW7__c_kr_rdy[0:0]),
    .kr_tag(ctl_NW_p28__kr_tag[16:0]),
    .kr_beat(ctl_NW_p28__kr_beat[3:0]),
    .kr_data(ctl_NW_p28__kr_data[255:0]),
    .k_wr_done(ctl_NW_p28__k_wr_done[0:0]),
    .row_v(ctl_NW_p28__row_v[0:0]),
    .row_op(ctl_NW_p28__row_op[2:0]),
    .row_bank(ctl_NW_p28__row_bank[4:0]),
    .row_row(ctl_NW_p28__row_row[18:0]),
    .col_v(ctl_NW_p28__col_v[0:0]),
    .col_we(ctl_NW_p28__col_we[0:0]),
    .col_bank(ctl_NW_p28__col_bank[4:0]),
    .col_col(ctl_NW_p28__col_col[4:0]),
    .col_data(ctl_NW_p28__col_data[255:0]),
    .col_strb(ctl_NW_p28__col_strb[31:0]),
    .dram_rvalid(phy_NW__dram_rvalid[28:28]),
    .dram_rdata(phy_NW__dram_rdata[7423:7168]),
    .pc_fault(ctl_NW_p28__pc_fault[0:0]),
    .owner_fault_split(ctl_NW_p28__owner_fault_split[5:0])
  );
  ot_hbm_svc_pc_ctrl_leaf_cfg_h9b #(.OREG(1), .KREG(1), .KRREG(1), .RREG(1), .WPAY(1), .QREG(1)) ctl_NW_p29 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(refcfg_NE__pc_rst_n[0:0]),
    .pc_id(5'b11101),
    .refresh_reload(refcfg_NE__refresh_reload[111:104]),
    .k_v(vmks_NW7__c_k_v[1:1]),
    .k_rdy(ctl_NW_p29__k_rdy[0:0]),
    .k_we(vmks_NW7__c_k_we[1:1]),
    .k_addr(vmks_NW7__c_k_addr[59:30]),
    .k_len(vmks_NW7__c_k_len[7:4]),
    .k_tag(vmks_NW7__c_k_tag[33:17]),
    .k_wdata(vmks_NW7__c_k_wdata[511:256]),
    .k_wstrb(vmks_NW7__c_k_wstrb[63:32]),
    .kr_v(ctl_NW_p29__kr_v[0:0]),
    .kr_rdy(vmks_NW7__c_kr_rdy[1:1]),
    .kr_tag(ctl_NW_p29__kr_tag[16:0]),
    .kr_beat(ctl_NW_p29__kr_beat[3:0]),
    .kr_data(ctl_NW_p29__kr_data[255:0]),
    .k_wr_done(ctl_NW_p29__k_wr_done[0:0]),
    .row_v(ctl_NW_p29__row_v[0:0]),
    .row_op(ctl_NW_p29__row_op[2:0]),
    .row_bank(ctl_NW_p29__row_bank[4:0]),
    .row_row(ctl_NW_p29__row_row[18:0]),
    .col_v(ctl_NW_p29__col_v[0:0]),
    .col_we(ctl_NW_p29__col_we[0:0]),
    .col_bank(ctl_NW_p29__col_bank[4:0]),
    .col_col(ctl_NW_p29__col_col[4:0]),
    .col_data(ctl_NW_p29__col_data[255:0]),
    .col_strb(ctl_NW_p29__col_strb[31:0]),
    .dram_rvalid(phy_NW__dram_rvalid[29:29]),
    .dram_rdata(phy_NW__dram_rdata[7679:7424]),
    .pc_fault(ctl_NW_p29__pc_fault[0:0]),
    .owner_fault_split(ctl_NW_p29__owner_fault_split[5:0])
  );
  ot_hbm_svc_pc_ctrl_leaf_cfg_h9b #(.OREG(1), .KREG(1), .KRREG(1), .RREG(1), .WPAY(1), .QREG(1)) ctl_NW_p30 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(refcfg_NE__pc_rst_n[0:0]),
    .pc_id(5'b11110),
    .refresh_reload(refcfg_NE__refresh_reload[119:112]),
    .k_v(vmks_NW7__c_k_v[2:2]),
    .k_rdy(ctl_NW_p30__k_rdy[0:0]),
    .k_we(vmks_NW7__c_k_we[2:2]),
    .k_addr(vmks_NW7__c_k_addr[89:60]),
    .k_len(vmks_NW7__c_k_len[11:8]),
    .k_tag(vmks_NW7__c_k_tag[50:34]),
    .k_wdata(vmks_NW7__c_k_wdata[767:512]),
    .k_wstrb(vmks_NW7__c_k_wstrb[95:64]),
    .kr_v(ctl_NW_p30__kr_v[0:0]),
    .kr_rdy(vmks_NW7__c_kr_rdy[2:2]),
    .kr_tag(ctl_NW_p30__kr_tag[16:0]),
    .kr_beat(ctl_NW_p30__kr_beat[3:0]),
    .kr_data(ctl_NW_p30__kr_data[255:0]),
    .k_wr_done(ctl_NW_p30__k_wr_done[0:0]),
    .row_v(ctl_NW_p30__row_v[0:0]),
    .row_op(ctl_NW_p30__row_op[2:0]),
    .row_bank(ctl_NW_p30__row_bank[4:0]),
    .row_row(ctl_NW_p30__row_row[18:0]),
    .col_v(ctl_NW_p30__col_v[0:0]),
    .col_we(ctl_NW_p30__col_we[0:0]),
    .col_bank(ctl_NW_p30__col_bank[4:0]),
    .col_col(ctl_NW_p30__col_col[4:0]),
    .col_data(ctl_NW_p30__col_data[255:0]),
    .col_strb(ctl_NW_p30__col_strb[31:0]),
    .dram_rvalid(phy_NW__dram_rvalid[30:30]),
    .dram_rdata(phy_NW__dram_rdata[7935:7680]),
    .pc_fault(ctl_NW_p30__pc_fault[0:0]),
    .owner_fault_split(ctl_NW_p30__owner_fault_split[5:0])
  );
  ot_hbm_svc_pc_ctrl_leaf_cfg_h9b #(.OREG(1), .KREG(1), .KRREG(1), .RREG(1), .WPAY(1), .QREG(1)) ctl_NW_p31 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(refcfg_NE__pc_rst_n[0:0]),
    .pc_id(5'b11111),
    .refresh_reload(refcfg_NE__refresh_reload[127:120]),
    .k_v(vmks_NW7__c_k_v[3:3]),
    .k_rdy(ctl_NW_p31__k_rdy[0:0]),
    .k_we(vmks_NW7__c_k_we[3:3]),
    .k_addr(vmks_NW7__c_k_addr[119:90]),
    .k_len(vmks_NW7__c_k_len[15:12]),
    .k_tag(vmks_NW7__c_k_tag[67:51]),
    .k_wdata(vmks_NW7__c_k_wdata[1023:768]),
    .k_wstrb(vmks_NW7__c_k_wstrb[127:96]),
    .kr_v(ctl_NW_p31__kr_v[0:0]),
    .kr_rdy(vmks_NW7__c_kr_rdy[3:3]),
    .kr_tag(ctl_NW_p31__kr_tag[16:0]),
    .kr_beat(ctl_NW_p31__kr_beat[3:0]),
    .kr_data(ctl_NW_p31__kr_data[255:0]),
    .k_wr_done(ctl_NW_p31__k_wr_done[0:0]),
    .row_v(ctl_NW_p31__row_v[0:0]),
    .row_op(ctl_NW_p31__row_op[2:0]),
    .row_bank(ctl_NW_p31__row_bank[4:0]),
    .row_row(ctl_NW_p31__row_row[18:0]),
    .col_v(ctl_NW_p31__col_v[0:0]),
    .col_we(ctl_NW_p31__col_we[0:0]),
    .col_bank(ctl_NW_p31__col_bank[4:0]),
    .col_col(ctl_NW_p31__col_col[4:0]),
    .col_data(ctl_NW_p31__col_data[255:0]),
    .col_strb(ctl_NW_p31__col_strb[31:0]),
    .dram_rvalid(phy_NW__dram_rvalid[31:31]),
    .dram_rdata(phy_NW__dram_rdata[8191:7936]),
    .pc_fault(ctl_NW_p31__pc_fault[0:0]),
    .owner_fault_split(ctl_NW_p31__owner_fault_split[5:0])
  );
  ot_hbm_su_static_cxport_dl_q cxdl_NE0_q (
    .clk_q(hb_ckgen__pll_stream[0:0]),
    .rst_q_n(hb_ckgen__por_stream[0:0]),
    .b0(cxdl_NE0_s__b0[523:0]),
    .b1(cxdl_NE0_s__b1[523:0]),
    .v0(cxdl_NE0_s__v0[7:0]),
    .v1(cxdl_NE0_s__v1[7:0]),
    .sfault_s(cxdl_NE0_s__sfault_s[0:0]),
    .dw_v(cxdl_NE0_q__dw_v[1:0]),
    .dw_row(cxdl_NE0_q__dw_row[17:0]),
    .dw_d(cxdl_NE0_q__dw_d[1023:0]),
    .fault(cxdl_NE0_q__fault[0:0])
  );
  ot_hbm_su_static_cxport_dl_s #(.QID(3), .G(0)) cxdl_NE0_s (
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .rst_s_n(hb_ckgen__por_stream[0:0]),
    .del_valid(hb_coll_NE__del_valid[0:0]),
    .del_flit(hb_coll_NE__del_flit[544:0]),
    .del_obase(hb_coll_NE__hgi_del_obase[39:0]),
    .b0(cxdl_NE0_s__b0[523:0]),
    .b1(cxdl_NE0_s__b1[523:0]),
    .v0(cxdl_NE0_s__v0[7:0]),
    .v1(cxdl_NE0_s__v1[7:0]),
    .sfault_s(cxdl_NE0_s__sfault_s[0:0])
  );
  ot_hbm_su_static_cxport_dl_q cxdl_NE1_q (
    .clk_q(hb_ckgen__pll_stream[0:0]),
    .rst_q_n(hb_ckgen__por_stream[0:0]),
    .b0(cxdl_NE1_s__b0[523:0]),
    .b1(cxdl_NE1_s__b1[523:0]),
    .v0(cxdl_NE1_s__v0[7:0]),
    .v1(cxdl_NE1_s__v1[7:0]),
    .sfault_s(cxdl_NE1_s__sfault_s[0:0]),
    .dw_v(cxdl_NE1_q__dw_v[1:0]),
    .dw_row(cxdl_NE1_q__dw_row[17:0]),
    .dw_d(cxdl_NE1_q__dw_d[1023:0]),
    .fault(cxdl_NE1_q__fault[0:0])
  );
  ot_hbm_su_static_cxport_dl_s #(.QID(3), .G(1)) cxdl_NE1_s (
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .rst_s_n(hb_ckgen__por_stream[0:0]),
    .del_valid(hb_coll_NE__del_valid[1:1]),
    .del_flit(hb_coll_NE__del_flit[1089:545]),
    .del_obase(hb_coll_NE__hgi_del_obase[79:40]),
    .b0(cxdl_NE1_s__b0[523:0]),
    .b1(cxdl_NE1_s__b1[523:0]),
    .v0(cxdl_NE1_s__v0[7:0]),
    .v1(cxdl_NE1_s__v1[7:0]),
    .sfault_s(cxdl_NE1_s__sfault_s[0:0])
  );
  ot_hbm_su_static_cxport_dl_q cxdl_NE2_q (
    .clk_q(hb_ckgen__pll_stream[0:0]),
    .rst_q_n(hb_ckgen__por_stream[0:0]),
    .b0(cxdl_NE2_s__b0[523:0]),
    .b1(cxdl_NE2_s__b1[523:0]),
    .v0(cxdl_NE2_s__v0[7:0]),
    .v1(cxdl_NE2_s__v1[7:0]),
    .sfault_s(cxdl_NE2_s__sfault_s[0:0]),
    .dw_v(cxdl_NE2_q__dw_v[1:0]),
    .dw_row(cxdl_NE2_q__dw_row[17:0]),
    .dw_d(cxdl_NE2_q__dw_d[1023:0]),
    .fault(cxdl_NE2_q__fault[0:0])
  );
  ot_hbm_su_static_cxport_dl_s #(.QID(3), .G(2)) cxdl_NE2_s (
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .rst_s_n(hb_ckgen__por_stream[0:0]),
    .del_valid(hb_coll_NE__del_valid[2:2]),
    .del_flit(hb_coll_NE__del_flit[1634:1090]),
    .del_obase(hb_coll_NE__hgi_del_obase[119:80]),
    .b0(cxdl_NE2_s__b0[523:0]),
    .b1(cxdl_NE2_s__b1[523:0]),
    .v0(cxdl_NE2_s__v0[7:0]),
    .v1(cxdl_NE2_s__v1[7:0]),
    .sfault_s(cxdl_NE2_s__sfault_s[0:0])
  );
  ot_hbm_su_static_cxport_dl_q cxdl_NE3_q (
    .clk_q(hb_ckgen__pll_stream[0:0]),
    .rst_q_n(hb_ckgen__por_stream[0:0]),
    .b0(cxdl_NE3_s__b0[523:0]),
    .b1(cxdl_NE3_s__b1[523:0]),
    .v0(cxdl_NE3_s__v0[7:0]),
    .v1(cxdl_NE3_s__v1[7:0]),
    .sfault_s(cxdl_NE3_s__sfault_s[0:0]),
    .dw_v(cxdl_NE3_q__dw_v[1:0]),
    .dw_row(cxdl_NE3_q__dw_row[17:0]),
    .dw_d(cxdl_NE3_q__dw_d[1023:0]),
    .fault(cxdl_NE3_q__fault[0:0])
  );
  ot_hbm_su_static_cxport_dl_s #(.QID(3), .G(3)) cxdl_NE3_s (
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .rst_s_n(hb_ckgen__por_stream[0:0]),
    .del_valid(hb_coll_NE__del_valid[3:3]),
    .del_flit(hb_coll_NE__del_flit[2179:1635]),
    .del_obase(hb_coll_NE__hgi_del_obase[159:120]),
    .b0(cxdl_NE3_s__b0[523:0]),
    .b1(cxdl_NE3_s__b1[523:0]),
    .v0(cxdl_NE3_s__v0[7:0]),
    .v1(cxdl_NE3_s__v1[7:0]),
    .sfault_s(cxdl_NE3_s__sfault_s[0:0])
  );
  ot_hbm_su_static_cxport_dl_q cxdl_NW0_q (
    .clk_q(hb_ckgen__pll_stream[0:0]),
    .rst_q_n(hb_ckgen__por_stream[0:0]),
    .b0(cxdl_NW0_s__b0[523:0]),
    .b1(cxdl_NW0_s__b1[523:0]),
    .v0(cxdl_NW0_s__v0[7:0]),
    .v1(cxdl_NW0_s__v1[7:0]),
    .sfault_s(cxdl_NW0_s__sfault_s[0:0]),
    .dw_v(cxdl_NW0_q__dw_v[1:0]),
    .dw_row(cxdl_NW0_q__dw_row[17:0]),
    .dw_d(cxdl_NW0_q__dw_d[1023:0]),
    .fault(cxdl_NW0_q__fault[0:0])
  );
  ot_hbm_su_static_cxport_dl_s #(.QID(2), .G(0)) cxdl_NW0_s (
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .rst_s_n(hb_ckgen__por_stream[0:0]),
    .del_valid(hb_coll_NW__del_valid[0:0]),
    .del_flit(hb_coll_NW__del_flit[544:0]),
    .del_obase(hb_coll_NW__hgi_del_obase[39:0]),
    .b0(cxdl_NW0_s__b0[523:0]),
    .b1(cxdl_NW0_s__b1[523:0]),
    .v0(cxdl_NW0_s__v0[7:0]),
    .v1(cxdl_NW0_s__v1[7:0]),
    .sfault_s(cxdl_NW0_s__sfault_s[0:0])
  );
  ot_hbm_su_static_cxport_dl_q cxdl_NW1_q (
    .clk_q(hb_ckgen__pll_stream[0:0]),
    .rst_q_n(hb_ckgen__por_stream[0:0]),
    .b0(cxdl_NW1_s__b0[523:0]),
    .b1(cxdl_NW1_s__b1[523:0]),
    .v0(cxdl_NW1_s__v0[7:0]),
    .v1(cxdl_NW1_s__v1[7:0]),
    .sfault_s(cxdl_NW1_s__sfault_s[0:0]),
    .dw_v(cxdl_NW1_q__dw_v[1:0]),
    .dw_row(cxdl_NW1_q__dw_row[17:0]),
    .dw_d(cxdl_NW1_q__dw_d[1023:0]),
    .fault(cxdl_NW1_q__fault[0:0])
  );
  ot_hbm_su_static_cxport_dl_s #(.QID(2), .G(1)) cxdl_NW1_s (
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .rst_s_n(hb_ckgen__por_stream[0:0]),
    .del_valid(hb_coll_NW__del_valid[1:1]),
    .del_flit(hb_coll_NW__del_flit[1089:545]),
    .del_obase(hb_coll_NW__hgi_del_obase[79:40]),
    .b0(cxdl_NW1_s__b0[523:0]),
    .b1(cxdl_NW1_s__b1[523:0]),
    .v0(cxdl_NW1_s__v0[7:0]),
    .v1(cxdl_NW1_s__v1[7:0]),
    .sfault_s(cxdl_NW1_s__sfault_s[0:0])
  );
  ot_hbm_su_static_cxport_dl_q cxdl_NW2_q (
    .clk_q(hb_ckgen__pll_stream[0:0]),
    .rst_q_n(hb_ckgen__por_stream[0:0]),
    .b0(cxdl_NW2_s__b0[523:0]),
    .b1(cxdl_NW2_s__b1[523:0]),
    .v0(cxdl_NW2_s__v0[7:0]),
    .v1(cxdl_NW2_s__v1[7:0]),
    .sfault_s(cxdl_NW2_s__sfault_s[0:0]),
    .dw_v(cxdl_NW2_q__dw_v[1:0]),
    .dw_row(cxdl_NW2_q__dw_row[17:0]),
    .dw_d(cxdl_NW2_q__dw_d[1023:0]),
    .fault(cxdl_NW2_q__fault[0:0])
  );
  ot_hbm_su_static_cxport_dl_s #(.QID(2), .G(2)) cxdl_NW2_s (
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .rst_s_n(hb_ckgen__por_stream[0:0]),
    .del_valid(hb_coll_NW__del_valid[2:2]),
    .del_flit(hb_coll_NW__del_flit[1634:1090]),
    .del_obase(hb_coll_NW__hgi_del_obase[119:80]),
    .b0(cxdl_NW2_s__b0[523:0]),
    .b1(cxdl_NW2_s__b1[523:0]),
    .v0(cxdl_NW2_s__v0[7:0]),
    .v1(cxdl_NW2_s__v1[7:0]),
    .sfault_s(cxdl_NW2_s__sfault_s[0:0])
  );
  ot_hbm_su_static_cxport_dl_q cxdl_NW3_q (
    .clk_q(hb_ckgen__pll_stream[0:0]),
    .rst_q_n(hb_ckgen__por_stream[0:0]),
    .b0(cxdl_NW3_s__b0[523:0]),
    .b1(cxdl_NW3_s__b1[523:0]),
    .v0(cxdl_NW3_s__v0[7:0]),
    .v1(cxdl_NW3_s__v1[7:0]),
    .sfault_s(cxdl_NW3_s__sfault_s[0:0]),
    .dw_v(cxdl_NW3_q__dw_v[1:0]),
    .dw_row(cxdl_NW3_q__dw_row[17:0]),
    .dw_d(cxdl_NW3_q__dw_d[1023:0]),
    .fault(cxdl_NW3_q__fault[0:0])
  );
  ot_hbm_su_static_cxport_dl_s #(.QID(2), .G(3)) cxdl_NW3_s (
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .rst_s_n(hb_ckgen__por_stream[0:0]),
    .del_valid(hb_coll_NW__del_valid[3:3]),
    .del_flit(hb_coll_NW__del_flit[2179:1635]),
    .del_obase(hb_coll_NW__hgi_del_obase[159:120]),
    .b0(cxdl_NW3_s__b0[523:0]),
    .b1(cxdl_NW3_s__b1[523:0]),
    .v0(cxdl_NW3_s__v0[7:0]),
    .v1(cxdl_NW3_s__v1[7:0]),
    .sfault_s(cxdl_NW3_s__sfault_s[0:0])
  );
  ot_hbm_su_static_cxport_ij_q #(.SD(0), .SAFE_GATHER(1)) cxij_NE_q (
    .clk_q(hb_ckgen__pll_stream[0:0]),
    .rst_q_n(hb_ckgen__por_stream[0:0]),
    .jb0(cxij_NE_s__jb0[31:0]),
    .jb1(cxij_NE_s__jb1[31:0]),
    .inj_q0(su_NE0__inj_q[1023:0]),
    .inj_q1(su_NE1__inj_q[1023:0]),
    .inj_q2(su_NE2__inj_q[1023:0]),
    .inj_q3(su_NE3__inj_q[1023:0]),
    .ob0(cxij_NE_q__ob0[1023:0]),
    .ob1(cxij_NE_q__ob1[1023:0]),
    .sfault_s(cxij_NE_s__sfault_s[0:0]),
    .ins_coll(cxij_NE_s__ins_coll[0:0]),
    .fault(cxij_NE_q__fault[0:0])
  );
  ot_hbm_su_static_cxport_ij_s #(.QID(3), .B39_NOOP(1), .INJ_RET(9), .RQ(0), .RQC(0), .SD(0), .OBR(0)) cxij_NE_s (
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .rst_s_n(hb_ckgen__por_stream[0:0]),
    .inj_rd(cic_NE__inj_rd_o[1:0]),
    .inj_addr(cic_NE__inj_addr_o[159:0]),
    .inj_d(cxij_NE_s__inj_d[1023:0]),
    .jb0(cxij_NE_s__jb0[31:0]),
    .jb1(cxij_NE_s__jb1[31:0]),
    .ob0(cxij_NE_q__ob0[1023:0]),
    .ob1(cxij_NE_q__ob1[1023:0]),
    .sfault_s(cxij_NE_s__sfault_s[0:0]),
    .ins_coll(cxij_NE_s__ins_coll[0:0])
  );
  ot_hbm_su_static_cxport_ij_q #(.SD(0), .SAFE_GATHER(1)) cxij_NW_q (
    .clk_q(hb_ckgen__pll_stream[0:0]),
    .rst_q_n(hb_ckgen__por_stream[0:0]),
    .jb0(cxij_NW_s__jb0[31:0]),
    .jb1(cxij_NW_s__jb1[31:0]),
    .inj_q0(su_NW0__inj_q[1023:0]),
    .inj_q1(su_NW1__inj_q[1023:0]),
    .inj_q2(su_NW2__inj_q[1023:0]),
    .inj_q3(su_NW3__inj_q[1023:0]),
    .ob0(cxij_NW_q__ob0[1023:0]),
    .ob1(cxij_NW_q__ob1[1023:0]),
    .sfault_s(cxij_NW_s__sfault_s[0:0]),
    .ins_coll(cxij_NW_s__ins_coll[0:0]),
    .fault(cxij_NW_q__fault[0:0])
  );
  ot_hbm_su_static_cxport_ij_s #(.QID(2), .B39_NOOP(1), .INJ_RET(9), .RQ(0), .RQC(0), .SD(0), .OBR(0)) cxij_NW_s (
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .rst_s_n(hb_ckgen__por_stream[0:0]),
    .inj_rd(cic_NW__inj_rd_o[1:0]),
    .inj_addr(cic_NW__inj_addr_o[159:0]),
    .inj_d(cxij_NW_s__inj_d[1023:0]),
    .jb0(cxij_NW_s__jb0[31:0]),
    .jb1(cxij_NW_s__jb1[31:0]),
    .ob0(cxij_NW_q__ob0[1023:0]),
    .ob1(cxij_NW_q__ob1[1023:0]),
    .sfault_s(cxij_NW_s__sfault_s[0:0]),
    .ins_coll(cxij_NW_s__ins_coll[0:0])
  );
  ot_hbm_su_static_cxport_rc_q cxrc_NE_q (
    .clk_q(hb_ckgen__pll_stream[0:0]),
    .rst_q_n(hb_ckgen__por_stream[0:0]),
    .red_sv(sucore_NE__red_sv[0:0]),
    .red_tag(sucore_NE__red_tag[31:0]),
    .red_x(sucore_NE__red_x[31:0]),
    .rr_wv(cxrc_NE_q__rr_wv[0:0]),
    .rr_wa(cxrc_NE_q__rr_wa[4:0]),
    .rr_wd(cxrc_NE_q__rr_wd[255:0]),
    .red_sel({pgp_NE__command[73:70], pgp_NE__command[7:0]}),
    .sfu_x(cxrc_NE_q__sfu_x[31:0]),
    .ob0(cxrc_NE_s__ob0[527:0]),
    .ob1(cxrc_NE_s__ob1[527:0]),
    .rb0(cxrc_NE_s__rb0[267:0]),
    .rb1(cxrc_NE_s__rb1[267:0]),
    .cb0(cxrc_NE_q__cb0[260:0]),
    .cb1(cxrc_NE_q__cb1[260:0]),
    .sfault_s(cxrc_NE_s__sfault_s[0:0]),
    .rc_coll(cxrc_NE_s__rc_coll[0:0]),
    .fault(cxrc_NE_q__fault[0:0])
  );
  ot_hbm_su_static_cxport_rc_s cxrc_NE_s (
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .rst_s_n(hb_ckgen__por_stream[0:0]),
    .rc_v(cxrc_NE_s__rc_v[0:0]),
    .rc_tag(cxrc_NE_s__rc_tag[2:0]),
    .rc_d(cxrc_NE_s__rc_d[255:0]),
    .rr_v(hb_coll_NE__rr_v[0:0]),
    .rr_tag(hb_coll_NE__rr_tag[2:0]),
    .rr_d(hb_coll_NE__rr_d[255:0]),
    .ro_v({sfucore_NE__ro_v_s[3:0], sfucore_NE__ro_v_e[3:0], sfucore_NE__ro_v_n[3:0], sfucore_NE__ro_v_w[3:0]}),
    .ro_x({sfucore_NE__ro_x_s[127:0], sfucore_NE__ro_x_e[127:0], sfucore_NE__ro_x_n[127:0], sfucore_NE__ro_x_w[127:0]}),
    .ob0(cxrc_NE_s__ob0[527:0]),
    .ob1(cxrc_NE_s__ob1[527:0]),
    .rb0(cxrc_NE_s__rb0[267:0]),
    .rb1(cxrc_NE_s__rb1[267:0]),
    .cb0(cxrc_NE_q__cb0[260:0]),
    .cb1(cxrc_NE_q__cb1[260:0]),
    .sfault_s(cxrc_NE_s__sfault_s[0:0]),
    .rc_coll(cxrc_NE_s__rc_coll[0:0])
  );
  ot_hbm_su_static_cxport_rc_q cxrc_NW_q (
    .clk_q(hb_ckgen__pll_stream[0:0]),
    .rst_q_n(hb_ckgen__por_stream[0:0]),
    .red_sv(sucore_NW__red_sv[0:0]),
    .red_tag(sucore_NW__red_tag[31:0]),
    .red_x(sucore_NW__red_x[31:0]),
    .rr_wv(cxrc_NW_q__rr_wv[0:0]),
    .rr_wa(cxrc_NW_q__rr_wa[4:0]),
    .rr_wd(cxrc_NW_q__rr_wd[255:0]),
    .red_sel({pgp_NW__command[73:70], pgp_NW__command[7:0]}),
    .sfu_x(cxrc_NW_q__sfu_x[31:0]),
    .ob0(cxrc_NW_s__ob0[527:0]),
    .ob1(cxrc_NW_s__ob1[527:0]),
    .rb0(cxrc_NW_s__rb0[267:0]),
    .rb1(cxrc_NW_s__rb1[267:0]),
    .cb0(cxrc_NW_q__cb0[260:0]),
    .cb1(cxrc_NW_q__cb1[260:0]),
    .sfault_s(cxrc_NW_s__sfault_s[0:0]),
    .rc_coll(cxrc_NW_s__rc_coll[0:0]),
    .fault(cxrc_NW_q__fault[0:0])
  );
  ot_hbm_su_static_cxport_rc_s cxrc_NW_s (
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .rst_s_n(hb_ckgen__por_stream[0:0]),
    .rc_v(cxrc_NW_s__rc_v[0:0]),
    .rc_tag(cxrc_NW_s__rc_tag[2:0]),
    .rc_d(cxrc_NW_s__rc_d[255:0]),
    .rr_v(hb_coll_NW__rr_v[0:0]),
    .rr_tag(hb_coll_NW__rr_tag[2:0]),
    .rr_d(hb_coll_NW__rr_d[255:0]),
    .ro_v({sfucore_NW__ro_v_s[3:0], sfucore_NW__ro_v_e[3:0], sfucore_NW__ro_v_n[3:0], sfucore_NW__ro_v_w[3:0]}),
    .ro_x({sfucore_NW__ro_x_s[127:0], sfucore_NW__ro_x_e[127:0], sfucore_NW__ro_x_n[127:0], sfucore_NW__ro_x_w[127:0]}),
    .ob0(cxrc_NW_s__ob0[527:0]),
    .ob1(cxrc_NW_s__ob1[527:0]),
    .rb0(cxrc_NW_s__rb0[267:0]),
    .rb1(cxrc_NW_s__rb1[267:0]),
    .cb0(cxrc_NW_q__cb0[260:0]),
    .cb1(cxrc_NW_q__cb1[260:0]),
    .sfault_s(cxrc_NW_s__sfault_s[0:0]),
    .rc_coll(cxrc_NW_s__rc_coll[0:0])
  );
  hfd_ep_static_vc2 #(.IDLE_K(204), .HQ(4)) ep_N0 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .tx_v(hb_coll_NW__tx_pin_v[0:0]),
    .tx_frame(hb_coll_NW__tx_pin_flit[611:0]),
    .rx_arm_v(epcal_NW__payload[0:0]),
    .rx_arm_bank(epcal_NW__payload[1:1]),
    .rx_block_words(epcal_NW__payload[8:2]),
    .rx_release_v(epcal_NW__payload[9:9]),
    .rx_release_bank(epcal_NW__payload[10:10]),
    .rx_slot_v(epcal_NW__payload[11:11]),
    .rx_slot_bank(epcal_NW__payload[12:12]),
    .rx_slot_index(epcal_NW__payload[18:13]),
    .rx_pin_v(ep_N0__rx_pin_v[0:0]),
    .rx_pin_flit(ep_N0__rx_pin_flit[611:0]),
    .rx_block_ready(ep_N0__rx_block_ready[1:0]),
    .phy_up(ep_N0__phy_up[0:0]),
    .fault(ep_N0__fault[0:0]),
    .fault_cause(ep_N0__fault_cause[10:0]),
    .sd_tx(ep_N0__sd_tx[511:0]),
    .sd_rx(lk_N0__rx[511:0]),
    .sd_st(lk_N0__st[1:0]),
    .h_tx_v(host_ep__vc_tx_v[0:0]),
    .h_tx_frame(host_ep__vc_tx_frame[611:0]),
    .h_rx_v(ep_N0__h_rx_v[0:0]),
    .h_rx_frame(ep_N0__h_rx_frame[611:0]),
    .h_up(ep_N0__h_up[0:0]),
    .h_cause(ep_N0__h_cause[2:0])
  );
  hfd_ep_static ep_N2 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .tx_v(hb_coll_NE__tx_pin_v[0:0]),
    .tx_frame(hb_coll_NE__tx_pin_flit[611:0]),
    .rx_arm_v(epcal_NE__payload[0:0]),
    .rx_arm_bank(epcal_NE__payload[1:1]),
    .rx_block_words(epcal_NE__payload[8:2]),
    .rx_release_v(epcal_NE__payload[9:9]),
    .rx_release_bank(epcal_NE__payload[10:10]),
    .rx_slot_v(epcal_NE__payload[11:11]),
    .rx_slot_bank(epcal_NE__payload[12:12]),
    .rx_slot_index(epcal_NE__payload[18:13]),
    .rx_pin_v(ep_N2__rx_pin_v[0:0]),
    .rx_pin_flit(ep_N2__rx_pin_flit[611:0]),
    .rx_block_ready(ep_N2__rx_block_ready[1:0]),
    .phy_up(ep_N2__phy_up[0:0]),
    .fault(ep_N2__fault[0:0]),
    .fault_cause(ep_N2__fault_cause[10:0]),
    .sd_tx(ep_N2__sd_tx[511:0]),
    .sd_rx(lk_N2__rx[511:0]),
    .sd_st(lk_N2__st[1:0])
  );
  hfd_ep_static ep_S0 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .tx_v(hb_coll_NW__tx_pin_v[1:1]),
    .tx_frame(hb_coll_NW__tx_pin_flit[1223:612]),
    .rx_arm_v(epcal_NW__payload[19:19]),
    .rx_arm_bank(epcal_NW__payload[20:20]),
    .rx_block_words(epcal_NW__payload[27:21]),
    .rx_release_v(epcal_NW__payload[28:28]),
    .rx_release_bank(epcal_NW__payload[29:29]),
    .rx_slot_v(epcal_NW__payload[30:30]),
    .rx_slot_bank(epcal_NW__payload[31:31]),
    .rx_slot_index(epcal_NW__payload[37:32]),
    .rx_pin_v(ep_S0__rx_pin_v[0:0]),
    .rx_pin_flit(ep_S0__rx_pin_flit[611:0]),
    .rx_block_ready(ep_S0__rx_block_ready[1:0]),
    .phy_up(ep_S0__phy_up[0:0]),
    .fault(ep_S0__fault[0:0]),
    .fault_cause(ep_S0__fault_cause[10:0]),
    .sd_tx(ep_S0__sd_tx[511:0]),
    .sd_rx(lk_S0__rx[511:0]),
    .sd_st(lk_S0__st[1:0])
  );
  hfd_ep_static ep_S1 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .tx_v(b2_ep1_root__tx_o[612:612]),
    .tx_frame(b2_ep1_root__tx_o[611:0]),
    .rx_arm_v(b2_ep1_root__tx_o[613:613]),
    .rx_arm_bank(b2_ep1_root__tx_o[614:614]),
    .rx_block_words(b2_ep1_root__tx_o[621:615]),
    .rx_release_v(b2_ep1_root__tx_o[622:622]),
    .rx_release_bank(b2_ep1_root__tx_o[623:623]),
    .rx_slot_v(b2_ep1_root__tx_o[624:624]),
    .rx_slot_bank(b2_ep1_root__tx_o[625:625]),
    .rx_slot_index(b2_ep1_root__tx_o[631:626]),
    .rx_pin_v(ep_S1__rx_pin_v[0:0]),
    .rx_pin_flit(ep_S1__rx_pin_flit[611:0]),
    .rx_block_ready(ep_S1__rx_block_ready[1:0]),
    .phy_up(ep_S1__phy_up[0:0]),
    .fault(ep_S1__fault[0:0]),
    .fault_cause(ep_S1__fault_cause[10:0]),
    .sd_tx(ep_S1__sd_tx[511:0]),
    .sd_rx(lk_S1__rx[511:0]),
    .sd_st(lk_S1__st[1:0])
  );
  hfd_ep_static ep_S3 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .tx_v(hb_coll_NE__tx_pin_v[1:1]),
    .tx_frame(hb_coll_NE__tx_pin_flit[1223:612]),
    .rx_arm_v(epcal_NE__payload[19:19]),
    .rx_arm_bank(epcal_NE__payload[20:20]),
    .rx_block_words(epcal_NE__payload[27:21]),
    .rx_release_v(epcal_NE__payload[28:28]),
    .rx_release_bank(epcal_NE__payload[29:29]),
    .rx_slot_v(epcal_NE__payload[30:30]),
    .rx_slot_bank(epcal_NE__payload[31:31]),
    .rx_slot_index(epcal_NE__payload[37:32]),
    .rx_pin_v(ep_S3__rx_pin_v[0:0]),
    .rx_pin_flit(ep_S3__rx_pin_flit[611:0]),
    .rx_block_ready(ep_S3__rx_block_ready[1:0]),
    .phy_up(ep_S3__phy_up[0:0]),
    .fault(ep_S3__fault[0:0]),
    .fault_cause(ep_S3__fault_cause[10:0]),
    .sd_tx(ep_S3__sd_tx[511:0]),
    .sd_rx(lk_S3__rx[511:0]),
    .sd_st(lk_S3__st[1:0])
  );
  hfd_hgi_vm_calendar_f20_role #(.W(38)) epcal_NE (
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_cap(hb_ckgen__pll_stream[0:0]),
    .clk_mem(hb_ckgen__pll_stream[0:0]),
    .clk_tgt(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .tgt(8'b10000111),
    .cfg_v(hleaf_NE__b_cfg_v[0:0]),
    .cfg_target(hleaf_NE__b_cfg_target[7:0]),
    .cfg_addr(hleaf_NE__b_cfg_addr[11:0]),
    .cfg_data(hleaf_NE__b_cfg_data[255:0]),
    .desc_v(hleaf_NE__b_desc_v[0:0]),
    .desc_base(hleaf_NE__b_desc_base[11:0]),
    .desc_limit(hleaf_NE__b_desc_limit[12:0]),
    .desc_loops(hleaf_NE__b_desc_loops[15:0]),
    .launch_v(hleaf_NE__b_launch_v[0:0]),
    .tgt_configured(epcal_NE__tgt_configured[0:0]),
    .tgt_fault(epcal_NE__tgt_fault[0:0]),
    .calendar_v(epcal_NE__calendar_v[0:0]),
    .active(epcal_NE__active[0:0]),
    .done(epcal_NE__done[0:0]),
    .fault(epcal_NE__fault[0:0]),
    .ordinal(epcal_NE__ordinal[31:0]),
    .payload(epcal_NE__payload[37:0])
  );
  hfd_hgi_vm_calendar_f20_role #(.W(57)) epcal_NW (
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_cap(hb_ckgen__pll_stream[0:0]),
    .clk_mem(hb_ckgen__pll_stream[0:0]),
    .clk_tgt(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .tgt(8'b10000110),
    .cfg_v(hleaf_NW__b_cfg_v[0:0]),
    .cfg_target(hleaf_NW__b_cfg_target[7:0]),
    .cfg_addr(hleaf_NW__b_cfg_addr[11:0]),
    .cfg_data(hleaf_NW__b_cfg_data[255:0]),
    .desc_v(hleaf_NW__b_desc_v[0:0]),
    .desc_base(hleaf_NW__b_desc_base[11:0]),
    .desc_limit(hleaf_NW__b_desc_limit[12:0]),
    .desc_loops(hleaf_NW__b_desc_loops[15:0]),
    .launch_v(hleaf_NW__b_launch_v[0:0]),
    .tgt_configured(epcal_NW__tgt_configured[0:0]),
    .tgt_fault(epcal_NW__tgt_fault[0:0]),
    .calendar_v(epcal_NW__calendar_v[0:0]),
    .active(epcal_NW__active[0:0]),
    .done(epcal_NW__done[0:0]),
    .fault(epcal_NW__fault[0:0]),
    .ordinal(epcal_NW__ordinal[31:0]),
    .payload(epcal_NW__payload[56:0])
  );
  ot_hbm_fault_leaf #(.N(6), .SYNC_MASK(64'h3f)) fcx_NE (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .in({cxrc_NE_q__fault[0:0], cxij_NE_q__fault[0:0], cxdl_NE3_q__fault[0:0], cxdl_NE2_q__fault[0:0], cxdl_NE1_q__fault[0:0], cxdl_NE0_q__fault[0:0]}),
    .fault(fcx_NE__fault[0:0])
  );
  ot_hbm_fault_leaf #(.N(6), .SYNC_MASK(64'h3f)) fcx_NW (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .in({cxrc_NW_q__fault[0:0], cxij_NW_q__fault[0:0], cxdl_NW3_q__fault[0:0], cxdl_NW2_q__fault[0:0], cxdl_NW1_q__fault[0:0], cxdl_NW0_q__fault[0:0]}),
    .fault(fcx_NW__fault[0:0])
  );
  ot_hbm_fault_leaf #(.N(4), .SYNC_MASK(64'h8)) fl_NE0 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .in({su_NE0__fault[0:0], hc_NE0__fault[0:0], sfu_NE0__fault[0:0], su_NE0__lg_fault[0:0]}),
    .fault(fl_NE0__fault[0:0])
  );
  ot_hbm_fault_leaf #(.N(5), .SYNC_MASK(64'h8)) fl_NE1 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .in({fl_NE0__fault[0:0], su_NE1__fault[0:0], hc_NE1__fault[0:0], sfu_NE1__fault[0:0], su_NE1__lg_fault[0:0]}),
    .fault(fl_NE1__fault[0:0])
  );
  ot_hbm_fault_leaf #(.N(5), .SYNC_MASK(64'h8)) fl_NE2 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .in({fl_NE1__fault[0:0], su_NE2__fault[0:0], hc_NE2__fault[0:0], sfu_NE2__fault[0:0], su_NE2__lg_fault[0:0]}),
    .fault(fl_NE2__fault[0:0])
  );
  ot_hbm_fault_leaf #(.N(5), .SYNC_MASK(64'h8)) fl_NE3 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .in({fl_NE2__fault[0:0], su_NE3__fault[0:0], hc_NE3__fault[0:0], sfu_NE3__fault[0:0], su_NE3__lg_fault[0:0]}),
    .fault(fl_NE3__fault[0:0])
  );
  ot_hbm_fault_leaf #(.N(4), .SYNC_MASK(64'h8)) fl_NW0 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .in({su_NW0__fault[0:0], hc_NW0__fault[0:0], sfu_NW0__fault[0:0], su_NW0__lg_fault[0:0]}),
    .fault(fl_NW0__fault[0:0])
  );
  ot_hbm_fault_leaf #(.N(5), .SYNC_MASK(64'h8)) fl_NW1 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .in({fl_NW0__fault[0:0], su_NW1__fault[0:0], hc_NW1__fault[0:0], sfu_NW1__fault[0:0], su_NW1__lg_fault[0:0]}),
    .fault(fl_NW1__fault[0:0])
  );
  ot_hbm_fault_leaf #(.N(5), .SYNC_MASK(64'h8)) fl_NW2 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .in({fl_NW1__fault[0:0], su_NW2__fault[0:0], hc_NW2__fault[0:0], sfu_NW2__fault[0:0], su_NW2__lg_fault[0:0]}),
    .fault(fl_NW2__fault[0:0])
  );
  ot_hbm_fault_leaf #(.N(5), .SYNC_MASK(64'h8)) fl_NW3 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .in({fl_NW2__fault[0:0], su_NW3__fault[0:0], hc_NW3__fault[0:0], sfu_NW3__fault[0:0], su_NW3__lg_fault[0:0]}),
    .fault(fl_NW3__fault[0:0])
  );
  ot_hbm_fault_leaf #(.N(14), .SYNC_MASK(64'h40)) fr_NE (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .in({hb_vms_NE__vmstat[18:16], cij_NE__fault[0:0], fs_NE__fault[0:0], hb_dbk_NE__mv_fault[0:0], fl_NE3__fault[0:0], sucore_NE__fault[0:0], hb_argmax__nan_flag[0:0], hb_coll_NE__retry_requested[1:0], hb_vms_NE__ring_fault[2:0]}),
    .fault(fr_NE__fault[0:0])
  );
  ot_hbm_fault_leaf #(.N(14), .SYNC_MASK(64'h80)) fr_NW (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .in({hb_vms_NW__vmstat[18:16], cij_NW__fault[0:0], fs_NW__fault[0:0], fl_NW3__fault[0:0], sucore_NW__fault[0:0], hb_dbk_NW__mv_fault[0:0], hb_coll_NW__retry_requested[2:0], hb_vms_NW__ring_fault[2:0]}),
    .fault(fr_NW__fault[0:0])
  );
  ot_hbm_fault_leaf_n8_s0 fs_NE (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .in({sfault_NE__status[6:0], sfault_NE__fault[0:0]}),
    .fault(fs_NE__fault[0:0])
  );
  ot_hbm_fault_leaf_n8_s0 fs_NW (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .in({sfault_NW__status[6:0], sfault_NW__fault[0:0]}),
    .fault(fs_NW__fault[0:0])
  );
  ot_hbm_argmax_static_sw_vm_r2 #(.TP(192), .VMX(89), .ACK(52)) hb_argmax (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .die_id(col_idx__prm[74:67]),
    .go(col_idx__go[1:1]),
    .mode(col_idx__rec[0:0]),
    .imm_a(col_idx__rec[18:1]),
    .a_mirror(col_idx__rec[19:19]),
    .a_base(col_idx__rec[37:20]),
    .n(col_idx__rec[55:38]),
    .o_base(col_idx__rec[73:56]),
    .o_is(col_idx__rec[89:74]),
    .vm_rq(hb_argmax__vm_rq[135:0]),
    .vm_rr(hb_idx__ctl__argmax_m[263:0]),
    .cq(hb_argmax__cq[337:0]),
    .cq_seq(hb_argmax__cq_seq[1:0]),
    .cr(hb_vms_SW__cr[273:0]),
    .busy(hb_argmax__busy[0:0]),
    .done(hb_argmax__done[0:0]),
    .fault(hb_argmax__fault[0:0]),
    .nan_flag(hb_argmax__nan_flag[0:0])
  );
  hfd_ckgen_nolink hb_ckgen (
    .refclk(hb_ckgen__refclk[0:0]),
    .por_n(hb_ckgen__por_n[0:0]),
    .pll_stream(hb_ckgen__pll_stream[0:0]),
    .pll_serial(hb_ckgen__pll_serial[0:0]),
    .pll_hbm(hb_ckgen__pll_hbm[0:0]),
    .por_stream(hb_ckgen__por_stream[0:0]),
    .por_serial(hb_ckgen__por_serial[0:0]),
    .por_hbm(hb_ckgen__por_hbm[0:0])
  );
  ot_hfd_coll_q2_hard_v8g #(.NLINK(2), .TP(192), .AR_ITER(1), .ROWS(256), .VM_RT(3)) hb_coll_NE (
    .rst_n(hb_ckgen__por_stream[0:0]),
    .qid(2'b11),
    .clk_program(hb_ckgen__pll_stream[0:0]),
    .clk_control(hb_ckgen__pll_stream[0:0]),
    .clk_vmasm({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .clk_upipe({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .clk_issue(hb_ckgen__pll_stream[0:0]),
    .clk_qslots({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .clk_ring({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .clk_reduce({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .clk_vmwrite({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .clk_link({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .cfg_v(hleaf_NE__a_cfg_v[0:0]),
    .cfg_target(hleaf_NE__a_cfg_target[7:0]),
    .cfg_addr(hleaf_NE__a_cfg_addr[11:0]),
    .cfg_data(hleaf_NE__a_cfg_data[255:0]),
    .desc_v(hleaf_NE__a_desc_v[0:0]),
    .desc_base(hleaf_NE__a_desc_base[11:0]),
    .desc_limit(hleaf_NE__a_desc_limit[12:0]),
    .desc_loops(hleaf_NE__a_desc_loops[15:0]),
    .launch_v(hleaf_NE__a_launch_v[0:0]),
    .program_configured(hb_coll_NE__program_configured[0:0]),
    .program_init_busy(hb_coll_NE__program_init_busy[0:0]),
    .program_fault(hb_coll_NE__program_fault[0:0]),
    .hgi_busy(hb_coll_NE__hgi_busy[0:0]),
    .hgi_done(hb_coll_NE__hgi_done[0:0]),
    .hgi_fault(hb_coll_NE__hgi_fault[0:0]),
    .inj_rd(hb_coll_NE__inj_rd[1:0]),
    .inj_idx(hb_coll_NE__inj_idx[31:0]),
    .hgi_inj_addr(hb_coll_NE__hgi_inj_addr[159:0]),
    .inj_d({cij_NE__inj_d_r1[511:256], cij_NE__inj_d_r0[511:256], cij_NE__inj_d_r1[255:0], cij_NE__inj_d_r0[255:0]}),
    .del_valid(hb_coll_NE__del_valid[3:0]),
    .del_flit(hb_coll_NE__del_flit[2179:0]),
    .hgi_del_obase(hb_coll_NE__hgi_del_obase[159:0]),
    .rc_v(cxrc_NE_s__rc_v[0:0]),
    .rc_tag(cxrc_NE_s__rc_tag[2:0]),
    .rc_d(cxrc_NE_s__rc_d[255:0]),
    .rr_v(hb_coll_NE__rr_v[0:0]),
    .rr_tag(hb_coll_NE__rr_tag[2:0]),
    .rr_d(hb_coll_NE__rr_d[255:0]),
    .phy_up({ep_S3__phy_up[0:0], ep_N2__phy_up[0:0]}),
    .tx_pin_v(hb_coll_NE__tx_pin_v[1:0]),
    .tx_pin_flit(hb_coll_NE__tx_pin_flit[1223:0]),
    .rx_pin_v({ep_S3__rx_pin_v[0:0], ep_N2__rx_pin_v[0:0]}),
    .rx_pin_flit({ep_S3__rx_pin_flit[611:0], ep_N2__rx_pin_flit[611:0]}),
    .retry_requested(hb_coll_NE__retry_requested[1:0]),
    .pr_cw_i(hb_coll_NW__pr_cw_o[279:0]),
    .pr_ccw_i(hb_coll_NW__pr_ccw_o[279:0]),
    .pr_cw_o(hb_coll_NE__pr_cw_o[279:0]),
    .pr_ccw_o(hb_coll_NE__pr_ccw_o[279:0]),
    .isa_ring(hb_coll_NE__isa_ring[57:0]),
    .isa_lp_data(hb_coll_NE__isa_lp_data[255:0]),
    .ra_lp_we(hcollgi_NE__ra_lp_we[0:0]),
    .ra_lp_tag(hcollgi_NE__ra_lp_tag[2:0]),
    .ra_lp_data(hcollgi_NE__ra_lp_data[255:0]),
    .ra_state_read_add(hcollgi_NE__ra_state_read_add[0:0]),
    .ra_state_read_tx(hcollgi_NE__ra_state_read_tx[0:0]),
    .ra_state_read_rr(hcollgi_NE__ra_state_read_rr[0:0]),
    .ra_state_add_tag(hcollgi_NE__ra_state_add_tag[2:0]),
    .ra_state_tx_tag(hcollgi_NE__ra_state_tx_tag[2:0]),
    .ra_state_rr_tag(hcollgi_NE__ra_state_rr_tag[2:0]),
    .ra_state_add_src(hcollgi_NE__ra_state_add_src[1:0]),
    .ra_state_add_rhs_acc(hcollgi_NE__ra_state_add_rhs_acc[0:0]),
    .ra_state_tx_acc(hcollgi_NE__ra_state_tx_acc[0:0]),
    .ra_add_v(hcollgi_NE__ra_add_v[0:0]),
    .ra_add_tag(hcollgi_NE__ra_add_tag[2:0]),
    .ra_add_src(hcollgi_NE__ra_add_src[1:0]),
    .ra_add_rhs_acc(hcollgi_NE__ra_add_rhs_acc[0:0]),
    .ra_tx_inject(hcollgi_NE__ra_tx_inject[1:0]),
    .ra_tx_forward(hcollgi_NE__ra_tx_forward[1:0]),
    .ra_tx_tag(hcollgi_NE__ra_tx_tag[2:0]),
    .ra_tx_dst(hcollgi_NE__ra_tx_dst[1:0]),
    .ra_tx_result(hcollgi_NE__ra_tx_result[0:0]),
    .ra_tx_acc(hcollgi_NE__ra_tx_acc[0:0]),
    .ra_tx_gather(hcollgi_NE__ra_tx_gather[0:0]),
    .ra_tx_ttl(hcollgi_NE__ra_tx_ttl[3:0]),
    .ra_rx_slot(hcollgi_NE__ra_rx_slot[1:0]),
    .ra_rx_kind(hcollgi_NE__ra_rx_kind[3:0]),
    .ra_rx_src(hcollgi_NE__ra_rx_src[3:0]),
    .ra_rx_tag(hcollgi_NE__ra_rx_tag[5:0]),
    .ra_rr_local(hcollgi_NE__ra_rr_local[0:0]),
    .ra_rr_local_tag(hcollgi_NE__ra_rr_local_tag[2:0]),
    .ag_v(hb_coll_NE__ag_v[1:0]),
    .ag_src(hb_coll_NE__ag_src[3:0]),
    .ag_tag(hb_coll_NE__ag_tag[5:0]),
    .ag_d(hb_coll_NE__ag_d[511:0]),
    .vm_rq(hb_coll_NE__vm_rq[135:0]),
    .vm_rr(hcollrs_NE__a_rr[2055:0]),
    .vm_kq(hb_coll_NE__vm_kq[2247:0]),
    .fault(hb_coll_NE__fault[0:0]),
    .fault_cause(hb_coll_NE__fault_cause[15:0]),
    .done(hb_coll_NE__done[0:0]),
    .stat_cycles(hb_coll_NE__stat_cycles[31:0])
  );
  ot_hfd_coll_q3_hard_v8x #(.NLINK(3), .TP(192), .AR_ITER(1), .ROWS(256), .VM_RT(3)) hb_coll_NW (
    .rst_n(hb_ckgen__por_stream[0:0]),
    .qid(2'b10),
    .clk_program(hb_ckgen__pll_stream[0:0]),
    .clk_control(hb_ckgen__pll_stream[0:0]),
    .clk_vmasm({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .clk_upipe({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .clk_issue(hb_ckgen__pll_stream[0:0]),
    .clk_qslots({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .clk_ring({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .clk_reduce({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .clk_vmwrite({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .clk_link({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .cfg_v(hleaf_NW__a_cfg_v[0:0]),
    .cfg_target(hleaf_NW__a_cfg_target[7:0]),
    .cfg_addr(hleaf_NW__a_cfg_addr[11:0]),
    .cfg_data(hleaf_NW__a_cfg_data[255:0]),
    .desc_v(hleaf_NW__a_desc_v[0:0]),
    .desc_base(hleaf_NW__a_desc_base[11:0]),
    .desc_limit(hleaf_NW__a_desc_limit[12:0]),
    .desc_loops(hleaf_NW__a_desc_loops[15:0]),
    .launch_v(hleaf_NW__a_launch_v[0:0]),
    .program_configured(hb_coll_NW__program_configured[0:0]),
    .program_init_busy(hb_coll_NW__program_init_busy[0:0]),
    .program_fault(hb_coll_NW__program_fault[0:0]),
    .hgi_busy(hb_coll_NW__hgi_busy[0:0]),
    .hgi_done(hb_coll_NW__hgi_done[0:0]),
    .hgi_fault(hb_coll_NW__hgi_fault[0:0]),
    .inj_rd(hb_coll_NW__inj_rd[1:0]),
    .inj_idx(hb_coll_NW__inj_idx[31:0]),
    .hgi_inj_addr(hb_coll_NW__hgi_inj_addr[159:0]),
    .inj_d({cij_NW__inj_d_r1[511:256], cij_NW__inj_d_r0[511:256], cij_NW__inj_d_r1[255:0], cij_NW__inj_d_r0[255:0]}),
    .del_valid(hb_coll_NW__del_valid[3:0]),
    .del_flit(hb_coll_NW__del_flit[2179:0]),
    .hgi_del_obase(hb_coll_NW__hgi_del_obase[159:0]),
    .rc_v(cxrc_NW_s__rc_v[0:0]),
    .rc_tag(cxrc_NW_s__rc_tag[2:0]),
    .rc_d(cxrc_NW_s__rc_d[255:0]),
    .rr_v(hb_coll_NW__rr_v[0:0]),
    .rr_tag(hb_coll_NW__rr_tag[2:0]),
    .rr_d(hb_coll_NW__rr_d[255:0]),
    .phy_up({b2_ep1_root__rx_o[613:613], ep_S0__phy_up[0:0], ep_N0__phy_up[0:0]}),
    .tx_pin_v(hb_coll_NW__tx_pin_v[2:0]),
    .tx_pin_flit(hb_coll_NW__tx_pin_flit[1835:0]),
    .rx_pin_v({b2_ep1_root__rx_o[612:612], ep_S0__rx_pin_v[0:0], ep_N0__rx_pin_v[0:0]}),
    .rx_pin_flit({b2_ep1_root__rx_o[611:0], ep_S0__rx_pin_flit[611:0], ep_N0__rx_pin_flit[611:0]}),
    .retry_requested(hb_coll_NW__retry_requested[2:0]),
    .pr_cw_i(hb_coll_NE__pr_cw_o[279:0]),
    .pr_ccw_i(hb_coll_NE__pr_ccw_o[279:0]),
    .pr_cw_o(hb_coll_NW__pr_cw_o[279:0]),
    .pr_ccw_o(hb_coll_NW__pr_ccw_o[279:0]),
    .isa_ring(hb_coll_NW__isa_ring[57:0]),
    .isa_lp_data(hb_coll_NW__isa_lp_data[255:0]),
    .ra_lp_we(hcollgi_NW__ra_lp_we[0:0]),
    .ra_lp_tag(hcollgi_NW__ra_lp_tag[2:0]),
    .ra_lp_data(hcollgi_NW__ra_lp_data[255:0]),
    .ra_state_read_add(hcollgi_NW__ra_state_read_add[0:0]),
    .ra_state_read_tx(hcollgi_NW__ra_state_read_tx[0:0]),
    .ra_state_read_rr(hcollgi_NW__ra_state_read_rr[0:0]),
    .ra_state_add_tag(hcollgi_NW__ra_state_add_tag[2:0]),
    .ra_state_tx_tag(hcollgi_NW__ra_state_tx_tag[2:0]),
    .ra_state_rr_tag(hcollgi_NW__ra_state_rr_tag[2:0]),
    .ra_state_add_src(hcollgi_NW__ra_state_add_src[1:0]),
    .ra_state_add_rhs_acc(hcollgi_NW__ra_state_add_rhs_acc[0:0]),
    .ra_state_tx_acc(hcollgi_NW__ra_state_tx_acc[0:0]),
    .ra_add_v(hcollgi_NW__ra_add_v[0:0]),
    .ra_add_tag(hcollgi_NW__ra_add_tag[2:0]),
    .ra_add_src(hcollgi_NW__ra_add_src[1:0]),
    .ra_add_rhs_acc(hcollgi_NW__ra_add_rhs_acc[0:0]),
    .ra_tx_inject(hcollgi_NW__ra_tx_inject[1:0]),
    .ra_tx_forward(hcollgi_NW__ra_tx_forward[1:0]),
    .ra_tx_tag(hcollgi_NW__ra_tx_tag[2:0]),
    .ra_tx_dst(hcollgi_NW__ra_tx_dst[1:0]),
    .ra_tx_result(hcollgi_NW__ra_tx_result[0:0]),
    .ra_tx_acc(hcollgi_NW__ra_tx_acc[0:0]),
    .ra_tx_gather(hcollgi_NW__ra_tx_gather[0:0]),
    .ra_tx_ttl(hcollgi_NW__ra_tx_ttl[3:0]),
    .ra_rx_slot(hcollgi_NW__ra_rx_slot[1:0]),
    .ra_rx_kind(hcollgi_NW__ra_rx_kind[3:0]),
    .ra_rx_src(hcollgi_NW__ra_rx_src[3:0]),
    .ra_rx_tag(hcollgi_NW__ra_rx_tag[5:0]),
    .ra_rr_local(hcollgi_NW__ra_rr_local[0:0]),
    .ra_rr_local_tag(hcollgi_NW__ra_rr_local_tag[2:0]),
    .ag_v(hb_coll_NW__ag_v[1:0]),
    .ag_src(hb_coll_NW__ag_src[3:0]),
    .ag_tag(hb_coll_NW__ag_tag[5:0]),
    .ag_d(hb_coll_NW__ag_d[511:0]),
    .vm_rq(hb_coll_NW__vm_rq[135:0]),
    .vm_rr(hcollrs_NW__a_rr[2055:0]),
    .vm_kq(hb_coll_NW__vm_kq[2247:0]),
    .fault(hb_coll_NW__fault[0:0]),
    .fault_cause(hb_coll_NW__fault_cause[15:0]),
    .done(hb_coll_NW__done[0:0]),
    .stat_cycles(hb_coll_NW__stat_cycles[31:0]),
    .clk_arg(hb_ckgen__pll_stream[0:0]),
    .tkx_w_v(tkm_SW__w_v[0:0]),
    .tkx_w_addr(tkm_SW__w_addr[39:0]),
    .tkx_w_mask(tkm_SW__w_mask[15:0]),
    .tkx_w_data(tkm_SW__w_data[511:0]),
    .tkx_busy(tkm_SW__busy[0:0]),
    .tkx_done(tkm_SW__done[0:0]),
    .tkx_fault(tkm_SW__fault[0:0]),
    .tkx_start(hb_coll_NW__tkx_start[0:0]),
    .tkx_arg_mode(hb_coll_NW__tkx_arg_mode[0:0]),
    .tkx_cfg_n(hb_coll_NW__tkx_cfg_n[11:0]),
    .tkx_cfg_k(hb_coll_NW__tkx_cfg_k[12:0]),
    .tkx_cfg_nout(hb_coll_NW__tkx_cfg_nout[12:0]),
    .tkx_cfg_g(hb_coll_NW__tkx_cfg_g[7:0]),
    .tkx_cfg_gbase(hb_coll_NW__tkx_cfg_gbase[7:0]),
    .tkx_cfg_pf(hb_coll_NW__tkx_cfg_pf[15:0]),
    .tkx_cfg_obase(hb_coll_NW__tkx_cfg_obase[39:0]),
    .tkx_cfg_rbase(hb_coll_NW__tkx_cfg_rbase[39:0]),
    .tkx_cfg_has_r(hb_coll_NW__tkx_cfg_has_r[0:0]),
    .tkx_del_slot(hb_coll_NW__tkx_del_slot[3:0]),
    .tkx_del_valid(hb_coll_NW__tkx_del_valid[3:0]),
    .tkx_del_flit(hb_coll_NW__tkx_del_flit[2179:0])
  );
  ot_hgi_dma_back_static_vp4_banks_cp #(.RR_RT(80)) hb_dbk_NE (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .clk_cp(hb_ckgen__pll_stream[0:0]),
    .clk_rst(hb_ckgen__pll_stream[0:0]),
    .stk(2'b10),
    .tgt(8'b01101011),
    .clk_bank({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .cfg_v(hleaf_NE__b_cfg_v[0:0]),
    .cfg_target(hleaf_NE__b_cfg_target[7:0]),
    .cfg_addr(hleaf_NE__b_cfg_addr[11:0]),
    .cfg_data(hleaf_NE__b_cfg_data[255:0]),
    .desc_v(hleaf_NE__b_desc_v[0:0]),
    .desc_base(hleaf_NE__b_desc_base[11:0]),
    .desc_limit(hleaf_NE__b_desc_limit[12:0]),
    .desc_loops(hleaf_NE__b_desc_loops[15:0]),
    .launch_v(hleaf_NE__b_launch_v[0:0]),
    .cp_configured(hb_dbk_NE__cp_configured[0:0]),
    .cp_fault(hb_dbk_NE__cp_fault[0:0]),
    .cp_active(hb_dbk_NE__cp_active[0:0]),
    .mv_src(hb_dbk_NE__mv_src[0:0]),
    .mv_done(hb_dbk_NE__mv_done[0:0]),
    .mv_fault(hb_dbk_NE__mv_fault[0:0]),
    .quiet(hb_dbk_NE__quiet[0:0]),
    .busy(hb_dbk_NE__busy[0:0]),
    .rq(hb_dbk_NE__rq[135:0]),
    .rr({vmb_NE7__rr1[256:0], vmb_NE6__rr1[256:0], vmb_NE5__rr1[256:0], vmb_NE4__rr1[256:0], vmb_NE3__rr1[256:0], vmb_NE2__rr1[256:0], vmb_NE1__rr1[256:0], vmb_NE0__rr1[256:0]}),
    .wb_reserve_v(hb_dbk_NE__wb_reserve_v[0:0]),
    .wb_reserve_bank(hb_dbk_NE__wb_reserve_bank[0:0]),
    .wb_fill_bank(hb_dbk_NE__wb_fill_bank[0:0]),
    .wb_reserve_epoch(hb_dbk_NE__wb_reserve_epoch[15:0]),
    .wb_fill_epoch(hb_dbk_NE__wb_fill_epoch[15:0]),
    .wb_reserve_sectors(hb_dbk_NE__wb_reserve_sectors[11:0]),
    .wb_reserve_base(hb_dbk_NE__wb_reserve_base[31:0]),
    .wb_fill_start(hb_dbk_NE__wb_fill_start[0:0]),
    .wb_ready(wbk_NE__wb_ready[0:0]),
    .wd(hb_dbk_NE__wd[2311:0]),
    .wa(wbk_NE__wa[11:0])
  );
  ot_hgi_dma_back_static_vp4_banks_cp #(.RR_RT(80)) hb_dbk_NW (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .clk_cp(hb_ckgen__pll_stream[0:0]),
    .clk_rst(hb_ckgen__pll_stream[0:0]),
    .stk(2'b10),
    .tgt(8'b01101010),
    .clk_bank({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .cfg_v(hleaf_NW__b_cfg_v[0:0]),
    .cfg_target(hleaf_NW__b_cfg_target[7:0]),
    .cfg_addr(hleaf_NW__b_cfg_addr[11:0]),
    .cfg_data(hleaf_NW__b_cfg_data[255:0]),
    .desc_v(hleaf_NW__b_desc_v[0:0]),
    .desc_base(hleaf_NW__b_desc_base[11:0]),
    .desc_limit(hleaf_NW__b_desc_limit[12:0]),
    .desc_loops(hleaf_NW__b_desc_loops[15:0]),
    .launch_v(hleaf_NW__b_launch_v[0:0]),
    .cp_configured(hb_dbk_NW__cp_configured[0:0]),
    .cp_fault(hb_dbk_NW__cp_fault[0:0]),
    .cp_active(hb_dbk_NW__cp_active[0:0]),
    .mv_src(hb_dbk_NW__mv_src[0:0]),
    .mv_done(hb_dbk_NW__mv_done[0:0]),
    .mv_fault(hb_dbk_NW__mv_fault[0:0]),
    .quiet(hb_dbk_NW__quiet[0:0]),
    .busy(hb_dbk_NW__busy[0:0]),
    .rq(hb_dbk_NW__rq[135:0]),
    .rr({vmb_NW7__rr1[256:0], vmb_NW6__rr1[256:0], vmb_NW5__rr1[256:0], vmb_NW4__rr1[256:0], vmb_NW3__rr1[256:0], vmb_NW2__rr1[256:0], vmb_NW1__rr1[256:0], vmb_NW0__rr1[256:0]}),
    .wb_reserve_v(hb_dbk_NW__wb_reserve_v[0:0]),
    .wb_reserve_bank(hb_dbk_NW__wb_reserve_bank[0:0]),
    .wb_fill_bank(hb_dbk_NW__wb_fill_bank[0:0]),
    .wb_reserve_epoch(hb_dbk_NW__wb_reserve_epoch[15:0]),
    .wb_fill_epoch(hb_dbk_NW__wb_fill_epoch[15:0]),
    .wb_reserve_sectors(hb_dbk_NW__wb_reserve_sectors[11:0]),
    .wb_reserve_base(hb_dbk_NW__wb_reserve_base[31:0]),
    .wb_fill_start(hb_dbk_NW__wb_fill_start[0:0]),
    .wb_ready(wbk_NW__wb_ready[0:0]),
    .wd(hb_dbk_NW__wd[2311:0]),
    .wa(wbk_NW__wa[11:0])
  );
  ot_hbm_idx_rootctl_static_am #(.VM_RT(75), .CR_RT(36), .SEL_LAT(40), .RSTL(1), .FAN32(1)) hb_idx__ctl (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .program_we(col_idx__pw_we[0:0]),
    .program_addr(col_idx__pw_addr[7:0]),
    .program_data(col_idx__pw_data[255:0]),
    .start(col_idx__start_v[0:0]),
    .length(col_idx__prm[11:0]),
    .sel_op(hb_idx__ctl__sel_op[3:0]),
    .sel_pass(hb_idx__ctl__sel_pass[1:0]),
    .sel_addr(hb_idx__ctl__sel_addr[7:0]),
    .link_flush(hb_idx__ctl__link_flush[0:0]),
    .link_emit(hb_idx__ctl__link_emit[0:0]),
    .link_group(hb_idx__ctl__link_group[3:0]),
    .link_clear(hb_idx__ctl__link_clear[0:0]),
    .selected_v(hb_idx__selector__selected_v[3:0]),
    .ingest_v(hb_idx__ctl__ingest_v[0:0]),
    .tree_ev({hb_idx__xqr__y[1187:1187], hb_idx__xqr__y[890:890], hb_idx__xqr__y[593:593], hb_idx__xqr__y[296:296]}),
    .qfault({hb_idx__qctl_NE__fault[0:0], hb_idx__qctl_NW__fault[0:0], hb_idx__qctl_SE__fault[0:0], hb_idx__qctl_SW__fault[0:0]}),
    .sf(hb_idx__selector__fault[0:0]),
    .lf(hb_idx__link__fault[0:0]),
    .done(hb_idx__ctl__done[0:0]),
    .fault(hb_idx__ctl__fault[0:0]),
    .topk_go(col_idx__go[0:0]),
    .topk_k(col_idx__rec[3:0]),
    .topk_order(col_idx__rec[4:4]),
    .topk_n(col_idx__rec[24:5]),
    .topk_m(col_idx__rec[44:25]),
    .topk_a_mirror(col_idx__rec[45:45]),
    .topk_a_base(col_idx__rec[63:46]),
    .topk_a_str(col_idx__rec[81:64]),
    .topk_o_mirror(col_idx__rec[82:82]),
    .topk_o_base(col_idx__rec[100:83]),
    .topk_o_str(col_idx__rec[118:101]),
    .topk_has_r(col_idx__rec[119:119]),
    .topk_r_base(col_idx__rec[137:120]),
    .topk_r_str(col_idx__rec[155:138]),
    .cq(hb_idx__ctl__cq[337:0]),
    .cq_seq(hb_idx__ctl__cq_seq[1:0]),
    .cr(hb_vms_SW__cr[547:274]),
    .topk_busy(hb_idx__ctl__topk_busy[0:0]),
    .topk_done(hb_idx__ctl__topk_done[0:0]),
    .topk_fault(hb_idx__ctl__topk_fault[0:0]),
    .index_rq(hb_idx__op_SW__vm_rq[135:0]),
    .index_rr(hb_idx__ctl__index_rr[2055:0]),
    .argmax_rq(hb_argmax__vm_rq[135:0]),
    .argmax_m(hb_idx__ctl__argmax_m[263:0]),
    .vm_rq(hb_idx__ctl__vm_rq[135:0]),
    .vm_rr({vmb_SW7__rr4[256:0], vmb_SW6__rr4[256:0], vmb_SW5__rr4[256:0], vmb_SW4__rr4[256:0], vmb_SW3__rr4[256:0], vmb_SW2__rr4[256:0], vmb_SW1__rr4[256:0], vmb_SW0__rr4[256:0]}),
    .share_fault(hb_idx__ctl__share_fault[0:0])
  );
  ot_hbm_idx_topk_link_static hb_idx__link (
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_mem({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .clear(hb_idx__ctl__link_clear[0:0]),
    .ingest_v(hb_idx__ctl__ingest_v[0:0]),
    .selected_line(hb_idx__selector__selected_line[2367:0]),
    .flush(hb_idx__ctl__link_flush[0:0]),
    .emit_v(hb_idx__ctl__link_emit[0:0]),
    .emit_group(hb_idx__ctl__link_group[3:0]),
    .rank(col_idx__prm[74:67]),
    .gbase(col_idx__prm[51:44]),
    .tx_v(hb_idx__link__tx_v[3:0]),
    .tx(hb_idx__link__tx[2179:0]),
    .fault(hb_idx__link__fault[0:0]),
    .selected_count(hb_idx__link__selected_count[9:0])
  );
  ot_hbm_idx_vm_share2_static_r #(.BANK_RT(54)) hb_idx__nwsh (
    .clk_pair({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .a_rq(hb_idx__op_NW__vm_rq[135:0]),
    .b_rq({hb_quant_NW__quant_NW3_lg__rq_o[33:0], hb_quant_NW__quant_NW2_lg__rq_o[33:0], hb_quant_NW__quant_NW1_lg__rq_o[33:0], hb_quant_NW__quant_NW0_lg__rq_o[33:0]}),
    .vm_rq(hb_idx__nwsh__vm_rq[135:0]),
    .vm_rr({vmb_NW7__rr3[256:0], vmb_NW6__rr3[256:0], vmb_NW5__rr3[256:0], vmb_NW4__rr3[256:0], vmb_NW3__rr3[256:0], vmb_NW2__rr3[256:0], vmb_NW1__rr3[256:0], vmb_NW0__rr3[256:0]}),
    .a_rr(hb_idx__nwsh__a_rr[2055:0]),
    .b_rr(hb_idx__nwsh__b_rr[2055:0]),
    .fault(hb_idx__nwsh__fault[0:0])
  );
  ot_hbm_idx_vm_query_static_n12 #(.VM_RT_EXTRA(171)) hb_idx__op_NE (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .sid(2'b11),
    .weight_slot(hb_idx__qctl_NE__weight_slot[0:0]),
    .query_slot(hb_idx__qctl_NE__query_slot[0:0]),
    .query_index(hb_idx__qctl_NE__query_index[6:0]),
    .weight_sector(col_idx__prm[27:12]),
    .query_sector(col_idx__prm[43:28]),
    .vm_rq(hb_idx__op_NE__vm_rq[135:0]),
    .vm_rr({vmb_NE7__rr4[256:0], vmb_NE6__rr4[256:0], vmb_NE5__rr4[256:0], vmb_NE4__rr4[256:108], vmb_NE4__rr4[107:0], vmb_NE3__rr4[256:0], vmb_NE2__rr4[256:0], vmb_NE1__rr4[256:0], vmb_NE0__rr4[256:0]}),
    .block_v(hb_idx__op_NE__block_v[0:0]),
    .block_head(hb_idx__op_NE__block_head[4:0]),
    .block_number(hb_idx__op_NE__block_number[1:0]),
    .block_data(hb_idx__op_NE__block_data[1023:0]),
    .head_weight(hb_idx__op_NE__head_weight[15:0]),
    .fault(hb_idx__op_NE__fault[0:0])
  );
  ot_hbm_idx_vm_query_static_n12 #(.VM_RT_EXTRA(173)) hb_idx__op_NW (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .sid(2'b10),
    .weight_slot(hb_idx__qctl_NW__weight_slot[0:0]),
    .query_slot(hb_idx__qctl_NW__query_slot[0:0]),
    .query_index(hb_idx__qctl_NW__query_index[6:0]),
    .weight_sector(col_idx__prm[27:12]),
    .query_sector(col_idx__prm[43:28]),
    .vm_rq(hb_idx__op_NW__vm_rq[135:0]),
    .vm_rr(hb_idx__nwsh__a_rr[2055:0]),
    .block_v(hb_idx__op_NW__block_v[0:0]),
    .block_head(hb_idx__op_NW__block_head[4:0]),
    .block_number(hb_idx__op_NW__block_number[1:0]),
    .block_data(hb_idx__op_NW__block_data[1023:0]),
    .head_weight(hb_idx__op_NW__head_weight[15:0]),
    .fault(hb_idx__op_NW__fault[0:0])
  );
  ot_hbm_idx_vm_query_static_n12 #(.VM_RT_EXTRA(171)) hb_idx__op_SE (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .sid(2'b01),
    .weight_slot(hb_idx__qctl_SE__weight_slot[0:0]),
    .query_slot(hb_idx__qctl_SE__query_slot[0:0]),
    .query_index(hb_idx__qctl_SE__query_index[6:0]),
    .weight_sector(col_idx__prm[27:12]),
    .query_sector(col_idx__prm[43:28]),
    .vm_rq(hb_idx__op_SE__vm_rq[135:0]),
    .vm_rr({vmb_SE7__rr4[256:0], vmb_SE6__rr4[256:0], vmb_SE5__rr4[256:0], vmb_SE4__rr4[256:108], vmb_SE4__rr4[107:0], vmb_SE3__rr4[256:0], vmb_SE2__rr4[256:0], vmb_SE1__rr4[256:0], vmb_SE0__rr4[256:0]}),
    .block_v(hb_idx__op_SE__block_v[0:0]),
    .block_head(hb_idx__op_SE__block_head[4:0]),
    .block_number(hb_idx__op_SE__block_number[1:0]),
    .block_data(hb_idx__op_SE__block_data[1023:0]),
    .head_weight(hb_idx__op_SE__head_weight[15:0]),
    .fault(hb_idx__op_SE__fault[0:0])
  );
  ot_hbm_idx_vm_query_static_n12 #(.VM_RT_EXTRA(171)) hb_idx__op_SW (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .sid(2'b00),
    .weight_slot(hb_idx__qctl_SW__weight_slot[0:0]),
    .query_slot(hb_idx__qctl_SW__query_slot[0:0]),
    .query_index(hb_idx__qctl_SW__query_index[6:0]),
    .weight_sector(col_idx__prm[27:12]),
    .query_sector(col_idx__prm[43:28]),
    .vm_rq(hb_idx__op_SW__vm_rq[135:0]),
    .vm_rr({hb_idx__ctl__index_rr[2055:1760], hb_idx__ctl__index_rr[1759:0]}),
    .block_v(hb_idx__op_SW__block_v[0:0]),
    .block_head(hb_idx__op_SW__block_head[4:0]),
    .block_number(hb_idx__op_SW__block_number[1:0]),
    .block_data(hb_idx__op_SW__block_data[1023:0]),
    .head_weight(hb_idx__op_SW__head_weight[15:0]),
    .fault(hb_idx__op_SW__fault[0:0])
  );
  ot_hbm_idx_query_static hb_idx__q_NE (
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_quant(hb_ckgen__pll_stream[0:0]),
    .clk_quant_delay(hb_ckgen__pll_stream[0:0]),
    .clk_bank({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .frame_start(hb_idx__qctl_NE__frame_start[0:0]),
    .block_v(hb_idx__op_NE__block_v[0:0]),
    .block_head(hb_idx__op_NE__block_head[4:0]),
    .block_number(hb_idx__op_NE__block_number[1:0]),
    .block_data(hb_idx__op_NE__block_data[1023:0]),
    .head_weight(hb_idx__op_NE__head_weight[15:0]),
    .emit_v(hb_idx__qctl_NE__query_emit[0:0]),
    .emit_head(hb_idx__qctl_NE__query_emit_head[4:0]),
    .ql_v(hb_idx__q_NE__ql_v[0:0]),
    .ql_head(hb_idx__q_NE__ql_head[7:0]),
    .ql_codes(hb_idx__q_NE__ql_codes[511:0]),
    .ql_sc(hb_idx__q_NE__ql_sc[31:0]),
    .ql_w(hb_idx__q_NE__ql_w[15:0]),
    .fault(hb_idx__q_NE__fault[0:0])
  );
  ot_hbm_idx_query_static hb_idx__q_NW (
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_quant(hb_ckgen__pll_stream[0:0]),
    .clk_quant_delay(hb_ckgen__pll_stream[0:0]),
    .clk_bank({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .frame_start(hb_idx__qctl_NW__frame_start[0:0]),
    .block_v(hb_idx__op_NW__block_v[0:0]),
    .block_head(hb_idx__op_NW__block_head[4:0]),
    .block_number(hb_idx__op_NW__block_number[1:0]),
    .block_data(hb_idx__op_NW__block_data[1023:0]),
    .head_weight(hb_idx__op_NW__head_weight[15:0]),
    .emit_v(hb_idx__qctl_NW__query_emit[0:0]),
    .emit_head(hb_idx__qctl_NW__query_emit_head[4:0]),
    .ql_v(hb_idx__q_NW__ql_v[0:0]),
    .ql_head(hb_idx__q_NW__ql_head[7:0]),
    .ql_codes(hb_idx__q_NW__ql_codes[511:0]),
    .ql_sc(hb_idx__q_NW__ql_sc[31:0]),
    .ql_w(hb_idx__q_NW__ql_w[15:0]),
    .fault(hb_idx__q_NW__fault[0:0])
  );
  ot_hbm_idx_query_static hb_idx__q_SE (
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_quant(hb_ckgen__pll_stream[0:0]),
    .clk_quant_delay(hb_ckgen__pll_stream[0:0]),
    .clk_bank({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .frame_start(hb_idx__qctl_SE__frame_start[0:0]),
    .block_v(hb_idx__op_SE__block_v[0:0]),
    .block_head(hb_idx__op_SE__block_head[4:0]),
    .block_number(hb_idx__op_SE__block_number[1:0]),
    .block_data(hb_idx__op_SE__block_data[1023:0]),
    .head_weight(hb_idx__op_SE__head_weight[15:0]),
    .emit_v(hb_idx__qctl_SE__query_emit[0:0]),
    .emit_head(hb_idx__qctl_SE__query_emit_head[4:0]),
    .ql_v(hb_idx__q_SE__ql_v[0:0]),
    .ql_head(hb_idx__q_SE__ql_head[7:0]),
    .ql_codes(hb_idx__q_SE__ql_codes[511:0]),
    .ql_sc(hb_idx__q_SE__ql_sc[31:0]),
    .ql_w(hb_idx__q_SE__ql_w[15:0]),
    .fault(hb_idx__q_SE__fault[0:0])
  );
  ot_hbm_idx_query_static hb_idx__q_SW (
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_quant(hb_ckgen__pll_stream[0:0]),
    .clk_quant_delay(hb_ckgen__pll_stream[0:0]),
    .clk_bank({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .frame_start(hb_idx__qctl_SW__frame_start[0:0]),
    .block_v(hb_idx__op_SW__block_v[0:0]),
    .block_head(hb_idx__op_SW__block_head[4:0]),
    .block_number(hb_idx__op_SW__block_number[1:0]),
    .block_data(hb_idx__op_SW__block_data[1023:0]),
    .head_weight(hb_idx__op_SW__head_weight[15:0]),
    .emit_v(hb_idx__qctl_SW__query_emit[0:0]),
    .emit_head(hb_idx__qctl_SW__query_emit_head[4:0]),
    .ql_v(hb_idx__q_SW__ql_v[0:0]),
    .ql_head(hb_idx__q_SW__ql_head[7:0]),
    .ql_codes(hb_idx__q_SW__ql_codes[511:0]),
    .ql_sc(hb_idx__q_SW__ql_sc[31:0]),
    .ql_w(hb_idx__q_SW__ql_w[15:0]),
    .fault(hb_idx__q_SW__fault[0:0])
  );
  ot_hbm_idx_qctl_static hb_idx__qctl_NE (
    .clk_program(hb_ckgen__pll_stream[0:0]),
    .clk_program_mem(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .slot(1'b1),
    .program_we(col_idx__pw_we[0:0]),
    .program_addr(col_idx__pw_addr[7:0]),
    .program_data(col_idx__pw_data[255:0]),
    .start(col_idx__start_v[0:0]),
    .length(col_idx__prm[11:0]),
    .nkeys(col_idx__prm[65:52]),
    .weight_slot(hb_idx__qctl_NE__weight_slot[0:0]),
    .query_slot(hb_idx__qctl_NE__query_slot[0:0]),
    .query_index(hb_idx__qctl_NE__query_index[6:0]),
    .query_emit(hb_idx__qctl_NE__query_emit[0:0]),
    .query_emit_head(hb_idx__qctl_NE__query_emit_head[4:0]),
    .key_slot(hb_idx__qctl_NE__key_slot[0:0]),
    .key_index(hb_idx__qctl_NE__key_index[7:0]),
    .nq(hb_idx__qctl_NE__nq[11:0]),
    .frame_start(hb_idx__qctl_NE__frame_start[0:0]),
    .vf(hb_idx__op_NE__fault[0:0]),
    .qf(hb_idx__q_NE__fault[0:0]),
    .scf(hb_idx__s_NE__fault[0:0]),
    .fault(hb_idx__qctl_NE__fault[0:0])
  );
  ot_hbm_idx_qctl_static hb_idx__qctl_NW (
    .clk_program(hb_ckgen__pll_stream[0:0]),
    .clk_program_mem(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .slot(1'b1),
    .program_we(col_idx__pw_we[0:0]),
    .program_addr(col_idx__pw_addr[7:0]),
    .program_data(col_idx__pw_data[255:0]),
    .start(col_idx__start_v[0:0]),
    .length(col_idx__prm[11:0]),
    .nkeys(col_idx__prm[65:52]),
    .weight_slot(hb_idx__qctl_NW__weight_slot[0:0]),
    .query_slot(hb_idx__qctl_NW__query_slot[0:0]),
    .query_index(hb_idx__qctl_NW__query_index[6:0]),
    .query_emit(hb_idx__qctl_NW__query_emit[0:0]),
    .query_emit_head(hb_idx__qctl_NW__query_emit_head[4:0]),
    .key_slot(hb_idx__qctl_NW__key_slot[0:0]),
    .key_index(hb_idx__qctl_NW__key_index[7:0]),
    .nq(hb_idx__qctl_NW__nq[11:0]),
    .frame_start(hb_idx__qctl_NW__frame_start[0:0]),
    .vf(hb_idx__op_NW__fault[0:0]),
    .qf(hb_idx__q_NW__fault[0:0]),
    .scf(hb_idx__s_NW__fault[0:0]),
    .fault(hb_idx__qctl_NW__fault[0:0])
  );
  ot_hbm_idx_qctl_static hb_idx__qctl_SE (
    .clk_program(hb_ckgen__pll_stream[0:0]),
    .clk_program_mem(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .slot(1'b0),
    .program_we(col_idx__pw_we[0:0]),
    .program_addr(col_idx__pw_addr[7:0]),
    .program_data(col_idx__pw_data[255:0]),
    .start(col_idx__start_v[0:0]),
    .length(col_idx__prm[11:0]),
    .nkeys(col_idx__prm[65:52]),
    .weight_slot(hb_idx__qctl_SE__weight_slot[0:0]),
    .query_slot(hb_idx__qctl_SE__query_slot[0:0]),
    .query_index(hb_idx__qctl_SE__query_index[6:0]),
    .query_emit(hb_idx__qctl_SE__query_emit[0:0]),
    .query_emit_head(hb_idx__qctl_SE__query_emit_head[4:0]),
    .key_slot(hb_idx__qctl_SE__key_slot[0:0]),
    .key_index(hb_idx__qctl_SE__key_index[7:0]),
    .nq(hb_idx__qctl_SE__nq[11:0]),
    .frame_start(hb_idx__qctl_SE__frame_start[0:0]),
    .vf(hb_idx__op_SE__fault[0:0]),
    .qf(hb_idx__q_SE__fault[0:0]),
    .scf(hb_idx__s_SE__fault[0:0]),
    .fault(hb_idx__qctl_SE__fault[0:0])
  );
  ot_hbm_idx_qctl_static hb_idx__qctl_SW (
    .clk_program(hb_ckgen__pll_stream[0:0]),
    .clk_program_mem(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .slot(1'b0),
    .program_we(col_idx__pw_we[0:0]),
    .program_addr(col_idx__pw_addr[7:0]),
    .program_data(col_idx__pw_data[255:0]),
    .start(col_idx__start_v[0:0]),
    .length(col_idx__prm[11:0]),
    .nkeys(col_idx__prm[65:52]),
    .weight_slot(hb_idx__qctl_SW__weight_slot[0:0]),
    .query_slot(hb_idx__qctl_SW__query_slot[0:0]),
    .query_index(hb_idx__qctl_SW__query_index[6:0]),
    .query_emit(hb_idx__qctl_SW__query_emit[0:0]),
    .query_emit_head(hb_idx__qctl_SW__query_emit_head[4:0]),
    .key_slot(hb_idx__qctl_SW__key_slot[0:0]),
    .key_index(hb_idx__qctl_SW__key_index[7:0]),
    .nq(hb_idx__qctl_SW__nq[11:0]),
    .frame_start(hb_idx__qctl_SW__frame_start[0:0]),
    .vf(hb_idx__op_SW__fault[0:0]),
    .qf(hb_idx__q_SW__fault[0:0]),
    .scf(hb_idx__s_SW__fault[0:0]),
    .fault(hb_idx__qctl_SW__fault[0:0])
  );
  ot_hnx_idxn_quarter_with_keybuf #(.TP(192), .DELIVERED_RESET(1)) hb_idx__s_NE (
    .rst_n(native_required__hb_idx__s_NE__rst_n[0:0]),
    .half(1'b1),
    .rank(col_idx__prm[74:67]),
    .first_ord(11'b00101010110),
    .nkeys(hb_idx__qctl_NE__nq[11:0]),
    .keep_en(col_idx__prm[66:66]),
    .keep_bitmap({col_idx__prm[758:758], col_idx__prm[756:756], col_idx__prm[754:754], col_idx__prm[752:752], col_idx__prm[750:750], col_idx__prm[748:748], col_idx__prm[746:746], col_idx__prm[744:744], col_idx__prm[742:742], col_idx__prm[740:740], col_idx__prm[738:738], col_idx__prm[736:736], col_idx__prm[734:734], col_idx__prm[732:732], col_idx__prm[730:730], col_idx__prm[728:728], col_idx__prm[726:726], col_idx__prm[724:724], col_idx__prm[722:722], col_idx__prm[720:720], col_idx__prm[718:718], col_idx__prm[716:716], col_idx__prm[714:714], col_idx__prm[712:712], col_idx__prm[710:710], col_idx__prm[708:708], col_idx__prm[706:706], col_idx__prm[704:704], col_idx__prm[702:702], col_idx__prm[700:700], col_idx__prm[698:698], col_idx__prm[696:696], col_idx__prm[694:694], col_idx__prm[692:692], col_idx__prm[690:690], col_idx__prm[688:688], col_idx__prm[686:686], col_idx__prm[684:684], col_idx__prm[682:682], col_idx__prm[680:680], col_idx__prm[678:678], col_idx__prm[676:676], col_idx__prm[674:674], col_idx__prm[672:672], col_idx__prm[670:670], col_idx__prm[668:668], col_idx__prm[666:666], col_idx__prm[664:664], col_idx__prm[662:662], col_idx__prm[660:660], col_idx__prm[658:658], col_idx__prm[656:656], col_idx__prm[654:654], col_idx__prm[652:652], col_idx__prm[650:650], col_idx__prm[648:648], col_idx__prm[646:646], col_idx__prm[644:644], col_idx__prm[642:642], col_idx__prm[640:640], col_idx__prm[638:638], col_idx__prm[636:636], col_idx__prm[634:634], col_idx__prm[632:632], col_idx__prm[630:630], col_idx__prm[628:628], col_idx__prm[626:626], col_idx__prm[624:624], col_idx__prm[622:622], col_idx__prm[620:620], col_idx__prm[618:618], col_idx__prm[616:616], col_idx__prm[614:614], col_idx__prm[612:612], col_idx__prm[610:610], col_idx__prm[608:608], col_idx__prm[606:606], col_idx__prm[604:604], col_idx__prm[602:602], col_idx__prm[600:600], col_idx__prm[598:598], col_idx__prm[596:596], col_idx__prm[594:594], col_idx__prm[592:592], col_idx__prm[590:590], col_idx__prm[588:588], col_idx__prm[586:586], col_idx__prm[584:584], col_idx__prm[582:582], col_idx__prm[580:580], col_idx__prm[578:578], col_idx__prm[576:576], col_idx__prm[574:574], col_idx__prm[572:572], col_idx__prm[570:570], col_idx__prm[568:568], col_idx__prm[566:566], col_idx__prm[564:564], col_idx__prm[562:562], col_idx__prm[560:560], col_idx__prm[558:558], col_idx__prm[556:556], col_idx__prm[554:554], col_idx__prm[552:552], col_idx__prm[550:550], col_idx__prm[548:548], col_idx__prm[546:546], col_idx__prm[544:544], col_idx__prm[542:542], col_idx__prm[540:540], col_idx__prm[538:538], col_idx__prm[536:536], col_idx__prm[534:534], col_idx__prm[532:532], col_idx__prm[530:530], col_idx__prm[528:528], col_idx__prm[526:526], col_idx__prm[524:524], col_idx__prm[522:522], col_idx__prm[520:520], col_idx__prm[518:518], col_idx__prm[516:516], col_idx__prm[514:514], col_idx__prm[512:512], col_idx__prm[510:510], col_idx__prm[508:508], col_idx__prm[506:506], col_idx__prm[504:504], col_idx__prm[502:502], col_idx__prm[500:500], col_idx__prm[498:498], col_idx__prm[496:496], col_idx__prm[494:494], col_idx__prm[492:492], col_idx__prm[490:490], col_idx__prm[488:488], col_idx__prm[486:486], col_idx__prm[484:484], col_idx__prm[482:482], col_idx__prm[480:480], col_idx__prm[478:478], col_idx__prm[476:476], col_idx__prm[474:474], col_idx__prm[472:472], col_idx__prm[470:470], col_idx__prm[468:468], col_idx__prm[466:466], col_idx__prm[464:464], col_idx__prm[462:462], col_idx__prm[460:460], col_idx__prm[458:458], col_idx__prm[456:456], col_idx__prm[454:454], col_idx__prm[452:452], col_idx__prm[450:450], col_idx__prm[448:448], col_idx__prm[446:446], col_idx__prm[444:444], col_idx__prm[442:442], col_idx__prm[440:440], col_idx__prm[438:438], col_idx__prm[436:436], col_idx__prm[434:434], col_idx__prm[432:432], col_idx__prm[430:430], col_idx__prm[428:428], col_idx__prm[426:426], col_idx__prm[424:424], col_idx__prm[422:422], col_idx__prm[420:420], col_idx__prm[418:418]}),
    .ql_v(hb_idx__q_NE__ql_v[0:0]),
    .ql_head(hb_idx__q_NE__ql_head[7:0]),
    .ql_codes(hb_idx__q_NE__ql_codes[511:0]),
    .ql_sc(hb_idx__q_NE__ql_sc[31:0]),
    .ql_w(hb_idx__q_NE__ql_w[15:0]),
    .beat_v(hb_idx__qctl_NE__key_slot[0:0]),
    .beat_index(hb_idx__qctl_NE__key_index[7:0]),
    .key_lines({svg_NW7__sm_packet[1087:0], svg_NW7__sm_packet[1097:1088], svg_NW7__sm_packet[1098:1098], svg_NW6__sm_packet[1087:0], svg_NW6__sm_packet[1097:1088], svg_NW6__sm_packet[1098:1098], svg_NW5__sm_packet[1087:0], svg_NW5__sm_packet[1097:1088], svg_NW5__sm_packet[1098:1098], svg_NW4__sm_packet[1087:0], svg_NW4__sm_packet[1097:1088], svg_NW4__sm_packet[1098:1098]}),
    .score(hb_idx__s_NE__score[305:0]),
    .fault(hb_idx__s_NE__fault[0:0]),
    .clk(hb_ckgen__pll_stream[0:0]),
    .clear(native_required__hb_idx__s_NE__clear[0:0]),
    .live_v(native_required__hb_idx__s_NE__live_v[0:0]),
    .live_index(native_required__hb_idx__s_NE__live_index[7:0]),
    .pre_v(native_required__hb_idx__s_NE__pre_v[0:0]),
    .pre_index(native_required__hb_idx__s_NE__pre_index[7:0]),
    .replay_v(native_required__hb_idx__s_NE__replay_v[0:0]),
    .replay_index(native_required__hb_idx__s_NE__replay_index[7:0])
  );
  ot_hnx_idxn_quarter_with_keybuf #(.TP(192), .DELIVERED_RESET(1)) hb_idx__s_NW (
    .rst_n(native_required__hb_idx__s_NW__rst_n[0:0]),
    .half(1'b0),
    .rank(col_idx__prm[74:67]),
    .first_ord(11'b00101010110),
    .nkeys(hb_idx__qctl_NW__nq[11:0]),
    .keep_en(col_idx__prm[66:66]),
    .keep_bitmap({col_idx__prm[757:757], col_idx__prm[755:755], col_idx__prm[753:753], col_idx__prm[751:751], col_idx__prm[749:749], col_idx__prm[747:747], col_idx__prm[745:745], col_idx__prm[743:743], col_idx__prm[741:741], col_idx__prm[739:739], col_idx__prm[737:737], col_idx__prm[735:735], col_idx__prm[733:733], col_idx__prm[731:731], col_idx__prm[729:729], col_idx__prm[727:727], col_idx__prm[725:725], col_idx__prm[723:723], col_idx__prm[721:721], col_idx__prm[719:719], col_idx__prm[717:717], col_idx__prm[715:715], col_idx__prm[713:713], col_idx__prm[711:711], col_idx__prm[709:709], col_idx__prm[707:707], col_idx__prm[705:705], col_idx__prm[703:703], col_idx__prm[701:701], col_idx__prm[699:699], col_idx__prm[697:697], col_idx__prm[695:695], col_idx__prm[693:693], col_idx__prm[691:691], col_idx__prm[689:689], col_idx__prm[687:687], col_idx__prm[685:685], col_idx__prm[683:683], col_idx__prm[681:681], col_idx__prm[679:679], col_idx__prm[677:677], col_idx__prm[675:675], col_idx__prm[673:673], col_idx__prm[671:671], col_idx__prm[669:669], col_idx__prm[667:667], col_idx__prm[665:665], col_idx__prm[663:663], col_idx__prm[661:661], col_idx__prm[659:659], col_idx__prm[657:657], col_idx__prm[655:655], col_idx__prm[653:653], col_idx__prm[651:651], col_idx__prm[649:649], col_idx__prm[647:647], col_idx__prm[645:645], col_idx__prm[643:643], col_idx__prm[641:641], col_idx__prm[639:639], col_idx__prm[637:637], col_idx__prm[635:635], col_idx__prm[633:633], col_idx__prm[631:631], col_idx__prm[629:629], col_idx__prm[627:627], col_idx__prm[625:625], col_idx__prm[623:623], col_idx__prm[621:621], col_idx__prm[619:619], col_idx__prm[617:617], col_idx__prm[615:615], col_idx__prm[613:613], col_idx__prm[611:611], col_idx__prm[609:609], col_idx__prm[607:607], col_idx__prm[605:605], col_idx__prm[603:603], col_idx__prm[601:601], col_idx__prm[599:599], col_idx__prm[597:597], col_idx__prm[595:595], col_idx__prm[593:593], col_idx__prm[591:591], col_idx__prm[589:589], col_idx__prm[587:587], col_idx__prm[585:585], col_idx__prm[583:583], col_idx__prm[581:581], col_idx__prm[579:579], col_idx__prm[577:577], col_idx__prm[575:575], col_idx__prm[573:573], col_idx__prm[571:571], col_idx__prm[569:569], col_idx__prm[567:567], col_idx__prm[565:565], col_idx__prm[563:563], col_idx__prm[561:561], col_idx__prm[559:559], col_idx__prm[557:557], col_idx__prm[555:555], col_idx__prm[553:553], col_idx__prm[551:551], col_idx__prm[549:549], col_idx__prm[547:547], col_idx__prm[545:545], col_idx__prm[543:543], col_idx__prm[541:541], col_idx__prm[539:539], col_idx__prm[537:537], col_idx__prm[535:535], col_idx__prm[533:533], col_idx__prm[531:531], col_idx__prm[529:529], col_idx__prm[527:527], col_idx__prm[525:525], col_idx__prm[523:523], col_idx__prm[521:521], col_idx__prm[519:519], col_idx__prm[517:517], col_idx__prm[515:515], col_idx__prm[513:513], col_idx__prm[511:511], col_idx__prm[509:509], col_idx__prm[507:507], col_idx__prm[505:505], col_idx__prm[503:503], col_idx__prm[501:501], col_idx__prm[499:499], col_idx__prm[497:497], col_idx__prm[495:495], col_idx__prm[493:493], col_idx__prm[491:491], col_idx__prm[489:489], col_idx__prm[487:487], col_idx__prm[485:485], col_idx__prm[483:483], col_idx__prm[481:481], col_idx__prm[479:479], col_idx__prm[477:477], col_idx__prm[475:475], col_idx__prm[473:473], col_idx__prm[471:471], col_idx__prm[469:469], col_idx__prm[467:467], col_idx__prm[465:465], col_idx__prm[463:463], col_idx__prm[461:461], col_idx__prm[459:459], col_idx__prm[457:457], col_idx__prm[455:455], col_idx__prm[453:453], col_idx__prm[451:451], col_idx__prm[449:449], col_idx__prm[447:447], col_idx__prm[445:445], col_idx__prm[443:443], col_idx__prm[441:441], col_idx__prm[439:439], col_idx__prm[437:437], col_idx__prm[435:435], col_idx__prm[433:433], col_idx__prm[431:431], col_idx__prm[429:429], col_idx__prm[427:427], col_idx__prm[425:425], col_idx__prm[423:423], col_idx__prm[421:421], col_idx__prm[419:419], col_idx__prm[417:417]}),
    .ql_v(hb_idx__q_NW__ql_v[0:0]),
    .ql_head(hb_idx__q_NW__ql_head[7:0]),
    .ql_codes(hb_idx__q_NW__ql_codes[511:0]),
    .ql_sc(hb_idx__q_NW__ql_sc[31:0]),
    .ql_w(hb_idx__q_NW__ql_w[15:0]),
    .beat_v(hb_idx__qctl_NW__key_slot[0:0]),
    .beat_index(hb_idx__qctl_NW__key_index[7:0]),
    .key_lines({svg_NW3__sm_packet[1087:0], svg_NW3__sm_packet[1097:1088], svg_NW3__sm_packet[1098:1098], svg_NW2__sm_packet[1087:0], svg_NW2__sm_packet[1097:1088], svg_NW2__sm_packet[1098:1098], svg_NW1__sm_packet[1087:0], svg_NW1__sm_packet[1097:1088], svg_NW1__sm_packet[1098:1098], svg_NW0__sm_packet[1087:0], svg_NW0__sm_packet[1097:1088], svg_NW0__sm_packet[1098:1098]}),
    .score(hb_idx__s_NW__score[305:0]),
    .fault(hb_idx__s_NW__fault[0:0]),
    .clk(hb_ckgen__pll_stream[0:0]),
    .clear(native_required__hb_idx__s_NW__clear[0:0]),
    .live_v(native_required__hb_idx__s_NW__live_v[0:0]),
    .live_index(native_required__hb_idx__s_NW__live_index[7:0]),
    .pre_v(native_required__hb_idx__s_NW__pre_v[0:0]),
    .pre_index(native_required__hb_idx__s_NW__pre_index[7:0]),
    .replay_v(native_required__hb_idx__s_NW__replay_v[0:0]),
    .replay_index(native_required__hb_idx__s_NW__replay_index[7:0])
  );
  ot_hnx_idxn_quarter_with_keybuf #(.TP(192), .DELIVERED_RESET(1)) hb_idx__s_SE (
    .rst_n(native_required__hb_idx__s_SE__rst_n[0:0]),
    .half(1'b1),
    .rank(col_idx__prm[74:67]),
    .first_ord(11'b00000000000),
    .nkeys(hb_idx__qctl_SE__nq[11:0]),
    .keep_en(col_idx__prm[66:66]),
    .keep_bitmap({col_idx__prm[416:416], col_idx__prm[414:414], col_idx__prm[412:412], col_idx__prm[410:410], col_idx__prm[408:408], col_idx__prm[406:406], col_idx__prm[404:404], col_idx__prm[402:402], col_idx__prm[400:400], col_idx__prm[398:398], col_idx__prm[396:396], col_idx__prm[394:394], col_idx__prm[392:392], col_idx__prm[390:390], col_idx__prm[388:388], col_idx__prm[386:386], col_idx__prm[384:384], col_idx__prm[382:382], col_idx__prm[380:380], col_idx__prm[378:378], col_idx__prm[376:376], col_idx__prm[374:374], col_idx__prm[372:372], col_idx__prm[370:370], col_idx__prm[368:368], col_idx__prm[366:366], col_idx__prm[364:364], col_idx__prm[362:362], col_idx__prm[360:360], col_idx__prm[358:358], col_idx__prm[356:356], col_idx__prm[354:354], col_idx__prm[352:352], col_idx__prm[350:350], col_idx__prm[348:348], col_idx__prm[346:346], col_idx__prm[344:344], col_idx__prm[342:342], col_idx__prm[340:340], col_idx__prm[338:338], col_idx__prm[336:336], col_idx__prm[334:334], col_idx__prm[332:332], col_idx__prm[330:330], col_idx__prm[328:328], col_idx__prm[326:326], col_idx__prm[324:324], col_idx__prm[322:322], col_idx__prm[320:320], col_idx__prm[318:318], col_idx__prm[316:316], col_idx__prm[314:314], col_idx__prm[312:312], col_idx__prm[310:310], col_idx__prm[308:308], col_idx__prm[306:306], col_idx__prm[304:304], col_idx__prm[302:302], col_idx__prm[300:300], col_idx__prm[298:298], col_idx__prm[296:296], col_idx__prm[294:294], col_idx__prm[292:292], col_idx__prm[290:290], col_idx__prm[288:288], col_idx__prm[286:286], col_idx__prm[284:284], col_idx__prm[282:282], col_idx__prm[280:280], col_idx__prm[278:278], col_idx__prm[276:276], col_idx__prm[274:274], col_idx__prm[272:272], col_idx__prm[270:270], col_idx__prm[268:268], col_idx__prm[266:266], col_idx__prm[264:264], col_idx__prm[262:262], col_idx__prm[260:260], col_idx__prm[258:258], col_idx__prm[256:256], col_idx__prm[254:254], col_idx__prm[252:252], col_idx__prm[250:250], col_idx__prm[248:248], col_idx__prm[246:246], col_idx__prm[244:244], col_idx__prm[242:242], col_idx__prm[240:240], col_idx__prm[238:238], col_idx__prm[236:236], col_idx__prm[234:234], col_idx__prm[232:232], col_idx__prm[230:230], col_idx__prm[228:228], col_idx__prm[226:226], col_idx__prm[224:224], col_idx__prm[222:222], col_idx__prm[220:220], col_idx__prm[218:218], col_idx__prm[216:216], col_idx__prm[214:214], col_idx__prm[212:212], col_idx__prm[210:210], col_idx__prm[208:208], col_idx__prm[206:206], col_idx__prm[204:204], col_idx__prm[202:202], col_idx__prm[200:200], col_idx__prm[198:198], col_idx__prm[196:196], col_idx__prm[194:194], col_idx__prm[192:192], col_idx__prm[190:190], col_idx__prm[188:188], col_idx__prm[186:186], col_idx__prm[184:184], col_idx__prm[182:182], col_idx__prm[180:180], col_idx__prm[178:178], col_idx__prm[176:176], col_idx__prm[174:174], col_idx__prm[172:172], col_idx__prm[170:170], col_idx__prm[168:168], col_idx__prm[166:166], col_idx__prm[164:164], col_idx__prm[162:162], col_idx__prm[160:160], col_idx__prm[158:158], col_idx__prm[156:156], col_idx__prm[154:154], col_idx__prm[152:152], col_idx__prm[150:150], col_idx__prm[148:148], col_idx__prm[146:146], col_idx__prm[144:144], col_idx__prm[142:142], col_idx__prm[140:140], col_idx__prm[138:138], col_idx__prm[136:136], col_idx__prm[134:134], col_idx__prm[132:132], col_idx__prm[130:130], col_idx__prm[128:128], col_idx__prm[126:126], col_idx__prm[124:124], col_idx__prm[122:122], col_idx__prm[120:120], col_idx__prm[118:118], col_idx__prm[116:116], col_idx__prm[114:114], col_idx__prm[112:112], col_idx__prm[110:110], col_idx__prm[108:108], col_idx__prm[106:106], col_idx__prm[104:104], col_idx__prm[102:102], col_idx__prm[100:100], col_idx__prm[98:98], col_idx__prm[96:96], col_idx__prm[94:94], col_idx__prm[92:92], col_idx__prm[90:90], col_idx__prm[88:88], col_idx__prm[86:86], col_idx__prm[84:84], col_idx__prm[82:82], col_idx__prm[80:80], col_idx__prm[78:78], col_idx__prm[76:76]}),
    .ql_v(hb_idx__q_SE__ql_v[0:0]),
    .ql_head(hb_idx__q_SE__ql_head[7:0]),
    .ql_codes(hb_idx__q_SE__ql_codes[511:0]),
    .ql_sc(hb_idx__q_SE__ql_sc[31:0]),
    .ql_w(hb_idx__q_SE__ql_w[15:0]),
    .beat_v(hb_idx__qctl_SE__key_slot[0:0]),
    .beat_index(hb_idx__qctl_SE__key_index[7:0]),
    .key_lines({svg_SW7__sm_packet[1087:0], svg_SW7__sm_packet[1097:1088], svg_SW7__sm_packet[1098:1098], svg_SW6__sm_packet[1087:0], svg_SW6__sm_packet[1097:1088], svg_SW6__sm_packet[1098:1098], svg_SW5__sm_packet[1087:0], svg_SW5__sm_packet[1097:1088], svg_SW5__sm_packet[1098:1098], svg_SW4__sm_packet[1087:0], svg_SW4__sm_packet[1097:1088], svg_SW4__sm_packet[1098:1098]}),
    .score(hb_idx__s_SE__score[305:0]),
    .fault(hb_idx__s_SE__fault[0:0]),
    .clk(hb_ckgen__pll_stream[0:0]),
    .clear(native_required__hb_idx__s_SE__clear[0:0]),
    .live_v(native_required__hb_idx__s_SE__live_v[0:0]),
    .live_index(native_required__hb_idx__s_SE__live_index[7:0]),
    .pre_v(native_required__hb_idx__s_SE__pre_v[0:0]),
    .pre_index(native_required__hb_idx__s_SE__pre_index[7:0]),
    .replay_v(native_required__hb_idx__s_SE__replay_v[0:0]),
    .replay_index(native_required__hb_idx__s_SE__replay_index[7:0])
  );
  ot_hnx_idxn_quarter_with_keybuf #(.TP(192), .DELIVERED_RESET(1)) hb_idx__s_SW (
    .rst_n(native_required__hb_idx__s_SW__rst_n[0:0]),
    .half(1'b0),
    .rank(col_idx__prm[74:67]),
    .first_ord(11'b00000000000),
    .nkeys(hb_idx__qctl_SW__nq[11:0]),
    .keep_en(col_idx__prm[66:66]),
    .keep_bitmap({col_idx__prm[415:415], col_idx__prm[413:413], col_idx__prm[411:411], col_idx__prm[409:409], col_idx__prm[407:407], col_idx__prm[405:405], col_idx__prm[403:403], col_idx__prm[401:401], col_idx__prm[399:399], col_idx__prm[397:397], col_idx__prm[395:395], col_idx__prm[393:393], col_idx__prm[391:391], col_idx__prm[389:389], col_idx__prm[387:387], col_idx__prm[385:385], col_idx__prm[383:383], col_idx__prm[381:381], col_idx__prm[379:379], col_idx__prm[377:377], col_idx__prm[375:375], col_idx__prm[373:373], col_idx__prm[371:371], col_idx__prm[369:369], col_idx__prm[367:367], col_idx__prm[365:365], col_idx__prm[363:363], col_idx__prm[361:361], col_idx__prm[359:359], col_idx__prm[357:357], col_idx__prm[355:355], col_idx__prm[353:353], col_idx__prm[351:351], col_idx__prm[349:349], col_idx__prm[347:347], col_idx__prm[345:345], col_idx__prm[343:343], col_idx__prm[341:341], col_idx__prm[339:339], col_idx__prm[337:337], col_idx__prm[335:335], col_idx__prm[333:333], col_idx__prm[331:331], col_idx__prm[329:329], col_idx__prm[327:327], col_idx__prm[325:325], col_idx__prm[323:323], col_idx__prm[321:321], col_idx__prm[319:319], col_idx__prm[317:317], col_idx__prm[315:315], col_idx__prm[313:313], col_idx__prm[311:311], col_idx__prm[309:309], col_idx__prm[307:307], col_idx__prm[305:305], col_idx__prm[303:303], col_idx__prm[301:301], col_idx__prm[299:299], col_idx__prm[297:297], col_idx__prm[295:295], col_idx__prm[293:293], col_idx__prm[291:291], col_idx__prm[289:289], col_idx__prm[287:287], col_idx__prm[285:285], col_idx__prm[283:283], col_idx__prm[281:281], col_idx__prm[279:279], col_idx__prm[277:277], col_idx__prm[275:275], col_idx__prm[273:273], col_idx__prm[271:271], col_idx__prm[269:269], col_idx__prm[267:267], col_idx__prm[265:265], col_idx__prm[263:263], col_idx__prm[261:261], col_idx__prm[259:259], col_idx__prm[257:257], col_idx__prm[255:255], col_idx__prm[253:253], col_idx__prm[251:251], col_idx__prm[249:249], col_idx__prm[247:247], col_idx__prm[245:245], col_idx__prm[243:243], col_idx__prm[241:241], col_idx__prm[239:239], col_idx__prm[237:237], col_idx__prm[235:235], col_idx__prm[233:233], col_idx__prm[231:231], col_idx__prm[229:229], col_idx__prm[227:227], col_idx__prm[225:225], col_idx__prm[223:223], col_idx__prm[221:221], col_idx__prm[219:219], col_idx__prm[217:217], col_idx__prm[215:215], col_idx__prm[213:213], col_idx__prm[211:211], col_idx__prm[209:209], col_idx__prm[207:207], col_idx__prm[205:205], col_idx__prm[203:203], col_idx__prm[201:201], col_idx__prm[199:199], col_idx__prm[197:197], col_idx__prm[195:195], col_idx__prm[193:193], col_idx__prm[191:191], col_idx__prm[189:189], col_idx__prm[187:187], col_idx__prm[185:185], col_idx__prm[183:183], col_idx__prm[181:181], col_idx__prm[179:179], col_idx__prm[177:177], col_idx__prm[175:175], col_idx__prm[173:173], col_idx__prm[171:171], col_idx__prm[169:169], col_idx__prm[167:167], col_idx__prm[165:165], col_idx__prm[163:163], col_idx__prm[161:161], col_idx__prm[159:159], col_idx__prm[157:157], col_idx__prm[155:155], col_idx__prm[153:153], col_idx__prm[151:151], col_idx__prm[149:149], col_idx__prm[147:147], col_idx__prm[145:145], col_idx__prm[143:143], col_idx__prm[141:141], col_idx__prm[139:139], col_idx__prm[137:137], col_idx__prm[135:135], col_idx__prm[133:133], col_idx__prm[131:131], col_idx__prm[129:129], col_idx__prm[127:127], col_idx__prm[125:125], col_idx__prm[123:123], col_idx__prm[121:121], col_idx__prm[119:119], col_idx__prm[117:117], col_idx__prm[115:115], col_idx__prm[113:113], col_idx__prm[111:111], col_idx__prm[109:109], col_idx__prm[107:107], col_idx__prm[105:105], col_idx__prm[103:103], col_idx__prm[101:101], col_idx__prm[99:99], col_idx__prm[97:97], col_idx__prm[95:95], col_idx__prm[93:93], col_idx__prm[91:91], col_idx__prm[89:89], col_idx__prm[87:87], col_idx__prm[85:85], col_idx__prm[83:83], col_idx__prm[81:81], col_idx__prm[79:79], col_idx__prm[77:77], col_idx__prm[75:75]}),
    .ql_v(hb_idx__q_SW__ql_v[0:0]),
    .ql_head(hb_idx__q_SW__ql_head[7:0]),
    .ql_codes(hb_idx__q_SW__ql_codes[511:0]),
    .ql_sc(hb_idx__q_SW__ql_sc[31:0]),
    .ql_w(hb_idx__q_SW__ql_w[15:0]),
    .beat_v(hb_idx__qctl_SW__key_slot[0:0]),
    .beat_index(hb_idx__qctl_SW__key_index[7:0]),
    .key_lines({svg_SW3__sm_packet[1087:0], svg_SW3__sm_packet[1097:1088], svg_SW3__sm_packet[1098:1098], svg_SW2__sm_packet[1087:0], svg_SW2__sm_packet[1097:1088], svg_SW2__sm_packet[1098:1098], svg_SW1__sm_packet[1087:0], svg_SW1__sm_packet[1097:1088], svg_SW1__sm_packet[1098:1098], svg_SW0__sm_packet[1087:0], svg_SW0__sm_packet[1097:1088], svg_SW0__sm_packet[1098:1098]}),
    .score(hb_idx__s_SW__score[305:0]),
    .fault(hb_idx__s_SW__fault[0:0]),
    .clk(hb_ckgen__pll_stream[0:0]),
    .clear(native_required__hb_idx__s_SW__clear[0:0]),
    .live_v(native_required__hb_idx__s_SW__live_v[0:0]),
    .live_index(native_required__hb_idx__s_SW__live_index[7:0]),
    .pre_v(native_required__hb_idx__s_SW__pre_v[0:0]),
    .pre_index(native_required__hb_idx__s_SW__pre_index[7:0]),
    .replay_v(native_required__hb_idx__s_SW__replay_v[0:0]),
    .replay_index(native_required__hb_idx__s_SW__replay_index[7:0])
  );
  ot_hbm_idx_selector_static_sel hb_idx__selector (
    .clk_ctl(hb_ckgen__pll_stream[0:0]),
    .clk_q({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .clk_mem({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .op(hb_idx__ctl__sel_op[3:0]),
    .pass(hb_idx__ctl__sel_pass[1:0]),
    .addr(hb_idx__ctl__sel_addr[7:0]),
    .k(col_idx__prm[768:759]),
    .in_line({1184'b00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000, hb_idx__xqr__y[1186:891], hb_idx__xqr__y[889:594], hb_idx__xqr__y[592:297], hb_idx__xqr__y[295:0]}),
    .selected_v(hb_idx__selector__selected_v[3:0]),
    .selected_line(hb_idx__selector__selected_line[2367:0]),
    .fault(hb_idx__selector__fault[0:0])
  );
  ot_hbm_idx_xq_node_static #(.WI(297)) hb_idx__xq_N (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .a({hb_idx__s_NW__score[0:0], hb_idx__s_NW__score[305:286], hb_idx__s_NW__score[145:130], hb_idx__s_NW__score[17:17], hb_idx__s_NW__score[285:266], hb_idx__s_NW__score[129:114], hb_idx__s_NW__score[16:16], hb_idx__s_NW__score[265:246], hb_idx__s_NW__score[113:98], hb_idx__s_NW__score[15:15], hb_idx__s_NW__score[245:226], hb_idx__s_NW__score[97:82], hb_idx__s_NW__score[14:14], hb_idx__s_NW__score[225:206], hb_idx__s_NW__score[81:66], hb_idx__s_NW__score[13:13], hb_idx__s_NW__score[205:186], hb_idx__s_NW__score[65:50], hb_idx__s_NW__score[12:12], hb_idx__s_NW__score[185:166], hb_idx__s_NW__score[49:34], hb_idx__s_NW__score[11:11], hb_idx__s_NW__score[165:146], hb_idx__s_NW__score[33:18], hb_idx__s_NW__score[10:10]}),
    .b({hb_idx__s_NE__score[0:0], hb_idx__s_NE__score[305:286], hb_idx__s_NE__score[145:130], hb_idx__s_NE__score[17:17], hb_idx__s_NE__score[285:266], hb_idx__s_NE__score[129:114], hb_idx__s_NE__score[16:16], hb_idx__s_NE__score[265:246], hb_idx__s_NE__score[113:98], hb_idx__s_NE__score[15:15], hb_idx__s_NE__score[245:226], hb_idx__s_NE__score[97:82], hb_idx__s_NE__score[14:14], hb_idx__s_NE__score[225:206], hb_idx__s_NE__score[81:66], hb_idx__s_NE__score[13:13], hb_idx__s_NE__score[205:186], hb_idx__s_NE__score[65:50], hb_idx__s_NE__score[12:12], hb_idx__s_NE__score[185:166], hb_idx__s_NE__score[49:34], hb_idx__s_NE__score[11:11], hb_idx__s_NE__score[165:146], hb_idx__s_NE__score[33:18], hb_idx__s_NE__score[10:10]}),
    .y(hb_idx__xq_N__y[593:0])
  );
  ot_hbm_idx_xq_node_static #(.WI(297)) hb_idx__xq_S (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .a({hb_idx__s_SW__score[0:0], hb_idx__s_SW__score[305:286], hb_idx__s_SW__score[145:130], hb_idx__s_SW__score[17:17], hb_idx__s_SW__score[285:266], hb_idx__s_SW__score[129:114], hb_idx__s_SW__score[16:16], hb_idx__s_SW__score[265:246], hb_idx__s_SW__score[113:98], hb_idx__s_SW__score[15:15], hb_idx__s_SW__score[245:226], hb_idx__s_SW__score[97:82], hb_idx__s_SW__score[14:14], hb_idx__s_SW__score[225:206], hb_idx__s_SW__score[81:66], hb_idx__s_SW__score[13:13], hb_idx__s_SW__score[205:186], hb_idx__s_SW__score[65:50], hb_idx__s_SW__score[12:12], hb_idx__s_SW__score[185:166], hb_idx__s_SW__score[49:34], hb_idx__s_SW__score[11:11], hb_idx__s_SW__score[165:146], hb_idx__s_SW__score[33:18], hb_idx__s_SW__score[10:10]}),
    .b({hb_idx__s_SE__score[0:0], hb_idx__s_SE__score[305:286], hb_idx__s_SE__score[145:130], hb_idx__s_SE__score[17:17], hb_idx__s_SE__score[285:266], hb_idx__s_SE__score[129:114], hb_idx__s_SE__score[16:16], hb_idx__s_SE__score[265:246], hb_idx__s_SE__score[113:98], hb_idx__s_SE__score[15:15], hb_idx__s_SE__score[245:226], hb_idx__s_SE__score[97:82], hb_idx__s_SE__score[14:14], hb_idx__s_SE__score[225:206], hb_idx__s_SE__score[81:66], hb_idx__s_SE__score[13:13], hb_idx__s_SE__score[205:186], hb_idx__s_SE__score[65:50], hb_idx__s_SE__score[12:12], hb_idx__s_SE__score[185:166], hb_idx__s_SE__score[49:34], hb_idx__s_SE__score[11:11], hb_idx__s_SE__score[165:146], hb_idx__s_SE__score[33:18], hb_idx__s_SE__score[10:10]}),
    .y(hb_idx__xq_S__y[593:0])
  );
  ot_hbm_idx_xq_node_static #(.WI(594)) hb_idx__xqr (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .a(hb_idx__xq_S__y[593:0]),
    .b(hb_idx__xq_N__y[593:0]),
    .y(hb_idx__xqr__y[1187:0])
  );
  hbfd_qdq_split_and hb_quant_NW__hbfd_qdq_split_and (
    .A(hb_quant_NW__program_leaf__command_v[0:0]),
    .B(hb_quant_NW__program_leaf__command[0:0]),
    .Y(hb_quant_NW__hbfd_qdq_split_and__Y[0:0])
  );
  hbfd_qdq_split_or hb_quant_NW__hbfd_qdq_split_or (
    .A(hb_quant_NW__program_leaf__fault[0:0]),
    .B(hb_quant_NW__quant_NW_xp_ctl__fault[0:0]),
    .Y(hb_quant_NW__hbfd_qdq_split_or__Y[0:0])
  );
  ot_hgi_qdq_nw_program_leaf #(.COMPACT(1), .PIN_BOUNDARY(1)) hb_quant_NW__program_leaf (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .cfg_v(hleaf_NW__a_cfg_v[0:0]),
    .cfg_target(hleaf_NW__a_cfg_target[7:0]),
    .cfg_addr(hleaf_NW__a_cfg_addr[11:0]),
    .cfg_data(hleaf_NW__a_cfg_data[255:0]),
    .desc_v(hleaf_NW__a_desc_v[0:0]),
    .desc_base(hleaf_NW__a_desc_base[11:0]),
    .desc_limit(hleaf_NW__a_desc_limit[12:0]),
    .desc_loops(hleaf_NW__a_desc_loops[15:0]),
    .launch_v(hleaf_NW__a_launch_v[0:0]),
    .command(hb_quant_NW__program_leaf__command[47:0]),
    .command_v(hb_quant_NW__program_leaf__command_v[0:0]),
    .ordinal(hb_quant_NW__program_leaf__ordinal[31:0]),
    .active(hb_quant_NW__program_leaf__active[0:0]),
    .done(hb_quant_NW__program_leaf__done[0:0]),
    .configured(hb_quant_NW__program_leaf__configured[0:0]),
    .fault(hb_quant_NW__program_leaf__fault[0:0])
  );
  ot_hgi_qdq_lg_bf16_r2 #(.BANKS(2)) hb_quant_NW__quant_NW0_lg (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .rq_i(hb_quant_NW__quant_NW_xp_ctl__rq[33:0]),
    .rq_o(hb_quant_NW__quant_NW0_lg__rq_o[33:0]),
    .rr_i(hb_idx__nwsh__b_rr[513:0]),
    .rr_o(hb_quant_NW__quant_NW0_lg__rr_o[513:0]),
    .wq_i({hb_quant_NW__quant_NW_xp_ctl__wq_v[1:1], hb_quant_NW__quant_NW_xp_ctl__wq_addr[31:16], hb_quant_NW__quant_NW_xp_slice_3__wslice__wq_w[63:32], hb_quant_NW__quant_NW_xp_slice_2__wslice__wq_w[63:32], hb_quant_NW__quant_NW_xp_slice_1__wslice__wq_w[63:32], hb_quant_NW__quant_NW_xp_slice_0__wslice__wq_w[63:32], hb_quant_NW__quant_NW_xp_ctl__wq_mask[15:8], hb_quant_NW__quant_NW_xp_ctl__wq_v[0:0], hb_quant_NW__quant_NW_xp_ctl__wq_addr[15:0], hb_quant_NW__quant_NW_xp_slice_3__wslice__wq_w[31:0], hb_quant_NW__quant_NW_xp_slice_2__wslice__wq_w[31:0], hb_quant_NW__quant_NW_xp_slice_1__wslice__wq_w[31:0], hb_quant_NW__quant_NW_xp_slice_0__wslice__wq_w[31:0], hb_quant_NW__quant_NW_xp_ctl__wq_mask[7:0]}),
    .wq_o(hb_quant_NW__quant_NW0_lg__wq_o[561:0])
  );
  ot_hgi_qdq_lg_bf16_r2 #(.BANKS(2)) hb_quant_NW__quant_NW1_lg (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .rq_i(hb_quant_NW__quant_NW_xp_ctl__rq[67:34]),
    .rq_o(hb_quant_NW__quant_NW1_lg__rq_o[33:0]),
    .rr_i(hb_idx__nwsh__b_rr[1027:514]),
    .rr_o(hb_quant_NW__quant_NW1_lg__rr_o[513:0]),
    .wq_i({hb_quant_NW__quant_NW_xp_ctl__wq_v[3:3], hb_quant_NW__quant_NW_xp_ctl__wq_addr[63:48], hb_quant_NW__quant_NW_xp_slice_3__wslice__wq_w[127:96], hb_quant_NW__quant_NW_xp_slice_2__wslice__wq_w[127:96], hb_quant_NW__quant_NW_xp_slice_1__wslice__wq_w[127:96], hb_quant_NW__quant_NW_xp_slice_0__wslice__wq_w[127:96], hb_quant_NW__quant_NW_xp_ctl__wq_mask[31:24], hb_quant_NW__quant_NW_xp_ctl__wq_v[2:2], hb_quant_NW__quant_NW_xp_ctl__wq_addr[47:32], hb_quant_NW__quant_NW_xp_slice_3__wslice__wq_w[95:64], hb_quant_NW__quant_NW_xp_slice_2__wslice__wq_w[95:64], hb_quant_NW__quant_NW_xp_slice_1__wslice__wq_w[95:64], hb_quant_NW__quant_NW_xp_slice_0__wslice__wq_w[95:64], hb_quant_NW__quant_NW_xp_ctl__wq_mask[23:16]}),
    .wq_o(hb_quant_NW__quant_NW1_lg__wq_o[561:0])
  );
  ot_hgi_qdq_lg_bf16_r2 #(.BANKS(2)) hb_quant_NW__quant_NW2_lg (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .rq_i(hb_quant_NW__quant_NW_xp_ctl__rq[101:68]),
    .rq_o(hb_quant_NW__quant_NW2_lg__rq_o[33:0]),
    .rr_i(hb_idx__nwsh__b_rr[1541:1028]),
    .rr_o(hb_quant_NW__quant_NW2_lg__rr_o[513:0]),
    .wq_i({hb_quant_NW__quant_NW_xp_ctl__wq_v[5:5], hb_quant_NW__quant_NW_xp_ctl__wq_addr[95:80], hb_quant_NW__quant_NW_xp_slice_3__wslice__wq_w[191:160], hb_quant_NW__quant_NW_xp_slice_2__wslice__wq_w[191:160], hb_quant_NW__quant_NW_xp_slice_1__wslice__wq_w[191:160], hb_quant_NW__quant_NW_xp_slice_0__wslice__wq_w[191:160], hb_quant_NW__quant_NW_xp_ctl__wq_mask[47:40], hb_quant_NW__quant_NW_xp_ctl__wq_v[4:4], hb_quant_NW__quant_NW_xp_ctl__wq_addr[79:64], hb_quant_NW__quant_NW_xp_slice_3__wslice__wq_w[159:128], hb_quant_NW__quant_NW_xp_slice_2__wslice__wq_w[159:128], hb_quant_NW__quant_NW_xp_slice_1__wslice__wq_w[159:128], hb_quant_NW__quant_NW_xp_slice_0__wslice__wq_w[159:128], hb_quant_NW__quant_NW_xp_ctl__wq_mask[39:32]}),
    .wq_o(hb_quant_NW__quant_NW2_lg__wq_o[561:0])
  );
  ot_hgi_qdq_lg_bf16_r2 #(.BANKS(2)) hb_quant_NW__quant_NW3_lg (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .rq_i(hb_quant_NW__quant_NW_xp_ctl__rq[135:102]),
    .rq_o(hb_quant_NW__quant_NW3_lg__rq_o[33:0]),
    .rr_i(hb_idx__nwsh__b_rr[2055:1542]),
    .rr_o(hb_quant_NW__quant_NW3_lg__rr_o[513:0]),
    .wq_i({hb_quant_NW__quant_NW_xp_ctl__wq_v[7:7], hb_quant_NW__quant_NW_xp_ctl__wq_addr[127:112], hb_quant_NW__quant_NW_xp_slice_3__wslice__wq_w[255:224], hb_quant_NW__quant_NW_xp_slice_2__wslice__wq_w[255:224], hb_quant_NW__quant_NW_xp_slice_1__wslice__wq_w[255:224], hb_quant_NW__quant_NW_xp_slice_0__wslice__wq_w[255:224], hb_quant_NW__quant_NW_xp_ctl__wq_mask[63:56], hb_quant_NW__quant_NW_xp_ctl__wq_v[6:6], hb_quant_NW__quant_NW_xp_ctl__wq_addr[111:96], hb_quant_NW__quant_NW_xp_slice_3__wslice__wq_w[223:192], hb_quant_NW__quant_NW_xp_slice_2__wslice__wq_w[223:192], hb_quant_NW__quant_NW_xp_slice_1__wslice__wq_w[223:192], hb_quant_NW__quant_NW_xp_slice_0__wslice__wq_w[223:192], hb_quant_NW__quant_NW_xp_ctl__wq_mask[55:48]}),
    .wq_o(hb_quant_NW__quant_NW3_lg__wq_o[561:0])
  );
  ot_hgi_qdq_transport_ctl_r4 #(.DL(25), .MUT(0)) hb_quant_NW__quant_NW_xp_ctl (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .rl_cfg(7'b1111110),
    .wc_cfg(6'b010010),
    .cmd_v(hb_quant_NW__hbfd_qdq_split_and__Y[0:0]),
    .cmd_op(hb_quant_NW__program_leaf__command[6:1]),
    .cmd_block(hb_quant_NW__program_leaf__command[14:7]),
    .cmd_src(hb_quant_NW__program_leaf__command[30:15]),
    .cmd_dst(hb_quant_NW__program_leaf__command[46:31]),
    .cmd_last(hb_quant_NW__program_leaf__command[47:47]),
    .rq(hb_quant_NW__quant_NW_xp_ctl__rq[135:0]),
    .rr_v({hb_quant_NW__quant_NW3_lg__rr_o[513:513], hb_quant_NW__quant_NW3_lg__rr_o[256:256], hb_quant_NW__quant_NW2_lg__rr_o[513:513], hb_quant_NW__quant_NW2_lg__rr_o[256:256], hb_quant_NW__quant_NW1_lg__rr_o[513:513], hb_quant_NW__quant_NW1_lg__rr_o[256:256], hb_quant_NW__quant_NW0_lg__rr_o[513:513], hb_quant_NW__quant_NW0_lg__rr_o[256:256]}),
    .wq_v(hb_quant_NW__quant_NW_xp_ctl__wq_v[7:0]),
    .wq_addr(hb_quant_NW__quant_NW_xp_ctl__wq_addr[127:0]),
    .wq_mask(hb_quant_NW__quant_NW_xp_ctl__wq_mask[63:0]),
    .rsel(hb_quant_NW__quant_NW_xp_ctl__rsel[2:0]),
    .wsel(hb_quant_NW__quant_NW_xp_ctl__wsel[2:0]),
    .beat_done(hb_quant_NW__quant_NW_xp_ctl__beat_done[0:0]),
    .record_done(hb_quant_NW__quant_NW_xp_ctl__record_done[0:0]),
    .fault(hb_quant_NW__quant_NW_xp_ctl__fault[0:0]),
    .dec_v(hb_quant_NW__quant_NW_xp_ctl__dec_v[0:0]),
    .dec_header(hb_quant_NW__quant_NW_xp_ctl__dec_header[127:0]),
    .vo(hb_quant_NW__u_dec__vo[0:0]),
    .qfault(hb_quant_NW__u_dec__fault[0:0]),
    .decode_fault(hb_quant_NW__u_dec__decode_fault[0:0])
  );
  ot_hgi_qdq_transport_rslice #(.MUT(0), .NW(2)) hb_quant_NW__quant_NW_xp_slice_0__rslice (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rr_w({hb_quant_NW__quant_NW3_lg__rr_o[320:257], hb_quant_NW__quant_NW3_lg__rr_o[63:0], hb_quant_NW__quant_NW2_lg__rr_o[320:257], hb_quant_NW__quant_NW2_lg__rr_o[63:0], hb_quant_NW__quant_NW1_lg__rr_o[320:257], hb_quant_NW__quant_NW1_lg__rr_o[63:0], hb_quant_NW__quant_NW0_lg__rr_o[320:257], hb_quant_NW__quant_NW0_lg__rr_o[63:0]}),
    .rsel(hb_quant_NW__quant_NW_xp_ctl__rsel[2:0]),
    .gx_w(hb_quant_NW__quant_NW_xp_slice_0__rslice__gx_w[255:0])
  );
  ot_hgi_qdq_transport_wslice #(.MUT(0), .NW(2)) hb_quant_NW__quant_NW_xp_slice_0__wslice (
    .clk(hb_ckgen__pll_stream[0:0]),
    .y_w({hb_quant_NW__u_dec__y[415:384], hb_quant_NW__u_dec__y[287:256], hb_quant_NW__u_dec__y[159:128], hb_quant_NW__u_dec__y[31:0]}),
    .wsel(hb_quant_NW__quant_NW_xp_ctl__wsel[2:0]),
    .wq_w(hb_quant_NW__quant_NW_xp_slice_0__wslice__wq_w[255:0])
  );
  ot_hgi_qdq_transport_rslice #(.MUT(0), .NW(2)) hb_quant_NW__quant_NW_xp_slice_1__rslice (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rr_w({hb_quant_NW__quant_NW3_lg__rr_o[384:321], hb_quant_NW__quant_NW3_lg__rr_o[127:64], hb_quant_NW__quant_NW2_lg__rr_o[384:321], hb_quant_NW__quant_NW2_lg__rr_o[127:64], hb_quant_NW__quant_NW1_lg__rr_o[384:321], hb_quant_NW__quant_NW1_lg__rr_o[127:64], hb_quant_NW__quant_NW0_lg__rr_o[384:321], hb_quant_NW__quant_NW0_lg__rr_o[127:64]}),
    .rsel(hb_quant_NW__quant_NW_xp_ctl__rsel[2:0]),
    .gx_w(hb_quant_NW__quant_NW_xp_slice_1__rslice__gx_w[255:0])
  );
  ot_hgi_qdq_transport_wslice #(.MUT(0), .NW(2)) hb_quant_NW__quant_NW_xp_slice_1__wslice (
    .clk(hb_ckgen__pll_stream[0:0]),
    .y_w({hb_quant_NW__u_dec__y[447:416], hb_quant_NW__u_dec__y[319:288], hb_quant_NW__u_dec__y[191:160], hb_quant_NW__u_dec__y[63:32]}),
    .wsel(hb_quant_NW__quant_NW_xp_ctl__wsel[2:0]),
    .wq_w(hb_quant_NW__quant_NW_xp_slice_1__wslice__wq_w[255:0])
  );
  ot_hgi_qdq_transport_rslice #(.MUT(0), .NW(2)) hb_quant_NW__quant_NW_xp_slice_2__rslice (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rr_w({hb_quant_NW__quant_NW3_lg__rr_o[448:385], hb_quant_NW__quant_NW3_lg__rr_o[191:128], hb_quant_NW__quant_NW2_lg__rr_o[448:385], hb_quant_NW__quant_NW2_lg__rr_o[191:128], hb_quant_NW__quant_NW1_lg__rr_o[448:385], hb_quant_NW__quant_NW1_lg__rr_o[191:128], hb_quant_NW__quant_NW0_lg__rr_o[448:385], hb_quant_NW__quant_NW0_lg__rr_o[191:128]}),
    .rsel(hb_quant_NW__quant_NW_xp_ctl__rsel[2:0]),
    .gx_w(hb_quant_NW__quant_NW_xp_slice_2__rslice__gx_w[255:0])
  );
  ot_hgi_qdq_transport_wslice #(.MUT(0), .NW(2)) hb_quant_NW__quant_NW_xp_slice_2__wslice (
    .clk(hb_ckgen__pll_stream[0:0]),
    .y_w({hb_quant_NW__u_dec__y[479:448], hb_quant_NW__u_dec__y[351:320], hb_quant_NW__u_dec__y[223:192], hb_quant_NW__u_dec__y[95:64]}),
    .wsel(hb_quant_NW__quant_NW_xp_ctl__wsel[2:0]),
    .wq_w(hb_quant_NW__quant_NW_xp_slice_2__wslice__wq_w[255:0])
  );
  ot_hgi_qdq_transport_rslice #(.MUT(0), .NW(2)) hb_quant_NW__quant_NW_xp_slice_3__rslice (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rr_w({hb_quant_NW__quant_NW3_lg__rr_o[512:449], hb_quant_NW__quant_NW3_lg__rr_o[255:192], hb_quant_NW__quant_NW2_lg__rr_o[512:449], hb_quant_NW__quant_NW2_lg__rr_o[255:192], hb_quant_NW__quant_NW1_lg__rr_o[512:449], hb_quant_NW__quant_NW1_lg__rr_o[255:192], hb_quant_NW__quant_NW0_lg__rr_o[512:449], hb_quant_NW__quant_NW0_lg__rr_o[255:192]}),
    .rsel(hb_quant_NW__quant_NW_xp_ctl__rsel[2:0]),
    .gx_w(hb_quant_NW__quant_NW_xp_slice_3__rslice__gx_w[255:0])
  );
  ot_hgi_qdq_transport_wslice #(.MUT(0), .NW(2)) hb_quant_NW__quant_NW_xp_slice_3__wslice (
    .clk(hb_ckgen__pll_stream[0:0]),
    .y_w({hb_quant_NW__u_dec__y[511:480], hb_quant_NW__u_dec__y[383:352], hb_quant_NW__u_dec__y[255:224], hb_quant_NW__u_dec__y[127:96]}),
    .wsel(hb_quant_NW__quant_NW_xp_ctl__wsel[2:0]),
    .wq_w(hb_quant_NW__quant_NW_xp_slice_3__wslice__wq_w[255:0])
  );
  ot_hgi_qw_dec hb_quant_NW__u_dec (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .v(hb_quant_NW__quant_NW_xp_ctl__dec_v[0:0]),
    .header(hb_quant_NW__quant_NW_xp_ctl__dec_header[127:0]),
    .x({hb_quant_NW__quant_NW_xp_slice_3__rslice__gx_w[255:192], hb_quant_NW__quant_NW_xp_slice_2__rslice__gx_w[255:192], hb_quant_NW__quant_NW_xp_slice_1__rslice__gx_w[255:192], hb_quant_NW__quant_NW_xp_slice_0__rslice__gx_w[255:192], hb_quant_NW__quant_NW_xp_slice_3__rslice__gx_w[191:128], hb_quant_NW__quant_NW_xp_slice_2__rslice__gx_w[191:128], hb_quant_NW__quant_NW_xp_slice_1__rslice__gx_w[191:128], hb_quant_NW__quant_NW_xp_slice_0__rslice__gx_w[191:128], hb_quant_NW__quant_NW_xp_slice_3__rslice__gx_w[127:64], hb_quant_NW__quant_NW_xp_slice_2__rslice__gx_w[127:64], hb_quant_NW__quant_NW_xp_slice_1__rslice__gx_w[127:64], hb_quant_NW__quant_NW_xp_slice_0__rslice__gx_w[127:64], hb_quant_NW__quant_NW_xp_slice_3__rslice__gx_w[63:0], hb_quant_NW__quant_NW_xp_slice_2__rslice__gx_w[63:0], hb_quant_NW__quant_NW_xp_slice_1__rslice__gx_w[63:0], hb_quant_NW__quant_NW_xp_slice_0__rslice__gx_w[63:0]}),
    .vo(hb_quant_NW__u_dec__vo[0:0]),
    .y(hb_quant_NW__u_dec__y[511:0]),
    .fault(hb_quant_NW__u_dec__fault[0:0]),
    .decode_fault(hb_quant_NW__u_dec__decode_fault[0:0])
  );
  ot_hbm_router_ids_static_2src #(.XRT(1), .GO_DELAY(1), .CQ_DELAY(1)) hb_router_ids (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .run_v(cp_svg_NW0__run_v[0:0]),
    .run_layer(cp_svg_NW0__run_arg[7:0]),
    .topk_go(col_idx__go[0:0]),
    .topk_rec(col_idx__rec[155:0]),
    .cq(hb_idx__ctl__cq[337:0]),
    .cq_seq(hb_idx__ctl__cq_seq[1:0]),
    .ids_v(hb_router_ids__ids_v[0:0]),
    .ids_layer(hb_router_ids__ids_layer[7:0]),
    .ids(hb_router_ids__ids[53:0]),
    .ids_cohort(hb_router_ids__ids_cohort[15:0]),
    .fault(hb_router_ids__fault[0:0]),
    .run1_v(cp_svg_NW4__run_v[0:0]),
    .run1_layer(cp_svg_NW4__run_arg[7:0])
  );
  hfd_hgi_vms_static_NE_glue hb_vms_NE (
    .clk_hub(hb_ckgen__pll_stream[0:0]),
    .clk_ring({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .clk_replay(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .client_seq(calendar_NE__client_seq[1:0]),
    .response_enable(calendar_NE__response_enable[0:0]),
    .response_seq(calendar_NE__response_seq[1:0]),
    .bank_enable(calendar_NE__bank_enable[7:0]),
    .bank_client(calendar_NE__bank_client[7:0]),
    .hub_ring_enable(calendar_NE__hub_ring_enable[1:0]),
    .hub_ring_client(calendar_NE__hub_ring_client[1:0]),
    .cw_in(hb_vms_SE__cw_out[2223:0]),
    .ccw_in(hb_vms_NW__ccw_out[2223:0]),
    .cw_out(hb_vms_NE__cw_out[2223:0]),
    .ccw_out(hb_vms_NE__ccw_out[2223:0]),
    .ring_tx_enable(calendar_NE__ring_tx_enable[1:0]),
    .ring_tx_source(calendar_NE__ring_tx_source[5:0]),
    .replay_enable(calendar_NE__replay_enable[0:0]),
    .replay_source(calendar_NE__replay_source[0:0]),
    .bank_status({vmb_NE7__status[17:0], vmb_NE6__status[17:0], vmb_NE5__status[17:0], vmb_NE4__status[17:0], vmb_NE3__status[17:0], vmb_NE2__status[17:0], vmb_NE1__status[17:0], vmb_NE0__status[17:0]}),
    .bk_xq(hb_vms_NE__bk_xq[2207:0]),
    .bk_xq2(hb_vms_NE__bk_xq2[2207:0]),
    .bk_xq_done({vmb_NE7__xq_done[0:0], vmb_NE6__xq_done[0:0], vmb_NE5__xq_done[0:0], vmb_NE4__xq_done[0:0], vmb_NE3__xq_done[0:0], vmb_NE2__xq_done[0:0], vmb_NE1__xq_done[0:0], vmb_NE0__xq_done[0:0]}),
    .bk_xq2_done({vmb_NE7__xq2_done[0:0], vmb_NE6__xq2_done[0:0], vmb_NE5__xq2_done[0:0], vmb_NE4__xq2_done[0:0], vmb_NE3__xq2_done[0:0], vmb_NE2__xq2_done[0:0], vmb_NE1__xq2_done[0:0], vmb_NE0__xq2_done[0:0]}),
    .bk_eg({vmb_NE7__eg[275:0], vmb_NE6__eg[275:0], vmb_NE5__eg[275:0], vmb_NE4__eg[275:0], vmb_NE3__eg[275:0], vmb_NE2__eg[275:0], vmb_NE1__eg[275:0], vmb_NE0__eg[275:0]}),
    .bk_pq(hb_vms_NE__bk_pq[2279:0]),
    .bk_pr({vmb_NE7__pr[265:0], vmb_NE6__pr[265:0], vmb_NE5__pr[265:0], vmb_NE4__pr[265:0], vmb_NE3__pr[265:0], vmb_NE2__pr[265:0], vmb_NE1__pr[265:0], vmb_NE0__pr[265:0]}),
    .hub_status(hb_vms_NE__hub_status[2:0]),
    .mirror_busy(hb_vms_NE__mirror_busy[1:0]),
    .vmstat(hb_vms_NE__vmstat[18:0]),
    .ring_fault(hb_vms_NE__ring_fault[2:0])
  );
  hfd_hgi_vms_glue_nw_t hb_vms_NW (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .client_seq(calendar_NW__client_seq[1:0]),
    .response_enable(calendar_NW__response_enable[0:0]),
    .response_seq(calendar_NW__response_seq[1:0]),
    .bank_enable(calendar_NW__bank_enable[7:0]),
    .bank_client(calendar_NW__bank_client[7:0]),
    .hub_ring_enable(calendar_NW__hub_ring_enable[1:0]),
    .hub_ring_client(calendar_NW__hub_ring_client[1:0]),
    .cw_in(hb_vms_NE__cw_out[2223:0]),
    .ccw_in(hb_vms_SW__ccw_out[2223:0]),
    .cw_out(hb_vms_NW__cw_out[2223:0]),
    .ccw_out(hb_vms_NW__ccw_out[2223:0]),
    .ring_tx_enable(calendar_NW__ring_tx_enable[1:0]),
    .ring_tx_source(calendar_NW__ring_tx_source[5:0]),
    .replay_enable(calendar_NW__replay_enable[0:0]),
    .replay_source(calendar_NW__replay_source[0:0]),
    .b0_xq(hb_vms_NW__b0_xq[275:0]),
    .b0_xq2(hb_vms_NW__b0_xq2[275:0]),
    .b0_xq_done(vmb_NW0__xq_done[0:0]),
    .b0_xq2_done(vmb_NW0__xq2_done[0:0]),
    .b0_eg(vmb_NW0__eg[275:0]),
    .b0_pq(hb_vms_NW__b0_pq[284:0]),
    .b0_pr(vmb_NW0__pr[265:0]),
    .b0_status(vmb_NW0__status[17:0]),
    .b0_flt(vmm_NW0__flt[0:0]),
    .b1_xq(hb_vms_NW__b1_xq[275:0]),
    .b1_xq2(hb_vms_NW__b1_xq2[275:0]),
    .b1_xq_done(vmb_NW1__xq_done[0:0]),
    .b1_xq2_done(vmb_NW1__xq2_done[0:0]),
    .b1_eg(vmb_NW1__eg[275:0]),
    .b1_pq(hb_vms_NW__b1_pq[284:0]),
    .b1_pr(vmb_NW1__pr[265:0]),
    .b1_status(vmb_NW1__status[17:0]),
    .b1_flt(vmm_NW1__flt[0:0]),
    .b2_xq(hb_vms_NW__b2_xq[275:0]),
    .b2_xq2(hb_vms_NW__b2_xq2[275:0]),
    .b2_xq_done(vmb_NW2__xq_done[0:0]),
    .b2_xq2_done(vmb_NW2__xq2_done[0:0]),
    .b2_eg(vmb_NW2__eg[275:0]),
    .b2_pq(hb_vms_NW__b2_pq[284:0]),
    .b2_pr(vmb_NW2__pr[265:0]),
    .b2_status(vmb_NW2__status[17:0]),
    .b2_flt(vmm_NW2__flt[0:0]),
    .b3_xq(hb_vms_NW__b3_xq[275:0]),
    .b3_xq2(hb_vms_NW__b3_xq2[275:0]),
    .b3_xq_done(vmb_NW3__xq_done[0:0]),
    .b3_xq2_done(vmb_NW3__xq2_done[0:0]),
    .b3_eg(vmb_NW3__eg[275:0]),
    .b3_pq(hb_vms_NW__b3_pq[284:0]),
    .b3_pr(vmb_NW3__pr[265:0]),
    .b3_status(vmb_NW3__status[17:0]),
    .b3_flt(vmm_NW3__flt[0:0]),
    .b4_xq(hb_vms_NW__b4_xq[275:0]),
    .b4_xq2(hb_vms_NW__b4_xq2[275:0]),
    .b4_xq_done(vmb_NW4__xq_done[0:0]),
    .b4_xq2_done(vmb_NW4__xq2_done[0:0]),
    .b4_eg(vmb_NW4__eg[275:0]),
    .b4_pq(hb_vms_NW__b4_pq[284:0]),
    .b4_pr(vmb_NW4__pr[265:0]),
    .b4_status(vmb_NW4__status[17:0]),
    .b4_flt(vmm_NW4__flt[0:0]),
    .b5_xq(hb_vms_NW__b5_xq[275:0]),
    .b5_xq2(hb_vms_NW__b5_xq2[275:0]),
    .b5_xq_done(vmb_NW5__xq_done[0:0]),
    .b5_xq2_done(vmb_NW5__xq2_done[0:0]),
    .b5_eg(vmb_NW5__eg[275:0]),
    .b5_pq(hb_vms_NW__b5_pq[284:0]),
    .b5_pr(vmb_NW5__pr[265:0]),
    .b5_status(vmb_NW5__status[17:0]),
    .b5_flt(vmm_NW5__flt[0:0]),
    .b6_xq(hb_vms_NW__b6_xq[275:0]),
    .b6_xq2(hb_vms_NW__b6_xq2[275:0]),
    .b6_xq_done(vmb_NW6__xq_done[0:0]),
    .b6_xq2_done(vmb_NW6__xq2_done[0:0]),
    .b6_eg(vmb_NW6__eg[275:0]),
    .b6_pq(hb_vms_NW__b6_pq[284:0]),
    .b6_pr(vmb_NW6__pr[265:0]),
    .b6_status(vmb_NW6__status[17:0]),
    .b6_flt(vmm_NW6__flt[0:0]),
    .b7_xq(hb_vms_NW__b7_xq[275:0]),
    .b7_xq2(hb_vms_NW__b7_xq2[275:0]),
    .b7_xq_done(vmb_NW7__xq_done[0:0]),
    .b7_xq2_done(vmb_NW7__xq2_done[0:0]),
    .b7_eg(vmb_NW7__eg[275:0]),
    .b7_pq(hb_vms_NW__b7_pq[284:0]),
    .b7_pr(vmb_NW7__pr[265:0]),
    .b7_status(vmb_NW7__status[17:0]),
    .b7_flt(vmm_NW7__flt[0:0]),
    .hub_status(hb_vms_NW__hub_status[2:0]),
    .mirror_busy(hb_vms_NW__mirror_busy[1:0]),
    .vmstat(hb_vms_NW__vmstat[18:0]),
    .ring_fault(hb_vms_NW__ring_fault[2:0])
  );
  hfd_hgi_vms_static_SE_glue hb_vms_SE (
    .clk_hub(hb_ckgen__pll_stream[0:0]),
    .clk_ring({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .clk_replay(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .client_seq(calendar_SE__client_seq[1:0]),
    .response_enable(calendar_SE__response_enable[0:0]),
    .response_seq(calendar_SE__response_seq[1:0]),
    .bank_enable(calendar_SE__bank_enable[7:0]),
    .bank_client(calendar_SE__bank_client[7:0]),
    .hub_ring_enable(calendar_SE__hub_ring_enable[1:0]),
    .hub_ring_client(calendar_SE__hub_ring_client[1:0]),
    .cw_in(hb_vms_SW__cw_out[2223:0]),
    .ccw_in(hb_vms_NE__ccw_out[2223:0]),
    .cw_out(hb_vms_SE__cw_out[2223:0]),
    .ccw_out(hb_vms_SE__ccw_out[2223:0]),
    .ring_tx_enable(calendar_SE__ring_tx_enable[1:0]),
    .ring_tx_source(calendar_SE__ring_tx_source[5:0]),
    .replay_enable(calendar_SE__replay_enable[0:0]),
    .replay_source(calendar_SE__replay_source[0:0]),
    .bank_status({vmb_SE7__status[17:0], vmb_SE6__status[17:0], vmb_SE5__status[17:0], vmb_SE4__status[17:0], vmb_SE3__status[17:0], vmb_SE2__status[17:0], vmb_SE1__status[17:0], vmb_SE0__status[17:0]}),
    .bk_xq(hb_vms_SE__bk_xq[2207:0]),
    .bk_xq2(hb_vms_SE__bk_xq2[2207:0]),
    .bk_xq_done({vmb_SE7__xq_done[0:0], vmb_SE6__xq_done[0:0], vmb_SE5__xq_done[0:0], vmb_SE4__xq_done[0:0], vmb_SE3__xq_done[0:0], vmb_SE2__xq_done[0:0], vmb_SE1__xq_done[0:0], vmb_SE0__xq_done[0:0]}),
    .bk_xq2_done({vmb_SE7__xq2_done[0:0], vmb_SE6__xq2_done[0:0], vmb_SE5__xq2_done[0:0], vmb_SE4__xq2_done[0:0], vmb_SE3__xq2_done[0:0], vmb_SE2__xq2_done[0:0], vmb_SE1__xq2_done[0:0], vmb_SE0__xq2_done[0:0]}),
    .bk_eg({vmb_SE7__eg[275:0], vmb_SE6__eg[275:0], vmb_SE5__eg[275:0], vmb_SE4__eg[275:0], vmb_SE3__eg[275:0], vmb_SE2__eg[275:0], vmb_SE1__eg[275:0], vmb_SE0__eg[275:0]}),
    .bk_pq(hb_vms_SE__bk_pq[2279:0]),
    .bk_pr({vmb_SE7__pr[265:0], vmb_SE6__pr[265:0], vmb_SE5__pr[265:0], vmb_SE4__pr[265:0], vmb_SE3__pr[265:0], vmb_SE2__pr[265:0], vmb_SE1__pr[265:0], vmb_SE0__pr[265:0]}),
    .hub_status(hb_vms_SE__hub_status[2:0]),
    .mirror_busy(hb_vms_SE__mirror_busy[1:0]),
    .vmstat(hb_vms_SE__vmstat[18:0]),
    .ring_fault(hb_vms_SE__ring_fault[2:0])
  );
  hfd_hgi_vms_glue_sw_t hb_vms_SW (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .cq({hb_idx__ctl__cq[337:0], hb_argmax__cq[337:0]}),
    .cr(hb_vms_SW__cr[547:0]),
    .client_seq(calendar_SW__client_seq[5:0]),
    .response_enable(calendar_SW__response_enable[2:0]),
    .response_seq(calendar_SW__response_seq[5:0]),
    .bank_enable(calendar_SW__bank_enable[7:0]),
    .bank_client(calendar_SW__bank_client[15:0]),
    .hub_ring_enable(calendar_SW__hub_ring_enable[1:0]),
    .hub_ring_client(calendar_SW__hub_ring_client[3:0]),
    .cw_in(hb_vms_NW__cw_out[2223:0]),
    .ccw_in(hb_vms_SE__ccw_out[2223:0]),
    .cw_out(hb_vms_SW__cw_out[2223:0]),
    .ccw_out(hb_vms_SW__ccw_out[2223:0]),
    .ring_tx_enable(calendar_SW__ring_tx_enable[1:0]),
    .ring_tx_source(calendar_SW__ring_tx_source[5:0]),
    .replay_enable(calendar_SW__replay_enable[0:0]),
    .replay_source(calendar_SW__replay_source[0:0]),
    .b0_xq(hb_vms_SW__b0_xq[275:0]),
    .b0_xq2(hb_vms_SW__b0_xq2[275:0]),
    .b0_xq_done(vmb_SW0__xq_done[0:0]),
    .b0_xq2_done(vmb_SW0__xq2_done[0:0]),
    .b0_eg(vmb_SW0__eg[275:0]),
    .b0_pq(hb_vms_SW__b0_pq[284:0]),
    .b0_pr(vmb_SW0__pr[265:0]),
    .b0_status(vmb_SW0__status[17:0]),
    .b1_xq(hb_vms_SW__b1_xq[275:0]),
    .b1_xq2(hb_vms_SW__b1_xq2[275:0]),
    .b1_xq_done(vmb_SW1__xq_done[0:0]),
    .b1_xq2_done(vmb_SW1__xq2_done[0:0]),
    .b1_eg(vmb_SW1__eg[275:0]),
    .b1_pq(hb_vms_SW__b1_pq[284:0]),
    .b1_pr(vmb_SW1__pr[265:0]),
    .b1_status(vmb_SW1__status[17:0]),
    .b2_xq(hb_vms_SW__b2_xq[275:0]),
    .b2_xq2(hb_vms_SW__b2_xq2[275:0]),
    .b2_xq_done(vmb_SW2__xq_done[0:0]),
    .b2_xq2_done(vmb_SW2__xq2_done[0:0]),
    .b2_eg(vmb_SW2__eg[275:0]),
    .b2_pq(hb_vms_SW__b2_pq[284:0]),
    .b2_pr(vmb_SW2__pr[265:0]),
    .b2_status(vmb_SW2__status[17:0]),
    .b3_xq(hb_vms_SW__b3_xq[275:0]),
    .b3_xq2(hb_vms_SW__b3_xq2[275:0]),
    .b3_xq_done(vmb_SW3__xq_done[0:0]),
    .b3_xq2_done(vmb_SW3__xq2_done[0:0]),
    .b3_eg(vmb_SW3__eg[275:0]),
    .b3_pq(hb_vms_SW__b3_pq[284:0]),
    .b3_pr(vmb_SW3__pr[265:0]),
    .b3_status(vmb_SW3__status[17:0]),
    .b4_xq(hb_vms_SW__b4_xq[275:0]),
    .b4_xq2(hb_vms_SW__b4_xq2[275:0]),
    .b4_xq_done(vmb_SW4__xq_done[0:0]),
    .b4_xq2_done(vmb_SW4__xq2_done[0:0]),
    .b4_eg(vmb_SW4__eg[275:0]),
    .b4_pq(hb_vms_SW__b4_pq[284:0]),
    .b4_pr(vmb_SW4__pr[265:0]),
    .b4_status(vmb_SW4__status[17:0]),
    .b5_xq(hb_vms_SW__b5_xq[275:0]),
    .b5_xq2(hb_vms_SW__b5_xq2[275:0]),
    .b5_xq_done(vmb_SW5__xq_done[0:0]),
    .b5_xq2_done(vmb_SW5__xq2_done[0:0]),
    .b5_eg(vmb_SW5__eg[275:0]),
    .b5_pq(hb_vms_SW__b5_pq[284:0]),
    .b5_pr(vmb_SW5__pr[265:0]),
    .b5_status(vmb_SW5__status[17:0]),
    .b6_xq(hb_vms_SW__b6_xq[275:0]),
    .b6_xq2(hb_vms_SW__b6_xq2[275:0]),
    .b6_xq_done(vmb_SW6__xq_done[0:0]),
    .b6_xq2_done(vmb_SW6__xq2_done[0:0]),
    .b6_eg(vmb_SW6__eg[275:0]),
    .b6_pq(hb_vms_SW__b6_pq[284:0]),
    .b6_pr(vmb_SW6__pr[265:0]),
    .b6_status(vmb_SW6__status[17:0]),
    .b7_xq(hb_vms_SW__b7_xq[275:0]),
    .b7_xq2(hb_vms_SW__b7_xq2[275:0]),
    .b7_xq_done(vmb_SW7__xq_done[0:0]),
    .b7_xq2_done(vmb_SW7__xq2_done[0:0]),
    .b7_eg(vmb_SW7__eg[275:0]),
    .b7_pq(hb_vms_SW__b7_pq[284:0]),
    .b7_pr(vmb_SW7__pr[265:0]),
    .b7_status(vmb_SW7__status[17:0]),
    .hub_status(hb_vms_SW__hub_status[2:0]),
    .mirror_busy(hb_vms_SW__mirror_busy[1:0]),
    .vmstat(hb_vms_SW__vmstat[18:0]),
    .ring_fault(hb_vms_SW__ring_fault[2:0])
  );
  ot_hbm_hc_qhub_static #(.DRLY(2), .CHX(11), .RD_CAPTURE(51), .GATHER_PHASE(51), .DONE_LAT(47), .W(128)) hc_NE (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .tgt(8'b01101111),
    .cfg_v(hleaf_NE__b_cfg_v[0:0]),
    .cfg_target(hleaf_NE__b_cfg_target[7:0]),
    .cfg_addr(hleaf_NE__b_cfg_addr[11:0]),
    .cfg_data(hleaf_NE__b_cfg_data[255:0]),
    .desc_v(hleaf_NE__b_desc_v[0:0]),
    .desc_base(hleaf_NE__b_desc_base[11:0]),
    .desc_limit(hleaf_NE__b_desc_limit[12:0]),
    .desc_loops(hleaf_NE__b_desc_loops[15:0]),
    .launch_v(hleaf_NE__b_launch_v[0:0]),
    .configured(hc_NE__configured[0:0]),
    .lg_rq(hc_NE__lg_rq[135:0]),
    .lg_wq(hc_NE__lg_wq[2247:0]),
    .lg_rr({hc_NE3__c_rr[513:0], hc_NE2__c_rr[513:0], hc_NE1__c_rr[513:0], hc_NE0__c_rr[513:0]}),
    .lg_w_done({hc_NE3__c_w_done[1:0], hc_NE2__c_w_done[1:0], hc_NE1__c_w_done[1:0], hc_NE0__c_w_done[1:0]}),
    .residual_done(hc_NE__residual_done[0:0]),
    .gathered_mix_v(hc_NE__gathered_mix_v[0:0]),
    .gathered_mix_row(hc_NE__gathered_mix_row[4:0]),
    .gathered_mix_pos(hc_NE__gathered_mix_pos[2:0]),
    .gathered_mix_data(hc_NE__gathered_mix_data[31:0]),
    .gather_done(hc_NE__gather_done[0:0]),
    .result_v(hc_eng__result_v[1:1]),
    .result_position(hc_eng__result_position[5:3]),
    .result(hc_eng__result[1535:768]),
    .program_active(hc_NE__program_active[0:0]),
    .program_done(hc_NE__program_done[0:0]),
    .hcq_fault(hc_NE__hcq_fault[0:0]),
    .d_v(hc_eng__qd_v[1:1]),
    .d_ss(hc_eng__qd_ss[1:1]),
    .d_nv(hc_eng__qd_nv[15:8]),
    .d_wa(hc_eng__qd_wa[19:10]),
    .d_xa(hc_eng__qd_xa[19:10]),
    .i_v(hc_eng__qi_v[1:1]),
    .i_kind(hc_eng__qi_kind[1:1]),
    .i_slot(hc_eng__qi_slot[3:2]),
    .i_lo(hc_eng__qi_lo[9:5]),
    .i_w(hc_eng__qi_w[11:6]),
    .i_cnt(hc_eng__qi_cnt[23:12]),
    .i_word(hc_eng__qi_word[19:10]),
    .ps_v(hc_NE__ps_v[0:0]),
    .ps(hc_NE__ps[31:0]),
    .ps_f(hc_NE__ps_f[0:0]),
    .eng_fault(hc_NE__eng_fault[0:0]),
    .rstb_w(hc_NE__rstb_w[0:0]),
    .rstb_e(hc_NE__rstb_e[0:0]),
    .rstb_n(hc_NE__rstb_n[2:0]),
    .rstb_s(hc_NE__rstb_s[2:0]),
    .bd_v(hc_NE__bd_v[0:0]),
    .bd_ss(hc_NE__bd_ss[0:0]),
    .bd_nv(hc_NE__bd_nv[7:0]),
    .bd_wa(hc_NE__bd_wa[9:0]),
    .bd_xa(hc_NE__bd_xa[9:0]),
    .s_i(hcb_NE0__s_o[4096:0]),
    .wf_w(hcb_NE0__wfault[0:0]),
    .wf_e(hcb_NE4__wfault[0:0]),
    .wf_n({hcb_NE2__fb_wfault_o[0:0], hcb_NE2__wfault[0:0], hcb_NE2__fa_wfault_o[0:0]}),
    .wf_s({hcb_NE6__fb_wfault_o[0:0], hcb_NE6__wfault[0:0], hcb_NE6__fa_wfault_o[0:0]}),
    .wc_w(hc_NE__wc_w[13:0]),
    .wc_n(hc_NE__wc_n[13:0]),
    .wc_e(hc_NE__wc_e[13:0]),
    .wc_s(hc_NE__wc_s[13:0]),
    .xb_v(hc_NE__xb_v[0:0]),
    .xb_beat(hc_NE__xb_beat[1:0]),
    .xb_v_n(hc_NE__xb_v_n[0:0]),
    .xb_v_e(hc_NE__xb_v_e[0:0]),
    .xb_v_s(hc_NE__xb_v_s[0:0]),
    .xb_beat_n(hc_NE__xb_beat_n[1:0]),
    .xb_beat_e(hc_NE__xb_beat_e[1:0]),
    .xb_beat_s(hc_NE__xb_beat_s[1:0]),
    .xb_d0(hc_NE__xb_d0[255:0]),
    .xb_d1(hc_NE__xb_d1[255:0]),
    .xb_d2(hc_NE__xb_d2[255:0]),
    .xb_d3(hc_NE__xb_d3[255:0]),
    .xb_d4(hc_NE__xb_d4[255:0]),
    .xb_d5(hc_NE__xb_d5[255:0]),
    .xb_d6(hc_NE__xb_d6[255:0]),
    .xb_d7(hc_NE__xb_d7[255:0])
  );
  ot_hgi_sfu_lg_pair_tap_leaf_term #(.READ_RETURN(33), .WRITE_RETURN(30)) hc_NE0 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .c_rq(hc_NE__lg_rq[33:0]),
    .c_wq(hc_NE__lg_wq[561:0]),
    .c_rr(hc_NE0__c_rr[513:0]),
    .c_w_done(hc_NE0__c_w_done[1:0]),
    .local_read(calendar_NE__lg_local_read[17:16]),
    .local_write(calendar_NE__lg_local_write[17:16]),
    .near_rq(hc_NE0__near_rq[33:0]),
    .near_wq(hc_NE0__near_wq[561:0]),
    .near_rr(sfu_NE0__far_rr[513:0]),
    .near_w_done(sfu_NE0__far_w_done[1:0]),
    .fault(hc_NE0__fault[0:0])
  );
  ot_hgi_sfu_lg_pair_tap_leaf_term #(.READ_RETURN(23), .WRITE_RETURN(20)) hc_NE1 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .c_rq(hc_NE__lg_rq[67:34]),
    .c_wq(hc_NE__lg_wq[1123:562]),
    .c_rr(hc_NE1__c_rr[513:0]),
    .c_w_done(hc_NE1__c_w_done[1:0]),
    .local_read(calendar_NE__lg_local_read[19:18]),
    .local_write(calendar_NE__lg_local_write[19:18]),
    .near_rq(hc_NE1__near_rq[33:0]),
    .near_wq(hc_NE1__near_wq[561:0]),
    .near_rr(sfu_NE1__far_rr[513:0]),
    .near_w_done(sfu_NE1__far_w_done[1:0]),
    .fault(hc_NE1__fault[0:0])
  );
  ot_hgi_sfu_lg_pair_tap_leaf_term #(.READ_RETURN(27), .WRITE_RETURN(24)) hc_NE2 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .c_rq(hc_NE__lg_rq[101:68]),
    .c_wq(hc_NE__lg_wq[1685:1124]),
    .c_rr(hc_NE2__c_rr[513:0]),
    .c_w_done(hc_NE2__c_w_done[1:0]),
    .local_read(calendar_NE__lg_local_read[21:20]),
    .local_write(calendar_NE__lg_local_write[21:20]),
    .near_rq(hc_NE2__near_rq[33:0]),
    .near_wq(hc_NE2__near_wq[561:0]),
    .near_rr(sfu_NE2__far_rr[513:0]),
    .near_w_done(sfu_NE2__far_w_done[1:0]),
    .fault(hc_NE2__fault[0:0])
  );
  ot_hgi_sfu_lg_pair_tap_leaf_term #(.READ_RETURN(23), .WRITE_RETURN(20)) hc_NE3 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .c_rq(hc_NE__lg_rq[135:102]),
    .c_wq(hc_NE__lg_wq[2247:1686]),
    .c_rr(hc_NE3__c_rr[513:0]),
    .c_w_done(hc_NE3__c_w_done[1:0]),
    .local_read(calendar_NE__lg_local_read[23:22]),
    .local_write(calendar_NE__lg_local_write[23:22]),
    .near_rq(hc_NE3__near_rq[33:0]),
    .near_wq(hc_NE3__near_wq[561:0]),
    .near_rr(sfu_NE3__far_rr[513:0]),
    .near_w_done(sfu_NE3__far_w_done[1:0]),
    .fault(hc_NE3__fault[0:0])
  );
  ot_hbm_hc_qhub_static #(.DRLY(2), .CHX(11), .RD_CAPTURE(51), .GATHER_PHASE(51), .DONE_LAT(47), .W(128)) hc_NW (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .tgt(8'b01101110),
    .cfg_v(hleaf_NW__b_cfg_v[0:0]),
    .cfg_target(hleaf_NW__b_cfg_target[7:0]),
    .cfg_addr(hleaf_NW__b_cfg_addr[11:0]),
    .cfg_data(hleaf_NW__b_cfg_data[255:0]),
    .desc_v(hleaf_NW__b_desc_v[0:0]),
    .desc_base(hleaf_NW__b_desc_base[11:0]),
    .desc_limit(hleaf_NW__b_desc_limit[12:0]),
    .desc_loops(hleaf_NW__b_desc_loops[15:0]),
    .launch_v(hleaf_NW__b_launch_v[0:0]),
    .configured(hc_NW__configured[0:0]),
    .lg_rq(hc_NW__lg_rq[135:0]),
    .lg_wq(hc_NW__lg_wq[2247:0]),
    .lg_rr({hc_NW3__c_rr[513:0], hc_NW2__c_rr[513:0], hc_NW1__c_rr[513:0], hc_NW0__c_rr[513:0]}),
    .lg_w_done({hc_NW3__c_w_done[1:0], hc_NW2__c_w_done[1:0], hc_NW1__c_w_done[1:0], hc_NW0__c_w_done[1:0]}),
    .residual_done(hc_NW__residual_done[0:0]),
    .gathered_mix_v(hc_NW__gathered_mix_v[0:0]),
    .gathered_mix_row(hc_NW__gathered_mix_row[4:0]),
    .gathered_mix_pos(hc_NW__gathered_mix_pos[2:0]),
    .gathered_mix_data(hc_NW__gathered_mix_data[31:0]),
    .gather_done(hc_NW__gather_done[0:0]),
    .result_v(hc_eng__result_v[0:0]),
    .result_position(hc_eng__result_position[2:0]),
    .result(hc_eng__result[767:0]),
    .program_active(hc_NW__program_active[0:0]),
    .program_done(hc_NW__program_done[0:0]),
    .hcq_fault(hc_NW__hcq_fault[0:0]),
    .d_v(hc_eng__qd_v[0:0]),
    .d_ss(hc_eng__qd_ss[0:0]),
    .d_nv(hc_eng__qd_nv[7:0]),
    .d_wa(hc_eng__qd_wa[9:0]),
    .d_xa(hc_eng__qd_xa[9:0]),
    .i_v(hc_eng__qi_v[0:0]),
    .i_kind(hc_eng__qi_kind[0:0]),
    .i_slot(hc_eng__qi_slot[1:0]),
    .i_lo(hc_eng__qi_lo[4:0]),
    .i_w(hc_eng__qi_w[5:0]),
    .i_cnt(hc_eng__qi_cnt[11:0]),
    .i_word(hc_eng__qi_word[9:0]),
    .ps_v(hc_NW__ps_v[0:0]),
    .ps(hc_NW__ps[31:0]),
    .ps_f(hc_NW__ps_f[0:0]),
    .eng_fault(hc_NW__eng_fault[0:0]),
    .rstb_w(hc_NW__rstb_w[0:0]),
    .rstb_e(hc_NW__rstb_e[0:0]),
    .rstb_n(hc_NW__rstb_n[2:0]),
    .rstb_s(hc_NW__rstb_s[2:0]),
    .bd_v(hc_NW__bd_v[0:0]),
    .bd_ss(hc_NW__bd_ss[0:0]),
    .bd_nv(hc_NW__bd_nv[7:0]),
    .bd_wa(hc_NW__bd_wa[9:0]),
    .bd_xa(hc_NW__bd_xa[9:0]),
    .s_i(hcb_NW0__s_o[4096:0]),
    .wf_w(hcb_NW0__wfault[0:0]),
    .wf_e(hcb_NW4__wfault[0:0]),
    .wf_n({hcb_NW2__fb_wfault_o[0:0], hcb_NW2__wfault[0:0], hcb_NW2__fa_wfault_o[0:0]}),
    .wf_s({hcb_NW6__fb_wfault_o[0:0], hcb_NW6__wfault[0:0], hcb_NW6__fa_wfault_o[0:0]}),
    .wc_w(hc_NW__wc_w[13:0]),
    .wc_n(hc_NW__wc_n[13:0]),
    .wc_e(hc_NW__wc_e[13:0]),
    .wc_s(hc_NW__wc_s[13:0]),
    .xb_v(hc_NW__xb_v[0:0]),
    .xb_beat(hc_NW__xb_beat[1:0]),
    .xb_v_n(hc_NW__xb_v_n[0:0]),
    .xb_v_e(hc_NW__xb_v_e[0:0]),
    .xb_v_s(hc_NW__xb_v_s[0:0]),
    .xb_beat_n(hc_NW__xb_beat_n[1:0]),
    .xb_beat_e(hc_NW__xb_beat_e[1:0]),
    .xb_beat_s(hc_NW__xb_beat_s[1:0]),
    .xb_d0(hc_NW__xb_d0[255:0]),
    .xb_d1(hc_NW__xb_d1[255:0]),
    .xb_d2(hc_NW__xb_d2[255:0]),
    .xb_d3(hc_NW__xb_d3[255:0]),
    .xb_d4(hc_NW__xb_d4[255:0]),
    .xb_d5(hc_NW__xb_d5[255:0]),
    .xb_d6(hc_NW__xb_d6[255:0]),
    .xb_d7(hc_NW__xb_d7[255:0])
  );
  ot_hgi_sfu_lg_pair_tap_leaf_term #(.READ_RETURN(33), .WRITE_RETURN(30)) hc_NW0 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .c_rq(hc_NW__lg_rq[33:0]),
    .c_wq(hc_NW__lg_wq[561:0]),
    .c_rr(hc_NW0__c_rr[513:0]),
    .c_w_done(hc_NW0__c_w_done[1:0]),
    .local_read(calendar_NW__lg_local_read[17:16]),
    .local_write(calendar_NW__lg_local_write[17:16]),
    .near_rq(hc_NW0__near_rq[33:0]),
    .near_wq(hc_NW0__near_wq[561:0]),
    .near_rr(sfu_NW0__far_rr[513:0]),
    .near_w_done(sfu_NW0__far_w_done[1:0]),
    .fault(hc_NW0__fault[0:0])
  );
  ot_hgi_sfu_lg_pair_tap_leaf_term #(.READ_RETURN(23), .WRITE_RETURN(20)) hc_NW1 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .c_rq(hc_NW__lg_rq[67:34]),
    .c_wq(hc_NW__lg_wq[1123:562]),
    .c_rr(hc_NW1__c_rr[513:0]),
    .c_w_done(hc_NW1__c_w_done[1:0]),
    .local_read(calendar_NW__lg_local_read[19:18]),
    .local_write(calendar_NW__lg_local_write[19:18]),
    .near_rq(hc_NW1__near_rq[33:0]),
    .near_wq(hc_NW1__near_wq[561:0]),
    .near_rr(sfu_NW1__far_rr[513:0]),
    .near_w_done(sfu_NW1__far_w_done[1:0]),
    .fault(hc_NW1__fault[0:0])
  );
  ot_hgi_sfu_lg_pair_tap_leaf_term #(.READ_RETURN(27), .WRITE_RETURN(24)) hc_NW2 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .c_rq(hc_NW__lg_rq[101:68]),
    .c_wq(hc_NW__lg_wq[1685:1124]),
    .c_rr(hc_NW2__c_rr[513:0]),
    .c_w_done(hc_NW2__c_w_done[1:0]),
    .local_read(calendar_NW__lg_local_read[21:20]),
    .local_write(calendar_NW__lg_local_write[21:20]),
    .near_rq(hc_NW2__near_rq[33:0]),
    .near_wq(hc_NW2__near_wq[561:0]),
    .near_rr(sfu_NW2__far_rr[513:0]),
    .near_w_done(sfu_NW2__far_w_done[1:0]),
    .fault(hc_NW2__fault[0:0])
  );
  ot_hgi_sfu_lg_pair_tap_leaf_term #(.READ_RETURN(23), .WRITE_RETURN(20)) hc_NW3 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .c_rq(hc_NW__lg_rq[135:102]),
    .c_wq(hc_NW__lg_wq[2247:1686]),
    .c_rr(hc_NW3__c_rr[513:0]),
    .c_w_done(hc_NW3__c_w_done[1:0]),
    .local_read(calendar_NW__lg_local_read[23:22]),
    .local_write(calendar_NW__lg_local_write[23:22]),
    .near_rq(hc_NW3__near_rq[33:0]),
    .near_wq(hc_NW3__near_wq[561:0]),
    .near_rr(sfu_NW3__far_rr[513:0]),
    .near_w_done(sfu_NW3__far_w_done[1:0]),
    .fault(hc_NW3__fault[0:0])
  );
  ot_hbm_hc_root_static #(.QDRLY(2), .QCHX(11), .NQ(2)) hc_eng (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .tgt(8'b10100100),
    .cfg_v(hleaf_NE__a_cfg_v[0:0]),
    .cfg_target(hleaf_NE__a_cfg_target[7:0]),
    .cfg_addr(hleaf_NE__a_cfg_addr[11:0]),
    .cfg_data(hleaf_NE__a_cfg_data[255:0]),
    .desc_v(hleaf_NE__a_desc_v[0:0]),
    .desc_base(hleaf_NE__a_desc_base[11:0]),
    .desc_limit(hleaf_NE__a_desc_limit[12:0]),
    .desc_loops(hleaf_NE__a_desc_loops[15:0]),
    .launch_v(hleaf_NE__a_launch_v[0:0]),
    .configured(hc_eng__configured[0:0]),
    .qd_v(hc_eng__qd_v[1:0]),
    .qd_ss(hc_eng__qd_ss[1:0]),
    .qd_nv(hc_eng__qd_nv[15:0]),
    .qd_wa(hc_eng__qd_wa[19:0]),
    .qd_xa(hc_eng__qd_xa[19:0]),
    .qi_v(hc_eng__qi_v[1:0]),
    .qi_kind(hc_eng__qi_kind[1:0]),
    .qi_slot(hc_eng__qi_slot[3:0]),
    .qi_lo(hc_eng__qi_lo[9:0]),
    .qi_w(hc_eng__qi_w[11:0]),
    .qi_cnt(hc_eng__qi_cnt[23:0]),
    .qi_word(hc_eng__qi_word[19:0]),
    .qps_v({hc_NE__ps_v[0:0], hc_NW__ps_v[0:0]}),
    .qps({hc_NE__ps[31:0], hc_NW__ps[31:0]}),
    .qps_f({hc_NE__ps_f[0:0], hc_NW__ps_f[0:0]}),
    .q_fault({hc_NE__eng_fault[0:0], hc_NW__eng_fault[0:0]}),
    .gathered_mix_v({hc_NE__gathered_mix_v[0:0], hc_NW__gathered_mix_v[0:0]}),
    .gathered_mix_row({hc_NE__gathered_mix_row[4:0], hc_NW__gathered_mix_row[4:0]}),
    .gathered_mix_pos({hc_NE__gathered_mix_pos[2:0], hc_NW__gathered_mix_pos[2:0]}),
    .gathered_mix_data({hc_NE__gathered_mix_data[31:0], hc_NW__gathered_mix_data[31:0]}),
    .result_v(hc_eng__result_v[1:0]),
    .result_position(hc_eng__result_position[5:0]),
    .result(hc_eng__result[1535:0]),
    .program_active(hc_eng__program_active[0:0]),
    .program_done(hc_eng__program_done[0:0]),
    .fault(hc_eng__fault[0:0])
  );
  ot_hbm_hc_bankq0_static #(.DRLY(2), .CPO(1), .W(128)) hcb_NE0 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hc_NE__rstb_w[0:0]),
    .d_v(hc_NE__bd_v[0:0]),
    .d_ss(hc_NE__bd_ss[0:0]),
    .d_nv(hc_NE__bd_nv[7:0]),
    .d_wa(hc_NE__bd_wa[9:0]),
    .d_xa(hc_NE__bd_xa[9:0]),
    .o_v(hcb_NE0__o_v[0:0]),
    .o_ss(hcb_NE0__o_ss[0:0]),
    .o_nv(hcb_NE0__o_nv[7:0]),
    .o_wa(hcb_NE0__o_wa[9:0]),
    .o_xa(hcb_NE0__o_xa[9:0]),
    .sum_out(hcb_NE0__sum_out[4095:0]),
    .f_out(hcb_NE0__f_out[0:0]),
    .xb_v(hc_NE__xb_v[0:0]),
    .xb_beat(hc_NE__xb_beat[1:0]),
    .xb_d(hc_NE__xb_d0[255:0]),
    .wv(hc_NE__wc_w[13:13]),
    .xv(hc_NE__wc_w[12:12]),
    .j(hc_NE__wc_w[11:10]),
    .wa(hc_NE__wc_w[9:0]),
    .wfault(hcb_NE0__wfault[0:0]),
    .s_i({hcb_NE7__f_out[0:0], hcb_NE7__sum_out[4095:0]}),
    .s_o(hcb_NE0__s_o[4096:0])
  );
  ot_hbm_hc_bankq_static #(.CPI(1), .CPO(1), .W(128)) hcb_NE1 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hcb_NE2__fa_rst_n_o[0:0]),
    .d_v(hcb_NE0__o_v[0:0]),
    .d_ss(hcb_NE0__o_ss[0:0]),
    .d_nv(hcb_NE0__o_nv[7:0]),
    .d_wa(hcb_NE0__o_wa[9:0]),
    .d_xa(hcb_NE0__o_xa[9:0]),
    .o_v(hcb_NE1__o_v[0:0]),
    .o_ss(hcb_NE1__o_ss[0:0]),
    .o_nv(hcb_NE1__o_nv[7:0]),
    .o_wa(hcb_NE1__o_wa[9:0]),
    .o_xa(hcb_NE1__o_xa[9:0]),
    .sum_in(hcb_NE0__sum_out[4095:0]),
    .sum_out(hcb_NE1__sum_out[4095:0]),
    .f_in(hcb_NE0__f_out[0:0]),
    .f_out(hcb_NE1__f_out[0:0]),
    .xb_v(hcb_NE2__fa_xb_v_o[0:0]),
    .xb_beat(hcb_NE2__fa_xb_beat_o[1:0]),
    .xb_d(hcb_NE2__fa_xb_d_o[255:0]),
    .wv(hcb_NE2__fa_wv_o[0:0]),
    .xv(hcb_NE2__fa_xv_o[0:0]),
    .j(hcb_NE2__fa_j_o[1:0]),
    .wa(hcb_NE2__fa_wa_o[9:0]),
    .wfault(hcb_NE1__wfault[0:0])
  );
  ot_hbm_hc_bankq_ft_static #(.W(128)) hcb_NE2 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hc_NE__rstb_n[1:1]),
    .d_v(hcb_NE1__o_v[0:0]),
    .d_ss(hcb_NE1__o_ss[0:0]),
    .d_nv(hcb_NE1__o_nv[7:0]),
    .d_wa(hcb_NE1__o_wa[9:0]),
    .d_xa(hcb_NE1__o_xa[9:0]),
    .o_v(hcb_NE2__o_v[0:0]),
    .o_ss(hcb_NE2__o_ss[0:0]),
    .o_nv(hcb_NE2__o_nv[7:0]),
    .o_wa(hcb_NE2__o_wa[9:0]),
    .o_xa(hcb_NE2__o_xa[9:0]),
    .sum_in(hcb_NE1__sum_out[4095:0]),
    .sum_out(hcb_NE2__sum_out[4095:0]),
    .f_in(hcb_NE1__f_out[0:0]),
    .f_out(hcb_NE2__f_out[0:0]),
    .xb_v(hc_NE__xb_v_n[0:0]),
    .xb_beat(hc_NE__xb_beat_n[1:0]),
    .xb_d(hc_NE__xb_d2[255:0]),
    .wv(hc_NE__wc_n[13:13]),
    .xv(hc_NE__wc_n[12:12]),
    .j(hc_NE__wc_n[11:10]),
    .wa(hc_NE__wc_n[9:0]),
    .wfault(hcb_NE2__wfault[0:0]),
    .fa_xb_v(hc_NE__xb_v_n[0:0]),
    .fa_xb_beat(hc_NE__xb_beat_n[1:0]),
    .fa_xb_d(hc_NE__xb_d1[255:0]),
    .fa_wv(hc_NE__wc_n[13:13]),
    .fa_xv(hc_NE__wc_n[12:12]),
    .fa_j(hc_NE__wc_n[11:10]),
    .fa_wa(hc_NE__wc_n[9:0]),
    .fa_xb_v_o(hcb_NE2__fa_xb_v_o[0:0]),
    .fa_xb_beat_o(hcb_NE2__fa_xb_beat_o[1:0]),
    .fa_xb_d_o(hcb_NE2__fa_xb_d_o[255:0]),
    .fa_wv_o(hcb_NE2__fa_wv_o[0:0]),
    .fa_xv_o(hcb_NE2__fa_xv_o[0:0]),
    .fa_j_o(hcb_NE2__fa_j_o[1:0]),
    .fa_wa_o(hcb_NE2__fa_wa_o[9:0]),
    .fb_xb_v(hc_NE__xb_v_n[0:0]),
    .fb_xb_beat(hc_NE__xb_beat_n[1:0]),
    .fb_xb_d(hc_NE__xb_d3[255:0]),
    .fb_wv(hc_NE__wc_n[13:13]),
    .fb_xv(hc_NE__wc_n[12:12]),
    .fb_j(hc_NE__wc_n[11:10]),
    .fb_wa(hc_NE__wc_n[9:0]),
    .fb_xb_v_o(hcb_NE2__fb_xb_v_o[0:0]),
    .fb_xb_beat_o(hcb_NE2__fb_xb_beat_o[1:0]),
    .fb_xb_d_o(hcb_NE2__fb_xb_d_o[255:0]),
    .fb_wv_o(hcb_NE2__fb_wv_o[0:0]),
    .fb_xv_o(hcb_NE2__fb_xv_o[0:0]),
    .fb_j_o(hcb_NE2__fb_j_o[1:0]),
    .fb_wa_o(hcb_NE2__fb_wa_o[9:0]),
    .fa_rst_n(hc_NE__rstb_n[0:0]),
    .fb_rst_n(hc_NE__rstb_n[2:2]),
    .fa_rst_n_o(hcb_NE2__fa_rst_n_o[0:0]),
    .fb_rst_n_o(hcb_NE2__fb_rst_n_o[0:0]),
    .fa_wfault(hcb_NE1__wfault[0:0]),
    .fb_wfault(hcb_NE3__wfault[0:0]),
    .fa_wfault_o(hcb_NE2__fa_wfault_o[0:0]),
    .fb_wfault_o(hcb_NE2__fb_wfault_o[0:0])
  );
  ot_hbm_hc_bankq_static #(.CPI(1), .CPO(1), .W(128)) hcb_NE3 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hcb_NE2__fb_rst_n_o[0:0]),
    .d_v(hcb_NE2__o_v[0:0]),
    .d_ss(hcb_NE2__o_ss[0:0]),
    .d_nv(hcb_NE2__o_nv[7:0]),
    .d_wa(hcb_NE2__o_wa[9:0]),
    .d_xa(hcb_NE2__o_xa[9:0]),
    .o_v(hcb_NE3__o_v[0:0]),
    .o_ss(hcb_NE3__o_ss[0:0]),
    .o_nv(hcb_NE3__o_nv[7:0]),
    .o_wa(hcb_NE3__o_wa[9:0]),
    .o_xa(hcb_NE3__o_xa[9:0]),
    .sum_in(hcb_NE2__sum_out[4095:0]),
    .sum_out(hcb_NE3__sum_out[4095:0]),
    .f_in(hcb_NE2__f_out[0:0]),
    .f_out(hcb_NE3__f_out[0:0]),
    .xb_v(hcb_NE2__fb_xb_v_o[0:0]),
    .xb_beat(hcb_NE2__fb_xb_beat_o[1:0]),
    .xb_d(hcb_NE2__fb_xb_d_o[255:0]),
    .wv(hcb_NE2__fb_wv_o[0:0]),
    .xv(hcb_NE2__fb_xv_o[0:0]),
    .j(hcb_NE2__fb_j_o[1:0]),
    .wa(hcb_NE2__fb_wa_o[9:0]),
    .wfault(hcb_NE3__wfault[0:0])
  );
  ot_hbm_hc_bankq_static #(.CPI(1), .CPO(1), .W(128)) hcb_NE4 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hc_NE__rstb_e[0:0]),
    .d_v(hcb_NE3__o_v[0:0]),
    .d_ss(hcb_NE3__o_ss[0:0]),
    .d_nv(hcb_NE3__o_nv[7:0]),
    .d_wa(hcb_NE3__o_wa[9:0]),
    .d_xa(hcb_NE3__o_xa[9:0]),
    .o_v(hcb_NE4__o_v[0:0]),
    .o_ss(hcb_NE4__o_ss[0:0]),
    .o_nv(hcb_NE4__o_nv[7:0]),
    .o_wa(hcb_NE4__o_wa[9:0]),
    .o_xa(hcb_NE4__o_xa[9:0]),
    .sum_in(hcb_NE3__sum_out[4095:0]),
    .sum_out(hcb_NE4__sum_out[4095:0]),
    .f_in(hcb_NE3__f_out[0:0]),
    .f_out(hcb_NE4__f_out[0:0]),
    .xb_v(hc_NE__xb_v_e[0:0]),
    .xb_beat(hc_NE__xb_beat_e[1:0]),
    .xb_d(hc_NE__xb_d4[255:0]),
    .wv(hc_NE__wc_e[13:13]),
    .xv(hc_NE__wc_e[12:12]),
    .j(hc_NE__wc_e[11:10]),
    .wa(hc_NE__wc_e[9:0]),
    .wfault(hcb_NE4__wfault[0:0])
  );
  ot_hbm_hc_bankq_static #(.CPI(1), .CPO(1), .W(128)) hcb_NE5 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hcb_NE6__fa_rst_n_o[0:0]),
    .d_v(hcb_NE4__o_v[0:0]),
    .d_ss(hcb_NE4__o_ss[0:0]),
    .d_nv(hcb_NE4__o_nv[7:0]),
    .d_wa(hcb_NE4__o_wa[9:0]),
    .d_xa(hcb_NE4__o_xa[9:0]),
    .o_v(hcb_NE5__o_v[0:0]),
    .o_ss(hcb_NE5__o_ss[0:0]),
    .o_nv(hcb_NE5__o_nv[7:0]),
    .o_wa(hcb_NE5__o_wa[9:0]),
    .o_xa(hcb_NE5__o_xa[9:0]),
    .sum_in(hcb_NE4__sum_out[4095:0]),
    .sum_out(hcb_NE5__sum_out[4095:0]),
    .f_in(hcb_NE4__f_out[0:0]),
    .f_out(hcb_NE5__f_out[0:0]),
    .xb_v(hcb_NE6__fa_xb_v_o[0:0]),
    .xb_beat(hcb_NE6__fa_xb_beat_o[1:0]),
    .xb_d(hcb_NE6__fa_xb_d_o[255:0]),
    .wv(hcb_NE6__fa_wv_o[0:0]),
    .xv(hcb_NE6__fa_xv_o[0:0]),
    .j(hcb_NE6__fa_j_o[1:0]),
    .wa(hcb_NE6__fa_wa_o[9:0]),
    .wfault(hcb_NE5__wfault[0:0])
  );
  ot_hbm_hc_bankq_ft_static #(.W(128)) hcb_NE6 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hc_NE__rstb_s[1:1]),
    .d_v(hcb_NE5__o_v[0:0]),
    .d_ss(hcb_NE5__o_ss[0:0]),
    .d_nv(hcb_NE5__o_nv[7:0]),
    .d_wa(hcb_NE5__o_wa[9:0]),
    .d_xa(hcb_NE5__o_xa[9:0]),
    .o_v(hcb_NE6__o_v[0:0]),
    .o_ss(hcb_NE6__o_ss[0:0]),
    .o_nv(hcb_NE6__o_nv[7:0]),
    .o_wa(hcb_NE6__o_wa[9:0]),
    .o_xa(hcb_NE6__o_xa[9:0]),
    .sum_in(hcb_NE5__sum_out[4095:0]),
    .sum_out(hcb_NE6__sum_out[4095:0]),
    .f_in(hcb_NE5__f_out[0:0]),
    .f_out(hcb_NE6__f_out[0:0]),
    .xb_v(hc_NE__xb_v_s[0:0]),
    .xb_beat(hc_NE__xb_beat_s[1:0]),
    .xb_d(hc_NE__xb_d6[255:0]),
    .wv(hc_NE__wc_s[13:13]),
    .xv(hc_NE__wc_s[12:12]),
    .j(hc_NE__wc_s[11:10]),
    .wa(hc_NE__wc_s[9:0]),
    .wfault(hcb_NE6__wfault[0:0]),
    .fa_xb_v(hc_NE__xb_v_s[0:0]),
    .fa_xb_beat(hc_NE__xb_beat_s[1:0]),
    .fa_xb_d(hc_NE__xb_d5[255:0]),
    .fa_wv(hc_NE__wc_s[13:13]),
    .fa_xv(hc_NE__wc_s[12:12]),
    .fa_j(hc_NE__wc_s[11:10]),
    .fa_wa(hc_NE__wc_s[9:0]),
    .fa_xb_v_o(hcb_NE6__fa_xb_v_o[0:0]),
    .fa_xb_beat_o(hcb_NE6__fa_xb_beat_o[1:0]),
    .fa_xb_d_o(hcb_NE6__fa_xb_d_o[255:0]),
    .fa_wv_o(hcb_NE6__fa_wv_o[0:0]),
    .fa_xv_o(hcb_NE6__fa_xv_o[0:0]),
    .fa_j_o(hcb_NE6__fa_j_o[1:0]),
    .fa_wa_o(hcb_NE6__fa_wa_o[9:0]),
    .fb_xb_v(hc_NE__xb_v_s[0:0]),
    .fb_xb_beat(hc_NE__xb_beat_s[1:0]),
    .fb_xb_d(hc_NE__xb_d7[255:0]),
    .fb_wv(hc_NE__wc_s[13:13]),
    .fb_xv(hc_NE__wc_s[12:12]),
    .fb_j(hc_NE__wc_s[11:10]),
    .fb_wa(hc_NE__wc_s[9:0]),
    .fb_xb_v_o(hcb_NE6__fb_xb_v_o[0:0]),
    .fb_xb_beat_o(hcb_NE6__fb_xb_beat_o[1:0]),
    .fb_xb_d_o(hcb_NE6__fb_xb_d_o[255:0]),
    .fb_wv_o(hcb_NE6__fb_wv_o[0:0]),
    .fb_xv_o(hcb_NE6__fb_xv_o[0:0]),
    .fb_j_o(hcb_NE6__fb_j_o[1:0]),
    .fb_wa_o(hcb_NE6__fb_wa_o[9:0]),
    .fa_rst_n(hc_NE__rstb_s[0:0]),
    .fb_rst_n(hc_NE__rstb_s[2:2]),
    .fa_rst_n_o(hcb_NE6__fa_rst_n_o[0:0]),
    .fb_rst_n_o(hcb_NE6__fb_rst_n_o[0:0]),
    .fa_wfault(hcb_NE5__wfault[0:0]),
    .fb_wfault(hcb_NE7__wfault[0:0]),
    .fa_wfault_o(hcb_NE6__fa_wfault_o[0:0]),
    .fb_wfault_o(hcb_NE6__fb_wfault_o[0:0])
  );
  ot_hbm_hc_bankq_term_static #(.CPI(1), .CPO(1), .W(128)) hcb_NE7 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hcb_NE6__fb_rst_n_o[0:0]),
    .d_v(hcb_NE6__o_v[0:0]),
    .d_ss(hcb_NE6__o_ss[0:0]),
    .d_nv(hcb_NE6__o_nv[7:0]),
    .d_wa(hcb_NE6__o_wa[9:0]),
    .d_xa(hcb_NE6__o_xa[9:0]),
    .sum_in(hcb_NE6__sum_out[4095:0]),
    .sum_out(hcb_NE7__sum_out[4095:0]),
    .f_in(hcb_NE6__f_out[0:0]),
    .f_out(hcb_NE7__f_out[0:0]),
    .xb_v(hcb_NE6__fb_xb_v_o[0:0]),
    .xb_beat(hcb_NE6__fb_xb_beat_o[1:0]),
    .xb_d(hcb_NE6__fb_xb_d_o[255:0]),
    .wv(hcb_NE6__fb_wv_o[0:0]),
    .xv(hcb_NE6__fb_xv_o[0:0]),
    .j(hcb_NE6__fb_j_o[1:0]),
    .wa(hcb_NE6__fb_wa_o[9:0]),
    .wfault(hcb_NE7__wfault[0:0])
  );
  ot_hbm_hc_bankq0_static #(.DRLY(2), .CPO(1), .W(128)) hcb_NW0 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hc_NW__rstb_w[0:0]),
    .d_v(hc_NW__bd_v[0:0]),
    .d_ss(hc_NW__bd_ss[0:0]),
    .d_nv(hc_NW__bd_nv[7:0]),
    .d_wa(hc_NW__bd_wa[9:0]),
    .d_xa(hc_NW__bd_xa[9:0]),
    .o_v(hcb_NW0__o_v[0:0]),
    .o_ss(hcb_NW0__o_ss[0:0]),
    .o_nv(hcb_NW0__o_nv[7:0]),
    .o_wa(hcb_NW0__o_wa[9:0]),
    .o_xa(hcb_NW0__o_xa[9:0]),
    .sum_out(hcb_NW0__sum_out[4095:0]),
    .f_out(hcb_NW0__f_out[0:0]),
    .xb_v(hc_NW__xb_v[0:0]),
    .xb_beat(hc_NW__xb_beat[1:0]),
    .xb_d(hc_NW__xb_d0[255:0]),
    .wv(hc_NW__wc_w[13:13]),
    .xv(hc_NW__wc_w[12:12]),
    .j(hc_NW__wc_w[11:10]),
    .wa(hc_NW__wc_w[9:0]),
    .wfault(hcb_NW0__wfault[0:0]),
    .s_i({hcb_NW7__f_out[0:0], hcb_NW7__sum_out[4095:0]}),
    .s_o(hcb_NW0__s_o[4096:0])
  );
  ot_hbm_hc_bankq_static #(.CPI(1), .CPO(1), .W(128)) hcb_NW1 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hcb_NW2__fa_rst_n_o[0:0]),
    .d_v(hcb_NW0__o_v[0:0]),
    .d_ss(hcb_NW0__o_ss[0:0]),
    .d_nv(hcb_NW0__o_nv[7:0]),
    .d_wa(hcb_NW0__o_wa[9:0]),
    .d_xa(hcb_NW0__o_xa[9:0]),
    .o_v(hcb_NW1__o_v[0:0]),
    .o_ss(hcb_NW1__o_ss[0:0]),
    .o_nv(hcb_NW1__o_nv[7:0]),
    .o_wa(hcb_NW1__o_wa[9:0]),
    .o_xa(hcb_NW1__o_xa[9:0]),
    .sum_in(hcb_NW0__sum_out[4095:0]),
    .sum_out(hcb_NW1__sum_out[4095:0]),
    .f_in(hcb_NW0__f_out[0:0]),
    .f_out(hcb_NW1__f_out[0:0]),
    .xb_v(hcb_NW2__fa_xb_v_o[0:0]),
    .xb_beat(hcb_NW2__fa_xb_beat_o[1:0]),
    .xb_d(hcb_NW2__fa_xb_d_o[255:0]),
    .wv(hcb_NW2__fa_wv_o[0:0]),
    .xv(hcb_NW2__fa_xv_o[0:0]),
    .j(hcb_NW2__fa_j_o[1:0]),
    .wa(hcb_NW2__fa_wa_o[9:0]),
    .wfault(hcb_NW1__wfault[0:0])
  );
  ot_hbm_hc_bankq_ft_static #(.W(128)) hcb_NW2 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hc_NW__rstb_n[1:1]),
    .d_v(hcb_NW1__o_v[0:0]),
    .d_ss(hcb_NW1__o_ss[0:0]),
    .d_nv(hcb_NW1__o_nv[7:0]),
    .d_wa(hcb_NW1__o_wa[9:0]),
    .d_xa(hcb_NW1__o_xa[9:0]),
    .o_v(hcb_NW2__o_v[0:0]),
    .o_ss(hcb_NW2__o_ss[0:0]),
    .o_nv(hcb_NW2__o_nv[7:0]),
    .o_wa(hcb_NW2__o_wa[9:0]),
    .o_xa(hcb_NW2__o_xa[9:0]),
    .sum_in(hcb_NW1__sum_out[4095:0]),
    .sum_out(hcb_NW2__sum_out[4095:0]),
    .f_in(hcb_NW1__f_out[0:0]),
    .f_out(hcb_NW2__f_out[0:0]),
    .xb_v(hc_NW__xb_v_n[0:0]),
    .xb_beat(hc_NW__xb_beat_n[1:0]),
    .xb_d(hc_NW__xb_d2[255:0]),
    .wv(hc_NW__wc_n[13:13]),
    .xv(hc_NW__wc_n[12:12]),
    .j(hc_NW__wc_n[11:10]),
    .wa(hc_NW__wc_n[9:0]),
    .wfault(hcb_NW2__wfault[0:0]),
    .fa_xb_v(hc_NW__xb_v_n[0:0]),
    .fa_xb_beat(hc_NW__xb_beat_n[1:0]),
    .fa_xb_d(hc_NW__xb_d1[255:0]),
    .fa_wv(hc_NW__wc_n[13:13]),
    .fa_xv(hc_NW__wc_n[12:12]),
    .fa_j(hc_NW__wc_n[11:10]),
    .fa_wa(hc_NW__wc_n[9:0]),
    .fa_xb_v_o(hcb_NW2__fa_xb_v_o[0:0]),
    .fa_xb_beat_o(hcb_NW2__fa_xb_beat_o[1:0]),
    .fa_xb_d_o(hcb_NW2__fa_xb_d_o[255:0]),
    .fa_wv_o(hcb_NW2__fa_wv_o[0:0]),
    .fa_xv_o(hcb_NW2__fa_xv_o[0:0]),
    .fa_j_o(hcb_NW2__fa_j_o[1:0]),
    .fa_wa_o(hcb_NW2__fa_wa_o[9:0]),
    .fb_xb_v(hc_NW__xb_v_n[0:0]),
    .fb_xb_beat(hc_NW__xb_beat_n[1:0]),
    .fb_xb_d(hc_NW__xb_d3[255:0]),
    .fb_wv(hc_NW__wc_n[13:13]),
    .fb_xv(hc_NW__wc_n[12:12]),
    .fb_j(hc_NW__wc_n[11:10]),
    .fb_wa(hc_NW__wc_n[9:0]),
    .fb_xb_v_o(hcb_NW2__fb_xb_v_o[0:0]),
    .fb_xb_beat_o(hcb_NW2__fb_xb_beat_o[1:0]),
    .fb_xb_d_o(hcb_NW2__fb_xb_d_o[255:0]),
    .fb_wv_o(hcb_NW2__fb_wv_o[0:0]),
    .fb_xv_o(hcb_NW2__fb_xv_o[0:0]),
    .fb_j_o(hcb_NW2__fb_j_o[1:0]),
    .fb_wa_o(hcb_NW2__fb_wa_o[9:0]),
    .fa_rst_n(hc_NW__rstb_n[0:0]),
    .fb_rst_n(hc_NW__rstb_n[2:2]),
    .fa_rst_n_o(hcb_NW2__fa_rst_n_o[0:0]),
    .fb_rst_n_o(hcb_NW2__fb_rst_n_o[0:0]),
    .fa_wfault(hcb_NW1__wfault[0:0]),
    .fb_wfault(hcb_NW3__wfault[0:0]),
    .fa_wfault_o(hcb_NW2__fa_wfault_o[0:0]),
    .fb_wfault_o(hcb_NW2__fb_wfault_o[0:0])
  );
  ot_hbm_hc_bankq_static #(.CPI(1), .CPO(1), .W(128)) hcb_NW3 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hcb_NW2__fb_rst_n_o[0:0]),
    .d_v(hcb_NW2__o_v[0:0]),
    .d_ss(hcb_NW2__o_ss[0:0]),
    .d_nv(hcb_NW2__o_nv[7:0]),
    .d_wa(hcb_NW2__o_wa[9:0]),
    .d_xa(hcb_NW2__o_xa[9:0]),
    .o_v(hcb_NW3__o_v[0:0]),
    .o_ss(hcb_NW3__o_ss[0:0]),
    .o_nv(hcb_NW3__o_nv[7:0]),
    .o_wa(hcb_NW3__o_wa[9:0]),
    .o_xa(hcb_NW3__o_xa[9:0]),
    .sum_in(hcb_NW2__sum_out[4095:0]),
    .sum_out(hcb_NW3__sum_out[4095:0]),
    .f_in(hcb_NW2__f_out[0:0]),
    .f_out(hcb_NW3__f_out[0:0]),
    .xb_v(hcb_NW2__fb_xb_v_o[0:0]),
    .xb_beat(hcb_NW2__fb_xb_beat_o[1:0]),
    .xb_d(hcb_NW2__fb_xb_d_o[255:0]),
    .wv(hcb_NW2__fb_wv_o[0:0]),
    .xv(hcb_NW2__fb_xv_o[0:0]),
    .j(hcb_NW2__fb_j_o[1:0]),
    .wa(hcb_NW2__fb_wa_o[9:0]),
    .wfault(hcb_NW3__wfault[0:0])
  );
  ot_hbm_hc_bankq_static #(.CPI(1), .CPO(1), .W(128)) hcb_NW4 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hc_NW__rstb_e[0:0]),
    .d_v(hcb_NW3__o_v[0:0]),
    .d_ss(hcb_NW3__o_ss[0:0]),
    .d_nv(hcb_NW3__o_nv[7:0]),
    .d_wa(hcb_NW3__o_wa[9:0]),
    .d_xa(hcb_NW3__o_xa[9:0]),
    .o_v(hcb_NW4__o_v[0:0]),
    .o_ss(hcb_NW4__o_ss[0:0]),
    .o_nv(hcb_NW4__o_nv[7:0]),
    .o_wa(hcb_NW4__o_wa[9:0]),
    .o_xa(hcb_NW4__o_xa[9:0]),
    .sum_in(hcb_NW3__sum_out[4095:0]),
    .sum_out(hcb_NW4__sum_out[4095:0]),
    .f_in(hcb_NW3__f_out[0:0]),
    .f_out(hcb_NW4__f_out[0:0]),
    .xb_v(hc_NW__xb_v_e[0:0]),
    .xb_beat(hc_NW__xb_beat_e[1:0]),
    .xb_d(hc_NW__xb_d4[255:0]),
    .wv(hc_NW__wc_e[13:13]),
    .xv(hc_NW__wc_e[12:12]),
    .j(hc_NW__wc_e[11:10]),
    .wa(hc_NW__wc_e[9:0]),
    .wfault(hcb_NW4__wfault[0:0])
  );
  ot_hbm_hc_bankq_static #(.CPI(1), .CPO(1), .W(128)) hcb_NW5 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hcb_NW6__fa_rst_n_o[0:0]),
    .d_v(hcb_NW4__o_v[0:0]),
    .d_ss(hcb_NW4__o_ss[0:0]),
    .d_nv(hcb_NW4__o_nv[7:0]),
    .d_wa(hcb_NW4__o_wa[9:0]),
    .d_xa(hcb_NW4__o_xa[9:0]),
    .o_v(hcb_NW5__o_v[0:0]),
    .o_ss(hcb_NW5__o_ss[0:0]),
    .o_nv(hcb_NW5__o_nv[7:0]),
    .o_wa(hcb_NW5__o_wa[9:0]),
    .o_xa(hcb_NW5__o_xa[9:0]),
    .sum_in(hcb_NW4__sum_out[4095:0]),
    .sum_out(hcb_NW5__sum_out[4095:0]),
    .f_in(hcb_NW4__f_out[0:0]),
    .f_out(hcb_NW5__f_out[0:0]),
    .xb_v(hcb_NW6__fa_xb_v_o[0:0]),
    .xb_beat(hcb_NW6__fa_xb_beat_o[1:0]),
    .xb_d(hcb_NW6__fa_xb_d_o[255:0]),
    .wv(hcb_NW6__fa_wv_o[0:0]),
    .xv(hcb_NW6__fa_xv_o[0:0]),
    .j(hcb_NW6__fa_j_o[1:0]),
    .wa(hcb_NW6__fa_wa_o[9:0]),
    .wfault(hcb_NW5__wfault[0:0])
  );
  ot_hbm_hc_bankq_ft_static #(.W(128)) hcb_NW6 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hc_NW__rstb_s[1:1]),
    .d_v(hcb_NW5__o_v[0:0]),
    .d_ss(hcb_NW5__o_ss[0:0]),
    .d_nv(hcb_NW5__o_nv[7:0]),
    .d_wa(hcb_NW5__o_wa[9:0]),
    .d_xa(hcb_NW5__o_xa[9:0]),
    .o_v(hcb_NW6__o_v[0:0]),
    .o_ss(hcb_NW6__o_ss[0:0]),
    .o_nv(hcb_NW6__o_nv[7:0]),
    .o_wa(hcb_NW6__o_wa[9:0]),
    .o_xa(hcb_NW6__o_xa[9:0]),
    .sum_in(hcb_NW5__sum_out[4095:0]),
    .sum_out(hcb_NW6__sum_out[4095:0]),
    .f_in(hcb_NW5__f_out[0:0]),
    .f_out(hcb_NW6__f_out[0:0]),
    .xb_v(hc_NW__xb_v_s[0:0]),
    .xb_beat(hc_NW__xb_beat_s[1:0]),
    .xb_d(hc_NW__xb_d6[255:0]),
    .wv(hc_NW__wc_s[13:13]),
    .xv(hc_NW__wc_s[12:12]),
    .j(hc_NW__wc_s[11:10]),
    .wa(hc_NW__wc_s[9:0]),
    .wfault(hcb_NW6__wfault[0:0]),
    .fa_xb_v(hc_NW__xb_v_s[0:0]),
    .fa_xb_beat(hc_NW__xb_beat_s[1:0]),
    .fa_xb_d(hc_NW__xb_d5[255:0]),
    .fa_wv(hc_NW__wc_s[13:13]),
    .fa_xv(hc_NW__wc_s[12:12]),
    .fa_j(hc_NW__wc_s[11:10]),
    .fa_wa(hc_NW__wc_s[9:0]),
    .fa_xb_v_o(hcb_NW6__fa_xb_v_o[0:0]),
    .fa_xb_beat_o(hcb_NW6__fa_xb_beat_o[1:0]),
    .fa_xb_d_o(hcb_NW6__fa_xb_d_o[255:0]),
    .fa_wv_o(hcb_NW6__fa_wv_o[0:0]),
    .fa_xv_o(hcb_NW6__fa_xv_o[0:0]),
    .fa_j_o(hcb_NW6__fa_j_o[1:0]),
    .fa_wa_o(hcb_NW6__fa_wa_o[9:0]),
    .fb_xb_v(hc_NW__xb_v_s[0:0]),
    .fb_xb_beat(hc_NW__xb_beat_s[1:0]),
    .fb_xb_d(hc_NW__xb_d7[255:0]),
    .fb_wv(hc_NW__wc_s[13:13]),
    .fb_xv(hc_NW__wc_s[12:12]),
    .fb_j(hc_NW__wc_s[11:10]),
    .fb_wa(hc_NW__wc_s[9:0]),
    .fb_xb_v_o(hcb_NW6__fb_xb_v_o[0:0]),
    .fb_xb_beat_o(hcb_NW6__fb_xb_beat_o[1:0]),
    .fb_xb_d_o(hcb_NW6__fb_xb_d_o[255:0]),
    .fb_wv_o(hcb_NW6__fb_wv_o[0:0]),
    .fb_xv_o(hcb_NW6__fb_xv_o[0:0]),
    .fb_j_o(hcb_NW6__fb_j_o[1:0]),
    .fb_wa_o(hcb_NW6__fb_wa_o[9:0]),
    .fa_rst_n(hc_NW__rstb_s[0:0]),
    .fb_rst_n(hc_NW__rstb_s[2:2]),
    .fa_rst_n_o(hcb_NW6__fa_rst_n_o[0:0]),
    .fb_rst_n_o(hcb_NW6__fb_rst_n_o[0:0]),
    .fa_wfault(hcb_NW5__wfault[0:0]),
    .fb_wfault(hcb_NW7__wfault[0:0]),
    .fa_wfault_o(hcb_NW6__fa_wfault_o[0:0]),
    .fb_wfault_o(hcb_NW6__fb_wfault_o[0:0])
  );
  ot_hbm_hc_bankq_term_static #(.CPI(1), .CPO(1), .W(128)) hcb_NW7 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hcb_NW6__fb_rst_n_o[0:0]),
    .d_v(hcb_NW6__o_v[0:0]),
    .d_ss(hcb_NW6__o_ss[0:0]),
    .d_nv(hcb_NW6__o_nv[7:0]),
    .d_wa(hcb_NW6__o_wa[9:0]),
    .d_xa(hcb_NW6__o_xa[9:0]),
    .sum_in(hcb_NW6__sum_out[4095:0]),
    .sum_out(hcb_NW7__sum_out[4095:0]),
    .f_in(hcb_NW6__f_out[0:0]),
    .f_out(hcb_NW7__f_out[0:0]),
    .xb_v(hcb_NW6__fb_xb_v_o[0:0]),
    .xb_beat(hcb_NW6__fb_xb_beat_o[1:0]),
    .xb_d(hcb_NW6__fb_xb_d_o[255:0]),
    .wv(hcb_NW6__fb_wv_o[0:0]),
    .xv(hcb_NW6__fb_xv_o[0:0]),
    .j(hcb_NW6__fb_j_o[1:0]),
    .wa(hcb_NW6__fb_wa_o[9:0]),
    .wfault(hcb_NW7__wfault[0:0])
  );
  ot_hgi_coll_ring_b_stop hcollb_NE (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .qid(2'b11),
    .cw_i(hcollb_NW__cw_o[279:0]),
    .ccw_i(hcollb_NW__ccw_o[279:0]),
    .cw_o(hcollb_NE__cw_o[279:0]),
    .ccw_o(hcollb_NE__ccw_o[279:0]),
    .lp_we(hcollgi_NE__rb_lp_we[0:0]),
    .lp_tag(hcollgi_NE__rb_lp_tag[2:0]),
    .lp_data(hcollgi_NE__rb_lp_data[255:0]),
    .state_read_tx(hcollgi_NE__rb_state_read_tx[0:0]),
    .state_tx_tag(hcollgi_NE__rb_state_tx_tag[2:0]),
    .tx_inject(hcollgi_NE__rb_tx_inject[1:0]),
    .tx_forward(hcollgi_NE__rb_tx_forward[1:0]),
    .tx_tag(hcollgi_NE__rb_tx_tag[2:0]),
    .tx_ttl(hcollgi_NE__rb_tx_ttl[3:0]),
    .rx_slot(hcollgi_NE__rb_rx_slot[1:0]),
    .rx_kind(hcollgi_NE__rb_rx_kind[3:0]),
    .rx_src(hcollgi_NE__rb_rx_src[3:0]),
    .rx_tag(hcollgi_NE__rb_rx_tag[5:0]),
    .ag_v(hcollb_NE__ag_v[1:0]),
    .ag_src(hcollb_NE__ag_src[3:0]),
    .ag_tag(hcollb_NE__ag_tag[5:0]),
    .ag_d(hcollb_NE__ag_d[511:0]),
    .fault(hcollb_NE__fault[0:0])
  );
  ot_hgi_coll_ring_b_stop hcollb_NW (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .qid(2'b10),
    .cw_i(hcollb_NE__cw_o[279:0]),
    .ccw_i(hcollb_NE__ccw_o[279:0]),
    .cw_o(hcollb_NW__cw_o[279:0]),
    .ccw_o(hcollb_NW__ccw_o[279:0]),
    .lp_we(hcollgi_NW__rb_lp_we[0:0]),
    .lp_tag(hcollgi_NW__rb_lp_tag[2:0]),
    .lp_data(hcollgi_NW__rb_lp_data[255:0]),
    .state_read_tx(hcollgi_NW__rb_state_read_tx[0:0]),
    .state_tx_tag(hcollgi_NW__rb_state_tx_tag[2:0]),
    .tx_inject(hcollgi_NW__rb_tx_inject[1:0]),
    .tx_forward(hcollgi_NW__rb_tx_forward[1:0]),
    .tx_tag(hcollgi_NW__rb_tx_tag[2:0]),
    .tx_ttl(hcollgi_NW__rb_tx_ttl[3:0]),
    .rx_slot(hcollgi_NW__rb_rx_slot[1:0]),
    .rx_kind(hcollgi_NW__rb_rx_kind[3:0]),
    .rx_src(hcollgi_NW__rb_rx_src[3:0]),
    .rx_tag(hcollgi_NW__rb_rx_tag[5:0]),
    .ag_v(hcollb_NW__ag_v[1:0]),
    .ag_src(hcollb_NW__ag_src[3:0]),
    .ag_tag(hcollb_NW__ag_tag[5:0]),
    .ag_d(hcollb_NW__ag_d[511:0]),
    .fault(hcollb_NW__fault[0:0])
  );
  ot_hgi_coll_gq_issue #(.VM_RT(3)) hcollgi_NE (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .qid(2'b11),
    .tgt(8'b10110011),
    .cfg_v(host_cp_ingress__cfg_v[0:0]),
    .cfg_target(host_cp_ingress__cfg_target[7:0]),
    .cfg_addr(host_cp_ingress__cfg_addr[11:0]),
    .cfg_data(host_cp_ingress__cfg_data[255:0]),
    .desc_v(host_cp_ingress__desc_v[0:0]),
    .desc_base(host_cp_ingress__desc_base[11:0]),
    .desc_limit(host_cp_ingress__desc_limit[12:0]),
    .desc_loops(host_cp_ingress__desc_loops[15:0]),
    .launch_v(host_cp_ingress__launch_v[0:0]),
    .configured(hcollgi_NE__configured[0:0]),
    .tgt_fault(hcollgi_NE__tgt_fault[0:0]),
    .active(hcollgi_NE__active[0:0]),
    .done(hcollgi_NE__done[0:0]),
    .fault(hcollgi_NE__fault[0:0]),
    .isa_ring(hb_coll_NE__isa_ring[57:0]),
    .isa_lp_data(hb_coll_NE__isa_lp_data[255:0]),
    .ra_lp_we(hcollgi_NE__ra_lp_we[0:0]),
    .ra_lp_tag(hcollgi_NE__ra_lp_tag[2:0]),
    .ra_lp_data(hcollgi_NE__ra_lp_data[255:0]),
    .ra_state_read_add(hcollgi_NE__ra_state_read_add[0:0]),
    .ra_state_read_tx(hcollgi_NE__ra_state_read_tx[0:0]),
    .ra_state_read_rr(hcollgi_NE__ra_state_read_rr[0:0]),
    .ra_state_add_tag(hcollgi_NE__ra_state_add_tag[2:0]),
    .ra_state_tx_tag(hcollgi_NE__ra_state_tx_tag[2:0]),
    .ra_state_rr_tag(hcollgi_NE__ra_state_rr_tag[2:0]),
    .ra_state_add_src(hcollgi_NE__ra_state_add_src[1:0]),
    .ra_state_add_rhs_acc(hcollgi_NE__ra_state_add_rhs_acc[0:0]),
    .ra_state_tx_acc(hcollgi_NE__ra_state_tx_acc[0:0]),
    .ra_add_v(hcollgi_NE__ra_add_v[0:0]),
    .ra_add_tag(hcollgi_NE__ra_add_tag[2:0]),
    .ra_add_src(hcollgi_NE__ra_add_src[1:0]),
    .ra_add_rhs_acc(hcollgi_NE__ra_add_rhs_acc[0:0]),
    .ra_tx_inject(hcollgi_NE__ra_tx_inject[1:0]),
    .ra_tx_forward(hcollgi_NE__ra_tx_forward[1:0]),
    .ra_tx_tag(hcollgi_NE__ra_tx_tag[2:0]),
    .ra_tx_dst(hcollgi_NE__ra_tx_dst[1:0]),
    .ra_tx_result(hcollgi_NE__ra_tx_result[0:0]),
    .ra_tx_acc(hcollgi_NE__ra_tx_acc[0:0]),
    .ra_tx_gather(hcollgi_NE__ra_tx_gather[0:0]),
    .ra_tx_ttl(hcollgi_NE__ra_tx_ttl[3:0]),
    .ra_rx_slot(hcollgi_NE__ra_rx_slot[1:0]),
    .ra_rx_kind(hcollgi_NE__ra_rx_kind[3:0]),
    .ra_rx_src(hcollgi_NE__ra_rx_src[3:0]),
    .ra_rx_tag(hcollgi_NE__ra_rx_tag[5:0]),
    .ra_rr_local(hcollgi_NE__ra_rr_local[0:0]),
    .ra_rr_local_tag(hcollgi_NE__ra_rr_local_tag[2:0]),
    .rb_lp_we(hcollgi_NE__rb_lp_we[0:0]),
    .rb_lp_tag(hcollgi_NE__rb_lp_tag[2:0]),
    .rb_lp_data(hcollgi_NE__rb_lp_data[255:0]),
    .rb_state_read_tx(hcollgi_NE__rb_state_read_tx[0:0]),
    .rb_state_tx_tag(hcollgi_NE__rb_state_tx_tag[2:0]),
    .rb_tx_inject(hcollgi_NE__rb_tx_inject[1:0]),
    .rb_tx_forward(hcollgi_NE__rb_tx_forward[1:0]),
    .rb_tx_tag(hcollgi_NE__rb_tx_tag[2:0]),
    .rb_tx_ttl(hcollgi_NE__rb_tx_ttl[3:0]),
    .rb_rx_slot(hcollgi_NE__rb_rx_slot[1:0]),
    .rb_rx_kind(hcollgi_NE__rb_rx_kind[3:0]),
    .rb_rx_src(hcollgi_NE__rb_rx_src[3:0]),
    .rb_rx_tag(hcollgi_NE__rb_rx_tag[5:0]),
    .vm_rq_lo(hcollgi_NE__vm_rq_lo[67:0]),
    .vm_rq_hi(hcollgi_NE__vm_rq_hi[67:0]),
    .vm_rr_lo(hcollrs_NE__b_rr[1027:0]),
    .vm_rr_hi(hcollrs_NE__b_rr[2055:1028]),
    .ld_fire(hcollgi_NE__ld_fire[0:0]),
    .ld_desc(hcollgi_NE__ld_desc[52:0]),
    .ld_ev_v(hcollgi_NE__ld_ev_v[0:0]),
    .ld_ev_k(hcollgi_NE__ld_ev_k[9:0]),
    .ld_p_v(hcollgi_NE__ld_p_v[1:0]),
    .ld_p_d(hcollgi_NE__ld_p_d[511:0])
  );
  ot_hgi_coll_gq_issue #(.VM_RT(3)) hcollgi_NW (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .qid(2'b10),
    .tgt(8'b10110010),
    .cfg_v(host_cp_ingress__cfg_v[0:0]),
    .cfg_target(host_cp_ingress__cfg_target[7:0]),
    .cfg_addr(host_cp_ingress__cfg_addr[11:0]),
    .cfg_data(host_cp_ingress__cfg_data[255:0]),
    .desc_v(host_cp_ingress__desc_v[0:0]),
    .desc_base(host_cp_ingress__desc_base[11:0]),
    .desc_limit(host_cp_ingress__desc_limit[12:0]),
    .desc_loops(host_cp_ingress__desc_loops[15:0]),
    .launch_v(host_cp_ingress__launch_v[0:0]),
    .configured(hcollgi_NW__configured[0:0]),
    .tgt_fault(hcollgi_NW__tgt_fault[0:0]),
    .active(hcollgi_NW__active[0:0]),
    .done(hcollgi_NW__done[0:0]),
    .fault(hcollgi_NW__fault[0:0]),
    .isa_ring(hb_coll_NW__isa_ring[57:0]),
    .isa_lp_data(hb_coll_NW__isa_lp_data[255:0]),
    .ra_lp_we(hcollgi_NW__ra_lp_we[0:0]),
    .ra_lp_tag(hcollgi_NW__ra_lp_tag[2:0]),
    .ra_lp_data(hcollgi_NW__ra_lp_data[255:0]),
    .ra_state_read_add(hcollgi_NW__ra_state_read_add[0:0]),
    .ra_state_read_tx(hcollgi_NW__ra_state_read_tx[0:0]),
    .ra_state_read_rr(hcollgi_NW__ra_state_read_rr[0:0]),
    .ra_state_add_tag(hcollgi_NW__ra_state_add_tag[2:0]),
    .ra_state_tx_tag(hcollgi_NW__ra_state_tx_tag[2:0]),
    .ra_state_rr_tag(hcollgi_NW__ra_state_rr_tag[2:0]),
    .ra_state_add_src(hcollgi_NW__ra_state_add_src[1:0]),
    .ra_state_add_rhs_acc(hcollgi_NW__ra_state_add_rhs_acc[0:0]),
    .ra_state_tx_acc(hcollgi_NW__ra_state_tx_acc[0:0]),
    .ra_add_v(hcollgi_NW__ra_add_v[0:0]),
    .ra_add_tag(hcollgi_NW__ra_add_tag[2:0]),
    .ra_add_src(hcollgi_NW__ra_add_src[1:0]),
    .ra_add_rhs_acc(hcollgi_NW__ra_add_rhs_acc[0:0]),
    .ra_tx_inject(hcollgi_NW__ra_tx_inject[1:0]),
    .ra_tx_forward(hcollgi_NW__ra_tx_forward[1:0]),
    .ra_tx_tag(hcollgi_NW__ra_tx_tag[2:0]),
    .ra_tx_dst(hcollgi_NW__ra_tx_dst[1:0]),
    .ra_tx_result(hcollgi_NW__ra_tx_result[0:0]),
    .ra_tx_acc(hcollgi_NW__ra_tx_acc[0:0]),
    .ra_tx_gather(hcollgi_NW__ra_tx_gather[0:0]),
    .ra_tx_ttl(hcollgi_NW__ra_tx_ttl[3:0]),
    .ra_rx_slot(hcollgi_NW__ra_rx_slot[1:0]),
    .ra_rx_kind(hcollgi_NW__ra_rx_kind[3:0]),
    .ra_rx_src(hcollgi_NW__ra_rx_src[3:0]),
    .ra_rx_tag(hcollgi_NW__ra_rx_tag[5:0]),
    .ra_rr_local(hcollgi_NW__ra_rr_local[0:0]),
    .ra_rr_local_tag(hcollgi_NW__ra_rr_local_tag[2:0]),
    .rb_lp_we(hcollgi_NW__rb_lp_we[0:0]),
    .rb_lp_tag(hcollgi_NW__rb_lp_tag[2:0]),
    .rb_lp_data(hcollgi_NW__rb_lp_data[255:0]),
    .rb_state_read_tx(hcollgi_NW__rb_state_read_tx[0:0]),
    .rb_state_tx_tag(hcollgi_NW__rb_state_tx_tag[2:0]),
    .rb_tx_inject(hcollgi_NW__rb_tx_inject[1:0]),
    .rb_tx_forward(hcollgi_NW__rb_tx_forward[1:0]),
    .rb_tx_tag(hcollgi_NW__rb_tx_tag[2:0]),
    .rb_tx_ttl(hcollgi_NW__rb_tx_ttl[3:0]),
    .rb_rx_slot(hcollgi_NW__rb_rx_slot[1:0]),
    .rb_rx_kind(hcollgi_NW__rb_rx_kind[3:0]),
    .rb_rx_src(hcollgi_NW__rb_rx_src[3:0]),
    .rb_rx_tag(hcollgi_NW__rb_rx_tag[5:0]),
    .vm_rq_lo(hcollgi_NW__vm_rq_lo[67:0]),
    .vm_rq_hi(hcollgi_NW__vm_rq_hi[67:0]),
    .vm_rr_lo(hcollrs_NW__b_rr[1027:0]),
    .vm_rr_hi(hcollrs_NW__b_rr[2055:1028]),
    .ld_fire(hcollgi_NW__ld_fire[0:0]),
    .ld_desc(hcollgi_NW__ld_desc[52:0]),
    .ld_ev_v(hcollgi_NW__ld_ev_v[0:0]),
    .ld_ev_k(hcollgi_NW__ld_ev_k[9:0]),
    .ld_p_v(hcollgi_NW__ld_p_v[1:0]),
    .ld_p_d(hcollgi_NW__ld_p_d[511:0])
  );
  ot_hgi_coll_gq_land hcollgl_NE (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .qid(2'b11),
    .ld_fire(hcollgi_NE__ld_fire[0:0]),
    .ld_desc(hcollgi_NE__ld_desc[52:0]),
    .ld_ev_v(hcollgi_NE__ld_ev_v[0:0]),
    .ld_ev_k(hcollgi_NE__ld_ev_k[9:0]),
    .ld_p_v(hcollgi_NE__ld_p_v[1:0]),
    .ld_p_d(hcollgi_NE__ld_p_d[511:0]),
    .pa_v(hb_coll_NE__ag_v[1:0]),
    .pb_v(hcollb_NE__ag_v[1:0]),
    .pa_src(hb_coll_NE__ag_src[3:0]),
    .pb_src(hcollb_NE__ag_src[3:0]),
    .pa_tag(hb_coll_NE__ag_tag[5:0]),
    .pb_tag(hcollb_NE__ag_tag[5:0]),
    .pa_d(hb_coll_NE__ag_d[511:0]),
    .pb_d(hcollb_NE__ag_d[511:0]),
    .vm_kq_lo(hcollgl_NE__vm_kq_lo[1123:0]),
    .vm_kq_hi(hcollgl_NE__vm_kq_hi[1123:0]),
    .fault(hcollgl_NE__fault[0:0])
  );
  ot_hgi_coll_gq_land hcollgl_NW (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .qid(2'b10),
    .ld_fire(hcollgi_NW__ld_fire[0:0]),
    .ld_desc(hcollgi_NW__ld_desc[52:0]),
    .ld_ev_v(hcollgi_NW__ld_ev_v[0:0]),
    .ld_ev_k(hcollgi_NW__ld_ev_k[9:0]),
    .ld_p_v(hcollgi_NW__ld_p_v[1:0]),
    .ld_p_d(hcollgi_NW__ld_p_d[511:0]),
    .pa_v(hb_coll_NW__ag_v[1:0]),
    .pb_v(hcollb_NW__ag_v[1:0]),
    .pa_src(hb_coll_NW__ag_src[3:0]),
    .pb_src(hcollb_NW__ag_src[3:0]),
    .pa_tag(hb_coll_NW__ag_tag[5:0]),
    .pb_tag(hcollb_NW__ag_tag[5:0]),
    .pa_d(hb_coll_NW__ag_d[511:0]),
    .pb_d(hcollb_NW__ag_d[511:0]),
    .vm_kq_lo(hcollgl_NW__vm_kq_lo[1123:0]),
    .vm_kq_hi(hcollgl_NW__vm_kq_hi[1123:0]),
    .fault(hcollgl_NW__fault[0:0])
  );
  ot_hbm_kqs_fault_or4 hcollks_NE (
    .leaf_faults({hcollks_NE_p3__fault[0:0], hcollks_NE_p2__fault[0:0], hcollks_NE_p1__fault[0:0], hcollks_NE_p0__fault[0:0]}),
    .fault(hcollks_NE__fault[0:0])
  );
  ot_hgi_coll_kq_share2_leaf hcollks_NE_p0 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .a_kq(hb_coll_NE__vm_kq[561:0]),
    .b_kq(hcollgl_NE__vm_kq_lo[561:0]),
    .vm_kq(hcollks_NE_p0__vm_kq[561:0]),
    .fault(hcollks_NE_p0__fault[0:0])
  );
  ot_hgi_coll_kq_share2_leaf hcollks_NE_p1 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .a_kq(hb_coll_NE__vm_kq[1123:562]),
    .b_kq(hcollgl_NE__vm_kq_lo[1123:562]),
    .vm_kq(hcollks_NE_p1__vm_kq[561:0]),
    .fault(hcollks_NE_p1__fault[0:0])
  );
  ot_hgi_coll_kq_share2_leaf hcollks_NE_p2 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .a_kq(hb_coll_NE__vm_kq[1685:1124]),
    .b_kq(hcollgl_NE__vm_kq_hi[561:0]),
    .vm_kq(hcollks_NE_p2__vm_kq[561:0]),
    .fault(hcollks_NE_p2__fault[0:0])
  );
  ot_hgi_coll_kq_share2_leaf hcollks_NE_p3 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .a_kq(hb_coll_NE__vm_kq[2247:1686]),
    .b_kq(hcollgl_NE__vm_kq_hi[1123:562]),
    .vm_kq(hcollks_NE_p3__vm_kq[561:0]),
    .fault(hcollks_NE_p3__fault[0:0])
  );
  ot_hbm_kqs_fault_or4 hcollks_NW (
    .leaf_faults({hcollks_NW_p3__fault[0:0], hcollks_NW_p2__fault[0:0], hcollks_NW_p1__fault[0:0], hcollks_NW_p0__fault[0:0]}),
    .fault(hcollks_NW__fault[0:0])
  );
  ot_hgi_coll_kq_share2_leaf hcollks_NW_p0 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .a_kq(hb_coll_NW__vm_kq[561:0]),
    .b_kq(hcollgl_NW__vm_kq_lo[561:0]),
    .vm_kq(hcollks_NW_p0__vm_kq[561:0]),
    .fault(hcollks_NW_p0__fault[0:0])
  );
  ot_hgi_coll_kq_share2_leaf hcollks_NW_p1 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .a_kq(hb_coll_NW__vm_kq[1123:562]),
    .b_kq(hcollgl_NW__vm_kq_lo[1123:562]),
    .vm_kq(hcollks_NW_p1__vm_kq[561:0]),
    .fault(hcollks_NW_p1__fault[0:0])
  );
  ot_hgi_coll_kq_share2_leaf hcollks_NW_p2 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .a_kq(hb_coll_NW__vm_kq[1685:1124]),
    .b_kq(hcollgl_NW__vm_kq_hi[561:0]),
    .vm_kq(hcollks_NW_p2__vm_kq[561:0]),
    .fault(hcollks_NW_p2__fault[0:0])
  );
  ot_hgi_coll_kq_share2_leaf hcollks_NW_p3 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .a_kq(hb_coll_NW__vm_kq[2247:1686]),
    .b_kq(hcollgl_NW__vm_kq_hi[1123:562]),
    .vm_kq(hcollks_NW_p3__vm_kq[561:0]),
    .fault(hcollks_NW_p3__fault[0:0])
  );
  ot_hbm_idx_vm_share2_static_r #(.BANK_RT(7)) hcollrs_NE (
    .clk_pair({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .a_rq(hb_coll_NE__vm_rq[135:0]),
    .b_rq({hcollgi_NE__vm_rq_hi[67:0], hcollgi_NE__vm_rq_lo[67:0]}),
    .vm_rq(hcollrs_NE__vm_rq[135:0]),
    .vm_rr({vmb_NE7__rr3[256:0], vmb_NE6__rr3[256:0], vmb_NE5__rr3[256:0], vmb_NE4__rr3[256:0], vmb_NE3__rr3[256:0], vmb_NE2__rr3[256:0], vmb_NE1__rr3[256:0], vmb_NE0__rr3[256:0]}),
    .a_rr(hcollrs_NE__a_rr[2055:0]),
    .b_rr(hcollrs_NE__b_rr[2055:0]),
    .fault(hcollrs_NE__fault[0:0])
  );
  ot_hbm_idx_vm_share2_static_r #(.BANK_RT(7)) hcollrs_NW (
    .clk_pair({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .a_rq(hb_coll_NW__vm_rq[135:0]),
    .b_rq({hcollgi_NW__vm_rq_hi[67:0], hcollgi_NW__vm_rq_lo[67:0]}),
    .vm_rq(hcollrs_NW__vm_rq[135:0]),
    .vm_rr({vmb_NW7__rr4[256:0], vmb_NW6__rr4[256:0], vmb_NW5__rr4[256:0], vmb_NW4__rr4[256:0], vmb_NW3__rr4[256:0], vmb_NW2__rr4[256:0], vmb_NW1__rr4[256:0], vmb_NW0__rr4[256:0]}),
    .a_rr(hcollrs_NW__a_rr[2055:0]),
    .b_rr(hcollrs_NW__b_rr[2055:0]),
    .fault(hcollrs_NW__fault[0:0])
  );
  ot_hbm_host_cfg_leaf2 #(.NT(21), .NF(31)) hleaf_NE (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .cfg_v(host_cp_ingress__cfg_v[0:0]),
    .cfg_target(host_cp_ingress__cfg_target[7:0]),
    .cfg_addr(host_cp_ingress__cfg_addr[11:0]),
    .cfg_data(host_cp_ingress__cfg_data[255:0]),
    .desc_v(host_cp_ingress__desc_v[0:0]),
    .desc_base(host_cp_ingress__desc_base[11:0]),
    .desc_limit(host_cp_ingress__desc_limit[12:0]),
    .desc_loops(host_cp_ingress__desc_loops[15:0]),
    .launch_v(host_cp_ingress__launch_v[0:0]),
    .a_cfg_v(hleaf_NE__a_cfg_v[0:0]),
    .a_cfg_target(hleaf_NE__a_cfg_target[7:0]),
    .a_cfg_addr(hleaf_NE__a_cfg_addr[11:0]),
    .a_cfg_data(hleaf_NE__a_cfg_data[255:0]),
    .a_desc_v(hleaf_NE__a_desc_v[0:0]),
    .a_desc_base(hleaf_NE__a_desc_base[11:0]),
    .a_desc_limit(hleaf_NE__a_desc_limit[12:0]),
    .a_desc_loops(hleaf_NE__a_desc_loops[15:0]),
    .a_launch_v(hleaf_NE__a_launch_v[0:0]),
    .b_cfg_v(hleaf_NE__b_cfg_v[0:0]),
    .b_cfg_target(hleaf_NE__b_cfg_target[7:0]),
    .b_cfg_addr(hleaf_NE__b_cfg_addr[11:0]),
    .b_cfg_data(hleaf_NE__b_cfg_data[255:0]),
    .b_desc_v(hleaf_NE__b_desc_v[0:0]),
    .b_desc_base(hleaf_NE__b_desc_base[11:0]),
    .b_desc_limit(hleaf_NE__b_desc_limit[12:0]),
    .b_desc_loops(hleaf_NE__b_desc_loops[15:0]),
    .b_launch_v(hleaf_NE__b_launch_v[0:0]),
    .t_ready({hc_eng__configured[0:0], hc_eng__configured[0:0], col_idx__ready[0:0], col_su__ready[0:0], refcfg_NE__ready[0:0], hb_dbk_NE__cp_configured[0:0], xl_NE_ctl__configured[0:0], xc_NW7__configured[0:0], xc_NW6__configured[0:0], xc_NW5__configured[0:0], xc_NW4__configured[0:0], epcal_NE__tgt_configured[0:0], hc_NE__configured[0:0], calendar_NE__tgt_configured[0:0], cp_svg_NW7__configured[0:0], cp_svg_NW6__configured[0:0], cp_svg_NW5__configured[0:0], cp_svg_NW4__configured[0:0], vmfc_NE__tgt_configured[0:0], col_sfu_NE__ready[0:0], hb_coll_NE__program_configured[0:0]}),
    .t_active({hc_eng__program_active[0:0], hc_eng__program_active[0:0], col_idx__active[0:0], col_su__active[0:0], refcfg_NE__active[0:0], hb_dbk_NE__cp_active[0:0], xl_NE_ctl__active[0:0], xc_NW7__active[0:0], xc_NW6__active[0:0], xc_NW5__active[0:0], xc_NW4__active[0:0], epcal_NE__active[0:0], hc_NE__program_active[0:0], calendar_NE__active[0:0], cp_svg_NW7__active[0:0], cp_svg_NW6__active[0:0], cp_svg_NW5__active[0:0], cp_svg_NW4__active[0:0], vmfc_NE__active[0:0], col_sfu_NE__active[0:0], hb_coll_NE__hgi_busy[0:0]}),
    .t_fault({hc_eng__fault[0:0], ep_S3__fault[0:0], col_idx__fault[0:0], col_su__fault[0:0], wbk_NE__fault[0:0], refcfg_NE__fault[0:0], hb_dbk_NE__cp_fault[0:0], xl_NE_ctl__fault[0:0], sfup_NE__fault[0:0], sfus_NE__fault[0:0], fcx_NE__fault[0:0], xc_NW7__fault[0:0], xc_NW6__fault[0:0], xc_NW5__fault[0:0], xc_NW4__fault[0:0], ep_N2__fault[0:0], epcal_NE__fault[0:0], epcal_NE__tgt_fault[0:0], hc_NE__hcq_fault[0:0], calendar_NE__fault[0:0], calendar_NE__tgt_fault[0:0], cp_svg_NW7__fault[0:0], cp_svg_NW6__fault[0:0], cp_svg_NW5__fault[0:0], cp_svg_NW4__fault[0:0], vmfc_NE__fault[0:0], vmfc_NE__tgt_fault[0:0], col_sfu_NE__fault[0:0], hb_coll_NE__fault[0:0], hb_coll_NE__hgi_fault[0:0], hb_coll_NE__program_fault[0:0]}),
    .s_ready(hleaf_NE__s_ready[20:0]),
    .s_active(hleaf_NE__s_active[20:0]),
    .s_fault(hleaf_NE__s_fault[30:0])
  );
  ot_hbm_host_cfg_leaf2 #(.NT(20), .NF(32)) hleaf_NW (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .cfg_v(host_cp_ingress__cfg_v[0:0]),
    .cfg_target(host_cp_ingress__cfg_target[7:0]),
    .cfg_addr(host_cp_ingress__cfg_addr[11:0]),
    .cfg_data(host_cp_ingress__cfg_data[255:0]),
    .desc_v(host_cp_ingress__desc_v[0:0]),
    .desc_base(host_cp_ingress__desc_base[11:0]),
    .desc_limit(host_cp_ingress__desc_limit[12:0]),
    .desc_loops(host_cp_ingress__desc_loops[15:0]),
    .launch_v(host_cp_ingress__launch_v[0:0]),
    .a_cfg_v(hleaf_NW__a_cfg_v[0:0]),
    .a_cfg_target(hleaf_NW__a_cfg_target[7:0]),
    .a_cfg_addr(hleaf_NW__a_cfg_addr[11:0]),
    .a_cfg_data(hleaf_NW__a_cfg_data[255:0]),
    .a_desc_v(hleaf_NW__a_desc_v[0:0]),
    .a_desc_base(hleaf_NW__a_desc_base[11:0]),
    .a_desc_limit(hleaf_NW__a_desc_limit[12:0]),
    .a_desc_loops(hleaf_NW__a_desc_loops[15:0]),
    .a_launch_v(hleaf_NW__a_launch_v[0:0]),
    .b_cfg_v(hleaf_NW__b_cfg_v[0:0]),
    .b_cfg_target(hleaf_NW__b_cfg_target[7:0]),
    .b_cfg_addr(hleaf_NW__b_cfg_addr[11:0]),
    .b_cfg_data(hleaf_NW__b_cfg_data[255:0]),
    .b_desc_v(hleaf_NW__b_desc_v[0:0]),
    .b_desc_base(hleaf_NW__b_desc_base[11:0]),
    .b_desc_limit(hleaf_NW__b_desc_limit[12:0]),
    .b_desc_loops(hleaf_NW__b_desc_loops[15:0]),
    .b_launch_v(hleaf_NW__b_launch_v[0:0]),
    .t_ready({u_mu_fused_programme__ready[0:0], refcfg_NW__ready[0:0], xc_NW3__configured[0:0], xc_NW2__configured[0:0], xc_NW1__configured[0:0], xc_NW0__configured[0:0], smw_NW__configured[0:0], epcal_NW__tgt_configured[0:0], hc_NW__configured[0:0], hb_dbk_NW__cp_configured[0:0], xl_NW_ctl__configured[0:0], calendar_NW__tgt_configured[0:0], cp_svg_NW3__configured[0:0], cp_svg_NW2__configured[0:0], cp_svg_NW1__configured[0:0], cp_svg_NW0__configured[0:0], vmfc_NW__tgt_configured[0:0], col_sfu_NW__ready[0:0], hb_coll_NW__program_configured[0:0], hb_quant_NW__program_leaf__configured[0:0]}),
    .t_active({u_mu_fused_programme__active[0:0], refcfg_NW__active[0:0], xc_NW3__active[0:0], xc_NW2__active[0:0], xc_NW1__active[0:0], xc_NW0__active[0:0], smw_NW__active[0:0], epcal_NW__active[0:0], hc_NW__program_active[0:0], hb_dbk_NW__cp_active[0:0], xl_NW_ctl__active[0:0], calendar_NW__active[0:0], cp_svg_NW3__active[0:0], cp_svg_NW2__active[0:0], cp_svg_NW1__active[0:0], cp_svg_NW0__active[0:0], vmfc_NW__active[0:0], col_sfu_NW__active[0:0], hb_coll_NW__hgi_busy[0:0], hb_quant_NW__program_leaf__active[0:0]}),
    .t_fault({u_mu_fused_programme__fault[0:0], b2_ep1_root__rx_o[614:614], ep_S0__fault[0:0], refcfg_NW__fault[0:0], sfup_NW__fault[0:0], sfus_NW__fault[0:0], fcx_NW__fault[0:0], wbk_NW__fault[0:0], xc_NW3__fault[0:0], xc_NW2__fault[0:0], xc_NW1__fault[0:0], xc_NW0__fault[0:0], smw_NW__fault[0:0], ep_N0__fault[0:0], epcal_NW__fault[0:0], epcal_NW__tgt_fault[0:0], hc_NW__hcq_fault[0:0], hb_dbk_NW__cp_fault[0:0], xl_NW_ctl__fault[0:0], calendar_NW__fault[0:0], calendar_NW__tgt_fault[0:0], cp_svg_NW3__fault[0:0], cp_svg_NW2__fault[0:0], cp_svg_NW1__fault[0:0], cp_svg_NW0__fault[0:0], vmfc_NW__fault[0:0], vmfc_NW__tgt_fault[0:0], col_sfu_NW__fault[0:0], hb_coll_NW__fault[0:0], hb_coll_NW__hgi_fault[0:0], hb_coll_NW__program_fault[0:0], hb_quant_NW__hbfd_qdq_split_or__Y[0:0]}),
    .s_ready(hleaf_NW__s_ready[19:0]),
    .s_active(hleaf_NW__s_active[19:0]),
    .s_fault(hleaf_NW__s_fault[31:0])
  );
  ot_hbm_host_static_ingress_obs #(.MUT(0), .TARGET_MASK(256'h00000002ffffffff000f003f000000f3e1f1ffffffffffff0ff1000000000000)) host_cp_ingress (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .s_awvalid(host_cp_rxs__s_awvalid[0:0]),
    .s_awready(host_cp_ingress__s_awready[0:0]),
    .s_awaddr(host_cp_rxs__s_awaddr[11:0]),
    .s_wvalid(host_cp_rxs__s_wvalid[0:0]),
    .s_wready(host_cp_ingress__s_wready[0:0]),
    .s_wdata(host_cp_rxs__s_wdata[31:0]),
    .s_wstrb(host_cp_rxs__s_wstrb[3:0]),
    .s_bvalid(host_cp_ingress__s_bvalid[0:0]),
    .s_bready(host_cp_rxs__s_bready[0:0]),
    .s_bresp(host_cp_ingress__s_bresp[1:0]),
    .s_arvalid(host_cp_rxs__s_arvalid[0:0]),
    .s_arready(host_cp_ingress__s_arready[0:0]),
    .s_araddr(host_cp_rxs__s_araddr[11:0]),
    .s_rvalid(host_cp_ingress__s_rvalid[0:0]),
    .s_rready(host_cp_rxs__s_rready[0:0]),
    .s_rdata(host_cp_ingress__s_rdata[31:0]),
    .block_ready(host_status__block_ready[0:0]),
    .program_active(host_status__program_active[0:0]),
    .program_fault(host_status__program_fault[0:0]),
    .cfg_v(host_cp_ingress__cfg_v[0:0]),
    .cfg_target(host_cp_ingress__cfg_target[7:0]),
    .cfg_addr(host_cp_ingress__cfg_addr[11:0]),
    .cfg_data(host_cp_ingress__cfg_data[255:0]),
    .desc_v(host_cp_ingress__desc_v[0:0]),
    .desc_base(host_cp_ingress__desc_base[11:0]),
    .desc_limit(host_cp_ingress__desc_limit[12:0]),
    .desc_loops(host_cp_ingress__desc_loops[15:0]),
    .launch_v(host_cp_ingress__launch_v[0:0]),
    .fault(host_cp_ingress__fault[0:0]),
    .obs_q_v(host_cp_ingress__obs_q_v[0:0]),
    .obs_q_idx(host_cp_ingress__obs_q_idx[7:0]),
    .obs_q_d(host_cp_ingress__obs_q_d[31:0]),
    .obs_r_v(obs_NW__r_v[0:0]),
    .obs_r_idx(obs_NW__r_idx[7:0]),
    .obs_r_d(obs_NW__r_d[31:0])
  );
  ot_hbm_host_cp_rxs host_cp_rxs (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .session(host_cp_rxs__session[7:0]),
    .ep_tx_v(host_cp_rxs__ep_tx_v[0:0]),
    .ep_tx_frame(host_cp_rxs__ep_tx_frame[611:0]),
    .ep_rx_arm_v(host_cp_rxs__ep_rx_arm_v[0:0]),
    .ep_rx_arm_bank(host_cp_rxs__ep_rx_arm_bank[0:0]),
    .ep_rx_block_words(host_cp_rxs__ep_rx_block_words[6:0]),
    .ep_rx_release_v(host_cp_rxs__ep_rx_release_v[0:0]),
    .ep_rx_release_bank(host_cp_rxs__ep_rx_release_bank[0:0]),
    .ep_rx_slot_v(host_cp_rxs__ep_rx_slot_v[0:0]),
    .ep_rx_slot_bank(host_cp_rxs__ep_rx_slot_bank[0:0]),
    .ep_rx_slot_index(host_cp_rxs__ep_rx_slot_index[5:0]),
    .ep_rx_pin_v(host_ep__rx_pin_v[0:0]),
    .ep_rx_pin_flit(host_ep__rx_pin_flit[611:0]),
    .ep_rx_block_ready(host_ep__rx_block_ready[1:0]),
    .ep_phy_up(host_ep__phy_up[0:0]),
    .s_awvalid(host_cp_rxs__s_awvalid[0:0]),
    .s_awready(host_cp_ingress__s_awready[0:0]),
    .s_awaddr(host_cp_rxs__s_awaddr[11:0]),
    .s_wvalid(host_cp_rxs__s_wvalid[0:0]),
    .s_wready(host_cp_ingress__s_wready[0:0]),
    .s_wdata(host_cp_rxs__s_wdata[31:0]),
    .s_wstrb(host_cp_rxs__s_wstrb[3:0]),
    .s_bvalid(host_cp_ingress__s_bvalid[0:0]),
    .s_bresp(host_cp_ingress__s_bresp[1:0]),
    .s_bready(host_cp_rxs__s_bready[0:0]),
    .s_arvalid(host_cp_rxs__s_arvalid[0:0]),
    .s_arready(host_cp_ingress__s_arready[0:0]),
    .s_araddr(host_cp_rxs__s_araddr[11:0]),
    .s_rvalid(host_cp_ingress__s_rvalid[0:0]),
    .s_rready(host_cp_rxs__s_rready[0:0]),
    .s_rdata(host_cp_ingress__s_rdata[31:0]),
    .irq(host_status__irq[0:0]),
    .fault(host_status__die_fault[0:0]),
    .land_fault(host_cp_rxs__land_fault[0:0]),
    .protocol_fault(host_cp_rxs__protocol_fault[0:0]),
    .link_fault(host_cp_rxs__link_fault[0:0]),
    .seq_fault(host_cp_rxs__seq_fault[0:0])
  );
  hfd_ep_host_vc host_ep (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .tx_v(host_cp_rxs__ep_tx_v[0:0]),
    .tx_frame(host_cp_rxs__ep_tx_frame[611:0]),
    .rx_arm_v(host_cp_rxs__ep_rx_arm_v[0:0]),
    .rx_arm_bank(host_cp_rxs__ep_rx_arm_bank[0:0]),
    .rx_block_words(host_cp_rxs__ep_rx_block_words[6:0]),
    .rx_release_v(host_cp_rxs__ep_rx_release_v[0:0]),
    .rx_release_bank(host_cp_rxs__ep_rx_release_bank[0:0]),
    .rx_slot_v(host_cp_rxs__ep_rx_slot_v[0:0]),
    .rx_slot_bank(host_cp_rxs__ep_rx_slot_bank[0:0]),
    .rx_slot_index(host_cp_rxs__ep_rx_slot_index[5:0]),
    .rx_pin_v(host_ep__rx_pin_v[0:0]),
    .rx_pin_flit(host_ep__rx_pin_flit[611:0]),
    .rx_block_ready(host_ep__rx_block_ready[1:0]),
    .phy_up(host_ep__phy_up[0:0]),
    .fault(host_ep__fault[0:0]),
    .fault_cause(host_ep__fault_cause[10:0]),
    .vc_tx_v(host_ep__vc_tx_v[0:0]),
    .vc_tx_frame(host_ep__vc_tx_frame[611:0]),
    .vc_rx_v(ep_N0__h_rx_v[0:0]),
    .vc_rx_frame(ep_N0__h_rx_frame[611:0]),
    .vc_up(ep_N0__h_up[0:0]),
    .vc_cause(ep_N0__h_cause[2:0])
  );
  ot_hbm_status_join_fa #(.NT(44), .NF(76), .NH(6), .TGTS(352'ha5a47870816b67d7d6d5d4876f63575655543b7737e17fd3d2d1d0a2866e6a6662535251503a763630b3b2a3), .NA(2), .FCLR(125), .RRELAY(1), .GUARD(12)) host_status (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .cfg_v(host_cp_ingress__cfg_v[0:0]),
    .desc_v(host_cp_ingress__desc_v[0:0]),
    .launch_v(host_cp_ingress__launch_v[0:0]),
    .cfg_target(host_cp_ingress__cfg_target[7:0]),
    .t_ready({hleaf_NE__s_ready[20:0], hleaf_NW__s_ready[19:0], hcollgi_NE__configured[0:0], hcollgi_NW__configured[0:0], smw_NE__configured[0:0]}),
    .t_active({hleaf_NE__s_active[20:0], hleaf_NW__s_active[19:0], hcollgi_NE__active[0:0], hcollgi_NW__active[0:0], smw_NE__active[0:0]}),
    .t_fault({hleaf_NE__s_fault[30:0], hleaf_NW__s_fault[31:0], hcollb_NE__fault[0:0], hcollks_NE__fault[0:0], hcollrs_NE__fault[0:0], hcollgl_NE__fault[0:0], hcollb_NW__fault[0:0], hcollks_NW__fault[0:0], hcollrs_NW__fault[0:0], hcollgl_NW__fault[0:0], hcollgi_NE__tgt_fault[0:0], hcollgi_NW__tgt_fault[0:0], hcollgi_NE__fault[0:0], hcollgi_NW__fault[0:0], smw_NE__fault[0:0]}),
    .h_fault({host_cp_rxs__seq_fault[0:0], host_cp_rxs__link_fault[0:0], host_ep__fault[0:0], host_cp_rxs__land_fault[0:0], host_cp_rxs__protocol_fault[0:0], host_cp_ingress__fault[0:0]}),
    .block_ready(host_status__block_ready[0:0]),
    .program_active(host_status__program_active[0:0]),
    .program_fault(host_status__program_fault[0:0]),
    .die_fault(host_status__die_fault[0:0]),
    .irq(host_status__irq[0:0]),
    .a_fault({fr_NW__fault[0:0], fr_NE__fault[0:0]}),
    .a_cause(host_status__a_cause[1:0])
  );
  ot_pdie_serdes lk_N0 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst(hb_ckgen__por_stream[0:0]),
    .tx(ep_N0__sd_tx[511:0]),
    .rx(lk_N0__rx[511:0]),
    .st(lk_N0__st[1:0]),
    .pma_tx(lk_N0__pma_tx[543:0]),
    .pma_tck(lk_N0__pma_tck[0:0]),
    .pma_rx(lk_N0__pma_rx[543:0]),
    .pma_rck(lk_N0__pma_rck[0:0])
  );
  ot_pdie_serdes lk_N2 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst(hb_ckgen__por_stream[0:0]),
    .tx(ep_N2__sd_tx[511:0]),
    .rx(lk_N2__rx[511:0]),
    .st(lk_N2__st[1:0]),
    .pma_tx(lk_N2__pma_tx[543:0]),
    .pma_tck(lk_N2__pma_tck[0:0]),
    .pma_rx(lk_N2__pma_rx[543:0]),
    .pma_rck(lk_N2__pma_rck[0:0])
  );
  ot_pdie_serdes lk_S0 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst(hb_ckgen__por_stream[0:0]),
    .tx(ep_S0__sd_tx[511:0]),
    .rx(lk_S0__rx[511:0]),
    .st(lk_S0__st[1:0]),
    .pma_tx(lk_S0__pma_tx[543:0]),
    .pma_tck(lk_S0__pma_tck[0:0]),
    .pma_rx(lk_S0__pma_rx[543:0]),
    .pma_rck(lk_S0__pma_rck[0:0])
  );
  ot_pdie_serdes lk_S1 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst(hb_ckgen__por_stream[0:0]),
    .tx(ep_S1__sd_tx[511:0]),
    .rx(lk_S1__rx[511:0]),
    .st(lk_S1__st[1:0]),
    .pma_tx(lk_S1__pma_tx[543:0]),
    .pma_tck(lk_S1__pma_tck[0:0]),
    .pma_rx(lk_S1__pma_rx[543:0]),
    .pma_rck(lk_S1__pma_rck[0:0])
  );
  ot_pdie_serdes lk_S3 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst(hb_ckgen__por_stream[0:0]),
    .tx(ep_S3__sd_tx[511:0]),
    .rx(lk_S3__rx[511:0]),
    .st(lk_S3__st[1:0]),
    .pma_tx(lk_S3__pma_tx[543:0]),
    .pma_tck(lk_S3__pma_tck[0:0]),
    .pma_rx(lk_S3__pma_rx[543:0]),
    .pma_rck(lk_S3__pma_rck[0:0])
  );
  ot_hbm_obs_leaf #(.N(144), .LID(0), .SYNC_MASK(512'h0)) obs_C (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .obs({vm_status4__vmstat[18:0], tkm_SW__stat_cycles[31:0], host_status__a_cause[1:0], host_ep__fault_cause[10:0], hc_eng__program_done[0:0], hb_idx__link__selected_count[9:0], hb_idx__ctl__topk_done[0:0], hb_argmax__done[0:0], hb_argmax__cq_seq[1:0], ep_S3__rx_block_ready[1:0], ep_S3__fault_cause[10:0], ep_S1__rx_block_ready[1:0], ep_S1__fault_cause[10:0], ep_S0__rx_block_ready[1:0], ep_S0__fault_cause[10:0], ep_N2__rx_block_ready[1:0], ep_N2__fault_cause[10:0], ep_N0__rx_block_ready[1:0], ep_N0__fault_cause[10:0]}),
    .q_v(host_cp_ingress__obs_q_v[0:0]),
    .q_idx(host_cp_ingress__obs_q_idx[7:0]),
    .q_d(host_cp_ingress__obs_q_d[31:0]),
    .r_v(obs_C__r_v[0:0]),
    .r_idx(obs_C__r_idx[7:0]),
    .r_d(obs_C__r_d[31:0])
  );
  ot_hbm_obs_leaf #(.N(182), .LID(3), .SYNC_MASK(512'h7fffe000000000000000000000000000)) obs_NE (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .obs({xq_NE_p1_eg__xw_last[0:0], xq_NE_p1_eg__x_done[0:0], xq_NE_p0_eg__xw_last[0:0], xq_NE_p0_eg__x_done[0:0], vmfc_NE__done[0:0], vmfc_NE__calendar_v[0:0], vmdel_NE7__busy[0:0], vmdel_NE7__block_ready[1:0], vmdel_NE6__busy[0:0], vmdel_NE6__block_ready[1:0], vmdel_NE5__busy[0:0], vmdel_NE5__block_ready[1:0], vmdel_NE4__busy[0:0], vmdel_NE4__block_ready[1:0], vmdel_NE3__busy[0:0], vmdel_NE3__block_ready[1:0], vmdel_NE2__busy[0:0], vmdel_NE2__block_ready[1:0], vmdel_NE1__busy[0:0], vmdel_NE1__block_ready[1:0], vmdel_NE0__busy[0:0], vmdel_NE0__block_ready[1:0], vmb_NE7__wq_done1[0:0], vmb_NE7__kq_done[0:0], vmb_NE7__dq_done[0:0], vmb_NE6__wq_done1[0:0], vmb_NE6__kq_done[0:0], vmb_NE6__dq_done[0:0], vmb_NE5__wq_done1[0:0], vmb_NE5__kq_done[0:0], vmb_NE5__dq_done[0:0], vmb_NE4__wq_done1[0:0], vmb_NE4__kq_done[0:0], vmb_NE4__dq_done[0:0], vmb_NE3__wq_done1[0:0], vmb_NE3__kq_done[0:0], vmb_NE3__dq_done[0:0], vmb_NE2__wq_done1[0:0], vmb_NE2__kq_done[0:0], vmb_NE2__dq_done[0:0], vmb_NE1__wq_done1[0:0], vmb_NE1__kq_done[0:0], vmb_NE1__dq_done[0:0], vmb_NE0__wq_done1[0:0], vmb_NE0__kq_done[0:0], vmb_NE0__dq_done[0:0], sfup_NE__programme_done[0:0], pgp_NE__valid[0:0], pgp_NE__edge_index[15:0], pgp_NE__done[0:0], hcollgi_NE__done[0:0], hc_NE__residual_done[0:0], hc_NE__program_done[0:0], hc_NE__gather_done[0:0], hb_vms_NE__mirror_busy[1:0], hb_vms_NE__hub_status[2:0], hb_idx__s_NE__score[1:1], hb_dbk_NE__quiet[0:0], hb_dbk_NE__mv_src[0:0], hb_dbk_NE__mv_done[0:0], hb_dbk_NE__busy[0:0], hb_coll_NE__stat_cycles[31:0], hb_coll_NE__program_init_busy[0:0], hb_coll_NE__hgi_done[0:0], hb_coll_NE__fault_cause[15:0], hb_coll_NE__done[0:0], epcal_NE__done[0:0], epcal_NE__calendar_v[0:0], calendar_NE__response_seq[9:2], calendar_NE__response_enable[4:1], calendar_NE__hub_ring_client[5:2], calendar_NE__done[0:0], calendar_NE__client_seq[9:2], calendar_NE__calendar_v[0:0], calendar_NE__bank_client[23:8]}),
    .q_v(obs_C__r_v[0:0]),
    .q_idx(obs_C__r_idx[7:0]),
    .q_d(obs_C__r_d[31:0]),
    .r_v(obs_NE__r_v[0:0]),
    .r_idx(obs_NE__r_idx[7:0]),
    .r_d(obs_NE__r_d[31:0])
  );
  ot_hbm_obs_leaf #(.N(209), .LID(4), .SYNC_MASK(512'h3ffff0000000000000000000000000000)) obs_NW (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .obs({xq_NW_p1_eg__xw_last[0:0], xq_NW_p1_eg__x_done[0:0], xq_NW_p0_eg__xw_last[0:0], xq_NW_p0_eg__x_done[0:0], xc_NW7__done[0:0], xc_NW6__done[0:0], xc_NW5__done[0:0], xc_NW4__done[0:0], xc_NW3__done[0:0], xc_NW2__done[0:0], xc_NW1__done[0:0], xc_NW0__done[0:0], vmm_NW7__wq_done2[0:0], vmm_NW7__wq_done1[0:0], vmm_NW6__wq_done2[0:0], vmm_NW6__wq_done1[0:0], vmm_NW5__wq_done2[0:0], vmm_NW5__wq_done1[0:0], vmm_NW4__wq_done2[0:0], vmm_NW4__wq_done1[0:0], vmm_NW3__wq_done2[0:0], vmm_NW3__wq_done1[0:0], vmm_NW2__wq_done2[0:0], vmm_NW2__wq_done1[0:0], vmm_NW1__wq_done2[0:0], vmm_NW1__wq_done1[0:0], vmm_NW0__wq_done2[0:0], vmm_NW0__wq_done1[0:0], vmfc_NW__done[0:0], vmfc_NW__calendar_v[0:0], vmdel_NW7__busy[0:0], vmdel_NW7__block_ready[1:0], vmdel_NW6__busy[0:0], vmdel_NW6__block_ready[1:0], vmdel_NW5__busy[0:0], vmdel_NW5__block_ready[1:0], vmdel_NW4__busy[0:0], vmdel_NW4__block_ready[1:0], vmdel_NW3__busy[0:0], vmdel_NW3__block_ready[1:0], vmdel_NW2__busy[0:0], vmdel_NW2__block_ready[1:0], vmdel_NW1__busy[0:0], vmdel_NW1__block_ready[1:0], vmdel_NW0__busy[0:0], vmdel_NW0__block_ready[1:0], vmb_NW7__kq_done[0:0], vmb_NW7__dq_done[0:0], vmb_NW6__kq_done[0:0], vmb_NW6__dq_done[0:0], vmb_NW5__kq_done[0:0], vmb_NW5__dq_done[0:0], vmb_NW4__kq_done[0:0], vmb_NW4__dq_done[0:0], vmb_NW3__kq_done[0:0], vmb_NW3__dq_done[0:0], vmb_NW2__kq_done[0:0], vmb_NW2__dq_done[0:0], vmb_NW1__kq_done[0:0], vmb_NW1__dq_done[0:0], vmb_NW0__kq_done[0:0], vmb_NW0__dq_done[0:0], svg_NW7__run_done[0:0], svg_NW6__run_done[0:0], svg_NW5__run_done[0:0], svg_NW4__run_done[0:0], svg_NW3__run_done[0:0], svg_NW2__run_done[0:0], svg_NW1__run_done[0:0], svg_NW0__run_done[0:0], sfup_NW__programme_done[0:0], pgp_NW__valid[0:0], pgp_NW__edge_index[15:0], pgp_NW__done[0:0], hcollgi_NW__done[0:0], hc_NW__residual_done[0:0], hc_NW__program_done[0:0], hc_NW__gather_done[0:0], hb_vms_NW__mirror_busy[1:0], hb_vms_NW__hub_status[2:0], hb_quant_NW__quant_NW_xp_ctl__record_done[0:0], hb_quant_NW__program_leaf__done[0:0], hb_quant_NW__quant_NW_xp_ctl__beat_done[0:0], hb_idx__s_NW__score[1:1], hb_dbk_NW__quiet[0:0], hb_dbk_NW__mv_src[0:0], hb_dbk_NW__mv_done[0:0], hb_dbk_NW__busy[0:0], hb_coll_NW__stat_cycles[31:0], hb_coll_NW__program_init_busy[0:0], hb_coll_NW__hgi_done[0:0], hb_coll_NW__fault_cause[15:0], hb_coll_NW__done[0:0], epcal_NW__done[0:0], epcal_NW__calendar_v[0:0], calendar_NW__response_seq[9:2], calendar_NW__response_enable[4:1], calendar_NW__hub_ring_client[5:2], calendar_NW__done[0:0], calendar_NW__client_seq[9:2], calendar_NW__calendar_v[0:0], calendar_NW__bank_client[23:8]}),
    .q_v(obs_NE__r_v[0:0]),
    .q_idx(obs_NE__r_idx[7:0]),
    .q_d(obs_NE__r_d[31:0]),
    .r_v(obs_NW__r_v[0:0]),
    .r_idx(obs_NW__r_idx[7:0]),
    .r_d(obs_NW__r_d[31:0])
  );
  ot_hbm_su_programme_pslice_c5 #(.SB(2470)) pgp_NE (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .cfg_we(su_prog__r_we[1:1]),
    .cfg_bank(su_prog__r_bank[31:16]),
    .cfg_row(su_prog__r_row[6:0]),
    .cfg_data(su_prog__r_data[255:0]),
    .start(su_prog__r_start[0:0]),
    .length(su_prog__r_len[15:0]),
    .busy(pgp_NE__busy[0:0]),
    .valid(pgp_NE__valid[0:0]),
    .done(pgp_NE__done[0:0]),
    .fault(pgp_NE__fault[0:0]),
    .edge_index(pgp_NE__edge_index[15:0]),
    .command(pgp_NE__command[2469:0])
  );
  ot_hbm_su_programme_pslice_c5 #(.SB(2470)) pgp_NW (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .cfg_we(su_prog__r_we[0:0]),
    .cfg_bank(su_prog__r_bank[15:0]),
    .cfg_row(su_prog__r_row[6:0]),
    .cfg_data(su_prog__r_data[255:0]),
    .start(su_prog__r_start[0:0]),
    .length(su_prog__r_len[15:0]),
    .busy(pgp_NW__busy[0:0]),
    .valid(pgp_NW__valid[0:0]),
    .done(pgp_NW__done[0:0]),
    .fault(pgp_NW__fault[0:0]),
    .edge_index(pgp_NW__edge_index[15:0]),
    .command(pgp_NW__command[2469:0])
  );
  ot_hbm3e_phy_rc_e8p5 phy_NW (
    .clk(hb_ckgen__pll_hbm[0:0]),
    .rst_n(hb_ckgen__por_hbm[0:0]),
    .row_v({ctl_NW_p31__row_v[0:0], ctl_NW_p30__row_v[0:0], ctl_NW_p29__row_v[0:0], ctl_NW_p28__row_v[0:0], ctl_NW_p27__row_v[0:0], ctl_NW_p26__row_v[0:0], ctl_NW_p25__row_v[0:0], ctl_NW_p24__row_v[0:0], ctl_NW_p23__row_v[0:0], ctl_NW_p22__row_v[0:0], ctl_NW_p21__row_v[0:0], ctl_NW_p20__row_v[0:0], ctl_NW_p19__row_v[0:0], ctl_NW_p18__row_v[0:0], ctl_NW_p17__row_v[0:0], ctl_NW_p16__row_v[0:0], ctl_NW_p15__row_v[0:0], ctl_NW_p14__row_v[0:0], ctl_NW_p13__row_v[0:0], ctl_NW_p12__row_v[0:0], ctl_NW_p11__row_v[0:0], ctl_NW_p10__row_v[0:0], ctl_NW_p09__row_v[0:0], ctl_NW_p08__row_v[0:0], ctl_NW_p07__row_v[0:0], ctl_NW_p06__row_v[0:0], ctl_NW_p05__row_v[0:0], ctl_NW_p04__row_v[0:0], ctl_NW_p03__row_v[0:0], ctl_NW_p02__row_v[0:0], ctl_NW_p01__row_v[0:0], ctl_NW_p00__row_v[0:0]}),
    .row_op({ctl_NW_p31__row_op[2:0], ctl_NW_p30__row_op[2:0], ctl_NW_p29__row_op[2:0], ctl_NW_p28__row_op[2:0], ctl_NW_p27__row_op[2:0], ctl_NW_p26__row_op[2:0], ctl_NW_p25__row_op[2:0], ctl_NW_p24__row_op[2:0], ctl_NW_p23__row_op[2:0], ctl_NW_p22__row_op[2:0], ctl_NW_p21__row_op[2:0], ctl_NW_p20__row_op[2:0], ctl_NW_p19__row_op[2:0], ctl_NW_p18__row_op[2:0], ctl_NW_p17__row_op[2:0], ctl_NW_p16__row_op[2:0], ctl_NW_p15__row_op[2:0], ctl_NW_p14__row_op[2:0], ctl_NW_p13__row_op[2:0], ctl_NW_p12__row_op[2:0], ctl_NW_p11__row_op[2:0], ctl_NW_p10__row_op[2:0], ctl_NW_p09__row_op[2:0], ctl_NW_p08__row_op[2:0], ctl_NW_p07__row_op[2:0], ctl_NW_p06__row_op[2:0], ctl_NW_p05__row_op[2:0], ctl_NW_p04__row_op[2:0], ctl_NW_p03__row_op[2:0], ctl_NW_p02__row_op[2:0], ctl_NW_p01__row_op[2:0], ctl_NW_p00__row_op[2:0]}),
    .row_bank({ctl_NW_p31__row_bank[4:0], ctl_NW_p30__row_bank[4:0], ctl_NW_p29__row_bank[4:0], ctl_NW_p28__row_bank[4:0], ctl_NW_p27__row_bank[4:0], ctl_NW_p26__row_bank[4:0], ctl_NW_p25__row_bank[4:0], ctl_NW_p24__row_bank[4:0], ctl_NW_p23__row_bank[4:0], ctl_NW_p22__row_bank[4:0], ctl_NW_p21__row_bank[4:0], ctl_NW_p20__row_bank[4:0], ctl_NW_p19__row_bank[4:0], ctl_NW_p18__row_bank[4:0], ctl_NW_p17__row_bank[4:0], ctl_NW_p16__row_bank[4:0], ctl_NW_p15__row_bank[4:0], ctl_NW_p14__row_bank[4:0], ctl_NW_p13__row_bank[4:0], ctl_NW_p12__row_bank[4:0], ctl_NW_p11__row_bank[4:0], ctl_NW_p10__row_bank[4:0], ctl_NW_p09__row_bank[4:0], ctl_NW_p08__row_bank[4:0], ctl_NW_p07__row_bank[4:0], ctl_NW_p06__row_bank[4:0], ctl_NW_p05__row_bank[4:0], ctl_NW_p04__row_bank[4:0], ctl_NW_p03__row_bank[4:0], ctl_NW_p02__row_bank[4:0], ctl_NW_p01__row_bank[4:0], ctl_NW_p00__row_bank[4:0]}),
    .row_row({ctl_NW_p31__row_row[18:0], ctl_NW_p30__row_row[18:0], ctl_NW_p29__row_row[18:0], ctl_NW_p28__row_row[18:0], ctl_NW_p27__row_row[18:0], ctl_NW_p26__row_row[18:0], ctl_NW_p25__row_row[18:0], ctl_NW_p24__row_row[18:0], ctl_NW_p23__row_row[18:0], ctl_NW_p22__row_row[18:0], ctl_NW_p21__row_row[18:0], ctl_NW_p20__row_row[18:0], ctl_NW_p19__row_row[18:0], ctl_NW_p18__row_row[18:0], ctl_NW_p17__row_row[18:0], ctl_NW_p16__row_row[18:0], ctl_NW_p15__row_row[18:0], ctl_NW_p14__row_row[18:0], ctl_NW_p13__row_row[18:0], ctl_NW_p12__row_row[18:0], ctl_NW_p11__row_row[18:0], ctl_NW_p10__row_row[18:0], ctl_NW_p09__row_row[18:0], ctl_NW_p08__row_row[18:0], ctl_NW_p07__row_row[18:0], ctl_NW_p06__row_row[18:0], ctl_NW_p05__row_row[18:0], ctl_NW_p04__row_row[18:0], ctl_NW_p03__row_row[18:0], ctl_NW_p02__row_row[18:0], ctl_NW_p01__row_row[18:0], ctl_NW_p00__row_row[18:0]}),
    .col_v({ctl_NW_p31__col_v[0:0], ctl_NW_p30__col_v[0:0], ctl_NW_p29__col_v[0:0], ctl_NW_p28__col_v[0:0], ctl_NW_p27__col_v[0:0], ctl_NW_p26__col_v[0:0], ctl_NW_p25__col_v[0:0], ctl_NW_p24__col_v[0:0], ctl_NW_p23__col_v[0:0], ctl_NW_p22__col_v[0:0], ctl_NW_p21__col_v[0:0], ctl_NW_p20__col_v[0:0], ctl_NW_p19__col_v[0:0], ctl_NW_p18__col_v[0:0], ctl_NW_p17__col_v[0:0], ctl_NW_p16__col_v[0:0], ctl_NW_p15__col_v[0:0], ctl_NW_p14__col_v[0:0], ctl_NW_p13__col_v[0:0], ctl_NW_p12__col_v[0:0], ctl_NW_p11__col_v[0:0], ctl_NW_p10__col_v[0:0], ctl_NW_p09__col_v[0:0], ctl_NW_p08__col_v[0:0], ctl_NW_p07__col_v[0:0], ctl_NW_p06__col_v[0:0], ctl_NW_p05__col_v[0:0], ctl_NW_p04__col_v[0:0], ctl_NW_p03__col_v[0:0], ctl_NW_p02__col_v[0:0], ctl_NW_p01__col_v[0:0], ctl_NW_p00__col_v[0:0]}),
    .col_we({ctl_NW_p31__col_we[0:0], ctl_NW_p30__col_we[0:0], ctl_NW_p29__col_we[0:0], ctl_NW_p28__col_we[0:0], ctl_NW_p27__col_we[0:0], ctl_NW_p26__col_we[0:0], ctl_NW_p25__col_we[0:0], ctl_NW_p24__col_we[0:0], ctl_NW_p23__col_we[0:0], ctl_NW_p22__col_we[0:0], ctl_NW_p21__col_we[0:0], ctl_NW_p20__col_we[0:0], ctl_NW_p19__col_we[0:0], ctl_NW_p18__col_we[0:0], ctl_NW_p17__col_we[0:0], ctl_NW_p16__col_we[0:0], ctl_NW_p15__col_we[0:0], ctl_NW_p14__col_we[0:0], ctl_NW_p13__col_we[0:0], ctl_NW_p12__col_we[0:0], ctl_NW_p11__col_we[0:0], ctl_NW_p10__col_we[0:0], ctl_NW_p09__col_we[0:0], ctl_NW_p08__col_we[0:0], ctl_NW_p07__col_we[0:0], ctl_NW_p06__col_we[0:0], ctl_NW_p05__col_we[0:0], ctl_NW_p04__col_we[0:0], ctl_NW_p03__col_we[0:0], ctl_NW_p02__col_we[0:0], ctl_NW_p01__col_we[0:0], ctl_NW_p00__col_we[0:0]}),
    .col_bank({ctl_NW_p31__col_bank[4:0], ctl_NW_p30__col_bank[4:0], ctl_NW_p29__col_bank[4:0], ctl_NW_p28__col_bank[4:0], ctl_NW_p27__col_bank[4:0], ctl_NW_p26__col_bank[4:0], ctl_NW_p25__col_bank[4:0], ctl_NW_p24__col_bank[4:0], ctl_NW_p23__col_bank[4:0], ctl_NW_p22__col_bank[4:0], ctl_NW_p21__col_bank[4:0], ctl_NW_p20__col_bank[4:0], ctl_NW_p19__col_bank[4:0], ctl_NW_p18__col_bank[4:0], ctl_NW_p17__col_bank[4:0], ctl_NW_p16__col_bank[4:0], ctl_NW_p15__col_bank[4:0], ctl_NW_p14__col_bank[4:0], ctl_NW_p13__col_bank[4:0], ctl_NW_p12__col_bank[4:0], ctl_NW_p11__col_bank[4:0], ctl_NW_p10__col_bank[4:0], ctl_NW_p09__col_bank[4:0], ctl_NW_p08__col_bank[4:0], ctl_NW_p07__col_bank[4:0], ctl_NW_p06__col_bank[4:0], ctl_NW_p05__col_bank[4:0], ctl_NW_p04__col_bank[4:0], ctl_NW_p03__col_bank[4:0], ctl_NW_p02__col_bank[4:0], ctl_NW_p01__col_bank[4:0], ctl_NW_p00__col_bank[4:0]}),
    .col_col({ctl_NW_p31__col_col[4:0], ctl_NW_p30__col_col[4:0], ctl_NW_p29__col_col[4:0], ctl_NW_p28__col_col[4:0], ctl_NW_p27__col_col[4:0], ctl_NW_p26__col_col[4:0], ctl_NW_p25__col_col[4:0], ctl_NW_p24__col_col[4:0], ctl_NW_p23__col_col[4:0], ctl_NW_p22__col_col[4:0], ctl_NW_p21__col_col[4:0], ctl_NW_p20__col_col[4:0], ctl_NW_p19__col_col[4:0], ctl_NW_p18__col_col[4:0], ctl_NW_p17__col_col[4:0], ctl_NW_p16__col_col[4:0], ctl_NW_p15__col_col[4:0], ctl_NW_p14__col_col[4:0], ctl_NW_p13__col_col[4:0], ctl_NW_p12__col_col[4:0], ctl_NW_p11__col_col[4:0], ctl_NW_p10__col_col[4:0], ctl_NW_p09__col_col[4:0], ctl_NW_p08__col_col[4:0], ctl_NW_p07__col_col[4:0], ctl_NW_p06__col_col[4:0], ctl_NW_p05__col_col[4:0], ctl_NW_p04__col_col[4:0], ctl_NW_p03__col_col[4:0], ctl_NW_p02__col_col[4:0], ctl_NW_p01__col_col[4:0], ctl_NW_p00__col_col[4:0]}),
    .col_data({ctl_NW_p31__col_data[255:0], ctl_NW_p30__col_data[255:0], ctl_NW_p29__col_data[255:0], ctl_NW_p28__col_data[255:0], ctl_NW_p27__col_data[255:0], ctl_NW_p26__col_data[255:0], ctl_NW_p25__col_data[255:0], ctl_NW_p24__col_data[255:0], ctl_NW_p23__col_data[255:0], ctl_NW_p22__col_data[255:0], ctl_NW_p21__col_data[255:0], ctl_NW_p20__col_data[255:0], ctl_NW_p19__col_data[255:0], ctl_NW_p18__col_data[255:0], ctl_NW_p17__col_data[255:0], ctl_NW_p16__col_data[255:0], ctl_NW_p15__col_data[255:0], ctl_NW_p14__col_data[255:0], ctl_NW_p13__col_data[255:0], ctl_NW_p12__col_data[255:0], ctl_NW_p11__col_data[255:0], ctl_NW_p10__col_data[255:0], ctl_NW_p09__col_data[255:0], ctl_NW_p08__col_data[255:0], ctl_NW_p07__col_data[255:0], ctl_NW_p06__col_data[255:0], ctl_NW_p05__col_data[255:0], ctl_NW_p04__col_data[255:0], ctl_NW_p03__col_data[255:0], ctl_NW_p02__col_data[255:0], ctl_NW_p01__col_data[255:0], ctl_NW_p00__col_data[255:0]}),
    .col_strb({ctl_NW_p31__col_strb[31:0], ctl_NW_p30__col_strb[31:0], ctl_NW_p29__col_strb[31:0], ctl_NW_p28__col_strb[31:0], ctl_NW_p27__col_strb[31:0], ctl_NW_p26__col_strb[31:0], ctl_NW_p25__col_strb[31:0], ctl_NW_p24__col_strb[31:0], ctl_NW_p23__col_strb[31:0], ctl_NW_p22__col_strb[31:0], ctl_NW_p21__col_strb[31:0], ctl_NW_p20__col_strb[31:0], ctl_NW_p19__col_strb[31:0], ctl_NW_p18__col_strb[31:0], ctl_NW_p17__col_strb[31:0], ctl_NW_p16__col_strb[31:0], ctl_NW_p15__col_strb[31:0], ctl_NW_p14__col_strb[31:0], ctl_NW_p13__col_strb[31:0], ctl_NW_p12__col_strb[31:0], ctl_NW_p11__col_strb[31:0], ctl_NW_p10__col_strb[31:0], ctl_NW_p09__col_strb[31:0], ctl_NW_p08__col_strb[31:0], ctl_NW_p07__col_strb[31:0], ctl_NW_p06__col_strb[31:0], ctl_NW_p05__col_strb[31:0], ctl_NW_p04__col_strb[31:0], ctl_NW_p03__col_strb[31:0], ctl_NW_p02__col_strb[31:0], ctl_NW_p01__col_strb[31:0], ctl_NW_p00__col_strb[31:0]}),
    .dram_rvalid(phy_NW__dram_rvalid[31:0]),
    .dram_rdata(phy_NW__dram_rdata[8191:0])
  );
  ot_hbm_pc_refresh_cfg #(.NPC(16)) refcfg_NE (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .clk_hbm(hb_ckgen__pll_stream[0:0]),
    .rst_hbm_n(hb_ckgen__por_stream[0:0]),
    .tgt(8'b10000001),
    .cfg_v(hleaf_NE__a_cfg_v[0:0]),
    .cfg_target(hleaf_NE__a_cfg_target[7:0]),
    .cfg_addr(hleaf_NE__a_cfg_addr[11:0]),
    .cfg_data(hleaf_NE__a_cfg_data[255:0]),
    .refresh_reload(refcfg_NE__refresh_reload[127:0]),
    .pc_rst_n(refcfg_NE__pc_rst_n[0:0]),
    .ready(refcfg_NE__ready[0:0]),
    .active(refcfg_NE__active[0:0]),
    .fault(refcfg_NE__fault[0:0])
  );
  ot_hbm_pc_refresh_cfg #(.NPC(16)) refcfg_NW (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .clk_hbm(hb_ckgen__pll_stream[0:0]),
    .rst_hbm_n(hb_ckgen__por_stream[0:0]),
    .tgt(8'b01111111),
    .cfg_v(hleaf_NW__b_cfg_v[0:0]),
    .cfg_target(hleaf_NW__b_cfg_target[7:0]),
    .cfg_addr(hleaf_NW__b_cfg_addr[11:0]),
    .cfg_data(hleaf_NW__b_cfg_data[255:0]),
    .refresh_reload(refcfg_NW__refresh_reload[127:0]),
    .pc_rst_n(refcfg_NW__pc_rst_n[0:0]),
    .ready(refcfg_NW__ready[0:0]),
    .active(refcfg_NW__active[0:0]),
    .fault(refcfg_NW__fault[0:0])
  );
  ot_hbm_svc_stack_fault #(.MUT(0), .OWN_W(6), .NPC(16), .NG(4), .ND(8)) sfault_NE (
    .hbm_clk(hb_ckgen__pll_stream[0:0]),
    .hbm_rst_n(hb_ckgen__por_stream[0:0]),
    .stream_clk(hb_ckgen__pll_stream[0:0]),
    .stream_rst_n(hb_ckgen__por_stream[0:0]),
    .row_v({ctl_NW_p31__row_v[0:0], ctl_NW_p30__row_v[0:0], ctl_NW_p29__row_v[0:0], ctl_NW_p28__row_v[0:0], ctl_NW_p27__row_v[0:0], ctl_NW_p26__row_v[0:0], ctl_NW_p25__row_v[0:0], ctl_NW_p24__row_v[0:0], ctl_NW_p23__row_v[0:0], ctl_NW_p22__row_v[0:0], ctl_NW_p21__row_v[0:0], ctl_NW_p20__row_v[0:0], ctl_NW_p19__row_v[0:0], ctl_NW_p18__row_v[0:0], ctl_NW_p17__row_v[0:0], ctl_NW_p16__row_v[0:0]}),
    .pc_fault({ctl_NW_p31__pc_fault[0:0], ctl_NW_p30__pc_fault[0:0], ctl_NW_p29__pc_fault[0:0], ctl_NW_p28__pc_fault[0:0], ctl_NW_p27__pc_fault[0:0], ctl_NW_p26__pc_fault[0:0], ctl_NW_p25__pc_fault[0:0], ctl_NW_p24__pc_fault[0:0], ctl_NW_p23__pc_fault[0:0], ctl_NW_p22__pc_fault[0:0], ctl_NW_p21__pc_fault[0:0], ctl_NW_p20__pc_fault[0:0], ctl_NW_p19__pc_fault[0:0], ctl_NW_p18__pc_fault[0:0], ctl_NW_p17__pc_fault[0:0], ctl_NW_p16__pc_fault[0:0]}),
    .owner_fault({ctl_NW_p31__owner_fault_split[5:0], ctl_NW_p30__owner_fault_split[5:0], ctl_NW_p29__owner_fault_split[5:0], ctl_NW_p28__owner_fault_split[5:0], ctl_NW_p27__owner_fault_split[5:0], ctl_NW_p26__owner_fault_split[5:0], ctl_NW_p25__owner_fault_split[5:0], ctl_NW_p24__owner_fault_split[5:0], ctl_NW_p23__owner_fault_split[5:0], ctl_NW_p22__owner_fault_split[5:0], ctl_NW_p21__owner_fault_split[5:0], ctl_NW_p20__owner_fault_split[5:0], ctl_NW_p19__owner_fault_split[5:0], ctl_NW_p18__owner_fault_split[5:0], ctl_NW_p17__owner_fault_split[5:0], ctl_NW_p16__owner_fault_split[5:0]}),
    .svg_fault({svg_NW7__fault[0:0], svg_NW6__fault[0:0], svg_NW5__fault[0:0], svg_NW4__fault[0:0]}),
    .share_fault({vmks_NW7__fault[0:0], vmks_NW6__fault[0:0], vmks_NW5__fault[0:0], vmks_NW4__fault[0:0]}),
    .del_fault({vmdel_NE7__fault[0:0], vmdel_NE6__fault[0:0], vmdel_NE5__fault[0:0], vmdel_NE4__fault[0:0], vmdel_NE3__fault[0:0], vmdel_NE2__fault[0:0], vmdel_NE1__fault[0:0], vmdel_NE0__fault[0:0]}),
    .cal_fault(vmfc_NE__fault[0:0]),
    .fault(sfault_NE__fault[0:0]),
    .status(sfault_NE__status[6:0])
  );
  ot_hbm_svc_stack_fault #(.MUT(0), .OWN_W(6), .NPC(16), .NG(4), .ND(8)) sfault_NW (
    .hbm_clk(hb_ckgen__pll_stream[0:0]),
    .hbm_rst_n(hb_ckgen__por_stream[0:0]),
    .stream_clk(hb_ckgen__pll_stream[0:0]),
    .stream_rst_n(hb_ckgen__por_stream[0:0]),
    .row_v({ctl_NW_p15__row_v[0:0], ctl_NW_p14__row_v[0:0], ctl_NW_p13__row_v[0:0], ctl_NW_p12__row_v[0:0], ctl_NW_p11__row_v[0:0], ctl_NW_p10__row_v[0:0], ctl_NW_p09__row_v[0:0], ctl_NW_p08__row_v[0:0], ctl_NW_p07__row_v[0:0], ctl_NW_p06__row_v[0:0], ctl_NW_p05__row_v[0:0], ctl_NW_p04__row_v[0:0], ctl_NW_p03__row_v[0:0], ctl_NW_p02__row_v[0:0], ctl_NW_p01__row_v[0:0], ctl_NW_p00__row_v[0:0]}),
    .pc_fault({ctl_NW_p15__pc_fault[0:0], ctl_NW_p14__pc_fault[0:0], ctl_NW_p13__pc_fault[0:0], ctl_NW_p12__pc_fault[0:0], ctl_NW_p11__pc_fault[0:0], ctl_NW_p10__pc_fault[0:0], ctl_NW_p09__pc_fault[0:0], ctl_NW_p08__pc_fault[0:0], ctl_NW_p07__pc_fault[0:0], ctl_NW_p06__pc_fault[0:0], ctl_NW_p05__pc_fault[0:0], ctl_NW_p04__pc_fault[0:0], ctl_NW_p03__pc_fault[0:0], ctl_NW_p02__pc_fault[0:0], ctl_NW_p01__pc_fault[0:0], ctl_NW_p00__pc_fault[0:0]}),
    .owner_fault({ctl_NW_p15__owner_fault_split[5:0], ctl_NW_p14__owner_fault_split[5:0], ctl_NW_p13__owner_fault_split[5:0], ctl_NW_p12__owner_fault_split[5:0], ctl_NW_p11__owner_fault_split[5:0], ctl_NW_p10__owner_fault_split[5:0], ctl_NW_p09__owner_fault_split[5:0], ctl_NW_p08__owner_fault_split[5:0], ctl_NW_p07__owner_fault_split[5:0], ctl_NW_p06__owner_fault_split[5:0], ctl_NW_p05__owner_fault_split[5:0], ctl_NW_p04__owner_fault_split[5:0], ctl_NW_p03__owner_fault_split[5:0], ctl_NW_p02__owner_fault_split[5:0], ctl_NW_p01__owner_fault_split[5:0], ctl_NW_p00__owner_fault_split[5:0]}),
    .svg_fault({svg_NW3__fault[0:0], svg_NW2__fault[0:0], svg_NW1__fault[0:0], svg_NW0__fault[0:0]}),
    .share_fault({vmks_NW3__fault[0:0], vmks_NW2__fault[0:0], vmks_NW1__fault[0:0], vmks_NW0__fault[0:0]}),
    .del_fault({vmdel_NW7__fault[0:0], vmdel_NW6__fault[0:0], vmdel_NW5__fault[0:0], vmdel_NW4__fault[0:0], vmdel_NW3__fault[0:0], vmdel_NW2__fault[0:0], vmdel_NW1__fault[0:0], vmdel_NW0__fault[0:0]}),
    .cal_fault(vmfc_NW__fault[0:0]),
    .fault(sfault_NW__fault[0:0]),
    .status(sfault_NW__status[6:0])
  );
  ot_hgi_sfu_lg_pair_tap_leaf #(.READ_RETURN(29), .WRITE_RETURN(26)) sfu_NE0 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .c_rq(sfucore_NE__local_rq[33:0]),
    .c_wq(sfucore_NE__local_wq[561:0]),
    .c_rr(sfu_NE0__c_rr[513:0]),
    .c_w_done(sfu_NE0__c_w_done[1:0]),
    .local_read(calendar_NE__lg_local_read[9:8]),
    .local_write(calendar_NE__lg_local_write[9:8]),
    .far_rq(hc_NE0__near_rq[33:0]),
    .far_wq(hc_NE0__near_wq[561:0]),
    .far_rr(sfu_NE0__far_rr[513:0]),
    .far_w_done(sfu_NE0__far_w_done[1:0]),
    .near_rq(sfu_NE0__near_rq[33:0]),
    .near_wq(sfu_NE0__near_wq[561:0]),
    .near_rr(su_NE0__far_rr[513:0]),
    .near_w_done(su_NE0__far_w_done[1:0]),
    .fault(sfu_NE0__fault[0:0])
  );
  ot_hgi_sfu_lg_pair_tap_leaf #(.READ_RETURN(19), .WRITE_RETURN(16)) sfu_NE1 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .c_rq(sfucore_NE__local_rq[67:34]),
    .c_wq(sfucore_NE__local_wq[1123:562]),
    .c_rr(sfu_NE1__c_rr[513:0]),
    .c_w_done(sfu_NE1__c_w_done[1:0]),
    .local_read(calendar_NE__lg_local_read[11:10]),
    .local_write(calendar_NE__lg_local_write[11:10]),
    .far_rq(hc_NE1__near_rq[33:0]),
    .far_wq(hc_NE1__near_wq[561:0]),
    .far_rr(sfu_NE1__far_rr[513:0]),
    .far_w_done(sfu_NE1__far_w_done[1:0]),
    .near_rq(sfu_NE1__near_rq[33:0]),
    .near_wq(sfu_NE1__near_wq[561:0]),
    .near_rr(su_NE1__far_rr[513:0]),
    .near_w_done(su_NE1__far_w_done[1:0]),
    .fault(sfu_NE1__fault[0:0])
  );
  ot_hgi_sfu_lg_pair_tap_leaf #(.READ_RETURN(23), .WRITE_RETURN(20)) sfu_NE2 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .c_rq(sfucore_NE__local_rq[101:68]),
    .c_wq(sfucore_NE__local_wq[1685:1124]),
    .c_rr(sfu_NE2__c_rr[513:0]),
    .c_w_done(sfu_NE2__c_w_done[1:0]),
    .local_read(calendar_NE__lg_local_read[13:12]),
    .local_write(calendar_NE__lg_local_write[13:12]),
    .far_rq(hc_NE2__near_rq[33:0]),
    .far_wq(hc_NE2__near_wq[561:0]),
    .far_rr(sfu_NE2__far_rr[513:0]),
    .far_w_done(sfu_NE2__far_w_done[1:0]),
    .near_rq(sfu_NE2__near_rq[33:0]),
    .near_wq(sfu_NE2__near_wq[561:0]),
    .near_rr(su_NE2__far_rr[513:0]),
    .near_w_done(su_NE2__far_w_done[1:0]),
    .fault(sfu_NE2__fault[0:0])
  );
  ot_hgi_sfu_lg_pair_tap_leaf #(.READ_RETURN(19), .WRITE_RETURN(16)) sfu_NE3 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .c_rq(sfucore_NE__local_rq[135:102]),
    .c_wq(sfucore_NE__local_wq[2247:1686]),
    .c_rr(sfu_NE3__c_rr[513:0]),
    .c_w_done(sfu_NE3__c_w_done[1:0]),
    .local_read(calendar_NE__lg_local_read[15:14]),
    .local_write(calendar_NE__lg_local_write[15:14]),
    .far_rq(hc_NE3__near_rq[33:0]),
    .far_wq(hc_NE3__near_wq[561:0]),
    .far_rr(sfu_NE3__far_rr[513:0]),
    .far_w_done(sfu_NE3__far_w_done[1:0]),
    .near_rq(sfu_NE3__near_rq[33:0]),
    .near_wq(sfu_NE3__near_wq[561:0]),
    .near_rr(su_NE3__far_rr[513:0]),
    .near_w_done(su_NE3__far_w_done[1:0]),
    .fault(sfu_NE3__fault[0:0])
  );
  ot_hgi_sfu_lg_pair_tap_leaf #(.READ_RETURN(29), .WRITE_RETURN(26)) sfu_NW0 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .c_rq(sfucore_NW__local_rq[33:0]),
    .c_wq(sfucore_NW__local_wq[561:0]),
    .c_rr(sfu_NW0__c_rr[513:0]),
    .c_w_done(sfu_NW0__c_w_done[1:0]),
    .local_read(calendar_NW__lg_local_read[9:8]),
    .local_write(calendar_NW__lg_local_write[9:8]),
    .far_rq(hc_NW0__near_rq[33:0]),
    .far_wq(hc_NW0__near_wq[561:0]),
    .far_rr(sfu_NW0__far_rr[513:0]),
    .far_w_done(sfu_NW0__far_w_done[1:0]),
    .near_rq(sfu_NW0__near_rq[33:0]),
    .near_wq(sfu_NW0__near_wq[561:0]),
    .near_rr(su_NW0__far_rr[513:0]),
    .near_w_done(su_NW0__far_w_done[1:0]),
    .fault(sfu_NW0__fault[0:0])
  );
  ot_hgi_sfu_lg_pair_tap_leaf #(.READ_RETURN(19), .WRITE_RETURN(16)) sfu_NW1 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .c_rq(sfucore_NW__local_rq[67:34]),
    .c_wq(sfucore_NW__local_wq[1123:562]),
    .c_rr(sfu_NW1__c_rr[513:0]),
    .c_w_done(sfu_NW1__c_w_done[1:0]),
    .local_read(calendar_NW__lg_local_read[11:10]),
    .local_write(calendar_NW__lg_local_write[11:10]),
    .far_rq(hc_NW1__near_rq[33:0]),
    .far_wq(hc_NW1__near_wq[561:0]),
    .far_rr(sfu_NW1__far_rr[513:0]),
    .far_w_done(sfu_NW1__far_w_done[1:0]),
    .near_rq(sfu_NW1__near_rq[33:0]),
    .near_wq(sfu_NW1__near_wq[561:0]),
    .near_rr(su_NW1__far_rr[513:0]),
    .near_w_done(su_NW1__far_w_done[1:0]),
    .fault(sfu_NW1__fault[0:0])
  );
  ot_hgi_sfu_lg_pair_tap_leaf #(.READ_RETURN(23), .WRITE_RETURN(20)) sfu_NW2 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .c_rq(sfucore_NW__local_rq[101:68]),
    .c_wq(sfucore_NW__local_wq[1685:1124]),
    .c_rr(sfu_NW2__c_rr[513:0]),
    .c_w_done(sfu_NW2__c_w_done[1:0]),
    .local_read(calendar_NW__lg_local_read[13:12]),
    .local_write(calendar_NW__lg_local_write[13:12]),
    .far_rq(hc_NW2__near_rq[33:0]),
    .far_wq(hc_NW2__near_wq[561:0]),
    .far_rr(sfu_NW2__far_rr[513:0]),
    .far_w_done(sfu_NW2__far_w_done[1:0]),
    .near_rq(sfu_NW2__near_rq[33:0]),
    .near_wq(sfu_NW2__near_wq[561:0]),
    .near_rr(su_NW2__far_rr[513:0]),
    .near_w_done(su_NW2__far_w_done[1:0]),
    .fault(sfu_NW2__fault[0:0])
  );
  ot_hgi_sfu_lg_pair_tap_leaf #(.READ_RETURN(19), .WRITE_RETURN(16)) sfu_NW3 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .c_rq(sfucore_NW__local_rq[135:102]),
    .c_wq(sfucore_NW__local_wq[2247:1686]),
    .c_rr(sfu_NW3__c_rr[513:0]),
    .c_w_done(sfu_NW3__c_w_done[1:0]),
    .local_read(calendar_NW__lg_local_read[15:14]),
    .local_write(calendar_NW__lg_local_write[15:14]),
    .far_rq(hc_NW3__near_rq[33:0]),
    .far_wq(hc_NW3__near_wq[561:0]),
    .far_rr(sfu_NW3__far_rr[513:0]),
    .far_w_done(sfu_NW3__far_w_done[1:0]),
    .near_rq(sfu_NW3__near_rq[33:0]),
    .near_wq(sfu_NW3__near_wq[561:0]),
    .near_rr(su_NW3__far_rr[513:0]),
    .near_w_done(su_NW3__far_w_done[1:0]),
    .fault(sfu_NW3__fault[0:0])
  );
  ot_hgi_sfu_core_split3 #(.LWB(15), .LG_PATH(31), .TAP_RR(24), .TAP_WR(21)) sfucore_NE (
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_pw(hb_ckgen__pll_stream[0:0]),
    .clk_pe(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .clk_lg({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .rst_lg_n({hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0]}),
    .clk_lane({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .clk_map({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .rst_lane_n({hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0]}),
    .rst_map_n({hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0]}),
    .io_word(sfup_NE__io_word[470:0]),
    .compiler_control(sfup_NE__compiler_control[1741:0]),
    .local_rq(sfucore_NE__local_rq[135:0]),
    .local_rr({sfu_NE3__c_rr[513:0], sfu_NE2__c_rr[513:0], sfu_NE1__c_rr[513:0], sfu_NE0__c_rr[513:0]}),
    .local_wq(sfucore_NE__local_wq[2247:0]),
    .local_w_done({sfu_NE3__c_w_done[1:0], sfu_NE2__c_w_done[1:0], sfu_NE1__c_w_done[1:0], sfu_NE0__c_w_done[1:0]}),
    .vi_re_w(sfucore_NE__vi_re_w[3:0]),
    .vi_re_n(sfucore_NE__vi_re_n[3:0]),
    .vi_re_e(sfucore_NE__vi_re_e[3:0]),
    .vi_re_s(sfucore_NE__vi_re_s[3:0]),
    .vi_addr_w(sfucore_NE__vi_addr_w[95:0]),
    .vi_addr_n(sfucore_NE__vi_addr_n[95:0]),
    .vi_addr_e(sfucore_NE__vi_addr_e[95:0]),
    .vi_addr_s(sfucore_NE__vi_addr_s[95:0]),
    .vi_q_w({sfus_NE__l03_vi_q[31:0], sfus_NE__l02_vi_q[31:0], sfus_NE__l01_vi_q[31:0], sfus_NE__l00_vi_q[31:0]}),
    .vi_q_n({sfus_NE__l07_vi_q[31:0], sfus_NE__l06_vi_q[31:0], sfus_NE__l05_vi_q[31:0], sfus_NE__l04_vi_q[31:0]}),
    .vi_q_e({sfus_NE__l11_vi_q[31:0], sfus_NE__l10_vi_q[31:0], sfus_NE__l09_vi_q[31:0], sfus_NE__l08_vi_q[31:0]}),
    .vi_q_s({sfus_NE__l15_vi_q[31:0], sfus_NE__l14_vi_q[31:0], sfus_NE__l13_vi_q[31:0], sfus_NE__l12_vi_q[31:0]}),
    .ro_v_w(sfucore_NE__ro_v_w[3:0]),
    .ro_v_n(sfucore_NE__ro_v_n[3:0]),
    .ro_v_e(sfucore_NE__ro_v_e[3:0]),
    .ro_v_s(sfucore_NE__ro_v_s[3:0]),
    .kv_we_w(sfucore_NE__kv_we_w[3:0]),
    .kv_we_n(sfucore_NE__kv_we_n[3:0]),
    .kv_we_e(sfucore_NE__kv_we_e[3:0]),
    .kv_we_s(sfucore_NE__kv_we_s[3:0]),
    .ro_x_w(sfucore_NE__ro_x_w[127:0]),
    .ro_x_n(sfucore_NE__ro_x_n[127:0]),
    .ro_x_e(sfucore_NE__ro_x_e[127:0]),
    .ro_x_s(sfucore_NE__ro_x_s[127:0]),
    .kv_wdata_w(sfucore_NE__kv_wdata_w[127:0]),
    .kv_wdata_n(sfucore_NE__kv_wdata_n[127:0]),
    .kv_wdata_e(sfucore_NE__kv_wdata_e[127:0]),
    .kv_wdata_s(sfucore_NE__kv_wdata_s[127:0]),
    .kv_waddr_w(sfucore_NE__kv_waddr_w[95:0]),
    .kv_waddr_n(sfucore_NE__kv_waddr_n[95:0]),
    .kv_waddr_e(sfucore_NE__kv_waddr_e[95:0]),
    .kv_waddr_s(sfucore_NE__kv_waddr_s[95:0]),
    .fault(sfucore_NE__fault[0:0])
  );
  ot_hgi_sfu_core_split3 #(.LWB(15), .LG_PATH(31), .TAP_RR(24), .TAP_WR(21)) sfucore_NW (
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_pw(hb_ckgen__pll_stream[0:0]),
    .clk_pe(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .clk_lg({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .rst_lg_n({hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0]}),
    .clk_lane({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .clk_map({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .rst_lane_n({hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0]}),
    .rst_map_n({hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0]}),
    .io_word(sfup_NW__io_word[470:0]),
    .compiler_control(sfup_NW__compiler_control[1741:0]),
    .local_rq(sfucore_NW__local_rq[135:0]),
    .local_rr({sfu_NW3__c_rr[513:0], sfu_NW2__c_rr[513:0], sfu_NW1__c_rr[513:0], sfu_NW0__c_rr[513:0]}),
    .local_wq(sfucore_NW__local_wq[2247:0]),
    .local_w_done({sfu_NW3__c_w_done[1:0], sfu_NW2__c_w_done[1:0], sfu_NW1__c_w_done[1:0], sfu_NW0__c_w_done[1:0]}),
    .vi_re_w(sfucore_NW__vi_re_w[3:0]),
    .vi_re_n(sfucore_NW__vi_re_n[3:0]),
    .vi_re_e(sfucore_NW__vi_re_e[3:0]),
    .vi_re_s(sfucore_NW__vi_re_s[3:0]),
    .vi_addr_w(sfucore_NW__vi_addr_w[95:0]),
    .vi_addr_n(sfucore_NW__vi_addr_n[95:0]),
    .vi_addr_e(sfucore_NW__vi_addr_e[95:0]),
    .vi_addr_s(sfucore_NW__vi_addr_s[95:0]),
    .vi_q_w({sfus_NW__l03_vi_q[31:0], sfus_NW__l02_vi_q[31:0], sfus_NW__l01_vi_q[31:0], sfus_NW__l00_vi_q[31:0]}),
    .vi_q_n({sfus_NW__l07_vi_q[31:0], sfus_NW__l06_vi_q[31:0], sfus_NW__l05_vi_q[31:0], sfus_NW__l04_vi_q[31:0]}),
    .vi_q_e({sfus_NW__l11_vi_q[31:0], sfus_NW__l10_vi_q[31:0], sfus_NW__l09_vi_q[31:0], sfus_NW__l08_vi_q[31:0]}),
    .vi_q_s({sfus_NW__l15_vi_q[31:0], sfus_NW__l14_vi_q[31:0], sfus_NW__l13_vi_q[31:0], sfus_NW__l12_vi_q[31:0]}),
    .ro_v_w(sfucore_NW__ro_v_w[3:0]),
    .ro_v_n(sfucore_NW__ro_v_n[3:0]),
    .ro_v_e(sfucore_NW__ro_v_e[3:0]),
    .ro_v_s(sfucore_NW__ro_v_s[3:0]),
    .kv_we_w(sfucore_NW__kv_we_w[3:0]),
    .kv_we_n(sfucore_NW__kv_we_n[3:0]),
    .kv_we_e(sfucore_NW__kv_we_e[3:0]),
    .kv_we_s(sfucore_NW__kv_we_s[3:0]),
    .ro_x_w(sfucore_NW__ro_x_w[127:0]),
    .ro_x_n(sfucore_NW__ro_x_n[127:0]),
    .ro_x_e(sfucore_NW__ro_x_e[127:0]),
    .ro_x_s(sfucore_NW__ro_x_s[127:0]),
    .kv_wdata_w(sfucore_NW__kv_wdata_w[127:0]),
    .kv_wdata_n(sfucore_NW__kv_wdata_n[127:0]),
    .kv_wdata_e(sfucore_NW__kv_wdata_e[127:0]),
    .kv_wdata_s(sfucore_NW__kv_wdata_s[127:0]),
    .kv_waddr_w(sfucore_NW__kv_waddr_w[95:0]),
    .kv_waddr_n(sfucore_NW__kv_waddr_n[95:0]),
    .kv_waddr_e(sfucore_NW__kv_waddr_e[95:0]),
    .kv_waddr_s(sfucore_NW__kv_waddr_s[95:0]),
    .fault(sfucore_NW__fault[0:0])
  );
  ot_hgi_sfu_programme_store_r10 #(.PAGE_AW(1)) sfup_NE (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .cfg_we(col_sfu_NE__pw_we[0:0]),
    .cfg_stripe(col_sfu_NE__pw_addr[13:11]),
    .cfg_addr(col_sfu_NE__pw_addr[10:0]),
    .cfg_data(col_sfu_NE__pw_data[255:0]),
    .start_base(col_sfu_NE__prm[10:0]),
    .start_limit(col_sfu_NE__prm[22:11]),
    .start_loops(col_sfu_NE__prm[38:23]),
    .programme_active(sfup_NE__programme_active[0:0]),
    .programme_done(sfup_NE__programme_done[0:0]),
    .programme_ordinal(sfup_NE__programme_ordinal[31:0]),
    .io_cfg_we(col_sfu_NE__pw_we[1:1]),
    .io_cfg_stripe(col_sfu_NE__pw_addr[12:11]),
    .io_cfg_addr(col_sfu_NE__pw_addr[10:0]),
    .io_cfg_data(col_sfu_NE__pw_data[255:0]),
    .io_start_v(col_sfu_NE__start_v[0:0]),
    .io_start_base(col_sfu_NE__prm[49:39]),
    .io_start_limit(col_sfu_NE__prm[61:50]),
    .io_start_loops(col_sfu_NE__prm[77:62]),
    .io_active(sfup_NE__io_active[0:0]),
    .io_done(sfup_NE__io_done[0:0]),
    .io_ordinal(sfup_NE__io_ordinal[31:0]),
    .io_word(sfup_NE__io_word[470:0]),
    .compiler_control(sfup_NE__compiler_control[1741:0]),
    .fault(sfup_NE__fault[0:0])
  );
  ot_hgi_sfu_programme_store_r10 #(.PAGE_AW(1)) sfup_NW (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .cfg_we(col_sfu_NW__pw_we[0:0]),
    .cfg_stripe(col_sfu_NW__pw_addr[13:11]),
    .cfg_addr(col_sfu_NW__pw_addr[10:0]),
    .cfg_data(col_sfu_NW__pw_data[255:0]),
    .start_base(col_sfu_NW__prm[10:0]),
    .start_limit(col_sfu_NW__prm[22:11]),
    .start_loops(col_sfu_NW__prm[38:23]),
    .programme_active(sfup_NW__programme_active[0:0]),
    .programme_done(sfup_NW__programme_done[0:0]),
    .programme_ordinal(sfup_NW__programme_ordinal[31:0]),
    .io_cfg_we(col_sfu_NW__pw_we[1:1]),
    .io_cfg_stripe(col_sfu_NW__pw_addr[12:11]),
    .io_cfg_addr(col_sfu_NW__pw_addr[10:0]),
    .io_cfg_data(col_sfu_NW__pw_data[255:0]),
    .io_start_v(col_sfu_NW__start_v[0:0]),
    .io_start_base(col_sfu_NW__prm[49:39]),
    .io_start_limit(col_sfu_NW__prm[61:50]),
    .io_start_loops(col_sfu_NW__prm[77:62]),
    .io_active(sfup_NW__io_active[0:0]),
    .io_done(sfup_NW__io_done[0:0]),
    .io_ordinal(sfup_NW__io_ordinal[31:0]),
    .io_word(sfup_NW__io_word[470:0]),
    .compiler_control(sfup_NW__compiler_control[1741:0]),
    .fault(sfup_NW__fault[0:0])
  );
  ot_hbm_su_static_sfustore_hw sfus_NE (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .qid(2'b11),
    .l00_vi_re(sfucore_NE__vi_re_w[0:0]),
    .l01_vi_re(sfucore_NE__vi_re_w[1:1]),
    .l02_vi_re(sfucore_NE__vi_re_w[2:2]),
    .l03_vi_re(sfucore_NE__vi_re_w[3:3]),
    .l04_vi_re(sfucore_NE__vi_re_n[0:0]),
    .l05_vi_re(sfucore_NE__vi_re_n[1:1]),
    .l06_vi_re(sfucore_NE__vi_re_n[2:2]),
    .l07_vi_re(sfucore_NE__vi_re_n[3:3]),
    .l08_vi_re(sfucore_NE__vi_re_e[0:0]),
    .l09_vi_re(sfucore_NE__vi_re_e[1:1]),
    .l10_vi_re(sfucore_NE__vi_re_e[2:2]),
    .l11_vi_re(sfucore_NE__vi_re_e[3:3]),
    .l12_vi_re(sfucore_NE__vi_re_s[0:0]),
    .l13_vi_re(sfucore_NE__vi_re_s[1:1]),
    .l14_vi_re(sfucore_NE__vi_re_s[2:2]),
    .l15_vi_re(sfucore_NE__vi_re_s[3:3]),
    .l00_vi_addr(sfucore_NE__vi_addr_w[23:0]),
    .l01_vi_addr(sfucore_NE__vi_addr_w[47:24]),
    .l02_vi_addr(sfucore_NE__vi_addr_w[71:48]),
    .l03_vi_addr(sfucore_NE__vi_addr_w[95:72]),
    .l04_vi_addr(sfucore_NE__vi_addr_n[23:0]),
    .l05_vi_addr(sfucore_NE__vi_addr_n[47:24]),
    .l06_vi_addr(sfucore_NE__vi_addr_n[71:48]),
    .l07_vi_addr(sfucore_NE__vi_addr_n[95:72]),
    .l08_vi_addr(sfucore_NE__vi_addr_e[23:0]),
    .l09_vi_addr(sfucore_NE__vi_addr_e[47:24]),
    .l10_vi_addr(sfucore_NE__vi_addr_e[71:48]),
    .l11_vi_addr(sfucore_NE__vi_addr_e[95:72]),
    .l12_vi_addr(sfucore_NE__vi_addr_s[23:0]),
    .l13_vi_addr(sfucore_NE__vi_addr_s[47:24]),
    .l14_vi_addr(sfucore_NE__vi_addr_s[71:48]),
    .l15_vi_addr(sfucore_NE__vi_addr_s[95:72]),
    .l00_vi_q(sfus_NE__l00_vi_q[31:0]),
    .l01_vi_q(sfus_NE__l01_vi_q[31:0]),
    .l02_vi_q(sfus_NE__l02_vi_q[31:0]),
    .l03_vi_q(sfus_NE__l03_vi_q[31:0]),
    .l04_vi_q(sfus_NE__l04_vi_q[31:0]),
    .l05_vi_q(sfus_NE__l05_vi_q[31:0]),
    .l06_vi_q(sfus_NE__l06_vi_q[31:0]),
    .l07_vi_q(sfus_NE__l07_vi_q[31:0]),
    .l08_vi_q(sfus_NE__l08_vi_q[31:0]),
    .l09_vi_q(sfus_NE__l09_vi_q[31:0]),
    .l10_vi_q(sfus_NE__l10_vi_q[31:0]),
    .l11_vi_q(sfus_NE__l11_vi_q[31:0]),
    .l12_vi_q(sfus_NE__l12_vi_q[31:0]),
    .l13_vi_q(sfus_NE__l13_vi_q[31:0]),
    .l14_vi_q(sfus_NE__l14_vi_q[31:0]),
    .l15_vi_q(sfus_NE__l15_vi_q[31:0]),
    .l00_kv_we(sfucore_NE__kv_we_w[0:0]),
    .l01_kv_we(sfucore_NE__kv_we_w[1:1]),
    .l02_kv_we(sfucore_NE__kv_we_w[2:2]),
    .l03_kv_we(sfucore_NE__kv_we_w[3:3]),
    .l04_kv_we(sfucore_NE__kv_we_n[0:0]),
    .l05_kv_we(sfucore_NE__kv_we_n[1:1]),
    .l06_kv_we(sfucore_NE__kv_we_n[2:2]),
    .l07_kv_we(sfucore_NE__kv_we_n[3:3]),
    .l08_kv_we(sfucore_NE__kv_we_e[0:0]),
    .l09_kv_we(sfucore_NE__kv_we_e[1:1]),
    .l10_kv_we(sfucore_NE__kv_we_e[2:2]),
    .l11_kv_we(sfucore_NE__kv_we_e[3:3]),
    .l12_kv_we(sfucore_NE__kv_we_s[0:0]),
    .l13_kv_we(sfucore_NE__kv_we_s[1:1]),
    .l14_kv_we(sfucore_NE__kv_we_s[2:2]),
    .l15_kv_we(sfucore_NE__kv_we_s[3:3]),
    .l00_kv_waddr(sfucore_NE__kv_waddr_w[23:0]),
    .l01_kv_waddr(sfucore_NE__kv_waddr_w[47:24]),
    .l02_kv_waddr(sfucore_NE__kv_waddr_w[71:48]),
    .l03_kv_waddr(sfucore_NE__kv_waddr_w[95:72]),
    .l04_kv_waddr(sfucore_NE__kv_waddr_n[23:0]),
    .l05_kv_waddr(sfucore_NE__kv_waddr_n[47:24]),
    .l06_kv_waddr(sfucore_NE__kv_waddr_n[71:48]),
    .l07_kv_waddr(sfucore_NE__kv_waddr_n[95:72]),
    .l08_kv_waddr(sfucore_NE__kv_waddr_e[23:0]),
    .l09_kv_waddr(sfucore_NE__kv_waddr_e[47:24]),
    .l10_kv_waddr(sfucore_NE__kv_waddr_e[71:48]),
    .l11_kv_waddr(sfucore_NE__kv_waddr_e[95:72]),
    .l12_kv_waddr(sfucore_NE__kv_waddr_s[23:0]),
    .l13_kv_waddr(sfucore_NE__kv_waddr_s[47:24]),
    .l14_kv_waddr(sfucore_NE__kv_waddr_s[71:48]),
    .l15_kv_waddr(sfucore_NE__kv_waddr_s[95:72]),
    .l00_kv_wdata(sfucore_NE__kv_wdata_w[31:0]),
    .l01_kv_wdata(sfucore_NE__kv_wdata_w[63:32]),
    .l02_kv_wdata(sfucore_NE__kv_wdata_w[95:64]),
    .l03_kv_wdata(sfucore_NE__kv_wdata_w[127:96]),
    .l04_kv_wdata(sfucore_NE__kv_wdata_n[31:0]),
    .l05_kv_wdata(sfucore_NE__kv_wdata_n[63:32]),
    .l06_kv_wdata(sfucore_NE__kv_wdata_n[95:64]),
    .l07_kv_wdata(sfucore_NE__kv_wdata_n[127:96]),
    .l08_kv_wdata(sfucore_NE__kv_wdata_e[31:0]),
    .l09_kv_wdata(sfucore_NE__kv_wdata_e[63:32]),
    .l10_kv_wdata(sfucore_NE__kv_wdata_e[95:64]),
    .l11_kv_wdata(sfucore_NE__kv_wdata_e[127:96]),
    .l12_kv_wdata(sfucore_NE__kv_wdata_s[31:0]),
    .l13_kv_wdata(sfucore_NE__kv_wdata_s[63:32]),
    .l14_kv_wdata(sfucore_NE__kv_wdata_s[95:64]),
    .l15_kv_wdata(sfucore_NE__kv_wdata_s[127:96]),
    .fault(sfus_NE__fault[0:0])
  );
  ot_hbm_su_static_sfustore_hw sfus_NW (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .qid(2'b10),
    .l00_vi_re(sfucore_NW__vi_re_w[0:0]),
    .l01_vi_re(sfucore_NW__vi_re_w[1:1]),
    .l02_vi_re(sfucore_NW__vi_re_w[2:2]),
    .l03_vi_re(sfucore_NW__vi_re_w[3:3]),
    .l04_vi_re(sfucore_NW__vi_re_n[0:0]),
    .l05_vi_re(sfucore_NW__vi_re_n[1:1]),
    .l06_vi_re(sfucore_NW__vi_re_n[2:2]),
    .l07_vi_re(sfucore_NW__vi_re_n[3:3]),
    .l08_vi_re(sfucore_NW__vi_re_e[0:0]),
    .l09_vi_re(sfucore_NW__vi_re_e[1:1]),
    .l10_vi_re(sfucore_NW__vi_re_e[2:2]),
    .l11_vi_re(sfucore_NW__vi_re_e[3:3]),
    .l12_vi_re(sfucore_NW__vi_re_s[0:0]),
    .l13_vi_re(sfucore_NW__vi_re_s[1:1]),
    .l14_vi_re(sfucore_NW__vi_re_s[2:2]),
    .l15_vi_re(sfucore_NW__vi_re_s[3:3]),
    .l00_vi_addr(sfucore_NW__vi_addr_w[23:0]),
    .l01_vi_addr(sfucore_NW__vi_addr_w[47:24]),
    .l02_vi_addr(sfucore_NW__vi_addr_w[71:48]),
    .l03_vi_addr(sfucore_NW__vi_addr_w[95:72]),
    .l04_vi_addr(sfucore_NW__vi_addr_n[23:0]),
    .l05_vi_addr(sfucore_NW__vi_addr_n[47:24]),
    .l06_vi_addr(sfucore_NW__vi_addr_n[71:48]),
    .l07_vi_addr(sfucore_NW__vi_addr_n[95:72]),
    .l08_vi_addr(sfucore_NW__vi_addr_e[23:0]),
    .l09_vi_addr(sfucore_NW__vi_addr_e[47:24]),
    .l10_vi_addr(sfucore_NW__vi_addr_e[71:48]),
    .l11_vi_addr(sfucore_NW__vi_addr_e[95:72]),
    .l12_vi_addr(sfucore_NW__vi_addr_s[23:0]),
    .l13_vi_addr(sfucore_NW__vi_addr_s[47:24]),
    .l14_vi_addr(sfucore_NW__vi_addr_s[71:48]),
    .l15_vi_addr(sfucore_NW__vi_addr_s[95:72]),
    .l00_vi_q(sfus_NW__l00_vi_q[31:0]),
    .l01_vi_q(sfus_NW__l01_vi_q[31:0]),
    .l02_vi_q(sfus_NW__l02_vi_q[31:0]),
    .l03_vi_q(sfus_NW__l03_vi_q[31:0]),
    .l04_vi_q(sfus_NW__l04_vi_q[31:0]),
    .l05_vi_q(sfus_NW__l05_vi_q[31:0]),
    .l06_vi_q(sfus_NW__l06_vi_q[31:0]),
    .l07_vi_q(sfus_NW__l07_vi_q[31:0]),
    .l08_vi_q(sfus_NW__l08_vi_q[31:0]),
    .l09_vi_q(sfus_NW__l09_vi_q[31:0]),
    .l10_vi_q(sfus_NW__l10_vi_q[31:0]),
    .l11_vi_q(sfus_NW__l11_vi_q[31:0]),
    .l12_vi_q(sfus_NW__l12_vi_q[31:0]),
    .l13_vi_q(sfus_NW__l13_vi_q[31:0]),
    .l14_vi_q(sfus_NW__l14_vi_q[31:0]),
    .l15_vi_q(sfus_NW__l15_vi_q[31:0]),
    .l00_kv_we(sfucore_NW__kv_we_w[0:0]),
    .l01_kv_we(sfucore_NW__kv_we_w[1:1]),
    .l02_kv_we(sfucore_NW__kv_we_w[2:2]),
    .l03_kv_we(sfucore_NW__kv_we_w[3:3]),
    .l04_kv_we(sfucore_NW__kv_we_n[0:0]),
    .l05_kv_we(sfucore_NW__kv_we_n[1:1]),
    .l06_kv_we(sfucore_NW__kv_we_n[2:2]),
    .l07_kv_we(sfucore_NW__kv_we_n[3:3]),
    .l08_kv_we(sfucore_NW__kv_we_e[0:0]),
    .l09_kv_we(sfucore_NW__kv_we_e[1:1]),
    .l10_kv_we(sfucore_NW__kv_we_e[2:2]),
    .l11_kv_we(sfucore_NW__kv_we_e[3:3]),
    .l12_kv_we(sfucore_NW__kv_we_s[0:0]),
    .l13_kv_we(sfucore_NW__kv_we_s[1:1]),
    .l14_kv_we(sfucore_NW__kv_we_s[2:2]),
    .l15_kv_we(sfucore_NW__kv_we_s[3:3]),
    .l00_kv_waddr(sfucore_NW__kv_waddr_w[23:0]),
    .l01_kv_waddr(sfucore_NW__kv_waddr_w[47:24]),
    .l02_kv_waddr(sfucore_NW__kv_waddr_w[71:48]),
    .l03_kv_waddr(sfucore_NW__kv_waddr_w[95:72]),
    .l04_kv_waddr(sfucore_NW__kv_waddr_n[23:0]),
    .l05_kv_waddr(sfucore_NW__kv_waddr_n[47:24]),
    .l06_kv_waddr(sfucore_NW__kv_waddr_n[71:48]),
    .l07_kv_waddr(sfucore_NW__kv_waddr_n[95:72]),
    .l08_kv_waddr(sfucore_NW__kv_waddr_e[23:0]),
    .l09_kv_waddr(sfucore_NW__kv_waddr_e[47:24]),
    .l10_kv_waddr(sfucore_NW__kv_waddr_e[71:48]),
    .l11_kv_waddr(sfucore_NW__kv_waddr_e[95:72]),
    .l12_kv_waddr(sfucore_NW__kv_waddr_s[23:0]),
    .l13_kv_waddr(sfucore_NW__kv_waddr_s[47:24]),
    .l14_kv_waddr(sfucore_NW__kv_waddr_s[71:48]),
    .l15_kv_waddr(sfucore_NW__kv_waddr_s[95:72]),
    .l00_kv_wdata(sfucore_NW__kv_wdata_w[31:0]),
    .l01_kv_wdata(sfucore_NW__kv_wdata_w[63:32]),
    .l02_kv_wdata(sfucore_NW__kv_wdata_w[95:64]),
    .l03_kv_wdata(sfucore_NW__kv_wdata_w[127:96]),
    .l04_kv_wdata(sfucore_NW__kv_wdata_n[31:0]),
    .l05_kv_wdata(sfucore_NW__kv_wdata_n[63:32]),
    .l06_kv_wdata(sfucore_NW__kv_wdata_n[95:64]),
    .l07_kv_wdata(sfucore_NW__kv_wdata_n[127:96]),
    .l08_kv_wdata(sfucore_NW__kv_wdata_e[31:0]),
    .l09_kv_wdata(sfucore_NW__kv_wdata_e[63:32]),
    .l10_kv_wdata(sfucore_NW__kv_wdata_e[95:64]),
    .l11_kv_wdata(sfucore_NW__kv_wdata_e[127:96]),
    .l12_kv_wdata(sfucore_NW__kv_wdata_s[31:0]),
    .l13_kv_wdata(sfucore_NW__kv_wdata_s[63:32]),
    .l14_kv_wdata(sfucore_NW__kv_wdata_s[95:64]),
    .l15_kv_wdata(sfucore_NW__kv_wdata_s[127:96]),
    .fault(sfus_NW__fault[0:0])
  );
  ot_hbm_accel_smh_attn #(.ENABLE_INT8(1), .INT8W(1)) sm_NW0 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .command({xc_NW0__cmd_ext[108:0], svg_NW0__sm_command[82:0]}),
    .kv_desc(xc_NW0__kv_desc[63:0]),
    .packet(svg_NW0__sm_packet[1098:0]),
    .request(sm_NW0__request[42:0]),
    .xw_en(xq_NW_p0_eg__xw_en[0:0]),
    .xw_addr(xq_NW_p0_eg__xw_addr[6:0]),
    .xw_grp(xq_NW_p0_eg__xw_grp[6:0]),
    .xw_data(xq_NW_p0_eg__xw_data[2047:0]),
    .rv(sm_NW0__rv[0:0]),
    .rrow(sm_NW0__rrow[11:0]),
    .rdata(sm_NW0__rdata[255:0]),
    .fault(sm_NW0__fault[0:0]),
    .schedule_fault(sm_NW0__schedule_fault[0:0])
  );
  ot_hbm_accel_smh_attn #(.ENABLE_INT8(1), .INT8W(1)) sm_NW1 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .command({xc_NW1__cmd_ext[108:0], svg_NW1__sm_command[82:0]}),
    .kv_desc(xc_NW1__kv_desc[63:0]),
    .packet(svg_NW1__sm_packet[1098:0]),
    .request(sm_NW1__request[42:0]),
    .xw_en(xq_NW_p0_eg__xw_en[0:0]),
    .xw_addr(xq_NW_p0_eg__xw_addr[6:0]),
    .xw_grp(xq_NW_p0_eg__xw_grp[6:0]),
    .xw_data(xq_NW_p0_eg__xw_data[2047:0]),
    .rv(sm_NW1__rv[0:0]),
    .rrow(sm_NW1__rrow[11:0]),
    .rdata(sm_NW1__rdata[255:0]),
    .fault(sm_NW1__fault[0:0]),
    .schedule_fault(sm_NW1__schedule_fault[0:0])
  );
  ot_hbm_accel_smh_attn #(.ENABLE_INT8(1), .INT8W(1)) sm_NW2 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .command({xc_NW2__cmd_ext[108:0], svg_NW2__sm_command[82:0]}),
    .kv_desc(xc_NW2__kv_desc[63:0]),
    .packet(svg_NW2__sm_packet[1098:0]),
    .request(sm_NW2__request[42:0]),
    .xw_en(xq_NW_p1_eg__xw_en[0:0]),
    .xw_addr(xq_NW_p1_eg__xw_addr[6:0]),
    .xw_grp(xq_NW_p1_eg__xw_grp[6:0]),
    .xw_data(xq_NW_p1_eg__xw_data[2047:0]),
    .rv(sm_NW2__rv[0:0]),
    .rrow(sm_NW2__rrow[11:0]),
    .rdata(sm_NW2__rdata[255:0]),
    .fault(sm_NW2__fault[0:0]),
    .schedule_fault(sm_NW2__schedule_fault[0:0])
  );
  ot_hbm_accel_smh_attn #(.ENABLE_INT8(1), .INT8W(1)) sm_NW3 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .command({xc_NW3__cmd_ext[108:0], svg_NW3__sm_command[82:0]}),
    .kv_desc(xc_NW3__kv_desc[63:0]),
    .packet(svg_NW3__sm_packet[1098:0]),
    .request(sm_NW3__request[42:0]),
    .xw_en(xq_NW_p1_eg__xw_en[0:0]),
    .xw_addr(xq_NW_p1_eg__xw_addr[6:0]),
    .xw_grp(xq_NW_p1_eg__xw_grp[6:0]),
    .xw_data(xq_NW_p1_eg__xw_data[2047:0]),
    .rv(sm_NW3__rv[0:0]),
    .rrow(sm_NW3__rrow[11:0]),
    .rdata(sm_NW3__rdata[255:0]),
    .fault(sm_NW3__fault[0:0]),
    .schedule_fault(sm_NW3__schedule_fault[0:0])
  );
  ot_hbm_accel_smh_attn #(.ENABLE_INT8(1), .INT8W(1)) sm_NW4 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .command({xc_NW4__cmd_ext[108:0], svg_NW4__sm_command[82:0]}),
    .kv_desc(xc_NW4__kv_desc[63:0]),
    .packet(svg_NW4__sm_packet[1098:0]),
    .request(sm_NW4__request[42:0]),
    .xw_en(xq_NE_p0_eg__xw_en[0:0]),
    .xw_addr(xq_NE_p0_eg__xw_addr[6:0]),
    .xw_grp(xq_NE_p0_eg__xw_grp[6:0]),
    .xw_data(xq_NE_p0_eg__xw_data[2047:0]),
    .rv(sm_NW4__rv[0:0]),
    .rrow(sm_NW4__rrow[11:0]),
    .rdata(sm_NW4__rdata[255:0]),
    .fault(sm_NW4__fault[0:0]),
    .schedule_fault(sm_NW4__schedule_fault[0:0])
  );
  ot_hbm_accel_smh_attn #(.ENABLE_INT8(1), .INT8W(1)) sm_NW5 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .command({xc_NW5__cmd_ext[108:0], svg_NW5__sm_command[82:0]}),
    .kv_desc(xc_NW5__kv_desc[63:0]),
    .packet(svg_NW5__sm_packet[1098:0]),
    .request(sm_NW5__request[42:0]),
    .xw_en(xq_NE_p0_eg__xw_en[0:0]),
    .xw_addr(xq_NE_p0_eg__xw_addr[6:0]),
    .xw_grp(xq_NE_p0_eg__xw_grp[6:0]),
    .xw_data(xq_NE_p0_eg__xw_data[2047:0]),
    .rv(sm_NW5__rv[0:0]),
    .rrow(sm_NW5__rrow[11:0]),
    .rdata(sm_NW5__rdata[255:0]),
    .fault(sm_NW5__fault[0:0]),
    .schedule_fault(sm_NW5__schedule_fault[0:0])
  );
  ot_hbm_accel_smh_attn #(.ENABLE_INT8(1), .INT8W(1)) sm_NW6 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .command({xc_NW6__cmd_ext[108:0], svg_NW6__sm_command[82:0]}),
    .kv_desc(xc_NW6__kv_desc[63:0]),
    .packet(svg_NW6__sm_packet[1098:0]),
    .request(sm_NW6__request[42:0]),
    .xw_en(xq_NE_p1_eg__xw_en[0:0]),
    .xw_addr(xq_NE_p1_eg__xw_addr[6:0]),
    .xw_grp(xq_NE_p1_eg__xw_grp[6:0]),
    .xw_data(xq_NE_p1_eg__xw_data[2047:0]),
    .rv(sm_NW6__rv[0:0]),
    .rrow(sm_NW6__rrow[11:0]),
    .rdata(sm_NW6__rdata[255:0]),
    .fault(sm_NW6__fault[0:0]),
    .schedule_fault(sm_NW6__schedule_fault[0:0])
  );
  ot_hbm_accel_smh_attn #(.ENABLE_INT8(1), .INT8W(1)) sm_NW7 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .command({xc_NW7__cmd_ext[108:0], svg_NW7__sm_command[82:0]}),
    .kv_desc(xc_NW7__kv_desc[63:0]),
    .packet(svg_NW7__sm_packet[1098:0]),
    .request(sm_NW7__request[42:0]),
    .xw_en(xq_NE_p1_eg__xw_en[0:0]),
    .xw_addr(xq_NE_p1_eg__xw_addr[6:0]),
    .xw_grp(xq_NE_p1_eg__xw_grp[6:0]),
    .xw_data(xq_NE_p1_eg__xw_data[2047:0]),
    .rv(sm_NW7__rv[0:0]),
    .rrow(sm_NW7__rrow[11:0]),
    .rdata(sm_NW7__rdata[255:0]),
    .fault(sm_NW7__fault[0:0]),
    .schedule_fault(sm_NW7__schedule_fault[0:0])
  );
  ot_hbm_sm_vm_wr_q_t_lanes4 #(.DEPTH(4)) smw_NE (
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_cal(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .tgt(8'b10100011),
    .quad(2'b11),
    .lbase(1'b1),
    .cfg_v(hleaf_NE__a_cfg_v[0:0]),
    .cfg_target(hleaf_NE__a_cfg_target[7:0]),
    .cfg_addr(hleaf_NE__a_cfg_addr[11:0]),
    .cfg_data(hleaf_NE__a_cfg_data[255:0]),
    .desc_v(hleaf_NE__a_desc_v[0:0]),
    .desc_base(hleaf_NE__a_desc_base[11:0]),
    .desc_limit(hleaf_NE__a_desc_limit[12:0]),
    .desc_loops(hleaf_NE__a_desc_loops[15:0]),
    .launch_v(hleaf_NE__a_launch_v[0:0]),
    .clk_l0(hb_ckgen__pll_stream[0:0]),
    .rv_s0(sm_NW4__rv[0:0]),
    .smf_s0(sm_NW4__fault[0:0]),
    .sms_s0(sm_NW4__schedule_fault[0:0]),
    .rrow_s0(sm_NW4__rrow[11:0]),
    .rdata_s0(sm_NW4__rdata[255:0]),
    .wq_s0(smw_NE__wq_s0[280:0]),
    .wq_t0(smw_NE__wq_t0[280:0]),
    .clk_l1(hb_ckgen__pll_stream[0:0]),
    .rv_s1(sm_NW5__rv[0:0]),
    .smf_s1(sm_NW5__fault[0:0]),
    .sms_s1(sm_NW5__schedule_fault[0:0]),
    .rrow_s1(sm_NW5__rrow[11:0]),
    .rdata_s1(sm_NW5__rdata[255:0]),
    .wq_s1(smw_NE__wq_s1[280:0]),
    .wq_t1(smw_NE__wq_t1[280:0]),
    .clk_l2(hb_ckgen__pll_stream[0:0]),
    .rv_s2(sm_NW6__rv[0:0]),
    .smf_s2(sm_NW6__fault[0:0]),
    .sms_s2(sm_NW6__schedule_fault[0:0]),
    .rrow_s2(sm_NW6__rrow[11:0]),
    .rdata_s2(sm_NW6__rdata[255:0]),
    .wq_s2(smw_NE__wq_s2[280:0]),
    .wq_t2(smw_NE__wq_t2[280:0]),
    .clk_l3(hb_ckgen__pll_stream[0:0]),
    .rv_s3(sm_NW7__rv[0:0]),
    .smf_s3(sm_NW7__fault[0:0]),
    .sms_s3(sm_NW7__schedule_fault[0:0]),
    .rrow_s3(sm_NW7__rrow[11:0]),
    .rdata_s3(sm_NW7__rdata[255:0]),
    .wq_s3(smw_NE__wq_s3[280:0]),
    .wq_t3(smw_NE__wq_t3[280:0]),
    .configured(smw_NE__configured[0:0]),
    .fault(smw_NE__fault[0:0]),
    .active(smw_NE__active[0:0])
  );
  ot_hbm_sm_vm_wr_q_t_lanes4 #(.DEPTH(4)) smw_NW (
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_cal(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .tgt(8'b10100010),
    .quad(2'b10),
    .lbase(1'b0),
    .cfg_v(hleaf_NW__a_cfg_v[0:0]),
    .cfg_target(hleaf_NW__a_cfg_target[7:0]),
    .cfg_addr(hleaf_NW__a_cfg_addr[11:0]),
    .cfg_data(hleaf_NW__a_cfg_data[255:0]),
    .desc_v(hleaf_NW__a_desc_v[0:0]),
    .desc_base(hleaf_NW__a_desc_base[11:0]),
    .desc_limit(hleaf_NW__a_desc_limit[12:0]),
    .desc_loops(hleaf_NW__a_desc_loops[15:0]),
    .launch_v(hleaf_NW__a_launch_v[0:0]),
    .clk_l0(hb_ckgen__pll_stream[0:0]),
    .rv_s0(sm_NW0__rv[0:0]),
    .smf_s0(sm_NW0__fault[0:0]),
    .sms_s0(sm_NW0__schedule_fault[0:0]),
    .rrow_s0(sm_NW0__rrow[11:0]),
    .rdata_s0(sm_NW0__rdata[255:0]),
    .wq_s0(smw_NW__wq_s0[280:0]),
    .wq_t0(smw_NW__wq_t0[280:0]),
    .clk_l1(hb_ckgen__pll_stream[0:0]),
    .rv_s1(sm_NW1__rv[0:0]),
    .smf_s1(sm_NW1__fault[0:0]),
    .sms_s1(sm_NW1__schedule_fault[0:0]),
    .rrow_s1(sm_NW1__rrow[11:0]),
    .rdata_s1(sm_NW1__rdata[255:0]),
    .wq_s1(smw_NW__wq_s1[280:0]),
    .wq_t1(smw_NW__wq_t1[280:0]),
    .clk_l2(hb_ckgen__pll_stream[0:0]),
    .rv_s2(sm_NW2__rv[0:0]),
    .smf_s2(sm_NW2__fault[0:0]),
    .sms_s2(sm_NW2__schedule_fault[0:0]),
    .rrow_s2(sm_NW2__rrow[11:0]),
    .rdata_s2(sm_NW2__rdata[255:0]),
    .wq_s2(smw_NW__wq_s2[280:0]),
    .wq_t2(smw_NW__wq_t2[280:0]),
    .clk_l3(hb_ckgen__pll_stream[0:0]),
    .rv_s3(sm_NW3__rv[0:0]),
    .smf_s3(sm_NW3__fault[0:0]),
    .sms_s3(sm_NW3__schedule_fault[0:0]),
    .rrow_s3(sm_NW3__rrow[11:0]),
    .rdata_s3(sm_NW3__rdata[255:0]),
    .wq_s3(smw_NW__wq_s3[280:0]),
    .wq_t3(smw_NW__wq_t3[280:0]),
    .configured(smw_NW__configured[0:0]),
    .fault(smw_NW__fault[0:0]),
    .active(smw_NW__active[0:0])
  );
  ot_hbm_su_stree_leaf #(.MUT(0), .NLEG(2)) stl_NE (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .head_i({sucore_NE__red_rf_v[0:0], sucore_NE__red_tag[7:0], sucore_NE__red_x[31:0]}),
    .up_o(stl_NE__up_o[40:0]),
    .dn_i(str_C__dn1_o[81:0]),
    .rf_wv(stl_NE__rf_wv[1:0]),
    .rf_wa(stl_NE__rf_wa[15:0]),
    .rf_wd(stl_NE__rf_wd[63:0])
  );
  ot_hbm_su_stree_leaf #(.MUT(0), .NLEG(2)) stl_NW (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .head_i({sucore_NW__red_rf_v[0:0], sucore_NW__red_tag[7:0], sucore_NW__red_x[31:0]}),
    .up_o(stl_NW__up_o[40:0]),
    .dn_i(str_C__dn0_o[81:0]),
    .rf_wv(stl_NW__rf_wv[1:0]),
    .rf_wa(stl_NW__rf_wa[15:0]),
    .rf_wd(stl_NW__rf_wd[63:0])
  );
  ot_hbm_su_stree_root2 #(.MUT(0)) str_C (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .up0_i(stl_NW__up_o[40:0]),
    .up1_i(stl_NE__up_o[40:0]),
    .dn0_o(str_C__dn0_o[81:0]),
    .dn1_o(str_C__dn1_o[81:0])
  );
  ot_hbm_su_static_pgslice_lg #(.QID(3), .G(0), .READ_RETURN(25), .WRITE_RETURN(22), .FETCH_EXTRA_EDGES(2), .MLAT(4), .ALAT(4), .LEAF(1), .MUT(0), .MULTIRATE(0), .COLLPORT(1), .RF_LOCAL(1), .PRETREE(1), .RSYNC(0)) su_NE0 (
    .pg_clk(hb_ckgen__pll_stream[0:0]),
    .clk_lane({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .clk_insert({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .rst_lane_n({hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0]}),
    .clk_bcast({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .rst_bcast_n({hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0]}),
    .clk_bank({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .clk_bank_macro({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .clk_ctl(hb_ckgen__pll_stream[0:0]),
    .clk_side({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .bridge_rst_n(hb_ckgen__por_stream[0:0]),
    .control(pgp_NE__command[2421:680]),
    .vmr_cmd(pgp_NE__command[499:440]),
    .vmw_cmd(pgp_NE__command[205:128]),
    .rf_bword(sucore_NE__rf_bword[127:0]),
    .rf_bcmd(sucore_NE__rf_bcmd[35:0]),
    .rf_dsec(sucore_NE__rf_dsec[255:0]),
    .red_sel({pgp_NE__command[73:70], pgp_NE__command[7:0]}),
    .slice_x(su_NE0__slice_x[31:0]),
    .inj_rd(cic_NE__inj_rd_o[1:0]),
    .inj_addr(cic_NE__inj_addr_o[159:0]),
    .inj_q(su_NE0__inj_q[1023:0]),
    .dw_v(cxdl_NE0_q__dw_v[1:0]),
    .dw_row(cxdl_NE0_q__dw_row[17:0]),
    .dw_d(cxdl_NE0_q__dw_d[1023:0]),
    .fault(su_NE0__fault[0:0]),
    .lg_rq(su_NE0__lg_rq[33:0]),
    .lg_wq(su_NE0__lg_wq[561:0]),
    .lg_rr({vmb_NE1__rr0[256:0], vmb_NE0__rr0[256:0]}),
    .lg_w_done({vmb_NE1__wq_done0[0:0], vmb_NE0__wq_done0[0:0]}),
    .lg_read(calendar_NE__lg_local_read[1:0]),
    .lg_write(calendar_NE__lg_local_write[1:0]),
    .far_rq(sfu_NE0__near_rq[33:0]),
    .far_wq(sfu_NE0__near_wq[561:0]),
    .far_rr(su_NE0__far_rr[513:0]),
    .far_w_done(su_NE0__far_w_done[1:0]),
    .lg_fault(su_NE0__lg_fault[0:0]),
    .tree_cmd(pgp_NE__command[2433:2422]),
    .tree_o(su_NE0__tree_o[66:0])
  );
  ot_hbm_su_static_pgslice_lg #(.QID(3), .G(1), .READ_RETURN(15), .WRITE_RETURN(12), .FETCH_EXTRA_EDGES(2), .MLAT(4), .ALAT(4), .LEAF(1), .MUT(0), .MULTIRATE(0), .COLLPORT(1), .RF_LOCAL(1), .PRETREE(1), .RSYNC(0)) su_NE1 (
    .pg_clk(hb_ckgen__pll_stream[0:0]),
    .clk_lane({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .clk_insert({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .rst_lane_n({hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0]}),
    .clk_bcast({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .rst_bcast_n({hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0]}),
    .clk_bank({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .clk_bank_macro({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .clk_ctl(hb_ckgen__pll_stream[0:0]),
    .clk_side({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .bridge_rst_n(hb_ckgen__por_stream[0:0]),
    .control(pgp_NE__command[2421:680]),
    .vmr_cmd(pgp_NE__command[559:500]),
    .vmw_cmd(pgp_NE__command[283:206]),
    .rf_bword(sucore_NE__rf_bword[127:0]),
    .rf_bcmd(sucore_NE__rf_bcmd[35:0]),
    .rf_dsec(sucore_NE__rf_dsec[255:0]),
    .red_sel({pgp_NE__command[73:70], pgp_NE__command[7:0]}),
    .slice_x(su_NE1__slice_x[31:0]),
    .inj_rd(cic_NE__inj_rd_o[1:0]),
    .inj_addr(cic_NE__inj_addr_o[159:0]),
    .inj_q(su_NE1__inj_q[1023:0]),
    .dw_v(cxdl_NE1_q__dw_v[1:0]),
    .dw_row(cxdl_NE1_q__dw_row[17:0]),
    .dw_d(cxdl_NE1_q__dw_d[1023:0]),
    .fault(su_NE1__fault[0:0]),
    .lg_rq(su_NE1__lg_rq[33:0]),
    .lg_wq(su_NE1__lg_wq[561:0]),
    .lg_rr({vmb_NE3__rr0[256:0], vmb_NE2__rr0[256:0]}),
    .lg_w_done({vmb_NE3__wq_done0[0:0], vmb_NE2__wq_done0[0:0]}),
    .lg_read(calendar_NE__lg_local_read[3:2]),
    .lg_write(calendar_NE__lg_local_write[3:2]),
    .far_rq(sfu_NE1__near_rq[33:0]),
    .far_wq(sfu_NE1__near_wq[561:0]),
    .far_rr(su_NE1__far_rr[513:0]),
    .far_w_done(su_NE1__far_w_done[1:0]),
    .lg_fault(su_NE1__lg_fault[0:0]),
    .tree_cmd(pgp_NE__command[2445:2434]),
    .tree_o(su_NE1__tree_o[66:0])
  );
  ot_hbm_su_static_pgslice_lg #(.QID(3), .G(2), .READ_RETURN(19), .WRITE_RETURN(16), .FETCH_EXTRA_EDGES(2), .MLAT(4), .ALAT(4), .LEAF(1), .MUT(0), .MULTIRATE(0), .COLLPORT(1), .RF_LOCAL(1), .PRETREE(1), .RSYNC(0)) su_NE2 (
    .pg_clk(hb_ckgen__pll_stream[0:0]),
    .clk_lane({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .clk_insert({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .rst_lane_n({hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0]}),
    .clk_bcast({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .rst_bcast_n({hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0]}),
    .clk_bank({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .clk_bank_macro({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .clk_ctl(hb_ckgen__pll_stream[0:0]),
    .clk_side({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .bridge_rst_n(hb_ckgen__por_stream[0:0]),
    .control(pgp_NE__command[2421:680]),
    .vmr_cmd(pgp_NE__command[619:560]),
    .vmw_cmd(pgp_NE__command[361:284]),
    .rf_bword(sucore_NE__rf_bword[127:0]),
    .rf_bcmd(sucore_NE__rf_bcmd[35:0]),
    .rf_dsec(sucore_NE__rf_dsec[255:0]),
    .red_sel({pgp_NE__command[73:70], pgp_NE__command[7:0]}),
    .slice_x(su_NE2__slice_x[31:0]),
    .inj_rd(cic_NE__inj_rd_o[1:0]),
    .inj_addr(cic_NE__inj_addr_o[159:0]),
    .inj_q(su_NE2__inj_q[1023:0]),
    .dw_v(cxdl_NE2_q__dw_v[1:0]),
    .dw_row(cxdl_NE2_q__dw_row[17:0]),
    .dw_d(cxdl_NE2_q__dw_d[1023:0]),
    .fault(su_NE2__fault[0:0]),
    .lg_rq(su_NE2__lg_rq[33:0]),
    .lg_wq(su_NE2__lg_wq[561:0]),
    .lg_rr({vmb_NE5__rr0[256:0], vmb_NE4__rr0[256:0]}),
    .lg_w_done({vmb_NE5__wq_done0[0:0], vmb_NE4__wq_done0[0:0]}),
    .lg_read(calendar_NE__lg_local_read[5:4]),
    .lg_write(calendar_NE__lg_local_write[5:4]),
    .far_rq(sfu_NE2__near_rq[33:0]),
    .far_wq(sfu_NE2__near_wq[561:0]),
    .far_rr(su_NE2__far_rr[513:0]),
    .far_w_done(su_NE2__far_w_done[1:0]),
    .lg_fault(su_NE2__lg_fault[0:0]),
    .tree_cmd(pgp_NE__command[2457:2446]),
    .tree_o(su_NE2__tree_o[66:0])
  );
  ot_hbm_su_static_pgslice_lg #(.QID(3), .G(3), .READ_RETURN(15), .WRITE_RETURN(12), .FETCH_EXTRA_EDGES(2), .MLAT(4), .ALAT(4), .LEAF(1), .MUT(0), .MULTIRATE(0), .COLLPORT(1), .RF_LOCAL(1), .PRETREE(1), .RSYNC(0)) su_NE3 (
    .pg_clk(hb_ckgen__pll_stream[0:0]),
    .clk_lane({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .clk_insert({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .rst_lane_n({hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0]}),
    .clk_bcast({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .rst_bcast_n({hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0]}),
    .clk_bank({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .clk_bank_macro({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .clk_ctl(hb_ckgen__pll_stream[0:0]),
    .clk_side({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .bridge_rst_n(hb_ckgen__por_stream[0:0]),
    .control(pgp_NE__command[2421:680]),
    .vmr_cmd(pgp_NE__command[679:620]),
    .vmw_cmd(pgp_NE__command[439:362]),
    .rf_bword(sucore_NE__rf_bword[127:0]),
    .rf_bcmd(sucore_NE__rf_bcmd[35:0]),
    .rf_dsec(sucore_NE__rf_dsec[255:0]),
    .red_sel({pgp_NE__command[73:70], pgp_NE__command[7:0]}),
    .slice_x(su_NE3__slice_x[31:0]),
    .inj_rd(cic_NE__inj_rd_o[1:0]),
    .inj_addr(cic_NE__inj_addr_o[159:0]),
    .inj_q(su_NE3__inj_q[1023:0]),
    .dw_v(cxdl_NE3_q__dw_v[1:0]),
    .dw_row(cxdl_NE3_q__dw_row[17:0]),
    .dw_d(cxdl_NE3_q__dw_d[1023:0]),
    .fault(su_NE3__fault[0:0]),
    .lg_rq(su_NE3__lg_rq[33:0]),
    .lg_wq(su_NE3__lg_wq[561:0]),
    .lg_rr({vmb_NE7__rr0[256:0], vmb_NE6__rr0[256:0]}),
    .lg_w_done({vmb_NE7__wq_done0[0:0], vmb_NE6__wq_done0[0:0]}),
    .lg_read(calendar_NE__lg_local_read[7:6]),
    .lg_write(calendar_NE__lg_local_write[7:6]),
    .far_rq(sfu_NE3__near_rq[33:0]),
    .far_wq(sfu_NE3__near_wq[561:0]),
    .far_rr(su_NE3__far_rr[513:0]),
    .far_w_done(su_NE3__far_w_done[1:0]),
    .lg_fault(su_NE3__lg_fault[0:0]),
    .tree_cmd(pgp_NE__command[2469:2458]),
    .tree_o(su_NE3__tree_o[66:0])
  );
  ot_hbm_su_static_pgslice_lg #(.QID(2), .G(0), .READ_RETURN(25), .WRITE_RETURN(22), .FETCH_EXTRA_EDGES(2), .MLAT(4), .ALAT(4), .LEAF(1), .MUT(0), .MULTIRATE(0), .COLLPORT(1), .RF_LOCAL(1), .PRETREE(1), .RSYNC(0)) su_NW0 (
    .pg_clk(hb_ckgen__pll_stream[0:0]),
    .clk_lane({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .clk_insert({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .rst_lane_n({hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0]}),
    .clk_bcast({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .rst_bcast_n({hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0]}),
    .clk_bank({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .clk_bank_macro({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .clk_ctl(hb_ckgen__pll_stream[0:0]),
    .clk_side({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .bridge_rst_n(hb_ckgen__por_stream[0:0]),
    .control(pgp_NW__command[2421:680]),
    .vmr_cmd(pgp_NW__command[499:440]),
    .vmw_cmd(pgp_NW__command[205:128]),
    .rf_bword(sucore_NW__rf_bword[127:0]),
    .rf_bcmd(sucore_NW__rf_bcmd[35:0]),
    .rf_dsec(sucore_NW__rf_dsec[255:0]),
    .red_sel({pgp_NW__command[73:70], pgp_NW__command[7:0]}),
    .slice_x(su_NW0__slice_x[31:0]),
    .inj_rd(cic_NW__inj_rd_o[1:0]),
    .inj_addr(cic_NW__inj_addr_o[159:0]),
    .inj_q(su_NW0__inj_q[1023:0]),
    .dw_v(cxdl_NW0_q__dw_v[1:0]),
    .dw_row(cxdl_NW0_q__dw_row[17:0]),
    .dw_d(cxdl_NW0_q__dw_d[1023:0]),
    .fault(su_NW0__fault[0:0]),
    .lg_rq(su_NW0__lg_rq[33:0]),
    .lg_wq(su_NW0__lg_wq[561:0]),
    .lg_rr({vmb_NW1__rr0[256:0], vmb_NW0__rr0[256:0]}),
    .lg_w_done({vmb_NW1__wq_done0[0:0], vmb_NW0__wq_done0[0:0]}),
    .lg_read(calendar_NW__lg_local_read[1:0]),
    .lg_write(calendar_NW__lg_local_write[1:0]),
    .far_rq(sfu_NW0__near_rq[33:0]),
    .far_wq(sfu_NW0__near_wq[561:0]),
    .far_rr(su_NW0__far_rr[513:0]),
    .far_w_done(su_NW0__far_w_done[1:0]),
    .lg_fault(su_NW0__lg_fault[0:0]),
    .tree_cmd(pgp_NW__command[2433:2422]),
    .tree_o(su_NW0__tree_o[66:0])
  );
  ot_hbm_su_static_pgslice_lg #(.QID(2), .G(1), .READ_RETURN(15), .WRITE_RETURN(12), .FETCH_EXTRA_EDGES(2), .MLAT(4), .ALAT(4), .LEAF(1), .MUT(0), .MULTIRATE(0), .COLLPORT(1), .RF_LOCAL(1), .PRETREE(1), .RSYNC(0)) su_NW1 (
    .pg_clk(hb_ckgen__pll_stream[0:0]),
    .clk_lane({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .clk_insert({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .rst_lane_n({hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0]}),
    .clk_bcast({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .rst_bcast_n({hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0]}),
    .clk_bank({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .clk_bank_macro({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .clk_ctl(hb_ckgen__pll_stream[0:0]),
    .clk_side({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .bridge_rst_n(hb_ckgen__por_stream[0:0]),
    .control(pgp_NW__command[2421:680]),
    .vmr_cmd(pgp_NW__command[559:500]),
    .vmw_cmd(pgp_NW__command[283:206]),
    .rf_bword(sucore_NW__rf_bword[127:0]),
    .rf_bcmd(sucore_NW__rf_bcmd[35:0]),
    .rf_dsec(sucore_NW__rf_dsec[255:0]),
    .red_sel({pgp_NW__command[73:70], pgp_NW__command[7:0]}),
    .slice_x(su_NW1__slice_x[31:0]),
    .inj_rd(cic_NW__inj_rd_o[1:0]),
    .inj_addr(cic_NW__inj_addr_o[159:0]),
    .inj_q(su_NW1__inj_q[1023:0]),
    .dw_v(cxdl_NW1_q__dw_v[1:0]),
    .dw_row(cxdl_NW1_q__dw_row[17:0]),
    .dw_d(cxdl_NW1_q__dw_d[1023:0]),
    .fault(su_NW1__fault[0:0]),
    .lg_rq(su_NW1__lg_rq[33:0]),
    .lg_wq(su_NW1__lg_wq[561:0]),
    .lg_rr({vmb_NW3__rr0[256:0], vmb_NW2__rr0[256:0]}),
    .lg_w_done({vmb_NW3__wq_done0[0:0], vmb_NW2__wq_done0[0:0]}),
    .lg_read(calendar_NW__lg_local_read[3:2]),
    .lg_write(calendar_NW__lg_local_write[3:2]),
    .far_rq(sfu_NW1__near_rq[33:0]),
    .far_wq(sfu_NW1__near_wq[561:0]),
    .far_rr(su_NW1__far_rr[513:0]),
    .far_w_done(su_NW1__far_w_done[1:0]),
    .lg_fault(su_NW1__lg_fault[0:0]),
    .tree_cmd(pgp_NW__command[2445:2434]),
    .tree_o(su_NW1__tree_o[66:0])
  );
  ot_hbm_su_static_pgslice_lg #(.QID(2), .G(2), .READ_RETURN(19), .WRITE_RETURN(16), .FETCH_EXTRA_EDGES(2), .MLAT(4), .ALAT(4), .LEAF(1), .MUT(0), .MULTIRATE(0), .COLLPORT(1), .RF_LOCAL(1), .PRETREE(1), .RSYNC(0)) su_NW2 (
    .pg_clk(hb_ckgen__pll_stream[0:0]),
    .clk_lane({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .clk_insert({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .rst_lane_n({hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0]}),
    .clk_bcast({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .rst_bcast_n({hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0]}),
    .clk_bank({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .clk_bank_macro({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .clk_ctl(hb_ckgen__pll_stream[0:0]),
    .clk_side({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .bridge_rst_n(hb_ckgen__por_stream[0:0]),
    .control(pgp_NW__command[2421:680]),
    .vmr_cmd(pgp_NW__command[619:560]),
    .vmw_cmd(pgp_NW__command[361:284]),
    .rf_bword(sucore_NW__rf_bword[127:0]),
    .rf_bcmd(sucore_NW__rf_bcmd[35:0]),
    .rf_dsec(sucore_NW__rf_dsec[255:0]),
    .red_sel({pgp_NW__command[73:70], pgp_NW__command[7:0]}),
    .slice_x(su_NW2__slice_x[31:0]),
    .inj_rd(cic_NW__inj_rd_o[1:0]),
    .inj_addr(cic_NW__inj_addr_o[159:0]),
    .inj_q(su_NW2__inj_q[1023:0]),
    .dw_v(cxdl_NW2_q__dw_v[1:0]),
    .dw_row(cxdl_NW2_q__dw_row[17:0]),
    .dw_d(cxdl_NW2_q__dw_d[1023:0]),
    .fault(su_NW2__fault[0:0]),
    .lg_rq(su_NW2__lg_rq[33:0]),
    .lg_wq(su_NW2__lg_wq[561:0]),
    .lg_rr({vmb_NW5__rr0[256:0], vmb_NW4__rr0[256:0]}),
    .lg_w_done({vmb_NW5__wq_done0[0:0], vmb_NW4__wq_done0[0:0]}),
    .lg_read(calendar_NW__lg_local_read[5:4]),
    .lg_write(calendar_NW__lg_local_write[5:4]),
    .far_rq(sfu_NW2__near_rq[33:0]),
    .far_wq(sfu_NW2__near_wq[561:0]),
    .far_rr(su_NW2__far_rr[513:0]),
    .far_w_done(su_NW2__far_w_done[1:0]),
    .lg_fault(su_NW2__lg_fault[0:0]),
    .tree_cmd(pgp_NW__command[2457:2446]),
    .tree_o(su_NW2__tree_o[66:0])
  );
  ot_hbm_su_static_pgslice_lg #(.QID(2), .G(3), .READ_RETURN(15), .WRITE_RETURN(12), .FETCH_EXTRA_EDGES(2), .MLAT(4), .ALAT(4), .LEAF(1), .MUT(0), .MULTIRATE(0), .COLLPORT(1), .RF_LOCAL(1), .PRETREE(1), .RSYNC(0)) su_NW3 (
    .pg_clk(hb_ckgen__pll_stream[0:0]),
    .clk_lane({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .clk_insert({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .rst_lane_n({hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0]}),
    .clk_bcast({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .rst_bcast_n({hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0], hb_ckgen__por_stream[0:0]}),
    .clk_bank({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .clk_bank_macro({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .clk_ctl(hb_ckgen__pll_stream[0:0]),
    .clk_side({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .bridge_rst_n(hb_ckgen__por_stream[0:0]),
    .control(pgp_NW__command[2421:680]),
    .vmr_cmd(pgp_NW__command[679:620]),
    .vmw_cmd(pgp_NW__command[439:362]),
    .rf_bword(sucore_NW__rf_bword[127:0]),
    .rf_bcmd(sucore_NW__rf_bcmd[35:0]),
    .rf_dsec(sucore_NW__rf_dsec[255:0]),
    .red_sel({pgp_NW__command[73:70], pgp_NW__command[7:0]}),
    .slice_x(su_NW3__slice_x[31:0]),
    .inj_rd(cic_NW__inj_rd_o[1:0]),
    .inj_addr(cic_NW__inj_addr_o[159:0]),
    .inj_q(su_NW3__inj_q[1023:0]),
    .dw_v(cxdl_NW3_q__dw_v[1:0]),
    .dw_row(cxdl_NW3_q__dw_row[17:0]),
    .dw_d(cxdl_NW3_q__dw_d[1023:0]),
    .fault(su_NW3__fault[0:0]),
    .lg_rq(su_NW3__lg_rq[33:0]),
    .lg_wq(su_NW3__lg_wq[561:0]),
    .lg_rr({vmb_NW7__rr0[256:0], vmb_NW6__rr0[256:0]}),
    .lg_w_done({vmb_NW7__wq_done0[0:0], vmb_NW6__wq_done0[0:0]}),
    .lg_read(calendar_NW__lg_local_read[7:6]),
    .lg_write(calendar_NW__lg_local_write[7:6]),
    .far_rq(sfu_NW3__near_rq[33:0]),
    .far_wq(sfu_NW3__near_wq[561:0]),
    .far_rr(su_NW3__far_rr[513:0]),
    .far_w_done(su_NW3__far_w_done[1:0]),
    .lg_fault(su_NW3__lg_fault[0:0]),
    .tree_cmd(pgp_NW__command[2469:2458]),
    .tree_o(su_NW3__tree_o[66:0])
  );
  ot_hbm_su_programme_root_h5 #(.PARTS(2)) su_prog (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .cfg_we(col_su__pw_we[0:0]),
    .cfg_bank(col_su__pw_addr[22:7]),
    .cfg_row(col_su__pw_addr[6:0]),
    .cfg_data(col_su__pw_data[255:0]),
    .start(col_su__start_v[0:0]),
    .length(col_su__prm[15:0]),
    .p_fault({pgp_NE__fault[0:0], pgp_NW__fault[0:0]}),
    .r_start(su_prog__r_start[0:0]),
    .r_len(su_prog__r_len[15:0]),
    .r_we(su_prog__r_we[1:0]),
    .r_bank(su_prog__r_bank[31:0]),
    .r_row(su_prog__r_row[6:0]),
    .r_data(su_prog__r_data[255:0]),
    .fault(su_prog__fault[0:0])
  );
  ot_hbm_su_static_qcore_r13_w2 #(.MUT(0), .COLLPORT(1), .RF_LOCAL(1), .PRETREE(1), .ROW_EN(2), .WDEC(1)) sucore_NE (
    .clk_ctl(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .rf_rd_cmd(pgp_NE__command[127:74]),
    .red_cmd(pgp_NE__command[73:0]),
    .rf_drain_cmd(pgp_NE__command[166:165]),
    .slice_x({su_NE3__slice_x[31:0], su_NE2__slice_x[31:0], su_NE1__slice_x[31:0], su_NE0__slice_x[31:0]}),
    .rf_wv(stl_NE__rf_wv[1:0]),
    .rf_wa(stl_NE__rf_wa[15:0]),
    .rf_wd(stl_NE__rf_wd[63:0]),
    .rf_bword(sucore_NE__rf_bword[127:0]),
    .rf_bcmd(sucore_NE__rf_bcmd[35:0]),
    .rf_dsec(sucore_NE__rf_dsec[255:0]),
    .red_sv(sucore_NE__red_sv[0:0]),
    .red_tag(sucore_NE__red_tag[31:0]),
    .red_x(sucore_NE__red_x[31:0]),
    .red_rf_v(sucore_NE__red_rf_v[0:0]),
    .rr_wv(cxrc_NE_q__rr_wv[0:0]),
    .rr_wa(cxrc_NE_q__rr_wa[4:0]),
    .rr_wd(cxrc_NE_q__rr_wd[255:0]),
    .sfu_x(cxrc_NE_q__sfu_x[31:0]),
    .fault(sucore_NE__fault[0:0]),
    .slice_t({su_NE3__tree_o[66:0], su_NE2__tree_o[66:0], su_NE1__tree_o[66:0], su_NE0__tree_o[66:0]})
  );
  ot_hbm_su_static_qcore_r13_w2 #(.MUT(0), .COLLPORT(1), .RF_LOCAL(1), .PRETREE(1), .ROW_EN(2), .WDEC(1)) sucore_NW (
    .clk_ctl(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .rf_rd_cmd(pgp_NW__command[127:74]),
    .red_cmd(pgp_NW__command[73:0]),
    .rf_drain_cmd(pgp_NW__command[166:165]),
    .slice_x({su_NW3__slice_x[31:0], su_NW2__slice_x[31:0], su_NW1__slice_x[31:0], su_NW0__slice_x[31:0]}),
    .rf_wv(stl_NW__rf_wv[1:0]),
    .rf_wa(stl_NW__rf_wa[15:0]),
    .rf_wd(stl_NW__rf_wd[63:0]),
    .rf_bword(sucore_NW__rf_bword[127:0]),
    .rf_bcmd(sucore_NW__rf_bcmd[35:0]),
    .rf_dsec(sucore_NW__rf_dsec[255:0]),
    .red_sv(sucore_NW__red_sv[0:0]),
    .red_tag(sucore_NW__red_tag[31:0]),
    .red_x(sucore_NW__red_x[31:0]),
    .red_rf_v(sucore_NW__red_rf_v[0:0]),
    .rr_wv(cxrc_NW_q__rr_wv[0:0]),
    .rr_wa(cxrc_NW_q__rr_wa[4:0]),
    .rr_wd(cxrc_NW_q__rr_wd[255:0]),
    .sfu_x(cxrc_NW_q__sfu_x[31:0]),
    .fault(sucore_NW__fault[0:0]),
    .slice_t({su_NW3__tree_o[66:0], su_NW2__tree_o[66:0], su_NW1__tree_o[66:0], su_NW0__tree_o[66:0]})
  );
  ot_hbm_svc_sm_group_rel_id_rc #(.LBANKS(4), .NID(6), .IDW(9), .PAW(11), .PREL(1), .DD(256), .ID_COHORT(1), .XSLOT(1), .OPEN_IL(1), .RQD(39)) svg_NW0 (
    .id_stack(2'b10),
    .id_sm(3'b000),
    .stream_clk(hb_ckgen__pll_stream[0:0]),
    .stream_rst_n(hb_ckgen__por_stream[0:0]),
    .hbm_clk(hb_ckgen__pll_stream[0:0]),
    .hbm_rst_n(hb_ckgen__por_stream[0:0]),
    .stream_bank_clk({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .hbm_fifo_clk({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .hbm_pc_clk({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .program_cfg_we(cp_svg_NW0__a_we[0:0]),
    .program_cfg_addr(cp_svg_NW0__a_addr[10:0]),
    .program_cfg_data(cp_svg_NW0__a_data[255:0]),
    .desc_we(cp_svg_NW0__b_we[0:0]),
    .desc_addr(cp_svg_NW0__b_addr[7:0]),
    .desc_data(cp_svg_NW0__b_data[255:0]),
    .run_v(cp_svg_NW0__run_v[0:0]),
    .run_base(cp_svg_NW0__run_base[7:0]),
    .run_count(cp_svg_NW0__run_count[8:0]),
    .run_layer(cp_svg_NW0__run_arg[7:0]),
    .ids_v(hb_router_ids__ids_v[0:0]),
    .ids_layer(hb_router_ids__ids_layer[7:0]),
    .ids(hb_router_ids__ids[53:0]),
    .ids_cohort(hb_router_ids__ids_cohort[15:0]),
    .running(svg_NW0__running[0:0]),
    .run_done(svg_NW0__run_done[0:0]),
    .program_active(svg_NW0__program_active[0:0]),
    .fault(svg_NW0__fault[0:0]),
    .sm_packet(svg_NW0__sm_packet[1098:0]),
    .sm_command(svg_NW0__sm_command[82:0]),
    .k_v(svg_NW0__k_v[3:0]),
    .k_rdy(vmks_NW0__g_k_rdy[3:0]),
    .k_addr(svg_NW0__k_addr[119:0]),
    .k_len(svg_NW0__k_len[15:0]),
    .k_tag(svg_NW0__k_tag[67:0]),
    .k_we(svg_NW0__k_we[3:0]),
    .k_wdata(svg_NW0__k_wdata[1023:0]),
    .k_wstrb(svg_NW0__k_wstrb[127:0]),
    .k_wr_done(vmks_NW0__g_k_wr_done[3:0]),
    .kr_v(vmks_NW0__g_kr_v[3:0]),
    .kr_rdy(svg_NW0__kr_rdy[3:0]),
    .kr_tag(vmks_NW0__g_kr_tag[67:0]),
    .kr_beat(vmks_NW0__g_kr_beat[15:0]),
    .kr_data(vmks_NW0__g_kr_data[1023:0]),
    .sm_request(sm_NW0__request[42:0])
  );
  ot_hbm_svc_sm_group_rel_id_rc #(.LBANKS(4), .NID(6), .IDW(9), .PAW(11), .PREL(1), .DD(256), .ID_COHORT(1), .XSLOT(1), .OPEN_IL(1), .RQD(19)) svg_NW1 (
    .id_stack(2'b10),
    .id_sm(3'b001),
    .stream_clk(hb_ckgen__pll_stream[0:0]),
    .stream_rst_n(hb_ckgen__por_stream[0:0]),
    .hbm_clk(hb_ckgen__pll_stream[0:0]),
    .hbm_rst_n(hb_ckgen__por_stream[0:0]),
    .stream_bank_clk({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .hbm_fifo_clk({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .hbm_pc_clk({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .program_cfg_we(cp_svg_NW1__a_we[0:0]),
    .program_cfg_addr(cp_svg_NW1__a_addr[10:0]),
    .program_cfg_data(cp_svg_NW1__a_data[255:0]),
    .desc_we(cp_svg_NW1__b_we[0:0]),
    .desc_addr(cp_svg_NW1__b_addr[7:0]),
    .desc_data(cp_svg_NW1__b_data[255:0]),
    .run_v(cp_svg_NW1__run_v[0:0]),
    .run_base(cp_svg_NW1__run_base[7:0]),
    .run_count(cp_svg_NW1__run_count[8:0]),
    .run_layer(cp_svg_NW1__run_arg[7:0]),
    .ids_v(hb_router_ids__ids_v[0:0]),
    .ids_layer(hb_router_ids__ids_layer[7:0]),
    .ids(hb_router_ids__ids[53:0]),
    .ids_cohort(hb_router_ids__ids_cohort[15:0]),
    .running(svg_NW1__running[0:0]),
    .run_done(svg_NW1__run_done[0:0]),
    .program_active(svg_NW1__program_active[0:0]),
    .fault(svg_NW1__fault[0:0]),
    .sm_packet(svg_NW1__sm_packet[1098:0]),
    .sm_command(svg_NW1__sm_command[82:0]),
    .k_v(svg_NW1__k_v[3:0]),
    .k_rdy(vmks_NW1__g_k_rdy[3:0]),
    .k_addr(svg_NW1__k_addr[119:0]),
    .k_len(svg_NW1__k_len[15:0]),
    .k_tag(svg_NW1__k_tag[67:0]),
    .k_we(svg_NW1__k_we[3:0]),
    .k_wdata(svg_NW1__k_wdata[1023:0]),
    .k_wstrb(svg_NW1__k_wstrb[127:0]),
    .k_wr_done(vmks_NW1__g_k_wr_done[3:0]),
    .kr_v(vmks_NW1__g_kr_v[3:0]),
    .kr_rdy(svg_NW1__kr_rdy[3:0]),
    .kr_tag(vmks_NW1__g_kr_tag[67:0]),
    .kr_beat(vmks_NW1__g_kr_beat[15:0]),
    .kr_data(vmks_NW1__g_kr_data[1023:0]),
    .sm_request(sm_NW1__request[42:0])
  );
  ot_hbm_svc_sm_group_rel_id_rc #(.LBANKS(4), .NID(6), .IDW(9), .PAW(11), .PREL(1), .DD(256), .ID_COHORT(1), .XSLOT(1), .OPEN_IL(1), .RQD(22)) svg_NW2 (
    .id_stack(2'b10),
    .id_sm(3'b010),
    .stream_clk(hb_ckgen__pll_stream[0:0]),
    .stream_rst_n(hb_ckgen__por_stream[0:0]),
    .hbm_clk(hb_ckgen__pll_stream[0:0]),
    .hbm_rst_n(hb_ckgen__por_stream[0:0]),
    .stream_bank_clk({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .hbm_fifo_clk({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .hbm_pc_clk({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .program_cfg_we(cp_svg_NW2__a_we[0:0]),
    .program_cfg_addr(cp_svg_NW2__a_addr[10:0]),
    .program_cfg_data(cp_svg_NW2__a_data[255:0]),
    .desc_we(cp_svg_NW2__b_we[0:0]),
    .desc_addr(cp_svg_NW2__b_addr[7:0]),
    .desc_data(cp_svg_NW2__b_data[255:0]),
    .run_v(cp_svg_NW2__run_v[0:0]),
    .run_base(cp_svg_NW2__run_base[7:0]),
    .run_count(cp_svg_NW2__run_count[8:0]),
    .run_layer(cp_svg_NW2__run_arg[7:0]),
    .ids_v(hb_router_ids__ids_v[0:0]),
    .ids_layer(hb_router_ids__ids_layer[7:0]),
    .ids(hb_router_ids__ids[53:0]),
    .ids_cohort(hb_router_ids__ids_cohort[15:0]),
    .running(svg_NW2__running[0:0]),
    .run_done(svg_NW2__run_done[0:0]),
    .program_active(svg_NW2__program_active[0:0]),
    .fault(svg_NW2__fault[0:0]),
    .sm_packet(svg_NW2__sm_packet[1098:0]),
    .sm_command(svg_NW2__sm_command[82:0]),
    .k_v(svg_NW2__k_v[3:0]),
    .k_rdy(vmks_NW2__g_k_rdy[3:0]),
    .k_addr(svg_NW2__k_addr[119:0]),
    .k_len(svg_NW2__k_len[15:0]),
    .k_tag(svg_NW2__k_tag[67:0]),
    .k_we(svg_NW2__k_we[3:0]),
    .k_wdata(svg_NW2__k_wdata[1023:0]),
    .k_wstrb(svg_NW2__k_wstrb[127:0]),
    .k_wr_done(vmks_NW2__g_k_wr_done[3:0]),
    .kr_v(vmks_NW2__g_kr_v[3:0]),
    .kr_rdy(svg_NW2__kr_rdy[3:0]),
    .kr_tag(vmks_NW2__g_kr_tag[67:0]),
    .kr_beat(vmks_NW2__g_kr_beat[15:0]),
    .kr_data(vmks_NW2__g_kr_data[1023:0]),
    .sm_request(sm_NW2__request[42:0])
  );
  ot_hbm_svc_sm_group_rel_id_rc #(.LBANKS(4), .NID(6), .IDW(9), .PAW(11), .PREL(1), .DD(256), .ID_COHORT(1), .XSLOT(1), .OPEN_IL(1), .RQD(19)) svg_NW3 (
    .id_stack(2'b10),
    .id_sm(3'b011),
    .stream_clk(hb_ckgen__pll_stream[0:0]),
    .stream_rst_n(hb_ckgen__por_stream[0:0]),
    .hbm_clk(hb_ckgen__pll_stream[0:0]),
    .hbm_rst_n(hb_ckgen__por_stream[0:0]),
    .stream_bank_clk({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .hbm_fifo_clk({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .hbm_pc_clk({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .program_cfg_we(cp_svg_NW3__a_we[0:0]),
    .program_cfg_addr(cp_svg_NW3__a_addr[10:0]),
    .program_cfg_data(cp_svg_NW3__a_data[255:0]),
    .desc_we(cp_svg_NW3__b_we[0:0]),
    .desc_addr(cp_svg_NW3__b_addr[7:0]),
    .desc_data(cp_svg_NW3__b_data[255:0]),
    .run_v(cp_svg_NW3__run_v[0:0]),
    .run_base(cp_svg_NW3__run_base[7:0]),
    .run_count(cp_svg_NW3__run_count[8:0]),
    .run_layer(cp_svg_NW3__run_arg[7:0]),
    .ids_v(hb_router_ids__ids_v[0:0]),
    .ids_layer(hb_router_ids__ids_layer[7:0]),
    .ids(hb_router_ids__ids[53:0]),
    .ids_cohort(hb_router_ids__ids_cohort[15:0]),
    .running(svg_NW3__running[0:0]),
    .run_done(svg_NW3__run_done[0:0]),
    .program_active(svg_NW3__program_active[0:0]),
    .fault(svg_NW3__fault[0:0]),
    .sm_packet(svg_NW3__sm_packet[1098:0]),
    .sm_command(svg_NW3__sm_command[82:0]),
    .k_v(svg_NW3__k_v[3:0]),
    .k_rdy(vmks_NW3__g_k_rdy[3:0]),
    .k_addr(svg_NW3__k_addr[119:0]),
    .k_len(svg_NW3__k_len[15:0]),
    .k_tag(svg_NW3__k_tag[67:0]),
    .k_we(svg_NW3__k_we[3:0]),
    .k_wdata(svg_NW3__k_wdata[1023:0]),
    .k_wstrb(svg_NW3__k_wstrb[127:0]),
    .k_wr_done(vmks_NW3__g_k_wr_done[3:0]),
    .kr_v(vmks_NW3__g_kr_v[3:0]),
    .kr_rdy(svg_NW3__kr_rdy[3:0]),
    .kr_tag(vmks_NW3__g_kr_tag[67:0]),
    .kr_beat(vmks_NW3__g_kr_beat[15:0]),
    .kr_data(vmks_NW3__g_kr_data[1023:0]),
    .sm_request(sm_NW3__request[42:0])
  );
  ot_hbm_svc_sm_group_rel_id_rc #(.LBANKS(4), .NID(6), .IDW(9), .PAW(11), .PREL(1), .DD(256), .ID_COHORT(1), .XSLOT(1), .OPEN_IL(1), .RQD(39)) svg_NW4 (
    .id_stack(2'b10),
    .id_sm(3'b100),
    .stream_clk(hb_ckgen__pll_stream[0:0]),
    .stream_rst_n(hb_ckgen__por_stream[0:0]),
    .hbm_clk(hb_ckgen__pll_stream[0:0]),
    .hbm_rst_n(hb_ckgen__por_stream[0:0]),
    .stream_bank_clk({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .hbm_fifo_clk({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .hbm_pc_clk({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .program_cfg_we(cp_svg_NW4__a_we[0:0]),
    .program_cfg_addr(cp_svg_NW4__a_addr[10:0]),
    .program_cfg_data(cp_svg_NW4__a_data[255:0]),
    .desc_we(cp_svg_NW4__b_we[0:0]),
    .desc_addr(cp_svg_NW4__b_addr[7:0]),
    .desc_data(cp_svg_NW4__b_data[255:0]),
    .run_v(cp_svg_NW4__run_v[0:0]),
    .run_base(cp_svg_NW4__run_base[7:0]),
    .run_count(cp_svg_NW4__run_count[8:0]),
    .run_layer(cp_svg_NW4__run_arg[7:0]),
    .ids_v(hb_router_ids__ids_v[0:0]),
    .ids_layer(hb_router_ids__ids_layer[7:0]),
    .ids(hb_router_ids__ids[53:0]),
    .ids_cohort(hb_router_ids__ids_cohort[15:0]),
    .running(svg_NW4__running[0:0]),
    .run_done(svg_NW4__run_done[0:0]),
    .program_active(svg_NW4__program_active[0:0]),
    .fault(svg_NW4__fault[0:0]),
    .sm_packet(svg_NW4__sm_packet[1098:0]),
    .sm_command(svg_NW4__sm_command[82:0]),
    .k_v(svg_NW4__k_v[3:0]),
    .k_rdy(vmks_NW4__g_k_rdy[3:0]),
    .k_addr(svg_NW4__k_addr[119:0]),
    .k_len(svg_NW4__k_len[15:0]),
    .k_tag(svg_NW4__k_tag[67:0]),
    .k_we(svg_NW4__k_we[3:0]),
    .k_wdata(svg_NW4__k_wdata[1023:0]),
    .k_wstrb(svg_NW4__k_wstrb[127:0]),
    .k_wr_done(vmks_NW4__g_k_wr_done[3:0]),
    .kr_v(vmks_NW4__g_kr_v[3:0]),
    .kr_rdy(svg_NW4__kr_rdy[3:0]),
    .kr_tag(vmks_NW4__g_kr_tag[67:0]),
    .kr_beat(vmks_NW4__g_kr_beat[15:0]),
    .kr_data(vmks_NW4__g_kr_data[1023:0]),
    .sm_request(sm_NW4__request[42:0])
  );
  ot_hbm_svc_sm_group_rel_id_rc #(.LBANKS(4), .NID(6), .IDW(9), .PAW(11), .PREL(1), .DD(256), .ID_COHORT(1), .XSLOT(1), .OPEN_IL(1), .RQD(19)) svg_NW5 (
    .id_stack(2'b10),
    .id_sm(3'b101),
    .stream_clk(hb_ckgen__pll_stream[0:0]),
    .stream_rst_n(hb_ckgen__por_stream[0:0]),
    .hbm_clk(hb_ckgen__pll_stream[0:0]),
    .hbm_rst_n(hb_ckgen__por_stream[0:0]),
    .stream_bank_clk({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .hbm_fifo_clk({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .hbm_pc_clk({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .program_cfg_we(cp_svg_NW5__a_we[0:0]),
    .program_cfg_addr(cp_svg_NW5__a_addr[10:0]),
    .program_cfg_data(cp_svg_NW5__a_data[255:0]),
    .desc_we(cp_svg_NW5__b_we[0:0]),
    .desc_addr(cp_svg_NW5__b_addr[7:0]),
    .desc_data(cp_svg_NW5__b_data[255:0]),
    .run_v(cp_svg_NW5__run_v[0:0]),
    .run_base(cp_svg_NW5__run_base[7:0]),
    .run_count(cp_svg_NW5__run_count[8:0]),
    .run_layer(cp_svg_NW5__run_arg[7:0]),
    .ids_v(hb_router_ids__ids_v[0:0]),
    .ids_layer(hb_router_ids__ids_layer[7:0]),
    .ids(hb_router_ids__ids[53:0]),
    .ids_cohort(hb_router_ids__ids_cohort[15:0]),
    .running(svg_NW5__running[0:0]),
    .run_done(svg_NW5__run_done[0:0]),
    .program_active(svg_NW5__program_active[0:0]),
    .fault(svg_NW5__fault[0:0]),
    .sm_packet(svg_NW5__sm_packet[1098:0]),
    .sm_command(svg_NW5__sm_command[82:0]),
    .k_v(svg_NW5__k_v[3:0]),
    .k_rdy(vmks_NW5__g_k_rdy[3:0]),
    .k_addr(svg_NW5__k_addr[119:0]),
    .k_len(svg_NW5__k_len[15:0]),
    .k_tag(svg_NW5__k_tag[67:0]),
    .k_we(svg_NW5__k_we[3:0]),
    .k_wdata(svg_NW5__k_wdata[1023:0]),
    .k_wstrb(svg_NW5__k_wstrb[127:0]),
    .k_wr_done(vmks_NW5__g_k_wr_done[3:0]),
    .kr_v(vmks_NW5__g_kr_v[3:0]),
    .kr_rdy(svg_NW5__kr_rdy[3:0]),
    .kr_tag(vmks_NW5__g_kr_tag[67:0]),
    .kr_beat(vmks_NW5__g_kr_beat[15:0]),
    .kr_data(vmks_NW5__g_kr_data[1023:0]),
    .sm_request(sm_NW5__request[42:0])
  );
  ot_hbm_svc_sm_group_rel_id_rc #(.LBANKS(4), .NID(6), .IDW(9), .PAW(11), .PREL(1), .DD(256), .ID_COHORT(1), .XSLOT(1), .OPEN_IL(1), .RQD(22)) svg_NW6 (
    .id_stack(2'b10),
    .id_sm(3'b110),
    .stream_clk(hb_ckgen__pll_stream[0:0]),
    .stream_rst_n(hb_ckgen__por_stream[0:0]),
    .hbm_clk(hb_ckgen__pll_stream[0:0]),
    .hbm_rst_n(hb_ckgen__por_stream[0:0]),
    .stream_bank_clk({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .hbm_fifo_clk({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .hbm_pc_clk({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .program_cfg_we(cp_svg_NW6__a_we[0:0]),
    .program_cfg_addr(cp_svg_NW6__a_addr[10:0]),
    .program_cfg_data(cp_svg_NW6__a_data[255:0]),
    .desc_we(cp_svg_NW6__b_we[0:0]),
    .desc_addr(cp_svg_NW6__b_addr[7:0]),
    .desc_data(cp_svg_NW6__b_data[255:0]),
    .run_v(cp_svg_NW6__run_v[0:0]),
    .run_base(cp_svg_NW6__run_base[7:0]),
    .run_count(cp_svg_NW6__run_count[8:0]),
    .run_layer(cp_svg_NW6__run_arg[7:0]),
    .ids_v(hb_router_ids__ids_v[0:0]),
    .ids_layer(hb_router_ids__ids_layer[7:0]),
    .ids(hb_router_ids__ids[53:0]),
    .ids_cohort(hb_router_ids__ids_cohort[15:0]),
    .running(svg_NW6__running[0:0]),
    .run_done(svg_NW6__run_done[0:0]),
    .program_active(svg_NW6__program_active[0:0]),
    .fault(svg_NW6__fault[0:0]),
    .sm_packet(svg_NW6__sm_packet[1098:0]),
    .sm_command(svg_NW6__sm_command[82:0]),
    .k_v(svg_NW6__k_v[3:0]),
    .k_rdy(vmks_NW6__g_k_rdy[3:0]),
    .k_addr(svg_NW6__k_addr[119:0]),
    .k_len(svg_NW6__k_len[15:0]),
    .k_tag(svg_NW6__k_tag[67:0]),
    .k_we(svg_NW6__k_we[3:0]),
    .k_wdata(svg_NW6__k_wdata[1023:0]),
    .k_wstrb(svg_NW6__k_wstrb[127:0]),
    .k_wr_done(vmks_NW6__g_k_wr_done[3:0]),
    .kr_v(vmks_NW6__g_kr_v[3:0]),
    .kr_rdy(svg_NW6__kr_rdy[3:0]),
    .kr_tag(vmks_NW6__g_kr_tag[67:0]),
    .kr_beat(vmks_NW6__g_kr_beat[15:0]),
    .kr_data(vmks_NW6__g_kr_data[1023:0]),
    .sm_request(sm_NW6__request[42:0])
  );
  ot_hbm_svc_sm_group_rel_id_rc #(.LBANKS(4), .NID(6), .IDW(9), .PAW(11), .PREL(1), .DD(256), .ID_COHORT(1), .XSLOT(1), .OPEN_IL(1), .RQD(19)) svg_NW7 (
    .id_stack(2'b10),
    .id_sm(3'b111),
    .stream_clk(hb_ckgen__pll_stream[0:0]),
    .stream_rst_n(hb_ckgen__por_stream[0:0]),
    .hbm_clk(hb_ckgen__pll_stream[0:0]),
    .hbm_rst_n(hb_ckgen__por_stream[0:0]),
    .stream_bank_clk({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .hbm_fifo_clk({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .hbm_pc_clk({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .program_cfg_we(cp_svg_NW7__a_we[0:0]),
    .program_cfg_addr(cp_svg_NW7__a_addr[10:0]),
    .program_cfg_data(cp_svg_NW7__a_data[255:0]),
    .desc_we(cp_svg_NW7__b_we[0:0]),
    .desc_addr(cp_svg_NW7__b_addr[7:0]),
    .desc_data(cp_svg_NW7__b_data[255:0]),
    .run_v(cp_svg_NW7__run_v[0:0]),
    .run_base(cp_svg_NW7__run_base[7:0]),
    .run_count(cp_svg_NW7__run_count[8:0]),
    .run_layer(cp_svg_NW7__run_arg[7:0]),
    .ids_v(hb_router_ids__ids_v[0:0]),
    .ids_layer(hb_router_ids__ids_layer[7:0]),
    .ids(hb_router_ids__ids[53:0]),
    .ids_cohort(hb_router_ids__ids_cohort[15:0]),
    .running(svg_NW7__running[0:0]),
    .run_done(svg_NW7__run_done[0:0]),
    .program_active(svg_NW7__program_active[0:0]),
    .fault(svg_NW7__fault[0:0]),
    .sm_packet(svg_NW7__sm_packet[1098:0]),
    .sm_command(svg_NW7__sm_command[82:0]),
    .k_v(svg_NW7__k_v[3:0]),
    .k_rdy(vmks_NW7__g_k_rdy[3:0]),
    .k_addr(svg_NW7__k_addr[119:0]),
    .k_len(svg_NW7__k_len[15:0]),
    .k_tag(svg_NW7__k_tag[67:0]),
    .k_we(svg_NW7__k_we[3:0]),
    .k_wdata(svg_NW7__k_wdata[1023:0]),
    .k_wstrb(svg_NW7__k_wstrb[127:0]),
    .k_wr_done(vmks_NW7__g_k_wr_done[3:0]),
    .kr_v(vmks_NW7__g_kr_v[3:0]),
    .kr_rdy(svg_NW7__kr_rdy[3:0]),
    .kr_tag(vmks_NW7__g_kr_tag[67:0]),
    .kr_beat(vmks_NW7__g_kr_beat[15:0]),
    .kr_data(vmks_NW7__g_kr_data[1023:0]),
    .sm_request(sm_NW7__request[42:0])
  );
  ot_hgi_coll_tkm_m_tp192 tkm_SW (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .start(hb_coll_NW__tkx_start[0:0]),
    .arg_mode(hb_coll_NW__tkx_arg_mode[0:0]),
    .tile_clk({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .buffer_clk(hb_ckgen__pll_stream[0:0]),
    .cfg_n(hb_coll_NW__tkx_cfg_n[11:0]),
    .cfg_k(hb_coll_NW__tkx_cfg_k[12:0]),
    .cfg_nout(hb_coll_NW__tkx_cfg_nout[12:0]),
    .cfg_g(hb_coll_NW__tkx_cfg_g[7:0]),
    .cfg_gbase(hb_coll_NW__tkx_cfg_gbase[7:0]),
    .cfg_pf(hb_coll_NW__tkx_cfg_pf[15:0]),
    .cfg_obase(hb_coll_NW__tkx_cfg_obase[39:0]),
    .cfg_rbase(hb_coll_NW__tkx_cfg_rbase[39:0]),
    .cfg_has_r(hb_coll_NW__tkx_cfg_has_r[0:0]),
    .del_slot(hb_coll_NW__tkx_del_slot[3:0]),
    .del_valid(hb_coll_NW__tkx_del_valid[3:0]),
    .del_flit(hb_coll_NW__tkx_del_flit[2179:0]),
    .w_v(tkm_SW__w_v[0:0]),
    .w_addr(tkm_SW__w_addr[39:0]),
    .w_mask(tkm_SW__w_mask[15:0]),
    .w_data(tkm_SW__w_data[511:0]),
    .busy(tkm_SW__busy[0:0]),
    .done(tkm_SW__done[0:0]),
    .fault(tkm_SW__fault[0:0]),
    .stat_cycles(tkm_SW__stat_cycles[31:0])
  );
  ot_hnx_fused_tnode #(.LA(6), .UW(271), .DW(173), .DELIVERED_RESET(1)) u_mu_fused_n4_ne (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__u_mu_fused_n4_ne__rst_n[0:0]),
    .dn(u_mu_fused_root__down_ne[172:0]),
    .pad_k(native_required__u_mu_fused_n4_ne__pad_k[5:0]),
    .pad_b(native_required__u_mu_fused_n4_ne__pad_b[0:0]),
    .ua(native_required__u_mu_fused_n4_ne__ua[270:0]),
    .ub(native_required__u_mu_fused_n4_ne__ub[270:0]),
    .uo(u_mu_fused_n4_ne__uo[270:0]),
    .da(u_mu_fused_n4_ne__da[172:0]),
    .db(u_mu_fused_n4_ne__db[172:0])
  );
  ot_hnx_fused_tnode #(.LA(6), .UW(271), .DW(173), .DELIVERED_RESET(1)) u_mu_fused_n4_nw (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__u_mu_fused_n4_nw__rst_n[0:0]),
    .dn(u_mu_fused_root__down_nw[172:0]),
    .pad_k(native_required__u_mu_fused_n4_nw__pad_k[5:0]),
    .pad_b(native_required__u_mu_fused_n4_nw__pad_b[0:0]),
    .ua(native_required__u_mu_fused_n4_nw__ua[270:0]),
    .ub(native_required__u_mu_fused_n4_nw__ub[270:0]),
    .uo(u_mu_fused_n4_nw__uo[270:0]),
    .da(u_mu_fused_n4_nw__da[172:0]),
    .db(u_mu_fused_n4_nw__db[172:0])
  );
  ot_hnx_fused_host_program #(.TARGET(8'd225), .DELIVERED_RESET(1)) u_mu_fused_programme (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__u_mu_fused_programme__rst_n[0:0]),
    .cfg_v(hleaf_NW__a_cfg_v[0:0]),
    .cfg_target(hleaf_NW__a_cfg_target[7:0]),
    .cfg_addr(hleaf_NW__a_cfg_addr[11:0]),
    .cfg_data(hleaf_NW__a_cfg_data[255:0]),
    .desc_v(hleaf_NW__a_desc_v[0:0]),
    .desc_base(hleaf_NW__a_desc_base[11:0]),
    .desc_limit(hleaf_NW__a_desc_limit[12:0]),
    .desc_loops(hleaf_NW__a_desc_loops[15:0]),
    .launch_v(hleaf_NW__a_launch_v[0:0]),
    .ready(u_mu_fused_programme__ready[0:0]),
    .active(u_mu_fused_programme__active[0:0]),
    .done(u_mu_fused_programme__done[0:0]),
    .fault(u_mu_fused_programme__fault[0:0]),
    .job_v(u_mu_fused_programme__job_v[0:0]),
    .job(u_mu_fused_programme__job[216:0]),
    .wsc(u_mu_fused_programme__wsc[7:0]),
    .pk5(u_mu_fused_programme__pk5[5:0]),
    .pb5(u_mu_fused_programme__pb5[0:0]),
    .root_done(u_mu_fused_root__done[0:0]),
    .root_fault(u_mu_fused_root__fault[0:0]),
    .root_busy(u_mu_fused_root__busy[0:0])
  );
  ot_hnx_fused_hub_n4ext #(.DELIVERED_RESET(1)) u_mu_fused_root (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__u_mu_fused_root__rst_n[0:0]),
    .job_v(u_mu_fused_programme__job_v[0:0]),
    .job(u_mu_fused_programme__job[216:0]),
    .wsc(u_mu_fused_programme__wsc[7:0]),
    .pk5(u_mu_fused_programme__pk5[5:0]),
    .pb5(u_mu_fused_programme__pb5[0:0]),
    .done(u_mu_fused_root__done[0:0]),
    .fault(u_mu_fused_root__fault[0:0]),
    .busy(u_mu_fused_root__busy[0:0]),
    .down_nw(u_mu_fused_root__down_nw[172:0]),
    .down_ne(u_mu_fused_root__down_ne[172:0]),
    .up_nw(u_mu_fused_n4_nw__uo[270:0]),
    .up_ne(u_mu_fused_n4_ne__uo[270:0])
  );
  ot_vms_status4_static #(.NQ(2)) vm_status4 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .quadrant_status({hb_vms_NE__vmstat[18:0], hb_vms_NW__vmstat[18:0]}),
    .vmstat(vm_status4__vmstat[18:0])
  );
  hfd_vms_bank_native_q0_faces vmb_NE0 (
    .rq0(su_NE0__lg_rq[16:0]),
    .rr0(vmb_NE0__rr0[256:0]),
    .rq1(hb_dbk_NE__rq[16:0]),
    .rr1(vmb_NE0__rr1[256:0]),
    .rq2(xl_NE_ctl__rq[16:0]),
    .rr2(vmb_NE0__rr2[256:0]),
    .rq3(hcollrs_NE__vm_rq[16:0]),
    .rr3(vmb_NE0__rr3[256:0]),
    .rq4(hb_idx__op_NE__vm_rq[16:0]),
    .rr4(vmb_NE0__rr4[256:0]),
    .wq0(su_NE0__lg_wq[280:0]),
    .wq_done0(vmb_NE0__wq_done0[0:0]),
    .wq1(smw_NE__wq_t0[280:0]),
    .wq_done1(vmb_NE0__wq_done1[0:0]),
    .bid(3'b000),
    .sid(2'b11),
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_e(hb_ckgen__pll_stream[0:0]),
    .clk_w(hb_ckgen__pll_stream[0:0]),
    .clk_macro0(hb_ckgen__pll_stream[0:0]),
    .clk_macro1(hb_ckgen__pll_stream[0:0]),
    .clk_macro2(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__vmb_NE0__rst_n[0:0]),
    .rslot_v(calendar_NE__rslot_v[0:0]),
    .rslot(calendar_NE__rslot[2:0]),
    .wslot_v(calendar_NE__wslot_v[0:0]),
    .wslot(calendar_NE__wslot[2:0]),
    .dq(vmdel_NE0__dq[280:0]),
    .dq_done(vmb_NE0__dq_done[0:0]),
    .kq(hcollks_NE_p0__vm_kq[280:0]),
    .kq_done(vmb_NE0__kq_done[0:0]),
    .xq(hb_vms_NE__bk_xq[275:0]),
    .xq_done(vmb_NE0__xq_done[0:0]),
    .xq2(hb_vms_NE__bk_xq2[275:0]),
    .xq2_done(vmb_NE0__xq2_done[0:0]),
    .eg(vmb_NE0__eg[275:0]),
    .pq(hb_vms_NE__bk_pq[284:0]),
    .pr(vmb_NE0__pr[265:0]),
    .status(vmb_NE0__status[17:0])
  );
  hfd_vms_bank_native_q0_faces vmb_NE1 (
    .rq0(su_NE0__lg_rq[33:17]),
    .rr0(vmb_NE1__rr0[256:0]),
    .rq1(hb_dbk_NE__rq[33:17]),
    .rr1(vmb_NE1__rr1[256:0]),
    .rq2(xl_NE_ctl__rq[33:17]),
    .rr2(vmb_NE1__rr2[256:0]),
    .rq3(hcollrs_NE__vm_rq[33:17]),
    .rr3(vmb_NE1__rr3[256:0]),
    .rq4(hb_idx__op_NE__vm_rq[33:17]),
    .rr4(vmb_NE1__rr4[256:0]),
    .wq0(su_NE0__lg_wq[561:281]),
    .wq_done0(vmb_NE1__wq_done0[0:0]),
    .wq1(smw_NE__wq_t1[280:0]),
    .wq_done1(vmb_NE1__wq_done1[0:0]),
    .bid(3'b001),
    .sid(2'b11),
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_e(hb_ckgen__pll_stream[0:0]),
    .clk_w(hb_ckgen__pll_stream[0:0]),
    .clk_macro0(hb_ckgen__pll_stream[0:0]),
    .clk_macro1(hb_ckgen__pll_stream[0:0]),
    .clk_macro2(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__vmb_NE1__rst_n[0:0]),
    .rslot_v(calendar_NE__rslot_v[1:1]),
    .rslot(calendar_NE__rslot[5:3]),
    .wslot_v(calendar_NE__wslot_v[1:1]),
    .wslot(calendar_NE__wslot[5:3]),
    .dq(vmdel_NE1__dq[280:0]),
    .dq_done(vmb_NE1__dq_done[0:0]),
    .kq(hcollks_NE_p0__vm_kq[561:281]),
    .kq_done(vmb_NE1__kq_done[0:0]),
    .xq(hb_vms_NE__bk_xq[551:276]),
    .xq_done(vmb_NE1__xq_done[0:0]),
    .xq2(hb_vms_NE__bk_xq2[551:276]),
    .xq2_done(vmb_NE1__xq2_done[0:0]),
    .eg(vmb_NE1__eg[275:0]),
    .pq(hb_vms_NE__bk_pq[569:285]),
    .pr(vmb_NE1__pr[265:0]),
    .status(vmb_NE1__status[17:0])
  );
  hfd_vms_bank_native_q0_faces vmb_NE2 (
    .rq0(su_NE1__lg_rq[16:0]),
    .rr0(vmb_NE2__rr0[256:0]),
    .rq1(hb_dbk_NE__rq[50:34]),
    .rr1(vmb_NE2__rr1[256:0]),
    .rq2(xl_NE_ctl__rq[50:34]),
    .rr2(vmb_NE2__rr2[256:0]),
    .rq3(hcollrs_NE__vm_rq[50:34]),
    .rr3(vmb_NE2__rr3[256:0]),
    .rq4(hb_idx__op_NE__vm_rq[50:34]),
    .rr4(vmb_NE2__rr4[256:0]),
    .wq0(su_NE1__lg_wq[280:0]),
    .wq_done0(vmb_NE2__wq_done0[0:0]),
    .wq1(smw_NE__wq_t2[280:0]),
    .wq_done1(vmb_NE2__wq_done1[0:0]),
    .bid(3'b010),
    .sid(2'b11),
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_e(hb_ckgen__pll_stream[0:0]),
    .clk_w(hb_ckgen__pll_stream[0:0]),
    .clk_macro0(hb_ckgen__pll_stream[0:0]),
    .clk_macro1(hb_ckgen__pll_stream[0:0]),
    .clk_macro2(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__vmb_NE2__rst_n[0:0]),
    .rslot_v(calendar_NE__rslot_v[2:2]),
    .rslot(calendar_NE__rslot[8:6]),
    .wslot_v(calendar_NE__wslot_v[2:2]),
    .wslot(calendar_NE__wslot[8:6]),
    .dq(vmdel_NE2__dq[280:0]),
    .dq_done(vmb_NE2__dq_done[0:0]),
    .kq(hcollks_NE_p1__vm_kq[280:0]),
    .kq_done(vmb_NE2__kq_done[0:0]),
    .xq(hb_vms_NE__bk_xq[827:552]),
    .xq_done(vmb_NE2__xq_done[0:0]),
    .xq2(hb_vms_NE__bk_xq2[827:552]),
    .xq2_done(vmb_NE2__xq2_done[0:0]),
    .eg(vmb_NE2__eg[275:0]),
    .pq(hb_vms_NE__bk_pq[854:570]),
    .pr(vmb_NE2__pr[265:0]),
    .status(vmb_NE2__status[17:0])
  );
  hfd_vms_bank_native_q0_faces vmb_NE3 (
    .rq0(su_NE1__lg_rq[33:17]),
    .rr0(vmb_NE3__rr0[256:0]),
    .rq1(hb_dbk_NE__rq[67:51]),
    .rr1(vmb_NE3__rr1[256:0]),
    .rq2(xl_NE_ctl__rq[67:51]),
    .rr2(vmb_NE3__rr2[256:0]),
    .rq3(hcollrs_NE__vm_rq[67:51]),
    .rr3(vmb_NE3__rr3[256:0]),
    .rq4(hb_idx__op_NE__vm_rq[67:51]),
    .rr4(vmb_NE3__rr4[256:0]),
    .wq0(su_NE1__lg_wq[561:281]),
    .wq_done0(vmb_NE3__wq_done0[0:0]),
    .wq1(smw_NE__wq_t3[280:0]),
    .wq_done1(vmb_NE3__wq_done1[0:0]),
    .bid(3'b011),
    .sid(2'b11),
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_e(hb_ckgen__pll_stream[0:0]),
    .clk_w(hb_ckgen__pll_stream[0:0]),
    .clk_macro0(hb_ckgen__pll_stream[0:0]),
    .clk_macro1(hb_ckgen__pll_stream[0:0]),
    .clk_macro2(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__vmb_NE3__rst_n[0:0]),
    .rslot_v(calendar_NE__rslot_v[3:3]),
    .rslot(calendar_NE__rslot[11:9]),
    .wslot_v(calendar_NE__wslot_v[3:3]),
    .wslot(calendar_NE__wslot[11:9]),
    .dq(vmdel_NE3__dq[280:0]),
    .dq_done(vmb_NE3__dq_done[0:0]),
    .kq(hcollks_NE_p1__vm_kq[561:281]),
    .kq_done(vmb_NE3__kq_done[0:0]),
    .xq(hb_vms_NE__bk_xq[1103:828]),
    .xq_done(vmb_NE3__xq_done[0:0]),
    .xq2(hb_vms_NE__bk_xq2[1103:828]),
    .xq2_done(vmb_NE3__xq2_done[0:0]),
    .eg(vmb_NE3__eg[275:0]),
    .pq(hb_vms_NE__bk_pq[1139:855]),
    .pr(vmb_NE3__pr[265:0]),
    .status(vmb_NE3__status[17:0])
  );
  hfd_vms_bank_native_q0_faces vmb_NE4 (
    .rq0(su_NE2__lg_rq[16:0]),
    .rr0(vmb_NE4__rr0[256:0]),
    .rq1(hb_dbk_NE__rq[84:68]),
    .rr1(vmb_NE4__rr1[256:0]),
    .rq2(xl_NE_ctl__rq[84:68]),
    .rr2(vmb_NE4__rr2[256:0]),
    .rq3(hcollrs_NE__vm_rq[84:68]),
    .rr3(vmb_NE4__rr3[256:0]),
    .rq4(hb_idx__op_NE__vm_rq[84:68]),
    .rr4(vmb_NE4__rr4[256:0]),
    .wq0(su_NE2__lg_wq[280:0]),
    .wq_done0(vmb_NE4__wq_done0[0:0]),
    .wq1(smw_NE__wq_s0[280:0]),
    .wq_done1(vmb_NE4__wq_done1[0:0]),
    .bid(3'b100),
    .sid(2'b11),
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_e(hb_ckgen__pll_stream[0:0]),
    .clk_w(hb_ckgen__pll_stream[0:0]),
    .clk_macro0(hb_ckgen__pll_stream[0:0]),
    .clk_macro1(hb_ckgen__pll_stream[0:0]),
    .clk_macro2(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__vmb_NE4__rst_n[0:0]),
    .rslot_v(calendar_NE__rslot_v[4:4]),
    .rslot(calendar_NE__rslot[14:12]),
    .wslot_v(calendar_NE__wslot_v[4:4]),
    .wslot(calendar_NE__wslot[14:12]),
    .dq(vmdel_NE4__dq[280:0]),
    .dq_done(vmb_NE4__dq_done[0:0]),
    .kq(hcollks_NE_p2__vm_kq[280:0]),
    .kq_done(vmb_NE4__kq_done[0:0]),
    .xq(hb_vms_NE__bk_xq[1379:1104]),
    .xq_done(vmb_NE4__xq_done[0:0]),
    .xq2(hb_vms_NE__bk_xq2[1379:1104]),
    .xq2_done(vmb_NE4__xq2_done[0:0]),
    .eg(vmb_NE4__eg[275:0]),
    .pq(hb_vms_NE__bk_pq[1424:1140]),
    .pr(vmb_NE4__pr[265:0]),
    .status(vmb_NE4__status[17:0])
  );
  hfd_vms_bank_native_q0_faces vmb_NE5 (
    .rq0(su_NE2__lg_rq[33:17]),
    .rr0(vmb_NE5__rr0[256:0]),
    .rq1(hb_dbk_NE__rq[101:85]),
    .rr1(vmb_NE5__rr1[256:0]),
    .rq2(xl_NE_ctl__rq[101:85]),
    .rr2(vmb_NE5__rr2[256:0]),
    .rq3(hcollrs_NE__vm_rq[101:85]),
    .rr3(vmb_NE5__rr3[256:0]),
    .rq4(hb_idx__op_NE__vm_rq[101:85]),
    .rr4(vmb_NE5__rr4[256:0]),
    .wq0(su_NE2__lg_wq[561:281]),
    .wq_done0(vmb_NE5__wq_done0[0:0]),
    .wq1(smw_NE__wq_s1[280:0]),
    .wq_done1(vmb_NE5__wq_done1[0:0]),
    .bid(3'b101),
    .sid(2'b11),
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_e(hb_ckgen__pll_stream[0:0]),
    .clk_w(hb_ckgen__pll_stream[0:0]),
    .clk_macro0(hb_ckgen__pll_stream[0:0]),
    .clk_macro1(hb_ckgen__pll_stream[0:0]),
    .clk_macro2(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__vmb_NE5__rst_n[0:0]),
    .rslot_v(calendar_NE__rslot_v[5:5]),
    .rslot(calendar_NE__rslot[17:15]),
    .wslot_v(calendar_NE__wslot_v[5:5]),
    .wslot(calendar_NE__wslot[17:15]),
    .dq(vmdel_NE5__dq[280:0]),
    .dq_done(vmb_NE5__dq_done[0:0]),
    .kq(hcollks_NE_p2__vm_kq[561:281]),
    .kq_done(vmb_NE5__kq_done[0:0]),
    .xq(hb_vms_NE__bk_xq[1655:1380]),
    .xq_done(vmb_NE5__xq_done[0:0]),
    .xq2(hb_vms_NE__bk_xq2[1655:1380]),
    .xq2_done(vmb_NE5__xq2_done[0:0]),
    .eg(vmb_NE5__eg[275:0]),
    .pq(hb_vms_NE__bk_pq[1709:1425]),
    .pr(vmb_NE5__pr[265:0]),
    .status(vmb_NE5__status[17:0])
  );
  hfd_vms_bank_native_q0_faces vmb_NE6 (
    .rq0(su_NE3__lg_rq[16:0]),
    .rr0(vmb_NE6__rr0[256:0]),
    .rq1(hb_dbk_NE__rq[118:102]),
    .rr1(vmb_NE6__rr1[256:0]),
    .rq2(xl_NE_ctl__rq[118:102]),
    .rr2(vmb_NE6__rr2[256:0]),
    .rq3(hcollrs_NE__vm_rq[118:102]),
    .rr3(vmb_NE6__rr3[256:0]),
    .rq4(hb_idx__op_NE__vm_rq[118:102]),
    .rr4(vmb_NE6__rr4[256:0]),
    .wq0(su_NE3__lg_wq[280:0]),
    .wq_done0(vmb_NE6__wq_done0[0:0]),
    .wq1(smw_NE__wq_s2[280:0]),
    .wq_done1(vmb_NE6__wq_done1[0:0]),
    .bid(3'b110),
    .sid(2'b11),
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_e(hb_ckgen__pll_stream[0:0]),
    .clk_w(hb_ckgen__pll_stream[0:0]),
    .clk_macro0(hb_ckgen__pll_stream[0:0]),
    .clk_macro1(hb_ckgen__pll_stream[0:0]),
    .clk_macro2(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__vmb_NE6__rst_n[0:0]),
    .rslot_v(calendar_NE__rslot_v[6:6]),
    .rslot(calendar_NE__rslot[20:18]),
    .wslot_v(calendar_NE__wslot_v[6:6]),
    .wslot(calendar_NE__wslot[20:18]),
    .dq(vmdel_NE6__dq[280:0]),
    .dq_done(vmb_NE6__dq_done[0:0]),
    .kq(hcollks_NE_p3__vm_kq[280:0]),
    .kq_done(vmb_NE6__kq_done[0:0]),
    .xq(hb_vms_NE__bk_xq[1931:1656]),
    .xq_done(vmb_NE6__xq_done[0:0]),
    .xq2(hb_vms_NE__bk_xq2[1931:1656]),
    .xq2_done(vmb_NE6__xq2_done[0:0]),
    .eg(vmb_NE6__eg[275:0]),
    .pq(hb_vms_NE__bk_pq[1994:1710]),
    .pr(vmb_NE6__pr[265:0]),
    .status(vmb_NE6__status[17:0])
  );
  hfd_vms_bank_native_q0_faces vmb_NE7 (
    .rq0(su_NE3__lg_rq[33:17]),
    .rr0(vmb_NE7__rr0[256:0]),
    .rq1(hb_dbk_NE__rq[135:119]),
    .rr1(vmb_NE7__rr1[256:0]),
    .rq2(xl_NE_ctl__rq[135:119]),
    .rr2(vmb_NE7__rr2[256:0]),
    .rq3(hcollrs_NE__vm_rq[135:119]),
    .rr3(vmb_NE7__rr3[256:0]),
    .rq4(hb_idx__op_NE__vm_rq[135:119]),
    .rr4(vmb_NE7__rr4[256:0]),
    .wq0(su_NE3__lg_wq[561:281]),
    .wq_done0(vmb_NE7__wq_done0[0:0]),
    .wq1(smw_NE__wq_s3[280:0]),
    .wq_done1(vmb_NE7__wq_done1[0:0]),
    .bid(3'b111),
    .sid(2'b11),
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_e(hb_ckgen__pll_stream[0:0]),
    .clk_w(hb_ckgen__pll_stream[0:0]),
    .clk_macro0(hb_ckgen__pll_stream[0:0]),
    .clk_macro1(hb_ckgen__pll_stream[0:0]),
    .clk_macro2(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__vmb_NE7__rst_n[0:0]),
    .rslot_v(calendar_NE__rslot_v[7:7]),
    .rslot(calendar_NE__rslot[23:21]),
    .wslot_v(calendar_NE__wslot_v[7:7]),
    .wslot(calendar_NE__wslot[23:21]),
    .dq(vmdel_NE7__dq[280:0]),
    .dq_done(vmb_NE7__dq_done[0:0]),
    .kq(hcollks_NE_p3__vm_kq[561:281]),
    .kq_done(vmb_NE7__kq_done[0:0]),
    .xq(hb_vms_NE__bk_xq[2207:1932]),
    .xq_done(vmb_NE7__xq_done[0:0]),
    .xq2(hb_vms_NE__bk_xq2[2207:1932]),
    .xq2_done(vmb_NE7__xq2_done[0:0]),
    .eg(vmb_NE7__eg[275:0]),
    .pq(hb_vms_NE__bk_pq[2279:1995]),
    .pr(vmb_NE7__pr[265:0]),
    .status(vmb_NE7__status[17:0])
  );
  hfd_vms_bank_native_q0_faces vmb_NW0 (
    .rq0(su_NW0__lg_rq[16:0]),
    .rr0(vmb_NW0__rr0[256:0]),
    .rq1(hb_dbk_NW__rq[16:0]),
    .rr1(vmb_NW0__rr1[256:0]),
    .rq2(xl_NW_ctl__rq[16:0]),
    .rr2(vmb_NW0__rr2[256:0]),
    .rq3(hb_idx__nwsh__vm_rq[16:0]),
    .rr3(vmb_NW0__rr3[256:0]),
    .rq4(hcollrs_NW__vm_rq[16:0]),
    .rr4(vmb_NW0__rr4[256:0]),
    .wq0(su_NW0__lg_wq[280:0]),
    .wq_done0(vmb_NW0__wq_done0[0:0]),
    .wq1(vmm_NW0__wq_m[280:0]),
    .wq_done1(vmb_NW0__wq_done1[0:0]),
    .bid(3'b000),
    .sid(2'b10),
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_e(hb_ckgen__pll_stream[0:0]),
    .clk_w(hb_ckgen__pll_stream[0:0]),
    .clk_macro0(hb_ckgen__pll_stream[0:0]),
    .clk_macro1(hb_ckgen__pll_stream[0:0]),
    .clk_macro2(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__vmb_NW0__rst_n[0:0]),
    .rslot_v(calendar_NW__rslot_v[0:0]),
    .rslot(calendar_NW__rslot[2:0]),
    .wslot_v(calendar_NW__wslot_v[0:0]),
    .wslot(calendar_NW__wslot[2:0]),
    .dq(vmdel_NW0__dq[280:0]),
    .dq_done(vmb_NW0__dq_done[0:0]),
    .kq(hcollks_NW_p0__vm_kq[280:0]),
    .kq_done(vmb_NW0__kq_done[0:0]),
    .xq(hb_vms_NW__b0_xq[275:0]),
    .xq_done(vmb_NW0__xq_done[0:0]),
    .xq2(hb_vms_NW__b0_xq2[275:0]),
    .xq2_done(vmb_NW0__xq2_done[0:0]),
    .eg(vmb_NW0__eg[275:0]),
    .pq(hb_vms_NW__b0_pq[284:0]),
    .pr(vmb_NW0__pr[265:0]),
    .status(vmb_NW0__status[17:0])
  );
  hfd_vms_bank_native_q0_faces vmb_NW1 (
    .rq0(su_NW0__lg_rq[33:17]),
    .rr0(vmb_NW1__rr0[256:0]),
    .rq1(hb_dbk_NW__rq[33:17]),
    .rr1(vmb_NW1__rr1[256:0]),
    .rq2(xl_NW_ctl__rq[33:17]),
    .rr2(vmb_NW1__rr2[256:0]),
    .rq3(hb_idx__nwsh__vm_rq[33:17]),
    .rr3(vmb_NW1__rr3[256:0]),
    .rq4(hcollrs_NW__vm_rq[33:17]),
    .rr4(vmb_NW1__rr4[256:0]),
    .wq0(su_NW0__lg_wq[561:281]),
    .wq_done0(vmb_NW1__wq_done0[0:0]),
    .wq1(vmm_NW1__wq_m[280:0]),
    .wq_done1(vmb_NW1__wq_done1[0:0]),
    .bid(3'b001),
    .sid(2'b10),
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_e(hb_ckgen__pll_stream[0:0]),
    .clk_w(hb_ckgen__pll_stream[0:0]),
    .clk_macro0(hb_ckgen__pll_stream[0:0]),
    .clk_macro1(hb_ckgen__pll_stream[0:0]),
    .clk_macro2(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__vmb_NW1__rst_n[0:0]),
    .rslot_v(calendar_NW__rslot_v[1:1]),
    .rslot(calendar_NW__rslot[5:3]),
    .wslot_v(calendar_NW__wslot_v[1:1]),
    .wslot(calendar_NW__wslot[5:3]),
    .dq(vmdel_NW1__dq[280:0]),
    .dq_done(vmb_NW1__dq_done[0:0]),
    .kq(hcollks_NW_p0__vm_kq[561:281]),
    .kq_done(vmb_NW1__kq_done[0:0]),
    .xq(hb_vms_NW__b1_xq[275:0]),
    .xq_done(vmb_NW1__xq_done[0:0]),
    .xq2(hb_vms_NW__b1_xq2[275:0]),
    .xq2_done(vmb_NW1__xq2_done[0:0]),
    .eg(vmb_NW1__eg[275:0]),
    .pq(hb_vms_NW__b1_pq[284:0]),
    .pr(vmb_NW1__pr[265:0]),
    .status(vmb_NW1__status[17:0])
  );
  hfd_vms_bank_native_q0_faces vmb_NW2 (
    .rq0(su_NW1__lg_rq[16:0]),
    .rr0(vmb_NW2__rr0[256:0]),
    .rq1(hb_dbk_NW__rq[50:34]),
    .rr1(vmb_NW2__rr1[256:0]),
    .rq2(xl_NW_ctl__rq[50:34]),
    .rr2(vmb_NW2__rr2[256:0]),
    .rq3(hb_idx__nwsh__vm_rq[50:34]),
    .rr3(vmb_NW2__rr3[256:0]),
    .rq4(hcollrs_NW__vm_rq[50:34]),
    .rr4(vmb_NW2__rr4[256:0]),
    .wq0(su_NW1__lg_wq[280:0]),
    .wq_done0(vmb_NW2__wq_done0[0:0]),
    .wq1(vmm_NW2__wq_m[280:0]),
    .wq_done1(vmb_NW2__wq_done1[0:0]),
    .bid(3'b010),
    .sid(2'b10),
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_e(hb_ckgen__pll_stream[0:0]),
    .clk_w(hb_ckgen__pll_stream[0:0]),
    .clk_macro0(hb_ckgen__pll_stream[0:0]),
    .clk_macro1(hb_ckgen__pll_stream[0:0]),
    .clk_macro2(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__vmb_NW2__rst_n[0:0]),
    .rslot_v(calendar_NW__rslot_v[2:2]),
    .rslot(calendar_NW__rslot[8:6]),
    .wslot_v(calendar_NW__wslot_v[2:2]),
    .wslot(calendar_NW__wslot[8:6]),
    .dq(vmdel_NW2__dq[280:0]),
    .dq_done(vmb_NW2__dq_done[0:0]),
    .kq(hcollks_NW_p1__vm_kq[280:0]),
    .kq_done(vmb_NW2__kq_done[0:0]),
    .xq(hb_vms_NW__b2_xq[275:0]),
    .xq_done(vmb_NW2__xq_done[0:0]),
    .xq2(hb_vms_NW__b2_xq2[275:0]),
    .xq2_done(vmb_NW2__xq2_done[0:0]),
    .eg(vmb_NW2__eg[275:0]),
    .pq(hb_vms_NW__b2_pq[284:0]),
    .pr(vmb_NW2__pr[265:0]),
    .status(vmb_NW2__status[17:0])
  );
  hfd_vms_bank_native_q0_faces vmb_NW3 (
    .rq0(su_NW1__lg_rq[33:17]),
    .rr0(vmb_NW3__rr0[256:0]),
    .rq1(hb_dbk_NW__rq[67:51]),
    .rr1(vmb_NW3__rr1[256:0]),
    .rq2(xl_NW_ctl__rq[67:51]),
    .rr2(vmb_NW3__rr2[256:0]),
    .rq3(hb_idx__nwsh__vm_rq[67:51]),
    .rr3(vmb_NW3__rr3[256:0]),
    .rq4(hcollrs_NW__vm_rq[67:51]),
    .rr4(vmb_NW3__rr4[256:0]),
    .wq0(su_NW1__lg_wq[561:281]),
    .wq_done0(vmb_NW3__wq_done0[0:0]),
    .wq1(vmm_NW3__wq_m[280:0]),
    .wq_done1(vmb_NW3__wq_done1[0:0]),
    .bid(3'b011),
    .sid(2'b10),
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_e(hb_ckgen__pll_stream[0:0]),
    .clk_w(hb_ckgen__pll_stream[0:0]),
    .clk_macro0(hb_ckgen__pll_stream[0:0]),
    .clk_macro1(hb_ckgen__pll_stream[0:0]),
    .clk_macro2(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__vmb_NW3__rst_n[0:0]),
    .rslot_v(calendar_NW__rslot_v[3:3]),
    .rslot(calendar_NW__rslot[11:9]),
    .wslot_v(calendar_NW__wslot_v[3:3]),
    .wslot(calendar_NW__wslot[11:9]),
    .dq(vmdel_NW3__dq[280:0]),
    .dq_done(vmb_NW3__dq_done[0:0]),
    .kq(hcollks_NW_p1__vm_kq[561:281]),
    .kq_done(vmb_NW3__kq_done[0:0]),
    .xq(hb_vms_NW__b3_xq[275:0]),
    .xq_done(vmb_NW3__xq_done[0:0]),
    .xq2(hb_vms_NW__b3_xq2[275:0]),
    .xq2_done(vmb_NW3__xq2_done[0:0]),
    .eg(vmb_NW3__eg[275:0]),
    .pq(hb_vms_NW__b3_pq[284:0]),
    .pr(vmb_NW3__pr[265:0]),
    .status(vmb_NW3__status[17:0])
  );
  hfd_vms_bank_native_q0_faces vmb_NW4 (
    .rq0(su_NW2__lg_rq[16:0]),
    .rr0(vmb_NW4__rr0[256:0]),
    .rq1(hb_dbk_NW__rq[84:68]),
    .rr1(vmb_NW4__rr1[256:0]),
    .rq2(xl_NW_ctl__rq[84:68]),
    .rr2(vmb_NW4__rr2[256:0]),
    .rq3(hb_idx__nwsh__vm_rq[84:68]),
    .rr3(vmb_NW4__rr3[256:0]),
    .rq4(hcollrs_NW__vm_rq[84:68]),
    .rr4(vmb_NW4__rr4[256:0]),
    .wq0(su_NW2__lg_wq[280:0]),
    .wq_done0(vmb_NW4__wq_done0[0:0]),
    .wq1(vmm_NW4__wq_m[280:0]),
    .wq_done1(vmb_NW4__wq_done1[0:0]),
    .bid(3'b100),
    .sid(2'b10),
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_e(hb_ckgen__pll_stream[0:0]),
    .clk_w(hb_ckgen__pll_stream[0:0]),
    .clk_macro0(hb_ckgen__pll_stream[0:0]),
    .clk_macro1(hb_ckgen__pll_stream[0:0]),
    .clk_macro2(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__vmb_NW4__rst_n[0:0]),
    .rslot_v(calendar_NW__rslot_v[4:4]),
    .rslot(calendar_NW__rslot[14:12]),
    .wslot_v(calendar_NW__wslot_v[4:4]),
    .wslot(calendar_NW__wslot[14:12]),
    .dq(vmdel_NW4__dq[280:0]),
    .dq_done(vmb_NW4__dq_done[0:0]),
    .kq(hcollks_NW_p2__vm_kq[280:0]),
    .kq_done(vmb_NW4__kq_done[0:0]),
    .xq(hb_vms_NW__b4_xq[275:0]),
    .xq_done(vmb_NW4__xq_done[0:0]),
    .xq2(hb_vms_NW__b4_xq2[275:0]),
    .xq2_done(vmb_NW4__xq2_done[0:0]),
    .eg(vmb_NW4__eg[275:0]),
    .pq(hb_vms_NW__b4_pq[284:0]),
    .pr(vmb_NW4__pr[265:0]),
    .status(vmb_NW4__status[17:0])
  );
  hfd_vms_bank_native_q0_faces vmb_NW5 (
    .rq0(su_NW2__lg_rq[33:17]),
    .rr0(vmb_NW5__rr0[256:0]),
    .rq1(hb_dbk_NW__rq[101:85]),
    .rr1(vmb_NW5__rr1[256:0]),
    .rq2(xl_NW_ctl__rq[101:85]),
    .rr2(vmb_NW5__rr2[256:0]),
    .rq3(hb_idx__nwsh__vm_rq[101:85]),
    .rr3(vmb_NW5__rr3[256:0]),
    .rq4(hcollrs_NW__vm_rq[101:85]),
    .rr4(vmb_NW5__rr4[256:0]),
    .wq0(su_NW2__lg_wq[561:281]),
    .wq_done0(vmb_NW5__wq_done0[0:0]),
    .wq1(vmm_NW5__wq_m[280:0]),
    .wq_done1(vmb_NW5__wq_done1[0:0]),
    .bid(3'b101),
    .sid(2'b10),
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_e(hb_ckgen__pll_stream[0:0]),
    .clk_w(hb_ckgen__pll_stream[0:0]),
    .clk_macro0(hb_ckgen__pll_stream[0:0]),
    .clk_macro1(hb_ckgen__pll_stream[0:0]),
    .clk_macro2(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__vmb_NW5__rst_n[0:0]),
    .rslot_v(calendar_NW__rslot_v[5:5]),
    .rslot(calendar_NW__rslot[17:15]),
    .wslot_v(calendar_NW__wslot_v[5:5]),
    .wslot(calendar_NW__wslot[17:15]),
    .dq(vmdel_NW5__dq[280:0]),
    .dq_done(vmb_NW5__dq_done[0:0]),
    .kq(hcollks_NW_p2__vm_kq[561:281]),
    .kq_done(vmb_NW5__kq_done[0:0]),
    .xq(hb_vms_NW__b5_xq[275:0]),
    .xq_done(vmb_NW5__xq_done[0:0]),
    .xq2(hb_vms_NW__b5_xq2[275:0]),
    .xq2_done(vmb_NW5__xq2_done[0:0]),
    .eg(vmb_NW5__eg[275:0]),
    .pq(hb_vms_NW__b5_pq[284:0]),
    .pr(vmb_NW5__pr[265:0]),
    .status(vmb_NW5__status[17:0])
  );
  hfd_vms_bank_native_q0_faces vmb_NW6 (
    .rq0(su_NW3__lg_rq[16:0]),
    .rr0(vmb_NW6__rr0[256:0]),
    .rq1(hb_dbk_NW__rq[118:102]),
    .rr1(vmb_NW6__rr1[256:0]),
    .rq2(xl_NW_ctl__rq[118:102]),
    .rr2(vmb_NW6__rr2[256:0]),
    .rq3(hb_idx__nwsh__vm_rq[118:102]),
    .rr3(vmb_NW6__rr3[256:0]),
    .rq4(hcollrs_NW__vm_rq[118:102]),
    .rr4(vmb_NW6__rr4[256:0]),
    .wq0(su_NW3__lg_wq[280:0]),
    .wq_done0(vmb_NW6__wq_done0[0:0]),
    .wq1(vmm_NW6__wq_m[280:0]),
    .wq_done1(vmb_NW6__wq_done1[0:0]),
    .bid(3'b110),
    .sid(2'b10),
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_e(hb_ckgen__pll_stream[0:0]),
    .clk_w(hb_ckgen__pll_stream[0:0]),
    .clk_macro0(hb_ckgen__pll_stream[0:0]),
    .clk_macro1(hb_ckgen__pll_stream[0:0]),
    .clk_macro2(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__vmb_NW6__rst_n[0:0]),
    .rslot_v(calendar_NW__rslot_v[6:6]),
    .rslot(calendar_NW__rslot[20:18]),
    .wslot_v(calendar_NW__wslot_v[6:6]),
    .wslot(calendar_NW__wslot[20:18]),
    .dq(vmdel_NW6__dq[280:0]),
    .dq_done(vmb_NW6__dq_done[0:0]),
    .kq(hcollks_NW_p3__vm_kq[280:0]),
    .kq_done(vmb_NW6__kq_done[0:0]),
    .xq(hb_vms_NW__b6_xq[275:0]),
    .xq_done(vmb_NW6__xq_done[0:0]),
    .xq2(hb_vms_NW__b6_xq2[275:0]),
    .xq2_done(vmb_NW6__xq2_done[0:0]),
    .eg(vmb_NW6__eg[275:0]),
    .pq(hb_vms_NW__b6_pq[284:0]),
    .pr(vmb_NW6__pr[265:0]),
    .status(vmb_NW6__status[17:0])
  );
  hfd_vms_bank_native_q0_faces vmb_NW7 (
    .rq0(su_NW3__lg_rq[33:17]),
    .rr0(vmb_NW7__rr0[256:0]),
    .rq1(hb_dbk_NW__rq[135:119]),
    .rr1(vmb_NW7__rr1[256:0]),
    .rq2(xl_NW_ctl__rq[135:119]),
    .rr2(vmb_NW7__rr2[256:0]),
    .rq3(hb_idx__nwsh__vm_rq[135:119]),
    .rr3(vmb_NW7__rr3[256:0]),
    .rq4(hcollrs_NW__vm_rq[135:119]),
    .rr4(vmb_NW7__rr4[256:0]),
    .wq0(su_NW3__lg_wq[561:281]),
    .wq_done0(vmb_NW7__wq_done0[0:0]),
    .wq1(vmm_NW7__wq_m[280:0]),
    .wq_done1(vmb_NW7__wq_done1[0:0]),
    .bid(3'b111),
    .sid(2'b10),
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_e(hb_ckgen__pll_stream[0:0]),
    .clk_w(hb_ckgen__pll_stream[0:0]),
    .clk_macro0(hb_ckgen__pll_stream[0:0]),
    .clk_macro1(hb_ckgen__pll_stream[0:0]),
    .clk_macro2(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__vmb_NW7__rst_n[0:0]),
    .rslot_v(calendar_NW__rslot_v[7:7]),
    .rslot(calendar_NW__rslot[23:21]),
    .wslot_v(calendar_NW__wslot_v[7:7]),
    .wslot(calendar_NW__wslot[23:21]),
    .dq(vmdel_NW7__dq[280:0]),
    .dq_done(vmb_NW7__dq_done[0:0]),
    .kq(hcollks_NW_p3__vm_kq[561:281]),
    .kq_done(vmb_NW7__kq_done[0:0]),
    .xq(hb_vms_NW__b7_xq[275:0]),
    .xq_done(vmb_NW7__xq_done[0:0]),
    .xq2(hb_vms_NW__b7_xq2[275:0]),
    .xq2_done(vmb_NW7__xq2_done[0:0]),
    .eg(vmb_NW7__eg[275:0]),
    .pq(hb_vms_NW__b7_pq[284:0]),
    .pr(vmb_NW7__pr[265:0]),
    .status(vmb_NW7__status[17:0])
  );
  hfd_vms_bank_native_q0_faces vmb_SE0 (
    .rq0(su_SE0__lg_rq[16:0]),
    .rr0(vmb_SE0__rr0[256:0]),
    .rq1(hb_dbk_SE__rq[16:0]),
    .rr1(vmb_SE0__rr1[256:0]),
    .rq2(xl_SE_ctl__rq[16:0]),
    .rr2(vmb_SE0__rr2[256:0]),
    .rq3(hcollrs_SE__vm_rq[16:0]),
    .rr3(vmb_SE0__rr3[256:0]),
    .rq4(hb_idx__op_SE__vm_rq[16:0]),
    .rr4(vmb_SE0__rr4[256:0]),
    .wq0(su_SE0__lg_wq[280:0]),
    .wq_done0(vmb_SE0__wq_done0[0:0]),
    .wq1(smw_SE__wq_t0[280:0]),
    .wq_done1(vmb_SE0__wq_done1[0:0]),
    .bid(3'b000),
    .sid(2'b01),
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_e(hb_ckgen__pll_stream[0:0]),
    .clk_w(hb_ckgen__pll_stream[0:0]),
    .clk_macro0(hb_ckgen__pll_stream[0:0]),
    .clk_macro1(hb_ckgen__pll_stream[0:0]),
    .clk_macro2(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__vmb_SE0__rst_n[0:0]),
    .rslot_v(calendar_SE__rslot_v[0:0]),
    .rslot(calendar_SE__rslot[2:0]),
    .wslot_v(calendar_SE__wslot_v[0:0]),
    .wslot(calendar_SE__wslot[2:0]),
    .dq(vmdel_SE0__dq[280:0]),
    .dq_done(vmb_SE0__dq_done[0:0]),
    .kq(hcollks_SE_p0__vm_kq[280:0]),
    .kq_done(vmb_SE0__kq_done[0:0]),
    .xq(hb_vms_SE__bk_xq[275:0]),
    .xq_done(vmb_SE0__xq_done[0:0]),
    .xq2(hb_vms_SE__bk_xq2[275:0]),
    .xq2_done(vmb_SE0__xq2_done[0:0]),
    .eg(vmb_SE0__eg[275:0]),
    .pq(hb_vms_SE__bk_pq[284:0]),
    .pr(vmb_SE0__pr[265:0]),
    .status(vmb_SE0__status[17:0])
  );
  hfd_vms_bank_native_q0_faces vmb_SE1 (
    .rq0(su_SE0__lg_rq[33:17]),
    .rr0(vmb_SE1__rr0[256:0]),
    .rq1(hb_dbk_SE__rq[33:17]),
    .rr1(vmb_SE1__rr1[256:0]),
    .rq2(xl_SE_ctl__rq[33:17]),
    .rr2(vmb_SE1__rr2[256:0]),
    .rq3(hcollrs_SE__vm_rq[33:17]),
    .rr3(vmb_SE1__rr3[256:0]),
    .rq4(hb_idx__op_SE__vm_rq[33:17]),
    .rr4(vmb_SE1__rr4[256:0]),
    .wq0(su_SE0__lg_wq[561:281]),
    .wq_done0(vmb_SE1__wq_done0[0:0]),
    .wq1(smw_SE__wq_t1[280:0]),
    .wq_done1(vmb_SE1__wq_done1[0:0]),
    .bid(3'b001),
    .sid(2'b01),
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_e(hb_ckgen__pll_stream[0:0]),
    .clk_w(hb_ckgen__pll_stream[0:0]),
    .clk_macro0(hb_ckgen__pll_stream[0:0]),
    .clk_macro1(hb_ckgen__pll_stream[0:0]),
    .clk_macro2(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__vmb_SE1__rst_n[0:0]),
    .rslot_v(calendar_SE__rslot_v[1:1]),
    .rslot(calendar_SE__rslot[5:3]),
    .wslot_v(calendar_SE__wslot_v[1:1]),
    .wslot(calendar_SE__wslot[5:3]),
    .dq(vmdel_SE1__dq[280:0]),
    .dq_done(vmb_SE1__dq_done[0:0]),
    .kq(hcollks_SE_p0__vm_kq[561:281]),
    .kq_done(vmb_SE1__kq_done[0:0]),
    .xq(hb_vms_SE__bk_xq[551:276]),
    .xq_done(vmb_SE1__xq_done[0:0]),
    .xq2(hb_vms_SE__bk_xq2[551:276]),
    .xq2_done(vmb_SE1__xq2_done[0:0]),
    .eg(vmb_SE1__eg[275:0]),
    .pq(hb_vms_SE__bk_pq[569:285]),
    .pr(vmb_SE1__pr[265:0]),
    .status(vmb_SE1__status[17:0])
  );
  hfd_vms_bank_native_q0_faces vmb_SE2 (
    .rq0(su_SE1__lg_rq[16:0]),
    .rr0(vmb_SE2__rr0[256:0]),
    .rq1(hb_dbk_SE__rq[50:34]),
    .rr1(vmb_SE2__rr1[256:0]),
    .rq2(xl_SE_ctl__rq[50:34]),
    .rr2(vmb_SE2__rr2[256:0]),
    .rq3(hcollrs_SE__vm_rq[50:34]),
    .rr3(vmb_SE2__rr3[256:0]),
    .rq4(hb_idx__op_SE__vm_rq[50:34]),
    .rr4(vmb_SE2__rr4[256:0]),
    .wq0(su_SE1__lg_wq[280:0]),
    .wq_done0(vmb_SE2__wq_done0[0:0]),
    .wq1(smw_SE__wq_t2[280:0]),
    .wq_done1(vmb_SE2__wq_done1[0:0]),
    .bid(3'b010),
    .sid(2'b01),
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_e(hb_ckgen__pll_stream[0:0]),
    .clk_w(hb_ckgen__pll_stream[0:0]),
    .clk_macro0(hb_ckgen__pll_stream[0:0]),
    .clk_macro1(hb_ckgen__pll_stream[0:0]),
    .clk_macro2(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__vmb_SE2__rst_n[0:0]),
    .rslot_v(calendar_SE__rslot_v[2:2]),
    .rslot(calendar_SE__rslot[8:6]),
    .wslot_v(calendar_SE__wslot_v[2:2]),
    .wslot(calendar_SE__wslot[8:6]),
    .dq(vmdel_SE2__dq[280:0]),
    .dq_done(vmb_SE2__dq_done[0:0]),
    .kq(hcollks_SE_p1__vm_kq[280:0]),
    .kq_done(vmb_SE2__kq_done[0:0]),
    .xq(hb_vms_SE__bk_xq[827:552]),
    .xq_done(vmb_SE2__xq_done[0:0]),
    .xq2(hb_vms_SE__bk_xq2[827:552]),
    .xq2_done(vmb_SE2__xq2_done[0:0]),
    .eg(vmb_SE2__eg[275:0]),
    .pq(hb_vms_SE__bk_pq[854:570]),
    .pr(vmb_SE2__pr[265:0]),
    .status(vmb_SE2__status[17:0])
  );
  hfd_vms_bank_native_q0_faces vmb_SE3 (
    .rq0(su_SE1__lg_rq[33:17]),
    .rr0(vmb_SE3__rr0[256:0]),
    .rq1(hb_dbk_SE__rq[67:51]),
    .rr1(vmb_SE3__rr1[256:0]),
    .rq2(xl_SE_ctl__rq[67:51]),
    .rr2(vmb_SE3__rr2[256:0]),
    .rq3(hcollrs_SE__vm_rq[67:51]),
    .rr3(vmb_SE3__rr3[256:0]),
    .rq4(hb_idx__op_SE__vm_rq[67:51]),
    .rr4(vmb_SE3__rr4[256:0]),
    .wq0(su_SE1__lg_wq[561:281]),
    .wq_done0(vmb_SE3__wq_done0[0:0]),
    .wq1(smw_SE__wq_t3[280:0]),
    .wq_done1(vmb_SE3__wq_done1[0:0]),
    .bid(3'b011),
    .sid(2'b01),
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_e(hb_ckgen__pll_stream[0:0]),
    .clk_w(hb_ckgen__pll_stream[0:0]),
    .clk_macro0(hb_ckgen__pll_stream[0:0]),
    .clk_macro1(hb_ckgen__pll_stream[0:0]),
    .clk_macro2(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__vmb_SE3__rst_n[0:0]),
    .rslot_v(calendar_SE__rslot_v[3:3]),
    .rslot(calendar_SE__rslot[11:9]),
    .wslot_v(calendar_SE__wslot_v[3:3]),
    .wslot(calendar_SE__wslot[11:9]),
    .dq(vmdel_SE3__dq[280:0]),
    .dq_done(vmb_SE3__dq_done[0:0]),
    .kq(hcollks_SE_p1__vm_kq[561:281]),
    .kq_done(vmb_SE3__kq_done[0:0]),
    .xq(hb_vms_SE__bk_xq[1103:828]),
    .xq_done(vmb_SE3__xq_done[0:0]),
    .xq2(hb_vms_SE__bk_xq2[1103:828]),
    .xq2_done(vmb_SE3__xq2_done[0:0]),
    .eg(vmb_SE3__eg[275:0]),
    .pq(hb_vms_SE__bk_pq[1139:855]),
    .pr(vmb_SE3__pr[265:0]),
    .status(vmb_SE3__status[17:0])
  );
  hfd_vms_bank_native_q0_faces vmb_SE4 (
    .rq0(su_SE2__lg_rq[16:0]),
    .rr0(vmb_SE4__rr0[256:0]),
    .rq1(hb_dbk_SE__rq[84:68]),
    .rr1(vmb_SE4__rr1[256:0]),
    .rq2(xl_SE_ctl__rq[84:68]),
    .rr2(vmb_SE4__rr2[256:0]),
    .rq3(hcollrs_SE__vm_rq[84:68]),
    .rr3(vmb_SE4__rr3[256:0]),
    .rq4(hb_idx__op_SE__vm_rq[84:68]),
    .rr4(vmb_SE4__rr4[256:0]),
    .wq0(su_SE2__lg_wq[280:0]),
    .wq_done0(vmb_SE4__wq_done0[0:0]),
    .wq1(smw_SE__wq_s0[280:0]),
    .wq_done1(vmb_SE4__wq_done1[0:0]),
    .bid(3'b100),
    .sid(2'b01),
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_e(hb_ckgen__pll_stream[0:0]),
    .clk_w(hb_ckgen__pll_stream[0:0]),
    .clk_macro0(hb_ckgen__pll_stream[0:0]),
    .clk_macro1(hb_ckgen__pll_stream[0:0]),
    .clk_macro2(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__vmb_SE4__rst_n[0:0]),
    .rslot_v(calendar_SE__rslot_v[4:4]),
    .rslot(calendar_SE__rslot[14:12]),
    .wslot_v(calendar_SE__wslot_v[4:4]),
    .wslot(calendar_SE__wslot[14:12]),
    .dq(vmdel_SE4__dq[280:0]),
    .dq_done(vmb_SE4__dq_done[0:0]),
    .kq(hcollks_SE_p2__vm_kq[280:0]),
    .kq_done(vmb_SE4__kq_done[0:0]),
    .xq(hb_vms_SE__bk_xq[1379:1104]),
    .xq_done(vmb_SE4__xq_done[0:0]),
    .xq2(hb_vms_SE__bk_xq2[1379:1104]),
    .xq2_done(vmb_SE4__xq2_done[0:0]),
    .eg(vmb_SE4__eg[275:0]),
    .pq(hb_vms_SE__bk_pq[1424:1140]),
    .pr(vmb_SE4__pr[265:0]),
    .status(vmb_SE4__status[17:0])
  );
  hfd_vms_bank_native_q0_faces vmb_SE5 (
    .rq0(su_SE2__lg_rq[33:17]),
    .rr0(vmb_SE5__rr0[256:0]),
    .rq1(hb_dbk_SE__rq[101:85]),
    .rr1(vmb_SE5__rr1[256:0]),
    .rq2(xl_SE_ctl__rq[101:85]),
    .rr2(vmb_SE5__rr2[256:0]),
    .rq3(hcollrs_SE__vm_rq[101:85]),
    .rr3(vmb_SE5__rr3[256:0]),
    .rq4(hb_idx__op_SE__vm_rq[101:85]),
    .rr4(vmb_SE5__rr4[256:0]),
    .wq0(su_SE2__lg_wq[561:281]),
    .wq_done0(vmb_SE5__wq_done0[0:0]),
    .wq1(smw_SE__wq_s1[280:0]),
    .wq_done1(vmb_SE5__wq_done1[0:0]),
    .bid(3'b101),
    .sid(2'b01),
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_e(hb_ckgen__pll_stream[0:0]),
    .clk_w(hb_ckgen__pll_stream[0:0]),
    .clk_macro0(hb_ckgen__pll_stream[0:0]),
    .clk_macro1(hb_ckgen__pll_stream[0:0]),
    .clk_macro2(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__vmb_SE5__rst_n[0:0]),
    .rslot_v(calendar_SE__rslot_v[5:5]),
    .rslot(calendar_SE__rslot[17:15]),
    .wslot_v(calendar_SE__wslot_v[5:5]),
    .wslot(calendar_SE__wslot[17:15]),
    .dq(vmdel_SE5__dq[280:0]),
    .dq_done(vmb_SE5__dq_done[0:0]),
    .kq(hcollks_SE_p2__vm_kq[561:281]),
    .kq_done(vmb_SE5__kq_done[0:0]),
    .xq(hb_vms_SE__bk_xq[1655:1380]),
    .xq_done(vmb_SE5__xq_done[0:0]),
    .xq2(hb_vms_SE__bk_xq2[1655:1380]),
    .xq2_done(vmb_SE5__xq2_done[0:0]),
    .eg(vmb_SE5__eg[275:0]),
    .pq(hb_vms_SE__bk_pq[1709:1425]),
    .pr(vmb_SE5__pr[265:0]),
    .status(vmb_SE5__status[17:0])
  );
  hfd_vms_bank_native_q0_faces vmb_SE6 (
    .rq0(su_SE3__lg_rq[16:0]),
    .rr0(vmb_SE6__rr0[256:0]),
    .rq1(hb_dbk_SE__rq[118:102]),
    .rr1(vmb_SE6__rr1[256:0]),
    .rq2(xl_SE_ctl__rq[118:102]),
    .rr2(vmb_SE6__rr2[256:0]),
    .rq3(hcollrs_SE__vm_rq[118:102]),
    .rr3(vmb_SE6__rr3[256:0]),
    .rq4(hb_idx__op_SE__vm_rq[118:102]),
    .rr4(vmb_SE6__rr4[256:0]),
    .wq0(su_SE3__lg_wq[280:0]),
    .wq_done0(vmb_SE6__wq_done0[0:0]),
    .wq1(smw_SE__wq_s2[280:0]),
    .wq_done1(vmb_SE6__wq_done1[0:0]),
    .bid(3'b110),
    .sid(2'b01),
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_e(hb_ckgen__pll_stream[0:0]),
    .clk_w(hb_ckgen__pll_stream[0:0]),
    .clk_macro0(hb_ckgen__pll_stream[0:0]),
    .clk_macro1(hb_ckgen__pll_stream[0:0]),
    .clk_macro2(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__vmb_SE6__rst_n[0:0]),
    .rslot_v(calendar_SE__rslot_v[6:6]),
    .rslot(calendar_SE__rslot[20:18]),
    .wslot_v(calendar_SE__wslot_v[6:6]),
    .wslot(calendar_SE__wslot[20:18]),
    .dq(vmdel_SE6__dq[280:0]),
    .dq_done(vmb_SE6__dq_done[0:0]),
    .kq(hcollks_SE_p3__vm_kq[280:0]),
    .kq_done(vmb_SE6__kq_done[0:0]),
    .xq(hb_vms_SE__bk_xq[1931:1656]),
    .xq_done(vmb_SE6__xq_done[0:0]),
    .xq2(hb_vms_SE__bk_xq2[1931:1656]),
    .xq2_done(vmb_SE6__xq2_done[0:0]),
    .eg(vmb_SE6__eg[275:0]),
    .pq(hb_vms_SE__bk_pq[1994:1710]),
    .pr(vmb_SE6__pr[265:0]),
    .status(vmb_SE6__status[17:0])
  );
  hfd_vms_bank_native_q0_faces vmb_SE7 (
    .rq0(su_SE3__lg_rq[33:17]),
    .rr0(vmb_SE7__rr0[256:0]),
    .rq1(hb_dbk_SE__rq[135:119]),
    .rr1(vmb_SE7__rr1[256:0]),
    .rq2(xl_SE_ctl__rq[135:119]),
    .rr2(vmb_SE7__rr2[256:0]),
    .rq3(hcollrs_SE__vm_rq[135:119]),
    .rr3(vmb_SE7__rr3[256:0]),
    .rq4(hb_idx__op_SE__vm_rq[135:119]),
    .rr4(vmb_SE7__rr4[256:0]),
    .wq0(su_SE3__lg_wq[561:281]),
    .wq_done0(vmb_SE7__wq_done0[0:0]),
    .wq1(smw_SE__wq_s3[280:0]),
    .wq_done1(vmb_SE7__wq_done1[0:0]),
    .bid(3'b111),
    .sid(2'b01),
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_e(hb_ckgen__pll_stream[0:0]),
    .clk_w(hb_ckgen__pll_stream[0:0]),
    .clk_macro0(hb_ckgen__pll_stream[0:0]),
    .clk_macro1(hb_ckgen__pll_stream[0:0]),
    .clk_macro2(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__vmb_SE7__rst_n[0:0]),
    .rslot_v(calendar_SE__rslot_v[7:7]),
    .rslot(calendar_SE__rslot[23:21]),
    .wslot_v(calendar_SE__wslot_v[7:7]),
    .wslot(calendar_SE__wslot[23:21]),
    .dq(vmdel_SE7__dq[280:0]),
    .dq_done(vmb_SE7__dq_done[0:0]),
    .kq(hcollks_SE_p3__vm_kq[561:281]),
    .kq_done(vmb_SE7__kq_done[0:0]),
    .xq(hb_vms_SE__bk_xq[2207:1932]),
    .xq_done(vmb_SE7__xq_done[0:0]),
    .xq2(hb_vms_SE__bk_xq2[2207:1932]),
    .xq2_done(vmb_SE7__xq2_done[0:0]),
    .eg(vmb_SE7__eg[275:0]),
    .pq(hb_vms_SE__bk_pq[2279:1995]),
    .pr(vmb_SE7__pr[265:0]),
    .status(vmb_SE7__status[17:0])
  );
  hfd_vms_bank_native_q0_faces vmb_SW0 (
    .rq0(su_SW0__lg_rq[16:0]),
    .rr0(vmb_SW0__rr0[256:0]),
    .rq1(hb_dbk_SW__rq[16:0]),
    .rr1(vmb_SW0__rr1[256:0]),
    .rq2(xl_SW_ctl__rq[16:0]),
    .rr2(vmb_SW0__rr2[256:0]),
    .rq3(hcollrs_SW__vm_rq[16:0]),
    .rr3(vmb_SW0__rr3[256:0]),
    .rq4(hb_idx__ctl__vm_rq[16:0]),
    .rr4(vmb_SW0__rr4[256:0]),
    .wq0(su_SW0__lg_wq[280:0]),
    .wq_done0(vmb_SW0__wq_done0[0:0]),
    .wq1(smw_SW__wq_s0[280:0]),
    .wq_done1(vmb_SW0__wq_done1[0:0]),
    .bid(3'b000),
    .sid(2'b00),
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_e(hb_ckgen__pll_stream[0:0]),
    .clk_w(hb_ckgen__pll_stream[0:0]),
    .clk_macro0(hb_ckgen__pll_stream[0:0]),
    .clk_macro1(hb_ckgen__pll_stream[0:0]),
    .clk_macro2(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__vmb_SW0__rst_n[0:0]),
    .rslot_v(calendar_SW__rslot_v[0:0]),
    .rslot(calendar_SW__rslot[2:0]),
    .wslot_v(calendar_SW__wslot_v[0:0]),
    .wslot(calendar_SW__wslot[2:0]),
    .dq(vmdel_SW0__dq[280:0]),
    .dq_done(vmb_SW0__dq_done[0:0]),
    .kq(hcollks_SW_p0__vm_kq[280:0]),
    .kq_done(vmb_SW0__kq_done[0:0]),
    .xq(hb_vms_SW__b0_xq[275:0]),
    .xq_done(vmb_SW0__xq_done[0:0]),
    .xq2(hb_vms_SW__b0_xq2[275:0]),
    .xq2_done(vmb_SW0__xq2_done[0:0]),
    .eg(vmb_SW0__eg[275:0]),
    .pq(hb_vms_SW__b0_pq[284:0]),
    .pr(vmb_SW0__pr[265:0]),
    .status(vmb_SW0__status[17:0])
  );
  hfd_vms_bank_native_q0_faces vmb_SW1 (
    .rq0(su_SW0__lg_rq[33:17]),
    .rr0(vmb_SW1__rr0[256:0]),
    .rq1(hb_dbk_SW__rq[33:17]),
    .rr1(vmb_SW1__rr1[256:0]),
    .rq2(xl_SW_ctl__rq[33:17]),
    .rr2(vmb_SW1__rr2[256:0]),
    .rq3(hcollrs_SW__vm_rq[33:17]),
    .rr3(vmb_SW1__rr3[256:0]),
    .rq4(hb_idx__ctl__vm_rq[33:17]),
    .rr4(vmb_SW1__rr4[256:0]),
    .wq0(su_SW0__lg_wq[561:281]),
    .wq_done0(vmb_SW1__wq_done0[0:0]),
    .wq1(smw_SW__wq_s1[280:0]),
    .wq_done1(vmb_SW1__wq_done1[0:0]),
    .bid(3'b001),
    .sid(2'b00),
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_e(hb_ckgen__pll_stream[0:0]),
    .clk_w(hb_ckgen__pll_stream[0:0]),
    .clk_macro0(hb_ckgen__pll_stream[0:0]),
    .clk_macro1(hb_ckgen__pll_stream[0:0]),
    .clk_macro2(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__vmb_SW1__rst_n[0:0]),
    .rslot_v(calendar_SW__rslot_v[1:1]),
    .rslot(calendar_SW__rslot[5:3]),
    .wslot_v(calendar_SW__wslot_v[1:1]),
    .wslot(calendar_SW__wslot[5:3]),
    .dq(vmdel_SW1__dq[280:0]),
    .dq_done(vmb_SW1__dq_done[0:0]),
    .kq(hcollks_SW_p0__vm_kq[561:281]),
    .kq_done(vmb_SW1__kq_done[0:0]),
    .xq(hb_vms_SW__b1_xq[275:0]),
    .xq_done(vmb_SW1__xq_done[0:0]),
    .xq2(hb_vms_SW__b1_xq2[275:0]),
    .xq2_done(vmb_SW1__xq2_done[0:0]),
    .eg(vmb_SW1__eg[275:0]),
    .pq(hb_vms_SW__b1_pq[284:0]),
    .pr(vmb_SW1__pr[265:0]),
    .status(vmb_SW1__status[17:0])
  );
  hfd_vms_bank_native_q0_faces vmb_SW2 (
    .rq0(su_SW1__lg_rq[16:0]),
    .rr0(vmb_SW2__rr0[256:0]),
    .rq1(hb_dbk_SW__rq[50:34]),
    .rr1(vmb_SW2__rr1[256:0]),
    .rq2(xl_SW_ctl__rq[50:34]),
    .rr2(vmb_SW2__rr2[256:0]),
    .rq3(hcollrs_SW__vm_rq[50:34]),
    .rr3(vmb_SW2__rr3[256:0]),
    .rq4(hb_idx__ctl__vm_rq[50:34]),
    .rr4(vmb_SW2__rr4[256:0]),
    .wq0(su_SW1__lg_wq[280:0]),
    .wq_done0(vmb_SW2__wq_done0[0:0]),
    .wq1(smw_SW__wq_s2[280:0]),
    .wq_done1(vmb_SW2__wq_done1[0:0]),
    .bid(3'b010),
    .sid(2'b00),
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_e(hb_ckgen__pll_stream[0:0]),
    .clk_w(hb_ckgen__pll_stream[0:0]),
    .clk_macro0(hb_ckgen__pll_stream[0:0]),
    .clk_macro1(hb_ckgen__pll_stream[0:0]),
    .clk_macro2(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__vmb_SW2__rst_n[0:0]),
    .rslot_v(calendar_SW__rslot_v[2:2]),
    .rslot(calendar_SW__rslot[8:6]),
    .wslot_v(calendar_SW__wslot_v[2:2]),
    .wslot(calendar_SW__wslot[8:6]),
    .dq(vmdel_SW2__dq[280:0]),
    .dq_done(vmb_SW2__dq_done[0:0]),
    .kq(hcollks_SW_p1__vm_kq[280:0]),
    .kq_done(vmb_SW2__kq_done[0:0]),
    .xq(hb_vms_SW__b2_xq[275:0]),
    .xq_done(vmb_SW2__xq_done[0:0]),
    .xq2(hb_vms_SW__b2_xq2[275:0]),
    .xq2_done(vmb_SW2__xq2_done[0:0]),
    .eg(vmb_SW2__eg[275:0]),
    .pq(hb_vms_SW__b2_pq[284:0]),
    .pr(vmb_SW2__pr[265:0]),
    .status(vmb_SW2__status[17:0])
  );
  hfd_vms_bank_native_q0_faces vmb_SW3 (
    .rq0(su_SW1__lg_rq[33:17]),
    .rr0(vmb_SW3__rr0[256:0]),
    .rq1(hb_dbk_SW__rq[67:51]),
    .rr1(vmb_SW3__rr1[256:0]),
    .rq2(xl_SW_ctl__rq[67:51]),
    .rr2(vmb_SW3__rr2[256:0]),
    .rq3(hcollrs_SW__vm_rq[67:51]),
    .rr3(vmb_SW3__rr3[256:0]),
    .rq4(hb_idx__ctl__vm_rq[67:51]),
    .rr4(vmb_SW3__rr4[256:0]),
    .wq0(su_SW1__lg_wq[561:281]),
    .wq_done0(vmb_SW3__wq_done0[0:0]),
    .wq1(smw_SW__wq_s3[280:0]),
    .wq_done1(vmb_SW3__wq_done1[0:0]),
    .bid(3'b011),
    .sid(2'b00),
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_e(hb_ckgen__pll_stream[0:0]),
    .clk_w(hb_ckgen__pll_stream[0:0]),
    .clk_macro0(hb_ckgen__pll_stream[0:0]),
    .clk_macro1(hb_ckgen__pll_stream[0:0]),
    .clk_macro2(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__vmb_SW3__rst_n[0:0]),
    .rslot_v(calendar_SW__rslot_v[3:3]),
    .rslot(calendar_SW__rslot[11:9]),
    .wslot_v(calendar_SW__wslot_v[3:3]),
    .wslot(calendar_SW__wslot[11:9]),
    .dq(vmdel_SW3__dq[280:0]),
    .dq_done(vmb_SW3__dq_done[0:0]),
    .kq(hcollks_SW_p1__vm_kq[561:281]),
    .kq_done(vmb_SW3__kq_done[0:0]),
    .xq(hb_vms_SW__b3_xq[275:0]),
    .xq_done(vmb_SW3__xq_done[0:0]),
    .xq2(hb_vms_SW__b3_xq2[275:0]),
    .xq2_done(vmb_SW3__xq2_done[0:0]),
    .eg(vmb_SW3__eg[275:0]),
    .pq(hb_vms_SW__b3_pq[284:0]),
    .pr(vmb_SW3__pr[265:0]),
    .status(vmb_SW3__status[17:0])
  );
  hfd_vms_bank_native_q0_faces vmb_SW4 (
    .rq0(su_SW2__lg_rq[16:0]),
    .rr0(vmb_SW4__rr0[256:0]),
    .rq1(hb_dbk_SW__rq[84:68]),
    .rr1(vmb_SW4__rr1[256:0]),
    .rq2(xl_SW_ctl__rq[84:68]),
    .rr2(vmb_SW4__rr2[256:0]),
    .rq3(hcollrs_SW__vm_rq[84:68]),
    .rr3(vmb_SW4__rr3[256:0]),
    .rq4(hb_idx__ctl__vm_rq[84:68]),
    .rr4(vmb_SW4__rr4[256:0]),
    .wq0(su_SW2__lg_wq[280:0]),
    .wq_done0(vmb_SW4__wq_done0[0:0]),
    .wq1(smw_SW__wq_t0[280:0]),
    .wq_done1(vmb_SW4__wq_done1[0:0]),
    .bid(3'b100),
    .sid(2'b00),
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_e(hb_ckgen__pll_stream[0:0]),
    .clk_w(hb_ckgen__pll_stream[0:0]),
    .clk_macro0(hb_ckgen__pll_stream[0:0]),
    .clk_macro1(hb_ckgen__pll_stream[0:0]),
    .clk_macro2(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__vmb_SW4__rst_n[0:0]),
    .rslot_v(calendar_SW__rslot_v[4:4]),
    .rslot(calendar_SW__rslot[14:12]),
    .wslot_v(calendar_SW__wslot_v[4:4]),
    .wslot(calendar_SW__wslot[14:12]),
    .dq(vmdel_SW4__dq[280:0]),
    .dq_done(vmb_SW4__dq_done[0:0]),
    .kq(hcollks_SW_p2__vm_kq[280:0]),
    .kq_done(vmb_SW4__kq_done[0:0]),
    .xq(hb_vms_SW__b4_xq[275:0]),
    .xq_done(vmb_SW4__xq_done[0:0]),
    .xq2(hb_vms_SW__b4_xq2[275:0]),
    .xq2_done(vmb_SW4__xq2_done[0:0]),
    .eg(vmb_SW4__eg[275:0]),
    .pq(hb_vms_SW__b4_pq[284:0]),
    .pr(vmb_SW4__pr[265:0]),
    .status(vmb_SW4__status[17:0])
  );
  hfd_vms_bank_native_q0_faces vmb_SW5 (
    .rq0(su_SW2__lg_rq[33:17]),
    .rr0(vmb_SW5__rr0[256:0]),
    .rq1(hb_dbk_SW__rq[101:85]),
    .rr1(vmb_SW5__rr1[256:0]),
    .rq2(xl_SW_ctl__rq[101:85]),
    .rr2(vmb_SW5__rr2[256:0]),
    .rq3(hcollrs_SW__vm_rq[101:85]),
    .rr3(vmb_SW5__rr3[256:0]),
    .rq4(hb_idx__ctl__vm_rq[101:85]),
    .rr4(vmb_SW5__rr4[256:0]),
    .wq0(su_SW2__lg_wq[561:281]),
    .wq_done0(vmb_SW5__wq_done0[0:0]),
    .wq1(smw_SW__wq_t1[280:0]),
    .wq_done1(vmb_SW5__wq_done1[0:0]),
    .bid(3'b101),
    .sid(2'b00),
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_e(hb_ckgen__pll_stream[0:0]),
    .clk_w(hb_ckgen__pll_stream[0:0]),
    .clk_macro0(hb_ckgen__pll_stream[0:0]),
    .clk_macro1(hb_ckgen__pll_stream[0:0]),
    .clk_macro2(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__vmb_SW5__rst_n[0:0]),
    .rslot_v(calendar_SW__rslot_v[5:5]),
    .rslot(calendar_SW__rslot[17:15]),
    .wslot_v(calendar_SW__wslot_v[5:5]),
    .wslot(calendar_SW__wslot[17:15]),
    .dq(vmdel_SW5__dq[280:0]),
    .dq_done(vmb_SW5__dq_done[0:0]),
    .kq(hcollks_SW_p2__vm_kq[561:281]),
    .kq_done(vmb_SW5__kq_done[0:0]),
    .xq(hb_vms_SW__b5_xq[275:0]),
    .xq_done(vmb_SW5__xq_done[0:0]),
    .xq2(hb_vms_SW__b5_xq2[275:0]),
    .xq2_done(vmb_SW5__xq2_done[0:0]),
    .eg(vmb_SW5__eg[275:0]),
    .pq(hb_vms_SW__b5_pq[284:0]),
    .pr(vmb_SW5__pr[265:0]),
    .status(vmb_SW5__status[17:0])
  );
  hfd_vms_bank_native_q0_faces vmb_SW6 (
    .rq0(su_SW3__lg_rq[16:0]),
    .rr0(vmb_SW6__rr0[256:0]),
    .rq1(hb_dbk_SW__rq[118:102]),
    .rr1(vmb_SW6__rr1[256:0]),
    .rq2(xl_SW_ctl__rq[118:102]),
    .rr2(vmb_SW6__rr2[256:0]),
    .rq3(hcollrs_SW__vm_rq[118:102]),
    .rr3(vmb_SW6__rr3[256:0]),
    .rq4(hb_idx__ctl__vm_rq[118:102]),
    .rr4(vmb_SW6__rr4[256:0]),
    .wq0(su_SW3__lg_wq[280:0]),
    .wq_done0(vmb_SW6__wq_done0[0:0]),
    .wq1(smw_SW__wq_t2[280:0]),
    .wq_done1(vmb_SW6__wq_done1[0:0]),
    .bid(3'b110),
    .sid(2'b00),
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_e(hb_ckgen__pll_stream[0:0]),
    .clk_w(hb_ckgen__pll_stream[0:0]),
    .clk_macro0(hb_ckgen__pll_stream[0:0]),
    .clk_macro1(hb_ckgen__pll_stream[0:0]),
    .clk_macro2(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__vmb_SW6__rst_n[0:0]),
    .rslot_v(calendar_SW__rslot_v[6:6]),
    .rslot(calendar_SW__rslot[20:18]),
    .wslot_v(calendar_SW__wslot_v[6:6]),
    .wslot(calendar_SW__wslot[20:18]),
    .dq(vmdel_SW6__dq[280:0]),
    .dq_done(vmb_SW6__dq_done[0:0]),
    .kq(hcollks_SW_p3__vm_kq[280:0]),
    .kq_done(vmb_SW6__kq_done[0:0]),
    .xq(hb_vms_SW__b6_xq[275:0]),
    .xq_done(vmb_SW6__xq_done[0:0]),
    .xq2(hb_vms_SW__b6_xq2[275:0]),
    .xq2_done(vmb_SW6__xq2_done[0:0]),
    .eg(vmb_SW6__eg[275:0]),
    .pq(hb_vms_SW__b6_pq[284:0]),
    .pr(vmb_SW6__pr[265:0]),
    .status(vmb_SW6__status[17:0])
  );
  hfd_vms_bank_native_q0_faces vmb_SW7 (
    .rq0(su_SW3__lg_rq[33:17]),
    .rr0(vmb_SW7__rr0[256:0]),
    .rq1(hb_dbk_SW__rq[135:119]),
    .rr1(vmb_SW7__rr1[256:0]),
    .rq2(xl_SW_ctl__rq[135:119]),
    .rr2(vmb_SW7__rr2[256:0]),
    .rq3(hcollrs_SW__vm_rq[135:119]),
    .rr3(vmb_SW7__rr3[256:0]),
    .rq4(hb_idx__ctl__vm_rq[135:119]),
    .rr4(vmb_SW7__rr4[256:0]),
    .wq0(su_SW3__lg_wq[561:281]),
    .wq_done0(vmb_SW7__wq_done0[0:0]),
    .wq1(smw_SW__wq_t3[280:0]),
    .wq_done1(vmb_SW7__wq_done1[0:0]),
    .bid(3'b111),
    .sid(2'b00),
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_e(hb_ckgen__pll_stream[0:0]),
    .clk_w(hb_ckgen__pll_stream[0:0]),
    .clk_macro0(hb_ckgen__pll_stream[0:0]),
    .clk_macro1(hb_ckgen__pll_stream[0:0]),
    .clk_macro2(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__vmb_SW7__rst_n[0:0]),
    .rslot_v(calendar_SW__rslot_v[7:7]),
    .rslot(calendar_SW__rslot[23:21]),
    .wslot_v(calendar_SW__wslot_v[7:7]),
    .wslot(calendar_SW__wslot[23:21]),
    .dq(vmdel_SW7__dq[280:0]),
    .dq_done(vmb_SW7__dq_done[0:0]),
    .kq(hcollks_SW_p3__vm_kq[561:281]),
    .kq_done(vmb_SW7__kq_done[0:0]),
    .xq(hb_vms_SW__b7_xq[275:0]),
    .xq_done(vmb_SW7__xq_done[0:0]),
    .xq2(hb_vms_SW__b7_xq2[275:0]),
    .xq2_done(vmb_SW7__xq2_done[0:0]),
    .eg(vmb_SW7__eg[275:0]),
    .pq(hb_vms_SW__b7_pq[284:0]),
    .pr(vmb_SW7__pr[265:0]),
    .status(vmb_SW7__status[17:0])
  );
  ot_hbm_svc_vmdel_lane_n #(.NPC(2)) vmdel_NE0 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .bank_id(3'b000),
    .begin_v_i(vmfc_NE__payload[0:0]),
    .begin_bank_i(vmfc_NE__payload[1:1]),
    .begin_epoch_i(vmfc_NE__payload[17:2]),
    .start_i(vmfc_NE__payload[18:18]),
    .start_bank_i(vmfc_NE__payload[19:19]),
    .start_epoch_i(vmfc_NE__payload[35:20]),
    .start_base_sector_i(vmfc_NE__payload[51:36]),
    .fill_v_i({vmks_NW6__fill_v[0:0], vmks_NW4__fill_v[0:0]}),
    .fill_bank_i({vmks_NW6__fill_bank[0:0], vmks_NW4__fill_bank[0:0]}),
    .fill_slot_i({vmks_NW6__fill_slot[5:0], vmks_NW4__fill_slot[5:0]}),
    .fill_epoch_i({vmks_NW6__fill_epoch[15:0], vmks_NW4__fill_epoch[15:0]}),
    .fill_data_i({vmks_NW6__fill_data[255:0], vmks_NW4__fill_data[255:0]}),
    .full0_all({vmdel_NE7__full0[0:0], vmdel_NE6__full0[0:0], vmdel_NE5__full0[0:0], vmdel_NE4__full0[0:0], vmdel_NE3__full0[0:0], vmdel_NE2__full0[0:0], vmdel_NE1__full0[0:0], vmdel_NE0__full0[0:0]}),
    .full1_all({vmdel_NE7__full1[0:0], vmdel_NE6__full1[0:0], vmdel_NE5__full1[0:0], vmdel_NE4__full1[0:0], vmdel_NE3__full1[0:0], vmdel_NE2__full1[0:0], vmdel_NE1__full1[0:0], vmdel_NE0__full1[0:0]}),
    .pcbad_all({vmdel_NE7__pcbad[0:0], vmdel_NE6__pcbad[0:0], vmdel_NE5__pcbad[0:0], vmdel_NE4__pcbad[0:0], vmdel_NE3__pcbad[0:0], vmdel_NE2__pcbad[0:0], vmdel_NE1__pcbad[0:0], vmdel_NE0__pcbad[0:0]}),
    .full0(vmdel_NE0__full0[0:0]),
    .full1(vmdel_NE0__full1[0:0]),
    .pcbad(vmdel_NE0__pcbad[0:0]),
    .block_ready(vmdel_NE0__block_ready[1:0]),
    .busy(vmdel_NE0__busy[0:0]),
    .fault(vmdel_NE0__fault[0:0]),
    .dq(vmdel_NE0__dq[280:0])
  );
  ot_hbm_svc_vmdel_lane_n #(.NPC(2)) vmdel_NE1 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .bank_id(3'b001),
    .begin_v_i(vmfc_NE__payload[0:0]),
    .begin_bank_i(vmfc_NE__payload[1:1]),
    .begin_epoch_i(vmfc_NE__payload[17:2]),
    .start_i(vmfc_NE__payload[18:18]),
    .start_bank_i(vmfc_NE__payload[19:19]),
    .start_epoch_i(vmfc_NE__payload[35:20]),
    .start_base_sector_i(vmfc_NE__payload[51:36]),
    .fill_v_i({vmks_NW6__fill_v[1:1], vmks_NW4__fill_v[1:1]}),
    .fill_bank_i({vmks_NW6__fill_bank[1:1], vmks_NW4__fill_bank[1:1]}),
    .fill_slot_i({vmks_NW6__fill_slot[11:6], vmks_NW4__fill_slot[11:6]}),
    .fill_epoch_i({vmks_NW6__fill_epoch[31:16], vmks_NW4__fill_epoch[31:16]}),
    .fill_data_i({vmks_NW6__fill_data[511:256], vmks_NW4__fill_data[511:256]}),
    .full0_all({vmdel_NE7__full0[0:0], vmdel_NE6__full0[0:0], vmdel_NE5__full0[0:0], vmdel_NE4__full0[0:0], vmdel_NE3__full0[0:0], vmdel_NE2__full0[0:0], vmdel_NE1__full0[0:0], vmdel_NE0__full0[0:0]}),
    .full1_all({vmdel_NE7__full1[0:0], vmdel_NE6__full1[0:0], vmdel_NE5__full1[0:0], vmdel_NE4__full1[0:0], vmdel_NE3__full1[0:0], vmdel_NE2__full1[0:0], vmdel_NE1__full1[0:0], vmdel_NE0__full1[0:0]}),
    .pcbad_all({vmdel_NE7__pcbad[0:0], vmdel_NE6__pcbad[0:0], vmdel_NE5__pcbad[0:0], vmdel_NE4__pcbad[0:0], vmdel_NE3__pcbad[0:0], vmdel_NE2__pcbad[0:0], vmdel_NE1__pcbad[0:0], vmdel_NE0__pcbad[0:0]}),
    .full0(vmdel_NE1__full0[0:0]),
    .full1(vmdel_NE1__full1[0:0]),
    .pcbad(vmdel_NE1__pcbad[0:0]),
    .block_ready(vmdel_NE1__block_ready[1:0]),
    .busy(vmdel_NE1__busy[0:0]),
    .fault(vmdel_NE1__fault[0:0]),
    .dq(vmdel_NE1__dq[280:0])
  );
  ot_hbm_svc_vmdel_lane_n #(.NPC(2)) vmdel_NE2 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .bank_id(3'b010),
    .begin_v_i(vmfc_NE__payload[0:0]),
    .begin_bank_i(vmfc_NE__payload[1:1]),
    .begin_epoch_i(vmfc_NE__payload[17:2]),
    .start_i(vmfc_NE__payload[18:18]),
    .start_bank_i(vmfc_NE__payload[19:19]),
    .start_epoch_i(vmfc_NE__payload[35:20]),
    .start_base_sector_i(vmfc_NE__payload[51:36]),
    .fill_v_i({vmks_NW6__fill_v[2:2], vmks_NW4__fill_v[2:2]}),
    .fill_bank_i({vmks_NW6__fill_bank[2:2], vmks_NW4__fill_bank[2:2]}),
    .fill_slot_i({vmks_NW6__fill_slot[17:12], vmks_NW4__fill_slot[17:12]}),
    .fill_epoch_i({vmks_NW6__fill_epoch[47:32], vmks_NW4__fill_epoch[47:32]}),
    .fill_data_i({vmks_NW6__fill_data[767:512], vmks_NW4__fill_data[767:512]}),
    .full0_all({vmdel_NE7__full0[0:0], vmdel_NE6__full0[0:0], vmdel_NE5__full0[0:0], vmdel_NE4__full0[0:0], vmdel_NE3__full0[0:0], vmdel_NE2__full0[0:0], vmdel_NE1__full0[0:0], vmdel_NE0__full0[0:0]}),
    .full1_all({vmdel_NE7__full1[0:0], vmdel_NE6__full1[0:0], vmdel_NE5__full1[0:0], vmdel_NE4__full1[0:0], vmdel_NE3__full1[0:0], vmdel_NE2__full1[0:0], vmdel_NE1__full1[0:0], vmdel_NE0__full1[0:0]}),
    .pcbad_all({vmdel_NE7__pcbad[0:0], vmdel_NE6__pcbad[0:0], vmdel_NE5__pcbad[0:0], vmdel_NE4__pcbad[0:0], vmdel_NE3__pcbad[0:0], vmdel_NE2__pcbad[0:0], vmdel_NE1__pcbad[0:0], vmdel_NE0__pcbad[0:0]}),
    .full0(vmdel_NE2__full0[0:0]),
    .full1(vmdel_NE2__full1[0:0]),
    .pcbad(vmdel_NE2__pcbad[0:0]),
    .block_ready(vmdel_NE2__block_ready[1:0]),
    .busy(vmdel_NE2__busy[0:0]),
    .fault(vmdel_NE2__fault[0:0]),
    .dq(vmdel_NE2__dq[280:0])
  );
  ot_hbm_svc_vmdel_lane_n #(.NPC(2)) vmdel_NE3 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .bank_id(3'b011),
    .begin_v_i(vmfc_NE__payload[0:0]),
    .begin_bank_i(vmfc_NE__payload[1:1]),
    .begin_epoch_i(vmfc_NE__payload[17:2]),
    .start_i(vmfc_NE__payload[18:18]),
    .start_bank_i(vmfc_NE__payload[19:19]),
    .start_epoch_i(vmfc_NE__payload[35:20]),
    .start_base_sector_i(vmfc_NE__payload[51:36]),
    .fill_v_i({vmks_NW6__fill_v[3:3], vmks_NW4__fill_v[3:3]}),
    .fill_bank_i({vmks_NW6__fill_bank[3:3], vmks_NW4__fill_bank[3:3]}),
    .fill_slot_i({vmks_NW6__fill_slot[23:18], vmks_NW4__fill_slot[23:18]}),
    .fill_epoch_i({vmks_NW6__fill_epoch[63:48], vmks_NW4__fill_epoch[63:48]}),
    .fill_data_i({vmks_NW6__fill_data[1023:768], vmks_NW4__fill_data[1023:768]}),
    .full0_all({vmdel_NE7__full0[0:0], vmdel_NE6__full0[0:0], vmdel_NE5__full0[0:0], vmdel_NE4__full0[0:0], vmdel_NE3__full0[0:0], vmdel_NE2__full0[0:0], vmdel_NE1__full0[0:0], vmdel_NE0__full0[0:0]}),
    .full1_all({vmdel_NE7__full1[0:0], vmdel_NE6__full1[0:0], vmdel_NE5__full1[0:0], vmdel_NE4__full1[0:0], vmdel_NE3__full1[0:0], vmdel_NE2__full1[0:0], vmdel_NE1__full1[0:0], vmdel_NE0__full1[0:0]}),
    .pcbad_all({vmdel_NE7__pcbad[0:0], vmdel_NE6__pcbad[0:0], vmdel_NE5__pcbad[0:0], vmdel_NE4__pcbad[0:0], vmdel_NE3__pcbad[0:0], vmdel_NE2__pcbad[0:0], vmdel_NE1__pcbad[0:0], vmdel_NE0__pcbad[0:0]}),
    .full0(vmdel_NE3__full0[0:0]),
    .full1(vmdel_NE3__full1[0:0]),
    .pcbad(vmdel_NE3__pcbad[0:0]),
    .block_ready(vmdel_NE3__block_ready[1:0]),
    .busy(vmdel_NE3__busy[0:0]),
    .fault(vmdel_NE3__fault[0:0]),
    .dq(vmdel_NE3__dq[280:0])
  );
  ot_hbm_svc_vmdel_lane_n #(.NPC(2)) vmdel_NE4 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .bank_id(3'b100),
    .begin_v_i(vmfc_NE__payload[0:0]),
    .begin_bank_i(vmfc_NE__payload[1:1]),
    .begin_epoch_i(vmfc_NE__payload[17:2]),
    .start_i(vmfc_NE__payload[18:18]),
    .start_bank_i(vmfc_NE__payload[19:19]),
    .start_epoch_i(vmfc_NE__payload[35:20]),
    .start_base_sector_i(vmfc_NE__payload[51:36]),
    .fill_v_i({vmks_NW7__fill_v[0:0], vmks_NW5__fill_v[0:0]}),
    .fill_bank_i({vmks_NW7__fill_bank[0:0], vmks_NW5__fill_bank[0:0]}),
    .fill_slot_i({vmks_NW7__fill_slot[5:0], vmks_NW5__fill_slot[5:0]}),
    .fill_epoch_i({vmks_NW7__fill_epoch[15:0], vmks_NW5__fill_epoch[15:0]}),
    .fill_data_i({vmks_NW7__fill_data[255:0], vmks_NW5__fill_data[255:0]}),
    .full0_all({vmdel_NE7__full0[0:0], vmdel_NE6__full0[0:0], vmdel_NE5__full0[0:0], vmdel_NE4__full0[0:0], vmdel_NE3__full0[0:0], vmdel_NE2__full0[0:0], vmdel_NE1__full0[0:0], vmdel_NE0__full0[0:0]}),
    .full1_all({vmdel_NE7__full1[0:0], vmdel_NE6__full1[0:0], vmdel_NE5__full1[0:0], vmdel_NE4__full1[0:0], vmdel_NE3__full1[0:0], vmdel_NE2__full1[0:0], vmdel_NE1__full1[0:0], vmdel_NE0__full1[0:0]}),
    .pcbad_all({vmdel_NE7__pcbad[0:0], vmdel_NE6__pcbad[0:0], vmdel_NE5__pcbad[0:0], vmdel_NE4__pcbad[0:0], vmdel_NE3__pcbad[0:0], vmdel_NE2__pcbad[0:0], vmdel_NE1__pcbad[0:0], vmdel_NE0__pcbad[0:0]}),
    .full0(vmdel_NE4__full0[0:0]),
    .full1(vmdel_NE4__full1[0:0]),
    .pcbad(vmdel_NE4__pcbad[0:0]),
    .block_ready(vmdel_NE4__block_ready[1:0]),
    .busy(vmdel_NE4__busy[0:0]),
    .fault(vmdel_NE4__fault[0:0]),
    .dq(vmdel_NE4__dq[280:0])
  );
  ot_hbm_svc_vmdel_lane_n #(.NPC(2)) vmdel_NE5 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .bank_id(3'b101),
    .begin_v_i(vmfc_NE__payload[0:0]),
    .begin_bank_i(vmfc_NE__payload[1:1]),
    .begin_epoch_i(vmfc_NE__payload[17:2]),
    .start_i(vmfc_NE__payload[18:18]),
    .start_bank_i(vmfc_NE__payload[19:19]),
    .start_epoch_i(vmfc_NE__payload[35:20]),
    .start_base_sector_i(vmfc_NE__payload[51:36]),
    .fill_v_i({vmks_NW7__fill_v[1:1], vmks_NW5__fill_v[1:1]}),
    .fill_bank_i({vmks_NW7__fill_bank[1:1], vmks_NW5__fill_bank[1:1]}),
    .fill_slot_i({vmks_NW7__fill_slot[11:6], vmks_NW5__fill_slot[11:6]}),
    .fill_epoch_i({vmks_NW7__fill_epoch[31:16], vmks_NW5__fill_epoch[31:16]}),
    .fill_data_i({vmks_NW7__fill_data[511:256], vmks_NW5__fill_data[511:256]}),
    .full0_all({vmdel_NE7__full0[0:0], vmdel_NE6__full0[0:0], vmdel_NE5__full0[0:0], vmdel_NE4__full0[0:0], vmdel_NE3__full0[0:0], vmdel_NE2__full0[0:0], vmdel_NE1__full0[0:0], vmdel_NE0__full0[0:0]}),
    .full1_all({vmdel_NE7__full1[0:0], vmdel_NE6__full1[0:0], vmdel_NE5__full1[0:0], vmdel_NE4__full1[0:0], vmdel_NE3__full1[0:0], vmdel_NE2__full1[0:0], vmdel_NE1__full1[0:0], vmdel_NE0__full1[0:0]}),
    .pcbad_all({vmdel_NE7__pcbad[0:0], vmdel_NE6__pcbad[0:0], vmdel_NE5__pcbad[0:0], vmdel_NE4__pcbad[0:0], vmdel_NE3__pcbad[0:0], vmdel_NE2__pcbad[0:0], vmdel_NE1__pcbad[0:0], vmdel_NE0__pcbad[0:0]}),
    .full0(vmdel_NE5__full0[0:0]),
    .full1(vmdel_NE5__full1[0:0]),
    .pcbad(vmdel_NE5__pcbad[0:0]),
    .block_ready(vmdel_NE5__block_ready[1:0]),
    .busy(vmdel_NE5__busy[0:0]),
    .fault(vmdel_NE5__fault[0:0]),
    .dq(vmdel_NE5__dq[280:0])
  );
  ot_hbm_svc_vmdel_lane_n #(.NPC(2)) vmdel_NE6 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .bank_id(3'b110),
    .begin_v_i(vmfc_NE__payload[0:0]),
    .begin_bank_i(vmfc_NE__payload[1:1]),
    .begin_epoch_i(vmfc_NE__payload[17:2]),
    .start_i(vmfc_NE__payload[18:18]),
    .start_bank_i(vmfc_NE__payload[19:19]),
    .start_epoch_i(vmfc_NE__payload[35:20]),
    .start_base_sector_i(vmfc_NE__payload[51:36]),
    .fill_v_i({vmks_NW7__fill_v[2:2], vmks_NW5__fill_v[2:2]}),
    .fill_bank_i({vmks_NW7__fill_bank[2:2], vmks_NW5__fill_bank[2:2]}),
    .fill_slot_i({vmks_NW7__fill_slot[17:12], vmks_NW5__fill_slot[17:12]}),
    .fill_epoch_i({vmks_NW7__fill_epoch[47:32], vmks_NW5__fill_epoch[47:32]}),
    .fill_data_i({vmks_NW7__fill_data[767:512], vmks_NW5__fill_data[767:512]}),
    .full0_all({vmdel_NE7__full0[0:0], vmdel_NE6__full0[0:0], vmdel_NE5__full0[0:0], vmdel_NE4__full0[0:0], vmdel_NE3__full0[0:0], vmdel_NE2__full0[0:0], vmdel_NE1__full0[0:0], vmdel_NE0__full0[0:0]}),
    .full1_all({vmdel_NE7__full1[0:0], vmdel_NE6__full1[0:0], vmdel_NE5__full1[0:0], vmdel_NE4__full1[0:0], vmdel_NE3__full1[0:0], vmdel_NE2__full1[0:0], vmdel_NE1__full1[0:0], vmdel_NE0__full1[0:0]}),
    .pcbad_all({vmdel_NE7__pcbad[0:0], vmdel_NE6__pcbad[0:0], vmdel_NE5__pcbad[0:0], vmdel_NE4__pcbad[0:0], vmdel_NE3__pcbad[0:0], vmdel_NE2__pcbad[0:0], vmdel_NE1__pcbad[0:0], vmdel_NE0__pcbad[0:0]}),
    .full0(vmdel_NE6__full0[0:0]),
    .full1(vmdel_NE6__full1[0:0]),
    .pcbad(vmdel_NE6__pcbad[0:0]),
    .block_ready(vmdel_NE6__block_ready[1:0]),
    .busy(vmdel_NE6__busy[0:0]),
    .fault(vmdel_NE6__fault[0:0]),
    .dq(vmdel_NE6__dq[280:0])
  );
  ot_hbm_svc_vmdel_lane_n #(.NPC(2)) vmdel_NE7 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .bank_id(3'b111),
    .begin_v_i(vmfc_NE__payload[0:0]),
    .begin_bank_i(vmfc_NE__payload[1:1]),
    .begin_epoch_i(vmfc_NE__payload[17:2]),
    .start_i(vmfc_NE__payload[18:18]),
    .start_bank_i(vmfc_NE__payload[19:19]),
    .start_epoch_i(vmfc_NE__payload[35:20]),
    .start_base_sector_i(vmfc_NE__payload[51:36]),
    .fill_v_i({vmks_NW7__fill_v[3:3], vmks_NW5__fill_v[3:3]}),
    .fill_bank_i({vmks_NW7__fill_bank[3:3], vmks_NW5__fill_bank[3:3]}),
    .fill_slot_i({vmks_NW7__fill_slot[23:18], vmks_NW5__fill_slot[23:18]}),
    .fill_epoch_i({vmks_NW7__fill_epoch[63:48], vmks_NW5__fill_epoch[63:48]}),
    .fill_data_i({vmks_NW7__fill_data[1023:768], vmks_NW5__fill_data[1023:768]}),
    .full0_all({vmdel_NE7__full0[0:0], vmdel_NE6__full0[0:0], vmdel_NE5__full0[0:0], vmdel_NE4__full0[0:0], vmdel_NE3__full0[0:0], vmdel_NE2__full0[0:0], vmdel_NE1__full0[0:0], vmdel_NE0__full0[0:0]}),
    .full1_all({vmdel_NE7__full1[0:0], vmdel_NE6__full1[0:0], vmdel_NE5__full1[0:0], vmdel_NE4__full1[0:0], vmdel_NE3__full1[0:0], vmdel_NE2__full1[0:0], vmdel_NE1__full1[0:0], vmdel_NE0__full1[0:0]}),
    .pcbad_all({vmdel_NE7__pcbad[0:0], vmdel_NE6__pcbad[0:0], vmdel_NE5__pcbad[0:0], vmdel_NE4__pcbad[0:0], vmdel_NE3__pcbad[0:0], vmdel_NE2__pcbad[0:0], vmdel_NE1__pcbad[0:0], vmdel_NE0__pcbad[0:0]}),
    .full0(vmdel_NE7__full0[0:0]),
    .full1(vmdel_NE7__full1[0:0]),
    .pcbad(vmdel_NE7__pcbad[0:0]),
    .block_ready(vmdel_NE7__block_ready[1:0]),
    .busy(vmdel_NE7__busy[0:0]),
    .fault(vmdel_NE7__fault[0:0]),
    .dq(vmdel_NE7__dq[280:0])
  );
  ot_hbm_svc_vmdel_lane_n #(.NPC(2)) vmdel_NW0 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .bank_id(3'b000),
    .begin_v_i(vmfc_NW__payload[0:0]),
    .begin_bank_i(vmfc_NW__payload[1:1]),
    .begin_epoch_i(vmfc_NW__payload[17:2]),
    .start_i(vmfc_NW__payload[18:18]),
    .start_bank_i(vmfc_NW__payload[19:19]),
    .start_epoch_i(vmfc_NW__payload[35:20]),
    .start_base_sector_i(vmfc_NW__payload[51:36]),
    .fill_v_i({vmks_NW2__fill_v[0:0], vmks_NW0__fill_v[0:0]}),
    .fill_bank_i({vmks_NW2__fill_bank[0:0], vmks_NW0__fill_bank[0:0]}),
    .fill_slot_i({vmks_NW2__fill_slot[5:0], vmks_NW0__fill_slot[5:0]}),
    .fill_epoch_i({vmks_NW2__fill_epoch[15:0], vmks_NW0__fill_epoch[15:0]}),
    .fill_data_i({vmks_NW2__fill_data[255:0], vmks_NW0__fill_data[255:0]}),
    .full0_all({vmdel_NW7__full0[0:0], vmdel_NW6__full0[0:0], vmdel_NW5__full0[0:0], vmdel_NW4__full0[0:0], vmdel_NW3__full0[0:0], vmdel_NW2__full0[0:0], vmdel_NW1__full0[0:0], vmdel_NW0__full0[0:0]}),
    .full1_all({vmdel_NW7__full1[0:0], vmdel_NW6__full1[0:0], vmdel_NW5__full1[0:0], vmdel_NW4__full1[0:0], vmdel_NW3__full1[0:0], vmdel_NW2__full1[0:0], vmdel_NW1__full1[0:0], vmdel_NW0__full1[0:0]}),
    .pcbad_all({vmdel_NW7__pcbad[0:0], vmdel_NW6__pcbad[0:0], vmdel_NW5__pcbad[0:0], vmdel_NW4__pcbad[0:0], vmdel_NW3__pcbad[0:0], vmdel_NW2__pcbad[0:0], vmdel_NW1__pcbad[0:0], vmdel_NW0__pcbad[0:0]}),
    .full0(vmdel_NW0__full0[0:0]),
    .full1(vmdel_NW0__full1[0:0]),
    .pcbad(vmdel_NW0__pcbad[0:0]),
    .block_ready(vmdel_NW0__block_ready[1:0]),
    .busy(vmdel_NW0__busy[0:0]),
    .fault(vmdel_NW0__fault[0:0]),
    .dq(vmdel_NW0__dq[280:0])
  );
  ot_hbm_svc_vmdel_lane_n #(.NPC(2)) vmdel_NW1 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .bank_id(3'b001),
    .begin_v_i(vmfc_NW__payload[0:0]),
    .begin_bank_i(vmfc_NW__payload[1:1]),
    .begin_epoch_i(vmfc_NW__payload[17:2]),
    .start_i(vmfc_NW__payload[18:18]),
    .start_bank_i(vmfc_NW__payload[19:19]),
    .start_epoch_i(vmfc_NW__payload[35:20]),
    .start_base_sector_i(vmfc_NW__payload[51:36]),
    .fill_v_i({vmks_NW2__fill_v[1:1], vmks_NW0__fill_v[1:1]}),
    .fill_bank_i({vmks_NW2__fill_bank[1:1], vmks_NW0__fill_bank[1:1]}),
    .fill_slot_i({vmks_NW2__fill_slot[11:6], vmks_NW0__fill_slot[11:6]}),
    .fill_epoch_i({vmks_NW2__fill_epoch[31:16], vmks_NW0__fill_epoch[31:16]}),
    .fill_data_i({vmks_NW2__fill_data[511:256], vmks_NW0__fill_data[511:256]}),
    .full0_all({vmdel_NW7__full0[0:0], vmdel_NW6__full0[0:0], vmdel_NW5__full0[0:0], vmdel_NW4__full0[0:0], vmdel_NW3__full0[0:0], vmdel_NW2__full0[0:0], vmdel_NW1__full0[0:0], vmdel_NW0__full0[0:0]}),
    .full1_all({vmdel_NW7__full1[0:0], vmdel_NW6__full1[0:0], vmdel_NW5__full1[0:0], vmdel_NW4__full1[0:0], vmdel_NW3__full1[0:0], vmdel_NW2__full1[0:0], vmdel_NW1__full1[0:0], vmdel_NW0__full1[0:0]}),
    .pcbad_all({vmdel_NW7__pcbad[0:0], vmdel_NW6__pcbad[0:0], vmdel_NW5__pcbad[0:0], vmdel_NW4__pcbad[0:0], vmdel_NW3__pcbad[0:0], vmdel_NW2__pcbad[0:0], vmdel_NW1__pcbad[0:0], vmdel_NW0__pcbad[0:0]}),
    .full0(vmdel_NW1__full0[0:0]),
    .full1(vmdel_NW1__full1[0:0]),
    .pcbad(vmdel_NW1__pcbad[0:0]),
    .block_ready(vmdel_NW1__block_ready[1:0]),
    .busy(vmdel_NW1__busy[0:0]),
    .fault(vmdel_NW1__fault[0:0]),
    .dq(vmdel_NW1__dq[280:0])
  );
  ot_hbm_svc_vmdel_lane_n #(.NPC(2)) vmdel_NW2 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .bank_id(3'b010),
    .begin_v_i(vmfc_NW__payload[0:0]),
    .begin_bank_i(vmfc_NW__payload[1:1]),
    .begin_epoch_i(vmfc_NW__payload[17:2]),
    .start_i(vmfc_NW__payload[18:18]),
    .start_bank_i(vmfc_NW__payload[19:19]),
    .start_epoch_i(vmfc_NW__payload[35:20]),
    .start_base_sector_i(vmfc_NW__payload[51:36]),
    .fill_v_i({vmks_NW2__fill_v[2:2], vmks_NW0__fill_v[2:2]}),
    .fill_bank_i({vmks_NW2__fill_bank[2:2], vmks_NW0__fill_bank[2:2]}),
    .fill_slot_i({vmks_NW2__fill_slot[17:12], vmks_NW0__fill_slot[17:12]}),
    .fill_epoch_i({vmks_NW2__fill_epoch[47:32], vmks_NW0__fill_epoch[47:32]}),
    .fill_data_i({vmks_NW2__fill_data[767:512], vmks_NW0__fill_data[767:512]}),
    .full0_all({vmdel_NW7__full0[0:0], vmdel_NW6__full0[0:0], vmdel_NW5__full0[0:0], vmdel_NW4__full0[0:0], vmdel_NW3__full0[0:0], vmdel_NW2__full0[0:0], vmdel_NW1__full0[0:0], vmdel_NW0__full0[0:0]}),
    .full1_all({vmdel_NW7__full1[0:0], vmdel_NW6__full1[0:0], vmdel_NW5__full1[0:0], vmdel_NW4__full1[0:0], vmdel_NW3__full1[0:0], vmdel_NW2__full1[0:0], vmdel_NW1__full1[0:0], vmdel_NW0__full1[0:0]}),
    .pcbad_all({vmdel_NW7__pcbad[0:0], vmdel_NW6__pcbad[0:0], vmdel_NW5__pcbad[0:0], vmdel_NW4__pcbad[0:0], vmdel_NW3__pcbad[0:0], vmdel_NW2__pcbad[0:0], vmdel_NW1__pcbad[0:0], vmdel_NW0__pcbad[0:0]}),
    .full0(vmdel_NW2__full0[0:0]),
    .full1(vmdel_NW2__full1[0:0]),
    .pcbad(vmdel_NW2__pcbad[0:0]),
    .block_ready(vmdel_NW2__block_ready[1:0]),
    .busy(vmdel_NW2__busy[0:0]),
    .fault(vmdel_NW2__fault[0:0]),
    .dq(vmdel_NW2__dq[280:0])
  );
  ot_hbm_svc_vmdel_lane_n #(.NPC(2)) vmdel_NW3 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .bank_id(3'b011),
    .begin_v_i(vmfc_NW__payload[0:0]),
    .begin_bank_i(vmfc_NW__payload[1:1]),
    .begin_epoch_i(vmfc_NW__payload[17:2]),
    .start_i(vmfc_NW__payload[18:18]),
    .start_bank_i(vmfc_NW__payload[19:19]),
    .start_epoch_i(vmfc_NW__payload[35:20]),
    .start_base_sector_i(vmfc_NW__payload[51:36]),
    .fill_v_i({vmks_NW2__fill_v[3:3], vmks_NW0__fill_v[3:3]}),
    .fill_bank_i({vmks_NW2__fill_bank[3:3], vmks_NW0__fill_bank[3:3]}),
    .fill_slot_i({vmks_NW2__fill_slot[23:18], vmks_NW0__fill_slot[23:18]}),
    .fill_epoch_i({vmks_NW2__fill_epoch[63:48], vmks_NW0__fill_epoch[63:48]}),
    .fill_data_i({vmks_NW2__fill_data[1023:768], vmks_NW0__fill_data[1023:768]}),
    .full0_all({vmdel_NW7__full0[0:0], vmdel_NW6__full0[0:0], vmdel_NW5__full0[0:0], vmdel_NW4__full0[0:0], vmdel_NW3__full0[0:0], vmdel_NW2__full0[0:0], vmdel_NW1__full0[0:0], vmdel_NW0__full0[0:0]}),
    .full1_all({vmdel_NW7__full1[0:0], vmdel_NW6__full1[0:0], vmdel_NW5__full1[0:0], vmdel_NW4__full1[0:0], vmdel_NW3__full1[0:0], vmdel_NW2__full1[0:0], vmdel_NW1__full1[0:0], vmdel_NW0__full1[0:0]}),
    .pcbad_all({vmdel_NW7__pcbad[0:0], vmdel_NW6__pcbad[0:0], vmdel_NW5__pcbad[0:0], vmdel_NW4__pcbad[0:0], vmdel_NW3__pcbad[0:0], vmdel_NW2__pcbad[0:0], vmdel_NW1__pcbad[0:0], vmdel_NW0__pcbad[0:0]}),
    .full0(vmdel_NW3__full0[0:0]),
    .full1(vmdel_NW3__full1[0:0]),
    .pcbad(vmdel_NW3__pcbad[0:0]),
    .block_ready(vmdel_NW3__block_ready[1:0]),
    .busy(vmdel_NW3__busy[0:0]),
    .fault(vmdel_NW3__fault[0:0]),
    .dq(vmdel_NW3__dq[280:0])
  );
  ot_hbm_svc_vmdel_lane_n #(.NPC(2)) vmdel_NW4 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .bank_id(3'b100),
    .begin_v_i(vmfc_NW__payload[0:0]),
    .begin_bank_i(vmfc_NW__payload[1:1]),
    .begin_epoch_i(vmfc_NW__payload[17:2]),
    .start_i(vmfc_NW__payload[18:18]),
    .start_bank_i(vmfc_NW__payload[19:19]),
    .start_epoch_i(vmfc_NW__payload[35:20]),
    .start_base_sector_i(vmfc_NW__payload[51:36]),
    .fill_v_i({vmks_NW3__fill_v[0:0], vmks_NW1__fill_v[0:0]}),
    .fill_bank_i({vmks_NW3__fill_bank[0:0], vmks_NW1__fill_bank[0:0]}),
    .fill_slot_i({vmks_NW3__fill_slot[5:0], vmks_NW1__fill_slot[5:0]}),
    .fill_epoch_i({vmks_NW3__fill_epoch[15:0], vmks_NW1__fill_epoch[15:0]}),
    .fill_data_i({vmks_NW3__fill_data[255:0], vmks_NW1__fill_data[255:0]}),
    .full0_all({vmdel_NW7__full0[0:0], vmdel_NW6__full0[0:0], vmdel_NW5__full0[0:0], vmdel_NW4__full0[0:0], vmdel_NW3__full0[0:0], vmdel_NW2__full0[0:0], vmdel_NW1__full0[0:0], vmdel_NW0__full0[0:0]}),
    .full1_all({vmdel_NW7__full1[0:0], vmdel_NW6__full1[0:0], vmdel_NW5__full1[0:0], vmdel_NW4__full1[0:0], vmdel_NW3__full1[0:0], vmdel_NW2__full1[0:0], vmdel_NW1__full1[0:0], vmdel_NW0__full1[0:0]}),
    .pcbad_all({vmdel_NW7__pcbad[0:0], vmdel_NW6__pcbad[0:0], vmdel_NW5__pcbad[0:0], vmdel_NW4__pcbad[0:0], vmdel_NW3__pcbad[0:0], vmdel_NW2__pcbad[0:0], vmdel_NW1__pcbad[0:0], vmdel_NW0__pcbad[0:0]}),
    .full0(vmdel_NW4__full0[0:0]),
    .full1(vmdel_NW4__full1[0:0]),
    .pcbad(vmdel_NW4__pcbad[0:0]),
    .block_ready(vmdel_NW4__block_ready[1:0]),
    .busy(vmdel_NW4__busy[0:0]),
    .fault(vmdel_NW4__fault[0:0]),
    .dq(vmdel_NW4__dq[280:0])
  );
  ot_hbm_svc_vmdel_lane_n #(.NPC(2)) vmdel_NW5 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .bank_id(3'b101),
    .begin_v_i(vmfc_NW__payload[0:0]),
    .begin_bank_i(vmfc_NW__payload[1:1]),
    .begin_epoch_i(vmfc_NW__payload[17:2]),
    .start_i(vmfc_NW__payload[18:18]),
    .start_bank_i(vmfc_NW__payload[19:19]),
    .start_epoch_i(vmfc_NW__payload[35:20]),
    .start_base_sector_i(vmfc_NW__payload[51:36]),
    .fill_v_i({vmks_NW3__fill_v[1:1], vmks_NW1__fill_v[1:1]}),
    .fill_bank_i({vmks_NW3__fill_bank[1:1], vmks_NW1__fill_bank[1:1]}),
    .fill_slot_i({vmks_NW3__fill_slot[11:6], vmks_NW1__fill_slot[11:6]}),
    .fill_epoch_i({vmks_NW3__fill_epoch[31:16], vmks_NW1__fill_epoch[31:16]}),
    .fill_data_i({vmks_NW3__fill_data[511:256], vmks_NW1__fill_data[511:256]}),
    .full0_all({vmdel_NW7__full0[0:0], vmdel_NW6__full0[0:0], vmdel_NW5__full0[0:0], vmdel_NW4__full0[0:0], vmdel_NW3__full0[0:0], vmdel_NW2__full0[0:0], vmdel_NW1__full0[0:0], vmdel_NW0__full0[0:0]}),
    .full1_all({vmdel_NW7__full1[0:0], vmdel_NW6__full1[0:0], vmdel_NW5__full1[0:0], vmdel_NW4__full1[0:0], vmdel_NW3__full1[0:0], vmdel_NW2__full1[0:0], vmdel_NW1__full1[0:0], vmdel_NW0__full1[0:0]}),
    .pcbad_all({vmdel_NW7__pcbad[0:0], vmdel_NW6__pcbad[0:0], vmdel_NW5__pcbad[0:0], vmdel_NW4__pcbad[0:0], vmdel_NW3__pcbad[0:0], vmdel_NW2__pcbad[0:0], vmdel_NW1__pcbad[0:0], vmdel_NW0__pcbad[0:0]}),
    .full0(vmdel_NW5__full0[0:0]),
    .full1(vmdel_NW5__full1[0:0]),
    .pcbad(vmdel_NW5__pcbad[0:0]),
    .block_ready(vmdel_NW5__block_ready[1:0]),
    .busy(vmdel_NW5__busy[0:0]),
    .fault(vmdel_NW5__fault[0:0]),
    .dq(vmdel_NW5__dq[280:0])
  );
  ot_hbm_svc_vmdel_lane_n #(.NPC(2)) vmdel_NW6 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .bank_id(3'b110),
    .begin_v_i(vmfc_NW__payload[0:0]),
    .begin_bank_i(vmfc_NW__payload[1:1]),
    .begin_epoch_i(vmfc_NW__payload[17:2]),
    .start_i(vmfc_NW__payload[18:18]),
    .start_bank_i(vmfc_NW__payload[19:19]),
    .start_epoch_i(vmfc_NW__payload[35:20]),
    .start_base_sector_i(vmfc_NW__payload[51:36]),
    .fill_v_i({vmks_NW3__fill_v[2:2], vmks_NW1__fill_v[2:2]}),
    .fill_bank_i({vmks_NW3__fill_bank[2:2], vmks_NW1__fill_bank[2:2]}),
    .fill_slot_i({vmks_NW3__fill_slot[17:12], vmks_NW1__fill_slot[17:12]}),
    .fill_epoch_i({vmks_NW3__fill_epoch[47:32], vmks_NW1__fill_epoch[47:32]}),
    .fill_data_i({vmks_NW3__fill_data[767:512], vmks_NW1__fill_data[767:512]}),
    .full0_all({vmdel_NW7__full0[0:0], vmdel_NW6__full0[0:0], vmdel_NW5__full0[0:0], vmdel_NW4__full0[0:0], vmdel_NW3__full0[0:0], vmdel_NW2__full0[0:0], vmdel_NW1__full0[0:0], vmdel_NW0__full0[0:0]}),
    .full1_all({vmdel_NW7__full1[0:0], vmdel_NW6__full1[0:0], vmdel_NW5__full1[0:0], vmdel_NW4__full1[0:0], vmdel_NW3__full1[0:0], vmdel_NW2__full1[0:0], vmdel_NW1__full1[0:0], vmdel_NW0__full1[0:0]}),
    .pcbad_all({vmdel_NW7__pcbad[0:0], vmdel_NW6__pcbad[0:0], vmdel_NW5__pcbad[0:0], vmdel_NW4__pcbad[0:0], vmdel_NW3__pcbad[0:0], vmdel_NW2__pcbad[0:0], vmdel_NW1__pcbad[0:0], vmdel_NW0__pcbad[0:0]}),
    .full0(vmdel_NW6__full0[0:0]),
    .full1(vmdel_NW6__full1[0:0]),
    .pcbad(vmdel_NW6__pcbad[0:0]),
    .block_ready(vmdel_NW6__block_ready[1:0]),
    .busy(vmdel_NW6__busy[0:0]),
    .fault(vmdel_NW6__fault[0:0]),
    .dq(vmdel_NW6__dq[280:0])
  );
  ot_hbm_svc_vmdel_lane_n #(.NPC(2)) vmdel_NW7 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .bank_id(3'b111),
    .begin_v_i(vmfc_NW__payload[0:0]),
    .begin_bank_i(vmfc_NW__payload[1:1]),
    .begin_epoch_i(vmfc_NW__payload[17:2]),
    .start_i(vmfc_NW__payload[18:18]),
    .start_bank_i(vmfc_NW__payload[19:19]),
    .start_epoch_i(vmfc_NW__payload[35:20]),
    .start_base_sector_i(vmfc_NW__payload[51:36]),
    .fill_v_i({vmks_NW3__fill_v[3:3], vmks_NW1__fill_v[3:3]}),
    .fill_bank_i({vmks_NW3__fill_bank[3:3], vmks_NW1__fill_bank[3:3]}),
    .fill_slot_i({vmks_NW3__fill_slot[23:18], vmks_NW1__fill_slot[23:18]}),
    .fill_epoch_i({vmks_NW3__fill_epoch[63:48], vmks_NW1__fill_epoch[63:48]}),
    .fill_data_i({vmks_NW3__fill_data[1023:768], vmks_NW1__fill_data[1023:768]}),
    .full0_all({vmdel_NW7__full0[0:0], vmdel_NW6__full0[0:0], vmdel_NW5__full0[0:0], vmdel_NW4__full0[0:0], vmdel_NW3__full0[0:0], vmdel_NW2__full0[0:0], vmdel_NW1__full0[0:0], vmdel_NW0__full0[0:0]}),
    .full1_all({vmdel_NW7__full1[0:0], vmdel_NW6__full1[0:0], vmdel_NW5__full1[0:0], vmdel_NW4__full1[0:0], vmdel_NW3__full1[0:0], vmdel_NW2__full1[0:0], vmdel_NW1__full1[0:0], vmdel_NW0__full1[0:0]}),
    .pcbad_all({vmdel_NW7__pcbad[0:0], vmdel_NW6__pcbad[0:0], vmdel_NW5__pcbad[0:0], vmdel_NW4__pcbad[0:0], vmdel_NW3__pcbad[0:0], vmdel_NW2__pcbad[0:0], vmdel_NW1__pcbad[0:0], vmdel_NW0__pcbad[0:0]}),
    .full0(vmdel_NW7__full0[0:0]),
    .full1(vmdel_NW7__full1[0:0]),
    .pcbad(vmdel_NW7__pcbad[0:0]),
    .block_ready(vmdel_NW7__block_ready[1:0]),
    .busy(vmdel_NW7__busy[0:0]),
    .fault(vmdel_NW7__fault[0:0]),
    .dq(vmdel_NW7__dq[280:0])
  );
  hfd_hgi_vm_calendar_f20_role #(.W(89)) vmfc_NE (
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_cap(hb_ckgen__pll_stream[0:0]),
    .clk_mem(hb_ckgen__pll_stream[0:0]),
    .clk_tgt(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .tgt(8'b00111011),
    .cfg_v(hleaf_NE__a_cfg_v[0:0]),
    .cfg_target(hleaf_NE__a_cfg_target[7:0]),
    .cfg_addr(hleaf_NE__a_cfg_addr[11:0]),
    .cfg_data(hleaf_NE__a_cfg_data[255:0]),
    .desc_v(hleaf_NE__a_desc_v[0:0]),
    .desc_base(hleaf_NE__a_desc_base[11:0]),
    .desc_limit(hleaf_NE__a_desc_limit[12:0]),
    .desc_loops(hleaf_NE__a_desc_loops[15:0]),
    .launch_v(hleaf_NE__a_launch_v[0:0]),
    .tgt_configured(vmfc_NE__tgt_configured[0:0]),
    .tgt_fault(vmfc_NE__tgt_fault[0:0]),
    .calendar_v(vmfc_NE__calendar_v[0:0]),
    .active(vmfc_NE__active[0:0]),
    .done(vmfc_NE__done[0:0]),
    .fault(vmfc_NE__fault[0:0]),
    .ordinal(vmfc_NE__ordinal[31:0]),
    .payload(vmfc_NE__payload[88:0])
  );
  hfd_hgi_vm_calendar_f20_role #(.W(89)) vmfc_NW (
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_cap(hb_ckgen__pll_stream[0:0]),
    .clk_mem(hb_ckgen__pll_stream[0:0]),
    .clk_tgt(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .tgt(8'b00111010),
    .cfg_v(hleaf_NW__b_cfg_v[0:0]),
    .cfg_target(hleaf_NW__b_cfg_target[7:0]),
    .cfg_addr(hleaf_NW__b_cfg_addr[11:0]),
    .cfg_data(hleaf_NW__b_cfg_data[255:0]),
    .desc_v(hleaf_NW__b_desc_v[0:0]),
    .desc_base(hleaf_NW__b_desc_base[11:0]),
    .desc_limit(hleaf_NW__b_desc_limit[12:0]),
    .desc_loops(hleaf_NW__b_desc_loops[15:0]),
    .launch_v(hleaf_NW__b_launch_v[0:0]),
    .tgt_configured(vmfc_NW__tgt_configured[0:0]),
    .tgt_fault(vmfc_NW__tgt_fault[0:0]),
    .calendar_v(vmfc_NW__calendar_v[0:0]),
    .active(vmfc_NW__active[0:0]),
    .done(vmfc_NW__done[0:0]),
    .fault(vmfc_NW__fault[0:0]),
    .ordinal(vmfc_NW__ordinal[31:0]),
    .payload(vmfc_NW__payload[88:0])
  );
  ot_hbm_svc_vm_kshare_splitstrap #(.MUT(0), .KRL1(1)) vmks_NW0 (
    .hbm_clk(hb_ckgen__pll_stream[0:0]),
    .hbm_rst_n(hb_ckgen__por_stream[0:0]),
    .stream_clk(hb_ckgen__pll_stream[0:0]),
    .stream_rst_n(hb_ckgen__por_stream[0:0]),
    .sm_stream(3'b000),
    .sm_hbm(3'b000),
    .g_k_v(svg_NW0__k_v[3:0]),
    .g_k_rdy(vmks_NW0__g_k_rdy[3:0]),
    .g_k_addr(svg_NW0__k_addr[119:0]),
    .g_k_len(svg_NW0__k_len[15:0]),
    .g_k_tag(svg_NW0__k_tag[67:0]),
    .g_k_we(svg_NW0__k_we[3:0]),
    .g_k_wdata(svg_NW0__k_wdata[1023:0]),
    .g_k_wstrb(svg_NW0__k_wstrb[127:0]),
    .g_k_wr_done(vmks_NW0__g_k_wr_done[3:0]),
    .g_kr_v(vmks_NW0__g_kr_v[3:0]),
    .g_kr_rdy(svg_NW0__kr_rdy[3:0]),
    .g_kr_tag(vmks_NW0__g_kr_tag[67:0]),
    .g_kr_beat(vmks_NW0__g_kr_beat[15:0]),
    .g_kr_data(vmks_NW0__g_kr_data[1023:0]),
    .c_k_v(vmks_NW0__c_k_v[3:0]),
    .c_k_rdy({ctl_NW_p03__k_rdy[0:0], ctl_NW_p02__k_rdy[0:0], ctl_NW_p01__k_rdy[0:0], ctl_NW_p00__k_rdy[0:0]}),
    .c_k_addr(vmks_NW0__c_k_addr[119:0]),
    .c_k_len(vmks_NW0__c_k_len[15:0]),
    .c_k_tag(vmks_NW0__c_k_tag[67:0]),
    .c_k_we(vmks_NW0__c_k_we[3:0]),
    .c_k_wdata(vmks_NW0__c_k_wdata[1023:0]),
    .c_k_wstrb(vmks_NW0__c_k_wstrb[127:0]),
    .c_k_wr_done({ctl_NW_p03__k_wr_done[0:0], ctl_NW_p02__k_wr_done[0:0], ctl_NW_p01__k_wr_done[0:0], ctl_NW_p00__k_wr_done[0:0]}),
    .c_kr_v({ctl_NW_p03__kr_v[0:0], ctl_NW_p02__kr_v[0:0], ctl_NW_p01__kr_v[0:0], ctl_NW_p00__kr_v[0:0]}),
    .c_kr_rdy(vmks_NW0__c_kr_rdy[3:0]),
    .c_kr_tag({ctl_NW_p03__kr_tag[16:0], ctl_NW_p02__kr_tag[16:0], ctl_NW_p01__kr_tag[16:0], ctl_NW_p00__kr_tag[16:0]}),
    .c_kr_beat({ctl_NW_p03__kr_beat[3:0], ctl_NW_p02__kr_beat[3:0], ctl_NW_p01__kr_beat[3:0], ctl_NW_p00__kr_beat[3:0]}),
    .c_kr_data({ctl_NW_p03__kr_data[255:0], ctl_NW_p02__kr_data[255:0], ctl_NW_p01__kr_data[255:0], ctl_NW_p00__kr_data[255:0]}),
    .vm_v(vmfc_NW__payload[52:52]),
    .vm_bank(vmfc_NW__payload[53:53]),
    .vm_epoch(vmfc_NW__payload[69:54]),
    .vm_row(vmfc_NW__payload[84:70]),
    .vm_col(vmfc_NW__payload[88:85]),
    .wbw_v(wbc_NW__o_wbw_v[0:0]),
    .wbw_base(wbc_NW__o_wbw_base[29:0]),
    .wbw_total(wbc_NW__o_wbw_total[11:0]),
    .w_k_v(wbk_NW__w_k_v[3:0]),
    .w_k_rdy(vmks_NW0__w_k_rdy[3:0]),
    .w_k_addr(wbk_NW__w_k_addr[119:0]),
    .w_k_wdata(wbk_NW__w_k_wdata[1023:0]),
    .w_k_wr_done(vmks_NW0__w_k_wr_done[3:0]),
    .fill_v(vmks_NW0__fill_v[3:0]),
    .fill_bank(vmks_NW0__fill_bank[3:0]),
    .fill_slot(vmks_NW0__fill_slot[23:0]),
    .fill_epoch(vmks_NW0__fill_epoch[63:0]),
    .fill_data(vmks_NW0__fill_data[1023:0]),
    .fault(vmks_NW0__fault[0:0])
  );
  ot_hbm_svc_vm_kshare_splitstrap #(.MUT(0), .KRL1(1)) vmks_NW1 (
    .hbm_clk(hb_ckgen__pll_stream[0:0]),
    .hbm_rst_n(hb_ckgen__por_stream[0:0]),
    .stream_clk(hb_ckgen__pll_stream[0:0]),
    .stream_rst_n(hb_ckgen__por_stream[0:0]),
    .sm_stream(3'b001),
    .sm_hbm(3'b001),
    .g_k_v(svg_NW1__k_v[3:0]),
    .g_k_rdy(vmks_NW1__g_k_rdy[3:0]),
    .g_k_addr(svg_NW1__k_addr[119:0]),
    .g_k_len(svg_NW1__k_len[15:0]),
    .g_k_tag(svg_NW1__k_tag[67:0]),
    .g_k_we(svg_NW1__k_we[3:0]),
    .g_k_wdata(svg_NW1__k_wdata[1023:0]),
    .g_k_wstrb(svg_NW1__k_wstrb[127:0]),
    .g_k_wr_done(vmks_NW1__g_k_wr_done[3:0]),
    .g_kr_v(vmks_NW1__g_kr_v[3:0]),
    .g_kr_rdy(svg_NW1__kr_rdy[3:0]),
    .g_kr_tag(vmks_NW1__g_kr_tag[67:0]),
    .g_kr_beat(vmks_NW1__g_kr_beat[15:0]),
    .g_kr_data(vmks_NW1__g_kr_data[1023:0]),
    .c_k_v(vmks_NW1__c_k_v[3:0]),
    .c_k_rdy({ctl_NW_p07__k_rdy[0:0], ctl_NW_p06__k_rdy[0:0], ctl_NW_p05__k_rdy[0:0], ctl_NW_p04__k_rdy[0:0]}),
    .c_k_addr(vmks_NW1__c_k_addr[119:0]),
    .c_k_len(vmks_NW1__c_k_len[15:0]),
    .c_k_tag(vmks_NW1__c_k_tag[67:0]),
    .c_k_we(vmks_NW1__c_k_we[3:0]),
    .c_k_wdata(vmks_NW1__c_k_wdata[1023:0]),
    .c_k_wstrb(vmks_NW1__c_k_wstrb[127:0]),
    .c_k_wr_done({ctl_NW_p07__k_wr_done[0:0], ctl_NW_p06__k_wr_done[0:0], ctl_NW_p05__k_wr_done[0:0], ctl_NW_p04__k_wr_done[0:0]}),
    .c_kr_v({ctl_NW_p07__kr_v[0:0], ctl_NW_p06__kr_v[0:0], ctl_NW_p05__kr_v[0:0], ctl_NW_p04__kr_v[0:0]}),
    .c_kr_rdy(vmks_NW1__c_kr_rdy[3:0]),
    .c_kr_tag({ctl_NW_p07__kr_tag[16:0], ctl_NW_p06__kr_tag[16:0], ctl_NW_p05__kr_tag[16:0], ctl_NW_p04__kr_tag[16:0]}),
    .c_kr_beat({ctl_NW_p07__kr_beat[3:0], ctl_NW_p06__kr_beat[3:0], ctl_NW_p05__kr_beat[3:0], ctl_NW_p04__kr_beat[3:0]}),
    .c_kr_data({ctl_NW_p07__kr_data[255:0], ctl_NW_p06__kr_data[255:0], ctl_NW_p05__kr_data[255:0], ctl_NW_p04__kr_data[255:0]}),
    .vm_v(vmfc_NW__payload[52:52]),
    .vm_bank(vmfc_NW__payload[53:53]),
    .vm_epoch(vmfc_NW__payload[69:54]),
    .vm_row(vmfc_NW__payload[84:70]),
    .vm_col(vmfc_NW__payload[88:85]),
    .wbw_v(wbc_NW__o_wbw_v[1:1]),
    .wbw_base(wbc_NW__o_wbw_base[59:30]),
    .wbw_total(wbc_NW__o_wbw_total[23:12]),
    .w_k_v(wbk_NW__w_k_v[7:4]),
    .w_k_rdy(vmks_NW1__w_k_rdy[3:0]),
    .w_k_addr(wbk_NW__w_k_addr[239:120]),
    .w_k_wdata(wbk_NW__w_k_wdata[2047:1024]),
    .w_k_wr_done(vmks_NW1__w_k_wr_done[3:0]),
    .fill_v(vmks_NW1__fill_v[3:0]),
    .fill_bank(vmks_NW1__fill_bank[3:0]),
    .fill_slot(vmks_NW1__fill_slot[23:0]),
    .fill_epoch(vmks_NW1__fill_epoch[63:0]),
    .fill_data(vmks_NW1__fill_data[1023:0]),
    .fault(vmks_NW1__fault[0:0])
  );
  ot_hbm_svc_vm_kshare_splitstrap #(.MUT(0), .KRL1(1)) vmks_NW2 (
    .hbm_clk(hb_ckgen__pll_stream[0:0]),
    .hbm_rst_n(hb_ckgen__por_stream[0:0]),
    .stream_clk(hb_ckgen__pll_stream[0:0]),
    .stream_rst_n(hb_ckgen__por_stream[0:0]),
    .sm_stream(3'b010),
    .sm_hbm(3'b010),
    .g_k_v(svg_NW2__k_v[3:0]),
    .g_k_rdy(vmks_NW2__g_k_rdy[3:0]),
    .g_k_addr(svg_NW2__k_addr[119:0]),
    .g_k_len(svg_NW2__k_len[15:0]),
    .g_k_tag(svg_NW2__k_tag[67:0]),
    .g_k_we(svg_NW2__k_we[3:0]),
    .g_k_wdata(svg_NW2__k_wdata[1023:0]),
    .g_k_wstrb(svg_NW2__k_wstrb[127:0]),
    .g_k_wr_done(vmks_NW2__g_k_wr_done[3:0]),
    .g_kr_v(vmks_NW2__g_kr_v[3:0]),
    .g_kr_rdy(svg_NW2__kr_rdy[3:0]),
    .g_kr_tag(vmks_NW2__g_kr_tag[67:0]),
    .g_kr_beat(vmks_NW2__g_kr_beat[15:0]),
    .g_kr_data(vmks_NW2__g_kr_data[1023:0]),
    .c_k_v(vmks_NW2__c_k_v[3:0]),
    .c_k_rdy({ctl_NW_p11__k_rdy[0:0], ctl_NW_p10__k_rdy[0:0], ctl_NW_p09__k_rdy[0:0], ctl_NW_p08__k_rdy[0:0]}),
    .c_k_addr(vmks_NW2__c_k_addr[119:0]),
    .c_k_len(vmks_NW2__c_k_len[15:0]),
    .c_k_tag(vmks_NW2__c_k_tag[67:0]),
    .c_k_we(vmks_NW2__c_k_we[3:0]),
    .c_k_wdata(vmks_NW2__c_k_wdata[1023:0]),
    .c_k_wstrb(vmks_NW2__c_k_wstrb[127:0]),
    .c_k_wr_done({ctl_NW_p11__k_wr_done[0:0], ctl_NW_p10__k_wr_done[0:0], ctl_NW_p09__k_wr_done[0:0], ctl_NW_p08__k_wr_done[0:0]}),
    .c_kr_v({ctl_NW_p11__kr_v[0:0], ctl_NW_p10__kr_v[0:0], ctl_NW_p09__kr_v[0:0], ctl_NW_p08__kr_v[0:0]}),
    .c_kr_rdy(vmks_NW2__c_kr_rdy[3:0]),
    .c_kr_tag({ctl_NW_p11__kr_tag[16:0], ctl_NW_p10__kr_tag[16:0], ctl_NW_p09__kr_tag[16:0], ctl_NW_p08__kr_tag[16:0]}),
    .c_kr_beat({ctl_NW_p11__kr_beat[3:0], ctl_NW_p10__kr_beat[3:0], ctl_NW_p09__kr_beat[3:0], ctl_NW_p08__kr_beat[3:0]}),
    .c_kr_data({ctl_NW_p11__kr_data[255:0], ctl_NW_p10__kr_data[255:0], ctl_NW_p09__kr_data[255:0], ctl_NW_p08__kr_data[255:0]}),
    .vm_v(vmfc_NW__payload[52:52]),
    .vm_bank(vmfc_NW__payload[53:53]),
    .vm_epoch(vmfc_NW__payload[69:54]),
    .vm_row(vmfc_NW__payload[84:70]),
    .vm_col(vmfc_NW__payload[88:85]),
    .wbw_v(wbc_NW__o_wbw_v[2:2]),
    .wbw_base(wbc_NW__o_wbw_base[89:60]),
    .wbw_total(wbc_NW__o_wbw_total[35:24]),
    .w_k_v(wbk_NW__w_k_v[11:8]),
    .w_k_rdy(vmks_NW2__w_k_rdy[3:0]),
    .w_k_addr(wbk_NW__w_k_addr[359:240]),
    .w_k_wdata(wbk_NW__w_k_wdata[3071:2048]),
    .w_k_wr_done(vmks_NW2__w_k_wr_done[3:0]),
    .fill_v(vmks_NW2__fill_v[3:0]),
    .fill_bank(vmks_NW2__fill_bank[3:0]),
    .fill_slot(vmks_NW2__fill_slot[23:0]),
    .fill_epoch(vmks_NW2__fill_epoch[63:0]),
    .fill_data(vmks_NW2__fill_data[1023:0]),
    .fault(vmks_NW2__fault[0:0])
  );
  ot_hbm_svc_vm_kshare_splitstrap #(.MUT(0), .KRL1(1)) vmks_NW3 (
    .hbm_clk(hb_ckgen__pll_stream[0:0]),
    .hbm_rst_n(hb_ckgen__por_stream[0:0]),
    .stream_clk(hb_ckgen__pll_stream[0:0]),
    .stream_rst_n(hb_ckgen__por_stream[0:0]),
    .sm_stream(3'b011),
    .sm_hbm(3'b011),
    .g_k_v(svg_NW3__k_v[3:0]),
    .g_k_rdy(vmks_NW3__g_k_rdy[3:0]),
    .g_k_addr(svg_NW3__k_addr[119:0]),
    .g_k_len(svg_NW3__k_len[15:0]),
    .g_k_tag(svg_NW3__k_tag[67:0]),
    .g_k_we(svg_NW3__k_we[3:0]),
    .g_k_wdata(svg_NW3__k_wdata[1023:0]),
    .g_k_wstrb(svg_NW3__k_wstrb[127:0]),
    .g_k_wr_done(vmks_NW3__g_k_wr_done[3:0]),
    .g_kr_v(vmks_NW3__g_kr_v[3:0]),
    .g_kr_rdy(svg_NW3__kr_rdy[3:0]),
    .g_kr_tag(vmks_NW3__g_kr_tag[67:0]),
    .g_kr_beat(vmks_NW3__g_kr_beat[15:0]),
    .g_kr_data(vmks_NW3__g_kr_data[1023:0]),
    .c_k_v(vmks_NW3__c_k_v[3:0]),
    .c_k_rdy({ctl_NW_p15__k_rdy[0:0], ctl_NW_p14__k_rdy[0:0], ctl_NW_p13__k_rdy[0:0], ctl_NW_p12__k_rdy[0:0]}),
    .c_k_addr(vmks_NW3__c_k_addr[119:0]),
    .c_k_len(vmks_NW3__c_k_len[15:0]),
    .c_k_tag(vmks_NW3__c_k_tag[67:0]),
    .c_k_we(vmks_NW3__c_k_we[3:0]),
    .c_k_wdata(vmks_NW3__c_k_wdata[1023:0]),
    .c_k_wstrb(vmks_NW3__c_k_wstrb[127:0]),
    .c_k_wr_done({ctl_NW_p15__k_wr_done[0:0], ctl_NW_p14__k_wr_done[0:0], ctl_NW_p13__k_wr_done[0:0], ctl_NW_p12__k_wr_done[0:0]}),
    .c_kr_v({ctl_NW_p15__kr_v[0:0], ctl_NW_p14__kr_v[0:0], ctl_NW_p13__kr_v[0:0], ctl_NW_p12__kr_v[0:0]}),
    .c_kr_rdy(vmks_NW3__c_kr_rdy[3:0]),
    .c_kr_tag({ctl_NW_p15__kr_tag[16:0], ctl_NW_p14__kr_tag[16:0], ctl_NW_p13__kr_tag[16:0], ctl_NW_p12__kr_tag[16:0]}),
    .c_kr_beat({ctl_NW_p15__kr_beat[3:0], ctl_NW_p14__kr_beat[3:0], ctl_NW_p13__kr_beat[3:0], ctl_NW_p12__kr_beat[3:0]}),
    .c_kr_data({ctl_NW_p15__kr_data[255:0], ctl_NW_p14__kr_data[255:0], ctl_NW_p13__kr_data[255:0], ctl_NW_p12__kr_data[255:0]}),
    .vm_v(vmfc_NW__payload[52:52]),
    .vm_bank(vmfc_NW__payload[53:53]),
    .vm_epoch(vmfc_NW__payload[69:54]),
    .vm_row(vmfc_NW__payload[84:70]),
    .vm_col(vmfc_NW__payload[88:85]),
    .wbw_v(wbc_NW__o_wbw_v[3:3]),
    .wbw_base(wbc_NW__o_wbw_base[119:90]),
    .wbw_total(wbc_NW__o_wbw_total[47:36]),
    .w_k_v(wbk_NW__w_k_v[15:12]),
    .w_k_rdy(vmks_NW3__w_k_rdy[3:0]),
    .w_k_addr(wbk_NW__w_k_addr[479:360]),
    .w_k_wdata(wbk_NW__w_k_wdata[4095:3072]),
    .w_k_wr_done(vmks_NW3__w_k_wr_done[3:0]),
    .fill_v(vmks_NW3__fill_v[3:0]),
    .fill_bank(vmks_NW3__fill_bank[3:0]),
    .fill_slot(vmks_NW3__fill_slot[23:0]),
    .fill_epoch(vmks_NW3__fill_epoch[63:0]),
    .fill_data(vmks_NW3__fill_data[1023:0]),
    .fault(vmks_NW3__fault[0:0])
  );
  ot_hbm_svc_vm_kshare_splitstrap #(.MUT(0), .KRL1(1)) vmks_NW4 (
    .hbm_clk(hb_ckgen__pll_stream[0:0]),
    .hbm_rst_n(hb_ckgen__por_stream[0:0]),
    .stream_clk(hb_ckgen__pll_stream[0:0]),
    .stream_rst_n(hb_ckgen__por_stream[0:0]),
    .sm_stream(3'b100),
    .sm_hbm(3'b100),
    .g_k_v(svg_NW4__k_v[3:0]),
    .g_k_rdy(vmks_NW4__g_k_rdy[3:0]),
    .g_k_addr(svg_NW4__k_addr[119:0]),
    .g_k_len(svg_NW4__k_len[15:0]),
    .g_k_tag(svg_NW4__k_tag[67:0]),
    .g_k_we(svg_NW4__k_we[3:0]),
    .g_k_wdata(svg_NW4__k_wdata[1023:0]),
    .g_k_wstrb(svg_NW4__k_wstrb[127:0]),
    .g_k_wr_done(vmks_NW4__g_k_wr_done[3:0]),
    .g_kr_v(vmks_NW4__g_kr_v[3:0]),
    .g_kr_rdy(svg_NW4__kr_rdy[3:0]),
    .g_kr_tag(vmks_NW4__g_kr_tag[67:0]),
    .g_kr_beat(vmks_NW4__g_kr_beat[15:0]),
    .g_kr_data(vmks_NW4__g_kr_data[1023:0]),
    .c_k_v(vmks_NW4__c_k_v[3:0]),
    .c_k_rdy({ctl_NW_p19__k_rdy[0:0], ctl_NW_p18__k_rdy[0:0], ctl_NW_p17__k_rdy[0:0], ctl_NW_p16__k_rdy[0:0]}),
    .c_k_addr(vmks_NW4__c_k_addr[119:0]),
    .c_k_len(vmks_NW4__c_k_len[15:0]),
    .c_k_tag(vmks_NW4__c_k_tag[67:0]),
    .c_k_we(vmks_NW4__c_k_we[3:0]),
    .c_k_wdata(vmks_NW4__c_k_wdata[1023:0]),
    .c_k_wstrb(vmks_NW4__c_k_wstrb[127:0]),
    .c_k_wr_done({ctl_NW_p19__k_wr_done[0:0], ctl_NW_p18__k_wr_done[0:0], ctl_NW_p17__k_wr_done[0:0], ctl_NW_p16__k_wr_done[0:0]}),
    .c_kr_v({ctl_NW_p19__kr_v[0:0], ctl_NW_p18__kr_v[0:0], ctl_NW_p17__kr_v[0:0], ctl_NW_p16__kr_v[0:0]}),
    .c_kr_rdy(vmks_NW4__c_kr_rdy[3:0]),
    .c_kr_tag({ctl_NW_p19__kr_tag[16:0], ctl_NW_p18__kr_tag[16:0], ctl_NW_p17__kr_tag[16:0], ctl_NW_p16__kr_tag[16:0]}),
    .c_kr_beat({ctl_NW_p19__kr_beat[3:0], ctl_NW_p18__kr_beat[3:0], ctl_NW_p17__kr_beat[3:0], ctl_NW_p16__kr_beat[3:0]}),
    .c_kr_data({ctl_NW_p19__kr_data[255:0], ctl_NW_p18__kr_data[255:0], ctl_NW_p17__kr_data[255:0], ctl_NW_p16__kr_data[255:0]}),
    .vm_v(vmfc_NE__payload[52:52]),
    .vm_bank(vmfc_NE__payload[53:53]),
    .vm_epoch(vmfc_NE__payload[69:54]),
    .vm_row(vmfc_NE__payload[84:70]),
    .vm_col(vmfc_NE__payload[88:85]),
    .wbw_v(wbc_NE__o_wbw_v[0:0]),
    .wbw_base(wbc_NE__o_wbw_base[29:0]),
    .wbw_total(wbc_NE__o_wbw_total[11:0]),
    .w_k_v(wbk_NE__w_k_v[3:0]),
    .w_k_rdy(vmks_NW4__w_k_rdy[3:0]),
    .w_k_addr(wbk_NE__w_k_addr[119:0]),
    .w_k_wdata(wbk_NE__w_k_wdata[1023:0]),
    .w_k_wr_done(vmks_NW4__w_k_wr_done[3:0]),
    .fill_v(vmks_NW4__fill_v[3:0]),
    .fill_bank(vmks_NW4__fill_bank[3:0]),
    .fill_slot(vmks_NW4__fill_slot[23:0]),
    .fill_epoch(vmks_NW4__fill_epoch[63:0]),
    .fill_data(vmks_NW4__fill_data[1023:0]),
    .fault(vmks_NW4__fault[0:0])
  );
  ot_hbm_svc_vm_kshare_splitstrap #(.MUT(0), .KRL1(1)) vmks_NW5 (
    .hbm_clk(hb_ckgen__pll_stream[0:0]),
    .hbm_rst_n(hb_ckgen__por_stream[0:0]),
    .stream_clk(hb_ckgen__pll_stream[0:0]),
    .stream_rst_n(hb_ckgen__por_stream[0:0]),
    .sm_stream(3'b101),
    .sm_hbm(3'b101),
    .g_k_v(svg_NW5__k_v[3:0]),
    .g_k_rdy(vmks_NW5__g_k_rdy[3:0]),
    .g_k_addr(svg_NW5__k_addr[119:0]),
    .g_k_len(svg_NW5__k_len[15:0]),
    .g_k_tag(svg_NW5__k_tag[67:0]),
    .g_k_we(svg_NW5__k_we[3:0]),
    .g_k_wdata(svg_NW5__k_wdata[1023:0]),
    .g_k_wstrb(svg_NW5__k_wstrb[127:0]),
    .g_k_wr_done(vmks_NW5__g_k_wr_done[3:0]),
    .g_kr_v(vmks_NW5__g_kr_v[3:0]),
    .g_kr_rdy(svg_NW5__kr_rdy[3:0]),
    .g_kr_tag(vmks_NW5__g_kr_tag[67:0]),
    .g_kr_beat(vmks_NW5__g_kr_beat[15:0]),
    .g_kr_data(vmks_NW5__g_kr_data[1023:0]),
    .c_k_v(vmks_NW5__c_k_v[3:0]),
    .c_k_rdy({ctl_NW_p23__k_rdy[0:0], ctl_NW_p22__k_rdy[0:0], ctl_NW_p21__k_rdy[0:0], ctl_NW_p20__k_rdy[0:0]}),
    .c_k_addr(vmks_NW5__c_k_addr[119:0]),
    .c_k_len(vmks_NW5__c_k_len[15:0]),
    .c_k_tag(vmks_NW5__c_k_tag[67:0]),
    .c_k_we(vmks_NW5__c_k_we[3:0]),
    .c_k_wdata(vmks_NW5__c_k_wdata[1023:0]),
    .c_k_wstrb(vmks_NW5__c_k_wstrb[127:0]),
    .c_k_wr_done({ctl_NW_p23__k_wr_done[0:0], ctl_NW_p22__k_wr_done[0:0], ctl_NW_p21__k_wr_done[0:0], ctl_NW_p20__k_wr_done[0:0]}),
    .c_kr_v({ctl_NW_p23__kr_v[0:0], ctl_NW_p22__kr_v[0:0], ctl_NW_p21__kr_v[0:0], ctl_NW_p20__kr_v[0:0]}),
    .c_kr_rdy(vmks_NW5__c_kr_rdy[3:0]),
    .c_kr_tag({ctl_NW_p23__kr_tag[16:0], ctl_NW_p22__kr_tag[16:0], ctl_NW_p21__kr_tag[16:0], ctl_NW_p20__kr_tag[16:0]}),
    .c_kr_beat({ctl_NW_p23__kr_beat[3:0], ctl_NW_p22__kr_beat[3:0], ctl_NW_p21__kr_beat[3:0], ctl_NW_p20__kr_beat[3:0]}),
    .c_kr_data({ctl_NW_p23__kr_data[255:0], ctl_NW_p22__kr_data[255:0], ctl_NW_p21__kr_data[255:0], ctl_NW_p20__kr_data[255:0]}),
    .vm_v(vmfc_NE__payload[52:52]),
    .vm_bank(vmfc_NE__payload[53:53]),
    .vm_epoch(vmfc_NE__payload[69:54]),
    .vm_row(vmfc_NE__payload[84:70]),
    .vm_col(vmfc_NE__payload[88:85]),
    .wbw_v(wbc_NE__o_wbw_v[1:1]),
    .wbw_base(wbc_NE__o_wbw_base[59:30]),
    .wbw_total(wbc_NE__o_wbw_total[23:12]),
    .w_k_v(wbk_NE__w_k_v[7:4]),
    .w_k_rdy(vmks_NW5__w_k_rdy[3:0]),
    .w_k_addr(wbk_NE__w_k_addr[239:120]),
    .w_k_wdata(wbk_NE__w_k_wdata[2047:1024]),
    .w_k_wr_done(vmks_NW5__w_k_wr_done[3:0]),
    .fill_v(vmks_NW5__fill_v[3:0]),
    .fill_bank(vmks_NW5__fill_bank[3:0]),
    .fill_slot(vmks_NW5__fill_slot[23:0]),
    .fill_epoch(vmks_NW5__fill_epoch[63:0]),
    .fill_data(vmks_NW5__fill_data[1023:0]),
    .fault(vmks_NW5__fault[0:0])
  );
  ot_hbm_svc_vm_kshare_splitstrap #(.MUT(0), .KRL1(1)) vmks_NW6 (
    .hbm_clk(hb_ckgen__pll_stream[0:0]),
    .hbm_rst_n(hb_ckgen__por_stream[0:0]),
    .stream_clk(hb_ckgen__pll_stream[0:0]),
    .stream_rst_n(hb_ckgen__por_stream[0:0]),
    .sm_stream(3'b110),
    .sm_hbm(3'b110),
    .g_k_v(svg_NW6__k_v[3:0]),
    .g_k_rdy(vmks_NW6__g_k_rdy[3:0]),
    .g_k_addr(svg_NW6__k_addr[119:0]),
    .g_k_len(svg_NW6__k_len[15:0]),
    .g_k_tag(svg_NW6__k_tag[67:0]),
    .g_k_we(svg_NW6__k_we[3:0]),
    .g_k_wdata(svg_NW6__k_wdata[1023:0]),
    .g_k_wstrb(svg_NW6__k_wstrb[127:0]),
    .g_k_wr_done(vmks_NW6__g_k_wr_done[3:0]),
    .g_kr_v(vmks_NW6__g_kr_v[3:0]),
    .g_kr_rdy(svg_NW6__kr_rdy[3:0]),
    .g_kr_tag(vmks_NW6__g_kr_tag[67:0]),
    .g_kr_beat(vmks_NW6__g_kr_beat[15:0]),
    .g_kr_data(vmks_NW6__g_kr_data[1023:0]),
    .c_k_v(vmks_NW6__c_k_v[3:0]),
    .c_k_rdy({ctl_NW_p27__k_rdy[0:0], ctl_NW_p26__k_rdy[0:0], ctl_NW_p25__k_rdy[0:0], ctl_NW_p24__k_rdy[0:0]}),
    .c_k_addr(vmks_NW6__c_k_addr[119:0]),
    .c_k_len(vmks_NW6__c_k_len[15:0]),
    .c_k_tag(vmks_NW6__c_k_tag[67:0]),
    .c_k_we(vmks_NW6__c_k_we[3:0]),
    .c_k_wdata(vmks_NW6__c_k_wdata[1023:0]),
    .c_k_wstrb(vmks_NW6__c_k_wstrb[127:0]),
    .c_k_wr_done({ctl_NW_p27__k_wr_done[0:0], ctl_NW_p26__k_wr_done[0:0], ctl_NW_p25__k_wr_done[0:0], ctl_NW_p24__k_wr_done[0:0]}),
    .c_kr_v({ctl_NW_p27__kr_v[0:0], ctl_NW_p26__kr_v[0:0], ctl_NW_p25__kr_v[0:0], ctl_NW_p24__kr_v[0:0]}),
    .c_kr_rdy(vmks_NW6__c_kr_rdy[3:0]),
    .c_kr_tag({ctl_NW_p27__kr_tag[16:0], ctl_NW_p26__kr_tag[16:0], ctl_NW_p25__kr_tag[16:0], ctl_NW_p24__kr_tag[16:0]}),
    .c_kr_beat({ctl_NW_p27__kr_beat[3:0], ctl_NW_p26__kr_beat[3:0], ctl_NW_p25__kr_beat[3:0], ctl_NW_p24__kr_beat[3:0]}),
    .c_kr_data({ctl_NW_p27__kr_data[255:0], ctl_NW_p26__kr_data[255:0], ctl_NW_p25__kr_data[255:0], ctl_NW_p24__kr_data[255:0]}),
    .vm_v(vmfc_NE__payload[52:52]),
    .vm_bank(vmfc_NE__payload[53:53]),
    .vm_epoch(vmfc_NE__payload[69:54]),
    .vm_row(vmfc_NE__payload[84:70]),
    .vm_col(vmfc_NE__payload[88:85]),
    .wbw_v(wbc_NE__o_wbw_v[2:2]),
    .wbw_base(wbc_NE__o_wbw_base[89:60]),
    .wbw_total(wbc_NE__o_wbw_total[35:24]),
    .w_k_v(wbk_NE__w_k_v[11:8]),
    .w_k_rdy(vmks_NW6__w_k_rdy[3:0]),
    .w_k_addr(wbk_NE__w_k_addr[359:240]),
    .w_k_wdata(wbk_NE__w_k_wdata[3071:2048]),
    .w_k_wr_done(vmks_NW6__w_k_wr_done[3:0]),
    .fill_v(vmks_NW6__fill_v[3:0]),
    .fill_bank(vmks_NW6__fill_bank[3:0]),
    .fill_slot(vmks_NW6__fill_slot[23:0]),
    .fill_epoch(vmks_NW6__fill_epoch[63:0]),
    .fill_data(vmks_NW6__fill_data[1023:0]),
    .fault(vmks_NW6__fault[0:0])
  );
  ot_hbm_svc_vm_kshare_splitstrap #(.MUT(0), .KRL1(1)) vmks_NW7 (
    .hbm_clk(hb_ckgen__pll_stream[0:0]),
    .hbm_rst_n(hb_ckgen__por_stream[0:0]),
    .stream_clk(hb_ckgen__pll_stream[0:0]),
    .stream_rst_n(hb_ckgen__por_stream[0:0]),
    .sm_stream(3'b111),
    .sm_hbm(3'b111),
    .g_k_v(svg_NW7__k_v[3:0]),
    .g_k_rdy(vmks_NW7__g_k_rdy[3:0]),
    .g_k_addr(svg_NW7__k_addr[119:0]),
    .g_k_len(svg_NW7__k_len[15:0]),
    .g_k_tag(svg_NW7__k_tag[67:0]),
    .g_k_we(svg_NW7__k_we[3:0]),
    .g_k_wdata(svg_NW7__k_wdata[1023:0]),
    .g_k_wstrb(svg_NW7__k_wstrb[127:0]),
    .g_k_wr_done(vmks_NW7__g_k_wr_done[3:0]),
    .g_kr_v(vmks_NW7__g_kr_v[3:0]),
    .g_kr_rdy(svg_NW7__kr_rdy[3:0]),
    .g_kr_tag(vmks_NW7__g_kr_tag[67:0]),
    .g_kr_beat(vmks_NW7__g_kr_beat[15:0]),
    .g_kr_data(vmks_NW7__g_kr_data[1023:0]),
    .c_k_v(vmks_NW7__c_k_v[3:0]),
    .c_k_rdy({ctl_NW_p31__k_rdy[0:0], ctl_NW_p30__k_rdy[0:0], ctl_NW_p29__k_rdy[0:0], ctl_NW_p28__k_rdy[0:0]}),
    .c_k_addr(vmks_NW7__c_k_addr[119:0]),
    .c_k_len(vmks_NW7__c_k_len[15:0]),
    .c_k_tag(vmks_NW7__c_k_tag[67:0]),
    .c_k_we(vmks_NW7__c_k_we[3:0]),
    .c_k_wdata(vmks_NW7__c_k_wdata[1023:0]),
    .c_k_wstrb(vmks_NW7__c_k_wstrb[127:0]),
    .c_k_wr_done({ctl_NW_p31__k_wr_done[0:0], ctl_NW_p30__k_wr_done[0:0], ctl_NW_p29__k_wr_done[0:0], ctl_NW_p28__k_wr_done[0:0]}),
    .c_kr_v({ctl_NW_p31__kr_v[0:0], ctl_NW_p30__kr_v[0:0], ctl_NW_p29__kr_v[0:0], ctl_NW_p28__kr_v[0:0]}),
    .c_kr_rdy(vmks_NW7__c_kr_rdy[3:0]),
    .c_kr_tag({ctl_NW_p31__kr_tag[16:0], ctl_NW_p30__kr_tag[16:0], ctl_NW_p29__kr_tag[16:0], ctl_NW_p28__kr_tag[16:0]}),
    .c_kr_beat({ctl_NW_p31__kr_beat[3:0], ctl_NW_p30__kr_beat[3:0], ctl_NW_p29__kr_beat[3:0], ctl_NW_p28__kr_beat[3:0]}),
    .c_kr_data({ctl_NW_p31__kr_data[255:0], ctl_NW_p30__kr_data[255:0], ctl_NW_p29__kr_data[255:0], ctl_NW_p28__kr_data[255:0]}),
    .vm_v(vmfc_NE__payload[52:52]),
    .vm_bank(vmfc_NE__payload[53:53]),
    .vm_epoch(vmfc_NE__payload[69:54]),
    .vm_row(vmfc_NE__payload[84:70]),
    .vm_col(vmfc_NE__payload[88:85]),
    .wbw_v(wbc_NE__o_wbw_v[3:3]),
    .wbw_base(wbc_NE__o_wbw_base[119:90]),
    .wbw_total(wbc_NE__o_wbw_total[47:36]),
    .w_k_v(wbk_NE__w_k_v[15:12]),
    .w_k_rdy(vmks_NW7__w_k_rdy[3:0]),
    .w_k_addr(wbk_NE__w_k_addr[479:360]),
    .w_k_wdata(wbk_NE__w_k_wdata[4095:3072]),
    .w_k_wr_done(vmks_NW7__w_k_wr_done[3:0]),
    .fill_v(vmks_NW7__fill_v[3:0]),
    .fill_bank(vmks_NW7__fill_bank[3:0]),
    .fill_slot(vmks_NW7__fill_slot[23:0]),
    .fill_epoch(vmks_NW7__fill_epoch[63:0]),
    .fill_data(vmks_NW7__fill_data[1023:0]),
    .fault(vmks_NW7__fault[0:0])
  );
  hfd_vms_wq2_merge vmm_NW0 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__vmm_NW0__rst_n[0:0]),
    .wq1(smw_NW__wq_s0[280:0]),
    .wq2(hb_quant_NW__quant_NW0_lg__wq_o[280:0]),
    .wq_m(vmm_NW0__wq_m[280:0]),
    .done_m(vmb_NW0__wq_done1[0:0]),
    .wq_done1(vmm_NW0__wq_done1[0:0]),
    .wq_done2(vmm_NW0__wq_done2[0:0]),
    .flt(vmm_NW0__flt[0:0])
  );
  hfd_vms_wq2_merge vmm_NW1 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__vmm_NW1__rst_n[0:0]),
    .wq1(smw_NW__wq_s1[280:0]),
    .wq2(hb_quant_NW__quant_NW0_lg__wq_o[561:281]),
    .wq_m(vmm_NW1__wq_m[280:0]),
    .done_m(vmb_NW1__wq_done1[0:0]),
    .wq_done1(vmm_NW1__wq_done1[0:0]),
    .wq_done2(vmm_NW1__wq_done2[0:0]),
    .flt(vmm_NW1__flt[0:0])
  );
  hfd_vms_wq2_merge vmm_NW2 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__vmm_NW2__rst_n[0:0]),
    .wq1(smw_NW__wq_s2[280:0]),
    .wq2(hb_quant_NW__quant_NW1_lg__wq_o[280:0]),
    .wq_m(vmm_NW2__wq_m[280:0]),
    .done_m(vmb_NW2__wq_done1[0:0]),
    .wq_done1(vmm_NW2__wq_done1[0:0]),
    .wq_done2(vmm_NW2__wq_done2[0:0]),
    .flt(vmm_NW2__flt[0:0])
  );
  hfd_vms_wq2_merge vmm_NW3 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__vmm_NW3__rst_n[0:0]),
    .wq1(smw_NW__wq_s3[280:0]),
    .wq2(hb_quant_NW__quant_NW1_lg__wq_o[561:281]),
    .wq_m(vmm_NW3__wq_m[280:0]),
    .done_m(vmb_NW3__wq_done1[0:0]),
    .wq_done1(vmm_NW3__wq_done1[0:0]),
    .wq_done2(vmm_NW3__wq_done2[0:0]),
    .flt(vmm_NW3__flt[0:0])
  );
  hfd_vms_wq2_merge vmm_NW4 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__vmm_NW4__rst_n[0:0]),
    .wq1(smw_NW__wq_t0[280:0]),
    .wq2(hb_quant_NW__quant_NW2_lg__wq_o[280:0]),
    .wq_m(vmm_NW4__wq_m[280:0]),
    .done_m(vmb_NW4__wq_done1[0:0]),
    .wq_done1(vmm_NW4__wq_done1[0:0]),
    .wq_done2(vmm_NW4__wq_done2[0:0]),
    .flt(vmm_NW4__flt[0:0])
  );
  hfd_vms_wq2_merge vmm_NW5 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__vmm_NW5__rst_n[0:0]),
    .wq1(smw_NW__wq_t1[280:0]),
    .wq2(hb_quant_NW__quant_NW2_lg__wq_o[561:281]),
    .wq_m(vmm_NW5__wq_m[280:0]),
    .done_m(vmb_NW5__wq_done1[0:0]),
    .wq_done1(vmm_NW5__wq_done1[0:0]),
    .wq_done2(vmm_NW5__wq_done2[0:0]),
    .flt(vmm_NW5__flt[0:0])
  );
  hfd_vms_wq2_merge vmm_NW6 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__vmm_NW6__rst_n[0:0]),
    .wq1(smw_NW__wq_t2[280:0]),
    .wq2(hb_quant_NW__quant_NW3_lg__wq_o[280:0]),
    .wq_m(vmm_NW6__wq_m[280:0]),
    .done_m(vmb_NW6__wq_done1[0:0]),
    .wq_done1(vmm_NW6__wq_done1[0:0]),
    .wq_done2(vmm_NW6__wq_done2[0:0]),
    .flt(vmm_NW6__flt[0:0])
  );
  hfd_vms_wq2_merge vmm_NW7 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(native_required__vmm_NW7__rst_n[0:0]),
    .wq1(smw_NW__wq_t3[280:0]),
    .wq2(hb_quant_NW__quant_NW3_lg__wq_o[561:281]),
    .wq_m(vmm_NW7__wq_m[280:0]),
    .done_m(vmb_NW7__wq_done1[0:0]),
    .wq_done1(vmm_NW7__wq_done1[0:0]),
    .wq_done2(vmm_NW7__wq_done2[0:0]),
    .flt(vmm_NW7__flt[0:0])
  );
  ot_hbm_svc_wbw_copy #(.NS(4), .MUT(0)) wbc_NE (
    .stream_clk(hb_ckgen__pll_stream[0:0]),
    .stream_rst_n(hb_ckgen__por_stream[0:0]),
    .wbw_v(wbk_NE__wbw_v[0:0]),
    .wbw_base(wbk_NE__wbw_base[29:0]),
    .wbw_total(wbk_NE__wbw_total[11:0]),
    .o_wbw_v(wbc_NE__o_wbw_v[3:0]),
    .o_wbw_base(wbc_NE__o_wbw_base[119:0]),
    .o_wbw_total(wbc_NE__o_wbw_total[47:0])
  );
  ot_hbm_svc_wbw_copy #(.NS(4), .MUT(0)) wbc_NW (
    .stream_clk(hb_ckgen__pll_stream[0:0]),
    .stream_rst_n(hb_ckgen__por_stream[0:0]),
    .wbw_v(wbk_NW__wbw_v[0:0]),
    .wbw_base(wbk_NW__wbw_base[29:0]),
    .wbw_total(wbk_NW__wbw_total[11:0]),
    .o_wbw_v(wbc_NW__o_wbw_v[3:0]),
    .o_wbw_base(wbc_NW__o_wbw_base[119:0]),
    .o_wbw_total(wbc_NW__o_wbw_total[47:0])
  );
  ot_hbm_svc_wb_kport_q #(.WOPEN(0), .MUT(0)) wbk_NE (
    .stream_clk(hb_ckgen__pll_stream[0:0]),
    .stream_rst_n(hb_ckgen__por_stream[0:0]),
    .hbm_clk(hb_ckgen__pll_stream[0:0]),
    .hbm_rst_n(hb_ckgen__por_stream[0:0]),
    .stream_fifo_clk({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .stk(2'b10),
    .quad(1'b1),
    .wb_reserve_v(hb_dbk_NE__wb_reserve_v[0:0]),
    .wb_reserve_bank(hb_dbk_NE__wb_reserve_bank[0:0]),
    .wb_fill_bank(hb_dbk_NE__wb_fill_bank[0:0]),
    .wb_reserve_epoch(hb_dbk_NE__wb_reserve_epoch[15:0]),
    .wb_fill_epoch(hb_dbk_NE__wb_fill_epoch[15:0]),
    .wb_reserve_sectors(hb_dbk_NE__wb_reserve_sectors[11:0]),
    .wb_reserve_base(hb_dbk_NE__wb_reserve_base[31:0]),
    .wb_fill_start(hb_dbk_NE__wb_fill_start[0:0]),
    .wd(hb_dbk_NE__wd[2311:0]),
    .wb_ready(wbk_NE__wb_ready[0:0]),
    .wa(wbk_NE__wa[11:0]),
    .wbw_v(wbk_NE__wbw_v[0:0]),
    .wbw_base(wbk_NE__wbw_base[29:0]),
    .wbw_total(wbk_NE__wbw_total[11:0]),
    .w_k_v(wbk_NE__w_k_v[15:0]),
    .w_k_rdy({vmks_NW7__w_k_rdy[3:0], vmks_NW6__w_k_rdy[3:0], vmks_NW5__w_k_rdy[3:0], vmks_NW4__w_k_rdy[3:0]}),
    .w_k_addr(wbk_NE__w_k_addr[479:0]),
    .w_k_wdata(wbk_NE__w_k_wdata[4095:0]),
    .w_k_wr_done({vmks_NW7__w_k_wr_done[3:0], vmks_NW6__w_k_wr_done[3:0], vmks_NW5__w_k_wr_done[3:0], vmks_NW4__w_k_wr_done[3:0]}),
    .fault(wbk_NE__fault[0:0])
  );
  ot_hbm_svc_wb_kport_q #(.WOPEN(0), .MUT(0)) wbk_NW (
    .stream_clk(hb_ckgen__pll_stream[0:0]),
    .stream_rst_n(hb_ckgen__por_stream[0:0]),
    .hbm_clk(hb_ckgen__pll_stream[0:0]),
    .hbm_rst_n(hb_ckgen__por_stream[0:0]),
    .stream_fifo_clk({hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0], hb_ckgen__pll_stream[0:0]}),
    .stk(2'b10),
    .quad(1'b0),
    .wb_reserve_v(hb_dbk_NW__wb_reserve_v[0:0]),
    .wb_reserve_bank(hb_dbk_NW__wb_reserve_bank[0:0]),
    .wb_fill_bank(hb_dbk_NW__wb_fill_bank[0:0]),
    .wb_reserve_epoch(hb_dbk_NW__wb_reserve_epoch[15:0]),
    .wb_fill_epoch(hb_dbk_NW__wb_fill_epoch[15:0]),
    .wb_reserve_sectors(hb_dbk_NW__wb_reserve_sectors[11:0]),
    .wb_reserve_base(hb_dbk_NW__wb_reserve_base[31:0]),
    .wb_fill_start(hb_dbk_NW__wb_fill_start[0:0]),
    .wd(hb_dbk_NW__wd[2311:0]),
    .wb_ready(wbk_NW__wb_ready[0:0]),
    .wa(wbk_NW__wa[11:0]),
    .wbw_v(wbk_NW__wbw_v[0:0]),
    .wbw_base(wbk_NW__wbw_base[29:0]),
    .wbw_total(wbk_NW__wbw_total[11:0]),
    .w_k_v(wbk_NW__w_k_v[15:0]),
    .w_k_rdy({vmks_NW3__w_k_rdy[3:0], vmks_NW2__w_k_rdy[3:0], vmks_NW1__w_k_rdy[3:0], vmks_NW0__w_k_rdy[3:0]}),
    .w_k_addr(wbk_NW__w_k_addr[479:0]),
    .w_k_wdata(wbk_NW__w_k_wdata[4095:0]),
    .w_k_wr_done({vmks_NW3__w_k_wr_done[3:0], vmks_NW2__w_k_wr_done[3:0], vmks_NW1__w_k_wr_done[3:0], vmks_NW0__w_k_wr_done[3:0]}),
    .fault(wbk_NW__fault[0:0])
  );
  ot_hbm_svc_sm_xcal_rel_t #(.PAW(11), .PREL(1), .DD(256), .XSLOT(1)) xc_NW0 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .tgt(8'b11010000),
    .cfg_v(hleaf_NW__a_cfg_v[0:0]),
    .cfg_target(hleaf_NW__a_cfg_target[7:0]),
    .cfg_addr(hleaf_NW__a_cfg_addr[11:0]),
    .cfg_data(hleaf_NW__a_cfg_data[255:0]),
    .desc_v(hleaf_NW__a_desc_v[0:0]),
    .desc_base(hleaf_NW__a_desc_base[11:0]),
    .desc_limit(hleaf_NW__a_desc_limit[12:0]),
    .desc_loops(hleaf_NW__a_desc_loops[15:0]),
    .launch_v(hleaf_NW__a_launch_v[0:0]),
    .cmd_ext(xc_NW0__cmd_ext[108:0]),
    .kv_desc(xc_NW0__kv_desc[63:0]),
    .done(xc_NW0__done[0:0]),
    .configured(xc_NW0__configured[0:0]),
    .fault(xc_NW0__fault[0:0]),
    .active(xc_NW0__active[0:0])
  );
  ot_hbm_svc_sm_xcal_rel_t #(.PAW(11), .PREL(1), .DD(256), .XSLOT(1)) xc_NW1 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .tgt(8'b11010001),
    .cfg_v(hleaf_NW__b_cfg_v[0:0]),
    .cfg_target(hleaf_NW__b_cfg_target[7:0]),
    .cfg_addr(hleaf_NW__b_cfg_addr[11:0]),
    .cfg_data(hleaf_NW__b_cfg_data[255:0]),
    .desc_v(hleaf_NW__b_desc_v[0:0]),
    .desc_base(hleaf_NW__b_desc_base[11:0]),
    .desc_limit(hleaf_NW__b_desc_limit[12:0]),
    .desc_loops(hleaf_NW__b_desc_loops[15:0]),
    .launch_v(hleaf_NW__b_launch_v[0:0]),
    .cmd_ext(xc_NW1__cmd_ext[108:0]),
    .kv_desc(xc_NW1__kv_desc[63:0]),
    .done(xc_NW1__done[0:0]),
    .configured(xc_NW1__configured[0:0]),
    .fault(xc_NW1__fault[0:0]),
    .active(xc_NW1__active[0:0])
  );
  ot_hbm_svc_sm_xcal_rel_t #(.PAW(11), .PREL(1), .DD(256), .XSLOT(1)) xc_NW2 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .tgt(8'b11010010),
    .cfg_v(hleaf_NW__a_cfg_v[0:0]),
    .cfg_target(hleaf_NW__a_cfg_target[7:0]),
    .cfg_addr(hleaf_NW__a_cfg_addr[11:0]),
    .cfg_data(hleaf_NW__a_cfg_data[255:0]),
    .desc_v(hleaf_NW__a_desc_v[0:0]),
    .desc_base(hleaf_NW__a_desc_base[11:0]),
    .desc_limit(hleaf_NW__a_desc_limit[12:0]),
    .desc_loops(hleaf_NW__a_desc_loops[15:0]),
    .launch_v(hleaf_NW__a_launch_v[0:0]),
    .cmd_ext(xc_NW2__cmd_ext[108:0]),
    .kv_desc(xc_NW2__kv_desc[63:0]),
    .done(xc_NW2__done[0:0]),
    .configured(xc_NW2__configured[0:0]),
    .fault(xc_NW2__fault[0:0]),
    .active(xc_NW2__active[0:0])
  );
  ot_hbm_svc_sm_xcal_rel_t #(.PAW(11), .PREL(1), .DD(256), .XSLOT(1)) xc_NW3 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .tgt(8'b11010011),
    .cfg_v(hleaf_NW__b_cfg_v[0:0]),
    .cfg_target(hleaf_NW__b_cfg_target[7:0]),
    .cfg_addr(hleaf_NW__b_cfg_addr[11:0]),
    .cfg_data(hleaf_NW__b_cfg_data[255:0]),
    .desc_v(hleaf_NW__b_desc_v[0:0]),
    .desc_base(hleaf_NW__b_desc_base[11:0]),
    .desc_limit(hleaf_NW__b_desc_limit[12:0]),
    .desc_loops(hleaf_NW__b_desc_loops[15:0]),
    .launch_v(hleaf_NW__b_launch_v[0:0]),
    .cmd_ext(xc_NW3__cmd_ext[108:0]),
    .kv_desc(xc_NW3__kv_desc[63:0]),
    .done(xc_NW3__done[0:0]),
    .configured(xc_NW3__configured[0:0]),
    .fault(xc_NW3__fault[0:0]),
    .active(xc_NW3__active[0:0])
  );
  ot_hbm_svc_sm_xcal_rel_t #(.PAW(11), .PREL(1), .DD(256), .XSLOT(1)) xc_NW4 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .tgt(8'b11010100),
    .cfg_v(hleaf_NE__b_cfg_v[0:0]),
    .cfg_target(hleaf_NE__b_cfg_target[7:0]),
    .cfg_addr(hleaf_NE__b_cfg_addr[11:0]),
    .cfg_data(hleaf_NE__b_cfg_data[255:0]),
    .desc_v(hleaf_NE__b_desc_v[0:0]),
    .desc_base(hleaf_NE__b_desc_base[11:0]),
    .desc_limit(hleaf_NE__b_desc_limit[12:0]),
    .desc_loops(hleaf_NE__b_desc_loops[15:0]),
    .launch_v(hleaf_NE__b_launch_v[0:0]),
    .cmd_ext(xc_NW4__cmd_ext[108:0]),
    .kv_desc(xc_NW4__kv_desc[63:0]),
    .done(xc_NW4__done[0:0]),
    .configured(xc_NW4__configured[0:0]),
    .fault(xc_NW4__fault[0:0]),
    .active(xc_NW4__active[0:0])
  );
  ot_hbm_svc_sm_xcal_rel_t #(.PAW(11), .PREL(1), .DD(256), .XSLOT(1)) xc_NW5 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .tgt(8'b11010101),
    .cfg_v(hleaf_NE__a_cfg_v[0:0]),
    .cfg_target(hleaf_NE__a_cfg_target[7:0]),
    .cfg_addr(hleaf_NE__a_cfg_addr[11:0]),
    .cfg_data(hleaf_NE__a_cfg_data[255:0]),
    .desc_v(hleaf_NE__a_desc_v[0:0]),
    .desc_base(hleaf_NE__a_desc_base[11:0]),
    .desc_limit(hleaf_NE__a_desc_limit[12:0]),
    .desc_loops(hleaf_NE__a_desc_loops[15:0]),
    .launch_v(hleaf_NE__a_launch_v[0:0]),
    .cmd_ext(xc_NW5__cmd_ext[108:0]),
    .kv_desc(xc_NW5__kv_desc[63:0]),
    .done(xc_NW5__done[0:0]),
    .configured(xc_NW5__configured[0:0]),
    .fault(xc_NW5__fault[0:0]),
    .active(xc_NW5__active[0:0])
  );
  ot_hbm_svc_sm_xcal_rel_t #(.PAW(11), .PREL(1), .DD(256), .XSLOT(1)) xc_NW6 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .tgt(8'b11010110),
    .cfg_v(hleaf_NE__b_cfg_v[0:0]),
    .cfg_target(hleaf_NE__b_cfg_target[7:0]),
    .cfg_addr(hleaf_NE__b_cfg_addr[11:0]),
    .cfg_data(hleaf_NE__b_cfg_data[255:0]),
    .desc_v(hleaf_NE__b_desc_v[0:0]),
    .desc_base(hleaf_NE__b_desc_base[11:0]),
    .desc_limit(hleaf_NE__b_desc_limit[12:0]),
    .desc_loops(hleaf_NE__b_desc_loops[15:0]),
    .launch_v(hleaf_NE__b_launch_v[0:0]),
    .cmd_ext(xc_NW6__cmd_ext[108:0]),
    .kv_desc(xc_NW6__kv_desc[63:0]),
    .done(xc_NW6__done[0:0]),
    .configured(xc_NW6__configured[0:0]),
    .fault(xc_NW6__fault[0:0]),
    .active(xc_NW6__active[0:0])
  );
  ot_hbm_svc_sm_xcal_rel_t #(.PAW(11), .PREL(1), .DD(256), .XSLOT(1)) xc_NW7 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .tgt(8'b11010111),
    .cfg_v(hleaf_NE__a_cfg_v[0:0]),
    .cfg_target(hleaf_NE__a_cfg_target[7:0]),
    .cfg_addr(hleaf_NE__a_cfg_addr[11:0]),
    .cfg_data(hleaf_NE__a_cfg_data[255:0]),
    .desc_v(hleaf_NE__a_desc_v[0:0]),
    .desc_base(hleaf_NE__a_desc_base[11:0]),
    .desc_limit(hleaf_NE__a_desc_limit[12:0]),
    .desc_loops(hleaf_NE__a_desc_loops[15:0]),
    .launch_v(hleaf_NE__a_launch_v[0:0]),
    .cmd_ext(xc_NW7__cmd_ext[108:0]),
    .kv_desc(xc_NW7__kv_desc[63:0]),
    .done(xc_NW7__done[0:0]),
    .configured(xc_NW7__configured[0:0]),
    .fault(xc_NW7__fault[0:0]),
    .active(xc_NW7__active[0:0])
  );
  ot_hbm_xp_aq_tree13_fmt #(.FP4(0), .MUT(0)) xl_NE_aqhi (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(xl_NE_ctl__rn_o[0:0]),
    .v(xl_NE_ctl__qv_hi[0:0]),
    .x(xl_NE_ctl__l_d_o[2047:1024]),
    .vo(xl_NE_aqhi__vo[0:0]),
    .q(xl_NE_aqhi__q[255:0]),
    .e(xl_NE_aqhi__e[9:0]),
    .y(xl_NE_aqhi__y[511:0]),
    .fault(xl_NE_aqhi__fault[0:0])
  );
  ot_hbm_xp_aq_tree13_fmt #(.FP4(0), .MUT(0)) xl_NE_aqlo (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(xl_NE_ctl__rn_o[0:0]),
    .v(xl_NE_ctl__qv_lo[0:0]),
    .x(xl_NE_ctl__l_d_o[1023:0]),
    .vo(xl_NE_aqlo__vo[0:0]),
    .q(xl_NE_aqlo__q[255:0]),
    .e(xl_NE_aqlo__e[9:0]),
    .y(xl_NE_aqlo__y[511:0]),
    .fault(xl_NE_aqlo__fault[0:0])
  );
  ot_hgi_sm_xload_cl2_ctlx #(.PMAX(8), .RD_LAT({8'd46, 8'd44, 8'd66, 8'd62, 8'd30, 8'd28, 8'd44, 8'd42}), .NR(32), .LEAD(8)) xl_NE_ctl (
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_cal(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .tgt(8'b01100111),
    .cfg_v(hleaf_NE__b_cfg_v[0:0]),
    .cfg_target(hleaf_NE__b_cfg_target[7:0]),
    .cfg_addr(hleaf_NE__b_cfg_addr[11:0]),
    .cfg_data(hleaf_NE__b_cfg_data[255:0]),
    .desc_v(hleaf_NE__b_desc_v[0:0]),
    .desc_base(hleaf_NE__b_desc_base[11:0]),
    .desc_limit(hleaf_NE__b_desc_limit[12:0]),
    .desc_loops(hleaf_NE__b_desc_loops[15:0]),
    .launch_v(hleaf_NE__b_launch_v[0:0]),
    .configured(xl_NE_ctl__configured[0:0]),
    .fault(xl_NE_ctl__fault[0:0]),
    .active(xl_NE_ctl__active[0:0]),
    .rq(xl_NE_ctl__rq[135:0]),
    .rr({vmb_NE7__rr2[256:0], vmb_NE6__rr2[256:0], vmb_NE5__rr2[256:0], vmb_NE4__rr2[256:0], vmb_NE3__rr2[256:0], vmb_NE2__rr2[256:0], vmb_NE1__rr2[256:0], vmb_NE0__rr2[256:0]}),
    .rn_o(xl_NE_ctl__rn_o[0:0]),
    .c_d(xl_NE_ctl__c_d[1023:0]),
    .c_wce(xl_NE_ctl__c_wce[3:0]),
    .c_mhi(xl_NE_ctl__c_mhi[0:0]),
    .c_mlo(xl_NE_ctl__c_mlo[0:0]),
    .c_wa(xl_NE_ctl__c_wa[6:0]),
    .r_ce(xl_NE_ctl__r_ce[7:0]),
    .r_a(xl_NE_ctl__r_a[6:0]),
    .l_d_o(xl_NE_ctl__l_d_o[2047:0]),
    .qv_lo(xl_NE_ctl__qv_lo[0:0]),
    .qv_hi(xl_NE_ctl__qv_hi[0:0]),
    .qo_lo(xl_NE_aqlo__vo[0:0]),
    .qo_hi(xl_NE_aqhi__vo[0:0]),
    .qf_lo(xl_NE_aqlo__fault[0:0]),
    .qf_hi(xl_NE_aqhi__fault[0:0]),
    .r_wsel(xl_NE_ctl__r_wsel[15:0]),
    .zlo(xl_NE_ctl__zlo[0:0]),
    .zhi(xl_NE_ctl__zhi[0:0]),
    .bsel(xl_NE_ctl__bsel[25:0]),
    .lane_en(xl_NE_ctl__lane_en[63:0]),
    .eg_ed5(xl_NE_ctl__eg_ed5[7:0]),
    .eg_ede(xl_NE_ctl__eg_ede[16:0]),
    .eg_bqv(xl_NE_ctl__eg_bqv[0:0]),
    .eg_bqlast(xl_NE_ctl__eg_bqlast[0:0]),
    .eg_bqaddr(xl_NE_ctl__eg_bqaddr[6:0]),
    .eg_bqb(xl_NE_ctl__eg_bqb[6:0])
  );
  ot_hbm_xp_aq_tree13_fmt #(.FP4(0), .MUT(0)) xl_NW_aqhi (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(xl_NW_ctl__rn_o[0:0]),
    .v(xl_NW_ctl__qv_hi[0:0]),
    .x(xl_NW_ctl__l_d_o[2047:1024]),
    .vo(xl_NW_aqhi__vo[0:0]),
    .q(xl_NW_aqhi__q[255:0]),
    .e(xl_NW_aqhi__e[9:0]),
    .y(xl_NW_aqhi__y[511:0]),
    .fault(xl_NW_aqhi__fault[0:0])
  );
  ot_hbm_xp_aq_tree13_fmt #(.FP4(0), .MUT(0)) xl_NW_aqlo (
    .clk(hb_ckgen__pll_stream[0:0]),
    .rst_n(xl_NW_ctl__rn_o[0:0]),
    .v(xl_NW_ctl__qv_lo[0:0]),
    .x(xl_NW_ctl__l_d_o[1023:0]),
    .vo(xl_NW_aqlo__vo[0:0]),
    .q(xl_NW_aqlo__q[255:0]),
    .e(xl_NW_aqlo__e[9:0]),
    .y(xl_NW_aqlo__y[511:0]),
    .fault(xl_NW_aqlo__fault[0:0])
  );
  ot_hgi_sm_xload_cl2_ctlx #(.PMAX(8), .RD_LAT({8'd46, 8'd44, 8'd66, 8'd62, 8'd30, 8'd28, 8'd44, 8'd42}), .NR(32), .LEAD(8)) xl_NW_ctl (
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_cal(hb_ckgen__pll_stream[0:0]),
    .rst_n(hb_ckgen__por_stream[0:0]),
    .tgt(8'b01100110),
    .cfg_v(hleaf_NW__a_cfg_v[0:0]),
    .cfg_target(hleaf_NW__a_cfg_target[7:0]),
    .cfg_addr(hleaf_NW__a_cfg_addr[11:0]),
    .cfg_data(hleaf_NW__a_cfg_data[255:0]),
    .desc_v(hleaf_NW__a_desc_v[0:0]),
    .desc_base(hleaf_NW__a_desc_base[11:0]),
    .desc_limit(hleaf_NW__a_desc_limit[12:0]),
    .desc_loops(hleaf_NW__a_desc_loops[15:0]),
    .launch_v(hleaf_NW__a_launch_v[0:0]),
    .configured(xl_NW_ctl__configured[0:0]),
    .fault(xl_NW_ctl__fault[0:0]),
    .active(xl_NW_ctl__active[0:0]),
    .rq(xl_NW_ctl__rq[135:0]),
    .rr({vmb_NW7__rr2[256:0], vmb_NW6__rr2[256:0], vmb_NW5__rr2[256:0], vmb_NW4__rr2[256:0], vmb_NW3__rr2[256:0], vmb_NW2__rr2[256:0], vmb_NW1__rr2[256:0], vmb_NW0__rr2[256:0]}),
    .rn_o(xl_NW_ctl__rn_o[0:0]),
    .c_d(xl_NW_ctl__c_d[1023:0]),
    .c_wce(xl_NW_ctl__c_wce[3:0]),
    .c_mhi(xl_NW_ctl__c_mhi[0:0]),
    .c_mlo(xl_NW_ctl__c_mlo[0:0]),
    .c_wa(xl_NW_ctl__c_wa[6:0]),
    .r_ce(xl_NW_ctl__r_ce[7:0]),
    .r_a(xl_NW_ctl__r_a[6:0]),
    .l_d_o(xl_NW_ctl__l_d_o[2047:0]),
    .qv_lo(xl_NW_ctl__qv_lo[0:0]),
    .qv_hi(xl_NW_ctl__qv_hi[0:0]),
    .qo_lo(xl_NW_aqlo__vo[0:0]),
    .qo_hi(xl_NW_aqhi__vo[0:0]),
    .qf_lo(xl_NW_aqlo__fault[0:0]),
    .qf_hi(xl_NW_aqhi__fault[0:0]),
    .r_wsel(xl_NW_ctl__r_wsel[15:0]),
    .zlo(xl_NW_ctl__zlo[0:0]),
    .zhi(xl_NW_ctl__zhi[0:0]),
    .bsel(xl_NW_ctl__bsel[25:0]),
    .lane_en(xl_NW_ctl__lane_en[63:0]),
    .eg_ed5(xl_NW_ctl__eg_ed5[7:0]),
    .eg_ede(xl_NW_ctl__eg_ede[16:0]),
    .eg_bqv(xl_NW_ctl__eg_bqv[0:0]),
    .eg_bqlast(xl_NW_ctl__eg_bqlast[0:0]),
    .eg_bqaddr(xl_NW_ctl__eg_bqaddr[6:0]),
    .eg_bqb(xl_NW_ctl__eg_bqb[6:0])
  );
  ot_hgi_sm_xload_cl2_bdring #(.PMAX(8), .NR(32)) xq_NE_p0_bd (
    .clk(hb_ckgen__pll_stream[0:0]),
    .r_wsel(xl_NE_ctl__r_wsel[15:0]),
    .zlo(xl_NE_ctl__zlo[0:0]),
    .zhi(xl_NE_ctl__zhi[0:0]),
    .qq_lo(xl_NE_aqlo__q[255:0]),
    .qq_hi(xl_NE_aqhi__q[255:0]),
    .qe_lo(xl_NE_aqlo__e[9:0]),
    .qe_hi(xl_NE_aqhi__e[9:0]),
    .bsel(xl_NE_ctl__bsel[25:0]),
    .lane_en_i(xl_NE_ctl__lane_en[63:0]),
    .bq_d(xq_NE_p0_bd__bq_d[2047:0])
  );
  ot_hgi_sm_xload_cl2_bfqg xq_NE_p0_bfq0 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_ctrl(hb_ckgen__pll_stream[0:0]),
    .clk_m0(hb_ckgen__pll_stream[0:0]),
    .clk_m1(hb_ckgen__pll_stream[0:0]),
    .clk_m2(hb_ckgen__pll_stream[0:0]),
    .clk_m3(hb_ckgen__pll_stream[0:0]),
    .clk_m4(hb_ckgen__pll_stream[0:0]),
    .clk_m5(hb_ckgen__pll_stream[0:0]),
    .clk_m6(hb_ckgen__pll_stream[0:0]),
    .clk_m7(hb_ckgen__pll_stream[0:0]),
    .clk_l0(hb_ckgen__pll_stream[0:0]),
    .clk_l1(hb_ckgen__pll_stream[0:0]),
    .clk_l2(hb_ckgen__pll_stream[0:0]),
    .clk_l3(hb_ckgen__pll_stream[0:0]),
    .clk_l4(hb_ckgen__pll_stream[0:0]),
    .clk_l5(hb_ckgen__pll_stream[0:0]),
    .clk_l6(hb_ckgen__pll_stream[0:0]),
    .clk_l7(hb_ckgen__pll_stream[0:0]),
    .rst_n(xl_NE_ctl__rn_o[0:0]),
    .c_d(xl_NE_ctl__c_d[1023:0]),
    .wce(xl_NE_ctl__c_wce[0:0]),
    .mhi0(xl_NE_ctl__c_mhi[0:0]),
    .mhi1(xl_NE_ctl__c_mhi[0:0]),
    .mhi2(xl_NE_ctl__c_mhi[0:0]),
    .mhi3(xl_NE_ctl__c_mhi[0:0]),
    .mhi4(xl_NE_ctl__c_mhi[0:0]),
    .mhi5(xl_NE_ctl__c_mhi[0:0]),
    .mhi6(xl_NE_ctl__c_mhi[0:0]),
    .mhi7(xl_NE_ctl__c_mhi[0:0]),
    .mlo0(xl_NE_ctl__c_mlo[0:0]),
    .mlo1(xl_NE_ctl__c_mlo[0:0]),
    .mlo2(xl_NE_ctl__c_mlo[0:0]),
    .mlo3(xl_NE_ctl__c_mlo[0:0]),
    .mlo4(xl_NE_ctl__c_mlo[0:0]),
    .mlo5(xl_NE_ctl__c_mlo[0:0]),
    .mlo6(xl_NE_ctl__c_mlo[0:0]),
    .mlo7(xl_NE_ctl__c_mlo[0:0]),
    .wa(xl_NE_ctl__c_wa[6:0]),
    .r_ce(xl_NE_ctl__r_ce[7:0]),
    .r_a(xl_NE_ctl__r_a[6:0]),
    .rwq(xq_NE_p0_bfq0__rwq[255:0])
  );
  ot_hgi_sm_xload_cl2_bfqg xq_NE_p0_bfq1 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_ctrl(hb_ckgen__pll_stream[0:0]),
    .clk_m0(hb_ckgen__pll_stream[0:0]),
    .clk_m1(hb_ckgen__pll_stream[0:0]),
    .clk_m2(hb_ckgen__pll_stream[0:0]),
    .clk_m3(hb_ckgen__pll_stream[0:0]),
    .clk_m4(hb_ckgen__pll_stream[0:0]),
    .clk_m5(hb_ckgen__pll_stream[0:0]),
    .clk_m6(hb_ckgen__pll_stream[0:0]),
    .clk_m7(hb_ckgen__pll_stream[0:0]),
    .clk_l0(hb_ckgen__pll_stream[0:0]),
    .clk_l1(hb_ckgen__pll_stream[0:0]),
    .clk_l2(hb_ckgen__pll_stream[0:0]),
    .clk_l3(hb_ckgen__pll_stream[0:0]),
    .clk_l4(hb_ckgen__pll_stream[0:0]),
    .clk_l5(hb_ckgen__pll_stream[0:0]),
    .clk_l6(hb_ckgen__pll_stream[0:0]),
    .clk_l7(hb_ckgen__pll_stream[0:0]),
    .rst_n(xl_NE_ctl__rn_o[0:0]),
    .c_d(xl_NE_ctl__c_d[1023:0]),
    .wce(xl_NE_ctl__c_wce[1:1]),
    .mhi0(xl_NE_ctl__c_mhi[0:0]),
    .mhi1(xl_NE_ctl__c_mhi[0:0]),
    .mhi2(xl_NE_ctl__c_mhi[0:0]),
    .mhi3(xl_NE_ctl__c_mhi[0:0]),
    .mhi4(xl_NE_ctl__c_mhi[0:0]),
    .mhi5(xl_NE_ctl__c_mhi[0:0]),
    .mhi6(xl_NE_ctl__c_mhi[0:0]),
    .mhi7(xl_NE_ctl__c_mhi[0:0]),
    .mlo0(xl_NE_ctl__c_mlo[0:0]),
    .mlo1(xl_NE_ctl__c_mlo[0:0]),
    .mlo2(xl_NE_ctl__c_mlo[0:0]),
    .mlo3(xl_NE_ctl__c_mlo[0:0]),
    .mlo4(xl_NE_ctl__c_mlo[0:0]),
    .mlo5(xl_NE_ctl__c_mlo[0:0]),
    .mlo6(xl_NE_ctl__c_mlo[0:0]),
    .mlo7(xl_NE_ctl__c_mlo[0:0]),
    .wa(xl_NE_ctl__c_wa[6:0]),
    .r_ce(xl_NE_ctl__r_ce[7:0]),
    .r_a(xl_NE_ctl__r_a[6:0]),
    .rwq(xq_NE_p0_bfq1__rwq[255:0])
  );
  ot_hgi_sm_xload_cl2_bfqg xq_NE_p0_bfq2 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_ctrl(hb_ckgen__pll_stream[0:0]),
    .clk_m0(hb_ckgen__pll_stream[0:0]),
    .clk_m1(hb_ckgen__pll_stream[0:0]),
    .clk_m2(hb_ckgen__pll_stream[0:0]),
    .clk_m3(hb_ckgen__pll_stream[0:0]),
    .clk_m4(hb_ckgen__pll_stream[0:0]),
    .clk_m5(hb_ckgen__pll_stream[0:0]),
    .clk_m6(hb_ckgen__pll_stream[0:0]),
    .clk_m7(hb_ckgen__pll_stream[0:0]),
    .clk_l0(hb_ckgen__pll_stream[0:0]),
    .clk_l1(hb_ckgen__pll_stream[0:0]),
    .clk_l2(hb_ckgen__pll_stream[0:0]),
    .clk_l3(hb_ckgen__pll_stream[0:0]),
    .clk_l4(hb_ckgen__pll_stream[0:0]),
    .clk_l5(hb_ckgen__pll_stream[0:0]),
    .clk_l6(hb_ckgen__pll_stream[0:0]),
    .clk_l7(hb_ckgen__pll_stream[0:0]),
    .rst_n(xl_NE_ctl__rn_o[0:0]),
    .c_d(xl_NE_ctl__c_d[1023:0]),
    .wce(xl_NE_ctl__c_wce[2:2]),
    .mhi0(xl_NE_ctl__c_mhi[0:0]),
    .mhi1(xl_NE_ctl__c_mhi[0:0]),
    .mhi2(xl_NE_ctl__c_mhi[0:0]),
    .mhi3(xl_NE_ctl__c_mhi[0:0]),
    .mhi4(xl_NE_ctl__c_mhi[0:0]),
    .mhi5(xl_NE_ctl__c_mhi[0:0]),
    .mhi6(xl_NE_ctl__c_mhi[0:0]),
    .mhi7(xl_NE_ctl__c_mhi[0:0]),
    .mlo0(xl_NE_ctl__c_mlo[0:0]),
    .mlo1(xl_NE_ctl__c_mlo[0:0]),
    .mlo2(xl_NE_ctl__c_mlo[0:0]),
    .mlo3(xl_NE_ctl__c_mlo[0:0]),
    .mlo4(xl_NE_ctl__c_mlo[0:0]),
    .mlo5(xl_NE_ctl__c_mlo[0:0]),
    .mlo6(xl_NE_ctl__c_mlo[0:0]),
    .mlo7(xl_NE_ctl__c_mlo[0:0]),
    .wa(xl_NE_ctl__c_wa[6:0]),
    .r_ce(xl_NE_ctl__r_ce[7:0]),
    .r_a(xl_NE_ctl__r_a[6:0]),
    .rwq(xq_NE_p0_bfq2__rwq[255:0])
  );
  ot_hgi_sm_xload_cl2_bfqg xq_NE_p0_bfq3 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_ctrl(hb_ckgen__pll_stream[0:0]),
    .clk_m0(hb_ckgen__pll_stream[0:0]),
    .clk_m1(hb_ckgen__pll_stream[0:0]),
    .clk_m2(hb_ckgen__pll_stream[0:0]),
    .clk_m3(hb_ckgen__pll_stream[0:0]),
    .clk_m4(hb_ckgen__pll_stream[0:0]),
    .clk_m5(hb_ckgen__pll_stream[0:0]),
    .clk_m6(hb_ckgen__pll_stream[0:0]),
    .clk_m7(hb_ckgen__pll_stream[0:0]),
    .clk_l0(hb_ckgen__pll_stream[0:0]),
    .clk_l1(hb_ckgen__pll_stream[0:0]),
    .clk_l2(hb_ckgen__pll_stream[0:0]),
    .clk_l3(hb_ckgen__pll_stream[0:0]),
    .clk_l4(hb_ckgen__pll_stream[0:0]),
    .clk_l5(hb_ckgen__pll_stream[0:0]),
    .clk_l6(hb_ckgen__pll_stream[0:0]),
    .clk_l7(hb_ckgen__pll_stream[0:0]),
    .rst_n(xl_NE_ctl__rn_o[0:0]),
    .c_d(xl_NE_ctl__c_d[1023:0]),
    .wce(xl_NE_ctl__c_wce[3:3]),
    .mhi0(xl_NE_ctl__c_mhi[0:0]),
    .mhi1(xl_NE_ctl__c_mhi[0:0]),
    .mhi2(xl_NE_ctl__c_mhi[0:0]),
    .mhi3(xl_NE_ctl__c_mhi[0:0]),
    .mhi4(xl_NE_ctl__c_mhi[0:0]),
    .mhi5(xl_NE_ctl__c_mhi[0:0]),
    .mhi6(xl_NE_ctl__c_mhi[0:0]),
    .mhi7(xl_NE_ctl__c_mhi[0:0]),
    .mlo0(xl_NE_ctl__c_mlo[0:0]),
    .mlo1(xl_NE_ctl__c_mlo[0:0]),
    .mlo2(xl_NE_ctl__c_mlo[0:0]),
    .mlo3(xl_NE_ctl__c_mlo[0:0]),
    .mlo4(xl_NE_ctl__c_mlo[0:0]),
    .mlo5(xl_NE_ctl__c_mlo[0:0]),
    .mlo6(xl_NE_ctl__c_mlo[0:0]),
    .mlo7(xl_NE_ctl__c_mlo[0:0]),
    .wa(xl_NE_ctl__c_wa[6:0]),
    .r_ce(xl_NE_ctl__r_ce[7:0]),
    .r_a(xl_NE_ctl__r_a[6:0]),
    .rwq(xq_NE_p0_bfq3__rwq[255:0])
  );
  ot_hgi_sm_xload_xq_pegress #(.PMAX(8), .NR(32)) xq_NE_p0_eg (
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_w(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_e(hb_ckgen__pll_stream[0:0]),
    .clk_c(hb_ckgen__pll_stream[0:0]),
    .rn(xl_NE_ctl__rn_o[0:0]),
    .ed5(xl_NE_ctl__eg_ed5[7:0]),
    .ede(xl_NE_ctl__eg_ede[16:0]),
    .bq_v(xl_NE_ctl__eg_bqv[0:0]),
    .bq_last(xl_NE_ctl__eg_bqlast[0:0]),
    .bq_addr(xl_NE_ctl__eg_bqaddr[6:0]),
    .bq_b(xl_NE_ctl__eg_bqb[6:0]),
    .rwq({xq_NE_p0_bfq3__rwq[255:0], xq_NE_p0_bfq2__rwq[255:0], xq_NE_p0_bfq1__rwq[255:0], xq_NE_p0_bfq0__rwq[255:0]}),
    .bq_d(xq_NE_p0_bd__bq_d[2047:0]),
    .x_done(xq_NE_p0_eg__x_done[0:0]),
    .xw_en(xq_NE_p0_eg__xw_en[0:0]),
    .xw_last(xq_NE_p0_eg__xw_last[0:0]),
    .xw_addr(xq_NE_p0_eg__xw_addr[6:0]),
    .xw_grp(xq_NE_p0_eg__xw_grp[6:0]),
    .xw_data(xq_NE_p0_eg__xw_data[2047:0])
  );
  ot_hgi_sm_xload_cl2_bdring #(.PMAX(8), .NR(32)) xq_NE_p1_bd (
    .clk(hb_ckgen__pll_stream[0:0]),
    .r_wsel(xl_NE_ctl__r_wsel[15:0]),
    .zlo(xl_NE_ctl__zlo[0:0]),
    .zhi(xl_NE_ctl__zhi[0:0]),
    .qq_lo(xl_NE_aqlo__q[255:0]),
    .qq_hi(xl_NE_aqhi__q[255:0]),
    .qe_lo(xl_NE_aqlo__e[9:0]),
    .qe_hi(xl_NE_aqhi__e[9:0]),
    .bsel(xl_NE_ctl__bsel[25:0]),
    .lane_en_i(xl_NE_ctl__lane_en[63:0]),
    .bq_d(xq_NE_p1_bd__bq_d[2047:0])
  );
  ot_hgi_sm_xload_cl2_bfqg xq_NE_p1_bfq0 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_ctrl(hb_ckgen__pll_stream[0:0]),
    .clk_m0(hb_ckgen__pll_stream[0:0]),
    .clk_m1(hb_ckgen__pll_stream[0:0]),
    .clk_m2(hb_ckgen__pll_stream[0:0]),
    .clk_m3(hb_ckgen__pll_stream[0:0]),
    .clk_m4(hb_ckgen__pll_stream[0:0]),
    .clk_m5(hb_ckgen__pll_stream[0:0]),
    .clk_m6(hb_ckgen__pll_stream[0:0]),
    .clk_m7(hb_ckgen__pll_stream[0:0]),
    .clk_l0(hb_ckgen__pll_stream[0:0]),
    .clk_l1(hb_ckgen__pll_stream[0:0]),
    .clk_l2(hb_ckgen__pll_stream[0:0]),
    .clk_l3(hb_ckgen__pll_stream[0:0]),
    .clk_l4(hb_ckgen__pll_stream[0:0]),
    .clk_l5(hb_ckgen__pll_stream[0:0]),
    .clk_l6(hb_ckgen__pll_stream[0:0]),
    .clk_l7(hb_ckgen__pll_stream[0:0]),
    .rst_n(xl_NE_ctl__rn_o[0:0]),
    .c_d(xl_NE_ctl__c_d[1023:0]),
    .wce(xl_NE_ctl__c_wce[0:0]),
    .mhi0(xl_NE_ctl__c_mhi[0:0]),
    .mhi1(xl_NE_ctl__c_mhi[0:0]),
    .mhi2(xl_NE_ctl__c_mhi[0:0]),
    .mhi3(xl_NE_ctl__c_mhi[0:0]),
    .mhi4(xl_NE_ctl__c_mhi[0:0]),
    .mhi5(xl_NE_ctl__c_mhi[0:0]),
    .mhi6(xl_NE_ctl__c_mhi[0:0]),
    .mhi7(xl_NE_ctl__c_mhi[0:0]),
    .mlo0(xl_NE_ctl__c_mlo[0:0]),
    .mlo1(xl_NE_ctl__c_mlo[0:0]),
    .mlo2(xl_NE_ctl__c_mlo[0:0]),
    .mlo3(xl_NE_ctl__c_mlo[0:0]),
    .mlo4(xl_NE_ctl__c_mlo[0:0]),
    .mlo5(xl_NE_ctl__c_mlo[0:0]),
    .mlo6(xl_NE_ctl__c_mlo[0:0]),
    .mlo7(xl_NE_ctl__c_mlo[0:0]),
    .wa(xl_NE_ctl__c_wa[6:0]),
    .r_ce(xl_NE_ctl__r_ce[7:0]),
    .r_a(xl_NE_ctl__r_a[6:0]),
    .rwq(xq_NE_p1_bfq0__rwq[255:0])
  );
  ot_hgi_sm_xload_cl2_bfqg xq_NE_p1_bfq1 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_ctrl(hb_ckgen__pll_stream[0:0]),
    .clk_m0(hb_ckgen__pll_stream[0:0]),
    .clk_m1(hb_ckgen__pll_stream[0:0]),
    .clk_m2(hb_ckgen__pll_stream[0:0]),
    .clk_m3(hb_ckgen__pll_stream[0:0]),
    .clk_m4(hb_ckgen__pll_stream[0:0]),
    .clk_m5(hb_ckgen__pll_stream[0:0]),
    .clk_m6(hb_ckgen__pll_stream[0:0]),
    .clk_m7(hb_ckgen__pll_stream[0:0]),
    .clk_l0(hb_ckgen__pll_stream[0:0]),
    .clk_l1(hb_ckgen__pll_stream[0:0]),
    .clk_l2(hb_ckgen__pll_stream[0:0]),
    .clk_l3(hb_ckgen__pll_stream[0:0]),
    .clk_l4(hb_ckgen__pll_stream[0:0]),
    .clk_l5(hb_ckgen__pll_stream[0:0]),
    .clk_l6(hb_ckgen__pll_stream[0:0]),
    .clk_l7(hb_ckgen__pll_stream[0:0]),
    .rst_n(xl_NE_ctl__rn_o[0:0]),
    .c_d(xl_NE_ctl__c_d[1023:0]),
    .wce(xl_NE_ctl__c_wce[1:1]),
    .mhi0(xl_NE_ctl__c_mhi[0:0]),
    .mhi1(xl_NE_ctl__c_mhi[0:0]),
    .mhi2(xl_NE_ctl__c_mhi[0:0]),
    .mhi3(xl_NE_ctl__c_mhi[0:0]),
    .mhi4(xl_NE_ctl__c_mhi[0:0]),
    .mhi5(xl_NE_ctl__c_mhi[0:0]),
    .mhi6(xl_NE_ctl__c_mhi[0:0]),
    .mhi7(xl_NE_ctl__c_mhi[0:0]),
    .mlo0(xl_NE_ctl__c_mlo[0:0]),
    .mlo1(xl_NE_ctl__c_mlo[0:0]),
    .mlo2(xl_NE_ctl__c_mlo[0:0]),
    .mlo3(xl_NE_ctl__c_mlo[0:0]),
    .mlo4(xl_NE_ctl__c_mlo[0:0]),
    .mlo5(xl_NE_ctl__c_mlo[0:0]),
    .mlo6(xl_NE_ctl__c_mlo[0:0]),
    .mlo7(xl_NE_ctl__c_mlo[0:0]),
    .wa(xl_NE_ctl__c_wa[6:0]),
    .r_ce(xl_NE_ctl__r_ce[7:0]),
    .r_a(xl_NE_ctl__r_a[6:0]),
    .rwq(xq_NE_p1_bfq1__rwq[255:0])
  );
  ot_hgi_sm_xload_cl2_bfqg xq_NE_p1_bfq2 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_ctrl(hb_ckgen__pll_stream[0:0]),
    .clk_m0(hb_ckgen__pll_stream[0:0]),
    .clk_m1(hb_ckgen__pll_stream[0:0]),
    .clk_m2(hb_ckgen__pll_stream[0:0]),
    .clk_m3(hb_ckgen__pll_stream[0:0]),
    .clk_m4(hb_ckgen__pll_stream[0:0]),
    .clk_m5(hb_ckgen__pll_stream[0:0]),
    .clk_m6(hb_ckgen__pll_stream[0:0]),
    .clk_m7(hb_ckgen__pll_stream[0:0]),
    .clk_l0(hb_ckgen__pll_stream[0:0]),
    .clk_l1(hb_ckgen__pll_stream[0:0]),
    .clk_l2(hb_ckgen__pll_stream[0:0]),
    .clk_l3(hb_ckgen__pll_stream[0:0]),
    .clk_l4(hb_ckgen__pll_stream[0:0]),
    .clk_l5(hb_ckgen__pll_stream[0:0]),
    .clk_l6(hb_ckgen__pll_stream[0:0]),
    .clk_l7(hb_ckgen__pll_stream[0:0]),
    .rst_n(xl_NE_ctl__rn_o[0:0]),
    .c_d(xl_NE_ctl__c_d[1023:0]),
    .wce(xl_NE_ctl__c_wce[2:2]),
    .mhi0(xl_NE_ctl__c_mhi[0:0]),
    .mhi1(xl_NE_ctl__c_mhi[0:0]),
    .mhi2(xl_NE_ctl__c_mhi[0:0]),
    .mhi3(xl_NE_ctl__c_mhi[0:0]),
    .mhi4(xl_NE_ctl__c_mhi[0:0]),
    .mhi5(xl_NE_ctl__c_mhi[0:0]),
    .mhi6(xl_NE_ctl__c_mhi[0:0]),
    .mhi7(xl_NE_ctl__c_mhi[0:0]),
    .mlo0(xl_NE_ctl__c_mlo[0:0]),
    .mlo1(xl_NE_ctl__c_mlo[0:0]),
    .mlo2(xl_NE_ctl__c_mlo[0:0]),
    .mlo3(xl_NE_ctl__c_mlo[0:0]),
    .mlo4(xl_NE_ctl__c_mlo[0:0]),
    .mlo5(xl_NE_ctl__c_mlo[0:0]),
    .mlo6(xl_NE_ctl__c_mlo[0:0]),
    .mlo7(xl_NE_ctl__c_mlo[0:0]),
    .wa(xl_NE_ctl__c_wa[6:0]),
    .r_ce(xl_NE_ctl__r_ce[7:0]),
    .r_a(xl_NE_ctl__r_a[6:0]),
    .rwq(xq_NE_p1_bfq2__rwq[255:0])
  );
  ot_hgi_sm_xload_cl2_bfqg xq_NE_p1_bfq3 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_ctrl(hb_ckgen__pll_stream[0:0]),
    .clk_m0(hb_ckgen__pll_stream[0:0]),
    .clk_m1(hb_ckgen__pll_stream[0:0]),
    .clk_m2(hb_ckgen__pll_stream[0:0]),
    .clk_m3(hb_ckgen__pll_stream[0:0]),
    .clk_m4(hb_ckgen__pll_stream[0:0]),
    .clk_m5(hb_ckgen__pll_stream[0:0]),
    .clk_m6(hb_ckgen__pll_stream[0:0]),
    .clk_m7(hb_ckgen__pll_stream[0:0]),
    .clk_l0(hb_ckgen__pll_stream[0:0]),
    .clk_l1(hb_ckgen__pll_stream[0:0]),
    .clk_l2(hb_ckgen__pll_stream[0:0]),
    .clk_l3(hb_ckgen__pll_stream[0:0]),
    .clk_l4(hb_ckgen__pll_stream[0:0]),
    .clk_l5(hb_ckgen__pll_stream[0:0]),
    .clk_l6(hb_ckgen__pll_stream[0:0]),
    .clk_l7(hb_ckgen__pll_stream[0:0]),
    .rst_n(xl_NE_ctl__rn_o[0:0]),
    .c_d(xl_NE_ctl__c_d[1023:0]),
    .wce(xl_NE_ctl__c_wce[3:3]),
    .mhi0(xl_NE_ctl__c_mhi[0:0]),
    .mhi1(xl_NE_ctl__c_mhi[0:0]),
    .mhi2(xl_NE_ctl__c_mhi[0:0]),
    .mhi3(xl_NE_ctl__c_mhi[0:0]),
    .mhi4(xl_NE_ctl__c_mhi[0:0]),
    .mhi5(xl_NE_ctl__c_mhi[0:0]),
    .mhi6(xl_NE_ctl__c_mhi[0:0]),
    .mhi7(xl_NE_ctl__c_mhi[0:0]),
    .mlo0(xl_NE_ctl__c_mlo[0:0]),
    .mlo1(xl_NE_ctl__c_mlo[0:0]),
    .mlo2(xl_NE_ctl__c_mlo[0:0]),
    .mlo3(xl_NE_ctl__c_mlo[0:0]),
    .mlo4(xl_NE_ctl__c_mlo[0:0]),
    .mlo5(xl_NE_ctl__c_mlo[0:0]),
    .mlo6(xl_NE_ctl__c_mlo[0:0]),
    .mlo7(xl_NE_ctl__c_mlo[0:0]),
    .wa(xl_NE_ctl__c_wa[6:0]),
    .r_ce(xl_NE_ctl__r_ce[7:0]),
    .r_a(xl_NE_ctl__r_a[6:0]),
    .rwq(xq_NE_p1_bfq3__rwq[255:0])
  );
  ot_hgi_sm_xload_xq_pegress #(.PMAX(8), .NR(32)) xq_NE_p1_eg (
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_w(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_e(hb_ckgen__pll_stream[0:0]),
    .clk_c(hb_ckgen__pll_stream[0:0]),
    .rn(xl_NE_ctl__rn_o[0:0]),
    .ed5(xl_NE_ctl__eg_ed5[7:0]),
    .ede(xl_NE_ctl__eg_ede[16:0]),
    .bq_v(xl_NE_ctl__eg_bqv[0:0]),
    .bq_last(xl_NE_ctl__eg_bqlast[0:0]),
    .bq_addr(xl_NE_ctl__eg_bqaddr[6:0]),
    .bq_b(xl_NE_ctl__eg_bqb[6:0]),
    .rwq({xq_NE_p1_bfq3__rwq[255:0], xq_NE_p1_bfq2__rwq[255:0], xq_NE_p1_bfq1__rwq[255:0], xq_NE_p1_bfq0__rwq[255:0]}),
    .bq_d(xq_NE_p1_bd__bq_d[2047:0]),
    .x_done(xq_NE_p1_eg__x_done[0:0]),
    .xw_en(xq_NE_p1_eg__xw_en[0:0]),
    .xw_last(xq_NE_p1_eg__xw_last[0:0]),
    .xw_addr(xq_NE_p1_eg__xw_addr[6:0]),
    .xw_grp(xq_NE_p1_eg__xw_grp[6:0]),
    .xw_data(xq_NE_p1_eg__xw_data[2047:0])
  );
  ot_hgi_sm_xload_cl2_bdring #(.PMAX(8), .NR(32)) xq_NW_p0_bd (
    .clk(hb_ckgen__pll_stream[0:0]),
    .r_wsel(xl_NW_ctl__r_wsel[15:0]),
    .zlo(xl_NW_ctl__zlo[0:0]),
    .zhi(xl_NW_ctl__zhi[0:0]),
    .qq_lo(xl_NW_aqlo__q[255:0]),
    .qq_hi(xl_NW_aqhi__q[255:0]),
    .qe_lo(xl_NW_aqlo__e[9:0]),
    .qe_hi(xl_NW_aqhi__e[9:0]),
    .bsel(xl_NW_ctl__bsel[25:0]),
    .lane_en_i(xl_NW_ctl__lane_en[63:0]),
    .bq_d(xq_NW_p0_bd__bq_d[2047:0])
  );
  ot_hgi_sm_xload_cl2_bfqg xq_NW_p0_bfq0 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_ctrl(hb_ckgen__pll_stream[0:0]),
    .clk_m0(hb_ckgen__pll_stream[0:0]),
    .clk_m1(hb_ckgen__pll_stream[0:0]),
    .clk_m2(hb_ckgen__pll_stream[0:0]),
    .clk_m3(hb_ckgen__pll_stream[0:0]),
    .clk_m4(hb_ckgen__pll_stream[0:0]),
    .clk_m5(hb_ckgen__pll_stream[0:0]),
    .clk_m6(hb_ckgen__pll_stream[0:0]),
    .clk_m7(hb_ckgen__pll_stream[0:0]),
    .clk_l0(hb_ckgen__pll_stream[0:0]),
    .clk_l1(hb_ckgen__pll_stream[0:0]),
    .clk_l2(hb_ckgen__pll_stream[0:0]),
    .clk_l3(hb_ckgen__pll_stream[0:0]),
    .clk_l4(hb_ckgen__pll_stream[0:0]),
    .clk_l5(hb_ckgen__pll_stream[0:0]),
    .clk_l6(hb_ckgen__pll_stream[0:0]),
    .clk_l7(hb_ckgen__pll_stream[0:0]),
    .rst_n(xl_NW_ctl__rn_o[0:0]),
    .c_d(xl_NW_ctl__c_d[1023:0]),
    .wce(xl_NW_ctl__c_wce[0:0]),
    .mhi0(xl_NW_ctl__c_mhi[0:0]),
    .mhi1(xl_NW_ctl__c_mhi[0:0]),
    .mhi2(xl_NW_ctl__c_mhi[0:0]),
    .mhi3(xl_NW_ctl__c_mhi[0:0]),
    .mhi4(xl_NW_ctl__c_mhi[0:0]),
    .mhi5(xl_NW_ctl__c_mhi[0:0]),
    .mhi6(xl_NW_ctl__c_mhi[0:0]),
    .mhi7(xl_NW_ctl__c_mhi[0:0]),
    .mlo0(xl_NW_ctl__c_mlo[0:0]),
    .mlo1(xl_NW_ctl__c_mlo[0:0]),
    .mlo2(xl_NW_ctl__c_mlo[0:0]),
    .mlo3(xl_NW_ctl__c_mlo[0:0]),
    .mlo4(xl_NW_ctl__c_mlo[0:0]),
    .mlo5(xl_NW_ctl__c_mlo[0:0]),
    .mlo6(xl_NW_ctl__c_mlo[0:0]),
    .mlo7(xl_NW_ctl__c_mlo[0:0]),
    .wa(xl_NW_ctl__c_wa[6:0]),
    .r_ce(xl_NW_ctl__r_ce[7:0]),
    .r_a(xl_NW_ctl__r_a[6:0]),
    .rwq(xq_NW_p0_bfq0__rwq[255:0])
  );
  ot_hgi_sm_xload_cl2_bfqg xq_NW_p0_bfq1 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_ctrl(hb_ckgen__pll_stream[0:0]),
    .clk_m0(hb_ckgen__pll_stream[0:0]),
    .clk_m1(hb_ckgen__pll_stream[0:0]),
    .clk_m2(hb_ckgen__pll_stream[0:0]),
    .clk_m3(hb_ckgen__pll_stream[0:0]),
    .clk_m4(hb_ckgen__pll_stream[0:0]),
    .clk_m5(hb_ckgen__pll_stream[0:0]),
    .clk_m6(hb_ckgen__pll_stream[0:0]),
    .clk_m7(hb_ckgen__pll_stream[0:0]),
    .clk_l0(hb_ckgen__pll_stream[0:0]),
    .clk_l1(hb_ckgen__pll_stream[0:0]),
    .clk_l2(hb_ckgen__pll_stream[0:0]),
    .clk_l3(hb_ckgen__pll_stream[0:0]),
    .clk_l4(hb_ckgen__pll_stream[0:0]),
    .clk_l5(hb_ckgen__pll_stream[0:0]),
    .clk_l6(hb_ckgen__pll_stream[0:0]),
    .clk_l7(hb_ckgen__pll_stream[0:0]),
    .rst_n(xl_NW_ctl__rn_o[0:0]),
    .c_d(xl_NW_ctl__c_d[1023:0]),
    .wce(xl_NW_ctl__c_wce[1:1]),
    .mhi0(xl_NW_ctl__c_mhi[0:0]),
    .mhi1(xl_NW_ctl__c_mhi[0:0]),
    .mhi2(xl_NW_ctl__c_mhi[0:0]),
    .mhi3(xl_NW_ctl__c_mhi[0:0]),
    .mhi4(xl_NW_ctl__c_mhi[0:0]),
    .mhi5(xl_NW_ctl__c_mhi[0:0]),
    .mhi6(xl_NW_ctl__c_mhi[0:0]),
    .mhi7(xl_NW_ctl__c_mhi[0:0]),
    .mlo0(xl_NW_ctl__c_mlo[0:0]),
    .mlo1(xl_NW_ctl__c_mlo[0:0]),
    .mlo2(xl_NW_ctl__c_mlo[0:0]),
    .mlo3(xl_NW_ctl__c_mlo[0:0]),
    .mlo4(xl_NW_ctl__c_mlo[0:0]),
    .mlo5(xl_NW_ctl__c_mlo[0:0]),
    .mlo6(xl_NW_ctl__c_mlo[0:0]),
    .mlo7(xl_NW_ctl__c_mlo[0:0]),
    .wa(xl_NW_ctl__c_wa[6:0]),
    .r_ce(xl_NW_ctl__r_ce[7:0]),
    .r_a(xl_NW_ctl__r_a[6:0]),
    .rwq(xq_NW_p0_bfq1__rwq[255:0])
  );
  ot_hgi_sm_xload_cl2_bfqg xq_NW_p0_bfq2 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_ctrl(hb_ckgen__pll_stream[0:0]),
    .clk_m0(hb_ckgen__pll_stream[0:0]),
    .clk_m1(hb_ckgen__pll_stream[0:0]),
    .clk_m2(hb_ckgen__pll_stream[0:0]),
    .clk_m3(hb_ckgen__pll_stream[0:0]),
    .clk_m4(hb_ckgen__pll_stream[0:0]),
    .clk_m5(hb_ckgen__pll_stream[0:0]),
    .clk_m6(hb_ckgen__pll_stream[0:0]),
    .clk_m7(hb_ckgen__pll_stream[0:0]),
    .clk_l0(hb_ckgen__pll_stream[0:0]),
    .clk_l1(hb_ckgen__pll_stream[0:0]),
    .clk_l2(hb_ckgen__pll_stream[0:0]),
    .clk_l3(hb_ckgen__pll_stream[0:0]),
    .clk_l4(hb_ckgen__pll_stream[0:0]),
    .clk_l5(hb_ckgen__pll_stream[0:0]),
    .clk_l6(hb_ckgen__pll_stream[0:0]),
    .clk_l7(hb_ckgen__pll_stream[0:0]),
    .rst_n(xl_NW_ctl__rn_o[0:0]),
    .c_d(xl_NW_ctl__c_d[1023:0]),
    .wce(xl_NW_ctl__c_wce[2:2]),
    .mhi0(xl_NW_ctl__c_mhi[0:0]),
    .mhi1(xl_NW_ctl__c_mhi[0:0]),
    .mhi2(xl_NW_ctl__c_mhi[0:0]),
    .mhi3(xl_NW_ctl__c_mhi[0:0]),
    .mhi4(xl_NW_ctl__c_mhi[0:0]),
    .mhi5(xl_NW_ctl__c_mhi[0:0]),
    .mhi6(xl_NW_ctl__c_mhi[0:0]),
    .mhi7(xl_NW_ctl__c_mhi[0:0]),
    .mlo0(xl_NW_ctl__c_mlo[0:0]),
    .mlo1(xl_NW_ctl__c_mlo[0:0]),
    .mlo2(xl_NW_ctl__c_mlo[0:0]),
    .mlo3(xl_NW_ctl__c_mlo[0:0]),
    .mlo4(xl_NW_ctl__c_mlo[0:0]),
    .mlo5(xl_NW_ctl__c_mlo[0:0]),
    .mlo6(xl_NW_ctl__c_mlo[0:0]),
    .mlo7(xl_NW_ctl__c_mlo[0:0]),
    .wa(xl_NW_ctl__c_wa[6:0]),
    .r_ce(xl_NW_ctl__r_ce[7:0]),
    .r_a(xl_NW_ctl__r_a[6:0]),
    .rwq(xq_NW_p0_bfq2__rwq[255:0])
  );
  ot_hgi_sm_xload_cl2_bfqg xq_NW_p0_bfq3 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_ctrl(hb_ckgen__pll_stream[0:0]),
    .clk_m0(hb_ckgen__pll_stream[0:0]),
    .clk_m1(hb_ckgen__pll_stream[0:0]),
    .clk_m2(hb_ckgen__pll_stream[0:0]),
    .clk_m3(hb_ckgen__pll_stream[0:0]),
    .clk_m4(hb_ckgen__pll_stream[0:0]),
    .clk_m5(hb_ckgen__pll_stream[0:0]),
    .clk_m6(hb_ckgen__pll_stream[0:0]),
    .clk_m7(hb_ckgen__pll_stream[0:0]),
    .clk_l0(hb_ckgen__pll_stream[0:0]),
    .clk_l1(hb_ckgen__pll_stream[0:0]),
    .clk_l2(hb_ckgen__pll_stream[0:0]),
    .clk_l3(hb_ckgen__pll_stream[0:0]),
    .clk_l4(hb_ckgen__pll_stream[0:0]),
    .clk_l5(hb_ckgen__pll_stream[0:0]),
    .clk_l6(hb_ckgen__pll_stream[0:0]),
    .clk_l7(hb_ckgen__pll_stream[0:0]),
    .rst_n(xl_NW_ctl__rn_o[0:0]),
    .c_d(xl_NW_ctl__c_d[1023:0]),
    .wce(xl_NW_ctl__c_wce[3:3]),
    .mhi0(xl_NW_ctl__c_mhi[0:0]),
    .mhi1(xl_NW_ctl__c_mhi[0:0]),
    .mhi2(xl_NW_ctl__c_mhi[0:0]),
    .mhi3(xl_NW_ctl__c_mhi[0:0]),
    .mhi4(xl_NW_ctl__c_mhi[0:0]),
    .mhi5(xl_NW_ctl__c_mhi[0:0]),
    .mhi6(xl_NW_ctl__c_mhi[0:0]),
    .mhi7(xl_NW_ctl__c_mhi[0:0]),
    .mlo0(xl_NW_ctl__c_mlo[0:0]),
    .mlo1(xl_NW_ctl__c_mlo[0:0]),
    .mlo2(xl_NW_ctl__c_mlo[0:0]),
    .mlo3(xl_NW_ctl__c_mlo[0:0]),
    .mlo4(xl_NW_ctl__c_mlo[0:0]),
    .mlo5(xl_NW_ctl__c_mlo[0:0]),
    .mlo6(xl_NW_ctl__c_mlo[0:0]),
    .mlo7(xl_NW_ctl__c_mlo[0:0]),
    .wa(xl_NW_ctl__c_wa[6:0]),
    .r_ce(xl_NW_ctl__r_ce[7:0]),
    .r_a(xl_NW_ctl__r_a[6:0]),
    .rwq(xq_NW_p0_bfq3__rwq[255:0])
  );
  ot_hgi_sm_xload_xq_pegress #(.PMAX(8), .NR(32)) xq_NW_p0_eg (
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_w(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_e(hb_ckgen__pll_stream[0:0]),
    .clk_c(hb_ckgen__pll_stream[0:0]),
    .rn(xl_NW_ctl__rn_o[0:0]),
    .ed5(xl_NW_ctl__eg_ed5[7:0]),
    .ede(xl_NW_ctl__eg_ede[16:0]),
    .bq_v(xl_NW_ctl__eg_bqv[0:0]),
    .bq_last(xl_NW_ctl__eg_bqlast[0:0]),
    .bq_addr(xl_NW_ctl__eg_bqaddr[6:0]),
    .bq_b(xl_NW_ctl__eg_bqb[6:0]),
    .rwq({xq_NW_p0_bfq3__rwq[255:0], xq_NW_p0_bfq2__rwq[255:0], xq_NW_p0_bfq1__rwq[255:0], xq_NW_p0_bfq0__rwq[255:0]}),
    .bq_d(xq_NW_p0_bd__bq_d[2047:0]),
    .x_done(xq_NW_p0_eg__x_done[0:0]),
    .xw_en(xq_NW_p0_eg__xw_en[0:0]),
    .xw_last(xq_NW_p0_eg__xw_last[0:0]),
    .xw_addr(xq_NW_p0_eg__xw_addr[6:0]),
    .xw_grp(xq_NW_p0_eg__xw_grp[6:0]),
    .xw_data(xq_NW_p0_eg__xw_data[2047:0])
  );
  ot_hgi_sm_xload_cl2_bdring #(.PMAX(8), .NR(32)) xq_NW_p1_bd (
    .clk(hb_ckgen__pll_stream[0:0]),
    .r_wsel(xl_NW_ctl__r_wsel[15:0]),
    .zlo(xl_NW_ctl__zlo[0:0]),
    .zhi(xl_NW_ctl__zhi[0:0]),
    .qq_lo(xl_NW_aqlo__q[255:0]),
    .qq_hi(xl_NW_aqhi__q[255:0]),
    .qe_lo(xl_NW_aqlo__e[9:0]),
    .qe_hi(xl_NW_aqhi__e[9:0]),
    .bsel(xl_NW_ctl__bsel[25:0]),
    .lane_en_i(xl_NW_ctl__lane_en[63:0]),
    .bq_d(xq_NW_p1_bd__bq_d[2047:0])
  );
  ot_hgi_sm_xload_cl2_bfqg xq_NW_p1_bfq0 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_ctrl(hb_ckgen__pll_stream[0:0]),
    .clk_m0(hb_ckgen__pll_stream[0:0]),
    .clk_m1(hb_ckgen__pll_stream[0:0]),
    .clk_m2(hb_ckgen__pll_stream[0:0]),
    .clk_m3(hb_ckgen__pll_stream[0:0]),
    .clk_m4(hb_ckgen__pll_stream[0:0]),
    .clk_m5(hb_ckgen__pll_stream[0:0]),
    .clk_m6(hb_ckgen__pll_stream[0:0]),
    .clk_m7(hb_ckgen__pll_stream[0:0]),
    .clk_l0(hb_ckgen__pll_stream[0:0]),
    .clk_l1(hb_ckgen__pll_stream[0:0]),
    .clk_l2(hb_ckgen__pll_stream[0:0]),
    .clk_l3(hb_ckgen__pll_stream[0:0]),
    .clk_l4(hb_ckgen__pll_stream[0:0]),
    .clk_l5(hb_ckgen__pll_stream[0:0]),
    .clk_l6(hb_ckgen__pll_stream[0:0]),
    .clk_l7(hb_ckgen__pll_stream[0:0]),
    .rst_n(xl_NW_ctl__rn_o[0:0]),
    .c_d(xl_NW_ctl__c_d[1023:0]),
    .wce(xl_NW_ctl__c_wce[0:0]),
    .mhi0(xl_NW_ctl__c_mhi[0:0]),
    .mhi1(xl_NW_ctl__c_mhi[0:0]),
    .mhi2(xl_NW_ctl__c_mhi[0:0]),
    .mhi3(xl_NW_ctl__c_mhi[0:0]),
    .mhi4(xl_NW_ctl__c_mhi[0:0]),
    .mhi5(xl_NW_ctl__c_mhi[0:0]),
    .mhi6(xl_NW_ctl__c_mhi[0:0]),
    .mhi7(xl_NW_ctl__c_mhi[0:0]),
    .mlo0(xl_NW_ctl__c_mlo[0:0]),
    .mlo1(xl_NW_ctl__c_mlo[0:0]),
    .mlo2(xl_NW_ctl__c_mlo[0:0]),
    .mlo3(xl_NW_ctl__c_mlo[0:0]),
    .mlo4(xl_NW_ctl__c_mlo[0:0]),
    .mlo5(xl_NW_ctl__c_mlo[0:0]),
    .mlo6(xl_NW_ctl__c_mlo[0:0]),
    .mlo7(xl_NW_ctl__c_mlo[0:0]),
    .wa(xl_NW_ctl__c_wa[6:0]),
    .r_ce(xl_NW_ctl__r_ce[7:0]),
    .r_a(xl_NW_ctl__r_a[6:0]),
    .rwq(xq_NW_p1_bfq0__rwq[255:0])
  );
  ot_hgi_sm_xload_cl2_bfqg xq_NW_p1_bfq1 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_ctrl(hb_ckgen__pll_stream[0:0]),
    .clk_m0(hb_ckgen__pll_stream[0:0]),
    .clk_m1(hb_ckgen__pll_stream[0:0]),
    .clk_m2(hb_ckgen__pll_stream[0:0]),
    .clk_m3(hb_ckgen__pll_stream[0:0]),
    .clk_m4(hb_ckgen__pll_stream[0:0]),
    .clk_m5(hb_ckgen__pll_stream[0:0]),
    .clk_m6(hb_ckgen__pll_stream[0:0]),
    .clk_m7(hb_ckgen__pll_stream[0:0]),
    .clk_l0(hb_ckgen__pll_stream[0:0]),
    .clk_l1(hb_ckgen__pll_stream[0:0]),
    .clk_l2(hb_ckgen__pll_stream[0:0]),
    .clk_l3(hb_ckgen__pll_stream[0:0]),
    .clk_l4(hb_ckgen__pll_stream[0:0]),
    .clk_l5(hb_ckgen__pll_stream[0:0]),
    .clk_l6(hb_ckgen__pll_stream[0:0]),
    .clk_l7(hb_ckgen__pll_stream[0:0]),
    .rst_n(xl_NW_ctl__rn_o[0:0]),
    .c_d(xl_NW_ctl__c_d[1023:0]),
    .wce(xl_NW_ctl__c_wce[1:1]),
    .mhi0(xl_NW_ctl__c_mhi[0:0]),
    .mhi1(xl_NW_ctl__c_mhi[0:0]),
    .mhi2(xl_NW_ctl__c_mhi[0:0]),
    .mhi3(xl_NW_ctl__c_mhi[0:0]),
    .mhi4(xl_NW_ctl__c_mhi[0:0]),
    .mhi5(xl_NW_ctl__c_mhi[0:0]),
    .mhi6(xl_NW_ctl__c_mhi[0:0]),
    .mhi7(xl_NW_ctl__c_mhi[0:0]),
    .mlo0(xl_NW_ctl__c_mlo[0:0]),
    .mlo1(xl_NW_ctl__c_mlo[0:0]),
    .mlo2(xl_NW_ctl__c_mlo[0:0]),
    .mlo3(xl_NW_ctl__c_mlo[0:0]),
    .mlo4(xl_NW_ctl__c_mlo[0:0]),
    .mlo5(xl_NW_ctl__c_mlo[0:0]),
    .mlo6(xl_NW_ctl__c_mlo[0:0]),
    .mlo7(xl_NW_ctl__c_mlo[0:0]),
    .wa(xl_NW_ctl__c_wa[6:0]),
    .r_ce(xl_NW_ctl__r_ce[7:0]),
    .r_a(xl_NW_ctl__r_a[6:0]),
    .rwq(xq_NW_p1_bfq1__rwq[255:0])
  );
  ot_hgi_sm_xload_cl2_bfqg xq_NW_p1_bfq2 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_ctrl(hb_ckgen__pll_stream[0:0]),
    .clk_m0(hb_ckgen__pll_stream[0:0]),
    .clk_m1(hb_ckgen__pll_stream[0:0]),
    .clk_m2(hb_ckgen__pll_stream[0:0]),
    .clk_m3(hb_ckgen__pll_stream[0:0]),
    .clk_m4(hb_ckgen__pll_stream[0:0]),
    .clk_m5(hb_ckgen__pll_stream[0:0]),
    .clk_m6(hb_ckgen__pll_stream[0:0]),
    .clk_m7(hb_ckgen__pll_stream[0:0]),
    .clk_l0(hb_ckgen__pll_stream[0:0]),
    .clk_l1(hb_ckgen__pll_stream[0:0]),
    .clk_l2(hb_ckgen__pll_stream[0:0]),
    .clk_l3(hb_ckgen__pll_stream[0:0]),
    .clk_l4(hb_ckgen__pll_stream[0:0]),
    .clk_l5(hb_ckgen__pll_stream[0:0]),
    .clk_l6(hb_ckgen__pll_stream[0:0]),
    .clk_l7(hb_ckgen__pll_stream[0:0]),
    .rst_n(xl_NW_ctl__rn_o[0:0]),
    .c_d(xl_NW_ctl__c_d[1023:0]),
    .wce(xl_NW_ctl__c_wce[2:2]),
    .mhi0(xl_NW_ctl__c_mhi[0:0]),
    .mhi1(xl_NW_ctl__c_mhi[0:0]),
    .mhi2(xl_NW_ctl__c_mhi[0:0]),
    .mhi3(xl_NW_ctl__c_mhi[0:0]),
    .mhi4(xl_NW_ctl__c_mhi[0:0]),
    .mhi5(xl_NW_ctl__c_mhi[0:0]),
    .mhi6(xl_NW_ctl__c_mhi[0:0]),
    .mhi7(xl_NW_ctl__c_mhi[0:0]),
    .mlo0(xl_NW_ctl__c_mlo[0:0]),
    .mlo1(xl_NW_ctl__c_mlo[0:0]),
    .mlo2(xl_NW_ctl__c_mlo[0:0]),
    .mlo3(xl_NW_ctl__c_mlo[0:0]),
    .mlo4(xl_NW_ctl__c_mlo[0:0]),
    .mlo5(xl_NW_ctl__c_mlo[0:0]),
    .mlo6(xl_NW_ctl__c_mlo[0:0]),
    .mlo7(xl_NW_ctl__c_mlo[0:0]),
    .wa(xl_NW_ctl__c_wa[6:0]),
    .r_ce(xl_NW_ctl__r_ce[7:0]),
    .r_a(xl_NW_ctl__r_a[6:0]),
    .rwq(xq_NW_p1_bfq2__rwq[255:0])
  );
  ot_hgi_sm_xload_cl2_bfqg xq_NW_p1_bfq3 (
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_n(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_ctrl(hb_ckgen__pll_stream[0:0]),
    .clk_m0(hb_ckgen__pll_stream[0:0]),
    .clk_m1(hb_ckgen__pll_stream[0:0]),
    .clk_m2(hb_ckgen__pll_stream[0:0]),
    .clk_m3(hb_ckgen__pll_stream[0:0]),
    .clk_m4(hb_ckgen__pll_stream[0:0]),
    .clk_m5(hb_ckgen__pll_stream[0:0]),
    .clk_m6(hb_ckgen__pll_stream[0:0]),
    .clk_m7(hb_ckgen__pll_stream[0:0]),
    .clk_l0(hb_ckgen__pll_stream[0:0]),
    .clk_l1(hb_ckgen__pll_stream[0:0]),
    .clk_l2(hb_ckgen__pll_stream[0:0]),
    .clk_l3(hb_ckgen__pll_stream[0:0]),
    .clk_l4(hb_ckgen__pll_stream[0:0]),
    .clk_l5(hb_ckgen__pll_stream[0:0]),
    .clk_l6(hb_ckgen__pll_stream[0:0]),
    .clk_l7(hb_ckgen__pll_stream[0:0]),
    .rst_n(xl_NW_ctl__rn_o[0:0]),
    .c_d(xl_NW_ctl__c_d[1023:0]),
    .wce(xl_NW_ctl__c_wce[3:3]),
    .mhi0(xl_NW_ctl__c_mhi[0:0]),
    .mhi1(xl_NW_ctl__c_mhi[0:0]),
    .mhi2(xl_NW_ctl__c_mhi[0:0]),
    .mhi3(xl_NW_ctl__c_mhi[0:0]),
    .mhi4(xl_NW_ctl__c_mhi[0:0]),
    .mhi5(xl_NW_ctl__c_mhi[0:0]),
    .mhi6(xl_NW_ctl__c_mhi[0:0]),
    .mhi7(xl_NW_ctl__c_mhi[0:0]),
    .mlo0(xl_NW_ctl__c_mlo[0:0]),
    .mlo1(xl_NW_ctl__c_mlo[0:0]),
    .mlo2(xl_NW_ctl__c_mlo[0:0]),
    .mlo3(xl_NW_ctl__c_mlo[0:0]),
    .mlo4(xl_NW_ctl__c_mlo[0:0]),
    .mlo5(xl_NW_ctl__c_mlo[0:0]),
    .mlo6(xl_NW_ctl__c_mlo[0:0]),
    .mlo7(xl_NW_ctl__c_mlo[0:0]),
    .wa(xl_NW_ctl__c_wa[6:0]),
    .r_ce(xl_NW_ctl__r_ce[7:0]),
    .r_a(xl_NW_ctl__r_a[6:0]),
    .rwq(xq_NW_p1_bfq3__rwq[255:0])
  );
  ot_hgi_sm_xload_xq_pegress #(.PMAX(8), .NR(32)) xq_NW_p1_eg (
    .clk(hb_ckgen__pll_stream[0:0]),
    .clk_w(hb_ckgen__pll_stream[0:0]),
    .clk_s(hb_ckgen__pll_stream[0:0]),
    .clk_e(hb_ckgen__pll_stream[0:0]),
    .clk_c(hb_ckgen__pll_stream[0:0]),
    .rn(xl_NW_ctl__rn_o[0:0]),
    .ed5(xl_NW_ctl__eg_ed5[7:0]),
    .ede(xl_NW_ctl__eg_ede[16:0]),
    .bq_v(xl_NW_ctl__eg_bqv[0:0]),
    .bq_last(xl_NW_ctl__eg_bqlast[0:0]),
    .bq_addr(xl_NW_ctl__eg_bqaddr[6:0]),
    .bq_b(xl_NW_ctl__eg_bqb[6:0]),
    .rwq({xq_NW_p1_bfq3__rwq[255:0], xq_NW_p1_bfq2__rwq[255:0], xq_NW_p1_bfq1__rwq[255:0], xq_NW_p1_bfq0__rwq[255:0]}),
    .bq_d(xq_NW_p1_bd__bq_d[2047:0]),
    .x_done(xq_NW_p1_eg__x_done[0:0]),
    .xw_en(xq_NW_p1_eg__xw_en[0:0]),
    .xw_last(xq_NW_p1_eg__xw_last[0:0]),
    .xw_addr(xq_NW_p1_eg__xw_addr[6:0]),
    .xw_grp(xq_NW_p1_eg__xw_grp[6:0]),
    .xw_data(xq_NW_p1_eg__xw_data[2047:0])
  );
endmodule
`default_nettype wire
