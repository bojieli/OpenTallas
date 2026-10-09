// Source-selected native SM program dispatch; no SIMT64/690 reinterpretation.
// Model tools/dshbm_mtp_record_dispatch_model.py precedes this implementation.
// One installed kernel in this minimum component; actual allocator supplies PC.
// MX1: caller resets only after CP, owner, SM and publication drain together.
`timescale 1ns/1ps
`default_nettype none
module ot_hbm_native_mtp_smh_pc_dispatch_mx1 #(parameter integer ENABLE=0)(
 input wire clk,rst_n,
 input wire install_v,input wire [31:0] install_pc,install_program_base,
 input wire [32:0] install_program_limit,input wire [15:0] install_record_count,
 input wire install_payload_error,
 input wire launch_v,input wire [31:0] launch_pc,
 input wire [16:0] launch_token,input wire [19:0] launch_position,
 input wire [72:0] launch_owner,
 output wire run_v,input wire run_ready,
 output wire [31:0] program_base,output wire [32:0] program_limit,
 output wire [15:0] record_count,
 output wire [72:0] operand_owner,
 output wire [16:0] operand_token,output wire [19:0] operand_position,
 input wire owner_done,owner_fault,output wire owner_done_ready,
 output reg sm_done,sm_fault,output wire drained_ready
);
 localparam IDLE=0,SEND=1,WAIT=2,FAILED=3;
 reg [1:0] state;
 reg valid;reg [31:0] entry,base;reg [32:0] limit;reg [15:0] count;
 reg [72:0] owner;
 wire [32:0] installed_end={1'b0,install_program_base}+40*install_record_count;
 wire valid_install=!install_payload_error && install_program_base[1:0]==0 &&
  install_record_count>0 && install_record_count<=256 &&
  installed_end<=33'h100000000 && install_program_limit==installed_end;
 assign run_v=ENABLE && rst_n && state==SEND && !owner_fault;
 assign program_base=base;assign program_limit=limit;assign record_count=count;
 assign operand_owner=owner;
 assign operand_token=owner[52:36];assign operand_position=owner[72:53];
 assign owner_done_ready=ENABLE && rst_n && state==WAIT;
 assign drained_ready=ENABLE && rst_n && state==IDLE && !owner_done && !owner_fault;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin state<=IDLE;valid<=0;entry<=0;base<=0;limit<=0;count<=0;owner<=0;sm_done<=0;sm_fault<=0;end
  else if(ENABLE)begin
   sm_done<=0;
   if(install_v)begin
    if(state!=IDLE || launch_v || !valid_install)begin state<=FAILED;sm_fault<=1;end
    else begin entry<=install_pc;base<=install_program_base;limit<=install_program_limit;
     count<=install_record_count;valid<=1;end
   end else if(launch_v)begin
    if(state!=IDLE || !valid || launch_pc!=entry || owner_fault || owner_done ||
       launch_owner[52:36]!=launch_token || launch_owner[72:53]!=launch_position)begin
     state<=FAILED;sm_fault<=1;
    end else begin owner<=launch_owner;state<=SEND;end
   end else if(owner_fault || (owner_done && state!=WAIT))begin state<=FAILED;sm_fault<=1;end
   else case(state)
    SEND:if(run_v && run_ready)state<=WAIT;
    WAIT:if(owner_done && owner_done_ready)begin state<=IDLE;sm_done<=1;end
    default:begin end
   endcase
  end
 end
endmodule
`default_nettype wire
