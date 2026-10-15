(* keep_hierarchy = 1 *) module ot_coll_rep_reg #(parameter integer W = 1, ID = 0, RST = 1) (
    input wire clk, input wire rst_n, input wire [W-1:0] d, output reg [W-1:0] q);
    generate if (RST) begin : g_r
        always @(posedge clk or negedge rst_n) if (!rst_n) q <= {W{1'b0}}; else q <= d;
    end else begin : g_n
        always @(posedge clk) q <= d;
    end endgenerate
endmodule
