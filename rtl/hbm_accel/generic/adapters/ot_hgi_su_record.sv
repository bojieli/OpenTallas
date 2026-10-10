`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HGI-1 SU record adapter (hgi-adapters, 2026-10-09).  Unit 2 (SU.VOP) of the normative sequencer dispatch
// (ot_hgi_seq v1.0: d_hdr, d_sut, effective d_desc {I,R,O,D,C,B,A}, d_n) onto the stream unit's EXISTING op port:
// the vec campaign op word (tools/rtl_hdc_v41x_vec_campaign.py PFIELDS up to ch_mul, 670 bits; the ABI the DS / Qwen
// SU programs already use, tools/qwen_r25_decode_program.py "vec_campaign_PFIELDS"), consumed by ot_hdc_v41x_vec.
// Decode + handshake only: no arithmetic, no data path.
//
// Mapping (spec 6.6 / 6.9; semantics tools/hgi_sim/machine.py u_su_vop = Machine.su1 over descriptors):
//   nout = A.m, nin = effective n of A (d_n[A]); every SUT pipeline field verbatim (a_ind, b_half, c_pair, a_rnd,
//   a_relu, a_min, c_clip, m1, m2, qm, ad, sfu, e1, e2, rnd, dst, red, red_sq, red_whole, red_tree, red_rnd, imm1-3);
//   X in {A,B,C,D,O}: Xbase = X effective base, Xso = X.stride, Xsi = 0 if X.ibcast else (X.istride or 1) (24-bit
//   VM word arithmetic, as the unit's AW); aibase = I effective base; rbase = R effective base, rso = R.stride or 1;
//   sources from VM (src 0); orow 0; ch_src 0 (no vector chaining: spec 4.1 orders records within a unit).
// Fail-closed refusals (rec_fault, sticky halt): unit != 2 or op != 0, no template, SUT reserved bits 255:142 != 0,
//   su_vec != 0, any present operand not in VM space, a source field != VM, an operand the template reads that is
//   absent (A always; B: m1 AB / DIVB / MAXB, ad NEGB, e2 MULB; C (unless c_pair: C = A[i XOR 1]): m2 C, qm != OFF, ad Q / C, e1 MULC / ADDC;
//   D: qm != OFF, ad D; I: a_ind != NONE; O: dst VM; R: red != NONE), dst KV / KVT (no KV SRAM on the HBM die),
//   a_ind 3, nout or nin >= 2^16.  An op with nout = 0 or nin = 0 retires at once (Machine.su1 returns).
// Ordering (spec 4.1): op k+1 is issued only after op k has made its writes visible (the unit's `idle`: every element
//   write and reducer result landed); the station decodes op k+1 meanwhile.  Retire = that idle (the unit's real
//   completion); a unit fault seen while the op runs retires it with rec_fault and halts (sticky until rst_n).
// Latency: record accept edge E0 -> decoded word registered E1 -> op_v; the unit accepts at E2 (2 edges); retire
//   1 edge after the unit's idle.  DS lockstep identity: hgi_en = 0 (static strap) connects the legacy op port
//   (lg_*) straight to the unit port, combinationally (no added flop): the DS control path is cycle-identical.  The
//   routed adapter is LEGACY = 0 (registered boundary); the static strap mux sits in front of the unit wrapper's pin
//   register on the die (0 cycles).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_su_record #(
    parameter integer MUT_ISTRIDE = 0,     // mutant: Xsi = istride (no 0 -> 1, no ibcast)
    parameter integer MUT_EARLY = 0,       // mutant: retire on the unit's accept, not on its completion
    parameter integer GLU = 0,             // 1: the SFU form (unit 3 SFU.GLU decoded as its one vec op; ot_hgi_sfu_record)
    parameter integer LEGACY = 1           // 1: the static legacy pass-through mux (die wrapper / bench); 0: the routed
                                           //    adapter alone (records only, every output from a register; hgi_en unused)
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          hgi_en,          // static: 1 = records drive the unit, 0 = the legacy op port does
    // record (unit 2 of the sequencer dispatch)
    input  wire          rec_v,
    output wire          rec_rdy,
    input  wire [127:0]  rec_hdr,
    input  wire [255:0]  rec_sut,
    input  wire [255:0]  rec_a, rec_b, rec_c, rec_d, rec_o, rec_r, rec_i,
    input  wire [20:0]   rec_n_a,
    output reg           rec_done,
    output reg           rec_fault,
    output wire          halted,
    output wire          drained,         // no record held, decoded or executing
    // legacy op port (the DS control path)
    input  wire          lg_v,
    output wire          lg_rdy,
    input  wire [669:0]  lg_w,
    // the stream unit's op port (ot_hdc_v41x_vec go / ready / i_* in PFIELDS order) and its status
    output wire          op_v,
    input  wire          op_rdy,
    output wire [669:0]  op_w,
    input  wire          su_idle,
    input  wire          su_fault
);
    // ---- PFIELDS offsets (tools/rtl_hdc_v41x_vec_campaign.py)
    localparam integer F_NOUT = 0, F_NIN = 16, F_ASRC = 32, F_BSRC = 34, F_CSRC = 36, F_DSRC = 38, F_ABASE = 40,
        F_ASO = 64, F_ASI = 88, F_AIBASE = 112, F_AIND = 136, F_BBASE = 138, F_BSO = 162, F_BSI = 186, F_BHALF = 210,
        F_CBASE = 211, F_CSO = 235, F_CSI = 259, F_CPAIR = 283, F_DBASE = 284, F_DSO = 308, F_DSI = 332, F_ARND = 356,
        F_ARELU = 357, F_AMIN = 358, F_CCLIP = 359, F_M1 = 360, F_M2 = 363, F_QM = 365, F_AD = 368, F_SFU = 371,
        F_E1 = 374, F_E2 = 377, F_RND = 379, F_DST = 380, F_OBASE = 382, F_OSO = 406, F_OSI = 430, F_OROW = 454,
        F_RED = 478, F_REDSQ = 480, F_REDWHOLE = 481, F_REDTREE = 482, F_REDRND = 483, F_RBASE = 484, F_RSO = 508,
        F_IMM1 = 532, F_IMM2 = 564, F_IMM3 = 596, F_CH_SRC = 628;
    // ---- ISA codes (tools/hdc_isa_v41.py)
    localparam [2:0] M1_AB = 3'd1, M1_DIVB = 3'd5, M1_MAXB = 3'd6;
    localparam [1:0] M2_C = 2'd1;
    localparam [2:0] AD_Q = 3'd1, AD_C = 3'd2, AD_NEGB = 3'd3, AD_D = 3'd5;
    localparam [2:0] E1_MULC = 3'd1, E1_ADDC = 3'd2;
    localparam [1:0] E2_MULB = 2'd1;

    // ---- station: raw record (E0), decoded word (E1)
    reg          raw_v, dec_v, exec, halt_q, el_seen;
    reg  [1:0]   exec_ph;                 // edges since the unit accepted (idle is stale for 2 edges)
    reg  [127:0] hdr_q;
    reg  [255:0] sut_q, a_q, b_q, c_q, d_q, o_q, r_q, i_q;
    reg  [20:0]  na_q;
    reg  [669:0] w_q;
    reg          nop_q, bad_q;
    reg          in_idle, in_fault;
    always @(posedge clk) begin in_idle <= su_idle; in_fault <= su_fault; end

    assign halted  = halt_q;
    assign drained = !raw_v && !dec_v && !exec;
    wire   hen     = LEGACY ? hgi_en : 1'b1;
    assign rec_rdy = hen && !raw_v && !dec_v && !halt_q;
    assign op_v    = hen ? (dec_v && !nop_q && !bad_q && !exec && !halt_q) : lg_v;
    assign op_w    = hen ? w_q : lg_w;
    assign lg_rdy  = !hen && op_rdy;

    // ---- decode (combinational from the raw station)
    // SFU.GLU as the vec op (GLU = 1): A = gate (a_min L), C = up (record B, c_clip L), B = route weight (record C);
    // SUT: a_min, c_clip, SFU SILU, E1 MULC, E2 MULB, rnd if O BF16, dst VM, imm3 = imm_a (L)
    wire [255:0] glu_sut = (256'd1 << 14) | (256'd1 << 15) | (256'd5 << 27) | (256'd1 << 30) | (256'd1 << 33) |
                           ({255'd0, o_q[4:2] == 3'd1} << 35) | (256'd1 << 36) | ({224'd0, hdr_q[63:32]} << 110);
    wire [6:0]  ropnd = hdr_q[99:93];
    wire        glu_bad = GLU && ((hdr_q[127:124] != 4'd3) || (hdr_q[123:118] != 6'd0) || hdr_q[92] ||
                                  ((ropnd & 7'b0010111) != 7'b0010111) || (o_q[4:2] != 3'd0 && o_q[4:2] != 3'd1));
    wire [6:0] opnd = GLU ? 7'b0010111 : ropnd;
    wire [255:0] sut_e = GLU ? glu_sut : sut_q;
    wire pa = opnd[0], pb = opnd[1], pc = opnd[2], pd = opnd[3], po = opnd[4], pr = opnd[5], pi = opnd[6];
    wire [1:0] a_src = sut_e[1:0], a_ind = sut_e[3:2], b_src = sut_e[5:4], c_src = sut_e[8:7], d_src = sut_e[11:10];
    wire       b_half = sut_e[6], c_pair = sut_e[9], a_rnd = sut_e[12], a_relu = sut_e[13], a_min = sut_e[14],
               c_clip = sut_e[15];
    wire [2:0] m1 = sut_e[18:16], qm = sut_e[23:21], ad = sut_e[26:24], sfu = sut_e[29:27], e1 = sut_e[32:30];
    wire [1:0] m2 = sut_e[20:19], e2 = sut_e[34:33], dst = sut_e[37:36], red = sut_e[39:38], su_vec = sut_e[44:43];
    wire       rnd = sut_e[35], red_sq = sut_e[40], red_whole = sut_e[41], red_rnd = sut_e[42], red_tree = sut_e[45];
    wire [31:0] imm1 = sut_e[77:46], imm2 = sut_e[109:78], imm3 = sut_e[141:110];
    wire use_b = (m1 == M1_AB) || (m1 == M1_DIVB) || (m1 == M1_MAXB) || (ad == AD_NEGB) || (e2 == E2_MULB);
    wire use_c = !c_pair && ((m2 == M2_C) || (qm != 3'd0) || (ad == AD_Q) || (ad == AD_C) || (e1 == E1_MULC) ||
                              (e1 == E1_ADDC));      // c_pair: C is A's pair element, not an operand
    wire use_d = (qm != 3'd0) || (ad == AD_D);
    function automatic not_vm(input p, input [255:0] d); not_vm = p && (d[1:0] != 2'd1); endfunction
    function automatic [23:0] isi(input [255:0] d);
        isi = MUT_ISTRIDE ? {8'd0, d[135:120]} : (d[5] ? 24'd0 : (d[135:120] == 16'd0) ? 24'd1 : {8'd0, d[135:120]});
    endfunction
    wire [19:0] nout = a_q[87:68];
    wire bad = glu_bad || (!GLU && ((hdr_q[127:124] != 4'd2) || (hdr_q[123:118] != 6'd0) || !hdr_q[92])) || (|sut_e[255:142]) ||
               (su_vec != 2'd0) || !pa ||
               not_vm(pa, a_q) || not_vm(pb, b_q) || not_vm(pc, c_q) || not_vm(pd, d_q) || not_vm(po, o_q) ||
               not_vm(pr, r_q) || not_vm(pi, i_q) ||
               (a_src != 2'd0) || (b_src != 2'd0) || (c_src != 2'd0) || (d_src != 2'd0) ||
               (use_b && !pb) || (use_c && !pc) || (use_d && !pd) ||
               (a_ind == 2'd3) || (a_ind != 2'd0 && !pi) ||
               (dst == 2'd2) || (dst == 2'd3) || (dst == 2'd1 && !po) || (red != 2'd0 && !pr) ||
               (|nout[19:16]) || (|na_q[20:16]);
    wire nop = (nout == 20'd0) || (na_q == 21'd0);
    wire [669:0] w_dec = {
        16'd0, 16'd0, 8'd0, 2'd0,                                            // ch_mul, ch_lead, ch_seq, ch_src
        imm3, imm2, imm1,
        (r_q[119:88] == 32'd0) ? 24'd1 : r_q[111:88], r_q[31:8],             // rso, rbase
        red_rnd, red_tree, red_whole, red_sq, red,
        24'd0, isi(o_q), o_q[111:88], o_q[31:8],                              // orow, osi, oso, obase
        dst, rnd, e2, e1, sfu, ad, qm, m2, m1, c_clip, a_min, a_relu, a_rnd,
        isi(d_q), d_q[111:88], d_q[31:8],                                      // dsi, dso, dbase
        c_pair, isi(c_q), c_q[111:88], c_q[31:8],                              // cpair, csi, cso, cbase
        b_half, isi(b_q), b_q[111:88], b_q[31:8],                              // bhalf, bsi, bso, bbase
        a_ind, i_q[31:8], isi(a_q), a_q[111:88], a_q[31:8],                    // aind, aibase, asi, aso, abase
        2'd0, 2'd0, 2'd0, 2'd0,                                                // dsrc, csrc, bsrc, asrc
        na_q[15:0], nout[15:0]};

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            raw_v <= 1'b0; dec_v <= 1'b0; exec <= 1'b0; halt_q <= 1'b0; el_seen <= 1'b0; exec_ph <= 2'd0;
            rec_done <= 1'b0; rec_fault <= 1'b0; nop_q <= 1'b0; bad_q <= 1'b0; w_q <= 670'd0;
            hdr_q <= 128'd0; sut_q <= 256'd0; a_q <= 256'd0; b_q <= 256'd0; c_q <= 256'd0; d_q <= 256'd0;
            o_q <= 256'd0; r_q <= 256'd0; i_q <= 256'd0; na_q <= 21'd0;
        end else begin
            rec_done <= 1'b0; rec_fault <= 1'b0;
            // pin flops: the record bus lands unconditionally (no enable fanout from the rec_v pin); raw_v marks the
            // accepted record, decoded at the next edge
            hdr_q <= rec_hdr; sut_q <= rec_sut; a_q <= rec_a; b_q <= GLU ? rec_c : rec_b; c_q <= GLU ? rec_b : rec_c;
            d_q <= rec_d; o_q <= rec_o; r_q <= rec_r; i_q <= rec_i; na_q <= rec_n_a;
            if (rec_v && rec_rdy) raw_v <= 1'b1;
            if (raw_v) begin                                  // E1: the decoded word
                raw_v <= 1'b0; dec_v <= 1'b1; w_q <= w_dec; nop_q <= nop; bad_q <= bad;
            end
            // a refusal or an empty op retires in order: only once the op ahead of it has retired
            if (dec_v && !exec && !halt_q && (bad_q || nop_q)) begin
                dec_v <= 1'b0;
                if (bad_q) begin rec_fault <= 1'b1; halt_q <= 1'b1; end else rec_done <= 1'b1;
            end
            if (op_v && op_rdy && hen) begin                // the unit took the op
                dec_v <= 1'b0; exec <= 1'b1; exec_ph <= 2'd0; el_seen <= 1'b0;
                if (MUT_EARLY) begin rec_done <= 1'b1; exec <= 1'b0; end
            end else if (exec) begin
                if (exec_ph != 2'd3) exec_ph <= exec_ph + 2'd1;
                if (in_fault) begin rec_fault <= 1'b1; halt_q <= 1'b1; exec <= 1'b0; end
                else if (exec_ph == 2'd3 && in_idle) begin rec_done <= 1'b1; exec <= 1'b0; end
            end
        end
    end
endmodule
`default_nettype wire
