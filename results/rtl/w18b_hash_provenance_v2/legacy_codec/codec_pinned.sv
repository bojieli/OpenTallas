`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Packed-KV codec boundary of the adopted V4.1 layer die (the plug-in point
// of ot_chip_v41x_kv_prefetch.sv, interface revision 3).
//
// THE CONTRACT.  The unit is a ROW BLOCK: 32 consecutive head-dim elements of
// one KV row, as the core writes and reads them, one element per 32-bit lane
// (a BF16 value in bits 31:16, zeros below: tools/hdc_program_v41.py writes
// every KV element through to_bf16).  A row block is stored in HBM as a
// RECORD of PB bytes; records of consecutive blocks of a row, and of
// consecutive rows, are packed back to back (a record may straddle sectors).
//   encoder  v[32 x 32] -> rec[PB x 8], ok: ok = 0 when the block has no exact
//            encoding (the prefetch faults: the path is lossless or it stops);
//   decoder  rec[PB x 8] -> v[32 x 32], exactly the values the encoder took
//            (bit for bit, sign of zero included).
// Both are combinational.  Element e of the block is v[32e +: 32].
//
// IMPLEMENTATIONS (CODEC):
//   0  BF16 stand-in, PB = 64: the upper 16 bits of each lane.  Lossless for
//      BF16 lanes; ok = 0 if a lane's low half is not zero.  It is NOT the
//      model's storage format: it exercises the packed path (row grouping,
//      byte-granular records, packed staging, the unpack at the core port)
//      at half the unpacked size.
//   1  reserved: the FP8 layout (E4M3 codes + UE8M0 / E4M3 scales, the
//      spec's rows) -- owned by Codex's packed-KV agent, bit-exact against the
//      golden's quantisers; it plugs in here with its PB.
// ---------------------------------------------------------------------------
module ot_chip_v41x_kv_enc #(
    parameter integer CODEC = 0,
    parameter integer PB    = 64
) (
    input  wire [32*32-1:0] v,
    output reg  [PB*8-1:0]  rec,
    output reg              ok
);
    integer e;
    always @(*) begin
        rec = '0; ok = 1'b0;
        if (CODEC == 0) begin
            ok = 1'b1;
            for (e = 0; e < 32; e = e + 1) begin
                rec[16*e +: 16] = v[32*e + 16 +: 16];
                if (v[32*e +: 16] != 16'd0) ok = 1'b0;
            end
        end
    end
`ifndef SYNTHESIS
    initial begin
        if (CODEC == 0 && PB != 64) $fatal(1, "ot_chip_v41x_kv_enc: the BF16 stand-in record is 64 bytes");
        if (CODEC != 0) $fatal(1, "ot_chip_v41x_kv_enc: CODEC %0d not provided here", CODEC);
    end
`endif
endmodule

module ot_chip_v41x_kv_dec #(
    parameter integer CODEC = 0,
    parameter integer PB    = 64
) (
    input  wire [PB*8-1:0]  rec,
    output reg  [32*32-1:0] v
);
    integer e;
    always @(*) begin
        v = '0;
        if (CODEC == 0)
            for (e = 0; e < 32; e = e + 1) v[32*e +: 32] = {rec[16*e +: 16], 16'h0000};
    end
endmodule
