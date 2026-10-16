`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// dsfd_host_s (s81-svceng-1011): the S81 host die master with per-stack host-write ports = dsfd_host_native (ENABLE 1,
// the closed rev-c pipeline: FPIPE 2, ENG_TRIM 1, APIPE 2) + dsfd_host_sd.  The read return i_rv / i_rd of the host
// engine is ABSENT on the DS dies (RMW_EN 0: an RMW descriptor fails closed in the engine; dsfd_host_sd faults an
// o_we = 0 word), so it is driven 0 here: not a functional port.
// ---------------------------------------------------------------------------------------------------------------
module dsfd_host_s #(parameter integer NS = 2, KVS = 1, ENG = 1, MUT = 0) (
    input  wire              rst_n,
    input  wire              clk_h,
    input  wire              h_v,
    input  wire [1:0]        h_cls,
    input  wire [511:0]      h_d,
    output wire [4:0]        h_crn,
    output wire              t_v,
    output wire [63:0]       t_d,
    input  wire              t_cr,
    input  wire              clk_i,
    input  wire              ck,
    output wire [292*NS-1:0] hw,
    input  wire [9*NS-1:0]   hc,
    output wire              fault
);
    wire ov, owe, ocr, hf, sf; wire [31:0] oa; wire [255:0] od; wire [7:0] ack;
    dsfd_host_native #(.ENABLE(1), .FPIPE(2), .ENG_TRIM(1), .APIPE(2)) u_h (.rst_n(rst_n), .clk_h(clk_h), .h_v(h_v), .h_cls(h_cls),
        .h_d(h_d), .h_crn(h_crn), .t_v(t_v), .t_d(t_d), .t_cr(t_cr), .clk_i(clk_i), .ck(ck), .o_v(ov), .o_we(owe), .o_addr(oa),
        .o_d(od), .o_cr(ocr), .i_rv(1'b0), .i_rd(256'd0), .host_ack_n(ack), .fault(hf));
    dsfd_host_sd #(.NS(NS), .KVS(KVS), .ENG(ENG), .MUT(MUT)) u_sd (.ck(ck), .rst_n(rst_n), .o_v(ov), .o_we(owe), .o_addr(oa),
        .o_d(od), .o_cr(ocr), .hw(hw), .hc(hc), .host_ack_n(ack), .fault(sf));
    assign fault = hf | sf;
endmodule
