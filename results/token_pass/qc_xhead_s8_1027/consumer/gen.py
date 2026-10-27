from pathlib import Path
import sys
R,O=map(Path,sys.argv[1:]);O.mkdir(parents=True,exist_ok=True)
s=(R/'rtl/qwen_dv/s5/s8/qfd_dv_s8_flat.sv').read_text();body=s[s.index('    qfd_dv_s8_tap_bounded u_tap'):s.rindex('endmodule')]
header='''`timescale 1ns/1ps
// Exact x-delivery component carved from the current bound S8 flat parent.
module xh_consumer(input ck,rst_n,input[3:0]sid,input[452:0]hr_q,input xt_v,input[23:0]xt_a,input[1023:0]xt_d,
output[515:0]cw_n0,cw_n1,cw_n2,cw_n3,cw_s0,cw_s1,cw_s2,cw_s3,output fault);
wire xt_bad=0;wire[1566:0]hw;wire[23:0]cid;wire tap_fault,fch0,fch1,fch2,fch3;
wire[7:0]lqb0,lqb1,lqb2,lqb3;wire[515:0]cs0,cs1,cs2,cs3;
assign fault=fch0|fch1|fch2|fch3;
qfd_dv_s5_fs u_fs(.ck(ck),.cs0(cs0),.cs1(cs1),.cs2(cs2),.cs3(cs3),.cw_s0(cw_s0),.cw_s1(cw_s1),.cw_s2(cw_s2),.cw_s3(cw_s3));
'''
(O/'consumer.sv').write_text(header+body+'\nendmodule\n')
(O/'tb.sv').write_text('''`timescale 1ns/1ps
module tb(input ck);
reg rst_n=0;reg[3:0]sid=0;reg[452:0]hr_i=0;reg[452:0]hr_q=0;reg xt_v=0;reg[23:0]xt_a=0;reg[1023:0]xt_d=0;
wire[515:0]n0,n1,n2,n3,s0,s1,s2,s3;wire fault;
xh_consumer u(.ck(ck),.rst_n(rst_n),.sid(sid),.hr_q(hr_q),.xt_v(xt_v),.xt_a(xt_a),.xt_d(xt_d),
.cw_n0(n0),.cw_n1(n1),.cw_n2(n2),.cw_n3(n3),.cw_s0(s0),.cw_s1(s1),.cw_s2(s2),.cw_s3(s3),.fault(fault));
always@(posedge ck)hr_q<=hr_i;
wire[7:0]go={n3[0],n2[0],n1[0],n0[0],s3[0],s2[0],s1[0],s0[0]};
wire[7:0]xl={n3[515]|n3[511],n2[515]|n2[511],n1[515]|n1[511],n0[515]|n0[511],s3[515]|s3[511],s2[515]|s2[511],s1[515]|s1[511],s0[515]|s0[511]};
integer fd,lg,r,cyc=0,pre=0,ec,ep,NCYC=4000,i;reg[1047:0]ev;reg have=0;reg hf_seen=0;string EV,LOG;
initial begin
if(!$value$plusargs("EV=%s",EV)||!$value$plusargs("LOG=%s",LOG))$fatal(1,"missing paths");
r=$value$plusargs("NCYC=%d",NCYC);r=$value$plusargs("SID=%d",sid);
fd=$fopen(EV,"r");lg=$fopen(LOG,"w");r=$fscanf(fd,"%d %d %h\\n",ec,ep,ev);have=(r==3);
end
always@(negedge ck)begin
if(pre<4)begin pre=pre+1;if(pre==4)rst_n=1;end
else begin
if(|go)$fdisplay(lg,"%0d S0CW %h",cyc,go);
if(|xl)$fdisplay(lg,"%0d S0XL %h",cyc,xl);
if(fault&&!hf_seen)$fdisplay(lg,"%0d S0HF 1",cyc);hf_seen=fault;
xt_v=0;xt_a=0;xt_d=0;hr_i=0;
while(have&&ec==cyc)begin
if(ep==1)begin xt_v=1;xt_a=ev[1047:1024];xt_d=ev[1023:0];end
if(ep==2)hr_i=ev[452:0];
r=$fscanf(fd,"%d %d %h\\n",ec,ep,ev);have=(r==3);
end
if(have&&ec<cyc)$fatal(1,"unsorted event %0d vs%0d",ec,cyc);
cyc=cyc+1;if(cyc>=NCYC)begin $fclose(lg);$finish;end
end
end
endmodule
''')
