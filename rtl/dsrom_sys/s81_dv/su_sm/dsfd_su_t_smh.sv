`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-2 (2026-10-17, S81-DV p4h): dsfd_su_t_smh, the HARDENED per-head SM cluster (one per regional service slice,
// x16 on the die, hardened once).  ot_s81_su_smh with its leaves as the closed hard tiles' tops (dsfd_su_t_sml x16,
// dsfd_su_t_smc, dsfd_su_t_smr, dsfd_su_t_smd x8; production parameters NVMAX 40, LM 5, LA 4); the SRL relay stations
// are the cluster's own flops (glue: < 5k flops, placed between the tiles).  No mutant parameter (the routed tops carry
// none): the bit-exact gate is su_gate.py run --hier --smu with OT_SU_VDEFS=-DSU_SMU_T (the slab instantiates this top).
// ---------------------------------------------------------------------------------------------------------------------
module dsfd_su_t_smh #(
    parameter integer SRL = 2,
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
    generate for (ln = 0; ln < 16; ln = ln + 1) begin : g_l
        wire sken = (ln == 0);
        dsfd_su_t_sml u_sml (
            .ck(clk), .rst(rst_in), .sk_en(sken), .i_cv(rc_v), .i_nv(rc_nv), .i_scale(rc_scale),
            .i_sink(rc_sink), .i_sv(rs_v), .i_s(rd_d[32 * ln +: 32]),
            .i_mv(rmv), .i_nmb(rnmb), .o_mxv(l_mxv[ln]), .o_mx(l_mx[32 * ln +: 32]),
            .o_ev(l_ev[ln]), .o_es(l_es[ln]), .o_el(l_el[ln]), .o_e(l_e[32 * ln +: 32]));
    end endgenerate
    // lane outputs relayed to the sum / root / tap
    wire rl_mxv, rl_ev, rl_el, rl_skv; wire [511:0] rl_mx, rl_e; wire [31:0] rl_sk;
    ot_hdc_delay #(.W(4), .D(SRL), .RESET(1)) u_lv (.clk(clk), .rst_n(rst_in),
        .d({l_mxv[1], l_ev[1], l_el[1], l_ev[0] && l_es[0]}), .q({rl_mxv, rl_ev, rl_el, rl_skv}));
    ot_hdc_delay #(.W(512 + 512 + 32), .D(SRL)) u_ld (.clk(clk), .rst_n(rst_in), .d({l_mx, l_e, l_e[31:0]}),
        .q({rl_mx, rl_e, rl_sk}));
    wire c_ov, c_ol; wire [31:0] c_os; wire rc_ov, rc_ol; wire [31:0] rc_os;
    dsfd_su_t_smc u_smc (.ck(clk), .rst(rst_in), .i_v(rl_ev), .i_l(rl_el), .i_e(rl_e),
        .o_v(c_ov), .o_l(c_ol), .o_s(c_os));
    ot_hdc_delay #(.W(2), .D(SRL), .RESET(1)) u_cv (.clk(clk), .rst_n(rst_in), .d({c_ov, c_ol}), .q({rc_ov, rc_ol}));
    ot_hdc_delay #(.W(32), .D(SRL)) u_cd (.clk(clk), .rst_n(rst_in), .d(c_os), .q(rc_os));
    dsfd_su_t_smr u_smr (.ck(clk), .rst(rst_in), .i_cv(rc_v), .i_lt(rc_lt),
        .i_mxv(rl_mxv), .i_mx(rl_mx), .i_skv(rl_skv), .i_sk(rl_sk), .i_vv(rc_ov), .i_vl(rc_ol), .i_vs(rc_os),
        .o_mv(mv), .o_nmb(nmb), .o_dv(dv0), .o_den(den));
    assign den_v = rdv;
    // divide engines (one RoPE pair each)
    wire [7:0] d_ov; wire [255:0] d_o;
    generate for (pp = 0; pp < 8; pp = pp + 1) begin : g_p
        wire [2:0] CP = pp;
        dsfd_su_t_smd u_smd (
            .ck(clk), .rst(rst_in), .cfg_p(CP), .i_pv(rp_v), .i_pa(rd_d[64 * pp +: 64]),
            .i_dv(rdv), .i_den(rden), .i_csv(rcs_v), .i_csi(rcs_i), .i_csd(rcs_d),
            .o_ov(d_ov[pp]), .o_o(d_o[32 * pp +: 32]), .o_f(f[pp]));
    end endgenerate
    // e / o rows to the tap
    ot_hdc_delay #(.W(1), .D(SRL), .RESET(1)) u_ov (.clk(clk), .rst_n(rst_in), .d(d_ov[0]), .q(o_v));
    ot_hdc_delay #(.W(256), .D(SRL)) u_od (.clk(clk), .rst_n(rst_in), .d(d_o), .q(o_d));
    assign e_d = rl_e;
    assign e_v = rl_ev;
endmodule
