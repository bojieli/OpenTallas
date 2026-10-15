`timescale 1ns/1ps
// Opt-in static successor, component only until mapped into the die contract.
// Lower 547 bits retain the existing engine record {tag,mode,last,par,data}.
// No ready, credit, arbitration, occupancy-driven issue or dynamic completion.
module s81_static_tp4_endpoint_dynamic(
 input wire clk, rst_n,input wire [1:0] rank,input wire configuration_fault,
 input wire issue_slot, src_valid, input wire [511:0] src_data,
 input wire [31:0] tag, input wire [15:0] seq,
 input wire last, input wire [3:0] rankmask,
 output reg tx_valid, output reg [568:0] tx_frame,
 input wire commit_slot, input wire [3:0] rx_valid,
 input wire [4*569-1:0] rx_frame,
 input wire [31:0] commit_tag, input wire [15:0] commit_seq,
 input wire commit_last, input wire [3:0] commit_rankmask,
 // Explicit compiler rows, one per rank. No inferred contiguous-row assumption.
 input wire [59:0] commit_rows,
 output reg [3:0] vm_we, output reg [59:0] vm_rows,
 output reg [2047:0] vm_data,output reg [31:0] gather_tag,output reg [15:0] gather_seq,output reg gather_last, output reg fault
);
 integer r; reg bad; reg [568:0] f;
 always @* begin
  bad=(rx_valid != (commit_slot ? commit_rankmask : 4'b0));
  for(integer k=0;k<4;k=k+1) begin
   f=rx_frame[k*569+:569];
   if(commit_slot && commit_rankmask[k])
    if(f[568:567]!=2'(k) || f[566:563]!=commit_rankmask ||
       f[562:547]!=commit_seq || f[546:515]!=commit_tag ||
       f[514]!=1'b0 || f[513]!=commit_last || f[512]!=^f[511:0]) bad=1;
  end
 end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin tx_valid<=0;tx_frame<=0;vm_we<=0;vm_rows<=0;vm_data<=0;gather_tag<=0;gather_seq<=0;gather_last<=0;fault<=0;end
  else begin
   // Missing, extra or late source is a sticky schedule fault, never rescheduled.
   if(configuration_fault)fault<=1;
   gather_tag<=commit_tag;gather_seq<=commit_seq;gather_last<=commit_last;
   if(src_valid != (issue_slot && rankmask[rank])) fault<=1;
   tx_valid<=issue_slot && rankmask[rank] && src_valid;
   tx_frame<={rank,rankmask,seq,tag,1'b0,last,^src_data,src_data};
   if(bad || (commit_slot && commit_rankmask!=4'hf)) fault<=1;
   // Timing is fixed even on failure. Invalid transactions suppress writes.
   vm_we<=commit_slot && !bad && !fault && !configuration_fault && commit_rankmask==4'hf ? 4'hf : 4'h0;
   vm_rows<=commit_rows;
   for(r=0;r<4;r=r+1) vm_data[r*512+:512]<=rx_frame[r*569+:512];
  end
 end
endmodule
