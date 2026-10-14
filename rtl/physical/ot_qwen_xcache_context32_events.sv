// Default-off two-clock candidate. Events are one-entry acknowledged mailboxes.
// The caller must pause the whole coherent core when read_credit is low.
// Ack toggles require an explicitly declared related-clock/CDC protocol; no
// physical crossing or registered lookahead is qualified by this RTL alone.
module ot_qwen_xcache_context32_events_store (
 input wire load_clk,rst_n,clear,load_v,load_j_repeat,
 input wire [39:0] load_query_seq,
 input wire [20:0] load_epoch,
 input wire [15:0] load_context,load_token,load_recipient,
 input wire [31:0] load_version,
 input wire [95:0] load_addr,
 input wire [127:0] load_x,
 input wire [4:0] load_root,
 input wire [3:0] load_phase,
 input wire fill_ack_toggle,
 output wire load_ready,
 output reg fill_toggle,
 output reg [246:0] fill_tuple,
 input wire read_j_repeat,
 input wire [20:0] read_epoch,
 input wire [15:0] read_context,
 input wire [31:0] read_version,
 input wire [95:0] read_addr,
 output wire found,
 output wire [127:0] read_data,
 output wire [206:0] resident_tuple
);
 reg [127:0] data[0:31];
 reg [20:0] tags[0:31];
 reg [15:0] contexts[0:31],tokens[0:31],recipients[0:31];
 reg [31:0] versions[0:31];
 reg [95:0] addresses[0:31];
 reg [4:0] roots[0:31];reg [3:0] phases[0:31];
 reg [31:0] valid,modes;
 wire [20:0] lt=load_j_repeat?{load_epoch[20:3],3'b0}:load_epoch;
 wire [20:0] rt=read_j_repeat?{read_epoch[20:3],3'b0}:read_epoch;
 wire [4:0] li=load_j_repeat?load_epoch[7:3]:load_epoch[4:0];
 wire [4:0] ri=read_j_repeat?read_epoch[7:3]:read_epoch[4:0];
 assign load_ready=(fill_toggle==fill_ack_toggle)&&!clear;
 assign found=valid[ri]&&tags[ri]==rt&&modes[ri]==read_j_repeat&&
  contexts[ri]==read_context&&versions[ri]==read_version&&addresses[ri]==read_addr;
 assign read_data=data[ri];
 // Event tuple: context16/version32/mode1/epoch21/address96/token16/root5/phase4/recipient16.
 // Report actual read epoch for a response, retaining source provenance from its resident row.
 assign resident_tuple={read_context,read_version,read_j_repeat,read_epoch,read_addr,
   tokens[ri],roots[ri],phases[ri],recipients[ri]};
 always @(posedge load_clk or negedge rst_n) begin
  if(!rst_n)begin valid<=0;fill_toggle<=0;end
  else begin
   if(clear)valid<=0;
   else if(load_v&&load_ready)begin
    valid[li]<=1;data[li]<=load_x;tags[li]<=lt;modes[li]<=load_j_repeat;
    contexts[li]<=load_context;versions[li]<=load_version;addresses[li]<=load_addr;
    tokens[li]<=load_token;roots[li]<=load_root;phases[li]<=load_phase;recipients[li]<=load_recipient;
    fill_tuple<={load_context,load_version,load_j_repeat,load_epoch,load_addr,
      load_token,load_root,load_phase,load_recipient,load_query_seq};
    fill_toggle<=!fill_toggle;
   end
  end
 end
endmodule

module ot_qwen_xcache_context32_events_response (
 input wire core_clk,rst_n,
 input wire [3:0] read_v,
 input wire found,
 input wire [127:0] read_data,
 input wire [206:0] resident_tuple,
 input wire [39:0] read_query_seq,
 input wire response_ack_toggle,
 output wire read_credit,
 output reg response_toggle,
 output reg [246:0] response_tuple,
 output reg [127:0] q_x,
 output reg fault
);
 assign read_credit=response_toggle==response_ack_toggle;
 always @(posedge core_clk or negedge rst_n)begin
  if(!rst_n)begin q_x<=0;fault<=0;response_toggle<=0;end
  else if(|read_v)begin
   if(!read_credit)begin q_x<=0;fault<=1;end // caller failed coherent pause/credit contract
   else if(found)begin q_x<=read_data;response_tuple<={resident_tuple,read_query_seq};response_toggle<=!response_toggle;end
   else begin q_x<=0;fault<=1;end
  end
 end
endmodule

// Wires-only parent: one live-loader entry and one coherent-response entry.
module ot_qwen_xcache_context32_events (
 input wire load_clk,core_clk,rst_n,clear,
 input wire load_j_repeat,load_v,
 input wire [39:0] load_query_seq,read_query_seq,
 input wire [20:0] load_epoch,read_epoch,
 input wire [15:0] load_context,read_context,load_token,load_recipient,
 input wire [31:0] load_version,read_version,
 input wire [95:0] load_addr,read_addr,
 input wire [127:0] load_x,
 input wire [4:0] load_root,
 input wire [3:0] load_phase,
 input wire read_j_repeat,
 input wire [3:0] read_v,
 input wire fill_ack_toggle,response_ack_toggle,
 output wire load_ready,read_credit,hit,
 output wire fill_toggle,response_toggle,
 output wire [246:0] fill_tuple,response_tuple,
 output wire [127:0] q_x,
 output wire fault
);
 wire found;wire [127:0] read_data;wire [206:0] resident_tuple;
 ot_qwen_xcache_context32_events_store u_store (
  .load_clk(load_clk),.rst_n(rst_n),.clear(clear),.load_v(load_v),.load_j_repeat(load_j_repeat),
  .load_epoch(load_epoch),.load_query_seq(load_query_seq),.load_context(load_context),.load_version(load_version),.load_addr(load_addr),.load_x(load_x),
  .load_token(load_token),.load_root(load_root),.load_phase(load_phase),.load_recipient(load_recipient),
  .fill_ack_toggle(fill_ack_toggle),.load_ready(load_ready),.fill_toggle(fill_toggle),.fill_tuple(fill_tuple),
  .read_j_repeat(read_j_repeat),.read_epoch(read_epoch),.read_context(read_context),.read_version(read_version),
  .read_addr(read_addr),.found(found),.read_data(read_data),.resident_tuple(resident_tuple));
 ot_qwen_xcache_context32_events_response u_response (
  .core_clk(core_clk),.rst_n(rst_n),.read_v(read_v),.found(found),.read_data(read_data),.resident_tuple(resident_tuple),
  .read_query_seq(read_query_seq),.response_ack_toggle(response_ack_toggle),.read_credit(read_credit),.response_toggle(response_toggle),
  .response_tuple(response_tuple),.q_x(q_x),.fault(fault));
 assign hit=!(|read_v)||found;
endmodule
