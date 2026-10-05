`timescale 1ns/1ps
// ot_hbm_accel_bd_col: ot_gpu_bd_col (rtl/gpu/ot_gpu_bd_col.sv) on ot_hbm_accel_bterm2 (FP4 decode in the input
// register), the DS HBM SM's 1.2 GHz block-dot column macro.  Bit-identical, zero added cycles.  Original follows.
// ---------------------------------------------------------------------------
// One column of the V4.1 SM's block-dot tensor core (GPU-organised HBM
// comparator).  LB block-dot lanes (rtl/hdc/v41/ot_hdc_blockdot.sv, legacy
// sequential mode) share the weight line: each lane takes one 32-wide K
// block per cycle -- 32 E4M3, or E2M1 in the low nibble of each byte when
// `fp4` -- with its block exponent, and this column's activation block (32
// E4M3 codes and the block's scale exponent).  A lane forms the block dot
// EXACTLY (42-bit integer), rounds it once to binary32 and scales it by
// 2^(xe + we): the golden linear_q block term, i.e. a k32 FP8/FP4 MMA step.
// Its circulating FP32 accumulator adds the terms of one golden chunk (8
// blocks) in order from +0 across IL = 8 slots; at the chunk's last block the
// LB chunk sums enter the fixed pairwise tree together (the bottom log2(LB)
// levels of csum's tree).  Lane l holds chunk (group * LB + l).
// Latency: input -> chunk sum 15 cycles (block-dot P0..P8 + adder + output).
// ---------------------------------------------------------------------------
module ot_hbm_accel_bd_col #(
    parameter integer M1   = 10,        // ot_hbm_accel_bterm2 P2/P3 CSA cut (10: 3 + 5 levels; 7: original 4 + 4)
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
    localparam integer BT = 11;
    localparam integer ALAT = 7;
    localparam integer FB = IL - ALAT;
    wire [LB-1:0] tv_l, tf_l;
    wire [LB*32-1:0] term;
    genvar l;
    generate for (l = 0; l < LB; l = l + 1) begin : g_bt
        ot_hbm_accel_bterm2 #(.TW(1), .M1(M1)) u_bt (.clk(clk), .rst_n(rst_n), .v(v), .fp4(fp4),
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
// into the P0 input register, for the DS HBM SM's block-dot column at 1.2 GHz SS (M2-M6 leaf macro).  In the original
// the registered fp4 flag fans out to all 32 weight decoders of P1, a buffer tree in front of the products; here P1
// sees the decoded codes.  Bit-identical, LATENCY unchanged (11), zero added cycles.  Original header follows.
// ---------------------------------------------------------------------------
// ot_v41_bterm2: ot_v41_bterm re-cut for 1.2 GHz at SS (W10, 0.833 ns): the 42-bit sum and its negation
// split (P4a / P4b, the negation as a parallel-prefix increment), the 41-bit normalise split (P5a coarse
// 32/16/8, P5b fine 4/2/1), and the two roundings as parallel-prefix increments (yosys otherwise maps an
// increment as a ripple of ORs).  Arithmetic bit-identical to ot_v41_bterm; LATENCY = 11 (was 9).
// ---------------------------------------------------------------------------
module ot_hbm_accel_bterm2 #(
    parameter integer TW = 8,
    parameter integer M1 = 7        // P2's CSA output count: 7 = ot_v41_bterm2's cut (32 -> 7 | 7 -> 2);
                                    // 10 moves one 3:2 level from P2 (behind the term shift) to P3
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              v,
    input  wire              fp4,
    input  wire [255:0]      xq,
    input  wire signed [9:0] xe,
    input  wire [255:0]      wq,
    input  wire signed [9:0] we,
    input  wire [TW-1:0]     tag,
    output wire              ov,
    output wire [31:0]       y,
    output wire              f,
    output wire [TW-1:0]     otag
);
    localparam integer W = 42;
    wire first = 1'b0, last = 1'b0;
    function automatic [7:0] e2m1(input [3:0] c);
        if (c[2:1] == 2'd0) e2m1 = {c[3], c[0] ? 4'd6 : 4'd0, 3'd0};
        else                e2m1 = {c[3], {2'b00, c[2:1]} + 4'd6, c[0], 2'b00};
    endfunction


    integer i;

    // -- P0: input register -----------------------------------------------------------
    reg              p0_v, p0_first, p0_last;
    reg [255:0]      p0_xq, p0_wq;     // p0_wq: the weight codes already decoded (E2M1 -> E4M3 when fp4)
    reg signed [9:0] p0_xe, p0_we;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) p0_v <= 1'b0;
        else p0_v <= v;
    end
    always @(posedge clk) begin
        p0_first <= first; p0_last <= last;
        p0_xq <= xq; p0_xe <= xe; p0_we <= we;
        for (i = 0; i < 32; i = i + 1) p0_wq[8*i +: 8] <= fp4 ? e2m1(wq[8*i +: 4]) : wq[8*i +: 8];
    end

    // -- P1: decode, signed 4x4 products, shift amounts -----------------------------------
    reg               p1_v, p1_first, p1_last, p1_nan;
    reg signed [10:0] p1_es;
    reg signed [8:0]  p1_p [0:31];
    reg [4:0]         p1_sh [0:31];
    reg [7:0]         xc, wc;
    reg [3:0]         xs, ws, xf, wf;
    reg [7:0]         pm;
    reg               nan;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) p1_v <= 1'b0;
        else p1_v <= p0_v;
    end
    always @(posedge clk) begin
        p1_first <= p0_first; p1_last <= p0_last;
        p1_es <= p0_xe + p0_we;
        nan = 1'b0;
        for (i = 0; i < 32; i = i + 1) begin
            xc = p0_xq[8*i +: 8];
            wc = p0_wq[8*i +: 8];
            nan = nan | (xc[6:0] == 7'h7F) | (wc[6:0] == 7'h7F);
            xs = {(xc[6:3] != 4'd0), xc[2:0]};
            ws = {(wc[6:3] != 4'd0), wc[2:0]};
            xf = (xc[6:3] == 4'd0) ? 4'd1 : xc[6:3];
            wf = (wc[6:3] == 4'd0) ? 4'd1 : wc[6:3];
            pm = xs * ws;
            p1_p[i] <= (xc[7] ^ wc[7]) ? -$signed({1'b0, pm}) : $signed({1'b0, pm});
            p1_sh[i] <= {1'b0, xf} + {1'b0, wf} - 5'd2;
        end
        p1_nan <= nan;
    end

    // -- P2: terms (units of 2^-18) and CSA 32 -> 7 ---------------------------------------
    reg [32*W-1:0] terms;
    always @(*) begin
        for (i = 0; i < 32; i = i + 1)
            terms[W*i +: W] = {{(W-9){p1_p[i][8]}}, p1_p[i]} << p1_sh[i];
    end
    wire [M1*W-1:0] c7;
    ot_v41_csa #(.N(32), .M(M1), .W(W)) u_csa1 (.d(terms), .q(c7));
    reg               p2_v, p2_first, p2_last, p2_nan;
    reg signed [10:0] p2_es;
    reg [M1*W-1:0]    p2_c;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) p2_v <= 1'b0;
        else p2_v <= p1_v;
    end
    always @(posedge clk) begin
        p2_first <= p1_first; p2_last <= p1_last; p2_nan <= p1_nan; p2_es <= p1_es;
        p2_c <= c7;
    end

    // -- P3: CSA 7 -> 2 ------------------------------------------------------------------------
    wire [2*W-1:0] c2;
    ot_v41_csa #(.N(M1), .M(2), .W(W)) u_csa2 (.d(p2_c), .q(c2));
    reg               p3_v, p3_first, p3_last, p3_nan;
    reg signed [10:0] p3_es;
    reg [W-1:0]       p3_a, p3_b;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) p3_v <= 1'b0;
        else p3_v <= p2_v;
    end
    always @(posedge clk) begin
        p3_first <= p2_first; p3_last <= p2_last; p3_nan <= p2_nan; p3_es <= p2_es;
        p3_a <= c2[W-1:0]; p3_b <= c2[2*W-1:W];
    end

    // -- P4a: the carry-save pair's sum -------------------------------------------------------------
    reg               p4a_v, p4a_nan;
    reg signed [10:0] p4a_es;
    reg [W-1:0]       p4a_s;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) p4a_v <= 1'b0;
        else p4a_v <= p3_v;
    end
    always @(posedge clk) begin
        p4a_nan <= p3_nan; p4a_es <= p3_es;
        p4a_s <= p3_a + p3_b;
    end
    // -- P4b: sign-magnitude (the negation as ~s + 1 with a parallel-prefix increment) ---------------
    reg  [W-1:0] ng;
    reg  [W-1:0] ones4;
    always @* begin
        ones4[0] = 1'b1;
        for (i = 1; i < W; i = i + 1) ones4[i] = &(~p4a_s | ~(({{(W-1){1'b0}}, 1'b1} << i) - {{(W-1){1'b0}}, 1'b1}));
        ng = ~p4a_s ^ ones4;                  // -(a + b) = ~s + 1
    end
    reg               p4_v, p4_first, p4_last, p4_nan, p4_s;
    reg signed [11:0] p4_eb;
    reg [W-2:0]       p4_m;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) p4_v <= 1'b0;
        else p4_v <= p4a_v;
    end
    always @(posedge clk) begin
        p4_nan <= p4a_nan;
        //: biased exponent of the leading bit at position 40 is xe + we + 149
        p4_eb <= p4a_es + 12'sd149;
        p4_s <= p4a_s[W-1];
        p4_m <= p4a_s[W-1] ? ng[W-2:0] : p4a_s[W-2:0];
    end

    // -- P5a: normalise, coarse (32 / 16 / 8) ----------------------------------------------------------
    reg [40:0] nma;
    reg [5:0]  lza;
    always @(*) begin
        nma = p4_m; lza = 6'd0;
        if (nma[40:9]  == 32'd0) begin nma = nma << 32; lza = lza + 6'd32; end
        if (nma[40:25] == 16'd0) begin nma = nma << 16; lza = lza + 6'd16; end
        if (nma[40:33] == 8'd0)  begin nma = nma << 8;  lza = lza + 6'd8;  end
    end
    reg               p5a_v, p5a_nan, p5a_s, p5a_z;
    reg signed [11:0] p5a_eb;
    reg [40:0]        p5a_nm;
    reg [5:0]         p5a_lz;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) p5a_v <= 1'b0;
        else p5a_v <= p4_v;
    end
    always @(posedge clk) begin
        p5a_nan <= p4_nan; p5a_s <= p4_s; p5a_z <= (p4_m == 41'd0);
        p5a_eb <= p4_eb; p5a_nm <= nma; p5a_lz <= lza;
    end
    // -- P5b: normalise, fine (4 / 2 / 1) -----------------------------------------------------------
    reg [40:0] nm;
    reg [5:0]  lz;
    always @(*) begin
        nm = p5a_nm; lz = p5a_lz;
        if (nm[40:37] == 4'd0)  begin nm = nm << 4;  lz = lz + 6'd4;  end
        if (nm[40:39] == 2'd0)  begin nm = nm << 2;  lz = lz + 6'd2;  end
        if (nm[40] == 1'b0)     begin nm = nm << 1;  lz = lz + 6'd1;  end
    end
    reg               p5_v, p5_first, p5_last, p5_nan, p5_s, p5_z;
    reg signed [11:0] p5_eb;
    reg [40:0]        p5_nm;
    reg [5:0]         p5_lz;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) p5_v <= 1'b0;
        else p5_v <= p5a_v;
    end
    always @(posedge clk) begin
        p5_nan <= p5a_nan; p5_s <= p5a_s;
        p5_z <= p5a_z;
        p5_eb <= p5a_eb; p5_nm <= nm; p5_lz <= lz;
    end

    // -- P6: round to 24 bits (the golden's float32 of the exact dot) -----------------------------
    wire [23:0] m24 = p5_nm[40:17];
    wire        inc = p5_nm[16] & ((p5_nm[15:0] != 16'd0) | m24[0]);
    reg  [24:0] ones6;
    always @* begin
        ones6[0] = 1'b1;
        for (i = 1; i < 25; i = i + 1) ones6[i] = &({1'b0, m24} | ~((25'd1 << i) - 25'd1));
    end
    wire [24:0] mr = {1'b0, m24} ^ ({25{inc}} & ones6);          // m24 + inc, parallel prefix
    reg               p6_v, p6_first, p6_last, p6_nan, p6_s, p6_z;
    reg signed [11:0] p6_b;
    reg [22:0]        p6_f;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) p6_v <= 1'b0;
        else p6_v <= p5_v;
    end
    always @(posedge clk) begin
        p6_first <= p5_first; p6_last <= p5_last; p6_nan <= p5_nan; p6_s <= p5_s; p6_z <= p5_z;
        p6_b <= p5_eb - $signed({6'd0, p5_lz}) + $signed({11'd0, mr[24]});
        p6_f <= mr[24] ? 23'd0 : mr[22:0];
    end

    // -- P7: scale by 2^(xe+we): exponent add done; subnormal right shift -------------------------
    wire [11:0] rsh = 12'd1 - p6_b;                         // used when p6_b <= 0
    wire [4:0]  rs5 = (p6_b < -12'sd24) ? 5'd26 : rsh[4:0];
    wire [49:0] sw = {1'b1, p6_f, 26'd0} >> rs5;
    reg               p7_v, p7_first, p7_last, p7_nan, p7_sub, p7_ovf, p7_s;
    reg [31:0]        p7_n;                                 // normal / zero / inf result
    reg [23:0]        p7_t;
    reg               p7_g, p7_st;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) p7_v <= 1'b0;
        else p7_v <= p6_v;
    end
    always @(posedge clk) begin
        p7_first <= p6_first; p7_last <= p6_last; p7_nan <= p6_nan; p7_s <= p6_s;
        p7_sub <= !p6_z && (p6_b < 12'sd1);
        p7_ovf <= !p6_z && (p6_b > 12'sd254);
        if (p6_z)                  p7_n <= 32'd0;
        else if (p6_b > 12'sd254)  p7_n <= {p6_s, 8'hFF, 23'd0};
        else                       p7_n <= {p6_s, p6_b[7:0], p6_f};
        p7_t <= sw[49:26];
        p7_g <= sw[25];
        p7_st <= (sw[24:0] != 25'd0);
    end

    // -- P8: subnormal round and pack ---------------------------------------------------------------
    wire        inc8 = p7_g & (p7_st | p7_t[0]);
    reg  [23:0] ones8;
    always @* begin
        ones8[0] = 1'b1;
        for (i = 1; i < 24; i = i + 1) ones8[i] = &(p7_t | ~((24'd1 << i) - 24'd1));
    end
    wire [23:0] tr = p7_t ^ ({24{inc8}} & ones8);                  // p7_t + inc, parallel prefix
    reg         p8_v, p8_first, p8_last, p8_f;
    reg [31:0]  p8_y;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) p8_v <= 1'b0;
        else p8_v <= p7_v;
    end
    always @(posedge clk) begin
        p8_first <= p7_first; p8_last <= p7_last;
        p8_f <= p7_nan | p7_ovf;
        //: a subnormal that rounds up to 2^-126 carries into the exponent field
        p8_y <= p7_sub ? {p7_s, 7'd0, tr} : p7_n;
    end

    assign ov = p8_v;
    assign y = p8_y;
    assign f = p8_f;
    ot_hdc_delay #(.W(TW), .D(11)) u_tag (.clk(clk), .rst_n(rst_n), .d(tag), .q(otag));
endmodule
