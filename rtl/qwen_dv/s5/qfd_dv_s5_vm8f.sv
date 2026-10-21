`timescale 1ns/1ps
// =====================================================================================================================
// QW-SLICE2R 10-20 (Q.STA.SLICE.2): WIRES-ONLY flat parent of the slice2 VM8 leaf group = qfd_dv_s5_vm8x SPLIT 1
// (CROM bound: qfd_dv_s8x_crom; BTAB + PROG as two leaves), the input of tools/landed_parent/lp.py
// (spec tools/landed_parent/specs/qfd_dv_s5_vm8f.json).  Six CLOSED leaves, each its own clock region; every port is in
// the neighbour (SU / slice2 core) region r_io, so every port -> leaf and leaf -> port net is a LANDED crossing
// (mesochronous fixed-latency ring, owner clock rule 10-20 08:55).  There is no leaf -> leaf net (the VM8 split cut).
// Answers / faults: every leaf output is LANDED into r_io and captured by qfd_dv_s5_vm8out (a capture register child that
// sits in r_io), so every boundary port of the group is on ONE clock (ck_r_io = the neighbour's region clock): the
// capture register is the port launch flop.  Faults: one bit per leaf (the consumer ORs them; sticky OR distributes).
// Differences from qfd_dv_s5_vm8x: no MUT / generate (leaves at defaults), tw_addr / tw_data slices on wires.
// =====================================================================================================================
module qfd_dv_s5_vm8f (
    input  wire            ck,
    input  wire            rst_n,
    input  wire [7:0]      a_re, b_re, c_re,
    input  wire [8*24-1:0] a_addr, b_addr, c_addr,
    output wire [8*32-1:0] a_q, b_q, c_q,
    input  wire [7:0]      cr_re,
    input  wire [8*24-1:0] cr_addr,
    output wire [8*64-1:0] cr_q,
    input  wire            bs_re,
    input  wire [23:0]     bs_addr,
    output wire [255:0]    bs_q,
    input  wire            p_re,
    input  wire [8:0]      p_idx,
    output wire [456:0]    p_q,
    input  wire [7:0]      vm_we,
    input  wire [8*24-1:0] vm_waddr,
    input  wire [8*32-1:0] vm_wdata,
    input  wire            w16_we,
    input  wire [23:0]     w16_addr,
    input  wire [511:0]    w16_data,
    input  wire            w1_we,
    input  wire [23:0]     w1_addr,
    input  wire [31:0]     w1_data,
    input  wire            tw_we,
    input  wire [1:0]      tw_kind,
    input  wire [23:0]     tw_addr,
    input  wire [1023:0]   tw_data,
    output wire            f_va, f_vb, f_vc, f_cr, f_bt
);
    wire [6:0]   tw_a_bt;
    wire [7:0]   tw_a_pg;
    wire [456:0] tw_d0, tw_d1;
    wire [255:0] qa, qb, qc, qbs;
    wire [511:0] qcr;
    wire [456:0] qpg;
    wire         fa, fb, fc, fcr, fbt;
    assign tw_a_bt = tw_addr[8:2];
    assign tw_a_pg = tw_addr[7:0];
    assign tw_d0   = tw_data[456:0];
    assign tw_d1   = tw_data[968:512];
    qfd_dv_s8x_vmr u_va (.ck(ck), .rst_n(rst_n), .re(a_re), .addr(a_addr), .q(qa),
        .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .w16_we(w16_we), .w16_addr(w16_addr), .w16_data(w16_data),
        .w1_we(w1_we), .w1_addr(w1_addr), .w1_data(w1_data), .fault(fa));
    qfd_dv_s8x_vmr u_vb (.ck(ck), .rst_n(rst_n), .re(b_re), .addr(b_addr), .q(qb),
        .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .w16_we(w16_we), .w16_addr(w16_addr), .w16_data(w16_data),
        .w1_we(w1_we), .w1_addr(w1_addr), .w1_data(w1_data), .fault(fb));
    qfd_dv_s8x_vmr u_vc (.ck(ck), .rst_n(rst_n), .re(c_re), .addr(c_addr), .q(qc),
        .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .w16_we(w16_we), .w16_addr(w16_addr), .w16_data(w16_data),
        .w1_we(w1_we), .w1_addr(w1_addr), .w1_data(w1_data), .fault(fc));
    qfd_dv_s8x_crom u_cr (.ck(ck), .rst_n(rst_n), .cr_re(cr_re), .cr_addr(cr_addr), .cr_q(qcr),
        .tw_we(tw_we), .tw_kind(tw_kind), .tw_addr(tw_addr), .tw_data(tw_data), .fault(fcr));
    qfd_dv_s8x_btab u_bt (.ck(ck), .rst_n(rst_n), .bs_re(bs_re), .bs_addr(bs_addr), .bs_q(qbs),
        .tw_we(tw_we), .tw_kind(tw_kind), .tw_addr(tw_a_bt), .tw_data(tw_data), .fault(fbt));
    qfd_dv_s8x_prog u_pg (.ck(ck), .p_re(p_re), .p_idx(p_idx), .p_q(qpg),
        .tw_we(tw_we), .tw_kind(tw_kind), .tw_addr(tw_a_pg), .tw_d0(tw_d0), .tw_d1(tw_d1));
    // answers landed into r_io (the consumer's region)
    qfd_dv_s5_vm8out #(.W(256)) u_oa (.ck(ck), .d(qa), .q(a_q));
    qfd_dv_s5_vm8out #(.W(256)) u_ob (.ck(ck), .d(qb), .q(b_q));
    qfd_dv_s5_vm8out #(.W(256)) u_oc (.ck(ck), .d(qc), .q(c_q));
    qfd_dv_s5_vm8out #(.W(512)) u_ocr (.ck(ck), .d(qcr), .q(cr_q));
    qfd_dv_s5_vm8out #(.W(256)) u_obs (.ck(ck), .d(qbs), .q(bs_q));
    qfd_dv_s5_vm8out #(.W(457)) u_opg (.ck(ck), .d(qpg), .q(p_q));
    qfd_dv_s5_vm8out #(.W(1)) u_ofa (.ck(ck), .d(fa), .q(f_va));
    qfd_dv_s5_vm8out #(.W(1)) u_ofb (.ck(ck), .d(fb), .q(f_vb));
    qfd_dv_s5_vm8out #(.W(1)) u_ofc (.ck(ck), .d(fc), .q(f_vc));
    qfd_dv_s5_vm8out #(.W(1)) u_ofcr (.ck(ck), .d(fcr), .q(f_cr));
    qfd_dv_s5_vm8out #(.W(1)) u_ofbt (.ck(ck), .d(fbt), .q(f_bt));
endmodule
