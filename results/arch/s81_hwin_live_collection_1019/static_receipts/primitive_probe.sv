module primitive_probe;
 reg [135:0] a=0,d=0;reg[43:0] b=0,e=0;reg[1:0] c=0,f=0;integer i,j,n=0;
 task check(input bit want);
 begin
  #1;
  if(($isunknown(a)||$isunknown(b)||$isunknown(c)||$isunknown(d)||$isunknown(e)||$isunknown(f))!==want)
   $fatal(1,"PRIMITIVE_PROBE incorrectpervector unknown result");
  n=n+1;
 end endtask
 initial begin
  check(0);
  $display("PRIMITIVE_PROBE knownconcat%b pervector%b%b%b%b%b%b",$isunknown({a,b,c,d,e,f}),$isunknown(a),$isunknown(b),$isunknown(c),$isunknown(d),$isunknown(e),$isunknown(f));
  for(j=0;j<2;j=j+1)for(i=0;i<6;i=i+1)begin
   a=0;b=0;c=0;d=0;e=0;f=0;
   case(i)
    0:a[0]=j?1'bz:1'bx;1:b[0]=j?1'bz:1'bx;2:c[0]=j?1'bz:1'bx;
    3:d[0]=j?1'bz:1'bx;4:e[0]=j?1'bz:1'bx;5:f[0]=j?1'bz:1'bx;
   endcase
   check(1);
  end
  $display("PRIMITIVE_PROBE PASS cases%0d",n);$finish;
 end
endmodule
