`timescale 1ns/1ps
`default_nettype none
module tb;
 reg fast_clk=1,slow_clk=1;always #3 fast_clk=~fast_clk;always #4 slow_clk=~slow_clk;
 reg cold_n=0,fast_rst_n=0,slow_rst_n=0,abort_fast=0,abort_slow=0;
 reg [4:0] rv=0;wire [4:0] rr,qv;reg [4:0] qready=31;
 reg [19:0] en=0;reg [599:0] addr=0;reg [824:0] ctx=0;
 wire [10239:0] q;wire [1139:0] qo;
 reg [3:0] me_en=0,coll_en=0;reg [119:0] me_addr=0;reg [63:0] me_mask=0;
 reg [2047:0] me_data=0,coll_data=0;reg [59:0] coll_addr=0;
 reg [127:0] row_en=0;reg [3839:0] row_addr=0;reg [4095:0] row_data=0;reg [494:0] wctx=0;
 wire [2:0] wready,wvisible,wpending;wire [127:0] row_visible;
 wire fault,quarantine;wire [7:0] debt;wire [3:0] nwa,nack;wire nra;
 integer fast_edges=0,slow_edges=0,bank_writes=0,groups=0,replies=0;
 reg [4:0] accepted=0;reg [127:0] expected_row_mask=0;
 function automatic [31:0] expected(input integer a);expected=a==7 ? 32'h40000003 : 32'h3f800000+a;endfunction
 ot_ds_native_vm_related_parent #(.ENABLE(1)) dut(
 .fast_clk(fast_clk),.slow_clk(slow_clk),.cold_n(cold_n),.fast_rst_n(fast_rst_n),.slow_rst_n(slow_rst_n),.abort_fast(abort_fast),.abort_slow(abort_slow),
 .r_v(rv),.r_ready(rr),.r_enable(en),.r_addr(addr),.r_context(ctx),.q_v(qv),.q_ready(qready),.q_data(q),.q_owner(qo),
 .me_en(me_en),.me_wordaddr(me_addr),.me_mask(me_mask),.me_data(me_data),
 .row_en(row_en),.row_addr(row_addr),.row_data(row_data),.coll_en(coll_en),.coll_wordaddr(coll_addr),.coll_data(coll_data),
 .w_context(wctx),.w_ready(wready),.w_visible(wvisible),.w_pending(wpending),.row_visible_mask(row_visible),
 .fault(fault),.quarantined(quarantine),.debt(debt),.debug_native_write_accept(nwa),.debug_native_visible(nack),.debug_native_read_accept(nra));
 always @(posedge slow_clk)if(cold_n)begin slow_edges<=slow_edges+1;bank_writes<=bank_writes+$countones(nack);groups<=groups+nra;end
 always @(posedge fast_clk)if(cold_n)begin
  fast_edges<=fast_edges+1;
  for(integer c=0;c<5;c=c+1)begin
   if(rv[c]&&rr[c])begin rv[c]<=0;accepted[c]<=1;$display("EVENT transport_accept client=%0d fast_edge=%0d",c,fast_edges);end
   if(qv[c]&&qready[c])begin
    replies<=replies+1;
    if(qo[c*228+224+:4]!=c || qo[c*228+:11]!=0)$fatal(1,"source namespace/identity mismatch");
    for(integer l=0;l<(c==0 ? 64 : c==1 ? 1 : c==2 ? 16 : c==3 ? 4 : 64);l=l+1)begin
     integer a;
     if(c==0)a=31+l;else if(c==1)a=7;else if(c==2)a=32+l;
     else if(c==3)a=addr[c*120+l*30+:30];else a=addr[c*120+(l/16)*30+:30]+l%16;
     if(q[c*2048+l*32+:32]!==expected(a))$fatal(1,"data/order client%0d lane%0d got%h expected%h",c,l,q[c*2048+l*32+:32],expected(a));
    end
    $display("EVENT caller_capture client=%0d fast_edge=%0d",c,fast_edges);
   end
  end
  if(wvisible[1] && row_visible!==expected_row_mask)$fatal(1,"field receipt cleared unowned row");
  if(fault)$fatal(1,"unexpected parent fault");
 end
 task field_write(input integer tag,input integer duplicate);
 begin
  @(negedge fast_clk);wctx[165+:165]=tag;
  row_en=duplicate ? 128'd3 : {128{1'b1}};expected_row_mask=row_en;
  for(integer i=0;i<128;i=i+1)begin row_addr[i*30+:30]=duplicate ? 7 : i;row_data[i*32+:32]=duplicate ? 32'h40000002+i : 32'h3f800000+i;end
  do @(posedge fast_clk);while(!wready[1]);
  @(negedge fast_clk);row_en=0;wait(wvisible[1]);@(negedge fast_clk);
 end endtask
 initial begin
  repeat(5)@(negedge slow_clk);cold_n=1;fast_rst_n=1;slow_rst_n=1;
  field_write(11,0);
  @(negedge fast_clk);me_en=15;me_mask={64{1'b1}};
  for(integer p=0;p<4;p=p+1)begin me_addr[p*30+:30]=p;
   for(integer l=0;l<16;l=l+1)me_data[p*512+l*32+:32]=32'h3f800000+p*16+l;end
  do @(posedge fast_clk);while(!wready[0]);@(negedge fast_clk);me_en=0;wait(wvisible[0]);@(negedge fast_clk);
  coll_en=15;
  for(integer p=0;p<4;p=p+1)begin coll_addr[p*15+:15]=p+4;
   for(integer l=0;l<16;l=l+1)coll_data[p*512+l*32+:32]=32'h3f800000+64+p*16+l;end
  do @(posedge fast_clk);while(!wready[2]);@(negedge fast_clk);coll_en=0;wait(wvisible[2]);@(negedge fast_clk);
  field_write(14,1);
  if(bank_writes!=17)$fatal(1,"visible native writes %0d",bank_writes);
  en=20'hfffff;en[3:0]=1;en[7:4]=1;en[11:8]=1;
  addr[0+:30]=31;addr[120+:30]=7;addr[240+:30]=2;
  addr[360+:30]=1;addr[390+:30]=7;addr[420+:30]=63;addr[450+:30]=127;
  addr[480+:30]=3;addr[510+:30]=49;addr[540+:30]=64;addr[570+:30]=112;
  // Consumer0 stalls after dispatch; other endpoint services must continue.
  qready[0]=0;rv=31;wait(replies==4);
  if(!debt[0]||!qv[0]||dut.reqp[0]==0)$fatal(1,"stalled consumer debt lost");
  repeat(8)@(negedge fast_clk);qready[0]=1;wait(replies==5);wait(debt==0);@(negedge fast_clk);
  $display("EVENT all_reverse_receipts fast_edge=%0d slow_edge=%0d",fast_edges,slow_edges);
  // Accepted-undelivered read survives transport reset, no new owner admitted.
  rv=2;do @(posedge fast_clk);while(!rr[1]);@(negedge fast_clk);rv=0;abort_fast=1;abort_slow=1;
  repeat(2)@(negedge slow_clk);fast_rst_n=0;slow_rst_n=0;
  repeat(5)@(negedge slow_clk);fast_rst_n=1;slow_rst_n=1;abort_fast=0;abort_slow=0;
  repeat(10)@(negedge slow_clk);
  if(!debt[1]||!quarantine||rr[1])$fatal(1,"reset erased debt or admitted stale owner");
  $display("PASS RELATED_NATIVE_PARENT native_clients=8 related_planes=13 macros=256 visible_bank_writes=17 replies=5 no_head_of_line_block=1 masked_row_receipt=1 reset_debt=1 groups=%0d",groups);$finish;
 end
 initial begin repeat(10000)@(posedge fast_clk);$fatal(1,"directed event bound");end
endmodule
`default_nettype wire
