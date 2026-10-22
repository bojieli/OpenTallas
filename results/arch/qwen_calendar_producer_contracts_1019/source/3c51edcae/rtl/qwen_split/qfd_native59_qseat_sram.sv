`timescale 1ns/1ps
// Exact eight-write scatter store: each incoming lane owns one masked writer
// SRAM. A 3-bit seat owner selects its latest writer (higher lane wins on a
// duplicate, matching legacy NBA order). No arbitration, waiting, or dropped
// writes. Logical payload 32x512; physical capacity 8x32x512.
module qfd_native59_qseat_sram #(parameter integer MUT=0, REGIONAL=0, REPLICATE=0)(
 input wire ck,ck_mem,rst_n,clear,
 input wire[7:0]write_v,input wire[71:0]write_element,input wire[255:0]write_data,
 input wire[1151:0]element_copies,input wire[127:0]valid_copies,
 input wire read_v,input wire[4:0]read_beat,output wire[511:0]read_data
);
 reg[2:0]owner[0:511];
 wire[2:0]owner_n[0:511];
 genvar e,w,l;
 generate for(e=0;e<512;e=e+1)begin:g_owner
  wire[7:0]hit;
  for(w=0;w<8;w=w+1)begin:g_hit
   assign hit[w]=(REPLICATE!=0)?(valid_copies[8*(e/32)+w]&&(element_copies[72*(e/32)+9*w+:9]==9'(e))):(write_v[w]&&(write_element[9*w+:9]==9'(e))&&!clear);
  end
  assign owner_n[e]=hit[7]?3'd7:hit[6]?3'd6:hit[5]?3'd5:hit[4]?3'd4:
                     hit[3]?3'd3:hit[2]?3'd2:hit[1]?3'd1:hit[0]?3'd0:owner[e];
  always @(posedge ck)owner[e]<=owner_n[e];
 end endgenerate
 wire[511:0]bank_data[0:7];
 (* keep = "true" *) reg[127:0]select_q;
 reg[7:0]bypass_v;reg[31:0]bypass_lane;reg[255:0]bypass_data;
 always @(posedge ck)begin
  bypass_data<=write_data;
  for(integer k=0;k<8;k=k+1)begin
   bypass_v[k]<=write_v[k]&&!clear&&(write_element[9*k+4+:5]==read_beat);
   bypass_lane[4*k+:4]<=write_element[9*k+:4];
  end
 end
 generate for(w=0;w<8;w=w+1)begin:g_writer
  wire[511:0]mask;
  for(l=0;l<16;l=l+1)begin:g_mask
   assign mask[32*l+:32]={32{write_element[9*w+:4]==4'(l)}};
   // One kept select drives only the 32 bits of one FP32 seat.
   always @(posedge ck)if(read_v)
    select_q[8*l+w]<=owner_n[16*read_beat+l]==3'((MUT==7)?((w+1)%8):w);
  end
  ot_sram_1r1w_32x512_m1 u_mem(.clk(REGIONAL?ck_mem:ck),.r_ce_in(read_v),.r_addr_in(read_beat),.rd_out(bank_data[w]),
   .w_ce_in(write_v[w]&&!clear),.w_addr_in(write_element[9*w+4+:5]),
   .wd_in({16{write_data[32*w+:32]}}),.w_mask_in(mask));
 end endgenerate
 generate for(l=0;l<16;l=l+1)begin:g_read
  wire[31:0]tree[0:8];assign tree[0]=32'd0;
  for(w=0;w<8;w=w+1)begin:g_gather
   wire[31:0]d=(bypass_v[w]&&bypass_lane[4*w+:4]==4'(l))?bypass_data[32*w+:32]:bank_data[w][32*l+:32];
   assign tree[w+1]=tree[w]|({32{select_q[8*l+w]}}&d);
  end
  assign read_data[32*l+:32]=tree[8];
 end endgenerate
endmodule
