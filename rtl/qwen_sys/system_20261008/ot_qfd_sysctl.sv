`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// Die master qfd_sysctl (stream qwen-system, 2026-10-08): the full-shape CONTROL PLANE of the Qwen3-8B ROM package, on
// die 0 of the TP4 group.  The reduced-vehicle blocks of results/rtl/qwen_rom_system_rtl_20261003 at full shape:
//   ot_host_if (FMT 1: 18-bit tokens, positions to CTX = 8,192, one user slot: the full-shape KV map holds one user)
//   ot_qwen_sys_csr (AXI4-Lite split, SYS_STATUS, 32 sticky fault sources, FAULT_FIRST, mask, IRQ, counters)
//   ot_qwen_sys_rst_seq (POR -> links trained -> HBM round trip -> dies -> ready; soft reset)
//   ot_qfd_pkgctl (start fan-out with a step generation, done = all dies done for that generation and drained,
//                  token / logit agreement, step watchdog, fail closed)
//   the prompt buffer (NSLOT x 2^PLB x NW; 8,192 x 18 b at full shape: one ot_sram_1r1w macro set, behavioural here)
// The token loop (fed-back token, position + 1, the prompt phase) and the stop condition (EOS ids, max new tokens,
// context limit) are ot_host_if's.  The per-die 38-stage loop is ot_qfd_dctl on every die.
// Ports: the host side is the AXI4-Lite register slave + AXI4 DMA master the host link endpoint (qfd_io_host, HOST class
// on the board SerDes) terminates; the die side is the package control channel (CTRL class): start {token, pos,
// kv_base, gen} out, per-die {done, gen, token, logit, drained, fault} in.  Every port leaves / enters at a flop of the
// sub-blocks (host_if / csr / pkgctl register their outputs); the CTRL-class link adds the relay / PHY latency outside.
// Fault sources (FAULT_STATUS): [4d +: 4] die d {stage-stepper fault, sequencer, KV / memory, link}; [16] dies disagree,
// [17] step watchdog, [18] start before ready, [19] boot fault, [20] die step fault (pkgctl), [21] constant ROM.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qfd_sysctl #(
    parameter integer D       = 4,
    parameter integer NW      = 18,
    parameter integer AW      = 24,
    parameter integer NSLOT   = 1,
    parameter integer PLB     = 13,
    parameter integer CTX     = 8192,
    parameter integer KVW     = 1024,
    parameter integer NL      = 6,          // link ends the reset sequencer waits for
    parameter integer T_LINK  = 200000,
    parameter integer T_HBM   = 200000,
    parameter integer WDOG    = 1 << 22
) (
    input  wire               clk,
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
    // AXI4 DMA master to host memory
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
    // reset / boot
    input  wire [NL-1:0]      link_up,
    input  wire [D-1:0]       boot_done,
    input  wire [D-1:0]       boot_ok,
    output wire               host_rst_n,
    output wire               link_rst_n,
    output wire               hbm_rst_n,
    output wire               boot_go,
    output wire               die_rst_n,
    output wire               sys_ready,
    // package control channel
    output wire               c_start,
    output wire [NW-1:0]      c_token,
    output wire [NW-1:0]      c_pos,
    output wire [AW-1:0]      c_kv_base,
    output wire [1:0]         c_gen,
    input  wire [D-1:0]       c_done,
    input  wire [D*2-1:0]     c_done_gen,
    input  wire [D*NW-1:0]    c_next_token,
    input  wire [D*32-1:0]    c_next_val,
    input  wire [D-1:0]       c_drained,
    input  wire [D-1:0]       c_fault,
    input  wire [D*4-1:0]     c_fault_vec,  // per die: {link, KV / memory, sequencer, stage stepper}
    input  wire               crom_fault,
    output wire [31:0]        fault_src
);
    localparam integer SB = (NSLOT > 1) ? $clog2(NSLOT) : 1;
    // ---- reset / power-up ----
    wire boot_fault, soft_rst;
    wire [3:0] boot_state, boot_err;
    wire [31:0] boot_cycles;
    ot_qwen_sys_rst_seq #(.NL(NL), .ND(D), .T_LINK(T_LINK), .T_HBM(T_HBM)) u_rst (
        .clk(clk), .por_n(por_n), .soft_rst(soft_rst), .link_up(link_up), .boot_done(boot_done), .boot_ok(boot_ok),
        .host_rst_n(host_rst_n), .link_rst_n(link_rst_n), .hbm_rst_n(hbm_rst_n), .boot_go(boot_go),
        .die_rst_n(die_rst_n), .sys_ready(sys_ready), .boot_fault(boot_fault), .boot_state(boot_state),
        .boot_err(boot_err), .boot_cycles(boot_cycles));
    // ---- host interface + prompt buffer ----
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
    // user-state clear (ENG_CTX = NSLOT = 1): nothing to clear -- a step at position p reads KV positions 0..p only,
    // every one rewritten by the current request (prompt steps or ingest) before it is read; acknowledged next edge
    wire clr_req;
    reg  clr_ack;
    always @(posedge clk or negedge host_rst_n) if (!host_rst_n) clr_ack <= 1'b0; else clr_ack <= clr_req && !clr_ack;
    ot_host_if #(.NSLOT(NSLOT), .MODE(0), .ENG_CTX(NSLOT), .NW(NW), .PLB(PLB), .CTX_MAX(CTX), .AW(AW),
                 .KVW(KVW), .FMT(1)) u_host (
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
        .eng_clr_req(clr_req), .eng_clr_ack(clr_ack),
        .arr_rst_n(), .cfg_users(), .cfg_prompt_len(), .cfg_gen_len(),
        .pr_re(1'b0), .pr_user(8'd0), .pr_pos({NW{1'b0}}),
        .tok_valid(1'b0), .tok_user(8'd0), .tok_pos({NW{1'b0}}), .tok_id({NW{1'b0}}), .users_done(8'd0),
        .arr_fault(1'b0));
    // ---- package controller ----
    wire disagree, wdog_fault, start_unready, die_fault;
    wire [31:0] n_steps;
    ot_qfd_pkgctl #(.D(D), .NW(NW), .AW(AW), .WDOG(WDOG)) u_pkg (
        .clk(clk), .rst_n(host_rst_n), .ready(sys_ready),
        .eng_start(eng_start), .eng_token(eng_token), .eng_pos(eng_pos), .eng_kv_base(kv_base),
        .eng_done(eng_done), .eng_next_token(eng_next_token), .eng_next_val(eng_next_val),
        .eng_cycles(eng_cycles), .eng_fault(eng_fault),
        .d_start(c_start), .d_token(c_token), .d_pos(c_pos), .d_kv_base(c_kv_base), .d_gen(c_gen),
        .d_done(c_done), .d_done_gen(c_done_gen), .d_next_token(c_next_token), .d_next_val(c_next_val),
        .d_drained(c_drained), .d_fault(c_fault),
        .disagree(disagree), .wdog_fault(wdog_fault), .start_unready(start_unready), .die_fault(die_fault),
        .n_steps(n_steps));
    // ---- CSRs, faults, interrupt ----
    assign fault_src = {10'd0, crom_fault, die_fault, boot_fault, start_unready, wdog_fault, disagree,
                        16'(c_fault_vec)};
    reg [16*32-1:0] cnt;
    always @(*) begin
        cnt = 0;
        cnt[32*11 +: 32] = boot_cycles;
        cnt[32*12 +: 32] = n_steps;
        cnt[32*13 +: 32] = eng_cycles;
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
