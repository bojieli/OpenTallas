`timescale 1ns/1ps
module tb_hbm_attn_qk_score_serializer;
 reg clk=0;always #2 clk=~clk;reg rst_n=0;
 reg cv=0,ce=0,ct=0,dv=0,de=0,dt=0;
 reg[15:0]row=0,base=0;reg[1:0]mask=3;
 reg[1023:0]data=0;reg[31:0]flags=0;reg[3:0]head=0,block_=0;
 wire wv,fault;wire[2047:0]wd;wire[63:0]wf;wire[15:0]ws;
 ot_hbm_attn_qk_score_serializer dut(.clk(clk),.rst_n(rst_n),.capture_v(cv),.capture_epoch(ce),.capture_T640(ct),
 .capture_row(row),.capture_mask(mask),.capture_data(data),.capture_flags(flags),.drain_v(dv),.drain_epoch(de),.drain_T640(dt),
 .drain_head(head),.drain_block(block_),.drain_base_sector(base),.write_v(wv),.write_data(wd),.write_flags(wf),.write_base_sector(ws),.fault(fault));
 integer mut=0,n,T,seq,edge_,h,l,r,checks=0,beats=0;reg active=0;
 reg expv=0;reg[3:0]eh,eb;reg[15:0]es;integer et,eseq;
 function automatic[31:0]value_(input integer s,hd,rr);value_=32'h3f000000^32'(s*71237+hd*997+rr*37037);endfunction
 function automatic flag_(input integer s,hd,rr);flag_=((s*17+hd*7+rr)%23)==0;endfunction
 always @(posedge clk)begin
  expv=dv;eh=head;eb=block_;es=base;et=T;eseq=seq;
  #1;
  if(active)begin
   if(fault)$fatal(1,"QK_SCORE protocol fault");
   if(wv!==expv)$fatal(1,"QK_SCORE valid alignment");
   if(wv)begin
    if(ws!==16'(int'(es)+int'(eh)*(et/8)+int'(eb)*8))$fatal(1,"QK_SCORE sector mapping");
    for(integer d=0;d<64;d=d+1)begin
     if(wd[d*32+:32]!==value_(eseq,int'(eh),int'(eb)*64+d))$fatal(1,"QK_SCORE payload mismatch seq%0d head%0d row%0d",eseq,eh,int'(eb)*64+d);
     if(wf[d]!==flag_(eseq,int'(eh),int'(eb)*64+d))$fatal(1,"QK_SCORE flags mismatch");
     checks++;
    end
    beats++;
   end
  end
 end
 initial begin
  void'($value$plusargs("MUT=%d",mut));repeat(5)@(negedge clk);rst_n=1;active=1;
  for(n=0;n<2;n=n+1)begin
   T=n==0?128:640;
   for(seq=0;seq<3;seq=seq+1)begin
    for(edge_=0;edge_<T/2+16;edge_=edge_+1)begin
     @(negedge clk);cv=edge_<T/2;ce=1'(seq%2);ct=n!=0;row=16'(2*edge_);mask=3;data=0;flags=0;
     if(cv)for(l=0;l<2;l=l+1)for(h=0;h<16;h=h+1)begin
      data[(l*16+h)*32+:32]=value_(seq,h,edge_*2+l);flags[l*16+h]=flag_(seq,h,edge_*2+l);
     end
     if(mut==1&&cv&&edge_==8)row=16'(2*edge_+2);
     if(mut==2&&cv&&edge_==8)mask=1;
     if(mut==3&&cv&&edge_==8)flags[0]=~flags[0];
     dv=edge_>=32&&((edge_-32)%32)<16;de=ce;dt=ct;head=4'((edge_-32)%32);block_=4'((edge_-32)/32);base=16'(24576+seq*2048);
    end
    @(negedge clk);cv=0;dv=0;repeat(2)@(negedge clk);
   end
  end
  if(checks!=36864||beats!=576)$fatal(1,"QK_SCORE wrong counts%0d/%0d",checks,beats);
  $display("PASS QK_SCORE H16 T128/T640 epochs0,1,0 words%0d beats%0d realSRAM256 maskedcapture/overlap/status",checks,beats);$finish;
 end
endmodule
