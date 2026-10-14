// ot_hgi_seq_fe.sv -- FE child of the R25GQ sequencer split (el1013-hbm-seq-split, 2026-10-13).
// Holds the fetch-request state and FIFO, the ring (two macros when USE_MACRO), the sector reader, the lazy word FIFO,
// the record parser and the loop state of the flat ot_hgi_seq, plus the image-address chain (md_d / md_k are FE pins).
// Logic is MOVED from ot_hgi_seq.sv; the seam contract is ot_hgi_seq_seam.svh (rules R1-R4).  Two flat combinational
// cross-region signals are re-protocolled here:
//   q_cnt < QD (queue room)  ->  the credit counter q_cred (QD at a job start, -1 an alloc sent, +1 a returned be_qpop)
//   be_inj (AU input taken)  ->  the registered level be_inj_hold_r (BE waits SEAM_INJ_WAIT before its first injection)
`default_nettype none
module ot_hgi_seq_fe #(
    parameter integer RW   = 4096,
    parameter integer NOS  = 160,
    parameter integer USE_MACRO = 0,
    parameter integer DS_TPL = 2,
    parameter integer DS_WIN = 128,
    parameter integer DS_SCAN = 16384,
    parameter integer DS_TOPK = 512,
    parameter integer DS_HDL = 9,
    parameter integer QD = 4,
    parameter integer FD = 12,
    parameter integer IKS_I = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [159:0]  md_d,
    input  wire [11*32-1:0] md_k,
    output wire          f_req_v,
    input  wire          f_req_rdy,
    output wire [39:0]   f_req_addr,
    input  wire          f_rsp_v,
    input  wire [255:0]  f_rsp_data,
    // S5a / S5b  BE -> FE
    input  wire          be_jl_v,
    input  wire [1:0]    be_jl_entry,
    input  wire [3:0]    be_jl_kernel,
    input  wire [31:0]   be_jl_loff,
    input  wire [19:0]   be_jl_pos,
    input  wire          be_js,
    input  wire          be_stop,
    input  wire          be_qpop,
    input  wire          be_lv_v,
    input  wire [15:0]   be_lv_cnt,
    input  wire          be_inj_hold,
    output reg           fe_kz,
    // AU -> FE
    input  wire          au_tbl_ok,
    // S1  FE -> AU
    output reg           fe_s1_v,
    output reg  [39:0]   fe_s1_base,
    output reg  [31:0]   fe_s1_lstr,
    output reg  [31:0]   fe_s1_l1str,
    output reg  [31:0]   fe_s1_str,
    output reg  [26:0]   fe_s1_dmul,
    output reg  [5:0]    fe_s1_dsel,
    output reg  [5:0]    fe_s1_nsel,
    output reg  [19:0]   fe_s1_n,
    output reg           fe_s1_idx,
    output reg  [1:0]    fe_s1_sp,
    output reg  [15:0]   fe_s1_L,
    output reg  [15:0]   fe_s1_L1,
    output reg  [2:0]    fe_s1_slot,
    output reg  [2:0]    fe_s1_j,
    output reg  [((QD <= 2) ? 1 : $clog2(QD))-1:0] fe_s1_tag,
    output reg           fe_s1_last,
    output reg           fe_s1_isI,
    output reg           fe_s1_hi,
    output reg           fe_s1_et,
    output reg  [2:0]    fe_hslot,
    // S2  FE -> BE
    output reg           fe_s2a_v,
    output reg  [((QD <= 2) ? 1 : $clog2(QD))-1:0] fe_s2a_tag,
    output reg  [127:0]  fe_s2a_hdr,
    output reg  [2:0]    fe_s2a_kind,
    output reg           fe_s2a_rdy0,
    output reg  [15:0]   fe_s2a_L,
    output reg  [15:0]   fe_s2a_L1,
    output reg           fe_s2i_v,
    output reg  [255:0]  fe_s2i_d,
    output reg  [((QD <= 2) ? 1 : $clog2(QD))-1:0] fe_s2i_tag,
    output reg  [2:0]    fe_s2i_slot,
    output reg           fe_s2i_sut,
    output reg           fe_s2i_np0
);
`include "ot_hgi_seq_seam.svh"
    // ---- pins: hold-delay stage + pin flop on every input (as the flat design)
    wire [160-1:0] md_d_h; ot_hgi_seq_hd #(.W(160), .N(2)) u_hdly_md_d (.a(md_d), .y(md_d_h));
    wire [11*32-1:0] md_k_h; ot_hgi_seq_hd #(.W(11*32), .N(2)) u_hdly_md_k (.a(md_k), .y(md_k_h));
    wire [1-1:0] f_req_rdy_h; ot_hgi_seq_hd #(.W(1), .N(2)) u_hdly_f_req_rdy (.a(f_req_rdy), .y(f_req_rdy_h));
    wire [1-1:0] f_rsp_v_h; ot_hgi_seq_hd #(.W(1), .N(2)) u_hdly_f_rsp_v (.a(f_rsp_v), .y(f_rsp_v_h));
    wire [256-1:0] f_rsp_data_h; ot_hgi_seq_hd #(.W(256), .N(2)) u_hdly_f_rsp_data (.a(f_rsp_data), .y(f_rsp_data_h));
    reg [159:0] md_d_r; reg [11*32-1:0] md_k_r; reg f_rsp_v_r; reg [255:0] f_rsp_data_r;
    // ---- reset: this child's OWN release synchroniser, two kept copies (boundary / fetch state, parser)
    (* keep = 1 *) reg [1:0] rs_q, rs_f;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rs_q <= 2'b00; rs_f <= 2'b00; end
        else begin rs_q <= {rs_q[0], 1'b1}; rs_f <= {rs_f[0], 1'b1}; end
    wire rn = rs_q[1];                   // boundary / fetch state
    wire rn_f = rs_f[1];                 // parser / FIFO / seam valids
    always @(posedge clk or negedge rn) if (!rn) f_rsp_v_r <= 1'b0; else f_rsp_v_r <= f_rsp_v_h;
    always @(posedge clk) begin md_d_r <= md_d_h; md_k_r <= md_k_h; f_rsp_data_r <= f_rsp_data_h; end
    localparam integer RB = $clog2(RW);
    localparam integer RS = RW / 2;                       // sectors
    localparam integer QB = (QD <= 2) ? 1 : $clog2(QD);
    // ------------------------------------------------------------------ field positions (spec.json, v1.0)
    localparam integer H_UNIT = 124, H_OP = 118, H_WAIT = 102, H_PRED = 100, H_OPND = 93, H_TMPL = 92, H_SLOT = 89,
                       H_PARAM = 64;
    localparam integer M_SPACE = 0, M_IBC = 5, M_IDX = 6, M_BASE = 8, M_N = 48, M_M = 68, M_STRIDE = 88,
                       M_LSTR = 136, M_DSEL = 168, M_DMUL = 174, M_NSEL = 201, M_L1STR = 207;
    localparam [2:0] K_DISP = 3'd0, K_END = 3'd1, K_TOKX = 3'd2, K_FENCE = 3'd3, K_LVM = 3'd4, K_FLT = 3'd5;
    // ------------------------------------------------------------------ ring + fetch (word pointers, RB+1 bits)
    reg [RB:0]  wp, frp;                 // write (sector aligned), free (outermost loop body start or the parse pointer)
    reg [39:0]  faddr, faddr_n, faddr_nn, img_q;   // faddr_n = faddr + 32 kept registered (the push selects; no 40-bit add)
    reg [7:0]   inflight, drop;
    reg         fetching;
    wire [RB:0] frp_al = {frp[RB:1], 1'b0};
    wire [RB+1:0] used = {1'b0, wp - frp_al} + {{(RB-7){1'b0}}, inflight, 1'b0};
    reg         wv;                      // a sector has landed since the doorbell
    reg [RB:0]  rd_ptr;                  // the ring read address (registered); the sector lands three edges later
    // the ring (unchanged from v1): macro-side flops on both ports; a sector read issued on edge E is valid in the
    // cycle after E + 2 (rd_sec); a write lands one edge after wp advances and every read of that sector samples its
    // address at least one edge after wp advanced (the reader issues on wp - rdp != 0 from flops)
    reg [255:0] rd_sec;
    wire        ring_we = f_rsp_v_r && (drop == 8'd0);
    generate if (USE_MACRO) begin : g_ring_m
        initial if (RW != 512 && RW != 4096) $fatal(1, "ot_hgi_seq: USE_MACRO needs RW 512 or 4096");
        if (RW == 512) begin : g_8k
            wire [255:0] q; reg [255:0] q_r, wd_q; reg we_q; reg [7:0] wa_q;
            always @(posedge clk) begin q_r <= q; we_q <= ring_we; wa_q <= wp[8:1]; if (ring_we) wd_q <= f_rsp_data_r; end
            ot_sram_1r1w_256x256_m2_r2c2 u_ring (.clk(clk), .r_ce_in(1'b1), .r_addr_in(rd_ptr[8:1]), .rd_out(q),
                .w_ce_in(we_q), .w_addr_in(wa_q), .wd_in(wd_q), .w_mask_in({256{1'b1}}),
                .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
            always @* rd_sec = q_r;
        end else begin : g_64k                                  // bank = word pointer bit 11 (sector bit 10)
            wire [255:0] q0, q1; reg rb_q, rb_qq; reg [255:0] q0_r, q1_r, wd0_q, wd1_q; reg we0_q, we1_q; reg [9:0] wa0_q, wa1_q;
            wire [255:0] wd0_d, wd1_d;     // v2.3: hold-delay stage flop -> macro write data (FF hold -4.2 ps)
            ot_hgi_seq_hd #(.W(256), .N(2)) u_hdly_wd0 (.a(wd0_q), .y(wd0_d));
            ot_hgi_seq_hd #(.W(256), .N(2)) u_hdly_wd1 (.a(wd1_q), .y(wd1_d));
            // v2.4 (route 8447139d1 FF hold: wd1_q -> u_ring1/wd_in -15.5, we1_q -> w_ce_in -7.6): two kept HB4 stages on
            // the macro write data / enables (flop -> macro hold, the macro's clock pin sits late in the tree)
            wire we0_d, we1_d;
            ot_hgi_seq_hd #(.W(1), .N(2)) u_hdly_we0 (.a(we0_q), .y(we0_d));
            ot_hgi_seq_hd #(.W(1), .N(2)) u_hdly_we1 (.a(we1_q), .y(we1_d));
            always @(posedge clk) begin
                rb_q <= rd_ptr[11]; rb_qq <= rb_q;
                if (!rb_q) q0_r <= q0;                          // the bank read on the previous edge
                if (rb_q)  q1_r <= q1;
                we0_q <= ring_we && !wp[11]; wa0_q <= wp[10:1]; if (ring_we && !wp[11]) wd0_q <= f_rsp_data_r;
                we1_q <= ring_we &&  wp[11]; wa1_q <= wp[10:1]; if (ring_we &&  wp[11]) wd1_q <= f_rsp_data_r;
            end
            ot_sram_1r1w_1024x256_m2_r2c2 u_ring0 (.clk(clk), .r_ce_in(!rd_ptr[11]), .r_addr_in(rd_ptr[10:1]), .rd_out(q0),
                .w_ce_in(we0_d), .w_addr_in(wa0_q), .wd_in(wd0_d), .w_mask_in({256{1'b1}}),
                .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
            ot_sram_1r1w_1024x256_m2_r2c2 u_ring1 (.clk(clk), .r_ce_in(rd_ptr[11]), .r_addr_in(rd_ptr[10:1]), .rd_out(q1),
                .w_ce_in(we1_d), .w_addr_in(wa1_q), .wd_in(wd1_d), .w_mask_in({256{1'b1}}),
                .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
            always @* rd_sec = rb_qq ? q1_r : q0_r;
        end
    end else begin : g_ring_r
        reg [255:0] ring [0:RS-1]; reg [255:0] rd_sec0;
        always @(posedge clk) begin
            rd_sec0 <= ring[rd_ptr[RB-1:1]]; rd_sec <= rd_sec0;     // the same 3-edge read latency as the macro ring
            if (ring_we) ring[wp[RB-1:1]] <= f_rsp_data_r;
        end
    end endgenerate
    // ------------------------------------------------------------------ fetch request FIFO (unchanged, NOS wide)
    reg [39:0] rqf [0:1]; reg rqh; reg [1:0] rqn;
    wire [1:0] rqn_m1 = rqn - 2'd1, rqn_p1 = rqn + 2'd1;
    assign f_req_v = (rqn != 2'd0);
    assign f_req_addr = rqf[rqh];
    wire [7:0] infl_p1 = inflight + 8'd1, infl_m1 = inflight - 8'd1;
    reg room_q;
    wire       rq_push = fetching && (rqn != 2'd2) && (inflight < NOS) && room_q;
    always @(posedge clk or negedge rn) if (!rn) room_q <= 1'b0; else room_q <= (used + (rq_push ? 2 : 0) + 2 <= RW);
    wire       rq_pop = f_req_v && f_req_rdy_h;
    always @(posedge clk or negedge rn)
        if (!rn) begin rqh <= 1'b0; rqn <= 2'd0; end
        else begin
            if (rq_push) rqf[rqh ^ (rqn != 2'd0)] <= faddr;
            if (rq_pop) rqh <= ~rqh;
            rqn <= rq_pop ? (rq_push ? rqn : rqn_m1) : (rq_push ? rqn_p1 : rqn);
        end
    wire [7:0] fl_after = (rq_push && !f_rsp_v_r) ? infl_p1 : (!rq_push && f_rsp_v_r) ? infl_m1 : inflight;
    function automatic [3:0] nops(input [3:0] u);
        // = hbm_generic_iface D_OPS (hgi-1010: HC 3 ops since G22 HC_MIX_ROWS / HC_MIX_POST; IDX MERGE / OWNED live)
        case (u) 4'd0: nops = 4'd8; 4'd4: nops = 4'd7; 4'd5: nops = 4'd2; 4'd6: nops = 4'd6; 4'd8: nops = 4'd4;
                 4'd9: nops = 4'd5; 4'd10: nops = 4'd3; 4'd1, 4'd2, 4'd3, 4'd7: nops = 4'd1; default: nops = 4'd0; endcase
    endfunction
    function automatic [2:0] mth(input [6:0] o, input [2:0] m);     // slot of the m-th present descriptor
        integer q; reg [2:0] c; begin mth = 3'd7; c = 0;
            for (q = 0; q < 7; q = q + 1) if (o[q]) begin if (c == m && mth == 3'd7) mth = q[2:0]; c = c + 3'd1; end
        end
    endfunction
    // ---- seam RX (R1): every seam input is registered once before use
    reg be_jl_v_r, be_js_r, be_stop_r, be_qpop_r, be_lv_v_r, be_inj_hold_r, au_tbl_ok_r;
    reg [1:0] be_jl_entry_r; reg [3:0] be_jl_kernel_r; reg [31:0] be_jl_loff_r; reg [19:0] be_jl_pos_r; reg [15:0] be_lv_cnt_r;
    always @(posedge clk or negedge rn_f)
        if (!rn_f) begin
            be_jl_v_r <= 1'b0; be_js_r <= 1'b0; be_stop_r <= 1'b0; be_qpop_r <= 1'b0; be_lv_v_r <= 1'b0; be_inj_hold_r <= 1'b0;
            au_tbl_ok_r <= 1'b0;
        end else begin
            be_jl_v_r <= be_jl_v; be_js_r <= be_js; be_stop_r <= be_stop; be_qpop_r <= be_qpop; be_lv_v_r <= be_lv_v;
            be_inj_hold_r <= be_inj_hold; au_tbl_ok_r <= au_tbl_ok;
        end
    always @(posedge clk) begin
        be_jl_entry_r <= be_jl_entry; be_jl_kernel_r <= be_jl_kernel; be_jl_loff_r <= be_jl_loff; be_jl_pos_r <= be_jl_pos;
        be_lv_cnt_r <= be_lv_cnt;
    end
    // returned queue credit (be_qpop, two seam flops after the BE's pop)
    reg qpop_sk;
`ifdef OT_HGI_SEQ_MUT_SEAM_QPOP
    wire cred_inc = be_qpop_r && !qpop_sk;                // NEGATIVE CONTROL: every 2nd returned credit dropped
`else
    wire cred_inc = be_qpop_r;
`endif
    // ---- job load: the image address (flat S_IDLE / S_DB / S_DB2 arithmetic, run as a 3-edge chain after the jl RX)
    (* keep = 1 *) reg run_f;         // the FE's run flag (set on be_js_r, cleared on be_stop_r)
    reg [1:0] db_entry_q; reg pos0;      // the job's entry; pos == 0 (the record predicates)
    reg [31:0] kern_off;
    wire [31:0] kern_base = (be_jl_kernel_r > 4'd10) ? 32'd0 : md_k_r[be_jl_kernel_r*32 +: 32];
    wire kern_pl = be_jl_kernel_r == 4'd3 || be_jl_kernel_r == 4'd7 || be_jl_kernel_r == 4'd8;
    wire [39:0] entry_off = {4'd0, (db_entry_q == 2'd0) ? md_d_r[31:0] : (db_entry_q == 2'd1) ? md_d_r[63:32] :
                             (db_entry_q == 2'd2) ? md_d_r[95:64] : kern_off, 4'd0};
    wire [39:0] img_a = {md_d_r[123:96], 12'd0};
    reg [20:0] img_l; reg [19:0] img_ha, img_hb;
    // kern_off in two edges (s1 route 983266320: be_jl_kernel_r -> 11:1 x 32 select -> zero test -> 32-b add -> select was
    // the block's only TT miss, -59.6 ps on 28 endpoints): edge 1 = the kernel-table select, edge 2 = zero test / add.
    reg jl_v2, kpl_q; reg [31:0] kb_q, loff_q;
    always @(posedge clk) begin
        jl_v2 <= be_jl_v_r; kb_q <= kern_base; kpl_q <= kern_pl; loff_q <= be_jl_loff_r;
        if (be_jl_v_r) begin db_entry_q <= be_jl_entry_r; pos0 <= (be_jl_pos_r == 20'd0); end
        if (jl_v2) kern_off <= (kb_q == 32'd0) ? 32'd0 : kpl_q ? kb_q + loff_q : kb_q;
        img_l <= {1'b0, img_a[19:0]} + {1'b0, entry_off[19:0]};
        img_ha <= img_a[39:20]; img_hb <= entry_off[39:20];
        img_q <= {img_ha + img_hb + {19'd0, img_l[20]}, img_l[19:0]};
    end
    // ================================================================== FE: ring reader, word FIFO, record parser
    localparam [2:0] F_H = 3'd0, F_P = 3'd1, F_LVW = 3'd2, F_HALT = 3'd3;
    localparam [1:0] RC_DSP = 2'd0, RC_DISC = 2'd1, RC_FLT = 2'd2;
    reg [2:0]  fs;
    reg [RB:0] rp, rdp;                  // record header pointer / next ring word to read
    reg        ep;                       // FIFO epoch (a redirect drops older reads)
    reg [3:0]  rv, rodd, rep;            // read pipe: valid, started at an odd word, epoch (4 edges since s3: + rd_sec_q)
    // s3 (s2 route 031099211: TT -55.2 on 50 endpoints, all rb_qq -> bank select x 256 -> word select -> FIFO entry
    // select -> fqv, 14-15 levels launched 106 ps late beside the ring macros): the selected sector is registered once
    // more before the FIFO.  The reader is credit-based (fcred at issue, returned at pop), so the pipe depth is free.
    reg [255:0] rd_sec_q;
    always @(posedge clk) rd_sec_q <= rd_sec;
    reg [FD*128-1:0] fqv;                // shift FIFO: word 0 is the head
    reg [4:0]  fq_n, fcred;              // words held / free credits (FD - held - in the read pipe)
    reg [FD+1:0] fq_th;                  // v2.3: thermometer copy of fq_n (fq_th[j] = j < fq_n), registered
    // the current record (registered at the header cycle)
    reg [127:0] h;
    reg [1:0]  rcl; reg rskip;
    reg [4:0]  hq_rlen; reg [RB:0] hq_rpn; reg [3:0] hq_nit; reg [2:0] hq_np; reg [20:0] hq_sl;
    reg [QB-1:0] ctag;                  // its queue entry
    reg [3:0]  pi;                       // items popped
    reg [1:0]  settle;                   // loop state changed: the registered loop flags settle before the next header
    // loops
    reg [1:0]  depth;
    reg        lv_lvl [0:1]; reg [15:0] lv_cnt [0:1]; reg [RB:0] lv_body [0:1];
    reg [15:0] Lc, L1c;
    wire       in_lvl = (depth == 2'd2) ? lv_lvl[1] : lv_lvl[0];
    wire [15:0] in_cnt = (depth == 2'd2) ? lv_cnt[1] : lv_cnt[0];
    wire [15:0] in_ctr = in_lvl ? L1c : Lc;
    reg [15:0] in_ctr_q, in_cnt_q; reg in_dep_q;
    always @(posedge clk) begin in_ctr_q <= in_ctr; in_cnt_q <= in_cnt; in_dep_q <= (depth != 2'd0); end
    reg        last_iter;
    always @(posedge clk) last_iter <= in_dep_q && (in_ctr_q + 16'd1 == in_cnt_q);
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
    always @(posedge clk) more <= more_c;
    // ---- header evaluation from the FIFO head (flops): every decision flag is registered at the header pop
    // v2.4 LAZY-SHIFT FIFO (route 8447139d1: run_q -> be_inj -> pc -> 1.5k fqv data flops TT -48.25, 22-24 levels; pc
    // fanned out to ~4.6k mux selects): the storage fqv lags the view by the PREVIOUS cycle's pop count pq (registered,
    // one keep'd copy per entry / reader group).  View word i = fqv[i + pq].  Storage update: keep view words below
    // fq_n (registered thermometer), pushes at fq_n / fq_n + 1 -- this cycle's pop decision pc reaches only pq, fq_n /
    // fq_th and the FE counters, never the FIFO data.  Readers add one 3:1 select from flops.
    wire [127:0] fv0, fv1;               // view words 0 and 1
    wire [127:0] hw = fv0;
    wire [3:0]  hw_unit = hw[H_UNIT +: 4];
    wire [5:0]  hw_op   = hw[H_OP +: 6];
    wire [1:0]  hw_pred = hw[H_PRED +: 2];
    wire [6:0]  hw_opnd = hw[H_OPND +: 7];
    wire        hw_tmpl = hw[H_TMPL];
    wire [24:0] hw_param = hw[H_PARAM +: 25];
    wire [2:0]  hw_np = hw_opnd[0] + hw_opnd[1] + hw_opnd[2] + hw_opnd[3] + hw_opnd[4] + hw_opnd[5] + hw_opnd[6];
    wire [4:0]  hw_rlen = 5'd1 + {3'd0, hw_tmpl, 1'b0} + {1'b0, hw_np, 1'b0};
    // body-over-the-ring check against a REGISTERED limit (RW - 2 - (rp - frp)): no subtract in the header cycle
    reg  [4:0]  lim5; reg lim_big;
    wire        hw_recbad = (depth != 2'd0) && !lim_big && (hw_rlen > lim5);
    wire        hw_bad = (hw_unit >= 4'd11) || (hw_op >= {2'd0, nops(hw_unit)});
    reg         hw_pok;
    always @* case (hw_pred) 2'd0: hw_pok = 1'b1; 2'd1: hw_pok = pos0; 2'd2: hw_pok = !pos0;
                             default: hw_pok = last_iter; endcase
    wire        hw_isctl = (hw_unit == 4'd0);
    wire        hw_ctl = hw_isctl && hw_op != 6'd3 && hw_op != 6'd5;
    wire        hw_noa = hw_isctl && !hw_opnd[0];
    wire        hw_loopbad = (!hw_param[17] && hw_param[15:0] == 16'd0) || (hw_param[17] && hw[63:50] != 14'd0) ||
                             depth == 2'd2 || (depth == 2'd1 && lv_lvl[0] == hw_param[16]);
    // record class: the v1 evaluation order (body over the ring, bad unit / op, predicate, CTL, END / TOKX without A)
    wire [1:0]  hw_rc = (hw_recbad || hw_bad) ? RC_FLT : !hw_pok ? RC_DISC :
                        hw_ctl ? ((hw_op == 6'd0 || hw_op == 6'd4) ? RC_DISC :
                                  (hw_op == 6'd1) ? (hw_loopbad ? RC_FLT : RC_DISC) :
                                  (hw_op == 6'd2) ? ((depth == 2'd0) ? RC_FLT : RC_DISC) : RC_FLT) :
                        hw_noa ? RC_FLT : RC_DSP;
    // ---- the FE's alloc tag and its queue credit (BE frees: be_qpop)
    reg [QB:0] q_cred; reg [QB-1:0] qt;
    // ---- FE control (combinational from flops)
    wire        job_start = be_js_r;     // the BE's job start, two seam flops later
    wire        fe_hcap  = run_f && fs == F_H && fq_th[0] && settle == 2'd0 && au_tbl_ok_r && (q_cred != {(QB+1){1'b0}} || cred_inc);   // a credit returning this cycle is usable now
    wire        fe_halloc = fe_hcap && hw_rc != RC_DISC;               // dispatch / END / TOKX / header fault entry
    // v2.3 (route 905100ec5 limiter hw -> e_hdr, TT -187): the header's queue entry is written the cycle AFTER the
    // header pop from registered state (h, hq_kind, hq_rdy0) under a per-entry registered enable (ha_e) -- the
    // header decode ends in a few flops instead of fanning out to every entry's ~200 data flops.
    reg         ha_v;                    // (split: the entry itself is written by BE from the S2 alloc channel)
    wire        fe_inp   = run_f && fs == F_P && rcl != RC_FLT;
    wire        fe_pop2  = fe_inp && (pi != hq_nit) && fq_th[1] && !(rcl == RC_DSP && be_inj_hold_r);
    wire        fe_sut   = fe_pop2 && rcl == RC_DSP && h[H_TMPL] && pi == 4'd0;
    wire        fe_item  = fe_pop2 && rcl == RC_DSP && !(h[H_TMPL] && pi == 4'd0);
    wire        fe_done  = fe_inp && (hq_nit == 4'd0 || (fe_pop2 && pi + 4'd1 == hq_nit));
    wire [5:0]  h_op = h[H_OP +: 6];
    wire        h_lvm = h[H_PARAM + 17];
    wire        fe_aalloc = fe_done && rcl == RC_DISC && !rskip && (h_op == 6'd4 || (h_op == 6'd1 && h_lvm));   // FENCE / LOOP-from-VM
    wire        fe_redir = fe_done && rcl == RC_DISC && !rskip && h_op == 6'd2 && more;
    wire        fe_flush = job_start || fe_redir;
    wire [1:0]  pc = fe_hcap ? 2'd1 : fe_pop2 ? 2'd2 : 2'd0;
    wire        q_alloc = ha_v || fe_aalloc;
    reg  [2:0]  q_akind;                 // the header's entry kind (registered into hq_kind at the pop)
    always @* begin
        if (hw_rc == RC_FLT) q_akind = K_FLT;
        else if (hw_isctl && hw_op == 6'd3) q_akind = K_END;
        else if (hw_isctl && hw_op == 6'd5) q_akind = K_TOKX;
        else q_akind = K_DISP;
    end
    wire [2:0]  fe_sl = hq_sl[(pi - {3'd0, h[H_TMPL]}) * 3 +: 3];      // the item's descriptor slot
    wire [255:0] fe_it = {fv1, fv0};                                    // the item (two words)
    // ---- reader: one sector a cycle while the ring has it and the FIFO has room
    wire [RB:0] ravail = wv ? (wp - rdp) : {(RB+1){1'b0}};
    wire        rd_iss = run_f && !fe_flush && (ravail != {(RB+1){1'b0}}) && fcred >= 5'd2;
    wire        push_ok = rv[3] && (rep[3] == ep) && !fe_flush;
    wire [1:0]  sc = !push_ok ? 2'd0 : rodd[3] ? 2'd1 : 2'd2;
    wire [127:0] pw0 = rodd[3] ? rd_sec_q[255:128] : rd_sec_q[127:0];
    wire [127:0] pw1 = rd_sec_q[255:128];
    // ---- loop-from-VM reply (BE)
    wire        lv_rsp = be_lv_v_r; wire [15:0] lv_rcnt = be_lv_cnt_r;
    // ---- FIFO data (no reset), v2.4 lazy shift: storage entry i takes storage word i + pq when i < fq_n (view kept),
    // pushed word 0 at i == fq_n, pushed word 1 at i == fq_n + 1.  Writes in a flush cycle are harmless (fq_th clears),
    // so the data path carries the raw push (no fe_flush cone).
    wire [FD+4:0] feq = {3'b000, fq_th[FD:0] & ~fq_th[FD+1:1], !fq_th[0]};    // feq[m] = (m == fq_n)
    wire        push_raw = rv[3] && (rep[3] == ep);
    wire [1:0]  scr = !push_raw ? 2'd0 : rodd[3] ? 2'd1 : 2'd2;
    wire [1:0]  pq_n = fe_flush ? 2'd0 : pc;
    genvar gi;
    generate for (gi = 0; gi < FD; gi = gi + 1) begin : g_fq
        (* keep = 1 *) reg [1:0] pq;      // this entry's copy of the previous pop count (one-hot-ish: 0 / 1 / 2)
        always @(posedge clk or negedge rn_f) if (!rn_f) pq <= 2'd0; else pq <= pq_n;
        wire [127:0] s0 = fqv[gi*128 +: 128];
        wire [127:0] s1 = (gi + 1 < FD) ? fqv[((gi + 1) % FD)*128 +: 128] : 128'd0;
        wire [127:0] s2 = (gi + 2 < FD) ? fqv[((gi + 2) % FD)*128 +: 128] : 128'd0;
        wire [127:0] cur = pq[1] ? s2 : pq[0] ? s1 : s0;
        wire keep = fq_th[gi];
        wire e0 = feq[gi];
        wire e1 = (gi >= 1) ? feq[(gi >= 1) ? gi - 1 : 0] : 1'b0;
        always @(posedge clk)
            if (keep) fqv[gi*128 +: 128] <= cur;
            else if (e0 && scr != 2'd0) fqv[gi*128 +: 128] <= pw0;
            else if (e1 && scr == 2'd2) fqv[gi*128 +: 128] <= pw1;
    end endgenerate
    // view readers: 4 x 32-bit groups (view words 0 and 1), each with its own pq copy
    generate for (gi = 0; gi < 4; gi = gi + 1) begin : g_fr
        (* keep = 1 *) reg [1:0] pr;
        always @(posedge clk or negedge rn_f) if (!rn_f) pr <= 2'd0; else pr <= pq_n;
        assign fv0[gi*32 +: 32] = pr[1] ? fqv[256 + gi*32 +: 32] : pr[0] ? fqv[128 + gi*32 +: 32] : fqv[gi*32 +: 32];
        assign fv1[gi*32 +: 32] = pr[1] ? fqv[384 + gi*32 +: 32] : pr[0] ? fqv[256 + gi*32 +: 32] : fqv[128 + gi*32 +: 32];
    end endgenerate
    // v2.4: the thermometer moves by d = sc - pc (-2..+2): five shifted copies from flops, selected by d
    wire [FD+1:0] th_m2 = {2'b00, fq_th[FD+1:2]}, th_m1 = {1'b0, fq_th[FD+1:1]}, th_p1 = {fq_th[FD:0], 1'b1},
                  th_p2 = {fq_th[FD-1:0], 2'b11};
    wire [FD+1:0] th_n = (pc == 2'd2) ? ((sc == 2'd2) ? fq_th : (sc == 2'd1) ? th_m1 : th_m2) :
                         (pc == 2'd1) ? ((sc == 2'd2) ? th_p1 : (sc == 2'd1) ? fq_th : th_m1) :
                                        ((sc == 2'd2) ? th_p2 : (sc == 2'd1) ? th_p1 : fq_th);
    always @(posedge clk or negedge rn_f)
        if (!rn_f) fq_th <= {(FD+2){1'b0}};
        else if (fe_flush) fq_th <= {(FD+2){1'b0}};
        else fq_th <= th_n;
    // ---- ring-limit register: rpd = rp - frp after this cycle's update, lim = RW - 2 - rpd
    reg  [RB:0] rpd;
    wire        fe_adv = run_f && !job_start && fs == F_P && fe_done &&
                         (rcl == RC_DSP || rskip || h_op == 6'd0 || h_op == 6'd4);      // rp <= hq_rpn, no settle
    wire [RB:0] rpd_n = job_start ? {(RB+1){1'b0}} : (settle != 2'd0) ? (rp - frp) :
                        fe_adv ? ((depth == 2'd0) ? {(RB+1){1'b0}} : rpd + {{(RB-4){1'b0}}, hq_rlen}) : rpd;
    wire [RB:0] lim_n = RW - 2 - rpd_n;
    always @(posedge clk) begin rpd <= rpd_n; lim5 <= lim_n[4:0]; lim_big <= |lim_n[RB:5]; end
    always @(posedge clk or negedge rn_f) if (!rn_f) ha_v <= 1'b0; else ha_v <= !job_start && fe_halloc;
    // ---- FE sequential
    integer fk;
    always @(posedge clk or negedge rn_f) begin
        if (!rn_f) begin
            fs <= F_HALT; rp <= 0; rdp <= 0; frp <= 0; ep <= 1'b0; rv <= 4'b0000; rodd <= 4'b0000; rep <= 4'b0000;
            fq_n <= 5'd0; fcred <= FD; depth <= 2'd0; Lc <= 16'd0; L1c <= 16'd0; settle <= 2'd0; pi <= 4'd0;
            rd_ptr <= 0; rcl <= RC_DISC; rskip <= 1'b0;
        end else begin
            // reader pipe
            rv <= {rv[2:0], rd_iss}; rodd <= {rodd[2:0], rdp[0]}; rep <= {rep[2:0], ep};
            if (rd_iss) begin rd_ptr <= rdp; rdp <= {rdp[RB:1] + {{(RB-1){1'b0}}, 1'b1}, 1'b0}; end
            if (settle != 2'd0) settle <= settle - 2'd1;
            // FIFO occupancy / credits (pops return credits, issues take them)
            if (fe_flush) begin fq_n <= 5'd0; fcred <= FD; end
            else begin
                fq_n <= fq_n - {3'd0, pc} + {3'd0, sc};
                fcred <= fcred + {3'd0, pc} - (rd_iss ? (rdp[0] ? 5'd1 : 5'd2) : 5'd0);
            end
            if (job_start) begin
                fs <= F_H; rp <= {{RB{1'b0}}, img_q[4]}; rdp <= {{RB{1'b0}}, img_q[4]}; frp <= {{RB{1'b0}}, img_q[4]};
                ep <= ~ep; depth <= 2'd0; Lc <= 16'd0; L1c <= 16'd0; settle <= 2'd0; pi <= 4'd0;
            end else if (run_f) begin
                case (fs)
                    F_H: if (fe_hcap) begin
                        h <= hw; rcl <= hw_rc; rskip <= !hw_pok && !(hw_recbad || hw_bad);
                        hq_rlen <= hw_rlen; hq_rpn <= rp + {{(RB-4){1'b0}}, hw_rlen};
                        hq_nit <= {3'd0, hw_tmpl} + {1'b0, hw_np}; hq_np <= hw_np;
                        for (fk = 0; fk < 7; fk = fk + 1) hq_sl[fk*3 +: 3] <= mth(hw_opnd, fk[2:0]);
                        ctag <= qt; pi <= 4'd0;
                        fs <= F_P;
                    end
                    F_P: begin
                        if (rcl == RC_FLT) fs <= F_HALT;            // the fault entry is queued; decode stops
                        if (fe_pop2) pi <= pi + 4'd1;
                        if (fe_done) begin
                            if (rcl == RC_DSP) begin
                                rp <= hq_rpn; if (depth == 2'd0) frp <= hq_rpn;
                                fs <= (h[H_UNIT +: 4] == 4'd0 && h_op == 6'd3) ? F_HALT : F_H;   // END: decode stops
                            end else if (rskip || h_op == 6'd0 || h_op == 6'd4) begin             // skip / NOP / FENCE
                                rp <= hq_rpn; if (depth == 2'd0) frp <= hq_rpn; fs <= F_H;
                            end else if (h_op == 6'd1) begin                                       // LOOP
                                if (h_lvm) fs <= F_LVW;
                                else begin
                                    lv_lvl[depth[0]] <= h[H_PARAM + 16]; lv_cnt[depth[0]] <= h[H_PARAM +: 16];
                                    lv_body[depth[0]] <= hq_rpn;
                                    if (h[H_PARAM + 16]) L1c <= 16'd0; else Lc <= 16'd0;
                                    depth <= depth + 2'd1; rp <= hq_rpn;
                                    if (depth == 2'd0) frp <= hq_rpn;
                                    settle <= 2'd2; fs <= F_H;
                                end
                            end else begin                                                         // ENDLOOP
                                if (more) begin
                                    if (top_lvl) L1c <= L1c + 16'd1; else Lc <= Lc + 16'd1;
                                    rp <= lv_body[top[0]]; rdp <= lv_body[top[0]]; ep <= ~ep;      // replay from the ring
                                end else begin
                                    if (top_lvl) L1c <= 16'd0; else Lc <= 16'd0;
                                    depth <= depth - 2'd1; rp <= hq_rpn;
                                    if (depth == 2'd1) frp <= hq_rpn;
                                end
                                settle <= 2'd2; fs <= F_H;
                            end
                        end
                    end
                    F_LVW: if (lv_rsp) begin                                                       // the count arrived
                        lv_lvl[depth[0]] <= h[H_PARAM + 16]; lv_cnt[depth[0]] <= lv_rcnt;
                        lv_body[depth[0]] <= hq_rpn;
                        if (h[H_PARAM + 16]) L1c <= 16'd0; else Lc <= 16'd0;
                        depth <= depth + 2'd1; rp <= hq_rpn;
                        if (depth == 2'd0) frp <= hq_rpn;
                        settle <= 2'd2; fs <= F_H;
                    end
                    default: ;
                endcase
            end
        end
    end
    // ---- fetch state (moved out of the flat main block; the flat S_DB3 load runs on be_js_r)
    always @(posedge clk or negedge rn)
        if (!rn) begin wp <= 0; wv <= 1'b0; inflight <= 0; drop <= 0; fetching <= 1'b0; run_f <= 1'b0; end
        else begin
            inflight <= fl_after;
            if (rq_push) begin faddr <= faddr_n; faddr_n <= faddr_nn; faddr_nn <= faddr_nn + 40'd32; end   // v2.3: no add after the push decision
            if (f_rsp_v_r) begin
                if (drop != 0) drop <= drop - 8'd1;
                else begin wp <= wp + 2'd2; wv <= 1'b1; end
            end
            if (be_stop_r) begin run_f <= 1'b0; fetching <= 1'b0; end
            if (job_start) begin
                faddr <= {img_q[39:5], 5'd0}; faddr_n <= {img_q[39:5] + 35'd1, 5'd0}; faddr_nn <= {img_q[39:5] + 35'd2, 5'd0}; fetching <= 1'b1;
                wp <= 0; wv <= 1'b0; drop <= fl_after; run_f <= 1'b1;
            end
        end
    // ---- alloc tag and queue credit (re-protocolled q_cnt < QD): BE's q_cnt <= QD - q_cred at every edge
`ifdef OT_HGI_SEQ_MUT_SEAM_CRED
    localparam [QB:0] CRED0 = QD + 1;                     // NEGATIVE CONTROL: one credit too many (queue overrun)
`else
    localparam [QB:0] CRED0 = QD;
`endif
    // one credit an alloc sent.  The header alloc is counted from its registered copy ha_v (the cycle after the header
    // pop: the next header pop is >= 2 cycles after this one, so the count is current when it is read; counting on
    // fe_halloc put the whole header decode in front of the credit adder: 17 levels, ~610 ps in the pre-route gate)
    wire cred_dec = q_alloc;
    always @(posedge clk or negedge rn_f)
        if (!rn_f) begin qt <= {QB{1'b0}}; q_cred <= CRED0; qpop_sk <= 1'b0; end
        else if (job_start) begin qt <= {QB{1'b0}}; q_cred <= CRED0; qpop_sk <= 1'b0; end
        else begin
            if (q_alloc) qt <= qt + 1'b1;
            q_cred <= q_cred + {{QB{1'b0}}, cred_inc} - {{QB{1'b0}}, cred_dec};
            if (be_qpop_r) qpop_sk <= ~qpop_sk;
        end
    // ---- seam TX (R1): one dedicated flop a bit, valids on the FE reset
    always @(posedge clk or negedge rn_f)
        if (!rn_f) begin fe_s1_v <= 1'b0; fe_s2a_v <= 1'b0; fe_s2i_v <= 1'b0; fe_kz <= 1'b0; end
        else begin
            fe_s1_v <= fe_item; fe_s2a_v <= !job_start && (fe_halloc || fe_aalloc); fe_s2i_v <= fe_item || fe_sut;
            fe_kz <= (kern_off == 32'd0);
        end
    always @(posedge clk) begin
        // S1: the FE branch of the flat a0_* load
        fe_s1_base <= fe_it[M_BASE +: 40]; fe_s1_lstr <= fe_it[M_LSTR +: 32];
        fe_s1_l1str <= fe_it[M_L1STR +: 32]; fe_s1_str <= fe_it[M_STRIDE +: 32]; fe_s1_dmul <= fe_it[M_DMUL +: 27];
        fe_s1_dsel <= fe_it[M_DSEL +: 6]; fe_s1_nsel <= fe_it[M_NSEL +: 6]; fe_s1_n <= fe_it[M_N +: 20]; fe_s1_idx <= fe_it[M_IDX];
        fe_s1_sp <= fe_it[M_SPACE +: 2]; fe_s1_L <= Lc; fe_s1_L1 <= L1c; fe_s1_slot <= h[H_SLOT +: 3]; fe_s1_j <= fe_sl; fe_s1_tag <= ctag;
        fe_s1_last <= (pi + 4'd1 == hq_nit); fe_s1_isI <= (fe_sl == 3'd6); fe_s1_hi <= h[H_OPND + 6];
        fe_s1_et <= (h[H_UNIT +: 4] == 4'd0) && (h_op == 6'd3 || h_op == 6'd5);
        if (fe_hcap) fe_hslot <= hw[H_SLOT +: 3];
        // S2 item: the flat it_d staging
        fe_s2i_d <= fe_it; fe_s2i_tag <= ctag; fe_s2i_slot <= fe_sl; fe_s2i_sut <= fe_sut; fe_s2i_np0 <= (hq_np == 3'd0);
        // S2 alloc: the header's entry (from the FIFO head at the header pop) or a FENCE / LOOP-from-VM entry (from h)
        // (the header branch loads on the state decode alone, as the flat d_ld: the TX data only matter under fe_s2a_v,
        // and the header decode -> fe_halloc -> 170 TX enables was the FE's longest stage, ~600 ps in the pre-route gate)
        if (fs == F_H) begin
            fe_s2a_tag <= qt; fe_s2a_hdr <= hw; fe_s2a_kind <= q_akind;
            fe_s2a_rdy0 <= (hw_rc == RC_FLT) || (!hw_tmpl && hw_np == 3'd0); fe_s2a_L <= Lc; fe_s2a_L1 <= L1c;
        end else if (fe_aalloc) begin
            fe_s2a_tag <= qt; fe_s2a_hdr <= h; fe_s2a_kind <= (h_op == 6'd4) ? K_FENCE : K_LVM;
            fe_s2a_rdy0 <= 1'b1; fe_s2a_L <= Lc; fe_s2a_L1 <= L1c;
        end
    end
endmodule
`default_nettype wire
