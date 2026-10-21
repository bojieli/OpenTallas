`timescale 1ns/1ps
module bridge_default_tb;
 parameter integer MUTANT=0;
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0,raw_por_n=0,warm_rst_n=1,pll_locked_i=1,health_bad_i=0,health_armed_i=0;
 reg execution_restart_i=0,role_fault_i=0,retained_bad_i=0;
 wire retained_bad_o,retained_owned_o;
 reg rx_v=0;reg[511:0]rx_d=0;wire rx_cr,tx_v;wire[511:0]tx_d;reg tx_cr=0;wire fault;
 wire s_awvalid,s_wvalid,s_bready,s_arvalid,s_rready;
 reg s_awready=0,s_wready=0,s_bvalid=0,s_arready=0,s_rvalid=0;
 wire[12:0]s_awaddr,s_araddr;wire[31:0]s_wdata;wire[3:0]s_wstrb;
 reg[1:0]s_bresp=0,s_rresp=0;reg[31:0]s_rdata=0;
 reg m_arvalid=0,m_rready=0,m_awvalid=0,m_wvalid=0,m_bready=0;
 wire m_arready,m_rvalid,m_rlast,m_awready,m_wready,m_bvalid;
 reg[63:0]m_araddr=0,m_awaddr=0,m_wdata=0;reg[7:0]m_wstrb=0;
 wire[63:0]m_rdata;wire[1:0]m_rresp,m_bresp;
 wire ref_rx_cr;
 wire ref_tx_v;
 wire[511:0] ref_tx_d;
 wire ref_fault;
 wire ref_s_awvalid;
 wire[12:0] ref_s_awaddr;
 wire ref_s_wvalid;
 wire[31:0] ref_s_wdata;
 wire[3:0] ref_s_wstrb;
 wire ref_s_bready;
 wire ref_s_arvalid;
 wire[12:0] ref_s_araddr;
 wire ref_s_rready;
 wire ref_m_arready;
 wire ref_m_rvalid;
 wire[63:0] ref_m_rdata;
 wire[1:0] ref_m_rresp;
 wire ref_m_rlast;
 wire ref_m_awready;
 wire ref_m_wready;
 wire ref_m_bvalid;
 wire[1:0] ref_m_bresp;
 qkd_host_axi_packet_rc #(.ENABLE_RETAINED_COMMIT(0)) dut(.*);
 qkd_host_axi_packet original(.rx_cr(ref_rx_cr),.tx_v(ref_tx_v),.tx_d(ref_tx_d),.fault(ref_fault),.s_awvalid(ref_s_awvalid),.s_awaddr(ref_s_awaddr),.s_wvalid(ref_s_wvalid),.s_wdata(ref_s_wdata),.s_wstrb(ref_s_wstrb),.s_bready(ref_s_bready),.s_arvalid(ref_s_arvalid),.s_araddr(ref_s_araddr),.s_rready(ref_s_rready),.m_arready(ref_m_arready),.m_rvalid(ref_m_rvalid),.m_rdata(ref_m_rdata),.m_rresp(ref_m_rresp),.m_rlast(ref_m_rlast),.m_awready(ref_m_awready),.m_wready(ref_m_wready),.m_bvalid(ref_m_bvalid),.m_bresp(ref_m_bresp),.*);
 integer edge_n=0;reg[31:0] rng=32'h127894da;
 function automatic [31:0] rnd;begin rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);rnd=rng;end endfunction
 initial begin
  repeat(2000)begin
   @(negedge ck);rst_n=(edge_n%67)>2;raw_por_n=rnd();warm_rst_n=rnd();health_armed_i=rnd();health_bad_i=rnd();pll_locked_i=rnd();execution_restart_i=rnd();role_fault_i=rnd();retained_bad_i=rnd();
   rx_v=(edge_n%7)==0;rx_d=0;rx_d[15:0]=(edge_n%2)?16'h0101:16'h0102;rx_d[31:16]=rnd();rx_d[44:32]=rnd();
   tx_cr=(edge_n%11)==0;
   s_awready=rnd();s_wready=rnd();s_bvalid=rnd();s_bresp=rnd();s_arready=rnd();s_rvalid=rnd();s_rdata=rnd();s_rresp=rnd();
   m_arvalid=rnd();m_araddr={rnd(),rnd()};m_rready=rnd();m_awvalid=rnd();m_awaddr={rnd(),rnd()};m_wvalid=rnd();m_wdata={rnd(),rnd()};m_wstrb=rnd();m_bready=rnd();
   @(posedge ck);#1;edge_n++;
   if({rx_cr,tx_v,tx_d,fault,s_awvalid,s_awaddr,s_wvalid,s_wdata,s_wstrb,s_bready,s_arvalid,s_araddr,s_rready,m_arready,m_rvalid,m_rdata,m_rresp,m_rlast,m_awready,m_wready,m_bvalid,m_bresp} !== {ref_rx_cr,ref_tx_v,ref_tx_d,ref_fault,ref_s_awvalid,ref_s_awaddr,ref_s_wvalid,ref_s_wdata,ref_s_wstrb,ref_s_bready,ref_s_arvalid,ref_s_araddr,ref_s_rready,ref_m_arready,ref_m_rvalid,ref_m_rdata,ref_m_rresp,ref_m_rlast,ref_m_awready,ref_m_wready,ref_m_bvalid,ref_m_bresp}) $fatal(1,"DEFAULT_IDENTITY edge=%0d",edge_n);
  end
  $display("PASS DEFAULT_IDENTITY 2000 edges all original outputs");$finish;
 end
endmodule
