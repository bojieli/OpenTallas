`timescale 1ns/1ps
module tb_hbm_attn_pv_native_output_h1;
 localparam integer VM_SID=0,VM_BASE=VM_SID*8192;
 reg clk=0;always #2 clk=~clk;reg rst_n=0;
 reg cv=0,ce=0,dv=0,de=0;reg[3:0]cd=0,dh=0;reg[2:0]db=0;reg[15:0]base=0,tag_=0;
 reg[16383:0]data=0;reg[511:0]flags=0;wire[2247:0]wq;
 wire done,recfault,fault;wire[15:0]tagout;
 ot_hbm_attn_pv_native_output_h1 dut(.clk(clk),.bank_clk({4{clk}}),.rst_n(rst_n),.capture_v(cv),.capture_epoch(ce),.capture_dim(cd),.capture_data(data),.capture_flags(flags),
 .drain_v(dv),.drain_epoch(de),.drain_head(dh),.drain_block(db),.drain_base_sector(base),.drain_tag(tag_),
 .wq(wq),.record_done(done),.record_fault(recfault),.record_tag(tagout),.fault(fault));
 integer mut=0,seq=0,c,t,h,k,j,checked=0,commits=0,retired=0,cycle=0,lastcommit=0;
 reg rv=0;reg[15:0]rbase=0;wire[2055:0]rr;wire[15:0]wdone;wire[143:0]status;
 genvar b;
 generate for(b=0;b<8;b=b+1)begin:g_bank
  wire[280:0]word_=wq[b*281+:281] ^ ((mut==1&&b==0)?281'(1<<8):281'd0) ^ ((mut==4&&b==0)?(281'd1<<277):281'd0);
  wire[6*257-1:0]rall;
  ot_vms_bank_static #(.RG(6),.WG(2))u(.clk(clk),.rst_n(rst_n),.bid(3'(b)),.sid(2'(VM_SID)),
   // Explicit dedicated fixed RG3/WG1 ownership. Full programme-SRAM/CP binding
   // is a separate gate; selectors here never depend on observedready/response.
   .rslot_v(1'b1),.rslot(3'd0),.wslot_v(1'b1),.wslot(mut==2?3'd1:3'd0),
   .rq({85'd0,rv,16'(rbase+b)}),.rr(rall),.wq({281'd0,word_}),.wq_done(wdone[b*2+:2]),
   .dq(281'd0),.dq_done(),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(285'd0),.pr(),.status(status[b*18+:18]));
  assign rr[b*257+:257]=rall[0+:257];
 end endgenerate
 function automatic[31:0]word_(input integer n,hd,dim);word_=32'h3f000000^32'(n*99991+hd*777+dim*37037);endfunction
 integer response=0;reg active=0;
 always @(posedge clk)begin
  cycle++;
  #1;
  if(active)begin
   for(integer bb=0;bb<8;bb++)if(status[bb*18+17])$fatal(1,"PV_LOCAL_NATIVE actualbank fault");
   if(wdone[0])begin
    for(integer bb=0;bb<8;bb++)if(!wdone[bb*2])$fatal(1,"PV_LOCAL_NATIVE splitcommit");
    commits++;lastcommit=cycle;
   end
   if(done||recfault)begin
    if(commits!=(retired+1)*8||cycle!=lastcommit)$fatal(1,"PV_LOCAL_NATIVE earlyretire commits%0d seq%0d cycle%0d lastcommit%0d",commits,seq,cycle,lastcommit);
    if(tagout!==16'(100+retired)||done!==(mut!=3)||recfault!==(mut==3))$fatal(1,"PV_LOCAL_NATIVE fault/tag mismatch");
    retired++;
   end
   if(rr[256])begin
    for(integer bb=0;bb<8;bb++)begin
     if(!rr[bb*257+256])$fatal(1,"PV_LOCAL_NATIVE splitresponse");
     for(integer ww=0;ww<8;ww++)begin
      if(rr[bb*257+ww*32+:32]!==word_(seq,(response*64+bb*8+ww)/512,(response*64+bb*8+ww)%512))$fatal(1,"PV_LOCAL_NATIVE readback mismatch seq%0d beat%0d",seq,response);
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
   @(negedge clk);cv=1;ce=0;cd=4'(c);data=0;flags='1;
   for(t=0;t<32;t=t+1)for(h=0;h<16;h=h+1)begin data[(t*16+h)*32+:32]=word_(0,h,t*16+c);if(h==0)flags[t*16+h]=0;end
   if(mut==3&&c==0)flags[0]=1;
  end
  @(negedge clk);cv=0;repeat(2)@(negedge clk);
  for(seq=0;seq<3;seq=seq+1)begin
   for(k=0;k<16;k=k+1)begin
    @(negedge clk);dv=k<8;de=1'(seq%2);dh=0;db=3'(k);base=16'(7016);tag_=16'(100+seq);
    cv=seq<2;ce=1'((seq+1)%2);cd=4'(k);
    if(cv)begin
     data=0;flags='1;
     for(t=0;t<32;t=t+1)for(integer hh=0;hh<16;hh++)begin
      data[(t*16+hh)*32+:32]=word_(seq+1,hh,t*16+k);
      if(hh==0)flags[t*16+hh]=0;
     end
    end
   end
   @(negedge clk);dv=0;cv=0;repeat(10)@(negedge clk);
   if(retired!=seq+1||commits!=(seq+1)*8)$fatal(1,"PV_LOCAL_NATIVE missingH1retire%0d commits%0d",retired,commits);
   response=0;
   for(j=0;j<8;j=j+1)begin @(negedge clk);rv=1;rbase=16'(7016+j*8);end
   @(negedge clk);rv=0;repeat(10)@(negedge clk);
   if(response!=8)$fatal(1,"PV_LOCAL_NATIVE missingresponse%0d",response);
  end
  if(checked!=1536)$fatal(1,"PV_LOCAL_NATIVE accounting%0d",checked);
  $display("PASS PV_LOCAL_NATIVE H1 words1536 actualVMmacros24 serializerSRAM2048 exclusiveSID0_WG0_RG0 fixedcommit3 safe_retire concurrentcapture records3_drain8_capture16 epochs0_1_0 faultcase%0d",mut==3);$finish;
 end
endmodule
