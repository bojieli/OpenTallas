`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// DS-ROM recovery lever su_hcpost (2026-10-04): the hyper-connection POST mix as ONE fused 1.2 GHz pipeline
// (default-off: new files only; nothing existing instantiates it).  It replaces the four dependent SU ops of
// tools/dshbm_baseline_measure.lower_hc_post (three accumulate passes through the vector memory and the final
// y * post pass, each paying the hub traverse, the lane's fixed M1/M2/AD/S/E1/E2 depth and a VM round trip):
//
//   out[k][i] = BF16( y[i]*post[k] + ( r3[i]*c[3][k] + ( r2[i]*c[2][k] + ( r0[i]*c[0][k] + r1[i]*c[1][k] ))))
//
// in the golden's exact order (hdc_golden_v41 add / mul: binary32, round to nearest even, every zero result +0;
// BF16 round to nearest even), on the SAME binary32 units bit for bit (ot_hdc_fp32_mul_f12_l5 / _add_f12_l4,
// bit- and cycle-identical to the fast units the SU lane builds on, closed standalone at 0.833 ns).
//
// Per element the five products are independent and issue together; only the four adds are serial:
//   mul 5 | add 4 | add 4 | add 4 | add 4 | BF16 round + output register 1   = 22 cycles (LANE_D)
//
// Shape: NG element groups (one i each) x 4 lanes (k = 0..3); a beat carries r0..r3[i] and y[i] of NG
// consecutive i.  At NG = 256 (1,024 outputs a cycle, the SU's width) the [4, 5120] output is 20 beats.
// Hub wire: WIN register stages carry a beat (and the op's comb / post words with its go) from the vector memory
// to the lanes, WOUT carry the outputs back (the SU's BCAST 22 / RET 15 slow stages re-staged at the 1.2 GHz
// wire reach: 22 x 748/504 -> 33, 15 x 748/504 -> 23).  The traverse is paid ONCE for the chain.
// The fused sum of squares the SU op carried for the next hyper-connection mix is NOT here: the next mix's
// hc.sumsq is its own graph node on the parallel mix branch (measured on the SU); it reads this output.
// ---------------------------------------------------------------------------
module ot_dsrom_su_hcpost_lane #(
    parameter integer ML = 5,           // multiplier latency: 5 (ot_hdc_fp32_mul_f12_l5) or 6 (_l6, input-side cut)
    parameter integer AL = 4            // adder latency: 4 (ot_hdc_fp32_add_f12_l4) or 5 (_l5x, decode cut)
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] r0, r1, r2, r3, y,
    input  wire [31:0] c0, c1, c2, c3, p,      // c[j][k] of this lane's k, post[k]
    output reg         vo,
    output reg  [31:0] o,
    output reg         fault
);
    /*verilator hier_block*/
    wire [31:0] m0, m1, m2, m3, m4, a1, a2, a3, a4, m2d, m3d, m4d;
    wire [1:0]  e0, e1, e2, e3, e4, ea1, ea2, ea3, ea4;
    wire        vm, va1, va2, va3, va4;
    generate if (ML == 6) begin : g_u_m0
        ot_hdc_fp32_mul_f12_l6 u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(r0), .b(c0), .y(m0), .err(e0), .valid_out(vm));
    end else begin : g_u_m05
        ot_hdc_fp32_mul_f12_l5 u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(r0), .b(c0), .y(m0), .err(e0), .valid_out(vm));
    end endgenerate
    generate if (ML == 6) begin : g_u_m1
        ot_hdc_fp32_mul_f12_l6 u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(r1), .b(c1), .y(m1), .err(e1), .valid_out());
    end else begin : g_u_m15
        ot_hdc_fp32_mul_f12_l5 u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(r1), .b(c1), .y(m1), .err(e1), .valid_out());
    end endgenerate
    generate if (ML == 6) begin : g_u_m2
        ot_hdc_fp32_mul_f12_l6 u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(r2), .b(c2), .y(m2), .err(e2), .valid_out());
    end else begin : g_u_m25
        ot_hdc_fp32_mul_f12_l5 u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(r2), .b(c2), .y(m2), .err(e2), .valid_out());
    end endgenerate
    generate if (ML == 6) begin : g_u_m3
        ot_hdc_fp32_mul_f12_l6 u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(r3), .b(c3), .y(m3), .err(e3), .valid_out());
    end else begin : g_u_m35
        ot_hdc_fp32_mul_f12_l5 u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(r3), .b(c3), .y(m3), .err(e3), .valid_out());
    end endgenerate
    ot_hdc_fp32_mul_f12_l5 u_m4 (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(y),  .b(p),  .y(m4), .err(e4), .valid_out());
    generate if (AL == 5) begin : g_u_a1
        ot_hdc_fp32_add_f12_l5x u (.clk(clk), .rst_n(rst_n), .valid_in(vm), .a(m0), .b(m1), .y(a1), .err(ea1), .valid_out(va1));
    end else begin : g_u_a14
        ot_hdc_fp32_add_f12_l4 u (.clk(clk), .rst_n(rst_n), .valid_in(vm), .a(m0), .b(m1), .y(a1), .err(ea1), .valid_out(va1));
    end endgenerate
    ot_hdc_delay #(.W(32), .D(AL))  u_d2 (.clk(clk), .rst_n(rst_n), .d(m2), .q(m2d));
    generate if (AL == 5) begin : g_u_a2
        ot_hdc_fp32_add_f12_l5x u (.clk(clk), .rst_n(rst_n), .valid_in(va1), .a(m2d), .b(a1), .y(a2), .err(ea2), .valid_out(va2));
    end else begin : g_u_a24
        ot_hdc_fp32_add_f12_l4 u (.clk(clk), .rst_n(rst_n), .valid_in(va1), .a(m2d), .b(a1), .y(a2), .err(ea2), .valid_out(va2));
    end endgenerate
    ot_hdc_delay #(.W(32), .D(2*AL))  u_d3 (.clk(clk), .rst_n(rst_n), .d(m3), .q(m3d));
    generate if (AL == 5) begin : g_u_a3
        ot_hdc_fp32_add_f12_l5x u (.clk(clk), .rst_n(rst_n), .valid_in(va2), .a(m3d), .b(a2), .y(a3), .err(ea3), .valid_out(va3));
    end else begin : g_u_a34
        ot_hdc_fp32_add_f12_l4 u (.clk(clk), .rst_n(rst_n), .valid_in(va2), .a(m3d), .b(a2), .y(a3), .err(ea3), .valid_out(va3));
    end endgenerate
    ot_hdc_delay #(.W(32), .D(3*AL)) u_d4 (.clk(clk), .rst_n(rst_n), .d(m4), .q(m4d));
    generate if (AL == 5) begin : g_u_a4
        ot_hdc_fp32_add_f12_l5x u (.clk(clk), .rst_n(rst_n), .valid_in(va3), .a(m4d), .b(a3), .y(a4), .err(ea4), .valid_out(va4));
    end else begin : g_u_a44
        ot_hdc_fp32_add_f12_l4 u (.clk(clk), .rst_n(rst_n), .valid_in(va3), .a(m4d), .b(a3), .y(a4), .err(ea4), .valid_out(va4));
    end endgenerate
    // BF16 round to nearest even: (a4[31:16] + inc) << 16, inc = a4[15] & (a4[16] | a4[14:0] != 0)
    wire [15:0] hi;
    ot_hdc_inc_k #(.W(16)) u_rnd (.a(a4[31:16]), .inc(a4[15] & (a4[16] | (|a4[14:0]))), .y(hi), .co());
    // a multiply error is held to the add that consumes it (the faults are a sticky status, not data)
    reg [3*AL:0] fm;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin vo <= 1'b0; fault <= 1'b0; fm <= 0; end
        else begin
            vo <= va4;
            fm <= {fm[3*AL-1:0], vm && ((e0 | e1 | e2 | e3 | e4) != 2'd0)};
            fault <= fault | fm[0] | (va1 && ea1 != 2'd0) | (va2 && ea2 != 2'd0) | (va3 && ea3 != 2'd0) |
                     (va4 && ea4 != 2'd0);
        end
    end
    always @(posedge clk) o <= {hi, 16'd0};
endmodule

// a W-bit bundle delayed D register stages (D = 0: a wire); the valid bit resets
module ot_dsrom_su_hcpost_wire #(parameter integer W = 32, parameter integer D = 1) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         v,
    input  wire [W-1:0] d,
    output wire         vq,
    output wire [W-1:0] q
);
    generate if (D == 0) begin : g_w
        assign vq = v;
        assign q = d;
    end else begin : g_r
        reg         vl [0:D-1];
        reg [W-1:0] dl [0:D-1];
        integer s;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin
                for (s = 0; s < D; s = s + 1) vl[s] <= 1'b0;
            end else begin
                vl[0] <= v;
                for (s = 1; s < D; s = s + 1) vl[s] <= vl[s-1];
            end
        end
        always @(posedge clk) begin
            dl[0] <= d;
            for (s = 1; s < D; s = s + 1) dl[s] <= dl[s-1];
        end
        assign vq = vl[D-1];
        assign q = dl[D-1];
    end endgenerate
endmodule

// one element group: r0..r3 and y of one i through WIN hub stages, the operand register (the op words land in
// the broadcast registers the cycle before), 4 lanes (k = 0..3), WOUT hub stages back
module ot_dsrom_su_hcpost_group #(
    parameter integer WIN = 33,
    parameter integer WOUT = 23,
    parameter integer ML = 5,
    parameter integer AL = 4
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          in_v,
    input  wire [127:0]  r,
    input  wire [31:0]   y,
    input  wire [511:0]  c,
    input  wire [127:0]  p,
    output wire          out_v,
    output wire [127:0]  o,
    output wire          fault
);
    /*verilator hier_block*/
    wire         b_v;
    wire [159:0] b_d;
    ot_dsrom_su_hcpost_wire #(.W(160), .D(WIN)) u_win (.clk(clk), .rst_n(rst_n), .v(in_v), .d({y, r}), .vq(b_v), .q(b_d));
    reg          x_v;
    reg  [159:0] x_d;
    always @(posedge clk or negedge rst_n) if (!rst_n) x_v <= 1'b0; else x_v <= b_v;
    always @(posedge clk) x_d <= b_d;
    wire [127:0] l_o;
    wire [3:0]   l_v, l_f;
    genvar k;
    generate for (k = 0; k < 4; k = k + 1) begin : g_k
        ot_dsrom_su_hcpost_lane #(.ML(ML), .AL(AL)) u (
            .clk(clk), .rst_n(rst_n), .v(x_v),
            .r0(x_d[0 +: 32]), .r1(x_d[32 +: 32]), .r2(x_d[64 +: 32]), .r3(x_d[96 +: 32]), .y(x_d[128 +: 32]),
            .c0(c[32*(0+k) +: 32]), .c1(c[32*(4+k) +: 32]), .c2(c[32*(8+k) +: 32]), .c3(c[32*(12+k) +: 32]),
            .p(p[32*k +: 32]), .vo(l_v[k]), .o(l_o[32*k +: 32]), .fault(l_f[k]));
    end endgenerate
    ot_dsrom_su_hcpost_wire #(.W(128), .D(WOUT)) u_wout (.clk(clk), .rst_n(rst_n), .v(l_v[0]), .d(l_o), .vq(out_v), .q(o));
    assign fault = |l_f;
endmodule

module ot_dsrom_su_hcpost #(
    parameter integer NG   = 256,   // element groups: NG x 4 outputs a beat (256: 1,024 a cycle)
    parameter integer WIN  = 33,    // hub stages, vector memory -> lanes (1.2 GHz reach)
    parameter integer WOUT = 23,    // hub stages, lanes -> vector memory
    parameter integer ML = 5,
    parameter integer AL = 4
) (
    input  wire                 clk,
    input  wire                 rst_n,
    // op words (with the op's first beat): comb[j][k] at [32*(4j+k)], post[k] at [32*k]
    input  wire                 go,
    input  wire [16*32-1:0]     comb,
    input  wire [4*32-1:0]      post,
    // a beat: r_j of group g at [32*(4g+j)], y of group g at [32*g]
    input  wire                 in_v,
    input  wire [NG*4*32-1:0]   in_r,
    input  wire [NG*32-1:0]     in_y,
    // outputs at the vector memory: group g, k at [32*(4g+k)] (BF16 in the high half)
    output wire                 out_v,
    output wire [NG*4*32-1:0]   out_d,
    output wire                 fault
);
    // ---- the op words travel the hub traverse in with go and land in the (lane-tile) broadcast registers
    wire             w_v;
    wire [20*32-1:0] w_d;
    ot_dsrom_su_hcpost_wire #(.W(20*32), .D(WIN)) u_wop (.clk(clk), .rst_n(rst_n), .v(go), .d({post, comb}),
                                                        .vq(w_v), .q(w_d));
    reg [16*32-1:0] c_r;
    reg [4*32-1:0]  p_r;
    always @(posedge clk) if (w_v) begin c_r <= w_d[16*32-1:0]; p_r <= w_d[20*32-1:16*32]; end
    // ---- element groups: each carries its own slice of the beat through the hub stages (identical timing)
    wire [NG-1:0] g_v, g_f;
    genvar g;
    generate for (g = 0; g < NG; g = g + 1) begin : g_g
        ot_dsrom_su_hcpost_group #(.WIN(WIN), .WOUT(WOUT), .ML(ML), .AL(AL)) u (
            .clk(clk), .rst_n(rst_n), .in_v(in_v), .r(in_r[32*4*g +: 128]), .y(in_y[32*g +: 32]), .c(c_r), .p(p_r),
            .out_v(g_v[g]), .o(out_d[32*4*g +: 128]), .fault(g_f[g]));
    end endgenerate
    assign out_v = g_v[0];
    assign fault = |g_f;
endmodule
