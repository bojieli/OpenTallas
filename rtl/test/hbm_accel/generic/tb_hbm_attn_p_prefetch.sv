`timescale 1ns/1ps
module tb_hbm_attn_p_prefetch;
 reg clk=0;always #2 clk=~clk;reg rst_n=0;
 reg fv=0,fe=0,rv=0,re=0;reg[3:0]fh=0,fb=0;reg[15:0]base=0,rows=128;reg[9:0]row_=0;
 wire[135:0]rq;wire[2055:0]rr,rawrr,mappedrr;reg[2055:0]late;
 wire[1023:0]pw;wire pv,fault;reg preload=1;reg[2247:0]prewq=0;
 integer mut=0,ep,h,s,b,w,r,T,checked=0;wire[143:0]status;
 always @(posedge clk)late<=rawrr;
 assign rr=mut==3?late:rawrr;
 for(genvar k=0;k<8;k=k+1)assign mappedrr[k*257+:257]=rr[(k^((mut==1)?1:0))*257+:257];
 ot_hbm_attn_p_prefetch dut(.clk(clk),.rst_n(rst_n),.fetch_v(fv),.fetch_epoch(fe),.fetch_head(fh^((mut==2)?4'd1:4'd0)),.fetch_burst(fb),
 .fetch_base_sector(base),.profile_rows(rows),.rq(rq),.rr(mappedrr),.read_v(rv),.read_epoch(re),.read_row(row_),.p_v(pv),.p_w(pw),.fault(fault));
 for(genvar k=0;k<8;k=k+1)begin:g_bank
  wire[7*257-1:0]allrr;
  ot_vms_bank_static #(.RG(7),.WG(3))bank(.clk(clk),.rst_n(rst_n),.bid(3'(k)),.sid(2'd0),
   .rslot_v(1'b1),.rslot(3'd3),.wslot_v(1'b1),.wslot(3'd0),
   .rq({51'd0,preload?17'd0:rq[k*17+:17],51'd0}),.rr(allrr),
   .wq({562'd0,preload?prewq[k*281+:281]:281'd0}),.wq_done(),.dq(281'd0),.dq_done(),.kq(281'd0),.kq_done(),
   .xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(285'd0),.pr(),.status(status[k*18+:18]));
  assign rawrr[k*257+:257]=allrr[3*257+:257];
 end
 function automatic[15:0]value(input integer e,hd,row);value=16'h3b00+16'(e*4096+hd*131+row*3);endfunction
 reg active=0;
 always @(posedge clk)begin
  #1;
  if(active&&fault)$fatal(1,"P_PREFETCH source/phase fault");
  if(active&&pv)for(integer rr_=0;rr_<4;rr_=rr_+1)for(integer hh=0;hh<16;hh=hh+1)begin
   if(pw[(rr_*16+hh)*16+:16]!==value(re,hh,int'(row_)+rr_))$fatal(1,"P_PREFETCH mapped SRAM mismatch ep%0d row%0d h%0d",re,row_,hh);
   checked++;
  end
 end
 initial begin
  void'($value$plusargs("MUT=%d",mut));repeat(8)@(negedge clk);rst_n=1;
  for(ep=0;ep<2;ep=ep+1)for(h=0;h<16;h=h+1)for(s=0;s<10;s=s+1)begin
   @(negedge clk);prewq=0;
   for(b=0;b<8;b=b+1)begin
    prewq[b*281+:281]={1'b1,16'(ep*2048+h*80+s*8+b),256'd0,8'hff};
    for(w=0;w<8;w=w+1)prewq[b*281+8+w*32+:32]={value(ep,h,s*64+b*8+w),16'((mut==4&&ep==0&&h==0&&s==0&&b==0&&w==0)?1:0)};
   end
  end
  @(negedge clk);prewq=0;repeat(8)@(negedge clk);preload=0;active=1;
  for(T=128;T<=640;T=T+512)begin
   rows=16'(T);
   for(ep=0;ep<2;ep=ep+1)begin
    for(h=0;h<16;h=h+1)for(s=0;s<T/64;s=s+1)begin
     @(negedge clk);fv=1;fe=1'(ep);fh=4'(h);fb=4'(s);base=16'(ep*2048+h*80+s*8);
    end
    @(negedge clk);fv=0;repeat(10)@(negedge clk);
    for(r=0;r<T;r=r+4)begin @(negedge clk);rv=1;re=1'(ep);row_=10'(r);end
    @(negedge clk);rv=0;repeat(2)@(negedge clk);
   end
  end
  if(checked!=24576)$fatal(1,"P_PREFETCH accounting%0d",checked);
  $display("PASS P_PREFETCH fullH16_T128_T640 epochs2 values24576 actualP_SRAM128 actualVM_SRAM24 nativeRG3of7");$finish;
 end
endmodule
