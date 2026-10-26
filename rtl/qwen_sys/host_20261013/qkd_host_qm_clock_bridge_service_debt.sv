// DEFAULT_OFF separately named warm epoch permission profile.
`timescale 1ns/1ps
// Wires-only assembly, packet833 and QMhost1000 are UNRELATED clock domains.
// TWO additional dedicated W546/PIPE2 CDC leaves; neither PHY pair nor any
// collective CDC instance is reused. All returned credits are capacity only.
// entry clocks cq/qw form packet family; qp/qr/ccw form QM-host family;
// ccr forms packet family. Physical compensation is required inside families.
module qkd_host_qm_clock_bridge_service_debt #(parameter integer MUT=0,ENABLE_SERVICE=0)(
 input wire cq,qw,qr,qp,ccw,ccr,rst_n,
 input wire ing_v,ingest_permission,input wire[1:0]ing_cls,input wire[511:0]ing_d,output wire[4:0]ing_crn,
 output wire qm_v,output wire[1:0]qm_cls,output wire[511:0]qm_d,input wire[4:0]qm_crn,
 input wire done_v,input wire[63:0]done_d,output wire done_cr,
 output wire packet_done_v,output wire[63:0]packet_done_d,input wire packet_done_cr,
 output wire[5:0]faults,output wire queue_quiet
);
 wire qv,qcr,return_cr;wire[545:0]qd,hd,cd;
 qkd_host_qm_ingress16_service_debt #(.ENABLE_SERVICE(ENABLE_SERVICE),.MUT(MUT==4?3:(MUT==1?1:(MUT==2?2:0))))u_queue(.ck(cq),.rst_n(rst_n),.in_v(ing_v),.allow(ingest_permission),.in_cls(ing_cls),.in_d(ing_d),.in_crn(ing_crn),.out_v(qv),.out_d(qd),.out_cr(qcr),.fault(faults[0]),.queue_quiet(queue_quiet));
 ot_qwen_die_cdc_ch #(.W(546),.PIPE(2))u_ing(.wclk(qw),.wrst_n(rst_n),.i_v(qv),.i_d(qd),.i_cr(qcr),.w_fault(faults[1]),.rclk(qr),.rrst_n(rst_n),.o_v(qm_v),.o_d(hd),.o_cr(return_cr),.r_fault(faults[2]));
 assign qm_cls=hd[513:512];assign qm_d=hd[511:0];
 qkd_host_qm_credit_pacer #(.MUT(MUT==3?1:0))u_pacer(.clk_h(qp),.rst_n(rst_n),.in_v(qm_v),.in_crn(qm_crn),.out_cr(return_cr),.fault(faults[3]));
 ot_qwen_die_cdc_ch #(.W(546),.PIPE(2))u_done(.wclk(ccw),.wrst_n(rst_n),.i_v(done_v),.i_d({482'd0,done_d}),.i_cr(done_cr),.w_fault(faults[4]),.rclk(ccr),.rrst_n(rst_n),.o_v(packet_done_v),.o_d(cd),.o_cr(packet_done_cr),.r_fault(faults[5]));
 assign packet_done_d=cd[63:0];
endmodule
