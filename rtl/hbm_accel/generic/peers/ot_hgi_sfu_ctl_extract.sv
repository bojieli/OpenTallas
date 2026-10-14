`timescale 1ns/1ps
// Opt-in actual c12 controller extraction; not a native VM/cache qualification.
// Original issue/setup/control pipes retained; no original CLOSED source edited.
module ot_hgi_sfu_ctl_extract #(
    parameter integer ENABLE_NATIVE = 0,
    parameter integer SPLIT_S_PIPE = 0,
    parameter integer N  = 16,          // light lanes (elements a cycle), a power of two >= 8
    parameter integer M  = 16,          // SFU lanes, a power of two, 8 <= M <= N
    parameter integer LV = 6,           // reducer time levels, 1..7 (l_in is 3 bits; elaboration fails otherwise)
    parameter integer AW = 24,
    parameter integer NW = 16,
    parameter integer KVT_SH = 9,
    parameter integer BCAST_STAGES = 1, // register stages of the pipelined controller -> lane broadcast tree
    parameter integer RET_STAGES = 5,   // register stages of the lane / reducer -> vector-memory write path
    parameter integer MLAT = 6,         // multiplier latency (ot_hdc_qmul_lat): 3, 4 or 5 (W11 serial domain)
    parameter integer ALAT = 6,         // FP add latency (ot_hdc_qadd_lat): 3, or 4 (input cut); ALAT <= MLAT
    parameter integer OPR = 1,          // c12: lane operand registers (M1, AD, E1) and gather word register
    parameter integer DDIV = 21,        // c12: divider depth (21: ot_dsrom_fdiv_f12)
    parameter integer SIDEX = 4,        // c12: side pipe port registers (0 or 3)
    parameter integer FSQ = 0,          // c12: ot_hdc_fsqrt_c12 in the side pipe
    parameter integer RPAD = 0,         // c12 reducer: padding register
    parameter integer CAPR = 1,         // c12: lane memory-word port register (every fetch CAPR deeper)
    parameter integer RSL = 0,          // c12 reducer: slice-boundary register
    parameter integer RTAP = 0,         // c12 reducer: tap register
    parameter integer ROUT = 0,         // c12 reducer: OUT input register
    parameter integer RSLICE = 64,      // c12 reducer: lanes a slice
    parameter integer ROPI = 0,         // reducer operand stage, default off
    parameter integer RKC = 0,          // reducer kept driver copies, default off
    parameter integer RHALF = 0,        // phase-locked half-rate reducer, default off
    parameter integer RHPAR = 0,        // controller issue parity; reducer locks to first beat
    parameter integer CTL12 = 2,        // c12 controller: pipelined set-up, registered emit-loop conditions
    // CLAUDE HBM-ABSTRACTS hub margin (2026-10-06, default off): see rtl/hdc/v41x/ot_hdc_v41x_vec_lane_c12.sv
    parameter integer GSH = 1,          // lanes register the gather word's shift: every gather fetch one deeper
    parameter integer KIMM = 1,         // imm3 travels to the lanes as its order key okey(imm3)
    parameter integer DENR = 1,         // lanes register the sigmoid denominator operand: sigmoid / SiLU one deeper
    parameter integer SFUT = 0,         // el1011-hbm-sfu: lanes' sigmoid chain as a registered sub-tile: exp / sigmoid / SiLU +2
    parameter integer DRING = 3         // lanes' SFU delay lines as ring buffers (0 cycles)
) (
    input  wire              clk,
    input  wire              rst_n,
    input wire clk_s_ops_lo,clk_s_ops_hi,clk_s_meta_lo,clk_s_meta_hi,
    input  wire              go,
    output wire              ready,
    output reg               idle,
    // ---- instruction (DYN already added to the bases and counts)
    input  wire [NW-1:0]     i_nout, i_nin,
    input  wire [1:0]        i_asrc, i_bsrc, i_csrc, i_dsrc,
    input  wire [AW-1:0]     i_abase, i_aso, i_asi, i_aibase,
    input  wire [1:0]        i_aind,
    input  wire [AW-1:0]     i_bbase, i_bso, i_bsi,
    input  wire              i_bhalf,
    input  wire [AW-1:0]     i_cbase, i_cso, i_csi,
    input  wire              i_cpair,
    input  wire [AW-1:0]     i_dbase, i_dso, i_dsi,
    input  wire              i_arnd, i_arelu, i_amin, i_cclip,
    input  wire [2:0]        i_m1,
    input  wire [1:0]        i_m2,
    input  wire [2:0]        i_qm, i_ad, i_sfu, i_e1,
    input  wire [1:0]        i_e2,
    input  wire              i_rnd,
    input  wire [1:0]        i_dst,
    input  wire [AW-1:0]     i_obase, i_oso, i_osi, i_orow,
    input  wire [1:0]        i_red,
    input  wire              i_redsq, i_redwhole, i_redtree, i_redrnd,
    input  wire [AW-1:0]     i_rbase, i_rso,
    input  wire [31:0]       i_imm1, i_imm2, i_imm3,
    // ---- chaining (see the protocol above)
    input  wire [1:0]        i_ch_src,
    input  wire [7:0]        i_ch_seq,
    input  wire [15:0]       i_ch_lead,
    input  wire [15:0]       i_ch_mul,
    input  wire [7:0]        x_seq, x_dseq,
    input  wire [15:0]       x_cnt,
    output reg  [7:0]        cr_seq, cr_dseq, cr_rseq,
    output wire [15:0]       cr_cnt,
    // ---- per lane: element writes
    output wire [N-1:0]      vm_we,
    output wire [N*AW-1:0]   vm_waddr,
    output wire [N*32-1:0]   vm_wdata,
    output wire [N-1:0]      kv_we,
    output wire [N*AW-1:0]   kv_waddr,
    output wire [N*32-1:0]   kv_wdata,
    // ---- reduction results (to the vector memory)
    output wire [N/8-1:0]    res_we,
    output wire [N/8*AW-1:0] res_addr,
    output wire [N/8*32-1:0] res_data,
    // ---- status
    output reg               fault,          // an arithmetic refusal or a configuration the unit cannot run
    output reg               order_fault,    // an internal ordering violation (never, by construction)
    output reg  [15:0]       emitted,        // vectors emitted since reset (bench)
    output reg               retire_o,       // a vector retired this cycle (bench)
    output wire              dbg_emit,       // this cycle: a vector of op dbg_eseq is emitted
    output wire [7:0]        dbg_eseq,
    output wire              dbg_ret,        // this cycle: a vector of op dbg_rseq retires (writes)
    output wire [7:0]        dbg_rseq,
    output wire              dbg_res,        // this cycle: results of op dbg_sseq are written
    output wire [7:0]        dbg_sseq,
    output wire [1741:0]     grid_control,
    input wire [N-1:0] l_fault, l_coll, l_rov, l_vm_we, l_kv_we,
    input wire [N*32-1:0] l_rox, l_vm_wdata, l_kv_wdata,
    input wire [N*AW-1:0] l_vm_waddr, l_kv_waddr,
    output reg admission_fault
);
    initial begin
        if (N != 16 || M != 16 || AW != 24 || BCAST_STAGES != 1 || RET_STAGES != 5 ||
            MLAT != 6 || ALAT != 6 || OPR != 1 || DDIV != 21 || CAPR != 1 ||
            GSH != 1 || KIMM != 1 || DENR != 1 || SFUT != 0 || DRING != 3)
            $fatal(1, "SFU controller extraction requires exact CLOSED lane and mapper params");
    end
    // LV is bounded by the 3-bit TIME-level field (l_in): an LV above 7 would let an 8-level segment pass
    // the controller's c_L > LV check and be clamped to 7 levels, a silently wrong sum.  Fail closed at
    // elaboration: the trap instantiates a module that does not exist, which Verilator (even under
    // -Wno-fatal), Icarus and Yosys (hierarchy -check, as synth runs it) all reject.
    generate if (LV < 1 || LV > 7) begin : g_lv_out_of_range
        ot_hdc_v41x_vec_LV_must_be_1_to_7 u_trap ();
    end endgenerate

    localparam integer LN = $clog2(N);
    localparam integer LM = $clog2(M);
    localparam integer NR = N / 8;
    localparam integer CW = 24;
    // this unit's own consumers read BCAST_STAGES after their emit: their credits lead the landing by that much
    localparam integer DI = (RET_STAGES > BCAST_STAGES) ? RET_STAGES - BCAST_STAGES : 0;
    localparam [1:0] IND_NONE = 0, IND_I = 1, IND_O = 2;
    localparam [1:0] DST_NONE = 0, DST_KVT = 3;
    localparam [2:0] M1_DIVB = 4, M1_DIVIMM = 5;
    localparam [2:0] QM_ALT_NP = 3, QM_ALT_PN = 4;
    localparam [2:0] SFU_NONE = 0, SFU_EXP = 1, SFU_RSQRT = 2, SFU_SQRT = 3, SFU_SIGM = 4, SFU_SILU = 5,
                     SFU_SPSQRT = 6, SFU_EGATE = 7;
    localparam [1:0] RED_NONE = 0, RED_MAX = 2;
    localparam [1:0] CH_NONE = 0, CH_SELF = 1, CH_RES = 2, CH_EXT = 3;

    function automatic [4:0] log2c(input [31:0] x);     // ceil(log2 x), x >= 1
        integer b;
        begin
            log2c = 0;
            for (b = 0; b < 32; b = b + 1) if ((32'd1 << b) < x) log2c = b + 1;
        end
    endfunction
    function automatic [4:0] log2f(input [31:0] x);     // floor(log2 x), x >= 1
        integer b;
        begin
            log2f = 0;
            for (b = 0; b < 32; b = b + 1) if (x[b]) log2f = b;
        end
    endfunction
    function automatic [4:0] tzero(input [CW-1:0] x);   // trailing zeros (x > 0)
        integer b;
        begin
            tzero = 0;
            for (b = CW - 1; b >= 0; b = b - 1) if (x[b]) tzero = b;
        end
    endfunction
    function automatic pow2(input [AW-1:0] x);
        pow2 = (x != 0) && ((x & (x - 1)) == 0);
    endfunction
    // S-stage depths (ot_hdc_v41x_vec_lane / _side): exp 7 MLAT + 8 ALAT + 4, sigmoid exp + ALAT + 19, rsqrt
    // 1 + 9 MLAT + 3 ALAT, sqrt 31, sqrt(softplus) exp + 11 MLAT + 10 ALAT + 50, gate 33 + sigmoid
    localparam integer D_EXP = 7 * MLAT + 8 * ALAT + 4, D_SIG0 = D_EXP + ALAT + DDIV, D_SIG = D_SIG0 + DENR + 2 * SFUT, D_EXPL = D_EXP + 2 * SFUT,
                       D_RSQ = 1 + 9 * MLAT + 3 * ALAT + SIDEX, D_SQRT = 31 + SIDEX,
                       D_SP = D_EXP + 11 * MLAT + 10 * ALAT + 31 + DDIV + SIDEX, D_EG = 33 + D_SIG0 + SIDEX;
    localparam [15:0] H_A = ALAT;
    localparam [15:0] H_R = ALAT + ROPI;                        // a reducer TREE / TIME level
`ifdef OT_NEG_DDIV_DEPTH
    // Negative control: M1 divide retires one cycle before its result.
    localparam [15:0] H_F5 = 5 + OPR + CAPR + GSH, H_F3 = 3 + CAPR, H_MD = DDIV + OPR - 1, H_MM = MLAT + OPR;   // gather fetch, M1 divide / multiply
`else
    localparam [15:0] H_F5 = 5 + OPR + CAPR + GSH, H_F3 = 3 + CAPR, H_MD = DDIV + OPR, H_MM = MLAT + OPR;   // gather fetch, M1 divide / multiply
`endif
`ifdef OT_NEG_SIG_DEPTH
    // Negative control (tput-fix-1011): the sigmoid / SiLU stage retires one cycle before its result.
    localparam [15:0] H_M = MLAT, H_EXP = D_EXPL, H_SIG = D_SIG - 1, H_RSQ = D_RSQ, H_SQRT = D_SQRT, H_SP = D_SP,
                      H_EG = D_EG;
`else
    localparam [15:0] H_M = MLAT, H_EXP = D_EXPL, H_SIG = D_SIG, H_RSQ = D_RSQ, H_SQRT = D_SQRT, H_SP = D_SP,
                      H_EG = D_EG;
