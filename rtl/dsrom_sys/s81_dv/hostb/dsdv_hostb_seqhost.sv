`timescale 1ns/1ps
`default_nettype none
// Source-only explicit real seqhost consumer composition. HOSTB_ENABLE=0 preserves input path.
module dsdv_hostb_seqhost #(parameter integer V = 276, parameter integer STAGE = 0, parameter integer MUT = 0, parameter integer RL = 1, parameter integer HOSTB_ENABLE = 0) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [7:0]    tap_k, sink_k,   // vstop straps (captured pins); seqhost: 0 / 0
    input  wire [V-1:0]  vi_s, output wire [V-1:0] vo_s,      // rung S face (bk_sel)
    input  wire [V-1:0]  vi_n, output wire [V-1:0] vo_n,      // rung N face (s_4N)
    input wire select_hbe, input wire [514:0] hbe_f_host, input wire [52:0] starter_f_ks,
    output wire [52:0] engram_f_ks, output wire [2:0] hostb_fault,
    input  wire [514:0]  f_host, output wire [76:0] t_host, input wire [3:0] f_lf,
    input  wire [52:0]   f_ks,   output wire [53:0] t_kd,
    output wire [32:0]   s_j,    input  wire [1:0]  s_jd_w, s_jd_e,     // job broadcast to both halves / per-half done
    output wire [291:0]  s_hw_w, s_hw_e, input wire [8:0] s_hc_w, s_hc_e, // per-half host writes / credits + acks
    input  wire [1:0]    st_rg_w, st_rg_e,                               // per-half region status (svc entry st_rg)
    output wire          cw_v, output wire [9:0] cw_a, output wire [255:0] cw_d   // gunit cw port
);
 wire [514:0] landed_host;wire [52:0] landed_ks;
 dsdv_hostb_landing #(.ENABLE(HOSTB_ENABLE)) u_landing(.ck(ck),.rst_n(rst_n),.select_hbe(select_hbe),
 .legacy_f_host(f_host),.hbe_f_host(hbe_f_host),.legacy_f_ks(f_ks),.starter_f_ks(starter_f_ks),
 .seq_f_host(landed_host),.seq_f_ks(landed_ks),.engram_f_ks(engram_f_ks),.fault(hostb_fault));
 dsdv_seq_host #(.V(V),.STAGE(STAGE),.MUT(MUT),.RL(RL)) u_seqhost(
 .ck(ck),.rst_n(rst_n),.tap_k(tap_k),.sink_k(sink_k),.vi_s(vi_s),.vo_s(vo_s),.vi_n(vi_n),.vo_n(vo_n),
 .f_host(landed_host),.t_host(t_host),.f_lf(f_lf),.f_ks(landed_ks),.t_kd(t_kd),.s_j(s_j),
 .s_jd_w(s_jd_w),.s_jd_e(s_jd_e),.s_hw_w(s_hw_w),.s_hw_e(s_hw_e),.s_hc_w(s_hc_w),.s_hc_e(s_hc_e),
 .st_rg_w(st_rg_w),.st_rg_e(st_rg_e),.cw_v(cw_v),.cw_a(cw_a),.cw_d(cw_d));
endmodule
`default_nettype wire
