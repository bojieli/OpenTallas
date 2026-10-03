`timescale 1ns/1ps
// Selected compressed-KV main-row reader.  This is intentionally separate from
// the 528-byte FP8 window ring: a source row has 512 E2M1 codes, low nibble
// first, and 32 E4M3FN scales (one per 16 codes), exactly 288 bytes/9 sectors.
//
// Ingest publishes source_count only after its HBM writes are visible.  The
// selector supplies source_id explicitly; local_row is a position in the
// current attention job, not an address in the source's compressed cache.
// The published placement stripes 16-row groups over 4 dies and 4 stacks.
// Nonlocal-die sources assert remote_needed and make no local HBM request;
// the array fabric must transfer them to this die before attention can run.
// local_row < window_count is never accepted here.  One row is staged at a
// time; kv_ok only means that exact local/source pair has fully arrived.
//
// PIPE (opt-in, default 0 = the original one-outstanding-sector schedule):
// PIPE = 1 issues the row's nine sector reads back to back (one per grant,
// tag = sector index) and accepts their responses in any order and while
// requests are still issuing; each tag must be 0..8, not yet received and
// already issued. kv_ok rises when all nine have arrived (the NaN-scale probe
// is applied to the tag-8 sector whenever it arrives). The HBM response port
// must therefore keep the TAGW-bit tag of every request. Several PIPE
// instances behind a per-stack arbiter form the multi-row selected fetch
// (ot_chip_v41x_ckv_sel_fetch).
module ot_chip_v41x_ckv_selected_dma #(
    parameter integer POS_W = 21,
    parameter integer SEC_W = 30,
    parameter integer HAW = 30,
    parameter integer TAGW = 16,
    parameter integer DIE_ID = 0,
    parameter integer MAX_CONTEXT = 1048576,
    parameter integer PIPE = 0
) (
    input wire clk, rst_n,
    input wire [4*SEC_W-1:0] region_base_sector,
    input wire [4*SEC_W-1:0] region_sector_count,
    input wire [POS_W-1:0] published_source_count,
    input wire fetch_v,
    output wire fetch_ready,
    input wire [9:0] local_row,
    input wire [7:0] window_count,
    input wire [POS_W-1:0] source_id,
    output reg remote_needed,
    output wire [1:0] remote_die,
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
    reg [1:0] active_stack;
    reg [POS_W-1:0] active_local_source;
    reg [2303:0] stage;
    reg stage_valid;
    reg [8:0] got;                         // PIPE: sectors received
    wire [TAGW-1:0] rtag = s_tag[active_stack*TAGW +: TAGW];
    wire rtag_ok = rtag < TAGW'(9) && rtag < TAGW'(sec) + TAGW'(state == RSP) &&
                   !got[rtag[3:0]];
    wire [8:0] got_next = got | (9'd1 << rtag[3:0]);
    wire [1:0] source_die = source_id[5:4];
    wire [1:0] source_stack = source_id[7:6];
    wire [POS_W-1:0] source_local = (source_id >> 8 << 4) | POS_W'(source_id[3:0]);
    wire [SEC_W-1:0] base = region_base_sector[active_stack*SEC_W +: SEC_W];
    wire [SEC_W-1:0] count = region_sector_count[active_stack*SEC_W +: SEC_W];
    wire [SEC_W+4:0] end_wide = (SEC_W+5)'(base) + (SEC_W+5)'(count);
    wire [SEC_W+4:0] addr_wide = (SEC_W+5)'(base) +
        (SEC_W+5)'(active_local_source) * (SEC_W+5)'(9) + (SEC_W+5)'(sec);
    wire addr_bad = end_wide >= ((SEC_W+5)'(1) << SEC_W) ||
                    addr_wide >= end_wide || addr_wide >= ((SEC_W+5)'(1) << SEC_W);
    wire response = s_v[active_stack];
    wire grant = m_v[active_stack] && m_rdy[active_stack];
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
    assign remote_die = source_die;
    assign s_rdy = 4'hf;
`ifndef SYNTHESIS
    initial if (POS_W < 21 || SEC_W < 30 || HAW < SEC_W ||
                DIE_ID < 0 || DIE_ID > 3 || TAGW < 4)
        $fatal(1, "selected CKV DMA parameter contract failed");
