`timescale 1ns/1ps
// Physical envelope for one wo_a activation cluster.
// One 64-lane converter preloads one 16-macro 1R1W xbank. The xbank's
// 2048-bit tile beat is registered once before reaching 41 distinct adapter
// capture banks, matching the SHARED_XBANK/RL3 latency contract. Consumer
// banks are a conservative port/load proxy, not the full MAC tiles. Their
// enables are independent to prevent synthesis from collapsing physically
// separate capture points; the admitted wo_a schedule asserts all enables.
module ot_v41_me_cluster41_phy #(
    parameter integer CONSUMERS = 41
) (
    input  wire clk,
    input  wire rst_n,
    input  wire pre_v,
    input  wire [1:0] pre_p,
    input  wire [12:0] pre_e,
    input  wire [2047:0] pre_fp32,
    input  wire [7:0] rq_v,
    input  wire [8*14-1:0] rq_q,
    input  wire [8*4-1:0] rq_plg,
    input  wire [1:0] rd_rot,
    input  wire [CONSUMERS-1:0] consumer_take,
    output wire pre_fault,
    output wire pre_saturated,
    output reg  [CONSUMERS-1:0] consumer_valid,
    output wire [CONSUMERS*2048-1:0] consumer_operand
);
    wire cv_v;
    wire [1:0] cv_p;
    wire [12:0] cv_e;
    wire [1023:0] cv_bf16;
    ot_hdc_v41x_fp32_bf16_preload64 #(.EW(13),.PW(2)) u_conv (
        .clk(clk),.rst_n(rst_n),.in_v(pre_v),.in_p(pre_p),.in_e(pre_e),
        .in_d(pre_fp32),.out_v(cv_v),.out_p(cv_p),.out_e(cv_e),
        .out_d(cv_bf16),.out_fault(pre_fault),.out_saturated(pre_saturated)
    );

    wire [2047:0] xbank_q;
    ot_hdc_v41x_me_xbank_macro #(.MG(8),.MP(2),.G(4),.KMAX(5120),.NBW(14),.EW(13)) u_xbank (
        .clk(clk),.wr_v(1'b0),.wr_p(2'b0),.wr_e(13'b0),.wr_d(64'b0),
        .pre_v(cv_v && !pre_fault),.pre_p(cv_p),.pre_e(cv_e),.pre_d(cv_bf16),
        .rd_rot(rd_rot),.rq_v(rq_v),.rq_q(rq_q),.rq_plg(rq_plg),.rd_x(xbank_q)
    );

    reg [2047:0] multicast_q;
    reg read_v_q;
    reg multicast_v_q;
    always @(posedge clk) begin
        multicast_q <= xbank_q;
        if (!rst_n) begin
            read_v_q <= 1'b0;
            multicast_v_q <= 1'b0;
        end else begin
            read_v_q <= |rq_v;
            multicast_v_q <= read_v_q;
        end
    end

    genvar c;
    generate for (c=0;c<CONSUMERS;c=c+1) begin : g_consumer
        // This capture flop bank represents each adapter's existing local
        // xr register. No extra operand stage beyond RL3 is credited.
        reg [2047:0] operand_q;
        always @(posedge clk) begin
            if (consumer_take[c]) operand_q <= multicast_q;
            if (!rst_n) consumer_valid[c] <= 1'b0;
            else consumer_valid[c] <= multicast_v_q && consumer_take[c];
        end
        assign consumer_operand[c*2048 +: 2048] = operand_q;
    end endgenerate
endmodule
