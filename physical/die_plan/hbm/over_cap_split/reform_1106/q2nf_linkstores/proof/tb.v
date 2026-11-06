module tb;
reg clk=0,rst=0,we0=0,we1=0;reg [1:0]addr=0;reg[7:0]din=0;
wire[7:0]g0,g1,gc,n0,n1,nc;
gold G(clk,rst,we0,we1,addr,din,g0,g1,gc);
gate N(clk,rst,we0,we1,addr,din,n0,n1,nc);
integer j;
initial begin
 for(j=0;j<96;j=j+1) begin
  clk=0;rst=(j>=2 && j!=45);addr=j%4;din=(j*19+165)%256;
  we0=(j<16 || (j%3==0));we1=(j<16 || (j%5==0));
  #5;clk=1;#1;
  if(j>=12 && {g0,g1,gc} !== {n0,n1,nc}) begin
   $display("MISMATCH cycle=%0d gold=%h_%h_%h gate=%h_%h_%h",j,g0,g1,gc,n0,n1,nc);$fatal(1);
  end
  #4;
 end
 $display("PASS 96-cycle lockstep with native write/read hold, two stores, shared control and reset");$finish;
end
endmodule
