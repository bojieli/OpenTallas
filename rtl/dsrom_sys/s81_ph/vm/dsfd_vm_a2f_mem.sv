`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------
// dsfd_vm_a2f_mem (S-VM-RTL, 2026-10-16): the S81 VM native memory with the ADOPTED A2-F write front and hop-1 storage.
// Replaces, inside the A2-F parent only, the legacy write service dsfd_vm_static_wsched (W0 + wcontrol + wdispatch128 +
// wstage128) AND the legacy write capture stage (dsfd_vm_static_write_capture128) and b4 quarter relays of
// dsfd_vm_static512_suhc.  The legacy files are untouched; the legacy parent dsfd_sp_vm still instantiates them.
//
//   write  53 sources --> s81_a2f_controlled_split4m (5 W0 roots + 4 x [control4_resetlocal, 32 field4 data leaves,
//          7 field4 metadata leaves, fault_join4]; bank-linear outputs, compact source-ID capture, 3 slots/bank)
//          --> dsfd_vm_static_scatter_b8_out PIPE 1 (one per slice x bank group, 16) --> relay128_b8 (16)
//          --> [HOP1=0: relay128_b4 (32)] --> bank128 (128 real ot_sram_1r1w_512x128 macros)
//   read   rsched native/aux requests --> dsfd_vm_static_suhc_fsr_split (4 per slice) --> relay128_b8 --> [b4] --> bank128
//          --> [b4] --> b8 --> dsfd_vm_static_return32_native_lanes --> dsfd_vm_static_suhc_return_map (unchanged leaves)
//   commit bank128 o_commit --> [b4] --> b8 response --> commit_v / addr / mask / tag (engine-12 CHECK observations)
// Fixed edges (source pin sample P = W0 header/payload edge, lane = A2 capture slot 0..2):
//   A2-F hop-2 (HOP1=0): raw SRAM write P+12+lane, returned commit P+14+lane (component proof s81_vm_area_1417)
//   A2-F hop-1 (HOP1=1): raw SRAM write P+11+lane, returned commit P+12+lane; read raw / return each -1 / -2 edges
//   (component proof s81_vm_hop1_2210).  The read release edge moves with it: dsfd_vm_a2f_rsched REL = 10 - 2*HOP1.
// Static rules only: no ready, credit, queue, arbitration or backpressure.  Every leaf boundary is a register (the A2-F
// leaves, scatter, relays and banks register every input or output; this module is wires only).
// Clock ABI (each bit = one leaf root): front 169 = header 1 + payload 4 + control 4 + fault 4 + meta 28 + data 128;
// wscatter 16; relay 16 (HOP1=1: b8 only -- the legacy 48-entry relay port's 32-entry b4 tail is PRUNED, not tied) or
// 48 (HOP1=0: b8 4s+g, b4 16+8s+g'); rscatter (FSR) 16; return 16 (4 per slice, reset 1 per slice); bank 128.
// The legacy 128 write-capture roots (ck_mem_wcapture) are retired with dsfd_vm_static_write_capture128.
// Mutants (DUT-side, each must FAIL the differential bench):
//   DSFD_VM_A2F_MUT_LANE    record of bank k drives the scatter data lane of bank k^1 (wrong lane)
//   DSFD_VM_A2F_MUT_COMMIT  slice 0 bank 5 commit observation dropped (dropped commit)
// ---------------------------------------------------------------------------------------------------------------
module dsfd_vm_a2f_slice128 #(parameter integer HOP1=1, parameter integer SLICE=0)(
 input wire [3:0] ck_rscatter,input wire [3:0] ck_wscatter,input wire [31:0] ck_bank,
 input wire [(HOP1?4:12)-1:0] ck_relay_req,ck_relay_rsp,
 input wire [3:0] rst_rscatter_n,input wire [3:0] rst_wscatter_n,input wire [31:0] rst_bank_n,
 input wire [(HOP1?4:12)-1:0] rst_relay_n,
 input wire [17:0] native_rq_v,input wire [251:0] native_rq_row,input wire [89:0] native_rq_slot,
 input wire [2:0] native_rq_group,input wire [11:0] aux_rq_v,input wire [167:0] aux_rq_row,
 // A2-F front records of this slice, bank-linear (bank k = 8 * group + local)
 input wire [31:0] w_v,input wire [447:0] w_row,input wire [127:0] w_mask,input wire [4095:0] w_data,input wire [255:0] w_tag,
 output wire [31:0] rs_v,output wire [4095:0] rs_data,output wire [255:0] rs_tag,
 output wire [31:0] commit_v,output wire [287:0] commit_addr,
 output wire [127:0] commit_mask,output wire [255:0] commit_tag,output wire [4:0] fault
);
 wire [31:0] rv,wv,we;wire [287:0] ra,wa;wire [255:0] rt,wt;
 wire [127:0] wm;wire [4095:0] wd;wire [3:0] wfault;
 dsfd_vm_static_suhc_fsr_split u_r(.ck(ck_rscatter),.rst_n(rst_rscatter_n),.i_v(native_rq_v),.i_row(native_rq_row),
  .i_slot(native_rq_slot),.i_group(native_rq_group),.i_aux_v(aux_rq_v),.i_aux_row(aux_rq_row),
  .o_v(rv),.o_addr(ra),.o_tag(rt),.fault(fault[3:0]));
 assign fault[4]=|wfault;
 wire [4095:0] w_data_l;
 genvar l,k;
 generate for(k=0;k<32;k=k+1)begin:lane_map
`ifdef DSFD_VM_A2F_MUT_LANE
  if(SLICE==0)begin:mut assign w_data_l[128*k+:128]=w_data[128*(k^1)+:128];end
  else begin:ok assign w_data_l[128*k+:128]=w_data[128*k+:128];end
