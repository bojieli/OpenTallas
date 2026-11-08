module q2nf_cfg_miter(input[5:0]step,input[7:0]row,input[1535:0]assembly,input[63:0]metadata,input draining,output ok);
wire[36:0] a,b;
q2nf_cfg_ref ref_u(step,row,assembly,metadata,draining,a);
ot_bodyctl_cfg_case new_u(step,row,assembly,metadata,draining,b);
assign ok=(a==b);
endmodule
