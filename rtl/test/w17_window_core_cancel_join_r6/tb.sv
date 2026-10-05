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
string scenario, control;
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

localparam integer OPT_CORE_PRODUCER_CANCEL = 1;
localparam integer FULL_SHAPE = 1;
localparam integer INSTR_BITS = FULL_SHAPE ? 2048 : 1536;
localparam integer W = 16;
localparam integer G = 4;
localparam integer IL = 8;
localparam integer BL = 16;
localparam integer QLB = 272;
localparam integer AW = FULL_SHAPE ? 30 : 24;
localparam integer NW = FULL_SHAPE ? 21 : 16;
localparam integer PAW = 14;
localparam integer DIM = FULL_SHAPE ? 5120 : 160;
localparam integer TOPK = FULL_SHAPE ? 512 : 16;
localparam integer HDIM = FULL_SHAPE ? 512 : 32;
localparam integer ROPE_PAIR = FULL_SHAPE ? 32 : 2;
localparam integer FULL_WINDOW = 128;
localparam integer FULL_SCAN_CAP = 16384;
localparam integer FULL_TP = 4;
localparam integer XU_KW = FULL_SHAPE ? 12 : 5;
localparam integer HNL = 3;
localparam integer SW = 8;
localparam integer HS = 8;
localparam integer W_HBM = 0;
localparam integer KV_HBM = 1;
localparam integer ME0_HBM = 0;
localparam integer NSLOT = 1;
localparam integer MP = 1;
localparam integer X_HE = 1;
localparam integer X_ME = 0;
localparam integer X_ME_XBANK = 0;
localparam integer X_ATT = 0;
localparam integer X_IDX = 0;
localparam integer PIKH_HAW = FULL_SHAPE ? 30 : 28;
localparam integer IDX_SHARDED = 0;
localparam integer IDX_MULTIUSER = 0;
localparam integer IDX_KEY_SLICE_SECTORS = 0;
localparam integer IDX_RING = 0;
localparam integer IDX_RING_RSB = 1;
localparam integer IDX_RING_RTAIL = 0;
localparam integer X_SEL = 0;
localparam integer X_EG = 0;
localparam integer XSQ = 4;
localparam integer XSW = 16;
localparam integer X_SU = 1;
localparam integer SUN = 256;
localparam integer SUM = 64;
localparam integer SULV = 7;
localparam integer SUBCAST = 0;
localparam integer SURET = 0;
localparam integer HHW = 8;
localparam integer HTL = 9;
localparam integer HBAW = 16;
localparam integer MG = 8;
localparam integer MBAW = FULL_SHAPE ? 18 : 17;
localparam integer RANK = 0;
localparam integer X_ROM = 0;
localparam integer ROM_R = 128;
localparam integer ROM_PHW = 6;
localparam integer ROM_SAW = 16;
localparam integer ROM_BST = 17;
localparam integer ROM_VRD = 64;
localparam integer ROM_FBW = 1 + ROM_PHW + 3 + 1 + 1 + 1 + 8 + 3 + 2 + 256 + 10 + 256 + 10 + 3 + 3 + 1 + 3 + 4 + 32 + 1024;
localparam integer ROM_FRW = ROM_R * 69;
localparam integer ATT_TW = 1 + 16 + 1 + HDIM*16 + 1 + 4 + 4*(HDIM/32)*265 + 1 + 1 + 32*16 + 1;
localparam integer ATT_FW = 4 + 16 + 4 + 4*16*32 + 4*16 + 2 + 8 + 4*(HDIM/32)*16*32 + 4*(HDIM/32)*16;
logic  core_clk=0;
logic  core_rst_n=0;
logic  core_start=0;
logic [NW-1:0] core_token=0;
logic [NW-1:0] core_pos=0;
logic [PAW-1:0] core_entry=0;
wire  core_done;
wire [3:0] core_acc_n;
wire [NSLOT*NW-1:0] core_acc_tok;
wire [NW-1:0] core_next_token;
wire [31:0] core_next_val;
wire [31:0] core_cycles;
wire  core_fault;
wire  core_rom_xre;
wire [AW-1:0] core_rom_xaddr;
logic [ROM_VRD*32-1:0] core_rom_xq=0;
wire [ROM_R-1:0] core_rom_we;
wire [ROM_R*AW-1:0] core_rom_waddr;
wire [ROM_R*32-1:0] core_rom_wdata;
wire  core_rom_vre;
wire [AW-1:0] core_rom_vaddr;
logic [31:0] core_rom_vq=0;
wire [ROM_FBW-1:0] core_rom_fb;
logic [ROM_FRW-1:0] core_rom_fr=0;
logic  core_rom_ffault=0;
wire [ATT_TW-1:0] core_att_to;
logic [ATT_FW-1:0] core_att_from=0;
logic  core_prime_v=0;
logic  core_prime_first=0;
logic [11:0] core_prime_cid=0;
wire  core_prog_re;
wire [PAW-1:0] core_prog_addr;
logic [INSTR_BITS-1:0] core_prog_q=0;
wire  core_wrom_re;
wire [AW-1:0] core_wrom_addr;
logic [G*W*16-1:0] core_wrom_q=0;
wire [MP*SW-1:0] core_ewrom_re;
wire [MP*SW*AW-1:0] core_ewrom_addr;
logic [MP*SW*G*W*16-1:0] core_ewrom_q=0;
wire  core_hrom_re;
wire [AW-1:0] core_hrom_addr;
logic [HS*HNL*32-1:0] core_hrom_q=0;
logic [AW-1:0] core_cfg_ik_base=0;
logic [PIKH_HAW-1:0] core_idx_user_base_sec=0;
logic [3:0] core_cfg_me_xs=0;
wire [7:0] core_mb_re;
wire [8*MBAW-1:0] core_mb_addr;
logic [8*MG*32-1:0] core_mb_q=0;
wire [SUN-1:0] core_xs_vi_re;
wire [SUN*AW-1:0] core_xs_vi_addr;
logic [SUN*32-1:0] core_xs_vi_q=0;
wire [4*SUN-1:0] core_xs_rd_re;
wire [4*SUN*AW-1:0] core_xs_rd_addr;
wire [8*SUN-1:0] core_xs_rd_src;
logic [4*SUN*32-1:0] core_xs_rd_q=0;
wire [SUN-1:0] core_xs_vm_we;
wire [SUN*AW-1:0] core_xs_vm_waddr;
wire [SUN*32-1:0] core_xs_vm_wdata;
wire [SUN-1:0] core_xs_kv_we;
wire [SUN*AW-1:0] core_xs_kv_waddr;
wire [SUN*32-1:0] core_xs_kv_wdata;
wire [SUN/8-1:0] core_xs_res_we;
wire [SUN/8*AW-1:0] core_xs_res_addr;
wire [SUN/8*32-1:0] core_xs_res_data;
wire [7:0] core_hb_re;
wire [8*HBAW-1:0] core_hb_addr;
logic [8*HHW*32-1:0] core_hb_q=0;
wire [31:0] core_ikh_req_v;
logic [31:0] core_ikh_req_rdy=0;
wire [32*28-1:0] core_ikh_req_addr;
wire [32*4-1:0] core_ikh_req_len;
wire [32*16-1:0] core_ikh_req_tag;
logic [31:0] core_ikh_rsp_v=0;
wire [31:0] core_ikh_rsp_rdy;
logic [32*16-1:0] core_ikh_rsp_tag=0;
logic [32*4-1:0] core_ikh_rsp_beat=0;
logic [32*256-1:0] core_ikh_rsp_data=0;
wire  core_ikw_v;
wire [27:0] core_ikw_csec;
wire [127:0] core_ikw_codes;
wire [27:0] core_ikw_ssec;
wire [2:0] core_ikw_sslot;
wire [7:0] core_ikw_scale;
wire [127:0] core_pikh_req_v;
logic [127:0] core_pikh_req_rdy=0;
wire [128*PIKH_HAW-1:0] core_pikh_req_addr;
wire [128*4-1:0] core_pikh_req_len;
wire [128*16-1:0] core_pikh_req_tag;
logic [127:0] core_pikh_rsp_v=0;
wire [127:0] core_pikh_rsp_rdy;
logic [128*16-1:0] core_pikh_rsp_tag=0;
logic [128*4-1:0] core_pikh_rsp_beat=0;
logic [128*256-1:0] core_pikh_rsp_data=0;
wire  core_pikw_v;
logic  core_pikw_rdy=0;
wire [3:0] core_pikw_stack_mask;
wire [PIKH_HAW-1:0] core_pikw_csec;
wire [511:0] core_pikw_codes;
wire [PIKH_HAW-1:0] core_pikw_ssec;
wire [2:0] core_pikw_sslot;
wire [31:0] core_pikw_scales;
wire  core_qrom_re;
wire [AW-1:0] core_qrom_addr;
logic [BL*QLB-1:0] core_qrom_q=0;
wire  core_erom_re;
wire [AW-1:0] core_erom_addr;
logic [263:0] core_erom_q=0;
wire [MP*4*SW-1:0] core_crom_re;
wire [MP*4*SW*AW-1:0] core_crom_addr;
logic [MP*4*SW*64-1:0] core_crom_q=0;
wire  core_xcrom_re;
wire [AW-1:0] core_xcrom_addr;
logic [63:0] core_xcrom_q=0;
wire  core_kv_re;
wire [G*AW-1:0] core_kv_raddr;
logic [G*W*32-1:0] core_kv_q=0;
wire [MP*SW-1:0] core_kv_we;
wire [MP*SW*AW-1:0] core_kv_waddr;
wire [MP*SW*32-1:0] core_kv_wdata;
logic  core_att_packed_kv_v=0;
wire  core_att_packed_kv_ready;
logic [3:0] core_att_packed_kv_m=0;
logic [4*(HDIM/32)*265-1:0] core_att_packed_kv_w=0;
logic  core_att_packed_kv_fault=0;
wire  core_att_packed_issue;
wire  core_att_packed_idle;
wire  core_win_blk_v;
logic  core_win_blk_ready=0;
wire [AW-1:0] core_win_blk_kvt_base;
wire [NW-1:0] core_win_blk_row;
wire [NW-1:0] core_win_blk_kvt_row;
wire [3:0] core_win_blk_idx;
wire [AW-1:0] core_win_blk_first_elem;
wire [255:0] core_win_blk_codes;
wire [7:0] core_win_blk_scale;
wire [MP*G-1:0] core_vx_re;
wire [MP*G*AW-1:0] core_vx_addr;
logic [MP*G*32-1:0] core_vx_q=0;
wire [MP*4*SW-1:0] core_vs_re;
wire [MP*4*SW*AW-1:0] core_vs_addr;
logic [MP*4*SW*32-1:0] core_vs_q=0;
wire [MP*SW-1:0] core_vi_re;
wire [MP*SW*AW-1:0] core_vi_addr;
logic [MP*SW*32-1:0] core_vi_q=0;
wire  core_vq_re;
wire [AW-1:0] core_vq_addr;
logic [31:0] core_vq_q=0;
wire  core_vr_re;
wire [AW-1:0] core_vr_addr;
logic [31:0] core_vr_q=0;
wire  core_wqr_re;
wire [AW-1:0] core_wqr_addr;
logic [1023:0] core_wqr_q=0;
wire [MP*HS-1:0] core_vh_re;
wire [MP*HS*AW-1:0] core_vh_addr;
logic [MP*HS*32-1:0] core_vh_q=0;
wire  core_wxr_re;
wire [AW-1:0] core_wxr_addr;
logic [1023:0] core_wxr_q=0;
wire [XSQ-1:0] core_vsl_re;
wire [XSQ*AW-1:0] core_vsl_addr;
logic [XSQ*XSW*32-1:0] core_vsl_q=0;
wire [MP*G-1:0] core_vw_me_we;
wire [MP*G*AW-1:0] core_vw_me_addr;
wire [MP*G*W-1:0] core_vw_me_mask;
wire [MP*G*W*32-1:0] core_vw_me_data;
wire [MP*SW-1:0] core_vw_su_we;
wire [MP*SW*AW-1:0] core_vw_su_addr;
wire [MP*SW*32-1:0] core_vw_su_data;
wire [MP*SW-1:0] core_vw_rd_we;
wire [MP*SW*AW-1:0] core_vw_rd_addr;
wire [MP*SW*32-1:0] core_vw_rd_data;
wire  core_vw_xe_we;
wire [AW-1:0] core_vw_xe_addr;
wire [31:0] core_vw_xe_data;
wire [MP-1:0] core_ww_q_we;
wire [MP*AW-1:0] core_ww_q_addr;
wire [MP*32-1:0] core_ww_q_mask;
wire [MP*1024-1:0] core_ww_q_data;
wire [MP-1:0] core_ww_h_we;
wire [MP*AW-1:0] core_ww_h_addr;
wire [MP*32-1:0] core_ww_h_mask;
wire [MP*1024-1:0] core_ww_h_data;
wire  core_ww_x_we;
wire [AW-1:0] core_ww_x_addr;
wire [31:0] core_ww_x_mask;
wire [1023:0] core_ww_x_data;
wire  core_me_ov;
wire [MP*G*AW-1:0] core_me_oaddr;
wire [MP*G*W-1:0] core_me_omask;
wire [MP*G*W*32-1:0] core_me_odata;
wire [4:0] core_unit_busy;
wire [2:0] core_issue_unit;
wire  core_coll_go;
wire [1:0] core_coll_op;
wire [AW-1:0] core_coll_src;
wire [NW-1:0] core_coll_n;
wire [11:0] core_coll_k;
wire [31:0] core_coll_stride;
wire [7:0] core_coll_seq;
wire  core_coll_rnd;
logic  core_coll_busy=0;
wire  core_qd_v;
wire [AW-1:0] core_qd_wbase;
wire [7:0] core_qd_nb;
wire [NW-1:0] core_qd_tiles;
logic  core_q_ok=0;
wire  core_m0d_v;
wire [AW-1:0] core_m0d_wbase;
wire [NW-1:0] core_m0d_nout;
wire [AW-1:0] core_m0d_xjs;
wire [1:0] core_m0d_split;
logic  core_m0_select=0;
logic  core_m0_ok=0;
wire  core_kvd_v;
wire [AW-1:0] core_kvd_wbase;
wire [NW-1:0] core_kvd_tiles;
wire [1:0] core_kvd_hg;
wire  core_kvd_mmode;
logic  core_kv_ok=0;
wire  core_rope_pf_v;
logic  core_rope_pf_rdy=0;
wire  core_rope_pf_kind;
wire [NW-1:0] core_rope_pf_pos;
logic  core_rope_pf_done=0;
wire  core_rope_pf_release;
logic  core_rope_pf_fault=0;
wire  core_wrel_v;
logic  core_rec_request=0;
logic  core_rec_token=0;
logic  core_rec_rearm_request=0;
logic  core_rec_provider_ready=0;
logic  core_rec_delivery_certified=0;
logic  core_rec_visibility_certified=0;
logic  core_rec_provenance_valid=0;
logic  core_rec_fault_inject=0;
wire  core_rec_frozen_out;
wire  core_rec_local_ack;
wire  core_rec_local_token_ack;
wire  core_rec_commit_qualified;
wire  core_rec_provenance_fault;
ot_hdc_core_v41x_cancel_fastpp #(.OPT_CORE_PRODUCER_CANCEL(OPT_CORE_PRODUCER_CANCEL),.FULL_SHAPE(FULL_SHAPE),.KV_HBM(KV_HBM),.X_SU(X_SU),.SUN(SUN),.SUM(SUM),.X_ROM(X_ROM),.NSLOT(NSLOT),.MP(MP)) core (
.clk(core_clk),
.rst_n(core_rst_n),
.start(core_start),
.token(core_token),
.pos(core_pos),
.entry(core_entry),
.done(core_done),
.acc_n(core_acc_n),
.acc_tok(core_acc_tok),
.next_token(core_next_token),
.next_val(core_next_val),
.cycles(core_cycles),
.fault(core_fault),
.rom_xre(core_rom_xre),
.rom_xaddr(core_rom_xaddr),
.rom_xq(core_rom_xq),
.rom_we(core_rom_we),
.rom_waddr(core_rom_waddr),
.rom_wdata(core_rom_wdata),
.rom_vre(core_rom_vre),
.rom_vaddr(core_rom_vaddr),
.rom_vq(core_rom_vq),
.rom_fb(core_rom_fb),
.rom_fr(core_rom_fr),
.rom_ffault(core_rom_ffault),
.att_to(core_att_to),
.att_from(core_att_from),
.prime_v(core_prime_v),
.prime_first(core_prime_first),
.prime_cid(core_prime_cid),
.prog_re(core_prog_re),
.prog_addr(core_prog_addr),
.prog_q(core_prog_q),
.wrom_re(core_wrom_re),
.wrom_addr(core_wrom_addr),
.wrom_q(core_wrom_q),
.ewrom_re(core_ewrom_re),
.ewrom_addr(core_ewrom_addr),
.ewrom_q(core_ewrom_q),
.hrom_re(core_hrom_re),
.hrom_addr(core_hrom_addr),
.hrom_q(core_hrom_q),
.cfg_ik_base(core_cfg_ik_base),
.idx_user_base_sec(core_idx_user_base_sec),
.cfg_me_xs(core_cfg_me_xs),
.mb_re(core_mb_re),
.mb_addr(core_mb_addr),
.mb_q(core_mb_q),
.xs_vi_re(core_xs_vi_re),
.xs_vi_addr(core_xs_vi_addr),
.xs_vi_q(core_xs_vi_q),
.xs_rd_re(core_xs_rd_re),
.xs_rd_addr(core_xs_rd_addr),
.xs_rd_src(core_xs_rd_src),
.xs_rd_q(core_xs_rd_q),
.xs_vm_we(core_xs_vm_we),
.xs_vm_waddr(core_xs_vm_waddr),
.xs_vm_wdata(core_xs_vm_wdata),
.xs_kv_we(core_xs_kv_we),
.xs_kv_waddr(core_xs_kv_waddr),
.xs_kv_wdata(core_xs_kv_wdata),
.xs_res_we(core_xs_res_we),
.xs_res_addr(core_xs_res_addr),
.xs_res_data(core_xs_res_data),
.hb_re(core_hb_re),
.hb_addr(core_hb_addr),
.hb_q(core_hb_q),
.ikh_req_v(core_ikh_req_v),
.ikh_req_rdy(core_ikh_req_rdy),
.ikh_req_addr(core_ikh_req_addr),
.ikh_req_len(core_ikh_req_len),
.ikh_req_tag(core_ikh_req_tag),
.ikh_rsp_v(core_ikh_rsp_v),
.ikh_rsp_rdy(core_ikh_rsp_rdy),
.ikh_rsp_tag(core_ikh_rsp_tag),
.ikh_rsp_beat(core_ikh_rsp_beat),
.ikh_rsp_data(core_ikh_rsp_data),
.ikw_v(core_ikw_v),
.ikw_csec(core_ikw_csec),
.ikw_codes(core_ikw_codes),
.ikw_ssec(core_ikw_ssec),
.ikw_sslot(core_ikw_sslot),
.ikw_scale(core_ikw_scale),
.pikh_req_v(core_pikh_req_v),
.pikh_req_rdy(core_pikh_req_rdy),
.pikh_req_addr(core_pikh_req_addr),
.pikh_req_len(core_pikh_req_len),
.pikh_req_tag(core_pikh_req_tag),
.pikh_rsp_v(core_pikh_rsp_v),
.pikh_rsp_rdy(core_pikh_rsp_rdy),
.pikh_rsp_tag(core_pikh_rsp_tag),
.pikh_rsp_beat(core_pikh_rsp_beat),
.pikh_rsp_data(core_pikh_rsp_data),
.pikw_v(core_pikw_v),
.pikw_rdy(core_pikw_rdy),
.pikw_stack_mask(core_pikw_stack_mask),
.pikw_csec(core_pikw_csec),
.pikw_codes(core_pikw_codes),
.pikw_ssec(core_pikw_ssec),
.pikw_sslot(core_pikw_sslot),
.pikw_scales(core_pikw_scales),
.qrom_re(core_qrom_re),
.qrom_addr(core_qrom_addr),
.qrom_q(core_qrom_q),
.erom_re(core_erom_re),
.erom_addr(core_erom_addr),
.erom_q(core_erom_q),
.crom_re(core_crom_re),
.crom_addr(core_crom_addr),
.crom_q(core_crom_q),
.xcrom_re(core_xcrom_re),
.xcrom_addr(core_xcrom_addr),
.xcrom_q(core_xcrom_q),
.kv_re(core_kv_re),
.kv_raddr(core_kv_raddr),
.kv_q(core_kv_q),
.kv_we(core_kv_we),
.kv_waddr(core_kv_waddr),
.kv_wdata(core_kv_wdata),
.att_packed_kv_v(core_att_packed_kv_v),
.att_packed_kv_ready(core_att_packed_kv_ready),
.att_packed_kv_m(core_att_packed_kv_m),
.att_packed_kv_w(core_att_packed_kv_w),
.att_packed_kv_fault(core_att_packed_kv_fault),
.att_packed_issue(core_att_packed_issue),
.att_packed_idle(core_att_packed_idle),
.win_blk_v(core_win_blk_v),
.win_blk_ready(core_win_blk_ready),
.win_blk_kvt_base(core_win_blk_kvt_base),
.win_blk_row(core_win_blk_row),
.win_blk_kvt_row(core_win_blk_kvt_row),
.win_blk_idx(core_win_blk_idx),
.win_blk_first_elem(core_win_blk_first_elem),
.win_blk_codes(core_win_blk_codes),
.win_blk_scale(core_win_blk_scale),
.vx_re(core_vx_re),
.vx_addr(core_vx_addr),
.vx_q(core_vx_q),
.vs_re(core_vs_re),
.vs_addr(core_vs_addr),
.vs_q(core_vs_q),
.vi_re(core_vi_re),
.vi_addr(core_vi_addr),
.vi_q(core_vi_q),
.vq_re(core_vq_re),
.vq_addr(core_vq_addr),
.vq_q(core_vq_q),
.vr_re(core_vr_re),
.vr_addr(core_vr_addr),
.vr_q(core_vr_q),
.wqr_re(core_wqr_re),
.wqr_addr(core_wqr_addr),
.wqr_q(core_wqr_q),
.vh_re(core_vh_re),
.vh_addr(core_vh_addr),
.vh_q(core_vh_q),
.wxr_re(core_wxr_re),
.wxr_addr(core_wxr_addr),
.wxr_q(core_wxr_q),
.vsl_re(core_vsl_re),
.vsl_addr(core_vsl_addr),
.vsl_q(core_vsl_q),
.vw_me_we(core_vw_me_we),
.vw_me_addr(core_vw_me_addr),
.vw_me_mask(core_vw_me_mask),
.vw_me_data(core_vw_me_data),
.vw_su_we(core_vw_su_we),
.vw_su_addr(core_vw_su_addr),
.vw_su_data(core_vw_su_data),
.vw_rd_we(core_vw_rd_we),
.vw_rd_addr(core_vw_rd_addr),
.vw_rd_data(core_vw_rd_data),
.vw_xe_we(core_vw_xe_we),
.vw_xe_addr(core_vw_xe_addr),
.vw_xe_data(core_vw_xe_data),
.ww_q_we(core_ww_q_we),
.ww_q_addr(core_ww_q_addr),
.ww_q_mask(core_ww_q_mask),
.ww_q_data(core_ww_q_data),
.ww_h_we(core_ww_h_we),
.ww_h_addr(core_ww_h_addr),
.ww_h_mask(core_ww_h_mask),
.ww_h_data(core_ww_h_data),
.ww_x_we(core_ww_x_we),
.ww_x_addr(core_ww_x_addr),
.ww_x_mask(core_ww_x_mask),
.ww_x_data(core_ww_x_data),
.me_ov(core_me_ov),
.me_oaddr(core_me_oaddr),
.me_omask(core_me_omask),
.me_odata(core_me_odata),
.unit_busy(core_unit_busy),
.issue_unit(core_issue_unit),
.coll_go(core_coll_go),
.coll_op(core_coll_op),
.coll_src(core_coll_src),
.coll_n(core_coll_n),
.coll_k(core_coll_k),
.coll_stride(core_coll_stride),
.coll_seq(core_coll_seq),
.coll_rnd(core_coll_rnd),
.coll_busy(core_coll_busy),
.qd_v(core_qd_v),
.qd_wbase(core_qd_wbase),
.qd_nb(core_qd_nb),
.qd_tiles(core_qd_tiles),
.q_ok(core_q_ok),
.m0d_v(core_m0d_v),
.m0d_wbase(core_m0d_wbase),
.m0d_nout(core_m0d_nout),
.m0d_xjs(core_m0d_xjs),
.m0d_split(core_m0d_split),
.m0_select(core_m0_select),
.m0_ok(core_m0_ok),
.kvd_v(core_kvd_v),
.kvd_wbase(core_kvd_wbase),
.kvd_tiles(core_kvd_tiles),
.kvd_hg(core_kvd_hg),
.kvd_mmode(core_kvd_mmode),
.kv_ok(core_kv_ok),
.rope_pf_v(core_rope_pf_v),
.rope_pf_rdy(core_rope_pf_rdy),
.rope_pf_kind(core_rope_pf_kind),
.rope_pf_pos(core_rope_pf_pos),
.rope_pf_done(core_rope_pf_done),
.rope_pf_release(core_rope_pf_release),
.rope_pf_fault(core_rope_pf_fault),
.wrel_v(core_wrel_v),
.rec_request(core_rec_request),
.rec_token(core_rec_token),
.rec_rearm_request(core_rec_rearm_request),
.rec_provider_ready(core_rec_provider_ready),
.rec_delivery_certified(core_rec_delivery_certified),
.rec_visibility_certified(core_rec_visibility_certified),
.rec_provenance_valid(core_rec_provenance_valid),
.rec_fault_inject(core_rec_fault_inject),
.rec_frozen_out(core_rec_frozen_out),
.rec_local_ack(core_rec_local_ack),
.rec_local_token_ack(core_rec_local_token_ack),
.rec_commit_qualified(core_rec_commit_qualified),
.rec_provenance_fault(core_rec_provenance_fault));

