`timescale 1ns/1ps
// Bounded operation window for an HBM-resident V4.1 weight family. The core
// announces one ROM address interval before issuing its fixed-latency engine.
// Every word is fetched as consecutive 256-bit sectors in bounded bursts;
// response tags carry the word slot and burst segment, and response beats are
// local to that segment. The engine may read the complete window in any order
// with the same one-cycle contract as its ROM port. A compiler must split an
// operation whose weight interval is larger than WORDS.
module ot_hdc_v41x_weight_window #(
    parameter integer WB = 1024,
    parameter integer SB = 256,
    parameter integer WORDS = 16,
    parameter integer AW = 24,
    parameter integer HAW = 28,
    parameter integer NPC = 4,
    parameter integer LENW = 4,
    parameter integer CW = $clog2(WORDS + 1),
    parameter integer SW = WB / SB,
    parameter integer TW = (WORDS > 1) ? $clog2(WORDS) : 1,
    parameter integer BURST_MAX = (SW < 32) ? SW : 32,
    parameter integer SEGMENTS = (SW + BURST_MAX - 1) / BURST_MAX,
    parameter integer SGW = (SEGMENTS > 1) ? $clog2(SEGMENTS) : 0,
    parameter integer RTW = TW + SGW,
    parameter integer BW = (BURST_MAX > 1) ? $clog2(BURST_MAX) : 1,
    parameter integer IQW = $clog2(WORDS * SEGMENTS + 1)
) (
    input  wire                   clk,
    input  wire                   rst_n,
    input  wire                   start,
    input  wire                   release_window,
    input  wire [AW-1:0]          rom_base,
    input  wire [HAW-1:0]         hbm_base,
    input  wire [CW-1:0]          nwords,
    output wire                   ready,
    // One request fetches at most BURST_MAX sectors. The HBM controller may
    // reorder requests across pseudo-channels; tag and beat restore them.
    output wire                   hq_v,
    input  wire                   hq_rdy,
    output wire [HAW-1:0]         hq_addr,
    output wire [LENW-1:0]        hq_len,
    output wire [RTW-1:0]         hq_tag,
    input  wire [NPC-1:0]         hr_v,
    output wire [NPC-1:0]         hr_rdy,
    input  wire [NPC*RTW-1:0]     hr_tag,
    input  wire [NPC*BW-1:0]      hr_beat,
    input  wire [NPC*SB-1:0]      hr_data,
    input  wire                   rom_re,
    input  wire [AW-1:0]          rom_addr,
    output reg  [WB-1:0]          rom_q,
    output reg                    fault,
    output reg  [3:0]             fault_why, // descriptor, response, duplicate, ROM read
    output wire [CW-1:0]          fetched_words,
    output reg  [31:0]            received_sectors
);
    localparam integer VB = WORDS * SW;
    reg active;
    reg [AW-1:0] base_r;
    reg [HAW-1:0] hbase_r;
    reg [CW-1:0] count_r, issued;
    reg [SGW:0] issue_seg;
    reg [IQW-1:0] issued_reqs;
    reg [VB-1:0] valid;
    reg [WB-1:0] data [0:WORDS-1];
    reg [VB-1:0] seen;
    reg [31:0] inc;
    reg response_bad, duplicate_bad;
    integer p;
    integer c_slot, c_segment, c_beat, c_offset, c_request_index, c_segment_len;
    integer slot, segment, beat, request_index, segment_len;
    wire [HAW:0] end_sector = {1'b0, hbm_base} + (nwords * SW);
    wire [AW:0] end_rom = {1'b0, rom_base} + nwords;
    wire [AW:0] rom_offset = {1'b0, rom_addr} - {1'b0, base_r};

    assign fetched_words = issued;
    assign hq_v = active && !fault && issued < count_r;
    assign hq_addr = hbase_r + (issued * SW) + (issue_seg * BURST_MAX);
    assign hq_len = LENW'(((SEGMENTS > 1) && (issue_seg == SEGMENTS-1)) ?
                           (SW - (SEGMENTS-1) * BURST_MAX) : BURST_MAX);
    assign hq_tag = RTW'((issued << SGW) | issue_seg);
    assign hr_rdy = {NPC{active && !fault}};
    assign ready = active && !fault && issued == count_r &&
                   received_sectors == (count_r * SW);

    // Resolve all response ports against one temporary valid bitmap. This
    // catches duplicate beats even when two ports return them on one cycle.
    always @* begin
        seen = valid;
        inc = 0;
        response_bad = 1'b0;
        duplicate_bad = 1'b0;
        c_slot = 0; c_segment = 0; c_beat = 0; c_offset = 0;
        c_request_index = 0; c_segment_len = 0;
        for (integer i = 0; i < NPC; i = i + 1) begin
            if (hr_v[i] && hr_rdy[i]) begin
                c_slot = (hr_tag[i*RTW +: RTW] >> SGW);
                c_segment = hr_tag[i*RTW +: RTW] & ((1 << SGW) - 1);
                c_beat = hr_beat[i*BW +: BW];
                c_request_index = c_slot * SEGMENTS + c_segment;
                c_segment_len = ((SEGMENTS > 1) && (c_segment == SEGMENTS-1)) ?
                              SW - (SEGMENTS-1)*BURST_MAX : BURST_MAX;
                c_offset = c_slot*SW + c_segment*BURST_MAX + c_beat;
                if (c_slot >= count_r || c_segment >= SEGMENTS ||
                    c_request_index >= issued_reqs || c_beat >= c_segment_len) begin
                    response_bad = 1'b1;
                end else begin
                    if (seen[c_offset])
                        duplicate_bad = 1'b1;
                    else begin
                        seen[c_offset] = 1'b1;
                        inc = inc + 1;
                    end
                end
            end
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active <= 1'b0;
            base_r <= '0;
            hbase_r <= '0;
            count_r <= '0;
            issued <= '0;
            issue_seg <= '0;
            issued_reqs <= '0;
            valid <= '0;
            received_sectors <= 0;
            rom_q <= '0;
            fault <= 1'b0;
            fault_why <= '0;
        end else begin
            if (start) begin
                if (active || nwords == 0 || nwords > WORDS || SW < 1 ||
                    WB % SB != 0 || BURST_MAX < 1 || BURST_MAX > SW ||
                    BURST_MAX >= (1 << LENW) ||
                    end_sector[HAW] || end_rom[AW]) begin
                    fault <= 1'b1;
                    fault_why[0] <= 1'b1;
                end else begin
                    active <= 1'b1;
                    base_r <= rom_base;
                    hbase_r <= hbm_base;
                    count_r <= nwords;
                    issued <= '0;
                    issue_seg <= '0;
                    issued_reqs <= '0;
                    valid <= '0;
                    received_sectors <= 0;
                end
            end else if (release_window) begin
                if (!ready) begin
                    fault <= 1'b1;
                    fault_why[0] <= 1'b1;
                end else begin
                    active <= 1'b0;
                end
            end else begin
                if (hq_v && hq_rdy) begin
                    issued_reqs <= issued_reqs + 1'b1;
                    if (issue_seg == SEGMENTS-1) begin
                        issued <= issued + 1'b1;
                        issue_seg <= '0;
                    end else issue_seg <= issue_seg + 1'b1;
                end
                if (response_bad) begin
                    fault <= 1'b1;
                    fault_why[1] <= 1'b1;
                end
                if (duplicate_bad) begin
                    fault <= 1'b1;
                    fault_why[2] <= 1'b1;
                end
                if (inc != 0) begin
                    valid <= seen;
                    received_sectors <= received_sectors + inc;
                    for (p = 0; p < NPC; p = p + 1) begin
                        slot = hr_tag[p*RTW +: RTW] >> SGW;
                        segment = hr_tag[p*RTW +: RTW] & ((1 << SGW) - 1);
                        beat = hr_beat[p*BW +: BW];
                        request_index = slot * SEGMENTS + segment;
                        segment_len = ((SEGMENTS > 1) && (segment == SEGMENTS-1)) ?
                                      SW - (SEGMENTS-1)*BURST_MAX : BURST_MAX;
                        if (hr_v[p] && hr_rdy[p] && slot < count_r &&
                            segment < SEGMENTS && request_index < issued_reqs &&
                            beat < segment_len)
                            data[slot][(segment*BURST_MAX+beat)*SB +: SB] <= hr_data[p*SB +: SB];
                    end
                end
                if (rom_re) begin
                    if (!ready || rom_offset >= count_r) begin
                        fault <= 1'b1;
                        fault_why[3] <= 1'b1;
                    end else begin
                        rom_q <= data[rom_offset[TW-1:0]];
                    end
                end
            end
        end
    end
endmodule
