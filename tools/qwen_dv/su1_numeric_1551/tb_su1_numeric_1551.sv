`timescale 1ns/1ps
module tb_su1_numeric_1551;
reg clk=0;always #0.4165 clk=~clk;
reg rst_n=0;integer cycle=0,ep,step,kind=0,j,n,k,lag;
reg[17:0] i;reg[18:0] fin_th;reg[23:0] cura,curb,curc,curd,rrow,asi,bsi,csi,dsi;
reg asrc,bsrc,csrc,mc,md,redsq;reg[1:0]ma,mb,dst,red;reg[2:0]ad,cls=0,isfu;
reg[31:0]imm1,imm2;reg emit0,live,ilast,accept;
function automatic[31:0] fp(input[23:0]a,input integer portid);fp=32'h3f000000|((a*131+portid*197)&32'h007fffff);endfunction
function automatic[255:0] fw(input[23:0]a);integer t;begin for(t=0;t<16;t=t+1)fw[t*16+:16]=16'h3f00|((a+t)&127);end endfunction
// Independent global broadcast advances every source cycle; it is NEVER generated from DUT WROM requests.
wire[255:0] broadcast=fw(24'(cycle/16));
wire[499:0]gb={i,fin_th,rrow,asi,bsi,csi,dsi,asrc,bsrc,csrc,mc,md,redsq,ma,mb,dst,red,ad,cls,isfu,imm1,imm2,broadcast};
wire[2:0]gv={emit0,accept,ilast};wire[95:0]pd={cura,curb,curc,curd};
wire[247:0]co[0:4];wire[759:0]ci[0:4];
reg[31:0]va0[0:3],vb0[0:3],vc0[0:3];reg[63:0]cr0[0:3];
always @(posedge clk)begin
if(co[0][140])va0[0]<=fp(co[0][139:116],0);
if(co[0][165])vb0[0]<=fp(co[0][164:141],1);
if(co[0][190])vc0[0]<=fp(co[0][189:166],2);
if(co[0][24])cr0[0]<={fp(co[0][23:0],5),fp(co[0][23:0],6)};
for(integer t=1;t<4;t=t+1)begin va0[t]<=va0[t-1];vb0[t]<=vb0[t-1];vc0[t]<=vc0[t-1];cr0[t]<=cr0[t-1];end end
assign ci[0]={cr0[3][31:0],cr0[3][63:32],vc0[0],vb0[0],va0[0],pd,live,gv,gb};
codex_su1_transport #(.EXTRA(0),.WCOMP(0),.CDEPTH(0),.RDEPTH(0),.ODEPTH(0)) u0(.clk(clk),.rst_n(rst_n),.ci(ci[0]),.co(co[0]));
reg[31:0]va1[0:3],vb1[0:3],vc1[0:3];reg[63:0]cr1[0:3];
always @(posedge clk)begin
if(co[1][140])va1[0]<=fp(co[1][139:116],0);
if(co[1][165])vb1[0]<=fp(co[1][164:141],1);
if(co[1][190])vc1[0]<=fp(co[1][189:166],2);
if(co[1][24])cr1[0]<={fp(co[1][23:0],5),fp(co[1][23:0],6)};
for(integer t=1;t<4;t=t+1)begin va1[t]<=va1[t-1];vb1[t]<=vb1[t-1];vc1[t]<=vc1[t-1];cr1[t]<=cr1[t-1];end end
assign ci[1]={cr1[3][31:0],cr1[3][63:32],vc1[0],vb1[0],va1[0],pd,live,gv,gb};
codex_su1_transport #(.EXTRA(4),.WCOMP(4),.CDEPTH(2),.RDEPTH(2),.ODEPTH(3)) u1(.clk(clk),.rst_n(rst_n),.ci(ci[1]),.co(co[1]));
reg[31:0]va2[0:3],vb2[0:3],vc2[0:3];reg[63:0]cr2[0:3];
always @(posedge clk)begin
if(co[2][140])va2[0]<=fp(co[2][139:116],0);
if(co[2][165])vb2[0]<=fp(co[2][164:141],1);
if(co[2][190])vc2[0]<=fp(co[2][189:166],2);
if(co[2][24])cr2[0]<={fp(co[2][23:0],5),fp(co[2][23:0],6)};
for(integer t=1;t<4;t=t+1)begin va2[t]<=va2[t-1];vb2[t]<=vb2[t-1];vc2[t]<=vc2[t-1];cr2[t]<=cr2[t-1];end end
assign ci[2]={cr2[3][31:0],cr2[3][63:32],vc2[0],vb2[0],va2[0],pd,live,gv,gb};
codex_su1_transport #(.EXTRA(4),.WCOMP(0),.CDEPTH(2),.RDEPTH(2),.ODEPTH(3)) u2(.clk(clk),.rst_n(rst_n),.ci(ci[2]),.co(co[2]));
reg[31:0]va3[0:3],vb3[0:3],vc3[0:3];reg[63:0]cr3[0:3];
always @(posedge clk)begin
if(co[3][140])va3[0]<=fp(co[3][139:116],0);
if(co[3][165])vb3[0]<=fp(co[3][164:141],1);
if(co[3][190])vc3[0]<=fp(co[3][189:166],2);
if(co[3][24])cr3[0]<={fp(co[3][23:0],5),fp(co[3][23:0],6)};
for(integer t=1;t<4;t=t+1)begin va3[t]<=va3[t-1];vb3[t]<=vb3[t-1];vc3[t]<=vc3[t-1];cr3[t]<=cr3[t-1];end end
assign ci[3]={cr3[3][31:0],cr3[3][63:32],vc3[0],vb3[0],va3[0],pd,live,gv,gb};
codex_su1_transport #(.EXTRA(4),.WCOMP(2),.CDEPTH(2),.RDEPTH(2),.ODEPTH(3)) u3(.clk(clk),.rst_n(rst_n),.ci(ci[3]),.co(co[3]));
reg[31:0]va4[0:3],vb4[0:3],vc4[0:3];reg[63:0]cr4[0:3];
always @(posedge clk)begin
if(co[4][140])va4[0]<=fp(co[4][139:116],0);
if(co[4][165])vb4[0]<=fp(co[4][164:141],1);
if(co[4][190])vc4[0]<=fp(co[4][189:166],2);
if(co[4][24])cr4[0]<={fp(co[4][23:0],5),fp(co[4][23:0],6)};
for(integer t=1;t<4;t=t+1)begin va4[t]<=va4[t-1];vb4[t]<=vb4[t-1];vc4[t]<=vc4[t-1];cr4[t]<=cr4[t-1];end end
assign ci[4]={cr4[3][31:0],cr4[3][63:32],vc4[0],vb4[0],va4[0],pd,live,gv,gb};
codex_su1_transport #(.EXTRA(0),.WCOMP(4),.CDEPTH(2),.RDEPTH(2),.ODEPTH(3)) u4(.clk(clk),.rst_n(rst_n),.ci(ci[4]),.co(co[4]));
reg[247:0]hist[0:19];integer reqerr[1:4],dataerr[1:4],faultphase[1:4][0:16],counts[0:7],clcounts[0:4];integer warmleak=0;
initial begin for(integer x=0;x<8;x=x+1)counts[x]=0;for(integer x=0;x<5;x=x+1)clcounts[x]=0;for(integer x=1;x<5;x=x+1)begin reqerr[x]=0;dataerr[x]=0;for(integer z=0;z<17;z=z+1)faultphase[x][z]=0;end end
always @(posedge clk)begin hist[0]<=co[0];for(integer t=1;t<20;t=t+1)hist[t]<=hist[t-1];end
always @(negedge clk)begin
cycle=cycle+1;rst_n=(cycle>64)&&!(cycle>=3500&&cycle<3564);
ep=(cycle-128)/640;step=(cycle-128)%640;live=(cycle>=128&&ep<10&&step>=192&&step<224);emit0=live;i=live?(step-192):0;ilast=live&&(i==31);fin_th=32;
cura=cycle;curb=64+cycle*3;curc=128+cycle*5;curd=4096+cycle;rrow=32+cycle;asi=1;bsi=1;csi=1;dsi=1;asrc=(cycle/768)%2;bsrc=(cycle/256)%2;csrc=!bsrc;mc=(((cycle/1024)%2)==0&&((cycle/512)%2)==0)?0:1;md=(((cycle/1024)%2)==0&&((cycle/512)%2)==0)?0:(cycle/512)%2;red=0;dst=(cycle/256)%3;ad=((cycle/512)%2)?2:0;ma=(cycle/1024)%2;mb=0;
case(ep)0,5:kind=0;1,9:kind=1;2,8:kind=2;3,7:kind=3;default:kind=4;endcase
accept=(cycle>=128&&step==0);if(cycle>=128&&step>=1)cls=kind;isfu=kind;redsq=0;imm1=32'h3f800000;imm2=0;
if(!rst_n&&cycle>3508)for(n=0;n<5;n=n+1)if(co[n][247]||co[n][115]||co[n][81])warmleak=warmleak+1;
if(cycle>256&&rst_n&&!(cycle>=3500&&cycle<3700))begin
if(co[0][24])counts[0]=counts[0]+1;if(co[0][140])counts[1]=counts[1]+1;if(co[0][165])counts[2]=counts[2]+1;if(co[0][190])counts[3]=counts[3]+1;
if(co[0][247])counts[4]=counts[4]+1;if(co[0][81])counts[5]=counts[5]+1;if(co[0][115])begin counts[6]=counts[6]+1;clcounts[cls]=clcounts[cls]+1;end if(co[0][82])counts[7]=counts[7]+1;
for(n=1;n<5;n=n+1)begin
if(co[n][24]!==hist[3][24]||(co[n][24]&&co[n][23:0]!==hist[3][23:0]))reqerr[n]=reqerr[n]+1;
if(co[n][140]!==hist[3][140]||(co[n][140]&&co[n][139:116]!==hist[3][139:116]))reqerr[n]=reqerr[n]+1;
if(co[n][165]!==hist[3][165]||(co[n][165]&&co[n][164:141]!==hist[3][164:141]))reqerr[n]=reqerr[n]+1;
if(co[n][190]!==hist[3][190]||(co[n][190]&&co[n][189:166]!==hist[3][189:166]))reqerr[n]=reqerr[n]+1;
if(co[n][247]!==hist[8][247]||(co[n][247]&&co[n][246:191]!==hist[8][246:191]))dataerr[n]=dataerr[n]+1;
if(co[n][81]!==hist[8][81]||(co[n][81]&&co[n][80:25]!==hist[8][80:25]))dataerr[n]=dataerr[n]+1;
if(co[n][115]!==hist[8][115]||(co[n][115]&&co[n][114:83]!==hist[8][114:83]))dataerr[n]=dataerr[n]+1;
for(lag=0;lag<17;lag=lag+1)if(co[n][82] !== (lag==0?co[0][82]:hist[lag-1][82]))faultphase[n][lag]=faultphase[n][lag]+1;
end end
if(cycle==6700)begin
for(n=0;n<8;n=n+1)$display("COUNT %0d %0d",n,counts[n]);for(n=0;n<5;n=n+1)$display("CLASS %0d %0d",n,clcounts[n]);
for(n=1;n<5;n=n+1)begin $display("CANDIDATE %0d req_errors=%0d data_errors=%0d",n,reqerr[n],dataerr[n]);for(lag=0;lag<17;lag=lag+1)$display("FAULT %0d lag=%0d errors=%0d",n,lag,faultphase[n][lag]);end
$display("WARM_LEAK %0d",warmleak);$finish;end
end
endmodule
