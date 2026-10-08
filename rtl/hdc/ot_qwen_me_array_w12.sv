`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Qwen3-8B O4 ROM die matrix engine as a replicated array (docs/MICROARCH_MODEL.md,
// Qwen section; W12).  GT lane groups are built from GT/TG identical tile
// elements (ot_qwen_w12_matvec_part PART 1: TG groups, their strap i_gbase = t*TG,
// the first log2(TG) split-tree levels), upper split-tree nodes
// (ot_qwen_me_node_w12, one pair-adder word per node) for levels log2(TG)+1..TCUT,
// and one spine top (ot_qwen_w12_matvec_part PART 2: the issue loop that drives the
// x chunk stream, tree levels TCUT+1.., the GT >> SMIN result-port groups with
// the INT8 post-scale, results, argmax and per-slot maxima).
//
// Wires are register stages:
//   BD   the instruction broadcast to every tile (go and the i_* fields), and
//        the x network from the vector memory's read port (BD - XVM stages
//        after the VM's own XVM extra registers, e.g. its conflict stage);
//   NWS  each upper tree level's input wire;
//   TWS  level TCUT's words to the spine top;
//   ORD  the result write from the port groups to the vector memory.
// Every tile's issue loop starts BD cycles after the top's and runs in
// lockstep with it; the top's tags wait XD = BD + (TCUT - log2 TG) * NWS + TWS
// extra cycles for the tree.  Values are those of the monolithic engine
// (ot_qwen_w12_matvec with the same GT and SMIN); only the latency grows.
//
// x network.  Group g reads chunk c = g mod S.  A tile's TG groups are TG
// consecutive chunks starting at TG*t mod S, so the vector memory drives
// NXL = 2^SMAX / TG quad lines, line r carrying chunks TG*(r mod S/TG) .. +TG-1
// (replicated at the source for S < 2^SMAX), and tile t listens to line
// t mod NXL.  Ops with split > SMAX or < SMIN fault.
// ---------------------------------------------------------------------------
module ot_qwen_me_array_w12 #(
    parameter integer W  = 16,
    parameter integer IL = 8,
    parameter integer AW = 24,
    parameter integer NW = 16,
    parameter integer INT8_SCALE_WCS_BASE = 1,
    parameter integer GT = 80,
    parameter integer TG = 4,
    parameter integer SMIN = 3,
    parameter integer SMAX = 5,
    parameter integer TCUT = 3,
    parameter integer BD = 0,
    parameter integer XVM = 0,
    parameter integer NWS = 0,
    parameter integer TWS = 0,
    parameter integer ORD = 0,
    parameter integer MEM_EXTRA = 0,      // tile memory capture stage (ot_qwen_rom_tile_logic_w12)
    parameter integer ROM_PIPE = 0,       // ot_qwen_rom_tile_logic_w12 ROM_PIPE / ROM_ARELAY / LRST (tiles' memories ROM_ARELAY + 2 later)
    parameter integer ROM_ARELAY = 1,
    parameter integer ROM_MUT = 0,
    parameter integer LRST = 0,
    parameter integer SCALE_LOCAL = 0,    // port-local scale ROM (ot_qwen_w12_matvec_part SCALE_LOCAL)
    parameter integer CODE_BANKS = 2,
    parameter integer KV_LOCAL = 0,       // 1: tiles hold KV slices (ot_qwen_rom_tile_w12); 0: global KV port
    parameter integer ACC_LAT = 5,        // lane accumulator FP32 add latency (ot_qwen_w12_matvec_part ACC_LAT)
    parameter integer FAST_ISSUE = 0,     // 1.2 GHz issue loop (ot_qwen_w12_matvec_part FAST_ISSUE)
    parameter integer KV_PREP = 0,        // KV-op offset pipeline cycles (ot_qwen_w12_matvec_part KV_PREP)
    parameter integer MUL_LAT = 5,        // lane BF16 product latency (ot_qwen_w12_matvec_part MUL_LAT)
    parameter integer TREE_LAT = 3        // split-tree pair adder latency (ot_qwen_w12_matvec_part TREE_LAT)
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    output wire              ready,
    output wire              idle,
    input  wire [NW-1:0]     i_nout, i_tiles, i_k,
    input  wire              i_wsrc,
    input  wire [AW-1:0]     i_wbase, i_ts, i_ks, i_js,
    input  wire [AW-1:0]     i_xbase, i_xks, i_xjs, i_xcs,
    input  wire [2:0]        i_jsh,
    input  wire [3:0]        i_split,
    input  wire [AW-1:0]     i_wcs,
    input  wire              i_round,
    input  wire [AW-1:0]     i_obase, i_ots, i_ojs,
    input  wire              i_mmode, i_oen, i_amax, i_rmax,
    input  wire [AW-1:0]     i_mbase,
    // result-port scale ROM (spine)
    output wire              scale_re,
    output wire [GT-1:0]     scale_gre,
    output wire [GT*AW-1:0]  scale_addr,
    input  wire [GT*W*16-1:0] scale_q,
    // vector-memory x read port: one element per chunk
    output wire [(1<<SMAX)-1:0]    x_re,
    output wire [(1<<SMAX)*AW-1:0] x_addr,
    input  wire [(1<<SMAX)*32-1:0] x_q,
    // tile memory macro pins (the hardened element's code ROM banks; KV_LOCAL = 0: a global KV port)
    output wire [GT/TG*CODE_BANKS-1:0]     t_rom_ce,
    output wire [GT/TG*12-1:0]             t_rom_addr,
    input  wire [GT/TG*2*CODE_BANKS*266-1:0] t_rom_rd,
    output wire [GT/TG-1:0]        t_kv_re,
    output wire [GT*AW-1:0]        t_kv_addr,
    input  wire [GT*W*32-1:0]      t_kv_q,
    // results (port groups only)
    output wire              ov,
    output wire [GT-1:0]     o_we,
    output wire [GT*AW-1:0]  o_addr,
    output wire [GT*W-1:0]   o_mask,
    output wire [GT*W*32-1:0] o_data,
    output wire [NW-1:0]     am_idx,
    output wire [31:0]       am_val,
    output wire              am_any,
    output wire              mx_we,
    output wire [AW-1:0]     mx_addr,
    output wire [W-1:0]      mx_mask,
    output wire [W*32-1:0]   mx_data,
    output wire [15:0]       progress,
    output wire              fault
);
    localparam integer NT  = GT / TG;
    localparam integer LT  = $clog2(TG);
    localparam integer NXC = 1 << SMAX;
    localparam integer NXL = NXC / TG;
    localparam integer RXA = (ROM_PIPE != 0) ? (ROM_ARELAY + 2) : 0;
    localparam integer XD  = BD + (TCUT - LT) * NWS + TWS + MEM_EXTRA + RXA;
    localparam integer NPT = GT >> TCUT;                  // tree words into the top
    localparam integer IBW = 3 * NW + 13 * AW + 13;       // the i_* fields
    localparam integer IREG = (BD > XVM && BD > 0) ? 1 : 0;   // the tile's own input stage is one of BD
    localparam integer NREG = (NWS > 0) ? 1 : 0;

    // -- spine: engine top, instruction broadcast, x network ------------------------
    wire              tgo;
    wire [IBW-1:0]    tb;
    wire [NXC*32-1:0] xl_d;
    wire [NPT*W*32-1:0] t_lvl;
    wire              fab_fault;
    localparam integer NPG = GT >> SMIN;
    wire [NPG-1:0]      sp_scale_gre, sp_o_we;
    wire [NPG*AW-1:0]   sp_scale_addr, sp_o_addr;
    wire [NPG*W-1:0]    sp_o_mask;
    wire [NPG*W*32-1:0] sp_o_data;
    ot_qwen_me_spine_w12 #(.W(W), .IL(IL), .AW(AW), .NW(NW), .INT8_SCALE_WCS_BASE(INT8_SCALE_WCS_BASE), .GT(GT), .TG(TG),
        .SMIN(SMIN), .SMAX(SMAX), .TCUT(TCUT), .BD(BD), .XVM(XVM), .NWS(NWS), .TWS(TWS), .ORD(ORD), .SCALE_LOCAL(SCALE_LOCAL), .MEM_EXTRA(MEM_EXTRA + RXA),
        .ACC_LAT(ACC_LAT), .TREE_LAT(TREE_LAT), .FAST_ISSUE(FAST_ISSUE), .KV_PREP(KV_PREP), .MUL_LAT(MUL_LAT)) u_spine (
        .clk(clk), .rst_n(rst_n), .go(go), .ready(ready), .idle(idle),
        .i_nout(i_nout), .i_tiles(i_tiles), .i_k(i_k), .i_wsrc(i_wsrc),
        .i_wbase(i_wbase), .i_ts(i_ts), .i_ks(i_ks), .i_js(i_js),
        .i_xbase(i_xbase), .i_xks(i_xks), .i_xjs(i_xjs), .i_xcs(i_xcs),
        .i_jsh(i_jsh), .i_split(i_split), .i_wcs(i_wcs), .i_round(i_round),
        .i_obase(i_obase), .i_ots(i_ots), .i_ojs(i_ojs),
        .i_mmode(i_mmode), .i_oen(i_oen), .i_amax(i_amax), .i_rmax(i_rmax), .i_mbase(i_mbase),
        .scale_re(scale_re), .scale_gre(sp_scale_gre), .scale_addr(sp_scale_addr), .scale_q(scale_q[NPG*W*16-1:0]),
        .x_re(x_re), .x_addr(x_addr), .x_q(x_q),
        .wrom_re(), .wrom_addr(), .kv_re(),
        .tgo(tgo), .tb(tb), .xl_d(xl_d), .t_lvl(t_lvl), .fab_fault(fab_fault),
        .ov(ov), .o_we(sp_o_we), .o_addr(sp_o_addr), .o_mask(sp_o_mask), .o_data(sp_o_data),
        .am_idx(am_idx), .am_val(am_val), .am_any(am_any),
        .mx_we(mx_we), .mx_addr(mx_addr), .mx_mask(mx_mask), .mx_data(mx_data),
        .progress(progress), .fault(fault));
    generate if (NPG < GT) begin : g_zx
        assign scale_gre = {{(GT - NPG){1'b0}}, sp_scale_gre};
        assign scale_addr = {{((GT - NPG) * AW){1'b0}}, sp_scale_addr};
        assign o_we = {{(GT - NPG){1'b0}}, sp_o_we};
        assign o_addr = {{((GT - NPG) * AW){1'b0}}, sp_o_addr};
        assign o_mask = {{((GT - NPG) * W){1'b0}}, sp_o_mask};
        assign o_data = {{((GT - NPG) * W * 32){1'b0}}, sp_o_data};
    end else begin : g_full
        assign scale_gre = sp_scale_gre; assign scale_addr = sp_scale_addr;
        assign o_we = sp_o_we; assign o_addr = sp_o_addr; assign o_mask = sp_o_mask; assign o_data = sp_o_data;
    end endgenerate

    // -- tiles and the tree above them -------------------------------------------------
    // Level LT position p is tile p's t_out.  The node of level lv > LT,
    // position p (k = lv - LT) lives in tile host = p*2^k + 2^(k-1) - 1: one
    // node per tile at most (hosts of different levels differ mod 2^k).
    function automatic integer host_level(input integer tt);
        integer kk;
        begin
            host_level = 0;
            for (kk = 1; kk <= TCUT - LT; kk = kk + 1)
                if ((tt % (1 << kk)) == (1 << (kk - 1)) - 1 && (tt >> kk) < (GT >> (LT + kk)) && host_level == 0)
                    host_level = LT + kk;
        end
    endfunction
    wire [NT*W*32-1:0] lw [LT:TCUT];
    wire [NT-1:0]      lvv [LT:TCUT];
    wire [NT-1:0]      tile_fault;
    genvar t, lv, p;
    generate
        for (lv = LT + 1; lv <= TCUT; lv = lv + 1) begin : g_lz
            for (p = (GT >> lv); p < NT; p = p + 1) begin : g_z
                assign lw[lv][p*W*32 +: W*32] = {W*32{1'b0}};
                assign lvv[lv][p] = 1'b0;
            end
        end
        for (t = 0; t < NT; t = t + 1) begin : g_tile
            localparam integer HL = host_level(t);
            localparam integer HK = HL - LT;
            localparam integer HP = (HL > 0) ? (t >> HK) : 0;
            wire [W*32-1:0] na, nb, ny;
            wire            nva, nvy;
            if (HL > 0) begin : g_host
                ot_hdc_delay #(.W(2*W*32), .D(NWS - NREG)) u_nw (.clk(clk), .rst_n(rst_n),
                    .d({lw[HL-1][(2*HP)*W*32 +: W*32], lw[HL-1][(2*HP+1)*W*32 +: W*32]}), .q({na, nb}));
                ot_hdc_delay #(.W(1), .D(NWS - NREG), .RESET(1)) u_nv (.clk(clk), .rst_n(rst_n),
                    .d(lvv[HL-1][2*HP]), .q(nva));
                assign lw[HL][HP*W*32 +: W*32] = ny;
                assign lvv[HL][HP] = nvy;
            end else begin : g_nohost
                assign na = {W*32{1'b0}}; assign nb = {W*32{1'b0}}; assign nva = 1'b0;
            end
            wire [TG*W*32-1:0] kvq = t_kv_q[t*TG*W*32 +: TG*W*32];
            ot_qwen_rom_tile_logic_w12 #(.W(W), .IL(IL), .AW(AW), .NW(NW), .GT(GT), .TG(TG), .SMIN(SMIN),
                .CODE_BANKS(CODE_BANKS), .IREG(IREG), .NREG(NREG), .KV_LOCAL(KV_LOCAL), .MEM_EXTRA(MEM_EXTRA), .ROM_PIPE(ROM_PIPE), .ROM_ARELAY(ROM_ARELAY), .ROM_MUT(ROM_MUT), .LRST(LRST),
                .ACC_LAT(ACC_LAT), .TREE_LAT(TREE_LAT), .FAST_ISSUE(FAST_ISSUE), .KV_PREP(KV_PREP), .MUL_LAT(MUL_LAT)) u_t (
                .clk(clk), .rst_n(rst_n), .tile_id(t[15:0]), .ib_go(tgo), .ib(tb),
                .xl(xl_d[(t % NXL)*TG*32 +: TG*32]),
                .t_out(lw[LT][t*W*32 +: W*32]), .t_vout(lvv[LT][t]),
                .n_a(na), .n_b(nb), .n_va(nva), .n_y(ny), .n_vy(nvy), .fault(tile_fault[t]),
                .rom_ce(t_rom_ce[t*CODE_BANKS +: CODE_BANKS]), .rom_addr(t_rom_addr[t*12 +: 12]),
                .rom_rd(t_rom_rd[t*2*CODE_BANKS*266 +: 2*CODE_BANKS*266]),
                .kvs_r_ce(), .kvs_r_addr(), .kvs_rd({TG*W*8{1'b0}}),
                .kv_re(t_kv_re[t]), .kv_addr(t_kv_addr[t*TG*AW +: TG*AW]), .kv_q(kvq));
        end
    endgenerate
    assign t_lvl = lw[TCUT][NPT*W*32-1:0];
    assign fab_fault = |tile_fault;     // lanes, tile tree levels and hosted nodes
endmodule

// The spine part of the array: the engine top (ot_qwen_w12_matvec_part PART 2), the
// instruction broadcast and the x network, facing the tile fabric.
module ot_qwen_me_spine_w12 #(
    parameter integer W  = 16,
    parameter integer IL = 8,
    parameter integer AW = 24,
    parameter integer NW = 16,
    parameter integer INT8_SCALE_WCS_BASE = 1,
    parameter integer GT = 80,
    parameter integer TG = 4,
    parameter integer SMIN = 3,
    parameter integer SMAX = 5,
    parameter integer TCUT = 3,
    parameter integer BD = 0,
    parameter integer XVM = 0,
    parameter integer NWS = 0,
    parameter integer TWS = 0,
    parameter integer ORD = 0,
    parameter integer MEM_EXTRA = 0,      // tile memory capture stage (ot_qwen_rom_tile_logic_w12)
    parameter integer SCALE_LOCAL = 0,
    parameter integer ACC_LAT = 5,        // lane accumulator FP32 add latency (ot_qwen_w12_matvec_part ACC_LAT)
    parameter integer FAST_ISSUE = 0,     // 1.2 GHz issue loop (ot_qwen_w12_matvec_part FAST_ISSUE)
    parameter integer KV_PREP = 0,        // KV-op offset pipeline cycles (ot_qwen_w12_matvec_part KV_PREP)
    parameter integer MUL_LAT = 5,        // lane BF16 product latency (ot_qwen_w12_matvec_part MUL_LAT)
    parameter integer TREE_LAT = 3        // split-tree pair adder latency (ot_qwen_w12_matvec_part TREE_LAT)
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    output wire              ready,
    output wire              idle,
    input  wire [NW-1:0]     i_nout, i_tiles, i_k,
    input  wire              i_wsrc,
    input  wire [AW-1:0]     i_wbase, i_ts, i_ks, i_js,
    input  wire [AW-1:0]     i_xbase, i_xks, i_xjs, i_xcs,
    input  wire [2:0]        i_jsh,
    input  wire [3:0]        i_split,
    input  wire [AW-1:0]     i_wcs,
    input  wire              i_round,
    input  wire [AW-1:0]     i_obase, i_ots, i_ojs,
    input  wire              i_mmode, i_oen, i_amax, i_rmax,
    input  wire [AW-1:0]     i_mbase,
    // result-port scale ROM (spine)
    output wire              scale_re,
    output wire [(GT >> SMIN)-1:0]     scale_gre,
    output wire [(GT >> SMIN)*AW-1:0]  scale_addr,
    input  wire [(GT >> SMIN)*W*16-1:0] scale_q,
    // vector-memory x read port: one element per chunk
    output wire [(1<<SMAX)-1:0]    x_re,
    output wire [(1<<SMAX)*AW-1:0] x_addr,
    input  wire [(1<<SMAX)*32-1:0] x_q,
    // the engine's own ROM and KV read strobes (the tiles issue the same reads BD cycles later)
    output wire              wrom_re,
    output wire [AW-1:0]     wrom_addr,
    output wire              kv_re,
    // fabric side (tiles and tree nodes)
    output wire              tgo,
    output wire [3*NW+13*AW+13-1:0] tb,
    output wire [(1<<SMAX)*32-1:0] xl_d,
    input  wire [(GT >> TCUT)*W*32-1:0] t_lvl,
    input  wire              fab_fault,
    // results (port groups only)
    output wire              ov,
    output wire [(GT >> SMIN)-1:0]     o_we,
    output wire [(GT >> SMIN)*AW-1:0]  o_addr,
    output wire [(GT >> SMIN)*W-1:0]   o_mask,
    output wire [(GT >> SMIN)*W*32-1:0] o_data,
    output wire [NW-1:0]     am_idx,
    output wire [31:0]       am_val,
    output wire              am_any,
    output wire              mx_we,
    output wire [AW-1:0]     mx_addr,
    output wire [W-1:0]      mx_mask,
    output wire [W*32-1:0]   mx_data,
    output wire [15:0]       progress,
    output wire              fault
);
    localparam integer NT  = GT / TG;
    localparam integer LT  = $clog2(TG);
    localparam integer NXC = 1 << SMAX;
    localparam integer NXL = NXC / TG;
    localparam integer XD  = BD + (TCUT - LT) * NWS + TWS + MEM_EXTRA;
    localparam integer NPT = GT >> TCUT;                  // tree words into the top
    localparam integer IBW = 3 * NW + 13 * AW + 13;       // the i_* fields
    localparam integer IREG = (BD > XVM && BD > 0) ? 1 : 0;   // the tile's own input stage is one of BD
    localparam integer NREG = (NWS > 0) ? 1 : 0;

    // -- spine top --------------------------------------------------------------
    wire [GT-1:0]    x_re_full;
    wire [GT*AW-1:0] x_addr_full;
    wire [GT*32-1:0] x_q_full;
    wire [NPT*W*32-1:0] t_in;
    reg                 fault_in;
    wire                top_fault;
    reg                 range_fault;
    ot_qwen_w12_matvec_part #(.W(W), .G(GT), .IL(IL), .AW(AW), .NW(NW), .INT8_WEIGHT(1),
        .INT8_SCALE_WCS_BASE(INT8_SCALE_WCS_BASE), .PART(2), .GT(GT), .SMIN(SMIN), .TCUT(TCUT),
        .XD(XD), .NX(NXC), .ORD(ORD), .SCALE_LOCAL(SCALE_LOCAL), .GOUT(GT >> SMIN), .ACC_LAT(ACC_LAT), .TREE_LAT(TREE_LAT), .FAST_ISSUE(FAST_ISSUE), .KV_PREP(KV_PREP), .MUL_LAT(MUL_LAT)) u_top (
        .clk(clk), .rst_n(rst_n), .go(go), .ready(ready), .idle(idle),
        .i_nout(i_nout), .i_tiles(i_tiles), .i_k(i_k), .i_wsrc(i_wsrc),
        .i_wbase(i_wbase), .i_ts(i_ts), .i_ks(i_ks), .i_js(i_js),
        .i_xbase(i_xbase), .i_xks(i_xks), .i_xjs(i_xjs), .i_xcs(i_xcs),
        .i_jsh(i_jsh), .i_split(i_split), .i_wcs(i_wcs), .i_round(i_round),
        .i_obase(i_obase), .i_ots(i_ots), .i_ojs(i_ojs),
        .i_mmode(i_mmode), .i_oen(i_oen), .i_amax(i_amax), .i_rmax(i_rmax), .i_mbase(i_mbase),
        .wrom_re(wrom_re), .wrom_addr(wrom_addr), .wrom_q({GT*W*8{1'b0}}),
        .scale_re(scale_re), .scale_gre(scale_gre), .scale_addr(scale_addr), .scale_q(scale_q),
        .kv_re(kv_re), .kv_addr(), .kv_q({GT*W*32{1'b0}}),
        .x_re(x_re_full), .x_addr(x_addr_full), .x_q(x_q_full),
        .ov(ov), .o_we(o_we), .o_addr(o_addr), .o_mask(o_mask), .o_data(o_data),
        .am_idx(am_idx), .am_val(am_val), .am_any(am_any),
        .mx_we(mx_we), .mx_addr(mx_addr), .mx_mask(mx_mask), .mx_data(mx_data),
        .progress(progress), .fault(top_fault),
        .i_gbase(32'd0), .t_in(t_in), .t_fault_in(fault_in),
        .t_out(), .t_vout(), .t_fault(), .active_o());
    genvar c;
    generate
        for (c = 0; c < GT; c = c + 1) begin : g_xq
            if (c < NXC) begin : g_p
                assign x_q_full[c*32 +: 32] = x_q[c*32 +: 32];
            end else begin : g_z
                assign x_q_full[c*32 +: 32] = 32'd0;
            end
        end
        for (c = 0; c < NXC; c = c + 1) begin : g_xport
            if (c < GT) begin : g_p
                assign x_re[c] = x_re_full[c];
                assign x_addr[c*AW +: AW] = x_addr_full[c*AW +: AW];
            end else begin : g_z
                assign x_re[c] = 1'b0;
                assign x_addr[c*AW +: AW] = {AW{1'b0}};
            end
        end
    endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) range_fault <= 1'b0;
        else if (go && ready && (i_split > SMAX)) range_fault <= 1'b1;
    end
    assign fault = top_fault | range_fault;

    // -- instruction broadcast: BD stages to every tile ----------------------------
    wire [IBW-1:0] ib = {i_nout, i_tiles, i_k, i_wsrc, i_wbase, i_ts, i_ks, i_js, i_xbase, i_xks, i_xjs, i_xcs,
                         i_jsh, i_split, i_wcs, i_round, i_obase, i_ots, i_ojs, i_mmode, i_oen, i_amax, i_rmax,
                         i_mbase};
    ot_hdc_delay #(.W(IBW), .D(BD - IREG)) u_ib (.clk(clk), .rst_n(rst_n), .d(ib), .q(tb));
    ot_hdc_delay #(.W(1), .D(BD - IREG), .RESET(1)) u_go (.clk(clk), .rst_n(rst_n), .d(go && ready), .q(tgo));

    // -- x network: quad lines built at the vector memory, BD - XVM stages out ----
    //: the split of the element whose x arrives now: the op's split, two edges
    //: after issue (x_addr registered, then the synchronous read), plus XVM
    reg  [3:0] op_split;
    always @(posedge clk) if (go && ready) op_split <= i_split;
    wire [3:0] x_split;
    ot_hdc_delay #(.W(4), .D(2 + XVM)) u_xs (.clk(clk), .rst_n(rst_n), .d(op_split), .q(x_split));
    //: op_split changes on the accepting edge while the previous op's last x
    //: may still be in flight; ops are issued back to back only after the
    //: previous issue loop ends, and the two cycles of read latency are covered
    //: because x_split is delayed from the issue-time value (see the gate).
    wire [NXL*TG*32-1:0] xl;
    genvar r, i;
    generate
        for (r = 0; r < NXL; r = r + 1) begin : g_line
            wire [SMAX:0] quads = (1 << x_split) / TG;          // S / TG lines are distinct
            wire [SMAX:0] src = r & (quads - 1);             // quads is a power of two
            for (i = 0; i < TG; i = i + 1) begin : g_e
                assign xl[(r*TG + i)*32 +: 32] = x_q[(src*TG + i)*32 +: 32];
            end
        end
    endgenerate
    ot_hdc_delay #(.W(NXL*TG*32), .D(BD - XVM - IREG)) u_xnet (.clk(clk), .rst_n(rst_n), .d(xl), .q(xl_d));

    ot_hdc_delay #(.W(NPT*W*32), .D(TWS)) u_tws (.clk(clk), .rst_n(rst_n), .d(t_lvl), .q(t_in));
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) fault_in <= 1'b0;
        else fault_in <= fab_fault;
    end
endmodule


// One upper split-tree node: the pair sum of two tree words (ot_qwen_w12_tadd, then
// the level's output register: TL = TREE_LAT + 1 cycles), after WS wire stages.
module ot_qwen_me_node_w12 #(
    parameter integer W = 16,
    parameter integer WS = 0,
    parameter integer TREE_LAT = 3
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [W*32-1:0] a,
    input  wire [W*32-1:0] b,
    input  wire            va,
    output reg  [W*32-1:0] y,
    output wire            vy,
    output wire            fault
);
    wire [W*32-1:0] ad, bd;
    wire            vd;
    ot_hdc_delay #(.W(2*W*32), .D(WS)) u_w (.clk(clk), .rst_n(rst_n), .d({a, b}), .q({ad, bd}));
    ot_hdc_delay #(.W(1), .D(WS), .RESET(1)) u_wv (.clk(clk), .rst_n(rst_n), .d(va), .q(vd));
    wire [W-1:0] pf;
    genvar p;
    generate
        for (p = 0; p < W; p = p + 1) begin : g_add
            wire [31:0] s;
            ot_qwen_w12_tadd #(.LAT(TREE_LAT)) u_add (clk, rst_n, vd, ad[32*p +: 32], bd[32*p +: 32], s, pf[p]);
            always @(posedge clk) y[32*p +: 32] <= s;
        end
    endgenerate
    ot_hdc_delay #(.W(1), .D(TREE_LAT + 1), .RESET(1)) u_vy (.clk(clk), .rst_n(rst_n), .d(vd), .q(vy));
    assign fault = |pf;
endmodule