`endif
    function automatic [9:0] sfu_d(input [2:0] s);
        case (s)
            SFU_EXP: sfu_d = D_EXPL;
            SFU_SIGM, SFU_SILU: sfu_d = D_SIG;
            SFU_RSQRT: sfu_d = D_RSQ;
            SFU_SQRT: sfu_d = D_SQRT;
            SFU_SPSQRT: sfu_d = D_SP;
            SFU_EGATE: sfu_d = D_EG;
            default: sfu_d = 0;
        endcase
    endfunction

    // =========================================================================================
    // Set-up: accepted op -> S1 (flatten test) -> S2 (layout, depths, offset terms) -> lanes'
    // offset bank -> pending, ready to start
    // =========================================================================================
    reg  [1:0]  pst;                     // 0 empty, 1 S1, 2 S2 done (lanes load), 3 ready
    wire instruction_supported = i_red == RED_NONE && i_asrc == 0 && i_bsrc == 0 && i_csrc == 0 && i_dsrc == 0 && (i_dst == DST_NONE || i_dst == 2'd1) &&
        (i_sfu == SFU_NONE || i_sfu == SFU_EXP || i_sfu == SFU_SIGM || i_sfu == SFU_SILU);
    assign ready = ENABLE_NATIVE && (pst == 2'd0) && instruction_supported;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) admission_fault <= 1'b0;
        else if (ENABLE_NATIVE && go && !instruction_supported) admission_fault <= 1'b1;
    wire accept = go && ready;
    // CTL12 >= 2: the loop / set-up control of register group g (KC kept copies); otherwise the one control
    localparam integer KC = 26;
    wire [KC-1:0] PROM, EMIT, WRAPS, STRT, ACC, LAST, AVC;
    localparam integer KK = (CTL12 >= 2) ? 1 : 0;      // kept-prefix adders / compares
    // raw fields
    reg [NW-1:0] q_nout, q_nin;
    reg [1:0]    q_asrc, q_bsrc, q_csrc, q_dsrc, q_aind, q_dst, q_red, q_m2, q_e2;
    reg [AW-1:0] q_abase, q_aso, q_asi, q_aibase, q_bbase, q_bso, q_bsi, q_cbase, q_cso, q_csi,
                 q_dbase, q_dso, q_dsi, q_obase, q_oso, q_osi, q_orow, q_rbase, q_rso;
    reg          q_bhalf, q_cpair, q_arnd, q_arelu, q_amin, q_cclip, q_rnd, q_redsq, q_redwhole, q_redtree, q_redrnd;
    reg [2:0]    q_m1, q_qm, q_ad, q_sfu, q_e1;
    reg [31:0]   q_imm1, q_imm2, q_imm3;
    reg [1:0]    q_chsrc;
    reg [7:0]    q_chseq, q_seq, seq_ctr;
    reg [15:0]   q_chlead, q_chmul;
    reg          q_bank, nbank;
    always @(posedge clk) if (ACC[17]) begin q_nout <= i_nout; q_nin <= i_nin; q_seq <= seq_ctr; q_bank <= nbank;
        q_asrc <= i_asrc; q_bsrc <= i_bsrc; q_csrc <= i_csrc; q_dsrc <= i_dsrc; q_aind <= i_aind; q_dst <= i_dst;
        q_red <= i_red; q_m2 <= i_m2; q_e2 <= i_e2; end
    always @(posedge clk) if (ACC[18]) begin q_abase <= i_abase; q_aso <= i_aso; q_asi <= i_asi; q_aibase <= i_aibase; end
    always @(posedge clk) if (ACC[19]) begin q_bbase <= i_bbase; q_bso <= i_bso; q_bsi <= i_bsi; q_cbase <= i_cbase; end
    always @(posedge clk) if (ACC[20]) begin q_cso <= i_cso; q_csi <= i_csi; q_dbase <= i_dbase; q_dso <= i_dso; end
    always @(posedge clk) if (ACC[21]) begin q_dsi <= i_dsi; q_obase <= i_obase; q_oso <= i_oso; q_osi <= i_osi; end
    always @(posedge clk) if (ACC[22]) begin q_orow <= i_orow; q_rbase <= i_rbase; q_rso <= i_rso;
        q_bhalf <= i_bhalf; q_cpair <= i_cpair; q_arnd <= i_arnd; q_arelu <= i_arelu; q_amin <= i_amin;
        q_cclip <= i_cclip; q_rnd <= i_rnd; q_redsq <= i_redsq; q_redwhole <= i_redwhole; q_redtree <= i_redtree;
        q_redrnd <= i_redrnd; q_m1 <= i_m1; q_qm <= i_qm; q_ad <= i_ad; q_sfu <= i_sfu; q_e1 <= i_e1; end
    always @(posedge clk) if (ACC[23]) begin q_imm1 <= i_imm1; q_imm2 <= i_imm2; q_imm3 <= i_imm3; end
    always @(posedge clk) if (ACC[24]) begin
        q_chsrc <= i_ch_src; q_chseq <= i_ch_seq; q_chlead <= i_ch_lead; q_chmul <= i_ch_mul; end

    // ---- S1: flatten test ------------------------------------------------------------------------
    wire [AW-1:0] ni_a = q_nin;
    wire [AW-1:0] ni_h = q_nin >> 1;
    wire s1_even = !q_nin[0];
    wire s1_cand = (q_red == RED_NONE) || q_redwhole || q_redtree;
    wire s1_ok = (q_aind == IND_NONE) && (q_dst != DST_KVT) &&
                 (s1_even || !(q_bhalf || q_qm == QM_ALT_NP || q_qm == QM_ALT_PN)) &&
                 (q_aso == ni_a * q_asi) &&
                 (q_bso == (q_bhalf ? ni_h : ni_a) * q_bsi) &&
                 (q_cpair || q_cso == ni_a * q_csi) &&
                 (q_dso == (q_bhalf ? ni_h : ni_a) * q_dsi) &&
                 (q_dst == DST_NONE || q_oso == ni_a * q_osi);
    reg          s_flat, s_wnf, s_flatbad;
    reg [CW-1:0] s_ni, s_no;
    reg [3:0]    sst;                    // CTL12: the set-up's sub-step while pst == 1
    // CTL12 stage A: the stride products (mod 2^AW) in two halves of the 16-bit count, registered
    reg [AW-1:0] pl_a, pl_b, pl_c, pl_d, pl_o, pl_n;
    reg [AW-9:0] ph_a, ph_b, ph_c, ph_d, ph_o, ph_n;
    wire [AW-1:0] f_h = q_bhalf ? ni_h : ni_a;
    always @(posedge clk) if (pst == 2'd1 && sst == 3'd0) begin
        pl_a <= ni_a[7:0] * q_asi; ph_a <= ni_a[15:8] * q_asi[AW-9:0];
        pl_b <= f_h[7:0] * q_bsi;  ph_b <= f_h[15:8] * q_bsi[AW-9:0];
        pl_c <= ni_a[7:0] * q_csi; ph_c <= ni_a[15:8] * q_csi[AW-9:0];
        pl_d <= f_h[7:0] * q_dsi;  ph_d <= f_h[15:8] * q_dsi[AW-9:0];
        pl_o <= ni_a[7:0] * q_osi; ph_o <= ni_a[15:8] * q_osi[AW-9:0];
        pl_n <= q_nout * q_nin[7:0]; ph_n <= q_nout * q_nin[15:8];
    end
    // CTL12 >= 2: S0 the products in 4-bit slices of the count (f * x mod 2^AW, kept-prefix adds), S1 their sums
    wire [AW-1:0] f_n = {{(AW-NW){1'b0}}, q_nout};
    // CTL12 >= 2: the slice sources registered at accept, one copy a stream (the half stream's count halved there)
    reg  [6*NW-1:0] fx_r;
    wire [NW-1:0]   fh_i = i_bhalf ? (i_nin >> 1) : i_nin;
    always @(posedge clk) if (ACC[17]) fx_r <= {i_nin, i_nin, fh_i, i_nin, fh_i, i_nin};
    wire [6*AW-1:0] f_x = (CTL12 >= 2) ? {{{(AW-NW){1'b0}}, fx_r[5*NW +: NW]}, {{(AW-NW){1'b0}}, fx_r[4*NW +: NW]},
                                          {{(AW-NW){1'b0}}, fx_r[3*NW +: NW]}, {{(AW-NW){1'b0}}, fx_r[2*NW +: NW]},
                                          {{(AW-NW){1'b0}}, fx_r[1*NW +: NW]}, {{(AW-NW){1'b0}}, fx_r[0 +: NW]}}
                                       : {{{(AW-NW){1'b0}}, q_nin}, ni_a, f_h, ni_a, f_h, ni_a};     // n, o, d, c, b, a
    wire [6*AW-1:0] m_x = {f_n, q_osi, q_dsi, q_csi, q_bsi, q_asi};
    wire [6*8*AW-1:0] pq_w;
    reg  [6*8*AW-1:0] pq_r;
    wire [6*AW-1:0] pr2_w, pqs_w, pqc_w;
    reg  [6*AW-1:0] pr2_r, pqs_r, pqc_r;      // S1: the slices' carry-save pair; S2: their sum
    genvar gx, gq;
    generate for (gx = 0; gx < 6; gx = gx + 1) begin : g_px
        // 2-bit slices: slice q is f[2q+1:2q] * x, weighted 4^q in the S1 sum
        for (gq = 0; gq < 8; gq = gq + 1) begin : g_pq
            ot_hdc_v41x_cmul2 #(.W(AW), .K(KK)) u_m (.f(f_x[gx*AW + 2*gq +: 2]), .x(m_x[gx*AW +: AW]),
                                                     .y(pq_w[(gx*8 + gq)*AW +: AW]));
        end
        ot_hdc_v41x_csa8 #(.W(AW)) u_c (.x(pq_r[gx*8*AW +: 8*AW]), .s(pqs_w[gx*AW +: AW]), .c(pqc_w[gx*AW +: AW]));
        wire unused_pc;
        ot_hdc_kadd #(.W(AW), .K(KK)) u_s (.a(pqs_r[gx*AW +: AW]), .b(pqc_r[gx*AW +: AW]), .cin(1'b0),
                                          .s(pr2_w[gx*AW +: AW]), .cout(unused_pc));
    end endgenerate
    always @(posedge clk) begin
        if (pst == 2'd1 && sst == 4'd0) pq_r <= pq_w;
        if (pst == 2'd1 && sst == 4'd1) begin pqs_r <= pqs_w; pqc_r <= pqc_w; end
        if (pst == 2'd1 && sst == 4'd2) pr2_r <= pr2_w;
    end
    wire [AW-1:0] pr_a = (CTL12 >= 2) ? pr2_r[0*AW +: AW] : pl_a + {ph_a, 8'd0};
    wire [AW-1:0] pr_b = (CTL12 >= 2) ? pr2_r[1*AW +: AW] : pl_b + {ph_b, 8'd0};
    wire [AW-1:0] pr_c = (CTL12 >= 2) ? pr2_r[2*AW +: AW] : pl_c + {ph_c, 8'd0};
    wire [AW-1:0] pr_d = (CTL12 >= 2) ? pr2_r[3*AW +: AW] : pl_d + {ph_d, 8'd0};
    wire [AW-1:0] pr_o = (CTL12 >= 2) ? pr2_r[4*AW +: AW] : pl_o + {ph_o, 8'd0};
    wire [AW-1:0] pr_n = (CTL12 >= 2) ? pr2_r[5*AW +: AW] : pl_n + {ph_n, 8'd0};
    // CTL12 >= 2 (round 5): the five stride equalities t == s + c (mod 2^AW) on the S1 carry-save pair, carry-free
    // (s + c + ~t + 1 == 0 iff s ^ c ^ ~t == ~(maj(s, c, ~t) << 1)), registered with the sum at sub-step 2
    function automatic csa_eq(input [AW-1:0] cs, input [AW-1:0] cc, input [AW-1:0] t);
        reg [AW-1:0] nt, x, m;
        begin
            nt = ~t; x = cs ^ cc ^ nt; m = (cs & cc) | (cs & nt) | (cc & nt);
            csa_eq = &(x ^ {m[AW-2:0], 1'b0});
        end
    endfunction
    reg [4:0] eq_r;                      // a, b, c, d, o
    always @(posedge clk) if (pst == 2'd1 && sst == 4'd2)
        eq_r <= {csa_eq(pqs_r[4*AW +: AW], pqc_r[4*AW +: AW], q_oso), csa_eq(pqs_r[3*AW +: AW], pqc_r[3*AW +: AW], q_dso),
                 csa_eq(pqs_r[2*AW +: AW], pqc_r[2*AW +: AW], q_cso), csa_eq(pqs_r[1*AW +: AW], pqc_r[1*AW +: AW], q_bso),
                 csa_eq(pqs_r[0*AW +: AW], pqc_r[0*AW +: AW], q_aso)};
    wire [4:0] eqv = (CTL12 >= 2) ? eq_r : {q_oso == pr_o, q_dso == pr_d, q_cso == pr_c, q_bso == pr_b, q_aso == pr_a};
    wire s1_okp = (q_aind == IND_NONE) && (q_dst != DST_KVT) &&
                  (s1_even || !(q_bhalf || q_qm == QM_ALT_NP || q_qm == QM_ALT_PN)) &&
                  eqv[0] && eqv[1] && (q_cpair || eqv[2]) && eqv[3] &&
                  (q_dst == DST_NONE || eqv[4]);
    wire s1_okx = (CTL12 != 0) ? s1_okp : s1_ok;
    wire [CW-1:0] s1_nn = (CTL12 != 0) ? pr_n : q_nout * q_nin;
    wire s1_ld = (CTL12 >= 2) ? (pst == 2'd1 && sst == 4'd3) : (CTL12 != 0) ? (pst == 2'd1 && sst == 3'd1) : (pst == 2'd1);
    always @(posedge clk) if (s1_ld) begin
        s_flat <= s1_cand && s1_okx;
        // a whole-op reduction whose layout does not flatten: rows of whole 8-element chunks
        s_wnf <= (q_redwhole || q_redtree) && q_red != RED_NONE && !s1_okx && q_nout > 1;
        s_flatbad <= (q_redwhole || q_redtree) && q_red != RED_NONE && !s1_okx && q_nout > 1 && (q_nin[2:0] != 3'd0);
        s_ni <= (s1_cand && s1_okx) ? s1_nn : q_nin;
        s_no <= (s1_cand && s1_okx) ? 1 : q_nout;
    end

    // ---- S2: layout, depths, offset terms ---------------------------------------------------------
    wire scalar_c = (q_sfu == SFU_RSQRT || q_sfu == SFU_SQRT || q_sfu == SFU_SPSQRT || q_sfu == SFU_EGATE);
    wire sfu_c = (q_sfu == SFU_EXP || q_sfu == SFU_SIGM || q_sfu == SFU_SILU || q_m1 == M1_DIVB || q_m1 == M1_DIVIMM);
    wire [3:0] c_lvw = scalar_c ? 4'd0 : sfu_c ? LM[3:0] : LN[3:0];
    wire red_on = (q_red != RED_NONE);
    // slot size: pow2ceil(max(ni, 8 if reducing)); a whole-op reduction over unflattened rows takes the
    // largest power of two dividing ni, so a vector never straddles a row and every vector is an
    // aligned block of the op's element order
    wire [4:0] c_tz = tzero(s_ni);
    wire [4:0] c_lsz = s_wnf ? c_tz : log2c((s_ni > (red_on ? 8 : 1)) ? s_ni : (red_on ? 8 : 1));
    wire [3:0] x_ls = (c_lsz > c_lvw) ? c_lvw : c_lsz[3:0];
    // CTL12 stages C (slot size), D (layout and the first depths), E / F (a non-flattening whole-op
    // reduction's vector count s_no * (s_ni >> ls), in two halves of s_no)
    reg  [3:0] r_ls, r_nsh;
    reg        r_packed;
    reg  [CW-1:0] r_nvs, r_sh;
    reg  [9:0] r_dF, r_dM, r_dS, r_lt2;
    reg  [CW-1:0] r_wl;
    reg  [CW-9:0] r_wh;
    // CTL12 >= 2: S3 the logarithms, S4 the slot size, S5 layout / depths / offset terms, S6 count, S_LR levels / dR
    reg  [4:0] r2_tz, r2_lg, r2_gsh, r2_rsh;
    reg        r2_gpow, r2_rpow;
    reg  [3:0] r2_ls;
    wire [4:0] c2_lsz = s_wnf ? r2_tz : r2_lg;
    wire [3:0] c_ls = (CTL12 >= 2) ? r2_ls : (CTL12 != 0) ? r_ls : x_ls;
    wire [5*4-1:0] r2_ls_t;              // CTL12 >= 2: kept copies of r2_ls for the offset terms, one a stream
    wire [5*4-1:0] c_ls_t = (CTL12 >= 2) ? r2_ls_t : {5{c_ls}};
    wire x_packed = !s_wnf && (s_ni <= (1 << c_ls));
    reg  r2_packed;
    wire c_packed = (CTL12 >= 2) ? r2_packed : (CTL12 != 0) ? r_packed : x_packed;
    wire c_rpow = (CTL12 >= 2) ? r2_rpow : pow2(q_rso);
    wire [3:0] x_nsh = (x_packed && (!red_on || c_rpow)) ? (c_lvw - c_ls) : 4'd0;
    reg  [3:0] r2_nsh;
    wire [3:0] c_nsh = (CTL12 >= 2) ? r2_nsh : (CTL12 != 0) ? r_nsh : x_nsh;
    wire [CW-1:0] x_nvs = s_wnf ? s_no * (s_ni >> c_ls) : (s_ni + (1 << c_ls) - 1) >> c_ls;
    reg  [CW-1:0] r2_nvs;
    wire [CW-1:0] c_nvs = (CTL12 >= 2) ? r2_nvs : (CTL12 != 0) ? r_nvs : x_nvs;
    wire [4:0] c_L = log2c(c_nvs);
    wire c_span = red_on && !c_packed;
    wire c_gather = (q_aind != IND_NONE);
    wire [AW-1:0] c_gstr = (q_aind == IND_I) ? q_asi : q_aso;
    wire c_div = (q_m1 == M1_DIVB || q_m1 == M1_DIVIMM);
    wire [9:0] x_dF = c_gather ? 10'd6 + OPR + CAPR + GSH : 10'd4 + CAPR;       // broadcast register + fetch
    wire [9:0] x_dM = x_dF + 10'd1 + OPR + (c_div ? DDIV : H_M[9:0]);
    wire [9:0] x_dS = x_dM + H_M[9:0] + H_A[9:0] + OPR + sfu_d(q_sfu);
    wire [9:0] x_lt = red_on ? {6'd0, c_ls} - 10'd3 : 10'd0;
    reg  [9:0] r2_dF, r2_dM, r2_dS, r2_lt2;
    wire [9:0] c_dF = (CTL12 >= 2) ? r2_dF : (CTL12 != 0) ? r_dF : x_dF;
    wire [9:0] c_dM = (CTL12 >= 2) ? r2_dM : (CTL12 != 0) ? r_dM : x_dM;
    wire [9:0] c_dS = (CTL12 >= 2) ? r2_dS : (CTL12 != 0) ? r_dS : x_dS;
    wire [9:0] c_lt = (CTL12 >= 2) ? r2_lt2 : (CTL12 != 0) ? r_lt2 : x_lt;
    always @(posedge clk) begin
        if (pst == 2'd1 && sst == 3'd2) r_ls <= x_ls;
        if (pst == 2'd1 && sst == 3'd3) begin
            r_packed <= x_packed; r_nsh <= x_nsh; r_sh <= s_ni >> c_ls;
            r_nvs <= (s_ni + (1 << c_ls) - 1) >> c_ls;          // replaced below for a non-flattening reduction
            r_dF <= x_dF; r_dM <= x_dM; r_dS <= x_dS; r_lt2 <= x_lt;
        end
        if (pst == 2'd1 && sst == 3'd4) begin r_wl <= s_no[7:0] * r_sh; r_wh <= s_no[15:8] * r_sh[CW-9:0]; end
        if (pst == 2'd1 && sst == 3'd5) r_nvs <= r_wl + {r_wh, 8'd0};
    end
    // retire (E1, E2, OUT: 2 MLAT + 1), then the reducer to its tap (IN 1, SQ MLAT, CHAIN 7 ALAT, TREE ALAT lt)
    // RHALF: every reducer stage takes two fast cycles, plus 4 pin stages (x 2) and the fast event register
    localparam [9:0] RHM = (RHALF != 0) ? 10'd2 : 10'd1, RHO = (RHALF != 0) ? 10'd9 : 10'd0;
    wire [9:0] c_dT = c_dS + (H_M[9:0] << 1) + OPR + 10'd1 + RHO + RHM * (10'd1 + H_M[9:0] + 10'd7 * (H_A[9:0] + ROPI) + RPAD + RSL + RTAP + ROUT
                      + H_R[9:0] * c_lt);
    wire [9:0] c_dR = c_dT + RHM * (10'd1 + (c_span ? H_R[9:0] * {5'd0, c_L} : 10'd0));
    wire c_bad = (red_on && scalar_c) || s_flatbad || (c_span && c_L > LV) || (c_gather && !pow2(c_gstr));
    // offset terms: stream s (A, B, C, D, O), bit k of the lane index
    wire [AW-1:0] so_s [0:4];
    wire [AW-1:0] si_s [0:4];
    assign so_s[0] = q_aso; assign so_s[1] = q_bso; assign so_s[2] = q_cso; assign so_s[3] = q_dso; assign so_s[4] = q_oso;
    assign si_s[0] = q_asi; assign si_s[1] = q_bsi; assign si_s[2] = q_csi; assign si_s[3] = q_dsi; assign si_s[4] = q_osi;
    reg [5*LN*AW-1:0] c_terms;
    reg [5*AW-1:0]    c_istep, c_ostep;
    integer s, kk;
    always @(*) begin
        for (s = 0; s < 5; s = s + 1) begin
            // stream s's lane offset = d_i * si (or (d_i >> 1) * si for a half stream) + d_o * so
            for (kk = 0; kk < LN; kk = kk + 1) begin
                if (kk < c_ls_t[s*4 +: 4]) begin
                    if (s == 0 && q_aind == IND_I) c_terms[(s*LN + kk)*AW +: AW] = 0;
                    else if ((s == 1 || s == 3) && q_bhalf) c_terms[(s*LN + kk)*AW +: AW] = (kk == 0) ? 0 : si_s[s] << (kk - 1);
                    else c_terms[(s*LN + kk)*AW +: AW] = si_s[s] << kk;
                end else begin
                    if (s == 0 && q_aind == IND_O) c_terms[(s*LN + kk)*AW +: AW] = 0;
                    else c_terms[(s*LN + kk)*AW +: AW] = so_s[s] << (kk - c_ls_t[s*4 +: 4]);
                end
            end
            c_ostep[s*AW +: AW] = (s == 0 && q_aind == IND_O) ? 0 : so_s[s] << c_nsh;
            c_istep[s*AW +: AW] = (s == 0 && q_aind == IND_I) ? 0 :
                                  ((s == 1 || s == 3) && q_bhalf) ? ((c_ls_t[s*4 +: 4] == 0) ? 0 : si_s[s] << (c_ls_t[s*4 +: 4] - 1)) :
                                  si_s[s] << c_ls_t[s*4 +: 4];
        end
    end
    // CTL12 >= 2 sub-steps
    localparam [CW-1:0] ONE_CW = 1;
    reg  [CW:0]   r2_nva;
    reg  [CW-1:0] r2_sh, r2_ssz;
    reg  [CW-1:0] r2_nslot;
    reg           r2_hls0;
    reg  [4*CW-1:0] r2_wq;
    wire [4*CW-1:0] wq_w;
    wire [CW-1:0]   wsum_w;
    // round 11 (margin): each 4-bit slice product s_no[4q+3:4q] * r2_sh is registered as its carry-save pair at
    // sub-step 7 (r2_wqs / r2_wqc) and carry-propagated at sub-step 8 into r2_wq; the four-slice sum is sub-step 9
    // (a non-flattening reduction's set-up takes one more cycle: S2_LR 9 -> 10). Round-10 route: s_no -> cmul4 -> r2_wq
    // -59.2 ps @770 (+4.2 @833.333), the only class under +40.
    reg  [4*CW-1:0] r2_wqs, r2_wqc;
    wire [4*CW-1:0] wqs_w, wqc_w;
    generate for (gq = 0; gq < 4; gq = gq + 1) begin : g_wq
        wire [CW-1:0] m0 = s_no[4*gq]     ? r2_sh        : {CW{1'b0}};
        wire [CW-1:0] m1 = s_no[4*gq + 1] ? (r2_sh << 1) : {CW{1'b0}};
        wire [CW-1:0] m2 = s_no[4*gq + 2] ? (r2_sh << 2) : {CW{1'b0}};
        wire [CW-1:0] m3 = s_no[4*gq + 3] ? (r2_sh << 3) : {CW{1'b0}};
        wire [CW-1:0] a1 = m0 ^ m1 ^ m2;
        wire [CW-1:0] b1 = ((m0 & m1) | (m0 & m2) | (m1 & m2)) << 1;
        assign wqs_w[gq*CW +: CW] = a1 ^ b1 ^ m3;
        assign wqc_w[gq*CW +: CW] = ((a1 & b1) | (a1 & m3) | (b1 & m3)) << 1;
        wire wq_co;
        ot_hdc_kadd #(.W(CW), .K(KK)) u_m (.a(r2_wqs[gq*CW +: CW]), .b(r2_wqc[gq*CW +: CW]), .cin(1'b0),
                                           .s(wq_w[gq*CW +: CW]), .cout(wq_co));
    end endgenerate
    ot_hdc_v41x_csum4 #(.W(CW), .K(KK)) u_ws (.a(r2_wq[0 +: CW]), .b(r2_wq[CW +: CW] << 4), .c(r2_wq[2*CW +: CW] << 8),
                                              .d(r2_wq[3*CW +: CW] << 12), .y(wsum_w));
    wire [CW:0] nva_w;
    wire        nva_unused;
    ot_hdc_kadd #(.W(CW + 1), .K(KK)) u_nva (.a({1'b0, s_ni}), .b({1'b0, (ONE_CW << c_ls) - ONE_CW}), .cin(1'b0),
                                            .s(nva_w), .cout(nva_unused));
`ifdef OT_NEG_CTL12_WQ
    // NEGATIVE CONTROL (compile-time only): the levels L read the slice-product sum a cycle early (round-10 timing);
    // the exact campaign must FAIL with this defined
    wire [3:0] S2_LR = s_wnf ? 4'd9 : 4'd8;
