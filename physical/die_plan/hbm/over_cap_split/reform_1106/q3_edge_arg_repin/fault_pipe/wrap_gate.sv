module eqtop #(parameter integer MUT_FP=0)(input wire clk,rst_n,start,input wire [7:0] cfg_g,cfg_gbase,cfg_rank,input wire [3:0] in_slot,in_v,
 input wire [2179:0] in_flit,input wire flush_slot,publish_slot,output wire out_v,output wire [544:0] out_flit,output wire fault);
 ot_hgi_coll_argmax_static_fp #(.MAX_GROUP(192),.MUT_FP(MUT_FP)) u(.clk(clk),.rst_n(rst_n),.start(start),.cfg_g(cfg_g),.cfg_gbase(cfg_gbase),
  .cfg_rank(cfg_rank),.in_slot(in_slot),.in_v(in_v),.in_flit(in_flit),.flush_slot(flush_slot),.publish_slot(publish_slot),
  .out_v(out_v),.out_flit(out_flit),.fault(fault));
endmodule
