// DIAGNOSTIC ONLY: runtime credits are prohibited in the static production schedule.
`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// diag_dsfd_sp_su (stream s81-suhc-1011, 2026-10-11): die master of the S81 SU slab.  The dsfd_sp_ctrl engine adapter
// (ot_s81_engine_adapter QD 8, engine port su = 1) sits at the slab boundary (physical/s81_ctrl/ADAPTER_CONTRACT_1011
// .json): the die nets c_cmd_v / c_cmd_d (85 b) and c_done_v / c_done_tag (9 b) are the controller-clock pulses;
// the engine (diag_ot_s81_su_core) runs on the slab clock sk (stream 1.2 GHz).  `inp` is the die dependency net (s81-ctl):
// the operands of the head descriptor are present (VM rows written by their producer).  Every die input lands in a pin flop and every output leaves a flop (VM, status);
// the command / done pulses are flopped inside the adapter's CDC FIFOs.
// ---------------------------------------------------------------------------------------------------------------------
module diag_dsfd_sp_su #(
    parameter integer CREDIT_MODE = 0, PACING_MUT = 0,
    parameter integer QN_N = 256, KV_N = 512, QB_NB = 32, SW_W = 1024, SM_H = 16, SM_LPH = 16, SM_NVMAX = 40,
    parameter integer S_RD = 16, S_WR = 16, LM = 5, LA = 4, OQ = 1024, MUT = 0, AMUT = 0, XMUT = 0, RAL = 16
) (
    input  wire                cck, crs,                 // controller clock / reset (dsfd_sp_ctrl domain)
    input  wire                sk, srs,                  // slab clock / reset
    input  wire                c_cmd_v,
    input  wire [83:0]         c_cmd_d,
    output wire                c_done_v,
    output wire [7:0]          c_done_tag,
    input  wire                inp,
    output wire [S_RD-1:0]     rq_v,
    output wire [S_RD*14-1:0]  rq_row,
    input wire [S_RD-1:0] rq_credit,
    input wire [S_WR-1:0] wq_credit,
    input  wire [S_RD-1:0]     rs_v,
    input  wire [S_RD*512-1:0] rs_d,
    output wire [S_WR-1:0]     wq_v,
    output wire [S_WR*14-1:0]  wq_row,
    output wire [S_WR*16-1:0]  wq_mask,
    output wire [S_WR*512-1:0] wq_d,
    output wire                flt,
    output wire                online,
    output wire [3:0]          fcode
);
    wire e_v, e_r, d_v, a_flt, c_flt;
    wire [83:0] e_d;
    wire [7:0]  d_t;
    reg inp_q;
    always @(posedge sk or negedge srs) if (!srs) inp_q <= 1'b0; else inp_q <= inp;
    ot_s81_engine_adapter #(.QD(8), .MUT(AMUT)) u_ad (
        .c_clk(cck), .c_rst_n(crs), .c_cmd_v(c_cmd_v), .c_cmd_d(c_cmd_d), .c_done_v(c_done_v), .c_done_tag(c_done_tag),
        .fault(a_flt), .online(online),
        .e_clk(sk), .e_rst_n(srs), .e_cmd_v(e_v), .e_cmd_d(e_d), .e_cmd_ready(e_r), .e_inputs_present(inp_q),
        .e_done_v(d_v), .e_done_tag(d_t));
    wire [31:0] jobs;
    wire        bsy;
    // pin flops: VM responses (fixed latency + 1, the core counts responses)
    reg  [S_RD-1:0]     rs_v_q;
    reg  [S_RD*512-1:0] rs_d_q;
    always @(posedge sk) rs_d_q <= rs_d;
    always @(posedge sk or negedge srs) if (!srs) rs_v_q <= 0; else rs_v_q <= rs_v;
    diag_ot_s81_su_core #(.CREDIT_MODE(CREDIT_MODE), .PACING_MUT(PACING_MUT), .QN_N(QN_N), .KV_N(KV_N), .QB_NB(QB_NB), .SW_W(SW_W), .SM_H(SM_H), .SM_LPH(SM_LPH),
                     .SM_NVMAX(SM_NVMAX), .S_RD(S_RD), .S_WR(S_WR), .LM(LM), .LA(LA), .OQ(OQ), .MUT(MUT), .XMUT(XMUT), .RAL(RAL)) u_core (
        .clk(sk), .rst_n(srs), .e_cmd_v(e_v), .e_cmd_d(e_d), .e_cmd_ready(e_r), .e_done_v(d_v), .e_done_tag(d_t),
        .rq_credit(rq_credit), .wq_credit(wq_credit), .rq_v(rq_v), .rq_row(rq_row), .rs_v(rs_v_q), .rs_d(rs_d_q),
        .wq_v(wq_v), .wq_row(wq_row), .wq_mask(wq_mask), .wq_d(wq_d), .busy(bsy), .fault(c_flt), .fault_code(fcode),
        .st_jobs(jobs));
    assign flt = a_flt | c_flt;
endmodule
