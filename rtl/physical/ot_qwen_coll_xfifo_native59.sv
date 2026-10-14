`timescale 1ns/1ps
// Native TP8 local port: sequencer32 credits, engine32 credits, return rank3. Return is posted: the consumer
// must accept EVERY valid beat while its operation is active. This leaf returns a registered credit for that
// accepted beat. Source/consumer integration is separately qualified by the composition bench.
module qfd_coll_xfifo_native59 #(parameter integer IBMEM = 0) (
    input wire ck, ckd, rst_n,
    input wire i_seq_coll_v, input wire [572:0] i_seq_coll, output wire i_seq_coll_cr,
    output wire o_seq_coll_v, output wire [572:0] o_seq_coll, input wire o_seq_coll_cr,
    input wire i_coll_seq_v, input wire [575:0] i_coll_seq,
    output wire o_coll_seq_v, output wire [575:0] o_coll_seq,
    output wire fault_ck, fault_ckd
);
    initial if (IBMEM != 0) $error("native59 functional FIFO has no old32 SRAM view alias");
    reg posted_credit;
    always @(posedge ckd or negedge rst_n)
        if (!rst_n) posted_credit <= 1'b0; else posted_credit <= o_coll_seq_v;
    wire [575:0] ret;
    ot_qwen_die_coll_xfifo #(.WSQ(573),.WCQ(576),.N(8),.CR(32),.ENG_IB(32),.LCR(32),
        .CQ_AD(256),.PIPE(2),.MEMM(0),.SQ_IBMEM(IBMEM)) u_port (
        .ck(ck),.ckd(ckd),.rst_n(rst_n),
        .i_seq_coll_v(i_seq_coll_v),.i_seq_coll(i_seq_coll),.i_seq_coll_cr(i_seq_coll_cr),
        .o_seq_coll_v(o_seq_coll_v),.o_seq_coll(o_seq_coll),.o_seq_coll_cr(o_seq_coll_cr),
        .i_coll_seq_v(i_coll_seq_v),.i_coll_seq(i_coll_seq),
        .o_coll_seq_v(o_coll_seq_v),.o_coll_seq(ret),.o_coll_seq_cr(posted_credit),
        .fault_ck(fault_ck),.fault_ckd(fault_ckd));
`ifdef OT_NCOLL_NATIVE59_MUT
    assign o_coll_seq = {ret[575:38],ret[5],ret[36:6],ret[37],ret[4:0]};
`else
    assign o_coll_seq = ret;
`endif
endmodule
