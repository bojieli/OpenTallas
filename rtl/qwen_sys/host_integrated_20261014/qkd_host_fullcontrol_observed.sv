`timescale 1ns/1ps
// TP8 full host-control composition. Prompt storage is an external physical leaf.
// All clock ports are synchronous 833ps roots delivered at their contract phase.
module qkd_host_fullcontrol_observed #(
    parameter integer PROMPT_VALID_ONLY = 1, // mutant switch; gate unwritten prompt reads
    parameter integer MUT_DIAG = 0,
    parameter integer MUT_DONE_GUARD = 0,
    parameter integer MUT_FMT = 0,
    parameter integer PROMPT_READ_LATENCY = 1, // external SRAM response edges after request pin // opt-in until exact/physical gates pass
    parameter integer D       = 8,
    parameter integer NW      = 18,
    parameter integer AW      = 24,
    parameter integer NSLOT   = 1,
    parameter integer PLB     = 13,
    parameter integer CTX     = 8192,
    parameter integer KVW     = 1024,
    parameter integer NL      = 6,          // link ends the reset sequencer waits for
    parameter integer T_LINK  = 200000,
    parameter integer T_HBM   = 200000,
    parameter integer ENABLE_SERVICE=0,
    parameter integer WDOG    = 1 << 22
) (
    input wire ck_host, ck_csr, ck_rst, ck_ctl,
    input wire [2:0] die_id,
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
    input wire [7:0] transport_fault, physical_fault,
    input  wire               crom_fault,
    output wire [31:0]        fault_src,
    output wire pb_we, pb_re,
    output wire [13:0] pb_waddr,pb_raddr,
    output wire [17:0] pb_wdata,
    input wire [17:0] pb_q,
    input wire pb_fault,
    input wire [142:0] pr,
    input wire [743:0] tk8,
    input wire [79:0] kst8,
    output wire [181:0] hc,
 input wire service_abort,service_ready,input wire[7:0]service_ready8,
 input wire[25:0]service_diag_raw,input wire[31:0]service_status,
input wire  begin_tx_cr,
input wire  begin_tx_available,
input wire [7:0] pending_ack8,
input wire [127:0] service_epoch8,
input wire  service_fault,
input wire  ingest_permission,
output wire  begin_v,
output wire [15:0] begin_epoch,
output wire  begin_available,
output wire  begin_fault,
 output wire epoch_busy,startup_allowed,
 output wire package_abort,
 output wire cq_commit_v,output wire[15:0]cq_client_tag,output wire[7:0]cq_slot,
 output wire[17:0]cq_pos,cq_token,output wire[1:0]cq_kind,output wire[3:0]cq_status,
 output wire step_issue_v,output wire[15:0]step_client_tag,output wire[7:0]step_slot,output wire[17:0]step_pos,
 output wire step_retire_v,step_retire_cq,output wire[15:0]step_retire_client_tag,output wire[7:0]step_retire_slot,output wire[17:0]step_retire_pos,step_retire_token,
 output wire host_idle,host_observer_fault,
 input wire peer_reset_request
);
    wire [31:0] c_fault_vec;
    for(genvar d=0;d<8;d=d+1) begin:g_diag
        // Four independent summaries; detailed KV cause9 remains raw in CSR1090.
        assign c_fault_vec[d*4+:4]={physical_fault[d],transport_fault[d],kst8[d*10+9],tk8[d*93+88]};
    end
    localparam integer SB = (NSLOT > 1) ? $clog2(NSLOT) : 1;
    // ---- reset / power-up ----
    wire boot_fault, soft_rst;
 reg recovery_reset_q;
 always @(posedge ck_rst or negedge por_n)if(!por_n)recovery_reset_q<=0;else recovery_reset_q<=peer_reset_request;
 wire recovery_soft_pulse=peer_reset_request&&!recovery_reset_q;
    wire [3:0] boot_state, boot_err;
    wire [31:0] boot_cycles;
    qkd_host_rst_role_pins #(.NL(NL), .ND(D), .T_LINK(T_LINK), .T_HBM(T_HBM)) u_rst (
        .clk(ck_rst), .die_id(die_id), .por_n(por_n), .soft_rst(soft_rst||recovery_soft_pulse), .link_up(link_up), .boot_done(boot_done), .boot_ok(boot_ok),
        .host_rst_n(host_rst_n), .link_rst_n(link_rst_n), .hbm_rst_n(hbm_rst_n), .boot_go(boot_go),
        .die_rst_n(die_rst_n), .sys_ready(sys_ready), .boot_fault(boot_fault), .boot_state(boot_state),
        .boot_err(boot_err), .boot_cycles(boot_cycles));
    // ---- host interface + prompt buffer ----
    wire h_awvalid, h_awready, h_wvalid, h_wready, h_bvalid, h_bready, h_arvalid, h_arready, h_rvalid, h_rready;
    wire [11:0] h_awaddr, h_araddr;
    wire [31:0] h_wdata, h_rdata;
    wire [3:0]  h_wstrb;
    wire        hi_irq;
    wire eng_start, eng_done, eng_fault;
    wire [NW-1:0] eng_token, eng_pos, eng_next_token;
    wire [SB-1:0] eng_slot;
    wire [AW-1:0] kv_base;
    wire [31:0] eng_cycles, eng_next_val;
    // user-state clear (ENG_CTX = NSLOT = 1): nothing to clear -- a step at position p reads KV positions 0..p only,
    // every one rewritten by the current request (prompt steps or ingest) before it is read; acknowledged next edge
    wire clr_req;
    wire clr_ack=1'b0; // acknowledgement now owned by host hardened leaf
    qkd_host_if_pins_observed #(.PB_READ_PIPE(1+PROMPT_READ_LATENCY),.MUT_DONE_GUARD(MUT_DONE_GUARD),.PB_VALID_ONLY(PROMPT_VALID_ONLY), .NSLOT(NSLOT), .MODE(0), .ENG_CTX(NSLOT), .NW(NW), .PLB(PLB), .CTX_MAX(CTX), .AW(AW),
                 .KVW(KVW), .FMT(MUT_FMT?0:1)) u_host (.cq_commit_v(cq_commit_v),.cq_client_tag(cq_client_tag),.cq_slot(cq_slot),.cq_pos(cq_pos),.cq_token(cq_token),.cq_kind(cq_kind),.cq_status(cq_status),.step_issue_v(step_issue_v),.step_client_tag(step_client_tag),.step_slot(step_slot),.step_pos(step_pos),.host_idle(host_idle),.host_observer_fault(host_observer_fault),.step_retire_v(step_retire_v),.step_retire_cq(step_retire_cq),.step_retire_client_tag(step_retire_client_tag),.step_retire_slot(step_retire_slot),.step_retire_pos(step_retire_pos),.step_retire_token(step_retire_token),
        .clk(ck_host), .rst_n(host_rst_n), .die_id(die_id),
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
    wire [119:0] ctl_res;
    qkd_host_ctl_service_pins #(.WDOG(WDOG),.ENABLE_SERVICE(ENABLE_SERVICE)) u_pkg(
        .ck(ck_ctl),.rst_n(host_rst_n),.sys_ready(sys_ready),.pb_fault(pb_fault),.die_id(die_id),
        .service_abort(service_abort),.service_ready(service_ready),.service_ready8(service_ready8),.begin_block(epoch_busy),.epoch_fault(begin_fault),
        .req({kv_base,eng_pos,eng_token,eng_start}),.pr(pr),.tk(tk8),.hc(hc),.res(ctl_res));
    assign package_abort=eng_fault;
    assign eng_done=ctl_res[0]; assign eng_fault=ctl_res[1];
    assign eng_next_token=ctl_res[19:2];assign eng_next_val=ctl_res[51:20];
    assign eng_cycles=ctl_res[83:52];assign disagree=ctl_res[84];
    assign wdog_fault=ctl_res[85];assign start_unready=ctl_res[86];
    assign die_fault=ctl_res[87];assign n_steps=ctl_res[119:88];
    assign c_start=hc[38];assign c_gen=hc[37:36];
    assign c_token=hc[35:18];assign c_pos=hc[17:0];assign c_kv_base=kv_base;
    initial if (PROMPT_READ_LATENCY<1 || D!=8 || NW!=18 || AW!=24 || NSLOT!=1 || PLB!=13 || CTX!=8192)
        $fatal(1,"full-control physical shape mismatch");
    // ---- CSRs, faults, interrupt ----
    assign fault_src = {9'd0, pb_fault, crom_fault, die_fault, boot_fault, start_unready, wdog_fault, disagree,
                        16'(c_fault_vec)};
    reg [16*32-1:0] cnt;
    always @(*) begin
        cnt = 0;
        cnt[32*11 +: 32] = boot_cycles;
        cnt[32*12 +: 32] = n_steps;
        cnt[32*13 +: 32] = eng_cycles;
        cnt[32*14 +: 32] = {6'b0,service_diag_raw};
        cnt[32*15 +: 32] = service_status;
    end
    qkd_host_csr_service_pins #(.NCNT(16),.MUT_DIAG(MUT_DIAG),.ENABLE_SERVICE(ENABLE_SERVICE)) u_csr (
        .decode_request(eng_start),.decode_start(hc[38]),.decode_done(eng_done),.epoch_busy(epoch_busy),.startup_allowed(startup_allowed),
        .clk(ck_csr), .rst_n(host_rst_n),.por_n(por_n),.service_ready8(service_ready8),
.begin_tx_cr(begin_tx_cr),.begin_tx_available(begin_tx_available),.pending_ack8(pending_ack8),.service_epoch8(service_epoch8),.service_fault(service_fault),.ingest_permission(ingest_permission),.begin_v(begin_v),.begin_epoch(begin_epoch),.begin_available(begin_available),.begin_fault(begin_fault),
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
        .soft_rst(soft_rst), .fault_src(fault_src), .die_fault_vec(c_fault_vec),.die_kst(kst8), .cnt(cnt), .irq(irq));
endmodule
