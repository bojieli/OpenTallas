module ot_hbm_idx_query_static_core(
 input wire clk,clk_quant,clk_quant_delay,input wire [3:0] clk_bank,
 input wire rst_n,frame_start,
 input wire block_v,input wire [4:0] block_head,input wire [1:0] block_number,
 input wire [1023:0] block_data,input wire [15:0] head_weight,
 input wire emit_v,input wire [4:0] emit_head,
 output reg ql_v,output reg [7:0] ql_head,
 output wire [511:0] ql_codes,output wire [31:0] ql_sc,output reg [15:0] ql_w,
 output wire fault
);
  
  
  
  
  
  
  
 reg bad,bfault;reg[6:0]tag[0:12];
 reg[15:0]weights[0:31];reg[3:0]seen[0:31];
 wire qv,qfault;wire[255:0]q;wire signed[9:0]qe;wire[511:0]qy;
 assign fault=bad||bfault;
 ot_hbm_idx_actquant_owned_native #(.XRF(1)) quant(.clk(clk),.clk_delay(clk),.rst_n(rst_n),.v(block_v),.fp4(1'b1),.x(block_data),
 .vo(qv),.q(q),.e(qe),.y(qy),.fault(qfault));
 wire[4:0]qh=tag[12][6:2];wire[1:0]qp=tag[12][1:0];
 wire qok=!(qfault||qe < -127||qe>125||seen[qh][qp]);
  
 reg[127:0]qcode;
 always @*for(integer l=0;l<32;l=l+1)qcode[4*l+:4]=q[8*l+:4];
 wire[7:0]qscale=8'(qe+127);
 for(genvar p=0;p<4;p=p+1)begin:gcode
  ot_sram_1r1w_32x128_m1 mem(.clk(clk),.r_ce_in(emit_v),.r_addr_in(emit_head),.rd_out(ql_codes[p*128+:128]),
   .w_ce_in(qv&&qok&&qp==2'(p)),.w_addr_in(qh),.wd_in(qcode),.w_mask_in({128{1'b1}}));
 end
 wire[127:0]sc_rd;
 ot_sram_1r1w_32x128_m1 scmem(.clk(clk),.r_ce_in(emit_v),.r_addr_in(emit_head),.rd_out(sc_rd),
  .w_ce_in(qv&&qok),.w_addr_in(qh),.wd_in({16{qscale}}),
  .w_mask_in({96'd0,(qp==2'd3)?8'hff:8'h00,(qp==2'd2)?8'hff:8'h00,(qp==2'd1)?8'hff:8'h00,(qp==2'd0)?8'hff:8'h00}));
 assign ql_sc=sc_rd[31:0];
  
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin bfault<=0;for(integer h=0;h<32;h=h+1)seen[h]<=0;end
  else begin
   if(frame_start)for(integer h=0;h<32;h=h+1)seen[h]<=0;
   if(block_v&&block_number!=0&&weights[block_head]!=head_weight)bfault<=1;
   if(qv)begin
    if(!qok)bfault<=1;
    else seen[qh][qp]<=1;
   end
  end
 end
 always @(posedge clk)if(block_v&&block_number==0)weights[block_head]<=head_weight;
 always @(posedge clk)begin
  tag[0]<={block_head,block_number};
  for(integer t=1;t<13;t=t+1)tag[t]<=tag[t-1];
  ql_head<={3'b0,emit_head};ql_w<=weights[emit_head];
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin bad<=0;ql_v<=0;end
  else begin
   ql_v<=emit_v;
   if(emit_v && !(&seen[emit_head]))begin bad<=1;ql_v<=0;end
   if(frame_start && (block_v||emit_v||qv))bad<=1;
  end
 end
endmodule
