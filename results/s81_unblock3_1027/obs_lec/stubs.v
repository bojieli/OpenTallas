module ot_rst_relay #(parameter integer REGIONS=1, SYNC_STAGES=2, TREE_STAGES=1) (input wire clk, input wire rst_n_in, output wire [REGIONS-1:0] rst_n); reg [REGIONS-1:0] q; always @(posedge clk or negedge rst_n_in) if(!rst_n_in) q<=0; else q<={REGIONS{1'b1}}; assign rst_n=q; endmodule
(* blackbox *) module dsdv_hostb_source #(parameter integer HOSTB_ENABLE=0, STATIC_KS6=0, STATIC_KS_SPAN=0, parameter [31:0] STATIC_KS_GRAPH_TAG=0) (
 input wire ck, rst_n, select_hbe, upstream_fault, input wire [514:0] f_host, hbe_f_host, input wire [52:0] f_ks, starter_f_ks,
 input wire [2:0] hbe_ks_slot, output wire [514:0] issue_host, output wire [52:0] issue_ks, engram_f_ks, output wire [2:0] hostb_fault, output wire hb_starter_armed); endmodule
(* blackbox *) module dsdv_seq_host_mux (input wire ck, rst_n, input wire [7:0] tap_k, sink_k, input wire [275:0] vi_s, output wire [275:0] vo_s,
 input wire [275:0] vi_n, output wire [275:0] vo_n, input wire [514:0] f_host, output wire [76:0] t_host, input wire [3:0] f_lf,
 input wire [52:0] f_ks, output wire [53:0] t_kd, output wire [3:0] t_mf, output wire [32:0] s_j, input wire [1:0] s_jd_w, s_jd_e,
 output wire [291:0] s_hw_w, s_hw_e, input wire [8:0] s_hc_w, s_hc_e, input wire [1:0] st_rg_w, st_rg_e,
 output wire cw_v, output wire [9:0] cw_a, output wire [255:0] cw_d, output wire [33:0] mu_c_7n, mu_c_7s, mu_c_0n, mu_c_0s,
 output wire [10:0] mu_rc_7n, mu_rc_7s, mu_rc_0n, mu_rc_0s, input wire [31:0] mu_rt_7n, mu_rt_0n); endmodule
