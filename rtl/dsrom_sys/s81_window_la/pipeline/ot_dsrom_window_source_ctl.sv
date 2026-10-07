`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_dsrom_window_source_ctl: the control leaf of ot_dsrom_window_source_pipeline (STREAM_LA branch) as its
// own hardened block (takeover-ds, 2026-10-06).  It holds the K-port writer, the tag mirror, the 32-channel
// stream engine and the job FSM.  The staging array (ot_dsrom_window_stage_pipeline + 68 columns) and the
// row merge are separate neighbours reached through explicit ports; the HBM wmux belongs to the HBM service.
//
// MARGIN = 0: the original body, cycle for cycle (only the hierarchy cut moves).
// MARGIN = 1 (margin-first boundary, priced in tools/uarch_model.py dsrom_window_source_ctl_margin_model):
//   * configuration, status and response inputs are flopped at the pin (region_*, m_wr_done, s_*, the
//     stage's all_rows/landed/fault, the merge's ready/done/fault, stream_go);
//   * prime / blk / start and the K-port write request pass 2-entry skid buffers whose ready is a flop;
//   * every output is a flop.  The registered region is the "live" region of the original checks (an
//     upstream retime), accepted write debt still drains.  No register sits inside a one-cycle loop.
// Bytes are moved, never transformed.  Exactness: tools/dsrom_window_pipeline_gate.py --ctl-leaf.
// ---------------------------------------------------------------------------
module ot_dsrom_window_skid #(parameter integer W = 1, parameter bit ZERO_IDLE = 0,
    // PTR = 1 (MARGIN 2): the same two-entry skid (identical valid / ready / head-data timing) built as a pointer
    // FIFO: a push writes one slot, a pop only moves the read pointer, so no payload register ever depends on the
    // consumer's ready (the shift form's e0_d <= e1_d made every payload bit an endpoint of out_ready).
    parameter bit PTR = 0) (
    input  wire         clk, rst_n,
    input  wire         in_v,
    output wire         in_ready,
    input  wire [W-1:0] in_d,
    output wire         out_v,
    input  wire         out_ready,
    output wire [W-1:0] out_d
);
    reg e0_v, e1_v;
    reg [W-1:0] e0_d, e1_d;
`ifdef OT_WINDOW_CTL_MUTANT_LATE_PAYLOAD
    // negative control: the request slice captures its payload one edge after its valid
    reg [W-1:0] d_late;
    always @(posedge clk) d_late <= in_d;
    wire [W-1:0] cap_d = ZERO_IDLE ? d_late : in_d;
`else
    wire [W-1:0] cap_d = in_d;
`endif
    reg rdy_q;                                // = !e1_v outside reset; low in reset
    assign in_ready = rdy_q;
    assign out_v = e0_v;
    wire push = in_v && rdy_q;
    wire pop = e0_v && out_ready;
    wire e1_next = pop ? (e1_v && push) : (push ? e0_v : e1_v);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) rdy_q <= 1'b0; else rdy_q <= !e1_next;
    generate if (PTR) begin : g_ptr
        reg wp, rp;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin e0_v <= 1'b0; e1_v <= 1'b0; wp <= 1'b0; rp <= 1'b0; end
            else begin
                if (pop) begin
                    if (e1_v) e1_v <= push; else e0_v <= push;
                end else if (push) begin
                    if (!e0_v) e0_v <= 1'b1; else e1_v <= 1'b1;
                end
                if (push) wp <= !wp;
                if (pop) rp <= !rp;
            end
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin e0_d <= '0; e1_d <= '0; end
            else if (push) begin if (wp) e1_d <= cap_d; else e0_d <= cap_d; end
        wire [W-1:0] head = rp ? e1_d : e0_d;
        assign out_d = ZERO_IDLE ? (head & {W{e0_v}}) : head;
    end else begin : g_shift
        assign out_d = e0_d;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin e0_v <= 1'b0; e1_v <= 1'b0; e0_d <= '0; e1_d <= '0; end
            else if (pop) begin
                if (e1_v) begin
                    e0_d <= e1_d;
                    e1_v <= push;
                    if (push) e1_d <= cap_d;
                end else begin
                    e0_v <= push;
                    if (push) e0_d <= cap_d; else if (ZERO_IDLE) e0_d <= '0;
                end
            end else if (push) begin
                if (!e0_v) begin e0_v <= 1'b1; e0_d <= cap_d; end
                else begin e1_v <= 1'b1; e1_d <= cap_d; end
            end
    end endgenerate
endmodule

