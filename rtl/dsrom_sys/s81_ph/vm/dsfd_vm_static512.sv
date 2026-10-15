`timescale 1ns/1ps
// Four actual128b physical slices, unchanged16384x512 capacity.
// Wires-only parent: each leaf retains its own externally delivered clock.
// Compiler assigns every request and release edge; no ready/credits or waits.
// Per-slice valids and commit observations remain separate: this parent does
// not hide a late physical slice by pretending that a logical row is complete.
module dsfd_vm_static512(
 input wire [3:0] ck_rscatter,ck_wscatter,ck_return,
 input wire [127:0] ck_bank,input wire rst_n,
 input wire [31:0] rq_v,input wire [447:0] rq_row,input wire [255:0] rq_tag,
 input wire [31:0] wq_v,input wire [447:0] wq_row,input wire [511:0] wq_mask,
 input wire [16383:0] wq_data,input wire [255:0] wq_tag,
 input wire release_v,input wire [3:0] release_group,input wire [15:0] release_mask,
 output wire [63:0] group_v,output wire [8191:0] group_data,output wire [15:0] group_id,
 output wire [127:0] commit_v,output wire [1151:0] commit_addr,
 output wire [511:0] commit_mask,output wire [1023:0] commit_tag,
 output wire [11:0] fault
);
 genvar s,q;generate for(s=0;s<4;s=s+1)begin:slice
  wire [4095:0] wd,rd;wire [127:0] wm;wire [31:0] rv;wire [255:0] rt;
  wire [2047:0] gd;
  for(q=0;q<32;q=q+1)begin:write_rows
   assign wd[128*q+:128]=wq_data[512*q+128*s+:128];
   assign wm[4*q+:4]=wq_mask[16*q+4*s+:4];
  end
  dsfd_vm_static_slice128 u_slice(.ck_rscatter(ck_rscatter[s]),.ck_wscatter(ck_wscatter[s]),
   .ck_bank(ck_bank[32*s+:32]),.rst_n(rst_n),.rq_v(rq_v),.rq_row(rq_row),.rq_tag(rq_tag),
   .wq_v(wq_v),.wq_row(wq_row),.wq_mask(wm),.wq_data(wd),.wq_tag(wq_tag),
   .rs_v(rv),.rs_data(rd),.rs_tag(rt),.commit_v(commit_v[32*s+:32]),
   .commit_addr(commit_addr[288*s+:288]),.commit_mask(commit_mask[128*s+:128]),
   .commit_tag(commit_tag[256*s+:256]),.fault(fault[3*s+:2]));
  dsfd_vm_static_return u_return(.ck(ck_return[s]),.rst_n(rst_n),.i_v(rv),.i_tag(rt),.i_data(rd),
   .release_v(release_v),.release_group(release_group),.release_mask(release_mask),
   .o_v(group_v[16*s+:16]),.o_data(gd),.o_group(group_id[4*s+:4]),.fault(fault[3*s+2]));
  for(q=0;q<16;q=q+1)begin:read_rows
`ifdef OT_VM_512_MUT_SWAP_SLICES
   assign group_data[512*q+128*((s+1)%4)+:128]=gd[128*q+:128];
`else
   assign group_data[512*q+128*s+:128]=gd[128*q+:128];
`endif
  end
 end endgenerate
endmodule
