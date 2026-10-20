// qfd_ckdiv6 -- the collective's 200 MHz block clock (coll_blk, 5000 ps) as a REAL registered divide-by-6 of the
// collective core clock clk_coll (stream, 833.333 ps) on the Qwen compute die (lane QW-GEN5 10-20, g5 GEN).
//
// Replaces the R0 receiver model output clk_rx.pll_coll_blk, which the GEN emitted as an identity of pll_fwd (833 ps)
// while clocks_*.tcl declares coll_blk at 5000 ps: functionally wrong. The r10 collective source documents
// B(m) = F(5m) = C(6m): one coll_blk period = 6 core periods, so the divider runs on the collective's own core trunk.
//
// Function: ck_o is a 50 % duty /6 of ck, taken straight from a flop (q): high for counts 0..2, low for 3..5. After
// reset release ck_o's first rising edge is the 3rd ck edge after rst_n releases (2 landing + 1; fixed, deterministic: the collective's
// own reset releases the phase; the die reset calendar prices it, as for every other root).
//
// Safe-design checklist (owner 10-19):
//  1 pins   : rst_n lands in 2 registered stages (rl); ck_o is a flop output; no other inputs.
//  2 reach  : 3 + 3 flops, placed by the GEN beside io_collective's blk_ck pins (< 405 um).
//  3 fanout : rl[1] drives 4 flops; q drives the coll_blk clock trunk (the die clock tool builds that tree).
//  4 depth  : 3-bit counter compare, < 6 levels.
//  5 storage: 6 flops.
//  7 clock  : one clock ck (clk_coll); ck_o is the root of the coll_blk region tree (die clock tool).
//  8 schedule: static; the coll_blk phase is a fixed count after reset release (no handshake).
module qfd_ckdiv6 (
    input  wire ck,
    input  wire rst_n,      // collective reset (active low, async assert, release lands in 2 stages on ck)
    output wire ck_o
);
    reg [1:0] rl;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) rl <= 2'b00;
        else        rl <= {rl[0], 1'b1};

    reg [2:0] c;
    reg       q;
    always @(posedge ck or negedge rl[1])
        if (!rl[1]) begin
            c <= 3'd0;
            q <= 1'b0;
        end else begin
`ifdef QFD_CKDIV6_MUT_DIV5
            c <= (c == 3'd4) ? 3'd0 : c + 3'd1;      // bench mutant: divide by 5
`else
            c <= (c == 3'd5) ? 3'd0 : c + 3'd1;
`endif
            q <= (c < 3'd3);
        end
    assign ck_o = q;
endmodule
