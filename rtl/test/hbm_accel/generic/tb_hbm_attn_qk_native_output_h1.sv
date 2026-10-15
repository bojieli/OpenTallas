`timescale 1ns/1ps
module tb_hbm_attn_qk_native_output_h1;
 reg clk=0;always #2 clk=~clk;reg rst_n=0;
 reg cv=0,ce=0,ct=0,dv=0,de=0,dt=0;
 reg[15:0]row=0,base=0;reg[1:0]mask=3;
 reg[1023:0]data=0;reg[31:0]flags=0;reg[3:0]head=0,block_=0;
 wire fault;wire[2247:0]wq;wire done,recfault;wire[15:0]tagout;
 ot_hbm_attn_qk_native_output_h1 dut(.clk(clk),.rst_n(rst_n),.capture_v(cv),.capture_epoch(ce),.capture_T640(ct),
 .capture_row(row),.capture_mask(mask),.capture_data(data),.capture_flags(flags),.drain_v(dv),.drain_epoch(de),.drain_T640(dt),
 .drain_head(head),.drain_block(block_),.drain_base_sector(base),.drain_tag(16'(100+seq)),.wq(wq),.record_done(done),.record_fault(recfault),.record_tag(tagout),.fault(fault));
 integer mut=0,n,T=128,seq=0,edge_,h,l,r,checks=0,beats=0;reg active=0;
 reg rv=0;reg[15:0]rbase=0;wire[2055:0]rr;wire[15:0]wdone;wire[143:0]status;
 integer commits=0,retired=0,cycle=0,lastcommit=0,expected_commits=0,response=0;
 genvar b;
 generate for(b=0;b<8;b=b+1)begin:g_bank
  wire[280:0]word_=wq[b*281+:281]^((mut==4&&b==0)?281'd256:281'd0)^((mut==6&&b==0)?(281'd1<<277):281'd0);
  wire[6*257-1:0]rall;
  ot_vms_bank_static #(.RG(6),.WG(2))u(.clk(clk),.rst_n(rst_n),.bid(3'(b)),.sid(2'd0),
   .rslot_v(1'b1),.rslot(3'd0),.wslot_v(1'b1),.wslot(mut==5?3'd1:3'd0),
   .rq({85'd0,rv,16'(rbase+b)}),.rr(rall),.wq({281'd0,word_}),.wq_done(wdone[b*2+:2]),
   .dq(281'd0),.dq_done(),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(285'd0),.pr(),.status(status[b*18+:18]));
  assign rr[b*257+:257]=rall[0+:257];
 end endgenerate
 function automatic[31:0]value_(input integer s,hd,rr_);value_=32'h3f000000^32'(s*71237+hd*997+rr_*37037);endfunction
 function automatic flag_(input integer s,hd,rr_);flag_=(hd!=0)||(mut==3&&s==0&&hd==0&&rr_==0);endfunction
 always @(posedge clk)begin
  cycle++;
  #1;
  if(active)begin
   for(integer bb=0;bb<8;bb++)if(status[bb*18+17])$fatal(1,"QK_NATIVE actualbank fault");
   if(wdone[0])begin
    for(integer bb=0;bb<8;bb++)if(!wdone[bb*2])$fatal(1,"QK_NATIVE splitcommit");
    commits++;lastcommit=cycle;
   end
   if(done||recfault)begin
    if(commits!=expected_commits||cycle!=lastcommit)$fatal(1,"QK_NATIVE earlyretire commits%0d expected%0d",commits,expected_commits);
    if(tagout!==16'(100+seq)||done!==!(mut>=1&&mut<=3)||recfault!==(mut>=1&&mut<=3))$fatal(1,"QK_NATIVE fault/tag mismatch");
    retired++;
   end
   if(rr[256])begin
    for(integer bb=0;bb<8;bb++)begin
     if(!rr[bb*257+256])$fatal(1,"QK_NATIVE splitresponse");
     for(integer ww=0;ww<8;ww++)begin
      if(rr[bb*257+ww*32+:32]!==value_(seq,(response*64+bb*8+ww)/T,(response*64+bb*8+ww)%T))$fatal(1,"QK_NATIVE readback mismatch");
      checks++;
     end
    end
    response++;
   end
  end
 end
 initial begin
  void'($value$plusargs("MUT=%d",mut));repeat(5)@(negedge clk);rst_n=1;active=1;
  for(n=0;n<2;n=n+1)begin
   T=n==0?128:640;
   for(seq=0;seq<3;seq=seq+1)begin
    expected_commits+=T/64;
    for(edge_=0;edge_<T/2+16;edge_=edge_+1)begin
     @(negedge clk);cv=edge_<T/2;ce=1'(seq%2);ct=n!=0;row=16'(2*edge_);mask=3;data=0;flags=0;
     if(cv)for(l=0;l<2;l=l+1)for(h=0;h<16;h=h+1)begin
      data[(l*16+h)*32+:32]=value_(seq,h,edge_*2+l);flags[l*16+h]=flag_(seq,h,edge_*2+l);
     end
     if(mut==1&&cv&&edge_==8)row=16'(2*edge_+2);
     if(mut==2&&cv&&edge_==8)mask=1;
     
     dv=edge_>=32&&((edge_-32)%32)==0;de=ce;dt=ct;head=0;block_=4'((edge_-32)/32);base=16'(6736);
    end
    @(negedge clk);cv=0;dv=0;repeat(8)@(negedge clk);
    if(retired!=n*3+seq+1)$fatal(1,"QK_NATIVE missingretire");
    if(mut==1||mut==2)begin $display("PASS QK_NATIVE H1 actualcapture phase fault safe retirement MUT%0d",mut);$finish;end
    response=0;
    for(integer jj=0;jj<T/64;jj++)begin @(negedge clk);rv=1;rbase=16'(6736+jj*8);end
    @(negedge clk);rv=0;repeat(10)@(negedge clk);
    if(response!=T/64)$fatal(1,"QK_NATIVE missingresponse");
   end
  end
  if(checks!=2304||commits!=36)$fatal(1,"QK_NATIVE wrong counts%0d/%0d",checks,commits);
  $display("PASS QK_NATIVE H1 T128/T640 epochs0,1,0 words%0d commits%0d actualSID0 exclusiveWG0_RG0 fixedcommit3 safe_retire faultcase%0d",checks,commits,mut==3);$finish;
 end
endmodule
