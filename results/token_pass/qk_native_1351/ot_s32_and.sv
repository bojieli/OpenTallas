module ot_s32_and #(parameter integer W = 16) (input wire s, input wire [W-1:0] a, output wire [W-1:0] y);
    assign y = a & {W{s}};
endmodule
