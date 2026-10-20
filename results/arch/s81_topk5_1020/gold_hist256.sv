`timescale 1ns/1ps
// Immutableb6bba788c golden arithmetic; ONLY module identifiers renamed.
module ot_s81ph_hist256_gold_popc #(
    parameter integer N  = 16,
    parameter integer OW = 5
) (
    input  wire [N-1:0]  x,
    output wire [OW-1:0] y
);
    localparam integer NP = (N > 1) ? (1 << $clog2(N)) : 2;
    /* verilator lint_off UNOPTFLAT */
    wire [2*NP*OW-1:0] t;
    /* verilator lint_on UNOPTFLAT */
    genvar n;
    generate
        for (n = 0; n < NP; n = n + 1) begin : g_leaf
            if (n < N) begin : g_x
                assign t[OW*(NP+n) +: OW] = {{(OW-1){1'b0}}, x[n]};
            end else begin : g_0
                assign t[OW*(NP+n) +: OW] = {OW{1'b0}};
            end
        end
        for (n = 1; n < NP; n = n + 1) begin : g_node
            assign t[OW*n +: OW] = t[OW*(2*n) +: OW] + t[OW*(2*n+1) +: OW];
        end
    endgenerate
    assign t[OW-1:0] = {OW{1'b0}};
    assign y = t[OW +: OW];
endmodule
module ot_s81ph_hist256_gold_topk5 #(
    parameter integer W  = 16,
    parameter integer CB = 11,
    // CLAUDE s81-blocks 2026-10-07 (selt_q cd3337221-b SS -434.7: hbin -> gs1, gs1 -> gsum, clr -> hbin): HPIPE 1 =
    // the inputs (valid, enables, digits, clear) registered one edge, and each 4-bin group sum split into two
    // registered Kogge-Stone pair sums (+1 edge in each of the two trees).  gsel -> gbin is unchanged (the control's
    // step-B round trip stays aligned); gsum arrives 3 edges later, gbin 1 (the slice's settle counters cover it).
    parameter integer HPIPE = 0
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 clr,
    input  wire                 i_v,
    input  wire [W-1:0]         i_en,
    input  wire [W*8-1:0]       i_dg,
    input  wire [3:0]           gsel,
`ifdef OT_S81PH_SEL_FAN32
    // S81-TOPK FAN32: 16 KEPT identical copies of gsel (one per gbin output bin), registered on gsel's edge
    input  wire [16*4-1:0]      gsel_c,
