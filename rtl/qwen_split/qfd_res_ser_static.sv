`timescale 1ns/1ps
// Static (no credit, no ready) band result serialiser for the native Qwen TP8 compute join: one per band b,
// between the real slab master qfd_port_tiles_b (rq) and the static vector memory result face rb_b
// (ot_qfd_sp_vector_memory_bv STATIC_SCHEDULE=1: at most one band beat per cycle, every beat taken, `end` lands
// one burst). Successor of the credit-based qfd_sp_res_ser for the owner's static-cycle rule (2026-10-14).
//
// Input (qfd_port_tiles_b.rq packing, 4425 b): slot s = 0..7 at [552 s +: 552] = {addr[23:0], mask[15:0], data[511:0]},
//   we[7:0] = rq[4423:4416], ov = rq[4424].  Output rb (551 b) = {v, end, nul, row[19:0], mask[15:0], data[511:0]}.
//
// Fixed calendar (compiler-visible, no runtime arbitration): a burst is captured on engine edge C (me_en && ov).
// Band b's slot j is decoded at edge C + 1 + D + 8 b + j and is on the rb pins (output register) after that edge (j = 0..7): a row beat when we[j], otherwise nothing,
// except that the LAST band (b = NB-1) always emits slot 7, as a NUL beat when it holds no row, carrying `end`, so the
// memory lands exactly one burst per capture at C + D + 8 NB - 1 (+ the memory's own write stages).  Bands never
// share a cycle, so the memory's single result write never sees two beats.
// Schedule contract: captures are >= 8 NB cycles apart (the compiler spaces ME op outputs).  A closer capture, a row
// address above 20 bits, or an occupied buffer is a SCHEDULE FAULT (sticky `fault`); it never stretches the timeline.
// Storage: two burst buffers (ping-pong) of 8 x 552 b flops (a burst is read while the next is captured).
// MUT = 1 (bench): slots 0 and 1 swap their emission cycles (the bench must FAIL).
module qfd_res_ser_static #(
    parameter integer BAND = 0,
    parameter integer NB = 3,
    parameter integer D = 2,
    parameter integer MUT = 0
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire          me_en,
    input  wire [4424:0] rq,
    output reg  [550:0]  rb,
    output reg           fault
);
    localparam integer SPAN = 8 * NB;                 // cycles of one burst on the shared result face
    localparam integer T0 = D + 8 * BAND;             // first emission slot of this band after the capture edge
    localparam integer CW = $clog2(SPAN + D + 8) + 1;
    localparam LAST = (BAND == NB - 1);
    wire cap = me_en && rq[4424];
    reg  [551:0] buf_s [0:1][0:7];
    reg  [7:0]   buf_we [0:1];
    reg  [1:0]   busy;                                // buffer holds a burst not yet fully emitted
    reg          wp;                                  // next capture buffer
    reg          rp;                                  // buffer being emitted
    reg  [CW-1:0] age;                                // cycles since the oldest un-emitted capture
    reg  [CW-1:0] since;                              // edges since the last capture minus one (saturating)
    reg          pend;                                // a capture is waiting / emitting
    reg  [CW-1:0] age2;                               // age of the second (younger) capture
    integer s;
    wire [CW-1:0] slot = age - T0[CW-1:0];
    wire in_win = pend && (age >= T0) && (age < T0 + 8);
    wire [2:0] j0 = slot[2:0];
    wire [2:0] j = (MUT != 0 && j0 < 3'd2) ? {2'b00, ~j0[0]} : j0;  // MUT: slots 0/1 swapped
    wire [551:0] w = buf_s[rp][j];
    wire row_beat = in_win && buf_we[rp][j];
    wire end_beat = in_win && LAST && (j0 == 3'd7);
    wire done = pend && (age == T0 + 7);
    reg bad_addr;
    always @(*) begin
        bad_addr = 1'b0;
        for (s = 0; s < 8; s = s + 1) if (rq[4416 + s] && |rq[552 * s + 548 +: 4]) bad_addr = 1'b1;
    end
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin
            busy <= 2'b00; wp <= 1'b0; rp <= 1'b0; pend <= 1'b0; age <= 0; age2 <= 0;
            since <= {CW{1'b1}}; fault <= 1'b0; rb <= 551'd0;
        end else begin
            // emission (a register at the output pin: the beat leaves one edge after its slot decode)
            rb <= {row_beat || end_beat, end_beat, end_beat && !buf_we[rp][j],
                   (row_beat ? w[547:528] : 20'd0), (row_beat ? w[527:512] : 16'd0), (row_beat ? w[511:0] : 512'd0)};
            // ages of pending captures
            if (pend) age <= age + 1'b1;
            if (busy == 2'b11) age2 <= age2 + 1'b1;
            if (done) begin
                busy[rp] <= 1'b0; rp <= ~rp;
                if (busy == 2'b11) begin age <= age2 + 1'b1; end else pend <= 1'b0;
            end
            since <= (since == {CW{1'b1}}) ? since : since + 1'b1;
            if (cap) begin
                if (since < SPAN - 1 || busy[wp] || bad_addr) fault <= 1'b1;
                for (s = 0; s < 8; s = s + 1) buf_s[wp][s] <= rq[552 * s +: 552];
                buf_we[wp] <= rq[4423:4416];
                busy[wp] <= 1'b1; wp <= ~wp; since <= 0;
                if (!pend || done && busy != 2'b11) begin pend <= 1'b1; age <= 0; end
                else age2 <= 0;
            end
        end
    end
endmodule
