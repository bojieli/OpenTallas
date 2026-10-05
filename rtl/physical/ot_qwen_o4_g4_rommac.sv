`timescale 1ns/1ps
// Qwen3-8B O4 ROM/MAC neighbourhood: four lane groups x 16 lanes of the
// adopted INT8 ot_hdc_matvec with its code ROM (and, for a result-port
// neighbourhood, its per-group scale ROM) as real ASAP7 macro views.
//
// Physical experiment unit of W5 (docs/QWEN_O4_FLOORPLAN.md). The matvec is
// instantiated unchanged; this wrapper only binds its synchronous ROM ports
// to finite macros:
//
//  * Code ROM. Groups 2p and 2p+1 share one 256-bit word column (bits
//    128*(g%2) + 8*lane) of CODE_BANKS depth-4096 macros. The per-die image
//    (target 38,880 + drafter 5,600 = 44,480 words, tools/qwen_o4_rom_placement.py)
//    needs 11 banks. Bank b holds words 4096*b..4096*b+4095 and is enabled
//    only for its own addresses; the bank-select registered with the read
//    picks its output. The select and OR sit between the macro pins and the
//    matvec's own MEM_PIPE capture (mq_wrom) inside the same cycle, so the
//    cycle contract of ot_hdc_matvec (return c+1, capture c+2) is unchanged:
//    zero added cycles.
//  * Scale ROM. With SCALE_BANKS > 0, each group gets SCALE_BANKS depth-4096
//    macros on its own scale_addr / scale_gre, selected the same way.
//    SCALE_BANKS = 0 ties scale_q to zero: a neighbourhood above the
//    result-port groups never raises scale_gre (ot_hdc_matvec g_post_scale).
//  * The 10 spare bits of each 266-bit word are not read (no ECC decode on
//    the path; the O4 contract carries none).
module ot_qwen_o4_g4_rommac #(
    parameter integer CODE_BANKS  = 11,
    parameter integer SCALE_BANKS = 1,
    parameter integer AW = 24,
    parameter integer NW = 16
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
    // KV operand port (the KV service lands here through a registered channel)
    output wire              kv_re,
    output wire [4*AW-1:0]   kv_addr,
    input  wire [4*16*32-1:0] kv_q,
    // x operand port (vector-memory read, one element a group)
    output wire [3:0]        x_re,
    output wire [4*AW-1:0]   x_addr,
    input  wire [4*32-1:0]   x_q,
    // results
    output wire              ov,
    output wire [3:0]        o_we,
    output wire [4*AW-1:0]   o_addr,
    output wire [4*16-1:0]   o_mask,
    output wire [4*16*32-1:0] o_data,
    output wire [NW-1:0]     am_idx,
    output wire [31:0]       am_val,
    output wire              am_any,
    output wire              mx_we,
    output wire [AW-1:0]     mx_addr,
    output wire [15:0]       mx_mask,
    output wire [16*32-1:0]  mx_data,
    output wire [15:0]       progress,
    output wire              fault
);
    localparam integer G = 4, W = 16;
    localparam integer CB = (CODE_BANKS > 1) ? $clog2(CODE_BANKS) : 1;
    localparam integer SB = (SCALE_BANKS > 1) ? $clog2(SCALE_BANKS) : 1;

    wire              wrom_re;
    wire [AW-1:0]     wrom_addr;
    wire [G*W*8-1:0]  wrom_q;
    wire              scale_re;
    wire [G-1:0]      scale_gre;
    wire [G*AW-1:0]   scale_addr;
    wire [G*W*16-1:0] scale_q;

    ot_hdc_matvec #(.W(W), .G(G), .IL(8), .AW(AW), .NW(NW),
                    .INT8_WEIGHT(1), .INT8_SCALE_WCS_BASE(1)) u_me (
        .clk(clk), .rst_n(rst_n), .go(go), .ready(ready), .idle(idle),
        .i_nout(i_nout), .i_tiles(i_tiles), .i_k(i_k), .i_wsrc(i_wsrc),
        .i_wbase(i_wbase), .i_ts(i_ts), .i_ks(i_ks), .i_js(i_js),
        .i_xbase(i_xbase), .i_xks(i_xks), .i_xjs(i_xjs), .i_xcs(i_xcs),
        .i_jsh(i_jsh), .i_split(i_split), .i_wcs(i_wcs), .i_round(i_round),
        .i_obase(i_obase), .i_ots(i_ots), .i_ojs(i_ojs),
        .i_mmode(i_mmode), .i_oen(i_oen), .i_amax(i_amax), .i_rmax(i_rmax),
        .i_mbase(i_mbase),
        .wrom_re(wrom_re), .wrom_addr(wrom_addr), .wrom_q(wrom_q),
        .scale_re(scale_re), .scale_gre(scale_gre), .scale_addr(scale_addr), .scale_q(scale_q),
        .kv_re(kv_re), .kv_addr(kv_addr), .kv_q(kv_q),
        .x_re(x_re), .x_addr(x_addr), .x_q(x_q),
        .ov(ov), .o_we(o_we), .o_addr(o_addr), .o_mask(o_mask), .o_data(o_data),
        .am_idx(am_idx), .am_val(am_val), .am_any(am_any),
        .mx_we(mx_we), .mx_addr(mx_addr), .mx_mask(mx_mask), .mx_data(mx_data),
        .progress(progress), .fault(fault)
    );

    // ---- code ROM: two word columns (group pairs) x CODE_BANKS banks ----------
    wire [CODE_BANKS-1:0] code_ce;
    reg  [CODE_BANKS-1:0] code_sel_q;
    genvar b, p, g;
    generate
        for (b = 0; b < CODE_BANKS; b = b + 1) begin : g_code_ce
            assign code_ce[b] = wrom_re && (wrom_addr[AW-1:12] == b);
        end
    endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) code_sel_q <= {CODE_BANKS{1'b0}};
        else if (wrom_re) code_sel_q <= code_ce;
    end
    generate
        for (p = 0; p < 2; p = p + 1) begin : g_pair
            wire [255:0] bank_q [0:CODE_BANKS-1];
            wire [255:0] or_q   [0:CODE_BANKS];
            assign or_q[0] = 256'd0;
            for (b = 0; b < CODE_BANKS; b = b + 1) begin : g_bank
                wire [265:0] rd;
                ot_rom_4096x266_m8 u_rom (.clk(clk), .ce_in(code_ce[b]),
                                          .addr_in(wrom_addr[11:0]), .rd_out(rd));
                assign bank_q[b] = rd[255:0] & {256{code_sel_q[b]}};
                assign or_q[b+1] = or_q[b] | bank_q[b];
            end
            assign wrom_q[256*p +: 256] = or_q[CODE_BANKS];
        end
    endgenerate

    // ---- scale ROM: SCALE_BANKS banks per group --------------------------------
    generate
        if (SCALE_BANKS == 0) begin : g_no_scale
            assign scale_q = {G*W*16{1'b0}};
        end else begin : g_scale
            for (g = 0; g < G; g = g + 1) begin : g_grp
                wire [AW-1:0] sa = scale_addr[g*AW +: AW];
                wire [SCALE_BANKS-1:0] sce;
                reg  [SCALE_BANKS-1:0] ssel_q;
                wire [255:0] sor [0:SCALE_BANKS];
                assign sor[0] = 256'd0;
                for (b = 0; b < SCALE_BANKS; b = b + 1) begin : g_bank
                    wire [265:0] rd;
                    assign sce[b] = scale_gre[g] && (sa[AW-1:12] == b);
                    ot_rom_4096x266_m8 u_rom (.clk(clk), .ce_in(sce[b]),
                                              .addr_in(sa[11:0]), .rd_out(rd));
                    assign sor[b+1] = sor[b] | (rd[255:0] & {256{ssel_q[b]}});
                end
                always @(posedge clk or negedge rst_n) begin
                    if (!rst_n) ssel_q <= {SCALE_BANKS{1'b0}};
                    else if (scale_gre[g]) ssel_q <= sce;
                end
                assign scale_q[256*g +: 256] = sor[SCALE_BANKS];
            end
        end
    endgenerate
    // scale_re is the OR of scale_gre; the per-group enables drive the banks.
    wire unused_scale_re = scale_re;
endmodule
