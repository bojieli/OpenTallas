module ot_hbm_idx_query_static(
 input wire clk,clk_quant,clk_quant_delay,input wire [3:0] clk_bank,
 input wire rst_n,frame_start,
 input wire block_v,input wire [4:0] block_head,input wire [1:0] block_number,
 input wire [1023:0] block_data,input wire [15:0] head_weight,
 input wire emit_v,input wire [4:0] emit_head,
 output reg ql_v,output reg [7:0] ql_head,
 output reg [511:0] ql_codes,output reg [31:0] ql_sc,output reg [15:0] ql_w,
 output reg fault
);
  
  
  
  
 wire rst_core_n;
 ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rst(.clk(clk),.rst_n_in(rst_n),.rst_n(rst_core_n));
 (* keep *) reg fs_r,bv_r,ev_r;(* keep *) reg[4:0]bh_r,eh_r;(* keep *) reg[1:0]bn_r;(* keep *) reg[1023:0]bd_r;(* keep *) reg[15:0]hw_r;
 wire c_v,c_fault;wire[7:0]c_head;wire[511:0]c_codes;wire[31:0]c_sc;wire[15:0]c_w;
 always @(posedge clk)begin
  fs_r<=frame_start;bv_r<=block_v;bh_r<=block_head;bn_r<=block_number;bd_r<=block_data;hw_r<=head_weight;ev_r<=emit_v;eh_r<=emit_head;
  ql_v<=c_v;ql_head<=c_head;ql_codes<=c_codes;ql_sc<=c_sc;ql_w<=c_w;fault<=c_fault;
 end
 ot_hbm_idx_query_static_core core(.clk(clk),.clk_quant(clk_quant),.clk_quant_delay(clk_quant_delay),.clk_bank(clk_bank),.rst_n(rst_core_n),
  .frame_start(fs_r),.block_v(bv_r),.block_head(bh_r),.block_number(bn_r),.block_data(bd_r),.head_weight(hw_r),
  .emit_v(ev_r),.emit_head(eh_r),.ql_v(c_v),.ql_head(c_head),.ql_codes(c_codes),.ql_sc(c_sc),.ql_w(c_w),.fault(c_fault));
endmodule
