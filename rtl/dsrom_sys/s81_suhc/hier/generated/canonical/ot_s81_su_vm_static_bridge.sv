`timescale 1ns/1ps
`default_nettype none
// Fixed 3:4 serial-SU <-> stream-VM bridge. No queue, credit, ready or replay.
// All clock/reset categories are actual independent entries, delivered from
// one related-clock PLL/common reset epoch. Physical phi-R remains a die gate.
// The VM response path has ONE real 513-bit stream stage before x43. This
// compensates the actual READ_PIPE1 core L13 response phase; it never waits for
// a valid or changes the calendar. Exact end-to-end ages require the native
// dual-clock composition gate, not the ideal same-clock component fixtures.
module ot_s81_su_vm_static_bridge (
    input wire [15:0] ck_req_s,ck_req_t,ck_rsp_pad_t,ck_rsp_t,ck_rsp_s,ck_wr_s,ck_wr_t,
    input wire [15:0] rst_req_s_n,rst_req_t_n,rst_rsp_pad_t_n,rst_rsp_t_n,rst_rsp_s_n,rst_wr_s_n,rst_wr_t_n,
    // SU serial-domain pins, before/after the actual related-clock bridge.
    input wire [15:0] s_rq_v,
    input wire [223:0] s_rq_row,
    output wire [15:0] s_rs_v,
    output wire [8191:0] s_rs_data,
    input wire [15:0] s_wq_v,
    input wire [223:0] s_wq_row,
    input wire [255:0] s_wq_mask,
    input wire [8191:0] s_wq_data,
    // Actual stream-domain VM f_su_* / t_su_* pins, not memory substitutes.
    output wire [15:0] t_rq_v,
    output wire [223:0] t_rq_row,
    input wire [15:0] t_rs_v,
    input wire [8191:0] t_rs_data,
    output wire [15:0] t_wq_v,
    output wire [223:0] t_wq_row,
    output wire [255:0] t_wq_mask,
    output wire [8191:0] t_wq_data,
    output wire [15:0] req_fault,rsp_fault,wr_fault,
    output wire fault
);
    genvar p;
    generate for(p=0;p<16;p=p+1) begin:g_port
        ot_s81_vm_x34 #(.W(14)) u_req(
            .s_ck(ck_req_s[p]),.s_rst_n(rst_req_s_n[p]),
            .s_v(s_rq_v[p]),.s_d(s_rq_row[14*p+:14]),
            .t_ck(ck_req_t[p]),.t_rst_n(rst_req_t_n[p]),
            .o_v(t_rq_v[p]),.o_d(t_rq_row[14*p+:14]),.fault(req_fault[p]));
        reg pad_v;
        reg [511:0] pad_data;
        always @(posedge ck_rsp_pad_t[p] or negedge rst_rsp_pad_t_n[p])
            if(!rst_rsp_pad_t_n[p])pad_v<=1'b0;
            else pad_v<=t_rs_v[p];
        always @(posedge ck_rsp_pad_t[p])pad_data<=t_rs_data[512*p+:512];
        ot_s81_vm_x43 #(.W(512)) u_rsp(
            .t_ck(ck_rsp_t[p]),.t_rst_n(rst_rsp_t_n[p]),.s_v(pad_v),.s_d(pad_data),
            .s_ck(ck_rsp_s[p]),.s_rst_n(rst_rsp_s_n[p]),
            .o_v(s_rs_v[p]),.o_d(s_rs_data[512*p+:512]),.fault(rsp_fault[p]));
        wire [541:0] wr;
        ot_s81_vm_x34 #(.W(542)) u_write(
            .s_ck(ck_wr_s[p]),.s_rst_n(rst_wr_s_n[p]),.s_v(s_wq_v[p]),
            .s_d({s_wq_data[512*p+:512],s_wq_mask[16*p+:16],s_wq_row[14*p+:14]}),
            .t_ck(ck_wr_t[p]),.t_rst_n(rst_wr_t_n[p]),
            .o_v(t_wq_v[p]),.o_d(wr),.fault(wr_fault[p]));
        assign t_wq_row[14*p+:14]=wr[13:0];
        assign t_wq_mask[16*p+:16]=wr[29:14];
        assign t_wq_data[512*p+:512]=wr[541:30];
    end endgenerate
    assign fault=(|req_fault)|(|rsp_fault)|(|wr_fault);
endmodule
`default_nettype wire
