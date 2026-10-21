module psel_gate(input wire clk,rst_n,step,oddstep,input wire[1023:0]banks,output wire[511:0]word0,word1);
`ifdef BASELINE
reg p,sel;wire pn=p^(step&&oddstep);
always@(posedge clk or negedge rst_n)if(!rst_n)p<=0;else p<=pn;
always@(posedge clk)sel<=pn;
assign word0=sel?banks[1023:512]:banks[511:0];assign word1=sel?banks[511:0]:banks[1023:512];
`else
dsdv_svc_pword_pick_n32 u(.clk(clk),.rst_n(rst_n),.step(step),.oddstep(oddstep),.banks(banks),.word0(word0),.word1(word1));
`endif
endmodule
