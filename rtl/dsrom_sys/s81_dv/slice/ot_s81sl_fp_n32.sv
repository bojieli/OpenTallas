`timescale 1ns/1ps
// Explicit S81 VS-only native consumer partition. Original shared FP files/defaults unchanged.
module ot_s81sl_fp_cut #(parameter integer W = 2, parameter integer CUT = 0) (
    input  wire clk, input wire rst_n, input wire [W-1:0] d, output wire [W-1:0] q
);
    generate if (CUT) begin : g_r
        reg         v;
        reg [W-2:0] r;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) v <= 1'b0;
            else v <= d[W-1];
        end
        always @(posedge clk) r <= d[W-2:0];
        assign q = {v, r};
    end else begin : g_w
        assign q = d;
    end endgenerate
endmodule

module ot_s81sl_fp_add_n32 #(
    parameter integer CUTS = 7'b1101011
) (
    input  wire        clk,
    input  wire [5:0]  rst_n,
    input  wire        valid_in,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output reg  [1:0]  err,
    output reg         valid_out
);
    localparam [1:0] E_NONE = 2'd0, E_NONFINITE = 2'd1, E_OVERFLOW = 2'd2;
    localparam integer K0 = CUTS % 2, K1 = (CUTS / 2) % 2, K2 = (CUTS / 4) % 2, K3 = (CUTS / 8) % 2,
                       K4 = (CUTS / 16) % 2, K5 = (CUTS / 32) % 2, K6 = (CUTS / 64) % 2;

    // ---- decode, exponent differences (bit 6: cut here, the magnitude compare after it); magnitude compare ----------------------------------------------
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
    wire [31:0] bypass_code;
    for(genvar g=0;g<4;g=g+1)begin:g_bypass
      ot_s81sl_fp_bypass #(.LO(8*g)) u_bp(.a(a),.b(b),.y(bypass_code[8*g+:8]));
    end
    wire [7:0] dab, dba;
    wire dab_c, dba_c;
    ot_hdc_ksadd_k #(.W(8)) u_dab (.a(a_exp), .b(~b_exp), .cin(1'b1), .s(dab), .cout(dab_c));
    ot_hdc_ksadd_k #(.W(8)) u_dba (.a(b_exp), .b(~a_exp), .cin(1'b1), .s(dba), .cout(dba_c));
    wire [5:0] g6, g0;                         // {valid, f_eq, f_lt, -, dab >= 28, dba >= 28}
    ot_s81sl_fp_cut #(.W(6), .CUT(K6)) u_g6 (.clk(clk), .rst_n(rst_n[0]),
        .d({valid_in, a_field == b_field, a_field < b_field, 1'b0, dab >= 8'd28, dba >= 8'd28}), .q(g6));
    localparam integer WA6 = 1 + 1 + 2 + 32 + 1 + 1 + 1 + 8 + 8 + 24 + 24 + 8 + 8 + 31 + 31;
    wire [WA6-1:0] q6;
    ot_s81sl_fp_cut #(.W(WA6), .CUT(K6)) u_k6 (.clk(clk), .rst_n(rst_n[0]),
        .d({valid_in, bypass, (nonfinite ? E_NONFINITE : E_NONE), bypass_code, a[31] ^ b[31], a[31], b[31],
            a_exp, b_exp, a_man, b_man, dab, dba, a[30:0], b[30:0]}), .q(q6));
    wire [30:0] c_a = q6[61:31], c_b = q6[30:0];
    // the magnitude order of the encodings (swap = |b| > |a|) split at the exponent field: the field order is decided
    // beside the exponent differences (f_lt, f_eq, carried in g6 / g0), the fraction order after the cut; the same
    // predicate as the 31-bit compare of add_lat (the lane's compare + swap stage was 2-13 ps over 0.833 ns)
    wire frac_c;
    wire [22:0] frac_s;
    ot_hdc_ksadd_k #(.W(23)) u_cmp (.a(c_a[22:0]), .b(~c_b[22:0]), .cin(1'b1), .s(frac_s), .cout(frac_c));
    wire cmp_c = g6[4] ? frac_c : !g6[3];          // a >= b
    localparam integer WA = 1 + 1 + 1 + 2 + 32 + 1 + 1 + 1 + 8 + 8 + 24 + 24 + 8 + 8;
    wire [WA-1:0] qa;
    ot_s81sl_fp_cut #(.W(WA), .CUT(K0)) u_k0 (.clk(clk), .rst_n(rst_n[0]),
        .d({q6[WA6-1], !cmp_c, q6[WA6-2:62]}), .q(qa));
    wire        x_v, x_swap, x_byp, x_sub, x_as, x_bs;
    wire [1:0]  x_err;
    wire [31:0] x_code;
    wire [7:0]  x_aexp, x_bexp, x_dab, x_dba;
    wire [23:0] x_aman, x_bman;
    assign {x_v, x_swap, x_byp, x_err, x_code, x_sub, x_as, x_bs, x_aexp, x_bexp, x_aman, x_bman, x_dab, x_dba} = qa;
    // ---- both alignments, the swap pick -------------------------------------------------------------
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
    // the shifted-out-entirely flags (d >= 28), decided beside the exponent differences and carried through the cuts
    // (the stage after cut 6 was 4 ps over 0.833 ns in the lane with the compares in it)

    function automatic [27:0] jam28f;
        input [23:0] man;
        input [4:0]  d;
        input        far;
        reg [27:0] val, lost;
        begin
            val = {1'b0, man, 3'b000};
            if (far) jam28f = {27'd0, |val};
            else begin
                lost = val & ~({28{1'b1}} << d);
                jam28f = (val >> d) | {27'd0, |lost};
            end
        end
    endfunction
    ot_s81sl_fp_cut #(.W(6), .CUT(K0)) u_g0 (.clk(clk), .rst_n(rst_n[0]), .d(g6), .q(g0));
    wire [7:0] swap_cp;
    ot_s81sl_fp_copy #(.W(1),.N(8),.CUT(K0)) u_swap_cp(.clk(clk),.d(!cmp_c),.q(swap_cp));
    wire [7:0] pick_exp; wire [23:0] pick_big; wire [27:0] pick_small;
    ot_s81sl_fp_mux #(.W(8)) u_pick_exp(.s(swap_cp[0]),.a(x_bexp),.b(x_aexp),.y(pick_exp));
    for(genvar g=0;g<3;g=g+1)begin:g_pick_big
      ot_s81sl_fp_mux #(.W(8)) u_pick(.s(swap_cp[1+g]),.a(x_bman[8*g+:8]),.b(x_aman[8*g+:8]),.y(pick_big[8*g+:8]));
    end
    for(genvar g=0;g<4;g=g+1)begin:g_pick_small
      localparam integer W=(g==3)?4:8;
      ot_s81sl_fp_mux #(.W(W)) u_pick(.s(swap_cp[4+g]),.a(small_a[8*g+:W]),.b(small_b[8*g+:W]),.y(pick_small[8*g+:W]));
    end
    wire [27:0] small_a,small_b;
    ot_s81sl_fp_jam28 u_ja(.clk(clk),.man(x_aman),.raw_count(q6[66:62]),.raw_far(g6[0]),.y(small_a));
    ot_s81sl_fp_jam28 u_jb(.clk(clk),.man(x_bman),.raw_count(q6[74:70]),.raw_far(g6[1]),.y(small_b));
    localparam integer W1 = 1 + 1 + 1 + 1 + 2 + 32 + 8 + 24 + 28;
    wire [W1-1:0] q1;
    ot_s81sl_fp_cut #(.W(W1), .CUT(K1)) u_k1 (.clk(clk), .rst_n(rst_n[0]),
        .d({x_v, x_byp, x_sub, x_swap ? x_bs : x_as, x_err, x_code, pick_exp,
            pick_big, pick_small}), .q(q1));
    wire        s1_v, s1_byp, s1_sub, s1_sign;
    wire [1:0]  s1_err;
    wire [31:0] s1_code;
    wire [7:0]  s1_exp;
    wire [23:0] s1_big;
    wire [27:0] s1_small;
    assign {s1_v, s1_byp, s1_sub, s1_sign, s1_err, s1_code, s1_exp, s1_big, s1_small} = q1;
    // ---- the sum and the difference ------------------------------------------------------------------
    wire [27:0] big28 = {1'b0, s1_big, 3'b000};
    wire [27:0] sum_w, dif_w;
    wire sum_c, dif_c;
    ot_hdc_ksadd_k #(.W(28)) u_sum (.a(big28), .b(s1_small), .cin(1'b0), .s(sum_w), .cout(sum_c));
    // the difference adder reads its own kept copy of the stage-1 operands (same edge as u_k1), stored inverted so it is
    // never merged back into u_k1: the sum adder / add picks and the difference adder no longer share one 34-36 load
    // register per operand bit
    wire [51:0] k1n;
    ot_s81sl_fp_copy #(.W(52),.N(1),.CUT(K1)) u_k1d(.clk(clk),.d(~{pick_big,pick_small}),.q(k1n));
    wire [27:0] big28d = {1'b0, ~k1n[51:28], 3'b000};
    ot_hdc_ksadd_k #(.W(28)) u_dif (.a(big28d), .b(k1n[27:0]), .cin(1'b1), .s(dif_w), .cout(dif_c));
    localparam integer W2 = 1 + 1 + 1 + 1 + 2 + 32 + 8 + 28 + 28;
    wire [W2-1:0] q2;
    ot_s81sl_fp_cut #(.W(W2), .CUT(K2)) u_k2 (.clk(clk), .rst_n(rst_n[0]),
        .d({s1_v, s1_byp, s1_sub, s1_sign, s1_err, s1_code, s1_exp, sum_w, dif_w}), .q(q2));
    wire        t_v, t_byp, t_sub, t_sign;
    wire [1:0]  t_err;
    wire [31:0] t_code;
    wire [7:0]  t_exp;
    wire [27:0] sum, dif;
    assign {t_v, t_byp, t_sub, t_sign, t_err, t_code, t_exp, sum, dif} = q2;
    // ---- the add's renormalise; the sentinel leading-zero count ------------------------------------------
    wire carry = sum[27];
    wire[26:0] add_val;
    for(genvar g=0;g<7;g=g+1)begin:g_add_val
      localparam integer W=(g==6)?3:4;
      ot_s81sl_fp_add_pick #(.LO(4*g),.W(W)) u_p(.a(big28),.b(s1_small),.sum(sum),.y(add_val[4*g+:W]));
    end
    wire [7:0]  room = t_exp - 8'd1;
    wire [26:0] sentinel = (room <= 8'd26) ? (27'd1 << (5'd26 - room[4:0])) : 27'd0;
    wire [5:0]  lz_w;
    ot_hdc_lzc32 u_lzc (.x({dif[26:0] | sentinel, 5'b11111}), .n(lz_w));
    localparam integer W3 = 1 + 1 + 1 + 1 + 2 + 32 + 8 + 27 + 28 + 6 + 1;
    wire [W3-1:0] q3;
    ot_s81sl_fp_cut #(.W(W3), .CUT(K3)) u_k3 (.clk(clk), .rst_n(rst_n[0]),
        .d({t_v, t_byp, t_sub, t_sign, t_err, t_code, t_exp, add_val, dif, lz_w, carry}), .q(q3));
    wire        w_v, w_byp, w_sub, w_sign, w_carry;
    wire [1:0]  w_err;
    wire [31:0] w_code;
    wire [7:0]  w_exp;
    wire [26:0] w_add;
    wire [27:0] w_dif;
    wire [5:0]  lz;
    assign {w_v, w_byp, w_sub, w_sign, w_err, w_code, w_exp, w_add, w_dif, lz, w_carry} = q3;
    // ---- the cancellation shift, the exponent adjust ------------------------------------------------------
    wire [26:0] sub_val;
    ot_s81sl_fp_shift_chain #(.IW(27),.CW(5),.LEFT(1),.CUT(K3)) u_sub_shift(
      .clk(clk),.x(w_dif[26:0]),.raw_count(lz_w[4:0]),.y(sub_val));
    wire [7:0]  exp_sub, exp_add;
    wire exp_sub_c, exp_add_c;
    ot_hdc_ksadd_k #(.W(8)) u_esub (.a(w_exp), .b(~{3'd0, lz[4:0]}), .cin(1'b1), .s(exp_sub), .cout(exp_sub_c));
    ot_hdc_inc_k #(.W(8)) u_eadd (.a(w_exp), .inc(w_carry), .y(exp_add), .co(exp_add_c));
    localparam integer W4 = 1 + 1 + 1 + 1 + 2 + 32 + 8 + 27;
    wire [W4-1:0] q4;
    wire[7:0] sub_cp;
    ot_s81sl_fp_copy #(.W(1),.N(8),.CUT(K3)) u_sub_cp(.clk(clk),.d(t_sub),.q(sub_cp));
    wire[7:0] pick_ex;wire[26:0] pick_val;
    ot_s81sl_fp_mux #(.W(8)) u_ex(.s(sub_cp[0]),.a(exp_sub),.b(exp_add),.y(pick_ex));
    for(genvar g=0;g<7;g=g+1)begin:g_val
      localparam integer W=(g==6)?3:4;
      ot_s81sl_fp_mux #(.W(W)) u_p(.s(sub_cp[g+1]),.a(sub_val[4*g+:W]),.b(w_add[4*g+:W]),.y(pick_val[4*g+:W]));
    end
    ot_s81sl_fp_cut #(.W(W4), .CUT(K4)) u_k4 (.clk(clk), .rst_n(rst_n[0]),
        .d({w_v, w_byp, w_sign, w_sub && (w_dif == 28'd0), w_err, w_code, pick_ex,
            pick_val}), .q(q4));
    wire        s2_v, s2_byp, s2_sign, s2_zero;
    wire [1:0]  s2_err;
    wire [31:0] s2_code;
    wire [7:0]  s2_exp;
    wire [26:0] s2_val;
    assign {s2_v, s2_byp, s2_sign, s2_zero, s2_err, s2_code, s2_exp, s2_val} = q4;
    // ---- round increment ----------------------------------------------------------------------------------
    wire inc = s2_val[2] && ((|s2_val[1:0]) || s2_val[3]);
    wire [23:0] rnd_w;
    wire rnd_cw;
    ot_hdc_inc_k #(.W(24)) u_rnd (.a(s2_val[26:3]), .inc(inc), .y(rnd_w), .co(rnd_cw));
    localparam integer W5 = 1 + 1 + 1 + 1 + 2 + 32 + 8 + 24 + 1;
    wire [W5-1:0] q5;
    ot_s81sl_fp_cut #(.W(W5), .CUT(K5)) u_k5 (.clk(clk), .rst_n(rst_n[0]),
        .d({s2_v, s2_byp, s2_zero, s2_sign, s2_err, s2_code, s2_exp, rnd_w, rnd_cw}), .q(q5));
    wire        u_v, u_byp, u_zero, u_sign, rnd_c;
    wire [1:0]  u_err;
    wire [31:0] u_code;
    wire [7:0]  u_exp;
    wire [23:0] rnd;
    assign {u_v, u_byp, u_zero, u_sign, u_err, u_code, u_exp, rnd, rnd_c} = q5;
    // ---- encode, subnormal, overflow, canonical zero -------------------------------------------------------
    wire [2:0] carry_cp;
    ot_s81sl_fp_copy #(.W(1),.N(3),.CUT(K5)) u_carry_cp(.clk(clk),.d(rnd_cw),.q(carry_cp));
    wire [23:0] man; wire [23:0] man_c={1'b1,rnd[23:1]};
    for(genvar g=0;g<3;g=g+1)begin:g_man
      ot_s81sl_fp_mux #(.W(8)) u_m(.s(carry_cp[g]),.a(man_c[8*g+:8]),.b(rnd[8*g+:8]),.y(man[8*g+:8]));
    end
    wire [8:0]  e = {1'b0, u_exp} + {8'd0, rnd_c};
    wire subnormal = (e == 9'd1) && !man[23];
    wire [31:0] code = {u_sign, subnormal ? 8'd0 : e[7:0], man[22:0]};
    wire over = (u_exp == 8'hff) || (e >= 9'd255);
    wire[3:0] byp_cp;
    ot_s81sl_fp_copy #(.W(1),.N(4),.CUT(K5)) u_byp_cp(.clk(clk),.d(s2_byp),.q(byp_cp));
    wire nz=|code[30:0];
    for(genvar g=0;g<4;g=g+1)begin:g_out
      wire[7:0] nd;
      ot_s81sl_fp_out_byte u_e(.byp(byp_cp[g]),.zero(u_zero),.over(over),.nz(nz),.code(code[8*g+:8]),.bc(u_code[8*g+:8]),.y(nd));
      always @(posedge clk or negedge rst_n[g+1]) if(!rst_n[g+1])y[8*g+:8]<=0;else y[8*g+:8]<=nd;
    end
    always @(posedge clk or negedge rst_n[5])begin
      if(!rst_n[5])begin err<=E_NONE;valid_out<=0;end
      else begin
        valid_out<=u_v;
        if(u_byp)err<=u_err;else if(u_zero)err<=E_NONE;else if(over)err<=E_OVERFLOW;else err<=E_NONE;
      end
    end
endmodule

module ot_s81sl_fp_mul_n32 #(
    parameter integer CUTS = 8'b01101011
) (
    input  wire        clk,
    input  wire [5:0]  rst_n,
    input  wire        valid_in,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output reg  [1:0]  err,
    output reg         valid_out
);
    localparam [1:0] E_NONE = 2'd0, E_NONFINITE = 2'd1, E_OVERFLOW = 2'd2;
    localparam integer K0 = CUTS % 2, K1 = (CUTS / 2) % 2, K2 = (CUTS / 4) % 2, K3 = (CUTS / 8) % 2,
                       K4 = (CUTS / 16) % 2, K5 = (CUTS / 32) % 2, K6 = (CUTS / 64) % 2, K7 = (CUTS / 128) % 2;
    function automatic [95:0] csa;
        input [47:0] r0, r1, r2;
        begin
            csa[47:0] = r0 ^ r1 ^ r2;
            csa[95:48] = ((r0 & r1) | (r0 & r2) | (r1 & r2)) << 1;
        end
    endfunction

    // ---- decode; the fractions' leading zeros ---------------------------------------------------------
    wire [7:0] a_field = a[30:23];
    wire [7:0] b_field = b[30:23];
    wire nonfinite = (a_field == 8'hff) || (b_field == 8'hff);
    wire zero = (a[30:0] == 31'd0) || (b[30:0] == 31'd0);
    wire [5:0] a_cz, b_cz;                      // clz23 of the fraction (23 for a zero fraction)
    ot_hdc_lzc32 u_la (.x({a[22:0], 9'h1ff}), .n(a_cz));
    ot_hdc_lzc32 u_lb (.x({b[22:0], 9'h1ff}), .n(b_cz));
    localparam integer W0 = 1 + 1 + 2 + 1 + 23 + 23 + 8 + 8 + 5 + 5;
    wire [W0-1:0] q0;
    ot_s81sl_fp_cut #(.W(W0), .CUT(K0)) u_k0 (.clk(clk), .rst_n(rst_n[0]),
        .d({valid_in, nonfinite || zero, (nonfinite ? E_NONFINITE : E_NONE), a[31] ^ b[31], a[22:0], b[22:0],
            a_field, b_field, a_cz[4:0], b_cz[4:0]}), .q(q0));
    wire        o0_v, o0_byp, o0_sign;
    wire [1:0]  o0_err;
    wire [22:0] o0_af, o0_bf;
    wire [7:0]  o0_ae, o0_be;
    wire [4:0]  o0_acz, o0_bcz;
    assign {o0_v, o0_byp, o0_err, o0_sign, o0_af, o0_bf, o0_ae, o0_be, o0_acz, o0_bcz} = q0;
    // ---- normalise (a subnormal's significand {frac, 0} << clz23; mul_lat's a_raw << (1 + clz23)), powers ---
    wire a_s = (o0_ae == 8'd0), b_s = (o0_be == 8'd0);
    wire [23:0] a_n,b_n,a_shift,b_shift;
    ot_s81sl_fp_shift_chain #(.IW(24),.CW(5),.LEFT(1),.CUT(K0)) u_na(.clk(clk),.x({o0_af,1'b0}),.raw_count(a_cz[4:0]),.y(a_shift));
    ot_s81sl_fp_shift_chain #(.IW(24),.CW(5),.LEFT(1),.CUT(K0)) u_nb(.clk(clk),.x({o0_bf,1'b0}),.raw_count(b_cz[4:0]),.y(b_shift));
    wire[23:0] a_normal={1'b1,o0_af},b_normal={1'b1,o0_bf};
    for(genvar g=0;g<6;g=g+1)begin:g_norm
      ot_s81sl_fp_norm_pick u_a(.e(o0_ae),.s(a_shift[4*g+:4]),.n(a_normal[4*g+:4]),.y(a_n[4*g+:4]));
      ot_s81sl_fp_norm_pick u_b(.e(o0_be),.s(b_shift[4*g+:4]),.n(b_normal[4*g+:4]),.y(b_n[4*g+:4]));
    end
    wire signed [11:0] a_power = a_s ? (-12'sd150 - {7'd0, o0_acz}) : ($signed({4'd0, o0_ae}) - 12'sd150);
    wire signed [11:0] b_power = b_s ? (-12'sd150 - {7'd0, o0_bcz}) : ($signed({4'd0, o0_be}) - 12'sd150);
    localparam integer W1 = 1 + 1 + 2 + 1 + 24 + 24 + 12 + 12;
    wire [W1-1:0] q1;
    ot_s81sl_fp_cut #(.W(W1), .CUT(K1)) u_k1 (.clk(clk), .rst_n(rst_n[0]),
        .d({o0_v, o0_byp, o0_err, o0_sign, a_n, b_n, a_power, b_power}), .q(q1));
    wire        p_v, p_byp, p_sign;
    wire [1:0]  p_err;
    wire [23:0] p_a, p_b;
    wire [11:0] p_ap, p_bp;
    assign {p_v, p_byp, p_err, p_sign, p_a, p_b, p_ap, p_bp} = q1;
    // ---- rows (24 AND rows, three carry-save levels), the exponent sum -----------------------------------
    wire [11:0] power;
    wire power_c;
    ot_hdc_ksadd_k #(.W(12)) u_pw (.a(p_ap), .b(p_bp), .cin(1'b0), .s(power), .cout(power_c));
    wire [48*8-1:0] rows;
    wire [48*16-1:0] row_l1; wire [48*11-1:0] row_l2;
    for(genvar g=0;g<8;g=g+1)begin:g_row_group
      ot_s81sl_fp_rows3 #(.FIRST(3*g)) u_rg(.a(p_a),.b(p_b),.y(row_l1[96*g+:96]));
    end
    for(genvar g=0;g<5;g=g+1)begin:g_row_l2
      assign row_l2[96*g+:96]=csa(row_l1[144*g+:48],row_l1[144*g+48+:48],row_l1[144*g+96+:48]);
    end
    assign row_l2[480+:48]=row_l1[720+:48];
    for(genvar g=0;g<3;g=g+1)begin:g_row_l3
      assign rows[96*g+:96]=csa(row_l2[144*g+:48],row_l2[144*g+48+:48],row_l2[144*g+96+:48]);
    end
    assign rows[288+:96]=row_l2[432+:96];
    localparam integer W2 = 1 + 1 + 2 + 1 + 48 * 8 + 12;
    wire [W2-1:0] q2;
    ot_s81sl_fp_cut #(.W(W2), .CUT(K2)) u_k2 (.clk(clk), .rst_n(rst_n[0]),
        .d({p_v, p_byp, p_err, p_sign, rows, power}), .q(q2));
    wire        s1_v, s1_byp, s1_sign;
    wire [1:0]  s1_err;
    wire [48*8-1:0] s1_rows;
    wire signed [11:0] s1_power;
    assign {s1_v, s1_byp, s1_err, s1_sign, s1_rows, s1_power} = q2;
    // ---- two carry-save levels (8 -> 6 -> 4) ---------------------------------------------------------------
    wire [48*6-1:0] l4;
    wire [48*4-1:0] l5;
    genvar i;
    generate
        for (i = 0; i < 2; i = i + 1) begin : g_l4
            assign l4[96*i +: 96] = csa(s1_rows[144*i +: 48], s1_rows[144*i + 48 +: 48], s1_rows[144*i + 96 +: 48]);
        end
        assign l4[192 +: 96] = s1_rows[288 +: 96];
        for (i = 0; i < 2; i = i + 1) begin : g_l5
            assign l5[96*i +: 96] = csa(l4[144*i +: 48], l4[144*i + 48 +: 48], l4[144*i + 96 +: 48]);
        end
    endgenerate
    localparam integer W3 = 1 + 1 + 2 + 1 + 48 * 4 + 12;
    wire [W3-1:0] q3;
    ot_s81sl_fp_cut #(.W(W3), .CUT(K3)) u_k3 (.clk(clk), .rst_n(rst_n[0]),
        .d({s1_v, s1_byp, s1_err, s1_sign, l5, s1_power}), .q(q3));
    wire        r3_v, r3_byp, r3_sign;
    wire [1:0]  r3_err;
    wire [48*4-1:0] r3_l5;
    wire signed [11:0] r3_power;
    assign {r3_v, r3_byp, r3_err, r3_sign, r3_l5, r3_power} = q3;
    // ---- two more carry-save levels (4 -> 3 -> 2); the floors and the subnormal masks -------------------
    wire [48*3-1:0] l6;
    wire [48*2-1:0] l7;
    assign l6[0 +: 96] = csa(r3_l5[0 +: 48], r3_l5[48 +: 48], r3_l5[96 +: 48]);
    assign l6[96 +: 48] = r3_l5[144 +: 48];
    assign l7 = csa(l6[0 +: 48], l6[48 +: 48], l6[96 +: 48]);
    wire signed [11:0] fl47 = r3_power + 12'sd47;
    wire signed [11:0] fl46 = r3_power + 12'sd46;
    wire signed [11:0] sh_sub = -(r3_power + 12'sd149);
    wire [5:0] shc = (sh_sub > 12'sd63) ? 6'd63 : sh_sub[5:0];
    wire[47:0] m_round,m_sticky;
    wire[12*6-1:0] mask_power;
    ot_s81sl_fp_copy #(.W(12),.N(6),.CUT(K3)) u_mask_cp(.clk(clk),.d(s1_power),.q(mask_power));
    for(genvar g=0;g<6;g=g+1)begin:g_mask
      ot_s81sl_fp_mask8 #(.LO(8*g)) u_m(.power(mask_power[12*g+:12]),.mr(m_round[8*g+:8]),.ms(m_sticky[8*g+:8]));
    end
    localparam integer W4 = 1 + 1 + 2 + 1 + 96 + 1 + 1 + 12 + 12 + 6 + 48 + 48;
    wire [W4-1:0] q4;
    ot_s81sl_fp_cut #(.W(W4), .CUT(K4)) u_k4 (.clk(clk), .rst_n(rst_n[0]),
        .d({r3_v, r3_byp, r3_err, r3_sign, l7, fl47 < -12'sd126, fl46 < -12'sd126, fl47, fl46, shc, m_round, m_sticky}),
        .q(q4));
    wire        q_v, q_byp, q_sign, q_s47, q_s46;
    wire [1:0]  q_err;
    wire [95:0] q_l7;
    wire [11:0] q_fl47, q_fl46;
    wire [5:0]  q_sh;
    wire [47:0] q_mr, q_ms;
    assign {q_v, q_byp, q_err, q_sign, q_l7, q_s47, q_s46, q_fl47, q_fl46, q_sh, q_mr, q_ms} = q4;
    // ---- the 48-bit prefix add ---------------------------------------------------------------------------
    wire [47:0] prod;
    wire unused_cout;
    ot_hdc_ksadd_k #(.W(48)) u_cpa (.a(q_l7[47:0]), .b(q_l7[95:48]), .cin(1'b0), .s(prod), .cout(unused_cout));
    localparam integer W5 = 1 + 1 + 2 + 1 + 48 + 1 + 1 + 12 + 12 + 6 + 48 + 48;
    wire [W5-1:0] q5;
    ot_s81sl_fp_cut #(.W(W5), .CUT(K5)) u_k5 (.clk(clk), .rst_n(rst_n[0]),
        .d({q_v, q_byp, q_err, q_sign, prod, q_s47, q_s46, q_fl47, q_fl46, q_sh, q_mr, q_ms}), .q(q5));
    wire        s2_v, s2_byp, s2_sign, s2_sub47, s2_sub46;
    wire [1:0]  s2_err;
    wire [47:0] s2_prod, s2_mr, s2_ms;
    wire [5:0]  s2_sh;
    wire signed [11:0] s2_fl47, s2_fl46;
    assign {s2_v, s2_byp, s2_err, s2_sign, s2_prod, s2_sub47, s2_sub46, s2_fl47, s2_fl46, s2_sh, s2_mr, s2_ms} = q5;
    // ---- select, subnormal shift, round / sticky bits; both encode exponents ------------------------------
    wire top = s2_prod[47];
    wire is_sub = top ? s2_sub47 : s2_sub46;
    wire signed [11:0] fl = top ? s2_fl47 : s2_fl46;
    wire[9:0] top_cp;
    ot_s81sl_fp_copy #(.W(1),.N(10),.CUT(K5)) u_top_cp(.clk(clk),.d(prod[47]),.q(top_cp));
    wire[23:0] n_main;
    for(genvar g=0;g<3;g=g+1)begin:g_n_main
      ot_s81sl_fp_mux #(.W(8)) u_p(.s(top_cp[g]),.a(s2_prod[24+8*g+:8]),.b(s2_prod[23+8*g+:8]),.y(n_main[8*g+:8]));
    end
    wire n_rb = top ? s2_prod[23] : s2_prod[22];
    wire n_st = top ? (|s2_prod[22:0]) : (|s2_prod[21:0]);
    wire [47:0] sub_shifted;
    ot_s81sl_fp_shift_chain #(.IW(48),.CW(6),.CUT(K5)) u_sub_shift(
      .clk(clk),.x(s2_prod),.raw_count(q_sh),.y(sub_shifted));
    wire [23:0] s_main = sub_shifted[23:0];
    wire s_rb = |(s2_prod & s2_mr);
    wire s_st = |(s2_prod & s2_ms);
    wire[23:0] main;
    for(genvar g=0;g<3;g=g+1)begin:g_main
      ot_s81sl_fp_sub_pick u_m(.top(top_cp[7+g]),.s47(s2_sub47),.s46(s2_sub46),.s(s_main[8*g+:8]),.n(n_main[8*g+:8]),.y(main[8*g+:8]));
    end
    wire rb = is_sub ? s_rb : n_rb;
    wire st = is_sub ? s_st : n_st;
    // mul_lat's encode: floor_ = fl + carry; over = !sub && floor_ > 127; field = floor_[7:0] + 127.  Both
    // carries here (from the select's fl, both top choices side by side), picked by the carry after the round
    wire signed [11:0] f47p1 = s2_fl47 + 12'sd1, f46p1 = s2_fl46 + 12'sd1;
    wire [7:0]  fa47 = s2_fl47[7:0] + 8'd127, fb47 = f47p1[7:0] + 8'd127;
    wire [7:0]  fa46 = s2_fl46[7:0] + 8'd127, fb46 = f46p1[7:0] + 8'd127;
    wire        oa47 = s2_fl47 > 12'sd127, ob47 = f47p1 > 12'sd127;
    wire        oa46 = s2_fl46 > 12'sd127, ob46 = f46p1 > 12'sd127;
    wire[7:0] fa,fb;
    ot_s81sl_fp_mux #(.W(8)) u_fa(.s(top_cp[3]),.a(fa47),.b(fa46),.y(fa));
    ot_s81sl_fp_mux #(.W(8)) u_fb(.s(top_cp[4]),.a(fb47),.b(fb46),.y(fb));
    wire        oa = top_cp[5] ? oa47 : oa46, ob = top_cp[6] ? ob47 : ob46;
    localparam integer W6 = 1 + 1 + 2 + 1 + 1 + 24 + 1 + 8 + 8 + 1 + 1;
    wire [W6-1:0] q6;
    ot_s81sl_fp_cut #(.W(W6), .CUT(K6)) u_k6 (.clk(clk), .rst_n(rst_n[0]),
        .d({s2_v, s2_byp, s2_err, s2_sign, is_sub, main, rb && (st || main[0]), fa, fb, oa, ob}), .q(q6));
    wire        r_v, r_byp, r_sign, r_sub, r_inc, r_oa, r_ob;
    wire [1:0]  r_err;
    wire [23:0] r_main;
    wire [7:0]  r_fa, r_fb;
    assign {r_v, r_byp, r_err, r_sign, r_sub, r_main, r_inc, r_fa, r_fb, r_oa, r_ob} = q6;
    // ---- round ----------------------------------------------------------------------------------------------
    wire [23:0] rnd_w;
    wire rnd_cw;
    ot_hdc_inc_k #(.W(24)) u_rnd (.a(r_main), .inc(r_inc), .y(rnd_w), .co(rnd_cw));
    localparam integer W7 = 1 + 1 + 2 + 1 + 1 + 24 + 1 + 8 + 8 + 1 + 1;
    wire [W7-1:0] q7;
    ot_s81sl_fp_cut #(.W(W7), .CUT(K7)) u_k7 (.clk(clk), .rst_n(rst_n[0]),
        .d({r_v, r_byp, r_err, r_sign, r_sub, rnd_w, rnd_cw, r_fa, r_fb, r_oa, r_ob}), .q(q7));
    wire        o_v, o_byp, o_sign, o_sub, rnd_c, o_oa, o_ob;
    wire [1:0]  o_err;
    wire [23:0] rnd;
    wire [7:0]  o_fa, o_fb;
    assign {o_v, o_byp, o_err, o_sign, o_sub, rnd, rnd_c, o_fa, o_fb, o_oa, o_ob} = q7;
    // ---- encode ---------------------------------------------------------------------------------------------
    wire carry = !o_sub && rnd_c;
    wire [23:0] man = carry ? {1'b1, rnd[23:1]} : rnd;
    wire over = !o_sub && (carry ? o_ob : o_oa);
    wire [7:0] field = carry ? o_fb : o_fa;
    wire sub_carry = o_sub && rnd[23];
    wire [31:0] code = o_sub ? (sub_carry ? {o_sign, 8'h01, 23'd0} : {o_sign, 8'h00, rnd[22:0]})
                             : {o_sign, field, man[22:0]};
    wire nz=|code[30:0];
    for(genvar g=0;g<4;g=g+1)begin:g_out
      wire[7:0] nd;
      ot_s81sl_fp_out_zero u_e(.byp(o_byp),.over(over),.nz(nz),.code(code[8*g+:8]),.y(nd));
      always @(posedge clk or negedge rst_n[g+1])if(!rst_n[g+1])y[8*g+:8]<=0;else y[8*g+:8]<=nd;
    end
    always @(posedge clk or negedge rst_n[5])begin
      if(!rst_n[5])begin err<=E_NONE;valid_out<=0;end
      else begin valid_out<=o_v;if(o_byp)err<=o_err;else if(over)err<=E_OVERFLOW;else err<=E_NONE;end
    end
endmodule


// Every copy is consumed by a bounded byte/row group on the original edge.
module ot_s81sl_fp_copy #(parameter integer W=1,N=1,CUT=1)(input wire clk,input wire [W-1:0] d,output wire [W*N-1:0] q);
 generate for(genvar g=0;g<N;g=g+1)begin:g_copy
  if(CUT)begin:g_r
   (* keep=1 *) reg [W-1:0] r;
   always @(posedge clk) r<=d;
   assign q[W*g+:W]=r;
  end else assign q[W*g+:W]=d;
 end endgenerate
endmodule
(* keep_hierarchy=1 *) module ot_s81sl_fp_mux #(parameter integer W=8)(input wire s,input wire[W-1:0] a,b,output wire[W-1:0] y);
 assign y=s?a:b;
endmodule
(* keep_hierarchy=1 *) module ot_s81sl_fp_shift #(parameter integer IW=27,OW=4,LO=0,LEFT=0,CW=5)(input wire[IW-1:0] x,input wire[CW-1:0] sh,output wire[OW-1:0] y);
 wire[IW-1:0] v=LEFT?(x<<sh):(x>>sh);
 assign y=v[LO+:OW];
endmodule
(* keep_hierarchy=1 *) module ot_s81sl_fp_rows3 #(parameter integer FIRST=0)(input wire[23:0] a,b,output wire[95:0] y);
 wire[23:0] pp[0:2];
 for(genvar r=0;r<3;r=r+1)begin:g_r
  for(genvar g=0;g<4;g=g+1)begin:g_g
   ot_s81sl_fp_pp6 u_pp(.a(a[6*g+:6]),.b(b[FIRST+r]),.y(pp[r][6*g+:6]));
  end
 end
 wire[47:0] r0={24'd0,pp[0]}<<FIRST;
 wire[47:0] r1={24'd0,pp[1]}<<(FIRST+1);
 wire[47:0] r2={24'd0,pp[2]}<<(FIRST+2);
 assign y[47:0]=r0^r1^r2;
 assign y[95:48]=((r0&r1)|(r0&r2)|(r1&r2))<<1;
endmodule
module ot_s81sl_qadd_n32 #(parameter integer LAT=6)(input wire clk,input wire[5:0] rst_n,input wire v,input wire[31:0] a,b,output wire[31:0] y,output wire fault);
 wire[1:0] err;wire vo;
 if(LAT!=6)begin:g_bad ot_s81sl_FP_LAT_must_equal_6 u_bad();end
 ot_s81sl_fp_add_n32 u(.clk(clk),.rst_n(rst_n),.valid_in(v),.a(a),.b(b),.y(y),.err(err),.valid_out(vo));
 assign fault=vo&&(err!=0);
endmodule
module ot_s81sl_qmul_n32 #(parameter integer LAT=6)(input wire clk,input wire[5:0] rst_n,input wire v,input wire[31:0] a,b,output wire[31:0] y,output wire fault);
 wire[1:0] err;wire vo;
 if(LAT!=6)begin:g_bad ot_s81sl_FP_LAT_must_equal_6 u_bad();end
 ot_s81sl_fp_mul_n32 u(.clk(clk),.rst_n(rst_n),.valid_in(v),.a(a),.b(b),.y(y),.err(err),.valid_out(vo));
 assign fault=vo&&(err!=0);
endmodule

// Retain actual partial products before the CSA: each operand bit has exactly
//24 AND consumers instead of ABC duplicating its predicate into CSA gates.
(* keep_hierarchy=1 *) module ot_s81sl_fp_pp6(input wire[5:0] a,input wire b,output wire[5:0] y);
 assign y=a&{6{b}};
endmodule

// Each count bit controls one four-output constant-distance mux group at ONE
// shift level. Kept level boundaries prevent ABC expanding it across levels.
module ot_s81sl_fp_shift_chain #(parameter integer IW=27,CW=5,LEFT=0,CUT=1,JAM=0)(input wire clk,input wire[IW-1:0] x,input wire[CW-1:0] raw_count,output wire[IW-1:0] y);
 localparam integer NG=(IW+3)/4;
 wire[CW*NG-1:0] count;
 ot_s81sl_fp_copy #(.W(CW),.N(NG),.CUT(CUT)) u_cp(.clk(clk),.d(raw_count),.q(count));
 wire[IW-1:0] stage[0:CW];assign stage[0]=x;assign y=stage[CW];
 for(genvar st=0;st<CW;st=st+1)begin:g_st
  for(genvar g=0;g<NG;g=g+1)begin:g_gr
   localparam integer W=(IW-4*g<4)?IW-4*g:4;
   ot_s81sl_fp_shift_step #(.IW(IW),.OW(W),.LO(4*g),.DIST(1<<st),.LEFT(LEFT),.JAM(JAM)) u_step(.x(stage[st]),.sh(count[CW*g+st]),.y(stage[st+1][4*g+:W]));
  end
 end
endmodule
(* keep_hierarchy=1 *) module ot_s81sl_fp_shift_step #(parameter integer IW=27,OW=4,LO=0,DIST=1,LEFT=0,JAM=0)(input wire[IW-1:0] x,input wire sh,output wire[OW-1:0] y);
 wire[IW-1:0] shifted=LEFT?(x<<DIST):(x>>DIST);
 wire sticky=JAM?((DIST>=IW)?(|x):(|(x&({IW{1'b1}}>>(IW-DIST))))):1'b0;
 wire[IW-1:0] sj=shifted|{{(IW-1){1'b0}},sticky};
 assign y=sh?sj[LO+:OW]:x[LO+:OW];
endmodule
module ot_s81sl_fp_jam28(input wire clk,input wire[23:0] man,input wire[4:0] raw_count,input wire raw_far,output wire[27:0] y);
 wire[27:0] x={1'b0,man,3'b000},v;wire[6:0] far;
 ot_s81sl_fp_shift_chain #(.IW(28),.CW(5),.CUT(1),.JAM(1)) u_sh(.clk(clk),.x(x),.raw_count(raw_count),.y(v));
 ot_s81sl_fp_copy #(.W(1),.N(7),.CUT(1)) u_far(.clk(clk),.d(raw_far),.q(far));
 wire[27:0] f={27'd0,|x};
 for(genvar g=0;g<7;g=g+1)begin:g_far
  ot_s81sl_fp_mux #(.W(4)) u_m(.s(far[g]),.a(f[4*g+:4]),.b(v[4*g+:4]),.y(y[4*g+:4]));
 end
endmodule
(* keep_hierarchy=1 *) module ot_s81sl_fp_norm_pick(input wire[7:0] e,input wire[3:0] s,n,output wire[3:0] y);
 assign y=(e==0)?s:n;
endmodule

(* keep_hierarchy=1 *) module ot_s81sl_fp_bypass #(parameter integer LO=0)(input wire[31:0] a,b,output wire[7:0] y);
 wire nf=(a[30:23]==255)||(b[30:23]==255);wire az=(a[30:0]==0),bz=(b[30:0]==0);
 assign y=nf?0:(az?(bz?0:b[LO+:8]):a[LO+:8]);
endmodule
(* keep_hierarchy=1 *) module ot_s81sl_fp_add_pick #(parameter integer LO=0,W=4)(input wire[27:0] a,b,sum,output wire[W-1:0] y);
 wire[27:0] local_sum=a+b;
 wire[26:0] cv={sum[27:2],sum[1]|sum[0]};
 assign y=local_sum[27]?cv[LO+:W]:sum[LO+:W];
endmodule
(* keep_hierarchy=1 *) module ot_s81sl_fp_mask8 #(parameter integer LO=0)(input wire signed[11:0] power,output wire[7:0] mr,ms);
 wire signed[11:0] sub=-(power+12'sd149);
 wire[5:0] sh=(sub>12'sd63)?6'd63:sub[5:0];
 for(genvar g=0;g<8;g=g+1)begin:g_b
  assign mr[g]=({6'd0,6'(LO+g)}=={6'd0,sh}-12'd1);
  assign ms[g]=({6'd0,6'(LO+g)}<{6'd0,sh}-12'd1);
 end
endmodule
(* keep_hierarchy=1 *) module ot_s81sl_fp_sub_pick(input wire top,s47,s46,input wire[7:0] s,n,output wire[7:0] y);
 wire sub=top?s47:s46;assign y=sub?s:n;
endmodule
(* keep_hierarchy=1 *) module ot_s81sl_fp_out_byte(input wire byp,zero,over,nz,input wire[7:0] code,bc,output wire[7:0] y);
 wire clear;
 ot_s81sl_fp_clear u_c(.byp(1'b0),.zero(zero),.over(over),.nz(nz),.clear(clear));
 assign y=byp?bc:(clear?8'd0:code);
endmodule
(* keep_hierarchy=1 *) module ot_s81sl_fp_out_zero(input wire byp,over,nz,input wire[7:0] code,output wire[7:0] y);
 wire clear;
 ot_s81sl_fp_clear u_c(.byp(byp),.zero(1'b0),.over(over),.nz(nz),.clear(clear));
 assign y=clear?8'd0:code;
endmodule

(* keep_hierarchy=1 *) module ot_s81sl_fp_clear(input wire byp,zero,over,nz,output wire clear);
 assign clear=byp||zero||over||!nz;
endmodule
