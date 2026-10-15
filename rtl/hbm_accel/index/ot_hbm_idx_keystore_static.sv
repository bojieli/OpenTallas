`default_nettype none
// Fixed68B key store serializer. Compiler samples one key, then reserves four
// sector store slots. Byte masks preserve adjacent packed keys at every offset.
module ot_hbm_idx_keystore_static(
 input wire clk,rst_n,
 input wire key_v,input wire[543:0]key_data,input wire[36:0]key_address,
 input wire store_slot,input wire[1:0]store_part,
 output reg write_v,output reg[36:0]write_address,
 output reg[255:0]write_data,output reg[31:0]write_mask,
 output reg fault
);
 reg[543:0]held;reg[36:0]address;reg valid;reg[1:0]next_part;
 wire[1023:0]shifted={480'd0,held}<<(int'(address[4:0])*8);
 wire[127:0]mask=((128'd1<<68)-1)<<address[4:0];
 wire[31:0]selected_mask=mask[store_part*32+:32];
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin held<=0;address<=0;valid<=0;next_part<=0;write_v<=0;write_address<=0;write_data<=0;write_mask<=0;fault<=0;end
  else begin
   write_v<=store_slot&&selected_mask!=0;
   write_address<={address[36:5],5'd0}+37'(int'(store_part)*32);
   write_data<=shifted[store_part*256+:256];write_mask<=selected_mask;
   if(key_v)begin held<=key_data;address<=key_address;valid<=1;next_part<=0;if(valid&&!(store_slot&&store_part==3))fault<=1;end
   if(store_slot)begin
    if(!valid||store_part!=next_part)fault<=1;
    next_part<=store_part+1;
    if(store_part==3&&!key_v)valid<=0;
   end
  end
 end
endmodule
`default_nettype wire
