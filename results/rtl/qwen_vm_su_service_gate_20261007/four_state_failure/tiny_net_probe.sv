module net_probe;
reg clk=0;always #5 clk=~clk;
wire [511:0] bank_word[0:3];genvar b,p;
generate for(b=0;b<4;b=b+1)begin:g_bank
reg [511:0] partial_q[0:3];
for(p=0;p<4;p=p+1)begin:g_partial
always @(posedge clk)partial_q[p]<=p==0?32'hbe916038:0;
end
assign bank_word[b]=partial_q[0]|partial_q[1]|partial_q[2]|partial_q[3];
end endgenerate
initial begin #20;$display("bank=%h rhs=%h",bank_word[0][31:0],g_bank[0].partial_q[0][31:0]);if(bank_word[0][31:0]!==32'hbe916038)$fatal(1,"netarray propagation");$finish;end
endmodule
