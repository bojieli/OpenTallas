`timescale 1ns/1ps
// Prototype write-side bridge for the SW-wide Qwen vector stream unit.
// Input bytes have already been rounded to the HBM FP8 format. K writes go to
// two tile parities x SW independent 16-byte tail-word banks. The bank row is
// floor(logical_word/SW); the bank number is logical_word mod SW. Read muxing,
// macro collars/BIST, and closed-tile flush scheduling are integration work.
//
// V writes and externally supplied K-tail flush words share one 32-byte sector
// assembler. A full sector writes directly; a partial sector explicitly reads
// the old 32 bytes and merges before writing. There is one sector buffer, so
// in_ready/fl_ready backpressure a new sector until the old write completes.
// A vector beat must target a single sector; malformed beats raise fault.
module ot_hdc_qwen_kv_write_adapter #(
    parameter integer SW = 8,
    parameter integer AW = 24,
    parameter integer LOG_HD = 7,
    parameter integer LOG_TW = 2,
    parameter integer V0_ELEMENT = 1048576
) (
    input  wire clk, rst_n,
    input  wire in_v,
    output reg  in_ready,
    input  wire [SW-1:0] in_we,
    input  wire [SW*AW-1:0] in_addr,
    input  wire [SW*8-1:0] in_data,
    output reg  [2*SW-1:0] tl_we,
    output reg  [2*SW*AW-1:0] tl_row,
    output reg  [2*SW*16-1:0] tl_mask,
    output reg  [2*SW*128-1:0] tl_data,
    // A completed K-tail word, emitted by the tail read/flush controller.
    input  wire fl_v,
    output reg  fl_ready,
    input  wire [AW-1:0] fl_word_addr,
    input  wire [127:0] fl_word_data,
    input  wire flush,
    output wire idle,
    output wire mem_r_v,
    input  wire mem_r_ready,
    output wire [AW-1:0] mem_r_sector,
    input  wire mem_r_resp_v,
    input  wire [255:0] mem_r_resp_data,
    output wire mem_w_v,
    input  wire mem_w_ready,
    output wire [AW-1:0] mem_w_sector,
    output wire [255:0] mem_w_data,
    output reg  fault
);
    localparam integer LG_SW = $clog2(SW);
    localparam [2:0] EMPTY=0, FILL=1, RREQ=2, RWAIT=3, WREQ=4;
    reg [2:0] state;
    reg [AW-1:0] sector;
    reg [255:0] data_buf, merged;
    reg [31:0] byte_mask;
    reg [AW-1:0] first_sector;
    wire [AW-1:0] fl_sector = fl_word_addr >> 1;
    reg all_k, all_v, one_sector, bank_unique, have_first;
    reg [2*SW-1:0] occupied;
    reg [AW-1:0] addr_i, word_i;
    integer i, j, bank_i, lane_i, off_i;

    // A beat is accepted atomically. Mixed K/V and duplicate tail write ports
    // are protocol faults rather than dropped writes.
    always @(*) begin
        all_k = 1'b1; all_v = 1'b1; one_sector = 1'b1;
        bank_unique = 1'b1; occupied = 0;
        have_first = 1'b0; first_sector = 0;
        for (i=0; i<SW; i=i+1) if (in_we[i]) begin
            addr_i = in_addr[i*AW +: AW];
            if (!have_first) begin
                first_sector = addr_i >> 5;
                have_first = 1'b1;
            end else if ((addr_i >> 5) != first_sector) one_sector = 1'b0;
            if (addr_i >= V0_ELEMENT) all_k = 1'b0;
            else all_v = 1'b0;
            word_i = addr_i >> 4;
            bank_i = ((word_i >> LOG_HD) & 1) * SW + (word_i & (SW-1));
            if (addr_i < V0_ELEMENT) begin
                if (occupied[bank_i]) bank_unique = 1'b0;
                occupied[bank_i] = 1'b1;
            end
        end
        addr_i = 0; word_i = 0; bank_i = 0;
        in_ready = 1'b0;
        fl_ready = 1'b0;
        if (!in_v || in_we == 0) in_ready = 1'b1;
        else if (all_k && bank_unique) in_ready = 1'b1;
        else if (all_v && one_sector && !fl_v &&
                 (state == EMPTY || (state == FILL && sector == first_sector))) in_ready = 1'b1;
        if (!in_v && (state == EMPTY || (state == FILL && sector == fl_sector)))
            fl_ready = 1'b1;

        tl_we = 0; tl_row = 0; tl_mask = 0; tl_data = 0;
        if (in_v && in_ready && all_k) begin
            for (j=0; j<SW; j=j+1) if (in_we[j]) begin
                word_i = in_addr[j*AW +: AW] >> 4;
                lane_i = in_addr[j*AW +: AW] & 15;
                bank_i = ((word_i >> LOG_HD) & 1) * SW + (word_i & (SW-1));
                tl_we[bank_i] = 1'b1;
                // Drop tile bits: tiles 0 and 2 reuse one parity's SRAM.
                tl_row[bank_i*AW +: AW] =
                    ((word_i >> (LOG_HD + LOG_TW)) << (LOG_HD - LG_SW)) |
                    ((word_i & ((1 << LOG_HD) - 1)) >> LG_SW);
                tl_mask[bank_i*16 +: 16] = lane_i == 0 ? 16'hffff : (16'h1 << lane_i);
                tl_data[bank_i*128 + lane_i*8 +: 8] = in_data[j*8 +: 8];
            end
        end
        word_i = 0; lane_i = 0; bank_i = 0;
    end

    assign idle = state == EMPTY;
    assign mem_r_v = state == RREQ;
    assign mem_r_sector = sector;
    assign mem_w_v = state == WREQ;
    assign mem_w_sector = sector;
    assign mem_w_data = merged;

    integer k;
    reg [31:0] next_mask;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= EMPTY; sector <= 0; data_buf <= 0; merged <= 0;
            byte_mask <= 0; fault <= 0;
        end else begin
            if (in_v && in_we != 0 && !(all_k && bank_unique) &&
                !(all_v && one_sector)) fault <= 1'b1;
            if (in_v && in_ready && all_v && in_we != 0) begin
                if (state == EMPTY) begin
                    sector <= first_sector; data_buf <= 0; byte_mask <= 0;
                end
                next_mask = state == EMPTY ? 0 : byte_mask;
                for (k=0; k<SW; k=k+1) if (in_we[k]) begin
                    off_i = in_addr[k*AW +: AW] & 31;
                    data_buf[off_i*8 +: 8] <= in_data[k*8 +: 8];
                    next_mask[off_i] = 1'b1;
                end
                byte_mask <= next_mask;
                state <= FILL;
            end else if (fl_v && fl_ready) begin
                if (state == EMPTY) begin
                    sector <= fl_sector; data_buf <= 0; byte_mask <= 0;
                end
                for (k=0; k<16; k=k+1)
                    data_buf[((fl_word_addr[0] * 16 + k)*8) +: 8] <= fl_word_data[k*8 +: 8];
                next_mask = (state == EMPTY ? 32'b0 : byte_mask) |
                            (fl_word_addr[0] ? 32'hffff0000 : 32'h0000ffff);
                byte_mask <= next_mask;
                state <= FILL;
            end else case (state)
                FILL: if (byte_mask == 32'hffffffff) begin
                    merged <= data_buf; state <= WREQ;
                end else if (flush || (in_v && all_v && first_sector != sector) ||
                             (fl_v && fl_sector != sector)) state <= RREQ;
                RREQ: if (mem_r_ready) state <= RWAIT;
                RWAIT: if (mem_r_resp_v) begin
                    for (k=0; k<32; k=k+1)
                        merged[k*8 +: 8] <= byte_mask[k] ? data_buf[k*8 +: 8] : mem_r_resp_data[k*8 +: 8];
                    state <= WREQ;
                end
                WREQ: if (mem_w_ready) begin
                    state <= EMPTY; byte_mask <= 0;
                end
                default: state <= EMPTY;
            endcase
        end
    end
endmodule
