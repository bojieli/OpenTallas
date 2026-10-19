`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-SMH2 (2026-10-17): dsfd_su_t_smhq, the LANE-QUAD regional cluster of one softmax head (x4 per head, hardened once).
// The g2 single cluster dsfd_su_t_smh (1,037 x 769 um, one clock pin) measured TT insertion 1.04-1.29 ns / spread 249 ps
// and setup -646 ps (rst_in unregistered to 26 children) / -330 ps (one relay to a lane 1 mm away).  The head is now
// 4 of these quads + 1 root cluster dsfd_su_t_smhr, each ~400 um with its own clock pin beside its register band and
// its own registered reset relay; every inter-cluster hop is registered at both ends (flop-last / flop-first).
//
//   quad q (strap cfg_q): lanes 4q .. 4q+3 (dsfd_su_t_sml) and divide pairs 2q, 2q+1 (dsfd_su_t_smd, which read
//   operand lanes 4q .. 4q+3 only: the divide engines never talk to the lanes).
//   Station split (SRL = 2 production, the cycle count of every path is that of ot_s81_su_smh at DOP = SRL):
//     tap  -> lanes / divide   SRL stations here (flop-first)
//     root -> lanes / divide   1 station in the root (flop-last) + SRL - 1 here (flop-first)
//     lanes -> root            1 station here (flop-last: q_*) + SRL - 1 in the root (flop-first)
//     lanes -> tap  (e row)    SRL stations here (flop-last)
//     divide -> tap (o row)    SRL stations here (flop-last)
//   Only quad 0's valids (lane 1, lane 0 sink) and its e_v / o_v are used by the parent (lockstep lanes).
//   SMH 10-18: EVERY pin is registered (owner pin-register rule): the cfg_q strap is captured flop-first (static, no
//   cycle cost) and the divide faults f leave flop-last (+1 edge on the sticky fault, read only at job end).  The 10-17 kit had
//   cfg_q -> child cfg_p / sk_en and child o_f -> f unregistered, so the hard children's clock pins (spine-compensated
//   ~225 ps early for their own insertion) were the pin flops: TT pin-flop spread 240 ps on raw child clock pins.
// MUT (bench only; the kit builds MUT 0): 5 = stale den in the divide engines (behavioural smd STALEDEN),
//   6 = the root -> quad hop one station short (a split-latency mutant).
// ---------------------------------------------------------------------------------------------------------------------
module dsfd_su_t_smhq #(
    parameter integer SRL = 2,
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_in,                       // active low; relayed through this cluster's own synchroniser
    input  wire [1:0]    cfg_q,                        // strap: the quad index q of the head
    // from the tap (registered there)
    input  wire          s_v,
    input  wire          p_v,
    input  wire          c_v,
    input  wire [6:0]    c_nv,
    input  wire [31:0]   c_scale,
    input  wire [31:0]   c_sink,
    input  wire          cs_v,
    input  wire [4:0]    cs_i,
    input  wire [63:0]   cs_d,
    input  wire [127:0]  d,                            // operand lanes 4q .. 4q+3
    // from the root (registered there)
    input  wire          m_v,
    input  wire [31:0]   m_nmb,
    input  wire          dn_v,
    input  wire [31:0]   dn,
    // to the root (registered here)
    output wire          q_mxv,
    output wire          q_ev,
    output wire          q_el,
    output wire          q_skv,
    output wire [127:0]  q_mx,
    output wire [127:0]  q_e,
    // to the tap (registered here)
    output wire          e_v,
    output wire [127:0]  e_d,
    output wire          o_v,
    output wire [63:0]   o_d,
    output wire [1:0]    f
);
    localparam integer RQ = (MUT == 6) ? SRL - 2 : SRL - 1;    // root -> quad stations on this side
    // registered reset relay: async assert, two-flop release; the only rst_in loads are these two flops
    reg rr0, rr1;
    always @(posedge clk or negedge rst_in)
        if (!rst_in) begin rr0 <= 1'b0; rr1 <= 1'b0; end else begin rr0 <= 1'b1; rr1 <= rr0; end
    wire rst_l = rr1;

    wire rs_v, rp_v, rc_v, rcs_v; wire [127:0] rd_d; wire [6:0] rc_nv; wire [31:0] rc_scale, rc_sink;
    wire [4:0] rcs_i; wire [63:0] rcs_d;
    ot_hdc_delay #(.W(4), .D(SRL), .RESET(1)) u_tv (.clk(clk), .rst_n(rst_l), .d({s_v, p_v, c_v, cs_v}),
        .q({rs_v, rp_v, rc_v, rcs_v}));
    ot_hdc_delay #(.W(7 + 32 + 32 + 5 + 64), .D(SRL)) u_td (.clk(clk), .rst_n(rst_l),
        .d({c_nv, c_scale, c_sink, cs_i, cs_d}), .q({rc_nv, rc_scale, rc_sink, rcs_i, rcs_d}));
    ot_hdc_delay #(.W(128), .D(SRL)) u_tdd (.clk(clk), .rst_n(rst_l), .d(d), .q(rd_d));

    wire rmv, rdv; wire [31:0] rnmb, rden;
    ot_hdc_delay #(.W(2), .D(RQ), .RESET(1)) u_rv (.clk(clk), .rst_n(rst_l), .d({m_v, dn_v}), .q({rmv, rdv}));
    ot_hdc_delay #(.W(64), .D(RQ)) u_rd (.clk(clk), .rst_n(rst_l), .d({m_nmb, dn}), .q({rnmb, rden}));

    wire [3:0] l_mxv, l_ev, l_es, l_el; wire [127:0] l_mx, l_e;
    reg [1:0] r_cfg;                                   // strap, flop-first (static: no reset needed)
    always @(posedge clk) r_cfg <= cfg_q;
    wire sk0 = (r_cfg == 2'd0);                        // the head's lane 0 carries the sink column
    genvar ln, pp;
    generate for (ln = 0; ln < 4; ln = ln + 1) begin : g_l
        dsfd_su_t_sml u_sml (
            .ck(clk), .rst(rst_l), .sk_en(ln == 0 ? sk0 : 1'b0), .i_cv(rc_v), .i_nv(rc_nv), .i_scale(rc_scale),
            .i_sink(rc_sink), .i_sv(rs_v), .i_s(rd_d[32 * ln +: 32]),
            .i_mv(rmv), .i_nmb(rnmb), .o_mxv(l_mxv[ln]), .o_mx(l_mx[32 * ln +: 32]),
            .o_ev(l_ev[ln]), .o_es(l_es[ln]), .o_el(l_el[ln]), .o_e(l_e[32 * ln +: 32]));
    end endgenerate
    // lanes -> root: station 1 (flop-last)
    ot_hdc_delay #(.W(4), .D(1), .RESET(1)) u_lv (.clk(clk), .rst_n(rst_l),
        .d({l_mxv[1], l_ev[1], l_el[1], l_ev[0] && l_es[0]}), .q({q_mxv, q_ev, q_el, q_skv}));
    ot_hdc_delay #(.W(256), .D(1)) u_ld (.clk(clk), .rst_n(rst_l), .d({l_mx, l_e}), .q({q_mx, q_e}));
    // lanes -> tap: the remaining SRL - 1 stations
    ot_hdc_delay #(.W(1), .D(SRL - 1), .RESET(1)) u_ev (.clk(clk), .rst_n(rst_l), .d(q_ev), .q(e_v));
    ot_hdc_delay #(.W(128), .D(SRL - 1)) u_ed (.clk(clk), .rst_n(rst_l), .d(q_e), .q(e_d));

    // divide engines: pairs 2q + pp
    wire [1:0] d_ov; wire [63:0] d_o; wire [1:0] d_f;
    generate for (pp = 0; pp < 2; pp = pp + 1) begin : g_p
        wire [2:0] CP = {r_cfg, pp[0]};
        if (MUT == 5) begin : g_mut
            ot_s81_su_smd #(.LPH(16), .LM(5), .LA(4), .STALEDEN(1)) u_smd (
                .clk(clk), .rst_in(rst_l), .cfg_p(CP), .i_pv(rp_v), .i_pa(rd_d[64 * pp +: 64]),
                .i_dv(rdv), .i_den(rden), .i_csv(rcs_v), .i_csi(rcs_i), .i_csd(rcs_d),
                .o_ov(d_ov[pp]), .o_o(d_o[32 * pp +: 32]), .o_f(d_f[pp]));
        end else begin : g_hard
            dsfd_su_t_smd u_smd (
                .ck(clk), .rst(rst_l), .cfg_p(CP), .i_pv(rp_v), .i_pa(rd_d[64 * pp +: 64]),
                .i_dv(rdv), .i_den(rden), .i_csv(rcs_v), .i_csi(rcs_i), .i_csd(rcs_d),
                .o_ov(d_ov[pp]), .o_o(d_o[32 * pp +: 32]), .o_f(d_f[pp]));
        end
    end endgenerate
    ot_hdc_delay #(.W(1), .D(SRL), .RESET(1)) u_ov (.clk(clk), .rst_n(rst_l), .d(d_ov[0]), .q(o_v));
    ot_hdc_delay #(.W(64), .D(SRL)) u_od (.clk(clk), .rst_n(rst_l), .d(d_o), .q(o_d));
    ot_hdc_delay #(.W(2), .D(1), .RESET(1)) u_fo (.clk(clk), .rst_n(rst_l), .d(d_f), .q(f));   // faults flop-last
endmodule
