`default_nettype none
// PREP actual CW308 context before privateCOPY fill, with STATIC admission at
// issue_at-2. No ready/wait. The original issue_at==cmdcycle+2 case bypasses
// storage to preserve already-filled-window command timing. Otherwise cmd308
// is held; consumer dates stay the original absolute CP dates. Caller must
// finish real fill before that dated admission/step; a late window faults in
// the actual consumer. COPY context lasts through actual VM completion.
module ot_hbm_static_load_dated_cmd_hold(
 input wire clk,rst_n,cmd_v_i,input wire[307:0]cmd_i,input wire[31:0]cycle_i,
 input wire consumer_done_i,consumer_fault_i,
 output wire consumer_cmd_v_o,output wire[307:0]consumer_cmd_o,
 output wire context_v_o,output wire[307:0]context_cmd_o,
 output wire busy_o,output reg fault_o
);
 reg active,waiting;reg[307:0]held;reg[31:0]last_cycle;
 wire[226:0]mv=cmd_i[290:64];
 wire bad=mv[1:0]!=0||mv[94:93]!=1||mv[205:186]!=1||mv[226:206]==0||
          ($signed(cmd_i[31:0]-cycle_i)<2)||($signed(cmd_i[63:32]-cmd_i[31:0])<=0);
 wire accept=cmd_v_i&&!active&&!fault_o&&!consumer_fault_i&&!bad;
 wire bypass=accept&&cmd_i[31:0]-cycle_i==2;
 wire due=active&&waiting&&cycle_i==held[31:0]-2;
 assign consumer_cmd_v_o=(bypass||due)&&!fault_o&&!consumer_fault_i;
 assign consumer_cmd_o=active?held:cmd_i;
 assign context_v_o=(active||accept)&&!fault_o&&!consumer_fault_i;
 assign context_cmd_o=active?held:cmd_i;
 assign busy_o=active;
 always @(posedge clk)begin
 if(!rst_n)begin active<=0;waiting<=0;held<=0;last_cycle<=0;fault_o<=0;end
 else begin
 if(consumer_fault_i||(cmd_v_i&&(active||bad))||
    (active&&cycle_i!=last_cycle+1)||
    (active&&waiting&&$signed(cycle_i-(held[31:0]-2))>0)||
    (consumer_done_i&&(!active||waiting)))fault_o<=1;
 if(active)last_cycle<=cycle_i;
 if(accept)begin active<=1;waiting<=!bypass;held<=cmd_i;last_cycle<=cycle_i;end
 if(due)waiting<=0;
 if(consumer_done_i&&active&&!waiting)active<=0;
 end end
endmodule
`default_nettype wire
