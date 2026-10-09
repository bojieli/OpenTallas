`timescale 1ps/1fs
`default_nettype none
// Lossless co72 -> real TU545. Fifteen literal34-bit slots per payload,
// payload511 actual quarter-last, payload510 zero; no header truncation.
module ot_hbm_native_candidate_format #(parameter integer ENABLE=0)(
 input wire clk,por_n,
 input wire owner_valid,owner_fault,retained,input wire [72:0] owner_frame,
 input wire [6:0] owner_rank,input wire tu_kind,input wire [7:0] tu_dst,
 input wire [71:0] co,input wire co_quarter_last,output reg coc,
 output wire tu_v,input wire tu_r,output wire [544:0] tu,
 output wire [72:0] tu_owner,output wire drained,output wire fault
);
 reg [72:0] fifo[0:7];reg [2:0] wp,rp;reg [3:0] used;
 reg half;
 reg [509:0] payload;reg [3:0] slots;
 reg [1:0] quarter;reg [13:0] beat;
 reg pending,qlast,sticky_fault;
 reg [72:0] held_owner;reg [6:0] held_rank;
 reg [7:0] held_dst;reg held_kind,seen_retained;
 wire allowed=ENABLE&&retained&&owner_valid&&!owner_fault&&!sticky_fault;
 wire push=allowed&&co[0]&&used<8;
 wire [72:0] packet=fifo[rp];
 wire [1:0] pq=packet[3:2];
 wire [33:0] tuple=half?{packet[71:55],packet[37:22],packet[5]}:
                               {packet[54:38],packet[21:6],packet[4]};
 wire step=allowed&&used!=0&&!pending;
 wire pop=step&&half;
 wire final_slot=step&&half&&packet[72];
 wire emit=step&&(slots==14||final_slot);
 assign tu_v=allowed&&pending;
 assign tu={held_kind,held_dst,{1'b0,held_rank},{quarter,beat},qlast,1'b0,payload};
 assign tu_owner=held_owner;
 assign drained=ENABLE&&used==0&&!pending&&slots==0;
 assign fault=ENABLE&&(sticky_fault||owner_fault);
 always @(posedge clk or negedge por_n)begin
  if(!por_n)begin wp<=0;rp<=0;used<=0;half<=0;payload<=0;slots<=0;
   quarter<=0;beat<=0;pending<=0;qlast<=0;sticky_fault<=0;coc<=0;
   held_owner<=0;held_rank<=0;held_dst<=0;held_kind<=0;seen_retained<=0;end
  else if(ENABLE)begin
   coc<=pop;seen_retained<=retained;
   if(retained&&!seen_retained)begin
    held_owner<=owner_frame;held_rank<=owner_rank;held_dst<=tu_dst;held_kind<=tu_kind;
    if(!drained||owner_rank>=96)sticky_fault<=1;
   end
   if(owner_fault||(retained&&seen_retained&&
      (held_owner!=owner_frame||held_rank!=owner_rank||held_dst!=tu_dst||held_kind!=tu_kind))||
      (co[0]&&(!allowed||used==8))||
      (!retained&&seen_retained&&!drained)||
      (step&&(pq!=quarter||packet[1]!=(packet[72]&&pq==3))))sticky_fault<=1;
   case({push,pop})2'b10:used<=used+1'b1;2'b01:used<=used-1'b1;default:;endcase
   if(push)begin fifo[wp]<={co_quarter_last,co};wp<=wp+1'b1;end
   if(step)begin
    payload[34*slots+:34]<=tuple;
    half<=!half;
    if(pop)rp<=rp+1'b1;
    if(emit)begin pending<=1;qlast<=final_slot;end
    else slots<=slots+1'b1;
   end
   if(tu_v&&tu_r)begin
    pending<=0;payload<=0;slots<=0;
    if(qlast)begin quarter<=quarter+1'b1;beat<=0;end
    else if(beat==14'h3fff)sticky_fault<=1;
    else beat<=beat+1'b1;
   end
   // The last quarter leaves the ordinal ready for the next retained frame.
   if(!retained&&seen_retained&&drained)begin quarter<=0;beat<=0;end
  end else coc<=0;
 end
endmodule
`default_nettype wire
