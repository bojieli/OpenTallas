`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_qwen_rom_sys_top: full-system RTL top of the Qwen3 ROM target, TP-N
// (N = 4 dies), at the reduced vehicle shape of tools/hdc_program.py --tp.
// NEW, DEFAULT-OFF: nothing else instantiates it; no existing file changes.
//
//   host side   ot_qwen_sys_csr (AXI4-Lite split + system status + fault
//               aggregation + interrupt) in front of ot_host_if (MODE 0: the
//               NVMe-style submission / completion rings in host memory, SQ
//               doorbell, CQ phase bit, MSI); the prompt buffer SRAM.
//   control     ot_qwen_sys_rst_seq (power-up: host -> links trained -> HBM
//               round trip -> dies -> ready), ot_qwen_sys_pkg_ctl (the host's
//               step engine port to the N dies: start fan-out, done only when
//               every die is done AND its KV writes are acknowledged by HBM,
//               cross-die token agreement), per-die sequencers.
//   dies        ot_qwen_sys_die x N (core, sequencer, collective engine, link
//               layers, KV service, ROMs, vector memory).
//   PHY         one flit a cycle per ordered die pair (die s -> die t); the
//               channels (and the HBM devices) are outside, as hard IP is.
//
// Nothing on the token path is tied ready: kv_ok comes from the KV service,
// the KV write drain from tagged HBM write-dones, link readiness from link
// training and replay-buffer room, collective readiness from engine credits
// carried by the links, system readiness from the reset sequencer.
//
// Fault sources (FAULT_STATUS bits): die d -> [5d + 0] core or ROM address
// bound, [5d + 1] sequencer (collective protocol, stray record, watchdog),
// [5d + 2] collective engine, [5d + 3] KV service (tag identity, duplicate
// beat, read of an unfilled word, ...), [5d + 4] link (down); [20] dies
// disagree on the token, [21] step watchdog, [22] start before ready,
// [23] boot fault.
// ---------------------------------------------------------------------------
module ot_qwen_rom_sys_top #(
    parameter integer N          = 4,
    parameter integer G          = 4,
    parameter integer NW         = 16,
    parameter integer NSLOT      = 4,
    parameter integer KVW        = 512,      // KV words per user (one die's slice)
    parameter integer TAGW       = 2 + 2 * 16 + 6,
    parameter integer WROM_WORDS = 16384,
    parameter integer NPC        = 4,
    parameter integer HTAGW      = 7,
    parameter integer LINK_TMO   = 96,
    parameter integer TAG_FULL   = 1,
    parameter integer ME_CDC     = 0,
    parameter integer KV_PREFETCH = 0,       // 1: token-start KV prefetch notice to every die's KV service        // 1: matrix engines on fclk (1.2 GHz), the rest on clk (0.9 GHz)
    parameter integer LFW        = 32 + 1 + 1 + 8 + 1 + 8 + 1 + 1 + 3 + (512 + 2 + TAGW)
) (
    input  wire               clk,          // 0.9 GHz serial-chain / control domain (the only clock if ME_CDC = 0)
    input  wire               fclk,         // 1.2 GHz streaming domain, 3:4 with clk from one PLL (ME_CDC = 1)
    input  wire               por_n,
    // host AXI4-Lite slave (13-bit byte address: [12] = 0 host interface, 1 system CSRs)
    input  wire               s_awvalid,
    output wire               s_awready,
    input  wire [12:0]        s_awaddr,
    input  wire               s_wvalid,
    output wire               s_wready,
    input  wire [31:0]        s_wdata,
    input  wire [3:0]         s_wstrb,
    output wire               s_bvalid,
    input  wire               s_bready,
    output wire [1:0]         s_bresp,
    input  wire               s_arvalid,
    output wire               s_arready,
    input  wire [12:0]        s_araddr,
    output wire               s_rvalid,
    input  wire               s_rready,
    output wire [31:0]        s_rdata,
    output wire [1:0]         s_rresp,
    // AXI4 master to host memory (the PCIe bridge's DMA)
    output wire               m_arvalid,
    input  wire               m_arready,
    output wire [63:0]        m_araddr,
    output wire [7:0]         m_arlen,
    output wire [2:0]         m_arsize,
    input  wire               m_rvalid,
    output wire               m_rready,
    input  wire [63:0]        m_rdata,
    input  wire [1:0]         m_rresp,
    input  wire               m_rlast,
    output wire               m_awvalid,
    input  wire               m_awready,
    output wire [63:0]        m_awaddr,
    output wire [7:0]         m_awlen,
    output wire [2:0]         m_awsize,
    output wire               m_wvalid,
    input  wire               m_wready,
    output wire [63:0]        m_wdata,
    output wire [7:0]         m_wstrb,
    output wire               m_wlast,
    input  wire               m_bvalid,
    output wire               m_bready,
    input  wire [1:0]         m_bresp,
    output wire               irq,
    // die-to-die PHY: [(s*N + t)] = die s -> die t
    output wire [N*N*LFW-1:0] ph_tx,
    input  wire [N*N-1:0]     ph_rx_v,       // [(t*N + s)] at die t from die s
    input  wire [N*N*LFW-1:0] ph_rx,
    // HBM controller ports, one per die
    output wire [N-1:0]       h_req_v,
    input  wire [N-1:0]       h_req_rdy,
    output wire [N-1:0]       h_req_we,
    output wire [N*24-1:0]    h_req_addr,
    output wire [N*5-1:0]     h_req_len,
    output wire [N*HTAGW-1:0] h_req_tag,
    output wire [N*256-1:0]   h_req_wdata,
    input  wire [N*NPC-1:0]   h_rsp_v,
    output wire [N*NPC-1:0]   h_rsp_rdy,
    input  wire [N*NPC*HTAGW-1:0] h_rsp_tag,
    input  wire [N*NPC*4-1:0] h_rsp_beat,
    input  wire [N*NPC*256-1:0] h_rsp_data,
    input  wire [N*NPC-1:0]   h_rsp_wr,
    // observation
    output wire               sys_ready,
    output wire [31:0]        fault_src,
    output wire [N-1:0]       die_done,
    output wire [N*NW-1:0]    die_token,
    output wire [N*32-1:0]    die_val,
    output wire               step_start,
    output wire [NW-1:0]      step_pos
);
    localparam integer AW = 24, PLB = 8;
    localparam integer SB = (NSLOT > 1) ? $clog2(NSLOT) : 1;

    // ---------------------------------------------------------------- reset / power-up
    wire host_rst_n, link_rst_n, hbm_rst_n, boot_go, die_rst_n, boot_fault, soft_rst;
    wire [3:0] boot_state, boot_err;
    wire [31:0] boot_cycles;
    wire [N*N-1:0] lup;
    wire [N-1:0] boot_done, boot_ok;
    ot_qwen_sys_rst_seq #(.NL(N*N), .ND(N)) u_rst (
        .clk(clk), .por_n(por_n), .soft_rst(soft_rst), .link_up(lup), .boot_done(boot_done), .boot_ok(boot_ok),
        .host_rst_n(host_rst_n), .link_rst_n(link_rst_n), .hbm_rst_n(hbm_rst_n), .boot_go(boot_go),
        .die_rst_n(die_rst_n), .sys_ready(sys_ready), .boot_fault(boot_fault), .boot_state(boot_state),
        .boot_err(boot_err), .boot_cycles(boot_cycles));

    // ---------------------------------------------------------------- host interface
    wire h_awvalid, h_awready, h_wvalid, h_wready, h_bvalid, h_bready, h_arvalid, h_arready, h_rvalid, h_rready;
    wire [11:0] h_awaddr, h_araddr;
    wire [31:0] h_wdata, h_rdata;
    wire [3:0]  h_wstrb;
    wire        hi_irq;
    wire pb_we, pb_re; wire [SB+PLB-1:0] pb_waddr, pb_raddr; wire [NW-1:0] pb_wdata; reg [NW-1:0] pb_q;
    reg  [NW-1:0] pbuf [0:NSLOT*(1<<PLB)-1];
    always @(posedge clk) begin
        if (pb_we) pbuf[pb_waddr] <= pb_wdata;
        if (pb_re) pb_q <= pbuf[pb_raddr];
    end
    wire eng_start, eng_done, eng_fault;
    wire [NW-1:0] eng_token, eng_pos, eng_next_token;
    wire [SB-1:0] eng_slot;
    wire [AW-1:0] kv_base;
    wire [31:0] eng_cycles, eng_next_val;
    ot_host_if #(.NSLOT(NSLOT), .MODE(0), .ENG_CTX(NSLOT), .NW(NW), .PLB(PLB), .CTX_MAX(64), .AW(AW),
                 .KVW(KVW)) u_host (
        .clk(clk), .rst_n(host_rst_n),
        .s_awvalid(h_awvalid), .s_awready(h_awready), .s_awaddr(h_awaddr),
        .s_wvalid(h_wvalid), .s_wready(h_wready), .s_wdata(h_wdata), .s_wstrb(h_wstrb),
        .s_bvalid(h_bvalid), .s_bready(h_bready), .s_bresp(),
        .s_arvalid(h_arvalid), .s_arready(h_arready), .s_araddr(h_araddr),
        .s_rvalid(h_rvalid), .s_rready(h_rready), .s_rdata(h_rdata), .s_rresp(),
        .m_arvalid(m_arvalid), .m_arready(m_arready), .m_araddr(m_araddr), .m_arlen(m_arlen), .m_arsize(m_arsize),
        .m_rvalid(m_rvalid), .m_rready(m_rready), .m_rdata(m_rdata), .m_rresp(m_rresp), .m_rlast(m_rlast),
        .m_awvalid(m_awvalid), .m_awready(m_awready), .m_awaddr(m_awaddr), .m_awlen(m_awlen), .m_awsize(m_awsize),
        .m_wvalid(m_wvalid), .m_wready(m_wready), .m_wdata(m_wdata), .m_wstrb(m_wstrb), .m_wlast(m_wlast),
        .m_bvalid(m_bvalid), .m_bready(m_bready), .m_bresp(m_bresp),
        .irq(hi_irq),
        .pb_we(pb_we), .pb_waddr(pb_waddr), .pb_wdata(pb_wdata), .pb_re(pb_re), .pb_raddr(pb_raddr), .pb_q(pb_q),
        .eng_start(eng_start), .eng_token(eng_token), .eng_pos(eng_pos), .eng_slot(eng_slot), .kv_base(kv_base),
        .eng_done(eng_done), .eng_next_token(eng_next_token), .eng_cycles(eng_cycles), .eng_fault(eng_fault),
        .eng_clr_req(), .eng_clr_ack(1'b0),
        .arr_rst_n(), .cfg_users(), .cfg_prompt_len(), .cfg_gen_len(),
        .pr_re(1'b0), .pr_user(8'd0), .pr_pos({NW{1'b0}}),
        .tok_valid(1'b0), .tok_user(8'd0), .tok_pos({NW{1'b0}}), .tok_id({NW{1'b0}}), .users_done(8'd0),
        .arr_fault(1'b0));

    // ---------------------------------------------------------------- package controller
    wire d_start;
    wire [NW-1:0] d_token, d_pos;
    wire [AW-1:0] d_kv_base;
    wire [N-1:0] d_done, d_drained;
    wire [N*NW-1:0] d_ntok;
    wire [N*32-1:0] d_nval;
    wire [N*5-1:0] d_fv;
    wire [N-1:0] d_fault;
    wire disagree, wdog_fault, start_unready;
    wire [31:0] n_steps;
    genvar d, t;
    generate for (d = 0; d < N; d = d + 1) begin : g_df
        assign d_fault[d] = |d_fv[5*d +: 5];
    end endgenerate
    ot_qwen_sys_pkg_ctl #(.D(N), .NW(NW), .AW(AW)) u_pkg (
        .clk(clk), .rst_n(host_rst_n), .ready(sys_ready),
        .eng_start(eng_start), .eng_token(eng_token), .eng_pos(eng_pos), .eng_kv_base(kv_base),
        .eng_done(eng_done), .eng_next_token(eng_next_token), .eng_next_val(eng_next_val),
        .eng_cycles(eng_cycles), .eng_fault(eng_fault),
        .d_start(d_start), .d_token(d_token), .d_pos(d_pos), .d_kv_base(d_kv_base),
        .d_done(d_done), .d_next_token(d_ntok), .d_next_val(d_nval), .d_drained(d_drained), .d_fault(d_fault),
        .disagree(disagree), .wdog_fault(wdog_fault), .start_unready(start_unready), .n_steps(n_steps));
    assign die_done = d_done; assign die_token = d_ntok; assign die_val = d_nval;
    assign step_start = d_start; assign step_pos = d_pos;

    // ---------------------------------------------------------------- dies
    wire [N*8*32-1:0] d_stats;
    generate for (d = 0; d < N; d = d + 1) begin : g_die
        wire [N*LFW-1:0] tx, rx;
        wire [N-1:0] rxv;
        for (t = 0; t < N; t = t + 1) begin : g_ph
            assign ph_tx[(d*N + t)*LFW +: LFW] = tx[t*LFW +: LFW];
            assign rx[t*LFW +: LFW] = ph_rx[(d*N + t)*LFW +: LFW];
            assign rxv[t] = ph_rx_v[d*N + t];
        end
        ot_qwen_sys_die #(.N(N), .RANK(d), .G(G), .NW(NW), .TAG_FULL(TAG_FULL), .TAGW(TAGW),
                          .WROM_WORDS(WROM_WORDS), .KVWORDS(KVW), .NPC(NPC), .HTAGW(HTAGW), .LINK_TMO(LINK_TMO),
                          .BOOT_SECTOR(24'(NSLOT * KVW * 2)), .SCRUB_SECTORS(NSLOT * KVW * 2), .ME_CDC(ME_CDC), .KV_PREFETCH(KV_PREFETCH)) u_die (
            .clk(clk), .fclk(fclk), .link_rst_n(link_rst_n), .hbm_rst_n(hbm_rst_n), .rst_n(die_rst_n),
            .start(d_start), .token(d_token), .pos(d_pos), .kv_base(d_kv_base[22:0]),
            .done(d_done[d]), .next_token(d_ntok[d*NW +: NW]), .next_val(d_nval[d*32 +: 32]), .drained(d_drained[d]),
            .ph_tx(tx), .ph_rx_v(rxv), .ph_rx(rx), .link_up(lup[d*N +: N]),
            .h_req_v(h_req_v[d]), .h_req_rdy(h_req_rdy[d]), .h_req_we(h_req_we[d]),
            .h_req_addr(h_req_addr[d*24 +: 24]), .h_req_len(h_req_len[d*5 +: 5]),
            .h_req_tag(h_req_tag[d*HTAGW +: HTAGW]), .h_req_wdata(h_req_wdata[d*256 +: 256]),
            .h_rsp_v(h_rsp_v[d*NPC +: NPC]), .h_rsp_rdy(h_rsp_rdy[d*NPC +: NPC]),
            .h_rsp_tag(h_rsp_tag[d*NPC*HTAGW +: NPC*HTAGW]), .h_rsp_beat(h_rsp_beat[d*NPC*4 +: NPC*4]),
            .h_rsp_data(h_rsp_data[d*NPC*256 +: NPC*256]), .h_rsp_wr(h_rsp_wr[d*NPC +: NPC]),
            .boot_go(boot_go), .boot_done(boot_done[d]), .boot_ok(boot_ok[d]),
            .fault_vec(d_fv[5*d +: 5]), .stats(d_stats[d*256 +: 256]));
    end endgenerate

    // ---------------------------------------------------------------- CSRs, faults, interrupt
    assign fault_src = {8'd0, boot_fault, start_unready, wdog_fault, disagree, d_fv[19:0]};
    reg [16*32-1:0] cnt;
    integer i;
    always @(*) begin
        cnt = 0;
        for (i = 0; i < N; i = i + 1) begin
            cnt[32*i +: 32]       = d_stats[i*256 + 7*32 +: 32];   // KV fill words
            cnt[32*(4 + i) +: 32] = d_stats[i*256 + 6*32 +: 32];   // KV write-back sectors
            cnt[32*8 +: 32]  = cnt[32*8 +: 32]  + d_stats[i*256 + 4*32 +: 32];   // link CRC errors
            cnt[32*9 +: 32]  = cnt[32*9 +: 32]  + d_stats[i*256 + 3*32 +: 32];   // link replays
            cnt[32*10 +: 32] = cnt[32*10 +: 32] + d_stats[i*256 + 2*32 +: 32];   // link sequence drops
        end
        cnt[32*11 +: 32] = boot_cycles;
        cnt[32*12 +: 32] = n_steps;
        cnt[32*13 +: 32] = d_stats[1*32 +: 32];                  // die 0 collective cycles
        cnt[32*14 +: 32] = d_stats[0 +: 32];                     // die 0 busy cycles
        cnt[32*15 +: 32] = d_stats[5*32 +: 32];                  // die 0 kv_ok wait cycles
    end
    ot_qwen_sys_csr #(.NCNT(16)) u_csr (
        .clk(clk), .rst_n(host_rst_n),
        .s_awvalid(s_awvalid), .s_awready(s_awready), .s_awaddr(s_awaddr),
        .s_wvalid(s_wvalid), .s_wready(s_wready), .s_wdata(s_wdata), .s_wstrb(s_wstrb),
        .s_bvalid(s_bvalid), .s_bready(s_bready), .s_bresp(s_bresp),
        .s_arvalid(s_arvalid), .s_arready(s_arready), .s_araddr(s_araddr),
        .s_rvalid(s_rvalid), .s_rready(s_rready), .s_rdata(s_rdata), .s_rresp(s_rresp),
        .h_awvalid(h_awvalid), .h_awready(h_awready), .h_awaddr(h_awaddr),
        .h_wvalid(h_wvalid), .h_wready(h_wready), .h_wdata(h_wdata), .h_wstrb(h_wstrb),
        .h_bvalid(h_bvalid), .h_bready(h_bready),
        .h_arvalid(h_arvalid), .h_arready(h_arready), .h_araddr(h_araddr),
        .h_rvalid(h_rvalid), .h_rready(h_rready), .h_rdata(h_rdata), .h_irq(hi_irq),
        .sys_ready(sys_ready), .boot_fault(boot_fault), .boot_state(boot_state), .boot_err(boot_err),
        .soft_rst(soft_rst), .fault_src(fault_src), .cnt(cnt), .irq(irq));
endmodule
