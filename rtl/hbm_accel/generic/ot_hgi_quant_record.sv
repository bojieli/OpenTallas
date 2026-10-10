`timescale 1ns/1ps
`default_nettype none
// HGI-1 quant record binding (hgi-takeover, 2026-10-09): the die's normative dispatch bus for unit 4 (FUSED.QDQ_*),
// tools/hgi_die_dispatch.py 'quant' = {n_O 21, n_A 21, desc_O 256, desc_A 256, header 128, valid} (683 bits, bit 0
// first), from ot_hgi_seq (main ef3135b44: d_hdr, effective d_desc A / O, d_n), repacked onto the qualified
// ot_hgi_quant_vm_transport command {O, C, B, A, SUT, header, valid} (C, B and SUT are not operands of QDQ: the
// transport's shape check requires opnd = {A, O} and no template).  Pure wiring plus one consistency check: the
// sequencer's effective counts must equal the effective descriptors' n; a mismatch suppresses the record and latches
// nfault (sticky until rst_n, fail-closed).  0 added edges (the die view registers the pins).
module ot_hgi_quant_record #(parameter integer MUT_NOCHECK = 0) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [682:0]  rec,
    output wire [1408:0] cmd,
    output reg           nfault
);
    wire         v  = rec[0];
    wire [127:0] h  = rec[128:1];
    wire [255:0] a  = rec[384:129];
    wire [255:0] o  = rec[640:385];
    wire [20:0]  na = rec[661:641];
    wire [20:0]  no = rec[682:662];
    wire bad = !MUT_NOCHECK && v && (na != {1'b0, a[67:48]} || no != {1'b0, o[67:48]});
    always @(posedge clk or negedge rst_n) if (!rst_n) nfault <= 1'b0; else if (bad) nfault <= 1'b1;
    assign cmd = {o, 512'd0, a, 256'd0, h, v & !bad & !nfault};
endmodule
`default_nettype wire
