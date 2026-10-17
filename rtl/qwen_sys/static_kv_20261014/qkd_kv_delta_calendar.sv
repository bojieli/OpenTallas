`timescale 1ns/1ps
// Compact immutable bytecode: {emit,positive_delta[6:0]}. Non-emitting
// records extend long waits. Two256-bit caches sustain one record/edge;
// actual aligned-v2 128x256 1R1W macros supply one word per32 records.
// Boot writes all rows before seal; no runtime writes, ready or arrivals.
module qkd_kv_delta_calendar #(parameter integer BANKS=5,MUT=0)(
 input wire ck,rst_n,input wire cfg_we,cfg_seal,
 input wire[9:0]cfg_row,input wire[255:0]cfg_data,
 input wire[14:0]cfg_bytes,input wire[31:0]cfg_stop,input wire start,
 output reg slot,output reg[14:0]ordinal,
 output reg configured,active,done,fault,output reg[31:0]cycle
);
 initial if(BANKS<1||BANKS>8)$error("calendar SRAM bank count1..8");
 (* keep *)reg rn;
 always @(posedge ck or negedge rst_n)if(!rst_n)rn<=0;else rn<=1;
 (* keep *)reg we_p,seal_p,start_p;
 (* keep *)reg[9:0]row_p;(* keep *)reg[255:0]data_p;
 (* keep *)reg[14:0]bytes_p;(* keep *)reg[31:0]stop_p;
 always @(posedge ck)begin row_p<=cfg_row;data_p<=cfg_data;bytes_p<=cfg_bytes;stop_p<=cfg_stop;end
 always @(posedge ck or negedge rn)
  if(!rn)begin we_p<=0;seal_p<=0;start_p<=0;end
  else begin we_p<=cfg_we;seal_p<=cfg_seal;start_p<=start;end
 reg[10:0]written;reg[14:0]bytes_total,remaining;
 reg[31:0]stop_time,deadline;
 reg[2:0]boot;
 reg[255:0]cur_word,next_word;
 reg[9:0]cur_row;reg[4:0]byte_index;reg next_valid;
 wire accept_write=we_p&&!seal_p&&!configured&&!active&&!fault&&boot==0&&
   {1'b0,row_p}==written&&written<BANKS*128;
 wire consume=active&&remaining!=0&&cycle+1'b1==deadline;
 wire boundary=consume&&byte_index==31&&remaining>1;
 wire fetch_more=boundary&&remaining>33;
 wire rce=boot==1||boot==3||fetch_more;
 wire[9:0]ra=boot==1?10'd0:boot==3?10'd1:cur_row+10'd2;
 wire[255:0]mq[0:BANKS-1];
 genvar g;
 generate for(g=0;g<BANKS;g=g+1)begin:calendar_sram
  ot_sram_1r1w_128x256_m1_r2c2 u_image(
   .clk(ck),.r_ce_in(rce&&ra[9:7]==g),.r_addr_in(ra[6:0]+((MUT==4)?7'd1:7'd0)),.rd_out(mq[g]),
   .w_ce_in(accept_write&&row_p[9:7]==g),.w_addr_in(row_p[6:0]),
   .wd_in(data_p),.w_mask_in({256{1'b1}}),
   .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 end endgenerate
 reg read_pending,read_next;reg[2:0]read_bank;
 wire[255:0]read_word=mq[read_bank];
 wire[7:0]following=byte_index==31?next_word[7:0]:cur_word[15:8];
 wire[31:0]next_cycle=cycle+32'd1;
 always @(posedge ck or negedge rn)begin
  if(!rn)begin
   written<=0;bytes_total<=0;remaining<=0;stop_time<=0;deadline<=0;
   boot<=0;cur_row<=0;byte_index<=0;next_valid<=0;read_pending<=0;read_next<=0;read_bank<=0;
   slot<=0;ordinal<=0;configured<=0;active<=0;done<=0;fault<=0;cycle<=0;
  end else begin
   slot<=0;done<=0;read_pending<=rce;
   if(rce)begin read_bank<=ra[9:7];read_next<=boot!=1;end
   if(read_pending)begin
    if(read_next)begin next_word<=read_word;next_valid<=1;end
    else cur_word<=read_word;
   end
   case(boot)
    1:boot<=2;
    2:if(read_pending)begin
     if(bytes_total>32)boot<=3;else begin boot<=5;configured<=1;end
    end
    3:boot<=4;
    4:if(read_pending)begin boot<=5;configured<=1;end
   endcase
   if(we_p||seal_p)begin
    if(we_p)begin if(!accept_write)fault<=1;else written<=written+1'b1;end
    else if(configured||active||fault||boot!=0||bytes_p==0||bytes_p>BANKS*4096||
      written!=(({1'b0,bytes_p}+16'd31)>>5)||stop_p<8)fault<=1;
    else begin bytes_total<=bytes_p;stop_time<=stop_p;boot<=1;end
   end
   if(start_p)begin
    if(!configured||active||fault||we_p||seal_p||cur_word[6:0]==0||cur_row!=0||byte_index!=0)
     fault<=1;
    else begin
     active<=1;cycle<=0;ordinal<=0;remaining<=bytes_total;deadline<={25'd0,cur_word[6:0]};
    end
   end else if(active)begin
    cycle<=next_cycle;
    if(consume)begin
     slot<=cur_word[7]^((MUT==1)?1'b1:1'b0);
     if(cur_word[7])ordinal<=ordinal+1'b1;
     remaining<=remaining-1'b1;
     if(byte_index==31)begin
      if(remaining>1&&!next_valid)fault<=1;
      cur_word<=next_word;next_valid<=0;cur_row<=cur_row+1'b1;byte_index<=0;
     end else begin cur_word<=cur_word>>8;byte_index<=byte_index+1'b1;end
     if(remaining>1)begin
      if(following[6:0]==0||deadline+{25'd0,following[6:0]}>=stop_time)fault<=1;
      deadline<=deadline+{25'd0,following[6:0]}+((MUT==2)?32'd1:32'd0);
     end
    end
    if(next_cycle==stop_time)begin
     active<=0;done<=1;if(remaining!=0)fault<=1;
     configured<=0;boot<=1;cur_row<=0;byte_index<=0;next_valid<=0;
    end
    if(&cycle)begin active<=0;done<=1;fault<=1;end
   end
  end
 end
endmodule
