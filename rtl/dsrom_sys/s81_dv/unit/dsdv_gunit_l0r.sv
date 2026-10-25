`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-GUNIT3 (2026-10-17): dsdv_gunit_l0r -- G-unit side leaf L0r (E of L0): the HP root store (2 window buffers x 16
// slices x 2 halves x 6 words of 32 bits = 12,288 flops) and the level-5 group stream, split out of L0 (the one-leaf L0
// was 15,319 sinks on one root, TT insertion 333 ps: clock-rule FAIL).  W face only (L0): every input lands in a flop,
// every output leaves a flop.
//   wr_*   store writes (L0 registers them on the edge the one-leaf form wrote): slot {g, h} = wr_?gh, buffer wr_b,
//          words j = 0..5 = wr_?d[32 j +: 32]; two writes (a, b) an edge.
//   go_*   window complete (accumulation go_acc in buffer go_b): the 16-group stream starts on the edge after it lands.
//   r_*    the stream, one group a cycle (L0 relays it to L4):  group i = 4 k + m = slices 4m .. 4m+3, half k >> 1,
//          words (k & 1) * 3 + 0..2: {D32, D8, C8, C16b, C16a, B16b, B16a, B8, A8, A32}.
// Timing: a write lands in the store 2 edges after L0's register, a go starts the stream 2 edges after L0's register,
// so a window's last write is in the store before the stream's first read (the same order as the one-leaf form).
// The read select is replicated per output byte (40 copies, keep; S81U-GUNIT4: the per-word copy drove 3,059 loads,
// the leaf's worst reg->reg path): one copy drives 8 bits of a 32:1 word mux.
// S81U-GUNIT6 (10-17, native pin rules): rst_n drives only ot_rst_relay (2 kept region copies: input flops, stream);
// release +3 edges after the port (transaction-level exact).  0 data edges.
// r_f (sticky): a go while the previous stream still runs.  MUT (bench only): 6 = roots 1 / 2 of g = 1 mod 4 swapped.
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_gunit_l0r #(
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          wr_av, input wire [4:0] wr_agh, input wire [191:0] wr_ad,
    input  wire          wr_bv, input wire [4:0] wr_bgh, input wire [191:0] wr_bd, input wire wr_b,
    input  wire          go_a, input wire [4:0] go_acc, input wire go_b,
    output reg           r_v, output reg [3:0] r_i, output reg [4:0] r_acc, output reg [319:0] r_d, output reg r_f
);
    // Private sticky state; the r_f boundary flop drives only the output pin.
    // Both capture the same next value, so this adds one FF and zero cycles.
    (* keep = "true" *) reg fault_hold;
    integer j;
    wire [1:0] rq;
    ot_rst_relay #(.REGIONS(2)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rq));
    // ---------------------------------------------------------------- input flops
    reg av, bv, wb, ga; reg [4:0] agh, bgh, gacc; reg [191:0] ad, bd; reg gb;
    always @(posedge clk or negedge rq[0])
        if (!rq[0]) begin av <= 1'b0; bv <= 1'b0; ga <= 1'b0; end
        else begin av <= wr_av; bv <= wr_bv; ga <= go_a; end
    always @(posedge clk) begin agh <= wr_agh; ad <= wr_ad; bgh <= wr_bgh; bd <= wr_bd; wb <= wr_b; gacc <= go_acc; gb <= go_b; end
    // ---------------------------------------------------------------- root store (2 window buffers)
    reg [31:0] rs [0:2*16*2*6-1];                       // buffer b, slice g, half h, word j (0..5)
    always @(posedge clk) begin
        if (av) for (j = 0; j < 6; j = j + 1) rs[192 * wb + 6 * agh + j] <= ad[32 * j +: 32];
        if (bv) for (j = 0; j < 6; j = j + 1) rs[192 * wb + 6 * bgh + j] <= bd[32 * j +: 32];
    end
    // ---------------------------------------------------------------- group stream (16 groups an accumulation)
    reg a_on; reg [3:0] a_i; reg [4:0] a_acc;
    wire [199:0] sel;                                   // {b, i} per output byte (40 kept copies: word w, byte k = 4 w + k)
    genvar c;
    generate for (c = 0; c < 40; c = c + 1) begin : g_sel
        (* keep = "true" *) reg [4:0] q;
        always @(posedge clk) q <= ga ? {gb, 4'd0} : {q[4], q[3:0] + 4'd1};
        assign sel[5 * c +: 5] = q;
    end endgenerate
    always @(posedge clk or negedge rq[1])
        if (!rq[1]) begin a_on <= 1'b0; a_i <= 4'd0; r_v <= 1'b0; r_f <= 1'b0; fault_hold <= 1'b0; end
        else begin
            if (ga) begin a_on <= 1'b1; a_i <= 4'd0; a_acc <= gacc; if (a_on && a_i != 4'd15) fault_hold <= 1'b1; end
            else if (a_on) begin a_i <= a_i + 4'd1; if (a_i == 4'd15) a_on <= 1'b0; end
            r_f <= fault_hold || (ga && a_on && a_i != 4'd15);
            r_v <= a_on;
        end
    // word w of group i: slice 4m + s, half k >> 1, word (k & 1) * 3 + o  (m = i[1:0], k = i[3:2])
    function automatic [8:0] wad(input [4:0] bi, input integer s, input integer o);
        wad = 9'd192 * bi[4] + 9'd12 * ({bi[1:0], 2'd0} + s) + 9'd6 * bi[3] + 9'd3 * bi[2] + o;
    endfunction
    // output word w (A32 [31:0] .. D32 [319:288]) = slice 4m + ws(w), word wo(w)
    function automatic integer ws(input integer w); ws = (w < 2) ? 0 : (w < 5) ? 1 : (w < 8) ? 2 : 3; endfunction
    function automatic integer wo(input integer w);
        case (w) 1, 6, 9: wo = 1; 3: wo = (MUT == 6) ? 2 : 1; 4: wo = (MUT == 6) ? 1 : 2; 7: wo = 2; default: wo = 0; endcase
    endfunction
    integer w, k;
    always @(posedge clk) begin
        r_i <= a_i; r_acc <= a_acc;
        for (w = 0; w < 10; w = w + 1)
            for (k = 0; k < 4; k = k + 1)
                r_d[32 * w + 8 * k +: 8] <= rs[wad(sel[5 * (4 * w + k) +: 5], ws(w), wo(w))][8 * k +: 8];
    end
endmodule
