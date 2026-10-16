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
//   HC_PRE_NORM -> the mix x = bf16(seq_j pre[j] h[j]) as one stream-unit op (red SEQ, red_rnd), then the ROW_NORM
//     steps on x with the DS golden's divide (rmsnorm_bf16: bf16(w (x rsqrt(csum(x x) / D + eps)))).
//   HC_POST -> per copy k: mix_k = seq_j comb[j][k] res[j] (red SEQ) then out_k = bf16(post_k y + mix_k) (8 ops;
//     hdc_golden_v41 Model.hc_post).  The ne_* job port is kept for a later dedicated norm engine (unused).
//   QDQ_* -> forwarded to the quant record bus (ot_hgi_quant_record: {n_O, n_A, desc_O, desc_A, header, valid}).
//   SOFTMAX -> refused (CF-SFX is not bound in the simulator; programs use the three SU records of spec 7.2).
// Refusals (rec_fault + halt): unit != 4, op > 6, SOFTMAX, ROW_NORM with A / O not VM-contiguous, B not HBM BF16 inner
//   contiguous, segment not dividing A, B.n != d, d or nseg >= 2^16.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_fused_record #(
    parameter integer PAYLOAD_RESET = 1,
    parameter integer MUT_SEG = 0,         // mutant: one segment of the whole row (seg ignored)
    parameter integer UNIT = 0,            // 1: the D1 die body: the micro-ops run on an internal ot_hgi_su_unit (stage /
                                           //    vec / drain through the vmq / vmr VM client); 0: the vec op port (op_*)
    parameter integer UN = 32, UM = 8, ULV = 7,
    parameter integer SCR_WORDS = 0,       // F10: words reserved at cfg_scratch (0 = up to the end of VM); over -> fault
    parameter integer UWIDE = 0,           // hgi-unitrate: 1 = the internal die body is the wide successor (32-lane VM stage
                                           //    / drain, record pipeline: ot_hgi_su_unit WIDE); its lanes leave on wrq / wwq
    parameter integer ULWB = 17,
    parameter integer HCE = 0,             // hgi-1010 b: 1 = HC_POST / HC_PRE_NORM of row length HCD (sector-aligned bases)
                                           //   run on the internal one-pass ot_hgi_hc_eng (UNIT = 1, UWIDE = 1) instead of
                                           //   the micro-op lowering; other shapes keep the lowering
                                           // 2 = the same HC jobs handed to the EXTERNAL lane-local engine (the die's hfd_hc_eng
                                           //   = ot_hgi_hc_eng_station, own lgE slot) over the ne_* pins (die net fused_ne):
                                           //   one credit (a job a record), ne_v held until the registered ne_rdy (the engine's
                                           //   relayed job_rdy) is seen -> a level the far side edge-detects; ne_g = the gain-
                                           //   landed level (HC_PRE_NORM); ne_done / ne_fault pulses retire the record.  The
                                           //   record's own lanes stay with its stream unit (no hand-over); always HLL rules
    parameter integer HCD = 5120,
    parameter integer HMUT = 0,            // ot_hgi_hc_eng MUT (bench negatives)
    parameter integer HLL = 0,             // hbm-hcvm 10-11: 1 = the lane-local HC engine build (ot_hgi_hc_eng LL = 1); it takes
                                           //   only bank-phase-aligned A / B (or the gain scratch) / O (compiler rule), else lowering
    parameter integer HRL = 10,            // HLL: relay stages each way between the engine top and a lane
    parameter integer ULQ = 8,             // UWIDE / HCE: credits a wide VM lane holds (= the VM lane queue depth)
    parameter integer URWB = 6             // UWIDE = 0: log2 rows of the internal SU's reducer-result file: a reduction whose
                                           //   result rows exceed it (the HC mix: d rows; ROW_NORM sum of squares: nseg rows)
                                           //   runs as chunks of 2^URWB rows (hgi-1010/d: the lane-local SU keeps R in a file)
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
    // VM packet client of the D1 die body (UNIT = 1)
    output wire [337:0]  vmq,
    input  wire [273:0]  vmr,
    // the wide VM lanes of the D1 die body (UNIT = 1, UWIDE = 1; ot_hgi_su_unit WIDE ports)
    //   el1011-hbm-fused: widths scale with UWIDE (1 b each when UWIDE = 0): the narrow adapter build carried 21,391 IO
    //   for lanes it never drives (PPL-0024 at its 320 x 320 outline; at 640 x 640 the flop-to-pin wires failed TT/FF)
    output wire [(UWIDE != 0 ? 32*16 : 1)-1:0]  wrq,
    input  wire [(UWIDE != 0 ? 32 : 1)-1:0]     wrq_cr,
    input  wire [(UWIDE != 0 ? 32*257 : 1)-1:0] wrr,
    output wire [(UWIDE != 0 ? 32*280 : 1)-1:0] wwq,
    input  wire [(UWIDE != 0 ? 32 : 1)-1:0]     wwq_cr,
    input  wire [(UWIDE != 0 ? 32 : 1)-1:0]     wwq_done,
    output wire              rg_req,
    input  wire              rg_gnt,
    output wire              wg_req,
    input  wire              wg_gnt,
    // DS norm engine / hc-post job: {op 2, eps 32, n 21, O base 18, C base 18, B base 40, A base 18} = 149 b
    output reg           ne_v,
    input  wire          ne_rdy,
    output reg  [148:0]  ne_job,
    output wire          ne_g,            // HCE 2: the streamed gain move landed (registered level, rides with ne_job)
    input  wire          ne_done,
    input  wire          ne_fault,
    // quant record bus (QDQ) and its return {fault, done}
    output reg  [682:0]  q_rec,
    input  wire          q_done,
    input  wire          q_fault
);
    localparam [3:0] S_LD = 12, S_G1 = 13, S_G2 = 14, S_G3 = 15;
    localparam [4:0] S_G4 = 16, S_MX = 17, S_PM = 18, S_PO = 19, S_PW = 20, S_HPI = 21, S_HPW = 22;
    // hgi-unitrate: on the wide (PIPED) body HC_POST's 8 micro-ops issue back to back (the body overlaps their stage /
    // run / drain and orders the out_k <- mix_k dependence by its source / undrained-sink hazard); retire on the 8th done
    reg hph; reg [3:0] hdone;
    reg hg_rdy;                            // HCE HC_PRE_NORM: the streamed gain move landed (held to the record's end)
    reg mixed;
    localparam [3:0] S_IDLE = 0, S_DEC = 1, S_MV = 2, S_MVW = 3, S_OP1 = 4, S_OP2 = 5, S_OP3 = 6, S_WSU = 7, S_NE = 8,
                     S_NEW = 9, S_Q = 10, S_HALT = 11;
    reg [4:0] st;
    reg [127:0] hdr; reg [255:0] dA, dB, dC, dO; reg [20:0] nA, nB, nO;
    reg [127:0] p_hdr; reg [255:0] p_a, p_b, p_c, p_o; reg [20:0] p_na, p_nb, p_no;      // pin flops
    always @(posedge clk) begin p_hdr <= rec_hdr; p_a <= rec_a; p_b <= rec_b; p_c <= rec_c; p_o <= rec_o;
                                p_na <= rec_n_a; p_nb <= rec_n_b; p_no <= rec_n_o; end
    reg in_mvd, in_mvf, in_ned, in_nef, in_qd, in_qf;
    wire e_rdy, e_done, e_fault;
    reg in_ner;                            // HCE 2: the external engine's job_rdy (pin flop)
    wire ne_rdy_m = (HCE == 1) ? e_rdy : (HCE == 2) ? in_ner : ne_rdy;
    always @(posedge clk) begin in_mvd <= mv_done; in_mvf <= mv_fault; in_ned <= (HCE == 1) ? e_done : ne_done;
                                in_nef <= (HCE == 1) ? e_fault : ne_fault; in_ner <= ne_rdy;
                                in_qd <= q_done; in_qf <= q_fault; end
    // el1011-hbm-fused (textbook class 2): the port reset drove ~4.2k flops directly; it now enters through a local
    // reset relay (synchronised release, one region per consumer: FSM / HC engine / stream unit); rec_rdy waits for
    // the FSM region's release (a record offered while the relay still holds the FSM in reset is not taken)
    wire [2:0] rr; wire rst_f = rr[0];
    ot_rst_relay #(.REGIONS(3)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rr));
    reg up_q; always @(posedge clk or negedge rst_f) if (!rst_f) up_q <= 1'b0; else up_q <= 1'b1;
    assign rec_rdy = (st == S_IDLE) && up_q;
    assign halted = (st == S_HALT);
    // ---- ROW_NORM geometry
    wire [5:0]  op  = hdr[123:118];
    wire [7:0]  seg = hdr[77:70];                         // param [13:6]
    // geometry over registered stages (S_G1 multiply, S_G2 d / log2 d, S_G3 segments / constants): no long path
    reg  [39:0] tot; reg [19:0] m_sh; reg [2:0] gdig;    // tot = A.n x A.m (radix-16 Horner over A.m, 5 edges)
    reg  [20:0] d; reg [4:0] lg_d; reg d_pow2; reg [15:0] nseg; reg seg_ok;
    wire [20:0] d_c = (op == 6'd0) ? {2'd0, nA[20:2]} : (op == 6'd2) ? nA :
                      ((seg == 8'd0 || MUT_SEG) ? tot[20:0] : {13'd0, seg});
    reg  [4:0]  lg_c; integer i;
    always @* begin lg_c = 5'd0; for (i = 0; i < 21; i = i + 1) if (d_c[i]) lg_c = i[4:0]; end
    wire        a_contig = (dA[1:0] == 2'd1) && !dA[5] && (dA[135:120] <= 16'd1) && (dA[87:68] == 20'd1 || dA[119:88] == {11'd0, nA});
    wire        o_contig = (dO[1:0] == 2'd1) && !dO[5] && (dO[135:120] <= 16'd1) && (dO[87:68] == dA[87:68]) &&
                           (dO[87:68] == 20'd1 || dO[119:88] == {11'd0, nA}) && (nO == nA);
    wire        rn_ok = a_contig && o_contig && (dB[1:0] == 2'd0) && (dB[4:2] == 3'd1) && !dB[5] && (dB[135:120] <= 16'd1) &&
                        (nB == d) && seg_ok && (d != 21'd0) && (d < 21'd65536) && (|tot[39:16] == 1'b0 || seg != 8'd0);
    // HC_PRE_NORM: A = h (VM, 4 copies x D), B = gain (HBM BF16, D), C = pre (VM, >= 4), O (VM, D)
    // HC_POST:     A = y (VM, D), B = the residual (VM, 4 x D), C = mix + 4 (VM: post 4 | comb 16), O (VM, 4 x D)
    wire vmc = 1'b1;
    function automatic vmok(input [255:0] x); vmok = (x[1:0] == 2'd1) && !x[5] && (x[135:120] <= 16'd1); endfunction
    wire hp_ok = vmok(dA) && (nA[1:0] == 2'd0) && (dB[1:0] == 2'd0) && (dB[4:2] == 3'd1) && !dB[5] && (dB[135:120] <= 16'd1) &&
                 (nB == d) && vmok(dC) && vmok(dO) && (nO == d) && (d != 21'd0) && (d < 21'd65536);
    wire hq_ok = vmok(dA) && vmok(dB) && (nB == {d[18:0], 2'b00}) && vmok(dC) && vmok(dO) && (nO == {d[18:0], 2'b00}) &&
                 (d != 21'd0) && (d < 21'd16384);
    reg  [2:0] hk;                                      // HC_POST copy k
    reg  [17:0] x_b;                                    // HC_PRE_NORM: the mixed x (BF16 values) in scratch
    // reduction chunks: ce = the first result row of the current chunk; a chunk is min(RC, total - ce) rows
    localparam integer RCL = (UWIDE != 0) ? 20 : URWB;   // the wide body keeps R in its memory: one chunk
    localparam [20:0] RC = 21'd1 << RCL;
    reg  [20:0] ce;
    wire [20:0] ce_n = ce + RC;
    wire [19:0] cr_d = (d - ce > RC) ? RC[19:0] : 20'(d - ce);                 // rows of a d-row chunk
    wire [19:0] cr_s = ({5'd0, nseg} - ce > RC) ? RC[19:0] : 20'({5'd0, nseg} - ce);   // rows of an nseg-row chunk
    wire [17:0] ce18 = ce[17:0];
    reg  [17:0] cea;                                    // ce x d (accumulated: + d << URWB a chunk, no multiplier)
    wire [17:0] xa = (op == 6'd0) ? x_b : dA[25:8];    // the norm's input
    // binary32 of d and of 1/d (d a power of two), registered at S_G3
    wire [43:0] dm = {23'd0, d} << (5'd23 - lg_d);
    reg  [31:0] f_d, f_inv; reg [17:0] s1_b, s2_b;
    // ---- the internal SU path
    // the wide lanes: the internal SU, or the HC engine while it owns them (S_NEW; both quiet at the hand-over)
    wire own = (HCE == 1) && (st == 5'd9);
    assign ne_g = (HCE == 2) && hg_rdy;
    wire [32*16-1:0] u_wrq, e_wrq; wire [32*280-1:0] u_wwq, e_wwq; wire u_rg, u_wg, e_rg, e_wg;
    generate if (HCE == 1 && UNIT != 0 && UWIDE != 0) begin : g_hce
        assign wrq = own ? e_wrq : u_wrq; assign wwq = own ? e_wwq : u_wwq;
        assign rg_req = own ? e_rg : u_rg; assign wg_req = own ? e_wg : u_wg;
        ot_hgi_hc_eng #(.D(HCD), .LQ(ULQ), .MUT(HMUT), .LL(HLL), .RL(HRL)) u_hce (.clk(clk), .rst_n(rr[1]), .job_v(ne_v), .job_rdy(e_rdy),
            .job(ne_job), .g_rdy(hg_rdy), .done(e_done), .fault(e_fault), .idle(), .wrq(e_wrq), .wrq_cr(own ? wrq_cr : 32'd0), .wrr(own ? wrr : '0),
            .wwq(e_wwq), .wwq_cr(own ? wwq_cr : 32'd0), .wwq_done(own ? wwq_done : 32'd0), .rg_req(e_rg), .rg_gnt(rg_gnt),
            .wg_req(e_wg), .wg_gnt(wg_gnt));
    end else begin : g_nohce
        if (UNIT != 0) begin : g_pass
            assign wrq = u_wrq; assign wwq = u_wwq; assign rg_req = u_rg; assign wg_req = u_wg;
        end
        assign e_rdy = 1'b0; assign e_done = 1'b0; assign e_fault = 1'b0;
    end endgenerate
    reg s_v; reg [127:0] s_hdr; reg [255:0] s_sut, s_a, s_b, s_c, s_o, s_r; reg [20:0] s_n;
    wire s_rdy, s_done, s_fault, s_halt, s_drained;
    generate if (UNIT) begin : g_unit
        ot_hgi_su_unit #(.PAYLOAD_RESET(PAYLOAD_RESET), .N(UN), .M(UM), .LV(ULV), .WIDE(UWIDE), .LWB(ULWB), .RWB(URWB), .LQ(ULQ)) u_su (.clk(clk), .rst_n(rr[2]), .rec_v(s_v), .rec_rdy(s_rdy),
            .rec_hdr(s_hdr), .rec_sut(s_sut), .rec_a(s_a), .rec_b(s_b), .rec_c(s_c), .rec_d(256'd0), .rec_o(s_o),
            .rec_r(s_r), .rec_i(256'd0), .rec_n_a(s_n), .rec_done(s_done), .rec_fault(s_fault), .halted(s_halt),
            .vmq(vmq), .vmr(vmr), .s0_v(1'b0), .s0_idx(20'd0), .s0_data(32'd0), .am_stream(), .am_rdy(1'b0),
            .wrq(u_wrq), .wrq_cr(own ? 32'd0 : wrq_cr), .wrr(own ? '0 : wrr), .wwq(u_wwq), .wwq_cr(own ? 32'd0 : wwq_cr),
            .wwq_done(own ? 32'd0 : wwq_done), .rg_req(u_rg), .rg_gnt(rg_gnt), .wg_req(u_wg), .wg_gnt(wg_gnt));
        assign s_drained = 1'b1; assign op_v = 1'b0; assign op_w = 670'd0;
    end else begin : g_port
        ot_hgi_su_record #(.LEGACY(0)) u_su (.clk(clk), .rst_n(rr[2]), .hgi_en(1'b1), .rec_v(s_v), .rec_rdy(s_rdy),
            .rec_hdr(s_hdr), .rec_sut(s_sut), .rec_a(s_a), .rec_b(s_b), .rec_c(s_c), .rec_d(256'd0), .rec_o(s_o), .rec_r(s_r),
            .rec_i(256'd0), .rec_n_a(s_n), .rec_done(s_done), .rec_fault(s_fault), .halted(s_halt), .drained(s_drained),
            .lg_v(1'b0), .lg_rdy(), .lg_w(670'd0), .op_v(op_v), .op_rdy(op_rdy), .op_w(op_w), .su_idle(su_idle),
            .su_fault(su_fault));
        assign vmq = 338'd0; assign wrq = '0; assign wwq = '0; assign rg_req = 1'b0; assign wg_req = 1'b0;
    end endgenerate
    function automatic [255:0] vmd(input [17:0] base, input [19:0] n, input [19:0] m, input [31:0] stride, input ib);
        vmd = {120'd0, 16'd0, stride, m, n, 22'd0, base, 2'b00, ib, 3'd0, 2'd1};   // space VM, fmt FP32, istride 0 (=1)
    endfunction
    function automatic [127:0] suh(input [6:0] opnd);
        suh = {4'd2, 6'd0, 16'd0, 2'd0, opnd, 1'b1, 92'd0};
    endfunction
    reg  [17:0] scr_q; always @(posedge clk) scr_q <= cfg_scratch;      // static strap, registered
    // hgi-1010 b: the one-pass HC engine takes row length HCD with sector-aligned A / B / O (the gain at the scratch base)
    // the gain streamed packed (the raw HBM BF16 row as U32 words, concurrent with the engine's h pass): 4-byte aligned
    wire hgp_ok = (HCD % 512 == 0) && (dB[9:8] == 2'd0);
    wire hce_ok = (HCE != 0) && (UNIT != 0) && (UWIDE != 0) && (d == 21'(HCD)) && (dA[10:8] == 3'd0) && (dO[10:8] == 3'd0) &&
                  ((op == 6'd2) ? (dB[10:8] == 3'd0) : (scr_q[2:0] == 3'd0)) &&
                  ((HLL == 0 && HCE != 2) || ((dA[15:11] == dO[15:11]) && ((op == 6'd2) ? (dB[15:11] == dO[15:11]) : (scr_q[7:3] == dO[15:11]))));
    // F10: the end of the scratch this record uses (exclusive), against the reserved limit (SCR_WORDS words from the base,
    // 0 = up to the end of VM): an over-size record FAULTS instead of wrapping its scratch over live VM words
    wire [20:0] scr_end = {3'd0, scr_q} + d + ((op == 6'd0) ? (21'd2 + d) : {4'd0, nseg, 1'b0});
    wire [20:0] SCR_LIMIT_W = (SCR_WORDS == 0) ? 21'd262144 : ({3'd0, scr_q} + 21'(SCR_WORDS));

    wire [17:0] g_b = scr_q;
    reg k_bad, k_hq, k_nm, k_scr, k_hce, k_hgp;   // S_DEC decisions, registered at S_G4
    // H-MTP2 (2026-10-15) P-ROW HC_PRE_NORM: A.m = C.m = O.m = R (2..8) rows of the MTP verify's positions, one
    // broadcast gain (B.m = 1): the gain is moved ONCE and the HC engine runs the R rows as ONE job (job[39:37] = R - 1).
    // Compiler rule: rows contiguous (A stride 4 d, O stride d, C stride 8 words = one sector a row, C sector-aligned);
    // only on the HC engine path (the micro-op lowering refuses R > 1).
    wire [19:0] rA = dA[87:68];
    wire rw_multi = (op == 6'd0) && (rA > 20'd1);
    wire rw_ok = (rA <= 20'd8) && (dA[119:88] == {9'd0, d, 2'b00}) && (dC[87:68] == rA) && (dC[119:88] == 32'd8) &&
                 (dC[10:8] == 3'd0) && (dO[87:68] == rA) && (dO[119:88] == {11'd0, d});
    reg k_rw, k_rwok; reg [2:0] k_nr;
    reg [1:0] sudone;
    always @(posedge clk or negedge rst_f) begin
        if (!rst_f) begin
            st <= S_IDLE; mixed <= 1'b0; hk <= 3'd0; ce <= 21'd0; cea <= 18'd0; x_b <= 18'd0; rec_done <= 1'b0; rec_fault <= 1'b0; mv_v <= 1'b0; mv <= 0; hg_rdy <= 1'b0; s_v <= 1'b0; ne_v <= 1'b0;
            ne_job <= 0; q_rec <= 0; hdr <= 0; dA <= 0; dB <= 0; dC <= 0; dO <= 0; nA <= 0; nB <= 0; nO <= 0; sudone <= 0;
            s_hdr <= 0; s_sut <= 0; s_a <= 0; s_b <= 0; s_c <= 0; s_o <= 0; s_r <= 0; s_n <= 0;
        end else begin
            rec_done <= 1'b0; rec_fault <= 1'b0; q_rec[0] <= 1'b0;
            if (s_v && s_rdy) s_v <= 1'b0;
            if (mv_v && mv_rdy) mv_v <= 1'b0;
            if (ne_v && ne_rdy_m) ne_v <= 1'b0;
            if (s_fault) begin rec_fault <= 1'b1; st <= S_HALT; end
            if ((st == S_HPI || st == S_HPW) && s_done) hdone <= hdone + 4'd1;
            case (st)
                S_IDLE: if (rec_v) st <= S_LD;
                S_LD: begin hdr <= p_hdr; dA <= p_a; dB <= p_b; dC <= p_c; dO <= p_o; nA <= p_na; nB <= p_nb; nO <= p_no;
                            tot <= 40'd0; m_sh <= p_a[87:68]; gdig <= 3'd5; st <= S_G1; end
                S_G1: begin                                   // tot = n x m, a radix-16 digit of m an edge
                    tot <= (tot << 4) + nA * m_sh[19:16]; m_sh <= m_sh << 4; gdig <= gdig - 3'd1;
                    if (gdig == 3'd1) st <= S_G2;
                end
                S_G2: begin d <= d_c; lg_d <= lg_c; d_pow2 <= (d_c != 21'd0) && ((d_c & (d_c - 21'd1)) == 21'd0); st <= S_G3; end
                S_G3: begin
                    nseg <= (seg == 8'd0 || MUT_SEG || op != 6'd1) ? 16'd1 : (tot >> lg_d);
                    seg_ok <= (seg == 8'd0 || MUT_SEG) ? 1'b1 : (d_pow2 && ((tot & ({19'd0, d} - 40'd1)) == 40'd0));
                    f_d <= {1'b0, 8'd127 + {3'd0, lg_d}, dm[22:0]}; f_inv <= {1'b0, 8'd127 - {3'd0, lg_d}, 23'd0};
                    s1_b <= scr_q + d[17:0]; st <= S_G4;
                end
                S_G4: begin s2_b <= s1_b + nseg; x_b <= s1_b + nseg + 18'd1; st <= S_DEC;
                    // el1011-hbm-fused: S_DEC's decisions registered here (operands stable since S_LD, d since S_G2,
                    // nseg since S_G3): S_DEC is a mux on flops, not a descriptor-check cone into mv / ne_job
                    k_bad <= (hdr[127:124] != 4'd4 || op > 6'd6 || op == 6'd3); k_hq <= hq_ok;
                    k_nm <= (op == 6'd1) ? rn_ok : hp_ok; k_scr <= (scr_end > SCR_LIMIT_W);
                    k_hce <= hce_ok; k_hgp <= hgp_ok;
                    k_rw <= rw_multi; k_rwok <= rw_ok && hce_ok; k_nr <= rw_multi ? 3'(rA - 20'd1) : 3'd0; end
                S_DEC: begin
                    if (k_bad) begin rec_fault <= 1'b1; st <= S_HALT; end
                    else if (op == 6'd2) begin                 // HC_POST: 4 x (mix_k, out_k) on the stream unit
                        if (!k_hq) begin rec_fault <= 1'b1; st <= S_HALT; end
                        else if (k_hce) begin
                            ne_job <= {2'd1, hdr[63:32], d, dO[25:8], dC[25:8], 22'd0, dB[25:8], dA[25:8]};
                            ne_v <= 1'b1; st <= S_NEW;
                        end
                        else if (UWIDE != 0) begin hk <= 3'd0; hph <= 1'b0; hdone <= 4'd0; ce <= 21'd0; st <= S_HPI; end
                        else begin hk <= 3'd0; st <= S_PM; end
                    end else if (op == 6'd1 || op == 6'd0) begin
                        // F10 (hgi-unitrate): the scratch the micro-sequence uses must fit the reserved region and VM:
                        // ROW_NORM G (d) + S (nseg) + S2 (nseg); HC_PRE_NORM G (d) + S + S2 + the mixed x (d)
                        if (!k_nm || (k_rw && !k_rwok)) begin rec_fault <= 1'b1; st <= S_HALT; end
                        else if (k_scr) begin rec_fault <= 1'b1; st <= S_HALT; end
                        else if (op == 6'd0 && k_hce && k_hgp) begin
                            // HC engine: gain -> G as raw U32 words {m 1, n d/2, dst VM U32 G, src HBM U32 B} streamed
                            // while the engine reads h (it reads G on hg_rdy)
                            mv <= {21'(d >> 1), 20'd1, 16'd1, 32'd0, {22'd0, g_b}, 3'd5, 2'd1, 16'd1, 32'd0, dB[47:8], 3'd5, 2'd0};
                            mv_v <= 1'b1; hg_rdy <= 1'b0;
                            ne_job <= {2'd0, hdr[63:32], d, dO[25:8], dC[25:8], 18'd0, k_nr, 1'b1, g_b, dA[25:8]};
                            ne_v <= 1'b1; st <= S_NEW;
                        end
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
                    else if (in_mvd && op == 6'd0 && k_hce) begin   // the one-pass engine: h, gain (G), pre
                        ne_job <= {2'd0, hdr[63:32], d, dO[25:8], dC[25:8], 18'd0, k_nr, 1'b0, g_b, dA[25:8]};
                        ne_v <= 1'b1; st <= S_NEW;
                    end
                    else if (in_mvd && op == 6'd0 && !mixed) begin   // (0b) x = bf16(seq_j pre[j] h[j]) -> X
                        s_hdr <= suh(7'b0100011);       // A, B, R
                        s_sut <= (256'd1 << 16) | (256'd3 << 38) | (256'd1 << 42);   // M1 AB, red SEQ, red_rnd
                        s_a <= vmd(dA[25:8], 20'd4, cr_d, 32'd1, 1'b0) | (256'd0 + ({240'd0, d[15:0]} << 120)); s_n <= 21'd4;
                        s_b <= vmd(dC[25:8], 20'd4, cr_d, 32'd0, 1'b0);
                        s_r <= vmd(x_b, cr_d, 20'd1, 32'd1, 1'b0);
                        s_v <= 1'b1; mixed <= 1'b1; st <= S_MX;
                    end
                    else if (in_mvd || (op == 6'd0 && mixed)) begin    // (1) sum of squares per segment -> S
                        s_hdr <= suh(7'b0100001);       // A, R
                        s_sut <= (256'd1 << 38) | (256'd1 << 40);                    // red SUM, red_sq
                        s_a <= vmd(xa, d[19:0], cr_s, {11'd0, d}, 1'b0); s_n <= d;
                        s_r <= vmd(s1_b, cr_s, 20'd1, 32'd1, 1'b0); mixed <= 1'b0; ce <= 21'd0;
                        cea <= 18'(d << RCL); s_v <= 1'b1; sudone <= 2'd0; st <= S_OP1;
                    end
                end
                S_OP1: if (s_done && ce_n < {5'd0, nseg}) begin   // (1) next chunk of segments
                    ce <= ce_n; cea <= cea + 18'(d << RCL);
                    s_a <= vmd(xa + cea, d[19:0], ({5'd0, nseg} - ce_n > RC) ? RC[19:0] : 20'({5'd0, nseg} - ce_n),
                               {11'd0, d}, 1'b0);
                    s_r <= vmd(s1_b + ce_n[17:0], ({5'd0, nseg} - ce_n > RC) ? RC[19:0] : 20'({5'd0, nseg} - ce_n), 20'd1, 32'd1, 1'b0);
                    s_v <= 1'b1;
                end
                else if (s_done) begin                // (2) r = rsqrt(s * 1/d + eps) (or s / d) -> S2
                    ce <= 21'd0;
                    s_hdr <= suh(7'b0010001);           // A, O
                    s_sut <= ((d_pow2 && op == 6'd1 ? 256'd3 : 256'd5) << 16) | (256'd4 << 24) | (256'd2 << 27) |
                             (256'd1 << 36) | ({224'd0, d_pow2 && op == 6'd1 ? f_inv : f_d} << 46) | ({224'd0, hdr[63:32]} << 78);
                    s_a <= vmd(s1_b, {4'd0, nseg}, 20'd1, 32'd0, 1'b0); s_n <= {5'd0, nseg};
                    s_o <= vmd(s2_b, {4'd0, nseg}, 20'd1, 32'd0, 1'b0);
                    s_v <= 1'b1; st <= S_OP2;
                end
                S_OP2: if (s_done) begin              // (3) y = (x * r) * g -> O
                    s_hdr <= suh(7'b0010111);           // A, B, C, O
                    s_sut <= (256'd1 << 16) | (256'd1 << 19) | ({255'd0, dO[4:2] == 3'd1 || op == 6'd0} << 35) | (256'd1 << 36);
                    s_a <= vmd(xa, d[19:0], {4'd0, nseg}, {11'd0, d}, 1'b0); s_n <= d;
                    s_b <= vmd(s2_b, {4'd0, nseg}, {4'd0, nseg}, 32'd1, 1'b1);   // one r a row (inner stride 0)
                    s_c <= vmd(g_b, d[19:0], 20'd1, 32'd0, 1'b0);                // the gain, every row
                    s_o <= vmd(dO[25:8], d[19:0], {4'd0, nseg}, {11'd0, d}, 1'b0);
                    s_v <= 1'b1; st <= S_OP3;
                end
                S_OP3: if (s_done) begin rec_done <= 1'b1; st <= S_IDLE; end
                S_MX: if (s_done) begin                         // a mix chunk landed: the next, else on to the norm
                    if (ce_n < d) begin
                        ce <= ce_n;
                        s_a <= vmd(dA[25:8] + ce_n[17:0], 20'd4, (d - ce_n > RC) ? RC[19:0] : 20'(d - ce_n), 32'd1, 1'b0) |
                               (256'd0 + ({240'd0, d[15:0]} << 120));
                        s_b <= vmd(dC[25:8], 20'd4, (d - ce_n > RC) ? RC[19:0] : 20'(d - ce_n), 32'd0, 1'b0);
                        s_r <= vmd(x_b + ce_n[17:0], (d - ce_n > RC) ? RC[19:0] : 20'(d - ce_n), 20'd1, 32'd1, 1'b0);
                        s_v <= 1'b1;
                    end else begin ce <= 21'd0; st <= S_MVW; end
                end
                // HC_POST copy k: (a) mix_k[d] = seq_j comb[j][k] res[j][d] -> scratch G; (b) out_k = bf16(post_k y + mix_k)
                S_PM: if (!s_v) begin
                    s_hdr <= suh(7'b0100011);           // A, B, R
                    s_sut <= (256'd1 << 16) | (256'd3 << 38);                  // M1 AB, red SEQ (FP32)
                    s_a <= vmd(dB[25:8] + ce18, 20'd4, cr_d, 32'd1, 1'b0) | ({240'd0, d[15:0]} << 120); s_n <= 21'd4;
                    s_b <= vmd(dC[25:8] + 18'd4 + {15'd0, hk}, 20'd4, cr_d, 32'd0, 1'b0) | (256'd4 << 120);
                    s_r <= vmd(g_b + ce18, cr_d, 20'd1, 32'd1, 1'b0);
                    s_v <= 1'b1; st <= S_PO;
                end
                S_PO: if (s_done && ce_n < d) begin ce <= ce_n; st <= S_PM; end   // the next mix chunk
                else if (s_done) begin
                    ce <= 21'd0;
                    s_hdr <= suh(7'b0010111);           // A, B, C, O
                    s_sut <= (256'd1 << 16) | (256'd2 << 24) | (256'd1 << 35) | (256'd1 << 36);   // M1 AB, AD C, rnd, VM
                    s_a <= vmd(dA[25:8], d[19:0], 20'd1, 32'd0, 1'b0); s_n <= d;
                    s_b <= vmd(dC[25:8] + {15'd0, hk}, d[19:0], 20'd1, 32'd0, 1'b1);   // post_k, every element
                    s_c <= vmd(g_b, d[19:0], 20'd1, 32'd0, 1'b0);
                    s_o <= vmd(dO[25:8] + hk * d[17:0], d[19:0], 20'd1, 32'd0, 1'b0);
                    s_v <= 1'b1; st <= S_PW;
                end
                S_PW: if (s_done) begin
                    if (hk == 3'd3) begin rec_done <= 1'b1; st <= S_IDLE; end
                    else begin hk <= hk + 3'd1; st <= S_PM; end
                end
                S_HPI: if (!s_v) begin                          // issue mix_k / out_k, k = 0..3, back to back
                    if (!hph) begin
                        s_hdr <= suh(7'b0100011);
                        s_sut <= (256'd1 << 16) | (256'd3 << 38);
                        s_a <= vmd(dB[25:8], 20'd4, d[19:0], 32'd1, 1'b0) | ({240'd0, d[15:0]} << 120); s_n <= 21'd4;
                        s_b <= vmd(dC[25:8] + 18'd4 + {15'd0, hk}, 20'd4, d[19:0], 32'd0, 1'b0) | (256'd4 << 120);
                        s_r <= vmd(g_b + {15'd0, hk[1:0], 1'b0} * 18'd0, d[19:0], 20'd1, 32'd1, 1'b0);
                        s_v <= 1'b1; hph <= 1'b1;
                    end else begin
                        s_hdr <= suh(7'b0010111);
                        s_sut <= (256'd1 << 16) | (256'd2 << 24) | (256'd1 << 35) | (256'd1 << 36);
                        s_a <= vmd(dA[25:8], d[19:0], 20'd1, 32'd0, 1'b0); s_n <= d;
                        s_b <= vmd(dC[25:8] + {15'd0, hk}, d[19:0], 20'd1, 32'd0, 1'b1);
                        s_c <= vmd(g_b, d[19:0], 20'd1, 32'd0, 1'b0);
                        s_o <= vmd(dO[25:8] + hk * d[17:0], d[19:0], 20'd1, 32'd0, 1'b0);
                        s_v <= 1'b1; hph <= 1'b0;
                        if (hk == 3'd3) st <= S_HPW; else hk <= hk + 3'd1;
                    end
                end
                S_HPW: if (hdone + {3'd0, s_done} == 4'd8) begin rec_done <= 1'b1; st <= S_IDLE; end
                S_NEW: if (in_mvf) begin rec_fault <= 1'b1; st <= S_HALT; end
                else begin
                    if (in_mvd) hg_rdy <= 1'b1;
                    if (ne_v) ;
                    else if (in_nef) begin rec_fault <= 1'b1; st <= S_HALT; end
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