`else
    wire [3:0] S2_LR = s_wnf ? 4'd10 : 4'd8;
`endif     // the levels L; the result depth and the check one step later
    reg  [9:0] r2_dT, r2_dR, r2_dTa, r2_lth;
    reg  [AW-1:0] r2_gstr;
    reg  [15:0] r2_need1;
    genvar gt;
    generate for (gt = 0; gt < 5; gt = gt + 1) begin : g_lst
        ot_hdc_v41x_ckreg #(.W(4), .R(0)) u_lst (.clk(clk), .rst_n(rst_n),
            .d((pst == 2'd1 && sst == 4'd5) ? ((c2_lsz > c_lvw) ? c_lvw : c2_lsz[3:0]) : r2_ls_t[gt*4 +: 4]),
            .q(r2_ls_t[gt*4 +: 4]));
    end endgenerate
    reg  [4:0] r2_L;
    reg        r2_bad;
    reg  [5*LN*AW-1:0] r2_terms;
    reg  [5*AW-1:0]    r2_istep, r2_ostep;
    reg  [AW-1:0]      r2_rstep;
    wire [4:0] c2_L = log2c(r2_nvs);
    always @(posedge clk) begin
        if (pst == 2'd1 && sst == 4'd4) begin
            r2_tz <= tzero(s_ni);
            r2_lg <= log2c((s_ni > (red_on ? 8 : 1)) ? s_ni : (red_on ? 8 : 1));
            r2_gstr <= c_gstr;
        end
        if (pst == 2'd1 && sst == 4'd5) begin
            r2_ls <= (c2_lsz > c_lvw) ? c_lvw : c2_lsz[3:0];
            r2_gsh <= log2f(r2_gstr); r2_rsh <= log2f(q_rso); r2_gpow <= pow2(r2_gstr); r2_rpow <= pow2(q_rso);
        end
        if (pst == 2'd1 && sst == 4'd6) begin
            r2_packed <= x_packed; r2_nsh <= x_nsh; r2_sh <= s_ni >> c_ls; r2_nva <= nva_w;
            r2_dF <= x_dF; r2_dM <= x_dM; r2_dS <= x_dS; r2_lt2 <= x_lt;
            r2_ssz <= ONE_CW << c_ls; r2_hls0 <= q_bhalf && (c_ls == 4'd0);
            r2_terms <= c_terms; r2_istep <= c_istep;
            r2_need1 <= q_chlead + {8'd0, q_chmul[15:8]};
        end
        if (pst == 2'd1 && sst == 4'd7) begin
            r2_nvs <= r2_nva >> c_ls;                    // replaced at S7 for a non-flattening reduction
            r2_wqs <= wqs_w; r2_wqc <= wqc_w;
            r2_nslot <= ONE_CW << c_nsh; r2_ostep <= c_ostep; r2_rstep <= s_wnf ? {AW{1'b0}} : q_rso << c_nsh;
            // c_dT = c_dS + the constant stages + H_R * c_lt, in two steps
            r2_dTa <= c_dS + (H_M[9:0] << 1) + OPR + 10'd1 + RHO + RHM * (10'd1 + H_M[9:0] + 10'd7 * (H_A[9:0] + ROPI) + RPAD + RSL + RTAP + ROUT);
            r2_lth <= RHM * (H_R[9:0] * c_lt);
        end
        if (pst == 2'd1 && sst == 4'd8) r2_dT <= r2_dTa + r2_lth;
        if (pst == 2'd1 && sst == 4'd8) r2_wq <= wq_w;
        if (pst == 2'd1 && sst == 4'd9 && s_wnf) r2_nvs <= wsum_w;
        if (pst == 2'd1 && sst == S2_LR) r2_L <= c2_L;
        if (pst == 2'd1 && sst == S2_LR + 4'd1) begin
            r2_dR <= r2_dT + RHM * (10'd1 + (c_span ? H_R[9:0] * {5'd0, r2_L} : 10'd0));
            r2_bad <= (red_on && scalar_c) || s_flatbad || (c_span && r2_L > LV) || (c_gather && !r2_gpow);
        end
    end
    wire s_done = (CTL12 == 0) || (CTL12 == 1 && ((sst == 4'd3 && !s_wnf) || sst == 4'd5)) ||
                  (CTL12 >= 2 && sst == S2_LR + 4'd1);
    // registered set-up results (the pending op)
    reg [CW-1:0]      p_no, p_ni;
    reg [3:0]         p_ls, p_lvw, p_nsh, p_lt;
    reg [2:0]         p_L;
    reg               p_packed, p_span, p_bad, p_gather, p_wnf;
    reg [4:0]         p_gsh, p_rsh;
    reg [9:0]         p_dF, p_dM, p_dS, p_dT, p_dR;
    reg [5*LN*AW-1:0] p_terms;
    reg [5*AW-1:0]    p_istep, p_ostep;
    reg [AW-1:0]      p_rstep;
    reg s2_go;
    reg [CW-1:0]      p_ssz, p_nslot;    // CTL12 >= 2: 1 << ls, 1 << nsh
    reg               p_hls0;            // CTL12 >= 2: a half stream at slot size 1
    wire [4:0] u_L = (CTL12 >= 2) ? r2_L : c_L;
    always @(posedge clk) if (s2_go) begin
        p_no <= s_no; p_ni <= s_ni; p_ls <= c_ls; p_lvw <= c_lvw; p_nsh <= c_nsh; p_lt <= c_lt[3:0];
        p_L <= (u_L > 7) ? 3'd7 : u_L[2:0];
        p_packed <= c_packed; p_span <= c_span; p_bad <= (CTL12 >= 2) ? r2_bad : c_bad; p_gather <= c_gather;
        p_gsh <= (CTL12 >= 2) ? r2_gsh : log2f(c_gstr); p_rsh <= (CTL12 >= 2) ? r2_rsh : log2f(q_rso);
        p_dF <= c_dF; p_dM <= c_dM; p_dS <= c_dS;
        p_dT <= (CTL12 >= 2) ? r2_dT : c_dT; p_dR <= (CTL12 >= 2) ? r2_dR : c_dR;
        p_terms <= (CTL12 >= 2) ? r2_terms : c_terms; p_istep <= (CTL12 >= 2) ? r2_istep : c_istep;
        p_ostep <= (CTL12 >= 2) ? r2_ostep : c_ostep;
        p_rstep <= (CTL12 >= 2) ? r2_rstep : s_wnf ? {AW{1'b0}} : q_rso << c_nsh;
        p_wnf <= s_wnf;
        p_ssz <= r2_ssz; p_nslot <= r2_nslot; p_hls0 <= r2_hls0;
    end

    // =========================================================================================
    // Active op and the vector loop
    // =========================================================================================
    reg              a_v;                // an op is emitting
    reg              a_started;
    reg [CW-1:0]     a_no, a_ni, o_v, i_v;
    reg [3:0]        a_ls, a_lvw, a_nsh, a_lt;
    reg [2:0]        a_L;
    reg              a_packed, a_span, a_gather, a_bank, a_wnf;
    reg [4:0]        a_gsh, a_rsh;
    reg [9:0]        a_dF, a_dM, a_dS, a_dT, a_dR;
    reg [5*AW-1:0]   a_istep, a_ostep, row, vb;
    reg [AW-1:0]     a_rstep, rrow, krow;
    reg [1:0]        a_asrc, a_bsrc, a_csrc, a_dsrc, a_aind, a_dst, a_red, a_m2, a_e2, a_chsrc;
    reg              a_bhalf, a_cpair, a_arnd, a_arelu, a_amin, a_cclip, a_rnd, a_redsq, a_redrnd;
    reg [2:0]        a_m1, a_qm, a_ad, a_sfu, a_e1;
    reg [31:0]       a_imm1, a_imm2, a_imm3;
    reg [AW-1:0]     a_obase, a_aibase;
    reg [7:0]        a_seq, a_chseq;
    reg [15:0]       a_chlead, a_chmul, a_mark, a_nv;
    reg [23:0]       a_acc;
    reg [AW-1:0]     a_istep_h1, a_istep_h3;
    // previous op (SELF_VEC chaining)
    reg              pv_v;
    reg [15:0]       pv_mark, pv_nv;
    reg [7:0]        pv_seq;
    // counters
    reg [15:0]       e_tot, r_tot;       // r_tot: vectors whose writes this unit's consumers may read (DI)
    reg [15:0]       rp_tot;             // vectors whose writes have landed (published)
    reg [7:0]        i_dseq, i_rseq;     // cr_dseq / cr_rseq at the internal credit timing (DI)
    wire             ret_i, ret_p, res_i, res_p;
    wire [7:0]       ret_i_seq, ret_p_seq, res_i_seq, res_p_seq;
    wire             ret_i_last, ret_p_last, res_i_last, res_p_last;
    reg [9:0]        cpF, cpM, cpS, cpT, cpR;
    reg [7:0]        rseq_r;

    // position of the vector, its end
    reg  [CW-1:0] a_ssz, a_nslot;         // CTL12 >= 2: 1 << a_ls, 1 << a_nsh (loaded at promote)
    reg           a_hls0;                 // CTL12 >= 2: a_bhalf && a_ls == 0
    wire [CW-1:0] S_sz = (CTL12 >= 2) ? a_ssz : 1 << a_ls;
    wire [CW-1:0] nslot = (CTL12 >= 2) ? a_nslot : 1 << a_nsh;
    wire wrap_c = a_packed || (i_v + S_sz >= a_ni);                  // the vector ends its row(s)
    wire last_c = wrap_c && (o_v + nslot >= a_no);
    reg  wrap_r, olast_r, ck_r, ch_r;   // CTL12: the conditions of the current vector, registered
    wire wrap = (CTL12 != 0) ? wrap_r : wrap_c;
    wire last_v = (CTL12 != 0) ? (wrap_r && olast_r) : last_c;
    // first-vector checkpoints
    wire ck_c = (a_dF >= cpF) && (a_dM >= cpM) && (a_dS >= cpS) &&
                (a_red == RED_NONE || a_dR >= cpR) && (!a_span || a_dT >= cpT);
    wire ck_ok = (CTL12 != 0) ? ck_r : ck_c;
    // chaining
    wire [15:0] need = a_chlead + a_acc[23:8];
    wire [15:0] pv_cnt = r_tot - pv_mark;
    wire        pv_neg = pv_cnt[15];
    wire [7:0]  ds = i_dseq - a_chseq;
    wire        pv_ok  = !ds[7] || (pv_v && pv_seq == a_chseq && !pv_neg && pv_cnt >= need);
    wire [7:0]  dx = x_dseq - a_chseq;
    wire [7:0]  dr = i_rseq - a_chseq;
    wire ch_c = (a_chsrc == CH_NONE) ? 1'b1 :
                (a_chsrc == CH_SELF) ? pv_ok :
                (a_chsrc == CH_RES)  ? !dr[7] :
                (!dx[7] || (x_seq == a_chseq && x_cnt >= need));
    wire ch_ok = (CTL12 != 0) ? ch_r : ch_c;
    // RHALF issue rule: a reduction beat emits only in a cycle whose retire lands in a ph = 1 cycle (hph = the
    // reducer's ph, both leave reset together); hok_r is that condition for THIS cycle, registered a cycle ahead.
    reg  hph, hok_r;
    wire emit = a_v && (a_started || ck_ok) && ch_ok && (RHALF == 0 || hok_r);
    wire promote = (pst == 2'd3) && (!a_v || (emit && last_v));
    wire [1:0] n_ared = promote ? q_red : a_red;
    wire       n_ads0 = promote ? p_dS[0] : a_dS[0];
`ifdef OT_NEG_RHALF_NOGATE
    wire       n_hok = 1'b1;     // NEGATIVE CONTROL: no issue rule -> back-to-back beats reach the half-rate reducer
`else
    wire       n_hok = (n_ared == RED_NONE) || ((~hph ^ n_ads0 ^ RHPAR[0]) == 1'b1);
`endif
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin hph <= 1'b0; hok_r <= 1'b1; end else begin hph <= ~hph; hok_r <= n_hok; end

    // ---- CTL12: the next cycle's conditions, registered ------------------------------------------
    // The row-end / last-vector flags of the current vector (with the next position i_v + S, o_v + nslot kept
    // in registers), the first-vector checkpoints and the chaining credits, each computed from the state the
    // next cycle will hold (promote / emit select among precomputed candidates), so `emit` is a few gates.
    reg  [CW-1:0] iv1_r, ov1_r;
    reg           a_wrap0, p_wrap0, p_olast0;
    always @(posedge clk) if (pst == 2'd2 && !s2_go) begin     // the lane-load cycle
        p_wrap0 <= p_packed || ((CTL12 >= 2) ? (p_ssz >= p_ni) : ((1 << p_ls) >= p_ni));
        p_olast0 <= (CTL12 >= 2) ? (p_nslot >= p_no) : ((1 << p_nsh) >= p_no);
    end
    wire [CW-1:0] iv2, ov2;
    wire          iv2_ge, ov2_ge, unused_iv2c, unused_ov2c;
    // CTL12 >= 2: iv2 / ov2 are registers (iv1 + S, ov1 + nslot, kept one step ahead), so the flags are one compare
    reg  [CW-1:0] iv2_r, ov2_r;
    wire [CW-1:0] iv2_c, ov2_c, iv3, ov3;
    wire          unused_iv3c, unused_ov3c;
    ot_hdc_kadd #(.W(CW), .K(KK)) u_iv2 (.a(iv1_r), .b(S_sz), .cin(1'b0), .s(iv2_c), .cout(unused_iv2c));
    ot_hdc_kadd #(.W(CW), .K(KK)) u_ov2 (.a(ov1_r), .b(nslot), .cin(1'b0), .s(ov2_c), .cout(unused_ov2c));
    ot_hdc_kadd #(.W(CW), .K(KK)) u_iv3 (.a(iv2_r), .b(S_sz), .cin(1'b0), .s(iv3), .cout(unused_iv3c));
    ot_hdc_kadd #(.W(CW), .K(KK)) u_ov3 (.a(ov2_r), .b(nslot), .cin(1'b0), .s(ov3), .cout(unused_ov3c));
    assign iv2 = (CTL12 >= 2) ? iv2_r : iv2_c;
    assign ov2 = (CTL12 >= 2) ? ov2_r : ov2_c;
    ot_hdc_kge  #(.W(CW), .K(KK)) u_iv2g (.a(iv2), .b(a_ni), .ge(iv2_ge));
    ot_hdc_kge  #(.W(CW), .K(KK)) u_ov2g (.a(ov2), .b(a_no), .ge(ov2_ge));
    // the registered conditions' next values (one D for the original and every CTL12 >= 2 copy)
    wire n_wr = promote ? p_wrap0 : emit ? (wrap_r ? a_wrap0 : (a_packed || iv2_ge)) : wrap_r;
    wire n_ol = promote ? p_olast0 : (emit && wrap_r) ? ov2_ge : olast_r;
    always @(posedge clk) begin
        wrap_r <= n_wr; olast_r <= n_ol;
        if (PROM[15]) begin
            iv1_r <= (CTL12 >= 2) ? p_ssz : 1 << p_ls; ov1_r <= (CTL12 >= 2) ? p_nslot : 1 << p_nsh; a_wrap0 <= p_wrap0;
            iv2_r <= p_ssz << 1; ov2_r <= p_nslot << 1;
        end else if (EMIT[15]) begin
            if (WRAPS[15]) begin iv1_r <= S_sz; ov1_r <= ov2; iv2_r <= S_sz << 1; ov2_r <= ov3; end
            else begin iv1_r <= iv2; iv2_r <= iv3; end
        end
    end
    // checkpoints: the counters' next values
    wire [9:0] n_cpF = emit ? a_dF : (cpF != 0) ? cpF - 10'd1 : 10'd0;
    wire [9:0] n_cpM = emit ? a_dM : (cpM != 0) ? cpM - 10'd1 : 10'd0;
    wire [9:0] n_cpS = emit ? a_dS : (cpS != 0) ? cpS - 10'd1 : 10'd0;
    wire [9:0] n_cpT = (emit && a_red != RED_NONE) ? a_dT : (cpT != 0) ? cpT - 10'd1 : 10'd0;
    wire [9:0] n_cpR = (emit && a_red != RED_NONE) ? a_dR : (cpR != 0) ? cpR - 10'd1 : 10'd0;
    wire ck_prom = (p_dF >= n_cpF) && (p_dM >= n_cpM) && (p_dS >= n_cpS) &&
                   (q_red == RED_NONE || p_dR >= n_cpR) && (!p_span || p_dT >= n_cpT);
    wire ck_hold = (a_dF >= n_cpF) && (a_dM >= n_cpM) && (a_dS >= n_cpS) &&
                   (a_red == RED_NONE || a_dR >= n_cpR) && (!a_span || a_dT >= n_cpT);
    // CTL12 >= 2: both candidates of the counters (an emit loads the op's depths, so ck_hold is then true),
    // emit selects last
    // CTL12 >= 2: cpX - 1 (saturating) is a register, mm_cpX, updated with cpX
    reg  [9:0] mm_cpF, mm_cpM, mm_cpS, mm_cpT, mm_cpR, a_dFm, a_dMm, a_dSm, a_dTm, a_dRm;
    wire [9:0] m_cpF = (CTL12 >= 2) ? mm_cpF : (cpF != 0) ? cpF - 10'd1 : 10'd0;
    wire [9:0] m_cpM = (CTL12 >= 2) ? mm_cpM : (cpM != 0) ? cpM - 10'd1 : 10'd0;
    wire [9:0] m_cpS = (CTL12 >= 2) ? mm_cpS : (cpS != 0) ? cpS - 10'd1 : 10'd0;
    wire [9:0] m_cpT = (CTL12 >= 2) ? mm_cpT : (cpT != 0) ? cpT - 10'd1 : 10'd0;
    wire [9:0] m_cpR = (CTL12 >= 2) ? mm_cpR : (cpR != 0) ? cpR - 10'd1 : 10'd0;
    function automatic [9:0] sdec(input [9:0] x); sdec = (x != 0) ? x - 10'd1 : 10'd0; endfunction
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin mm_cpF <= 0; mm_cpM <= 0; mm_cpS <= 0; mm_cpT <= 0; mm_cpR <= 0; end
        else begin
            mm_cpF <= EMIT[13] ? a_dFm : sdec(mm_cpF);
            mm_cpM <= EMIT[13] ? a_dMm : sdec(mm_cpM);
            mm_cpS <= EMIT[13] ? a_dSm : sdec(mm_cpS);
            mm_cpT <= (EMIT[13] && a_red != RED_NONE) ? a_dTm : sdec(mm_cpT);
            mm_cpR <= (EMIT[13] && a_red != RED_NONE) ? a_dRm : sdec(mm_cpR);
        end
    end
    always @(posedge clk) if (PROM[2]) begin
        a_dFm <= sdec(p_dF); a_dMm <= sdec(p_dM); a_dSm <= sdec(p_dS); a_dTm <= sdec(p_dT); a_dRm <= sdec(p_dR);
    end
    wire [9:0] e_cpT = (a_red != RED_NONE) ? a_dT : m_cpT, e_cpR = (a_red != RED_NONE) ? a_dR : m_cpR;
    wire ck_hold_n = (a_dF >= m_cpF) && (a_dM >= m_cpM) && (a_dS >= m_cpS) &&
                     (a_red == RED_NONE || a_dR >= m_cpR) && (!a_span || a_dT >= m_cpT);
    wire ck_prom_e = (p_dF >= a_dF) && (p_dM >= a_dM) && (p_dS >= a_dS) &&
                     (q_red == RED_NONE || p_dR >= e_cpR) && (!p_span || p_dT >= e_cpT);
    wire ck_prom_n = (p_dF >= m_cpF) && (p_dM >= m_cpM) && (p_dS >= m_cpS) &&
                     (q_red == RED_NONE || p_dR >= m_cpR) && (!p_span || p_dT >= m_cpT);
    wire n_ck = (CTL12 >= 2) ? (promote ? (emit ? ck_prom_e : ck_prom_n) : (emit || ck_hold_n))
                             : (promote ? ck_prom : ck_hold);
    // chaining: next-cycle internal credit state (exact) and the external producer's state now
    reg  [15:0] rtot1_r;                 // CTL12 >= 2: r_tot + 1
    wire [15:0] n_rtot = (CTL12 >= 2) ? (ret_i ? rtot1_r : r_tot) : r_tot + (ret_i ? 16'd1 : 16'd0);
    wire [7:0]  n_idseq = (ret_i && ret_i_last) ? ret_i_seq : i_dseq;
    wire [7:0]  n_irseq = (res_i && res_i_last) ? res_i_seq : i_rseq;
    wire [15:0] pvm_e = a_started ? a_mark : e_tot;          // pv_mark after this op's last emit
    function automatic chf(input [1:0] src, input [7:0] cseq, input [15:0] nd, input pvv, input [7:0] pvs,
                           input [15:0] pvm, input [15:0] rt, input [7:0] dsq, input [7:0] rsq);
        reg [15:0] cnt;
        reg [7:0] d_s, d_r, d_x;
        begin
            cnt = rt - pvm;
            d_s = dsq - cseq; d_r = rsq - cseq; d_x = x_dseq - cseq;
            chf = (src == CH_NONE) ? 1'b1 :
                  (src == CH_SELF) ? (!d_s[7] || (pvv && pvs == cseq && !cnt[15] && cnt >= nd)) :
                  (src == CH_RES)  ? !d_r[7] :
                  (!d_x[7] || (x_seq == cseq && x_cnt >= nd));
        end
    endfunction
    wire [23:0] acc_e = a_acc + {8'd0, a_chmul};
    wire [15:0] need_e = a_chlead + acc_e[23:8];
    wire ch_prom_a = chf(q_chsrc, q_chseq, q_chlead, 1'b1, a_seq, pvm_e, n_rtot, n_idseq, n_irseq);
    wire ch_prom_i = chf(q_chsrc, q_chseq, q_chlead, pv_v, pv_seq, pv_mark, n_rtot, n_idseq, n_irseq);
    wire ch_emit = chf(a_chsrc, a_chseq, need_e, pv_v, pv_seq, pv_mark, n_rtot, n_idseq, n_irseq);
    wire ch_hold = chf(a_chsrc, a_chseq, need, pv_v, pv_seq, pv_mark, n_rtot, n_idseq, n_irseq);
    // CTL12 >= 2: the same four credit functions on kept-prefix subtracts / compares and the registered needs
    reg  [23:0] acc1_r, acc2_r;          // a_acc + a_chmul, a_acc + 2 a_chmul
    reg  [15:0] need0_r, need1_r;        // a_chlead + a_acc[23:8], a_chlead + (a_acc + a_chmul)[23:8]
    // the count rt - pvm for both values of this cycle's retire (r_tot, r_tot + 1); ret_i selects last
    // the counts r_tot - pv_mark and r_tot - pvm_e as registers (and + 1), from the next-cycle values of their terms
    reg  [15:0] cnt_p0, cnt_p1, cnt_e0, cnt_e1;
    // the loop / set-up state's next values (the original registers and every copy take these)
    wire       n_av = promote ? 1'b1 : (emit && last_v) ? 1'b0 : a_v;
    wire       n_st = promote ? 1'b0 : (emit && !a_started) ? 1'b1 : a_started;
    wire [1:0] n_pst = accept ? 2'd1 : (pst == 2'd1 && s_done) ? 2'd2 : (pst == 2'd2 && !s2_go) ? 2'd3 :
                       promote ? 2'd0 : pst;
    // every candidate of the next marks is subtracted from n_rtot in parallel; the selects (emit / promote state) last
    wire [15:0] n_amark = (!PROM[11] && EMIT[11] && !STRT[11]) ? e_tot : a_mark;
    // round 6: r_tot, r_tot + 1, r_tot + 2 are registers (rtot1_r, rtot2_r), so every candidate count is ONE subtract
    // per mark (pv_mark, a_mark, e_tot; and r_tot - e_tot - 1 for an emit's e_tot + 1).  n_amark / e_tot_n / the
    // started state / this cycle's retire are all late selects among those subtracts (on registered control copies).
    reg  [15:0] rtot2_r;
    wire [15:0] dk0, dm0, de0, dk1, dm1, de1, dk2, dm2, de2, dem;
    wire [9:0]  unused_cc;
    ot_hdc_kadd #(.W(16), .K(KK)) u_dk (.a(r_tot), .b(~pv_mark), .cin(1'b1), .s(dk0), .cout(unused_cc[0]));
    ot_hdc_kadd #(.W(16), .K(KK)) u_dm (.a(r_tot), .b(~a_mark), .cin(1'b1), .s(dm0), .cout(unused_cc[1]));
    ot_hdc_kadd #(.W(16), .K(KK)) u_de (.a(r_tot), .b(~e_tot), .cin(1'b1), .s(de0), .cout(unused_cc[2]));
    ot_hdc_kadd #(.W(16), .K(KK)) u_dem (.a(r_tot), .b(~e_tot), .cin(1'b0), .s(dem), .cout(unused_cc[3]));
    ot_hdc_kadd #(.W(16), .K(KK)) u_dk1 (.a(rtot1_r), .b(~pv_mark), .cin(1'b1), .s(dk1), .cout(unused_cc[4]));
    ot_hdc_kadd #(.W(16), .K(KK)) u_dm1 (.a(rtot1_r), .b(~a_mark), .cin(1'b1), .s(dm1), .cout(unused_cc[5]));
    ot_hdc_kadd #(.W(16), .K(KK)) u_de1 (.a(rtot1_r), .b(~e_tot), .cin(1'b1), .s(de1), .cout(unused_cc[6]));
    ot_hdc_kadd #(.W(16), .K(KK)) u_dk2 (.a(rtot2_r), .b(~pv_mark), .cin(1'b1), .s(dk2), .cout(unused_cc[7]));
    ot_hdc_kadd #(.W(16), .K(KK)) u_dm2 (.a(rtot2_r), .b(~a_mark), .cin(1'b1), .s(dm2), .cout(unused_cc[8]));
    ot_hdc_kadd #(.W(16), .K(KK)) u_de2 (.a(rtot2_r), .b(~e_tot), .cin(1'b1), .s(de2), .cout(unused_cc[9]));
    wire        pv_upd = EMIT[14] && LAST[14];
    wire        am_e = !PROM[11] && EMIT[11] && !STRT[11];             // n_amark == e_tot
    wire        nst_k = PROM[0] ? 1'b0 : (EMIT[0] && !STRT[0]) ? 1'b1 : STRT[0];   // n_st on control copy 0
    // r_j - X for r_j = r_tot + j: pv_mark (k), a_mark (m), e_tot (e); e_tot_n = e_tot + EMIT[14] shifts e by one
    wire [15:0] cp_r0 = pv_upd ? (STRT[14] ? dm0 : de0) : dk0, cp_r1 = pv_upd ? (STRT[14] ? dm1 : de1) : dk1,
                cp_r2 = pv_upd ? (STRT[14] ? dm2 : de2) : dk2;
    wire [15:0] dA0 = am_e ? de0 : dm0, dA1 = am_e ? de1 : dm1, dA2 = am_e ? de2 : dm2;
    wire [15:0] dB0 = EMIT[14] ? dem : de0, dB1 = EMIT[14] ? de0 : de1, dB2 = EMIT[14] ? de1 : de2;
    wire [15:0] ce_r0 = nst_k ? dA0 : dB0, ce_r1 = nst_k ? dA1 : dB1, ce_r2 = nst_k ? dA2 : dB2;
    always @(posedge clk) begin
        cnt_p0 <= ret_i ? cp_r1 : cp_r0;                         // r_tot - pv_mark, next cycle
        cnt_p1 <= ret_i ? cp_r2 : cp_r1;
        cnt_e0 <= ret_i ? ce_r1 : ce_r0;                         // r_tot - pvm_e, next cycle
        cnt_e1 <= ret_i ? ce_r2 : ce_r1;
    end
    wire [1:0] cpa_o, cpi_o, cem_o, cho_o;
    genvar gr;
    generate for (gr = 0; gr < 2; gr = gr + 1) begin : g_cr
        wire [15:0] ce = gr ? cnt_e1 : cnt_e0, cp = gr ? cnt_p1 : cnt_p0;
        wire [7:0]  gds = (gr && ret_i_last) ? ret_i_seq : i_dseq;        // n_idseq for ret_i = gr
        wire        rsel_k = res_i && res_i_last;                            // n_irseq's select, applied last
        ot_hdc_v41x_chf3 #(.K(KK)) u_cpa (.src(q_chsrc), .cseq(q_chseq), .nd(q_chlead), .pvv(1'b1), .pvs(a_seq), .cnt(ce),
            .dsq(gds), .rsq0(i_rseq), .rsq1(res_i_seq), .rsel(rsel_k), .x_dseq(x_dseq), .x_seq(x_seq), .x_cnt(x_cnt), .ok(cpa_o[gr]));
        ot_hdc_v41x_chf3 #(.K(KK)) u_cpi (.src(q_chsrc), .cseq(q_chseq), .nd(q_chlead), .pvv(pv_v), .pvs(pv_seq), .cnt(cp),
            .dsq(gds), .rsq0(i_rseq), .rsq1(res_i_seq), .rsel(rsel_k), .x_dseq(x_dseq), .x_seq(x_seq), .x_cnt(x_cnt), .ok(cpi_o[gr]));
        ot_hdc_v41x_chf3 #(.K(KK)) u_cem (.src(a_chsrc), .cseq(a_chseq), .nd(need1_r), .pvv(pv_v), .pvs(pv_seq), .cnt(cp),
            .dsq(gds), .rsq0(i_rseq), .rsq1(res_i_seq), .rsel(rsel_k), .x_dseq(x_dseq), .x_seq(x_seq), .x_cnt(x_cnt), .ok(cem_o[gr]));
        ot_hdc_v41x_chf3 #(.K(KK)) u_cho (.src(a_chsrc), .cseq(a_chseq), .nd(need0_r), .pvv(pv_v), .pvs(pv_seq), .cnt(cp),
            .dsq(gds), .rsq0(i_rseq), .rsq1(res_i_seq), .rsel(rsel_k), .x_dseq(x_dseq), .x_seq(x_seq), .x_cnt(x_cnt), .ok(cho_o[gr]));
    end endgenerate
    // next ch for each value of this cycle's retire; ret_i selects last, in two kept copies (13 control copies each)
    wire [1:0] n_chr;
    // round 7: the selects on control copy 4 (promote / a_v / emit), not the shared combinational ones
    assign n_chr[0] = PROM[4] ? (AVC[4] ? cpa_o[0] : cpi_o[0]) : EMIT[4] ? cem_o[0] : cho_o[0];
    assign n_chr[1] = PROM[4] ? (AVC[4] ? cpa_o[1] : cpi_o[1]) : EMIT[4] ? cem_o[1] : cho_o[1];
    wire n_ch = (CTL12 >= 2) ? (ret_i ? n_chr[1] : n_chr[0])
                             : (promote ? (a_v ? ch_prom_a : ch_prom_i) : emit ? ch_emit : ch_hold);
    // round 7: four kept ret_i selects, each driving a quarter of the control copies
    wire [3:0] n_chq;
`ifdef OT_NEG_CTL12_CREDIT
    // NEGATIVE CONTROL (compile-time only): the next-ch copies always take the credit computed for "this cycle
    // retired" (count + 1), i.e. a consumer may run one element ahead of its producer; the campaign must FAIL.
    wire ch_sel = 1'b1;
`else
    wire ch_sel = ret_i;
`endif
    genvar gq4;
    generate for (gq4 = 0; gq4 < 4; gq4 = gq4 + 1) begin : g_chq
        ot_hdc_v41x_ckmux u_ch (.s(ch_sel), .a(n_chr[0]), .b(n_chr[1]), .y(n_chq[gq4]));
    end endgenerate
    genvar gk;
    generate if (CTL12 >= 2) begin : g_rep
        for (gk = 0; gk < KC; gk = gk + 1) begin : g_k
            wire [1:0] kp;
            wire       kav, kst, kck, kch, kwr, kol;
            ot_hdc_v41x_ckreg #(.W(6), .R(1)) u_r (.clk(clk), .rst_n(rst_n), .d({n_pst, n_av, n_st, n_ck, n_chq[gk * 4 / KC]}),
                                                 .q({kp, kav, kst, kck, kch}));
            ot_hdc_v41x_ckreg #(.W(2), .R(0)) u_c (.clk(clk), .rst_n(rst_n), .d({n_wr, n_ol}), .q({kwr, kol}));
            wire kho;
            if (RHALF != 0) begin : g_kh
                reg kh;
                always @(posedge clk or negedge rst_n) if (!rst_n) kh <= 1'b1; else kh <= n_hok;
                assign kho = kh;
            end else begin : g_kn
                assign kho = 1'b1;
            end
            wire kem = kav && (kst || kck) && kch && kho;
            assign EMIT[gk] = kem;
            assign WRAPS[gk] = kwr;
            assign STRT[gk] = kst;
            assign PROM[gk] = (kp == 2'd3) && (!kav || (kem && kwr && kol));
            assign ACC[gk] = go && (kp == 2'd0);
            assign LAST[gk] = kwr && kol;
            assign AVC[gk] = kav;
        end
    end else begin : g_one
        assign EMIT = {KC{emit}};
        assign WRAPS = {KC{wrap}};
        assign STRT = {KC{a_started}};
        assign PROM = {KC{promote}};
        assign ACC = {KC{accept}};
        assign LAST = {KC{last_v}};
        assign AVC = {KC{a_v}};
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin ck_r <= 1'b0; ch_r <= 1'b0; end
        else begin
            ck_r <= n_ck;
            ch_r <= n_ch;
        end
    end

    // set-up state
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin pst <= 2'd0; sst <= 4'd0; seq_ctr <= 8'd0; nbank <= 1'b0; s2_go <= 1'b0; end
        else begin
            s2_go <= 1'b0;
            if (accept) begin pst <= 2'd1; sst <= 4'd0; seq_ctr <= seq_ctr + 8'd1; nbank <= ~nbank; end
            else if (pst == 2'd1 && s_done) s2_go <= 1'b1;
            else if (pst == 2'd1) sst <= sst + 4'd1;
            pst <= n_pst;
        end
    end
    // (pst 2 takes two cycles: S2 registers p_*, then the lanes load their offsets from p_terms)
    wire lane_ld = (pst == 2'd2) && !s2_go;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            a_v <= 1'b0; a_started <= 1'b0; pv_v <= 1'b0; e_tot <= 0; r_tot <= 0; rp_tot <= 0; rtot1_r <= 16'd1; rtot2_r <= 16'd2;
            cpF <= 0; cpM <= 0; cpS <= 0; cpT <= 0; cpR <= 0;
        end else begin
            e_tot <= e_tot_n;
            r_tot <= n_rtot;
            rtot1_r <= rtot1_n; rtot2_r <= rtot2_n;
            rp_tot <= rp_tot_n;
            cpF <= EMIT[13] ? a_dF : m_cpF;
            cpM <= EMIT[13] ? a_dM : m_cpM;
            cpS <= EMIT[13] ? a_dS : m_cpS;
            // T is the reducer's tap (one multiplexer for packed results and spanning items): every
            // reducing op arms it, so a spanning op never reaches the tap before an older packed result
            cpT <= (EMIT[13] && a_red != RED_NONE) ? a_dT : m_cpT;
            cpR <= (EMIT[13] && a_red != RED_NONE) ? a_dR : m_cpR;
            if (EMIT[14] && LAST[14]) begin
                pv_v <= 1'b1; pv_mark <= STRT[14] ? a_mark : e_tot; pv_nv <= a_nv_p1; pv_seq <= a_seq;
            end
            a_v <= n_av; a_started <= n_st;
        end
    end
    // the vector position's adds (CTL12 >= 2: kept-prefix adders on registered operands)
    wire [5*AW-1:0] s_row;
    wire [CW-1:0]   s_ov, s_iv;
    wire [AW-1:0]   s_rrow, s_krow;
    wire [5*AW-1:0] s_vb;
    wire [5*AW-1:0] vb_inc;
    wire            hls0 = (CTL12 >= 2) ? a_hls0 : (a_bhalf && a_ls == 0);
    assign vb_inc[0 +: AW] = a_istep[0 +: AW];
    reg  iv0_r;                          // CTL12 >= 2: a copy of i_v[0] beside vb
    wire iv0 = (CTL12 >= 2) ? iv0_r : i_v[0];
    always @(posedge clk) begin
        if (PROM[7]) iv0_r <= 1'b0;
        else if (EMIT[7]) iv0_r <= WRAPS[7] ? 1'b0 : s_iv[0];
    end
    assign vb_inc[AW +: AW] = hls0 ? (iv0 ? a_istep_h1 : {AW{1'b0}}) : a_istep[AW +: AW];
    assign vb_inc[2*AW +: AW] = a_istep[2*AW +: AW];
    assign vb_inc[3*AW +: AW] = hls0 ? (iv0 ? a_istep_h3 : {AW{1'b0}}) : a_istep[3*AW +: AW];
    assign vb_inc[4*AW +: AW] = a_istep[4*AW +: AW];
    wire [8:0] unused_lc;
    // CTL12 >= 2: row + a_ostep is a register (row_nx), kept one step ahead of row
    reg  [5*AW-1:0] row_nx;
    wire [5*AW-1:0] s_row_c, row_nx_n, row_pr;
    wire [1:0]      unused_rx;
    ot_hdc_kadd #(.W(5*AW), .K(KK)) u_srow (.a(row), .b(a_ostep), .cin(1'b0), .s(s_row_c), .cout(unused_lc[0]));
    ot_hdc_kadd #(.W(5*AW), .K(KK)) u_rnx (.a(row_nx), .b(a_ostep), .cin(1'b0), .s(row_nx_n), .cout(unused_rx[0]));
    ot_hdc_kadd #(.W(5*AW), .K(KK)) u_rpr (.a({q_obase, q_dbase, q_cbase, q_bbase, q_abase}), .b(p_ostep), .cin(1'b0),
                                           .s(row_pr), .cout(unused_rx[1]));
    assign s_row = (CTL12 >= 2) ? row_nx : s_row_c;
    always @(posedge clk) begin
        if (PROM[6]) row_nx <= row_pr;
        else if (EMIT[6] && WRAPS[6]) row_nx <= row_nx_n;
    end
    ot_hdc_kadd #(.W(CW), .K(KK)) u_sov (.a(o_v), .b(nslot), .cin(1'b0), .s(s_ov), .cout(unused_lc[1]));
    ot_hdc_kadd #(.W(CW), .K(KK)) u_siv (.a(i_v), .b(S_sz), .cin(1'b0), .s(s_iv), .cout(unused_lc[2]));
    ot_hdc_kadd #(.W(AW), .K(KK)) u_srr (.a(rrow), .b(a_rstep), .cin(1'b0), .s(s_rrow), .cout(unused_lc[3]));
    ot_hdc_kadd #(.W(AW), .K(KK)) u_skr (.a(krow), .b(nslot[AW-1:0]), .cin(1'b0), .s(s_krow), .cout(unused_lc[4]));
    genvar gf;
    generate for (gf = 0; gf < 5; gf = gf + 1) begin : g_vbf
        wire unused_vc;
        ot_hdc_kadd #(.W(AW), .K(KK)) u_svb (.a(vb[gf*AW +: AW]), .b(vb_inc[gf*AW +: AW]), .cin(1'b0),
                                             .s(s_vb[gf*AW +: AW]), .cout(unused_vc));
    end endgenerate
    wire [15:0] a_nv_p1, e_tot_n, rp_tot_n, rtot1_n, emitted_n;
    wire [23:0] acc2_n;
    wire [15:0] need1_n;
    ot_hdc_kinc #(.W(16), .K(KK)) u_anv (.a(a_nv), .inc(1'b1), .y(a_nv_p1));
    ot_hdc_kinc #(.W(16), .K(KK)) u_etn (.a(e_tot), .inc(EMIT[14]), .y(e_tot_n));
    ot_hdc_kinc #(.W(16), .K(KK)) u_rpn (.a(rp_tot), .inc(ret_p), .y(rp_tot_n));
    wire [15:0] rtot3_w;
    ot_hdc_kinc #(.W(16), .K(KK)) u_r3 (.a(rtot2_r), .inc(1'b1), .y(rtot3_w));
    assign rtot1_n = ret_i ? rtot2_r : rtot1_r;                  // n_rtot + 1
    wire [15:0] rtot2_n = ret_i ? rtot3_w : rtot2_r;             // n_rtot + 2
    ot_hdc_kinc #(.W(16), .K(KK)) u_emn (.a(emitted), .inc(EMIT[16]), .y(emitted_n));
    ot_hdc_kadd #(.W(24), .K(KK)) u_acc2 (.a(acc2_r), .b({8'd0, a_chmul}), .cin(1'b0), .s(acc2_n), .cout(unused_lc[5]));
    ot_hdc_kadd #(.W(16), .K(KK)) u_nd1 (.a(a_chlead), .b(acc2_r[23:8]), .cin(1'b0), .s(need1_n), .cout(unused_lc[6]));
    wire [23:0] acc_n = (CTL12 >= 2) ? acc1_r : a_acc + {8'd0, a_chmul};
    // group 1: the position
    always @(posedge clk) begin
        if (PROM[1]) begin a_no <= p_no; a_ni <= p_ni; o_v <= 0; i_v <= 0; end
        else if (EMIT[1]) begin
            if (WRAPS[1]) begin o_v <= s_ov; i_v <= 0; end
            else i_v <= s_iv;
        end
    end
    // group 2: the layout and depths
    always @(posedge clk) if (PROM[2]) begin
        a_ls <= p_ls; a_lvw <= p_lvw; a_nsh <= p_nsh; a_lt <= p_lt; a_L <= p_L;
        a_packed <= p_packed; a_span <= p_span; a_gather <= p_gather; a_bank <= q_bank; a_wnf <= p_wnf;
        a_gsh <= p_gsh; a_rsh <= p_rsh;
        a_dF <= p_dF; a_dM <= p_dM; a_dS <= p_dS; a_dT <= p_dT; a_dR <= p_dR;
        a_ssz <= p_ssz; a_nslot <= p_nslot; a_hls0 <= p_hls0;
    end
    always @(posedge clk) if (PROM[3]) a_istep <= p_istep;
    always @(posedge clk) if (PROM[4]) a_ostep <= p_ostep;
    // group 5: the result and KV rows
    always @(posedge clk) begin
        if (PROM[5]) begin a_rstep <= p_rstep; rrow <= q_rbase; krow <= q_orow; end
        else if (EMIT[5] && WRAPS[5]) begin rrow <= s_rrow; krow <= s_krow; end
    end
    // groups 6 / 7 / 25: the row and the vector bases
    always @(posedge clk) begin
        if (PROM[6]) row <= {q_obase, q_dbase, q_cbase, q_bbase, q_abase};
        else if (EMIT[6] && WRAPS[6]) row <= s_row;
    end
    always @(posedge clk) begin
        if (PROM[7]) vb[0 +: 3*AW] <= {q_cbase, q_bbase, q_abase};
        else if (EMIT[7]) vb[0 +: 3*AW] <= WRAPS[7] ? s_row[0 +: 3*AW] : s_vb[0 +: 3*AW];
    end
    always @(posedge clk) begin
        if (PROM[25]) vb[3*AW +: 2*AW] <= {q_obase, q_dbase};
        else if (EMIT[25]) vb[3*AW +: 2*AW] <= WRAPS[25] ? s_row[3*AW +: 2*AW] : s_vb[3*AW +: 2*AW];
    end
    // groups 8 / 9 / 10: the op fields
    always @(posedge clk) if (PROM[8]) begin
        a_asrc <= q_asrc; a_bsrc <= q_bsrc; a_csrc <= q_csrc; a_dsrc <= q_dsrc; a_aind <= q_aind;
        a_dst <= q_dst; a_red <= q_red; a_m2 <= q_m2; a_e2 <= q_e2; a_chsrc <= q_chsrc;
        a_bhalf <= q_bhalf; a_cpair <= q_cpair; a_arnd <= q_arnd; a_arelu <= q_arelu; a_amin <= q_amin;
        a_cclip <= q_cclip; a_rnd <= q_rnd; a_redsq <= q_redsq; a_redrnd <= q_redrnd;
        a_m1 <= q_m1; a_qm <= q_qm; a_ad <= q_ad; a_sfu <= q_sfu; a_e1 <= q_e1; a_imm1 <= q_imm1;
    end
    always @(posedge clk) if (PROM[9]) begin a_imm2 <= q_imm2; a_imm3 <= q_imm3; end
    always @(posedge clk) if (PROM[10]) begin
        a_obase <= q_obase; a_aibase <= q_aibase;
        a_seq <= q_seq; a_chseq <= q_chseq; a_chlead <= q_chlead; a_chmul <= q_chmul;
    end
    // group 11: the vector count, the chaining accumulator and its needs
    always @(posedge clk) begin
        if (PROM[11]) begin
            a_nv <= 0; a_acc <= 0;
            acc1_r <= {8'd0, q_chmul}; acc2_r <= {7'd0, q_chmul, 1'b0};
            need0_r <= q_chlead; need1_r <= (CTL12 >= 2) ? r2_need1 : q_chlead + {8'd0, q_chmul[15:8]};
        end else if (EMIT[11]) begin
            if (!STRT[11]) a_mark <= e_tot;
            a_nv <= a_nv_p1;
            a_acc <= acc_n;
            acc1_r <= acc2_r; acc2_r <= acc2_n;
            need0_r <= need1_r; need1_r <= need1_n;
        end
    end
    // a half stream's inner stride at slot size 1 (its term is 0; it moves by si every other index)
    always @(posedge clk) if (PROM[12]) begin a_istep_h1 <= q_bsi; a_istep_h3 <= q_dsi; end

    // published chaining state
    reg [7:0]  lst_seq;
    reg [15:0] lst_mark;
    wire [15:0] lst_cnt = rp_tot - lst_mark;
    assign cr_cnt = lst_cnt[15] ? 16'd0 : lst_cnt;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin lst_seq <= 8'hFF; lst_mark <= 0; cr_seq <= 8'hFF; end
        else begin
            if (EMIT[16] && !STRT[16]) begin lst_seq <= a_seq; lst_mark <= e_tot; end
            cr_seq <= (EMIT[16] && !STRT[16]) ? a_seq : lst_seq;
        end
    end

    // =========================================================================================
    // Control pipe: one control word a vector, through the lanes' stage structure
    // =========================================================================================
    // datapath fields
    localparam integer WD = 8 + 4 + 32 + 3 + 32 + 2 + 3 + 3 + 32 + 3 + 3 + 2 + 1 + 2;       // 130
    // retire meta: seq, lastv, red, sq, redrnd, lt, L, span, seglast, nres, rbase, rsh, lastres
    localparam integer WR = 8 + 1 + 2 + 1 + 1 + 4 + 3 + 1 + 1 + 8 + AW + 5 + 1;
    localparam integer WC = WD + WR;
    // CTL12 >= 2: the remaining rows a_no - o_v kept in a register (it moves with o_v)
    reg  [CW-1:0] rem_r;
    wire [CW-1:0] rem_n;
    wire          rem_ge, unused_rem;
    ot_hdc_kadd #(.W(CW), .K(KK)) u_rem (.a(rem_r), .b(~nslot), .cin(1'b1), .s(rem_n), .cout(unused_rem));
    ot_hdc_kge  #(.W(CW), .K(KK)) u_remg (.a(rem_r), .b(nslot), .ge(rem_ge));
    always @(posedge clk) begin
        if (PROM[1]) rem_r <= p_no;
        else if (EMIT[1] && WRAPS[1]) rem_r <= rem_n;
    end
    wire [CW-1:0] rem_rows = (CTL12 >= 2) ? rem_r : a_no - o_v;
    wire          rem_lt = (CTL12 >= 2) ? !rem_ge : (rem_rows < nslot);
    wire [7:0] nres = !a_packed ? 8'd1 : rem_lt ? rem_rows[7:0] : nslot[7:0];
    wire [WC-1:0] cw0 = {a_dsrc, a_csrc, a_bsrc, a_asrc,
                         a_arnd, a_arelu, a_amin, a_cclip, (KIMM != 0) ? (a_imm3[31] ? ~a_imm3 : {1'b1, a_imm3[30:0]}) : a_imm3,
                         a_m1, a_imm1, a_m2, a_qm, a_ad, a_imm2, a_sfu, a_e1, a_e2, a_rnd, a_dst,
                         a_seq, last_v, a_red, a_redsq, a_redrnd, a_lt, a_L, a_span, a_wnf ? last_v : wrap, nres, rrow, a_rsh,
                         last_v && (a_red != RED_NONE)};
    // BROADCAST register: every lane input of the emitted vector (and its control word) is registered once
    // in the controller, so the lanes see no combinational path from the emit decision.  At the die's width
    // this is the register each 64-lane tile takes its copy from.  It adds one cycle to every depth.
    reg              b_emit, b_bank, b_gather, b_cpair;
    reg [CW-1:0]     b_ov, b_iv, b_no, b_ni;
    reg [3:0]        b_ls, b_lvw;
    reg [5*AW-1:0]   b_vb;
    reg [AW-1:0]     b_krow, b_obase, b_aibase;
    reg [1:0]        b_aind, b_dst;
    reg [4:0]        b_gsh;
    reg [7:0]        b_srcs;
    reg [WC-1:0]     b_cw;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) b_emit <= 1'b0; else b_emit <= emit;
    end
    always @(posedge clk) begin
        b_bank <= a_bank; b_gather <= a_gather; b_cpair <= a_cpair; b_ov <= o_v; b_iv <= i_v; b_no <= a_no;
        b_ni <= a_ni; b_ls <= a_ls; b_lvw <= a_ls + a_nsh; b_vb <= vb; b_krow <= krow; b_obase <= a_obase;
        b_aibase <= a_aibase; b_aind <= a_aind; b_dst <= a_dst; b_gsh <= a_gsh;
        b_srcs <= {a_dsrc, a_csrc, a_bsrc, a_asrc}; b_cw <= cw0;
    end
    // BROADCAST TREE: BCAST_STAGES register stages from the broadcast register to the lanes' leaf register.
    // Everything that travels to the lanes crosses it together: the vector, its control word (the control
    // pipe below starts at the leaf) and the op set-up's offset loads, so the lanes see the same sequence as
    // with no stages, BCAST_STAGES cycles later.  The first BCAST_STAGES - 1 stages are the tree (tr_*, here);
    // the LAST stage is each lane's own leaf register (ot_hdc_v41x_vec_lane LEAF = 1), which holds the lane's
    // partial addresses instead of the raw fields.  The control pipe takes the same last stage here (t_*).
    localparam integer WB = 3 + 4 * CW + 8 + 8 * AW + 4 + 5 + 8 + WC;
    localparam integer WL = 1 + 5 * LN * AW;
    localparam integer BT = (BCAST_STAGES > 0) ? BCAST_STAGES - 1 : 0;     // stages outside the lanes
    wire [WB-1:0]    b_bus = {b_bank, b_gather, b_cpair, b_ov, b_iv, b_no, b_ni, b_ls, b_lvw, b_vb, b_krow, b_obase,
                              b_aibase, b_aind, b_dst, b_gsh, b_srcs, b_cw};
    wire [WB-1:0]    tr_bus;
    wire [WL-1:0]    tr_lbus;
    wire             tr_emit, tr_ld, t_emit, t_gather, bt_live;
    wire             tr_bank, tr_gather, tr_cpair;
    wire [CW-1:0]    tr_ov, tr_iv, tr_no, tr_ni;
    wire [3:0]       tr_ls, tr_lvw;
    wire [5*AW-1:0]  tr_vb;
    wire [AW-1:0]    tr_krow, tr_obase, tr_aibase;
    wire [1:0]       tr_aind, tr_dst;
    wire [4:0]       tr_gsh;
    wire [7:0]       tr_srcs;
    wire [WC-1:0]    tr_cw, t_cw;
    wire             tr_ldbank;
    wire [5*LN*AW-1:0] tr_ldc;
    ot_hdc_delay #(.W(WB), .D(BT)) u_bt (.clk(clk), .rst_n(rst_n), .d(b_bus), .q(tr_bus));
    ot_hdc_delay #(.W(WL), .D(BT)) u_bl (.clk(clk), .rst_n(rst_n), .d({q_bank, p_terms}), .q(tr_lbus));
    assign {tr_bank, tr_gather, tr_cpair, tr_ov, tr_iv, tr_no, tr_ni, tr_ls, tr_lvw, tr_vb, tr_krow, tr_obase, tr_aibase, tr_aind,
            tr_dst, tr_gsh, tr_srcs, tr_cw} = tr_bus;
    assign {tr_ldbank, tr_ldc} = tr_lbus;
    generate if (BCAST_STAGES == 0) begin : g_bt0
        assign {tr_emit, tr_ld} = {b_emit, lane_ld};
        assign {t_emit, t_gather, t_cw} = {b_emit, b_gather, b_cw};
        assign bt_live = 1'b0;
    end else begin : g_bt
        reg [BCAST_STAGES-1:0] bt_e, bt_l;      // valid of every stage, the leaf's included
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin bt_e <= {BCAST_STAGES{1'b0}}; bt_l <= {BCAST_STAGES{1'b0}}; end
            else begin
                bt_e <= (bt_e << 1) | {{(BCAST_STAGES-1){1'b0}}, b_emit};
                bt_l <= (bt_l << 1) | {{(BCAST_STAGES-1){1'b0}}, lane_ld};
            end
        end
        assign tr_emit = (BCAST_STAGES > 1) ? bt_e[BT > 0 ? BT - 1 : 0] : b_emit;
        assign tr_ld   = (BCAST_STAGES > 1) ? bt_l[BT > 0 ? BT - 1 : 0] : lane_ld;
        assign t_emit = bt_e[BCAST_STAGES-1];
        reg          t_g;
        reg [WC-1:0] t_c;
        always @(posedge clk) begin t_g <= tr_gather; t_c <= tr_cw; end
        assign t_gather = t_g;
        assign t_cw = t_c;
        assign bt_live = |{bt_e, bt_l};
    end endgenerate
    // F-line: depth 3 or 5
    wire [WC-1:0] cwx;
    wire          vx, col_f, bz_f, bz_m, bz_s;
    ot_hdc_v41x_ins #(.W(WC), .K(2), .DEPTHS({H_F5, H_F3}), .DMAX(5 + OPR + CAPR + GSH)) u_cf (.clk(clk), .rst_n(rst_n),
        .v(t_emit), .sel({t_gather, !t_gather}), .d(t_cw), .vo(vx), .q(cwx), .coll(col_f), .busy(bz_f));
    `define CW_SRCS(w)  w[WC-1 -: 8]
    `define CW_ARND(w)  w[WC-9]
    `define CW_ARELU(w) w[WC-10]
    `define CW_AMIN(w)  w[WC-11]
    `define CW_CCLIP(w) w[WC-12]
    `define CW_IMM3(w)  w[WC-13 -: 32]
    `define CW_M1(w)    w[WC-45 -: 3]
    `define CW_IMM1(w)  w[WC-48 -: 32]
    `define CW_M2(w)    w[WC-80 -: 2]
    `define CW_QM(w)    w[WC-82 -: 3]
    `define CW_AD(w)    w[WC-85 -: 3]
    `define CW_IMM2(w)  w[WC-88 -: 32]
    `define CW_SFU(w)   w[WC-120 -: 3]
    `define CW_E1(w)    w[WC-123 -: 3]
    `define CW_E2(w)    w[WC-126 -: 2]
    `define CW_RND(w)   w[WC-128]
    `define CW_DST(w)   w[WC-129 -: 2]
    // PRE -> M1 inputs
    reg  [WC-1:0] cwp;
    reg           vp;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) vp <= 1'b0; else vp <= vx;
    end
    always @(posedge clk) cwp <= cwx;
    wire p_div = (`CW_M1(cwp) == M1_DIVB) || (`CW_M1(cwp) == M1_DIVIMM);
    // M1-line: 3 or 19
    wire [WC-1:0] cwm;
    wire          vm, col_m;
    ot_hdc_v41x_ins #(.W(WC), .K(2), .DEPTHS({H_MD, H_MM}), .DMAX(DDIV + OPR)) u_cm (.clk(clk), .rst_n(rst_n),
        .v(vp), .sel({p_div, !p_div}), .d(cwp), .vo(vm), .q(cwm), .coll(col_m), .busy(bz_m));
    // AD in (+MLAT: M2), S in (+MLAT + ALAT: AD)
    wire [WC-1:0] cwa, cwi;
    wire [MLAT+ALAT+OPR:0] vml;
    ot_hdc_delay #(.W(WC), .D(MLAT)) u_ca (.clk(clk), .rst_n(rst_n), .d(cwm), .q(cwa));
    ot_hdc_delay #(.W(WC), .D(ALAT + OPR)) u_ci (.clk(clk), .rst_n(rst_n), .d(cwa), .q(cwi));
    ot_hdc_vline #(.D(MLAT + ALAT + OPR)) u_vml (.clk(clk), .rst_n(rst_n), .v(vm), .vd(vml));
    wire vi = vml[MLAT + ALAT + OPR];
    wire [2:0] i_s = `CW_SFU(cwi);
    wire [6:0] s_sel = {i_s == SFU_EGATE, i_s == SFU_SPSQRT, i_s == SFU_SQRT, i_s == SFU_RSQRT,
                        i_s == SFU_SIGM || i_s == SFU_SILU, i_s == SFU_EXP, i_s == SFU_NONE};
    wire [WC-1:0] cws;
    wire          vs, col_s;
    generate if(SPLIT_S_PIPE==0)begin:g_legacy_s
    ot_hdc_v41x_ins #(.W(WC), .K(7), .DEPTHS({H_EG, H_SP, H_SQRT, H_RSQ, H_SIG, H_EXP, 16'd0}),
                      .DMAX(D_SP)) u_cs (.clk(clk), .rst_n(rst_n), .v(vi), .sel(s_sel), .d(cwi), .vo(vs), .q(cws),
                      .coll(col_s), .busy(bz_s));
    end else begin:g_split_s
        wire [74:0] ops_in={`CW_SFU(cwi),`CW_E1(cwi),`CW_IMM2(cwi),`CW_E2(cwi),`CW_IMM1(cwi),`CW_RND(cwi),`CW_DST(cwi)};
        wire [74:0] ops_hi,ops_lo;
        wire [59:0] meta_hi,meta_lo;
        wire ohv,olv,mhv,mlv,ohc,olc,mhc,mlc,ohb,olb,mhb,mlb;
        ot_hgi_sfu_ctl_chunk #(.W(75),.OFFSET(138),.PIN_CAPTURE(1),.STATUS_REG(1)) u_oph
            (.clk(clk_s_ops_hi),.rst_n(rst_n),.v(vi),.sfu(i_s),.d(ops_in),.tail_d(75'd0),.tail_v(1'b0),.q(ops_hi),.vo(ohv),.coll(ohc),.busy(ohb));
        ot_hgi_sfu_ctl_chunk #(.W(75),.OFFSET(0),.PIN_CAPTURE(1),.STATUS_REG(1)) u_opl
            (.clk(clk_s_ops_lo),.rst_n(rst_n),.v(vi),.sfu(i_s),.d(ops_in),.tail_d(ops_hi),.tail_v(ohv),.q(ops_lo),.vo(olv),.coll(olc),.busy(olb));
        ot_hgi_sfu_ctl_chunk #(.W(60),.OFFSET(138),.PIN_CAPTURE(1),.STATUS_REG(1)) u_mth
            (.clk(clk_s_meta_hi),.rst_n(rst_n),.v(vi),.sfu(i_s),.d(cwi[59:0]),.tail_d(60'd0),.tail_v(1'b0),.q(meta_hi),.vo(mhv),.coll(mhc),.busy(mhb));
        ot_hgi_sfu_ctl_chunk #(.W(60),.OFFSET(0),.PIN_CAPTURE(1),.STATUS_REG(1)) u_mtl
            (.clk(clk_s_meta_lo),.rst_n(rst_n),.v(vi),.sfu(i_s),.d(cwi[59:0]),.tail_d(meta_hi),.tail_v(mhv),.q(meta_lo),.vo(mlv),.coll(mlc),.busy(mlb));
        wire now=vi&&(i_s==SFU_NONE);
        wire [74:0] ops=now?ops_in:ops_lo;
        wire [59:0] meta=now?cwi[59:0]:meta_lo;
        wire [2:0] fn,e1;
        wire [31:0] imm2,imm1;
        wire [1:0] e2,dst;
        wire rnd;
        assign {fn,e1,imm2,e2,imm1,rnd,dst}=ops;
        assign cws={8'd0,4'd0,32'd0,3'd0,imm1,2'd0,3'd0,3'd0,imm2,fn,e1,e2,rnd,dst,meta};
        assign vs=now||olv;
        assign col_s=ohc||olc||mhc||mlc||(now&&olv);
        assign bz_s=ohb||olb||mhb||mlb;
        // Root data/valid edges unchanged. Registered status observation needs composed fault/idle qualification.
    end endgenerate
    // E2 in (+MLAT: E1), OUT in (+2 MLAT), retire (+2 MLAT + 1)
    wire [WC-1:0] cwe, cwo, cwr;
    wire [2*MLAT+1+OPR:0] vsl;
    ot_hdc_delay #(.W(WC), .D(MLAT + OPR)) u_ce (.clk(clk), .rst_n(rst_n), .d(cws), .q(cwe));
    ot_hdc_delay #(.W(WC), .D(MLAT)) u_co (.clk(clk), .rst_n(rst_n), .d(cwe), .q(cwo));
    ot_hdc_delay #(.W(WC), .D(1)) u_cr (.clk(clk), .rst_n(rst_n), .d(cwo), .q(cwr));
    ot_hdc_vline #(.D(2 * MLAT + 1 + OPR)) u_vsl (.clk(clk), .rst_n(rst_n), .v(vs), .vd(vsl));
    wire retire = vsl[2 * MLAT + 1 + OPR];
    // retire meta
    wire [WR-1:0] rm = cwr[WR-1:0];
    wire [7:0]  r_seq   = rm[WR-1 -: 8];
    wire        r_lastv = rm[WR-9];
    wire [1:0]  r_red   = rm[WR-10 -: 2];
    wire        r_sq    = rm[WR-12];
    wire        r_rnd   = rm[WR-13];
    wire [3:0]  r_lt    = rm[WR-14 -: 4];
    wire [2:0]  r_L     = rm[WR-18 -: 3];
    wire        r_span  = rm[WR-21];
    wire        r_wrap  = rm[WR-22];
    wire [7:0]  r_nres  = rm[WR-23 -: 8];
    wire [AW-1:0] r_rbase = rm[WR-31 -: AW];
    wire [4:0]  r_rsh   = rm[5:1];
    wire        r_lastres = rm[0];

    // =========================================================================================
    // Lanes
    // =========================================================================================
    // Lane array is external: sixteen unchanged CLOSED lanes behind four-edge mappers plus CLOSED b_q input stage.
    wire [1199:0] padded_terms;
    for (genvar stream = 0; stream < 5; stream = stream + 1) begin:g_term_pad
        for (genvar bit_j = 0; bit_j < 10; bit_j = bit_j + 1) begin:g_term
            if (bit_j < LN) assign padded_terms[(stream*10+bit_j)*24+:24] = tr_ldc[(stream*LN+bit_j)*AW+:AW];
            else assign padded_terms[(stream*10+bit_j)*24+:24] = 24'd0;
        end
    end
    assign grid_control = {tr_ld, tr_ldbank, padded_terms, tr_emit, tr_bank, tr_ov, tr_iv, tr_no, tr_ni, tr_ls, tr_lvw, tr_vb, tr_krow, tr_obase, tr_aibase, tr_aind, tr_gsh, tr_cpair, tr_dst, tr_srcs, `CW_ARND(cwx), `CW_ARELU(cwx), `CW_AMIN(cwx), `CW_CCLIP(cwx), `CW_IMM3(cwx), `CW_M1(cwp), `CW_IMM1(cwp), `CW_M1(cwm), `CW_M2(cwm), `CW_QM(cwm), `CW_IMM1(cwm), `CW_AD(cwa), `CW_IMM2(cwa), `CW_SFU(cwi), `CW_SFU(cws), `CW_E1(cws), `CW_IMM2(cws), `CW_E2(cwe), `CW_IMM1(cwe), `CW_RND(cwo), `CW_DST(cwo)};
    // Reductions/side operations are refused at instruction admission; no arithmetic surrogate.
    wire [7:0] red_seq = 8'd0;
    wire red_lastres = 1'b0, red_ev = 1'b0, red_busy = 1'b0, red_f = 1'b0, side_f = 1'b0;
    wire [NR-1:0] l_res_we = '0;
    wire [NR*AW-1:0] l_res_addr = '0;
    wire [NR*32-1:0] l_res_data = '0;

    // =========================================================================================
    // RETURN: RET_STAGES register stages from the lanes and the reducer to the vector memory.  The
    // write events travel beside them: at RET_STAGES (the write lands: published state, the bench trace)
    // and at DI (this unit's own consumers, which read BCAST_STAGES after their emit)
    // =========================================================================================
    ot_hdc_delay #(.W(2 * N), .D(0), .RESET(1)) u_rwe (.clk(clk), .rst_n(rst_n),
        .d({l_vm_we, l_kv_we}), .q({vm_we, kv_we}));
    ot_hdc_delay #(.W(N * (2 * AW + 64)), .D(0)) u_rwd (.clk(clk), .rst_n(rst_n),
        .d({l_vm_waddr, l_vm_wdata, l_kv_waddr, l_kv_wdata}), .q({vm_waddr, vm_wdata, kv_waddr, kv_wdata}));
    ot_hdc_delay #(.W(NR), .D(RET_STAGES), .RESET(1)) u_rre (.clk(clk), .rst_n(rst_n), .d(l_res_we), .q(res_we));
    ot_hdc_delay #(.W(NR * (AW + 32)), .D(RET_STAGES)) u_rrd (.clk(clk), .rst_n(rst_n),
        .d({l_res_addr, l_res_data}), .q({res_addr, res_data}));
    wire rt_live;
    generate if (RET_STAGES == 0) begin : g_rt0
        assign {ret_p, ret_p_seq, ret_p_last} = {retire, r_seq, r_lastv};
        assign {res_p, res_p_seq, res_p_last} = {red_ev, red_seq, red_lastres};
        assign rt_live = 1'b0;
    end else begin : g_rt
        reg [RET_STAGES-1:0] rt_v, rs_v;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin rt_v <= {RET_STAGES{1'b0}}; rs_v <= {RET_STAGES{1'b0}}; end
            else begin
                rt_v <= (rt_v << 1) | {{(RET_STAGES-1){1'b0}}, retire};
                rs_v <= (rs_v << 1) | {{(RET_STAGES-1){1'b0}}, red_ev};
            end
        end
        wire [8:0] rt_m, rs_m;
        ot_hdc_delay #(.W(9), .D(RET_STAGES)) u_rtm (.clk(clk), .rst_n(rst_n), .d({r_seq, r_lastv}), .q(rt_m));
        ot_hdc_delay #(.W(9), .D(RET_STAGES)) u_rsm (.clk(clk), .rst_n(rst_n), .d({red_seq, red_lastres}), .q(rs_m));
        assign {ret_p, ret_p_seq, ret_p_last} = {rt_v[RET_STAGES-1], rt_m};
        assign {res_p, res_p_seq, res_p_last} = {rs_v[RET_STAGES-1], rs_m};
        assign rt_live = |{rt_v, rs_v};
    end endgenerate
    generate if (DI == 0) begin : g_di0
        assign {ret_i, ret_i_seq, ret_i_last} = {retire, r_seq, r_lastv};
        assign {res_i, res_i_seq, res_i_last} = {red_ev, red_seq, red_lastres};
    end else begin : g_di
        wire [9:0] di_r, di_s;
        ot_hdc_delay #(.W(1), .D(DI), .RESET(1)) u_dirv (.clk(clk), .rst_n(rst_n), .d(retire), .q(di_r[9]));
        ot_hdc_delay #(.W(9), .D(DI)) u_dirm (.clk(clk), .rst_n(rst_n), .d({r_seq, r_lastv}), .q(di_r[8:0]));
        ot_hdc_delay #(.W(1), .D(DI), .RESET(1)) u_disv (.clk(clk), .rst_n(rst_n), .d(red_ev), .q(di_s[9]));
        ot_hdc_delay #(.W(9), .D(DI)) u_dism (.clk(clk), .rst_n(rst_n), .d({red_seq, red_lastres}), .q(di_s[8:0]));
        assign {ret_i, ret_i_seq, ret_i_last} = di_r;
        assign {res_i, res_i_seq, res_i_last} = di_s;
    end endgenerate

    assign dbg_emit = emit;
    assign dbg_eseq = a_seq;
    assign dbg_ret = ret_p;             // the trace records writes when they land
    assign dbg_rseq = ret_p_seq;
    assign dbg_res = res_p;
    assign dbg_sseq = res_p_seq;
    // published completion (writes landed) and the internal credit copies
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            cr_dseq <= 8'hFF; cr_rseq <= 8'hFF; i_dseq <= 8'hFF; i_rseq <= 8'hFF; emitted <= 0; retire_o <= 1'b0;
        end else begin
            if (ret_p && ret_p_last) cr_dseq <= ret_p_seq;
            if (res_p && res_p_last) cr_rseq <= res_p_seq;
            if (ret_i && ret_i_last) i_dseq <= ret_i_seq;
            if (res_i && res_i_last) i_rseq <= res_i_seq;
            emitted <= emitted_n;
            retire_o <= ret_p;
        end
    end

    // =========================================================================================
    // Status
    // =========================================================================================
    wire pipe_live = b_emit || bt_live || rt_live || bz_f || vp || bz_m || (|vml) || bz_s || (|vsl);
    wire idle_c = (pst == 2'd0) && !a_v && !pipe_live && !red_busy;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin idle <= 1'b1; fault <= 1'b0; order_fault <= 1'b0; end
        else begin
            idle <= idle_c && !accept;
            fault <= (|l_fault) || side_f || red_f || (promote && p_bad);
            order_fault <= (|l_coll) || col_f || col_m || col_s;
        end
    end
    `undef CW_SRCS
    `undef CW_ARND
    `undef CW_ARELU
    `undef CW_AMIN
    `undef CW_CCLIP
    `undef CW_IMM3
    `undef CW_M1
    `undef CW_IMM1
    `undef CW_M2
    `undef CW_QM
    `undef CW_AD
    `undef CW_IMM2
    `undef CW_SFU
    `undef CW_E1
    `undef CW_E2
    `undef CW_RND
    `undef CW_DST
endmodule
