`timescale 1ps/1fs
// One installed span of the ORIGINAL segment table. No bank truncation or
// invented resident sidx allocator: resident sidx=0 is retained as source data.
module ot_hbm_qwen_code_span_read #(
 parameter integer ENABLE=0,NSEG=8,CW=32,ROWS=4496
)(
 input wire [NSEG*24-1:0] seg_base,seg_len,
 input wire [NSEG*CW-1:0] seg_sidx,input wire[NSEG*2-1:0] seg_kind,
 input wire installed,input wire[2:0] installed_segment,
 input wire[23:0] installed_base,installed_length,
 input wire[CW-1:0] installed_sidx,input wire[1:0] installed_kind,
 input wire[12:0] installed_first_row,input wire[13:0] installed_rows,
 input wire published,input wire read_v,input wire[23:0] virtual_address,
 output reg read_bound,output reg[12:0] physical_row,
 output wire[2:0] virtual_bank,output reg mapping_fault
);
 integer i,hits;reg[24:0] last,offset,destination;
 reg source_match;
 assign virtual_bank=virtual_address[14:12];
 always @* begin
  hits=0;source_match=0;last=0;offset=0;destination=0;
  for(i=0;i<NSEG;i=i+1)begin
   last={1'b0,seg_base[i*24+:24]}+{1'b0,seg_len[i*24+:24]};
   if((seg_kind[i*2+:2]==1||seg_kind[i*2+:2]==2)&&
      {1'b0,virtual_address}>={1'b0,seg_base[i*24+:24]}&&{1'b0,virtual_address}<last)begin
    hits=hits+1;
    if(i==installed_segment&&seg_base[i*24+:24]==installed_base&&
       seg_len[i*24+:24]==installed_length&&seg_sidx[i*CW+:CW]==installed_sidx&&
       seg_kind[i*2+:2]==installed_kind)source_match=1;
   end
  end
  offset={1'b0,virtual_address}-{1'b0,installed_base};
  destination={12'b0,installed_first_row}+offset;
  read_bound=ENABLE&&installed&&published&&hits==1&&source_match&&
    (installed_kind==1||installed_kind==2)&&installed_length!=0&&
    installed_length==installed_rows&&installed_rows!=0&&
    ({1'b0,installed_first_row}+installed_rows)<=ROWS&&destination<ROWS&&
    virtual_address<24'd20480;
  physical_row=read_bound?destination[12:0]:13'b0;
  // An absent/unpublished grant is a wait; a malformed active grant is a fault.
  mapping_fault=ENABLE&&read_v&&installed&&
    (hits!=1||!source_match||installed_length!=installed_rows||
     ({1'b0,installed_first_row}+installed_rows)>ROWS||virtual_address>=24'd20480);
 end
endmodule
