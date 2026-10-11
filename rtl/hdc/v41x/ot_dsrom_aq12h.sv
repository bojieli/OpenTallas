`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_dsrom_aq12h (s81-suhc-hier-1011, 2026-10-11): HALF of ot_dsrom_aq12 (the 1.2 GHz FP8 act-quant of a 32-element
// block) for a 32-element block split over two neighbouring tiles (16 elements each).  The block maximum is order
// free (max of magnitudes, then the 1e-4 floor), so each half reduces its 16 magnitudes in 4 compare levels, exports
// its local maximum (mloc, nonfinite flag nloc), takes its partner's (mpart / npart, arriving XD cycles after its own)
// and both halves form the SAME amax = max(mine, partner, floor); every later stage is ot_dsrom_aq12's, per element,
// verbatim.  Codes / BF16 / exponent of each element are therefore bit-identical to ot_dsrom_aq12 on the whole block.
// LATENCY 18 + XD.
// ---------------------------------------------------------------------------
module ot_dsrom_aq12h #(parameter integer XD = 2) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          v,
    input  wire [511:0]  x,
    output wire [30:0]   mloc,
    output wire          nloc,
    input  wire [30:0]   mpart,
    input  wire          npart,
    output reg           vo,
    output reg  [127:0]  q,
    output reg  signed [9:0] e,
    output reg  [255:0]  y,
    output reg           fault
);
    localparam integer LATENCY = 18 + XD;
    localparam [30:0] FLOOR_FP8 = 31'h38d1b717;   // float32(1e-4)
    localparam [31:0] INV_448   = 32'h3b124925;   // float32(1/448)
    integer i;
    function automatic [30:0] mx(input [30:0] a, input [30:0] b);
        mx = (a >= b) ? a : b;
    endfunction

    wire [LATENCY:0] vl;
    ot_hdc_vline #(.D(LATENCY)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vl));
    // elements wait from S0 to the grid stage (S0 + 5 + 5 + 1 = 11 registers)
    reg  [511:0] s0_x;
    always @(posedge clk) s0_x <= x;
    wire [511:0] xg;
    ot_hdc_delay #(.W(512), .D(11 + XD)) u_x (.clk(clk), .rst_n(rst_n), .d(s0_x), .q(xg));

    // -- S1..S4: 16 -> 1, one compare level a stage (this half's local maximum) -----------------------
    reg [30:0] m1 [0:7];
    reg [30:0] m2 [0:3];
    reg [30:0] m3 [0:1];
    reg [30:0] m4;
    reg        nf1, nf2, nf3, nf4;
    reg        nfx;
    always @(*) begin
        nfx = 1'b0;
        for (i = 0; i < 16; i = i + 1) nfx = nfx | (s0_x[32*i + 23 +: 8] == 8'hFF);
    end
    always @(posedge clk) begin
        for (i = 0; i < 8; i = i + 1) m1[i] <= mx(s0_x[64*i +: 31], s0_x[64*i + 32 +: 31]);
        for (i = 0; i < 4; i = i + 1) m2[i] <= mx(m1[2*i], m1[2*i+1]);
        for (i = 0; i < 2; i = i + 1) m3[i] <= mx(m2[2*i], m2[2*i+1]);
        m4 <= mx(m3[0], m3[1]);
        nf1 <= nfx; nf2 <= nf1; nf3 <= nf2; nf4 <= nf3;
    end
    assign mloc = m4;
    assign nloc = nf4;
    // own maximum held XD cycles to meet the partner's
    wire [30:0] m4d;
    wire        nf4d;
    ot_hdc_delay #(.W(32), .D(XD)) u_md (.clk(clk), .rst_n(rst_n), .d({nf4, m4}), .q({nf4d, m4d}));
    // -- S5: max(own, partner, floor): three parallel compares and a select (order free) ----------------
    reg [30:0] amax;
    reg        nf5;
    wire ab = m4d >= mpart, af = m4d >= FLOOR_FP8, bf = mpart >= FLOOR_FP8;
    always @(posedge clk) begin
        amax <= (ab && af) ? m4d : (!ab && bf) ? mpart : FLOOR_FP8;
        nf5 <= nf4d | npart;
    end

    // -- S6..S10: amax * (1/448) ----------------------------------------------------------------
    wire [31:0] prod;
    wire        pfault;
    ot_hdc_qmul_lat #(5) u_scale (clk, rst_n, vl[6 + XD], {1'b0, amax}, INV_448, prod, pfault);
    wire nf10;
    ot_hdc_delay #(.W(1), .D(5)) u_nf (.clk(clk), .rst_n(rst_n), .d(nf5), .q(nf10));

    // -- S11: e = ceil_log2(prod) -----------------------------------------------------------------
    // also e + 127 and e + 121, so S12's two exponent differences are one subtract each, in parallel
    reg signed [9:0]  s11_e;
    reg signed [10:0] s11_ep, s11_dm;
    reg               s11_nf;
    wire [8:0] ce = {1'b0, prod[30:23]} + {8'd0, (prod[22:0] != 23'd0)};     // ceil_log2 + 127
    always @(posedge clk) begin
        s11_e <= $signed({1'b0, ce}) - 10'sd127;
        s11_ep <= $signed({2'b00, ce});
        s11_dm <= $signed({2'b00, ce}) - 11'sd6;
        s11_nf <= nf10 | pfault;
    end

    // -- S12: per-element exponent difference dd = -6 - (exp(x) - e) ----------------------------------
    reg signed [10:0] s12_ev [0:15];
    reg signed [10:0] s12_dd [0:15];
    reg [23:0]        s12_sig [0:15];
    reg [15:0]        s12_sgn;
    reg signed [9:0]  s12_e;
    reg               s12_nf;
    reg [7:0]         fld;
    reg signed [10:0] ev;   // max(fld, 1)
    always @(posedge clk) begin
        s12_e <= s11_e; s12_nf <= s11_nf;
        for (i = 0; i < 16; i = i + 1) begin
            fld = xg[32*i + 23 +: 8];
            //: ev = exp(x) - e with exp(x) = max(fld, 1) - 127;  dd = -6 - ev = (e + 121) - max(fld, 1)
            ev = $signed({3'b000, (fld == 8'd0) ? 8'd1 : fld});
            s12_ev[i] <= ev - s11_ep;
            s12_dd[i] <= s11_dm - ev;
            s12_sig[i] <= {(fld != 8'd0), xg[32*i +: 23]};
            s12_sgn[i] <= xg[32*i + 31] && (xg[32*i +: 31] != 31'd0);
        end
    end
    // -- S13: grid exponent and shift ------------------------------------------------------------------
    reg [23:0]       s13_sig [0:15];
    reg [4:0]        s13_rs [0:15];
    reg signed [4:0] s13_g [0:15];
    reg [15:0]       s13_sgn;
    reg signed [9:0] s13_e;
    reg              s13_nf;
    always @(posedge clk) begin
        s13_e <= s12_e; s13_nf <= s12_nf; s13_sgn <= s12_sgn;
        for (i = 0; i < 16; i = i + 1) begin
            s13_sig[i] <= s12_sig[i];
            if (s12_dd[i] > 11'sd0) begin
                s13_g[i] <= -5'sd6;
                s13_rs[i] <= (s12_dd[i] > 11'sd6) ? 5'd26 : (5'd20 + s12_dd[i][4:0]);
            end else begin
                s13_g[i] <= s12_ev[i][4:0];
                s13_rs[i] <= 5'd20;
            end
        end
    end
    // -- S14: the rounding shift ----------------------------------------------------------------------
    reg [23:0]       s14_tq [0:15];
    reg [15:0]       s14_gd, s14_st, s14_sgn;
    reg signed [4:0] s14_g [0:15];
    reg signed [9:0] s14_e;
    reg              s14_nf;
    reg [50:0]       wide;
    always @(posedge clk) begin
        s14_e <= s13_e; s14_nf <= s13_nf; s14_sgn <= s13_sgn;
        for (i = 0; i < 16; i = i + 1) begin
            wide = {s13_sig[i], 27'd0} >> s13_rs[i];
            s14_tq[i] <= wide[50:27];
            s14_gd[i] <= wide[26];
            s14_st[i] <= (wide[25:0] != 26'd0);
            s14_g[i] <= s13_g[i];
        end
    end
    // -- S15: round to the grid -------------------------------------------------------------------------
    reg [4:0]        s15_c [0:15];
    reg signed [4:0] s15_g [0:15];
    reg [15:0]       s15_sgn;
    reg signed [9:0] s15_e;
    reg              s15_nf;
    always @(posedge clk) begin
        s15_e <= s14_e; s15_nf <= s14_nf; s15_sgn <= s14_sgn;
        for (i = 0; i < 16; i = i + 1) begin
            s15_c[i] <= s14_tq[i][4:0] + {4'd0, s14_gd[i] & (s14_st[i] | s14_tq[i][0])};
            s15_g[i] <= s14_g[i];
        end
    end
    // -- S16: encode terms ------------------------------------------------------------------------------
    reg [4:0]         s16_c [0:15];
    reg [3:0]         s16_g4 [0:15];
    reg signed [11:0] s16_be [0:15];
    reg [7:0]         s16_cn [0:15];
    reg [6:0]         s16_sub [0:15];
    reg [15:0]        s16_sgn;
    reg signed [9:0]  s16_e;
    reg               s16_nf;
    reg [2:0]         p;
    reg [4:0]         c;
    reg signed [11:0] shs;
    always @(posedge clk) begin
        s16_e <= s15_e; s16_nf <= s15_nf; s16_sgn <= s15_sgn;
        for (i = 0; i < 16; i = i + 1) begin
            c = s15_c[i];
            p = c[4] ? 3'd4 : c[3] ? 3'd3 : c[2] ? 3'd2 : c[1] ? 3'd1 : 3'd0;
            s16_c[i] <= c;
            s16_g4[i] <= s15_g[i][3:0];
            s16_be[i] <= $signed({9'd0, p}) + s15_g[i] - 12'sd3 + s15_e + 12'sd127;
            s16_cn[i] <= {3'd0, c} << (3'd7 - p);
            shs = s15_g[i] - 12'sd3 + s15_e + 12'sd133;
            s16_sub[i] <= (shs < 12'sd0) ? 7'd0 : ({2'd0, c} << shs[3:0]);
        end
    end
    // -- S17: codes and dequantised BF16 (output registers) ----------------------------------------------
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin vo <= 1'b0; fault <= 1'b0; end
        else begin vo <= vl[LATENCY - 1]; fault <= vl[LATENCY - 1] && s16_nf; end
    end
    always @(posedge clk) begin
        e <= s16_e;
        for (i = 0; i < 16; i = i + 1) begin
            if (s16_c[i][4])      q[8*i +: 8] <= {s16_sgn[i], s16_g4[i] + 4'd8, 3'd0};
            else if (s16_c[i][3]) q[8*i +: 8] <= {s16_sgn[i], s16_g4[i] + 4'd7, s16_c[i][2:0]};
            else                  q[8*i +: 8] <= {s16_sgn[i], 4'd0, s16_c[i][2:0]};
            if (s16_c[i] == 5'd0)          y[16*i +: 16] <= {s16_sgn[i], 15'd0};
            else if (s16_be[i] >= 12'sd255) y[16*i +: 16] <= {s16_sgn[i], 8'hFF, 7'd0};
            else if (s16_be[i] >= 12'sd1)   y[16*i +: 16] <= {s16_sgn[i], s16_be[i][7:0], s16_cn[i][6:0]};
            else                            y[16*i +: 16] <= {s16_sgn[i], 8'd0, s16_sub[i]};
        end
    end
endmodule
