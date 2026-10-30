`default_nettype none
// PREP static RAW/privateCOPY fill classification, keyed by an ACCEPTED native
// LOAD command before the VMFC fill event. Default no-context behavior passes
// EVERY RAW valid bit unchanged, including malformed traffic for nativefault
// detection. Payload/bank/slot/epoch data wires bypass unchanged; only valids
// are split. No arbitration, wait, newword or data register edge.
// COPY-only fill commands omit RAWbegin; joint RAW+COPY fills have an explicit
// matching RAWbegin identity. Existing context/epoch ownership and static
// no-reuse-while-inflight contracts remain mandatory. This logical endpoint
// does not establish physical16PC broadcast/fanout timing.
module ot_hbm_static_load_raw_copy_fill_route(
 input wire clk,rst_n,input wire context_v_i,input wire[307:0]context_cmd_i,
 input wire calendar_v_i,input wire[88:0]calendar_payload_i,
 input wire[15:0]fill_v_i,fill_bank_i,input wire[255:0]fill_epoch_i,
 output reg[15:0]raw_fill_v_o,copy_fill_v_o,
 output wire copy_calendar_v_o,output wire[88:0]copy_calendar_payload_o,
 output reg fault_o
);
 reg[1:0]raw_prepared,copy_live,joint;
 reg[15:0]raw_epoch[0:1],copy_epoch[0:1];
 wire rb=calendar_payload_i[1],fb=calendar_payload_i[53];
 wire raw_begin=calendar_v_i&&calendar_payload_i[0];
 wire fill_command=calendar_v_i&&calendar_payload_i[52];
 wire cb=context_cmd_i[291];wire[15:0]ce=context_cmd_i[307:292];
 wire same_identity=fb==cb&&calendar_payload_i[69:54]==ce;
 wire same_window=calendar_payload_i[84:70]==context_cmd_i[103:89]&&calendar_payload_i[88:85]==context_cmd_i[85:82];
 wire copy_event=fill_command&&context_v_i&&same_identity&&same_window;
 wire joint_event=(raw_prepared[fb]&&raw_epoch[fb]==calendar_payload_i[69:54])||
                 (raw_begin&&rb==fb&&calendar_payload_i[17:2]==calendar_payload_i[69:54]);
 assign copy_calendar_v_o=copy_event&&!fault_o;
 // COPYbridge uses meaningfulfill metadata, not RAW begin/start commands.
 assign copy_calendar_payload_o=calendar_payload_i&~89'h40001;
 integer i,b;reg tag_context,classified;
 always @*begin
 raw_fill_v_o=fill_v_i;copy_fill_v_o=0;tag_context=0;classified=0;
 for(i=0;i<16;i=i+1)begin
 tag_context=context_v_i&&fill_bank_i[i]==cb&&fill_epoch_i[i*16+:16]==ce;
 classified=copy_live[fill_bank_i[i]]&&copy_epoch[fill_bank_i[i]]==fill_epoch_i[i*16+:16];
 if(tag_context&&classified&&!fault_o)begin
 copy_fill_v_o[i]=fill_v_i[i];
 if(!joint[fill_bank_i[i]])raw_fill_v_o[i]=0;
 end
 end end
 always @(posedge clk)begin
 if(!rst_n)begin
 raw_prepared<=0;copy_live<=0;joint<=0;fault_o<=0;
 for(b=0;b<2;b=b+1)begin raw_epoch[b]<=0;copy_epoch[b]<=0;end
 end else begin
 if(raw_begin)begin
 if(raw_prepared[rb])fault_o<=1;
 raw_prepared[rb]<=1;raw_epoch[rb]<=calendar_payload_i[17:2];
 end
 if(fill_command&&joint_event)raw_prepared[fb]<=0;
 if(fill_command&&context_v_i&&same_identity&&!same_window)fault_o<=1;
 if(copy_event)begin copy_live[fb]<=1;copy_epoch[fb]<=ce;joint[fb]<=joint_event;end
 for(b=0;b<16;b=b+1)
 if(fill_v_i[b]&&context_v_i&&fill_bank_i[b]==cb&&fill_epoch_i[b*16+:16]==ce&&
    !(copy_live[cb]&&copy_epoch[cb]==ce))fault_o<=1;
 end end
endmodule
`default_nettype wire
