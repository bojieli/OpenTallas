`timescale 1ns/1ps
// Compute-die x network exactness bench (el1014-qwen-split-compute.log, contract v1 x-line fix).
//   ref  ot_qwen_me_array_w12 (reference: tile t reads quad line t mod NXL, all lines every cycle)
//   die  ot_qwen_me_array_xdie_w12 (generated from the reference; tiles read the die x network ot_qwen_xdie_net:
//        one 4-line bundle per physical column, 1-of-4 select by the tile's row in its block)
// Same hash ROM / scale / KV / x memories served to each by its own addresses, random back-to-back ops (dense and
// KV-sourced) at splits SMIN..SMAX.  Every output port of the two arrays is compared on every cycle, and every
// memory request.  XMUT = 1 (tile 1 takes a wrong line of its column bundle) must FAIL.
module tb_qwen_xdie_array;
    parameter integer GT = 512, TG = 4, SMIN = 3, SMAX = 7, TCUT = 5, NBC = 4;
    parameter integer NOPS = 200, SEED = 1, XMUT = 0, MUTANT = 0;
    parameter integer W = 16;
    localparam integer IL = 8, AW = 24, NW = 16, BAW = 12;
    localparam integer NT = GT / TG, NXC = 1 << SMAX;
    localparam integer CB = 8192 >> BAW;
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


    reg              go;
    reg [NW-1:0]     i_nout, i_tiles, i_k;
    reg              i_wsrc, i_round, i_mmode, i_oen, i_amax, i_rmax;
    reg [AW-1:0]     i_wbase, i_ts, i_ks, i_js, i_xbase, i_xks, i_xjs, i_xcs, i_wcs, i_obase, i_ots, i_ojs, i_mbase;
    reg [2:0]        i_jsh;
    reg [3:0]        i_split;
`define AP(P) \
    wire P``_ready, P``_idle, P``_scale_re, P``_ov, P``_am_any, P``_mx_we, P``_fault; \
    wire [GT-1:0] P``_scale_gre, P``_o_we; \
    wire [GT*AW-1:0] P``_scale_addr, P``_o_addr, P``_t_kv_addr; \
    reg  [GT*W*16-1:0] P``_scale_q; \
    wire [NXC-1:0] P``_x_re; wire [NXC*AW-1:0] P``_x_addr; reg [NXC*32-1:0] P``_x_q; \
    wire [NT*CB-1:0] P``_t_rom_ce; wire [NT*12-1:0] P``_t_rom_addr; reg [NT*2*CB*266-1:0] P``_t_rom_rd; \
    wire [NT-1:0] P``_t_kv_re; reg [GT*W*32-1:0] P``_t_kv_q; \
    wire [GT*W-1:0] P``_o_mask; wire [GT*W*32-1:0] P``_o_data; \
    wire [NW-1:0] P``_am_idx; wire [31:0] P``_am_val; \
    wire [AW-1:0] P``_mx_addr; wire [W-1:0] P``_mx_mask; wire [W*32-1:0] P``_mx_data; wire [15:0] P``_progress;
    `AP(a)
    `AP(d)
