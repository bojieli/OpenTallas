`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hnx_coll_aq14 (HNX-GQ s3, L2H-P3/GQ 10-19): the next-release HBM COLL gather master's quantiser, structurally safe
// successor of ot_hgi_coll_aq13 (hnx_gq_issue_1019 n2 72d501b02 NEEDS_RTL: TT -53.69 ps on u_aq0.s8_e[0] -> s9_rs
// = exponent broadcast + signed exponent subtract + clamp + shift count in ONE stage, 16 cells / ~737 ps).
// Same numerics as ot_hdc_actquant (golden hdc_golden_v41.quant_fp8 / qdq_fp4_e8m0), same II 1, LATENCY 14 (was 13):
//   S0 input | S1 32->8 max | S2 8->2 | S2b 2->1 + floor | S3-S7 scale multiply (ot_hnx_coll_aq_scale13r) |
//   S8 e = ceil_log2(prod), formed as 32 KEPT per-element copies (one per element, each loads one subtractor) |
//   S9  (NEW split, a) per element: signed exponent Ev = exponent(x) - e (11 b), significand, sign |
//   S10 (split, b) per element: dd = min_exp - Ev, grid g, right-shift count (clamp 26), registered as 3 KEPT copies
//       (one per shifter chunk: [31:26] code+guard, [25:13] / [12:0] sticky) |
//   S11 round (chunk shifters read only their own count copy) | S12 encode = output registers (q, e, y, eb, vo, fault).
// No algebraic rewrite: every stage computes exactly the expression of ot_hgi_coll_aq13 (r4 FAN32 form), only cut at
// a register. The 1,024 b x 9-edge element line is the 16-slot SRAM ring ot_hnx_coll_aq_sramdelay (4 x
// ot_sram_1r1w_128x256_m1_r2c2, distinct read / write rows, read captured by a full-cycle register; LMUT = ring one
// slot short, x one edge early -> must fail); the S9 -> S10 significand / sign pass is 2 registers (no >= 3 flop line).
// eb = EBC kept copies of the biased exponent byte e + EBIAS (the issue leaf's exponent-word merge reads one copy per
// 16 bytes; was a 512-load capture register in the issue leaf).
// Bench: rtl/hbm_next/coll/tb/tb_hnx_aq14.sv (lockstep vs ot_hdc_actquant delayed one edge, 1,024 blocks FP8 + FP4,
// warm resets, eb check); tools/hbm_next/hnx_gq_s3_bench.sh.
// ---------------------------------------------------------------------------
module ot_hnx_coll_aq14 #(parameter integer MUT = 0, parameter integer LMUT = 0, parameter integer EBIAS = 127,
                          parameter integer EBC = 4) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          v,
    input  wire          fp4,
    input  wire [1023:0] x,
    output reg           vo,
    output reg  [255:0]  q,
    output reg  signed [9:0] e,
    output reg  [511:0]  y,
    output wire [8*EBC-1:0] eb,
    output reg           fault
);
    localparam [30:0] FLOOR_FP8 = 31'h38d1b717;   // float32(1e-4)
    localparam [30:0] FLOOR_FP4 = 31'h01c00000;   // float32(6 * 2^-126)
    localparam [31:0] INV_448   = 32'h3b124925;   // float32(1/448)
    localparam [31:0] INV_6     = 32'h3e2aaaab;   // float32(1/6)

    function automatic [30:0] mx(input [30:0] a, input [30:0] b);
        mx = (a >= b) ? a : b;
    endfunction
    function automatic [30:0] mx4(input [30:0] a,b,c,d);
      reg ab,ac,ad,bc,bd,cd,wa,wb,wc,wd;
      begin
        ab=a>=b;ac=a>=c;ad=a>=d;bc=b>=c;bd=b>=d;cd=c>=d;
        wa=ab&&ac&&ad;wb=!ab&&bc&&bd;wc=!ac&&!bc&&cd;wd=!ad&&!bd&&!cd;
        mx4=({31{wa}}&a)|({31{wb}}&b)|({31{wc}}&c)|({31{wd}}&d);
      end
    endfunction
    integer i;

    // -- S0: input register ------------------------------------------------------------------------------------------
    reg          s0_v, s0_fp4;
    reg [1023:0] s0_x;
    always @(posedge clk or negedge rst_n) if (!rst_n) s0_v <= 1'b0; else s0_v <= v;
    always @(posedge clk) begin s0_x <= x; s0_fp4 <= fp4; end

    // -- S1: magnitudes, 32 -> 8 ---------------------------------------------------------------------------------------
    reg        s1_v, s1_fp4, s1_nf;
    reg [30:0] s1_m [0:7];
    reg        nf0;
    always @(*) begin
        nf0 = 1'b0;
        for (i = 0; i < 32; i = i + 1) nf0 = nf0 | (s0_x[32*i + 23 +: 8] == 8'hFF);
    end
    always @(posedge clk or negedge rst_n) if (!rst_n) s1_v <= 1'b0; else s1_v <= s0_v;
    always @(posedge clk) begin
        s1_fp4 <= s0_fp4; s1_nf <= nf0;
        for (i = 0; i < 8; i = i + 1) s1_m[i] <= mx4(s0_x[128*i+:31],s0_x[128*i+32+:31],s0_x[128*i+64+:31],s0_x[128*i+96+:31]);
    end

    // -- S2: 8 -> 2 ------------------------------------------------------------------------------------------------------
    reg        s2a_v, s2a_fp4, s2a_nf;
    reg [30:0] s2a_m [0:1];
    always @(posedge clk or negedge rst_n) if (!rst_n) s2a_v <= 1'b0; else s2a_v <= s1_v;
    always @(posedge clk) begin
        s2a_fp4 <= s1_fp4; s2a_nf <= s1_nf;
        for (i = 0; i < 2; i = i + 1) s2a_m[i] <= mx4(s1_m[4*i],s1_m[4*i+1],s1_m[4*i+2],s1_m[4*i+3]);
    end

    // -- S2b: 2 -> 1 and the floor ---------------------------------------------------------------------------------------
    reg        s2_v, s2_fp4, s2_nf;
    reg [30:0] s2_amax;
    always @(posedge clk or negedge rst_n) if (!rst_n) s2_v <= 1'b0; else s2_v <= s2a_v;
    always @(posedge clk) begin
        s2_fp4 <= s2a_fp4; s2_nf <= s2a_nf;
        s2_amax <= mx(mx(s2a_m[0], s2a_m[1]), s2a_fp4 ? FLOOR_FP4 : FLOOR_FP8);
    end

    // -- S3-S7: amax * (1/448 or 1/6), one binary32 multiply ----------------------------------------------------------
    wire [31:0] prod;
    wire        pfault;
    ot_hnx_coll_aq_scale13r u_scale (.clk(clk), .rst_n(rst_n), .v(s2_v), .a({1'b0, s2_amax}),
                         .b((s2_fp4^(MUT!=0)) ? INV_6 : INV_448), .y(prod), .fault(pfault));
    reg [4:0] vl;
    always @(posedge clk or negedge rst_n) if (!rst_n) vl <= 5'd0; else vl <= {vl[3:0], s2_v};
    wire s7_v = vl[4];
    // fp4 / nf ride a 5-edge 2-bit control line (2 bits: no wide flop line)
    reg [1:0] fn [0:4];
    always @(posedge clk) begin fn[0] <= {s2_fp4, s2_nf}; for (i = 1; i < 5; i = i + 1) fn[i] <= fn[i-1]; end
    wire s7_fp4 = fn[4][1], s7_nf = fn[4][0];

    // elements S0 -> S8 (nine edges) on the SRAM ring
    wire [1023:0] x8;
    ot_hnx_coll_aq_sramdelay #(.MUT(LMUT)) u_x (.clk(clk), .rst_n(rst_n), .d(s0_x), .q(x8));

    // -- S8: e = ceil_log2(prod), one KEPT {fp4, e} copy per element -----------------------------------------------------
    reg s8_v, s8_nf;
    always @(posedge clk or negedge rst_n) if (!rst_n) s8_v <= 1'b0; else s8_v <= s7_v;
    always @(posedge clk) s8_nf <= s7_nf | pfault;
    wire signed [9:0] e8_d = $signed({2'b00, prod[30:23]}) - 10'sd127 + {9'd0, (prod[22:0] != 23'd0)};
    wire signed [9:0] s8_ec [0:31];
    wire [31:0] s8_fp4c;
    genvar g;
    generate for (g = 0; g < 32; g = g + 1) begin : g_s8
        ot_hnx_coll_aq_cff #(.W(11)) u_ff(.clk(clk),
`ifdef OT_HNX_AQ_MUT_EC
            .d({s7_fp4, (g == 5) ? (e8_d ^ 10'd1) : e8_d}),
`else
            .d({s7_fp4, e8_d}),
`endif
            .q({s8_fp4c[g], s8_ec[g]}));
    end endgenerate

    // -- S9 (split a): signed element exponent Ev = exponent(x) - e ----------------------------------------------------
    reg              s9_v, s9_nf;
    reg signed [9:0] s9_e;
    reg              s9_fp4;
    reg signed [10:0] s9_ev [0:31];
    reg [31:0]       s9_fp4e;
    reg [23:0]       s9_sig [0:31];
    reg [31:0]       s9_sgn;
    always @(posedge clk or negedge rst_n) if (!rst_n) s9_v <= 1'b0; else s9_v <= s8_v;
    always @(posedge clk) begin : p_s9
        reg [7:0] fld;
        s9_nf <= s8_nf; s9_e <= s8_ec[0]; s9_fp4 <= s8_fp4c[0];
        for (i = 0; i < 32; i = i + 1) begin
            fld = x8[32*i + 23 +: 8];
            //: a subnormal element has exponent -126 and no leading one
            s9_ev[i] <= ((fld == 8'd0) ? -11'sd126 : ($signed({3'b000, fld}) - 11'sd127)) - s8_ec[i];
            s9_fp4e[i] <= s8_fp4c[i];
            s9_sig[i] <= {(fld != 8'd0), x8[32*i +: 23]};
            s9_sgn[i] <= x8[32*i + 31] && (x8[32*i +: 31] != 31'd0);
        end
    end

    // -- S10 (split b): dd = min_exp - Ev, grid exponent g, shift count (3 kept copies per element) ----------------------
    reg              s10_v, s10_nf, s10_fp4;
    reg signed [9:0] s10_e;
    reg signed [4:0] s10_g [0:31];
    reg [23:0]       s10_sig [0:31];
    reg [31:0]       s10_sgn;
    wire [4:0]       s10_rs [0:31][0:2];
    function automatic [4:0] rs_of(input signed [10:0] ev, input fp4);
        reg signed [10:0] mine, dd;
        begin
            mine = fp4 ? 11'sd0 : -11'sd6; dd = mine - ev;
            //: past 26 every bit of the 24-bit significand is below the guard
            if (dd > 11'sd0) rs_of = (dd > (fp4 ? 11'sd4 : 11'sd6)) ? 5'd26 : ((fp4 ? 5'd22 : 5'd20) + dd[4:0]);
            else             rs_of = fp4 ? 5'd22 : 5'd20;
        end
    endfunction
    generate for (g = 0; g < 32; g = g + 1) begin : g_s10
        wire [4:0] rsd = rs_of(s9_ev[g], s9_fp4e[g]);
        for (genvar c = 0; c < 3; c = c + 1) begin : g_c
            ot_hnx_coll_aq_cff #(.W(5)) u_ff(.clk(clk),
`ifdef OT_HNX_AQ_MUT_RS
                .d((g == 9 && c == 0) ? (rsd ^ 5'd1) : rsd),
`else
                .d(rsd),
`endif
                .q(s10_rs[g][c]));
        end
    end endgenerate
    always @(posedge clk or negedge rst_n) if (!rst_n) s10_v <= 1'b0; else s10_v <= s9_v;
    always @(posedge clk) begin : p_s10
        reg signed [10:0] mine, dd;
        s10_nf <= s9_nf; s10_e <= s9_e; s10_fp4 <= s9_fp4; s10_sgn <= s9_sgn;
        for (i = 0; i < 32; i = i + 1) begin
            mine = s9_fp4e[i] ? 11'sd0 : -11'sd6; dd = mine - s9_ev[i];
            s10_g[i] <= (dd > 11'sd0) ? mine[4:0] : s9_ev[i][4:0];
            s10_sig[i] <= s9_sig[i];
        end
    end

    // -- S11: round to the grid (chunk shifters on their own count copy) -------------------------------------------------
    reg              s11_v, s11_nf;
    reg signed [9:0] s11_e;
    reg [4:0]        s11_c [0:31];
    reg signed [4:0] s11_g [0:31];
    reg [31:0]       s11_sgn;
    wire [31:0]      wlo [0:31];        // wide[31:0] of {sig, 27'd0} >> rs (wide[31:27] = tq[4:0], [26] guard, [25:0] sticky)
    generate for (g = 0; g < 32; g = g + 1) begin : g_s11
        ot_hnx_coll_aq_shift_chunk #(.LO(26), .W(6))  u_c0(.sig(s10_sig[g]), .shift(s10_rs[g][0]), .q(wlo[g][31:26]));
        ot_hnx_coll_aq_shift_chunk #(.LO(13), .W(13)) u_c1(.sig(s10_sig[g]), .shift(s10_rs[g][1]), .q(wlo[g][25:13]));
        ot_hnx_coll_aq_shift_chunk #(.LO(0),  .W(13)) u_c2(.sig(s10_sig[g]), .shift(s10_rs[g][2]), .q(wlo[g][12:0]));
    end endgenerate
    // encode-stage {fp4, e} copies: 16 kept copies, 2 elements each
    wire signed [9:0] s11_ec [0:15];
    wire [15:0]       s11_fp4c;
    generate for (g = 0; g < 16; g = g + 1) begin : g_s11c
        ot_hnx_coll_aq_cff #(.W(11)) u_ff(.clk(clk), .d({s10_fp4, s10_e}), .q({s11_fp4c[g], s11_ec[g]}));
    end endgenerate
    always @(posedge clk or negedge rst_n) if (!rst_n) s11_v <= 1'b0; else s11_v <= s10_v;
    always @(posedge clk) begin : p_s11
        reg [4:0] tq; reg gd, st;
        s11_nf <= s10_nf; s11_e <= s10_e; s11_sgn <= s10_sgn;
        for (i = 0; i < 32; i = i + 1) begin
            tq = wlo[i][31:27];
            gd = wlo[i][26];
            st = (wlo[i][25:0] != 26'd0);
            s11_c[i] <= tq[4:0] + {4'd0, gd & (st | tq[0])};
            s11_g[i] <= s10_g[i];
        end
    end

    // -- S12: codes, dequantised BF16, exponent (+ biased byte copies) = output registers --------------------------------
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin vo <= 1'b0; fault <= 1'b0; end
        else begin vo <= s11_v; fault <= s11_v && s11_nf; end
    end
    generate for (g = 0; g < EBC; g = g + 1) begin : g_eb
        ot_hnx_coll_aq_cff #(.W(8)) u_ff(.clk(clk), .d(8'(s11_e + EBIAS)), .q(eb[8*g +: 8]));
    end endgenerate
    always @(posedge clk) begin : p_s12
        reg [2:0] p; reg signed [11:0] be, shs; reg [4:0] c; reg [7:0] cn; reg [6:0] sub; reg [3:0] g4;
        reg f4; reg signed [9:0] ee;
        e <= s11_e;
        for (i = 0; i < 32; i = i + 1) begin
            c = s11_c[i];
            g4 = s11_g[i][3:0];
            f4 = s11_fp4c[i/2]; ee = s11_ec[i/2];
            if (!f4) begin
                if (c[4])      q[8*i +: 8] <= {s11_sgn[i], g4 + 4'd8, 3'd0};
                else if (c[3]) q[8*i +: 8] <= {s11_sgn[i], g4 + 4'd7, c[2:0]};
                else           q[8*i +: 8] <= {s11_sgn[i], 4'd0, c[2:0]};
            end else begin
                if (c[2])      q[8*i +: 8] <= {4'd0, s11_sgn[i], g4[1:0] + 2'd2, 1'b0};
                else if (c[1]) q[8*i +: 8] <= {4'd0, s11_sgn[i], g4[1:0] + 2'd1, c[0]};
                else           q[8*i +: 8] <= {4'd0, s11_sgn[i], 2'd0, c[0]};
            end
            // value c * 2^(g - mant_bits + e) as BF16
            p = c[4] ? 3'd4 : c[3] ? 3'd3 : c[2] ? 3'd2 : c[1] ? 3'd1 : 3'd0;
            be = $signed({9'd0, p}) + s11_g[i] - (f4 ? 12'sd1 : 12'sd3) + ee + 12'sd127;
            cn = {3'd0, c} << (3'd7 - p);
            shs = s11_g[i] - (f4 ? 12'sd1 : 12'sd3) + ee + 12'sd133;
            sub = (shs < 12'sd0) ? 7'd0 : ({2'd0, c} << shs[3:0]);
            if (c == 5'd0)           y[16*i +: 16] <= {s11_sgn[i], 15'd0};
            else if (be >= 12'sd255) y[16*i +: 16] <= {s11_sgn[i], 8'hFF, 7'd0};
            else if (be >= 12'sd1)   y[16*i +: 16] <= {s11_sgn[i], be[7:0], cn[6:0]};
            else                     y[16*i +: 16] <= {s11_sgn[i], 8'd0, sub};
        end
    end
endmodule

// Nine-edge, II 1 delay on a 16-slot SRAM ring (= ot_hgi_coll_aq_sramdelay, codex/hbm-gqissue-sram-proof-1019
// @151a73129, aqexact PASS + wrong-slot mutant FAIL witnessed there). Write address / data sampled at the negedge after
// the source edge, written at the next posedge; read slot 7 behind; the macro output is captured by a full-cycle
// register: q[n] = d[n-9]. Distinct read and write rows every edge (no same-address read-during-write assumption).
// No reset on data.
module ot_hnx_coll_aq_sramdelay #(parameter integer MUT = 0) (
    input wire clk, input wire rst_n, input wire [1023:0] d, output reg [1023:0] q
);
    wire [1023:0] rd;
    always @(posedge clk) q <= rd;
    reg [3:0] slot;
    always @(posedge clk or negedge rst_n) if (!rst_n) slot <= 4'd0; else slot <= slot + 4'd1;
    genvar k;
    generate for (k = 0; k < 4; k = k + 1) begin : g_sram
        reg [3:0] wa_n, ra_n;
        reg [255:0] wd_n;
        always @(negedge clk) begin
            wa_n <= slot;
            ra_n <= slot - ((MUT != 0) ? 4'd6 : 4'd7);
            wd_n <= d[256*k +: 256];
        end
        ot_sram_1r1w_128x256_m1_r2c2 u_mem (
            .clk(clk), .r_ce_in(1'b1), .r_addr_in({3'd0, ra_n}), .rd_out(rd[256*k +: 256]),
            .w_ce_in(1'b1), .w_addr_in({3'd0, wa_n}), .wd_in(wd_n),
            .w_mask_in({256{1'b1}}),
            .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end endgenerate
endmodule

// kept control copy: one register bank per instance (keep_hierarchy + keep / dont_touch: Yosys cannot merge copies)
(* keep_hierarchy = "yes" *)
module ot_hnx_coll_aq_cff #(parameter integer W = 11) (input wire clk, input wire [W-1:0] d, output wire [W-1:0] q);
    (* keep = "true", dont_touch = "true" *) reg [W-1:0] r;
    always @(posedge clk) r <= d;
    assign q = r;
endmodule

// bits [LO +: W] of {sig, 27'd0} >> shift (one chunk of the S11 rounding shifter, on its own count copy)
(* keep_hierarchy = "yes" *)
module ot_hnx_coll_aq_shift_chunk #(parameter integer LO = 0, parameter integer W = 13) (
    input wire [23:0] sig, input wire [4:0] shift, output wire [W-1:0] q);
    wire [50:0] xs = {sig, 27'd0} >> shift;
    assign q = xs[LO +: W];
endmodule
