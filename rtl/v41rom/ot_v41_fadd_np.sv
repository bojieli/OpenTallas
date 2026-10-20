`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_v41_fadd_np: ot_v41_fadd / ot_v41_fadd2 (CUT = 9'b1_0111_1011, SPLIT9 = 0) in native-partition form (S81-QXPQ3
// 2026-10-20, SAFE item 3: no driver above 32 loads, counted through BUF / INV).  Bit-identical to ot_v41_fadd, same
// LATENCY (8), same valid timing; only the select / shift-amount registers are split into kept copies (ot_v41_kreg, never
// merged by Yosys) that each drive one slice of the datapath, and every slice's logic is built only from its own copy:
//   R0  swap decision inputs {egt, eeq, mgt} x3 (exponent / big / small operand muxes); {nonf, az, bz} x2 (the bypass
//       code, now formed in step 1 from the registered decoded fields instead of a 32-bit mux in step 0)
//   R1  alignment distance x4 (the 28-bit right shift with sticky in four 7-bit slices; steps 2+3 as one shift by d[4:0])
//   R4  {sub, sum[27]} x2 (the step-5 select / carry renormalise in two halves)
//   R6  normalise shift amount x4 (the 27-bit left shift in four slices; the exponent update on copy 0)
//   R8  round carry x4 (mantissa in 6-bit groups + exponent), {byp, z} x2 (the output select in two 16-bit halves)
// EXT0 = 1: step 0's bundle comes from o0_ext (ot_v41_fadd_s0 of the caller, as ot_v41_fadd2); its code field is
// not used (the code is re-formed in step 1 from the bundle's fields, bit-identical).
// NYK kept copies of the output register (yk, async reset 0 like y) and NVK of valid_out (vk) let a parent give each
// consumer slice its own copy (a flattened netlist otherwise shares one decode of y across modules).
// ---------------------------------------------------------------------------
module ot_v41_fadd_np #(
    parameter [8:0] CUT = 9'b1_0111_1011,
    parameter integer LATENCY = 8,
    parameter integer EXT0 = 0,
    parameter integer NYK = 1,
    parameter integer NVK = NYK,
    parameter integer NKW = (NYK > 0) ? NYK : 1,
    parameter integer NVW = (NVK > 0) ? NVK : 1
) (
    input  wire          clk,
    input  wire          rst_v,       // regional reset leaves: valid chain / err / valid_out / vk copies
    input  wire          rst_y,       // the sum register y
    input  wire [NKW-1:0] rst_k,      // one per yk copy
    input  wire          valid_in,
    input  wire [31:0]   a,
    input  wire [31:0]   b,
    input  wire [104:0]  o0_ext,
    output wire [31:0]   y,
    output wire [1:0]    err,
    output wire          valid_out,
    output wire [32*NKW-1:0] yk,
    output wire [NVW-1:0]    vk
);
`ifndef SYNTHESIS
    initial if (CUT != 9'b1_0111_1011 || LATENCY != 8) $fatal(1, "ot_v41_fadd_np: CUT 1_0111_1011 / LATENCY 8 only");
`endif
    localparam [1:0] E_NONE = 2'd0;
    localparam [1:0] E_NONFINITE = 2'd1;
    localparam [1:0] E_OVERFLOW = 2'd2;
    integer k;

    // ---------------- step 0: decode and compare (as ot_v41_fadd_s0) ----------------
    wire [104:0] s0;
    ot_v41_fadd_s0 u_s0 (.valid_in(valid_in), .a(a), .b(b), .o0(s0));
    wire [104:0] o0 = (EXT0 != 0) ? o0_ext : s0;
    // o0 = {v[104], a_exp0[103:96], b_exp0[95:88], a_man0[87:64], b_man0[63:40], as[39], bs[38], nonf[37], az[36],
    //       bz[35], egt[34], eeq[33], mgt[32], code[31:0]}
    reg          v1;
    always @(posedge clk or negedge rst_v) if (!rst_v) v1 <= 1'b0; else v1 <= o0[104];
    reg [7:0]  ae1, be1; reg [23:0] am1, bm1; reg as1, bs1, nonf1, az1, bz1;
    always @(posedge clk) begin
        ae1 <= o0[103:96]; be1 <= o0[95:88]; am1 <= o0[87:64]; bm1 <= o0[63:40];
        as1 <= o0[39]; bs1 <= o0[38]; nonf1 <= o0[37]; az1 <= o0[36]; bz1 <= o0[35];
    end
    wire [2:0] cmpk [0:2];          // {egt, eeq, mgt} copies: 0 exponents + sign, 1 big significand, 2 small significand
    wire [2:0] zk   [0:1];          // {nonf, az, bz} copies: code[15:0], code[31:16]
    for (genvar g = 0; g < 3; g = g + 1) begin : g_ck
        ot_v41_kreg #(.W(3)) u_k (.clk(clk), .arst_n(1'b1), .d(o0[34:32]), .q(cmpk[g]));
    end
    for (genvar g = 0; g < 2; g = g + 1) begin : g_zk
        ot_v41_kreg #(.W(3)) u_k (.clk(clk), .arst_n(1'b1), .d(o0[37:35]), .q(zk[g]));
    end

    // ---------------- step 1: swap, distance; the bypass code from the decoded fields ----------------
    wire sw0 = cmpk[0][2] || (cmpk[0][1] && cmpk[0][0]);
    wire sw1 = cmpk[1][2] || (cmpk[1][1] && cmpk[1][0]);
    wire sw2 = cmpk[2][2] || (cmpk[2][1] && cmpk[2][0]);
    wire [7:0]  bigx1 = sw0 ? be1 : ae1;
    wire [7:0]  smlx1 = sw0 ? ae1 : be1;
    wire        sg1 = sw0 ? bs1 : as1;
    wire [23:0] bigm1 = sw1 ? bm1 : am1;
    wire [23:0] smlm1 = sw2 ? am1 : bm1;
    // the original operands from the decoded fields: field = man0[23] ? exp0 : 0
    wire [31:0] ra = {as1, am1[23] ? ae1 : 8'd0, am1[22:0]};
    wire [31:0] rb = {bs1, bm1[23] ? be1 : 8'd0, bm1[22:0]};
    wire [31:0] code1;
    assign code1[15:0]  = zk[0][2] ? 16'd0 : (zk[0][1] ? (zk[0][0] ? 16'd0 : rb[15:0])  : ra[15:0]);
    assign code1[31:16] = zk[1][2] ? 16'd0 : (zk[1][1] ? (zk[1][0] ? 16'd0 : rb[31:16]) : ra[31:16]);
    reg         v2;
    always @(posedge clk or negedge rst_v) if (!rst_v) v2 <= 1'b0; else v2 <= v1;
    reg         byp2, sub2, sg2; reg [1:0] er2; reg [31:0] code2; reg [7:0] ex2; reg [23:0] big2, sml2;
    always @(posedge clk) begin
        byp2 <= nonf1 || az1 || bz1; er2 <= nonf1 ? E_NONFINITE : E_NONE; code2 <= code1;
        sub2 <= as1 != bs1; sg2 <= sg1; ex2 <= bigx1; big2 <= bigm1; sml2 <= smlm1;
    end
    // the alignment distance {sat, d[4:0]}: one kept copy per 4-bit slice of the aligned operand (7 slices) plus
    // one for the sticky; each slice shifts MSB-first (16, 8, 4, 2, 1) so a copy bit selects <= S + 15 muxes
    localparam integer NAS = 7;
    wire [7:0] dsub = bigx1 - smlx1;
    wire [5:0] dk [0:NAS];
    for (genvar g = 0; g <= NAS; g = g + 1) begin : g_dk
        ot_v41_kreg #(.W(6)) u_k (.clk(clk), .arst_n(1'b1), .d({dsub >= 8'd28, dsub[4:0]}), .q(dk[g]));
    end

    // ---------------- steps 2 + 3: align by d (shift right by d[4:0], jamming), saturate past 27 ----------------
    wire [27:0] val2 = {1'b0, sml2, 3'b000};
    wire        any2 = |sml2;
    wire [27:0] small3;
    for (genvar g = 0; g < NAS; g = g + 1) begin : g_al
        wire [5:0]  c = dk[g];
        wire [27:0] f16 = c[4] ? {16'd0, val2[27:16]} : val2;
        wire [27:0] f8  = c[3] ? {8'd0, f16[27:8]} : f16;
        wire [27:0] f4  = c[2] ? {4'd0, f8[27:4]} : f8;
        wire [27:0] f2  = c[1] ? {2'd0, f4[27:2]} : f4;
        wire [27:0] f   = c[0] ? {1'd0, f2[27:1]} : f2;
        if (g == 0) begin : g_s
            // sticky: what each layer drops, from the sticky copy (its own layer chain)
            wire [5:0]  e = dk[NAS];
            wire [27:0] e16 = e[4] ? {16'd0, val2[27:16]} : val2;
            wire [27:0] e8  = e[3] ? {8'd0, e16[27:8]} : e16;
            wire [27:0] e4  = e[2] ? {4'd0, e8[27:4]} : e8;
            wire [27:0] e2  = e[1] ? {2'd0, e4[27:2]} : e4;
            wire        lost = (e[4] && |val2[15:0]) || (e[3] && |e16[7:0]) || (e[2] && |e8[3:0]) || (e[1] && |e4[1:0]) || (e[0] && e2[0]);
`ifdef OT_NP_FADD_MUT
            assign small3[3:0] = c[5] ? {3'd0, any2} : f[3:0];                 // negative control: the alignment sticky lost
`else
            assign small3[3:0] = c[5] ? {3'd0, any2} : {f[3:1], f[0] | lost};
`endif
        end else begin : g_n
            assign small3[4*g +: 4] = c[5] ? 4'd0 : f[4*g +: 4];
        end
    end
    reg         v4;
    always @(posedge clk or negedge rst_v) if (!rst_v) v4 <= 1'b0; else v4 <= v2;
    reg         byp4, sub4, sg4; reg [1:0] er4; reg [31:0] code4; reg [7:0] ex4; reg [27:0] big4, sml4;
    always @(posedge clk) begin
        byp4 <= byp2; sub4 <= sub2; sg4 <= sg2; er4 <= er2; code4 <= code2; ex4 <= ex2;
        big4 <= {1'b0, big2, 3'b000}; sml4 <= small3;
    end

    // ---------------- step 4: add and subtract ----------------
    wire [27:0] sum4, dif4;
    wire        c4a, c4b;
    ot_v41_ksadd #(.W(28)) u_s4 (.a(big4), .b(sml4), .cin(1'b0), .s(sum4), .cout(c4a));
    ot_v41_ksadd #(.W(28)) u_d4 (.a(big4), .b(~sml4), .cin(1'b1), .s(dif4), .cout(c4b));
    reg         v5;
    always @(posedge clk or negedge rst_v) if (!rst_v) v5 <= 1'b0; else v5 <= v4;
    reg         byp5, sub5, sg5; reg [1:0] er5; reg [31:0] code5; reg [7:0] ex5; reg [27:0] sum5, dif5;
    always @(posedge clk) begin
        byp5 <= byp4; sub5 <= sub4; sg5 <= sg4; er5 <= er4; code5 <= code4; ex5 <= ex4; sum5 <= sum4; dif5 <= dif4;
    end
    wire [1:0] sk [0:1];            // {sub, sum[27]} copies: 0 bits 26:13, 1 bits 12:0 + exponent
    for (genvar g = 0; g < 2; g = g + 1) begin : g_sk
        ot_v41_kreg #(.W(2)) u_k (.clk(clk), .arst_n(1'b1), .d({sub4, sum4[27]}), .q(sk[g]));
    end

    // ---------------- step 5: select, carry renormalize, cancel ----------------
    wire        cyA = !sk[0][1] && sk[0][0];
    wire        cyB = !sk[1][1] && sk[1][0];
    wire [26:0] o5v;
    for (genvar j = 0; j < 27; j = j + 1) begin : g_s5
        if (j >= 13) begin : g_a
            assign o5v[j] = cyA ? sum5[j + 1] : (sk[0][1] ? dif5[j] : sum5[j]);
        end else if (j >= 1) begin : g_b
            assign o5v[j] = cyB ? sum5[j + 1] : (sk[1][1] ? dif5[j] : sum5[j]);
        end else begin : g_0
            assign o5v[j] = cyB ? (sum5[1] | sum5[0]) : (sk[1][1] ? dif5[0] : sum5[0]);
        end
    end
    reg         v6;
    always @(posedge clk or negedge rst_v) if (!rst_v) v6 <= 1'b0; else v6 <= v5;
    reg         byp6, sub6, sg6, z6; reg [1:0] er6; reg [31:0] code6; reg [7:0] ex6; reg [26:0] val6;
    always @(posedge clk) begin
        byp6 <= byp5; sub6 <= sub5; sg6 <= sg5; z6 <= sub5 && (dif5 == 28'd0); er6 <= er5; code6 <= code5;
        ex6 <= cyB ? (ex5 + 8'd1) : ex5; val6 <= o5v;
    end

    // ---------------- step 6: leading zeros, clamped ----------------
    reg [4:0] lz6;
    always @* begin
        lz6 = 5'd27;
        for (k = 0; k <= 26; k = k + 1)
            if (val6[k]) lz6 = 5'd26 - k[4:0];
    end
    wire [7:0] room6 = ex6 - 8'd1;
    wire [7:0] shf6 = ({3'd0, lz6} > room6) ? room6 : {3'd0, lz6};
    wire       apply6 = sub6 && !z6 && !byp6;
    wire [4:0] sh6 = apply6 ? shf6[4:0] : 5'd0;
    reg         v7;
    always @(posedge clk or negedge rst_v) if (!rst_v) v7 <= 1'b0; else v7 <= v6;
    reg         byp7, sg7, z7; reg [1:0] er7; reg [31:0] code7; reg [7:0] ex7; reg [26:0] val7;
    always @(posedge clk) begin
        byp7 <= byp6; sg7 <= sg6; z7 <= z6; er7 <= er6; code7 <= code6; ex7 <= ex6; val7 <= val6;
    end
    // the normalise shift: one kept copy per 4-bit slice (7 slices) plus one for the exponent, MSB-first layers
    localparam integer NNS = 7;
    wire [4:0] hk [0:NNS];
    for (genvar g = 0; g <= NNS; g = g + 1) begin : g_hk
        ot_v41_kreg #(.W(5)) u_k (.clk(clk), .arst_n(1'b1), .d(sh6), .q(hk[g]));
    end

    // ---------------- step 7: normalize; step 8: round increment ----------------
    wire [26:0] val8;
    for (genvar g = 0; g < NNS; g = g + 1) begin : g_nm
        wire [4:0]  c = hk[g];
        wire [26:0] s16 = c[4] ? {val7[10:0], 16'd0} : val7;
        wire [26:0] s8  = c[3] ? {s16[18:0], 8'd0} : s16;
        wire [26:0] s4  = c[2] ? {s8[22:0], 4'd0} : s8;
        wire [26:0] s2  = c[1] ? {s4[24:0], 2'd0} : s4;
        wire [26:0] sx  = c[0] ? {s2[25:0], 1'd0} : s2;
        if (g < NNS - 1) begin : g_f
            assign val8[4*g +: 4] = sx[4*g +: 4];
        end else begin : g_l
            assign val8[26:24] = sx[26:24];
        end
    end
    wire [7:0]  ex8 = ex7 - {3'd0, hk[NNS]};
    wire        inc8 = val8[2] && ((|val8[1:0]) || val8[3]);
    wire [24:0] t8 = {1'b0, val8[26:3]};
    wire [24:0] r8;
    wire        co8;
    ot_v41_inc #(.W(25)) u_i8 (.a(t8), .inc(inc8), .y(r8), .co(co8));
    reg         v9;
    always @(posedge clk or negedge rst_v) if (!rst_v) v9 <= 1'b0; else v9 <= v7;
    reg         sg9; reg [1:0] er9; reg [31:0] code9; reg [7:0] ex9; reg [23:0] rnd9;
    always @(posedge clk) begin
        sg9 <= sg7; er9 <= er7; code9 <= code7; ex9 <= ex8; rnd9 <= r8[23:0];
    end
    wire [3:0] cyk;                 // the round carry r8[24], one copy per 6-bit mantissa group (copy 3 also exponent)
    for (genvar g = 0; g < 4; g = g + 1) begin : g_cy
        ot_v41_kreg #(.W(1)) u_k (.clk(clk), .arst_n(1'b1), .d(r8[24]), .q(cyk[g]));
    end
    wire [1:0] bz [0:1];            // {byp, z} copies: output bits 15:0 (+ err), 31:16
    for (genvar g = 0; g < 2; g = g + 1) begin : g_bz
        ot_v41_kreg #(.W(2)) u_k (.clk(clk), .arst_n(1'b1), .d({byp7, z7}), .q(bz[g]));
    end

    // ---------------- step 9: encode, output select ----------------
    wire [24:0] rnd = {cyk[0], rnd9};   // rnd[24] only feeds group 0 (= cyk[0]'s own mux), so any copy is exact
    wire [23:0] man9 = {cyk[0] ? rnd[24:19] : rnd[23:18], cyk[1] ? rnd[18:13] : rnd[17:12],
                        cyk[2] ? rnd[12:7] : rnd[11:6], cyk[3] ? rnd[6:1] : rnd[5:0]};
    wire [7:0]  exo9 = cyk[3] ? (ex9 + 8'd1) : ex9;
    wire        over9 = (ex9 == 8'hff) || (cyk[3] && ex9 == 8'hfe);     // = (ex9 >= 255) || (exo9 >= 255)
    wire        subn9 = (exo9 == 8'd1) && !man9[23];
    wire [31:0] enc9 = {sg9, subn9 ? 8'd0 : exo9, man9[22:0]};
    wire        encz = enc9[30:0] == 31'd0;
    wire        killL = bz[0][0] || over9 || encz;
    wire        killH = bz[1][0] || over9 || encz;
    wire [31:0] y_d;
    assign y_d[15:0]  = bz[0][1] ? code9[15:0]  : (killL ? 16'd0 : enc9[15:0]);
    assign y_d[31:16] = bz[1][1] ? code9[31:16] : (killH ? 16'd0 : enc9[31:16]);
    wire [1:0]  err_d = bz[0][1] ? er9 : ((!bz[0][0] && over9) ? E_OVERFLOW : E_NONE);
    reg  [31:0] y_q; reg [1:0] err_q; reg vo_q;
    always @(posedge clk or negedge rst_v) if (!rst_v) begin err_q <= E_NONE; vo_q <= 1'b0; end else begin err_q <= err_d; vo_q <= v9; end
    always @(posedge clk or negedge rst_y) if (!rst_y) y_q <= 32'd0; else y_q <= y_d;
    assign y = y_q; assign err = err_q; assign valid_out = vo_q;
    if (NYK > 0) begin : g_k
        for (genvar g = 0; g < NYK; g = g + 1) begin : g_yk
            ot_v41_kreg #(.W(32), .AR(1), .RV(32'd0)) u_y (.clk(clk), .arst_n(rst_k[g]), .d(y_d), .q(yk[32*g +: 32]));
        end
    end else begin : g_nk
        assign yk = '0;
    end
    if (NVK > 0) begin : g_v
        for (genvar g = 0; g < NVK; g = g + 1) begin : g_vk
            ot_v41_kreg #(.W(1), .AR(1), .RV(1'b0)) u_v (.clk(clk), .arst_n(rst_v), .d(v9), .q(vk[g]));
        end
    end else begin : g_nv
        assign vk = '0;
    end
endmodule
