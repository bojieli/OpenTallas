`timescale 1ns/1ps
// Vector-packed candidate: G/U/O each32 physical128x256 SRAMs. One256word
// read/edge per operand. Eight independently addressed full-sector staging
// writes/edge and eight O-sector drain reads/edge. No dynamic multiport alias.
module ot_hgi_sfu_fused_glu_store(
 input wire clk,rst_n,
 input wire [7:0] stage_v,stage_group,
 input wire [39:0] stage_bank,
 input wire [55:0] stage_row,
 input wire [2047:0] stage_data,
 input wire read_v,input wire [6:0] read_row,
 output reg read_valid,
 output wire [8191:0] gate_words,up_words,
 input wire [255:0] result_v,
 input wire [6:0] result_row,
 input wire [8191:0] result_data,
 input wire [7:0] drain_v,
 input wire [39:0] drain_bank,
 input wire [55:0] drain_row,
 output reg [7:0] drain_valid,
 output wire [2047:0] drain_data,
 output reg fault
);
 wire [8191:0] out_sectors;
 wire [95:0] collisions;
 genvar g,b,w;
 generate for(g=0;g<3;g=g+1) begin:group_mem
  for(b=0;b<32;b=b+1) begin:bank_mem
   reg we,re;
   reg [6:0] wa,ra;
   reg [255:0] wd,mask;
   reg clash;
   integer p;
   always @* begin
    we=0;re=0;wa=0;ra=0;wd=0;mask=0;clash=0;
    if(g<2) begin
     re=read_v;ra=read_row;
     for(p=0;p<8;p=p+1) if(stage_v[p] && stage_group[p]==g && stage_bank[p*5+:5]==b) begin
      if(we) clash=1;
      we=1;wa=stage_row[p*7+:7];wd=stage_data[p*256+:256];mask={256{1'b1}};
     end
    end else begin
     we=|result_v[b*8+:8];wa=result_row;wd=result_data[b*256+:256];
     for(p=0;p<8;p=p+1) mask[p*32+:32]={32{result_v[b*8+p]}};
     for(p=0;p<8;p=p+1) if(drain_v[p] && drain_bank[p*5+:5]==b) begin
      if(re) clash=1;
      re=1;ra=drain_row[p*7+:7];
     end
    end
   end
   wire [255:0] q;
   ot_sram_1r1w_128x256_m1_r2c2 ram(.clk(clk),.r_ce_in(re),.r_addr_in(ra),.rd_out(q),
    .w_ce_in(we),.w_addr_in(wa),.wd_in(wd),.w_mask_in(mask),
    .rr_en(2'd0),.rr_addr(14'd0),.cr_en(2'd0),.cr_sel(16'd0));
   if(g==0) assign gate_words[b*256+:256]=q;
   if(g==1) assign up_words[b*256+:256]=q;
   if(g==2) assign out_sectors[b*256+:256]=q;
   assign collisions[g*32+b]=clash;
  end
 end endgenerate
 reg [39:0] drain_bq;
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin read_valid<=0;drain_valid<=0;fault<=0;end
  else begin read_valid<=read_v;drain_valid<=drain_v;fault<=fault|(|collisions);end
 end
 always @(posedge clk) drain_bq<=drain_bank;
 generate for(w=0;w<8;w=w+1) begin:drain_mux
  assign drain_data[w*256+:256]=out_sectors[drain_bq[w*5+:5]*256+:256];
 end endgenerate
endmodule
