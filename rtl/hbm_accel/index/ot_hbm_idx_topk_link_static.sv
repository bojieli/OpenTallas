`default_nettype none
// Actual512-result native collective producer. Eight real memory banks absorb
// up to64chosen records/edge. Compiler issues exactly171ingest edges, fixed
// flush, then16 four-flit emit beats at8-edge intervals. No ready/credits.
module ot_hbm_idx_topk_link_static #(parameter integer MUT=0)(
 input wire clk,input wire[7:0]clk_mem,input wire rst_n,
 input wire clear,ingest_v,input wire[2367:0]selected_line,
 input wire flush,emit_v,input wire[3:0]emit_group,input wire[7:0]rank,gbase,
 output reg[3:0]tx_v,output reg[2179:0]tx,
 output reg fault,output wire[9:0]selected_count
);
 reg[4607:0]carry;
 reg[2:0]fill;
 reg[6:0]flits;
 reg[9:0]total;
 assign selected_count=total;
 reg[4607:0]packed_next;
 integer n,nf,count,bank,row;
 reg[7:0]we;
 reg[47:0]wa;
 reg[4095:0]wd;
 wire[4095:0]rd;
 reg[511:0]flit;
 reg[63:0]record;
 always @*begin
  packed_next=carry;n=int'(fill);count=0;
  if(ingest_v)for(integer q=0;q<4;q=q+1)for(integer l=0;l<16;l=l+1)begin
   if(selected_line[q*592+l*37])begin
    record={12'd0,selected_line[q*592+l*37+17+:20],selected_line[q*592+l*37+1+:16],16'd0};
    if(MUT==1)record={record[31:0],record[63:32]};
    packed_next[n*64+:64]=record;n=n+1;count=count+1;
   end
  end
  nf=n/8;we=0;wa=0;wd=0;flit=0;bank=0;row=0;
  for(integer j=0;j<8;j=j+1)if(j<nf)begin
   flit=0;
   for(integer r=0;r<8;r=r+1)begin
    flit[r*32+:32]=packed_next[(j*8+r)*64+:32];
    flit[256+r*32+:32]=packed_next[(j*8+r)*64+32+:32];
   end
   bank=(int'(flits)+j)%8;row=(int'(flits)+j)/8;
   we[bank]=1;wa[bank*6+:6]=6'(row);wd[bank*512+:512]=flit;
  end
 end
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
    carry<=packed_next>>(nf*512);fill<=3'(n%8);flits<=flits+7'(nf);total<=total+10'(count);
    if(int'(total)+count>512||int'(flits)+nf>64)fault<=1;
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
