`timescale 1ns/1ps
// S81 VM A2-F: field-major write front (S-VM, 2026-10-15). Isolated candidate, no production adoption.
//
// A2 (area_a2_controlled.sv) broadcasts every slice payload (53 sources x 128 b = 6,784 b) to four quarter fronts
// (bank groups q = bank/8), each holding eight 16-bit data stripes + one metadata stripe as SEPARATE leaves.  The four
// quarter copies of stripe k all receive the SAME 848 input bits (field k = bits 16k..16k+15 of every source), so the
// 6,784-bit trunk has to cross all four quarter fronts on parent (over-the-leaf) metal: 0.40 of every full-width line
// of the VM.  A2-F regroups the same logic by FIELD instead of by quarter:
//   * s81_a2f_field16 (slice x, field k): ONE leaf = the four quarter stripes of field k sharing one input pipeline
//     (d0/d1/d2) -- the 848-bit fan-out to the four bank groups now lives inside the leaf on its own low metal, and
//     the leaf sits directly over the payload's field-k pins; only the drained records (one 16-bit word per bank per
//     cycle, 4 x 128 b) leave it toward the storage;
//   * s81_a2f_meta26 (slice x): the four quarter metadata stripes, shared 1,378-bit input pipeline;
//   * s81_a2f_control4 (slice x): the four quarter controllers sharing the pin registers and the 53-source lane
//     (prefix-count) logic, which never depended on the quarter; per-quarter ID / drain / fault outputs kept;
//   * s81_a2f_fault_join4 (slice x): the four quarter fault joins, per-quarter outputs kept.
// Every register stage, edge and fault of A2 is kept (cycle-exact: source sample P -> registered capture P+6+lane), so
// the compiler profile, the 128 real SRAMs, all 53 sources and the 3 capture slots are unchanged.  Proof:
// area_a2f_equiv_gate.py drives A2 and A2-F with the same stimulus and compares every output on every edge.
`default_nettype none

