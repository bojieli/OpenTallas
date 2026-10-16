`default_nettype none
// Additive same-cycle structural candidate: balanced prefix counts and constant
// destinations replace the serial variable-width compaction/barrel-write chain.
// The only retained carry is its seven live records. Eight actual SRAM banks,
// 512 records/frame, fixed 171 ingest slots and fixed emit calendar are unchanged.
module ot_hbm_idx_topk_link_static_core_dense #(parameter integer MUT=0)(
 input wire clk,input wire[7:0]clk_mem,input wire rst_n,
 input wire clear,ingest_v,input wire[2367:0]selected_line,
 input wire flush,emit_v,input wire[3:0]emit_group,input wire[7:0]rank,gbase,
 output reg[3:0]tx_v,output reg[2179:0]tx,
 output reg fault,output wire[9:0]selected_count
);
 reg[447:0]carry;
 reg[2:0]fill;
 reg[6:0]flits;
 reg[9:0]total;
 assign selected_count=total;
 wire[63:0]mask;
 wire[63:0]word[0:63];
 wire[3:0]group_count[0:7];
 wire[4:0]pair_count[0:3];
 wire[5:0]quad_count[0:1];
 wire[6:0]group_before[0:7],prefix[0:63];
 for(genvar j=0;j<64;j=j+1)begin:record_in
  assign mask[j]=ingest_v&&selected_line[j*37];
  wire[63:0]normal_word={12'd0,selected_line[j*37+17+:20],selected_line[j*37+1+:16],16'd0};
  assign word[j]=(MUT==1)?{normal_word[31:0],normal_word[63:32]}:normal_word;
  wire[3:0]within_group=$countones(mask[(j/8)*8+:8] & ((8'h1<<(j%8))-1));
  assign prefix[j]=group_before[j/8]+7'(within_group);
 end
 for(genvar g=0;g<8;g=g+1)begin:count_group
  assign group_count[g]=$countones(mask[g*8+:8]);
  assign group_before[g]=7'(fill)+(g>=4?7'(quad_count[0]):7'd0)
   +(g%4>=2?7'(pair_count[(g/4)*2]):7'd0)+(g%2?7'(group_count[g==0?0:g-1]):7'd0);
 end
 for(genvar g=0;g<4;g=g+1)begin:count_pair
  assign pair_count[g]=5'(group_count[g*2])+5'(group_count[g*2+1]);
 end
 for(genvar g=0;g<2;g=g+1)begin:count_quad
  assign quad_count[g]=6'(pair_count[g*2])+6'(pair_count[g*2+1]);
 end
 wire[6:0]count=7'(quad_count[0])+7'(quad_count[1]);
 wire[6:0]n=7'(fill)+count;
 wire[3:0]nf=n[6:3];
 reg[4607:0]packed_next;
 reg[447:0]carry_next;
 always @*begin
  packed_next=0;
  // Every destination slice is constant. No variable 64-bit write into a
  // 4608-bit vector and no sequence of wide read/modify/write muxes remains.
  for(integer d=0;d<72;d=d+1)begin
   if(d<7)if(d<int'(fill))packed_next[d*64+:64]=carry[d*64+:64];
   for(integer j=0;j<64;j=j+1)if(mask[j]&&prefix[j]==7'(d))
    packed_next[d*64+:64]=packed_next[d*64+:64]|word[j];
  end
  carry_next=0;
  for(integer f=0;f<=8;f=f+1)if(nf==4'(f))
   for(integer r=0;r<7;r=r+1)carry_next[r*64+:64]=packed_next[(f*8+r)*64+:64];
 end
 wire[511:0]write_flit[0:7];
 for(genvar j=0;j<8;j=j+1)begin:flit_pack
  for(genvar r=0;r<8;r=r+1)begin:record_pack
   assign write_flit[j][r*32+:32]=packed_next[(j*8+r)*64+:32];
   assign write_flit[j][256+r*32+:32]=packed_next[(j*8+r)*64+32+:32];
  end
 end
 reg[7:0]we;reg[47:0]wa;reg[4095:0]wd;
 always @*begin
  we=0;wa=0;wd=0;
  // Constant bank destinations also remove eight dynamic 512-bit writes.
  for(integer b=0;b<8;b=b+1)for(integer j=0;j<8;j=j+1)
   if(j<int'(nf)&&((int'(flits)+j)%8)==b)begin
    we[b]=1;wa[b*6+:6]=6'((int'(flits)+j)/8);wd[b*512+:512]=write_flit[j];
   end
 end
 wire[4095:0]rd;
 for(genvar b=0;b<8;b=b+1)begin:gm
  wire re=emit_v&&(b/4==int'(emit_group[0]));
  ot_sram_1r1w_64x512_m1_r2c2 mem(.clk(clk_mem[b]),.r_ce_in(re),.r_addr_in({3'd0,emit_group[3:1]}),.rd_out(rd[b*512+:512]),
   .w_ce_in(we[b]),.w_addr_in(wa[b*6+:6]),.wd_in(wd[b*512+:512]),.w_mask_in({512{1'b1}}),
   .rr_en(2'd0),.rr_addr(12'd0),.cr_en(2'd0),.cr_sel(18'd0));
 end
 reg read_v;reg[3:0]read_group;reg[7:0]read_rank,read_gbase;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin carry<=0;fill<=0;flits<=0;total<=0;fault<=0;read_v<=0;tx_v<=0;read_group<=0;read_rank<=0;read_gbase<=0;end
  else begin
   read_v<=emit_v;read_group<=emit_group;read_rank<=rank;read_gbase<=gbase;tx_v<={4{read_v}};
   if(clear)begin carry<=0;fill<=0;flits<=0;total<=0;end
   if(ingest_v)begin
    carry<=carry_next;fill<=n[2:0];flits<=flits+7'(nf);total<=total+10'(count);
    if(int'(total)+int'(count)>512||int'(flits)+int'(nf)>64)fault<=1;
   end
   if(emit_v&&rank<gbase)fault<=1;
   if(flush&&(total!=512||flits!=64||fill!=0))fault<=1;
   if((clear&&ingest_v)||(emit_v&&(ingest_v||flits!=64)))fault<=1;
   for(integer l=0;l<4;l=l+1)if(read_v)begin
    tx[l*545+:545]<={1'b1,8'hff,read_rank,16'((int'(read_rank)-int'(read_gbase))*64+int'(read_group)*4+l),rd[(int'(read_group[0])*4+l)*512+:512]};
    if(MUT==2)tx[l*545+512+:16]<=16'((int'(read_rank)-int'(read_gbase))*64+int'(read_group)*4+l)^16'd1;
   end
  end
 end
endmodule
`default_nettype wire

