`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// dsfd_capt_status_x43_t / dsfd_capt_status_x43_s (S-VM-CAPT-STATUS, 2026-10-16): the capture status word (64 b,
// latest-value semantics) from the stream domain (ck, 1.2 GHz) to the serial domain (ckv, 0.9 GHz) as a FIXED-PHASE
// 3-bank transfer on the common 3:4 epoch (coordinator DECISION B; successor of the intra-leaf ot_ratio_cdc_fifo of
// dsfd_capt_status_dual, which failed FF hold -81 ps: its 1-VCO-tick 4:3 arcs could not meet the die-skew reserve,
// hold 100 / setup 150, inside one 256.67 ps tick).  Pattern of ot_s81_vm_x43 (rtl/dsrom_sys/s81_ph/vm), split per
// clock root like the VM's CLOSED x43 leaves: _t is a single-clock leaf on ck, _s a single-clock leaf on ckv; the
// bank / parity / marker arcs between them are parent-level related-clock paths.  No handshake, pointer, credit or
// ready: every word moves at a fixed edge.
//
// EPOCH: 4 stream edges = 3 serial edges = 12 VCO ticks (stream edge n at tick 3n, serial edge j at tick 4j; edge 0
// of both coincides).  STARTUP CONTRACT (as x34 / x43): rst (stream) and rsv (serial) are the die's epoch resets,
// active low, asserted asynchronously, released so that the first rising edge of each clock after release is epoch
// edge 0.  A slip is detected (below), never re-timed.
//
// SAMPLE RULE (stream sample index n of f_sn at a ck edge):
//     n = 0 of epoch E -> bank b0 -> t_st from serial edge 2 of epoch E      (tick 0 -> 8 : 8 ticks)
//     n = 2 of epoch E -> bank b2 -> t_st from serial edge 0 of epoch E + 1  (tick 6 -> 12: 6 ticks)
//     n = 3 of epoch E -> bank b3 -> t_st from serial edge 1 of epoch E + 1  (tick 9 -> 16: 7 ticks)
//     n = 1            -> not sampled (the status word is a level: the n = 2 sample supersedes it one cycle later)
// FIXED LATENCY: f_sn at stream edge n is on t_st after 2 stream cycles (n = 2), 2 1/3 (n = 3), 2 2/3 (n = 0),
// i.e. t_st after serial edge j shows f_sn as sampled 6 / 7 / 8 VCO ticks earlier for j = 0 / 1 / 2 (1.50 / 1.75 /
// 2.00 serial cycles).  Every serial edge loads a new word (3 words per epoch).
//
// TIMING WINDOWS (why this closes where the FIFO did not): _t launches cross-domain flops ONLY at stream indices 0,
// 2, 3 (ticks 0, 6, 9).  The nearest serial capture after each launch is 4 / 2 / 3 ticks later (setup >= 513 ps at
// the 770 ps route period) and the capture at or before it is 0 / 2 / 1 ticks earlier (hold: the coincident edge
// with a 4-tick setup window behind it, so hold padding is free).  No arc has the 1-tick setup window.  Differences
// from ot_s81_vm_x43: the phase marker is high in stream cycle 2 (x43: cycle 1, a 1-tick arc) and is checked at
// serial edge 2; there is no valid bit / sample-index-1 schedule check (the status lane is continuous).
// Read hold by construction: a bank is rewritten >= 1 tick + one full epoch after its fixed read (b0 read tick 8,
// rewritten tick 12; b2 read 12, rewritten 18; b3 read 16, rewritten 21).
//
// ALIGNMENT ASSERTIONS (as x43): each bank carries the stream epoch parity (bpar), checked against the serial epoch
// parity at its read; the marker must be sampled high by serial edge 2 only.  A slip sets a sticky fault that is
// OR-ed into status bit 3 (the capture fault bit: cfault | proto_fault | g_fault), which t_cd[10] carries to the
// field sequencer.  With aligned resets it never fires, so t_st[3] is unchanged.
// PIN REGISTERS (S leaf): every input (b0 / b2 / b3 / bpar) is captured unconditionally at EVERY serial edge into its
// own flop (sh0 / sh2 / sh3 / bq), and the fixed-edge select works on those flops.  Zero added latency: each bank's
// first serial edge strictly after its write (b0: tick 4, b2: 8, b3: 12) precedes its fixed read edge (8 / 12 / 16),
// and the next write (12 / 18 / 21) follows it.  The cross-root arcs stay pin -> flop (setup >= 2 ticks).
// Reset: stq holds 0 until the first written bank is read (serial edge 2 of the first epoch).
// S LEAF RESET STAGE (S-VM-CAPT-X43RST, 2026-10-16; native audit 1316: capture rsv[0] 218.0 ps > 190 when rsv was
// the raw async reset of ~70 flops): rsv drives only the 2-flop local stage rv (async assert, synchronous release,
// as dsfd_capt_x8x_s's rv_s); rv1 resets the leaf state.  rv1 rises after serial edge 1, so the state's first
// active edge is epoch edge 2 -- the reset values are those the rsv-direct leaf held AFTER edge 1 (sp = 1, se = 1,
// warm = 1, flt = 0, stq = 0; warm is then constant 1 and removed) and mk (the t_mark pin register) has no reset, so
// at edge 2 it holds the edge-1 sample exactly as before.  t_st is therefore identical to the rsv-direct leaf at
// every time for every rsv timing (tb_dsfd_capt_status_x43_eq compares the two under random releases / re-resets):
// ZERO added serial edges, startup contract unchanged.
// Mutants: S81PH_CAPS_MUT_STATUS (t_st[3] inverted, the externally consumed fault bit, as the old leaf);
//          DSFD_CAPT_STX43_MUT_PHASE (the n = 3 bank is read at serial edge 0, with the n = 2 bank's slot);
//          DSFD_CAPT_STX43_MUT_RVPH (the rsv-direct reset values sp = 2 / se = 0 under the 2-flop stage: phase
//          off by the stage delay).
// ---------------------------------------------------------------------------------------------------------------
module dsfd_capt_status_x43_t (
    input  wire [0:0]  ck,
    input  wire [0:0]  rst,                // stream epoch reset (active low; released on epoch edge 0)
    input  wire [63:0] f_sn,
    output reg  [63:0] b0, b2, b3,
    output reg  [2:0]  bpar,
    output reg         t_mark
);
    // tp = index of the last stream edge (3 at reset: the next edge is epoch edge 0)
    reg [1:0] tp; reg te;
    wire [1:0] tn = tp + 2'd1;             // sample index of THIS edge
    always @(posedge ck[0] or negedge rst[0])
        if (!rst[0]) begin tp <= 2'd3; te <= 1'b0; bpar <= 3'b000; t_mark <= 1'b0; end
        else begin
            tp <= tn;
            t_mark <= tn == 2'd2;          // high from stream edge 2 (tick 6) to stream edge 3 (tick 9)
            case (tn)
                2'd0: begin te <= ~te; bpar[0] <= ~te; end
                2'd2: bpar[1] <= te;
                2'd3: bpar[2] <= te;
                default: ;
            endcase
        end
    always @(posedge ck[0])
        case (tn)
            2'd0: b0 <= f_sn;
            2'd2: b2 <= f_sn;
            2'd3: b3 <= f_sn;
            default: ;
        endcase
endmodule

module dsfd_capt_status_x43_s (
    input  wire [0:0]  ckv,
    input  wire [0:0]  rsv,                // serial epoch reset (active low; released on epoch edge 0)
    input  wire [63:0] b0, b2, b3,
    input  wire [2:0]  bpar,
    input  wire        t_mark,
    output wire [63:0] t_st
);
    // local reset stage: rsv (the die's epoch reset) drives only these 2 flops; rv1 resets the leaf state, whose
    // first active edge is therefore epoch edge 2 (rsv released before epoch edge 0, rv0 rises at edge 0, rv1 at 1)
    (* keep *) reg rv0, rv1;
    always @(posedge ckv[0] or negedge rsv[0]) if (!rsv[0]) begin rv0 <= 1'b0; rv1 <= 1'b0; end else begin rv0 <= 1'b1; rv1 <= rv0; end
    // sp = index of the last serial edge (1 under reset: the state's first edge is epoch edge 2).  Reset values = the
    // state the rsv-direct leaf held after epoch edge 1 (sp 1, se toggled at edge 0, warm set at edge 1, no check yet)
    reg [1:0] sp; reg se; reg mk; reg flt;
    reg [63:0] stq;
    reg [63:0] sh0, sh2, sh3; reg [2:0] bq;               // input pin registers, loaded at every serial edge
    // mk = t_mark pin register (no reset: at the state's first edge it holds the edge-1 sample, as before)
    always @(posedge ckv[0]) begin sh0 <= b0; sh2 <= b2; sh3 <= b3; bq <= bpar; mk <= t_mark; end
    wire [1:0] sn = (sp == 2'd2) ? 2'd0 : sp + 2'd1;   // serial edge index of THIS edge
    always @(posedge ckv[0] or negedge rv1)
`ifdef DSFD_CAPT_STX43_MUT_RVPH
        if (!rv1) begin sp <= 2'd2; se <= 1'b0; flt <= 1'b0; end
