`timescale 1ns/1ps
// LG tap fold lockstep (coordinator 0db 10-17). Each folded tile vs its DISCRETE die composition, all outputs compared
// every edge after cold init, under random records (valid bits included) and random local selects:
//  SFU: ot_hgi_sfu_lg_pair_tap_leaf(14/11)   vs ot_hgi_sfu_lg_pair_leaf(PIN_RST=1) + 2 x ot_hbm_vm_lg_static_bank(RET_PIN=1, rret 14 / wret 11 straps)
//  HC : ot_hgi_sfu_lg_pair_tap_leaf_term(18/15) vs ot_hgi_sfu_lg_pair_leaf(PIN_RST=1) + 2 x ot_hbm_vm_lg_static_bank_term(18/15)
//  SU : ot_hbm_vm_lg_pair_tap(10/7)          vs 2 x ot_hbm_vm_lg_static_bank(RET_PIN=1, rret 10 / wret 7) (the SU slice side is the unchanged pgslice)
// +MUT: the folded SFU tile's bank-1 write payload mux selects far despite the local calendar -> must FAIL.
module tb_hgi_lg_pair_tap_fold;
 parameter integer MUT=0;
 reg clk=0,rst_n=0; always #0.4166 clk=~clk;
 reg [33:0] c_rq,far_rq; reg [561:0] c_wq,far_wq; reg [513:0] near_rr; reg [1:0] near_done,lrd,lwr;
 integer n,errors=0,checks=0,i;
 // ---------------- SFU level
 wire [513:0] f_c_rr,d_c_rr,f_far_rr,d_far_rr; wire [1:0] f_c_done,d_c_done,f_far_done,d_far_done;
 wire [33:0] f_near_rq,d_near_rq; wire [561:0] f_near_wq,d_near_wq; wire f_fault; wire [1:0] d_fault;
 ot_hgi_sfu_lg_pair_tap_leaf #(.READ_RETURN(14),.WRITE_RETURN(11),.MUT(MUT)) f_sfu(.clk(clk),.rst_n(rst_n),
  .c_rq(c_rq),.c_wq(c_wq),.c_rr(f_c_rr),.c_w_done(f_c_done),.local_read(lrd),.local_write(lwr),
  .far_rq(far_rq),.far_wq(far_wq),.far_rr(f_far_rr),.far_w_done(f_far_done),
  .near_rq(f_near_rq),.near_wq(f_near_wq),.near_rr(near_rr),.near_w_done(near_done),.fault(f_fault));
 wire [33:0] l_rq; wire [561:0] l_wq; wire [513:0] l_rr; wire [1:0] l_done;
 ot_hgi_sfu_lg_pair_leaf #(.PIN_RST(1)) d_leaf(.clk(clk),.rst_n(rst_n),.c_rq(c_rq),.c_wq(c_wq),.c_rr(d_c_rr),.c_w_done(d_c_done),
  .lg_rq(l_rq),.lg_wq(l_wq),.lg_rr(l_rr),.lg_w_done(l_done));
 for(genvar b=0;b<2;b=b+1)begin:d_tap
  ot_hbm_vm_lg_static_bank #(.READ_RETURN(18),.WRITE_RETURN(15),.RET_PIN(1)) t(.clk(clk),.rst_n(rst_n),.rret(5'd14),.wret(5'd11),
   .local_rq(l_rq[b*17+:17]),.far_rq(far_rq[b*17+:17]),.local_wq(l_wq[b*281+:281]),.far_wq(far_wq[b*281+:281]),
   .local_read(lrd[b]),.local_write(lwr[b]),.near_rq(d_near_rq[b*17+:17]),.near_wq(d_near_wq[b*281+:281]),
   .near_rr(near_rr[b*257+:257]),.near_w_done(near_done[b]),.local_rr(l_rr[b*257+:257]),.far_rr(d_far_rr[b*257+:257]),
   .local_w_done(l_done[b]),.far_w_done(d_far_done[b]),.fault(d_fault[b]));
 end
 // ---------------- HC level (terminal)
 wire [513:0] fh_c_rr,dh_c_rr; wire [1:0] fh_c_done,dh_c_done; wire [33:0] fh_near_rq,dh_near_rq;
 wire [561:0] fh_near_wq,dh_near_wq; wire fh_fault; wire [1:0] dh_fault;
 ot_hgi_sfu_lg_pair_tap_leaf_term #(.READ_RETURN(18),.WRITE_RETURN(15)) f_hc(.clk(clk),.rst_n(rst_n),
  .c_rq(c_rq),.c_wq(c_wq),.c_rr(fh_c_rr),.c_w_done(fh_c_done),.local_read(lrd),.local_write(lwr),
  .near_rq(fh_near_rq),.near_wq(fh_near_wq),.near_rr(near_rr),.near_w_done(near_done),.fault(fh_fault));
 wire [33:0] h_rq; wire [561:0] h_wq; wire [513:0] h_rr; wire [1:0] h_done;
 ot_hgi_sfu_lg_pair_leaf #(.PIN_RST(1)) dh_leaf(.clk(clk),.rst_n(rst_n),.c_rq(c_rq),.c_wq(c_wq),.c_rr(dh_c_rr),.c_w_done(dh_c_done),
  .lg_rq(h_rq),.lg_wq(h_wq),.lg_rr(h_rr),.lg_w_done(h_done));
 for(genvar b=0;b<2;b=b+1)begin:dh_tap
  ot_hbm_vm_lg_static_bank_term #(.READ_RETURN(18),.WRITE_RETURN(15)) t(.clk(clk),.rst_n(rst_n),
   .local_rq(h_rq[b*17+:17]),.local_wq(h_wq[b*281+:281]),.local_read(lrd[b]),.local_write(lwr[b]),
   .near_rq(dh_near_rq[b*17+:17]),.near_wq(dh_near_wq[b*281+:281]),.near_rr(near_rr[b*257+:257]),.near_w_done(near_done[b]),
   .local_rr(h_rr[b*257+:257]),.local_w_done(h_done[b]),.fault(dh_fault[b]));
 end
 // ---------------- SU level (pair tap only; driven by c_* as the slice's lg_* output)
 wire [513:0] fs_rr,ds_rr,fs_far_rr,ds_far_rr; wire [1:0] fs_done,ds_done,fs_far_done,ds_far_done;
 wire [33:0] fs_near_rq,ds_near_rq; wire [561:0] fs_near_wq,ds_near_wq; wire fs_fault; wire [1:0] ds_fault;
 ot_hbm_vm_lg_pair_tap #(.READ_RETURN(10),.WRITE_RETURN(7)) f_su(.clk(clk),.rst_n(rst_n),.local_rq(c_rq),.far_rq(far_rq),
  .local_wq(c_wq),.far_wq(far_wq),.local_read(lrd),.local_write(lwr),.near_rq(fs_near_rq),.near_wq(fs_near_wq),
  .near_rr(near_rr),.near_w_done(near_done),.local_rr(fs_rr),.far_rr(fs_far_rr),.local_w_done(fs_done),.far_w_done(fs_far_done),.fault(fs_fault));
 for(genvar b=0;b<2;b=b+1)begin:ds_tap
  ot_hbm_vm_lg_static_bank #(.READ_RETURN(18),.WRITE_RETURN(15),.RET_PIN(1)) t(.clk(clk),.rst_n(rst_n),.rret(5'd10),.wret(5'd7),
   .local_rq(c_rq[b*17+:17]),.far_rq(far_rq[b*17+:17]),.local_wq(c_wq[b*281+:281]),.far_wq(far_wq[b*281+:281]),
   .local_read(lrd[b]),.local_write(lwr[b]),.near_rq(ds_near_rq[b*17+:17]),.near_wq(ds_near_wq[b*281+:281]),
   .near_rr(near_rr[b*257+:257]),.near_w_done(near_done[b]),.local_rr(ds_rr[b*257+:257]),.far_rr(ds_far_rr[b*257+:257]),
   .local_w_done(ds_done[b]),.far_w_done(ds_far_done[b]),.fault(ds_fault[b]));
 end
 // build in a 576-bit temporary: no part-select past bit 561 (a fleet vvp build asserts on that, rc 134)
 function automatic [561:0] rnd562(input integer s); integer k; reg [575:0] t; begin for(k=0;k<576;k=k+32) t[k+:32]=$urandom; rnd562=t[561:0]; end endfunction
 integer faults=0, valids=0;
 initial begin
  {c_rq,far_rq,c_wq,far_wq,near_rr,near_done,lrd,lwr}=0;
  repeat(4) @(negedge clk); rst_n=1; repeat(2) @(negedge clk);
  for(n=0;n<20000;n=n+1)begin
   c_rq=rnd562(0); far_rq=rnd562(0); c_wq=rnd562(0); far_wq=rnd562(0); near_rr=rnd562(0); near_done=$urandom; lrd=$urandom; lwr=$urandom;
   if(n%7!=0) begin c_rq[16]&=lrd[0]; c_rq[33]&=lrd[1]; far_rq[16]&=~lrd[0]; far_rq[33]&=~lrd[1]; end
   @(posedge clk); #0.05;
   if(n>2)begin
    checks=checks+1;
    if({f_c_rr,f_c_done,f_far_rr,f_far_done,f_near_rq,f_near_wq,f_fault}!=={d_c_rr,d_c_done,d_far_rr,d_far_done,d_near_rq,d_near_wq,|d_fault}) begin errors=errors+1; if(errors<4)$display("SFU mismatch n=%0d",n); end
    if({fh_c_rr,fh_c_done,fh_near_rq,fh_near_wq,fh_fault}!=={dh_c_rr,dh_c_done,dh_near_rq,dh_near_wq,|dh_fault}) begin errors=errors+1; if(errors<4)$display("HC mismatch n=%0d",n); end
    if({fs_rr,fs_done,fs_far_rr,fs_far_done,fs_near_rq,fs_near_wq,fs_fault}!=={ds_rr,ds_done,ds_far_rr,ds_far_done,ds_near_rq,ds_near_wq,|ds_fault}) begin errors=errors+1; if(errors<4)$display("SU mismatch n=%0d",n); end
    valids=valids+f_near_rq[16]+f_near_wq[280]+f_c_rr[256]+f_far_rr[256]+fh_c_rr[256]+fs_rr[256];
   end
   @(negedge clk);
   if(n==10000)begin rst_n=0; repeat(3) @(negedge clk); rst_n=1; repeat(2) @(negedge clk); end
  end
  if(errors||valids<1000)begin $display("LG_FOLD FAIL checks=%0d errors=%0d valids=%0d",checks,errors,valids);$fatal(1);end
  $display("LG_FOLD PASS checks=%0d edges x3 tiles, valids=%0d",checks,valids);$finish;
 end
endmodule
