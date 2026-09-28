`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ROM-array token simulation of the reduced DeepSeek-V4.1 decode: a layer-range
// pipeline of V4.1 hardwired decode cores (tools/hdc_program_v41_array.py
// decides the split and what crosses a boundary; the configuration comes in as
// v41_array_cfg.svh, generated per build by tools/rtl_hdc_v41_array_campaign.py).
//
// Package n: one ot_hdc_core_v41x and one ot_rom_pkg_ctrl_x with the package's
// memories (behavioural): program, vector memory, KV SRAM.  The weight,
// quantised, HE, Engram and constant ROMs are one image read through
// per-package ports.  Per-user state:
//   * KV SRAM: a slice per user (the controller's kv_base);
//   * vector memory: the persistent segment [PB, PB + PS) (compressor slots,
//     compressed rows, SIDE staging) has a copy per user -- the memory adds
//     user * PS to every core address in it (the controller addresses its
//     SIDE writes physically);
//   * the Engram hash history: a package that hashes (C_PRIME) keeps each
//     user's last three token ids and primes the core's hash unit with them
//     before the step starts (a context restore of up to 3 primes plus 16
//     cycles for their hash results to drain; `done` is held from the
//     controller meanwhile).
//
// Messages: HIDDEN (hop: H words, scalars, relayed items), SIDE (multicast of a
// producer's new shared rows), RESULT (argmax of an lm_head part to package 0).
// FABRIC 0: point-to-point ot_rom_pkg_link ring (n -> n+1, last -> 0);
// FABRIC 1: one NODES-port ot_rom_fabric_router, each package on an uplink and
// a downlink (ROUTE: ids < NODES are packages, 32 + q the SIDE group of
// producer q, 48 the lm_head group).
//
// Checks: package 0 compares every step's reduced token (prompt positions
// too) with the golden's; every lm_head package compares its part's logits
// with the golden's, bit for bit, every step; at the end every package's KV
// slice and persistent segment of every user is compared with the ISA
// pipeline model's final state for that user's prompt.
// ---------------------------------------------------------------------------
`ifndef HDC_SW
`define HDC_SW 8
`endif
`ifndef HDC_X_HE
`define HDC_X_HE 1
`endif
`ifndef HDC_X_ME
`define HDC_X_ME 0
`endif
`ifndef HDC_X_ATT
`define HDC_X_ATT 0
`endif
`ifndef HDC_X_IDX
`define HDC_X_IDX 0
`endif
`ifndef HDC_X_SEL
`define HDC_X_SEL 0
`endif
`ifndef HDC_X_EG
`define HDC_X_EG 0
`endif
`ifndef HDC_X_SU
`define HDC_X_SU 0
`endif
`ifndef HDC_W_HBM
`define HDC_W_HBM 0
`endif
`ifndef HDC_KV_HBM
`define HDC_KV_HBM 0
`endif
module tb_hdc_v41x_array #(
    parameter integer USERS = 2,
    parameter integer STALL = 0
) (input wire clk);
    `include "v41_array_cfg.svh"
    localparam integer INSTR_BITS = 1536;
    localparam integer W = 16, G = 4, BL = 16, QLB = 272, AW = 24, NW = 16, PAW = 14, HNL = 3;
    localparam integer SW = `HDC_SW, HS = 8, HHW = 8, HBAW = 16;       // stream-unit lanes, HE K chunks (as tb_hdc_core_v41)
    localparam integer MG = 8, MBAW = 17, ML = 2, SUN = 16, SUM = 8;
    localparam integer XSQ = 4, XSW = 16;
    localparam integer NPC = 8, LWIN = 10, LAW = 12, SPW = BL * QLB / 256;
    localparam integer HMEM = 1 << 20, IKH_WORDS = 1 << 18;
    localparam integer IKH_USER_SHIFT = $clog2(IKH_WORDS);
    localparam integer HROM_WORDS = 1 << 16, WROM_WORDS = 1 << 19, QROM_WORDS = 1 << 16, EROM_WORDS = 1 << 19;
    localparam integer CROM_WORDS = 1 << 15, KVW = 32768, PS = 16384, PROG_WORDS = 1 << PAW;
    localparam integer VMP = PB + USERS * PS;       // physical vector memory, elements
    localparam integer FLIT = 512, MAXU = 16, DESTS = 64;
    localparam integer LINK_CH_MAX = FABRIC ? 228 : 60;
    integer link_ch = FABRIC ? 30 : 60;
    initial begin
        if (`HDC_KV_HBM && `HDC_X_IDX != 2)
            $fatal(1, "HDC_KV_HBM requires pooled index HBM to exercise shared K stacks");
        if ($value$plusargs("LINK_CH=%d", link_ch)) begin
            if (link_ch < 1 || link_ch > LINK_CH_MAX)
                $fatal(1, "LINK_CH=%0d outside 1..%0d", link_ch, LINK_CH_MAX);
        end
    end

    // -- shared ROMs -----------------------------------------------------------------------
    reg [G*W*16-1:0]  wrom [0:WROM_WORDS-1];
    reg [HS*HNL*32-1:0] hrom [0:HROM_WORDS-1];
    reg [HHW*32-1:0] hbank [0:(1<<HBAW)*8-1];
    reg [31:0]        mbank [0:8*MG*(1<<MBAW)-1];
    reg [AW-1:0]      cfg [0:15];
    reg [BL*QLB-1:0]  qrom [0:QROM_WORDS-1];
    reg [263:0]       erom [0:EROM_WORDS-1];
    reg [63:0]        crom [0:CROM_WORDS-1];
    localparam integer NPMAX = 8, SMAX = 16;         // prompt tokens and steps provisioned per prompt
    reg [NW-1:0]      prompt [0:NPR*NPMAX-1];
    reg [NW-1:0]      e_tok [0:NPR*SMAX-1];
    reg [31:0]        e_lg [0:NPR*SMAX*VOCAB-1];
    reg [8*512-1:0]   dir, romdir;
    // +NPROMPT / +NGEN: prompt tokens (a prefix of each prompt) and generated tokens per user;
    // +HB=n: heartbeat every n cycles
    integer n_gen = 3, n_users = USERS, n_prompt = NPMAX, hb = 0;
    reg rst_n = 1'b0;
    integer cyc = 0;

    wire [NODES-1:0] tx_v, tx_r, tx_l, rx_v, rx_r, rx_l;
    wire [NODES*FLIT-1:0] tx_d, rx_d;
    wire [NODES-1:0] fault_w, pfault_w, busy_w;
    wire [NODES-1:0] qs_fault_w;
    wire [NODES-1:0] kv_fault_w;
    wire [NODES*32-1:0] kv_ops_w, kv_words_w, kv_writes_w, kv_holds_w;
    wire [NODES*4*32-1:0] kv_hbm_state_bad_w;
    wire [NODES*32-1:0] qs_bad_w, qs_words_w, qs_hbm_reads_w;
    wire [NODES*32-1:0] idx_records_w, idx_writes_w, idx_stalls_w;
    wire [NODES*USERS-1:0] idx_user_read_w, idx_user_record_w;
    wire [7:0] users_done;
    wire tok_v; wire [7:0] tok_u; wire [NW-1:0] tok_p, tok_i;

    // -- fabric --------------------------------------------------------------------------------
    localparam integer NLINKS = FABRIC ? 2 * NODES : NODES;
    wire [NLINKS*32-1:0] l_stalls;
    wire [31:0] r_drops; wire r_overflow;
    genvar n;
    generate
        if (FABRIC == 0) begin : g_p2p
            for (n = 0; n < NODES; n = n + 1) begin : g_link
                localparam integer DST = (n + 1) % NODES;
                ot_rom_pkg_link #(.FLIT_BYTES(FLIT / 8), .TX_STAGES(2), .CHANNEL_CYCLES(LINK_CH_MAX), .RX_STAGES(2),
                                  .CREDITS(32), .DYNAMIC_DELAY(FABRIC)) u_link (
                    .clk(clk), .rst_n(rst_n),
                    .channel_cycles(link_ch[15:0]),
                    .in_valid(tx_v[n]), .in_ready(tx_r[n]), .in_data(tx_d[n*FLIT +: FLIT]), .in_last(tx_l[n]),
                    .out_valid(rx_v[DST]), .out_ready(rx_r[DST]), .out_data(rx_d[DST*FLIT +: FLIT]),
                    .out_last(rx_l[DST]), .credit_stalls(l_stalls[n*32 +: 32]));
            end
            assign r_drops = 0; assign r_overflow = 1'b0;
        end else begin : g_star
            wire [NODES-1:0] ri_v, ri_r, ri_l, ro_v, ro_r, ro_l, ri_c;
            wire [NODES*FLIT-1:0] ri_d, ro_d;
            ot_rom_fabric_router #(.NP(NODES), .FW(FLIT), .BUF(4), .DESTS(DESTS),
                                   .INPUT_READY_VALID(1), .ROUTE_INIT(ROUTE)) u_router (
                .clk(clk), .rst_n(rst_n),
                .in_valid(ri_v), .in_ready(ri_r), .in_credit(ri_c), .in_data(ri_d), .in_last(ri_l),
                .out_valid(ro_v), .out_ready(ro_r), .out_data(ro_d), .out_last(ro_l),
                .cfg_we(1'b0), .cfg_dest(8'd0), .cfg_mask({NODES{1'b0}}), .drops(r_drops), .overflow(r_overflow));
            for (n = 0; n < NODES; n = n + 1) begin : g_link
                ot_rom_pkg_link #(.FLIT_BYTES(FLIT / 8), .TX_STAGES(2), .CHANNEL_CYCLES(LINK_CH_MAX), .RX_STAGES(2),
                                  .CREDITS(32), .DYNAMIC_DELAY(FABRIC)) u_up (
                    .clk(clk), .rst_n(rst_n),
                    .channel_cycles(link_ch[15:0]),
                    .in_valid(tx_v[n]), .in_ready(tx_r[n]), .in_data(tx_d[n*FLIT +: FLIT]), .in_last(tx_l[n]),
                    .out_valid(ri_v[n]), .out_ready(ri_r[n]), .out_data(ri_d[n*FLIT +: FLIT]),
                    .out_last(ri_l[n]), .credit_stalls(l_stalls[n*32 +: 32]));
                ot_rom_pkg_link #(.FLIT_BYTES(FLIT / 8), .TX_STAGES(2), .CHANNEL_CYCLES(LINK_CH_MAX), .RX_STAGES(2),
                                  .CREDITS(32), .DYNAMIC_DELAY(FABRIC)) u_down (
                    .clk(clk), .rst_n(rst_n),
                    .channel_cycles(link_ch[15:0]),
                    .in_valid(ro_v[n]), .in_ready(ro_r[n]), .in_data(ro_d[n*FLIT +: FLIT]), .in_last(ro_l[n]),
                    .out_valid(rx_v[n]), .out_ready(rx_r[n]), .out_data(rx_d[n*FLIT +: FLIT]),
                    .out_last(rx_l[n]), .credit_stalls(l_stalls[(NODES + n)*32 +: 32]));
            end
        end
    endgenerate

    integer gen_n [0:MAXU-1];
    integer bad = 0, finished = 0, gen_total = 0, lg_bad = 0, lg_checked = 0, st_bad = 0, checked_pkgs = 0;
    reg checking = 1'b0;

    generate
        for (n = 0; n < NODES; n = n + 1) begin : g_node
            localparam integer PRIME = C_PRIME(n);
            localparam integer HEAD = C_HEAD(n);
            localparam integer PROWS = C_PROWS(n);
            localparam integer ROW0 = C_ROW0(n);
            localparam integer HID = C_HID(n);

            // -- memories -------------------------------------------------------------------
            reg [INSTR_BITS-1:0] prog [0:PROG_WORDS-1];
            reg [31:0]           vm [0:VMP-1];
            reg [W*32-1:0]       kv [0:USERS*KVW-1];
            reg [31:0]           lg [0:VOCAB-1];

            reg rst_core = 1'b0;
            wire done, cfault;
            wire [NW-1:0] next_token;
            wire [31:0] next_val, cycles;
            reg prime_v = 1'b0, prime_first = 1'b0;
            reg [11:0] prime_cid = 0;
            wire prog_re; wire [PAW-1:0] prog_addr; reg [INSTR_BITS-1:0] prog_q;
            wire wrom_re; wire [AW-1:0] wrom_addr; reg [G*W*16-1:0] wrom_q;
            wire [SW-1:0] ewrom_re; wire [SW*AW-1:0] ewrom_addr; reg [SW*G*W*16-1:0] ewrom_q;
            wire qrom_re; wire [AW-1:0] qrom_addr;
            wire [BL*QLB-1:0] qrom_q, qrom_stream_q;
            reg [BL*QLB-1:0] qrom_rom_q;
            assign qrom_q = `HDC_W_HBM ? qrom_stream_q : qrom_rom_q;
            wire hrom_re; wire [AW-1:0] hrom_addr; reg [HS*HNL*32-1:0] hrom_q;
            wire [7:0] hb_re; wire [8*HBAW-1:0] hb_addr; reg [8*HHW*32-1:0] hb_q;
            wire [7:0] mb_re; wire [8*MBAW-1:0] mb_addr;
            reg [8*MG*32-1:0] mb_p [0:ML-1];
            wire [HS-1:0] vh_re; wire [HS*AW-1:0] vh_addr; reg [HS*32-1:0] vh_q;
            wire ww_h_we; wire [AW-1:0] ww_h_addr; wire [31:0] ww_h_mask; wire [1023:0] ww_h_data;
            wire erom_re; wire [AW-1:0] erom_addr; reg [263:0] erom_q;
            wire [4*SW-1:0] crom_re; wire [4*SW*AW-1:0] crom_addr; reg [4*SW*64-1:0] crom_q;
            wire xcrom_re; wire [AW-1:0] xcrom_addr; reg [63:0] xcrom_q;
            wire kv_re; wire [G*AW-1:0] kv_raddr;
            reg [G*W*32-1:0] kv_q_local;
            wire [G*W*32-1:0] kv_q_hbm, kv_q;
            assign kv_q = `HDC_KV_HBM ? kv_q_hbm : kv_q_local;
            wire [SW-1:0] kv_we; wire [SW*AW-1:0] kv_waddr; wire [SW*32-1:0] kv_wdata;
            wire kvd_v, kv_ok; wire [AW-1:0] kvd_wbase, kvd_ts, kvd_ks, kvd_js;
            wire [NW-1:0] kvd_tiles, kvd_k, kvd_nout, kvd_pos;
            wire [1:0] kvd_hg; wire kvd_mmode;
            wire [G-1:0] vx_re; wire [G*AW-1:0] vx_addr; reg [G*32-1:0] vx_q;
            wire [4*SW-1:0] vs_re; wire [4*SW*AW-1:0] vs_addr; reg [4*SW*32-1:0] vs_q;
            wire [SW-1:0] vi_re; wire [SW*AW-1:0] vi_addr; reg [SW*32-1:0] vi_q;
            wire [XSQ-1:0] vsl_re; wire [XSQ*AW-1:0] vsl_addr; reg [XSQ*XSW*32-1:0] vsl_q;
            wire [SUN-1:0] xs_vi_re, xs_vm_we, xs_kv_we;
            wire [SUN*AW-1:0] xs_vi_addr, xs_vm_waddr, xs_kv_waddr;
            reg [SUN*32-1:0] xs_vi_q;
            wire [4*SUN-1:0] xs_rd_re; wire [4*SUN*AW-1:0] xs_rd_addr;
            wire [8*SUN-1:0] xs_rd_src; reg [4*SUN*32-1:0] xs_rd_q;
            wire [SUN*32-1:0] xs_vm_wdata, xs_kv_wdata;
            wire [SUN/8-1:0] xs_res_we; wire [SUN/8*AW-1:0] xs_res_addr;
            wire [SUN/8*32-1:0] xs_res_data;
            wire vq_re, vr_re, wqr_re, wxr_re;
            wire [AW-1:0] vq_addr, vr_addr, wqr_addr, wxr_addr;
            reg [31:0] vq_q, vr_q;
            reg [1023:0] wqr_q, wxr_q;
            wire [G-1:0] vw_me_we; wire [G*AW-1:0] vw_me_addr; wire [G*W-1:0] vw_me_mask;
            wire [G*W*32-1:0] vw_me_data;
            wire [SW-1:0] vw_su_we, vw_rd_we; wire [SW*AW-1:0] vw_su_addr, vw_rd_addr;
            wire [SW*32-1:0] vw_su_data, vw_rd_data;
            wire vw_xe_we, ww_q_we, ww_x_we;
            wire [AW-1:0] vw_xe_addr, ww_q_addr, ww_x_addr;
            wire [31:0] vw_xe_data, ww_q_mask, ww_x_mask;
            wire [1023:0] ww_q_data, ww_x_data;
            wire me_ov; wire [G*AW-1:0] me_oaddr; wire [G*W-1:0] me_omask; wire [G*W*32-1:0] me_odata;
            wire [4:0] unit_busy; wire [2:0] issue_unit;
            wire qd_v, q_ok, wrel_v; wire [AW-1:0] qd_wbase;
            wire [7:0] qd_nb; wire [NW-1:0] qd_tiles;
            wire qs_fault; wire [31:0] qs_bad, qs_words, qs_hbm_reads;
            wire [127:0] pikh_req_v, pikh_req_rdy, pikh_rsp_v, pikh_rsp_rdy;
            wire [128*28-1:0] pikh_req_addr;
            wire [128*4-1:0] pikh_req_len, pikh_rsp_beat;
            wire [128*16-1:0] pikh_req_tag, pikh_rsp_tag;
            wire [128*256-1:0] pikh_rsp_data;
            wire pikw_v, pikw_rdy; wire [3:0] pikw_stack_mask;
            wire [27:0] pikw_csec, pikw_ssec; wire [511:0] pikw_codes;
            wire [2:0] pikw_sslot; wire [31:0] pikw_scales;
            wire [31:0] idxwr_records, idxwr_writes, idxwr_highwater;
            wire [31:0] idxwr_read_stalls, idxwr_writer_stalls;
            wire [63:0] idxwr_refreshes;
            assign qs_fault_w[n] = qs_fault;
            assign qs_bad_w[n*32 +: 32] = qs_bad;
            assign qs_words_w[n*32 +: 32] = qs_words;
            assign qs_hbm_reads_w[n*32 +: 32] = qs_hbm_reads;
            assign idx_records_w[n*32 +: 32] = idxwr_records;
            assign idx_writes_w[n*32 +: 32] = idxwr_writes;
            assign idx_stalls_w[n*32 +: 32] = idxwr_read_stalls + idxwr_writer_stalls;

            // controller <-> (context restore) <-> core
            wire          c_start, c_done;
            wire [NW-1:0] c_token, c_pos;
            wire [AW-1:0] kv_base;
            reg           k_start = 1'b0;
            reg  [NW-1:0] k_token = 0, k_pos = 0;
            wire          core_start = PRIME ? k_start : c_start;
            wire [NW-1:0] core_token = PRIME ? k_token : c_token;
            wire [NW-1:0] core_pos = PRIME ? k_pos : c_pos;
            reg  [2:0]    sh_st = 3'd0;
            assign c_done = PRIME ? (done && sh_st == 3'd0) : done;
            wire [7:0]    cur_u = kv_base / KVW;

            ot_hdc_core_v41x #(.SW(SW), .HS(HS), .W_HBM(`HDC_W_HBM), .KV_HBM(`HDC_KV_HBM),
                                   .X_HE(`HDC_X_HE), .X_ME(`HDC_X_ME), .X_ATT(`HDC_X_ATT),
                                   .X_IDX(`HDC_X_IDX), .X_SEL(`HDC_X_SEL), .X_EG(`HDC_X_EG),
                                   .X_SU(`HDC_X_SU), .SUN(SUN), .SUM(SUM),
                                   .XSQ(XSQ), .XSW(XSW), .MG(MG), .MBAW(MBAW)) core (
                .clk(clk), .rst_n(rst_n), .start(core_start), .token(core_token), .pos(core_pos), .entry(14'd0), .acc_n(), .acc_tok(),
                .done(done), .next_token(next_token), .next_val(next_val), .cycles(cycles), .fault(fault_w[n]),
                .prime_v(prime_v), .prime_first(prime_first), .prime_cid(prime_cid),
                .prog_re(prog_re), .prog_addr(prog_addr), .prog_q(prog_q),
                .wrom_re(wrom_re), .wrom_addr(wrom_addr), .wrom_q(wrom_q),
                .ewrom_re(ewrom_re), .ewrom_addr(ewrom_addr), .ewrom_q(ewrom_q),
                .qrom_re(qrom_re), .qrom_addr(qrom_addr), .qrom_q(qrom_q),
                .hrom_re(hrom_re), .hrom_addr(hrom_addr), .hrom_q(hrom_q),
                .cfg_ik_base(cfg[0]), .cfg_me_xs(cfg[1][3:0]),
                .mb_re(mb_re), .mb_addr(mb_addr), .mb_q(mb_p[ML-1]),
                .pikh_req_v(pikh_req_v), .pikh_req_rdy(pikh_req_rdy),
                .pikh_req_addr(pikh_req_addr), .pikh_req_len(pikh_req_len),
                .pikh_req_tag(pikh_req_tag), .pikh_rsp_v(pikh_rsp_v),
                .pikh_rsp_rdy(pikh_rsp_rdy), .pikh_rsp_tag(pikh_rsp_tag),
                .pikh_rsp_beat(pikh_rsp_beat), .pikh_rsp_data(pikh_rsp_data),
                .pikw_v(pikw_v), .pikw_rdy(pikw_rdy), .pikw_stack_mask(pikw_stack_mask),
                .pikw_csec(pikw_csec), .pikw_codes(pikw_codes), .pikw_ssec(pikw_ssec),
                .pikw_sslot(pikw_sslot), .pikw_scales(pikw_scales),
                .hb_re(hb_re), .hb_addr(hb_addr), .hb_q(hb_q), .vh_re(vh_re), .vh_addr(vh_addr),
                .vh_q(vh_q), .ww_h_we(ww_h_we), .ww_h_addr(ww_h_addr), .ww_h_mask(ww_h_mask), .ww_h_data(ww_h_data),
                .erom_re(erom_re), .erom_addr(erom_addr), .erom_q(erom_q),
                .crom_re(crom_re), .crom_addr(crom_addr), .crom_q(crom_q),
                .xcrom_re(xcrom_re), .xcrom_addr(xcrom_addr), .xcrom_q(xcrom_q),
                .kv_re(kv_re), .kv_raddr(kv_raddr), .kv_q(kv_q), .kv_we(kv_we), .kv_waddr(kv_waddr),
                .kv_wdata(kv_wdata),
                .vx_re(vx_re), .vx_addr(vx_addr), .vx_q(vx_q), .vs_re(vs_re), .vs_addr(vs_addr), .vs_q(vs_q),
                .vi_re(vi_re), .vi_addr(vi_addr), .vi_q(vi_q), .vq_re(vq_re), .vq_addr(vq_addr), .vq_q(vq_q),
                .vsl_re(vsl_re), .vsl_addr(vsl_addr), .vsl_q(vsl_q),
                .xs_vi_re(xs_vi_re), .xs_vi_addr(xs_vi_addr), .xs_vi_q(xs_vi_q),
                .xs_rd_re(xs_rd_re), .xs_rd_addr(xs_rd_addr), .xs_rd_src(xs_rd_src),
                .xs_rd_q(xs_rd_q), .xs_vm_we(xs_vm_we), .xs_vm_waddr(xs_vm_waddr),
                .xs_vm_wdata(xs_vm_wdata), .xs_kv_we(xs_kv_we), .xs_kv_waddr(xs_kv_waddr),
                .xs_kv_wdata(xs_kv_wdata), .xs_res_we(xs_res_we), .xs_res_addr(xs_res_addr),
                .xs_res_data(xs_res_data),
                .vr_re(vr_re), .vr_addr(vr_addr), .vr_q(vr_q), .wqr_re(wqr_re), .wqr_addr(wqr_addr), .wqr_q(wqr_q),
                .wxr_re(wxr_re), .wxr_addr(wxr_addr), .wxr_q(wxr_q),
                .vw_me_we(vw_me_we), .vw_me_addr(vw_me_addr), .vw_me_mask(vw_me_mask), .vw_me_data(vw_me_data),
                .vw_su_we(vw_su_we), .vw_su_addr(vw_su_addr), .vw_su_data(vw_su_data),
                .vw_rd_we(vw_rd_we), .vw_rd_addr(vw_rd_addr), .vw_rd_data(vw_rd_data),
                .vw_xe_we(vw_xe_we), .vw_xe_addr(vw_xe_addr), .vw_xe_data(vw_xe_data),
                .ww_q_we(ww_q_we), .ww_q_addr(ww_q_addr), .ww_q_mask(ww_q_mask), .ww_q_data(ww_q_data),
                .ww_x_we(ww_x_we), .ww_x_addr(ww_x_addr), .ww_x_mask(ww_x_mask), .ww_x_data(ww_x_data),
                .me_ov(me_ov), .me_oaddr(me_oaddr), .me_omask(me_omask), .me_odata(me_odata),
                .unit_busy(unit_busy), .issue_unit(issue_unit),
                .qd_v(qd_v), .qd_wbase(qd_wbase), .qd_nb(qd_nb), .qd_tiles(qd_tiles),
                .q_ok(q_ok), .wrel_v(wrel_v),
                .kvd_v(kvd_v), .kvd_wbase(kvd_wbase), .kvd_ts(kvd_ts), .kvd_ks(kvd_ks),
                .kvd_js(kvd_js), .kvd_tiles(kvd_tiles), .kvd_k(kvd_k), .kvd_nout(kvd_nout),
                .kvd_pos(kvd_pos), .kvd_hg(kvd_hg), .kvd_mmode(kvd_mmode), .kv_ok(kv_ok));

            // Each package has its own QE fetch list and weight window. The HBM
            // sectors are a common read-only image; the list follows this
            // package's stage program, so only its QE instructions are fetched.
            if (`HDC_W_HBM) begin : g_qs
                reg [127:0] qlist [0:(1<<LAW)-1];
                reg [255:0] qwin [0:SPW-1][0:(1<<LWIN)-1];
                reg [127:0] l_q;
                wire l_re, xi_re, qw_re, hq_v, hq_rdy;
                wire [LAW-1:0] l_addr;
                wire [AW-1:0] xi_addr;
                reg [31:0] xi_q;
                wire [SPW-1:0] qw_we;
                wire [SPW*LWIN-1:0] qw_waddr;
                wire [BL*QLB-1:0] qw_wdata;
                wire [LWIN-1:0] qw_raddr;
                reg [BL*QLB-1:0] qw_q;
                wire [23:0] hq_addr; wire [5:0] hq_len;
                wire [LWIN-1:0] hq_tag;
                wire [NPC-1:0] hr_v, hr_rdy, pc_room;
                wire [NPC*LWIN-1:0] hr_tag;
                wire [NPC*5-1:0] hr_beat;
                wire [NPC*256-1:0] hr_data;
                wire [3:0] qs_why;
                wire [31:0] qs_fetched, qs_consumed;
                reg [15:0] qlead, qrate;
                reg [8*512-1:0] qdir, qromdir;
                integer qi, qb, qr;
                reg qchk_v; reg [AW-1:0] qchk_a;
                reg [31:0] q_bad = 0, q_words = 0;
                assign qs_bad = q_bad;
                assign qs_words = q_words;
                always @(*) begin
                    qr = 0;
                    for (integer p = 0; p < NPC; p = p + 1) qr = qr + u_hbm.st_rd[p];
                end
                assign qs_hbm_reads = qr;
                initial begin
                    if (!$value$plusargs("DIR=%s", qdir)) qdir = ".";
                    if (!$value$plusargs("ROMS=%s", qromdir)) qromdir = qdir;
                    if (!$value$plusargs("QLEAD=%d", qlead)) qlead = 512;
                    if (!$value$plusargs("QRATE=%d", qrate)) qrate = 32;
                    $readmemh({qdir, "/qlist_stage", D1, D0, ".hex"}, qlist);
                    for (qi = 0; qi < HMEM; qi = qi + 1) u_hbm.mem[qi] = 256'd0;
                    $readmemh({qromdir, "/hbm_q.hex"}, u_hbm.mem);
                end
                ot_hdc_qstream #(.BL(BL), .QLB(QLB), .AW(AW), .HAW(24),
                    .NW(NW), .LWIN(LWIN), .NPC(NPC), .LENW(6), .BEATW(5), .LAW(LAW)) u_qs (
                    .clk(clk), .rst_n(rst_n), .cfg_base(24'd0), .cfg_lbase({LAW{1'b0}}),
                    .cfg_lead(qlead), .cfg_rate(qrate), .tok_start(core_start), .pos(core_pos),
                    .l_re(l_re), .l_addr(l_addr), .l_q(l_q), .vi_re(xi_re), .vi_addr(xi_addr),
                    .vi_q(xi_q), .wrel_v(wrel_v), .qd_v(qd_v), .qd_nb(qd_nb),
                    .qd_tiles(qd_tiles), .q_ok(q_ok), .qr_re(qrom_re), .qr_addr(qrom_addr),
                    .qr_q(qrom_stream_q), .win_we(qw_we), .win_waddr(qw_waddr),
                    .win_wdata(qw_wdata), .win_re(qw_re), .win_raddr(qw_raddr),
                    .win_q(qw_q), .hq_v(hq_v), .hq_rdy(hq_rdy), .hq_addr(hq_addr),
                    .hq_len(hq_len), .hq_tag(hq_tag), .hq_room(pc_room),
                    .hr_v(hr_v), .hr_rdy(hr_rdy), .hr_tag(hr_tag),
                    .hr_beat(hr_beat), .hr_data(hr_data),
                    .fault(qs_fault), .fault_why(qs_why),
                    .st_fetched(qs_fetched), .st_consumed(qs_consumed));
                ot_hdc_hbm_model #(.NPC(NPC), .AW(24), .DW(256), .MEM_WORDS(HMEM),
                    .TAGW(LWIN), .LENW(6), .BEATW(5), .CLK_PS(1000),
                    .PC_RDY(1), .PC_ROOM(16)) u_hbm (
                    .clk(clk), .rst_n(rst_n), .req_v(hq_v), .req_rdy(hq_rdy),
                    .pc_room(pc_room), .req_we(1'b0), .req_addr(hq_addr),
                    .req_len(hq_len), .req_tag(hq_tag), .req_wdata(256'd0),
                    .rsp_v(hr_v), .rsp_rdy(hr_rdy), .rsp_tag(hr_tag),
                    .rsp_beat(hr_beat), .rsp_data(hr_data));
                always @(posedge clk) begin
                    if (l_re) l_q <= qlist[l_addr];
                    if (xi_re) xi_q <= vm[pa(xi_addr, cur_u)];
                    for (qb = 0; qb < SPW; qb = qb + 1) begin
                        if (qw_re) qw_q[qb*256 +: 256] <= qwin[qb][qw_raddr];
                        if (qw_we[qb]) qwin[qb][qw_waddr[qb*LWIN +: LWIN]] <= qw_wdata[qb*256 +: 256];
                    end
                    qchk_v <= qrom_re; qchk_a <= qrom_addr;
                    if (qchk_v) begin
                        q_words <= q_words + 1;
                        if (qrom_q !== qrom[qchk_a[15:0]]) q_bad <= q_bad + 1;
                    end
                end
            end else begin : g_qs_n
                assign qrom_stream_q = 0;
                assign q_ok = 1'b1;
                assign qs_fault = 1'b0;
                assign qs_bad = 0;
                assign qs_words = 0;
                assign qs_hbm_reads = 0;
            end

            // Four replicated 32-pseudo-channel index-key stacks per package.
            // The bridge holds complete K128 records until all sector writes
            // commit; its read arbitration also covers the pooled selector.
            if (`HDC_X_IDX == 2) begin : g_pooled_idx
                localparam integer KV_SBASE = USERS*IKH_WORDS;
                localparam integer KV_SECTORS = USERS*KVW/2;
                wire [127:0] h_v, h_rdy, h_we, h_wr_done;
                wire [128*28-1:0] h_addr;
                wire [128*4-1:0] h_len;
                wire [128*16-1:0] h_tag;
                wire [128*256-1:0] h_wdata;
                wire [128*32-1:0] h_wstrb;
                wire [3:0] km_v, km_rdy, km_we, ks_v, ks_rdy;
                wire [4*28-1:0] km_addr;
                wire [4*4-1:0] km_len, ks_beat;
                wire [4*16-1:0] km_tag, ks_tag;
                wire [4*256-1:0] km_wdata, ks_data;
                wire [4*32-1:0] km_wstrb;
                wire bridge_busy;
                wire [4*64-1:0] stack_refs;
                wire [27:0] user_sector_base = {cur_u, {IKH_USER_SHIFT{1'b0}}};
                wire [27:0] physical_csec = pikw_csec + user_sector_base;
                wire [27:0] physical_ssec = pikw_ssec + user_sector_base;
                wire [128*28-1:0] physical_raddr;
                reg [31:0] user_reads [0:USERS-1];
                reg [31:0] user_records [0:USERS-1];
                for (genvar u = 0; u < USERS; u = u + 1) begin : g_user_activity
                    assign idx_user_read_w[n*USERS+u] = user_reads[u] != 0;
                    assign idx_user_record_w[n*USERS+u] = user_records[u] != 0;
                end
                for (genvar pc = 0; pc < 128; pc = pc + 1) begin : g_user_addr
                    assign physical_raddr[pc*28 +: 28] =
                        pikh_req_addr[pc*28 +: 28] + user_sector_base;
                end
                // The writer FIFO captures these physical addresses at admission.
                // Requests are checked while the current package user is known;
                // the HBM can finish an older user's queued writes later.
                always @(posedge clk) begin
                    if (!rst_n) begin
                        for (integer u = 0; u < USERS; u = u + 1) begin
                            user_reads[u] <= 0;
                            user_records[u] <= 0;
                        end
                    end else begin
                        if (cur_u >= n_users || cur_u >= USERS)
                            $fatal(1, "IDXHBM user out of range pkg=%0d user=%0d", n, cur_u);
                        if (pikw_v && pikw_rdy) begin
                            if (pikw_csec + 1 >= IKH_WORDS || pikw_ssec >= IKH_WORDS)
                                $fatal(1, "IDXHBM write outside user slice pkg=%0d user=%0d code=%0d scale=%0d",
                                       n, cur_u, pikw_csec, pikw_ssec);
                            user_records[cur_u] <= user_records[cur_u] + 1;
                        end
                        for (integer pc = 0; pc < 128; pc = pc + 1)
                            if (pikh_req_v[pc] && pikh_req_rdy[pc]) begin
                                if (pikh_req_addr[pc*28 +: 28] + pikh_req_len[pc*4 +: 4] > IKH_WORDS)
                                    $fatal(1, "IDXHBM read outside user slice pkg=%0d user=%0d pc=%0d addr=%0d len=%0d",
                                           n, cur_u, pc, pikh_req_addr[pc*28 +: 28], pikh_req_len[pc*4 +: 4]);
                            end
                        if (|(pikh_req_v & pikh_req_rdy))
                            user_reads[cur_u] <= user_reads[cur_u] + 1;
                    end
                end
                assign idxwr_refreshes = stack_refs[0 +: 64] + stack_refs[64 +: 64]
                    + stack_refs[128 +: 64] + stack_refs[192 +: 64];
                ot_hdc_v41x_idx_pool_hbm_bridge u_bridge (
                    .clk(clk), .rst_n(rst_n), .w_v(pikw_v), .w_rdy(pikw_rdy),
                    .w_stack_mask(pikw_stack_mask), .w_csec(physical_csec),
                    .w_codes(pikw_codes), .w_ssec(physical_ssec),
                    .w_sslot(pikw_sslot), .w_scales(pikw_scales),
                    .r_v(pikh_req_v), .r_rdy(pikh_req_rdy),
                    .r_addr(physical_raddr), .r_len(pikh_req_len),
                    .r_tag(pikh_req_tag), .h_v(h_v), .h_rdy(h_rdy),
                    .h_addr(h_addr), .h_len(h_len), .h_tag(h_tag),
                    .h_we(h_we), .h_wdata(h_wdata), .h_wstrb(h_wstrb),
                    .h_wr_done(h_wr_done), .busy(bridge_busy),
                    .dbg_records(idxwr_records), .dbg_writes(idxwr_writes),
                    .dbg_fifo_highwater(idxwr_highwater),
                    .dbg_read_stalls(idxwr_read_stalls),
                    .dbg_writer_stalls(idxwr_writer_stalls));
                if (`HDC_KV_HBM) begin : g_kv_hbm
                    wire [4:0] fault_code;
                    wire [31:0] refetches, highwater;
                    ot_chip_v41x_kv_prefetch #(.G(G), .W(W), .SW(SW), .SUN(SUN), .AW(AW),
                        .STG(2048), .SAW(11), .KV_SBASE(KV_SBASE), .KV_SECTORS(KV_SECTORS),
                        .HAW(28), .TAGW(16)) u_kv (
                        .clk(clk), .rst_n(rst_n), .base(kv_base),
                        .kvd_v(kvd_v), .kvd_wbase(kvd_wbase), .kvd_ts(kvd_ts),
                        .kvd_ks(kvd_ks), .kvd_js(kvd_js), .kvd_tiles(kvd_tiles),
                        .kvd_k(kvd_k), .kvd_hg(kvd_hg), .kv_ok(kv_ok),
                        .re(kv_re), .raddr(kv_raddr), .q(kv_q_hbm),
                        .we(kv_we), .waddr(kv_waddr), .wdata(kv_wdata),
                        .xwe(xs_kv_we), .xwaddr(xs_kv_waddr), .xwdata(xs_kv_wdata),
                        .m_v(km_v), .m_rdy(km_rdy), .m_addr(km_addr),
                        .m_len(km_len), .m_tag(km_tag), .m_we(km_we),
                        .m_wdata(km_wdata), .m_wstrb(km_wstrb),
                        .s_v(ks_v), .s_rdy(ks_rdy), .s_tag(ks_tag),
                        .s_beat(ks_beat), .s_data(ks_data),
                        .fault(kv_fault_w[n]), .fault_code(fault_code),
                        .st_ops(kv_ops_w[n*32 +: 32]), .st_words(kv_words_w[n*32 +: 32]),
                        .st_sectors_written(kv_writes_w[n*32 +: 32]),
                        .st_refetches(refetches), .st_wq_high(highwater),
                        .st_hold_cycles(kv_holds_w[n*32 +: 32]));
                end else begin : g_no_kv_hbm
                    assign kv_ok = 1'b1;
                    assign kv_q_hbm = '0;
                    assign km_v = '0; assign km_addr = '0; assign km_len = '0;
                    assign km_tag = '0; assign km_we = '0;
                    assign km_wdata = '0; assign km_wstrb = '0;
                    assign ks_rdy = '1;
                    assign kv_fault_w[n] = 1'b0;
                    assign kv_ops_w[n*32 +: 32] = '0;
                    assign kv_words_w[n*32 +: 32] = '0;
                    assign kv_writes_w[n*32 +: 32] = '0;
                    assign kv_holds_w[n*32 +: 32] = '0;
                end
                for (genvar s = 0; s < 4; s = s + 1) begin : g_stack
                    if (`HDC_KV_HBM) begin : g_shared
                        wire [31:0] sh_v, sh_rdy, sh_we, sh_wr_done, sr_v, sr_rdy;
                        wire [32*28-1:0] sh_addr;
                        wire [32*4-1:0] sh_len, sr_beat;
                        wire [32*17-1:0] sh_tag, sr_tag;
                        wire [32*256-1:0] sh_wdata, sr_data;
                        wire [32*32-1:0] sh_wstrb;
                        ot_chip_v41x_hbm_karb #(.NPC(32), .AW(28), .TAGW(16)) u_arb (
                            .clk(clk), .rst_n(rst_n),
                            .b_v(h_v[s*32 +: 32]), .b_rdy(h_rdy[s*32 +: 32]),
                            .b_addr(h_addr[s*32*28 +: 32*28]), .b_len(h_len[s*32*4 +: 32*4]),
                            .b_tag(h_tag[s*32*16 +: 32*16]), .b_we(h_we[s*32 +: 32]),
                            .b_wdata(h_wdata[s*32*256 +: 32*256]),
                            .b_wstrb(h_wstrb[s*32*32 +: 32*32]),
                            .b_wr_done(h_wr_done[s*32 +: 32]),
                            .b_rsp_v(pikh_rsp_v[s*32 +: 32]),
                            .b_rsp_rdy(pikh_rsp_rdy[s*32 +: 32]),
                            .b_rsp_tag(pikh_rsp_tag[s*32*16 +: 32*16]),
                            .b_rsp_beat(pikh_rsp_beat[s*32*4 +: 32*4]),
                            .b_rsp_data(pikh_rsp_data[s*32*256 +: 32*256]),
                            .k_v(km_v[s]), .k_rdy(km_rdy[s]),
                            .k_addr(km_addr[s*28 +: 28]), .k_len(km_len[s*4 +: 4]),
                            .k_tag(km_tag[s*16 +: 16]), .k_we(km_we[s]),
                            .k_wdata(km_wdata[s*256 +: 256]),
                            .k_wstrb(km_wstrb[s*32 +: 32]), .k_wr_done(),
                            .k_rsp_v(ks_v[s]), .k_rsp_rdy(ks_rdy[s]),
                            .k_rsp_tag(ks_tag[s*16 +: 16]),
                            .k_rsp_beat(ks_beat[s*4 +: 4]),
                            .k_rsp_data(ks_data[s*256 +: 256]),
                            .h_v(sh_v), .h_rdy(sh_rdy), .h_addr(sh_addr),
                            .h_len(sh_len), .h_tag(sh_tag), .h_we(sh_we),
                            .h_wdata(sh_wdata), .h_wstrb(sh_wstrb),
                            .h_wr_done(sh_wr_done), .r_v(sr_v), .r_rdy(sr_rdy),
                            .r_tag(sr_tag), .r_beat(sr_beat), .r_data(sr_data),
                            .k_grants(), .b_grants(), .contended());
                        ot_hdc_v41x_idx_hbm #(.NPC(32), .AW(28), .DW(256),
                            .MEM_WORDS(KV_SBASE + KV_SECTORS), .TAGW(17),
                            .LENW(4), .BEATW(4), .QD(64), .REFPB(3), .MEM_MODE(0)) hm (
                            .clk(clk), .rst_n(rst_n), .req_v(sh_v), .req_rdy(sh_rdy),
                            .req_addr(sh_addr), .req_len(sh_len), .req_tag(sh_tag),
                            .req_we(sh_we), .req_wdata(sh_wdata), .req_wstrb(sh_wstrb),
                            .wr_done(sh_wr_done), .rsp_v(sr_v), .rsp_rdy(sr_rdy),
                            .rsp_tag(sr_tag), .rsp_beat(sr_beat), .rsp_data(sr_data));
                        reg [63:0] refresh_count;
                        always @(*) begin
                            refresh_count = 0;
                            for (integer p = 0; p < 32; p = p + 1)
                                refresh_count = refresh_count + hm.st_ref[p];
                        end
                        assign stack_refs[s*64 +: 64] = refresh_count;
                        initial for (integer i = 0; i < KV_SBASE + KV_SECTORS; i = i + 1)
                            hm.mem[i] = 256'd0;
                        reg [31:0] state_bad = 0;
                        assign kv_hbm_state_bad_w[(n*4+s)*32 +: 32] = state_bad;
                        always @(posedge clk) if (checking && !printed) begin
                            state_bad = 0;
                            for (integer i = 0; i < USERS*KVW/4; i = i + 1)
                                if ({hm.mem[KV_SBASE+2*i+1], hm.mem[KV_SBASE+2*i]} !== kv[4*i+s]) begin
                                    if (state_bad < 3)
                                        $display("KVHBM_STATE pkg=%0d stack=%0d word=%0d", n, s, i);
                                    state_bad = state_bad + 1;
                                end
                        end
                    end else begin : g_idx_only
                    assign kv_hbm_state_bad_w[(n*4+s)*32 +: 32] = '0;
                    ot_hdc_v41x_idx_hbm #(.NPC(32), .AW(28), .DW(256),
                        .MEM_WORDS(USERS*IKH_WORDS), .TAGW(16), .LENW(4), .BEATW(4),
                        .QD(64), .REFPB(3), .MEM_MODE(0)) hm (
                        .clk(clk), .rst_n(rst_n), .req_v(h_v[s*32 +: 32]),
                        .req_rdy(h_rdy[s*32 +: 32]),
                        .req_addr(h_addr[s*32*28 +: 32*28]),
                        .req_len(h_len[s*32*4 +: 32*4]),
                        .req_tag(h_tag[s*32*16 +: 32*16]),
                        .req_we(h_we[s*32 +: 32]),
                        .req_wdata(h_wdata[s*32*256 +: 32*256]),
                        .req_wstrb(h_wstrb[s*32*32 +: 32*32]),
                        .wr_done(h_wr_done[s*32 +: 32]),
                        .rsp_v(pikh_rsp_v[s*32 +: 32]),
                        .rsp_rdy(pikh_rsp_rdy[s*32 +: 32]),
                        .rsp_tag(pikh_rsp_tag[s*32*16 +: 32*16]),
                        .rsp_beat(pikh_rsp_beat[s*32*4 +: 32*4]),
                        .rsp_data(pikh_rsp_data[s*32*256 +: 32*256]));
                    reg [63:0] refresh_count;
                    always @(*) begin
                        refresh_count = 0;
                        for (integer p = 0; p < 32; p = p + 1)
                            refresh_count = refresh_count + hm.st_ref[p];
                    end
                    assign stack_refs[s*64 +: 64] = refresh_count;
                    initial for (integer i = 0; i < USERS*IKH_WORDS; i = i + 1)
                        hm.mem[i] = 256'd0;
                    end
                end
            end else begin : g_pooled_idx_n
                assign kv_hbm_state_bad_w[n*4*32 +: 4*32] = '0;
                assign kv_ok = 1'b1;
                assign kv_q_hbm = '0;
                assign kv_fault_w[n] = 1'b0;
                assign kv_ops_w[n*32 +: 32] = '0;
                assign kv_words_w[n*32 +: 32] = '0;
                assign kv_writes_w[n*32 +: 32] = '0;
                assign kv_holds_w[n*32 +: 32] = '0;
                assign idx_user_read_w[n*USERS +: USERS] = '0;
                assign idx_user_record_w[n*USERS +: USERS] = '0;
                assign pikh_req_rdy = 0;
                assign pikh_rsp_v = 0;
                assign pikh_rsp_tag = 0;
                assign pikh_rsp_beat = 0;
                assign pikh_rsp_data = 0;
                assign pikw_rdy = 0;
                assign idxwr_records = 0;
                assign idxwr_writes = 0;
                assign idxwr_highwater = 0;
                assign idxwr_read_stalls = 0;
                assign idxwr_writer_stalls = 0;
                assign idxwr_refreshes = 0;
            end

            // stress: random hold-off on both link ports of the controller
            reg in_ok = 1'b1, out_ok = 1'b1;
            if (STALL > 0) begin : g_stall
                always @(posedge clk) begin
                    in_ok  <= ($unsigned($random) % 100) >= STALL;
                    out_ok <= ($unsigned($random) % 100) >= STALL;
                end
            end
            wire c_in_ready, c_out_valid;
            assign rx_r[n] = c_in_ready && in_ok;
            assign tx_v[n] = c_out_valid && out_ok;

            wire          c_we, c_re; wire [15:0] c_waddr, c_raddr;
            wire [FLIT-1:0] c_wdata; reg [FLIT-1:0] c_rq;
            wire          pr_re; wire [7:0] pr_user; wire [NW-1:0] pr_pos; reg [NW-1:0] pr_q;
            wire          t_v; wire [7:0] t_u; wire [NW-1:0] t_p, t_i; wire [7:0] u_done;
            ot_rom_pkg_ctrl_x #(.PKG_ID(n), .FLIT(FLIT), .NW(NW), .AW(AW), .VWA(16), .MAXU(MAXU), .KVW(KVW),
                                .XWORDS(C_TXW(n) > 0 ? C_TXW(n) : 1), .RXWORDS(C_RXW(n) > 0 ? C_RXW(n) : 1),
                                .RXB(C_RXB(n)), .TXB(C_TXB(n)), .SOURCE(n == 0), .RESULT_PARTS(RPARTS),
                                .SEND_HIDDEN(HID >= 0), .HID_DEST(HID >= 0 ? HID : 0),
                                .SEND_RESULT(C_RES(n)), .RES_DEST(0), .COMBINE_IN(C_COMB(n)), .ROW0(ROW0),
                                .FWD_TOKEN(1), .SEND_SIDE(C_SOUT(n)), .SIDE_DEST(C_SDEST(n)),
                                .SIDE_WORDS(C_SW(n) > 0 ? C_SW(n) : 1), .SIDE_TXB(C_STXB(n)),
                                .SIDE_RXB(C_SRXB(n)), .SIDE_IN(C_SIN(n)), .SIDE_USH(10)) ctrl (
                .clk(clk), .rst_n(rst_n),
                .cfg_users(n_users[7:0]), .cfg_prompt_len(n_prompt[NW-1:0]), .cfg_gen_len(n_gen[NW-1:0]),
                .in_valid(rx_v[n] && in_ok), .in_ready(c_in_ready), .in_data(rx_d[n*FLIT +: FLIT]),
                .in_last(rx_l[n]),
                .out_valid(c_out_valid), .out_ready(tx_r[n] && out_ok), .out_data(tx_d[n*FLIT +: FLIT]),
                .out_last(tx_l[n]),
                .core_start(c_start), .core_token(c_token), .core_pos(c_pos), .core_done(c_done),
                .core_next_token(next_token), .core_next_val(next_val), .kv_base(kv_base),
                .vm_we(c_we), .vm_waddr(c_waddr), .vm_wdata(c_wdata), .vm_re(c_re), .vm_raddr(c_raddr),
                .vm_rq(c_rq),
                .pr_re(pr_re), .pr_user(pr_user), .pr_pos(pr_pos), .pr_q(pr_q),
                .core_busy(busy_w[n]), .tok_valid(t_v), .tok_user(t_u), .tok_pos(t_p), .tok_id(t_i),
                .users_done(u_done), .proto_fault(pfault_w[n]));
            if (n == 0) begin : g_obs
                assign tok_v = t_v; assign tok_u = t_u; assign tok_p = t_p; assign tok_i = t_i;
                assign users_done = u_done;
            end

            // -- Engram hash context restore (packages whose program hashes) -----------------
            reg [NW-1:0] htok [0:USERS*3-1];       // per user, the last three tokens (newest first)
            reg [1:0]    sh_k, sh_np;
            reg [4:0]    sh_w;
            reg [7:0]    sh_u;
            integer      hi;
            initial for (hi = 0; hi < USERS * 3; hi = hi + 1) htok[hi] = 0;
            if (PRIME) begin : g_prime
                always @(posedge clk) begin
                    prime_v <= 1'b0;
                    case (sh_st)
                        3'd0: if (c_start) begin
                            k_token <= c_token; k_pos <= c_pos;
                            sh_np <= (c_pos > 3) ? 2'd3 : c_pos[1:0];
                            sh_st <= 3'd1;
                        end
                        3'd1: begin                          // kv_base now holds the user
                            sh_u <= cur_u; sh_k <= sh_np; sh_st <= 3'd2; sh_w <= 5'd0;
                        end
                        3'd2: if (sh_k != 0) begin           // oldest first; the first resets the history
                            prime_v <= 1'b1; prime_first <= (sh_k == sh_np);
                            prime_cid <= crom[TMAP + htok[sh_u * 3 + sh_k - 1]][11:0];
                            sh_k <= sh_k - 1'b1;
                        end else if (sh_np != 0 && sh_w != 5'd16) begin
                            // let the primes' hash results (latency 12) drain before the step's own
                            // hash can be issued, or the unit would take a prime's result as its own
                            sh_w <= sh_w + 1'b1;
                        end else begin
                            k_start <= 1'b1; sh_st <= 3'd3;
                            htok[sh_u * 3 + 2] <= htok[sh_u * 3 + 1];
                            htok[sh_u * 3 + 1] <= htok[sh_u * 3];
                            htok[sh_u * 3] <= k_token;
                        end
                        default: begin k_start <= 1'b0; sh_st <= 3'd0; end
                    endcase
                end
            end

            // -- per-user persistent vector-memory segment ----------------------------------------
            function automatic integer pa(input [AW-1:0] a, input [7:0] u);
                pa = (a[15:0] >= PB) ? a[15:0] + u * PS : a[15:0];
            endfunction

            integer k, q, l, e;
            reg [AW:0] xa;
            reg [8*512-1:0] pdir;
            reg [31:0] e_kv [0:NPR*KVW*W-1];
            reg [31:0] e_vm [0:NPR*PS-1];
            localparam [7:0] D1 = 8'h30 + n / 10;
            localparam [7:0] D0 = 8'h30 + n % 10;
            initial begin
                if (!$value$plusargs("DIR=%s", pdir)) pdir = ".";
                $readmemh({pdir, "/prog_stage", D1, D0, ".hex"}, prog);
                for (k = 0; k < VMP; k = k + 1) vm[k] = 32'd0;
                for (k = 0; k < USERS * KVW; k = k + 1) kv[k] = {(W*32){1'b0}};
                for (k = 0; k < VOCAB; k = k + 1) lg[k] = 32'hFFFFFFFF;
                $readmemh({pdir, "/expect_kv", D1, D0, "_0.hex"}, e_kv, 0, KVW * W - 1);
                $readmemh({pdir, "/expect_vm", D1, D0, "_0.hex"}, e_vm, 0, PS - 1);
                if (NPR > 1) begin
                    $readmemh({pdir, "/expect_kv", D1, D0, "_1.hex"}, e_kv, KVW * W, 2 * KVW * W - 1);
                    $readmemh({pdir, "/expect_vm", D1, D0, "_1.hex"}, e_vm, PS, 2 * PS - 1);
                end
            end

            always @(posedge clk) begin
                if (prog_re) prog_q <= prog[prog_addr];
                if (wrom_re) wrom_q <= wrom[wrom_addr[18:0]];
                for (q = 0; q < SW; q = q + 1)
                    if (ewrom_re[q]) ewrom_q[q*G*W*16 +: G*W*16] <= wrom[ewrom_addr[q*AW +: 19]];
                if (!`HDC_W_HBM && qrom_re) qrom_rom_q <= qrom[qrom_addr[15:0]];
                if (hrom_re) hrom_q <= hrom[hrom_addr[15:0]];
                for (q = 0; q < 8*MG; q = q + 1)
                    mb_p[0][32*q +: 32] <= mbank[32'(mb_addr[(q % 8)*MBAW +: MBAW]) * (8*MG) + q];
                for (l = 1; l < ML; l = l + 1) mb_p[l] <= mb_p[l-1];
                for (q = 0; q < 8; q = q + 1) if (hb_re[q])
                    hb_q[q*HHW*32 +: HHW*32] <= hbank[{hb_addr[q*HBAW +: HBAW], 3'(q)}];
                if (erom_re) erom_q <= erom[erom_addr[18:0]];
                for (q = 0; q < 4*SW; q = q + 1) if (crom_re[q]) crom_q[64*q +: 64] <= crom[crom_addr[q*AW +: 15]];
                if (xcrom_re) xcrom_q <= crom[xcrom_addr[14:0]];
                if (!`HDC_KV_HBM)
                    for (q = 0; q < G; q = q + 1) if (kv_re)
                        kv_q_local[q*W*32 +: W*32] <= kv[kv_raddr[q*AW +: 15] + kv_base];
                for (q = 0; q < HS; q = q + 1) if (vh_re[q]) vh_q[32*q +: 32] <= vm[pa(vh_addr[q*AW +: AW], cur_u)];
                for (q = 0; q < G; q = q + 1) if (vx_re[q]) vx_q[32*q +: 32] <= vm[pa(vx_addr[q*AW +: AW], cur_u)];
                for (q = 0; q < 4*SW; q = q + 1) if (vs_re[q]) vs_q[32*q +: 32] <= vm[pa(vs_addr[q*AW +: AW], cur_u)];
                for (q = 0; q < SW; q = q + 1) if (vi_re[q]) vi_q[32*q +: 32] <= vm[pa(vi_addr[q*AW +: AW], cur_u)];
                for (q = 0; q < XSQ; q = q + 1)
                    if (vsl_re[q]) for (l = 0; l < XSW; l = l + 1)
                        vsl_q[32*(q*XSW+l) +: 32] <= vm[pa(vsl_addr[q*AW +: AW], cur_u) + l];
                for (q = 0; q < SUN; q = q + 1)
                    if (xs_vi_re[q]) xs_vi_q[32*q +: 32] <= vm[pa(xs_vi_addr[q*AW +: AW], cur_u)];
                for (q = 0; q < 4*SUN; q = q + 1) if (xs_rd_re[q]) begin
                    xa = xs_rd_addr[q*AW +: AW];
                    case (xs_rd_src[2*q +: 2])
                        2'd0: xs_rd_q[32*q +: 32] <= vm[pa(xa[AW-1:0], cur_u)];
                        2'd1: xs_rd_q[32*q +: 32] <= crom[xa[14:0]][31:0];
                        2'd2: xs_rd_q[32*q +: 32] <= crom[xa[14:0]][63:32];
                        default: xs_rd_q[32*q +: 32] <= {wrom[xa[24:6]][16*xa[5:0] +: 16], 16'h0000};
                    endcase
                end
                if (vq_re) vq_q <= vm[pa(vq_addr, cur_u)];
                if (vr_re) vr_q <= vm[pa(vr_addr, cur_u)];
                if (wqr_re) for (q = 0; q < 32; q = q + 1) wqr_q[32*q +: 32] <= vm[pa(wqr_addr, cur_u) + q];
                if (wxr_re) for (q = 0; q < 32; q = q + 1) wxr_q[32*q +: 32] <= vm[pa(wxr_addr, cur_u) + q];
                if (ww_h_we)
                    for (q = 0; q < 32; q = q + 1) if (ww_h_mask[q]) vm[pa(ww_h_addr, cur_u) + q] <= ww_h_data[32*q +: 32];
                for (q = 0; q < SW; q = q + 1)
                    if (kv_we[q]) kv[kv_waddr[q*AW+4 +: 15] + kv_base][32*kv_waddr[q*AW +: 4] +: 32] <= kv_wdata[32*q +: 32];
                for (q = 0; q < G; q = q + 1)
                    if (vw_me_we[q])
                        for (l = 0; l < W; l = l + 1)
                            if (vw_me_mask[q*W + l])
                                vm[pa({vw_me_addr[q*AW +: 12], 4'b0}, cur_u) + l] <= vw_me_data[32*(q*W + l) +: 32];
                for (q = 0; q < SW; q = q + 1) if (vw_su_we[q]) vm[pa(vw_su_addr[q*AW +: AW], cur_u)] <= vw_su_data[32*q +: 32];
                for (q = 0; q < SW; q = q + 1) if (vw_rd_we[q]) vm[pa(vw_rd_addr[q*AW +: AW], cur_u)] <= vw_rd_data[32*q +: 32];
                for (q = 0; q < SUN; q = q + 1) begin
                    if (xs_vm_we[q]) vm[pa(xs_vm_waddr[q*AW +: AW], cur_u)] <= xs_vm_wdata[32*q +: 32];
                    if (xs_kv_we[q])
                        kv[xs_kv_waddr[q*AW+4 +: 15] + kv_base][32*xs_kv_waddr[q*AW +: 4] +: 32]
                            <= xs_kv_wdata[32*q +: 32];
                end
                for (q = 0; q < SUN/8; q = q + 1)
                    if (xs_res_we[q]) vm[pa(xs_res_addr[q*AW +: AW], cur_u)] <= xs_res_data[32*q +: 32];
                if (vw_xe_we) vm[pa(vw_xe_addr, cur_u)] <= vw_xe_data;
                if (ww_q_we)
                    for (q = 0; q < 32; q = q + 1) if (ww_q_mask[q]) vm[pa(ww_q_addr, cur_u) + q] <= ww_q_data[32*q +: 32];
                if (ww_x_we)
                    for (q = 0; q < 32; q = q + 1) if (ww_x_mask[q]) vm[pa(ww_x_addr, cur_u) + q] <= ww_x_data[32*q +: 32];
                // controller word ports (physical word addresses)
                if (c_we) for (l = 0; l < W; l = l + 1) vm[{c_waddr, 4'b0} + l] <= c_wdata[32*l +: 32];
                if (c_re) for (l = 0; l < W; l = l + 1) c_rq[32*l +: 32] <= vm[{c_raddr, 4'b0} + l];
                if (pr_re) pr_q <= prompt[(pr_user % NPR) * NPMAX + pr_pos];
                // lm_head part: the unwritten matrix-vector op's result words are its logits
                if (HEAD && me_ov && vw_me_we == 0)
                    for (q = 0; q < G; q = q + 1)
                        for (l = 0; l < W; l = l + 1)
                            if (me_omask[q*W + l] && ({me_oaddr[q*AW +: 12], 4'b0} + l) < PROWS)
                                lg[{me_oaddr[q*AW +: 12], 4'b0} + l] <= me_odata[32*(q*W + l) +: 32];
            end

            // -- accounting and the lm_head logit check ------------------------------------------
            reg [63:0] busy_cycles = 0, side_wait = 0, tx_wait = 0, starved = 0, jobs = 0;
            reg [NW-1:0] job_pos = 0;
            reg done_q = 1'b0, printed = 1'b0;
            integer lb;
            always @(posedge clk) if (rst_n) begin
                if (hb != 0 && cyc % hb == 0)
                    $display("HB cyc=%0d node=%0d st=%0d pc=%0d running=%0d pend=%0d rx_st=%0d tx_st=%0d jobs=%0d",
                             cyc, n, core.st, core.pc, ctrl.running, ctrl.pend, ctrl.rx_st, ctrl.tx_st, jobs);
                if (busy_w[n]) busy_cycles <= busy_cycles + 1;
                else if (ctrl.pend && !ctrl.side_ok) side_wait <= side_wait + 1;
                else if (ctrl.pend && ctrl.tx_hold) tx_wait <= tx_wait + 1;
                else starved <= starved + 1;
                if (core_start) job_pos <= core_pos;
                done_q <= done;
                if (done && !done_q && cyc > 40) begin
                    jobs <= jobs + 1;
                    if (HEAD) begin
                        lb = 0;
                        for (e = 0; e < PROWS; e = e + 1)
                            if (lg[e] !== e_lg[((cur_u % NPR) * SMAX + job_pos) * VOCAB + ROW0 + e]) begin
                                if (lb < 3) $display("LOGIT pkg=%0d user=%0d pos=%0d row=%0d rtl=%h gold=%h", n,
                                                     cur_u, job_pos, ROW0 + e, lg[e],
                                                     e_lg[((cur_u % NPR) * SMAX + job_pos) * VOCAB + ROW0 + e]);
                                lb = lb + 1;
                            end
                        lg_bad = lg_bad + lb;
                        lg_checked = lg_checked + 1;
                    end
                end
            end

            // -- final state: every user's KV slice and persistent segment -----------------------
            integer u2, i2, sb;
            reg [31:0] x2;
            always @(posedge clk) if (checking && !printed) begin
                sb = 0;
                for (u2 = 0; u2 < n_users; u2 = u2 + 1) begin
                    for (i2 = 0; i2 < KVW * W; i2 = i2 + 1) begin
                        x2 = kv[u2 * KVW + i2 / W][32*(i2 % W) +: 32];
                        if (x2 !== e_kv[(u2 % NPR) * KVW * W + i2]) begin
                            if (sb < 3) $display("KV pkg=%0d user=%0d elem=%0d rtl=%h isa=%h", n, u2, i2, x2,
                                                 e_kv[(u2 % NPR) * KVW * W + i2]);
                            sb = sb + 1;
                        end
                    end
                    for (i2 = 0; i2 < PS; i2 = i2 + 1)
                        if (vm[PB + u2 * PS + i2] !== e_vm[(u2 % NPR) * PS + i2]) begin
                            if (sb < 3) $display("VM pkg=%0d user=%0d elem=%0d rtl=%h isa=%h", n, u2, PB + i2,
                                                 vm[PB + u2 * PS + i2], e_vm[(u2 % NPR) * PS + i2]);
                            sb = sb + 1;
                        end
                end
                st_bad = st_bad + sb;
                checked_pkgs = checked_pkgs + 1;
                $display("NODE node=%0d busy=%0d side_wait=%0d tx_wait=%0d starved=%0d jobs=%0d state_mismatch=%0d",
                         n, busy_cycles, side_wait, tx_wait, starved, jobs, sb);
                if (`HDC_W_HBM || `HDC_X_IDX == 2)
                    $display("HBM_NODE node=%0d q_bad=%0d q_words=%0d q_reads=%0d q_fault=%0d idx_records=%0d idx_writes=%0d idx_read_stalls=%0d idx_writer_stalls=%0d idx_refresh=%0d",
                             n, qs_bad, qs_words, qs_hbm_reads, qs_fault, idxwr_records,
                             idxwr_writes, idxwr_read_stalls, idxwr_writer_stalls, idxwr_refreshes);
                printed <= 1'b1;
            end
        end
    endgenerate

    // -- token check at package 0 ----------------------------------------------------------------
    integer i, u;
    always @(posedge clk) if (rst_n) begin
        if (tok_v) begin
            if (tok_i != e_tok[(tok_u % NPR) * SMAX + tok_p]) begin
                bad = bad + 1;
                $display("MISMATCH user=%0d pos=%0d got=%0d gold=%0d", tok_u, tok_p, tok_i,
                         e_tok[(tok_u % NPR) * SMAX + tok_p]);
            end
            $display("TOK user=%0d pos=%0d token=%0d cycle=%0d", tok_u, tok_p, tok_i, cyc);
            if (tok_p >= n_prompt - 1) begin
                gen_n[tok_u] = gen_n[tok_u] + 1; gen_total = gen_total + 1;
                if (gen_n[tok_u] == n_gen) finished = finished + 1;
            end
        end
    end

    reg [31:0] l_stall_sum;
    reg [31:0] q_bad_sum, q_words_sum, q_reads_sum, idx_records_sum, idx_writes_sum;
    reg [31:0] kv_ops_sum, kv_words_sum, kv_writes_sum, kv_holds_sum, kv_state_bad_sum;
    reg [USERS-1:0] idx_users_read, idx_users_wrote;
    always @(*) begin
        l_stall_sum = 0;
        for (i = 0; i < NLINKS; i = i + 1) l_stall_sum = l_stall_sum + l_stalls[i*32 +: 32];
        q_bad_sum = 0; q_words_sum = 0; q_reads_sum = 0; idx_records_sum = 0; idx_writes_sum = 0;
        kv_ops_sum = 0; kv_words_sum = 0; kv_writes_sum = 0;
        kv_holds_sum = 0; kv_state_bad_sum = 0;
        idx_users_read = 0; idx_users_wrote = 0;
        for (i = 0; i < NODES; i = i + 1) begin
            q_bad_sum = q_bad_sum + qs_bad_w[i*32 +: 32];
            q_words_sum = q_words_sum + qs_words_w[i*32 +: 32];
            q_reads_sum = q_reads_sum + qs_hbm_reads_w[i*32 +: 32];
            idx_records_sum = idx_records_sum + idx_records_w[i*32 +: 32];
            idx_writes_sum = idx_writes_sum + idx_writes_w[i*32 +: 32];
            kv_ops_sum = kv_ops_sum + kv_ops_w[i*32 +: 32];
            kv_words_sum = kv_words_sum + kv_words_w[i*32 +: 32];
            kv_writes_sum = kv_writes_sum + kv_writes_w[i*32 +: 32];
            kv_holds_sum = kv_holds_sum + kv_holds_w[i*32 +: 32];
            idx_users_read = idx_users_read | idx_user_read_w[i*USERS +: USERS];
            idx_users_wrote = idx_users_wrote | idx_user_record_w[i*USERS +: USERS];
        end
        for (i = 0; i < 4*NODES; i = i + 1)
            kv_state_bad_sum = kv_state_bad_sum + kv_hbm_state_bad_w[i*32 +: 32];
    end
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        if (!$value$plusargs("ROMS=%s", romdir)) romdir = dir;
        if (!$value$plusargs("NUSERS=%d", n_users)) n_users = USERS;
        if (!$value$plusargs("HB=%d", hb)) hb = 0;
        if (!$value$plusargs("NPROMPT=%d", n_prompt)) n_prompt = NPMAX;
        if (!$value$plusargs("NGEN=%d", n_gen)) n_gen = 3;
        $readmemh({romdir, "/wrom.hex"}, wrom);
        $readmemh({romdir, "/qrom.hex"}, qrom);
        $readmemh({romdir, "/hrom.hex"}, hrom);
        $readmemh({romdir, "/hbank.hex"}, hbank);
        for (integer c = 0; c < 16; c = c + 1) cfg[c] = 0;
        if (`HDC_X_ME || `HDC_X_IDX) begin
            $readmemh({romdir, "/cfg.hex"}, cfg);
            $readmemh({romdir, "/mbank.hex"}, mbank);
        end
        $readmemh({romdir, "/erom.hex"}, erom);
        $readmemh({romdir, "/crom.hex"}, crom);
        $readmemh({dir, "/prompts.hex"}, prompt);
        $readmemh({dir, "/expect_tokens.hex"}, e_tok);
        $readmemh({dir, "/expect_logits.hex"}, e_lg);
        for (u = 0; u < MAXU; u = u + 1) gen_n[u] = 0;
    end

    reg [63:0] end_cyc = 0;
    reg [14:0] kv_drain_wait = 0;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (hb > 0 && cyc != 0 && cyc % hb == 0)
            $display("HEARTBEAT cycle=%0d finished=%0d", cyc, finished);
        if (cyc == 5) rst_n <= 1'b1;
        if (finished == n_users && !checking) begin
            if (end_cyc == 0) end_cyc <= cyc;
            // The final KV element writes can still be in the bounded sector
            // queue after the controller reports the token. Keep the token
            // cycle separate from this observation window, then compare the
            // physical HBM sectors with the exact KV shadow.
            if (`HDC_KV_HBM && kv_drain_wait < 15'd16384)
                kv_drain_wait <= kv_drain_wait + 1'b1;
            else
                checking <= 1'b1;
        end
        if (checking && checked_pkgs == NODES) begin
            if (fault_w != 0 || pfault_w != 0 || r_overflow) begin
                bad = bad + 1;
                $display("FAULT core=%b protocol=%b overflow=%0d", fault_w, pfault_w, r_overflow);
            end
            if (`HDC_W_HBM && (qs_fault_w != 0 || q_bad_sum != 0 || q_words_sum == 0 || q_reads_sum == 0)) begin
                bad = bad + 1;
                $display("QSTREAM_FAIL fault=%b bad=%0d words=%0d reads=%0d", qs_fault_w,
                         q_bad_sum, q_words_sum, q_reads_sum);
            end
            if (`HDC_KV_HBM) begin
                $display("KVHBM ops=%0d words=%0d writes=%0d holds=%0d state_bad=%0d fault=%b",
                         kv_ops_sum, kv_words_sum, kv_writes_sum, kv_holds_sum,
                         kv_state_bad_sum, kv_fault_w);
                if (kv_fault_w != 0 || kv_ops_sum == 0 || kv_words_sum == 0 ||
                    kv_writes_sum == 0 || kv_state_bad_sum != 0) begin
                    bad = bad + 1;
                    $display("KVHBM_FAIL");
                end
            end
            if (`HDC_X_IDX == 2 && (idx_records_sum == 0 || idx_writes_sum != 12 * idx_records_sum)) begin
                bad = bad + 1;
                $display("IDXHBM_FAIL records=%0d writes=%0d", idx_records_sum, idx_writes_sum);
            end
            if (`HDC_X_IDX == 2) begin
                for (integer ui = 0; ui < USERS; ui = ui + 1)
                    if (ui < n_users && (!idx_users_read[ui] || !idx_users_wrote[ui])) begin
                        bad = bad + 1;
                        $display("IDXHBM_USER_FAIL user=%0d read=%0d wrote=%0d", ui,
                                 idx_users_read[ui], idx_users_wrote[ui]);
                    end
                $display("IDXHBM_USERS read=%b wrote=%b", idx_users_read, idx_users_wrote);
            end
            $display("HDC41_ARRAY nodes=%0d users=%0d generated=%0d mismatches=%0d logit_mismatch=%0d lm_head_checks=%0d state_mismatch=%0d total_cycles=%0d",
                     NODES, n_users, gen_total, bad, lg_bad, lg_checked, st_bad, end_cyc);
            $display("USERS_DONE %0d", users_done);
            $display("LINK_STALLS %0d", l_stall_sum);
            if (bad == 0 && lg_bad == 0 && st_bad == 0 && users_done == n_users) $display("PASS");
            else $display("FAIL");
            $finish;
        end
        if (cyc > 400000000) begin $display("TIMEOUT finished=%0d", finished); $finish; end
    end
endmodule
