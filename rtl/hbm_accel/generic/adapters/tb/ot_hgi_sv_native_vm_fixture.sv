`timescale 1ps/1fs
`default_nettype none
// Functional integration fixture only. No physical clock/pin or slot grant.
module ot_hgi_sv_native_vm_fixture(
 input wire clk,vclk,rst_n,
 input wire rg_req,wg_req,output wire rg_gnt,wg_gnt,
 input wire [511:0] rq,output wire[31:0]rq_cr,output wire[8223:0]rr,
 input wire [8959:0]wq,output wire[31:0]wcredit,wdone,
 input wire [337:0]su_q,bench_q,output wire[273:0]su_r,bench_r,
 output wire[420:0]fault,output wire[3:0]released
);
 wire[543:0]srq,drq;wire[8991:0]swq,dwq;
 wire[31:0]src,swc,swd,drc,dwc,dwd;wire[8223:0]srr,drr;
 wire[3:0]srg,swg,sra,swa,srreq,swreq,srd,swdn,sdr;
 wire[3:0]drg,dwg,dra,dwa,drreq,dwreq,dd;
 wire[31:0]scd,svd,dcd,dvd;wire[130:0]pf;wire[64:0]rf,wf;wire[159:0]parent_fault;
 wire[8256:0]legacy_r;wire[575:0]bank_status;
 ot_hgi_dma_native_read_owned #(.HARD_CLOCKS(1),.LEGACY_SLOTS(8),.REQUIRE_GRANT(0)) reads(
  .clk(clk),.rst_n(rst_n),.leaf_clk({64{clk}}),.legacy_q({rg_req,rq}),.legacy_r(legacy_r),
  .rgrant(srg),.rack(sra),.rreq(srreq),.drained(srd),.released(),
  .native_rq(srq),.native_credit(src),.native_rr(srr),.fault(rf));
 assign rr=legacy_r[8223:0];assign rq_cr=legacy_r[8255:8224];assign rg_gnt=legacy_r[8256];
 ot_hgi_sv_native_write_owned #(.HARD_CLOCKS(1),.LEGACY_SLOTS(8)) writes(
  .clk(clk),.rst_n(rst_n),.leaf_clk({64{clk}}),.legacy_q({wg_req,wq}),.legacy_credit(wcredit),.legacy_done(wdone),.legacy_grant(wg_gnt),
  .wgrant(swg),.wack(swa),.wreq(swreq),.drained(swdn),.released(),
  .native_wq(swq),.native_credit(swc),.native_done(swd),.fault(wf));
 assign sdr=srd&swdn&{4{!rg_req&&!wg_req}};
 ot_hgi_sv_native_packet_owned packets(.clk(clk),.rst_n(rst_n),.leaf_clk({128{clk}}),
  .su_q(su_q),.bench_q(bench_q),.su_r(su_r),.bench_r(bench_r),
  .rgrant(drg),.wgrant(dwg),.rack(dra),.wack(dwa),.rreq(drreq),.wreq(dwreq),.drained(dd),
  .native_rq(drq),.native_credit(drc),.native_rr(drr),.native_wq(dwq),.native_wcredit(dwc),.native_done(dwd),.fault(pf));
 ot_hbm_b2_native_owned4 #(.SU_NATIVE_RAW(1),.HARD_CLOCKS(1),.HARD_VM_CLOCKS(1),.HARD_CDC_CLOCKS(1),.HARD_COMMIT_CLOCKS(1),.VM_NC(4)) vehicle(
  .su_clk({4{clk}}),.quant_clk({4{clk}}),.dma_clk({4{clk}}),.vclk(vclk),.rst_n(rst_n),
  .station_clk({32{vclk}}),.commit_clk({32{vclk}}),.commit_rst_n({32{rst_n}}),
  .cdc_cclk({96{clk}}),.cdc_vclk({96{vclk}}),.cdc_crst_n({96{rst_n}}),.cdc_vrst_n({96{rst_n}}),
  .vm_child_clk({52{vclk}}),.vm_child_rst_n({52{rst_n}}),.relay_clk({24{vclk}}),.relay_rst_n({24{rst_n}}),
  .su_native_rq(srq),.su_native_wq(swq),.su_rreq(srreq),.su_wreq(swreq),.su_drained(sdr),.su_mirror(4'b0),
  .su_rq(512'b0),.su_rcredit(src),.su_rr(srr),.su_wq(8960'b0),.su_wcredit(swc),.su_done(swd),
  .su_rgrant(srg),.su_wgrant(swg),.su_rack(sra),.su_wack(swa),
  .quant_rec(2732'b0),.quant_mirror(4'b0),.quant_ret(),.quant_drained(),
  .dma_rreq(drreq),.dma_wreq(dwreq),.dma_peer_drained(dd),.dma_rq(drq),.dma_rcredit(drc),.dma_rr(drr),
  .dma_wq(dwq),.dma_wcredit(dwc),.dma_wdone(dwd),.dma_rgrant(drg),.dma_wgrant(dwg),.dma_rack(dra),.dma_wack(dwa),
  .dma_dq(8992'b0),.dma_dq_done(),.probe_clk({4{clk}}),.probe_permit(4'b0),.probe_mirror(4'b0),
  .probe_rq(512'b0),.probe_rcredit(),.probe_rr(),.probe_wq(8960'b0),.probe_wcredit(),.probe_done(),
  .su_cdrained(scd),.su_vdrained(svd),.dma_cdrained(dcd),.dma_vdrained(dvd),
  .vm_rgrant(),.vm_wgrant(),.bank_status(bank_status),.fault(parent_fault));
 assign fault={parent_fault,pf,wf,rf};
 assign released=sdr&dd&sra&swa&dra&dwa&~srg&~swg&~drg&~dwg;
endmodule
`default_nettype wire
