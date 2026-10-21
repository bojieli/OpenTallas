module smj_gate(input wire clk,input wire rst,input wire load,input wire[511:0]d,output wire[511:0]q);
`ifdef BASELINE
reg rn,we;always @(posedge clk)begin rn<=rst;we<=load;end
reg[511:0]held;always @(posedge clk or negedge rn)if(!rn)held<=0;else if(we)held<=d;
assign q=held;
`else
dsdv_svc_smj_payload_n32 u_payload(.clk(clk),.d(d),.q(q));
`endif
endmodule
