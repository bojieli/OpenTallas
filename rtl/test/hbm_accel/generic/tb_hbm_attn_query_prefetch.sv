`timescale 1ns/1ps
module tb_hbm_attn_query_prefetch;
 reg clk=0;always #1 clk=~clk;reg rst_n=0;
 reg fv=0,fe=0,rv=0,re=0;reg[3:0]fh=0,rh=0;reg[2:0]fb=0;reg[15:0]base=0;
 wire[135:0]rq;wire[2055:0]rrbank;reg[2055:0]rrdelay;wire[2055:0]rr;
 wire[8191:0]qw;wire qv,fault;reg preload=1;reg[2247:0]pwq=0;
 integer mut=0,checked=0;wire[143:0]status;
 always @(posedge clk)rrdelay<=rrbank;
 assign rr=mut==3?rrdelay:rrbank;
 // Mutation runs use actual transformed response/address pins, not oracle changes.
 wire[2055:0]mappedrr;
 for(genvar b=0;b<8;b=b+1)assign mappedrr[b*257+:257]=rr[(b^((mut==1)?1:0))*257+:257];
 ot_hbm_attn_query_prefetch dut(.clk(clk),.rst_n(rst_n),.fetch_v(fv),.fetch_epoch(fe),
  .fetch_head(fh^((mut==2)?4'd1:4'd0)),.fetch_burst(fb),.fetch_base_sector(base),.rq(rq),.rr(mappedrr),
  .read_v(rv),.read_epoch(re),.read_head(rh),.q_v(qv),.q_w(qw),.fault(fault));
 for(genvar b=0;b<8;b=b+1)begin:banks
  wire[16:0]brq=preload?17'd0:rq[b*17+:17];wire[280:0]bwq=preload?pwq[b*281+:281]:281'd0;
  ot_vms_bank_static #(.RG(1),.WG(1))bank(.clk(clk),.rst_n(rst_n),.bid(3'(b)),.sid(2'd0),
   .rslot_v(brq[16]),.rslot(1'd0),.wslot_v(bwq[280]),.wslot(3'd0),.rq(brq),.rr(rrbank[b*257+:257]),
   .wq(bwq),.wq_done(),.dq(281'd0),.dq_done(),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),
   .xq2(276'd0),.xq2_done(),.eg(),.pq(285'd0),.pr(),.status(status[b*18+:18]));
 end
 function automatic[15:0]word(input integer ep,h,e);
  word=16'h3b00+16'(ep*4096+h*131+e*3);
 endfunction
 integer ep,h,s,b,w,idx;
 initial begin
  void'($value$plusargs("MUT=%d",mut));repeat(8)@(negedge clk);rst_n=1;
  for(ep=0;ep<2;ep++)for(h=0;h<16;h++)for(s=0;s<8;s++)begin
   @(negedge clk);pwq=0;
   for(b=0;b<8;b++)begin
    pwq[b*281+:281]={1'b1,16'(ep*1024+h*64+s*8+b),256'd0,8'hff};
    for(w=0;w<8;w++)pwq[b*281+8+w*32+:32]={word(ep,h,s*64+b*8+w),16'((mut==4&&ep==0&&h==0&&s==0&&b==0&&w==0)?1:0)};
   end
  end
  @(negedge clk);pwq=0;repeat(8)@(negedge clk);preload=0;
  for(ep=0;ep<2;ep++)for(h=0;h<16;h++)for(s=0;s<8;s++)begin
   fv=1;fe=1'(ep);fh=4'(h);fb=3'(s);base=16'(ep*1024+h*64+s*8);@(negedge clk);
  end
  fv=0;repeat(12)@(negedge clk);
  if(fault)$fatal(1,"query-prefetch fixed response phase fault");
  for(ep=0;ep<2;ep++)for(h=0;h<16;h++)begin
   rv=1;re=1'(ep);rh=4'(h);@(negedge clk);
   if(!qv)$fatal(1,"query-prefetch missing scheduled head");
   for(idx=0;idx<512;idx++)begin
    if(qw[idx*16+:16]!==word(ep,h,idx))$fatal(1,"query-prefetch mapped SRAM mismatch epoch%0d head%0d element%0d",ep,h,idx);
    checked++;
   end
  end
  rv=0;@(negedge clk);
  $display("PASS ATT_QUERY_PREFETCH heads=32 words=%0d fetch_edges=256 query_macros=64 VM_macros=24 source_FP32_to_BF16=1",checked);$finish;
 end
endmodule
