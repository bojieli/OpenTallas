`timescale 1ns/1ps
module bridge_tb;
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
 qkd_host_axi_packet_rc #(.ENABLE_RETAINED_COMMIT(1),.RC_MUT(MUTANT)) dut(.*);
 integer edge_n=0,ntx=0,ncr=0;reg[511:0] sent[0:63];
 task tick;begin @(posedge ck);#1;edge_n++;if(tx_v)begin sent[ntx]=tx_d;ntx++;$display("TX edge=%0d op=%h id=%h",edge_n,tx_d[7:0],tx_d[31:16]);end if(rx_cr)ncr++;@(negedge ck);end endtask
 task cycles(input integer n);integer i;begin for(i=0;i<n;i++)tick;end endtask
 task fail(input string why);begin $display("FAIL %s edge=%0d",why,edge_n);$fatal(1,"%s",why);end endtask
 task boot;begin raw_por_n=0;rst_n=0;warm_rst_n=1;health_bad_i=0;health_armed_i=0;rx_v=0;tx_cr=0;m_awvalid=0;m_wvalid=0;m_arvalid=0;m_rready=0;m_bready=0;s_awready=0;s_wready=0;s_arready=0;s_bvalid=0;s_rvalid=0;cycles(3);raw_por_n=1;rst_n=1;cycles(2);health_armed_i=1;cycles(2);end endtask
 task packet(input reg[511:0] p);begin rx_d=p;rx_v=1;tick;rx_v=0;cycles(6);end endtask
 task await_tx(input integer base,input reg[7:0] op,input string why);integer n;begin n=0;while(ntx==base&&n<24)begin tick;n++;end if(ntx==base||sent[base][7:0]!=op)fail(why);end endtask
 integer base,i;reg[511:0]p;
 initial begin
  // Genuine half-AW ownership precedes poison and a protocol fault. W remains
  // eligible, then a real outstanding B must drain despite that sticky fault.
  boot;m_awaddr=64'h1234567800001040;m_awvalid=1;cycles(3);m_awvalid=0;cycles(2);
  if(!dut.ba)fail("SETUP_AW_NOT_ACCEPTED");
  warm_rst_n=0;cycles(2);packet(512'h01ff);if(!fault)fail("SETUP_PROTOCOL_FAULT");
  base=ntx;m_wdata=64'hcafebabedeadbeef;m_wstrb=8'hdf;m_wvalid=1;cycles(3);m_wvalid=0;
  await_tx(base,8'h14,"ACCEPTED_DMA_STUCK");
  if(sent[base][95:32]!=64'h1234567800001040||sent[base][159:96]!=64'hcafebabedeadbeef)fail("OFFER_STABILITY");
  packet(512'h0115);if(!m_bvalid||m_bresp!=0)fail("ACCEPTED_DMA_STUCK");
  m_bready=1;cycles(3);m_bready=0;if(dut.dw||m_bvalid)fail("ACCEPTED_DMA_STUCK");
  // Queued, never-offered poisoned CSR commands get finite correctly-ID'd
  // SLVERR records, never actual CSR mutation. Both opcodes use real credits.
  for(i=0;i<2;i++)begin
   base=ntx;p=512'h0101+i;p[31:16]=16'h73a1+i;p[44:32]=13'h124;
   if(i==0)begin p[127:96]=32'h11223344;p[131:128]=4'hf;end
   packet(p);
   if(s_awvalid||s_wvalid||s_arvalid)fail("POST_POISON_CSR_MUTATION");
   await_tx(base,8'h81+i,"CSR_ERROR_ID");
   if(sent[base][31:16]!=(16'h73a1+i)||sent[base][33:32]!=2)fail("CSR_ERROR_ID");
  end
  if(ncr!=4)fail("REAL_RX_CREDIT_ACCOUNTING");
  // A pre-poison CSR offer remains immutable independently on AW and W.
  boot;base=ntx;p=512'h0101;p[31:16]=16'hb231;p[44:32]=13'h318;p[127:96]=32'h55aa33cc;p[131:128]=4'hb;packet(p);
  if(!s_awvalid||!s_wvalid)fail("SETUP_CSR_NOT_OFFERED");
  health_bad_i=1;cycles(5);
  if(!s_awvalid||!s_wvalid||s_awaddr!=13'h318||s_wdata!=32'h55aa33cc||s_wstrb!=4'hb)fail("OFFER_STABILITY");
  s_awready=1;cycles(3);s_awready=0;
  if(s_awvalid||!s_wvalid)fail("OFFER_STABILITY");
  cycles(3);if(!s_wvalid||s_wdata!=32'h55aa33cc)fail("OFFER_STABILITY");
  s_wready=1;cycles(3);s_wready=0;s_bvalid=1;cycles(2);
  await_tx(base,8'h81,"ACCEPTED_CSR_STUCK");if(sent[base][31:16]!=16'hb231||sent[base][33:32]!=0)fail("CSR_ERROR_ID");
  // Raw POR clears retained state; warm never did so.
  raw_por_n=0;cycles(2);if(retained_owned_o||retained_bad_o||fault)fail("RAW_POR_CLEAR");
  $display("PASS bridge component mutant=%0d edges=%0d",MUTANT,edge_n);$finish;
 end
endmodule
