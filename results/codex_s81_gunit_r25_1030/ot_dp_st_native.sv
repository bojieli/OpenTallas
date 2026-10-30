// (feedthrough 4,859 / shared 2,937) -> 179 with it, the rest = plan-vs-bound width spares).
(* keep_hierarchy, keep *)
module ot_dp_st #(parameter integer W = 1) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    input  wire         ea,
    output reg  [W-1:0] q,
    output reg          eq
);
    always @(posedge clk) q <= d;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) eq <= 1'b0; else eq <= ea;
endmodule
// ot_dp_rsync: a reset spine landing (asbuilt.reset_spines): W active-low resets, each asserted asynchronously and
