`default_nettype none
// Five real 1R1W macros provide one canonical SM row per fixed read edge.
// Filling costs five 256-bit sectors/row. This burst bandwidth does not alter
// the PHY prefetch lower bound or prove the compiler fill/read calendar fits.
module ot_hbm_svc_static_sm_rows (
 input wire clk,rst_n,
 input wire open_v,open_bank,input wire [15:0] open_epoch,input wire [6:0] open_count,
 input wire fill_v,fill_bank,input wire [15:0] fill_epoch,input wire [5:0] fill_row,
 input wire [2:0] fill_part,input wire [255:0] fill_data,input wire [9:0] fill_tag,
 input wire read_v,read_bank,input wire [15:0] read_epoch,input wire [5:0] read_row,input wire [9:0] read_tag,
 input wire retire_v,retire_bank,input wire [15:0] retire_epoch,
 output wire [1:0] block_ready,bank_owned,output reg fault,
 output wire [1098:0] out_packet
);
 reg [1:0] owned;reg [15:0] epoch[0:1];reg [6:0] count[0:1];
 reg [4:0] seen[0:127];reg [9:0] tags[0:127];
 reg out_valid;reg [9:0] out_tag;wire [255:0] payload[0:4];
 wire [6:0] fill_addr={fill_bank,fill_row},read_addr={read_bank,read_row};
 reg [1:0] ready;integer i,b,r;
 always @*begin
  ready=owned;
  for(b=0;b<2;b=b+1)begin
   if(count[b]==0)ready[b]=0;
   for(r=0;r<64;r=r+1)if(r<count[b]&&seen[b*64+r]!=5'b11111)ready[b]=0;
  end
 end
 assign block_ready=ready;assign bank_owned=owned;
 wire fill_ok=fill_v&&owned[fill_bank]&&fill_epoch==epoch[fill_bank]&&
   {1'b0,fill_row}<count[fill_bank]&&fill_part<5&&!seen[fill_addr][fill_part]&&
   (seen[fill_addr]==0||tags[fill_addr]==fill_tag)&&!fault&&
   !(retire_v&&retire_bank==fill_bank);
 wire read_ok=read_v&&ready[read_bank]&&read_epoch==epoch[read_bank]&&
   {1'b0,read_row}<count[read_bank]&&read_tag==tags[read_addr]&&!fault&&
   !(retire_v&&retire_bank==read_bank);
 assign out_packet={out_valid&&!fault,out_tag,payload[4][63:0],payload[3],payload[2],payload[1],payload[0]};
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   owned<=0;epoch[0]<=0;epoch[1]<=0;count[0]<=0;count[1]<=0;fault<=0;out_valid<=0;out_tag<=0;
   for(i=0;i<128;i=i+1)begin seen[i]<=0;tags[i]<=0;end
  end else begin
   out_valid<=read_ok;if(read_ok)out_tag<=tags[read_addr];
   if(open_v)begin
    if(owned[open_bank]||open_count==0||open_count>64||
       (retire_v&&retire_bank==open_bank))fault<=1;
    else begin
     owned[open_bank]<=1;epoch[open_bank]<=open_epoch;count[open_bank]<=open_count;
     for(i=0;i<64;i=i+1)begin seen[open_bank*64+i]<=0;tags[open_bank*64+i]<=0;end
    end
   end
   if(fill_v&&!fill_ok)fault<=1;
   if(fill_ok)begin seen[fill_addr][fill_part]<=1;if(seen[fill_addr]==0)tags[fill_addr]<=fill_tag;end
   if(read_v&&!read_ok)fault<=1;
   if(retire_v)begin
    if(!owned[retire_bank]||retire_epoch!=epoch[retire_bank]||
      (open_v&&open_bank==retire_bank)||(fill_v&&fill_bank==retire_bank)||
      (read_v&&read_bank==retire_bank))fault<=1;
    else owned[retire_bank]<=0;
   end
  end
 end
 genvar p;
 generate for(p=0;p<5;p=p+1)begin: g_part
  ot_sram_1r1w_128x256_m1_r2c2 u_payload (
   .clk(clk),.r_ce_in(read_ok),.r_addr_in(read_addr),.rd_out(payload[p]),
   .w_ce_in(fill_ok&&fill_part==p),.w_addr_in(fill_addr),.wd_in(fill_data),
   .w_mask_in({256{1'b1}}),.rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 end endgenerate
endmodule
`default_nettype wire
