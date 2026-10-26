`timescale 1ps/1fs
module tb;
reg clk=0;reg [567:0]q_b=0;wire [34:0]gold,test;
always #416.5 clk=~clk;
ot_hidx_score_hcol g(.clk_pair({2{clk}}),.q_b(q_b),.cs_out(gold[34:3]),.cf_out(gold[2]),.prdy(gold[1:0]));
ot_hidx_score_hcol__oneclk d(.clk(clk),.q_b(q_b),.cs_out(test[34:3]),.cf_out(test[2]),.prdy(test[1:0]));
integer i;initial begin
for(i=0;i<1000;i=i+1)begin
@(clk);#0.001;
if(i>3 && test!==gold) $fatal(1,"CLOCK_MISMATCH edge %0d",i);
q_b=q_b+568'h5298b3497;

end
$display("PASS 1000 half edges period833ps");$finish;end
endmodule
