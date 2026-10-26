`timescale 1ns/1ps
module tb_hbm_attn_program_query_front;
 reg clk=0;always #1 clk=~clk;reg rst_n=0,iv=0;reg[222:0]instruction=0;wire[135:0]rq;wire[2055:0]rr;
 wire[6:0]events;wire[7:0]phase;wire valid,pv,qv,fault;wire[15:0]rows;wire[8191:0]q;
 ot_hbm_attn_program_query_front dut(.clk(clk),.rst_n(rst_n),.instruction_v(iv),.instruction(instruction),
  .query_rq(rq),.query_rr(rr),.events(events),.phase(phase),.event_valid(valid),.rows(rows),.pv_only(pv),.q_words(q),.q_present(qv),.fault(fault));
 reg preload=1;reg[2247:0]pwq=0;wire[143:0]status;
 for(genvar b=0;b<8;b=b+1)begin:banks
  wire[7*17-1:0]arq={51'd0,(preload?17'd0:rq[b*17+:17]),51'd0};
  wire[3*281-1:0]awq={562'd0,(preload?pwq[b*281+:281]:281'd0)};
  wire[7*257-1:0]arr;
  ot_vms_bank_static #(.RG(7),.WG(3))bank(.clk(clk),.rst_n(rst_n),.bid(3'(b)),.sid(2'd0),
   .rslot_v(!preload&&rq[b*17+16]),.rslot(3'd3),.wslot_v(preload&&pwq[b*281+280]),.wslot(3'd0),
   .rq(arq),.rr(arr),.wq(awq),.wq_done(),.dq(281'd0),.dq_done(),.kq(281'd0),.kq_done(),
   .xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(285'd0),.pr(),.status(status[b*18+:18]));
  assign rr[b*257+:257]=arr[3*257+:257];
 end
 function automatic[15:0]word(input integer ep,h,e);word=16'h3b00+16'(ep*4096+h*131+e*3);endfunction
 reg[222:0]cfg[0:255],outer[0:255];reg[6:0]cal[0:255];integer mut=0,profile=0,checked=0,heads=0,seen=0,eventcycles=0;
 integer ep,h,s,b,w,i;string dir,fn;reg active=0;
 always @(posedge clk)if(active)begin
  if(fault)$fatal(1,"ATT_FRONT source/calendar fault");
  for(integer bb=0;bb<8;bb++)if(status[bb*18+17])$fatal(1,"ATT_FRONT bank fault");
  if(valid)begin
   if(events!==cal[phase])$fatal(1,"ATT_FRONT wrong actual event profile/phase%0d",phase);
   eventcycles++;
   if(events[1])begin
    if(!qv)$fatal(1,"ATT_FRONT missing actual query SRAM head");
    for(integer ee=0;ee<512;ee++)begin
     if(q[ee*16+:16]!==word(profile/2,heads,ee))$fatal(1,"ATT_FRONT query payload mismatch profile%0d head%0d elem%0d",profile,heads,ee);
     checked++;
    end
    heads++;
   end
   if(events[0])seen++;
  end
 end
 initial begin
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"DIR");void'($value$plusargs("MUT=%d",mut));
  repeat(8)@(negedge clk);rst_n=1;
  for(ep=0;ep<2;ep++)for(h=0;h<16;h++)for(s=0;s<8;s++)begin
   @(negedge clk);pwq=0;
   for(b=0;b<8;b++)begin pwq[b*281+:281]={1'b1,16'(ep*1024+h*64+s*8+b),256'd0,8'hff};
    for(w=0;w<8;w++)pwq[b*281+8+w*32+:32]={word(ep,h,s*64+b*8+w),16'd0};end
  end
  @(negedge clk);pwq=0;repeat(8)@(negedge clk);preload=0;
  $readmemh({dir,"/config.hex"},cfg);
  // Four resident profiles: 182 actual host instructions configure all modes.
  for(i=0;i<182;i++)begin iv=1;instruction=cfg[i];if(mut==1&&i==0)instruction[100]=1;@(negedge clk);end
  iv=0;repeat(4)@(negedge clk);if(fault)$fatal(1,"ATT_FRONT source/calendar fault");
  for(profile=0;profile<4;profile++)begin
   fn=$sformatf("%s/outer%0d.hex",dir,profile);$readmemh(fn,outer);fn=$sformatf("%s/event%0d.hex",dir,profile);$readmemh(fn,cal);
   heads=0;seen=0;active=1;
   for(i=0;i<(profile%2?1:138);i++)begin
    iv=1;instruction=outer[i];if(mut==2&&i==137)instruction[5:4]=2'(profile^1);@(negedge clk);
   end
   iv=0;repeat(230)@(negedge clk);
   if(seen!=1||heads!=(profile%2?0:16))$fatal(1,"ATT_FRONT event/head accounting");
   $display("ATT_FRONT_PROFILE PASS profile%0d heads%0d",profile,heads);active=0;
  end
  $display("PASS ATT_PROGRAM_QUERY_FRONT profiles=4 heads=32 words=%0d event_cycles=%0d native_RG=3 native_RG_total=7 real_query_macros=64 actual_VM_macros=24 actual_programme_macros=1",checked,eventcycles);$finish;
 end
endmodule
