// Opt-in local byte slices; no added operation edges.
`default_nettype none
(* keep_hierarchy="yes" *) module ot_hbm_svg_return_safe_pair_slice #(
 parameter integer J=0,W=16,MUT=0
)(input wire clk,rst_n,input wire [W-1:0] lo,hi,input wire [2:0] ordinal,
 output reg [W-1:0] data_out);
 reg [W-1:0] lo_q,hi_q;
 (* keep="true" *) reg [2:0] ord_q;
 wire pick_hi=ord_q[2]^(J<ord_q[1:0])^(MUT!=0);
 always @(posedge clk)ord_q<=ordinal;
 always @(posedge clk)begin lo_q<=lo;hi_q<=hi;data_out<=pick_hi?hi_q:lo_q;end
endmodule

module ot_hbm_svg_return_safe_pair #(parameter integer J=0,MUT=0)(
 input wire clk,rst_n,input wire [255:0] lo,hi,input wire [2:0] ordinal,input wire valid,
 output wire [255:0] data_out,output reg [2:0] ordinal_out,output reg valid_out);
 reg [2:0] ord_q;reg valid_q;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin valid_q<=0;valid_out<=0;end
  else begin valid_q<=valid;valid_out<=valid_q;end
 always @(posedge clk)begin ord_q<=ordinal;ordinal_out<=ord_q;end
 genvar g;generate for(g=0;g<16;g=g+1)begin:g_slice
  (* keep_hierarchy="yes" *) ot_hbm_svg_return_safe_pair_slice #(.J(J),.MUT(MUT)) u_slice(
   .clk(clk),.rst_n(rst_n),.lo(lo[g*16+:16]),.hi(hi[g*16+:16]),
   .ordinal(ordinal),.data_out(data_out[g*16+:16]));
 end endgenerate
endmodule

// Each slice is an ACTUAL four-slot ring, never a four-flop shift chain.
(* keep_hierarchy="yes" *) module ot_hbm_svg_return_safe_ring_slice #(
 parameter integer W=16,MUT=0,HASVALID=0
)(input wire src_clk,src_rst_n,dst_clk,dst_rst_n,input wire [W-1:0] data_in,
 input wire valid_allow,output reg [W-1:0] data_out);
 wire sr,dr;
 ot_hbm_pair_reset_phase u_source_reset(.clk(src_clk),.rst_n(src_rst_n),.q(sr));
 ot_hbm_pair_reset_phase u_dest_reset(.clk(dst_clk),.rst_n(dst_rst_n),.q(dr));
 reg [W-1:0] slots[0:3];
 (* keep="true" *) reg [1:0] wp,rp;
 wire [1:0] ra=rp+(MUT!=0?2'd1:2'd0);
 always @(posedge src_clk or negedge sr)if(!sr)wp<=0;else wp<=wp+1'b1;
 always @(posedge dst_clk or negedge dr)if(!dr)rp<=3;else rp<=rp+1'b1;
 always @(posedge src_clk)slots[wp]<=data_in;
 generate if(HASVALID)begin:g_valid
  always @(posedge dst_clk)begin data_out[W-1:4]<=slots[ra][W-1:4];data_out[2:0]<=slots[ra][2:0];end
  always @(posedge dst_clk or negedge dr)
   if(!dr)data_out[3]<=0;else data_out[3]<=valid_allow&&slots[ra][3];
 end else begin:g_data
  always @(posedge dst_clk)data_out<=slots[ra];
 end endgenerate
endmodule

module ot_hbm_svg_return_safe_ring4 #(parameter integer MUT=0)(
 input wire src_clk,src_rst_n,dst_clk,dst_rst_n,src_raw_rst_n,dst_raw_rst_n,
 input wire [1:0] src_phase0,dst_phase0,
 input wire [255:0] data_in,input wire [2:0] ordinal_in,input wire valid_in,
 output wire [255:0] data_out,output wire [2:0] ordinal_out,output wire valid_out,
 output reg phase_fault);
 reg [2:0] src_phase,dst_phase,expected_q;
 reg [1:0] warm;
 wire [262:0] payload={src_phase,valid_in,ordinal_in,data_in};
 wire [262:0] landed;
 always @(posedge src_clk or negedge src_rst_n)
  if(!src_rst_n)src_phase<=0;else src_phase<=src_phase+1'b1;
 always @(posedge dst_clk or negedge dst_rst_n)begin
  if(!dst_rst_n)begin dst_phase<=7;expected_q<=7;warm<=0;phase_fault<=0;end
  else begin
   dst_phase<=dst_phase+1'b1;expected_q<=dst_phase;warm<={warm[0],1'b1};
   if(warm[1]&&landed[259]&&landed[262:260]!=expected_q)phase_fault<=1;
  end
 end
 genvar g;generate for(g=0;g<33;g=g+1)begin:g_slice
  localparam integer W=g==32?7:8;
  (* keep_hierarchy="yes" *) ot_hbm_svg_return_safe_ring_slice #(.W(W),.MUT(MUT),.HASVALID(g==32)) u_slice(
   .src_clk(src_clk),.src_rst_n(src_phase0[g%2]),.dst_clk(dst_clk),.dst_rst_n(dst_phase0[g%2]),
   .data_in(payload[g*8+:W]),.valid_allow(warm[0]),.data_out(landed[g*8+:W]));
 end endgenerate
 assign data_out=landed[255:0];assign ordinal_out=landed[258:256];
 assign valid_out=landed[259];
endmodule

`default_nettype wire
