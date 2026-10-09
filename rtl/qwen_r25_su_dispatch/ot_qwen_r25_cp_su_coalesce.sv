`timescale 1ns/1ps
// AR-only interception of the source-assigned CP namespace0x53550000..05.
// Plain finite control; no mirrored control protection, leases or reset epochs.
// Native request/completion must be in this CP clock domain.
module ot_qwen_r25_cp_su_coalesce #(parameter integer ENABLE=0)(
 input wire clk,rst_n,
 input wire [31:0] cp_launch_v,input wire [63:0] cp_launch_pc,
 input wire [147:0] cp_launch_owner,
 output wire [31:0] sm_launch_v,output wire [63:0] sm_launch_pc,
 output wire [147:0] sm_launch_owner,
 input wire [31:0] sm_done,sm_fault,
 output wire [31:0] cp_done,cp_fault,
 output wire native_req_v,input wire native_req_rdy,
 output wire [31:0] native_req_pc,output wire [73:0] native_req_owner,
 input wire native_complete_v,output wire native_complete_rdy,
 input wire [73:0] native_complete_owner,input wire native_fault,
 output wire fault
);
 assign sm_launch_pc=cp_launch_pc;assign sm_launch_owner=cp_launch_owner;
 generate if(!ENABLE)begin:g_off
  assign sm_launch_v=cp_launch_v;assign cp_done=sm_done;assign cp_fault=sm_fault;
  assign native_req_v=0;assign native_req_pc=0;assign native_req_owner=0;
  assign native_complete_rdy=0;assign fault=0;
 end else begin:g_on
  reg [1:0] have=0;reg issued=0,failed=0;
  reg [15:0] masks[0:1];reg [31:0] entries[0:1];reg [73:0] owners[0:1];
  wire [1:0] reserved,known;
  for(genvar h=0;h<2;h=h+1)begin:g_half
   assign reserved[h]=cp_launch_pc[h*32+16+:16]==16'h5355;
   assign known[h]=reserved[h]&&cp_launch_pc[h*32+:16]<=16'd5;
   assign sm_launch_v[h*16+:16]=(!fault&&!reserved[h])?cp_launch_v[h*16+:16]:16'd0;
  end
  wire pair_match=owners[0]==owners[1]&&entries[0]==entries[1];
  wire [31:0] held_masks={have[1]?masks[1]:16'd0,have[0]?masks[0]:16'd0};
  assign fault=failed||native_fault;
  assign native_req_v=(&have)&&pair_match&&!issued&&!fault;
  assign native_req_pc=entries[0];assign native_req_owner=owners[0];
  assign native_complete_rdy=issued&&!fault&&native_complete_owner==owners[0];
  wire real_complete=native_complete_v&&native_complete_rdy;
  assign cp_done=!fault?((sm_done&~held_masks)|(real_complete?held_masks:32'd0)):32'd0;
  assign cp_fault=sm_fault|(native_fault?held_masks:32'd0);
  integer h;
  always @(posedge clk or negedge rst_n)begin
   if(!rst_n)begin
    have<=0;issued<=0;failed<=0;
    for(h=0;h<2;h=h+1)begin masks[h]<=0;entries[h]<=0;owners[h]<=0;end
   end else if(!failed)begin
    if(native_fault||((&have)&&!pair_match)||
       (native_complete_v&&(!issued||native_complete_owner!=owners[0])))failed<=1;
    else begin
     if(native_req_v&&native_req_rdy)issued<=1;
     if(real_complete)begin have<=0;issued<=0;end
     for(h=0;h<2;h=h+1)begin
      if((|cp_launch_v[h*16+:16])&&reserved[h])begin
       if(!known[h]||have[h]||issued)failed<=1;
       else begin
        have[h]<=1;masks[h]<=cp_launch_v[h*16+:16];
        entries[h]<=cp_launch_pc[h*32+:32];owners[h]<=cp_launch_owner[h*74+:74];
       end
      end
     end
    end
   end
  end
 end endgenerate
endmodule
