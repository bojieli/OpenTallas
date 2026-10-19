`timescale 1ns/1ps
// HBM-BANKLAT-DMA 10-19: the DMA write-back controller (ot_hgi_dma_back_static_vp4_banks: controller + 8 real landing
// banks) against a die model with the d4g bank contract and GEN2c lanes:
//   rq lane (17 b, registered stages LQ_b = GEN2c lq_b + die pad_b) -> faces bank model (pin flop + ot_vms_bank_static
//   n+6: rr launch = rq launch + FACES_D, 8 for hfd_vms_bank_native_q0_faces, 7 for a bare ot_vms_bank_static)
//   -> rr lane (257 b, LR_b = GEN2c lr_b stages, never padded) -> controller rr.
// The die pads every bank to DIE_RT (scalar budget): pad_b = DIE_RT - FACES_D - lq_b - lr_b.  The compiler derives
// drain_at = issue_at + DIE_RT + 3 + slack (d4g_bank_latency.dma_min_drain_lag).  The bank model answers each request
// with a payload that is a function of the requested VM sector, so every landing slot is checked through the real
// landing SRAMs: each wd beat must carry the data of the VM sector that maps to its HBM address, exactly once, on the
// compiled edge drain_at + WD_K + chunk; no fault; one mv_src and one mv_done per move.
// Defines: RR_RT (DUT parameter; undefined -> DUT instantiated without override = closed default), DIE_RT, FACES_D,
// LANES (0 none, 1 GEN2c NE quadrant), PAD_SHORT (bank whose pad is one short, -1 none), LAG_ADJ (drain lag vs rule).
`ifndef DIE_RT
`define DIE_RT 7
`endif
`ifndef FACES_D
`define FACES_D 7
`endif
`ifndef LANES
`define LANES 0
`endif
`ifndef PAD_SHORT
`define PAD_SHORT -1
`endif
`ifndef LAG_ADJ
`define LAG_ADJ 0
`endif
`ifndef WD_K
`define WD_K 3
`endif
module tb_dma_vp4_banklat;
 localparam integer DIE_RT=`DIE_RT, D=`FACES_D;
 // GEN2c contract_pre (artifacts/hdie-d4/d4g_gen2c/net/contract_pre.json) hb_dbk_NE <-> vmb_NE<b> rq1/rr1 relay edges
 function automatic integer lq(input integer b);
  case(b) 0,1,6,7: lq=21; 2,3: lq=17; default: lq=25; endcase if(`LANES!=1)lq=0;
 endfunction
 function automatic integer lr(input integer b);
  case(b) 0,6,7: lr=20; 1: lr=21; 2: lr=16; 3: lr=17; 4: lr=24; default: lr=25; endcase if(`LANES!=1)lr=0;
 endfunction
 function automatic integer pad(input integer b);
  pad=DIE_RT-D-lq(b)-lr(b)-((b==`PAD_SHORT)?1:0);
 endfunction
 reg clk=0; always #5 clk=~clk; reg rst_n=0; reg [31:0] cycle=0;
 reg mv_v=0; reg [226:0] mv=0; reg [31:0] issue_at=0,drain_at=0;
 wire src,done,fault,quiet,busy,reserve,rbank,fbank,fill; wire [15:0] repoch,fepoch; wire [11:0] rsec; wire [31:0] rbase;
 wire [135:0] rq; wire [2055:0] rr; wire [2311:0] wd; reg [11:0] wa=0; reg [11:0] ack[0:4];
