module ot_s32_sel #(parameter integer W = 16) (input wire s, input wire [W-1:0] a, b, output wire [W-1:0] y);
    assign y = s ? a : b;
endmodule
