`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// Qwen TP8 split compute die, contract v1: the die x network (x-line delivery fix, el1014-qwen-split-compute.log).
//
// Reference (rtl/hdc/ot_qwen_me_array_w12.sv): tile t listens to quad line t mod NXL, all NXL lines every cycle.
// The merged die broadcast ONE line per head root to every tile of its half: not the reference for split > TG.
//
// Die network (this module = its functional definition; the die adds only balanced register stages, equal depth to
// every tile, the reference's BD):
//   * tile id placement (contract v1 TILE MAP): 4x4 blocks of 16 consecutive tile ids, row-major inside the block
//     (local id l = 4*row_in_block + col_in_block); block b sits in block column bc with bc mod 2 == b mod 2 (even
//     blocks fill the even block columns row by row, odd blocks the odd ones; the TP8 die's three bands are 8 even + 8
//     odd blocks each, so the band tree is unchanged).
//   * every physical tile column C = 4*bc + lc carries ONE bundle of 4 lines, fixed by its position only:
//       bundle(C)[i] = line (16*(bc mod 2) + 4*i + lc) mod NXL,  i = 0..3   (4 x TG*32 = 512 b at TG 4)
//     -> with NXL = 32 (SMAX 7, splits <= 128) every tile of the column finds its reference line t mod 32 in it.
//   * the tile at physical row R takes bundle[R mod 4] (a 4:1 select at the tile pin, set by its row strap).
// Bandwidth: NXL*TG*32 = 4,096 b/cycle out of the vector memory (32 lines, its native rate), 512 b per column chain.
// XMUT = 1 (bench mutant): tile 1 takes bundle[(R + 1) mod 4], a wrong line -> the bench must fail.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qwen_xdie_net #(
    parameter integer NT   = 32,      // tiles
    parameter integer TG   = 4,
    parameter integer NXL  = 32,      // reference quad lines (2^SMAX / TG); must divide 32
    parameter integer NBC  = 2,       // block columns (even); NT = 16 * NBC * block rows
    parameter integer XMUT = 0
) (
    input  wire [NXL*TG*32-1:0] xl,
    output wire [NT*TG*32-1:0]  xt
);
    localparam integer LW  = TG * 32;
    localparam integer NB  = NT / 16;
    localparam integer NC  = 4 * NBC;
    initial begin
        if (NT % 16 != 0 || NB % NBC != 0 || NBC % 2 != 0 || 32 % NXL != 0)
            $fatal(1, "ot_qwen_xdie_net: NT %0d / NBC %0d / NXL %0d not a legal die map", NT, NBC, NXL);
    end
    function automatic integer col_of(input integer t);
        integer b, e;
        begin
            b = t / 16; e = b / 2;
            col_of = 4 * (2 * (e % (NBC / 2)) + (b % 2)) + (t % 16) % 4;
        end
    endfunction
    function automatic integer row_of(input integer t);
        integer b, e;
        begin
            b = t / 16; e = b / 2;
            row_of = 4 * (e / (NBC / 2)) + (t % 16) / 4;
        end
    endfunction
    wire [4*LW-1:0] bundle [0:NC-1];
    genvar c, i, t;
    generate
        for (c = 0; c < NC; c = c + 1) begin : g_col
            for (i = 0; i < 4; i = i + 1) begin : g_line
                localparam integer L = (16 * ((c / 4) % 2) + 4 * i + c % 4) % NXL;
                assign bundle[c][i*LW +: LW] = xl[L*LW +: LW];
            end
        end
        for (t = 0; t < NT; t = t + 1) begin : g_tile
            localparam integer C = col_of(t);
            localparam integer R = row_of(t);
            localparam integer SEL = (XMUT != 0 && t == 1) ? (R + 1) % 4 : R % 4;
            assign xt[t*LW +: LW] = bundle[C][SEL*LW +: LW];
        end
    endgenerate
endmodule
