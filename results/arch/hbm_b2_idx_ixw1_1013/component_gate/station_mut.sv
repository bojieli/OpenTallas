`timescale 1ns/1ps
`default_nettype none
// SW wide slot5. The accepted station protocol is unchanged; unused high24
// lanes are tied at every boundary and disappear in synthesis. Native sec16
// is retained by REQW17/281. Two independent burst owners, eight lanes each.
module ot_hgi_idx_b2_station(
 input wire clk,rst_n,
 output wire [5:0] r_up_req,output wire [135:0] r_up_q,input wire [5:0] r_up_gnt,
 input wire [7:0] r_up_cr,input wire [2055:0] r_up_rsp,
 input wire [5:0] r_dn_req,input wire [135:0] r_dn_q,output wire [5:0] r_dn_gnt,
 output wire [7:0] r_dn_cr,output wire [2055:0] r_dn_rsp,
 input wire r_req,output wire r_gnt,input wire [135:0] rq,
 output wire [7:0] rq_cr,output wire [2055:0] rr,
 output wire [5:0] w_up_req,output wire [2247:0] w_up_q,input wire [5:0] w_up_gnt,
 input wire [7:0] w_up_cr,w_up_rsp,
 input wire [5:0] w_dn_req,input wire [2247:0] w_dn_q,output wire [5:0] w_dn_gnt,
 output wire [7:0] w_dn_cr,w_dn_rsp,
 input wire w_req,output wire w_gnt,input wire [2247:0] wq,
 output wire [7:0] wq_cr,wq_done);
 wire [543:0] ruq;wire [31:0] rdcr,rlcr;wire [8223:0] rdrsp,rlrsp;
 wire [8991:0] wuq;wire [31:0] wdcr,wdrsp,wlcr,wlrsp;
 assign r_up_q=ruq[135:0];assign r_dn_cr=rdcr[7:0];assign r_dn_rsp=rdrsp[2055:0];
 assign rq_cr=rlcr[7:0];assign rr=rlrsp[2055:0];
 assign w_up_q=wuq[2247:0];assign w_dn_cr=wdcr[7:0];assign w_dn_rsp=wdrsp[7:0];
 assign wq_cr=wlcr[7:0];assign wq_done=wlrsp[7:0];
 ot_hgi_vm_lanestation #(.K(6),.ID(4),.REQW(17),.RSPW(257)) u_read(
 .clk(clk),.rst_n(rst_n),.up_req(r_up_req),.up_q(ruq),.up_gnt(r_up_gnt),
 .up_cr({24'd0,r_up_cr}),.up_rsp({6168'd0,r_up_rsp}),.dn_req(r_dn_req),.dn_q({408'd0,r_dn_q}),
 .dn_gnt(r_dn_gnt),.dn_cr(rdcr),.dn_rsp(rdrsp),.l_req(r_req),.l_gnt(r_gnt),
 .l_q({408'd0,rq}),.l_cr(rlcr),.l_rsp(rlrsp));
 ot_hgi_vm_lanestation #(.K(6),.ID(4),.REQW(281),.RSPW(1)) u_write(
 .clk(clk),.rst_n(rst_n),.up_req(w_up_req),.up_q(wuq),.up_gnt(w_up_gnt),
 .up_cr({24'd0,w_up_cr}),.up_rsp({24'd0,w_up_rsp}),.dn_req(w_dn_req),.dn_q({6744'd0,w_dn_q}),
 .dn_gnt(w_dn_gnt),.dn_cr(wdcr),.dn_rsp(wdrsp),.l_req(w_req),.l_gnt(w_gnt),
 .l_q({6744'd0,wq}),.l_cr(wlcr),.l_rsp(wlrsp));
endmodule
`default_nettype wire
