module tb;
reg clk=0;always #5 clk=~clk;
reg[343:0]entry=0;reg[7:0]entry_tag=0;
wire[343:0]g,c,m1,m2;
ot_tkm_merge_gold gold(entry,entry_tag,g);
ot_tkm_merge_parallel candidate(entry,entry_tag,c);
ot_tkm_merge_parallel #(.MUT(1)) mutant1(entry,entry_tag,m1);
ot_tkm_merge_parallel #(.MUT(2)) mutant2(entry,entry_tag,m2);
reg[343:0]gq,cq;integer n,j,bad=0,m1bad=0,m2bad=0;
always @(posedge clk)begin gq<=g;cq<=c;end
initial begin
for(n=0;n<20000;n=n+1)begin
 @(negedge clk);
 for(j=0;j<11;j=j+1)entry=(entry<<32)^$random;
 entry_tag=$random;
 case(n%7)
 0:entry[86+:86]=entry[0+:86];
 1:begin entry[172+:86]=entry[0+:86];entry_tag[5:4]=entry_tag[1:0];end
 2:begin entry[258+:86]=entry[86+:86];entry_tag[7:6]=entry_tag[3:2];end
 3:begin entry={4{86'h1fffffffffffffffffffff}};entry_tag=0;end
 4:entry=0;
 endcase
 @(posedge clk);#1;
 if(gq!==cq)bad=bad+1;
 if(g!==m1)m1bad=m1bad+1;
 if(g!==m2)m2bad=m2bad+1;
end
$display("LOCKSTEP cycles=%0d bad=%0d middle_order_mutant=%0d duplicated_middle_mutant=%0d",n,bad,m1bad,m2bad);
if(bad!=0||m1bad==0||m2bad==0)$fatal(1,"proof/control failure");
$finish;
end
endmodule
