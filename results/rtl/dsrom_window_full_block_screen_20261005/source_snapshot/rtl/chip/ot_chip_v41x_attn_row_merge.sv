`timescale 1ns/1ps
// Ordered packed-row bridge to ot_hdc_v41x_attn. This is a functional path:
// upstream window/selected-CKV readers may deliver only one row at a time.
// It does not establish the engine's four-row-per-cycle supply rate.
module ot_chip_v41x_attn_row_merge #(
    parameter integer POS_W = 21,
    parameter integer USER_W = 10,
    parameter integer MAX_CONTEXT = 1048576
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 start_v,
    output wire                 start_ready,
    input  wire [USER_W-1:0]    start_user,
    input  wire [POS_W-1:0]     window_start_pos,
    input  wire [7:0]           window_count,
    input  wire [9:0]           selected_count,
    input  wire [POS_W-1:0]     published_source_count,
    output wire                 win_need,
    output wire [USER_W-1:0]    win_user,
    output wire [POS_W-1:0]     win_rrow,
    input  wire                 win_packed_valid,
    input  wire [4223:0]        win_packed_row,
    input  wire                 win_fault,
    // Optional synchronous four-bank WINDOW read. Full beats use four banks;
    // tails use lane zero from the same registered bank path.
    output wire                 wb_req_v,
    input  wire                 wb_req_ready,
    output wire [USER_W-1:0]    wb_req_user,
    output wire [POS_W-1:0]     wb_req_first,
    output wire [3:0]           wb_req_m,
    input  wire                 wb_rsp_v,
    input  wire [USER_W-1:0]    wb_rsp_user,
    input  wire [POS_W-1:0]     wb_rsp_first,
    input  wire [3:0]           wb_rsp_m,
    input  wire [3:0]           wb_rsp_lane_valid,
    input  wire [4*4224-1:0]    wb_rsp_rows,
    input  wire                 wb_rsp_fault,
    input  wire                 selected_id_valid,
    output wire                 selected_id_ready,
    input  wire [POS_W-1:0]     selected_source_id,
    output wire                 ckv_fetch_v,
    input  wire                 ckv_fetch_ready,
    output wire [9:0]          ckv_fetch_local_row,
    output wire [POS_W-1:0]    ckv_fetch_source_id,
    input  wire                 ckv_packed_valid,
    input  wire [2303:0]        ckv_packed_row,
    input  wire [9:0]           ckv_packed_local_row,
    input  wire [POS_W-1:0]     ckv_packed_source_id,
    input  wire                 ckv_fault,
    input  wire                 ckv_remote_needed,
    input  wire [1:0]           ckv_remote_die,
    output wire                 remote_req_v,
    input  wire                 remote_req_ready,
    output wire [1:0]          remote_req_die,
    output wire [9:0]          remote_req_local_row,
    output wire [POS_W-1:0]    remote_req_source_id,
    input  wire                 remote_rsp_v,
    input  wire [1:0]           remote_rsp_die,
    input  wire [9:0]           remote_rsp_local_row,
    input  wire [POS_W-1:0]     remote_rsp_source_id,
    input  wire [2303:0]        remote_rsp_row,
    input  wire                 remote_fault,
    output wire                 kv_v,
    input  wire                 kv_ready,
    output wire [3:0]           kv_m,
    output wire [4*16*265-1:0] kv_w,
    output reg                  done,
    output reg                  fault
);
    localparam [2:0] IDLE=0, RUN=1, WAIT_CKV=2, REMOTE_REQ=3,
                     WAIT_REMOTE=4, FAULT=5, WAIT_WB=6;
    reg [2:0] state;
    reg [POS_W-1:0] wbase;
    reg [USER_W-1:0] user_id;
    reg [7:0] wcount;
    reg [10:0] total;
    reg [10:0] next_row;
    reg [2:0] nlanes;
    reg [POS_W-1:0] want_source;
    reg [1:0] want_die;
    reg [3:0] wb_pending_m;
    reg [4*16*265-1:0] beat;
    wire [POS_W:0] window_end = {1'b0, window_start_pos} + (POS_W+1)'(window_count);
    wire full = nlanes == 3'd4;
    wire last = (next_row == total) && (nlanes != 0);
    wire room = !full && !last;
    wire [2303:0] ckv_row = (state == WAIT_REMOTE) ? remote_rsp_row : ckv_packed_row;
    wire [16*265-1:0] wfmt, cfmt;
    wire [4*16*265-1:0] wb_fmt;
    genvar g, l;
    generate for (g=0; g<16; g=g+1) begin : g_pack
        assign wfmt[g*265 +: 265] = {1'b0, win_packed_row[4096+8*g +: 8],
                                     win_packed_row[256*g +: 256]};
        assign cfmt[g*265 +: 265] = {1'b1, 120'b0, ckv_row[2048+16*g +: 16],
                                     ckv_row[128*g +: 128]};
    end endgenerate
    generate for (l=0; l<4; l=l+1) begin : g_batch_lane
        for (g=0; g<16; g=g+1) begin : g_batch_group
            assign wb_fmt[(l*16+g)*265 +: 265] =
                {1'b0, wb_rsp_rows[l*4224+4096+8*g +: 8],
                 wb_rsp_rows[l*4224+256*g +: 256]};
        end
    end endgenerate
    assign start_ready = (state == IDLE);
    assign wb_req_v = (state == RUN) && room &&
                      (next_row < {3'b0,wcount});
    assign wb_req_user = user_id;
    assign wb_req_first = wbase + POS_W'(next_row);
    assign wb_req_m = (nlanes == 0 &&
                       ({1'b0,next_row} + 12'd4 <= {4'b0,wcount})) ? 4'hf : 4'h1;
    assign win_need = (state == RUN) && room && (next_row < {3'b0,wcount}) &&
                      !(wb_req_v && wb_req_ready);
    assign win_user = user_id;
    assign win_rrow = wbase + POS_W'(next_row);
    assign selected_id_ready = (state == RUN) && room &&
        (next_row >= {3'b0,wcount}) && (next_row < total) && ckv_fetch_ready;
    assign ckv_fetch_v = selected_id_valid && selected_id_ready &&
                         selected_source_id < published_source_count;
    assign ckv_fetch_local_row = 10'(next_row);
    assign ckv_fetch_source_id = selected_source_id;
    assign remote_req_v = (state == REMOTE_REQ);
    assign remote_req_die = want_die;
    assign remote_req_local_row = 10'(next_row);
    assign remote_req_source_id = want_source;
    assign kv_v = (state == RUN) && (full || last);
    assign kv_m = full ? 4'hf : ((4'b1 << nlanes) - 4'b1);
    assign kv_w = beat;

`ifndef SYNTHESIS
    initial if (POS_W < 21 || MAX_CONTEXT > (1 << POS_W))
        $fatal(1, "attention packed merge parameter contract failed");
