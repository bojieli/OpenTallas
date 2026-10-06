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
    localparam integer LS = 1 + ALAT;
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
    ot_gpu_tree #(.N(LB), .TAGW(TAGW), .ALAT(7)) u_tree (.clk(clk), .rst_n(rst_n), .v(lov[0]), .d(acc), .tag(tag_d),
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
    always @(posedge clk) begin
        {s_c, s_lo} <= {1'b0, p3_a[HL-1:0]} + {1'b0, p3_b[HL-1:0]};
        h_a <= p3_a[W-1:HL]; h_b <= p3_b[W-1:HL];
        p4a1_nan <= p3_nan; p4a1_es <= p3_es;
    end
    reg [W-1:0]       p4a_s;
    reg               p4a_nan;
    reg signed [10:0] p4a_es;
    always @(posedge clk) begin
        p4a_s <= {h_a + h_b + {{(W-HL-1){1'b0}}, s_c}, s_lo};
        p4a_nan <= p4a1_nan; p4a_es <= p4a1_es;
    end
    // -- P4b1: the negation's prefix (-(s) = ~s + 1: ones4[i] = s[i-1:0] all zero) ---------------------
    reg  [W-1:0] ones4;
    always @* begin
        ones4[0] = 1'b1;
        for (i = 1; i < W; i = i + 1) ones4[i] = &(~p4a_s | ~(({{(W-1){1'b0}}, 1'b1} << i) - {{(W-1){1'b0}}, 1'b1}));
    end
    reg [W-1:0]       p4b_s, p4b_o;
    reg               p4b_nan;
    reg signed [10:0] p4b_es;
    always @(posedge clk) begin p4b_s <= p4a_s; p4b_o <= ones4; p4b_nan <= p4a_nan; p4b_es <= p4a_es; end
    // -- P4b2: sign-magnitude --------------------------------------------------------------------------
    wire [W-1:0] ng = ~p4b_s ^ p4b_o;
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
    reg  [24:0] ones6;
    always @* begin
        ones6[0] = 1'b1;
        for (i = 1; i < 25; i = i + 1) ones6[i] = &({1'b0, m24} | ~((25'd1 << i) - 25'd1));
    end
    wire [24:0] mr = {1'b0, m24} ^ ({25{inc}} & ones6);          // m24 + inc
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
    reg  [23:0] ones8;
    always @* begin
        ones8[0] = 1'b1;
        for (i = 1; i < 24; i = i + 1) ones8[i] = &(p7_t | ~((24'd1 << i) - 24'd1));
    end
    reg        p8a_f, p8a_sub, p8a_s;
    reg [31:0] p8a_n;
    reg [23:0] p8a_tr;
    always @(posedge clk) begin
        p8a_f <= p7_nan | p7_ovf; p8a_sub <= p7_sub; p8a_s <= p7_s; p8a_n <= p7_n;
        p8a_tr <= p7_t ^ ({24{inc8}} & ones8);
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
