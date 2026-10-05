`timescale 1ns/1ps
// Exact number of attention score position rounds. W is a power of two and
// split_log2 is a valid power-of-two divisor of G. Factoring G into an odd
// divisor and a power of two avoids a variable-divisor circuit for G=6144.
module ot_hdc_dyn_ttiles #(
    parameter integer W=16, G=4, NW=18
) (
    input wire [NW-1:0] pos,
    input wire [3:0] split_log2,
    output wire [NW-1:0] rounds,
    output wire invalid_split
);
    function automatic integer trailing_zeros(input integer value);
        integer n;
        begin
            n=0;
            while ((value & 1)==0 && value>0) begin
                value=value>>1; n=n+1;
            end
            trailing_zeros=n;
        end
    endfunction
    localparam integer WT=trailing_zeros(W);
    localparam integer GT=trailing_zeros(G);
    localparam integer ODD=G>>GT;
    wire [4:0] shift_amount=WT+GT-split_log2;
    wire [NW-1:0] shifted=pos>>shift_amount;
    assign invalid_split=(W != (1<<WT)) || split_log2>GT || split_log2>WT+GT;
    assign rounds=invalid_split ? {NW{1'b0}} : (shifted/ODD)+1'b1;
endmodule
