`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// el1011-q-kvd 2026-10-11: near-HBM attention hub as HARDENED SUB-TILES (textbook audit, owner 10-11).  Same ports and the
// same arithmetic in the same order as ot_qwen_nearhbm_attn_hub_p (ANR = 1, PSRAM = 1); differs only in where registers
// sit.  hub_p routed as one flat block: one clock root over 226k sinks (PSRAM: ~95k), CTS hold repair stuck (-53 / -38 ps,
// 28k endpoints), 9-writer / 33-reader Z store in one 512-entry vector.  Here:
//   ot_nhb_pbst  x4  per stack: the stack's pi_* pin flops (= hub _b), the _c stage, its 2 x 128x256 SRAM beat store, the
//                    capture register sr (512 b).  Read address {pg, pp} lands on the tile's pin flop (= hub_p's dup a).
//   ot_nhb_pvlg  x4  P.V lane group (4 lanes x {add 01, add 23, add 9, x 1/Z}); pin flops in, y / fault registered out.
//   ot_nhb_zh    x4  one head of the Z tree: zm[g][node] (128 x 32 b) + zv, the head's ZW = 4 tree adders, 16
//                    replicated read-address copies, one-hot writes decoded in the tile, root (zv-masked) registered out.
//   parent           boundary si_* registers, decode, max, Z control, reciprocal, rz, P.V control, the sr relay band,
//                    output registers.
// Cycle shifts (values bit-identical): P.V +3 (tile pin flop + relay + tile output register); a Z tile runs +2 behind the
// parent's issue (pin flop + its own address copies) with its internal read / write order unchanged; the reciprocal read
// is issued 3 cycles later so it stays behind the final tree write.  Bench: layer bench with KVD_HUBT (HPS=1).
// ---------------------------------------------------------------------------------------------------------------------

// ---- beat-store tile (one stack) ------------------------------------------------------------------------------------
module ot_nhb_pbst (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         pv,              // pi_valid[s]   (hub port)
    input  wire         pgi,             // pi_g[s]       (hub port)
    input  wire [5:0]   pbeat,           // pi_beat[6s +: 6] (hub port)
    input  wire [511:0] pdata,           // pi_data[512s +: 512] (hub port)
    input  wire [5:0]   ra,              // {pg, pp[4:0]} (parent registers)
    output reg  [511:0] sr
);
    wire [1:0] rr;
    ot_rst_relay #(.REGIONS(2), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rr));
    reg         pv_b, pv_c;
    reg         pg_b, pg_c;
    reg [4:0]   pb_b, pb_c;
    reg [511:0] pd_b, pd_c;
    reg [5:0]   a;
    always @(posedge clk or negedge rr[0]) if (!rr[0]) begin pv_b <= 1'b0; pv_c <= 1'b0; end else begin pv_b <= pv; pv_c <= pv_b; end
    always @(posedge clk) begin
        pg_b <= pgi; pb_b <= pbeat[4:0]; pd_b <= pdata;
        pg_c <= pg_b; pb_c <= pb_b; pd_c <= pd_b;
        a <= ra;
    end
`ifdef KVD_PBMUT
    wire [5:0] ar = a ^ 6'd1;                 // bench mutant: the neighbouring beat
