`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// One slice (one contiguous position range, "quarter") of the V4.1x streaming-filter
// SELECT ot_hdc_v41x_sel.  See ot_hdc_v41x_sel.sv for the unit's contract; this header
// describes the slice.
//
// Ingest.  A beat (W lanes {lv, BF16 value, index}) is registered (i0), each lane's
// order-preserving key is compared with the unit's running bound T (i1): a lane
// SURVIVES when key > T (a later key equal to T loses the tie to the k earlier ones).  Survivors are counted in the coarse histogram (hi digit)
// and, when their hi digit equals the tracked bucket Bt, in the fine histogram (lo
// digit); they are compacted and packed into full W-lane lines appended to the line
// memory at `head` (the write port gives ingest lines priority).  A line that finds
// the memory full is dropped and the slice reports overflow (the unit then replays).
//
// Sweeps.  One engine reads the line memory in order and writes the lanes it keeps
// back IN PLACE from line 0 (write address <= lines already read, so nothing unread
// is overwritten).  The memory content is the concatenation of up to three ranges
// A = [0, a_end), B = [b_st, b_end), C = [y_st, head): a sweep reads A, B, C and ends
// with A = its output (B, C empty; C restarts at the sweep's stop point).
//   GC  (while ingesting)  keep key >= T (the current bound, re-read every edge);
//       read issue is credit-limited to DG lines in flight + queued, because the
//       write port belongs to the ingest first.  Aborted by c_stop: the unread rest
//       becomes B (or C).
//   P2  keep key >= {bucket, 0}; histogram the lo digits of the bucket's elements in
//       the fine histogram (cleared at the start).
//   P3  keep key > T*, or key == T* among the first `rem` ties in stream order.
//   then EMIT: lines [0, a_end) leave on the output port (valid/ready, OD-entry FIFO).
// In replay mode (after an overflow anywhere in the unit) P2 and P3 take their beats
// from the input port instead of the memory (the source re-streams the range); P2
// replay only histograms, P3 replay writes its selection from line 0.
//
// Every element that can still be selected is kept by every sweep (see the unit
// header), so the final content before EMIT is exactly the slice's part of the
// selection, in stream (= position) order.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_sel_slice #(
    parameter integer W  = 16,        // lanes (power of two, >= 2)
    parameter integer IW = 20,        // index width
    parameter integer K  = 512,       // largest runtime k
    parameter integer AW = 8,         // line-memory address width (2^AW lines of W lanes)
    parameter integer DG = 8,         // GC write-back queue (lines)
    parameter integer OD = 4,         // output FIFO (beats)
    parameter integer KW = $clog2(K + 1),
    parameter integer CB = KW + 1     // saturating histogram bin width
) (
    input  wire                  clk,
    input  wire                  rst_n,
    // input stream
    input  wire                  in_valid,
    output wire                  in_ready,
    input  wire                  in_last,
    input  wire [W-1:0]          in_lv,
    input  wire [W*16-1:0]       in_val,
    input  wire [W*IW-1:0]       in_idx,
    // commands from the control (registered there, registered again here)
    input  wire [15:0]           c_T,
    input  wire [7:0]            c_Bt,
    input  wire                  c_fclr,
    input  wire [3:0]            c_cg,
    input  wire [3:0]            c_fg,
    input  wire                  c_ing,
    input  wire                  c_stop,
    input  wire                  c_p2,
    input  wire                  c_p3,
    input  wire                  c_rep,
    input  wire [15:0]           c_st,
    input  wire [KW:0]           c_rem,
    input  wire                  c_hclr,
    // status to the control (registered)
    output wire [16*(CB+4)-1:0]  s_gc,
    output wire [16*(CB+4)-1:0]  s_gf,
    output wire [16*CB-1:0]      s_bc,
    output wire [16*CB-1:0]      s_bf,
    output reg                   s_last,
    output reg                   s_hfin,
    output reg                   s_stopped,
    output reg                   s_done2,
    output reg                   s_emitted,
    output reg                   s_ovf,
    output reg  [AW:0]           s_nhead,    // statistics: lines written by the ingest
    output reg  [AW:0]           s_n2,       //             lines read by P2
    output reg  [AW:0]           s_n3,       //             lines read by P3
    // line memory (1R1W, synchronous read: data from the edge after the read)
    output reg                   mem_we,
    output reg  [AW-1:0]         mem_waddr,
    output reg  [W*(17+IW)-1:0]  mem_wdata,
    output reg                   mem_re,
    output reg  [AW-1:0]         mem_raddr,
    input  wire [W*(17+IW)-1:0]  mem_rdata,
    // output stream
    output wire                  out_valid,
    input  wire                  out_ready,
    output wire                  out_last,
    output wire [W-1:0]          out_lv,
    output wire [W*16-1:0]       out_val,
    output wire [W*IW-1:0]       out_idx,
    output wire [W-1:0]          out_ninf
);
    localparam integer EW   = 17 + IW;             // lane {lv, value, index}
    localparam integer LW   = (W > 1) ? $clog2(W) : 1;
    localparam integer CAPI = 1 << AW;
    localparam [AW:0]  CAP  = CAPI[AW:0];
    localparam integer FW   = (DG > 1) ? $clog2(DG) : 1;
    localparam integer OCW  = $clog2(OD + 1);
    localparam [2:0] P_ING = 3'd0, P_STOP = 3'd1, P_P2 = 3'd2, P_P3 = 3'd3, P_EM = 3'd4, P_DONE = 3'd5;
    localparam [2:0] SW_IDLE = 3'd0, SW_RD = 3'd1, SW_FL = 3'd2, SW_DR = 3'd3, SW_WB = 3'd4;
    localparam [1:0] K_GC = 2'd0, K_P2 = 2'd1, K_P3 = 2'd2;

    function automatic [15:0] fkey(input [15:0] v);
        fkey = (v[14:0] == 0) ? 16'h8000 : v[15] ? ~v : {1'b1, v[14:0]};
    endfunction

    // -- command registers -------------------------------------------------------------
    reg [15:0] r_T, r_st;
    reg [7:0]  r_Bt;
    reg [3:0]  r_cg, r_fg;
    reg [KW:0] r_rem;
    reg        r_fclr, r_ing, r_stop, r_p2, r_p3, r_rep, r_hclr;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            r_fclr <= 1'b0; r_ing <= 1'b0; r_stop <= 1'b0; r_p2 <= 1'b0; r_p3 <= 1'b0; r_rep <= 1'b0; r_hclr <= 1'b0;
            r_T <= 16'h0000;
        end else begin
            r_fclr <= c_fclr; r_ing <= c_ing; r_stop <= c_stop; r_p2 <= c_p2; r_p3 <= c_p3; r_rep <= c_rep;
            r_hclr <= c_hclr; r_T <= c_T;
        end
    end
    always @(posedge clk) begin r_st <= c_st; r_Bt <= c_Bt; r_cg <= c_cg; r_fg <= c_fg; r_rem <= c_rem; end

    reg [2:0] init;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) init <= 3'd7;
        else if (init != 0) init <= init - 1'b1;
    end
    wire seg_clr = r_hclr || (init != 0);

    // -- state ---------------------------------------------------------------------------
    reg [2:0]  ph, sw_st;
    reg [1:0]  sw_k, sw_seg, ab_seg;
    reg        sw_rp, sw_all, ab;
    reg [AW:0] rd, w, rd_ab, rd_stop, a_end, b_st, b_end, y_st, head;
    reg [15:0] sw_T, t_last;
    reg        ovf, last_seen, ing_fl_done;

    // -- input ---------------------------------------------------------------------------
    wire rp_acc = (sw_st == SW_RD) && sw_rp;
    assign in_ready = (init == 0) && !last_seen && (((ph == P_ING) && r_ing && !r_stop) || rp_acc);
    wire acc = in_valid && in_ready;
    reg            i0_v, i0_last, i0_rp;
    reg [W-1:0]    i0_lv;
    reg [W*16-1:0] i0_val;
    reg [W*IW-1:0] i0_idx;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) i0_v <= 1'b0;
        else i0_v <= acc;
    end
    always @(posedge clk) if (acc) begin
        i0_last <= in_last; i0_lv <= in_lv; i0_val <= in_val; i0_idx <= in_idx; i0_rp <= rp_acc;
    end

    // -- ingest: filter ------------------------------------------------------------------
    genvar gl;
    wire [W-1:0]    i1_s_d, i1_fm_d;
    wire [W*16-1:0] i1_k_d;
    wire [W*EW-1:0] i0_lane;                        // {lv, value, index} per lane
    generate
        for (gl = 0; gl < W; gl = gl + 1) begin : g_i1
            wire [15:0] k = fkey(i0_val[16*gl +: 16]);
            assign i1_k_d[16*gl +: 16] = k;
            // strict: the k elements that verified T all arrived earlier, so a later key == T
            // loses to every one of them (ties go to the lower index)
            assign i1_s_d[gl]  = i0_lv[gl] && (k > r_T);
            assign i1_fm_d[gl] = i0_lv[gl] && (k > r_T) && (k[15:8] == r_Bt);
            assign i0_lane[EW*gl +: EW] = {i0_lv[gl], i0_val[16*gl +: 16], i0_idx[IW*gl +: IW]};
        end
    endgenerate
    reg            i1_v, i1_fl;
    reg [W-1:0]    i1_s, i1_fm;
    reg [W*16-1:0] i1_k;
    reg [W*EW-1:0] i1_p;
    wire i_ing = i0_v && !i0_rp;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin i1_v <= 1'b0; i1_fl <= 1'b0; end
        else begin i1_v <= i_ing; i1_fl <= i_ing && i0_last; end
    end
    always @(posedge clk) begin i1_s <= i1_s_d; i1_fm <= i1_fm_d; i1_k <= i1_k_d; i1_p <= i0_lane; end

    // -- sweep read path: R1 (line), C1 (compare), C2 (tie prefix), C3 (select) -----------
    reg          t1_v, t1_fl, t1_em, t1_last, t2_v, t2_fl, t2_em, t2_last;
    reg          r1_v, r1_fl;
    reg [W*EW-1:0] r1_d;
    wire rp_beat = i0_v && i0_rp;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin r1_v <= 1'b0; r1_fl <= 1'b0; t2_v <= 1'b0; t2_fl <= 1'b0; t2_em <= 1'b0; end
        else begin
            t2_v <= t1_v; t2_fl <= t1_fl; t2_em <= t1_em;
            r1_v  <= (t2_v && !t2_em) || t2_fl || rp_beat;
            r1_fl <= t2_fl || (rp_beat && i0_last);
        end
    end
    always @(posedge clk) begin
        t2_last <= t1_last;
        r1_d <= rp_beat ? i0_lane : t2_fl ? {W*EW{1'b0}} : mem_rdata;
    end
    wire [15:0] tsw = (sw_k == K_GC) ? r_T : sw_T;
    wire [W-1:0]    c1_gt_d, c1_eq_d, p2_en;
    wire [W*8-1:0]  p2_dg;
    generate
        for (gl = 0; gl < W; gl = gl + 1) begin : g_c1
            wire        lv = r1_d[EW*gl + EW - 1];
            wire [15:0] k  = fkey(r1_d[EW*gl + IW +: 16]);
            assign c1_gt_d[gl] = lv && (k > tsw);
            assign c1_eq_d[gl] = lv && (k == tsw);
            assign p2_en[gl]   = lv && (k[15:8] == sw_T[15:8]);
            assign p2_dg[8*gl +: 8] = k[7:0];
        end
    endgenerate
    reg            c1_v, c1_fl, c2_v, c2_fl, c3_v, c3_fl;
    reg [W-1:0]    c1_gt, c1_eq, c2_gt, c2_eq, c3_sel;
    reg [W*EW-1:0] c1_p, c2_p, c3_p;
    reg [W*(LW+1)-1:0] c2_pre;
    reg [LW:0]     c2_cnt;
    reg [KW:0]     rem;
    wire [W*(LW+1)-1:0] eq_inc;
    ot_hdc_v41x_sel_prefix #(.N(W), .OW(LW + 1)) u_eqpre (.x(c1_eq), .y(eq_inc));
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin c1_v <= 1'b0; c1_fl <= 1'b0; c2_v <= 1'b0; c2_fl <= 1'b0; c3_v <= 1'b0; c3_fl <= 1'b0; end
        else begin
            c1_v <= r1_v; c1_fl <= r1_fl; c2_v <= c1_v; c2_fl <= c1_fl; c3_v <= c2_v; c3_fl <= c2_fl;
        end
    end
    integer ll;
    always @(posedge clk) begin
        c1_gt <= c1_gt_d; c1_eq <= c1_eq_d; c1_p <= r1_d;
        c2_gt <= c1_gt; c2_eq <= c1_eq; c2_p <= c1_p;
        c2_pre <= {eq_inc[(LW+1)*(W-1)-1:0], {(LW+1){1'b0}}};
        c2_cnt <= eq_inc[(LW+1)*(W-1) +: LW+1];
        for (ll = 0; ll < W; ll = ll + 1)
            c3_sel[ll] <= c2_gt[ll] || (c2_eq[ll] && (sw_all || ({{(KW-LW){1'b0}}, c2_pre[(LW+1)*ll +: LW+1]} < rem)));
        c3_p <= c2_p;
    end

    // -- histograms --------------------------------------------------------------------------
    wire p2m = (sw_k == K_P2) && (sw_st != SW_IDLE);
    wire sw_start;                                   // a sweep starts on this edge
    wire hc_busy, hf_busy;
    ot_hdc_v41x_sel_hist #(.W(W), .CB(CB)) u_hc (
        .clk(clk), .rst_n(rst_n), .clr(seg_clr), .i_v(i1_v), .i_en(i1_s), .i_dg(hi_digits(i1_k)),
        .gsel(r_cg), .gsum(s_gc), .gbin(s_bc), .busy(hc_busy));
    wire f_clr = seg_clr || r_fclr || (sw_start && p2q);
    ot_hdc_v41x_sel_hist #(.W(W), .CB(CB)) u_hf (
        .clk(clk), .rst_n(rst_n), .clr(f_clr), .i_v(p2m ? r1_v : i1_v), .i_en(p2m ? p2_en : i1_fm),
        .i_dg(p2m ? p2_dg : lo_digits(i1_k)), .gsel(r_fg), .gsum(s_gf), .gbin(s_bf), .busy(hf_busy));
    function automatic [W*8-1:0] hi_digits(input [W*16-1:0] k);
        integer j;
        for (j = 0; j < W; j = j + 1) hi_digits[8*j +: 8] = k[16*j + 8 +: 8];
    endfunction
    function automatic [W*8-1:0] lo_digits(input [W*16-1:0] k);
        integer j;
        for (j = 0; j < W; j = j + 1) lo_digits[8*j +: 8] = k[16*j +: 8];
    endfunction

    // -- packers ------------------------------------------------------------------------------
    wire            pi_v, pi_bv, pi_fl, ps_v, ps_bv, ps_fl;
    wire [W-1:0]    pi_lv, ps_lv;
    wire [W*EW-1:0] pi_line, ps_line;
    ot_hdc_v41x_sel_pack #(.W(W), .PW(EW)) u_pi (
        .clk(clk), .rst_n(rst_n), .i_v(i1_v), .i_fl(i1_fl), .i_sel(i1_s), .i_p(i1_p),
        .o_v(pi_v), .o_lv(pi_lv), .o_line(pi_line), .o_bv(pi_bv), .o_fl(pi_fl));
    ot_hdc_v41x_sel_pack #(.W(W), .PW(EW)) u_ps (
        .clk(clk), .rst_n(rst_n), .i_v(c3_v), .i_fl(c3_fl), .i_sel(c3_sel), .i_p(c3_p),
        .o_v(ps_v), .o_lv(ps_lv), .o_line(ps_line), .o_bv(ps_bv), .o_fl(ps_fl));

    // -- write-back queue and the write port -----------------------------------------------------
    reg [W*EW-1:0] fq [0:DG-1];
    reg [FW-1:0]   fwp, frp;
    reg [FW:0]     fcnt;
    reg            wpend;
    wire discard = sw_rp && (sw_k == K_P2);
    wire f_push  = ps_v && !discard;
    wire ing_wr  = pi_v && !head[AW];
    wire f_pop   = (fcnt != 0) && !ing_wr;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin fwp <= 0; frp <= 0; fcnt <= 0; mem_we <= 1'b0; wpend <= 1'b0; end
        else begin
            if (f_push) fwp <= (fwp == DG - 1) ? {FW{1'b0}} : fwp + 1'b1;
            if (f_pop)  frp <= (frp == DG - 1) ? {FW{1'b0}} : frp + 1'b1;
            fcnt <= fcnt + {{FW{1'b0}}, f_push} - {{FW{1'b0}}, f_pop};
            mem_we <= ing_wr || f_pop;
            wpend <= f_pop;
        end
    end
    always @(posedge clk) begin
        if (f_push) fq[fwp] <= ps_line;
        mem_waddr <= ing_wr ? head[AW-1:0] : w[AW-1:0];
        mem_wdata <= ing_wr ? pi_line : fq[frp];
    end

    // -- sweep engine ------------------------------------------------------------------------------
    reg  [4:0] infl;                                 // memory tokens between issue and the packer's exit
    wire [AW:0] lim = (sw_seg == 2'd0) ? a_end : (sw_seg == 2'd1) ? b_end : head;
    wire have      = rd < lim;
    wire credit    = (sw_k != K_GC) || (({{(4-FW){1'b0}}, fcnt} + infl) < DG);
    wire abort_now = (sw_k == K_GC) && r_stop;
    wire rd_issue  = (sw_st == SW_RD) && !sw_rp && !abort_now && have && credit;
    wire fl_issue  = (sw_st == SW_FL) && credit;
    wire sw_fin    = (sw_st == SW_WB) && (fcnt == 0) && !f_push && !wpend;
    wire gc_go     = (ph == P_ING) && r_ing && !r_stop && !seg_clr && (sw_st == SW_IDLE) &&
                     ((head != y_st) || (r_T != t_last));
    assign sw_start = (sw_st == SW_IDLE) && !seg_clr && (gc_go || (((ph == P_STOP) && (p2q || p3q))));
    // pass requests wait for the sweep engine (P3 may be requested while P2's write-back drains)
    reg p2q, p3q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin p2q <= 1'b0; p3q <= 1'b0; end
        else if (seg_clr) begin p2q <= 1'b0; p3q <= 1'b0; end
        else begin
            if (r_p2) p2q <= 1'b1; else if (sw_start) p2q <= 1'b0;
            if (r_p3) p3q <= 1'b1; else if (sw_start) p3q <= 1'b0;
        end
    end
    // emit
    reg  [AW:0]    e_rd;
    reg  [2:0]     e_infl;
    reg            p2h, dmode, pend_v;
    reg  [AW:0]    dcnt;
    reg  [W*EW-1:0] pend;
    reg            e_go, e_empty;
    reg  [OCW-1:0] ocnt;
    wire em_issue = (ph == P_EM) && e_go && (e_rd < a_end) &&
                    ({{(8-OCW){1'b0}}, ocnt} + {5'd0, e_infl} < OD);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            t1_v <= 1'b0; t1_fl <= 1'b0; t1_em <= 1'b0; mem_re <= 1'b0;
        end else begin
            t1_v <= rd_issue || em_issue; t1_fl <= fl_issue; t1_em <= em_issue;
            mem_re <= rd_issue || em_issue;
        end
    end
    always @(posedge clk) begin
        mem_raddr <= em_issue ? e_rd[AW-1:0] : rd[AW-1:0];
        t1_last <= em_issue && (e_rd + 1'b1 == a_end);
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ph <= P_ING; sw_st <= SW_IDLE; sw_k <= K_GC; sw_seg <= 2'd0; sw_rp <= 1'b0; sw_all <= 1'b1; ab <= 1'b0;
            rd <= 0; w <= 0; a_end <= 0; b_st <= 0; b_end <= 0; y_st <= 0; head <= 0; infl <= 0;
            ovf <= 1'b0; last_seen <= 1'b0; ing_fl_done <= 1'b0; t_last <= 16'h0000;
            e_rd <= 0; e_infl <= 0; e_go <= 1'b0; e_empty <= 1'b0;
            sw_T <= 16'h0000; rem <= 0; ab_seg <= 2'd0; rd_ab <= 0; rd_stop <= 0;
            p2h <= 1'b0; dmode <= 1'b0; pend_v <= 1'b0; dcnt <= 0;
            s_last <= 1'b0; s_hfin <= 1'b0; s_stopped <= 1'b0; s_done2 <= 1'b0; s_ovf <= 1'b0; s_emitted <= 1'b0;
            s_nhead <= 0; s_n2 <= 0; s_n3 <= 0;
        end else if (seg_clr) begin
            ph <= P_ING; sw_st <= SW_IDLE; sw_k <= K_GC; sw_seg <= 2'd0; sw_rp <= 1'b0; sw_all <= 1'b1; ab <= 1'b0;
            rd <= 0; w <= 0; a_end <= 0; b_st <= 0; b_end <= 0; y_st <= 0; head <= 0; infl <= 0;
            ovf <= 1'b0; last_seen <= 1'b0; ing_fl_done <= 1'b0; t_last <= 16'h0000;
            e_rd <= 0; e_infl <= 0; e_go <= 1'b0; e_empty <= 1'b0;
            sw_T <= 16'h0000; rem <= 0; ab_seg <= 2'd0; rd_ab <= 0; rd_stop <= 0;
            p2h <= 1'b0; dmode <= 1'b0; pend_v <= 1'b0; dcnt <= 0;
            s_last <= 1'b0; s_hfin <= 1'b0; s_stopped <= 1'b0; s_done2 <= 1'b0; s_ovf <= 1'b0; s_emitted <= 1'b0;
        end else begin
            // input bookkeeping
            if (sw_start && (p2q || p3q) && r_rep) last_seen <= 1'b0;
            else if (acc && in_last) last_seen <= 1'b1;
            if (pi_fl) ing_fl_done <= 1'b1;
            if (pi_v) begin
                if (head[AW]) ovf <= 1'b1;
                else head <= head + 1'b1;
            end
            if (f_pop) w <= w + 1'b1;
            infl <= infl + {4'd0, rd_issue || fl_issue} - {4'd0, ps_bv && !sw_rp};
            if (ph == P_ING && r_stop) ph <= P_STOP;

            // sweep start
            if (sw_start) begin
                sw_st <= SW_RD; sw_seg <= 2'd0; rd <= 0; w <= 0; ab <= 1'b0;
                if (gc_go) begin
                    sw_k <= K_GC; sw_rp <= 1'b0; sw_all <= 1'b1; t_last <= r_T;
                end else begin
                    sw_k <= p2q ? K_P2 : K_P3; sw_rp <= r_rep; sw_all <= p2q; sw_T <= r_st; rem <= r_rem;
                    ph <= p2q ? P_P2 : P_P3;
                    if (p2q) begin s_n2 <= 0; p2h <= 1'b0; end else begin s_n3 <= 0; dmode <= 1'b1; dcnt <= 0; pend_v <= 1'b0; end
                end
            end
            if (c2_v && !sw_all) rem <= (rem > {{(KW-LW){1'b0}}, c2_cnt}) ? rem - {{(KW-LW){1'b0}}, c2_cnt} : {(KW+1){1'b0}};
            if (rd_issue && sw_k == K_P2) s_n2 <= s_n2 + 1'b1;
            if (rd_issue && sw_k == K_P3) s_n3 <= s_n3 + 1'b1;

            case (sw_st)
                SW_RD: begin
                    if (sw_rp) begin
                        if (acc && in_last) sw_st <= SW_DR;
                    end else if (abort_now) begin
                        ab <= 1'b1; ab_seg <= sw_seg; rd_ab <= rd; sw_st <= SW_FL;
                    end else if (have) begin
                        if (credit) rd <= rd + 1'b1;
                    end else if (sw_seg == 2'd0) begin
                        sw_seg <= 2'd1; rd <= b_st;
                    end else if (sw_seg == 2'd1) begin
                        sw_seg <= 2'd2; rd <= y_st;
                    end else begin
                        rd_stop <= rd; sw_st <= SW_FL;
                    end
                end
                SW_FL: if (credit) sw_st <= SW_DR;
                SW_DR: if (ps_fl) sw_st <= SW_WB;
                SW_WB: if (sw_fin) begin
                    sw_st <= SW_IDLE;
                    case (sw_k)
                        K_GC: begin
                            a_end <= w;
                            if (!ab) begin b_st <= 0; b_end <= 0; y_st <= rd_stop; end
                            else if (ab_seg == 2'd0) begin b_st <= rd_ab; b_end <= a_end; end
                            else if (ab_seg == 2'd1) b_st <= rd_ab;
                            else begin b_st <= 0; b_end <= 0; y_st <= rd_ab; end
                        end
                        K_P2: begin
                            if (!sw_rp) begin a_end <= w; b_st <= 0; b_end <= 0; y_st <= head; end
                            ph <= P_STOP;
                        end
                        default: begin
                            a_end <= w; b_st <= 0; b_end <= 0; y_st <= head;
                            // lines already delivered straight from pass 3 are not read again
                            ph <= P_EM; e_rd <= dcnt; e_go <= !d_fin; e_empty <= (w == 0);
                        end
                    endcase
                end
                default: ;
            endcase

            // pass 2 is done for the control once its last line has been histogrammed
            if (sw_k == K_P2 && sw_st != SW_IDLE && r1_v && r1_fl) p2h <= 1'b1;
            if (p2h && hf_cnt == 0 && !hf_busy && !s_done2) s_done2 <= 1'b1;
            // pass 3 lines go straight to the output FIFO while it has room (one line held back so
            // the last one can carry out_last); from the first line that finds it full, EMIT re-reads
            if (d_push) begin dcnt <= dcnt + 1'b1; end
            if (sw_k == K_P3 && sw_st != SW_IDLE && dmode && f_push) begin
                if (pend_v && !d_room) dmode <= 1'b0;
                else begin pend <= ps_line; pend_v <= 1'b1; end
            end
            if (d_fin_push) begin pend_v <= 1'b0; end
            if (sw_fin && sw_k == K_P3 && dmode && pend_v && !d_room) dmode <= 1'b0;
            // emit
            e_infl <= e_infl + {2'd0, em_issue} - {2'd0, t2_v && t2_em};
            if (em_issue) e_rd <= e_rd + 1'b1;
            if (ph == P_EM && e_go && (e_rd == a_end) && !e_empty) e_go <= 1'b0;
            if (ph == P_EM && e_empty && ocnt < OD) begin e_empty <= 1'b0; e_go <= 1'b0; end
            if (ph == P_EM && out_valid && out_ready && out_last) begin ph <= P_DONE; s_emitted <= 1'b1; end

            // status
            s_last    <= (ph == P_ING) && (last_seen || (acc && in_last));
            s_hfin    <= last_seen && hs_quiet;
            s_stopped <= (ph == P_STOP) && (sw_st == SW_IDLE) && !sw_start && ing_fl_done && hs_quiet && !pi_v;
            s_ovf     <= ovf || (pi_v && head[AW]);
            s_nhead   <= head;
        end
    end
    reg [1:0] hf_cnt;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) hf_cnt <= 2'd3;
        else if (hf_busy || (p2m && r1_v)) hf_cnt <= 2'd3;
        else if (hf_cnt != 0) hf_cnt <= hf_cnt - 1'b1;
    end
    // histogram settle: the group sums are final 3 edges after the last beat left the input stages
    reg [1:0] hs_cnt;
    wire      hs_quiet = (hs_cnt == 0) && !i0_v && !i1_v && !hc_busy && !hf_busy;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) hs_cnt <= 2'd3;
        else if (i0_v || i1_v || hc_busy || hf_busy) hs_cnt <= 2'd3;
        else if (hs_cnt != 0) hs_cnt <= hs_cnt - 1'b1;
    end

    // -- output FIFO (shift register; entry 0 drives the port) ------------------------------------
    reg  [EW*W:0]  ofq [0:OD-1];                    // {last, line}
    // direct delivery from pass 3
    wire           d_room     = (ocnt < OD);
    wire           d_mid      = (sw_k == K_P3) && (sw_st != SW_IDLE) && dmode && f_push && pend_v && d_room;
    wire           d_fin_push = sw_fin && (sw_k == K_P3) && dmode && pend_v && d_room;
    wire           d_fin      = sw_fin && (sw_k == K_P3) && dmode && (pend_v ? d_room : 1'b1) && (w != 0);
    wire           d_push     = d_mid || d_fin_push;
    wire           o_push = (t2_v && t2_em) || (ph == P_EM && e_empty && ocnt < OD) || d_push;
    wire [EW*W:0]  o_in   = (t2_v && t2_em) ? {t2_last, mem_rdata} : d_push ? {d_fin_push, pend} :
                            {1'b1, {W*EW{1'b0}}};
    wire           o_pop  = (ocnt != 0) && out_ready;
    integer oi;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) ocnt <= 0;
        else if (seg_clr) ocnt <= 0;
        else ocnt <= ocnt + {{(OCW-1){1'b0}}, o_push} - {{(OCW-1){1'b0}}, o_pop};
    end
    always @(posedge clk) begin
        for (oi = 0; oi < OD; oi = oi + 1) begin
            if (o_pop) begin
                if (o_push && oi == ocnt - 1) ofq[oi] <= o_in;
                else if (oi + 1 < OD) ofq[oi] <= ofq[(oi + 1) % OD];
            end else if (o_push && oi == ocnt) ofq[oi] <= o_in;
        end
    end
    assign out_valid = (ocnt != 0);
    assign out_last  = ofq[0][EW*W];
    generate
        for (gl = 0; gl < W; gl = gl + 1) begin : g_out
            wire [EW-1:0] ln = ofq[0][EW*gl +: EW];
            assign out_lv[gl]             = ln[EW-1];
            assign out_val[16*gl +: 16]   = ln[IW +: 16];
            assign out_idx[IW*gl +: IW]   = ln[IW-1:0];
            assign out_ninf[gl]           = ln[EW-1] && (ln[IW +: 16] == 16'hFF80);
        end
    endgenerate
endmodule
