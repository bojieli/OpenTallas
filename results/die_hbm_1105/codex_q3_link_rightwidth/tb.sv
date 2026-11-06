`timescale 1ps/1ps
module tb;
reg ck=0,we=0;reg [5:0] wa=0,ra=0;reg [140:0] din=0;wire [140:0] a,b,m;
leaf_old #(.W(141)) old(.ck(ck),.we(we),.wa(wa),.ra(ra),.din(din),.dout(a));
leaf_new #(.W(141)) new_good(.ck(ck),.we(we),.wa(wa),.ra(ra),.din(din),.dout(b));
leaf_new #(.W(141),.MUT(1)) mutant(.ck(ck),.we(we),.wa(wa),.ra(ra),.din(din),.dout(m));
integer i,j,err=0,mut=0,checks=0;reg [31:0] rng=32'h348912bc;
function automatic [31:0] rnd; begin rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);rnd=rng;end endfunction
initial begin
 for(i=0;i<12000;i=i+1) begin
  ck=0; #1;
  we=(i<128)?1:(rnd()%4!=0);wa=(i<128)?i%64:rnd()%64;
  ra=(i<128)?i%64:((i%3==0)?wa:rnd()%64);
  for(j=0;j<5;j=j+1) din=(din<<32)|rnd();
  #415;ck=1;#2;
  if(i>8)begin checks=checks+1;if(a!==b)begin err=err+1;if(err<4)$display("DIFF %0d",i);end if(a!==m)mut=mut+1;end
  #415;
 end
 $display("STORE_EQ checks=%0d mismatches=%0d mutant_diffs=%0d PIN_CYCLES=0",checks,err,mut);
 if(err!=0||mut==0)$fatal(1,"proof failed");$finish;
end
endmodule
