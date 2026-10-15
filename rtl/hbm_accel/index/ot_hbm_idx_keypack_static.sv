`default_nettype none
// Canonical cmp.ik_qdq input is KR FP32 BEFORE quantization. Never requantize
// already-QDQ IK. Compiler reserves all4 head blocks in order, no ready.
// Version1 native packed key: codes512 low, four E8M0 scale bytes high.
module ot_hbm_idx_keypack_static(
 input wire clk,clk_quant,clk_quant_delay,rst_n,
 input wire block_v,input wire[1:0]block_number,source,
 input wire[13:0]local_key,input wire[1023:0]kr_fp32,
 output reg key_v,output reg[543:0]key_data,output reg[36:0]key_address,
 output reg fault
);
 reg[17:0]meta[0:12];
 wire qv,qfault;wire[255:0]codes;wire signed[9:0]e;wire[511:0]unused_qdq;
 ot_hbm_idx_actquant_owned_native quant(.clk(clk_quant),.clk_delay(clk_quant_delay),.rst_n(rst_n),.v(block_v),.fp4(1'b1),.x(kr_fp32),
 .vo(qv),.q(codes),.e(e),.y(unused_qdq),.fault(qfault));
 reg[511:0]packed_codes;reg[31:0]packed_scales;reg[3:0]seen;
 reg[15:0]owner;
 wire[1:0]number=meta[12][1:0];
 wire[13:0]key_index=meta[12][15:2];wire[1:0]src=meta[12][17:16];
 wire[31:0]current_codes;
 wire[127:0]nibbles;
 for(genvar i=0;i<32;i=i+1)assign nibbles[i*4+:4]=codes[i*8+:4];
 localparam[34:0]BASE=35'd19864223744,FENCE=35'd20401094656; //18.5..19GiB
 wire[1:0]stack=2'(int'(key_index)/2736);
 wire[34:0]offset=35'(int'(key_index)%2736)*35'd68;
 wire[34:0]byteaddr=BASE+35'(src)*35'd134217728+offset;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin key_v<=0;key_data<=0;key_address<=0;fault<=0;seen<=0;packed_codes<=0;packed_scales<=0;owner<=0;end
  else begin
   meta[0]<={source,local_key,block_number};
   for(integer t=1;t<13;t=t+1)meta[t]<=meta[t-1];
   key_v<=0;
   if(qv)begin
    if(qfault||e< -127||e>125||key_index>=10944||byteaddr+68>FENCE)fault<=1;
    if(number==0)begin
     if(seen!=0)fault<=1;
     owner<={src,key_index};seen<=4'b0001;
    end else begin
     if(owner!={src,key_index}||seen!=((4'b1<<number)-1))fault<=1;
     seen[number]<=1;
    end
    packed_codes[number*128+:128]<=nibbles;
    packed_scales[number*8+:8]<=8'(e+127);
    if(number==3)begin
     key_v<=1;key_data<={8'(e+127),packed_scales[23:0],nibbles,packed_codes[383:0]};
     key_address<={stack,byteaddr};seen<=0;
    end
   end
  end
 end
endmodule
`default_nettype wire
