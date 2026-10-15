`timescale 1ns/1ps
`default_nettype none
// Eight real paged protected issuers drive the fixed1742-bit SFU ABI.
// PAGE_AW1:16 actual SRAMs,2048 rows,payload7x222+188,global11-bit PC.
// PAGE_AW2:32 actual SRAMs,4096 rows,payload7x221+195,global12-bit PC.
// All stripes consume the same absolute PC/start. Agreement is checked;
// disagreement raises an exceptional fault, never normal backpressure.
module ot_hgi_sfu_calendar_paged_static #(parameter integer PAGE_AW=1, AW=10+PAGE_AW)(
 input wire clk,rst_n,
 input wire cfg_we,
 input wire [2:0] cfg_stripe,
 input wire [AW-1:0] cfg_addr,
 input wire [255:0] cfg_data,
 input wire start_v,
 input wire [AW-1:0] start_base,
 input wire [AW:0] start_limit,
 input wire [15:0] start_loops,
 output wire [1741:0] compiler_control,
 output wire control_v,
 output wire [31:0] ordinal,
 output wire active,done,
 output reg fault
);
 localparam integer CHUNK=223-PAGE_AW;
 wire [7:0] valid_s,active_s,done_s,fault_s;
 wire [31:0] ord_s[0:7];
 wire [1741:0] words;
 for(genvar s=0;s<8;s=s+1)begin:g_stripe
  localparam integer W=(s==7)?1742-7*CHUNK:CHUNK;
  ot_hgi_sfu_program_stripe_static #(.PAGE_AW(PAGE_AW),.W(W)) u_program(
   .clk(clk),.rst_n(rst_n),.cfg_we(cfg_we && cfg_stripe==s),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
   .start_v(start_v),.start_base(start_base),.start_limit(start_limit),.start_loops(start_loops),
   .calendar(words[s*CHUNK+:W]),.calendar_v(valid_s[s]),.ordinal(ord_s[s]),
   .active(active_s[s]),.done(done_s[s]),.fault(fault_s[s]));
 end
 assign compiler_control=control_v?words:1742'd0;
 assign control_v=(&valid_s) && !(|fault_s);
 assign ordinal=ord_s[0];
 assign active=|active_s;
 assign done=&done_s;
 reg disagree;
 always @*begin
  disagree=(|valid_s && !(&valid_s)) || (|done_s && !(&done_s)) || (|active_s && !(&active_s));
  for(integer s=1;s<8;s=s+1)
   if(valid_s[s] && ord_s[s]!=ord_s[0])disagree=1;
 end
 always @(posedge clk or negedge rst_n)
  if(!rst_n)fault<=0;
  else if(disagree || |fault_s)fault<=1;
endmodule
`default_nettype wire