wire guard_bad;
ot_chip_v41x_window_block_guard #(.AW(30),.POS_W(21)) guard (
 .step_pos(core_pos), .blk_abs_row(core_win_blk_row), .blk_kvt_row(core_win_blk_kvt_row),
 .blk_idx(core_win_blk_idx), .kvt_base(core_win_blk_kvt_base), .first_elem(core_win_blk_first_elem),
 .hbm_slot(), .expected_first(), .bad(guard_bad));
// Only synthetic finite fixture inputs. No manually injected captures/blocks.

assign src_clk = clk;
assign src_rst_n = rst_n;
assign src_region_base_sector = 30'd262144;
assign src_region_sector_count = 30'd2176;
assign src_prime_v = prime;
assign src_prime_user = '0;
assign src_prime_row = '0;
assign src_blk_v = core_win_blk_v && !guard_bad;
assign src_blk_user = '0;
assign src_blk_row = core_win_blk_row;
assign src_blk_idx = core_win_blk_idx;
assign src_blk_codes = core_win_blk_codes;
assign src_blk_scale = core_win_blk_scale;
assign src_prefetch_v = prefetch;
assign src_prefetch_user = '0;
assign src_prefetch_row = '0;
assign src_re = '0;
assign src_ruser = '0;
assign src_rrow = '0;
assign src_relem = '0;
assign src_packed_re = 0;
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
 .rec_commit(core_rec_commit_qualified),
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
 .rec_commit(core_rec_commit_qualified),
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
 .rec_commit(core_rec_commit_qualified),
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
 .rec_commit(core_rec_commit_qualified),
 .rec_owner_empty(back_empty),
 .rec_visible_empty(back_visible),
 .rec_token_ack(back_ack)
);
// Independent quiescence oracle: no identities travel on candidate wires.
always @(posedge clk) begin
 if(rst_n) begin
  cycles=cycles+1;
  if(cycles>250000 || (control=="discard_retirement_omitted" && cycles>4096)) $fatal(1,"bounded recovery case timeout; ownership retained");
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

