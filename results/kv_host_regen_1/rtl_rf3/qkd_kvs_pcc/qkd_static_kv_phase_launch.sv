`timescale 1ns/1fs
// Actual fixed-phase control transport. There is no ready/credit/wait input.
// Source pin capture -> toggle register is1 core edge. Destination captures the
// toggle through2 FF then publishes the pulse/held metadata on its third HBM
// edge. The first HBM edge must be strictly after the toggle launch and inside
// the compiler's PHYSICALLY PROVED setup/hold phase window. A bad phase or
// overwritten/too-close packet faults and aborts; it never moves a launch.
//
// Core625u/HBM768u (u=4/3ps). q is time until the next HBM edge at this core edge;
// q=PH0 at the first edge with internal rn active, exactly the landing calendar
// phase-origin convention. The real die must prove that reset/PLL/phi-R origin.
// PH0 and SAFE limits must come from actual clock/pin/relay profiles. Default
// zero limits are deliberately illegal, not an unchecked production budget.
module qkd_static_kv_phase_launch #(
 parameter integer PH0=0, SAFE_LOW_U=0, SAFE_HIGH_U=0, META_HOLD_CORE=0, MUT=0,
 parameter integer SAME_CLOCK=0
)(
 input wire ck,rst_n,hck,hrst_n,
 input wire ctrl_go,kgo,vgo,input wire[13:0]ctx_t,input wire[15:0]epoch,input wire[5:0]layer,
 output reg ctrl_go_h,kgo_h,vgo_h,output reg[13:0]ctx_t_h,output reg[15:0]epoch_h,output reg[5:0]layer_h,
 output reg fault_core,fault_hbm,output reg idle_core,idle_hbm
);
 initial begin
  if((!SAME_CLOCK && (PH0<0||PH0>=768||SAFE_LOW_U<=0||SAFE_HIGH_U>=768||SAFE_HIGH_U<SAFE_LOW_U))||META_HOLD_CORE<6||META_HOLD_CORE>255)
   $fatal(1,"actual phase profile and held-metadata budget required");
 end
 // Decision14: both domains use the same clock tree. Keep the transport
 // pipeline/metadata contract; the ratio-phase state has no meaning here.
 wire dst_ck = SAME_CLOCK ? ck : hck;
 (* keep *)reg rn,hr;
 always @(posedge ck)rn<=rst_n;
 always @(posedge dst_ck)hr<=hrst_n;
 reg[2:0]go_q,tag;reg[35:0]meta_q,held;
 reg[9:0]q;reg[7:0]hold_q;reg[7:0]lane_hold[0:2];
 wire[9:0]next_gap=(q==0)?10'd768:q;
 wire phase_ok=SAME_CLOCK||(next_gap>=10'(SAFE_LOW_U)&&next_gap<=10'(SAFE_HIGH_U));
 reg gap_bad;integer i;
 always @*begin
  gap_bad=0;for(integer k=0;k<3;k=k+1)if(go_q[k]&&lane_hold[k]!=0)gap_bad=1;
 end
 always @(posedge ck)meta_q<={ctx_t,epoch,layer};
 always @(posedge ck or negedge rn)begin
  if(!rn)begin
   go_q<=0;tag<=0;held<=0;q<=10'(PH0);hold_q<=0;fault_core<=0;idle_core<=0;
   for(i=0;i<3;i=i+1)lane_hold[i]<=0;
  end else begin
   go_q<={vgo,kgo,ctrl_go};
   q<=SAME_CLOCK ? 10'd0 : ((q>=625)?q-10'd625:q+10'd143);
   if(hold_q!=0)hold_q<=hold_q-1'b1;
   for(i=0;i<3;i=i+1)if(lane_hold[i]!=0)lane_hold[i]<=lane_hold[i]-1'b1;
   idle_core<=hold_q==0&&go_q==0&&!ctrl_go&&!kgo&&!vgo;
   if(|go_q)begin
    if((!phase_ok&&MUT!=2)||gap_bad||(hold_q!=0&&held!=meta_q))fault_core<=1;
    else if(!fault_core)begin
     tag<=tag^go_q;held<=meta_q;hold_q<=8'(META_HOLD_CORE);
     for(i=0;i<3;i=i+1)if(go_q[i])lane_hold[i]<=8'(META_HOLD_CORE);
    end
   end
  end
 end
 (* async_reg="true" *)reg[2:0]tag_meta,tag_sync;
 reg[2:0]seen;
 wire[2:0]observed=(MUT==1)?tag_meta:tag_sync;
 wire[2:0]events=observed^seen;
 always @(posedge dst_ck or negedge hr)begin
  if(!hr)begin
   tag_meta<=0;tag_sync<=0;seen<=0;ctrl_go_h<=0;kgo_h<=0;vgo_h<=0;
   ctx_t_h<=0;epoch_h<=0;layer_h<=0;fault_hbm<=0;idle_hbm<=0;
  end else begin
   tag_meta<=tag;tag_sync<=tag_meta;seen<=observed;
   {vgo_h,kgo_h,ctrl_go_h}<=events;
   if(|events)begin
    {ctx_t_h,epoch_h,layer_h}<=held^((MUT==3)?36'd1:36'd0);
    if(held[35:22]<1||held[35:22]>8192||held[5:0]>35)fault_hbm<=1;
   end
   idle_hbm<=tag_meta==tag_sync&&tag_sync==seen&&{vgo_h,kgo_h,ctrl_go_h}==0;
  end
 end
endmodule
