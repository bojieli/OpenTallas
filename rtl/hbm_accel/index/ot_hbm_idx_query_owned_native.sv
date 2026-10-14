`timescale 1ps/1fs
`default_nettype none
// Distinct retained-head clock partition of real FP32→FP4 query hardware.
// Four 8-head banks, control/tag clock, actual actquant clock. Common phase
// functional adapter only; no physical pin/phase/reset lease qualification.
module ot_hbm_idx_query_bank_native #(parameter integer BANK=0)(
 input wire clk,rst_n,start,
 input wire take,input wire [4:0] block_head,input wire [1:0] block_number,
 input wire [15:0] head_weight,
 input wire qv,qfault,input wire signed[9:0] qe,
 input wire [6:0] tag,input wire [255:0] q,
 output wire [4095:0] codes_out,
 output wire [255:0] scales_out,
 output wire [127:0] weights_out,
 output wire [31:0] seen_out,
 output reg fault
);
 reg[511:0]codes[0:7];reg[31:0]scales[0:7];reg[15:0]weights[0:7];reg[3:0]seen[0:7];
 for(genvar h=0;h<8;h=h+1)begin:gout
  assign codes_out[h*512+:512]=codes[h];assign scales_out[h*32+:32]=scales[h];
  assign weights_out[h*16+:16]=weights[h];assign seen_out[h*4+:4]=seen[h];
 end
 integer h,l;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin fault<=0;for(h=0;h<8;h=h+1)seen[h]<=0;end
  else begin
   if(start)for(h=0;h<8;h=h+1)seen[h]<=0;
   if(take&&block_head[4:3]==BANK)begin
    if(block_number==0)weights[block_head[2:0]]<=head_weight;
    else if(weights[block_head[2:0]]!=head_weight)fault<=1;
   end
   if(qv&&tag[6:5]==BANK)begin
    if(qfault||qe < -127||qe>125||seen[tag[4:2]][tag[1:0]])fault<=1;
    else begin
     seen[tag[4:2]][tag[1:0]]<=1;
     scales[tag[4:2]][8*tag[1:0]+:8]<=8'(qe+127);
     for(l=0;l<32;l=l+1)codes[tag[4:2]][128*tag[1:0]+4*l+:4]<=q[8*l+:4];
    end
   end
  end
 end
endmodule
module ot_hbm_idx_query_owned_native(
 input wire clk,clk_quant,clk_quant_delay,input wire [3:0] clk_bank,
 input wire por_n,start,output wire start_ready,
 input wire block_v,output wire block_r,
 input wire [4:0] block_head,input wire [1:0] block_number,
 input wire [1023:0] block_data,input wire [15:0] head_weight,
 output wire ql_v,input wire ql_r,output wire [7:0] ql_head,
 output wire [511:0] ql_codes,output wire [31:0] ql_sc,output wire [15:0] ql_w,
 output reg done,output wire fault
);
 reg active,bad;reg[7:0]accepted;reg[5:0]sent;reg[6:0]tag[0:12];
 wire[3:0]bank_fault;
 wire[16383:0]codes;wire[1023:0]scales;wire[511:0]weights;wire[127:0]seen;
 assign fault=bad||(|bank_fault);
 assign start_ready=!active&&!fault;
 assign block_r=active&&accepted<128&&!fault;
 wire take=block_v&&block_r;
 assign ql_head={3'b0,sent[4:0]};
 assign ql_codes=codes[sent[4:0]*512+:512];
 assign ql_sc=scales[sent[4:0]*32+:32];assign ql_w=weights[sent[4:0]*16+:16];
 assign ql_v=active&&sent<32&&(&seen[sent[4:0]*4+:4])&&!fault;
 wire qv,qfault;wire[255:0]q;wire signed[9:0]qe;wire[511:0]qy;
 ot_hbm_idx_actquant_owned_native quant(.clk(clk_quant),.clk_delay(clk_quant_delay),.rst_n(por_n),.v(take),.fp4(1'b1),.x(block_data),
  .vo(qv),.q(q),.e(qe),.y(qy),.fault(qfault));
 for(genvar b=0;b<4;b=b+1)begin:gbank
  ot_hbm_idx_query_bank_native #(.BANK(b))bank(
   .clk(clk_bank[b]),.rst_n(por_n),.start(start&&start_ready),.take(take),
   .block_head(block_head),.block_number(block_number),.head_weight(head_weight),
   .qv(qv&&active),.qfault(qfault),.qe(qe),.tag(tag[12]),.q(q),
   .codes_out(codes[b*4096+:4096]),.scales_out(scales[b*256+:256]),
   .weights_out(weights[b*128+:128]),.seen_out(seen[b*32+:32]),.fault(bank_fault[b]));
 end
 integer t;
 always @(posedge clk or negedge por_n)begin
  if(!por_n)begin active<=0;accepted<=0;sent<=0;done<=0;bad<=0;end
  else begin
   done<=0;tag[0]<={block_head,block_number};
   for(t=1;t<13;t=t+1)tag[t]<=tag[t-1];
   if(start&&start_ready)begin active<=1;accepted<=0;sent<=0;end
   if(take)begin
    if({block_head,block_number}!==accepted[6:0])bad<=1;
    accepted<=accepted+1;
   end
   if(qv&&!active)bad<=1;
   if(ql_v&&ql_r)begin sent<=sent+1;if(sent==31)begin active<=0;done<=1;end end
  end
 end
endmodule
`default_nettype wire
