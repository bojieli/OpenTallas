`default_nettype none
// Real mapped compiler program storage. Instruction32b bitfields:
// [31]weight [30]query [29]heademit [28]keybeat [27:20]query/head/beatindex
// [19:16]selectorop [15:14]pass [13:6]selectoraddr [5]linkflush [4]linkemit [3:0]linkgroup.
// The external compiler loads eight sequential instructions per SRAM row.
// Start retires a fixed-length program; no client status/ready enters control.
module ot_hbm_idx_calendar_static(
 input wire clk,clk_mem,rst_n,
 input wire program_we,input wire[7:0]program_addr,input wire[255:0]program_data,
 input wire start,input wire[11:0]length,
 output reg issue_v,output reg[31:0]instruction,output reg done,output reg fault
);
 reg active;
 reg[11:0]pc,limit;
 wire read=active;
 wire[255:0]raw;
 reg read_v,read_last;
 reg[2:0]word_index;
 ot_sram_1r1w_256x256_m2_r2c2 store(.clk(clk_mem),.r_ce_in(read),.r_addr_in(pc[10:3]),.rd_out(raw),
 .w_ce_in(program_we),.w_addr_in(program_addr),.wd_in(program_data),.w_mask_in({256{1'b1}}),
 .rr_en(2'd0),.rr_addr(14'd0),.cr_en(2'd0),.cr_sel(16'd0));
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin active<=0;pc<=0;limit<=0;read_v<=0;read_last<=0;word_index<=0;issue_v<=0;instruction<=0;done<=0;fault<=0;end
  else begin
   issue_v<=read_v;done<=read_v&&read_last;instruction<=raw[word_index*32+:32];
   read_v<=read;word_index<=pc[2:0];read_last<=pc+1==limit;
   if(start)begin active<=1;pc<=0;limit<=length;if(active||read_v||length==0||length>2048)fault<=1;end
   else if(active)begin pc<=pc+1;if(pc+1==limit)active<=0;end
   if(program_we&&(active||read_v))fault<=1;
  end
 end
endmodule
`default_nettype wire
