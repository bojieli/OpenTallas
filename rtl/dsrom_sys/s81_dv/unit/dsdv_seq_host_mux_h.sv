`timescale 1ns/1ps
// S81-ELEM2-SEQ 10-21: dsdv_seq_host_mux_h = G9 SUCCESSOR of the G8IQ die master dsdv_seq_host_mux (dsdv_mu_hwin.sv, blob
// 153949fc), SAME PORTS.  Composition (lanes/TOK-FUNC2-SEQ.md Step 1/2):
//   CSR flops mc / mw (host CSR 0x15 / 0x16, as dsdv_seq_host_mux)
//   u_c  dsdv_seq_host_c  = hard dsdv_seq_host_h (lk CLOSED s10hq 649101c0d + sq + vc; lk APIPE 10 => host path +2 vs G8IQ)
//   u_d0 / u_d1 dsdv_sh_ft = the two registered 276-b rung hops of dsdv_seq_host's ft L3 / L4 (k = 2 reproduces
//        dsdv_seq_host exactly, dsdv_seq_host_c.sv header; the same pair dsdv_seq_host_bw uses as die-lane stand-in)
//   u_hs dsdv_mu_hslot #(NSLOT 47) = CLOSED adb53b6fe view (blob 8e9b03d6 == G8IQ), wired as dsdv_seq_host_mu
//   u_win dsdv_mu_hwin #(47, NEV 8, NEP 4, NRT 2) = the hwin SUCCESSOR view (S81-ELEM2-HWIN; same ports)
// Latency deltas vs G8IQ (calendar/compiler must take them; no aliasing): host path +2 (lk APIPE 10); hwin per its successor.
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
    wire csr = f_host[0] && f_host[514:513] == 2'd0;
    reg [25:0] mc, mw;
    always @(posedge ck) begin
        mc <= (csr && f_host[8:1] == 8'h15) ? f_host[58:33] : 26'd0;
        mw <= (csr && f_host[8:1] == 8'h16) ? f_host[58:33] : 26'd0;
    end
    wire [275:0] cn, cs, n1, s1;
    wire [53:0] kd; wire [31:0] ku; wire [3:0] hmf; wire [1:0] wf;
    dsdv_seq_host_c u_c (.ck(ck), .rst_n(rst_n), .tap_k(tap_k), .sink_k(sink_k),
        .vi_s(vi_s), .vo_s(vo_s), .vi_n(cs), .vo_n(cn), .f_host(f_host), .t_host(t_host), .f_lf(f_lf), .f_ks(f_ks), .t_kd(kd),
        .s_j(s_j), .s_jd_w(s_jd_w), .s_jd_e(s_jd_e), .s_hw_w(s_hw_w), .s_hw_e(s_hw_e), .s_hc_w(s_hc_w), .s_hc_e(s_hc_e),
        .st_rg_w(st_rg_w), .st_rg_e(st_rg_e), .cw_v(cw_v), .cw_a(cw_a), .cw_d(cw_d));
    dsdv_sh_ft #(.V(276)) u_d0 (.ck(ck), .ni(cn), .no(n1), .si(s1), .so(cs));       // rung hop L3
    dsdv_sh_ft #(.V(276)) u_d1 (.ck(ck), .ni(n1), .no(vo_n), .si(vi_n), .so(s1));   // rung hop L4
    dsdv_mu_hslot #(.NSLOT(47)) u_hs (.ck(ck), .rst_n(rst_n), .f_ks(f_ks), .f_kd(kd), .f_mc(mc), .t_ku(ku), .t_mf(hmf));
    assign t_kd = {kd[53:32], ku[30:0], 1'b0};          // kd[31:0] = 0 by the unit's contract (sh_sq kd_o), as dsdv_seq_host_mu
    dsdv_mu_hwin #(.NSLOT(47), .NEV(8), .NEP(4), .NRT(2)) u_win (.ck(ck), .rst_n(rst_n), .f_ks(f_ks), .f_mc(mc), .f_mw(mw),
        .mu_c({mu_c_0s, mu_c_0n, mu_c_7s, mu_c_7n}), .mu_rc({mu_rc_0s, mu_rc_0n, mu_rc_7s, mu_rc_7n}),
        .mu_rt({mu_rt_0n, mu_rt_7n}), .t_wf(wf));
    assign t_mf = {hmf[3] | wf[1], hmf[2] | wf[0], hmf[1:0]};
endmodule
