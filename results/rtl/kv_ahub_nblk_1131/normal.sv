module m(input clk,input[13:0]T,output pass);
reg[19:0]a,b;
always@(posedge clk)for(integer s=0;s<4;s=s+1)begin
 a[5*s+:5]<=(T>14'(128*s))?5'(((T-14'(128*s)-14'd1)>>9)+14'd1):5'd0;
 b[5*s+:5]<=(T>14'(128*s))?5'(((T-14'(128*s)-14'd1)>>9)+14'd1):5'd0;
end
reg[63:0]ma,mb;
always@*begin
ma=0;mb=0;
for(integer s=0;s<4;s=s+1)for(integer k=0;k<16;k=k+1)begin
if(k<a[5*s+:5])ma[4*k+s]=1;
if(k<b[5*s+:5])mb[4*k+s]=1;
end
end
assign pass=ma==mb;
endmodule