`else
  assign w_data_l[128*k+:128]=w_data[128*k+:128];
`endif
 end
 // Write scatter: the A2-F front already delivers bank-linear records, so the legacy logical-packet permutation
 // (J = 8 (k mod 4) + k / 4) and its 32 write-capture leaves are gone; PIPE 1 = every scatter input pin-registered.
 for(l=0;l<4;l=l+1)begin:write_group
  dsfd_vm_static_scatter_b8_out #(.BANK_BASE(8*l),.PIPE(1)) u_w(.ck(ck_wscatter[l]),.rst_n(rst_wscatter_n[l]),
   .i_v(w_v[8*l+:8]),.i_we(w_v[8*l+:8]),.i_row(w_row[112*l+:112]),
   .i_mask(w_mask[32*l+:32]),.i_data(w_data_l[1024*l+:1024]),.i_tag(w_tag[64*l+:64]),
   .o_v(wv[8*l+:8]),.o_we(we[8*l+:8]),.o_addr(wa[72*l+:72]),.o_mask(wm[32*l+:32]),
   .o_data(wd[1024*l+:1024]),.o_tag(wt[64*l+:64]),.fault(wfault[l]));
 end endgenerate
 // b8 bridges (both directions); HOP1 drives the banks straight from the b8 outputs
 wire [31:0] ar,aw,asv,acv,br,bw,sv,cv;wire [287:0] ara,awa,aca,bra,bwa,ca;
 wire [255:0] art,awt,ast,act,brt,bwt,st,ct;wire [127:0] awm,acm,bwm,cm;wire [4095:0] awd,asd,bwd,sd;
 wire [31:0] commit_v_b8;
 genvar g;
 generate for(g=0;g<4;g=g+1)begin:bridge
  dsfd_vm_static_relay128_b8 u_hop(.ck_req(ck_relay_req[g]),.ck_rsp(ck_relay_rsp[g]),.rst_n(rst_relay_n[g]),
   .i_rv(rv[8*g+:8]),.i_wv(wv[8*g+:8]),.i_ra(ra[72*g+:72]),.i_wa(wa[72*g+:72]),.i_rt(rt[64*g+:64]),.i_wt(wt[64*g+:64]),
   .i_wm(wm[32*g+:32]),.i_wd(wd[1024*g+:1024]),
   .i_sv(asv[8*g+:8]),.i_cv(acv[8*g+:8]),.i_sd(asd[1024*g+:1024]),.i_st(ast[64*g+:64]),.i_ct(act[64*g+:64]),
   .i_ca(aca[72*g+:72]),.i_cm(acm[32*g+:32]),
   .o_rv(ar[8*g+:8]),.o_wv(aw[8*g+:8]),.o_ra(ara[72*g+:72]),.o_wa(awa[72*g+:72]),.o_rt(art[64*g+:64]),.o_wt(awt[64*g+:64]),
   .o_wm(awm[32*g+:32]),.o_wd(awd[1024*g+:1024]),
   .o_sv(rs_v[8*g+:8]),.o_cv(commit_v_b8[8*g+:8]),.o_sd(rs_data[1024*g+:1024]),.o_st(rs_tag[64*g+:64]),
   .o_ct(commit_tag[64*g+:64]),.o_ca(commit_addr[72*g+:72]),.o_cm(commit_mask[32*g+:32]));
 end
 if(HOP1)begin:hop1
  assign br=ar;assign bw=aw;assign bra=ara;assign bwa=awa;assign brt=art;assign bwt=awt;assign bwm=awm;assign bwd=awd;
  assign asv=sv;assign acv=cv;assign asd=sd;assign ast=st;assign act=ct;assign aca=ca;assign acm=cm;
 end else begin:hop2
  for(g=0;g<8;g=g+1)begin:quarter
   dsfd_vm_static_relay128_b4 u_hop(.ck_req(ck_relay_req[g+4]),.ck_rsp(ck_relay_rsp[g+4]),.rst_n(rst_relay_n[g+4]),
    .i_rv(ar[4*g+:4]),.i_wv(aw[4*g+:4]),.i_ra(ara[36*g+:36]),.i_wa(awa[36*g+:36]),.i_rt(art[32*g+:32]),.i_wt(awt[32*g+:32]),
    .i_wm(awm[16*g+:16]),.i_wd(awd[512*g+:512]),
    .i_sv(sv[4*g+:4]),.i_cv(cv[4*g+:4]),.i_sd(sd[512*g+:512]),.i_st(st[32*g+:32]),.i_ct(ct[32*g+:32]),
    .i_ca(ca[36*g+:36]),.i_cm(cm[16*g+:16]),
    .o_rv(br[4*g+:4]),.o_wv(bw[4*g+:4]),.o_ra(bra[36*g+:36]),.o_wa(bwa[36*g+:36]),.o_rt(brt[32*g+:32]),.o_wt(bwt[32*g+:32]),
    .o_wm(bwm[16*g+:16]),.o_wd(bwd[512*g+:512]),
    .o_sv(asv[4*g+:4]),.o_cv(acv[4*g+:4]),.o_sd(asd[512*g+:512]),.o_st(ast[32*g+:32]),.o_ct(act[32*g+:32]),
    .o_ca(aca[36*g+:36]),.o_cm(acm[16*g+:16]));
  end
 end endgenerate
