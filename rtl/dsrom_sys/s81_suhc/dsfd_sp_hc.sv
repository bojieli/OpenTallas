`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// dsfd_sp_hc (stream s81-suhc-1011, 2026-10-11): die master of the S81 HC slab.  The dsfd_sp_ctrl engine adapter
// (ot_s81_engine_adapter QD 8, engine port hc = 2) sits at the slab boundary (physical/s81_ctrl/ADAPTER_CONTRACT_1011
// .json): the die nets c_cmd_v / c_cmd_d (85 b) and c_done_v / c_done_tag (9 b) are the controller-clock pulses;
// the engine (ot_s81_hc_core) runs on the slab clock sk.  `inp` is the die dependency net (s81-ctl): the operands of
// the head descriptor are present (VM rows written by their producer); the y operand of a POST is flow-controlled on
// its own bus (y_v / y_rdy).  Every die input lands in a pin flop and every output leaves a flop (VM, y, status);
// the command / done pulses are flopped inside the adapter's CDC FIFOs.
// ---------------------------------------------------------------------------------------------------------------------
module dsfd_sp_hc #(
    parameter integer NG = 256, D = 5120, S_RD = 2, S_WR = 8, LVM = 10, WIN = 2, WOUT = 2, ML = 5, AL = 4,
    parameter integer OQ = 512, MUT = 0, AMUT = 0,
    parameter integer KT = 0,                            // 0: flat engine ot_s81_hc_core; > 0: hierarchical slab
    parameter integer RS = 1                             //    ot_s81_hc_hier (KT row-group tiles, RS relays a hop)
) (
    input  wire                cck, crs,                 // controller clock / reset (dsfd_sp_ctrl domain)
    input  wire                sk, srs,                  // slab clock / reset
    input  wire                c_cmd_v,
    input  wire [83:0]         c_cmd_d,
    output wire                c_done_v,
    output wire [7:0]          c_done_tag,
    input  wire                inp,
    input  wire                y_v,
    output wire                y_rdy,
    input  wire [NG*32-1:0]    y_d,
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
    // pin flops: VM responses (fixed latency + 1, the core counts responses), y through a registered-ready skid
    reg  [S_RD-1:0]     rs_v_q;
    reg  [S_RD*512-1:0] rs_d_q;
    always @(posedge sk) rs_d_q <= rs_d;
    always @(posedge sk or negedge srs) if (!srs) rs_v_q <= 0; else rs_v_q <= rs_v;
    wire yq_v, yq_r, y_ov, y_un;
    wire [NG*32-1:0] yq_d;
    ot_skid_buffer #(.WIDTH(NG*32), .DEPTH(2)) u_ysk (.clk(sk), .rst_n(srs), .in_valid(y_v), .in_ready(y_rdy),
        .in_data(y_d), .out_valid(yq_v), .out_ready(yq_r), .out_data(yq_d), .overflow(y_ov), .underflow(y_un));
    generate if (KT > 0) begin : g_hier
    ot_s81_hc_hier #(.NG(NG), .D(D), .S_RD(S_RD), .S_WR(S_WR), .LVM(LVM), .WIN(WIN), .WOUT(WOUT), .ML(ML), .AL(AL),
                     .OQ(OQ), .MUT(MUT), .KT(KT), .RS(RS)) u_core (
        .clk(sk), .rst_n(srs), .e_cmd_v(e_v), .e_cmd_d(e_d), .e_cmd_ready(e_r), .e_done_v(d_v), .e_done_tag(d_t),
        .y_v(yq_v), .y_rdy(yq_r), .y_d(yq_d), .rq_v(rq_v), .rq_row(rq_row), .rs_v(rs_v_q), .rs_d(rs_d_q),
        .wq_v(wq_v), .wq_row(wq_row), .wq_mask(wq_mask), .wq_d(wq_d), .busy(bsy), .fault(c_flt), .fault_code(fcode),
        .st_jobs(jobs));
    end else begin : g_flat
    ot_s81_hc_core #(.NG(NG), .D(D), .S_RD(S_RD), .S_WR(S_WR), .LVM(LVM), .WIN(WIN), .WOUT(WOUT), .ML(ML), .AL(AL),
                     .OQ(OQ), .MUT(MUT)) u_core (
        .clk(sk), .rst_n(srs), .e_cmd_v(e_v), .e_cmd_d(e_d), .e_cmd_ready(e_r), .e_done_v(d_v), .e_done_tag(d_t),
        .y_v(yq_v), .y_rdy(yq_r), .y_d(yq_d), .rq_v(rq_v), .rq_row(rq_row), .rs_v(rs_v_q), .rs_d(rs_d_q),
        .wq_v(wq_v), .wq_row(wq_row), .wq_mask(wq_mask), .wq_d(wq_d), .busy(bsy), .fault(c_flt), .fault_code(fcode),
        .st_jobs(jobs));
    end endgenerate
    assign flt = a_flt | c_flt | y_ov | y_un;
endmodule