`define AC(P) \
        .clk(clk), .rst_n(rst_n), .go(go), .ready(P``_ready), .idle(P``_idle), \
        .i_nout(i_nout), .i_tiles(i_tiles), .i_k(i_k), .i_wsrc(i_wsrc), .i_wbase(i_wbase), .i_ts(i_ts), \
        .i_ks(i_ks), .i_js(i_js), .i_xbase(i_xbase), .i_xks(i_xks), .i_xjs(i_xjs), .i_xcs(i_xcs), .i_jsh(i_jsh), \
        .i_split(i_split), .i_wcs(i_wcs), .i_round(i_round), .i_obase(i_obase), .i_ots(i_ots), .i_ojs(i_ojs), \
        .i_mmode(i_mmode), .i_oen(i_oen), .i_amax(i_amax), .i_rmax(i_rmax), .i_mbase(i_mbase), \
        .scale_re(P``_scale_re), .scale_gre(P``_scale_gre), .scale_addr(P``_scale_addr), .scale_q(P``_scale_q), \
        .x_re(P``_x_re), .x_addr(P``_x_addr), .x_q(P``_x_q), \
        .t_rom_ce(P``_t_rom_ce), .t_rom_addr(P``_t_rom_addr), .t_rom_rd(P``_t_rom_rd), \
        .t_kv_re(P``_t_kv_re), .t_kv_addr(P``_t_kv_addr), .t_kv_q(P``_t_kv_q), \
        .ov(P``_ov), .o_we(P``_o_we), .o_addr(P``_o_addr), .o_mask(P``_o_mask), .o_data(P``_o_data), \
        .am_idx(P``_am_idx), .am_val(P``_am_val), .am_any(P``_am_any), .mx_we(P``_mx_we), .mx_addr(P``_mx_addr), \
        .mx_mask(P``_mx_mask), .mx_data(P``_mx_data), .progress(P``_progress), .fault(P``_fault)
    ot_qwen_me_array_w12 #(.W(W), .IL(IL), .AW(AW), .NW(NW), .GT(GT), .TG(TG), .SMIN(SMIN), .SMAX(SMAX), .TCUT(TCUT),
        .CODE_BANKS(CB), .KV_LOCAL(0), .BAW(BAW)) u_ref (`AC(a));
    ot_qwen_me_array_xdie_w12 #(.NBC(NBC), .XMUT(XMUT), .W(W), .IL(IL), .AW(AW), .NW(NW), .GT(GT), .TG(TG), .SMIN(SMIN), .SMAX(SMAX),
        .TCUT(TCUT), .CODE_BANKS(CB), .KV_LOCAL(0), .BAW(BAW)) u_die (`AC(d));
    integer g, l, b, pc;
`define AM(P) \
        for (g = 0; g < GT; g = g + 1) begin \
            if (P``_scale_gre[g]) for (l = 0; l < W; l = l + 1) P``_scale_q[16*(g*W+l) +: 16] <= scl(P``_scale_addr[g*AW +: AW], l); \
            if (P``_t_kv_re[g / TG]) for (l = 0; l < W; l = l + 1) P``_t_kv_q[32*(g*W+l) +: 32] <= kvw(P``_t_kv_addr[g*AW +: AW], l); \
        end \
        for (g = 0; g < NT; g = g + 1) \
            for (b = 0; b < CB; b = b + 1) \
                if (P``_t_rom_ce[g*CB + b]) \
                    for (pc = 0; pc < 2; pc = pc + 1) begin \
                        P``_t_rom_rd[((g*2 + pc)*CB + b)*266 +: 266] <= 266'd0; \
                        for (l = 0; l < 2 * W; l = l + 1) \
                            P``_t_rom_rd[((g*2 + pc)*CB + b)*266 + 8*l +: 8] <= rom(b * (1 << BAW) + P``_t_rom_addr[g*12 +: 12], (g * TG + 2*pc) * W + l); \
                    end \
        for (g = 0; g < NXC; g = g + 1) if (P``_x_re[g]) P``_x_q[32*g +: 32] <= xv(P``_x_addr[g*AW +: AW]);
    always @(posedge clk) begin
        `AM(a)
        `AM(d)
    end
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


    integer cyc = 0, errors = 0, nwr = 0, nscale = 0, nmx = 0;
    parameter integer MAXCYC = 2000000;
    wire [0:0] dummy;
    always @(negedge clk) if (rst_n) begin
        cyc = cyc + 1;
        if ({a_ready, a_idle, a_scale_re, a_ov, a_am_any, a_mx_we, a_fault} !== {d_ready, d_idle, d_scale_re, d_ov, d_am_any, d_mx_we, d_fault}
            || a_scale_gre !== d_scale_gre || a_scale_addr !== d_scale_addr || a_x_re !== d_x_re || a_x_addr !== d_x_addr
            || a_t_rom_ce !== d_t_rom_ce || a_t_rom_addr !== d_t_rom_addr || a_t_kv_re !== d_t_kv_re || a_t_kv_addr !== d_t_kv_addr
            || a_o_we !== d_o_we || a_o_addr !== d_o_addr || a_o_mask !== d_o_mask || a_o_data !== d_o_data
            || a_am_idx !== d_am_idx || a_am_val !== d_am_val || a_mx_addr !== d_mx_addr || a_mx_mask !== d_mx_mask
            || a_mx_data !== d_mx_data || a_progress !== d_progress) begin
            if (errors < 10) $display("FAIL cyc=%0d ref/die port mismatch (o_we %0d/%0d ov %b/%b)", cyc, $countones(a_o_we), $countones(d_o_we), a_ov, d_ov);
            errors = errors + 1;
        end
        if (a_ov) nwr = nwr + $countones(a_o_we);
        if (a_scale_re) nscale = nscale + 1;
        if (a_mx_we) nmx = nmx + 1;
        if (a_fault) begin $display("FAIL reference fault cyc=%0d", cyc); errors = errors + 1; end
        if (cyc > MAXCYC) begin $display("FAIL timeout"); $finish; end
    end
    initial begin
        seed = SEED; ops = 0; go = 0;
        i_nout = 0; i_tiles = 0; i_k = 0; i_wsrc = 0; i_round = 0; i_mmode = 0; i_oen = 0; i_amax = 0; i_rmax = 0;
        i_wbase = 0; i_ts = 0; i_ks = 0; i_js = 0; i_xbase = 0; i_xks = 0; i_xjs = 0; i_xcs = 0; i_wcs = 0;
        i_obase = 0; i_ots = 0; i_ojs = 0; i_mbase = 0; i_jsh = 0; i_split = SMIN;
        new_op;
        repeat (4) @(posedge clk);
        rst_n = 1;
        while (ops < NOPS) begin
            @(posedge clk);
            #0.1;
            if (go) begin ops = ops + 1; new_op; end
            go = (($urandom(seed) % 8) != 0) && (!i_amax || (a_idle && d_idle)) && a_ready && d_ready;
            seed = seed + 1;
        end
        go = 0;
        repeat (20) @(posedge clk);
        while (!(a_idle && d_idle)) @(posedge clk);
        repeat (200) @(posedge clk);
        if (errors == 0 && nwr > 0)
            $display("PASS xdie GT=%0d TG=%0d SMAX=%0d NBC=%0d tiles=%0d ops=%0d cycles=%0d result_group_writes=%0d scale_reads=%0d maxima=%0d XMUT=%0d",
                     GT, TG, SMAX, NBC, NT, ops, cyc, nwr, nscale, nmx, XMUT);
        else $display("FAIL errors=%0d result_group_writes=%0d XMUT=%0d", errors, nwr, XMUT);
        $finish;
    end
endmodule
