`timescale 1ns/1ps
// Actual CP entry addresses are explicitly installed, never guessed from ROM PCs.
// Default off; p4 remains rejected until the real per-query lease provider binds.
module ot_qwen_r25_cp_native_launch #(parameter integer ENABLE=0, SLOTS=6)(
 input wire clk,rst_n,warm_abort,
 input wire map_v,output wire map_rdy,input wire [2:0] map_slot,
 input wire [1:0] map_checked,input wire [31:0] map_cp_pc,
 input wire [11:0] map_rom_pc,input wire [12:0] map_count,
 input wire req_v,output wire req_rdy,input wire [1:0] req_checked,
 input wire [31:0] req_cp_pc,input wire [73:0] req_owner,input wire [2:0] req_queries,
 input wire vm_ready,input wire [1:0] vm_checked,input wire [73:0] vm_owner,
 output wire launch_v,input wire launch_rdy,output wire [1:0] launch_checked,
 output wire [73:0] launch_owner,output wire [11:0] launch_pc,
 output wire [12:0] launch_count,output wire [19:0] launch_position,
 output wire [2:0] launch_queries,
 input wire native_finished_v,output wire native_finished_rdy,
 input wire [73:0] native_finished_owner,input wire native_fault,
 output wire complete_v,input wire complete_rdy,output wire [73:0] complete_owner,
 output wire fault
);
 import ot_gpu_w6_secded_pkg::*;
 generate if(!ENABLE)begin:g_off
  assign map_rdy=0;assign req_rdy=0;assign launch_v=0;assign launch_checked=0;
  assign launch_owner=0;assign launch_pc=0;assign launch_count=0;
  assign launch_position=0;assign launch_queries=0;assign native_finished_rdy=0;
  assign complete_v=0;assign complete_owner=0;assign fault=0;
 end else begin:g_on
  localparam IDLE=0,LOOKUP=1,LAUNCH=2,WAIT_FINISH=3,COMPLETE=4,FAILED=5;
  reg [71:0] maps[0:SLOTS-1],control,owner_lo,invocation,selection;
  wire [65:0] cd=decode64(control),od=decode64(owner_lo),id=decode64(invocation),sd=decode64(selection);
  wire [2:0] phase=cd[2:0];wire locked=cd[3];
  wire [73:0] held_owner={id[9:0],od[63:0]};
  wire [31:0] held_pc=id[41:10];wire [2:0] held_queries=id[44:42];
  wire [65:0] md[0:SLOTS-1];wire [SLOTS-1:0] mue;
  for(genvar k=0;k<SLOTS;k=k+1)begin:decode_map
   assign md[k]=decode64(maps[k]);assign mue[k]=md[k][65];
  end
  wire bad=cd[65]||od[65]||id[65]||sd[65]||(|mue);
  reg [3:0] match_count;reg [63:0] chosen;reg duplicate;
  integer j;
  always @*begin
   match_count=0;chosen=0;duplicate=0;
   for(integer k=0;k<SLOTS;k=k+1)begin
    if(md[k][57]&&md[k][31:0]==held_pc)begin match_count=match_count+1;chosen=md[k][63:0];end
    if(k!=map_slot&&md[k][57]&&md[k][31:0]==map_cp_pc)duplicate=1;
   end
  end
  assign fault=bad||phase==FAILED;
  assign map_rdy=phase==IDLE&&!locked&&!fault;
  assign req_rdy=phase==IDLE&&!map_v&&!fault;
  assign launch_v=phase==LAUNCH&&!fault;
  assign launch_checked=launch_v?2'b11:2'b00;
  assign launch_owner=held_owner;assign launch_pc=sd[43:32];
  assign launch_count=sd[56:44];assign launch_position=held_owner[73:54];
  assign launch_queries=held_queries;
  assign native_finished_rdy=phase==WAIT_FINISH&&!fault;
  assign complete_v=phase==COMPLETE&&!fault;assign complete_owner=held_owner;
  function automatic [71:0] state_seat(input [2:0] p,input l);
   state_seat=encode64({60'b0,l,p});
  endfunction
  always @(posedge clk or negedge rst_n)begin
   if(!rst_n)begin
    control<=state_seat(IDLE,0);owner_lo<=encode64(0);
    invocation<=encode64(0);selection<=encode64(0);
    for(j=0;j<SLOTS;j=j+1)maps[j]<=encode64(0);
   end else if(warm_abort||bad||native_fault)control<=state_seat(FAILED,locked);
   else if(phase!=FAILED)begin
    if(native_finished_v&&phase!=WAIT_FINISH)control<=state_seat(FAILED,locked);
    else case(phase)
     IDLE:begin
      if(map_v&&map_rdy)begin
       if(map_checked!=3||map_slot>=SLOTS||duplicate||map_count==0||
          ({1'b0,map_rom_pc}+map_count)>13'd4096)control<=state_seat(FAILED,locked);
       else maps[map_slot]<=encode64({6'b0,1'b1,map_count,map_rom_pc,map_cp_pc});
      end else if(req_v&&req_rdy)begin
       if(req_checked!=3||req_queries!=1||req_owner[53:36]>=18'd151936||
          req_owner[73:54]>=20'd8224||!vm_ready||vm_checked!=3||vm_owner!=req_owner)
        control<=state_seat(FAILED,1);
       else begin
        owner_lo<=encode64(req_owner[63:0]);
        invocation<=encode64({19'b0,req_queries,req_cp_pc,req_owner[73:64]});
        control<=state_seat(LOOKUP,1);
       end
      end
     end
     LOOKUP:begin
      if(match_count!=1)control<=state_seat(FAILED,locked);
      else begin selection<=encode64(chosen);control<=state_seat(LAUNCH,locked);end
     end
     LAUNCH:if(launch_v&&launch_rdy)control<=state_seat(WAIT_FINISH,locked);
     WAIT_FINISH:if(native_finished_v&&native_finished_rdy)begin
      if(native_finished_owner!=held_owner)control<=state_seat(FAILED,locked);
      else control<=state_seat(COMPLETE,locked);
     end
     COMPLETE:if(complete_v&&complete_rdy)control<=state_seat(IDLE,locked);
     default:control<=state_seat(FAILED,locked);
    endcase
   end
  end
 end endgenerate
endmodule
