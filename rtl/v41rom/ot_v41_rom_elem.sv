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
//   cfg_a = NSEG .. 2NSEG-1  class c:   [0] valid, [8:1] first unit (pair / BF16 lane group), [15:9] units,
//                            [18:16] first segment, [21:19] last segment, [22] BF16 family (NSEG <= 8)
//   cfg_a = 2NSEG            [2:0] sub-blocks - 1 (a class of u units spans ceil(u / 8) sub-blocks)
//   segment [42]             BF16
// ---------------------------------------------------------------------------
module ot_v41_rom_elem #(
    parameter integer NSEG = 8,
    parameter integer NCH = 16,
    parameter integer XF = 4,
    parameter integer LV = 4,
    parameter integer BF16 = 0,       // 1: the 16-lane BF16 path (ot_v41_bf16_lanes) and its x port
    parameter integer NCHB = 8,
    parameter INSTANCE = ""
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         cfg_v,
    input  wire [4:0]   cfg_a,
    input  wire [47:0]  cfg_d,
    input  wire         go,
    input  wire         go_bf,        // the phase's family: 0 = FP8/FP4 (shared FP8 x stream), 1 = BF16
    input  wire         xs_v,
    input  wire [7:0]   xs_p,
    input  wire [2:0]   xs_b,
    input  wire [1:0]   xs_sv,
    input  wire [255:0] xs_q0,
    input  wire [9:0]   xs_e0,
    input  wire [255:0] xs_q1,
    input  wire [9:0]   xs_e1,
    // BF16 x stream beat: 4 lane-group slices {unit, 16 BF16} for block b
    input  wire         xb_v,
    input  wire [2:0]   xb_b,
    input  wire [3:0]   xb_sv,
    input  wire [31:0]  xb_u,
    input  wire [1023:0] xb_d,
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
    reg        s_bf  [0:NSEG-1];
    reg        c_bf  [0:NSEG-1];
    reg        fam;
    reg [12:0] s_base [0:NSEG-1];
    reg        c_v   [0:NSEG-1];
    reg [7:0]  c_u0  [0:NSEG-1];
    reg [6:0]  c_nu  [0:NSEG-1];
    reg [SW-1:0] c_s0 [0:NSEG-1];
    reg [SW-1:0] c_s1 [0:NSEG-1];
    reg [2:0]  qlast;               // sub-blocks - 1
    always @(posedge clk) if (cfg_v) begin
        if ({27'd0, cfg_a} < NSEG) begin
            s_row[cfg_a[SW-1:0]]  <= cfg_d[15:0];
            s_idx[cfg_a[SW-1:0]]  <= cfg_d[20:16];
            s_n[cfg_a[SW-1:0]]    <= cfg_d[25:21];
            s_fp4[cfg_a[SW-1:0]]  <= cfg_d[26];
            s_lo[cfg_a[SW-1:0]]   <= cfg_d[27];
            s_hi[cfg_a[SW-1:0]]   <= cfg_d[28];
            s_base[cfg_a[SW-1:0]] <= cfg_d[41:29];
            s_bf[cfg_a[SW-1:0]]   <= cfg_d[42];
        end else if ({27'd0, cfg_a} < 2 * NSEG) begin
            c_v[cfg_a[SW-1:0]]  <= cfg_d[0];
            c_u0[cfg_a[SW-1:0]] <= cfg_d[8:1];
            c_nu[cfg_a[SW-1:0]] <= cfg_d[15:9];
            c_s0[cfg_a[SW-1:0]] <= cfg_d[16 +: SW];
            c_s1[cfg_a[SW-1:0]] <= cfg_d[19 +: SW];
            c_bf[cfg_a[SW-1:0]] <= cfg_d[22];
        end else begin
            qlast <= cfg_d[2:0];
        end
    end

    // per class: unit count and whether it belongs to the running family, packed for the walkers
    reg [7*NSEG-1:0] nu_p;
    reg [NSEG-1:0] base_live, base_go;
    integer ci;
    always @* begin
        for (ci = 0; ci < NSEG; ci = ci + 1) begin
            nu_p[7*ci +: 7] = c_nu[ci];
            base_live[ci] = c_v[ci] && c_bf[ci] == fam;
            base_go[ci] = c_v[ci] && c_bf[ci] == go_bf;
        end
    end
    localparam integer UW = 1 + 3 + 3 + SW + 3;     // {run, q, b, c, j}
    wire [SW-1:0] c_first;
    wire          c_first_ok;
    ot_v41_first #(.N(NSEG)) u_first (.live(base_go), .c(c_first), .ok(c_first_ok));

    // ---------------- x-need walker: one (pair, b) per class unit per round ------------------------------
    reg        n_run;
    reg [2:0]  n_q;
    reg [2:0]  n_b, n_j;
    reg [SW-1:0] n_c;
    wire [7:0] n_pair = c_u0[n_c] + {2'd0, n_q, n_j};
    wire [UW-1:0] n_nx;
    ot_v41_walk #(.N(NSEG)) u_nw (.q(n_q), .b(n_b), .c(n_c), .j(n_j), .nu(nu_p), .base(base_live),
                                   .qlast(qlast), .nx(n_nx));
    wire hit_q = n_run && !fam && xs_v && xs_p == n_pair && xs_b == n_b;
    // BF16: capture, in slot order, every slice of this round (b) whose unit lies in a live class's sub-block
    reg        bn_run;
    reg [2:0]  bn_q;
    reg [2:0]  bn_b;
    reg [6:0]  bn_cnt, bn_tot;
    reg [3:0]  bm;
    reg [6:0]  q8, rem, nq;
    integer bk, bc;
    always @* begin
        bn_tot = 7'd0;
        q8 = {bn_q, 3'd0};
        for (bc = 0; bc < NSEG; bc = bc + 1) begin
            rem = (c_nu[bc] > q8) ? c_nu[bc] - q8 : 7'd0;
            nq = (rem > 7'd8) ? 7'd8 : rem;
            if (base_live[bc]) bn_tot = bn_tot + nq;
        end
        for (bk = 0; bk < 4; bk = bk + 1) begin
            bm[bk] = 1'b0;
            for (bc = 0; bc < NSEG; bc = bc + 1) begin
                rem = (c_nu[bc] > q8) ? c_nu[bc] - q8 : 7'd0;
                nq = (rem > 7'd8) ? 7'd8 : rem;
                if (base_live[bc] && {1'b0, xb_u[8*bk +: 8]} >= {1'b0, c_u0[bc]} + {2'd0, q8} &&
                    {1'b0, xb_u[8*bk +: 8]} < {1'b0, c_u0[bc]} + {2'd0, q8} + {2'd0, nq})
                    bm[bk] = 1'b1;
            end
            bm[bk] = bm[bk] && (BF16 != 0) && bn_run && fam && xb_v && xb_sv[bk] && xb_b == bn_b;
        end
    end
    wire [2:0] bnum = {2'd0, bm[0]} + {2'd0, bm[1]} + {2'd0, bm[2]} + {2'd0, bm[3]};
    wire hit = hit_q;

    // ---------------- x FIFO (pair slices) ------------------------------------------------------------------
    localparam integer XW = $clog2(XF);
    reg [255:0] f_q0 [0:XF-1];
    reg [9:0]   f_e0 [0:XF-1];
    reg [255:0] f_q1 [0:XF-1];
    reg [9:0]   f_e1 [0:XF-1];
    reg [XW-1:0] f_wr, f_rd;
    reg [XW:0]  f_cnt;
    wire [2:0] npush = hit_q ? 3'd1 : bnum;
    reg [XW-1:0] bpre [0:3];
    always @* begin
        bpre[0] = '0;
        bpre[1] = {{(XW-1){1'b0}}, bm[0]};
        bpre[2] = bpre[1] + {{(XW-1){1'b0}}, bm[1]};
        bpre[3] = bpre[2] + {{(XW-1){1'b0}}, bm[2]};
    end

    // ---------------- word walker -------------------------------------------------------------------------------
    reg        w_run, w_h;
    reg [2:0]  w_q;
    reg [2:0]  w_b, w_j;
    reg [SW-1:0] w_c, w_s;
    reg [HW-1:0] w_cnt;
    reg [12:0] w_ptr [0:NSEG-1];
    wire [6:0] w_uabs = {1'b0, w_q, w_j};
    wire w_firstu = w_uabs == 7'd0;
    wire w_lastu  = w_uabs + 7'd1 == c_nu[w_c];
    wire [1:0] hv = {!(w_lastu && !s_hi[w_s]), !(w_firstu && !s_lo[w_s])};
    wire w_fp4 = s_fp4[w_s];
    wire w_bf = s_bf[w_s];
    wire w_seg_last = w_fp4 || w_bf || w_h || !hv[1];          // the segment's last word for this unit
    wire w_cls_last = w_seg_last && w_s == c_s1[w_c];
    wire [UW-1:0] w_nx;
    ot_v41_walk #(.N(NSEG)) u_ww (.q(w_q), .b(w_b), .c(w_c), .j(w_j), .nu(nu_p), .base(base_live),
                                   .qlast(qlast), .nx(w_nx));
    wire w_round_end = !w_nx[UW-1] || w_nx[UW-5 -: 3] != w_b;
    wire [SW-1:0] w_nx_c = w_nx[3 +: SW];
    wire [SW-1:0] s_next = w_s + 1'b1;
    wire [6:0] nx_uabs = {1'b0, w_nx[UW-2 -: 3], w_nx[2:0]};

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
    wire c0_fault, c1_fault, t_fault, b_fault;

    // an FP8 segment whose first unit lacks the low chunk starts at half 1
    wire [SW-1:0] s0_first = c_s0[c_first];
    wire [SW-1:0] s0_nx = c_s0[w_nx_c];
    wire h_go   = !s_fp4[s0_first] && !s_bf[s0_first] && !s_lo[s0_first];
    wire h_next = !s_fp4[s_next] && !s_bf[s_next] && w_firstu && !s_lo[s_next];
    wire h_nx   = !s_fp4[s0_nx] && !s_bf[s0_nx] && nx_uabs == 7'd0 && !s_lo[s0_nx];

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            n_run <= 1'b0; bn_run <= 1'b0; fam <= 1'b0; w_run <= 1'b0; f_cnt <= 0; f_wr <= 0; f_rd <= 0; hz_v <= 5'd0; fault <= 1'b0;
        end else begin
            hz_v <= {hz_v[3:0], issue};
            if (go) begin
                n_run <= !go_bf; n_q <= 3'd0; n_b <= 3'd0; n_c <= c_first; n_j <= 3'd0;
                bn_run <= go_bf; bn_q <= 3'd0; bn_b <= 3'd0; bn_cnt <= 7'd0; fam <= go_bf;
                w_run <= 1'b1; w_q <= 3'd0; w_b <= 3'd0; w_c <= c_first; w_j <= 3'd0;
                w_s <= s0_first; w_h <= h_go; w_cnt <= 0;
                f_cnt <= 0; f_wr <= 0; f_rd <= 0;
            end else begin
                if (hit) {n_run, n_q, n_b, n_c, n_j} <= n_nx;
                if (issue) begin
                    if (!w_seg_last) begin
                        w_h <= 1'b1;
                        w_cnt <= w_cnt + 1'b1;
                    end else if (w_s != c_s1[w_c]) begin
                        w_s <= s_next;
                        w_h <= h_next;
                        w_cnt <= w_cnt + 1'b1;
                    end else begin
                        {w_run, w_q, w_b, w_c, w_j} <= w_nx;
                        w_s <= s0_nx;
                        w_h <= h_nx;
                        w_cnt <= w_round_end ? {HW{1'b0}} : w_cnt + 1'b1;
                    end
                end
                f_cnt <= f_cnt + npush - (pop ? 1'b1 : 1'b0);
                f_wr <= f_wr + npush[XW-1:0];
                if (bnum != 0) begin
                    if (bn_cnt + {4'd0, bnum} == bn_tot) begin
                        bn_cnt <= 7'd0;
                        if (bn_b == 3'd7 && bn_q == qlast) bn_run <= 1'b0;
                        else begin bn_b <= bn_b + 3'd1; if (bn_b == 3'd7) bn_q <= bn_q + 3'd1; end
                    end else bn_cnt <= bn_cnt + {4'd0, bnum};
                end
                if (pop) f_rd <= f_rd + 1'b1;
                if ({1'b0, f_cnt} + {2'b0, npush} > XF + (pop ? 1 : 0) || c0_fault || c1_fault || t_fault || b_fault)
                    fault <= 1'b1;
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
        for (bk = 0; bk < 4; bk = bk + 1)
            if (bm[bk]) f_q0[f_wr + bpre[bk]] <= xb_d[256*bk +: 256];
        hz_s[0] <= w_cnt;
        for (k = 1; k < 5; k = k + 1) hz_s[k] <= hz_s[k-1];
    end

    // ---------------- ROM, capture at the pins, x alignment ------------------------------------------------
    wire [273:0] rd;
    ot_rom_8192x274_m8
`ifndef SYNTHESIS
        #(.INSTANCE(INSTANCE))
`endif
        u_rom (.clk(clk), .ce_in(issue), .addr_in(w_ptr[w_s]), .rd_out(rd));
    reg [273:0] cap;
    reg         i1_v, i2_v;
    reg [255:0] i1_q0, i1_q1, i2_q0, i2_q1;
    reg [9:0]   i1_e0, i1_e1, i2_e0, i2_e1;
    localparam integer TW = HW + SW + 6;   // {slot, tree, first, last, final, ok0, ok1, fp4}
    reg [TW-1:0] i1_t, i2_t;
    reg i1_bf, i2_bf;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin i1_v <= 1'b0; i2_v <= 1'b0; end
        else begin i1_v <= issue; i2_v <= i1_v; end
    end
    // FP8 word of half h uses slice h on lane 0; FP4 uses slice 0 on lane 0 and slice 1 on lane 1
    wire use_hi = !w_fp4 && !w_bf && w_h;
    always @(posedge clk) begin
        i1_q0 <= use_hi ? f_q1[f_rd] : f_q0[f_rd];
        i1_e0 <= use_hi ? f_e1[f_rd] : f_e0[f_rd];
        i1_q1 <= f_q1[f_rd]; i1_e1 <= f_e1[f_rd];
        i1_t <= {w_cnt, w_s, w_b == 3'd0, w_b == 3'd7, w_b == 3'd7 && w_lastu && w_seg_last,
                 !w_bf && (w_fp4 ? hv[0] : 1'b1), !w_bf && w_fp4 && hv[1], w_fp4};
        i1_bf <= w_bf;
        i2_bf <= i1_bf;
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
    wire        q_v = pr_vp[4];
    wire [31:0] q_val = pr_t[1] ? pr_sum : pr_pass;
    wire        q_err = pr_t[0] | (pr_t[1] && pr_err != 2'd0);

    // ---------------- optional BF16 lanes -------------------------------------------------------------------
    wire bf_v, bf_err, bf_final;
    wire [31:0] bf_val;
    wire [SW-1:0] bf_tree;
    generate if (BF16 != 0) begin : g_bf
        ot_v41_bf16_lanes #(.NCHB(NCHB), .TRW(SW)) u_bf (.clk(clk), .rst_n(rst_n), .v(i2_v && i2_bf),
            .w(cap[255:0]), .x(i2_q0), .slot(i2_t[TW-HW +: $clog2(NCHB)]), .first(i2_t[5]), .last(i2_t[4]),
            .tree(i2_t[TW-HW-1 -: SW]), .final_i(i2_t[3]), .ov(bf_v), .oval(bf_val), .otree(bf_tree),
            .ofinal(bf_final), .oerr(bf_err), .fault(b_fault));
    end else begin : g_nobf
        assign bf_v = 1'b0; assign bf_val = 32'd0; assign bf_tree = '0; assign bf_final = 1'b0;
        assign bf_err = 1'b0; assign b_fault = 1'b0;
    end endgenerate
    wire        b_v = q_v | bf_v;
    wire [31:0] b_val = bf_v ? bf_val : q_val;
    wire        b_err = bf_v ? bf_err : q_err;
    wire [SW-1:0] b_tree = bf_v ? bf_tree : pr_t[SW+2:3];
    wire        b_final = bf_v ? bf_final : pr_t[2];

    // ---------------- segment tree -> partial ---------------------------------------------------------------------
    wire t_v, t_err;
    wire [SW-1:0] t_tree;
    wire [31:0] t_val;
    ot_v41_segtree #(.NT(NSEG), .LV(LV)) u_tree (.clk(clk), .rst_n(rst_n), .in_v(b_v),
        .in_tree(b_tree), .in_val(b_val), .in_final(b_final), .in_err(b_err),
        .ov(t_v), .otree(t_tree), .oval(t_val), .oerr(t_err), .fault(t_fault));
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) pv <= 1'b0;
        else pv <= t_v;
    end
    always @(posedge clk) begin
        pval <= t_val; prow <= s_row[t_tree]; pseg <= s_idx[t_tree]; pnseg <= s_n[t_tree]; perr <= t_err;
    end
    assign busy = w_run | i1_v | i2_v;
    // slot field of the tag is HW bits; BF16 chains use its low log2(NCHB) bits (words per round <= NCHB)
endmodule

// first live class
module ot_v41_first #(parameter integer N = 4) (
    input  wire [N-1:0] live,
    output reg  [$clog2(N)-1:0] c,
    output reg  ok
);
    integer k;
    always @* begin
        c = '0; ok = 1'b0;
        for (k = N - 1; k >= 0; k = k - 1) if (live[k]) begin c = k[$clog2(N)-1:0]; ok = 1'b1; end
    end
endmodule

// next (q, b, class, unit) of the element's round walk: next unit of the class, else the next live class of
// the sub-block, else the next round (b, then sub-block q), else done (run = 0).  A class of nu units has
// min(8, nu - 8q) units in sub-block q.
module ot_v41_walk #(parameter integer N = 4) (
    input  wire [2:0] q,
    input  wire [2:0] b,
    input  wire [$clog2(N)-1:0] c,
    input  wire [2:0] j,
    input  wire [7*N-1:0] nu,
    input  wire [N-1:0] base,
    input  wire [2:0] qlast,
    output reg  [1+3+3+$clog2(N)+3-1:0] nx
);
    localparam integer SW = $clog2(N);
    reg [SW-1:0] nc, fc;
    reg nf, ff;
    reg [2:0] nq;
    reg [6:0] rem, q8, nq8;
    reg [3:0] cur;
    reg [N-1:0] live, livn;
    integer k;
    always @* begin
        q8 = {1'b0, q, 3'd0};
        nq = (b == 3'd7) ? q + 3'd1 : q;
        nq8 = {1'b0, nq, 3'd0};
        cur = 4'd0;
        for (k = 0; k < N; k = k + 1) begin
            rem = (nu[7*k +: 7] > q8) ? nu[7*k +: 7] - q8 : 7'd0;
            live[k] = base[k] && rem != 7'd0;
            if (k == c) cur = (rem > 7'd8) ? 4'd8 : rem[3:0];
            livn[k] = base[k] && nu[7*k +: 7] > nq8;
        end
        nf = 1'b0; nc = '0;
        for (k = N - 1; k >= 0; k = k - 1) if (live[k] && k > c) begin nc = k[SW-1:0]; nf = 1'b1; end
        ff = 1'b0; fc = '0;
        for (k = N - 1; k >= 0; k = k - 1) if (livn[k]) begin fc = k[SW-1:0]; ff = 1'b1; end
        if ({1'b0, j} + 4'd1 < cur)              nx = {1'b1, q, b, c, j + 3'd1};
        else if (nf)                             nx = {1'b1, q, b, nc, 3'd0};
        else if (b == 3'd7 && q == qlast)        nx = '0;
        else                                     nx = {1'b1, nq, b + 3'd1, fc, 3'd0};
    end
endmodule
