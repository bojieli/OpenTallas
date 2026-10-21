module reset_gate(input wire clk,input wire reset_early9,input wire[16383:0]data,output wire[16383:0]out);
wire[511:0]rn;
`ifdef BASELINE
reg[8:0]r9;always@(posedge clk)r9<={r9[7:0],reset_early9};assign rn={512{r9[8]}};
`else
ot_s81svc_reset9_n32 u(.clk(clk),.reset_early9(reset_early9),.reset_leaf(rn));
`endif
for(genvar g=0;g<512;g=g+1)begin:loads
reg[31:0]q;always@(posedge clk or negedge rn[g])if(!rn[g])q<=0;else q<=data[32*g+:32];
assign out[32*g+:32]=q;
end
endmodule
