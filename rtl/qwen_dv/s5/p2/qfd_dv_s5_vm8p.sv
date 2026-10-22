`timescale 1ns/1ps
// =====================================================================================================================
// QW-SLICE2W 10-20 (Q.STA.SLICE.2) VM8 leaf group, option P2 = ONE clock region (no landing rings), relayed by tier.
// Why (gates qfd_dv_slice2_vm8l / vm8lh, P1 = 8 regions + 71 D4 rings, FAIL 10-20): the 37.5k ring flops of the S-face
// region r_io spread over the whole 1.1 x 1.2 mm group (ck_r_io pin-flop spread TT 339 / FF 300 ps), the leaf regions'
// ring halves sat between the leaf and the S band (spread 129-289 ps), port -> ring in->reg -544 ps, and the 1-bit
// reset runs crossed regions single-cycle (cross_clock -71 ps).  P2 removes every in-group region crossing: the seven
// CLOSED leaves (vmr x3, crh lo/hi, btab, prog; vm8x SPLIT 2) share the group's one clock root ck (the SU neighbour's
// region, owner 10-20 09:05: touching same-region tiles connect directly when timing is met) and the long hops are
// static registered relays (no flow control, no reset; datapath).  Leaf L at relay depth d(L): its reset and every input
// reach it d(L) edges later and every output gets d(L) more relay edges before the S-face capture register
// (qfd_dv_s5_vm8out), so the group == qfd_dv_s5_vm8fh with each answer / fault observed 2*d(L) edges later
// (exact lockstep, tb_qfd_dv_s5_vm8p).  Floorplan tiers (S face = SU): tier 1 va/vb/vc d=0 (VM reads = the SU hot path),
// tier 2 btab/prog d=1, cl d=2 (padded to ch), tier 3 ch d=2.  Price vs vm8fh: VM reads +0, BTAB/PROG reads +2,
// CROM reads +4, table writes +1 (BTAB/PROG) / +2 (CROM) with write->read distance unchanged; P1 was +6 on every read.
// MUT (bench only; 0 in every kit): 1 = prog input relay bypassed for p_idx, 2 = cl table-write data one relay short.
// =====================================================================================================================
module qfd_dv_s5_vm8p_rly #(parameter integer W = 1, parameter integer N = 1) (
    input wire ck, input wire [W-1:0] d, output wire [W-1:0] q);
    generate if (N == 0) begin : g_wire
        assign q = d;
    end else begin : g_reg
        reg [W-1:0] r [0:N-1];
        integer i;
        always @(posedge ck) begin
            r[0] <= d;
            for (i = 1; i < N; i = i + 1) r[i] <= r[i-1];
        end
        assign q = r[N-1];
    end endgenerate
endmodule

module qfd_dv_s5_vm8p #(parameter integer MUT = 0) (
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
    output wire            f_va, f_vb, f_vc, f_crl, f_crh, f_bt
);
    // ---- tier 1: VM replicas, d = 0 (direct; the leaves' own pin registers capture) ----
    wire [255:0] qa, qb, qc;
    wire         fa, fb, fc;
    qfd_dv_s8x_vmr u_va (.ck(ck), .rst_n(rst_n), .re(a_re), .addr(a_addr), .q(qa),
        .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .w16_we(w16_we), .w16_addr(w16_addr), .w16_data(w16_data),
        .w1_we(w1_we), .w1_addr(w1_addr), .w1_data(w1_data), .fault(fa));
    qfd_dv_s8x_vmr u_vb (.ck(ck), .rst_n(rst_n), .re(b_re), .addr(b_addr), .q(qb),
        .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .w16_we(w16_we), .w16_addr(w16_addr), .w16_data(w16_data),
        .w1_we(w1_we), .w1_addr(w1_addr), .w1_data(w1_data), .fault(fb));
    qfd_dv_s8x_vmr u_vc (.ck(ck), .rst_n(rst_n), .re(c_re), .addr(c_addr), .q(qc),
        .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .w16_we(w16_we), .w16_addr(w16_addr), .w16_data(w16_data),
        .w1_we(w1_we), .w1_addr(w1_addr), .w1_data(w1_data), .fault(fc));

    // ---- table-write relay trunk: stage 1 feeds tier 2 (btab / prog), stage 2 feeds the CROM halves ----
    wire       tw_we1, tw_we2;  wire [1:0] tw_kind1, tw_kind2;  wire [23:0] tw_addr1, tw_addr2;
    wire [1023:0] tw_data1, tw_data2;
    qfd_dv_s5_vm8p_rly #(.W(1+2+24+1024)) u_rtw1 (.ck(ck), .d({tw_we, tw_kind, tw_addr, tw_data}),
        .q({tw_we1, tw_kind1, tw_addr1, tw_data1}));
    qfd_dv_s5_vm8p_rly #(.W(1+2+24+1024)) u_rtw2 (.ck(ck), .d({tw_we1, tw_kind1, tw_addr1, tw_data1}),
        .q({tw_we2, tw_kind2, tw_addr2, tw_data2}));

    // ---- tier 2: BTAB (d = 1) ----
    wire rst_1, rst_2;
    qfd_dv_s5_vm8p_rly #(.W(1), .N(1)) u_rrs1 (.ck(ck), .d(rst_n), .q(rst_1));
    qfd_dv_s5_vm8p_rly #(.W(1), .N(1)) u_rrs2 (.ck(ck), .d(rst_1), .q(rst_2));
    wire        bs_re1;  wire [23:0] bs_addr1;
    qfd_dv_s5_vm8p_rly #(.W(25)) u_rbs (.ck(ck), .d({bs_re, bs_addr}), .q({bs_re1, bs_addr1}));
    wire [255:0] qbs;  wire fbt;
    qfd_dv_s8x_btab u_bt (.ck(ck), .rst_n(rst_1), .bs_re(bs_re1), .bs_addr(bs_addr1), .bs_q(qbs),
        .tw_we(tw_we1), .tw_kind(tw_kind1), .tw_addr(tw_addr1[8:2]), .tw_data(tw_data1), .fault(fbt));

    // ---- tier 2: PROG (d = 1; no reset pin) ----
    wire        p_re1;  wire [8:0] p_idx1, p_idx1r;
    qfd_dv_s5_vm8p_rly #(.W(10)) u_rpg (.ck(ck), .d({p_re, p_idx}), .q({p_re1, p_idx1r}));
    assign p_idx1 = (MUT == 1) ? p_idx : p_idx1r;
    wire [456:0] qpg;
    qfd_dv_s8x_prog u_pg (.ck(ck), .p_re(p_re1), .p_idx(p_idx1), .p_q(qpg),
        .tw_we(tw_we1), .tw_kind(tw_kind1), .tw_addr(tw_addr1[7:0]), .tw_d0(tw_data1[456:0]), .tw_d1(tw_data1[968:512]));

    // ---- CROM halves: ch tier 3, cl tier 2 padded; both d = 2 so cr_q halves stay aligned ----
    wire [7:0]   cr_re2;  wire [8*24-1:0] cr_addr2;
    qfd_dv_s5_vm8p_rly #(.W(8+192), .N(2)) u_rcr (.ck(ck), .d({cr_re, cr_addr}), .q({cr_re2, cr_addr2}));
    wire [511:0] dlo, dhi, dlo_m;
    genvar g;
    generate for (g = 0; g < 16; g = g + 1) begin : g_tw
        assign dlo[32*g +: 32] = tw_data2[64*g +: 32];
        assign dhi[32*g +: 32] = tw_data2[64*g + 32 +: 32];
    end endgenerate
    assign dlo_m = (MUT == 2) ? {tw_data1[64*15 +: 32], dlo[479:0]} : dlo;
    wire [255:0] qlo, qhi;  wire fcl, fch;
    qfd_dv_s8x_crh u_cl (.ck(ck), .rst_n(rst_2), .cr_re(cr_re2), .cr_addr(cr_addr2), .q(qlo),
        .tw_we(tw_we2), .tw_kind(tw_kind2), .tw_addr(tw_addr2), .tw_d(dlo_m), .fault(fcl));
    qfd_dv_s8x_crh u_ch (.ck(ck), .rst_n(rst_2), .cr_re(cr_re2), .cr_addr(cr_addr2), .q(qhi),
        .tw_we(tw_we2), .tw_kind(tw_kind2), .tw_addr(tw_addr2), .tw_d(dhi), .fault(fch));

    // ---- answers: d(L) relay edges, then the S-face capture register (the SU consumer's input register in slice2) ----
    wire [255:0] qbs1, qlo2, qhi2;  wire [456:0] qpg1;  wire fbt1, fcl2, fch2;
    qfd_dv_s5_vm8p_rly #(.W(257), .N(1)) u_rabs (.ck(ck), .d({fbt, qbs}), .q({fbt1, qbs1}));
    qfd_dv_s5_vm8p_rly #(.W(457), .N(1)) u_rapg (.ck(ck), .d(qpg), .q(qpg1));
    qfd_dv_s5_vm8p_rly #(.W(257), .N(2)) u_racl (.ck(ck), .d({fcl, qlo}), .q({fcl2, qlo2}));
    qfd_dv_s5_vm8p_rly #(.W(257), .N(2)) u_rach (.ck(ck), .d({fch, qhi}), .q({fch2, qhi2}));
    wire [255:0] qcr_lo, qcr_hi;
    qfd_dv_s5_vm8out #(.W(256)) u_oa (.ck(ck), .d(qa), .q(a_q));
    qfd_dv_s5_vm8out #(.W(256)) u_ob (.ck(ck), .d(qb), .q(b_q));
    qfd_dv_s5_vm8out #(.W(256)) u_oc (.ck(ck), .d(qc), .q(c_q));
    qfd_dv_s5_vm8out #(.W(256)) u_ocl (.ck(ck), .d(qlo2), .q(qcr_lo));
    qfd_dv_s5_vm8out #(.W(256)) u_och (.ck(ck), .d(qhi2), .q(qcr_hi));
    generate for (g = 0; g < 8; g = g + 1) begin : g_cr
        assign cr_q[64*g +: 64] = {qcr_hi[32*g +: 32], qcr_lo[32*g +: 32]};
    end endgenerate
    qfd_dv_s5_vm8out #(.W(256)) u_obs (.ck(ck), .d(qbs1), .q(bs_q));
    qfd_dv_s5_vm8out #(.W(457)) u_opg (.ck(ck), .d(qpg1), .q(p_q));
    qfd_dv_s5_vm8out #(.W(1)) u_ofa (.ck(ck), .d(fa), .q(f_va));
    qfd_dv_s5_vm8out #(.W(1)) u_ofb (.ck(ck), .d(fb), .q(f_vb));
    qfd_dv_s5_vm8out #(.W(1)) u_ofc (.ck(ck), .d(fc), .q(f_vc));
    qfd_dv_s5_vm8out #(.W(1)) u_ofcl (.ck(ck), .d(fcl2), .q(f_crl));
    qfd_dv_s5_vm8out #(.W(1)) u_ofch (.ck(ck), .d(fch2), .q(f_crh));
    qfd_dv_s5_vm8out #(.W(1)) u_ofbt (.ck(ck), .d(fbt1), .q(f_bt));
endmodule