module ot_dsrom_window_source_ctl #(
    // 0: original body; 1: margin-first boundary; 2: MARGIN 1 + the 2026-10-07 class fixes (takeover-ds, route_r2
    // post-CTS classes at 770 ps): pointer-FIFO skids, kept idle copies for the ready paths, FSM data registers
    // outside the fault priority, five-stage mirror check, predecoded mirror writes, the writer's dead refill
    // response port tied off (FR/FR_DONE/FR_PIPE are unreachable here), writer MARGIN2, stream engine MARGIN2.
    parameter integer MARGIN = 0,
    parameter bit REFILL_OWNER_SAFE = 0,
    parameter integer POS_W = 21, USER_W = 10, SEC_W = 30, HAW = 30, TAGW = 16,
    parameter integer WIN_STACK = 0, REFILL_CREDITS = 1,
    parameter integer NPC = 32, WTAGW = 13, WLENW = 4, BEATW = 4, LA_IW = 8, LA_ISSUE_PC = 0,
    parameter integer MAX_CONTEXT = 1048576
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
    input wire [POS_W-1:0] start_first,
    input wire [7:0] start_count,
    output wire staged_v,
    input wire stream_go,
    output wire busy, done, fault,
    output wire [4:0] fault_code,
    output wire [31:0] refill_cycles, sectors_read,
    output wire [31:0] rows_fetched, blocks_written, sectors_written,
    output wire [7:0] rows_refilled,
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
    // wide port: client 0 of the stack's ot_dsrom_hbm_wmux
    output wire [NPC-1:0] wl_req_v,
    input wire [NPC-1:0] wl_req_rdy,
    output wire [NPC*HAW-1:0] wl_req_addr,
    output wire [NPC*WLENW-1:0] wl_req_len,
    output wire [NPC*WTAGW-1:0] wl_req_tag,
    // staging array neighbour
    input wire [NPC-1:0] acc_v,
    input wire [NPC*WTAGW-1:0] acc_tag,
    input wire [NPC*BEATW-1:0] acc_beat,
    input wire [NPC*256-1:0] acc_data,
    output wire stage_job_v,
    output wire [USER_W-1:0] stage_job_user,
    output wire [POS_W-1:0] stage_job_first,
    output wire [7:0] stage_job_count,
    input wire stage_all_rows,
    input wire [11:0] stage_landed,
    input wire stage_fault,
    // row merge neighbour
    output wire merge_start_v,
    input wire merge_start_ready,
    output wire [USER_W-1:0] merge_user,
    output wire [POS_W-1:0] merge_first,
    output wire [7:0] merge_count,
    input wire merge_done,
    input wire merge_fault,
    output wire [31:0] la_load_cycles
);
    // ---------------- reset (MARGIN: flopped at the pin, asynchronous assert, synchronous release) -----
    wire rst_i;
    generate if (MARGIN) begin : g_rst
        (* keep *) reg rst_s1, rst_s2;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin rst_s1 <= 1'b0; rst_s2 <= 1'b0; end
            else begin rst_s1 <= 1'b1; rst_s2 <= rst_s1; end
        assign rst_i = rst_s2;
    end else begin : g_rst_direct
        assign rst_i = rst_n;
    end endgenerate
    localparam integer PITCH = 17, REGION_SECTORS = 128 * PITCH;
    localparam [2:0] IDLE = 0, LOAD = 1, ISSUE = 2, RUN = 3, FAILED = 4, ADMIT1=5, ADMIT2=6, ADMIT3=7;
    // ---------------- boundary (MARGIN) ----------------
    wire [SEC_W-1:0] rg_base, rg_count;
    wire i_prime_v, i_blk_v, i_start_v;
    wire i_prime_ready, i_blk_ready, i_start_ready;
    wire [USER_W-1:0] i_prime_user, i_blk_user, i_start_user;
    wire [POS_W-1:0] i_prime_row, i_blk_row, i_start_first;
    wire [3:0] i_blk_idx; wire [255:0] i_blk_codes; wire [7:0] i_blk_scale; wire [7:0] i_start_count;
    wire i_stream_go, i_all_rows, i_stage_fault, i_merge_ready, i_merge_done, i_merge_fault;
    wire [11:0] i_landed;
    wire [3:0] i_m_wr_done, i_s_v; wire [4*TAGW-1:0] i_s_tag; wire [15:0] i_s_beat; wire [1023:0] i_s_data;
    wire [3:0] w_m_v, w_m_rdy, w_m_we; wire [4*HAW-1:0] w_m_addr; wire [15:0] w_m_len; wire [4*TAGW-1:0] w_m_tag;
    wire [1023:0] w_m_wdata; wire [127:0] w_m_wstrb;
    generate if (MARGIN) begin : g_margin
        reg [SEC_W-1:0] rb_q, rc_q;
        reg go_q, all_q, sf_q, mr_q, md_q, mf_q;
        reg [11:0] landed_q;
        reg [3:0] wd_q, sv_q; reg [4*TAGW-1:0] st_q; reg [15:0] sb_q; reg [1023:0] sd_q;
        always @(posedge clk or negedge rst_i)
            if (!rst_i) begin
                rb_q <= 0; rc_q <= 0; go_q <= 0; all_q <= 0; sf_q <= 0; mr_q <= 0; md_q <= 0; mf_q <= 0;
                landed_q <= 0; wd_q <= 0; sv_q <= 0; st_q <= 0; sb_q <= 0; sd_q <= 0;
            end else begin
                rb_q <= region_base_sector; rc_q <= region_sector_count; go_q <= stream_go;
                all_q <= stage_all_rows; sf_q <= stage_fault; landed_q <= stage_landed;
                mr_q <= merge_start_ready; md_q <= merge_done; mf_q <= merge_fault;
                wd_q <= m_wr_done; sv_q <= s_v; st_q <= s_tag; sb_q <= s_beat; sd_q <= s_data;
            end
        assign rg_base = rb_q; assign rg_count = rc_q; assign i_stream_go = go_q;
        assign i_all_rows = all_q; assign i_stage_fault = sf_q; assign i_landed = landed_q;
        assign i_merge_ready = mr_q; assign i_merge_done = md_q; assign i_merge_fault = mf_q;
        assign i_m_wr_done = wd_q; assign i_s_v = sv_q; assign i_s_tag = st_q; assign i_s_beat = sb_q;
        assign i_s_data = sd_q;
        ot_dsrom_window_skid #(.W(USER_W+POS_W), .PTR(MARGIN >= 2)) u_prime (.clk(clk), .rst_n(rst_i),
            .in_v(prime_v), .in_ready(prime_ready), .in_d({prime_user, prime_row}),
            .out_v(i_prime_v), .out_ready(i_prime_ready), .out_d({i_prime_user, i_prime_row}));
        ot_dsrom_window_skid #(.W(USER_W+POS_W+4+256+8), .PTR(MARGIN >= 2)) u_blk (.clk(clk), .rst_n(rst_i),
            .in_v(blk_v), .in_ready(blk_ready), .in_d({blk_user, blk_row, blk_idx, blk_codes, blk_scale}),
            .out_v(i_blk_v), .out_ready(i_blk_ready),
            .out_d({i_blk_user, i_blk_row, i_blk_idx, i_blk_codes, i_blk_scale}));
        ot_dsrom_window_skid #(.W(USER_W+POS_W+8), .PTR(MARGIN >= 2)) u_start (.clk(clk), .rst_n(rst_i),
            .in_v(start_v), .in_ready(start_ready), .in_d({start_user, start_first, start_count}),
            .out_v(i_start_v), .out_ready(i_start_ready), .out_d({i_start_user, i_start_first, i_start_count}));
        // K-port write request: one lane (WIN_STACK) carries the writer's request; the others stay zero.
        localparam integer MW = HAW + 4 + TAGW + 1 + 256 + 32;
        wire mo_v; wire [MW-1:0] mo_d; wire mi_ready;
        ot_dsrom_window_skid #(.W(MW), .ZERO_IDLE(1), .PTR(MARGIN >= 2)) u_mreq (.clk(clk), .rst_n(rst_i),
            .in_v(w_m_v[WIN_STACK]), .in_ready(mi_ready),
            .in_d({w_m_addr[WIN_STACK*HAW +: HAW], w_m_len[WIN_STACK*4 +: 4], w_m_tag[WIN_STACK*TAGW +: TAGW],
                   w_m_we[WIN_STACK], w_m_wdata[WIN_STACK*256 +: 256], w_m_wstrb[WIN_STACK*32 +: 32]}),
            .out_v(mo_v), .out_ready(m_rdy[WIN_STACK]), .out_d(mo_d));
        assign w_m_rdy = 4'(mi_ready) << WIN_STACK;
        assign m_v = 4'(mo_v) << WIN_STACK;
        assign m_addr = (4*HAW)'(mo_d[MW-1 -: HAW]) << (WIN_STACK*HAW);
        assign m_len = 16'(mo_d[MW-HAW-1 -: 4]) << (WIN_STACK*4);
        assign m_tag = (4*TAGW)'(mo_d[MW-HAW-5 -: TAGW]) << (WIN_STACK*TAGW);
        assign m_we = 4'(mo_d[288]) << WIN_STACK;
        assign m_wdata = 1024'(mo_d[287:32]) << (WIN_STACK*256);
        assign m_wstrb = 128'(mo_d[31:0]) << (WIN_STACK*32);
    end else begin : g_direct
        assign rg_base = region_base_sector; assign rg_count = region_sector_count;
        assign i_stream_go = stream_go; assign i_all_rows = stage_all_rows; assign i_stage_fault = stage_fault;
        assign i_landed = stage_landed; assign i_merge_ready = merge_start_ready; assign i_merge_done = merge_done;
        assign i_merge_fault = merge_fault; assign i_m_wr_done = m_wr_done; assign i_s_v = s_v;
        assign i_s_tag = s_tag; assign i_s_beat = s_beat; assign i_s_data = s_data;
        assign i_prime_v = prime_v; assign prime_ready = i_prime_ready;
        assign i_prime_user = prime_user; assign i_prime_row = prime_row;
        assign i_blk_v = blk_v; assign blk_ready = i_blk_ready; assign i_blk_user = blk_user;
        assign i_blk_row = blk_row; assign i_blk_idx = blk_idx; assign i_blk_codes = blk_codes;
        assign i_blk_scale = blk_scale;
        assign i_start_v = start_v; assign start_ready = i_start_ready; assign i_start_user = start_user;
        assign i_start_first = start_first; assign i_start_count = start_count;
        assign w_m_rdy = m_rdy; assign m_v = w_m_v; assign m_addr = w_m_addr; assign m_len = w_m_len;
        assign m_tag = w_m_tag; assign m_we = w_m_we; assign m_wdata = w_m_wdata; assign m_wstrb = w_m_wstrb;
    end endgenerate
    // ---------------- original STREAM_LA body (ot_dsrom_window_source_pipeline g_la) ----------------
    reg [2:0] st;
    reg [USER_W-1:0] j_user;
    reg [POS_W-1:0] j_first;
    reg [7:0] j_count;
    reg [31:0] load_cyc, load_cyc_q;
    wire [31:0] load_cyc_inc;
    ot_hdc_inc_k #(.W(32)) u_k_load (.a(load_cyc), .inc(1'b1), .y(load_cyc_inc), .co());
    reg staged_sent, done_r, ctl_fault;
    reg [2:0] ctl_code;                       // {region/geometry, tag mirror, merge}
    wire wr_prime_ready, wr_blk_ready, wr_pf_ready, wr_fault;
    wire [4:0] wr_code;
    wire [31:0] w_blocks_written, w_sectors_written;
    // MARGIN 2: the K-port read-response port serves only the writer's refill states (FR / FR_DONE / FR_PIPE),
    // which no transition of this leaf reaches (refill is the wide-load engine's); outside them the writer ignores
    // s_*, so tying them off is exact and removes the dead 1,024-bit response logic from timing.
    wire [3:0] w_s_v = MARGIN >= 2 ? 4'd0 : i_s_v;
    wire [4*TAGW-1:0] w_s_tag = MARGIN >= 2 ? '0 : i_s_tag;
    wire [15:0] w_s_beat = MARGIN >= 2 ? 16'd0 : i_s_beat;
    wire [1023:0] w_s_data = MARGIN >= 2 ? 1024'd0 : i_s_data;
    ot_dsrom_window_writer_pipeline #(.REFILL_OWNER_SAFE(REFILL_OWNER_SAFE), .POS_W(POS_W),
        .USER_W(USER_W), .SEC_W(SEC_W), .HAW(HAW), .TAGW(TAGW), .WIN_STACK(WIN_STACK),
        .REFILL_CREDITS(REFILL_CREDITS), .BANKED_STAGE(1), .MARGIN(MARGIN != 0), .MARGIN2(MARGIN >= 2)) u_writer (
        .clk(clk), .rst_n(rst_i),
        .region_base_sector(rg_base), .region_sector_count(rg_count),
        .prime_v(i_prime_v && i_prime_ready), .prime_ready(wr_prime_ready),
        .prime_user(i_prime_user), .prime_row(i_prime_row),
        .blk_v(i_blk_v && i_blk_ready), .blk_ready(wr_blk_ready),
        .blk_user(i_blk_user), .blk_row(i_blk_row), .blk_idx(i_blk_idx), .blk_codes(i_blk_codes),
        .blk_scale(i_blk_scale),
        .prefetch_v(1'b0), .prefetch_ready(wr_pf_ready), .prefetch_user(USER_W'(0)), .prefetch_row(POS_W'(0)),
        .kv_ok(),
        .re(1'b0), .ruser(USER_W'(0)), .rrow(POS_W'(0)), .relem(9'd0), .q(),
        .packed_re(1'b0), .packed_ruser(USER_W'(0)), .packed_rrow(POS_W'(0)), .packed_ridx(4'd0),
        .packed_valid(), .packed_row(), .packed_codes(), .packed_scale(),
        .bank_req_v(1'b0), .bank_req_ready(), .bank_req_user(USER_W'(0)), .bank_req_first(POS_W'(0)),
        .bank_req_mask(4'd0), .bank_rsp_v(), .bank_rsp_user(), .bank_rsp_first(), .bank_rsp_mask(),
        .bank_rsp_valid_mask(), .bank_rsp_rows(), .bank_rsp_fault(),
        .fault(wr_fault), .fault_code(wr_code),
        .st_rows_fetched(), .st_blocks_written(w_blocks_written), .st_sectors_read(),
        .st_sectors_written(w_sectors_written),
        .m_v(w_m_v), .m_rdy(w_m_rdy), .m_addr(w_m_addr), .m_len(w_m_len), .m_tag(w_m_tag), .m_we(w_m_we),
        .m_wdata(w_m_wdata), .m_wstrb(w_m_wstrb), .m_wr_done(i_m_wr_done),
        .s_v(w_s_v), .s_rdy(s_rdy), .s_tag(w_s_tag), .s_beat(w_s_beat), .s_data(w_s_data));
    assign blocks_written = w_blocks_written;
    assign sectors_written = w_sectors_written;
    wire i_busy = st != IDLE;
    // MARGIN 2: kept copies of (st == IDLE), one per ready path, loaded from the FSM's exact next-state test
    // (st leaves IDLE only on accept and returns only from RUN on merge_done without a fault).
    (* keep *) reg idle_p, idle_b, idle_s;
    wire la_busy, la_fault;
    wire fsm_fault_c = wr_fault || la_fault || i_stage_fault || i_merge_fault;
    wire accept;
    wire idle_next = (st == IDLE && !accept) || (st == RUN && i_merge_done && !fsm_fault_c);
    always @(posedge clk or negedge rst_i)
        if (!rst_i) begin idle_p <= 1'b1; idle_b <= 1'b1; idle_s <= 1'b1; end
        else begin idle_p <= idle_next; idle_b <= idle_next; idle_s <= idle_next; end
`ifndef SYNTHESIS
    always @(posedge clk) if (MARGIN >= 2 && rst_i && (idle_p != (st == IDLE) || idle_b != idle_p || idle_s != idle_p))
        $fatal(1, "ot_dsrom_window_source_ctl: kept idle copy diverged from st");
`endif
    assign i_prime_ready = (MARGIN >= 2 ? idle_p : !i_busy) && wr_prime_ready;
    assign i_blk_ready = (MARGIN >= 2 ? idle_b : !i_busy) && wr_blk_ready;
    // ---- tag mirror ----
    reg [127:0] mv;
    reg [POS_W-1:0] mtag [0:127];
    reg [USER_W-1:0] muser [0:127];
    // MARGIN: the mirror write command is registered, then applied (one edge later).  Mirror reads start
    // only after a job is admitted, which needs the writer idle, so no read can observe the extra edge.
    wire mw_prime = i_prime_v && i_prime_ready, mw_blk = !mw_prime && i_blk_v && i_blk_ready;
    reg mw_prime_q, mw_blk_q; reg [3:0] mw_idx_q; reg [POS_W-1:0] mw_row_q; reg [USER_W-1:0] mw_user_q;
    reg [127:0] mw_sel_q;                     // pre-decoded slot (MARGIN)
    wire [POS_W-1:0] mw_row = mw_prime ? i_prime_row : i_blk_row;
    // MARGIN 2: the command is decoded before its register (tag/user write, mv set, mv clear), with one kept copy
    // of the tag-write enable per 16-entry group.
    (* keep *) reg [7:0] mw_tagw_q; reg mw_mv1_q, mw_mv0_q;
    always @(posedge clk or negedge rst_i)
        if (!rst_i) begin mw_tagw_q <= 0; mw_mv1_q <= 0; mw_mv0_q <= 0; end
        else begin
            mw_tagw_q <= {8{mw_prime || (mw_blk && i_blk_idx == 4'd0)}};
            mw_mv1_q <= mw_prime || (mw_blk && i_blk_idx == 4'd15);
            mw_mv0_q <= mw_blk && i_blk_idx == 4'd0;
        end
    always @(posedge clk or negedge rst_i)
        if (!rst_i) begin mw_prime_q <= 0; mw_blk_q <= 0; end
        else begin
            mw_prime_q <= mw_prime; mw_blk_q <= mw_blk;
            mw_idx_q <= i_blk_idx; mw_row_q <= mw_row;
            mw_user_q <= mw_prime ? i_prime_user : i_blk_user;
            mw_sel_q <= 128'h1 << mw_row[6:0];
        end
    integer mwi;
    wire a_prime = MARGIN ? mw_prime_q : mw_prime;
    wire a_blk = MARGIN ? mw_blk_q : mw_blk;
    wire [3:0] a_idx = MARGIN ? mw_idx_q : i_blk_idx;
    wire [POS_W-1:0] a_row = MARGIN ? mw_row_q : (mw_prime ? i_prime_row : i_blk_row);
    wire [USER_W-1:0] a_user = MARGIN ? mw_user_q : (mw_prime ? i_prime_user : i_blk_user);
    always @(posedge clk or negedge rst_i)
        if (!rst_i) mv <= 0;
        else if (MARGIN >= 2) begin
            for (mwi = 0; mwi < 128; mwi = mwi + 1) if (mw_sel_q[mwi]) begin
                if (mw_tagw_q[mwi/16]) begin mtag[mwi] <= a_row; muser[mwi] <= a_user; end
                if (mw_mv1_q) mv[mwi] <= 1'b1; else if (mw_mv0_q) mv[mwi] <= 1'b0;
            end
        end else if (MARGIN) begin
            for (mwi = 0; mwi < 128; mwi = mwi + 1) if (mw_sel_q[mwi]) begin
                if (a_prime) begin
                    mv[mwi] <= 1'b1; mtag[mwi] <= a_row; muser[mwi] <= a_user;
                end else if (a_blk) begin
                    if (a_idx == 4'd0) begin mv[mwi] <= 1'b0; mtag[mwi] <= a_row; muser[mwi] <= a_user; end
                    if (a_idx == 4'd15) mv[mwi] <= 1'b1;
                end
            end
        end else begin
            if (a_prime) begin
                mv[a_row[6:0]] <= 1'b1; mtag[a_row[6:0]] <= a_row; muser[a_row[6:0]] <= a_user;
            end else if (a_blk) begin
                if (a_idx == 4'd0) begin
                    mv[a_row[6:0]] <= 1'b0; mtag[a_row[6:0]] <= a_row; muser[a_row[6:0]] <= a_user;
                end
                if (a_idx == 4'd15) mv[a_row[6:0]] <= 1'b1;
            end
        end
    // ---- job admission ----
    reg [SEC_W-1:0] cfg_base, cfg_count;
    reg [SEC_W:0] region_end, user_plus, required_size, user_offset;
    reg [POS_W:0] end_pos;
    // log-depth adders (exact; the behavioural forms ripple under ABC)
    wire [SEC_W:0] ks_region_end, ks_user_plus, ks_size, ks_uoff, ks_cnt_ge; wire [SEC_W-1:0] ks_base;
    wire [POS_W:0] ks_end_pos; wire cnt_ge_size;
    ot_hdc_ksadd_k #(.W(SEC_W+1)) u_k_rend (.a({1'b0,cfg_base}), .b({1'b0,cfg_count}), .cin(1'b0), .s(ks_region_end), .cout());
    ot_hdc_ksadd_k #(.W(SEC_W+1)) u_k_uplus (.a((SEC_W+1)'(j_user)), .b('0), .cin(1'b1), .s(ks_user_plus), .cout());
    ot_hdc_ksadd_k #(.W(POS_W+1)) u_k_endp (.a({1'b0,j_first}), .b((POS_W+1)'(j_count)), .cin(1'b0), .s(ks_end_pos), .cout());
    ot_hdc_ksadd_k #(.W(SEC_W+1)) u_k_size (.a(user_plus<<11), .b(user_plus<<7), .cin(1'b0), .s(ks_size), .cout());
    ot_hdc_ksadd_k #(.W(SEC_W+1)) u_k_uoff (.a((SEC_W+1)'(j_user)<<11), .b((SEC_W+1)'(j_user)<<7), .cin(1'b0), .s(ks_uoff), .cout());
    ot_hdc_ksadd_k #(.W(SEC_W)) u_k_base (.a(cfg_base), .b(user_offset[SEC_W-1:0]), .cin(1'b0), .s(ks_base), .cout());
    ot_hdc_ksadd_k #(.W(SEC_W+1)) u_k_cge (.a({1'b0,cfg_count}), .b(~required_size), .cin(1'b1), .s(ks_cnt_ge), .cout(cnt_ge_size));
    // MARGIN: the size and captured-vs-live region predicates are registered in ADMIT2 (carry-save
    // signed difference, user_plus <= 1024 so nothing truncates).
    reg size_bad_q, cfg_mismatch_q;
    wire [32:0] za = {2'b0, cfg_count}, zb = ~{2'b0, user_plus << 11}, zc = ~{2'b0, user_plus << 7};
    wire [32:0] zs = za ^ zb ^ zc, zk = {((za & zb) | (za & zc) | (zb & zc)), 1'b1};
    wire [32:0] zd;
    ot_hdc_ksadd_k #(.W(33)) u_k_zsz (.a(zs), .b(zk), .cin(1'b1), .s(zd), .cout());
    wire start_bad = MARGIN ?
        (j_count > 8'd128 || end_pos > (POS_W+1)'(MAX_CONTEXT) || region_end[SEC_W] || size_bad_q || cfg_mismatch_q) :
        (j_count > 8'd128 || end_pos > (POS_W+1)'(MAX_CONTEXT) || region_end[SEC_W] ||
         !cnt_ge_size || cfg_base!=rg_base || cfg_count!=rg_count);
    assign i_start_ready = (MARGIN >= 2 ? idle_s : st == IDLE) && wr_pf_ready && !la_busy && !(ctl_fault || wr_fault);
    assign accept = i_start_v && i_start_ready;
    reg [SEC_W-1:0] j_base;
    reg [5:0] ck_i; reg ck_run, ck_bad, ck_issue;
    reg [4:0] ck_valid;                       // [2] is used only with MARGIN, [4:3] only with MARGIN 2
    reg [POS_W-1:0] ck_row0 [0:3], ck_row1 [0:3], ck_tag1 [0:3];
    reg [USER_W-1:0] ck_user1 [0:3];
    reg [3:0] ck_use0, ck_use1, ck_mv1;
    integer ck_l; reg [8:0] ck_t;
    integer ck_g;
    // MARGIN: the 128-entry mirror read is split, eight 16:1 group reads registered, then an 8:1 select.
    reg [POS_W-1:0] ck_rowa [0:3]; reg [3:0] ck_usea;
    reg [POS_W-1:0] ck_gtag [0:3][0:7]; reg [USER_W-1:0] ck_guser [0:3][0:7]; reg [7:0] ck_gmv [0:3];
    wire [POS_W-1:0] ck_sum [0:3];
    genvar ckq;
    generate for (ckq = 0; ckq < 4; ckq = ckq + 1) begin : g_ck_add
        ot_hdc_ksadd_k #(.W(POS_W)) u_k_row (.a(j_first), .b(POS_W'({ck_i, 2'(ckq)})), .cin(1'b0), .s(ck_sum[ckq]), .cout());
    end endgenerate
    reg la_start, stage_job;
    // MARGIN: accepted beats from the staging neighbour are flopped at the pin.
    wire [NPC-1:0] a_v; wire [NPC*WTAGW-1:0] a_tag; wire [NPC*BEATW-1:0] a_beat; wire [NPC*256-1:0] a_data;
    generate if (MARGIN) begin : g_acc
        reg [NPC-1:0] v_q; reg [NPC*WTAGW-1:0] t_q; reg [NPC*BEATW-1:0] b_q; reg [NPC*256-1:0] d_q;
        always @(posedge clk or negedge rst_i)
            if (!rst_i) v_q <= '0; else v_q <= acc_v;
        always @(posedge clk) begin t_q <= acc_tag; b_q <= acc_beat; d_q <= acc_data; end
        assign a_v = v_q; assign a_tag = t_q; assign a_beat = b_q; assign a_data = d_q;
    end else begin : g_acc_direct
        assign a_v = acc_v; assign a_tag = acc_tag; assign a_beat = acc_beat; assign a_data = acc_data;
    end endgenerate
    ot_dsrom_window_stream_la_s81 #(.NPC(NPC), .AW(HAW), .TAGW(WTAGW), .LENW(WLENW), .BEATW(BEATW), .IW(LA_IW),
        .ISSUE_PC(LA_ISSUE_PC), .MARGIN(MARGIN != 0), .MARGIN2(MARGIN >= 2)) u_la (
        .clk(clk), .rst_n(rst_i), .start(la_start), .base(HAW'(j_base)), .busy(la_busy), .fault(la_fault),
        .req_v(wl_req_v), .req_rdy(wl_req_rdy), .req_addr(wl_req_addr), .req_len(wl_req_len), .req_tag(wl_req_tag),
        .rsp_v(a_v), .rsp_tag(a_tag), .rsp_beat(a_beat), .rsp_data(a_data));
    assign stage_job_v = stage_job;
    assign stage_job_user = j_user; assign stage_job_first = j_first; assign stage_job_count = j_count;
    assign merge_user = j_user; assign merge_first = j_first; assign merge_count = j_count;
    wire issue_v = st == ISSUE;
    wire i_staged_v = issue_v && !staged_sent;
    wire issue_ready = i_merge_ready && i_stream_go && staged_sent;
    reg mstart_q;
    assign merge_start_v = MARGIN ? mstart_q : (issue_v && issue_ready);
    generate if (MARGIN < 2) begin : g_fsm1
    always @(posedge clk or negedge rst_i) begin
        if (!rst_i) begin
            st <= IDLE; j_user <= 0; j_first <= 0; j_count <= 0; j_base <= 0; load_cyc <= 0; load_cyc_q <= 0;
            staged_sent <= 0; done_r <= 0; ctl_fault <= 0; ctl_code <= 0; la_start <= 0; stage_job<=0;
            cfg_base<=0; cfg_count<=0; ck_valid<=0; ck_issue<=0;
            ck_i <= 0; ck_run <= 0; ck_bad <= 0; mstart_q <= 0;
        end else begin
            done_r <= 1'b0; la_start <= 1'b0; stage_job<=0; mstart_q <= 1'b0;
            if (i_staged_v) staged_sent <= 1'b1;
            if (st != IDLE && st != FAILED && (wr_fault || la_fault || i_stage_fault || i_merge_fault)) begin
                ctl_fault <= 1'b1; if (i_merge_fault) ctl_code[0] <= 1'b1; st <= FAILED;
            end else case (st)
                IDLE: if (accept) begin
                    j_user<=i_start_user; j_first<=i_start_first; j_count<=i_start_count;
                    cfg_base<=rg_base; cfg_count<=rg_count;
                    load_cyc<=0; staged_sent<=0; st<=ADMIT1;
                end
                ADMIT1: begin
                    region_end<=ks_region_end;
                    user_plus<=ks_user_plus;
                    end_pos<=ks_end_pos; st<=ADMIT2;
                end
                ADMIT2: begin
                    size_bad_q <= zd[32]; cfg_mismatch_q <= cfg_base!=rg_base || cfg_count!=rg_count;
                    required_size<=ks_size;
                    user_offset<=ks_uoff; st<=ADMIT3;
                end
                ADMIT3: begin
                    j_base<=ks_base;
                    ck_i<=0; ck_run<=1; ck_issue<=1; ck_bad<=0;
                    if(start_bad) begin ctl_fault<=1; ctl_code[2]<=1; st<=FAILED; end
                    else begin la_start<=1; stage_job<=1; st<=LOAD; end
                end
                LOAD: begin
                    load_cyc <= load_cyc_inc;
                    if (!ck_run && ck_bad) begin ctl_fault <= 1'b1; ctl_code[1] <= 1'b1; st <= FAILED; end
                    else if (!ck_run && i_all_rows && !la_start && !la_busy) begin load_cyc_q <= load_cyc_inc; st <= ISSUE; end
                end
                ISSUE: if (issue_ready) begin st <= RUN; mstart_q <= 1'b1; end
                RUN: if (i_merge_done) begin done_r <= 1'b1; st <= IDLE; end
                FAILED: st <= FAILED;
                default: begin ctl_fault <= 1'b1; st <= FAILED; end
            endcase
            ck_valid<={ck_valid[1:0],ck_issue};
            if(ck_issue) begin
                for(ck_l=0;ck_l<4;ck_l=ck_l+1) begin
                    ck_t={ck_i,2'b00}+ck_l;
                    ck_row0[ck_l]<=ck_sum[ck_l];
                    ck_use0[ck_l]<=ck_t<j_count;
                end
                ck_i<=ck_i+1'b1;
                if(ck_i==31) ck_issue<=0;
            end
            if (!MARGIN) begin
                if(ck_valid[0]) for(ck_l=0;ck_l<4;ck_l=ck_l+1) begin
                    ck_row1[ck_l]<=ck_row0[ck_l]; ck_use1[ck_l]<=ck_use0[ck_l];
                    ck_tag1[ck_l]<=mtag[ck_row0[ck_l][6:0]];
                    ck_user1[ck_l]<=muser[ck_row0[ck_l][6:0]];
                    ck_mv1[ck_l]<=mv[ck_row0[ck_l][6:0]];
                end
                if(ck_valid[1]) for(ck_l=0;ck_l<4;ck_l=ck_l+1)
                    if(ck_use1[ck_l] && (!ck_mv1[ck_l] || ck_tag1[ck_l]!=ck_row1[ck_l] || ck_user1[ck_l]!=j_user)) ck_bad<=1;
                if(ck_run && !ck_issue && ck_valid[1:0]==0) ck_run<=0;
            end else begin
                if(ck_valid[0]) for(ck_l=0;ck_l<4;ck_l=ck_l+1) begin
                    ck_rowa[ck_l]<=ck_row0[ck_l]; ck_usea[ck_l]<=ck_use0[ck_l];
                    for(ck_g=0;ck_g<8;ck_g=ck_g+1) begin
                        ck_gtag[ck_l][ck_g]<=mtag[{ck_g[2:0],ck_row0[ck_l][3:0]}];
                        ck_guser[ck_l][ck_g]<=muser[{ck_g[2:0],ck_row0[ck_l][3:0]}];
                        ck_gmv[ck_l][ck_g]<=mv[{ck_g[2:0],ck_row0[ck_l][3:0]}];
                    end
                end
                if(ck_valid[1]) for(ck_l=0;ck_l<4;ck_l=ck_l+1) begin
                    ck_row1[ck_l]<=ck_rowa[ck_l]; ck_use1[ck_l]<=ck_usea[ck_l];
                    ck_tag1[ck_l]<=ck_gtag[ck_l][ck_rowa[ck_l][6:4]];
                    ck_user1[ck_l]<=ck_guser[ck_l][ck_rowa[ck_l][6:4]];
                    ck_mv1[ck_l]<=ck_gmv[ck_l][ck_rowa[ck_l][6:4]];
                end
                if(ck_valid[2]) for(ck_l=0;ck_l<4;ck_l=ck_l+1)
                    if(ck_use1[ck_l] && (!ck_mv1[ck_l] || ck_tag1[ck_l]!=ck_row1[ck_l] || ck_user1[ck_l]!=j_user)) ck_bad<=1;
                if(ck_run && !ck_issue && ck_valid==0) ck_run<=0;
            end
        end
    end
    end else begin : g_fsm2
    // MARGIN 2.  Control registers (st, ctl_fault/code, the pulses, load_cyc_q, j_*) keep the fault priority
    // exactly; data registers that are only read by the FSM's own later decisions (cfg_*, the ADMIT
    // predicates, j_base, load_cyc, staged_sent, the check pipeline) update without it: FAILED is terminal, so
    // a value written in the faulting cycle is never read.  cfg_* / load_cyc / staged_sent load while IDLE
    // (their accept-edge value is the same).  The mirror check reads 4:1 (row[1:0]) -> 4:1 ([3:2]) -> 4:1
    // ([5:4]) -> 2:1 ([6]) -> compare: five edges instead of three, inside LOAD (hidden by the stream load).
    reg [POS_W-1:0] ck_rowA [0:3], ck_rowC [0:3]; reg [3:0] ck_useA, ck_useC;
    reg [POS_W-1:0] ck_stag [0:3][0:31]; reg [USER_W-1:0] ck_suser [0:3][0:31]; reg [31:0] ck_smv [0:3];
    reg [POS_W-1:0] ck_htag [0:3][0:1]; reg [USER_W-1:0] ck_huser [0:3][0:1]; reg [1:0] ck_hmv [0:3];
    integer ck_s;
    always @(posedge clk or negedge rst_i) begin
        if (!rst_i) begin
            st <= IDLE; j_user <= 0; j_first <= 0; j_count <= 0; j_base <= 0; load_cyc <= 0; load_cyc_q <= 0;
            staged_sent <= 0; done_r <= 0; ctl_fault <= 0; ctl_code <= 0; la_start <= 0; stage_job<=0;
            cfg_base<=0; cfg_count<=0; ck_valid<=0; ck_issue<=0;
            ck_i <= 0; ck_run <= 0; ck_bad <= 0; mstart_q <= 0;
        end else begin
            done_r <= 1'b0; la_start <= 1'b0; stage_job<=0; mstart_q <= 1'b0;
            if (i_staged_v) staged_sent <= 1'b1;
            // ---- data registers ----
            case (st)
                IDLE: begin cfg_base <= rg_base; cfg_count <= rg_count; load_cyc <= 0; staged_sent <= 1'b0; end
                ADMIT1: begin region_end <= ks_region_end; user_plus <= ks_user_plus; end_pos <= ks_end_pos; end
                ADMIT2: begin
                    size_bad_q <= zd[32]; cfg_mismatch_q <= cfg_base != rg_base || cfg_count != rg_count;
                    required_size <= ks_size; user_offset <= ks_uoff;
                end
                ADMIT3: begin j_base <= ks_base; ck_i <= 0; ck_run <= 1; ck_issue <= 1; ck_bad <= 0; end
                LOAD: load_cyc <= load_cyc_inc;
                default: begin end
            endcase
            // ---- control registers (fault priority unchanged) ----
            if (st != IDLE && st != FAILED && fsm_fault_c) begin
                ctl_fault <= 1'b1; if (i_merge_fault) ctl_code[0] <= 1'b1; st <= FAILED;
            end else case (st)
                IDLE: if (accept) begin
                    j_user<=i_start_user; j_first<=i_start_first; j_count<=i_start_count; st<=ADMIT1;
                end
                ADMIT1: st<=ADMIT2;
                ADMIT2: st<=ADMIT3;
                ADMIT3: begin
                    if(start_bad) begin ctl_fault<=1; ctl_code[2]<=1; st<=FAILED; end
                    else begin la_start<=1; stage_job<=1; st<=LOAD; end
                end
                LOAD: begin
                    if (!ck_run && ck_bad) begin ctl_fault <= 1'b1; ctl_code[1] <= 1'b1; st <= FAILED; end
                    else if (!ck_run && i_all_rows && !la_start && !la_busy) begin load_cyc_q <= load_cyc_inc; st <= ISSUE; end
                end
                ISSUE: if (issue_ready) begin st <= RUN; mstart_q <= 1'b1; end
                RUN: if (i_merge_done) begin done_r <= 1'b1; st <= IDLE; end
                FAILED: st <= FAILED;
                default: begin ctl_fault <= 1'b1; st <= FAILED; end
            endcase
            // ---- mirror check ----
            ck_valid<={ck_valid[3:0],ck_issue};
            if(ck_issue) begin
                for(ck_l=0;ck_l<4;ck_l=ck_l+1) begin
                    ck_t={ck_i,2'b00}+ck_l;
                    ck_row0[ck_l]<=ck_sum[ck_l];
                    ck_use0[ck_l]<=ck_t<j_count;
                end
                ck_i<=ck_i+1'b1;
                if(ck_i==31) ck_issue<=0;
            end
            if(ck_valid[0]) for(ck_l=0;ck_l<4;ck_l=ck_l+1) begin       // A: 32 x (4:1 by row[1:0])
                ck_rowA[ck_l]<=ck_row0[ck_l]; ck_useA[ck_l]<=ck_use0[ck_l];
                for(ck_s=0;ck_s<32;ck_s=ck_s+1) begin
                    ck_stag[ck_l][ck_s]<=mtag[{ck_s[4:0],ck_row0[ck_l][1:0]}];
                    ck_suser[ck_l][ck_s]<=muser[{ck_s[4:0],ck_row0[ck_l][1:0]}];
                    ck_smv[ck_l][ck_s]<=mv[{ck_s[4:0],ck_row0[ck_l][1:0]}];
                end
            end
            if(ck_valid[1]) for(ck_l=0;ck_l<4;ck_l=ck_l+1) begin       // B: 8 x (4:1 by row[3:2])
                ck_rowa[ck_l]<=ck_rowA[ck_l]; ck_usea[ck_l]<=ck_useA[ck_l];
                for(ck_g=0;ck_g<8;ck_g=ck_g+1) begin
                    ck_gtag[ck_l][ck_g]<=ck_stag[ck_l][{ck_g[2:0],ck_rowA[ck_l][3:2]}];
                    ck_guser[ck_l][ck_g]<=ck_suser[ck_l][{ck_g[2:0],ck_rowA[ck_l][3:2]}];
                    ck_gmv[ck_l][ck_g]<=ck_smv[ck_l][{ck_g[2:0],ck_rowA[ck_l][3:2]}];
                end
            end
            if(ck_valid[2]) for(ck_l=0;ck_l<4;ck_l=ck_l+1) begin       // C: 2 x (4:1 by row[5:4])
                ck_rowC[ck_l]<=ck_rowa[ck_l]; ck_useC[ck_l]<=ck_usea[ck_l];
                for(ck_g=0;ck_g<2;ck_g=ck_g+1) begin
                    ck_htag[ck_l][ck_g]<=ck_gtag[ck_l][{ck_g[0],ck_rowa[ck_l][5:4]}];
                    ck_huser[ck_l][ck_g]<=ck_guser[ck_l][{ck_g[0],ck_rowa[ck_l][5:4]}];
                    ck_hmv[ck_l][ck_g]<=ck_gmv[ck_l][{ck_g[0],ck_rowa[ck_l][5:4]}];
                end
            end
            if(ck_valid[3]) for(ck_l=0;ck_l<4;ck_l=ck_l+1) begin       // D: 2:1 by row[6]
                ck_row1[ck_l]<=ck_rowC[ck_l]; ck_use1[ck_l]<=ck_useC[ck_l];
                ck_tag1[ck_l]<=ck_htag[ck_l][ck_rowC[ck_l][6]];
                ck_user1[ck_l]<=ck_huser[ck_l][ck_rowC[ck_l][6]];
                ck_mv1[ck_l]<=ck_hmv[ck_l][ck_rowC[ck_l][6]];
            end
            if(ck_valid[4]) for(ck_l=0;ck_l<4;ck_l=ck_l+1)              // E: compare
                if(ck_use1[ck_l] && (!ck_mv1[ck_l] || ck_tag1[ck_l]!=ck_row1[ck_l] || ck_user1[ck_l]!=j_user)) ck_bad<=1;
            if(ck_run && !ck_issue && ck_valid==0) ck_run<=0;
        end
    end
    end endgenerate
    wire i_fault = ctl_fault || wr_fault || la_fault || i_stage_fault;
    wire [4:0] i_fault_code = wr_code | {la_fault || i_stage_fault, 1'b0, ctl_code};
    wire [31:0] i_rows_fetched = 32'(st == IDLE || st == ISSUE || st == RUN ? j_count : 8'd0);
    assign done = done_r;
    assign refill_cycles = load_cyc_q;
    assign la_load_cycles = load_cyc_q;
    assign rows_refilled = j_count;
    generate if (MARGIN) begin : g_out
        reg busy_q, fault_q, staged_q; reg [4:0] code_q; reg [31:0] rf_q, sr_q;
        always @(posedge clk or negedge rst_i)
            if (!rst_i) begin busy_q <= 0; fault_q <= 0; staged_q <= 0; code_q <= 0; rf_q <= 0; sr_q <= 0; end
            else begin
                busy_q <= i_busy; fault_q <= i_fault; staged_q <= i_staged_v; code_q <= i_fault_code;
                rf_q <= i_rows_fetched; sr_q <= 32'(i_landed);
            end
        assign busy = busy_q; assign fault = fault_q; assign staged_v = staged_q; assign fault_code = code_q;
        assign rows_fetched = rf_q; assign sectors_read = sr_q;
    end else begin : g_out_direct
        assign busy = i_busy; assign fault = i_fault; assign staged_v = i_staged_v; assign fault_code = i_fault_code;
        assign rows_fetched = i_rows_fetched; assign sectors_read = 32'(i_landed);
    end endgenerate
endmodule
