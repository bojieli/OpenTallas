`ifndef SYNTHESIS
`timescale 1ns/1ps
module tb #(parameter MUT=0);
 reg ck=0;always #5 ck=~ck;
 reg[15:0]d=0;wire[15:0]q;reg delayed7=0;
 qfd_c_reset_group16_safe u(ck,d,q);
 always@(posedge ck)delayed7<=q[7];
 wire[15:0]observed=(MUT==1)?{q[15:8],delayed7,q[6:0]}:q;
 integer n=0,errors=0,checks=0;
 function automatic[15:0] pattern(input integer t);
  integer b;
  begin
   pattern=0;
   if(t>=8)for(b=0;b<16;b=b+1)
    // Independent pulse periods/widths plus repeated common assertion windows.
    pattern[b]=(t%97>=6)&&(((t/(1+b%3)+b*7)^(t>>(b%6)))&1);
  end
 endfunction
 always@(negedge ck)begin
  n=n+1;d=pattern(n);
  if(n==4096)begin
   if(errors)$fatal(1,"SAFE_RESET_GROUP_FAIL MUT%0d errors%0d",MUT,errors);
   $display("SAFE_RESET_GROUP_PASS MUT%0d channels16 captures2 checks%0d",MUT,checks);$finish;
  end
 end
 always@(posedge ck)begin
  #0.001;
  if(n>=8)begin
   checks=checks+16;
   if(observed!==pattern(n-1))begin errors=errors+1;if(errors<5)$display("RESET_GROUP_MISMATCH n%0d got%h expected%h",n,observed,pattern(n-1));end
  end
 end
endmodule
`endif
