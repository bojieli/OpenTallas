`default_nettype none
// Real existing relay primitive; every payload bit captures on every edge.
module ot_hbm_gather_transport_bundle #(parameter integer W=83,EDGES=0,RESET_RELAY=1)(
 input wire clk,rst_n,input wire[W-1:0]d,output wire[W-1:0]q);
 wire[W-1:0]data[0:EDGES];assign data[0]=d;assign q=data[EDGES];
 for(genvar n=0;n<EDGES;n=n+1)begin:stage
  ot_hbm_rly #(.W(W),.RS_RELAY(RESET_RELAY)) relay(.ck(clk),.rs(rst_n),.i(data[n]),.o(data[n+1]));
 end
endmodule
`default_nettype wire
