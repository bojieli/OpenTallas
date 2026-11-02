`timescale 1ps/1fs
`default_nettype none
module tb_delay;
reg clk=0,rst_n=0,ea=0;reg[2724:0]d=0;always #416.5 clk=~clk;
wire[2724:0]q7,q8,gold;wire e7,e8,ge;integer cycle=0,checked=0,resets=0,mut=0;
su31_ft_7 old7(.clk(clk),.rst_n(rst_n),.d(d),.ea(ea),.q(q7),.eq(e7));
su31_ft_8 new8(.clk(clk),.rst_n(rst_n),.d(d),.ea(ea),.q(q8),.eq(e8));
ot_dp_st #(.W(2725)) expected_one_added_cycle(.clk(clk),.rst_n(rst_n),.d(q7),.ea(e7),.q(gold),.eq(ge));
wire[2724:0]observed=q8^(mut!=0?2725'd1:2725'd0);
always @(posedge clk)begin #0.001;if(cycle>16)begin
 if(observed!==gold||e8!==ge)$fatal(1,"SU31_DELAY_MISMATCH cycle%0d epoch%b/%b bit0%b/%b",cycle,e8,ge,observed[0],gold[0]);checked=checked+1;
end end
initial begin
void'($value$plusargs("MUT=%d",mut));
for(cycle=0;cycle<4096;cycle=cycle+1)begin
 @(negedge clk);rst_n=(cycle%79)>=4;if(!rst_n)resets=resets+1;ea=(cycle%5)!=0;
 for(integer b=0;b<2725;b=b+1)d[b]=1'((32'(cycle)*32'h9e3779b9+32'(b)*32'h45d9f3b)>>(b%31));
end
@(negedge clk);
$display("SU31_DELAY PASS bits2725+epoch old7 new8 golden+1 checked%0d resetedges%0d",checked,resets);$finish;
end
endmodule
`default_nettype wire
