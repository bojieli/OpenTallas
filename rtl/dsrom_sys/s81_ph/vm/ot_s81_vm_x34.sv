`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------
// ot_s81_vm_x34 (claude S81 VM owner r8, 2026-10-14): FIXED-PHASE serial (0.9 GHz) -> stream (1.2 GHz) word transfer
// on the common 3:4 epoch (3 serial = 4 stream cycles = 3.333 ns, both clocks from one source; the owner's static rule:
// no handshake, no FIFO pointers, no credit, no ready).  Every serial cycle's word {v, d} is written into bank
// k = serial phase (0..2); the stream side reads bank 0 / 1 / 2 at fixed stream edges 2 / 3 / 4 (= 0 of the next epoch)
// of the epoch the word was written in.  Launch -> capture is >= 1.111 ns on every bank and the word stays in its
// bank for 3.333 ns (written once per epoch), so every arc is a full-period related-clock transfer (no synchroniser:
// phase-locked clocks; STA owns the arcs with the epoch multicycle).  Stream edge 1 of every epoch carries no word.
// Latency (fixed): serial word sampled at serial edge k of epoch n -> o_v/o_d registered at stream edge 2 + k of n.
// STARTUP CONTRACT: both resets are released so that the first rising edges after release are the epoch's serial edge
// 0 and stream edge 0 (the common-epoch divider, aa670a062 family).  ALIGNMENT ASSERTION: every bank entry carries the
// serial epoch parity; the stream side compares it with its own epoch parity on every read after one warm-up epoch;
// a slipped epoch -> sticky fault; PHASE ASSERTION: a serial phase marker (high in serial cycle 1 only) must be
// sampled high by stream edge 2 and low by stream edges 0 / 1 / 3: any sub-epoch misalignment -> sticky fault
// (never a re-timed transfer).
// ---------------------------------------------------------------------------------------------------------------
// PHYSICAL SPLIT (claude S81 VM F2 2026-10-15): the serial bank writer ot_s81_vm_x34_s and the stream reader
// ot_s81_vm_x34_t are separate hard leaves, one per clock root (ABI categories ck_*_x34_s / ck_*_x34_t); the flow's
// multiple_cts_roots leaf admits only same-frequency roots, and the 3:4 related arcs (bank / parity / marker flops ->
// stream capture, >= 1.111 ns by construction) are parent-level related-clock paths.  ot_s81_vm_x34 is the wrapper
// of the two: the same flops, the same logic, bit-identical behaviour (tb_ot_s81_vm_x34 unchanged).
module ot_s81_vm_x34 #(parameter integer W = 512) (
    input  wire         s_ck, s_rst_n,
    input  wire         s_v, input wire [W-1:0] s_d,
    input  wire         t_ck, t_rst_n,
    output wire         o_v, output wire [W-1:0] o_d,
    output wire         fault
);
    wire [W:0] b0, b1, b2; wire [2:0] bp; wire mark;
    ot_s81_vm_x34_s #(.W(W)) u_s (.s_ck(s_ck), .s_rst_n(s_rst_n), .s_v(s_v), .s_d(s_d), .b0(b0), .b1(b1), .b2(b2),
        .bpar(bp), .s_mark(mark));
    ot_s81_vm_x34_t #(.W(W)) u_t (.t_ck(t_ck), .t_rst_n(t_rst_n), .b0(b0), .b1(b1), .b2(b2), .bpar(bp), .s_mark(mark),
        .o_v(o_v), .o_d(o_d), .fault(fault));
endmodule

// serial side: phase counter, epoch parity, phase marker and the three banks (every output a flop)
module ot_s81_vm_x34_s #(parameter integer W = 512) (
    input  wire         s_ck, s_rst_n,
    input  wire         s_v, input wire [W-1:0] s_d,
    output reg  [W:0]   b0, b1, b2,
    output reg  [2:0]   bpar,
    output reg          s_mark
);
    reg [1:0] sp; reg se;               // phase of the cycle that FOLLOWS the last edge; epoch parity
    always @(posedge s_ck or negedge s_rst_n)
        if (!s_rst_n) begin sp <= 2'd2; se <= 1'b0; bpar <= 3'b000; s_mark <= 1'b0; end   // first edge after release = epoch edge 0
        else begin
            s_mark <= sp == 2'd0;           // set by serial edge 1, cleared by serial edge 2
            // the edge that ends cycle sp writes bank (sp + 1) mod 3 (edge 0 of the epoch writes bank 0)
            case (sp)
                2'd2: begin bpar[0] <= ~se; end
                2'd0: begin bpar[1] <= se; end
                default: begin bpar[2] <= se; end
            endcase
            if (sp == 2'd2) begin sp <= 2'd0; se <= ~se; end else sp <= sp + 2'd1;
        end
    // data banks (no reset: the parity and v bit gate their use)
    always @(posedge s_ck) begin
        case (sp)
            2'd2: b0 <= {s_v, s_d};
`ifdef OT_VM_X34_MUT_SBANK
            2'd0: b2 <= {s_v, s_d};         // MUTANT: serial phase-1 word written into bank 2
`else
            2'd0: b1 <= {s_v, s_d};
`endif
            default: b2 <= {s_v, s_d};
        endcase
    end
endmodule

// stream side: fixed-edge bank reads, epoch-parity and phase-marker assertions
module ot_s81_vm_x34_t #(parameter integer W = 512) (
    input  wire         t_ck, t_rst_n,
    input  wire [W:0]   b0, b1, b2,
    input  wire [2:0]   bpar,
    input  wire         s_mark,
    output reg          o_v, output reg [W-1:0] o_d,
    output reg          fault
);
    reg [1:0] tp; reg te; reg warm; reg mk;    // tp = index of the last stream edge (3 at reset: the next edge is epoch edge 0)
    always @(posedge t_ck or negedge t_rst_n)
        if (!t_rst_n) begin tp <= 2'd3; te <= 1'b0; warm <= 1'b0; o_v <= 1'b0; fault <= 1'b0; mk <= 1'b0; end
        else begin
            tp <= tp + 2'd1;
            // PHASE ASSERTION: the marker is sampled high by stream edge 2 only (0.557 ns after serial edge 1), low by
            // edges 0 / 1 / 3; mk holds the previous edge's sample, so after edge 2 (tp == 2) mk must be 1, else 0
            mk <= s_mark;
            if (warm && mk != (tp == 2'd2)) fault <= 1'b1;
            if (tp == 2'd3) begin te <= ~te; warm <= 1'b1; end
            case (tp)
`ifdef OT_VM_X34_MUT_PHASE
                2'd0: begin o_v <= b0[W]; if (warm && bpar[0] != te) fault <= 1'b1; end     // MUTANT: one stream edge early
`else
                2'd1: begin o_v <= b0[W]; if (warm && bpar[0] != te) fault <= 1'b1; end
`endif
                2'd2: begin o_v <= b1[W]; if (warm && bpar[1] != te) fault <= 1'b1; end
                2'd3: begin o_v <= b2[W]; if (warm && bpar[2] != te) fault <= 1'b1; end
                default: o_v <= 1'b0;
            endcase
        end
    always @(posedge t_ck)
        case (tp)
`ifdef OT_VM_X34_MUT_PHASE
            2'd0: o_d <= b0[W-1:0];
`else
            2'd1: o_d <= b0[W-1:0];
`endif
            2'd2: o_d <= b1[W-1:0];
            2'd3: o_d <= b2[W-1:0];
            default: ;
        endcase
endmodule
`default_nettype wire
