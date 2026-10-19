module lpt_leaf #(parameter integer W = 8) (input wire clk, input wire rst_n, input wire [W-1:0] a,
    input wire [W-1:0] b, output reg [W-1:0] y);
    reg [3:0] c;
    always @(posedge clk or negedge rst_n) if (!rst_n) begin c <= 0; y <= 0; end else begin c <= c + 1; y <= a + b + c; end
endmodule

module lpt_rst(input wire clk,input wire rst_n,output reg rs);
 always @(posedge clk) rs <= rst_n;
endmodule

module lpt_fwd(input wire clk,input wire [7:0] x, output reg [7:0] y);
 always @(posedge clk) y <= x;
endmodule
