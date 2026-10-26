`timescale 1ps/1fs
// Direct public-port equivalence at the unchanged fixed LK=2. Reset remains
// legacy asynchronous; this component proof gives no synchronous-reset/timing approval.
module tb_cfifo_lk_profile;
localparam realtime T=833.0;
reg clk=0,rst=0;reg[3:0]xk=0;
reg[65:0]ri=0;reg[1:0]st=0;reg[1103:0]xl=0;
wire[14:0]cc[0:2];wire[69:0]rd[0:2];wire[2:0]rs;
wire[282:0]xa[0:2];wire[265:0]xb[0:2];wire[535:0]x2[0:2];
wire[1170:0]old_public={cc[0],rd[0],rs[0],xa[0],xb[0],x2[0]};
wire[1170:0]new_public={cc[1],rd[1],rs[1],xa[1],xb[1],x2[1]};
wire[1170:0]mut_public={cc[2],rd[2],rs[2],xa[2],xb[2],x2[2]};
integer checks=0,known=0,activity=0,mutants=0,edges=0,k;
reg[1170:0]prev=0;
always #(T/2.0)clk=~clk;
always @(clk)begin xk[0]<=#0 clk;xk[1]<=#25 clk;xk[2]<=#55 clk;xk[3]<=#80 clk;end
always @(negedge clk)begin
 for(k=0;k<1104;k=k+1)xl[k]=$random;
 for(k=0;k<66;k=k+1)ri[k]=$random;
 st=$random; xl[0]=rst;xl[566]=rst;
end
dsfd_cfifo_crs4 u_old(.cc(cc[0]),.cr(clk),.cr_s(clk),.rd(rd[0]),.ri(ri),.rs(rs[0]),.rst(rst),.st(st),
 .xa(xa[0]),.xb(xb[0]),.x2(x2[0]),.xl0(xl[275:0]),.xl1(xl[551:276]),.xl2(xl[827:552]),.xl3(xl[1103:828]),.xk(xk),.lk({4{3'd2}}));
dsfd_cfifo_crs4p #(.LK({4{3'd2}})) u_new(.cc(cc[1]),.cr(clk),.cr_s(clk),.rd(rd[1]),.ri(ri),.rs(rs[1]),.rst(rst),.st(st),
 .xa(xa[1]),.xb(xb[1]),.x2(x2[1]),.xl0(xl[275:0]),.xl1(xl[551:276]),.xl2(xl[827:552]),.xl3(xl[1103:828]),.xk(xk));
dsfd_cfifo_crs4p #(.LK({3'd2,3'd2,3'd2,3'd1})) u_mut(.cc(cc[2]),.cr(clk),.cr_s(clk),.rd(rd[2]),.ri(ri),.rs(rs[2]),.rst(rst),.st(st),
 .xa(xa[2]),.xb(xb[2]),.x2(x2[2]),.xl0(xl[275:0]),.xl1(xl[551:276]),.xl2(xl[827:552]),.xl3(xl[1103:828]),.xk(xk));
task compare;begin
 #0.001;
 checks=checks+1;
 if(old_public!==new_public)begin $display("CFIFO_MISMATCH time%0t old%h new%h",$time,old_public,new_public);$fatal;end
 if((^old_public)!==1'bx)begin
 known=known+1;if(old_public!==prev)activity=activity+1;
 if(mut_public!==old_public)mutants=mutants+1;
 prev=old_public;
 end
end endtask
always @(posedge clk)begin edges=edges+1;compare();end
always @(rst)compare();
initial begin
 #(T*3+53)rst=1;
 #(T*400+31)rst=0;
 #(T*5+19)rst=1;
 #(T*600+43)rst=0;
 #(T*4+11)rst=1;
end
initial begin
 repeat(1800)@(negedge clk);
 if(checks<1800||known<1500||activity<1400||mutants<1000)$fatal(1,"CFIFO_VACUOUS checks%0d known%0d activity%0d mutants%0d",checks,known,activity,mutants);
 $display("CFIFO_STATIC_LK_PASS checks%0d known%0d activity%0d mutant_hits%0d cycles%0d",checks,known,activity,mutants,edges);$finish;
end
endmodule
