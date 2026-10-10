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
    parameter integer NOS  = 48,         // fetch sectors outstanding (F5 2026-10-09: 48 x 2 words covers ~128 cycles of
                                         // memory latency at the program's peak record rate; the link must keep them in order)
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
    input  wire [3:0]    db_kernel,     // G23: entry 3 = KERNEL, offset = MD word 16 + db_kernel
    input  wire [11*32-1:0] md_k,       // G23: MD words 16 .. 26 (cfg master)
    // record fetch: 32 B sectors, in-order responses
    output wire          f_req_v,
    input  wire          f_req_rdy,
    output wire [39:0]   f_req_addr,
    input  wire          f_rsp_v,
    input  wire [255:0]  f_rsp_data,
    // VM read port (I tables, the END token): one outstanding, in order
    output wire          vr_v,
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
    output reg  [31:0]   cpl_cycles,    // = {cc_hi, cc_lo} (combinational copy of two flop halves)
    // CTL.TOKX (Q-MTP-1, hbm-forks 2026-10-09): the committed tokens of the step, up to 16, carried on the completion
    output wire          cpl_tokx       // 1: this completion beat is a CTL.TOKX committed token (status 0), END follows
);
    // ---- registered boundary (submit rule X4): every data / status input lands in a pin flop (config words are
    // quasi-static, retire / fault pulses and VM read data one cycle later: the drain mask only waits longer)
    reg [159:0] md_d_r; reg [11*32-1:0] md_k_r; reg [17:0] cfg_vocab_r; reg [20:0] cfg_ctx_max_r; reg [7:0] rank_r; reg hold_r;
    reg vr_rsp_v_r; reg [31:0] vr_rsp_data_r; reg [15:0] u_done_r, u_fault_r; reg wr_quiet_r; reg f_rsp_v_r; reg [255:0] f_rsp_data_r;
    // reset: asynchronous assert, synchronous release through two flops (route: rst_n recovery -89 ps, fanout ~3k);
    // every other register resets on rn
    reg [1:0] rs_q;
    always @(posedge clk or negedge rst_n) if (!rst_n) rs_q <= 2'b00; else rs_q <= {rs_q[0], 1'b1};
    wire rn = rs_q[1];
    always @(posedge clk or negedge rn)
        if (!rn) begin hold_r <= 1'b1; vr_rsp_v_r <= 1'b0; u_done_r <= 16'd0; u_fault_r <= 16'd0; wr_quiet_r <= 1'b0; f_rsp_v_r <= 1'b0; end
        else begin hold_r <= hold; vr_rsp_v_r <= vr_rsp_v; u_done_r <= u_done; u_fault_r <= u_fault; wr_quiet_r <= wr_quiet; f_rsp_v_r <= f_rsp_v; end
    always @(posedge clk) begin
        md_d_r <= md_d; md_k_r <= md_k; cfg_vocab_r <= cfg_vocab; cfg_ctx_max_r <= cfg_ctx_max; rank_r <= rank; vr_rsp_data_r <= vr_rsp_data; f_rsp_data_r <= f_rsp_data;
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
                     S_WAIT = 5'd6, S_IDX = 5'd7, S_DISP = 5'd8, S_DRAIN = 5'd9, S_ENDRD = 5'd10, S_CPL = 5'd11, S_DB = 5'd12, S_ADV = 5'd13, S_TOKX = 5'd14, S_TKB = 5'd15,
                     S_HQ = 5'd16, S_DB2 = 5'd17, S_DB3 = 5'd18;     // header pre-evaluation (registered decision flags)
    reg [4:0]  st;
    reg [17:0] token; reg [19:0] pos; reg [1:0] db_entry_q; reg [20:0] pos1_q;
    // ------------------------------------------------------------------ ring + fetch (word pointers, RB+1 bits)
    reg [RB:0]  wp, rp, frp;             // write (sector aligned), record, free (outermost loop body start or rp)
    reg [39:0]  faddr, faddr_n, img_q;   // faddr_n = faddr + 32 kept registered (the push selects; no 40-bit add)
    reg [6:0]   inflight, drop;
    reg         fetching;
    wire [RB:0] frp_al = {frp[RB:1], 1'b0};
    wire [RB+1:0] used = {1'b0, wp - frp_al} + {inflight, 1'b0};
    reg         wv;                      // a sector has landed since the doorbell (before it, rp may lead wp by 1)
    wire [RB:0] avail = wv ? wp - rp : {(RB+1){1'b0}};
    // timing pass 5: S_RDW reads the words-available compare registered (wp -> avail -> header evaluation -> u_vr /
    // cpl_* was -147 ps); avail only grows while a header waits, rp last moved >= 4 edges earlier
    reg avail_ok;                        // rlen comes from h (loaded at S_H2): valid from the S_HQ edge on
    always @(posedge clk) avail_ok <= (avail >= {{(RB-4){1'b0}}, rlen});
    reg [RB:0]  rd_ptr;                  // the ring read address (registered); the sector lands one edge later
    reg [255:0] rd_sec; reg rd_hi;
    wire        ring_we = f_rsp_v_r && (drop == 7'd0);
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
    reg hq_recbad, hq_bad, hq_skip, hq_ctl, hq_noa, clr_q; reg [4:0] hq_rlen;
    reg hq_loopbad; reg [5:0] hq_op; reg [RB:0] hq_rpn; reg [2:0] hq_sl [0:6];   // timing pass 4: op class, LOOP checks, operand slot table
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
    // two registered stages (timing pass 4: depth -> select -> +1 -> compare was -97 ps in one): the loop counters change
    // only at LOOP / ENDLOOP, 4 edges before the next header's pre-evaluation reads last_iter (S_DEC, S_H1, S_H2, S_HQ)
    reg [15:0] in_ctr_q, in_cnt_q; reg in_dep_q;
    always @(posedge clk) begin in_ctr_q <= in_ctr; in_cnt_q <= in_cnt; in_dep_q <= (depth != 2'd0); end
    reg        last_iter;
    always @(posedge clk) last_iter <= in_dep_q && (in_ctr_q + 16'd1 == in_cnt_q);
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
    always @(posedge clk or negedge rn) if (!rn) busy_q <= 1'b0; else busy_q <= (st != S_IDLE) || (busy_u != 16'd0);
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
    reg [20:0] q_sc1b, q_psb;
    reg [31:0] dsq [16:40];
    reg [3:0]  dv_cnt;
    wire       dv_ok = (dv_cnt == 4'd8);
    // timing pass 5: rank x sc1 as a carry-save tree (8 partial products -> 2, no carry chain; the 8 x 21 product was
    // -91 ps), resolved in two chunks (15 / 14 b), then the slot-range test at 21 b (rank x sc1 >= 2^21 means the
    // position precedes the rank's slice)
    wire [28:0] rp0 = rank_r[0] ? {8'd0, q_sc1}       : 29'd0, rp1 = rank_r[1] ? {7'd0, q_sc1, 1'b0} : 29'd0,
                rp2 = rank_r[2] ? {6'd0, q_sc1, 2'b0} : 29'd0, rp3 = rank_r[3] ? {5'd0, q_sc1, 3'b0} : 29'd0,
                rp4 = rank_r[4] ? {4'd0, q_sc1, 4'b0} : 29'd0, rp5 = rank_r[5] ? {3'd0, q_sc1, 5'b0} : 29'd0,
                rp6 = rank_r[6] ? {2'd0, q_sc1, 6'b0} : 29'd0, rp7 = rank_r[7] ? {1'd0, q_sc1, 7'b0} : 29'd0;
    function automatic [57:0] fa3(input [28:0] a, input [28:0] b, input [28:0] c);   // {carry << 1, sum}
        fa3 = {((a & b) | (a & c) | (b & c)) << 1, a ^ b ^ c};
    endfunction
    wire [57:0] ra = fa3(rp0, rp1, rp2), rb = fa3(rp3, rp4, rp5);
    wire [57:0] rc = fa3(ra[28:0], ra[57:29], rb[28:0]), rd = fa3(rb[57:29], rp6, rp7);
    wire [57:0] re = fa3(rc[28:0], rc[57:29], rd[28:0]);
    wire [57:0] rf = fa3(re[28:0], re[57:29], rd[57:29]);
    reg [28:0] rs_s, rs_c; reg [15:0] rs_l; reg [13:0] rs_hs, rs_hc; reg [28:0] q_rsc_r;
    reg [20:0] q_psc, q_psd, q_pse, q_sc1c, q_sc1d, q_sc1e, q_sc1f, q_psf; reg [20:0] r_diff; reg r_ge;
    always @(posedge clk) begin
        ps <= {1'b0, pos} + {18'd0, h_slot};                                   // stage 1
        p1 <= {1'b0, pos} + {18'd0, h_slot} + 21'd1;
        q_ps <= ps; q_p1 <= p1; q_n2 <= {1'b0, p1[20:1]};                       // stage 2
        q_ns1 <= mn(p1, DS_TOPK); q_ns2 <= mn({1'b0, p1[20:1]}, DS_TOPK); q_win <= mn(p1, DS_WIN);
        q_sc1 <= cdv(p1, DS_TPL); q_sc2 <= cdv({1'b0, p1[20:1]}, DS_TPL); q_scr <= cdv(mn(p1, DS_SCAN), DS_TPL);
        rs_s <= rf[28:0]; rs_c <= rf[57:29];                                     // stage 3 (carry-save rank x sc1)
        q_sc1b <= q_sc1; q_psb <= q_ps;
        dsq[16] <= q_win;            dsq[17] <= q_p1;             dsq[18] <= q_n2;             dsq[19] <= q_ns1;  // stage 3
        dsq[20] <= q_ns2;            dsq[21] <= q_win;            dsq[22] <= q_win + q_ns1;    dsq[23] <= q_win + q_ns2;
        dsq[24] <= q_sc1;            dsq[25] <= q_sc2;            dsq[26] <= q_scr;            dsq[27] <= mn(q_sc1, DS_TOPK);
        dsq[28] <= mn(q_sc2, DS_TOPK); dsq[29] <= mn(q_scr, DS_TOPK);
        dsq[30] <= cdv(q_sc1, 4);    dsq[31] <= cdv(q_sc1, 3);    dsq[32] <= cdv(q_sc2, 4);    dsq[33] <= cdv(q_scr, 4);
        dsq[34] <= cdv(q_win, 5);    dsq[35] <= cdv(dsq[22], 5);  dsq[36] <= cdv(dsq[23], 5);  // stage 4 (sum registered)
        dsq[37] <= q_win - 21'd1;    dsq[38] <= {11'd0, q_win} << DS_HDL; dsq[39] <= {11'd0, q_win - 21'd1} << DS_HDL;
        rs_l <= {1'b0, rs_s[14:0]} + {1'b0, rs_c[14:0]}; rs_hs <= rs_s[28:15]; rs_hc <= rs_c[28:15];   // stage 4
        q_psc <= q_psb; q_sc1c <= q_sc1b;
        q_rsc_r <= {rs_hs + rs_hc + {13'd0, rs_l[15]}, rs_l[14:0]};                                     // stage 5
        q_psd <= q_psc; q_sc1d <= q_sc1c;
        r_ge <= (q_rsc_r[28:21] == 8'd0) && (q_psd >= q_rsc_r[20:0]); r_diff <= q_psd - q_rsc_r[20:0];   // stage 6
        q_sc1e <= q_sc1d;
        dsq[40] <= (r_ge && (r_diff < q_sc1e)) ? {11'd0, r_diff >> 3} : {11'd0, cdv(q_sc1e, 3)};      // stage 7
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
    reg [63:0]  acc, mcand, acs, acx;     // acs / acx: carry-save accumulator of the multiply steps; acc: the resolved sum
    reg         m3v;                      // (unused since timing pass 4; kept for the reset list)
    reg [31:0]  cpa_lo; reg cpa_c;
    reg [255:0] dc_q;                     // the descriptor in the address pass, registered (aj -> dr[aj] mux)
    reg [31:0]  mplier;
    reg [5:0]   ash;
    reg [39:0]  ieff;
    reg         have_i, is_end, is_tokx;
    reg [4:0]   tk_i, tk_n; reg [17:0] tk_base; reg tk_k; reg [3:0] ncol; reg [19:0] tk_pos;
    localparam [2:0] A_LOAD = 3'd0, A_ML = 3'd1, A_ML1 = 3'd2, A_MD = 3'd3, A_FIN = 3'd4, A_PRE = 3'd5, A_C1 = 3'd6,
                     A_C2 = 3'd7;
    wire [255:0] dc = dc_q;
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
    // ------------------------------------------------------------------ VM read request (timing pass 6)
    // vr_rdy -> the FSM's vr_v write chain was -182 ps at the route SDC (-44 at the routed IO reference): the FSM sets
    // vr_vr (with a vr_new pulse) and never clears it on the handshake; vr_tk marks the request taken (vr_rdy enters one
    // OR gate), vr_v = vr_vr & ~vr_tk.  A new request clears vr_tk one edge after it is issued (+1 cycle a VM read).
    assign vr_v = vr_vr & ~vr_tk;
    always @(posedge clk or negedge rn)
        if (!rn) vr_tk <= 1'b0;
        else vr_tk <= vr_new ? (vr_v & vr_rdy) : (vr_tk | (vr_v & vr_rdy));
    // ------------------------------------------------------------------ main FSM
    integer k;
    wire [15:0] u_acc = u_v & u_rdy;
    // doorbell ready leaves a flop (route: st decode -> db_rdy -64 ps); it implies st == S_IDLE (IDLE is left only on
    // the doorbell handshake) and folds hold one edge earlier than hold_r did (never later)
    reg db_rdy_q;
    always @(posedge clk or negedge rn)
        if (!rn) db_rdy_q <= 1'b0;
        else db_rdy_q <= (st == S_IDLE) && !hold_r && !hold && !(db_v && db_rdy_q) && !db_pend;
    assign db_rdy = db_rdy_q;
    // timing pass 4: the doorbell is captured at the port (db_v -> the FSM's job-start enables was -239 ps); the FSM
    // starts from the captured copy one edge later
    reg db_pend; reg [17:0] dbq_token; reg [19:0] dbq_pos; reg [31:0] dbq_job; reg [3:0] dbq_gen, dbq_ncol, dbq_kernel; reg [1:0] dbq_entry;
    always @(posedge clk or negedge rn)
        if (!rn) db_pend <= 1'b0;
        else if (db_v && db_rdy_q) db_pend <= 1'b1;
        else if (st == S_IDLE) db_pend <= 1'b0;
    // the fields follow the port while ready is high (enable = the ready flop alone; db_v -> 70 enables was -65 ps)
    always @(posedge clk) if (db_rdy_q) begin
        dbq_token <= db_token; dbq_pos <= db_pos; dbq_job <= db_job; dbq_gen <= db_gen; dbq_ncol <= db_ncol; dbq_entry <= db_entry; dbq_kernel <= db_kernel;
    end
    // completion outputs leave flops (route: st -> cpl_tokx decode, fanout 20, -88 ps); valid rises one edge after the
    // state is entered and drops on the handshake edge, so back-to-back TOKX beats are separated by one bubble
    reg cpl_v_q, cpl_tokx_q;
    wire cpl_hs = cpl_v_q & cpl_rdy;
    reg  cpl_hs_q;                       // the handshake registered once (cpl_rdy -> FSM was -163 ps); valid stays low meanwhile
    always @(posedge clk or negedge rn) if (!rn) cpl_hs_q <= 1'b0; else cpl_hs_q <= cpl_hs;
    always @(posedge clk or negedge rn)
        if (!rn) begin cpl_v_q <= 1'b0; cpl_tokx_q <= 1'b0; end
        else begin
            cpl_v_q <= ((st == S_CPL) || (st == S_TKB)) && !cpl_hs && !cpl_hs_q;
            cpl_tokx_q <= (st == S_TKB) && !cpl_hs && !cpl_hs_q;
        end
    assign cpl_v = cpl_v_q;
    assign cpl_tokx = cpl_tokx_q;
    // dispatch acceptance registered (route TT -441: u_rdy -> |u_acc -> state / u_v): a valid bit clears on its own
    // ready (one gate), the FSM leaves S_DISP on the registered accept (+1 cycle a dispatch)
    // accepts registered once (u_rdy -> outst / acc was -184 / -118 ps): outst counts them one edge later (a wait reads
    // outst >= 4 edges after an accept); S_DISP leaves on any registered accept
    reg [15:0] u_acc_q;
    always @(posedge clk or negedge rn) if (!rn) u_acc_q <= 16'd0; else u_acc_q <= u_acc;
    wire acc_q = |u_acc_q;
    reg db_bad;
    // cpl_cycles: two 16-bit halves, the high half one edge behind its carry (a 32-bit increment rippled -189 ps); the
    // completion valid rises one edge after the last count, when the high half has caught up
    reg [15:0] cc_lo, cc_hi; reg cc_c;
    always @(*) cpl_cycles = {cc_hi, cc_lo};
    // the FSM's dispatch register u_vr is set / cleared from flops only; u_tk marks a valid already taken (u_rdy enters
    // one OR gate), so u_v = u_vr & ~u_tk drops on the accepting edge
    // (u_vr is cleared when the FSM leaves S_DISP, so u_tk is clear again before the next dispatch sets u_vr)
    reg [15:0] u_vr, u_tk;
    always @(posedge clk or negedge rn)
        if (!rn) u_tk <= 16'd0;
        else u_tk <= (u_vr == 16'd0) ? 16'd0 : (u_tk | (u_v & u_rdy));
    assign u_v = u_vr & ~u_tk;
    reg [3:0] kern_q;
    wire [31:0] kern_off = (kern_q > 4'd10) ? 32'd0 : md_k_r[kern_q*32 +: 32];
    wire [39:0] entry_off = {4'd0, (db_entry_q == 2'd0) ? md_d_r[31:0] : (db_entry_q == 2'd1) ? md_d_r[63:32] :
                             (db_entry_q == 2'd2) ? md_d_r[95:64] : kern_off, 4'd0};
    wire [39:0] img_a = {md_d_r[123:96], 12'd0};                       // image_base pages (word 60)
    reg [20:0] img_l; reg [19:0] img_ha, img_hb;
    wire [6:0] infl_p1 = inflight + 7'd1, infl_m1 = inflight - 7'd1;   // from flops: the ready only selects
    // fetch requests leave through a 2-entry FIFO (registered boundary: f_req_rdy only pops it); inflight counts
    // requests PUSHED and not yet answered (every pushed request is sent and answered; a new doorbell drops them)
    reg [39:0] rqf [0:1]; reg rqh; reg [1:0] rqn;
    wire [1:0] rqn_m1 = rqn - 2'd1, rqn_p1 = rqn + 2'd1;
    assign f_req_v = (rqn != 2'd0);
    assign f_req_addr = rqf[rqh];
    // timing pass 5: the ring-room compare registered (frp -> used -> push -> faddr_n was -208 ps): room_q is the room
    // after this cycle's push (used grows only by a push; a landed sector moves 2 words from inflight to wp - frp; frp
    // only moves forward), so the ring fills to the same RW - 2 words as the combinational form (the ring-overflow fault
    // threshold depends on it: a 2-word margin deadlocked the ring_overflow case instead of faulting)
    reg room_q;
    wire       rq_push = fetching && (rqn != 2'd2) && (inflight < NOS) && room_q;
    always @(posedge clk or negedge rn) if (!rn) room_q <= 1'b0; else room_q <= (used + (rq_push ? 2 : 0) + 2 <= RW);
    wire       rq_pop = f_req_v && f_req_rdy;
    always @(posedge clk or negedge rn)
        if (!rn) begin rqh <= 1'b0; rqn <= 2'd0; end
        else begin
            if (rq_push) rqf[rqh ^ (rqn != 2'd0)] <= faddr;
            if (rq_pop) rqh <= ~rqh;
            rqn <= rq_pop ? (rq_push ? rqn : rqn_m1) : (rq_push ? rqn_p1 : rqn);   // f_req_rdy only selects
        end
    wire [6:0] fl_after = (rq_push && !f_rsp_v_r) ? infl_p1 : (!rq_push && f_rsp_v_r) ? infl_m1 : inflight;
    wire       is_ctl = (h_unit == 4'd0);
    wire [RB+1:0] rec_end = {1'b0, rp - frp} + {{(RB-3){1'b0}}, rlen};
    wire [1:0] top = depth - 2'd1;
    wire       top_lvl = lv_lvl[top[0]];
    wire [15:0] top_ctr = top_lvl ? L1c : Lc;
    reg [15:0] top_ctr_q, top_cnt_q;
    always @(posedge clk) begin top_ctr_q <= top_ctr; top_cnt_q <= lv_cnt[top[0]]; end
`ifdef OT_HGI_SEQ_MUT_LOOP
    wire more_c = top_ctr_q + 16'd2 < top_cnt_q;          // NEGATIVE CONTROL: one iteration short
`else
    wire more_c = top_ctr_q + 16'd1 < top_cnt_q;
`endif
    reg more;
    always @(posedge clk) more <= more_c;                 // two registered stages (see last_iter)
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
    wire [2:0]  wk_sl = hq_sl[wk_m[3:1]];             // the slot table registered in S_HQ (was mth(h_opnd, ..))
    // timing pass 4: the indexed-read addresses and their range checks leave flops (Lc -> 64-bit adds -> fault3 ->
    // st / cpl_* / u_vr / vr_* was -351 ps): ieff, dr[6] and Lc are stable >= 3 edges before S_IDX reads them (iq_cnt)
    // stage 1: ieff + L; stage 2: its range flag, the low 32 bits + the stride; stage 3: the stride sum's flag
    // (bits 63:32 of ieff + L + sx(stride) are zero iff ieff+L[40:32] + carry == the stride's sign)
    // timing pass 5: no add wider than 17 bits a stage (a 33-bit add was -148 ps, 41-bit -144 ps):
    //   1: ieff[15:0] + L (17 b)          2: high 24 b + carry -> ieff + L (iax_q); X range flag
    //   3: low 16 b + stride low (17 b)   4: next 16 b + stride + carry   5: the N range flag (high bits vs stride sign)
    reg [16:0] ia_l, iam_l; reg [23:0] ia_h; reg [40:0] iax_q, iax_m; reg [17:0] iax_a; reg iax_bad;
    reg [16:0] in_l; reg [16:0] in_m, ian_t; reg [8:0] in_h, in_h2; reg in_sg, in_sg2; reg [15:0] in_l2; reg ian_bad; reg [17:0] ian_a;
    reg [2:0] iq_cnt;
    always @(posedge clk) begin
        ia_l <= {1'b0, ieff[15:0]} + {1'b0, Lc}; ia_h <= ieff[39:16];
`ifdef OT_HGI_SEQ_MUT_IDXL
        iam_l <= {1'b0, ieff[15:0]};                        // NEGATIVE CONTROL: the indexed read ignores L
`else
        iam_l <= {1'b0, ieff[15:0]} + {1'b0, Lc};
`endif
        iax_q <= {{1'b0, ia_h} + {24'd0, ia_l[16]}, ia_l[15:0]};
        iax_m <= {{1'b0, ia_h} + {24'd0, iam_l[16]}, iam_l[15:0]};
        iax_bad <= (iax_m[40:18] != 23'd0); iax_a <= iax_m[17:0];
        in_l <= {1'b0, iax_q[15:0]} + {1'b0, dr[6][M_STRIDE +: 16]}; in_h <= iax_q[40:32]; in_sg <= dr[6][M_STRIDE + 31];
        in_m <= {1'b0, iax_q[31:16]};                        // stage 3 copy of the next chunk
        in_l2 <= in_l[15:0]; in_h2 <= in_h; in_sg2 <= in_sg;
        ian_t <= in_m + {1'b0, dr[6][M_STRIDE + 16 +: 16]} + {16'd0, in_l[16]};
        ian_bad <= ({1'b0, in_h2} + {9'd0, ian_t[16]} != {9'd0, in_sg2}) || ({ian_t[15:0], in_l2[15:0]} >> 18 != 0);
        ian_a <= {ian_t[1:0], in_l2[15:0]};
    end
    // one radix-16 step of the address unit; returns 1 when the multiplier is exhausted
    // radix-4 multiply step: acc += {0, m, 2m, 3m}[digit]; m and 3m shift left by 2 (3m registered one cycle after a
    // new multiplicand: m3v).  One 64-bit add a cycle (the radix-16 form's 64 x 4 product + variable shift was a
    // setup limiter)
    wire        mdone = (mplier == 32'd0);
    // timing pass 4: a carry-save radix-4 step ({acs, acx} += d0 * m + d1 * 2m: two full-adder levels, no carry chain);
    // the resolved sum is two 32-bit halves (A_C1 / A_C2, ix 6 / 7) -- every 64-bit add rippled (~1 ns) on ASAP7
    wire [63:0] x1 = mplier[0] ? mcand : 64'd0, x2 = mplier[1] ? {mcand[62:0], 1'b0} : 64'd0;
    wire [63:0] s1 = acs ^ acx ^ x1;
    wire [63:0] k1 = {((acs[62:0] & acx[62:0]) | (acs[62:0] & x1[62:0]) | (acx[62:0] & x1[62:0])), 1'b0};
    wire [63:0] s2 = s1 ^ k1 ^ x2;
    wire [63:0] k2 = {((s1[62:0] & k1[62:0]) | (s1[62:0] & x2[62:0]) | (k1[62:0] & x2[62:0])), 1'b0};
    // timing pass 5: 16 bits a cycle (a 32-bit add was -82 ps)
    reg [1:0] ci;
    wire [16:0] cpa16 = {1'b0, acs[ci*16 +: 16]} + {1'b0, acx[ci*16 +: 16]} + {16'd0, cpa_c};
    // the effective-base range flags registered (acc -> base_bad -> the d_desc write enable was -75 ps)
    reg bad_q, bad_vm_q;
    always @(posedge clk) begin bad_q <= base_bad(dc_q[M_SPACE +: 2], acc); bad_vm_q <= base_bad(2'd1, acc); end
    function automatic [2:0] first0(input [6:0] o); first0 = o[0] ? 3'd0 : nxt(o, 4'd0); endfunction
    task advance(input [RB:0] n);
        begin rp <= rp + n; if (depth == 2'd0) frp <= rp + n; end
    endtask
    reg vr_vr, vr_new, vr_tk;             // VM read request register / issue pulse / taken flag (see below)
    task cpa_put(input [1:0] c, input [15:0] v);
        case (c) 2'd0: acc[15:0] <= v; 2'd1: acc[31:16] <= v; 2'd2: acc[47:32] <= v; default: acc[63:48] <= v; endcase
    endtask
    task fault3;
        begin st <= S_CPL; cpl_status <= 4'd3; cpl_token <= 18'd0; fetching <= 1'b0; u_vr <= 16'd0;
              vr_vr <= 1'b0; end
    endtask
    always @(posedge clk or negedge rn) begin
        if (!rn) begin
            st <= S_IDLE; clr_q <= 1'b0; wp <= 0; wv <= 1'b0; rp <= 0; frp <= 0; inflight <= 0; drop <= 0; fetching <= 1'b0;
            depth <= 0; Lc <= 0; L1c <= 0; u_vr <= 16'd0; vr_vr <= 1'b0; vr_new <= 1'b0; rpipe_v <= 2'b00; dv_cnt <= 4'd0; m3v <= 1'b0;
            cpl_status <= 0; cpl_token <= 0; cc_lo <= 0; cc_hi <= 0; cc_c <= 0; iq_cnt <= 3'd6; faddr <= 0; faddr_n <= 40'd32; rd_ptr <= 0; wk <= 0; ix <= 0;
            for (k = 0; k < 16; k = k + 1) outst[k] <= 8'd0;
        end else begin
            for (k = 0; k < 16; k = k + 1)                     // +1 / -1 precomputed from flops: u_rdy only selects
                if (u_acc_q[k] && !u_done_r[k]) outst[k] <= outst[k] + 8'd1;
                else if (!u_acc_q[k] && u_done_r[k]) outst[k] <= outst[k] - 8'd1;
            if (st != S_IDLE && st != S_CPL) {cc_c, cc_lo} <= {1'b0, cc_lo} + 17'd1; else cc_c <= 1'b0;
            if (cc_c) cc_hi <= cc_hi + 16'd1;
            inflight <= fl_after;
            // the record's operand registers clear one edge after the header is accepted (a single-flop enable); the
            // first operand word lands two edges after its read issue (rpipe), so nothing writes them on this edge
            if (clr_q) begin
                clr_q <= 1'b0; d_sut <= 256'd0; d_desc <= 1792'd0; d_n <= 147'd0;
                for (k = 0; k < 7; k = k + 1) dr[k] <= 256'd0;
            end
            if (dv_cnt != 4'd8) dv_cnt <= dv_cnt + 4'd1;
            if (iq_cnt != 3'd6) iq_cnt <= iq_cnt + 3'd1;   // the indexed-read address pipe settles 6 edges after ieff
            // ---- fetch requests (valid held until ready)
            vr_new <= 1'b0;
            if (rq_push) begin faddr <= faddr_n; faddr_n <= faddr_n + 40'd32; end
            // ---- fetch responses -> ring (one sector a response)
            if (f_rsp_v_r) begin
                if (drop != 0) drop <= drop - 7'd1;
                else begin wp <= wp + 2'd2; wv <= 1'b1; end         // the ring write: g_ring_*
            end
            // ---- ring read pipe (address registered, sector registered: a word lands two edges after its issue)
            rpipe_v <= {rpipe_v[0], 1'b0}; rpipe_k1 <= rpipe_k0;
            if (|(u_fault_r & ~16'd1) && st != S_IDLE && st != S_CPL) begin
                st <= S_CPL; cpl_status <= 4'd1; cpl_token <= 0; u_vr <= 0; vr_vr <= 1'b0; fetching <= 1'b0;
            end else case (st)
                S_IDLE: if (db_pend) begin
                    token <= dbq_token; pos <= dbq_pos; cpl_job <= dbq_job; cpl_gen <= dbq_gen; cpl_pos <= dbq_pos;
                    db_entry_q <= dbq_entry; kern_q <= dbq_kernel;
`ifdef OT_HGI_SEQ_CC_PRESET
                    cc_lo <= 16'hFF00; cc_hi <= 16'd0; cc_c <= 1'b0;   // bench: start near the low half's wrap
`else
                    cc_lo <= 16'd0; cc_hi <= 16'd0; cc_c <= 1'b0;
`endif
                    depth <= 0; Lc <= 0; L1c <= 0; cpl_token <= 0; cpl_status <= 0; st <= S_DB;
                    ncol <= dbq_ncol;
                end
                S_DB: begin                                         // the doorbell checks registered (cfg -> ring resets)
                    pos1_q <= {1'b0, pos} + 21'd1;
                    db_bad <= (token >= cfg_vocab_r || {1'b0, pos} >= cfg_ctx_max_r) || (db_entry_q == 2'd3 && kern_off == 32'd0);   // G23: an absent kernel
                    img_l <= {1'b0, img_a[19:0]} + {1'b0, entry_off[19:0]};   // image base + entry offset, 20 b a cycle
                    img_ha <= img_a[39:20]; img_hb <= entry_off[39:20];
                    st <= S_DB2;
                end
                S_DB2: begin img_q <= {img_ha + img_hb + {19'd0, img_l[20]}, img_l[19:0]}; st <= S_DB3; end
                S_DB3: begin
                    if (db_bad) begin
                        st <= S_CPL; cpl_status <= 4'd3;
                    end else begin
                        faddr <= {img_q[39:5], 5'd0}; faddr_n <= {img_q[39:5] + 35'd1, 5'd0}; fetching <= 1'b1;
                        wp <= 0; wv <= 1'b0; rp <= {{RB{1'b0}}, img_q[4]}; frp <= {{RB{1'b0}}, img_q[4]}; drop <= fl_after;
                        st <= S_DEC;
                    end
                end
                S_DEC: if (avail != 0) begin rd_ptr <= rp; st <= S_H1; end
                S_H1: st <= S_H2;                                      // the sector read (registered address)
                S_H2: begin h <= rd_word; st <= S_HQ; wk <= 5'd0; dv_cnt <= 4'd0;
`ifdef SEQ_DEBUG
                    $display("SEQDBG t=%0t rp=%0d wp=%0d frp=%0d hdr=%h", $time, rp, wp, frp, rd_word);
`endif
                end
                // ---- header pre-evaluation: the decision flags leave flops (route TT -466: h -> header checks ->
                // the d_desc / dr / d_sut clear enables); h, rp, frp, depth, pos and the loop flags are stable here
                S_HQ: begin
                    hq_recbad <= (depth != 2'd0 && rec_end > RW - 2);
                    hq_bad <= (h_unit >= 4'd11 || h_op >= {2'd0, nops(h_unit)} ||
                               (h_unit == 4'd9 && (h_op == 6'd1 || h_op == 6'd3)));   // IDX ops 1 / 3 reserved (HGI-1 6.7)
                    hq_skip <= !pred_ok;
                    hq_ctl <= is_ctl && h_op != 6'd3 && h_op != 6'd5;
                    hq_noa <= is_ctl && !h_opnd[0];
                    hq_rlen <= rlen; hq_rpn <= rp + {{(RB-4){1'b0}}, rlen};
                    hq_op <= h_op;
                    hq_loopbad <= (h_param[15:0] == 16'd0 || depth == 2'd2 || (depth == 2'd1 && lv_lvl[0] == h_param[16]));
                    for (k = 0; k < 7; k = k + 1) hq_sl[k] <= mth(h_opnd, k[2:0]);
                    st <= S_RDW;
                end
                S_RDW: if (wk == 5'd0) begin                           // ---- evaluate the header
                    if (hq_recbad) fault3;
                    else if (!avail_ok) ;                              // wait for the record's words (registered)
                    else if (hq_bad) fault3;
                    else if (hq_skip) begin advance(hq_rlen); st <= S_DEC; end
                    else if (hq_ctl) begin
                        case (hq_op)
                            6'd0: begin advance(hq_rlen); st <= S_DEC; end                       // NOP
                            6'd1: if (hq_loopbad) fault3;                                    // LOOP
                                  else begin
                                      lv_lvl[depth[0]] <= h_param[16]; lv_cnt[depth[0]] <= h_param[15:0];
                                      lv_body[depth[0]] <= hq_rpn;
                                      if (h_param[16]) L1c <= 16'd0; else Lc <= 16'd0;
                                      depth <= depth + 2'd1; rp <= hq_rpn;
                                      if (depth == 2'd0) frp <= hq_rpn;
                                      st <= S_DEC;
                                  end
                            6'd2: if (depth == 2'd0) fault3;                                  // ENDLOOP
                                  else if (more) begin
                                      if (top_lvl) L1c <= L1c + 16'd1; else Lc <= Lc + 16'd1;
                                      rp <= lv_body[top[0]]; st <= S_DEC;
                                  end else begin
                                      if (top_lvl) L1c <= 16'd0; else Lc <= 16'd0;
                                      depth <= depth - 2'd1; rp <= hq_rpn;
                                      if (depth == 2'd1) frp <= hq_rpn;
                                      st <= S_DEC;
                                  end
                            6'd4: st <= S_DRAIN;                                              // FENCE
                            default: fault3;                                                  // AMAX ACCEPT (reserved)
                        endcase
                    end else if (hq_noa) fault3;                                             // END / TOKX need A
                    else begin
                        is_end <= is_ctl && h_op == 6'd3; is_tokx <= is_ctl && h_op == 6'd5;
                        clr_q <= 1'b1;                                 // d_sut / dr / d_desc / d_n clear next edge
                        pend_x <= 7'd0; pend_n <= 7'd0; have_i <= h_opnd[6];
                        wk <= 5'd1;
                    end
                end else begin                                         // ---- read words 1 .. rlen-1
                    if (wk < hq_rlen) begin rd_ptr <= rp + wk; rpipe_v[0] <= 1'b1; rpipe_k0 <= wk; wk <= wk + 5'd1; end
                    if (rpipe_v[1]) begin
`ifdef SEQ_DEBUG
                        $display("SEQDBG word k=%0d m=%0d sl=%0d w=%h rd_ptr=%0d", rpipe_k1, wk_m, wk_sl, rd_word, rd_ptr);
`endif
                        if (h_tmpl && rpipe_k1 <= 5'd2) d_sut[(rpipe_k1 - 5'd1) * 128 +: 128] <= rd_word;
                        else dr[wk_sl][wk_m[0] * 128 +: 128] <= rd_word;
                    end
                    if (wk == hq_rlen && rpipe_v == 2'b00) begin
                        aj <= h_opnd[6] ? 3'd6 : first0(h_opnd); as <= A_PRE; st <= S_ADDR;
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
                            acs <= {24'd0, dc[M_BASE +: 40]}; acx <= 64'd0;
                            mcand <= sx32(dc[M_LSTR +: 32]); mplier <= {16'd0, Lc};
                            ash <= 6'd0; as <= A_ML;
                        end
                    end
                    A_ML, A_ML1, A_MD: if (!mdone) begin
                            acs <= s2; acx <= k2; mplier <= mplier >> 2; mcand <= mcand << 2;
                        end else begin
                            m3v <= 1'b0;
                            ash <= 6'd0;
                            if (as == A_ML) begin mcand <= sx32(dc[M_L1STR +: 32]); mplier <= {16'd0, L1c}; as <= A_ML1; end
                            else if (as == A_ML1 && !dc_idx) begin
                                mcand <= {37'd0, dc[M_DMUL +: 27]}; mplier <= dyn_d; as <= A_MD;
                            end else begin as <= A_C1; ci <= 2'd0; cpa_c <= 1'b0; end
                        end
                    A_FIN: begin
                        pn[aj] <= n_eff;
                        if (aj == 3'd6) begin
                            if (bad_vm_q) fault3;
                            else begin
                                ieff <= acc[39:0]; iq_cnt <= 3'd0;
                                d_desc[6*256 +: 256] <= eff_desc(dc, acc, n_eff);
                                d_n[6*21 +: 21] <= n_eff;
                                aj <= first0(h_opnd); as <= A_PRE;
                            end
                        end else begin
                            if (dc_idx || dc_nsel == 6'd63) begin
                                pacc[aj] <= acc; pend_x[aj] <= dc_idx; pend_n[aj] <= (dc_nsel == 6'd63);
                                aj <= nxt(h_opnd, {1'b0, aj}); as <= A_PRE;
                            end else if (bad_q) fault3;
                            else begin
                                d_desc[aj*256 +: 256] <= eff_desc(dc, acc, n_eff);
                                d_n[aj*21 +: 21] <= n_eff;
                                aj <= nxt(h_opnd, {1'b0, aj}); as <= A_PRE;
                            end
                        end
                    end
                    A_PRE: begin dc_q <= dr[aj]; as <= A_LOAD; end    // the descriptor registered (aj -> dr mux)
                    A_C1: begin                                    // resolve {acs, acx}: 16 bits a cycle
                        cpa_c <= cpa16[16]; cpa_put(ci, cpa16[15:0]);
                        ci <= ci + 2'd1; if (ci == 2'd3) as <= A_C2;
                    end
                    A_C2: as <= A_FIN;                             // the range flags (bad_q) settle on the resolved sum
                    endcase
                S_WAIT: if (waitok(h_wait, busy_u) && iq_cnt == 3'd6) begin
                    aj <= (pend_x[0] | pend_n[0]) ? 3'd0 : nxtp(pend_x | pend_n, 4'd0); ix <= 3'd0; st <= S_IDX;
                end
                S_IDX: if (aj == 3'd7) begin
                        if (is_end) begin
                            vr_vr <= 1'b1; vr_new <= 1'b1; vr_addr <= d_desc[M_BASE +: 18]; st <= S_ENDRD;
                        end else if (is_tokx) begin                 // A[0] = k, then A[1..k]: k completion beats
                            if ({3'd0, d_desc[M_BASE +: 18]} + 21'd17 > 21'h40000) fault3;
                            else begin
                                tk_base <= d_desc[M_BASE +: 18]; tk_i <= 5'd0; tk_k <= 1'b1; tk_pos <= pos;
                                vr_vr <= 1'b1; vr_new <= 1'b1; vr_addr <= d_desc[M_BASE +: 18]; st <= S_TOKX;
                            end
                        end else begin
                            d_hdr <= h; d_pos1 <= pos1_q; d_pslot1 <= p1; d_L <= Lc; d_L1 <= L1c;
                            u_vr <= 16'd1 << h_unit; st <= S_DISP;
                        end
                    end else case (ix)
                    3'd0: begin                                        // the X read (indexed) or straight to n
                        acc <= pacc[aj]; acs <= pacc[aj]; acx <= 64'd0; dc_q <= dr[aj];
                        if (pend_x[aj]) begin
                            if (iax_bad) fault3;
                            else begin vr_vr <= 1'b1; vr_new <= 1'b1; vr_addr <= iax_a; ix <= 3'd1; end
                        end else ix <= 3'd3;
                    end
                    3'd1: begin
                        if (vr_rsp_v_r) begin
                            mcand <= {37'd0, dc_q[M_DMUL +: 27]}; mplier <= vr_rsp_data_r; ash <= 6'd0; ix <= 3'd2;
                        end
                    end
                    3'd2: if (!mdone) begin acs <= s2; acx <= k2; mplier <= mplier >> 2; mcand <= mcand << 2; end
                          else begin ix <= 3'd6; ci <= 2'd0; cpa_c <= 1'b0; end
                    3'd6: begin cpa_c <= cpa16[16]; cpa_put(ci, cpa16[15:0]); ci <= ci + 2'd1; if (ci == 2'd3) ix <= 3'd7; end
                    3'd7: ix <= 3'd3;
                    3'd3: if (pend_n[aj]) begin
                            if (ian_bad) fault3;
                            else begin vr_vr <= 1'b1; vr_new <= 1'b1; vr_addr <= ian_a; ix <= 3'd4; end
                        end else ix <= 3'd5;
                    3'd4: begin
                        if (vr_rsp_v_r) begin
                            if (vr_rsp_data_r[31:21] != 11'd0) fault3;
                            else begin pn[aj] <= vr_rsp_data_r[20:0]; ix <= 3'd5; end
                        end
                    end
                    default: begin                                     // finalize
                        if (bad_q) fault3;
                        else begin
                            d_desc[aj*256 +: 256] <= eff_desc(dc_q, acc, pn[aj]);
                            d_n[aj*21 +: 21] <= pn[aj];
                            aj <= nxtp(pend_x | pend_n, {1'b0, aj}); ix <= 3'd0;
                        end
                    end
                    endcase
                S_DISP: if (acc_q) begin st <= S_ADV; u_vr <= 16'd0; end                   // accepted (registered): the ring advances next
                S_ADV: begin advance(hq_rlen); st <= S_DEC; end
                S_DRAIN: if ((busy_u & 16'hFFFE) == 16'd0 && wr_quiet_r) begin advance(hq_rlen); st <= S_DEC; end
                S_ENDRD: begin
                    if (vr_rsp_v_r) begin
                        st <= S_CPL; fetching <= 1'b0; cpl_pos <= pos;
                        cpl_token <= vr_rsp_data_r[17:0];
                        cpl_status <= (vr_rsp_data_r[31:18] != 14'd0 || vr_rsp_data_r[17:0] >= cfg_vocab_r) ? 4'd3 : 4'd0;
                    end
                end
                // CTL.TOKX (HGI-1 7.4, Q-MTP-1): A = U32 [1 + ncol], A[0] = k (1 <= k <= ncol), A[1 .. k] = the committed
                // tokens; each becomes a completion beat {token A[i], pos + i - 1, status 0} (cpl_tokx) before END
                S_TOKX: begin
                    if (vr_rsp_v_r) begin
                        if (tk_k) begin
                            if (vr_rsp_data_r == 32'd0 || vr_rsp_data_r > {28'd0, ncol}) fault3;
                            else begin
                                tk_k <= 1'b0; tk_n <= vr_rsp_data_r[4:0]; tk_i <= 5'd1;
                                vr_vr <= 1'b1; vr_new <= 1'b1; vr_addr <= tk_base + 18'd1;
                            end
                        end else if (vr_rsp_data_r[31:18] != 14'd0 || vr_rsp_data_r[17:0] >= cfg_vocab_r) fault3;
                        else begin
                            cpl_token <= vr_rsp_data_r[17:0]; cpl_pos <= tk_pos; cpl_status <= 4'd0; st <= S_TKB;
                        end
                    end
                end
                S_TKB: if (cpl_hs_q) begin
                    tk_pos <= tk_pos + 20'd1;
                    if (tk_i == tk_n) begin advance(hq_rlen); st <= S_DEC; end
                    else begin
                        tk_i <= tk_i + 5'd1; vr_vr <= 1'b1; vr_new <= 1'b1; st <= S_TOKX;
`ifdef OT_HGI_SEQ_MUT_TOKX
                        vr_addr <= tk_base + {13'd0, tk_i};       // NEGATIVE CONTROL: the token address does not advance
`else
                        vr_addr <= tk_base + {13'd0, tk_i} + 18'd1;
`endif
                    end
                end
                S_CPL: if (cpl_hs_q) st <= S_IDLE;
                default: st <= S_IDLE;
            endcase
        end
    end
endmodule
`default_nettype wire
