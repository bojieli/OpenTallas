module formal_mapped(input wire clk,input wire[15:0]lane_v,input wire[287:0]payload,output wire bad);
 wire[287:0]rc,gc;wire[575:0]rp,gp;wire[1439:0]rq,gq;
 reference #(.ENABLE(1))r(.clk(clk),.lane_v(lane_v),.payload(payload),.compacted(rc),.pair_select(rp),.quad_select(rq));
 mapped g(.clk(clk),.lane_v(lane_v),.payload(payload),.compacted(gc),.pair_select(gp),.quad_select(gq));
 assign bad=({rc,rp,rq}!={gc,gp,gq});
endmodule
