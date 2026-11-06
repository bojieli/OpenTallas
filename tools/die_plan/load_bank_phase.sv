module gold(input clk,rst_n,set_n,en,input [2:0] d,output [2:0] out);
reg [2:0] q;
always @(posedge clk) q[0] <= en ? d[0] : q[0];
always @(posedge clk or negedge rst_n or negedge set_n)
 if (!rst_n) q[1]<=0; else if (!set_n) q[1]<=1; else q[1]<=en?d[1]:q[1];
always @(posedge clk) q[2]<=d[2];
assign out={(q[0]&q[1])|q[2],~(q[1]|q[2])|q[0],q[0]^q[1]^q[2]};
endmodule
module gate(input clk,rst_n,set_n,en,input [2:0] d,output [2:0] out);
reg [2:0] orig,bank;
always @(posedge clk) orig[0] <= en?d[0]:orig[0];
always @(posedge clk or negedge rst_n or negedge set_n)
 if (!rst_n) orig[1]<=0; else if (!set_n) orig[1]<=1; else orig[1]<=en?d[1]:orig[1];
always @(posedge clk) orig[2]<=d[2];
always @(posedge clk) bank[0] <= en?d[0]:orig[0];
always @(posedge clk or negedge rst_n or negedge set_n)
 if (!rst_n) bank[1]<=0; else if (!set_n) bank[1]<=1; else bank[1]<=en?d[1]:orig[1];
`ifdef MUTANT
always @(posedge clk) bank[2]<=orig[2];
`else
always @(posedge clk) bank[2]<=d[2];
`endif
assign out={(bank[0]&bank[1])|bank[2],~(bank[1]|bank[2])|bank[0],bank[0]^bank[1]^bank[2]};
endmodule
