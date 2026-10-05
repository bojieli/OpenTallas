`timescale 1ns/1ps
// Three reusable 256-word SRAM windows: activation64, activation-scale32,
// weight-scale64. Addresses are service words, not deployment byte addresses.
// The parent supplies bounded window descriptors and exact ordered fills;
// this module never rounds a read beyond a declared object extent. Generation
// tags bind residency to an operation. clear must accompany transport drain.
// Each plane remains invalid until its last fill is accepted. Other resident
// planes survive replacement, including independent activation/scale reuse.
// One held complete-bundle response; fills cannot overwrite a pending read.
module ot_a3_runtime_auxiliary_windows(
 input wire clk,rst_n,clear,
 input wire window_valid,
 output wire window_ready,
 input wire [1:0] window_plane,
 input wire [31:0] window_generation,window_base,
 input wire [8:0] window_words,
 input wire fill_valid,
 output wire fill_ready,
 input wire [1:0] fill_plane,
 input wire [31:0] fill_generation,
 input wire [8:0] fill_index,
 input wire [63:0] fill_data,
 input wire request_valid,
 output wire request_ready,
 input wire [31:0] request_generation,request_a,request_s,request_ws,request_w,
 input wire request_scale_a,request_scale_b,
 output wire [2:0] missing_planes,
 output wire response_valid,
 input wire response_ready,
 output reg [31:0] response_generation,response_w,
 output wire [63:0] response_a_data,response_ws_data,
 output wire [31:0] response_s_data,
 output reg protocol_error
);
 reg [2:0] resident,filling;
 reg [31:0] base[0:2],generation[0:2];
 reg [8:0] extent[0:2],next_fill[0:2];
 wire [31:0] address[0:2];
 assign address[0]=request_a;assign address[1]=request_s;assign address[2]=request_ws;
 wire [2:0] needed={request_scale_b,request_scale_a,1'b1};
 wire [2:0] hit;
 wire [31:0] offset[0:2];
 wire [63:0] memory_data[0:2];
 reg pending;
 reg [2:1] response_planes;
 wire enabled=rst_n && !clear && !protocol_error;
 wire read_slot=!pending || response_ready;
 wire plane_ok=window_plane<3;
 wire [32:0] window_end={1'b0,window_base}+{24'd0,window_words};
 wire geometry_ok=window_words!=0 && window_words<=9'd256 &&
                  window_end<=33'h100000000;
 assign window_ready=enabled && !pending && plane_ok && geometry_ok && !filling[window_plane];
 wire install=window_valid && window_ready;
 wire fill_ok=fill_plane<3 && filling[fill_plane] &&
              fill_generation==generation[fill_plane] && fill_index==next_fill[fill_plane];
 assign fill_ready=enabled && !pending && fill_ok && !install;
 wire write_word=fill_valid && fill_ready;
 assign missing_planes=needed & ~hit;
 assign request_ready=enabled && read_slot && !(|missing_planes) && !window_valid && !fill_valid;
 wire read_word=request_valid && request_ready;
 assign response_valid=rst_n && !clear && pending;
 assign response_a_data=memory_data[0];
 assign response_s_data=response_planes[1]?memory_data[1][31:0]:32'd0;
 assign response_ws_data=response_planes[2]?memory_data[2]:64'd0;
 genvar p;
 generate for(p=0;p<3;p=p+1)begin : plane
  assign offset[p]=address[p]-base[p];
  assign hit[p]=resident[p] && generation[p]==request_generation &&
                address[p]>=base[p] && offset[p]<{23'd0,extent[p]};
  wire reading=read_word && needed[p];
  wire writing=write_word && fill_plane==2'(p);
  wire [7:0] ram_address=reading?offset[p][7:0]:fill_index[7:0];
  if(p==1)begin : scale32
   fakeram7_256x32 ram(.clk(clk),.addr_in(ram_address),.ce_in(reading || writing),
    .we_in(writing),.wd_in(fill_data[31:0]),.rd_out(memory_data[p][31:0]));
   assign memory_data[p][63:32]=0;
  end else begin : data64
   fakeram_256x64 ram(.clk(clk),.addr_in(ram_address),.ce_in(reading || writing),
    .we_in(writing),.wd_in(fill_data),.rd_out(memory_data[p]));
  end
 end endgenerate
 integer i;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   resident<=0;filling<=0;pending<=0;response_planes<=0;
   response_generation<=0;response_w<=0;protocol_error<=0;
   for(i=0;i<3;i=i+1)begin base[i]<=0;generation[i]<=0;extent[i]<=0;next_fill[i]<=0;end
  end else if(clear)begin resident<=0;filling<=0;pending<=0;protocol_error<=0;end
  else begin
   if(window_valid && (!plane_ok || !geometry_ok))protocol_error<=1;
   if(fill_valid && !fill_ok)protocol_error<=1;
   if(response_valid && response_ready)pending<=0;
   if(read_word)begin
    pending<=1;response_generation<=request_generation;response_w<=request_w;response_planes<=needed[2:1];
   end
   if(install)begin
    resident[window_plane]<=0;filling[window_plane]<=1;
    base[window_plane]<=window_base;generation[window_plane]<=window_generation;
    extent[window_plane]<=window_words;next_fill[window_plane]<=0;
   end
   if(write_word)begin
    next_fill[fill_plane]<=next_fill[fill_plane]+1'b1;
    if(fill_index==extent[fill_plane]-1'b1)begin resident[fill_plane]<=1;filling[fill_plane]<=0;end
   end
  end
 end
endmodule