`else
    wire [5:0] ar = a;
`endif
    wire [255:0] q0, q1;
    ot_sram_1r1w_128x256_m1_r2c2 u_pb0 (.clk(clk), .r_ce_in(1'b1), .r_addr_in({1'b0, ar}), .rd_out(q0),
        .w_ce_in(pv_c), .w_addr_in({1'b0, pg_c, pb_c}), .wd_in(pd_c[255:0]),
        .w_mask_in({256{1'b1}}), .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
    ot_sram_1r1w_128x256_m1_r2c2 u_pb1 (.clk(clk), .r_ce_in(1'b1), .r_addr_in({1'b0, ar}), .rd_out(q1),
        .w_ce_in(pv_c), .w_addr_in({1'b0, pg_c, pb_c}), .wd_in(pd_c[511:256]),
        .w_mask_in({256{1'b1}}), .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
    always @(posedge clk) sr <= {q1, q0};
endmodule

// ---- P.V lane-group tile (4 lanes) -----------------------------------------------------------------------------------
module ot_nhb_pvlg (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         v,               // pr (beat operands valid)
    input  wire [127:0] s0, s1, s2, s3,  // the 4 lanes' operands from stacks 0..3
    input  wire [31:0]  rz,              // 1/Z (aligned to the multiplier)
    output reg  [127:0] y,
    output reg  [3:0]   pf
);
    localparam integer ADD_LAT = 7, MUL_LAT = 6;
    wire [4:0] rr;
    ot_rst_relay #(.REGIONS(5), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rr));
    reg         v_q;
    reg [127:0] s0_q, s1_q, s2_q, s3_q;
    reg [31:0]  rz_q;
    always @(posedge clk or negedge rr[4]) if (!rr[4]) v_q <= 1'b0; else v_q <= v;
    always @(posedge clk) begin s0_q <= s0; s1_q <= s1; s2_q <= s2; s3_q <= s3; rz_q <= rz; end
    wire [127:0] y_o;
    wire [3:0]   pf_o;
    genvar gl;
    generate for (gl = 0; gl < 4; gl = gl + 1) begin : g_l
        wire [31:0] a01, a23, a;
        wire [1:0] e1, e2, e3, e4;
        wire v1, v2, v3, v4;
        ot_hdc_fp32_add_lat_sel #(.LAT(ADD_LAT), .NR(1)) u_01 (.clk(clk), .rst_n(rr[gl]), .valid_in(v_q),
            .a(s0_q[32*gl +: 32]), .b(s1_q[32*gl +: 32]), .y(a01), .err(e1), .valid_out(v1));
        ot_hdc_fp32_add_lat_sel #(.LAT(ADD_LAT), .NR(1)) u_23 (.clk(clk), .rst_n(rr[gl]), .valid_in(v_q),
            .a(s2_q[32*gl +: 32]), .b(s3_q[32*gl +: 32]), .y(a23), .err(e2), .valid_out(v2));
        ot_hdc_fp32_add_lat_sel #(.LAT(ADD_LAT), .NR(1)) u_9 (.clk(clk), .rst_n(rr[gl]), .valid_in(v1), .a(a01),
            .b(a23), .y(a), .err(e3), .valid_out(v3));
        ot_hdc_fp32_mul_lat #(.LAT(MUL_LAT)) u_m (.clk(clk), .rst_n(rr[gl]), .valid_in(v3), .a(a),
            .b(rz_q), .y(y_o[32*gl +: 32]), .err(e4), .valid_out(v4));
        assign pf_o[gl] = (v1 && e1 != 0) || (v2 && e2 != 0) || (v3 && e3 != 0) || (v4 && e4 != 0);
    end endgenerate
    always @(posedge clk) y <= y_o;
    always @(posedge clk or negedge rr[4]) if (!rr[4]) pf <= 4'd0; else pf <= pf_o;
endmodule

// ---- Z head tile (one head h: zm[g][node], g in {0,1}, node 0..63) ---------------------------------------------------
module ot_nhb_zh (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         start,           // start_c
    input  wire [127:0] zs_we,           // block-sum write enables of this head, index {g, k, sd}
    input  wire [127:0] sid,             // sid_c (data of stack sd = bits 32*sd)
    input  wire [3:0]   ziv,             // tree issue: lane valids (stage 0, combinational in the parent)
    input  wire         zg,
    input  wire [5:0]   zp,
    output reg  [63:0]  root,            // {g1 root, g0 root}, zv-masked
    output reg  [3:0]   zerr
);
    localparam integer ZW = 4, ADD_LAT = 7;
    integer e_, z_;
    wire [5:0] rr;
    ot_rst_relay #(.REGIONS(6), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rr));
    // pin flops (zs_we / sid / start / issue)
    reg         start_q;
    reg [127:0] zs_we_q, sid_q;
    reg [3:0]   ziv_p;
    reg         zg_p;
    reg [5:0]   zp_p;
    always @(posedge clk or negedge rr[4])
        if (!rr[4]) begin start_q <= 1'b0; zs_we_q <= 128'd0; ziv_p <= 4'd0; end
        else begin start_q <= start; zs_we_q <= zs_we; ziv_p <= ziv; end
    always @(posedge clk) begin sid_q <= sid; zg_p <= zg; zp_p <= zp; end
    // stage 0 (hub_p's issue registers, one edge later): lane valids and read addresses {g, pair}
    reg [ZW-1:0]   ziv0, ziv1;
    reg [ZW*6-1:0] zi0, zi1;
    reg            zg0, zg1;
    reg [6:0]      pz;
    always @(posedge clk or negedge rr[4]) if (!rr[4]) begin ziv0 <= 0; ziv1 <= 0; end else begin ziv0 <= ziv_p; ziv1 <= ziv0; end
    always @(posedge clk) begin
        for (z_ = 0; z_ < ZW; z_ = z_ + 1) begin pz = {1'b0, zp_p} + z_; zi0[6*z_ +: 6] <= pz[5:0]; end
        zi1 <= zi0; zg0 <= zg_p; zg1 <= zg0;
    end
    reg [32*128-1:0] zm;                          // {g, node} x 32 b
    reg [127:0]      zv;
    reg [ZW*32-1:0]  za_r, zb_r;
    wire [ZW*32-1:0] zy;
    wire [ZW-1:0]    zvo, zerr_o;
    wire [ZW*8-1:0]  zwi;
    genvar gz, gb, gf;
    generate for (gz = 0; gz < ZW; gz = gz + 1) begin : g_z
        for (gb = 0; gb < 2; gb = gb + 1) begin : g_b
            for (gf = 0; gf < 2; gf = gf + 1) begin : g_f
                wire [5:0] a;                     // {g, pair[4:0]}: one copy per (operand, 16-bit half)
                wire [5:0] pzz = {1'b0, zp_p[5:0]} + gz;
                (* keep_hierarchy *) ot_nhb_dup_a6 u_a (.clk(clk), .d({zg_p, pzz[4:0]}), .q(a));
                wire [6:0]  ix = {a[5], a[4:0], gb[0]};
                wire [15:0] rd = zv[ix] ? zm[32*ix + 16*gf +: 16] : 16'd0;
                if (gb == 0) begin : g_a
                    always @(posedge clk) za_r[32*gz + 16*gf +: 16] <= rd;
                end else begin : g_bb
                    always @(posedge clk) zb_r[32*gz + 16*gf +: 16] <= rd;
                end
            end
        end
        ot_hdc_delay #(.W(8), .D(ADD_LAT), .RESET(1)) u_i (.clk(clk), .rst_n(rr[gz]),
                                                           .d({ziv1[gz], zg1, zi1[6*gz +: 6]}), .q(zwi[8*gz +: 8]));
        wire [1:0] err;
        ot_hdc_fp32_add_lat_sel #(.LAT(ADD_LAT), .NR(1)) u_add (.clk(clk), .rst_n(rr[gz]), .valid_in(ziv1[gz]),
            .a(za_r[32*gz +: 32]), .b(zb_r[32*gz +: 32]), .y(zy[32*gz +: 32]), .err(err), .valid_out(zvo[gz]));
        assign zerr_o[gz] = zvo[gz] && (err != 2'd0);
    end endgenerate
    // write (one cycle after the adder): registered one-hot {g, node} per lane
    reg [127:0]     zw_oh [0:ZW-1];
    reg [ZW*32-1:0] zy_r;
    always @(posedge clk or negedge rr[5]) begin
        if (!rr[5]) for (z_ = 0; z_ < ZW; z_ = z_ + 1) zw_oh[z_] <= 128'd0;
        else for (z_ = 0; z_ < ZW; z_ = z_ + 1) begin
            zw_oh[z_] <= 128'd0;
            if (zwi[8*z_ + 7]) zw_oh[z_][zwi[8*z_ +: 7]] <= 1'b1;
        end
    end
    always @(posedge clk) zy_r <= zy;
    always @(posedge clk) begin
        for (e_ = 0; e_ < 128; e_ = e_ + 1) begin
            for (z_ = 0; z_ < ZW; z_ = z_ + 1) if (zw_oh[z_][e_]) zm[32*e_ +: 32] <= zy_r[32*z_ +: 32];
            if (zs_we_q[e_]) zm[32*e_ +: 32] <= sid_q[32*(e_ % 4) +: 32];
        end
        root <= {zv[64] ? zm[32*64 +: 32] : 32'd0, zv[0] ? zm[0 +: 32] : 32'd0};
    end
    always @(posedge clk or negedge rr[5]) begin
        if (!rr[5]) zv <= 0;
        else if (start_q) zv <= 0;
        else for (e_ = 0; e_ < 128; e_ = e_ + 1) begin
            for (z_ = 0; z_ < ZW; z_ = z_ + 1) if (zw_oh[z_][e_]) zv[e_] <= 1'b1;
            if (zs_we_q[e_]) zv[e_] <= 1'b1;
        end
    end
    always @(posedge clk or negedge rr[5]) if (!rr[5]) zerr <= 4'd0; else zerr <= zerr_o;
endmodule

// ---- parent ---------------------------------------------------------------------------------------------------------
module ot_qwen_nearhbm_attn_hub_t #(
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
    integer sd_, s_, s2_, s3_, i_, e4_;
    function automatic fgt(input [31:0] a, input [31:0] b);
        fgt = (a[31] != b[31]) ? !a[31] : (!a[31] ? (a[30:0] > b[30:0]) : (a[30:0] < b[30:0]));
    endfunction
    // reset: 0 input stage, 1 max, 2 Z control, 4 P control, 5 tag, 6 recip, 7 outputs (one relay, one copy each)
    wire [7:0] rl;
    ot_rst_relay #(.REGIONS(8), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rl));

    // ---- boundary input registers (_b) and decode stage (_c); pi_data goes straight to the beat-store tiles --------
    reg          start_b;
    reg [3:0]    siv_b, piv_b;
    reg [7:0]    sit_b;  reg [3:0] sig_b;  reg [7:0] sih_b;  reg [15:0] sik_b;  reg [3:0] sia_b;  reg [127:0] sid_b;
    reg [3:0]    pig_b;
    always @(posedge clk or negedge rl[0])
        if (!rl[0]) begin start_b <= 1'b0; siv_b <= 4'd0; piv_b <= 4'd0; end
        else begin start_b <= start; siv_b <= si_valid; piv_b <= pi_valid; end
    always @(posedge clk) begin
        sit_b <= si_type; sig_b <= si_g; sih_b <= si_hh; sik_b <= si_k; sia_b <= si_any; sid_b <= si_data; pig_b <= pi_g;
    end
    reg [31:0]  lm_we_n;
    reg [511:0] zs_we_n;
    always @* begin
        lm_we_n = 32'd0; zs_we_n = 512'd0;
        for (sd_ = 0; sd_ < 4; sd_ = sd_ + 1) begin
            if (siv_b[sd_] && sit_b[2*sd_ +: 2] == 2'd0) lm_we_n[{sig_b[sd_], sd_[1:0], sih_b[2*sd_ +: 2]}] = 1'b1;
            if (siv_b[sd_] && sit_b[2*sd_ +: 2] == 2'd1)
                zs_we_n[{sig_b[sd_], sih_b[2*sd_ +: 2], sik_b[4*sd_ +: 4], sd_[1:0]}] = 1'b1;
        end
    end
    reg          start_c;
    reg [3:0]    siv_c, piv_c;
    reg [7:0]    sit_c;  reg [3:0] sig_c;  reg [3:0] sia_c;  reg [127:0] sid_c;  reg [3:0] pig_c;
    reg [31:0]   lm_we;
    reg [511:0]  zs_we;
    always @(posedge clk or negedge rl[0])
        if (!rl[0]) begin start_c <= 1'b0; siv_c <= 4'd0; piv_c <= 4'd0; lm_we <= 32'd0; zs_we <= 512'd0; end
        else begin start_c <= start_b; siv_c <= siv_b; piv_c <= piv_b; lm_we <= lm_we_n; zs_we <= zs_we_n; end
    always @(posedge clk) begin sit_c <= sit_b; sig_c <= sig_b; sia_c <= sia_b; sid_c <= sid_b; pig_c <= pig_b; end

    // ---- max (unchanged) -------------------------------------------------------------------------------------------
    reg [31:0] lm [0:31];
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

    // ---- Z control (issue to the head tiles), reciprocal ------------------------------------------------------------
    reg [2:0]  zdc0, zdc1;
    reg        zrun, zg, zwait_recip;
    reg [1:0]  zdone_tree;
    reg [2:0]  zl;
    reg [5:0]  zp;
    reg [3:0]  zwt;
    reg        fault_i;
    wire [6:0] znp = 7'd64 >> zl;
    reg [ZW-1:0] ziv;
    reg [6:0]    pz;
    integer z;
    always @* begin
        for (z = 0; z < ZW; z = z + 1) begin
            pz = {1'b0, zp} + z;
            ziv[z] = zrun && (zwt == 0) && (pz < znp);
        end
    end
    wire [255:0] zroot;                            // head h: {g1, g0} root at [64h +: 64]
    wire [15:0]  zerr;
    genvar gh;
    generate for (gh = 0; gh < 4; gh = gh + 1) begin : g_zh
        wire [127:0] we_h;
        genvar ge;
        for (ge = 0; ge < 128; ge = ge + 1) begin : g_we      // {g, k, sd} of head gh = zs_we[{g, gh, k, sd}]
            assign we_h[ge] = zs_we[{ge[6], gh[1:0], ge[5:0]}];
        end
        ot_nhb_zh u_zh (.clk(clk), .rst_n(rst_n), .start(start_c), .zs_we(we_h), .sid(sid_c), .ziv(ziv), .zg(zg), .zp(zp),
                        .root(zroot[64*gh +: 64]), .zerr(zerr[4*gh +: 4]));
    end endgenerate
    // reciprocal: issue (rv0 / ra0) delayed 3 cycles to the root read (tile +2, root register +1)
    reg        rv0, rva, rvb, rvc, rv1;
    reg [2:0]  ra0, raa, rab, rac;
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
    always @(posedge clk or negedge rl[6])
        if (!rl[6]) begin rva <= 1'b0; rvb <= 1'b0; rvc <= 1'b0; rv1 <= 1'b0; end
        else begin rva <= rv0; rvb <= rva; rvc <= rvb; rv1 <= rvc; end
    always @(posedge clk) begin
        raa <= ra0; rab <= raa; rac <= rab;
        rx <= zroot[64*rac[1:0] + 32*rac[2] +: 32];
        if (rvo) rz[{rg_out, rcnt[1:0]}] <= ry;
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

    // ---- P.V control; beat-store tiles; relay band; lane-group tiles -------------------------------------------------
    reg [5:0]   pc [0:7];
    reg         pg;
    reg [5:0]   pp;
    reg [1:0]   pdone;
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
    reg pr0, pr1, pr2, pr3;
    always @(posedge clk or negedge rl[4])
        if (!rl[4]) begin pr0 <= 1'b0; pr1 <= 1'b0; pr2 <= 1'b0; pr3 <= 1'b0; end
        else begin pr0 <= p_ready; pr1 <= pr0; pr2 <= pr1; pr3 <= pr2; end
    wire [2047:0] sr;
    genvar gs, gl;
    generate for (gs = 0; gs < 4; gs = gs + 1) begin : g_s
        ot_nhb_pbst u_pbst (.clk(clk), .rst_n(rst_n), .pv(pi_valid[gs]), .pgi(pi_g[gs]), .pbeat(pi_beat[6*gs +: 6]),
                            .pdata(pi_data[512*gs +: 512]), .ra({pg, pp[4:0]}), .sr(sr[512*gs +: 512]));
    end endgenerate
    wire [5:0]   phh6 = pp / BPH;
    wire [31:0]  rzv = rz[{pg, phh6[1:0]}];
    wire [31:0]  rz_d;
    wire [6:0]   tag_o;
    ot_hdc_delay #(.W(32), .D(2 * ADD_LAT + 3)) u_rz (.clk(clk), .rst_n(rl[5]), .d(rzv), .q(rz_d));
    ot_hdc_delay #(.W(7), .D(2 * ADD_LAT + MUL_LAT + 3 + 3), .RESET(1)) u_tag (.clk(clk), .rst_n(rl[5]),
                                                                     .d({p_ready, pg, pp[4:0]}), .q(tag_o));
    // relay band: the stack -> lane-group crossbar in two stages
    reg [2047:0] sr_r;
    reg [31:0]   rz_r;
    always @(posedge clk) begin sr_r <= sr; rz_r <= rz_d; end
    wire [511:0] y_o;
    generate for (gl = 0; gl < 4; gl = gl + 1) begin : g_pv
        ot_nhb_pvlg u_pv (.clk(clk), .rst_n(rst_n), .v(pr3),
            .s0(sr_r[0    + 128*gl +: 128]), .s1(sr_r[512  + 128*gl +: 128]),
            .s2(sr_r[1024 + 128*gl +: 128]), .s3(sr_r[1536 + 128*gl +: 128]),
            .rz(rz_r), .y(y_o[128*gl +: 128]), .pf(pf[4*gl +: 4]));
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
