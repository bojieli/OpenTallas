`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-2 (2026-10-17, S81-DV p4h): ONE HEAD of the S81 SU softmax (SE / SO), the per-head share that sits in each of the
// 16 regional service slices (1/16 of the SM tiles; the old 2-head SM stop on the 16-slot spine is gone).
//
//   ot_s81_su_smh = the lane subtree of one head of the dsfd_sp_su_h SM stop (g_sm.g_h), unchanged leaf for leaf:
//     16 x ot_s81_su_sml (lane), 1 x ot_s81_su_smc (sum), 1 x ot_s81_su_smr (root), 8 x ot_s81_su_smd (divide), and the
//     SRL equal-depth relay stations on every link between them (lanes in lockstep).
//   The tap side (job, parameters, cos / sin stream, result rows) is outside: in the slab it is ot_s81_su_smt (one per
//   2-head stop, -DSU_SMU embedding); in the DV slice it is the per-head tap ot_s81_su_smq.
//   DOP: stations on the operand row before the lanes.  The slab's spine row is SRL + 2 behind the tap's valids (the
//   tap's pin + valid registers); the smq tap forwards its registered row with the valids, so DOP = SRL there.
// Values and cycles are those of the slab's head h (bit-exact gate: tools/s81_suhc/su_gate.py run --hier --smu).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_su_smh #(
    parameter integer SM_NVMAX = 40, LM = 5, LA = 4, SRL = 2, MUT = 0,
    parameter integer DOP = SRL + 2
) (
    input  wire          clk,
    input  wire          rst_in,                       // the stop's reset (each leaf has its own two-flop relay)
    // from the tap (registered there)
    input  wire          s_v,                          // a score vector (SE)
    input  wire          p_v,                          // a PV vector (SO)
    input  wire          c_v,                          // SE configuration pulse
    input  wire [6:0]    c_nv,
    input  wire [2:0]    c_lt,
    input  wire [31:0]   c_scale,
    input  wire [31:0]   c_sink,                       // this head's sink
    input  wire          cs_v,                         // cos / sin pair cs_i
    input  wire [4:0]    cs_i,
    input  wire [63:0]   cs_d,
    input  wire [511:0]  d,                            // this head's operand row (16 lanes x 32 b)
    // to the tap
    output wire          e_v,                          // e vector (16 lanes)
    output wire [511:0]  e_d,
    output wire          o_v,                          // o vector (16 lanes BF16)
    output wire [255:0]  o_d,
    output wire          den_v,                        // den reached the divide engines
    output wire [7:0]    f                             // the divide engines' sticky faults
);
    // relayed copies (SRL stations) of the tap's outputs
    wire rs_v, rp_v, rc_v, rcs_v; wire [511:0] rd_d; wire [6:0] rc_nv; wire [2:0] rc_lt; wire [31:0] rc_scale;
    wire [31:0] rc_sink; wire [4:0] rcs_i; wire [63:0] rcs_d;
    ot_hdc_delay #(.W(4), .D(SRL), .RESET(1)) u_tv (.clk(clk), .rst_n(rst_in), .d({s_v, p_v, c_v, cs_v}),
        .q({rs_v, rp_v, rc_v, rcs_v}));
    ot_hdc_delay #(.W(7 + 3 + 32 + 32 + 5 + 64), .D(SRL)) u_td (.clk(clk), .rst_n(rst_in),
        .d({c_nv, c_lt, c_scale, c_sink, cs_i, cs_d}), .q({rc_nv, rc_lt, rc_scale, rc_sink, rcs_i, rcs_d}));
    ot_hdc_delay #(.W(512), .D(DOP)) u_tdd (.clk(clk), .rst_n(rst_in), .d(d), .q(rd_d));

    wire [15:0] l_mxv, l_ev, l_es, l_el; wire [511:0] l_mx, l_e;
    wire mv, dv0; wire [31:0] nmb, den;
    wire rmv, rdv; wire [31:0] rnmb, rden;
    ot_hdc_delay #(.W(2), .D(SRL), .RESET(1)) u_rv (.clk(clk), .rst_n(rst_in), .d({mv, dv0}), .q({rmv, rdv}));
    ot_hdc_delay #(.W(64), .D(SRL)) u_rd (.clk(clk), .rst_n(rst_in), .d({nmb, den}), .q({rnmb, rden}));
    genvar ln, pp;
    // SVC-SMS-ORDER (rc16, 11-23, -DOT_SVC_BCAST, opt-in): the SRL stations above are ONE shared chain each, so their last
    // stage drives all 16 u_sml and 8 u_smd over the 4 engine rows.  Under BCAST each lane pair (2 u_sml + its u_smd, one
    // pair per engine row) takes a KEPT copy of the last station (same D, same depth SRL, 0 cycles); the shared chains
    // end in 8 loads.  The originals still feed the sum / root and den_v.
    wire [7:0]   b_cv, b_sv, b_mv, b_pv, b_csv, b_dv;
    wire [7*8-1:0] b_nv; wire [32*8-1:0] b_scale, b_sink, b_nmb, b_den; wire [5*8-1:0] b_csi; wire [64*8-1:0] b_csd;
`ifdef OT_SVC_BCAST
    generate if (SRL >= 1) begin : g_bc
        wire m_cv, m_sv, m_pv, m_csv, m_mv, m_dv; wire [6:0] m_nv; wire [31:0] m_scale, m_sink, m_nmb, m_den;
        wire [4:0] m_csi; wire [63:0] m_csd;
        ot_hdc_delay #(.W(4), .D(SRL - 1), .RESET(1)) u_tvm (.clk(clk), .rst_n(rst_in), .d({s_v, p_v, c_v, cs_v}),
            .q({m_sv, m_pv, m_cv, m_csv}));
        ot_hdc_delay #(.W(7 + 32 + 32 + 5 + 64), .D(SRL - 1)) u_tdm (.clk(clk), .rst_n(rst_in),
            .d({c_nv, c_scale, c_sink, cs_i, cs_d}), .q({m_nv, m_scale, m_sink, m_csi, m_csd}));
        ot_hdc_delay #(.W(2), .D(SRL - 1), .RESET(1)) u_rvm (.clk(clk), .rst_n(rst_in), .d({mv, dv0}), .q({m_mv, m_dv}));
        ot_hdc_delay #(.W(64), .D(SRL - 1)) u_rdm (.clk(clk), .rst_n(rst_in), .d({nmb, den}), .q({m_nmb, m_den}));
        for (pp = 0; pp < 8; pp = pp + 1) begin : g_k
            ot_hdc_v41x_kreg #(.W(6), .R(1)) u_v (.clk(clk), .rst_n(rst_in), .d({m_cv, m_sv, m_mv, m_pv, m_csv, m_dv}),
                .q({b_cv[pp], b_sv[pp], b_mv[pp], b_pv[pp], b_csv[pp], b_dv[pp]}));
            ot_hdc_v41x_kreg #(.W(7 + 32 + 32 + 32 + 5 + 64 + 32), .R(0)) u_d (.clk(clk), .rst_n(rst_in),
                .d({m_nv, m_scale, m_sink, m_nmb, m_csi, m_csd, m_den}),
                .q({b_nv[7*pp +: 7], b_scale[32*pp +: 32], b_sink[32*pp +: 32], b_nmb[32*pp +: 32], b_csi[5*pp +: 5],
                    b_csd[64*pp +: 64], b_den[32*pp +: 32]}));
        end
    end else begin : g_bc0
