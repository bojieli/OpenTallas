`timescale 1ns/1ps
// Real32-bank storage slice, fully static1R1W service. Four slices form512b rows.
// All clocks are stream1.2GHz; separate pins preserve die phi-R delivery to leaves.
// Compiler owns incoming32-record packet and bank reservations. Serial clients
// need explicit fixed-ratio ingress, not a credit adapter hidden in this parent.
module dsfd_vm_static_slice128_suhc(
 input wire ck_rscatter,ck_wscatter,input wire [31:0] ck_bank,input wire rst_n,
 input wire [5:0] ck_relay_req,ck_relay_rsp,
 input wire [17:0] native_rq_v,input wire [251:0] native_rq_row,input wire [89:0] native_rq_slot,
 input wire [2:0] native_rq_group,input wire [11:0] aux_rq_v,input wire [167:0] aux_rq_row,
 input wire [31:0] wq_v,input wire [447:0] wq_row,input wire [127:0] wq_mask,
 input wire [4095:0] wq_data,input wire [255:0] wq_tag,
 output wire [31:0] rs_v,output wire [4095:0] rs_data,output wire [255:0] rs_tag,
 output wire [31:0] commit_v,output wire [287:0] commit_addr,
 output wire [127:0] commit_mask,output wire [255:0] commit_tag,output wire [1:0] fault
);
 wire [31:0] rv,wv,we;wire [287:0] ra,wa;wire [255:0] rt,wt;
 wire [127:0] wm;wire [4095:0] wd;
 dsfd_vm_static_suhc_fsr u_r(.ck(ck_rscatter),.rst_n(rst_n),.i_v(native_rq_v),.i_row(native_rq_row),
 .i_slot(native_rq_slot),.i_group(native_rq_group),.i_aux_v(aux_rq_v),.i_aux_row(aux_rq_row),
 .o_v(rv),.o_addr(ra),.o_tag(rt),.fault(fault[0]));
 dsfd_vm_static_scatter u_w(.ck(ck_wscatter),.rst_n(rst_n),.i_v(wq_v),.i_we(wq_v),
 .i_row(wq_row),.i_mask(wq_mask),.i_data(wq_data),.i_tag(wq_tag),
 .o_v(wv),.o_we(we),.o_addr(wa),.o_mask(wm),.o_data(wd),.o_tag(wt),.fault(fault[1]));
 wire [31:0] ar,aw,br,bw,sv,cv,asv,acv;
 wire [287:0] ara,awa,bra,bwa,ca,aca;
 wire [255:0] art,awt,brt,bwt,st,ct,ast,act;
 wire [127:0] awm,bwm,cm,acm;wire [4095:0] awd,bwd,sd,asd;
 genvar g;
 generate
 for(g=0;g<2;g=g+1)begin:bridge
 dsfd_vm_static_relay128 #(.NBANK(16)) u_hop(.ck_req(ck_relay_req[g+0]),.ck_rsp(ck_relay_rsp[g+0]),.rst_n(rst_n)
 ,.i_rv(rv[16*g+:16])
 ,.i_wv(wv[16*g+:16])
 ,.i_ra(ra[144*g+:144])
 ,.i_wa(wa[144*g+:144])
 ,.i_rt(rt[128*g+:128])
 ,.i_wt(wt[128*g+:128])
 ,.i_wm(wm[64*g+:64])
 ,.i_wd(wd[2048*g+:2048])
 ,.i_sv(asv[16*g+:16])
 ,.i_cv(acv[16*g+:16])
 ,.i_sd(asd[2048*g+:2048])
 ,.i_st(ast[128*g+:128])
 ,.i_ct(act[128*g+:128])
 ,.i_ca(aca[144*g+:144])
 ,.i_cm(acm[64*g+:64])
 ,.o_rv(ar[16*g+:16])
 ,.o_wv(aw[16*g+:16])
 ,.o_ra(ara[144*g+:144])
 ,.o_wa(awa[144*g+:144])
 ,.o_rt(art[128*g+:128])
 ,.o_wt(awt[128*g+:128])
 ,.o_wm(awm[64*g+:64])
 ,.o_wd(awd[2048*g+:2048])
 ,.o_sv(rs_v[16*g+:16])
 ,.o_cv(commit_v[16*g+:16])
 ,.o_sd(rs_data[2048*g+:2048])
 ,.o_st(rs_tag[128*g+:128])
 ,.o_ct(commit_tag[128*g+:128])
 ,.o_ca(commit_addr[144*g+:144])
 ,.o_cm(commit_mask[64*g+:64]));
 end
 for(g=0;g<4;g=g+1)begin:quarter
 dsfd_vm_static_relay128 #(.NBANK(8)) u_hop(.ck_req(ck_relay_req[g+2]),.ck_rsp(ck_relay_rsp[g+2]),.rst_n(rst_n)
 ,.i_rv(ar[8*g+:8])
 ,.i_wv(aw[8*g+:8])
 ,.i_ra(ara[72*g+:72])
 ,.i_wa(awa[72*g+:72])
 ,.i_rt(art[64*g+:64])
 ,.i_wt(awt[64*g+:64])
 ,.i_wm(awm[32*g+:32])
 ,.i_wd(awd[1024*g+:1024])
 ,.i_sv(sv[8*g+:8])
 ,.i_cv(cv[8*g+:8])
 ,.i_sd(sd[1024*g+:1024])
 ,.i_st(st[64*g+:64])
 ,.i_ct(ct[64*g+:64])
 ,.i_ca(ca[72*g+:72])
 ,.i_cm(cm[32*g+:32])
 ,.o_rv(br[8*g+:8])
 ,.o_wv(bw[8*g+:8])
 ,.o_ra(bra[72*g+:72])
 ,.o_wa(bwa[72*g+:72])
 ,.o_rt(brt[64*g+:64])
 ,.o_wt(bwt[64*g+:64])
 ,.o_wm(bwm[32*g+:32])
 ,.o_wd(bwd[1024*g+:1024])
 ,.o_sv(asv[8*g+:8])
 ,.o_cv(acv[8*g+:8])
 ,.o_sd(asd[1024*g+:1024])
 ,.o_st(ast[64*g+:64])
 ,.o_ct(act[64*g+:64])
 ,.o_ca(aca[72*g+:72])
 ,.o_cm(acm[32*g+:32]));
 end
 endgenerate
 genvar b;generate for(b=0;b<32;b=b+1)begin:bank
  dsfd_vm_static_bank128 u_bank(.ck(ck_bank[b]),.rst_n(rst_n),
  .i_rv(br[b]),.i_ra(bra[9*b+:9]),.i_rt(brt[8*b+:8]),
  .i_wv(bw[b]),.i_wa(bwa[9*b+:9]),.i_wd(bwd[128*b+:128]),.i_wm(bwm[4*b+:4]),.i_wt(bwt[8*b+:8]),
  .o_rv(sv[b]),.o_rd(sd[128*b+:128]),.o_rt(st[8*b+:8]),
  .o_commit(cv[b]),.o_ca(ca[9*b+:9]),.o_cm(cm[4*b+:4]),.o_ct(ct[8*b+:8]));
 end endgenerate
endmodule
