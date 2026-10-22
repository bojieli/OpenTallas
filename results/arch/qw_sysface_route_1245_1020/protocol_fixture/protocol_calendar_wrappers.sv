// Functional specialization only; independent source copies are the parent's responsibility.
module qfd_syscal16_n32 (
  input wire ck,
  // reset 0: control+rep/bcur <=32FF; 1:cur32FF; 2:cnt14FF;
  // reset 3+2g / 4+2g: the two 16-bit pointer-select groups.
  input wire [3+2*1-1:0] rst_n,
  input wire cfg_we,
  input wire [4:0] cfg_addr,
  // Each independent 32-bit producer supplies at most 32 table words.
  input wire [1*32-1:0] cfg_data_k,
  // Three independent segment decoder producers per 16-entry group,
  // followed by the binary segment-base producer.
  input wire [(3*1+1)*4-1:0] cfg_seg_k,
  // 0:curhi14,1:curmid8,2:curlo10,3:rep/bcur10,4:cnt14,5:control,
  // 6+2g / 7+2g: the two pointer-select groups, each16bits.
  input wire [6+2*1-1:0] start_k, halt_k,
  // 0:firsthi14,1:firstmid8,2:firstlo10,3:binarybase,
  // 4+g: pointer-start group16.
  input wire [4+1-1:0] seg_k,
  output reg ev_v,
  output reg [2:0] ev_port,
  output reg [3:0] ev_kind,
  output reg [4:0] ev_beat,
  output reg running, fault);
ot_qwen_d2d_cal_sysface32 #(.NE(16)) u_cal(.ck(ck),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data_k(cfg_data_k),.cfg_seg_k(cfg_seg_k),.start_k(start_k),.halt_k(halt_k),.seg_k(seg_k),.ev_v(ev_v),.ev_port(ev_port),.ev_kind(ev_kind),.ev_beat(ev_beat),.running(running),.fault(fault));
endmodule

// Functional specialization only; independent source copies are the parent's responsibility.
module qfd_syscal32_n32 (
  input wire ck,
  // reset 0: control+rep/bcur <=32FF; 1:cur32FF; 2:cnt14FF;
  // reset 3+2g / 4+2g: the two 16-bit pointer-select groups.
  input wire [3+2*2-1:0] rst_n,
  input wire cfg_we,
  input wire [5:0] cfg_addr,
  // Each independent 32-bit producer supplies at most 32 table words.
  input wire [1*32-1:0] cfg_data_k,
  // Three independent segment decoder producers per 16-entry group,
  // followed by the binary segment-base producer.
  input wire [(3*2+1)*5-1:0] cfg_seg_k,
  // 0:curhi14,1:curmid8,2:curlo10,3:rep/bcur10,4:cnt14,5:control,
  // 6+2g / 7+2g: the two pointer-select groups, each16bits.
  input wire [6+2*2-1:0] start_k, halt_k,
  // 0:firsthi14,1:firstmid8,2:firstlo10,3:binarybase,
  // 4+g: pointer-start group16.
  input wire [4+2-1:0] seg_k,
  output reg ev_v,
  output reg [2:0] ev_port,
  output reg [3:0] ev_kind,
  output reg [4:0] ev_beat,
  output reg running, fault);
ot_qwen_d2d_cal_sysface32 #(.NE(32)) u_cal(.ck(ck),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data_k(cfg_data_k),.cfg_seg_k(cfg_seg_k),.start_k(start_k),.halt_k(halt_k),.seg_k(seg_k),.ev_v(ev_v),.ev_port(ev_port),.ev_kind(ev_kind),.ev_beat(ev_beat),.running(running),.fault(fault));
endmodule

// Functional specialization only; independent source copies are the parent's responsibility.
module qfd_syscal64_n32 (
  input wire ck,
  // reset 0: control+rep/bcur <=32FF; 1:cur32FF; 2:cnt14FF;
  // reset 3+2g / 4+2g: the two 16-bit pointer-select groups.
  input wire [3+2*4-1:0] rst_n,
  input wire cfg_we,
  input wire [6:0] cfg_addr,
  // Each independent 32-bit producer supplies at most 32 table words.
  input wire [2*32-1:0] cfg_data_k,
  // Three independent segment decoder producers per 16-entry group,
  // followed by the binary segment-base producer.
  input wire [(3*4+1)*6-1:0] cfg_seg_k,
  // 0:curhi14,1:curmid8,2:curlo10,3:rep/bcur10,4:cnt14,5:control,
  // 6+2g / 7+2g: the two pointer-select groups, each16bits.
  input wire [6+2*4-1:0] start_k, halt_k,
  // 0:firsthi14,1:firstmid8,2:firstlo10,3:binarybase,
  // 4+g: pointer-start group16.
  input wire [4+4-1:0] seg_k,
  output reg ev_v,
  output reg [2:0] ev_port,
  output reg [3:0] ev_kind,
  output reg [4:0] ev_beat,
  output reg running, fault);
ot_qwen_d2d_cal_sysface32 #(.NE(64)) u_cal(.ck(ck),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data_k(cfg_data_k),.cfg_seg_k(cfg_seg_k),.start_k(start_k),.halt_k(halt_k),.seg_k(seg_k),.ev_v(ev_v),.ev_port(ev_port),.ev_kind(ev_kind),.ev_beat(ev_beat),.running(running),.fault(fault));
endmodule
