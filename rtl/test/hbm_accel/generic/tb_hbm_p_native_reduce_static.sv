`timescale 1ns/1ps
module tb_hbm_p_native_reduce_static;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,fill_slot=0,command_v=0,source_operand=0,publish_slot=0;
 reg[3:0]fill_burst=0;reg[2055:0]rr=0;
 reg[9:0]source_word=0,a=0,b=0,d=0;reg[2:0]op=0;
 reg[31:0]cx=0,tag=0,expected_tag=0;reg[15:0]sector=0;reg[2:0]word_index=0;
 wire[2247:0]wq;wire sv,fault;wire[31:0]st,sy;wire[15:0]sb;
 ot_hbm_p_native_reduce_static dut(clk,rst_n,fill_slot,fill_burst,rr,command_v,source_operand,
 source_word,op,a,b,d,cx,tag,publish_slot,expected_tag,sector,word_index,wq,sv,st,sy,sb,fault);
 integer cf,ef,ff,cc,ec,fc,rc,co,ca,cb,cd,ct,sw,so,et,eb,fr,fkind,ft;
 reg[31:0]xx,ey;
 integer k=0,seen=0,published=0,last_c=0,previous_scalar=0,previous_tag=0;
 integer mutant=0;
 reg[31:0]previous_y;
 string dir;
 task next_command;rc=$fscanf(cf,"%d %d %d %d %d %d %d %d %d\n",cc,co,ca,cb,cd,xx,ct,sw,so);if(rc!=9)cc=2147483647;endtask
 task next_expected;rc=$fscanf(ef,"%d %d %d %d\n",ec,et,ey,eb);if(rc!=4)ec=2147483647;endtask
 task next_fill;rc=$fscanf(ff,"%d %d %d %d\n",fc,fr,fkind,ft);if(rc!=4)fc=2147483647;endtask
 initial begin
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"missing fixture directory");
  mutant=$test$plusargs("MUTANT_SOURCE");
  cf=$fopen({dir,"/commands.txt"},"r");ef=$fopen({dir,"/expected.txt"},"r");ff=$fopen({dir,"/fills.txt"},"r");
  next_command();next_expected();next_fill();
  repeat(3)@(negedge clk);rst_n=1;
  while(cc!=2147483647||ec!=2147483647||k<last_c+20)begin
   fill_slot=k>=fc&&k<fc+fr/64;fill_burst=4'(k-fc);rr=0;
   if(fill_slot)for(integer bank=0;bank<8;bank=bank+1)begin
    rr[257*bank+256]=1;
    for(integer w=0;w<8;w=w+1)rr[257*bank+32*w+:32]=fkind==1?32'h3f800000:
     32'h3f800000+32'(((k-fc)*64+bank*8+w)*8192);
   end
   command_v=k==cc;
   if(command_v)begin op=3'(co);a=10'(ca);b=10'(cb);d=10'(cd);cx=xx;tag=32'(ct);
    source_operand=1'(so);source_word=10'((mutant&&so)?0:sw);last_c=k;next_command();end
   else source_operand=0;
   publish_slot=1'(previous_scalar);expected_tag=32'(previous_tag);
   sector=16'(256+previous_tag/8);word_index=3'(previous_tag%8);
   @(posedge clk);#1;
   if(fault)$fatal(1,"native join fault cycle %0d",k);
   if(sv!=(k==ec))$fatal(1,"scalar cycle %0d expected %0d",k,ec);
   if(sv)begin
    if(st!==32'(et)||sy!==ey||sb!==16'(eb))$fatal(1,"scalar arithmetic tag%0d y%h expected%h",st,sy,ey);
    seen=seen+1;next_expected();
   end
   if(previous_scalar)begin
    if(wq[281*sector[2:0]+:281]!=={1'b1,sector,{8{previous_y}},8'b1<<word_index})$fatal(1,"masked VM publication");
    published=published+1;
   end
   previous_scalar=int'(sv);previous_tag=int'(st);previous_y=sy;
   @(negedge clk);k=k+1;
   if(k==fc+fr/64)next_fill();
  end
  if(seen!=64||published!=64)$fatal(1,"incomplete native fullshape proof");
  $display("PASS T128/T640 H16 actual native SRAM/reducer/publisher:64scalars %0dcycles",k);$finish;
 end
endmodule
