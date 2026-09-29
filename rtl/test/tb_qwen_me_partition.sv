`timescale 1ns/1ps
// Exactness gate of the partitioned matrix engine (W12).
//
//   ref   the ORIGINAL ot_hdc_matvec (main 0e8df511), renamed ot_hdc_matvec_ref
//         by tools/rtl_qwen_me_partition_gate.py, G = GT
//   unp   the new ot_hdc_matvec, defaults (unpruned):   every port, every cycle == ref
//   mono  the new ot_hdc_matvec, SMIN (pruned):         every memory request, result
//         write, progress, ready and fault on every cycle == ref; the argmax and
//         per-slot maxima (a shallower tree) as event sequences == ref
//   arr   ot_qwen_me_array (GT/TG tiles + tree nodes + spine top, wire stages
//         BD/NWS/TWS/ORD):  with zero wire stages every port, every cycle == mono;
//         otherwise every result write, maxima word, argmax and scale read as an
//         event sequence == mono, the first result exactly XD + ORD cycles later
//
// Memories are deterministic hash images served with one-cycle registered
// reads (hold when not read), as the core's; the array's tiles are served
// from the same ROM/KV images by their own addresses and its x chunk port
// from the same vector memory.  Random back-to-back ops, dense and KV-sourced,
// splits SMIN..SMAX.  MUTANT = 1 swaps the ROM slices of tiles 0 and 1 and
// must fail.
module tb_qwen_me_partition;
    parameter integer GT = 80, TG = 4, SMIN = 3, SMAX = 5, TCUT = 3;
    parameter integer BD = 0, XVM = 0, NWS = 0, TWS = 0, ORD = 0;
    parameter integer NOPS = 300, SEED = 1, MUTANT = 0;
    parameter integer W = 16;
    localparam integer IL = 8, AW = 24, NW = 16;
    localparam integer NT = GT / TG, NXC = 1 << SMAX, LT = $clog2(TG);
    localparam integer XD = BD + (TCUT - LT) * NWS + TWS;
    localparam integer ZERO_WIRE = (XD == 0 && ORD == 0);

    reg clk = 0, rst_n = 0;
    always #1 clk = ~clk;

    // ---- hash images --------------------------------------------------------
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
    // finite BF16 in [2^-3, 2^3), either sign
    function automatic [15:0] bf16v(input [31:0] h);
        bf16v = {h[31], 8'd124 + {5'd0, h[10:8] % 3'd6}, h[6:0]};
    endfunction
    function automatic [15:0] scl(input [31:0] addr, input [31:0] lane);
        scl = bf16v(mix(addr, lane, 32'h2222));
    endfunction
    function automatic [31:0] kvw(input [31:0] addr, input [31:0] lane);
        kvw = {bf16v(mix(addr, lane, 32'h3333)), 16'h0000};
    endfunction
    function automatic [31:0] xv(input [31:0] addr);
        reg [31:0] h;
        begin h = mix(addr, 0, 32'h4444); xv = {h[31], 8'd124 + {5'd0, h[26:24] % 3'd6}, h[22:0]}; end
    endfunction

    // ---- instruction ----------------------------------------------------------
    reg              go;
    reg [NW-1:0]     i_nout, i_tiles, i_k;
    reg              i_wsrc, i_round, i_mmode, i_oen, i_amax, i_rmax;
    reg [AW-1:0]     i_wbase, i_ts, i_ks, i_js, i_xbase, i_xks, i_xjs, i_xcs, i_wcs, i_obase, i_ots, i_ojs, i_mbase;
    reg [2:0]        i_jsh;
    reg [3:0]        i_split;

    // ---- DUT ports --------------------------------------------------------------
`define MV_PORTS(P) \
    wire P``_ready, P``_idle, P``_wrom_re, P``_scale_re, P``_kv_re, P``_ov, P``_am_any, P``_mx_we, P``_fault; \
    wire [AW-1:0] P``_wrom_addr, P``_mx_addr; \
    wire [GT-1:0] P``_scale_gre, P``_x_re, P``_o_we; \
    wire [GT*AW-1:0] P``_scale_addr, P``_kv_addr, P``_x_addr, P``_o_addr; \
    wire [GT*W-1:0] P``_o_mask; \
    wire [GT*W*32-1:0] P``_o_data; \
    wire [NW-1:0] P``_am_idx; wire [31:0] P``_am_val; \
    wire [W-1:0] P``_mx_mask; wire [W*32-1:0] P``_mx_data; wire [15:0] P``_progress; \
    reg [GT*W*8-1:0] P``_wrom_q; reg [GT*W*16-1:0] P``_scale_q; reg [GT*W*32-1:0] P``_kv_q; reg [GT*32-1:0] P``_x_q;
    `MV_PORTS(r)
    `MV_PORTS(u)
    `MV_PORTS(m)
`define MV_CONN(P) \
        .clk(clk), .rst_n(rst_n), .go(go), .ready(P``_ready), .idle(P``_idle), \
        .i_nout(i_nout), .i_tiles(i_tiles), .i_k(i_k), .i_wsrc(i_wsrc), .i_wbase(i_wbase), .i_ts(i_ts), \
        .i_ks(i_ks), .i_js(i_js), .i_xbase(i_xbase), .i_xks(i_xks), .i_xjs(i_xjs), .i_xcs(i_xcs), .i_jsh(i_jsh), \
        .i_split(i_split), .i_wcs(i_wcs), .i_round(i_round), .i_obase(i_obase), .i_ots(i_ots), .i_ojs(i_ojs), \
        .i_mmode(i_mmode), .i_oen(i_oen), .i_amax(i_amax), .i_rmax(i_rmax), .i_mbase(i_mbase), \
        .wrom_re(P``_wrom_re), .wrom_addr(P``_wrom_addr), .wrom_q(P``_wrom_q), \
        .scale_re(P``_scale_re), .scale_gre(P``_scale_gre), .scale_addr(P``_scale_addr), .scale_q(P``_scale_q), \
        .kv_re(P``_kv_re), .kv_addr(P``_kv_addr), .kv_q(P``_kv_q), .x_re(P``_x_re), .x_addr(P``_x_addr), .x_q(P``_x_q), \
        .ov(P``_ov), .o_we(P``_o_we), .o_addr(P``_o_addr), .o_mask(P``_o_mask), .o_data(P``_o_data), \
        .am_idx(P``_am_idx), .am_val(P``_am_val), .am_any(P``_am_any), .mx_we(P``_mx_we), .mx_addr(P``_mx_addr), \
        .mx_mask(P``_mx_mask), .mx_data(P``_mx_data), .progress(P``_progress), .fault(P``_fault)
    ot_hdc_matvec_ref #(.W(W), .G(GT), .IL(IL), .AW(AW), .NW(NW), .INT8_WEIGHT(1), .INT8_SCALE_WCS_BASE(1)) u_ref (`MV_CONN(r));
    ot_hdc_matvec #(.W(W), .G(GT), .IL(IL), .AW(AW), .NW(NW), .INT8_WEIGHT(1), .INT8_SCALE_WCS_BASE(1)) u_unp (`MV_CONN(u));
    ot_hdc_matvec #(.W(W), .G(GT), .IL(IL), .AW(AW), .NW(NW), .INT8_WEIGHT(1), .INT8_SCALE_WCS_BASE(1),
                    .SMIN(SMIN)) u_mono (`MV_CONN(m));

    // array
    wire a_ready, a_idle, a_scale_re, a_ov, a_am_any, a_mx_we, a_fault;
    wire [GT-1:0] a_scale_gre, a_o_we;
    wire [GT*AW-1:0] a_scale_addr, a_o_addr, a_t_kv_addr;
    reg  [GT*W*16-1:0] a_scale_q;
    wire [NXC-1:0] a_x_re;
    wire [NXC*AW-1:0] a_x_addr;
    reg  [NXC*32-1:0] a_x_q;
    localparam integer CB = 2;
    wire [NT*CB-1:0] a_t_rom_ce;
    wire [NT*12-1:0] a_t_rom_addr;
    reg  [NT*2*CB*266-1:0] a_t_rom_rd;
    wire [NT-1:0] a_t_kv_re;
    reg  [GT*W*32-1:0] a_t_kv_q;
    wire [GT*W-1:0] a_o_mask;
    wire [GT*W*32-1:0] a_o_data;
    wire [NW-1:0] a_am_idx; wire [31:0] a_am_val;
    wire [AW-1:0] a_mx_addr; wire [W-1:0] a_mx_mask; wire [W*32-1:0] a_mx_data; wire [15:0] a_progress;
    ot_qwen_me_array #(.W(W), .IL(IL), .AW(AW), .NW(NW), .GT(GT), .TG(TG), .SMIN(SMIN), .SMAX(SMAX), .TCUT(TCUT),
                       .BD(BD), .XVM(XVM), .NWS(NWS), .TWS(TWS), .ORD(ORD), .CODE_BANKS(CB), .KV_LOCAL(0)) u_arr (
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

    // ---- memory service (registered, hold when not read) -------------------------
    integer g, l, b, pc;
`define MV_MEM(P) \
        if (P``_wrom_re) for (g = 0; g < GT * W; g = g + 1) P``_wrom_q[8*g +: 8] <= rom(P``_wrom_addr, g); \
        for (g = 0; g < GT; g = g + 1) begin \
            if (P``_scale_gre[g]) for (l = 0; l < W; l = l + 1) P``_scale_q[16*(g*W+l) +: 16] <= scl(P``_scale_addr[g*AW +: AW], l); \
            if (P``_kv_re) for (l = 0; l < W; l = l + 1) P``_kv_q[32*(g*W+l) +: 32] <= kvw(P``_kv_addr[g*AW +: AW], l); \
            if (P``_x_re[g]) P``_x_q[32*g +: 32] <= xv(P``_x_addr[g*AW +: AW]); \
        end
    always @(posedge clk) begin
        `MV_MEM(r)
        `MV_MEM(u)
        `MV_MEM(m)
        for (g = 0; g < GT; g = g + 1) begin
            if (a_scale_gre[g]) for (l = 0; l < W; l = l + 1) a_scale_q[16*(g*W+l) +: 16] <= scl(a_scale_addr[g*AW +: AW], l);
            if (a_t_kv_re[g / TG]) for (l = 0; l < W; l = l + 1) a_t_kv_q[32*(g*W+l) +: 32] <= kvw(a_t_kv_addr[g*AW +: AW], l);
        end
        // tile ROM macros: bank b of pair column p holds words 4096b.. of the pair's 32 lanes
        for (g = 0; g < NT; g = g + 1)
            for (b = 0; b < CB; b = b + 1)
                if (a_t_rom_ce[g*CB + b])
                    for (pc = 0; pc < 2; pc = pc + 1) begin
                        a_t_rom_rd[((g*2 + pc)*CB + b)*266 +: 266] <= 266'd0;
                        for (l = 0; l < 2 * W; l = l + 1)
                            a_t_rom_rd[((g*2 + pc)*CB + b)*266 + 8*l +: 8] <=
                                rom(b * 4096 + a_t_rom_addr[g*12 +: 12],
                                    (((MUTANT != 0 && g < 2) ? (1 - g) : g) * TG + 2*pc) * W + l);
                    end
        for (g = 0; g < NXC; g = g + 1)
            if (a_x_re[g]) a_x_q[32*g +: 32] <= xv(a_x_addr[g*AW +: AW]);
    end

    // ---- stimulus -------------------------------------------------------------------
    integer seed, ops, sp, per_round, maxrows;
    task automatic new_op;
        begin
            sp = SMIN + ($urandom(seed) % (SMAX - SMIN + 1)); seed = seed + 1;
            per_round = GT >> sp;
            i_split = sp;
            i_wsrc = ($urandom(seed) % 3) == 0; seed = seed + 1;
            i_tiles = 1 + $urandom(seed) % 3; seed = seed + 1;
            i_jsh = $urandom(seed) % 4; seed = seed + 1;
            i_js = $urandom(seed) % 3; seed = seed + 1;
            i_ks = 1 + $urandom(seed) % 40; seed = seed + 1;
            i_ts = 1 + $urandom(seed) % 200; seed = seed + 1;
            i_wbase = $urandom(seed) % 4000; seed = seed + 1;
            i_wcs = $urandom(seed) % 3000; seed = seed + 1;
            i_xbase = $urandom(seed) % 3000; seed = seed + 1;
            i_xks = $urandom(seed) % 7; seed = seed + 1;
            i_xjs = $urandom(seed) % 5; seed = seed + 1;
            i_xcs = $urandom(seed) % 9; seed = seed + 1;
            i_round = $urandom(seed) % 2; seed = seed + 1;
            i_obase = $urandom(seed) % 500; seed = seed + 1;
            i_ots = $urandom(seed) % 9; seed = seed + 1;
            i_ojs = $urandom(seed) % 3; seed = seed + 1;
            i_oen = ($urandom(seed) % 5) != 0; seed = seed + 1;
            i_mbase = $urandom(seed) % 400; seed = seed + 1;
            if (i_wsrc) begin
                i_k = 1 + $urandom(seed) % (3 << sp); seed = seed + 1;
                i_mmode = $urandom(seed) % 2; seed = seed + 1;
                i_rmax = ($urandom(seed) % 2) && i_mmode; seed = seed + 1;
                i_amax = !i_rmax && ($urandom(seed) % 2); seed = seed + 1;
            end else begin
                i_k = 1 + $urandom(seed) % 4; seed = seed + 1;
                i_mmode = 0; i_rmax = 0;
                i_amax = $urandom(seed) % 2; seed = seed + 1;
            end
            maxrows = i_mmode ? (i_tiles * per_round * W) : (i_tiles * per_round * W * IL);
            i_nout = 1 + $urandom(seed) % maxrows; seed = seed + 1;
        end
    endtask

    // ---- checks ---------------------------------------------------------------------
    integer cyc = 0, errors = 0, n_wr_r = 0, n_wr_m = 0, n_wr_a = 0, n_mx = 0;
    integer first_ov_m = -1, first_ov_a = -1;
    // event queues: result writes (group, addr, mask, data), maxima words, argmax states, scale reads
    reg [AW+W+W*32+8-1:0] qm [0:65535];
    reg [AW+W+W*32+8-1:0] qa [0:65535];
    reg [AW+W+W*32-1:0] xr [0:4095];
    reg [AW+W+W*32-1:0] xm [0:4095];
    reg [AW+W+W*32-1:0] xa [0:4095];
    reg [NW+32:0] amr [0:4095];
    reg [NW+32:0] amm [0:4095];
    reg [NW+32:0] ama [0:4095];
    reg [AW+8-1:0] scm [0:65535];
    reg [AW+8-1:0] sca [0:65535];
    integer nqm = 0, nqa = 0, nxr = 0, nxm = 0, nxa = 0, namr = 0, namm = 0, nama = 0, nscm = 0, nsca = 0;
    reg [NW+32:0] lam_r = 0, lam_m = 0, lam_a = 0;

    task automatic fail(input [8*48-1:0] what, input integer grp);
        begin
            if (errors < 20) $display("FAIL cyc=%0d %0s group=%0d", cyc, what, grp);
            errors = errors + 1;
        end
    endtask

    always @(negedge clk) if (rst_n) begin
        cyc = cyc + 1;
        // unpruned new engine == original, every port
        if ({u_ready, u_idle, u_wrom_re, u_wrom_addr, u_scale_re, u_scale_gre, u_scale_addr, u_kv_re, u_kv_addr,
             u_x_re, u_x_addr, u_ov, u_o_we, u_o_addr, u_o_mask, u_o_data, u_am_idx, u_am_val, u_am_any,
             u_mx_we, u_mx_addr, u_mx_mask, u_mx_data, u_progress, u_fault} !==
            {r_ready, r_idle, r_wrom_re, r_wrom_addr, r_scale_re, r_scale_gre, r_scale_addr, r_kv_re, r_kv_addr,
             r_x_re, r_x_addr, r_ov, r_o_we, r_o_addr, r_o_mask, r_o_data, r_am_idx, r_am_val, r_am_any,
             r_mx_we, r_mx_addr, r_mx_mask, r_mx_data, r_progress, r_fault}) fail("unpruned != original", -1);
        // pruned monolithic == original on requests, writes, progress
        if ({m_ready, m_wrom_re, m_wrom_addr, m_scale_re, m_scale_gre, m_kv_re, m_kv_addr, m_x_re, m_x_addr,
             m_ov, m_o_we, m_o_mask, m_progress, m_fault} !==
            {r_ready, r_wrom_re, r_wrom_addr, r_scale_re, r_scale_gre, r_kv_re, r_kv_addr, r_x_re, r_x_addr,
             r_ov, r_o_we, r_o_mask, r_progress, r_fault}) fail("pruned != original (requests/writes)", -1);
        for (g = 0; g < GT; g = g + 1) begin
            if (r_scale_gre[g] && m_scale_addr[g*AW +: AW] !== r_scale_addr[g*AW +: AW]) fail("pruned scale_addr", g);
            if (r_o_we[g] && ({m_o_addr[g*AW +: AW], m_o_data[g*W*32 +: W*32]} !==
                              {r_o_addr[g*AW +: AW], r_o_data[g*W*32 +: W*32]})) fail("pruned result word", g);
        end
        // array vs pruned monolithic
        if (ZERO_WIRE) begin
            if ({a_ready, a_idle, a_scale_re, a_scale_gre, a_ov, a_o_we, a_o_mask, a_am_idx, a_am_val, a_am_any,
                 a_mx_we, a_mx_addr, a_mx_mask, a_mx_data, a_progress, a_fault} !==
                {m_ready, m_idle, m_scale_re, m_scale_gre, m_ov, m_o_we, m_o_mask, m_am_idx, m_am_val, m_am_any,
                 m_mx_we, m_mx_addr, m_mx_mask, m_mx_data, m_progress, m_fault}) fail("array != pruned (ports)", -1);
            for (g = 0; g < NXC && g < GT; g = g + 1)
                if (m_x_re[g] !== a_x_re[g] || (m_x_re[g] && m_x_addr[g*AW +: AW] !== a_x_addr[g*AW +: AW]))
                    fail("array x chunk port", g);
            for (g = 0; g < NT; g = g + 1)
                if ((|a_t_rom_ce[g*CB +: CB]) !== m_wrom_re ||
                    (m_wrom_re && ({a_t_rom_ce[g*CB +: CB] == 2'b10 ? 12'd1 : 12'd0, a_t_rom_addr[g*12 +: 12]} !==
                                   {m_wrom_addr[23:12], m_wrom_addr[11:0]})))
                    fail("array tile ROM request", g);
            for (g = 0; g < GT; g = g + 1) begin
                if (m_kv_re && a_t_kv_addr[g*AW +: AW] !== m_kv_addr[g*AW +: AW]) fail("array tile KV request", g);
                if (m_scale_gre[g] && a_scale_addr[g*AW +: AW] !== m_scale_addr[g*AW +: AW]) fail("array scale_addr", g);
                if (m_o_we[g] && ({a_o_addr[g*AW +: AW], a_o_data[g*W*32 +: W*32]} !==
                                  {m_o_addr[g*AW +: AW], m_o_data[g*W*32 +: W*32]})) fail("array result word", g);
            end
        end
        if (a_fault || m_fault || r_fault) fail("a fault was raised", -1);
        // event streams
        if (m_ov && first_ov_m < 0) first_ov_m = cyc;
        if (a_ov && first_ov_a < 0) first_ov_a = cyc;
        for (g = 0; g < GT; g = g + 1) begin
            if (m_o_we[g]) begin qm[nqm] = {g[7:0], m_o_addr[g*AW +: AW], m_o_mask[g*W +: W], m_o_data[g*W*32 +: W*32]}; nqm = nqm + 1; end
            if (a_o_we[g]) begin qa[nqa] = {g[7:0], a_o_addr[g*AW +: AW], a_o_mask[g*W +: W], a_o_data[g*W*32 +: W*32]}; nqa = nqa + 1; end
            if (m_scale_gre[g]) begin scm[nscm] = {g[7:0], m_scale_addr[g*AW +: AW]}; nscm = nscm + 1; end
            if (a_scale_gre[g]) begin sca[nsca] = {g[7:0], a_scale_addr[g*AW +: AW]}; nsca = nsca + 1; end
        end
        if (r_mx_we) begin xr[nxr] = {r_mx_addr, r_mx_mask, r_mx_data}; nxr = nxr + 1; end
        if (m_mx_we) begin xm[nxm] = {m_mx_addr, m_mx_mask, m_mx_data}; nxm = nxm + 1; end
        if (a_mx_we) begin xa[nxa] = {a_mx_addr, a_mx_mask, a_mx_data}; nxa = nxa + 1; end
        if ({r_am_any, r_am_idx, r_am_val} !== lam_r) begin lam_r = {r_am_any, r_am_idx, r_am_val}; amr[namr] = lam_r; namr = namr + 1; end
        if ({m_am_any, m_am_idx, m_am_val} !== lam_m) begin lam_m = {m_am_any, m_am_idx, m_am_val}; amm[namm] = lam_m; namm = namm + 1; end
        if ({a_am_any, a_am_idx, a_am_val} !== lam_a) begin lam_a = {a_am_any, a_am_idx, a_am_val}; ama[nama] = lam_a; nama = nama + 1; end
    end

    integer n, busy;
    initial begin
        seed = SEED;
        go = 0; new_op;
        repeat (4) @(posedge clk);
        rst_n = 1;
        ops = 0;
        while (ops < NOPS) begin
            @(posedge clk);
            #0.1;
            if (go && r_ready) begin ops = ops + 1; new_op; end
            go = (($urandom(seed) % 8) != 0); seed = seed + 1;
        end
        go = 0;
        busy = 0;
        while (!(r_idle && m_idle && a_idle) || busy < 8) begin
            @(posedge clk); busy = (r_idle && m_idle && a_idle) ? busy + 1 : 0;
        end
        repeat (4) @(posedge clk);
        if (nqm != nqa) begin $display("FAIL result write count mono=%0d array=%0d", nqm, nqa); errors = errors + 1; end
        for (n = 0; n < nqm && n < nqa; n = n + 1)
            if (qm[n] !== qa[n]) begin
                if (errors < 20) $display("FAIL result write event %0d differs", n);
                errors = errors + 1;
            end
        if (nscm != nsca) begin $display("FAIL scale read count mono=%0d array=%0d", nscm, nsca); errors = errors + 1; end
        for (n = 0; n < nscm && n < nsca; n = n + 1)
            if (scm[n] !== sca[n]) begin if (errors < 20) $display("FAIL scale read event %0d", n); errors = errors + 1; end
        if (nxr != nxm || nxm != nxa) begin $display("FAIL maxima counts %0d %0d %0d", nxr, nxm, nxa); errors = errors + 1; end
        for (n = 0; n < nxr && n < nxm && n < nxa; n = n + 1)
            if (xr[n] !== xm[n] || xm[n] !== xa[n]) begin if (errors < 20) $display("FAIL maxima event %0d", n); errors = errors + 1; end
        if (namr != namm || namm != nama) begin $display("FAIL argmax change counts %0d %0d %0d", namr, namm, nama); errors = errors + 1; end
        for (n = 0; n < namr && n < namm && n < nama; n = n + 1)
            if (amr[n] !== amm[n] || amm[n] !== ama[n]) begin if (errors < 20) $display("FAIL argmax event %0d", n); errors = errors + 1; end
        if (first_ov_a - first_ov_m != XD + ORD) begin
            $display("FAIL first result at +%0d, expected +%0d", first_ov_a - first_ov_m, XD + ORD); errors = errors + 1;
        end
        if (errors == 0 && nqm > 0)
            $display("PASS GT=%0d TG=%0d SMIN=%0d SMAX=%0d TCUT=%0d BD=%0d XVM=%0d NWS=%0d TWS=%0d ORD=%0d ops=%0d cycles=%0d result_writes=%0d maxima=%0d argmax_changes=%0d scale_reads=%0d latency_added=%0d",
                     GT, TG, SMIN, SMAX, TCUT, BD, XVM, NWS, TWS, ORD, ops, cyc, nqm, nxm, namm, nscm, first_ov_a - first_ov_m);
        else $display("FAIL errors=%0d writes=%0d", errors, nqm);
        $finish;
    end
endmodule
