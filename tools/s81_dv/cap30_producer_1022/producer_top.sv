module producer_top #(parameter integer HOSTB_ENABLE=0, STATIC_KS6=0,
 parameter integer STATIC_KS_SPAN=0, parameter [31:0] STATIC_KS_GRAPH_TAG=0) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [7:0]    tap_k, sink_k,
    input  wire [275:0]  vi_s, output wire [275:0] vo_s,
    input  wire [275:0]  vi_n, output wire [275:0] vo_n,
    input wire select_hbe,input wire [514:0] hbe_f_host,input wire [52:0] starter_f_ks,
    input wire [2:0] hbe_ks_slot,
    output wire [52:0] engram_f_ks,
    output wire hb_starter_armed,
    input  wire sid_ri, vid_ri, output wire sid_ro, vid_ro,   // S81/PORTFIX-FLT 10-25 fault rings (t_mf / hostb_fault / hb_job_active dropped)
    input  wire [514:0]  f_host, output wire [76:0] t_host, input wire [3:0] f_lf,
    input  wire [52:0]   f_ks,   output wire [53:0] t_kd,
    output wire [32:0]   s_j,    input  wire [1:0]  s_jd_w, s_jd_e,
    output wire [291:0]  s_hw_w, s_hw_e, input wire [8:0] s_hc_w, s_hc_e,
    input  wire [1:0]    st_rg_w, st_rg_e,
    output wire          cw_v, output wire [9:0] cw_a, output wire [255:0] cw_d,
    output wire [33:0]   mu_c_7n, mu_c_7s, mu_c_0n, mu_c_0s,
    output wire [10:0]   mu_rc_7n, mu_rc_7s, mu_rc_0n, mu_rc_0s,
    input  wire [31:0]   mu_rt_7n, mu_rt_0n
);
 dsdv_hostb_seqhost_mux #(.HOSTB_ENABLE(0),.STATIC_KS6(0)) dut (.ck(ck),.rst_n(rst_n),.tap_k(tap_k),.sink_k(sink_k),.vi_s(vi_s),.vi_n(vi_n),.select_hbe(select_hbe),.hbe_ks_slot(hbe_ks_slot),.engram_f_ks(engram_f_ks),.hb_starter_armed(hb_starter_armed),.sid_ri(sid_ri),.vid_ri(vid_ri),.sid_ro(sid_ro),.vid_ro(vid_ro),.f_host(f_host),.f_ks(f_ks),.s_j(s_j),.s_jd_e(s_jd_e),.s_hw_w(s_hw_w),.s_hw_e(s_hw_e),.s_hc_e(s_hc_e),.st_rg_w(st_rg_w),.st_rg_e(st_rg_e),.cw_v(cw_v),.mu_c_7n(mu_c_7n),.mu_c_7s(mu_c_7s),.mu_c_0n(mu_c_0n),.mu_c_0s(mu_c_0s),.mu_rc_7n(mu_rc_7n),.mu_rc_7s(mu_rc_7s),.mu_rc_0n(mu_rc_0n),.mu_rc_0s(mu_rc_0s),.mu_rt_7n(mu_rt_7n),.mu_rt_0n(mu_rt_0n));
endmodule
