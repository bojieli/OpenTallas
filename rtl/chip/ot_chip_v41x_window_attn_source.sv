`timescale 1ns/1ps
// WINDOW-only packed attention source. Host or core must have published all
// requested packed FP8 rows, then prime their absolute row/user tags. A job
// fetches every row through the actual K/HBM port before publishing any of its
// ordered packed beats. Selected FP4 CKV and remote rows are unsupported.
module ot_chip_v41x_window_attn_source #(
    parameter integer POS_W=21, USER_W=10, SEC_W=30, HAW=30, TAGW=16,
    parameter integer WIN_STACK=0
) (
    input wire clk,rst_n,
    input wire [SEC_W-1:0] region_base_sector,region_sector_count,
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
    input wire [POS_W-1:0] start_first,
    input wire [7:0] start_count,
    output wire staged_v,
    input wire stream_go,
    output wire busy,done,fault,
    output wire [4:0] fault_code,
    output wire [31:0] refill_cycles,sectors_read,
    output wire [31:0] rows_fetched,blocks_written,sectors_written,
    output wire [7:0] rows_refilled,
    output wire kv_v,
    input wire kv_ready,
    output wire [3:0] kv_m,
    output wire [4*16*265-1:0] kv_w,
    output wire [3:0] m_v,
    input wire [3:0] m_rdy,
    output wire [4*HAW-1:0] m_addr,
    output wire [15:0] m_len,
    output wire [4*TAGW-1:0] m_tag,
    output wire [3:0] m_we,
    output wire [1023:0] m_wdata,
    output wire [127:0] m_wstrb,
    input wire [3:0] m_wr_done,
    input wire [3:0] s_v,
    output wire [3:0] s_rdy,
    input wire [4*TAGW-1:0] s_tag,
    input wire [15:0] s_beat,
    input wire [1023:0] s_data
);
    wire pf_v,pf_ready,pf_ok,pf_fault;
    wire [USER_W-1:0] pf_user,issue_user;
    wire [POS_W-1:0] pf_row,issue_first;
    wire issue_v,issue_ready,merge_start_ready,merge_done,merge_fault;
    wire [7:0] issue_count;
    wire prime_ready_i,blk_ready_i;
    wire wb_req_v,wb_req_ready,wb_rsp_v,wb_rsp_fault;
    wire [USER_W-1:0] wb_req_user,wb_rsp_user;
    wire [POS_W-1:0] wb_req_first,wb_rsp_first;
    wire [3:0] wb_req_m,wb_rsp_m,wb_rsp_lane_valid;
    wire [4*4224-1:0] wb_rsp_rows;
    wire [4:0] pf_fault_code;
    assign prime_ready=!busy && prime_ready_i;
    assign blk_ready=!busy && blk_ready_i;
    assign fault=pf_fault | merge_fault | schedule_fault;
    assign fault_code=pf_fault_code | {2'b0,merge_fault,schedule_fault,1'b0};
    wire schedule_fault;
    reg staged_sent;
    assign staged_v=issue_v && !staged_sent;
    assign issue_ready=merge_start_ready && stream_go && staged_sent;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) staged_sent<=1'b0;
        else if (start_v && start_ready) staged_sent<=1'b0;
        else if (staged_v) staged_sent<=1'b1;

    ot_chip_v41x_window_refill_schedule #(.POS_W(POS_W),.USER_W(USER_W)) u_schedule (
        .clk(clk),.rst_n(rst_n),.start_v(start_v),.start_ready(start_ready),
        .start_user(start_user),.start_first(start_first),.start_count(start_count),
        .prefetch_v(pf_v),.prefetch_ready(pf_ready),
        .prefetch_user(pf_user),.prefetch_row(pf_row),
        .prefetch_ok(pf_ok),.prefetch_fault(pf_fault),
        .issue_v(issue_v),.issue_ready(issue_ready),
        .issue_user(issue_user),.issue_first(issue_first),.issue_count(issue_count),
        .issue_done(merge_done),.issue_fault(merge_fault),
        .busy(busy),.done(done),.fault(schedule_fault),
        .refill_cycles(refill_cycles),.rows_refilled(rows_refilled));

    ot_chip_v41x_window_kv_prefetch #(.POS_W(POS_W),.USER_W(USER_W),
        .SEC_W(SEC_W),.HAW(HAW),.TAGW(TAGW),.WIN_STACK(WIN_STACK),
        .BANKED_STAGE(1)) u_window (
        .clk(clk),.rst_n(rst_n),
        .region_base_sector(region_base_sector),
        .region_sector_count(region_sector_count),
        .prime_v(prime_v && prime_ready),.prime_ready(prime_ready_i),
        .prime_user(prime_user),.prime_row(prime_row),
        .blk_v(blk_v && blk_ready),.blk_ready(blk_ready_i),
        .blk_user(blk_user),.blk_row(blk_row),
        .blk_idx(blk_idx),.blk_codes(blk_codes),.blk_scale(blk_scale),
        .prefetch_v(pf_v),.prefetch_ready(pf_ready),
        .prefetch_user(pf_user),.prefetch_row(pf_row),.kv_ok(pf_ok),
        .re(1'b0),.ruser(USER_W'(0)),.rrow(POS_W'(0)),.relem(9'd0),.q(),
        .packed_re(1'b0),.packed_ruser(USER_W'(0)),.packed_rrow(POS_W'(0)),
        .packed_ridx(4'd0),.packed_valid(),.packed_row(),
        .packed_codes(),.packed_scale(),
        .bank_req_v(wb_req_v),.bank_req_ready(wb_req_ready),
        .bank_req_user(wb_req_user),.bank_req_first(wb_req_first),
        .bank_req_mask(wb_req_m),.bank_rsp_v(wb_rsp_v),
        .bank_rsp_user(wb_rsp_user),.bank_rsp_first(wb_rsp_first),
        .bank_rsp_mask(wb_rsp_m),.bank_rsp_valid_mask(wb_rsp_lane_valid),
        .bank_rsp_rows(wb_rsp_rows),.bank_rsp_fault(wb_rsp_fault),
        .fault(pf_fault),.fault_code(pf_fault_code),
        .st_rows_fetched(rows_fetched),.st_blocks_written(blocks_written),
        .st_sectors_read(sectors_read),.st_sectors_written(sectors_written),
        .m_v(m_v),.m_rdy(m_rdy),.m_addr(m_addr),.m_len(m_len),
        .m_tag(m_tag),.m_we(m_we),.m_wdata(m_wdata),.m_wstrb(m_wstrb),
        .m_wr_done(m_wr_done),.s_v(s_v),.s_rdy(s_rdy),
        .s_tag(s_tag),.s_beat(s_beat),.s_data(s_data));

    ot_chip_v41x_attn_row_merge #(.POS_W(POS_W),.USER_W(USER_W)) u_merge (
        .clk(clk),.rst_n(rst_n),.start_v(issue_v && issue_ready),
        .start_ready(merge_start_ready),.start_user(issue_user),
        .window_start_pos(issue_first),.window_count(issue_count),
        .selected_count(10'd0),.published_source_count(POS_W'(0)),
        .win_need(),.win_user(),.win_rrow(),
        .win_packed_valid(1'b0),.win_packed_row(4224'd0),.win_fault(1'b0),
        .wb_req_v(wb_req_v),.wb_req_ready(wb_req_ready),
        .wb_req_user(wb_req_user),.wb_req_first(wb_req_first),
        .wb_req_m(wb_req_m),.wb_rsp_v(wb_rsp_v),
        .wb_rsp_user(wb_rsp_user),.wb_rsp_first(wb_rsp_first),
        .wb_rsp_m(wb_rsp_m),.wb_rsp_lane_valid(wb_rsp_lane_valid),
        .wb_rsp_rows(wb_rsp_rows),.wb_rsp_fault(wb_rsp_fault),
        .selected_id_valid(1'b0),.selected_id_ready(),.selected_source_id(POS_W'(0)),
        .ckv_fetch_v(),.ckv_fetch_ready(1'b0),
        .ckv_fetch_local_row(),.ckv_fetch_source_id(),
        .ckv_packed_valid(1'b0),.ckv_packed_row(2304'd0),
        .ckv_packed_local_row(10'd0),.ckv_packed_source_id(POS_W'(0)),
        .ckv_fault(1'b0),.ckv_remote_needed(1'b0),.ckv_remote_die(2'd0),
        .remote_req_v(),.remote_req_ready(1'b0),
        .remote_req_die(),.remote_req_local_row(),.remote_req_source_id(),
        .remote_rsp_v(1'b0),.remote_rsp_die(2'd0),
        .remote_rsp_local_row(10'd0),.remote_rsp_source_id(POS_W'(0)),
        .remote_rsp_row(2304'd0),.remote_fault(1'b0),
        .kv_v(kv_v),.kv_ready(kv_ready),.kv_m(kv_m),.kv_w(kv_w),
        .done(merge_done),.fault(merge_fault));
endmodule
