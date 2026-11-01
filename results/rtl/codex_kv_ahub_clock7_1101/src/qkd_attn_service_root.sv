`timescale 1ns/1ps
// KVJ-B 2026-10-17: qkd_attn_service_root -- the "fixed calendar control" block of
// ot_qwen_tp8_attention_native_service_w16 (identical text in the g3s2 copy) moved into its own module, so the split
// KV die has a producer for the PV pairs' start / context_len / epoch (pvw_0/1 'st', kv_expand.PV_OPEN) and for
// start_qk / ctx / ep / cal of the rest of the attention service.
//
// Behaviour is the moved block's, edge for edge (lockstep bench rtl/test/qwen_split/tb_qkd_attn_service_root_lockstep.sv
// against the verbatim extracted block, tools/qwen_attention_native/mk_service_root.py).  Two structural changes, both
// exact:
//  * the service compared age+1 against PV_START_AGE / END_AGE, which are combinational functions of the 176-bit
//    calendar (a 3-way 16-bit max and two adds in front of the compare).  The root registers both compare targets on the
//    accept edge from request_calendar (17-bit, so a target the 16-bit age can never reach stays unreachable) and the
//    per-edge path is one 17-bit equality.
//  * PV_LEAD: start_pv leaves the root PV_LEAD edges before PV_START_AGE, so that after the die's PV_LEAD registered
//    relay edges to pvw_0/1 it lands on the edge the service fired it (the compiler subtracts the fixed relay edges).
//    PV_LEAD=0 is the service.  With PV_LEAD>0 a calendar with PV_START_AGE <= PV_LEAD, or one whose END_AGE is not
//    after PV_START_AGE (the service would never fire start_pv; an early start would land after the token), cannot be
//    met and raises local_fault (never stretches the timeline).  ctx / ep are held from the accept edge to the next accept, so they ride the same relay.
// No credit, ready or completion signal moves any slot (static cycle schedule).
// KV-ATTNKIT 10-18: CAL_PIPE=1 (die knob OT_KV_ATTN_LAND; kit qkd_kvs_attn-g1 failed request_calendar -> end_t, ~25
// levels: a 3-way 16-bit max and two adds in one edge).  The calendar fields are piped one edge ahead of the accept:
// PV_START and max(P0, P1, R) are registered every edge from request_calendar, and the accept edge adds them.  Exact
// whenever request_calendar[175:112] is the same on the accept edge and the one before -- the programme's calendar is
// its static_ctl 'cal' register, loaded on 'load' >= 3 edges before any request; a moved calendar raises local_fault.
// MUT (diagnostic, bench only): 1 = start_pv one edge late, 2 = ctx = position (not position+1), 3 = CAL_PIPE without
// the moved-calendar check.
module qkd_attn_service_root #(
 parameter integer PV_LEAD=0,
 parameter integer CAL_PIPE=0,
 parameter integer MUT=0
)(
 input wire ck,rst_n,
 input wire request_valid,output wire request_ready,
 input wire [15:0] request_epoch,input wire [5:0] request_layer,
 input wire [17:0] request_position,input wire fused_program_capability,
 input wire [175:0] request_calendar,
 input wire q_valid,input wire [4:0] q_beat,output wire q_ready,
 output reg running,start_qk,start_pv,
 output reg [15:0] age,          // age 0 = the cycle in which start_qk is high
 output reg [15:0] ep,output reg [5:0] layer,output reg [13:0] ctx,
 output reg [175:0] cal,output reg [31:0] cycles,
 output reg local_fault,io_fault
);
 reg [6:0] boot_count;
 reg [16:0] pv_t,end_t;         // registered compare targets: fire when {0,age} == target
 assign request_ready=!running&&boot_count==80;
 wire q_window=running&&!start_qk&&age>=1&&age<=32;
 assign q_ready=q_window;
 // targets from the accepted calendar (fields: R [175:160], P1 [159:144], P0 [143:128], PV_START [127:112])
 wire [15:0] rq_pv=request_calendar[127:112],rq_p0=request_calendar[143:128];
 wire [15:0] rq_p1=request_calendar[159:144],rq_r=request_calendar[175:160];
 wire [15:0] rq_last=(rq_p0>rq_p1)?((rq_p0>rq_r)?rq_p0:rq_r):((rq_p1>rq_r)?rq_p1:rq_r);
 reg [15:0] cp_pv,cp_last;reg [63:0] cp_cal;            // CAL_PIPE: the fields one edge ahead of the accept
 always @(posedge ck)begin cp_pv<=rq_pv;cp_last<=rq_last;cp_cal<=request_calendar[175:112];end
 wire [15:0] u_pv=(CAL_PIPE!=0)?cp_pv:rq_pv,u_last=(CAL_PIPE!=0)?cp_last:rq_last;
 wire cal_moved=CAL_PIPE!=0&&MUT!=3&&cp_cal!=request_calendar[175:112];
 wire [15:0] rq_end_m1=u_pv+u_last+16'd48;              // END_AGE-1 = PV_START + LAST_CAPTURE + 16 + 33 - 1 (16-bit wrap)
 localparam integer PV_SUB=1+PV_LEAD-((MUT==1)?1:0);
 wire [16:0] rq_pv_t={1'b0,u_pv}-17'(PV_SUB);           // < 0 wraps above 16'hffff: never reached
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin boot_count<=0;running<=0;start_qk<=0;start_pv<=0;age<=0;ep<=0;layer<=0;ctx<=0;cal<=0;
   local_fault<=0;io_fault<=0;cycles<=0;pv_t<=17'h1ffff;end_t<=17'h1ffff;end
  else begin
   start_qk<=0;start_pv<=0;
   if(boot_count<80)boot_count<=boot_count+1'b1;
   if(running)begin age<=age+1'b1;cycles<=cycles+1;end
   if(running&&{1'b0,age}==pv_t)start_pv<=1;
   if(running&&{1'b0,age}==end_t)running<=0;
   if(request_valid&&!request_ready)io_fault<=1;
   if(q_valid!=q_window)io_fault<=1;
   if(q_window&&q_valid&&q_beat!=5'(age-1))io_fault<=1;
   if(request_valid&&request_ready)begin
    if(!fused_program_capability||request_position>8191)local_fault<=1;
    if(PV_LEAD>0&&(u_pv<=16'(PV_LEAD)||(rq_end_m1!=16'hffff&&u_pv>rq_end_m1)))local_fault<=1;
    if(cal_moved)local_fault<=1;
    ep<=request_epoch;layer<=request_layer;ctx<=(MUT==2)?14'(request_position):14'(request_position+1);
    cal<=request_calendar;pv_t<=rq_pv_t;end_t<={rq_end_m1==16'hffff,rq_end_m1};
    running<=1;start_qk<=1;age<=0;cycles<=0;
   end
  end
 end
endmodule
