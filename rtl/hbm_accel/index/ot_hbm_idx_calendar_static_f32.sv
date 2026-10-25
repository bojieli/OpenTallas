`default_nettype none
// FAN32 form of ot_hbm_idx_calendar_static (HBM-IDX6 2026-10-20; native32 census of g2d: calendar.word_index[] drove
// 160 loads = the 8:1 x 32 b instruction word select). Same function, same edges: the word select is a registered
// ONE-HOT (wsel = 1 << pc[2:0], loaded on the edge word_index was; reset 8'h01 = word_index 0), each bit gating 32
// AND inputs; start arrives as two kept copies (start: active / pc / fault, start_l: the 12-bit limit load).
module ot_hbm_idx_calendar_static_f32(
 input wire clk,clk_mem,rst_n,
 input wire program_we,input wire[7:0]program_addr,input wire[255:0]program_data,
 input wire start,start_l,input wire[11:0]length,
 output reg issue_v,output reg[31:0]instruction,output reg done,output reg fault
);
 reg active;
 reg[11:0]pc,limit;
 wire read=active;
 wire[255:0]raw;
 reg read_v,read_last;
 reg[7:0]wsel;
 ot_sram_1r1w_256x256_m2_r2c2 store(.clk(clk_mem),.r_ce_in(read),.r_addr_in(pc[10:3]),.rd_out(raw),
 .w_ce_in(program_we),.w_addr_in(program_addr),.wd_in(program_data),.w_mask_in({256{1'b1}}),
 .rr_en(2'd0),.rr_addr(14'd0),.cr_en(2'd0),.cr_sel(16'd0));
 reg[31:0]word;
 always @* begin word=32'd0; for(integer w=0;w<8;w=w+1) word=word|({32{wsel[w]}}&raw[32*w+:32]); end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin active<=0;pc<=0;limit<=0;read_v<=0;read_last<=0;wsel<=8'h01;issue_v<=0;instruction<=0;done<=0;fault<=0;end
  else begin
   issue_v<=read_v;done<=read_v&&read_last;instruction<=word;
   read_v<=read;wsel<=8'd1<<pc[2:0];read_last<=pc+1==limit;
   if(start_l)limit<=length;
   if(start)begin active<=1;pc<=0;if(active||read_v||length==0||length>2048)fault<=1;end
   else if(active)begin pc<=pc+1;if(pc+1==limit)active<=0;end
   if(program_we&&(active||read_v))fault<=1;
  end
 end
endmodule
`default_nettype wire
