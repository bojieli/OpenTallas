`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Core tile of the ADOPTED DeepSeek-V4.1 layer die (rtl/chip/ot_chip_v41x_die.sv).
//
// The adopted decode core ot_hdc_core_v41x with every re-specified unit (X_HE,
// X_ME, X_ATT, X_SEL, X_EG, X_SU = 1), the pooled four-stack indexer (X_IDX = 2)
// and the QE weights streamed from HBM (W_HBM = 1) -- the configuration of the
// all-unit array gate (results/rtl/hdc_v41x_array_allunit_b2_*.json) and of the
// single-token HBM gate (results/rtl/hdc_v41x_whbm_pooled_single.json,
// rtl/test/tb_hdc_core_v41x_whbm.sv), whose memory wiring this tile reproduces
// port for port.
//
// Inside the tile:
//   ROM banks (mask-programmed; behavioural synchronous-read stand-ins whose
//   contents are the via mask, loaded by the bench):
//     prog   program ROM
//     wrom   BF16 weight ROM: the matrix engine port, SW embedding ports and
//            the vector unit's weight-element source (xs_rd_src = 3)
//     hrom   HE FP32 projection ROM
//     hbank  HCP weight banks (8 banks of HHW binary32 lanes)
//     mbank  ME weight-tile banks (8*MG banks, read latency ML = 2)
//     erom   Engram table ROM
//     crom   constant ROM (4*SW stream ports, the auxiliary port and the
//            vector unit's constant sources)
//     qlist  the QE weight streamer's fetch list
//   SRAM (buffers and staging only):
//     vm     vector memory: every core port, the QE streamer's expert-id read
//            and two FLIT-wide external word ports (A: the package controller,
//            B: the collective DMA)
//     qwin   the QE weight streamer's HBM window (SPW banks of 2^LWIN sectors)
//   Logic:
//     ot_hdc_qstream                    QE weights from HBM: its request /
//                                       response channel leaves the tile
//     ot_hdc_v41x_idx_pool_hbm_bridge   the pooled indexer's four-stack key
//                                       reads and timed key-image writes: its
//                                       128 pseudo-channel ports leave the tile
//
// NO KV SRAM.  The core runs with KV_HBM = 1: it announces each attention-class
// ME op's KV descriptor (kvd_v and kvd_wbase / ts / ks / js / tiles / k / nout /
// hg / mmode / pos) when it decodes it and holds that op's issue until kv_ok.
// The tile carries the descriptor, kv_ok and the core's fixed-latency KV port
// (kv_re / kv_raddr / kv_q, kv_we, xs_kv_we) to the die, which serves them
// (ot_chip_v41x_die.sv, u_kv).  The index engine's keys do not use this port:
// they come from HBM through u_kb.
//
// The die's KV service is the HBM prefetch ot_chip_v41x_kv_prefetch.sv.
//
// The X_IDX = 1 single-stack key port (ikh_*) is unused at X_IDX = 2 and is
// terminated inside the tile.
// ---------------------------------------------------------------------------
module ot_chip_v41x_tile #(
    parameter integer FULL_SHAPE = 0,
    parameter integer AW = FULL_SHAPE ? 30 : 24,
    parameter integer NW = FULL_SHAPE ? 21 : 16,
    parameter integer INSTR_BITS = FULL_SHAPE ? 2048 : 1536,
    // core configuration (adopted)
    parameter integer SW    = 8,             // stream-unit lanes
    parameter integer HS    = 8,             // HE K chunks
    parameter integer HHW   = 8,
    parameter integer HBAW  = 16,
    parameter integer MG    = 8,
    parameter integer MBAW  = FULL_SHAPE ? 18 : 17,
    parameter integer SUN   = 16,
    parameter integer SUM   = 8,
    parameter integer XSQ   = 4,
    parameter integer XSW   = 16,
    parameter integer X_HE  = 1,
    parameter integer X_ME  = 1,
    parameter integer X_ATT = 1,
    parameter integer X_IDX = 2,
    parameter integer PIKH_HAW = FULL_SHAPE ? 30 : 28, // pooled-index physical HBM sector address
    parameter integer IDX_SHARDED = 0,      // paired compact index-key layout
    parameter integer IDX_RING = 0,         // opt-in W11 quarter-per-stack ring key layout
    parameter integer IDX_RING_RSB = 1,
    parameter integer IDX_RING_RTAIL = 0,
    parameter integer IDX_MULTIUSER = 0,    // latch a physical key-slice base at start
    parameter integer IDX_KEY_SLICE_SECTORS = 0,
    parameter integer X_SEL = 1,
    parameter integer X_EG  = 1,
    parameter integer X_SU  = 1,
    parameter integer W_HBM = 1,
    parameter integer KV_HBM = 1,
    // QE weight streamer
    parameter integer NPC_W = 8,             // weight-region pseudo-channels
    parameter integer LWIN  = 10,
    parameter integer LAW   = 12,
    parameter integer QLIST_BITS = FULL_SHAPE ? 160 : 128,
    // memory depths (address bits); the defaults are the reduced vehicle's bench sizes
    parameter integer PROG_AW = 14,
    parameter integer WROM_AW = 19,
    parameter integer HROM_AW = 16,
    parameter integer EROM_AW = 19,
    parameter integer CROM_AW = 15,
    parameter integer VM_AW   = FULL_SHAPE ? 19 : 16,
    // X_ROM (W17): weight ops on the adopted ROM field; the field is outside the tile (rom_fb / rom_fr)
    parameter integer RANK    = 0,
    parameter integer CKV_SEL = 0,       // W11 CKV_SELECTED copy: passed to the core (rtl/hdc/v41x/ckvsel)
    parameter integer X_ROM   = 0,
    parameter integer ROM_R   = 128,
    parameter integer ROM_PHW = 6,
    parameter integer ROM_SAW = 16,
    parameter integer ROM_BST = 17,
    parameter integer ROM_FBW = 1 + ROM_PHW + 3 + 1 + 1 + 1 + 8 + 3 + 2 + 256 + 10 + 256 + 10 + 3 + 3 + 1 + 3 + 4 + 32 + 1024,
    parameter integer ROM_FRW = ROM_R * 69
) (
    input  wire              clk,
    input  wire              rst_n,
    // -- step control ---------------------------------------------------------------
    input  wire              start,
    input  wire [NW-1:0]     token,
    input  wire [NW-1:0]     pos,
    input  wire [13:0]       entry,
    // -- X_ROM: the ROM field (composed outside the tile) ------------------------------
    output wire [ROM_FBW-1:0] rom_fb,
    input  wire [ROM_FRW-1:0] rom_fr,
    input  wire              rom_ffault,
    output wire [1 + 16 + 1 + (FULL_SHAPE ? 512 : 32)*16 + 1 + 4 + 4*((FULL_SHAPE ? 512 : 32)/32)*265 + 1 + 1 + 32*16 + 1 - 1:0] att_to,
    input  wire [4 + 16 + 4 + 4*16*32 + 4*16 + 2 + 8 + 4*((FULL_SHAPE ? 512 : 32)/32)*16*32 + 4*((FULL_SHAPE ? 512 : 32)/32)*16 - 1:0] att_from,
    output wire              done,
    output wire [NW-1:0]     next_token,
    output wire [31:0]       next_val,
    output wire [31:0]       cycles,
    output wire              fault,
    output wire [3:0]        acc_n,
    input  wire              prime_v,
    input  wire              prime_first,
    input  wire [11:0]       prime_cid,
    // -- configuration ----------------------------------------------------------------
    input  wire [AW-1:0]     cfg_ik_base,
    input  wire [PIKH_HAW-1:0] idx_user_base_sec,
    input  wire [3:0]        cfg_me_xs,
    input  wire [AW-1:0]     cfg_q_base,      // HBM sector of the quantised weight region
    input  wire [LAW-1:0]    cfg_q_lbase,
    input  wire [NW-1:0]     cfg_q_lead,
    input  wire [15:0]       cfg_q_rate,
    // W_HBM=0 QE ROM service. The request is sampled on clk; the external
    // macro returns one compact word and its format on the following cycle.
    // This logical 16-lane port is an execution boundary, not the 274-bit
    // qtile physical-bank mapping.
    output wire              qr_compact_re,
    output wire [AW-1:0]     qr_compact_addr,
    input  wire              qr_compact_valid,
    input  wire              qr_compact_fp4,
    input  wire [4351:0]     qr_compact_fp8,
    input  wire [2303:0]     qr_compact_fp4_word,
    // -- KV port (served by the die) -------------------------------------------------------
    output wire              kv_re,
    output wire [4*AW-1:0]   kv_raddr,
    input  wire [4*16*32-1:0] kv_q,
    output wire [SW-1:0]     kv_we,
    output wire [SW*AW-1:0]  kv_waddr,
    output wire [SW*32-1:0]  kv_wdata,
    input  wire              att_packed_kv_v,
    output wire              att_packed_kv_ready,
    input  wire [3:0]        att_packed_kv_m,
    input  wire [4*((FULL_SHAPE ? 512 : 32)/32)*265-1:0] att_packed_kv_w,
    input  wire              att_packed_kv_fault,
    output wire              att_packed_issue,
    output wire              att_packed_idle,
    output wire [SUN-1:0]    xs_kv_we,
    output wire [SUN*AW-1:0] xs_kv_waddr,
    // Packed QDQ8 window-row block handoff. The 10-bit user is package
    // context supplied by the die; CKV selected rows never use this path.
    input  wire [9:0]        window_user,
    output wire              ckv_sel_v,
    output wire [AW-1:0]     ckv_sel_ibase,
    output wire              ckv_nw_we,
    output wire [AW-1:0]     ckv_nw_addr,
    output wire [1023:0]     ckv_nw_data,
    output wire              win_blk_v,
    input  wire              win_blk_ready,
    output wire [9:0]        win_blk_user,
    output wire [AW-1:0]     win_blk_kvt_base,
    output wire [NW-1:0]     win_blk_row,
    output wire [NW-1:0]     win_blk_kvt_row,
    output wire [3:0]        win_blk_idx,
    output wire [AW-1:0]     win_blk_first_elem,
    output wire [255:0]      win_blk_codes,
    output wire [7:0]        win_blk_scale,
    output wire [SUN*32-1:0] xs_kv_wdata,
    // -- attention KV descriptor / issue permission (the core's KV_HBM handshake) -----------
    output wire              kvd_v,
    output wire [AW-1:0]     kvd_wbase,
    output wire [AW-1:0]     kvd_ts,
    output wire [AW-1:0]     kvd_ks,
    output wire [AW-1:0]     kvd_js,
    output wire [NW-1:0]     kvd_tiles,
    output wire [NW-1:0]     kvd_k,
    output wire [NW-1:0]     kvd_nout,
    output wire [1:0]        kvd_hg,
    output wire              kvd_mmode,
    output wire [NW-1:0]     kvd_pos,
    input  wire              kv_ok,
    // Read-only RoPE coefficients fetched through the die's shared K HBM port.
    output wire              rope_pf_v,
    input  wire              rope_pf_rdy,
    output wire              rope_pf_kind,
    output wire [NW-1:0]     rope_pf_pos,
    input  wire              rope_pf_done,
    output wire              rope_pf_release,
    input  wire              rope_pf_fault,
    input  wire              rope_cache_valid,
    input  wire              rope_cache_hold,
    input  wire              rope_cache_kind,
    input  wire [NW-1:0]     rope_cache_pos,
    input  wire [2047:0]     rope_cache_pairs,
    // -- QE weight HBM channel (ot_hdc_hbm_model protocol) ----------------------------------
    output wire              wq_v,
    input  wire              wq_rdy,
    output wire [AW-1:0]     wq_addr,
    output wire [5:0]        wq_len,
    output wire [LWIN-1:0]   wq_tag,
    input  wire [NPC_W-1:0]  wq_room,
    input  wire [NPC_W-1:0]  wr_v,
    output wire [NPC_W-1:0]  wr_rdy,
    input  wire [NPC_W*LWIN-1:0] wr_tag,
    input  wire [NPC_W*5-1:0] wr_beat,
    input  wire [NPC_W*256-1:0] wr_data,
    // -- index-key HBM, four stacks x 32 pseudo-channels (ot_hdc_v41x_idx_hbm protocol) ---
    output wire [127:0]      kh_v,
    input  wire [127:0]      kh_rdy,
    output wire [128*PIKH_HAW-1:0] kh_addr,
    output wire [128*4-1:0]  kh_len,
    output wire [128*16-1:0] kh_tag,
    output wire [127:0]      kh_we,
    output wire [128*256-1:0] kh_wdata,
    output wire [128*32-1:0] kh_wstrb,
    input  wire [127:0]      kh_wr_done,
    input  wire [127:0]      kr_v,
    output wire [127:0]      kr_rdy,
    input  wire [128*16-1:0] kr_tag,
    input  wire [128*4-1:0]  kr_beat,
    input  wire [128*256-1:0] kr_data,
    // -- vector-memory external word ports (FLIT = 16 elements) ---------------------------
    input  wire              xa_we,
    input  wire [VM_AW-5:0]  xa_waddr,
    input  wire [511:0]      xa_wdata,
    input  wire              xa_re,
    input  wire [VM_AW-5:0]  xa_raddr,
    output reg  [511:0]      xa_rq,
    // Collective port B: four static word-address-low2 banks in full shape;
    // the reduced die uses lane 0 only. The core is blocked during COLL.
    input  wire [3:0]        xb_we4,
    input  wire [4*(VM_AW-4)-1:0] xb_waddr4,
    input  wire [4*512-1:0] xb_wdata4,
    input  wire              xb_re,
    input  wire [VM_AW-5:0]  xb_raddr,
    output reg  [511:0]      xb_rq,
    // Full-shape core collective command; the die owns DMA and link ordering.
    output wire              coll_go,
    output wire [1:0]        coll_op,
    output wire [(FULL_SHAPE ? 30 : 24)-1:0] coll_src, coll_dst, coll_ibase,
    output wire [(FULL_SHAPE ? 21 : 16)-1:0] coll_n,
    output wire [11:0]       coll_k,
    output wire [31:0]       coll_stride,
    output wire [7:0]        coll_seq,
    output wire              coll_rnd,
    input  wire              coll_busy, coll_fault,
    // -- status -------------------------------------------------------------------------
    output wire [4:0]        unit_busy,
    output wire [2:0]        issue_unit,
    output wire              qs_fault,
    output wire [3:0]        qs_why,
    output wire [31:0]       qs_fetched,
    output wire [31:0]       qs_consumed,
    output wire              kb_busy,
    output wire [31:0]       kb_records,
    output wire [31:0]       kb_writes,
    output wire [31:0]       kb_highwater,
    output wire [31:0]       kb_read_stalls,
    output wire [31:0]       kb_writer_stalls
);
    localparam integer W = 16, G = 4, BL = 16, QLB = 272, PAW = 14, HNL = 3;
    assign win_blk_user = FULL_SHAPE ? window_user : 10'd0;
    localparam integer ML = 2;                        // ME weight-tile bank read latency
    localparam integer SPW = BL * QLB / 256;          // QE window banks

    // -- memories ---------------------------------------------------------------------
    // ROM banks: their contents are the via mask (loaded by the bench / the mask), never written here
    /* verilator lint_off UNDRIVEN */
    reg [INSTR_BITS-1:0] prog  [0:(1<<PROG_AW)-1];
    reg [G*W*16-1:0]     wrom  [0:(1<<WROM_AW)-1];
    reg [HS*HNL*32-1:0]  hrom  [0:(1<<HROM_AW)-1];
    reg [HHW*32-1:0]     hbank [0:8*(1<<HBAW)-1];
    reg [31:0]           mbank [0:8*MG*(1<<MBAW)-1];
    reg [263:0]          erom  [0:(1<<EROM_AW)-1];
    reg [63:0]           crom  [0:(1<<CROM_AW)-1];
    reg [QLIST_BITS-1:0] qlist [0:(1<<LAW)-1];
    /* verilator lint_on UNDRIVEN */
    reg [255:0]          qwin  [0:SPW-1][0:(1<<LWIN)-1];
    reg [31:0]           vm    [0:(1<<VM_AW)-1];

    // -- core ports ---------------------------------------------------------------------
    wire prog_re; wire [PAW-1:0] prog_addr; reg [INSTR_BITS-1:0] prog_q;
    wire wrom_re; wire [AW-1:0] wrom_addr; reg [G*W*16-1:0] wrom_q;
    wire [SW-1:0] ewrom_re; wire [SW*AW-1:0] ewrom_addr; reg [SW*G*W*16-1:0] ewrom_q;
    wire qrom_re; wire [AW-1:0] qrom_addr; wire [BL*QLB-1:0] qrom_q;
    wire [BL*QLB-1:0] qrom_hbm_q, qrom_rom_q;
    reg qrom_rom_pending, qrom_rom_fault;
    assign qr_compact_re = (W_HBM == 0) && qrom_re;
    assign qr_compact_addr = qrom_addr;
    assign qrom_q = (W_HBM == 0) ? qrom_rom_q : qrom_hbm_q;
    ot_hdc_v41x_qrom_compact_word u_qrom_decode (
        .fp4(qr_compact_fp4), .fp8_word(qr_compact_fp8),
        .fp4_word(qr_compact_fp4_word), .qe_word(qrom_rom_q));
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin qrom_rom_pending <= 1'b0; qrom_rom_fault <= 1'b0; end
        else if (W_HBM == 0) begin
            qrom_rom_pending <= qrom_re;
            if (qrom_rom_pending && !qr_compact_valid) qrom_rom_fault <= 1'b1;
        end
    end
    wire qd_v, q_ok, wrel_v; wire [AW-1:0] qd_wbase; wire [7:0] qd_nb; wire [NW-1:0] qd_tiles;
    wire hrom_re; wire [AW-1:0] hrom_addr; reg [HS*HNL*32-1:0] hrom_q;
    wire [XSQ-1:0] vsl_re; wire [XSQ*AW-1:0] vsl_addr; reg [XSQ*XSW*32-1:0] vsl_q;
    wire [7:0] mb_re; wire [8*MBAW-1:0] mb_addr; reg [8*MG*32-1:0] mb_p [0:ML-1];
    wire [7:0] hb_re; wire [8*HBAW-1:0] hb_addr; reg [8*HHW*32-1:0] hb_q;
    wire [HS-1:0] vh_re; wire [HS*AW-1:0] vh_addr; reg [HS*32-1:0] vh_q;
    wire ww_h_we; wire [AW-1:0] ww_h_addr; wire [31:0] ww_h_mask; wire [1023:0] ww_h_data;
    wire erom_re; wire [AW-1:0] erom_addr; reg [263:0] erom_q;
    wire [4*SW-1:0] crom_re; wire [4*SW*AW-1:0] crom_addr; reg [4*SW*64-1:0] crom_q;
    wire xcrom_re; wire [AW-1:0] xcrom_addr; reg [63:0] xcrom_q;
    wire [G-1:0] vx_re; wire [G*AW-1:0] vx_addr; reg [G*32-1:0] vx_q;
    wire [4*SW-1:0] vs_re; wire [4*SW*AW-1:0] vs_addr; reg [4*SW*32-1:0] vs_q;
    wire [SW-1:0] vi_re; wire [SW*AW-1:0] vi_addr; reg [SW*32-1:0] vi_q;
    wire vq_re, vr_re, wqr_re, wxr_re;
    wire [AW-1:0] vq_addr, vr_addr, wqr_addr, wxr_addr;
    reg [31:0] vq_q, vr_q;
    reg [1023:0] wqr_q, wxr_q;
    wire [G-1:0] vw_me_we; wire [G*AW-1:0] vw_me_addr; wire [G*W-1:0] vw_me_mask; wire [G*W*32-1:0] vw_me_data;
    wire [SUN-1:0] xs_vi_re, xs_vm_we; wire [SUN*AW-1:0] xs_vi_addr, xs_vm_waddr;
    reg  [SUN*32-1:0] xs_vi_q; wire [4*SUN-1:0] xs_rd_re; wire [4*SUN*AW-1:0] xs_rd_addr; wire [8*SUN-1:0] xs_rd_src;
    reg  [4*SUN*32-1:0] xs_rd_q; wire [SUN*32-1:0] xs_vm_wdata;
    wire [SUN/8-1:0] xs_res_we; wire [SUN/8*AW-1:0] xs_res_addr; wire [SUN/8*32-1:0] xs_res_data;
    wire core_fault;
    reg rope_read_fault;
    wire rope_cache_match = rope_cache_valid && rope_cache_hold &&
                            rope_cache_kind == rope_pf_kind && rope_cache_pos == rope_pf_pos;
    wire [4*SUN-1:0] rope_bad_lane;
    wire [4*SUN-1:0] rope_tagged;
    wire [4*SUN*32-1:0] rope_words;
    genvar rp;
    generate for (rp = 0; rp < 4*SUN; rp = rp + 1) begin : g_rope_check
        wire lane_bad;
        ot_chip_v41x_rope_su_word #(.AW(AW), .PW(NW)) u_word (
            .src(xs_rd_src[rp*2 +: 2]), .addr(xs_rd_addr[rp*AW +: AW]),
            .cache_valid(rope_cache_valid), .cache_hold(rope_cache_hold),
            .cache_kind(rope_cache_kind), .cache_pos(rope_cache_pos),
            .cache_pairs(rope_cache_pairs), .is_rope(rope_tagged[rp]),
            .bad(lane_bad), .data(rope_words[rp*32 +: 32]));
        assign rope_bad_lane[rp] = FULL_SHAPE && xs_rd_re[rp] && lane_bad;
    end endgenerate
    wire [SW-1:0] vw_su_we, vw_rd_we; wire [SW*AW-1:0] vw_su_addr, vw_rd_addr; wire [SW*32-1:0] vw_su_data, vw_rd_data;
    wire vw_xe_we, ww_q_we, ww_x_we;
    wire [AW-1:0] vw_xe_addr, ww_q_addr, ww_x_addr;
    wire [31:0] vw_xe_data, ww_q_mask, ww_x_mask;
    wire [1023:0] ww_q_data, ww_x_data;
    wire me_ov; wire [G*AW-1:0] me_oaddr; wire [G*W-1:0] me_omask; wire [G*W*32-1:0] me_odata;
    wire [127:0] pikh_req_v, pikh_req_rdy;
    wire [128*PIKH_HAW-1:0] pikh_req_addr; wire [128*4-1:0] pikh_req_len; wire [128*16-1:0] pikh_req_tag;
    wire pikw_v, pikw_rdy; wire [3:0] pikw_stack_mask;
    wire [PIKH_HAW-1:0] pikw_csec, pikw_ssec; wire [511:0] pikw_codes; wire [2:0] pikw_sslot; wire [31:0] pikw_scales;
    reg idx_user_fault;
    wire [127:0] core_kr_v, core_kr_rdy;   // K responses to / readiness from the core's key reader
    wire kb_ring_fault;
    reg [PIKH_HAW-1:0] idx_user_base_q;
    wire [PIKH_HAW:0] idx_slice_end={1'b0,idx_user_base_sec}+
                                  (PIKH_HAW+1)'(IDX_KEY_SLICE_SECTORS);
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin idx_user_base_q<=0;idx_user_fault<=0;end
        else if(start) begin
            idx_user_base_q<=IDX_MULTIUSER ? idx_user_base_sec : '0;
            idx_user_fault<=IDX_MULTIUSER &&
                (idx_user_base_sec[6:0]!=0 || idx_slice_end[PIKH_HAW]);
        end
    end
    // One fault output: core, RoPE read, QE ROM and per-user index-slice faults
    // (main carried two drivers of fault and two core_fault declarations here).
    assign fault = core_fault | rope_read_fault | qrom_rom_fault | idx_user_fault | kb_ring_fault;

    // X_ROM vector-memory ports: the spine's x read (64 consecutive elements) and one row write per region root
    wire                rom_xre, rom_vre;
    wire [AW-1:0]       rom_xaddr, rom_vaddr;
    reg  [64*32-1:0]    rom_xq;
    reg  [31:0]         rom_vq;
    wire [ROM_R-1:0]    rom_we;
    wire [ROM_R*AW-1:0] rom_waddr;
    wire [ROM_R*32-1:0] rom_wdata;
    ot_hdc_core_v41x #(.FULL_SHAPE(FULL_SHAPE), .AW(AW), .NW(NW), .INSTR_BITS(INSTR_BITS),
                       .SW(SW), .HS(HS), .W_HBM(W_HBM), .KV_HBM(KV_HBM), .X_HE(X_HE), .X_ME(X_ME), .X_ATT(X_ATT), .X_IDX(X_IDX),
                       .X_SEL(X_SEL), .X_EG(X_EG), .XSQ(XSQ), .XSW(XSW), .X_SU(X_SU), .SUN(SUN), .SUM(SUM),
                       .HHW(HHW), .HBAW(HBAW), .MG(MG), .MBAW(MBAW),
                       .PIKH_HAW(PIKH_HAW), .IDX_SHARDED(IDX_SHARDED), .IDX_MULTIUSER(IDX_MULTIUSER),
                       .IDX_KEY_SLICE_SECTORS(IDX_KEY_SLICE_SECTORS), .IDX_RING(IDX_RING),
                       .IDX_RING_RSB(IDX_RING_RSB), .IDX_RING_RTAIL(IDX_RING_RTAIL),
                       .X_ROM(X_ROM), .ROM_R(ROM_R), .ROM_PHW(ROM_PHW), .ROM_SAW(ROM_SAW), .ROM_BST(ROM_BST), .RANK(RANK), .CKV_SEL(CKV_SEL)) u_core (
        .clk(clk), .rst_n(rst_n), .start(start), .token(token), .pos(pos), .entry(entry),
        .rom_xre(rom_xre), .rom_xaddr(rom_xaddr), .rom_xq(rom_xq), .rom_we(rom_we), .rom_waddr(rom_waddr),
        .rom_wdata(rom_wdata), .rom_vre(rom_vre), .rom_vaddr(rom_vaddr), .rom_vq(rom_vq), .rom_fb(rom_fb),
        .rom_fr(rom_fr), .rom_ffault(rom_ffault), .att_to(att_to), .att_from(att_from),
        .done(done), .acc_n(acc_n), .acc_tok(), .next_token(next_token), .next_val(next_val), .cycles(cycles),
        .fault(core_fault), .prime_v(prime_v), .prime_first(prime_first), .prime_cid(prime_cid),
        .rope_pf_v(rope_pf_v), .rope_pf_rdy(rope_pf_rdy),
        .rope_pf_kind(rope_pf_kind), .rope_pf_pos(rope_pf_pos),
        .rope_pf_done(rope_pf_done), .rope_pf_release(rope_pf_release),
        .rope_pf_fault(rope_pf_fault),
        .coll_go(coll_go), .coll_op(coll_op), .coll_src(coll_src), .coll_dst(coll_dst),
        .coll_ibase(coll_ibase), .coll_n(coll_n), .coll_k(coll_k), .coll_stride(coll_stride), .coll_seq(coll_seq),
        .coll_rnd(coll_rnd), .coll_busy(coll_busy), .coll_fault(coll_fault),
        .prog_re(prog_re), .prog_addr(prog_addr), .prog_q(prog_q),
        .wrom_re(wrom_re), .wrom_addr(wrom_addr), .wrom_q(wrom_q),
        .ewrom_re(ewrom_re), .ewrom_addr(ewrom_addr), .ewrom_q(ewrom_q),
        .hrom_re(hrom_re), .hrom_addr(hrom_addr), .hrom_q(hrom_q),
        .cfg_ik_base(cfg_ik_base), .idx_user_base_sec(idx_user_base_q), .cfg_me_xs(cfg_me_xs),
        .mb_re(mb_re), .mb_addr(mb_addr), .mb_q(mb_p[ML-1]),
        .xs_vi_re(xs_vi_re), .xs_vi_addr(xs_vi_addr), .xs_vi_q(xs_vi_q), .xs_rd_re(xs_rd_re),
        .xs_rd_addr(xs_rd_addr), .xs_rd_src(xs_rd_src), .xs_rd_q(xs_rd_q), .xs_vm_we(xs_vm_we),
        .xs_vm_waddr(xs_vm_waddr), .xs_vm_wdata(xs_vm_wdata), .xs_kv_we(xs_kv_we), .xs_kv_waddr(xs_kv_waddr),
        .xs_kv_wdata(xs_kv_wdata), .xs_res_we(xs_res_we), .xs_res_addr(xs_res_addr), .xs_res_data(xs_res_data),
        .hb_re(hb_re), .hb_addr(hb_addr), .hb_q(hb_q),
        // X_IDX = 1 single-stack key port: unused at X_IDX = 2
        .ikh_req_v(), .ikh_req_rdy(32'd0), .ikh_req_addr(), .ikh_req_len(), .ikh_req_tag(),
        .ikh_rsp_v(32'd0), .ikh_rsp_rdy(), .ikh_rsp_tag({32*16{1'b0}}), .ikh_rsp_beat({32*4{1'b0}}),
        .ikh_rsp_data({32*256{1'b0}}), .ikw_v(), .ikw_csec(), .ikw_codes(), .ikw_ssec(), .ikw_sslot(),
        .ikw_scale(),
        .pikh_req_v(pikh_req_v), .pikh_req_rdy(pikh_req_rdy), .pikh_req_addr(pikh_req_addr),
        .pikh_req_len(pikh_req_len), .pikh_req_tag(pikh_req_tag), .pikh_rsp_v(core_kr_v),
        .pikh_rsp_rdy(core_kr_rdy), .pikh_rsp_tag(kr_tag), .pikh_rsp_beat(kr_beat), .pikh_rsp_data(kr_data),
        .pikw_v(pikw_v), .pikw_rdy(pikw_rdy), .pikw_stack_mask(pikw_stack_mask), .pikw_csec(pikw_csec),
        .pikw_codes(pikw_codes), .pikw_ssec(pikw_ssec), .pikw_sslot(pikw_sslot), .pikw_scales(pikw_scales),
        .qrom_re(qrom_re), .qrom_addr(qrom_addr), .qrom_q(qrom_q),
        .erom_re(erom_re), .erom_addr(erom_addr), .erom_q(erom_q),
        .crom_re(crom_re), .crom_addr(crom_addr), .crom_q(crom_q),
        .xcrom_re(xcrom_re), .xcrom_addr(xcrom_addr), .xcrom_q(xcrom_q),
        .kv_re(kv_re), .kv_raddr(kv_raddr), .kv_q(kv_q), .kv_we(kv_we), .kv_waddr(kv_waddr), .kv_wdata(kv_wdata),
        .att_packed_kv_v(att_packed_kv_v), .att_packed_kv_ready(att_packed_kv_ready),
        .att_packed_kv_m(att_packed_kv_m), .att_packed_kv_w(att_packed_kv_w),
        .att_packed_kv_fault(att_packed_kv_fault),
        .att_packed_issue(att_packed_issue), .att_packed_idle(att_packed_idle),
        .ckv_sel_v(ckv_sel_v), .ckv_sel_ibase(ckv_sel_ibase),
        .ckv_nw_we(ckv_nw_we), .ckv_nw_addr(ckv_nw_addr), .ckv_nw_data(ckv_nw_data),
        .win_blk_v(win_blk_v), .win_blk_ready(win_blk_ready),
        .win_blk_kvt_base(win_blk_kvt_base), .win_blk_row(win_blk_row),
        .win_blk_kvt_row(win_blk_kvt_row),
        .win_blk_idx(win_blk_idx), .win_blk_first_elem(win_blk_first_elem),
        .win_blk_codes(win_blk_codes), .win_blk_scale(win_blk_scale),
        .vx_re(vx_re), .vx_addr(vx_addr), .vx_q(vx_q), .vs_re(vs_re), .vs_addr(vs_addr), .vs_q(vs_q),
        .vi_re(vi_re), .vi_addr(vi_addr), .vi_q(vi_q), .vq_re(vq_re), .vq_addr(vq_addr), .vq_q(vq_q),
        .vr_re(vr_re), .vr_addr(vr_addr), .vr_q(vr_q), .wqr_re(wqr_re), .wqr_addr(wqr_addr), .wqr_q(wqr_q),
        .vh_re(vh_re), .vh_addr(vh_addr), .vh_q(vh_q),
        .wxr_re(wxr_re), .wxr_addr(wxr_addr), .wxr_q(wxr_q),
        .vsl_re(vsl_re), .vsl_addr(vsl_addr), .vsl_q(vsl_q),
        .vw_me_we(vw_me_we), .vw_me_addr(vw_me_addr), .vw_me_mask(vw_me_mask), .vw_me_data(vw_me_data),
        .vw_su_we(vw_su_we), .vw_su_addr(vw_su_addr), .vw_su_data(vw_su_data),
        .vw_rd_we(vw_rd_we), .vw_rd_addr(vw_rd_addr), .vw_rd_data(vw_rd_data),
        .vw_xe_we(vw_xe_we), .vw_xe_addr(vw_xe_addr), .vw_xe_data(vw_xe_data),
        .ww_q_we(ww_q_we), .ww_q_addr(ww_q_addr), .ww_q_mask(ww_q_mask), .ww_q_data(ww_q_data),
        .ww_h_we(ww_h_we), .ww_h_addr(ww_h_addr), .ww_h_mask(ww_h_mask), .ww_h_data(ww_h_data),
        .ww_x_we(ww_x_we), .ww_x_addr(ww_x_addr), .ww_x_mask(ww_x_mask), .ww_x_data(ww_x_data),
        .me_ov(me_ov), .me_oaddr(me_oaddr), .me_omask(me_omask), .me_odata(me_odata),
        .unit_busy(unit_busy), .issue_unit(issue_unit),
        .qd_v(qd_v), .qd_wbase(qd_wbase), .qd_nb(qd_nb), .qd_tiles(qd_tiles),
        .q_ok(q_ok), .wrel_v(wrel_v),
        .kvd_v(kvd_v), .kvd_wbase(kvd_wbase), .kvd_ts(kvd_ts), .kvd_ks(kvd_ks), .kvd_js(kvd_js),
        .kvd_tiles(kvd_tiles), .kvd_k(kvd_k), .kvd_nout(kvd_nout), .kvd_pos(kvd_pos), .kvd_hg(kvd_hg),
        .kvd_mmode(kvd_mmode), .kv_ok(kv_ok));

    // -- QE weight streamer: the QE's weight port served from an HBM window ----------------
    wire l_re; wire [LAW-1:0] l_addr; reg [QLIST_BITS-1:0] l_q;
    wire xi_re; wire [AW-1:0] xi_addr; reg [31:0] xi_q;
    wire [SPW-1:0] qw_we; wire [SPW*LWIN-1:0] qw_waddr; wire [BL*QLB-1:0] qw_wdata;
    wire qw_re; wire [LWIN-1:0] qw_raddr; reg [BL*QLB-1:0] qw_q;
    generate if (W_HBM != 0) begin : g_qstream
    ot_hdc_qstream #(.FULL_SHAPE(FULL_SHAPE), .LIST_BITS(QLIST_BITS),
        .BL(BL), .QLB(QLB), .AW(AW), .HAW(AW), .NW(NW), .LWIN(LWIN),
                     .NPC(NPC_W), .LENW(6), .BEATW(5), .LAW(LAW)) u_qs (
        .clk(clk), .rst_n(rst_n), .cfg_base(cfg_q_base), .cfg_lbase(cfg_q_lbase),
        .cfg_lead(cfg_q_lead), .cfg_rate(cfg_q_rate), .tok_start(start), .pos(pos),
        .l_re(l_re), .l_addr(l_addr), .l_q(l_q), .vi_re(xi_re), .vi_addr(xi_addr),
        .vi_q(xi_q), .wrel_v(wrel_v), .qd_v(qd_v), .qd_nb(qd_nb),
        .qd_tiles(qd_tiles), .q_ok(q_ok), .qr_re(qrom_re), .qr_addr(qrom_addr),
        .qr_q(qrom_hbm_q), .win_we(qw_we), .win_waddr(qw_waddr), .win_wdata(qw_wdata),
        .win_re(qw_re), .win_raddr(qw_raddr), .win_q(qw_q),
        .hq_v(wq_v), .hq_rdy(wq_rdy), .hq_addr(wq_addr), .hq_len(wq_len),
        .hq_tag(wq_tag), .hq_room(wq_room), .hr_v(wr_v), .hr_rdy(wr_rdy),
        .hr_tag(wr_tag), .hr_beat(wr_beat), .hr_data(wr_data),
        .fault(qs_fault), .fault_why(qs_why), .st_fetched(qs_fetched),
        .st_consumed(qs_consumed));
    end else begin : g_qrom_only
        assign qrom_hbm_q = '0;
        assign q_ok = 1'b1;
        assign l_re = 1'b0; assign l_addr = '0;
        assign xi_re = 1'b0; assign xi_addr = '0;
        assign qw_we = '0; assign qw_waddr = '0; assign qw_wdata = '0;
        assign qw_re = 1'b0; assign qw_raddr = '0;
        assign wq_v = 1'b0; assign wq_addr = '0;
        assign wq_len = '0; assign wq_tag = '0;
        assign wr_rdy = '0;
        assign qs_fault = 1'b0; assign qs_why = '0;
        assign qs_fetched = '0; assign qs_consumed = '0;
    end endgenerate

    // -- pooled index-key HBM bridge: four stacks, timed key-image writes -------------------
    generate if (IDX_RING != 0) begin : g_kb_ring
    // W11 ring layout: key writer (decode steps + boundary migration) and the K-port arbiter
    ot_hdc_v41x_idx_ring_port #(.AW(PIKH_HAW), .RSB(IDX_RING_RSB), .RTAIL(IDX_RING_RTAIL), .READ_FENCE(1),
                                .WIDE_REC(1)) u_kb (
        .clk(clk), .rst_n(rst_n), .w_v(pikw_v), .w_rdy(pikw_rdy),
        .w_csec(pikw_csec), .w_codes(pikw_codes), .w_ssec(pikw_ssec), .w_sslot(pikw_sslot),
        .w_scales(pikw_scales), .r_v(pikh_req_v), .r_rdy(pikh_req_rdy), .r_addr(pikh_req_addr),
        .r_len(pikh_req_len), .r_tag(pikh_req_tag), .r_rsp_v(core_kr_v), .r_rsp_rdy(core_kr_rdy),
        .d_v(1'b0), .d_rdy(), .d_base('0), .d_n('0), .d_key('0),
        .h_v(kh_v), .h_rdy(kh_rdy), .h_addr(kh_addr),
        .h_len(kh_len), .h_tag(kh_tag), .h_we(kh_we), .h_wdata(kh_wdata), .h_wstrb(kh_wstrb),
        .h_wr_done(kh_wr_done), .h_rsp_v(kr_v), .h_rsp_rdy(kr_rdy), .h_rsp_tag(kr_tag),
        .h_rsp_data(kr_data), .busy(kb_busy), .fault(kb_ring_fault), .dbg_records(kb_records),
        .dbg_writes(kb_writes), .dbg_fifo_highwater(kb_highwater),
        .dbg_read_stalls(kb_read_stalls), .dbg_writer_stalls(kb_writer_stalls),
        .dbg_migrations(), .dbg_copied_sectors());
    end else begin : g_kb_bridge
    ot_hdc_v41x_idx_pool_hbm_bridge #(.AW(PIKH_HAW)) u_kb (
            .clk(clk), .rst_n(rst_n), .w_v(pikw_v), .w_rdy(pikw_rdy), .w_stack_mask(pikw_stack_mask),
            .w_csec(pikw_csec), .w_codes(pikw_codes), .w_ssec(pikw_ssec), .w_sslot(pikw_sslot),
            .w_scales(pikw_scales), .r_v(pikh_req_v), .r_rdy(pikh_req_rdy), .r_addr(pikh_req_addr),
            .r_len(pikh_req_len), .r_tag(pikh_req_tag), .h_v(kh_v), .h_rdy(kh_rdy), .h_addr(kh_addr),
            .h_len(kh_len), .h_tag(kh_tag), .h_we(kh_we), .h_wdata(kh_wdata), .h_wstrb(kh_wstrb),
            .h_wr_done(kh_wr_done), .busy(kb_busy), .dbg_records(kb_records),
            .dbg_writes(kb_writes), .dbg_fifo_highwater(kb_highwater),
            .dbg_read_stalls(kb_read_stalls), .dbg_writer_stalls(kb_writer_stalls));
    assign core_kr_v = kr_v; assign kr_rdy = core_kr_rdy; assign kb_ring_fault = 1'b0;
    end endgenerate

    // -- synchronous-read memories (the port behaviour of rtl/test/tb_hdc_core_v41x_whbm.sv) --
    integer l, q, e;
    reg [AW:0] xa;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) rope_read_fault <= 1'b0;
        else if (start) rope_read_fault <= 1'b0;
        else if ((FULL_SHAPE && rope_pf_release && !rope_cache_match) || |rope_bad_lane)
            rope_read_fault <= 1'b1;
    always @(posedge clk) begin
        if (prog_re) prog_q <= prog[prog_addr[PROG_AW-1:0]];
        if (wrom_re) wrom_q <= wrom[wrom_addr[WROM_AW-1:0]];
        for (q = 0; q < SW; q = q + 1)
            if (ewrom_re[q]) ewrom_q[q*G*W*16 +: G*W*16] <= wrom[ewrom_addr[q*AW +: WROM_AW]];
        if (hrom_re) hrom_q <= hrom[hrom_addr[HROM_AW-1:0]];
        // ME weight-tile banks: bank b = 8u + c answers chain position c's address ML cycles later
        for (q = 0; q < 8 * MG; q = q + 1)
            mb_p[0][32*q +: 32] <= mbank[32'(mb_addr[(q % 8)*MBAW +: MBAW]) * (8 * MG) + q];
        for (l = 1; l < ML; l = l + 1) mb_p[l] <= mb_p[l-1];
        for (q = 0; q < 8; q = q + 1) if (hb_re[q]) hb_q[q*HHW*32 +: HHW*32] <= hbank[{hb_addr[q*HBAW +: HBAW], 3'(q)}];
        for (q = 0; q < HS; q = q + 1) if (vh_re[q]) vh_q[32*q +: 32] <= vm[vh_addr[q*AW +: VM_AW]];
        if (ww_h_we) for (q = 0; q < 32; q = q + 1) if (ww_h_mask[q]) vm[ww_h_addr[VM_AW-1:0] + q] <= ww_h_data[32*q +: 32];
        if (erom_re) erom_q <= erom[erom_addr[EROM_AW-1:0]];
        for (q = 0; q < 4*SW; q = q + 1) if (crom_re[q]) crom_q[64*q +: 64] <= crom[crom_addr[q*AW +: CROM_AW]];
        if (xcrom_re) xcrom_q <= crom[xcrom_addr[CROM_AW-1:0]];
        for (q = 0; q < G; q = q + 1) if (vx_re[q]) vx_q[32*q +: 32] <= vm[vx_addr[q*AW +: VM_AW]];
        for (q = 0; q < 4*SW; q = q + 1) if (vs_re[q]) vs_q[32*q +: 32] <= vm[vs_addr[q*AW +: VM_AW]];
        for (q = 0; q < SW; q = q + 1) if (vi_re[q]) vi_q[32*q +: 32] <= vm[vi_addr[q*AW +: VM_AW]];
        if (vq_re) vq_q <= vm[vq_addr[VM_AW-1:0]];
        if (X_ROM != 0) begin
            if (rom_xre) for (q = 0; q < 64; q = q + 1) rom_xq[32*q +: 32] <= vm[rom_xaddr[VM_AW-1:0] + VM_AW'(q)];
            if (rom_vre) rom_vq <= vm[rom_vaddr[VM_AW-1:0]];
            for (q = 0; q < ROM_R; q = q + 1) if (rom_we[q]) vm[rom_waddr[q*AW +: VM_AW]] <= rom_wdata[32*q +: 32];
        end
        if (vr_re) vr_q <= vm[vr_addr[VM_AW-1:0]];
        if (wqr_re) for (q = 0; q < 32; q = q + 1) wqr_q[32*q +: 32] <= vm[wqr_addr[VM_AW-1:0] + q];
        if (wxr_re) for (q = 0; q < 32; q = q + 1) wxr_q[32*q +: 32] <= vm[wxr_addr[VM_AW-1:0] + q];
        for (q = 0; q < XSQ; q = q + 1)
            if (vsl_re[q]) for (l = 0; l < XSW; l = l + 1) vsl_q[32*(q*XSW + l) +: 32] <= vm[vsl_addr[q*AW +: VM_AW] + l];
        for (q = 0; q < G; q = q + 1)
            if (vw_me_we[q])
                for (l = 0; l < W; l = l + 1)
                    if (vw_me_mask[q*W + l]) vm[{vw_me_addr[q*AW +: VM_AW-4], 4'b0} + l] <= vw_me_data[32*(q*W + l) +: 32];
        for (q = 0; q < SW; q = q + 1) if (vw_su_we[q]) vm[vw_su_addr[q*AW +: VM_AW]] <= vw_su_data[32*q +: 32];
        for (q = 0; q < SW; q = q + 1) if (vw_rd_we[q]) vm[vw_rd_addr[q*AW +: VM_AW]] <= vw_rd_data[32*q +: 32];
        // the vector unit (X_SU): reads by source, element writes, reducer results
        for (q = 0; q < SUN; q = q + 1) if (xs_vi_re[q]) xs_vi_q[32*q +: 32] <= vm[xs_vi_addr[q*AW +: VM_AW]];
        for (q = 0; q < 4*SUN; q = q + 1) if (xs_rd_re[q]) begin
            xa = xs_rd_addr[q*AW +: AW];
            case (xs_rd_src[2*q +: 2])
                2'd0: xs_rd_q[32*q +: 32] <= vm[xa[VM_AW-1:0]];
                2'd1, 2'd2: begin
                    if (FULL_SHAPE && rope_tagged[q])
                        xs_rd_q[32*q +: 32] <= rope_words[32*q +: 32];
                    else if (xs_rd_src[2*q +: 2] == 2'd1)
                        xs_rd_q[32*q +: 32] <= crom[xa[CROM_AW-1:0]][31:0];
                    else
                        xs_rd_q[32*q +: 32] <= crom[xa[CROM_AW-1:0]][63:32];
                end
                default: xs_rd_q[32*q +: 32] <= {wrom[xa[6 +: WROM_AW]][16*xa[5:0] +: 16], 16'h0000};
            endcase
        end
        for (q = 0; q < SUN; q = q + 1) if (xs_vm_we[q]) vm[xs_vm_waddr[q*AW +: VM_AW]] <= xs_vm_wdata[32*q +: 32];
        for (q = 0; q < SUN/8; q = q + 1) if (xs_res_we[q]) vm[xs_res_addr[q*AW +: VM_AW]] <= xs_res_data[32*q +: 32];
        if (vw_xe_we) vm[vw_xe_addr[VM_AW-1:0]] <= vw_xe_data;
        if (ww_q_we) for (q = 0; q < 32; q = q + 1) if (ww_q_mask[q]) vm[ww_q_addr[VM_AW-1:0] + q] <= ww_q_data[32*q +: 32];
        if (ww_x_we) for (q = 0; q < 32; q = q + 1) if (ww_x_mask[q]) vm[ww_x_addr[VM_AW-1:0] + q] <= ww_x_data[32*q +: 32];
        // QE streamer: fetch list, expert-id read, HBM window
        if (l_re) l_q <= qlist[l_addr];
        if (xi_re) xi_q <= vm[xi_addr[VM_AW-1:0]];
        for (q = 0; q < SPW; q = q + 1) begin
            if (qw_re) qw_q[q*256 +: 256] <= qwin[q][qw_raddr];
            if (qw_we[q]) qwin[q][qw_waddr[q*LWIN +: LWIN]] <= qw_wdata[q*256 +: 256];
        end
        // external word ports (package controller, collective DMA)
        for (e = 0; e < 16; e = e + 1) begin
            if (xa_we) vm[{xa_waddr, 4'(e)}] <= xa_wdata[32*e +: 32];
            for (integer b = 0; b < 4; b = b + 1)
                if (xb_we4[b])
                    vm[{xb_waddr4[b*(VM_AW-4) +: (VM_AW-4)], 4'(e)}] <=
                        xb_wdata4[b*512 + 32*e +: 32];
            if (xa_re) xa_rq[32*e +: 32] <= vm[{xa_raddr, 4'(e)}];
            if (xb_re) xb_rq[32*e +: 32] <= vm[{xb_raddr, 4'(e)}];
        end
    end
endmodule
