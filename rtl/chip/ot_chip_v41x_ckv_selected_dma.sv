`timescale 1ns/1ps
// Selected compressed-KV main-row reader.  This is intentionally separate from
// the 528-byte FP8 window ring: a source row has 512 E2M1 codes, low nibble
// first, and 32 E4M3FN scales (one per 16 codes), exactly 288 bytes/9 sectors.
//
// Ingest publishes source_count only after its HBM writes are visible.  The
// selector supplies source_id explicitly; local_row is a position in the
// current attention job, not an address in the source's compressed cache.
// local_row < window_count is never accepted here.  One row is staged at a
// time; kv_ok only means that exact local/source pair has fully arrived.
module ot_chip_v41x_ckv_selected_dma #(
    parameter integer POS_W = 21,
    parameter integer SEC_W = 30,
    parameter integer HAW = 30,
    parameter integer TAGW = 16,
    parameter integer SEL_STACK = 0,
    parameter integer MAX_CONTEXT = 1048576
) (
    input wire clk, rst_n,
    input wire [SEC_W-1:0] region_base_sector,
    input wire [SEC_W-1:0] region_sector_count,
    input wire [POS_W-1:0] published_source_count,
    input wire fetch_v,
    output wire fetch_ready,
    input wire [9:0] local_row,
    input wire [7:0] window_count,
    input wire [POS_W-1:0] source_id,
    output wire kv_ok,
    input wire re,
    input wire [9:0] rrow,
    input wire [8:0] relem,
    output reg [31:0] q,
    output reg [7:0] q_fp8,
    output wire [2303:0] packed_row,
    output wire packed_valid,
    output wire [9:0] packed_local_row,
    output wire [POS_W-1:0] packed_source_id,
    output reg fault,
    output reg [3:0] fault_code, // range, HBM response, poison, read
    output reg [31:0] st_rows_fetched,
    output reg [31:0] st_sectors_read,
    output reg [3:0] m_v,
    input wire [3:0] m_rdy,
    output reg [4*HAW-1:0] m_addr,
    output reg [4*4-1:0] m_len,
    output reg [4*TAGW-1:0] m_tag,
    output reg [3:0] m_we,
    output reg [4*256-1:0] m_wdata,
    output reg [4*32-1:0] m_wstrb,
    input wire [3:0] m_wr_done,
    input wire [3:0] s_v,
    output wire [3:0] s_rdy,
    input wire [4*TAGW-1:0] s_tag,
    input wire [4*4-1:0] s_beat,
    input wire [4*256-1:0] s_data
);
    localparam [1:0] IDLE=0, REQ=1, RSP=2;
    reg [1:0] state;
    reg [3:0] sec;
    reg [9:0] active_row;
    reg [POS_W-1:0] active_source;
    reg [2303:0] stage;
    reg stage_valid;
    wire [SEC_W+4:0] end_wide = (SEC_W+5)'(region_base_sector) +
                                  (SEC_W+5)'(region_sector_count);
    wire [SEC_W+4:0] addr_wide = (SEC_W+5)'(region_base_sector) +
        (SEC_W+5)'(active_source) * (SEC_W+5)'(9) + (SEC_W+5)'(sec);
    wire addr_bad = end_wide >= ((SEC_W+5)'(1) << SEC_W) ||
                    addr_wide >= end_wide || addr_wide >= ((SEC_W+5)'(1) << SEC_W);
    wire response = s_v[SEL_STACK];
    wire grant = m_v[SEL_STACK] && m_rdy[SEL_STACK];
    wire [7:0] packed_code_byte = stage[8*integer'(relem >> 1) +: 8];
    wire [3:0] code = relem[0] ? packed_code_byte[7:4] : packed_code_byte[3:0];
    wire [7:0] scale = stage[2048+8*integer'(relem >> 4) +: 8];
    wire [7:0] decoded_fp8;
    wire [31:0] decoded_fp32;
    wire poison;
    ot_chip_v41x_ckv_fp4_decode u_decode (
        .code(code), .scale(scale), .fp8(decoded_fp8),
        .fp32(decoded_fp32), .poison(poison));
    assign fetch_ready = state == IDLE;
    assign kv_ok = state == IDLE && stage_valid;
    assign packed_valid = kv_ok;
    assign packed_row = packed_valid ? stage : '0;
    assign packed_local_row = active_row;
    assign packed_source_id = active_source;
    assign s_rdy = 4'hf;
`ifndef SYNTHESIS
    initial if (POS_W < 21 || SEC_W < 30 || HAW < SEC_W ||
                SEL_STACK < 0 || SEL_STACK > 3 || TAGW < 4)
        $fatal(1, "selected CKV DMA parameter contract failed");
