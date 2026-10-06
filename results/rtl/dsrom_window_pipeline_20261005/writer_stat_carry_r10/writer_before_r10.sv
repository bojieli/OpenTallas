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
// The connected successor uses only prime and block-write commands on the
// K port; the original refill/read interface is retained but must remain idle.
// Captured metadata, poison/order/bounds checks and address decode are split
// across registers. Each issue checks the captured region against the live
// region. Once accepted, write debt drains before publication even if that
// region changes. The functional result does not establish the bandwidth/rate
// of the 640-row mixed attention path.
module ot_dsrom_window_writer_pipeline #(
    parameter bit REFILL_OWNER_SAFE = 0,
    parameter integer POS_W = 21,
    parameter integer SEC_W = 30,
    parameter integer HAW = 30,
    parameter integer TAGW = 16,
    parameter integer USER_W = 10,
    parameter bit BANKED_STAGE = 0,
    parameter integer WIN_STACK = 0,
    parameter integer REFILL_CREDITS = 1,
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
    // Optional registered four-bank row path.  It accepts one four-row
    // request per cycle after the rows are staged.  The legacy packed_re
    // combinational read is disabled when BANKED_STAGE=1.
    input  wire                  bank_req_v,
    output wire                  bank_req_ready,
    input  wire [USER_W-1:0]     bank_req_user,
    input  wire [POS_W-1:0]      bank_req_first,
    input  wire [3:0]            bank_req_mask,
    output wire                  bank_rsp_v,
    output wire [USER_W-1:0]     bank_rsp_user,
    output wire [POS_W-1:0]      bank_rsp_first,
    output wire [3:0]            bank_rsp_mask,
    output wire [3:0]            bank_rsp_valid_mask,
    output wire [4*4224-1:0]    bank_rsp_rows,
    output wire                  bank_rsp_fault,
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
    reg [3:0] state;
    localparam [3:0] CHECK1=8, CHECK2=9, CHECK3=10, ADDR1=11, ADDR2=12, ADDR3=13;
    reg command_prime;
    reg [SEC_W-1:0] cfg_base, cfg_count;
    reg [SEC_W:0] cfg_end, user_plus, required_size, user_offset, slot_offset, row_base, checked_addr;
    reg check_payload_bad, check_identity_bad;
    reg meta_active;
    reg [POS_W-1:0] meta_tag;
    reg [USER_W-1:0] meta_user;
    reg [15:0] meta_blocks;
    wire config_matches = cfg_base == region_base_sector && cfg_count == region_sector_count;
    // A captured address is permission only while its originating live region matches.
    // Responses to already accepted writes always drain via WC_DONE/WS_DONE.

    localparam [2:0] FR_PIPE = 7;
    // Client tags enter an outer two-owner-bit mux. Never spend owner bits
    // on epoch identity. Modulo reuse is legal only after all17 old sectors
    // have completed uniquely; reset additionally requires endpoint drain.
    localparam integer EPOCH_W = REFILL_OWNER_SAFE ?
        (TAGW > 7 ? TAGW-7 : 1) : (TAGW > 5 ? TAGW-5 : 1);
    reg [EPOCH_W-1:0] refill_epoch;
    reg [16:0] refill_issued, refill_received;
    reg [4:0] refill_next, refill_pending;
    wire [4:0] reply_sector = s_tag[WIN_STACK*TAGW +: 5];
    wire reply_epoch_ok = (s_tag[WIN_STACK*TAGW +: TAGW] >> 5) == refill_epoch;
    wire pipe_reply_ok = state == FR_PIPE && !fault && response &&
        reply_sector <= 16 && reply_epoch_ok &&
        refill_issued[reply_sector] && !refill_received[reply_sector] &&
        s_beat[WIN_STACK*4 +: 4] == 0 && !response_poison;
    wire pipe_issue = state == FR_PIPE && !fault && refill_pending < REFILL_CREDITS &&
        (refill_next < 16 || (refill_next == 16 && refill_received[15:0] == 16'hffff));
    wire [4:0] fill_sector_index = state == FR_PIPE ? reply_sector : sec;
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
    wire [SEC_W:0] addr_wide = checked_addr;
    wire addr_bad = !config_matches || cfg_end[SEC_W] || checked_addr[SEC_W] || checked_addr >= cfg_end;
    wire [4223:0] read_row = BANKED_STAGE ? '0 : stage[rslot];
    assign packed_valid = !BANKED_STAGE && stage_valid[pslot] && stage_tag[pslot] == packed_rrow &&
                          stage_user[pslot] == packed_ruser &&
                          row_valid[pslot] && row_tag[pslot] == packed_rrow &&
                          row_user[pslot] == packed_ruser;
    assign packed_row = packed_valid ? stage[pslot] : '0;
    assign packed_codes = packed_valid ? stage[pslot][256*packed_ridx +: 256] : '0;
    assign packed_scale = packed_valid ? stage[pslot][4096+8*packed_ridx +: 8] : '0;
    generate if (BANKED_STAGE) begin : g_bank_stage
        wire fill_ok = pipe_reply_ok || (state == FR_DONE && response && !response_poison &&
            s_tag[WIN_STACK*TAGW +: TAGW] == TAGW'(sec) &&
            s_beat[WIN_STACK*4 +: 4] == 0);
        ot_chip_v41x_window_stage4 #(.POS_W(POS_W), .USER_W(USER_W),
            .MAX_CONTEXT(MAX_CONTEXT)) u_stage4 (
            .clk(clk), .rst_n(rst_n),
            .inv_v((blk_v && blk_ready) || (prime_v && prime_ready) ||
                   (prefetch_v && prefetch_ready)),
            .inv_row((blk_v && blk_ready) ? blk_row :
                     (prime_v && prime_ready) ? prime_row : prefetch_row),
            .fill_v(fill_ok), .fill_user(user_id), .fill_row(row),
            .fill_sector(fill_sector_index), .fill_data(s_data[WIN_STACK*256 +: 256]),
            .fill_last(fill_sector_index == 5'd16),
            .req_v(bank_req_v), .req_ready(bank_req_ready),
            .req_user(bank_req_user), .req_first_row(bank_req_first),
            .req_mask(bank_req_mask), .rsp_v(bank_rsp_v),
            .rsp_user(bank_rsp_user), .rsp_first_row(bank_rsp_first),
            .rsp_mask(bank_rsp_mask), .rsp_valid_mask(bank_rsp_valid_mask),
            .rsp_rows(bank_rsp_rows), .rsp_fault(bank_rsp_fault));
    end else begin : g_legacy_stage
        assign bank_req_ready = 1'b0;
        assign bank_rsp_v = 1'b0;
        assign bank_rsp_user = '0; assign bank_rsp_first = '0;
        assign bank_rsp_mask = '0; assign bank_rsp_valid_mask = '0;
        assign bank_rsp_rows = 16896'h0; assign bank_rsp_fault = 1'b0;
    end endgenerate
    function automatic poison_codes(input [255:0] c);
        integer z;
        begin
            poison_codes = 1'b0;
            for (z = 0; z < 32; z = z + 1)
                if (c[8*z +: 7] == 7'h7f) poison_codes = 1'b1;
        end
    endfunction
    function automatic poison_scales(input [127:0] s);
        integer z;
        begin
            poison_scales = 1'b0;
            for (z = 0; z < 16; z = z + 1)
                if (s[8*z +: 8] == 8'hff) poison_scales = 1'b1;
        end
    endfunction
    wire response_poison = (fill_sector_index < 5'd16) ?
        poison_codes(s_data[WIN_STACK*256 +: 256]) :
        poison_scales(s_data[WIN_STACK*256 +: 128]);
    wire [31:0] decoded;
    wire dec_fault;
    // The codec is the same one used by the standalone exact-rational gate.
    ot_chip_v41x_window_row_codec #(.POS_W(POS_W), .SEC_W(SEC_W),
        .MAX_CONTEXT(MAX_CONTEXT), .WINDOW_SLOTS(WINDOW_SLOTS)) u_codec (
        .row(read_row), .position(rrow), .region_base_sector(region_base_sector),
        .region_sector_count(region_sector_count), .sector_index(5'd0),
        .sector_address(), .sector_data(), .sector_strobe(), .address_fault(),
        .element_index(relem), .element_fp32(decoded), .element_fault(dec_fault));
    assign blk_ready = state == IDLE && (REFILL_CREDITS == 1 || !fault);
    assign prime_ready = state == IDLE && (REFILL_CREDITS == 1 || !fault) && !blk_v;
    assign prefetch_ready = state == IDLE && (REFILL_CREDITS == 1 || !fault) && !blk_v && !prime_v;
    assign kv_ok = (REFILL_CREDITS == 1 || !fault) && state == IDLE && stage_valid[aslot] &&
                   stage_tag[aslot] == active_row && stage_user[aslot] == active_user;
    assign s_rdy = 4'hf;
    wire grant = m_rdy[WIN_STACK] && m_v[WIN_STACK];
    wire response = s_v[WIN_STACK];
    wire done_write = m_wr_done[WIN_STACK];

`ifndef SYNTHESIS
    // This writer is the minimum source-faithful write/prime vehicle; refill is
    // served exclusively by the connected wide-load engine.
    always @(posedge clk) if (rst_n && prefetch_v) $fatal(1,"pipeline writer has no refill caller");
    initial begin
        if (WIN_STACK < 0 || WIN_STACK > 3 || WINDOW_SLOTS != 128 ||
            POS_W < 21 || SEC_W < 30 || HAW < SEC_W || TAGW < 5 || (REFILL_CREDITS > 1 && TAGW < 6) ||
            (REFILL_OWNER_SAFE && REFILL_CREDITS > 1 && TAGW < 8) ||
            REFILL_CREDITS < 1 || REFILL_CREDITS > 16)
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
        if (pipe_issue && !addr_bad) begin
            m_v[WIN_STACK] = 1'b1;
            m_addr[WIN_STACK*HAW +: HAW] = HAW'(addr_wide - (SEC_W+1)'(sec) + (SEC_W+1)'(refill_next));
            m_len[WIN_STACK*4 +: 4] = 1;
            m_tag[WIN_STACK*TAGW +: TAGW] = TAGW'({refill_epoch, refill_next});
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            refill_epoch <= 0; refill_issued <= 0; refill_received <= 0;
            refill_next <= 0; refill_pending <= 0;
            command_prime <= 0; cfg_base <= 0; cfg_count <= 0; cfg_end <= 0; checked_addr <= 0;
            state <= IDLE; row <= 0; bidx <= 0; sec <= 0; codes <= 0; scale <= 0;
            user_id <= 0; active_row <= 0; active_user <= 0; q <= 0; fault <= 0; fault_code <= 0;
            st_rows_fetched <= 0; st_blocks_written <= 0;
            st_sectors_read <= 0; st_sectors_written <= 0;
            row_active <= 0; row_valid <= 0; stage_valid <= 0;
        end else begin
            if (re) begin
                if (BANKED_STAGE || !kv_ok || rrow != active_row || ruser != active_user ||
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
                    if (blk_v || prime_v) begin
                        command_prime <= !blk_v;
                        row <= blk_v ? blk_row : prime_row;
                        user_id <= blk_v ? blk_user : prime_user;
                        bidx <= blk_idx; sec <= {1'b0, blk_idx};
                        codes <= blk_codes; scale <= blk_scale;
                        cfg_base <= region_base_sector; cfg_count <= region_sector_count;
                        state <= CHECK1;
                    end
                end
                CHECK1: begin
                    cfg_end <= {1'b0,cfg_base} + {1'b0,cfg_count};
                    user_plus <= (SEC_W+1)'(user_id) + 1'b1;
                    check_payload_bad <= row >= POS_W'(MAX_CONTEXT) ||
                        (!command_prime && (scale == 8'hff || poison_codes(codes)));
                    meta_active <= row_active[slot]; meta_tag <= row_tag[slot];
                    meta_user <= row_user[slot]; meta_blocks <= block_valid[slot];
                    state <= CHECK2;
                end
                CHECK2: begin
                    required_size <= (user_plus << 11) + (user_plus << 7);
                    user_offset <= ((SEC_W+1)'(user_id) << 11) + ((SEC_W+1)'(user_id) << 7);
                    slot_offset <= ((SEC_W+1)'(slot) << 4) + (SEC_W+1)'(slot);
                    check_identity_bad <= !command_prime && bidx != 0 &&
                        (!meta_active || meta_tag != row || meta_user != user_id ||
                         meta_blocks != (16'h1 << bidx)-1);
                    state <= CHECK3;
                end
                CHECK3: begin
                    if (check_payload_bad || check_identity_bad || cfg_end[SEC_W] ||
                        {1'b0,cfg_count} < required_size || !config_matches) begin
                        fault <= 1'b1;
                        if (command_prime) fault_code[0] <= 1'b1;
                        else fault_code[1] <= 1'b1;
                        state <= IDLE;
                    end else if (command_prime) begin
                        row_user[slot] <= user_id; row_tag[slot] <= row;
                        row_active[slot] <= 1'b1; block_valid[slot] <= 16'hffff;
                        row_valid[slot] <= 1'b1; stage_valid[slot] <= 1'b0;
                        state <= IDLE;
                    end else begin
                        if (bidx == 0) begin
                            row_tag[slot] <= row; row_user[slot] <= user_id;
                            block_valid[slot] <= 0; row_active[slot] <= 1'b1; row_valid[slot] <= 0;
                        end
                        stage_valid[slot] <= 0; state <= ADDR1;
                    end
                end
                ADDR1: begin row_base <= {1'b0,cfg_base} + user_offset; state <= ADDR2; end
                ADDR2: begin row_base <= row_base + slot_offset; state <= ADDR3; end
                ADDR3: begin checked_addr <= row_base + (SEC_W+1)'(sec); state <= sec == 16 ? WS : WC; end
                WC: if (grant) begin
                    st_sectors_written <= st_sectors_written + 1;
                    state <= WC_DONE;
                end
                WC_DONE: if (done_write) begin sec <= 5'd16; state <= ADDR3; end
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
                    end else if (response_poison) begin
                        fault <= 1'b1; fault_code[4] <= 1'b1; state <= IDLE;
                    end else begin
                        if (!BANKED_STAGE) begin
                            if (sec < 16) stage[slot][256*sec +: 256] <= s_data[WIN_STACK*256 +: 256];
                            else stage[slot][4096 +: 128] <= s_data[WIN_STACK*256 +: 128];
                        end
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
                FR_PIPE: if (!fault) begin
                    if (addr_bad) begin fault <= 1; fault_code[0] <= 1; end
                    else begin
                        case ({grant, pipe_reply_ok})
                            2'b10: refill_pending <= refill_pending + 1'b1;
                            2'b01: refill_pending <= refill_pending - 1'b1;
                            default: begin end
                        endcase
                        if (grant) begin
                            refill_issued[refill_next] <= 1'b1;
                            refill_next <= refill_next + 1'b1;
                        end
                        if (response) begin
                            if (!pipe_reply_ok) begin fault <= 1; fault_code[2] <= 1; end
                            else begin
                                refill_received[reply_sector] <= 1'b1;
                                st_sectors_read <= st_sectors_read + 1;
                                if (!BANKED_STAGE) begin
                                    if (reply_sector < 16) stage[slot][256*reply_sector +: 256] <= s_data[WIN_STACK*256 +: 256];
                                    else stage[slot][4096 +: 128] <= s_data[WIN_STACK*256 +: 128];
                                end
                                if (reply_sector == 16) begin
                                    stage_tag[slot] <= row; stage_user[slot] <= user_id;
                                    stage_valid[slot] <= 1; st_rows_fetched <= st_rows_fetched + 1;
                                    state <= IDLE;
                                end
                            end
                        end
                    end
                end
                default: state <= IDLE;
            endcase
        end
    end
endmodule
