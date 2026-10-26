`timescale 1ns/1ps
// HBM-VMEARLY-DMA 10-19: back-to-back DMA-back moves (ot_hgi_dma_back_static_vp4_banks #(RR_RT 80): controller + 8 real
// landing banks) on the d4g die model of tb_dma_vp4_banklat (GEN2c NE rq/rr lanes, faces bank n+7, die pads every bank
// to DIE_RT), driven by the static compiler calendar, and EXPOSED edges measured per move:
//   exposed(i) = first wd beat of move i+1 - last wd beat of move i - 1   (edges the HBM write port idles between moves)
// The last move (RAWM) DEPENDS on a producer's VM write: the producer retires its write into the VM bank at edge TP and
// the move's VM read issues at issue_at = TP (contract: t_iss >= producer retire); its data must be the NEW data.
// Calendar (ISSUE_AHEAD 0 = what the controller accepts today):
//   mv_v at tb cycle C_i;  issue_at = C_i + LEAD;  drain_at = issue_at + DIE_RT + 3 + SL_i;  end_at = drain_at + nchunk + 1
//   C_{i+1} = max(end_at_i - K,  TP - LEAD for the RAW move)       (K: the earliest next-command edge the controller takes)
// Every wd beat is checked through the real landing SRAMs (payload = f(VM sector, producer version), exactly once, on
// drain_at + 3 + chunk of ITS move), no mv_fault, one mv_src per move; mv_done (= idle and every write acknowledged)
// fires once the burst is quiet, as the controller defines it.
// Defines: RR_RT, DIE_RT, FACES_D, LANES as tb_dma_vp4_banklat; K (default 3); LEAD (default 6);
//   AHEAD1  : drive the ISSUE_AHEAD-1 calendar instead (issue_at(i+1) = drain_at(i), command during move i's drain)
//   STALE   : the producer retires its write AFTER the RAW move's reads reached the banks (read before the write)
`ifndef DIE_RT
`define DIE_RT 80
`endif
`ifndef FACES_D
`define FACES_D 8
`endif
`ifndef LANES
`define LANES 1
`endif
`ifndef K
`define K 3
`endif
`ifndef LEAD
`define LEAD 6
`endif
module tb_dma_vp4_vmearly;
 localparam integer DIE_RT=`DIE_RT, D=`FACES_D, NM=6, RAWM=5, WD_K=3;
 function automatic integer lq(input integer b);
  case(b) 0,1,6,7: lq=21; 2,3: lq=17; default: lq=25; endcase if(`LANES!=1)lq=0;
 endfunction
 function automatic integer lr(input integer b);
  case(b) 0,6,7: lr=20; 1: lr=21; 2: lr=16; 3: lr=17; 4: lr=24; default: lr=25; endcase if(`LANES!=1)lr=0;
 endfunction
 function automatic integer pad(input integer b);
  pad=DIE_RT-D-lq(b)-lr(b);
 endfunction
 reg clk=0; always #5 clk=~clk; reg rst_n=0; reg [31:0] cycle=0;
 reg mv_v=0; reg [226:0] mv=0; reg [31:0] issue_at=0,drain_at=0;
 wire src,done,fault,quiet,busy,reserve,rbank,fbank,fill; wire [15:0] repoch,fepoch; wire [11:0] rsec; wire [31:0] rbase;
 wire [135:0] rq; wire [2055:0] rr; wire [2311:0] wd; reg [11:0] wa=0; reg [11:0] ack[0:4];
 ot_hgi_dma_back_static_vp4_banks #(.RR_RT(`RR_RT)) dut(
  .clk(clk),.clk_bank({8{clk}}),.rst_n(rst_n),.stk(2'd0),.cycle(cycle),.mv_v(mv_v),.mv(mv),.issue_at(issue_at),.drain_at(drain_at),
  .mv_wb_bank(1'b0),.mv_wb_epoch(16'h1234),.mv_src(src),.mv_done(done),.mv_fault(fault),.quiet(quiet),.busy(busy),
  .rq(rq),.rr(rr),.wb_reserve_v(reserve),.wb_reserve_bank(rbank),.wb_fill_bank(fbank),.wb_reserve_epoch(repoch),
  .wb_fill_epoch(fepoch),.wb_reserve_sectors(rsec),.wb_reserve_base(rbase),.wb_fill_start(fill),.wb_ready(1'b1),.wd(wd),.wa(wa));
 // VM contents: f(sector) xor the producer's version mark (the producer of the RAW move rewrites its sectors at TP)
 reg ver[0:65535]; integer TP=-1; integer raw_nsec=1;
 function automatic [255:0] vmdata(input [15:0] sec,input v);
  for(integer k=0;k<8;k=k+1)vmdata[k*32+:32]=(32'h9e3779b9*(32'(sec)+1)+32'(k)*32'h01010101)^(v?32'h5a5aa5a5:32'd0);
 endfunction
 always @(posedge clk)if(TP>=0&&int'(cycle)==TP)for(integer s=0;s<raw_nsec;s=s+1)ver[s]<=1'b1;   // producer write retires
 for(genvar b=0;b<8;b=b+1)begin:DIE
  localparam integer NQ=lq(b)+pad(b), NR=lr(b);
  reg [16:0] qs[0:NQ]; reg [256:0] rs[0:NR]; reg [256:0] bk[0:D];
  always @* begin qs[0]=rq[b*17+:17]; end
  always @(posedge clk)for(integer i=1;i<=NQ;i=i+1)qs[i]<=rst_n?qs[i-1]:17'd0;
  always @* bk[0]={qs[NQ][16],vmdata(qs[NQ][15:0],ver[qs[NQ][15:0]])};
  always @(posedge clk)for(integer i=1;i<=D;i=i+1)bk[i]<=rst_n?bk[i-1]:257'd0;
  always @* rs[0]=bk[D];
  always @(posedge clk)for(integer i=1;i<=NR;i=i+1)rs[i]<=rst_n?rs[i-1]:257'd0;
  assign rr[b*257+:257]={rs[NR][256],rs[NR][256]?rs[NR][255:0]:256'd0};
  initial if(NQ<0)begin $display("VMEARLY FAIL die cannot pad bank %0d",b);$fatal(1);end
 end
 integer NQMAX; initial begin NQMAX=0; for(integer b=0;b<8;b=b+1)if(lq(b)+pad(b)>NQMAX)NQMAX=lq(b)+pad(b); end
 always @(posedge clk)begin
  cycle<=cycle+1;
  begin:ACK integer n; n=0;for(integer b=0;b<8;b=b+1)if(wd[b*289+288])n=n+1;ack[0]<=12'(n);end
  for(integer k=1;k<5;k=k+1)ack[k]<=ack[k-1];
 end
 function automatic [226:0] descriptor(input integer nsec,input integer rows);
  descriptor={21'(nsec*8),20'(rows),16'd1,32'(nsec*32),40'h100000,3'd0,2'd0,16'd1,32'(((nsec+7)/8)*64),40'd0,3'd0,2'd1};
 endfunction
 integer NS[0:NM-1],RW[0:NM-1],SL[0:NM-1],NC[0:NM-1],CI[0:NM-1],CD[0:NM-1],CE[0:NM-1],FW[0:NM-1],LW[0:NM-1],NB[0:NM-1];
 integer issued=-1,srcs=0,dones=0,expect_beats=0,beats=0;
 reg seen[0:NM-1][0:131071];
 always @(negedge clk)if(rst_n)begin
  wa=ack[4];
  if(fault)begin $display("VMEARLY FAIL mv_fault at cycle %0d (moves issued %0d): lag_ok %0b busy %0b",cycle,issued+1,dut.u_control.c_lag_ok,busy);$fatal(1); end
  if(src)srcs=srcs+1; if(done)dones=dones+1;
  for(integer j=0;j<8;j=j+1)if(wd[j*289+288])begin : BEAT
   reg [31:0] a; integer off,r,col,vmidx,chunk,dk,m,ns;
   m=-1; for(integer q=0;q<NM;q=q+1)if(q<=issued&&int'(cycle)>=CD[q]+WD_K)m=q;
   if(m<0)begin $display("VMEARLY FAIL wd beat at cycle %0d before any drain",cycle);$fatal(1);end
   ns=NS[m]; a=wd[j*289+256+:32]; off=int'(a)-32'h8000; r=off/ns; col=off%ns; vmidx=r*(((ns+7)/8)*8)+col;
   chunk=r*((ns+7)/8)+col/8; dk=int'(cycle)-CD[m]-chunk;
   if(off<0||col%8!=j)begin $display("VMEARLY FAIL beat bank%0d addr %h off %0d move %0d",j,a,off,m);$fatal(1);end
   if(seen[m][off])begin $display("VMEARLY FAIL duplicate beat off %0d move %0d",off,m);$fatal(1);end
   seen[m][off]=1;
   if(wd[j*289+:256]!==vmdata(16'(vmidx),m==RAWM))begin
    $display("VMEARLY FAIL payload cycle %0d move %0d bank%0d off %0d (vm sector %0d): got %h want %h (%s)",cycle,m,j,off,vmidx,
             wd[j*289+:32],vmdata(16'(vmidx),m==RAWM)[31:0],(m==RAWM)?"stale: read before the producer's write":"wrong data");$fatal(1);end
   if(dk!=WD_K)begin $display("VMEARLY FAIL wd edge: cycle %0d move %0d = drain_at %0d + chunk %0d + %0d",cycle,m,CD[m],chunk,dk);$fatal(1);end
   if(FW[m]<0)FW[m]=int'(cycle); LW[m]=int'(cycle); NB[m]=NB[m]+1; beats=beats+1;
  end
 end
 initial begin : TMO #20000000; $display("VMEARLY FAIL timeout"); $fatal(1); end
 integer C,lag,sum_exp,t; integer EXP[0:NM-1];
 initial begin
  // DS KVWB_DS window_row_append-shaped moves (64 sectors = 8 chunks) plus partial / long / 128-chunk moves
  NS[0]=64;RW[0]=1;SL[0]=0;  NS[1]=64;RW[1]=1;SL[1]=0;  NS[2]=17;RW[2]=1;SL[2]=2;
  NS[3]=8;RW[3]=80;SL[3]=0;  NS[4]=1023;RW[4]=1;SL[4]=0; NS[5]=64;RW[5]=1;SL[5]=0;
  for(integer e=0;e<NM;e=e+1)begin NC[e]=RW[e]*((NS[e]+7)/8); FW[e]=-1; LW[e]=-1; NB[e]=0; end
  for(integer s=0;s<65536;s=s+1)ver[s]=0;
  for(integer k=0;k<5;k=k+1)ack[k]=0;
  raw_nsec=NS[RAWM];
  lag=DIE_RT+3;
  repeat(5)@(posedge clk); rst_n=1; repeat(8)@(posedge clk);
  @(negedge clk); C=int'(cycle)+2;
  for(integer e=0;e<NM;e=e+1)begin
   if(e>0)begin
`ifdef AHEAD1
    C=CD[e-1]-`LEAD;                       // ISSUE_AHEAD 1: issue_at(e) = start (drain_at) of move e-1
`else
    C=CE[e-1]-`K;                          // ISSUE_AHEAD 0: next command K edges before move e-1 ends
`endif
   end
   CI[e]=C+`LEAD; CD[e]=CI[e]+lag+SL[e]; CE[e]=CD[e]+NC[e]+1;
   if(e==RAWM)begin
`ifdef STALE
    TP=CI[e]+NQMAX+2;                       // producer write retires after every request of the move reached its bank
`else
    TP=CI[e];                               // producer write retired at the issue edge (contract: t_iss >= retire)
`endif
   end
   while(int'(cycle)<C)@(negedge clk);
   if(int'(cycle)!=C)begin $display("VMEARLY FAIL calendar slipped: move %0d at %0d wanted %0d",e,cycle,C);$fatal(1);end
   #1; mv=descriptor(NS[e],RW[e]); issue_at=32'(CI[e]); drain_at=32'(CD[e]); mv_v=1; issued=e;
   expect_beats=expect_beats+NS[e]*RW[e];
   @(negedge clk); #1; mv_v=0;
  end
  t=int'(cycle);
  while(!(dones>=1&&quiet&&beats==expect_beats) && int'(cycle)<CE[NM-1]+400)@(negedge clk);
  if(dones<1||!quiet||beats!=expect_beats||srcs!=NM)begin
   $display("VMEARLY FAIL beats %0d/%0d src %0d done %0d (moves %0d)",beats,expect_beats,srcs,dones,NM);$fatal(1);end
  sum_exp=0;
  for(integer e=0;e<NM;e=e+1)begin
   if(NB[e]!=NS[e]*RW[e])begin $display("VMEARLY FAIL move %0d beats %0d/%0d",e,NB[e],NS[e]*RW[e]);$fatal(1);end
   EXP[e]=(e+1<NM)?FW[e+1]-LW[e]-1:0; if(e+1<NM)sum_exp=sum_exp+EXP[e];
   $display("VMEARLY move %0d nsec %0d rows %0d chunks %0d: cmd %0d issue_at %0d drain_at %0d end_at %0d first_wd %0d last_wd %0d%s",
            e,NS[e],RW[e],NC[e],CI[e]-`LEAD,CI[e],CD[e],CE[e],FW[e],LW[e],(e==RAWM)?" RAW":"");
   if(e+1<NM)$display("VMEARLY exposed move %0d -> %0d: %0d edges (first_wd %0d - last_wd %0d - 1)",e,e+1,EXP[e],FW[e+1],LW[e]);
  end
  $display("VMEARLY RAW move %0d: producer retire %0d -> issue %0d -> first wd %0d (+%0d) -> last wd %0d (+%0d)",
           RAWM,TP,CI[RAWM],FW[RAWM],FW[RAWM]-TP,LW[RAWM],LW[RAWM]-TP);
  $display("VMEARLY PASS RR_RT=%0d K=%0d LEAD=%0d moves=%0d beats=%0d exposed_sum=%0d over %0d back-to-back pairs (mean %0d), RAW new data exact",
           DIE_RT,`K,`LEAD,NM,beats,sum_exp,NM-1,sum_exp/(NM-1));
  $finish;
 end
endmodule
