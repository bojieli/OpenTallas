`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// The hierarchical SM element's block-dot column (rtl/hbm_accel/sm/ot_hbm_accel_smh.sv tile, flat in the tile):
// ot_hbm_accel_bd_col on ot_hbm_accel_bterm3, the block term re-cut to ~700 ps stages for the tile context, where
// ot_hbm_accel_bterm2's stages missed SS by up to 356 ps (post-CTS classes of the 2026-10-05 tile route:
// P3 -> P4a 42-bit add -356, P5 -> P6 round carry + exponent -242, P1 -> P2 shift + CSA -147, P0 -> P1 -114,
// P7 -> P8 -86, P2 -> P3 -78, P4a -> P4 -72, P4 -> P5a -69).  Bit-identical to ot_hbm_accel_bterm2 (the same exact
// integer dot, the same normalise and the same two roundings, only cut into more registers); LATENCY 18 (was 11),
// so the column's input -> chunk-sum latency grows by 7 cycles; the issue's BF16-minus-block-dot latency figure (DBF)
// drops by 7 accordingly.  ot_hbm_accel_bd_col.sv is pinned and stays byte-identical.
// ---------------------------------------------------------------------------
module ot_hbm_accel_smh_bd_col #(
    parameter integer LB   = 2,         // defaults = the hardened macro (V4.1 SM: 2 lanes, 16-bit tag)
    parameter integer IL   = 8,
    parameter integer TAGW = 16
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              v,
    input  wire              first,
    input  wire              last,
    input  wire              fp4,
    input  wire [TAGW-1:0]   tag,
    input  wire [LB*256-1:0] wq,
    input  wire [LB*10-1:0]  we,
    input  wire [LB*256-1:0] xq,
    input  wire [LB*10-1:0]  xe,
    output wire              ov,
    output wire [31:0]       y,
    output wire [TAGW-1:0]   otag,
    output wire              fault
);
    // 1.2 GHz at SS: the block term is W10's ot_v41_bterm2 (ot_hdc_blockdot's P0..P8 re-cut, bit-identical,
    // LATENCY 11), accumulated per golden chunk on an IL-slot circulating ring around the LAT-7 FP32 adder
    // (ot_gpu_fadd): the term of slot s arrives BT cycles after its issue, so the ring runs BT cycles late and
    // keeps the slot rotation; a bubble adds +0 (the slot's sum holds, bit for bit).
    localparam integer BT = 18;            // ot_hbm_accel_bterm3 LATENCY
    localparam integer ALAT = 7;
    localparam integer FB = IL - ALAT;
    wire [LB-1:0] tv_l, tf_l;
    wire [LB*32-1:0] term;
    genvar l;
    generate for (l = 0; l < LB; l = l + 1) begin : g_bt
        ot_hbm_accel_bterm3 u_bt (.clk(clk), .rst_n(rst_n), .v(v), .fp4(fp4),
            .xq(xq[256*l +: 256]), .xe(xe[10*l +: 10]), .wq(wq[256*l +: 256]), .we(we[10*l +: 10]),
            .tag(1'b0), .ov(tv_l[l]), .y(term[32*l +: 32]), .f(tf_l[l]), .otag());
    end endgenerate
    // first / last / tag aligned with the terms
    wire [BT:0] fl_d, ll_d;
    ot_hdc_vline #(.D(BT)) u_fd (.clk(clk), .rst_n(rst_n), .v(v && first), .vd(fl_d));
    ot_hdc_vline #(.D(BT)) u_ld (.clk(clk), .rst_n(rst_n), .v(v && last), .vd(ll_d));
    wire [TAGW-1:0] tag_t;
    ot_hdc_delay #(.W(TAGW), .D(BT)) u_tt (.clk(clk), .rst_n(rst_n), .d(tag), .q(tag_t));
    // ring: acc register (1) + adder (ALAT) + feedback delay (FB - 1) = IL
    reg  [LB*32-1:0] tm_q;
    reg              first_q, last_q, tv_q;
    reg  [TAGW-1:0]  tag_q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin first_q <= 1'b0; last_q <= 1'b0; tv_q <= 1'b0; end
        else begin first_q <= fl_d[BT]; last_q <= ll_d[BT]; tv_q <= tv_l[0]; end
    end
    integer k;
    always @(posedge clk) begin
        tag_q <= tag_t;
        for (k = 0; k < LB; k = k + 1) tm_q[32*k +: 32] <= tv_l[k] ? term[32*k +: 32] : 32'd0;
    end
    wire [LB*32-1:0] acc;
    wire [LB-1:0] af;
    generate for (l = 0; l < LB; l = l + 1) begin : g_ring
        wire [31:0] sum, fb_pre;
        reg  [31:0] acc_q;
        always @(posedge clk) acc_q <= first_q ? 32'd0 : fb_pre;
        reg [31:0] tm_d;
        always @(posedge clk) tm_d <= tm_q[32*l +: 32];
        ot_gpu_fadd #(.LAT(ALAT)) u_add (.clk(clk), .rst_n(rst_n), .v(1'b1), .a(acc_q), .b(tm_d), .y(sum), .fault(af[l]));
        ot_hdc_delay #(.W(32), .D(FB - 1)) u_fb (.clk(clk), .rst_n(rst_n), .d(sum), .q(fb_pre));
        assign acc[32*l +: 32] = sum;
    end endgenerate
    // the chunk's final sum leaves the adder 1 + ALAT cycles after its last term is registered
    // (margin m1) and is registered once more in front of the tree (+1: acc_r)
    localparam integer LS = 1 + ALAT + 1;
    reg [LB*32-1:0] acc_r;
    always @(posedge clk) acc_r <= acc;
    wire [LS:0] lo;
    ot_hdc_vline #(.D(LS)) u_lo (.clk(clk), .rst_n(rst_n), .v(last_q), .vd(lo));
    wire [TAGW-1:0] tag_d;
    ot_hdc_delay #(.W(TAGW), .D(LS)) u_td (.clk(clk), .rst_n(rst_n), .d(tag_q), .q(tag_d));
    wire [LB-1:0] lov = {LB{lo[LS]}};
    reg sticky;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) sticky <= 1'b0;
        else sticky <= sticky | (|(tf_l & tv_l)) | (|af);
    wire tf, t_ov;
    wire [31:0] t_y;
    wire [TAGW-1:0] t_tag;
    ot_gpu_tree #(.N(LB), .TAGW(TAGW), .ALAT(7)) u_tree (.clk(clk), .rst_n(rst_n), .v(lov[0]), .d(acc_r), .tag(tag_d),
                                              .ov(t_ov), .y(t_y), .otag(t_tag), .fault(tf));
    // output registers: the hardened macro's outputs leave flops
    reg ov_q, fault_q;
    reg [31:0] y_q;
    reg [TAGW-1:0] otag_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin ov_q <= 1'b0; fault_q <= 1'b0; end
        else begin ov_q <= t_ov; fault_q <= sticky | tf; end
    always @(posedge clk) begin y_q <= t_y; otag_q <= t_tag; end
    assign ov = ov_q;
    assign y = y_q;
    assign otag = otag_q;
    assign fault = fault_q;
endmodule

`timescale 1ns/1ps
// ot_hbm_accel_bterm2: ot_v41_bterm2 (rtl/v41rom/ot_v41_bterm2.sv) with the FP4 weight decode (E2M1 -> E4M3) moved

