`timescale 1ns/1ps
// qwen-rtl-finish 2026-10-07: the spine re-assembled from the die masters (ot_qfd_spine_part: tree top + VM x root +
// 16 tree lanes + port elements) against ot_qwen_me_spine_h_w12, EVERY output EVERY cycle (scale, fault included), on the
// random stimulus of tb_qwen_me_spine_h_lockstep (copied).  MUT = 1 corrupts the tree top's x descriptor: must mismatch.
module tb_qfd_tree_top_lockstep #(
    parameter integer W = 16, IL = 8, AW = 24, NW = 18,
    parameter integer GT = 96, TG = 4, SMIN = 3, SMAX = 5, TCUT = 3,
    parameter integer BD = 4, XVM = 1, NWS = 1, TWS = 2, ORD = 1, MEM_EXTRA = 0, SCALE_LOCAL = 0,
    parameter integer ACC_LAT = 7, TREE_LAT = 7, MUL_LAT = 6, FAST_ISSUE = 1, KV_PREP = 3,
    parameter integer MAXT = 3, MAXK = 4, SEED = 1, MUT = 0
) (
    input  wire        clk,
    input  wire        rst_n,
    output reg  [63:0] mism,
    output reg  [63:0] ops,
    output reg  [63:0] results,
    output reg  [63:0] amax_upd,
    output reg  [63:0] first_bad
);
    localparam integer NPG = GT >> SMIN, NXC = 1 << SMAX, NPT = GT >> TCUT, IBW = 3*NW + 13*AW + 13;
    reg  [63:0] cyc;
    // ---- stimulus ------------------------------------------------------------------------------------------
    reg go;
    reg [NW-1:0] i_nout, i_tiles, i_k;
    reg i_wsrc, i_round, i_mmode, i_oen, i_amax, i_rmax;
    reg [AW-1:0] i_wbase, i_ts, i_ks, i_js, i_xbase, i_xks, i_xjs, i_xcs, i_wcs, i_obase, i_ots, i_ojs, i_mbase;
    reg [2:0] i_jsh;
    reg [3:0] i_split;
    reg [NPT*W*32-1:0] t_lvl;
    reg [NXC*32-1:0] x_q;
    function automatic [31:0] rfloat(input [31:0] r);
        // a finite binary32 with a moderate exponent (so sums rarely overflow), random sign / mantissa
        rfloat = {r[31], 8'd100 + {3'd0, r[27:23]}, r[22:0]};
    endfunction
    function automatic [15:0] rscale(input [31:0] a, input integer lane);
        reg [31:0] h;
        begin
            h = a * 32'h9E3779B1 + lane * 32'h85EBCA6B;
            h = h ^ (h >> 15);
            rscale = {h[15], 8'd120 + {5'd0, h[2:0]}, h[13:7]};
        end
    endfunction
    integer n;
    always @(posedge clk) begin
        if (!rst_n) begin
            go <= 1'b0; cyc <= 0;
        end else begin
            cyc <= cyc + 1;
            go <= ($urandom % 4) == 0;
            i_tiles <= 1 + ($urandom % MAXT); i_k <= 1 + ($urandom % MAXK);
            i_nout <= $urandom % (GT * W * IL); i_wsrc <= ($urandom % 3) == 0; i_round <= $urandom % 2;
            i_mmode <= ($urandom % 4) == 0; i_oen <= ($urandom % 8) != 0;
            i_amax <= ($urandom % 3) == 0; i_rmax <= ($urandom % 4) == 0;
            i_wbase <= $urandom; i_ts <= $urandom; i_ks <= $urandom; i_js <= $urandom; i_xbase <= $urandom;
            i_xks <= $urandom; i_xjs <= $urandom; i_xcs <= $urandom; i_wcs <= $urandom; i_obase <= $urandom;
            i_ots <= $urandom; i_ojs <= $urandom; i_mbase <= $urandom; i_jsh <= $urandom % 4;
            i_split <= SMIN + ($urandom % (SMAX - SMIN + 1));
        end
        for (n = 0; n < NPT * W; n = n + 1) t_lvl[n*32 +: 32] <= rfloat($urandom);
        for (n = 0; n < NXC; n = n + 1) x_q[n*32 +: 32] <= $urandom;
    end
    // ---- the two spines -----------------------------------------------------------------------------------------
`define SPINE_PORTS(P) \
        .clk(clk), .rst_n(rst_n), .go(go), .ready(P``ready), .idle(P``idle), \
        .i_nout(i_nout), .i_tiles(i_tiles), .i_k(i_k), .i_wsrc(i_wsrc), \
        .i_wbase(i_wbase), .i_ts(i_ts), .i_ks(i_ks), .i_js(i_js), \
        .i_xbase(i_xbase), .i_xks(i_xks), .i_xjs(i_xjs), .i_xcs(i_xcs), \
        .i_jsh(i_jsh), .i_split(i_split), .i_wcs(i_wcs), .i_round(i_round), \
        .i_obase(i_obase), .i_ots(i_ots), .i_ojs(i_ojs), \
        .i_mmode(i_mmode), .i_oen(i_oen), .i_amax(i_amax), .i_rmax(i_rmax), .i_mbase(i_mbase), \
        .scale_re(P``scale_re), .scale_gre(P``scale_gre), .scale_addr(P``scale_addr), .scale_q(P``scale_q), \
        .x_re(P``x_re), .x_addr(P``x_addr), .x_q(x_q), \
        .wrom_re(P``wrom_re), .wrom_addr(P``wrom_addr), .kv_re(P``kv_re), \
        .tgo(P``tgo), .tb(P``tb), .xl_d(P``xl_d), .t_lvl(t_lvl), .fab_fault(1'b0), \
        .ov(P``ov), .o_we(P``o_we), .o_addr(P``o_addr), .o_mask(P``o_mask), .o_data(P``o_data), \
        .am_idx(P``am_idx), .am_val(P``am_val), .am_any(P``am_any), \
        .mx_we(P``mx_we), .mx_addr(P``mx_addr), .mx_mask(P``mx_mask), .mx_data(P``mx_data), \
        .progress(P``progress), .fault(P``fault)
`define SPINE_WIRES(P) \
    wire P``ready, P``idle, P``scale_re, P``wrom_re, P``kv_re, P``tgo, P``ov, P``am_any, P``mx_we, P``fault; \
    wire [NPG-1:0] P``scale_gre, P``o_we; wire [NPG*AW-1:0] P``scale_addr, P``o_addr; \
    reg  [NPG*W*16-1:0] P``scale_q; wire [NXC-1:0] P``x_re; wire [NXC*AW-1:0] P``x_addr; \
    wire [AW-1:0] P``wrom_addr, P``mx_addr; wire [IBW-1:0] P``tb; wire [NXC*32-1:0] P``xl_d; \
    wire [NPG*W-1:0] P``o_mask; wire [NPG*W*32-1:0] P``o_data; wire [NW-1:0] P``am_idx; wire [31:0] P``am_val; \
    wire [W-1:0] P``mx_mask; wire [W*32-1:0] P``mx_data; wire [15:0] P``progress;
    `SPINE_WIRES(a_)
    `SPINE_WIRES(b_)
    ot_qwen_me_spine_h_w12 #(.W(W), .IL(IL), .AW(AW), .NW(NW), .GT(GT), .TG(TG), .SMIN(SMIN), .SMAX(SMAX), .TCUT(TCUT),
        .BD(BD), .XVM(XVM), .NWS(NWS), .TWS(TWS), .ORD(ORD), .MEM_EXTRA(MEM_EXTRA), .SCALE_LOCAL(SCALE_LOCAL),
        .ACC_LAT(ACC_LAT), .TREE_LAT(TREE_LAT), .MUL_LAT(MUL_LAT), .FAST_ISSUE(FAST_ISSUE), .KV_PREP(KV_PREP))
        u_a (`SPINE_PORTS(a_));
    ot_qfd_spine_part #(.MUT(MUT), .W(W), .IL(IL), .AW(AW), .NW(NW), .GT(GT), .TG(TG), .SMIN(SMIN), .SMAX(SMAX), .TCUT(TCUT),
        .BD(BD), .XVM(XVM), .NWS(NWS), .TWS(TWS), .ORD(ORD), .MEM_EXTRA(MEM_EXTRA), .SCALE_LOCAL(SCALE_LOCAL),
        .ACC_LAT(ACC_LAT), .TREE_LAT(TREE_LAT), .MUL_LAT(MUL_LAT), .FAST_ISSUE(FAST_ISSUE), .KV_PREP(KV_PREP))
        u_b (.land_cnt(16'd0), `SPINE_PORTS(b_));
    // synchronous scale ROMs (one per spine, same contents): a group's word is read when its enable is high
    integer g, l;
    always @(posedge clk) begin
        for (g = 0; g < NPG; g = g + 1) begin
            if (a_scale_gre[g]) for (l = 0; l < W; l = l + 1) a_scale_q[(g*W + l)*16 +: 16] <= rscale(a_scale_addr[g*AW +: AW], l);
            if (b_scale_gre[g]) for (l = 0; l < W; l = l + 1) b_scale_q[(g*W + l)*16 +: 16] <= rscale(b_scale_addr[g*AW +: AW], l);
        end
    end
    // ---- compare --------------------------------------------------------------------------------------------------
    reg  b_scale_re_d; reg [NPG-1:0] b_scale_gre_d; reg [NPG*AW-1:0] b_scale_addr_d;
    reg  a_fault_d;
    integer bad, c;
    always @(posedge clk) begin
        b_scale_re_d <= b_scale_re; b_scale_gre_d <= b_scale_gre; b_scale_addr_d <= b_scale_addr; a_fault_d <= a_fault;
        if (!rst_n) begin
            mism <= 0; ops <= 0; results <= 0; amax_upd <= 0; first_bad <= 0;
        end else if (cyc > 2) begin
            bad = 0;
            if (a_ready !== b_ready || a_idle !== b_idle || a_x_re !== b_x_re || a_wrom_re !== b_wrom_re ||
                a_wrom_addr !== b_wrom_addr || a_kv_re !== b_kv_re || a_tgo !== b_tgo || a_tb !== b_tb ||
                a_xl_d !== b_xl_d || a_ov !== b_ov || a_o_we !== b_o_we || a_am_idx !== b_am_idx ||
                a_am_val !== b_am_val || a_am_any !== b_am_any || a_mx_we !== b_mx_we || a_progress !== b_progress) bad = bad | 1;
            for (c = 0; c < NXC; c = c + 1)
                if (a_x_re[c] && a_x_addr[c*AW +: AW] !== b_x_addr[c*AW +: AW]) bad = bad | 2;
            if (a_ov && (a_o_addr !== b_o_addr || a_o_mask !== b_o_mask || a_o_data !== b_o_data)) bad = bad | 4;
            if (a_mx_we && (a_mx_addr !== b_mx_addr || a_mx_mask !== b_mx_mask || a_mx_data !== b_mx_data)) bad = bad | 8;
            if (a_scale_re !== b_scale_re || a_scale_gre !== b_scale_gre || a_scale_addr !== b_scale_addr) bad = bad | 16;
            if (b_fault !== a_fault) bad = bad | 32;
            if (bad != 0) begin
                mism <= mism + 1;
                if (first_bad == 0) first_bad <= {cyc[55:0], bad[7:0]};
            end
            if (go && a_ready) ops <= ops + 1;
            if (a_ov) results <= results + 1;
            if (a_am_any && (a_am_idx != 0)) amax_upd <= amax_upd + 1;
        end
    end
endmodule
