`timescale 1ns/1ps
// Eight independently addressed HCP weight banks backed by bounded HBM
// windows. Bank k owns a contiguous sector region [hbm_base+k*WORDS*SPW,
// hbm_base+(k+1)*WORDS*SPW). This preserves every 32-bit checkpoint weight and
// permits the HCP's eight skewed read addresses in the same cycle.
// The caller holds an HCP operation until ready; each bank then has the same
// one-cycle synchronous read contract as the ROM bank. A caller adds its
// existing second pipeline register when the HCP is configured with ML=2.
module ot_hdc_v41x_hcp_hbm_window #(
    parameter integer HW = 8,
    parameter integer WORDS = 256,
    parameter integer AW = 16,
    parameter integer HAW = 20,
    parameter integer CW = $clog2(WORDS+1),
    parameter integer TW = (WORDS > 1) ? $clog2(WORDS) : 1,
    parameter integer SPW = HW/8,
    parameter integer BW = (SPW > 1) ? $clog2(SPW) : 1,
    parameter integer LENW = $clog2(SPW+1)
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire                  start,
    input  wire                  release_window,
    input  wire [AW-1:0]         rom_base,
    input  wire [HAW-1:0]        hbm_base,
    input  wire [CW-1:0]         nwords,
    output wire                  ready,
    output wire [7:0]            hq_v,
    input  wire [7:0]            hq_rdy,
    output wire [8*HAW-1:0]      hq_addr,
    output wire [8*LENW-1:0]     hq_len,
    output wire [8*TW-1:0]       hq_tag,
    input  wire [7:0]            hr_v,
    output wire [7:0]            hr_rdy,
    input  wire [8*TW-1:0]       hr_tag,
    input  wire [8*BW-1:0]       hr_beat,
    input  wire [8*256-1:0]      hr_data,
    input  wire [7:0]            rom_re,
    input  wire [8*AW-1:0]       rom_addr,
    output wire [8*HW*32-1:0]    rom_q,
    output wire                  fault,
    output wire [31:0]           received_sectors
);
    wire [7:0] rdy, flt;
    wire [8*32-1:0] counts;
    genvar b;
    generate for (b = 0; b < 8; b = b + 1) begin : g_bank
        wire [3:0] why;
        wire [CW-1:0] fetched;
        wire [HAW:0] bank_base = {1'b0, hbm_base} + (b * WORDS * SPW);
        ot_hdc_v41x_weight_window #(
            .WB(HW*32), .SB(256), .WORDS(WORDS), .AW(AW),
            .HAW(HAW), .NPC(1), .LENW(LENW)
        ) u_window (
            .clk(clk), .rst_n(rst_n), .start(start),
            .release_window(release_window), .rom_base(rom_base),
            .hbm_base(bank_base[HAW-1:0]), .nwords(nwords),
            .ready(rdy[b]), .hq_v(hq_v[b]), .hq_rdy(hq_rdy[b]),
            .hq_addr(hq_addr[b*HAW +: HAW]), .hq_len(hq_len[b*LENW +: LENW]),
            .hq_tag(hq_tag[b*TW +: TW]), .hr_v(hr_v[b]),
            .hr_rdy(hr_rdy[b]), .hr_tag(hr_tag[b*TW +: TW]),
            .hr_beat(hr_beat[b*BW +: BW]), .hr_data(hr_data[b*256 +: 256]),
            .rom_re(rom_re[b]), .rom_addr(rom_addr[b*AW +: AW]),
            .rom_q(rom_q[b*HW*32 +: HW*32]), .fault(flt[b]),
            .fault_why(why), .fetched_words(fetched),
            .received_sectors(counts[b*32 +: 32])
        );
    end endgenerate
    assign ready = &rdy;
    assign fault = |flt;
    assign received_sectors = counts[0 +: 32] + counts[32 +: 32] +
                              counts[64 +: 32] + counts[96 +: 32] +
                              counts[128 +: 32] + counts[160 +: 32] +
                              counts[192 +: 32] + counts[224 +: 32];
endmodule
