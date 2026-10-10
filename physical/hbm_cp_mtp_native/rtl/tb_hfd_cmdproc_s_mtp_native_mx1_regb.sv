`timescale 1ns/1ps
// mtp-lead 2026-10-09: directed pin bench of the MX1 REGISTERED MTP boundary (REGB=1).  Transaction-level port of
// tb_hfd_cmdproc_s_mtp_native_mx1 (6adb6c001): every pin handshake is driven / observed at the pins with valid/ready
// (no fixed cycle offsets).  Covers the two orderings and the ownership path the system bench does not stress:
//   A. CP-result AM pulses during an in-flight command, the backend identity lines (not a completion) carrying the
//      command identity: all 6 must come out owned with their index (MUT 3 compares the stale completion FIFO head);
//   B. 12 emitted tokens with the host stalled (8 in the queue + 2 in the host-record pin FIFO + 2 in the emit pin
//      FIFO), native done right after the 12th; the host then reads records slowly (1 in 4 cycles): it must get
//      all 12 in order and the done only after the last (MUT 1 loses the 2 emit-FIFO beats; MUT 2 shows done
//      while a record is still valid at the pins).  (MUT 3 is NOT a mutant here: ot_sc_pfifo loads its free slot
//      every cycle, so an empty completion FIFO's head equals the identity lines one cycle late, like the flops.)
//   C. owned completion ACK (t_mtp[83] one pulse), drained after done, wrong-job completion after a drained reset
//      raises identity fault + sticky abort.
//   R. HGI ARGMAX dispatch relay (x_hgi_argmax_rec -> t_hgi_argmax, f_hgi_argmax -> x_hgi_argmax_ret): a model
//      sequencer (valid held until ready) sends 4 records back to back to a model unit (ready = idle, busy 7 cycles,
//      then a done pulse): the unit must take all 4 in order exactly once and the sequencer see 4 done pulses
//      (MUT 3, the relay popping without the unit's ready, loses records).
module tb_hfd_cmdproc_s_mtp_native_mx1_regb #(parameter integer MUT=0, parameter integer N=12);
 reg clk=0;always #5 clk=~clk;
 reg rst=1;reg[516:0] mtp=0;wire[196:0] to_mtp;
 reg[215:0] host=0;wire[4:0] status;reg[178:0] provider=0;
 reg[72:0] backend=0;wire[270:0] request;wire[37:0] emitted;wire[42:0] addresses;
 reg[1:0] emit_accept=0;wire[99:0] emit_host;
 wire abort,drained;
 reg [17:0] am=0;
 wire[826:0] cSE,cSW;wire[63:0] suSE,suSW;wire[146:0] xl;wire[15:0] xt;
 hfd_cmdproc_s_mtp_native_mx1 #(.ENABLE_MTP(1),.REGB(1),.MUT(MUT)) dut(.cSE(cSE),.cSW(cSW),.ck(clk),.rst(rst),
 .f_loader(341'b0),.f_router(64'b0),.t_su_SE(suSE),.t_su_SW(suSW),.xb(16'b0),.xl(xl),.xt(xt),
 .f_mtp(mtp),.t_mtp(to_mtp),.f_host(host),.t_host(status),.f_provider(provider),
 .t_emit(emitted),.t_provider(addresses),.f_emit_host(emit_accept),.t_emit_host(emit_host),
 .t_abort(abort),.t_drained(drained),
 .f_am(am),
 .f_backend(backend),.t_backend(request),
 .x_hgi_argmax_rec(xrec),.x_hgi_argmax_ret(xret),.t_hgi_argmax(trec),.f_hgi_argmax(fret));
 // ---- R: model sequencer / model ARGMAX unit around the dispatch relay
 reg [682:0] xrec=0;wire [2:0] xret;wire [682:0] trec;
 reg u_rdy=1;reg u_done=0;integer u_busy=0,u_got=0,s_done=0;reg [2:0] fret_r=3'b001;wire [2:0] fret={1'b0,u_done,u_rdy};
 always @(posedge clk) if(rst) begin u_rdy<=1;u_done<=0;u_busy=0; end else begin
  u_done<=0;
  if(trec[0]&&u_rdy)begin
   if(trec[682:1]!=={681'(1000+u_got),1'b1})fail("argmax record order/content through the relay");
   u_got=u_got+1;u_rdy<=0;u_busy=7;
  end else if(u_busy>0)begin u_busy=u_busy-1;if(u_busy==0)begin u_done<=1;u_rdy<=1;end end
  if(xret[1])s_done=s_done+1;
  if(xret[2])fail("argmax relay fault");
 end
 task fail(input[511:0] msg);begin $display("FAIL %0s",msg);$fatal(1);end endtask
 integer i,n,guard,owned_am=0,acks=0,recs=0,emit_beats=0;reg seen_done=0;
 // monitors sample at the posedge (pre-edge values: pins are flops / AND-OR of flops; bench drives at negedges)
 always @(posedge clk) if(!rst) begin
  if(to_mtp[179])begin
   if(to_mtp[180+:17]!==17'h1ffff-owned_am)fail("owned AM index");
   owned_am=owned_am+1;
  end
  if(to_mtp[83])acks=acks+1;
  if(emitted[0])emit_beats=emit_beats+1;
 end
 // host side consumer of records / done (enabled by emit_accept): a transfer is valid && ready at the posedge
 always @(posedge clk) if(!rst) begin
  if(emit_host[74]&&emit_host[0])fail("host done visible while a record is pending");
  if(emit_host[0]&&emit_accept[0])begin
   if(seen_done)fail("record after host done");
   if(emit_host[1+:17]!==17'h1ffff-recs||emit_host[18+:20]!==recs||emit_host[38+:32]!==32'h12345678||emit_host[70+:4]!==15)
    fail("finite host record identity/order");
   recs=recs+1;
  end
  if(emit_host[74]&&emit_accept[1])begin if(recs!=N)fail("host done before all records");seen_done=1;end
 end
 // valid/ready helpers: valid is set in the low phase; ready is a flop (stable in the low phase), so the helper returns
 // in the low phase before the accepting posedge; the caller then waits one negedge (the transfer) and drops valid
 task wait_ready_host;begin guard=0;while(!status[0])begin @(negedge clk);guard=guard+1;if(guard>200)fail("job ready timeout");end end endtask
 task wait_ready_emit;begin guard=0;while(!to_mtp[139])begin @(negedge clk);guard=guard+1;if(guard>200)fail("emit ready timeout");end end endtask
 task wait_ready_cmd;begin guard=0;while(!to_mtp[82])begin @(negedge clk);guard=guard+1;if(guard>200)fail("cmd ready timeout");end end endtask
 task wait_ready_cpl;begin guard=0;while(!request[270])begin @(negedge clk);guard=guard+1;if(guard>200)fail("cpl ready timeout");end end endtask
 task wait_cycles(input integer k);begin repeat(k)@(negedge clk);end endtask
 task wait_until_active;begin guard=0;while(!status[1])begin @(negedge clk);guard=guard+1;if(guard>200)fail("not active");end end endtask
 initial begin
  repeat(3)@(negedge clk);if(status[0])fail("ready during reset");
  @(negedge clk);rst=0;
  // ---- R: 4 dispatch records through the relay (valid held until the registered ready is seen at a posedge)
  for(i=0;i<4;i=i+1)begin
   xrec={681'(1000+i),1'b1,1'b1};
   guard=0;while(!xret[0])begin @(negedge clk);guard=guard+1;if(guard>200)fail("dispatch ready timeout");end
   @(negedge clk);
  end
  xrec=0;
  guard=0;while(s_done<4)begin @(negedge clk);guard=guard+1;if(guard>400)fail("dispatch done pulses missing");end
  if(u_got!=4)fail("unit records != 4");
  // ---- job 1 admission
  backend[71]=1;backend[0]=1;
  host[0]=1;host[1+:32]=32'h12345678;host[33+:4]=4'hf;
  host[37+1+:4]=4;host[37+140]=1;host[37+141+:17]=17'h1ffff;host[37+158+:21]=21'd1048575;
  wait_ready_host();@(negedge clk);host[0]=0;
  wait_until_active();
  // ---- A: one command, held identity, 6 CP-result pulses, owned completion
  mtp[83+:4]=4'hb;mtp[87+:8]=8'ha5;mtp[95+:4]=8;mtp[99+:32]=32'h8000abcd;
  mtp[131+:17]=17'h1ffff;mtp[148+:136]=136'h0123456789abcdef0123456789abcdef01;
  mtp[82]=1;wait_ready_cmd();@(negedge clk);mtp[82]=0;
  guard=0;while(!request[0])begin @(negedge clk);guard=guard+1;if(guard>50)fail("command not issued");end
  if(request[1+:201]!=={136'h0123456789abcdef0123456789abcdef01,17'h1ffff,32'h8000abcd,4'd8,8'ha5,4'hb})fail("command field loss");
  if(request[202+:32]!==32'h12345678||request[234+:4]!==15||request[238+:32]!==0)fail("command identity loss");
  @(negedge clk);   // backend[0]=1: taken at the posedge above
  wait_cycles(3);
  if(!status[2])fail("not in flight");
  backend[2+:32]=32'h12345678;backend[34+:4]=15;backend[38+:32]=0;   // identity lines of the in-flight command
  wait_cycles(2);
  for(i=0;i<6;i=i+1)begin am={17'(17'h1ffff-i),1'b1};@(negedge clk);am=0;@(negedge clk);end
  wait_cycles(6);
  if(owned_am!=6)fail("owned CP-result pulses != 6");
  if(status[3]||status[4]||abort)fail("AM ownership fault");
  backend[1]=1;wait_ready_cpl();@(negedge clk);backend[1]=0;
  wait_cycles(6);
  if(acks!=1)fail("completion ACK not exactly one pulse");
  if(status[4]||status[2])fail("owned completion");
  // ---- B: 10 emits with the host stalled, native done right after the 10th
  for(i=0;i<N;i=i+1)begin
   mtp[43]=1;mtp[44+:17]=17'h1ffff-i;mtp[61+:20]=i;wait_ready_emit();@(negedge clk);
  end
  mtp[43]=0;mtp[81]=1;mtp[514+:3]=1;
  wait_cycles(12);
  if(emit_host[74])fail("done visible while records wait");
  emit_accept[1]=1;
  guard=0;while(!seen_done)begin emit_accept[0]=(guard%4==0);@(negedge clk);guard=guard+1;if(guard>600)fail("host done never came");end
  if(recs!=N)fail("host records != N");
  if(emit_host[78+:21]!==N)fail("accepted count");
  if(emit_beats!=N)fail("t_emit accepted beats != N");
  emit_accept=0;
  wait_cycles(6);
  if(!drained||status[0])fail("held native done drain/admit");
  // ---- C: drained reset, job 2, wrong-job completion
  @(negedge clk);rst=1;mtp=0;host=0;backend=0;am=0;wait_cycles(4);
  if(status[0]||drained)fail("reset handshake");
  @(negedge clk);rst=0;backend[71]=1;backend[0]=1;
  host[0]=1;host[1+:32]=32'h12345680;host[33+:4]=13;wait_ready_host();@(negedge clk);host[0]=0;
  wait_until_active();
  mtp[82]=1;wait_ready_cmd();@(negedge clk);mtp[82]=0;wait_cycles(4);
  backend[2+:32]=32'h12345679;backend[34+:4]=13;backend[38+:32]=0;
  backend[1]=1;wait_ready_cpl();@(negedge clk);backend[1]=0;
  wait_cycles(4);
  if(!status[3]||!status[4])fail("wrong job completion accepted");
  if(!abort||status[0])fail("cross abort not sticky");
  $display("PASS MX1 REGB pins argmax dispatch relay 4/4, owned AM 6/6, %0d tokens + done ordered behind both pin FIFOs, owned ACK, drained reset, wrong-job rejection",N);
  $finish;
 end
endmodule
