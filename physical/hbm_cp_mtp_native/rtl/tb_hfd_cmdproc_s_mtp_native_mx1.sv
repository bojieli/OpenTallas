`timescale 1ns/1ps
module tb_hfd_cmdproc_s_mtp_native_mx1;
 reg clk=0;always #5 clk=~clk;
 reg rst=1;reg[516:0] mtp=0;wire[196:0] to_mtp;
 reg[215:0] host=0;wire[4:0] status;reg[178:0] provider=0;
 reg[72:0] backend=0;wire[270:0] request;wire[37:0] emitted;wire[42:0] addresses;
 reg[1:0] emit_accept=0;wire[99:0] emit_host;
 wire abort,drained;
 reg [17:0] am=0;
 wire[826:0] cSE,cSW;wire[63:0] suSE,suSW;wire[146:0] xl;wire[15:0] xt;
 hfd_cmdproc_s_mtp_native_mx1 #(.ENABLE_MTP(1)) dut(.cSE(cSE),.cSW(cSW),.ck(clk),.rst(rst),
 .f_loader(341'b0),.f_router(64'b0),.t_su_SE(suSE),.t_su_SW(suSW),.xb(16'b0),.xl(xl),.xt(xt),
 .f_mtp(mtp),.t_mtp(to_mtp),.f_host(host),.t_host(status),.f_provider(provider),
 .t_emit(emitted),.t_provider(addresses),.f_emit_host(emit_accept),.t_emit_host(emit_host),
 .t_abort(abort),.t_drained(drained),
 .f_am(am),
 .f_backend(backend),.t_backend(request));
 task tick;begin @(posedge clk);#1;end endtask
 task fail(input[255:0] msg);begin $display("FAIL %s",msg);$fatal(1);end endtask
 integer i;
 initial begin
  repeat(3)tick();@(negedge clk);rst=0;tick();
  if(status[0])fail("admitted nonquiescent backend");
  @(negedge clk);backend[71]=1;backend[0]=1;host[0]=1;host[1+:32]=32'h12345678;host[33+:4]=4'hf;
  host[37+1+:4]=4;host[37+140]=1;host[37+141+:17]=17'h1ffff;host[37+158+:21]=21'd1048575;
  tick();@(negedge clk);host[0]=0;backend[0]=0;provider[48+:17]=17'h1fffe;provider[65+:17]=17'h1ffff;
  provider[139]=1;mtp[0+:20]=20'habcde;mtp[20+:23]=23'h123456;
  mtp[82]=1;mtp[83+:4]=4'hb;mtp[87+:8]=8'ha5;mtp[95+:4]=8;mtp[99+:32]=32'h8000abcd;
  mtp[131+:17]=17'h1ffff;mtp[148+:136]=136'h0123456789abcdef0123456789abcdef01;
  for(i=0;i<8;i=i+1)begin
   mtp[43]=1;mtp[44+:17]=17'h1ffff-i;mtp[61+:20]=i;tick();
   if(emitted!==mtp[43+:38]||addresses!==mtp[0+:43])fail("native emit/provider field loss");
   if(!request[0]||status[2])fail("command not held under stall");
   @(negedge clk);
  end
  mtp[43]=0;
  if(to_mtp[139]||to_mtp[82])fail("full sink/command accepted");
  if(!request[0]||request[1+:201]!=={mtp[148+:136],mtp[131+:17],mtp[99+:32],mtp[95+:4],mtp[87+:8],mtp[83+:4]})fail("full command loss");
  if(request[202+:32]!==32'h12345678||request[234+:4]!==15)fail("command identity loss");
  backend[0]=1;tick();if(!status[2]||request[0])fail("real backend accept");
  // Actual captured backend identity remains stable across six CPRESULT pulses.
  @(negedge clk);backend[2+:32]=32'h12345678;backend[34+:4]=15;
  backend[38+:32]=0;
  for(i=0;i<6;i=i+1)begin
   am={17'(17'h1ffff-i),1'b1};#1;
   if(!to_mtp[179]||to_mtp[180+:17]!==17'h1ffff-i)fail("owned CPRESULT AM loss");
   tick();@(negedge clk);
  end
  am=0;
  @(negedge clk);mtp[82]=0;backend[0]=0;backend[1]=1;backend[2+:32]=32'h12345678;
  backend[34+:4]=15;backend[38+:32]=0;tick();
  if(status[4]||!to_mtp[83])fail("owned completion did not ACK");
  @(negedge clk);backend[1]=0;tick();if(to_mtp[83])fail("completion ACK not one cycle");
  @(negedge clk);mtp[81]=1;tick();if(emit_host[74])fail("done overtook tokens");
  @(negedge clk);emit_accept[0]=1;
  for(i=0;i<8;i=i+1)begin
   if(!emit_host[0]||emit_host[1+:17]!==17'h1ffff-i||emit_host[18+:20]!==i||emit_host[38+:32]!==32'h12345678||emit_host[70+:4]!==15)fail("finite host record identity");
   tick();@(negedge clk);
  end
  if(!emit_host[74]||emit_host[78+:21]!==8||status[0])fail("host completion/ownership");
  emit_accept[1]=1;tick();@(negedge clk);emit_accept=0;
  // S_DONE must remain high; job admission is blocked until reset.
  backend[0]=1;#1;if(!drained||status[0])fail("held native done drain/admit");
  @(negedge clk);rst=1;mtp=0;host=0;backend=0;
  repeat(3)tick();if(status[0]||drained)fail("reset handshake");
  @(negedge clk);rst=0;backend[71]=1;backend[0]=1;
  host[0]=1;host[1+:32]=32'h12345679;host[33+:4]=4'he;
  tick();@(negedge clk);host[0]=0;mtp[82]=1;
  backend[2+:32]=32'h12345679;backend[34+:4]=14;backend[38+:32]=0;
  tick();if(!status[2])fail("second drained-reset job accept");
  @(negedge clk);mtp[82]=0;backend[1]=1;
  tick();if(!to_mtp[83]||status[4])fail("second actual completion");
  @(negedge clk);backend[1]=0;mtp[81]=1;tick();
  @(negedge clk);emit_accept[1]=1;tick();#1;
  if(!drained||status[0])fail("second terminal drain");
  // Only after all queues/backend/native outputs drain, reset again.
  @(negedge clk);rst=1;mtp=0;backend=0;host=0;emit_accept=0;repeat(3)tick();
  @(negedge clk);rst=0;backend[71]=1;backend[0]=1;
  host[0]=1;host[1+:32]=32'h12345680;host[33+:4]=13;tick();
  @(negedge clk);host[0]=0;mtp[82]=1;tick();
  @(negedge clk);mtp[82]=0;backend[1]=1;
  backend[2+:32]=32'h12345679;backend[34+:4]=13;backend[38+:32]=0;
  tick();if(!status[3]||!status[4]||to_mtp[83])fail("wrong job completion accepted");
  tick();if(!abort||status[0])fail("cross abort not sticky");
  $display("PASS MX1 actual facade finite8 owned AM197/517 two drained-reset jobs wrong-job rejection");$finish;
 end
endmodule
