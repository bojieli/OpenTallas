`default_nettype none
// PREP static adapter from the EXISTING VMFC ROLE W89 payload to the new
// private LOAD buffers. RAW begin/start/fill paths bypass this module unchanged.
// bit0 records the RAW begin identity; bit52 is the dated actual VMKS fill
// command carrying meaningful row/col/buffer/epoch. At that event release the
// old COPY ownership, if present; exactly2 edges later begin the COPY window.
// The physical calendar MUST put the first COPY fill after that begin edge,
// including path skew. No ready/wait is provided. A fill event while LOAD has
// pending work, absent RAW begin, or during another2-edge transition faults.
// REQUIRE_RAW_BEGIN=0 is only for the accepted-LOAD-context fill router,
// which supplies matching COPY fill events; it does not broadcast to RAW.
// Completion is actual VM commit guard completion, not counter/packet drain.
module ot_hbm_static_load_window_calendar #(parameter integer REQUIRE_RAW_BEGIN=1)(
 input wire clk,rst_n,input wire calendar_v_i,input wire[88:0]payload_i,
 input wire load_busy_i,load_fault_i,
 output wire release_v_o,release_buffer_o,output wire[15:0]release_epoch_o,
 output wire begin_v_o,begin_buffer_o,output wire[15:0]begin_epoch_o,
 output wire[14:0]begin_row_o,output wire[3:0]begin_col_o,
 output reg fault_o
);
 reg[1:0]prepared,owned;reg[15:0]prepared_epoch[0:1],owned_epoch[0:1];
 reg[1:0]phase;reg buf_q;reg[15:0]epoch_q;reg[14:0]row_q;reg[3:0]col_q;
 wire raw_begin=calendar_v_i&&payload_i[0];
 wire fill=calendar_v_i&&payload_i[52];wire fb=payload_i[53];
 wire badfill=load_busy_i||phase!=0||((REQUIRE_RAW_BEGIN!=0)&&(!prepared[fb]||prepared_epoch[fb]!=payload_i[69:54]));
 wire admit=fill&&!badfill&&!fault_o&&!load_fault_i;
 assign release_v_o=admit&&owned[fb];
 assign release_buffer_o=fb;
 assign release_epoch_o=owned_epoch[fb];
 assign begin_v_o=phase==2&&!fault_o&&!load_fault_i&&!load_busy_i;
 assign begin_buffer_o=buf_q;assign begin_epoch_o=epoch_q;
 assign begin_row_o=row_q;assign begin_col_o=col_q;
 integer b;
 always @(posedge clk)begin
 if(!rst_n)begin
 prepared<=0;owned<=0;phase<=0;buf_q<=0;epoch_q<=0;row_q<=0;col_q<=0;fault_o<=0;
 for(b=0;b<2;b=b+1)begin prepared_epoch[b]<=0;owned_epoch[b]<=0;end
 end else begin
 if(load_fault_i||(fill&&badfill)||(phase!=0&&load_busy_i))fault_o<=1;
 if(raw_begin)begin
 if(prepared[payload_i[1]])fault_o<=1;
 prepared[payload_i[1]]<=1;prepared_epoch[payload_i[1]]<=payload_i[17:2];
 end
 if(admit)begin
 prepared[fb]<=0;owned[fb]<=0;buf_q<=fb;epoch_q<=payload_i[69:54];
 row_q<=payload_i[84:70];col_q<=payload_i[88:85];phase<=1;
 end else if(phase==1)phase<=2;
 else if(phase==2)begin
 phase<=0;
 if(begin_v_o)begin owned[buf_q]<=1;owned_epoch[buf_q]<=epoch_q;end
 end
 end end
endmodule
`default_nettype wire
