`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_s81hd_key (S81-HEAD HD-TILE 10-21): the ot_rom_argmax_rows order key of an FP32 value, census-safe.
//   key(x) = c[31] ? ~c : (c | 0x8000_0000),  c = (x == -0) ? +0 : x       (real order, -0 = +0)
// Two registered stages (latency 2, no valid: it recomputes every cycle).  Stage 1 registers x with kept copies of the
// two wide selects (invert = x[31] && x != -0, zero = x == -0), one copy per 8-bit group; stage 2 applies them, so no
// net drives more than ~16 load pins (the mapped AOI/OAI select costs 2 pins a bit).
// ---------------------------------------------------------------------------
module ot_s81hd_key (
    input  wire        ck,
    input  wire [31:0] x,
    output reg  [31:0] key
);
    reg [31:0] xq;
    (* keep *) reg [3:0] inv;
    (* keep *) reg [3:0] zro;
    wire negz = x == 32'h8000_0000;
    always @(posedge ck) begin
        xq  <= x;
        inv <= {4{x[31] & ~negz}};
        zro <= {4{negz}};
    end
    integer b;
    always @(posedge ck)
        for (b = 0; b < 32; b = b + 1)
            if (b == 31) key[b] <= ~inv[3];                         // +x / +0 / -0 -> 1, -x -> 0
            else key[b] <= ~zro[b / 8] & (xq[b] ^ inv[b / 8]);
endmodule
