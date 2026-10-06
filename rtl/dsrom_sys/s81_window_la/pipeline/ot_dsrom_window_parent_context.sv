`timescale 1ns/1ps
// Actual native WINDOW-only caller (CKV_SELECTED=0, WINDOW_RETAIN_L0=0)
// through the full physical first-consumer cut. Scheduler/arithmetic and HBM
// service terminals remain timed IO. No native wiring or new pipeline edges.
// WINDOW leaf binds its retained routed views after terminal; no CTS/slot claim
// follows from this source preparation. This is a measurement top only.
module ot_dsrom_window_parent_context #(
    parameter integer NPC=32, AW=30, TAGW=16, STAGW=17, LENW=4, BEATW=4, DW=256, WTAGW=13,
    parameter integer SEC_W=30, HAW=30, POS_W=21, USER_W=10,
    parameter integer KEY_SECTORS=262144, WIN_SECTORS=2176, K_MEM=524288
) (
    input wire clk, rst_n,
    input wire retain_qk, retain_pv, retain_complete, retain_invalidate,
    input wire [15:0] retain_generation,
    input wire [SEC_W-1:0] region_base_sector, region_sector_count,
    input wire prime_v,
    output wire prime_ready,
    input wire [USER_W-1:0] prime_user,
    input wire [POS_W-1:0] prime_row,
    output wire blk_ready,
    output wire start_ready,
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
    input wire [NPC-1:0] a_v, a_rsp_rdy, g_v, g_rsp_rdy, h_rdy, h_wr_done, r_v,
    input wire [NPC*AW-1:0] a_addr, g_addr,
    input wire [NPC*LENW-1:0] a_len, g_len,
    input wire [NPC*STAGW-1:0] a_tag, r_tag,
    input wire [NPC*WTAGW-1:0] g_tag,
    input wire [NPC-1:0] a_we,
    input wire [NPC*DW-1:0] a_wdata, r_data,
    input wire [NPC*DW/8-1:0] a_wstrb,
    input wire [NPC*BEATW-1:0] r_beat,
    output wire [NPC-1:0] a_rdy, a_wr_done, a_rsp_v, g_rdy, g_rsp_v, h_v, h_we, r_rdy,
    output wire [NPC*STAGW-1:0] a_rsp_tag, h_tag,
    output wire [NPC*BEATW-1:0] a_rsp_beat, g_rsp_beat,
    output wire [NPC*DW-1:0] a_rsp_data, g_rsp_data, h_wdata,
    output wire [NPC*WTAGW-1:0] g_rsp_tag,
    output wire [NPC*AW-1:0] h_addr,
    output wire [NPC*LENW-1:0] h_len,
    output wire [NPC*DW/8-1:0] h_wstrb,
    output wire [31:0] la_load_cycles, wg, ah,
    output wire wm_fault,
    input wire host_mode, host_start, c_start,
    input wire [9:0] host_user, c_user,
    input wire [20:0] host_pos, c_pos,
    input wire window_region_valid, kv_re,
    input wire cap_v, issue,
    input wire [29:0] cap_src_addr, issue_src_base, issue_kvt_base,
    input wire [255:0] cap_codes,
    input wire [7:0] cap_scale,
    input wire [20:0] issue_row, issue_abs_row,
    output wire cap_ready, producer_idle, issue_ready,
    output wire [29:0] cap_src_base,
    output wire producer_fault,
    input wire kvd_v, kvd_mmode,
    input wire [20:0] kvd_pos, kvd_tiles, kvd_k, kvd_nout,
    input wire [29:0] kvd_wbase, kvd_ts, kvd_ks, kvd_js,
    input wire [1:0] kvd_hg,
    input wire att_packed_idle, att_adapt_run, att_adapt_kv_v,
    output wire tile_packed_fault, caller_kv_fault,
    output wire packed_desc_ok, descriptor_done, descriptor_fault,
    output wire [3:0] descriptor_fault_code,
    output wire bad_block, unsupported_read,
    input wire act,
    input wire [15:0] wptr, T,
    input wire [3:0] engine_kv_m,
    input wire [7:0] rd_addr,
    input wire [15:0] r0_qk, r0_qk_s,
    input wire rd_qk_s, pv_e, q_go, p_go, p_w2v,
    input wire [7:0] pl_word, q_cnt,
    input wire [1:0] nb_p, pl_bank, nb_q, q_bank, e_iss_bank, rd_bank_s,
    input wire [511:0] p_w_i,
    input wire [8191:0] q_w,
    input wire [36863:0] tr_col,
    input wire e_iss_final,
    input wire [15:0] e_iss_blk,
    input wire [7:0] e_iss_c,
    output wire [70655:0] r0_captures,
    output wire [35:0] e_tags
);
    // These nets terminate in the actual descriptor/consumer inside this cut.
    // Keep their real macro/capture loads without extra observation terminals.
    wire kv_v, kv_ready;
    wire [3:0] kv_m;
    wire [4*16*265-1:0] kv_w;
    wire blk_v;
    wire [USER_W-1:0] blk_user;
    wire [POS_W-1:0] blk_row;
    wire [3:0] blk_idx;
    wire [255:0] blk_codes;
    wire [7:0] blk_scale;
    wire start_v;
    wire [USER_W-1:0] start_user;
    wire [POS_W-1:0] start_first;
    wire [7:0] start_count;
    localparam integer NW=21;
    reg [1:0] rst_s;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    wire rn = rst_s[1];
    reg [9:0] step_user;
    reg capture_ctrl_user;
    wire t_start = host_mode ? host_start : c_start;
    wire [NW-1:0] t_pos = host_mode ? host_pos : c_pos;
    always @(posedge clk or negedge rn)
        if (!rn) begin step_user <= 0; capture_ctrl_user <= 0; end
        else begin
            capture_ctrl_user <= !host_mode && c_start;
            if (host_mode && host_start) step_user <= host_user;
            if (capture_ctrl_user) step_user <= 10'(c_user);
        end
    reg [NW-1:0] step_pos;
    always @(posedge clk or negedge rn)
        if (!rn) step_pos <= '0;
        else if (t_start) step_pos <= t_pos;
    wire raw_blk_v, bad_block_addr;
    wire [29:0] blk_kvt_base, blk_first_elem;
    wire [20:0] blk_kvt_row;
    reg bad_block_q, unsupported_read_q;
    assign bad_block=bad_block_q;
    assign unsupported_read=unsupported_read_q;
    always @(posedge clk or negedge rn)
        if (!rn) begin unsupported_read_q <= 0; bad_block_q <= 0; end
        else begin
            if (kv_re) unsupported_read_q <= 1;
            if (raw_blk_v && blk_ready && bad_block_addr) bad_block_q <= 1;
        end
    wire [30:0] window_region_end = {1'b0,region_base_sector} + {1'b0,region_sector_count};
    wire window_region_ok = window_region_valid && region_base_sector >= 30'(KEY_SECTORS) &&
        region_sector_count >= 30'(WIN_SECTORS) && !window_region_end[30] && window_region_end <= 31'(K_MEM);
    wire source_prime_ready;
    assign prime_ready=window_region_ok && source_prime_ready;
    assign blk_user=step_user;
    assign blk_v=raw_blk_v && !bad_block_addr && !bad_block_q;
    ot_hdc_v41x_window_kv_blocks #(.AW(30),.POS_W(21),.KVT_SH(13),.SEPARATE_ROWS(1)) u_blocks (
        .clk(clk),.rst_n(rn),.cap_v(cap_v),.cap_src_addr(cap_src_addr),.cap_codes(cap_codes),.cap_scale(cap_scale),
        .cap_ready(cap_ready),.cap_src_base(cap_src_base),.idle(producer_idle),.issue(issue),
        .issue_src_base(issue_src_base),.issue_kvt_base(issue_kvt_base),.issue_row(issue_row),.issue_abs_row(issue_abs_row),
        .issue_ready(issue_ready),.blk_v(raw_blk_v),.blk_ready(blk_ready),.blk_kvt_base(blk_kvt_base),
        .blk_row(blk_row),.blk_kvt_row(blk_kvt_row),.blk_idx(blk_idx),.blk_first_elem(blk_first_elem),
        .blk_codes(blk_codes),.blk_scale(blk_scale),.fault(producer_fault));
    ot_chip_v41x_window_block_guard #(.AW(30),.POS_W(21)) u_guard (
        .step_pos(step_pos),.blk_abs_row(blk_row),.blk_kvt_row(blk_kvt_row),.blk_idx(blk_idx),
        .kvt_base(blk_kvt_base),.first_elem(blk_first_elem),.hbm_slot(),.expected_first(),.bad(bad_block_addr));
    wire desc_accept;
    wire [15:0] desc_gen;
    wire [10:0] desc_rows;
    assign tile_packed_fault=fault || (desc_accept && !window_region_ok);
    assign caller_kv_fault=tile_packed_fault || unsupported_read_q || bad_block_q || descriptor_fault;
    reg [15:0] win_service_gen;
    assign start_v=desc_accept && window_region_ok && kvd_mmode && desc_rows==11'd128 && kvd_pos>=21'(127);
    assign start_user=step_user;
    assign start_first=kvd_pos-21'(127);
    assign start_count=8'd128;
    always @(posedge clk or negedge rn)
        if (!rn) win_service_gen <= 16'd0;
        else if (start_v) win_service_gen <= desc_gen;
    ot_chip_v41x_attn_desc_lifecycle #(.AW(30),.NW(21),.NL(4),.L0_ONLY(1)) u_desc_life (
        .clk(clk),.rst_n(rn),.desc_v(kvd_v),.desc_user(step_user),.desc_pos(kvd_pos),.desc_tiles(kvd_tiles),
        .desc_k(kvd_k),.desc_nout(kvd_nout),.desc_wbase(kvd_wbase),.desc_ts(kvd_ts),.desc_ks(kvd_ks),.desc_js(kvd_js),
        .desc_hg(kvd_hg),.desc_mmode(kvd_mmode),.desc_accept(desc_accept),.desc_gen(desc_gen),.desc_rows(desc_rows),
        .stage_v(staged_v),.stage_gen(win_service_gen),.stage_rows(11'd128),
        .beat_v(kv_v),.beat_ready(kv_ready),.beat_gen(win_service_gen),.beat_mask(kv_m),
        .issue_v(stream_go),.engine_idle(att_packed_idle),.service_fault(tile_packed_fault),
        .wrap_drained(!busy && prime_ready && !raw_blk_v),.issue_ok(packed_desc_ok),
        .done(descriptor_done),.fault(descriptor_fault),.fault_code(descriptor_fault_code),.beats_accepted());
    wire engine_kv_ready;
    assign kv_ready=att_adapt_run && att_adapt_kv_v && engine_kv_ready;
    ot_dsrom_window_attention_capture_context u_capture (
        .clk(clk),.rst_n(rn),.act(act),.wptr(wptr),.T(T),.kv_v(att_adapt_kv_v && kv_v),.kv_ready(engine_kv_ready),
        .kv_m(engine_kv_m),.kv_w(kv_w),.rd_addr(rd_addr),.r0_qk(r0_qk),.r0_qk_s(r0_qk_s),
        .rd_qk_s(rd_qk_s),.pv_e(pv_e),.q_go(q_go),.p_go(p_go),.p_w2v(p_w2v),.pl_word(pl_word),.q_cnt(q_cnt),
        .nb_p(nb_p),.pl_bank(pl_bank),.nb_q(nb_q),.q_bank(q_bank),.e_iss_bank(e_iss_bank),.rd_bank_s(rd_bank_s),
        .p_w_i(p_w_i),.q_w(q_w),.tr_col(tr_col),.e_iss_final(e_iss_final),.e_iss_blk(e_iss_blk),.e_iss_c(e_iss_c),
        .r0_captures(r0_captures),.e_tags(e_tags));
    ot_dsrom_window_pipeline_context u_window (
        .clk(clk),
        .rst_n(rn),
        .retain_qk(retain_qk),
        .retain_pv(retain_pv),
        .retain_complete(retain_complete),
        .retain_invalidate(retain_invalidate),
        .retain_generation(retain_generation),
        .region_base_sector(region_base_sector),
        .region_sector_count(region_sector_count),
        .prime_v(prime_v && window_region_ok),
        .prime_ready(source_prime_ready),
        .prime_user(prime_user),
        .prime_row(prime_row),
        .blk_v(blk_v),
        .blk_ready(blk_ready),
        .blk_user(blk_user),
        .blk_row(blk_row),
        .blk_idx(blk_idx),
        .blk_codes(blk_codes),
        .blk_scale(blk_scale),
        .start_v(start_v),
        .start_ready(start_ready),
        .start_user(start_user),
        .start_first(start_first),
        .start_count(start_count),
        .staged_v(staged_v),
        .stream_go(stream_go),
        .busy(busy),
        .done(done),
        .fault(fault),
        .fault_code(fault_code),
        .refill_cycles(refill_cycles),
        .sectors_read(sectors_read),
        .rows_fetched(rows_fetched),
        .blocks_written(blocks_written),
        .sectors_written(sectors_written),
        .rows_refilled(rows_refilled),
        .kv_v(kv_v),
        .kv_ready(kv_ready),
        .kv_m(kv_m),
        .kv_w(kv_w),
        .m_v(m_v),
        .m_rdy(m_rdy),
        .m_addr(m_addr),
        .m_len(m_len),
        .m_tag(m_tag),
        .m_we(m_we),
        .m_wdata(m_wdata),
        .m_wstrb(m_wstrb),
        .m_wr_done(m_wr_done),
        .s_v(s_v),
        .s_rdy(s_rdy),
        .s_tag(s_tag),
        .s_beat(s_beat),
        .s_data(s_data),
        .a_v(a_v),
        .a_rsp_rdy(a_rsp_rdy),
        .g_v(g_v),
        .g_rsp_rdy(g_rsp_rdy),
        .h_rdy(h_rdy),
        .h_wr_done(h_wr_done),
        .r_v(r_v),
        .a_addr(a_addr),
        .g_addr(g_addr),
        .a_len(a_len),
        .g_len(g_len),
        .a_tag(a_tag),
        .r_tag(r_tag),
        .g_tag(g_tag),
        .a_we(a_we),
        .a_wdata(a_wdata),
        .r_data(r_data),
        .a_wstrb(a_wstrb),
        .r_beat(r_beat),
        .a_rdy(a_rdy),
        .a_wr_done(a_wr_done),
        .a_rsp_v(a_rsp_v),
        .g_rdy(g_rdy),
        .g_rsp_v(g_rsp_v),
        .h_v(h_v),
        .h_we(h_we),
        .r_rdy(r_rdy),
        .a_rsp_tag(a_rsp_tag),
        .h_tag(h_tag),
        .a_rsp_beat(a_rsp_beat),
        .g_rsp_beat(g_rsp_beat),
        .a_rsp_data(a_rsp_data),
        .g_rsp_data(g_rsp_data),
        .h_wdata(h_wdata),
        .g_rsp_tag(g_rsp_tag),
        .h_addr(h_addr),
        .h_len(h_len),
        .h_wstrb(h_wstrb),
        .la_load_cycles(la_load_cycles),
        .wg(wg),
        .ah(ah),
        .wm_fault(wm_fault)
    );
endmodule
