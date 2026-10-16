`default_nettype none
// Static counterpart of query_owned_native. Same exact quant and retained
// arithmetic; all input/output issue decisions are compiler slots. The compiler
// must leave >=14 edges after the last head block before its emit slot.
module ot_hbm_idx_query_static_core(
 input wire clk,clk_quant,clk_quant_delay,input wire [3:0] clk_bank,
 input wire rst_n,frame_start,
 input wire block_v,input wire [4:0] block_head,input wire [1:0] block_number,
 input wire [1023:0] block_data,input wire [15:0] head_weight,
 input wire emit_v,input wire [4:0] emit_head,
 output reg ql_v,output reg [7:0] ql_head,
 output reg [511:0] ql_codes,output reg [31:0] ql_sc,output reg [15:0] ql_w,
 output wire fault
);
 reg bad;reg[6:0]tag[0:12];wire[3:0]bf;
 wire[16383:0]codes;wire[1023:0]scales;wire[511:0]weights;wire[127:0]seen;
 wire qv,qfault;wire[255:0]q;wire signed[9:0]qe;wire[511:0]qy;
 assign fault=bad||(|bf);
 ot_hbm_idx_actquant_owned_native quant(.clk(clk_quant),.clk_delay(clk_quant_delay),.rst_n(rst_n),.v(block_v),.fp4(1'b1),.x(block_data),
 .vo(qv),.q(q),.e(qe),.y(qy),.fault(qfault));
 for(genvar b=0;b<4;b=b+1)begin:gbank
  ot_hbm_idx_query_bank_native #(.BANK(b))bank(.clk(clk_bank[b]),.rst_n(rst_n),.start(frame_start),.take(block_v),
   .block_head(block_head),.block_number(block_number),.head_weight(head_weight),
   .qv(qv),.qfault(qfault),.qe(qe),.tag(tag[12]),.q(q),
   .codes_out(codes[b*4096+:4096]),.scales_out(scales[b*256+:256]),
   .weights_out(weights[b*128+:128]),.seen_out(seen[b*32+:32]),.fault(bf[b]));
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin bad<=0;ql_v<=0;ql_head<=0;ql_codes<=0;ql_sc<=0;ql_w<=0;end
  else begin
   tag[0]<={block_head,block_number};
   for(integer t=1;t<13;t=t+1)tag[t]<=tag[t-1];
   ql_v<=emit_v;
   ql_head<={3'b0,emit_head};ql_codes<=codes[emit_head*512+:512];
   ql_sc<=scales[emit_head*32+:32];ql_w<=weights[emit_head*16+:16];
   if(emit_v && !(&seen[emit_head*4+:4]))begin bad<=1;ql_v<=0;end
   if(frame_start && (block_v||emit_v||qv))bad<=1;
  end
 end
endmodule
`default_nettype wire
`default_nettype none
// ---------------------------------------------------------------------------
// PIN-REGISTERED TILE (OWNER RULE 19:50 PT 10-15, H-NETLIST/idxreg 2026-10-16): the die
// master ot_hbm_idx_query_static is this shell. Every data input and every output passes ONE kept
// flop at the pin (clocks pass through; rst_n enters a 2-flop release synchroniser); the unchanged arithmetic/control is
// ot_hbm_idx_query_static_core. Latency: +1 edge on every input, +1 edge on every output; the IDX
// calendar compiler (tools/hbm_idx_static_calendar.py, PIN table) schedules them.
// Pin flops have no reset (as physical/common_flow/ot_pin_regs.tcl); the core is reset.
// One data clock (clk) for every pin flop, as the flow's single-clock pin wrapper.
module ot_hbm_idx_query_static(
 input wire clk,clk_quant,clk_quant_delay,input wire [3:0] clk_bank,
 input wire rst_n,frame_start,
 input wire block_v,input wire [4:0] block_head,input wire [1:0] block_number,
 input wire [1023:0] block_data,input wire [15:0] head_weight,
 input wire emit_v,input wire [4:0] emit_head,
 output reg ql_v,output reg [7:0] ql_head,
 output reg [511:0] ql_codes,output reg [31:0] ql_sc,output reg [15:0] ql_w,
 output reg fault
);
 // rst_n: async assert, 2-edge release on clk; the core's resets (async and synchronous uses on every
 // same-PLL phase-0 root) come from this one kept register, so no input port feeds another root's data pins.
 (* keep *) reg [1:0] rst_sync;
 always @(posedge clk or negedge rst_n) if(!rst_n) rst_sync<=2'b00; else rst_sync<={rst_sync[0],1'b1};
 wire rst_core_n=rst_sync[1];
 (* keep *) reg fs_r,bv_r,ev_r;(* keep *) reg[4:0]bh_r,eh_r;(* keep *) reg[1:0]bn_r;(* keep *) reg[1023:0]bd_r;(* keep *) reg[15:0]hw_r;
 wire c_v,c_fault;wire[7:0]c_head;wire[511:0]c_codes;wire[31:0]c_sc;wire[15:0]c_w;
 always @(posedge clk)begin
  fs_r<=frame_start;bv_r<=block_v;bh_r<=block_head;bn_r<=block_number;bd_r<=block_data;hw_r<=head_weight;ev_r<=emit_v;eh_r<=emit_head;
  ql_v<=c_v;ql_head<=c_head;ql_codes<=c_codes;ql_sc<=c_sc;ql_w<=c_w;fault<=c_fault;
 end
 ot_hbm_idx_query_static_core core(.clk(clk),.clk_quant(clk_quant),.clk_quant_delay(clk_quant_delay),.clk_bank(clk_bank),.rst_n(rst_core_n),
  .frame_start(fs_r),.block_v(bv_r),.block_head(bh_r),.block_number(bn_r),.block_data(bd_r),.head_weight(hw_r),
  .emit_v(ev_r),.emit_head(eh_r),.ql_v(c_v),.ql_head(c_head),.ql_codes(c_codes),.ql_sc(c_sc),.ql_w(c_w),.fault(c_fault));
endmodule
`default_nettype wire
