`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// KV sector ECC of the Qwen3-8B ROM die (stream qwen-system, 2026-10-08; T1 F02 / coverage O3 policy proposal).
// Every HBM-resident 32-B KV sector (256 b of FP8 K or V) carries 4 x SECDED(72,64) = 32 check bits in the HBM3E
// ECC side-band (32 b a 32-B sector): no capacity or bandwidth cost, the same code and bit layout as the embedding copy
// (ot_gpu_w6_secded_pkg encode64 / decode64, emb-hbm-impl).  Encode on the write-back path, decode on the landing path:
//   enc: s_v / s_d (256)  -> one registered edge -> e_v / e_d (288 = {chk word 3 .. 0, data})
//   dec: c_v / c_d (288)  -> one registered edge -> d_v / d_d (256, single-bit errors corrected), d_ce, d_ue
// A UE never releases silently: d_ue with the beat, sticky ue_fault (the KV service's fault code / CSR source), and a
// CE counter.  MUT = 1 (bench mutant): the decoder reports but does not apply the correction.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qfd_kv_ecc #(parameter integer MUT = 0) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          s_v,
    input  wire [255:0]  s_d,
    output reg           e_v,
    output reg  [287:0]  e_d,
    input  wire          c_v,
    input  wire [287:0]  c_d,
    output reg           d_v,
    output reg  [255:0]  d_d,
    output reg           d_ce,
    output reg           d_ue,
    output reg           ue_fault,
    output reg  [31:0]   ce_count
);
    import ot_gpu_w6_secded_pkg::*;
    integer w;
    // the codeword is stored as {8 check bits = codeword positions 2^k (7) + overall parity, the 64 data bits}: the
    // data bits are the codeword's non-power-of-two positions in order, so a store permutes, never re-encodes
    function automatic [71:0] pack(input [71:0] c);           // codeword -> {chk8, data64}
        integer p, j, k; reg [63:0] d; reg [7:0] q;
        begin
            j = 0; k = 0; d = 0; q = 0;
            for (p = 1; p <= 71; p = p + 1)
                if ((p & (p - 1)) != 0) begin d[j] = c[p-1]; j = j + 1; end else begin q[k] = c[p-1]; k = k + 1; end
            q[7] = c[71];
            pack = {q, d};
        end
    endfunction
    function automatic [71:0] unpack(input [71:0] s);         // {chk8, data64} -> codeword
        integer p, j, k; reg [71:0] c;
        begin
            j = 0; k = 0; c = 0;
            for (p = 1; p <= 71; p = p + 1)
                if ((p & (p - 1)) != 0) begin c[p-1] = s[j]; j = j + 1; end else begin c[p-1] = s[64 + k]; k = k + 1; end
            c[71] = s[71];
            unpack = c;
        end
    endfunction
    reg [287:0] enc;
    reg [255:0] dd2;
    reg ce2, ue2;
    always @(*) begin
        for (w = 0; w < 4; w = w + 1) begin : g_e
            reg [71:0] pk;
            pk = pack(encode64(s_d[64*w +: 64]));
            enc[64*w +: 64] = pk[63:0];
            enc[256 + 8*w +: 8] = pk[71:64];
        end
        dd2 = 0; ce2 = 1'b0; ue2 = 1'b0;
        for (w = 0; w < 4; w = w + 1) begin : g_d
            reg [65:0] r;
            r = decode64(unpack({c_d[256 + 8*w +: 8], c_d[64*w +: 64]}));
            ce2 = ce2 | r[64];
            ue2 = ue2 | r[65];
            dd2[64*w +: 64] = (MUT != 0 && r[64]) ? c_d[64*w +: 64] : r[63:0];
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            e_v <= 1'b0; d_v <= 1'b0; d_ce <= 1'b0; d_ue <= 1'b0; ue_fault <= 1'b0; ce_count <= 0;
        end else begin
            e_v <= s_v; d_v <= c_v;
            d_ce <= c_v && ce2; d_ue <= c_v && ue2;
            if (c_v && ue2) ue_fault <= 1'b1;
            if (c_v && ce2 && !ue2) ce_count <= ce_count + 1;
        end
    end
    always @(posedge clk) begin
        if (s_v) e_d <= enc;
        if (c_v) d_d <= dd2;
    end
endmodule
