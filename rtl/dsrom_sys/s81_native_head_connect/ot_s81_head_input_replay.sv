`timescale 1ns/1ps
// Functional source-native consumer seam for actual normalized producer pins.
// Production final POST/NORMR/NX/XQ routing is NOT supplied by this module.
// Fixed schedule, one resident owner, no ready/credits/backpressure.
// Legacy macros are functional bindings only; dense physical access unqualified.
module ot_s81_head_input_replay (
 input wire clk,rst_n,load_begin,load_v,go,
 input wire [46:0] owner, input wire [63:0] sequence_id,
 input wire [6:0] load_i, input wire [2047:0] load_d,
 output reg [255:0] xa,xb,
 output reg active, fault
);
 reg [1:0] reset_landing;
 always @(posedge clk or negedge rst_n)
  if(!rst_n) reset_landing<=0; else reset_landing<={reset_landing[0],1'b1};
 wire rs=reset_landing[1];
 reg [46:0] resident_owner;reg[63:0] resident_sequence;
 reg loading,complete;reg[6:0] count;reg[13:0] age;
 // Request at G+3; macro output after that edge, output capture G+4,
 // then native field samples the registered value at G+5.
 wire re=active && age>=2 && age<8271;
 wire[13:0] word_index=age-2;
 wire[6:0] ra={1'b0,word_index[7:2]};
 wire[6:0] rb={3'b0,word_index[5:2]};
 wire[1023:0] da,db;
 reg[1:0] select_q;
 wire accepted_load=load_v && loading && !active && load_i==count &&
                    owner==resident_owner && sequence_id==resident_sequence && count<80;
 for(genvar b=0;b<4;b=b+1)begin:bank
  wire[255:0] wd;
  for(genvar j=0;j<16;j=j+1)begin:pack
   assign wd[16*j+:16]=load_d[32*(b*16+j)+16+:16];
  end
  ot_sram_1r1w_128x256_m1_r2c2 a(.clk(clk),.r_ce_in(re),.r_addr_in(ra),.rd_out(da[256*b+:256]),
   .w_ce_in(accepted_load && load_i<64),.w_addr_in(load_i),.wd_in(wd),.w_mask_in({256{1'b1}}),
   .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
  ot_sram_1r1w_128x256_m1_r2c2 bmem(.clk(clk),.r_ce_in(re),.r_addr_in(rb),.rd_out(db[256*b+:256]),
   .w_ce_in(accepted_load && load_i>=64),.w_addr_in(load_i-7'd64),.wd_in(wd),.w_mask_in({256{1'b1}}),
   .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 end
 always @(posedge clk)begin
  select_q<=word_index[1:0];
  xa<=da[256*select_q+:256];xb<=db[256*select_q+:256];
 end
 integer k;
 always @(posedge clk or negedge rs)begin
  if(!rs)begin resident_owner<=0;resident_sequence<=0;loading<=0;complete<=0;count<=0;age<=0;active<=0;fault<=0;end
  else begin
   if(load_begin)begin
    if(active||loading||load_v||go)fault<=1;
    else begin loading<=1;complete<=0;count<=0;resident_owner<=owner;resident_sequence<=sequence_id;end
   end
   if(load_v)begin
    if(!accepted_load)fault<=1;
    else begin count<=count+1'b1;if(count==79)begin loading<=0;complete<=1;end end
    for(k=0;k<64;k=k+1)if(load_d[32*k+:16]!=0)fault<=1;
   end
   if(go)begin
    if(active||!complete||loading||load_begin||load_v||owner!=resident_owner||sequence_id!=resident_sequence)fault<=1;
    else begin active<=1;age<=0;end
   end
   if(active)begin age<=age+1'b1;if(age==8272)active<=0;end
  end
 end
endmodule
