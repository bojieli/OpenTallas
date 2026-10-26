`timescale 1ns/1ps
module tb;
reg cr=0,cr_s=0,rst=1;reg[3:0]xk=0;
reg[275:0]x0=276'h35a729,x1=276'hfeed13,x2i=276'h158ae8,x3=276'hacdd27;
reg[65:0]ri=0;reg[1:0]st=0;
wire[11:0]lk={3'd5,3'd4,3'd3,3'd2};
wire[14:0]ca,cb;wire[69:0]rda,rdb;wire rsa,rsb;
wire[282:0]xaa,xab;wire[265:0]xba,xbb;wire[535:0]x2a,x2b;
dsfd_cfifo_crs4 gold(ca,cr,cr_s,rda,ri,rsa,rst,st,xaa,xba,x2a,x0,x1,x2i,x3,xk,lk);
dsfd_cfifo_crs4_pin_capture cand(cb,cr,cr_s,rdb,ri,rsb,rst,st,xab,xbb,x2b,x0,x1,x2i,x3,xk,lk);
always #50 cr=~cr;
initial begin #25;forever #50 cr_s=~cr_s;end
initial begin #300;forever begin xk[0]=1;#50;xk[0]=0;#50;end end
initial begin #323;forever begin xk[1]=1;#50;xk[1]=0;#50;end end
initial begin #357;forever begin xk[2]=1;#50;xk[2]=0;#50;end end
initial begin #399;forever begin xk[3]=1;#50;xk[3]=0;#50;end end
always @(negedge xk[0]) begin x0<={x0[274:0],x0[275]^x0[268]}; x0[0]<=1; x0[1]<=0;end
always @(negedge xk[1]) x1<={x1[274:0],x1[275]^x1[268]};
always @(negedge xk[2]) begin x2i<={x2i[274:0],x2i[275]^x2i[268]};x2i[14]<=1;x2i[15]<=0;end
always @(negedge xk[3]) x3<={x3[274:0],x3[275]^x3[268]};
always @(negedge cr) begin ri<={ri[64:0],~ri[65]};st<=st+1'b1;end
reg[1099:0]delayed;
always @(posedge cr) delayed<={ca,xaa,xba,x2a};
integer n;
initial begin
 #10;rst=0;#290;rst=1;
 for(n=0;n<384;n=n+1) begin @(negedge cr);
   if(n>16) begin
     if({cb,xab,xbb,x2b}!==delayed) $fatal(1,"payload differs %0d",n);
     if(^delayed===1'bx) $fatal(1,"unknown payload %0d",n);
     if(rsa!==rsb || rda!==rdb) $fatal(1,"private status copy differs %0d",n);
   end
 end
 $display("FULL_CFIFO_CAPTURE_PASS384");$finish;
end
endmodule
