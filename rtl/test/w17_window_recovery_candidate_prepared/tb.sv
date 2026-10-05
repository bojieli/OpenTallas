`timescale 1ns/1ps
// PREPARED NOT COMPILED: selected-stack2 minimum fixture, observer IDs only.
module tb;
logic clk=0, rst_n=0;
always #0.5 clk=~clk;
logic prime=0, prefetch=0, block_offer=0, fault_pulse=0;
logic recover=0, token=0, commit=0, hold_return=0;
logic b_offer=0, ckv_offer=0, b_is_write=0;
integer other_grants=0, other_reads=0, other_returns=0, other_writes=0;
integer other_qr_total=0, other_qw_total=0;
wire freeze, source_empty, restart_ready;
wire mux_empty,mux_visible,mux_ack,arb_empty,arb_visible,arb_ack;
wire back_empty,back_visible,back_ack;
integer cycles=0, accepted_reads=0, returned_reads=0, accepted_writes=0;
integer expected_writes=0, pc, qi, ri, oq, orq, ow;
longint observer_operation=0, oracle_visible_at=0;
string scenario;
wire  src_clk;
wire  src_rst_n;
wire [30-1:0] src_region_base_sector;
wire [30-1:0] src_region_sector_count;
wire  src_prime_v;
wire  src_prime_ready;
wire [10-1:0] src_prime_user;
wire [21-1:0] src_prime_row;
wire  src_blk_v;
wire  src_blk_ready;
wire [10-1:0] src_blk_user;
wire [21-1:0] src_blk_row;
wire [3:0] src_blk_idx;
wire [255:0] src_blk_codes;
wire [7:0] src_blk_scale;
wire  src_prefetch_v;
wire  src_prefetch_ready;
wire [10-1:0] src_prefetch_user;
wire [21-1:0] src_prefetch_row;
wire  src_kv_ok;
wire  src_re;
wire [10-1:0] src_ruser;
wire [21-1:0] src_rrow;
wire [8:0] src_relem;
wire [31:0] src_q;
wire  src_packed_re;
wire [10-1:0] src_packed_ruser;
wire [21-1:0] src_packed_rrow;
wire [3:0] src_packed_ridx;
wire  src_packed_valid;
wire [4223:0] src_packed_row;
wire [255:0] src_packed_codes;
wire [7:0] src_packed_scale;
wire  src_bank_req_v;
wire  src_bank_req_ready;
wire [10-1:0] src_bank_req_user;
wire [21-1:0] src_bank_req_first;
wire [3:0] src_bank_req_mask;
wire  src_bank_rsp_v;
wire [10-1:0] src_bank_rsp_user;
wire [21-1:0] src_bank_rsp_first;
wire [3:0] src_bank_rsp_mask;
wire [3:0] src_bank_rsp_valid_mask;
wire [4*4224-1:0] src_bank_rsp_rows;
wire  src_bank_rsp_fault;
wire  src_fault;
wire [4:0] src_fault_code;
wire [31:0] src_st_rows_fetched;
wire [31:0] src_st_blocks_written;
wire [31:0] src_st_sectors_read;
wire [31:0] src_st_sectors_written;
wire [3:0] src_m_v;
wire [3:0] src_m_rdy;
wire [4*30-1:0] src_m_addr;
wire [4*4-1:0] src_m_len;
wire [4*16-1:0] src_m_tag;
wire [3:0] src_m_we;
wire [4*256-1:0] src_m_wdata;
wire [4*32-1:0] src_m_wstrb;
wire [3:0] src_m_wr_done;
wire [3:0] src_s_v;
wire [3:0] src_s_rdy;
wire [4*16-1:0] src_s_tag;
wire [4*4-1:0] src_s_beat;
wire [4*256-1:0] src_s_data;
wire  mux_clk;
wire [3:0] mux_w_v;
wire [3:0] mux_w_rdy;
wire [4*30-1:0] mux_w_addr;
wire [15:0] mux_w_len;
wire [4*16-1:0] mux_w_tag;
wire [3:0] mux_w_we;
wire [1023:0] mux_w_wdata;
wire [127:0] mux_w_wstrb;
wire [3:0] mux_w_wr_done;
wire [3:0] mux_w_sv;
wire [3:0] mux_w_srdy;
wire [4*16-1:0] mux_w_stag;
wire [15:0] mux_w_sbeat;
wire [1023:0] mux_w_sdata;
wire [3:0] mux_c_v;
wire [3:0] mux_c_rdy;
wire [4*30-1:0] mux_c_addr;
wire [15:0] mux_c_len;
wire [4*16-1:0] mux_c_tag;
wire [3:0] mux_c_we;
wire [1023:0] mux_c_wdata;
wire [127:0] mux_c_wstrb;
wire [3:0] mux_c_wr_done;
wire [3:0] mux_c_sv;
wire [3:0] mux_c_srdy;
wire [4*16-1:0] mux_c_stag;
wire [15:0] mux_c_sbeat;
wire [1023:0] mux_c_sdata;
wire [3:0] mux_p_v;
wire [3:0] mux_p_rdy;
wire [4*30-1:0] mux_p_addr;
wire [15:0] mux_p_len;
wire [4*16-1:0] mux_p_tag;
wire [3:0] mux_p_we;
wire [1023:0] mux_p_wdata;
wire [127:0] mux_p_wstrb;
wire [3:0] mux_p_wr_done;
wire [3:0] mux_p_sv;
wire [3:0] mux_p_srdy;
wire [4*16-1:0] mux_p_stag;
wire [15:0] mux_p_sbeat;
wire [1023:0] mux_p_sdata;
wire [3:0] mux_m_v;
wire [3:0] mux_m_rdy;
wire [4*30-1:0] mux_m_addr;
wire [15:0] mux_m_len;
wire [4*16-1:0] mux_m_tag;
wire [3:0] mux_m_we;
wire [1023:0] mux_m_wdata;
wire [127:0] mux_m_wstrb;
wire [3:0] mux_m_wr_done;
wire [3:0] mux_s_v;
wire [3:0] mux_s_rdy;
wire [4*16-1:0] mux_s_tag;
wire [15:0] mux_s_beat;
wire [1023:0] mux_s_data;
wire  mux_fault;
wire [31:0] mux_rope_grants;
wire [31:0] mux_rope_wait_cycles;
wire  arb_clk;
wire  arb_rst_n;
wire [32-1:0] arb_b_v;
wire [32-1:0] arb_b_rdy;
wire [32*30-1:0] arb_b_addr;
wire [32*4-1:0] arb_b_len;
wire [32*16-1:0] arb_b_tag;
wire [32-1:0] arb_b_we;
wire [32*256-1:0] arb_b_wdata;
wire [32*256/8-1:0] arb_b_wstrb;
wire [32-1:0] arb_b_wr_done;
wire [32-1:0] arb_b_rsp_v;
wire [32-1:0] arb_b_rsp_rdy;
wire [32*16-1:0] arb_b_rsp_tag;
wire [32*4-1:0] arb_b_rsp_beat;
wire [32*256-1:0] arb_b_rsp_data;
wire  arb_k_v;
wire  arb_k_rdy;
wire [30-1:0] arb_k_addr;
wire [4-1:0] arb_k_len;
wire [16-1:0] arb_k_tag;
wire  arb_k_we;
wire [256-1:0] arb_k_wdata;
wire [256/8-1:0] arb_k_wstrb;
wire  arb_k_wr_done;
wire  arb_k_rsp_v;
wire  arb_k_rsp_rdy;
wire [16-1:0] arb_k_rsp_tag;
wire [4-1:0] arb_k_rsp_beat;
wire [256-1:0] arb_k_rsp_data;
wire [32-1:0] arb_h_v;
wire [32-1:0] arb_h_rdy;
wire [32*30-1:0] arb_h_addr;
wire [32*4-1:0] arb_h_len;
wire [32*(16+1)-1:0] arb_h_tag;
wire [32-1:0] arb_h_we;
wire [32*256-1:0] arb_h_wdata;
wire [32*256/8-1:0] arb_h_wstrb;
wire [32-1:0] arb_h_wr_done;
wire [32-1:0] arb_r_v;
wire [32-1:0] arb_r_rdy;
wire [32*(16+1)-1:0] arb_r_tag;
wire [32*4-1:0] arb_r_beat;
wire [32*256-1:0] arb_r_data;
wire [31:0] arb_k_grants;
wire [31:0] arb_b_grants;
wire [31:0] arb_contended;
wire  back_clk;
wire  back_rst_n;
wire [32-1:0] back_req_v;
wire [32-1:0] back_req_rdy;
wire [32*30-1:0] back_req_addr;
wire [32*4-1:0] back_req_len;
wire [32*17-1:0] back_req_tag;
wire [32-1:0] back_req_we;
wire [32*256-1:0] back_req_wdata;
wire [32*(256/8)-1:0] back_req_wstrb;
wire [32-1:0] back_wr_done;
wire [32-1:0] back_rsp_v;
wire [32-1:0] back_rsp_rdy;
wire [32*17-1:0] back_rsp_tag;
wire [32*4-1:0] back_rsp_beat;
wire [32*256-1:0] back_rsp_data;
assign src_clk = clk;
assign src_rst_n = rst_n;
assign src_region_base_sector = 30'd262144;
assign src_region_sector_count = 30'd2176;
assign src_prime_v = prime;
assign src_prime_user = '0;
assign src_prime_row = '0;
assign src_blk_v = block_offer;
assign src_blk_user = '0;
assign src_blk_row = '0;
assign src_blk_idx = '0;
assign src_blk_codes = '0;
assign src_blk_scale = 8'd127;
assign src_prefetch_v = prefetch;
assign src_prefetch_user = '0;
assign src_prefetch_row = '0;
assign src_re = '0;
assign src_ruser = '0;
assign src_rrow = '0;
assign src_relem = '0;
assign src_packed_re = fault_pulse;
assign src_packed_ruser = '0;
assign src_packed_rrow = '0;
assign src_packed_ridx = '0;
assign src_bank_req_v = '0;
assign src_bank_req_user = '0;
assign src_bank_req_first = '0;
assign src_bank_req_mask = '0;
assign src_m_rdy = mux_w_rdy;
assign src_m_wr_done = mux_w_wr_done;
assign src_s_v = mux_w_sv;
assign src_s_tag = mux_w_stag;
assign src_s_beat = mux_w_sbeat;
assign src_s_data = mux_w_sdata;
assign mux_clk = clk;
assign mux_w_v = src_m_v;
assign mux_w_addr = src_m_addr;
assign mux_w_len = src_m_len;
assign mux_w_tag = src_m_tag;
assign mux_w_we = src_m_we;
assign mux_w_wdata = src_m_wdata;
assign mux_w_wstrb = src_m_wstrb;
assign mux_w_srdy = src_s_rdy;
assign mux_c_v = (4'(ckv_offer) << 2);
assign mux_c_addr = (120'(30'd20) << 60);
assign mux_c_len = (16'(4'd1) << 8);
assign mux_c_tag = '0;
assign mux_c_we = '0;
assign mux_c_wdata = '0;
assign mux_c_wstrb = '0;
assign mux_c_srdy = 4'hf;
assign mux_p_v = '0;
assign mux_p_addr = '0;
assign mux_p_len = '0;
assign mux_p_tag = '0;
assign mux_p_we = '0;
assign mux_p_wdata = '0;
assign mux_p_wstrb = '0;
assign mux_p_srdy = 4'hf;
assign mux_m_rdy = (4'(arb_k_rdy) << 2);
assign mux_m_wr_done = (4'(arb_k_wr_done) << 2);
assign mux_s_v = (4'(arb_k_rsp_v) << 2);
assign mux_s_tag = (64'(arb_k_rsp_tag) << 32);
assign mux_s_beat = (16'(arb_k_rsp_beat) << 8);
assign mux_s_data = (1024'(arb_k_rsp_data) << 512);
assign arb_clk = clk;
assign arb_rst_n = rst_n;
assign arb_b_v = (32'(b_offer) << 31);
assign arb_b_addr = (960'(30'd124) << 930);
assign arb_b_len = (128'(4'd1) << 124);
assign arb_b_tag = '0;
assign arb_b_we = (32'(b_offer && b_is_write) << 31);
assign arb_b_wdata = '0;
assign arb_b_wstrb = (1024'(32'hffffffff) << 992);
assign arb_b_rsp_rdy = 32'hffffffff;
assign arb_k_v = mux_m_v[2];
assign arb_k_addr = mux_m_addr[60 +: 30];
assign arb_k_len = mux_m_len[8 +: 4];
assign arb_k_tag = mux_m_tag[32 +: 16];
assign arb_k_we = mux_m_we[2];
assign arb_k_wdata = mux_m_wdata[512 +: 256];
assign arb_k_wstrb = mux_m_wstrb[64 +: 32];
assign arb_k_rsp_rdy = mux_s_rdy[2];
assign arb_h_rdy = back_req_rdy;
assign arb_h_wr_done = back_wr_done;
assign arb_r_v = back_rsp_v & {32{!hold_return}};
assign arb_r_tag = back_rsp_tag;
assign arb_r_beat = back_rsp_beat;
assign arb_r_data = back_rsp_data;
assign back_clk = clk;
assign back_rst_n = rst_n;
assign back_req_v = arb_h_v;
assign back_req_addr = arb_h_addr;
assign back_req_len = arb_h_len;
assign back_req_tag = arb_h_tag;
assign back_req_we = arb_h_we;
assign back_req_wdata = arb_h_wdata;
assign back_req_wstrb = arb_h_wstrb;
assign back_rsp_rdy = arb_r_rdy & {32{!hold_return}};
ot_chip_v41x_window_kv_prefetch_recovery #(
 .POS_W(21),
 .SEC_W(30),
 .HAW(30),
 .TAGW(16),
 .USER_W(10),
 .BANKED_STAGE(0),
 .WIN_STACK(2),
 .REFILL_CREDITS(8),
 .WINDOW_SLOTS(128),
 .MAX_CONTEXT(1048576),
 .OPT_RECOVERY(1),
 .SELECT_STACK(2)
) src (
 .clk(src_clk),
 .rst_n(src_rst_n),
 .region_base_sector(src_region_base_sector),
 .region_sector_count(src_region_sector_count),
 .prime_v(src_prime_v),
 .prime_ready(src_prime_ready),
 .prime_user(src_prime_user),
 .prime_row(src_prime_row),
 .blk_v(src_blk_v),
 .blk_ready(src_blk_ready),
 .blk_user(src_blk_user),
 .blk_row(src_blk_row),
 .blk_idx(src_blk_idx),
 .blk_codes(src_blk_codes),
 .blk_scale(src_blk_scale),
 .prefetch_v(src_prefetch_v),
 .prefetch_ready(src_prefetch_ready),
 .prefetch_user(src_prefetch_user),
 .prefetch_row(src_prefetch_row),
 .kv_ok(src_kv_ok),
 .re(src_re),
 .ruser(src_ruser),
 .rrow(src_rrow),
 .relem(src_relem),
 .q(src_q),
 .packed_re(src_packed_re),
 .packed_ruser(src_packed_ruser),
 .packed_rrow(src_packed_rrow),
 .packed_ridx(src_packed_ridx),
 .packed_valid(src_packed_valid),
 .packed_row(src_packed_row),
 .packed_codes(src_packed_codes),
 .packed_scale(src_packed_scale),
 .bank_req_v(src_bank_req_v),
 .bank_req_ready(src_bank_req_ready),
 .bank_req_user(src_bank_req_user),
 .bank_req_first(src_bank_req_first),
 .bank_req_mask(src_bank_req_mask),
 .bank_rsp_v(src_bank_rsp_v),
 .bank_rsp_user(src_bank_rsp_user),
 .bank_rsp_first(src_bank_rsp_first),
 .bank_rsp_mask(src_bank_rsp_mask),
 .bank_rsp_valid_mask(src_bank_rsp_valid_mask),
 .bank_rsp_rows(src_bank_rsp_rows),
 .bank_rsp_fault(src_bank_rsp_fault),
 .fault(src_fault),
 .fault_code(src_fault_code),
 .st_rows_fetched(src_st_rows_fetched),
 .st_blocks_written(src_st_blocks_written),
 .st_sectors_read(src_st_sectors_read),
 .st_sectors_written(src_st_sectors_written),
 .m_v(src_m_v),
 .m_rdy(src_m_rdy),
 .m_addr(src_m_addr),
 .m_len(src_m_len),
 .m_tag(src_m_tag),
 .m_we(src_m_we),
 .m_wdata(src_m_wdata),
 .m_wstrb(src_m_wstrb),
 .m_wr_done(src_m_wr_done),
 .s_v(src_s_v),
 .s_rdy(src_s_rdy),
 .s_tag(src_s_tag),
 .s_beat(src_s_beat),
 .s_data(src_s_data),
 .rec_request(recover),
 .rec_token(token),
 .rec_commit(commit),
 .rec_down_empty(mux_empty),
 .rec_down_visible(mux_visible),
 .rec_down_token_ack(mux_ack),
 .rec_freeze(freeze),
 .rec_owner_empty(source_empty),
 .rec_restart_ready(restart_ready)
);
ot_chip_v41x_kv_rope_reqmux_recovery #(
 .HAW(30),
 .TAGW(16),
 .OPT_RECOVERY(1),
 .SELECT_STACK(2)
) mux (
 .clk(mux_clk),
 .w_v(mux_w_v),
 .w_rdy(mux_w_rdy),
 .w_addr(mux_w_addr),
 .w_len(mux_w_len),
 .w_tag(mux_w_tag),
 .w_we(mux_w_we),
 .w_wdata(mux_w_wdata),
 .w_wstrb(mux_w_wstrb),
 .w_wr_done(mux_w_wr_done),
 .w_sv(mux_w_sv),
 .w_srdy(mux_w_srdy),
 .w_stag(mux_w_stag),
 .w_sbeat(mux_w_sbeat),
 .w_sdata(mux_w_sdata),
 .c_v(mux_c_v),
 .c_rdy(mux_c_rdy),
 .c_addr(mux_c_addr),
 .c_len(mux_c_len),
 .c_tag(mux_c_tag),
 .c_we(mux_c_we),
 .c_wdata(mux_c_wdata),
 .c_wstrb(mux_c_wstrb),
 .c_wr_done(mux_c_wr_done),
 .c_sv(mux_c_sv),
 .c_srdy(mux_c_srdy),
 .c_stag(mux_c_stag),
 .c_sbeat(mux_c_sbeat),
 .c_sdata(mux_c_sdata),
 .p_v(mux_p_v),
 .p_rdy(mux_p_rdy),
 .p_addr(mux_p_addr),
 .p_len(mux_p_len),
 .p_tag(mux_p_tag),
 .p_we(mux_p_we),
 .p_wdata(mux_p_wdata),
 .p_wstrb(mux_p_wstrb),
 .p_wr_done(mux_p_wr_done),
 .p_sv(mux_p_sv),
 .p_srdy(mux_p_srdy),
 .p_stag(mux_p_stag),
 .p_sbeat(mux_p_sbeat),
 .p_sdata(mux_p_sdata),
 .m_v(mux_m_v),
 .m_rdy(mux_m_rdy),
 .m_addr(mux_m_addr),
 .m_len(mux_m_len),
 .m_tag(mux_m_tag),
 .m_we(mux_m_we),
 .m_wdata(mux_m_wdata),
 .m_wstrb(mux_m_wstrb),
 .m_wr_done(mux_m_wr_done),
 .s_v(mux_s_v),
 .s_rdy(mux_s_rdy),
 .s_tag(mux_s_tag),
 .s_beat(mux_s_beat),
 .s_data(mux_s_data),
 .fault(mux_fault),
 .rope_grants(mux_rope_grants),
 .rope_wait_cycles(mux_rope_wait_cycles),
 .rec_freeze(freeze),
 .rec_token(token),
 .rec_commit(commit),
 .rec_down_empty(arb_empty),
 .rec_down_visible(arb_visible),
 .rec_down_token_ack(arb_ack),
 .rec_owner_empty(mux_empty),
 .rec_visible_empty(mux_visible),
 .rec_token_ack(mux_ack)
);
ot_chip_v41x_hbm_karb_recovery #(
 .NPC(32),
 .AW(30),
 .TAGW(16),
 .LENW(4),
 .BEATW(4),
 .DW(256),
 .PIPE_OUT(0),
 .PIPE_RSP(0),
 .OPT_RECOVERY(1),
 .SELECT_STACK(2)
) arb (
 .clk(arb_clk),
 .rst_n(arb_rst_n),
 .b_v(arb_b_v),
 .b_rdy(arb_b_rdy),
 .b_addr(arb_b_addr),
 .b_len(arb_b_len),
 .b_tag(arb_b_tag),
 .b_we(arb_b_we),
 .b_wdata(arb_b_wdata),
 .b_wstrb(arb_b_wstrb),
 .b_wr_done(arb_b_wr_done),
 .b_rsp_v(arb_b_rsp_v),
 .b_rsp_rdy(arb_b_rsp_rdy),
 .b_rsp_tag(arb_b_rsp_tag),
 .b_rsp_beat(arb_b_rsp_beat),
 .b_rsp_data(arb_b_rsp_data),
 .k_v(arb_k_v),
 .k_rdy(arb_k_rdy),
 .k_addr(arb_k_addr),
 .k_len(arb_k_len),
 .k_tag(arb_k_tag),
 .k_we(arb_k_we),
 .k_wdata(arb_k_wdata),
 .k_wstrb(arb_k_wstrb),
 .k_wr_done(arb_k_wr_done),
 .k_rsp_v(arb_k_rsp_v),
 .k_rsp_rdy(arb_k_rsp_rdy),
 .k_rsp_tag(arb_k_rsp_tag),
 .k_rsp_beat(arb_k_rsp_beat),
 .k_rsp_data(arb_k_rsp_data),
 .h_v(arb_h_v),
 .h_rdy(arb_h_rdy),
 .h_addr(arb_h_addr),
 .h_len(arb_h_len),
 .h_tag(arb_h_tag),
 .h_we(arb_h_we),
 .h_wdata(arb_h_wdata),
 .h_wstrb(arb_h_wstrb),
 .h_wr_done(arb_h_wr_done),
 .r_v(arb_r_v),
 .r_rdy(arb_r_rdy),
 .r_tag(arb_r_tag),
 .r_beat(arb_r_beat),
 .r_data(arb_r_data),
 .k_grants(arb_k_grants),
 .b_grants(arb_b_grants),
 .contended(arb_contended),
 .rec_freeze(freeze),
 .rec_token(token),
 .rec_commit(commit),
 .rec_down_empty(back_empty),
 .rec_down_visible(back_visible),
 .rec_down_token_ack(back_ack),
 .rec_owner_empty(arb_empty),
 .rec_visible_empty(arb_visible),
 .rec_token_ack(arb_ack)
);
ot_hdc_v41x_idx_hbm_recovery #(
 .NPC(32),
 .AW(30),
 .TAGW(17),
 .LENW(4),
 .BEATW(4),
 .DW(256),
 .QD(64),
 .RQD(32),
 .RW(16),
 .MAXSKIP(16),
 .REFPB(3),
 .CLK_PS(1000),
 .MEM_MODE(0),
 .MEM_WORDS(264320),
 .OPT_RECOVERY(1),
 .SELECT_STACK(2)
) back (
 .clk(back_clk),
 .rst_n(back_rst_n),
 .req_v(back_req_v),
 .req_rdy(back_req_rdy),
 .req_addr(back_req_addr),
 .req_len(back_req_len),
 .req_tag(back_req_tag),
 .req_we(back_req_we),
 .req_wdata(back_req_wdata),
 .req_wstrb(back_req_wstrb),
 .wr_done(back_wr_done),
 .rsp_v(back_rsp_v),
 .rsp_rdy(back_rsp_rdy),
 .rsp_tag(back_rsp_tag),
 .rsp_beat(back_rsp_beat),
 .rsp_data(back_rsp_data),
 .rec_freeze(freeze),
 .rec_token(token),
 .rec_commit(commit),
 .rec_owner_empty(back_empty),
 .rec_visible_empty(back_visible),
 .rec_token_ack(back_ack)
);
// Independent quiescence oracle: no identities travel on candidate wires.
always @(posedge clk) begin
 if(rst_n) begin
  cycles=cycles+1;
  if(cycles>250000) $fatal(1,"bounded recovery case timeout; ownership retained");
  if(src_blk_v && src_blk_ready) expected_writes=expected_writes+2;
  for(pc=0;pc<32;pc=pc+1) begin
   if(back_req_v[pc] && back_req_rdy[pc] && back_req_tag[pc*17+14 +: 3]!=3'b100) begin
    other_grants=other_grants+1;
    if(back_req_we[pc]) other_writes=other_writes+1; else other_reads=other_reads+1;
   end
   if(back_rsp_v[pc] && back_rsp_rdy[pc] && back_rsp_tag[pc*17+14 +: 3]!=3'b100)
    other_returns=other_returns+1;
   if(back_req_v[pc] && back_req_rdy[pc] && back_req_tag[pc*17+14 +: 3]==3'b100) begin
    if(back_req_we[pc]) accepted_writes=accepted_writes+1;
    else accepted_reads=accepted_reads+1;
   end
   if(back_rsp_v[pc] && back_rsp_rdy[pc] && back_rsp_tag[pc*17+14 +: 3]==3'b100)
    returned_reads=returned_reads+1;
  end
 end
end
// Finite B/CKV interference, driven away from sampling edge. B onPC31 and
// CKV onPC5 do not alias WINDOW block0 WCpc0 / WSpc4 visibility oracle.
always @(negedge clk) if(rst_n) begin
 b_offer=(cycles%13==0); ckv_offer=(cycles%17==0); b_is_write=(cycles%2==0);
end
// Post-NBA sample prevents mistaking registered offers for absent ownership.
always @(negedge clk) if(rst_n) begin
 other_qr_total=0; other_qw_total=0;
 for(pc=0;pc<32;pc=pc+1) begin
  oq=0; orq=0; ow=0;
  for(qi=0;qi<back.g_recovery.u_impl.q_n[pc];qi=qi+1)
   if(back.g_recovery.u_impl.q_tag[pc][(back.g_recovery.u_impl.q_rp[pc]+qi)%64][16:14]==3'b100) begin
    if(back.g_recovery.u_impl.q_we[pc][(back.g_recovery.u_impl.q_rp[pc]+qi)%64]) ow=ow+1;
    else oq=oq+1;
   end else begin
    if(back.g_recovery.u_impl.q_we[pc][(back.g_recovery.u_impl.q_rp[pc]+qi)%64]) other_qw_total=other_qw_total+1;
    else other_qr_total=other_qr_total+1;
   end
  for(ri=0;ri<back.g_recovery.u_impl.r_n[pc];ri=ri+1)
   if(back.g_recovery.u_impl.r_tag[pc][(back.g_recovery.u_impl.r_rp[pc]+ri)%32][16:14]==3'b100) orq=orq+1; else other_qr_total=other_qr_total+1;
  if(back.g_recovery.u_impl.rec_reads[pc] != oq+orq || back.g_recovery.u_impl.rec_writes[pc] != ow)
   $fatal(1,"observer ring/ledger mismatch");
  // Existing schedule history records column timestamps, independent of new watermark.
  if((pc==0 || pc==4) && back.g_recovery.u_impl.last_wr[pc]>=0 && back.g_recovery.u_impl.last_wr[pc]+7274 > oracle_visible_at)
   oracle_visible_at=back.g_recovery.u_impl.last_wr[pc]+7274;
 end
 if(other_reads-other_returns != other_qr_total ||
    other_writes-back.g_recovery.u_impl.st_wr[31] != other_qw_total)
  $fatal(1,"observer unrelated owner conservation");
 if(restart_ready && (accepted_reads!=returned_reads || expected_writes!=accepted_writes ||
     back.g_recovery.u_impl.now<oracle_visible_at || hold_return))
  $fatal(1,"observer premature closed/visible fence");
 if(freeze && (src_packed_valid || src_kv_ok)) $fatal(1,"fault publication");
end

task automatic tick(); @(posedge clk); #0.001; endtask
task automatic freeze_fault();
 @(negedge clk); recover=1; fault_pulse=1;
 tick(); @(negedge clk); fault_pulse=0;
endtask
task automatic drain_and_restart();
 wait(restart_ready); @(negedge clk); commit=1;
 tick(); @(negedge clk); commit=0; recover=0; token=!token;
 observer_operation=observer_operation+1;
 tick(); if(src_fault) $fatal(1,"fault did not clear after certified fence");
endtask
initial begin
 if(!$value$plusargs("CASE=%s",scenario)) scenario="READ_HELD";
 repeat(3) tick(); @(negedge clk); rst_n=1;
 // Legal synthetic backing; no checkpoint/model payload reads.
 back.g_recovery.u_impl.mem[20]=0; back.g_recovery.u_impl.mem[124]=0;
 for(qi=262144;qi<264320;qi=qi+1) back.g_recovery.u_impl.mem[qi]=0;
 tick(); @(negedge clk); prime=1; tick(); @(negedge clk); prime=0;
 if(scenario=="READ_HELD") begin
  @(negedge clk); prefetch=1; tick(); @(negedge clk); prefetch=0; hold_return=1;
  wait(|back_rsp_v); freeze_fault(); repeat(12) tick();
  if(restart_ready) $fatal(1,"held return admitted restart");
  @(negedge clk); hold_return=0;
 end else if(scenario=="WC_INTENT" || scenario=="WS_VISIBLE") begin
  @(negedge clk); block_offer=1; tick(); @(negedge clk); block_offer=0;
  if(scenario=="WC_INTENT") wait(src.g_recovery.u_impl.state==2);
  else wait(src.g_recovery.u_impl.state==4);
  freeze_fault();
 end else $fatal(1,"unreviewed recovery scenario");
 drain_and_restart();
 if(other_grants==0) $fatal(1,"other clients never exercised");
 if(expected_writes!=accepted_writes || accepted_reads!=returned_reads)
  $fatal(1,"ownership not drained");
 $display("PREPARED_RECOVERY_CASE_PASS case=%s cycles=%0d reads=%0d replies=%0d writes=%0d observerop=%0d",scenario,cycles,accepted_reads,returned_reads,accepted_writes,observer_operation);
 $finish;
end
endmodule
