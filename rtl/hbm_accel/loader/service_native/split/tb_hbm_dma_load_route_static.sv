`timescale 1ns/1ps
module tb_hbm_dma_load_route_static;
 reg clk=0; always #5 clk=~clk;
 reg rst_n=0;
 reg [2247:0] lanes=0;
 reg [39:0] destinations=0;
 wire [280:0] sp,dp,dq;
 wire [4:0] sd;
 wire [2:0] bank;
 wire sf,df,bf;
 reg [1123:0] packets=0;
 reg [19:0] routes=0;
 reg [280:0] raw=0;
 ot_hbm_dma_load_source_join s(clk,rst_n,lanes,destinations,sp,sd,sf);
 ot_hbm_dma_load_destination_join #(.QID(2)) d(clk,rst_n,packets,routes,dp,bank,df);
 ot_hbm_dma_load_bank_join #(.BANK(5)) b(clk,rst_n,raw,dp,bank,dq,bf);
 reg [280:0] expected;
 integer l,q;
 task tick; begin @(posedge clk); #1; end endtask
 task reset;
 begin
  @(negedge clk);rst_n=0;lanes=0;packets=0;raw=0;
  tick();@(negedge clk);rst_n=1;tick();
 end endtask
 initial begin
  reset();
  for(l=0;l<8;l=l+1) for(q=0;q<4;q=q+1) begin
   expected={1'b1,16'(123+l),256'(32'h12345678+l),8'(1<<l)};
   @(negedge clk);lanes=0;destinations=0;
   lanes[l*281+:281]=expected;destinations[l*5+:5]={2'(q),3'd5};
   tick();tick();if(sp!==expected||sd!=={2'(q),3'd5}||sf)$fatal(1,"source route corrupt");
   @(negedge clk);packets=0;routes=0;
   packets[(l%4)*281+:281]=sp;routes[(l%4)*5+:5]=sd;
   tick();tick();tick();
   if(q==2)begin
    if(dp!==expected||bank!==5||dq!==expected)$fatal(1,"destination or mask corrupt");
   end else if(dp[280]||dq[280])$fatal(1,"wrong quadrant received packet");
   if(df||bf)$fatal(1,"unexpected route fault");
  end
  // The raw loader retains its existing edge and arbitrary word masks.
  @(negedge clk);packets=0;tick();tick();tick();
  raw={1'b1,16'd77,256'd42,8'h81};tick();
  if(dq!==raw)$fatal(1,"raw delivery changed");
  raw=0;
  // Two source lanes at the same reserved slot must fail closed.
  @(negedge clk);lanes=0;lanes[280]=1;lanes[561]=1;
  tick();tick();if(!sf||sp[280])$fatal(1,"source collision escaped");
  reset();
  @(negedge clk);packets=0;routes=0;
  packets[280]=1;packets[561]=1;routes[0+:5]={2'd2,3'd5};routes[5+:5]={2'd2,3'd5};
  tick();tick();if(!df||dp[280])$fatal(1,"destination collision escaped");
  reset();
  @(negedge clk);packets=0;packets[0+:281]={1'b1,280'd9};routes[0+:5]={2'd2,3'd5};
  tick();tick();raw={1'b1,280'd2};tick();
  if(dq[280]!==0)$fatal(1,"raw LOAD collision emitted data");
  tick();if(!bf)$fatal(1,"raw LOAD collision not reported");
  $display("DMA_LOAD_ROUTE PASS 32 routes, raw masks, three collision classes");$finish;
 end
endmodule