`default_nettype none
module ot_hbm_idx_topk_link_static_dense #(parameter integer MUT=0)(
 input wire clk,input wire[7:0]clk_mem,input wire rst_n,
 input wire clear,ingest_v,input wire[2367:0]selected_line,
 input wire flush,emit_v,input wire[3:0]emit_group,input wire[7:0]rank,gbase,
 output reg[3:0]tx_v,output reg[2179:0]tx,
 output reg fault,output reg[9:0]selected_count
);
 // rst_n: async assert, 2-edge release on clk; the core's resets (async and synchronous uses on every
 // same-PLL phase-0 root) come from this one kept register, so no input port feeds another root's data pins.
 (* keep *) reg [1:0] rst_sync;
 always @(posedge clk or negedge rst_n) if(!rst_n) rst_sync<=2'b00; else rst_sync<={rst_sync[0],1'b1};
 wire rst_core_n=rst_sync[1];
 (* keep *) reg clear_r,ingest_r,flush_r,emit_r;(* keep *) reg[2367:0]line_r;(* keep *) reg[3:0]group_r;(* keep *) reg[7:0]rank_r,gbase_r;
 wire[3:0]c_tx_v;wire[2179:0]c_tx;wire c_fault;wire[9:0]c_count;
 always @(posedge clk)begin
  clear_r<=clear;ingest_r<=ingest_v;line_r<=selected_line;flush_r<=flush;emit_r<=emit_v;group_r<=emit_group;rank_r<=rank;gbase_r<=gbase;
  tx_v<=c_tx_v;tx<=c_tx;fault<=c_fault;selected_count<=c_count;
 end
 ot_hbm_idx_topk_link_static_core_dense #(.MUT(MUT)) core(.clk(clk),.clk_mem(clk_mem),.rst_n(rst_core_n),.clear(clear_r),.ingest_v(ingest_r),
  .selected_line(line_r),.flush(flush_r),.emit_v(emit_r),.emit_group(group_r),.rank(rank_r),.gbase(gbase_r),
  .tx_v(c_tx_v),.tx(c_tx),.fault(c_fault),.selected_count(c_count));
endmodule
`default_nettype wire
