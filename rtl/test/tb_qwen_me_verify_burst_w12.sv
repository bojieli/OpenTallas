`timescale 1ns/1ps
// Multi-position verify on the W12 tile-array matrix engine: P back-to-back
// copies of one dense INT8 matrix op (the same weight words, P different x
// vectors and result bases), as a P-position speculative verify would issue a
// projection.  No RTL is changed: the bench drives the unmodified
// ot_qwen_me_array_w12 with the runtime's wire stages (BD 41, XVM 1, NWS 5,
// TWS 38, ORD 7, MEM_EXTRA 1).
//
// The case is chosen at run time by plusargs (+P +TILES +KK +SPLIT +MUTANT).
// Phase A issues the P ops one at a time, draining the engine between them
// (the single-position schedule); phase B issues them back to back, each go
// on the first cycle the engine is ready.  Checks:
//   * the phase-B result-write sequence (group, address, mask, data) equals the
//     phase-A sequence: back-to-back issue is bit-identical to solo issue;
//   * the write counts are equal and no fault is raised.
// MUTANT = 1 (negative control) shifts one burst position's x base and must fail.
// Reported: the issue spacing of consecutive gos in phase B, the solo op
// latency (go -> last result write), and the burst span; the increment per
// extra position is (burst - solo) / (P - 1).
module tb_qwen_me_verify_burst_w12;
    parameter integer GT = 32, TG = 4, SMIN = 3, SMAX = 5, TCUT = 3;
    parameter integer BD = 41, XVM = 1, NWS = 5, TWS = 38, ORD = 7, MEM_EXTRA = 1;
    // run-time knobs (one build serves every case): +P= +TILES= +KK= +SPLIT= +MUTANT=
    // MUTANT = 1: position 1's burst copy reads a shifted x vector and must FAIL
    integer P = 4, TILES = 2, KK = 8, SPLIT = 4, MUTANT = 0;
    parameter integer W = 16;
    localparam integer IL = 8, AW = 24, NW = 16;
    localparam integer NT = GT / TG, NXC = 1 << SMAX;
    localparam integer CB = 2;

    reg clk = 0, rst_n = 0;
    always #1 clk = ~clk;

    function automatic [31:0] mix(input [31:0] a, input [31:0] b, input [31:0] salt);
        reg [31:0] x;
        begin
            x = a * 32'h9E3779B1 ^ (b + 32'h7F4A7C15) * 32'h85EBCA77 ^ salt;
            x = x ^ (x >> 15); x = x * 32'h2C1B3C6D; x = x ^ (x >> 12); x = x * 32'h297A2D39; x = x ^ (x >> 15);
            mix = x;
        end
    endfunction
    function automatic [7:0] rom(input [31:0] addr, input [31:0] lane);
        rom = mix(addr, lane, 32'h1111);
    endfunction
    function automatic [15:0] bf16v(input [31:0] h);
        bf16v = {h[31], 8'd124 + {5'd0, h[10:8] % 3'd6}, h[6:0]};
    endfunction
    function automatic [15:0] scl(input [31:0] addr, input [31:0] lane);
        scl = bf16v(mix(addr, lane, 32'h2222));
    endfunction
    function automatic [31:0] xv(input [31:0] addr);
        reg [31:0] h;
        begin h = mix(addr, 0, 32'h4444); xv = {h[31], 8'd124 + {5'd0, h[26:24] % 3'd6}, h[22:0]}; end
    endfunction

    reg              go;
    reg [NW-1:0]     i_nout, i_tiles, i_k;
    reg              i_wsrc, i_round, i_mmode, i_oen, i_amax, i_rmax;
    reg [AW-1:0]     i_wbase, i_ts, i_ks, i_js, i_xbase, i_xks, i_xjs, i_xcs, i_wcs, i_obase, i_ots, i_ojs, i_mbase;
    reg [2:0]        i_jsh;
    reg [3:0]        i_split;

    wire a_ready, a_idle, a_scale_re, a_ov, a_am_any, a_mx_we, a_fault;
    wire [GT-1:0] a_scale_gre, a_o_we;
    wire [GT*AW-1:0] a_scale_addr, a_o_addr, a_t_kv_addr;
    reg  [GT*W*16-1:0] a_scale_q;
    wire [NXC-1:0] a_x_re;
    wire [NXC*AW-1:0] a_x_addr;
    reg  [NXC*32-1:0] a_x_q;
    wire [NT*CB-1:0] a_t_rom_ce;
    wire [NT*12-1:0] a_t_rom_addr;
    reg  [NT*2*CB*266-1:0] a_t_rom_rd;
    wire [NT-1:0] a_t_kv_re;
    reg  [GT*W*32-1:0] a_t_kv_q;
    wire [GT*W-1:0] a_o_mask;
    wire [GT*W*32-1:0] a_o_data;
    wire [NW-1:0] a_am_idx; wire [31:0] a_am_val;
    wire [AW-1:0] a_mx_addr; wire [W-1:0] a_mx_mask; wire [W*32-1:0] a_mx_data; wire [15:0] a_progress;
    ot_qwen_me_array_w12 #(.W(W), .IL(IL), .AW(AW), .NW(NW), .GT(GT), .TG(TG), .SMIN(SMIN), .SMAX(SMAX), .TCUT(TCUT),
                       .BD(BD), .XVM(XVM), .NWS(NWS), .TWS(TWS), .ORD(ORD), .CODE_BANKS(CB), .KV_LOCAL(0),
                       .MEM_EXTRA(MEM_EXTRA)) u_arr (
        .clk(clk), .rst_n(rst_n), .go(go), .ready(a_ready), .idle(a_idle),
        .i_nout(i_nout), .i_tiles(i_tiles), .i_k(i_k), .i_wsrc(i_wsrc), .i_wbase(i_wbase), .i_ts(i_ts),
        .i_ks(i_ks), .i_js(i_js), .i_xbase(i_xbase), .i_xks(i_xks), .i_xjs(i_xjs), .i_xcs(i_xcs), .i_jsh(i_jsh),
        .i_split(i_split), .i_wcs(i_wcs), .i_round(i_round), .i_obase(i_obase), .i_ots(i_ots), .i_ojs(i_ojs),
        .i_mmode(i_mmode), .i_oen(i_oen), .i_amax(i_amax), .i_rmax(i_rmax), .i_mbase(i_mbase),
        .scale_re(a_scale_re), .scale_gre(a_scale_gre), .scale_addr(a_scale_addr), .scale_q(a_scale_q),
        .x_re(a_x_re), .x_addr(a_x_addr), .x_q(a_x_q),
        .t_rom_ce(a_t_rom_ce), .t_rom_addr(a_t_rom_addr), .t_rom_rd(a_t_rom_rd),
        .t_kv_re(a_t_kv_re), .t_kv_addr(a_t_kv_addr), .t_kv_q(a_t_kv_q),
        .ov(a_ov), .o_we(a_o_we), .o_addr(a_o_addr), .o_mask(a_o_mask), .o_data(a_o_data),
        .am_idx(a_am_idx), .am_val(a_am_val), .am_any(a_am_any), .mx_we(a_mx_we), .mx_addr(a_mx_addr),
        .mx_mask(a_mx_mask), .mx_data(a_mx_data), .progress(a_progress), .fault(a_fault));

    integer g, l, b, pc;
    always @(posedge clk) begin
        for (g = 0; g < GT; g = g + 1)
            if (a_scale_gre[g]) for (l = 0; l < W; l = l + 1) a_scale_q[16*(g*W+l) +: 16] <= scl(a_scale_addr[g*AW +: AW], l);
        for (g = 0; g < NT; g = g + 1)
            for (b = 0; b < CB; b = b + 1)
                if (a_t_rom_ce[g*CB + b])
                    for (pc = 0; pc < 2; pc = pc + 1) begin
                        a_t_rom_rd[((g*2 + pc)*CB + b)*266 +: 266] <= 266'd0;
                        for (l = 0; l < 2 * W; l = l + 1)
                            a_t_rom_rd[((g*2 + pc)*CB + b)*266 + 8*l +: 8] <=
                                rom(b * 4096 + a_t_rom_addr[g*12 +: 12], (g * TG + 2*pc) * W + l);
                    end
        for (g = 0; g < NXC; g = g + 1)
            if (a_x_re[g]) a_x_q[32*g +: 32] <= xv(a_x_addr[g*AW +: AW]);
    end

    // one dense INT8 op of the program's shape (tools/hdc_program.py: ts = k*IL, ks = IL, js = 1), position p
    task automatic set_op(input integer p);
        begin
            i_wsrc = 0; i_mmode = 0; i_rmax = 0; i_amax = 0; i_oen = 1; i_round = 1;
            i_split = SPLIT; i_tiles = TILES; i_k = KK;
            i_wbase = 64; i_ts = KK * IL; i_ks = IL; i_js = 1; i_jsh = 0; i_wcs = 3000;
            i_xbase = 1024 + p * 4096; i_xcs = KK; i_xks = 1; i_xjs = 0;
            i_obase = 100000 + p * 8192; i_ots = IL; i_ojs = 1; i_mbase = 0;
            i_nout = TILES * (GT >> SPLIT) * W * IL;
        end
    endtask

    // result writes in issue order: (group, address, mask, data); the engine retires in order, so the burst's
    // write sequence must equal the solo sequence element for element
    localparam integer QW = 8 + AW + W + W * 32;
    localparam integer QN = 8192;
    reg [QW-1:0] qa [0:QN-1];
    integer cyc = 0, phase = 0, errors = 0, nA = 0, nB = 0, lastA = 0, lastB = 0;
    always @(negedge clk) if (rst_n) begin
        cyc = cyc + 1;
        if (cyc > 2000000) begin $display("FAIL timeout"); $finish; end
        if (a_fault) begin if (errors < 10) $display("FAIL fault cyc=%0d", cyc); errors = errors + 1; end
        for (g = 0; g < GT; g = g + 1) if (a_o_we[g]) begin
            if (phase == 1) begin
                if (nA < QN) qa[nA] = {g[7:0], a_o_addr[g*AW +: AW], a_o_mask[g*W +: W], a_o_data[g*W*32 +: W*32]};
                nA = nA + 1; lastA = cyc;
            end else if (phase == 2) begin
                if (nB >= nA || qa[nB] !== {g[7:0], a_o_addr[g*AW +: AW], a_o_mask[g*W +: W], a_o_data[g*W*32 +: W*32]}) begin
                    if (errors < 10) $display("FAIL burst write %0d differs g=%0d addr=%0d", nB, g, a_o_addr[g*AW +: AW]);
                    errors = errors + 1;
                end
                nB = nB + 1; lastB = cyc;
            end
        end
    end

    integer p, t0, solo_first, solo_lat, burst_t0, prev_go, spacing_min, spacing_max, sp, busy;
    integer go_cyc [0:63];
    initial begin
        if ($value$plusargs("P=%d", P)) ;
        if ($value$plusargs("TILES=%d", TILES)) ;
        if ($value$plusargs("KK=%d", KK)) ;
        if ($value$plusargs("SPLIT=%d", SPLIT)) ;
        if ($value$plusargs("MUTANT=%d", MUTANT)) ;
        go = 0; set_op(0);
        repeat (4) @(posedge clk);
        rst_n = 1;
        repeat (4) @(posedge clk);
        // phase A: one position at a time, drained in between
        phase = 1; solo_lat = 0;
        for (p = 0; p < P; p = p + 1) begin
            set_op(p);
            while (!(a_ready && a_idle)) @(posedge clk);
            #0.1 go = 1; t0 = cyc;
            @(posedge clk); #0.1 go = 0;
            @(posedge clk);
            while (!a_idle) @(posedge clk);
            repeat (2) @(posedge clk);
            if (p == 0) solo_lat = lastA - t0;
            else if (lastA - t0 != solo_lat) begin $display("FAIL solo latency varies %0d vs %0d", lastA - t0, solo_lat); errors = errors + 1; end
        end
        repeat (8) @(posedge clk);
        // phase B: back to back, each go on the first ready cycle
        phase = 2;
        for (p = 0; p < P; p = p + 1) begin
            set_op(p);
            if (MUTANT != 0 && p == 1) i_xbase = i_xbase + 1;
            #0.1;
            while (!a_ready) begin @(posedge clk); #0.1; end
            go = 1; go_cyc[p] = cyc;
            @(posedge clk); #0.1 go = 0;
        end
        busy = 0;
        while (!a_idle || busy < 8) begin @(posedge clk); busy = a_idle ? busy + 1 : 0; end
        repeat (4) @(posedge clk);
        burst_t0 = go_cyc[0];
        spacing_min = 1 << 30; spacing_max = 0;
        for (p = 1; p < P; p = p + 1) begin
            sp = go_cyc[p] - go_cyc[p-1];
            if (sp < spacing_min) spacing_min = sp;
            if (sp > spacing_max) spacing_max = sp;
        end
        if (P == 1) begin spacing_min = 0; spacing_max = 0; end
        if (nA != nB) begin $display("FAIL write counts solo=%0d burst=%0d", nA, nB); errors = errors + 1; end
        if (errors == 0 && nA > 0)
            $display("PASS P=%0d GT=%0d TG=%0d SPLIT=%0d TILES=%0d K=%0d issue_cycles=%0d spacing_min=%0d spacing_max=%0d solo_latency=%0d burst_span=%0d increment_per_position=%0d writes=%0d BD=%0d NWS=%0d TWS=%0d ORD=%0d MEM_EXTRA=%0d",
                     P, GT, TG, SPLIT, TILES, KK, TILES * KK * IL, spacing_min, spacing_max, solo_lat, lastB - burst_t0,
                     (P > 1) ? ((lastB - burst_t0 - solo_lat) / (P - 1)) : 0, nA, BD, NWS, TWS, ORD, MEM_EXTRA);
        else $display("FAIL errors=%0d writes=%0d/%0d", errors, nA, nB);
        $finish;
    end
endmodule