// ot_hbm_accel_bterm3: ot_hbm_accel_bterm2 cut into 18 stages:
// (round 5: every add / increment is a kept ot_hdc_ksadd_k prefix adder; the tile's post-CTS classes showed ABC
// re-rippling the plain forms: P4a -> P4b -132, P5 -> P6a -93, P3 -> P4a1 -57, P7 -> P8a -55 ps)
//   P0 in | P1a decode | P1b products | P2a shift + CSA 32->22 | P2b CSA 22->7 | P3 CSA 7->2 | P4a1 low-half add |
//   P4a2 high-half add | P4b1 negation prefix | P4b2 sign-magnitude | P5a normalise 32/16 | P5b 8/4 | P5c 2/1 |
//   P6a round increment, exponent - lz | P6b carry into exponent | P7 scale / subnormal shift | P8a subnormal round |
//   P8b pack.
// The carry-save reduction is exact mod 2^42 in any 3:2 order, so the pair's sum equals bterm2's.
module ot_hbm_accel_bterm3 (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              v,
    input  wire              fp4,
    input  wire [255:0]      xq,
    input  wire signed [9:0] xe,
    input  wire [255:0]      wq,
    input  wire signed [9:0] we,
    input  wire              tag,
    output wire              ov,
    output wire [31:0]       y,
    output wire              f,
    output wire              otag
);
    localparam integer W = 42;
    localparam integer LAT = 18;
    function automatic [7:0] e2m1(input [3:0] c);
        if (c[2:1] == 2'd0) e2m1 = {c[3], c[0] ? 4'd6 : 4'd0, 3'd0};
        else                e2m1 = {c[3], {2'b00, c[2:1]} + 4'd6, c[0], 2'b00};
    endfunction
    integer i, j;
    // valid pipe (reset), one bit per stage
    reg [LAT-1:0] vp;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) vp <= {LAT{1'b0}};
        else vp <= {vp[LAT-2:0], v};
    assign ov = vp[LAT-1];
    ot_hdc_delay #(.W(1), .D(LAT)) u_tag (.clk(clk), .rst_n(rst_n), .d(tag), .q(otag));

    // -- P0: input register (the E2M1 -> E4M3 decode of the weights, as bterm2) -------------------
    reg [255:0]      p0_xq, p0_wq;
    reg signed [9:0] p0_xe, p0_we;
    always @(posedge clk) begin
        p0_xq <= xq; p0_xe <= xe; p0_we <= we;
        for (i = 0; i < 32; i = i + 1) p0_wq[8*i +: 8] <= fp4 ? e2m1(wq[8*i +: 4]) : wq[8*i +: 8];
    end

    // -- P1a: per-element decode: significands, sign, shift amount, NaN per group of 8 ----------------
    reg [3:0]  q_xs [0:31];
    reg [3:0]  q_ws [0:31];
    reg [31:0] q_sg;
    reg [4:0]  q_sh [0:31];
    reg [3:0]  q_nan;
    reg signed [10:0] q_es;
    reg [7:0]  xc, wc;
    reg [3:0]  xf, wf;
    reg        nn;
    always @(posedge clk) begin
        q_es <= p0_xe + p0_we;
        for (i = 0; i < 32; i = i + 1) begin
            xc = p0_xq[8*i +: 8];
            wc = p0_wq[8*i +: 8];
            q_xs[i] <= {(xc[6:3] != 4'd0), xc[2:0]};
            q_ws[i] <= {(wc[6:3] != 4'd0), wc[2:0]};
            q_sg[i] <= xc[7] ^ wc[7];
            xf = (xc[6:3] == 4'd0) ? 4'd1 : xc[6:3];
            wf = (wc[6:3] == 4'd0) ? 4'd1 : wc[6:3];
            q_sh[i] <= {1'b0, xf} + {1'b0, wf} - 5'd2;
        end
        for (i = 0; i < 4; i = i + 1) begin
            nn = 1'b0;
            for (j = 0; j < 8; j = j + 1)
                nn = nn | (p0_xq[8*(8*i+j) +: 7] == 7'h7F) | (p0_wq[8*(8*i+j) +: 7] == 7'h7F);
            q_nan[i] <= nn;
        end
    end

    // -- P1b: signed 4x4 products ------------------------------------------------------------------------
    reg signed [8:0]  p1_p [0:31];
    reg [4:0]         p1_sh [0:31];
    reg               p1_nan;
    reg signed [10:0] p1_es;
    reg [7:0]         pm;
    always @(posedge clk) begin
        p1_es <= q_es; p1_nan <= |q_nan;
        for (i = 0; i < 32; i = i + 1) begin
            pm = q_xs[i] * q_ws[i];
            p1_p[i] <= q_sg[i] ? -$signed({1'b0, pm}) : $signed({1'b0, pm});
            p1_sh[i] <= q_sh[i];
        end
    end

    // -- P2a: terms (units of 2^-18) and one 3:2 level (32 -> 22) --------------------------------------
    reg [32*W-1:0] terms;
    always @(*) begin
        for (i = 0; i < 32; i = i + 1)
            terms[W*i +: W] = {{(W-9){p1_p[i][8]}}, p1_p[i]} << p1_sh[i];
    end
    wire [22*W-1:0] c22;
    ot_v41_csa #(.N(32), .M(22), .W(W)) u_csa1 (.d(terms), .q(c22));
    reg [22*W-1:0]    p2a_c;
    reg               p2a_nan;
    reg signed [10:0] p2a_es;
    always @(posedge clk) begin p2a_c <= c22; p2a_nan <= p1_nan; p2a_es <= p1_es; end
    // -- P2b: CSA 22 -> 7 -------------------------------------------------------------------------------
    wire [7*W-1:0] c7;
    ot_v41_csa #(.N(22), .M(7), .W(W)) u_csa2 (.d(p2a_c), .q(c7));
    reg [7*W-1:0]     p2_c;
    reg               p2_nan;
    reg signed [10:0] p2_es;
    always @(posedge clk) begin p2_c <= c7; p2_nan <= p2a_nan; p2_es <= p2a_es; end
    // -- P3: CSA 7 -> 2 ---------------------------------------------------------------------------------
    wire [2*W-1:0] c2;
    ot_v41_csa #(.N(7), .M(2), .W(W)) u_csa3 (.d(p2_c), .q(c2));
    reg [W-1:0]       p3_a, p3_b;
    reg               p3_nan;
    reg signed [10:0] p3_es;
    always @(posedge clk) begin p3_a <= c2[W-1:0]; p3_b <= c2[2*W-1:W]; p3_nan <= p2_nan; p3_es <= p2_es; end

    // -- P4a1 / P4a2: the pair's sum, low 21 bits then high 21 bits with the carry -----------------------
    localparam integer HL = W / 2;
    reg [HL-1:0]      s_lo;
    reg               s_c;
    reg [W-HL-1:0]    h_a, h_b;
    reg               p4a1_nan;
    reg signed [10:0] p4a1_es;
    // every add / increment below is ot_hdc_ksadd_k ((* keep *) Kogge-Stone: ABC cannot re-ripple it in the tile)
    wire [HL-1:0] lo_s; wire lo_c;
    ot_hdc_ksadd_k #(.W(HL)) u_lo (.a(p3_a[HL-1:0]), .b(p3_b[HL-1:0]), .cin(1'b0), .s(lo_s), .cout(lo_c));
    always @(posedge clk) begin
        {s_c, s_lo} <= {lo_c, lo_s};
        h_a <= p3_a[W-1:HL]; h_b <= p3_b[W-1:HL];
        p4a1_nan <= p3_nan; p4a1_es <= p3_es;
    end
    reg [W-1:0]       p4a_s;
    reg               p4a_nan;
    reg signed [10:0] p4a_es;
    wire [W-HL-1:0] hi_s;
    ot_hdc_ksadd_k #(.W(W-HL)) u_hi (.a(h_a), .b(h_b), .cin(s_c), .s(hi_s), .cout());
    always @(posedge clk) begin
        p4a_s <= {hi_s, s_lo};
        p4a_nan <= p4a1_nan; p4a_es <= p4a1_es;
    end
    // -- P4b1: the negation -(s) = ~s + 1 (prefix adder), registered ---------------------------------------
    wire [W-1:0] ngw;
    ot_hdc_ksadd_k #(.W(W)) u_ng (.a(~p4a_s), .b({W{1'b0}}), .cin(1'b1), .s(ngw), .cout());
    reg [W-1:0]       p4b_s, p4b_n;
    reg               p4b_nan;
    reg signed [10:0] p4b_es;
    always @(posedge clk) begin p4b_s <= p4a_s; p4b_n <= ngw; p4b_nan <= p4a_nan; p4b_es <= p4a_es; end
    // -- P4b2: sign-magnitude --------------------------------------------------------------------------
    wire [W-1:0] ng = p4b_n;
    reg               p4_nan, p4_s;
    reg signed [11:0] p4_eb;
    reg [W-2:0]       p4_m;
    always @(posedge clk) begin
        p4_nan <= p4b_nan;
        p4_eb <= p4b_es + 12'sd149;           // biased exponent of the leading bit at position 40
        p4_s <= p4b_s[W-1];
        p4_m <= p4b_s[W-1] ? ng[W-2:0] : p4b_s[W-2:0];
    end

    // -- P5a: normalise 32 / 16 ----------------------------------------------------------------------------
    reg [40:0] na; reg [5:0] la;
    always @(*) begin
        na = p4_m; la = 6'd0;
        if (na[40:9]  == 32'd0) begin na = na << 32; la = la + 6'd32; end
        if (na[40:25] == 16'd0) begin na = na << 16; la = la + 6'd16; end
    end
    reg               p5a_nan, p5a_s, p5a_z;
    reg signed [11:0] p5a_eb;
    reg [40:0]        p5a_nm;
    reg [5:0]         p5a_lz;
    always @(posedge clk) begin
        p5a_nan <= p4_nan; p5a_s <= p4_s; p5a_z <= (p4_m == 41'd0);
        p5a_eb <= p4_eb; p5a_nm <= na; p5a_lz <= la;
    end
    // -- P5b: normalise 8 / 4 --------------------------------------------------------------------------------
    reg [40:0] nb; reg [5:0] lb;
    always @(*) begin
        nb = p5a_nm; lb = p5a_lz;
        if (nb[40:33] == 8'd0)  begin nb = nb << 8;  lb = lb + 6'd8;  end
        if (nb[40:37] == 4'd0)  begin nb = nb << 4;  lb = lb + 6'd4;  end
    end
    reg               p5b_nan, p5b_s, p5b_z;
    reg signed [11:0] p5b_eb;
    reg [40:0]        p5b_nm;
    reg [5:0]         p5b_lz;
    always @(posedge clk) begin
        p5b_nan <= p5a_nan; p5b_s <= p5a_s; p5b_z <= p5a_z;
        p5b_eb <= p5a_eb; p5b_nm <= nb; p5b_lz <= lb;
    end
    // -- P5c: normalise 2 / 1 --------------------------------------------------------------------------------
    reg [40:0] nc; reg [5:0] lc;
    always @(*) begin
        nc = p5b_nm; lc = p5b_lz;
        if (nc[40:39] == 2'd0)  begin nc = nc << 2;  lc = lc + 6'd2;  end
        if (nc[40] == 1'b0)     begin nc = nc << 1;  lc = lc + 6'd1;  end
    end
    reg               p5_nan, p5_s, p5_z;
    reg signed [11:0] p5_eb;
    reg [40:0]        p5_nm;
    reg [5:0]         p5_lz;
    always @(posedge clk) begin
        p5_nan <= p5b_nan; p5_s <= p5b_s; p5_z <= p5b_z;
        p5_eb <= p5b_eb; p5_nm <= nc; p5_lz <= lc;
    end

    // -- P6a: round to 24 bits (parallel-prefix increment), exponent minus the leading-zero count ----------
    wire [23:0] m24 = p5_nm[40:17];
    wire        inc = p5_nm[16] & ((p5_nm[15:0] != 16'd0) | m24[0]);
    wire [23:0] mr_s; wire mr_c;
    ot_hdc_ksadd_k #(.W(24)) u_r6 (.a(m24), .b(24'd0), .cin(inc), .s(mr_s), .cout(mr_c));
    wire [24:0] mr = {mr_c, mr_s};                                 // m24 + inc
    reg               p6a_nan, p6a_s, p6a_z;
    reg signed [11:0] p6a_el;
    reg [24:0]        p6a_mr;
    always @(posedge clk) begin
        p6a_nan <= p5_nan; p6a_s <= p5_s; p6a_z <= p5_z;
        p6a_el <= p5_eb - $signed({6'd0, p5_lz});
        p6a_mr <= mr;
    end
    // -- P6b: the rounding carry into the exponent -------------------------------------------------------------
    reg               p6_nan, p6_s, p6_z;
    reg signed [11:0] p6_b;
    reg [22:0]        p6_f;
    always @(posedge clk) begin
        p6_nan <= p6a_nan; p6_s <= p6a_s; p6_z <= p6a_z;
        p6_b <= p6a_el + $signed({11'd0, p6a_mr[24]});
        p6_f <= p6a_mr[24] ? 23'd0 : p6a_mr[22:0];
    end

    // -- P7: scale: subnormal right shift ------------------------------------------------------------------
    wire [11:0] rsh = 12'd1 - p6_b;
    wire [4:0]  rs5 = (p6_b < -12'sd24) ? 5'd26 : rsh[4:0];
    wire [49:0] sw = {1'b1, p6_f, 26'd0} >> rs5;
    reg               p7_nan, p7_sub, p7_ovf, p7_s;
    reg [31:0]        p7_n;
    reg [23:0]        p7_t;
    reg               p7_g, p7_st;
    always @(posedge clk) begin
        p7_nan <= p6_nan; p7_s <= p6_s;
        p7_sub <= !p6_z && (p6_b < 12'sd1);
        p7_ovf <= !p6_z && (p6_b > 12'sd254);
        if (p6_z)                  p7_n <= 32'd0;
        else if (p6_b > 12'sd254)  p7_n <= {p6_s, 8'hFF, 23'd0};
        else                       p7_n <= {p6_s, p6_b[7:0], p6_f};
        p7_t <= sw[49:26];
        p7_g <= sw[25];
        p7_st <= (sw[24:0] != 25'd0);
    end
    // -- P8a: subnormal round (parallel-prefix increment) ------------------------------------------------------
    wire        inc8 = p7_g & (p7_st | p7_t[0]);
    wire [23:0] tr8;
    ot_hdc_ksadd_k #(.W(24)) u_r8 (.a(p7_t), .b(24'd0), .cin(inc8), .s(tr8), .cout());
    reg        p8a_f, p8a_sub, p8a_s;
    reg [31:0] p8a_n;
    reg [23:0] p8a_tr;
    always @(posedge clk) begin
        p8a_f <= p7_nan | p7_ovf; p8a_sub <= p7_sub; p8a_s <= p7_s; p8a_n <= p7_n;
        p8a_tr <= tr8;
    end
    // -- P8b: pack (a subnormal that rounds up to 2^-126 carries into the exponent field) ------------------------
    reg        p8_f;
    reg [31:0] p8_y;
    always @(posedge clk) begin
        p8_f <= p8a_f;
        p8_y <= p8a_sub ? {p8a_s, 7'd0, p8a_tr} : p8a_n;
    end
    assign y = p8_y;
    assign f = p8_f;
endmodule

// ---------------------------------------------------------------------------
// The hierarchical SM element's BF16 column (flat in the tile): ot_hbm_accel_tc_col (rtl/hbm_accel/sm/ot_hbm_accel_tc16.sv,
// pinned, byte-identical) with three registers added for the tile context (post-CTS classes of the 2026-10-05 tile
// route: x_q -> multiplier decode -90 ps, 8x4 partial products -97 ps, lane sum -> combine tree -64 ps):
//   * a per-lane second input register (the shared input register no longer drives every lane's decode);
//   * ot_hbm_accel_smh_bmul: the 8x8 significand product in two stages (four 8x2 partials, then the two 8x4 sums);
//   * each lane's sum registered in front of the combine tree.
// Bit-identical (the same products, the same ring, the same tree); latency +3 cycles (input -> column result).
// ---------------------------------------------------------------------------
module ot_hbm_accel_smh_tc_col #(
    parameter integer L    = 16,
    parameter integer IL   = 8,
    parameter integer TAGW = 16,
    parameter integer ALAT = 7          // adder latency: the IL-slot ring needs ALAT <= IL - 1
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire            v,
    input  wire            first,
    input  wire            last,
    input  wire [TAGW-1:0] tag,
    input  wire [L*16-1:0] w,
    input  wire [L*16-1:0] x,
    output wire            ov,
    output wire [31:0]     y,
    output wire [TAGW-1:0] otag,
    output wire            fault
);
    localparam integer FB = IL - ALAT;          // ring = acc register + adder + (FB - 1) delay = IL
    localparam integer ML = 7;                  // ot_hbm_accel_smh_bmul latency (margin m1: 6 -> 7)
    reg            v_q, first_q, last_q, v_q2, first_q2, last_q2;
    reg [L-1:0]    v_ql;
    reg [TAGW-1:0] tag_q, tag_q2;
    reg [L*16-1:0] w_q, x_q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            v_q <= 1'b0; first_q <= 1'b0; last_q <= 1'b0; v_q2 <= 1'b0; first_q2 <= 1'b0; last_q2 <= 1'b0;
            v_ql <= {L{1'b0}};
        end else begin
            v_q <= v; first_q <= v && first; last_q <= v && last;
            v_q2 <= v_q; first_q2 <= first_q; last_q2 <= last_q; v_ql <= {L{v_q}};
        end
    end
    always @(posedge clk) begin
        w_q <= w;
        x_q <= x;
        tag_q <= tag; tag_q2 <= tag_q;
    end
    wire [ML:0] fl;
    ot_hdc_vline #(.D(ML)) u_f (.clk(clk), .rst_n(rst_n), .v(first_q2), .vd(fl));
    // chunk end: the lane's final sum leaves the adder ML (mul) + ALAT (add) cycles after the second input register,
    // and its register one cycle later
    localparam integer LL = ML + ALAT + 2;      // (margin m1) + the second lane-sum register (sum_q2)
    wire [LL:0] ll;
    ot_hdc_vline #(.D(LL)) u_l (.clk(clk), .rst_n(rst_n), .v(last_q2), .vd(ll));
    wire [TAGW-1:0] tag_d;
    ot_hdc_delay #(.W(TAGW), .D(LL)) u_t (.clk(clk), .rst_n(rst_n), .d(tag_q2), .q(tag_d));
    wire [ML:0] vl;
    ot_hdc_vline #(.D(ML)) u_v (.clk(clk), .rst_n(rst_n), .v(v_q2), .vd(vl));
    wire [L*32-1:0] sum;
    reg  [L*32-1:0] sum_q, sum_q2;
    always @(posedge clk) sum_q2 <= sum_q;      // (margin m1) the lane sums cross the tile to the tree: two registers
    wire [L-1:0] lf;
    genvar l;
    generate for (l = 0; l < L; l = l + 1) begin : g_lane
        wire [31:0] prod, fb_pre;
        reg  [31:0] acc_q;
        reg  [15:0] w_l, x_l;
        wire f0, f1;
        always @(posedge clk) begin w_l <= w_q[16*l +: 16]; x_l <= x_q[16*l +: 16]; end
        // a bubble multiplies by +0: the slot's sum holds
        ot_hbm_accel_smh_bmul u_mul (.clk(clk), .rst_n(rst_n), .v(v_q2), .kill(!v_ql[l]), .a({w_l, 16'd0}),
                                     .b({x_l, 16'd0}), .y(prod), .fault(f0));
        always @(posedge clk) acc_q <= fl[ML-1] ? 32'd0 : fb_pre;
        ot_gpu_fadd #(.LAT(ALAT)) u_add (.clk(clk), .rst_n(rst_n), .v(vl[ML]), .a(acc_q), .b(prod), .y(sum[32*l +: 32]), .fault(f1));
        ot_hdc_delay #(.W(32), .D(FB - 1)) u_fb (.clk(clk), .rst_n(rst_n), .d(sum[32*l +: 32]), .q(fb_pre));
        always @(posedge clk) sum_q[32*l +: 32] <= sum[32*l +: 32];
        assign lf[l] = f0 | f1;
    end endgenerate
    wire tf, t_ov;
    wire [31:0] t_y;
    wire [TAGW-1:0] t_tag;
    ot_gpu_tree #(.N(L), .TAGW(TAGW), .ALAT(ALAT)) u_tree (.clk(clk), .rst_n(rst_n), .v(ll[LL]), .d(sum_q2), .tag(tag_d),
                                             .ov(t_ov), .y(t_y), .otag(t_tag), .fault(tf));
    reg lane_fault, ov_q, fault_q;
    reg [31:0] y_q;
    reg [TAGW-1:0] otag_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin lane_fault <= 1'b0; ov_q <= 1'b0; fault_q <= 1'b0; end
        else begin
            lane_fault <= lane_fault | (|lf);
            ov_q <= t_ov;
            fault_q <= lane_fault | tf;
        end
    always @(posedge clk) begin y_q <= t_y; otag_q <= t_tag; end
    assign ov = ov_q;
    assign y = y_q;
    assign otag = otag_q;
    assign fault = fault_q;
endmodule

// ot_hbm_accel_bmul with the 8x8 significand product in two stages (8x2 partials, then the 8x4 sums) and the encode
// decision registered ahead of the select (margin m1): LATENCY 7.
module ot_hbm_accel_smh_bmul (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire        kill,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output reg         fault
);
    function automatic [17:0] dec;   // {sig[7:0], E[9:0] signed}
        input [7:0] e;
        input [6:0] m;
        integer i;
        reg [2:0] p;
        begin
            if (e != 0) dec = {1'b1, m, e - 10'sd127};
            else begin
                p = 0;
                for (i = 0; i < 7; i = i + 1) if (m[i]) p = i[2:0];
                dec = {({1'b0, m} << (7 - p)), $signed(-10'sd133) + $signed({7'd0, p})};
            end
        end
    endfunction
    wire [17:0] da = dec(a[30:23], a[22:16]);
    wire [17:0] db = dec(b[30:23], b[22:16]);
    // stage 1: decode
    reg        s1_v, s1_s, s1_z, s1_nf;
    reg [7:0]  s1_a, s1_b;
    reg signed [10:0] s1_e;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s1_v <= 1'b0;
        else s1_v <= v;
    end
    always @(posedge clk) begin
        s1_s <= a[31] ^ b[31];
        s1_z <= kill || (a[30:16] == 15'd0) || (b[30:16] == 15'd0);
        s1_nf <= (a[30:23] == 8'hFF) || (b[30:23] == 8'hFF);
        s1_a <= da[17:10]; s1_b <= db[17:10];
        s1_e <= $signed(da[9:0]) + $signed(db[9:0]);
    end
    // stage 2a: four 8x2 partial products
    reg        t_v, t_s, t_z, t_nf;
    reg [9:0]  t_q0, t_q1, t_q2, t_q3;
    reg signed [10:0] t_e8, t_e7;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) t_v <= 1'b0;
        else t_v <= s1_v;
    end
    always @(posedge clk) begin
        t_s <= s1_s; t_z <= s1_z; t_nf <= s1_nf;
        t_e8 <= s1_e + 11'sd128; t_e7 <= s1_e + 11'sd127;
        t_q0 <= s1_a * s1_b[1:0]; t_q1 <= s1_a * s1_b[3:2];
        t_q2 <= s1_a * s1_b[5:4]; t_q3 <= s1_a * s1_b[7:6];
    end
    // stage 2b: the two 8x4 products
    reg        s2_v, s2_s, s2_z, s2_nf;
    reg [11:0] s2_pl, s2_ph;
    reg signed [10:0] s2_e8, s2_e7;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s2_v <= 1'b0;
        else s2_v <= t_v;
    end
    always @(posedge clk) begin
        s2_s <= t_s; s2_z <= t_z; s2_nf <= t_nf; s2_e8 <= t_e8; s2_e7 <= t_e7;
        s2_pl <= {2'd0, t_q0} + {t_q1, 2'd0};
        s2_ph <= {2'd0, t_q2} + {t_q3, 2'd0};
    end
    // stage 3: normalise (leading bit 15 or 14) and bias
    wire [15:0] s2_p;
    wire        s2_pc;
    ot_hdc_ksadd_k #(.W(16)) u_psum (.a({4'd0, s2_pl}), .b({s2_ph, 4'd0}), .cin(1'b0), .s(s2_p), .cout(s2_pc));
    reg        s3_v, s3_s, s3_z, s3_nf;
    reg [22:0] s3_f;
    reg signed [10:0] s3_be;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s3_v <= 1'b0;
        else s3_v <= s2_v;
    end
    always @(posedge clk) begin
        s3_s <= s2_s; s3_z <= s2_z; s3_nf <= s2_nf;
        if (s2_p[15]) begin s3_f <= {s2_p[14:0], 8'd0}; s3_be <= s2_e8; end
        else          begin s3_f <= {s2_p[13:0], 9'd0}; s3_be <= s2_e7; end
    end
    // stage 3b (margin m1, +1): the encode decision and both candidate words registered; stage 4 only selects
    reg        t3_v, t3_zero, t3_bad, t3_norm;
    reg [31:0] t3_n, t3_sub;
    wire [23:0] sig24 = {1'b1, s3_f};
    wire [3:0]  sub_sh = 4'd1 - s3_be[3:0];
    wire [23:0] sub_v = sig24 >> sub_sh;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) t3_v <= 1'b0;
        else t3_v <= s3_v;
    end
    always @(posedge clk) begin
        t3_zero <= s3_z && !s3_nf;
        t3_bad  <= s3_nf || s3_be > 11'sd254 || s3_be < -11'sd6;
        t3_norm <= s3_be >= 11'sd1;
        t3_n    <= {s3_s, s3_be[7:0], s3_f};
        t3_sub  <= {s3_s, 8'd0, sub_v[22:0]};
    end
    // stage 4: encode (select)
    reg        s4_v, s4_bad;
    reg [31:0] s4_y;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s4_v <= 1'b0;
        else s4_v <= t3_v;
    end
    always @(posedge clk) begin
        s4_bad <= 1'b0;
        if (t3_zero) s4_y <= 32'd0;
        else if (t3_bad) begin s4_y <= 32'd0; s4_bad <= 1'b1; end
        else if (t3_norm) s4_y <= t3_n;
        else s4_y <= t3_sub;
    end
    // stage 5: output register
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin y <= 32'd0; fault <= 1'b0; end
        else begin y <= s4_y; fault <= s4_v && s4_bad; end
    end
endmodule
