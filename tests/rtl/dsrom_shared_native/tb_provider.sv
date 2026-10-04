`timescale 1ns/1ps
`default_nettype none
module tb;
 reg clk=1;always #4 clk=~clk;
 reg cold_n=0,rst_n=0,abort=0;
 reg [4:0] rv=0;wire [4:0] rr,qv,retire;reg [19:0] en=0;reg [599:0] addr=0;
 reg [1139:0] ro=0;wire [10239:0] q;wire [1139:0] qo,rto;
 reg [4:0] consumed=0;reg [1139:0] co=0;
 reg [2:0] wv=0;wire [2:0] wr,wt;reg [383:0] we=0;reg [11519:0] wa=0;reg [12287:0] wd=0;
 reg [683:0] wo=0;wire [683:0] wto;wire fault,quarantine;wire [7:0] debt;
 wire [3:0] native_accept,native_ack;wire native_read;
 integer write_events=0,read_events=0,replies=0,retired=0,edges=0;reg checking=0;
 function automatic [31:0] expected(input integer a);
  expected=a==7 ? 32'h40000003 : 32'h3f800000+a;
 endfunction
 ot_ds_shared_native_vm_provider #(.ENABLE(1)) dut(
 .clk(clk),.cold_n(cold_n),.rst_n(rst_n),.abort(abort),.r_v(rv),.r_ready(rr),.r_enable(en),.r_addr(addr),.r_owner(ro),
 .q_v(qv),.q_ready(5'h1f),.q_data(q),.q_owner(qo),.consumed(consumed),.consumed_owner(co),
 .r_retire(retire),.r_retire_ready(5'h1f),.r_retire_owner(rto),.w_v(wv),.w_ready(wr),
 .w_enable(we),.w_addr(wa),.w_data(wd),.w_format_bad(3'b0),.w_owner(wo),
 .w_retire(wt),.w_retire_ready(3'b111),.w_retire_owner(wto),.fault(fault),.quarantined(quarantine),.debt(debt),
 .debug_native_write_accept(native_accept),.debug_native_visible(native_ack),.debug_native_read_accept(native_read));
 always @(posedge clk)if(cold_n)begin
  edges<=edges+1;write_events<=write_events+$countones(native_ack);read_events<=read_events+native_read;
  consumed<=qv;co<=qo;
  for(integer c=0;c<5;c=c+1)begin
   if(rv[c]&&rr[c])begin rv[c]<=0;$display("EVENT grant client=%0d edge=%0d",c,edges);end
   if(retire[c])begin retired<=retired+1;if(rto[c*228+:228]!==ro[c*228+:228])$fatal(1,"wrong retired owner");end
   if(qv[c])begin
    replies<=replies+1;
    if(qo[c*228+:228]!==ro[c*228+:228])$fatal(1,"reply owner mismatch");
    for(integer l=0;l<(c==0 ? 64 : c==1 ? 1 : c==2 ? 16 : c==3 ? 4 : 64);l=l+1)begin
     integer a;
     if(c==0)a=31+l;else if(c==1)a=7;else if(c==2)a=32+l;
     else if(c==3)a=addr[c*120+(l*30)+:30];else a=addr[c*120+(l/16)*30+:30]+l%16;
     if(q[c*2048+l*32+:32]!==expected(a))$fatal(1,"value/order client%0d lane%0d addr%0d got%h expect%h",c,l,a,q[c*2048+l*32+:32],expected(a));
    end
    $display("EVENT reply client=%0d edge=%0d",c,edges);
   end
  end
  if(fault&&!checking)$fatal(1,"unexpected provider fault");
 end
 task write_packet(input integer client,input integer start,input integer n,input integer tag);
  begin
   @(negedge clk);we[client*128+:128]=0;wo[client*228+:228]=tag;
   for(integer i=0;i<n;i=i+1)begin we[client*128+i]=1;wa[client*3840+i*30+:30]=start+i;wd[client*4096+i*32+:32]=32'h3f800000+start+i;end
   wv[client]=1;do @(posedge clk);while(!wr[client]);@(negedge clk);wv[client]=0;
   wait(wt[client]);@(negedge clk);
   if(wto[client*228+:228]!==228'(tag))$fatal(1,"write owner mismatch");
  end
 endtask
 initial begin
  repeat(4)@(negedge clk);cold_n=1;rst_n=1;
  write_packet(1,0,128,11);write_packet(0,0,64,12);write_packet(2,64,64,13);
  @(negedge clk);we[128+:128]=3;wa[3840+:30]=7;wa[3840+30+:30]=7;
  wd[4096+:32]=32'h40000002;wd[4096+32+:32]=32'h40000003;wo[228+:228]=14;wv[1]=1;
  do @(posedge clk);while(!wr[1]);@(negedge clk);wv[1]=0;wait(wt[1]);@(negedge clk);
  if(write_events!=17)$fatal(1,"native visible batch count %0d",write_events);
  en=20'hfffff;en[3:0]=1;en[7:4]=1;en[11:8]=1;
  addr[0+:30]=31;addr[120+:30]=7;addr[240+:30]=32;
  addr[360+:30]=1;addr[390+:30]=7;addr[420+:30]=63;addr[450+:30]=127;
  addr[480+:30]=3;addr[510+:30]=49;addr[540+:30]=64;addr[570+:30]=112;
  for(integer c=0;c<5;c=c+1)ro[c*228+:228]=100+c;
  rv=31;wait(retired==5);@(negedge clk);
  if(debt!=0||fault||quarantine||replies!=5)$fatal(1,"not all owners retired");
  checking=1;rv=1;addr[0+:30]=524288-63;repeat(3)@(negedge clk);
  if(!fault||!quarantine||rr!=0)$fatal(1,"bounds failed open");
  $display("PASS SHARED_NATIVE_PROVIDER clients=8 macros=256 visible_bank_writes=17 replies=5 last_write_wins=1 bounds_refused=1 read_groups=%0d",read_events);$finish;
 end
 initial begin repeat(10000)@(posedge clk);$fatal(1,"directed event bound");end
endmodule
`default_nettype wire
