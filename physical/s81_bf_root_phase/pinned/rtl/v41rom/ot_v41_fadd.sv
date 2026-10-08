`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_v41_fadd: pipelined binary32 adder of the V4.1 ROM element at 1.2 GHz (W10; root/user decision 2026-09-30:
// every block closes 0.833 ns at SS setup / FF hold).
//
// Bit-identical to ot_fp32_add_rne_pipe (and so to ot_fp32_rne_pkg::fp32_add_rne, the scalar authority),
// including its non-IEEE choices: (-0) + (-0) = +0, every zero result is +0, nonfinite operands and overflow
// fail closed through `err` with y = 0.  The arithmetic is the same five steps cut finer: ten combinational
// steps, and a register after step i when CUT[i] is set (the last step always ends in the output register).
//
//   step 0  decode, operand zero / nonfinite, exponent and significand compares
//   step 1  order by magnitude (swap), shift distance
//   step 2  align, coarse: shift right by 8 * dist[4:3], jamming what falls off
//   step 3  align, fine: shift right by dist[2:0], jamming; saturate past 27
//   step 4  28-bit add and subtract (both)
//   step 5  select, carry renormalize, exact-cancel zero
//   step 6  leading-zero count of the cancellation, clamped by the exponent floor
//   step 7  normalizing left shift
//   step 8  round-to-nearest-even increment
//   step 9  round carry, subnormal / overflow, encode
//
// LATENCY = popcount(CUT) + 1.  CUT = 9'b0_1010_1010 reproduces ot_fp32_add_rne_pipe's five stages.
// Measured per step at SS (ORFS WC floorplan, 0.833 ns, every step cut): 1 swap 568 ps, 2+3 align 475, 4 add
// 596, 5 select 306, 6 LZC 454, 7 shift 317, 8 round 726 before the prefix increment, 9 encode 381.
// ---------------------------------------------------------------------------
module ot_v41_fadd #(
    parameter [8:0] CUT = 9'b1_0111_1011,          // 8 stages: steps 2+3 and 7+8 share a stage
    parameter integer LATENCY = 1 + CUT[0] + CUT[1] + CUT[2] + CUT[3] + CUT[4] + CUT[5] + CUT[6] + CUT[7] + CUT[8]
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output reg  [1:0]  err,
    output reg         valid_out
);
    localparam [1:0] E_NONE = 2'd0;
    localparam [1:0] E_NONFINITE = 2'd1;
    localparam [1:0] E_OVERFLOW = 2'd2;
    integer k;

    // ---------------- step 0: decode and compare ----------------
    wire [7:0]  a_field = a[30:23];
    wire [7:0]  b_field = b[30:23];
    wire [7:0]  a_exp0 = (a_field == 8'd0) ? 8'd1 : a_field;
    wire [7:0]  b_exp0 = (b_field == 8'd0) ? 8'd1 : b_field;
    wire [23:0] a_man0 = {(a_field != 8'd0), a[22:0]};
    wire [23:0] b_man0 = {(b_field != 8'd0), b[22:0]};
    wire        nonf0 = (a_field == 8'hff) || (b_field == 8'hff);
    wire        az0 = (a_man0 == 24'd0);
    wire        bz0 = (b_man0 == 24'd0);
    // |b| significand > |a| significand  <=>  a - b borrows (explicit prefix: a 24-bit compare ripples otherwise)
    wire [23:0] dm0;
    wire        age0;
    ot_v41_ksadd #(.W(24)) u_cm0 (.a(a_man0), .b(~b_man0), .cin(1'b1), .s(dm0), .cout(age0));
    localparam integer W0 = 1 + 8 + 8 + 24 + 24 + 1 + 1 + 1 + 1 + 1 + 1 + 1 + 1 + 32;
    wire [W0-1:0] o0 = {valid_in, a_exp0, b_exp0, a_man0, b_man0, a[31], b[31], nonf0, az0, bz0,
                        b_exp0 > a_exp0, b_exp0 == a_exp0, !age0,
                        nonf0 ? 32'd0 : (az0 ? (bz0 ? 32'd0 : b) : a)};
    wire [W0-1:0] i1;
    ot_v41_cut #(.W(W0), .EN(CUT[0])) u_c0 (.clk(clk), .rst_n(rst_n), .d(o0), .q(i1));

    // ---------------- step 1: swap, distance ----------------
    wire        v1; wire [7:0] ae1, be1; wire [23:0] am1, bm1; wire as1, bs1, nonf1, az1, bz1, egt1, eeq1, mgt1;
    wire [31:0] code1;
    assign {v1, ae1, be1, am1, bm1, as1, bs1, nonf1, az1, bz1, egt1, eeq1, mgt1, code1} = i1;
    wire swap1 = egt1 || (eeq1 && mgt1);
    wire [7:0]  bigx1 = swap1 ? be1 : ae1;
    wire [7:0]  smlx1 = swap1 ? ae1 : be1;
    localparam integer W1 = 1 + 1 + 2 + 32 + 1 + 1 + 8 + 8 + 24 + 24;
    wire [W1-1:0] o1 = {v1, nonf1 || az1 || bz1, nonf1 ? E_NONFINITE : E_NONE, code1, as1 != bs1,
                        swap1 ? bs1 : as1, bigx1, bigx1 - smlx1, swap1 ? bm1 : am1, swap1 ? am1 : bm1};
    wire [W1-1:0] i2;
    ot_v41_cut #(.W(W1), .EN(CUT[1])) u_c1 (.clk(clk), .rst_n(rst_n), .d(o1), .q(i2));

    // ---------------- step 2: align, coarse (8 * dist[4:3]) ----------------
    wire        v2, byp2, sub2, sg2; wire [1:0] er2; wire [31:0] code2; wire [7:0] ex2, d2; wire [23:0] big2, sml2;
    assign {v2, byp2, er2, code2, sub2, sg2, ex2, d2, big2, sml2} = i2;
    wire [27:0] val2 = {1'b0, sml2, 3'b000};
    reg  [27:0] sh2;
    reg         st2;
    always @* begin
        case (d2[4:3])
            2'd0: begin sh2 = val2;               st2 = 1'b0; end
            2'd1: begin sh2 = {8'd0, val2[27:8]};  st2 = |val2[7:0]; end
            2'd2: begin sh2 = {16'd0, val2[27:16]}; st2 = |val2[15:0]; end
            default: begin sh2 = {24'd0, val2[27:24]}; st2 = |val2[23:0]; end
        endcase
    end
    wire sat2 = d2 >= 8'd28;
    localparam integer W2 = 1 + 1 + 1 + 1 + 2 + 32 + 8 + 3 + 24 + 28 + 1 + 1 + 1;
    wire [W2-1:0] o2 = {v2, byp2, sub2, sg2, er2, code2, ex2, d2[2:0], big2, sh2, st2, sat2, |val2};
    wire [W2-1:0] i3;
    ot_v41_cut #(.W(W2), .EN(CUT[2])) u_c2 (.clk(clk), .rst_n(rst_n), .d(o2), .q(i3));

    // ---------------- step 3: align, fine (dist[2:0]); jam ----------------
    wire        v3, byp3, sub3, sg3, st3, sat3, any3; wire [1:0] er3; wire [31:0] code3; wire [7:0] ex3;
    wire [2:0]  d3; wire [23:0] big3; wire [27:0] sh3;
    assign {v3, byp3, sub3, sg3, er3, code3, ex3, d3, big3, sh3, st3, sat3, any3} = i3;
    reg  [27:0] f3;
    reg         fs3;
    always @* begin
        f3 = sh3 >> d3;
        fs3 = 1'b0;
        for (k = 0; k < 7; k = k + 1)
            if (k < d3) fs3 = fs3 | sh3[k];
    end
    wire [27:0] small3 = sat3 ? {27'd0, any3} : {f3[27:1], f3[0] | fs3 | st3};
    localparam integer W3 = 1 + 1 + 1 + 1 + 2 + 32 + 8 + 28 + 28;
    wire [W3-1:0] o3 = {v3, byp3, sub3, sg3, er3, code3, ex3, {1'b0, big3, 3'b000}, small3};
    wire [W3-1:0] i4;
    ot_v41_cut #(.W(W3), .EN(CUT[3])) u_c3 (.clk(clk), .rst_n(rst_n), .d(o3), .q(i4));

    // ---------------- step 4: add and subtract ----------------
    wire        v4, byp4, sub4, sg4; wire [1:0] er4; wire [31:0] code4; wire [7:0] ex4; wire [27:0] big4, sml4;
    assign {v4, byp4, sub4, sg4, er4, code4, ex4, big4, sml4} = i4;
    localparam integer W4 = 1 + 1 + 1 + 1 + 2 + 32 + 8 + 28 + 28;
    wire [27:0] sum4, dif4;
    wire        c4a, c4b;
    ot_v41_ksadd #(.W(28)) u_s4 (.a(big4), .b(sml4), .cin(1'b0), .s(sum4), .cout(c4a));
    ot_v41_ksadd #(.W(28)) u_d4 (.a(big4), .b(~sml4), .cin(1'b1), .s(dif4), .cout(c4b));
    wire [W4-1:0] o4 = {v4, byp4, sub4, sg4, er4, code4, ex4, sum4, dif4};
    wire [W4-1:0] i5;
    ot_v41_cut #(.W(W4), .EN(CUT[4])) u_c4 (.clk(clk), .rst_n(rst_n), .d(o4), .q(i5));

    // ---------------- step 5: select, carry renormalize, cancel ----------------
    wire        v5, byp5, sub5, sg5; wire [1:0] er5; wire [31:0] code5; wire [7:0] ex5; wire [27:0] sum5, dif5;
    assign {v5, byp5, sub5, sg5, er5, code5, ex5, sum5, dif5} = i5;
    wire        cy5 = !sub5 && sum5[27];
    wire [27:0] ar5 = sub5 ? dif5 : sum5;
    localparam integer W5 = 1 + 1 + 1 + 1 + 1 + 2 + 32 + 8 + 27;
    wire [W5-1:0] o5 = {v5, byp5, sub5, sg5, sub5 && (dif5 == 28'd0), er5, code5,
                        cy5 ? (ex5 + 8'd1) : ex5, cy5 ? {sum5[27:2], sum5[1] | sum5[0]} : ar5[26:0]};
    wire [W5-1:0] i6;
    ot_v41_cut #(.W(W5), .EN(CUT[5])) u_c5 (.clk(clk), .rst_n(rst_n), .d(o5), .q(i6));

    // ---------------- step 6: leading zeros, clamped ----------------
    wire        v6, byp6, sub6, sg6, z6; wire [1:0] er6; wire [31:0] code6; wire [7:0] ex6; wire [26:0] val6;
    assign {v6, byp6, sub6, sg6, z6, er6, code6, ex6, val6} = i6;
    reg [4:0] lz6;
    always @* begin
        lz6 = 5'd27;
        for (k = 0; k <= 26; k = k + 1)
            if (val6[k]) lz6 = 5'd26 - k[4:0];
    end
    wire [7:0] room6 = ex6 - 8'd1;
    wire [7:0] shf6 = ({3'd0, lz6} > room6) ? room6 : {3'd0, lz6};
    wire       apply6 = sub6 && !z6 && !byp6;
    localparam integer W6 = 1 + 1 + 1 + 1 + 2 + 32 + 8 + 27 + 5;
    wire [W6-1:0] o6 = {v6, byp6, sg6, z6, er6, code6, ex6, val6, apply6 ? shf6[4:0] : 5'd0};
    wire [W6-1:0] i7;
    ot_v41_cut #(.W(W6), .EN(CUT[6])) u_c6 (.clk(clk), .rst_n(rst_n), .d(o6), .q(i7));

    // ---------------- step 7: normalize ----------------
    wire        v7, byp7, sg7, z7; wire [1:0] er7; wire [31:0] code7; wire [7:0] ex7; wire [26:0] val7;
    wire [4:0]  sh7;
    assign {v7, byp7, sg7, z7, er7, code7, ex7, val7, sh7} = i7;
    localparam integer W7 = 1 + 1 + 1 + 1 + 2 + 32 + 8 + 27;
    wire [W7-1:0] o7 = {v7, byp7, sg7, z7, er7, code7, ex7 - {3'd0, sh7}, val7 << sh7};
    wire [W7-1:0] i8;
    ot_v41_cut #(.W(W7), .EN(CUT[7])) u_c7 (.clk(clk), .rst_n(rst_n), .d(o7), .q(i8));

    // ---------------- step 8: round increment ----------------
    wire        v8, byp8, sg8, z8; wire [1:0] er8; wire [31:0] code8; wire [7:0] ex8; wire [26:0] val8;
    assign {v8, byp8, sg8, z8, er8, code8, ex8, val8} = i8;
    wire        inc8 = val8[2] && ((|val8[1:0]) || val8[3]);
    // t + inc as a parallel-prefix flip mask (bit i flips when inc and every bit below is one): yosys otherwise
    // maps the increment as a 24-deep ripple of ORs (-83 ps alone at SS, 0.833 ns)
    wire [24:0] t8 = {1'b0, val8[26:3]};
    wire [24:0] r8;
    wire        co8;
    ot_v41_inc #(.W(25)) u_i8 (.a(t8), .inc(inc8), .y(r8), .co(co8));
    localparam integer W8 = 1 + 1 + 1 + 1 + 2 + 32 + 8 + 25;
    wire [W8-1:0] o8 = {v8, byp8, sg8, z8, er8, code8, ex8, r8};
    wire [W8-1:0] i9;
    ot_v41_cut #(.W(W8), .EN(CUT[8])) u_c8 (.clk(clk), .rst_n(rst_n), .d(o8), .q(i9));

    // ---------------- step 9: encode ----------------
    wire        v9, byp9, sg9, z9; wire [1:0] er9; wire [31:0] code9; wire [7:0] ex9; wire [24:0] rnd9;
    assign {v9, byp9, sg9, z9, er9, code9, ex9, rnd9} = i9;
    wire        cy9 = rnd9[24];
    wire [23:0] man9 = cy9 ? rnd9[24:1] : rnd9[23:0];
    wire [7:0]  exo9 = cy9 ? (ex9 + 8'd1) : ex9;
    wire        subn9 = (exo9 == 8'd1) && !man9[23];
    wire [31:0] enc9 = {sg9, subn9 ? 8'd0 : exo9, man9[22:0]};
    wire        over9 = (ex9 >= 8'hff) || (exo9 >= 8'hff);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            y <= 32'd0; err <= E_NONE; valid_out <= 1'b0;
        end else begin
            valid_out <= v9;
            if (byp9) begin
                y <= code9; err <= er9;
            end else if (z9) begin
                y <= 32'd0; err <= E_NONE;
            end else if (over9) begin
                y <= 32'd0; err <= E_OVERFLOW;
            end else begin
                y <= (enc9[30:0] == 31'd0) ? 32'd0 : enc9; err <= E_NONE;
            end
        end
    end
endmodule


// a pipeline cut: a register when EN, else a wire (the valid bit, bit W-1, is reset)
module ot_v41_cut #(
    parameter integer W = 8,
    parameter EN = 1'b1
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    if (EN) begin : g_r
        reg         v;
        reg [W-2:0] r;
        always @(posedge clk or negedge rst_n) if (!rst_n) v <= 1'b0; else v <= d[W-1];
        always @(posedge clk) r <= d[W-2:0];
        assign q = {v, r};
    end else begin : g_w
        assign q = d;
    end
endmodule
