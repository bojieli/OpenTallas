`timescale 1ns/1ps
// Default-off split-reset NC kernels. rst_y and rst_n must have identical phase/contract.
// 32 output-data reset pins separated from <=9 control reset pins; arithmetic and ages unchanged.
module ot_hdc_fp32_add_lat_ncr #(
    parameter integer LAT = 7       // only LAT 7 (cuts A, B, C, D + HSPLIT) exists in this variant
) (
    input  wire        clk,
    input  wire        rst_n,
    input wire rst_y,
    input  wire        valid_in,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output reg  [1:0]  err,
    output reg         valid_out
);
    generate if (LAT != 7) begin : g_bad_lat
        ot_hdc_fp32_add_lat_ncr_needs_LAT_7 u_trap ();
    end endgenerate
    localparam [1:0] E_NONE = 2'd0, E_OVERFLOW = 2'd2;

    // ---- A1 ----------------------------------------------------------------------------------------
    wire [7:0]  a_field = a[30:23];
    wire [7:0]  b_field = b[30:23];
    wire [7:0]  a_exp = (a_field == 8'd0) ? 8'd1 : a_field;
    wire [7:0]  b_exp = (b_field == 8'd0) ? 8'd1 : b_field;
    wire [23:0] a_man = {(a_field != 8'd0), a[22:0]};
    wire [23:0] b_man = {(b_field != 8'd0), b[22:0]};
    wire nonfinite = (a_field == 8'hff) || (b_field == 8'hff);
    wire a_zero = (a[30:0] == 31'd0);
    wire b_zero = (b[30:0] == 31'd0);
    wire bypass = nonfinite || a_zero || b_zero;
    wire [31:0] bypass_code = nonfinite ? 32'd0 : (a_zero ? (b_zero ? 32'd0 : b) : a);
    wire cmp_c;
    wire [30:0] cmp_s;
    ot_hdc_ksadd_k #(.W(31)) u_cmp (.a(a[30:0]), .b(~b[30:0]), .cin(1'b1), .s(cmp_s), .cout(cmp_c));
    wire [7:0] dab, dba;
    wire dab_c, dba_c;
    ot_hdc_ksadd_k #(.W(8)) u_dab (.a(a_exp), .b(~b_exp), .cin(1'b1), .s(dab), .cout(dab_c));
    ot_hdc_ksadd_k #(.W(8)) u_dba (.a(b_exp), .b(~a_exp), .cin(1'b1), .s(dba), .cout(dba_c));
    // A1 -> A2 cut (u_ca): the valid bit is the one reset flop, the rest plain data flops
    reg         x_v;
    reg         x_swap, x_byp, x_nf, x_sub, x_as, x_bs;
    reg  [31:0] x_code;
    reg  [7:0]  x_aexp, x_bexp, x_dab, x_dba;
    reg  [23:0] x_aman, x_bman;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) x_v <= 1'b0;
        else x_v <= valid_in;
    always @(posedge clk) begin
        x_swap <= !cmp_c; x_byp <= bypass; x_nf <= nonfinite; x_code <= bypass_code;
        x_sub <= a[31] ^ b[31]; x_as <= a[31]; x_bs <= b[31];
        x_aexp <= a_exp; x_bexp <= b_exp; x_aman <= a_man; x_bman <= b_man; x_dab <= dab; x_dba <= dba;
    end
    // ---- A2 ----------------------------------------------------------------------------------------
    function automatic [27:0] jam28;
        input [23:0] man;
        input [7:0]  d;
        reg [27:0] val, lost;
        begin
            val = {1'b0, man, 3'b000};
            if (d >= 8'd28) jam28 = {27'd0, |val};
            else begin
                lost = val & ~({28{1'b1}} << d[4:0]);
                jam28 = (val >> d[4:0]) | {27'd0, |lost};
            end
        end
    endfunction
    wire [27:0] small_a = jam28(x_aman, x_dba);
    wire [27:0] small_b = jam28(x_bman, x_dab);

    reg        s1_v, s1_byp, s1_sub, s1_sign, s1_nf;
    reg [31:0] s1_code;
    reg [7:0]  s1_exp;
    reg [23:0] s1_big;
    reg [26:0] s1_small;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s1_v <= 1'b0;
        else s1_v <= x_v;
    end
    wire [27:0] small_s = x_swap ? small_a : small_b;
    always @(posedge clk) begin
        s1_byp <= x_byp;
        s1_nf <= x_nf;
        s1_code <= x_code;
        s1_sub <= x_sub;
        s1_sign <= x_swap ? x_bs : x_as;
        s1_exp <= x_swap ? x_bexp : x_aexp;
        s1_big <= x_swap ? x_bman : x_aman;
`ifdef KVP3_MUT4
        s1_small <= {1'b0, small_s[25:0]};             // bench mutant 4 (must FAIL): a live bit dropped
`else
        s1_small <= small_s[26:0];
`endif
    end

    // ---- B1 ----------------------------------------------------------------------------------------
    wire [27:0] big28 = {1'b0, s1_big, 3'b000};
    wire [27:0] small28 = {1'b0, s1_small};
    wire [27:0] sum_w, dif_w;
    wire sum_c, dif_c;
    ot_hdc_ksadd_k #(.W(28)) u_sum (.a(big28), .b(small28), .cin(1'b0), .s(sum_w), .cout(sum_c));
    ot_hdc_ksadd_k #(.W(28)) u_dif (.a(big28), .b(~small28), .cin(1'b1), .s(dif_w), .cout(dif_c));
    // B1 -> B2 cut (u_cb)
    reg         t_v;
    reg         t_byp, t_sub, t_sign, t_nf;
    reg  [31:0] t_code;
    reg  [7:0]  t_exp;
    reg  [27:0] sum;
    reg  [26:1] t_dif;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) t_v <= 1'b0;
        else t_v <= s1_v;
    always @(posedge clk) begin
        t_byp <= s1_byp; t_sub <= s1_sub; t_sign <= s1_sign; t_nf <= s1_nf; t_code <= s1_code; t_exp <= s1_exp;
        sum <= sum_w; t_dif <= dif_w[26:1];
    end
    // ---- B2 ----------------------------------------------------------------------------------------
`ifdef KVP3_MUT1
    wire [26:0] dif = {1'b0, t_dif[25:1], sum[0]}; // mutant1: drop live high normalization bit; old LSB-only mutant passed300k
`else
    wire [26:0] dif = {t_dif, sum[0]};                 // dif_w[0] == sum_w[0] == s1_small[0]
`endif
    wire carry = sum[27];
    wire [26:0] add_val = carry ? {sum[27:2], sum[1] | sum[0]} : sum[26:0];
    wire [7:0]  room = t_exp - 8'd1;
    wire [26:0] sentinel = (room <= 8'd26) ? (27'd1 << (5'd26 - room[4:0])) : 27'd0;
    wire [5:0]  lz_w;
    ot_hdc_lzc32 u_lzc (.x({dif | sentinel, 5'b11111}), .n(lz_w));
    // HSPLIT: {t_exp, dif} for the pass-through from a kept second copy of the B1 -> B2 register (same edge, same value)
    wire [35:0] hq;
    ot_hdc_add_hcopy36 u_hc (.clk(clk), .d({s1_exp, dif_w}), .q(hq));
    wire [7:0]  p_exp = hq[35:28];
    wire [27:0] p_dif = hq[27:0];
    // B2a -> B2b cut (u_cd)
    reg         w_v;
    reg         w_byp, w_sub, w_sign, w_nf, w_carry;
    reg  [31:0] w_code;
    reg  [7:0]  w_exp;
    reg  [26:0] w_add;
    reg  [27:0] w_dif;
    reg  [4:0]  lz;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) w_v <= 1'b0;
        else w_v <= t_v;
    always @(posedge clk) begin
        w_byp <= t_byp; w_sub <= t_sub; w_sign <= t_sign; w_nf <= t_nf; w_code <= t_code; w_exp <= p_exp;
        w_add <= add_val; w_dif <= p_dif; lz <= lz_w[4:0]; w_carry <= carry;
    end
    wire [26:0] sub_val = w_dif[26:0] << lz[4:0];
    wire [7:0]  exp_sub, exp_add;
    wire exp_sub_c, exp_add_c;
    ot_hdc_ksadd_k #(.W(8)) u_esub (.a(w_exp), .b(~{3'd0, lz[4:0]}), .cin(1'b1), .s(exp_sub), .cout(exp_sub_c));
    ot_hdc_ksadd_k #(.W(8)) u_eadd (.a(w_exp), .b(8'd0), .cin(w_carry), .s(exp_add), .cout(exp_add_c));

    reg        s2_v, s2_byp, s2_sign, s2_zero, s2_nf;
    reg [31:0] s2_code;
    reg [7:0]  s2_exp;
    reg [26:0] s2_val;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s2_v <= 1'b0;
        else s2_v <= w_v;
    end
    always @(posedge clk) begin
        s2_byp <= w_byp; s2_nf <= w_nf; s2_code <= w_code; s2_sign <= w_sign;
        s2_zero <= w_sub && (w_dif == 28'd0);
        s2_exp <= w_sub ? exp_sub : exp_add;
        s2_val <= w_sub ? sub_val : w_add;
    end

    // ---- C1 ----------------------------------------------------------------------------------------
    wire inc = s2_val[2] && ((|s2_val[1:0]) || s2_val[3]);
    wire [23:0] rnd_w;
    wire rnd_cw;
    ot_hdc_ksadd_k #(.W(24)) u_rnd (.a(s2_val[26:3]), .b(24'd0), .cin(inc), .s(rnd_w), .cout(rnd_cw));
    // C1 -> C2 cut (u_cc)
    reg         u_v;
    reg         u_byp, u_zero, u_sign, u_nf, rnd_c;
    reg  [31:0] u_code;
    reg  [7:0]  u_exp;
    reg  [23:0] rnd;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) u_v <= 1'b0;
        else u_v <= s2_v;
    always @(posedge clk) begin
        u_byp <= s2_byp; u_zero <= s2_zero; u_sign <= s2_sign; u_nf <= s2_nf; u_code <= s2_code; u_exp <= s2_exp;
        rnd <= rnd_w; rnd_c <= rnd_cw;
    end
    // ---- C2 ----------------------------------------------------------------------------------------
    wire [23:0] man = rnd_c ? {1'b1, rnd[23:1]} : rnd;
    wire [8:0]  e = {1'b0, u_exp} + {8'd0, rnd_c};
    wire subnormal = (e == 9'd1) && !man[23];
    wire [31:0] code = {u_sign, subnormal ? 8'd0 : e[7:0], man[22:0]};
    wire over = (u_exp == 8'hff) || (e >= 9'd255);
    always @(posedge clk or negedge rst_y) begin
        if(!rst_y)y<=32'd0;
        else if(u_byp)y<=u_code;
        else if(u_zero || over)y<=32'd0;
        else y<=(code[30:0]==31'd0)?32'd0:code;
    end
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n)begin err<=E_NONE;valid_out<=1'b0;end
        else begin
            valid_out<=u_v;
`ifdef KVP3_MUT2
            if(u_byp)err<=E_NONE;
`else
            if(u_byp)err<={1'b0,u_nf};
`endif
            else if(u_zero)err<=E_NONE;
            else if(over)err<=E_OVERFLOW;
            else err<=E_NONE;
        end
    end
endmodule

module ot_qwen_nearhbm_prod_ncr (
    input  wire        clk,
    input  wire        rst_n,
    input wire rst_y,
    input  wire        valid_in,
    input  wire [15:0] a,            // BF16
    input  wire [7:0]  k,            // FP8 E4M3 (bias 7)
    output reg  [31:0] y,
    output reg         fault,
    output reg         valid_out
);
    wire        a_sub = (a[14:7] == 8'd0);
    wire [7:0]  sa = {!a_sub, a[6:0]};
    wire [9:0]  ea = a_sub ? 10'd1 : {2'd0, a[14:7]};
    wire        k_sub = (k[6:3] == 4'd0);
    wire [3:0]  sk = {!k_sub, k[2:0]};
    wire [9:0]  ek = k_sub ? 10'd1 : {6'd0, k[6:3]};
    wire        bad1 = (a[14:7] == 8'hFF) || (k[6:0] == 7'h7F);
    wire [9:0]  e1 = ea + ek + 10'd5;
    reg         v1, s1_sign, s1_bad;
    reg [11:0]  s1_p;
    reg [8:0]   s1_e9;
    wire [9:0]  s1_e = {1'b0, s1_e9};
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) v1 <= 1'b0; else v1 <= valid_in;
    end
    always @(posedge clk) begin
        s1_sign <= a[15] ^ k[7];
        s1_bad <= bad1;
        s1_p <= sa * sk;
`ifdef KVP3_MUT5
        s1_e9 <= {1'b0, e1[7:0]};                      // bench mutant 5 (must FAIL): a live exponent bit dropped
`else
        s1_e9 <= e1[8:0];
`endif
    end
    reg [3:0] lz;
    integer i;
    always @* begin
        lz = 4'd0;
        for (i = 0; i < 12; i = i + 1) if (s1_p[i]) lz = i[3:0];
    end
    wire [10:0] be = {1'b0, s1_e} + {7'd0, lz} - 11'd22;
    reg         v2, s2_bad, s2_zero, s2_sign, s2_ovf, s2_normal;
    reg [11:0]  s2_p;
    reg [7:0]   s2_be;
    reg [4:0]   s2_sh;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) v2 <= 1'b0; else v2 <= v1;
    end
    always @(posedge clk) begin
        s2_bad <= s1_bad;
        s2_sign <= s1_sign;
        s2_zero <= (s1_p == 12'd0);
        s2_p <= s1_p;
        s2_normal <= !be[10] && (be != 11'd0);
        s2_ovf <= !be[10] && (be >= 11'd255);
        s2_be <= be[7:0];
        s2_sh <= (!be[10] && (be != 11'd0)) ? (5'd23 - {1'b0, lz}) : s1_e[4:0];
    end
    wire [34:0] sh = {23'd0, s2_p} << s2_sh;
    reg         v3, s3_bad, s3_zero, s3_ovf;
    reg [31:0]  s3_y;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) v3 <= 1'b0; else v3 <= v2;
    end
    always @(posedge clk) begin
        s3_bad <= s2_bad;
        s3_zero <= s2_zero;
        s3_ovf <= s2_ovf;
        s3_y <= {s2_sign, s2_normal ? s2_be : 8'd0, sh[22:0]};
    end
    always @(posedge clk or negedge rst_y) begin
        if(!rst_y)y<=32'd0;
        else if(s3_bad || s3_ovf)y<=32'd0;
        else y<=s3_zero?32'd0:s3_y;
    end
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n)begin valid_out<=1'b0;fault<=1'b0;end
        else begin valid_out<=v3;fault<=(s3_bad || s3_ovf)?v3:1'b0;end
    end
endmodule
