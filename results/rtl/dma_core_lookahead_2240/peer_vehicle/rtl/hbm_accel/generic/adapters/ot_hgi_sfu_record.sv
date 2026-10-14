`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HGI-1 SFU record adapter (hgi-adapters, 2026-10-09).  Unit 3 (SFU.GLU, the fused SwiGLU chain) onto the SFU quarter's
// stream-unit op port (the vec op word of ot_hdc_v41x_vec; hfd_sfu = ot_su12_sfu lanes of the same vec family).
// Decode + handshake only: SFU.GLU is ONE vec op; this is ot_hgi_su_record with GLU = 1 (the record is decoded straight
// into that op: same pin flops, issue, ordering, retire, fault logic and legacy pass-through):
//   golden (spec 6.7, hgi_sim u_glu): g' = min(g, L), u' = clip(u, -L, L), y = rw * ((g' / (exp(-g') + 1)) * u'),
//   O.fmt BF16 -> round, L = imm_a (FLT_MAX disables);
//   vec op: A = g (record A) with a_min, imm3 = L; sfu SILU (div(x, add(exp(neg x), 1)): hdc_golden silu);
//           E1 MULC with C = u (record B) and c_clip; E2 MULB with B = rw (record C); rnd = (O.fmt == BF16); dst VM.
//   IEEE multiply is commutative, so mul(mul(silu, u'), rw) == mul(rw, mul(silu, u')) bit for bit.
// Refusals (rec_fault, halt): unit != 3 / op != 0, a template present, A / B / C / O absent, O.fmt not FP32 / BF16
//   (plus every SU-path refusal: non-VM operand, sizes >= 2^16).
// Latency: as the SU path (record accept E0 -> decoded word E1 -> unit accepts E2).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_sfu_record #(
    parameter integer MUT_SWAP = 0,        // mutant: up (B) and route weight (C) swapped
    parameter integer LEGACY = 1           // as ot_hgi_su_record (0: the routed adapter, records only)
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          hgi_en,
    input  wire          rec_v,
    output wire          rec_rdy,
    input  wire [127:0]  rec_hdr,
    input  wire [255:0]  rec_a, rec_b, rec_c, rec_o,
    input  wire [20:0]   rec_n_a,
    output wire          rec_done,
    output wire          rec_fault,
    output wire          halted,
    input  wire          lg_v,
    output wire          lg_rdy,
    input  wire [669:0]  lg_w,
    output wire          op_v,
    input  wire          op_rdy,
    output wire [669:0]  op_w,
    input  wire          su_idle,
    input  wire          su_fault
);
    ot_hgi_su_record #(.GLU(1), .LEGACY(LEGACY)) u_su (.clk(clk), .rst_n(rst_n), .hgi_en(hgi_en), .rec_v(rec_v),
        .rec_rdy(rec_rdy), .rec_hdr(rec_hdr), .rec_sut(256'd0), .rec_a(rec_a), .rec_b(MUT_SWAP ? rec_c : rec_b),
        .rec_c(MUT_SWAP ? rec_b : rec_c), .rec_d(256'd0), .rec_o(rec_o), .rec_r(256'd0), .rec_i(256'd0),
        .rec_n_a(rec_n_a), .rec_done(rec_done), .rec_fault(rec_fault), .halted(halted), .drained(), .lg_v(lg_v),
        .lg_rdy(lg_rdy), .lg_w(lg_w), .op_v(op_v), .op_rdy(op_rdy), .op_w(op_w), .su_idle(su_idle), .su_fault(su_fault));
endmodule
`default_nettype wire
