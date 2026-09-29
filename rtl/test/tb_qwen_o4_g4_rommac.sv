`timescale 1ns/1ps
// Cycle equivalence of the banked-macro neighbourhood (ot_qwen_o4_g4_rommac)
// against the unchanged ot_hdc_matvec fed by a flat synchronous ROM.
// Every ROM word is a hash of (bank instance path, address): the test ROM
// below replaces the macro view, and the reference computes the same word
// from the global address. All matvec outputs are compared every cycle.
module ot_rom_4096x266_m8 (
    input  wire clk,
    input  wire ce_in,
    input  wire [11:0] addr_in,
    output reg  [265:0] rd_out
);
    integer id;
    string path;
    integer i;
    initial begin
        path = $sformatf("%m");
        id = 0;
        for (i = 0; i < path.len(); i = i + 1) id = (id * 31 + path[i]) & 32'h7fffffff;
        rd_out = 266'd0;
    end
    function automatic [265:0] word(input integer who, input integer a);
        integer k;
        reg [31:0] h;
        begin
            word = 0;
            for (k = 0; k < 9; k = k + 1) begin
                h = who * 32'h9E3779B1 + a * 32'h85EBCA77 + k * 32'hC2B2AE3D;
                h = h ^ (h >> 15); h = h * 32'h2C1B3C6D; h = h ^ (h >> 12);
                word[32*k +: 32] = h;
            end
        end
    endfunction
    always @(posedge clk) if (ce_in) rd_out <= word(id, addr_in);
endmodule

module tb_qwen_o4_g4_rommac;
    localparam integer G = 4, W = 16, AW = 24, NW = 16, CB = 11, SB = 2;
    reg clk = 0, rst_n = 0, go = 0;
    always #1 clk = ~clk;
    reg [NW-1:0] i_nout, i_tiles, i_k;
    reg [AW-1:0] i_wbase, i_ts, i_ks, i_js, i_xbase, i_xks, i_xjs, i_xcs, i_wcs, i_obase, i_ots, i_ojs, i_mbase;
    reg [3:0] i_split;
    reg i_amax;
    wire d_ready, d_idle, r_ready, r_idle;
    wire d_kv_re, r_kv_re;
    wire [G*AW-1:0] d_kv_addr, r_kv_addr, d_x_addr, r_x_addr, d_o_addr, r_o_addr;
    wire [G-1:0] d_x_re, r_x_re, d_o_we, r_o_we;
    wire d_ov, r_ov, d_am_any, r_am_any, d_mx_we, r_mx_we, d_fault, r_fault;
    wire [G*W-1:0] d_o_mask, r_o_mask;
    wire [G*W*32-1:0] d_o_data, r_o_data;
    wire [NW-1:0] d_am_idx, r_am_idx;
    wire [31:0] d_am_val, r_am_val;
    wire [AW-1:0] d_mx_addr, r_mx_addr;
    wire [W-1:0] d_mx_mask, r_mx_mask;
    wire [W*32-1:0] d_mx_data, r_mx_data;
    wire [15:0] d_prog, r_prog;
    // operand memories shared by both (1-cycle synchronous, deterministic content)
    reg [G*32-1:0] xq_d, xq_r;
    reg [G*W*32-1:0] kvq;
    function automatic [31:0] xval(input [AW-1:0] a);
        // small BF16-exact values: sign, exponent 120..135, 7-bit mantissa
        xval = {a[0], 8'd120 + {4'd0, a[4:1]}, a[11:5], 16'd0};
    endfunction
    integer gi;
    always @(posedge clk) begin
        for (gi = 0; gi < G; gi = gi + 1) begin
            xq_d[32*gi +: 32] <= xval(d_x_addr[gi*AW +: AW]);
            xq_r[32*gi +: 32] <= xval(r_x_addr[gi*AW +: AW]);
        end
        kvq <= 0;
    end

    ot_qwen_o4_g4_rommac #(.CODE_BANKS(CB), .SCALE_BANKS(SB)) dut (
        .clk(clk), .rst_n(rst_n), .go(go), .ready(d_ready), .idle(d_idle),
        .i_nout(i_nout), .i_tiles(i_tiles), .i_k(i_k), .i_wsrc(1'b0),
        .i_wbase(i_wbase), .i_ts(i_ts), .i_ks(i_ks), .i_js(i_js),
        .i_xbase(i_xbase), .i_xks(i_xks), .i_xjs(i_xjs), .i_xcs(i_xcs),
        .i_jsh(3'd0), .i_split(i_split), .i_wcs(i_wcs), .i_round(1'b1),
        .i_obase(i_obase), .i_ots(i_ots), .i_ojs(i_ojs),
        .i_mmode(1'b0), .i_oen(1'b1), .i_amax(i_amax), .i_rmax(1'b0), .i_mbase(i_mbase),
        .kv_re(d_kv_re), .kv_addr(d_kv_addr), .kv_q(kvq),
        .x_re(d_x_re), .x_addr(d_x_addr), .x_q(xq_d),
        .ov(d_ov), .o_we(d_o_we), .o_addr(d_o_addr), .o_mask(d_o_mask), .o_data(d_o_data),
        .am_idx(d_am_idx), .am_val(d_am_val), .am_any(d_am_any),
        .mx_we(d_mx_we), .mx_addr(d_mx_addr), .mx_mask(d_mx_mask), .mx_data(d_mx_data),
        .progress(d_prog), .fault(d_fault));

    // reference: unchanged matvec, flat ROMs computing the banked words from the global address
    wire r_wrom_re, r_scale_re;
    wire [AW-1:0] r_wrom_addr;
    wire [G-1:0] r_scale_gre;
    wire [G*AW-1:0] r_scale_addr;
    reg  [G*W*8-1:0] r_wrom_q;
    reg  [G*W*16-1:0] r_scale_q;
    ot_hdc_matvec #(.W(W), .G(G), .IL(8), .AW(AW), .NW(NW), .INT8_WEIGHT(1), .INT8_SCALE_WCS_BASE(1)) ref_me (
        .clk(clk), .rst_n(rst_n), .go(go), .ready(r_ready), .idle(r_idle),
        .i_nout(i_nout), .i_tiles(i_tiles), .i_k(i_k), .i_wsrc(1'b0),
        .i_wbase(i_wbase), .i_ts(i_ts), .i_ks(i_ks), .i_js(i_js),
        .i_xbase(i_xbase), .i_xks(i_xks), .i_xjs(i_xjs), .i_xcs(i_xcs),
        .i_jsh(3'd0), .i_split(i_split), .i_wcs(i_wcs), .i_round(1'b1),
        .i_obase(i_obase), .i_ots(i_ots), .i_ojs(i_ojs),
        .i_mmode(1'b0), .i_oen(1'b1), .i_amax(i_amax), .i_rmax(1'b0), .i_mbase(i_mbase),
        .wrom_re(r_wrom_re), .wrom_addr(r_wrom_addr), .wrom_q(r_wrom_q),
        .scale_re(r_scale_re), .scale_gre(r_scale_gre), .scale_addr(r_scale_addr), .scale_q(r_scale_q),
        .kv_re(r_kv_re), .kv_addr(r_kv_addr), .kv_q(kvq),
        .x_re(r_x_re), .x_addr(r_x_addr), .x_q(xq_r),
        .ov(r_ov), .o_we(r_o_we), .o_addr(r_o_addr), .o_mask(r_o_mask), .o_data(r_o_data),
        .am_idx(r_am_idx), .am_val(r_am_val), .am_any(r_am_any),
        .mx_we(r_mx_we), .mx_addr(r_mx_addr), .mx_mask(r_mx_mask), .mx_data(r_mx_data),
        .progress(r_prog), .fault(r_fault));

    function automatic integer hpath(input string s);
        integer i;
        begin
            hpath = 0;
            for (i = 0; i < s.len(); i = i + 1) hpath = (hpath * 31 + s[i]) & 32'h7fffffff;
        end
    endfunction
    integer code_id [0:1][0:CB-1];
    integer scale_id [0:G-1][0:SB-1];
    integer p, b, g;
    initial begin
        for (p = 0; p < 2; p = p + 1)
            for (b = 0; b < CB; b = b + 1)
                code_id[p][b] = hpath($sformatf("tb_qwen_o4_g4_rommac.dut.g_pair[%0d].g_bank[%0d].u_rom", p, b));
        for (g = 0; g < G; g = g + 1)
            for (b = 0; b < SB; b = b + 1)
                scale_id[g][b] = hpath($sformatf("tb_qwen_o4_g4_rommac.dut.g_scale.g_grp[%0d].g_bank[%0d].u_rom", g, b));
    end
    // the same word function as the test ROM
    function automatic [265:0] word(input integer who, input integer a);
        integer k;
        reg [31:0] h;
        begin
            word = 0;
            for (k = 0; k < 9; k = k + 1) begin
                h = who * 32'h9E3779B1 + a * 32'h85EBCA77 + k * 32'hC2B2AE3D;
                h = h ^ (h >> 15); h = h * 32'h2C1B3C6D; h = h ^ (h >> 12);
                word[32*k +: 32] = h;
            end
        end
    endfunction
    reg [265:0] tmp;
    always @(posedge clk) begin
        if (r_wrom_re)
            for (p = 0; p < 2; p = p + 1) begin
                tmp = word(code_id[p][r_wrom_addr >> 12], r_wrom_addr & 12'hfff);
                r_wrom_q[256*p +: 256] <= tmp[255:0];
            end
        for (g = 0; g < G; g = g + 1)
            if (r_scale_gre[g]) begin
                tmp = word(scale_id[g][r_scale_addr[g*AW +: AW] >> 12], r_scale_addr[g*AW +: AW] & 12'hfff);
                r_scale_q[256*g +: 256] <= tmp[255:0];
            end
    end

    integer cyc = 0, mism = 0, results = 0, ops = 0;
    always @(posedge clk) if (rst_n) begin
        cyc <= cyc + 1;
        if ({d_ready, d_idle, d_x_re, d_x_addr, d_ov, d_o_we, d_o_addr, d_o_mask, d_o_data,
             d_am_idx, d_am_val, d_am_any, d_mx_we, d_prog, d_fault} !==
            {r_ready, r_idle, r_x_re, r_x_addr, r_ov, r_o_we, r_o_addr, r_o_mask, r_o_data,
             r_am_idx, r_am_val, r_am_any, r_mx_we, r_prog, r_fault}) begin
            mism <= mism + 1;
            if (mism < 5) $display("MISMATCH cycle %0d o_we %b/%b ov %b/%b", cyc, d_o_we, r_o_we, d_ov, r_ov);
        end
        if (r_ov) results <= results + 1;
    end

    task automatic run_op(input integer wbase, input integer tiles, input integer k, input integer split,
                          input integer sbase, input integer amax);
        begin
            @(negedge clk);
            i_nout = G * W * 8; i_tiles = tiles; i_k = k; i_split = split;
            i_wbase = wbase; i_ts = k; i_ks = 1; i_js = 0;
            i_xbase = 64; i_xks = 1; i_xjs = 0; i_xcs = k; i_wcs = sbase;
            i_obase = 0; i_ots = 8; i_ojs = 1; i_mbase = 0; i_amax = amax;
            wait (d_ready && r_ready);
            @(negedge clk); go = 1; @(negedge clk); go = 0;
            ops = ops + 1;
            repeat (tiles * k * 8 + 80) @(negedge clk);
        end
    endtask

    initial begin
        i_nout = 0; i_tiles = 1; i_k = 1; i_split = 0; i_wbase = 0; i_ts = 0; i_ks = 0; i_js = 0;
        i_xbase = 0; i_xks = 0; i_xjs = 0; i_xcs = 0; i_wcs = 0; i_obase = 0; i_ots = 0; i_ojs = 0;
        i_mbase = 0; i_amax = 0;
        repeat (4) @(negedge clk); rst_n = 1;
        run_op(0, 1, 12, 0, 0, 1);            // bank 0
        run_op(4090, 1, 12, 0, 4094, 0);      // crosses code bank 0 -> 1 and scale bank 0 -> 1
        run_op(40950, 2, 10, 1, 8000, 1);     // top bank (10) with a K split and two rounds
        run_op(20000, 1, 30, 2, 100, 0);      // mid banks, split 4
        repeat (40) @(negedge clk);
        if (mism == 0 && results > 0 && ops == 4) $display("PASS rommac equivalence: %0d ops, %0d result cycles, %0d cycles", ops, results, cyc);
        else $display("FAIL rommac equivalence: %0d mismatching cycles, %0d results", mism, results);
        $finish;
    end
endmodule
