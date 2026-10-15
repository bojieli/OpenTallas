`timescale 1ns/1ps
`default_nettype none
// Three real protected paged programme issuers drive the 471-bit SFU IO ABI.
// PAGE_AW1:6 SRAMs/2048 rows; PAGE_AW2:12 SRAMs/4096 rows; global PC11/12.
// VM prefetch/drain/scalar/arith-start slots are actual stored hardware words.
// All stripes consume the same absolute PC/start. Agreement is checked;
// disagreement raises an exceptional fault, never normal backpressure.
module ot_hgi_sfu_io_calendar_static #(parameter integer PAGE_AW=1, AW=10+PAGE_AW)(
 input wire clk,rst_n,
 input wire cfg_we,
 input wire [1:0] cfg_stripe,
 input wire [AW-1:0] cfg_addr,
 input wire [255:0] cfg_data,
 input wire start_v,
 input wire [AW-1:0] start_base,
 input wire [AW:0] start_limit,
 input wire [15:0] start_loops,
 output wire [470:0] compiler_control,
 output wire control_v,
 output wire [31:0] ordinal,
 output wire active,done,
 output reg fault
);
 localparam integer CHUNK=223-PAGE_AW;
 wire [2:0] valid_s,active_s,done_s,fault_s;
 wire [31:0] ord_s[0:2];
 wire [470:0] words;
 for(genvar s=0;s<3;s=s+1)begin:g_stripe
  localparam integer W=(s==2)?471-2*CHUNK:CHUNK;
  ot_hgi_sfu_program_stripe_static #(.PAGE_AW(PAGE_AW),.W(W)) u_program(
   .clk(clk),.rst_n(rst_n),.cfg_we(cfg_we && cfg_stripe==s),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
   .start_v(start_v),.start_base(start_base),.start_limit(start_limit),.start_loops(start_loops),
   .calendar(words[s*CHUNK+:W]),.calendar_v(valid_s[s]),.ordinal(ord_s[s]),
   .active(active_s[s]),.done(done_s[s]),.fault(fault_s[s]));
 end
 assign compiler_control=control_v?words:471'd0;
 assign control_v=(&valid_s) && !(|fault_s);
 assign ordinal=ord_s[0];
 assign active=|active_s;
 assign done=&done_s;
 reg disagree;
 always @*begin
  disagree=(|valid_s && !(&valid_s)) || (|done_s && !(&done_s)) || (|active_s && !(&active_s));
  for(integer s=1;s<3;s=s+1)
   if(valid_s[s] && ord_s[s]!=ord_s[0])disagree=1;
 end
 always @(posedge clk or negedge rst_n)
  if(!rst_n)fault<=0;
  else if(disagree || |fault_s)fault<=1;
endmodule
`default_nettype wire