`ifdef RR_RT
 ot_hgi_dma_back_static_vp4_banks #(.RR_RT(`RR_RT)) dut(
`else
 ot_hgi_dma_back_static_vp4_banks dut(
`endif
  .clk(clk),.clk_bank({8{clk}}),.rst_n(rst_n),.stk(2'd0),.cycle(cycle),.mv_v(mv_v),.mv(mv),.issue_at(issue_at),.drain_at(drain_at),
  .mv_wb_bank(1'b0),.mv_wb_epoch(16'h1234),.mv_src(src),.mv_done(done),.mv_fault(fault),.quiet(quiet),.busy(busy),
  .rq(rq),.rr(rr),.wb_reserve_v(reserve),.wb_reserve_bank(rbank),.wb_fill_bank(fbank),.wb_reserve_epoch(repoch),
  .wb_fill_epoch(fepoch),.wb_reserve_sectors(rsec),.wb_reserve_base(rbase),.wb_fill_start(fill),.wb_ready(1'b1),.wd(wd),.wa(wa));
 function automatic [255:0] vmdata(input [15:0] sec);
  for(integer k=0;k<8;k=k+1)vmdata[k*32+:32]=32'h9e3779b9*(32'(sec)+1)+32'(k)*32'h01010101;
 endfunction
 // ---- die: rq lane + pad, faces bank model, rr lane (registered stages, no flow control)
 for(genvar b=0;b<8;b=b+1)begin:DIE
  localparam integer NQ=lq(b)+pad(b), NR=lr(b);
  reg [16:0] qs[0:NQ]; reg [256:0] rs[0:NR]; reg [256:0] bk[0:D];
  always @* begin qs[0]=rq[b*17+:17]; end
  always @(posedge clk)for(integer i=1;i<=NQ;i=i+1)qs[i]<=rst_n?qs[i-1]:17'd0;
  // bank: samples its (pin) input one edge after launch, answers D edges after the request launch
  always @* bk[0]={qs[NQ][16],vmdata(qs[NQ][15:0])};
  always @(posedge clk)for(integer i=1;i<=D;i=i+1)bk[i]<=rst_n?bk[i-1]:257'd0;
  always @* rs[0]=bk[D];
  always @(posedge clk)for(integer i=1;i<=NR;i=i+1)rs[i]<=rst_n?rs[i-1]:257'd0;
  assign rr[b*257+:257]={rs[NR][256],rs[NR][256]?rs[NR][255:0]:256'd0};
  initial if(NQ<0)begin $display("BANKLAT FAIL die cannot pad bank %0d: round trip %0d > budget %0d",b,D+lq(b)+lr(b),DIE_RT);$fatal(1);end
 end
 always @(posedge clk)begin
  cycle<=cycle+1;
  begin:ACK integer n; n=0;for(integer b=0;b<8;b=b+1)if(wd[b*289+288])n=n+1;ack[0]<=12'(n);end
  for(integer k=1;k<5;k=k+1)ack[k]<=ack[k-1];
 end
 function automatic [226:0] descriptor(input integer nsec,input integer rows);
  descriptor={21'(nsec*8),20'(rows),16'd1,32'(nsec*32),40'h100000,3'd0,2'd0,16'd1,32'(((nsec+7)/8)*64),40'd0,3'd0,2'd1};
 endfunction
 integer cur_move=-1,cur_nsec=1,cur_drain=0,beats=0,srcs=0,dones=0,bad=0,wdk=-999,checks=0;
 reg seen[0:131071];
 always @(negedge clk)if(rst_n)begin
  wa=ack[4]; checks=checks+1;
  if(fault)begin $display("BANKLAT FAIL mv_fault at cycle %0d move %0d (landing/response latency or drain lag) lag_ok %0b resp %b/%b",cycle,cur_move,dut.u_control.c_lag_ok,dut.u_control.rr_valid,dut.u_control.expect_response_q);$fatal(1); end
  if(src)srcs=srcs+1; if(done)dones=dones+1;
  for(integer j=0;j<8;j=j+1)if(wd[j*289+288])begin : BEAT
   reg [31:0] a; integer off,r,col,vmidx,chunk,dk;
   a=wd[j*289+256+:32]; off=int'(a)-32'h8000; r=off/cur_nsec; col=off%cur_nsec; vmidx=r*(((cur_nsec+7)/8)*8)+col;
   chunk=r*((cur_nsec+7)/8)+col/8; dk=int'(cycle)-cur_drain-chunk;
   if(off<0||col%8!=j)begin $display("BANKLAT FAIL beat bank%0d addr %h off %0d",j,a,off);$fatal(1);end
   if(seen[off])begin $display("BANKLAT FAIL duplicate beat off %0d",off);$fatal(1);end
   seen[off]=1;
   if(wd[j*289+:256]!==vmdata(16'(vmidx)))begin
    $display("BANKLAT FAIL landing payload cycle %0d bank%0d off %0d (vm sector %0d): got %h",cycle,j,off,vmidx,wd[j*289+:32]);$fatal(1);end
   if(dk!=`WD_K)begin $display("BANKLAT FAIL wd edge: cycle %0d = drain_at %0d + chunk %0d + %0d (calendar expects +%0d)",cycle,cur_drain,chunk,dk,`WD_K);$fatal(1);end
   beats=beats+1;
  end
 end
 integer NS[0:7],RW[0:7],SL[0:7],expect_beats=0,lag,t0;
 initial begin : TMO #50000000; $display("BANKLAT FAIL timeout"); $fatal(1); end
 initial begin
  NS[0]=1;RW[0]=1;SL[0]=0; NS[1]=17;RW[1]=1;SL[1]=3; NS[2]=8;RW[2]=2;SL[2]=0; NS[3]=64;RW[3]=16;SL[3]=0;
  NS[4]=8;RW[4]=80;SL[4]=5; NS[5]=1023;RW[5]=1;SL[5]=0; NS[6]=16;RW[6]=3;SL[6]=0; NS[7]=24;RW[7]=5;SL[7]=1;
  for(integer k=0;k<5;k=k+1)ack[k]=0;
  for(integer b=0;b<8;b=b+1)$display("BANKLAT die bank%0d: rq lane %0d + pad %0d, bank %0d, rr lane %0d -> round trip %0d",
                                      b,lq(b),pad(b),D,lr(b),lq(b)+pad(b)+D+lr(b));
  lag=DIE_RT+3+`LAG_ADJ;   // compiler rule: drain_rel - issue_rel >= RR_RT + 3 (RR_RT = the die's padded round trip)
  repeat(5)@(posedge clk); rst_n=1; repeat(8)@(posedge clk);
  for(integer e=0;e<8;e=e+1)begin
   for(integer i=0;i<131072;i=i+1)seen[i]=0;
   @(negedge clk); #1; cur_nsec=NS[e]; cur_move=e;
   mv=descriptor(NS[e],RW[e]); issue_at=cycle+8; drain_at=cycle+8+lag+SL[e]; cur_drain=drain_at; mv_v=1;
   @(negedge clk); #1; mv_v=0; expect_beats=expect_beats+NS[e]*RW[e]; t0=cycle;
   while(!(dones==e+1) && cycle<t0+lag+SL[e]+((NS[e]+7)/8)*RW[e]+200)@(negedge clk);
   if(dones!=e+1||beats!=expect_beats||srcs!=e+1)begin
    $display("BANKLAT FAIL move %0d (nsec %0d rows %0d): beats %0d/%0d src %0d done %0d",e,NS[e],RW[e],beats,expect_beats,srcs,dones);$fatal(1);end
   repeat(3)@(negedge clk);
  end
  $display("BANKLAT PASS RR_RT_die=%0d faces_D=%0d lanes=%0d moves=8 beats=%0d checks=%0d lag=%0d (every landing slot through the real landing SRAMs, wd on drain_at+%0d+chunk)",
           DIE_RT,D,`LANES,beats,checks,lag,`WD_K);
  $finish;
 end
endmodule
