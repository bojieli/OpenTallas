`timescale 1ns/1ps
// SOURCE CANDIDATE, no available-view alias. See s81_seqmux_source_1340_1021/MODEL.md.
module dsdv_seq_host_cr2 #(parameter integer V = 276, parameter integer STAGE = 0, parameter integer MUT = 0, parameter integer RL = 1, parameter integer RUNG_MUT = 0) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [7:0]    tap_k, sink_k,   // vstop straps (captured pins); seqhost: 0 / 0
    input  wire [V-1:0]  vi_s, output wire [V-1:0] vo_s,      // rung S face (bk_sel)
    input  wire [V-1:0]  vi_n, output wire [V-1:0] vo_n,      // rung N face = vc N face (die lane to s_4N on closed dvrlyh relays)
    input  wire [514:0]  f_host, output wire [76:0] t_host, input wire [3:0] f_lf,
    input  wire [52:0]   f_ks,   output wire [53:0] t_kd,
    output wire [32:0]   s_j,    input  wire [1:0]  s_jd_w, s_jd_e,     // job broadcast to both halves / per-half done
    output wire [291:0]  s_hw_w, s_hw_e, input wire [8:0] s_hc_w, s_hc_e, // per-half host writes / credits + acks
    input  wire [1:0]    st_rg_w, st_rg_e,                               // per-half region status (svc entry st_rg)
    output wire          cw_v, output wire [9:0] cw_a, output wire [255:0] cw_d   // gunit cw port
);
    wire [V-1:0] n23,s32,n34,s43;
    dsdv_seq_host_c #(.V(V),.STAGE(STAGE),.MUT(MUT),.RL(RL)) u_core (.ck(ck), .rst_n(rst_n), .tap_k(tap_k), .sink_k(sink_k), .vi_s(vi_s), .vo_s(vo_s), .f_host(f_host), .t_host(t_host), .f_lf(f_lf), .f_ks(f_ks), .t_kd(t_kd), .s_j(s_j), .s_jd_w(s_jd_w), .s_jd_e(s_jd_e), .s_hw_w(s_hw_w), .s_hw_e(s_hw_e), .s_hc_w(s_hc_w), .s_hc_e(s_hc_e), .st_rg_w(st_rg_w), .st_rg_e(st_rg_e), .cw_v(cw_v), .cw_a(cw_a), .cw_d(cw_d), .vi_n(s32),.vo_n(n23));
    dsdv_sh_ft #(.V(V)) u_l3 (.ck(ck),.ni(n23),.no(n34),.si(s43),.so(s32));
    generate if(MUT==3 || RUNG_MUT==1)begin:g_mut3
        assign vo_n=n34;assign s43=vi_n;
    end else begin:g_l4
        dsdv_sh_ft #(.V(V)) u_l4 (.ck(ck),.ni(n34),.no(vo_n),.si(vi_n),.so(s43));
    end endgenerate
endmodule

module dsdv_seq_host_mu_h #(parameter integer V = 276, parameter integer STAGE = 0, parameter integer MUT = 0,
                          parameter integer NSLOT = 1, parameter integer MU_MUT = 0) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [7:0]    tap_k, sink_k,
    input  wire [V-1:0]  vi_s, output wire [V-1:0] vo_s,
    input  wire [V-1:0]  vi_n, output wire [V-1:0] vo_n,
    input  wire [514:0]  f_host, output wire [76:0] t_host, input wire [3:0] f_lf,
    input  wire [52:0]   f_ks,   output wire [53:0] t_kd,
    input  wire [25:0]   f_mc,   output wire [3:0]  t_mf,
    output wire [32:0]   s_j,    input  wire [1:0]  s_jd_w, s_jd_e,
    output wire [291:0]  s_hw_w, s_hw_e, input wire [8:0] s_hc_w, s_hc_e,
    input  wire [1:0]    st_rg_w, st_rg_e,
    output wire          cw_v, output wire [9:0] cw_a, output wire [255:0] cw_d
);
    wire [53:0] kd;
    dsdv_seq_host_cr2 #(.V(V), .STAGE(STAGE), .MUT(MUT)) u_u (.ck(ck), .rst_n(rst_n), .tap_k(tap_k), .sink_k(sink_k),
        .vi_s(vi_s), .vo_s(vo_s), .vi_n(vi_n), .vo_n(vo_n), .f_host(f_host), .t_host(t_host), .f_lf(f_lf), .f_ks(f_ks),
        .t_kd(kd), .s_j(s_j), .s_jd_w(s_jd_w), .s_jd_e(s_jd_e), .s_hw_w(s_hw_w), .s_hw_e(s_hw_e), .s_hc_w(s_hc_w),
        .s_hc_e(s_hc_e), .st_rg_w(st_rg_w), .st_rg_e(st_rg_e), .cw_v(cw_v), .cw_a(cw_a), .cw_d(cw_d));
    generate if (NSLOT > 1) begin : g_mu
        wire [31:0] ku;
        dsdv_mu_hslot #(.NSLOT(NSLOT), .MUT(MU_MUT)) u_hs (.ck(ck), .rst_n(rst_n), .f_ks(f_ks), .f_kd(kd), .f_mc(f_mc),
            .t_ku(ku), .t_mf(t_mf));
        assign t_kd = {kd[53:32], ku[30:0], 1'b0};      // kd[31:0] = 0 by the unit's contract (sh_sq kd_o)
    end else begin : g_su
        assign t_kd = kd; assign t_mf = 4'd0;
    end endgenerate
endmodule

module dsdv_seq_host_mux_h (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [7:0]    tap_k, sink_k,
    input  wire [275:0]  vi_s, output wire [275:0] vo_s,
    input  wire [275:0]  vi_n, output wire [275:0] vo_n,
    input  wire [514:0]  f_host, output wire [76:0] t_host, input wire [3:0] f_lf,
    input  wire [52:0]   f_ks,   output wire [53:0] t_kd,
    output wire [3:0]    t_mf,
    output wire [32:0]   s_j,    input  wire [1:0]  s_jd_w, s_jd_e,
    output wire [291:0]  s_hw_w, s_hw_e, input wire [8:0] s_hc_w, s_hc_e,
    input  wire [1:0]    st_rg_w, st_rg_e,
    output wire          cw_v, output wire [9:0] cw_a, output wire [255:0] cw_d,
    output wire [33:0]   mu_c_7n, mu_c_7s, mu_c_0n, mu_c_0s,
    output wire [10:0]   mu_rc_7n, mu_rc_7s, mu_rc_0n, mu_rc_0s,
    input  wire [31:0]   mu_rt_7n, mu_rt_0n
);
    // CSR decode (the f_host word {h_cls 2, h_d 512, h_v}; h_d[7:0] index, h_d[57:32] value) into one flop each
    wire csr = f_host[0] && f_host[514:513] == 2'd0;
    reg [25:0] mc, mw;
    always @(posedge ck) begin
        mc <= (csr && f_host[8:1] == 8'h15) ? f_host[58:33] : 26'd0;
        mw <= (csr && f_host[8:1] == 8'h16) ? f_host[58:33] : 26'd0;
    end
    wire [3:0] hmf; wire [1:0] wf;
    dsdv_seq_host_mu_h #(.NSLOT(47)) u (.ck(ck), .rst_n(rst_n), .tap_k(tap_k), .sink_k(sink_k),
        .vi_s(vi_s), .vo_s(vo_s), .vi_n(vi_n), .vo_n(vo_n), .f_host(f_host), .t_host(t_host), .f_lf(f_lf), .f_ks(f_ks),
        .t_kd(t_kd), .f_mc(mc), .t_mf(hmf), .s_j(s_j), .s_jd_w(s_jd_w), .s_jd_e(s_jd_e), .s_hw_w(s_hw_w),
        .s_hw_e(s_hw_e), .s_hc_w(s_hc_w), .s_hc_e(s_hc_e), .st_rg_w(st_rg_w), .st_rg_e(st_rg_e), .cw_v(cw_v),
        .cw_a(cw_a), .cw_d(cw_d));
    dsdv_mu_hwin_capture_1019 #(.NSLOT(47),.NEV(16),.NEP(4),.NRT(2),
        .HEAD_STAGE(1),.COMPACT_PTR(1),.CHECK_STAGE(1),.LIVE_COUNT(1),.RAW_SELECT(1),.LOCAL_BOOT(1),
        .EARLY_HEAD_CAPTURE(1),.CFG_RELAY(1),.DUE_COPIES(2),.SAFE_NATIVE(1),.LOCAL_RECORD(1)) u_win (.ck(ck), .rst_n(rst_n), .f_ks(f_ks), .f_mc(mc), .f_mw(mw),
        .mu_c({mu_c_0s, mu_c_0n, mu_c_7s, mu_c_7n}), .mu_rc({mu_rc_0s, mu_rc_0n, mu_rc_7s, mu_rc_7n}),
        .mu_rt({mu_rt_0n, mu_rt_7n}), .t_wf(wf));
    assign t_mf = {hmf[3] | wf[1], hmf[2] | wf[0], hmf[1:0]};
endmodule