`ifdef DSFD_VM_A2F_MUT_COMMIT
 assign commit_v=(SLICE==0)?(commit_v_b8&~32'h20):commit_v_b8;
`else
 assign commit_v=commit_v_b8;
`endif
 genvar b;generate for(b=0;b<32;b=b+1)begin:bank
  dsfd_vm_static_bank128 u_bank(.ck(ck_bank[b]),.rst_n(rst_bank_n[b]),
   .i_rv(br[b]),.i_ra(bra[9*b+:9]),.i_rt(brt[8*b+:8]),
   .i_wv(bw[b]),.i_wa(bwa[9*b+:9]),.i_wd(bwd[128*b+:128]),.i_wm(bwm[4*b+:4]),.i_wt(bwt[8*b+:8]),
   .o_rv(sv[b]),.o_rd(sd[128*b+:128]),.o_rt(st[8*b+:8]),
   .o_commit(cv[b]),.o_ca(ca[9*b+:9]),.o_cm(cm[4*b+:4]),.o_ct(ct[8*b+:8]));
 end endgenerate
endmodule

module dsfd_vm_a2f_mem #(parameter integer RET_PINREG=0, parameter integer HOP1=1)(
 // A2-F write front roots
 input wire [3:0] ck_native_diag,rst_native_diag_n,
 input wire ck_wf_header,input wire [15:0] ck_wf_payload,input wire [3:0] ck_wf_control,ck_wf_fault,
 input wire [27:0] ck_wf_meta,input wire [127:0] ck_wf_data,
 input wire rst_wf_header_n,input wire [15:0] rst_wf_payload_n,input wire [3:0] rst_wf_control_n,rst_wf_fault_n,
 input wire [27:0] rst_wf_meta_n,input wire [127:0] rst_wf_data_n,
 // storage roots
 input wire [15:0] ck_rscatter,input wire [15:0] ck_return,input wire [15:0] ck_wscatter,input wire [127:0] ck_bank,
 input wire [(HOP1?16:48)-1:0] ck_relay_req,ck_relay_rsp,
 input wire [15:0] rst_rscatter_n,input wire [3:0] rst_return_n,input wire [15:0] rst_wscatter_n,
 input wire [127:0] rst_bank_n,input wire [(HOP1?16:48)-1:0] rst_relay_n,
 // read requests (rsched)
 input wire [17:0] native_rq_v,input wire [251:0] native_rq_row,input wire [89:0] native_rq_slot,
 input wire [2:0] native_rq_group,input wire [11:0] aux_rq_v,input wire [167:0] aux_rq_row,
 // 53 write sources {v, row 14, tag 8, mask 16 words, data 512} -- the A2-F front's W0 roots are their pin registers
 input wire [52:0] i_v,input wire [741:0] i_row,input wire [423:0] i_tag,input wire [847:0] i_mask,input wire [27135:0] i_data,
 input wire release_v,input wire [2:0] release_group,input wire [31:0] release_mask,
 input wire prepare_v,input wire [2:0] prepare_group,input wire [31:0] prepare_mask,
 input wire [17:0] native_expected_v,input wire [89:0] native_release_slot,
 output wire [71:0] native_v,output wire [9215:0] native_data,
 output wire [127:0] group_v,output wire [16383:0] group_data,output wire [11:0] group_id,
 output wire [127:0] commit_v,output wire [1151:0] commit_addr,
 output wire [511:0] commit_mask,output wire [1023:0] commit_tag,
 // per slice s: [10s+:4] FSR, [10s+4] write scatter, [10s+5+:4] return lanes, [10s+9] native map (legacy layout)
 output wire [39:0] fault,
 output wire [15:0] w_fault          // A2-F front: 4 slices x 4 quarter fault joins (registered, sticky)
);
 localparam integer NR = HOP1 ? 4 : 12;   // relay roots per slice
 wire [127:0] fv;wire [1791:0] fr;wire [1023:0] ft;wire [511:0] fm;wire [16383:0] fd;
 s81_a2f_controlled_split4m_payload33 u_front(
  .ck_header(ck_wf_header),.ck_payload(ck_wf_payload),.ck_control(ck_wf_control),.ck_fault(ck_wf_fault),
  .ck_meta(ck_wf_meta),.ck_data(ck_wf_data),
  .rst_header_n(rst_wf_header_n),.rst_payload_n(rst_wf_payload_n),.rst_control_n(rst_wf_control_n),
  .rst_fault_n(rst_wf_fault_n),.rst_meta_n(rst_wf_meta_n),.rst_data_n(rst_wf_data_n),
  .i_v(i_v),.i_row(i_row),.i_tag(i_tag),.i_mask(i_mask),.i_data(i_data),
  .o_slice_v(fv),.o_slice_row(fr),.o_slice_tag(ft),.o_mask(fm),.o_data(fd),.o_fault(w_fault));
 genvar s,q;generate for(s=0;s<4;s=s+1)begin:slice
  wire [127:0] wm;wire [4095:0] wd;
  wire [4095:0] rd;wire [31:0] rv;wire [255:0] rt;wire [4095:0] gd;wire [2303:0] nd;
  for(q=0;q<32;q=q+1)begin:wrow
   assign wm[4*q+:4]=fm[16*q+4*s+:4];
   assign wd[128*q+:128]=fd[512*q+128*s+:128];
  end
  // relay roots: HOP1 -> b8 g of slice s = bit 4s+g; HOP1=0 -> the legacy 12-per-slice slicing
  dsfd_vm_a2f_slice128 #(.HOP1(HOP1),.SLICE(s)) u_slice(.ck_rscatter(ck_rscatter[4*s+:4]),.ck_wscatter(ck_wscatter[4*s+:4]),
   .ck_bank(ck_bank[32*s+:32]),.ck_relay_req(ck_relay_req[NR*s+:NR]),.ck_relay_rsp(ck_relay_rsp[NR*s+:NR]),
   .rst_rscatter_n(rst_rscatter_n[4*s+:4]),.rst_wscatter_n(rst_wscatter_n[4*s+:4]),.rst_bank_n(rst_bank_n[32*s+:32]),
   .rst_relay_n(rst_relay_n[NR*s+:NR]),
   .native_rq_v(native_rq_v),.native_rq_row(native_rq_row),.native_rq_slot(native_rq_slot),
   .native_rq_group(native_rq_group),.aux_rq_v(aux_rq_v),.aux_rq_row(aux_rq_row),
   .w_v(fv[32*s+:32]),.w_row(fr[448*s+:448]),.w_mask(wm),.w_data(wd),.w_tag(ft[256*s+:256]),
   .rs_v(rv),.rs_data(rd),.rs_tag(rt),.commit_v(commit_v[32*s+:32]),
   .commit_addr(commit_addr[288*s+:288]),.commit_mask(commit_mask[128*s+:128]),
   .commit_tag(commit_tag[256*s+:256]),.fault(fault[10*s+:5]));
  // unchanged return lanes + native map (dsfd_vm_static512_suhc)
  wire [11:0] lane_group;
  dsfd_vm_static_return32_native_lanes #(.PINREG(RET_PINREG)) u_return(.ck(ck_return[4*s+:4]),.rst_n({4{rst_return_n[s]}}),
   .i_v(rv),.i_tag(rt),.i_data(rd),
   .release_v(release_v),.release_group(release_group),.release_mask(release_mask),
   .prepare_v(prepare_v),.prepare_group(prepare_group),.prepare_mask(prepare_mask),
   .o_v(group_v[32*s+:32]),.o_data(gd),.o_group(lane_group),.fault(fault[10*s+5+:4]));
  assign group_id[3*s+:3]=lane_group[2:0];
  dsfd_vm_static_suhc_return_map u_native(.i_v(group_v[32*s+:32]),.i_data(gd),
   .expected_v(native_expected_v),.release_slot(native_release_slot),
   .o_v(native_v[18*s+:18]),.o_data(nd),.fault());
  dsfd_vm_native_valid_diag u_native_diag(.i_fault(16'd0),.ck(ck_native_diag[s]),.rst_n(rst_native_diag_n[s]),
   .i_v(group_v[32*s+:32]),.expected_v(native_expected_v),.release_slot(native_release_slot),
   .fault(fault[10*s+9]));
  for(q=0;q<18;q=q+1)begin:native_rows
   assign native_data[512*q+128*s+:128]=nd[128*q+:128];
  end
  for(q=0;q<32;q=q+1)begin:read_rows
   assign group_data[512*q+128*s+:128]=gd[128*q+:128];
  end
 end endgenerate
endmodule
`default_nettype wire
