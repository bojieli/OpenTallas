`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ROM-array token simulation of the reduced DeepSeek-V4.1 decode: a layer-range
// pipeline of V4.1 hardwired decode cores (tools/hdc_program_v41_array.py
// decides the split and what crosses a boundary; the configuration comes in as
// v41_array_cfg.svh, generated per build by tools/rtl_hdc_v41_array_campaign.py).
//
// Package n: one ot_hdc_core_v41 and one ot_rom_pkg_ctrl_x with the package's
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
module tb_hdc_v41_array #(
    parameter integer USERS = 2,
    parameter integer STALL = 0
) (input wire clk);
    `include "v41_array_cfg.svh"
    localparam integer INSTR_BITS = 1536;
    localparam integer W = 16, G = 4, BL = 16, QLB = 272, AW = 24, NW = 16, PAW = 14, HNL = 3;
    localparam integer HROM_WORDS = 1 << 19, WROM_WORDS = 1 << 19, QROM_WORDS = 1 << 16, EROM_WORDS = 1 << 19;
    localparam integer CROM_WORDS = 1 << 15, KVW = 32768, PS = 16384, PROG_WORDS = 1 << PAW;
    localparam integer VMP = PB + USERS * PS;       // physical vector memory, elements
    localparam integer FLIT = 512, MAXU = 16, DESTS = 64;
    localparam integer LINK_CH = FABRIC ? 30 : 60;

    // -- shared ROMs -----------------------------------------------------------------------
    reg [G*W*16-1:0]  wrom [0:WROM_WORDS-1];
    reg [HNL*32-1:0]  hrom [0:HROM_WORDS-1];
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
                ot_rom_pkg_link #(.FLIT_BYTES(FLIT / 8), .TX_STAGES(2), .CHANNEL_CYCLES(LINK_CH), .RX_STAGES(2),
                                  .CREDITS(32)) u_link (
                    .clk(clk), .rst_n(rst_n),
                    .in_valid(tx_v[n]), .in_ready(tx_r[n]), .in_data(tx_d[n*FLIT +: FLIT]), .in_last(tx_l[n]),
                    .out_valid(rx_v[DST]), .out_ready(rx_r[DST]), .out_data(rx_d[DST*FLIT +: FLIT]),
                    .out_last(rx_l[DST]), .credit_stalls(l_stalls[n*32 +: 32]));
            end
            assign r_drops = 0; assign r_overflow = 1'b0;
        end else begin : g_star
            wire [NODES-1:0] ri_v, ri_r, ri_l, ro_v, ro_r, ro_l, ri_c;
            wire [NODES*FLIT-1:0] ri_d, ro_d;
            ot_rom_fabric_router #(.NP(NODES), .FW(FLIT), .BUF(4), .DESTS(DESTS), .ROUTE_INIT(ROUTE)) u_router (
                .clk(clk), .rst_n(rst_n),
                .in_valid(ri_v), .in_ready(ri_r), .in_credit(ri_c), .in_data(ri_d), .in_last(ri_l),
                .out_valid(ro_v), .out_ready(ro_r), .out_data(ro_d), .out_last(ro_l),
                .cfg_we(1'b0), .cfg_dest(8'd0), .cfg_mask({NODES{1'b0}}), .drops(r_drops), .overflow(r_overflow));
            for (n = 0; n < NODES; n = n + 1) begin : g_link
                ot_rom_pkg_link #(.FLIT_BYTES(FLIT / 8), .TX_STAGES(2), .CHANNEL_CYCLES(LINK_CH), .RX_STAGES(2),
                                  .CREDITS(32)) u_up (
                    .clk(clk), .rst_n(rst_n),
                    .in_valid(tx_v[n]), .in_ready(tx_r[n]), .in_data(tx_d[n*FLIT +: FLIT]), .in_last(tx_l[n]),
                    .out_valid(ri_v[n]), .out_ready(ri_r[n]), .out_data(ri_d[n*FLIT +: FLIT]),
                    .out_last(ri_l[n]), .credit_stalls(l_stalls[n*32 +: 32]));
                ot_rom_pkg_link #(.FLIT_BYTES(FLIT / 8), .TX_STAGES(2), .CHANNEL_CYCLES(LINK_CH), .RX_STAGES(2),
                                  .CREDITS(32)) u_down (
                    .clk(clk), .rst_n(rst_n),
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
            wire wrom_re, ewrom_re; wire [AW-1:0] wrom_addr, ewrom_addr; reg [G*W*16-1:0] wrom_q, ewrom_q;
            wire qrom_re; wire [AW-1:0] qrom_addr; reg [BL*QLB-1:0] qrom_q;
            wire hrom_re; wire [AW-1:0] hrom_addr; reg [HNL*32-1:0] hrom_q;
            wire vh_re; wire [AW-1:0] vh_addr; reg [31:0] vh_q;
            wire ww_h_we; wire [AW-1:0] ww_h_addr; wire [31:0] ww_h_mask; wire [1023:0] ww_h_data;
            wire erom_re; wire [AW-1:0] erom_addr; reg [263:0] erom_q;
            wire [3:0] crom_re; wire [4*AW-1:0] crom_addr; reg [4*64-1:0] crom_q;
            wire xcrom_re; wire [AW-1:0] xcrom_addr; reg [63:0] xcrom_q;
            wire kv_re, kv_we; wire [G*AW-1:0] kv_raddr; wire [AW-1:0] kv_waddr; reg [G*W*32-1:0] kv_q;
            wire [31:0] kv_wdata;
            wire [G-1:0] vx_re; wire [G*AW-1:0] vx_addr; reg [G*32-1:0] vx_q;
            wire [3:0] vs_re; wire [4*AW-1:0] vs_addr; reg [4*32-1:0] vs_q;
            wire vi_re, vq_re, vr_re, wqr_re, wxr_re;
            wire [AW-1:0] vi_addr, vq_addr, vr_addr, wqr_addr, wxr_addr;
            reg [31:0] vi_q, vq_q, vr_q;
            reg [1023:0] wqr_q, wxr_q;
            wire [G-1:0] vw_me_we; wire [G*AW-1:0] vw_me_addr; wire [G*W-1:0] vw_me_mask;
            wire [G*W*32-1:0] vw_me_data;
            wire vw_su_we, vw_rd_we, vw_xe_we, ww_q_we, ww_x_we;
            wire [AW-1:0] vw_su_addr, vw_rd_addr, vw_xe_addr, ww_q_addr, ww_x_addr;
            wire [31:0] vw_su_data, vw_rd_data, vw_xe_data, ww_q_mask, ww_x_mask;
            wire [1023:0] ww_q_data, ww_x_data;
            wire me_ov; wire [G*AW-1:0] me_oaddr; wire [G*W-1:0] me_omask; wire [G*W*32-1:0] me_odata;
            wire [4:0] unit_busy; wire [2:0] issue_unit;

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

            ot_hdc_core_v41 core (
                .clk(clk), .rst_n(rst_n), .start(core_start), .token(core_token), .pos(core_pos),
                .done(done), .next_token(next_token), .next_val(next_val), .cycles(cycles), .fault(fault_w[n]),
                .prime_v(prime_v), .prime_first(prime_first), .prime_cid(prime_cid),
                .prog_re(prog_re), .prog_addr(prog_addr), .prog_q(prog_q),
                .wrom_re(wrom_re), .wrom_addr(wrom_addr), .wrom_q(wrom_q),
                .ewrom_re(ewrom_re), .ewrom_addr(ewrom_addr), .ewrom_q(ewrom_q),
                .qrom_re(qrom_re), .qrom_addr(qrom_addr), .qrom_q(qrom_q),
                .hrom_re(hrom_re), .hrom_addr(hrom_addr), .hrom_q(hrom_q), .vh_re(vh_re), .vh_addr(vh_addr),
                .vh_q(vh_q), .ww_h_we(ww_h_we), .ww_h_addr(ww_h_addr), .ww_h_mask(ww_h_mask), .ww_h_data(ww_h_data),
                .erom_re(erom_re), .erom_addr(erom_addr), .erom_q(erom_q),
                .crom_re(crom_re), .crom_addr(crom_addr), .crom_q(crom_q),
                .xcrom_re(xcrom_re), .xcrom_addr(xcrom_addr), .xcrom_q(xcrom_q),
                .kv_re(kv_re), .kv_raddr(kv_raddr), .kv_q(kv_q), .kv_we(kv_we), .kv_waddr(kv_waddr),
                .kv_wdata(kv_wdata),
                .vx_re(vx_re), .vx_addr(vx_addr), .vx_q(vx_q), .vs_re(vs_re), .vs_addr(vs_addr), .vs_q(vs_q),
                .vi_re(vi_re), .vi_addr(vi_addr), .vi_q(vi_q), .vq_re(vq_re), .vq_addr(vq_addr), .vq_q(vq_q),
                .vr_re(vr_re), .vr_addr(vr_addr), .vr_q(vr_q), .wqr_re(wqr_re), .wqr_addr(wqr_addr), .wqr_q(wqr_q),
                .wxr_re(wxr_re), .wxr_addr(wxr_addr), .wxr_q(wxr_q),
                .vw_me_we(vw_me_we), .vw_me_addr(vw_me_addr), .vw_me_mask(vw_me_mask), .vw_me_data(vw_me_data),
                .vw_su_we(vw_su_we), .vw_su_addr(vw_su_addr), .vw_su_data(vw_su_data),
                .vw_rd_we(vw_rd_we), .vw_rd_addr(vw_rd_addr), .vw_rd_data(vw_rd_data),
                .vw_xe_we(vw_xe_we), .vw_xe_addr(vw_xe_addr), .vw_xe_data(vw_xe_data),
                .ww_q_we(ww_q_we), .ww_q_addr(ww_q_addr), .ww_q_mask(ww_q_mask), .ww_q_data(ww_q_data),
                .ww_x_we(ww_x_we), .ww_x_addr(ww_x_addr), .ww_x_mask(ww_x_mask), .ww_x_data(ww_x_data),
                .me_ov(me_ov), .me_oaddr(me_oaddr), .me_omask(me_omask), .me_odata(me_odata),
                .unit_busy(unit_busy), .issue_unit(issue_unit));

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
                if (ewrom_re) ewrom_q <= wrom[ewrom_addr[18:0]];
                if (qrom_re) qrom_q <= qrom[qrom_addr[15:0]];
                if (hrom_re) hrom_q <= hrom[hrom_addr[18:0]];
                if (erom_re) erom_q <= erom[erom_addr[18:0]];
                for (q = 0; q < 4; q = q + 1) if (crom_re[q]) crom_q[64*q +: 64] <= crom[crom_addr[q*AW +: 15]];
                if (xcrom_re) xcrom_q <= crom[xcrom_addr[14:0]];
                for (q = 0; q < G; q = q + 1) if (kv_re) kv_q[q*W*32 +: W*32] <= kv[kv_raddr[q*AW +: 15] + kv_base];
                if (vh_re) vh_q <= vm[pa(vh_addr, cur_u)];
                for (q = 0; q < G; q = q + 1) if (vx_re[q]) vx_q[32*q +: 32] <= vm[pa(vx_addr[q*AW +: AW], cur_u)];
                for (q = 0; q < 4; q = q + 1) if (vs_re[q]) vs_q[32*q +: 32] <= vm[pa(vs_addr[q*AW +: AW], cur_u)];
                if (vi_re) vi_q <= vm[pa(vi_addr, cur_u)];
                if (vq_re) vq_q <= vm[pa(vq_addr, cur_u)];
                if (vr_re) vr_q <= vm[pa(vr_addr, cur_u)];
                if (wqr_re) for (q = 0; q < 32; q = q + 1) wqr_q[32*q +: 32] <= vm[pa(wqr_addr, cur_u) + q];
                if (wxr_re) for (q = 0; q < 32; q = q + 1) wxr_q[32*q +: 32] <= vm[pa(wxr_addr, cur_u) + q];
                if (ww_h_we)
                    for (q = 0; q < 32; q = q + 1) if (ww_h_mask[q]) vm[pa(ww_h_addr, cur_u) + q] <= ww_h_data[32*q +: 32];
                if (kv_we) kv[(kv_waddr >> 4) + kv_base][32*kv_waddr[3:0] +: 32] <= kv_wdata;
                for (q = 0; q < G; q = q + 1)
                    if (vw_me_we[q])
                        for (l = 0; l < W; l = l + 1)
                            if (vw_me_mask[q*W + l])
                                vm[pa({vw_me_addr[q*AW +: 12], 4'b0}, cur_u) + l] <= vw_me_data[32*(q*W + l) +: 32];
                if (vw_su_we) vm[pa(vw_su_addr, cur_u)] <= vw_su_data;
                if (vw_rd_we) vm[pa(vw_rd_addr, cur_u)] <= vw_rd_data;
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
    always @(*) begin
        l_stall_sum = 0;
        for (i = 0; i < NLINKS; i = i + 1) l_stall_sum = l_stall_sum + l_stalls[i*32 +: 32];
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
        $readmemh({romdir, "/erom.hex"}, erom);
        $readmemh({romdir, "/crom.hex"}, crom);
        $readmemh({dir, "/prompts.hex"}, prompt);
        $readmemh({dir, "/expect_tokens.hex"}, e_tok);
        $readmemh({dir, "/expect_logits.hex"}, e_lg);
        for (u = 0; u < MAXU; u = u + 1) gen_n[u] = 0;
    end

    reg [63:0] end_cyc = 0;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 5) rst_n <= 1'b1;
        if (finished == n_users && !checking) begin checking <= 1'b1; end_cyc <= cyc; end
        if (checking && checked_pkgs == NODES) begin
            if (fault_w != 0 || pfault_w != 0 || r_overflow) begin
                bad = bad + 1;
                $display("FAULT core=%b protocol=%b overflow=%0d", fault_w, pfault_w, r_overflow);
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
