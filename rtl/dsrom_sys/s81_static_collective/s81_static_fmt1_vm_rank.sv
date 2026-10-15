`timescale 1ns/1ps
// Actual static VM-service join, not a replacement for the historical collective
// slab's HC/WFC/host/clock functions. The compiler drives every calendar input.
// VM service pins: request {row14,v}; response {data512,v} after fixed L12.
// The registered request adds one edge before VM L12. issue_slot must be the
// compiler's matching return edge; payload validity only detects faults.
// Gather -> VM sources44..47 is one registered edge, with explicit rows/tags.
module s81_static_fmt1_vm_rank #(parameter integer RANK=0)(
 input wire clk,rst_n,
 input wire read_slot,input wire [13:0] read_row,
 output reg [14:0] t_crq,input wire [512:0] f_crs,
 input wire issue_slot,input wire [31:0] tag,input wire [15:0] seq,
 input wire last,input wire [3:0] rankmask,
 input wire commit_slot,input wire [31:0] commit_tag,input wire [15:0] commit_seq,
 input wire commit_last,input wire [3:0] commit_rankmask,input wire [59:0] commit_rows,
 input wire tx_beat_slot,input wire [1:0] tx_phase,input wire tx_frame_slot,
 input wire rx_beat_slot,input wire [1:0] rx_phase,input wire rx_frame_slot,
 output wire [2:0] phy_tx_valid,output wire [1535:0] phy_tx_data,
 input wire [2:0] phy_rx_valid,input wire [1535:0] phy_rx_data,
 output reg [2203:0] t_vm,output wire fault
);
 wire [3:0] vm_we;wire [59:0] vm_rows;wire [2047:0] vm_data;
 wire endpoint_fault;reg row_fault;reg [7:0] write_tag;
 s81_static_fmt1_rank #(.RANK(RANK)) transport(
  .clk(clk),.rst_n(rst_n),.issue_slot(issue_slot),.src_valid(f_crs[0]),.src_data(f_crs[512:1]),
  .tag(tag),.seq(seq),.last(last),.rankmask(rankmask),
  .commit_slot(commit_slot),.commit_tag(commit_tag),.commit_seq(commit_seq),
  .commit_last(commit_last),.commit_rankmask(commit_rankmask),.commit_rows(commit_rows),
  .tx_beat_slot(tx_beat_slot),.tx_phase(tx_phase),.tx_frame_slot(tx_frame_slot),
  .rx_beat_slot(rx_beat_slot),.rx_phase(rx_phase),.rx_frame_slot(rx_frame_slot),
  .phy_tx_valid(phy_tx_valid),.phy_tx_data(phy_tx_data),
  .phy_rx_valid(phy_rx_valid),.phy_rx_data(phy_rx_data),
  .vm_we(vm_we),.vm_rows(vm_rows),.vm_data(vm_data),.fault(endpoint_fault));
 reg invalid_row;
 always @* begin
  invalid_row=0;
  for(integer k=0;k<4;k=k+1) if(vm_we[k] && vm_rows[k*15+14]) invalid_row=1;
 end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n)begin t_crq<=0;t_vm<=0;write_tag<=0;row_fault<=0;end
  else begin
   t_crq<={read_row,read_slot};write_tag<=commit_tag[7:0];
   if(invalid_row)row_fault<=1;
   for(integer k=0;k<4;k=k+1)
    t_vm[k*551+:551]<={write_tag,vm_data[k*512+:512],16'hffff,
     vm_rows[k*15+:14],vm_we[k] && !invalid_row && !row_fault && !endpoint_fault};
  end
 end
 assign fault=endpoint_fault || row_fault;
endmodule
