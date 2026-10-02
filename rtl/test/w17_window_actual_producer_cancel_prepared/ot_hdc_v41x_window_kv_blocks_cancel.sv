module does not drive the old scalar KVT write port.
module ot_hdc_v41x_window_kv_blocks_cancel #(
    parameter integer OPT_CANCEL = 0,
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
    output wire              fault,
    input wire rec_freeze,
    input wire rec_cancel,
    input wire rec_token,
    input wire rec_suffix_closed,
    input wire rec_qe_idle,
    input wire rec_rearm,
    input wire rec_retired_certified,
    output wire rec_cancel_ack,
    output wire rec_cancel_token_ack
);
generate if (!OPT_CANCEL) begin : g_default
ot_hdc_v41x_window_kv_blocks_cancel_legacy #(.AW(AW), .POS_W(POS_W), .KVT_SH(KVT_SH), .SEPARATE_ROWS(SEPARATE_ROWS)) u_impl (
    .clk(clk),
    .rst_n(rst_n),
    .cap_v(cap_v),
    .cap_src_addr(cap_src_addr),
    .cap_codes(cap_codes),
    .cap_scale(cap_scale),
    .cap_ready(cap_ready),
    .cap_src_base(cap_src_base),
    .idle(idle),
    .issue(issue),
    .issue_src_base(issue_src_base),
    .issue_kvt_base(issue_kvt_base),
    .issue_row(issue_row),
    .issue_abs_row(issue_abs_row),
    .issue_ready(issue_ready),
    .blk_v(blk_v),
    .blk_ready(blk_ready),
    .blk_kvt_base(blk_kvt_base),
    .blk_row(blk_row),
    .blk_kvt_row(blk_kvt_row),
    .blk_idx(blk_idx),
    .blk_first_elem(blk_first_elem),
    .blk_codes(blk_codes),
    .blk_scale(blk_scale),
    .fault(fault));
assign rec_cancel_ack=0; assign rec_cancel_token_ack=0;
end else begin : g_cancel
ot_hdc_v41x_window_kv_blocks_cancel_enabled #(.AW(AW), .POS_W(POS_W), .KVT_SH(KVT_SH), .SEPARATE_ROWS(SEPARATE_ROWS)) u_impl (
    .clk(clk),
    .rst_n(rst_n),
    .cap_v(cap_v),
    .cap_src_addr(cap_src_addr),
    .cap_codes(cap_codes),
    .cap_scale(cap_scale),
    .cap_ready(cap_ready),
    .cap_src_base(cap_src_base),
    .idle(idle),
    .issue(issue),
    .issue_src_base(issue_src_base),
    .issue_kvt_base(issue_kvt_base),
    .issue_row(issue_row),
    .issue_abs_row(issue_abs_row),
    .issue_ready(issue_ready),
    .blk_v(blk_v),
    .blk_ready(blk_ready),
    .blk_kvt_base(blk_kvt_base),
    .blk_row(blk_row),
    .blk_kvt_row(blk_kvt_row),
    .blk_idx(blk_idx),
    .blk_first_elem(blk_first_elem),
    .blk_codes(blk_codes),
    .blk_scale(blk_scale),
    .fault(fault),
    .rec_freeze(rec_freeze),
    .rec_cancel(rec_cancel),
    .rec_token(rec_token),
    .rec_suffix_closed(rec_suffix_closed),
    .rec_qe_idle(rec_qe_idle),
    .rec_rearm(rec_rearm),
    .rec_retired_certified(rec_retired_certified),
    .rec_cancel_ack(rec_cancel_ack),
    .rec_cancel_token_ack(rec_cancel_token_ack));
end endgenerate
endmodule

module does not drive the old scalar KVT write port.
module ot_hdc_v41x_window_kv_blocks_cancel_legacy #(
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

module does not drive the old scalar KVT write port.
module ot_hdc_v41x_window_kv_blocks_cancel_enabled #(
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
    output reg               fault,
    input wire rec_freeze,
    input wire rec_cancel,
    input wire rec_token,
    input wire rec_suffix_closed,
    input wire rec_qe_idle,
    input wire rec_rearm,
    input wire rec_retired_certified,
    output reg rec_cancel_ack,
    output reg rec_cancel_token_ack
);
    localparam [1:0] EMPTY = 0, FILL = 1, FULL = 2, DRAIN = 3;
`ifndef SYNTHESIS
    initial if (AW < 30 || POS_W < 21 || KVT_SH < $clog2(16*512))
        $fatal(1, "full-shape window KV needs AW>=30, POS_W>=21, KVT_SH>=13");
`endif
    // Adapter holds rec_freeze independently of token-start-cleared core fault.
    // rec_cancel covers only local metadata, NEVER WINDOW or provider intent.
    wire rec_stop = rec_freeze || fault;
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
    wire rec_local_bad = (cap_v && (!((state == EMPTY || state == FILL) && count < 5'd16) || cap_scale == 8'hff || (state == FILL && (cap_expected[AW] || cap_src_addr != cap_expected[AW-1:0])) || cap_src_addr[4:0] != 5'd0)) || (issue && (state != FULL || issue_src_base != src_base || issue_abs >= POS_W'(1048576) || (SEPARATE_ROWS && issue_row >= POS_W'(128)) || issue_last_wide[AW])) || (cap_v && issue);
    assign cap_ready = !rec_stop && (state == EMPTY || state == FILL) && count < 5'd16;
    assign cap_src_base = src_base;
    assign idle = state == EMPTY;
    assign issue_ready = !rec_stop && state == FULL;
    assign blk_v = !rec_stop && !rec_local_bad && state == DRAIN;
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
            rec_cancel_ack <= 0; rec_cancel_token_ack <= 0;
        end else if (rec_cancel) begin
            // No local reset: preserve sticky cause and accepted downstream work.
            if (rec_rearm || !(rec_freeze && rec_suffix_closed && rec_qe_idle)) begin
                fault <= 1'b1;
            end else if (!rec_cancel_ack) begin
                state <= EMPTY; count <= 0; rd_idx <= 0;
                rec_cancel_ack <= 1'b1; rec_cancel_token_ack <= rec_token;
            end else if (rec_cancel_token_ack != rec_token) begin
                fault <= 1'b1; // cannot turn an outstanding receipt into a new one
            end
        end else if (rec_rearm) begin
            // Certified means local+selected-owner retirement AND causal fences.
            // No such physical provider exists in current source; never use timer.
            if (rec_cancel_ack && rec_freeze && rec_suffix_closed && rec_qe_idle &&
                rec_retired_certified && rec_cancel_token_ack == rec_token) begin
                fault <= 1'b0; rec_cancel_ack <= 1'b0;
            end else fault <= 1'b1;
        end else begin
            if (cap_v && !rec_stop && !rec_local_bad) begin
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
            if (issue && !rec_stop && !rec_local_bad) begin
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
            if (!rec_stop && rec_local_bad) fault <= 1'b1;
            if (blk_v && blk_ready && !rec_local_bad) begin
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
