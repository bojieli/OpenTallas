`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// L20 COPY (W11 CKV, one die model for the indexed layer): ot_v41_rt_die with the die's CKV_SELECTED path
// (rtl/chip/ckvsel/ot_chip_v41x_die.sv + core/tile copies) and its all-gather ports ckv_ag_*; the host
// (v41_die_rt.cpp) carries ckv_ag_tx of die s to ckv_ag_rx of the other three dies (UCIe 11 / board 142 cycles,
// 2 cycles a row on a board link).  W11's ring worker adds its X_IDX / IDX_RING parameters to THIS file.
// SIMULATION ONLY (W17 runtime composition of the adopted V4.1 layer die, tools/v41_die_rt.py):
// one layer die of a TP-4 group -- ot_chip_v41x_die FULL_SHAPE = 1 with X_ROM = 1 (every weight op on the ROM
// field through the spine) and the attention engine cut (V41_ATT_CUT) -- whose ROM field (ot_v41_pair,
// ot_v41_retn, ot_v41_ret_root) and attention engine (ot_hdc_v41x_attn) are separately compiled models
// composed by the host (rtl/test/v41_runtime/v41_die_rt.cpp), and whose collective links to the other three
// dies are the host's deterministic-release delay lines (W15: records are released at a fixed latency).
//
// Images (+DIR=<dir>, every file optional; a file that is absent leaves the memory zero):
//   prog.hex crom.hex hbank.hex hrom.hex erom.hex   the tile's ROMs (as tb_chip_v41x_die_smoke)
//   vm_init.hex                                     the tile's vector memory at step start
//   hbm<s>.hex (s = 0..3)                           stack s's K-port sectors (256 bits a line), from sector 0
//   hbmsparse<s>.hex                                "<sector hex> <256-bit hex>" lines (sparse regions: the
//                                                   RoPE table rows of the step's position)
// The ROM-field images are the host's (per-element words and configuration served through DPI).
// ---------------------------------------------------------------------------
module ot_v41_rt_die_l20_c8 #(
    parameter integer WFC_COMPLETION_JOIN=0,
    parameter integer NATIVE_RESULT_READ=0,
    parameter integer PKG_WAVE=0,
    parameter integer PKG_WAVE_WIN=6,
    parameter integer PKG_ID=0,
    parameter integer MAXU=866,
    parameter integer SOURCE=0,
    parameter integer RESULT_PARTS=1,
    parameter integer SEND_HIDDEN=0,
    parameter integer HID_DEST=0,
    parameter integer SEND_RESULT=0,
    parameter integer RES_DEST=0,
    parameter integer COMBINE_IN=0,
    parameter integer ROW0=0,
    parameter integer FWD_TOKEN=1,
    parameter integer COLL_ACCEPTED_POP=0,
    parameter integer S81_CAPTURE=0,
    parameter integer IDX_DRAIN_LOOKAHEAD=0,
    parameter integer S81_COMMAND_TRACE=0,
    parameter integer S81_TRACE_STAGE=-1,
    parameter integer S81_HOST_WORKSPACE=0,
    parameter integer C8_PUBLICATION=0,
    parameter integer C8_CONTEXT=0,
    parameter integer WINDOW_REFILL_CREDITS = 1,
    parameter bit WINDOW_REFILL_OWNER_SAFE = 0,
    parameter integer CKV_SELECTED = 1,
    parameter integer CKV_BASE = 1 << 22,
    parameter integer CKV_NSLOT = 64,
    parameter integer RANK = 0,
    // W11 adopted indexer (opt-in; W17 passes -GX_IDX=2 -GIDX_RING=1 for the ring key layout at full capacity:
    // C = 64 x 1,024 + 32 = 65,568 key slots a stack, a region UBLK = 1,090 blocks; keys placed by
    // tools/w11_idx_ring_place.py into ikring_s<s>.hex, loaded below)
    parameter integer X_IDX = 0,
    parameter integer X_SEL = 0,
    parameter integer IDX_RING = 0,
    parameter integer IDX_RING_RSB = 64,
    parameter integer IDX_RING_RTAIL = 32,
    parameter integer K_MEM = 1 << 24,
    parameter integer ROM_R = 128,
    parameter integer ROM_PHW = 6,
    parameter integer ROM_SAW = 16,
    parameter integer ROM_BST = 17,
    parameter integer SUN = 256,            // >= 256 at full shape: the SU's span depth L = log2(ceil(n/SUN)) <= LV (7) for
                                            // the hc_post sum of squares over 20,480 (tools/v41_su_legality.py)
    parameter integer SUM = 64,
    parameter integer CL_LANES = 16,
    parameter integer CL_DEPTH = 256,
    parameter integer CL_RELAY = 0,
    parameter integer ROM_FBW = 1 + ROM_PHW + 3 + 1 + 1 + 1 + 8 + 3 + 2 + 256 + 10 + 256 + 10 + 3 + 3 + 1 + 3 + 4 + 32 + 1024,
    parameter integer ROM_FRW = ROM_R * 69,
    parameter integer ATW = 1 + 16 + 1 + 512*16 + 1 + 4 + 4*16*265 + 1 + 1 + 32*16 + 1,
    parameter integer AFW = 4 + 16 + 4 + 4*16*32 + 4*16 + 2 + 8 + 4*16*16*32 + 4*16*16,
    parameter integer CL_PW = 32 * CL_LANES + 3 + 32
) (
    output wire native_result_selected,native_result_active,
    output wire native_result_producer_take,native_result_am_any,
    output wire native_result_end_take,native_result_done,
    output wire [46:0] native_result_identity,
    output wire [13:0] native_result_entry,native_result_pc,
    output wire [20:0] native_result_token,
    output wire [31:0] native_result_value,
    // OLD registered RESULT processed at the upcoming edge, not current core user.
    output wire wf_result_v,
    output wire [9:0] wf_result_user,
    output wire [20:0] wf_result_pos,
    output wire wf_result_final,

    // Actual whole-stage caller result; hold done/data until wf_stage_accepted is sampled high.
    // A fragment c8_retire_v is NOT whole-stage completion.
    // REQUIRED Arch-owned complete-plan and real visibility authority pins.
    // Unbound valid pins fail closed; never tie coverage/visibility to one.
    input wire wf_join_request_v, wf_join_request_binding_valid,
    output wire wf_join_request_ready,
    input wire [46:0] wf_join_request_identity,
    input wire [13:0] wf_join_terminal_entry, wf_join_producer_pc, wf_join_end_pc,
    input wire wf_join_coverage_valid, wf_join_wholeplan_complete,
    input wire [46:0] wf_join_coverage_identity,
    input wire wf_join_visibility_valid, wf_join_visibility_fault,
    input wire [46:0] wf_join_visibility_identity,
    input wire [4:0] wf_join_visibility,
    output wire wf_join_pending, wf_join_fault,
    input wire wf_stage_done,
    output wire wf_stage_accepted,
    input wire [20:0] wf_stage_next_token,
    input wire [31:0] wf_stage_next_val,
    output wire wf_request,
    output wire [20:0] wf_token,wf_pos,
    output wire [9:0] wf_user,
    output wire wf_busy,
    output wire [3:0] wf_pr_blk,
    input wire wf_pr_qk,
    output wire wf_issue,wf_reject,wf_squash,
    input  wire [((MAXU > 255) ? $clog2(MAXU+1) : 8)-1:0] wf_cfg_users,
    input  wire [21-1:0] wf_cfg_prompt_len,
    input  wire [21-1:0] wf_cfg_gen_len,
    output wire              wf_pr_re,
    output wire [10-1:0] wf_pr_user,
    output wire [21-1:0] wf_pr_pos,
    input  wire [21-1:0] wf_pr_q,
    output wire              wf_tok_valid,
    output wire [10-1:0] wf_tok_user,
    output wire [21-1:0] wf_tok_pos,
    output wire [21-1:0] wf_tok_id,
    output wire [((MAXU > 255) ? $clog2(MAXU+1) : 8)-1:0] wf_users_done,
    input  wire              wf_rcfg_we,
    input  wire [7:0]        wf_rcfg_dest,
    input  wire [2:0]        wf_rcfg_mask,
    output wire              wf_ucie_tx_valid,
    input  wire              wf_ucie_tx_ready,
    output wire [511:0]      wf_ucie_tx_data,
    output wire              wf_ucie_tx_last,
    input  wire              wf_ucie_rx_valid,
    output wire              wf_ucie_rx_ready,
    input  wire [511:0]      wf_ucie_rx_data,
    input  wire              wf_ucie_rx_last,
    output wire              wf_bl_tx_valid,
    input  wire              wf_bl_tx_ready,
    output wire [511:0]      wf_bl_tx_data,
    output wire              wf_bl_tx_last,
    input  wire              wf_bl_rx_valid,
    output wire              wf_bl_rx_ready,
    input  wire [511:0]      wf_bl_rx_data,
    input  wire              wf_bl_rx_last,
    input wire [ROM_R*19-1:0] capture_root_rows,
    output wire [46:0] capture_identity,
    input wire capture_reset_request,
    output wire capture_live,capture_drained,capture_fault,
    output wire [ROM_R-1:0] capture_vm_accept,
    input  wire              clk,
    input  wire              rst_n,
    input  wire              start,
    input  wire [20:0]       token,
    input  wire [20:0]       pos,
    input  wire [9:0]        user,
    // configuration (the manifest's values; held for the step)
    input  wire [29:0]       cfg_ik_base,
    input  wire              window_region_valid,
    input  wire [29:0]       window_region_base,
    input  wire [29:0]       window_region_count,
    input  wire              window_prime_v,
    output wire              window_prime_ready,
    input  wire [9:0]        window_prime_user,
    input  wire [20:0]       window_prime_row,
    input  wire [1:0]        rope_table_present,
    input  wire [4*30-1:0]   rope_reserved_end,
    input  wire [4*30-1:0]   rope_plain_base,
    input  wire [4*30-1:0]   rope_yarn_base,
    output wire              done,
    output wire [31:0]       cycles,
    output wire [7:0]        fault,
    output wire [4:0]        unit_busy,
    output wire [2:0]        issue_unit,
    output wire [13:0]       dbg_pc,           // the core's program counter (observability only)
    output wire [63:0]       dbg_state,        // {core st, d_unit, idles, coll_busy, waited, cdma busy/mode, e/o valid-ready}
    output wire [31:0]       dbg_words,        // {cdma words_out[15:0], words_in[15:0]}
    output reg  [23:0]       dbg_fs,           // sticky fault sources, one bit each (index map below)
    // ROM field
    output wire [ROM_FBW-1:0] rom_fb,
    input  wire [ROM_FRW-1:0] rom_fr,
    input  wire              rom_ffault,
    // attention engine
    output wire [ATW-1:0]    att_to,
    input  wire [AFW-1:0]    att_from,
    // collective records (TP-4): UCIe to the package peer, T1 board links to the partner package's two dies
    output wire              ucie_ctx_valid,
    input  wire              ucie_ctx_ready,
    output wire [CL_PW-1:0]  ucie_ctx_rec,
    input  wire [1:0]        ucie_ccr_in,
    input  wire              ucie_crx_valid,
    input  wire [CL_PW-1:0]  ucie_crx_rec,
    output wire [1:0]        ucie_ccr_out,
    output wire [1:0]        bl_ctx_valid,
    input  wire [1:0]        bl_ctx_ready,
    output wire [CL_PW-1:0]  bl_ctx_rec,
    input  wire [3:0]        bl_ccr_in,
    input  wire [1:0]        bl_crx_valid,
    input  wire [2*CL_PW-1:0] bl_crx_rec,
    output wire [3:0]        bl_ccr_out,
    // CKV all-gather (CKV_SELECTED)
    output wire              ckv_ag_tx_valid,
    input  wire              ckv_ag_tx_ready,
    output wire [9:0]        ckv_ag_tx_rank,
    output wire [20:0]       ckv_ag_tx_gid,
    output wire [2303:0]     ckv_ag_tx_row,
    input  wire [2:0]        ckv_ag_rx_valid,
    input  wire [29:0]       ckv_ag_rx_rank,
    input  wire [62:0]       ckv_ag_rx_gid,
    input  wire [3*2304-1:0] ckv_ag_rx_row,
    output wire [31:0]       ckv_cycles_to_ready,
    output wire [5:0]        ckv_fault_code,
    input wire [13:0] c8_entry,
    input wire c8_context_restored,
    output wire c8_offer_ready,c8_context_v,c8_retire_v,c8_stage_active,c8_stage_quarantine,
    output wire [46:0] c8_context_identity,c8_retire_identity,
    output wire [20:0] c8_context_token,
    output wire [13:0] c8_context_entry,
    input wire [46:0] c8_position_identity,
    output wire c8_write_quiet,c8_write_quarantine,c8_write_fault,
    output wire [127:0] c8_visible_v,
    output wire [128*47-1:0] c8_visible_identity,
    output wire [128*30-1:0] c8_visible_addr,
    output wire [255:0] c8_visible_writer,
    output wire c8_own_pending,c8_own_visible_v,
    output wire [46:0] c8_own_visible_identity,
    output wire [20:0] c8_own_visible_gid
);
    ot_chip_v41x_die_owner_safe_c8 #(.PKG_WAVE(PKG_WAVE), .PKG_WAVE_WIN(PKG_WAVE_WIN), .PKG_ID(PKG_ID), .MAXU(MAXU), .SOURCE(SOURCE), .RESULT_PARTS(RESULT_PARTS), .SEND_HIDDEN(SEND_HIDDEN), .HID_DEST(HID_DEST), .SEND_RESULT(SEND_RESULT), .RES_DEST(RES_DEST), .COMBINE_IN(COMBINE_IN), .ROW0(ROW0), .FWD_TOKEN(FWD_TOKEN), .S81_CAPTURE(S81_CAPTURE),.IDX_DRAIN_LOOKAHEAD(IDX_DRAIN_LOOKAHEAD),.COLL_ACCEPTED_POP(COLL_ACCEPTED_POP),.C8_PUBLICATION(C8_PUBLICATION),.WINDOW_REFILL_CREDITS(WINDOW_REFILL_CREDITS), .WINDOW_REFILL_OWNER_SAFE(WINDOW_REFILL_OWNER_SAFE),.FULL_SHAPE(1), .RANK(RANK), .X_ROM(1), .ROM_R(ROM_R), .ROM_PHW(ROM_PHW), .ROM_SAW(ROM_SAW),
                       .ROM_BST(ROM_BST), .X_ATT(1), .X_ME(0), .X_IDX(X_IDX), .X_SEL(X_SEL), .IDX_RING(IDX_RING), .IDX_RING_RSB(IDX_RING_RSB),
                       .IDX_RING_RTAIL(IDX_RING_RTAIL), .X_EG(0), .W_HBM(0),
                       .WINDOW_HBM_ATTENTION(1), .CKV_SELECTED(CKV_SELECTED != 0), .CKV_BASE(CKV_BASE),
                       .CKV_NSLOT(CKV_NSLOT), .K_MEM(K_MEM), .SUN(SUN), .SUM(SUM),
                       .CL_LANES(CL_LANES), .CL_DEPTH(CL_DEPTH), .CL_RELAY(CL_RELAY)) dut (
        .capture_root_rows(capture_root_rows),.capture_identity(capture_identity),
        .capture_reset_request(capture_reset_request),.capture_vm_accept(capture_vm_accept),
        .capture_live(capture_live),.capture_drained(capture_drained),.capture_fault(capture_fault),
        .clk(clk), .rst_n(rst_n), .rom_fb(rom_fb), .rom_fr(rom_fr), .rom_ffault(rom_ffault),
        .att_to(att_to), .att_from(att_from),
        .c8_position_identity(C8_CONTEXT ? c8_engine_identity : c8_position_identity),.c8_write_quiet(c8_write_quiet),.c8_write_quarantine(c8_write_quarantine),.c8_write_fault(c8_write_fault),
        .c8_visible_v(c8_visible_v),.c8_visible_identity(c8_visible_identity),.c8_visible_addr(c8_visible_addr),.c8_visible_writer(c8_visible_writer),
        .c8_own_pending(c8_own_pending),.c8_own_visible_v(c8_own_visible_v),.c8_own_visible_identity(c8_own_visible_identity),.c8_own_visible_gid(c8_own_visible_gid),
        .host_mode(1'b1),
        .wf_stage_done(WFC_COMPLETION_JOIN ? joined_stage_done : wf_stage_done),
        .wf_result_v(wf_result_v), .wf_result_user(wf_result_user),
        .wf_result_pos(wf_result_pos), .wf_result_final(wf_result_final),
        .wf_stage_accepted(wf_stage_accepted),
        .wf_stage_next_token(WFC_COMPLETION_JOIN ? joined_stage_token : wf_stage_next_token),
        .wf_stage_next_val(WFC_COMPLETION_JOIN ? joined_stage_value : wf_stage_next_val),
        .wf_request(wf_request),
        .wf_token(wf_token),
        .wf_pos(wf_pos),
        .wf_user(wf_user),
        .wf_busy(wf_busy),
        .wf_pr_blk(wf_pr_blk),
        .wf_pr_qk(wf_pr_qk),
        .wf_issue(wf_issue),
        .wf_reject(wf_reject),
        .wf_squash(wf_squash),
 .host_start(C8_CONTEXT ? c8_engine_start : start), .host_token(C8_CONTEXT ? c8_engine_token : token), .host_pos(C8_CONTEXT ? c8_engine_pos : pos), .host_user(C8_CONTEXT ? c8_engine_user : user),
        .host_entry(C8_PUBLICATION ? (C8_CONTEXT ? c8_engine_entry : c8_entry) : 14'd0), .host_prime_v(1'b0), .host_prime_first(1'b0), .host_prime_cid(12'd0),
        .window_region_valid(window_region_valid), .window_region_base(window_region_base),
        .window_region_count(window_region_count), .window_prime_v(window_prime_v),
        .window_prime_ready(window_prime_ready), .window_prime_user(window_prime_user),
        .window_prime_row(window_prime_row),
        .core_done(done), .core_next_token(native_result_token), .core_next_val(native_result_value), .core_cycles(cycles), .core_acc_n(),
        .att_packed_desc_v(), .att_packed_desc_accept(), .att_packed_desc_gen(), .att_packed_desc_rows(),
        .att_packed_desc_user(), .att_packed_desc_pos(), .att_packed_desc_tiles(), .att_packed_desc_nout(),
        .att_packed_desc_k(), .att_packed_desc_hg(), .att_packed_desc_mmode(), .att_packed_desc_wbase(),
        .att_packed_desc_ts(), .att_packed_desc_ks(), .att_packed_desc_js(),
        .att_packed_stage_v(1'b0), .att_packed_stage_gen(16'd0), .att_packed_stage_rows(11'd0),
        .att_packed_wrap_drained(1'b0), .att_packed_kv_v(1'b0), .att_packed_kv_ready(), .att_packed_kv_gen(16'd0),
        .att_packed_kv_m(4'd0), .att_packed_kv_w('0), .att_packed_kv_fault(1'b0),
        .att_packed_desc_done(), .att_packed_desc_fault(), .att_packed_desc_fault_code(),
        .cfg_ik_base(cfg_ik_base), .cfg_me_xs(4'd0), .cfg_q_base(30'd0), .cfg_q_lbase('0), .cfg_q_lead(21'd0),
        .cfg_q_rate(16'd0),
        .qr_compact_re(), .qr_compact_addr(), .qr_compact_valid(1'b0), .qr_compact_fp4(1'b0),
        .qr_compact_fp8('0), .qr_compact_fp4_word('0),
        .rope_table_present(rope_table_present), .rope_reserved_end(rope_reserved_end),
        .rope_plain_base(rope_plain_base), .rope_yarn_base(rope_yarn_base),
        .cfg_users(PKG_WAVE ? wf_cfg_users : 'd1), .cfg_prompt_len(PKG_WAVE ? wf_cfg_prompt_len : 21'd0), .cfg_gen_len(PKG_WAVE ? wf_cfg_gen_len : 21'd0),
        .pr_re(wf_pr_re), .pr_user(wf_pr_user), .pr_pos(wf_pr_pos), .pr_q(PKG_WAVE ? wf_pr_q : 21'd0),
        .tok_valid(wf_tok_valid), .tok_user(wf_tok_user), .tok_pos(wf_tok_pos), .tok_id(wf_tok_id), .users_done(wf_users_done),
        .rcfg_we(PKG_WAVE ? wf_rcfg_we : 1'b0), .rcfg_dest(PKG_WAVE ? wf_rcfg_dest : 8'd0), .rcfg_mask(PKG_WAVE ? wf_rcfg_mask : 3'd0),
        .coll_go(1'b0), .coll_mode(1'b0), .coll_tag('0), .coll_src('0), .coll_n('0), .coll_dst('0), .coll_busy(),
        .ucie_tx_valid(wf_ucie_tx_valid), .ucie_tx_ready(PKG_WAVE ? wf_ucie_tx_ready : 1'b1), .ucie_tx_data(wf_ucie_tx_data), .ucie_tx_last(wf_ucie_tx_last),
        .ucie_rx_valid(PKG_WAVE ? wf_ucie_rx_valid : 1'b0), .ucie_rx_ready(wf_ucie_rx_ready), .ucie_rx_data(PKG_WAVE ? wf_ucie_rx_data : 512'd0), .ucie_rx_last(PKG_WAVE ? wf_ucie_rx_last : 1'b0),
        .ucie_ctx_valid(ucie_ctx_valid), .ucie_ctx_ready(ucie_ctx_ready), .ucie_ctx_rec(ucie_ctx_rec),
        .ucie_ccr_in(ucie_ccr_in), .ucie_crx_valid(ucie_crx_valid), .ucie_crx_rec(ucie_crx_rec),
        .ucie_ccr_out(ucie_ccr_out),
        .ucie_rl_tx_valid(), .ucie_rl_tx_rec(), .ucie_rl_rx_valid(4'd0), .ucie_rl_rx_rec('0),
        .bl_tx_valid(wf_bl_tx_valid), .bl_tx_ready(PKG_WAVE ? wf_bl_tx_ready : 1'b1), .bl_tx_data(wf_bl_tx_data), .bl_tx_last(wf_bl_tx_last),
        .bl_rx_valid(PKG_WAVE ? wf_bl_rx_valid : 1'b0), .bl_rx_ready(wf_bl_rx_ready), .bl_rx_data(PKG_WAVE ? wf_bl_rx_data : 512'd0), .bl_rx_last(PKG_WAVE ? wf_bl_rx_last : 1'b0),
        .bl_ctx_valid(bl_ctx_valid), .bl_ctx_ready(bl_ctx_ready), .bl_ctx_rec(bl_ctx_rec), .bl_ccr_in(bl_ccr_in),
        .bl_crx_valid(bl_crx_valid), .bl_crx_rec(bl_crx_rec), .bl_ccr_out(bl_ccr_out),
        .fault(fault), .unit_busy(unit_busy), .issue_unit(issue_unit),
        .ckv_ag_tx_valid(ckv_ag_tx_valid), .ckv_ag_tx_ready(ckv_ag_tx_ready), .ckv_ag_tx_rank(ckv_ag_tx_rank),
        .ckv_ag_tx_gid(ckv_ag_tx_gid), .ckv_ag_tx_row(ckv_ag_tx_row), .ckv_ag_rx_valid(ckv_ag_rx_valid),
        .ckv_ag_rx_rank(ckv_ag_rx_rank), .ckv_ag_rx_gid(ckv_ag_rx_gid), .ckv_ag_rx_row(ckv_ag_rx_row),
        .ckv_cycles_to_ready(ckv_cycles_to_ready), .ckv_fault_code(ckv_fault_code),
        .qs_fetched(), .qs_consumed(), .qs_why(), .kb_records(), .kb_writes(), .kb_highwater(), .kb_stalls(),
        .hbm_refreshes(), .hbm_w_reads(), .rtr_drops(), .kv_ops(), .kv_words(), .kv_sectors_written(),
        .kv_refetches(), .kv_wq_high(), .kv_hold_cycles(), .kv_hbm_grants(), .kv_fault_code(),
        .rope_region_ok(), .rope_fault(), .rope_hbm_grants(), .rope_hbm_wait_cycles());

    assign dbg_pc = dut.u_tile.u_core.pc;
    wire [31:0] dbg_faults = {11'd0, dut.u_tile.qrom_rom_fault, dut.u_tile.rope_read_fault, dut.u_tile.idx_user_fault, dut.u_tile.kb_ring_fault,
        dut.u_tile.u_core.coll_fault, dut.u_tile.u_core.rope_pf_fault, dut.u_tile.u_core.win_fault,
        dut.u_tile.u_core.win_capture_fault, dut.u_tile.u_core.rom_fault_w, dut.u_tile.u_core.he_fault,
        dut.u_tile.u_core.xu_fault, dut.u_tile.u_core.qe_fault, dut.u_tile.u_core.su_fault, dut.u_tile.u_core.me_fault,
        dut.u_tile.u_core.e_fault, dut.u_tile.u_core.fuse_orphan, 1'b0};
    // sticky copy of the fault sources (a source may pulse: the core latches the OR)
    reg [31:0] dbg_fsticky;
    always @(posedge clk or negedge rst_n) if (!rst_n) dbg_fsticky <= 32'd0; else dbg_fsticky <= dbg_fsticky | dbg_faults
        | {31'd0, dut.u_tile.u_core.FULL_SHAPE != 0 && dut.u_tile.u_core.st == 4'd6 && dut.u_tile.u_core.d_unit == 3'd0 &&
           (dut.u_tile.u_core.d_ctl == 3'd5 || dut.u_tile.u_core.d_ctl == 3'd6) && !dut.u_tile.u_core.rope_ctl_ok};
    assign dbg_state = {dbg_fsticky, 4'(dut.u_tile.u_core.st), dut.u_tile.u_core.d_unit, dut.u_tile.u_core.idles,
                        dut.coll_busy, dut.u_tile.u_core.waited, dut.u_cdma.busy, dut.u_cdma.e_mode, dut.u_cdma.fault,
                        dut.e_valid, dut.e_ready, dut.o_valid, dut.o_ready, 7'd0};
    // dbg_fs: 0 me 1 su 2 qe 3 xu 4 he 5 rom 6 coll 7 rope_pf 8 win 9 win_cap 10 qrom 11 rope_read 12 idx_user
    //         13 kb_ring 14..17 e_fault[0..3] 18 fuse_orphan 19 rope ctl 20 key_user(die) 21 core.fault 22 t_fault
    wire [23:0] fs_now;
    assign fs_now[0] = dut.u_tile.u_core.me_fault;
    assign fs_now[1] = dut.u_tile.u_core.su_fault;
    assign fs_now[2] = dut.u_tile.u_core.qe_fault;
    assign fs_now[3] = dut.u_tile.u_core.xu_fault;
    assign fs_now[4] = dut.u_tile.u_core.he_fault;
    assign fs_now[5] = dut.u_tile.u_core.rom_fault_w;
    assign fs_now[6] = dut.u_tile.u_core.coll_fault;
    assign fs_now[7] = dut.u_tile.u_core.rope_pf_fault;
    assign fs_now[8] = dut.u_tile.u_core.win_fault;
    assign fs_now[9] = dut.u_tile.u_core.win_capture_fault;
    assign fs_now[10] = dut.u_tile.qrom_rom_fault;
    assign fs_now[11] = dut.u_tile.rope_read_fault;
    assign fs_now[12] = dut.u_tile.idx_user_fault;
    assign fs_now[13] = dut.u_tile.kb_ring_fault;
    assign fs_now[17:14] = dut.u_tile.u_core.e_fault;
    assign fs_now[18] = dut.u_tile.u_core.fuse_orphan;
    assign fs_now[19] = dut.u_tile.u_core.st == 4'd6 && dut.u_tile.u_core.d_unit == 3'd0 &&
                        (dut.u_tile.u_core.d_ctl == 3'd5 || dut.u_tile.u_core.d_ctl == 3'd6) && !dut.u_tile.u_core.rope_ctl_ok;
    assign fs_now[20] = dut.key_user_fault;
    assign fs_now[21] = dut.u_tile.u_core.fault;
    assign fs_now[22] = dut.t_fault;
    assign fs_now[23] = 1'b0;
    always @(posedge clk or negedge rst_n) if (!rst_n) dbg_fs <= 24'd0; else dbg_fs <= dbg_fs | fs_now;
    assign dbg_words = {dut.u_cdma.words_out[15:0], dut.u_cdma.words_in[15:0]};
    // ---- images ---------------------------------------------------------------------------------------
    string dir;
    integer fd, i;
    reg [255:0] sw;
    reg [31:0] sa;
    function automatic bit exists(input string f);
        integer h;
        begin
            h = $fopen(f, "r");
            exists = h != 0;
            if (h != 0) $fclose(h);
        end
    endfunction
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        if (exists({dir, "/prog.hex"})) $readmemh({dir, "/prog.hex"}, dut.u_tile.prog);
        if (exists({dir, "/crom.hex"})) $readmemh({dir, "/crom.hex"}, dut.u_tile.crom);
        if (exists({dir, "/hbank.hex"})) $readmemh({dir, "/hbank.hex"}, dut.u_tile.hbank);
        if (exists({dir, "/hrom.hex"})) $readmemh({dir, "/hrom.hex"}, dut.u_tile.hrom);
        if (exists({dir, "/erom.hex"})) $readmemh({dir, "/erom.hex"}, dut.u_tile.erom);
        if (exists({dir, "/vm_init.hex"})) $readmemh({dir, "/vm_init.hex"}, dut.u_tile.vm);
        if (exists({dir, "/hbm0.hex"})) $readmemh({dir, "/hbm0.hex"}, dut.g_hbm[0].u_hbm.u_k.mem);
        if (exists({dir, "/hbm1.hex"})) $readmemh({dir, "/hbm1.hex"}, dut.g_hbm[1].u_hbm.u_k.mem);
        if (exists({dir, "/hbm2.hex"})) $readmemh({dir, "/hbm2.hex"}, dut.g_hbm[2].u_hbm.u_k.mem);
        if (exists({dir, "/hbm3.hex"})) $readmemh({dir, "/hbm3.hex"}, dut.g_hbm[3].u_hbm.u_k.mem);
        fd = $fopen({dir, "/hbmsparse0.hex"}, "r");
        if (fd != 0) begin while ($fscanf(fd, "%h %h\n", sa, sw) == 2) dut.g_hbm[0].u_hbm.u_k.mem[sa] = sw; $fclose(fd); end
        fd = $fopen({dir, "/hbmsparse1.hex"}, "r");
        if (fd != 0) begin while ($fscanf(fd, "%h %h\n", sa, sw) == 2) dut.g_hbm[1].u_hbm.u_k.mem[sa] = sw; $fclose(fd); end
        fd = $fopen({dir, "/hbmsparse2.hex"}, "r");
        if (fd != 0) begin while ($fscanf(fd, "%h %h\n", sa, sw) == 2) dut.g_hbm[2].u_hbm.u_k.mem[sa] = sw; $fclose(fd); end
        fd = $fopen({dir, "/hbmsparse3.hex"}, "r");
        if (fd != 0) begin while ($fscanf(fd, "%h %h\n", sa, sw) == 2) dut.g_hbm[3].u_hbm.u_k.mem[sa] = sw; $fclose(fd); end
        // the ring-placed index keys (tools/w11_idx_ring_place.py; IDX_RING = 1)
        fd = $fopen({dir, "/ikring_s0.hex"}, "r");
        if (fd != 0) begin while ($fscanf(fd, "%h %h\n", sa, sw) == 2) dut.g_hbm[0].u_hbm.u_k.mem[sa] = sw; $fclose(fd); end
        fd = $fopen({dir, "/ikring_s1.hex"}, "r");
        if (fd != 0) begin while ($fscanf(fd, "%h %h\n", sa, sw) == 2) dut.g_hbm[1].u_hbm.u_k.mem[sa] = sw; $fclose(fd); end
        fd = $fopen({dir, "/ikring_s2.hex"}, "r");
        if (fd != 0) begin while ($fscanf(fd, "%h %h\n", sa, sw) == 2) dut.g_hbm[2].u_hbm.u_k.mem[sa] = sw; $fclose(fd); end
        fd = $fopen({dir, "/ikring_s3.hex"}, "r");
        if (fd != 0) begin while ($fscanf(fd, "%h %h\n", sa, sw) == 2) dut.g_hbm[3].u_hbm.u_k.mem[sa] = sw; $fclose(fd); end
        // indexed layers: the compressed rows this die owns, '<sector> <word>' on stack k (ckv_s<k>.hex)
        fd = $fopen({dir, "/ckv_s0.hex"}, "r");
        if (fd != 0) begin while ($fscanf(fd, "%h %h\n", sa, sw) == 2) dut.g_hbm[0].u_hbm.u_k.mem[sa] = sw; $fclose(fd); end
        fd = $fopen({dir, "/ckv_s1.hex"}, "r");
        if (fd != 0) begin while ($fscanf(fd, "%h %h\n", sa, sw) == 2) dut.g_hbm[1].u_hbm.u_k.mem[sa] = sw; $fclose(fd); end
        fd = $fopen({dir, "/ckv_s2.hex"}, "r");
        if (fd != 0) begin while ($fscanf(fd, "%h %h\n", sa, sw) == 2) dut.g_hbm[2].u_hbm.u_k.mem[sa] = sw; $fclose(fd); end
        fd = $fopen({dir, "/ckv_s3.hex"}, "r");
        if (fd != 0) begin while ($fscanf(fd, "%h %h\n", sa, sw) == 2) dut.g_hbm[3].u_hbm.u_k.mem[sa] = sw; $fclose(fd); end
    end
    // final vector memory dump on request (the host calls it through DPI export)
    export "DPI-C" function v41rt_vm_word;
    import "DPI-C" context function void v41rt_die_register(input int rank);
    initial v41rt_die_register(RANK);
    function int v41rt_vm_word(input int a);
        v41rt_vm_word = dut.u_tile.vm[a];
    endfunction

    wire c8_engine_start;
    wire [20:0] c8_engine_token,c8_engine_pos;
    wire [9:0] c8_engine_user;
    wire [13:0] c8_engine_entry;
    wire [46:0] c8_engine_identity;
    generate if(C8_CONTEXT) begin:g_c8_context
        initial if(!C8_PUBLICATION) $fatal(1,"C8 context requires actual native publication callbacks");
        ot_dsrom_c8_stage_context u_context(
            .clk(clk),.rst_n(rst_n),.offer_v(start),.offer_ready(c8_offer_ready),
            .offer_token(token),.offer_pos(pos),.offer_user(user),
            .offer_epoch(c8_position_identity[46:31]),.offer_entry(c8_entry),
            .context_v(c8_context_v),.context_restored(c8_context_restored),
            .context_identity(c8_context_identity),.context_token(c8_context_token),.context_entry(c8_context_entry),
            .engine_start(c8_engine_start),.engine_token(c8_engine_token),.engine_pos(c8_engine_pos),
            .engine_user(c8_engine_user),.engine_entry(c8_engine_entry),.engine_identity(c8_engine_identity),
            .engine_done(done),.write_journal_quiet(c8_write_quiet),
            .write_quarantine(c8_write_quarantine),.write_fault(c8_write_fault),
            .retire_v(c8_retire_v),.retire_identity(c8_retire_identity),
            .active(c8_stage_active),.quarantine(c8_stage_quarantine));
    end else begin:g_no_c8_context
        assign c8_offer_ready=rst_n;assign c8_context_v=0;assign c8_retire_v=0;
        assign c8_stage_active=0;assign c8_stage_quarantine=0;
        assign c8_context_identity=0;assign c8_retire_identity=0;
        assign c8_context_token=0;assign c8_context_entry=0;
        assign c8_engine_start=0;assign c8_engine_token=0;assign c8_engine_pos=0;
        assign c8_engine_user=0;assign c8_engine_entry=0;assign c8_engine_identity=0;
    end endgenerate

`ifndef SYNTHESIS
    generate if(S81_COMMAND_TRACE) begin:g_s81_trace
        integer launch_serial=0, command_ordinal=0;
        reg [46:0] trace_identity=0;
        initial if(!C8_CONTEXT || !C8_PUBLICATION || S81_TRACE_STAGE<0 || S81_TRACE_STAGE>=81)
            $fatal(1,"S81 trace requires actual source-root context/publication");
        always @(posedge clk) if(rst_n) begin
            if(c8_engine_start) begin
                launch_serial=launch_serial+1; command_ordinal=0;
                trace_identity=c8_engine_identity;
                $display("S81_LAUNCH stage=%0d rank=%0d launch=%0d identity=%0d entry=%0d token=%0d", S81_TRACE_STAGE,RANK,launch_serial,trace_identity,c8_engine_entry,c8_engine_token);
            end
            if(dut.cmd_go) begin
                if(launch_serial==0) $fatal(1,"collective without actual engine launch");
                $display("S81_COLLECTIVE stage=%0d rank=%0d launch=%0d identity=%0d ordinal=%0d pc=%0d op=%0d src=%0d dst=%0d n=%0d ibase=%0d k=%0d stride=%0d seq=%0d rnd=%0d", S81_TRACE_STAGE,RANK,launch_serial,trace_identity,command_ordinal,dbg_pc,dut.core_coll_op,dut.core_coll_src,dut.core_coll_dst,dut.core_coll_n,dut.core_coll_ibase,dut.core_coll_k,dut.core_coll_stride,dut.core_coll_seq,dut.core_coll_rnd);
                command_ordinal=command_ordinal+1;
            end
            if(c8_retire_v)
                $display("S81_RETIRE stage=%0d rank=%0d launch=%0d identity=%0d",S81_TRACE_STAGE,RANK,launch_serial,c8_retire_identity);
        end
    end endgenerate
