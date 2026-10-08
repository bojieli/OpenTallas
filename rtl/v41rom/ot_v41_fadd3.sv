`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_v41_fadd3 (s81-bf deep full-rate BF, 2026-10-07, OPTIONAL lever): ot_v41_fadd2 (EXT0 kept) with two more opt-in
// cuts sized on the routed BF RECUT / UNROLL limiters: SPLIT6 splits step 6, the 27-bit leading-zero count
// (u_c5 -> u_c6 -159 / -285 ps), into per-half counts and a combine; SPLIT9 splits step 9 (round carry select,
// overflow -> encode).  Bit-identical to ot_v41_fadd2 for every CUT; LATENCY = 1 + popcount(CUT) + SPLIT6 + SPLIT9.
// ---------------------------------------------------------------------------
module ot_v41_fadd3 #(
    parameter [8:0] CUT = 9'b1_0111_1011,          // 8 stages: steps 2+3 and 7+8 share a stage
    parameter integer EXT0 = 0,                      // 1: step 0's output bundle comes from o0_ext (ot_v41_fadd_s0)
    parameter integer SPLIT6 = 0,                    // 1: step 6 (leading-zero count) in two stages (+1)
    parameter integer SPLIT9 = 0,                    // 1: step 9 (round carry / encode) in two stages (+1)
    parameter integer LATENCY = 1 + CUT[0] + CUT[1] + CUT[2] + CUT[3] + CUT[4] + CUT[5] + CUT[6] + CUT[7] + CUT[8] + SPLIT6 + SPLIT9
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [31:0] a,
    input  wire [31:0] b,
    input  wire [104:0] o0_ext,
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
    ot_v41_cut #(.W(W0), .EN(CUT[0])) u_c0 (.clk(clk), .rst_n(rst_n), .d((EXT0 != 0) ? o0_ext : o0), .q(i1));

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
    // SPLIT6: 6a counts the leading zeros of the high 14 and low 13 bits separately (registered), 6b combines them:
    // lz = any(high) ? lz(high) : 14 + lz(low) (27 when all zero), identical to the single 27-bit count.
    wire        v6, byp6, sub6, sg6, z6; wire [1:0] er6; wire [31:0] code6; wire [7:0] ex6; wire [26:0] val6;
    localparam integer W5X = 1 + 1 + 1 + 1 + 1 + 2 + 32 + 8 + 27;
    reg [3:0] lzh6a, lzl6a;
    always @* begin
        lzh6a = 4'd14;
        for (k = 0; k <= 13; k = k + 1) if (i6[13 + k]) lzh6a = 4'd13 - k[3:0];
        lzl6a = 4'd13;
        for (k = 0; k <= 12; k = k + 1) if (i6[k]) lzl6a = 4'd12 - k[3:0];
    end
    wire hany6a = |i6[26:13];
    wire [W5X+8:0] o6a = {i6, lzh6a, lzl6a, hany6a};
    wire [W5X+8:0] i6b;
    ot_v41_cut #(.W(W5X + 9), .EN(SPLIT6 != 0)) u_c6a (.clk(clk), .rst_n(rst_n), .d(o6a), .q(i6b));
    wire [3:0] lzh6, lzl6; wire hany6;
    assign {v6, byp6, sub6, sg6, z6, er6, code6, ex6, val6, lzh6, lzl6, hany6} = i6b;
`ifdef BF_DEEP_MUTANT_LZ
    wire [4:0] lz6 = hany6 ? {1'b0, lzh6} : 5'd13 + {1'b0, lzl6};   // negative control: low-half offset off by one
`else
    wire [4:0] lz6 = hany6 ? {1'b0, lzh6} : 5'd14 + {1'b0, lzl6};
`endif
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
    // SPLIT9: 9a (round carry, mantissa / exponent select, overflow) registered, 9b encodes and selects
    wire        v9, byp9, sg9, z9; wire [1:0] er9; wire [31:0] code9; wire [7:0] ex9; wire [24:0] rnd9;
    assign {v9, byp9, sg9, z9, er9, code9, ex9, rnd9} = i9;
    wire        cy9 = rnd9[24];
    wire [23:0] man9a = cy9 ? rnd9[24:1] : rnd9[23:0];
    wire [7:0]  exo9a = cy9 ? (ex9 + 8'd1) : ex9;
    wire        over9a = (ex9 >= 8'hff) || (exo9a >= 8'hff);
    localparam integer W9 = 1 + 1 + 1 + 1 + 2 + 32 + 8 + 24 + 1;
    wire [W9-1:0] i9b;
    ot_v41_cut #(.W(W9), .EN(SPLIT9 != 0)) u_c9a (.clk(clk), .rst_n(rst_n), .d({v9, byp9, sg9, z9, er9, code9, exo9a, man9a, over9a}), .q(i9b));
    wire        vb, bypb, sgb, zb, over9; wire [1:0] erb; wire [31:0] codeb; wire [7:0] exo9; wire [23:0] man9;
    assign {vb, bypb, sgb, zb, erb, codeb, exo9, man9, over9} = i9b;
    wire        subn9 = (exo9 == 8'd1) && !man9[23];
    wire [31:0] enc9 = {sgb, subn9 ? 8'd0 : exo9, man9[22:0]};
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            y <= 32'd0; err <= E_NONE; valid_out <= 1'b0;
        end else begin
            valid_out <= vb;
            if (bypb) begin
                y <= codeb; err <= erb;
            end else if (zb) begin
                y <= 32'd0; err <= E_NONE;
            end else if (over9) begin
                y <= 32'd0; err <= E_OVERFLOW;
            end else begin
                y <= (enc9[30:0] == 31'd0) ? 32'd0 : enc9; err <= E_NONE;
            end
        end
    end
endmodule
