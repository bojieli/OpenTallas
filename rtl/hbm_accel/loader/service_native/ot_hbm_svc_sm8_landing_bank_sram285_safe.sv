// Ownership-gated metadata and local bitmap predicates. Production LBANKS4 only.
`default_nettype none
(* keep_hierarchy="yes" *) module ot_hbm_landing_field_inverse #(parameter integer W=10)(
 input wire [W-1:0] field,output wire [W-1:0] inverse);
 assign inverse=~field;
endmodule
(* keep_hierarchy="yes" *) module ot_hbm_landing_safe_epoch #(parameter integer INDEX=0)(
 input wire clk,reserve_v,input wire [1:0] negative_bank,input wire [15:0] reserve_epoch,output reg [15:0] epoch_q);
 always @(posedge clk)if(reserve_v&&negative_bank==(~2'(INDEX)))epoch_q<=reserve_epoch;
endmodule
(* keep_hierarchy="yes" *) module ot_hbm_landing_safe_metadata #(
 parameter integer INDEX=0,parameter [2:0] BANK=0)(
 input wire clk,rst_n,reserve_v,input wire [1:0] reserve_bank,
 input wire [15:0] reserve_epoch,input wire [11:0] reserve_total,
 input wire [1:0] packet_bank,input wire [5:0] row,input wire [15:0] epoch,
 input wire landing_write,output wire identity,last_packet);
 wire [10:0] n;
 ot_hbm_landing_field_inverse #(.W(11)) u_fields(.field({reserve_v,reserve_bank,packet_bank,row}),.inverse(n));
 wire mine=n[7:6]==(~2'(INDEX));wire reserve_mine=n[9:8]==(~2'(INDEX));
 wire [15:0] epoch_q;reg valid_q;reg [6:0] count_q,received_q;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)valid_q<=0;else if(!n[10]&&reserve_mine)valid_q<=1;
 // Reservation always initializes the complete metadata tuple before valid ownership.
 always @(posedge clk)begin
  if(!n[10]&&reserve_mine)begin
   count_q<=reserve_total>BANK?(reserve_total+7-BANK)/8:0;received_q<=0;
  end
  if(landing_write&&mine)received_q<=received_q+1'b1;
 end
 ot_hbm_landing_safe_epoch #(.INDEX(INDEX)) u_epoch(.clk(clk),.reserve_v(!n[10]),
  .negative_bank(n[9:8]),.reserve_epoch(reserve_epoch),.epoch_q(epoch_q));
 assign identity=mine&&valid_q&&epoch_q==epoch&&{1'b0,~n[5:0]}<count_q;
 assign last_packet=mine&&valid_q&&received_q+1'b1==count_q;
endmodule
(* keep_hierarchy="yes" *) module ot_hbm_landing_safe_seen_byte #(parameter integer INDEX=0)(
 input wire clk,reserve_clear,write_enable,input wire [5:0] negative_row,
 output wire seen);
 reg [7:0] bits_q;
 wire mine=negative_row[5:3]==(~3'(INDEX));
 wire [2:0] bit_index=~negative_row[2:0];
 integer k;
 always @(posedge clk)begin
  for(k=0;k<8;k=k+1)begin
   if(reserve_clear)bits_q[k]<=0;
   if(write_enable&&mine&&bit_index==3'(k))bits_q[k]<=1;
  end
 end
 assign seen=mine&&bits_q[bit_index];
endmodule
(* keep_hierarchy="yes" *) module ot_hbm_landing_safe_seen_group #(parameter integer INDEX=0)(
 input wire clk,reserve_v,input wire [1:0] reserve_bank,packet_bank,input wire [5:0] row,
 input wire landing_write,output wire seen);
 localparam integer LBINDEX=INDEX/4,ROWGROUP=INDEX%4;
 wire [10:0] n;
 ot_hbm_landing_field_inverse #(.W(11)) u_fields(.field({reserve_v,reserve_bank,packet_bank,row}),.inverse(n));
 wire reserve_clear=!n[10]&&n[9:8]==(~2'(LBINDEX));
 wire write_enable=landing_write&&n[7:6]==(~2'(LBINDEX));
 wire [1:0] byte_seen;
 ot_hbm_landing_safe_seen_byte #(.INDEX(2*ROWGROUP)) u_lo(
  .clk(clk),.reserve_clear(reserve_clear),.write_enable(write_enable),.negative_row(n[5:0]),.seen(byte_seen[0]));
 ot_hbm_landing_safe_seen_byte #(.INDEX(2*ROWGROUP+1)) u_hi(
  .clk(clk),.reserve_clear(reserve_clear),.write_enable(write_enable),.negative_row(n[5:0]),.seen(byte_seen[1]));
 assign seen=(n[7:6]==(~2'(LBINDEX)))&&(|byte_seen);
endmodule
module ot_hbm_svc_sm8_landing_bank_sram285_safe #(
 parameter [2:0] BANK=0,parameter integer RESPONSE_DEPTH=8,parameter integer LBANKS=4,parameter integer FMUT=0,
 parameter integer LB=(LBANKS>2)?2:1,parameter integer IW=283+LB
)(
 input wire hbm_clk,hbm_rst_n,stream_clk,stream_rst_n,
 input wire in_v,output wire in_ready,input wire [IW-1:0] in_data,
 output wire overflow,
 input wire reserve_v,input wire [LB-1:0] reserve_bank,input wire [15:0] reserve_epoch,
 input wire [11:0] reserve_total,input wire stop,
 output wire complete_v,output wire [LB-1:0] complete_bank,output wire fault,
 input wire read_v,input wire [LB-1:0] read_bank,input wire [5:0] read_row,
 output wire [255:0] read_data
);
 wire packet_v,packet_take,underflow;wire [IW-1:0] packet;
 ot_hbm_svc_async_fifo_sram285 #(.WIDTH(IW),.DEPTH(RESPONSE_DEPTH),.MUT(FMUT)) u_response(
  .wr_clk(hbm_clk),.wr_rst_n(hbm_rst_n),.wr_valid(in_v),.wr_ready(in_ready),.wr_data(in_data),.wr_overflow(overflow),
  .rd_clk(stream_clk),.rd_rst_n(stream_rst_n),.rd_valid(packet_v),.rd_ready(packet_take),.rd_data(packet),.rd_underflow(underflow));
 wire [10:0] ordinal=packet[IW-1:IW-11];
 wire [LB-1:0] bank=packet[271+LB:272];wire [15:0] epoch=packet[271:256];
 wire [5:0] row=ordinal[8:3];
 wire [3:0] meta_identity,last_here;
 wire [15:0] seen_here;
 reg sticky;
 wire identity_ok=(|meta_identity)&&ordinal[2:0]==BANK&&!(|seen_here);
 wire landing_write=packet_v&&!stop&&!sticky&&identity_ok;
 assign packet_take=packet_v&&!stop&&!sticky;
 assign complete_v=landing_write&&(|last_here);
 assign complete_bank=bank;assign fault=sticky||underflow;
 always @(posedge stream_clk or negedge stream_rst_n)
  if(!stream_rst_n)sticky<=0;else if(packet_take&&!identity_ok)sticky<=1;
 genvar m;
 generate for(m=0;m<4;m=m+1)begin:g_metadata
  ot_hbm_landing_safe_metadata #(.INDEX(m),.BANK(BANK)) u_meta(
   .clk(stream_clk),.rst_n(stream_rst_n),.reserve_v(reserve_v),.reserve_bank(reserve_bank),
   .reserve_epoch(reserve_epoch),.reserve_total(reserve_total),.packet_bank(bank),.row(row),.epoch(epoch),
   .landing_write(landing_write),.identity(meta_identity[m]),.last_packet(last_here[m]));
 end
 for(m=0;m<16;m=m+1)begin:g_seen
  ot_hbm_landing_safe_seen_group #(.INDEX(m)) u_seen(
   .clk(stream_clk),.reserve_v(reserve_v),.reserve_bank(reserve_bank),.packet_bank(bank),.row(row),
   .landing_write(landing_write),.seen(seen_here[m]));
 end endgenerate
 generate if(LBANKS<=2)begin:g_two
 ot_sram_1r1w_128x256_m1_r2c2 u_payload(
  .clk(stream_clk),.r_ce_in(read_v&&!stop&&!sticky),.r_addr_in({read_bank[0],read_row}),.rd_out(read_data),
  .w_ce_in(landing_write),.w_addr_in({bank[0],row}),.wd_in(packet[255:0]),.w_mask_in({256{1'b1}}),
  .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 end else begin:g_four
 ot_sram_1r1w_256x256_m2_r2c2 u_payload(
  .clk(stream_clk),.r_ce_in(read_v&&!stop&&!sticky),.r_addr_in({read_bank,read_row}),.rd_out(read_data),
  .w_ce_in(landing_write),.w_addr_in({bank,row}),.wd_in(packet[255:0]),.w_mask_in({256{1'b1}}),
  .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 end endgenerate
endmodule
`default_nettype wire
