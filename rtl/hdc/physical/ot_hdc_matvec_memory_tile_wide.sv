`timescale 1ns/1ps
// Reduced, bank-explicit physical wrapper for the adopted matvec. W is 4
// or a multiple of 8 and G a power of two. This is not the full ot_hdc_memsys:
// ROM depth is 8192, KV/vector depth is 1024, and vector SRAM uses only 32
// of 256 stored bits per independently addressed group.
module ot_hdc_matvec_memory_tile_wide #(
    parameter integer W = 8,
    parameter integer G = 4,
    parameter integer AW = 16,
    parameter integer NW = 8
) (
    input wire clk, rst_n, go,
    output wire ready, idle,
    input wire [NW-1:0] i_nout, i_tiles, i_k,
    input wire i_wsrc,
    input wire [AW-1:0] i_wbase, i_ts, i_ks, i_js,
    input wire [AW-1:0] i_xbase, i_xks, i_xjs, i_xcs,
    input wire [2:0] i_jsh,
    input wire [3:0] i_split,
    input wire [AW-1:0] i_wcs,
    input wire i_round,
    input wire [AW-1:0] i_obase, i_ots, i_ojs,
    input wire i_mmode, i_oen, i_amax, i_rmax,
    input wire [AW-1:0] i_mbase,
    input wire kv_load, x_load,
    input wire [9:0] kv_load_addr, x_load_addr,
    input wire [G*W*32-1:0] kv_load_data,
    input wire [G*32-1:0] x_load_data,
    output reg kv_load_commit, x_load_commit,
    output wire ov,
    output wire [G-1:0] o_we,
    output wire [G*AW-1:0] o_addr,
    output wire [G*W-1:0] o_mask,
    output wire [G*W*32-1:0] o_data,
    output wire [NW-1:0] am_idx,
    output wire [31:0] am_val,
    output wire am_any,
    output wire mx_we,
    output wire [AW-1:0] mx_addr,
    output wire [W-1:0] mx_mask,
    output wire [W*32-1:0] mx_data,
    output wire [15:0] progress,
    output wire fault
);
    localparam integer KR = (W + 7) / 8; // 256-bit KV macro slices per group
    localparam integer KB = (W < 8) ? W*32 : 256;
    localparam integer RR = G * W / 16; // 256-bit ROM data slices
    initial begin
        if ((W != 4 && (W < 8 || W % 8 != 0)) || G < 2 ||
            (G & (G-1)) != 0 || (G*W) % 16 != 0)
            $fatal(1, "wide tile requires W=4 or multiple of 8, G power of two >=2, and G*W multiple of 16");
    end

    wire wrom_re, kv_re;
    wire [AW-1:0] wrom_addr;
    wire [G*AW-1:0] kv_addr, x_addr;
    wire [G-1:0] x_re;
    wire [G*W*16-1:0] wrom_q;
    wire [G*W*32-1:0] kv_q;
    wire [G*32-1:0] x_q;

    // One accepted whole-word load per cycle. Each bank takes its own slice
    // of the data and all banks write on the next rising edge. Commit pulses
    // after that write edge; a consumer must wait for commit before reading
    // the loaded address. KV and X can load concurrently.
    reg kv_load_q, x_load_q;
    reg [9:0] kv_load_addr_q, x_load_addr_q;
    reg [G*W*32-1:0] kv_load_data_q;
    reg [G*32-1:0] x_load_data_q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            kv_load_q <= 1'b0;
            x_load_q <= 1'b0;
            kv_load_commit <= 1'b0;
            x_load_commit <= 1'b0;
        end else begin
            kv_load_q <= kv_load;
            x_load_q <= x_load;
            kv_load_commit <= kv_load_q;
            x_load_commit <= x_load_q;
        end
    end
    always @(posedge clk) begin
        kv_load_addr_q <= kv_load_addr;
        x_load_addr_q <= x_load_addr;
        kv_load_data_q <= kv_load_data;
        x_load_data_q <= x_load_data;
    end

    ot_hdc_matvec #(.W(W), .G(G), .IL(8), .AW(AW), .NW(NW)) u_me (
        .clk(clk), .rst_n(rst_n), .go(go), .ready(ready), .idle(idle),
        .i_nout(i_nout), .i_tiles(i_tiles), .i_k(i_k), .i_wsrc(i_wsrc),
        .i_wbase(i_wbase), .i_ts(i_ts), .i_ks(i_ks), .i_js(i_js),
        .i_xbase(i_xbase), .i_xks(i_xks), .i_xjs(i_xjs), .i_xcs(i_xcs),
        .i_jsh(i_jsh), .i_split(i_split), .i_wcs(i_wcs), .i_round(i_round),
        .i_obase(i_obase), .i_ots(i_ots), .i_ojs(i_ojs),
        .i_mmode(i_mmode), .i_oen(i_oen), .i_amax(i_amax), .i_rmax(i_rmax),
        .i_mbase(i_mbase), .wrom_re(wrom_re), .wrom_addr(wrom_addr),
        .wrom_q(wrom_q), .kv_re(kv_re), .kv_addr(kv_addr), .kv_q(kv_q),
        .x_re(x_re), .x_addr(x_addr), .x_q(x_q),
        .ov(ov), .o_we(o_we), .o_addr(o_addr), .o_mask(o_mask),
        .o_data(o_data), .am_idx(am_idx), .am_val(am_val), .am_any(am_any),
        .mx_we(mx_we), .mx_addr(mx_addr), .mx_mask(mx_mask),
        .mx_data(mx_data), .progress(progress), .fault(fault)
    );

    wire rom_ce = wrom_re && (wrom_addr[AW-1:13] == 0);
    reg rom_valid;
    always @(posedge clk) if (wrom_re) rom_valid <= rom_ce;
    genvar r, g, k;
    generate for (r = 0; r < RR; r = r + 1) begin : g_rom
        wire [265:0] codeword;
        wire [255:0] data;
        wire corrected, uncorrectable;
        ot_rom_8192x266_m8 u_rom (
            .clk(clk), .ce_in(rom_ce), .addr_in(wrom_addr[12:0]),
            .rd_out(codeword));
        ot_rom_secded_dec #(.K(256)) u_ecc (
            .cw(codeword), .data(data),
            .corrected(corrected), .uncorrectable(uncorrectable));
        assign wrom_q[r*256 +: 256] = rom_valid ? data : 256'd0;
    end endgenerate

    generate for (g = 0; g < G; g = g + 1) begin : g_bank
        wire [255:0] x_word;
        ot_sram_1r1w_1024x256_m2_r2c2 u_x (
            .clk(clk), .r_ce_in(x_re[g]),
            .r_addr_in(x_addr[g*AW +: 10]), .rd_out(x_word),
            .w_ce_in(x_load_q), .w_addr_in(x_load_addr_q),
            .wd_in({224'd0, x_load_data_q[g*32 +: 32]}),
            .w_mask_in({256{1'b1}}),
            .rr_en(2'b00), .rr_addr(18'd0),
            .cr_en(2'b00), .cr_sel(16'd0));
        assign x_q[g*32 +: 32] = x_word[31:0];
        for (k = 0; k < KR; k = k + 1) begin : g_kv
            wire [255:0] kv_word;
            ot_sram_1r1w_1024x256_m2_r2c2 u_kv (
                .clk(clk), .r_ce_in(kv_re),
                .r_addr_in(kv_addr[g*AW +: 10]),
                .rd_out(kv_word),
                .w_ce_in(kv_load_q), .w_addr_in(kv_load_addr_q),
                .wd_in({{(256-KB){1'b0}},
                        kv_load_data_q[g*W*32+k*256 +: KB]}),
                .w_mask_in({256{1'b1}}),
                .rr_en(2'b00), .rr_addr(18'd0),
                .cr_en(2'b00), .cr_sel(16'd0));
            assign kv_q[g*W*32+k*256 +: KB] = kv_word[KB-1:0];
        end
    end endgenerate
endmodule
