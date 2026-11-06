`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// ot_s81_kp4_enc (s81-die-rtl-bind 2026-10-14, die item F10; STREAMING rewrite S81-KP4 2026-10-17): the transmit FEC of
// one S81 die link -- RS(544,514) "KP4" (GF(2^10), p = x^10 + x^3 + 1, g(x) = prod_{j=0..29} (x - alpha^j)), owner
// decision 2026-10-06: full KP4 FEC on every off-package link.  Reference model and frame: tools/s81_link/rs544.py.
//   in : one 512-b lane beat a cycle (the collective gearbox beat; the stream never stalls), tx_v = beat present
//   out: one 544-b PMA word a cycle: an FEC frame = 10 words = one codeword {header 20 = {AM 12'hA5C, seq 8},
//        10 beats, parity 30 symbols}; word w = codeword bits [5439 - 544 w -: 544]
// STRUCTURE (S81-KP4 10-17; replaces the A -> E -> O frame copies of 8cd04168b, whose 5,200-bit barrel window
// {60'b0, e_m} << 520 ph and 10:1 output select gave ph a fanout of 6,446, an 18-level setup path and 17,084 sinks):
//   * the parity LFSR runs ON THE ARRIVING STREAM: chunk k (52 symbols = 520 bits, 6 leading zero symbols in chunk 0)
//     lies inside {beat k-1, beat k} at a FIXED offset per k (8 k bits apart), so the window is a 10:1 one-hot select
//     over two registered beats (local wires, replicated select registers), never a barrel shifter;
//   * next rem = A rem ^ P0 ch[259:0] ^ P1 ch[519:260] (ot_s81_kp4_enc_mat.svh, tools/s81_link/gen_kp4_linear.py):
//     the two window parts are computed a cycle ahead and registered (wb), only A rem (<= 173 inputs) is in the loop;
//   * the beats wait in a 6-deep register delay line d0..d5; PMA word w is a 10:1 one-hot select over {d5, d4} at a
//     fixed offset per w (32 w bits apart; word 0 starts with the header, word 9 ends with the parity).
//   Schedule (fixed cycles, t_k = the cycle beat k sits in d0): chunk window ch at t_k + 1, wb at t_k + 3, rem after
//   chunk k at t_k + 4, parity par from t_9 + 5, PMA word w in p_d at t_k + 6.  RTL latency port -> p_d 7 cycles
//   (8cd04168b: 21).  Registers: ~6.4k (8cd04168b: 17.1k).  The tile adds one pin register per port (recipe 3/4).
// The PMA side runs continuously from the first full frame on (p_v); before it the PMA carries zero words (no AM:
// the receiver stays in hunt).  Every output leaves a flop.  Reset: regional synchronous tree, control only.
// MUT 1: parity symbol 7 inverted (the receive side must see a nonzero syndrome) -- bench mutant.
// ---------------------------------------------------------------------------------------------------------------
module ot_s81_kp4_enc #(parameter integer MUT = 0) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          tx_v,
    input  wire [511:0]  tx_d,
    output reg           p_v,
    output reg  [543:0]  p_d,
    output wire          fault          // a cycle without a beat once the stream has started (sticky)
);
`include "ot_s81_gf1024.svh"
    localparam integer NP = 30;
    localparam integer NRC = 4;          // chunk-select copies (130 window bits each)
    localparam integer NRO = 17;         // word-select copies (32 PMA bits each)
    wire [3:0] rs_n;
    ot_s81_kp4_rst #(.NL(4)) u_rst (.clk(clk), .rst_n(rst_n), .rs_n(rs_n));
    // ---------------- input side: beat phase, header, beat delay line
    reg        run, flt;
    reg  [3:0] ph;                       // index of the beat arriving at the port
    reg  [7:0] seq;
    reg  [19:0] h0;                      // header of the frame whose beats are in flight (loaded with beat 0)
    reg  [511:0] d0, d1, d2, d3, d4, d5;
    wire       st = tx_v || run;         // a beat enters d0 this cycle
    (* keep *) reg [9:0] sk [0:NRC-1];   // one-hot beat index of d0 (zero = no beat), NRC copies
    always @(posedge clk) begin
        d0 <= tx_d; d1 <= d0; d2 <= d1; d3 <= d2; d4 <= d3; d5 <= d4;
        if (st && ph == 4'd0) h0 <= {12'hA5C, seq};
    end
    integer i;
    always @(posedge clk)
        if (!rs_n[0]) begin
            run <= 1'b0; flt <= 1'b0; ph <= 4'd0; seq <= 8'd0;
            for (i = 0; i < NRC; i = i + 1) sk[i] <= 10'd0;
        end else begin
            if (tx_v) run <= 1'b1;
            if (run && !tx_v) flt <= 1'b1;
            if (st) begin
                ph <= (ph == 4'd9) ? 4'd0 : ph + 1'b1;
                if (ph == 4'd0) seq <= seq + 1'b1;
            end
            for (i = 0; i < NRC; i = i + 1) sk[i] <= st ? (10'd1 << ph) : 10'd0;
        end
    // ---------------- chunk window: chunk k = {d1, d0}[591 - 8k -: 520]; chunk 0 = {60'b0, h0, d0[511:72]}
    wire [1023:0] wd = {d1, d0};
    wire [519:0]  src [0:9];
    genvar gk, gb;
    generate for (gk = 0; gk < 10; gk = gk + 1) begin : g_src
        if (gk == 0) begin : g0
            assign src[gk] = {60'b0, h0, d0[511:72]};
        end else begin : gn
            assign src[gk] = wd[591 - 8 * gk -: 520];
        end
    end endgenerate
    reg  [519:0] ch_q;
    wire [519:0] ch_n;
    generate for (gb = 0; gb < 520; gb = gb + 1) begin : g_chm
        wire [9:0] s;
        for (gk = 0; gk < 10; gk = gk + 1) begin : g_s
            assign s[gk] = src[gk][gb];
        end
        assign ch_n[gb] = |(s & sk[gb / 130]);
    end endgenerate
    // ---------------- parity: window parts registered (wb), state loop rem
    wire [299:0] e_ar, e_p0, e_p1;
    reg  [299:0] rem_q, pp0, pp1, wb, par;
`include "ot_s81_kp4_enc_mat.svh"
    // control pipeline: chunk-0 / chunk-9 flags at the ch, pp, wb and rem stages
    reg  [3:0] f0, f9;                   // [0] = ch stage, [1] = pp stage, [2] = wb stage, [3] = rem (par load)
    (* keep *) reg [3:0] f0w;            // chunk-0 flag at the wb stage, 4 copies (75 rem bits each)
    always @(posedge clk) begin
        ch_q <= ch_n;
        pp0 <= e_p0; pp1 <= e_p1;
        wb <= pp0 ^ pp1;
    end
    always @(posedge clk)
        if (!rs_n[1]) begin f0 <= 4'd0; f9 <= 4'd0; f0w <= 4'd0; end
        else begin
            f0 <= {f0[2:0], sk[0][0]};
            f9 <= {f9[2:0], sk[0][9]};
            f0w <= {4{f0[1]}};
        end
    genvar gr;
    generate for (gr = 0; gr < 300; gr = gr + 1) begin : g_rem
        always @(posedge clk) rem_q[gr] <= (f0w[gr / 75] ? 1'b0 : e_ar[gr]) ^ wb[gr];
    end endgenerate
    // parity of the frame: rem after chunk 9, rem[0] (rem_q[9:0], the x^29 side) transmitted first (MUT 1: symbol 7
    // inverted)
    wire [299:0] rem_tx;
    generate for (gr = 0; gr < NP; gr = gr + 1) begin : g_ptx
        assign rem_tx[299 - 10 * gr -: 10] = rem_q[10 * gr +: 10] ^ ((MUT == 1 && gr == 7) ? 10'h3FF : 10'h000);
    end endgenerate
    always @(posedge clk)
        if (f9[3]) par <= rem_tx;
    // ---------------- PMA words: word w = {d5, d4} at a fixed offset (cycle t_w + 5; d5 = beat w, d4 = beat w + 1)
    reg  [9:0] so [0:4];                 // one-hot beat index delayed 1..5 (so[4] = index of d5)
    (* keep *) reg [9:0] sw [0:NRO-1];   // so[3] delayed once more: the word select at the d5 stage, NRO copies
    reg        o_v;
    always @(posedge clk)
        if (!rs_n[2]) begin
            for (i = 0; i < 5; i = i + 1) so[i] <= 10'd0;
            for (i = 0; i < NRO; i = i + 1) sw[i] <= 10'd0;
            o_v <= 1'b0; p_v <= 1'b0;
        end else begin
            so[0] <= sk[1]; so[1] <= so[0]; so[2] <= so[1]; so[3] <= so[2]; so[4] <= so[3];
            for (i = 0; i < NRO; i = i + 1) sw[i] <= so[3];
            if (so[4][0]) o_v <= 1'b1;
            p_v <= o_v || so[4][0];
        end
    wire [1023:0] wo = {d5, d4};
    wire [543:0]  wsrc [0:9];
    generate for (gk = 0; gk < 10; gk = gk + 1) begin : g_wsrc
        if (gk == 0) begin : g0
            assign wsrc[gk] = {h0, d5, d4[511:500]};
        end else if (gk == 9) begin : g9
            assign wsrc[gk] = {d5[243:0], par};
        end else begin : gn
            assign wsrc[gk] = wo[1043 - 32 * gk -: 544];
        end
    end endgenerate
    generate for (gb = 0; gb < 544; gb = gb + 1) begin : g_om
        wire [9:0] s;
        for (gk = 0; gk < 10; gk = gk + 1) begin : g_s
            assign s[gk] = wsrc[gk][gb];
        end
        always @(posedge clk) p_d[gb] <= |(s & sw[gb / 32]);
    end endgenerate
    assign fault = flt;
endmodule
