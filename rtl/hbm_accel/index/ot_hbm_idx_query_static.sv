`default_nettype none
// Static counterpart of query_owned_native. Same exact quant and retained
// arithmetic; all input/output issue decisions are compiler slots. The compiler
// must leave >=14 edges after the last head block before its emit slot.
module ot_hbm_idx_query_static(
 input wire clk,clk_quant,clk_quant_delay,input wire [3:0] clk_bank,
 input wire rst_n,frame_start,
 input wire block_v,input wire [4:0] block_head,input wire [1:0] block_number,
 input wire [1023:0] block_data,input wire [15:0] head_weight,
 input wire emit_v,input wire [4:0] emit_head,
 output reg ql_v,output reg [7:0] ql_head,
 output reg [511:0] ql_codes,output reg [31:0] ql_sc,output reg [15:0] ql_w,
 output wire fault
);
 reg bad;reg[6:0]tag[0:12];wire[3:0]bf;
 wire[16383:0]codes;wire[1023:0]scales;wire[511:0]weights;wire[127:0]seen;
 wire qv,qfault;wire[255:0]q;wire signed[9:0]qe;wire[511:0]qy;
 assign fault=bad||(|bf);
 ot_hbm_idx_actquant_owned_native quant(.clk(clk_quant),.clk_delay(clk_quant_delay),.rst_n(rst_n),.v(block_v),.fp4(1'b1),.x(block_data),
 .vo(qv),.q(q),.e(qe),.y(qy),.fault(qfault));
 for(genvar b=0;b<4;b=b+1)begin:gbank
  ot_hbm_idx_query_bank_native #(.BANK(b))bank(.clk(clk_bank[b]),.rst_n(rst_n),.start(frame_start),.take(block_v),
   .block_head(block_head),.block_number(block_number),.head_weight(head_weight),
   .qv(qv),.qfault(qfault),.qe(qe),.tag(tag[12]),.q(q),
   .codes_out(codes[b*4096+:4096]),.scales_out(scales[b*256+:256]),
   .weights_out(weights[b*128+:128]),.seen_out(seen[b*32+:32]),.fault(bf[b]));
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin bad<=0;ql_v<=0;ql_head<=0;ql_codes<=0;ql_sc<=0;ql_w<=0;end
  else begin
   tag[0]<={block_head,block_number};
   for(integer t=1;t<13;t=t+1)tag[t]<=tag[t-1];
   ql_v<=emit_v;
   ql_head<={3'b0,emit_head};ql_codes<=codes[emit_head*512+:512];
   ql_sc<=scales[emit_head*32+:32];ql_w<=weights[emit_head*16+:16];
   if(emit_v && !(&seen[emit_head*4+:4]))begin bad<=1;ql_v<=0;end
   if(frame_start && (block_v||emit_v||qv))bad<=1;
  end
 end
endmodule
`default_nettype wire
