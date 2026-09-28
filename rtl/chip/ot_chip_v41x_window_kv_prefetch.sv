`timescale 1ns/1ps
// Packed WINDOW KV half of the adopted V4.1 die KV service.  The compressed
// main KV uses a different 288-byte format and must use a different path.
//
// One absolute window row occupies 17 32-byte sectors at a 544-byte pitch:
// 16 code sectors and one sector whose low 16 bytes are E8M0 scales.  The
// producer transfers each 32-code/scale block atomically.  A row becomes
// readable only after all 16 block transactions have completed.  A 128-entry
// absolute-position tag prevents a stale ring slot from being read after wrap.
//
// The HBM port is the K side of one per-stack arbiter.  This version has one
// outstanding read or write at a time, so its functional result does not
// establish the bandwidth/rate of the 640-row mixed attention path.
module ot_chip_v41x_window_kv_prefetch #(
    parameter integer POS_W = 21,
    parameter integer SEC_W = 30,
    parameter integer HAW = 30,
    parameter integer TAGW = 16,
    parameter integer USER_W = 10,
    parameter integer WIN_STACK = 0,
    parameter integer WINDOW_SLOTS = 128,
    parameter integer MAX_CONTEXT = 1048576
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire [SEC_W-1:0]      region_base_sector,
    input  wire [SEC_W-1:0]      region_sector_count,
    // A host/prefill image may already contain packed rows.  Priming only
    // restores the absolute-position tag after that image is installed.
    input  wire                  prime_v,
    output wire                  prime_ready,
    input  wire [USER_W-1:0]     prime_user,
    input  wire [POS_W-1:0]      prime_row,
    input  wire                  blk_v,
    output wire                  blk_ready,
    input  wire [USER_W-1:0]     blk_user,
    input  wire [POS_W-1:0]      blk_row,
    input  wire [3:0]            blk_idx,
    input  wire [255:0]          blk_codes,
    input  wire [7:0]            blk_scale,
    input  wire                  prefetch_v,
    output wire                  prefetch_ready,
    input  wire [USER_W-1:0]     prefetch_user,
    input  wire [POS_W-1:0]      prefetch_row,
    output wire                  kv_ok,
    input  wire                  re,
    input  wire [USER_W-1:0]     ruser,
    input  wire [POS_W-1:0]      rrow,
    input  wire [8:0]            relem,
    output reg  [31:0]           q,
    // A packed block can feed the attention engine without a 32-bit-lane
    // re-encoder.  One block is 32 code bytes plus its E8M0 scale byte.
    input  wire                  packed_re,
    input  wire [USER_W-1:0]     packed_ruser,
    input  wire [POS_W-1:0]      packed_rrow,
    input  wire [3:0]            packed_ridx,
    output wire                  packed_valid,
    output wire [4223:0]         packed_row,
    output wire [255:0]          packed_codes,
    output wire [7:0]            packed_scale,
    output reg                   fault,
    output reg  [4:0]            fault_code, // address, order, HBM response, read, poison
    output reg  [31:0]           st_rows_fetched,
    output reg  [31:0]           st_blocks_written,
    output reg  [31:0]           st_sectors_read,
    output reg  [31:0]           st_sectors_written,
    output reg  [3:0]            m_v,
    input  wire [3:0]            m_rdy,
    output reg  [4*HAW-1:0]      m_addr,
    output reg  [4*4-1:0]        m_len,
    output reg  [4*TAGW-1:0]     m_tag,
    output reg  [3:0]            m_we,
    output reg  [4*256-1:0]      m_wdata,
    output reg  [4*32-1:0]       m_wstrb,
    input  wire [3:0]            m_wr_done,
    input  wire [3:0]            s_v,
    output wire [3:0]            s_rdy,
    input  wire [4*TAGW-1:0]     s_tag,
    input  wire [4*4-1:0]        s_beat,
    input  wire [4*256-1:0]      s_data
);
    localparam integer PITCH = 17;
    localparam integer REGION_SECTORS = WINDOW_SLOTS * PITCH;
    localparam [2:0] IDLE = 0, WC = 1, WC_DONE = 2, WS = 3,
                     WS_DONE = 4, FR = 5, FR_DONE = 6;
    reg [2:0] state;
    reg [USER_W-1:0] user_id, active_user;
    reg [POS_W-1:0] row;
    reg [3:0] bidx;
    reg [4:0] sec;
    reg [255:0] codes;
    reg [7:0] scale;
    reg [POS_W-1:0] active_row;
    reg [15:0] block_valid [0:WINDOW_SLOTS-1];
    reg [USER_W-1:0] row_user [0:WINDOW_SLOTS-1];
    reg [POS_W-1:0] row_tag [0:WINDOW_SLOTS-1];
    reg [WINDOW_SLOTS-1:0] row_active, row_valid;
    reg [4223:0] stage [0:WINDOW_SLOTS-1];
    reg [USER_W-1:0] stage_user [0:WINDOW_SLOTS-1];
    reg [POS_W-1:0] stage_tag [0:WINDOW_SLOTS-1];
    reg [WINDOW_SLOTS-1:0] stage_valid;
    wire [6:0] slot = row[6:0];
    wire [6:0] rslot = rrow[6:0];
    wire [6:0] pslot = packed_rrow[6:0];
    wire [6:0] aslot = active_row[6:0];
    wire [SEC_W:0] region_end = {1'b0, region_base_sector} + {1'b0, region_sector_count};
    wire [SEC_W:0] addr_wide = {1'b0, region_base_sector} +
                              (SEC_W+1)'(user_id) * (SEC_W+1)'(REGION_SECTORS) +
                              (SEC_W+1)'(slot) * (SEC_W+1)'(PITCH) + (SEC_W+1)'(sec);
    wire addr_bad = (row >= POS_W'(MAX_CONTEXT)) ||
                    {1'b0, region_sector_count} <
                    ((SEC_W+1)'(user_id) + 1'b1) * (SEC_W+1)'(REGION_SECTORS) ||
                    region_end[SEC_W] || addr_wide[SEC_W] ||
                    (addr_wide >= region_end);
    wire [4223:0] read_row = stage[rslot];
    assign packed_valid = stage_valid[pslot] && stage_tag[pslot] == packed_rrow &&
                          stage_user[pslot] == packed_ruser &&
                          row_valid[pslot] && row_tag[pslot] == packed_rrow &&
                          row_user[pslot] == packed_ruser;
    assign packed_row = packed_valid ? stage[pslot] : '0;
    assign packed_codes = packed_valid ? stage[pslot][256*packed_ridx +: 256] : '0;
    assign packed_scale = packed_valid ? stage[pslot][4096+8*packed_ridx +: 8] : '0;
    function automatic poison_codes(input [255:0] c);
        integer z;
        begin
            poison_codes = 1'b0;
            for (z = 0; z < 32; z = z + 1)
                if (c[8*z +: 7] == 7'h7f) poison_codes = 1'b1;
        end
    endfunction
    wire [31:0] decoded;
    wire dec_fault;
    // The codec is the same one used by the standalone exact-rational gate.
    ot_chip_v41x_window_row_codec #(.POS_W(POS_W), .SEC_W(SEC_W),
        .MAX_CONTEXT(MAX_CONTEXT), .WINDOW_SLOTS(WINDOW_SLOTS)) u_codec (
        .row(read_row), .position(rrow), .region_base_sector(region_base_sector),
        .region_sector_count(region_sector_count), .sector_index(5'd0),
        .sector_address(), .sector_data(), .sector_strobe(), .address_fault(),
        .element_index(relem), .element_fp32(decoded), .element_fault(dec_fault));
    assign blk_ready = state == IDLE;
    assign prime_ready = state == IDLE && !blk_v;
    assign prefetch_ready = state == IDLE && !blk_v && !prime_v;
    assign kv_ok = state == IDLE && stage_valid[aslot] &&
                   stage_tag[aslot] == active_row && stage_user[aslot] == active_user;
    assign s_rdy = 4'hf;
    wire grant = m_rdy[WIN_STACK] && m_v[WIN_STACK];
    wire response = s_v[WIN_STACK];
    wire done_write = m_wr_done[WIN_STACK];

`ifndef SYNTHESIS
    initial begin
        if (WIN_STACK < 0 || WIN_STACK > 3 || WINDOW_SLOTS != 128 ||
            POS_W < 21 || SEC_W < 30 || HAW < SEC_W || TAGW < 5)
            $fatal(1, "packed window KV parameter contract failed");
    end
