// PRIVATE SOURCE PROTOTYPE. Not bound to production. No synthetic Liberty.
module hbm_private_reset_station #(parameter ENABLE=0)(input clock_in, reset_in_n,
 output clock_out,reset_out_n);
 generate if(ENABLE) begin: enabled
 wire hi,q1,q2,d2;
 TIEHIx1_ASAP7_75t_R tiehi(.H(hi));
 BUFx12f_ASAP7_75t_R clock_buffer(.A(clock_in),.Y(clock_out));
 DFFASRHQNx1_ASAP7_75t_R ff1(.CLK(clock_out),.D(hi),.RESETN(reset_in_n),.SETN(hi),.QN(q1));
 INVx1_ASAP7_75t_R inv1(.A(q1),.Y(d2));
 DFFASRHQNx1_ASAP7_75t_R ff2(.CLK(clock_out),.D(d2),.RESETN(reset_in_n),.SETN(hi),.QN(q2));
 INVx1_ASAP7_75t_R inv2(.A(q2),.Y(reset_out_n));
 end else begin: disabled
 // No production use or bypass: disabled prototype has no active interface.
 assign clock_out=1'bx;
 assign reset_out_n=1'bx;
 end endgenerate
endmodule

// Local face pair shares its owning station's true clock Y and TIEHI H.
module hbm_private_reset_face(input clock_in,reset_in_n,hi,output reset_out_n);
 wire q1,q2,d2;
 DFFASRHQNx1_ASAP7_75t_R ff1(.CLK(clock_in),.D(hi),.RESETN(reset_in_n),.SETN(hi),.QN(q1));
 INVx1_ASAP7_75t_R inv1(.A(q1),.Y(d2));
 DFFASRHQNx1_ASAP7_75t_R ff2(.CLK(clock_in),.D(d2),.RESETN(reset_in_n),.SETN(hi),.QN(q2));
 INVx1_ASAP7_75t_R inv2(.A(q2),.Y(reset_out_n));
endmodule
