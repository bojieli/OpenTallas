// Default-off component; captures are the actual unreset parent S1 contract.
module hidx_registered_coupon #(parameter ENABLE=0,MUT=0)(
 input wire clk,input wire[15:0]lane_v,input wire[287:0]payload,
 output wire[287:0]compacted,output wire[575:0]pair_select,output wire[1439:0]quad_select);
 wire[287:0]gc;reg[287:0]s1_gc,late_gc;
 hidx_coupon1 #(.ENABLE(ENABLE)) body(.clk(clk),.lane_v(lane_v),.payload(payload),.compacted(gc),.pair_select(pair_select),.quad_select(quad_select));
 always @(posedge clk)begin s1_gc<=gc;late_gc<=s1_gc;end
 assign compacted=MUT==1?gc:MUT==2?late_gc:s1_gc;
endmodule
