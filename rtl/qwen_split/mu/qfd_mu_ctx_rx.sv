`timescale 1ns/1ps
// =====================================================================================================================
// qfd_mu_ctx_rx -- compute-die receiver of the fillers' INITIAL CONTEXT from the KV die host plane (MU-KV-CTX 2026-10-19,
// coordinator 0kg; field spec results/rtl/mu_qwen_1018/kvctx/README.md section 2, posted in lanes/MU-QW-DIE.md).
// PROPOSAL for MU-QW-DIE (the compute-die owner): an observer leaf at the die top BESIDE the closed qfd_sys_face.  It reads
// existing die nets only -- the static D2D end's checked RX word (qfd_d2d_static rx_payload, the header [547:517] and the
// TAG [58:0]), prog_rx_v and prog_context_slot -- so no die port and no change of the closed face or D2D end.
//
// The transport: the token run's kind-12 CONTEXT slots come in a compiled pair (d2d_link_calendar.py --mu).  The 1st
// carries one filler's initial context (TAG epoch[1:0] = user u = 1..3) or a copy of the latency user's record; the 2nd
// is the existing user-0 context.  Both are canonical kind-12 records, so the face's own context RX accepts both and ends
// the pair on user 0's context (the face's token register sees the filler tag for one edge, before any consumer).
// This leaf: on a context slot whose record is a good kind 12 with user u, 1 <= u < NU, it emits the mu_opcal.ctx_words
// record the ctlm boot-context loader already decodes (qfd_tt_ctlm_dv OPSEG, 811e75a88):
//     ctx_x[127:112] = 16'h4D43, ctx_x[111] = 0, ctx_x[110:108] = mask = 1 << (u - 1),
//     ctx_x[36(u-1) +: 36] = {tok18 = TAG[36:19], pos18 = {5'd0, TAG[18:6]}}, other fields 0;   ctx_x[128] = load (1 edge)
// i.e. the ctlm takes c_ctx = ctx_x[127:0], c_ctxld = ctx_x[128] (one new 129-b cluster input, parameter-selected; the
// image DW5 / DW6 record stays the boot default).  User 0 records load nothing (the latency user is unchanged).
// One register edge after the slot (the face's context RX latency).  Sticky mu_fault (fail closed, never a stall):
// a slot without a word or a word without a slot, a bad structure (reserved, kind, layer, beat, header epoch != TAG epoch,
// TAG stage / segment != 0, token >= 151936), or a user >= NU.
// MUT (bench only): 1 = the record is loaded into user (u mod (NU-1)) + 1.
// =====================================================================================================================
module qfd_mu_ctx_rx #(
    parameter integer NU = 4,
    parameter integer MUT = 0
) (
    input  wire         ck,
    input  wire         rst_n,
    input  wire         context_slot,       // qfd_d2d_static prog_context_slot
    input  wire         rx_v,               // qfd_d2d_static prog_rx_v
    input  wire [30:0]  rx_hdr,             // rx_payload[547:517] = {reserved5, kind4, layer6, epoch16}
    input  wire [4:0]   rx_beat,            // rx_payload[516:512]
    input  wire [58:0]  rx_tag,             // rx_payload[58:0]
    output reg  [128:0] ctx_x,              // {load, record128}
    output reg  [1:0]   ctx_user,           // the user of the last load (observability)
    output reg          mu_fault
);
    wire [1:0]  u = rx_tag[44:43];
    wire        good = rx_hdr[30:26] == 5'd0 && rx_hdr[25:22] == 4'd12 && rx_hdr[21:16] == 6'd63 && rx_beat == 5'd0 &&
                       rx_hdr[15:0] == rx_tag[58:43] && rx_tag[42:37] == 6'd0 && rx_tag[5:0] == 6'd0 &&
                       rx_tag[36:19] < 18'd151936;
    wire [1:0]  ul = (MUT == 1) ? ((u == 2'(NU - 1)) ? 2'd1 : u + 2'd1) : u;
    reg  [127:0] r;
    always @(*) begin
        r = 128'd0;
        r[127:112] = 16'h4D43;
        r[108 + ul - 1] = 1'b1;
        r[36 * (ul - 1) + 18 +: 18] = rx_tag[36:19];
        r[36 * (ul - 1) +: 18] = {5'd0, rx_tag[18:6]};
    end
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin ctx_x <= 129'd0; ctx_user <= 2'd0; mu_fault <= 1'b0; end
        else begin
            ctx_x[128] <= 1'b0;
            if (rx_v !== context_slot && context_slot) mu_fault <= 1'b1;
            if (context_slot && rx_v) begin
                if (!good || {1'b0, u} >= 3'(NU)) mu_fault <= 1'b1;
                else if (u != 2'd0) begin ctx_x <= {1'b1, r}; ctx_user <= ul; end
            end
        end
    end
endmodule
