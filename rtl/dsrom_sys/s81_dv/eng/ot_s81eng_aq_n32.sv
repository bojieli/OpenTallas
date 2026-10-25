`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81sl_aq12x (S81-TILES3 2026-10-17, vq-only fork of rtl/hdc/v41x/ot_dsrom_aq12.sv , blob 02945a744 on origin/main): the
// same FP8 activation quantiser, bit for bit, except that the 11-deep x wait line u_x is NOT inside the quantiser: the
// grid stage reads xg = xd, which the instantiating tile must drive with x delayed by 12 cycles (= s0_x delayed 11 = the
// original flop line's xg) on every cycle.  ot_s81sl_vq AQ_XMEM = 2 rebuilds it from the 256-b sub-beat stream in ONE
// 128x256 SRAM ring.  Forked (coordinator 0co 10-17) so the shared ot_dsrom_aq12 stays byte-identical with what the
// CLOSED su_norm / norm_split / hroot tiles bound.  Everything below the port list is the original text, minus u_x.
// ---------------------------------------------------------------------------------------------------------------------
// ---------------------------------------------------------------------------
// FP8 activation quantiser at 1.2 GHz (DS-ROM recovery lever su_norm): the FP8 path (fp4 = 0) of
// rtl/hdc/v41/ot_hdc_actquant.sv, bit for bit, re-staged for 0.833 ns at ASAP7 SS.  ot_hdc_actquant screens at
// 745 MHz (its 2-level compare stages, the ot_fp32_mul_pipe scale multiply and the per-element shift / round /
// encode stages each miss by 100-510 ps), so:
//   * the 32 -> 1 magnitude max is one compare level a stage (5 stages; the 1e-4 floor joins the last level as a
//     three-way select of parallel compares);
//   * the scale product amax * float32(1/448) is the 1.2 GHz f12 multiplier (ot_hdc_qmul_lat LAT 5 through
//     rtl/hdc/ot_hdc_fastfp_lat_f12.sv): both are binary32 RNE, and amax >= 1e-4 keeps the product normal
//     (>= 2.2e-7), where every RNE multiplier is the same function;
//   * the per-element grid exponent, the rounding shift and the encode are two stages each.
// Function (tools/hdc_golden_v41.quant_fp8 / qdq_fp8): amax = max(max|x|, 1e-4); e = ceil_log2(RN(amax / 448));
// codes E4M3 of x * 2^-e (RNE); y = codes * 2^e as BF16.  Nonfinite input raises `fault`.
// LATENCY 18 (vs 13): S0 | 5 max levels | 5 multiply | e | 2 grid | 2 round | 2 encode.
// ---------------------------------------------------------------------------
module ot_s81sl_aq12x_eng_n32 (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          rst_mul_early_n, // same reset origin, TWO release edges before rst_n
    input  wire [24:0]   rst_pair_n,
    input  wire          v,
    input  wire [1023:0] x,
    output reg           vo,
    output wire [24:0]   vo_pair,
    output reg  [255:0]  q,
    output reg  signed [9:0] e,
    output reg  [511:0]  y,
    output reg           fault,
    input  wire [1023:0] xd        // x delayed by 12 cycles (the wait line lives in the parent)
);
    localparam integer LATENCY = 18;
    localparam [30:0] FLOOR_FP8 = 31'h38d1b717;   // float32(1e-4)
    localparam [31:0] INV_448   = 32'h3b124925;   // float32(1/448)
    function automatic [30:0] mx(input [30:0] a, input [30:0] b);
        mx = (a >= b) ? a : b;
    endfunction

    wire [LATENCY:0] vl;
    ot_hdc_vline #(.D(LATENCY)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vl));
    for(genvar vg=0;vg<25;vg=vg+1)begin:g_vpair
        ot_s81eng_rr_validcap u_v(.ck(clk),.rn(rst_pair_n[vg]),.d(vl[LATENCY-1]),.q(vo_pair[vg]));
    end
    // elements wait from S0 to the grid stage (S0 + 5 + 5 + 1 = 11 registers)
    reg  [1023:0] s0_x;
    always @(posedge clk) s0_x <= x;
    wire [1023:0] xg = xd;      // the parent's wait line (was u_x: ot_hdc_delay W 1024 D 11 on s0_x)

    // -- S1..S4: 32 -> 2, one compare level a stage ---------------------------------------------
    reg [30:0] m1 [0:15];
    reg [30:0] m2 [0:7];
    reg [30:0] m3 [0:3];
    reg [30:0] m4 [0:1];
    reg        nf1, nf2, nf3, nf4, nf5;
    reg        nfx;
    always @(*) begin
        nfx = 1'b0;
        for (integer i = 0; i < 32; i = i + 1) nfx = nfx | (s0_x[32*i + 23 +: 8] == 8'hFF);
    end
    always @(posedge clk) begin
        for (integer i = 0; i < 16; i = i + 1) m1[i] <= mx(s0_x[64*i +: 31], s0_x[64*i + 32 +: 31]);
        for (integer i = 0; i < 8; i = i + 1)  m2[i] <= mx(m1[2*i], m1[2*i+1]);
        for (integer i = 0; i < 4; i = i + 1)  m3[i] <= mx(m2[2*i], m2[2*i+1]);
        for (integer i = 0; i < 2; i = i + 1)  m4[i] <= mx(m3[2*i], m3[2*i+1]);
        nf1 <= nfx; nf2 <= nf1; nf3 <= nf2; nf4 <= nf3; nf5 <= nf4;
    end
    // -- S5: max(m4[0], m4[1], floor): three parallel compares and a select -----------------------
    wire ab = m4[0] >= m4[1], af = m4[0] >= FLOOR_FP8, bf = m4[1] >= FLOOR_FP8;
`ifdef OT_S81ENG_RR_MUL_N32
    // STW-S81-COLLB-2 10-21: the S5 amax capture moves INTO the multiplier's own input cut (CUTS bit 0 = 1), same edge:
    // the former kept amaxbit flops each fed the multiplier's whole combinational front end (lzc32 + two norm12
    // shifters + zero/nonfinite + the k0 capture), 30..34 loads per bit in the kit flow (gate census: g_amax[22] 34).
    // With K0 = 1 the select output is captured once by u_k0 (lzc/zero/nonfinite precomputed before the edge) and the
    // normalisation becomes the staged shift chain -> fan-out bounded by construction.  Function and cycle unchanged:
    // amax_next enters at S5 with vl[5], one fewer external register + one more internal cut = the same output edge.
    wire[30:0]amax_next=(ab&&af)?m4[0]:(!ab&&bf)?m4[1]:FLOOR_FP8;
