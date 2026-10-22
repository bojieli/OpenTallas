`timescale 1ns/1ps
// Exact 75b9fe42b modern LOCAL32 helpers; only module names changed to
// coexist with main legacy DV definitions. No duplicate legacy wrapper.

module qfd_native59_dr_landing_local32 #(parameter integer LAND_EDGES=8,LOCAL32=0)(
 input wire ck,rst_n,
 input wire request_slot,input wire[58:0]request_tag59,
 input wire emit_v,input wire[4:0]emit_beat,input wire[58:0]emit_tag59,
 input wire visibility_slot,
 output reg vm_commit_v,output reg[4:0]vm_commit_beat,output reg[58:0]vm_commit_tag59,
 output wire complete,output reg fault,
 // R3e (QW-N59-6 10-20) opt-in same-edge publications (LOCAL32; 0 ignores / aliases): request_pub[k] == request_slot,
 // emit_beat_pub == emit_beat on every edge; vm_commit_beat_pub is a kept copy of vm_commit_beat.
 input wire[7:0]request_pub,input wire[4:0]emit_beat_pub,output wire[4:0]vm_commit_beat_pub,vm_commit_beat_pub2,
 input wire[4:0]emit_beat_pub2,output wire[4:0]vm_commit_beat_pub3,vm_commit_beat_pub4   // R3i
);
 reg active;reg[58:0]tag;reg[31:0]issued,covered;
 reg[LAND_EDGES-1:0]pending;reg[4:0]beat_pipe[0:LAND_EDGES-1];reg[58:0]tag_pipe[0:LAND_EDGES-1];
 integer i;
 wire[4:0]lb=beat_pipe[LAND_EDGES-1];
 assign complete=active&&(&covered)&&!fault;
 // R3e: kept copies of the last pipe stage (lb_c == beat_pipe[LAND_EDGES-1], pend_c[k] == pending[LAND_EDGES-1]: same D,
 // same reset) and of vm_commit_beat, so the commit capture (65 flops) and the covered decode each take their own driver.
 // R3f: groups of <= 16 enable bits (2 mapped loads per DFFE bit): request_pub [0..3] tag quarters, [4]/[5] issued
 // halves, [6]/[7] covered halves; pend_c [0..3] vm_commit_tag quarters, [4] vm_commit_v / beat, [5] covered decode.
 (* keep = "true" *) reg[4:0]lb_c,lb_c2;(* keep = "true" *) reg[5:0]pend_c;(* keep = "true" *) reg[4:0]vcb_c,vcb_c2,vcb_c3,vcb_c4;   // R3g/i
 wire[7:0]rp=LOCAL32?request_pub:{8{request_slot}};
 wire[4:0]ebp=LOCAL32?emit_beat_pub:emit_beat,lbc=LOCAL32?lb_c:lb;
 wire[5:0]pc=LOCAL32?pend_c:{6{pending[LAND_EDGES-1]}};
 assign vm_commit_beat_pub=LOCAL32?vcb_c:vm_commit_beat;
 assign vm_commit_beat_pub2=LOCAL32?vcb_c2:vm_commit_beat;
 assign vm_commit_beat_pub3=LOCAL32?vcb_c3:vm_commit_beat;assign vm_commit_beat_pub4=LOCAL32?vcb_c4:vm_commit_beat;
 wire[4:0]ebp2=LOCAL32?emit_beat_pub2:emit_beat;
 wire[4:0]lbc2=LOCAL32?lb_c2:lb;
 wire commit_bad=!active||request_slot||tag_pipe[LAND_EDGES-1]!=tag||covered[lb];
 always @(posedge ck or negedge rst_n)
  if(!rst_n)begin
   active<=0;tag<=0;issued<=0;covered<=0;pending<=0;vm_commit_v<=0;vm_commit_beat<=0;vm_commit_tag59<=0;fault<=0;
   for(i=0;i<LAND_EDGES;i=i+1)begin beat_pipe[i]<=0;tag_pipe[i]<=0;end
   lb_c<=0;lb_c2<=0;pend_c<=0;vcb_c<=0;vcb_c2<=0;vcb_c3<=0;vcb_c4<=0;
  end else begin
   vm_commit_v<=0;
   pending<={pending[LAND_EDGES-2:0],emit_v};
   beat_pipe[0]<=emit_beat;tag_pipe[0]<=emit_tag59;
   lb_c<=beat_pipe[LAND_EDGES-2];lb_c2<=beat_pipe[LAND_EDGES-2];pend_c<={6{pending[LAND_EDGES-2]}};
   for(i=1;i<LAND_EDGES;i=i+1)begin beat_pipe[i]<=beat_pipe[i-1];tag_pipe[i]<=tag_pipe[i-1];end
   if(request_slot)begin
    if((active&&!(&covered))||(|pending)||emit_v)fault<=1;
    active<=1;
   end
   if(rp[0])tag[14:0]<=request_tag59[14:0];
   if(rp[1])tag[29:15]<=request_tag59[29:15];
   if(rp[2])tag[44:30]<=request_tag59[44:30];
   if(rp[3])tag[58:45]<=request_tag59[58:45];
   if(rp[4])issued[15:0]<=0;
   if(rp[5])issued[31:16]<=0;
   if(rp[6])covered[15:0]<=0;
   if(rp[7])covered[31:16]<=0;
   if(emit_v)begin
    if(!active||request_slot||emit_tag59!=tag||(emit_beat[4]?issued[{1'b1,ebp2[3:0]}]:issued[{1'b0,emit_beat[3:0]}]))fault<=1;   // R3i: == issued[emit_beat]
    issued[ebp]<=1;
   end
   if(pending[LAND_EDGES-1]&&commit_bad)fault<=1;
   if(pc[5]&&!commit_bad)covered[lbc]<=1;
   if(pc[0]&&!commit_bad&&!fault)vm_commit_tag59[14:0]<=tag_pipe[LAND_EDGES-1][14:0];
   if(pc[1]&&!commit_bad&&!fault)vm_commit_tag59[29:15]<=tag_pipe[LAND_EDGES-1][29:15];
   if(pc[2]&&!commit_bad&&!fault)vm_commit_tag59[44:30]<=tag_pipe[LAND_EDGES-1][44:30];
   if(pc[3]&&!commit_bad&&!fault)vm_commit_tag59[58:45]<=tag_pipe[LAND_EDGES-1][58:45];
   if(pc[4]&&!commit_bad&&!fault)begin vm_commit_v<=1;vm_commit_beat<=lbc2;vcb_c<=lbc2;vcb_c2<=lbc2;vcb_c3<=lbc2;vcb_c4<=lbc2;end
   if(visibility_slot&&(!active||!(&issued)||!(&covered)||(|pending)))fault<=1;
  end
endmodule

module qfd_native59_command_context_mu_local32 #(parameter integer NU=4,LOCAL32=0)(
 input wire ck,rst_n,
 input wire host_epoch_valid,host_fused_capability,input wire [15:0] host_epoch,
 input wire [58:0] host_tag,input wire [1:0] host_generation,
 input wire context_v,input wire [5:0] context_stage,
 input wire [17:0] context_token,context_position,
 input wire [379:0] native_cmd,input wire [5:0] command_stage,
 input wire [17:0] command_token,command_position,
 input wire service_active,
 input wire [1:0] ctx_user,input wire [15:0] ctx_epoch,
 output wire begin_slot,output wire [58:0] begin_tag,
 output wire request_slot,output wire [58:0] request_tag,
 output wire [19:0] result_base_word,output reg fault,
 // R3e (QW-N59-6 10-20) opt-in: context_v_pub[k] == context_v on every edge (parent kept pin copies); the 59-bit
 // context_tag capture halves take their own copy.  Unconnected / zero ports leave the original (default 0 = off).
 input wire [3:0] context_v_pub
);
 wire[3:0]cvp=LOCAL32?context_v_pub:{4{context_v}};
 localparam [379:0] TEMPLATE=380'h0000003000001000001000c5f0000000000000000000000000100358000000000000000000000000080100000080401;
 reg valid,cap;reg [1:0] generation;reg [58:0] context_tag;reg [1:0] ctx_u;
 wire host0=ctx_user==2'd0;
 assign begin_slot=context_v;
 assign begin_tag={ctx_epoch,context_stage,context_token,context_position[12:0],6'd0};
 assign request_slot=native_cmd[0];
 assign request_tag={context_tag[58:43],command_stage,command_token,command_position[12:0],6'd0};
 assign result_base_word=native_cmd[299:280];
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin valid<=0;cap<=0;generation<=0;context_tag<=0;ctx_u<=0;fault<=0;end
  else begin
   if(context_v)begin
    if(host_tag[58:43]!=host_epoch||host_tag[42:37]!=0||host_tag[5:0]!=0||
       (host0&&(host_tag[36:19]!=context_token||host_tag[18:6]!=context_position||host_epoch[1:0]!=2'd0))||
       service_active||!host_epoch_valid||!host_fused_capability||(valid&&begin_tag==context_tag)||context_stage<1||context_stage>36||context_token>=151936||context_position>=8192)fault<=1;
    valid<=1;cap<=host_fused_capability;generation<=host_generation;ctx_u<=ctx_user;
   end
   if(cvp[0])context_tag[14:0]<=begin_tag[14:0];
   if(cvp[1])context_tag[29:15]<=begin_tag[29:15];
   if(cvp[2])context_tag[44:30]<=begin_tag[44:30];
   if(cvp[3])context_tag[58:45]<=begin_tag[58:45];
   if(request_slot)begin
    if(host_tag[58:43]!=host_epoch||host_tag[42:37]!=0||host_tag[5:0]!=0||
       (ctx_u==2'd0&&(host_tag[36:19]!=context_tag[36:19]||host_tag[18:6]!=context_tag[18:6]||host_epoch!=context_tag[58:43]))||
       ctx_user!=ctx_u||host_generation!=generation||!valid||context_v||!host_epoch_valid||!cap||!host_fused_capability||request_tag!=context_tag||command_position>=8192||native_cmd!=TEMPLATE)fault<=1;
   end
  end
 end
 initial if(NU<2||NU>4)$fatal(1,"qfd_native59_command_context_mu_local32: NU %0d outside 2..4 (NU 1 binds qfd_native59_command_context)",NU);
endmodule
