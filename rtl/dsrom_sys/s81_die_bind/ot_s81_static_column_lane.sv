`timescale 1ns/1ps
`default_nettype none
// BF/Q column candidate: ONE packed calendar word through the equal-frequency
// crossing and every station. Extension and legacy fragments cannot acquire
// separate relay delays. Decode at the consuming tile is wires only.
// Contract: common epoch as ot_s81_static_lane_cross, OFFSET+STAGES pin cycles.
// This source does not stand for an existing CLOSED cfifo/station physical view.
module ot_s81_static_column_lane #(
 parameter integer STAGES=1, OFFSET=4
)(
 input wire w_ck,w_rst_n,input wire [1100:0] i,
 input wire ck,rst_n,
 output wire [1100:0] lane,
 output wire [282:0] x0,output wire [265:0] x1,
 output wire [14:0] cc,output wire [1067:0] bf_xb,
 output wire fault
);
 wire [1100:0] crossed;
 ot_s81_static_lane_cross #(.W(1101),.OFFSET(OFFSET)) u_cross(
   .w_ck(w_ck),.w_rst_n(w_rst_n),.i(i),.r_ck(ck),.r_rst_n(rst_n),.o(crossed),.fault(fault));
 generate if(STAGES==0) begin:g_direct
   assign lane=crossed;
 end else begin:g_stages
   reg [1100:0] pipe[0:STAGES-1];integer j;
   always @(posedge ck or negedge rst_n)
     if(!rst_n) for(j=0;j<STAGES;j=j+1)pipe[j]<=0;
     else begin pipe[0]<=crossed;for(j=1;j<STAGES;j=j+1)pipe[j]<=pipe[j-1];end
   assign lane=pipe[STAGES-1];
 end endgenerate
 assign x0=lane[283:1];assign x1=lane[549:284];assign cc=lane[564:550];
`ifdef OT_S81_STATIC_COLUMN_MUT_SWAP
 assign bf_xb={lane[549:284],lane[266:1],lane[1100:567],lane[565],lane[566]};
`else
 assign bf_xb={lane[549:284],lane[266:1],lane[1100:565]};
`endif
endmodule
`default_nettype wire
