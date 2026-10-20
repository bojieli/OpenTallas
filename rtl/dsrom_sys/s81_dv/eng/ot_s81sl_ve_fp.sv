`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81-VE4 (2026-10-20, tree S81.STA.OWN.3.1): NATIVE-32 ve-local binary32 add / multiply.  Bit for bit and cycle for
// cycle the shared 1.2 GHz units of rtl/hdc/ot_hdc_fp32_f12.sv at the ve calendar's latencies (adder LAT 4 = f12
// CUTS 6'b101010, multiplier LAT 5 = f12 CUTS 8'b01101010; tb rtl/dsrom_sys/s81_dv/eng/test/tb_s81sl_ve_fp.sv compares
// them against the shared units every edge); the register boundaries are the f12 ones, the logic between them is
// restructured so that NO driver (register or gate, inverters / buffers transparent) has more than 32 loads in the
// mapped netlist (r3 6ad9506a1: 1,919 roots > 32, max 131, all inside these units and their operand registers):
//   * every wide select is a REGISTER, replicated as kept copies (* keep *) that each drive one slice of the select
//     (the swap pick, the bypass code, the add / cancellation pick, the carry, the product's top bit, the subnormal
//     flags, the encode refusals) -- a comb select was the r3 root class (cmp 131, dab 72, carry 53, is_sub 35);
//     the logic BEHIND a copy is per slice, so its inputs differ per slice and synthesis cannot merge it back;
//   * every shifter is one-hot: the shift amount is decoded once into kept one-hot nets (each <= 28 AND loads) from a
//     two-level predecode (kept), never a log shifter whose amount bit fans out to every bit of every level
//     (alignment jam, cancellation shift, subnormal output shift, subnormal input normalise = leading-one one-hot);
//   * the multiplier operands are three kept copies each (one per third of the AND array: r3 a_n / b_n 52 loads);
//   * each unit takes TWO copies of each operand (a / a2, b / b2: kept registers at the producer); the second copy
//     feeds only the alignment (adder) / normalise (multiplier) one-hot shifter, the first everything else, so no
//     operand bit drives more than ~28 loads; y2 is a kept copy of the output register for producers of a2 / b2.
// Valid-only reset (as r3): the valid bit of each cut and valid_out reset, nothing else (y / err never observed
// without valid_out).  Reset loads: adder 4, multiplier 5.
// Needs rtl/hdc/ot_hdc_fastfp.sv (ot_hdc_lzc32) and rtl/hdc/ot_hdc_prefix.sv (ot_hdc_ksadd_k, ot_hdc_inc_k).
// ---------------------------------------------------------------------------------------------------------------------

// prefix OR, LSB first: o[i] = |x[i:0]; log levels kept (no long OR chain, every node <= 3 loads)
// r4b: keep_hierarchy (a kept WIRE is not an ABC cut: r4a showed ABC re-deriving consumers straight from the cone inputs)
(* keep_hierarchy *)
module ot_s81sl_ve_por #(parameter integer W = 28) (input wire [W-1:0] x, output wire [W-1:0] o);
    localparam integer L = (W <= 1) ? 1 : $clog2(W);
    (* keep *) wire [W-1:0] t [0:L];
    assign t[0] = x;
    genvar l, i;
    generate for (l = 0; l < L; l = l + 1) begin : g_l
        for (i = 0; i < W; i = i + 1) begin : g_b
            if (i >= (1 << l)) begin : g_c
                assign t[l + 1][i] = t[l][i] | t[l][i - (1 << l)];
            end else begin : g_p
                assign t[l + 1][i] = t[l][i];
            end
        end
    end endgenerate
    assign o = t[L];
endmodule

// one-hot decode of a small value through a kept two-level predecode: oh[s] = (v == s), s < N (r4b: hard boundary)
(* keep_hierarchy *)
module ot_s81sl_ve_ohdec #(parameter integer VW = 8, parameter integer N = 28) (
    input wire [VW-1:0] v, output wire [N-1:0] oh);
    localparam integer NH = (N + 3) / 4;
    (* keep *) wire [NH-1:0] hi;               // v[VW-1:2] == j
    (* keep *) wire [3:0]    lo;               // v[1:0] == m
    (* keep *) wire [N-1:0]  ohk;
    genvar j;
    generate
        for (j = 0; j < NH; j = j + 1) begin : g_h
            assign hi[j] = (v[VW-1:2] == j);
        end
        for (j = 0; j < 4; j = j + 1) begin : g_lo
            assign lo[j] = (v[1:0] == j);
        end
        for (j = 0; j < N; j = j + 1) begin : g_o
            assign ohk[j] = hi[j / 4] & lo[j % 4];
        end
    endgenerate
    assign oh = ohk;
endmodule

// jam alignment (= jam28f of the f12 adder, one-hot): r = far ? {27'd0, |val} : (val >> d) | {27'd0, |lost},
// val = {1'b0, man, 3'b000}; oh = one-hot of d (no line set when far: d >= 28)
// r4b: the shift is two one-hot stages in hard-boundary modules (by 4 * d[4:2], 7 lines, then by d[1:0], 4 lines): an
// operand bit drives <= 7 + 1 select terms (r4a single 28-line AND-OR: 33-36 loads on every operand copy), a select line
// <= 28; oh (the full one-hot) now only feeds the sticky terms.  far (d >= 28) clears the first stage's lines.
module ot_s81sl_ve_jam (input wire [23:0] man, input wire [27:0] oh, input wire [4:0] d, input wire far,
                        output wire [27:0] r);
    wire [27:0] val = {1'b0, man, 3'b000};
    wire [27:0] pv;                             // pv[i] = |val[i:0]
    ot_s81sl_ve_por #(.W(28)) u_p (.x(val), .o(pv));
    (* keep *) wire [27:0] stk;                 // stk[s] = oh[s] & |val[s-1:0]
    reg  [27:0] sh;
    integer s, j;
    assign stk[0] = 1'b0;
    genvar g;
    generate for (g = 1; g < 28; g = g + 1) begin : g_st
        assign stk[g] = oh[g] & pv[g - 1];
    end endgenerate
    wire [6:0] s4;
    wire [3:0] s1;
    wire [27:0] sh4, sh1;
    ot_s81sl_ve_sdec u_sd (.d(d), .far(far), .s4(s4), .s1(s1));
    ot_s81sl_ve_ohsh #(.W(28), .N(7), .STEP(4)) u_s4 (.x(val), .sel(s4), .y(sh4));
    ot_s81sl_ve_ohsh #(.W(28), .N(4), .STEP(1)) u_s1 (.x(sh4), .sel(s1), .y(sh1));
    always @* sh = sh1;
    assign r = {sh[27:1], sh[0] | (|stk) | (far & pv[27])};
endmodule

// =====================================================================================================================
// adder, LAT 4 (f12 CUTS 6'b101010): A decode / differences / compare / both alignments | B swap pick, sum and
// difference, sentinel leading-zero count | C add / cancellation pick, exponent adjust, round increment | D encode
// =====================================================================================================================
module ot_s81sl_ve_fadd (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [31:0] a, a2,                   // a2, b2: kept copies of a, b (the alignment operands)
    input  wire [31:0] b, b2,
    (* keep *) output reg [31:0] y,            // r4b: BOTH copies kept (opt_merge folds a non-kept twin into the kept one)
    (* keep *) output reg [31:0] y2,           // kept copy of y
    output reg  [1:0]  err,
    output reg         valid_out
);
    localparam [1:0] E_NONE = 2'd0, E_NONFINITE = 2'd1, E_OVERFLOW = 2'd2;
    genvar g;
    // ---- A ----------------------------------------------------------------------------------------------------------
    wire [7:0]  a_field = a[30:23], b_field = b[30:23];
    wire [7:0]  a_exp = (a_field == 8'd0) ? 8'd1 : a_field;
    wire [7:0]  b_exp = (b_field == 8'd0) ? 8'd1 : b_field;
    wire [23:0] a_man = {(a_field != 8'd0), a[22:0]};
    wire [23:0] b_man = {(b_field != 8'd0), b[22:0]};
    wire nonfinite = (a_field == 8'hff) || (b_field == 8'hff);
    wire a_zero = (a[30:0] == 31'd0);
    wire b_zero = (b[30:0] == 31'd0);
    (* keep *) wire [7:0] dab, dba;            // kept: the one-hot decoders read the differences, not the adder's p / g
    wire dab_c, dba_c;
    ot_hdc_ksadd_k #(.W(8)) u_dab (.a(a_exp), .b(~b_exp), .cin(1'b1), .s(dab), .cout(dab_c));
    // dba from the SECOND operand copies (same value): b - a and a - b share their propagate terms bit for bit, so from
    // one copy synthesis merges the two adders' kept p nets into one 49-load net
    wire [7:0] a2_exp = (a2[30:23] == 8'd0) ? 8'd1 : a2[30:23];
    wire [7:0] b2_exp = (b2[30:23] == 8'd0) ? 8'd1 : b2[30:23];
    ot_hdc_ksadd_k #(.W(8)) u_dba (.a(b2_exp), .b(~a2_exp), .cin(1'b1), .s(dba), .cout(dba_c));
    wire frac_c;
    wire [22:0] frac_s;
    ot_hdc_ksadd_k #(.W(23)) u_cmp (.a(a[22:0]), .b(~b[22:0]), .cin(1'b1), .s(frac_s), .cout(frac_c));
    wire cmp_c = (a_field == b_field) ? frac_c : !(a_field < b_field);     // |a| >= |b|
    // both alignments, one-hot, from the second operand copies (small_a: a shifted by dba, small_b: b by dab)
    wire [27:0] oh_ab, oh_ba;
    ot_s81sl_ve_ohdec #(.VW(8), .N(28)) u_oab (.v(dab), .oh(oh_ab));
    ot_s81sl_ve_ohdec #(.VW(8), .N(28)) u_oba (.v(dba), .oh(oh_ba));
    wire [23:0] a2_man = {(a2[30:23] != 8'd0), a2[22:0]};
    wire [23:0] b2_man = {(b2[30:23] != 8'd0), b2[22:0]};
    wire [27:0] small_a, small_b;
    ot_s81sl_ve_jam u_ja (.man(a2_man), .oh(oh_ba), .d(dba[4:0]), .far(dba >= 8'd28), .r(small_a));
    ot_s81sl_ve_jam u_jb (.man(b2_man), .oh(oh_ab), .d(dab[4:0]), .far(dab >= 8'd28), .r(small_b));
    // ---- R1 ---------------------------------------------------------------------------------------------------------
    reg x_v;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) x_v <= 1'b0;
        else x_v <= valid_in;
    (* keep *) reg [4:0] x_sw;                  // swap copies: 0 big[11:0], 1 big[23:12], 2 sml[13:0], 3 sml[27:14], 4 exp/sign/sentinel
    (* keep *) reg [3:0] x_nf, x_az, x_bz;      // bypass-code selects, one copy per code byte
    reg        x_byp, x_nfe, x_sub, x_as, x_bs;
    reg [7:0]  x_af, x_bf, x_aexp, x_bexp;
    reg [23:0] x_aman, x_bman;
    reg [27:0] x_sa, x_sb;
    always @(posedge clk) begin
        x_sw <= {5{!cmp_c}};
        x_nf <= {4{nonfinite}}; x_az <= {4{a_zero}}; x_bz <= {4{b_zero}};
        x_byp <= nonfinite || a_zero || b_zero; x_nfe <= nonfinite;
        x_sub <= a[31] ^ b[31]; x_as <= a[31]; x_bs <= b[31];
        x_af <= a_field; x_bf <= b_field; x_aexp <= a_exp; x_bexp <= b_exp;
        x_aman <= a_man; x_bman <= b_man; x_sa <= small_a; x_sb <= small_b;
    end
    // ---- B ----------------------------------------------------------------------------------------------------------
    (* keep *) wire [23:0] big;                // kept: the swap pick stays a mux in front of the adders (copy loads bounded)
    (* keep *) wire [27:0] sml;
    // r4b: each slice's pick is a hard-boundary mux (r4a: ABC folded the pick into both adders, x_sw 49-55 loads)
    ot_s81sl_ve_kmux #(.W(12)) u_bg0 (.s(x_sw[0]), .a(x_bman[11:0]),  .b(x_aman[11:0]),  .y(big[11:0]));
    ot_s81sl_ve_kmux #(.W(12)) u_bg1 (.s(x_sw[1]), .a(x_bman[23:12]), .b(x_aman[23:12]), .y(big[23:12]));
    ot_s81sl_ve_kmux #(.W(14)) u_sm0 (.s(x_sw[2]), .a(x_sa[13:0]),    .b(x_sb[13:0]),    .y(sml[13:0]));
    ot_s81sl_ve_kmux #(.W(14)) u_sm1 (.s(x_sw[3]), .a(x_sa[27:14]),   .b(x_sb[27:14]),   .y(sml[27:14]));
    (* keep *) wire [7:0] t_exp = x_sw[4] ? x_bexp : x_aexp;
    wire       t_sign = x_sw[4] ? x_bs : x_as;
    wire [31:0] code_a = {x_as, x_af, x_aman[22:0]}, code_b = {x_bs, x_bf, x_bman[22:0]};
    wire [31:0] t_code;
    generate for (g = 0; g < 4; g = g + 1) begin : g_bc
        assign t_code[8*g +: 8] = x_nf[g] ? 8'd0 : (x_az[g] ? (x_bz[g] ? 8'd0 : code_b[8*g +: 8]) : code_a[8*g +: 8]);
    end endgenerate
    wire [27:0] big28 = {1'b0, big, 3'b000};
    wire [27:0] sum_w, dif_w;
    wire sum_c, dif_c;
    ot_hdc_ksadd_k #(.W(28)) u_sum (.a(big28), .b(sml), .cin(1'b0), .s(sum_w), .cout(sum_c));
    ot_hdc_ksadd_k #(.W(28)) u_dif (.a(big28), .b(~sml), .cin(1'b1), .s(dif_w), .cout(dif_c));
    // sentinel = (exp - 1 <= 26) ? 1 << (27 - exp) : 0  (exp >= 1): bit k set iff exp == 27 - k
    wire [27:0] e_oh;
    ot_s81sl_ve_ohdec #(.VW(8), .N(28)) u_eoh (.v(t_exp), .oh(e_oh));
    wire [26:0] sentinel;
    generate for (g = 0; g < 27; g = g + 1) begin : g_sn
        assign sentinel[g] = e_oh[27 - g];
    end endgenerate
    wire [5:0] lz_w;
    ot_hdc_lzc32 u_lzc (.x({dif_w[26:0] | sentinel, 5'b11111}), .n(lz_w));
    // ---- R3 ---------------------------------------------------------------------------------------------------------
    reg w_v;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) w_v <= 1'b0;
        else w_v <= x_v;
    (* keep *) reg [3:0]  w_cy;                 // carry (sum[27]) copies, one per add_val slice
    (* keep *) reg [4:0]  w_sb;                 // sub copies: 0..3 value slices, 4 exponent / zero
    (* keep *) reg [27:0] w_difa, w_difb;       // difference copies: a slices 0, 1 + zero test; b slices 2, 3
    reg        w_byp, w_sign, w_carry_e;
    reg [1:0]  w_err;
    reg [31:0] w_code;
    reg [7:0]  w_exp;
    reg [27:0] w_sum;
    always @(posedge clk) begin
        w_cy <= {4{sum_w[27]}}; w_sb <= {5{x_sub}};
        w_difa <= dif_w; w_difb <= dif_w;
        w_byp <= x_byp; w_sign <= t_sign; w_err <= x_nfe ? E_NONFINITE : E_NONE; w_code <= t_code;
        w_exp <= t_exp; w_sum <= sum_w; w_carry_e <= sum_w[27];
    end
    (* keep *) reg [4:0] w_l0, w_l1, w_l2, w_l3, w_le;   // lz[4:0] per cancellation-shift slice, le: exponent
    always @(posedge clk) begin
        w_l0 <= lz_w[4:0]; w_l1 <= lz_w[4:0]; w_l2 <= lz_w[4:0]; w_l3 <= lz_w[4:0]; w_le <= lz_w[4:0];
    end
    // ---- C ----------------------------------------------------------------------------------------------------------
    // the add's renormalise (carry copies), the cancellation shift (one-hot per 7-bit slice), the exponent adjust
    wire [26:0] add_val, sub_val;
    wire [27:0] oh0, oh1, oh2, oh3;
    ot_s81sl_ve_ohdec #(.VW(5), .N(28)) u_l0 (.v(w_l0), .oh(oh0));
    ot_s81sl_ve_ohdec #(.VW(5), .N(28)) u_l1 (.v(w_l1), .oh(oh1));
    ot_s81sl_ve_ohdec #(.VW(5), .N(28)) u_l2 (.v(w_l2), .oh(oh2));
    ot_s81sl_ve_ohdec #(.VW(5), .N(28)) u_l3 (.v(w_l3), .oh(oh3));
    reg [26:0] shv;
    integer j, s;
    always @* begin
        shv = 27'd0;
        for (j = 0; j < 27; j = j + 1)
            for (s = 0; s <= j; s = s + 1)
                shv[j] = shv[j] | ((j < 7  ? oh0[s] : j < 14 ? oh1[s] : j < 21 ? oh2[s] : oh3[s]) &
                                   (j < 14 ? w_difa[j - s] : w_difb[j - s]));
    end
    assign sub_val = shv;
    wire [26:0] sum_n = {w_sum[27:2], w_sum[1] | w_sum[0]};
    generate for (g = 0; g < 27; g = g + 1) begin : g_av
        assign add_val[g] = w_cy[g / 7] ? sum_n[g] : w_sum[g];
    end endgenerate
    wire [7:0]  exp_sub, exp_add;
    wire exp_sub_c, exp_add_c;
    ot_hdc_ksadd_k #(.W(8)) u_esub (.a(w_exp), .b(~{3'd0, w_le}), .cin(1'b1), .s(exp_sub), .cout(exp_sub_c));
    ot_hdc_inc_k #(.W(8)) u_eadd (.a(w_exp), .inc(w_carry_e), .y(exp_add), .co(exp_add_c));
    wire [26:0] s2_val;
    generate for (g = 0; g < 27; g = g + 1) begin : g_sv
        assign s2_val[g] = w_sb[g / 7] ? sub_val[g] : add_val[g];
    end endgenerate
    wire [7:0] s2_exp = w_sb[4] ? exp_sub : exp_add;
    wire s2_zero = w_sb[4] && (w_difa == 28'd0);
    wire inc = s2_val[2] && ((|s2_val[1:0]) || s2_val[3]);
    wire [23:0] rnd_w;
    wire rnd_cw;
    ot_hdc_inc_k #(.W(24)) u_rnd (.a(s2_val[26:3]), .inc(inc), .y(rnd_w), .co(rnd_cw));
    // ---- R5 ---------------------------------------------------------------------------------------------------------
    reg u_v;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) u_v <= 1'b0;
        else u_v <= w_v;
    (* keep *) reg [3:0]  u_byp, u_zero, u_rc;  // one copy per output byte
    (* keep *) reg [7:0]  u_exp2, u_exp3;       // exponent copies for the field bytes (2: y[23], 3: y[30:24] + refusals)
    reg        u_sign;
    reg [1:0]  u_err;
    reg [31:0] u_code;
    reg [23:0] rnd;
    always @(posedge clk) begin
        u_byp <= {4{w_byp}}; u_zero <= {4{s2_zero}}; u_rc <= {4{rnd_cw}};
        u_exp2 <= s2_exp; u_exp3 <= s2_exp;
        u_sign <= w_sign; u_err <= w_err; u_code <= w_code; rnd <= rnd_w;
    end
    // ---- D: encode, subnormal, overflow, canonical zero (per output byte, from that byte's copies) --------------------
    // man = rnd_c ? {1, rnd[23:1]} : rnd; e = exp + rnd_c; subnormal = e == 1 && !man[23]; over = exp == ff || e >= 255
    // y = byp ? code_u : (zero || over) ? 0 : (code[30:0] == 0 ? 0 : code)
    wire [23:0] man_lo;                         // bytes 0, 1, 2 mantissa bits, each from its byte's carry copy
    generate for (g = 0; g < 23; g = g + 1) begin : g_mn
        assign man_lo[g] = u_rc[g / 8] ? rnd[g + 1] : rnd[g];
    end endgenerate
    assign man_lo[23] = u_rc[2] | rnd[23];
    // byte 2 holds y[23] (exponent field bit 0); byte 3 y[30:24] and the sign
    wire [8:0] e2 = {1'b0, u_exp2} + {8'd0, u_rc[2]};
    wire [8:0] e3 = {1'b0, u_exp3} + {8'd0, u_rc[3]};
    wire man23_3 = u_rc[3] | rnd[23];
    wire sub2 = (e2 == 9'd1) && !man_lo[23];
    wire sub3 = (e3 == 9'd1) && !man23_3;
    wire [7:0] fld2 = sub2 ? 8'd0 : e2[7:0];
    wire [7:0] fld3 = sub3 ? 8'd0 : e3[7:0];
    wire over_b [0:3];
    wire [8:0] eb [0:3];
    generate for (g = 0; g < 4; g = g + 1) begin : g_ov
        // each byte's own refusal from its own copies (exp copy shared by bytes 0..2 -> u_exp2, byte 3 -> u_exp3)
        wire [7:0] ex = (g == 3) ? u_exp3 : u_exp2;
        assign eb[g] = {1'b0, ex} + {8'd0, u_rc[g]};
        assign over_b[g] = (ex == 8'hff) || (eb[g] >= 9'd255);
    end endgenerate
    wire [31:0] code = {u_sign, fld3[7:1], fld2[0], man_lo[22:0]};
    // the canonical zero only clears the sign (code[30:0] == 0 already): nonzero test from byte 3's view
    wire [22:0] man3;
    generate for (g = 0; g < 23; g = g + 1) begin : g_m3
        assign man3[g] = u_rc[3] ? rnd[g + 1] : rnd[g];
    end endgenerate
    wire nz3 = (|man3) || (|fld3);
    wire [31:0] y_d;
    generate for (g = 0; g < 4; g = g + 1) begin : g_y
        wire kill = u_zero[g] || over_b[g];
        if (g < 3) begin : g_lo
            assign y_d[8*g +: 8] = u_byp[g] ? u_code[8*g +: 8] : (kill ? 8'd0 : code[8*g +: 8]);
        end else begin : g_hi
            assign y_d[30:24] = u_byp[3] ? u_code[30:24] : (kill ? 7'd0 : code[30:24]);
            assign y_d[31]    = u_byp[3] ? u_code[31]    : (!kill && u_sign && nz3);
        end
    end endgenerate
    wire [1:0] err_d = u_byp[3] ? u_err : ((u_zero[3] || !over_b[3]) ? E_NONE : E_OVERFLOW);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) valid_out <= 1'b0;
        else valid_out <= u_v;
    always @(posedge clk) begin y <= y_d; y2 <= y_d; err <= err_d; end
endmodule

// =====================================================================================================================
// multiplier, LAT 5 (f12 CUTS 8'b01101010): A decode, leading-one normalise, powers | B AND rows, five carry-save
// levels | C two carry-save levels, 48-bit add, floors and subnormal masks | D select, subnormal shift, round / sticky,
// both encode exponents | E round increment, encode
// =====================================================================================================================
module ot_s81sl_ve_fmul (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [31:0] a, a2,                   // a2, b2: kept copies of a, b (the normalise operands)
    input  wire [31:0] b, b2,
    (* keep *) output reg [31:0] y,            // r4b: BOTH copies kept (opt_merge folds a non-kept twin into the kept one)
    (* keep *) output reg [31:0] y2,           // kept copy of y
    output reg  [1:0]  err,
    output reg         valid_out
);
    localparam [1:0] E_NONE = 2'd0, E_NONFINITE = 2'd1, E_OVERFLOW = 2'd2;
    function automatic [95:0] csa;
        input [47:0] r0, r1, r2;
        begin
            csa[47:0] = r0 ^ r1 ^ r2;
            csa[95:48] = ((r0 & r1) | (r0 & r2) | (r1 & r2)) << 1;
        end
    endfunction
    genvar g, h;
    // ---- A ----------------------------------------------------------------------------------------------------------
    wire [7:0] a_field = a[30:23], b_field = b[30:23];
    wire nonfinite = (a_field == 8'hff) || (b_field == 8'hff);
    wire zero = (a[30:0] == 31'd0) || (b[30:0] == 31'd0);
    wire a_s = (a_field == 8'd0), b_s = (b_field == 8'd0);
    wire [5:0] a_cz, b_cz;                      // clz23 of the fraction (23 for a zero fraction)
    ot_hdc_lzc32 u_la (.x({a[22:0], 9'h1ff}), .n(a_cz));
    ot_hdc_lzc32 u_lb (.x({b[22:0], 9'h1ff}), .n(b_cz));
    // power = a_s ? -150 - clz23 : field - 150  ==  (a_s ? 0 : field) - 150 - (a_s ? clz23 : 0)
    wire [11:0] a_pe = {4'd0, a_field & {8{!a_s}}}, b_pe = {4'd0, b_field & {8{!b_s}}};
    wire [11:0] a_pz = {7'd0, a_cz[4:0] & {5{a_s}}}, b_pz = {7'd0, b_cz[4:0] & {5{b_s}}};
    wire signed [11:0] a_power = a_pe - 12'd150 - a_pz;
    wire signed [11:0] b_power = b_pe - 12'd150 - b_pz;
    // normalise (second copies): the significand with its hidden bit (!subnormal), shifted so its leading one sits at
    // bit 23 (= {frac, 0} << clz23 for a subnormal, {1, frac} for a normal number); leading one as a kept one-hot
    wire [23:0] a_n, b_n;
    // r4b: the hidden bit of the second copy twice, in hard-boundary instances (x[23] for the prefix chain and the low
    // 12 shift terms, hp for the high 12); !a_s (first copy) stays with the powers only
    wire a_h1, a_h2, b_h1, b_h2;
    ot_s81sl_ve_nz8 u_ah1 (.f(a2[30:23]), .y(a_h1));
    ot_s81sl_ve_nz8 u_ah2 (.f(a2[30:23]), .y(a_h2));
    ot_s81sl_ve_nz8 u_bh1 (.f(b2[30:23]), .y(b_h1));
    ot_s81sl_ve_nz8 u_bh2 (.f(b2[30:23]), .y(b_h2));
    ot_s81sl_ve_norm u_na (.x({a_h1, a2[22:0]}), .hp(a_h2), .y(a_n));
    ot_s81sl_ve_norm u_nb (.x({b_h1, b2[22:0]}), .hp(b_h2), .y(b_n));
    // ---- R1 ---------------------------------------------------------------------------------------------------------
    reg p_v;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) p_v <= 1'b0;
        else p_v <= valid_in;
    (* keep *) reg [23:0] p_a0, p_a1, p_a2, p_b0, p_b1, p_b2;   // one copy per third of the AND array
    reg        p_byp, p_sign;
    reg [1:0]  p_err;
    reg [11:0] p_ap, p_bp;
    always @(posedge clk) begin
        p_a0 <= a_n; p_a1 <= a_n; p_a2 <= a_n; p_b0 <= b_n; p_b1 <= b_n; p_b2 <= b_n;
        p_byp <= nonfinite || zero; p_err <= nonfinite ? E_NONFINITE : E_NONE; p_sign <= a[31] ^ b[31];
        p_ap <= a_power; p_bp <= b_power;
    end
    // ---- B: power sum, 24 AND rows (row i = a & b[i]; a copy by row third, b copy by column third), 5 CSA levels ---
    wire [11:0] power;
    wire power_c;
    ot_hdc_ksadd_k #(.W(12)) u_pw (.a(p_ap), .b(p_bp), .cin(1'b0), .s(power), .cout(power_c));
    wire [48*24-1:0] l0;
    generate for (g = 0; g < 24; g = g + 1) begin : g_pp
        wire [23:0] ac = (g < 8) ? p_a0 : (g < 16) ? p_a1 : p_a2;
        wire [23:0] pr;
        for (h = 0; h < 24; h = h + 1) begin : g_c
            wire bb = (h < 8) ? p_b0[g] : (h < 16) ? p_b1[g] : p_b2[g];
            assign pr[h] = ac[h] & bb;
        end
        assign l0[48*g +: 48] = {24'd0, pr} << g;
    end endgenerate
    wire [48*16-1:0] l1;
    wire [48*11-1:0] l2;
    wire [48*8-1:0]  rows;
    generate
        for (g = 0; g < 8; g = g + 1) begin : g_l1
            assign l1[96*g +: 96] = csa(l0[144*g +: 48], l0[144*g + 48 +: 48], l0[144*g + 96 +: 48]);
        end
        for (g = 0; g < 5; g = g + 1) begin : g_l2
            assign l2[96*g +: 96] = csa(l1[144*g +: 48], l1[144*g + 48 +: 48], l1[144*g + 96 +: 48]);
        end
        assign l2[480 +: 48] = l1[720 +: 48];
        for (g = 0; g < 3; g = g + 1) begin : g_l3
            assign rows[96*g +: 96] = csa(l2[144*g +: 48], l2[144*g + 48 +: 48], l2[144*g + 96 +: 48]);
        end
        assign rows[288 +: 96] = l2[432 +: 96];
    endgenerate
    wire [48*6-1:0] l4;
    wire [48*4-1:0] l5;
    generate
        for (g = 0; g < 2; g = g + 1) begin : g_l4
            assign l4[96*g +: 96] = csa(rows[144*g +: 48], rows[144*g + 48 +: 48], rows[144*g + 96 +: 48]);
        end
        assign l4[192 +: 96] = rows[288 +: 96];
        for (g = 0; g < 2; g = g + 1) begin : g_l5
            assign l5[96*g +: 96] = csa(l4[144*g +: 48], l4[144*g + 48 +: 48], l4[144*g + 96 +: 48]);
        end
    endgenerate
    // ---- R3 ---------------------------------------------------------------------------------------------------------
    reg r3_v;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) r3_v <= 1'b0;
        else r3_v <= p_v;
    reg        r3_byp, r3_sign;
    reg [1:0]  r3_err;
    reg [48*4-1:0] r3_l5;
    (* keep *) reg signed [11:0] r3_power, r3_pws;   // r4b: kept copies: floors (fl47 / fl46) | subnormal shift amount
    always @(posedge clk) begin
        r3_byp <= p_byp; r3_err <= p_err; r3_sign <= p_sign; r3_l5 <= l5; r3_power <= power; r3_pws <= power;
    end
    // ---- C: two carry-save levels, the 48-bit add; floors, subnormal shift amount and its masks (kept one-hot) -----
    wire [48*3-1:0] l6;
    wire [48*2-1:0] l7;
    assign l6[0 +: 96] = csa(r3_l5[0 +: 48], r3_l5[48 +: 48], r3_l5[96 +: 48]);
    assign l6[96 +: 48] = r3_l5[144 +: 48];
    assign l7 = csa(l6[0 +: 48], l6[48 +: 48], l6[96 +: 48]);
    wire [47:0] prod;
    wire unused_cout;
    ot_hdc_ksadd_k #(.W(48)) u_cpa (.a(l7[47:0]), .b(l7[95:48]), .cin(1'b0), .s(prod), .cout(unused_cout));
    wire signed [11:0] fl47 = r3_power + 12'sd47;
    wire signed [11:0] fl46 = r3_power + 12'sd46;
    wire signed [11:0] sh_sub = -(r3_pws + 12'sd149);
    wire [5:0] shc = (sh_sub > 12'sd63) ? 6'd63 : sh_sub[5:0];
    // E[s] = (shc == s), Gt[s] = (shc > s): m_round[k] = E[k + 1], m_sticky[k] = E[0] | Gt[k + 1] (the f12 masks:
    // k == shc - 1 and k < shc - 1 in 12 bits, i.e. every k when shc == 0)
    // r4b: the mask decode is a hard-boundary module from shc (r4a: ABC folded the clamp into the 49 GT terms, 36-43 loads)
    wire [48:0] EQ, GT;
    wire [47:0] MS;                             // m_sticky = E[0] | Gt[k + 1], formed inside u_md from two E[0] copies
    ot_s81sl_ve_mdec u_md (.shc(shc), .eq(EQ), .gt(GT), .ms(MS));
    // ---- R5 ---------------------------------------------------------------------------------------------------------
    reg s2_v;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) s2_v <= 1'b0;
        else s2_v <= r3_v;
    (* keep *) reg [47:0] s2_pa, s2_pb;         // product copies: a = subnormal shift + round / sticky, b = normal pick
`ifdef OT_S81_VE_LOADSAFE5
    localparam integer TOP_COPIES = 5, TOP_EXP = 4;
