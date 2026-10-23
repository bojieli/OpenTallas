`timescale 1ps/1ps
`default_nettype none
// STEWARD-HBMd/PINREG q9 2026-10-23: cycle-exact lockstep of ot_hbm_svc_wb_kport_q KPREG=0 (u_ref, current K ring
// output = one-hot AND-OR after the ring flops) against KPREG=1 (u_dut, registered ring heads + folded-address flop).
// Both instances get IDENTICAL stimulus every edge: DMA reservations / fills of NB blocks (varied size, alignment, both
// banks overlapped), random per-PC w_k_rdy back-pressure (bursty: long stalls fill the 3-entry rings, then free-run),
// and w_k_wr_done completions returned for u_ref's accepted writes after a random 1..12-edge delay.  EVERY output of both
// instances (wb_ready, wa, wbw_v, wbw_base, wbw_total, w_k_v, w_k_addr, w_k_wdata, fault) is compared after EVERY
// stream and hbm edge from time 0 (2-state, zero initial values: ring entries and heads both start 0).
// Exit: "PASS tb_hbm_svc_wb_kq8_kpreg_lockstep ..." with counts, else "FAIL ..." + $fatal.
// Params: DMUT = u_dut MUT (12 / 13 = registered-head mutants: must FAIL), QE quad strap, PP, WOPEN.
// Plusargs: +SEED=<n> (stimulus), +NB=<n> blocks (default 10), +RDYP=<0..100> ready probability when not stalled.
module tb_hbm_svc_wb_kq8_kpreg_lockstep;
 parameter integer QE=1, DMUT=0, PP=1, WOPEN=0;
 localparam [1:0] STK=2'd2;localparam [31:0] O_BASE=32'h14400000;
 reg hbm=0,stream=0,hrst=0,srst=0;
 always #512 hbm=~hbm;
 always #417 stream=~stream;
 reg rv=0,rb=0,fb=0,fs=0;reg[15:0]re=0,fe=0;reg[11:0]rt=0;reg[31:0]rbase=0;reg[2311:0]wd=0;
 reg[15:0]rdy=0,done=0;
 wire a_ready,b_ready,a_fault,b_fault,a_wbw_v,b_wbw_v;wire[11:0]a_wa,b_wa,a_wbw_total,b_wbw_total;wire[29:0]a_wbw_base,b_wbw_base;
 wire[15:0]a_k_v,b_k_v;wire[479:0]a_k_addr,b_k_addr;wire[4095:0]a_k_wdata,b_k_wdata;
 ot_hbm_svc_wb_kport_q #(.WOPEN(WOPEN),.MUT(0),.PP(PP),.KPREG(0)) u_ref(.stream_clk(stream),.stream_rst_n(srst),.hbm_clk(hbm),
  .hbm_rst_n(hrst),.stream_fifo_clk({4{stream}}),.stk(STK),.quad(1'(QE)),
  .wb_reserve_v(rv),.wb_reserve_bank(rb),.wb_fill_bank(fb),.wb_reserve_epoch(re),.wb_fill_epoch(fe),.wb_reserve_sectors(rt),
  .wb_reserve_base(rbase),.wb_fill_start(fs),.wd(wd),.wb_ready(a_ready),.wa(a_wa),
  .wbw_v(a_wbw_v),.wbw_base(a_wbw_base),.wbw_total(a_wbw_total),
  .w_k_v(a_k_v),.w_k_rdy(rdy),.w_k_addr(a_k_addr),.w_k_wdata(a_k_wdata),.w_k_wr_done(done),.fault(a_fault));
 ot_hbm_svc_wb_kport_q #(.WOPEN(WOPEN),.MUT(DMUT),.PP(PP),.KPREG(1)) u_dut(.stream_clk(stream),.stream_rst_n(srst),.hbm_clk(hbm),
  .hbm_rst_n(hrst),.stream_fifo_clk({4{stream}}),.stk(STK),.quad(1'(QE)),
  .wb_reserve_v(rv),.wb_reserve_bank(rb),.wb_fill_bank(fb),.wb_reserve_epoch(re),.wb_fill_epoch(fe),.wb_reserve_sectors(rt),
  .wb_reserve_base(rbase),.wb_fill_start(fs),.wd(wd),.wb_ready(b_ready),.wa(b_wa),
  .wbw_v(b_wbw_v),.wbw_base(b_wbw_base),.wbw_total(b_wbw_total),
  .w_k_v(b_k_v),.w_k_rdy(rdy),.w_k_addr(b_k_addr),.w_k_wdata(b_k_wdata),.w_k_wr_done(done),.fault(b_fault));
 // ---------------------------------------------------------------- every output, every edge
 longint cmp_s=0,cmp_h=0,mism=0,fires=0,stall_fires=0,posted=0,blocks_done=0,kv_hi=0;
 task automatic compare(input string dom);
  if(a_ready!==b_ready||a_wa!==b_wa||a_wbw_v!==b_wbw_v||a_wbw_base!==b_wbw_base||a_wbw_total!==b_wbw_total||a_fault!==b_fault||
     a_k_v!==b_k_v||a_k_addr!==b_k_addr||a_k_wdata!==b_k_wdata)begin
   mism=mism+1;
   if(mism<=8)begin
    integer p;
    $display("MISMATCH %s t=%0t ready %b/%b wa %0d/%0d wbw %b/%b fault %b/%b k_v %h/%h",dom,$time,a_ready,b_ready,a_wa,b_wa,
             a_wbw_v,b_wbw_v,a_fault,b_fault,a_k_v,b_k_v);
    for(p=0;p<16;p=p+1)if(a_k_addr[30*p+:30]!==b_k_addr[30*p+:30]||a_k_wdata[256*p+:256]!==b_k_wdata[256*p+:256])
     $display("  PC %0d v %b rdy %b addr %h/%h wdata[63:0] %h/%h",p,a_k_v[p],rdy[p],a_k_addr[30*p+:30],b_k_addr[30*p+:30],
              a_k_wdata[256*p+:64],b_k_wdata[256*p+:64]);
   end
  end
 endtask
 always @(posedge stream)begin #1;compare("stream");cmp_s=cmp_s+1;end
 always @(posedge hbm)begin #1;compare("hbm");cmp_h=cmp_h+1;end
 // ---------------------------------------------------------------- K side: bursty ready, completions for u_ref's writes
 integer seed=1,RDYP=60,stall[0:15],pend[0:15][$];
 integer cyc_h=0;
 always @(negedge hbm)begin : kside
  integer p,j;
  cyc_h=cyc_h+1;
  done=0;
  for(p=0;p<16;p=p+1)begin
   // completions: oldest pending write whose delay has elapsed (at most one per PC per edge)
   if(pend[p].size()>0&&pend[p][0]<=cyc_h)begin done[p]=1'b1;void'(pend[p].pop_front());end
   // ready: stall bursts of 1..40 edges (rings fill), otherwise random with probability RDYP
   if(stall[p]>0)begin stall[p]=stall[p]-1;rdy[p]=1'b0;end
   else if($urandom%100<3)begin stall[p]=1+$urandom%40;rdy[p]=1'b0;end
   else rdy[p]=($urandom%100)<RDYP;
  end
 end
 always @(posedge hbm)begin : kfire
  integer p;
  for(p=0;p<16;p=p+1)begin
   if(a_k_v[p])kv_hi=kv_hi+1;
   if(a_k_v[p]&&rdy[p])begin fires=fires+1;pend[p].push_back(cyc_h+1+$urandom%12);end
  end
 end
 reg fault_seen=0;
 always @(posedge stream)if((a_fault||b_fault)&&!fault_seen)begin fault_seen<=1;$display("FAULT t=%0t ref %b dut %b (stream_sticky %b/%b hbm_sticky %b/%b)",$time,a_fault,b_fault,u_ref.u_wb.stream_sticky,u_dut.u_wb.stream_sticky,u_ref.u_wb.hbm_sticky,u_dut.u_wb.hbm_sticky);end
 always @(posedge stream)if(a_wa!=0)begin posted=posted+a_wa;blocks_done=blocks_done+1;end
 // ---------------------------------------------------------------- DMA side
 function automatic [255:0] wbimg(input [29:0] a,input [15:0] e);
  reg[255:0]r;integer i;begin for(i=0;i<8;i=i+1)r[32*i+:32]=(32'(a)*32'h7feb352d)^(32'(e)*32'h846ca68b)^(32'(i)*32'h27d4eb2d)^32'h5a5a_0000;wbimg=r;end
 endfunction
 localparam integer NBMAX=32;
 integer NB=10,boff[0:NBMAX-1],btot[0:NBMAX-1],issued_tot=0;
 task automatic run_block(input integer b);
  integer r,s,rows,t;reg[29:0]o;
  begin
   @(negedge stream);rv=1;rb=b[0];fb=b[0];re=16'h300+16'(b);fe=16'h300+16'(b);rt=12'(btot[b]);
   rbase={STK,30'(O_BASE)+30'(boff[b])};
   @(negedge stream);rv=0;
   t=0;while(a_ready!==1'b1&&t<5000)begin @(negedge stream);t=t+1;end
   repeat(12)@(negedge stream);
   if(a_ready!==1'b1)begin $display("FAIL block %0d: wb_ready never rose",b);$fatal(1);end
   fs=1;@(negedge stream);fs=0;
   rows=(btot[b]+7)/8;
   for(r=0;r<rows;r=r+1)begin
    wd=0;
    for(s=0;s<8;s=s+1)if(r*8+s<btot[b])begin
     o=30'(O_BASE)+30'(boff[b]+r*8+s);
     wd[289*s+:289]={1'b1,STK,o,wbimg(o,16'(16'h300+b))};
    end
    @(negedge stream);
   end
   wd=0;issued_tot=issued_tot+btot[b];
  end
 endtask
 integer b,t,p;
 initial begin
  if($value$plusargs("SEED=%d",seed));if($value$plusargs("NB=%d",NB));if($value$plusargs("RDYP=%d",RDYP));
  if(NB>NBMAX)NB=NBMAX;
  void'($urandom(seed));
  for(p=0;p<16;p=p+1)stall[p]=0;
  for(b=0;b<NB;b=b+1)begin
   btot[b]=(b==0)?1:(b==1)?1984:(b==2)?640:(b==3)?300:(b==4)?1024:(b==5)?7:1+$urandom%1500;   // total <= 1984: real window span <= 4095 (wb_kport_q contract)
   boff[b]=(b==0)?0:boff[b-1]+btot[b-1]+((b%3==0)?0:$urandom%97);
  end
  #(20000);hrst=1;srst=1;
  repeat(40)@(negedge stream);
  for(b=0;b<NB;b=b+1)begin
   // two banks in flight: block b waits for block b-2 to be posted (wa)
   t=0;while(blocks_done<b-1&&t<400000)begin @(negedge stream);t=t+1;end
   run_block(b);
   repeat(5+$urandom%40)@(negedge stream);
  end
  t=0;while(blocks_done<NB&&t<400000)begin @(negedge stream);t=t+1;end
  repeat(200)@(negedge hbm);
  if(mism!=0||blocks_done!=NB||posted!=issued_tot||fires!=issued_tot||a_fault!==1'b0||b_fault!==1'b0)begin
   $display("FAIL tb_hbm_svc_wb_kq8_kpreg_lockstep DMUT=%0d QE=%0d PP=%0d SEED=%0d mismatches=%0d blocks=%0d/%0d posted=%0d fires=%0d issued=%0d fault=%b/%b",
            DMUT,QE,PP,seed,mism,blocks_done,NB,posted,fires,issued_tot,a_fault,b_fault);
   $fatal(1);
  end
  $display("PASS tb_hbm_svc_wb_kq8_kpreg_lockstep DMUT=%0d QE=%0d PP=%0d WOPEN=%0d SEED=%0d blocks=%0d sectors=%0d K_fires=%0d K_valid_edges=%0d (back-pressured %0d) compares stream=%0d hbm=%0d mismatches=0",
           DMUT,QE,PP,WOPEN,seed,NB,issued_tot,fires,kv_hi,kv_hi-fires,cmp_s,cmp_h);
  $finish;
 end
endmodule
`default_nettype wire
