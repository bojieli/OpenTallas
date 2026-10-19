// Opt-in seven-edge regional SVG return. Ordinary single-cycle timed crossings.
// No multicycle/false-path assumptions. Separate matched-frequency native roots.
`default_nettype none
module ot_hbm_svg_return_reset(input wire clk,rst_n,output wire landed_n);
 (* async_reg="true" *) reg [1:0] q;
 always @(posedge clk or negedge rst_n)if(!rst_n)q<=0;else q<={q[0],1'b1};
 assign landed_n=q[1];
endmodule

(* keep_hierarchy="yes" *) module ot_hbm_svg_return_pair_slice #(
 parameter integer J=0,W=16,MUT=0
)(input wire clk,rst_n,input wire [W-1:0] lo,hi,input wire [2:0] ordinal,
 output reg [W-1:0] data_out);
 reg [W-1:0] lo_q,hi_q;
 (* keep="true" *) reg [2:0] ord_q;
 wire pick_hi=ord_q[2]^(J<ord_q[1:0])^(MUT!=0);
 always @(posedge clk or negedge rst_n)if(!rst_n)ord_q<=0;else ord_q<=ordinal;
 always @(posedge clk)begin lo_q<=lo;hi_q<=hi;data_out<=pick_hi?hi_q:lo_q;end
endmodule

module ot_hbm_svg_return_pair #(parameter integer J=0,MUT=0)(
 input wire clk,rst_n,input wire [255:0] lo,hi,input wire [2:0] ordinal,input wire valid,
 output wire [255:0] data_out,output reg [2:0] ordinal_out,output reg valid_out);
 reg [2:0] ord_q;reg valid_q;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin ord_q<=0;ordinal_out<=0;valid_q<=0;valid_out<=0;end
  else begin ord_q<=ordinal;ordinal_out<=ord_q;valid_q<=valid;valid_out<=valid_q;end
 genvar g;generate for(g=0;g<16;g=g+1)begin:g_slice
  (* keep_hierarchy="yes" *) ot_hbm_svg_return_pair_slice #(.J(J),.MUT(MUT)) u_slice(
   .clk(clk),.rst_n(rst_n),.lo(lo[g*16+:16]),.hi(hi[g*16+:16]),
   .ordinal(ordinal),.data_out(data_out[g*16+:16]));
 end endgenerate
endmodule

// Each slice is an ACTUAL four-slot ring, never a four-flop shift chain.
(* keep_hierarchy="yes" *) module ot_hbm_svg_return_ring_slice #(
 parameter integer W=16,MUT=0,HASVALID=0
)(input wire src_clk,src_rst_n,dst_clk,dst_rst_n,input wire [W-1:0] data_in,
 input wire valid_allow,output reg [W-1:0] data_out);
 reg [W-1:0] slots[0:3];
 (* keep="true" *) reg [1:0] wp,rp;
 wire [1:0] ra=rp+(MUT!=0?2'd1:2'd0);
 always @(posedge src_clk or negedge src_rst_n)if(!src_rst_n)wp<=0;else wp<=wp+1'b1;
 always @(posedge dst_clk or negedge dst_rst_n)if(!dst_rst_n)rp<=3;else rp<=rp+1'b1;
 always @(posedge src_clk)slots[wp]<=data_in;
 generate if(HASVALID)begin:g_valid
  always @(posedge dst_clk)begin data_out[W-1:4]<=slots[ra][W-1:4];data_out[2:0]<=slots[ra][2:0];end
  always @(posedge dst_clk or negedge dst_rst_n)
   if(!dst_rst_n)data_out[3]<=0;else data_out[3]<=valid_allow&&slots[ra][3];
 end else begin:g_data
  always @(posedge dst_clk)data_out<=slots[ra];
 end endgenerate
endmodule

module ot_hbm_svg_return_ring4 #(parameter integer MUT=0)(
 input wire src_clk,src_rst_n,dst_clk,dst_rst_n,
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
 genvar g;generate for(g=0;g<17;g=g+1)begin:g_slice
  localparam integer W=g==16?7:16;
  (* keep_hierarchy="yes" *) ot_hbm_svg_return_ring_slice #(.W(W),.MUT(MUT),.HASVALID(g==16)) u_slice(
   .src_clk(src_clk),.src_rst_n(src_rst_n),.dst_clk(dst_clk),.dst_rst_n(dst_rst_n),
   .data_in(payload[g*16+:W]),.valid_allow(warm[0]),.data_out(landed[g*16+:W]));
 end endgenerate
 assign data_out=landed[255:0];assign ordinal_out=landed[258:256];
 assign valid_out=landed[259];
endmodule

// One 16-bit slice in each of four lanes. Four kept controls each drive 16 muxes.
// Control copies use the corresponding pair ordinal, distributing pin fanout.
(* keep_hierarchy="yes" *) module ot_hbm_svg_return_rotate_slice #(parameter integer MUT=0)(
 input wire clk,input wire [63:0] data_in,input wire [11:0] ordinal_in,
 output wire [63:0] data_out);
 reg [15:0] pins[0:3],by2[0:3],by1[0:3];
 (* keep="true" *) reg [3:0] sel2,sel1,sel1_q;
 integer k;
 always @(posedge clk)begin
  for(k=0;k<4;k=k+1)begin
   pins[k]<=data_in[k*16+:16];
   sel2[k]<=ordinal_in[k*3+1];sel1[k]<=ordinal_in[k*3];sel1_q[k]<=sel1[k];
   by2[k]<=sel2[k]?pins[(k+2)%4]:pins[k];
   by1[k]<=(sel1_q[k]^(MUT!=0))?by2[(k+1)%4]:by2[k];
  end
 end
 genvar g;generate for(g=0;g<4;g=g+1)begin:g_out
  assign data_out[g*16+:16]=by1[g];
 end endgenerate
endmodule

module ot_hbm_svg_return_cache #(parameter integer MUT=0)(
 input wire clk,rst_n,input wire [1023:0] data_in,input wire [11:0] ordinal_in,
 input wire [3:0] valid_in,phase_fault_in,
 output wire [1023:0] data_out,output wire [2:0] ordinal_out,output reg valid_out,
 output reg fault);
 reg [11:0] ord_pin;reg [3:0] valid_pin,fault_pin;
 // Three-edge metadata alignment is an actual ring: write0/read2, then1/3,2/0.
 reg [3:0] meta_slots[0:3];reg [3:0] meta_out;
 reg [1:0] mwp,mrp,warm;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin ord_pin<=0;valid_pin<=0;fault_pin<=0;fault<=0;mwp<=0;mrp<=2;warm<=0;valid_out<=0;end
  else begin
   ord_pin<=ordinal_in;valid_pin<=valid_in;fault_pin<=phase_fault_in;
   if((|fault_pin)||((|valid_pin)&&
       (valid_pin!=4'b1111||ord_pin[2:0]!=ord_pin[5:3]||ord_pin[2:0]!=ord_pin[8:6]||ord_pin[2:0]!=ord_pin[11:9])))fault<=1;
   mwp<=mwp+1'b1;mrp<=mrp+1'b1;if(warm!=3)warm<=warm+1'b1;
   valid_out<=(warm>=2)&&meta_slots[mrp][0];
  end
 end
 always @(posedge clk)begin
  meta_slots[mwp]<={ordinal_in[2:0],&valid_in};meta_out<=meta_slots[mrp];
 end
 genvar g,k;generate for(g=0;g<16;g=g+1)begin:g_slice
  wire [63:0] slice_in,slice_out;
  for(k=0;k<4;k=k+1)begin:g_lane
   assign slice_in[k*16+:16]=data_in[k*256+g*16+:16];
   assign data_out[k*256+g*16+:16]=slice_out[k*16+:16];
  end
  (* keep_hierarchy="yes" *) ot_hbm_svg_return_rotate_slice #(.MUT(MUT)) u_slice(
   .clk(clk),.data_in(slice_in),.ordinal_in(ordinal_in),.data_out(slice_out));
 end endgenerate
 assign ordinal_out=meta_out[3:1];
endmodule

// in_ordinal contains one local native copy per pair, not a shared distant root.
// Assert and release all reset pins together; source/cache clock phases are fixed.
module ot_hbm_svg_return_regional #(parameter integer MUT=0)(
 input wire [3:0] pair_clk,pair_rst_n,input wire cache_clk,cache_rst_n,
 input wire [2047:0] bank_data,input wire [11:0] in_ordinal,input wire [3:0] in_valid,
 output wire [1023:0] out_data,output wire [2:0] out_ordinal,output wire out_valid,fault);
 wire [3:0] prst;wire crst;
 wire [1023:0] landed_data;wire [11:0] landed_ord;wire [3:0] landed_valid,phase_fault;
 ot_hbm_svg_return_reset u_cache_reset(.clk(cache_clk),.rst_n(cache_rst_n),.landed_n(crst));
 genvar j;generate for(j=0;j<4;j=j+1)begin:g_pair
  wire [255:0] pd;wire [2:0] po;wire pv;
  ot_hbm_svg_return_reset u_reset(.clk(pair_clk[j]),.rst_n(pair_rst_n[j]),.landed_n(prst[j]));
  ot_hbm_svg_return_pair #(.J(j),.MUT(MUT==1&&j==0?1:0)) u_pair(
   .clk(pair_clk[j]),.rst_n(prst[j]),.lo(bank_data[j*256+:256]),.hi(bank_data[(j+4)*256+:256]),
   .ordinal(in_ordinal[j*3+:3]),.valid(in_valid[j]),.data_out(pd),.ordinal_out(po),.valid_out(pv));
  ot_hbm_svg_return_ring4 #(.MUT(MUT==3&&j==0?1:0)) u_ring(
   .src_clk(pair_clk[j]),.src_rst_n(prst[j]),.dst_clk(cache_clk),.dst_rst_n(crst),
   .data_in(pd),.ordinal_in(po),.valid_in(pv),.data_out(landed_data[j*256+:256]),
   .ordinal_out(landed_ord[j*3+:3]),.valid_out(landed_valid[j]),.phase_fault(phase_fault[j]));
 end endgenerate
 ot_hbm_svg_return_cache #(.MUT(MUT==2?1:0)) u_cache(
  .clk(cache_clk),.rst_n(crst),.data_in(landed_data),.ordinal_in(landed_ord),
  .valid_in(landed_valid),.phase_fault_in(phase_fault),.data_out(out_data),
  .ordinal_out(out_ordinal),.valid_out(out_valid),.fault(fault));
endmodule
`default_nettype wire
