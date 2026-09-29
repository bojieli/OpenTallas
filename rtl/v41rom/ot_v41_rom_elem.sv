`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_v41_rom_elem: the V4.1 ROM-array element (docs/MICROARCH_MODEL.md build item 1; W10).
//
//   one ot_rom_8192x274_m8 macro + a 274-bit capture register at its pins
//   + 2 exact block-dot lanes (FP4: one 32-block each = 64 MACs/cycle; FP8: lane 0 = 32 MACs/cycle)
//   + per lane an NCH-slot golden chunk chain on one pipelined binary32 adder
//   + one pair adder (FP4 sibling chunks) + an NSEG-tree golden segment tree (LV levels)
//   -> one FP32 partial per K segment, tagged {row, segment, segments in the row}.
//
// Arithmetic: golden linear_q under R-ARITH chunk8 (tools/hdc_golden_v41.py): every 32-block dot is
// exact, rounded once to binary32 and scaled by 2^(xe + we) (ot_v41_bterm); each chunk of 8 blocks is
// summed sequentially from +0; chunk sums combine by the padded pairwise tree.  A segment is a
// power-of-two-aligned run of chunks, so its partial is a node of the row's golden tree; the array's
// return network finishes the tree (ot_v41_ret_node / ot_v41_ret_root).
//
// Units and words (tools/v41_rom_ksplit_bankmap.py): the x unit is a chunk PAIR (2p, 2p+1).  Word b of a
// unit holds block b: FP4 = {chunk 2p+1 (high 136 bits) | chunk 2p (low)}, two lanes; FP8 = one word per
// chunk of the pair that the segment covers (half h), lane 0.  Each segment's words are contiguous at its
// base in its read order: sub-block q (8 units), b, unit, half.
// Issue order (element_order): q, b, class (segments sharing one unit range; a macro's classes are
// disjoint) in ascending unit, unit, the class's segments, half.  One captured x slice (pair p, block b)
// serves every word of a (class, unit, b).  Each chain (word position in the round) is revisited once per
// round; rounds are >= 5 cycles by the stream schedule and an issue-side check stalls a re-visit that
// would come sooner than the adder's 5-cycle recurrence.
//
// X stream beat: {pair p, block b, slot valids, codes and exponents of chunk 2p (slot 0) and 2p+1 (1)};
// FP8 and FP4 share it.  The element captures the slices it needs, in stream order, into an XF-entry FIFO.
//
// Configuration (cfg_v, cfg_a, cfg_d[47:0]), loaded before `go`:
//   cfg_a = 0 .. NSEG-1      segment s: [15:0] row, [20:16] segment index, [25:21] segments in row, [26] fp4,
//                            [27] low half of its first unit present, [28] high half of its last unit
//                            present, [41:29] base address
//   cfg_a = NSEG .. 2NSEG-1  class c:   [0] valid, [8:1] first unit (pair), [13:9] units, [15:14] first
//                            segment, [17:16] last segment
//   cfg_a = 2NSEG            [0] some class spans two sub-blocks (> 8 units)
// ---------------------------------------------------------------------------
module ot_v41_rom_elem #(
    parameter integer NSEG = 4,
    parameter integer NCH = 16,
    parameter integer XF = 4,
    parameter integer LV = 4,
    parameter INSTANCE = ""
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         cfg_v,
    input  wire [3:0]   cfg_a,
    input  wire [47:0]  cfg_d,
    input  wire         go,
    input  wire         xs_v,
    input  wire [7:0]   xs_p,
    input  wire [2:0]   xs_b,
    input  wire [1:0]   xs_sv,
    input  wire [255:0] xs_q0,
    input  wire [9:0]   xs_e0,
    input  wire [255:0] xs_q1,
    input  wire [9:0]   xs_e1,
    output reg          pv,
    output reg  [31:0]  pval,
    output reg  [15:0]  prow,
    output reg  [4:0]   pseg,
    output reg  [4:0]   pnseg,
    output reg          perr,
    output wire         busy,
    output reg          fault
);
    localparam integer SW = $clog2(NSEG);
    localparam integer HW = $clog2(NCH);

    // ---------------- configuration ----------------------------------------------------------------
    reg [15:0] s_row [0:NSEG-1];
    reg [4:0]  s_idx [0:NSEG-1];
    reg [4:0]  s_n   [0:NSEG-1];
    reg        s_fp4 [0:NSEG-1];
    reg        s_lo  [0:NSEG-1];
    reg        s_hi  [0:NSEG-1];
    reg [12:0] s_base [0:NSEG-1];
    reg        c_v   [0:NSEG-1];
    reg [7:0]  c_u0  [0:NSEG-1];
    reg [4:0]  c_nu  [0:NSEG-1];
    reg [SW-1:0] c_s0 [0:NSEG-1];
    reg [SW-1:0] c_s1 [0:NSEG-1];
    reg        two_q;
    always @(posedge clk) if (cfg_v) begin
        if ({28'd0, cfg_a} < NSEG) begin
            s_row[cfg_a[SW-1:0]]  <= cfg_d[15:0];
            s_idx[cfg_a[SW-1:0]]  <= cfg_d[20:16];
            s_n[cfg_a[SW-1:0]]    <= cfg_d[25:21];
            s_fp4[cfg_a[SW-1:0]]  <= cfg_d[26];
            s_lo[cfg_a[SW-1:0]]   <= cfg_d[27];
            s_hi[cfg_a[SW-1:0]]   <= cfg_d[28];
            s_base[cfg_a[SW-1:0]] <= cfg_d[41:29];
        end else if ({28'd0, cfg_a} < 2 * NSEG) begin
            c_v[cfg_a[SW-1:0]]  <= cfg_d[0];
            c_u0[cfg_a[SW-1:0]] <= cfg_d[8:1];
            c_nu[cfg_a[SW-1:0]] <= cfg_d[13:9];
            c_s0[cfg_a[SW-1:0]] <= cfg_d[14 +: SW];
            c_s1[cfg_a[SW-1:0]] <= cfg_d[16 +: SW];
        end else begin
            two_q <= cfg_d[0];
        end
    end

    // units of class c in sub-block q
    function automatic [3:0] nun(input [4:0] nu, input q);
        reg [5:0] r;
        begin
            r = {1'b0, nu} - (q ? 6'd8 : 6'd0);
            nun = (nu <= (q ? 5'd8 : 5'd0)) ? 4'd0 : ((r > 6'd8) ? 4'd8 : r[3:0]);
        end
    endfunction
    // first class >= from with units in sub-block q: {found, class}
    function automatic [SW:0] next_cls(input integer from, input q);
        integer c;
        reg f;
        begin
            next_cls = '0;
            f = 1'b0;
            for (c = 0; c < NSEG; c = c + 1)
                if (!f && c >= from && c_v[c] && nun(c_nu[c], q) != 4'd0) begin
                    next_cls = {1'b1, c[SW-1:0]};
                    f = 1'b1;
                end
        end
    endfunction
    localparam integer UW = 1 + 1 + 3 + SW + 3;     // {run, q, b, c, j}
    function automatic [UW-1:0] adv(input q, input [2:0] b, input [SW-1:0] c, input [2:0] j);
        reg [SW:0] nc;
        reg nq;
        begin
            if ({1'b0, j} + 4'd1 < nun(c_nu[c], q))
                adv = {1'b1, q, b, c, j + 3'd1};
            else begin
                nc = next_cls({{(32-SW){1'b0}}, c} + 32'd1, q);
                if (nc[SW])
                    adv = {1'b1, q, b, nc[SW-1:0], 3'd0};
                else if (b == 3'd7 && (q || !two_q))
                    adv = '0;
                else begin
                    nq = (b == 3'd7) ? 1'b1 : q;
                    nc = next_cls(0, nq);
                    adv = {1'b1, nq, b + 3'd1, nc[SW-1:0], 3'd0};
                end
            end
        end
    endfunction
    wire [SW:0] c_first_f = next_cls(0, 1'b0);
    wire [SW-1:0] c_first = c_first_f[SW-1:0];

    // ---------------- x-need walker: one (pair, b) per class unit per round ------------------------------
    reg        n_run, n_q;
    reg [2:0]  n_b, n_j;
    reg [SW-1:0] n_c;
    wire [7:0] n_pair = c_u0[n_c] + {4'd0, n_q, n_j};
    wire [UW-1:0] n_nx = adv(n_q, n_b, n_c, n_j);
    wire hit = n_run && xs_v && xs_p == n_pair && xs_b == n_b;

    // ---------------- x FIFO (pair slices) ------------------------------------------------------------------
    localparam integer XW = $clog2(XF);
    reg [255:0] f_q0 [0:XF-1];
    reg [9:0]   f_e0 [0:XF-1];
    reg [255:0] f_q1 [0:XF-1];
    reg [9:0]   f_e1 [0:XF-1];
    reg [XW-1:0] f_wr, f_rd;
    reg [XW:0]  f_cnt;

    // ---------------- word walker -------------------------------------------------------------------------------
    reg        w_run, w_q, w_h;
    reg [2:0]  w_b, w_j;
    reg [SW-1:0] w_c, w_s;
    reg [HW-1:0] w_cnt;
    reg [12:0] w_ptr [0:NSEG-1];
    wire [4:0] w_uabs = {1'b0, w_q, w_j};
    wire w_firstu = w_uabs == 5'd0;
    wire w_lastu  = w_uabs + 5'd1 == c_nu[w_c];
    wire [1:0] hv = {!(w_lastu && !s_hi[w_s]), !(w_firstu && !s_lo[w_s])};
    wire w_fp4 = s_fp4[w_s];
    wire w_seg_last = w_fp4 || w_h || !hv[1];          // the segment's last word for this unit
    wire w_cls_last = w_seg_last && w_s == c_s1[w_c];
    wire [UW-1:0] w_nx = adv(w_q, w_b, w_c, w_j);
    wire w_round_end = !w_nx[UW-1] || w_nx[UW-3 -: 3] != w_b;
    wire [SW-1:0] w_nx_c = w_nx[3 +: SW];
    wire [SW-1:0] s_next = w_s + 1'b1;
    wire [4:0] nx_uabs = {1'b0, w_nx[UW-2], w_nx[2:0]};

    reg [4:0] hz_v;
    reg [HW-1:0] hz_s [0:4];
    reg hazard;
    integer k;
    always @* begin
        hazard = 1'b0;
        for (k = 0; k < 5; k = k + 1) if (hz_v[k] && hz_s[k] == w_cnt) hazard = 1'b1;
    end
    wire issue = w_run && f_cnt != 0 && !hazard;
    wire pop = issue && w_cls_last;
    wire c0_fault, c1_fault;

    // an FP8 segment whose first unit lacks the low chunk starts at half 1
    function automatic first_h(input [SW-1:0] s, input fu);
        first_h = !s_fp4[s] && fu && !s_lo[s];
    endfunction

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            n_run <= 1'b0; w_run <= 1'b0; f_cnt <= 0; f_wr <= 0; f_rd <= 0; hz_v <= 5'd0; fault <= 1'b0;
        end else begin
            hz_v <= {hz_v[3:0], issue};
            if (go) begin
                n_run <= 1'b1; n_q <= 1'b0; n_b <= 3'd0; n_c <= c_first; n_j <= 3'd0;
                w_run <= 1'b1; w_q <= 1'b0; w_b <= 3'd0; w_c <= c_first; w_j <= 3'd0;
                w_s <= c_s0[c_first]; w_h <= first_h(c_s0[c_first], 1'b1); w_cnt <= 0;
                f_cnt <= 0; f_wr <= 0; f_rd <= 0;
            end else begin
                if (hit) {n_run, n_q, n_b, n_c, n_j} <= n_nx;
                if (issue) begin
                    if (!w_seg_last) begin
                        w_h <= 1'b1;
                        w_cnt <= w_cnt + 1'b1;
                    end else if (w_s != c_s1[w_c]) begin
                        w_s <= s_next;
                        w_h <= first_h(s_next, w_firstu);
                        w_cnt <= w_cnt + 1'b1;
                    end else begin
                        {w_run, w_q, w_b, w_c, w_j} <= w_nx;
                        w_s <= c_s0[w_nx_c];
                        w_h <= first_h(c_s0[w_nx_c], nx_uabs == 5'd0);
                        w_cnt <= w_round_end ? {HW{1'b0}} : w_cnt + 1'b1;
                    end
                end
                f_cnt <= f_cnt + (hit ? 1'b1 : 1'b0) - (pop ? 1'b1 : 1'b0);
                if (hit) f_wr <= f_wr + 1'b1;
                if (pop) f_rd <= f_rd + 1'b1;
                if ((hit && !pop && f_cnt == XF) || c0_fault || c1_fault) fault <= 1'b1;
            end
        end
    end
    integer si;
    always @(posedge clk) begin
        if (go) for (si = 0; si < NSEG; si = si + 1) w_ptr[si] <= s_base[si];
        else if (issue) w_ptr[w_s] <= w_ptr[w_s] + 13'd1;
        if (hit) begin
            f_q0[f_wr] <= xs_q0; f_e0[f_wr] <= xs_e0; f_q1[f_wr] <= xs_q1; f_e1[f_wr] <= xs_e1;
        end
        hz_s[0] <= w_cnt;
        for (k = 1; k < 5; k = k + 1) hz_s[k] <= hz_s[k-1];
    end

    // ---------------- ROM, capture at the pins, x alignment ------------------------------------------------
    wire [273:0] rd;
    ot_rom_8192x274_m8 #(.INSTANCE(INSTANCE)) u_rom (.clk(clk), .ce_in(issue), .addr_in(w_ptr[w_s]), .rd_out(rd));
    reg [273:0] cap;
    reg         i1_v, i2_v;
    reg [255:0] i1_q0, i1_q1, i2_q0, i2_q1;
    reg [9:0]   i1_e0, i1_e1, i2_e0, i2_e1;
    localparam integer TW = HW + SW + 6;   // {slot, tree, first, last, final, ok0, ok1, fp4}
    reg [TW-1:0] i1_t, i2_t;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin i1_v <= 1'b0; i2_v <= 1'b0; end
        else begin i1_v <= issue; i2_v <= i1_v; end
    end
    // FP8 word of half h uses slice h on lane 0; FP4 uses slice 0 on lane 0 and slice 1 on lane 1
    wire use_hi = !w_fp4 && w_h;
    always @(posedge clk) begin
        i1_q0 <= use_hi ? f_q1[f_rd] : f_q0[f_rd];
        i1_e0 <= use_hi ? f_e1[f_rd] : f_e0[f_rd];
        i1_q1 <= f_q1[f_rd]; i1_e1 <= f_e1[f_rd];
        i1_t <= {w_cnt, w_s, w_b == 3'd0, w_b == 3'd7, w_b == 3'd7 && w_lastu && w_seg_last,
                 w_fp4 ? hv[0] : 1'b1, w_fp4 && hv[1], w_fp4};
        cap <= rd;
        i2_q0 <= i1_q0; i2_e0 <= i1_e0; i2_q1 <= i1_q1; i2_e1 <= i1_e1; i2_t <= i1_t;
    end
    wire t_fp4 = i2_t[0];
    function automatic [255:0] nib(input [127:0] c);
        integer i;
        begin
            nib = 256'd0;
            for (i = 0; i < 32; i = i + 1) nib[8*i +: 4] = c[4*i +: 4];
        end
    endfunction
    wire [255:0] w0q = t_fp4 ? nib(cap[127:0]) : cap[255:0];
    wire [7:0]   w0e = t_fp4 ? cap[135:128] : cap[263:256];
    wire [255:0] w1q = nib(cap[263:136]);
    wire [7:0]   w1e = cap[271:264];
    wire signed [9:0] we0 = $signed({2'b00, w0e}) - 10'sd127;
    wire signed [9:0] we1 = $signed({2'b00, w1e}) - 10'sd127;

    // ---------------- lanes --------------------------------------------------------------------------------------
    wire l0_v, l1_v, l0_f, l1_f;
    wire [31:0] l0_y, l1_y;
    wire [TW-1:0] l0_t, l1_t;
    ot_v41_bterm #(.TW(TW)) u_l0 (.clk(clk), .rst_n(rst_n), .v(i2_v && i2_t[2]), .fp4(t_fp4),
        .xq(i2_q0), .xe(i2_e0), .wq(w0q), .we(we0), .tag(i2_t), .ov(l0_v), .y(l0_y), .f(l0_f), .otag(l0_t));
    ot_v41_bterm #(.TW(TW)) u_l1 (.clk(clk), .rst_n(rst_n), .v(i2_v && i2_t[1]), .fp4(1'b1),
        .xq(i2_q1), .xe(i2_e1), .wq(w1q), .we(we1), .tag(i2_t), .ov(l1_v), .y(l1_y), .f(l1_f), .otag(l1_t));
    wire c0_v, c1_v, c0_f, c1_f;
    wire [31:0] c0_s, c1_s;
    wire [SW:0] c0_t, c1_t;   // {tree, final}
    ot_v41_chain #(.NCH(NCH), .TW(SW + 1)) u_c0 (.clk(clk), .rst_n(rst_n), .v(l0_v),
        .slot(l0_t[TW-1 -: HW]), .first(l0_t[5]), .last(l0_t[4]), .term(l0_y), .term_f(l0_f),
        .tag({l0_t[TW-HW-1 -: SW], l0_t[3]}), .ov(c0_v), .osum(c0_s), .of(c0_f), .otag(c0_t), .fault(c0_fault));
    ot_v41_chain #(.NCH(NCH), .TW(SW + 1)) u_c1 (.clk(clk), .rst_n(rst_n), .v(l1_v),
        .slot(l1_t[TW-1 -: HW]), .first(l1_t[5]), .last(l1_t[4]), .term(l1_y), .term_f(l1_f),
        .tag({l1_t[TW-HW-1 -: SW], l1_t[3]}), .ov(c1_v), .osum(c1_s), .of(c1_f), .otag(c1_t), .fault(c1_fault));

    // ---------------- sibling-chunk pair (FP4): chunk 2p + chunk 2p+1, or the one present ------------------
    wire both = c0_v && c1_v;
    wire any = c0_v || c1_v;
    wire [SW:0] ct = c0_v ? c0_t : c1_t;
    wire [31:0] one = c0_v ? c0_s : c1_s;
    wire one_f = c0_v ? c0_f : c1_f;
    wire [31:0] pr_sum, pr_pass;
    wire [1:0] pr_err;
    wire pr_vo;
    ot_fp32_add_rne_pipe u_pair (.clk(clk), .rst_n(rst_n), .valid_in(both), .a(c0_s), .b(c1_s),
        .y(pr_sum), .err(pr_err), .valid_out(pr_vo));
    ot_hdc_delay #(.W(32), .D(5)) u_pp (.clk(clk), .rst_n(rst_n), .d(one), .q(pr_pass));
    wire [SW+2:0] pr_t;   // {tree, final, both, err}
    ot_hdc_delay #(.W(SW + 3), .D(5)) u_pt (.clk(clk), .rst_n(rst_n),
        .d({ct, both, both ? (c0_f | c1_f) : one_f}), .q(pr_t));
    reg [4:0] pr_vp;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) pr_vp <= 5'd0; else pr_vp <= {pr_vp[3:0], any};
    wire        b_v = pr_vp[4];
    wire [31:0] b_val = pr_t[1] ? pr_sum : pr_pass;
    wire        b_err = pr_t[0] | (pr_t[1] && pr_err != 2'd0);

    // ---------------- segment tree -> partial ---------------------------------------------------------------------
    wire t_v, t_err;
    wire [SW-1:0] t_tree;
    wire [31:0] t_val;
    ot_v41_segtree #(.NT(NSEG), .LV(LV)) u_tree (.clk(clk), .rst_n(rst_n), .in_v(b_v),
        .in_tree(pr_t[SW+2:3]), .in_val(b_val), .in_final(pr_t[2]), .in_err(b_err),
        .ov(t_v), .otree(t_tree), .oval(t_val), .oerr(t_err));
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) pv <= 1'b0;
        else pv <= t_v;
    end
    always @(posedge clk) begin
        pval <= t_val; prow <= s_row[t_tree]; pseg <= s_idx[t_tree]; pnseg <= s_n[t_tree]; perr <= t_err;
    end
    assign busy = w_run | i1_v | i2_v;
endmodule
