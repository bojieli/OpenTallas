`timescale 1ns/1ps
module tb_qfd_vm_writer_command_fence;
 parameter integer MUT=0;
 reg clk=0,rst_n=0,command_v=0,writer_ready=0,writer_quiescent=0;
 reg lease_request=0,lease_accept=0,lease_release=0,commit_pending=0,commit_v=0,posted_write_v=0;
 reg [7:0] command_data=0;
 wire command_ready,writer_go,lease_guard,command_pending,lease_active,fault;wire [7:0] writer_data;
 ot_qfd_vm_writer_command_fence #(.CMD_W(8),.ENABLE(1),.MUT(MUT)) dut(.*);
 task step;begin #2;clk=1;#2;clk=0;#2;end endtask
 initial begin
  step();rst_n=1;command_v=1;command_data=8'ha5;step();command_v=0;
  lease_request=1;writer_quiescent=1;command_data=8'h5a;#1;
  if(!command_pending||lease_guard||command_ready||writer_go)$fatal(1,"queued command bypassed fence");
  step();writer_ready=1;#1;
  if(!writer_go||writer_data!==8'ha5||lease_guard)$fatal(1,"accepted descriptor not retained");
  step();writer_quiescent=0;#1;if(lease_guard||command_ready)$fatal(1,"future posted writer/new command fence ignored");
  posted_write_v=1;commit_pending=1;step();posted_write_v=0;writer_quiescent=1;#1;
  if(lease_guard)$fatal(1,"pending posted commit ignored");
  commit_pending=0;commit_v=1;step();#1;if(lease_guard)$fatal(1,"sameedge commit ignored");
  commit_v=0;#1;if(!lease_guard)$fatal(1,"drained lease denied");
  lease_accept=1;step();lease_accept=0;lease_request=0;command_v=1;#1;
  if(command_ready||writer_go||!lease_active||fault)$fatal(1,"new command admitted during lease");
  repeat(5)step();command_v=0;lease_release=1;step();lease_release=0;
  if(!command_ready||lease_active||fault)$fatal(1,"release blocked");
  rst_n=0;step();rst_n=1;writer_quiescent=0;command_data=8'h11;command_v=1;step();
  command_data=8'h22;step();command_v=0;
  // External posted ready stays high while the first command is still busy.
  if(writer_go||!command_pending)$fatal(1,"stale posted ready launched second command");
  repeat(5)begin step();if(writer_go)$fatal(1,"busy launch guard lost");end
  writer_quiescent=1;step();writer_quiescent=0;
  if(!writer_go||writer_data!==8'h22)$fatal(1,"old accepted queue did not drain after certificate");
  step();
  $display("PASS queued descriptor, new-command fence, actual posted commit admission and lease release");$finish;
 end
endmodule
