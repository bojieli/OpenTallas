`timescale 1ps/1fs
`default_nettype none
// Lossless co72 -> real TU545. Fifteen literal34-bit slots per payload,
// payload511 actual quarter-last, payload510 zero; no header truncation.
module ot_hbm_native_candidate_format #(parameter integer ENABLE=0)(
 input wire clk,por_n,
 input wire owner_valid,owner_fault,retained,input wire [72:0] owner_frame,
 input wire [6:0] owner_rank,input wire tu_kind,input wire [7:0] tu_dst,
 input wire [71:0] co,input wire co_quarter_last,output wire coc,
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
  reg [2:0] wp_n;
 reg [2:0] rp_n;
 reg [3:0] used_n;
 reg [0:0] half_n;
 reg [509:0] payload_n;
 reg [3:0] slots_n;
 reg [1:0] quarter_n;
 reg [13:0] beat_n;
 reg [0:0] pending_n;
 reg [0:0] qlast_n;
 reg [0:0] sticky_fault_n;
 reg [72:0] held_owner_n;
 reg [6:0] held_rank_n;
 reg [7:0] held_dst_n;
 reg [0:0] held_kind_n;
 reg [0:0] seen_retained_n;
 reg [72:0] fifo_n[0:7];
 reg coc_hold,coc_n;
 assign coc=ENABLE&&coded_ok&&!sticky_fault&&coc_hold;
 wire control_ok=(coc_n==~coc_hold)&&(wp_n==~wp)&&
   (rp_n==~rp)&&
   (used_n==~used)&&
   (half_n==~half)&&
   (payload_n==~payload)&&
   (slots_n==~slots)&&
   (quarter_n==~quarter)&&
   (beat_n==~beat)&&
   (pending_n==~pending)&&
   (qlast_n==~qlast)&&
   (sticky_fault_n==~sticky_fault)&&
   (held_owner_n==~held_owner)&&
   (held_rank_n==~held_rank)&&
   (held_dst_n==~held_dst)&&
   (held_kind_n==~held_kind)&&
   (seen_retained_n==~seen_retained);
 wire storage_ok=(used==0||fifo_n[rp]==~fifo[rp]);
 wire coded_ok=control_ok&&storage_ok;
 wire allowed=ENABLE&&retained&&owner_valid&&!owner_fault&&!sticky_fault&&coded_ok;
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
 assign drained=ENABLE&&!fault&&used==0&&!pending&&slots==0;
 assign fault=ENABLE&&(sticky_fault||owner_fault||!coded_ok);
 always @(posedge clk or negedge por_n)begin
  if(!por_n)begin begin wp<=0;wp_n<=~(0); end begin rp<=0;rp_n<=~(0); end begin used<=0;used_n<=~(0); end begin half<=0;half_n<=~(0); end begin payload<=0;payload_n<=~(0); end begin slots<=0;slots_n<=~(0); end 
   begin quarter<=0;quarter_n<=~(0); end begin beat<=0;beat_n<=~(0); end begin pending<=0;pending_n<=~(0); end begin qlast<=0;qlast_n<=~(0); end begin sticky_fault<=0;sticky_fault_n<=~(0); end begin coc_hold<=0;coc_n<=1;end 
   begin held_owner<=0;held_owner_n<=~(0); end begin held_rank<=0;held_rank_n<=~(0); end begin held_dst<=0;held_dst_n<=~(0); end begin held_kind<=0;held_kind_n<=~(0); end begin seen_retained<=0;seen_retained_n<=~(0); end end
  else if(ENABLE)begin
   begin coc_hold<=pop;coc_n<=~pop;end begin seen_retained<=retained;seen_retained_n<=~(retained); end 
   if(retained&&!seen_retained)begin
    begin held_owner<=owner_frame;held_owner_n<=~(owner_frame); end begin held_rank<=owner_rank;held_rank_n<=~(owner_rank); end begin held_dst<=tu_dst;held_dst_n<=~(tu_dst); end begin held_kind<=tu_kind;held_kind_n<=~(tu_kind); end 
    if(!drained||owner_rank>=96)begin sticky_fault<=1;sticky_fault_n<=~(1); end 
   end
   if(!coded_ok||owner_fault||(retained&&seen_retained&&
      (held_owner!=owner_frame||held_rank!=owner_rank||held_dst!=tu_dst||held_kind!=tu_kind))||
      (co[0]&&(!allowed||used==8))||
      (!retained&&seen_retained&&!drained)||
      (step&&(pq!=quarter||packet[1]!=(packet[72]&&pq==3))))begin sticky_fault<=1;sticky_fault_n<=~(1); end 
   case({push,pop})2'b10:begin used<=used+1'b1;used_n<=~(used+1'b1); end 2'b01:begin used<=used-1'b1;used_n<=~(used-1'b1); end default:;endcase
   if(push)begin begin fifo[wp]<={co_quarter_last,co};fifo_n[wp]<=~({co_quarter_last,co}); end begin wp<=wp+1'b1;wp_n<=~(wp+1'b1); end end
   if(step)begin
    begin payload[34*slots+:34]<=tuple;payload_n[34*slots+:34]<=~(tuple); end 
    begin half<=!half;half_n<=~(!half); end 
    if(pop)begin rp<=rp+1'b1;rp_n<=~(rp+1'b1); end 
    if(emit)begin begin pending<=1;pending_n<=~(1); end begin qlast<=final_slot;qlast_n<=~(final_slot); end end
    else begin slots<=slots+1'b1;slots_n<=~(slots+1'b1); end 
   end
   if(tu_v&&tu_r)begin
    begin pending<=0;pending_n<=~(0); end begin payload<=0;payload_n<=~(0); end begin slots<=0;slots_n<=~(0); end 
    if(qlast)begin begin quarter<=quarter+1'b1;quarter_n<=~(quarter+1'b1); end begin beat<=0;beat_n<=~(0); end end
    else if(beat==14'h3fff)begin sticky_fault<=1;sticky_fault_n<=~(1); end 
    else begin beat<=beat+1'b1;beat_n<=~(beat+1'b1); end 
   end
   // The last quarter leaves the ordinal ready for the next retained frame.
   if(!retained&&seen_retained&&drained)begin begin quarter<=0;quarter_n<=~(0); end begin beat<=0;beat_n<=~(0); end end
  end else begin coc_hold<=0;coc_n<=1;end 
 end
endmodule
`default_nettype wire
