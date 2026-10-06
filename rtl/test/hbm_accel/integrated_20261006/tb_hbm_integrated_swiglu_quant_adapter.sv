`timescale 1ns/1ps
// Boundary golden, not a replacement numerical gate. Compile with the explicit
// port-probe producer in the runner, never with both probe and production RTL.
module tb_hbm_integrated_swiglu_quant_adapter;
 localparam N=1024;
 reg clk=0;always #5 clk=~clk;
 reg por_n=0,permit=0,reserved=0,iv=0,warm=0;
 reg [72:0] frame={20'hc1234,17'h12345,4'ha,32'hdeadbeef};
 reg [7:0] index=8'h83;
 reg [31:0] lim=32'h41234567;
 reg [4*N*32-1:0] operands=0;
 wire ir,qv,fault;wire [72:0] qframe;wire [7:0] qi;
 wire [8*N-1:0] qc;wire [10*N/32-1:0] qe;wire [16*N-1:0] qy;
 wire off_ir,off_qv,off_fault;wire [72:0] off_frame;wire [7:0] off_i;
 wire [8*N-1:0] off_c;wire [10*N/32-1:0] off_e;wire [16*N-1:0] off_y;
 ot_hbm_integrated_swiglu_quant_adapter #(.ENABLE(1),.N(N)) dut(
  .clk(clk),.por_n(por_n),.launch_permit(permit&&!warm),.landing_reserved(reserved),
  .in_valid(iv),.in_ready(ir),.held_frame(frame),.landing_index(index),
  .lim(lim),.operands(operands),.q_valid(qv),.q_frame(qframe),.q_index(qi),
  .q_codes(qc),.q_exp(qe),.q_bf16(qy),.fault(fault));
 ot_hbm_integrated_swiglu_quant_adapter #(.N(N)) off(
  .clk(clk),.por_n(por_n),.launch_permit(1'b1),.landing_reserved(1'b1),
  .in_valid(iv),.in_ready(off_ir),.held_frame(frame),.landing_index(index),
  .lim(lim),.operands(operands),.q_valid(off_qv),.q_frame(off_frame),.q_index(off_i),
  .q_codes(off_c),.q_exp(off_e),.q_bf16(off_y),.fault(off_fault));
 task tick;begin @(posedge clk);#1;end endtask
 task check_off;begin
  if({off_ir,off_qv,off_frame,off_i,off_c,off_e,off_y,off_fault}!==0)
   $fatal(1,"default OFF not inert");
 end endtask
 task check_packet(input bit want_fault);begin
  if(!qv||qframe!==frame||qi!==index||fault!==want_fault)
   $fatal(1,"publication owner/cursor/fault mismatch");
  for(integer k=0;k<N;k=k+1)begin
   if(qc[8*k+:8]!==((k*13+7)&255)) $fatal(1,"G/code lane %0d",k);
   if(qy[16*k+:16]!==((k*29+16'h5a37)&65535)) $fatal(1,"U/BF16 lane %0d",k);
  end
  for(integer b=0;b<N/32;b=b+1)
   if(qe[10*b+:10]!==((b*19+10'h205)&1023)) $fatal(1,"weight/exponent block %0d",b);
  check_off();
 end endtask
 initial begin
  for(integer k=0;k<N;k=k+1)begin
   operands[32*k+:32]=32'h31000000|((k*13+7)&255);
   operands[32*N+32*k+:32]=32'h42000000|((k*29+16'h5a37)&65535);
   operands[64*N+32*k+:32]=32'h53000000|(((k/32)*19+10'h205)&1023);
   operands[96*N+32*k+:32]=32'hffffffff;
  end
  tick();check_off();if(ir||qv||fault)$fatal(1,"POR launch/publication");
  @(negedge clk);por_n=1;iv=1;permit=1;
  tick();if(ir||qv)$fatal(1,"unreserved launch");
  @(negedge clk);reserved=1;permit=0;
  tick();if(ir||qv)$fatal(1,"vetoed launch");
  @(negedge clk);permit=1;
  tick();if(!ir||qv)$fatal(1,"accepted launch");
  if(dut.g_on.producer.g!==operands[0+:32*N] ||
     dut.g_on.producer.u!==operands[32*N+:32*N] ||
     dut.g_on.producer.w!==operands[64*N+:32*N] ||
     dut.g_on.producer.lim!==lim)
   $fatal(1,"actual source-port operands differ from boundary golden");
  // Once accepted, producer publication may not be vetoed by warm/permit.
  @(negedge clk);warm=1;permit=0;reserved=0;
  tick();check_packet(0);if(ir)$fatal(1,"warm admission");
  tick();if(qv)$fatal(1,"duplicate/new warm work");
  // Plane3 changes have no effect; full TOKEN17/POS20 and output cursor survive.
  @(negedge clk);warm=0;permit=1;reserved=1;lim=32'hc1234567;
  operands[96*N+:32*N]=0;frame=~frame;index=8'hfe;
  tick();@(negedge clk);iv=0;permit=0;
  tick();check_packet(1);tick();if(qv||fault)$fatal(1,"invalid fault/extra publication");
  // Cold POR flushes a pending producer; no warm reset was wired into engine.
  @(negedge clk);iv=1;permit=1;
  tick();@(negedge clk);por_n=0;
  tick();if(qv||ir||fault)$fatal(1,"POR did not flush");check_off();
  $display("PASS adapter boundary N1024: ordered planes, 32 scales, full73 owner/cursor, reservation/veto/warm drain, fault, masked plane, POR, defaultOFF");
  $finish;
 end
endmodule
