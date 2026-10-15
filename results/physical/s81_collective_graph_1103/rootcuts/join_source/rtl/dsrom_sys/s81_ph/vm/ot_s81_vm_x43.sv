`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------
// ot_s81_vm_x43 (claude S81 VM owner r9, 2026-10-14): FIXED-PHASE stream (1.2 GHz) -> serial (0.9 GHz) word transfer
// on the common 3:4 epoch (4 stream = 3 serial cycles = 3.333 ns, both clocks from one source).  The mirror of
// ot_s81_vm_x34 (owner static rule 2026-10-14T18:59: no handshake, FIFO pointers, credit or ready).
// SAMPLE INDEX n = index (0..3) of the stream edge at which this block samples s_v / s_d (edge 0 of an epoch coincides
// with serial edge 0).  Words are accepted at n = 0, 2, 3; a valid word at n = 1 is a SCHEDULE FAULT (never delayed:
// the compiler places serial-bound words off sample index 1; the VM services that feed this block only ever produce
// words on n = 0 / 2 / 3, see dsfd_vm_static_core / _wfc).  Each accepted word is written into its own bank and read by
// the serial side at a FIXED serial edge:
//     n = 2 of epoch E  ->  serial edge 0 of epoch E+1     (launch 1.667 ns, capture 3.333 ns: 1.667 ns)
//     n = 3 of epoch E  ->  serial edge 1 of epoch E+1     (2.500 -> 4.444: 1.944 ns)
//     n = 0 of epoch E  ->  serial edge 2 of epoch E       (0.000 -> 2.222: 2.222 ns)
// Every bank is written once an epoch and read before its next write: full related-clock arcs (STA owns them with
// the epoch multicycle, as x34).  Output o_v / o_d is registered at that serial edge.
// STARTUP CONTRACT (as x34): both resets released so that the first rising edges after release are epoch edge 0 of
// both clocks.  ALIGNMENT ASSERTIONS: every bank carries the stream epoch parity, checked against the serial epoch
// parity on every read after one warm-up epoch; a stream phase marker (high in stream cycle 1 = [0.833, 1.667) ns)
// must be sampled high by serial edge 1 only.  Any slip -> sticky fault (never a re-timed transfer).
// Mutant OT_VM_X43_MUT_PHASE: the n = 3 bank is read one serial edge early (serial edge 0, with the n = 2 bank's slot).
// ---------------------------------------------------------------------------------------------------------------
// SPLIT PER CLOCK ROOT (claude S81 VM F4 cdc-leaves, 2026-10-15; same pattern as ot_s81_vm_x34): ot_s81_vm_x43_t (stream
// side: sample index, parity, marker, index-1 schedule check and the three banks, every output a flop) and
// ot_s81_vm_x43_s (serial side: fixed-edge bank reads, parity / marker assertions) are separate hard leaves, one per
// clock root (ABI categories ck_*_x43_t / ck_*_x43_s).  The 3:4 related arcs (bank / parity / marker / ph1_bad flops ->
// serial capture) are parent-level related-clock paths.  ot_s81_vm_x43 is the wrapper of the two: the same flops, the
// same logic, bit-identical behaviour (tb_ot_s81_vm_x43 unchanged).
module ot_s81_vm_x43 #(parameter integer W = 512) (
    input  wire         t_ck, t_rst_n,
    input  wire         s_v, input wire [W-1:0] s_d,
    input  wire         s_ck, s_rst_n,
    output wire         o_v, output wire [W-1:0] o_d,
    output wire         fault
);
    wire [W:0] b0, b2, b3; wire [2:0] bp; wire mark, p1;
    ot_s81_vm_x43_t #(.W(W)) u_t (.t_ck(t_ck), .t_rst_n(t_rst_n), .s_v(s_v), .s_d(s_d), .b0(b0), .b2(b2), .b3(b3),
        .bpar(bp), .t_mark(mark), .ph1_bad(p1));
    ot_s81_vm_x43_s #(.W(W)) u_s (.s_ck(s_ck), .s_rst_n(s_rst_n), .b0(b0), .b2(b2), .b3(b3), .bpar(bp), .t_mark(mark),
        .ph1_bad(p1), .o_v(o_v), .o_d(o_d), .fault(fault));
endmodule

// stream side: sample index, epoch parity, phase marker, index-1 schedule check and the three banks (every output a flop)
module ot_s81_vm_x43_t #(parameter integer W = 512) (
    input  wire         t_ck, t_rst_n,
    input  wire         s_v, input wire [W-1:0] s_d,
    output reg  [W:0]   b0, b2, b3,
    output reg  [2:0]   bpar,
    output reg          t_mark,
    output reg          ph1_bad
);
    // tp = index of the last stream edge (3 at reset: the next edge is epoch edge 0)
    reg [1:0] tp; reg te;                       // te = parity of the epoch whose edge 0 was the latest
    wire [1:0] tn = tp + 2'd1;                  // sample index of THIS edge
    always @(posedge t_ck or negedge t_rst_n)
        if (!t_rst_n) begin tp <= 2'd3; te <= 1'b0; bpar <= 3'b000; t_mark <= 1'b0; ph1_bad <= 1'b0; end
        else begin
            tp <= tn;
            t_mark <= tn == 2'd1;               // high from stream edge 1 to stream edge 2
            case (tn)
                2'd0: begin te <= ~te; bpar[0] <= ~te; end
                2'd2: bpar[1] <= te;
                2'd3: bpar[2] <= te;
                default: if (s_v) ph1_bad <= 1'b1;
            endcase
        end
    always @(posedge t_ck)
        case (tn)
            2'd0: b0 <= {s_v, s_d};
            2'd2: b2 <= {s_v, s_d};
            2'd3: b3 <= {s_v, s_d};
            default: ;
        endcase
endmodule

// serial side: fixed-edge bank reads, epoch-parity and phase-marker assertions, index-1 schedule fault
module ot_s81_vm_x43_s #(parameter integer W = 512) (
    input  wire         s_ck, s_rst_n,
    input  wire [W:0]   b0, b2, b3,
    input  wire [2:0]   bpar,
    input  wire         t_mark,
    input  wire         ph1_bad,
    output reg          o_v, output reg [W-1:0] o_d,
    output reg          fault
);
    // sp = phase index of the last serial edge (2 at reset: the next edge is epoch edge 0)
    reg [1:0] sp; reg se; reg warm; reg mk;
    wire [1:0] sn = (sp == 2'd2) ? 2'd0 : sp + 2'd1;   // serial edge index of THIS edge
    always @(posedge s_ck or negedge s_rst_n)
        if (!s_rst_n) begin sp <= 2'd2; se <= 1'b0; warm <= 1'b0; o_v <= 1'b0; fault <= 1'b0; mk <= 1'b0; end
        else begin
            sp <= sn;
            mk <= t_mark;
            // PHASE ASSERTION: t_mark sampled at serial edge 1 (1.111 ns) is high; at edges 0 / 2 low.  mk holds the
            // previous edge's sample: after serial edge 1 (sn == 2 now) mk must be 1, else 0.
            if (warm && mk != (sn == 2'd2)) fault <= 1'b1;
            if (ph1_bad) fault <= 1'b1;
            case (sn)
`ifdef OT_VM_X43_MUT_PHASE
                2'd0: begin se <= ~se; o_v <= b3[W]; if (warm && bpar[2] != se) fault <= 1'b1; end
                2'd1: begin warm <= 1'b1; o_v <= b2[W]; end
`else
                2'd0: begin se <= ~se; o_v <= b2[W]; if (warm && bpar[1] != se) fault <= 1'b1; end
                2'd1: begin warm <= 1'b1; o_v <= b3[W]; if (warm && bpar[2] != ~se) fault <= 1'b1; end
`endif
                default: begin o_v <= b0[W]; if (warm && bpar[0] != se) fault <= 1'b1; end
            endcase
        end
    always @(posedge s_ck)
        case (sn)
`ifdef OT_VM_X43_MUT_PHASE
            2'd0: o_d <= b3[W-1:0];
            2'd1: o_d <= b2[W-1:0];
`else
            2'd0: o_d <= b2[W-1:0];
            2'd1: o_d <= b3[W-1:0];
`endif
            default: o_d <= b0[W-1:0];
        endcase
endmodule
`default_nettype wire
