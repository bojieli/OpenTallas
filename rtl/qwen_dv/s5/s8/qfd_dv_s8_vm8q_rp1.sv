`timescale 1ns/1ps
// =====================================================================================================================
// QW-SLICE2W 10-21 (Q.STA.SLICE.2) VM8 leaf group, option P3 = structural successor of P2 (qfd_dv_s5_vm8p).
// Why (gates qfd_dv_slice2_vm8p / vm8pb --cts, FAIL 10-21): (1) tier-1 VM inputs went pin -> hard-child pin register
// directly, so the pin-flops were child-internal flops at the children's own insertion (TT/FF pin-flop spread 202/246
// and 384/455 ps) and the broadcast VM write buses ran up to 819 um single-cycle to the far replica; (2) ONE table-write
// relay trunk per tier fed leaves up to ~950 um apart (966 / 1050 stages beyond reach); (3) rst_n fanned to 4 sinks
// unlanded; (4) GRT-0183 boxed-in net while repair_timing fixed those long pin wires.
// P3 (same one clock region, no rings, static relays, no flow control, datapath unreset):
//   * every input of every leaf lands first on a PARENT relay flop (spine-balanced) -- VM tier now d_in = 1;
//   * every broadcast bus (VM writes -> 3 replicas, table writes -> btab / prog / crh lo / crh hi, CROM reads -> lo/hi)
//     is relayed by its OWN per-leaf copy (fixed-width non-parameterised modules, kept through synthesis:
//     route.synth_keep_modules), so no relay flop drives two far-apart leaves and each copy sits beside its leaf;
//   * reset lands at the face in 2 stages (kit reset_landing) and is relayed per leaf at that leaf's input depth.
// Equivalence: group == qfd_dv_s5_vm8fh with VM answers / faults 1 edge later (inputs +1, writes and reads alike, so
// VM write->read distance is unchanged), BTAB / PROG +2, CROM +4 (as P2).  Price vs P2: VM reads +1 (SU hot path),
// VM writes +1 (write->read distance unchanged); BTAB / PROG / CROM unchanged; p_q timing (SU8 si) unchanged.
// MUT (bench only; 0 in every kit): 1 = prog input relay bypassed for p_idx, 2 = cl table-write data (top word) one
// relay short.
// =====================================================================================================================
module qfd_dv_s8_vm8q_rp1_rly #(parameter integer W = 1, parameter integer N = 1) (
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

// ---- fixed-width per-leaf relay copies (kept modules: one instance = one physical copy beside its leaf) ----
module qfd_dv_s8_vm8q_rp1_rst (input wire ck, input wire d, output reg q);
    always @(posedge ck) q <= d;
endmodule
module qfd_dv_s8_vm8q_rp1_vrd (input wire ck, input wire [199:0] d, output reg [199:0] q);    // {re 8, addr 192}
    always @(posedge ck) q <= d;
endmodule
module qfd_dv_s8_vm8q_rp1_vwr (input wire ck, input wire [1049:0] d, output reg [1049:0] q);  // VM / w16 / w1 writes
    always @(posedge ck) q <= d;
endmodule
module qfd_dv_s8_vm8q_rp1_twb (input wire ck, input wire [1033:0] d, output reg [1033:0] q);  // btab: we, kind, addr[8:2], data
    always @(posedge ck) q <= d;
endmodule
module qfd_dv_s8_vm8q_rp1_twp (input wire ck, input wire [924:0] d, output reg [924:0] q);    // prog: we, kind, addr[7:0], d0, d1
    always @(posedge ck) q <= d;
endmodule
module qfd_dv_s8_vm8q_rp1_twc (input wire ck, input wire [538:0] d, output reg [538:0] q);    // crh half: we, kind, addr, 512 data
    always @(posedge ck) q <= d;
endmodule

module qfd_dv_s8_vm8q_rp1 #(parameter integer MUT = 0, parameter integer MIF = 0) (
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
    genvar g;
    // ---- tier 1: VM replicas, d_in = 1 (per-replica read relay, per-replica write copy, per-replica reset) ----
    wire [1049:0] vw = {vm_we, vm_waddr, vm_wdata, w16_we, w16_addr, w16_data, w1_we, w1_addr, w1_data};
    wire [1049:0] vwa, vwb, vwc;
    wire [199:0]  rda, rdb, rdc;
    wire          rsa, rsb, rsc;
    qfd_dv_s8_vm8q_rp1_vwr u_vwa (.ck(ck), .d(vw), .q(vwa));
    qfd_dv_s8_vm8q_rp1_vwr u_vwb (.ck(ck), .d(vw), .q(vwb));
    qfd_dv_s8_vm8q_rp1_vwr u_vwc (.ck(ck), .d(vw), .q(vwc));
    qfd_dv_s8_vm8q_rp1_vrd u_rda (.ck(ck), .d({a_re, a_addr}), .q(rda));
    qfd_dv_s8_vm8q_rp1_vrd u_rdb (.ck(ck), .d({b_re, b_addr}), .q(rdb));
    qfd_dv_s8_vm8q_rp1_vrd u_rdc (.ck(ck), .d({c_re, c_addr}), .q(rdc));
    qfd_dv_s8_vm8q_rp1_rst u_rsa (.ck(ck), .d(rst_n), .q(rsa));
    qfd_dv_s8_vm8q_rp1_rst u_rsb (.ck(ck), .d(rst_n), .q(rsb));
    qfd_dv_s8_vm8q_rp1_rst u_rsc (.ck(ck), .d(rst_n), .q(rsc));
    wire [255:0] qa, qb, qc;
    wire         fa, fb, fc;
    qfd_dv_s8x_vmr #(.MIF(MIF)) u_va (.ck(ck), .rst_n(rsa), .re(rda[199:192]), .addr(rda[191:0]), .q(qa),
        .vm_we(vwa[1049:1042]), .vm_waddr(vwa[1041:850]), .vm_wdata(vwa[849:594]), .w16_we(vwa[593]),
        .w16_addr(vwa[592:569]), .w16_data(vwa[568:57]), .w1_we(vwa[56]), .w1_addr(vwa[55:32]), .w1_data(vwa[31:0]),
        .fault(fa));
    qfd_dv_s8x_vmr #(.MIF(MIF)) u_vb (.ck(ck), .rst_n(rsb), .re(rdb[199:192]), .addr(rdb[191:0]), .q(qb),
        .vm_we(vwb[1049:1042]), .vm_waddr(vwb[1041:850]), .vm_wdata(vwb[849:594]), .w16_we(vwb[593]),
        .w16_addr(vwb[592:569]), .w16_data(vwb[568:57]), .w1_we(vwb[56]), .w1_addr(vwb[55:32]), .w1_data(vwb[31:0]),
        .fault(fb));
    qfd_dv_s8x_vmr #(.MIF(MIF)) u_vc (.ck(ck), .rst_n(rsc), .re(rdc[199:192]), .addr(rdc[191:0]), .q(qc),
        .vm_we(vwc[1049:1042]), .vm_waddr(vwc[1041:850]), .vm_wdata(vwc[849:594]), .w16_we(vwc[593]),
        .w16_addr(vwc[592:569]), .w16_data(vwc[568:57]), .w1_we(vwc[56]), .w1_addr(vwc[55:32]), .w1_data(vwc[31:0]),
        .fault(fc));

    // ---- BTAB (d = 1): own read relay, own table-write copy, own reset relay ----
    wire rsbt;
    qfd_dv_s8_vm8q_rp1_rst u_rsbt (.ck(ck), .d(rst_n), .q(rsbt));
    wire        bs_re1;  wire [23:0] bs_addr1;
    qfd_dv_s8_vm8q_rp1_rly #(.W(25)) u_rbs (.ck(ck), .d({bs_re, bs_addr}), .q({bs_re1, bs_addr1}));
    wire [1033:0] twb;
    qfd_dv_s8_vm8q_rp1_twb u_twb (.ck(ck), .d({tw_we, tw_kind, tw_addr[8:2], tw_data}), .q(twb));
    wire [255:0] qbs;  wire fbt;
    qfd_dv_s8x_btab #(.MIF(MIF)) u_bt (.ck(ck), .rst_n(rsbt), .bs_re(bs_re1), .bs_addr(bs_addr1), .bs_q(qbs),
        .tw_we(twb[1033]), .tw_kind(twb[1032:1031]), .tw_addr(twb[1030:1024]), .tw_data(twb[1023:0]), .fault(fbt));

    // ---- PROG (d = 1; no reset pin): own read relay, own table-write copy ----
    wire        p_re1;  wire [8:0] p_idx1, p_idx1r;
    qfd_dv_s8_vm8q_rp1_rly #(.W(10)) u_rpg (.ck(ck), .d({p_re, p_idx}), .q({p_re1, p_idx1r}));
    assign p_idx1 = (MUT == 1) ? p_idx : p_idx1r;
    wire [924:0] twp;
    qfd_dv_s8_vm8q_rp1_twp u_twp (.ck(ck), .d({tw_we, tw_kind, tw_addr[7:0], tw_data[456:0], tw_data[968:512]}), .q(twp));
    wire [456:0] qpg;
    qfd_dv_s8x_prog #(.MIF(MIF)) u_pg (.ck(ck), .p_re(p_re1), .p_idx(p_idx1), .p_q(qpg),
        .tw_we(twp[924]), .tw_kind(twp[923:922]), .tw_addr(twp[921:914]), .tw_d0(twp[913:457]), .tw_d1(twp[456:0]));

    // ---- CROM halves (d = 2): per-half read relays, per-half table-write chains, per-half reset relays ----
    wire [511:0] dlo, dhi;
    generate for (g = 0; g < 16; g = g + 1) begin : g_tw
        assign dlo[32*g +: 32] = tw_data[64*g +: 32];
        assign dhi[32*g +: 32] = tw_data[64*g + 32 +: 32];
    end endgenerate
    wire [538:0] twl1, twl2, twh1, twh2, twl2_m;
    qfd_dv_s8_vm8q_rp1_twc u_twl1 (.ck(ck), .d({tw_we, tw_kind, tw_addr, dlo}), .q(twl1));
    qfd_dv_s8_vm8q_rp1_twc u_twl2 (.ck(ck), .d(twl1), .q(twl2));
    qfd_dv_s8_vm8q_rp1_twc u_twh1 (.ck(ck), .d({tw_we, tw_kind, tw_addr, dhi}), .q(twh1));
    qfd_dv_s8_vm8q_rp1_twc u_twh2 (.ck(ck), .d(twh1), .q(twh2));
    assign twl2_m = (MUT == 2) ? {twl2[538:512], twl1[511:480], twl2[479:0]} : twl2;
    wire [199:0] crl1, crl2, crh1, crh2;
    qfd_dv_s8_vm8q_rp1_vrd u_crl1 (.ck(ck), .d({cr_re, cr_addr}), .q(crl1));
    qfd_dv_s8_vm8q_rp1_vrd u_crl2 (.ck(ck), .d(crl1), .q(crl2));
    qfd_dv_s8_vm8q_rp1_vrd u_crh1 (.ck(ck), .d({cr_re, cr_addr}), .q(crh1));
    qfd_dv_s8_vm8q_rp1_vrd u_crh2 (.ck(ck), .d(crh1), .q(crh2));
    wire rsl1, rsl2, rsh1, rsh2;
    qfd_dv_s8_vm8q_rp1_rst u_rsl1 (.ck(ck), .d(rst_n), .q(rsl1));
    qfd_dv_s8_vm8q_rp1_rst u_rsl2 (.ck(ck), .d(rsl1), .q(rsl2));
    qfd_dv_s8_vm8q_rp1_rst u_rsh1 (.ck(ck), .d(rst_n), .q(rsh1));
    qfd_dv_s8_vm8q_rp1_rst u_rsh2 (.ck(ck), .d(rsh1), .q(rsh2));
    wire [255:0] qlo, qhi;  wire fcl, fch;
    qfd_dv_s8_crh_rp1 #(.MIF(MIF)) u_cl (.ck(ck), .rst_n(rsl2), .cr_re(crl2[199:192]), .cr_addr(crl2[191:0]), .q(qlo),
        .tw_we(twl2_m[538]), .tw_kind(twl2_m[537:536]), .tw_addr(twl2_m[535:512]), .tw_d(twl2_m[511:0]), .fault(fcl));
    qfd_dv_s8_crh_rp1 #(.MIF(MIF)) u_ch (.ck(ck), .rst_n(rsh2), .cr_re(crh2[199:192]), .cr_addr(crh2[191:0]), .q(qhi),
        .tw_we(twh2[538]), .tw_kind(twh2[537:536]), .tw_addr(twh2[535:512]), .tw_d(twh2[511:0]), .fault(fch));

    // ---- answers: d_out relay edges (VM 0, BTAB / PROG 1, CROM 2), then the S-face capture register ----
    wire [255:0] qbs1, qlo2, qhi2;  wire [456:0] qpg1;  wire fbt1, fcl2, fch2;
    qfd_dv_s8_vm8q_rp1_rly #(.W(257), .N(1)) u_rabs (.ck(ck), .d({fbt, qbs}), .q({fbt1, qbs1}));
    qfd_dv_s8_vm8q_rp1_rly #(.W(457), .N(1)) u_rapg (.ck(ck), .d(qpg), .q(qpg1));
    qfd_dv_s8_vm8q_rp1_rly #(.W(257), .N(2)) u_racl (.ck(ck), .d({fcl, qlo}), .q({fcl2, qlo2}));
    qfd_dv_s8_vm8q_rp1_rly #(.W(257), .N(2)) u_rach (.ck(ck), .d({fch, qhi}), .q({fch2, qhi2}));
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
