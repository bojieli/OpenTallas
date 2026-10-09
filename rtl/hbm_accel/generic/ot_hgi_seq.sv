`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// hbm-forks 2026-10-09: the HGI-1 command-processor SEQUENCER, NORMATIVE v1.0 encoding (docs/HBM_GENERIC_INTERFACE.md
// 2.2, 3.1-3.5, 4.2, 6.1-6.8; owner approval REVIEW_20261009 ~11:30 PT).  Owner Claude (hbm-forks, item 4: record
// sequencer + indexed descriptors C3b + the 18-bit token).  Contract and vectors: tools/hgi_seq_vectors.py (Ref).
//   * fetch: records come from the program image in HBM (image_base pages + entry offset in 16 B units, MD section D)
//     through one in-order 32 B-sector read port into a PREFETCH RING of RW 16 B words (RW/2 sectors: one
//     ot_sram_1r1w_256x256 macro at RW = 512; behavioural here, 1-cycle registered read);
//   * decode word-serially: header (16 B) + [SUT 32 B] + one MDESC (32 B) per opnd bit in A, B, C, D, O, R, I order;
//   * predicate ALWAYS / POS0 / NOT_POS0 / LAST_ITER (innermost loop); CTL.LOOP param[15:0] count, [16] level
//     (0 -> L, 1 -> L1), two levels nested in either order, bodies REPLAYED from the ring (a body must fit: the record
//     ending past RW - 2 words of the outermost body start faults); CTL.FENCE = every unit drained AND every posted
//     HBM write visible (wr_quiet); CTL.END = token U32(VM[A_eff]) after END's wait mask, range-checked against 2^18 and
//     cp_vocab;
//   * effective base = base + L*lstride + L1*l1stride + X*dyn_mul (strides signed 32 b; one radix-16 iterative
//     multiplier, early exit), X = DYN[dyn_sel] or U32(VM[I_eff + L]) for an INDEXED descriptor; n = n | DYN[n_sel]
//     (1..62) | U32(VM[I_eff + I.stride + L]) (63, N_FROM_VM).  Everything that needs no VM read is computed BEFORE
//     the wait; the I-table reads come AFTER the record's wait mask is met (the IDX.TOPK writer is ordered by a wait
//     bit, section 3.3), through one VM read port;
//   * DYN 0 ZERO 1 POS 2 POS1 3 TOKEN 4 L 5 RANK 6 SLOT 7 POS_SLOT 8 L1 15 POS_SLOT1; 16..40 the DS full-shape
//     selectors (tools/hdc_isa_v41.FULL_DYN_KEYS order, tools/v41_fullshape_isa.full_dyn) at the slot's position;
//   * dispatch: unit valid/ready, payload {header, SUT, 7 EFFECTIVE MDESCs (base = effective base, n = effective n
//     low 20 b)} + full-width sidebands: 7 x 21-bit effective n, POS1, POS_SLOT1, L, L1;
//   * completion status: 0 OK, 1 unit fault, 3 bad command or range (absent unit: SIMT / 12..15, op outside the unit's
//     list, CTL.TOKX/AMAX/ACCEPT, reserved DYN 9..14 / 41..63, indexed or N_FROM_VM without a proper I, I-table read
//     outside VM, HBM base outside 2^40 / VM base outside 2^18, n from VM >= 2^21, bad LOOP nesting / count 0, ENDLOOP
//     without LOOP, body over the ring, END without a VM A, END token >= 2^18 or >= cp_vocab); a doorbell with
//     token >= cp_vocab or pos >= cp_ctx_max completes at once with status 3.
// Reset = DS (cp_vocab / cp_ctx_max come from the config path's active registers).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_seq #(
    parameter integer RW   = 512,        // ring words (16 B); a power of two
    parameter integer NOS  = 8,          // fetch sectors outstanding
    parameter integer USE_MACRO = 0,     // 1: the ring is one ot_sram_1r1w_256x256_m2_r2c2 (RW must be 512)
    parameter integer DS_TPL = 2,        // DS full-shape DYN: log2 TP (4)
    parameter integer DS_WIN = 128,      //   window
    parameter integer DS_SCAN = 16384,   //   scan cap
    parameter integer DS_TOPK = 512,     //   top-k
    parameter integer DS_HDL = 9         //   log2 head dim (512)
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [159:0]  md_d,           // {image_pages, image_base, entry_draft, entry_verify, entry_ar} (cfg master)
    input  wire [17:0]   cfg_vocab,
    input  wire [20:0]   cfg_ctx_max,
    input  wire [7:0]    rank,
    input  wire          hold,           // config commit / settle: doorbells refused
    output wire          busy,           // a job runs or a unit has work outstanding (config E_BUSY)
    // doorbell {token 18, pos 20, job 32, gen 4, entry 2, ncol 4}
    input  wire          db_v,
    output wire          db_rdy,
    input  wire [17:0]   db_token,
    input  wire [19:0]   db_pos,
    input  wire [31:0]   db_job,
    input  wire [3:0]    db_gen,
    input  wire [1:0]    db_entry,
    input  wire [3:0]    db_ncol,       // verify columns: bounds the TOKX count k
    // record fetch: 32 B sectors, in-order responses
    output wire          f_req_v,
    input  wire          f_req_rdy,
    output wire [39:0]   f_req_addr,
    input  wire          f_rsp_v,
    input  wire [255:0]  f_rsp_data,
    // VM read port (I tables, the END token): one outstanding, in order
    output reg           vr_v,
    input  wire          vr_rdy,
    output reg  [17:0]   vr_addr,
    input  wire          vr_rsp_v,
    input  wire [31:0]   vr_rsp_data,
    // unit dispatch (index = HGI unit code; CTL = 0 is internal)
    output wire [15:0]   u_v,
    input  wire [15:0]   u_rdy,
    output reg  [127:0]  d_hdr,
    output reg  [255:0]  d_sut,
    output reg  [1791:0] d_desc,         // {I, R, O, D, C, B, A} effective
    output reg  [146:0]  d_n,            // 7 x 21-bit effective n, A in bits 20:0
    output reg  [20:0]   d_pos1,
    output reg  [20:0]   d_pslot1,
    output reg  [15:0]   d_L,
    output reg  [15:0]   d_L1,
    input  wire [15:0]   u_done,         // retire pulses (one per dispatched record)
    input  wire [15:0]   u_fault,
    input  wire          wr_quiet,       // every posted HBM write is visible
    // completion {token, pos, job, gen, status, cycles}
    output wire          cpl_v,
    input  wire          cpl_rdy,
    output reg  [17:0]   cpl_token,
    output reg  [19:0]   cpl_pos,
    output reg  [31:0]   cpl_job,
    output reg  [3:0]    cpl_gen,
    output reg  [3:0]    cpl_status,
    output reg  [31:0]   cpl_cycles,
    // CTL.TOKX (Q-MTP-1, hbm-forks 2026-10-09): the committed tokens of the step, up to 16, carried on the completion
    output wire          cpl_tokx       // 1: this completion beat is a CTL.TOKX committed token (status 0), END follows
);
    // ---- registered boundary (submit rule X4): every data / status input lands in a pin flop (config words are
    // quasi-static, retire / fault pulses and VM read data one cycle later: the drain mask only waits longer)
    reg [159:0] md_d_r; reg [17:0] cfg_vocab_r; reg [20:0] cfg_ctx_max_r; reg [7:0] rank_r; reg hold_r;
    reg vr_rsp_v_r; reg [31:0] vr_rsp_data_r; reg [15:0] u_done_r, u_fault_r; reg wr_quiet_r; reg f_rsp_v_r; reg [255:0] f_rsp_data_r;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin hold_r <= 1'b1; vr_rsp_v_r <= 1'b0; u_done_r <= 16'd0; u_fault_r <= 16'd0; wr_quiet_r <= 1'b0; f_rsp_v_r <= 1'b0; end
        else begin hold_r <= hold; vr_rsp_v_r <= vr_rsp_v; u_done_r <= u_done; u_fault_r <= u_fault; wr_quiet_r <= wr_quiet; f_rsp_v_r <= f_rsp_v; end
    always @(posedge clk) begin
        md_d_r <= md_d; cfg_vocab_r <= cfg_vocab; cfg_ctx_max_r <= cfg_ctx_max; rank_r <= rank; vr_rsp_data_r <= vr_rsp_data; f_rsp_data_r <= f_rsp_data;
    end
    localparam integer RB = $clog2(RW);
    localparam integer RS = RW / 2;                       // sectors
    localparam integer SB = RB - 1;
    // ------------------------------------------------------------------ field positions (spec.json, v1.0)
    localparam integer H_UNIT = 124, H_OP = 118, H_WAIT = 102, H_PRED = 100, H_OPND = 93, H_TMPL = 92, H_SLOT = 89,
                       H_PARAM = 64;
    localparam integer M_SPACE = 0, M_IBC = 5, M_IDX = 6, M_BASE = 8, M_N = 48, M_M = 68, M_STRIDE = 88,
                       M_LSTR = 136, M_DSEL = 168, M_DMUL = 174, M_NSEL = 201, M_L1STR = 207;
    // ------------------------------------------------------------------ states
    localparam [4:0] S_IDLE = 5'd0, S_DEC = 5'd1, S_H1 = 5'd2, S_H2 = 5'd3, S_RDW = 5'd4, S_ADDR = 5'd5,
                     S_WAIT = 5'd6, S_IDX = 5'd7, S_DISP = 5'd8, S_DRAIN = 5'd9, S_ENDRD = 5'd10, S_CPL = 5'd11, S_DB = 5'd12, S_ADV = 5'd13, S_TOKX = 5'd14, S_TKB = 5'd15;
    reg [4:0]  st;
    reg [17:0] token; reg [19:0] pos; reg [1:0] db_entry_q; reg [20:0] pos1_q;
    // ------------------------------------------------------------------ ring + fetch (word pointers, RB+1 bits)
    reg [RB:0]  wp, rp, frp;             // write (sector aligned), record, free (outermost loop body start or rp)
    reg [39:0]  faddr;
    reg [4:0]   inflight, drop;
    reg         fetching;
    wire [RB:0] frp_al = {frp[RB:1], 1'b0};
    wire [RB+1:0] used = {1'b0, wp - frp_al} + {inflight, 1'b0};
    reg         wv;                      // a sector has landed since the doorbell (before it, rp may lead wp by 1)
    wire [RB:0] avail = wv ? wp - rp : {(RB+1){1'b0}};
    reg [RB:0]  rd_ptr;                  // the ring read address (registered); the sector lands one edge later
    reg [255:0] rd_sec; reg rd_hi;
    wire        ring_we = f_rsp_v_r && (drop == 5'd0);
    always @(posedge clk) rd_hi <= rd_ptr[0];
    generate if (USE_MACRO) begin : g_ring_m
        initial if (RW != 512) $fatal(1, "ot_hgi_seq: USE_MACRO needs RW 512");
        wire [255:0] q;
        ot_sram_1r1w_256x256_m2_r2c2 u_ring (.clk(clk), .r_ce_in(1'b1), .r_addr_in(rd_ptr[8:1]), .rd_out(q),
            .w_ce_in(ring_we), .w_addr_in(wp[8:1]), .wd_in(f_rsp_data_r), .w_mask_in({256{1'b1}}),
            .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
        always @* rd_sec = q;
    end else begin : g_ring_r
        reg [255:0] ring [0:RS-1];
        always @(posedge clk) begin
            rd_sec <= ring[rd_ptr[RB-1:1]];
            if (ring_we) ring[wp[RB-1:1]] <= f_rsp_data_r;
        end
    end endgenerate
    wire [127:0] rd_word = rd_hi ? rd_sec[255:128] : rd_sec[127:0];
    // ------------------------------------------------------------------ the current record
    reg  [127:0] h;
    wire [3:0]  h_unit = h[H_UNIT +: 4];
    wire [5:0]  h_op   = h[H_OP +: 6];
    wire [15:0] h_wait = h[H_WAIT +: 16];
    wire [1:0]  h_pred = h[H_PRED +: 2];
    wire [6:0]  h_opnd = h[H_OPND +: 7];
    wire        h_tmpl = h[H_TMPL];
    wire [2:0]  h_slot = h[H_SLOT +: 3];
    wire [24:0] h_param = h[H_PARAM +: 25];
    wire [2:0]  npres = h_opnd[0] + h_opnd[1] + h_opnd[2] + h_opnd[3] + h_opnd[4] + h_opnd[5] + h_opnd[6];
    wire [4:0]  rlen = 5'd1 + {3'd0, h_tmpl, 1'b0} + {1'b0, npres, 1'b0};
    // ops per unit (spec.json uop.ops), units 0..10 exist on r25
    function automatic [3:0] nops(input [3:0] u);
        case (u) 4'd0: nops = 4'd8; 4'd4: nops = 4'd7; 4'd5: nops = 4'd2; 4'd6: nops = 4'd6; 4'd8: nops = 4'd4;
                 4'd9: nops = 4'd5; 4'd1, 4'd2, 4'd3, 4'd7, 4'd10: nops = 4'd1; default: nops = 4'd0; endcase
    endfunction
    // slot of the m-th present descriptor
    function automatic [2:0] mth(input [6:0] o, input [2:0] m);
        integer q; reg [2:0] c; begin mth = 3'd7; c = 0;
            for (q = 0; q < 7; q = q + 1) if (o[q]) begin if (c == m && mth == 3'd7) mth = q[2:0]; c = c + 3'd1; end
        end
    endfunction
    // ------------------------------------------------------------------ loops
    reg [1:0]  depth;
    reg        lv_lvl [0:1]; reg [15:0] lv_cnt [0:1]; reg [RB:0] lv_body [0:1];
    reg [15:0] Lc, L1c;
    wire       in_lvl = (depth == 2'd2) ? lv_lvl[1] : lv_lvl[0];
    wire [15:0] in_cnt = (depth == 2'd2) ? lv_cnt[1] : lv_cnt[0];
    wire [15:0] in_ctr = in_lvl ? L1c : Lc;
    wire       last_iter_c = (depth != 2'd0) && (in_ctr + 16'd1 == in_cnt);
    // registered (route TT -403: Lc -> last / more -> the header evaluation -> u_v): the loop counters change only at
    // LOOP / ENDLOOP, at least 3 edges before the next header is evaluated (S_DEC, S_H1, S_H2)
    reg        last_iter;
    always @(posedge clk) last_iter <= last_iter_c;
    reg  pred_ok;
    always @* case (h_pred) 2'd0: pred_ok = 1'b1; 2'd1: pred_ok = (pos == 0); 2'd2: pred_ok = (pos != 0);
                            default: pred_ok = last_iter; endcase
    // ------------------------------------------------------------------ outstanding per unit
    reg [7:0] outst [0:15];
    reg [15:0] busy_u;
    integer u;
    always @* for (u = 0; u < 16; u = u + 1) busy_u[u] = (outst[u] != 8'd0);
    function automatic waitok(input [15:0] w, input [15:0] b);
`ifdef OT_HGI_SEQ_MUT_WAIT
        waitok = 1'b1;                                     // NEGATIVE CONTROL: the drain mask ignored