`else
    localparam integer TOP_COPIES = 4, TOP_EXP = 3;
`endif
    (* keep *) reg [TOP_COPIES-1:0] s2_top;
    (* keep *) reg [3:0] s2_s47, s2_s46;   // copies: 0..2 main bytes, 3 the rest
    reg        s2_byp, s2_sign;
    reg [1:0]  s2_err;
    reg signed [11:0] s2_fl47, s2_fl46;
    reg [47:0] s2_mr, s2_ms;
    reg        s2_e0;
    always @(posedge clk) begin
        s2_pa <= prod; s2_pb <= prod; s2_top <= {TOP_COPIES{prod[47]}};
        s2_s47 <= {4{fl47 < -12'sd126}}; s2_s46 <= {4{fl46 < -12'sd126}};
        s2_byp <= r3_byp; s2_err <= r3_err; s2_sign <= r3_sign; s2_fl47 <= fl47; s2_fl46 <= fl46;
        s2_mr <= EQ[48:1]; s2_ms <= MS; s2_e0 <= EQ[0];
    end
    // ---- D: select, subnormal shift (one-hot = the round mask, + shc == 0), round / sticky, both encode exponents ---
    // s_main[j] = prod[j + shc] = (shc == 0 & prod[j]) | OR_k (m_round[k] & prod[j + k + 1])
    reg [23:0] s_main;
    integer j, k;
    always @* begin
        for (j = 0; j < 24; j = j + 1) begin
            s_main[j] = s2_e0 & s2_pa[j];
            for (k = 0; k + j + 1 < 48; k = k + 1)
                s_main[j] = s_main[j] | (s2_mr[k] & s2_pa[j + k + 1]);
        end
    end
    wire s_rb = |(s2_pa & s2_mr);
    wire s_st = |(s2_pa & s2_ms);
    // main = top ? (sub47 ? s : n47) : (sub46 ? s : n46), every select a register copy
    wire [23:0] main;
    generate for (g = 0; g < 24; g = g + 1) begin : g_mn
        wire m47 = s2_s47[g / 8] ? s_main[g] : s2_pb[g + 24];
        wire m46 = s2_s46[g / 8] ? s_main[g] : s2_pb[g + 23];
        assign main[g] = s2_top[g / 8] ? m47 : m46;
    end endgenerate
    wire n_rb47 = s2_pb[23], n_rb46 = s2_pb[22];
    wire n_st47 = |s2_pb[22:0], n_st46 = |s2_pb[21:0];
    wire rb = s2_top[3] ? (s2_s47[3] ? s_rb : n_rb47) : (s2_s46[3] ? s_rb : n_rb46);
    wire st = s2_top[3] ? (s2_s47[3] ? s_st : n_st47) : (s2_s46[3] ? s_st : n_st46);
    wire is_sub = s2_top[3] ? s2_s47[3] : s2_s46[3];
    wire signed [11:0] f47p1 = s2_fl47 + 12'sd1, f46p1 = s2_fl46 + 12'sd1;
    wire [7:0]  fa47 = s2_fl47[7:0] + 8'd127, fb47 = f47p1[7:0] + 8'd127;
    wire [7:0]  fa46 = s2_fl46[7:0] + 8'd127, fb46 = f46p1[7:0] + 8'd127;
    wire        oa47 = s2_fl47 > 12'sd127, ob47 = f47p1 > 12'sd127;
    wire        oa46 = s2_fl46 > 12'sd127, ob46 = f46p1 > 12'sd127;
    wire [7:0]  fa = s2_top[TOP_EXP] ? fa47 : fa46, fb = s2_top[TOP_EXP] ? fb47 : fb46;
    wire        oa = s2_top[TOP_EXP] ? oa47 : oa46, ob = s2_top[TOP_EXP] ? ob47 : ob46;
    // ---- R6 ---------------------------------------------------------------------------------------------------------
    reg r_v;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) r_v <= 1'b0;
        else r_v <= s2_v;
    (* keep *) reg [3:0] r_byp, r_sub, r_oa, r_ob;  // one copy per output byte
    (* keep *) reg [7:0] r_fa2, r_fb2, r_fa3, r_fb3; // field copies for bytes 2 (y[23]) and 3 (y[30:24])
    reg        r_sign, r_inc;
    reg [1:0]  r_err;
    reg [23:0] r_main;
    always @(posedge clk) begin
        r_byp <= {4{s2_byp}}; r_sub <= {4{is_sub}}; r_oa <= {4{oa}}; r_ob <= {4{ob}};
        r_fa2 <= fa; r_fb2 <= fb; r_fa3 <= fa; r_fb3 <= fb;
        r_sign <= s2_sign; r_err <= s2_err; r_main <= main; r_inc <= rb && (st || main[0]);
    end
    // ---- E: round increment, encode (per output byte) -----------------------------------------------------------------
    // the round carry out (rnd_cw) only happens from all ones: rnd = 0 then, so man = {carry | rnd[23], rnd[22:0]} and a
    // subnormal's carry into bit 23 gives field {7'd0, rnd[23]} with rnd[22:0] = 0 -- no wide select on the comb carry
    wire [23:0] rnd;
    wire rnd_c;
    ot_hdc_inc_k #(.W(24)) u_rnd (.a(r_main), .inc(r_inc), .y(rnd), .co(rnd_c));
    wire [31:0] y_d;
    wire [7:0] fld2, fld3;
    wire c2 = !r_sub[2] && rnd_c, c3 = !r_sub[3] && rnd_c;
    assign fld2 = r_sub[2] ? {7'd0, rnd[23]} : (c2 ? r_fb2 : r_fa2);
    assign fld3 = r_sub[3] ? {7'd0, rnd[23]} : (c3 ? r_fb3 : r_fa3);
    wire [31:0] code = {r_sign, fld3[7:1], fld2[0], rnd[22:0]};
    wire nz = (|rnd[22:0]) || (|fld3);
    generate for (g = 0; g < 4; g = g + 1) begin : g_y
        wire cg = !r_sub[g] && rnd_c;
        wire kill = r_byp[g] || (!r_sub[g] && (cg ? r_ob[g] : r_oa[g]));
        if (g < 3) begin : g_lo
            assign y_d[8*g +: 8] = kill ? 8'd0 : code[8*g +: 8];
        end else begin : g_hi
            assign y_d[30:24] = kill ? 7'd0 : code[30:24];
            assign y_d[31]    = !kill && r_sign && nz;
        end
    end endgenerate
    wire over3 = !r_sub[3] && (c3 ? r_ob[3] : r_oa[3]);
    wire [1:0] err_d = r_byp[3] ? r_err : (over3 ? E_OVERFLOW : E_NONE);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) valid_out <= 1'b0;
        else valid_out <= r_v;
    always @(posedge clk) begin y <= y_d; y2 <= y_d; err <= err_d; end
endmodule

// leading-one normalise: y = x << (number of leading zeros of x), 24 bits (x = 0 -> 0); kept one-hot leading one.
// hp = x[23] computed from the other operand copy: the prefix chain reads hp, the 24 shift terms read x[23]
module ot_s81sl_ve_norm (input wire [23:0] x, input wire hp, output wire [23:0] y);
    wire [23:0] xr, pr;                         // xr = bit-reversed x; pr[i] = |xr[i:0] = |x[23:23-i]
    genvar i;
    assign xr[0] = x[23];
    generate for (i = 1; i < 24; i = i + 1) begin : g_r
        assign xr[i] = x[23 - i];
    end endgenerate
    ot_s81sl_ve_por #(.W(24)) u_p (.x(xr), .o(pr));
    (* keep *) wire [23:0] lead;                // lead[i]: the leading one is x[i]
    assign lead[23] = x[23];
    // r4b: the normal-number term (lead[23]) of output bits 12..23 reads hp (= x[23] from the other copy): r4a x[23] 33-39
`ifdef OT_S81_VE_LOADSAFE5
    // Nine low terms leave room for the prefix/data uses of x[23].
    // Fifteen high terms keep the independent hidden-bit driver below 32.
    localparam integer NORMAL_SPLIT = 9;
`else
    localparam integer NORMAL_SPLIT = 12;
`endif
    wire lead23_hi = hp;
    generate for (i = 0; i < 23; i = i + 1) begin : g_l
        assign lead[i] = x[i] & !pr[22 - i];    // pr[22 - i] = |x[23:i+1]
    end endgenerate
    reg [23:0] yr;
    integer j, k;
    always @* begin
        for (j = 0; j < 24; j = j + 1) begin
            yr[j] = 1'b0;
            for (k = 23 - j; k < 24; k = k + 1)   // leading one at k: y[j] = x[k - 23 + j]
                yr[j] = yr[j] | (((k == 23 && j >= NORMAL_SPLIT) ? lead23_hi : lead[k]) & x[k - 23 + j]);
        end
    end
    assign y = yr;
endmodule

module ot_s81sl_ve_qadd #(parameter integer LAT = 4) (
    input wire clk, input wire rst_n, input wire v, input wire [31:0] a, a2, b, b2,
    output wire [31:0] y, y2, output wire vo, output wire fault);
    wire [1:0] err;
    ot_s81sl_ve_fadd u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .a2(a2), .b(b), .b2(b2), .y(y), .y2(y2),
                        .err(err), .valid_out(vo));
    assign fault = vo && (err != 2'd0);
`ifndef SYNTHESIS
    initial if (LAT != 4) $error("ot_s81sl_ve_qadd: only LAT 4 (the ve calendar's adder)");
`endif
endmodule

module ot_s81sl_ve_qmul #(parameter integer LAT = 5) (
    input wire clk, input wire rst_n, input wire v, input wire [31:0] a, a2, b, b2,
    output wire [31:0] y, y2, output wire vo, output wire fault);
    wire [1:0] err;
    ot_s81sl_ve_fmul u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .a2(a2), .b(b), .b2(b2), .y(y), .y2(y2),
                        .err(err), .valid_out(vo));
    assign fault = vo && (err != 2'd0);
`ifndef SYNTHESIS
    initial if (LAT != 5) $error("ot_s81sl_ve_qmul: only LAT 5 (the ve calendar's multiplier)");
`endif
endmodule

// =====================================================================================================================
// r4b hard-boundary helpers (keep_hierarchy: ABC / opt_merge cannot fold logic across them, and a module attribute is
// copied to every $paramod derivative)
// =====================================================================================================================
// one-hot shift stage: y[j] = OR_g sel[g] & x[j + g * STEP] (x beyond W = 0)
(* keep_hierarchy *)
module ot_s81sl_ve_ohsh #(parameter integer W = 28, N = 7, STEP = 4) (
    input wire [W-1:0] x, input wire [N-1:0] sel, output reg [W-1:0] y);
    integer j, g;
    always @* begin
        y = {W{1'b0}};
        for (j = 0; j < W; j = j + 1)
            for (g = 0; g < N; g = g + 1)
                if (j + g * STEP < W) y[j] = y[j] | (sel[g] & x[j + g * STEP]);
    end
endmodule

// the jam's stage selects: s4[g] = !far & d[4:2] == g (g < 7: d < 28 when !far), s1[m] = d[1:0] == m
(* keep_hierarchy *)
module ot_s81sl_ve_sdec (input wire [4:0] d, input wire far, output wire [6:0] s4, output wire [3:0] s1);
    genvar g;
    generate
        for (g = 0; g < 7; g = g + 1) begin : g_4
            assign s4[g] = !far && (d[4:2] == g);
        end
        for (g = 0; g < 4; g = g + 1) begin : g_1
            assign s1[g] = (d[1:0] == g);
        end
    endgenerate
endmodule

// 2:1 pick (s ? a : b)
(* keep_hierarchy *)
module ot_s81sl_ve_kmux #(parameter integer W = 12) (input wire s, input wire [W-1:0] a, b, output wire [W-1:0] y);
    assign y = s ? a : b;
endmodule

// one 2-input AND (an enable copy: each instance is its own cell, so copies are never merged)
(* keep_hierarchy *)
module ot_s81sl_ve_kand (input wire a, b, output wire y);
    assign y = a & b;
endmodule

// subnormal masks: E[s] = (shc == s), Gt[s] = (shc > s) for s < 49, through the H / L predecode (each line <= 14 loads)
// (r4b: predecode and combine are separate hard-boundary modules: in one module ABC re-derived the 49 terms straight from
// shc, 49 loads per shc literal)
(* keep_hierarchy *)
module ot_s81sl_ve_mdec (input wire [5:0] shc, output wire [48:0] eq, gt, output wire [47:0] ms);
    wire [7:0] HE, HG, LE, LG;
    ot_s81sl_ve_mpre u_p (.shc(shc), .he(HE), .hg(HG), .le(LE), .lg(LG));
    ot_s81sl_ve_mcomb u_c (.he(HE), .hg(HG), .le(LE), .lg(LG), .eq(eq), .gt(gt));
    // ms[k] = E[0] | Gt[k + 1]: E[0] from two separate AND instances, one per half (r4c unit census: E[0] 49 loads)
    wire e0a, e0b;
    ot_s81sl_ve_kand u_e0a (.a(HE[0]), .b(LE[0]), .y(e0a));
    ot_s81sl_ve_kand u_e0b (.a(HE[0]), .b(LE[0]), .y(e0b));
    genvar k;
    generate for (k = 0; k < 48; k = k + 1) begin : g_ms
        assign ms[k] = (k < 24 ? e0a : e0b) | gt[k + 1];
    end endgenerate
endmodule

(* keep_hierarchy *)
module ot_s81sl_ve_mpre (input wire [5:0] shc, output wire [7:0] he, hg, le, lg);
    genvar g;
    generate for (g = 0; g < 8; g = g + 1) begin : g_pd
        assign he[g] = (shc[5:3] == g); assign hg[g] = (shc[5:3] > g);
        assign le[g] = (shc[2:0] == g); assign lg[g] = (shc[2:0] > g);
    end endgenerate
endmodule

(* keep_hierarchy *)
module ot_s81sl_ve_mcomb (input wire [7:0] he, hg, le, lg, output wire [48:0] eq, gt);
    wire [7:0] HE = he, HG = hg, LE = le, LG = lg;
    genvar g;
    generate for (g = 0; g < 49; g = g + 1) begin : g_eg
        assign eq[g] = HE[g / 8] & LE[g % 8];
        assign gt[g] = HG[g / 8] | (HE[g / 8] & LG[g % 8]);
    end endgenerate
endmodule

// |f (a hidden bit); separate instances stay separate cells
(* keep_hierarchy *)
module ot_s81sl_ve_nz8 (input wire [7:0] f, output wire y);
    assign y = |f;
endmodule
