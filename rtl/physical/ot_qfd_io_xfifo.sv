`timescale 1ns/1ps
// Compute die TP8 IO crossing parent. Real credit converters, no pin-only shells.
// The die supplies each boundary clock at phi-R of its own hardened leaf.
// The collective sends with 64 SerDes, 32 UCIe P/R initial credits; its
// receive queues have 64 SerDes, 64 P and 32 R entries. The adapter
// starts with four c-side and r-side credits; its board BDP buffer is local.
// Local sequencer port retains its reservation-aware 32-credit conversion.
// Physical variants for these credit counts require new views and slot fit;
// the existing IBUF4 channel view cannot represent these instances.
module qfd_io_xfifo (
    input wire rst_n,
    input wire ck_local, ck_seq,
    input wire i_seq_coll_v,
    input wire [545:0] i_seq_coll,
    output wire i_seq_coll_cr,
    output wire o_seq_coll_v,
    output wire [545:0] o_seq_coll,
    input wire o_seq_coll_cr,
    input wire i_coll_seq_v,
    input wire [516:0] i_coll_seq,
    output wire o_coll_seq_v,
    output wire [516:0] o_coll_seq,
    output wire [21:0] fault,
    input wire up_wck, up_rck,
    input wire up_i_v,
    input wire [545:0] up_i_d,
    output wire up_i_cr,
    output wire up_o_v,
    output wire [545:0] up_o_d,
    input wire up_o_cr,
    input wire dp_wck, dp_rck,
    input wire dp_i_v,
    input wire [545:0] dp_i_d,
    output wire dp_i_cr,
    output wire dp_o_v,
    output wire [545:0] dp_o_d,
    input wire dp_o_cr,
    input wire ur_wck, ur_rck,
    input wire ur_i_v,
    input wire [513:0] ur_i_d,
    output wire ur_i_cr,
    output wire ur_o_v,
    output wire [513:0] ur_o_d,
    input wire ur_o_cr,
    input wire dr_wck, dr_rck,
    input wire dr_i_v,
    input wire [513:0] dr_i_d,
    output wire dr_i_cr,
    output wire dr_o_v,
    output wire [513:0] dr_o_d,
    input wire dr_o_cr,
    input wire sx0_wck, sx0_rck,
    input wire sx0_i_v,
    input wire [545:0] sx0_i_d,
    output wire sx0_i_cr,
    output wire sx0_o_v,
    output wire [545:0] sx0_o_d,
    input wire sx0_o_cr,
    input wire sx1_wck, sx1_rck,
    input wire sx1_i_v,
    input wire [545:0] sx1_i_d,
    output wire sx1_i_cr,
    output wire sx1_o_v,
    output wire [545:0] sx1_o_d,
    input wire sx1_o_cr,
    input wire sx2_wck, sx2_rck,
    input wire sx2_i_v,
    input wire [545:0] sx2_i_d,
    output wire sx2_i_cr,
    output wire sx2_o_v,
    output wire [545:0] sx2_o_d,
    input wire sx2_o_cr,
    input wire sr0_wck, sr0_rck,
    input wire sr0_i_v,
    input wire [545:0] sr0_i_d,
    output wire sr0_i_cr,
    output wire sr0_o_v,
    output wire [545:0] sr0_o_d,
    input wire sr0_o_cr,
    input wire sr1_wck, sr1_rck,
    input wire sr1_i_v,
    input wire [545:0] sr1_i_d,
    output wire sr1_i_cr,
    output wire sr1_o_v,
    output wire [545:0] sr1_o_d,
    input wire sr1_o_cr,
    input wire sr2_wck, sr2_rck,
    input wire sr2_i_v,
    input wire [545:0] sr2_i_d,
    output wire sr2_i_cr,
    output wire sr2_o_v,
    output wire [545:0] sr2_o_d,
    input wire sr2_o_cr
);
    qfd_xf_ch #(.W(546),.IBUF(32),.OCRED(4),.IBMEM(1)) u_up (
        .wck(up_wck),.rck(up_rck),.rst_n(rst_n),
        .i_v(up_i_v),.i_d(up_i_d),.i_cr(up_i_cr),.w_fault(fault[0]),
        .o_v(up_o_v),.o_d(up_o_d),.o_cr(up_o_cr),.r_fault(fault[1]));
    qfd_xf_ch #(.W(546),.IBUF(4),.OCRED(64)) u_dp (
        .wck(dp_wck),.rck(dp_rck),.rst_n(rst_n),
        .i_v(dp_i_v),.i_d(dp_i_d),.i_cr(dp_i_cr),.w_fault(fault[2]),
        .o_v(dp_o_v),.o_d(dp_o_d),.o_cr(dp_o_cr),.r_fault(fault[3]));
    wire [545:0] ur_padded;
    assign ur_o_d=ur_padded[513:0];
    qfd_xf_ch #(.W(546),.IBUF(32),.OCRED(4),.IBMEM(1)) u_ur (
        .wck(ur_wck),.rck(ur_rck),.rst_n(rst_n),
        .i_v(ur_i_v),.i_d({32'b0,ur_i_d}),.i_cr(ur_i_cr),.w_fault(fault[4]),
        .o_v(ur_o_v),.o_d(ur_padded),.o_cr(ur_o_cr),.r_fault(fault[5]));
    wire [545:0] dr_padded;
    assign dr_o_d=dr_padded[513:0];
    qfd_xf_ch #(.W(546),.IBUF(4),.OCRED(32)) u_dr (
        .wck(dr_wck),.rck(dr_rck),.rst_n(rst_n),
        .i_v(dr_i_v),.i_d({32'b0,dr_i_d}),.i_cr(dr_i_cr),.w_fault(fault[6]),
        .o_v(dr_o_v),.o_d(dr_padded),.o_cr(dr_o_cr),.r_fault(fault[7]));
    qfd_xf_ch #(.W(546),.IBUF(64),.OCRED(4),.IBMEM(2)) u_sx0 (
        .wck(sx0_wck),.rck(sx0_rck),.rst_n(rst_n),
        .i_v(sx0_i_v),.i_d(sx0_i_d),.i_cr(sx0_i_cr),.w_fault(fault[8]),
        .o_v(sx0_o_v),.o_d(sx0_o_d),.o_cr(sx0_o_cr),.r_fault(fault[9]));
    qfd_xf_ch #(.W(546),.IBUF(64),.OCRED(4),.IBMEM(2)) u_sx1 (
        .wck(sx1_wck),.rck(sx1_rck),.rst_n(rst_n),
        .i_v(sx1_i_v),.i_d(sx1_i_d),.i_cr(sx1_i_cr),.w_fault(fault[10]),
        .o_v(sx1_o_v),.o_d(sx1_o_d),.o_cr(sx1_o_cr),.r_fault(fault[11]));
    qfd_xf_ch #(.W(546),.IBUF(64),.OCRED(4),.IBMEM(2)) u_sx2 (
        .wck(sx2_wck),.rck(sx2_rck),.rst_n(rst_n),
        .i_v(sx2_i_v),.i_d(sx2_i_d),.i_cr(sx2_i_cr),.w_fault(fault[12]),
        .o_v(sx2_o_v),.o_d(sx2_o_d),.o_cr(sx2_o_cr),.r_fault(fault[13]));
    qfd_xf_ch #(.W(546),.IBUF(4),.OCRED(64)) u_sr0 (
        .wck(sr0_wck),.rck(sr0_rck),.rst_n(rst_n),
        .i_v(sr0_i_v),.i_d(sr0_i_d),.i_cr(sr0_i_cr),.w_fault(fault[14]),
        .o_v(sr0_o_v),.o_d(sr0_o_d),.o_cr(sr0_o_cr),.r_fault(fault[15]));
    qfd_xf_ch #(.W(546),.IBUF(4),.OCRED(64)) u_sr1 (
        .wck(sr1_wck),.rck(sr1_rck),.rst_n(rst_n),
        .i_v(sr1_i_v),.i_d(sr1_i_d),.i_cr(sr1_i_cr),.w_fault(fault[16]),
        .o_v(sr1_o_v),.o_d(sr1_o_d),.o_cr(sr1_o_cr),.r_fault(fault[17]));
    qfd_xf_ch #(.W(546),.IBUF(4),.OCRED(64)) u_sr2 (
        .wck(sr2_wck),.rck(sr2_rck),.rst_n(rst_n),
        .i_v(sr2_i_v),.i_d(sr2_i_d),.i_cr(sr2_i_cr),.w_fault(fault[18]),
        .o_v(sr2_o_v),.o_d(sr2_o_d),.o_cr(sr2_o_cr),.r_fault(fault[19]));
    qfd_coll_xfifo_native u_local (
        .ck(ck_local),.ckd(ck_seq),.rst_n(rst_n),
        .i_seq_coll_v(i_seq_coll_v),.i_seq_coll(i_seq_coll),.i_seq_coll_cr(i_seq_coll_cr),
        .o_seq_coll_v(o_seq_coll_v),.o_seq_coll(o_seq_coll),.o_seq_coll_cr(o_seq_coll_cr),
        .i_coll_seq_v(i_coll_seq_v),.i_coll_seq(i_coll_seq),
        .o_coll_seq_v(o_coll_seq_v),.o_coll_seq(o_coll_seq),
        .fault_ck(fault[20]),.fault_ckd(fault[21]));
endmodule
