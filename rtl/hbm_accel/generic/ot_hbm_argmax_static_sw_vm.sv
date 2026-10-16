`timescale 1ns/1ps
`default_nettype none
// H-NETLIST/attn 2026-10-16: the v16 die's ARGMAX.LOCAL master = ot_hbm_argmax_static (SW slice, SID 0) WITHOUT the
// STREAM input (G-CIL-AMSTREAM / G-SU-MTP-LOGIT closed by architecture, not by a tie at the die):
//   The only STREAM into ARGMAX on the static die would be STREAM 2 (SM LM head -> ARGMAX, ds_native fuse) or 1 (SU
//   reduce -> ARGMAX).  The engine's local index is the stream position, so the stream must arrive in ascending row
//   order, while the 32 SMs (4 quadrants, ~42 head rows each) emit their rows concurrently on fixed slots: a static
//   adapter needs a reorder store of the whole head output -- the VM.  The SM results write VM directly (decision
//   23:21), and mode 0 reads the logits one sector (8 FP32) an edge: +~190 edges an ARGMAX.LOCAL against the stream
//   form, 11 per MTP step = ~2.1k cycles of a 1.4-2.5M-cycle step (<0.15 %, H-MTP2 2026-10-16 agreed), below the
//   1 % adoption bar of a lever.  So this die wires NO stream id into ARGMAX (HGI-1 6.4: the stream ids a die
//   supports are fixed by its wiring; a descriptor naming an unwired consumer faults).
// Specialisation (compile-time, like the SW SID): STREAM pins absent; the engine's stream-side inputs are constant
// because no wiring exists; a mode-1 (STREAM) record reaches the engine as an ILLEGAL record (imm_a = 2^18-1 fails the
// engine's own legality check), so it faults on the engine's normal E_CHK edge and never waits for a beat.  Every
// output is the unchanged engine's flop; mode-0 behaviour is identical edge for edge (bench: equivalence vs
// ot_hbm_argmax_static_sw on random VM traffic).  MUT (bench): 1 pass mode through (a STREAM record hangs busy); 2 illegal imm_a on every record.
module ot_hbm_argmax_static_sw_vm #(
    parameter integer MUT = 0,
    parameter integer ACK = 12,
    parameter integer ELAT = 14,
    parameter integer EMUT = 0       // engine mutant pass-through (ot_hbm_argmax_static MUT)
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [7:0]    die_id,
    input  wire          go,
    input  wire          mode,            // 0 VM; 1 STREAM = unwired on this die -> record fault
    input  wire [17:0]   imm_a,
    input  wire          a_mirror,
    input  wire [17:0]   a_base,
    input  wire [17:0]   n,
    input  wire [17:0]   o_base,
    input  wire [15:0]   o_is,
    output wire  [135:0] vm_rq,
    input  wire [2055:0] vm_rr,
    output wire  [337:0] cq,
    output wire  [1:0]   cq_seq,
    input  wire [273:0]  cr,
    output wire          busy, done, fault, nan_flag
);
    localparam [1:0] SID = 2'd0;
    wire stream_rec = (MUT == 1) ? 1'b0 : (MUT == 2) ? 1'b1 : mode;
    ot_hbm_argmax_static #(.MUT(EMUT), .ACK(ACK), .ELAT(ELAT)) implementation(.clk(clk), .rst_n(rst_n), .sid(SID),
        .die_id(die_id), .go(go), .mode((MUT == 1) ? mode : 1'b0), .imm_a(stream_rec ? 18'h3FFFF : imm_a),
        .a_mirror(a_mirror), .a_base(a_base), .n(n), .o_base(o_base), .o_is(o_is), .vm_rq(vm_rq), .vm_rr(vm_rr),
        .am_stream(523'd0), .cq(cq), .cq_seq(cq_seq), .cr(cr), .busy(busy), .done(done), .fault(fault),
        .nan_flag(nan_flag));
endmodule
`default_nettype wire
