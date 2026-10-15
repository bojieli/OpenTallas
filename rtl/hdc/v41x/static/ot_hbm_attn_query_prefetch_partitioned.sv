`timescale 1ns/1ps
`default_nettype none
// One physical field owns fourSL slices, four128b stripes perSL. Same64
// realSRAM inventory; no replicated query. Parent controls samephase clock
// and fixed station latency; no source-independent long-route permission.
module ot_hbm_attn_query_field #(parameter integer FIELD=0)(
 input wire clk,read_v,read_epoch,input wire[3:0]read_head,
 input wire write_v,write_epoch,input wire[3:0]write_head,
 input wire[2:0]write_burst,input wire[511:0]write_bf16,
 output wire[2047:0]field_words
);
 for(genvar k=0;k<16;k=k+1)begin:g_store
  localparam integer BURST=2*(k/4)+FIELD/2;
  ot_sram_1r1w_32x128_m1 u_mem(.clk(clk),
   .r_ce_in(read_v),.r_addr_in({read_epoch,read_head}),.rd_out(field_words[k*128+:128]),
   .w_ce_in(write_v&&write_burst==3'(BURST)),.w_addr_in({write_epoch,write_head}),
   .wd_in(write_bf16[(k%4)*128+:128]),.w_mask_in({128{1'b1}}));
 end
endmodule
module ot_hbm_attn_query_prefetch_partitioned #(parameter integer FILL_LAT=8,MUT=0)(
 input wire clk,rst_n,
 input wire fetch_v,fetch_epoch,input wire[3:0]fetch_head,
 input wire[2:0]fetch_burst,input wire[15:0]fetch_base_sector,
 output reg[135:0]rq,input wire[2055:0]rr,
 input wire read_v,read_epoch,input wire[3:0]read_head,
 output reg q_v,output wire[8191:0]q_w,output wire[8191:0]field_q_w,output reg fault
);
 reg[FILL_LAT-1:0]vp,ep;reg[3:0]hp[0:FILL_LAT-1];reg[2:0]bp[0:FILL_LAT-1];
 wire[1023:0]converted;
 for(genvar b=0;b<8;b=b+1)for(genvar w=0;w<8;w=w+1)
  assign converted[b*128+w*16+:16]=rr[b*257+w*32+16+:16];
 always @(posedge clk or negedge rst_n)if(!rst_n)begin
  rq<=0;vp<=0;ep<=0;q_v<=0;fault<=0;
 end else begin
  vp<={vp[FILL_LAT-2:0],fetch_v};ep<={ep[FILL_LAT-2:0],fetch_epoch};q_v<=read_v;rq<=0;
  for(integer k=0;k<8;k=k+1)begin
   rq[k*17+:17]<={fetch_v,16'(fetch_base_sector+k)};
   if(rr[k*257+256]!=vp[FILL_LAT-1])fault<=1;
   if(vp[FILL_LAT-1])for(integer w=0;w<8;w=w+1)if(rr[k*257+w*32+:16]!=0)fault<=1;
  end
  if(fetch_v&&fetch_base_sector[2:0]!=0)fault<=1;
 end
 always @(posedge clk)begin
  hp[0]<=fetch_head;bp[0]<=fetch_burst;
  for(integer k=1;k<FILL_LAT;k=k+1)begin hp[k]<=hp[k-1];bp[k]<=bp[k-1];end
 end
 for(genvar g=0;g<4;g=g+1)begin:g_field
  ot_hbm_attn_query_field #(.FIELD(g))u_field(.clk(clk),.read_v(read_v),.read_epoch(read_epoch),.read_head(read_head),
   .write_v(vp[FILL_LAT-1]),.write_epoch(ep[FILL_LAT-1]),.write_head(hp[FILL_LAT-1]),.write_burst(bp[FILL_LAT-1]),
   .write_bf16(converted[((g%2)^(MUT==1?1:0))*512+:512]),.field_words(field_q_w[g*2048+:2048]));
  for(genvar k=0;k<16;k=k+1)begin:g_global_alias
   localparam integer S=16*(k/4)+4*g+(k%4);
   assign q_w[S*128+:128]=field_q_w[g*2048+((MUT==2)?(k^4):k)*128+:128];
  end
 end
 initial if(FILL_LAT<2)$fatal(1,"querypartition requires actual positive fixed pipeline");
endmodule
`default_nettype wire