`endif
    output reg  [16*(CB+4)-1:0] gsum,
    output reg  [16*CB-1:0]     gbin,
    output wire                 busy
);
    localparam integer LW = (W > 1) ? $clog2(W) : 1;
    localparam integer HW = LW + 1;                 // per-beat count width
    localparam [CB-1:0] SAT = {CB{1'b1}};

    // HPIPE: registered inputs (x_*); HPIPE 0: the ports themselves
    wire           x_v, x_clr;
    wire [W-1:0]   x_en;
    wire [W*8-1:0] x_dg;
    generate if (HPIPE != 0) begin : g_xin
        reg          r_v, r_clr;
        reg [W-1:0]  r_en;
        reg [W*8-1:0] r_dg;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin r_v <= 1'b0; r_clr <= 1'b0; end
            else begin r_v <= i_v; r_clr <= clr; end
        always @(posedge clk) begin r_en <= i_en; r_dg <= i_dg; end
        assign x_v = r_v; assign x_clr = r_clr; assign x_en = r_en; assign x_dg = r_dg;
    end else begin : g_xd
        assign x_v = i_v; assign x_clr = clr; assign x_en = i_en; assign x_dg = i_dg;
    end endgenerate

    reg          v1, v2;
    reg [W*16-1:0] h1_hi, h1_lo;
    genvar gl, gb;
    wire [W*16-1:0] h1_hi_d, h1_lo_d;
    generate
        for (gl = 0; gl < W; gl = gl + 1) begin : g_pre
            wire [7:0] d = x_dg[8*gl +: 8];
            assign h1_hi_d[16*gl +: 16] = x_en[gl] ? (16'h0001 << d[7:4]) : 16'h0000;
            assign h1_lo_d[16*gl +: 16] = 16'h0001 << d[3:0];
        end
    endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin v1 <= 1'b0; v2 <= 1'b0; end
        else begin v1 <= x_v && !x_clr; v2 <= v1 && !x_clr; end
    end
    always @(posedge clk) begin h1_hi <= h1_hi_d; h1_lo <= h1_lo_d; end

    reg  [256*HW-1:0] h2;
    wire [256*HW-1:0] h2_d;
    generate
        for (gb = 0; gb < 256; gb = gb + 1) begin : g_cnt
            wire [W-1:0] x;
            for (gl = 0; gl < W; gl = gl + 1) begin : g_x
                assign x[gl] = h1_hi[16*gl + (gb >> 4)] && h1_lo[16*gl + (gb & 15)];
            end
            ot_s81ph_hist256_gold_popc #(.N(W), .OW(HW)) u_pc (.x(x), .y(h2_d[HW*gb +: HW]));
        end
    endgenerate
    always @(posedge clk) h2 <= h2_d;

    reg  [256*CB-1:0] hbin;
    wire [256*CB-1:0] hbin_d;
    generate
        for (gb = 0; gb < 256; gb = gb + 1) begin : g_add
            wire [CB:0] s = {1'b0, hbin[CB*gb +: CB]} + {{(CB+1-HW){1'b0}}, h2[HW*gb +: HW]};
            assign hbin_d[CB*gb +: CB] = s[CB] ? SAT : s[CB-1:0];
        end
    endgenerate
`ifdef OT_S81PH_SEL_FAN32
    // S81-TOPK FAN32 (10-19, SAFE item 3): the bin clear (2820 loads) and the bin update enable v2 (2112 loads) are
    // replaced by NCL KEPT identical copies, each owning 256/NCL bins (2 bins = 22 bin flops per copy).  Each clear
    // copy registers `clr` on the same edge as r_clr (HPIPE 1) and each v2 copy is v1 && !its clear copy, as v2.
    localparam integer NCL = 128;
    wire [NCL-1:0] x_clr_c, v2_c;
    genvar gk;
    for (gk = 0; gk < NCL; gk = gk + 1) begin : g_clc
        if (HPIPE != 0) begin : g_r
            (* keep = "true" *) reg rc;
  `ifdef OT_S81PH_SEL_FAN32_MUT_CLR
            // mutant witness only: the clear copies of the lower half of the bins never clear (stale counts)
            always @(posedge clk or negedge rst_n)
                if (!rst_n) rc <= 1'b0; else rc <= (gk < NCL / 2) ? 1'b0 : clr;
  `else
            always @(posedge clk or negedge rst_n)
                if (!rst_n) rc <= 1'b0; else rc <= clr;
  `endif
            assign x_clr_c[gk] = rc;
        end else begin : g_d
            assign x_clr_c[gk] = clr;
        end
        (* keep = "true" *) reg rv;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) rv <= 1'b0; else rv <= v1 && !x_clr_c[gk];
        assign v2_c[gk] = rv;
    end
    for (gb = 0; gb < 256; gb = gb + 1) begin : g_hbu
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) hbin[CB*gb +: CB] <= {CB{1'b0}};
            else if (x_clr_c[gb / (256 / NCL)]) hbin[CB*gb +: CB] <= {CB{1'b0}};
            else if (v2_c[gb / (256 / NCL)]) hbin[CB*gb +: CB] <= hbin_d[CB*gb +: CB];
        end
    end
`else
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) hbin <= {256*CB{1'b0}};
        else if (x_clr) hbin <= {256*CB{1'b0}};
        else if (v2) hbin <= hbin_d;
    end
`endif

    // group sums: 4-bin sums, then 16-bin sums
    reg [64*(CB+2)-1:0] gs1;
    integer j;
    generate if (HPIPE == 0) begin : g_sum0
        always @(posedge clk) begin
            for (j = 0; j < 64; j = j + 1)
                gs1[(CB+2)*j +: CB+2] <= {2'b00, hbin[CB*(4*j) +: CB]} + {2'b00, hbin[CB*(4*j+1) +: CB]}
                                        + {2'b00, hbin[CB*(4*j+2) +: CB]} + {2'b00, hbin[CB*(4*j+3) +: CB]};
            for (j = 0; j < 16; j = j + 1)
                gsum[(CB+4)*j +: CB+4] <= {2'b00, gs1[(CB+2)*(4*j) +: CB+2]} + {2'b00, gs1[(CB+2)*(4*j+1) +: CB+2]}
                                         + {2'b00, gs1[(CB+2)*(4*j+2) +: CB+2]} + {2'b00, gs1[(CB+2)*(4*j+3) +: CB+2]};
        end
    end else begin : g_sum1
        // pair sums (registered), then the group sums of the pairs, for both trees
        reg  [128*(CB+1)-1:0] p1;
        wire [128*(CB+1)-1:0] p1_d;
        wire [64*(CB+2)-1:0]  gs1_d;
        reg  [32*(CB+3)-1:0]  p2;
        wire [32*(CB+3)-1:0]  p2_d;
        wire [16*(CB+4)-1:0]  gsum_d;
        for (gb = 0; gb < 128; gb = gb + 1) begin : g_p1
            ot_hdc_ksadd_k #(.W(CB+1)) u_a (.a({1'b0, hbin[CB*(2*gb) +: CB]}), .b({1'b0, hbin[CB*(2*gb+1) +: CB]}),
                .cin(1'b0), .s(p1_d[(CB+1)*gb +: CB+1]), .cout());
        end
        for (gb = 0; gb < 64; gb = gb + 1) begin : g_g1
            ot_hdc_ksadd_k #(.W(CB+2)) u_a (.a({1'b0, p1[(CB+1)*(2*gb) +: CB+1]}), .b({1'b0, p1[(CB+1)*(2*gb+1) +: CB+1]}),
                .cin(1'b0), .s(gs1_d[(CB+2)*gb +: CB+2]), .cout());
        end
        for (gb = 0; gb < 32; gb = gb + 1) begin : g_p2
            ot_hdc_ksadd_k #(.W(CB+3)) u_a (.a({1'b0, gs1[(CB+2)*(2*gb) +: CB+2]}), .b({1'b0, gs1[(CB+2)*(2*gb+1) +: CB+2]}),
                .cin(1'b0), .s(p2_d[(CB+3)*gb +: CB+3]), .cout());
        end
        for (gb = 0; gb < 16; gb = gb + 1) begin : g_g2
            ot_hdc_ksadd_k #(.W(CB+4)) u_a (.a({1'b0, p2[(CB+3)*(2*gb) +: CB+3]}), .b({1'b0, p2[(CB+3)*(2*gb+1) +: CB+3]}),
                .cin(1'b0), .s(gsum_d[(CB+4)*gb +: CB+4]), .cout());
        end
        always @(posedge clk) begin p1 <= p1_d; gs1 <= gs1_d; p2 <= p2_d; gsum <= gsum_d; end
    end endgenerate
`ifdef OT_S81PH_SEL_FAN32
    // S81-TOPK FAN32: decoded constant-index group select.  Output bin o uses its own gsel copy, decoded to a
    // one-hot over the 16 groups, AND-OR over hbin[16 g + o]: = hbin[16*CB*gsel +: 16*CB] bin o (exact, same edge).
    wire [16*CB-1:0] gbin_d;
    genvar go, gg;
    for (go = 0; go < 16; go = go + 1) begin : g_gbo
        wire [3:0]       s = gsel_c[4*go +: 4];
        wire [16*CB-1:0] t;
        for (gg = 0; gg < 16; gg = gg + 1) begin : g_gg
            localparam [3:0] GI = gg;
            assign t[CB*gg +: CB] = hbin[CB*(16*gg + go) +: CB] & {CB{s == GI}};
        end
        reg [CB-1:0] o;
        integer m;
        always @(*) begin
            o = {CB{1'b0}};
            for (m = 0; m < 16; m = m + 1) o = o | t[CB*m +: CB];
        end
        assign gbin_d[CB*go +: CB] = o;
    end
    always @(posedge clk) gbin <= gbin_d;
`else
    always @(posedge clk) gbin <= hbin[16*CB*gsel +: 16*CB];
`endif
    assign busy = ((HPIPE != 0) && x_v) || v1 || v2;
endmodule
