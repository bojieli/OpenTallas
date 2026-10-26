`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_v41_bterm: one exact scaled block term of golden linear_q (tools/hdc_golden_v41.py):
// the 32-wide E4M3 x E4M3 (or E2M1) block dot formed exactly, rounded ONCE to binary32 and
// scaled by 2^(xe + we) -- the term every lane of the V4.1 ROM element feeds its chunk chain.
// Stages P0..P8 are ot_hdc_blockdot's (rtl/hdc/v41/ot_hdc_blockdot.sv, qualified 1195.7 MHz),
// copied verbatim; the accumulator is left to the caller.  `tag` rides alongside.
// LATENCY = 9: a block presented with v in cycle t leaves as ov in cycle t + 9.
// f = NaN code or scaled overflow (fail closed).  Zero terms are +0.
// ---------------------------------------------------------------------------
// (copied from rtl/hdc/v41/ot_hdc_blockdot.sv ot_hdc_v41_csa) Carry-save reduction of N W-bit operands (mod 2^W) to at most M, by levels of
// 3:2 compressors; operands that do not fill a triple pass to the next level.
module ot_v41_csa #(
    parameter integer N = 32,
    parameter integer M = 2,
    parameter integer W = 42
) (
    input  wire [N*W-1:0] d,
    output wire [M*W-1:0] q
);
    function automatic integer nxt(input integer n);
        nxt = 2 * (n / 3) + (n % 3);
    endfunction
    function automatic integer nlev(input integer n, input integer m);
        integer c, k;
        begin
            nlev = 0; c = n;
            for (k = 0; k < 64; k = k + 1)
                if (c > m) begin c = nxt(c); nlev = nlev + 1; end
        end
    endfunction
    function automatic integer cnt(input integer n, input integer l);
        integer k;
        begin
            cnt = n;
            for (k = 0; k < l; k = k + 1) cnt = nxt(cnt);
        end
    endfunction
    function automatic integer off(input integer n, input integer l);
        integer k, c;
        begin
            off = 0; c = n;
            for (k = 0; k < l; k = k + 1) begin off = off + c; c = nxt(c); end
        end
    endfunction
    localparam integer L = nlev(N, M);
    localparam integer NF = cnt(N, L);
    localparam integer OL = off(N, L);
    localparam integer TOT = OL + NF;
    wire [W-1:0] op [0:TOT-1] /*verilator split_var*/;
    genvar i, l;
    generate
        for (i = 0; i < N; i = i + 1) begin : g_in
            assign op[i] = d[W*i +: W];
        end
        for (l = 0; l < L; l = l + 1) begin : g_lvl
            localparam integer NI = cnt(N, l);
            localparam integer OI = off(N, l);
            localparam integer OO = off(N, l + 1);
            localparam integer G3 = NI / 3;
            for (i = 0; i < G3; i = i + 1) begin : g_fa
                wire [W-1:0] a = op[OI + 3*i];
                wire [W-1:0] b = op[OI + 3*i + 1];
                wire [W-1:0] c = op[OI + 3*i + 2];
                wire [W-1:0] mj = (a & b) | (a & c) | (b & c);
                assign op[OO + 2*i] = a ^ b ^ c;
                assign op[OO + 2*i + 1] = {mj[W-2:0], 1'b0};
            end
            for (i = 0; i < NI % 3; i = i + 1) begin : g_pass
                assign op[OO + 2*G3 + i] = op[OI + 3*G3 + i];
            end
        end
        for (i = 0; i < M; i = i + 1) begin : g_out
            if (i < NF) begin : g_op
                assign q[W*i +: W] = op[OL + i];
            end else begin : g_zero
                assign q[W*i +: W] = {W{1'b0}};
            end
        end
    endgenerate
endmodule


module ot_v41_bterm #(
    parameter integer TW = 8
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
    reg              p0_v, p0_first, p0_last, p0_fp4;
    reg [255:0]      p0_xq, p0_wq;
    reg signed [9:0] p0_xe, p0_we;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) p0_v <= 1'b0;
        else p0_v <= v;
    end
    always @(posedge clk) begin
        p0_first <= first; p0_last <= last; p0_fp4 <= fp4;
        p0_xq <= xq; p0_wq <= wq; p0_xe <= xe; p0_we <= we;
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
            wc = p0_fp4 ? e2m1(p0_wq[8*i +: 4]) : p0_wq[8*i +: 8];
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
    wire [7*W-1:0] c7;
    ot_v41_csa #(.N(32), .M(7), .W(W)) u_csa1 (.d(terms), .q(c7));
    reg               p2_v, p2_first, p2_last, p2_nan;
    reg signed [10:0] p2_es;
    reg [7*W-1:0]     p2_c;
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
    ot_v41_csa #(.N(7), .M(2), .W(W)) u_csa2 (.d(p2_c), .q(c2));
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

    // -- P4: sum and its negation in parallel; sign-magnitude -------------------------------------
    wire [W-1:0] sp = p3_a + p3_b;
    wire [W-1:0] sn = ~p3_a + ~p3_b + {{(W-2){1'b0}}, 2'd2};     // -(a + b)
    reg               p4_v, p4_first, p4_last, p4_nan, p4_s;
    reg signed [11:0] p4_eb;
    reg [W-2:0]       p4_m;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) p4_v <= 1'b0;
        else p4_v <= p3_v;
    end
    always @(posedge clk) begin
        p4_first <= p3_first; p4_last <= p3_last; p4_nan <= p3_nan;
        //: biased exponent of the leading bit at position 40 is xe + we + 149
        p4_eb <= p3_es + 12'sd149;
        p4_s <= sp[W-1];
        p4_m <= sp[W-1] ? sn[W-2:0] : sp[W-2:0];
    end

    // -- P5: normalise ----------------------------------------------------------------------------
    reg [40:0] nm;
    reg [5:0]  lz;
    always @(*) begin
        nm = p4_m; lz = 6'd0;
        if (nm[40:9]  == 32'd0) begin nm = nm << 32; lz = lz + 6'd32; end
        if (nm[40:25] == 16'd0) begin nm = nm << 16; lz = lz + 6'd16; end
        if (nm[40:33] == 8'd0)  begin nm = nm << 8;  lz = lz + 6'd8;  end
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
        else p5_v <= p4_v;
    end
    always @(posedge clk) begin
        p5_first <= p4_first; p5_last <= p4_last; p5_nan <= p4_nan; p5_s <= p4_s;
        p5_z <= (p4_m == 41'd0);
        p5_eb <= p4_eb; p5_nm <= nm; p5_lz <= lz;
    end

    // -- P6: round to 24 bits (the golden's float32 of the exact dot) -----------------------------
    wire [23:0] m24 = p5_nm[40:17];
    wire        inc = p5_nm[16] & ((p5_nm[15:0] != 16'd0) | m24[0]);
    wire [24:0] mr = {1'b0, m24} + {24'd0, inc};
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
    wire [23:0] tr = p7_t + {23'd0, p7_g & (p7_st | p7_t[0])};
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
    ot_hdc_delay #(.W(TW), .D(9)) u_tag (.clk(clk), .rst_n(rst_n), .d(tag), .q(otag));
endmodule
