`timescale 1ns/1ps
// PRODUCTION-SHAPE x delivery gate of the distributed x slices (el1014-qwen-dvm-build.log): 48 columns x 16 rows =
// 768 tiles (TG 4, GT 3,072), SMIN 7 / SMAX 11 (NXL 512 quad lines), against the x network of ot_qwen_me_array_w12
// (its spine ot_qwen_me_spine_w12 at GT 3,072: the issue loop, x chunk port and quad-line network, fed by a central
// read of XVMR edges).  No tile arithmetic here (the full-array exactness at reduced shape is tb_qwen_me_dvm_w12):
// every tile's x pins are compared, every edge on which the reference network delivers a fresh x word to that tile,
// with the dvm fabric's pins 3 + DX - XVMR edges later: the BF16 operand the tile multiplies (RNE16(x) when the op rounds,
// x[31:16] when not) must equal the slice's 16 bits and the low half must be 0.
// Ops: the decoded production TP8 weight ops (results/arch/qwen_tp8_native_dispatch_1014 actual_* die0: qkv k 8 S 512
// xbase 4096; o_proj k 2 S 256 xbase 50672 rounds 3; gate_up k 32 S 128 xbase 4096; down k 6 S 256 xbase 55280
// rounds 3; all round 1) in layer order, each with its own x image, x written by the SU (64 lanes, from xbase, as the
// producer's vector stream) or, for o_proj, by the attention return (16 lanes); then NRAND random production-form ops.
// Mutants (must FAIL): HEAD_MUT 3 (wrong station), LEAF_MUT 2 (swapped tile), HEAD_MUT 4 (stale epoch), TAP_MUT 1
// (no rounding).
module tb_qfd_xdvm_prod;
    parameter integer NCOL = 48, NH = 8, TG = 4;
    parameter integer GT = NCOL * 2 * NH * TG;
    parameter integer SMIN = 7, SMAX = 11, TCUT = 3;
    parameter integer LEAF_FILL_PIPE = 0, LEAF_BANK_PIPE = 0, REQ_PIPE = 0;
    parameter integer HB = 3, DX = 10 + LEAF_BANK_PIPE + REQ_PIPE + (NH/2-1)*LEAF_FILL_PIPE, FILL_LEAD = 2 + (NH/2-1)*LEAF_FILL_PIPE, TIDM = 1, XOFF = 3, XVMR = 12;
    parameter integer NLAYER = 2, NRAND = 6, SEED = 1, GAP = 4;
    parameter integer NATIVE_AFFINE=0,STATIC_SCHEDULE=0,NW=18;
    parameter integer TAP_MUT = 0, LEAF_MUT = 0, HEAD_MUT = 0;
    localparam integer W = 16, IL = 8, AW = 24, XCW = 12;
    localparam integer NT = GT / TG, NXC = 1 << SMAX, NXL = NXC / TG;
    localparam integer BDR = HB + NH + 3 + XVMR;
    localparam integer IBW = 3 * NW + 13 * AW + 13;
    localparam integer DOFF = 3 + DX - XVMR;      // dvm minus ref (r3: + the tap's 3 stages on the go path)

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
    function automatic [31:0] xv(input [31:0] addr, input integer n);
        reg [31:0] h;
        begin
            h = mix(addr + 32'd4099 * n, 0, 32'h4444);
            xv = {h[31], 8'd124 + {5'd0, h[26:24] % 3'd6}, h[22:0]};
            if (h[30:28] == 3'd0) xv[15:0] = 16'h8000;
        end
    endfunction
    function automatic [15:0] opnd(input [31:0] x, input rnd);
        reg cy;
        begin
            cy = (x[15:0] > 16'h8000) || (x[15:0] == 16'h8000 && x[16]);
            opnd = rnd ? x[31:16] + {15'd0, cy} : x[31:16];
        end
    endfunction

    reg              go;
    reg [NW-1:0]     i_nout, i_tiles, i_k;
    reg              i_round, i_amax;
    reg [AW-1:0]     i_wbase, i_ts, i_ks, i_js, i_xbase, i_xks, i_xcs, i_wcs, i_obase, i_ots, i_ojs, i_mbase;
    reg [2:0]        i_jsh;
    reg [3:0]        i_split;
    wire [IBW-1:0] ib = {i_nout, i_tiles, i_k, 1'b0, i_wbase, i_ts, i_ks, i_js, i_xbase, i_xks, {AW{1'b0}}, i_xcs,
                         i_jsh, i_split, i_wcs, i_round, i_obase, i_ots, i_ojs, 1'b0, 1'b1, i_amax, 1'b0, i_mbase};

    // ---- reference: the spine of ot_qwen_me_array_w12 (issue loop + x network) ----
    wire r_ready, r_idle, r_fault;
    wire [NXC-1:0] r_x_re;
    wire [NXC*AW-1:0] r_x_addr;
    wire [NXC*32-1:0] r_x_q;
    reg  [NXC*32-1:0] r_x_q0;
    wire [NXC*32-1:0] r_xl_d;
    wire              r_tgo;
    ot_qwen_me_spine_w12 #(.W(W), .IL(IL), .AW(AW), .NW(NW), .GT(GT), .TG(TG), .SMIN(SMIN), .SMAX(SMAX), .TCUT(TCUT),
        .BD(BDR), .XVM(XVMR)) u_ref (
        .clk(clk), .rst_n(rst_n), .go(go), .ready(r_ready), .idle(r_idle),
        .i_nout(i_nout), .i_tiles(i_tiles), .i_k(i_k), .i_wsrc(1'b0), .i_wbase(i_wbase), .i_ts(i_ts), .i_ks(i_ks),
        .i_js(i_js), .i_xbase(i_xbase), .i_xks(i_xks), .i_xjs({AW{1'b0}}), .i_xcs(i_xcs), .i_jsh(i_jsh),
        .i_split(i_split), .i_wcs(i_wcs), .i_round(i_round), .i_obase(i_obase), .i_ots(i_ots), .i_ojs(i_ojs),
        .i_mmode(1'b0), .i_oen(1'b1), .i_amax(i_amax), .i_rmax(1'b0), .i_mbase(i_mbase),
        .scale_re(), .scale_gre(), .scale_addr(), .scale_q({(GT >> SMIN)*W*16{1'b0}}),
        .x_re(r_x_re), .x_addr(r_x_addr), .x_q(r_x_q), .wrom_re(), .wrom_addr(), .kv_re(),
        .tgo(r_tgo), .tb(), .xl_d(r_xl_d), .t_lvl({(GT >> TCUT)*W*32{1'b0}}), .fab_fault(1'b0),
        .ov(), .o_we(), .o_addr(), .o_mask(), .o_data(), .am_idx(), .am_val(), .am_any(),
        .mx_we(), .mx_addr(), .mx_mask(), .mx_data(), .progress(), .fault(r_fault));
    ot_hdc_delay #(.W(NXC*32), .D(XVMR)) u_xvm (.clk(clk), .rst_n(rst_n), .d(r_x_q0), .q(r_x_q));
    integer n_acc = 0, g;
    reg rnd_op [0:255];
    always @(posedge clk) begin
        for (g = 0; g < NXC; g = g + 1)
            if (r_x_re[g]) r_x_q0[32*g +: 32] <= xv(r_x_addr[g*AW +: AW], n_acc - 1);
    end
    always @(posedge clk) if (rst_n && go && r_ready) n_acc <= n_acc + 1;
    // a fresh x word reaches the tiles 1 + BDR - 1 edges after the x read strobe (read, XVMR, network BD - XVM - 1);
    // carry the op's round flag along
    wire xr_any = |r_x_re;
    reg  cur_rnd;
    always @(posedge clk) if (rst_n && go && r_ready) cur_rnd <= i_round;
    wire fresh, fresh_rnd;
    ot_hdc_delay #(.W(2), .D(BDR), .RESET(1)) u_fr (.clk(clk), .rst_n(rst_n), .d({cur_rnd, xr_any}), .q({fresh_rnd, fresh}));

    // ---- dvm fabric ----
    reg              xpf_v, xpf_round, sw_v, aw_v;
    reg [AW-1:0]     xpf_xbase, sw_a, aw_a;
    reg [XCW-1:0]    xpf_xcs, xpf_xks;
    reg [3:0]        xpf_split;
    reg [NW-1:0]     xpf_k;
    reg [63:0]       sw_m;
    reg [64*32-1:0]  sw_d;
    reg [15:0]       aw_m;
    reg [16*32-1:0]  aw_d;
    wire [NT-1:0]    d_go;
    wire [NT*TG*32-1:0] d_xl;
    wire             d_x_fault;
    ot_qfd_xdvm_fabric #(.AW(AW), .NW(NW), .XCW(XCW), .IL(IL), .NCOL(NCOL), .NH(NH), .TG(TG), .SMIN(SMIN), .SMAX(SMAX),
        .HB(HB), .LEAF_FILL_PIPE(LEAF_FILL_PIPE), .LEAF_BANK_PIPE(LEAF_BANK_PIPE), .REQ_PIPE(REQ_PIPE), .DX(DX), .FILL_LEAD(FILL_LEAD), .TIDM(TIDM), .XOFF(XOFF), .NATIVE_AFFINE(NATIVE_AFFINE),.STATIC_SCHEDULE(STATIC_SCHEDULE),.TAP_MUT(TAP_MUT), .LEAF_MUT(LEAF_MUT),
        .HEAD_MUT(HEAD_MUT)) u_fab (
        .clk(clk), .rst_n(rst_n), .go_acc(go && r_ready), .ib(ib),
        .xpf_v(xpf_v), .xpf_xbase(xpf_xbase), .xpf_xcs(xpf_xcs), .xpf_xks(xpf_xks), .xpf_split(xpf_split),
        .xpf_k(xpf_k), .xpf_round(xpf_round), .sw_v(sw_v), .sw_a(sw_a), .sw_m(sw_m), .sw_d(sw_d),
        .aw_v(aw_v), .aw_a(aw_a), .aw_m(aw_m), .aw_d(aw_d), .go_t(d_go), .ib_t(), .xl_t(d_xl), .x_fault(d_x_fault));

    // ---- compare: reference delayed by XVMR - DX (it is that much later than the dvm pins) ----
    // here DX < XVMR: the dvm pins are EARLIER; delay the dvm pins by XVMR - DX instead
    localparam integer DL = (DOFF < 0) ? -DOFF : DOFF;
    wire [NT*TG*32-1:0] d_xl_al;
    wire [NXC*32-1:0]   r_xl_al;
    wire                fr_al, frr_al;
    generate if (DOFF < 0) begin : g_dl
        ot_hdc_delay #(.W(NT*TG*32), .D(DL)) u_d (.clk(clk), .rst_n(rst_n), .d(d_xl), .q(d_xl_al));
        assign r_xl_al = r_xl_d; assign fr_al = fresh; assign frr_al = fresh_rnd;
    end else begin : g_rl
        ot_hdc_delay #(.W(NXC*32), .D(DL)) u_r (.clk(clk), .rst_n(rst_n), .d(r_xl_d), .q(r_xl_al));
        ot_hdc_delay #(.W(2), .D(DL), .RESET(1)) u_f (.clk(clk), .rst_n(rst_n), .d({fresh_rnd, fresh}), .q({frr_al, fr_al}));
        assign d_xl_al = d_xl;
    end endgenerate
    integer cyc = 0, errors = 0, checks = 0, t, e, ln;
    integer distinct_max = 0;
    always @(negedge clk) if (rst_n) begin
        cyc = cyc + 1;
        if (r_fault) begin if (errors < 20) $display("FAIL cyc=%0d reference fault", cyc); errors = errors + 1; end
        if (d_x_fault) begin if (errors < 20) $display("FAIL cyc=%0d x_fault", cyc); errors = errors + 1; end
        if (fr_al) begin
            for (t = 0; t < NT; t = t + 1) begin
                ln = t % NXL;
                for (e = 0; e < TG; e = e + 1) begin
                    checks = checks + 1;
                    if (d_xl_al[(t*TG + e)*32 +: 32] !== {opnd(r_xl_al[(ln*TG + e)*32 +: 32], frr_al), 16'h0000}) begin
                        if (errors < 20) $display("FAIL cyc=%0d tile %0d element %0d ref %h (operand %h) dvm %h", cyc, t, e,
                            r_xl_al[(ln*TG + e)*32 +: 32], opnd(r_xl_al[(ln*TG + e)*32 +: 32], frr_al),
                            d_xl_al[(t*TG + e)*32 +: 32]);
                        errors = errors + 1;
                    end
                end
            end
        end
    end

    // ---- stimulus ----
    integer seed, ops, a, lo, hi, l, step, n, kk, sp, xc, xk, rr, nl;
    task automatic issue(input integer k, input integer split, input integer xbase, input integer rounds,
                         input integer nout, input integer use_ar, input integer rnd);
        begin
            sp = split; lo = xbase; hi = xbase + ((1 << split) - 1) * k + (k - 1) + 1;
            repeat (HB + 8) @(posedge clk); #0.1;
            xpf_v = 1; xpf_xbase = xbase; xpf_xcs = k; xpf_xks = 1; xpf_split = split; xpf_k = k; xpf_round = rnd;
            @(posedge clk); #0.1; xpf_v = 0;
            repeat (2) @(posedge clk); #0.1;      // sequencer rule: first write >= 3 edges after the XPF
            a = lo;
            while (a < hi) begin
                sw_v = 0; aw_v = 0;
                if (use_ar) begin
                    aw_v = 1; aw_a = a; aw_m = 16'd0;
                    for (l = 0; l < 16; l = l + 1) begin aw_m[l] = (a + l < hi); aw_d[32*l +: 32] = xv(a + l, ops); end
                    a = a + 16;
                end else begin
                    sw_v = 1; sw_a = a; sw_m = 64'd0;
                    for (l = 0; l < 64; l = l + 1) begin sw_m[l] = (a + l < hi); sw_d[32*l +: 32] = xv(a + l, ops); end
                    a = a + 64;
                end
                @(posedge clk); #0.1;
            end
            sw_v = 0; aw_v = 0;
            repeat (GAP) @(posedge clk); #0.1;
            while (!r_ready) begin @(posedge clk); #0.1; end
            i_k = k; i_split = split; i_xbase = xbase; i_xcs = k; i_xks = 1; i_tiles = rounds; i_nout = nout; i_round = rnd;
            i_wbase = 0; i_ts = k * IL; i_ks = IL; i_js = 1; i_jsh = 0; i_wcs = 0; i_obase = 0; i_ots = IL; i_ojs = 1;
            i_amax = 0; i_mbase = 0;
            go = 1; @(posedge clk); #0.1; go = 0;
            ops = ops + 1;
        end
    endtask
    initial begin
        seed = SEED; go = 0; xpf_v = 0; sw_v = 0; aw_v = 0; ops = 0;
        repeat (4) @(posedge clk); rst_n = 1; repeat (4) @(posedge clk); #0.1;
        for (nl = 0; nl < NLAYER; nl = nl + 1) begin
            issue(8, 9, 4096, 1, 768, 0, 1);         // qkv
            issue(2, 8, 50672, 3, 4096, 1, 1);       // o_proj, x from the attention return
            issue(32, 7, 4096, 1, 3072, 0, 1);       // gate_up
            issue(6, 8, 55280, 3, 4096, 0, 1);       // down
        end
        for (n = 0; n < NRAND; n = n + 1) begin
            sp = SMIN + ($urandom(seed) % (SMAX - SMIN + 1)); seed = seed + 1;
            kk = NATIVE_AFFINE ? ((($urandom(seed)%3)==0)?2:(($urandom(seed)%2)==0)?6:8) : 1 + ($urandom(seed) % 16); seed = seed + 1;
            rr = 1 + ($urandom(seed) % 2); seed = seed + 1;
            issue(kk, sp, $urandom(seed) % 60000, rr, 1 + ($urandom(seed + 1) % 4096), $urandom(seed + 2) % 2, $urandom(seed + 3) % 2);
            seed = seed + 4;
        end
        while (!r_idle) @(posedge clk);
        repeat (BDR + 40) @(posedge clk);
        if (errors == 0 && checks > 0)
            $display("PASS xdvm_prod NCOL=%0d NH=%0d tiles=%0d GT=%0d SMIN=%0d SMAX=%0d NXL=%0d HB=%0d DX=%0d XOFF=%0d XVMR=%0d ops=%0d cycles=%0d element_checks=%0d dvm_minus_ref_edges=%0d",
                NCOL, NH, NT, GT, SMIN, SMAX, NXL, HB, DX, XOFF, XVMR, ops, cyc, checks, DOFF);
        else $display("FAIL errors=%0d checks=%0d", errors, checks);
        $finish;
    end
endmodule
