`timescale 1ns/1ps
// Reduced physical tile of the adopted ot_hdc_matvec. The instruction and
// result interface is unchanged; W=4, G=2 selects eight real MAC lanes.
// Memory contract: one 8192x266 weight ROM (256 data + SECDED), two replicated
// 1024x256 KV SRAM read banks, and two replicated 1024x256 vector SRAM read
// banks. Each SRAM replica receives the same whole-word load. A 32-bit vector
// element occupies the low 32 bits of its 256-bit word. Unused capacity and
// high address bits are deliberate for this reduced tile and are NOT a full
// ot_hdc_memsys implementation.
module ot_hdc_matvec_memory_tile (
    input wire clk, rst_n, go,
    output wire ready, idle,
    input wire [7:0] i_nout, i_tiles, i_k,
    input wire i_wsrc,
    input wire [15:0] i_wbase, i_ts, i_ks, i_js,
    input wire [15:0] i_xbase, i_xks, i_xjs, i_xcs,
    input wire [2:0] i_jsh,
    input wire [3:0] i_split,
    input wire [15:0] i_wcs,
    input wire i_round,
    input wire [15:0] i_obase, i_ots, i_ojs,
    input wire i_mmode, i_oen, i_amax, i_rmax,
    input wire [15:0] i_mbase,
    input wire kv_load, x_load,
    input wire [9:0] kv_load_addr, x_load_addr,
    input wire [255:0] kv_load_data, x_load_data,
    output reg kv_load_commit, x_load_commit,
    output wire ov,
    output wire [1:0] o_we,
    output wire [31:0] o_addr,
    output wire [7:0] o_mask,
    output wire [255:0] o_data,
    output wire [7:0] am_idx,
    output wire [31:0] am_val,
    output wire am_any,
    output wire mx_we,
    output wire [15:0] mx_addr,
    output wire [3:0] mx_mask,
    output wire [127:0] mx_data,
    output wire [15:0] progress,
    output wire fault
);
    wire wrom_re, kv_re;
    wire [15:0] wrom_addr;
    wire [31:0] kv_addr, x_addr;
    wire [1:0] x_re;
    wire [127:0] wrom_q;
    wire [255:0] kv_q;
    wire [63:0] x_q;

    // The ingress stage accepts one whole-word load per bank each cycle.
    // SRAM writes occur at the following rising edge. A producer must wait
    // for the corresponding commit pulse before reading the loaded address.
    reg kv_load_q, x_load_q;
    reg [9:0] kv_load_addr_q, x_load_addr_q;
    reg [255:0] kv_load_data_q, x_load_data_q;
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

    ot_hdc_matvec #(.W(4), .G(2), .IL(8), .AW(16), .NW(8)) u_me (
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

    wire [265:0] rom_codeword;
    wire [255:0] rom_data;
    wire rom_corrected, rom_uncorrectable;
    wire rom_ce = wrom_re && (wrom_addr[15:13] == 0);
    reg rom_valid;
    always @(posedge clk) if (wrom_re) rom_valid <= rom_ce;
    ot_rom_8192x266_m8 u_wrom (
        .clk(clk), .ce_in(rom_ce), .addr_in(wrom_addr[12:0]),
        .rd_out(rom_codeword));
    ot_rom_secded_dec #(.K(256)) u_ecc (
        .cw(rom_codeword), .data(rom_data),
        .corrected(rom_corrected), .uncorrectable(rom_uncorrectable));
    assign wrom_q = rom_valid ? rom_data[127:0] : 128'd0;

    genvar g;
    generate for (g = 0; g < 2; g = g + 1) begin : g_bank
        wire [255:0] kv_word, x_word;
        ot_sram_1r1w_1024x256_m2_r2c2 u_kv (
            .clk(clk), .r_ce_in(kv_re), .r_addr_in(kv_addr[g*16 +: 10]),
            .rd_out(kv_word), .w_ce_in(kv_load_q), .w_addr_in(kv_load_addr_q),
            .wd_in(kv_load_data_q), .w_mask_in({256{1'b1}}),
            .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
        ot_sram_1r1w_1024x256_m2_r2c2 u_x (
            .clk(clk), .r_ce_in(x_re[g]), .r_addr_in(x_addr[g*16 +: 10]),
            .rd_out(x_word), .w_ce_in(x_load_q), .w_addr_in(x_load_addr_q),
            .wd_in(x_load_data_q), .w_mask_in({256{1'b1}}),
            .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
        assign kv_q[g*128 +: 128] = kv_word[127:0];
        assign x_q[g*32 +: 32] = x_word[31:0];
    end endgenerate
endmodule
