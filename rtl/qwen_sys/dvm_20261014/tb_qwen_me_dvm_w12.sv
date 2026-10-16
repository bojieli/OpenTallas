`timescale 1ns/1ps
// Exactness gate of the distributed x slices (el1014-qwen-dvm-build.log):
//   ref  ot_qwen_me_array_w12 (central x network) fed by a vector-memory model with XVMR edges of x read latency,
//        BD_ref = HB + NH + 3 + XVMR (head row HB, plain column head 1, corridor NH, tile IREG 1, plus the read);
//   dvm  ot_qwen_me_array_dvm_w12: the same tiles / tree / spine, x from ot_qfd_xs_tap -> head row -> ot_qfd_xhead +
//        ot_qfd_xs_leaf slices -> TDM on the corridor -> ot_qfd_xcst stations, BD = 3 + HB + DX + NH + 3 (r3: go / ib
//        pass the tap's three stages with the fill: XD = 3 + DX edges of x path on the instruction broadcast).
// Every op has its OWN x image (value of element a for op n = xv(a + 4099 n): a slice that serves another epoch's
// data, another tile's line or an unrounded operand is visible).  Before op n issues, the bench arms its x range on the
// tap (XPF) and writes the whole range through the SU (64-lane, any alignment) and attention-return (16-lane) ports
// in random chunks with idle edges and out-of-range noise writes; the go follows the last write by GAP edges.
// Checks: (1) result writes, scale reads, maxima and argmax as event sequences dvm == ref, first result exactly
// DX - XVMR edges later; (2) per tile, every cycle the tile's x operand stage is valid (u_me.s3_v), the multiplier
// operand bits s3_x[31:16] of each group dvm == ref; (3) no fault, no x_fault.  DROP = 1 omits one write of op 3: the
// slice must raise x_fault (fail-loud), the run then PASSES only if it did.
// Mutants (must FAIL): TAP_MUT 1 (no rounding), LEAF_MUT 2 (swapped tile), HEAD_MUT 3 (wrong station / line),
// HEAD_MUT 4 (other epoch = stale buffer), TAP_MUT 5 (stale write ownership: the previous epoch stays armed).
module tb_qwen_me_dvm_w12;
    parameter integer NCOL = 2, NH = 8, TG = 4;
    parameter integer GT = NCOL * 2 * NH * TG;
    parameter integer SMIN = 4, SMAX = 7, TCUT = 3;
    parameter integer LEAF_READ_PIN_PIPE = 0;
    parameter integer LEAF_FILL_PIPE = 0, HEAD_LOCAL_RST = 0, HEAD_ONWARD_REG = 0;
    parameter integer HB = 3, DX = 10 + LEAF_READ_PIN_PIPE + 3 * LEAF_FILL_PIPE, FILL_LEAD = 2 + 3 * LEAF_FILL_PIPE, TIDM = 1, XOFF = 3, XVMR = 12;
    parameter integer NOPS = 40, SEED = 1, GAP = 4, DROP = 0;
    // REUSE: 1 in REUSE ops starts INSIDE the previous op's x range (address reuse, as production: qkv / gate_up share
    // xbase 4096, o / down re-read the attention / act outputs): the previous epoch is still being read while this
    // op's producer writes the same addresses, so a tap that leaves the old epoch armed (TAP_MUT 5) faults or corrupts.
    parameter integer REUSE = 3;
    parameter integer TAP_MUT = 0, LEAF_MUT = 0, HEAD_MUT = 0;
    parameter integer MAXCYC = 2000000;
    localparam integer W = 16, IL = 8, AW = 24, NW = 16, XCW = 12;
    localparam integer NT = GT / TG, NXC = 1 << SMAX;
    localparam integer BDR = HB + NH + 3 + XVMR;
    localparam integer XD  = 3 + DX;                 // the x path's edges on the instruction broadcast
    localparam integer BDD = HB + XD + NH + 3;
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
    // x element value of op n: FP32 in [2^-3, 2^3), random low half with RNE ties (low half 0x8000) on 1 in 8
    function automatic [31:0] xv(input [31:0] addr, input integer n);
        reg [31:0] h, a;
        begin
            a = addr + 32'd4099 * n;
            h = mix(a, 0, 32'h4444);
            xv = {h[31], 8'd124 + {5'd0, h[26:24] % 3'd6}, h[22:0]};
            if (h[30:28] == 3'd0) xv[15:0] = 16'h8000;
        end
    endfunction

    // ---- instruction ----
    reg              go;
    reg [NW-1:0]     i_nout, i_tiles, i_k;
    reg              i_wsrc, i_round, i_mmode, i_oen, i_amax, i_rmax;
    reg [AW-1:0]     i_wbase, i_ts, i_ks, i_js, i_xbase, i_xks, i_xjs, i_xcs, i_wcs, i_obase, i_ots, i_ojs, i_mbase;
    reg [2:0]        i_jsh;
    reg [3:0]        i_split;

    // ---- reference ----
    wire r_ready, r_idle, r_scale_re, r_ov, r_am_any, r_mx_we, r_fault;
    wire [GT-1:0] r_scale_gre, r_o_we;
    wire [GT*AW-1:0] r_scale_addr, r_o_addr, r_t_kv_addr;
    reg  [GT*W*16-1:0] r_scale_q;
    wire [NXC-1:0] r_x_re;
    wire [NXC*AW-1:0] r_x_addr;
    wire [NXC*32-1:0] r_x_q;
    reg  [NXC*32-1:0] r_x_q0;
    wire [NT*CB-1:0] r_t_rom_ce;
    wire [NT*12-1:0] r_t_rom_addr;
    reg  [NT*2*CB*266-1:0] r_t_rom_rd;
    wire [NT-1:0] r_t_kv_re;
    wire [GT*W-1:0] r_o_mask;
    wire [GT*W*32-1:0] r_o_data;
    wire [NW-1:0] r_am_idx; wire [31:0] r_am_val;
    wire [AW-1:0] r_mx_addr; wire [W-1:0] r_mx_mask; wire [W*32-1:0] r_mx_data; wire [15:0] r_progress;
    ot_qwen_me_array_w12 #(.W(W), .IL(IL), .AW(AW), .NW(NW), .GT(GT), .TG(TG), .SMIN(SMIN), .SMAX(SMAX), .TCUT(TCUT),
        .BD(BDR), .XVM(XVMR), .CODE_BANKS(CB), .KV_LOCAL(0)) u_ref (
        .clk(clk), .rst_n(rst_n), .go(go), .ready(r_ready), .idle(r_idle),
        .i_nout(i_nout), .i_tiles(i_tiles), .i_k(i_k), .i_wsrc(i_wsrc), .i_wbase(i_wbase), .i_ts(i_ts),
        .i_ks(i_ks), .i_js(i_js), .i_xbase(i_xbase), .i_xks(i_xks), .i_xjs(i_xjs), .i_xcs(i_xcs), .i_jsh(i_jsh),
        .i_split(i_split), .i_wcs(i_wcs), .i_round(i_round), .i_obase(i_obase), .i_ots(i_ots), .i_ojs(i_ojs),
        .i_mmode(i_mmode), .i_oen(i_oen), .i_amax(i_amax), .i_rmax(i_rmax), .i_mbase(i_mbase),
        .scale_re(r_scale_re), .scale_gre(r_scale_gre), .scale_addr(r_scale_addr), .scale_q(r_scale_q),
        .x_re(r_x_re), .x_addr(r_x_addr), .x_q(r_x_q),
        .t_rom_ce(r_t_rom_ce), .t_rom_addr(r_t_rom_addr), .t_rom_rd(r_t_rom_rd),
        .t_kv_re(r_t_kv_re), .t_kv_addr(r_t_kv_addr), .t_kv_q({GT*W*32{1'b0}}),
        .ov(r_ov), .o_we(r_o_we), .o_addr(r_o_addr), .o_mask(r_o_mask), .o_data(r_o_data),
        .am_idx(r_am_idx), .am_val(r_am_val), .am_any(r_am_any), .mx_we(r_mx_we), .mx_addr(r_mx_addr),
        .mx_mask(r_mx_mask), .mx_data(r_mx_data), .progress(r_progress), .fault(r_fault));
    // the central read: one registered read + XVMR edges
    ot_hdc_delay #(.W(NXC*32), .D(XVMR)) u_xvm (.clk(clk), .rst_n(rst_n), .d(r_x_q0), .q(r_x_q));

    // ---- dvm ----
    reg              xpf_v, xpf_round, sw_v, aw_v;
    reg [AW-1:0]     xpf_xbase, sw_a, aw_a;
    reg [XCW-1:0]    xpf_xcs, xpf_xks;
    reg [3:0]        xpf_split;
    reg [NW-1:0]     xpf_k;
    reg [63:0]       sw_m;
    reg [64*32-1:0]  sw_d;
    reg [15:0]       aw_m;
    reg [16*32-1:0]  aw_d;
    wire d_ready, d_idle, d_scale_re, d_ov, d_am_any, d_mx_we, d_fault, d_x_fault;
    wire [GT-1:0] d_scale_gre, d_o_we;
    wire [GT*AW-1:0] d_scale_addr, d_o_addr;
    reg  [GT*W*16-1:0] d_scale_q;
    wire [NT*CB-1:0] d_t_rom_ce;
    wire [NT*12-1:0] d_t_rom_addr;
    reg  [NT*2*CB*266-1:0] d_t_rom_rd;
    wire [GT*W-1:0] d_o_mask;
    wire [GT*W*32-1:0] d_o_data;
    wire [NW-1:0] d_am_idx; wire [31:0] d_am_val;
    wire [AW-1:0] d_mx_addr; wire [W-1:0] d_mx_mask; wire [W*32-1:0] d_mx_data; wire [15:0] d_progress;
    wire [NT*TG*32-1:0] d_tile_xl;
    ot_qwen_me_array_dvm_w12 #(.W(W), .IL(IL), .AW(AW), .NW(NW), .XCW(XCW), .NCOL(NCOL), .NH(NH), .TG(TG), .GT(GT),
        .SMIN(SMIN), .SMAX(SMAX), .TCUT(TCUT), .HB(HB), .LEAF_READ_PIN_PIPE(LEAF_READ_PIN_PIPE), .LEAF_FILL_PIPE(LEAF_FILL_PIPE), .HEAD_LOCAL_RST(HEAD_LOCAL_RST),
        .HEAD_ONWARD_REG(HEAD_ONWARD_REG), .DX(DX), .FILL_LEAD(FILL_LEAD), .TIDM(TIDM), .XOFF(XOFF), .CODE_BANKS(CB),
        .TAP_MUT(TAP_MUT), .LEAF_MUT(LEAF_MUT), .HEAD_MUT(HEAD_MUT)) u_dvm (
        .clk(clk), .rst_n(rst_n), .go(go), .ready(d_ready), .idle(d_idle),
        .i_nout(i_nout), .i_tiles(i_tiles), .i_k(i_k), .i_wsrc(i_wsrc), .i_wbase(i_wbase), .i_ts(i_ts),
        .i_ks(i_ks), .i_js(i_js), .i_xbase(i_xbase), .i_xks(i_xks), .i_xjs(i_xjs), .i_xcs(i_xcs), .i_jsh(i_jsh),
        .i_split(i_split), .i_wcs(i_wcs), .i_round(i_round), .i_obase(i_obase), .i_ots(i_ots), .i_ojs(i_ojs),
        .i_mmode(i_mmode), .i_oen(i_oen), .i_amax(i_amax), .i_rmax(i_rmax), .i_mbase(i_mbase),
        .scale_re(d_scale_re), .scale_gre(d_scale_gre), .scale_addr(d_scale_addr), .scale_q(d_scale_q),
        .xpf_v(xpf_v), .xpf_xbase(xpf_xbase), .xpf_xcs(xpf_xcs), .xpf_xks(xpf_xks), .xpf_split(xpf_split),
        .xpf_k(xpf_k), .xpf_round(xpf_round), .sw_v(sw_v), .sw_a(sw_a), .sw_m(sw_m), .sw_d(sw_d),
        .aw_v(aw_v), .aw_a(aw_a), .aw_m(aw_m), .aw_d(aw_d),
        .t_rom_ce(d_t_rom_ce), .t_rom_addr(d_t_rom_addr), .t_rom_rd(d_t_rom_rd),
        .ov(d_ov), .o_we(d_o_we), .o_addr(d_o_addr), .o_mask(d_o_mask), .o_data(d_o_data),
        .am_idx(d_am_idx), .am_val(d_am_val), .am_any(d_am_any), .mx_we(d_mx_we), .mx_addr(d_mx_addr),
        .mx_mask(d_mx_mask), .mx_data(d_mx_data), .progress(d_progress), .fault(d_fault), .x_fault(d_x_fault),
        .tile_xl(d_tile_xl));

    // ---- memories ----
    integer g, l, b, pc, n_acc = 0;
    always @(posedge clk) begin
        for (g = 0; g < GT; g = g + 1) begin
            if (r_scale_gre[g]) for (l = 0; l < W; l = l + 1) r_scale_q[16*(g*W+l) +: 16] <= scl(r_scale_addr[g*AW +: AW], l);
            if (d_scale_gre[g]) for (l = 0; l < W; l = l + 1) d_scale_q[16*(g*W+l) +: 16] <= scl(d_scale_addr[g*AW +: AW], l);
        end
        for (g = 0; g < NT; g = g + 1)
            for (b = 0; b < CB; b = b + 1)
                for (pc = 0; pc < 2; pc = pc + 1) begin
                    if (r_t_rom_ce[g*CB + b]) begin
                        r_t_rom_rd[((g*2 + pc)*CB + b)*266 +: 266] <= 266'd0;
                        for (l = 0; l < 2 * W; l = l + 1)
                            r_t_rom_rd[((g*2 + pc)*CB + b)*266 + 8*l +: 8] <= rom(b * 4096 + r_t_rom_addr[g*12 +: 12], (g * TG + 2*pc) * W + l);
                    end
                    if (d_t_rom_ce[g*CB + b]) begin
                        d_t_rom_rd[((g*2 + pc)*CB + b)*266 +: 266] <= 266'd0;
                        for (l = 0; l < 2 * W; l = l + 1)
                            d_t_rom_rd[((g*2 + pc)*CB + b)*266 + 8*l +: 8] <= rom(b * 4096 + d_t_rom_addr[g*12 +: 12], (g * TG + 2*pc) * W + l);
                    end
                end
        // the central x read serves the image of the op issuing now (accepted gos so far - 1)
        for (g = 0; g < NXC; g = g + 1)
            if (r_x_re[g]) r_x_q0[32*g +: 32] <= xv(r_x_addr[g*AW +: AW], n_acc - 1);
    end
    always @(posedge clk) if (rst_n && go && r_ready && d_ready) n_acc <= n_acc + 1;

    // ---- per-tile operand check: s3_x[31:16] of every group, every cycle s3_v ----
    integer cyc = 0, errors = 0, opnd_checks = 0;
    genvar tt;
    // the two arrays run XD - XVMR edges apart: compare the operand streams through a delay of the earlier one
    localparam integer DOFF = (XD >= XVMR) ? XD - XVMR : XVMR - XD;
    generate for (tt = 0; tt < NT; tt = tt + 1) begin : g_op
        wire          rv = u_ref.g_tile[tt].u_t.u_me.s3_v;
        wire          dv = u_dvm.g_tile[tt].u_t.u_me.s3_v;
        wire [TG*32-1:0] rx = u_ref.g_tile[tt].u_t.u_me.s3_x;
        wire [TG*32-1:0] dx = u_dvm.g_tile[tt].u_t.u_me.s3_x;
        wire          ev, lv;
        wire [TG*32-1:0] ex, lx;
        if (XD >= XVMR) begin : g_rl
            ot_hdc_delay #(.W(1), .D(DOFF), .RESET(1)) u_v (.clk(clk), .rst_n(rst_n), .d(rv), .q(ev));
            ot_hdc_delay #(.W(TG*32), .D(DOFF)) u_x (.clk(clk), .rst_n(rst_n), .d(rx), .q(ex));
            assign lv = dv; assign lx = dx;
        end else begin : g_dl
            ot_hdc_delay #(.W(1), .D(DOFF), .RESET(1)) u_v (.clk(clk), .rst_n(rst_n), .d(dv), .q(lv));
            ot_hdc_delay #(.W(TG*32), .D(DOFF)) u_x (.clk(clk), .rst_n(rst_n), .d(dx), .q(lx));
            assign ev = rv; assign ex = rx;
        end
        // ev/ex: reference stream aligned to lv/lx: dvm stream
        integer gg;
        always @(negedge clk) if (rst_n) begin
            if (ev !== lv) begin
                if (errors < 20) $display("FAIL cyc=%0d tile %0d operand valid ref=%b dvm=%b", cyc, tt, ev, lv);
                errors = errors + 1;
            end else if (ev) begin
                opnd_checks = opnd_checks + 1;
                for (gg = 0; gg < TG; gg = gg + 1)
                    if (ex[32*gg + 16 +: 16] !== lx[32*gg + 16 +: 16]) begin
                        if (errors < 20) $display("FAIL cyc=%0d tile %0d group %0d operand ref=%h dvm=%h", cyc, tt, gg,
                            ex[32*gg + 16 +: 16], lx[32*gg + 16 +: 16]);
                        errors = errors + 1;
                    end
            end
        end
    end endgenerate

    // ---- event streams ----
    reg [AW+W+W*32+8-1:0] qr [0:65535];
    reg [AW+W+W*32+8-1:0] qd [0:65535];
    reg [AW+8-1:0] scr [0:65535];
    reg [AW+8-1:0] scd [0:65535];
    reg [AW+W+W*32-1:0] xr [0:4095];
    reg [AW+W+W*32-1:0] xd [0:4095];
    reg [NW+32:0] amr [0:4095];
    reg [NW+32:0] amd [0:4095];
    integer nqr = 0, nqd = 0, nscr = 0, nscd = 0, nxr = 0, nxd = 0, namr = 0, namd = 0;
    integer first_ov_r = -1, first_ov_d = -1;
    reg [NW+32:0] lam_r = 0, lam_d = 0;
    reg xf_seen = 0;
    always @(negedge clk) if (rst_n) begin
        cyc = cyc + 1;
        if (cyc > MAXCYC) begin $display("FAIL timeout"); $finish; end
        if (r_fault || d_fault) begin if (errors < 20) $display("FAIL cyc=%0d engine fault ref=%b dvm=%b", cyc, r_fault, d_fault); errors = errors + 1; end
        if (d_x_fault && !xf_seen) begin
            xf_seen = 1;
            if (!DROP) begin $display("FAIL cyc=%0d x_fault raised", cyc); errors = errors + 1; end
            else $display("NOTE cyc=%0d x_fault raised (DROP run: expected)", cyc);
        end
        if (r_ov && first_ov_r < 0) first_ov_r = cyc;
        if (d_ov && first_ov_d < 0) first_ov_d = cyc;
        for (g = 0; g < GT; g = g + 1) begin
            if (r_o_we[g]) begin qr[nqr] = {g[7:0], r_o_addr[g*AW +: AW], r_o_mask[g*W +: W], r_o_data[g*W*32 +: W*32]}; nqr = nqr + 1; end
            if (d_o_we[g]) begin qd[nqd] = {g[7:0], d_o_addr[g*AW +: AW], d_o_mask[g*W +: W], d_o_data[g*W*32 +: W*32]}; nqd = nqd + 1; end
            if (r_scale_gre[g]) begin scr[nscr] = {g[7:0], r_scale_addr[g*AW +: AW]}; nscr = nscr + 1; end
            if (d_scale_gre[g]) begin scd[nscd] = {g[7:0], d_scale_addr[g*AW +: AW]}; nscd = nscd + 1; end
        end
        if (r_mx_we) begin xr[nxr] = {r_mx_addr, r_mx_mask, r_mx_data}; nxr = nxr + 1; end
        if (d_mx_we) begin xd[nxd] = {d_mx_addr, d_mx_mask, d_mx_data}; nxd = nxd + 1; end
        if ({r_am_any, r_am_idx, r_am_val} !== lam_r) begin lam_r = {r_am_any, r_am_idx, r_am_val}; amr[namr] = lam_r; namr = namr + 1; end
        if ({d_am_any, d_am_idx, d_am_val} !== lam_d) begin lam_d = {d_am_any, d_am_idx, d_am_val}; amd[namd] = lam_d; namd = namd + 1; end
    end

    // ---- stimulus ----
    integer seed, ops, sp, kc, mode, xcs, xks, rounds, per_round, maxrows, lo, hi, a, step, nw, nnoise, nxl;
    integer since_go, wl, dropped = 0, fills = 0, sw_beats = 0, aw_beats = 0, dist_lines;
    reg [NW-1:0] o_nout, o_tiles, o_k; reg o_round, o_amax, o_oen;
    reg [AW-1:0] o_wbase, o_ts, o_ks, o_js, o_wcs, o_obase, o_ots, o_ojs, o_mbase, o_xbase;
    reg [2:0] o_jsh; reg [3:0] o_split; reg [AW-1:0] o_xcs, o_xks;
    integer p_lo = -1, p_hi = -1, reused = 0;
    task automatic r(output integer v, input integer m);
        begin v = $urandom(seed) % m; seed = seed + 1; end
    endtask
    // the fabric's tile id map (ot_qfd_xdvm_fabric.tid) and the pooled-pair rule of ot_qfd_xhead: a footprint over 64
    // elements needs N station s and S station NH-1-s on the same quad, i.e. S / TG divides their id difference
    function automatic integer tidb(input integer c, input integer r);
        integer dr, bc, br, lbc, lbr, blk, z, p, i;
        begin
            if (TIDM == 0) tidb = c * 2 * NH + r;
            else begin
                dr = (r < NH) ? NH + r : NH - 1 - (r - NH);
                bc = (NCOL >= 4) ? 4 : NCOL; br = (2 * NH >= 4) ? 4 : 2 * NH;
                lbc = (bc >= 4) ? 2 : (bc >= 2) ? 1 : 0; lbr = (br >= 4) ? 2 : (br >= 2) ? 1 : 0;
                blk = (c / bc) * (2 * NH / br) + dr / br;
                z = 0; p = 0;
                for (i = 0; i < 2; i = i + 1) begin
                    if (i < lbc) begin z = z | (((c % bc) >> i) & 1) << p; p = p + 1; end
                    if (i < lbr) begin z = z | (((dr % br) >> i) & 1) << p; p = p + 1; end
                end
                tidb = bc * br * blk + z;
            end
        end
    endfunction
    function automatic integer pool_ok(input integer spl);
        integer c, s2, qm;
        begin
            pool_ok = (spl >= 2);
            qm = (1 << spl) / TG;
            for (c = 0; c < NCOL; c = c + 1)
                for (s2 = 0; s2 < NH; s2 = s2 + 1)
                    if ((tidb(c, s2) % qm) != (tidb(c, NH + NH - 1 - s2) % qm)) pool_ok = 0;
        end
    endfunction
    integer pooled = 0;
    task automatic gen_op;
        integer t0, t1;
        begin
            r(t0, SMAX - SMIN + 1); sp = SMIN + t0;
            r(mode, 4);
            if (mode == 0) begin            // production, any alignment, kc <= 16
                r(t0, 16); kc = 1 + t0; xks = 1; xcs = kc; r(t1, 60000); o_xbase = t1;
            end else if (mode == 1) begin   // production gate_up / qkv shapes, 64-aligned
                r(t0, 3); kc = (t0 == 0) ? 32 : (t0 == 1) ? 24 : 8; xks = 1; xcs = kc; r(t1, 900); o_xbase = 64 * t1;
            end else if (mode == 2) begin   // production down / o shapes at the production offset 48
                r(t0, 2); kc = (t0 == 0) ? 6 : 2; xks = 1; xcs = kc; r(t1, 900); o_xbase = 64 * t1 + 48;
            end else begin                  // general strides inside a two-beat window
                r(t0, 2); xks = 1 + t0; r(t0, 4); kc = 1 + t0; r(t0, 3); xcs = kc * xks + t0; r(t1, 60000); o_xbase = t1;
            end
            if (kc > 16 && (o_xbase % 64) != 0) o_xbase = o_xbase - (o_xbase % 64);
            // a footprint over 64 (TG * kc) is pooled over a tile pair: pick a split whose pairs share their quad
            if (TG * kc > 64) begin
                while (!pool_ok(sp) && sp > SMIN) sp = sp - 1;
                if (!pool_ok(sp)) begin kc = 16; xcs = kc; end      // no poolable split: a footprint of 64
                else pooled = pooled + 1;
            end
            // address reuse: start inside the previous op's range (any-alignment shapes only, kc <= 16)
            r(t0, REUSE);
            if (REUSE > 0 && t0 == 0 && p_lo >= 0 && mode != 1 && kc <= 16) begin
                r(t1, (p_hi - p_lo < 8) ? p_hi - p_lo : 8); o_xbase = p_lo + t1; reused = reused + 1;
            end
            per_round = GT >> sp;
            o_split = sp; o_k = kc; o_xcs = xcs; o_xks = xks;
            r(t0, 3); o_tiles = 1 + t0;
            r(t0, 4); o_jsh = t0; r(t0, 3); o_js = t0; r(t0, 40); o_ks = 1 + t0; r(t0, 200); o_ts = 1 + t0;
            r(t0, 4000); o_wbase = t0; r(t0, 3000); o_wcs = t0;
            r(t0, 2); o_round = t0; r(t0, 500); o_obase = t0; r(t0, 9); o_ots = t0; r(t0, 3); o_ojs = t0;
            r(t0, 5); o_oen = (t0 != 0); r(t0, 400); o_mbase = t0; r(t0, 2); o_amax = t0;
            maxrows = o_tiles * per_round * W * IL;
            r(t0, maxrows); o_nout = 1 + t0;
            lo = o_xbase; hi = o_xbase + ((1 << sp) - 1) * xcs + (kc - 1) * xks + 1;
            p_lo = lo; p_hi = hi;
        end
    endtask
    task automatic idle_writes;
        begin sw_v = 0; aw_v = 0; xpf_v = 0; end
    endtask

    integer n, busy, k2, gapw, t2;
    initial begin
        seed = SEED; go = 0; idle_writes;
        i_wsrc = 0; i_xjs = 0; i_mmode = 0; i_rmax = 0;
        repeat (4) @(posedge clk);
        rst_n = 1;
        repeat (4) @(posedge clk);
        ops = 0;
        while (ops < NOPS) begin
            gen_op;
            // XPF: the epoch of this op was last used two ops ago; wait until it has finished everywhere
            repeat (HB + 8) @(posedge clk); #0.1;
            xpf_v = 1; xpf_xbase = o_xbase; xpf_xcs = xcs; xpf_xks = xks; xpf_split = sp; xpf_k = kc; xpf_round = o_round;
            @(posedge clk); #0.1; xpf_v = 0;
            repeat (2) @(posedge clk); #0.1;      // sequencer rule: first write >= 3 edges after the XPF
            // the range, in chunks, through both ports, with idle edges and noise
            a = lo; fills = fills + 1;
            while (a < hi) begin
                idle_writes;
                r(t2, 6);
                if (t2 == 0) begin
                    // idle edge
                end else if (t2 == 1) begin
                    sw_v = 1; sw_a = 24'h100000 + a; sw_m = {64{1'b1}};          // noise outside every range
                    for (l = 0; l < 64; l = l + 1) sw_d[32*l +: 32] = 32'hDEAD0000 + l;
                end else if (t2 == 2) begin
                    aw_v = 1; aw_a = a; aw_m = 16'd0; step = 16;
                    for (l = 0; l < 16; l = l + 1) begin
                        aw_m[l] = (a + l < hi); aw_d[32*l +: 32] = xv(a + l, ops);
                    end
                    if (!(DROP && ops == 3 && a == lo)) a = a + step; else begin aw_v = 0; a = a + step; dropped = dropped + 1; end
                    aw_beats = aw_beats + 1;
                end else begin
                    sw_v = 1; sw_a = a; sw_m = 0;
                    r(step, 64); step = (step < 8) ? 64 : 1 + step;      // mostly full beats, sometimes short
                    for (l = 0; l < 64; l = l + 1) begin
                        sw_m[l] = (l < step) && (a + l < hi); sw_d[32*l +: 32] = xv(a + l, ops);
                    end
                    if (DROP && ops == 3 && a == lo) begin sw_v = 0; dropped = dropped + 1; end
                    a = a + step;
                    sw_beats = sw_beats + 1;
                end
                @(posedge clk); #0.1;
            end
            idle_writes;
            // go: GAP edges after the last write, both engines ready
            repeat (GAP) @(posedge clk); #0.1;
            while (!(r_ready && d_ready && (!o_amax || (r_idle && d_idle)))) begin @(posedge clk); #0.1; end
            i_nout = o_nout; i_tiles = o_tiles; i_k = o_k; i_wbase = o_wbase; i_ts = o_ts; i_ks = o_ks; i_js = o_js;
            i_xbase = o_xbase; i_xks = o_xks; i_xcs = o_xcs; i_jsh = o_jsh; i_split = o_split; i_wcs = o_wcs;
            i_round = o_round; i_obase = o_obase; i_ots = o_ots; i_ojs = o_ojs; i_oen = o_oen; i_amax = o_amax;
            i_mbase = o_mbase;
            go = 1;
            @(posedge clk); #0.1;
            go = 0;
            ops = ops + 1;
        end
        busy = 0;
        while (!(r_idle && d_idle) || busy < 8) begin @(posedge clk); busy = (r_idle && d_idle) ? busy + 1 : 0; end
        repeat (8) @(posedge clk);
        if (nqr != nqd) begin $display("FAIL result write count ref=%0d dvm=%0d", nqr, nqd); errors = errors + 1; end
        for (n = 0; n < nqr && n < nqd; n = n + 1)
            if (qr[n] !== qd[n]) begin if (errors < 20) $display("FAIL result write event %0d differs", n); errors = errors + 1; end
        if (nscr != nscd) begin $display("FAIL scale read count ref=%0d dvm=%0d", nscr, nscd); errors = errors + 1; end
        for (n = 0; n < nscr && n < nscd; n = n + 1)
            if (scr[n] !== scd[n]) begin if (errors < 20) $display("FAIL scale read event %0d", n); errors = errors + 1; end
        if (nxr != nxd) begin $display("FAIL maxima count %0d %0d", nxr, nxd); errors = errors + 1; end
        for (n = 0; n < nxr && n < nxd; n = n + 1)
            if (xr[n] !== xd[n]) begin if (errors < 20) $display("FAIL maxima event %0d", n); errors = errors + 1; end
        if (namr != namd) begin $display("FAIL argmax change count %0d %0d", namr, namd); errors = errors + 1; end
        for (n = 0; n < namr && n < namd; n = n + 1)
            if (amr[n] !== amd[n]) begin if (errors < 20) $display("FAIL argmax event %0d", n); errors = errors + 1; end
        if (first_ov_d - first_ov_r != XD - XVMR) begin
            $display("FAIL first result dvm - ref = %0d, expected XD - XVMR = %0d", first_ov_d - first_ov_r, XD - XVMR);
            errors = errors + 1;
        end
        if (DROP) begin
            if (xf_seen) $display("PASS drop-detect NCOL=%0d NH=%0d GT=%0d dropped=%0d: x_fault raised (no silent stale read)", NCOL, NH, GT, dropped);
            else $display("FAIL drop-detect: a write was dropped and x_fault was NOT raised");
        end else if (errors == 0 && nqr > 0 && opnd_checks > 0)
            $display("PASS dvm NCOL=%0d NH=%0d GT=%0d SMIN=%0d SMAX=%0d HB=%0d DX=%0d XOFF=%0d XVMR=%0d GAP=%0d ops=%0d cycles=%0d result_writes=%0d operand_checks=%0d fills=%0d sw_beats=%0d aw_beats=%0d bd_ref=%0d bd_dvm=%0d first_result_delta=%0d reused=%0d pooled=%0d",
                NCOL, NH, GT, SMIN, SMAX, HB, DX, XOFF, XVMR, GAP, ops, cyc, nqr, opnd_checks, fills, sw_beats, aw_beats, BDR, BDD, first_ov_d - first_ov_r, reused, pooled);
        else $display("FAIL errors=%0d writes=%0d operand_checks=%0d reused=%0d", errors, nqr, opnd_checks, reused);
        $finish;
    end
endmodule
