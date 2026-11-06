// HBM-FORM-SPLIT d44v part 30: ot_hbm_idx_topk_link_static (WRITE_PIPE_STAGES=2 form) as two tiles at the SRAM write seam. Pin registers of the master stay in each
// tile. The output face of ingest and the input face of store are the two opt-in writer stages we0/wa0/wd0 and we1/wa1/wd1, so the seam adds no flop over that form.
// HBM-REFORM-B9: PD=3 form. ingest: compact tree registered at subtree sizes 8, 32 and 64 (ot_hbm_idx_compact_tree_p), the
// controls delayed to match; store: clear/emit/emit_group/rank/gbase delayed PD so the pair is the part 30 form delayed PD at every output.
`timescale 1ns/1ps
`default_nettype none
module ot_hbm_idx_topk_ingest #(parameter integer MUT=0, FILL_GROUPS=0)(
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
 localparam integer PD=3;
 reg[PD-1:0]clear_s,ingest_s,flush_s,emit_s;reg[7:0]rank_s[0:PD-1],gbase_s[0:PD-1];
 always @(posedge clk or negedge rst_core_n)if(!rst_core_n)begin clear_s<=0;ingest_s<=0;flush_s<=0;emit_s<=0;end
  else begin clear_s<={clear_s[PD-2:0],clear_r};ingest_s<={ingest_s[PD-2:0],ingest_r};flush_s<={flush_s[PD-2:0],flush_r};emit_s<={emit_s[PD-2:0],emit_r};end
 always @(posedge clk)begin
  rank_s[0]<=rank_r;gbase_s[0]<=gbase_r;for(integer i=1;i<PD;i=i+1)begin rank_s[i]<=rank_s[i-1];gbase_s[i]<=gbase_s[i-1];end
 end
 wire clear_p=clear_s[PD-1],ingest_p=ingest_s[PD-1],flush_p=flush_s[PD-1],emit_p=emit_s[PD-1];wire[7:0]rank_p=rank_s[PD-1],gbase_p=gbase_s[PD-1];
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
 ot_hbm_idx_compact_tree_p #(.N(64),.W(64),.PREG(7'b1101000)) compact(.clk(clk),.mask(mask),.words(words),.packed_words(compacted),.count(count));
 wire[6:0]n=7'(fill)+count;
 wire[3:0]nf=n[6:3];
 reg[447:0]live_carry;
 always @*begin
  live_carry=0;
  for(integer r=0;r<7;r=r+1)if(r<int'(fill))live_carry[r*64+:64]=carry[r*64+:64];
 end
 // Carry has only seven live records. Mask it by fill before merging, so the
 // datapath flops require no reset; fill is the reset control state.
 wire[4607:0]packed_next;
 wire[4607:0]live_carry_padded={4160'd0,live_carry};
 // Optional zero-edge fanout form: each eight-bit record-column group owns
 // its own three fill bits. Replicas sample the SAME next-state expression
 // and the SAME reset/clear/ingest priority as the original master fill.
 // No copy samples the old master, which would add a wrong edge.
 generate if(FILL_GROUPS==0)begin:g_fill_direct
  assign packed_next=({512'd0,compacted} << {fill,6'b0}) | {4160'd0,live_carry};
 end else if(FILL_GROUPS==8)begin:g_fill_columns
  for(genvar g=0;g<8;g=g+1)begin:column_group
   (* keep *) reg[2:0]fill_local;
   always @(posedge clk or negedge rst_core_n)begin
    if(!rst_core_n)fill_local<=0;
    else begin
     if(clear_p)fill_local<=0;
     if(ingest_p)fill_local<=(MUT==7&&g==2)?(n[2:0]^3'd1):
                              (MUT==8&&g==2)?fill:n[2:0];
    end
   end
   // Shift only this record-column plane.  Projecting an integer-record
   // shift commutes exactly with this 8-bit column projection.  Keeping the
   // plane explicit also avoids eight full-width gold-frontend intermediates.
   wire[575:0]column_words;
   for(genvar r=0;r<64;r=r+1)begin:input_column
    assign column_words[r*8+:8]=compacted[r*64+g*8+:8];
   end
   assign column_words[575:512]=64'd0;
   wire[575:0]shifted=column_words << {fill_local,3'b0};
   for(genvar r=0;r<72;r=r+1)begin:record_column
    assign packed_next[r*64+g*8+:8]=shifted[r*8+:8] |
                                      live_carry_padded[r*64+g*8+:8];
   end
  end
 end else begin:g_bad_fill_groups
  initial $fatal(1,"FILL_GROUPS must be 0 or 8");
  assign packed_next=0;
 end endgenerate
 reg[447:0]carry_next;
 always @*begin
  carry_next=0;
  for(integer f=0;f<=8;f=f+1)if(nf==4'(f))
   for(integer r=0;r<7;r=r+1)carry_next[r*64+:64]=packed_next[(f*8+r)*64+:64];
 end
 always @(posedge clk)if(ingest_p)carry<=carry_next;
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

 assign wo_we=(rst_core_n&&!clear_p)?we:8'd0;
 assign wo_wa=wa;assign wo_wd=wd;
 always @(posedge clk or negedge rst_core_n)begin
  if(!rst_core_n)begin fill<=0;flits<=0;total<=0;c_fault<=0;end
  else begin
   if(clear_p)begin fill<=0;flits<=0;total<=0;end
   if(ingest_p)begin
    fill<=n[2:0];flits<=flits+7'(nf);total<=total+10'(count);
    if(int'(total)+int'(count)>512||int'(flits)+int'(nf)>64)c_fault<=1;
   end
   if(emit_p&&rank_p<gbase_p)c_fault<=1;
   if(flush_p&&(total!=512||flits!=64||fill!=0))c_fault<=1;
   if((clear_p&&ingest_p)||(emit_p&&(ingest_p||flits!=64)))c_fault<=1;
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
 localparam integer PD=3;
 reg[PD-1:0]clear_s,emit_s;reg[3:0]group_s[0:PD-1];reg[7:0]rank_s[0:PD-1],gbase_s[0:PD-1];
 always @(posedge clk or negedge rst_core_n)if(!rst_core_n)begin clear_s<=0;emit_s<=0;end
  else begin clear_s<={clear_s[PD-2:0],clear};emit_s<={emit_s[PD-2:0],emit_v};end
 always @(posedge clk)begin
  clear_r<=clear_s[PD-1];clear_d<=clear_r;emit_r<=emit_s[PD-1];group_r<=group_s[PD-1];rank_r<=rank_s[PD-1];gbase_r<=gbase_s[PD-1];
  group_s[0]<=emit_group;rank_s[0]<=rank;gbase_s[0]<=gbase;
  for(integer i=1;i<PD;i=i+1)begin group_s[i]<=group_s[i-1];rank_s[i]<=rank_s[i-1];gbase_s[i]<=gbase_s[i-1];end
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
// pipelined compact tree: same packing as ot_hbm_idx_compact_tree; the outputs of every subtree of size 2^k with PREG[k] set
// are registered (PREG 7'b1101000: sizes 8, 32, 64 -> 3 cycles from mask/words to packed_words/count).
module ot_hbm_idx_compact_tree_p #(parameter integer N=64,W=64,parameter [6:0] PREG=7'b0)(
 input wire clk,input wire[N-1:0]mask,input wire[N*W-1:0]words,
 output wire[N*W-1:0]packed_words,
 output wire[$clog2(N+1)-1:0]count
);
 wire[N*W-1:0]pw;wire[$clog2(N+1)-1:0]c;
 generate if(N==1)begin:leaf
  assign pw=mask[0]?words:{W{1'b0}};
  assign c=mask[0];
 end else begin:branch
  localparam integer L=N/2,R=N-L;
  wire[L*W-1:0]left;wire[R*W-1:0]right;
  wire[$clog2(L+1)-1:0]lc;wire[$clog2(R+1)-1:0]rc;
  ot_hbm_idx_compact_tree_p #(.N(L),.W(W),.PREG(PREG)) lhs(
   .clk(clk),.mask(mask[L-1:0]),.words(words[L*W-1:0]),.packed_words(left),.count(lc));
  ot_hbm_idx_compact_tree_p #(.N(R),.W(W),.PREG(PREG)) rhs(
   .clk(clk),.mask(mask[N-1:L]),.words(words[N*W-1:L*W]),.packed_words(right),.count(rc));
  assign c=($clog2(N+1))'(lc)+($clog2(N+1))'(rc);
  assign pw={{R*W{1'b0}},left}|({{L*W{1'b0}},right} << (lc*W));
 end
 if(PREG[$clog2(N)])begin:q
  reg[N*W-1:0]pw_q;reg[$clog2(N+1)-1:0]c_q;
  always @(posedge clk)begin pw_q<=pw;c_q<=c;end
  assign packed_words=pw_q;assign count=c_q;
 end else begin:nq
  assign packed_words=pw;assign count=c;
 end endgenerate
endmodule
`default_nettype wire