`else
    generate if (1) begin : g_bc0
`endif
        assign b_cv = {8{rc_v}}; assign b_sv = {8{rs_v}}; assign b_mv = {8{rmv}}; assign b_pv = {8{rp_v}};
        assign b_csv = {8{rcs_v}}; assign b_dv = {8{rdv}};
        assign b_nv = {8{rc_nv}}; assign b_scale = {8{rc_scale}}; assign b_sink = {8{rc_sink}}; assign b_nmb = {8{rnmb}};
        assign b_den = {8{rden}}; assign b_csi = {8{rcs_i}}; assign b_csd = {8{rcs_d}};
    end endgenerate
    generate for (ln = 0; ln < 16; ln = ln + 1) begin : g_l
        wire sken = (ln == 0);
        ot_s81_su_sml #(.NVMAX(SM_NVMAX), .LM(LM), .LA(LA)) u_sml (
            .clk(clk), .rst_in(rst_in), .sk_en(sken), .i_cv(b_cv[ln/2]), .i_nv(b_nv[7*(ln/2) +: 7]), .i_scale(b_scale[32*(ln/2) +: 32]),
            .i_sink(b_sink[32*(ln/2) +: 32]), .i_sv(b_sv[ln/2]), .i_s(rd_d[32 * ln +: 32]),
            .i_mv(b_mv[ln/2]), .i_nmb(b_nmb[32*(ln/2) +: 32]), .o_mxv(l_mxv[ln]), .o_mx(l_mx[32 * ln +: 32]),
            .o_ev(l_ev[ln]), .o_es(l_es[ln]), .o_el(l_el[ln]), .o_e(l_e[32 * ln +: 32]));
    end endgenerate
    // lane outputs relayed to the sum / root / tap
    wire rl_mxv, rl_ev, rl_el, rl_skv; wire [511:0] rl_mx, rl_e; wire [31:0] rl_sk;
    ot_hdc_delay #(.W(4), .D(SRL), .RESET(1)) u_lv (.clk(clk), .rst_n(rst_in),
        .d({l_mxv[1], l_ev[1], l_el[1], l_ev[0] && l_es[0]}), .q({rl_mxv, rl_ev, rl_el, rl_skv}));
    ot_hdc_delay #(.W(512 + 512 + 32), .D(SRL)) u_ld (.clk(clk), .rst_n(rst_in), .d({l_mx, l_e, l_e[31:0]}),
        .q({rl_mx, rl_e, rl_sk}));
    wire c_ov, c_ol; wire [31:0] c_os; wire rc_ov, rc_ol; wire [31:0] rc_os;
    ot_s81_su_smc #(.LPH(16), .LA(LA)) u_smc (.clk(clk), .rst_in(rst_in), .i_v(rl_ev), .i_l(rl_el), .i_e(rl_e),
        .o_v(c_ov), .o_l(c_ol), .o_s(c_os));
    ot_hdc_delay #(.W(2), .D(SRL), .RESET(1)) u_cv (.clk(clk), .rst_n(rst_in), .d({c_ov, c_ol}), .q({rc_ov, rc_ol}));
    ot_hdc_delay #(.W(32), .D(SRL)) u_cd (.clk(clk), .rst_n(rst_in), .d(c_os), .q(rc_os));
    ot_s81_su_smr #(.LPH(16), .LA(LA)) u_smr (.clk(clk), .rst_in(rst_in), .i_cv(rc_v), .i_lt(rc_lt),
        .i_mxv(rl_mxv), .i_mx(rl_mx), .i_skv(rl_skv), .i_sk(rl_sk), .i_vv(rc_ov), .i_vl(rc_ol), .i_vs(rc_os),
        .o_mv(mv), .o_nmb(nmb), .o_dv(dv0), .o_den(den));
    assign den_v = rdv;
    // divide engines (one RoPE pair each)
    wire [7:0] d_ov; wire [255:0] d_o;
    generate for (pp = 0; pp < 8; pp = pp + 1) begin : g_p
        wire [2:0] CP = pp;
        ot_s81_su_smd #(.LPH(16), .LM(LM), .LA(LA), .STALEDEN(MUT == 5)) u_smd (
            .clk(clk), .rst_in(rst_in), .cfg_p(CP), .i_pv(b_pv[pp]), .i_pa(rd_d[64 * pp +: 64]),
            .i_dv(b_dv[pp]), .i_den(b_den[32*pp +: 32]), .i_csv(b_csv[pp]), .i_csi(b_csi[5*pp +: 5]), .i_csd(b_csd[64*pp +: 64]),
            .o_ov(d_ov[pp]), .o_o(d_o[32 * pp +: 32]), .o_f(f[pp]));
    end endgenerate
    // e / o rows to the tap
    ot_hdc_delay #(.W(1), .D(SRL), .RESET(1)) u_ov (.clk(clk), .rst_n(rst_in), .d(d_ov[0]), .q(o_v));
    ot_hdc_delay #(.W(256), .D(SRL)) u_od (.clk(clk), .rst_n(rst_in), .d(d_o), .q(o_d));
    assign e_d = rl_e;
    assign e_v = rl_ev;
endmodule
