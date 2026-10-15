`timescale 1ns/1ps
// Physical small-group variant: 4x8-bank bridges and 8x4-bank quarters, same two stages each direction.
// Real32-bank storage slice, fully static1R1W service. Four slices form512b rows.
// All clocks are stream1.2GHz; separate pins preserve die phi-R delivery to leaves.
// Compiler owns incoming32-record packet and bank reservations. Serial clients
// need explicit fixed-ratio ingress, not a credit adapter hidden in this parent.
module dsfd_vm_static_slice128_suhc(
 input wire ck_rscatter,input wire [3:0] ck_wscatter,input wire [31:0] ck_bank,input wire rst_n,
 input wire [11:0] ck_relay_req,ck_relay_rsp,
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
 wire [3:0] wfault;
 assign fault[1]=|wfault;
 genvar l,k;
 generate for(l=0;l<4;l=l+1)begin:write_lane
  wire [7:0] lv,lwe;wire [71:0] la;wire [31:0] lm;wire [1023:0] ld;wire [63:0] lt;
  dsfd_vm_static_scatter_lane #(.LANE(l)) u_w(.ck(ck_wscatter[l]),.rst_n(rst_n),
   .i_v(wq_v[8*l+:8]),.i_we(wq_v[8*l+:8]),.i_row(wq_row[112*l+:112]),
   .i_mask(wq_mask[32*l+:32]),.i_data(wq_data[1024*l+:1024]),.i_tag(wq_tag[64*l+:64]),
   .o_v(lv),.o_we(lwe),.o_addr(la),.o_mask(lm),.o_data(ld),.o_tag(lt),.fault(wfault[l]));
  for(k=0;k<8;k=k+1)begin:bank_outputs
   assign wv[4*k+l]=lv[k];assign we[4*k+l]=lwe[k];
   assign wa[9*(4*k+l)+:9]=la[9*k+:9];assign wm[4*(4*k+l)+:4]=lm[4*k+:4];
   assign wd[128*(4*k+l)+:128]=ld[128*k+:128];assign wt[8*(4*k+l)+:8]=lt[8*k+:8];
  end
 end endgenerate
 wire [31:0] ar,aw,br,bw,sv,cv,asv,acv;
 wire [287:0] ara,awa,bra,bwa,ca,aca;
 wire [255:0] art,awt,brt,bwt,st,ct,ast,act;
 wire [127:0] awm,bwm,cm,acm;wire [4095:0] awd,bwd,sd,asd;
 genvar g;
 generate
 for(g=0;g<4;g=g+1)begin:bridge
 dsfd_vm_static_relay128_b8 u_hop(.ck_req(ck_relay_req[g+0]),.ck_rsp(ck_relay_rsp[g+0]),.rst_n(rst_n)
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
 dsfd_vm_static_relay128_b4 u_hop(.ck_req(ck_relay_req[g+4]),.ck_rsp(ck_relay_rsp[g+4]),.rst_n(rst_n)
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
  dsfd_vm_static_bank128 u_bank(.ck(ck_bank[b]),.rst_n(rst_n),
  .i_rv(br[b]),.i_ra(bra[9*b+:9]),.i_rt(brt[8*b+:8]),
  .i_wv(bw[b]),.i_wa(bwa[9*b+:9]),.i_wd(bwd[128*b+:128]),.i_wm(bwm[4*b+:4]),.i_wt(bwt[8*b+:8]),
  .o_rv(sv[b]),.o_rd(sd[128*b+:128]),.o_rt(st[8*b+:8]),
  .o_commit(cv[b]),.o_ca(ca[9*b+:9]),.o_cm(cm[4*b+:4]),.o_ct(ct[8*b+:8]));
 end endgenerate
endmodule
