// Default-off 8-word numeric delivery candidate. Two declared clocks:
// source_clk is LIVE even while the coherent arithmetic family is paused;
// output_step identifies its exact arithmetic producing edges. It must be the
// enable used by the actual coherent clock gate, stable before source_clk rises.
// sink_clk is live downstream service. There is no assumed frequency ratio.
// Credit must gate arithmetic BEFORE a producing edge; reset is a transport
// fence affecting both domains together. This component does not certify CDC
// placement, clock gate legality, downstream consumption or global retirement.
module ot_qwen_tile_numeric_delivery_queue (
 input wire source_clk,sink_clk,rst_n,
 input wire output_step,numeric_v,
 input wire [511:0] numeric_d,
 input wire [15:0] numeric_context,
 input wire [31:0] numeric_version,
 input wire numeric_has_query,
 input wire [39:0] numeric_query_seq,
 output wire output_credit,
 output wire sink_valid,
 input wire sink_ready,
 output wire [511:0] sink_data,
 output wire [15:0] sink_context,
 output wire [31:0] sink_version,
 output wire sink_has_query,
 output wire [39:0] sink_query_seq,
 output reg overflow_fault
);
 reg [600:0] words[0:7];
 reg [3:0] write_bin,write_gray,read_bin,read_gray;
 // These synchronizers run on LIVE clocks, including when output_step is zero.
 (* async_reg="true" *) reg [3:0] read_sync1,read_sync2;
 (* async_reg="true" *) reg [3:0] write_sync1,write_sync2;
 wire [3:0] write_next=write_bin+4'd1;
 wire [3:0] write_next_gray=(write_next>>1)^write_next;
 wire full=write_gray=={~read_sync2[3:2],read_sync2[1:0]};
 assign output_credit=!full;
 assign sink_valid=read_gray!=write_sync2;
 assign {sink_context,sink_version,sink_has_query,sink_query_seq,sink_data}=words[read_bin[2:0]];
 always @(posedge source_clk or negedge rst_n) begin
  if(!rst_n)begin write_bin<=0;write_gray<=0;read_sync1<=0;read_sync2<=0;overflow_fault<=0;end
  else begin
   read_sync1<=read_gray;read_sync2<=read_sync1;
   if(output_step&&numeric_v)begin
    if(full)overflow_fault<=1;
    else begin
     words[write_bin[2:0]]<={numeric_context,numeric_version,numeric_has_query,numeric_query_seq,numeric_d};
     write_bin<=write_next;write_gray<=write_next_gray;
    end
   end
  end
 end
 wire [3:0] read_next=read_bin+4'd1;
 always @(posedge sink_clk or negedge rst_n)begin
  if(!rst_n)begin read_bin<=0;read_gray<=0;write_sync1<=0;write_sync2<=0;end
  else begin
   write_sync1<=write_gray;write_sync2<=write_sync1;
   if(sink_valid&&sink_ready)begin read_bin<=read_next;read_gray<=(read_next>>1)^read_next;end
  end
 end
endmodule
