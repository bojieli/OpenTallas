module readback_cone(input clk,input [8191:0]partial,output equal);
wire [511:0] bank_word[0:3];reg[2047:0]old_q,new_q;
genvar b;generate for(b=0;b<4;b=b+1)begin:g_bank
wire[511:0]partial_q[0:3];genvar p;for(p=0;p<4;p=p+1)assign partial_q[p]=partial[b*2048+p*512+:512];
assign bank_word[b]=partial_q[0]|partial_q[1]|partial_q[2]|partial_q[3];end endgenerate
always @(posedge clk)begin
for(integer i=0;i<4;i=i+1)old_q[i*512+:512]<=bank_word[i];
new_q[0*512+:512]<=g_bank[0].partial_q[0]|g_bank[0].partial_q[1]|g_bank[0].partial_q[2]|g_bank[0].partial_q[3];
new_q[1*512+:512]<=g_bank[1].partial_q[0]|g_bank[1].partial_q[1]|g_bank[1].partial_q[2]|g_bank[1].partial_q[3];
new_q[2*512+:512]<=g_bank[2].partial_q[0]|g_bank[2].partial_q[1]|g_bank[2].partial_q[2]|g_bank[2].partial_q[3];
new_q[3*512+:512]<=g_bank[3].partial_q[0]|g_bank[3].partial_q[1]|g_bank[3].partial_q[2]|g_bank[3].partial_q[3];
end
assign equal=old_q==new_q;endmodule
