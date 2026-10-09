`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HGI-1 SFU record adapter (hgi-adapters, 2026-10-09).  Unit 3 (SFU.GLU, the fused SwiGLU chain) onto the SFU quarter's
// stream-unit op port (the vec op word of ot_hdc_v41x_vec; hfd_sfu = ot_su12_sfu lanes of the same vec family).
// Decode + handshake only: SFU.GLU is ONE vec op, so the adapter re-expresses the record as that op and runs it through
// ot_hgi_su_record (same issue / ordering / retire / fault logic, same legacy pass-through):
//   golden (spec 6.7, hgi_sim u_glu): g' = min(g, L), u' = clip(u, -L, L), y = rw * ((g' / (exp(-g') + 1)) * u'),
//   O.fmt BF16 -> round, L = imm_a (FLT_MAX disables);
//   vec op: A = g (record A) with a_min, imm3 = L; sfu SILU (div(x, add(exp(neg x), 1)): hdc_golden silu);
//           E1 MULC with C = u (record B) and c_clip; E2 MULB with B = rw (record C); rnd = (O.fmt == BF16); dst VM.
//   IEEE multiply is commutative, so mul(mul(silu, u'), rw) == mul(rw, mul(silu, u')) bit for bit.
// Refusals (rec_fault, halt): unit != 3 / op != 0, a template present, A / B / C / O absent, O.fmt not FP32 / BF16
//   (plus every SU-path refusal: non-VM operand, sizes >= 2^16).
// Latency: one repack edge in front of the SU path (record accept E0 -> repacked E1 -> SU station E2 -> unit E3).
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
    reg          p_v, f_pend, f_halt;
    reg  [127:0] p_hdr; reg [255:0] p_sut, p_a, p_b, p_c, p_o; reg [20:0] p_n;
    wire         s_rdy, s_done, s_fault, s_halted, s_drained;
    wire [6:0]   opnd = rec_hdr[99:93];
    wire bad = (rec_hdr[127:124] != 4'd3) || (rec_hdr[123:118] != 6'd0) || rec_hdr[92] ||
               !opnd[0] || !opnd[1] || !opnd[2] || !opnd[4] || (rec_o[4:2] != 3'd0 && rec_o[4:2] != 3'd1);
    // SUT (spec 6.9): a_min 14, c_clip 15, sfu 29:27 = SILU 5, e1 32:30 = MULC 1, e2 34:33 = MULB 1, rnd 35, dst 37:36 = 1,
    // imm3 141:110
    wire [255:0] sut = (256'd1 << 14) | (256'd1 << 15) | (256'd5 << 27) | (256'd1 << 30) | (256'd1 << 33) |
                       ({255'd0, rec_o[4:2] == 3'd1} << 35) | (256'd1 << 36) | ({224'd0, rec_hdr[63:32]} << 110);
    // SU header: unit 2, op 0, opnd {O, C, B, A} = 0b0010111, tmpl 1
    wire [127:0] hdr = {4'd2, 6'd0, 16'd0, 2'd0, 7'b0010111, 1'b1, 92'd0};
    assign rec_rdy = (LEGACY ? hgi_en : 1'b1) && !p_v && !f_pend && !f_halt && !s_halted;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin p_v <= 1'b0; f_pend <= 1'b0; f_halt <= 1'b0; p_hdr <= 0; p_sut <= 0; p_a <= 0; p_b <= 0;
                          p_c <= 0; p_o <= 0; p_n <= 0; end
        else begin
            if (rec_v && rec_rdy) begin
                if (bad) f_pend <= 1'b1;
                else begin
                    p_v <= 1'b1; p_hdr <= hdr; p_sut <= sut; p_a <= rec_a; p_o <= rec_o; p_n <= rec_n_a;
                    p_b <= MUT_SWAP ? rec_b : rec_c;     // vec B = the route weight (record C)
                    p_c <= MUT_SWAP ? rec_c : rec_b;     // vec C = up (record B), clipped
                end
            end
            if (p_v && s_rdy) p_v <= 1'b0;
            // a refusal retires in order: after the SU path drained (it holds no record)
            if (f_pend && s_drained && !p_v) begin f_pend <= 1'b0; f_halt <= 1'b1; end
        end
    end
    reg f_pulse;
    always @(posedge clk or negedge rst_n) if (!rst_n) f_pulse <= 1'b0; else f_pulse <= f_pend && s_drained && !p_v;
    assign rec_fault = s_fault | f_pulse;
    assign rec_done  = s_done;
    assign halted    = s_halted | f_halt;
    ot_hgi_su_record #(.LEGACY(LEGACY)) u_su (.clk(clk), .rst_n(rst_n), .hgi_en(hgi_en), .rec_v(p_v), .rec_rdy(s_rdy), .rec_hdr(p_hdr),
        .rec_sut(p_sut), .rec_a(p_a), .rec_b(p_b), .rec_c(p_c), .rec_d(256'd0), .rec_o(p_o), .rec_r(256'd0),
        .rec_i(256'd0), .rec_n_a(p_n), .rec_done(s_done), .rec_fault(s_fault), .halted(s_halted), .drained(s_drained), .lg_v(lg_v),
        .lg_rdy(lg_rdy), .lg_w(lg_w), .op_v(op_v), .op_rdy(op_rdy), .op_w(op_w), .su_idle(su_idle), .su_fault(su_fault));
endmodule
`default_nettype wire
