`timescale 1ns/1ps
// A2P (H-NETLIST 2026-10-16): the VM ring as a REAL 2-node ring (N_Q=2): node 0 = sid 0 (SW), node 1 = sid 2 (NW);
// SW.cw_out -> NW.cw_in, NW.cw_out -> SW.cw_in, NW.ccw_out -> SW.ccw_in, SW.ccw_out -> NW.ccw_in.  Real bank SRAMs.
// Each node in turn writes a mirror word: CW stop egress (only) -> the other node commits it into its real SRAM
// (bank write owner CW ring), WACK returns on the CCW ring and retires the CW outstanding; then every node reads its
// main and mirror sectors.  Exact edges checked every cycle (commit, WACK, ack, read data).
// MUT 1: node 0 CW stop flips a mirror payload bit (ring payload mutant).  MUT 2: node 0 stops built N_Q=4 (wrong ring
// size / neighbour: mirror addressed to the 4-ring ranks).  Both must FAIL.
module tb_vms_static_ring2_memory;
parameter integer MUT=0;
reg clk=0;always #5 clk=~clk;
reg rst_n=0;
reg [1:0] node_sid[0:1];
reg [33:0] rq[0:1];wire [513:0] rr[0:1];
reg [561:0] wq[0:1];wire [1:0] done[0:1];
reg rv[0:1],wv[0:1];reg [1:0] rs[0:1];reg [2:0] ws[0:1];
wire [17:0] status[0:1];wire [275:0] eg[0:1];
wire [2207:0] xq[0:1][0:1];wire xd[0:1][0:1];
wire [2223:0] link[0:1][0:1];
wire [2:0] wko[0:1][0:1];wire ack[0:1][0:1],busy[0:1][0:1],fault[0:1][0:1];
reg tx[0:1][0:1];reg [2:0] pick[0:1][0:1];
for(genvar n=0;n<2;n=n+1) begin:B
  ot_vms_bank_static #(.RG(2),.WG(2)) bank(.clk(clk),.rst_n(rst_n),.bid(3'd0),.sid(node_sid[n]),
    .rslot_v(rv[n]),.rslot(rs[n]),.wslot_v(wv[n]),.wslot(ws[n]),.rq(rq[n]),.rr(rr[n]),.wq(wq[n]),.wq_done(done[n]),
    .dq(281'd0),.dq_done(),.kq(281'd0),.kq_done(),.xq(xq[n][0][275:0]),.xq_done(xd[n][0]),
    .xq2(xq[n][1][275:0]),.xq2_done(xd[n][1]),.eg(eg[n]),.pq(285'd0),.pr(),.status(status[n]));
  for(genvar d=0;d<2;d=d+1) begin:D
    ot_vms_rstop_static #(.N_Q((MUT==2&&n==0)?4:2),.COMMIT_DELAY(5),.MUT(n==0&&d==0&&MUT==1?1:0)) stop(.clk(clk),.rst_n(rst_n),.sid(node_sid[n]),.dir(1'(d)),
      .tx_enable(tx[n][d]),.tx_source(pick[n][d]),.l_in(link[1-n][d]),.l_out(link[n][d]),.pi(290'd0),
      .eg({1932'd0,eg[n]}),.xq(xq[n][d]),.xq_done({7'd0,xd[n][d]}),.rce(),.ri(266'd0),
      .wko(wko[n][d]),.wki(wko[n][1-d]),.cco(),.ack_o(ack[n][d]),.ack_i(ack[n][1-d]),.mirror_busy(busy[n][d]),.fault(fault[n][d]));
  end
end
integer cyc=0,s,o,n,d,base,phase,source=0;
integer ack_count[0:1][0:1],commit_count[0:1],read_count=0;
reg [255:0] main_expected[0:1],mirror_expected;
reg [256:0] expected[0:199][0:1];
reg [1:0] done_expected[0:199][0:1],xdone_expected[0:199][0:1],ack_expected[0:199][0:1],wko_expected[0:199][0:1];
function automatic [255:0] pattern(input integer value);
for(integer i=0;i<8;i=i+1) pattern[i*32+:32]=32'h6a09e667*(value+i+1);
endfunction
function automatic [15:0] sector(input integer node,input bit mir);
sector={mir,mir?2'b0:node_sid[node],10'd17,3'd0};
endfunction
task automatic clear;
begin
for(integer i=0;i<2;i=i+1) begin
rq[i]=0;wq[i]=0;rv[i]=0;wv[i]=0;rs[i]=0;ws[i]=0;
for(integer j=0;j<2;j=j+1) begin tx[i][j]=0;pick[i][j]=0;end
end
end
endtask
task automatic tick;
begin
@(posedge clk);#1;
for(integer i=0;i<2;i=i+1) begin
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
node_sid[0]=0;node_sid[1]=2;
for(n=0;n<2;n=n+1) begin commit_count[n]=0;for(d=0;d<2;d=d+1) ack_count[n][d]=0;end
for(base=0;base<200;base=base+1)for(n=0;n<2;n=n+1) begin expected[base][n]=0;done_expected[base][n]=0;xdone_expected[base][n]=0;ack_expected[base][n]=0;wko_expected[base][n]=0;end
clear();repeat(3) @(negedge clk);rst_n=1;
for(n=0;n<2;n=n+1)begin
main_expected[n]=pattern(n+20);wv[n]=1;ws[n]=0;wq[n][280:0]={1'b1,sector(n,0),main_expected[n],8'hff};done_expected[3][n]=1;
end
tick();clear();while(cyc<20) tick();
for(s=0;s<2;s=s+1)begin
source=s;o=1-s;base=20+s*40;
mirror_expected=pattern(s+200);
done_expected[base+3][s]=1;
xdone_expected[base+9][o][0]=1;
wko_expected[base+10][o][0]=1;
ack_expected[base+14][s][1]=1;
for(phase=0;phase<40;phase=phase+1)begin
clear();
case(phase)
0:begin wv[s]=1;ws[s]=0;wq[s][280:0]={1'b1,sector(s,1),mirror_expected,8'hff};end
2:begin tx[s][0]=1;pick[s][0]=2;end                 // mirror egress on the CW stop only (2-node ring)
11:begin tx[o][1]=1;pick[o][1]=4;end                // WACK back on the CCW ring
26,27:begin
for(n=0;n<2;n=n+1)begin rv[n]=1;rs[n]=0;rq[n][16:0]={1'b1,sector(n,phase==26)};expected[cyc+6][n]={1'b1,phase==26?mirror_expected:main_expected[n]};end
end
endcase
if(phase==6)begin wv[o]=1;ws[o]=3;end                // bank write owner WG+1 = CW ring
if(phase==25)for(n=0;n<2;n=n+1)for(d=0;d<2;d=d+1) if(busy[n][d]) $fatal(1,"outstanding not drained node%0d dir%0d",n,d);
tick();
end
end
for(n=0;n<2;n=n+1)begin
if(commit_count[n]!=1) $fatal(1,"expected one remote actual macro commit per node");
if(ack_count[n][0]!=0||ack_count[n][1]!=1) $fatal(1,"exact source acknowledgment counts node%0d CW%0d CCW%0d",n,ack_count[n][0],ack_count[n][1]);
end
if(read_count!=8) $fatal(1,"read coverage %0d",read_count);
$display("PASS ring2 actual SRAM: N_Q=2 sid0(SW)/sid2(NW); two banks four stops; 2 mirrors (CW only),2 remote commits,2 WACK (CCW),8 main/mirror exact reads; no faults, outstanding drained; cycles=%0d",cyc);$finish;
end
endmodule
