`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_v41_bterm2: ot_v41_bterm re-cut for 1.2 GHz at SS (W10, 0.833 ns): the 42-bit sum and its negation
// split (P4a / P4b, the negation as a parallel-prefix increment), the 41-bit normalise split (P5a coarse
// 32/16/8, P5b fine 4/2/1), and the two roundings as parallel-prefix increments (yosys otherwise maps an
// increment as a ripple of ORs).  Arithmetic bit-identical to ot_v41_bterm; LATENCY = 11 (was 9).
// ---------------------------------------------------------------------------
module ot_v41_bterm2 #(
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

    // -- P4a: the carry-save pair's sum -------------------------------------------------------------
    wire [W-1:0] s4a;
    wire         c4a;
    ot_v41_ksadd #(.W(W)) u_s4a (.a(p3_a), .b(p3_b), .cin(1'b0), .s(s4a), .cout(c4a));
    reg               p4a_v, p4a_nan;
    reg signed [10:0] p4a_es;
    reg [W-1:0]       p4a_s;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) p4a_v <= 1'b0;
        else p4a_v <= p3_v;
    end
    always @(posedge clk) begin
        p4a_nan <= p3_nan; p4a_es <= p3_es;
        p4a_s <= s4a;
    end
    // -- P4b: sign-magnitude (the negation as ~s + 1 with a parallel-prefix increment) ---------------
    wire [W-1:0] ng;                          // -(a + b) = ~s + 1
    wire         cng;
    ot_v41_inc #(.W(W)) u_ng (.a(~p4a_s), .inc(1'b1), .y(ng), .co(cng));
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
    reg signed [11:0] p5_ebl;           // exponent of the normalised leading bit (eb - lz), formed here
    reg [40:0]        p5_nm;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) p5_v <= 1'b0;
        else p5_v <= p5a_v;
    end
    always @(posedge clk) begin
        p5_nan <= p5a_nan; p5_s <= p5a_s;
        p5_z <= p5a_z;
        p5_ebl <= p5a_eb - $signed({6'd0, lz}); p5_nm <= nm;
    end

    // -- P6: round to 24 bits (the golden's float32 of the exact dot) -----------------------------
    wire [23:0] m24 = p5_nm[40:17];
    wire        inc = p5_nm[16] & ((p5_nm[15:0] != 16'd0) | m24[0]);
    wire [24:0] mr;                                              // m24 + inc, explicit prefix
    wire        cmr;
    ot_v41_inc #(.W(25)) u_mr (.a({1'b0, m24}), .inc(inc), .y(mr), .co(cmr));
    reg               p6_v, p6_first, p6_last, p6_nan, p6_s, p6_z;
    reg signed [11:0] p6_b;
    reg [22:0]        p6_f;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) p6_v <= 1'b0;
        else p6_v <= p5_v;
    end
    always @(posedge clk) begin
        p6_first <= p5_first; p6_last <= p5_last; p6_nan <= p5_nan; p6_s <= p5_s; p6_z <= p5_z;
        p6_b <= p5_ebl + $signed({11'd0, mr[24]});
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
    wire [23:0] tr;                                                // p7_t + inc, explicit prefix
    wire        ctr;
    ot_v41_inc #(.W(24)) u_tr (.a(p7_t), .inc(inc8), .y(tr), .co(ctr));
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
