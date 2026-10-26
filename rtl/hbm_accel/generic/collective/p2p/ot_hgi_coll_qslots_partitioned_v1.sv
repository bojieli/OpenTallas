`timescale 1ns/1ps
`default_nettype none
// Explicit physical successor candidate to V1 qslots, NOT silently instantiated
// by current q3/q2 parents. Same data ABI and fixed C/C+1/C+2 pipeline; one
// actual clock pin per native child leaf. Parent/clock ABI adoption is required.
// Model: tools/hbm_coll_static/qslots_partition_model.py. Controls/fault state
// replicated across bit slices costs 7020 FF across one q3 and three q2 parents.
module ot_hgi_coll_qslots_partitioned_v1 #(
 parameter integer NPT=3,INJ=2,DEL=4,PWT=545,
 parameter integer NS=INJ+NPT+DEL+1,ND=NPT+3*DEL+1,SELW=$clog2(NS),
 parameter integer BITS=32,NSL=(PWT+BITS-1)/BITS,
 parameter integer MUT_SELECT=0,MUT_PIN_LATENCY=0
)(
 input wire [NS-1:0] clk_capture,
 input wire [NSL-1:0] clk_output,
 input wire rst_n,
 input wire [NS-1:0] src_v,capture_slot,
 input wire [NS*PWT-1:0] src_d,
 input wire [ND-1:0] sink_slot,
 input wire [ND*SELW-1:0] sink_select,
 output wire [ND-1:0] dst_v,
 output wire [ND*PWT-1:0] dst_d,
 output wire fault,
 output wire [3:0] fault_kind
);
 wire [NS*PWT-1:0] captured;
 wire [NS-1:0] captured_slot,capture_fault;
 for(genvar s=0;s<NS;s=s+1)begin:g_source
  ot_hgi_coll_qslots_capture #(.NS(1),.PWT(PWT)) u_capture(
   .clk(clk_capture[s]),.rst_n(rst_n),.src_v(src_v[s]),.capture_slot(capture_slot[s]),
   .src_d(src_d[s*PWT+:PWT]),.captured(captured[s*PWT+:PWT]),
   .captured_slot(captured_slot[s]),.fault(capture_fault[s]));
 end
 wire [NSL-1:0] select_fault,unavailable_fault;
 wire [ND-1:0] slice_v[0:NSL-1];
 for(genvar k=0;k<NSL;k=k+1)begin:g_bits
  localparam integer CW=(PWT-k*BITS>=BITS)?BITS:PWT-k*BITS;
  wire [NS*CW-1:0] words;
  wire [ND*CW-1:0] results;
  for(genvar s=0;s<NS;s=s+1)begin:g_input
   assign words[s*CW+:CW]=MUT_PIN_LATENCY!=0 ? src_d[s*PWT+k*BITS+:CW] : captured[s*PWT+k*BITS+:CW];
  end
  ot_hgi_coll_qslots_output #(.NS(NS),.ND(ND),.PWT(CW),.SELW(SELW),.MUT_SELECT(MUT_SELECT)) u_output(
   .clk(clk_output[k]),.rst_n(rst_n),.captured(words),.captured_slot(captured_slot),
   .sink_slot(sink_slot),.sink_select(sink_select),.dst_v(slice_v[k]),.dst_d(results),
   .select_fault(select_fault[k]),.unavailable_fault(unavailable_fault[k]));
  for(genvar d=0;d<ND;d=d+1)begin:g_result
   assign dst_d[d*PWT+k*BITS+:CW]=results[d*CW+:CW];
  end
 end
 assign dst_v=slice_v[0];
 assign fault=(|capture_fault)|(|select_fault)|(|unavailable_fault);
 assign fault_kind={1'b0,|unavailable_fault,|select_fault,|capture_fault};
endmodule
`default_nettype wire
