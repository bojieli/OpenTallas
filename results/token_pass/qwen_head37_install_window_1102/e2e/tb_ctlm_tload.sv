`timescale 1ns/1fs
// TOK-QW-4 11-02: stage37 install window END-TO-END on the actual CTLM + actual 1021 calendar image + actual loaders.
// qfd_dv_cmd_cal_mu_head37 #(HEAD_STAGE37 1) (calendar_m0/m1 = the nent1021 image, dw.hex) -> table_load pulse ->
// treq_q (g_calr register, +1) -> die lane (T_die, modelled 0 here: add the die's lane age) -> 12 x qfd_dv_slice_tload
// #(HEAD_STAGE37 1) with the genuine rank0 HEAD37 ROMs. Slice resets between trials; the CTLM keeps its image.
// Dates are edges relative to the CTLM start edge of the range (start pulse sampled at posedge E).
module tb_ctlm_tload;
reg ck=0; always #0.4165 ck=~ck;
reg rst_n=0, rst_s=0;
reg pw_v=0,dw_v=0,start=0,rng=0;reg[9:0]pw_addr=0,first=0;reg[2:0]dw_addr=0;reg[63:0]dw_data=0,desc[0:7];reg[1:0]user_id=0;reg[5:0]stage=0;
wire load,ready,fault,done;wire[5:0]ts,fc;wire[1:0]tu;wire[3:0]running;wire[115:0]cmd;
qfd_dv_cmd_cal_mu_head37 #(.HEAD_STAGE37(1),.NU(4),.CTX_DW(1),.UFOLD(1),.CALENDAR_ROM(1),.TABLE_ROM(1),.UVM_STRIDE(4096),.PIDX_STRIDE(128),.CALREG(7)) ctlm(
 .ck(ck),.rst_n(rst_n),.pw_v(pw_v),.pw_addr(pw_addr),.pw_data(64'd0),.dw_v(dw_v),.dw_addr(dw_addr),.dw_data(dw_data),.start(start),.stage(stage),
 .start_user(user_id),.start_rng(rng),.start_first(first),.start_cnt(10'd1),.cmd(cmd),.table_load(load),.table_stage(ts),.table_user(tu),
 .image_ready(ready),.running_u(running),.done(done),.fault(fault),.fault_code(fc));
reg [8:0] treq_q;   // qfd_tt_ctlm_dv_gi g_calr.treq_q
always @(posedge ck or negedge rst_n) if(!rst_n) treq_q<=0; else treq_q<={load,ts,tu};
localparam integer NS=12;
wire [NS-1:0] we,bz,dn,ft;
genvar g;
generate for(g=0;g<NS;g=g+1)begin:sl
 wire [1:0] k; wire [23:0] a; wire [1023:0] x;
 qfd_dv_slice_tload #(.SLICE(g),.HEAD_STAGE37(1)) t(.ck(ck),.rst_n(rst_s),.treq(treq_q),.s_we(1'b0),.s_kind(2'd0),
   .s_addr(24'd0),.s_data(1024'd0),.tw_we(we[g]),.tw_kind(k),.tw_addr(a),.tw_data(x),.busy(bz[g]),.done(dn[g]),.fault(ft[g]));
end endgenerate
integer cyc=0; always @(posedge ck) cyc<=cyc+1;
integer nw0,nw11,fw,lw,ld_first,ld_last,nld,mark=0,bzlast;
always @(negedge ck) begin
  if(cyc>=mark) begin
   if(we[0]) begin if(fw<0) fw=cyc; lw=cyc; nw0++; end
   if(we[11]) nw11++;
   if(load) begin if(ld_first<0) ld_first=cyc; ld_last=cyc; nld++; end
   if(bz[0]) bzlast=cyc;
  end
end
task automatic clr(input integer m); mark=m; nw0=0;nw11=0;fw=-1;lw=-1;ld_first=-1;ld_last=-1;nld=0;bzlast=-1; endtask
function automatic integer fm(); fm=0; for(int i=0;i<NS;i++) if(ft[i]) fm|=(1<<i); endfunction
task automatic srst(); @(negedge ck); rst_s=0; repeat(4) @(negedge ck); rst_s=1; repeat(6) @(negedge ck); endtask
task automatic go(input integer st, input integer u); stage=6'(st); first=10'(st==37?1020:876+4*(st-1)); rng=1; user_id=2'(u); start=1; @(negedge ck); start=0; endtask
integer d,e0,e1,s,u,sp,nl,dmin=1000;
initial begin
 $readmemh("dw.hex",desc);
 repeat(64)@(negedge ck);rst_n=1;repeat(64)@(negedge ck);
 for(int k=0;k<1024;k++)begin pw_v=1;pw_addr=10'(k);@(negedge ck);end
 pw_v=0;
 for(int k=0;k<8;k++)begin dw_v=1;dw_addr=3'(k);dw_data=desc[k];@(negedge ck);end
 dw_v=0;repeat(128)@(negedge ck);
 if(ready!==1||fault!==0)$fatal(1,"CTLM_IMAGE_READY %b %b",ready,fault);
 // single stage37 range: CTLM start -> table_load -> slice writes
 srst(); e0=cyc+1; clr(e0); go(37,1); repeat(200) @(negedge ck);
 $display("E2E_SINGLE37 u1 ctlm_fault %0d slice_faultmask %03x load_at %0d nload %0d first_write %0d last_write %0d busy_last %0d writes s0 %0d s11 %0d",
          fault,fm(),ld_first-e0,nld,fw-e0,lw-e0,bzlast-e0,nw0,nw11);
 srst(); e0=cyc+1; clr(e0); go(36,1); repeat(200) @(negedge ck);
 $display("E2E_SINGLE36 u1 ctlm_fault %0d slice_faultmask %03x load_at %0d nload %0d first_write %0d last_write %0d busy_last %0d writes s0 %0d s11 %0d",
          fault,fm(),ld_first-e0,nld,fw-e0,lw-e0,bzlast-e0,nw0,nw11);
 // stage36 user0 range then stage37 user u range, start-to-start spacing d
 for(u=0;u<2;u++) for(d=60;d<=100;d++) begin
  srst(); e0=cyc+1; go(36,0); repeat(d-1) @(negedge ck); e1=cyc+1; clr(e1); go(37,u); repeat(200) @(negedge ck);
  $display("E2E_PAIR 36u0->37u%0d d %0d ctlm_fault %0d slice_faultmask %03x load37_at %0d first_write %0d last_write %0d writes s0 %0d s11 %0d",
           u,d,fault,fm(),ld_first-e1,fw-e1,lw-e1,nw0,nw11);
  if(fm()!=0||fault) dmin=1000; else if(dmin==1000) dmin=d;
 end
 // per-user boot install order 1..37 at the CTLM37-gate spacing 64 and at dmin-1 / dmin
 for(int t=0;t<3;t++) begin
  sp = (t==0) ? 65 : (t==1 ? dmin-1 : dmin);
  srst(); e0=cyc+1; clr(e0); nl=0;
  for(u=0;u<4;u++) for(s=1;s<=37;s++) begin go(s,u); nl++; repeat(sp-1) @(negedge ck); end
  repeat(200) @(negedge ck);
  $display("E2E_BOOT start_spacing %0d ranges %0d ctlm_fault %0d slice_faultmask %03x nload %0d writes s0 %0d s11 %0d last_write %0d",sp,nl,fault,fm(),nld,nw0,nw11,lw-e0);
 end
 $display("E2E_DONE dmin %0d",dmin);
 $finish;
end
endmodule
