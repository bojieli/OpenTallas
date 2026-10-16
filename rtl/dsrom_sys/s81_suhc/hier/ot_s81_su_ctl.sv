`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// The slab-pin side of the hierarchical SU slab dsfd_sp_su_h (s81-suhc-hier-1011, 2026-10-11), split so no tile
// exceeds ~600 um:
//   ot_s81_su_pin  a column-local PIN OWNER (NPO of them stacked N-S along the slab's VM pin edge): the VM read slots
//                  [KR p, KR p + KR) and write slots [KW p, KW p + KW) of its span -- pin flops on every slab input,
//                  registers on every slab output; VM rows go from its pin flops straight onto the down spine (its
//                  slice), the up spine's write rows (its slice) straight to the VM write pins; to the control tile
//                  only narrow copies (response valids + the descriptor fields, issued write valids), from it the
//                  read requests of its slots.
//   ot_s81_su_ctl  the small COMBINE tile: the dsfd_sp_ctrl engine adapter (ot_s81_engine_adapter QD 8, the c_cmd /
//                  c_done CDC), the slab reset relay and ot_s81_su_hctl (job state, read issue, completion); its
//                  job announce enters the down spine beside the pin owners' rows.
// Every seam is registered on both sides (the slab adds a relay station on each ctl <-> pin owner link).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_su_pin #(
    parameter integer KR = 4, KW = 4
) (
    input  wire               clk,
    input  wire               rst_in,
    output reg  [KR-1:0]      rq_v,
    output reg  [KR*14-1:0]   rq_row,
    input  wire [KR-1:0]      rs_v,
    input  wire [KR*512-1:0]  rs_d,
    (* keep = "true" *) output reg  [KW-1:0]      wq_v,
    output reg  [KW*14-1:0]   wq_row,
    output reg  [KW*16-1:0]   wq_mask,
    output reg  [KW*512-1:0]  wq_d,
    (* keep = "true" *) output reg  [KR-1:0]      dn_v,
    (* keep = "true" *) output reg  [KR*512-1:0]  dn_d,
    input  wire [KW-1:0]      up_v,
    input  wire [KW*14-1:0]   up_a,
    input  wire [KW*16-1:0]   up_m,
    input  wire [KW*512-1:0]  up_d,
    input  wire [KR-1:0]      c_rq_v,
    input  wire [KR*14-1:0]   c_rq_row,
    (* keep = "true" *) output reg  [KR-1:0]      c_rv,
    (* keep = "true" *) output reg  [KR*30-1:0]   c_rf,
    (* keep = "true" *) output reg  [KW-1:0]      c_uv
);
    // ONE FLOP A PIN (el1013-s81su, pin rt2 TT -10.55): dn_v / c_rv, wq_v / c_uv and c_rf / dn_d[..] register the same value for
    // ports on different faces; synthesis merged each pair into one flop, whose second port was then 213 ps of wire +
    // the output hold stage away.  The twins are (* keep *) registers (physical/common_flow/ot_keep_regs.tcl keeps the
    // flop cells), so every output port has its own flop at its own pin.  Function unchanged.
    reg rr0, rr1;
    always @(posedge clk or negedge rst_in) if (!rst_in) begin rr0 <= 1'b0; rr1 <= 1'b0; end else begin rr0 <= 1'b1; rr1 <= rr0; end
    wire rst_n = rr1;
    reg  [KR-1:0]     rv_q, cq_v;
    reg  [KR*512-1:0] rd_q;
    reg  [KR*14-1:0]  cq_r;
    reg  [KW-1:0]     uv_q;
    reg  [KW*14-1:0]  ua_q;
    reg  [KW*16-1:0]  um_q;
    reg  [KW*512-1:0] ud_q;
    integer s;
    always @(posedge clk) begin                       // datapath: no reset
        rd_q <= rs_d; cq_r <= c_rq_row; ua_q <= up_a; um_q <= up_m; ud_q <= up_d;
        dn_d <= rd_q; rq_row <= cq_r; wq_row <= ua_q; wq_mask <= um_q; wq_d <= ud_q;
        for (s = 0; s < KR; s = s + 1) c_rf[30 * s +: 30] <= {rd_q[512 * s + 64 +: 16], rd_q[512 * s + 32 +: 14]};
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin rv_q <= 0; cq_v <= 0; uv_q <= 0; dn_v <= 0; rq_v <= 0; wq_v <= 0; c_rv <= 0; c_uv <= 0; end
        else begin
            rv_q <= rs_v; cq_v <= c_rq_v; uv_q <= up_v;
            dn_v <= rv_q; c_rv <= rv_q; rq_v <= cq_v; wq_v <= uv_q; c_uv <= uv_q;
        end
    end
endmodule

module ot_s81_su_ctl #(
    parameter integer QN_N = 256, KV_N = 512, QB_NB = 32, SW_W = 1024, SM_H = 16, SM_LPH = 16,
    parameter integer S_RD = 16, S_WR = 16, NSW = 8, NQB = 4, NQN = 2, NKV = 2, MUT = 0, AMUT = 0, QRW = 2
) (
    input  wire                cck, crs,
    input  wire                sk, srs,
    input  wire                c_cmd_v,
    input  wire [83:0]         c_cmd_d,
    output wire                c_done_v,
    output wire [7:0]          c_done_tag,
    input  wire                inp,
    output wire                flt,
    output wire                online,
    output wire [3:0]          fcode,
    output wire                rst_o,                    // slab reset: pin owners and the reset spine
    // pin owner seams
    output wire [S_RD-1:0]     p_rq_v,
    output wire [S_RD*14-1:0]  p_rq_row,
    input  wire [S_RD-1:0]     p_rv,
    input  wire [S_RD*30-1:0]  p_rf,
    input  wire [S_WR-1:0]     p_uv,
    // down spine: the job announce
    output wire                dn_st,
    output wire [3:0]          dn_kind,
    output wire [1:0]          dn_gsel,
    output wire                dn_fp4,
    output wire [7:0]          dn_jid,
    // up spine: the tiles' status
    input  wire                up_fu, up_fo, up_alive, up_den, up_rdy,
    input  wire [7:0]          up_rjid,
    input wire up_cp_done
);
    wire e_v, e_r, d_v, a_flt, c_flt;
    wire [83:0] e_d;
    wire [7:0]  d_t;
    reg inp_q;
    reg s0, s1;
    always @(posedge sk or negedge srs) if (!srs) begin s0 <= 1'b0; s1 <= 1'b0; end else begin s0 <= 1'b1; s1 <= s0; end
    assign rst_o = s1;
    always @(posedge sk or negedge srs) if (!srs) inp_q <= 1'b0; else inp_q <= inp;
    // controller-side pin flops: the adapter's admit logic (256:1 pending lookup, FIFO write enables) starts from a
    // register, never from the slab pins
    reg        cmd_v_q;
    reg [83:0] cmd_d_q;
    always @(posedge cck or negedge crs) if (!crs) cmd_v_q <= 1'b0; else cmd_v_q <= c_cmd_v;
    always @(posedge cck) cmd_d_q <= c_cmd_d;
    ot_s81_engine_adapter #(.QD(8), .MUT(AMUT)) u_ad (
        .c_clk(cck), .c_rst_n(crs), .c_cmd_v(cmd_v_q), .c_cmd_d(cmd_d_q), .c_done_v(c_done_v), .c_done_tag(c_done_tag),
        .fault(a_flt), .online(online),
        .e_clk(sk), .e_rst_n(srs), .e_cmd_v(e_v), .e_cmd_d(e_d), .e_cmd_ready(e_r), .e_inputs_present(inp_q),
        .e_done_v(d_v), .e_done_tag(d_t));
    // pin flops: pin owner seams, status
    reg  [S_RD-1:0]    rv_q;
    reg  [S_RD*30-1:0] rf_q;
    reg  [S_WR-1:0]    uv_q;
    reg                ufu_q, ufo_q, ual_q, ude_q, urd_q, ucp_q;
    reg  [7:0]         urj_q;
    always @(posedge sk) rf_q <= p_rf;
    always @(posedge sk or negedge s1)
        if (!s1) begin rv_q <= 0; uv_q <= 0; ufu_q <= 0; ufo_q <= 0; ual_q <= 0; ude_q <= 0; urd_q <= 0; urj_q <= 0;ucp_q<=0; end
        else begin
            rv_q <= p_rv; uv_q <= p_uv; ufu_q <= up_fu; ufo_q <= up_fo; ual_q <= up_alive; ude_q <= up_den;
            urd_q <= up_rdy; urj_q <= up_rjid;
            ucp_q<=up_cp_done;
        end
    wire [31:0] jobs;
    wire        bsy;
    ot_s81_su_hctl #(.QN_N(QN_N), .KV_N(KV_N), .QB_NB(QB_NB), .SW_W(SW_W), .SM_H(SM_H), .SM_LPH(SM_LPH),
                     .S_RD(S_RD), .S_WR(S_WR), .NSW(NSW), .NQB(NQB), .NQN(NQN), .NKV(NKV), .MUT(MUT), .QRW(QRW)) u_core (
        .clk(sk), .rst_n(s1), .e_cmd_v(e_v), .e_cmd_d(e_d), .e_cmd_ready(e_r), .e_done_v(d_v), .e_done_tag(d_t),
        .rq_v(p_rq_v), .rq_row(p_rq_row), .rs_v(rv_q), .rs_f(rf_q), .busy(bsy), .fault(c_flt), .fault_code(fcode),
        .st_jobs(jobs),
        .dn_st(dn_st), .dn_kind(dn_kind), .dn_gsel(dn_gsel), .dn_fp4(dn_fp4), .dn_jid(dn_jid),
        .up_v(uv_q), .up_fu(ufu_q), .up_fo(ufo_q), .up_alive(ual_q), .up_den(ude_q), .up_rdy(urd_q), .up_rjid(urj_q),.up_cp_done(ucp_q));
    assign flt = a_flt | c_flt;
endmodule
