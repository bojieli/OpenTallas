`timescale 1ns/1ps
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
