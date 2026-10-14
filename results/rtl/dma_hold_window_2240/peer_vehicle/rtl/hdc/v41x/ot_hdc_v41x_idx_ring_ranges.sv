`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hdc_v41x_idx_ring_ranges -- scan geometry of the QUARTER-PER-STACK index
// key layout (W11): which HBM blocks each stack reads for one user's scan.
//
// Layout (all four stacks alike).  A user owns, on every stack, a RING of
// C = RSB x 1,024 + RTAIL key slots stored as RSB full super-blocks (17 x
// 4 KB: one scale block, 16 code blocks) plus one tail super-block of RTAIL
// keys (1 + ceil(RTAIL / 64) blocks): UBLK blocks per user per stack, at
// block cfg_key_base_block + user x UBLK.  Stack q holds position quarter q
// of the user's N keys (Qs = 8 floor(N / 32); quarter q < 3 is [q Qs,
// (q+1) Qs), quarter 3 is [3 Qs, N)), key position p in ring slot p mod C.
// The placement is a function of (user, N) alone: no per-user pointer state.
// Valid while every quarter fits its ring: Qs <= C and N - 3 Qs <= C (o_fault
// otherwise).  RTAIL is a multiple of 16 so the wrap keeps 16-key beat phase.
// Spec: RSB 64, RTAIL 32 (C = 65,568 >= 65,559, the longest quarter 3 of a
// 262,144-row die slice), UBLK 1,090.
//
// Per stack: the head slot h = (q Qs) mod C; segment 1 starts at super-block
// h / 1,024 with skip h mod 1,024 and runs n1 = min(L_q, C - h) keys; segment 2
// (the wrap) starts at the ring's first block with n2 = L_q - n1 keys.  These
// drive ot_hdc_v41x_idx_kstream_ring; o_skip drives ot_hdc_v41x_idx_quarter_join.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_idx_ring_ranges #(
    parameter integer HW=23, UW=10, RSB=64, RTAIL=32
) (
    input  wire [HW+9:0]     i_nkeys,
    input  wire [UW-1:0]     i_user,
    input  wire [HW-1:0]     cfg_key_base_block,
    output wire [4*HW-1:0]   o_base1,
    output wire [4*10-1:0]   o_skip,
    output wire [4*(HW+10)-1:0] o_n1,
    output wire [4*HW-1:0]   o_base2,
    output wire [4*(HW+10)-1:0] o_n2,
    output wire [HW-1:0]     o_user_base,
    output wire              o_fault
);
    localparam integer C = RSB*1024 + RTAIL;
    localparam integer UBLK = RSB*17 + ((RTAIL != 0) ? 1 + (RTAIL + 63) / 64 : 0);
    localparam integer NW = HW + 10;
    initial if (RTAIL % 16 != 0 || RTAIL >= 1024 || RSB < 1)
        $fatal(1, "ot_hdc_v41x_idx_ring_ranges: RTAIL must be a multiple of 16 below 1,024");
    wire [HW-1:0] ub = cfg_key_base_block + HW'(i_user) * HW'(UBLK);
    assign o_user_base = ub;
    wire [NW-1:0] qsv = (i_nkeys >> 5) << 3;
    wire [NW-1:0] l3 = i_nkeys - 3 * qsv;
    assign o_fault = (qsv > NW'(C)) || (l3 > NW'(C));
    // x mod C for x < 4 C: at most three compare-subtracts
    function automatic [NW-1:0] modc(input [NW+1:0] x);
        reg [NW+1:0] y;
        begin
            y = x;
            if (y >= (NW+2)'(C)) y = y - (NW+2)'(C);
            if (y >= (NW+2)'(C)) y = y - (NW+2)'(C);
            if (y >= (NW+2)'(C)) y = y - (NW+2)'(C);
            modc = y[NW-1:0];
        end
    endfunction
    genvar q;
    generate for (q = 0; q < 4; q = q + 1) begin : g_q
        wire [NW-1:0] len = (q == 3) ? l3 : qsv;
        wire [NW-1:0] h = modc((NW+2)'(q) * qsv);
        wire [NW-1:0] room = NW'(C) - h;
        wire [NW-1:0] n1 = (len < room) ? len : room;
        assign o_base1[q*HW +: HW] = ub + HW'(17) * HW'(h >> 10);
        assign o_skip[q*10 +: 10] = h[9:0];
        assign o_n1[q*NW +: NW] = n1;
        assign o_base2[q*HW +: HW] = ub;
        assign o_n2[q*NW +: NW] = len - n1;
    end endgenerate
endmodule
