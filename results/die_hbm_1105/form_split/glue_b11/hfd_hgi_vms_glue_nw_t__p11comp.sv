`timescale 1ns/1ps
`default_nettype none
// HBM-FORM-SPLIT-8+REFORM-B11 (glue_d15r RE-FORM, owner 11-03 two strikes -> conservative form): hfd_hgi_vms_glue_nw_t
// (331,797 placed cells, 2 GRT congestion strikes) split on its natural sub// crossing stage of the composition: XREG=0 wires (plan form), XREG=2 the two kit face flops (bench form)
module hfd_hgi_vms_gnw_xing #(parameter integer W=1, parameter integer XREG=0) (input wire clk, input wire [W-1:0] d, output wire [W-1:0] q);
    generate if(XREG==0) begin : g_w
        assign q=d;
    end else begin : g_r
        reg [W-1:0] s [0:XREG-1];
        always @(posedge clk) begin
            s[0]<=d;
            for(integer i=1;i<XREG;i=i+1) s[i]<=s[i-1];
        end
        assign q=s[XREG-1];
    end endgenerate
endmodule
module hfd_hgi_vms_glue_nw_t__p11comp #(parameter integer XREG=0, parameter integer DMUT=0) (
    input wire clk,
    input wire rst_n,
    input wire [1:0] client_seq,
    input wire response_enable,
    input wire [1:0] response_seq,
    input wire [7:0] bank_enable,
    input wire [7:0] bank_client,
    input wire [1:0] hub_ring_enable,
    input wire [1:0] hub_ring_client,
    input wire [2223:0] cw_in,
    input wire [2223:0] ccw_in,
    output wire [2223:0] cw_out,
    output wire [2223:0] ccw_out,
    input wire [1:0] ring_tx_enable,
    input wire [5:0] ring_tx_source,
    input wire replay_enable,
    input wire replay_source,
    output wire [275:0] b0_xq,
    output wire [275:0] b0_xq2,
    input wire b0_xq_done,
    input wire b0_xq2_done,
    input wire [275:0] b0_eg,
    output wire [284:0] b0_pq,
    input wire [265:0] b0_pr,
    input wire [17:0] b0_status,
    input wire b0_flt,
    output wire [275:0] b1_xq,
    output wire [275:0] b1_xq2,
    input wire b1_xq_done,
    input wire b1_xq2_done,
    input wire [275:0] b1_eg,
    output wire [284:0] b1_pq,
    input wire [265:0] b1_pr,
    input wire [17:0] b1_status,
    input wire b1_flt,
    output wire [275:0] b2_xq,
    output wire [275:0] b2_xq2,
    input wire b2_xq_done,
    input wire b2_xq2_done,
    input wire [275:0] b2_eg,
    output wire [284:0] b2_pq,
    input wire [265:0] b2_pr,
    input wire [17:0] b2_status,
    input wire b2_flt,
    output wire [275:0] b3_xq,
    output wire [275:0] b3_xq2,
    input wire b3_xq_done,
    input wire b3_xq2_done,
    input wire [275:0] b3_eg,
    output wire [284:0] b3_pq,
    input wire [265:0] b3_pr,
    input wire [17:0] b3_status,
    input wire b3_flt,
    output wire [275:0] b4_xq,
    output wire [275:0] b4_xq2,
    input wire b4_xq_done,
    input wire b4_xq2_done,
    input wire [275:0] b4_eg,
    output wire [284:0] b4_pq,
    input wire [265:0] b4_pr,
    input wire [17:0] b4_status,
    input wire b4_flt,
    output wire [275:0] b5_xq,
    output wire [275:0] b5_xq2,
    input wire b5_xq_done,
    input wire b5_xq2_done,
    input wire [275:0] b5_eg,
    output wire [284:0] b5_pq,
    input wire [265:0] b5_pr,
    input wire [17:0] b5_status,
    input wire b5_flt,
    output wire [275:0] b6_xq,
    output wire [275:0] b6_xq2,
    input wire b6_xq_done,
    input wire b6_xq2_done,
    input wire [275:0] b6_eg,
    output wire [284:0] b6_pq,
    input wire [265:0] b6_pr,
    input wire [17:0] b6_status,
    input wire b6_flt,
    output wire [275:0] b7_xq,
    output wire [275:0] b7_xq2,
    input wire b7_xq_done,
    input wire b7_xq2_done,
    input wire [275:0] b7_eg,
    output wire [284:0] b7_pq,
    input wire [265:0] b7_pr,
    input wire [17:0] b7_status,
    input wire b7_flt,
    output wire [2:0] hub_status,
    output wire [1:0] mirror_busy,
    output wire [18:0] vmstat,
    output wire [2:0] ring_fault
);
    wire [289:0] h_pi0, a_pi0;
    hfd_hgi_vms_gnw_xing #(.W(290),.XREG(XREG)) x_pi0(.clk(clk),.d(h_pi0),.q(a_pi0));
    wire [289:0] h_pi1, b_pi1;
    hfd_hgi_vms_gnw_xing #(.W(290),.XREG(XREG)) x_pi1(.clk(clk),.d(h_pi1),.q(b_pi1));
    wire [263:0] a_cco0, h_cco0;
    hfd_hgi_vms_gnw_xing #(.W(264),.XREG(XREG)) x_cco0(.clk(clk),.d(a_cco0),.q(h_cco0));
    wire [263:0] b_cco1, h_cco1;
    hfd_hgi_vms_gnw_xing #(.W(264),.XREG(XREG)) x_cco1(.clk(clk),.d(b_cco1),.q(h_cco1));
    wire [287:0] a_rce0, h_rce0;
    hfd_hgi_vms_gnw_xing #(.W(288),.XREG(XREG)) x_rce0(.clk(clk),.d(a_rce0),.q(h_rce0));
    wire [287:0] b_rce1, h_rce1;
    hfd_hgi_vms_gnw_xing #(.W(288),.XREG(XREG)) x_rce1(.clk(clk),.d(b_rce1),.q(h_rce1));
    wire [265:0] h_ri0, a_ri0;
    hfd_hgi_vms_gnw_xing #(.W(266),.XREG(XREG)) x_ri0(.clk(clk),.d(h_ri0),.q(a_ri0));
    wire [265:0] h_ri1, b_ri1;
    hfd_hgi_vms_gnw_xing #(.W(266),.XREG(XREG)) x_ri1(.clk(clk),.d(h_ri1),.q(b_ri1));
    wire [2:0] a_wk01, b_wk01;
    hfd_hgi_vms_gnw_xing #(.W(3),.XREG(XREG)) x_wk01(.clk(clk),.d(a_wk01),.q(b_wk01));
    wire [2:0] b_wk10, a_wk10;
    hfd_hgi_vms_gnw_xing #(.W(3),.XREG(XREG)) x_wk10(.clk(clk),.d(b_wk10),.q(a_wk10));
    wire [0:0] a_ack01, b_ack01;
    hfd_hgi_vms_gnw_xing #(.W(1),.XREG(XREG)) x_ack01(.clk(clk),.d(a_ack01),.q(b_ack01));
    wire [0:0] b_ack10, a_ack10;
    hfd_hgi_vms_gnw_xing #(.W(1),.XREG(XREG)) x_ack10(.clk(clk),.d(b_ack10),.q(a_ack10));
    wire [0:0] a_rf0, h_rf0;
    hfd_hgi_vms_gnw_xing #(.W(1),.XREG(XREG)) x_rf0(.clk(clk),.d(a_rf0),.q(h_rf0));
    wire [0:0] b_rf1, h_rf1;
    hfd_hgi_vms_gnw_xing #(.W(1),.XREG(XREG)) x_rf1(.clk(clk),.d(b_rf1),.q(h_rf1));
    assign ring_fault[0]=a_rf0; assign ring_fault[1]=b_rf1;
    hfd_hgi_vms_gnw_cw #(.DMUT(DMUT)) u_a(.clk(clk),.rst_n(rst_n),.tx_enable(ring_tx_enable[0]),.tx_source(ring_tx_source[2:0]),.cw_in(cw_in),.cw_out(cw_out),.b0_xq(b0_xq),.b0_xq_done(b0_xq_done),.b0_eg(b0_eg),.b1_xq(b1_xq),.b1_xq_done(b1_xq_done),.b1_eg(b1_eg),.b2_xq(b2_xq),.b2_xq_done(b2_xq_done),.b2_eg(b2_eg),.b3_xq(b3_xq),.b3_xq_done(b3_xq_done),.b3_eg(b3_eg),.b4_xq(b4_xq),.b4_xq_done(b4_xq_done),.b4_eg(b4_eg),.b5_xq(b5_xq),.b5_xq_done(b5_xq_done),.b5_eg(b5_eg),.b6_xq(b6_xq),.b6_xq_done(b6_xq_done),.b6_eg(b6_eg),.b7_xq(b7_xq),.b7_xq_done(b7_xq_done),.b7_eg(b7_eg),.pi(a_pi0),.rce(a_rce0),.ri(a_ri0),.cco(a_cco0),.wko(a_wk01),.wki(a_wk10),.ack_o(a_ack01),.ack_i(a_ack10),.mirror_busy(mirror_busy[0]),.fault(a_rf0));
    hfd_hgi_vms_gnw_ccw #(.DMUT(DMUT)) u_b(.clk(clk),.rst_n(rst_n),.tx_enable(ring_tx_enable[1]),.tx_source(ring_tx_source[5:3]),.ccw_in(ccw_in),.ccw_out(ccw_out),.b0_xq2(b0_xq2),.b0_xq2_done(b0_xq2_done),.b0_eg(b0_eg),.b1_xq2(b1_xq2),.b1_xq2_done(b1_xq2_done),.b1_eg(b1_eg),.b2_xq2(b2_xq2),.b2_xq2_done(b2_xq2_done),.b2_eg(b2_eg),.b3_xq2(b3_xq2),.b3_xq2_done(b3_xq2_done),.b3_eg(b3_eg),.b4_xq2(b4_xq2),.b4_xq2_done(b4_xq2_done),.b4_eg(b4_eg),.b5_xq2(b5_xq2),.b5_xq2_done(b5_xq2_done),.b5_eg(b5_eg),.b6_xq2(b6_xq2),.b6_xq2_done(b6_xq2_done),.b6_eg(b6_eg),.b7_xq2(b7_xq2),.b7_xq2_done(b7_xq2_done),.b7_eg(b7_eg),.pi(b_pi1),.rce(b_rce1),.ri(b_ri1),.cco(b_cco1),.wko(b_wk10),.wki(b_wk01),.ack_o(b_ack10),.ack_i(b_ack01),.mirror_busy(mirror_busy[1]),.fault(b_rf1));
    hfd_hgi_vms_gnw_hub #(.DMUT(DMUT)) u_h(.clk(clk),.rst_n(rst_n),.client_seq(client_seq),.response_enable(response_enable),.response_seq(response_seq),.bank_enable(bank_enable),.bank_client(bank_client),.hub_ring_enable(hub_ring_enable),.hub_ring_client(hub_ring_client),.replay_enable(replay_enable),.replay_source(replay_source),.b0_pq(b0_pq),.b0_pr(b0_pr),.b0_status(b0_status),.b0_flt(b0_flt),.b1_pq(b1_pq),.b1_pr(b1_pr),.b1_status(b1_status),.b1_flt(b1_flt),.b2_pq(b2_pq),.b2_pr(b2_pr),.b2_status(b2_status),.b2_flt(b2_flt),.b3_pq(b3_pq),.b3_pr(b3_pr),.b3_status(b3_status),.b3_flt(b3_flt),.b4_pq(b4_pq),.b4_pr(b4_pr),.b4_status(b4_status),.b4_flt(b4_flt),.b5_pq(b5_pq),.b5_pr(b5_pr),.b5_status(b5_status),.b5_flt(b5_flt),.b6_pq(b6_pq),.b6_pr(b6_pr),.b6_status(b6_status),.b6_flt(b6_flt),.b7_pq(b7_pq),.b7_pr(b7_pr),.b7_status(b7_status),.b7_flt(b7_flt),.hub_status(hub_status),.vmstat(vmstat),.replay_fault(ring_fault[2]),.pi0(h_pi0),.pi1(h_pi1),.cco0(h_cco0),.cco1(h_cco1),.rce0(h_rce0),.rce1(h_rce1),.ri0(h_ri0),.ri1(h_ri1),.ring_fault0(h_rf0),.ring_fault1(h_rf1));
endmodule
`default_nettype wire
