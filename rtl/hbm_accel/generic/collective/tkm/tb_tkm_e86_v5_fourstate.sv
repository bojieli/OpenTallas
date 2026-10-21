`timescale 1ns/1ps
module cmp_probe #(parameter W=85)(output reg done);
 reg [W-1:0] a,b;wire old_lt,new_lt;integer n,i,s;
 ot_tkm_lt_live #(.W(W)) old_u(a,b,old_lt);
 ot_tkm_lt_chunked #(.W(W),.G(5)) new_u(a,b,new_lt);
 function automatic logic digit(input integer x);case(x%4)0:digit=0;1:digit=1;2:digit=1'bx;3:digit=1'bz;endcase endfunction
 task check;begin #1;if(old_lt!==new_lt)$fatal(1,"CMP W%0d a%b b%b old%b new%b",W,a,b,old_lt,new_lt);end endtask
 initial begin done=0;a=0;b=0;check();a='1;b=0;check();
 // Exhaustive individual four-state pairs at every bit, with higher decisive bits and unknown lower bits.
 for(i=0;i<W;i=i+1)for(s=0;s<16;s=s+1)begin
 a=0;b=0;a[i]=digit(s/4);b[i]=digit(s);check();
 a='x;b='z;a[i]=digit(s/4);b[i]=digit(s);check();
 if(i+1<W)begin a[i+1]=0;b[i+1]=1;check();a[i+1]=1;b[i+1]=0;check();end
 end
 for(n=0;n<4096;n=n+1)begin for(i=0;i<W;i=i+1)begin a[i]=digit($urandom_range(0,3));b[i]=digit($urandom_range(0,3));end check();end
 done=1;end
endmodule
module tb_tkm_e86_v5_fourstate;
 wire d1,d6,d85;cmp_probe #(1) p1(d1);cmp_probe #(6)p6(d6);cmp_probe #(85)p85(d85);
 reg [19:0] cg,g2;reg [4:0] cv;reg [15:0] gb;reg c;reg [3:0] f;wire [3:0] oldgn,newgn,nextgn;integer i,n;reg gd;
 ot_tkm_gn_leaf #(.FOLD(0)) old_u(cg,cv,g2,gb,c,f,oldgn,);
 ot_tkm_gn_leaf #(.FOLD(1)) new_u(cg,cv,g2,gb,c,f,newgn,nextgn);
 function automatic logic digit(input integer x);case(x%4)0:digit=0;1:digit=1;2:digit=1'bx;3:digit=1'bz;endcase endfunction
 initial begin gd=0;for(n=0;n<4096;n=n+1)begin
 for(i=0;i<20;i=i+1)begin cg[i]=digit($urandom_range(0,3));g2[i]=digit($urandom_range(0,3));end
 for(i=0;i<16;i=i+1)gb[i]=digit($urandom_range(0,3));
 for(i=0;i<5;i=i+1)cv[i]=digit($urandom_range(0,3));
 for(i=0;i<4;i=i+1)f[i]=digit($urandom_range(0,3));c=digit(n);#1;
 if(oldgn!==newgn||nextgn!==(c?f:oldgn))$fatal(1,"GN fourstate mismatch");end gd=1;end
 initial begin wait(d1&&d6&&d85&&gd);$display("E86_V5_FOURSTATE PASS widths1,6,85 comparator and exact GN ternary");$finish;end
endmodule
