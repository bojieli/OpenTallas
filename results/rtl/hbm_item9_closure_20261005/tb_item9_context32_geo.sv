`timescale 1ps/1ps
// Minimum actual 32-caller register/control mechanism. No SM compute or die array.
module tb_item9_context32_geo;
 localparam N=32,W=4096,PW=546;
 reg clk=0;always #416.5 clk=~clk;
 reg por_n=0;reg[N-1:0]issue=0,mode='1;
 reg[N*8-1:0]count;reg[N*W-1:0]va;
 wire[N-1:0]idle[0:1],done[0:1];wire[N*W-1:0]vr[0:1];
 wire[1:0]tv,fault;wire[PW-1:0]tr[0:1];
 reg rxv=0;reg[PW-1:0]rxr=0;
 for(genvar b=0;b<1;b=b+1)begin:g_dut
 ot_gpu_coll_item9_context32_geo #(.ENABLE(1),.NSM(N),.OWNER64(1),.TX_MASK_LA(1),
 .RXOH(1),.RDUP(16),.TXCTRL(1),.TREE(1),.GEO(1)) dut(.por_n(por_n),.clk_sm(clk),.clk_link(clk),
 .clk_mem(clk),.clk_host(clk),.issue(issue),.issue_mode(mode),.issue_count(count),
 .issue_va(va),.caller_idle(idle[b]),.caller_done(done[b]),.caller_vr(vr[b]),
 .switch_rx_v(rxv),.switch_rx_rec(rxr),.switch_tx_v(tv[b]),.switch_tx_rec(tr[b]),.fault(fault[b]));
 end
 reg[PW-1:0]q[0:511];integer wp=0,rp=0,completed=0,cycles=0;
 reg[N-1:0]seen=0;reg checking=0;
 always @(posedge clk)begin
  cycles=cycles+1;
  if(checking)begin
   if(fault[0])$fatal(1,"unexpected protected endpoint fault");
   if(tv[0])begin
    if(wp+2>512)$fatal(1,"finite test queue full");
    q[wp]=tr[0];q[wp+1]={8'd1,tr[0][PW-9:0]};wp=wp+2;
   end
   for(integer s=0;s<N;s=s+1)if(done[0][s])begin
    if(seen[s])$fatal(1,"duplicate caller completion");
    // done is true on the same edge as the actual destination vector capture.
    #1;
    for(integer l=0;l<128;l=l+1)begin
     if(vr[0][s*W+l*32+:32]!==va[s*W+(l%64)*32+:32])$fatal(1,"gather golden mismatch caller%0d lane%0d",s,l);
    end
    seen[s]=1;completed=completed+1;
   end
  end
 end
 // Native pulse-record receive protocol; bounded queue emits both real ranks.
 always @(negedge clk)begin
  rxv=0;
  if(rp<wp)begin rxr=q[rp];rxv=1;rp=rp+1;end
 end
 initial begin
  for(integer s=0;s<N;s=s+1)begin
   count[s*8+:8]=64;
   for(integer l=0;l<128;l=l+1)va[s*W+l*32+:32]=32'h3f000000+s*128+l;
  end
  repeat(4)@(negedge clk);por_n=1;
  wait(g_dut[0].dut.g_on.rst_sm_n);
  @(negedge clk);checking=1;issue='1;@(negedge clk);issue=0;
  wait(completed==N);@(negedge clk);
  if(seen!=='1||wp!=256||rp!=256)$fatal(1,"record/completion counts");
  if(cycles!=789)$fatal(1,"changed cycle total %0d",cycles);
  $display("PASS GEO actual32 caller NL128 exact completed=%0d TXrecords=%0d RXrecords=%0d cycles=%0d added_cycles=0",completed,wp/2,rp,cycles);$finish;
 end
 // A logical deadlock check bounded by 32 finite requests and endpoint FIFO depth.
 initial begin repeat(32*512)@(posedge clk);$fatal(1,"finite transaction progress bound exceeded");end
endmodule
