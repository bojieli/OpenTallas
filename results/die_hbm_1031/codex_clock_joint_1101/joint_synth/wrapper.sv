module joint_stage(input clk,reset_in,p_start,output start,reset_out);
`ifdef BOUNDED
 reg r0,r1; always @(posedge clk) begin r0<=reset_in; r1<=r0; end
 wire rst=r1; assign reset_out=r1;
`else
 wire rst=reset_in; assign reset_out=reset_in;
`endif
 ot_dp_landing_origin #(.PAD(0),.EDGE_FALL(0)) u_origin(.clk(clk),.rst_raw_n(rst),.p_start(p_start),.start(start));
endmodule