`endif

`ifndef SYNTHESIS
    export "DPI-C" function v41rt_c8_workspace_write;
    function int v41rt_c8_workspace_write(input longint unsigned identity,
                                         input int address, input int raw_bits);
        v41rt_c8_workspace_write=1;
        if(S81_HOST_WORKSPACE && C8_CONTEXT && C8_PUBLICATION && rst_n &&
           identity < (64'd1 << 47) && address>=0 && address<(1<<19) &&
           c8_context_v && !c8_context_restored && !c8_stage_active &&
           identity[46:0]==c8_context_identity && c8_write_quiet &&
           !c8_write_fault && !c8_write_quarantine && !c8_stage_quarantine &&
           !(|dut.u_tile.rom_we)) begin
            dut.u_tile.vm[address]=32'(raw_bits);
            v41rt_c8_workspace_write=(dut.u_tile.vm[address]===32'(raw_bits)) ? 0 : 2;
        end
    endfunction
`endif

    assign capture_identity=C8_CONTEXT ? c8_engine_identity : c8_position_identity;
`ifndef SYNTHESIS
    initial if(S81_CAPTURE && (!C8_CONTEXT || !C8_PUBLICATION || ROM_R!=128))
      $fatal(1,"S81 capture requires native R128 saved C8 identity/publication");
    always @(posedge clk) if(rst_n && S81_CAPTURE && S81_COMMAND_TRACE)begin
      for(integer rr=0;rr<ROM_R;rr=rr+1)if(capture_vm_accept[rr])
        $display("S81_VM_COMMIT stage=%0d rank=%0d identity=%0d root=%0d addr=%0d raw=%08x",S81_TRACE_STAGE,RANK,capture_identity,rr,dut.u_tile.rom_waddr[rr*30 +:30],dut.u_tile.rom_wdata[rr*32 +:32]);
      if(c8_retire_v && (capture_live || capture_fault || !c8_write_quiet))
        $fatal(1,"C8 retirement before actual ROM visibility/fault fence");
    end
`endif

    // Existing engine signals only; fresh producer provenance is retained by
    // the caller binder. END/retire alone does not authorize full-stage output.
    assign native_result_selected = (NATIVE_RESULT_READ || WFC_COMPLETION_JOIN) != 0;
    assign native_result_active = (NATIVE_RESULT_READ || WFC_COMPLETION_JOIN) && c8_stage_active;
    assign native_result_identity = c8_engine_identity;
    assign native_result_entry = c8_engine_entry;
    assign native_result_pc = dbg_pc;
    assign native_result_done = (NATIVE_RESULT_READ || WFC_COMPLETION_JOIN) && done;
    assign native_result_producer_take = (NATIVE_RESULT_READ || WFC_COMPLETION_JOIN) &&
        dut.u_tile.u_core.e_go[dut.u_tile.u_core.EAM] &&
        dut.u_tile.u_core.e_ready[dut.u_tile.u_core.EAM] && dut.u_tile.u_core.me_amax;
    assign native_result_am_any = (NATIVE_RESULT_READ || WFC_COMPLETION_JOIN) && dut.u_tile.u_core.am_any_v[0];
    assign native_result_end_take = (NATIVE_RESULT_READ || WFC_COMPLETION_JOIN) && !fault &&
        dut.u_tile.u_core.st == 4'd6 && dut.u_tile.u_core.d_unit == 3'd0 &&
        dut.u_tile.u_core.d_ctl == 3'd0 && dut.u_tile.u_core.waited;

    wire joined_stage_done;
    wire [20:0] joined_stage_token;
    wire [31:0] joined_stage_value;
    initial if (WFC_COMPLETION_JOIN && (!PKG_WAVE || !C8_CONTEXT || !S81_CAPTURE))
        $fatal(1,"finite completion join requires selected WAVE/C8/native capture");
    ot_dsrom_wf_stage_completion_join #(.ENABLE(WFC_COMPLETION_JOIN)) u_wf_stage_completion (
        .clk(clk), .rst_n(rst_n),
        .request_v(wf_join_request_v), .request_binding_valid(wf_join_request_binding_valid),
        .request_ready(wf_join_request_ready), .request_identity(wf_join_request_identity),
        .request_terminal_entry(wf_join_terminal_entry), .request_producer_pc(wf_join_producer_pc),
        .request_end_pc(wf_join_end_pc),
        .native_active(native_result_active), .native_producer_take(native_result_producer_take),
        .native_end_take(native_result_end_take), .native_done(native_result_done),
        .native_am_any(native_result_am_any), .native_identity(native_result_identity),
        .native_entry(native_result_entry), .native_pc(native_result_pc),
        .native_next_token(native_result_token), .native_next_value(native_result_value),
        .coverage_valid(wf_join_coverage_valid), .coverage_wholeplan_complete(wf_join_wholeplan_complete),
        .coverage_identity(wf_join_coverage_identity), .visibility_valid(wf_join_visibility_valid),
        .visibility_fault(wf_join_visibility_fault), .visibility_identity(wf_join_visibility_identity),
        .visibility(wf_join_visibility), .c8_write_quiet(c8_write_quiet),
        .c8_quarantine(c8_write_quarantine || c8_stage_quarantine), .c8_fault(c8_write_fault),
        .capture_live(capture_live), .capture_drained(capture_drained), .capture_fault(capture_fault),
        .collective_busy(dut.coll_busy), .collective_fault(dut.die_coll_fault), .native_fault(fault),
        .stage_accepted(wf_stage_accepted), .stage_done(joined_stage_done),
        .stage_next_token(joined_stage_token), .stage_next_value(joined_stage_value),
        .pending(wf_join_pending), .fault(wf_join_fault));

endmodule
