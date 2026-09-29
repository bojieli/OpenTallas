`timescale 1ns/1ps
// Local functional service for one V4.1 attention job. WINDOW refill, the
// four-bank packed stage, ordered mixed-row merge and attention engine are
// co-located here; neither 4224-bit packed rows nor the 16960-bit engine KV
// input cross the die boundary. Selected CKV and remote rows are explicit
// inputs and need their own source/transport before a full mixed job is usable.
module ot_chip_v41x_packed_attn_service #(
    parameter integer H=16, D=512, TD=64,
    parameter integer POS_W=21, USER_W=10, SEC_W=30, HAW=30, TAGW=16,
    parameter integer WIN_STACK=0
) (
    input wire clk, rst_n,
    input wire [SEC_W-1:0] region_base_sector, region_sector_count,
    input wire prime_v,
    output wire prime_ready,
    input wire [USER_W-1:0] prime_user,
    input wire [POS_W-1:0] prime_row,
    input wire blk_v,
    output wire blk_ready,
    input wire [USER_W-1:0] blk_user,
    input wire [POS_W-1:0] blk_row,
    input wire [3:0] blk_idx,
    input wire [255:0] blk_codes,
    input wire [7:0] blk_scale,
    input wire start_v,
    output wire start_ready,
    input wire [USER_W-1:0] start_user,
    input wire [POS_W-1:0] start_window_first,
    input wire [7:0] start_window_count,
    input wire [9:0] start_selected_count,
    input wire [POS_W-1:0] published_source_count,
    output wire busy, done, fault,
    output wire [31:0] refill_cycles, sectors_read,
    output wire [7:0] rows_refilled,
    input wire selected_id_valid,
    output wire selected_id_ready,
    input wire [POS_W-1:0] selected_source_id,
    output wire ckv_fetch_v,
    input wire ckv_fetch_ready,
    output wire [9:0] ckv_fetch_local_row,
    output wire [POS_W-1:0] ckv_fetch_source_id,
    input wire ckv_packed_valid,
    input wire [2303:0] ckv_packed_row,
    input wire [9:0] ckv_packed_local_row,
    input wire [POS_W-1:0] ckv_packed_source_id,
    input wire ckv_fault, ckv_remote_needed,
    input wire [1:0] ckv_remote_die,
    output wire remote_req_v,
    input wire remote_req_ready,
    output wire [1:0] remote_req_die,
    output wire [9:0] remote_req_local_row,
    output wire [POS_W-1:0] remote_req_source_id,
    input wire remote_rsp_v,
    input wire [1:0] remote_rsp_die,
    input wire [9:0] remote_rsp_local_row,
    input wire [POS_W-1:0] remote_rsp_source_id,
    input wire [2303:0] remote_rsp_row,
    input wire remote_fault,
    input wire q_v,
    input wire [D*16-1:0] q_w,
    output wire q_ready,
    output wire sc_v,
    output wire [15:0] sc_row,
    output wire [3:0] sc_m,
    output wire [4*H*32-1:0] sc_y,
    output wire [4*H-1:0] sc_f,
    input wire sc_cr,
    input wire p_v,
    input wire [TD*16-1:0] p_w,
    output wire p_ready,
    output wire pv_v,
    output wire [7:0] pv_c,
    output wire [4*(D/TD)*H*32-1:0] pv_y,
    output wire [4*(D/TD)*H-1:0] pv_f,
    input wire pv_cr,
    output wire qk_iss, pv_iss,
    output wire [3:0] m_v,
    input wire [3:0] m_rdy,
    output wire [4*HAW-1:0] m_addr,
    output wire [4*4-1:0] m_len,
    output wire [4*TAGW-1:0] m_tag,
    output wire [3:0] m_we,
    output wire [4*256-1:0] m_wdata,
    output wire [4*32-1:0] m_wstrb,
    input wire [3:0] m_wr_done,
    input wire [3:0] s_v,
    output wire [3:0] s_rdy,
    input wire [4*TAGW-1:0] s_tag,
    input wire [4*4-1:0] s_beat,
    input wire [4*256-1:0] s_data
);
    wire scheduler_busy, scheduler_done, scheduler_fault;
    wire pf_v, pf_ready, pf_ok, pf_fault;
    wire [USER_W-1:0] pf_user, issue_user;
    wire [POS_W-1:0] pf_row, issue_first;
    wire issue_v, issue_ready, merge_start_ready, merge_done, merge_fault;
    wire [7:0] issue_count;
    wire [3:0] wb_req_m, wb_rsp_m, wb_rsp_lane_valid, kv_m;
    wire wb_req_v, wb_req_ready, wb_rsp_v, wb_rsp_fault, kv_v, kv_ready;
    wire [USER_W-1:0] wb_req_user, wb_rsp_user;
    wire [POS_W-1:0] wb_req_first, wb_rsp_first;
    wire [4*4224-1:0] wb_rsp_rows;
    wire [4*16*265-1:0] kv_w;
    wire [31:0] blocks_written, sectors_written, rows_fetched;
    wire [4:0] pf_fault_code;
    wire engine_job_ready;
    reg [9:0] selected_count_hold;
    reg [POS_W-1:0] published_count_hold;
    wire [15:0] job_rows = 16'(issue_count) + 16'(selected_count_hold);
    assign busy = scheduler_busy;
    assign done = scheduler_done;
    assign fault = scheduler_fault | pf_fault | merge_fault;
    assign prime_ready = !scheduler_busy && prime_ready_i;
    assign blk_ready = !scheduler_busy && blk_ready_i;
    wire prime_ready_i, blk_ready_i;
    assign issue_ready = merge_start_ready && engine_job_ready;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            selected_count_hold <= 0;
            published_count_hold <= 0;
        end else if (start_v && start_ready) begin
            selected_count_hold <= start_selected_count;
            published_count_hold <= published_source_count;
        end

    ot_chip_v41x_window_refill_schedule #(.POS_W(POS_W), .USER_W(USER_W)) u_schedule (
        .clk(clk), .rst_n(rst_n), .start_v(start_v), .start_ready(start_ready),
        .start_user(start_user), .start_first(start_window_first),
        .start_count(start_window_count), .prefetch_v(pf_v),
        .prefetch_ready(pf_ready), .prefetch_user(pf_user), .prefetch_row(pf_row),
        .prefetch_ok(pf_ok), .prefetch_fault(pf_fault),
        .issue_v(issue_v), .issue_ready(issue_ready), .issue_user(issue_user),
        .issue_first(issue_first), .issue_count(issue_count),
        .issue_done(merge_done), .issue_fault(merge_fault),
        .busy(scheduler_busy), .done(scheduler_done), .fault(scheduler_fault),
        .refill_cycles(refill_cycles), .rows_refilled(rows_refilled));

    ot_chip_v41x_window_kv_prefetch #(.POS_W(POS_W), .USER_W(USER_W),
        .SEC_W(SEC_W), .HAW(HAW), .TAGW(TAGW), .WIN_STACK(WIN_STACK),
        .BANKED_STAGE(1)) u_window (
        .clk(clk), .rst_n(rst_n),
        .region_base_sector(region_base_sector), .region_sector_count(region_sector_count),
        .prime_v(prime_v && prime_ready), .prime_ready(prime_ready_i),
        .prime_user(prime_user), .prime_row(prime_row),
        .blk_v(blk_v && blk_ready), .blk_ready(blk_ready_i),
        .blk_user(blk_user), .blk_row(blk_row), .blk_idx(blk_idx),
        .blk_codes(blk_codes), .blk_scale(blk_scale),
        .prefetch_v(pf_v), .prefetch_ready(pf_ready),
        .prefetch_user(pf_user), .prefetch_row(pf_row), .kv_ok(pf_ok),
        .re(1'b0), .ruser('0), .rrow('0), .relem('0), .q(),
        .packed_re(1'b0), .packed_ruser('0), .packed_rrow('0),
        .packed_ridx('0), .packed_valid(), .packed_row(),
        .packed_codes(), .packed_scale(),
        .bank_req_v(wb_req_v), .bank_req_ready(wb_req_ready),
        .bank_req_user(wb_req_user), .bank_req_first(wb_req_first),
        .bank_req_mask(wb_req_m), .bank_rsp_v(wb_rsp_v),
        .bank_rsp_user(wb_rsp_user), .bank_rsp_first(wb_rsp_first),
        .bank_rsp_mask(wb_rsp_m), .bank_rsp_valid_mask(wb_rsp_lane_valid),
        .bank_rsp_rows(wb_rsp_rows), .bank_rsp_fault(wb_rsp_fault),
        .fault(pf_fault), .fault_code(pf_fault_code),
        .st_rows_fetched(rows_fetched), .st_blocks_written(blocks_written),
        .st_sectors_read(sectors_read), .st_sectors_written(sectors_written),
        .m_v(m_v), .m_rdy(m_rdy), .m_addr(m_addr), .m_len(m_len),
        .m_tag(m_tag), .m_we(m_we), .m_wdata(m_wdata), .m_wstrb(m_wstrb),
        .m_wr_done(m_wr_done), .s_v(s_v), .s_rdy(s_rdy), .s_tag(s_tag),
        .s_beat(s_beat), .s_data(s_data));

    ot_chip_v41x_attn_row_merge #(.POS_W(POS_W), .USER_W(USER_W)) u_merge (
        .clk(clk), .rst_n(rst_n), .start_v(issue_v && issue_ready),
        .start_ready(merge_start_ready), .start_user(issue_user),
        .window_start_pos(issue_first), .window_count(issue_count),
        .selected_count(selected_count_hold),
        .published_source_count(published_count_hold),
        .win_need(), .win_user(), .win_rrow(),
        .win_packed_valid(1'b0), .win_packed_row('0), .win_fault(1'b0),
        .wb_req_v(wb_req_v), .wb_req_ready(wb_req_ready),
        .wb_req_user(wb_req_user), .wb_req_first(wb_req_first), .wb_req_m(wb_req_m),
        .wb_rsp_v(wb_rsp_v), .wb_rsp_user(wb_rsp_user),
        .wb_rsp_first(wb_rsp_first), .wb_rsp_m(wb_rsp_m),
        .wb_rsp_lane_valid(wb_rsp_lane_valid), .wb_rsp_rows(wb_rsp_rows),
        .wb_rsp_fault(wb_rsp_fault),
        .selected_id_valid(selected_id_valid), .selected_id_ready(selected_id_ready),
        .selected_source_id(selected_source_id),
        .ckv_fetch_v(ckv_fetch_v), .ckv_fetch_ready(ckv_fetch_ready),
        .ckv_fetch_local_row(ckv_fetch_local_row),
        .ckv_fetch_source_id(ckv_fetch_source_id),
        .ckv_packed_valid(ckv_packed_valid), .ckv_packed_row(ckv_packed_row),
        .ckv_packed_local_row(ckv_packed_local_row),
        .ckv_packed_source_id(ckv_packed_source_id),
        .ckv_fault(ckv_fault), .ckv_remote_needed(ckv_remote_needed),
        .ckv_remote_die(ckv_remote_die),
        .remote_req_v(remote_req_v), .remote_req_ready(remote_req_ready),
        .remote_req_die(remote_req_die), .remote_req_local_row(remote_req_local_row),
        .remote_req_source_id(remote_req_source_id),
        .remote_rsp_v(remote_rsp_v), .remote_rsp_die(remote_rsp_die),
        .remote_rsp_local_row(remote_rsp_local_row),
        .remote_rsp_source_id(remote_rsp_source_id), .remote_rsp_row(remote_rsp_row),
        .remote_fault(remote_fault), .kv_v(kv_v), .kv_ready(kv_ready),
        .kv_m(kv_m), .kv_w(kv_w), .done(merge_done), .fault(merge_fault));

    ot_hdc_v41x_attn #(.H(H), .D(D), .TD(TD), .NL(4), .TROWS(640)) u_engine (
        .clk(clk), .rst_n(rst_n), .job_v(issue_v && issue_ready),
        .job_t(job_rows),
        .job_ready(engine_job_ready), .q_v(q_v), .q_w(q_w), .q_ready(q_ready),
        .kv_v(kv_v), .kv_m(kv_m), .kv_w(kv_w), .kv_ready(kv_ready),
        .sc_v(sc_v), .sc_row(sc_row), .sc_m(sc_m), .sc_y(sc_y), .sc_f(sc_f),
        .sc_cr(sc_cr), .p_v(p_v), .p_w(p_w), .p_ready(p_ready),
        .pv_v(pv_v), .pv_c(pv_c), .pv_y(pv_y), .pv_f(pv_f),
        .pv_cr(pv_cr), .qk_iss(qk_iss), .pv_iss(pv_iss));
endmodule
