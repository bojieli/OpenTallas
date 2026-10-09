`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HGI-1 FUSED record adapter (hgi-adapters, 2026-10-09).  Unit 4 of the normative sequencer dispatch: the front of every
// FUSED operation (spec 6.7 order HC_PRE_NORM 0, ROW_NORM 1, HC_POST 2, SOFTMAX 3, QDQ_FP8 4, QDQ_FP4_E8M0 5,
// QDQ_FP4_E4M3 6).  Decode + handshake only; it reuses existing units:
//   ROW_NORM -> a micro-sequence on the FUSED stream unit (an ot_hdc_v41x_vec op port, through an internal
//     ot_hgi_su_record: same ordering / retire / fault) + one DMA move for the gain:
//       (0) mover: B (HBM BF16 gain, d elements) -> VM scratch G (FP32)                   [cfg_scratch: a VM region the
//           compiler reserves for the FUSED unit: d + 2 x nseg words]
//       (1) SU: R = csum(x * x) per segment      (A as nseg rows of d; red SUM, red_sq)   -> scratch S = G + d
//       (2) SU: r = rsqrt(s * (1/d) + eps)        (M1 AIMM 1/d (d a power of two: exact), or M1 DIVIMM d otherwise
//           (the DS golden's div), AD IMM eps = imm_a, SFU RSQRT)                          -> scratch S2 = S + nseg
//       (3) SU: y = (x * r) * g                    (M1 AB, B = S2 one value a row (ibcast); M2 C, C = G a row; rnd when
//           O is BF16)                                                                     -> O
//     = hgi_sim lib.row_norm (rsqrt(add(mul(s, 1/d), eps)), mul(mul(x, r), g)), segments of seg = param[13:6] (0: the
//     whole A), every step the golden's rounding point.
//   HC_PRE_NORM / HC_POST -> the DS norm engine / hc-post job port (ne_*: {op, A, B, C, O bases, n, eps}) unchanged.
//   QDQ_* -> forwarded to the quant record bus (ot_hgi_quant_record: {n_O, n_A, desc_O, desc_A, header, valid}).
//   SOFTMAX -> refused (CF-SFX is not bound in the simulator; programs use the three SU records of spec 7.2).
// Refusals (rec_fault + halt): unit != 4, op > 6, SOFTMAX, ROW_NORM with A / O not VM-contiguous, B not HBM BF16 inner
//   contiguous, segment not dividing A, B.n != d, d or nseg >= 2^16.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_fused_record #(
    parameter integer MUT_SEG = 0          // mutant: one segment of the whole row (seg ignored)
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [17:0]   cfg_scratch,     // VM word base of the FUSED scratch region (static)
    input  wire          rec_v,
    output wire          rec_rdy,
    input  wire [127:0]  rec_hdr,
    input  wire [255:0]  rec_a, rec_b, rec_c, rec_o,
    input  wire [20:0]   rec_n_a, rec_n_b, rec_n_o,
    output reg           rec_done,
    output reg           rec_fault,
    output wire          halted,
    // DMA move (ot_hgi_dma_record move word format, 227 b)
    output reg           mv_v,
    input  wire          mv_rdy,
    output reg  [226:0]  mv,
    input  wire          mv_done,
    input  wire          mv_fault,
    // stream-unit op port (vec PFIELDS) of the FUSED stream unit
    output wire          op_v,
    input  wire          op_rdy,
    output wire [669:0]  op_w,
    input  wire          su_idle,
    input  wire          su_fault,
    // DS norm engine / hc-post job: {op 2, eps 32, n 21, O base 18, C base 18, B base 40, A base 18} = 149 b
    output reg           ne_v,
    input  wire          ne_rdy,
    output reg  [148:0]  ne_job,
    input  wire          ne_done,
    input  wire          ne_fault,
    // quant record bus (QDQ) and its return {fault, done}
    output reg  [682:0]  q_rec,
    input  wire          q_done,
    input  wire          q_fault
);
    localparam [3:0] S_IDLE = 0, S_DEC = 1, S_MV = 2, S_MVW = 3, S_OP1 = 4, S_OP2 = 5, S_OP3 = 6, S_WSU = 7, S_NE = 8,
                     S_NEW = 9, S_Q = 10, S_HALT = 11;
    reg [3:0] st;
    reg [127:0] hdr; reg [255:0] dA, dB, dC, dO; reg [20:0] nA, nB, nO;
    reg in_mvd, in_mvf, in_ned, in_nef, in_qd, in_qf;
    always @(posedge clk) begin in_mvd <= mv_done; in_mvf <= mv_fault; in_ned <= ne_done; in_nef <= ne_fault;
                                in_qd <= q_done; in_qf <= q_fault; end
    assign rec_rdy = (st == S_IDLE);
    assign halted = (st == S_HALT);
    // ---- ROW_NORM geometry
    wire [5:0]  op  = hdr[123:118];
    wire [7:0]  seg = hdr[77:70];                         // param [13:6]
    wire [39:0] tot = nA * {20'd0, dA[87:68]};            // A elements (m rows of n)
    wire [20:0] d   = (seg == 8'd0 || MUT_SEG) ? tot[20:0] : {13'd0, seg};
    reg  [15:0] nseg;                                     // tot / d (d = seg | tot): by shift when seg is a power of 2
    wire        d_pow2 = (d != 21'd0) && ((d & (d - 21'd1)) == 21'd0);
    reg  [4:0]  lg_d; integer i;
    always @* begin lg_d = 5'd0; for (i = 0; i < 21; i = i + 1) if (d[i]) lg_d = i[4:0]; end
    always @* nseg = (seg == 8'd0 || MUT_SEG) ? 16'd1 : (tot >> lg_d);
    wire        seg_ok = (seg == 8'd0 || MUT_SEG) ? 1'b1 : (d_pow2 && ((tot & ({19'd0, d} - 40'd1)) == 40'd0));
    wire        a_contig = (dA[1:0] == 2'd1) && !dA[5] && (dA[135:120] <= 16'd1) && (dA[87:68] == 20'd1 || dA[119:88] == {11'd0, nA});
    wire        o_contig = (dO[1:0] == 2'd1) && !dO[5] && (dO[135:120] <= 16'd1) && (dO[87:68] == dA[87:68]) &&
                           (dO[87:68] == 20'd1 || dO[119:88] == {11'd0, nA}) && (nO == nA);
    wire        rn_ok = a_contig && o_contig && (dB[1:0] == 2'd0) && (dB[4:2] == 3'd1) && !dB[5] && (dB[135:120] <= 16'd1) &&
                        (nB == d) && seg_ok && (d != 21'd0) && (d < 21'd65536) && (|tot[39:16] == 1'b0 || seg != 8'd0);
    // binary32 of d and of 1/d (d a power of two)
    wire [43:0] dm = {23'd0, d} << (5'd23 - lg_d);
    wire [31:0] f_d = {1'b0, 8'd127 + {3'd0, lg_d}, dm[22:0]};
    wire [31:0] f_inv = {1'b0, 8'd127 - {3'd0, lg_d}, 23'd0};
    // ---- the internal SU path
    reg s_v; reg [127:0] s_hdr; reg [255:0] s_sut, s_a, s_b, s_c, s_o, s_r; reg [20:0] s_n;
    wire s_rdy, s_done, s_fault, s_halt, s_drained;
    ot_hgi_su_record #(.LEGACY(0)) u_su (.clk(clk), .rst_n(rst_n), .hgi_en(1'b1), .rec_v(s_v), .rec_rdy(s_rdy),
        .rec_hdr(s_hdr), .rec_sut(s_sut), .rec_a(s_a), .rec_b(s_b), .rec_c(s_c), .rec_d(256'd0), .rec_o(s_o), .rec_r(s_r),
        .rec_i(256'd0), .rec_n_a(s_n), .rec_done(s_done), .rec_fault(s_fault), .halted(s_halt), .drained(s_drained),
        .lg_v(1'b0), .lg_rdy(), .lg_w(670'd0), .op_v(op_v), .op_rdy(op_rdy), .op_w(op_w), .su_idle(su_idle),
        .su_fault(su_fault));
    function automatic [255:0] vmd(input [17:0] base, input [19:0] n, input [19:0] m, input [31:0] stride, input ib);
        vmd = {120'd0, 16'd0, stride, m, n, 22'd0, base, 2'b00, ib, 3'd0, 2'd1};   // space VM, fmt FP32, istride 0 (=1)
    endfunction
    function automatic [127:0] suh(input [6:0] opnd);
        suh = {4'd2, 6'd0, 16'd0, 2'd0, opnd, 1'b1, 92'd0};
    endfunction
    reg  [17:0] scr_q; always @(posedge clk) scr_q <= cfg_scratch;      // static strap, registered
    wire [17:0] g_b = scr_q, s1_b = cfg_scratch + d[17:0], s2_b = s1_b + nseg[15:0];
    reg [1:0] sudone;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; rec_done <= 1'b0; rec_fault <= 1'b0; mv_v <= 1'b0; mv <= 0; s_v <= 1'b0; ne_v <= 1'b0;
            ne_job <= 0; q_rec <= 0; hdr <= 0; dA <= 0; dB <= 0; dC <= 0; dO <= 0; nA <= 0; nB <= 0; nO <= 0; sudone <= 0;
            s_hdr <= 0; s_sut <= 0; s_a <= 0; s_b <= 0; s_c <= 0; s_o <= 0; s_r <= 0; s_n <= 0;
        end else begin
            rec_done <= 1'b0; rec_fault <= 1'b0; q_rec[0] <= 1'b0;
            if (s_v && s_rdy) s_v <= 1'b0;
            if (mv_v && mv_rdy) mv_v <= 1'b0;
            if (ne_v && ne_rdy) ne_v <= 1'b0;
            if (s_fault) begin rec_fault <= 1'b1; st <= S_HALT; end
            case (st)
                S_IDLE: if (rec_v) begin hdr <= rec_hdr; dA <= rec_a; dB <= rec_b; dC <= rec_c; dO <= rec_o;
                                         nA <= rec_n_a; nB <= rec_n_b; nO <= rec_n_o; st <= S_DEC; end
                S_DEC: begin
                    if (hdr[127:124] != 4'd4 || op > 6'd6 || op == 6'd3) begin rec_fault <= 1'b1; st <= S_HALT; end
                    else if (op == 6'd1) begin
                        if (!rn_ok) begin rec_fault <= 1'b1; st <= S_HALT; end
                        else begin                    // (0) gain -> G: {m 1, n d, dst VM FP32 G, src HBM BF16 B}
                            mv <= {d, 20'd1, 16'd1, 32'd0, {22'd0, g_b}, 3'd0, 2'd1, 16'd1, 32'd0, dB[47:8], 3'd1, 2'd0};
                            mv_v <= 1'b1; st <= S_MVW;
                        end
                    end else if (op >= 6'd4) begin
                        q_rec <= {nO, nA, dO, dA, hdr, 1'b1}; st <= S_Q;
                    end else begin
                        ne_job <= {op[1:0] == 2'd2 ? 2'd1 : 2'd0, hdr[63:32], nA, dO[25:8], dC[25:8], dB[47:8], dA[25:8]};
                        ne_v <= 1'b1; st <= S_NEW;
                    end
                end
                S_MVW: if (!mv_v) begin
                    if (in_mvf) begin rec_fault <= 1'b1; st <= S_HALT; end
                    else if (in_mvd) begin                // (1) sum of squares per segment -> S
                        s_hdr <= suh(7'b0100001);       // A, R
                        s_sut <= (256'd1 << 38) | (256'd1 << 40);                    // red SUM, red_sq
                        s_a <= vmd(dA[25:8], d[19:0], {4'd0, nseg}, {11'd0, d}, 1'b0); s_n <= d;
                        s_r <= vmd(s1_b, {4'd0, nseg}, 20'd1, 32'd1, 1'b0);
                        s_v <= 1'b1; sudone <= 2'd0; st <= S_OP1;
                    end
                end
                S_OP1: if (s_done) begin              // (2) r = rsqrt(s * 1/d + eps) (or s / d) -> S2
                    s_hdr <= suh(7'b0010001);           // A, O
                    s_sut <= ((d_pow2 ? 256'd3 : 256'd5) << 16) | (256'd4 << 24) | (256'd2 << 27) | (256'd1 << 36) |
                             ({224'd0, d_pow2 ? f_inv : f_d} << 46) | ({224'd0, hdr[63:32]} << 78);
                    s_a <= vmd(s1_b, {4'd0, nseg}, 20'd1, 32'd0, 1'b0); s_n <= {5'd0, nseg};
                    s_o <= vmd(s2_b, {4'd0, nseg}, 20'd1, 32'd0, 1'b0);
                    s_v <= 1'b1; st <= S_OP2;
                end
                S_OP2: if (s_done) begin              // (3) y = (x * r) * g -> O
                    s_hdr <= suh(7'b0010111);           // A, B, C, O
                    s_sut <= (256'd1 << 16) | (256'd1 << 19) | ({255'd0, dO[4:2] == 3'd1} << 35) | (256'd1 << 36);
                    s_a <= vmd(dA[25:8], d[19:0], {4'd0, nseg}, {11'd0, d}, 1'b0); s_n <= d;
                    s_b <= vmd(s2_b, {4'd0, nseg}, {4'd0, nseg}, 32'd1, 1'b1);   // one r a row (inner stride 0)
                    s_c <= vmd(g_b, d[19:0], 20'd1, 32'd0, 1'b0);                // the gain, every row
                    s_o <= vmd(dO[25:8], d[19:0], {4'd0, nseg}, {11'd0, d}, 1'b0);
                    s_v <= 1'b1; st <= S_OP3;
                end
                S_OP3: if (s_done) begin rec_done <= 1'b1; st <= S_IDLE; end
                S_NEW: if (!ne_v) begin
                    if (in_nef) begin rec_fault <= 1'b1; st <= S_HALT; end
                    else if (in_ned) begin rec_done <= 1'b1; st <= S_IDLE; end
                end
                S_Q: if (in_qf) begin rec_fault <= 1'b1; st <= S_HALT; end
                     else if (in_qd) begin rec_done <= 1'b1; st <= S_IDLE; end
                S_HALT: ;
                default: st <= S_HALT;
            endcase
        end
    end
endmodule
`default_nettype wire
