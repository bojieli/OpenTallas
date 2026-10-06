`timescale 1ns/1ps
// Existing CP LAUNCH -> actual shared SU lease. No second borrower/GO authority.
// Four protected control/frame/PC rows, within the combined bridge allowance.
module ot_hbm_integrated_su_cp_bind #(parameter integer ENABLE=0)(
 input wire clk,por_n,input wire [1:0] launch_v,input wire [31:0] launch_pc,
 input wire [31:0] cp_job,input wire [3:0] cp_gen,
 input wire [16:0] launch_token,input wire [19:0] launch_pos,
 output wire [1:0] native_launch,
 output wire lease_v,input wire lease_granted,
 output wire release_v,input wire release_r,
 input wire exec_done,exec_fault,input wire [3:0] retired_original_ops,
 input wire shared_fault,
 output wire owned,pending,quiet,selected,done,fault,
 output wire [31:0] selected_pc,held_job,output wire [3:0] held_gen,
 output wire [16:0] held_token,output wire [19:0] held_pos
);
 import ot_gpu_w6_secded_pkg::*;
 generate if(ENABLE==0)begin:off
 assign native_launch=launch_v;assign lease_v=0;assign release_v=0;
 assign owned=0;assign pending=0;assign quiet=1;assign selected=0;
 assign done=0;assign fault=0;assign selected_pc=0;assign held_job=0;
 assign held_gen=0;assign held_token=0;assign held_pos=0;
 end else begin:on
 localparam [2:0] IDLE=0,PENDING=1,ACTIVE=2,RELEASE=3,CLEANUP=4,DONE=5,FAIL=7;
 reg [71:0] control,pc_code,frame_lo,frame_hi;
 wire [65:0] c=decode64(control),p=decode64(pc_code),lo=decode64(frame_lo),hi=decode64(frame_hi);
 wire bad=c[65]||p[65]||lo[65]||hi[65];wire [2:0] state=c[2:0];
 wire [127:0] frame={hi[63:0],lo[63:0]};
 assign held_job=frame[31:0];assign held_gen=frame[35:32];
 assign held_token=frame[52:36];assign held_pos=frame[72:53];assign selected_pc=p[31:0];
 wire entry=launch_pc==32'h80000004||launch_pc==32'hc0000004;
 wire source_frame=cp_job==held_job&&cp_gen==held_gen&&launch_token==held_token&&launch_pos==held_pos;
 assign selected=state!=IDLE||(entry&&|launch_v);
 assign native_launch=entry?2'b0:launch_v;
 assign fault=bad||state==FAIL||exec_fault||shared_fault;
 assign pending=state==PENDING;
 assign lease_v=pending&&!fault;
 // Actual shared grant stays the executor's owned input through its FINISHED.
 assign owned=lease_granted&&!fault;
 assign quiet=(state==IDLE||state==PENDING)&&!lease_granted&&!exec_fault&&!fault;
 assign release_v=state==RELEASE&&exec_done&&retired_original_ops==4&&!fault;
 // One CP done edge follows accepted release and actual executor cleanup.
 assign done=state==DONE&&!fault;
 reg [127:0] captured;
 always @(posedge clk or negedge por_n)begin
  if(!por_n)begin control<=encode64(0);pc_code<=encode64(0);frame_lo<=encode64(0);frame_hi<=encode64(0);end
  else if(fault||(state!=IDLE&&!source_frame)||
    (state!=IDLE&&state!=DONE&&|launch_v))control<=encode64(64'(FAIL));
  else case(state)
   IDLE:if(|launch_v&&entry)begin
    if(launch_v!=2'b01)control<=encode64(64'(FAIL));
    else begin
     captured={55'b0,launch_pos,launch_token,cp_gen,cp_job};
     frame_lo<=encode64(captured[63:0]);frame_hi<=encode64(captured[127:64]);
     pc_code<=encode64({32'b0,launch_pc});control<=encode64(64'(PENDING));
    end
   end
   PENDING:if(lease_granted)control<=encode64(64'(ACTIVE));
   ACTIVE:if(!lease_granted)control<=encode64(64'(FAIL));
    else if(exec_done)begin
     if(retired_original_ops!=4)control<=encode64(64'(FAIL));else control<=encode64(64'(RELEASE));
    end
   RELEASE:if(!lease_granted)control<=encode64(64'(FAIL));
    else if(release_v&&release_r)control<=encode64(64'(CLEANUP));
   CLEANUP:if(!lease_granted&&!exec_done)control<=encode64(64'(DONE));
   DONE:control<=encode64(64'(IDLE));
   default:control<=encode64(64'(FAIL));
  endcase
 end
 end endgenerate
endmodule
