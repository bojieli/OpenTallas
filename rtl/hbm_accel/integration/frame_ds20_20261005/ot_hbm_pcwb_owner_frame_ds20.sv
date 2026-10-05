`timescale 1ps/1fs
// Actual DS20 issuer context; no conversion into producer/transport/IRS IDs.
// Model: hbm_pcwb_frame_ds20_20261005/preedit_model.json, 68raw+144coded.
module ot_hbm_pcwb_owner_frame_ds20 #(parameter integer ENABLE=0,STACK=0)(
 input wire service_clk,por_n,owner_v,output wire owner_r,
 input wire [31:0] owner_job,input wire [3:0] owner_gen,input wire [19:0] owner_pos,
 input wire [6:0] rank,input wire [1:0] stack,
 input wire writes_fenced,all_drained,external_fault,bad_event,
 input wire row_attempt,input wire [19:0] row_pos,input wire [6:0] row_die,
 output wire row_association_matches,
 output wire owner_held,output wire [31:0] held_job,output wire [3:0] held_gen,
 output wire [19:0] held_pos,output wire [6:0] held_rank,output wire [1:0] held_stack,
 output wire fenced,owner_released,fault
);
 import ot_gpu_w6_secded_pkg::*;
 generate if(!ENABLE)begin:off
  assign owner_r=0;assign owner_held=0;assign held_job=0;assign held_gen=0;
  assign held_pos=0;assign held_rank=0;assign held_stack=0;assign fenced=0;
  assign owner_released=0;assign fault=0;
  assign row_association_matches=0;
 end else begin:on
  reg [67:0] q,n;reg [143:0] seal;reg code_bad;
  wire accept=owner_v&&owner_r;
  assign held_job=q[67:36];assign held_gen=q[35:32];assign held_pos=q[31:12];
  assign held_rank=q[11:5];assign held_stack=q[4:3];assign owner_held=q[2];
  assign fenced=q[1];assign fault=q[0]||code_bad;
  assign row_association_matches=owner_held&&(row_pos==held_pos)&&(row_die==held_rank);
  wire association_bad=row_attempt&&!row_association_matches;
  assign owner_r=!fault&&all_drained&&(!owner_held||fenced)&&(stack==2'(STACK));
  // Current debt-empty level, not an invented whole-producer completion event.
  // The enclosing issuer join must separately wait for actual step completion.
  assign owner_released=owner_held&&fenced&&all_drained&&!fault&&!bad_event&&!association_bad;
  always @* begin
   reg [127:0] pad;pad={60'b0,q};code_bad=0;
   for(integer w=0;w<2;w=w+1)begin
    reg [65:0] d;d=decode64(seal[w*72+:72]);
    if(d[65]||d[63:0]!=pad[w*64+:64])code_bad=1;
   end
  end
  always @* begin
   n=q;
   if(accept)n[67:2]={owner_job,owner_gen,owner_pos,rank,stack,1'b1};
   n[1]=owner_held&&writes_fenced&&!accept;
   n[0]=fault||external_fault||bad_event||association_bad;
  end
  // No warm/core reset input: the caller must use common POR or drain first.
  always @(posedge service_clk or negedge por_n)
   if(!por_n)begin q<=0;seal<=0;end
   else begin
    reg [127:0] pad;pad={60'b0,n};q<=n;
    for(integer w=0;w<2;w=w+1)seal[w*72+:72]<=encode64(pad[w*64+:64]);
   end
 end endgenerate
endmodule
