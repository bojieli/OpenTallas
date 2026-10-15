`timescale 1ns/1ps
`default_nettype none
// Eight banks j=LANE+4*k and eight slots s=LANE+4*q. Two parity buffers.
// prepare is exactly the release descriptor one edge early (rsched stage9).
// The completion token describes state AFTER this edge's release and arrivals.
// All four lane tokens are checked INSIDE every leaf: no free parent reduction.
module dsfd_vm_static_return_bank8 #(parameter integer DW=128, parameter integer LANE=0)(
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
 reg [7:0] prepared_parity;
 reg bad,complete;reg [7:0] prepare_complete;
 integer j,idx,s,p;
 always @*begin
  complete=1;
  for(p=0;p<4;p=p+1)begin
`ifdef OT_VM_RETURN_BANK8_MUT_LOCAL
   if(p==LANE)
`endif
   if(!peer_token[12*p+11] || peer_token[12*p+8+:3]!=release_group || peer_token[12*p+:8]!=8'hff)complete=0;
  end
  if(prepared_mask!=release_mask)complete=0;
  used=0;bad=0;
  if(release_v)begin
   if(!complete)bad=1;
  end
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
  if(!rn)begin valid<=0;o_v<=0;fault<=0;o_group<=0;completion_token<=0;prepared_mask<=0;end
  else begin
   valid<=valid_n;fault<=fault|bad;
   o_v<=release_v && complete ? release_mask : 8'b0;
   o_group<=release_group;
   completion_token<={prepare_v,prepare_group,prepare_complete};
   prepared_mask<=prepare_mask;
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
  assign occupied[g]=valid[g] && !(release_v && release_group[0]==(g/8) && release_mask[g%8]);
  assign valid_n[g]=occupied[g] || incoming_valid;
  assign prepare_ok[g]=valid_n[g] && groups_next[g]==prepare_group;
  assign groups_next[g]=h ? ng : groups[g];
  always @(posedge ck)if(h)begin data[g]<=nd;groups[g]<=ng;end
 end endgenerate
 initial if(LANE<0 || LANE>3)$error("LANE must be0..3");
endmodule
`default_nettype wire
