from pathlib import Path
import re, hashlib,json
p=Path(__file__).parent
s=(p/'flat.sv').read_text(); col=s[s.index('    // ---- column 0:'):s.index('    // ---- column 1:')]
col=col.replace('.cid(cid[5:0])','.cid(cid[6*colsel+:6])').replace('.fault_i(fch1)', '.fault_i(1\'b0)')
wrap='''`timescale 1ns/1ps
module coupon(input wire ck,rst_n,input wire[3:0]sid,input wire[1:0]colsel,input wire[452:0]hr_q,input wire xt_v,input wire[23:0]xt_a,input wire[1023:0]xt_d,output wire[515:0]cw_n0,cs0,output wire fault);
wire[1566:0]hw;wire[23:0]cid;wire tap_fault,fch0;wire[7:0]lqb0;
qfd_dv_s8_tap_bounded u_tap(.ck(ck),.rst_n(rst_n),.sid(sid),.hr_q(hr_q),.xt_vcopies({6{xt_v}}),.xt_a(xt_a),.xt_d(xt_d),.xt_bad(1'b0),.lq_bad({24'd0,lqb0}),.hw(hw),.cid(cid),.tap_fault(tap_fault));
'''+col+'''assign fault=tap_fault|fch0;
endmodule
'''
(p/'coupon.sv').write_text(wrap)
(p/'tb.sv').write_text('''`timescale 1ns/1ps
module tb;
reg ck=0;always #5 ck=~ck;
reg rst_n=0;reg[3:0]sid=0;reg[1:0]colsel=0;
reg[1501:0]ev[0:16383];reg[1501:0]drive=0;
wire[452:0]hr=drive[452:0];wire xtv=drive[453];wire[23:0]xta=drive[477:454];wire[1023:0]xtd=drive[1501:478];
wire[515:0]nd,sd;wire fault;
coupon d(.ck(ck),.rst_n(rst_n),.sid(sid),.colsel(colsel),.hr_q(hr),.xt_v(xtv),.xt_a(xta),.xt_d(xtd),.cw_n0(nd),.cs0(sd),.fault(fault));
integer c=0,ncy=1024,sv=0,cv=0,n=0,s=0,firstn=-1,lastn=-1,firsts=-1,lasts=-1;string file;
initial begin
 if(!$value$plusargs("input=%s",file))$fatal(1,"no input");
 if($value$plusargs("ncy=%d",ncy))begin end
 if($value$plusargs("sid=%d",sv))begin end
 if($value$plusargs("col=%d",cv))begin end
 sid=sv;colsel=cv;for(integer i=0;i<16384;i++)ev[i]=0;$readmemh(file,ev);
 repeat(12)@(negedge ck);rst_n=1;
 for(c=0;c<ncy;c++)begin
 @(negedge ck);drive=ev[c];
 @(posedge ck);
 if(nd[515])begin n++;if(firstn<0)firstn=c;lastn=c;end
 if(sd[515])begin s++;if(firsts<0)firsts=c;lasts=c;end
 if(fault)$display("FAULT c=%0d tap=%b head=%b lqb=%h",c,d.tap_fault,d.fch0,d.lqb0);
 end
 $display("RESULT n=%0d s=%0d firstn=%0d lastn=%0d firsts=%0d lasts=%0d fault=%b",n,s,firstn,lastn,firsts,lasts,fault);$finish;
end
endmodule
''')
(p/'source_contract.json').write_text(json.dumps({'projection':'literal currentJ tap + one selectable replica of xhead3 + eight XS leaves; direct hr_q boundary after FDN; no MACs','files':{x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in p.glob('*.sv') if x.name not in ('coupon.sv','tb.sv')}},indent=2)+'\n')