`else
    reg[30:0]amax;
    always @(posedge clk)amax<=(ab&&af)?m4[0]:(!ab&&bf)?m4[1]:FLOOR_FP8;
`endif

    // -- S6..S10: amax * (1/448) ----------------------------------------------------------------
    wire [31:0] prod;
    wire        pfault;
`ifdef OT_S81ENG_RR_MUL_N32
    // Internal two-edge reset forest reconstitutes exactly the original consumer release edge.
    wire [1:0] s_err; wire s_vo;
    ot_s81dv_fp32_mul_f12_n32 #(.CUTS(8'b01101011)) u_scale (.clk(clk), .rst_n(rst_mul_early_n), .valid_in(vl[5]),
        .a({1'b0, amax_next}), .b(INV_448), .y(prod), .err(s_err), .valid_out(s_vo));
    assign pfault = s_vo && (s_err != 2'd0);
`else
    ot_hdc_qmul_lat #(5) u_scale (clk, rst_n, vl[6], {1'b0, amax}, INV_448, prod, pfault);
`endif
    wire nf10;
    ot_hdc_delay #(.W(1), .D(5)) u_nf (.clk(clk), .rst_n(rst_n), .d(nf5), .q(nf10));

    // -- S11: e = ceil_log2(prod) -----------------------------------------------------------------
    // also e + 127 and e + 121, so S12's two exponent differences are one subtract each, in parallel
    reg signed [9:0]  s11_e;
    wire signed[10:0] s11_ep_c[0:7],s11_dm_c[0:7];
    // LEC 10-25: declared BEFORE the g_ec instances (else implicit undriven nets -> TIELO exponent regs)
    wire [8:0] ce = {1'b0, prod[30:23]} + {8'd0, (prod[22:0] != 23'd0)};     // ceil_log2 + 127
    wire [10:0] ep_next = {2'b00,ce};
    wire [10:0] dm_next = $signed({2'b00,ce}) - 11'sd6;
    for(genvar eg=0;eg<8;eg=eg+1)begin:g_ec
        ot_s81eng_aq_exp u_e(.clk(clk),.ep_next(ep_next),.dm_next(dm_next),.ep(s11_ep_c[eg]),.dm(s11_dm_c[eg]));
    end
    reg               s11_nf;
    always @(posedge clk) begin
        s11_e <= $signed({1'b0, ce}) - 10'sd127;
        s11_nf <= nf10 | pfault;
    end

    // -- S12: per-element exponent difference dd = -6 - (exp(x) - e) ----------------------------------
    reg signed [10:0] s12_ev [0:31];
    reg signed [10:0] s12_dd [0:31];
    reg [23:0]        s12_sig [0:31];
    reg [31:0]        s12_sgn;
    reg signed [9:0]  s12_e;
    reg               s12_nf;
    reg [7:0]         fld;
    reg signed [10:0] ev;   // max(fld, 1)
    always @(posedge clk) begin
        s12_e <= s11_e; s12_nf <= s11_nf;
        for (integer i = 0; i < 32; i = i + 1) begin
            fld = xg[32*i + 23 +: 8];
            //: ev = exp(x) - e with exp(x) = max(fld, 1) - 127;  dd = -6 - ev = (e + 121) - max(fld, 1)
            ev = $signed({3'b000, (fld == 8'd0) ? 8'd1 : fld});
            s12_ev[i] <= ev - s11_ep_c[i/4];
            s12_dd[i] <= s11_dm_c[i/4] - ev;
            s12_sig[i] <= {(fld != 8'd0), xg[32*i +: 23]};
            s12_sgn[i] <= xg[32*i + 31] && (xg[32*i +: 31] != 31'd0);
        end
    end
    // -- S13: grid exponent and shift ------------------------------------------------------------------
    reg [23:0]       s13_sig [0:31];
    reg [4:0]        s13_rs [0:31];
    reg signed [4:0] s13_g [0:31];
    reg [31:0]       s13_sgn;
    reg signed [9:0] s13_e;
    reg              s13_nf;
    always @(posedge clk) begin
        s13_e <= s12_e; s13_nf <= s12_nf; s13_sgn <= s12_sgn;
        for (integer i = 0; i < 32; i = i + 1) begin
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
    reg [23:0]       s14_tq [0:31];
    reg [31:0]       s14_gd, s14_st, s14_sgn;
    reg signed [4:0] s14_g [0:31];
    reg signed [9:0] s14_e;
    reg              s14_nf;
    reg [50:0]       wide;
    always @(posedge clk) begin
        s14_e <= s13_e; s14_nf <= s13_nf; s14_sgn <= s13_sgn;
        for (integer i = 0; i < 32; i = i + 1) begin
            wide = {s13_sig[i], 27'd0} >> s13_rs[i];
            s14_tq[i] <= wide[50:27];
            s14_gd[i] <= wide[26];
            s14_st[i] <= (wide[25:0] != 26'd0);
            s14_g[i] <= s13_g[i];
        end
    end
    // -- S15: round to the grid -------------------------------------------------------------------------
    reg [4:0]        s15_c [0:31];
    reg signed [4:0] s15_g [0:31];
    reg [31:0]       s15_sgn;
    reg signed [9:0] s15_e;
    reg              s15_nf;
    always @(posedge clk) begin
        s15_e <= s14_e; s15_nf <= s14_nf; s15_sgn <= s14_sgn;
        for (integer i = 0; i < 32; i = i + 1) begin
            s15_c[i] <= s14_tq[i][4:0] + {4'd0, s14_gd[i] & (s14_st[i] | s14_tq[i][0])};
            s15_g[i] <= s14_g[i];
        end
    end
    // -- S16: encode terms ------------------------------------------------------------------------------
    reg [4:0]         s16_c [0:31];
    reg [3:0]         s16_g4 [0:31];
    reg signed [11:0] s16_be [0:31];
    reg [7:0]         s16_cn [0:31];
    reg [6:0]         s16_sub [0:31];
    reg [31:0]        s16_sgn;
    reg signed [9:0]  s16_e;
    reg               s16_nf;
    reg [2:0]         p;
    reg [4:0]         c;
    reg signed [11:0] shs;
    always @(posedge clk) begin
        s16_e <= s15_e; s16_nf <= s15_nf; s16_sgn <= s15_sgn;
        for (integer i = 0; i < 32; i = i + 1) begin
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
        for (integer i = 0; i < 32; i = i + 1) begin
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

(* keep_hierarchy = 1 *)module ot_s81eng_aq_exp(input wire clk,input wire[10:0] ep_next,dm_next,output reg[10:0] ep,dm);
 always @(posedge clk)begin ep<=ep_next;dm<=dm_next;end
endmodule

// A real captured field bit, used by its original multiplier input position.
(* keep_hierarchy=1 *)module ot_s81eng_rr_amaxbit(input wire ck,d,output reg q);
 always @(posedge ck)q<=d;
endmodule
