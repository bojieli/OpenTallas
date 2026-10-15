`timescale 1ns/1ps
`default_nettype none
// Logical eight-bank group, physically eight independently hardened leaves.
// All roots have the SAME compiler edge/phase; no CDC or extra stage is added.
module ot_hbm_vm_lg_static_split #(
    parameter integer READ_RETURN=10,WRITE_RETURN=7,MUT=0
)(
    input wire [7:0] clk,
    input wire rst_n,
    input wire [135:0] local_rq,far_rq,
    input wire [2247:0] local_wq,far_wq,
    input wire [7:0] local_read,local_write,
    output wire [135:0] near_rq,
    output wire [2247:0] near_wq,
    input wire [2055:0] near_rr,
    input wire [7:0] near_w_done,
    output wire [2055:0] local_rr,far_rr,
    output wire [7:0] local_w_done,far_w_done,
    output wire [7:0] bank_fault
);
    for(genvar b=0;b<8;b=b+1)begin:g_bank
        if (READ_RETURN==10 && WRITE_RETURN==7) begin:su
            hfd_vm_lg_su10 #(.MUT(MUT)) leaf(
            .clk(clk[b]),.rst_n(rst_n),.local_rq(local_rq[b*17+:17]),.far_rq(far_rq[b*17+:17]),
            .local_wq(local_wq[b*281+:281]),.far_wq(far_wq[b*281+:281]),
            .local_read(local_read[b]),.local_write(local_write[b]),
            .near_rq(near_rq[b*17+:17]),.near_wq(near_wq[b*281+:281]),
            .near_rr(near_rr[b*257+:257]),.near_w_done(near_w_done[b]),
            .local_rr(local_rr[b*257+:257]),.far_rr(far_rr[b*257+:257]),
            .local_w_done(local_w_done[b]),.far_w_done(far_w_done[b]),.fault(bank_fault[b]));
        end else if (READ_RETURN==14 && WRITE_RETURN==11) begin:sfu
            hfd_vm_lg_sfu14 #(.MUT(MUT)) leaf(
            .clk(clk[b]),.rst_n(rst_n),.local_rq(local_rq[b*17+:17]),.far_rq(far_rq[b*17+:17]),
            .local_wq(local_wq[b*281+:281]),.far_wq(far_wq[b*281+:281]),
            .local_read(local_read[b]),.local_write(local_write[b]),
            .near_rq(near_rq[b*17+:17]),.near_wq(near_wq[b*281+:281]),
            .near_rr(near_rr[b*257+:257]),.near_w_done(near_w_done[b]),
            .local_rr(local_rr[b*257+:257]),.far_rr(far_rr[b*257+:257]),
            .local_w_done(local_w_done[b]),.far_w_done(far_w_done[b]),.fault(bank_fault[b]));
        end else begin:parameterized
            ot_hbm_vm_lg_static_bank #(.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.MUT(MUT)) leaf(
            .clk(clk[b]),.rst_n(rst_n),.local_rq(local_rq[b*17+:17]),.far_rq(far_rq[b*17+:17]),
            .local_wq(local_wq[b*281+:281]),.far_wq(far_wq[b*281+:281]),
            .local_read(local_read[b]),.local_write(local_write[b]),
            .near_rq(near_rq[b*17+:17]),.near_wq(near_wq[b*281+:281]),
            .near_rr(near_rr[b*257+:257]),.near_w_done(near_w_done[b]),
            .local_rr(local_rr[b*257+:257]),.far_rr(far_rr[b*257+:257]),
            .local_w_done(local_w_done[b]),.far_w_done(far_w_done[b]),.fault(bank_fault[b]));
        end
    end
endmodule
`default_nettype wire
