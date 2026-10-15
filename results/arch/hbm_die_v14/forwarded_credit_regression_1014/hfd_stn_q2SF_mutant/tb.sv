module tb;
reg[1:0]a=2'b10;wire[1:0]b;integer i,errors=0;reg last_data;
hfd_stn_q2SF dut(.rst(1'b0),.a(a),.b(b));
initial begin
for(i=0;i<4096;i=i+1)begin
 a[1]=1; a[0]=((i*29+i/7)%11)<5; #1;
 if(i>0 && b[0]!==last_data)errors=errors+1;
 if(b[1]!==0)errors=errors+1;
 #3; a[1]=0; #1;
 if(b[0]!==a[0])errors=errors+1;
 if(b[1]!==1)errors=errors+1;
 last_data=a[0]; #3;
end
$display("OT_CREDIT checks=4096 errors=%0d",errors);
if(errors)$fatal(1,"credit regression");$finish;end
endmodule
