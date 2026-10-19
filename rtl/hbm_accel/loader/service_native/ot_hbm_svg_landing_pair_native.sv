// Opt-in four-actual-SRAM leaf. Entire selected return ring and output Q are local.
// Native read E1/SRAM E2/readQ E3/pair pins E4/select E5/ring E6/returnQ E7.
`default_nettype none
module ot_hbm_svg_group_read_meta #(parameter integer MUT=0)(
 input wire clk,rst_n,input wire [2:0] ordinal,input wire group_valid,
 output wire [2:0] ordinal_out,output reg valid_out);
 reg [3:0] slots[0:3];reg [2:0] ord_out;
 reg [1:0] wp,rp,warm;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin wp<=0;rp<=MUT!=0?3:2;warm<=0;valid_out<=0;end
  else begin
   wp<=wp+1'b1;rp<=rp+1'b1;if(warm!=3)warm<=warm+1'b1;
   valid_out<=(warm>=2)&&slots[rp][0];
  end
 end
 // Unconditional group metadata: read_v and partial masks never gate this ring.
 always @(posedge clk)begin slots[wp]<={ordinal,group_valid};ord_out<=slots[rp][3:1];end
 assign ordinal_out=ord_out;
endmodule

module ot_hbm_svg_landing_pair_native #(parameter integer J=0,MUT=0,FIFOMUT=0)(
 input wire pair_hbm_clk,pair_hbm_rst_n,pair_clk,pair_rst_n,return_clk,return_rst_n,
 input wire [1:0] in_v,input wire [569:0] in_data,output wire [1:0] in_ready,overflow,
 input wire reserve_v,input wire [1:0] reserve_bank,input wire [15:0] reserve_epoch,
 input wire [11:0] reserve_total,input wire stop,
 input wire [1:0] read_v,input wire [3:0] read_bank,input wire [11:0] read_row,
 input wire [2:0] ordinal,input wire group_valid,
 output wire [1:0] complete_v,output wire [3:0] complete_bank,output wire [1:0] bank_fault,
 output wire [255:0] out_data,output wire [2:0] out_ordinal,output wire out_valid,phase_fault
);
 wire prst,rrst;
 ot_hbm_svg_return_reset u_pair_reset(.clk(pair_clk),.rst_n(pair_rst_n),.landed_n(prst));
 ot_hbm_svg_return_reset u_return_reset(.clk(return_clk),.rst_n(return_rst_n),.landed_n(rrst));
 wire [511:0] native_data;
 genvar b;generate for(b=0;b<2;b=b+1)begin:g_bank
  // Native banks each own their HBM/pair reset landing. Feed RAW reset here,
  // not prst, so their landing remains two stages rather than four.
  ot_hbm_svc_sm8_landing_boundary #(.BANK(3'(J+4*b)),.LBANKS(4),.RESPONSE_DEPTH(8),.FMUT(FIFOMUT)) u_bank(
   .hbm_clk(pair_hbm_clk),.hbm_rst_n(pair_hbm_rst_n),.stream_clk(pair_clk),.stream_rst_n(pair_rst_n),
   .in_v(in_v[b]),.in_ready(in_ready[b]),.in_data(in_data[b*285+:285]),.overflow(overflow[b]),
   .reserve_v(reserve_v),.reserve_bank(reserve_bank),.reserve_epoch(reserve_epoch),.reserve_total(reserve_total),.stop(stop),
   .complete_v(complete_v[b]),.complete_bank(complete_bank[b*2+:2]),.fault(bank_fault[b]),
   .read_v(read_v[b]),.read_bank(read_bank[b*2+:2]),.read_row(read_row[b*6+:6]),.read_data(native_data[b*256+:256]));
 end endgenerate
 wire [2:0] meta_ord;wire meta_valid;
 ot_hbm_svg_group_read_meta #(.MUT(MUT==2?1:0)) u_read_meta(
  .clk(pair_clk),.rst_n(prst),.ordinal(ordinal),.group_valid(group_valid),.ordinal_out(meta_ord),.valid_out(meta_valid));
 wire [255:0] selected;wire [2:0] selected_ord;wire selected_valid;
 ot_hbm_svg_return_pair #(.J(J),.MUT(MUT==1?1:0)) u_pair(
  .clk(pair_clk),.rst_n(prst),.lo(native_data[255:0]),.hi(native_data[511:256]),
  .ordinal(meta_ord),.valid(meta_valid),.data_out(selected),.ordinal_out(selected_ord),.valid_out(selected_valid));
 // rp/read mux/registered return Q belong INSIDE this source leaf. No select
 // feedback or combinational data/fault pin is exported across the hard face.
 ot_hbm_svg_return_ring4 #(.MUT(MUT==3?1:0)) u_ring(
  .src_clk(pair_clk),.src_rst_n(prst),.dst_clk(return_clk),.dst_rst_n(rrst),
  .data_in(selected),.ordinal_in(selected_ord),.valid_in(selected_valid),
  .data_out(out_data),.ordinal_out(out_ordinal),.valid_out(out_valid),.phase_fault(phase_fault));
endmodule
`default_nettype wire
