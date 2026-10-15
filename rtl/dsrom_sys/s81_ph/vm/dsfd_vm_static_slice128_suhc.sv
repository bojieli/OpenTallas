`timescale 1ns/1ps
// Physical small-group variant: 4x8-bank bridges and 8x4-bank quarters, same two stages each direction.
// Real32-bank storage slice, fully static1R1W service. Four slices form512b rows.
// All clocks are stream1.2GHz; separate pins preserve die phi-R delivery to leaves.
// Compiler owns incoming32-record packet and bank reservations. Serial clients
// need explicit fixed-ratio ingress, not a credit adapter hidden in this parent.
module dsfd_vm_static_slice128_suhc(
 input wire [3:0] ck_rscatter,input wire [31:0] ck_wcapture,input wire [3:0] ck_wscatter,input wire [31:0] ck_bank,
 input wire [11:0] ck_relay_req,ck_relay_rsp,
 input wire [3:0] rst_rscatter_n,input wire [31:0] rst_wcapture_n,rst_bank_n,
 input wire [3:0] rst_wscatter_n,input wire [11:0] rst_relay_n,
 input wire [17:0] native_rq_v,input wire [251:0] native_rq_row,input wire [89:0] native_rq_slot,
 input wire [2:0] native_rq_group,input wire [11:0] aux_rq_v,input wire [167:0] aux_rq_row,
 input wire [31:0] wq_v,input wire [447:0] wq_row,input wire [127:0] wq_mask,
 input wire [4095:0] wq_data,input wire [255:0] wq_tag,
 output wire [31:0] rs_v,output wire [4095:0] rs_data,output wire [255:0] rs_tag,
 output wire [31:0] commit_v,output wire [287:0] commit_addr,
 output wire [127:0] commit_mask,output wire [255:0] commit_tag,output wire [4:0] fault
);
 wire [31:0] rv,wv,we;wire [287:0] ra,wa;wire [255:0] rt,wt;
 wire [127:0] wm;wire [4095:0] wd;
 dsfd_vm_static_suhc_fsr_split u_r(.ck(ck_rscatter),.rst_n(rst_rscatter_n),.i_v(native_rq_v),.i_row(native_rq_row),
 .i_slot(native_rq_slot),.i_group(native_rq_group),.i_aux_v(aux_rq_v),.i_aux_row(aux_rq_row),
 .o_v(rv),.o_addr(ra),.o_tag(rt),.fault(fault[3:0]));
 wire [31:0] cap_v,cap_we;wire [447:0] cap_row;wire [127:0] cap_mask;
 wire [4095:0] cap_data;wire [255:0] cap_tag;wire [3:0] wfault;
 assign fault[4]=|wfault;
 genvar l,k;
 generate for(l=0;l<4;l=l+1)begin:write_group
  for(k=0;k<8;k=k+1)begin:capture
   localparam integer B=8*l+k,J=8*(B%4)+B/4;
   dsfd_vm_static_write_capture128 u_capture(.ck(ck_wcapture[B]),.rst_n(rst_wcapture_n[B]),
    .i_v(wq_v[J]),.i_we(wq_v[J]),.i_row(wq_row[14*J+:14]),.i_mask(wq_mask[4*J+:4]),
    .i_data(wq_data[128*J+:128]),.i_tag(wq_tag[8*J+:8]),
    .o_v(cap_v[B]),.o_we(cap_we[B]),.o_row(cap_row[14*B+:14]),.o_mask(cap_mask[4*B+:4]),
    .o_data(cap_data[128*B+:128]),.o_tag(cap_tag[8*B+:8]));
  end
  dsfd_vm_static_scatter_b8_out #(.BANK_BASE(8*l)) u_w(.ck(ck_wscatter[l]),.rst_n(rst_wscatter_n[l]),
   .i_v(cap_v[8*l+:8]),.i_we(cap_we[8*l+:8]),.i_row(cap_row[112*l+:112]),
   .i_mask(cap_mask[32*l+:32]),.i_data(cap_data[1024*l+:1024]),.i_tag(cap_tag[64*l+:64]),
   .o_v(wv[8*l+:8]),.o_we(we[8*l+:8]),.o_addr(wa[72*l+:72]),.o_mask(wm[32*l+:32]),
   .o_data(wd[1024*l+:1024]),.o_tag(wt[64*l+:64]),.fault(wfault[l]));
 end endgenerate
 wire [31:0] ar,aw,br,bw,sv,cv,asv,acv;
 wire [287:0] ara,awa,bra,bwa,ca,aca;
 wire [255:0] art,awt,brt,bwt,st,ct,ast,act;
 wire [127:0] awm,bwm,cm,acm;wire [4095:0] awd,bwd,sd,asd;
 genvar g;
 generate
 for(g=0;g<4;g=g+1)begin:bridge
 dsfd_vm_static_relay128_b8 u_hop(.ck_req(ck_relay_req[g+0]),.ck_rsp(ck_relay_rsp[g+0]),.rst_n(rst_relay_n[g+0])
 ,.i_rv(rv[8*g+:8])
 ,.i_wv(wv[8*g+:8])
 ,.i_ra(ra[72*g+:72])
 ,.i_wa(wa[72*g+:72])
 ,.i_rt(rt[64*g+:64])
 ,.i_wt(wt[64*g+:64])
 ,.i_wm(wm[32*g+:32])
 ,.i_wd(wd[1024*g+:1024])
 ,.i_sv(asv[8*g+:8])
 ,.i_cv(acv[8*g+:8])
 ,.i_sd(asd[1024*g+:1024])
 ,.i_st(ast[64*g+:64])
 ,.i_ct(act[64*g+:64])
 ,.i_ca(aca[72*g+:72])
 ,.i_cm(acm[32*g+:32])
 ,.o_rv(ar[8*g+:8])
 ,.o_wv(aw[8*g+:8])
 ,.o_ra(ara[72*g+:72])
 ,.o_wa(awa[72*g+:72])
 ,.o_rt(art[64*g+:64])
 ,.o_wt(awt[64*g+:64])
 ,.o_wm(awm[32*g+:32])
 ,.o_wd(awd[1024*g+:1024])
 ,.o_sv(rs_v[8*g+:8])
 ,.o_cv(commit_v[8*g+:8])
 ,.o_sd(rs_data[1024*g+:1024])
 ,.o_st(rs_tag[64*g+:64])
 ,.o_ct(commit_tag[64*g+:64])
 ,.o_ca(commit_addr[72*g+:72])
 ,.o_cm(commit_mask[32*g+:32]));
 end
 for(g=0;g<8;g=g+1)begin:quarter
 dsfd_vm_static_relay128_b4 u_hop(.ck_req(ck_relay_req[g+4]),.ck_rsp(ck_relay_rsp[g+4]),.rst_n(rst_relay_n[g+4])
 ,.i_rv(ar[4*g+:4])
 ,.i_wv(aw[4*g+:4])
 ,.i_ra(ara[36*g+:36])
 ,.i_wa(awa[36*g+:36])
 ,.i_rt(art[32*g+:32])
 ,.i_wt(awt[32*g+:32])
 ,.i_wm(awm[16*g+:16])
 ,.i_wd(awd[512*g+:512])
 ,.i_sv(sv[4*g+:4])
 ,.i_cv(cv[4*g+:4])
 ,.i_sd(sd[512*g+:512])
 ,.i_st(st[32*g+:32])
 ,.i_ct(ct[32*g+:32])
 ,.i_ca(ca[36*g+:36])
 ,.i_cm(cm[16*g+:16])
 ,.o_rv(br[4*g+:4])
 ,.o_wv(bw[4*g+:4])
 ,.o_ra(bra[36*g+:36])
 ,.o_wa(bwa[36*g+:36])
 ,.o_rt(brt[32*g+:32])
 ,.o_wt(bwt[32*g+:32])
 ,.o_wm(bwm[16*g+:16])
 ,.o_wd(bwd[512*g+:512])
 ,.o_sv(asv[4*g+:4])
 ,.o_cv(acv[4*g+:4])
 ,.o_sd(asd[512*g+:512])
 ,.o_st(ast[32*g+:32])
 ,.o_ct(act[32*g+:32])
 ,.o_ca(aca[36*g+:36])
 ,.o_cm(acm[16*g+:16]));
 end
 endgenerate
 genvar b;generate for(b=0;b<32;b=b+1)begin:bank
  dsfd_vm_static_bank128 u_bank(.ck(ck_bank[b]),.rst_n(rst_bank_n[b]),
  .i_rv(br[b]),.i_ra(bra[9*b+:9]),.i_rt(brt[8*b+:8]),
  .i_wv(bw[b]),.i_wa(bwa[9*b+:9]),.i_wd(bwd[128*b+:128]),.i_wm(bwm[4*b+:4]),.i_wt(bwt[8*b+:8]),
  .o_rv(sv[b]),.o_rd(sd[128*b+:128]),.o_rt(st[8*b+:8]),
  .o_commit(cv[b]),.o_ca(ca[9*b+:9]),.o_cm(cm[4*b+:4]),.o_ct(ct[8*b+:8]));
 end endgenerate
endmodule
