`timescale 1ns/1ps
module tb_hbm_link_retry_sram;
 parameter TB_DEPTH=512, TB_SW=12;
 localparam W=551, SW=TB_SW, DEPTH=TB_DEPTH, ATO=DEPTH+24;
 reg clk=0; always #5 clk=~clk;
 reg rst=0; reg [15:0] epoch=1;
 reg iv=0; wire ir,tv; wire [W-1:0] td;
 reg [W-1:0] id=0; wire [SW-1:0] ts;
 wire [15:0] te; reg rv=0,ue=0,ordy=1;
 reg [W-1:0] rd=0; reg [SW-1:0] rs=0; reg [15:0] re=1;
 wire rr,ov; wire [W-1:0] od; wire [SW-1:0] ack,debt;
 wire nak; wire [15:0] ae; wire fault; wire [31:0] retries;
 reg fv=0,fg=1,fn=0; reg [SW-1:0] fs=0; reg [15:0] fe=1;
 wire tr= !rv || rr;
 ot_hbm_link_retry_sram #(.ENABLE(1),.W(W),.SW(SW),.DEPTH(DEPTH),.TIMEOUT(ATO),.MAX_RETRY(3)) dut
 (.clk(clk),.rst_n(rst),.session(epoch),.in_valid(iv),.in_ready(ir),.in_data(id),
 .tx_valid(tv),.tx_ready(tr),.tx_data(td),.tx_seq(ts),.tx_session(te),
 .rx_valid(rv),.rx_ready(rr),.rx_ue(ue),.rx_data(rd),.rx_seq(rs),.rx_session(re),
 .out_valid(ov),.out_ready(ordy),.out_data(od),.ack_seq(ack),.ack_nak(nak),.ack_session(ae),
 .fb_valid(fv),.fb_good(fg),.fb_nak(fn),.fb_seq(fs),.fb_session(fe),.fault(fault),.retained(debt),.replay_count(retries));
 function [W-1:0] payload(input integer n);
 integer j; begin for(j=0;j<W;j=j+1) payload[j]=((j*17+n*31)^(n>>(j%7)))&1; payload[31:0]=n; end endfunction
 integer seen=0, sent=0, cycle=0, inject=0;
 reg run=0, corrupt=0, feedback_on=1;
 // One-cycle elastic FEC channel with controlled UE at sequence 5.
 always @(negedge clk) if(run) begin
  cycle=cycle+1;
  fv=feedback_on; fs=ack; fn=nak; fe=epoch; fg=1;
  iv=sent<900; id=payload(sent);
  ordy=cycle%7!=0;
 end
 always @(posedge clk) if(run && rst) begin
  if(tr) begin
   rv<=tv; rd<=td; rs<=ts; re<=te; ue<=0;
   if(corrupt && tv && ts==5 && inject==0) begin ue<=1; inject<=1; end
  end
  if(iv && ir) sent<=sent+1;
  if(ov && ordy) begin
   if(od!==payload(seen)) $fatal(1,"payload/order expected %0d got %0d",seen,od[31:0]);
   seen=seen+1;
  end
  if(debt>DEPTH) $fatal(1,"retained overflow");
  if(fault) $fatal(1,"unexpected fault");
 end
 task tick; begin @(posedge clk); #1; end endtask
 task reset_link; begin
  run=0; @(negedge clk); rst=0; iv=0; rv=0; fv=0; ue=0; ordy=1;
  tick; @(negedge clk); rst=1; tick;
 end endtask
 integer k;
 initial begin
  reset_link; run=1;
  for(k=0;k<3000 && seen<900;k=k+1) tick;
  run=0; iv=0;rv=0;
  if(seen!=900 || retries!=0) $fatal(1,"faultfree delivery");
  $display("PASS full551 payload, pressure, ringwrap, faultfree0replay");
  reset_link; seen=0; sent=0; cycle=0; inject=0; corrupt=1; run=1;
  for(k=0;k<10000 && seen<900;k=k+1) tick;
  run=0; iv=0;rv=0;
  if(seen!=900 || retries==0) $fatal(1,"UE replay delivery seen%0d retries%0d",seen,retries);
  $display("PASS UE NAK replay full551");
  // Reset discards old-session frames and feedback, including NAK.
  reset_link; epoch=2; rv=1; rs=0; re=1; rd=payload(0); fv=1; fs=7; fn=1;fe=1;
  tick;
  if(ov || fault || ack!=0 || debt!=0) $fatal(1,"stale session reset");
  rv=0;fv=0;
  // Retain debt; duplicate/stale/corrupt ACK must not free data.
  @(negedge clk); iv=1; id=payload(0); tick; @(negedge clk);iv=0;
  fv=1;fe=2;fs=0;fn=0; tick;
  if(debt!=1) $fatal(1,"duplicate ACK changed debt");
  fs={SW{1'b1}}; tick; if(fault || debt!=1) $fatal(1,"stale ACK");
  fs=1;fg=0;tick; if(debt!=1) $fatal(1,"corrupt ACK");
  fg=1; fs=1;tick; if(debt!=0) $fatal(1,"good ACK");
  $display("PASS reset session, duplicate/stale/corrupt ACK");
  // ACK beyond retained window is terminal; no silent reclamation.
  fs=3;tick;if(!fault) $fatal(1,"future ACK accepted");
  reset_link; epoch=3;fv=0;
  @(negedge clk);iv=1;id=payload(0);tick;@(negedge clk);iv=0;
  for(k=0;k<ATO*5 && !fault;k=k+1) tick;
  if(!fault || debt!=1 || tv) $fatal(1,"bounded timeout debt");
  $display("PASS bounded retry exhaustion retains owned debt");
  reset_link; epoch=4;
  // Full configured replay depth, not a reduced occupancy proxy.
  for(k=0;k<DEPTH;k=k+1) begin
   @(negedge clk); iv=1; id=payload(k); tick;
  end
  @(negedge clk);iv=1;id=payload(DEPTH);#1;
  if(ir || debt!=DEPTH) $fatal(1,"full replay must backpressure");
  tick; @(negedge clk);iv=0;
  if(debt!=DEPTH) $fatal(1,"full retained debt changed");
  fv=1;fg=1;fe=4;fs=0;fn=1;tick;
  if(retries!=1) $fatal(1,"first NAK must rewind");
  tick; tick;
  if(retries!=1) $fatal(1,"duplicate NAK rewound twice");
  fs={SW{1'b1}};tick;
  if(fault || retries!=1 || debt!=DEPTH) $fatal(1,"stale NAK");
  $display("PASS full configured replay%0d entries, duplicate/stale NAK",DEPTH);

  reset_link;epoch=5;
  @(negedge clk);iv=1;id=payload(0);tick;@(negedge clk);iv=0;repeat(3)tick;
  dut.u_storage.g_bank[0].g_macro[0].u_mem.arr[0][17]=~dut.u_storage.g_bank[0].g_macro[0].u_mem.arr[0][17];
  dut.u_storage.g_bank[0].g_macro[0].u_mem.arr[0][18]=~dut.u_storage.g_bank[0].g_macro[0].u_mem.arr[0][18];
  @(negedge clk);fv=1;fg=1;fe=5;fs=0;fn=1;tick;
  for(k=0;k<20 && !fault;k=k+1)begin tick;if(tv)$fatal(1,"poison replay escaped");end
  if(!fault || debt!=1 || tv)$fatal(1,"replay SRAM UE must fault with retained debt");
  $display("PASS replay SRAM double error faults before emission and retains debt");
  $display("PASS_ALL");$finish;
 end
 initial begin #500000;$fatal(1,"watchdog");end
endmodule
