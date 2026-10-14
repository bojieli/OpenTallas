`timescale 1ns/1ps
// Native TP8 local port: sequencer32 credits, engine32 credits, return rank3. Return is posted: the consumer
// must accept EVERY valid beat while its operation is active. This leaf returns a registered credit for that
// accepted beat. Source/consumer integration is separately qualified by the composition bench.
module qfd_coll_xfifo_native #(parameter integer IBMEM = 1, WR_FREE = 1) (
    input wire ck, ckd, rst_n,
    input wire i_seq_coll_v, input wire [545:0] i_seq_coll, output wire i_seq_coll_cr,
    output wire o_seq_coll_v, output wire [545:0] o_seq_coll, input wire o_seq_coll_cr,
    input wire i_coll_seq_v, input wire [516:0] i_coll_seq,
    output wire o_coll_seq_v, output wire [516:0] o_coll_seq,
    output wire fault_ck, fault_ckd
);
    reg posted_credit;
    always @(posedge ckd or negedge rst_n)
        if (!rst_n) posted_credit <= 1'b0; else posted_credit <= o_coll_seq_v;
    wire [516:0] ret;
    ot_qwen_die_coll_xfifo #(.WSQ(546),.WCQ(517),.N(8),.CR(32),.ENG_IB(32),.LCR(32),
        .CQ_AD(256),.PIPE(2),.MEMM(1),.SQ_IBMEM(IBMEM),.WR_FREE(WR_FREE)) u_port (
        .ck(ck),.ckd(ckd),.rst_n(rst_n),
        .i_seq_coll_v(i_seq_coll_v),.i_seq_coll(i_seq_coll),.i_seq_coll_cr(i_seq_coll_cr),
        .o_seq_coll_v(o_seq_coll_v),.o_seq_coll(o_seq_coll),.o_seq_coll_cr(o_seq_coll_cr),
        .i_coll_seq_v(i_coll_seq_v),.i_coll_seq(i_coll_seq),
        .o_coll_seq_v(o_coll_seq_v),.o_coll_seq(ret),.o_coll_seq_cr(posted_credit),
        .fault_ck(fault_ck),.fault_ckd(fault_ckd));
`ifdef OT_NCOLL_NATIVE_MUT
    assign o_coll_seq = {ret[516:38],ret[5],ret[36:6],ret[37],ret[4:0]};
`else
    assign o_coll_seq = ret;
`endif
endmodule
