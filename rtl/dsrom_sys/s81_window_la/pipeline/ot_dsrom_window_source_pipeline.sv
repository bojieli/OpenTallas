`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_dsrom_window_source_pipeline: default-off successor of ot_chip_v41x_window_attn_source_owner_safe
// (rtl/chip/window_owner_safe/, unchanged) for the S81 layer die (claude/dsrom-s81-window-bind-20261004).
//
// This module is selected only by STREAM_LA && WINDOW_PIPELINE in the default-off
// source wrapper. The fallback branch below retains the original source interface.
// The full 128-slot ring is read through the unchanged 32-pseudo-channel stream
// engine and staged in the actual FF-backed pipeline. Golden packed bytes and the
// existing attention row merge are unchanged. Job admission is registered before
// issuing a load. Four row identities are checked per cycle using arithmetic,
// mirror-read and comparison registers. Publication waits for the stream engine's
// identity and poison validation tail to drain, including a zero-row job.
// The K-port writer pipelines prime/block validation and address decode while
// retaining accepted write debt and checking the live region before each issue.
//   Not supported with STREAM_LA = 1: RETAIN_L0 (elaboration error).
//   Contract: the user's ring region must be 32-sector aligned (stream_la faults otherwise), and slots outside
//   a job (count < 128, only positions < 127) must not hold poison bytes (FP8 code 0x7f/0xff, E8M0 0xff): the
//   stream engine checks every landed sector, so a poisoned stale slot fails closed.
// Exactness: bytes are moved, never transformed; tb_dsrom_s81_window_la checks every staged and streamed row
// against the golden packed rows of the 1M token.
// ---------------------------------------------------------------------------
module ot_dsrom_window_source_pipeline #(
    parameter bit STREAM_LA = 0,
    parameter bit REFILL_OWNER_SAFE = 0,
    parameter integer POS_W = 21, USER_W = 10, SEC_W = 30, HAW = 30, TAGW = 16,
    parameter bit RETAIN_L0 = 0,
    parameter integer WIN_STACK = 0, STREAM_II1 = 0, REFILL_CREDITS = 1,
    parameter integer NPC = 32, WTAGW = 13, WLENW = 4, BEATW = 4, LA_IW = 8, LA_ISSUE_PC = 0,
    parameter integer MAX_CONTEXT = 1048576,
    parameter integer SPLIT_COLUMNS = 0
) (
    input wire clk, rst_n,
    input wire retain_qk, retain_pv, retain_complete, retain_invalidate,
    input wire [15:0] retain_generation,
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
    input wire [POS_W-1:0] start_first,
    input wire [7:0] start_count,
    output wire staged_v,
    input wire stream_go,
    output wire busy, done, fault,
    output wire [4:0] fault_code,
    output wire [31:0] refill_cycles, sectors_read,
    output wire [31:0] rows_fetched, blocks_written, sectors_written,
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
    input wire [1023:0] s_data,
    // wide port: client 0 of the WIN_STACK stack's ot_dsrom_hbm_wmux
    output wire [NPC-1:0] wl_req_v,
    input wire [NPC-1:0] wl_req_rdy,
    output wire [NPC*HAW-1:0] wl_req_addr,
    output wire [NPC*WLENW-1:0] wl_req_len,
    output wire [NPC*WTAGW-1:0] wl_req_tag,
    input wire [NPC-1:0] wl_rsp_v,
    output wire [NPC-1:0] wl_rsp_rdy,
    input wire [NPC*WTAGW-1:0] wl_rsp_tag,
    input wire [NPC*BEATW-1:0] wl_rsp_beat,
    input wire [NPC*256-1:0] wl_rsp_data,
    // measurement: cycles from job acceptance to every job row staged (LA), 0 when STREAM_LA = 0
    output wire [31:0] la_load_cycles
);
    generate if (!STREAM_LA) begin : g_asbuilt
        ot_chip_v41x_window_attn_source_owner_safe #(.REFILL_OWNER_SAFE(REFILL_OWNER_SAFE), .POS_W(POS_W),
            .USER_W(USER_W), .SEC_W(SEC_W), .HAW(HAW), .TAGW(TAGW), .RETAIN_L0(RETAIN_L0), .WIN_STACK(WIN_STACK),
            .STREAM_II1(STREAM_II1), .REFILL_CREDITS(REFILL_CREDITS)) u_src (
            .clk(clk), .rst_n(rst_n),
            .retain_qk(retain_qk), .retain_pv(retain_pv), .retain_complete(retain_complete),
            .retain_invalidate(retain_invalidate), .retain_generation(retain_generation),
            .region_base_sector(region_base_sector), .region_sector_count(region_sector_count),
            .prime_v(prime_v), .prime_ready(prime_ready), .prime_user(prime_user), .prime_row(prime_row),
            .blk_v(blk_v), .blk_ready(blk_ready), .blk_user(blk_user), .blk_row(blk_row), .blk_idx(blk_idx),
            .blk_codes(blk_codes), .blk_scale(blk_scale),
            .start_v(start_v), .start_ready(start_ready), .start_user(start_user), .start_first(start_first),
            .start_count(start_count), .staged_v(staged_v), .stream_go(stream_go),
            .busy(busy), .done(done), .fault(fault), .fault_code(fault_code),
            .refill_cycles(refill_cycles), .sectors_read(sectors_read), .rows_fetched(rows_fetched),
            .blocks_written(blocks_written), .sectors_written(sectors_written), .rows_refilled(rows_refilled),
            .kv_v(kv_v), .kv_ready(kv_ready), .kv_m(kv_m), .kv_w(kv_w),
            .m_v(m_v), .m_rdy(m_rdy), .m_addr(m_addr), .m_len(m_len), .m_tag(m_tag), .m_we(m_we),
            .m_wdata(m_wdata), .m_wstrb(m_wstrb), .m_wr_done(m_wr_done),
            .s_v(s_v), .s_rdy(s_rdy), .s_tag(s_tag), .s_beat(s_beat), .s_data(s_data));
        assign wl_req_v = '0; assign wl_req_addr = '0; assign wl_req_len = '0; assign wl_req_tag = '0;
        assign wl_rsp_rdy = '0; assign la_load_cycles = 32'd0;
    end else begin : g_la
`ifndef SYNTHESIS
        initial if (RETAIN_L0 || NPC != 32 || WTAGW < 10 || HAW < SEC_W)
            $fatal(1, "ot_dsrom_window_source_pipeline: STREAM_LA needs RETAIN_L0=0, NPC=32, WTAGW>=10");
