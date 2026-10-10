`timescale 1ns/1ps
// One real layer/rank transient store: full64rows, eight words/position,
// two real SRAM macros. Identity+payload corrected before held response.
// Mutable lease/control protection and production quarter merge are open.
module ot_qwen_dspark_transient_kv #(parameter integer ENABLE=0,POSITIONS=8)(
 input wire clk,rst_n,input wire begin_v,output wire begin_r,
 input wire [63:0] begin_id,input wire [13:0] begin_pos,
 input wire retire_v,input wire allcopy_fenced,output wire retire_r,
 input wire w_v,output wire w_r,input wire [63:0] w_id,
 input wire [13:0] w_pos,input wire [2:0] w_word,input wire [7:0] w_sequence,
 input wire [511:0] w_data,output wire w_done_v,input wire w_done_r,
 output wire [63:0] w_done_id,output wire [7:0] w_done_sequence,
 input wire r_v,output wire r_r,input wire [63:0] r_id,
 input wire [13:0] r_pos,input wire [2:0] r_word,input wire [7:0] r_sequence,
 output wire o_v,input wire o_r,output reg [511:0] o_data,
 output wire [63:0] o_id,output wire [7:0] o_sequence,
 output wire [13:0] o_pos,output wire [2:0] o_word,
 output reg fault,output reg [31:0] corrected_reads
);
  function automatic logic [71:0] encode64(input logic [63:0] data);
    logic [71:0] c; integer p, k, j;
    begin
      c='0; j=0;
      for (p=1;p<=71;p=p+1)
        if ((p & (p-1)) != 0) begin c[p-1]=data[j]; j=j+1; end
      for (k=0;k<7;k=k+1)
        for (p=1;p<=71;p=p+1)
          if ((p & (1<<k)) != 0 && p!=(1<<k)) c[(1<<k)-1]=c[(1<<k)-1]^c[p-1];
      c[71]=^c[70:0]; encode64=c;
    end
  endfunction
  function automatic logic [65:0] decode64(input logic [71:0] code);
    logic [71:0] c; logic [6:0] syndrome; logic overall, ue, corrected;
    logic [63:0] data; integer p,k,j;
    begin
      c=code; syndrome='0; overall=^code; ue=0; corrected=0;
      for (k=0;k<7;k=k+1)
        for (p=1;p<=71;p=p+1)
          if ((p & (1<<k)) != 0) syndrome[k]=syndrome[k]^code[p-1];
      if (syndrome!=0) begin
        if (overall && syndrome<=71) begin c[syndrome-1]=~c[syndrome-1]; corrected=1; end
        else ue=1;
      end else if (overall) begin c[71]=~c[71]; corrected=1; end
      data='0; j=0;
      for (p=1;p<=71;p=p+1)
        if ((p & (p-1)) != 0) begin data[j]=c[p-1]; j=j+1; end
      decode64={ue,corrected,data};
    end
  endfunction
 reg live,seen;reg [63:0] owner,previous_owner;reg [13:0] base;
 reg [63:0] written;reg [2:0] phase;
 reg [5:0] row;reg [13:0] packet_pos;reg [2:0] packet_word;reg [7:0] packet_sequence;
 reg [1023:0] encoded,captured;wire [1023:0] macro_q;
 wire idle=(phase==0)&&!fault;
 assign begin_r=(ENABLE!=0)&&!live&&idle;
 assign retire_r=(ENABLE!=0)&&live&&idle&&allcopy_fenced;
 assign w_r=(ENABLE!=0)&&live&&idle&&!retire_v;
 assign r_r=(ENABLE!=0)&&live&&idle&&!retire_v&&!w_v;
 assign w_done_v=(phase==3)&&!fault;assign w_done_id=owner;assign w_done_sequence=packet_sequence;
 assign o_v=(phase==7)&&!fault;assign o_id=owner;assign o_sequence=packet_sequence;
 assign o_pos=packet_pos;assign o_word=packet_word;
 wire [14:0] w_offset={1'b0,w_pos}-{1'b0,base};
 wire [14:0] r_offset={1'b0,r_pos}-{1'b0,base};
 wire [5:0] write_row={w_offset[2:0],w_word};
 wire [5:0] read_row={r_offset[2:0],r_word};
 reg [639:0] decoded;reg any_ue,any_ce;reg [65:0] sector;
 always @* begin
  decoded=0;any_ue=0;any_ce=0;
  for(integer j=0;j<10;j=j+1)begin
   sector=decode64(captured[j*72+:72]);decoded[j*64+:64]=sector[63:0];
   any_ue=any_ue|sector[65];any_ce=any_ce|sector[64];
  end
 end
 integer j;reg [639:0] payload;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin live<=0;seen<=0;written<=0;phase<=0;fault<=0;corrected_reads<=0;end
  else begin
   if(begin_v&&begin_r)begin
    if((seen&&begin_id==previous_owner)||({1'b0,begin_pos}+POSITIONS)>16384||POSITIONS<1||POSITIONS>8)fault<=1;
    else begin live<=1;owner<=begin_id;previous_owner<=begin_id;seen<=1;base<=begin_pos;written<=0;end
   end
   if(retire_v&&live)begin
    if(!retire_r)fault<=1;
    else begin live<=0;written<=0;end
   end
   if(w_v&&w_r)begin
    if(w_id!=owner||w_offset>=POSITIONS||written[write_row])fault<=1;
    else begin
     payload={47'b0,w_word,w_pos,owner,w_data};encoded<=0;
     for(j=0;j<10;j=j+1)encoded[j*72+:72]<=encode64(payload[j*64+:64]);
     row<=write_row;packet_pos<=w_pos;packet_word<=w_word;packet_sequence<=w_sequence;phase<=1;
    end
   end else if(r_v&&r_r)begin
    if(r_id!=owner||r_offset>=POSITIONS||!written[read_row])fault<=1;
    else begin row<=read_row;packet_pos<=r_pos;packet_word<=r_word;packet_sequence<=r_sequence;phase<=4;end
   end
   if(phase==1)phase<=2;
   if(phase==2)begin written[row]<=1;phase<=3;end
   if(phase==3&&w_done_r)phase<=0;
   if(phase==4)phase<=5;
   if(phase==5)begin captured<=macro_q;phase<=6;end
   if(phase==6)begin
    if(any_ue||decoded[512+:64]!=owner||decoded[576+:14]!=packet_pos||decoded[590+:3]!=packet_word||decoded[593+:47]!=0)fault<=1;
    else begin o_data<=decoded[511:0];if(any_ce)corrected_reads<=corrected_reads+1'b1;phase<=7;end
   end
   if(phase==7&&o_r)phase<=0;
  end
 end
 for(genvar m=0;m<2;m=m+1)begin:memories
  ot_sram_1r1w_64x512_m1_r2c2 macro_inst(
   .clk(clk),.r_ce_in(phase==4&&!fault),.r_addr_in(row),.rd_out(macro_q[m*512+:512]),
   .w_ce_in(phase==1&&!fault),.w_addr_in(row),.wd_in(encoded[m*512+:512]),.w_mask_in({512{1'b1}}),
   .rr_en(2'b0),.rr_addr(12'b0),.cr_en(2'b0),.cr_sel(18'b0));
 end
endmodule
