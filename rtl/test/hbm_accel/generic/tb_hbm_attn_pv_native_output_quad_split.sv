`timescale 1ns/1ps
module tb_hbm_attn_pv_native_output_quad_split;
 // cohort a -> quadrant slice sid a (QSID default); each slice has its own attention WG (WG1 here).
 reg clk=0;always #2 clk=~clk;reg rst_n=0;
 reg cv=0,ce=0,dv=0,de=0;reg[3:0]cd=0,dh=0;reg[2:0]db=0;reg[15:0]base=0,tag_=0;
 reg[16383:0]data=0;reg[511:0]flags=0;wire[4*2248-1:0]wq;
 wire done,recfault,fault;wire[15:0]tagout;
 integer mut=0;
 wire[4*2248-1:0]wq0,wq1;
 ot_hbm_attn_pv_native_output_quad_split #(.MUT(0)) dut(.clk(clk),.quad_clk({128{clk}}),.gather_clk({32{clk}}),.rst_n(rst_n),.capture_v(cv),.capture_epoch(ce),.capture_dim(cd),.capture_data(data),.capture_flags(flags),
 .drain_v(dv),.drain_epoch(de),.drain_head(dh),.drain_block(db),.drain_base_sector(base),.drain_tag(tag_),
 .wq(wq0),.record_done(done0),.record_fault(recfault0),.record_tag(tagout0),.fault(fault0));
 // Mutant 5: quadrant-binding swap (quadrant 1 data into quadrant 0's write group).
 ot_hbm_attn_pv_native_output_quad_split #(.MUT(1)) dut_m(.clk(clk),.quad_clk({128{clk}}),.gather_clk({32{clk}}),.rst_n(rst_n),.capture_v(cv),.capture_epoch(ce),.capture_dim(cd),.capture_data(data),.capture_flags(flags),
 .drain_v(dv),.drain_epoch(de),.drain_head(dh),.drain_block(db),.drain_base_sector(base),.drain_tag(tag_),
 .wq(wq1),.record_done(done1),.record_fault(recfault1),.record_tag(tagout1),.fault(fault1));
 wire done0,done1,recfault0,recfault1,fault0,fault1;wire[15:0]tagout0,tagout1;
 assign wq=mut==5?wq1:wq0;assign done=mut==5?done1:done0;assign recfault=mut==5?recfault1:recfault0;
 assign tagout=mut==5?tagout1:tagout0;assign fault=mut==5?fault1:fault0;
 integer seq=0,c,t,h,k,j,checked=0,commits=0,retired=0,cycle=0,lastcommit=0;
 reg[3:0]rv=0;reg[15:0]rbase=0;wire[4*2056-1:0]rr;wire[4*24-1:0]wdone;wire[4*144-1:0]status;
 genvar q,b;
 generate for(q=0;q<4;q=q+1)begin:g_slice for(b=0;b<8;b=b+1)begin:g_bank
  wire[280:0]word_=wq[q*2248+b*281+:281] ^ ((mut==1&&b==0)?281'(1<<8):281'd0) ^ ((mut==4&&b==0)?(281'd1<<277):281'd0);
  wire[7*257-1:0]rall;
  ot_vms_bank_static #(.RG(7),.WG(3))u(.clk(clk),.rst_n(rst_n),.bid(3'(b)),.sid(2'(q)),
   // Each quadrant slice: dedicated fixed attention RG3/WG1 ownership (static selectors).
   .rslot_v(1'b1),.rslot(3'd3),.wslot_v(1'b1),.wslot(mut==2?3'd2:3'd1),
   .rq({51'd0,rv[q],16'(rbase+b),51'd0}),.rr(rall),.wq({281'd0,word_,281'd0}),.wq_done(wdone[q*24+b*3+:3]),
   .dq(281'd0),.dq_done(),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(285'd0),.pr(),.status(status[q*144+b*18+:18]));
  assign rr[q*2056+b*257+:257]=rall[3*257+:257];
 end end endgenerate
 function automatic[31:0]word_(input integer n,hd,dim);word_=32'h3f000000^32'(n*99991+hd*777+dim*37037);endfunction
 integer response=0;reg active=0;
 always @(posedge clk)begin
  cycle++;
  #1;
  if(active)begin
   for(integer bb=0;bb<32;bb++)if(status[bb*18+17])$fatal(1,"PV_LOCAL_NATIVE actualbank fault");
   for(integer qq=0;qq<4;qq++)if(wdone[qq*24+1])begin
    for(integer bb=0;bb<8;bb++)if(!wdone[qq*24+bb*3+1])$fatal(1,"PV_LOCAL_NATIVE splitcommit");
    commits++;lastcommit=cycle;
   end
   if(done||recfault)begin
    if(commits!=(retired+1)*128||cycle!=lastcommit)$fatal(1,"PV_LOCAL_NATIVE earlyretire commits%0d seq%0d cycle%0d lastcommit%0d",commits,seq,cycle,lastcommit);
    if(tagout!==16'(100+retired)||done!==(mut!=3)||recfault!==(mut==3))$fatal(1,"PV_LOCAL_NATIVE fault/tag mismatch");
    retired++;
   end
   for(integer qq=0;qq<4;qq++)if(rr[qq*2056+256])begin
    for(integer bb=0;bb<8;bb++)begin
     if(!rr[qq*2056+bb*257+256])$fatal(1,"PV_LOCAL_NATIVE splitresponse");
     for(integer ww=0;ww<8;ww++)begin
      if(rr[qq*2056+bb*257+ww*32+:32]!==word_(seq,(response*64+bb*8+ww)/512,(response*64+bb*8+ww)%512))$fatal(1,"PV_LOCAL_NATIVE readback mismatch seq%0d beat%0d quadrant%0d",seq,response,qq);
      checked++;
     end
    end
    response++;
   end
  end
 end
 initial begin
  void'($value$plusargs("MUT=%d",mut));repeat(5)@(negedge clk);rst_n=1;active=1;
  // Initialrecord capture, then continuous128edge drains for three records;
  // nextrecord capture occursduring priorrecorddrain andepoch0 is reused.
  for(c=0;c<16;c=c+1)begin
   @(negedge clk);cv=1;ce=0;cd=4'(c);data=0;flags=0;
   for(t=0;t<32;t=t+1)for(h=0;h<16;h=h+1)data[(t*16+h)*32+:32]=word_(0,h,t*16+c);
   if(mut==3&&c==0)flags[0]=1;
  end
  @(negedge clk);cv=0;repeat(2)@(negedge clk);
  for(seq=0;seq<3;seq=seq+1)begin
   for(h=0;h<16;h=h+1)for(k=0;k<8;k=k+1)begin
    @(negedge clk);dv=1;de=1'(seq%2);dh=4'(h);db=3'(k);base=16'({h[3],h[1]}*8192+seq*2048);tag_=16'(100+seq);
    cv=(seq<2&&h*8+k<16);ce=1'((seq+1)%2);cd=4'(h*8+k);
    if(cv)begin
     data=0;flags=0;
     for(t=0;t<32;t=t+1)for(integer hh=0;hh<16;hh++)data[(t*16+hh)*32+:32]=word_(seq+1,hh,t*16+h*8+k);
    end
   end
  end
  @(negedge clk);dv=0;cv=0;repeat(10)@(negedge clk);
  if(retired!=3||commits!=384)$fatal(1,"PV_LOCAL_NATIVE missingconcurrentretire%0d commits%0d",retired,commits);
  for(seq=0;seq<3;seq=seq+1)begin
   response=0;
   for(j=0;j<128;j=j+1)begin @(negedge clk);rv=4'b1<<{j[6],j[4]};rbase=16'({j[6],j[4]}*8192+seq*2048+j*8);end
   @(negedge clk);rv=0;repeat(10)@(negedge clk);
   if(response!=128)$fatal(1,"PV_LOCAL_NATIVE missingresponse%0d",response);
  end
  if(checked!=24576)$fatal(1,"PV_LOCAL_NATIVE accounting%0d",checked);
  $display("PASS PV_LOCAL_NATIVE PERQUADRANT words24576 slices4 actualVMmacros96 serializerSRAM2048 quad128_tilereg128_gather32 plus3read_plus1write WG1_RG3 fixedcommit3 safe_retire concurrentcapture backtobackrecords3 epochs0_1_0 faultcase%0d",mut==3);$finish;
 end
endmodule
