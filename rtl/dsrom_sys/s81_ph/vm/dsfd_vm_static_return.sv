`timescale 1ns/1ps
// Statically scheduled row-group assembly, one128b slice. No waiting/retry.
// Return tag={group4,slot4}. Two group buffers (group parity) permit adjacent
// groups on different physical bank/hop phases. The compiler supplies the exact
// release edge/mask. Missing, duplicate or overwritten rows are schedule faults.
// A row must arrive at least one edge before release, as registered timing needs.
module dsfd_vm_static_return #(parameter integer DW=128)(
 input wire ck,rst_n,
 input wire [31:0] i_v,
 input wire [255:0] i_tag,
 input wire [32*DW-1:0] i_data,
 input wire release_v,input wire [3:0] release_group,input wire [15:0] release_mask,
 output reg [15:0] o_v,output reg [16*DW-1:0] o_data,
 output reg [3:0] o_group,output reg fault
);
 reg [1:0] reset_release;
 always @(posedge ck or negedge rst_n)
  if(!rst_n)reset_release<=0;else reset_release<={reset_release[0],1'b1};
 wire rn=reset_release[1];

 reg [31:0] valid;
 reg [3:0] groups[0:31];reg [DW-1:0] data[0:31];
 reg [31:0] valid_n,used;
 reg bad,complete;integer j,idx,s;reg [7:0] tag;
 always @*begin
  valid_n=valid;used=0;bad=0;complete=1;
  if(release_v)begin
   for(s=0;s<16;s=s+1)if(release_mask[s])begin
    idx=16*release_group[0]+s;
    if(!valid[idx] || groups[idx]!=release_group)complete=0;
    valid_n[idx]=0;
   end
   if(!complete)bad=1;
  end
  for(j=0;j<32;j=j+1)if(i_v[j])begin
   tag=i_tag[8*j+:8];idx=16*tag[4]+tag[3:0];
   if(tag[1:0]!=(j%4))bad=1;
   if(valid_n[idx] || used[idx])bad=1;
   used[idx]=1;valid_n[idx]=1;
  end
 end
 always @(posedge ck or negedge rn)begin
  if(!rn)begin valid<=0;o_v<=0;fault<=0;o_group<=0;end
  else begin
   valid<=valid_n;fault<=fault|bad;
`ifdef OT_VM_RETURN_MUT_MASK
   o_v<=release_v ? release_mask : 16'd0; // mutant silently releases missing rows
`else
   o_v<=release_v && complete ? release_mask : 16'd0;
`endif
   o_group<=release_group;
  end
 end
 always @(posedge ck)begin : outputs integer q;
  if(release_v)for(q=0;q<16;q=q+1)o_data[DW*q+:DW]<=data[16*release_group[0]+q];
 end
 genvar g;
 generate for(g=0;g<32;g=g+1)begin:slot_store
  reg hit;reg [DW-1:0] next_data;reg [3:0] next_group;integer k,p;
  always @*begin
   hit=0;next_data=0;next_group=0;
   for(k=0;k<8;k=k+1)begin
    p=4*k+(g%4);
    if(i_v[p] && i_tag[8*p+:5]==g)begin
     hit=1;next_data=next_data|i_data[DW*p+:DW];next_group=next_group|i_tag[8*p+4+:4];
    end
   end
  end
  always @(posedge ck)if(hit)begin data[g]<=next_data;groups[g]<=next_group;end
 end endgenerate
endmodule
