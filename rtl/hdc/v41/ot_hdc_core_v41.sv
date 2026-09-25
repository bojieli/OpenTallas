`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Hardwired decode core, DeepSeek-V4.1 configuration: decodes one token of the
// reduced DeepSeek-V4.1-Flash (tools/hdc_program_v41.py, format
// tools/hdc_isa_v41.py).
//
// The sibling of ot_hdc_core (the reduced Qwen3 core).  It shares the matrix-
// vector engine (ot_hdc_matvec, with its FP32-weight lane mode for the
// hyper-connection projections) and the arithmetic primitives, and adds three
// units:
//
//   SU  ot_hdc_v41_stream  the four-operand stream pipeline (norms, RoPE,
//                          softmax, divides, sigmoid/SiLU/softplus, mixes)
//   QE  ot_hdc_v41_qe      activation quantiser + block-dot lanes (FP8/FP4)
//   XU  ot_hdc_v41_xu      top-k SELECT, Sinkhorn, Engram hash and gather
//
// The sequencer fetches an instruction, adds the per-token DYN values, skips it
// when its predicate fails or a count is zero, waits for the units named in
// its `wait` mask to drain (the program generator derives the mask from region
// hazards, so independent units overlap), and issues it when its unit is
// ready.  Every unit is a fixed pipeline that never stalls on its own data.
//
// Memories sit outside the core behind synchronous-read ports.
// ---------------------------------------------------------------------------
module ot_hdc_core_v41 #(
    parameter integer INSTR_BITS = 1536,
    parameter integer W    = 16,
    parameter integer G    = 4,
    parameter integer IL   = 8,
    parameter integer BL   = 16,
    parameter integer QLB  = 272,
    parameter integer AW   = 24,
    parameter integer NW   = 16,
    parameter integer PAW  = 14,
    parameter integer DIM  = 160,
    parameter integer TOPK = 16
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              start,
    input  wire [NW-1:0]     token,
    input  wire [NW-1:0]     pos,
    output reg               done,
    output reg  [NW-1:0]     next_token,
    output reg  [31:0]       next_val,
    output reg  [31:0]       cycles,
    output reg               fault,
    // Engram hash history priming (single-step tests)
    input  wire              prime_v,
    input  wire              prime_first,
    input  wire [11:0]       prime_cid,
    // program ROM
    output reg               prog_re,
    output reg  [PAW-1:0]    prog_addr,
    input  wire [INSTR_BITS-1:0] prog_q,
    // BF16 weight ROM: matrix engine, and the stream unit's embedding port
    output wire              wrom_re,
    output wire [AW-1:0]     wrom_addr,
    input  wire [G*W*16-1:0] wrom_q,
    output wire              ewrom_re,
    output wire [AW-1:0]     ewrom_addr,
    input  wire [G*W*16-1:0] ewrom_q,
    // quantised weight ROM, Engram table ROM
    output wire              qrom_re,
    output wire [AW-1:0]     qrom_addr,
    input  wire [BL*QLB-1:0] qrom_q,
    output wire              erom_re,
    output wire [AW-1:0]     erom_addr,
    input  wire [263:0]      erom_q,
    // constant ROM: four stream ports and one auxiliary port
    output wire [3:0]        crom_re,
    output wire [4*AW-1:0]   crom_addr,
    input  wire [4*64-1:0]   crom_q,
    output wire              xcrom_re,
    output wire [AW-1:0]     xcrom_addr,
    input  wire [63:0]       xcrom_q,
    // KV SRAM
    output wire              kv_re,
    output wire [G*AW-1:0]   kv_raddr,
    input  wire [G*W*32-1:0] kv_q,
    output wire              kv_we,
    output wire [AW-1:0]     kv_waddr,
    output wire [31:0]       kv_wdata,
    // vector memory
    output wire [G-1:0]      vx_re,           // matrix-engine x reads
    output wire [G*AW-1:0]   vx_addr,
    input  wire [G*32-1:0]   vx_q,
    output wire [3:0]        vs_re,           // stream operand reads A..D
    output wire [4*AW-1:0]   vs_addr,
    input  wire [4*32-1:0]   vs_q,
    output wire              vi_re,           // stream gather index
    output wire [AW-1:0]     vi_addr,
    input  wire [31:0]       vi_q,
    output wire              vq_re,           // QE expert index
    output wire [AW-1:0]     vq_addr,
    input  wire [31:0]       vq_q,
    output wire              vr_re,           // XU element read
    output wire [AW-1:0]     vr_addr,
    input  wire [31:0]       vr_q,
    output wire              wqr_re,          // QE 32-element read
    output wire [AW-1:0]     wqr_addr,
    input  wire [1023:0]     wqr_q,
    output wire              wxr_re,          // XU 32-element read
    output wire [AW-1:0]     wxr_addr,
    input  wire [1023:0]     wxr_q,
    output wire [G-1:0]      vw_me_we,
    output wire [G*AW-1:0]   vw_me_addr,
    output wire [G*W-1:0]    vw_me_mask,
    output wire [G*W*32-1:0] vw_me_data,
    output wire              vw_su_we,
    output wire [AW-1:0]     vw_su_addr,
    output wire [31:0]       vw_su_data,
    output wire              vw_rd_we,
    output wire [AW-1:0]     vw_rd_addr,
    output wire [31:0]       vw_rd_data,
    output wire              vw_xe_we,        // XU element write
    output wire [AW-1:0]     vw_xe_addr,
    output wire [31:0]       vw_xe_data,
    output wire              ww_q_we,         // QE masked 32-element write
    output wire [AW-1:0]     ww_q_addr,
    output wire [31:0]       ww_q_mask,
    output wire [1023:0]     ww_q_data,
    output wire              ww_x_we,         // XU masked 32-element write
    output wire [AW-1:0]     ww_x_addr,
    output wire [31:0]       ww_x_mask,
    output wire [1023:0]     ww_x_data,
    // observation: every matrix-vector result word
    output wire              me_ov,
    output wire [G*AW-1:0]   me_oaddr,
    output wire [G*W-1:0]    me_omask,
    output wire [G*W*32-1:0] me_odata,
    // per-unit activity (cycle accounting)
    output wire [3:0]        unit_busy,
    output reg  [2:0]        issue_unit       // unit of the instruction issued this cycle (0: none)
);
    `include "ot_hdc_isa_v41.svh"
    localparam integer LG = $clog2(W * G);

    // -- sequencer -----------------------------------------------------------------------------
    localparam [3:0] S_IDLE = 0, S_DYN = 1, S_FETCH = 2, S_WAIT = 3, S_CAP = 4, S_DEC = 5,
                     S_ISSUE = 6, S_GO = 7;
    reg [3:0]  st;
    reg [PAW-1:0] pc;
    reg [NW-1:0] tok_r, pos_r;
    reg [AW-1:0] dyn [0:31];
    reg [INSTR_BITS-1:0] ir;
    reg        me_go, su_go, qe_go, xu_go;
    wire       me_ready, me_idle, su_ready, su_idle, qe_ready, qe_idle, xu_ready, xu_idle;
    wire       me_fault, su_fault, qe_fault, xu_fault;
    wire [NW-1:0] am_idx;
    wire [31:0] am_val;
    wire       am_any;
    wire [15:0] me_progress;

    `define F(name) ir[O_``name +: W_``name]
    `define DY(name) dyn[ir[O_``name +: W_``name]]

    reg [2:0]  d_unit;
    reg [3:0]  d_wait;
    reg        d_skip;
    // ME
    reg [NW-1:0] me_nout, me_tiles, me_k;
    reg          me_wsrc, me_round, me_oen, me_amax, me_mmode, me_f32;
    reg [AW-1:0] me_wbase, me_ts, me_ks, me_js, me_xbase, me_obase, me_xks, me_xjs, me_ots, me_ojs, me_xcs;
    reg [2:0]    me_jsh;
    reg [1:0]    me_split;
    // SU
    reg [NW-1:0] su_nout, su_nin;
    reg [1:0]    a_src, b_src, c_src, d_src, a_ind, dst, red, m2, e2;
    reg [AW-1:0] a_base, a_so, a_si, a_ibase, b_base, b_so, b_si, c_base, c_so, c_si, d_base, d_so, d_si;
    reg [AW-1:0] o_base, o_so, o_si, o_row, r_base, r_so;
    reg          b_half, c_pair, a_rnd, a_relu, a_min, c_clip, rnd, red_sq, red_whole, red_rnd;
    reg [2:0]    m1, qm, ad, sfu, e1;
    reg [31:0]   imm1, imm2, imm3;
    // QE
    reg [1:0]    qe_mode;
    reg          qe_fp4, qe_ind;
    reg [AW-1:0] qe_xbase, qe_wbase, qe_ibase, qe_istride, qe_obase;
    reg [7:0]    qe_nb;
    reg [NW-1:0] qe_nout, qe_tiles;
    // XU
    reg [1:0]    xu_op;
    reg [AW-1:0] xu_src, xu_dst;
    reg [NW-1:0] xu_n;
    reg [4:0]    xu_k;
    reg          xu_layer;

    wire unit_ready = (d_unit == 3'd1) ? me_ready : (d_unit == 3'd2) ? su_ready :
                      (d_unit == 3'd3) ? qe_ready : xu_ready;
    wire [3:0] idles = {xu_idle, qe_idle, su_idle, me_idle};
    wire [3:0] gos = {xu_go, qe_go, su_go, me_go};
    //: the wait mask names units whose in-flight work must have drained
    wire waited = ((d_wait & ~(idles & ~gos)) == 4'd0);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; pc <= 0; done <= 1'b0; prog_re <= 1'b0;
            me_go <= 1'b0; su_go <= 1'b0; qe_go <= 1'b0; xu_go <= 1'b0; cycles <= 0; next_token <= 0;
            issue_unit <= 0;
        end else begin
            me_go <= 1'b0; su_go <= 1'b0; qe_go <= 1'b0; xu_go <= 1'b0; prog_re <= 1'b0; issue_unit <= 0;
            if (st != S_IDLE) cycles <= cycles + 1;
            case (st)
                S_IDLE: if (start) begin
                    tok_r <= token; pos_r <= pos; pc <= 0; done <= 1'b0; cycles <= 0;
                    st <= S_DYN;
                end
                S_DYN: st <= S_FETCH;
                S_FETCH: begin prog_re <= 1'b1; prog_addr <= pc; st <= S_WAIT; end
                S_WAIT: st <= S_CAP;
                S_CAP: begin ir <= prog_q; st <= S_DEC; end
                S_DEC: st <= S_ISSUE;
                S_ISSUE: begin
                    if (d_unit == 3'd0) begin
                        if (waited) begin
                            done <= 1'b1; next_token <= am_idx; next_val <= am_val; st <= S_IDLE;
                        end
                    end else if (d_skip) begin
                        pc <= pc + 1'b1; st <= S_FETCH;
                    end else if (waited && unit_ready) begin
                        me_go <= (d_unit == 3'd1); su_go <= (d_unit == 3'd2);
                        qe_go <= (d_unit == 3'd3); xu_go <= (d_unit == 3'd4);
                        issue_unit <= d_unit;
                        st <= S_GO;
                    end
                end
                S_GO: begin pc <= pc + 1'b1; st <= S_FETCH; end
                default: st <= S_IDLE;
            endcase
        end
    end

    // DYN values (tools/hdc_isa_v41.dyn_values), once per token
    wire [NW-1:0] p1 = pos_r + 1'b1;
    wire [NW-1:0] n2 = p1 >> 1;
    wire [NW-1:0] ns1 = (p1 < TOPK) ? p1 : TOPK;
    wire [NW-1:0] ns2 = (n2 < TOPK) ? n2 : TOPK;
    function automatic [AW-1:0] rnds(input [NW-1:0] x);
        rnds = (x == 0) ? 0 : ((x - 1) >> LG) + 1;
    endfunction
    integer di;
    always @(posedge clk) if (st == S_DYN) begin
        for (di = 0; di < 32; di = di + 1) dyn[di] <= 0;
        dyn[1] <= tok_r * DIM;
        dyn[2] <= pos_r * 2;
        dyn[3] <= (pos_r == 0) ? 0 : (pos_r - 1) * 2;
        dyn[4] <= pos_r;
        dyn[5] <= p1;
        dyn[6] <= n2;
        dyn[7] <= (n2 == 0) ? 0 : n2 - 1;
        dyn[8] <= ns1;
        dyn[9] <= ns2;
        dyn[10] <= p1 + ns1;
        dyn[11] <= p1 + ns2;
        dyn[12] <= rnds(p1);
        dyn[13] <= rnds(n2);
        dyn[14] <= rnds(p1 + ns1);
        dyn[15] <= rnds(p1 + ns2);
        dyn[16] <= pos_r * 32;
        dyn[17] <= p1 * 32;
        dyn[18] <= pos_r[0] ? 4 : 0;
        dyn[19] <= pos_r[0] ? 64 : 0;
        dyn[20] <= (n2 == 0) ? 0 : (n2 - 1) * 32;
    end

    // Decode: bases and counts add their DYN value.
    wire [NW-1:0] c_me_nout = `F(ME_NOUT) + `DY(ME_D_NOUT);
    wire [NW-1:0] c_me_tiles = `F(ME_TILES) + `DY(ME_D_TILES);
    wire [NW-1:0] c_me_k = `F(ME_K) + `DY(ME_D_K);
    wire [NW-1:0] c_su_nout = `F(SU_NOUT) + `DY(SU_D_NOUT);
    wire [NW-1:0] c_su_nin = `F(SU_NIN) + `DY(SU_D_NIN);
    wire [NW-1:0] c_xu_n = `F(XU_N) + `DY(XU_D_N);
    wire [AW-1:0] c_xu_k = `F(XU_K) + `DY(XU_D_K);
    wire [1:0]    c_pred = `F(PRED);
    wire          pred_ok = (c_pred == 2'd0) || (c_pred == 2'd1 && pos_r[0]) || (c_pred == 2'd2 && pos_r != 0);
    wire [2:0]    c_unit = `F(UNIT);
    wire          zero = (c_unit == 3'd1 && (c_me_nout == 0 || c_me_tiles == 0 || c_me_k == 0)) ||
                         (c_unit == 3'd2 && (c_su_nout == 0 || c_su_nin == 0)) ||
                         (c_unit == 3'd4 && `F(XU_OP) == 2'd0 && c_xu_n == 0);
    always @(posedge clk) if (st == S_DEC) begin
        d_unit <= c_unit; d_wait <= `F(WAIT); d_skip <= !pred_ok || zero;
        me_nout <= c_me_nout; me_tiles <= c_me_tiles; me_k <= c_me_k;
        me_wsrc <= `F(ME_WSRC); me_round <= `F(ME_ROUND); me_oen <= `F(ME_OEN); me_amax <= `F(ME_AMAX);
        me_f32 <= `F(ME_F32);
        me_wbase <= `F(ME_WBASE) + `DY(ME_D_WBASE);
        me_ts <= `F(ME_TS); me_ks <= `F(ME_KS); me_js <= `F(ME_JS);
        me_xbase <= `F(ME_XBASE) + `DY(ME_D_XBASE);
        me_obase <= `F(ME_OBASE) + `DY(ME_D_OBASE);
        me_xks <= `F(ME_XKS); me_xjs <= `F(ME_XJS); me_jsh <= `F(ME_JSH);
        me_ots <= `F(ME_OTS); me_ojs <= `F(ME_OJS); me_mmode <= `F(ME_MMODE);
        me_split <= `F(ME_SPLIT); me_xcs <= `F(ME_XCS);
        su_nout <= c_su_nout; su_nin <= c_su_nin;
        a_src <= `F(A_SRC); a_base <= `F(A_BASE) + `DY(A_D); a_so <= `F(A_SO); a_si <= `F(A_SI);
        a_ind <= `F(A_IND); a_ibase <= `F(A_IBASE);
        b_src <= `F(B_SRC); b_base <= `F(B_BASE) + `DY(B_D); b_so <= `F(B_SO); b_si <= `F(B_SI); b_half <= `F(B_HALF);
        c_src <= `F(C_SRC); c_base <= `F(C_BASE) + `DY(C_D); c_so <= `F(C_SO); c_si <= `F(C_SI); c_pair <= `F(C_PAIR);
        d_src <= `F(D_SRC); d_base <= `F(D_BASE) + `DY(D_D); d_so <= `F(D_SO); d_si <= `F(D_SI);
        a_rnd <= `F(A_RND); a_relu <= `F(A_RELU); a_min <= `F(A_MIN); c_clip <= `F(C_CLIP);
        m1 <= `F(M1); m2 <= `F(M2); qm <= `F(QM); ad <= `F(AD); sfu <= `F(SFU); e1 <= `F(E1); e2 <= `F(E2);
        rnd <= `F(RND); dst <= `F(DST);
        //: transposed-KV writes take the DYN value as a row, not an offset
        o_base <= `F(O_BASE) + ((`F(DST) == 2'd3) ? {AW{1'b0}} : `DY(O_D));
        o_row <= `DY(O_D); o_so <= `F(O_SO); o_si <= `F(O_SI);
        red <= `F(RED); red_sq <= `F(RED_SQ); red_whole <= `F(RED_WHOLE); red_rnd <= `F(RED_RND);
        r_base <= `F(R_BASE); r_so <= `F(R_SO);
        imm1 <= `F(IMM1); imm2 <= `F(IMM2); imm3 <= `F(IMM3);
        qe_mode <= `F(QE_MODE); qe_fp4 <= `F(QE_FP4); qe_ind <= `F(QE_IND);
        qe_xbase <= `F(QE_XBASE); qe_wbase <= `F(QE_WBASE); qe_ibase <= `F(QE_IBASE);
        qe_istride <= `F(QE_ISTRIDE); qe_obase <= `F(QE_OBASE) + `DY(QE_D_OBASE);
        qe_nb <= `F(QE_NB); qe_nout <= `F(QE_NOUT); qe_tiles <= `F(QE_TILES);
        xu_op <= `F(XU_OP); xu_src <= `F(XU_SRC); xu_dst <= `F(XU_DST); xu_n <= c_xu_n;
        xu_k <= c_xu_k[4:0]; xu_layer <= `F(XU_LAYER);
    end
    `undef F
    `undef DY

    // -- units -----------------------------------------------------------------------------------------
    wire me_wrom_re;
    wire [AW-1:0] me_wrom_addr;
    ot_hdc_matvec #(.W(W), .G(G), .IL(IL), .AW(AW), .NW(NW), .F32G(1)) u_me (
        .clk(clk), .rst_n(rst_n), .go(me_go), .ready(me_ready), .idle(me_idle),
        .i_nout(me_nout), .i_tiles(me_tiles), .i_k(me_k), .i_wsrc(me_wsrc), .i_wbase(me_wbase),
        .i_ts(me_ts), .i_ks(me_ks), .i_js(me_js), .i_xbase(me_xbase), .i_xks(me_xks), .i_xjs(me_xjs),
        .i_xcs(me_xcs), .i_jsh(me_jsh), .i_split(me_split), .i_round(me_round), .i_obase(me_obase),
        .i_ots(me_ots), .i_ojs(me_ojs), .i_mmode(me_mmode), .i_oen(me_oen), .i_amax(me_amax), .i_f32(me_f32),
        .wrom_re(wrom_re), .wrom_addr(wrom_addr), .wrom_q(wrom_q),
        .kv_re(kv_re), .kv_addr(kv_raddr), .kv_q(kv_q),
        .x_re(vx_re), .x_addr(vx_addr), .x_q(vx_q),
        .ov(me_ov), .o_we(vw_me_we), .o_addr(vw_me_addr), .o_mask(vw_me_mask), .o_data(vw_me_data),
        .am_idx(am_idx), .am_val(am_val), .am_any(am_any), .progress(me_progress), .fault(me_fault));
    assign me_oaddr = vw_me_addr;
    assign me_omask = vw_me_mask;
    assign me_odata = vw_me_data;

    ot_hdc_v41_stream #(.AW(AW), .NW(NW), .WR(G * W)) u_su (
        .clk(clk), .rst_n(rst_n), .go(su_go), .ready(su_ready), .idle(su_idle),
        .i_nout(su_nout), .i_nin(su_nin), .i_asrc(a_src), .i_bsrc(b_src), .i_csrc(c_src), .i_dsrc(d_src),
        .i_abase(a_base), .i_aso(a_so), .i_asi(a_si), .i_aibase(a_ibase), .i_aind(a_ind),
        .i_bbase(b_base), .i_bso(b_so), .i_bsi(b_si), .i_bhalf(b_half),
        .i_cbase(c_base), .i_cso(c_so), .i_csi(c_si), .i_cpair(c_pair),
        .i_dbase(d_base), .i_dso(d_so), .i_dsi(d_si),
        .i_arnd(a_rnd), .i_arelu(a_relu), .i_amin(a_min), .i_cclip(c_clip),
        .i_m1(m1), .i_m2(m2), .i_qm(qm), .i_ad(ad), .i_sfu(sfu), .i_e1(e1), .i_e2(e2), .i_rnd(rnd),
        .i_dst(dst), .i_obase(o_base), .i_oso(o_so), .i_osi(o_si), .i_orow(o_row),
        .i_red(red), .i_redsq(red_sq), .i_redwhole(red_whole), .i_redrnd(red_rnd), .i_rbase(r_base), .i_rso(r_so),
        .i_imm1(imm1), .i_imm2(imm2), .i_imm3(imm3),
        .vi_re(vi_re), .vi_addr(vi_addr), .vi_q(vi_q),
        .vm_re(vs_re), .vm_addr(vs_addr), .vm_q(vs_q),
        .cr_re(crom_re), .cr_addr(crom_addr), .cr_q(crom_q),
        .wrom_re(ewrom_re), .wrom_addr(ewrom_addr), .wrom_q(ewrom_q),
        .vm_we(vw_su_we), .vm_waddr(vw_su_addr), .vm_wdata(vw_su_data),
        .kv_we(kv_we), .kv_waddr(kv_waddr), .kv_wdata(kv_wdata),
        .red_we(vw_rd_we), .red_addr(vw_rd_addr), .red_data(vw_rd_data), .fault(su_fault));

    ot_hdc_v41_qe #(.AW(AW), .NW(NW), .BL(BL), .IL(IL), .QLB(QLB)) u_qe (
        .clk(clk), .rst_n(rst_n), .go(qe_go), .ready(qe_ready), .idle(qe_idle),
        .i_mode(qe_mode), .i_fp4(qe_fp4), .i_xbase(qe_xbase), .i_nb(qe_nb), .i_nout(qe_nout), .i_tiles(qe_tiles),
        .i_wbase(qe_wbase), .i_ind(qe_ind), .i_ibase(qe_ibase), .i_istride(qe_istride), .i_obase(qe_obase),
        .vi_re(vq_re), .vi_addr(vq_addr), .vi_q(vq_q),
        .xr_re(wqr_re), .xr_addr(wqr_addr), .xr_q(wqr_q),
        .w_we(ww_q_we), .w_addr(ww_q_addr), .w_mask(ww_q_mask), .w_data(ww_q_data),
        .qr_re(qrom_re), .qr_addr(qrom_addr), .qr_q(qrom_q), .fault(qe_fault));

    ot_hdc_v41_xu #(.AW(AW), .NW(NW), .K(TOPK)) u_xu (
        .clk(clk), .rst_n(rst_n), .go(xu_go), .ready(xu_ready), .idle(xu_idle),
        .i_op(xu_op), .i_src(xu_src), .i_dst(xu_dst), .i_n(xu_n), .i_k(xu_k), .i_layer(xu_layer),
        .token(tok_r), .first(pos_r == 0), .prime_v(prime_v && st == S_IDLE), .prime_first(prime_first),
        .prime_cid(prime_cid),
        .vr_re(vr_re), .vr_addr(vr_addr), .vr_q(vr_q), .xr_re(wxr_re), .xr_addr(wxr_addr), .xr_q(wxr_q),
        .vw_we(vw_xe_we), .vw_addr(vw_xe_addr), .vw_data(vw_xe_data),
        .w_we(ww_x_we), .w_addr(ww_x_addr), .w_mask(ww_x_mask), .w_data(ww_x_data),
        .cr_re(xcrom_re), .cr_addr(xcrom_addr), .cr_q(xcrom_q),
        .er_re(erom_re), .er_addr(erom_addr), .er_q(erom_q), .fault(xu_fault));

    assign unit_busy = ~idles;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) fault <= 1'b0;
        else if (start && st == S_IDLE) fault <= 1'b0;
        else if (me_fault || su_fault || qe_fault || xu_fault) fault <= 1'b1;
    end
endmodule
