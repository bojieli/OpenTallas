module ot_d2d_kffr (input wire ck, input wire rst_n, input wire d, output reg q);
    always @(posedge ck or negedge rst_n) if (!rst_n) q <= 1'b0; else q <= d;
endmodule
