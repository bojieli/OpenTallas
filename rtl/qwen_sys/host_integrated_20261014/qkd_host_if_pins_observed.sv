`timescale 1ns/1ps
// Registered physical pin seam around original production logic.
module qkd_host_if_pins_observed #(

    parameter integer PB_READ_PIPE = 2,
    parameter integer MUT_DONE_GUARD=0,
    parameter integer PB_VALID_ONLY = 0, // gate unused MODE0 prompt reads for protected SRAM
    parameter integer NSLOT   = 16,     // user contexts
    parameter integer MODE    = 0,      // 0 step (one core), 1 batch (ROM array SOURCE package)
    parameter integer ENG_CTX = 16,     // contexts the engine holds at once (1: clear between users)
    parameter integer NW      = 16,     // token / position bits
    parameter integer PLB     = 8,      // log2 prompt-buffer entries per slot
    parameter integer CTX_MAX = 64,     // KV positions per user (prompt + generated - 1 <= CTX_MAX)
    parameter integer AW      = 24,     // KV address bits
    parameter integer KVW     = 1024,   // KV words per user
    parameter integer EVQ     = 4,      // log2 completion-event queue depth
    // FMT 1 (stream qwen-system 2026-10-08, the full-shape Qwen3-8B vocabulary needs NW = 18): 32-bit token fields.
    //   descriptor w0 [47:32] prompt length / [63:48] max new tokens (16 b each); prompt tokens two per word
    //   ([31:0], [63:32]); w3 [31:0] EOS id 0, [63:32] EOS id 1.  Completion w0 [47:32] position[15:0],
    //   [63:48] token[15:0]; w1 [47:32] tokens generated[15:0], [63:48] token[31:16].  FMT 0: the layout above.
    parameter integer FMT     = 0
) (
    input  wire               clk,
    input  wire               rst_n,
    input wire [2:0] die_id,
    // AXI4-Lite slave: the register BAR
    input  wire               s_awvalid,
    output wire               s_awready,
    input  wire [11:0]        s_awaddr,
    input  wire               s_wvalid,
    output wire               s_wready,
    input  wire [31:0]        s_wdata,
    input  wire [3:0]         s_wstrb,
    output wire                s_bvalid,
    input  wire               s_bready,
    output wire [1:0]         s_bresp,
    input  wire               s_arvalid,
    output wire               s_arready,
    input  wire [11:0]        s_araddr,
    output wire                s_rvalid,
    input  wire               s_rready,
    output wire  [31:0]        s_rdata,
    output wire [1:0]         s_rresp,
    // AXI4 master: DMA to host memory, single 64-bit beats
    output wire                m_arvalid,
    input  wire               m_arready,
    output wire  [63:0]        m_araddr,
    output wire [7:0]         m_arlen,
    output wire [2:0]         m_arsize,
    input  wire               m_rvalid,
    output wire               m_rready,
    input  wire [63:0]        m_rdata,
    input  wire [1:0]         m_rresp,
    input  wire               m_rlast,
    output wire                m_awvalid,
    input  wire               m_awready,
    output wire  [63:0]        m_awaddr,
    output wire [7:0]         m_awlen,
    output wire [2:0]         m_awsize,
    output wire                m_wvalid,
    input  wire               m_wready,
    output wire  [63:0]        m_wdata,
    output wire  [7:0]         m_wstrb,
    output wire               m_wlast,
    input  wire               m_bvalid,
    output wire               m_bready,
    input  wire [1:0]         m_bresp,
    // interrupt, level (INTx model)
    output wire               irq,
    // prompt buffer: external 1R1W SRAM, synchronous read, address {slot, position}
    output wire                pb_we,
    output wire  [SB+PLB-1:0]  pb_waddr,
    output wire  [NW-1:0]      pb_wdata,
    output wire                pb_re,
    output wire  [SB+PLB-1:0]  pb_raddr,
    input  wire [NW-1:0]      pb_q,
    // MODE 0: one decode core
    output wire                eng_start,
    output wire  [NW-1:0]      eng_token,
    output wire  [NW-1:0]      eng_pos,
    output wire  [SB-1:0]      eng_slot,
    output wire  [AW-1:0]      kv_base,
    input  wire               eng_done,
    input  wire [NW-1:0]      eng_next_token,
    input  wire [31:0]        eng_cycles,
    input  wire               eng_fault,
    output wire                eng_clr_req,     // clear the engine's user state (ENG_CTX == 1)
    input  wire               eng_clr_ack,
    // MODE 1: SOURCE package of a ROM array (ot_rom_pkg_ctrl)
    output wire                arr_rst_n,
    output wire  [7:0]         cfg_users,
    output wire  [NW-1:0]      cfg_prompt_len,
    output wire  [NW-1:0]      cfg_gen_len,
    input  wire               pr_re,
    input  wire [7:0]         pr_user,
    input  wire [NW-1:0]      pr_pos,
    input  wire               tok_valid,
    input  wire [7:0]         tok_user,
    input  wire [NW-1:0]      tok_pos,
    input  wire [NW-1:0]      tok_id,
    input  wire [7:0]         users_done,
    input  wire               arr_fault,
 output wire cq_commit_v,output wire[15:0]cq_client_tag,output wire[7:0]cq_slot,
 output wire[17:0]cq_pos,cq_token,output wire[1:0]cq_kind,output wire[3:0]cq_status,
 output wire step_issue_v,output wire[15:0]step_client_tag,output wire[7:0]step_slot,output wire[17:0]step_pos,
 output wire step_retire_v,step_retire_cq,output wire[15:0]step_retire_client_tag,output wire[7:0]step_retire_slot,output wire[17:0]step_retire_pos,step_retire_token,
 output wire host_idle,host_observer_fault
);
initial if(MODE!=0 || NSLOT!=1 || ENG_CTX!=1 || NW!=18 || PLB!=13 || CTX_MAX!=8192)
 $fatal(1,"host pin leaf shape mismatch");
localparam integer SB=(NSLOT>1)?$clog2(NSLOT):1;
wire  clk_i;
wire  rst_n_i;
wire  s_awvalid_i;
wire  s_awready_i;
wire [11:0] s_awaddr_i;
wire  s_wvalid_i;
wire  s_wready_i;
wire [31:0] s_wdata_i;
wire [3:0] s_wstrb_i;
wire  s_bvalid_i;
wire  s_bready_i;
wire [1:0] s_bresp_i;
wire  s_arvalid_i;
wire  s_arready_i;
wire [11:0] s_araddr_i;
wire  s_rvalid_i;
wire  s_rready_i;
wire [31:0] s_rdata_i;
wire [1:0] s_rresp_i;
wire  m_arvalid_i;
wire  m_arready_i;
wire [63:0] m_araddr_i;
wire [7:0] m_arlen_i;
wire [2:0] m_arsize_i;
wire  m_rvalid_i;
wire  m_rready_i;
wire [63:0] m_rdata_i;
wire [1:0] m_rresp_i;
wire  m_rlast_i;
wire  m_awvalid_i;
wire  m_awready_i;
wire [63:0] m_awaddr_i;
wire [7:0] m_awlen_i;
wire [2:0] m_awsize_i;
wire  m_wvalid_i;
wire  m_wready_i;
wire [63:0] m_wdata_i;
wire [7:0] m_wstrb_i;
wire  m_wlast_i;
wire  m_bvalid_i;
wire  m_bready_i;
wire [1:0] m_bresp_i;
wire  irq_i;
wire  pb_we_i;
wire [SB+PLB-1:0] pb_waddr_i;
wire [NW-1:0] pb_wdata_i;
wire  pb_re_i;
wire [SB+PLB-1:0] pb_raddr_i;
wire [NW-1:0] pb_q_i;
wire  eng_start_i;
wire [NW-1:0] eng_token_i;
wire [NW-1:0] eng_pos_i;
wire [SB-1:0] eng_slot_i;
wire [AW-1:0] kv_base_i;
wire  eng_done_i;
wire [NW-1:0] eng_next_token_i;
wire [31:0] eng_cycles_i;
wire  eng_fault_i;
wire  eng_clr_req_i;
wire  eng_clr_ack_i;
wire  arr_rst_n_i;
wire [7:0] cfg_users_i;
wire [NW-1:0] cfg_prompt_len_i;
wire [NW-1:0] cfg_gen_len_i;
wire  pr_re_i;
wire [7:0] pr_user_i;
wire [NW-1:0] pr_pos_i;
wire  tok_valid_i;
wire [7:0] tok_user_i;
wire [NW-1:0] tok_pos_i;
wire [NW-1:0] tok_id_i;
wire [7:0] users_done_i;
wire  arr_fault_i;
qkd_host_pin_channel #(.W((11-0+1)),.IN_PIN(1),.OUT_PIN(0)) st_s_awvalid(
 .ck(clk),.rst_n(rst_n),.in_v(s_awvalid),.in_d({s_awaddr}),
 .in_r(s_awready),.out_v(s_awvalid_i),.out_d({s_awaddr_i}),.out_r(s_awready_i));
qkd_host_pin_channel #(.W((31-0+1)+(3-0+1)),.IN_PIN(1),.OUT_PIN(0)) st_s_wvalid(
 .ck(clk),.rst_n(rst_n),.in_v(s_wvalid),.in_d({s_wdata,s_wstrb}),
 .in_r(s_wready),.out_v(s_wvalid_i),.out_d({s_wdata_i,s_wstrb_i}),.out_r(s_wready_i));
qkd_host_pin_channel #(.W((1-0+1)),.IN_PIN(0),.OUT_PIN(1)) st_s_bvalid(
 .ck(clk),.rst_n(rst_n),.in_v(s_bvalid_i),.in_d({s_bresp_i}),
 .in_r(s_bready_i),.out_v(s_bvalid),.out_d({s_bresp}),.out_r(s_bready));
qkd_host_pin_channel #(.W((11-0+1)),.IN_PIN(1),.OUT_PIN(0)) st_s_arvalid(
 .ck(clk),.rst_n(rst_n),.in_v(s_arvalid),.in_d({s_araddr}),
 .in_r(s_arready),.out_v(s_arvalid_i),.out_d({s_araddr_i}),.out_r(s_arready_i));
qkd_host_pin_channel #(.W((31-0+1)+(1-0+1)),.IN_PIN(0),.OUT_PIN(1)) st_s_rvalid(
 .ck(clk),.rst_n(rst_n),.in_v(s_rvalid_i),.in_d({s_rdata_i,s_rresp_i}),
 .in_r(s_rready_i),.out_v(s_rvalid),.out_d({s_rdata,s_rresp}),.out_r(s_rready));
qkd_host_pin_channel #(.W((63-0+1)+(7-0+1)+(2-0+1)),.IN_PIN(0),.OUT_PIN(1)) st_m_arvalid(
 .ck(clk),.rst_n(rst_n),.in_v(m_arvalid_i),.in_d({m_araddr_i,m_arlen_i,m_arsize_i}),
 .in_r(m_arready_i),.out_v(m_arvalid),.out_d({m_araddr,m_arlen,m_arsize}),.out_r(m_arready));
qkd_host_pin_channel #(.W((63-0+1)+(1-0+1)+1),.IN_PIN(1),.OUT_PIN(0)) st_m_rvalid(
 .ck(clk),.rst_n(rst_n),.in_v(m_rvalid),.in_d({m_rdata,m_rresp,m_rlast}),
 .in_r(m_rready),.out_v(m_rvalid_i),.out_d({m_rdata_i,m_rresp_i,m_rlast_i}),.out_r(m_rready_i));
qkd_host_pin_channel #(.W((63-0+1)+(7-0+1)+(2-0+1)),.IN_PIN(0),.OUT_PIN(1)) st_m_awvalid(
 .ck(clk),.rst_n(rst_n),.in_v(m_awvalid_i),.in_d({m_awaddr_i,m_awlen_i,m_awsize_i}),
 .in_r(m_awready_i),.out_v(m_awvalid),.out_d({m_awaddr,m_awlen,m_awsize}),.out_r(m_awready));
qkd_host_pin_channel #(.W((63-0+1)+(7-0+1)+1),.IN_PIN(0),.OUT_PIN(1)) st_m_wvalid(
 .ck(clk),.rst_n(rst_n),.in_v(m_wvalid_i),.in_d({m_wdata_i,m_wstrb_i,m_wlast_i}),
 .in_r(m_wready_i),.out_v(m_wvalid),.out_d({m_wdata,m_wstrb,m_wlast}),.out_r(m_wready));
qkd_host_pin_channel #(.W((1-0+1)),.IN_PIN(1),.OUT_PIN(0)) st_m_bvalid(
 .ck(clk),.rst_n(rst_n),.in_v(m_bvalid),.in_d({m_bresp}),
 .in_r(m_bready),.out_v(m_bvalid_i),.out_d({m_bresp_i}),.out_r(m_bready_i));
assign clk_i=clk;
reg [2:0] role_q;
always @(posedge clk or negedge rst_n)if(!rst_n)role_q<=0;else role_q<=die_id;
assign rst_n_i=rst_n && role_q==0;
reg  pin_irq;
always @(posedge clk or negedge rst_n)if(!rst_n)pin_irq<=0;else pin_irq<=irq_i;
assign irq=pin_irq;
reg  pin_pb_we;
always @(posedge clk or negedge rst_n)if(!rst_n)pin_pb_we<=0;else pin_pb_we<=pb_we_i;
assign pb_we=pin_pb_we;
reg [SB+PLB-1:0] pin_pb_waddr;
always @(posedge clk or negedge rst_n)if(!rst_n)pin_pb_waddr<=0;else pin_pb_waddr<=pb_waddr_i;
assign pb_waddr=pin_pb_waddr;
reg [NW-1:0] pin_pb_wdata;
always @(posedge clk or negedge rst_n)if(!rst_n)pin_pb_wdata<=0;else pin_pb_wdata<=pb_wdata_i;
assign pb_wdata=pin_pb_wdata;
reg  pin_pb_re;
always @(posedge clk or negedge rst_n)if(!rst_n)pin_pb_re<=0;else pin_pb_re<=pb_re_i;
assign pb_re=pin_pb_re;
reg [SB+PLB-1:0] pin_pb_raddr;
always @(posedge clk or negedge rst_n)if(!rst_n)pin_pb_raddr<=0;else pin_pb_raddr<=pb_raddr_i;
assign pb_raddr=pin_pb_raddr;
reg [NW-1:0] pin_pb_q;
always @(posedge clk or negedge rst_n)if(!rst_n)pin_pb_q<=0;else pin_pb_q<=pb_q;
assign pb_q_i=pin_pb_q;
assign eng_start=eng_start_i;
assign eng_token=eng_token_i;
assign eng_pos=eng_pos_i;
assign eng_slot=eng_slot_i;
assign kv_base=kv_base_i;
reg  pin_eng_done;
always @(posedge clk or negedge rst_n)if(!rst_n)pin_eng_done<=0;else pin_eng_done<=eng_done;
reg completion_armed;
always @(posedge clk or negedge rst_n)if(!rst_n)completion_armed<=0;
else if(eng_start_i)completion_armed<=0;
else if(!pin_eng_done)completion_armed<=1;
assign eng_done_i=(MUT_DONE_GUARD || completion_armed) && pin_eng_done;
reg [NW-1:0] pin_eng_next_token;
always @(posedge clk or negedge rst_n)if(!rst_n)pin_eng_next_token<=0;else pin_eng_next_token<=eng_next_token;
assign eng_next_token_i=pin_eng_next_token;
reg [31:0] pin_eng_cycles;
always @(posedge clk or negedge rst_n)if(!rst_n)pin_eng_cycles<=0;else pin_eng_cycles<=eng_cycles;
assign eng_cycles_i=pin_eng_cycles;
reg  pin_eng_fault;
always @(posedge clk or negedge rst_n)if(!rst_n)pin_eng_fault<=0;else pin_eng_fault<=eng_fault;
assign eng_fault_i=pin_eng_fault;
assign eng_clr_req=eng_clr_req_i;
// Full physical shape ENG_CTX=NSLOT=1: original acknowledge, leaf-local.
reg clear_ack;
always @(posedge clk or negedge rst_n)if(!rst_n)clear_ack<=0;
else clear_ack<=eng_clr_req_i && !clear_ack;
assign eng_clr_ack_i=clear_ack;
reg  pin_arr_rst_n;
always @(posedge clk or negedge rst_n)if(!rst_n)pin_arr_rst_n<=0;else pin_arr_rst_n<=arr_rst_n_i;
assign arr_rst_n=pin_arr_rst_n;
reg [7:0] pin_cfg_users;
always @(posedge clk or negedge rst_n)if(!rst_n)pin_cfg_users<=0;else pin_cfg_users<=cfg_users_i;
assign cfg_users=pin_cfg_users;
reg [NW-1:0] pin_cfg_prompt_len;
always @(posedge clk or negedge rst_n)if(!rst_n)pin_cfg_prompt_len<=0;else pin_cfg_prompt_len<=cfg_prompt_len_i;
assign cfg_prompt_len=pin_cfg_prompt_len;
reg [NW-1:0] pin_cfg_gen_len;
always @(posedge clk or negedge rst_n)if(!rst_n)pin_cfg_gen_len<=0;else pin_cfg_gen_len<=cfg_gen_len_i;
assign cfg_gen_len=pin_cfg_gen_len;
reg  pin_pr_re;
always @(posedge clk or negedge rst_n)if(!rst_n)pin_pr_re<=0;else pin_pr_re<=pr_re;
assign pr_re_i=pin_pr_re;
reg [7:0] pin_pr_user;
always @(posedge clk or negedge rst_n)if(!rst_n)pin_pr_user<=0;else pin_pr_user<=pr_user;
assign pr_user_i=pin_pr_user;
reg [NW-1:0] pin_pr_pos;
always @(posedge clk or negedge rst_n)if(!rst_n)pin_pr_pos<=0;else pin_pr_pos<=pr_pos;
assign pr_pos_i=pin_pr_pos;
reg  pin_tok_valid;
always @(posedge clk or negedge rst_n)if(!rst_n)pin_tok_valid<=0;else pin_tok_valid<=tok_valid;
assign tok_valid_i=pin_tok_valid;
reg [7:0] pin_tok_user;
always @(posedge clk or negedge rst_n)if(!rst_n)pin_tok_user<=0;else pin_tok_user<=tok_user;
assign tok_user_i=pin_tok_user;
reg [NW-1:0] pin_tok_pos;
always @(posedge clk or negedge rst_n)if(!rst_n)pin_tok_pos<=0;else pin_tok_pos<=tok_pos;
assign tok_pos_i=pin_tok_pos;
reg [NW-1:0] pin_tok_id;
always @(posedge clk or negedge rst_n)if(!rst_n)pin_tok_id<=0;else pin_tok_id<=tok_id;
assign tok_id_i=pin_tok_id;
reg [7:0] pin_users_done;
always @(posedge clk or negedge rst_n)if(!rst_n)pin_users_done<=0;else pin_users_done<=users_done;
assign users_done_i=pin_users_done;
reg  pin_arr_fault;
always @(posedge clk or negedge rst_n)if(!rst_n)pin_arr_fault<=0;else pin_arr_fault<=arr_fault;
assign arr_fault_i=pin_arr_fault;
ot_host_if_pb2_observed #(.PB_READ_PIPE(PB_READ_PIPE),.PB_VALID_ONLY(PB_VALID_ONLY),.NSLOT(NSLOT),.MODE(MODE),.ENG_CTX(ENG_CTX),.NW(NW),.PLB(PLB),.CTX_MAX(CTX_MAX),.AW(AW),.KVW(KVW),.EVQ(EVQ),.FMT(FMT)) u_core(.cq_commit_v(cq_commit_v),.cq_client_tag(cq_client_tag),.cq_slot(cq_slot),.cq_pos(cq_pos),.cq_token(cq_token),.cq_kind(cq_kind),.cq_status(cq_status),.step_issue_v(step_issue_v),.step_client_tag(step_client_tag),.step_slot(step_slot),.step_pos(step_pos),.host_idle(host_idle),.host_observer_fault(host_observer_fault),.step_retire_v(step_retire_v),.step_retire_cq(step_retire_cq),.step_retire_client_tag(step_retire_client_tag),.step_retire_slot(step_retire_slot),.step_retire_pos(step_retire_pos),.step_retire_token(step_retire_token),
.clk(clk_i),
.rst_n(rst_n_i),
.s_awvalid(s_awvalid_i),
.s_awready(s_awready_i),
.s_awaddr(s_awaddr_i),
.s_wvalid(s_wvalid_i),
.s_wready(s_wready_i),
.s_wdata(s_wdata_i),
.s_wstrb(s_wstrb_i),
.s_bvalid(s_bvalid_i),
.s_bready(s_bready_i),
.s_bresp(s_bresp_i),
.s_arvalid(s_arvalid_i),
.s_arready(s_arready_i),
.s_araddr(s_araddr_i),
.s_rvalid(s_rvalid_i),
.s_rready(s_rready_i),
.s_rdata(s_rdata_i),
.s_rresp(s_rresp_i),
.m_arvalid(m_arvalid_i),
.m_arready(m_arready_i),
.m_araddr(m_araddr_i),
.m_arlen(m_arlen_i),
.m_arsize(m_arsize_i),
.m_rvalid(m_rvalid_i),
.m_rready(m_rready_i),
.m_rdata(m_rdata_i),
.m_rresp(m_rresp_i),
.m_rlast(m_rlast_i),
.m_awvalid(m_awvalid_i),
.m_awready(m_awready_i),
.m_awaddr(m_awaddr_i),
.m_awlen(m_awlen_i),
.m_awsize(m_awsize_i),
.m_wvalid(m_wvalid_i),
.m_wready(m_wready_i),
.m_wdata(m_wdata_i),
.m_wstrb(m_wstrb_i),
.m_wlast(m_wlast_i),
.m_bvalid(m_bvalid_i),
.m_bready(m_bready_i),
.m_bresp(m_bresp_i),
.irq(irq_i),
.pb_we(pb_we_i),
.pb_waddr(pb_waddr_i),
.pb_wdata(pb_wdata_i),
.pb_re(pb_re_i),
.pb_raddr(pb_raddr_i),
.pb_q(pb_q_i),
.eng_start(eng_start_i),
.eng_token(eng_token_i),
.eng_pos(eng_pos_i),
.eng_slot(eng_slot_i),
.kv_base(kv_base_i),
.eng_done(eng_done_i),
.eng_next_token(eng_next_token_i),
.eng_cycles(eng_cycles_i),
.eng_fault(eng_fault_i),
.eng_clr_req(eng_clr_req_i),
.eng_clr_ack(eng_clr_ack_i),
.arr_rst_n(arr_rst_n_i),
.cfg_users(cfg_users_i),
.cfg_prompt_len(cfg_prompt_len_i),
.cfg_gen_len(cfg_gen_len_i),
.pr_re(pr_re_i),
.pr_user(pr_user_i),
.pr_pos(pr_pos_i),
.tok_valid(tok_valid_i),
.tok_user(tok_user_i),
.tok_pos(tok_pos_i),
.tok_id(tok_id_i),
.users_done(users_done_i),
.arr_fault(arr_fault_i));

endmodule
