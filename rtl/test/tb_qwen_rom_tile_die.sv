// ot_qwen_rom_tile_die glue bench (the W12 tile itself is covered by its ME partition gate): with a bench stub of
// ot_qwen_rom_tile_w12 that exposes its KV write port, check on random landing words that
//   (1) lo == li two cycles later (W and E pin registers),
//   (2) the tile's kvw_* stream == an independently decoded reference ot_qwen_kv_land_merge (NSRC 3) fed the same
//       landing word one cycle later (slot = {col, v, port, loc, isk, ktail, sel, beat}, col matched to tile_id[5:0]),
//   (3) fault rises iff a presented slot was not granted (registered, sticky).
// NEG = 1 expects lo one cycle after li (must fail).
`timescale 1ns/1ps
module ot_qwen_rom_tile_w12 #(parameter integer NW = 18, GT = 6144, SMIN = 6, CODE_BANKS = 10, KV_VB = 262144,
    KV_NH = 4, MEM_EXTRA = 0, ACC_LAT = 5, FAST_ISSUE = 0, KV_PREP = 0, MUL_LAT = 5, TREE_LAT = 3, ROM_PIPE = 0, ROM_ARELAY = 1, ROM_CAP2 = 0,
    LRST = 0, BAW = 12) (
    input wire clk, input wire rst_n, input wire [15:0] tile_id, input wire ib_go, input wire [3*NW+13*24+13-1:0] ib,
    input wire [127:0] xl, output wire [511:0] t_out, output wire t_vout, input wire [511:0] n_a, input wire [511:0] n_b,
    input wire n_va, output wire [511:0] n_y, output wire n_vy, output wire fault,
    input wire kvw_ce, input wire [6:0] kvw_addr, input wire [511:0] kvw_data, input wire [511:0] kvw_mask);
    assign t_out = 0; assign t_vout = 0; assign n_y = 0; assign n_vy = 0; assign fault = 1'b0;
endmodule
module tb_qwen_rom_tile_die;
    parameter integer N = 20000, NEG = 0;
    reg clk = 0, rst_n = 0;
    reg [983:0] li = 0;
    wire [983:0] lo; wire fault;
    localparam [15:0] TID = 16'h0a2b;   // column 0x2b
    ot_qwen_rom_tile_die u (.clk(clk), .rst_n(rst_n), .tile_id(TID), .ib_go(1'b0), .ib({379{1'b0}}), .xl(128'd0), .t_out(),
        .t_vout(), .n_a(512'd0), .n_b(512'd0), .n_va(1'b0), .n_y(), .n_vy(), .fault(fault), .li(li), .lo(lo));
    // reference: decode written independently (field offsets from the slot MSB down)
    reg [983:0] li_d;
    always @(posedge clk) li_d <= li;
    reg [2:0] rv; reg [20:0] rport, rloc; reg [2:0] risk, rkt; reg [5:0] rsel; reg [767:0] rbeat;
    integer s;
    always @(*) for (s = 0; s < 3; s = s + 1) begin
        rbeat[s*256 +: 256] = li_d[s*281 +: 256];
        rsel[s*2 +: 2] = li_d[s*281 + 256 +: 2];
        rkt[s] = li_d[s*281 + 258]; risk[s] = li_d[s*281 + 259];
        rloc[s*7 +: 7] = li_d[s*281 + 260 +: 7]; rport[s*7 +: 7] = li_d[s*281 + 267 +: 7];
        rv[s] = li_d[s*281 + 274] & (li_d[s*281 + 275 +: 6] == TID[5:0]);
    end
    wire rce; wire [6:0] raddr; wire [511:0] rdata, rmask; wire [2:0] rgrant;
    ot_qwen_kv_land_merge #(.NSRC(3)) ref_m (.clk(clk), .rst_n(rst_n), .rr_n(li_d[843 +: 7]), .s_v(rv), .s_port(rport),
        .s_loc(rloc), .s_isk(risk), .s_ktail(rkt), .s_sel(rsel), .s_beat(rbeat), .tail_lm(li_d[850 +: 128]),
        .s_grant(rgrant), .tok_v(1'b0), .tok_loc(7'd0), .tok_data(512'd0), .tok_mask(512'd0),
        .kvw_ce(rce), .kvw_addr(raddr), .kvw_data(rdata), .kvw_mask(rmask));
    reg rf1, rf2;
    always @(posedge clk or negedge rst_n) if (!rst_n) begin rf1 <= 0; rf2 <= 0; end
        else begin rf1 <= rf1 | (|(rv & ~rgrant)); rf2 <= rf1; end
    always #1 clk = ~clk;
    reg [983:0] p1, p2;
    integer i, k, bad = 0, checks = 0, writes = 0, seed = 5;
    initial begin
        repeat (3) @(posedge clk); rst_n = 1;
        for (i = 0; i < N; i = i + 1) begin
            @(negedge clk);
            if (i > 6) begin
                if (lo !== (NEG ? p2 : p1)) bad = bad + 1;
                if (u.kvw_ce !== rce || (rce && (u.kvw_addr !== raddr || u.kvw_data !== rdata || u.kvw_mask !== rmask)))
                    bad = bad + 1;
                if (fault !== rf2) bad = bad + 1;
                checks = checks + 1; writes = writes + rce;
            end
            p2 = p1; p1 = li;
            for (k = 0; k < 984; k = k + 8) li[k +: 8] = $random(seed);
            // steer most slots to this tile's column, few same-word overlaps (sticky fault then tested late)
            for (k = 0; k < 3; k = k + 1) begin
                if (($random(seed) & 3) != 0) li[k*281 + 275 +: 6] = TID[5:0];
                if (i < N - 200) li[k*281 + 260 +: 7] = k;   // distinct words: always granted
            end
        end
        if (bad == 0 && writes > 0) $display("PASS tile_die checks=%0d writes=%0d fault=%0d", checks, writes, fault);
        else $display("FAIL tile_die NEG=%0d: %0d mismatches of %0d checks (writes %0d)", NEG, bad, checks, writes);
        $finish;
    end
endmodule
