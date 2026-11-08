module tb;
parameter integer MUT=0; reg clk=0;always #5 clk=~clk;
reg[1139:0]heads=0;reg[31:0]grants=0;wire[2279:0]gold,on,off;integer i,j,bad=0,trans=0;
slice G(clk,heads,grants,gold);slice #(.HEAD_REPL(1),.MUT(MUT)) N(clk,heads,grants,on);slice #(.HEAD_REPL(0)) O(clk,heads,grants,off);
initial begin
for(i=0;i<10000;i=i+1)begin
 @(negedge clk);
 for(j=0;j<36;j=j+1)begin if(j<35)heads[32*j+:32]=$random;else heads[1120+:20]=$random;end
 grants=$random;
 @(posedge clk);#1;
 if(i>1)begin if(gold!==on)bad=bad+1; if(gold!==off)$fatal(1,"default-off mismatch"); if(|grants)trans=trans+1;end
end
$display("HEAD_CLASS MUT=%0d cycles=10000 active_grants=%0d output_mismatch_edges=%0d",MUT,trans,bad);
if(MUT==0&&bad!=0)$fatal(1,"candidate mismatch");if(MUT!=0&&bad==0)$fatal(1,"vacuous mutant");$finish;
end
endmodule
