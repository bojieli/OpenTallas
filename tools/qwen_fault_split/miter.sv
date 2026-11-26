// HCSETUP 11-26: split sticky fault is the default (SPLIT_STICKY_FAULT = 1); u_old in tb_xhead3 pins the legacy single flop (0).
module fault_split_miter(input ck,rst_n,input [8:0] causes, output eq);
reg old;
wire candidate;
always @(posedge ck or negedge rst_n)
 if(!rst_n) old <= 0; else if (|causes) old <= 1;
`ifdef MUTANT
 ot_qfd_xh_sticky_fault #(.MUT(1)) u(ck,rst_n,causes,candidate);
`else
 ot_qfd_xh_sticky_fault u(ck,rst_n,causes,candidate);
`endif
assign eq = old == candidate;
endmodule
