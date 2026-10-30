(* keep_hierarchy, keep *)
module ot_dp_landing_relay (
    input  wire clk,
    input  wire rst_raw_n,
    input  wire d,
    output reg  q
);
    always @(posedge clk) begin
        if (!rst_raw_n) q <= 1'b0;
        else q <= d;
    end
endmodule
module top(input wire clk, input wire rst_n, input wire st, output wire mission, output wire o0, output wire o1);
reg reset_q;
always @(posedge clk) reset_q <= rst_n;
(* keep_hierarchy, keep *) ot_dp_landing_relay origin(.clk(clk),.rst_raw_n(reset_q),.d(st),.q(mission));
(* keep_hierarchy, keep *) ot_dp_landing_relay copy0(.clk(clk),.rst_raw_n(reset_q),.d(st),.q(o0));
(* keep_hierarchy, keep *) ot_dp_landing_relay copy1(.clk(clk),.rst_raw_n(reset_q),.d(st),.q(o1));
endmodule
