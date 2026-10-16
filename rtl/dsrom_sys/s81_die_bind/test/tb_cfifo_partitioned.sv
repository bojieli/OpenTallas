`timescale 1ns/1ps
module tb_cfifo_partitioned;
 parameter integer PHA=2,PHB=2;
 reg cr=0,xf=0,xf2=0,rst=0,go=0;
 initial forever #5 cr=~cr;
 initial begin #(PHA);forever #5 xf=~xf;end
 initial begin #(PHB);forever #5 xf2=~xf2;end
 reg [565:0] xd=0;reg[537:0]xd2=0;reg[65:0]ri=0;reg[1:0]st=0;
 wire[1170:0]a,b;
 dsfd_cfifo reference(.cr(cr),.xf(xf),.xf2(xf2),.rst(rst),.xd(xd),.xd2(xd2),.ri(ri),.st(st),
  .xa(a[282:0]),.xb(a[548:283]),.cc(a[563:549]),.x2(a[1099:564]),.rd(a[1169:1100]),.rs(a[1170]));
 dsfd_cfifo_partitioned dut(.xf_lane0({5{xf}}),.xf_lane1({5{xf2}}),.cr_ingress({10{cr}}),.cr_format({9{cr}}),.cr_return(cr),
  .rst(rst),.xd(xd),.xd2(xd2),.ri(ri),.st(st),
  .xa(b[282:0]),.xb(b[548:283]),.cc(b[563:549]),.x2(b[1099:564]),.rd(b[1169:1100]),.rs(b[1170]));
 function automatic [1100:0]word(input integer s);
 integer k;begin for(k=0;k<1101;k=k+1)word[k]=((s*1103515245+12345+k*2654435761)>>(k%29))^(s>>(k%5));word[0]=(s%3)!=0;end endfunction
 integer n=0,m=0,checks=0,bad=0;reg[1100:0]w,ww;
 always @(posedge xf)begin #1;if(go)begin w=word(n);xd={w[564:0],1'b1};n=n+1;end end
 always @(posedge xf2)begin #1;if(go)begin ww=word(m);if(m>=60&&m<80)ww[0]=!ww[0];xd2={ww[1100:565],ww[0],1'b1};m=m+1;end end
 always @(posedge cr)begin #1;ri={$random,$random,$random};st=$random;#1;
  if(go&&n>20)begin checks=checks+1;if(a!==b)begin if(bad<4)$display("CFIFO_SPLIT MISMATCH cycle%0d a%h b%h",n,a,b);bad=bad+1;end end
 end
 initial begin #23;rst=1;repeat(9)@(posedge cr);#4;go=1;repeat(400)@(posedge cr);#3;
 if(bad==0&&checks>350)$display("CFIFO_SPLIT PASS checks=%0d pha=%0d phb=%0d lane_valid_fault_injected=20",checks,PHA,PHB);
 else begin $display("CFIFO_SPLIT FAIL checks=%0d bad=%0d",checks,bad);$fatal;end
 $finish;end
endmodule
