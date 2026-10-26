`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// ot_s81_kp4_enc (s81-die-rtl-bind 2026-10-14, die item F10): the transmit FEC of one S81 die link -- RS(544,514)
// "KP4" (GF(2^10), p = x^10 + x^3 + 1, g(x) = prod_{j=0..29} (x - alpha^j)), owner decision 2026-10-06: full KP4
// FEC on every off-package link (results/arch/dsrom_s81_rack_20261006/rack.json decision_links).  Reference model and
// frame definition: tools/s81_link/rs544.py.
//   in : one 512-b lane beat a cycle (the collective gearbox beat; the stream never stalls), tx_v = beat present
//   out: one 544-b PMA word a cycle: an FEC frame = 10 words = one codeword {header 20 = {AM 12'hA5C, seq 8},
//        10 beats, parity 30 symbols}; word w = codeword bits [5439 - 544 w -: 544]
// Pipeline (fixed 10-cycle schedule, one codeword a frame): A collects 10 beats; at the frame strobe the message is
// moved to E, whose parity is computed over the next 10 cycles (52 symbols a cycle through the 30-stage LFSR, 6
// leading zero symbols); at the next strobe {message, parity} moves to O, emitted one word a cycle.  Latency 20 + 1.
// The PMA side runs continuously from the first full frame on (p_v); before it the PMA carries zero words (no AM:
// the receiver stays in hunt).  Every output leaves a flop.
// MUT 1: parity symbol 7 inverted (the receive side must see a nonzero syndrome) -- bench mutant.
// ---------------------------------------------------------------------------------------------------------------
module ot_hbm_kp4_enc_linear #(parameter integer MUT = 0) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          tx_v,
    input  wire [511:0]  tx_d,
    output reg           p_v,
    output reg  [543:0]  p_d,
    output wire          fault          // a cycle without a beat once the stream has started (sticky)
);
`include "ot_s81_gf1024.svh"
    localparam integer NS = 514, NP = 30, SPC = 52;      // message symbols, parity symbols, symbols a cycle
    reg  [3:0]    ph;                   // beat index in the frame being collected
    reg           run, flt;
    reg  [5119:0] a_b;                  // collecting
    reg  [7:0]    seq;
    reg  [5139:0] e_m;                  // message being encoded
    reg  [9:0]    rem [0:NP-1];         // LFSR (rem[0] = x^29 coefficient side, the feedback end)
    reg           e_v;
    reg  [5439:0] o_c;                  // codeword being emitted
    reg           o_v;
    integer i, k;
    // message symbol s (s = 0 first): e_m[5139 - 10 s -: 10]; cycle c processes symbols 52 c - 6 .. 52 c + 45
    reg [9:0] nrem [0:NP-1];
    reg [9:0] fb, sym;
    wire[819:0]linear_input;
    wire[299:0]linear_output;
    reg[519:0]linear_symbols;
    always @* case(ph)
    4'd0:linear_symbols={60'd0,e_m[5139-:460]};
    4'd1:linear_symbols=e_m[4679-:520];
    4'd2:linear_symbols=e_m[4159-:520];
    4'd3:linear_symbols=e_m[3639-:520];
    4'd4:linear_symbols=e_m[3119-:520];
    4'd5:linear_symbols=e_m[2599-:520];
    4'd6:linear_symbols=e_m[2079-:520];
    4'd7:linear_symbols=e_m[1559-:520];
    4'd8:linear_symbols=e_m[1039-:520];
    4'd9:linear_symbols=e_m[519-:520];
    default:linear_symbols=520'd0;
    endcase
    genvar lm;generate for(lm=0;lm<30;lm=lm+1)begin:g_linear
    assign linear_input[520+(29-lm)*10+:10]=rem[lm];
    always @* nrem[lm]=linear_output[(29-lm)*10+:10];
    end endgenerate
    assign linear_input[519:0]=linear_symbols;
    ot_hbm_kp4_encode52_map u_map(.x(linear_input),.y(linear_output));
    reg [299:0] par;
    always @* for (i = 0; i < NP; i = i + 1) par[299 - 10 * i -: 10] = nrem[i] ^ ((MUT == 1 && i == 7) ? 10'h3FF : 10'h000);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            ph <= 0; run <= 1'b0; flt <= 1'b0; seq <= 8'd0; e_v <= 1'b0; o_v <= 1'b0; p_v <= 1'b0; p_d <= 544'd0;
            for (i = 0; i < NP; i = i + 1) rem[i] <= 10'd0;
        end else begin
            if (tx_v) run <= 1'b1;
            if (run && !tx_v) flt <= 1'b1;
            if (tx_v || run) begin
                a_b[5119 - 512 * ph -: 512] <= tx_d;
                ph <= (ph == 4'd9) ? 4'd0 : ph + 1'b1;
            end
            // encode: the frame in E advances its LFSR one 52-symbol slice a cycle (slice = ph = 0..9 of the next frame)
            if (e_v) for (i = 0; i < NP; i = i + 1) rem[i] <= nrem[i];
            if ((tx_v || run) && ph == 4'd9) begin       // frame strobe: A -> E, E (+parity) -> O
                e_m <= {4'hA, 8'h5C, seq, a_b[5119:512], tx_d};
                seq <= seq + 1'b1;
                e_v <= 1'b1;
                for (i = 0; i < NP; i = i + 1) rem[i] <= 10'd0;
                if (e_v) begin o_c <= {e_m, par}; o_v <= 1'b1; end
            end
            // emit: one word a cycle, word index = ph (word 0 the cycle after the strobe)
            p_v <= o_v;
            p_d <= o_v ? o_c[5439 - 544 * ph -: 544] : 544'd0;
        end
    assign fault = flt;
endmodule
