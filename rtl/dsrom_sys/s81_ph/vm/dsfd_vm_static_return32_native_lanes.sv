`timescale 1ns/1ps
`default_nettype none
// Wires only: independent clocks, statically partitioned bank records/slots.
// Faults and groups stay per-leaf for the parent's actual registered fault tree.
module dsfd_vm_static_return32_native_lanes(
 input wire [3:0] ck,input wire [3:0] rst_n,
 input wire [31:0] i_v,input wire [255:0] i_tag,input wire [4096-1:0] i_data,
 input wire release_v,input wire [2:0] release_group,input wire [31:0] release_mask,
 input wire prepare_v,input wire [2:0] prepare_group,input wire [31:0] prepare_mask,
 output wire [31:0] o_v,output wire [4096-1:0] o_data,
 output wire [11:0] o_group,output wire [3:0] fault
);
 wire [19:0] tokens;
 genvar l,k;
 generate for(l=0;l<4;l=l+1)begin:lane
  wire [7:0] iv,rm,pm,ov;wire [63:0] it;wire [1024-1:0] id,od;
  for(k=0;k<8;k=k+1)begin:pin
   assign iv[k]=i_v[l+4*k];assign it[8*k+:8]=i_tag[8*(l+4*k)+:8];
   assign id[128*k+:128]=i_data[128*(l+4*k)+:128];
   assign rm[k]=release_mask[l+4*k];assign pm[k]=prepare_mask[l+4*k];
   assign o_v[l+4*k]=ov[k];assign o_data[128*(l+4*k)+:128]=od[128*k+:128];
  end
  if(l==0)begin:profile0
   dsfd_vm_static_return_bank8_l0 u(
   .ck(ck[l]),.rst_n(rst_n[l]),.i_v(iv),.i_tag(it),.i_data(id),
   .release_v(release_v),.release_group(release_group),.release_mask(rm),
   .prepare_v(prepare_v),.prepare_group(prepare_group),.prepare_mask(pm),
   .peer_token(tokens),.completion_token(tokens[5*l+:5]),.o_v(ov),.o_data(od),
   .o_group(o_group[3*l+:3]),.fault(fault[l]));
  end
  if(l==1)begin:profile1
   dsfd_vm_static_return_bank8_l1 u(
   .ck(ck[l]),.rst_n(rst_n[l]),.i_v(iv),.i_tag(it),.i_data(id),
   .release_v(release_v),.release_group(release_group),.release_mask(rm),
   .prepare_v(prepare_v),.prepare_group(prepare_group),.prepare_mask(pm),
   .peer_token(tokens),.completion_token(tokens[5*l+:5]),.o_v(ov),.o_data(od),
   .o_group(o_group[3*l+:3]),.fault(fault[l]));
  end
  if(l==2)begin:profile2
   dsfd_vm_static_return_bank8_l2 u(
   .ck(ck[l]),.rst_n(rst_n[l]),.i_v(iv),.i_tag(it),.i_data(id),
   .release_v(release_v),.release_group(release_group),.release_mask(rm),
   .prepare_v(prepare_v),.prepare_group(prepare_group),.prepare_mask(pm),
   .peer_token(tokens),.completion_token(tokens[5*l+:5]),.o_v(ov),.o_data(od),
   .o_group(o_group[3*l+:3]),.fault(fault[l]));
  end
  if(l==3)begin:profile3
   dsfd_vm_static_return_bank8_l3 u(
   .ck(ck[l]),.rst_n(rst_n[l]),.i_v(iv),.i_tag(it),.i_data(id),
   .release_v(release_v),.release_group(release_group),.release_mask(rm),
   .prepare_v(prepare_v),.prepare_group(prepare_group),.prepare_mask(pm),
   .peer_token(tokens),.completion_token(tokens[5*l+:5]),.o_v(ov),.o_data(od),
   .o_group(o_group[3*l+:3]),.fault(fault[l]));
  end

 end endgenerate
endmodule
`default_nettype wire
