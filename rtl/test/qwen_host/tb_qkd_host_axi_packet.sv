`timescale 1ns/1ps
module tb_qkd_host_axi_packet;
 parameter integer MUT=0;
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0,rx_v=0,tx_cr=0;reg[511:0]rx_d=0;wire rx_cr,tx_v,fault;wire[511:0]tx_d;
 wire s_awvalid,s_wvalid,s_arvalid,s_bready,s_rready;
 reg s_awready=0,s_wready=0,s_arready=0,s_bvalid=0,s_rvalid=0;reg[1:0]s_bresp=0,s_rresp=0;reg[31:0]s_rdata=0;
 wire[12:0]s_awaddr,s_araddr;wire[31:0]s_wdata;wire[3:0]s_wstrb;
 reg m_arvalid=0,m_awvalid=0,m_wvalid=0,m_rready=0,m_bready=0;reg[63:0]m_araddr=0,m_awaddr=0,m_wdata=0;reg[7:0]m_wstrb=0;
 wire m_arready,m_awready,m_wready,m_rvalid,m_bvalid,m_rlast;wire[63:0]m_rdata;wire[1:0]m_rresp,m_bresp;
 qkd_host_axi_packet #(.MUT(MUT)) dut(.*);
 integer checks=0;
 task tick;begin @(posedge ck);#1;end endtask
 task check(input bit ok,input string why);begin checks++;if(!ok)$fatal(1,"%s",why);end endtask
 task send(input[511:0]w);begin @(negedge ck);rx_v=1;rx_d=w;@(negedge ck);rx_v=0;end endtask
 task wait_tx(input[7:0]op);integer k;begin k=0;while(!tx_v&&k<100)begin tick();k++;end check(tx_v&&tx_d[7:0]==op,"packet opcode");end endtask
 task ret_credit;begin @(negedge ck);tx_cr=1;@(negedge ck);tx_cr=0;end endtask
 reg[511:0]p;
 initial begin
  repeat(4)tick();rst_n=1;repeat(4)tick();
  // BAR AW stalls independently of W; transaction id and byte strobes survive.
  p=512'h00000101;p[31:16]=16'hface;p[44:32]=13'h1050;p[127:96]=32'h89abcdef;p[131:128]=4'b1010;
  send(p);repeat(5)tick();check(s_awvalid&&s_wvalid,"BAR valid");check(s_awaddr==13'h1050&&s_wdata==32'h89abcdef&&s_wstrb==10,"BAR contents");
  s_wready=1;tick();s_wready=0;repeat(7)begin tick();check(s_awvalid&&!s_wvalid,"independent AXI AW backpressure");end
  s_awready=1;tick();s_awready=0;s_bvalid=1;s_bresp=2;wait_tx(8'h81);check(tx_d[31:16]==16'hface&&tx_d[33:32]==2,"BAR B id/resp");
  tick();s_bvalid=0;ret_credit();
  p=512'h0102;p[31:16]=16'h1234;p[44:32]=13'h0088;send(p);repeat(5)tick();check(s_arvalid&&s_araddr==13'h88,"BAR AR");
  s_arready=1;tick();s_arready=0;s_rvalid=1;s_rdata=32'h12345678;s_rresp=1;wait_tx(8'h82);
  check(tx_d[31:16]==16'h1234&&tx_d[127:96]==32'h12345678&&tx_d[33:32]==1,"BAR R exact");tick();s_rvalid=0;ret_credit();
  // Native 64-bit read plus delayed response and held rvalid under backpressure.
  m_arvalid=1;m_araddr=64'h123456789abcdef0;wait_tx(8'h12);check(tx_d[95:32]==m_araddr,"DMA AR64");m_arvalid=0;ret_credit();
  p=512'h0113;p[34]=1;p[33:32]=2;p[159:96]=64'hfedcba9876543210;send(p);repeat(6)tick();
  for(integer j=0;j<10;j++)begin check(m_rvalid&&m_rdata==64'hfedcba9876543210&&m_rresp==2&&m_rlast,"DMA R exact hold");tick();end
  m_rready=1;tick();m_rready=0;
  // AW and W may arrive in either order. No packet until both were captured.
  m_wvalid=1;m_wdata=64'h0123456789abcdef;m_wstrb=8'h5a;repeat(4)tick();m_wvalid=0;
  repeat(5)begin tick();check(!tx_v,"no write until AW");end
  m_awvalid=1;m_awaddr=64'h1122334455667788;wait_tx(8'h14);m_awvalid=0;
  check(tx_d[95:32]==64'h1122334455667788&&tx_d[159:96]==64'h0123456789abcdef&&tx_d[167:160]==8'h5a,"DMA write exact");ret_credit();
  p=512'h0115;p[33:32]=3;send(p);repeat(6)tick();check(m_bvalid&&m_bresp==3,"DMA B error");repeat(6)tick();check(m_bvalid,"B holds");m_bready=1;tick();m_bready=0;
  // Wrong version is fail-closed, never an AXI access.
  send(512'h0201);repeat(8)tick();check(fault&&!s_awvalid&&!s_wvalid,"bad version closed");
  $display("PASS HOST_AXI_PACKET checks=%0d",checks);$finish;
 end
 initial begin #100000;$fatal(1,"timeout");end
endmodule
