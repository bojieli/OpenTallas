`timescale 1ns/1ps
// Real32-bank storage slice, fully static1R1W service. Four slices form512b rows.
// All clocks are stream1.2GHz; separate pins preserve die phi-R delivery to leaves.
// Compiler owns incoming32-record packet and bank reservations. Serial clients
// need explicit fixed-ratio ingress, not a credit adapter hidden in this parent.
module dsfd_vm_static_slice128(
 input wire ck_rscatter,ck_wscatter,input wire [31:0] ck_bank,input wire rst_n,
 input wire [31:0] rq_v,input wire [447:0] rq_row,input wire [255:0] rq_tag,
 input wire [31:0] wq_v,input wire [447:0] wq_row,input wire [127:0] wq_mask,
 input wire [4095:0] wq_data,input wire [255:0] wq_tag,
 output wire [31:0] rs_v,output wire [4095:0] rs_data,output wire [255:0] rs_tag,
 output wire [31:0] commit_v,output wire [287:0] commit_addr,
 output wire [127:0] commit_mask,output wire [255:0] commit_tag,output wire [1:0] fault
);
 wire [31:0] rv,wv,we;wire [287:0] ra,wa;wire [255:0] rt,wt;
 wire [127:0] wm;wire [4095:0] wd;
 dsfd_vm_static_rscatter u_r(.ck(ck_rscatter),.rst_n(rst_n),.i_v(rq_v),.i_row(rq_row),.i_tag(rq_tag),
 .o_v(rv),.o_addr(ra),.o_tag(rt),.fault(fault[0]));
 dsfd_vm_static_scatter u_w(.ck(ck_wscatter),.rst_n(rst_n),.i_v(wq_v),.i_we(wq_v),
 .i_row(wq_row),.i_mask(wq_mask),.i_data(wq_data),.i_tag(wq_tag),
 .o_v(wv),.o_we(we),.o_addr(wa),.o_mask(wm),.o_data(wd),.o_tag(wt),.fault(fault[1]));
 genvar b;generate for(b=0;b<32;b=b+1)begin:bank
  dsfd_vm_static_bank128 u_bank(.ck(ck_bank[b]),.rst_n(rst_n),
  .i_rv(rv[b]),.i_ra(ra[9*b+:9]),.i_rt(rt[8*b+:8]),
  .i_wv(wv[b]),.i_wa(wa[9*b+:9]),.i_wd(wd[128*b+:128]),.i_wm(wm[4*b+:4]),.i_wt(wt[8*b+:8]),
  .o_rv(rs_v[b]),.o_rd(rs_data[128*b+:128]),.o_rt(rs_tag[8*b+:8]),
  .o_commit(commit_v[b]),.o_ca(commit_addr[9*b+:9]),.o_cm(commit_mask[4*b+:4]),.o_ct(commit_tag[8*b+:8]));
 end endgenerate
endmodule
