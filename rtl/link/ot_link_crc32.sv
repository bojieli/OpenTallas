`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_link_crc32: parallel CRC-32 (polynomial 0x04C11DB7, init 0xFFFFFFFF,
// MSB-first, no reflection, no final XOR) of a W-bit frame, in one cycle.
//
// The CRC is linear in the data: crc = step^W(init) ^ XOR_{b : d[b] = 1} e_b,
// with e_0 = POLY and e_{b+1} = step(e_b) (step = one zero-data LFSR shift).
// Output bit i is therefore the XOR of the data bits selected by a constant
// mask, computed at elaboration; synthesis maps each ^(d & MASK) to a
// balanced XOR tree (depth log2 W), where the serial LFSR loop would be a
// W-deep chain.  Bit-identical to the serial definition (checked by
// tb_w15_link_unit's CRC fault test and the frame checks).
// ---------------------------------------------------------------------------
module ot_link_crc32 #(
    parameter integer W = 64
) (
    input  wire [W-1:0] d,
    output wire [31:0]  crc
);
    localparam [31:0] POLY = 32'h04C1_1DB7;
    function automatic [31:0] step0(input [31:0] c);
        step0 = {c[30:0], 1'b0} ^ (c[31] ? POLY : 32'h0);
    endfunction
    function automatic [32*W-1:0] masks(input integer dummy);
        reg [31:0] e;
        integer b, i;
        begin
            masks = {32*W{1'b0}};
            e = POLY;
            for (b = 0; b < W; b = b + 1) begin
                for (i = 0; i < 32; i = i + 1) masks[i*W + b] = e[i];
                e = step0(e);
            end
        end
    endfunction
    function automatic [31:0] init_term(input integer dummy);
        reg [31:0] c;
        integer b;
        begin
            c = 32'hFFFF_FFFF;
            for (b = 0; b < W; b = b + 1) c = step0(c);
            init_term = c;
        end
    endfunction
    localparam [32*W-1:0] M = masks(0);
    localparam [31:0]     I0 = init_term(0);
    genvar i;
    generate for (i = 0; i < 32; i = i + 1) begin : g_bit
        assign crc[i] = (^(d & M[i*W +: W])) ^ I0[i];
    end endgenerate
endmodule
