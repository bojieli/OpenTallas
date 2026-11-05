module tb_tiny; reg [3:0] a;reg [11:0] o;reg [7:0] f;reg [15:0] c;reg [7:0] b;reg [11:0] r,t;wire ok;
 tiny u(a,o,f,c,b,r,t,ok); longint n=0,hit=0,bad=0;
 initial begin
  repeat(20000000)begin
   a=$urandom;o=$urandom;f=($urandom%2)?8'hff:$urandom;c=$urandom;b=$urandom;
   r=($urandom%4==0)?12'd4092+12'($urandom%4):$urandom;
   t=12'(int'(r)+int'($urandom%5));
   #1; n++; if(ok!==1'b1)bad++;
  end
  $display("TINY n %0d bad %0d",n,bad); $finish;
 end
endmodule