`endif
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE; wbase <= 0; user_id <= 0; wcount <= 0; total <= 0;
            next_row <= 0; nlanes <= 0; want_source <= 0; want_die <= 0;
            wb_pending_m <= 0;
            beat <= 0; done <= 0; fault <= 0;
        end else begin
            done <= 0;
            if (state != IDLE && (win_fault || ckv_fault || remote_fault ||
                                  (state == WAIT_WB && wb_rsp_fault))) begin
                fault <= 1; state <= FAULT;
            end else case (state)
                IDLE: if (start_v) begin
                    wbase <= window_start_pos;
                    user_id <= start_user;
                    wcount <= window_count;
                    total <= {3'b0,window_count} + {1'b0,selected_count};
                    next_row <= 0; nlanes <= 0; beat <= 0; fault <= 0;
                    if (window_count > 8'd128 || selected_count > 10'd512 ||
                        ({3'b0,window_count} + {1'b0,selected_count}) > 11'd640 ||
                        window_end > (POS_W+1)'(MAX_CONTEXT)) begin
                        fault <= 1; state <= FAULT;
                    end else if (window_count == 0 && selected_count == 0) begin
                        done <= 1;
                    end else state <= RUN;
                end
                RUN: begin
                    if (kv_v && kv_ready) begin
                        nlanes <= 0; beat <= 0;
                        if (next_row == total) begin done <= 1; state <= IDLE; end
                    end else if (wb_req_v && wb_req_ready) begin
                        wb_pending_m <= wb_req_m;
                        state <= WAIT_WB;
                    end else if (win_need && win_packed_valid) begin
                        beat[nlanes*16*265 +: 16*265] <= wfmt;
                        next_row <= next_row + 1'b1;
                        nlanes <= nlanes + 1'b1;
                    end else if (selected_id_valid && selected_id_ready) begin
                        if (selected_source_id >= published_source_count) begin
                            fault <= 1; state <= FAULT;
                        end else begin
                            want_source <= selected_source_id;
                            want_die <= selected_source_id[5:4];
                            state <= WAIT_CKV;
                        end
                    end
                end
                WAIT_WB: if (wb_rsp_v) begin
                    if (wb_rsp_user != user_id ||
                        wb_rsp_first != wbase + POS_W'(next_row) ||
                        wb_rsp_m != wb_pending_m ||
                        (wb_rsp_lane_valid & wb_pending_m) != wb_pending_m) begin
                        fault <= 1; state <= FAULT;
                    end else begin
                        if (wb_pending_m == 4'hf) begin
                            beat <= wb_fmt;
                            next_row <= next_row + 11'd4;
                            nlanes <= 3'd4;
                        end else begin
                            beat[nlanes*16*265 +: 16*265] <= wb_fmt[0 +: 16*265];
                            next_row <= next_row + 1'b1;
                            nlanes <= nlanes + 1'b1;
                        end
                        state <= RUN;
                    end
                end
                WAIT_CKV: begin
                    if (ckv_remote_needed) begin
                        if (ckv_remote_die != want_die) begin fault <= 1; state <= FAULT; end
                        else state <= REMOTE_REQ;
                    end else if (ckv_packed_valid) begin
                        if (ckv_packed_local_row != 10'(next_row) ||
                            ckv_packed_source_id != want_source) begin fault <= 1; state <= FAULT; end
                        else begin
                            beat[nlanes*16*265 +: 16*265] <= cfmt;
                            next_row <= next_row + 1'b1;
                            nlanes <= nlanes + 1'b1;
                            state <= RUN;
                        end
                    end
                end
                REMOTE_REQ: if (remote_req_ready) state <= WAIT_REMOTE;
                WAIT_REMOTE: if (remote_rsp_v) begin
                    if (remote_rsp_die != want_die ||
                        remote_rsp_local_row != 10'(next_row) ||
                        remote_rsp_source_id != want_source) begin fault <= 1; state <= FAULT; end
                    else begin
                        beat[nlanes*16*265 +: 16*265] <= cfmt;
                        next_row <= next_row + 1'b1;
                        nlanes <= nlanes + 1'b1;
                        state <= RUN;
                    end
                end
                FAULT: state <= FAULT;
                default: begin fault <= 1; state <= FAULT; end
            endcase
        end
    end
endmodule
