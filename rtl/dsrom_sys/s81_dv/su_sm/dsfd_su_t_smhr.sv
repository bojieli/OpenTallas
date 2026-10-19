`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-SMH2 (2026-10-17): dsfd_su_t_smhr, the ROOT regional cluster of one softmax head (x1 per head, hardened once):
// the row sum dsfd_su_t_smc and the max / den root dsfd_su_t_smr with their SRL link between them, its own clock pin
// and registered reset relay.  Inputs from the 4 lane quads dsfd_su_t_smhq arrive registered there (station 1); the
// remaining SRL - 1 stations are here (flop-first).  The max / den broadcast leaves registered (station 1; the quads
// hold the rest), and den_v to the tap leaves after SRL stations, as in ot_s81_su_smh.
// ---------------------------------------------------------------------------------------------------------------------
module dsfd_su_t_smhr #(
    parameter integer SRL = 2
) (
    input  wire          clk,
    input  wire          rst_in,                       // active low; relayed through this cluster's own synchroniser
    // from the tap (registered there)
    input  wire          c_v,
    input  wire [2:0]    c_lt,
    // from the quads (registered there; valids from quad 0)
    input  wire          q_mxv,
    input  wire          q_ev,
    input  wire          q_el,
    input  wire          q_skv,
    input  wire [511:0]  q_mx,
    input  wire [511:0]  q_e,
    // to the quads (registered here)
    output wire          m_v,
    output wire [31:0]   m_nmb,
    output wire          dn_v,
    output wire [31:0]   dn,
    // to the tap (registered here)
    output wire          den_v
);
    reg rr0, rr1;
    always @(posedge clk or negedge rst_in)
        if (!rst_in) begin rr0 <= 1'b0; rr1 <= 1'b0; end else begin rr0 <= 1'b1; rr1 <= rr0; end
    wire rst_l = rr1;

    wire rc_v; wire [2:0] rc_lt;
    ot_hdc_delay #(.W(1), .D(SRL), .RESET(1)) u_tv (.clk(clk), .rst_n(rst_l), .d(c_v), .q(rc_v));
    ot_hdc_delay #(.W(3), .D(SRL)) u_td (.clk(clk), .rst_n(rst_l), .d(c_lt), .q(rc_lt));
    // quads -> here: the remaining SRL - 1 stations
    wire rl_mxv, rl_ev, rl_el, rl_skv; wire [511:0] rl_mx, rl_e;
    ot_hdc_delay #(.W(4), .D(SRL - 1), .RESET(1)) u_lv (.clk(clk), .rst_n(rst_l), .d({q_mxv, q_ev, q_el, q_skv}),
        .q({rl_mxv, rl_ev, rl_el, rl_skv}));
    ot_hdc_delay #(.W(1024), .D(SRL - 1)) u_ld (.clk(clk), .rst_n(rst_l), .d({q_mx, q_e}), .q({rl_mx, rl_e}));
    wire [31:0] rl_sk = rl_e[31:0];                    // lane 0's e (the sink column)

    wire c_ov, c_ol; wire [31:0] c_os; wire rc_ov, rc_ol; wire [31:0] rc_os;
    dsfd_su_t_smc u_smc (.ck(clk), .rst(rst_l), .i_v(rl_ev), .i_l(rl_el), .i_e(rl_e), .o_v(c_ov), .o_l(c_ol), .o_s(c_os));
    ot_hdc_delay #(.W(2), .D(SRL), .RESET(1)) u_cv (.clk(clk), .rst_n(rst_l), .d({c_ov, c_ol}), .q({rc_ov, rc_ol}));
    ot_hdc_delay #(.W(32), .D(SRL)) u_cd (.clk(clk), .rst_n(rst_l), .d(c_os), .q(rc_os));
    wire mv, dv0; wire [31:0] nmb, den;
    dsfd_su_t_smr u_smr (.ck(clk), .rst(rst_l), .i_cv(rc_v), .i_lt(rc_lt),
        .i_mxv(rl_mxv), .i_mx(rl_mx), .i_skv(rl_skv), .i_sk(rl_sk), .i_vv(rc_ov), .i_vl(rc_ol), .i_vs(rc_os),
        .o_mv(mv), .o_nmb(nmb), .o_dv(dv0), .o_den(den));
    // max / den broadcast: station 1 (flop-last)
    ot_hdc_delay #(.W(2), .D(1), .RESET(1)) u_rv (.clk(clk), .rst_n(rst_l), .d({mv, dv0}), .q({m_v, dn_v}));
    ot_hdc_delay #(.W(64), .D(1)) u_rd (.clk(clk), .rst_n(rst_l), .d({nmb, den}), .q({m_nmb, dn}));
    // den reached the divide engines: SRL stations after dv0
    ot_hdc_delay #(.W(1), .D(SRL - 1), .RESET(1)) u_dv (.clk(clk), .rst_n(rst_l), .d(dn_v), .q(den_v));
endmodule
