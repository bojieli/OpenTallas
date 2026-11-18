// HEAD-TYPES-O: u_mux with internal cs decode (CS_COPIES=0) vs parent-registered cs copies (CS_COPIES=9), random 200k cycles
`timescale 1ns/1ps
module tb_cs;
 reg ck=0,rst_n=0;always #1 ck=~ck;
 reg rv;reg[552:0]rd;reg cvld,h0v,cv;reg[552:0]h0,cd;reg[1103:0]lr;reg[16:0]sf;
 reg l1v;reg[552:0]l1d;reg[8:0]csq;
 always@(posedge ck or negedge rst_n)if(!rst_n)begin l1v<=0;csq<=0;end else begin l1v<=rv;csq<={9{rv&&rd[552]&&rd[3:0]==4'd6}};end
 always@(posedge ck)l1d<=rd;
 wire[1103:0]fpA,fpB;wire xvA,xvB;wire[552:0]xdA,xdB;wire[1:0]tvA,tvB;wire[1105:0]tdA,tdB;wire[16:0]fA,fB;
 ot_s81hd_host_frame_mux #(.MUT(0),.CS_COPIES(0))a(.ck(ck),.rst_n(rst_n),.context_valid(cvld),.host1_cs_q(1'b0),
  .host0_v(h0v),.host1_v(l1v),.host0_d(h0),.host1_d(l1d),.local_ring(lr),.source_fault(sf),.ctl_v(cv),.ctl_d(cd),
  .from_prev(fpA),.ctl_rx_v(xvA),.ctl_rx_d(xdA),.lane_tx_v(tvA),.lane_tx_d(tdA),.fault(fA));
 ot_s81hd_host_frame_mux #(.MUT(0),.CS_COPIES(9))b(.ck(ck),.rst_n(rst_n),.context_valid(cvld),.host1_cs_q(csq),
  .host0_v(h0v),.host1_v(l1v),.host0_d(h0),.host1_d(l1d),.local_ring(lr),.source_fault(sf),.ctl_v(cv),.ctl_d(cd),
  .from_prev(fpB),.ctl_rx_v(xvB),.ctl_rx_d(xdB),.lane_tx_v(tvB),.lane_tx_d(tdB),.fault(fB));
 integer i,err=0,cfgs=0;
 initial begin
  rv=0;rd=0;cvld=0;h0v=0;cv=0;h0=0;cd=0;lr=0;sf=0; #5 rst_n=1;
  for(i=0;i<200000;i=i+1)begin
   @(negedge ck);
   rv=$random;rd={$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random};
   if(($random&3)==0)rd[3:0]=4'd6; if(($random&1))rd[552]=1;
   cvld=($random&3)!=0;h0v=$random;h0[552]=$random;h0[3:0]=$random;cv=$random;cd[552]=$random;cd[3:0]=$random&15;
   lr[0]=$random;lr[3:1]=$random;lr[532:21]={$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random};
   sf=(($random&255)==0)?$random:0;
   if(i==100000)begin rst_n=0;#0.1 rst_n=1;end
   #0.5;
   if(fpA!==fpB||xvA!==xvB||(xvA&&xdA!==xdB)||tvA!==tvB||tdA!==tdB||fA!==fB)begin err=err+1;if(err<5)$display("MISMATCH %0d",i);end
   if(xvA&&l1v&&csq[0])cfgs=cfgs+1;
  end
  $display("CS_EQ cycles %0d cfg_frames %0d errors %0d %s",i,cfgs,err,err==0?"PASS":"FAIL");$finish;
 end
endmodule
