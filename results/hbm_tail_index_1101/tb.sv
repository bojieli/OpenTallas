module tb;
reg clk=0,rst=0,launch=0,cap=0;always #5 clk=~clk;
wire[4:0]a,b;wire[8:0]aa,ba;wire ax,bx;
calendar gold(clk,rst,launch,cap,a,aa,ax);
calendar #(.PREDECODE_INDEX(1)) dut(clk,rst,launch,cap,b,ba,bx);
integer checks=0,errors=0,seed=1234567,k,f;
reg[511:0]ages=0;
always @(negedge clk)if(rst)begin
checks=checks+1;ages[aa]=1;
if({a,aa,ax}!=={b,ba,bx})begin errors=errors+1;if(errors<3)$display("DIFF age%0d index%0d/%0d",aa,a,b);end
end
initial begin
repeat(4)@(negedge clk);#1;rst=1;
for(f=0;f<20;f=f+1)begin
 launch=1;@(negedge clk);#1;launch=0;
 repeat(205)@(negedge clk);#1;cap=1;@(negedge clk);#1;cap=0;
end
for(k=0;k<16000;k=k+1)begin
 @(negedge clk);#1;
 rst=($unsigned($random(seed))%67!=0);
 launch=($unsigned($random(seed))%43==0);
 cap=($unsigned($random(seed))%59==0);
end
@(negedge clk);#1;
$display("TAIL_INDEX checks=%0d errors=%0d visitedages=%0d",checks,errors,$countones(ages));
if(errors!=0||checks<18000||$countones(ages)<199)$fatal(1,"TAIL_INDEX FAIL");
$display("TAIL_INDEX PASS");$finish;
end
endmodule
