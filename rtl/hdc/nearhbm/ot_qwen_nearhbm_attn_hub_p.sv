`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// Near-HBM attention hub, TIMING SUCCESSOR of ot_qwen_nearhbm_attn_hub (that file is pinned and untouched).  NEW,
// DEFAULT-OFF: nothing shipped instantiates it.  It computes exactly what the parent computes, in the same order
// (max, Z tree, reciprocal, P.V levels 8-9, x 1/Z), and differs only in pipelining, for 1.2 GHz at SS in ASAP7.
//
// Hub r7 (the parent, routed at 0.833 ns) failed by 1,037 ps.  Its paths were wire and fan-out, not arithmetic:
//   - every port faced a 738 ps clock tree with 20 % IO budgets;
//   - port and decoder signals fanned out to the 512-entry Z store and the 256 x 512-bit beat store;
//   - one select register drove each 1,024-bit or 2,048-bit operand mux;
//   - rst_n fanned out to ~65 k asynchronous-reset flops.
// This successor changes the following:
//   PORTS     Every input is registered at the boundary (_b).  Its decode (one-hot write enables) gets a second
//             registered stage (_c).  Every output is registered.  The ports therefore face registered neighbours
//             (the d2d link ends), and the block is timed register-to-register (--false-path-io).
//   RESET     rst_n reaches only the boundary valid flops, a root flop and per-unit leaf flops (keep_hierarchy).  Each
//             unit's asynchronous reset comes from its own leaf, released two clocks after rst_n.  Assertion is still
//             asynchronous everywhere.
//   READS     The Z-store and beat-store read addresses are registered one cycle ahead into duplicated copies
//             (keep_hierarchy; one copy per 16 or 32 output bits).  The beat operands get a second register (s*_r)
//             at the adders.
//   WRITES    Tree results are written one cycle after the adder, through registered one-hot enables.
//   HAZARD    The tree keeps the parent's level cadence (zwt = ADD_LAT + 3).  The read moved +1 and the write moved
//             +2, so the read-after-write margin drops from 2 cycles to 1.  A simulation check flags a read of an entry
//             whose write is still in flight.
// Added latency (cycles): inputs +2, outputs +1, Z/recip read +1, P.V +2 (the tree cadence is unchanged).
// ---------------------------------------------------------------------------------------------------------------------
module ot_nhb_rst_leaf (input wire clk, input wire arst_n, input wire d, output reg q);
    always @(posedge clk or negedge arst_n) if (!arst_n) q <= 1'b0; else q <= d;
endmodule

// register copies that synthesis must not merge with their siblings (instantiated with keep_hierarchy); fixed
// widths, no parameters (Yosys 0.68 asserts re-elaborating a parameterised keep_hierarchy module here)
module ot_nhb_dup_a6 (input wire clk, input wire [5:0] d, output reg [5:0] q);
    always @(posedge clk) q <= d;
endmodule
module ot_nhb_dup_we256 (input wire clk, input wire rst_n, input wire [255:0] d, output reg [255:0] q);
    always @(posedge clk or negedge rst_n) if (!rst_n) q <= 256'd0; else q <= d;
endmodule

module ot_qwen_nearhbm_attn_hub_p #(
    parameter integer HD = 128,
    parameter integer ADD_LAT = 7,
    parameter integer MUL_LAT = 6,
    parameter integer ZW = 4
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          start,
    input  wire [3:0]    si_valid,
    input  wire [7:0]    si_type,
    input  wire [3:0]    si_g,
    input  wire [7:0]    si_hh,
    input  wire [15:0]   si_k,
    input  wire [3:0]    si_any,
    input  wire [127:0]  si_data,
    input  wire [3:0]    pi_valid,
    input  wire [3:0]    pi_g,
    input  wire [23:0]   pi_beat,
    input  wire [2047:0] pi_data,
    output reg           mo_valid,
    output reg           mo_g,
    output reg  [1:0]    mo_hh,
    output reg  [31:0]   mo_data,
    output reg           out_valid,
    output reg           out_g,
    output reg  [5:0]    out_beat,
    output reg  [511:0]  out_data,
    output reg           fault,
    output reg  [7:0]    ev
);
    localparam integer NBEAT = 4 * HD / 16;
    localparam integer BPH = HD / 16;
    integer sd_, s_, s2_, s3_, s4_, i_, i2_, z, z2_, z3_, z4_, e_, e2_, e3_, e4_;
    function automatic fgt(input [31:0] a, input [31:0] b);
        fgt = (a[31] != b[31]) ? !a[31] : (!a[31] ? (a[30:0] > b[30:0]) : (a[30:0] < b[30:0]));
    endfunction

    // ---- reset tree: root + one leaf per unit ------------------------------------------------------------------------
    // leaves: 0 input stage c, 1 M control, 2 Z control, 3 zv, 4 P control, 5 tag, 6 recip, 7 output stage,
    //         8.. 8+ZW-1 Z tag lines, then 4*ZW Z adders, then 64 P.V units (4 per lane)
    localparam integer L_ZI = 8, L_ZA = 8 + ZW, L_PV = 8 + 5 * ZW, NL = 8 + 5 * ZW + 64;
    wire r0;
    wire [NL-1:0] rl;
    (* keep_hierarchy *) ot_nhb_rst_leaf u_r0 (.clk(clk), .arst_n(rst_n), .d(1'b1), .q(r0));
    genvar gr;
    generate for (gr = 0; gr < NL; gr = gr + 1) begin : g_rl
        (* keep_hierarchy *) ot_nhb_rst_leaf u_l (.clk(clk), .arst_n(rst_n), .d(r0), .q(rl[gr]));
    end endgenerate

    // ---- boundary input registers (_b) and decode stage (_c) ---------------------------------------------------------
    reg          start_b;
    reg [3:0]    siv_b, piv_b;
    reg [7:0]    sit_b;  reg [3:0] sig_b;  reg [7:0] sih_b;  reg [15:0] sik_b;  reg [3:0] sia_b;  reg [127:0] sid_b;
    reg [3:0]    pig_b;  reg [23:0] pib_b; reg [2047:0] pid_b;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin start_b <= 1'b0; siv_b <= 4'd0; piv_b <= 4'd0; end
        else begin start_b <= start; siv_b <= si_valid; piv_b <= pi_valid; end
    always @(posedge clk) begin
        sit_b <= si_type; sig_b <= si_g; sih_b <= si_hh; sik_b <= si_k; sia_b <= si_any; sid_b <= si_data;
        pig_b <= pi_g; pib_b <= pi_beat; pid_b <= pi_data;
    end
    // one-hot write enables, decoded from _b
    reg [31:0]  lm_we_n;
    reg [511:0] zs_we_n;
    reg [255:0] pb_we_n;
    always @* begin
        lm_we_n = 32'd0; zs_we_n = 512'd0; pb_we_n = 256'd0;
        for (sd_ = 0; sd_ < 4; sd_ = sd_ + 1) begin
            if (siv_b[sd_] && sit_b[2*sd_ +: 2] == 2'd0) lm_we_n[{sig_b[sd_], sd_[1:0], sih_b[2*sd_ +: 2]}] = 1'b1;
            if (siv_b[sd_] && sit_b[2*sd_ +: 2] == 2'd1)
                zs_we_n[{sig_b[sd_], sih_b[2*sd_ +: 2], sik_b[4*sd_ +: 4], sd_[1:0]}] = 1'b1;
            if (piv_b[sd_]) pb_we_n[{pig_b[sd_], sd_[1:0], pib_b[6*sd_ +: 5]}] = 1'b1;
        end
    end
    reg          start_c;
    reg [3:0]    siv_c, piv_c;
    reg [7:0]    sit_c;  reg [3:0] sig_c;  reg [3:0] sia_c;  reg [127:0] sid_c;  reg [3:0] pig_c;
    reg [2047:0] pid_c;
    reg [31:0]   lm_we;
    reg [511:0]  zs_we;
    wire [1023:0] pb_we;                          // one copy per 128-bit quarter of a beat: [256*q + entry]
    always @(posedge clk or negedge rl[0])
        if (!rl[0]) begin start_c <= 1'b0; siv_c <= 4'd0; piv_c <= 4'd0; lm_we <= 32'd0; zs_we <= 512'd0; end
        else begin start_c <= start_b; siv_c <= siv_b; piv_c <= piv_b; lm_we <= lm_we_n; zs_we <= zs_we_n; end
    always @(posedge clk) begin
        sit_c <= sit_b; sig_c <= sig_b; sia_c <= sia_b; sid_c <= sid_b; pig_c <= pig_b; pid_c <= pid_b;
    end
    genvar gq;
    generate for (gq = 0; gq < 4; gq = gq + 1) begin : g_pbwe
        (* keep_hierarchy *) ot_nhb_dup_we256 u_we (.clk(clk), .rst_n(rl[0]), .d(pb_we_n), .q(pb_we[256*gq +: 256]));
    end endgenerate

    // ---- max --------------------------------------------------------------------------------------------------------
    reg [31:0] lm [0:31];                        // {g, s, h}
    reg [7:0]  lany;
    reg [4:0]  lcnt0, lcnt1;
    reg [1:0]  msent;
    wire       mg = msent[0];
    reg [2:0]  mh;
    wire       mready = !msent[mg] && (mg ? (lcnt1 == 5'd16) : (lcnt0 == 5'd16));
    reg        ma_v, mb_v;
    reg        ma_g, mb_g;
    reg [1:0]  ma_h, mb_h;
    reg [127:0] ma_x;
    reg [3:0]  ma_a;
    reg [63:0] mb_x;
    reg [1:0]  mb_a;
    reg        mo_valid_i, mo_g_i;
    reg [1:0]  mo_hh_i;
    reg [31:0] mo_data_i;
    function automatic [32:0] fmax2(input [31:0] x, input ax, input [31:0] y, input ay);
        fmax2 = !ax ? {ay, y} : (!ay ? {1'b1, x} : {1'b1, (fgt(y, x) ? y : x)});
    endfunction
    wire [32:0] m01 = fmax2(ma_x[31:0], ma_a[0], ma_x[63:32], ma_a[1]);
    wire [32:0] m23 = fmax2(ma_x[95:64], ma_a[2], ma_x[127:96], ma_a[3]);
    wire [32:0] mfin = fmax2(mb_x[31:0], mb_a[0], mb_x[63:32], mb_a[1]);
    always @(posedge clk or negedge rl[1]) begin
        if (!rl[1]) begin ma_v <= 1'b0; mb_v <= 1'b0; end
        else begin ma_v <= mready && !start_c; mb_v <= ma_v && !start_c; end
    end
    always @(posedge clk) begin
        ma_g <= mg; ma_h <= mh[1:0];
        for (s2_ = 0; s2_ < 4; s2_ = s2_ + 1) begin
            ma_x[32*s2_ +: 32] <= lm[{mg, s2_[1:0], mh[1:0]}];
            ma_a[s2_] <= lany[4*mg + s2_];
        end
        mb_g <= ma_g; mb_h <= ma_h;
        mb_x <= {m23[31:0], m01[31:0]}; mb_a <= {m23[32], m01[32]};
        if (!start_c)
            for (e4_ = 0; e4_ < 32; e4_ = e4_ + 1)
                if (lm_we[e4_]) lm[e4_] <= sid_c[32*(e4_/4 % 4) +: 32];
    end
    always @(posedge clk or negedge rl[1]) begin
        if (!rl[1]) begin lcnt0 <= 0; lcnt1 <= 0; lany <= 0; msent <= 0; mh <= 0; mo_valid_i <= 1'b0; end
        else begin
            mo_valid_i <= 1'b0;
            if (start_c) begin lcnt0 <= 0; lcnt1 <= 0; lany <= 0; msent <= 0; mh <= 0; end
            else begin
                for (s3_ = 0; s3_ < 4; s3_ = s3_ + 1)
                    if (siv_c[s3_] && sit_c[2*s3_ +: 2] == 2'd0 && sia_c[s3_]) lany[4*sig_c[s3_] + s3_] <= 1'b1;
                lcnt0 <= lcnt0 + ((siv_c[0] && sit_c[1:0] == 0 && !sig_c[0]) ? 1 : 0)
                               + ((siv_c[1] && sit_c[3:2] == 0 && !sig_c[1]) ? 1 : 0)
                               + ((siv_c[2] && sit_c[5:4] == 0 && !sig_c[2]) ? 1 : 0)
                               + ((siv_c[3] && sit_c[7:6] == 0 && !sig_c[3]) ? 1 : 0);
                lcnt1 <= lcnt1 + ((siv_c[0] && sit_c[1:0] == 0 && sig_c[0]) ? 1 : 0)
                               + ((siv_c[1] && sit_c[3:2] == 0 && sig_c[1]) ? 1 : 0)
                               + ((siv_c[2] && sit_c[5:4] == 0 && sig_c[2]) ? 1 : 0)
                               + ((siv_c[3] && sit_c[7:6] == 0 && sig_c[3]) ? 1 : 0);
                if (mready) begin
                    if (mh == 3'd3) begin mh <= 0; msent[mg] <= 1'b1; end else mh <= mh + 3'd1;
                end
                if (mb_v) begin mo_valid_i <= 1'b1; mo_g_i <= mb_g; mo_hh_i <= mb_h; mo_data_i <= mfin[31:0]; end
            end
        end
    end

    // ---- Z: block sums, tree, reciprocal ------------------------------------------------------------------------------
    reg [31:0] zm [0:511];                        // {g, h, node}
    reg [511:0] zv;
    reg [2:0]  zdc0, zdc1;
    reg        zrun, zg, zwait_recip;
    reg [1:0]  zdone_tree;
    reg [2:0]  zl;
    reg [5:0]  zp;
    reg [3:0]  zwt;
    reg        fault_i;
    wire [6:0] znp = 7'd64 >> zl;
    // issue (stage 0): the lane valids and the read address {g, pair}, registered into duplicated copies
    reg [ZW-1:0] ziv;
    reg [5:0]    zi [0:ZW-1];
    reg [6:0]    pz;
    always @* begin
        for (z = 0; z < ZW; z = z + 1) begin
            pz = {1'b0, zp} + z;
            ziv[z] = zrun && (zwt == 0) && (pz < znp);
            zi[z] = pz[5:0];
        end
    end
    reg [ZW-1:0] ziv0, ziv1;
    reg [ZW*6-1:0] zi0, zi1;
    reg          zg0, zg1;
    always @(posedge clk or negedge rl[2]) if (!rl[2]) begin ziv0 <= 0; ziv1 <= 0; end else begin ziv0 <= ziv; ziv1 <= ziv0; end
    always @(posedge clk) begin
        for (z2_ = 0; z2_ < ZW; z2_ = z2_ + 1) zi0[6*z2_ +: 6] <= zi[z2_];
        zi1 <= zi0; zg0 <= zg; zg1 <= zg0;
    end
    // read (stage 1): one address copy per (lane, head, operand, 16-bit half)
    reg [ZW*4*32-1:0] za_r, zb_r;
    wire [ZW*4*32-1:0] zy;
    wire [ZW*4-1:0] zvo, zerr;
    wire [ZW*8-1:0] zwi;                           // {valid, g, node}
    genvar gz, gh, gb, gf;
    generate for (gz = 0; gz < ZW; gz = gz + 1) begin : g_z
        for (gh = 0; gh < 4; gh = gh + 1) begin : g_h
            for (gb = 0; gb < 2; gb = gb + 1) begin : g_b
                for (gf = 0; gf < 2; gf = gf + 1) begin : g_f
                    wire [5:0] a;                  // {g, pair[4:0]}
                    wire [5:0] pzz = {1'b0, zp[5:0]} + gz;
                    (* keep_hierarchy *) ot_nhb_dup_a6 u_a (.clk(clk), .d({zg, pzz[4:0]}), .q(a));
                    wire [8:0] ix = {a[5], gh[1:0], a[4:0], gb[0]};
                    wire [15:0] rd = zv[ix] ? zm[ix][16*gf +: 16] : 16'd0;
                    if (gb == 0) begin : g_a
                        always @(posedge clk) za_r[32*(4*gz+gh) + 16*gf +: 16] <= rd;
                    end else begin : g_bb
                        always @(posedge clk) zb_r[32*(4*gz+gh) + 16*gf +: 16] <= rd;
                    end
                end
            end
        end
        ot_hdc_delay #(.W(8), .D(ADD_LAT), .RESET(1)) u_i (.clk(clk), .rst_n(rl[L_ZI + gz]),
                                                           .d({ziv1[gz], zg1, zi1[6*gz +: 6]}), .q(zwi[8*gz +: 8]));
        for (gh = 0; gh < 4; gh = gh + 1) begin : g_h2
            wire [1:0] err;
            ot_hdc_fp32_add_lat #(.LAT(ADD_LAT)) u_add (
                .clk(clk), .rst_n(rl[L_ZA + 4*gz + gh]), .valid_in(ziv1[gz]), .a(za_r[32*(4*gz+gh) +: 32]),
                .b(zb_r[32*(4*gz+gh) +: 32]), .y(zy[32*(4*gz+gh) +: 32]), .err(err), .valid_out(zvo[4*gz+gh]));
            assign zerr[4*gz+gh] = zvo[4*gz+gh] && (err != 2'd0);
        end
    end endgenerate
    // write (one cycle after the adder): registered one-hot {g, node} per lane
    reg [127:0] zw_oh [0:ZW-1];
    reg [ZW*4*32-1:0] zy_r;
    always @(posedge clk or negedge rl[2]) begin
        if (!rl[2]) for (z3_ = 0; z3_ < ZW; z3_ = z3_ + 1) zw_oh[z3_] <= 128'd0;
        else for (z3_ = 0; z3_ < ZW; z3_ = z3_ + 1) begin
            zw_oh[z3_] <= 128'd0;
            if (zwi[8*z3_ + 7]) zw_oh[z3_][zwi[8*z3_ +: 7]] <= 1'b1;
        end
    end
    always @(posedge clk) zy_r <= zy;
    // reciprocal of the 4 Z of a g: address registered (stage 0), then the read (stage 1)
    reg        rv0, rv1;
    reg [2:0]  ra0;                                 // {g, h}
    reg [31:0] rx;
    reg [2:0]  rh;
    wire [31:0] ry;
    wire        rvo, rfault;
    ot_qwen_nearhbm_recip_p #(.LA(7), .LM(7)) u_recip (.clk(clk), .rst_n(rl[6]), .v(rv1), .x(rx), .y(ry), .vo(rvo),
                                                     .fault(rfault));
    reg [2:0]  rcnt;
    reg [31:0] rz [0:7];
    reg [1:0]  rz_ok;
    reg        rg_out;
    always @(posedge clk or negedge rl[6]) if (!rl[6]) rv1 <= 1'b0; else rv1 <= rv0;
    always @(posedge clk) begin
        rx <= zv[{ra0[2], ra0[1:0], 6'd0}] ? zm[{ra0[2], ra0[1:0], 6'd0}] : 32'd0;
        for (e_ = 0; e_ < 512; e_ = e_ + 1) begin
            for (z4_ = 0; z4_ < ZW; z4_ = z4_ + 1)
                if (zw_oh[z4_][{e_[8], e_[5:0]}]) zm[e_] <= zy_r[32*(4*z4_ + e_[7:6]) +: 32];
            if (zs_we[e_]) zm[e_] <= sid_c[32*(e_ % 4) +: 32];
        end
        if (rvo) rz[{rg_out, rcnt[1:0]}] <= ry;
    end
    always @(posedge clk or negedge rl[3]) begin
        if (!rl[3]) zv <= 0;
        else if (start_c) zv <= 0;
        else
            for (e2_ = 0; e2_ < 512; e2_ = e2_ + 1) begin
                for (i2_ = 0; i2_ < ZW; i2_ = i2_ + 1) if (zw_oh[i2_][{e2_[8], e2_[5:0]}]) zv[e2_] <= 1'b1;
                if (zs_we[e2_]) zv[e2_] <= 1'b1;
            end
    end
    wire [15:0] pf;
    always @(posedge clk or negedge rl[2]) begin
        if (!rl[2]) begin
            zdc0 <= 0; zdc1 <= 0; zrun <= 1'b0; zg <= 1'b0; zdone_tree <= 2'b00; zl <= 3'd1; zp <= 0; zwt <= 0;
            rv0 <= 1'b0; rh <= 0; rcnt <= 0; rz_ok <= 2'b00; zwait_recip <= 1'b0; fault_i <= 1'b0;
        end else begin
            rv0 <= 1'b0;
            if (|zerr || (rvo && rfault) || (|pf)) fault_i <= 1'b1;
            if (start_c) begin
                zdc0 <= 0; zdc1 <= 0; zrun <= 1'b0; zg <= 1'b0; zdone_tree <= 2'b00; rz_ok <= 2'b00; rcnt <= 0;
                zwait_recip <= 1'b0; fault_i <= 1'b0;
            end else begin
                zdc0 <= zdc0 + ((siv_c[0] && sit_c[1:0] == 2 && !sig_c[0]) ? 1 : 0)
                             + ((siv_c[1] && sit_c[3:2] == 2 && !sig_c[1]) ? 1 : 0)
                             + ((siv_c[2] && sit_c[5:4] == 2 && !sig_c[2]) ? 1 : 0)
                             + ((siv_c[3] && sit_c[7:6] == 2 && !sig_c[3]) ? 1 : 0);
                zdc1 <= zdc1 + ((siv_c[0] && sit_c[1:0] == 2 && sig_c[0]) ? 1 : 0)
                             + ((siv_c[1] && sit_c[3:2] == 2 && sig_c[1]) ? 1 : 0)
                             + ((siv_c[2] && sit_c[5:4] == 2 && sig_c[2]) ? 1 : 0)
                             + ((siv_c[3] && sit_c[7:6] == 2 && sig_c[3]) ? 1 : 0);
                if (!zrun && !zwait_recip) begin
                    if (!zdone_tree[0] && zdc0 == 3'd4) begin zrun <= 1'b1; zg <= 1'b0; zl <= 3'd1; zp <= 0; zwt <= 0; end
                    else if (zdone_tree[0] && !zdone_tree[1] && zdc1 == 3'd4) begin
                        zrun <= 1'b1; zg <= 1'b1; zl <= 3'd1; zp <= 0; zwt <= 0;
                    end
                end else if (zrun) begin
                    if (zwt != 0) begin
                        zwt <= zwt - 4'd1;
                        if (zwt == 4'd1) begin
                            if (zl == 3'd6) begin zrun <= 1'b0; zwait_recip <= 1'b1; rh <= 0; end
                            else begin zl <= zl + 3'd1; zp <= 0; end
                        end
                    end else if ({1'b0, zp} + ZW >= znp) begin zp <= 0; zwt <= ADD_LAT + 3; end
                    else zp <= zp + ZW;
                end else if (zwait_recip) begin
                    if (rh < 3'd4) begin
                        rv0 <= 1'b1; ra0 <= {zg, rh[1:0]};
                        rh <= rh + 3'd1; rg_out <= zg;
                    end else if (rcnt == 3'd4) begin
                        rcnt <= 0; zwait_recip <= 1'b0; zdone_tree[zg] <= 1'b1; rz_ok[zg] <= 1'b1;
                    end
                end
                if (rvo) rcnt <= rcnt + 3'd1;
            end
        end
    end
`ifndef SYNTHESIS
    // read-after-write check: a tree or reciprocal read of an entry whose tree write is still in flight
    integer infl [0:511];
    integer zc_, ze_;
    initial for (ze_ = 0; ze_ < 512; ze_ = ze_ + 1) infl[ze_] = 0;
    integer zh_, zk_;
    always @(posedge clk) if (rl[2]) begin
        // reads this cycle (lanes issued last cycle, and the reciprocal read) against writes still in flight
        for (zc_ = 0; zc_ < ZW; zc_ = zc_ + 1)
            if (ziv0[zc_])
                for (zh_ = 0; zh_ < 4; zh_ = zh_ + 1)
                    if (infl[{zg0, zh_[1:0], zi0[6*zc_ +: 5], 1'b0}] != 0 || infl[{zg0, zh_[1:0], zi0[6*zc_ +: 5], 1'b1}] != 0) begin
                        $display("NHB_HUB_P RAW HAZARD: tree read of an in-flight entry"); $stop;
                    end
        if (rv0 && infl[{ra0[2], ra0[1:0], 6'd0}] != 0) begin
            $display("NHB_HUB_P RAW HAZARD: reciprocal read of an in-flight entry"); $stop;
        end
        // writes landing at this edge, then the lanes that read this cycle go in flight
        for (zc_ = 0; zc_ < ZW; zc_ = zc_ + 1)
            for (ze_ = 0; ze_ < 128; ze_ = ze_ + 1)
                if (zw_oh[zc_][ze_])
                    for (zk_ = 0; zk_ < 4; zk_ = zk_ + 1)
                        infl[{ze_[6], zk_[1:0], ze_[5:0]}] = infl[{ze_[6], zk_[1:0], ze_[5:0]}] - 1;
        for (zc_ = 0; zc_ < ZW; zc_ = zc_ + 1)
            if (ziv0[zc_])
                for (zh_ = 0; zh_ < 4; zh_ = zh_ + 1)
                    infl[{zg0, zh_[1:0], zi0[6*zc_ +: 6]}] = infl[{zg0, zh_[1:0], zi0[6*zc_ +: 6]}] + 1;
    end
`endif

    // ---- P.V: levels 8-9 and x 1/Z ----------------------------------------------------------------------------------
    reg [511:0] pb [0:255];                        // {g, s, beat}
    reg [5:0]   pc [0:7];
    reg         pg;
    reg [5:0]   pp;
    reg [1:0]   pdone;
    always @(posedge clk)
        for (e3_ = 0; e3_ < 256; e3_ = e3_ + 1)
            for (s4_ = 0; s4_ < 4; s4_ = s4_ + 1)
                if (pb_we[256*s4_ + e3_]) pb[e3_][128*s4_ +: 128] <= pid_c[512*((e3_ / 32) % 4) + 128*s4_ +: 128];
    wire p_ready = rz_ok[pg] && !pdone[pg] && (pc[{pg, 2'd0}] > pp) && (pc[{pg, 2'd1}] > pp) &&
                   (pc[{pg, 2'd2}] > pp) && (pc[{pg, 2'd3}] > pp);
    always @(posedge clk or negedge rl[4]) begin
        if (!rl[4]) begin pg <= 1'b0; pp <= 0; pdone <= 2'b00; for (i_ = 0; i_ < 8; i_ = i_ + 1) pc[i_] <= 0; end
        else if (start_c) begin pg <= 1'b0; pp <= 0; pdone <= 2'b00; for (i_ = 0; i_ < 8; i_ = i_ + 1) pc[i_] <= 0; end
        else begin
            for (s_ = 0; s_ < 4; s_ = s_ + 1) if (piv_c[s_]) pc[{pig_c[s_], s_[1:0]}] <= pc[{pig_c[s_], s_[1:0]}] + 6'd1;
            if (p_ready) begin
                if (pp == NBEAT - 1) begin pp <= 0; pdone[pg] <= 1'b1; pg <= 1'b1; end
                else pp <= pp + 6'd1;
            end
        end
    end
    // read: address copies (stage 0), the 32-entry read (stage 1), an operand register at the adders (stage 2)
    reg pr0, pr1, pr2;
    always @(posedge clk or negedge rl[4])
        if (!rl[4]) begin pr0 <= 1'b0; pr1 <= 1'b0; pr2 <= 1'b0; end
        else begin pr0 <= p_ready; pr1 <= pr0; pr2 <= pr1; end
    reg [2047:0] sx, sr;                           // {stack s} x 512 bits (packed: Yosys re-elaborates unpacked ports)
    genvar gs, gl;
    generate for (gs = 0; gs < 4; gs = gs + 1) begin : g_s
        for (gl = 0; gl < 16; gl = gl + 1) begin : g_rd
            wire [5:0] a;                          // {g, beat}
            (* keep_hierarchy *) ot_nhb_dup_a6 u_a (.clk(clk), .d({pg, pp[4:0]}), .q(a));
            always @(posedge clk) begin
                sx[512*gs + 32*gl +: 32] <= pb[{a[5], gs[1:0], a[4:0]}][32*gl +: 32];
                sr[512*gs + 32*gl +: 32] <= sx[512*gs + 32*gl +: 32];
            end
        end
    end endgenerate
    wire [5:0]   phh6 = pp / BPH;
    wire [31:0]  rzv = rz[{pg, phh6[1:0]}];
    wire [31:0]  rz_d;
    wire [6:0]   tag_o;
    ot_hdc_delay #(.W(32), .D(2 * ADD_LAT + 3)) u_rz (.clk(clk), .rst_n(rl[5]), .d(rzv), .q(rz_d));
    ot_hdc_delay #(.W(7), .D(2 * ADD_LAT + MUL_LAT + 3), .RESET(1)) u_tag (.clk(clk), .rst_n(rl[5]),
                                                                     .d({p_ready, pg, pp[4:0]}), .q(tag_o));
    wire [511:0] y_o;
    generate for (gl = 0; gl < 16; gl = gl + 1) begin : g_l
        wire [31:0] a01, a23, a;
        wire [1:0] e1, e2, e3, e4;
        wire v1, v2, v3, v4;
        ot_hdc_fp32_add_lat #(.LAT(ADD_LAT)) u_01 (.clk(clk), .rst_n(rl[L_PV + 4*gl]), .valid_in(pr2),
            .a(sr[0 + 32*gl +: 32]), .b(sr[512 + 32*gl +: 32]), .y(a01), .err(e1), .valid_out(v1));
        ot_hdc_fp32_add_lat #(.LAT(ADD_LAT)) u_23 (.clk(clk), .rst_n(rl[L_PV + 4*gl + 1]), .valid_in(pr2),
            .a(sr[1024 + 32*gl +: 32]), .b(sr[1536 + 32*gl +: 32]), .y(a23), .err(e2), .valid_out(v2));
        ot_hdc_fp32_add_lat #(.LAT(ADD_LAT)) u_9 (.clk(clk), .rst_n(rl[L_PV + 4*gl + 2]), .valid_in(v1), .a(a01),
            .b(a23), .y(a), .err(e3), .valid_out(v3));
        ot_hdc_fp32_mul_lat #(.LAT(MUL_LAT)) u_m (.clk(clk), .rst_n(rl[L_PV + 4*gl + 3]), .valid_in(v3), .a(a),
            .b(rz_d), .y(y_o[32*gl +: 32]), .err(e4), .valid_out(v4));
        assign pf[gl] = (v1 && e1 != 0) || (v2 && e2 != 0) || (v3 && e3 != 0) || (v4 && e4 != 0);
    end endgenerate

    // ---- registered outputs -----------------------------------------------------------------------------------------
    always @(posedge clk or negedge rl[7]) begin
        if (!rl[7]) begin mo_valid <= 1'b0; out_valid <= 1'b0; fault <= 1'b0; ev <= 8'd0; end
        else begin
            mo_valid <= mo_valid_i; out_valid <= tag_o[6]; fault <= fault_i;
            ev <= {tag_o[6], p_ready, rz_ok, msent, mo_valid_i, 1'b0};
        end
    end
    always @(posedge clk) begin
        mo_g <= mo_g_i; mo_hh <= mo_hh_i; mo_data <= mo_data_i;
        out_g <= tag_o[5]; out_beat <= {1'b0, tag_o[4:0]}; out_data <= y_o;
    end
endmodule
