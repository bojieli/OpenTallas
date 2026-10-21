module fmem_gate(input clk,we,input[4:0]wa,ra,input[2119:0]wd,input[8:0]we_reps,output[2119:0]rd);
`ifdef FMEM_BASELINE
 dsdv_svc_fmem_ref #(.W(2120),.BYP(1))dut(.clk(clk),.we(we),.wa(wa),.ra(ra),.wd(wd),.rd(rd));
`else
 dsdv_svc_fmem #(.W(2120),.BYP(1))dut(.clk(clk),.we(we),.wa(wa),.ra(ra),.wd(wd),.rd(rd),.we_reps(we_reps));
`endif
endmodule
