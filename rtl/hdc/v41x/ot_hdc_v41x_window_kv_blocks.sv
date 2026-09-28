`timescale 1ns/1ps
// Core-side packed window KV block handoff.  Capture the exact QDQ8 result
// from ot_hdc_v41_qe, then dispatch one 32-code/E8M0-scale block at a time
// when the following KVT stream instruction names that VM source row.
//
// KVT is transposed: element i of local attention row r has logical address
//   kvt_base + ((r >> 4) << KVT_SH) + (i << 4) + (r & 15).
// Thus a block's first element is NOT necessarily 32-element aligned.  The
// die-side KVD adds the user base and maps the logical row to packed sectors.
// A handshake transfers all 33 bytes atomically.  The receiver must drain a
// committed block before a dependent prefetch and invalidate staged copies.
// This module does not drive the old scalar KVT write port.
module ot_hdc_v41x_window_kv_blocks #(
    parameter integer AW = 30,
    parameter integer POS_W = 21,
    parameter integer KVT_SH = 13, // 512 dimensions x 16 interleaved rows
    parameter integer SEPARATE_ROWS = 0 // full shape: HBM absolute row differs from local KVT row
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              cap_v,
    input  wire [AW-1:0]     cap_src_addr,
    input  wire [255:0]      cap_codes,
    input  wire [7:0]        cap_scale,
    output wire              cap_ready,
    output wire [AW-1:0]     cap_src_base,
    output wire              idle,
    input  wire              issue,
    input  wire [AW-1:0]     issue_src_base,
    input  wire [AW-1:0]     issue_kvt_base,
    input  wire [POS_W-1:0]  issue_row,      // local KVT row when SEPARATE_ROWS=1
    input  wire [POS_W-1:0]  issue_abs_row,  // persistent HBM row when SEPARATE_ROWS=1
    output wire              issue_ready,
    output wire              blk_v,
    input  wire              blk_ready,
    output wire [AW-1:0]     blk_kvt_base,
    output wire [POS_W-1:0]  blk_row,       // absolute HBM row
    output wire [POS_W-1:0]  blk_kvt_row,   // local KVT row for alias checking
    output wire [3:0]        blk_idx,
    output wire [AW-1:0]     blk_first_elem,
    output wire [255:0]      blk_codes,
    output wire [7:0]        blk_scale,
    output reg               fault
);
    localparam [1:0] EMPTY = 0, FILL = 1, FULL = 2, DRAIN = 3;
`ifndef SYNTHESIS
    initial if (AW < 30 || POS_W < 21 || KVT_SH < $clog2(16*512))
        $fatal(1, "full-shape window KV needs AW>=30, POS_W>=21, KVT_SH>=13");
`endif
    reg [1:0] state;
    reg [4:0] count;
    reg [3:0] rd_idx;
    reg [AW-1:0] src_base, kvt_base;
    reg [POS_W-1:0] row, kvt_row;
    reg [255:0] codes [0:15];
    reg [7:0] scales [0:15];
    wire [AW:0] cap_expected = {1'b0, src_base} + (AW+1)'(count) * (AW+1)'(32);
    wire [POS_W-1:0] issue_abs = SEPARATE_ROWS ? issue_abs_row : issue_row;
    wire [AW:0] block_offset = ((AW+1)'(kvt_row) >> 4) << KVT_SH;
    wire [AW:0] first_wide = {1'b0, kvt_base} + block_offset +
                             ((AW+1)'(rd_idx) << 9) + (AW+1)'(kvt_row[3:0]);
    wire [AW:0] issue_last_wide = {1'b0, issue_kvt_base} +
                                  ((((AW+1)'(issue_row) >> 4) << KVT_SH)) +
                                  ((AW+1)'(511) << 4) + (AW+1)'(issue_row[3:0]);
    assign cap_ready = (state == EMPTY || state == FILL) && count < 5'd16;
    assign cap_src_base = src_base;
    assign idle = state == EMPTY;
    assign issue_ready = state == FULL;
    assign blk_v = state == DRAIN;
    assign blk_kvt_base = kvt_base;
    assign blk_row = row;
    assign blk_kvt_row = kvt_row;
    assign blk_idx = rd_idx;
    assign blk_first_elem = first_wide[AW-1:0];
    assign blk_codes = codes[rd_idx];
    assign blk_scale = scales[rd_idx];

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= EMPTY; count <= 0; rd_idx <= 0; fault <= 0;
            src_base <= 0; kvt_base <= 0; row <= 0; kvt_row <= 0;
        end else begin
            if (cap_v) begin
                if (!cap_ready || cap_scale == 8'hff ||
                    (state == FILL && (cap_expected[AW] || cap_src_addr != cap_expected[AW-1:0])) ||
                    cap_src_addr[4:0] != 5'd0) fault <= 1'b1;
                else begin
                    if (state == EMPTY) src_base <= cap_src_addr;
                    codes[count[3:0]] <= cap_codes;
                    scales[count[3:0]] <= cap_scale;
                    count <= count + 1'b1;
                    state <= (count == 5'd15) ? FULL : FILL;
                end
            end
            if (issue) begin
                if (!issue_ready || issue_src_base != src_base ||
                    issue_abs >= POS_W'(1048576) ||
                    (SEPARATE_ROWS && issue_row >= POS_W'(128)) ||
                    issue_last_wide[AW])
                    fault <= 1'b1;
                else begin
                    kvt_base <= issue_kvt_base;
                    row <= issue_abs;
                    kvt_row <= issue_row;
                    rd_idx <= 0;
                    state <= DRAIN;
                end
            end
            if (blk_v && blk_ready) begin
                if (first_wide[AW]) fault <= 1'b1;
                if (rd_idx == 4'd15) begin
                    state <= EMPTY;
                    count <= 0;
                    rd_idx <= 0;
                end else rd_idx <= rd_idx + 1'b1;
            end
            if (cap_v && issue) fault <= 1'b1;
        end
    end
endmodule
