// CLAUDE S81-PH su (2026-10-06): REMOTE-READ copy of rtl/hdc/v41x/ot_hdc_v41x_vec_lane.sv (module renamed ot_s81ph_*). RX = 0, GX = 0 is the original
// cycle for cycle.  RX: extra cycles between a lane's operand read (MR) and the memory's answer (the read request and
// the word cross the die bus: SU slab lanes, VM in the hub slab); GX: the same for the gather-index read (vi).  The lane
// delays its read tags (m -> x) by RX and its gather G1 stage by GX; the controller's fetch insertion line and its
// depth model (c_dF) grow by RX (+ GX with a gather), so every later stage, credit and checkpoint moves with it.
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// One lane of the V4.1 vector stream unit (ot_hdc_v41x_vec): the element
// datapath from the controller's vector position to the element writes and the
// value handed to the reducer.  KIND picks the lane's units:
//
//   KIND 0  LIGHT  mul / add / max / BF16 rounding.  Every stage is fixed:
//                  M1 3, M2 3, AD 3, no SFU stage, E1 3, E2 3.
//   KIND 1  SFU    LIGHT plus an IEEE divider at M1 (A'/B, A'/imm1: 19) and the
//                  SFU stage: exp (49), sigmoid / SiLU (exp, +1, divide: 71).
//   KIND 2  FULL   (lane 0) SFU plus the scalar side pipe's results: rsqrt (37),
//                  sqrt (31), sqrt(softplus) (162), Engram gate (104).
//
// Timing, from the cycle E the lane sees the vector (the controller's broadcast
// register, one cycle after its emit decision; every boundary registered):
//   E+1   F0  lane position (o, i), liveness, the four operand addresses, the
//             output address (linear or transposed-KV), the gather-index read
//   E+3   G2  (gather ops only) A's address with the gathered index; B, C, D
//             wait with it
//   E+dF  X   operands captured (dF = 3, or 5 with a gather)
//   +1    PRE A' = min(relu(rnd?(A)), imm3), C' = clip(C, +-imm3)
//   +m1   M1  P = A' | A'*B | A'*A' | A'*imm1 | max(A', B) (3) | A'/B | A'/imm1 (19)
//   +3    M2  P2 = P | P*C' | P*imm1;  Q = C' * (+-D)  (a second multiplier)
//   +3    AD  R = P2 | P2+Q | P2+C' | P2-B | P2+imm2 | P2+D
//   +s    S   S = R | exp | sigmoid | silu | rsqrt | sqrt | sqrt(softplus) | gate
//   +3    E1  T = S | S*C' | S+C' | S*imm2 | S+imm2
//   +3    E2  U = T | T*B | T*imm1
//   +1    OUT out = rnd?(U) -> vector memory / KV SRAM, and to the reducer
// A linear op therefore writes 20 cycles after E, 21 after the emit decision (23 with a gather).
// MLAT = 4 (the LAT-4 multiplier, ot_hdc_qmul_lat; W11 serial domain, 0.9 GHz at SS): M1, M2, E1, E2 are 4 deep
// (E1's add waits one cycle), exp 56, sigmoid / SiLU 78, rsqrt 46, sqrt(softplus) 180, gate 111: a linear
// op writes 25 cycles after the emit decision.
//
// Stages whose depth depends on the op (the fetch, M1, S) are INSERTION lines
// (ot_hdc_v41x_ins): an element enters at the stage that leaves at its own
// depth, so there is one exit and the stage after it sees one element a cycle.
// The controller keeps every element leaving each such stage after the element
// before it (the checkpoint rule), so vectors of different ops overlap in the
// pipeline without draining.  The per-vector control (op fields, immediates)
// travels in ONE control pipe in the controller with the same stage
// structure; a lane takes each stage's fields from it (ctl_*).  Only
// per-element data travels in the lane: the operands B, C', D, the output
// address, the liveness and the index parity.
// ---------------------------------------------------------------------------
module ot_s81ph_vec_lane #(
    parameter integer RX = 0,           // S81-PH: operand-read extra latency
    parameter integer GX = 0,           // S81-PH: gather-index-read extra latency
    parameter integer AW = 24,
    parameter integer CW = 24,          // internal count width
    parameter integer LN = 3,           // log2 lanes (offset terms)
    parameter integer KIND = 0,         // 0 light, 1 SFU, 2 full (lane 0)
    parameter integer KVT_SH = 9,
    parameter integer LEAF = 0,         // 1: the broadcast tree's LAST stage is this lane's own leaf register (below)
    parameter integer MLAT = 3,         // multiplier latency (ot_hdc_qmul_lat): 3, 4, or 5 (W11 serial domain, 0.9 GHz)
    parameter integer ALAT = 3          // FP add latency (ot_hdc_qadd_lat): 3, or 4 (input cut); ALAT <= MLAT
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [10:0]       lane_id,   // this lane's index in the unit (a constant at every instance)
    // ---- offsets of an op being set up: lane l's offset is the sum of c[k] over the set bits k of l
    input  wire              ld,
    input  wire              ld_bank,
    input  wire [5*LN*AW-1:0] ld_c,     // stream s (A, B, C, D, O), term k: [(s*LN + k)*AW +: AW]
    // ---- emit (E): the controller's vector position and the active op's fields
    input  wire              emit,
    input  wire              bank,
    input  wire [CW-1:0]     o_v, i_v, no, ni,
    input  wire [3:0]        ls,        // log2 slot size S
    input  wire [3:0]        lvw,       // log2 of the lanes in use: slot size x slots a vector
    input  wire [5*AW-1:0]   vb,        // vector base of A, B, C, D, O
    input  wire [AW-1:0]     krow,      // transposed-KV row of the vector's first lane
    input  wire [AW-1:0]     obase,     // transposed-KV base
    input  wire [AW-1:0]     aibase,
    input  wire [1:0]        aind,
    input  wire [4:0]        gsh,       // gather: index << gsh
    input  wire              cpair,
    input  wire [1:0]        dst,
    input  wire [7:0]        srcs,      // {dsrc, csrc, bsrc, asrc}
    // ---- memories
    output reg               vi_re,
    output reg  [AW-1:0]     vi_addr,
    input  wire [31:0]       vi_q,
    output wire [4*AW-1:0]   rd_addr,   // {D, C, B, A}
    output wire [3:0]        rd_re,
    output wire [7:0]        rd_src,    // per stream: vector memory, constant ROM lo / hi, BF16 weight ROM
    input  wire [4*32-1:0]   rd_q,      // the selected source's word (the weight ROM's BF16 in the top half)
    // ---- per-stage control from the control pipe
    input  wire [7:0]        cx_srcs,                  // at X
    input  wire              cx_arnd, cx_arelu, cx_amin, cx_cclip,
    input  wire [31:0]       cx_imm3,
    input  wire [2:0]        cp_m1,                    // at PRE (M1 inputs)
    input  wire [31:0]       cp_imm1,
    input  wire [2:0]        cm_m1,                    // at M1 out
    input  wire [1:0]        cm_m2,
    input  wire [2:0]        cm_qm,
    input  wire [31:0]       cm_imm1,
    input  wire [2:0]        ca_ad,                    // at AD in
    input  wire [31:0]       ca_imm2,
    input  wire [2:0]        ci_sfu,                   // at S in
    input  wire [2:0]        cs_sfu,                   // at S out
    input  wire [2:0]        cs_e1,
    input  wire [31:0]       cs_imm2,
    input  wire [1:0]        ce_e2,                    // at E2 in
    input  wire [31:0]       ce_imm1,
    input  wire              co_rnd,                   // at OUT in
    input  wire [1:0]        co_dst,
    // ---- scalar side pipe (lane 0)
    output wire              side_v,
    output wire [31:0]       side_x,
    input  wire [31:0]       side_y,                   // the side function's result, at S out
    // ---- writes and the reducer
    output reg               vm_we,
    output reg  [AW-1:0]     vm_waddr,
    output reg  [31:0]       vm_wdata,
    output reg               kv_we,
    output reg  [AW-1:0]     kv_waddr,
    output reg  [31:0]       kv_wdata,
    output wire              ro_v,                     // live element at OUT (with vm_we timing)
    output wire [31:0]       ro_x,
    output wire              fault,
    output wire              coll
);
    /* verilator no_inline_module */
    localparam [1:0] SRC_VM = 0, SRC_CLO = 1, SRC_CHI = 2, SRC_WROM = 3;
    localparam [1:0] IND_NONE = 0, IND_I = 1, IND_O = 2;
    localparam [1:0] DST_NONE = 0, DST_VM = 1, DST_KV = 2, DST_KVT = 3;
    localparam [2:0] M1_BYP = 0, M1_AB = 1, M1_AA = 2, M1_AIMM = 3, M1_DIVB = 4, M1_DIVIMM = 5, M1_MAXB = 6;
    localparam [1:0] M2_BYP = 0, M2_C = 1, M2_IMM = 2;
    localparam [2:0] QM_OFF = 0, QM_POS = 1, QM_NEG = 2, QM_ALT_NP = 3, QM_ALT_PN = 4;
    localparam [2:0] AD_BYP = 0, AD_Q = 1, AD_C = 2, AD_NEGB = 3, AD_IMM = 4, AD_D = 5;
    localparam [2:0] SFU_NONE = 0, SFU_EXP = 1, SFU_RSQRT = 2, SFU_SQRT = 3, SFU_SIGM = 4, SFU_SILU = 5,
                     SFU_SPSQRT = 6, SFU_EGATE = 7;
    localparam [2:0] E1_BYP = 0, E1_MULC = 1, E1_ADDC = 2, E1_MULIMM = 3, E1_ADDIMM = 4;
    localparam [1:0] E2_BYP = 0, E2_MULB = 1, E2_MULIMM = 2;
    // stage depths; MLAT = 4 lengthens every multiplying stage by one (M1 / M2 / E1 / E2: 4) and the SFU chains
    localparam integer D_DIV = 19, D_EXP = 7 * MLAT + 8 * ALAT + 4, D_SIG = D_EXP + ALAT + D_DIV;  // 49, 71
    localparam integer D_RSQ = 1 + 9 * MLAT + 3 * ALAT, D_SQRT = 31;                                // 37
    localparam integer D_SP = D_EXP + 11 * MLAT + 10 * ALAT + 50;                                    // 162
    localparam integer D_EG = 1 + 31 + 1 + D_SIG;                                        // 104 (111)
    // MLAT >= 4 is the serial-domain build: its integer adds and compares are keep-prefix adders
    // (ot_hdc_kadd / _kge / _kinc over rtl/hdc/ot_hdc_prefix.sv) and its FP adds ot_hdc_fp32_add_lat3, so ABC
    // cannot re-ripple them inside the lane; MLAT = 3 keeps the behavioural operators (the unit as it was)
    localparam integer K = (MLAT != 3 || ALAT != 3) ? 1 : 0;
    generate if (ALAT > MLAT || ALAT < 3 || ALAT > 4) begin : g_bad_alat
        ot_hdc_v41x_vec_lane_ALAT_must_be_3_or_4_and_at_most_MLAT u_trap ();
    end endgenerate
    localparam [15:0] H_DIV = D_DIV, H_M = MLAT, H_EXP = D_EXP, H_SIG = D_SIG, H_RSQ = D_RSQ, H_SQRT = D_SQRT,
                      H_SP = D_SP, H_EG = D_EG;
    localparam integer HAS_SFU = (KIND != 0);
    localparam integer FULL = (KIND == 2);

    function automatic [31:0] bf16(input [31:0] x);
        bf16 = (x + 32'h7FFF + {31'd0, x[16]}) & 32'hFFFF0000;
    endfunction
    function automatic [31:0] okey(input [31:0] v);
        okey = v[31] ? ~v : {1'b1, v[30:0]};
    endfunction
    function automatic [31:0] fmin(input [31:0] a, input [31:0] b);
        fmin = (okey(a) <= okey(b)) ? a : b;
    endfunction
    function automatic [31:0] fmax(input [31:0] a, input [31:0] b);
        fmax = (okey(a) >= okey(b)) ? a : b;
    endfunction
    // relu then min: the two compares (v and +0 against imm) run side by side
    function automatic [31:0] pre_a(input [31:0] v, input relu, input amin, input [31:0] imm);
        reg zero, le_v, le_0;
        begin
            zero = relu && v[31];
            le_v = okey(v) <= okey(imm);
            le_0 = okey(32'd0) <= okey(imm);
            pre_a = !amin ? (zero ? 32'd0 : v) : zero ? (le_0 ? 32'd0 : imm) : (le_v ? v : imm);
        end
    endfunction

    // pre_a with its two compares supplied (le_v: okey(v) <= okey(imm), le_0: okey(+0) <= okey(imm))
    function automatic [31:0] pre_a2(input [31:0] v, input relu, input amin, input [31:0] imm, input le_v, input le_0);
        reg zero;
        begin
            zero = relu && v[31];
            pre_a2 = !amin ? (zero ? 32'd0 : v) : zero ? (le_0 ? 32'd0 : imm) : (le_v ? v : imm);
        end
    endfunction

    // ---- LEAF: the broadcast's last register stage --------------------------------------------------
    // LEAF = 0: the lane uses its inputs as they arrive (the controller's broadcast register, or the tree's
    // leaf outside the lane).  LEAF = 1 (ot_hdc_v41x_vec with BCAST_STAGES > 0): the tree's last stage is
    // this lane's own register, and it holds the lane-local partials of the vector instead of the raw
    // fields: the position (o_v + d_o, i_v + d_i), the transposed-KV row (krow + d_o), whether the lane is in
    // use, and the four stream addresses and the output address (vector base + this lane's offset).  F0 is
    // then one add / compare level (the liveness compares, the transposed-KV address, the gather index
    // address) instead of two adds feeding a three-input add.  Same cycle, same values: bit-exact.
    // Cost: 8 x 24-bit partials + 1 in-use bit, plus the fields F0 still reads (emit, no, ni, obase,
    // aibase, aind, gsh, cpair, dst, srcs: 115 bits): 308 flops a lane, plus the three-cycle offset load
    // below (604).  The offset load does not pass the leaf: it starts from the tree's stage (ld, ld_bank,
    // ld_c), where the lane without a leaf would have loaded in one cycle.
    reg [AW-1:0] off0 [0:4];
    reg [AW-1:0] off1 [0:4];
    wire [CW-1:0] lid = {{(CW-11){1'b0}}, lane_id};
    //: slot (outer) and in-slot (inner) offsets of this lane for a slot size 2^ls
    wire [CW-1:0] d_o = lid >> ls;
    wire [CW-1:0] d_i = lid & ((1 << ls) - 1);
    wire [CW-1:0] ol_c, il_c;
    wire [AW-1:0] row_c;
    wire [2:0]    unused_c0;
    ot_hdc_kadd #(.W(CW), .K(K)) u_olc (.a(o_v), .b(d_o), .cin(1'b0), .s(ol_c), .cout(unused_c0[0]));
    ot_hdc_kadd #(.W(CW), .K(K)) u_ilc (.a(i_v), .b(d_i), .cin(1'b0), .s(il_c), .cout(unused_c0[1]));
    ot_hdc_kadd #(.W(AW), .K(K)) u_rwc (.a(krow), .b(d_o[AW-1:0]), .cin(1'b0), .s(row_c), .cout(unused_c0[2]));
    wire          lin_c = (lid < (1 << lvw));
    wire [5*AW-1:0] sum_c;
    genvar gs;
    generate for (gs = 0; gs < 5; gs = gs + 1) begin : g_sum
        wire unused_cs;
        ot_hdc_kadd #(.W(AW), .K(K)) u_s (.a(vb[gs*AW +: AW]), .b(bank ? off1[gs] : off0[gs]), .cin(1'b0),
                                          .s(sum_c[gs*AW +: AW]), .cout(unused_cs));
    end endgenerate
    // what F0 and the offset bank read: the partials and fields at the leaf
    wire             emit_e, ld_e, ldbank_e, lin_e, cpair_e;
    wire [CW-1:0]    ol_e, il_e, no_e, ni_e;
    wire [AW-1:0]    row_e, obase_e, aibase_e;
    wire [5*AW-1:0]  sum_e;
    wire [1:0]       aind_e, dst_e;
    wire [4:0]       gsh_e;
    wire [7:0]       srcs_e;
    wire [5*LN*AW-1:0] ldc_e;
    generate if (LEAF == 0) begin : g_noleaf
        assign {emit_e, ld_e, ldbank_e, ldc_e} = {emit, ld, ld_bank, ld_c};
        assign {ol_e, il_e, row_e, lin_e, sum_e} = {ol_c, il_c, row_c, lin_c, sum_c};
        assign {no_e, ni_e, obase_e, aibase_e, aind_e, dst_e, gsh_e, srcs_e, cpair_e} =
               {no, ni, obase, aibase, aind, dst, gsh, srcs, cpair};
    end else begin : g_leaf
        reg              r_emit;
        reg              r_lin, r_cpair;
        reg [CW-1:0]     r_ol, r_il, r_no, r_ni;
        reg [AW-1:0]     r_row, r_obase, r_aibase;
        reg [5*AW-1:0]   r_sum;
        reg [1:0]        r_aind, r_dst;
        reg [4:0]        r_gsh;
        reg [7:0]        r_srcs;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) r_emit <= 1'b0;
            else r_emit <= emit;
        end
        always @(posedge clk) begin
            r_ol <= ol_c; r_il <= il_c; r_row <= row_c; r_lin <= lin_c; r_sum <= sum_c;
            r_no <= no; r_ni <= ni; r_obase <= obase; r_aibase <= aibase; r_aind <= aind; r_dst <= dst;
            r_gsh <= gsh; r_srcs <= srcs; r_cpair <= cpair;
        end
        assign emit_e = r_emit;
        assign {ld_e, ldbank_e, ldc_e} = {ld, ld_bank, ld_c};
        assign {ol_e, il_e, row_e, lin_e, sum_e} = {r_ol, r_il, r_row, r_lin, r_sum};
        assign {no_e, ni_e, obase_e, aibase_e, aind_e, dst_e, gsh_e, srcs_e, cpair_e} =
               {r_no, r_ni, r_obase, r_aibase, r_aind, r_dst, r_gsh, r_srcs, r_cpair};
    end endgenerate

    // ---- offsets: two banks, loaded by the op set-up --------------------------------------------
    // A lane's offset is the sum of the terms of its lane_id's set bits (LN terms).  LEAF = 0: in one cycle.
    // LEAF = 1: over THREE (W11 serial domain; the two-cycle form summed 5 terms in its first cycle and was
    // the routed lane's worst path at 1.111 ns SS): cycle 1 sums the terms in three groups (bits [0, G1),
    // [G1, G2), [G2, LN): at most ceil(LN/3) = 4 terms at LN = 10) and registers the three partials; cycle 2
    // adds the first two; cycle 3 adds the third into the bank.  Integer sums mod 2^AW: the same offsets.
    // Timing (ld_e is the tree stage's ld, one cycle before the leaf; the controller loads in the cycle
    // before the op may promote, so its first vector reaches the tree stage >= 3 cycles after ld_e): the bank
    // is written at the end of ld_e + 2 and read by the leaf's sums from ld_e + 3 on, so it lands in the
    // cycle before its first use (the two-cycle load landed one cycle earlier).  The op two back (same bank)
    // emitted its last vector >= 3 cycles before the load left the controller, so it read the bank >= 4
    // cycles before the write.  Cost 5 x 5 x AW + 4 flops (604; was 5 x 2 x AW + 2 = 242).
    localparam integer G1 = (LN + 2) / 3, G2 = 2 * ((LN + 2) / 3);
    generate if (LEAF == 0) begin : g_ld1
        integer s, k;
        reg [AW-1:0] acc;
        always @(posedge clk) begin
            if (ld_e) begin
                for (s = 0; s < 5; s = s + 1) begin
                    acc = {AW{1'b0}};
                    for (k = 0; k < LN; k = k + 1)
                        if (lane_id[k]) acc = acc + ldc_e[(s*LN + k)*AW +: AW];
                    if (ldbank_e) off1[s] <= acc; else off0[s] <= acc;
                end
            end
        end
    end else if (K == 0) begin : g_ld3
        integer s, k;
        reg [AW-1:0] g0, g1, g2;
        reg          ldp_v, ldq_v, ldp_bank, ldq_bank;
        reg [AW-1:0] ldp_0 [0:4];
        reg [AW-1:0] ldp_1 [0:4];
        reg [AW-1:0] ldp_2 [0:4];
        reg [AW-1:0] ldq_01 [0:4];
        reg [AW-1:0] ldq_2 [0:4];
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin ldp_v <= 1'b0; ldq_v <= 1'b0; end
            else begin ldp_v <= ld_e; ldq_v <= ldp_v; end
        end
        always @(posedge clk) begin
            if (ld_e) begin
                ldp_bank <= ldbank_e;
                for (s = 0; s < 5; s = s + 1) begin
                    g0 = {AW{1'b0}};
                    g1 = {AW{1'b0}};
                    g2 = {AW{1'b0}};
                    for (k = 0; k < LN; k = k + 1)
                        if (lane_id[k]) begin
                            if (k < G1)      g0 = g0 + ldc_e[(s*LN + k)*AW +: AW];
                            else if (k < G2) g1 = g1 + ldc_e[(s*LN + k)*AW +: AW];
                            else             g2 = g2 + ldc_e[(s*LN + k)*AW +: AW];
                        end
                    ldp_0[s] <= g0;
                    ldp_1[s] <= g1;
                    ldp_2[s] <= g2;
                end
            end
            if (ldp_v) begin
                ldq_bank <= ldp_bank;
                for (s = 0; s < 5; s = s + 1) begin
                    ldq_01[s] <= ldp_0[s] + ldp_1[s];
                    ldq_2[s] <= ldp_2[s];
                end
            end
            if (ldq_v)
                for (s = 0; s < 5; s = s + 1)
                    if (ldq_bank) off1[s] <= ldq_01[s] + ldq_2[s]; else off0[s] <= ldq_01[s] + ldq_2[s];
        end
    end else begin : g_ld3k
        // the same three cycles on keep-prefix adders: a group's (at most 4) masked terms in a two-level tree
        reg          ldp_v, ldq_v, ldp_bank, ldq_bank;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin ldp_v <= 1'b0; ldq_v <= 1'b0; end
            else begin ldp_v <= ld_e; ldq_v <= ldp_v; end
        end
        always @(posedge clk) begin
            if (ld_e) ldp_bank <= ldbank_e;
            if (ldp_v) ldq_bank <= ldp_bank;
        end
        genvar ss, jj, kk;
        wire [5*AW-1:0] s_bus;                         // stream ss's offset, at the third cycle
        integer s;
        always @(posedge clk)
            if (ldq_v)
                for (s = 0; s < 5; s = s + 1)
                    if (ldq_bank) off1[s] <= s_bus[s*AW +: AW]; else off0[s] <= s_bus[s*AW +: AW];
        for (ss = 0; ss < 5; ss = ss + 1) begin : g_s
            wire [3*AW-1:0] grp;                       // the three group sums of stream ss
            for (jj = 0; jj < 3; jj = jj + 1) begin : g_j
                localparam integer LO = (jj == 0) ? 0 : (jj == 1) ? G1 : G2;
                localparam integer HI = (jj == 0) ? G1 : (jj == 1) ? G2 : LN;
                wire [4*AW-1:0] t;                     // the group's masked terms, zero-padded to 4
                for (kk = 0; kk < 4; kk = kk + 1) begin : g_t
                    if (LO + kk < HI) begin : g_on
                        assign t[kk*AW +: AW] = lane_id[LO + kk] ? ldc_e[(ss*LN + LO + kk)*AW +: AW] : {AW{1'b0}};
                    end else begin : g_off
                        assign t[kk*AW +: AW] = {AW{1'b0}};
                    end
                end
                wire [AW-1:0] s01, s23;
                wire [2:0]    unused_c;
                if (HI - LO > 2) begin : g_4
                    ot_hdc_kadd #(.W(AW), .K(1)) u_a (.a(t[0 +: AW]), .b(t[AW +: AW]), .cin(1'b0), .s(s01), .cout(unused_c[0]));
                    ot_hdc_kadd #(.W(AW), .K(1)) u_b (.a(t[2*AW +: AW]), .b(t[3*AW +: AW]), .cin(1'b0), .s(s23), .cout(unused_c[1]));
                    ot_hdc_kadd #(.W(AW), .K(1)) u_c (.a(s01), .b(s23), .cin(1'b0), .s(grp[jj*AW +: AW]), .cout(unused_c[2]));
                end else if (HI - LO == 2) begin : g_2
                    ot_hdc_kadd #(.W(AW), .K(1)) u_a (.a(t[0 +: AW]), .b(t[AW +: AW]), .cin(1'b0), .s(grp[jj*AW +: AW]), .cout(unused_c[0]));
                    assign {s01, s23, unused_c[2:1]} = 0;
                end else begin : g_1
                    assign grp[jj*AW +: AW] = t[0 +: AW];
                    assign {s01, s23, unused_c} = 0;
                end
            end
            reg  [AW-1:0] p0, p1, p2, q01, q2;
            wire [AW-1:0] s_01, s_all;
            wire [1:0]    unused_q;
            ot_hdc_kadd #(.W(AW), .K(1)) u_q (.a(p0), .b(p1), .cin(1'b0), .s(s_01), .cout(unused_q[0]));
            ot_hdc_kadd #(.W(AW), .K(1)) u_o (.a(q01), .b(q2), .cin(1'b0), .s(s_all), .cout(unused_q[1]));
            assign s_bus[ss*AW +: AW] = s_all;
            always @(posedge clk) begin
                if (ld_e) begin p0 <= grp[0 +: AW]; p1 <= grp[AW +: AW]; p2 <= grp[2*AW +: AW]; end
                if (ldp_v) begin q01 <= s_01; q2 <= p2; end
            end
        end
    end endgenerate

    // ---- F0: liveness, addresses ------------------------------------------------------------------
    wire ol_ge, il_ge;
    ot_hdc_kge #(.W(CW), .K(K)) u_olg (.a(ol_e), .b(no_e), .ge(ol_ge));
    ot_hdc_kge #(.W(CW), .K(K)) u_ilg (.a(il_e), .b(ni_e), .ge(il_ge));
    wire live0 = emit_e && lin_e && !ol_ge && !il_ge;
    // (il << 4) + row[3:0] is the concatenation {il, row[3:0]}
    wire [AW-1:0] kvt, kvt1, vi_sum;
    wire [2:0]    unused_c1;
    ot_hdc_kadd #(.W(AW), .K(K)) u_kv1 (.a(obase_e), .b((row_e >> 4) << KVT_SH), .cin(1'b0), .s(kvt1), .cout(unused_c1[0]));
    ot_hdc_kadd #(.W(AW), .K(K)) u_kv2 (.a(kvt1), .b({il_e[AW-5:0], row_e[3:0]}), .cin(1'b0), .s(kvt), .cout(unused_c1[1]));
    ot_hdc_kadd #(.W(AW), .K(K)) u_via (.a(aibase_e), .b((aind_e == IND_I) ? il_e[AW-1:0] : ol_e[AW-1:0]), .cin(1'b0),
                                        .s(vi_sum), .cout(unused_c1[2]));
    reg          f_v, f_g, f_par;
    reg [AW-1:0] f_a, f_b, f_c, f_d, f_o;
    reg [7:0]    f_src;
    reg          f_cpair;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin f_v <= 1'b0; vi_re <= 1'b0; end
        else begin f_v <= live0; vi_re <= live0 && (aind_e != IND_NONE); end
    end
    always @(posedge clk) begin
        f_g <= (aind_e != IND_NONE);
        f_a <= sum_e[0 +: AW];
        f_b <= sum_e[AW +: AW];
        f_c <= sum_e[2*AW +: AW];
        f_d <= sum_e[3*AW +: AW];
        f_o <= (dst_e == DST_KVT) ? kvt : sum_e[4*AW +: AW];
        f_par <= il_e[0];
        f_src <= srcs_e;
        f_cpair <= cpair_e;
        vi_addr <= vi_sum;
    end
    // ---- S81-PH GX: the gather vector waits GX cycles for the remote index word (f_* -> gd_*)
    localparam integer GW = 5 * AW + 1 + 8 + 1 + 5;
    wire          gd_v, gd_par, gd_cpair;
    wire [AW-1:0] gd_a, gd_b, gd_c, gd_d, gd_o;
    wire [7:0]    gd_src;
    wire [4:0]    gd_sh;
    generate if (GX == 0) begin : g_gx0
        assign gd_v = f_v && f_g;
        assign {gd_a, gd_b, gd_c, gd_d, gd_o, gd_par, gd_src, gd_cpair, gd_sh} = {f_a, f_b, f_c, f_d, f_o, f_par, f_src, f_cpair, f_sh};
    end else begin : g_gx
        reg [GX-1:0] gv;
        reg [GW-1:0] gq [0:GX-1];
        integer gi;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) gv <= {GX{1'b0}};
            else gv <= {gv, f_v && f_g};   // shift in at bit 0, the oldest at the top
        end
        always @(posedge clk) begin
            gq[0] <= {f_a, f_b, f_c, f_d, f_o, f_par, f_src, f_cpair, f_sh};
            for (gi = 1; gi < GX; gi = gi + 1) gq[gi] <= gq[gi-1];
        end
        assign gd_v = gv[GX-1];
        assign {gd_a, gd_b, gd_c, gd_d, gd_o, gd_par, gd_src, gd_cpair, gd_sh} = gq[GX-1];
    end endgenerate
    // ---- G1, G2: a gathered A (index from the vector memory, scaled by a power of two) ---------------
    reg          g1_v, g2_v, g1_par, g2_par, g1_cpair, g2_cpair;
    reg [AW-1:0] g1_a, g1_b, g1_c, g1_d, g1_o, g2_a, g2_b, g2_c, g2_d, g2_o;
    reg [7:0]    g1_src, g2_src;
    reg [4:0]    g1_sh;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin g1_v <= 1'b0; g2_v <= 1'b0; end
        else begin g1_v <= gd_v; g2_v <= g1_v; end
    end
    reg [4:0] f_sh;
    always @(posedge clk) f_sh <= gsh_e;
    wire [AW-1:0] g2_sum;
    wire          unused_c2;
    ot_hdc_kadd #(.W(AW), .K(K)) u_g2a (.a(g1_a), .b(vi_q[AW-1:0] << g1_sh), .cin(1'b0), .s(g2_sum), .cout(unused_c2));
    always @(posedge clk) begin
        g1_a <= gd_a; g1_b <= gd_b; g1_c <= gd_c; g1_d <= gd_d; g1_o <= gd_o; g1_par <= gd_par; g1_src <= gd_src;
        g1_cpair <= gd_cpair; g1_sh <= gd_sh;
        g2_a <= g2_sum;
        g2_b <= g1_b; g2_c <= g1_c; g2_d <= g1_d; g2_o <= g1_o; g2_par <= g1_par; g2_src <= g1_src;
        g2_cpair <= g1_cpair;
    end
    // ---- memory reads: the F0 vector, or a gather vector two cycles later ------------------------------
    wire          mr_nv = f_v && !f_g;
    wire          mr_v  = mr_nv || g2_v;
    wire [AW-1:0] mr_a  = g2_v ? g2_a : f_a;
    wire [AW-1:0] mr_c  = (g2_v ? g2_cpair : f_cpair) ? (mr_a ^ {{(AW-1){1'b0}}, 1'b1}) : (g2_v ? g2_c : f_c);
    wire [7:0]    mr_src = g2_v ? g2_src : f_src;
    assign rd_addr = {g2_v ? g2_d : f_d, mr_c, g2_v ? g2_b : f_b, mr_a};
    assign rd_re = {4{mr_v}};
    assign rd_src = mr_src;
    // tags of the read, to the capture two cycles later
    reg          m_v, x_v;
    reg [AW-1:0] m_o, x_o;
    reg          m_par, x_par;
    // S81-PH RX: the read tags wait RX more cycles for the remote word (m -> md -> x)
    wire          md_v, md_par;
    wire [AW-1:0] md_o;
    generate if (RX == 0) begin : g_rx0
        assign {md_v, md_o, md_par} = {m_v, m_o, m_par};
    end else begin : g_rx
        reg [RX-1:0] rv;
        reg [AW:0]   rq [0:RX-1];
        integer ri;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) rv <= {RX{1'b0}};
            else rv <= {rv, m_v};   // shift in at bit 0, the oldest at the top
        end
        always @(posedge clk) begin
            rq[0] <= {m_o, m_par};
            for (ri = 1; ri < RX; ri = ri + 1) rq[ri] <= rq[ri-1];
        end
        assign md_v = rv[RX-1];
        assign {md_o, md_par} = rq[RX-1];
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin m_v <= 1'b0; x_v <= 1'b0; end
        else begin m_v <= mr_v; x_v <= md_v; end
    end
    always @(posedge clk) begin
        m_o <= g2_v ? g2_o : f_o; m_par <= g2_v ? g2_par : f_par;
        x_o <= md_o; x_par <= md_par;
    end
    // ---- X: capture (the memories answered during the cycle before) --------------------------------------
    reg [31:0] x_a, x_b, x_c, x_d;
    always @(posedge clk) begin
        x_a <= rd_q[31:0]; x_b <= rd_q[63:32]; x_c <= rd_q[95:64]; x_d <= rd_q[127:96];
    end
    // ---- PRE ------------------------------------------------------------------------------------------
    // A' = min(relu(rnd?(A)), imm3), evaluated for the three values rnd?(A) can take (A itself, A truncated to
    // BF16, and truncated + one BF16 ulp) side by side and selected by the rounding decision, so no compare
    // waits for the rounding carry (bit-identical for all inputs: tools/w11_equiv_clip.ys; W11 timing fix)
    wire [31:0] a_t  = {x_a[31:16], 16'd0};
    wire [15:0] a_hi1;
    ot_hdc_kinc #(.W(16), .K(K)) u_au (.a(x_a[31:16]), .inc(1'b1), .y(a_hi1));
    wire [31:0] a_u  = {a_hi1, 16'd0};
    wire        a_up = x_a[15] & ((|x_a[14:0]) | x_a[16]);
    // pre_a's compares, as prefix compares: okey(v) <= okey(imm3) for the three candidates, and +0 <= imm3
    wire [31:0] k_imm3 = okey(cx_imm3);
    wire        le_x, le_t, le_u, le_0;
    ot_hdc_kge #(.W(32), .K(K)) u_lex (.a(k_imm3), .b(okey(x_a)), .ge(le_x));
    ot_hdc_kge #(.W(32), .K(K)) u_let (.a(k_imm3), .b(okey(a_t)), .ge(le_t));
    ot_hdc_kge #(.W(32), .K(K)) u_leu (.a(k_imm3), .b(okey(a_u)), .ge(le_u));
    ot_hdc_kge #(.W(32), .K(K)) u_le0 (.a(k_imm3), .b(32'h80000000), .ge(le_0));
    wire [31:0] a_mx = pre_a2(x_a, cx_arelu, cx_amin, cx_imm3, le_x, le_0);
    wire [31:0] a_mt = pre_a2(a_t, cx_arelu, cx_amin, cx_imm3, le_t, le_0);
    wire [31:0] a_mu = pre_a2(a_u, cx_arelu, cx_amin, cx_imm3, le_u, le_0);
    wire [31:0] a_m  = !cx_arnd ? a_mx : a_up ? a_mu : a_mt;
    // clip(C, -imm3, imm3) = fmin(fmax(C, lo), hi) with its three comparisons side by side (bit-identical,
    // ties included: proven by tools/w11_equiv_clip.ys; the chained form was the lane's critical path, W11)
    wire [31:0] c_lo = {1'b1, cx_imm3[30:0]};
    wire        c_ge_lo, c_le_hi, c_lohi;
    ot_hdc_kge #(.W(32), .K(K)) u_cgl (.a(okey(x_c)), .b(okey(c_lo)), .ge(c_ge_lo));
    ot_hdc_kge #(.W(32), .K(K)) u_clh (.a(k_imm3), .b(okey(x_c)), .ge(c_le_hi));
    ot_hdc_kge #(.W(32), .K(K)) u_clo (.a(k_imm3), .b(okey(c_lo)), .ge(c_lohi));
    wire [31:0] c_m = !cx_cclip ? x_c : c_ge_lo ? (c_le_hi ? x_c : cx_imm3) : (c_lohi ? c_lo : cx_imm3);
    reg  [31:0] p_a, p_b, p_c, p_d;
    reg  [AW-1:0] p_o;
    reg         p_v, p_par;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) p_v <= 1'b0; else p_v <= x_v;
    end
    always @(posedge clk) begin
        p_a <= a_m; p_b <= x_b; p_c <= c_m; p_d <= x_d; p_o <= x_o; p_par <= x_par;
    end
    // ---- M1 ---------------------------------------------------------------------------------------------
    wire p_mul = (cp_m1 == M1_AB) || (cp_m1 == M1_AA) || (cp_m1 == M1_AIMM);
    wire p_div = (cp_m1 == M1_DIVB) || (cp_m1 == M1_DIVIMM);
    wire [31:0] mul1_y, byp1;
    wire f_m1;
    ot_hdc_qmul_lat #(MLAT) u_m1 (clk, rst_n, p_v && p_mul, p_a, (cp_m1 == M1_AB) ? p_b : (cp_m1 == M1_AA) ? p_a : cp_imm1,
                      mul1_y, f_m1);
    wire        ba_ge;                               // okey(p_a) >= okey(p_b), i.e. not (okey(p_b) > okey(p_a))
    ot_hdc_kge #(.W(32), .K(K)) u_mxb (.a(okey(p_a)), .b(okey(p_b)), .ge(ba_ge));
    wire [31:0] byp_in = (cp_m1 == M1_MAXB && !ba_ge) ? p_b : p_a;
    ot_hdc_delay #(.W(32), .D(MLAT)) u_b1 (.clk(clk), .rst_n(rst_n), .d(byp_in), .q(byp1));
    localparam integer T1W = 32 * 3 + AW + 1;            // B, C', D, O, parity
    wire [T1W-1:0] t1;
    wire           v1;
    wire [31:0]    div1_y;
    wire           f_d1, c1;
    generate
        if (HAS_SFU != 0) begin : g_m1s
            ot_hdc_v41x_fdiv u_d1 (.clk(clk), .rst_n(rst_n), .v(p_v && p_div), .a(p_a),
                                   .b((cp_m1 == M1_DIVB) ? p_b : cp_imm1), .y(div1_y), .vo(), .fault(f_d1));
            ot_hdc_v41x_ins #(.W(T1W), .K(2), .DEPTHS({H_DIV, H_M}), .DMAX(19)) u_l1 (
                .clk(clk), .rst_n(rst_n), .v(p_v), .sel({p_div, !p_div}), .d({p_b, p_c, p_d, p_o, p_par}),
                .vo(v1), .q(t1), .coll(c1), .busy());
        end else begin : g_m1l
            assign div1_y = 32'd0; assign f_d1 = 1'b0; assign c1 = 1'b0;
            ot_hdc_delay #(.W(T1W), .D(MLAT)) u_t1 (.clk(clk), .rst_n(rst_n), .d({p_b, p_c, p_d, p_o, p_par}), .q(t1));
            wire [MLAT:0] vl;
            ot_hdc_vline #(.D(MLAT)) u_v1 (.clk(clk), .rst_n(rst_n), .v(p_v), .vd(vl));
            assign v1 = vl[MLAT];
        end
    endgenerate
    wire [31:0] m_b = t1[T1W-1 -: 32], m_c = t1[T1W-33 -: 32], m_d = t1[T1W-65 -: 32];
    wire [AW-1:0] m_oa = t1[AW:1];
    wire        m_par1 = t1[0];
    wire [31:0] P = (cm_m1 == M1_DIVB || cm_m1 == M1_DIVIMM) ? div1_y :
                    (cm_m1 == M1_AB || cm_m1 == M1_AA || cm_m1 == M1_AIMM) ? mul1_y : byp1;
    // ---- M2 and Q -----------------------------------------------------------------------------------------
    wire [31:0] m2_y, q_y, m2_byp;
    wire f_m2, f_q;
    ot_hdc_qmul_lat #(MLAT) u_m2 (clk, rst_n, v1 && cm_m2 != M2_BYP, P, (cm_m2 == M2_C) ? m_c : cm_imm1, m2_y, f_m2);
    wire qneg = (cm_qm == QM_NEG) || (cm_qm == QM_ALT_NP && !m_par1) || (cm_qm == QM_ALT_PN && m_par1);
    ot_hdc_qmul_lat #(MLAT) u_q (clk, rst_n, v1 && cm_qm != QM_OFF, m_c, {m_d[31] ^ qneg, m_d[30:0]}, q_y, f_q);
    wire [31:0] a2_b, a2_c, a2_d;
    wire [AW-1:0] a2_o;
    wire [1:0]  a2_m2;
    ot_hdc_delay #(.W(32 * 4 + AW + 2), .D(MLAT)) u_d2 (.clk(clk), .rst_n(rst_n),
        .d({P, m_b, m_c, m_d, m_oa, cm_m2}), .q({m2_byp, a2_b, a2_c, a2_d, a2_o, a2_m2}));
    wire [MLAT:0] v2l;
    ot_hdc_vline #(.D(MLAT)) u_v2 (.clk(clk), .rst_n(rst_n), .v(v1), .vd(v2l));
    wire v2 = v2l[MLAT];
    wire [31:0] P2 = (a2_m2 == M2_BYP) ? m2_byp : m2_y;
    // ---- AD ------------------------------------------------------------------------------------------------
    reg [31:0] ad_y;
    always @(*) begin
        case (ca_ad)
            AD_Q:    ad_y = q_y;
            AD_C:    ad_y = a2_c;
            AD_NEGB: ad_y = {~a2_b[31], a2_b[30:0]};
            AD_IMM:  ad_y = ca_imm2;
            default: ad_y = a2_d;
        endcase
    end
    wire [31:0] add_y, add_byp;
    wire f_ad;
    ot_hdc_qadd_lat #(.KEEP(K), .LAT(ALAT)) u_ad (clk, rst_n, v2 && ca_ad != AD_BYP, P2, ad_y, add_y, f_ad);
    wire [31:0] r_b, r_c;
    wire [AW-1:0] r_o;
    wire [2:0]  r_ad;
    ot_hdc_delay #(.W(32 * 3 + AW + 3), .D(ALAT)) u_d3 (.clk(clk), .rst_n(rst_n),
        .d({P2, a2_b, a2_c, a2_o, ca_ad}), .q({add_byp, r_b, r_c, r_o, r_ad}));
    wire [ALAT:0] v3l;
    ot_hdc_vline #(.D(ALAT)) u_v3 (.clk(clk), .rst_n(rst_n), .v(v2), .vd(v3l));
    wire v3 = v3l[ALAT];
    wire [31:0] R = (r_ad == AD_BYP) ? add_byp : add_y;
    // ---- S --------------------------------------------------------------------------------------------------
    localparam integer T4W = 32 * 3 + AW;                 // R, B, C', O
    wire [T4W-1:0] t4;
    wire           v4, c4;
    wire [31:0]    S;
    wire           f_sfu;
    generate
        if (HAS_SFU != 0) begin : g_sfu
            // sigmoid chain: exp(-R); +1; (1 | R) / that
            wire is_exp = (ci_sfu == SFU_EXP), is_sig = (ci_sfu == SFU_SIGM || ci_sfu == SFU_SILU);
            wire [31:0] y_exp, den, num_d, y_div;
            wire f_e, f_den, f_div;
            wire [D_EXP:0] ve;
            wire [D_EXP:0] vs;                 // a sigmoid-chain element, along the exp
            ot_hdc_vline #(.D(D_EXP)) u_ve (.clk(clk), .rst_n(rst_n), .v(v3 && (is_exp || is_sig)), .vd(ve));
            ot_hdc_vline #(.D(D_EXP)) u_vs (.clk(clk), .rst_n(rst_n), .v(v3 && is_sig), .vd(vs));
            ot_hdc_v41x_exp #(.LM(MLAT), .LA(ALAT)) u_exp (.clk(clk), .rst_n(rst_n), .v(v3 && (is_exp || is_sig)),
                                   .x(is_exp ? R : {~R[31], R[30:0]}), .y(y_exp), .vo(), .fault(f_e));
            ot_hdc_qadd_lat #(.KEEP(K), .LAT(ALAT)) u_den (clk, rst_n, vs[D_EXP], y_exp, 32'h3F800000, den, f_den);
            wire silu_in = (ci_sfu == SFU_SILU);
            wire [31:0] num_in = silu_in ? R : 32'h3F800000;
            ot_hdc_delay #(.W(32), .D(D_EXP + ALAT)) u_num (.clk(clk), .rst_n(rst_n), .d(num_in), .q(num_d));
            wire [ALAT:0] vdn;
            ot_hdc_vline #(.D(ALAT)) u_vdn (.clk(clk), .rst_n(rst_n), .v(vs[D_EXP]), .vd(vdn));
            ot_hdc_v41x_fdiv u_div (.clk(clk), .rst_n(rst_n), .v(vdn[ALAT]), .a(num_d), .b(den), .y(y_div), .vo(),
                                    .fault(f_div));
            wire [6:0] sel;
            assign sel = {ci_sfu == SFU_EGATE, ci_sfu == SFU_SPSQRT, ci_sfu == SFU_SQRT, ci_sfu == SFU_RSQRT,
                          is_sig, is_exp, ci_sfu == SFU_NONE};
            if (FULL != 0) begin : g_full
                ot_hdc_v41x_ins #(.W(T4W), .K(7),
                    .DEPTHS({H_EG, H_SP, H_SQRT, H_RSQ, H_SIG, H_EXP, 16'd0}), .DMAX(D_SP)) u_l4 (
                    .clk(clk), .rst_n(rst_n), .v(v3), .sel(sel), .d({R, r_b, r_c, r_o}), .vo(v4), .q(t4), .coll(c4), .busy());
            end else begin : g_vec
                ot_hdc_v41x_ins #(.W(T4W), .K(3), .DEPTHS({H_SIG, H_EXP, 16'd0}), .DMAX(D_SIG)) u_l4 (
                    .clk(clk), .rst_n(rst_n), .v(v3), .sel(sel[2:0]), .d({R, r_b, r_c, r_o}), .vo(v4), .q(t4),
                    .coll(c4), .busy());
            end
            assign S = (cs_sfu == SFU_EXP) ? y_exp : (cs_sfu == SFU_SIGM || cs_sfu == SFU_SILU) ? y_div :
                       (cs_sfu == SFU_NONE) ? t4[T4W-1 -: 32] : side_y;
            assign f_sfu = f_e | f_den | f_div;
        end else begin : g_nosfu
            assign t4 = {R, r_b, r_c, r_o}; assign v4 = v3; assign c4 = 1'b0;
            assign S = R; assign f_sfu = 1'b0;
        end
    endgenerate
    assign side_v = (FULL != 0) && v3 && (ci_sfu == SFU_RSQRT || ci_sfu == SFU_SQRT || ci_sfu == SFU_SPSQRT ||
                                          ci_sfu == SFU_EGATE);
    assign side_x = R;
    wire [31:0] s_b = t4[T4W-33 -: 32], s_c = t4[T4W-65 -: 32];
    wire [AW-1:0] s_o = t4[AW-1:0];
    // ---- E1 -------------------------------------------------------------------------------------------------
    wire [31:0] e1m, e1a, e1_byp;
    wire f_e1m, f_e1a;
    ot_hdc_qmul_lat #(MLAT) u_e1m (clk, rst_n, v4 && (cs_e1 == E1_MULC || cs_e1 == E1_MULIMM), S,
                       (cs_e1 == E1_MULC) ? s_c : cs_imm2, e1m, f_e1m);
    wire [31:0] e1a3;
    ot_hdc_qadd_lat #(.KEEP(K), .LAT(ALAT)) u_e1a (clk, rst_n, v4 && (cs_e1 == E1_ADDC || cs_e1 == E1_ADDIMM), S,
                       (cs_e1 == E1_ADDC) ? s_c : cs_imm2, e1a3, f_e1a);
    // E1 is MLAT deep (its multiply); the 3-cycle add waits MLAT - 3 more
    ot_hdc_delay #(.W(32), .D(MLAT - ALAT)) u_e1ad (.clk(clk), .rst_n(rst_n), .d(e1a3), .q(e1a));
    wire [31:0] e_b;
    wire [AW-1:0] e_o;
    wire [2:0]  e_e1;
    ot_hdc_delay #(.W(32 * 2 + AW + 3), .D(MLAT)) u_d5 (.clk(clk), .rst_n(rst_n), .d({S, s_b, s_o, cs_e1}),
                                                   .q({e1_byp, e_b, e_o, e_e1}));
    wire [MLAT:0] v5l;
    ot_hdc_vline #(.D(MLAT)) u_v5 (.clk(clk), .rst_n(rst_n), .v(v4), .vd(v5l));
    wire v5 = v5l[MLAT];
    wire [31:0] T = (e_e1 == E1_MULC || e_e1 == E1_MULIMM) ? e1m : (e_e1 == E1_ADDC || e_e1 == E1_ADDIMM) ? e1a :
                    e1_byp;
    // ---- E2 ---------------------------------------------------------------------------------------------------
    wire [31:0] e2m, e2_byp;
    wire f_e2;
    ot_hdc_qmul_lat #(MLAT) u_me2 (clk, rst_n, v5 && ce_e2 != E2_BYP, T, (ce_e2 == E2_MULB) ? e_b : ce_imm1, e2m, f_e2);
    wire [AW-1:0] u_o;
    wire [1:0]  u_e2;
    ot_hdc_delay #(.W(32 + AW + 2), .D(MLAT)) u_d6 (.clk(clk), .rst_n(rst_n), .d({T, e_o, ce_e2}),
                                               .q({e2_byp, u_o, u_e2}));
    wire [MLAT:0] v6l;
    ot_hdc_vline #(.D(MLAT)) u_v6 (.clk(clk), .rst_n(rst_n), .v(v5), .vd(v6l));
    wire v6 = v6l[MLAT];
    wire [31:0] U = (u_e2 == E2_BYP) ? e2_byp : e2m;
    // ---- OUT --------------------------------------------------------------------------------------------------
    // bf16(U) = (U[31:16] + inc) << 16, inc = U[15] & (U[16] | U[14:0] != 0): round to nearest even.  The KV
    // write is bf16(out) = bf16(U) whether or not out was rounded (bf16 of a BF16 value is itself)
    wire [15:0] u_hi1;
    ot_hdc_kinc #(.W(16), .K(K)) u_rnd (.a(U[31:16]), .inc(U[15] & (U[16] | (|U[14:0]))), .y(u_hi1));
    wire [31:0] u_bf = {u_hi1, 16'd0};
    wire [31:0] out = co_rnd ? u_bf : U;
    reg         ov_r;
    reg  [31:0] o_x;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin vm_we <= 1'b0; kv_we <= 1'b0; ov_r <= 1'b0; end
        else begin
            vm_we <= v6 && co_dst == DST_VM;
            kv_we <= v6 && (co_dst == DST_KV || co_dst == DST_KVT);
            ov_r <= v6;
        end
    end
    always @(posedge clk) begin
        vm_waddr <= u_o; vm_wdata <= out;
        kv_waddr <= u_o; kv_wdata <= u_bf;
        o_x <= out;
    end
    assign ro_v = ov_r;
    assign ro_x = o_x;
    // ---- status ---------------------------------------------------------------------------------------------------
    reg fault_r;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) fault_r <= 1'b0;
        else fault_r <= f_m1 | f_d1 | f_m2 | f_q | f_ad | f_sfu | f_e1m | f_e1a | f_e2;
    end
    assign fault = fault_r;
    assign coll = c1 | c4;
endmodule
