`timescale 1ns/1ps
module tb_vms_static_ring4_memory;
parameter integer MUT=0;
// PIN_IN (H-SM 2026-10-17): every bank data/slot input passes one pin flop (the literal input pin registers of the
// bound masters hfd_vms_bank_native_q0_faces / hfd_vms_bank_native_q1_core_pr).  P=PIN_IN: the compiler moves the
// mirror egress tx (eg) +P, every downstream ring/slot/WACK reservation +2P (bank in + bank out per traversal: eg +P
// at the source, xq_done +P at the receiver), reads +P; the stop's COMMIT_DELAY = 5 + P (RTL parameter).  CDX: mutant
// override of COMMIT_DELAY (-1 = 5 + P).
parameter integer PIN_IN=0, CDX=-1;
localparam integer P=PIN_IN, CD=(CDX<0)?5+PIN_IN:CDX;
reg clk=0;always #5 clk=~clk;
reg rst_n=0;
reg [1:0] node_sid[0:3];
reg [33:0] rq[0:3];wire [513:0] rr[0:3];
reg [561:0] wq[0:3];wire [1:0] done[0:3];
reg rv[0:3],wv[0:3];reg [1:0] rs[0:3];reg [2:0] ws[0:3];
wire [17:0] status[0:3];wire [275:0] eg[0:3];
wire [2207:0] xq[0:3][0:1];wire xd[0:3][0:1];
wire [2223:0] link[0:3][0:1];
wire [2:0] wko[0:3][0:1];wire ack[0:3][0:1],busy[0:3][0:1],fault[0:3][0:1];
reg tx[0:3][0:1];reg [2:0] pick[0:3][0:1];
for(genvar n=0;n<4;n=n+1) begin:B
  reg brv,bwv;reg [1:0] brs;reg [2:0] bws;reg [33:0] brq;reg [561:0] bwq;reg [275:0] bx0,bx1;
  if(PIN_IN!=0)begin:pin always @(posedge clk) begin brv<=rv[n];bwv<=wv[n];brs<=rs[n];bws<=ws[n];brq<=rq[n];bwq<=wq[n];
    bx0<=xq[n][0][275:0];bx1<=xq[n][1][275:0];end end
  else begin:nopin always @* begin brv=rv[n];bwv=wv[n];brs=rs[n];bws=ws[n];brq=rq[n];bwq=wq[n];bx0=xq[n][0][275:0];bx1=xq[n][1][275:0];end end
  ot_vms_bank_static #(.RG(2),.WG(2)) bank(.clk(clk),.rst_n(rst_n),.bid(3'd0),.sid(node_sid[n]),
    .rslot_v(brv),.rslot(brs),.wslot_v(bwv),.wslot(bws),.rq(brq),.rr(rr[n]),.wq(bwq),.wq_done(done[n]),
    .dq(281'd0),.dq_done(),.kq(281'd0),.kq_done(),.xq(bx0),.xq_done(xd[n][0]),
    .xq2(bx1),.xq2_done(xd[n][1]),.eg(eg[n]),.pq(285'd0),.pr(),.status(status[n]));
  for(genvar d=0;d<2;d=d+1) begin:D
    localparam P=d==0?(n+3)%4:(n+1)%4;
    ot_vms_rstop_static #(.COMMIT_DELAY(CD),.MUT(n==0&&d==0?MUT:0)) stop(.clk(clk),.rst_n(rst_n),.sid(node_sid[n]),.dir(1'(d)),
      .tx_enable(tx[n][d]),.tx_source(pick[n][d]),.l_in(link[P][d]),.l_out(link[n][d]),.pi(290'd0),
      .eg({1932'd0,eg[n]}),.xq(xq[n][d]),.xq_done({7'd0,xd[n][d]}),.rce(),.ri(266'd0),
      .wko(wko[n][d]),.wki(wko[n][1-d]),.cco(),.ack_o(ack[n][d]),.ack_i(ack[n][1-d]),.mirror_busy(busy[n][d]),.fault(fault[n][d]));
  end
end
integer cyc=0,s,n,d,k,base,phase,source=0,cw1,cw2,ccw1;
integer ack_count[0:3][0:1],commit_count[0:3],read_count=0;
reg [255:0] main_expected[0:3],mirror_expected;
reg [256:0] expected[0:299][0:3];
reg [1:0] done_expected[0:299][0:3];
reg [1:0] xdone_expected[0:299][0:3];
reg [1:0] ack_expected[0:299][0:3];
reg [1:0] wko_expected[0:299][0:3];
function automatic [255:0] pattern(input integer value);
for(integer i=0;i<8;i=i+1) pattern[i*32+:32]=32'h6a09e667*(value+i+1);
endfunction
function automatic [15:0] sector(input integer node,input bit mir);
sector={mir,mir?2'b0:node_sid[node],10'd17,3'd0};
endfunction
task automatic clear;
begin
for(integer i=0;i<4;i=i+1) begin
rq[i]=0;wq[i]=0;rv[i]=0;wv[i]=0;rs[i]=0;ws[i]=0;
for(integer j=0;j<2;j=j+1) begin tx[i][j]=0;pick[i][j]=0;end
end
end
endtask
task automatic tick;
begin
@(posedge clk);#1;
for(integer i=0;i<4;i=i+1) begin
if(status[i]!==0) $fatal(1,"bank status cyc%0d node%0d =%h",cyc,i,status[i]);
if(rr[i][256]!==expected[cyc][i][256]||rr[i][513]!==0) $fatal(1,"read timing cyc%0d node%0d",cyc,i);
if(expected[cyc][i][256]) begin
if(rr[i][255:0]!==expected[cyc][i][255:0]) $fatal(1,"actual SRAM data cyc%0d sid%0d got%h exp%h",cyc,node_sid[i],rr[i][255:0],expected[cyc][i][255:0]);
read_count=read_count+1;
end
if(done[i]!==done_expected[cyc][i]) $fatal(1,"local done timing cyc%0d node%0d",cyc,i);
if({xd[i][1],xd[i][0]}!==xdone_expected[cyc][i]) $fatal(1,"remote done timing cyc%0d node%0d got%b expected%b",cyc,i,{xd[i][1],xd[i][0]},xdone_expected[cyc][i]);
for(integer j=0;j<2;j=j+1) begin
if(fault[i][j]!==0) $fatal(1,"stop fault cyc%0d sid%0d dir%0d",cyc,node_sid[i],j);
if(ack[i][j]!==ack_expected[cyc][i][j]) $fatal(1,"ack timing cyc%0d node%0d dir%0d",cyc,i,j);
if(wko[i][j][2]!==wko_expected[cyc][i][j]) $fatal(1,"commit ack timing cyc%0d node%0d dir%0d",cyc,i,j);
if(wko[i][j][2]&&wko[i][j][1:0]!==node_sid[source]) $fatal(1,"commit ack source identity");
if(ack[i][j]) ack_count[i][j]=ack_count[i][j]+1;
if(xd[i][j]) commit_count[i]=commit_count[i]+1;
end
end
cyc=cyc+1;@(negedge clk);
end
endtask
initial begin
node_sid[0]=0;node_sid[1]=1;node_sid[2]=3;node_sid[3]=2;
for(n=0;n<4;n=n+1) begin commit_count[n]=0;for(d=0;d<2;d=d+1) ack_count[n][d]=0;end
for(k=0;k<300;k=k+1)for(n=0;n<4;n=n+1) begin expected[k][n]=0;done_expected[k][n]=0;xdone_expected[k][n]=0;ack_expected[k][n]=0;wko_expected[k][n]=0;end
clear();repeat(3) @(negedge clk);rst_n=1;
// Distinct real main SRAM words must survive all replicated mirror writes.
for(n=0;n<4;n=n+1)begin
main_expected[n]=pattern(n+20);wv[n]=1;ws[n]=0;wq[n][280:0]={1'b1,sector(n,0),main_expected[n],8'hff};done_expected[3+P][n]=1;
end
tick();clear();while(cyc<20) tick();
// Compiler-reserved schedule, repeated with each physical source. No tx selection
// is derived from arriving requests or response validity.
for(s=0;s<4;s=s+1)begin
source=s;cw1=(s+1)%4;cw2=(s+2)%4;ccw1=(s+3)%4;base=20+s*40;
mirror_expected=pattern(s+200);
done_expected[base+3+P][s]=1;
xdone_expected[base+9+2*P][cw1][0]=1;xdone_expected[base+11+2*P][cw2][0]=1;xdone_expected[base+9+2*P][ccw1][1]=1;
wko_expected[base+10+2*P][cw1][0]=1;wko_expected[base+12+2*P][cw2][0]=1;wko_expected[base+10+2*P][ccw1][1]=1;
ack_expected[base+14+2*P][s]=2'b11;ack_expected[base+18+2*P][s][1]=1;
for(phase=0;phase<40;phase=phase+1)begin
clear();
// compiler calendar with the PIN_IN shifts (P = 0 is the original schedule edge for edge)
if(phase==0)begin wv[s]=1;ws[s]=0;wq[s][280:0]={1'b1,sector(s,1),mirror_expected,8'hff};end
if(phase==2+P)begin tx[s][0]=1;pick[s][0]=2;tx[s][1]=1;pick[s][1]=2;end
if(phase==4+P)begin tx[cw1][0]=1;pick[cw1][0]=0;end
if(phase==11+2*P)begin tx[cw1][1]=1;pick[cw1][1]=4;tx[ccw1][0]=1;pick[ccw1][0]=4;end
if(phase==13+2*P)begin tx[cw2][1]=1;pick[cw2][1]=4;end
if(phase==15+2*P)begin tx[cw1][1]=1;pick[cw1][1]=0;end
if(phase==26||phase==27)begin
for(n=0;n<4;n=n+1)begin rv[n]=1;rs[n]=0;rq[n][16:0]={1'b1,sector(n,phase==26)};expected[cyc+6+P][n]={1'b1,phase==26?mirror_expected:main_expected[n]};end
end
// The bank samples stop output xq one edge after it appears.
if(phase==6+P)begin wv[cw1]=1;ws[cw1]=3;wv[ccw1]=1;ws[ccw1]=5;end
if(phase==8+P)begin wv[cw2]=1;ws[cw2]=3;end
// Observation only: reservations above do not depend on mirror_busy.
if(phase==25)for(n=0;n<4;n=n+1)for(d=0;d<2;d=d+1) if(busy[n][d]) $fatal(1,"outstanding not drained node%0d dir%0d",n,d);
tick();
end
end
for(n=0;n<4;n=n+1)begin
if(commit_count[n]!=3) $fatal(1,"expected three remote actual macro commits per node");
if(ack_count[n][0]!=1||ack_count[n][1]!=2) $fatal(1,"exact source acknowledgment counts node%0d CW%0d CCW%0d",n,ack_count[n][0],ack_count[n][1]);
end
$display("PASS ring4 actual SRAM PIN_IN=%0d COMMIT_DELAY=%0d:",PIN_IN,CD," physical sid order0,1,3,2; four banks twelve real macros eight stops; 4 mirrors,12 remote commits,12 WACK,32 main/mirror exact reads; read+6 commit+3; no faults, all outstanding drained; cycles=%0d",cyc);$finish;
end
endmodule
