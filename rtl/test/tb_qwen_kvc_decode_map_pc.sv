`timescale 1ns/1ps
module tb_qwen_kvc_decode_map_pc;
 parameter integer NEG=0, KV_MAP=1;
 reg [6:0] i_port;
 `include "ot_qwen_kv_map_m.svh"
 reg clk=0; always #5 clk=~clk;
 reg rst_n=0,i_v=0,o_cr=0;
 reg [255:0] i_data;
 reg [16:0] i_sec,i_expected;
 reg [12:0] i_pos;
 reg [7:0] i_row,i_layer;
 reg [10:0] i_count,i_limit;
 reg i_active,i_done;
 wire i_cr,o_v,fault,o_bad,o_drop,o_isk,o_tail;
 wire [255:0] o_data;
 wire [10:0] o_tile0,o_tile1;
 wire [6:0] o_loc0,o_loc1;
 wire [1:0] o_sel0,o_sel1,o_n;
 wire [3:0] o_tail_lanes;
 ot_qwen_kvc_decode_map_pc #(.ENABLE(1),.KV_MAP(KV_MAP)) dut(.*);
 reg [16:0] secq[0:200000]; reg [12:0] posq[0:200000];
 reg [255:0] dataq[0:200000]; reg badq[0:200000];
 integer sent=0,got=0,credit=16,pending=0,tick=0;
 integer a,t,d,h,pp,q,loc,tile,half,n;
 reg bad,drop; reg [127:0] lm;
 reg [511:0] want_data,want_mask,actual_data,actual_mask;
 task fail(input [255:0] msg);
 begin $display("FAIL kvc_mapped %s sent=%0d got=%0d",msg,sent,got); $fatal(1); end
 endtask
 always @(posedge clk) if(rst_n) begin
  if(i_v) begin
   secq[sent]=i_expected; posq[sent]=i_pos; dataq[sent]=i_data;
   badq[sent]=!i_active || i_done || i_count>=i_limit || i_sec!=i_expected || i_row!=i_layer;
   sent=sent+1;
  end
  if(o_v) begin
   if(got>=sent) fail("unexpected response");
   a=secq[got]*2; bad=badq[got]; drop=(a>=131072 && ((a-131072)>>3 &8191)>=posq[got]);
   n=bad ? 0 : a<131072 ? 1 : drop ? 0 : 2;
   if(o_bad!==bad || o_drop!==drop || o_n!==n[1:0]) fail("verdict/count");
   for(half=0;half<n;half=half+1) begin
    if(a<131072) begin
     h=(a>>16)&1;t=(a>>7)&511;d=a&127;
     tile=(t%48)*32+d/4;loc=(t/48)*2+h;
     lm=t==(posq[got]>>4) ? (128'd1<<(8*(posq[got]&15)))-1 : {128{1'b1}};
     want_data={256'd0,dataq[got]}<<(128*(d&3));
     want_mask={256'd0,lm,lm}<<(128*(d&3));
     lm=o_tail ? (128'd1<<(8*o_tail_lanes))-1 : {128{1'b1}};
     actual_data={256'd0,o_data}<<(128*o_sel0);
     actual_mask={256'd0,lm,lm}<<(128*o_sel0);
     if(!o_isk || o_tail!==(t==(posq[got]>>4))) fail("K flags");
    end else begin
     h=((a-131072)>>16)&1;pp=((a-131072)>>3)&8191;q=(a-131072)&7;
     tile=(q+half)*128+(pp%512)/4;loc=22+(pp/512)*2+h;
     want_data={384'd0,dataq[got][half*128+:128]}<<(128*(pp&3));
     want_mask={384'd0,{128{1'b1}}}<<(128*(pp&3));
     actual_data={384'd0,o_data[half*128+:128]}<<(128*(half ? o_sel1:o_sel0));
     actual_mask={384'd0,{128{1'b1}}}<<(128*(half ? o_sel1:o_sel0));
     if(o_isk || o_tail) fail("V flags");
    end
    if(NEG && got==37) actual_data=actual_data^512'd1;
    if((half ? o_tile1:o_tile0)!==tile[10:0] || (half ? o_loc1:o_loc0)!==loc[6:0]) fail("tile/local");
    if(actual_data!==want_data || actual_mask!==want_mask) fail("data/mask");
   end
   got=got+1;pending=pending+1;
  end
 end
 integer s;integer pc;
 task drive(input integer sector,input integer position,input integer mode);
 begin
  @(negedge clk);
  tick=tick+1;
  if(i_cr) credit=credit+1;
  o_cr=pending>0 && tick%7!=0;
  if(o_cr) pending=pending-1;
  i_v=credit>0;
  while(!i_v) begin
   @(negedge clk); tick=tick+1;
   if(i_cr) credit=credit+1;
   o_cr=pending>0 && tick%7!=0;
   if(o_cr) pending=pending-1;
   i_v=credit>0;
  end
  credit=credit-1;
  i_port=pc;
  i_expected=KV_MAP ? m_p2l(pc,10'(sector)) : {1'(sector&1),1'((pc>>4)&1),9'(sector>>1),4'(pc&15),2'(pc>>5)};
  i_sec=i_expected ^ (mode==1);
  i_pos=position;i_row=31;i_layer=mode==2 ? 30:31;
  i_count=sector;i_limit=1024;
  i_active=mode!=4;i_done=mode==5;
  i_data={8{32'(sector*1664525+1013904223)}};
 end endtask
 initial begin
  i_data=0;i_sec=0;i_expected=0;i_pos=0;i_row=0;i_layer=0;
  i_count=0;i_limit=1;i_active=1;i_done=0;
  repeat(3) @(negedge clk);rst_n=1;
  // Exhaustive sectors; alternating open-tail and maximal history boundaries.
  for(pc=0;pc<128;pc=pc+1)
   for(s=0;s<1024;s=s+1) drive(s,(s%2) ? 8191 : ((s/2)&511)*16+(s&15),0);
  // Explicit every open-tail lane mask, all malformed transaction classes.
  pc=127;
  for(s=0;s<256;s=s+1) drive(s,((s>>6)&511)*16+(s&15),s%6);
  @(negedge clk);i_v=0;
  while(got<sent) begin
   @(negedge clk); o_cr=pending>0; if(o_cr) pending=pending-1;
  end
  @(negedge clk);o_cr=0;
  repeat(4) @(negedge clk);
  if(fault) fail("legal stream credit fault");
  // Invalid credit cannot mint a token; reset isolates this negative traffic.
  rst_n=0;o_cr=0;repeat(3) @(negedge clk);rst_n=1;
  o_cr=1;repeat(4) @(negedge clk);o_cr=0;
  if(!fault) fail("duplicate credit undetected");
  $display("PASS kvc_mapped transactions=%0d pc_index_pairs=131072 malformed=covered duplicate_credit=detected",got);$finish;
 end
 initial begin #20000000;fail("watchdog");end
endmodule
