// HBM-FORM-SPLIT d44v part 30: ot_hbm_idx_topk_link_static (WRITE_PIPE_STAGES=2 form) as two tiles at the SRAM write seam. Pin registers of the master stay in each
// tile. The output face of ingest and the input face of store are the two opt-in writer stages we0/wa0/wd0 and we1/wa1/wd1, so the seam adds no flop over that form.
`timescale 1ns/1ps
`default_nettype none
module ot_hbm_idx_topk_ingest #(parameter integer MUT=0)(
 input wire clk,input wire rst_n,
 input wire clear,ingest_v,input wire[2367:0]selected_line,
 input wire flush,emit_v,input wire[7:0]rank,gbase,
 output reg fault,output reg[9:0]selected_count,
 output wire[7:0]wo_we,output wire[47:0]wo_wa,output wire[4095:0]wo_wd
);
 (* keep *) reg [1:0] rst_sync;
 always @(posedge clk or negedge rst_n) if(!rst_n) rst_sync<=2'b00; else rst_sync<={rst_sync[0],1'b1};
 wire rst_core_n=rst_sync[1];
 (* keep *) reg clear_r,ingest_r,flush_r,emit_r;(* keep *) reg[2367:0]line_r;(* keep *) reg[7:0]rank_r,gbase_r;
 reg c_fault;wire[9:0]c_count;
 always @(posedge clk)begin
  clear_r<=clear;ingest_r<=ingest_v;line_r<=selected_line;flush_r<=flush;emit_r<=emit_v;rank_r<=rank;gbase_r<=gbase;
  fault<=c_fault;selected_count<=c_count;
 end
 reg[447:0]carry;
 reg[2:0]fill;
 reg[6:0]flits;
 reg[9:0]total;
 assign c_count=total;
 wire[63:0]mask;
 wire[4095:0]words,compacted;
 wire[6:0]count;
 for(genvar j=0;j<64;j=j+1)begin:record_in
  assign mask[j]=ingest_r&&line_r[j*37]&&!(MUT==3&&j==63);
  wire[63:0]normal_word={12'd0,line_r[j*37+17+:20],line_r[j*37+1+:16],16'd0};
  assign words[j*64+:64]=(MUT==1)?{normal_word[31:0],normal_word[63:32]}:normal_word;
 end
 ot_hbm_idx_compact_tree #(.N(64),.W(64)) compact(.mask(mask),.words(words),.packed_words(compacted),.count(count));
 wire[6:0]n=7'(fill)+count;
 wire[3:0]nf=n[6:3];
 reg[447:0]live_carry;
 always @*begin
  live_carry=0;
  for(integer r=0;r<7;r=r+1)if(r<int'(fill))live_carry[r*64+:64]=carry[r*64+:64];
 end
 // Carry has only seven live records. Mask it by fill before merging, so the
 // datapath flops require no reset; fill is the reset control state.
 wire[4607:0]packed_next=({512'd0,compacted} << {fill,6'b0}) | {4160'd0,live_carry};
 reg[447:0]carry_next;
 always @*begin
  carry_next=0;
  for(integer f=0;f<=8;f=f+1)if(nf==4'(f))
   for(integer r=0;r<7;r=r+1)carry_next[r*64+:64]=packed_next[(f*8+r)*64+:64];
 end
 always @(posedge clk)if(ingest_r)carry<=carry_next;
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

 assign wo_we=(rst_core_n&&!clear_r)?we:8'd0;
 assign wo_wa=wa;assign wo_wd=wd;
 always @(posedge clk or negedge rst_core_n)begin
  if(!rst_core_n)begin fill<=0;flits<=0;total<=0;c_fault<=0;end
  else begin
   if(clear_r)begin fill<=0;flits<=0;total<=0;end
   if(ingest_r)begin
    fill<=n[2:0];flits<=flits+7'(nf);total<=total+10'(count);
    if(int'(total)+int'(count)>512||int'(flits)+int'(nf)>64)c_fault<=1;
   end
   if(emit_r&&rank_r<gbase_r)c_fault<=1;
   if(flush_r&&(total!=512||flits!=64||fill!=0))c_fault<=1;
   if((clear_r&&ingest_r)||(emit_r&&(ingest_r||flits!=64)))c_fault<=1;
  end
 end
endmodule
module ot_hbm_idx_topk_store #(parameter integer MUT=0)(
 input wire clk,input wire[7:0]clk_mem,input wire rst_n,
 input wire clear,emit_v,input wire[3:0]emit_group,input wire[7:0]rank,gbase,
 input wire[7:0]wi_we,input wire[47:0]wi_wa,input wire[4095:0]wi_wd,
 output reg[3:0]tx_v,output reg[2179:0]tx
);
 (* keep *) reg [1:0] rst_sync;
 always @(posedge clk or negedge rst_n) if(!rst_n) rst_sync<=2'b00; else rst_sync<={rst_sync[0],1'b1};
 wire rst_core_n=rst_sync[1];
 (* keep *) reg clear_r,clear_d,emit_r;(* keep *) reg[3:0]group_r;(* keep *) reg[7:0]rank_r,gbase_r;
 reg[3:0]c_tx_v;wire[2179:0]c_tx;
 always @(posedge clk)begin
  clear_r<=clear;clear_d<=clear_r;emit_r<=emit_v;group_r<=emit_group;rank_r<=rank;gbase_r<=gbase;
  tx_v<=c_tx_v;tx<=c_tx;
 end
 // clear kills both writer stages: wi_we left the first stage before this clear when clear_d is set.
 wire[7:0]mem_we=(rst_core_n&&!clear_r&&!(clear_d&&MUT!=1))?wi_we:8'd0;
 wire[4095:0]rd;
 for(genvar b=0;b<8;b=b+1)begin:gm
  wire re=emit_r&&(b/4==int'(group_r[0]));
  ot_sram_1r1w_64x512_m1_r2c2 mem(.clk(clk_mem[b]),.r_ce_in(re),.r_addr_in({3'd0,group_r[3:1]}),.rd_out(rd[b*512+:512]),
   .w_ce_in(mem_we[b]),.w_addr_in(wi_wa[b*6+:6]),.wd_in(wi_wd[b*512+:512]),.w_mask_in({512{1'b1}}),
   .rr_en(2'd0),.rr_addr(12'd0),.cr_en(2'd0),.cr_sel(18'd0));
 end
 reg read_v;reg[3:0]read_group;reg[7:0]read_rank,read_gbase;
 reg[511:0]tx_data[0:3];reg[13:0]tx_seq[0:3];reg[7:0]tx_rank[0:3];
 wire[15:0]read_seq[0:3];
 for(genvar l=0;l<4;l=l+1)begin:tx_format
  assign read_seq[l]=16'((int'(read_rank)-int'(read_gbase))*64+int'(read_group)*4+l);
  assign c_tx[l*545+:545]={9'h1ff,tx_rank[l],tx_seq[l],l[1:0],tx_data[l]};
 end
 always @(posedge clk or negedge rst_core_n)begin
  if(!rst_core_n)begin read_v<=0;c_tx_v<=0;read_group<=0;read_rank<=0;read_gbase<=0;end
  else begin
   read_v<=emit_r;read_group<=group_r;read_rank<=rank_r;read_gbase<=gbase_r;c_tx_v<={4{read_v}};
   for(integer l=0;l<4;l=l+1)if(read_v)begin
    tx_data[l]<=rd[(int'(read_group[0])*4+l)*512+:512];
    tx_rank[l]<=read_rank;tx_seq[l]<=read_seq[l][15:2];
   end
  end
 end
endmodule
`default_nettype wire
