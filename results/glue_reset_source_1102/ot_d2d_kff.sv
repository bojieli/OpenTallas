module ot_d2d_kff (input wire ck, input wire d, output reg q);
    always @(posedge ck) q <= d;
endmodule
