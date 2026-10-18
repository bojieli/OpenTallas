`timescale 1ns/1ps
// KVJ-B 2026-10-17: exhaustive bench of qkd_attn_cal_gen against the bench-feeding calendar generators.
// +GOLD=<file>: one line per T, 56 hex digits {T[15:0], cal[175:0], tx_first[15:0], end[15:0]} written by
// tools/qwen_attention_native/run_cal_gen_bench.sh from attn_calendar.calendar_w16 / compile_native_endpoint.
// Phase 1 issues every T back to back (initiation interval 1) and checks each done in order (cal, link ages, epoch tag,
// latency LAT); phase 2 issues single tokens with gaps (held result, valid); phase 3 checks fault stays low, then
// rises on T = 0 / 8193 / 16383.  Prints CALGEN PASS / CALGEN FAIL.
// STRETCH=1 (KVJ-SMALL 10-17): the gold is kv_static_programme.attention_calendar(T, profile, service_end) with the
// fixed link words (run_cal_gen_bench.sh stretch configs); D_QK / D_RL / SERVICE_END come from that profile.
module tb_qkd_attn_cal_gen;
 parameter integer G3S2=1,RX_CMD=2,STRETCH=0,D_QK=0,D_RL=0,SERVICE_END=1777,MUT=0;
 localparam integer LAT=10;
 reg clk=0,rst_n=0;always #1 clk=~clk;
 reg go=0;reg [13:0] ctx_t=0;reg [15:0] epoch=0;
 wire [175:0] cal;wire [15:0] rx_cmd,tx_first,end_age,cal_epoch;wire done,valid,fault;
 qkd_attn_cal_gen #(.G3S2(G3S2),.RX_CMD(RX_CMD),.STRETCH(STRETCH),.D_QK(D_QK),.D_RL(D_RL),.SERVICE_END(SERVICE_END),.MUT(MUT)) u(.ck(clk),.rst_n(rst_n),.go(go),.ctx_t(ctx_t),.epoch(epoch),
  .cal(cal),.rx_cmd(rx_cmd),.tx_first(tx_first),.end_age(end_age),.cal_epoch(cal_epoch),.done(done),.valid(valid),.fault(fault));
 reg [223:0] gold[0:8191];integer ng=0,issued=0,checked=0,errors=0,cyc=0;
 integer q_idx[0:65535];integer q_cyc[0:65535];integer qw=0,qr=0;
 string gf;reg ph3=0;   // phase 3: illegal-T dones carry no gold
 always @(posedge clk)cyc<=cyc+1;
 task automatic err(input string m);errors=errors+1;if(errors<=10)$display("MISMATCH %s",m);endtask
 always @(negedge clk)if(rst_n&&done&&!ph3)begin
  if(qr>=qw)err("done without go");
  else begin
   integer i;reg [223:0] g;i=q_idx[qr];g=gold[i];
   if(cyc-q_cyc[qr]!=LAT)err($sformatf("latency %0d",cyc-q_cyc[qr]));
   if(cal!==g[207:32])err($sformatf("T=%0d cal %h gold %h",g[223:208],cal,g[207:32]));
   if(tx_first!==g[31:16]||end_age!==g[15:0])err($sformatf("T=%0d link ages %0d/%0d gold %0d/%0d",g[223:208],tx_first,end_age,g[31:16],g[15:0]));
   if(rx_cmd!==16'(RX_CMD))err("rx_cmd");
   if(cal_epoch!==(g[223:208]^16'h5a5a))err("epoch tag");
   if(!valid)err("valid low with a result");
   qr=qr+1;checked=checked+1;
  end
 end
 task automatic issue(input integer i);
  @(posedge clk);#0.25;go=1;ctx_t=14'(gold[i][223:208]);epoch=gold[i][223:208]^16'h5a5a;q_idx[qw]=i;q_cyc[qw]=cyc;qw=qw+1;
 endtask
 initial begin
  integer fd,c,k;reg [223:0] v;
  if(!$value$plusargs("GOLD=%s",gf))$fatal(1,"+GOLD required");
  fd=$fopen(gf,"r");while(!$feof(fd)&&ng<8192)begin c=$fscanf(fd,"%h\n",v);if(c==1)begin gold[ng]=v;ng=ng+1;end end $fclose(fd);
  $display("CALGEN start G3S2=%0d RX_CMD=%0d STRETCH=%0d D_QK=%0d D_RL=%0d SERVICE_END=%0d MUT=%0d gold=%0d",G3S2,RX_CMD,STRETCH,D_QK,D_RL,SERVICE_END,MUT,ng);
  repeat(3)@(posedge clk);#0.5 rst_n=1;
  for(k=0;k<ng;k=k+1)issue(k);                                  // phase 1: II = 1
  @(posedge clk);#0.25 go=0;
  repeat(LAT+2)@(posedge clk);
  for(k=0;k<64;k=k+1)begin issue(($urandom%ng));@(posedge clk);#0.25 go=0;repeat($urandom%(2*LAT))@(posedge clk);end  // phase 2
  repeat(LAT+2)@(posedge clk);
  if(!valid)err("result not held");
  if(fault)err("fault on legal T");
  ph3=1;
  for(k=0;k<3;k=k+1)begin                                        // phase 3
   @(posedge clk);#0.25 rst_n=0;#0.5 rst_n=1;
   @(posedge clk);#0.25;go=1;ctx_t=(k==0)?14'd0:(k==1)?14'd8193:14'd16383;
   @(posedge clk);#0.25 go=0;repeat(LAT+2)@(posedge clk);
   if(!fault)err($sformatf("no fault for T=%0d",ctx_t));
  end
  if(errors==0&&checked==ng+64)$display("CALGEN PASS checked=%0d (all T, II=1, +64 held) faults=3",checked);
  else $display("CALGEN FAIL errors=%0d checked=%0d",errors,checked);
  $finish;
 end
endmodule
