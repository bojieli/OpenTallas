`timescale 1ns/1ps
module tb #(parameter MUT=0);
reg clk=0;always #5 clk=~clk;reg rst=0;reg [68:0] ui=0;reg [35:0] di=0;
wire [68:0] ur,ud;wire [35:0] dr,dd;wire [127:0] gates;
ot_s81_engram_rly reference(clk,rst,ui,di,ur,dr);
ot_s81_engram_rly_split #(.MUT(MUT)) actual({18{clk}},rst,ui,di,ud,dd,gates);
integer c,fail=0,comparisons=0;
initial begin
for(c=0;c<4096;c=c+1)begin
 @(negedge clk);rst=(c%257>=3);ui={$random,$random,$random};di={$random,$random};
 @(posedge clk);#1;
 if(c>8)begin
 comparisons=comparisons+201;
 if(ur!==ud)fail=fail+1;
 if(dr!==dd)fail=fail+1;
 if(gates!=={4{dr[35:4]}})fail=fail+1;
 end
end
if(MUT==0&&fail==0)$display("PASS same-edge actual split relay 4096cycles comparisons=%0d resetepisodes=16 zeroaddededges",comparisons);
else if(MUT==27&&fail>0)$display("REJECT stopped new root mutant27 mismatchgroups=%0d",fail);
else $fatal(1,"unexpected fail=%0d MUT=%0d",fail,MUT);
$finish;
end
endmodule
