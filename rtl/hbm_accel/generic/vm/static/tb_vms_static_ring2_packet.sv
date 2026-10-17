`timescale 1ns/1ps
// A2P (H-NETLIST 2026-10-16): native packet path over the 2-node VM ring (N_Q=2, sid 0 = SW, sid 2 = NW): real
// hubs, replay controllers, banks and stops.  Per source: a remote write and a remote read (PREQ on CW, replay at the
// target, PRSP back on CCW, exact user response), then a NATIVE MIRROR write (local bank + CW to the other node; the hub
// expects exactly 2 acknowledgements).  MUT 1: replay return port flipped.  MUT 2: node 0 hub/stops built N_Q=4 (wrong
// ring size).  Both must FAIL.
module tb_vms_static_ring2_packet;
parameter integer MUT=0;
reg clk=0;always #5 clk=~clk;
reg rst_n=0;
reg [1:0] sid[0:1];
reg [337:0] local_cq[0:1];wire [337:0] hq[0:1];wire [547:0] cr[0:1];
reg [3:0] seq[0:1],response_seq[0:1];reg [1:0] response_enable[0:1];
reg [7:0] bank_enable[0:1];reg [7:0] bank_client[0:1];reg cw_enable[0:1],ccw_enable[0:1];
wire [2279:0] pq[0:1];wire [265:0] pr[0:1];wire [2:0] hub_status[0:1];
wire [289:0] pi[0:1][0:1];wire [263:0] cco[0:1][0:1];
wire [287:0] rce[0:1][0:1];wire [265:0] ri[0:1][0:1];
wire rcl_fault[0:1];reg rx[0:1],rxsource[0:1];
reg rv[0:1],wv[0:1];reg [1:0] rs[0:1];reg [2:0] ws[0:1];
wire [17:0] bank_status[0:1];
reg [561:0] wq[0:1];wire [1:0] wd[0:1];
wire [2223:0] link[0:1][0:1];wire fault[0:1][0:1];
reg tx[0:1][0:1];reg [2:0] pick[0:1][0:1];
for(genvar n=0;n<2;n=n+1)begin:N
  localparam integer NQ=(MUT==2&&n==0)?4:2;
  ot_vms_bank_static #(.RG(2),.WG(2)) bank(.clk(clk),.rst_n(rst_n),.bid(3'd0),.sid(sid[n]),
    .rslot_v(rv[n]),.rslot(rs[n]),.wslot_v(wv[n]),.wslot(ws[n]),.rq(34'd0),.rr(),.wq(wq[n]),.wq_done(wd[n]),
    .dq(281'd0),.dq_done(),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(pq[n][284:0]),.pr(pr[n]),.status(bank_status[n]));
  ot_vms_hub_static #(.N_Q(NQ),.NC(1)) hub(.clk(clk),.rst_n(rst_n),.sid(sid[n]),.cq({hq[n],local_cq[n]}),.client_seq(seq[n]),
    .bank_enable(bank_enable[n]),.bank_client(bank_client[n]),.cw_enable(cw_enable[n]),.cw_client(1'b0),.ccw_enable(ccw_enable[n]),.ccw_client(1'b0),
    .cr(cr[n]),.pq(pq[n]),.pr({1862'd0,pr[n]}),.cwi(pi[n][0]),.cci(pi[n][1]),.cco0(cco[n][0]),.cco1(cco[n][1]),
    .response_enable(response_enable[n]),.response_seq(response_seq[n]),.status(hub_status[n]));
  ot_vms_rcl_static #(.MUT(MUT==1?1:0)) replay(.clk(clk),.rst_n(rst_n),.sid(sid[n]),.rx_enable(rx[n]),.rx_source(rxsource[n]),
    .rce0(rce[n][0]),.rce1(rce[n][1]),.hq(hq[n]),.hr(cr[n][547:274]),.ri0(ri[n][0]),.ri1(ri[n][1]),.fault(rcl_fault[n]));
  for(genvar d=0;d<2;d=d+1)begin:D
    ot_vms_rstop_static #(.N_Q(NQ)) stop(.clk(clk),.rst_n(rst_n),.sid(sid[n]),.dir(1'(d)),.tx_enable(tx[n][d]),.tx_source(pick[n][d]),
      .l_in(link[1-n][d]),.l_out(link[n][d]),.pi(pi[n][d]),.eg(2208'd0),.xq(),.xq_done(8'd0),.rce(rce[n][d]),.ri(ri[n][d]),
      .wko(),.wki(3'd0),.cco(cco[n][d]),.ack_o(),.ack_i(1'b0),.mirror_busy(),.fault(fault[n][d]));
  end
end
integer cyc=0,n,t,source,target,phase,bbase,kind;
integer completions=0,replays=0;
reg we;
reg [255:0] expected_memory[0:1],payload;
reg [273:0] expect_cr[0:499][0:1];
reg expect_replay[0:499][0:1];
reg [15:0] usertag;
function automatic [255:0] pattern(input integer value);
for(integer i=0;i<8;i=i+1) pattern[i*32+:32]=32'hbb67ae85*(value+i+1);
endfunction
function automatic [31:0] addr(input integer node);
addr={11'd0,1'b0,sid[node],10'd17,3'd0,5'd0};
endfunction
function automatic [31:0] maddr;   // native mirror sector (section 00)
maddr={11'd0,1'b1,2'b00,10'd21,3'd0,5'd0};
endfunction
task automatic clear;
begin
for(integer i=0;i<2;i=i+1)begin
local_cq[i]=0;seq[i]=0;response_seq[i]=0;response_enable[i]=0;bank_enable[i]=0;bank_client[i]=0;cw_enable[i]=0;ccw_enable[i]=0;
rx[i]=0;rxsource[i]=0;rv[i]=0;wv[i]=0;rs[i]=0;ws[i]=0;wq[i]=0;
for(integer j=0;j<2;j=j+1)begin tx[i][j]=0;pick[i][j]=0;end
end
end
endtask
task automatic tick;
begin
@(posedge clk);#1;
for(integer i=0;i<2;i=i+1)begin
if(bank_status[i]!==0||hub_status[i]!==0||rcl_fault[i]!==0) $fatal(1,"native packet component fault cycle%0d node%0d bank%h hub%h rcl%b",cyc,i,bank_status[i],hub_status[i],rcl_fault[i]);
for(integer j=0;j<2;j=j+1)if(fault[i][j]!==0) $fatal(1,"native stop fault cycle%0d node%0d dir%0d",cyc,i,j);
if(cr[i][273]!==expect_cr[cyc][i][273]||(expect_cr[cyc][i][273]&&cr[i][273:0]!==expect_cr[cyc][i])) $fatal(1,"source response timing/tag/actual SRAM data cycle%0d sid%0d got%h expect%h",cyc,sid[i],cr[i][273:0],expect_cr[cyc][i]);
if(cr[i][273]) completions=completions+1;
if(hq[i][337]!==expect_replay[cyc][i]) $fatal(1,"native replay timing cycle%0d node%0d",cyc,i);
if(hq[i][337]) replays=replays+1;
end
cyc=cyc+1;@(negedge clk);
end
endtask
initial begin
sid[0]=0;sid[1]=2;
for(t=0;t<500;t=t+1)for(n=0;n<2;n=n+1)begin expect_cr[t][n]=0;expect_replay[t][n]=0;end
clear();repeat(3)@(negedge clk);rst_n=1;
for(n=0;n<2;n=n+1)begin
expected_memory[n]=pattern(n+10);wv[n]=1;ws[n]=0;wq[n][280:0]={1'b1,16'((addr(n)>>5)),expected_memory[n],8'hff};
end
tick();clear();while(cyc<20)tick();
// t: source = t/3, kind = t%3 (0 remote write, 1 remote read, 2 native mirror write)
for(t=0;t<6;t=t+1)begin
source=t/3;kind=t%3;target=1-source;
bbase=20+40*t;we=kind!=1;payload=pattern(200+t);usertag=16'hf200+16'(t);
if(kind==0)expected_memory[target]=payload;
expect_replay[bbase+7][target]=1;
expect_cr[bbase+26][source]={1'b1,usertag,we,we?256'd0:expected_memory[target]};
for(phase=0;phase<40;phase=phase+1)begin
clear();
if(phase==0)begin
local_cq[source]=(kind==2)?{1'b1,1'b1,maddr(),payload,32'hffffffff,usertag}:{1'b1,we,addr(target),payload,32'hffffffff,usertag};
seq[source][1:0]=2'(t%4);cw_enable[source]=1;
if(kind==2)begin bank_enable[source]=1;bank_client[source]=0;end   // local copy of the mirror write
end
if(kind==2&&phase==2)begin wv[source]=1;ws[source]=4;end
if(phase==2)begin tx[source][0]=1;pick[source][0]=1;end
if(phase==6)begin rx[target]=1;rxsource[target]=1'b0;end
if(phase==8)begin bank_enable[target]=1;bank_client[target]=1;end
if(phase==10)begin if(we)begin wv[target]=1;ws[target]=4;end else begin rv[target]=1;rs[target]=2;end end
if(phase==17)begin response_enable[target][1]=1;response_seq[target][3:2]=0;end
if(phase==21)begin tx[target][1]=1;pick[target][1]=3;end
if(phase==25)begin response_enable[source][0]=1;response_seq[source][1:0]=2'(t%4);end
tick();
end
end
if(completions!=6||replays!=6)$fatal(1,"packet coverage missing %0d %0d",completions,replays);
$display("PASS ring2 packet real SRAM: N_Q=2 sid0(SW)/sid2(NW); two banks two hubs two replay controllers four stops; 2 remote writes, 2 remote reads, 2 native mirror writes (local+CW, 2 acks); PREQ CW / PRSP CCW 1 hop; all statuses clean; cycles=%0d",cyc);$finish;
end
endmodule
