`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_su_root (s81-suhc-hier-1011, 2026-10-11): the root tile of the hierarchical SU slab dsfd_sp_su_h, placed at
// the c_cmd / VM pin edge: the dsfd_sp_ctrl engine adapter (ot_s81_engine_adapter QD 8, controller-clock CDC), the
// slab reset relay, the VM response pin flops, the up-spine pin flops and the control tile ot_s81_su_hctl (job state,
// VM read issue, VM write slots).  Every input lands in a flop (adapter CDC FIFOs, inp, rs, up spine); every output
// leaves a flop (hctl's rq / wq / dn registers, the reset relay).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_su_root #(
    parameter integer QN_N = 256, KV_N = 512, QB_NB = 32, SW_W = 1024, SM_H = 16, SM_LPH = 16,
    parameter integer S_RD = 16, S_WR = 16, NSW = 8, NQB = 4, MUT = 0, AMUT = 0
) (
    input  wire                cck, crs,
    input  wire                sk, srs,
    input  wire                c_cmd_v,
    input  wire [83:0]         c_cmd_d,
    output wire                c_done_v,
    output wire [7:0]          c_done_tag,
    input  wire                inp,
    output wire [S_RD-1:0]     rq_v,
    output wire [S_RD*14-1:0]  rq_row,
    input  wire [S_RD-1:0]     rs_v,
    input  wire [S_RD*512-1:0] rs_d,
    output wire [S_WR-1:0]     wq_v,
    output wire [S_WR*14-1:0]  wq_row,
    output wire [S_WR*16-1:0]  wq_mask,
    output wire [S_WR*512-1:0] wq_d,
    output wire                flt,
    output wire                online,
    output wire [3:0]          fcode,
    output wire                rst_o,                    // slab reset to the reset spine
    output wire                dn_st,
    output wire [3:0]          dn_kind,
    output wire [1:0]          dn_gsel,
    output wire                dn_fp4,
    output wire [7:0]          dn_jid,
    output wire [S_RD-1:0]     dn_v,
    output wire                dn_ph,
    output wire [15:0]         dn_idx,
    output wire [S_RD*512-1:0] dn_d,
    input  wire [S_WR-1:0]     up_v,
    input  wire [S_WR*14-1:0]  up_a,
    input  wire [S_WR*16-1:0]  up_m,
    input  wire [S_WR*512-1:0] up_d,
    input  wire                up_fu, up_fo, up_alive, up_den, up_rdy,
    input  wire [7:0]          up_rjid
);
    wire e_v, e_r, d_v, a_flt, c_flt;
    wire [83:0] e_d;
    wire [7:0]  d_t;
    reg inp_q;
    reg s0, s1;                                        // slab reset relay (pin)
    always @(posedge sk or negedge srs) if (!srs) begin s0 <= 1'b0; s1 <= 1'b0; end else begin s0 <= 1'b1; s1 <= s0; end
    assign rst_o = s1;
    always @(posedge sk or negedge srs) if (!srs) inp_q <= 1'b0; else inp_q <= inp;
    ot_s81_engine_adapter #(.QD(8), .MUT(AMUT)) u_ad (
        .c_clk(cck), .c_rst_n(crs), .c_cmd_v(c_cmd_v), .c_cmd_d(c_cmd_d), .c_done_v(c_done_v), .c_done_tag(c_done_tag),
        .fault(a_flt), .online(online),
        .e_clk(sk), .e_rst_n(srs), .e_cmd_v(e_v), .e_cmd_d(e_d), .e_cmd_ready(e_r), .e_inputs_present(inp_q),
        .e_done_v(d_v), .e_done_tag(d_t));
    // pin flops: VM responses, up spine
    reg  [S_RD-1:0]     rs_v_q;
    reg  [S_RD*512-1:0] rs_d_q;
    reg  [S_WR*14-1:0]  ua_q;
    reg  [S_WR*16-1:0]  um_q;
    reg  [S_WR*512-1:0] ud_q;
    reg  [S_WR-1:0]     uv_q;
    reg                 ufu_q, ufo_q, ual_q, ude_q, urd_q;
    reg  [7:0]          urj_q;
    always @(posedge sk) begin rs_d_q <= rs_d; ua_q <= up_a; um_q <= up_m; ud_q <= up_d; end
    always @(posedge sk or negedge s1)
        if (!s1) begin rs_v_q <= 0; uv_q <= 0; ufu_q <= 0; ufo_q <= 0; ual_q <= 0; ude_q <= 0; urd_q <= 0; urj_q <= 0; end
        else begin
            rs_v_q <= rs_v; uv_q <= up_v; ufu_q <= up_fu; ufo_q <= up_fo; ual_q <= up_alive; ude_q <= up_den;
            urd_q <= up_rdy; urj_q <= up_rjid;
        end
    wire [31:0] jobs;
    wire        bsy;
    ot_s81_su_hctl #(.QN_N(QN_N), .KV_N(KV_N), .QB_NB(QB_NB), .SW_W(SW_W), .SM_H(SM_H), .SM_LPH(SM_LPH),
                     .S_RD(S_RD), .S_WR(S_WR), .NSW(NSW), .NQB(NQB), .MUT(MUT)) u_core (
        .clk(sk), .rst_n(s1), .e_cmd_v(e_v), .e_cmd_d(e_d), .e_cmd_ready(e_r), .e_done_v(d_v), .e_done_tag(d_t),
        .rq_v(rq_v), .rq_row(rq_row), .rs_v(rs_v_q), .rs_d(rs_d_q),
        .wq_v(wq_v), .wq_row(wq_row), .wq_mask(wq_mask), .wq_d(wq_d), .busy(bsy), .fault(c_flt), .fault_code(fcode),
        .st_jobs(jobs),
        .dn_st(dn_st), .dn_kind(dn_kind), .dn_gsel(dn_gsel), .dn_fp4(dn_fp4), .dn_jid(dn_jid), .dn_v(dn_v),
        .dn_ph(dn_ph), .dn_idx(dn_idx), .dn_d(dn_d),
        .up_v(uv_q), .up_a(ua_q), .up_m(um_q), .up_d(ud_q), .up_fu(ufu_q), .up_fo(ufo_q), .up_alive(ual_q),
        .up_den(ude_q), .up_rdy(urd_q), .up_rjid(urj_q));
    assign flt = a_flt | c_flt;
endmodule
