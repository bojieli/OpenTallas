`timescale 1ns/1ps
// Baseline for source-pinned structural arithmetic replication.
// Input pins really register; old golden adder cuts and output registers stay.
module ot_s81svc7_add_graph_input (
    input wire clk, rst_n, valid_in,
    input wire [31:0] a,b,
    output wire [31:0] y,
    output wire [1:0] err,
    output wire valid_out
);
    (* keep *) reg rst0,rst1;
    (* keep *) reg [64:0] pins;
    always @(posedge clk) begin
        rst0<=rst_n; rst1<=rst0;
        pins<={valid_in,a,b};
    end
    ot_hdc_fp32_add_f12_l4 u_add(.clk(clk),.rst_n(rst1),.valid_in(pins[64]),
        .a(pins[63:32]),.b(pins[31:0]),.y(y),.err(err),.valid_out(valid_out));
endmodule