`else
        if (!rv1) begin sp <= 2'd1; se <= 1'b1; flt <= 1'b0; end
`endif
        else begin
            sp <= sn;
            // PHASE ASSERTION: t_mark sampled at serial edge 2 (tick 8) is high, at edges 0 / 1 low.  mk holds the
            // previous edge's sample: at serial edge 0 it must be 1, else 0.
            if (mk != (sn == 2'd0)) flt <= 1'b1;
            case (sn)
                2'd0: begin se <= ~se; if (bq[1] != se) flt <= 1'b1; end
                2'd1: if (bq[2] != ~se) flt <= 1'b1;
                default: if (bq[0] != se) flt <= 1'b1;
            endcase
        end
    // the bank read at this edge (fixed by sn); bit 3 also carries the sticky alignment fault
    reg [63:0] rd;
    always @(*)
        case (sn)
`ifdef DSFD_CAPT_STX43_MUT_PHASE
            2'd0: rd = sh3;
            2'd1: rd = sh2;
`else
            2'd0: rd = sh2;
            2'd1: rd = sh3;
`endif
            default: rd = sh0;
        endcase
    always @(posedge ckv[0] or negedge rv1)
        if (!rv1) stq <= 64'd0;
        else stq <= {rd[63:4], rd[3] | flt, rd[2:0]};
`ifdef S81PH_CAPS_MUT_STATUS
    assign t_st = stq ^ 64'd8; // deliberately corrupt the externally consumed fault bit
`else
    assign t_st = stq;
`endif
endmodule
