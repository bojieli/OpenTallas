`timescale 1ns/1ps
module tb;
reg ck=0;always #0.4165 ck=~ck;reg rst=0;reg[3:0]sid=0;reg[1501:0]raw[0:8191],gold[0:8191],dr=0,dg=0;
wire[452:0]ph[0:3];wire[3:0]pf;integer which=0;wire[452:0]selected=ph[which];
localparam[191:0]T={16'd2,16'd55,16'd106,16'd160,16'd211,16'd264,16'd315,16'd367,16'd419,16'd471,16'd524,16'd576};
for(genvar m=0;m<4;m++)begin:g_mut
 qfd_dv_ar_go_phase #(.ENABLE(1),.MUT(m),.HGD_TABLE(T)) p(ck,rst,sid,dr[452:0],ph[m],pf[m]);
end
wire[515:0]an,as_,bn,bs;wire af,bf;
coupon a(ck,rst,sid,2'd0,selected,dr[453],dr[477:454],dr[1501:478],an,as_,af);
coupon b(ck,rst,sid,2'd0,dg[452:0],dg[453],dg[477:454],dg[1501:478],bn,bs,bf);
integer cy,N=2200,SID=0,na=0,nb=0,go=0,mismatch=0,badgold=0,negative=0,per=24;reg[15:0]expected;string rfile,gfile;
initial begin
 if($value$plusargs("sid=%d",SID))begin end
 if($value$plusargs("mut=%d",which))begin end
 if($value$plusargs("ncy=%d",N))begin end
 if($value$plusargs("negative=%d",negative))begin end
 if($value$plusargs("per=%d",per))begin end
 if(!$value$plusargs("raw=%s",rfile)||!$value$plusargs("gold=%s",gfile))$fatal(1,"FILES");
 $readmemh(rfile,raw);$readmemh(gfile,gold);sid=SID;
 repeat(12)@(negedge ck);rst=1;
 for(cy=0;cy<N;cy++)begin
  @(negedge ck);dr=raw[cy];dg=gold[cy];
  @(posedge ck);
  if(selected[452])begin go++;$display("CACHE_GO edge%0d IB%095h",cy,selected[451:73]);end
  if(an[0]||bn[0]||an[515]||bn[515]||as_[515]||bs[515])begin
   if(an!==bn||as_!==bs)mismatch++;
  end
  if(bn[515])begin
   expected=(nb<per)?16'h4000:16'h4080;
   if(bn[507:380]!=={8{expected}}||bs[507:380]!=={8{expected}})begin badgold++;if(badgold<3)$display("DATA edge%0d idx%0d N%032h S%032h",cy,nb,bn[507:380],bs[507:380]);end
   nb++;
  end
  if(an[515])na++;
 end
 if(bf||badgold||nb!=2*per)$fatal(1,"REFERENCE_BAD fault%b data%0d words%0d",bf,badgold,nb);
 if(!negative&&(af||pf[which]||mismatch||na!=2*per||go!=2))$fatal(1,"EPOCH_BAD fault%b cache%b mismatch%0d count%0d go%0d",af,pf[which],mismatch,na,go);
 if(negative&&!af&&!pf[which]&&mismatch==0)$fatal(1,"MUTANT_NOT_CAUGHT");
 $display("AR_PHASE_EPOCH_PASS sid%0d mut%0d go%0d Xwords%0d reference%0d mismatch%0d fault%b cache%b negative%0d genuine2vectors",SID,which,go,na,nb,mismatch,af,pf[which],negative);$finish;
end
endmodule
