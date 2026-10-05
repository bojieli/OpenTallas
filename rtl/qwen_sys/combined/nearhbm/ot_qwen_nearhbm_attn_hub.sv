`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// Near-HBM attention for the Qwen3-8B ROM die (TP4): THE HUB.  NEW, DEFAULT-OFF (see ot_qwen_nearhbm_attn_stack.sv).
//   max  : M[g][h] = max over the 4 stacks' local maxima (order-free), broadcast back to every stack.
//   Z    : the 64 block sums b = 4 k + s per head (+0 for an empty block), pairwise = Z levels 5-10, then the
//          golden reciprocal (bit seed + 3 Newton steps, ot_qwen_nearhbm_recip_p: ot_hdc_recip_q on SS-1.2 GHz units).
//   P.V  : (S0 + S1) + (S2 + S3) = P.V levels 8-9, then x reciprocal(Z): the golden's normalise-after-sum.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qwen_nearhbm_attn_hub #(
    parameter integer HD = 128,
    parameter integer ADD_LAT = 7,
    parameter integer MUL_LAT = 6,
    parameter integer ZW = 4
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          start,
    // sideband from the 4 stacks
    input  wire [3:0]    si_valid,
    input  wire [7:0]    si_type,
    input  wire [3:0]    si_g,
    input  wire [7:0]    si_hh,
    input  wire [15:0]   si_k,
    input  wire [3:0]    si_any,
    input  wire [127:0]  si_data,
    // P.V partial beats from the 4 stacks
    input  wire [3:0]    pi_valid,
    input  wire [3:0]    pi_g,
    input  wire [23:0]   pi_beat,
    input  wire [2047:0] pi_data,
    // M to the stacks (one message a cycle, broadcast)
    output reg           mo_valid,
    output reg           mo_g,
    output reg  [1:0]    mo_hh,
    output reg  [31:0]   mo_data,
    // attention output beats: 16 FP32, head 4g + beat div (HD/16), d = 16 (beat mod (HD/16)) + lane
    output wire          out_valid,
    output wire          out_g,
    output wire [5:0]    out_beat,
    output wire [511:0]  out_data,
    output reg           fault,
    output wire [7:0]    ev
);
    localparam integer NBEAT = 4 * HD / 16;
    localparam integer BPH = HD / 16;
    wire [15:0] pf;
    wire [15:0] pv8;
    integer s_, i_;
    function automatic fgt(input [31:0] a, input [31:0] b);
        fgt = (a[31] != b[31]) ? !a[31] : (!a[31] ? (a[30:0] > b[30:0]) : (a[30:0] < b[30:0]));
    endfunction

    // ---- max --------------------------------------------------------------------------------------------------------
    reg [31:0] lm [0:31];                        // {g, s, h}
    reg [7:0]  lany;                             // {g, s}
    reg [4:0]  lcnt0, lcnt1;
    reg [1:0]  msent;
    wire       mg = msent[0];                    // the g being sent
    reg [2:0]  mh;
    // pipelined: A reads the 4 stacks' local maxima of (g, h), B and C compare pairwise (order-free: max is exact)
    wire       mready = !msent[mg] && (mg ? (lcnt1 == 5'd16) : (lcnt0 == 5'd16));
    reg        ma_v, mb_v;
    reg        ma_g, mb_g;
    reg [1:0]  ma_h, mb_h;
    reg [127:0] ma_x;
    reg [3:0]  ma_a;
    reg [63:0] mb_x;
    reg [1:0]  mb_a;
    function automatic [32:0] fmax2(input [31:0] x, input ax, input [31:0] y, input ay);   // {any, max}
        fmax2 = !ax ? {ay, y} : (!ay ? {1'b1, x} : {1'b1, (fgt(y, x) ? y : x)});
    endfunction
    wire [32:0] m01 = fmax2(ma_x[31:0], ma_a[0], ma_x[63:32], ma_a[1]);
    wire [32:0] m23 = fmax2(ma_x[95:64], ma_a[2], ma_x[127:96], ma_a[3]);
    wire [32:0] mfin = fmax2(mb_x[31:0], mb_a[0], mb_x[63:32], mb_a[1]);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin ma_v <= 1'b0; mb_v <= 1'b0; end
        else begin
            ma_v <= mready && !start; mb_v <= ma_v && !start;
        end
    end
    always @(posedge clk) begin
        ma_g <= mg; ma_h <= mh[1:0];
        for (s_ = 0; s_ < 4; s_ = s_ + 1) begin
            ma_x[32*s_ +: 32] <= lm[{mg, s_[1:0], mh[1:0]}];
            ma_a[s_] <= lany[4*mg + s_];
        end
        mb_g <= ma_g; mb_h <= ma_h;
        mb_x <= {m23[31:0], m01[31:0]}; mb_a <= {m23[32], m01[32]};
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin lcnt0 <= 0; lcnt1 <= 0; lany <= 0; msent <= 0; mh <= 0; mo_valid <= 1'b0; end
        else begin
            mo_valid <= 1'b0;
            if (start) begin lcnt0 <= 0; lcnt1 <= 0; lany <= 0; msent <= 0; mh <= 0; end
            else begin
                for (s_ = 0; s_ < 4; s_ = s_ + 1)
                    if (si_valid[s_] && si_type[2*s_ +: 2] == 2'd0) begin
                        lm[{si_g[s_], s_[1:0], si_hh[2*s_ +: 2]}] <= si_data[32*s_ +: 32];
                        if (si_any[s_]) lany[4*si_g[s_] + s_] <= 1'b1;
                    end
                lcnt0 <= lcnt0 + ((si_valid[0] && si_type[1:0] == 0 && !si_g[0]) ? 1 : 0)
                               + ((si_valid[1] && si_type[3:2] == 0 && !si_g[1]) ? 1 : 0)
                               + ((si_valid[2] && si_type[5:4] == 0 && !si_g[2]) ? 1 : 0)
                               + ((si_valid[3] && si_type[7:6] == 0 && !si_g[3]) ? 1 : 0);
                lcnt1 <= lcnt1 + ((si_valid[0] && si_type[1:0] == 0 && si_g[0]) ? 1 : 0)
                               + ((si_valid[1] && si_type[3:2] == 0 && si_g[1]) ? 1 : 0)
                               + ((si_valid[2] && si_type[5:4] == 0 && si_g[2]) ? 1 : 0)
                               + ((si_valid[3] && si_type[7:6] == 0 && si_g[3]) ? 1 : 0);
                if (mready) begin
                    if (mh == 3'd3) begin mh <= 0; msent[mg] <= 1'b1; end else mh <= mh + 3'd1;
                end
                if (mb_v) begin mo_valid <= 1'b1; mo_g <= mb_g; mo_hh <= mb_h; mo_data <= mfin[31:0]; end
            end
        end
    end

    // ---- Z: block sums, tree, reciprocal ------------------------------------------------------------------------------
    reg [31:0] zm [0:511];                        // {g, h, node}
    reg [511:0] zv;                               // written since start (else +0: an empty block)
    reg [2:0]  zdc0, zdc1;
    reg        zrun, zg, zwait_recip;
    reg [1:0]  zdone_tree;
    reg [2:0]  zl;                                // level 1..6
    reg [5:0]  zp;
    reg [3:0]  zwt;
    wire [6:0] znp = 7'd64 >> zl;                 // pairs at this level
    reg [ZW-1:0] ziv;
    reg [ZW*4*32-1:0] za, zb;
    reg [5:0] zi [0:ZW-1];
    integer z, h_;
    reg [6:0] pz;
    always @* begin
        for (z = 0; z < ZW; z = z + 1) begin
            pz = {1'b0, zp} + z;
            ziv[z] = zrun && (zwt == 0) && (pz < znp);
            zi[z] = pz[5:0];
            for (h_ = 0; h_ < 4; h_ = h_ + 1) begin
                za[32*(4*z + h_) +: 32] = zv[{zg, h_[1:0], pz[4:0], 1'b0}] ? zm[{zg, h_[1:0], pz[4:0], 1'b0}] : 32'd0;
                zb[32*(4*z + h_) +: 32] = zv[{zg, h_[1:0], pz[4:0], 1'b1}] ? zm[{zg, h_[1:0], pz[4:0], 1'b1}] : 32'd0;
            end
        end
    end
    // operand register (the 512-entry read and the zero mask get their own cycle)
    reg [ZW-1:0] ziv_r;
    reg [ZW*4*32-1:0] za_r, zb_r;
    reg [ZW*6-1:0] zi_r;
    always @(posedge clk or negedge rst_n) if (!rst_n) ziv_r <= 0; else ziv_r <= ziv;
    always @(posedge clk) begin
        za_r <= za; zb_r <= zb;
        for (z = 0; z < ZW; z = z + 1) zi_r[6*z +: 6] <= zi[z];
    end
    wire [ZW*4*32-1:0] zy;
    wire [ZW*4-1:0] zvo, zerr;
    wire [ZW*7-1:0] zwi;
    genvar gz, gh;
    generate for (gz = 0; gz < ZW; gz = gz + 1) begin : g_z
        ot_hdc_delay #(.W(7), .D(ADD_LAT), .RESET(1)) u_i (.clk(clk), .rst_n(rst_n), .d({ziv_r[gz], zi_r[6*gz +: 6]}),
                                                           .q(zwi[7*gz +: 7]));
        for (gh = 0; gh < 4; gh = gh + 1) begin : g_h
            wire [1:0] err;
            ot_hdc_fp32_add_lat #(.LAT(ADD_LAT)) u_add (
                .clk(clk), .rst_n(rst_n), .valid_in(ziv_r[gz]), .a(za_r[32*(4*gz+gh) +: 32]), .b(zb_r[32*(4*gz+gh) +: 32]),
                .y(zy[32*(4*gz+gh) +: 32]), .err(err), .valid_out(zvo[4*gz+gh]));
            assign zerr[4*gz+gh] = zvo[4*gz+gh] && (err != 2'd0);
        end
    end endgenerate
    // reciprocal of the 4 Z of a g
    reg        rv;
    reg [31:0] rx;
    reg [2:0]  rh;
    wire [31:0] ry;
    wire        rvo, rfault;
    ot_qwen_nearhbm_recip_p #(.LA(7), .LM(6)) u_recip (.clk(clk), .rst_n(rst_n), .v(rv), .x(rx), .y(ry), .vo(rvo),
                                                     .fault(rfault));
    reg [2:0]  rcnt;
    reg [31:0] rz [0:7];                           // {g, h}
    reg [1:0]  rz_ok;
    reg        rg_out;                             // g of the reciprocals in flight
    always @(posedge clk) begin
        for (z = 0; z < ZW; z = z + 1)
            if (zwi[7*z + 6])
                for (h_ = 0; h_ < 4; h_ = h_ + 1) zm[{zg, h_[1:0], zwi[7*z +: 6]}] <= zy[32*(4*z + h_) +: 32];
        for (s_ = 0; s_ < 4; s_ = s_ + 1)
            if (si_valid[s_] && si_type[2*s_ +: 2] == 2'd1)
                zm[{si_g[s_], si_hh[2*s_ +: 2], si_k[4*s_ +: 4], s_[1:0]}] <= si_data[32*s_ +: 32];
        if (rvo) rz[{rg_out, rcnt[1:0]}] <= ry;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            zdc0 <= 0; zdc1 <= 0; zrun <= 1'b0; zg <= 1'b0; zdone_tree <= 2'b00; zl <= 3'd1; zp <= 0; zwt <= 0;
            rv <= 1'b0; rh <= 0; rcnt <= 0; rz_ok <= 2'b00; zwait_recip <= 1'b0; fault <= 1'b0; zv <= 0;
        end else begin
            rv <= 1'b0;
            if (start) zv <= 0;
            else begin
                for (z = 0; z < ZW; z = z + 1)
                    if (zwi[7*z + 6])
                        for (h_ = 0; h_ < 4; h_ = h_ + 1) zv[{zg, h_[1:0], zwi[7*z +: 6]}] <= 1'b1;
                for (s_ = 0; s_ < 4; s_ = s_ + 1)
                    if (si_valid[s_] && si_type[2*s_ +: 2] == 2'd1) zv[{si_g[s_], si_hh[2*s_ +: 2], si_k[4*s_ +: 4], s_[1:0]}] <= 1'b1;
            end
            if (|zerr || (rvo && rfault) || (|pf)) fault <= 1'b1;
            if (start) begin
                zdc0 <= 0; zdc1 <= 0; zrun <= 1'b0; zg <= 1'b0; zdone_tree <= 2'b00; rz_ok <= 2'b00; rcnt <= 0;
                zwait_recip <= 1'b0; fault <= 1'b0;
            end else begin
                zdc0 <= zdc0 + ((si_valid[0] && si_type[1:0] == 2 && !si_g[0]) ? 1 : 0)
                             + ((si_valid[1] && si_type[3:2] == 2 && !si_g[1]) ? 1 : 0)
                             + ((si_valid[2] && si_type[5:4] == 2 && !si_g[2]) ? 1 : 0)
                             + ((si_valid[3] && si_type[7:6] == 2 && !si_g[3]) ? 1 : 0);
                zdc1 <= zdc1 + ((si_valid[0] && si_type[1:0] == 2 && si_g[0]) ? 1 : 0)
                             + ((si_valid[1] && si_type[3:2] == 2 && si_g[1]) ? 1 : 0)
                             + ((si_valid[2] && si_type[5:4] == 2 && si_g[2]) ? 1 : 0)
                             + ((si_valid[3] && si_type[7:6] == 2 && si_g[3]) ? 1 : 0);
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
                        rv <= 1'b1; rx <= zv[{zg, rh[1:0], 6'd0}] ? zm[{zg, rh[1:0], 6'd0}] : 32'd0;
                        rh <= rh + 3'd1; rg_out <= zg;
                    end else if (rcnt == 3'd4) begin
                        rcnt <= 0; zwait_recip <= 1'b0; zdone_tree[zg] <= 1'b1; rz_ok[zg] <= 1'b1;
                    end
                end
                if (rvo) rcnt <= rcnt + 3'd1;
            end
        end
    end

    // ---- P.V: levels 8-9 and x 1/Z ----------------------------------------------------------------------------------
    reg [511:0] pb [0:255];                        // {g, s, beat}
    reg [5:0]   pc [0:7];                          // beats received {g, s}
    reg         pg;                                // g being combined
    reg [5:0]   pp;
    reg [1:0]   pdone;
    always @(posedge clk) begin
        for (s_ = 0; s_ < 4; s_ = s_ + 1)
            if (pi_valid[s_]) pb[{pi_g[s_], s_[1:0], pi_beat[6*s_ +: 5]}] <= pi_data[512*s_ +: 512];
    end
    wire p_ready = rz_ok[pg] && !pdone[pg] && (pc[{pg, 2'd0}] > pp) && (pc[{pg, 2'd1}] > pp) &&
                   (pc[{pg, 2'd2}] > pp) && (pc[{pg, 2'd3}] > pp);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin pg <= 1'b0; pp <= 0; pdone <= 2'b00; for (i_ = 0; i_ < 8; i_ = i_ + 1) pc[i_] <= 0; end
        else if (start) begin pg <= 1'b0; pp <= 0; pdone <= 2'b00; for (i_ = 0; i_ < 8; i_ = i_ + 1) pc[i_] <= 0; end
        else begin
            for (s_ = 0; s_ < 4; s_ = s_ + 1) if (pi_valid[s_]) pc[{pi_g[s_], s_[1:0]}] <= pc[{pi_g[s_], s_[1:0]}] + 6'd1;
            if (p_ready) begin
                if (pp == NBEAT - 1) begin pp <= 0; pdone[pg] <= 1'b1; pg <= 1'b1; end
                else pp <= pp + 6'd1;
            end
        end
    end
    reg [511:0] s0, s1, s2, s3;                    // operand register: the 128-entry beat reads get their own cycle
    reg         pr_v;
    always @(posedge clk) begin
        s0 <= pb[{pg, 2'd0, pp[4:0]}]; s1 <= pb[{pg, 2'd1, pp[4:0]}];
        s2 <= pb[{pg, 2'd2, pp[4:0]}]; s3 <= pb[{pg, 2'd3, pp[4:0]}];
    end
    always @(posedge clk or negedge rst_n) if (!rst_n) pr_v <= 1'b0; else pr_v <= p_ready;
    wire [5:0]   phh6 = pp / BPH;
    wire [31:0]  rzv = rz[{pg, phh6[1:0]}];
    wire [31:0]  rz_d;
    wire [6:0]   tag_o;
    ot_hdc_delay #(.W(32), .D(2 * ADD_LAT + 1)) u_rz (.clk(clk), .rst_n(rst_n), .d(rzv), .q(rz_d));
    ot_hdc_delay #(.W(7), .D(2 * ADD_LAT + MUL_LAT + 1), .RESET(1)) u_tag (.clk(clk), .rst_n(rst_n),
                                                                     .d({p_ready, pg, pp[4:0]}), .q(tag_o));
    genvar gl;
    generate for (gl = 0; gl < 16; gl = gl + 1) begin : g_l
        wire [31:0] a01, a23, a, y;
        wire [1:0] e1, e2, e3, e4;
        wire v1, v2, v3, v4;
        ot_hdc_fp32_add_lat #(.LAT(ADD_LAT)) u_01 (.clk(clk), .rst_n(rst_n), .valid_in(pr_v), .a(s0[32*gl +: 32]),
            .b(s1[32*gl +: 32]), .y(a01), .err(e1), .valid_out(v1));
        ot_hdc_fp32_add_lat #(.LAT(ADD_LAT)) u_23 (.clk(clk), .rst_n(rst_n), .valid_in(pr_v), .a(s2[32*gl +: 32]),
            .b(s3[32*gl +: 32]), .y(a23), .err(e2), .valid_out(v2));
        ot_hdc_fp32_add_lat #(.LAT(ADD_LAT)) u_9 (.clk(clk), .rst_n(rst_n), .valid_in(v1), .a(a01), .b(a23),
            .y(a), .err(e3), .valid_out(v3));
        ot_hdc_fp32_mul_lat #(.LAT(MUL_LAT)) u_m (.clk(clk), .rst_n(rst_n), .valid_in(v3), .a(a), .b(rz_d),
            .y(out_data[32*gl +: 32]), .err(e4), .valid_out(v4));
        assign pf[gl] = (v1 && e1 != 0) || (v2 && e2 != 0) || (v3 && e3 != 0) || (v4 && e4 != 0);
        assign pv8[gl] = v4;
    end endgenerate
    assign out_valid = tag_o[6];
    assign out_g = tag_o[5];
    assign out_beat = {1'b0, tag_o[4:0]};
    assign ev = {out_valid, p_ready, rz_ok, msent, mo_valid, 1'b0};
endmodule
