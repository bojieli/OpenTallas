module reset_compact_gate(input wire clk,input wire reset_early9,input wire[4223:0]data,output wire[4223:0]out);
wire[131:0]rn;
`ifdef BASELINE
reg[8:0]r9;always@(posedge clk)r9<={r9[7:0],reset_early9};reg[1:0]rs;always@(posedge clk or negedge r9[8])if(!r9[8])rs<=0;else rs<={rs[0],1'b1};assign rn={132{rs[1]}};
`else
ot_s81svc_reset132_n32 u(.clk(clk),.reset_early9(reset_early9),.reset_leaf(rn));
`endif
for(genvar g=0;g<132;g=g+1)begin:loads
reg[31:0]q;always@(posedge clk or negedge rn[g])if(!rn[g])q<=0;else q<=data[32*g+:32];
assign out[32*g+:32]=q;
end
endmodule
