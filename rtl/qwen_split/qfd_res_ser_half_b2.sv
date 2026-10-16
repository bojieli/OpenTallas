`timescale 1ns/1ps
// DIAGNOSTIC predecessor, not native961w qualification (actual production uses PAR3 train serializer).
// Four-slot b2 serializer. HB=2*band+half; exact old 24-cycle shared calendar.
// LAST is east half of final band, slot3 (global slot23). Native static fault behavior.
module qfd_res_ser_half_b2 #(
    parameter integer HB = 0,
    parameter integer NB = 3,
    parameter integer D = 2,
    parameter integer MUT = 0
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire          me_en,
    input  wire [2212:0] rq,
    output reg  [550:0]  rb,
    output reg           fault
);
    localparam integer SPAN = 8 * NB;                 // cycles of one burst on the shared result face
    localparam integer T0 = D + 4 * HB;             // first emission slot of this band after the capture edge
    localparam integer CW = $clog2(SPAN + D + 8) + 1;
    localparam LAST = (HB == 2*NB - 1);
    wire cap = me_en && rq[2212];
    reg  [551:0] buf_s [0:1][0:3];
    reg  [3:0]   buf_we [0:1];
    reg  [1:0]   busy;                                // buffer holds a burst not yet fully emitted
    reg          wp;                                  // next capture buffer
    reg          rp;                                  // buffer being emitted
    reg  [CW-1:0] age;                                // cycles since the oldest un-emitted capture
    reg  [CW-1:0] since;                              // edges since the last capture minus one (saturating)
    reg          pend;                                // a capture is waiting / emitting
    reg  [CW-1:0] age2;                               // age of the second (younger) capture
    integer s;
    wire [CW-1:0] slot = age - T0[CW-1:0];
    wire in_win = pend && (age >= T0) && (age < T0 + 4);
    wire [2:0] j0 = slot[2:0];
    wire [2:0] j = (MUT != 0 && j0 < 3'd2) ? {2'b00, ~j0[0]} : j0;  // MUT: slots 0/1 swapped
    wire [551:0] w = buf_s[rp][j];
    wire row_beat = in_win && buf_we[rp][j];
    wire end_beat = in_win && LAST && (j0 == 3'd3);
    wire done = pend && (age == T0 + 3);
    reg bad_addr;
    always @(*) begin
        bad_addr = 1'b0;
        for (s = 0; s < 4; s = s + 1) if (rq[2208 + s] && |rq[552 * s + 548 +: 4]) bad_addr = 1'b1;
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
                for (s = 0; s < 4; s = s + 1) buf_s[wp][s] <= rq[552 * s +: 552];
                buf_we[wp] <= rq[2211:2208];
                busy[wp] <= 1'b1; wp <= ~wp; since <= 0;
                if (!pend || done && busy != 2'b11) begin pend <= 1'b1; age <= 0; end
                else age2 <= 0;
            end
        end
    end
endmodule