// Only synthetic finite fixture inputs. No manually injected captures/blocks.
always_comb begin
 core_clk=clk;core_rst_n=rst_n;core_win_blk_ready=src_blk_ready && !guard_bad;
 core_rec_request=recover;core_rec_token=token;
 core_rec_fault_inject=fault_pulse || src_fault || (core_win_blk_v && guard_bad);
 core_rec_provider_ready=restart_ready;
 core_rec_rearm_request=commit;
 // External causal certificates default false, independently supplied controls below.
end
integer qe_accepts=0, su_accepts=0, terminals=0, vm_stores=0, captures=0, blocks=0;
integer prefix=0, fault_cycle=-1, stopped_pc=-1, suppress_samples=0;
integer init_word, vlane;
integer local_edge=-1, start_edge=-1;
reg [31:0] vm_shadow[0:511]; // existing synchronous fixture VM, full AW30 aperture
string cut;
logic checking=0, injected=0;
always @(posedge clk) if(rst_n) begin
 local_edge++;
 if(core_start) start_edge=local_edge;
 if(core_prog_re) begin
  case(core_prog_addr)
   20: core_prog_q<=2048'h0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000006be0000000000000000000000000000000000040000d5c0200000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000003;
   21: core_prog_q<=2048'h0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000c0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000004000000000035f0000000100000004000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000022;
   default: core_prog_q<=2048'h000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000f8;
  endcase
 end
 if(core_wqr_re) begin
  if(core_wqr_addr < 54720 || core_wqr_addr+31 >= 55232)
   $fatal(1,"real QE input full-address aperture");
  core_wqr_q <= {32{32'h3f800000}};
  if(cut=="POISON" && core_wqr_addr==54720+8*32) core_wqr_q[31:0]<=32'h7fc00000;
 end
 if(core.g_cancel.u_impl.qe_go_e && core.g_cancel.u_impl.qe_ready_e) begin
  if(local_edge-start_edge!=7) $fatal(1,"declared actual QE admission calendar mismatch");
  qe_accepts++;
 end
 if(core.g_cancel.u_impl.rec_su_go && core.g_cancel.u_impl.su_ready) begin
  if(local_edge-start_edge!=43) $fatal(1,"declared actual SU admission calendar mismatch");
  su_accepts++;
 end
 if(core.g_cancel.u_impl.rec_terminal) begin
  if(local_edge-start_edge!=24+terminals) $fatal(1,"declared actual QE terminal calendar mismatch");
  terminals++;
 end
 if(core.g_cancel.u_impl.rec_cap_v && core.g_cancel.u_impl.win_cap_ready) captures++;
 if(core_ww_q_we) begin
  if(!core.g_cancel.u_impl.rec_terminal || core_ww_q_mask != 32'hffffffff ||
     core_ww_q_addr != 55232+32*vm_stores ||
     (!core.g_cancel.u_impl.win_capture_fault && core_ww_q_data != {32{32'h3f800000}}))
   $fatal(1,"accepted QE suffix VM store lost or changed");
  for(vlane=0;vlane<32;vlane++) if(core_ww_q_mask[vlane])
   vm_shadow[core_ww_q_addr-55232+vlane] <= core_ww_q_data[32*vlane +: 32];
  vm_stores++;
 end
 if(core_win_blk_v && core_win_blk_ready) begin
  if(guard_bad) $fatal(1,"actual producer block identity");
  blocks++;
 end
 if(checking && (core.g_cancel.u_impl.qe_go_e || core.g_cancel.u_impl.rec_su_go ||
                 core.g_cancel.u_impl.rec_cap_v || core_win_blk_v))
  $fatal(1,"admission freeze violated");
 if(checking && core.g_cancel.u_impl.pc != stopped_pc)
  $fatal(1,"fault edge advanced PC");
 if(core.g_cancel.u_impl.win_scalar_suppress && !core.g_cancel.u_impl.su_idle) begin
  suppress_samples++;
  if(|core_xs_kv_we || |core_kv_we) $fatal(1,"accepted scalar suppression lost");
 end
 if(core_rec_commit_qualified && (!core_rec_visibility_certified ||
    !core_rec_delivery_certified || !core_rec_provenance_valid || !core_rec_local_ack ||
    !restart_ready || !core.g_cancel.u_impl.su_idle))
  $fatal(1,"local ACK mistaken for selected owner or causal retirement");
 if(cycles>4096 && cut!="WC" && cut!="WS" && cut!="SU_SUFFIX")
  $fatal(1,"actual source suffix bounded timeout");
end
task automatic tick(); @(posedge clk); #0.001; endtask
task automatic inject();
 recover=1;fault_pulse=1;stopped_pc=core.g_cancel.u_impl.pc;fault_cycle=cycles;
 tick();checking=1;injected=1;@(negedge clk);fault_pulse=0;
endtask
initial begin
 if(!$value$plusargs("CUT=%s",cut)) cut="PREFIX";
 if(!$value$plusargs("PREFIX=%d",prefix)) prefix=8;
 if(prefix<0 || prefix>16) $fatal(1,"unreviewed prefix");
 scenario="actual_core";control="none";
 repeat(3) tick();@(negedge clk);rst_n=1;
 for(init_word=262144;init_word<264320;init_word++) back.g_recovery.u_impl.mem[init_word]=0;
 tick();@(negedge clk);core_entry=20;core_pos=0;core_start=1;
 tick();@(negedge clk);core_start=0;
 if(cut=="ISSUE") begin
  wait(core.g_cancel.u_impl.st==6 && core.g_cancel.u_impl.d_unit==3);
  @(negedge clk);inject();
 end else if(cut=="GO") begin
  wait(core.g_cancel.u_impl.qe_go);@(negedge clk);inject();
 end else if(cut=="PREFIX") begin
  wait(qe_accepts==1);
  if(prefix>0) wait(terminals==prefix);
  @(negedge clk);inject();
 end else if(cut=="POISON") begin
  wait(core.g_cancel.u_impl.win_capture_fault);@(negedge clk);inject();
 end else if(cut=="SU_SUFFIX") begin
  wait(su_accepts==1);@(negedge clk);inject();
 end else if(cut=="WC" || cut=="WS") begin
  if(cut=="WC") wait(src.g_recovery.u_impl.state==2);
  else wait(src.g_recovery.u_impl.state==4);
  @(negedge clk);inject();
 end else $fatal(1,"unreviewed actual-core cut");
 wait(core_rec_local_ack);tick();
 if(core.g_cancel.u_impl.rec_active || !core.g_cancel.u_impl.rec_suffix_closed ||
    !core.g_cancel.u_impl.qe_idle_e || !core.g_cancel.u_impl.win_idle)
  $fatal(1,"local ACK before actual suffix and logical EMPTY");
 if(cut=="ISSUE" || cut=="GO") begin
  if(qe_accepts!=0 || terminals!=0 || vm_stores!=0) $fatal(1,"registered go cut accepted QE");
 end else begin
  if(qe_accepts!=1 || terminals!=16 || vm_stores!=16)
   $fatal(1,"accepted QE suffix not completely drained");
  if(cut=="POISON" && captures!=8) $fatal(1,"poison suffix capture freeze violated");
  if(cut=="PREFIX" && captures!=prefix) $fatal(1,"capture prefix count changed");
 end
 for(init_word=0;init_word<512;init_word++)
  if(qe_accepts==1 && !(cut=="POISON" && init_word>=256 && init_word<288) && vm_shadow[init_word]!=32'h3f800000)
   $fatal(1,"actual masked VM suffix memory image mismatch");
 if(core_rec_provenance_fault) $fatal(1,"intended fault cut falsely classed provenance violation");
 // Test local ACK cannot certify ownership or projected-vs-causal visibility.
 @(negedge clk);commit=1;
 repeat(4) begin tick();if(core_rec_commit_qualified) $fatal(1,"causal certificates absent but rearm admitted");end
 @(negedge clk);commit=0;
 wait(restart_ready && core.g_cancel.u_impl.su_idle);tick();
 if(expected_writes!=accepted_writes || accepted_reads!=returned_reads)
  $fatal(1,"accepted owner intent lost before restart");
 if(cut=="SU_SUFFIX" && (su_accepts!=1 || suppress_samples==0))
  $fatal(1,"actual accepted SU suppression witness absent");
 if(other_grants==0) $fatal(1,"competitor ownership witness absent");
 // Certificates are intentionally never asserted: actual causal provider absent.
 $display("ACTUAL_CORE_CANCEL_PASS cut=%s prefix=%0d qe=%0d terminal=%0d vm=%0d capture=%0d blocks=%0d acceptedWR=%0d faultcycle=%0d localACKcycle=%0d suppressed=%0d",cut,prefix,qe_accepts,terminals,vm_stores,captures,blocks,accepted_writes,fault_cycle,cycles,suppress_samples);
 $finish;
end
endmodule