`endif
        localparam integer PITCH = 17, REGION_SECTORS = 128 * PITCH;
        localparam [2:0] IDLE = 0, LOAD = 1, ISSUE = 2, RUN = 3, FAILED = 4, ADMIT1=5, ADMIT2=6, ADMIT3=7;
        reg [2:0] st;
        reg [USER_W-1:0] j_user;
        reg [POS_W-1:0] j_first;
        reg [7:0] j_count;
        reg [31:0] load_cyc, load_cyc_q;
        reg staged_sent, done_r, ctl_fault;
        reg [2:0] ctl_code;                       // {region/geometry, tag mirror, merge}
        // ---- pipelined packed-row writer (K port): block writes and priming only ----
        wire wr_prime_ready, wr_blk_ready, wr_pf_ready, wr_fault;
        wire [4:0] wr_code;
        ot_dsrom_window_writer_pipeline #(.REFILL_OWNER_SAFE(REFILL_OWNER_SAFE), .POS_W(POS_W),
            .USER_W(USER_W), .SEC_W(SEC_W), .HAW(HAW), .TAGW(TAGW), .WIN_STACK(WIN_STACK),
            .REFILL_CREDITS(REFILL_CREDITS), .BANKED_STAGE(1)) u_writer (
            .clk(clk), .rst_n(rst_n),
            .region_base_sector(region_base_sector), .region_sector_count(region_sector_count),
            .prime_v(prime_v && prime_ready), .prime_ready(wr_prime_ready),
            .prime_user(prime_user), .prime_row(prime_row),
            .blk_v(blk_v && blk_ready), .blk_ready(wr_blk_ready),
            .blk_user(blk_user), .blk_row(blk_row), .blk_idx(blk_idx), .blk_codes(blk_codes), .blk_scale(blk_scale),
            .prefetch_v(1'b0), .prefetch_ready(wr_pf_ready), .prefetch_user(USER_W'(0)), .prefetch_row(POS_W'(0)),
            .kv_ok(),
            .re(1'b0), .ruser(USER_W'(0)), .rrow(POS_W'(0)), .relem(9'd0), .q(),
            .packed_re(1'b0), .packed_ruser(USER_W'(0)), .packed_rrow(POS_W'(0)), .packed_ridx(4'd0),
            .packed_valid(), .packed_row(), .packed_codes(), .packed_scale(),
            .bank_req_v(1'b0), .bank_req_ready(), .bank_req_user(USER_W'(0)), .bank_req_first(POS_W'(0)),
            .bank_req_mask(4'd0), .bank_rsp_v(), .bank_rsp_user(), .bank_rsp_first(), .bank_rsp_mask(),
            .bank_rsp_valid_mask(), .bank_rsp_rows(), .bank_rsp_fault(),
            .fault(wr_fault), .fault_code(wr_code),
            .st_rows_fetched(), .st_blocks_written(blocks_written), .st_sectors_read(),
            .st_sectors_written(sectors_written),
            .m_v(m_v), .m_rdy(m_rdy), .m_addr(m_addr), .m_len(m_len), .m_tag(m_tag), .m_we(m_we),
            .m_wdata(m_wdata), .m_wstrb(m_wstrb), .m_wr_done(m_wr_done),
            .s_v(s_v), .s_rdy(s_rdy), .s_tag(s_tag), .s_beat(s_beat), .s_data(s_data));
        assign busy = st != IDLE;
        assign prime_ready = !busy && wr_prime_ready;
        assign blk_ready = !busy && wr_blk_ready;
        // ---- tag mirror: the writer's row_valid / row_tag / row_user state, from its accepted traffic ----
        reg [127:0] mv;
        reg [POS_W-1:0] mtag [0:127];
        reg [USER_W-1:0] muser [0:127];
        always @(posedge clk or negedge rst_n)
            if (!rst_n) mv <= 0;
            else begin
                if (prime_v && prime_ready) begin
                    mv[prime_row[6:0]] <= 1'b1; mtag[prime_row[6:0]] <= prime_row; muser[prime_row[6:0]] <= prime_user;
                end else if (blk_v && blk_ready) begin
                    if (blk_idx == 4'd0) begin
                        mv[blk_row[6:0]] <= 1'b0; mtag[blk_row[6:0]] <= blk_row; muser[blk_row[6:0]] <= blk_user;
                    end
                    if (blk_idx == 4'd15) mv[blk_row[6:0]] <= 1'b1;
                end
            end
        // ---- job admission: geometry / region bound (the as-built schedule's and prefetch's checks) ----
        reg [SEC_W-1:0] cfg_base, cfg_count;
        reg [SEC_W:0] region_end, user_plus, required_size, user_offset;
        reg [POS_W:0] end_pos;
        wire start_bad = j_count > 8'd128 || end_pos > (POS_W+1)'(MAX_CONTEXT) || region_end[SEC_W] ||
                         {1'b0,cfg_count}<required_size || cfg_base!=region_base_sector || cfg_count!=region_sector_count;
        wire la_busy, la_fault;
        assign start_ready = st == IDLE && wr_pf_ready && !la_busy && !(ctl_fault || wr_fault);
        wire accept = start_v && start_ready;
        reg [SEC_W-1:0] j_base;
        // ---- tag check, 4 slots a cycle, overlapping the load ----
        reg [5:0] ck_i; reg ck_run, ck_bad, ck_issue;
        reg [1:0] ck_valid;
        reg [POS_W-1:0] ck_row0 [0:3], ck_row1 [0:3], ck_tag1 [0:3];
        reg [USER_W-1:0] ck_user1 [0:3];
        reg [3:0] ck_use0, ck_use1, ck_mv1;
        integer ck_l; reg [8:0] ck_t; reg [POS_W-1:0] ck_r;
        // ---- stream engine + stage ----
        wire [NPC-1:0] st_acc_v; wire [NPC*WTAGW-1:0] st_acc_tag; wire [NPC*BEATW-1:0] st_acc_beat;
        wire [NPC*256-1:0] st_acc_data;
        wire all_rows, stage_fault; wire [11:0] landed;
        reg la_start, stage_job;
        ot_dsrom_window_stream_la_s81 #(.NPC(NPC), .AW(HAW), .TAGW(WTAGW), .LENW(WLENW), .BEATW(BEATW), .IW(LA_IW), .ISSUE_PC(LA_ISSUE_PC)) u_la (
            .clk(clk), .rst_n(rst_n), .start(la_start), .base(HAW'(j_base)), .busy(la_busy), .fault(la_fault),
            .req_v(wl_req_v), .req_rdy(wl_req_rdy), .req_addr(wl_req_addr), .req_len(wl_req_len), .req_tag(wl_req_tag),
            .rsp_v(st_acc_v), .rsp_tag(st_acc_tag), .rsp_beat(st_acc_beat), .rsp_data(st_acc_data));
        wire wb_req_v, wb_req_ready, wb_rsp_v, wb_rsp_fault;
        wire [USER_W-1:0] wb_req_user, wb_rsp_user;
        wire [POS_W-1:0] wb_req_first, wb_rsp_first;
        wire [3:0] wb_req_m, wb_rsp_m, wb_rsp_lane_valid;
        wire [4*4224-1:0] wb_rsp_rows;
        ot_dsrom_window_stage_pipeline #(.POS_W(POS_W), .USER_W(USER_W), .NPC(NPC), .WTAGW(WTAGW), .BEATW(BEATW),
            .MAX_CONTEXT(MAX_CONTEXT), .SPLIT_COLUMNS(SPLIT_COLUMNS)) u_stage (
            .clk(clk), .rst_n(rst_n), .job_v(stage_job), .job_user(j_user), .job_first(j_first),
            .job_count(j_count), .all_rows(all_rows), .sectors_landed(landed), .fault(stage_fault),
            .in_v(wl_rsp_v), .in_rdy(wl_rsp_rdy), .in_tag(wl_rsp_tag), .in_beat(wl_rsp_beat), .in_data(wl_rsp_data),
            .acc_v(st_acc_v), .acc_tag(st_acc_tag), .acc_beat(st_acc_beat), .acc_data(st_acc_data),
            .req_v(wb_req_v), .req_ready(wb_req_ready), .req_user(wb_req_user), .req_first_row(wb_req_first),
            .req_mask(wb_req_m), .rsp_v(wb_rsp_v), .rsp_user(wb_rsp_user), .rsp_first_row(wb_rsp_first),
            .rsp_mask(wb_rsp_m), .rsp_valid_mask(wb_rsp_lane_valid), .rsp_rows(wb_rsp_rows),
            .rsp_fault(wb_rsp_fault));
        wire merge_start_ready, merge_done, merge_fault;
        wire issue_v = st == ISSUE;
        assign staged_v = issue_v && !staged_sent;
        wire issue_ready = merge_start_ready && stream_go && staged_sent;
        if (STREAM_II1) begin : g_stream_ii1
            ot_chip_v41x_window_stream #(.POS_W(POS_W), .USER_W(USER_W)) u_merge (
                .clk(clk), .rst_n(rst_n), .start_v(issue_v && issue_ready), .start_ready(merge_start_ready),
                .start_user(j_user), .start_first(j_first), .start_count(j_count),
                .req_v(wb_req_v), .req_ready(wb_req_ready), .req_user(wb_req_user), .req_first(wb_req_first),
                .req_mask(wb_req_m), .rsp_v(wb_rsp_v), .rsp_user(wb_rsp_user), .rsp_first(wb_rsp_first),
                .rsp_mask(wb_rsp_m), .rsp_valid_mask(wb_rsp_lane_valid), .rsp_rows(wb_rsp_rows),
                .rsp_fault(wb_rsp_fault),
                .kv_v(kv_v), .kv_ready(kv_ready), .kv_m(kv_m), .kv_w(kv_w), .done(merge_done), .fault(merge_fault));
        end else begin : g_compat
            ot_dsrom_window_row_merge_pipeline #(.POS_W(POS_W), .USER_W(USER_W)) u_merge (
                .clk(clk), .rst_n(rst_n), .start_v(issue_v && issue_ready), .start_ready(merge_start_ready),
                .start_user(j_user), .window_start_pos(j_first), .window_count(j_count),
                .selected_count(10'd0), .published_source_count(POS_W'(0)),
                .win_need(), .win_user(), .win_rrow(),
                .win_packed_valid(1'b0), .win_packed_row(4224'd0), .win_fault(1'b0),
                .wb_req_v(wb_req_v), .wb_req_ready(wb_req_ready), .wb_req_user(wb_req_user),
                .wb_req_first(wb_req_first), .wb_req_m(wb_req_m), .wb_rsp_v(wb_rsp_v), .wb_rsp_user(wb_rsp_user),
                .wb_rsp_first(wb_rsp_first), .wb_rsp_m(wb_rsp_m), .wb_rsp_lane_valid(wb_rsp_lane_valid),
                .wb_rsp_rows(wb_rsp_rows), .wb_rsp_fault(wb_rsp_fault),
                .selected_id_valid(1'b0), .selected_id_ready(), .selected_source_id(POS_W'(0)),
                .ckv_fetch_v(), .ckv_fetch_ready(1'b0), .ckv_fetch_local_row(), .ckv_fetch_source_id(),
                .ckv_packed_valid(1'b0), .ckv_packed_row(2304'd0), .ckv_packed_local_row(10'd0),
                .ckv_packed_source_id(POS_W'(0)), .ckv_fault(1'b0), .ckv_remote_needed(1'b0),
                .ckv_remote_die(2'd0), .remote_req_v(), .remote_req_ready(1'b0), .remote_req_die(),
                .remote_req_local_row(), .remote_req_source_id(), .remote_rsp_v(1'b0), .remote_rsp_die(2'd0),
                .remote_rsp_local_row(10'd0), .remote_rsp_source_id(POS_W'(0)), .remote_rsp_row(2304'd0),
                .remote_fault(1'b0), .kv_v(kv_v), .kv_ready(kv_ready), .kv_m(kv_m), .kv_w(kv_w),
                .done(merge_done), .fault(merge_fault));
        end
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin
                st <= IDLE; j_user <= 0; j_first <= 0; j_count <= 0; j_base <= 0; load_cyc <= 0; load_cyc_q <= 0;
                staged_sent <= 0; done_r <= 0; ctl_fault <= 0; ctl_code <= 0; la_start <= 0; stage_job<=0;
                cfg_base<=0; cfg_count<=0; ck_valid<=0; ck_issue<=0;
                ck_i <= 0; ck_run <= 0; ck_bad <= 0;
            end else begin
                done_r <= 1'b0; la_start <= 1'b0; stage_job<=0;
                if (staged_v) staged_sent <= 1'b1;
                if (st != IDLE && st != FAILED && (wr_fault || la_fault || stage_fault || merge_fault)) begin
                    ctl_fault <= 1'b1; if (merge_fault) ctl_code[0] <= 1'b1; st <= FAILED;
                end else case (st)
                    IDLE: if (accept) begin
                        j_user<=start_user; j_first<=start_first; j_count<=start_count;
                        cfg_base<=region_base_sector; cfg_count<=region_sector_count;
                        load_cyc<=0; staged_sent<=0; st<=ADMIT1;
                    end
                    ADMIT1: begin
                        region_end<={1'b0,cfg_base}+{1'b0,cfg_count};
                        user_plus<=(SEC_W+1)'(j_user)+1'b1;
                        end_pos<={1'b0,j_first}+(POS_W+1)'(j_count); st<=ADMIT2;
                    end
                    ADMIT2: begin
                        required_size<=(user_plus<<11)+(user_plus<<7);
                        user_offset<=((SEC_W+1)'(j_user)<<11)+((SEC_W+1)'(j_user)<<7); st<=ADMIT3;
                    end
                    ADMIT3: begin
                        j_base<=cfg_base+user_offset[SEC_W-1:0];
                        ck_i<=0; ck_run<=1; ck_issue<=1; ck_bad<=0;
                        if(start_bad) begin ctl_fault<=1; ctl_code[2]<=1; st<=FAILED; end
                        else begin la_start<=1; stage_job<=1; st<=LOAD; end
                    end
                    LOAD: begin
                        load_cyc <= load_cyc + 1;
                        if (!ck_run && ck_bad) begin ctl_fault <= 1'b1; ctl_code[1] <= 1'b1; st <= FAILED; end
                        else if (!ck_run && all_rows && !la_start && !la_busy) begin load_cyc_q <= load_cyc + 1; st <= ISSUE; end
                    end
                    ISSUE: if (issue_ready) st <= RUN;
                    RUN: if (merge_done) begin done_r <= 1'b1; st <= IDLE; end
                    FAILED: st <= FAILED;
                    default: begin ctl_fault <= 1'b1; st <= FAILED; end
                endcase
                // Register row arithmetic, tag-memory read and comparison separately.
                // ck_run remains asserted until the last qualified comparison drains.
                ck_valid<={ck_valid[0],ck_issue};
                if(ck_issue) begin
                    for(ck_l=0;ck_l<4;ck_l=ck_l+1) begin
                        ck_t={ck_i,2'b00}+ck_l;
                        ck_row0[ck_l]<=j_first+ck_t;
                        ck_use0[ck_l]<=ck_t<j_count;
                    end
                    ck_i<=ck_i+1'b1;
                    if(ck_i==31) ck_issue<=0;
                end
                if(ck_valid[0]) for(ck_l=0;ck_l<4;ck_l=ck_l+1) begin
                    ck_row1[ck_l]<=ck_row0[ck_l]; ck_use1[ck_l]<=ck_use0[ck_l];
                    ck_tag1[ck_l]<=mtag[ck_row0[ck_l][6:0]];
                    ck_user1[ck_l]<=muser[ck_row0[ck_l][6:0]];
                    ck_mv1[ck_l]<=mv[ck_row0[ck_l][6:0]];
                end
                if(ck_valid[1]) for(ck_l=0;ck_l<4;ck_l=ck_l+1)
                    if(ck_use1[ck_l] && (!ck_mv1[ck_l] || ck_tag1[ck_l]!=ck_row1[ck_l] || ck_user1[ck_l]!=j_user)) ck_bad<=1;
                if(ck_run && !ck_issue && ck_valid==0) ck_run<=0;
            end
        end
        assign done = done_r;
        assign fault = ctl_fault || wr_fault || la_fault || stage_fault;
        assign fault_code = wr_code | {la_fault || stage_fault, 1'b0, ctl_code};
        assign refill_cycles = load_cyc_q;
        assign la_load_cycles = load_cyc_q;
        assign sectors_read = 32'(landed);
        assign rows_fetched = 32'(st == IDLE || st == ISSUE || st == RUN ? j_count : 8'd0);
        assign rows_refilled = j_count;
    end endgenerate
endmodule
