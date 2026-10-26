`timescale 1ns/1ps
// Actual mapped TP8 constant-ROM provider for the native SU crom faces ca0..7/cq0..7.
// Wires only around the same real RTL as ot_qwen_native_memory_cluster g_crom:
// per group one physically mapped local buffer ot_qfd_su_cbuf_g_tp8 (local E5) in
// front of one far mask-ROM group ot_qfd_crom_gr TP8 (48 released masks, far E8,
// f_lat strap 8). SU ca packing (qfd_sp_su64_sfu_glue_entries):
//   ca = {stage[5:0], crom_addr[191:0], crom_re[7:0]}, cq = crom_q[511:0].
// No testbench storage, no response fabrication, no credits/ready: the compiler
// reserves the buffer fill window; constants_resident is an observation/fault check.
module qfd_native_crom8_tp8 #(
    parameter integer CROM_MUT = 0
) (
    input  wire [7:0]   crom_ck,
    input  wire [7:0]   cbuf_ck,
    input  wire         rst_n,
    input  wire         tok_start,
    input  wire [17:0]  tpos,
    input  wire [205:0] ca0, ca1, ca2, ca3, ca4, ca5, ca6, ca7,
    output wire [511:0] cq0, cq1, cq2, cq3, cq4, cq5, cq6, cq7,
    output wire [7:0]   constants_resident,
    output wire [47:0]  constants_resident_stage,
    output wire [15:0]  crom_fault_code,
    output wire         fault
);
    wire [206*8-1:0] ca = {ca7, ca6, ca5, ca4, ca3, ca2, ca1, ca0};
    wire [4095:0] cq;
    assign {cq7, cq6, cq5, cq4, cq3, cq2, cq1, cq0} = cq;
    wire [7:0] group_fault;
    genvar group_id;
    generate for (group_id = 0; group_id < 8; group_id = group_id + 1) begin : g_crom
        wire [205:0] req = ca[206*group_id +: 206];
        wire [7:0] far_re; wire [191:0] far_addr; wire [5:0] far_stage;
        wire [511:0] far_q; wire far_fault; wire [1:0] far_fault_code;
        ot_qfd_su_cbuf_g_tp8 u_cbuf (
            .clk(cbuf_ck[group_id]), .rst_n(rst_n),
            .crom_re(req[7:0]), .crom_addr(req[199:8]), .crom_stage(req[205:200]),
            .crom_q(cq[512*group_id +: 512]),
            .stage(req[205:200]), .tok_start(tok_start), .tpos(tpos), .grp(3'(group_id)),
            .st_rdy(constants_resident[group_id]), .st_rdy_stage(constants_resident_stage[6*group_id +: 6]),
            .f_re(far_re), .f_addr(far_addr), .f_stage(far_stage), .f_q(far_q), .f_fault(far_fault),
            .f_lat(5'd8), .fault(group_fault[group_id]), .fault_code(crom_fault_code[2*group_id +: 2])
        );
        ot_qfd_crom_gr #(.TP(8), .IMG_LB(8*group_id), .MUT(CROM_MUT)) u_rom (
            .clk(crom_ck[group_id]), .rst_n(rst_n),
            .crom_re(far_re), .crom_addr(far_addr), .crom_stage(far_stage),
            .crom_lb(6'(8*group_id)), .crom_q(far_q),
            .fault(far_fault), .fault_code(far_fault_code)
        );
    end endgenerate
    assign fault = |group_fault;
endmodule
