`timescale 1ns/1ps
`default_nettype none
// Leaf cores of examples/tiny_plan.json (illustration + generator test vehicle).
module tiny_src_core (input wire clk, input wire rst_n, input wire [31:0] din, input wire [15:0] r,
                      output reg [63:0] x, output reg [7:0] cfg);
    always @(posedge clk) x <= {din ^ {r, r}, din};
    always @(posedge clk or negedge rst_n) if (!rst_n) cfg <= 8'd0; else cfg <= cfg + 8'd1;
endmodule
module tiny_mid_core (input wire clk, input wire [7:0] cfg_i, output reg [7:0] cfg_o);
    always @(posedge clk) cfg_o <= cfg_i;
endmodule
module tiny_sink_core (input wire clk, input wire [63:0] x, input wire [7:0] cfg, input wire x_ep,
                       output reg [15:0] r, output reg [31:0] dout);
    always @(posedge clk) begin
        r <= x[15:0] ^ {8'd0, cfg};
        dout <= x_ep ? (x[63:32] + x[31:0]) : 32'd0;
    end
endmodule
`default_nettype wire
