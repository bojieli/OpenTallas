module tb;reg c0=0,c1=0;always #5 c0=~c0;initial begin #2;forever #5 c1=~c1;end
reg[1:0]rn=0;reg qv=0;reg[567:0]q=0;reg[543:0]key=0;wire[2225:0]a,b;integer mut=0,seed=2211,k,j,checks=0,errors=0;
wire[567:0]q1=(mut!=0)?q^(568'b1<<32):q;
capture_gold g(1'b0,{c1,c0},rn,{qv,qv},{q,q},{key,key},qv,q,key,a);
capture_new n(1'b0,{c1,c0},rn,{qv,qv},{q1,q},{key,key},qv,q,key,b);
always @(negedge c0 or negedge c1)begin if(checks>4 && a!==b)errors=errors+1;checks=checks+1;end
initial begin if($value$plusargs("MUT=%d",mut))begin end
for(k=0;k<12000;k=k+1)begin @(negedge c0);#1;rn=2'($random(seed));qv=1'($random(seed));for(j=0;j<17;j=j+1)begin q[32*j+:32]=$random(seed);key[32*j+:32]=$random(seed);end q[567:544]=24'($random(seed));end
#20;$display("HCOL_CAPTURE checks=%0d errors=%0d mutant=%0d",checks,errors,mut);if(errors!=0)$fatal(1,"HCOL_CAPTURE FAIL");$display("HCOL_CAPTURE PASS");$finish;end endmodule