module s81_a2f_field #(parameter integer NSRC=53, W=16, NQ=4)(
 input wire ck,rst_n,input wire [W*NSRC-1:0] i_data,
 input wire [NQ*168-1:0] i_sel,input wire [NQ*8-1:0] i_drain_v,input wire [NQ*16-1:0] i_drain_slot,
 output reg [NQ*8-1:0] o_v,output reg [NQ*8*W-1:0] o_data,output reg [NQ-1:0] fault
);
 reg rst_pin_q;reg [1:0] rr;wire rn;
 always @(posedge ck) rst_pin_q<=rst_n;
 always @(posedge ck) if(!rst_pin_q)rr<=0;else rr<={rr[0],1'b1};
`ifdef S81_A2F_MUT_HELD_RESET
 assign rn=1'b1;
`else
 assign rn=rr[1];
`endif
 reg rn_pin_d;
 // ONE shared input pipeline (was one copy per quarter stripe)
 reg [W*NSRC-1:0] d0,d1,d2;
 always @(posedge ck)begin rn_pin_d<=rn;d0<=i_data;d1<=d0;d2<=d1;end
 genvar q;
 generate for(q=0;q<NQ;q=q+1)begin:quarter
  reg [167:0] raw_sq;wire [167:0] sq=raw_sq & {168{rn_pin_d}};
  reg [7:0] raw_dv;wire [7:0] dv=raw_dv & {8{rn_pin_d}};reg [15:0] ds;reg [23:0] cv,valid;
  reg [W-1:0] chosen[0:23],storage[0:23];
  reg [24*W-1:0] muxed;reg [23:0] hits;reg bad;reg [23:0] vn;
  integer g,s,b,c;
  always @(posedge ck)begin
`ifdef S81_A2F_MUT_SEL_SWAP
   raw_sq<=i_sel[168*((q+1)%NQ)+:168];
`else
   raw_sq<=i_sel[168*q+:168];
`endif
   raw_dv<=i_drain_v[8*q+:8];ds<=i_drain_slot[16*q+:16];
  end
  always @(posedge ck)if(!rn)cv<=0;else cv<=hits;
  always @*begin
   muxed=0;hits=0;
   for(g=0;g<24;g=g+1)for(s=0;s<NSRC;s=s+1)if(sq[g*7+6] && sq[g*7+:6]==s)begin
    hits[g]=1;
`ifdef S81_A2F_MUT_STAGE
    muxed[g*W+:W]=muxed[g*W+:W]|d1[s*W+:W];
`else
    muxed[g*W+:W]=muxed[g*W+:W]|d2[s*W+:W];
`endif
   end
  end
  always @(posedge ck)begin
   for(integer k=0;k<24;k=k+1)begin
    chosen[k]<=muxed[k*W+:W];
    if(cv[k])storage[k]<=chosen[k];
   end
   for(integer k=0;k<8;k=k+1)begin
    o_data[(q*8+k)*W+:W]<=0;
    for(integer l=0;l<3;l=l+1)if(ds[2*k+:2]==l)o_data[(q*8+k)*W+:W]<=storage[3*k+l];
   end
`ifdef S81_A2F_MUT_DATA
   if(q==1)o_data[(q*8)*W]<=~storage[ds[1:0]][0];
`endif
  end
  always @*begin
   vn=valid;bad=0;
   for(b=0;b<8;b=b+1)if(dv[b])begin
    if(ds[2*b+:2]>=3)bad=1;
    else begin if(!valid[3*b+ds[2*b+:2]])bad=1;vn[3*b+ds[2*b+:2]]=0;end
   end
   for(c=0;c<24;c=c+1)if(cv[c])begin
    if(vn[c])bad=1;vn[c]=1;
   end
  end
  always @(posedge ck)if(!rn)begin valid<=0;fault[q]<=0;o_v[8*q+:8]<=0;end
  else begin
   valid<=vn;fault[q]<=fault[q]|bad;
   for(integer k=0;k<8;k=k+1)o_v[8*q+k]<=dv[k] && ds[2*k+:2]<3 && valid[3*k+ds[2*k+:2]];
  end
 end endgenerate
endmodule

// Four quarter controllers of one slice.  Pin registers, reset release, epoch check and the 53-source lane count are
// quarter independent and shared; ID formation, drain history and the sticky fault stay per quarter (BASE = 8q).
module s81_a2f_control #(parameter integer NSRC=53)(
 input wire ck_control,rst_n,
 input wire [NSRC-1:0] src_v,input wire [8*NSRC-1:0] src_bank,
 input wire [2:0] header_epoch,input wire [11:0] payload_epoch,
 output reg [4*168-1:0] ids,output reg [31:0] dr_v,output reg [63:0] dr_s,output reg [3:0] fault
);
 reg rst_pin_q;reg [1:0] rr;
 always @(posedge ck_control) rst_pin_q<=rst_n;
 always @(posedge ck_control)if(!rst_pin_q)rr<=0;else rr<={rr[0],1'b1};
`ifdef S81_A2F_MUT_HELD_RESET
 wire rn=1'b1;
`else
 wire rn=rr[1];
`endif
 reg [2:0] control_epoch,own_epoch_q,header_pin;
 reg [11:0] payload_pin;
 always @(posedge ck_control)begin
  header_pin<=header_epoch;payload_pin<=payload_epoch;own_epoch_q<=control_epoch;
  if(!rn)control_epoch<=0;else control_epoch<=control_epoch+3'd1;
 end
 wire phase_bad=(header_pin!=own_epoch_q) ||
   (payload_pin[2:0]!=own_epoch_q) || (payload_pin[5:3]!=own_epoch_q) ||
   (payload_pin[8:6]!=own_epoch_q) || (payload_pin[11:9]!=own_epoch_q);
 reg [2*NSRC-1:0] lane;reg [NSRC-1:0] lv;
 function automatic [1:0] sat3(input [1:0] a, input [1:0] b);
  reg [2:0] t; begin t = a + b; sat3 = t[2] ? 2'd3 : t[1:0]; end
 endfunction
 localparam integer NP = 64;
 reg rn_pin_d;
 reg [NSRC-1:0] raw_src_v;wire [NSRC-1:0] s_v=raw_src_v & {NSRC{rn_pin_d}}; reg [8*NSRC-1:0] s_bank;
 always @(posedge ck_control) begin
  s_bank <= src_bank;
  raw_src_v <= src_v; rn_pin_d <= rn;
 end
 reg [NSRC-1:0] lane_v_d; reg [2*NSRC-1:0] lane_d; reg lane_bad_d;
 always @* begin : p_lane integer c, d, w, k; reg [4:0] bc, bd; reg [1:0] t [0:NP-1]; reg [1:0] n;
  lane_bad_d = 1'b0;
  for (c = 0; c < NSRC; c = c + 1) begin
   bc = s_bank[8*c +: 5] ^ {s_bank[8*c+5 +: 3], 2'b00};
   for (d = 0; d < NP; d = d + 1) begin
    t[d] = 2'd0;
    if (d < c) begin
     bd = s_bank[8*d +: 5] ^ {s_bank[8*d+5 +: 3], 2'b00};
     t[d] = {1'b0, s_v[d] && bd == bc};
    end
   end
   for (w = NP / 2; w >= 1; w = w / 2)
    for (k = 0; k < w; k = k + 1) t[k] = sat3(t[2*k], t[2*k+1]);
   n = t[0];
   lane_d[2*c +: 2] = n;
   lane_v_d[c] = s_v[c] && n != 2'd3;
   if (s_v[c] && n == 2'd3) lane_bad_d = 1'b1;
  end
 end
 reg [8*NSRC-1:0] bank_d;
 reg lane_bad;
 always @(posedge ck_control)begin
  bank_d<=s_bank;lane<=lane_d;
  if(!rn)begin lv<=0;lane_bad<=0;end
  else begin lv<=lane_v_d;lane_bad<=lane_bad_d;end
 end
 genvar q;
 generate for(q=0;q<4;q=q+1)begin:quarter
  localparam integer BASE=8*q;
  reg [167:0] id_d;reg [23:0] id_valid;
  integer g,c;reg [4:0] bc;
  always @*begin
   id_d=0;id_valid=0;bc=0;
   for(g=0;g<24;g=g+1)for(c=0;c<NSRC;c=c+1)begin
    bc=bank_d[8*c+:5]^{bank_d[8*c+5+:3],2'b00};
`ifdef S81_A2F_MUT_BASE
    if(lv[c] && bc==((BASE+8)%32)+g/3 && lane[2*c+:2]==g%3)begin
`else
    if(lv[c] && bc==BASE+g/3 && lane[2*c+:2]==g%3)begin
`endif
     id_d[g*7+:6]=c;id_d[g*7+6]=1;
    end
   end
   for(g=0;g<24;g=g+1)id_valid[g]=ids[168*q+g*7+6];
  end
  always @(posedge ck_control)if(!rn)ids[168*q+:168]<=0;else ids[168*q+:168]<=id_d;
  reg [23:0] h0,h1,h2;
  reg [7:0] drain_v_d;reg [15:0] drain_s_d;reg drain_bad;
  integer b;reg l0,l1,l2;
  always @*begin
   drain_v_d=0;drain_s_d=0;drain_bad=0;l0=0;l1=0;l2=0;
   for(b=0;b<8;b=b+1)begin
    l0=h0[3*b];l1=h1[3*b+1];l2=h2[3*b+2];
    drain_v_d[b]=l0|l1|l2;
    drain_s_d[2*b+:2]=l0?0:l1?1:2;
    if((l0&&l1)||(l0&&l2)||(l1&&l2))drain_bad=1;
   end
  end
  always @(posedge ck_control)begin
   if(!rn)begin h0<=0;h1<=0;h2<=0;dr_v[8*q+:8]<=0;dr_s[16*q+:16]<=0;fault[q]<=0;end
   else begin
    h0<=id_valid;h1<=h0;h2<=h1;
    dr_v[8*q+:8]<=drain_v_d;dr_s[16*q+:16]<=drain_s_d;
    fault[q]<=fault[q]|lane_bad|drain_bad|phase_bad;
   end
  end
 end endgenerate
endmodule

module s81_a2f_fault_join4(
 input wire ck,rst_n,input wire [39:0] i_fault,output reg [3:0] fault
);
 reg rst_pin_q;reg [1:0] rr;reg [39:0] pin_fault;
 integer q;
 always @(posedge ck)begin
  rst_pin_q<=rst_n;
  if(!rst_pin_q)rr<=0;else rr<={rr[0],1'b1};
  pin_fault<=i_fault;
  for(q=0;q<4;q=q+1)if(!rr[1])fault[q]<=0;else fault[q]<=|pin_fault[10*q+:10];
 end
endmodule

// unique unparameterized hard-master names (one native view each)
module s81_a2f_field16(
 input wire ck,rst_n,input wire [847:0] i_data,input wire [671:0] i_sel,
 input wire [31:0] i_drain_v,input wire [63:0] i_drain_slot,
 output wire [31:0] o_v,output wire [511:0] o_data,output wire [3:0] fault
);
 s81_a2f_field #(.NSRC(53),.W(16)) u_impl(ck,rst_n,i_data,i_sel,i_drain_v,i_drain_slot,o_v,o_data,fault);
endmodule
module s81_a2f_meta26(
 input wire ck,rst_n,input wire [1377:0] i_data,input wire [671:0] i_sel,
 input wire [31:0] i_drain_v,input wire [63:0] i_drain_slot,
 output wire [31:0] o_v,output wire [831:0] o_data,output wire [3:0] fault
);
 s81_a2f_field #(.NSRC(53),.W(26)) u_impl(ck,rst_n,i_data,i_sel,i_drain_v,i_drain_slot,o_v,o_data,fault);
endmodule
module s81_a2f_control4(
 input wire ck_control,rst_n,
 input wire [52:0] src_v,input wire [423:0] src_bank,
 input wire [2:0] header_epoch,input wire [11:0] payload_epoch,
 output wire [671:0] ids,output wire [31:0] dr_v,output wire [63:0] dr_s,output wire [3:0] fault
);
 s81_a2f_control #(.NSRC(53)) u_impl(ck_control,rst_n,src_v,src_bank,header_epoch,payload_epoch,ids,dr_v,dr_s,fault);
endmodule

// One slice front: control4 + eight field16 + meta26 + fault_join4 (wires only).
module s81_a2f_slice(
 input wire ck_control,ck_meta,ck_fault,input wire [7:0] ck_data,
 input wire rst_control_n,rst_meta_n,rst_fault_n,input wire [7:0] rst_data_n,
 input wire [52:0] src_v,input wire [423:0] src_bank,
 input wire [2:0] header_epoch,input wire [11:0] payload_epoch,
 input wire [741:0] i_row,input wire [211:0] i_mask,input wire [423:0] i_tag,input wire [6783:0] i_data,
 output wire [31:0] o_v,output wire [447:0] o_row,output wire [127:0] o_mask,
 output wire [255:0] o_tag,output wire [4095:0] o_data,output wire [3:0] fault
);
 wire [671:0] ids;wire [31:0] dv;wire [63:0] ds;wire [3:0] fc,fm;wire [31:0] fd;
 wire [1377:0] mi;wire [831:0] mo;
 s81_a2f_control4 u_control(ck_control,rst_control_n,src_v,src_bank,header_epoch,payload_epoch,ids,dv,ds,fc);
 genvar s,k,q,b;
 generate for(s=0;s<53;s=s+1)begin:meta_in
  assign mi[26*s+:26]={i_tag[8*s+:8],i_mask[4*s+:4],i_row[14*s+:14]};
 end
 for(k=0;k<8;k=k+1)begin:field
  wire [847:0] di;wire [511:0] dout;wire [31:0] unused_v;
  for(s=0;s<53;s=s+1)begin:src assign di[16*s+:16]=i_data[128*s+16*k+:16];end
  s81_a2f_field16 u_data(ck_data[k],rst_data_n[k],di,ids,dv,ds,unused_v,dout,fd[4*k+:4]);
  for(q=0;q<4;q=q+1)begin:quarter
   for(b=0;b<8;b=b+1)begin:bank
    assign o_data[(q*8+b)*128+16*k+:16]=dout[(q*8+b)*16+:16];
   end
  end
 end
 for(q=0;q<4;q=q+1)begin:meta_out
  for(b=0;b<8;b=b+1)begin:bank
   assign {o_tag[(q*8+b)*8+:8],o_mask[(q*8+b)*4+:4],o_row[(q*8+b)*14+:14]}=mo[(q*8+b)*26+:26];
  end
 end endgenerate
 s81_a2f_meta26 u_meta(ck_meta,rst_meta_n,mi,ids,dv,ds,o_v,mo,fm);
 // join input order per quarter = A2 {fd[7:0], fm, fc}
 wire [39:0] fj;
 generate for(q=0;q<4;q=q+1)begin:fjq
  assign fj[10*q+:10]={fd[28+q],fd[24+q],fd[20+q],fd[16+q],fd[12+q],fd[8+q],fd[4+q],fd[q],fm[q],fc[q]};
 end endgenerate
 s81_a2f_fault_join4 u_fault(ck_fault,rst_fault_n,fj,fault);
endmodule

// Wires-only parent: five W0 roots (unchanged A2 header/payload leaves) and four slice fronts (11 roots each).
module s81_a2f_controlled(
 input wire ck_header,input wire [3:0] ck_payload,
 input wire [3:0] ck_control,ck_meta,ck_fault,input wire [31:0] ck_data,
 input wire rst_header_n,input wire [3:0] rst_payload_n,
 input wire [3:0] rst_control_n,rst_meta_n,rst_fault_n,input wire [31:0] rst_data_n,
 input wire [52:0] i_v,input wire [741:0] i_row,input wire [423:0] i_tag,
 input wire [847:0] i_mask,input wire [27135:0] i_data,
 output wire [127:0] o_slice_v,output wire [1791:0] o_slice_row,
 output wire [1023:0] o_slice_tag,output wire [511:0] o_mask,
 output wire [16383:0] o_data,output wire [15:0] o_fault
);
 wire [52:0] header_v;
 wire [741:0] header_row;wire [423:0] header_tag;
 wire [2:0] header_epoch;wire [11:0] payload_epoch;
 wire [423:0] src_bank;
 s81_a2_w0_header u_header(ck_header,rst_header_n,i_v,i_row,i_tag,header_v,header_row,header_tag,header_epoch);
 genvar s,x,q,b;
 generate for(s=0;s<53;s=s+1)begin:raw_bank
  assign src_bank[8*s+:8]=i_row[14*s+:8];
 end
 for(x=0;x<4;x=x+1)begin:payload
  wire [6783:0] di,dout;wire [211:0] mi,mout;
  for(s=0;s<53;s=s+1)begin:source
   assign di[128*s+:128]=i_data[512*s+128*x+:128];
   assign mi[4*s+:4]=i_mask[16*s+4*x+:4];
  end
  s81_a2_w0_payload u_payload(ck_payload[x],rst_payload_n[x],mi,di,mout,dout,payload_epoch[3*x+:3]);
  wire [31:0] vo;wire [447:0] ro;wire [127:0] mo;wire [255:0] to;wire [4095:0] dataout;
  s81_a2f_slice u_front(ck_control[x],ck_meta[x],ck_fault[x],ck_data[8*x+:8],
   rst_control_n[x],rst_meta_n[x],rst_fault_n[x],rst_data_n[8*x+:8],
   i_v,src_bank,header_epoch,payload_epoch,header_row,mout,header_tag,dout,
   vo,ro,mo,to,dataout,o_fault[4*x+:4]);
  for(q=0;q<4;q=q+1)begin:quarter
   for(b=0;b<8;b=b+1)begin:bank
    assign o_slice_v[x*32+q*8+b]=vo[q*8+b];
    assign o_slice_row[(x*32+q*8+b)*14+:14]=ro[(q*8+b)*14+:14];
    assign o_slice_tag[(x*32+q*8+b)*8+:8]=to[(q*8+b)*8+:8];
    assign o_mask[(q*8+b)*16+x*4+:4]=mo[(q*8+b)*4+:4];
    assign o_data[(q*8+b)*512+x*128+:128]=dataout[(q*8+b)*128+:128];
   end
  end
 end endgenerate
endmodule
`default_nettype wire
