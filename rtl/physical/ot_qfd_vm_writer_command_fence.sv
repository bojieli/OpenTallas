// Distinct default-off command admission seam. Posted writes never pass through
// this helper: they must remain directly connected to memory. Existing accepted
// commands drain before lease admission; a lease request blocks NEW offers.
// launch_busy prevents a posted/OS-delayed ready from launching another command
// before the actual future-strobe certificate returns. writer_quiescent certifies future strobes; commit_pending/commit_v must observe
// actual memory, not writer idle or a guessed fixed drain timer.
module ot_qfd_vm_writer_command_fence #(
 parameter integer CMD_W=1, ENABLE=0, MUT=0
)(
 input wire clk,rst_n,
 input wire command_v,input wire [CMD_W-1:0] command_data,
 output wire command_ready,
 input wire writer_ready,writer_quiescent,
 output wire writer_go,output wire [CMD_W-1:0] writer_data,
 input wire lease_request,lease_accept,lease_release,
 input wire commit_pending,commit_v,posted_write_v,
 output wire lease_guard,output wire command_pending,
 output reg lease_active,output reg fault
);
 reg pending,launch_busy;reg [CMD_W-1:0] descriptor;
 assign command_pending=ENABLE&&pending;
 assign writer_go=ENABLE?rst_n&&pending&&writer_ready&&!launch_busy&&!lease_active:command_v;
 assign writer_data=(ENABLE&&MUT!=2)?descriptor:command_data;
 assign command_ready=!ENABLE||(rst_n&&(MUT==3||!lease_request)&&!lease_active&&(!pending||writer_go));
 assign lease_guard=ENABLE&&rst_n&&!lease_active&&!writer_go&&
  ((MUT==1)||(!pending&&!launch_busy&&writer_quiescent&&!commit_pending&&!commit_v));
 always @(posedge clk)begin
  if(!rst_n)begin pending<=0;launch_busy<=0;lease_active<=0;fault<=0;end
  else if(ENABLE)begin
   if(writer_go)begin pending<=0;launch_busy<=1;end
   else if(writer_quiescent)launch_busy<=0;
   if(command_v&&command_ready)begin pending<=1;descriptor<=command_data;end
   if(lease_accept)begin
    if(!lease_guard)fault<=1;
    else lease_active<=1;
   end
   if(lease_release)lease_active<=0;
   if(lease_active&&(writer_go||posted_write_v||commit_v))fault<=1;
  end
 end
endmodule
