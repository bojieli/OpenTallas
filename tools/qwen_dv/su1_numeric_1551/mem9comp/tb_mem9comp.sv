`timescale 1ns/1fs
module tb_mem9comp;
reg clk=0;always #0.4165 clk=~clk;
reg rst_n=0;integer cycle=0,ep,step,kind=0,j,n,k,lag;
reg[17:0] i;reg[18:0] fin_th;reg[23:0] cura,curb,curc,curd,rrow,asi,bsi,csi,dsi;
reg asrc,bsrc,csrc,mc,md,redsq;reg[1:0]ma,mb,dst,red;reg[2:0]ad,cls=0,isfu;
reg[31:0]imm1,imm2;reg emit0,live,ilast,accept;
function automatic[31:0] fp(input[23:0]a,input integer portid);fp=(cls!=0&&portid<3&&a[3:0]==7)?32'h7fc00001:(32'h3f000000|((a*131+portid*197)&32'h007fffff));endfunction
function automatic[255:0] fw(input[23:0]a);integer t;begin for(t=0;t<16;t=t+1)fw[t*16+:16]=(cls!=0&&t==3)?16'h7fc1:(16'h3f00|((a+t)&127));end endfunction
// Independent global broadcast advances every source cycle; it is NEVER generated from DUT WROM requests.
wire[255:0] broadcast=fw(24'(cycle/16));
wire[499:0]gb={i,fin_th,rrow,asi,bsi,csi,dsi,asrc,bsrc,csrc,mc,md,redsq,ma,mb,dst,red,ad,cls,isfu,imm1,imm2,broadcast};
wire[2:0]gv={emit0,accept,ilast};wire[95:0]pd={cura,curb,curc,curd};
wire[247:0]co[0:8];wire[759:0]ci[0:8];
// Providers retain measured pin-to-pin VM6/CROM9; production adds request5/answer4.
for(genvar g=0;g<9;g=g+1)begin:g_vehicle
reg[31:0]va[0:8],vb[0:8],vc[0:8];reg[63:0]cr[0:8];
always @(posedge clk)begin
if(co[g][140])va[0]<=fp(co[g][139:116],0);
if(co[g][165])vb[0]<=fp(co[g][164:141],1);
if(co[g][190])vc[0]<=fp(co[g][189:166],2);
if(co[g][24])cr[0]<={fp(co[g][23:0],5),fp(co[g][23:0],6)};
for(integer t=1;t<9;t=t+1)begin va[t]<=va[t-1];vb[t]<=vb[t-1];vc[t]<=vc[t-1];cr[t]<=cr[t-1];end end
localparam integer K=(g==6)?8:(g==7)?10:9; localparam integer PRE=(g==8)?0:1;
wire prefix=(g>=5)&&(PRE!=0)&&(cycle>=128)&&(ep<10)&&(step>=192-K)&&(step<192);
wire [95:0] pd_x=(g>=5)?{24'(cycle+K),24'(64+(cycle+K)*3),24'(128+(cycle+K)*5),curd}:pd;
wire live_x=(g>=5)?(live|prefix):live;
wire [2:0] gv_x=(g>=5)?{emit0|prefix,accept,ilast}:gv;
wire [1:0] ma_x=prefix?2'd0:ma, mb_x=prefix?2'd0:mb, dst_x=prefix?2'd0:dst, red_x=prefix?2'd0:red;
wire [2:0] ad_x=prefix?3'd0:ad;
wire [499:0] gb_x=(g>=5)?{i,fin_th,rrow,asi,bsi,csi,dsi,asrc,bsrc,csrc,mc,md,redsq,ma_x,mb_x,dst_x,red_x,ad_x,cls,isfu,imm1,imm2,broadcast}:gb;
assign ci[g]={cr[8][31:0],cr[8][63:32],vc[5],vb[5],va[5],pd_x,live_x,gv_x,gb_x};
// 0 oracle; 1 compensated; 2 WROM mutant; 3 head mutant; 4 uncompensated parent.
codex_su1_transport #(.EXTRA(g==0||g>=4?0:g==3?4:9),.WCOMP(g==0||g>=4?0:g==2?4:9),.CDEPTH(g==0?0:4),.RDEPTH(g==0?0:5),.ODEPTH(g==0?0:5)) u(.clk(clk),.rst_n(rst_n),.ci(ci[g]),.co(co[g]));
end
reg[247:0]hist[0:47];integer reqerr[1:8],dataerr[1:8],faultphase[1:8][0:40],counts[0:7],clcounts[0:4];integer reqextra[5:8],ovextra[5:8],derr_a0[5:8],derr_a1[5:8],vwextra[5:8];integer derr_ep[5:8][0:9];reg noasrc,dbg;integer dbg_cnt=0,warmleak=0,golden_checks=0,golden_errors=0;integer tag;reg[31:0]gold;
initial begin noasrc=$test$plusargs("NOASRC");dbg=$test$plusargs("DBG");for(integer x=5;x<9;x=x+1)for(integer z=0;z<10;z=z+1)derr_ep[x][z]=0;for(integer x=0;x<8;x=x+1)counts[x]=0;for(integer x=0;x<5;x=x+1)clcounts[x]=0;for(integer x=1;x<9;x=x+1)begin reqerr[x]=0;dataerr[x]=0;for(integer z=0;z<41;z=z+1)faultphase[x][z]=0;end for(integer x=5;x<9;x=x+1)begin reqextra[x]=0;ovextra[x]=0;derr_a0[x]=0;derr_a1[x]=0;vwextra[x]=0;end end
always @(posedge clk)begin hist[0]<=co[0];for(integer t=1;t<48;t=t+1)hist[t]<=hist[t-1];end
always @(negedge clk)begin
cycle=cycle+1;rst_n=(cycle>64)&&!(cycle>=3500&&cycle<3564);
ep=(cycle-128)/640;step=(cycle-128)%640;live=(cycle>=128&&ep<10&&step>=192&&step<224);emit0=live;i=live?(step-192):0;ilast=live&&(i==31);fin_th=32;
cura=cycle;curb=64+cycle*3;curc=128+cycle*5;curd=4096+cycle;rrow=32+cycle;asi=1;bsi=1;csi=1;dsi=1;asrc=noasrc?1'b0:(cycle/768)%2;bsrc=(cycle/256)%2;csrc=!bsrc;mc=(((cycle/1024)%2)==0&&((cycle/512)%2)==0)?0:1;md=(((cycle/1024)%2)==0&&((cycle/512)%2)==0)?0:(cycle/512)%2;red=0;dst=(cycle/256)%3;ad=((cycle/512)%2)?2:0;ma=(cycle/1024)%2;mb=0;
case(ep)0,5:kind=0;1,9:kind=1;2,8:kind=2;3,7:kind=3;default:kind=4;endcase
accept=(cycle>=128&&step==0);if(cycle>=128&&step>=1)cls=kind;isfu=kind;if(cls==0)dst=1;redsq=0;imm1=32'h3f800000;imm2=0;
if(!rst_n&&cycle>3520)for(n=0;n<9;n=n+1)if(co[n][247]||co[n][115]||co[n][81])warmleak=warmleak+1;
if(cycle>256&&rst_n&&!(cycle>=3500&&cycle<3700))begin
if(co[0][24])counts[0]=counts[0]+1;if(co[0][140])counts[1]=counts[1]+1;if(co[0][165])counts[2]=counts[2]+1;if(co[0][190])counts[3]=counts[3]+1;
if(co[0][247])begin counts[4]=counts[4]+1;if(cls==0)begin tag=co[0][214:191]-4096;gold=fp(24'(tag),0);golden_checks=golden_checks+1;if(co[0][246:215]!==gold)begin golden_errors=golden_errors+1;if(golden_errors<5)$display("BASE_GOLD tag=%0d got=%h want=%h",tag,co[0][246:215],gold);end end end if(co[0][81])counts[5]=counts[5]+1;if(co[0][115])begin counts[6]=counts[6]+1;clcounts[cls]=clcounts[cls]+1;end if(co[0][82])counts[7]=counts[7]+1;
for(n=1;n<5;n=n+1)begin
if(co[n][24]!==hist[8][24]||(co[n][24]&&co[n][23:0]!==hist[8][23:0]))reqerr[n]=reqerr[n]+1;
if(co[n][140]!==hist[8][140]||(co[n][140]&&co[n][139:116]!==hist[8][139:116]))reqerr[n]=reqerr[n]+1;
if(co[n][165]!==hist[8][165]||(co[n][165]&&co[n][164:141]!==hist[8][164:141]))reqerr[n]=reqerr[n]+1;
if(co[n][190]!==hist[8][190]||(co[n][190]&&co[n][189:166]!==hist[8][189:166]))reqerr[n]=reqerr[n]+1;
if(co[n][247]!==hist[17][247]||(co[n][247]&&co[n][246:191]!==hist[17][246:191]))dataerr[n]=dataerr[n]+1;
if(co[n][81]!==hist[17][81]||(co[n][81]&&co[n][80:25]!==hist[17][80:25]))dataerr[n]=dataerr[n]+1;
if(co[n][115]!==hist[17][115]||(co[n][115]&&co[n][114:83]!==hist[17][114:83]))dataerr[n]=dataerr[n]+1;
for(lag=0;lag<41;lag=lag+1)if(co[n][82] !== (lag==0?co[0][82]:hist[lag-1][82]))faultphase[n][lag]=faultphase[n][lag]+1;
end
// Retimed candidates 5..8: request vs CURRENT oracle co[0] (address advanced by K cancels the 9-edge transport),
// data vs oracle delayed 9 (co_R(T)=co0(T-9)); extra prefix/overshoot valids counted, not errors.
for(n=5;n<9;n=n+1)begin
for(k=0;k<4;k=k+1)begin
integer vb_i,lo_i,hi_i;
case(k)0:begin vb_i=24;lo_i=0;hi_i=23;end 1:begin vb_i=140;lo_i=116;hi_i=139;end 2:begin vb_i=165;lo_i=141;hi_i=164;end default:begin vb_i=190;lo_i=166;hi_i=189;end endcase
if(co[0][vb_i]===1'b1&&co[n][vb_i]!==1'b1)reqerr[n]=reqerr[n]+1;
else if(co[0][vb_i]===1'b1&&co[n][lo_i +: 24]!==co[0][lo_i +: 24])reqerr[n]=reqerr[n]+1;
else if(co[0][vb_i]!==1'b1&&co[n][vb_i]===1'b1)reqextra[n]=reqextra[n]+1;
end
// data at +9
if(co[n][247]!==hist[8][247]||(co[n][247]&&co[n][246:191]!==hist[8][246:191]))begin dataerr[n]=dataerr[n]+1;if(n==5&&dbg&&dbg_cnt<400)begin dbg_cnt=dbg_cnt+1;$display("DBG5 vm cycle=%0d ep=%0d step=%0d cls=%0d got=%b/%h want=%b/%h",cycle,ep,step,cls,co[n][247],co[n][246:191],hist[8][247],hist[8][246:191]);end if(((320+640*ep)/768)%2==1&&!noasrc)derr_a1[n]=derr_a1[n]+1;else derr_a0[n]=derr_a0[n]+1;if(ep>=0&&ep<10)derr_ep[n][ep]=derr_ep[n][ep]+1;end
if(co[n][81]!==hist[8][81]||(co[n][81]&&co[n][80:25]!==hist[8][80:25]))begin dataerr[n]=dataerr[n]+1;if(n==5&&dbg&&dbg_cnt<400)begin dbg_cnt=dbg_cnt+1;$display("DBG5 kv cycle=%0d ep=%0d step=%0d cls=%0d got=%b/%h want=%b/%h",cycle,ep,step,cls,co[n][81],co[n][80:25],hist[8][81],hist[8][80:25]);end if(((320+640*ep)/768)%2==1&&!noasrc)derr_a1[n]=derr_a1[n]+1;else derr_a0[n]=derr_a0[n]+1;if(ep>=0&&ep<10)derr_ep[n][ep]=derr_ep[n][ep]+1;end
if(hist[8][115]===1'b1&&(co[n][115]!==1'b1||co[n][114:83]!==hist[8][114:83]))begin dataerr[n]=dataerr[n]+1;if(n==5&&dbg&&dbg_cnt<400)begin dbg_cnt=dbg_cnt+1;$display("DBG5 ov cycle=%0d ep=%0d step=%0d cls=%0d got=%b/%h want=%h",cycle,ep,step,cls,co[n][115],co[n][114:83],hist[8][114:83]);end if(((320+640*ep)/768)%2==1&&!noasrc)derr_a1[n]=derr_a1[n]+1;else derr_a0[n]=derr_a0[n]+1;if(ep>=0&&ep<10)derr_ep[n][ep]=derr_ep[n][ep]+1;end
if(hist[8][115]!==1'b1&&co[n][115]===1'b1)ovextra[n]=ovextra[n]+1;
if((co[n][247]===1'b1&&hist[8][247]!==1'b1)||(co[n][81]===1'b1&&hist[8][81]!==1'b1))vwextra[n]=vwextra[n]+1;
for(lag=0;lag<41;lag=lag+1)if(co[n][82] !== (lag==0?co[0][82]:hist[lag-1][82]))faultphase[n][lag]=faultphase[n][lag]+1;
end end
if(cycle==6700)begin
for(n=0;n<8;n=n+1)$display("COUNT %0d %0d",n,counts[n]);for(n=0;n<5;n=n+1)$display("CLASS %0d %0d",n,clcounts[n]);
for(n=1;n<9;n=n+1)begin $display("CANDIDATE %0d req_errors=%0d data_errors=%0d",n,reqerr[n],dataerr[n]);if(n>=5)for(lag=0;lag<10;lag=lag+1)$display("DERR_EP %0d ep=%0d errors=%0d",n,lag,derr_ep[n][lag]);for(lag=0;lag<41;lag=lag+1)$display("FAULT %0d lag=%0d errors=%0d",n,lag,faultphase[n][lag]);if(n>=5)$display("RETIME %0d req_extra=%0d ov_extra=%0d wr_extra=%0d derr_asrc0=%0d derr_asrc1=%0d",n,reqextra[n],ovextra[n],vwextra[n],derr_a0[n],derr_a1[n]);end
$display("BASE_GOLDEN checks=%0d errors=%0d",golden_checks,golden_errors);$display("WARM_LEAK %0d",warmleak);$finish;end
end
endmodule
