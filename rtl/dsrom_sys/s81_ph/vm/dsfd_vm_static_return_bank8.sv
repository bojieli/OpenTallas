`timescale 1ns/1ps
`default_nettype none
// Eight banks j=LANE+4*k and eight slots s=LANE+4*q. Two parity buffers.
// prepare is exactly the release descriptor one edge early (rsched stage9).
// The completion token describes state AFTER this edge's release and arrivals.
// All four lane tokens are checked INSIDE every leaf: no free parent reduction.
// Native5 structural repair (measured native4 CTS: release_group[0] input ->12 levels
// -> completion/valid state, TT -79.8ps at 770): the E10 release STATE update uses the
// leaf's own registered copy of the stage9 prepare descriptor (the same compiled
// descriptor one edge early). The release_* pins only feed a shallow equality check
// (descriptor mismatch = sticky fault + suppressed release), never the slot state.
// Native5 also registers the schedule-fault check once before the sticky flag (measured native5 CTS: the 8-source
// slot-collision cone i_tag -> bad -> fault was the worst input path, -20/-38 ps): fault rises one stream edge after
// the offending edge. It is a diagnostic level only; it never gates data or stretches the schedule.
// DEFER_PEER=1 (used with PINREG): the cross-lane completeness of the four peer tokens is an ASSERTION, not a release
// gate (owner static-schedule rule): o_v follows the compiled release (minus a local descriptor mismatch), and the peer
// check runs one edge later on the registered tokens (a pin-registered token describes the group one edge later); an
// incomplete group at its compiled release is a sticky schedule fault, never a wait.
module dsfd_vm_static_return_bank8_core #(parameter integer DW=128, parameter integer LANE=0, parameter integer DEFER_PEER=0)(
 input wire ck,rst_n,
 input wire [7:0] i_v,input wire [63:0] i_tag,input wire [8*DW-1:0] i_data,
 input wire release_v,input wire [2:0] release_group,input wire [7:0] release_mask,
 input wire prepare_v,input wire [2:0] prepare_group,input wire [7:0] prepare_mask,
 input wire [47:0] peer_token,
 output reg [11:0] completion_token,
 output reg [7:0] o_v,output reg [8*DW-1:0] o_data,
 output reg [2:0] o_group,output reg fault
);
 reg [1:0] reset_release;
 always @(posedge ck or negedge rst_n)
  if(!rst_n)reset_release<=0;else reset_release<={reset_release[0],1'b1};
 wire rn=reset_release[1];
 reg [15:0] valid,used;wire [15:0] valid_n,occupied,prepare_ok;
 reg [2:0] groups[0:15];wire [2:0] groups_next[0:15];
 reg [DW-1:0] data[0:15];
 wire [15:0] hit;
 reg [7:0] prepared_mask;
 reg prepared_v;reg [2:0] prepared_group;
 wire rel_mismatch=(release_v!=prepared_v) || (release_v && (release_group!=prepared_group || release_mask!=prepared_mask));
 reg [7:0] prepared_parity;
 reg chk_v;reg [2:0] chk_group;
 reg bad,complete,bad_q;reg [7:0] prepare_complete;
 integer j,idx,s,p;
 always @*begin
  complete=1;
  for(p=0;p<4;p=p+1)begin
`ifdef OT_VM_RETURN_BANK8_MUT_LOCAL
   if(p==LANE)
`endif
   if(!peer_token[12*p+11] || peer_token[12*p+8+:3]!=(DEFER_PEER!=0 ? chk_group : prepared_group) || peer_token[12*p+:8]!=8'hff)complete=0;
  end
  used=0;bad=0;
  if(DEFER_PEER!=0)begin
   if(chk_v && !complete)bad=1;
   complete=!rel_mismatch;
  end else begin
   if(rel_mismatch)complete=0;
   if(release_v)begin
    if(!complete)bad=1;
   end
  end
  if(rel_mismatch)bad=1;
  for(j=0;j<8;j=j+1)if(i_v[j])begin
   idx=i_tag[8*j+2+:4];
   if(i_tag[8*j+:2]!=2'(LANE))bad=1;
   if(occupied[idx] || used[idx])bad=1;
   used[idx]=1;
  end
  prepare_complete=8'hff;
  for(s=0;s<8;s=s+1)if(prepare_mask[s])begin
   prepare_complete[s]=prepare_group[0] ? prepare_ok[8+s] : prepare_ok[s];
  end
 end
 always @(posedge ck or negedge rn)begin
  if(!rn)begin valid<=0;o_v<=0;fault<=0;bad_q<=0;o_group<=0;completion_token<=0;prepared_mask<=0;prepared_v<=0;prepared_group<=0;chk_v<=0;chk_group<=0;end
  else begin
   valid<=valid_n;bad_q<=bad;fault<=fault|bad_q;
   o_v<=release_v && complete ? release_mask : 8'b0;
   o_group<=prepared_group;
   completion_token<={prepare_v,prepare_group,prepare_complete};
   prepared_mask<=prepare_mask;prepared_v<=prepare_v;prepared_group<=prepare_group;
   chk_v<=release_v;chk_group<=prepared_group;
  end
 end
 // Eight genuinely separate row controls: conditional mask enables prevent
 // synthesis from merging the parity registers. Each drives one128b row.
 // Data on invalid rows is unobserved; only valid release rows are sampled.
 genvar row;
 generate for(row=0;row<8;row=row+1)begin:row_output
  always @(posedge ck)begin
   if(prepare_v && prepare_mask[row])prepared_parity[row]<=prepare_group[0];
   if(completion_token[11] && prepared_mask[row])
    o_data[DW*row+:DW]<=data[8*prepared_parity[row]+row];
  end
 end endgenerate
 genvar g;
 generate for(g=0;g<16;g=g+1)begin:slot_store
  reg h,incoming_valid;reg [DW-1:0] nd;reg [2:0] ng;integer k;
  always @*begin
   h=0;incoming_valid=0;nd=0;ng=0;
   for(k=0;k<8;k=k+1)if(i_v[k] && i_tag[8*k+2+:4]==4'(g))incoming_valid=1;
   for(k=0;k<8;k=k+1)if(i_v[k] && i_tag[8*k+:6]=={4'(g),2'(LANE)})begin
    h=1;nd=nd|i_data[DW*k+:DW];ng=ng|i_tag[8*k+5+:3];
   end
  end
  assign hit[g]=h;
  assign occupied[g]=valid[g] && !(prepared_v && prepared_group[0]==(g/8) && prepared_mask[g%8]);
  assign valid_n[g]=occupied[g] || incoming_valid;
  assign prepare_ok[g]=valid_n[g] && groups_next[g]==prepare_group;
  assign groups_next[g]=h ? ng : groups[g];
  always @(posedge ck)if(h)begin data[g]<=nd;groups[g]<=ng;end
 end endgenerate
 initial if(LANE<0 || LANE>3)$error("LANE must be0..3");
endmodule
// PINREG=1 (READ_PIPE 4, L16; native pin audit 2026-10-15: every functional input of the r6 lanes failed capture,
// 490-507 ps on ~1168 pins): every input incl. the peer tokens is a pin register, so the lane (arrivals, prepare,
// release, peer tokens) runs one edge later uniformly: release_q[e] meets peer_q[e] = token(prepare_q[e-1]) exactly as
// before; only o_v / o_data / o_group / fault / completion_token move +1 edge.  Hard masters _l<k>_p.
module dsfd_vm_static_return_bank8 #(parameter integer DW=128, parameter integer LANE=0, parameter integer PINREG=0)(
 input wire ck,rst_n,
 input wire [7:0] i_v,input wire [63:0] i_tag,input wire [8*DW-1:0] i_data,
 input wire release_v,input wire [2:0] release_group,input wire [7:0] release_mask,
 input wire prepare_v,input wire [2:0] prepare_group,input wire [7:0] prepare_mask,
 input wire [47:0] peer_token,
 output wire [11:0] completion_token,
 output wire [7:0] o_v,output wire [8*DW-1:0] o_data,
 output wire [2:0] o_group,output wire fault
);
 wire [7:0] v;wire [63:0] t;wire [8*DW-1:0] d;wire rv,pv;wire [2:0] rg,pg;wire [7:0] rm,pm;wire [47:0] pt;
 generate if(PINREG!=0)begin:g_pin
  reg [1:0] rr;always @(posedge ck or negedge rst_n)if(!rst_n)rr<=0;else rr<={rr[0],1'b1};
  reg [7:0] q_v;reg [63:0] q_t;reg [8*DW-1:0] q_d;reg q_rv,q_pv;reg [2:0] q_rg,q_pg;reg [7:0] q_rm,q_pm;reg [47:0] q_pt;
  always @(posedge ck or negedge rr[1])if(!rr[1])begin q_v<=0;q_rv<=0;q_pv<=0;q_pt<=0;end
   else begin q_v<=i_v;q_rv<=release_v;q_pv<=prepare_v;q_pt<=peer_token;end
  always @(posedge ck)begin q_t<=i_tag;q_d<=i_data;q_rg<=release_group;q_rm<=release_mask;q_pg<=prepare_group;q_pm<=prepare_mask;end
`ifdef OT_VM_RETURN_BANK8_MUT_PINSKEW
  assign v=q_v;assign t=q_t;assign d=q_d;assign rv=release_v;   // DUT mutant: release bypasses its pin register
`else
  assign v=q_v;assign t=q_t;assign d=q_d;assign rv=q_rv;
`endif
 assign rg=q_rg;assign rm=q_rm;assign pv=q_pv;assign pg=q_pg;assign pm=q_pm;assign pt=q_pt;
 end else begin:g_nopin
  assign v=i_v;assign t=i_tag;assign d=i_data;assign rv=release_v;assign rg=release_group;assign rm=release_mask;
  assign pv=prepare_v;assign pg=prepare_group;assign pm=prepare_mask;assign pt=peer_token;
 end endgenerate
 dsfd_vm_static_return_bank8_core #(.DW(DW),.LANE(LANE),.DEFER_PEER(PINREG)) u_core(.ck(ck),.rst_n(rst_n),.i_v(v),.i_tag(t),.i_data(d),
  .release_v(rv),.release_group(rg),.release_mask(rm),.prepare_v(pv),.prepare_group(pg),.prepare_mask(pm),.peer_token(pt),
  .completion_token(completion_token),.o_v(o_v),.o_data(o_data),.o_group(o_group),.fault(fault));
endmodule
`default_nettype wire
