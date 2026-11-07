module eqtop(input wire clk,rst_n,start,input wire [7:0] cfg_g,cfg_gbase,cfg_rank,input wire [3:0] in_slot,in_v,
 input wire [2179:0] in_flit,input wire flush_slot,publish_slot,output wire out_v,output wire [544:0] out_flit,output reg fault);
 wire f0;
 ot_hgi_coll_argmax_static #(.MAX_GROUP(192)) u(.clk(clk),.rst_n(rst_n),.start(start),.cfg_g(cfg_g),.cfg_gbase(cfg_gbase),
  .cfg_rank(cfg_rank),.in_slot(in_slot),.in_v(in_v),.in_flit(in_flit),.flush_slot(flush_slot),.publish_slot(publish_slot),
  .out_v(out_v),.out_flit(out_flit),.fault(f0));
 always @(posedge clk or negedge rst_n) if(!rst_n)fault<=1'b0; else fault<=f0;
endmodule