`else
        waitok = ((w & 16'hFFFE) & b) == 16'd0;
`endif
    endfunction
    reg busy_q;
    always @(posedge clk or negedge rst_n) if (!rst_n) busy_q <= 1'b0; else busy_q <= (st != S_IDLE) || (busy_u != 16'd0);
    assign busy = busy_q;          // registered output (config E_BUSY: one cycle late is harmless)
    // ------------------------------------------------------------------ DYN
    // DS full-shape selectors: a free-running 4-stage registered bank from (pos, the record's slot, rank) -- the
    // values are valid 4 cycles after the header lands (dv_cnt); the address unit waits for it (timing: the
    // combinational form was the -701 ps limiter, header slot -> 21-bit adds / mins / rank x sc1 -> multiplier)
    function automatic [20:0] mn(input [20:0] a, input [20:0] b); mn = (a < b) ? a : b; endfunction
    function automatic [20:0] cdv(input [20:0] a, input integer sh);       // ceil(a / 2^sh)
        cdv = (a + ((21'd1 << sh) - 21'd1)) >> sh;
    endfunction
    reg [20:0] ps, p1, q_p1, q_n2, q_ns1, q_ns2, q_win, q_sc1, q_sc2, q_scr, q_ps;
    reg [28:0] q_rsc;
    reg [20:0] q_sc1b, q_psb;
    reg [31:0] dsq [16:40];
    reg [2:0]  dv_cnt;
    wire       dv_ok = (dv_cnt == 3'd4);
    always @(posedge clk) begin
        ps <= {1'b0, pos} + {18'd0, h_slot};                                   // stage 1
        p1 <= {1'b0, pos} + {18'd0, h_slot} + 21'd1;
        q_ps <= ps; q_p1 <= p1; q_n2 <= {1'b0, p1[20:1]};                       // stage 2
        q_ns1 <= mn(p1, DS_TOPK); q_ns2 <= mn({1'b0, p1[20:1]}, DS_TOPK); q_win <= mn(p1, DS_WIN);
        q_sc1 <= cdv(p1, DS_TPL); q_sc2 <= cdv({1'b0, p1[20:1]}, DS_TPL); q_scr <= cdv(mn(p1, DS_SCAN), DS_TPL);
        q_rsc <= {21'd0, rank_r} * {8'd0, cdv(p1, DS_TPL)};                    // stage 2 (rank x sc1)
        q_sc1b <= q_sc1; q_psb <= q_ps;
        dsq[16] <= q_win;            dsq[17] <= q_p1;             dsq[18] <= q_n2;             dsq[19] <= q_ns1;  // stage 3
        dsq[20] <= q_ns2;            dsq[21] <= q_win;            dsq[22] <= q_win + q_ns1;    dsq[23] <= q_win + q_ns2;
        dsq[24] <= q_sc1;            dsq[25] <= q_sc2;            dsq[26] <= q_scr;            dsq[27] <= mn(q_sc1, DS_TOPK);
        dsq[28] <= mn(q_sc2, DS_TOPK); dsq[29] <= mn(q_scr, DS_TOPK);
        dsq[30] <= cdv(q_sc1, 4);    dsq[31] <= cdv(q_sc1, 3);    dsq[32] <= cdv(q_sc2, 4);    dsq[33] <= cdv(q_scr, 4);
        dsq[34] <= cdv(q_win, 5);    dsq[35] <= cdv(q_win + q_ns1, 5); dsq[36] <= cdv(q_win + q_ns2, 5);
        dsq[37] <= q_win - 21'd1;    dsq[38] <= {11'd0, q_win} << DS_HDL; dsq[39] <= {11'd0, q_win - 21'd1} << DS_HDL;
        dsq[40] <= (({8'd0, q_psb} >= q_rsc) && ({8'd0, q_psb} < q_rsc + {8'd0, q_sc1b})) ?              // stage 3
                   {3'd0, ({8'd0, q_psb} - q_rsc) >> 3} : {11'd0, cdv(q_sc1b, 3)};
    end
    function automatic [31:0] dsv(input [5:0] c);
        dsv = (c >= 6'd16 && c <= 6'd40) ? dsq[c] : 32'd0;
    endfunction
    function automatic dyn_rsv(input [5:0] c);           // codes with no value on r25
        dyn_rsv = (c >= 6'd9 && c <= 6'd14) || (c >= 6'd41);
    endfunction
    function automatic [31:0] dynv(input [5:0] c);
        case (c)
            6'd0: dynv = 32'd0;
            6'd1: dynv = {12'd0, pos};
            6'd2: dynv = {11'd0, pos1_q};       // registered pos + 1 (drive-0849: pos -> d_n path)
            6'd3: dynv = {14'd0, token};
            6'd4: dynv = {16'd0, Lc};
            6'd5: dynv = {24'd0, rank_r};
            6'd6: dynv = {29'd0, h_slot};
            6'd7: dynv = {11'd0, ps};          // valid with dv_ok (registered)
            6'd8: dynv = {16'd0, L1c};
            6'd15: dynv = {11'd0, p1};
            default: dynv = dsv(c);
        endcase
    endfunction
    // ------------------------------------------------------------------ descriptors and the address unit
    reg [255:0] dr [0:6];                // raw descriptors as fetched
    reg [63:0]  pacc [0:6];              // base + L*lstride + L1*l1stride (+ DYN term) before the VM-read terms
    reg [20:0]  pn [0:6];
    reg [6:0]   pend_x, pend_n;          // indexed X / N_FROM_VM read still owed (after the wait)
    reg [4:0]   wk;                      // word index being read (0 = evaluate the header)
    reg [2:0]   aj;                      // descriptor in the address pass (6 = I first, then 0..5)
    reg [2:0]   as;                      // address sub-state
    reg [63:0]  acc, mcand, m3;
    reg         m3v;
    reg [31:0]  mplier;
    reg [5:0]   ash;
    reg [39:0]  ieff;
    reg         have_i, is_end, is_tokx;
    reg [4:0]   tk_i, tk_n; reg [17:0] tk_base; reg tk_k; reg [3:0] ncol; reg [19:0] tk_pos;
    localparam [2:0] A_LOAD = 3'd0, A_ML = 3'd1, A_ML1 = 3'd2, A_MD = 3'd3, A_FIN = 3'd4, A_NEXT = 3'd5;
    wire [255:0] dc = dr[aj];
    wire        dc_idx = dc[M_IDX];
    wire [5:0]  dc_dsel = dc[M_DSEL +: 6];
    wire [5:0]  dc_nsel = dc[M_NSEL +: 6];
    wire [1:0]  dc_sp = dc[M_SPACE +: 2];
    wire [31:0] dyn_d = dynv(dc_dsel), dyn_n = dynv(dc_nsel);
    wire [20:0] n_eff = (dc_nsel == 6'd0) ? {1'b0, dc[M_N +: 20]} : dyn_n[20:0];
    function automatic [63:0] sx32(input [31:0] v); sx32 = {{32{v[31]}}, v}; endfunction
    // range check of an effective base by space (HBM 2^40 bytes, VM 2^18 words; STREAM / NONE unchecked)
    function automatic base_bad(input [1:0] sp, input [63:0] a);
        base_bad = (sp == 2'd0) ? (a[63:40] != 24'd0) : (sp == 2'd1) ? (a[63:18] != 46'd0) : 1'b0;
    endfunction
    function automatic [255:0] eff_desc(input [255:0] raw, input [63:0] a, input [20:0] n);
        eff_desc = raw;
        eff_desc[M_BASE +: 40] = a[39:0];
        eff_desc[M_N +: 20] = n[19:0];
    endfunction
    // ------------------------------------------------------------------ main FSM
    integer k;
    wire [15:0] u_acc = u_v & u_rdy;
    assign db_rdy = (st == S_IDLE) && !hold_r;
    // completion outputs leave flops (route: st -> cpl_tokx decode, fanout 20, -88 ps); valid rises one edge after the
    // state is entered and drops on the handshake edge, so back-to-back TOKX beats are separated by one bubble
    reg cpl_v_q, cpl_tokx_q;
    wire cpl_hs = cpl_v_q & cpl_rdy;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin cpl_v_q <= 1'b0; cpl_tokx_q <= 1'b0; end
        else begin
            cpl_v_q <= ((st == S_CPL) || (st == S_TKB)) && !cpl_hs;
            cpl_tokx_q <= (st == S_TKB) && !cpl_hs;
        end
    assign cpl_v = cpl_v_q;
    assign cpl_tokx = cpl_tokx_q;
    // dispatch acceptance registered (route TT -441: u_rdy -> |u_acc -> state / u_v): a valid bit clears on its own
    // ready (one gate), the FSM leaves S_DISP on the registered accept (+1 cycle a dispatch)
    reg acc_q;
    always @(posedge clk or negedge rst_n) if (!rst_n) acc_q <= 1'b0; else acc_q <= |u_acc;
    // the FSM's dispatch register u_vr is set / cleared from flops only; u_tk marks a valid already taken (u_rdy enters
    // one OR gate), so u_v = u_vr & ~u_tk drops on the accepting edge
    // (u_vr is cleared when the FSM leaves S_DISP, so u_tk is clear again before the next dispatch sets u_vr)
    reg [15:0] u_vr, u_tk;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) u_tk <= 16'd0;
        else u_tk <= (u_vr == 16'd0) ? 16'd0 : (u_tk | (u_v & u_rdy));
    assign u_v = u_vr & ~u_tk;
    wire [39:0] entry_off = {4'd0, (db_entry_q == 2'd0) ? md_d_r[31:0] : (db_entry_q == 2'd1) ? md_d_r[63:32] : md_d_r[95:64], 4'd0};
    wire [39:0] img = {md_d_r[123:96], 12'd0} + entry_off;          // image_base pages (word 60)
    wire [4:0] infl_p1 = inflight + 5'd1, infl_m1 = inflight - 5'd1;   // from flops: the ready only selects
    // fetch requests leave through a 2-entry FIFO (registered boundary: f_req_rdy only pops it); inflight counts
    // requests PUSHED and not yet answered (every pushed request is sent and answered; a new doorbell drops them)
    reg [39:0] rqf [0:1]; reg rqh; reg [1:0] rqn;
    assign f_req_v = (rqn != 2'd0);
    assign f_req_addr = rqf[rqh];
    wire       rq_push = fetching && (rqn != 2'd2) && (inflight < NOS) && (used + 2 <= RW);
    wire       rq_pop = f_req_v && f_req_rdy;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rqh <= 1'b0; rqn <= 2'd0; end
        else begin
            if (rq_push) rqf[rqh ^ (rqn != 2'd0)] <= faddr;
            if (rq_pop) rqh <= ~rqh;
            rqn <= rqn + (rq_push ? 2'd1 : 2'd0) - (rq_pop ? 2'd1 : 2'd0);
        end
    wire [4:0] fl_after = (rq_push && !f_rsp_v_r) ? infl_p1 : (!rq_push && f_rsp_v_r) ? infl_m1 : inflight;
    wire       is_ctl = (h_unit == 4'd0);
    wire [RB+1:0] rec_end = {1'b0, rp - frp} + {{(RB-3){1'b0}}, rlen};
    wire [1:0] top = depth - 2'd1;
    wire       top_lvl = lv_lvl[top[0]];
    wire [15:0] top_ctr = top_lvl ? L1c : Lc;
`ifdef OT_HGI_SEQ_MUT_LOOP
    wire more_c = top_ctr + 16'd2 < lv_cnt[top[0]];       // NEGATIVE CONTROL: one iteration short
`else
    wire more_c = top_ctr + 16'd1 < lv_cnt[top[0]];
`endif
    reg more;
    always @(posedge clk) more <= more_c;                 // registered (see last_iter)
    // first present descriptor of 0..5 above j (7 = none)
    function automatic [2:0] nxt(input [6:0] o, input [3:0] j);
        integer q; begin nxt = 3'd7; for (q = 5; q >= 0; q = q - 1) if (o[q] && q > j) nxt = q[2:0]; end
    endfunction
    function automatic [2:0] nxtp(input [6:0] p, input [3:0] j);
        integer q; begin nxtp = 3'd7; for (q = 5; q >= 0; q = q - 1) if (p[q] && q > j) nxtp = q[2:0]; end
    endfunction
    reg [1:0] rpipe_v; reg [4:0] rpipe_k0, rpipe_k1;
    reg [2:0] ix;
    reg [31:0] xval;
    wire [4:0]  wk_m  = rpipe_k1 - 5'd1 - {3'd0, h_tmpl, 1'b0};
    wire [2:0]  wk_sl = mth(h_opnd, wk_m[3:1]);
    wire [63:0] iaddr_x = {24'd0, ieff} + {48'd0,
`ifdef OT_HGI_SEQ_MUT_IDXL
        16'd0                                               // NEGATIVE CONTROL: the indexed read ignores L
`else
        Lc
`endif
        };
    wire [63:0] iaddr_n = {24'd0, ieff} + sx32(dr[6][M_STRIDE +: 32]) + {48'd0, Lc};
    // one radix-16 step of the address unit; returns 1 when the multiplier is exhausted
    // radix-4 multiply step: acc += {0, m, 2m, 3m}[digit]; m and 3m shift left by 2 (3m registered one cycle after a
    // new multiplicand: m3v).  One 64-bit add a cycle (the radix-16 form's 64 x 4 product + variable shift was a
    // setup limiter)
    wire        mdone = (mplier == 32'd0);
    wire [63:0] mpick = (mplier[1:0] == 2'd1) ? mcand : (mplier[1:0] == 2'd2) ? {mcand[62:0], 1'b0} :
                        (mplier[1:0] == 2'd3) ? m3 : 64'd0;
    wire [63:0] mstep = acc + mpick;
    function automatic [2:0] first0(input [6:0] o); first0 = o[0] ? 3'd0 : nxt(o, 4'd0); endfunction
    task advance(input [RB:0] n);
        begin rp <= rp + n; if (depth == 2'd0) frp <= rp + n; end
    endtask
    task fault3;
        begin st <= S_CPL; cpl_status <= 4'd3; cpl_token <= 18'd0; fetching <= 1'b0; u_vr <= 16'd0;
              vr_v <= 1'b0; end
    endtask
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; wp <= 0; wv <= 1'b0; rp <= 0; frp <= 0; inflight <= 0; drop <= 0; fetching <= 1'b0;
            depth <= 0; Lc <= 0; L1c <= 0; u_vr <= 16'd0; vr_v <= 1'b0; rpipe_v <= 2'b00; dv_cnt <= 3'd0; m3v <= 1'b0;
            cpl_status <= 0; cpl_token <= 0; cpl_cycles <= 0; faddr <= 0; rd_ptr <= 0; wk <= 0; ix <= 0;
            for (k = 0; k < 16; k = k + 1) outst[k] <= 8'd0;
        end else begin
            for (k = 0; k < 16; k = k + 1)                     // +1 / -1 precomputed from flops: u_rdy only selects
                if (u_acc[k] && !u_done_r[k]) outst[k] <= outst[k] + 8'd1;
                else if (!u_acc[k] && u_done_r[k]) outst[k] <= outst[k] - 8'd1;
            if (st != S_IDLE && st != S_CPL) cpl_cycles <= cpl_cycles + 32'd1;
            inflight <= fl_after;
            if (dv_cnt != 3'd4) dv_cnt <= dv_cnt + 3'd1;
            // ---- fetch requests (valid held until ready)
            if (rq_push) faddr <= faddr + 40'd32;
            // ---- fetch responses -> ring (one sector a response)
            if (f_rsp_v_r) begin
                if (drop != 0) drop <= drop - 5'd1;
                else begin wp <= wp + 2'd2; wv <= 1'b1; end         // the ring write: g_ring_*
            end
            // ---- ring read pipe (address registered, sector registered: a word lands two edges after its issue)
            rpipe_v <= {rpipe_v[0], 1'b0}; rpipe_k1 <= rpipe_k0;
            if (|(u_fault_r & ~16'd1) && st != S_IDLE && st != S_CPL) begin
                st <= S_CPL; cpl_status <= 4'd1; cpl_token <= 0; u_vr <= 0; vr_v <= 1'b0; fetching <= 1'b0;
            end else case (st)
                S_IDLE: if (db_v && !hold_r) begin
                    token <= db_token; pos <= db_pos; cpl_job <= db_job; cpl_gen <= db_gen; cpl_pos <= db_pos;
                    db_entry_q <= db_entry;
                    cpl_cycles <= 0; depth <= 0; Lc <= 0; L1c <= 0; cpl_token <= 0; cpl_status <= 0; st <= S_DB;
                    ncol <= db_ncol;
                end
                S_DB: begin
                    pos1_q <= {1'b0, pos} + 21'd1;
                    if (token >= cfg_vocab_r || {1'b0, pos} >= cfg_ctx_max_r) begin
                        st <= S_CPL; cpl_status <= 4'd3;
                    end else begin
                        faddr <= {img[39:5], 5'd0}; fetching <= 1'b1;
                        wp <= 0; wv <= 1'b0; rp <= {{RB{1'b0}}, img[4]}; frp <= {{RB{1'b0}}, img[4]}; drop <= fl_after;
                        st <= S_DEC;
                    end
                end
                S_DEC: if (avail != 0) begin rd_ptr <= rp; st <= S_H1; end
                S_H1: st <= S_H2;                                      // the sector read (registered address)
                S_H2: begin h <= rd_word; st <= S_RDW; wk <= 5'd0; dv_cnt <= 3'd0;
`ifdef SEQ_DEBUG
                    $display("SEQDBG t=%0t rp=%0d wp=%0d frp=%0d hdr=%h", $time, rp, wp, frp, rd_word);
`endif
                end
                S_RDW: if (wk == 5'd0) begin                           // ---- evaluate the header
                    if (depth != 2'd0 && rec_end > RW - 2) fault3;
                    else if (avail < {{(RB-4){1'b0}}, rlen}) ;          // wait for the record's words
                    else if (h_unit >= 4'd11 || h_op >= {2'd0, nops(h_unit)} ||
                             (h_unit == 4'd9 && (h_op == 6'd1 || h_op == 6'd3))) fault3;   // IDX ops 1 / 3 reserved (HGI-1 6.7)
                    else if (!pred_ok) begin advance(rlen); st <= S_DEC; end
                    else if (is_ctl && h_op != 6'd3 && h_op != 6'd5) begin
                        case (h_op)
                            6'd0: begin advance(rlen); st <= S_DEC; end                       // NOP
                            6'd1: if (h_param[15:0] == 16'd0 || depth == 2'd2 ||
                                      (depth == 2'd1 && lv_lvl[0] == h_param[16])) fault3;   // LOOP
                                  else begin
                                      lv_lvl[depth[0]] <= h_param[16]; lv_cnt[depth[0]] <= h_param[15:0];
                                      lv_body[depth[0]] <= rp + rlen;
                                      if (h_param[16]) L1c <= 16'd0; else Lc <= 16'd0;
                                      depth <= depth + 2'd1; rp <= rp + rlen;
                                      if (depth == 2'd0) frp <= rp + rlen;
                                      st <= S_DEC;
                                  end
                            6'd2: if (depth == 2'd0) fault3;                                  // ENDLOOP
                                  else if (more) begin
                                      if (top_lvl) L1c <= L1c + 16'd1; else Lc <= Lc + 16'd1;
                                      rp <= lv_body[top[0]]; st <= S_DEC;
                                  end else begin
                                      if (top_lvl) L1c <= 16'd0; else Lc <= 16'd0;
                                      depth <= depth - 2'd1; rp <= rp + rlen;
                                      if (depth == 2'd1) frp <= rp + rlen;
                                      st <= S_DEC;
                                  end
                            6'd4: st <= S_DRAIN;                                              // FENCE
                            default: fault3;                                                  // AMAX ACCEPT (reserved)
                        endcase
                    end else if (is_ctl && !h_opnd[0]) fault3;                               // END / TOKX need A
                    else begin
                        is_end <= is_ctl && h_op == 6'd3; is_tokx <= is_ctl && h_op == 6'd5;
                        d_sut <= 256'd0;
                        for (k = 0; k < 7; k = k + 1) dr[k] <= 256'd0;
                        d_desc <= 1792'd0; d_n <= 147'd0; pend_x <= 7'd0; pend_n <= 7'd0; have_i <= h_opnd[6];
                        wk <= 5'd1;
                    end
                end else begin                                         // ---- read words 1 .. rlen-1
                    if (wk < rlen) begin rd_ptr <= rp + wk; rpipe_v[0] <= 1'b1; rpipe_k0 <= wk; wk <= wk + 5'd1; end
                    if (rpipe_v[1]) begin
`ifdef SEQ_DEBUG
                        $display("SEQDBG word k=%0d m=%0d sl=%0d w=%h rd_ptr=%0d", rpipe_k1, wk_m, wk_sl, rd_word, rd_ptr);
`endif
                        if (h_tmpl && rpipe_k1 <= 5'd2) d_sut[(rpipe_k1 - 5'd1) * 128 +: 128] <= rd_word;
                        else dr[wk_sl][wk_m[0] * 128 +: 128] <= rd_word;
                    end
                    if (wk == rlen && rpipe_v == 2'b00) begin
                        aj <= h_opnd[6] ? 3'd6 : first0(h_opnd); as <= A_LOAD; st <= S_ADDR;
                    end
                end
                S_ADDR: if (aj == 3'd7) st <= S_WAIT;
                    else case (as)
                    A_LOAD: if (dv_ok) begin
                        m3v <= 1'b0;
                        if ((aj == 3'd6 && (dc_idx || dc_nsel == 6'd63 || dc_sp != 2'd1)) ||
                            (aj != 3'd6 && (dc_idx || dc_nsel == 6'd63) && !have_i) ||
                            (!dc_idx && dyn_rsv(dc_dsel)) ||
                            (dc_nsel != 6'd0 && dc_nsel != 6'd63 && dyn_rsv(dc_nsel)) ||
                            ((is_end || is_tokx) && aj == 3'd0 && dc_sp != 2'd1)) fault3;
                        else begin
                            acc <= {24'd0, dc[M_BASE +: 40]}; mcand <= sx32(dc[M_LSTR +: 32]); mplier <= {16'd0, Lc};
                            ash <= 6'd0; as <= A_ML;
                        end
                    end
                    A_ML, A_ML1, A_MD: if (!mdone && !m3v) begin
                            m3 <= mcand + {mcand[62:0], 1'b0}; m3v <= 1'b1;
                        end else if (!mdone) begin
                            acc <= mstep; mplier <= mplier >> 2; mcand <= mcand << 2; m3 <= m3 << 2;
                        end else begin
                            m3v <= 1'b0;
                            ash <= 6'd0;
                            if (as == A_ML) begin mcand <= sx32(dc[M_L1STR +: 32]); mplier <= {16'd0, L1c}; as <= A_ML1; end
                            else if (as == A_ML1 && !dc_idx) begin
                                mcand <= {37'd0, dc[M_DMUL +: 27]}; mplier <= dyn_d; as <= A_MD;
                            end else as <= A_FIN;
                        end
                    A_FIN: begin
                        pn[aj] <= n_eff;
                        if (aj == 3'd6) begin
                            if (base_bad(2'd1, acc)) fault3;
                            else begin
                                ieff <= acc[39:0];
                                d_desc[6*256 +: 256] <= eff_desc(dc, acc, n_eff);
                                d_n[6*21 +: 21] <= n_eff;
                                aj <= first0(h_opnd); as <= A_LOAD;
                            end
                        end else begin
                            if (dc_idx || dc_nsel == 6'd63) begin
                                pacc[aj] <= acc; pend_x[aj] <= dc_idx; pend_n[aj] <= (dc_nsel == 6'd63);
                                aj <= nxt(h_opnd, {1'b0, aj}); as <= A_LOAD;
                            end else if (base_bad(dc_sp, acc)) fault3;
                            else begin
                                d_desc[aj*256 +: 256] <= eff_desc(dc, acc, n_eff);
                                d_n[aj*21 +: 21] <= n_eff;
                                aj <= nxt(h_opnd, {1'b0, aj}); as <= A_LOAD;
                            end
                        end
                    end
                    default: as <= A_LOAD;
                    endcase
                S_WAIT: if (waitok(h_wait, busy_u)) begin
                    aj <= (pend_x[0] | pend_n[0]) ? 3'd0 : nxtp(pend_x | pend_n, 4'd0); ix <= 3'd0; st <= S_IDX;
                end
                S_IDX: if (aj == 3'd7) begin
                        if (is_end) begin
                            vr_v <= 1'b1; vr_addr <= d_desc[M_BASE +: 18]; st <= S_ENDRD;
                        end else if (is_tokx) begin                 // A[0] = k, then A[1..k]: k completion beats
                            if ({3'd0, d_desc[M_BASE +: 18]} + 21'd17 > 21'h40000) fault3;
                            else begin
                                tk_base <= d_desc[M_BASE +: 18]; tk_i <= 5'd0; tk_k <= 1'b1; tk_pos <= pos;
                                vr_v <= 1'b1; vr_addr <= d_desc[M_BASE +: 18]; st <= S_TOKX;
                            end
                        end else begin
                            d_hdr <= h; d_pos1 <= pos1_q; d_pslot1 <= p1; d_L <= Lc; d_L1 <= L1c;
                            u_vr <= 16'd1 << h_unit; st <= S_DISP;
                        end
                    end else case (ix)
                    3'd0: begin                                        // the X read (indexed) or straight to n
                        acc <= pacc[aj];
                        if (pend_x[aj]) begin
                            if (iaddr_x[63:18] != 46'd0) fault3;
                            else begin vr_v <= 1'b1; vr_addr <= iaddr_x[17:0]; ix <= 3'd1; end
                        end else ix <= 3'd3;
                    end
                    3'd1: begin
                        if (vr_v && vr_rdy) vr_v <= 1'b0;
                        if (vr_rsp_v_r) begin
                            mcand <= {37'd0, dr[aj][M_DMUL +: 27]}; mplier <= vr_rsp_data_r; ash <= 6'd0; ix <= 3'd2;
                        end
                    end
                    3'd2: if (!mdone && !m3v) begin m3 <= mcand + {mcand[62:0], 1'b0}; m3v <= 1'b1; end
                          else if (!mdone) begin acc <= mstep; mplier <= mplier >> 2; mcand <= mcand << 2; m3 <= m3 << 2; end
                          else begin m3v <= 1'b0; ix <= 3'd3; end
                    3'd3: if (pend_n[aj]) begin
                            if (iaddr_n[63:18] != 46'd0) fault3;
                            else begin vr_v <= 1'b1; vr_addr <= iaddr_n[17:0]; ix <= 3'd4; end
                        end else ix <= 3'd5;
                    3'd4: begin
                        if (vr_v && vr_rdy) vr_v <= 1'b0;
                        if (vr_rsp_v_r) begin
                            if (vr_rsp_data_r[31:21] != 11'd0) fault3;
                            else begin pn[aj] <= vr_rsp_data_r[20:0]; ix <= 3'd5; end
                        end
                    end
                    default: begin                                     // finalize
                        if (base_bad(dr[aj][M_SPACE +: 2], acc)) fault3;
                        else begin
                            d_desc[aj*256 +: 256] <= eff_desc(dr[aj], acc, pn[aj]);
                            d_n[aj*21 +: 21] <= pn[aj];
                            aj <= nxtp(pend_x | pend_n, {1'b0, aj}); ix <= 3'd0;
                        end
                    end
                    endcase
                S_DISP: if (acc_q) begin st <= S_ADV; u_vr <= 16'd0; end                   // accepted (registered): the ring advances next
                S_ADV: begin advance(rlen); st <= S_DEC; end
                S_DRAIN: if ((busy_u & 16'hFFFE) == 16'd0 && wr_quiet_r) begin advance(rlen); st <= S_DEC; end
                S_ENDRD: begin
                    if (vr_v && vr_rdy) vr_v <= 1'b0;
                    if (vr_rsp_v_r) begin
                        st <= S_CPL; fetching <= 1'b0; cpl_pos <= pos;
                        cpl_token <= vr_rsp_data_r[17:0];
                        cpl_status <= (vr_rsp_data_r[31:18] != 14'd0 || vr_rsp_data_r[17:0] >= cfg_vocab_r) ? 4'd3 : 4'd0;
                    end
                end
                // CTL.TOKX (HGI-1 7.4, Q-MTP-1): A = U32 [1 + ncol], A[0] = k (1 <= k <= ncol), A[1 .. k] = the committed
                // tokens; each becomes a completion beat {token A[i], pos + i - 1, status 0} (cpl_tokx) before END
                S_TOKX: begin
                    if (vr_v && vr_rdy) vr_v <= 1'b0;
                    if (vr_rsp_v_r) begin
                        if (tk_k) begin
                            if (vr_rsp_data_r == 32'd0 || vr_rsp_data_r > {28'd0, ncol}) fault3;
                            else begin
                                tk_k <= 1'b0; tk_n <= vr_rsp_data_r[4:0]; tk_i <= 5'd1;
                                vr_v <= 1'b1; vr_addr <= tk_base + 18'd1;
                            end
                        end else if (vr_rsp_data_r[31:18] != 14'd0 || vr_rsp_data_r[17:0] >= cfg_vocab_r) fault3;
                        else begin
                            cpl_token <= vr_rsp_data_r[17:0]; cpl_pos <= tk_pos; cpl_status <= 4'd0; st <= S_TKB;
                        end
                    end
                end
                S_TKB: if (cpl_hs) begin
                    tk_pos <= tk_pos + 20'd1;
                    if (tk_i == tk_n) begin advance(rlen); st <= S_DEC; end
                    else begin
                        tk_i <= tk_i + 5'd1; vr_v <= 1'b1; st <= S_TOKX;
`ifdef OT_HGI_SEQ_MUT_TOKX
                        vr_addr <= tk_base + {13'd0, tk_i};       // NEGATIVE CONTROL: the token address does not advance
`else
                        vr_addr <= tk_base + {13'd0, tk_i} + 18'd1;
`endif
                    end
                end
                S_CPL: if (cpl_hs) st <= S_IDLE;
                default: st <= S_IDLE;
            endcase
        end
    end
endmodule
`default_nettype wire
