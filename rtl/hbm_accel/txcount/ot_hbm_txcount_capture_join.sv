// Actual edge observer, default off. Not a provider or canonical debt owner.
// One nonzero range per accepted GO, matching Euclid's installed issuer r2.
// Native tag/gen64 remain in tuple239; backend owner46 is retained separately.
module ot_hbm_txcount_capture_join #(parameter bit ENABLE=0,parameter integer INDEX=0)(
 input wire clk,por_n,rst_n,
 input wire go_accept,input wire [238:0] go_tuple,input wire [54:0] go_owner55,
 input wire [31:0] go_page_mask,
 input wire rf_ack_accept,input wire [54:0] rf_ack_owner55,
 input wire w6_visible_accept,input wire [54:0] w6_visible_owner55,
 input wire producer_visible_accept,input wire [238:0] producer_visible_tuple,
 input wire frame_retire_accept,input wire [238:0] frame_retire_tuple,
 input wire [54:0] frame_retire_owner55,input wire source_fault,
 output wire dependency_valid,input wire dependency_ready,
 output wire [238:0] dependency_tuple,output wire [54:0] dependency_owner55,
 output wire [31:0] dependency_page_mask,output wire retained,fault
);
 import ot_gpu_w6_secded_pkg::*;
 generate if(!ENABLE)begin:off
  assign dependency_valid=0;assign dependency_tuple=0;assign dependency_owner55=0;
  assign dependency_page_mask=0;assign retained=0;assign fault=0;
 end else begin:on
  // tuple239, owner55, expected32, ACK32, visibility32, active,producer,
  // delivered, frame_retired, stickyfault =395 bits; seven SECDED words.
  reg [503:0] coded;
  wire [447:0] decoded;wire [6:0] ue;
  for(genvar w=0;w<7;w=w+1)begin:word
   wire [65:0] d=decode64(coded[w*72+:72]);
   assign decoded[w*64+:64]=d[63:0];assign ue[w]=d[65];
  end
  wire [394:0] s=decoded[394:0];reg [394:0] ns;
  wire bad=(|ue)||(|decoded[447:395]);
  wire active=s[390],producer=s[391],delivered=s[392],retired=s[393];
  wire [238:0] tuple=s[238:0];wire [54:0] owner=s[293:239];
  wire [31:0] expected=s[325:294],acks=s[357:326],visible=s[389:358];
  wire [9:0] length=go_tuple[9:0]-{1'b0,go_tuple[18:10]};
  wire [31:0] legal_mask=length>=1&&length<=32 ? (32'hffffffff>>(32-length)) : 0;
  wire go_legal=!active&&go_tuple[35]==(INDEX/32)&&go_tuple[34:30]==(INDEX%32)&&
   go_tuple[9:0]<=512&&go_tuple[9:0]>{1'b0,go_tuple[18:10]}&&
   go_owner55[8:0]==go_tuple[18:10]&&go_page_mask!=0&&go_page_mask==legal_mask;
  wire [9:0] ack_offset={1'b0,rf_ack_owner55[8:0]}-{1'b0,tuple[18:10]};
  wire [9:0] vis_offset={1'b0,w6_visible_owner55[8:0]}-{1'b0,tuple[18:10]};
  wire [31:0] ack_bit=32'b1<<ack_offset,vis_bit=32'b1<<vis_offset;
  wire ack_match=rf_ack_owner55[54:9]==owner[54:9]&&ack_offset<32&&
   (ack_bit&expected)!=0&&(ack_bit&acks)==0;
  wire vis_match=w6_visible_owner55[54:9]==owner[54:9]&&vis_offset<32&&
   (vis_bit&expected)!=0&&(vis_bit&visible)==0;
  wire unexpected=(go_accept&&!go_legal)||(active&&(
   (rf_ack_accept&&!ack_match)||(w6_visible_accept&&!vis_match)||
   (producer_visible_accept&&(producer||producer_visible_tuple!=tuple))||
   (frame_retire_accept&&(retired||frame_retire_tuple!=tuple||frame_retire_owner55!=owner))));
  wire live=por_n&&rst_n&&!bad&&!s[394]&&!source_fault&&!unexpected;
  assign fault=bad||s[394]||(active&&(!rst_n||source_fault))||unexpected;
  assign retained=active;
  assign dependency_valid=live&&active&&producer&&!delivered&&acks==expected&&visible==expected;
  assign dependency_tuple=tuple;assign dependency_owner55=owner;assign dependency_page_mask=expected;
  always @* begin
   ns=s;
   if(unexpected||(active&&(!rst_n||source_fault)))ns[394]=1;
   else if(live)begin
    if(go_accept)begin ns=0;ns[238:0]=go_tuple;ns[293:239]=go_owner55;ns[325:294]=go_page_mask;ns[390]=1;end
    else if(active)begin
     if(rf_ack_accept)ns[357:326]=acks|ack_bit;
     if(w6_visible_accept)ns[389:358]=visible|vis_bit;
     if(producer_visible_accept)ns[391]=1;
     if(frame_retire_accept)ns[393]=1;
     if(dependency_valid&&dependency_ready)ns[392]=1;
     // Discard only observer state, after both actual positive captures.
     // This is not RF source lease retirement, drain or issuer authority.
     if(ns[392]&&ns[393])ns=0;
    end
   end
  end
  wire [447:0] padded={53'b0,ns};
  for(genvar w=0;w<7;w=w+1)begin:store
   always @(posedge clk or negedge por_n)
    if(!por_n)coded[w*72+:72]<=encode64(0);
    else if(!bad)coded[w*72+:72]<=encode64(padded[w*64+:64]);
  end
 end endgenerate
endmodule
