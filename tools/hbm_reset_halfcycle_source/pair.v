// PRIVATE default-off functional source. Native timing and physical age remain NULL.
module hbm_halfcycle_pair #(parameter ENABLE=0)(input clock_in,reset_in_n,hi,
 output reset_out_n);
 generate if(ENABLE) begin: enabled
 wire nc,q1,release1,q2;
`ifdef MUT_NO_CLOCK_INV
 assign nc=clock_in;
`else
 INVx1_ASAP7_75t_R clock_inv(.A(clock_in),.Y(nc));
`endif
`ifdef MUT_OWNERSHIP
 wire owned_reset=1'b1;
`else
 wire owned_reset=reset_in_n;
`endif
 DFFASRHQNx1_ASAP7_75t_R ff1(.CLK(nc),.D(hi),.RESETN(owned_reset),.SETN(hi),.QN(q1));
 INVx1_ASAP7_75t_R release_inv(.A(q1),.Y(release1));
`ifdef MUT_RAW_FF2_RESET
 wire stage_reset=reset_in_n;
`else
 wire stage_reset=release1;
`endif
 DFFASRHQNx1_ASAP7_75t_R ff2(.CLK(clock_in),.D(hi),.RESETN(stage_reset),.SETN(hi),.QN(q2));
 INVx6_ASAP7_75t_R output_inv(.A(q2),.Y(reset_out_n));
 end else begin: disabled
 assign reset_out_n=1'bx;
 end endgenerate
endmodule
module hbm_halfcycle_station #(parameter ENABLE=0)(input clock_in,reset_in_n,
 output clock_out,reset_out_n,hi);
 generate if(ENABLE) begin: enabled
 TIEHIx1_ASAP7_75t_R tiehi(.H(hi));
 BUFx12f_ASAP7_75t_R cb(.A(clock_in),.Y(clock_out));
 hbm_halfcycle_pair #(.ENABLE(1)) pair(clock_out,reset_in_n,hi,reset_out_n);
 end else begin
 assign clock_out=1'bx;assign reset_out_n=1'bx;assign hi=1'bx;
 end endgenerate
endmodule
