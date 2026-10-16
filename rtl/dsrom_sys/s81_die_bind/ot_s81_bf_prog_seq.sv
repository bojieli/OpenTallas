`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_bf_prog_seq (S-BIND 2026-10-15): the per-pair producer of the static BF programme f_prog[37:0] that
// dsfd_bf_front_static (ot_s81_bf_front STATIC_PROGRAM 1) consumes.  Owner rule 2026-10-14T18:59: the compiler fixes
// every BF issue edge; this block replays the compiled calendar, it never looks at data availability, readiness or
// credits.  The front checks every programmed word against its walker (programme_fault), so a wrong calendar is
// detected, never absorbed.
//
// Measured structure (results/rtl/s81_bf_programme_1015, real exact BF bench, 13 phases / 4,288 issues): within a
// phase the compiled programme is affine / modular in the issue index i, so ONE descriptor per phase regenerates it:
//   issue edge  = go + OFF + PER * (i >> LB) + (i & (B-1)) + DELTA          (B = 1 << LB issues a burst)
//   addr        = BASE + (i & AMASK)                                         (pp address walker, wraps at AMASK + 1)
//   operand     = {FAM, (i >> (LB + LU)) [5:0], (i >> LB) & UMASK}           ({family, position:block, unit})
//   segment     = (i >> SSH) & SMASK ;  half = i & (B-1) ;  chain = i & CMASK
// Descriptor d[DW-1:0] (DW = 82), held stable from before go until the phase ends:
//   [13:0] N issues   [14] LB   [22:15] OFF   [30:23] PER   [44:31] BASE   [58:45] AMASK   [59] FAM
//   [61:60] LU-3 (U = 8 << ...)  [65:62] UMASK-less: unused 0  [68:66] SSH   [71:69] SMASK   [75:72] CMASK   [81:76] 0
// (fields beyond the measured set are explicit zeros; tools/s81/bf_programme_compile.py writes and checks them.)
// DELTA (parameter, signed edges) = the go-pin -> core-go age minus the f_prog pin -> core-consume age of the front.
// go: the pair's go pin (the same net the front's go takes); a phase starts on its rising edge.  A go while a programme still runs is a sticky fault
// (observation only; the calendar never changes).  N = 0: the phase issues nothing.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_bf_prog_seq #(
    parameter integer DW = 82,
    parameter integer DELTA = 0
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire          go,
    input  wire [DW-1:0] desc,
    output reg  [37:0]   f_prog,
    output reg           fault
);
    // the phase descriptor is captured at the phase start: the source (cfg loader / table) may advance to the next phase
    // while this one runs
    reg  [DW-1:0] dq;
    wire [13:0] d_n    = dq[13:0];
    wire        d_lb   = dq[14];
    wire [7:0]  d_off  = dq[22:15];
    wire [7:0]  d_per  = dq[30:23];
    wire [13:0] d_base = dq[44:31];
    wire [13:0] d_am   = dq[58:45];
    wire        d_fam  = dq[59];
    wire [1:0]  d_lu   = dq[61:60];          // U = 8 << d_lu
    wire [2:0]  d_ssh  = dq[68:66];
    wire [2:0]  d_sm   = dq[71:69];
    wire [3:0]  d_cm   = dq[75:72];
    reg         run, go_q;
    reg  [13:0] i;
    // a phase starts on the go pin's rising edge (a go level held over several edges is one phase start)
    wire        start = go && !go_q;
    reg  [15:0] t, next_t;
    wire [13:0] ib = d_lb ? (i >> 1) : i;                 // burst index
    wire [4:0]  lsh = 5'd3 + {3'd0, d_lu} + {4'd0, d_lb};  // LB + LU
    wire [13:0] blk = i >> lsh;
    wire [7:0]  umask = (8'd8 << d_lu) - 8'd1;
`ifdef OT_S81_BF_PROG_MUT_ADDR
    wire [13:0] addr = d_base + (i & d_am) + 14'd1;       // negative control: programme one address ahead
`else
    wire [13:0] addr = d_base + (i & d_am);
`endif
    wire [37:0] word = {i[3:0] & d_cm,                                   // chain   [37:34]
                        d_lb & i[0],                                     // half    [33]
                        3'((i >> d_ssh) & {11'd0, d_sm}),                // segment [32:30]
                        d_fam, blk[5:0], ib[7:0] & umask,                // operand [29:15]
                        addr,                                            // address [14:1]
                        1'b1};                                           // issue   [0]
    // first issue edge, measured from the go edge (t = 0 on the edge after go)
    wire signed [17:0] first_e = $signed({2'b0, 8'd0, desc[22:15]}) + DELTA - 1;   // at the start edge: the new phase's
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin run <= 1'b0; go_q <= 1'b0; i <= 14'd0; t <= 16'd0; next_t <= 16'd0; f_prog <= 38'd0; fault <= 1'b0; end
        else begin
            f_prog <= 38'd0;
            go_q <= go;
            if (start) begin
                if (run) fault <= 1'b1;
                dq <= desc;
                run <= desc[13:0] != 14'd0; i <= 14'd0; t <= 16'd0; next_t <= first_e[15:0];
                if (first_e < 0) fault <= 1'b1;                  // DELTA larger than the compiled offset: not realisable
            end else if (run) begin
                t <= t + 16'd1;
                if (t == next_t) begin
                    f_prog <= word;
                    i <= i + 14'd1;
                    next_t <= (d_lb && !i[0]) ? next_t + 16'd1 : next_t + {8'd0, d_per} - {15'd0, d_lb};
                    if (i + 14'd1 == d_n) run <= 1'b0;
                end
            end
        end
endmodule
`default_nettype wire
