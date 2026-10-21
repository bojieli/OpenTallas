`timescale 1ns/1ps
module tb_head_producer;
reg ck=0;always #0.5 ck=~ck;
reg rst_n=0;integer cyc=-1,poison=0,stopat=7000,expect_count=0,got=0,bad=0;
reg [1103:0] events[0:9999];reg [1103:0] ri=0;reg [1:0] hv=0;reg[1105:0] hd=0;
wire [1103:0] ro;wire cf;
reg [511:0] expected[0:9999];integer input_edge[0:9999];integer i,latency=-1;
string vectors;
ot_s81hd_ctl dut(.ck(ck),.rst_n(rst_n),.ri(ri),.mu_rt(32'd0),.lw(11'd0),.lep_f(1'b0),.ro(ro),.mu_c(),.mu_rc(),.ctl_f(cf),
 .sn_o(),.ss_o(),.sn_i(565'd0),.ss_i(565'd0),.mtx_v(),.mtx_d(),.mrx_v(6'd0),.mrx_d(3318'd0),.mflt(24'd0),
 .htx_v(),.htx_d(),.hrx_v(hv),.hrx_d(hd),.hflt(8'd0),.dtx_v(),.dtx_d(),.drx_v(5'd0),.drx_d(2765'd0),.dflt(20'd0));
initial begin
 if(!$value$plusargs("VECTORS=%s",vectors))$fatal(1,"VECTORS required");
 if(!$value$plusargs("POISON=%d",poison))poison=0;
 for(i=0;i<10000;i++)events[i]=0;
 $readmemh({vectors,"/events.memh"},events);
 for(i=0;i<10000;i++)if(events[i][0])begin expected[expect_count]=events[i][532:21];input_edge[expect_count]=i;expect_count++;end
 if(expect_count!=835)$fatal(1,"genuine835 records required");
end
always @(negedge ck)begin
 cyc=cyc+1;rst_n=cyc>=5;ri=0;if(poison!=0)ri[1103:533]='1;
 hv=0;hd=0;
 if(events[cyc][0])begin hv[0]=1;hd[552:0]={1'b1,24'd0,events[cyc][532:21],8'd0,2'd0,2'd0,4'd7};end
end
always @(posedge ck)begin
 #0.01;
 if(ro[0])begin
  if(got>=expect_count)$fatal(1,"unexpected output");
  if(latency<0)begin latency=cyc-input_edge[got];$display("ACTUAL_HFWD_LATENCY %0d",latency);end
  if(ro[532:21]!==expected[got]||ro[20:0]!==21'h1d||cyc-input_edge[got]!=latency)begin bad++;if(bad<4)$display("BAD HFWD lower/order/age index%0d age%0d lower%h",got,cyc-input_edge[got],ro[20:0]);end
  if(ro[1103:533]!==571'd0)begin bad++;if(bad<4)$display("BAD HFWD reserved-upper index%0d bits%h",got,ro[1103:533]);end
  got++;
 end
 if(cyc==stopat)begin
  if(got!=835||cf)begin bad++;$display("BAD count/fault got%0d ctl_f%0b",got,cf);end
  if(bad)$fatal(1,"FAIL ACTUAL_HEAD_HFWD poison%0d bad%0d got%0d latency%0d",poison,bad,got,latency);
  $display("PASS ACTUAL_HEAD_HFWD poison%0d got%0d latency%0d c_run0 real-seq-reset",poison,got,latency);$finish;
 end
end
endmodule