`endif
    always @(*) begin
        m_v = 0; m_addr = 0; m_len = 0; m_tag = 0; m_we = 0;
        m_wdata = 0; m_wstrb = 0;
        if (state == REQ && !addr_bad) begin
            m_v[SEL_STACK] = 1'b1;
            m_addr[SEL_STACK*HAW +: HAW] = HAW'(addr_wide);
            m_len[SEL_STACK*4 +: 4] = 4'd1;
            m_tag[SEL_STACK*TAGW +: TAGW] = TAGW'(sec);
        end
    end
    integer j;
    reg final_poison;
    always @(*) begin
        final_poison = 1'b0;
        for (j = 0; j < 32; j = j + 1)
            if (s_data[SEL_STACK*256+8*j +: 7] == 7'h7f)
                final_poison = 1'b1;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE; sec <= 0; active_row <= 0; active_source <= 0;
            stage_valid <= 0; q <= 0; q_fp8 <= 0;
            fault <= 0; fault_code <= 0;
            st_rows_fetched <= 0; st_sectors_read <= 0;
        end else begin
            if (re) begin
                if (!kv_ok || rrow != active_row) begin
                    fault <= 1; fault_code[3] <= 1;
                end else if (poison) begin
                    fault <= 1; fault_code[2] <= 1;
                end else begin q <= decoded_fp32; q_fp8 <= decoded_fp8; end
            end
            if (state == REQ && addr_bad) begin
                fault <= 1; fault_code[0] <= 1; state <= IDLE;
            end else case (state)
                IDLE: if (fetch_v) begin
                    stage_valid <= 0;
                    active_row <= local_row;
                    active_source <= source_id;
                    sec <= 0;
                    if (local_row < {2'b0, window_count} || local_row >= 10'd640 ||
                        window_count > 8'd128 || source_id >= published_source_count ||
                        source_id >= POS_W'(MAX_CONTEXT) ||
                        end_wide >= ((SEC_W+5)'(1) << SEC_W) ||
                        (SEC_W+5)'(region_sector_count) <
                            (SEC_W+5)'(published_source_count) * (SEC_W+5)'(9)) begin
                        fault <= 1; fault_code[0] <= 1;
                    end else state <= REQ;
                end
                REQ: if (grant) state <= RSP;
                RSP: if (response) begin
                    if (s_tag[SEL_STACK*TAGW +: TAGW] != TAGW'(sec) ||
                        s_beat[SEL_STACK*4 +: 4] != 0) begin
                        fault <= 1; fault_code[1] <= 1; state <= IDLE;
                    end else if (sec == 4'd8 && final_poison) begin
                        fault <= 1; fault_code[2] <= 1; state <= IDLE;
                    end else begin
                        stage[256*sec +: 256] <= s_data[SEL_STACK*256 +: 256];
                        st_sectors_read <= st_sectors_read + 1;
                        if (sec == 4'd8) begin
                            stage_valid <= 1;
                            st_rows_fetched <= st_rows_fetched + 1;
                            state <= IDLE;
                        end else begin sec <= sec + 1'b1; state <= REQ; end
                    end
                end
                default: state <= IDLE;
            endcase
        end
    end
endmodule
