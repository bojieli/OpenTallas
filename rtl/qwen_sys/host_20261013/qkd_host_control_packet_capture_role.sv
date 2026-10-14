`timescale 1ns/1ps
// UNQUALIFIED capture256 candidate; no baseline source/view adoption.
// Wires-only complete host-control/packet/prompt composition. Genuine TP8
// tk/kst/boot status comes from addressed original CTRL transport, never ties.
// pr143 producer must reserve available credit per PW/DW pulse edge. All
// simultaneous rawhc pulses consume one credit; source_cr follows seven copies.
module qkd_host_control_packet_capture_role #(parameter T_LINK=200000,T_HBM=200000,WDOG=1<<22,HC_MUT=0,PROMPT_MUT=0,PROMPT_BIND_LATENCY=4)(
 input wire ck_host,ck_csr,ck_rst,ck_ctl,ck_prompt,
 input wire[2:0]die_id,input wire por_n,input wire[5:0]link_up,
 input wire[7:0]transport_fault,physical_fault,input wire crom_fault,input wire[142:0]pr,
 output wire irq,host_rst_n,link_rst_n,hbm_rst_n,boot_go,die_rst_n,sys_ready,
 output wire[31:0]fault_src,
input wire ck_rx,ck_tx,ck_axi,ck_ctrl,ck_hc,
 input wire rx_v,input wire[527:0]rx_d,output wire rx_cr,
 output wire tx_v,output wire[527:0]tx_d,input wire tx_cr,
 input wire[92:0]local_tk,input wire[9:0]local_kst,input wire[1:0]local_boot,
 output wire[181:0]hc,output wire[7:0]seen,
 output wire source_cr,available,source_fault,output wire[3:0]packet_faults,
 output wire ing_v,output wire[1:0]ing_cls,output wire[511:0]ing_d,input wire[4:0]ing_crn,
 input wire ing_t_v,input wire[63:0]ing_t_d,output wire ing_t_cr
);
 wire[743:0]tk8;wire[79:0]kst8;wire[15:0]boot8;wire[7:0]boot_done,boot_ok;
 for(genvar d=0;d<8;d=d+1)begin:g_boot
  assign boot_done[d]=boot8[d*2];assign boot_ok[d]=boot8[d*2+1];
 end
 wire[181:0]raw_hc,cmd_hc;wire cmd_v,cmd_cr;
wire  s_awvalid;
wire  s_awready;
wire [12:0] s_awaddr;
wire  s_wvalid;
wire  s_wready;
wire [31:0] s_wdata;
wire [3:0] s_wstrb;
wire  s_bvalid;
wire  s_bready;
wire [1:0] s_bresp;
wire  s_arvalid;
wire  s_arready;
wire [12:0] s_araddr;
wire  s_rvalid;
wire  s_rready;
wire [31:0] s_rdata;
wire [1:0] s_rresp;
wire  m_arvalid;
wire  m_arready;
wire [63:0] m_araddr;
wire [7:0] m_arlen;
wire [2:0] m_arsize;
wire  m_rvalid;
wire  m_rready;
wire [63:0] m_rdata;
wire [1:0] m_rresp;
wire  m_rlast;
wire  m_awvalid;
wire  m_awready;
wire [63:0] m_awaddr;
wire [7:0] m_awlen;
wire [2:0] m_awsize;
wire  m_wvalid;
wire  m_wready;
wire [63:0] m_wdata;
wire [7:0] m_wstrb;
wire  m_wlast;
wire  m_bvalid;
wire  m_bready;
wire [1:0] m_bresp;
qkd_host_control_prompt_capture_role #(.T_LINK(T_LINK),.T_HBM(T_HBM),.WDOG(WDOG),.PROMPT_MUT(PROMPT_MUT),.PROMPT_BIND_LATENCY(PROMPT_BIND_LATENCY))u_control(
.ck_host(ck_host),
.die_id(die_id),
.por_n(por_n),
.s_awvalid(s_awvalid),
.s_awready(s_awready),
.s_awaddr(s_awaddr),
.s_wvalid(s_wvalid),
.s_wready(s_wready),
.s_wdata(s_wdata),
.s_wstrb(s_wstrb),
.s_bvalid(s_bvalid),
.s_bready(s_bready),
.s_bresp(s_bresp),
.s_arvalid(s_arvalid),
.s_arready(s_arready),
.s_araddr(s_araddr),
.s_rvalid(s_rvalid),
.s_rready(s_rready),
.s_rdata(s_rdata),
.s_rresp(s_rresp),
.m_arvalid(m_arvalid),
.m_arready(m_arready),
.m_araddr(m_araddr),
.m_arlen(m_arlen),
.m_arsize(m_arsize),
.m_rvalid(m_rvalid),
.m_rready(m_rready),
.m_rdata(m_rdata),
.m_rresp(m_rresp),
.m_rlast(m_rlast),
.m_awvalid(m_awvalid),
.m_awready(m_awready),
.m_awaddr(m_awaddr),
.m_awlen(m_awlen),
.m_awsize(m_awsize),
.m_wvalid(m_wvalid),
.m_wready(m_wready),
.m_wdata(m_wdata),
.m_wstrb(m_wstrb),
.m_wlast(m_wlast),
.m_bvalid(m_bvalid),
.m_bready(m_bready),
.m_bresp(m_bresp),
.irq(irq),
.link_up(link_up),
.boot_done(boot_done),
.boot_ok(boot_ok),
.host_rst_n(host_rst_n),
.link_rst_n(link_rst_n),
.hbm_rst_n(hbm_rst_n),
.boot_go(boot_go),
.die_rst_n(die_rst_n),
.sys_ready(sys_ready),
.c_start(),
.c_token(),
.c_pos(),
.c_kv_base(),
.c_gen(),
.transport_fault(transport_fault),
.crom_fault(crom_fault),
.fault_src(fault_src),
.pr(pr),
.tk8(tk8),
.kst8(kst8),
.hc(raw_hc),
.ck_csr(ck_csr),
.ck_rst(ck_rst),
.ck_ctl(ck_ctl),
.ck_prompt(ck_prompt),
.physical_fault(physical_fault));
qkd_host_hc_station #(.MUT(HC_MUT))u_hc(.ck(ck_hc),.rst_n(host_rst_n),.die_id(die_id),.raw_hc(raw_hc),.cmd_cr(cmd_cr),
 .cmd_v(cmd_v),.cmd_hc(cmd_hc),.source_cr(source_cr),.available(available),.fault(source_fault));
qkd_host_packet_bundle u_packet(.ck_rx(ck_rx),.ck_tx(ck_tx),.ck_axi(ck_axi),.ck_ctrl(ck_ctrl),.rst_n(host_rst_n),.die_id(die_id),
 .rx_v(rx_v),.rx_d(rx_d),.rx_cr(rx_cr),.tx_v(tx_v),.tx_d(tx_d),.tx_cr(tx_cr),.irq(irq),
 .local_tk(local_tk),.local_kst(local_kst),.local_boot(local_boot),.cmd_v(cmd_v),.cmd_hc(cmd_hc),.cmd_cr(cmd_cr),
 .hc(hc),.tk8(tk8),.kst8(kst8),.boot8(boot8),.seen(seen),
 .ing_v(ing_v),.ing_cls(ing_cls),.ing_d(ing_d),.ing_crn(ing_crn),.ing_t_v(ing_t_v),.ing_t_d(ing_t_d),.ing_t_cr(ing_t_cr),.faults(packet_faults),
.s_awvalid(s_awvalid),
.s_awready(s_awready),
.s_awaddr(s_awaddr),
.s_wvalid(s_wvalid),
.s_wready(s_wready),
.s_wdata(s_wdata),
.s_wstrb(s_wstrb),
.s_bvalid(s_bvalid),
.s_bready(s_bready),
.s_bresp(s_bresp),
.s_arvalid(s_arvalid),
.s_arready(s_arready),
.s_araddr(s_araddr),
.s_rvalid(s_rvalid),
.s_rready(s_rready),
.s_rdata(s_rdata),
.s_rresp(s_rresp),
.m_arvalid(m_arvalid),
.m_arready(m_arready),
.m_araddr(m_araddr),
.m_rvalid(m_rvalid),
.m_rready(m_rready),
.m_rdata(m_rdata),
.m_rresp(m_rresp),
.m_rlast(m_rlast),
.m_awvalid(m_awvalid),
.m_awready(m_awready),
.m_awaddr(m_awaddr),
.m_wvalid(m_wvalid),
.m_wready(m_wready),
.m_wdata(m_wdata),
.m_wstrb(m_wstrb),
.m_bvalid(m_bvalid),
.m_bready(m_bready),
.m_bresp(m_bresp));
endmodule
