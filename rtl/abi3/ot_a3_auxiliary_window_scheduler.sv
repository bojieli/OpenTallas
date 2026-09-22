`timescale 1ns/1ps
// Demand refill of three reusable 256-word windows. Capture immutable service-
// word bounds once per operation; clear only with coordinated transport drain.
// Pages are relative to each plane's base, so an unaligned object never causes
// a read before its base. Tail bursts end exactly at the declared plane extent.
// A single tagged burst is outstanding. No per-word address division or multiply.
module ot_a3_auxiliary_window_scheduler(
 input wire clk,rst_n,clear,
 input wire command_valid,
 output wire command_ready,
 input wire [31:0] command_generation,
 input wire [95:0] command_bases,command_words,
 input wire request_valid,
 input wire [31:0] request_generation,
 input wire [95:0] request_addresses,
 input wire [2:0] missing_planes,
 output wire window_valid,
 input wire window_ready,
 output wire [1:0] window_plane,
 output wire [31:0] window_generation,window_base,
 output wire [8:0] window_words,
 output wire fill_valid,
 input wire fill_ready,
 output wire [1:0] fill_plane,
 output wire [31:0] fill_generation,
 output wire [8:0] fill_index,
 output wire [63:0] fill_data,
 output wire fetch_valid,
 input wire fetch_ready,
 output wire [63:0] fetch_tag,
 output wire [1:0] fetch_plane,
 output wire [31:0] fetch_address,
 output wire [8:0] fetch_words,
 input wire response_valid,
 output wire response_ready,
 input wire [63:0] response_tag,
 input wire [8:0] response_index,
 input wire [63:0] response_data,
 output reg active,protocol_error
);
 localparam [2:0] IDLE=0,CHECK=1,PLAN=2,INSTALL=3,FETCH=4,FILL=5,SIZE=6;
 reg [2:0] state;
 reg [31:0] generation,bases[0:2],words[0:2];
 reg [31:0] base_q,words_q,address_q,page_q,remaining_q;
 reg [23:0] offset_q;
 reg [31:0] burst_base,serial;
 reg [8:0] burst_words,index;
 reg [1:0] plane;
 wire enabled=rst_n && !clear && !protocol_error;
 wire [1:0] selected=missing_planes[0]?2'd0:missing_planes[1]?2'd1:2'd2;
 wire [32:0] end_q={1'b0,base_q}+{1'b0,words_q};
 wire identity_ok=response_tag=={generation,serial} && response_index==index;
 assign command_ready=enabled && !active;
 assign window_valid=enabled && state==INSTALL;
 assign window_plane=plane;assign window_generation=generation;
 assign window_base=burst_base;assign window_words=burst_words;
 assign fill_valid=enabled && state==FILL && response_valid && identity_ok;
 assign fill_plane=plane;assign fill_generation=generation;
 assign fill_index=index;assign fill_data=response_data;
 assign fetch_valid=enabled && state==FETCH;
 assign fetch_tag={generation,serial};assign fetch_plane=plane;
 assign fetch_address=burst_base;assign fetch_words=burst_words;
 assign response_ready=enabled && state==FILL && identity_ok && fill_ready;
 integer i;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   state<=IDLE;generation<=0;active<=0;protocol_error<=0;
   base_q<=0;words_q<=0;address_q<=0;offset_q<=0;page_q<=0;remaining_q<=0;
   burst_base<=0;burst_words<=0;serial<=0;plane<=0;index<=0;
   for(i=0;i<3;i=i+1)begin bases[i]<=0;words[i]<=0;end
  end else if(clear)begin state<=IDLE;active<=0;protocol_error<=0;end
  else if(enabled)begin
   if(command_valid && command_ready)begin
    active<=1;generation<=command_generation;serial<=0;
    for(i=0;i<3;i=i+1)begin bases[i]<=command_bases[32*i+:32];words[i]<=command_words[32*i+:32];end
   end
   // An unrequested, duplicate, stale or misordered beat is never written.
   if(response_valid && (state!=FILL || !identity_ok))protocol_error<=1;
   case(state)
    IDLE:if(active && request_valid)begin
     if(request_generation!=generation)protocol_error<=1;
     else if(|missing_planes)begin
      plane<=selected;base_q<=bases[selected];words_q<=words[selected];
      address_q<=request_addresses[32*selected+:32];state<=CHECK;
     end
    end
    CHECK:begin
     if(words_q==0 || end_q>33'h100000000 || address_q<base_q || {1'b0,address_q}>=end_q)
      protocol_error<=1;
     else begin offset_q<=24'((address_q-base_q)>>8);state<=PLAN;end
    end
    PLAN:begin
     page_q<={offset_q,8'b0};
     remaining_q<=words_q-{offset_q,8'b0};
     state<=SIZE;
    end
    SIZE:begin
     burst_base<=base_q+page_q;
     burst_words<=remaining_q>32'd256 ? 9'd256 : remaining_q[8:0];
     state<=INSTALL;
    end
    INSTALL:if(window_ready)state<=FETCH;
    FETCH:if(fetch_ready)begin state<=FILL;index<=0;end
    FILL:if(response_valid && response_ready)begin
     if(index==burst_words-1'b1)begin state<=IDLE;serial<=serial+1'b1;end
     else index<=index+1'b1;
    end
    default:state<=IDLE;
   endcase
  end
 end
endmodule
