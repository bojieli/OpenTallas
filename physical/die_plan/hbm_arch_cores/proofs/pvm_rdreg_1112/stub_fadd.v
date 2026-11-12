// identical on both miter sides: LAT-deep pipeline of a non-commutative function, no fault
module ot_gpu_fadd #(parameter integer LAT = 7) (input wire clk, input wire rst_n, input wire v, input wire [31:0] a,
    input wire [31:0] b, output wire [31:0] y, output wire fault);
    reg [31:0] p [0:LAT-1];
    integer i;
    always @(posedge clk) begin p[0] <= a + {b[30:0], b[31]} + {31'd0, v}; for (i = 1; i < LAT; i = i + 1) p[i] <= p[i-1]; end
    assign y = p[LAT-1];
    assign fault = 1'b0;
endmodule