`endif
    always @(*) begin
        m_v = 0; m_addr = 0; m_len = 0; m_tag = 0; m_we = 0;
        m_wdata = 0; m_wstrb = 0;
        if ((state == WC || state == WS || state == FR) && !addr_bad) begin
            m_v[WIN_STACK] = 1'b1;
            m_addr[WIN_STACK*HAW +: HAW] = HAW'(addr_wide);
            m_len[WIN_STACK*4 +: 4] = 4'd1;
            m_tag[WIN_STACK*TAGW +: TAGW] = TAGW'(sec);
            if (state == WC) begin
                m_we[WIN_STACK] = 1'b1;
                m_wdata[WIN_STACK*256 +: 256] = codes;
                m_wstrb[WIN_STACK*32 +: 32] = 32'hffff_ffff;
            end else if (state == WS) begin
                m_we[WIN_STACK] = 1'b1;
                m_wdata[WIN_STACK*256 +: 256] = 256'(scale) << (8*bidx);
                m_wstrb[WIN_STACK*32 +: 32] = 32'h1 << bidx;
            end
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE; row <= 0; bidx <= 0; sec <= 0; codes <= 0; scale <= 0;
            user_id <= 0; active_row <= 0; active_user <= 0; q <= 0; fault <= 0; fault_code <= 0;
            st_rows_fetched <= 0; st_blocks_written <= 0;
            st_sectors_read <= 0; st_sectors_written <= 0;
            row_active <= 0; row_valid <= 0; stage_valid <= 0;
        end else begin
            if (re) begin
                if (!kv_ok || rrow != active_row || ruser != active_user ||
                    !row_valid[rslot] || row_tag[rslot] != rrow || row_user[rslot] != ruser) begin
                    fault <= 1'b1; fault_code[3] <= 1'b1;
                end else if (dec_fault) begin
                    fault <= 1'b1; fault_code[4] <= 1'b1;
                end else q <= decoded;
            end
            if (packed_re && !packed_valid) begin
                fault <= 1'b1; fault_code[3] <= 1'b1;
            end
            if ((state == WC || state == WS || state == FR) && addr_bad) begin
                fault <= 1'b1; fault_code[0] <= 1'b1; state <= IDLE;
            end else case (state)
                IDLE: begin
                    if (blk_v) begin
                        row <= blk_row; user_id <= blk_user; bidx <= blk_idx; sec <= {1'b0, blk_idx};
                        codes <= blk_codes; scale <= blk_scale;
                        if (blk_row >= POS_W'(MAX_CONTEXT) || blk_scale == 8'hff ||
                            poison_codes(blk_codes) ||
                            {1'b0, region_sector_count} <
                              ((SEC_W+1)'(blk_user) + 1'b1) * (SEC_W+1)'(REGION_SECTORS) ||
                            region_end[SEC_W] ||
                            ((blk_idx != 0) && (!row_active[blk_row[6:0]] ||
                             row_tag[blk_row[6:0]] != blk_row ||
                             row_user[blk_row[6:0]] != blk_user ||
                             block_valid[blk_row[6:0]] != (16'h1 << blk_idx)-1))) begin
                            fault <= 1'b1; fault_code[1] <= 1'b1;
                        end else begin
                            if (blk_idx == 0) begin
                                row_tag[blk_row[6:0]] <= blk_row;
                                row_user[blk_row[6:0]] <= blk_user;
                                block_valid[blk_row[6:0]] <= 0;
                                row_active[blk_row[6:0]] <= 1'b1;
                                row_valid[blk_row[6:0]] <= 0;
                            end
                            stage_valid[blk_row[6:0]] <= 0;
                            state <= WC;
                        end
                    end else if (prime_v) begin
                        if (prime_row >= POS_W'(MAX_CONTEXT) ||
                            {1'b0, region_sector_count} <
                              ((SEC_W+1)'(prime_user) + 1'b1) * (SEC_W+1)'(REGION_SECTORS) ||
                            region_end[SEC_W]) begin
                            fault <= 1'b1; fault_code[0] <= 1'b1;
                        end else begin
                            row_user[prime_row[6:0]] <= prime_user;
                            row_tag[prime_row[6:0]] <= prime_row;
                            row_active[prime_row[6:0]] <= 1'b1;
                            block_valid[prime_row[6:0]] <= 16'hffff;
                            row_valid[prime_row[6:0]] <= 1'b1;
                            stage_valid[prime_row[6:0]] <= 1'b0;
                        end
                    end else if (prefetch_v) begin
                        row <= prefetch_row; user_id <= prefetch_user;
                        active_row <= prefetch_row; active_user <= prefetch_user;
                        sec <= 0;
                        if (prefetch_row >= POS_W'(MAX_CONTEXT) ||
                            !row_valid[prefetch_row[6:0]] ||
                            row_tag[prefetch_row[6:0]] != prefetch_row ||
                            row_user[prefetch_row[6:0]] != prefetch_user ||
                            {1'b0, region_sector_count} <
                              ((SEC_W+1)'(prefetch_user) + 1'b1) * (SEC_W+1)'(REGION_SECTORS) ||
                            region_end[SEC_W]) begin
                            fault <= 1'b1; fault_code[0] <= 1'b1;
                        end else if (!(stage_valid[prefetch_row[6:0]] &&
                            stage_tag[prefetch_row[6:0]] == prefetch_row &&
                            stage_user[prefetch_row[6:0]] == prefetch_user)) begin
                            stage_valid[prefetch_row[6:0]] <= 0;
                            state <= FR;
                        end
                    end
                end
                WC: if (grant) begin
                    st_sectors_written <= st_sectors_written + 1;
                    state <= WC_DONE;
                end
                WC_DONE: if (done_write) begin sec <= 5'd16; state <= WS; end
                WS: if (grant) begin
                    st_sectors_written <= st_sectors_written + 1;
                    state <= WS_DONE;
                end
                WS_DONE: if (done_write) begin
                    block_valid[slot][bidx] <= 1'b1;
                    st_blocks_written <= st_blocks_written + 1;
                    if (bidx == 4'd15) row_valid[slot] <= 1'b1;
                    state <= IDLE;
                end
                FR: if (grant) state <= FR_DONE;
                FR_DONE: if (response) begin
                    if (s_tag[WIN_STACK*TAGW +: TAGW] != TAGW'(sec) ||
                        s_beat[WIN_STACK*4 +: 4] != 0) begin
                        fault <= 1'b1; fault_code[2] <= 1'b1; state <= IDLE;
                    end else begin
                        if (sec < 16) stage[slot][256*sec +: 256] <= s_data[WIN_STACK*256 +: 256];
                        else stage[slot][4096 +: 128] <= s_data[WIN_STACK*256 +: 128];
                        st_sectors_read <= st_sectors_read + 1;
                        if (sec == 5'd16) begin
                            stage_tag[slot] <= row;
                            stage_user[slot] <= user_id;
                            stage_valid[slot] <= 1'b1;
                            st_rows_fetched <= st_rows_fetched + 1;
                            state <= IDLE;
                        end else begin sec <= sec + 1'b1; state <= FR; end
                    end
                end
                default: state <= IDLE;
            endcase
        end
    end
endmodule
