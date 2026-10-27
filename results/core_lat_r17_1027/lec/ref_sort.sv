`timescale 1ns/1ps
// S81-CORE-LAT-R17 retimed REFERENCE: the pre-R17 l1c order sort (dsdv_sel_sort8 CPS 3, two registered stages) with one
// register added on every output (q, fo, qn, fn) = "the reference re-timed by +1 edge".  gold of the sequential miter.
module ref_sort #(parameter integer EW = 11, FW = 1, ZQ = 1) (
    input wire clk, input wire rst_n, input wire [FW-1:0] fi, input wire [8*EW-1:0] d,
    output reg [FW-1:0] fo, output reg [8*EW-1:0] q, output reg [FW-1:0] fn, output reg [8*EW-1:0] qn);
    wire [FW-1:0] fo0, fn0; wire [8*EW-1:0] q0, qn0;
    old_dsdv_sel_sort8 #(.EW(EW), .CPS(3), .FW(FW), .ZQ(ZQ)) u (.clk(clk), .rst_n(rst_n), .fi(fi), .d(d), .fo(fo0), .q(q0), .fn(fn0), .qn(qn0));
    always @(posedge clk or negedge rst_n) if (!rst_n) begin fo <= 0; fn <= 0; end else begin fo <= fo0; fn <= fn0; end
    always @(posedge clk) begin q <= q0; qn <= qn0; end
endmodule
module new_sort #(parameter integer EW = 11, FW = 1, ZQ = 1, MUT = 0) (
    input wire clk, input wire rst_n, input wire [FW-1:0] fi, input wire [8*EW-1:0] d,
    output wire [FW-1:0] fo, output wire [8*EW-1:0] q, output wire [FW-1:0] fn, output wire [8*EW-1:0] qn);
    dsdv_sel_sort8 #(.EW(EW), .CPS(2), .FW(FW), .ZQ(ZQ), .MUT(MUT)) u (.clk(clk), .rst_n(rst_n), .fi(fi), .d(d), .fo(fo), .q(q), .fn(fn), .qn(qn));
endmodule