`endif
    always @(*) begin
        m_v = 0; m_addr = 0; m_len = 0; m_tag = 0; m_we = 0;
        m_wdata = 0; m_wstrb = 0;
        if (state == REQ && !addr_bad) begin
            m_v[active_stack] = 1'b1;
            m_addr[active_stack*HAW +: HAW] = HAW'(addr_wide);
            m_len[active_stack*4 +: 4] = 4'd1;
            m_tag[active_stack*TAGW +: TAGW] = TAGW'(sec);
        end
    end
    integer j, si;
    reg final_poison;
    always @(*) begin
        final_poison = 1'b0;
        for (j = 0; j < 32; j = j + 1)
            if (s_data[active_stack*256+8*j +: 7] == 7'h7f)
                final_poison = 1'b1;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE; sec <= 0; active_row <= 0; active_source <= 0;
            active_stack <= 0; active_local_source <= 0; remote_needed <= 0;
            stage_valid <= 0; q <= 0; q_fp8 <= 0; got <= 0;
            fault <= 0; fault_code <= 0;
            st_rows_fetched <= 0; st_sectors_read <= 0;
        end else begin
            remote_needed <= 0;
            if (re) begin
                if (!kv_ok || rrow != active_row) begin
                    fault <= 1; fault_code[3] <= 1;
                end else if (poison) begin
                    fault <= 1; fault_code[2] <= 1;
                end else begin q <= decoded_fp32; q_fp8 <= decoded_fp8; end
            end
            if (state == REQ && addr_bad) begin
                fault <= 1; fault_code[0] <= 1; state <= IDLE;
            end else if (PIPE != 0 && state != IDLE) begin
                // REQ: issuing sectors sec = 0..8; RSP: all issued.  Responses
                // are accepted in both.
                if (state == REQ && grant) begin
                    if (sec == 4'd8) state <= RSP; else sec <= sec + 1'b1;
                end
                if (response) begin
                    if (!rtag_ok || s_beat[active_stack*4 +: 4] != 0) begin
                        fault <= 1; fault_code[1] <= 1; state <= IDLE;
                    end else if (rtag == TAGW'(8) && final_poison) begin
                        fault <= 1; fault_code[2] <= 1; state <= IDLE;
                    end else begin
                        for (si = 0; si < 9; si = si + 1)     // constant-index sector writes (no shifter)
                            if (rtag[3:0] == 4'(si)) stage[256*si +: 256] <= s_data[active_stack*256 +: 256];
                        st_sectors_read <= st_sectors_read + 1;
                        got <= got_next;
                        if (got_next == 9'h1ff) begin
                            stage_valid <= 1;
                            st_rows_fetched <= st_rows_fetched + 1;
                            state <= IDLE;
                        end
                    end
                end
            end else case (state)
                IDLE: if (fetch_v) begin
                    stage_valid <= 0;
                    active_row <= local_row;
                    active_source <= source_id;
                    active_stack <= source_stack;
                    active_local_source <= source_local;
                    sec <= 0; got <= 0;
                    if (local_row < {2'b0, window_count} || local_row >= 10'd640 ||
                        window_count > 8'd128 || source_id >= published_source_count ||
                        source_id >= POS_W'(MAX_CONTEXT)) begin
                        fault <= 1; fault_code[0] <= 1;
                    end else if (source_die != 2'(DIE_ID)) begin
                        remote_needed <= 1;
                    end else state <= REQ;
                end
                REQ: if (grant) state <= RSP;
                RSP: if (response) begin
                    if (s_tag[active_stack*TAGW +: TAGW] != TAGW'(sec) ||
                        s_beat[active_stack*4 +: 4] != 0) begin
                        fault <= 1; fault_code[1] <= 1; state <= IDLE;
                    end else if (sec == 4'd8 && final_poison) begin
                        fault <= 1; fault_code[2] <= 1; state <= IDLE;
                    end else begin
                        for (si = 0; si < 9; si = si + 1)
                            if (sec == 4'(si)) stage[256*si +: 256] <= s_data[active_stack*256 +: 256];
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
