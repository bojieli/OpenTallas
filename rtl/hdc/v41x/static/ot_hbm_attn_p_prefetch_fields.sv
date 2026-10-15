`timescale 1ns/1ps
`default_nettype none
// One actual response producer, four explicit localcopies. Fieldclocks must be
// synchronous/phase matched; actualstations/FILL_LAT and CTS stillneed proof.
module ot_hbm_attn_p_field_store #(parameter integer MUT=0)(
 input wire clk,rst_n,write_v,write_epoch,input wire[3:0]write_head,write_burst,
 input wire[1023:0]write_data,input wire read_v,read_epoch,input wire[9:0]read_row,
 output wire[1023:0]p_w
);
 reg[2:0]bank_q,offset_q;wire[127:0]words[0:127];
 always @(posedge clk or negedge rst_n)if(!rst_n)begin bank_q<=0;offset_q<=0;end
 else if(read_v)begin bank_q<=read_row[5:3];offset_q<=read_row[2:0];end
 genvar s,h,r;
 generate for(s=0;s<128;s=s+1)begin:g_store
  localparam integer HEAD=s/8,BANK=s%8;
  ot_sram_1r1w_32x128_m1 u_mem(.clk(clk),.r_ce_in(read_v&&read_row[5:3]==3'(BANK)),
   .r_addr_in({read_epoch,read_row[9:6]}),.rd_out(words[s]),
   .w_ce_in(write_v&&write_head==4'(HEAD)),.w_addr_in({write_epoch,write_burst}),
   .wd_in(write_data[((BANK^(MUT==1?1:0))*128)+:128]),.w_mask_in({128{1'b1}}));
 end
 for(h=0;h<16;h=h+1)begin:g_head
  for(r=0;r<4;r=r+1)begin:g_row
   assign p_w[(r*16+h)*16+:16]=words[h*8+int'(bank_q)][(int'(offset_q)+r)*16+:16];
  end
 end endgenerate
endmodule
module ot_hbm_attn_p_prefetch_fields #(parameter integer FILL_LAT=8,MUT_FIELD=-1)(
 input wire clk,rst_n,input wire[3:0]bank_clk,
 input wire fetch_v,fetch_epoch,input wire[3:0]fetch_head,fetch_burst,
 input wire[15:0]fetch_base_sector,profile_rows,
 output reg[135:0]rq,input wire[2055:0]rr,
 input wire read_v,read_epoch,input wire[9:0]read_row,
 output reg p_v,output wire[1023:0]p_w,output wire[4095:0]field_p_w,output reg fault
);
 reg[FILL_LAT-1:0]vp,ep;reg[3:0]hp[0:FILL_LAT-1],bp[0:FILL_LAT-1];
 wire[1023:0]converted;integer i;
 always @(posedge clk or negedge rst_n)if(!rst_n)begin rq<=0;vp<=0;ep<=0;p_v<=0;fault<=0;end
 else begin
  rq<=0;vp<={vp[FILL_LAT-2:0],fetch_v};ep<={ep[FILL_LAT-2:0],fetch_epoch};p_v<=read_v;
  for(integer b=0;b<8;b=b+1)begin
   rq[b*17+:17]<={fetch_v,16'(fetch_base_sector+b)};
   if(rr[b*257+256]!=vp[FILL_LAT-1])fault<=1;
   if(vp[FILL_LAT-1])for(integer w=0;w<8;w=w+1)if(rr[b*257+w*32+:16]!=0)fault<=1;
  end
  if(fetch_v&&(fetch_base_sector[2:0]!=0||fetch_burst>=((profile_rows+63)/64)))fault<=1;
  if((fetch_v||read_v)&&!(profile_rows==128||profile_rows==640))fault<=1;
  if(read_v&&(read_row[1:0]!=0||{6'd0,read_row}+16'd3>=profile_rows))fault<=1;
 end
 always @(posedge clk)begin
  hp[0]<=fetch_head;bp[0]<=fetch_burst;
  for(integer j=1;j<FILL_LAT;j=j+1)begin hp[j]<=hp[j-1];bp[j]<=bp[j-1];end
 end
 genvar b,w,g;
 generate for(b=0;b<8;b=b+1)begin:g_bank
  for(w=0;w<8;w=w+1)begin:g_word
   assign converted[(b*8+w)*16+:16]=rr[b*257+w*32+16+:16];
  end
 end
 for(g=0;g<4;g=g+1)begin:g_field
  ot_hbm_attn_p_field_store #(.MUT(MUT_FIELD==g?1:0))u_store(.clk(bank_clk[g]),.rst_n(rst_n),
   .write_v(vp[FILL_LAT-1]),.write_epoch(ep[FILL_LAT-1]),.write_head(hp[FILL_LAT-1]),.write_burst(bp[FILL_LAT-1]),.write_data(converted),
   .read_v(read_v),.read_epoch(read_epoch),.read_row(read_row),.p_w(field_p_w[g*1024+:1024]));
 end endgenerate
 assign p_w=field_p_w[1023:0];
 initial if(FILL_LAT<2)$fatal(1,"P4 prefetch needs measuredpositivepipeline");
endmodule
`default_nettype wire
