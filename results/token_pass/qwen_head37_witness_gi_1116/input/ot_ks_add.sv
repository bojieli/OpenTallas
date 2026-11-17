`timescale 1ns/1ps
// CTLM7 (2026-10-20): explicit Kogge-Stone parallel-prefix adder, s = a + b + cin (mod 2^W).
// Log2(W) prefix levels written as plain AND/OR/XOR so the bounded native construction keeps a
// log-depth carry network (the generic $alu techmap it otherwise keeps is a serial carry chain).
module ot_ks_add #(parameter integer W = 20) (
    input  wire [W-1:0] a, b,
    input  wire         cin,
    output wire [W-1:0] s
);
    localparam integer L = (W <= 1) ? 1 : $clog2(W);
    wire [W-1:0] g0 = a & b, p0 = a ^ b;
    wire [W-1:0] gg [0:L], pp [0:L];
    // fold cin into bit 0: g0' = g0 | p0 & cin
    assign gg[0] = {g0[W-1:1], g0[0] | (p0[0] & cin)};
    assign pp[0] = p0;
    genvar l, i;
    generate for (l = 0; l < L; l = l + 1) begin : g_lvl
        for (i = 0; i < W; i = i + 1) begin : g_bit
            if (i >= (1 << l)) begin : g_c
                assign gg[l+1][i] = gg[l][i] | (pp[l][i] & gg[l][i - (1 << l)]);
                assign pp[l+1][i] = pp[l][i] & pp[l][i - (1 << l)];
            end else begin : g_p
                assign gg[l+1][i] = gg[l][i];
                assign pp[l+1][i] = pp[l][i];
            end
        end
    end endgenerate
    // carry into bit i = prefix generate of bits [i-1:0] (bit 0 gets cin)
    assign s = p0 ^ {gg[L][W-2:0], cin};
endmodule
