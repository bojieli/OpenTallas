`timescale 1ns/1ps
// Region leaf miter (claude/qwen-tp8-vm-rtl, RTL-B 2026-10-13): ot_qfd_vm_region_leaf (leaf instances and wires only:
// bctl_t, sctl_t, rr4_t, rr2_t, delay1_t / delay2_t and the closed bank_t / su_t / xfifo8_t / su1024_t) against the FLAT REFERENCE
// ot_qfd_vm_region_quarter, same xorshift64 stimulus on every input, xo / ro / so / ovf compared on EVERY clock
// from the first one (reset included).
//   main run      random reads / writes / masks / data on all 8 banks and both SU row banks, random row reads and SU
//                 answers, me stalls 1 in 4 (MEREG = 1: me_in is me one edge early), x beats on a LEGAL push / pop
//                 schedule (the FIFO runs up to NPP - 3 beats deep; the pop pin carries random garbage on non-engine
//                 edges, which both sides must ignore); ovf must stay 0.
//   overflow run  OVFMODE 0: pushes with no pop until ovf; OVFMODE 1: pops on the drained FIFO until ovf.  ovf must
//                 rise, on the same clock in both.
// Non-vacuity refusal: a run with too few pushes / pops / row reads / SU answers / stalls / output changes / nonzero
// compared words, or whose ovf never rose in the overflow run, prints FAIL.
// LEAF_MUT 1..12 (see ot_qfd_vm_region_leaf) must FAIL.
// DEPTH / LAW / DEPTHS / LAWS (2026-10-13 VERIF): the memory depths of the region.  Defaults 8 / 3 / 8 / 3 = the bench
// shape (same stimulus stream as before); 174 / 8 / 695 / 10 = the ROUTED parameters of the leaves (bctl_t LAW 8, sctl_t
// LAWS 10, bank_t DEPTH 174 LAW 8, su_t DEPTHS 695 LAWS 10): every line address is then drawn per bank below the depth.
// The overflow run must see ovf rise, not start with it: at most 158 of its 160 clocks (a FIFO left one beat deep by
// the main run underflows after 4 pops: 156 clocks, seen at the routed depths with SEED 2; the bound was 150).
// ROW_MUT / SU_MUT: the rr2_t (half select) / su1024_t leaf mutants of ot_qfd_vm_region_leaf (must FAIL).
module tb_qfd_vm_rg6;
    parameter integer CYCLES = 6000, SEED = 1, LEAF_MUT = 0, OVFMODE = 0, NPP = 12;
    parameter integer DEPTH = 174, LAW = 8, DEPTHS = 695, LAWS = 10, ROW_MUT = 0, SU_MUT = 0;
    reg clk = 0; always #5 clk = ~clk;
    reg rst_n = 0, me_in = 0;
    reg [7:0] re = 0, we = 0;
    reg [8*LAW-1:0] ra = 0, wl = 0;
    reg [127:0] wm = 0; reg [4095:0] wd = 0;
    reg xv = 0, rq = 0, pop = 0; reg [2:0] rqb = 0;
    reg [5:0] sre = 0; reg [6*LAWS-1:0] sra = 0; reg [2:0] sv = 0;
    reg [1:0] swe = 0; reg [2*LAWS-1:0] swl = 0; reg [31:0] swm = 0; reg [1023:0] swd = 0;
    wire [4095:0] xo, r_xo; wire [511:0] ro, r_ro; wire [3071:0] so, r_so; wire ovf, r_ovf;
    parameter integer MUT=0;
    reg [2807:0] d_w=0;
    reg [1823:0] d_e=0;
    wire [2975:0] q_w;
    wire [1687:0] q_e;
    wire [4063:0] q_s;
    ot_qfd_vm_rg6 #(.MUT(MUT)) candidate (.ck_c0(clk), .ck_c1(clk), .ck_c2(clk), .ck_c3(clk), .ck_c4(clk), .ck_c5(clk), .ck_c6(clk), .ck_c7(clk), .ck_c8(clk), .ck_c9(clk), .ck_c10(clk), .ck_c11(clk), .ck_c12(clk), .ck_c13(clk), .ck_c14(clk), .ck_c15(clk), .ck_c16(clk), .ck_c17(clk), .ck_c18(clk), .ck_c19(clk), .ck_c20(clk), .ck_c21(clk), .ck_c22(clk), .ck_c23(clk), .ck_c24(clk), .ck_c25(clk), .ck_c26(clk), .ck_c27(clk), .ck_c28(clk), .ck_c29(clk), .ck_c30(clk), .ck_c31(clk), .ck_c32(clk), .ck_c33(clk), .ck_c34(clk), .ck_c35(clk), .ck_c36(clk), .ck_c37(clk), .ck_c38(clk), .ck_c39(clk), .ck_c40(clk), .ck_c41(clk), .ck_c42(clk), .ck_c43(clk), .ck_c44(clk), .ck_c45(clk), .ck_c46(clk), .ck_c47(clk), .ck_c48(clk), .ck_c49(clk), .ck_c50(clk), .ck_c51(clk), .ck_c52(clk), .ck_c53(clk), .ck_c54(clk), .ck_c55(clk), .ck_c56(clk), .ck_c57(clk), .ck_c58(clk), .ck_c59(clk), .ck_c60(clk), .ck_c61(clk), .ck_c62(clk), .ck_c63(clk), .ck_c64(clk), .ck_c65(clk), .ck_c66(clk), .ck_c67(clk), .ck_c68(clk), .ck_c69(clk), .ck_c70(clk), .ck_c71(clk), .ck_t0(clk), .ck_t1(clk), .ck_t2(clk), .ck_t3(clk), .ck_t4(clk), .ck_t5(clk), .ck_t6(clk), .ck_t7(clk), .ck_t8(clk), .ck_t9(clk), .ck_t10(clk), .ck_t11(clk), .ck_t12(clk), .ck_t13(clk), .ck_t14(clk), .ck_t15(clk), .ck_t16(clk), .ck_t17(clk), .ck_t18(clk), .ck_t19(clk), .ck_t20(clk), .ck_t21(clk), .ck_t22(clk), .ck_t23(clk), .ck_t24(clk), .ck_t25(clk), .ck_t26(clk), .ck_t27(clk), .ck_t28(clk), .ck_t29(clk), .ck_t30(clk), .ck_t31(clk), .ck_t32(clk), .ck_t33(clk), .ck_t34(clk), .ck_t35(clk), .ck_t36(clk), .ck_t37(clk), .ck_t38(clk), .ck_t39(clk), .ck_t40(clk), .ck_t41(clk), .ck_t42(clk), .ck_t43(clk), .ck_t44(clk), .ck_t45(clk), .ck_t46(clk), .ck_t47(clk), .ck_t48(clk), .ck_t49(clk), .ck_t50(clk), .ck_t51(clk), .ck_t52(clk), .ck_t53(clk), .ck_t54(clk), .ck_t55(clk), .ck_t56(clk), .ck_t57(clk), .ck_t58(clk), .ck_t59(clk), .ck_t60(clk), .ck_t61(clk), .ck_t62(clk), .ck_t63(clk), .ck_t64(clk), .ck_t65(clk), .ck_t66(clk), .ck_t67(clk), .ck_t68(clk), .ck_t69(clk), .ck_t70(clk), .ck_t71(clk), .ck_t72(clk), .ck_t73(clk), .ck_t74(clk), .ck_t75(clk), .ck_t76(clk), .rst_n(rst_n), .me_in(me_in), .re(re), .ra(ra), .we(we), .wl(wl), .wm(wm), .wd(wd), .xv(xv), .rq(rq), .rqb(rqb), .sre(sre), .sra(sra), .sv(sv), .swe(swe), .swl(swl), .swm(swm), .swd(swd), .pop(pop), .ro(ro), .so(so), .ovf(ovf), .lane_me({30{me_in}}), .d_w(d_w), .d_e(d_e), .q_w(q_w), .q_e(q_e), .q_s(q_s));
    assign xo = candidate.xo;
    ot_qfd_vm_region_quarter #(.DEPTH(DEPTH), .LAW(LAW), .DEPTHS(DEPTHS), .LAWS(LAWS), .USE_MACRO(0), .NPP(NPP), .MEREG(1)) reference (
        .clk(clk), .rst_n(rst_n), .me_in(me_in), .re(re), .ra(ra), .we(we), .wl(wl), .wm(wm), .wd(wd),
        .xv(xv), .rq(rq), .rqb(rqb), .sre(sre), .sra(sra), .sv(sv), .swe(swe), .swl(swl), .swm(swm), .swd(swd),
        .pop(pop), .xo(r_xo), .ro(r_ro), .so(r_so), .ovf(r_ovf));
    reg lane_me_prev=0;
    integer lane_checks=0, lane_nonzero=0;
    always @(posedge clk) begin lane_me_prev <= me_in; end
    reg [23:0] ref0=0;
    always @(posedge clk) if (lane_me_prev) ref0 <= {ref0[15:0], d_e[0 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref0[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[0 +: 8] !== ref0[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 0 lane vm_g7_b6_xf1>p0"); end end end
    reg [23:0] ref1=0;
    always @(posedge clk) if (lane_me_prev) ref1 <= {ref1[15:0], d_e[8 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[8 +: 8] !== ref1[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1 lane vm_g7_b1_xf0>p0"); end end end
    reg [23:0] ref2=0;
    always @(posedge clk) if (lane_me_prev) ref2 <= {ref2[15:0], d_e[16 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref2[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[16 +: 8] !== ref2[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 2 lane vm_g7_b0_xf1>p0"); end end end
    reg [23:0] ref3=0;
    always @(posedge clk) if (lane_me_prev) ref3 <= {ref3[15:0], d_e[24 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref3[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[24 +: 8] !== ref3[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 3 lane vm_g7_b0_xf1>p1"); end end end
    reg [23:0] ref4=0;
    always @(posedge clk) if (lane_me_prev) ref4 <= {ref4[15:0], r_xo[3848 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref4[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[32 +: 8] !== ref4[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 4 lane vm_g6_b7_xf1>p1"); end end end
    reg [31:0] ref5=0;
    always @(posedge clk) if (lane_me_prev) ref5 <= {ref5[23:0], r_xo[3856 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref5[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[40 +: 8] !== ref5[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 5 lane vm_g6_b7_xf1>p2"); end end end
    reg [39:0] ref6=0;
    always @(posedge clk) if (lane_me_prev) ref6 <= {ref6[31:0], d_w[0 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref6[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[0 +: 8] !== ref6[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 6 lane vm_g4_b0_xf0>p26"); end end end
    reg [15:0] ref7=0;
    always @(posedge clk) if (lane_me_prev) ref7 <= {ref7[7:0], r_xo[2816 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref7[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[48 +: 8] !== ref7[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 7 lane vm_g6_b5_xf1>p0"); end end end
    reg [15:0] ref8=0;
    always @(posedge clk) if (lane_me_prev) ref8 <= {ref8[7:0], r_xo[2560 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref8[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[56 +: 8] !== ref8[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 8 lane vm_g6_b5_xf0>p0"); end end end
    reg [23:0] ref9=0;
    always @(posedge clk) if (lane_me_prev) ref9 <= {ref9[15:0], d_e[32 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref9[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[64 +: 8] !== ref9[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 9 lane vm_g7_b5_xf0>p0"); end end end
    reg [23:0] ref10=0;
    always @(posedge clk) if (lane_me_prev) ref10 <= {ref10[15:0], r_xo[3584 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref10[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[72 +: 8] !== ref10[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 10 lane vm_g6_b7_xf0>p0"); end end end
    reg [23:0] ref11=0;
    always @(posedge clk) if (lane_me_prev) ref11 <= {ref11[15:0], d_e[40 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref11[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[80 +: 8] !== ref11[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 11 lane vm_g7_b6_xf1>p2"); end end end
    reg [23:0] ref12=0;
    always @(posedge clk) if (lane_me_prev) ref12 <= {ref12[15:0], d_e[48 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref12[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[88 +: 8] !== ref12[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 12 lane vm_g7_b1_xf1>p0"); end end end
    reg [23:0] ref13=0;
    always @(posedge clk) if (lane_me_prev) ref13 <= {ref13[15:0], d_e[56 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref13[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[96 +: 8] !== ref13[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 13 lane vm_g7_b1_xf1>p1"); end end end
    reg [23:0] ref14=0;
    always @(posedge clk) if (lane_me_prev) ref14 <= {ref14[15:0], d_e[64 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref14[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[104 +: 8] !== ref14[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 14 lane vm_g7_b1_xf0>p1"); end end end
    reg [15:0] ref15=0;
    always @(posedge clk) if (lane_me_prev) ref15 <= {ref15[7:0], r_xo[2824 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref15[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[112 +: 8] !== ref15[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 15 lane vm_g6_b5_xf1>p1"); end end end
    reg [7:0] ref16=0;
    always @(posedge clk) if (lane_me_prev) ref16 <= r_xo[512 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref16[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[120 +: 8] !== ref16[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 16 lane vm_g6_b1_xf0>p0"); end end end
    reg [15:0] ref17=0;
    always @(posedge clk) if (lane_me_prev) ref17 <= {ref17[7:0], r_xo[3328 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref17[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[128 +: 8] !== ref17[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 17 lane vm_g6_b6_xf1>p0"); end end end
    reg [23:0] ref18=0;
    always @(posedge clk) if (lane_me_prev) ref18 <= {ref18[15:0], r_xo[776 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref18[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[136 +: 8] !== ref18[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 18 lane vm_g6_b1_xf1>p1"); end end end
    reg [7:0] ref19=0;
    always @(posedge clk) if (lane_me_prev) ref19 <= r_xo[1536 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref19[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[144 +: 8] !== ref19[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 19 lane vm_g6_b3_xf0>p0"); end end end
    reg [23:0] ref20=0;
    always @(posedge clk) if (lane_me_prev) ref20 <= {ref20[15:0], d_e[72 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref20[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[152 +: 8] !== ref20[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 20 lane vm_g7_b7_xf1>p0"); end end end
    reg [23:0] ref21=0;
    always @(posedge clk) if (lane_me_prev) ref21 <= {ref21[15:0], d_e[80 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref21[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[160 +: 8] !== ref21[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 21 lane vm_g7_b7_xf0>p0"); end end end
    reg [23:0] ref22=0;
    always @(posedge clk) if (lane_me_prev) ref22 <= {ref22[15:0], d_e[88 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref22[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[168 +: 8] !== ref22[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 22 lane vm_g7_b7_xf0>p1"); end end end
    reg [23:0] ref23=0;
    always @(posedge clk) if (lane_me_prev) ref23 <= {ref23[15:0], d_e[96 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref23[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[176 +: 8] !== ref23[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 23 lane vm_g7_b6_xf0>p0"); end end end
    reg [23:0] ref24=0;
    always @(posedge clk) if (lane_me_prev) ref24 <= {ref24[15:0], d_e[104 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref24[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[184 +: 8] !== ref24[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 24 lane vm_g7_b5_xf1>p0"); end end end
    reg [23:0] ref25=0;
    always @(posedge clk) if (lane_me_prev) ref25 <= {ref25[15:0], d_e[112 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref25[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[192 +: 8] !== ref25[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 25 lane vm_g7_b3_xf1>p0"); end end end
    reg [23:0] ref26=0;
    always @(posedge clk) if (lane_me_prev) ref26 <= {ref26[15:0], d_e[120 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref26[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[200 +: 8] !== ref26[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 26 lane vm_g7_b3_xf1>p1"); end end end
    reg [23:0] ref27=0;
    always @(posedge clk) if (lane_me_prev) ref27 <= {ref27[15:0], d_e[128 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref27[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[208 +: 8] !== ref27[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 27 lane vm_g7_b3_xf0>p0"); end end end
    reg [23:0] ref28=0;
    always @(posedge clk) if (lane_me_prev) ref28 <= {ref28[15:0], d_e[136 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref28[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[216 +: 8] !== ref28[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 28 lane vm_g7_b2_xf1>p0"); end end end
    reg [23:0] ref29=0;
    always @(posedge clk) if (lane_me_prev) ref29 <= {ref29[15:0], d_e[144 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref29[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[224 +: 8] !== ref29[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 29 lane vm_g7_b3_xf0>p1"); end end end
    reg [23:0] ref30=0;
    always @(posedge clk) if (lane_me_prev) ref30 <= {ref30[15:0], d_e[152 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref30[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[232 +: 8] !== ref30[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 30 lane vm_g7_b3_xf1>p2"); end end end
    reg [23:0] ref31=0;
    always @(posedge clk) if (lane_me_prev) ref31 <= {ref31[15:0], d_e[160 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref31[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[240 +: 8] !== ref31[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 31 lane vm_g7_b2_xf0>p0"); end end end
    reg [23:0] ref32=0;
    always @(posedge clk) if (lane_me_prev) ref32 <= {ref32[15:0], d_e[168 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref32[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[248 +: 8] !== ref32[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 32 lane vm_g7_b2_xf1>p1"); end end end
    reg [23:0] ref33=0;
    always @(posedge clk) if (lane_me_prev) ref33 <= {ref33[15:0], d_e[176 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref33[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[256 +: 8] !== ref33[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 33 lane vm_g7_b3_xf0>p2"); end end end
    reg [23:0] ref34=0;
    always @(posedge clk) if (lane_me_prev) ref34 <= {ref34[15:0], d_e[184 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref34[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[264 +: 8] !== ref34[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 34 lane vm_g7_b2_xf0>p1"); end end end
    reg [23:0] ref35=0;
    always @(posedge clk) if (lane_me_prev) ref35 <= {ref35[15:0], d_e[192 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref35[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[272 +: 8] !== ref35[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 35 lane vm_g7_b2_xf0>p2"); end end end
    reg [15:0] ref36=0;
    always @(posedge clk) if (lane_me_prev) ref36 <= {ref36[7:0], r_xo[1800 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref36[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[280 +: 8] !== ref36[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 36 lane vm_g6_b3_xf1>p1"); end end end
    reg [39:0] ref37=0;
    always @(posedge clk) if (lane_me_prev) ref37 <= {ref37[31:0], r_xo[1808 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref37[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[288 +: 8] !== ref37[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 37 lane vm_g6_b3_xf1>p2"); end end end
    reg [23:0] ref38=0;
    always @(posedge clk) if (lane_me_prev) ref38 <= {ref38[15:0], d_w[8 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref38[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[8 +: 8] !== ref38[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 38 lane vm_g4_b0_xf1>p31"); end end end
    reg [23:0] ref39=0;
    always @(posedge clk) if (lane_me_prev) ref39 <= {ref39[15:0], d_w[16 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref39[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[16 +: 8] !== ref39[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 39 lane vm_g4_b0_xf1>p30"); end end end
    reg [23:0] ref40=0;
    always @(posedge clk) if (lane_me_prev) ref40 <= {ref40[15:0], d_w[24 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref40[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[24 +: 8] !== ref40[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 40 lane vm_g4_b0_xf1>p29"); end end end
    reg [23:0] ref41=0;
    always @(posedge clk) if (lane_me_prev) ref41 <= {ref41[15:0], d_w[32 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref41[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[32 +: 8] !== ref41[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 41 lane vm_g4_b0_xf1>p27"); end end end
    reg [23:0] ref42=0;
    always @(posedge clk) if (lane_me_prev) ref42 <= {ref42[15:0], d_w[40 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref42[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[40 +: 8] !== ref42[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 42 lane vm_g4_b0_xf1>p26"); end end end
    reg [15:0] ref43=0;
    always @(posedge clk) if (lane_me_prev) ref43 <= {ref43[7:0], d_w[48 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref43[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[0 +: 8] !== ref43[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 43 lane vm_g4_b2_xf0>p21"); end end end
    reg [23:0] ref44=0;
    always @(posedge clk) if (lane_me_prev) ref44 <= {ref44[15:0], d_w[56 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref44[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[8 +: 8] !== ref44[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 44 lane vm_g4_b0_xf1>p24"); end end end
    reg [7:0] ref45=0;
    always @(posedge clk) if (lane_me_prev) ref45 <= d_w[64 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref45[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[16 +: 8] !== ref45[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 45 lane vm_g4_b1_xf1>p19"); end end end
    reg [23:0] ref46=0;
    always @(posedge clk) if (lane_me_prev) ref46 <= {ref46[15:0], d_w[72 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref46[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[48 +: 8] !== ref46[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 46 lane vm_g4_b1_xf0>p31"); end end end
    reg [23:0] ref47=0;
    always @(posedge clk) if (lane_me_prev) ref47 <= {ref47[15:0], d_w[80 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref47[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[56 +: 8] !== ref47[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 47 lane vm_g4_b1_xf0>p30"); end end end
    reg [23:0] ref48=0;
    always @(posedge clk) if (lane_me_prev) ref48 <= {ref48[15:0], d_w[88 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref48[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[64 +: 8] !== ref48[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 48 lane vm_g4_b1_xf0>p29"); end end end
    reg [23:0] ref49=0;
    always @(posedge clk) if (lane_me_prev) ref49 <= {ref49[15:0], d_w[96 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref49[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[72 +: 8] !== ref49[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 49 lane vm_g4_b1_xf0>p28"); end end end
    reg [23:0] ref50=0;
    always @(posedge clk) if (lane_me_prev) ref50 <= {ref50[15:0], d_w[104 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref50[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[80 +: 8] !== ref50[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 50 lane vm_g4_b1_xf0>p27"); end end end
    reg [23:0] ref51=0;
    always @(posedge clk) if (lane_me_prev) ref51 <= {ref51[15:0], d_w[112 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref51[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[88 +: 8] !== ref51[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 51 lane vm_g4_b1_xf0>p26"); end end end
    reg [31:0] ref52=0;
    always @(posedge clk) if (lane_me_prev) ref52 <= {ref52[23:0], d_w[120 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref52[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[24 +: 8] !== ref52[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 52 lane vm_g4_b1_xf0>p25"); end end end
    reg [23:0] ref53=0;
    always @(posedge clk) if (lane_me_prev) ref53 <= {ref53[15:0], d_w[128 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref53[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[32 +: 8] !== ref53[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 53 lane vm_g4_b1_xf1>p24"); end end end
    reg [23:0] ref54=0;
    always @(posedge clk) if (lane_me_prev) ref54 <= {ref54[15:0], d_w[136 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref54[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[40 +: 8] !== ref54[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 54 lane vm_g4_b1_xf0>p24"); end end end
    reg [15:0] ref55=0;
    always @(posedge clk) if (lane_me_prev) ref55 <= {ref55[7:0], d_w[144 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref55[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[48 +: 8] !== ref55[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 55 lane vm_g4_b3_xf0>p21"); end end end
    reg [15:0] ref56=0;
    always @(posedge clk) if (lane_me_prev) ref56 <= {ref56[7:0], d_w[152 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref56[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[56 +: 8] !== ref56[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 56 lane vm_g4_b1_xf1>p21"); end end end
    reg [7:0] ref57=0;
    always @(posedge clk) if (lane_me_prev) ref57 <= d_w[160 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref57[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[64 +: 8] !== ref57[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 57 lane vm_g4_b2_xf1>p18"); end end end
    reg [7:0] ref58=0;
    always @(posedge clk) if (lane_me_prev) ref58 <= d_w[168 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref58[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[72 +: 8] !== ref58[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 58 lane vm_g4_b2_xf0>p18"); end end end
    reg [23:0] ref59=0;
    always @(posedge clk) if (lane_me_prev) ref59 <= {ref59[15:0], d_w[176 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref59[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[96 +: 8] !== ref59[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 59 lane vm_g4_b2_xf1>p31"); end end end
    reg [23:0] ref60=0;
    always @(posedge clk) if (lane_me_prev) ref60 <= {ref60[15:0], d_w[184 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref60[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[104 +: 8] !== ref60[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 60 lane vm_g4_b2_xf0>p31"); end end end
    reg [23:0] ref61=0;
    always @(posedge clk) if (lane_me_prev) ref61 <= {ref61[15:0], d_w[192 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref61[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[112 +: 8] !== ref61[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 61 lane vm_g4_b1_xf1>p31"); end end end
    reg [23:0] ref62=0;
    always @(posedge clk) if (lane_me_prev) ref62 <= {ref62[15:0], d_w[200 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref62[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[120 +: 8] !== ref62[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 62 lane vm_g4_b1_xf1>p30"); end end end
    reg [23:0] ref63=0;
    always @(posedge clk) if (lane_me_prev) ref63 <= {ref63[15:0], d_w[208 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref63[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[128 +: 8] !== ref63[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 63 lane vm_g4_b1_xf1>p29"); end end end
    reg [23:0] ref64=0;
    always @(posedge clk) if (lane_me_prev) ref64 <= {ref64[15:0], d_w[216 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref64[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[136 +: 8] !== ref64[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 64 lane vm_g4_b1_xf1>p28"); end end end
    reg [23:0] ref65=0;
    always @(posedge clk) if (lane_me_prev) ref65 <= {ref65[15:0], d_w[224 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref65[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[144 +: 8] !== ref65[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 65 lane vm_g4_b1_xf1>p27"); end end end
    reg [23:0] ref66=0;
    always @(posedge clk) if (lane_me_prev) ref66 <= {ref66[15:0], d_w[232 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref66[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[152 +: 8] !== ref66[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 66 lane vm_g4_b1_xf1>p26"); end end end
    reg [23:0] ref67=0;
    always @(posedge clk) if (lane_me_prev) ref67 <= {ref67[15:0], d_w[240 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref67[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[160 +: 8] !== ref67[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 67 lane vm_g4_b2_xf0>p25"); end end end
    reg [31:0] ref68=0;
    always @(posedge clk) if (lane_me_prev) ref68 <= {ref68[23:0], d_w[248 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref68[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[80 +: 8] !== ref68[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 68 lane vm_g4_b1_xf1>p25"); end end end
    reg [23:0] ref69=0;
    always @(posedge clk) if (lane_me_prev) ref69 <= {ref69[15:0], d_w[256 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref69[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[88 +: 8] !== ref69[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 69 lane vm_g4_b3_xf0>p22"); end end end
    reg [23:0] ref70=0;
    always @(posedge clk) if (lane_me_prev) ref70 <= {ref70[15:0], d_w[264 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref70[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[96 +: 8] !== ref70[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 70 lane vm_g4_b2_xf1>p22"); end end end
    reg [23:0] ref71=0;
    always @(posedge clk) if (lane_me_prev) ref71 <= {ref71[15:0], d_w[272 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref71[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[104 +: 8] !== ref71[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 71 lane vm_g4_b2_xf0>p22"); end end end
    reg [47:0] ref72=0;
    always @(posedge clk) if (lane_me_prev) ref72 <= {ref72[39:0], d_w[280 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref72[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[112 +: 8] !== ref72[40 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 72 lane vm_g4_b1_xf1>p23"); end end end
    reg [15:0] ref73=0;
    always @(posedge clk) if (lane_me_prev) ref73 <= {ref73[7:0], d_w[288 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref73[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[120 +: 8] !== ref73[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 73 lane vm_g4_b3_xf1>p20"); end end end
    reg [23:0] ref74=0;
    always @(posedge clk) if (lane_me_prev) ref74 <= {ref74[15:0], d_w[296 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref74[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[128 +: 8] !== ref74[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 74 lane vm_g4_b1_xf1>p22"); end end end
    reg [15:0] ref75=0;
    always @(posedge clk) if (lane_me_prev) ref75 <= {ref75[7:0], d_w[304 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref75[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[136 +: 8] !== ref75[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 75 lane vm_g4_b3_xf0>p20"); end end end
    reg [15:0] ref76=0;
    always @(posedge clk) if (lane_me_prev) ref76 <= {ref76[7:0], d_w[312 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref76[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[144 +: 8] !== ref76[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 76 lane vm_g4_b2_xf1>p20"); end end end
    reg [15:0] ref77=0;
    always @(posedge clk) if (lane_me_prev) ref77 <= {ref77[7:0], d_w[320 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref77[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[152 +: 8] !== ref77[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 77 lane vm_g4_b2_xf0>p20"); end end end
    reg [15:0] ref78=0;
    always @(posedge clk) if (lane_me_prev) ref78 <= {ref78[7:0], d_w[328 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref78[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[160 +: 8] !== ref78[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 78 lane vm_g4_b2_xf1>p19"); end end end
    reg [15:0] ref79=0;
    always @(posedge clk) if (lane_me_prev) ref79 <= {ref79[7:0], d_w[336 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref79[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[168 +: 8] !== ref79[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 79 lane vm_g4_b1_xf1>p20"); end end end
    reg [31:0] ref80=0;
    always @(posedge clk) if (lane_me_prev) ref80 <= {ref80[23:0], d_w[344 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref80[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[176 +: 8] !== ref80[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 80 lane vm_g4_b3_xf1>p25"); end end end
    reg [23:0] ref81=0;
    always @(posedge clk) if (lane_me_prev) ref81 <= {ref81[15:0], d_w[352 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref81[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[168 +: 8] !== ref81[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 81 lane vm_g4_b3_xf1>p31"); end end end
    reg [23:0] ref82=0;
    always @(posedge clk) if (lane_me_prev) ref82 <= {ref82[15:0], d_w[360 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref82[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[176 +: 8] !== ref82[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 82 lane vm_g4_b3_xf0>p31"); end end end
    reg [23:0] ref83=0;
    always @(posedge clk) if (lane_me_prev) ref83 <= {ref83[15:0], d_w[368 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref83[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[184 +: 8] !== ref83[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 83 lane vm_g4_b2_xf0>p30"); end end end
    reg [23:0] ref84=0;
    always @(posedge clk) if (lane_me_prev) ref84 <= {ref84[15:0], d_w[376 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref84[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[192 +: 8] !== ref84[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 84 lane vm_g4_b2_xf0>p29"); end end end
    reg [23:0] ref85=0;
    always @(posedge clk) if (lane_me_prev) ref85 <= {ref85[15:0], d_w[384 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref85[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[200 +: 8] !== ref85[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 85 lane vm_g4_b2_xf0>p28"); end end end
    reg [23:0] ref86=0;
    always @(posedge clk) if (lane_me_prev) ref86 <= {ref86[15:0], d_w[392 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref86[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[208 +: 8] !== ref86[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 86 lane vm_g4_b2_xf0>p27"); end end end
    reg [23:0] ref87=0;
    always @(posedge clk) if (lane_me_prev) ref87 <= {ref87[15:0], d_w[400 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref87[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[216 +: 8] !== ref87[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 87 lane vm_g4_b2_xf0>p26"); end end end
    reg [23:0] ref88=0;
    always @(posedge clk) if (lane_me_prev) ref88 <= {ref88[15:0], r_xo[3840 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref88[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[296 +: 8] !== ref88[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 88 lane vm_g6_b7_xf1>p0"); end end end
    reg [23:0] ref89=0;
    always @(posedge clk) if (lane_me_prev) ref89 <= {ref89[15:0], d_w[408 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref89[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[184 +: 8] !== ref89[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 89 lane vm_g4_b3_xf1>p22"); end end end
    reg [31:0] ref90=0;
    always @(posedge clk) if (lane_me_prev) ref90 <= {ref90[23:0], d_w[416 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref90[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[192 +: 8] !== ref90[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 90 lane vm_g4_b2_xf0>p24"); end end end
    reg [15:0] ref91=0;
    always @(posedge clk) if (lane_me_prev) ref91 <= {ref91[7:0], r_xo[1792 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref91[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[304 +: 8] !== ref91[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 91 lane vm_g6_b3_xf1>p0"); end end end
    reg [31:0] ref92=0;
    always @(posedge clk) if (lane_me_prev) ref92 <= {ref92[23:0], d_w[424 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref92[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[200 +: 8] !== ref92[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 92 lane vm_g4_b2_xf0>p23"); end end end
    reg [15:0] ref93=0;
    always @(posedge clk) if (lane_me_prev) ref93 <= {ref93[7:0], r_xo[768 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref93[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[312 +: 8] !== ref93[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 93 lane vm_g6_b1_xf1>p0"); end end end
    reg [15:0] ref94=0;
    always @(posedge clk) if (lane_me_prev) ref94 <= {ref94[7:0], d_w[432 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref94[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[208 +: 8] !== ref94[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 94 lane vm_g4_b2_xf0>p19"); end end end
    reg [23:0] ref95=0;
    always @(posedge clk) if (lane_me_prev) ref95 <= {ref95[15:0], d_w[440 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref95[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[224 +: 8] !== ref95[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 95 lane vm_g4_b2_xf1>p30"); end end end
    reg [23:0] ref96=0;
    always @(posedge clk) if (lane_me_prev) ref96 <= {ref96[15:0], d_w[448 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref96[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[232 +: 8] !== ref96[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 96 lane vm_g4_b2_xf1>p29"); end end end
    reg [23:0] ref97=0;
    always @(posedge clk) if (lane_me_prev) ref97 <= {ref97[15:0], d_w[456 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref97[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[240 +: 8] !== ref97[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 97 lane vm_g4_b2_xf1>p28"); end end end
    reg [23:0] ref98=0;
    always @(posedge clk) if (lane_me_prev) ref98 <= {ref98[15:0], d_w[464 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref98[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[248 +: 8] !== ref98[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 98 lane vm_g4_b2_xf1>p27"); end end end
    reg [23:0] ref99=0;
    always @(posedge clk) if (lane_me_prev) ref99 <= {ref99[15:0], d_w[472 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref99[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[256 +: 8] !== ref99[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 99 lane vm_g4_b2_xf1>p26"); end end end
    reg [39:0] ref100=0;
    always @(posedge clk) if (lane_me_prev) ref100 <= {ref100[31:0], d_w[480 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref100[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[216 +: 8] !== ref100[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 100 lane vm_g4_b2_xf1>p25"); end end end
    reg [39:0] ref101=0;
    always @(posedge clk) if (lane_me_prev) ref101 <= {ref101[31:0], d_w[488 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref101[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[224 +: 8] !== ref101[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 101 lane vm_g4_b2_xf1>p24"); end end end
    reg [47:0] ref102=0;
    always @(posedge clk) if (lane_me_prev) ref102 <= {ref102[39:0], d_w[496 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref102[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[232 +: 8] !== ref102[40 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 102 lane vm_g4_b2_xf1>p23"); end end end
    reg [23:0] ref103=0;
    always @(posedge clk) if (lane_me_prev) ref103 <= {ref103[15:0], d_w[504 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref103[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[240 +: 8] !== ref103[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 103 lane vm_g4_b2_xf1>p21"); end end end
    reg [15:0] ref104=0;
    always @(posedge clk) if (lane_me_prev) ref104 <= {ref104[7:0], d_w[512 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref104[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[248 +: 8] !== ref104[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 104 lane vm_g4_b3_xf1>p19"); end end end
    reg [15:0] ref105=0;
    always @(posedge clk) if (lane_me_prev) ref105 <= {ref105[7:0], d_w[520 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref105[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[256 +: 8] !== ref105[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 105 lane vm_g4_b3_xf0>p19"); end end end
    reg [23:0] ref106=0;
    always @(posedge clk) if (lane_me_prev) ref106 <= {ref106[15:0], d_w[528 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref106[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[264 +: 8] !== ref106[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 106 lane vm_g4_b3_xf1>p30"); end end end
    reg [23:0] ref107=0;
    always @(posedge clk) if (lane_me_prev) ref107 <= {ref107[15:0], d_w[536 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref107[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[272 +: 8] !== ref107[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 107 lane vm_g4_b3_xf0>p30"); end end end
    reg [23:0] ref108=0;
    always @(posedge clk) if (lane_me_prev) ref108 <= {ref108[15:0], d_w[544 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref108[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[280 +: 8] !== ref108[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 108 lane vm_g4_b3_xf1>p29"); end end end
    reg [23:0] ref109=0;
    always @(posedge clk) if (lane_me_prev) ref109 <= {ref109[15:0], d_w[552 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref109[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[288 +: 8] !== ref109[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 109 lane vm_g4_b3_xf0>p29"); end end end
    reg [23:0] ref110=0;
    always @(posedge clk) if (lane_me_prev) ref110 <= {ref110[15:0], d_w[560 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref110[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[296 +: 8] !== ref110[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 110 lane vm_g4_b3_xf1>p28"); end end end
    reg [23:0] ref111=0;
    always @(posedge clk) if (lane_me_prev) ref111 <= {ref111[15:0], d_w[568 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref111[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[304 +: 8] !== ref111[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 111 lane vm_g4_b3_xf0>p28"); end end end
    reg [23:0] ref112=0;
    always @(posedge clk) if (lane_me_prev) ref112 <= {ref112[15:0], d_w[576 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref112[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[312 +: 8] !== ref112[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 112 lane vm_g4_b3_xf1>p27"); end end end
    reg [23:0] ref113=0;
    always @(posedge clk) if (lane_me_prev) ref113 <= {ref113[15:0], d_w[584 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref113[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[320 +: 8] !== ref113[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 113 lane vm_g4_b3_xf0>p27"); end end end
    reg [23:0] ref114=0;
    always @(posedge clk) if (lane_me_prev) ref114 <= {ref114[15:0], d_w[592 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref114[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[328 +: 8] !== ref114[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 114 lane vm_g4_b3_xf1>p26"); end end end
    reg [23:0] ref115=0;
    always @(posedge clk) if (lane_me_prev) ref115 <= {ref115[15:0], d_w[600 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref115[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[336 +: 8] !== ref115[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 115 lane vm_g4_b3_xf0>p26"); end end end
    reg [39:0] ref116=0;
    always @(posedge clk) if (lane_me_prev) ref116 <= {ref116[31:0], d_w[608 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref116[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[264 +: 8] !== ref116[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 116 lane vm_g4_b3_xf0>p25"); end end end
    reg [39:0] ref117=0;
    always @(posedge clk) if (lane_me_prev) ref117 <= {ref117[31:0], d_w[616 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref117[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[272 +: 8] !== ref117[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 117 lane vm_g4_b3_xf1>p24"); end end end
    reg [39:0] ref118=0;
    always @(posedge clk) if (lane_me_prev) ref118 <= {ref118[31:0], d_w[624 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref118[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[280 +: 8] !== ref118[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 118 lane vm_g4_b3_xf0>p24"); end end end
    reg [39:0] ref119=0;
    always @(posedge clk) if (lane_me_prev) ref119 <= {ref119[31:0], d_w[632 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref119[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[288 +: 8] !== ref119[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 119 lane vm_g4_b3_xf1>p23"); end end end
    reg [47:0] ref120=0;
    always @(posedge clk) if (lane_me_prev) ref120 <= {ref120[39:0], d_w[640 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref120[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[296 +: 8] !== ref120[40 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 120 lane vm_g4_b3_xf0>p23"); end end end
    reg [23:0] ref121=0;
    always @(posedge clk) if (lane_me_prev) ref121 <= {ref121[15:0], d_w[648 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref121[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[304 +: 8] !== ref121[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 121 lane vm_g4_b3_xf1>p21"); end end end
    reg [15:0] ref122=0;
    always @(posedge clk) if (lane_me_prev) ref122 <= {ref122[7:0], d_w[656 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref122[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[312 +: 8] !== ref122[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 122 lane vm_g4_b3_xf1>p17"); end end end
    reg [15:0] ref123=0;
    always @(posedge clk) if (lane_me_prev) ref123 <= {ref123[7:0], d_w[664 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref123[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[320 +: 8] !== ref123[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 123 lane vm_g4_b3_xf1>p18"); end end end
    reg [15:0] ref124=0;
    always @(posedge clk) if (lane_me_prev) ref124 <= {ref124[7:0], d_w[672 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref124[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[328 +: 8] !== ref124[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 124 lane vm_g4_b3_xf0>p18"); end end end
    reg [23:0] ref125=0;
    always @(posedge clk) if (lane_me_prev) ref125 <= {ref125[15:0], d_e[200 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref125[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[320 +: 8] !== ref125[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 125 lane vm_g7_b7_xf1>p1"); end end end
    reg [23:0] ref126=0;
    always @(posedge clk) if (lane_me_prev) ref126 <= {ref126[15:0], d_e[208 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref126[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[328 +: 8] !== ref126[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 126 lane vm_g7_b6_xf1>p1"); end end end
    reg [23:0] ref127=0;
    always @(posedge clk) if (lane_me_prev) ref127 <= {ref127[15:0], d_e[216 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref127[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[336 +: 8] !== ref127[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 127 lane vm_g7_b6_xf0>p1"); end end end
    reg [23:0] ref128=0;
    always @(posedge clk) if (lane_me_prev) ref128 <= {ref128[15:0], d_e[224 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref128[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[344 +: 8] !== ref128[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 128 lane vm_g7_b5_xf1>p1"); end end end
    reg [47:0] ref129=0;
    always @(posedge clk) if (lane_me_prev) ref129 <= {ref129[39:0], r_xo[3592 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref129[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[352 +: 8] !== ref129[40 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 129 lane vm_g6_b7_xf0>p1"); end end end
    reg [15:0] ref130=0;
    always @(posedge clk) if (lane_me_prev) ref130 <= {ref130[7:0], r_xo[3336 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref130[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[360 +: 8] !== ref130[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 130 lane vm_g6_b6_xf1>p1"); end end end
    reg [15:0] ref131=0;
    always @(posedge clk) if (lane_me_prev) ref131 <= {ref131[7:0], r_xo[1288 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref131[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[368 +: 8] !== ref131[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 131 lane vm_g6_b2_xf1>p1"); end end end
    reg [39:0] ref132=0;
    always @(posedge clk) if (lane_me_prev) ref132 <= {ref132[31:0], r_xo[1544 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref132[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[376 +: 8] !== ref132[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 132 lane vm_g6_b3_xf0>p1"); end end end
    reg [7:0] ref133=0;
    always @(posedge clk) if (lane_me_prev) ref133 <= r_xo[1032 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref133[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[384 +: 8] !== ref133[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 133 lane vm_g6_b2_xf0>p1"); end end end
    reg [23:0] ref134=0;
    always @(posedge clk) if (lane_me_prev) ref134 <= {ref134[15:0], d_e[232 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref134[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[392 +: 8] !== ref134[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 134 lane vm_g7_b7_xf1>p2"); end end end
    reg [31:0] ref135=0;
    always @(posedge clk) if (lane_me_prev) ref135 <= {ref135[23:0], d_e[240 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref135[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[400 +: 8] !== ref135[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 135 lane vm_g7_b7_xf0>p2"); end end end
    reg [23:0] ref136=0;
    always @(posedge clk) if (lane_me_prev) ref136 <= {ref136[15:0], d_e[248 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref136[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[408 +: 8] !== ref136[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 136 lane vm_g7_b6_xf0>p2"); end end end
    reg [23:0] ref137=0;
    always @(posedge clk) if (lane_me_prev) ref137 <= {ref137[15:0], d_e[256 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref137[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[416 +: 8] !== ref137[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 137 lane vm_g7_b5_xf1>p2"); end end end
    reg [23:0] ref138=0;
    always @(posedge clk) if (lane_me_prev) ref138 <= {ref138[15:0], d_e[264 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref138[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[424 +: 8] !== ref138[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 138 lane vm_g7_b5_xf0>p2"); end end end
    reg [23:0] ref139=0;
    always @(posedge clk) if (lane_me_prev) ref139 <= {ref139[15:0], d_e[272 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref139[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[432 +: 8] !== ref139[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 139 lane vm_g7_b3_xf1>p3"); end end end
    reg [23:0] ref140=0;
    always @(posedge clk) if (lane_me_prev) ref140 <= {ref140[15:0], d_e[280 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref140[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[440 +: 8] !== ref140[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 140 lane vm_g7_b2_xf1>p2"); end end end
    reg [23:0] ref141=0;
    always @(posedge clk) if (lane_me_prev) ref141 <= {ref141[15:0], d_e[288 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref141[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[448 +: 8] !== ref141[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 141 lane vm_g7_b5_xf0>p3"); end end end
    reg [23:0] ref142=0;
    always @(posedge clk) if (lane_me_prev) ref142 <= {ref142[15:0], d_e[296 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref142[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[456 +: 8] !== ref142[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 142 lane vm_g7_b1_xf1>p2"); end end end
    reg [23:0] ref143=0;
    always @(posedge clk) if (lane_me_prev) ref143 <= {ref143[15:0], d_e[304 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref143[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[464 +: 8] !== ref143[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 143 lane vm_g7_b1_xf0>p2"); end end end
    reg [47:0] ref144=0;
    always @(posedge clk) if (lane_me_prev) ref144 <= {ref144[39:0], r_xo[3600 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref144[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[472 +: 8] !== ref144[40 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 144 lane vm_g6_b7_xf0>p2"); end end end
    reg [15:0] ref145=0;
    always @(posedge clk) if (lane_me_prev) ref145 <= {ref145[7:0], r_xo[3344 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref145[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[480 +: 8] !== ref145[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 145 lane vm_g6_b6_xf1>p2"); end end end
    reg [15:0] ref146=0;
    always @(posedge clk) if (lane_me_prev) ref146 <= {ref146[7:0], r_xo[3608 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref146[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[488 +: 8] !== ref146[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 146 lane vm_g6_b7_xf0>p3"); end end end
    reg [15:0] ref147=0;
    always @(posedge clk) if (lane_me_prev) ref147 <= {ref147[7:0], r_xo[2832 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref147[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[496 +: 8] !== ref147[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 147 lane vm_g6_b5_xf1>p2"); end end end
    reg [15:0] ref148=0;
    always @(posedge clk) if (lane_me_prev) ref148 <= {ref148[7:0], r_xo[2840 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref148[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[504 +: 8] !== ref148[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 148 lane vm_g6_b5_xf1>p3"); end end end
    reg [7:0] ref149=0;
    always @(posedge clk) if (lane_me_prev) ref149 <= r_xo[1552 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref149[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[512 +: 8] !== ref149[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 149 lane vm_g6_b3_xf0>p2"); end end end
    reg [15:0] ref150=0;
    always @(posedge clk) if (lane_me_prev) ref150 <= {ref150[7:0], r_xo[1296 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref150[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[520 +: 8] !== ref150[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 150 lane vm_g6_b2_xf1>p2"); end end end
    reg [15:0] ref151=0;
    always @(posedge clk) if (lane_me_prev) ref151 <= {ref151[7:0], r_xo[2848 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref151[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[528 +: 8] !== ref151[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 151 lane vm_g6_b5_xf1>p4"); end end end
    reg [15:0] ref152=0;
    always @(posedge clk) if (lane_me_prev) ref152 <= {ref152[7:0], r_xo[784 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref152[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[536 +: 8] !== ref152[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 152 lane vm_g6_b1_xf1>p2"); end end end
    reg [7:0] ref153=0;
    always @(posedge clk) if (lane_me_prev) ref153 <= r_xo[528 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref153[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[544 +: 8] !== ref153[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 153 lane vm_g6_b1_xf0>p2"); end end end
    reg [7:0] ref154=0;
    always @(posedge clk) if (lane_me_prev) ref154 <= r_xo[536 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref154[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[552 +: 8] !== ref154[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 154 lane vm_g6_b1_xf0>p3"); end end end
    reg [23:0] ref155=0;
    always @(posedge clk) if (lane_me_prev) ref155 <= {ref155[15:0], d_e[312 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref155[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[560 +: 8] !== ref155[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 155 lane vm_g7_b1_xf0>p4"); end end end
    reg [23:0] ref156=0;
    always @(posedge clk) if (lane_me_prev) ref156 <= {ref156[15:0], d_w[680 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref156[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[344 +: 8] !== ref156[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 156 lane vm_g4_b4_xf0>p27"); end end end
    reg [23:0] ref157=0;
    always @(posedge clk) if (lane_me_prev) ref157 <= {ref157[15:0], d_w[688 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref157[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[336 +: 8] !== ref157[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 157 lane vm_g4_b5_xf0>p25"); end end end
    reg [15:0] ref158=0;
    always @(posedge clk) if (lane_me_prev) ref158 <= {ref158[7:0], r_xo[2576 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref158[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[568 +: 8] !== ref158[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 158 lane vm_g6_b5_xf0>p2"); end end end
    reg [15:0] ref159=0;
    always @(posedge clk) if (lane_me_prev) ref159 <= {ref159[7:0], r_xo[2584 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref159[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[576 +: 8] !== ref159[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 159 lane vm_g6_b5_xf0>p3"); end end end
    reg [55:0] ref160=0;
    always @(posedge clk) if (lane_me_prev) ref160 <= {ref160[47:0], d_w[696 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref160[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[344 +: 8] !== ref160[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 160 lane vm_g4_b5_xf1>p22"); end end end
    reg [55:0] ref161=0;
    always @(posedge clk) if (lane_me_prev) ref161 <= {ref161[47:0], d_w[704 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref161[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[352 +: 8] !== ref161[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 161 lane vm_g4_b5_xf0>p22"); end end end
    reg [7:0] ref162=0;
    always @(posedge clk) if (lane_me_prev) ref162 <= r_xo[272 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref162[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[584 +: 8] !== ref162[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 162 lane vm_g6_b0_xf1>p2"); end end end
    reg [55:0] ref163=0;
    always @(posedge clk) if (lane_me_prev) ref163 <= {ref163[47:0], d_w[712 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref163[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[360 +: 8] !== ref163[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 163 lane vm_g4_b5_xf1>p19"); end end end
    reg [23:0] ref164=0;
    always @(posedge clk) if (lane_me_prev) ref164 <= {ref164[15:0], d_e[320 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref164[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[592 +: 8] !== ref164[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 164 lane vm_g7_b0_xf1>p2"); end end end
    reg [55:0] ref165=0;
    always @(posedge clk) if (lane_me_prev) ref165 <= {ref165[47:0], r_xo[2320 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref165[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[600 +: 8] !== ref165[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 165 lane vm_g6_b4_xf1>p2"); end end end
    reg [23:0] ref166=0;
    always @(posedge clk) if (lane_me_prev) ref166 <= {ref166[15:0], d_e[328 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref166[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[608 +: 8] !== ref166[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 166 lane vm_g7_b5_xf1>p3"); end end end
    reg [7:0] ref167=0;
    always @(posedge clk) if (lane_me_prev) ref167 <= r_xo[1560 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref167[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[616 +: 8] !== ref167[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 167 lane vm_g6_b3_xf0>p3"); end end end
    reg [39:0] ref168=0;
    always @(posedge clk) if (lane_me_prev) ref168 <= {ref168[31:0], d_e[336 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref168[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[624 +: 8] !== ref168[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 168 lane vm_g7_b2_xf1>p3"); end end end
    reg [23:0] ref169=0;
    always @(posedge clk) if (lane_me_prev) ref169 <= {ref169[15:0], d_w[720 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref169[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[368 +: 8] !== ref169[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 169 lane vm_g4_b4_xf1>p25"); end end end
    reg [55:0] ref170=0;
    always @(posedge clk) if (lane_me_prev) ref170 <= {ref170[47:0], d_w[728 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref170[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[376 +: 8] !== ref170[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 170 lane vm_g4_b6_xf0>p22"); end end end
    reg [55:0] ref171=0;
    always @(posedge clk) if (lane_me_prev) ref171 <= {ref171[47:0], d_w[736 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref171[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[384 +: 8] !== ref171[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 171 lane vm_g4_b4_xf1>p22"); end end end
    reg [7:0] ref172=0;
    always @(posedge clk) if (lane_me_prev) ref172 <= d_w[744 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref172[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[392 +: 8] !== ref172[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 172 lane vm_g4_b4_xf1>p19"); end end end
    reg [23:0] ref173=0;
    always @(posedge clk) if (lane_me_prev) ref173 <= {ref173[15:0], d_e[344 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref173[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[632 +: 8] !== ref173[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 173 lane vm_g7_b7_xf1>p3"); end end end
    reg [23:0] ref174=0;
    always @(posedge clk) if (lane_me_prev) ref174 <= {ref174[15:0], d_e[352 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref174[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[640 +: 8] !== ref174[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 174 lane vm_g7_b7_xf1>p4"); end end end
    reg [23:0] ref175=0;
    always @(posedge clk) if (lane_me_prev) ref175 <= {ref175[15:0], d_e[360 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref175[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[648 +: 8] !== ref175[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 175 lane vm_g7_b7_xf0>p3"); end end end
    reg [23:0] ref176=0;
    always @(posedge clk) if (lane_me_prev) ref176 <= {ref176[15:0], d_e[368 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref176[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[656 +: 8] !== ref176[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 176 lane vm_g7_b6_xf1>p3"); end end end
    reg [23:0] ref177=0;
    always @(posedge clk) if (lane_me_prev) ref177 <= {ref177[15:0], d_e[376 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref177[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[664 +: 8] !== ref177[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 177 lane vm_g7_b6_xf0>p3"); end end end
    reg [23:0] ref178=0;
    always @(posedge clk) if (lane_me_prev) ref178 <= {ref178[15:0], d_w[752 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref178[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[352 +: 8] !== ref178[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 178 lane vm_g4_b4_xf0>p30"); end end end
    reg [23:0] ref179=0;
    always @(posedge clk) if (lane_me_prev) ref179 <= {ref179[15:0], d_w[760 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref179[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[360 +: 8] !== ref179[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 179 lane vm_g4_b4_xf0>p29"); end end end
    reg [39:0] ref180=0;
    always @(posedge clk) if (lane_me_prev) ref180 <= {ref180[31:0], r_xo[3864 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref180[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[672 +: 8] !== ref180[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 180 lane vm_g6_b7_xf1>p3"); end end end
    reg [15:0] ref181=0;
    always @(posedge clk) if (lane_me_prev) ref181 <= {ref181[7:0], r_xo[3080 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref181[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[680 +: 8] !== ref181[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 181 lane vm_g6_b6_xf0>p1"); end end end
    reg [15:0] ref182=0;
    always @(posedge clk) if (lane_me_prev) ref182 <= {ref182[7:0], r_xo[1280 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref182[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[688 +: 8] !== ref182[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 182 lane vm_g6_b2_xf1>p0"); end end end
    reg [15:0] ref183=0;
    always @(posedge clk) if (lane_me_prev) ref183 <= {ref183[7:0], r_xo[3352 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref183[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[696 +: 8] !== ref183[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 183 lane vm_g6_b6_xf1>p3"); end end end
    reg [15:0] ref184=0;
    always @(posedge clk) if (lane_me_prev) ref184 <= {ref184[7:0], r_xo[3096 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref184[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[704 +: 8] !== ref184[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 184 lane vm_g6_b6_xf0>p3"); end end end
    reg [7:0] ref185=0;
    always @(posedge clk) if (lane_me_prev) ref185 <= r_xo[1024 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref185[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[712 +: 8] !== ref185[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 185 lane vm_g6_b2_xf0>p0"); end end end
    reg [15:0] ref186=0;
    always @(posedge clk) if (lane_me_prev) ref186 <= {ref186[7:0], r_xo[1816 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref186[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[720 +: 8] !== ref186[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 186 lane vm_g6_b3_xf1>p3"); end end end
    reg [15:0] ref187=0;
    always @(posedge clk) if (lane_me_prev) ref187 <= {ref187[7:0], r_xo[3104 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref187[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[728 +: 8] !== ref187[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 187 lane vm_g6_b6_xf0>p4"); end end end
    reg [15:0] ref188=0;
    always @(posedge clk) if (lane_me_prev) ref188 <= {ref188[7:0], r_xo[1824 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref188[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[736 +: 8] !== ref188[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 188 lane vm_g6_b3_xf1>p4"); end end end
    reg [55:0] ref189=0;
    always @(posedge clk) if (lane_me_prev) ref189 <= {ref189[47:0], r_xo[1304 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref189[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[744 +: 8] !== ref189[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 189 lane vm_g6_b2_xf1>p3"); end end end
    reg [7:0] ref190=0;
    always @(posedge clk) if (lane_me_prev) ref190 <= r_xo[1048 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref190[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[752 +: 8] !== ref190[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 190 lane vm_g6_b2_xf0>p3"); end end end
    reg [23:0] ref191=0;
    always @(posedge clk) if (lane_me_prev) ref191 <= {ref191[15:0], r_xo[792 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref191[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[760 +: 8] !== ref191[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 191 lane vm_g6_b1_xf1>p3"); end end end
    reg [7:0] ref192=0;
    always @(posedge clk) if (lane_me_prev) ref192 <= r_xo[1056 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref192[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[768 +: 8] !== ref192[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 192 lane vm_g6_b2_xf0>p4"); end end end
    reg [23:0] ref193=0;
    always @(posedge clk) if (lane_me_prev) ref193 <= {ref193[15:0], d_e[384 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref193[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[776 +: 8] !== ref193[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 193 lane vm_g7_b7_xf0>p4"); end end end
    reg [23:0] ref194=0;
    always @(posedge clk) if (lane_me_prev) ref194 <= {ref194[15:0], d_e[392 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref194[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[784 +: 8] !== ref194[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 194 lane vm_g7_b6_xf1>p4"); end end end
    reg [23:0] ref195=0;
    always @(posedge clk) if (lane_me_prev) ref195 <= {ref195[15:0], d_e[400 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref195[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[792 +: 8] !== ref195[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 195 lane vm_g7_b6_xf0>p4"); end end end
    reg [31:0] ref196=0;
    always @(posedge clk) if (lane_me_prev) ref196 <= {ref196[23:0], d_e[408 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref196[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[800 +: 8] !== ref196[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 196 lane vm_g7_b3_xf1>p4"); end end end
    reg [23:0] ref197=0;
    always @(posedge clk) if (lane_me_prev) ref197 <= {ref197[15:0], d_e[416 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref197[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[808 +: 8] !== ref197[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 197 lane vm_g7_b3_xf0>p3"); end end end
    reg [31:0] ref198=0;
    always @(posedge clk) if (lane_me_prev) ref198 <= {ref198[23:0], d_e[424 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref198[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[816 +: 8] !== ref198[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 198 lane vm_g7_b2_xf0>p3"); end end end
    reg [23:0] ref199=0;
    always @(posedge clk) if (lane_me_prev) ref199 <= {ref199[15:0], d_e[432 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref199[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[824 +: 8] !== ref199[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 199 lane vm_g7_b1_xf1>p3"); end end end
    reg [31:0] ref200=0;
    always @(posedge clk) if (lane_me_prev) ref200 <= {ref200[23:0], d_e[440 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref200[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[832 +: 8] !== ref200[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 200 lane vm_g7_b2_xf0>p4"); end end end
    reg [23:0] ref201=0;
    always @(posedge clk) if (lane_me_prev) ref201 <= {ref201[15:0], d_w[768 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref201[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[368 +: 8] !== ref201[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 201 lane vm_g4_b4_xf1>p31"); end end end
    reg [23:0] ref202=0;
    always @(posedge clk) if (lane_me_prev) ref202 <= {ref202[15:0], d_w[776 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref202[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[376 +: 8] !== ref202[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 202 lane vm_g4_b4_xf1>p30"); end end end
    reg [23:0] ref203=0;
    always @(posedge clk) if (lane_me_prev) ref203 <= {ref203[15:0], d_w[784 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref203[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[384 +: 8] !== ref203[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 203 lane vm_g4_b4_xf1>p29"); end end end
    reg [23:0] ref204=0;
    always @(posedge clk) if (lane_me_prev) ref204 <= {ref204[15:0], d_w[792 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref204[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[392 +: 8] !== ref204[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 204 lane vm_g4_b4_xf1>p27"); end end end
    reg [23:0] ref205=0;
    always @(posedge clk) if (lane_me_prev) ref205 <= {ref205[15:0], d_w[800 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref205[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[400 +: 8] !== ref205[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 205 lane vm_g4_b4_xf1>p24"); end end end
    reg [15:0] ref206=0;
    always @(posedge clk) if (lane_me_prev) ref206 <= {ref206[7:0], d_w[808 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref206[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[408 +: 8] !== ref206[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 206 lane vm_g4_b4_xf1>p21"); end end end
    reg [23:0] ref207=0;
    always @(posedge clk) if (lane_me_prev) ref207 <= {ref207[15:0], d_w[816 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref207[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[400 +: 8] !== ref207[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 207 lane vm_g4_b4_xf1>p26"); end end end
    reg [7:0] ref208=0;
    always @(posedge clk) if (lane_me_prev) ref208 <= d_w[824 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref208[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[416 +: 8] !== ref208[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 208 lane vm_g4_b4_xf1>p18"); end end end
    reg [23:0] ref209=0;
    always @(posedge clk) if (lane_me_prev) ref209 <= {ref209[15:0], d_w[832 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref209[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[408 +: 8] !== ref209[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 209 lane vm_g4_b5_xf0>p31"); end end end
    reg [23:0] ref210=0;
    always @(posedge clk) if (lane_me_prev) ref210 <= {ref210[15:0], d_w[840 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref210[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[416 +: 8] !== ref210[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 210 lane vm_g4_b5_xf0>p30"); end end end
    reg [23:0] ref211=0;
    always @(posedge clk) if (lane_me_prev) ref211 <= {ref211[15:0], d_w[848 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref211[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[424 +: 8] !== ref211[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 211 lane vm_g4_b5_xf0>p29"); end end end
    reg [23:0] ref212=0;
    always @(posedge clk) if (lane_me_prev) ref212 <= {ref212[15:0], d_w[856 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref212[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[432 +: 8] !== ref212[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 212 lane vm_g4_b5_xf0>p28"); end end end
    reg [23:0] ref213=0;
    always @(posedge clk) if (lane_me_prev) ref213 <= {ref213[15:0], d_w[864 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref213[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[440 +: 8] !== ref213[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 213 lane vm_g4_b5_xf0>p27"); end end end
    reg [23:0] ref214=0;
    always @(posedge clk) if (lane_me_prev) ref214 <= {ref214[15:0], d_w[872 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref214[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[424 +: 8] !== ref214[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 214 lane vm_g4_b7_xf0>p24"); end end end
    reg [23:0] ref215=0;
    always @(posedge clk) if (lane_me_prev) ref215 <= {ref215[15:0], d_w[880 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref215[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[432 +: 8] !== ref215[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 215 lane vm_g4_b6_xf1>p24"); end end end
    reg [23:0] ref216=0;
    always @(posedge clk) if (lane_me_prev) ref216 <= {ref216[15:0], d_w[888 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref216[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[448 +: 8] !== ref216[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 216 lane vm_g4_b5_xf0>p26"); end end end
    reg [23:0] ref217=0;
    always @(posedge clk) if (lane_me_prev) ref217 <= {ref217[15:0], d_w[896 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref217[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[440 +: 8] !== ref217[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 217 lane vm_g4_b6_xf0>p24"); end end end
    reg [23:0] ref218=0;
    always @(posedge clk) if (lane_me_prev) ref218 <= {ref218[15:0], d_w[904 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref218[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[448 +: 8] !== ref218[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 218 lane vm_g4_b5_xf1>p24"); end end end
    reg [15:0] ref219=0;
    always @(posedge clk) if (lane_me_prev) ref219 <= {ref219[7:0], d_w[912 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref219[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[456 +: 8] !== ref219[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 219 lane vm_g4_b7_xf1>p21"); end end end
    reg [23:0] ref220=0;
    always @(posedge clk) if (lane_me_prev) ref220 <= {ref220[15:0], d_w[920 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref220[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[464 +: 8] !== ref220[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 220 lane vm_g4_b5_xf0>p24"); end end end
    reg [15:0] ref221=0;
    always @(posedge clk) if (lane_me_prev) ref221 <= {ref221[7:0], d_w[928 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref221[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[472 +: 8] !== ref221[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 221 lane vm_g4_b7_xf0>p21"); end end end
    reg [15:0] ref222=0;
    always @(posedge clk) if (lane_me_prev) ref222 <= {ref222[7:0], d_w[936 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref222[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[480 +: 8] !== ref222[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 222 lane vm_g4_b6_xf1>p21"); end end end
    reg [15:0] ref223=0;
    always @(posedge clk) if (lane_me_prev) ref223 <= {ref223[7:0], d_w[944 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref223[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[488 +: 8] !== ref223[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 223 lane vm_g4_b6_xf0>p21"); end end end
    reg [7:0] ref224=0;
    always @(posedge clk) if (lane_me_prev) ref224 <= d_w[952 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref224[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[496 +: 8] !== ref224[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 224 lane vm_g4_b7_xf0>p18"); end end end
    reg [7:0] ref225=0;
    always @(posedge clk) if (lane_me_prev) ref225 <= d_w[960 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref225[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[504 +: 8] !== ref225[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 225 lane vm_g4_b6_xf1>p18"); end end end
    reg [7:0] ref226=0;
    always @(posedge clk) if (lane_me_prev) ref226 <= d_w[968 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref226[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[512 +: 8] !== ref226[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 226 lane vm_g4_b6_xf0>p18"); end end end
    reg [23:0] ref227=0;
    always @(posedge clk) if (lane_me_prev) ref227 <= {ref227[15:0], d_w[976 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref227[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[456 +: 8] !== ref227[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 227 lane vm_g4_b5_xf1>p31"); end end end
    reg [23:0] ref228=0;
    always @(posedge clk) if (lane_me_prev) ref228 <= {ref228[15:0], d_w[984 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref228[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[464 +: 8] !== ref228[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 228 lane vm_g4_b5_xf1>p30"); end end end
    reg [23:0] ref229=0;
    always @(posedge clk) if (lane_me_prev) ref229 <= {ref229[15:0], d_w[992 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref229[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[472 +: 8] !== ref229[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 229 lane vm_g4_b5_xf1>p29"); end end end
    reg [23:0] ref230=0;
    always @(posedge clk) if (lane_me_prev) ref230 <= {ref230[15:0], d_w[1000 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref230[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[480 +: 8] !== ref230[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 230 lane vm_g4_b5_xf1>p28"); end end end
    reg [39:0] ref231=0;
    always @(posedge clk) if (lane_me_prev) ref231 <= {ref231[31:0], d_w[1008 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref231[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[488 +: 8] !== ref231[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 231 lane vm_g4_b5_xf1>p27"); end end end
    reg [39:0] ref232=0;
    always @(posedge clk) if (lane_me_prev) ref232 <= {ref232[31:0], d_w[1016 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref232[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[496 +: 8] !== ref232[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 232 lane vm_g4_b6_xf0>p26"); end end end
    reg [23:0] ref233=0;
    always @(posedge clk) if (lane_me_prev) ref233 <= {ref233[15:0], d_w[1024 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref233[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[504 +: 8] !== ref233[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 233 lane vm_g4_b5_xf1>p26"); end end end
    reg [31:0] ref234=0;
    always @(posedge clk) if (lane_me_prev) ref234 <= {ref234[23:0], d_w[1032 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref234[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[520 +: 8] !== ref234[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 234 lane vm_g4_b6_xf0>p25"); end end end
    reg [23:0] ref235=0;
    always @(posedge clk) if (lane_me_prev) ref235 <= {ref235[15:0], d_w[1040 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref235[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[528 +: 8] !== ref235[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 235 lane vm_g4_b7_xf0>p22"); end end end
    reg [23:0] ref236=0;
    always @(posedge clk) if (lane_me_prev) ref236 <= {ref236[15:0], d_w[1048 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref236[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[536 +: 8] !== ref236[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 236 lane vm_g4_b6_xf1>p22"); end end end
    reg [39:0] ref237=0;
    always @(posedge clk) if (lane_me_prev) ref237 <= {ref237[31:0], d_w[1056 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref237[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[544 +: 8] !== ref237[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 237 lane vm_g4_b5_xf1>p25"); end end end
    reg [39:0] ref238=0;
    always @(posedge clk) if (lane_me_prev) ref238 <= {ref238[31:0], d_w[1064 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref238[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[552 +: 8] !== ref238[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 238 lane vm_g4_b7_xf0>p20"); end end end
    reg [23:0] ref239=0;
    always @(posedge clk) if (lane_me_prev) ref239 <= {ref239[15:0], d_w[1072 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref239[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[560 +: 8] !== ref239[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 239 lane vm_g4_b6_xf1>p20"); end end end
    reg [23:0] ref240=0;
    always @(posedge clk) if (lane_me_prev) ref240 <= {ref240[15:0], d_w[1080 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref240[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[568 +: 8] !== ref240[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 240 lane vm_g4_b6_xf0>p20"); end end end
    reg [15:0] ref241=0;
    always @(posedge clk) if (lane_me_prev) ref241 <= {ref241[7:0], d_w[1088 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref241[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[576 +: 8] !== ref241[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 241 lane vm_g4_b6_xf1>p19"); end end end
    reg [15:0] ref242=0;
    always @(posedge clk) if (lane_me_prev) ref242 <= {ref242[7:0], d_w[1096 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref242[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[584 +: 8] !== ref242[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 242 lane vm_g4_b6_xf0>p19"); end end end
    reg [23:0] ref243=0;
    always @(posedge clk) if (lane_me_prev) ref243 <= {ref243[15:0], d_w[1104 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref243[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[592 +: 8] !== ref243[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 243 lane vm_g4_b5_xf1>p20"); end end end
    reg [23:0] ref244=0;
    always @(posedge clk) if (lane_me_prev) ref244 <= {ref244[15:0], d_w[1112 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref244[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[600 +: 8] !== ref244[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 244 lane vm_g4_b6_xf1>p23"); end end end
    reg [23:0] ref245=0;
    always @(posedge clk) if (lane_me_prev) ref245 <= {ref245[15:0], d_w[1120 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref245[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[608 +: 8] !== ref245[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 245 lane vm_g4_b6_xf0>p23"); end end end
    reg [15:0] ref246=0;
    always @(posedge clk) if (lane_me_prev) ref246 <= {ref246[7:0], d_w[1128 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref246[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[616 +: 8] !== ref246[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 246 lane vm_g4_b5_xf1>p23"); end end end
    reg [39:0] ref247=0;
    always @(posedge clk) if (lane_me_prev) ref247 <= {ref247[31:0], d_w[1136 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref247[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[624 +: 8] !== ref247[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 247 lane vm_g4_b7_xf1>p25"); end end end
    reg [23:0] ref248=0;
    always @(posedge clk) if (lane_me_prev) ref248 <= {ref248[15:0], d_w[1144 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref248[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[512 +: 8] !== ref248[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 248 lane vm_g4_b6_xf0>p31"); end end end
    reg [23:0] ref249=0;
    always @(posedge clk) if (lane_me_prev) ref249 <= {ref249[15:0], d_w[1152 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref249[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[520 +: 8] !== ref249[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 249 lane vm_g4_b6_xf0>p30"); end end end
    reg [23:0] ref250=0;
    always @(posedge clk) if (lane_me_prev) ref250 <= {ref250[15:0], d_w[1160 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref250[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[528 +: 8] !== ref250[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 250 lane vm_g4_b6_xf0>p29"); end end end
    reg [31:0] ref251=0;
    always @(posedge clk) if (lane_me_prev) ref251 <= {ref251[23:0], d_w[1168 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref251[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[536 +: 8] !== ref251[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 251 lane vm_g4_b6_xf0>p28"); end end end
    reg [39:0] ref252=0;
    always @(posedge clk) if (lane_me_prev) ref252 <= {ref252[31:0], d_w[1176 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref252[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[544 +: 8] !== ref252[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 252 lane vm_g4_b6_xf0>p27"); end end end
    reg [15:0] ref253=0;
    always @(posedge clk) if (lane_me_prev) ref253 <= {ref253[7:0], d_w[1184 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref253[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[632 +: 8] !== ref253[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 253 lane vm_g4_b7_xf0>p19"); end end end
    reg [23:0] ref254=0;
    always @(posedge clk) if (lane_me_prev) ref254 <= {ref254[15:0], d_w[1192 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref254[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[552 +: 8] !== ref254[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 254 lane vm_g4_b6_xf1>p31"); end end end
    reg [23:0] ref255=0;
    always @(posedge clk) if (lane_me_prev) ref255 <= {ref255[15:0], d_w[1200 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref255[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[560 +: 8] !== ref255[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 255 lane vm_g4_b6_xf1>p30"); end end end
    reg [23:0] ref256=0;
    always @(posedge clk) if (lane_me_prev) ref256 <= {ref256[15:0], d_w[1208 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref256[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[568 +: 8] !== ref256[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 256 lane vm_g4_b6_xf1>p29"); end end end
    reg [23:0] ref257=0;
    always @(posedge clk) if (lane_me_prev) ref257 <= {ref257[15:0], d_w[1216 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref257[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[576 +: 8] !== ref257[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 257 lane vm_g4_b6_xf1>p28"); end end end
    reg [23:0] ref258=0;
    always @(posedge clk) if (lane_me_prev) ref258 <= {ref258[15:0], d_w[1224 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref258[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[584 +: 8] !== ref258[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 258 lane vm_g4_b6_xf1>p27"); end end end
    reg [39:0] ref259=0;
    always @(posedge clk) if (lane_me_prev) ref259 <= {ref259[31:0], d_w[1232 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref259[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[592 +: 8] !== ref259[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 259 lane vm_g4_b6_xf1>p26"); end end end
    reg [39:0] ref260=0;
    always @(posedge clk) if (lane_me_prev) ref260 <= {ref260[31:0], d_w[1240 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref260[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[640 +: 8] !== ref260[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 260 lane vm_g4_b6_xf1>p25"); end end end
    reg [23:0] ref261=0;
    always @(posedge clk) if (lane_me_prev) ref261 <= {ref261[15:0], d_w[1248 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref261[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[648 +: 8] !== ref261[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 261 lane vm_g4_b7_xf1>p22"); end end end
    reg [47:0] ref262=0;
    always @(posedge clk) if (lane_me_prev) ref262 <= {ref262[39:0], d_w[1256 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref262[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[656 +: 8] !== ref262[40 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 262 lane vm_g4_b7_xf1>p17"); end end end
    reg [47:0] ref263=0;
    always @(posedge clk) if (lane_me_prev) ref263 <= {ref263[39:0], d_w[1264 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref263[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[664 +: 8] !== ref263[40 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 263 lane vm_g4_b7_xf1>p23"); end end end
    reg [15:0] ref264=0;
    always @(posedge clk) if (lane_me_prev) ref264 <= {ref264[7:0], d_w[1272 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref264[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[672 +: 8] !== ref264[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 264 lane vm_g4_b7_xf1>p19"); end end end
    reg [23:0] ref265=0;
    always @(posedge clk) if (lane_me_prev) ref265 <= {ref265[15:0], d_w[1280 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref265[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[600 +: 8] !== ref265[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 265 lane vm_g4_b7_xf1>p31"); end end end
    reg [23:0] ref266=0;
    always @(posedge clk) if (lane_me_prev) ref266 <= {ref266[15:0], d_w[1288 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref266[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[608 +: 8] !== ref266[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 266 lane vm_g4_b7_xf0>p31"); end end end
    reg [23:0] ref267=0;
    always @(posedge clk) if (lane_me_prev) ref267 <= {ref267[15:0], d_w[1296 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref267[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[616 +: 8] !== ref267[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 267 lane vm_g4_b7_xf1>p30"); end end end
    reg [23:0] ref268=0;
    always @(posedge clk) if (lane_me_prev) ref268 <= {ref268[15:0], d_w[1304 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref268[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[624 +: 8] !== ref268[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 268 lane vm_g4_b7_xf0>p30"); end end end
    reg [23:0] ref269=0;
    always @(posedge clk) if (lane_me_prev) ref269 <= {ref269[15:0], d_w[1312 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref269[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[632 +: 8] !== ref269[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 269 lane vm_g4_b7_xf1>p29"); end end end
    reg [23:0] ref270=0;
    always @(posedge clk) if (lane_me_prev) ref270 <= {ref270[15:0], d_w[1320 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref270[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[640 +: 8] !== ref270[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 270 lane vm_g4_b7_xf0>p29"); end end end
    reg [23:0] ref271=0;
    always @(posedge clk) if (lane_me_prev) ref271 <= {ref271[15:0], d_w[1328 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref271[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[648 +: 8] !== ref271[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 271 lane vm_g4_b7_xf1>p28"); end end end
    reg [23:0] ref272=0;
    always @(posedge clk) if (lane_me_prev) ref272 <= {ref272[15:0], d_w[1336 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref272[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[656 +: 8] !== ref272[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 272 lane vm_g4_b7_xf0>p28"); end end end
    reg [23:0] ref273=0;
    always @(posedge clk) if (lane_me_prev) ref273 <= {ref273[15:0], d_w[1344 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref273[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[664 +: 8] !== ref273[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 273 lane vm_g4_b7_xf1>p27"); end end end
    reg [23:0] ref274=0;
    always @(posedge clk) if (lane_me_prev) ref274 <= {ref274[15:0], d_w[1352 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref274[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[672 +: 8] !== ref274[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 274 lane vm_g4_b7_xf0>p27"); end end end
    reg [39:0] ref275=0;
    always @(posedge clk) if (lane_me_prev) ref275 <= {ref275[31:0], d_w[1360 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref275[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[680 +: 8] !== ref275[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 275 lane vm_g4_b7_xf1>p26"); end end end
    reg [39:0] ref276=0;
    always @(posedge clk) if (lane_me_prev) ref276 <= {ref276[31:0], d_w[1368 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref276[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[688 +: 8] !== ref276[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 276 lane vm_g4_b7_xf0>p26"); end end end
    reg [39:0] ref277=0;
    always @(posedge clk) if (lane_me_prev) ref277 <= {ref277[31:0], d_w[1376 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref277[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[680 +: 8] !== ref277[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 277 lane vm_g4_b7_xf0>p25"); end end end
    reg [39:0] ref278=0;
    always @(posedge clk) if (lane_me_prev) ref278 <= {ref278[31:0], d_w[1384 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref278[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[688 +: 8] !== ref278[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 278 lane vm_g4_b7_xf1>p24"); end end end
    reg [23:0] ref279=0;
    always @(posedge clk) if (lane_me_prev) ref279 <= {ref279[15:0], d_w[1392 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref279[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[696 +: 8] !== ref279[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 279 lane vm_g4_b7_xf1>p20"); end end end
    reg [47:0] ref280=0;
    always @(posedge clk) if (lane_me_prev) ref280 <= {ref280[39:0], d_w[1400 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref280[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[704 +: 8] !== ref280[40 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 280 lane vm_g4_b7_xf1>p18"); end end end
    reg [47:0] ref281=0;
    always @(posedge clk) if (lane_me_prev) ref281 <= {ref281[39:0], d_w[1408 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref281[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[712 +: 8] !== ref281[40 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 281 lane vm_g4_b7_xf0>p23"); end end end
    reg [55:0] ref282=0;
    always @(posedge clk) if (lane_me_prev) ref282 <= {ref282[47:0], d_e[448 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref282[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[840 +: 8] !== ref282[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 282 lane vm_g7_b2_xf0>p6"); end end end
    reg [23:0] ref283=0;
    always @(posedge clk) if (lane_me_prev) ref283 <= {ref283[15:0], d_e[456 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref283[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[848 +: 8] !== ref283[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 283 lane vm_g7_b2_xf1>p7"); end end end
    reg [63:0] ref284=0;
    always @(posedge clk) if (lane_me_prev) ref284 <= {ref284[55:0], r_xo[3376 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref284[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[856 +: 8] !== ref284[56 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 284 lane vm_g6_b6_xf1>p6"); end end end
    reg [63:0] ref285=0;
    always @(posedge clk) if (lane_me_prev) ref285 <= {ref285[55:0], r_xo[3384 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref285[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[864 +: 8] !== ref285[56 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 285 lane vm_g6_b6_xf1>p7"); end end end
    reg [55:0] ref286=0;
    always @(posedge clk) if (lane_me_prev) ref286 <= {ref286[47:0], r_xo[280 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref286[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[872 +: 8] !== ref286[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 286 lane vm_g6_b0_xf1>p3"); end end end
    reg [55:0] ref287=0;
    always @(posedge clk) if (lane_me_prev) ref287 <= {ref287[47:0], r_xo[288 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref287[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[880 +: 8] !== ref287[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 287 lane vm_g6_b0_xf1>p4"); end end end
    reg [63:0] ref288=0;
    always @(posedge clk) if (lane_me_prev) ref288 <= {ref288[55:0], r_xo[32 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref288[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[888 +: 8] !== ref288[56 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 288 lane vm_g6_b0_xf0>p4"); end end end
    reg [63:0] ref289=0;
    always @(posedge clk) if (lane_me_prev) ref289 <= {ref289[55:0], r_xo[40 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref289[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[896 +: 8] !== ref289[56 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 289 lane vm_g6_b0_xf0>p5"); end end end
    reg [15:0] ref290=0;
    always @(posedge clk) if (lane_me_prev) ref290 <= {ref290[7:0], r_xo[2568 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref290[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[904 +: 8] !== ref290[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 290 lane vm_g6_b5_xf0>p1"); end end end
    reg [23:0] ref291=0;
    always @(posedge clk) if (lane_me_prev) ref291 <= {ref291[15:0], d_e[464 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref291[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[912 +: 8] !== ref291[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 291 lane vm_g7_b1_xf1>p7"); end end end
    reg [23:0] ref292=0;
    always @(posedge clk) if (lane_me_prev) ref292 <= {ref292[15:0], d_e[472 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref292[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[920 +: 8] !== ref292[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 292 lane vm_g7_b1_xf0>p7"); end end end
    reg [23:0] ref293=0;
    always @(posedge clk) if (lane_me_prev) ref293 <= {ref293[15:0], d_w[1416 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref293[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[720 +: 8] !== ref293[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 293 lane vm_g5_b1_xf0>p28"); end end end
    reg [63:0] ref294=0;
    always @(posedge clk) if (lane_me_prev) ref294 <= {ref294[55:0], r_xo[2592 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref294[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[928 +: 8] !== ref294[56 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 294 lane vm_g6_b5_xf0>p4"); end end end
    reg [7:0] ref295=0;
    always @(posedge clk) if (lane_me_prev) ref295 <= r_xo[520 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref295[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[936 +: 8] !== ref295[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 295 lane vm_g6_b1_xf0>p1"); end end end
    reg [23:0] ref296=0;
    always @(posedge clk) if (lane_me_prev) ref296 <= {ref296[15:0], d_w[1424 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref296[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[728 +: 8] !== ref296[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 296 lane vm_g5_b1_xf0>p25"); end end end
    reg [63:0] ref297=0;
    always @(posedge clk) if (lane_me_prev) ref297 <= {ref297[55:0], r_xo[3656 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref297[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[944 +: 8] !== ref297[56 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 297 lane vm_g6_b7_xf0>p9"); end end end
    reg [63:0] ref298=0;
    always @(posedge clk) if (lane_me_prev) ref298 <= {ref298[55:0], r_xo[1608 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref298[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[952 +: 8] !== ref298[56 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 298 lane vm_g6_b3_xf0>p9"); end end end
    reg [15:0] ref299=0;
    always @(posedge clk) if (lane_me_prev) ref299 <= {ref299[7:0], r_xo[2872 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref299[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[960 +: 8] !== ref299[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 299 lane vm_g6_b5_xf1>p7"); end end end
    reg [15:0] ref300=0;
    always @(posedge clk) if (lane_me_prev) ref300 <= {ref300[7:0], r_xo[2880 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref300[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[968 +: 8] !== ref300[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 300 lane vm_g6_b5_xf1>p8"); end end end
    reg [15:0] ref301=0;
    always @(posedge clk) if (lane_me_prev) ref301 <= {ref301[7:0], d_w[1432 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref301[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[736 +: 8] !== ref301[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 301 lane vm_g5_b2_xf0>p22"); end end end
    reg [15:0] ref302=0;
    always @(posedge clk) if (lane_me_prev) ref302 <= {ref302[7:0], r_xo[2888 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref302[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[976 +: 8] !== ref302[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 302 lane vm_g6_b5_xf1>p9"); end end end
    reg [7:0] ref303=0;
    always @(posedge clk) if (lane_me_prev) ref303 <= r_xo[1600 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref303[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[984 +: 8] !== ref303[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 303 lane vm_g6_b3_xf0>p8"); end end end
    reg [15:0] ref304=0;
    always @(posedge clk) if (lane_me_prev) ref304 <= {ref304[7:0], d_w[1440 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref304[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[744 +: 8] !== ref304[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 304 lane vm_g5_b1_xf1>p22"); end end end
    reg [7:0] ref305=0;
    always @(posedge clk) if (lane_me_prev) ref305 <= r_xo[576 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref305[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[992 +: 8] !== ref305[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 305 lane vm_g6_b1_xf0>p8"); end end end
    reg [47:0] ref306=0;
    always @(posedge clk) if (lane_me_prev) ref306 <= {ref306[39:0], d_e[480 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref306[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1000 +: 8] !== ref306[40 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 306 lane vm_g7_b7_xf0>p8"); end end end
    reg [23:0] ref307=0;
    always @(posedge clk) if (lane_me_prev) ref307 <= {ref307[15:0], d_e[488 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref307[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1008 +: 8] !== ref307[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 307 lane vm_g7_b1_xf0>p5"); end end end
    reg [23:0] ref308=0;
    always @(posedge clk) if (lane_me_prev) ref308 <= {ref308[15:0], d_e[496 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref308[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1016 +: 8] !== ref308[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 308 lane vm_g7_b5_xf0>p8"); end end end
    reg [55:0] ref309=0;
    always @(posedge clk) if (lane_me_prev) ref309 <= {ref309[47:0], d_e[504 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref309[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1024 +: 8] !== ref309[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 309 lane vm_g7_b3_xf0>p8"); end end end
    reg [23:0] ref310=0;
    always @(posedge clk) if (lane_me_prev) ref310 <= {ref310[15:0], d_e[512 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref310[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1032 +: 8] !== ref310[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 310 lane vm_g7_b0_xf1>p5"); end end end
    reg [31:0] ref311=0;
    always @(posedge clk) if (lane_me_prev) ref311 <= {ref311[23:0], d_w[1448 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref311[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[752 +: 8] !== ref311[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 311 lane vm_g5_b2_xf0>p28"); end end end
    reg [23:0] ref312=0;
    always @(posedge clk) if (lane_me_prev) ref312 <= {ref312[15:0], d_e[520 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref312[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1040 +: 8] !== ref312[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 312 lane vm_g7_b1_xf0>p8"); end end end
    reg [31:0] ref313=0;
    always @(posedge clk) if (lane_me_prev) ref313 <= {ref313[23:0], d_w[1456 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref313[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[760 +: 8] !== ref313[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 313 lane vm_g5_b0_xf1>p28"); end end end
    reg [23:0] ref314=0;
    always @(posedge clk) if (lane_me_prev) ref314 <= {ref314[15:0], d_e[528 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref314[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1048 +: 8] !== ref314[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 314 lane vm_g7_b0_xf1>p8"); end end end
    reg [31:0] ref315=0;
    always @(posedge clk) if (lane_me_prev) ref315 <= {ref315[23:0], d_w[1464 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref315[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[768 +: 8] !== ref315[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 315 lane vm_g5_b0_xf0>p28"); end end end
    reg [15:0] ref316=0;
    always @(posedge clk) if (lane_me_prev) ref316 <= {ref316[7:0], r_xo[2856 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref316[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1056 +: 8] !== ref316[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 316 lane vm_g6_b5_xf1>p5"); end end end
    reg [15:0] ref317=0;
    always @(posedge clk) if (lane_me_prev) ref317 <= {ref317[7:0], r_xo[2600 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref317[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1064 +: 8] !== ref317[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 317 lane vm_g6_b5_xf0>p5"); end end end
    reg [15:0] ref318=0;
    always @(posedge clk) if (lane_me_prev) ref318 <= {ref318[7:0], r_xo[2864 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref318[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1072 +: 8] !== ref318[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 318 lane vm_g6_b5_xf1>p6"); end end end
    reg [15:0] ref319=0;
    always @(posedge clk) if (lane_me_prev) ref319 <= {ref319[7:0], r_xo[2608 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref319[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1080 +: 8] !== ref319[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 319 lane vm_g6_b5_xf0>p6"); end end end
    reg [23:0] ref320=0;
    always @(posedge clk) if (lane_me_prev) ref320 <= {ref320[15:0], d_w[1472 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref320[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[776 +: 8] !== ref320[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 320 lane vm_g5_b0_xf1>p25"); end end end
    reg [23:0] ref321=0;
    always @(posedge clk) if (lane_me_prev) ref321 <= {ref321[15:0], d_w[1480 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref321[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[784 +: 8] !== ref321[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 321 lane vm_g5_b0_xf0>p25"); end end end
    reg [15:0] ref322=0;
    always @(posedge clk) if (lane_me_prev) ref322 <= {ref322[7:0], r_xo[2624 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref322[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1088 +: 8] !== ref322[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 322 lane vm_g6_b5_xf0>p8"); end end end
    reg [7:0] ref323=0;
    always @(posedge clk) if (lane_me_prev) ref323 <= r_xo[552 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref323[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1096 +: 8] !== ref323[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 323 lane vm_g6_b1_xf0>p5"); end end end
    reg [63:0] ref324=0;
    always @(posedge clk) if (lane_me_prev) ref324 <= {ref324[55:0], r_xo[296 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref324[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1104 +: 8] !== ref324[56 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 324 lane vm_g6_b0_xf1>p5"); end end end
    reg [7:0] ref325=0;
    always @(posedge clk) if (lane_me_prev) ref325 <= r_xo[560 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref325[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1112 +: 8] !== ref325[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 325 lane vm_g6_b1_xf0>p6"); end end end
    reg [71:0] ref326=0;
    always @(posedge clk) if (lane_me_prev) ref326 <= {ref326[63:0], d_w[1488 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref326[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[792 +: 8] !== ref326[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 326 lane vm_g5_b1_xf0>p22"); end end end
    reg [71:0] ref327=0;
    always @(posedge clk) if (lane_me_prev) ref327 <= {ref327[63:0], d_w[1496 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref327[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[800 +: 8] !== ref327[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 327 lane vm_g5_b0_xf1>p22"); end end end
    reg [71:0] ref328=0;
    always @(posedge clk) if (lane_me_prev) ref328 <= {ref328[63:0], d_w[1504 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref328[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[808 +: 8] !== ref328[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 328 lane vm_g5_b0_xf0>p22"); end end end
    reg [7:0] ref329=0;
    always @(posedge clk) if (lane_me_prev) ref329 <= d_w[1512 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref329[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[816 +: 8] !== ref329[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 329 lane vm_g5_b2_xf0>p19"); end end end
    reg [71:0] ref330=0;
    always @(posedge clk) if (lane_me_prev) ref330 <= {ref330[63:0], d_w[1520 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref330[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[824 +: 8] !== ref330[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 330 lane vm_g5_b1_xf1>p19"); end end end
    reg [71:0] ref331=0;
    always @(posedge clk) if (lane_me_prev) ref331 <= {ref331[63:0], r_xo[320 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref331[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1120 +: 8] !== ref331[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 331 lane vm_g6_b0_xf1>p8"); end end end
    reg [7:0] ref332=0;
    always @(posedge clk) if (lane_me_prev) ref332 <= d_w[1528 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref332[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[832 +: 8] !== ref332[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 332 lane vm_g5_b1_xf0>p19"); end end end
    reg [71:0] ref333=0;
    always @(posedge clk) if (lane_me_prev) ref333 <= {ref333[63:0], d_w[1536 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref333[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[840 +: 8] !== ref333[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 333 lane vm_g5_b0_xf1>p19"); end end end
    reg [71:0] ref334=0;
    always @(posedge clk) if (lane_me_prev) ref334 <= {ref334[63:0], d_w[1544 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref334[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[848 +: 8] !== ref334[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 334 lane vm_g5_b0_xf0>p19"); end end end
    reg [23:0] ref335=0;
    always @(posedge clk) if (lane_me_prev) ref335 <= {ref335[15:0], d_e[536 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref335[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1128 +: 8] !== ref335[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 335 lane vm_g7_b5_xf0>p5"); end end end
    reg [23:0] ref336=0;
    always @(posedge clk) if (lane_me_prev) ref336 <= {ref336[15:0], d_w[1552 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref336[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[856 +: 8] !== ref336[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 336 lane vm_g5_b0_xf1>p31"); end end end
    reg [55:0] ref337=0;
    always @(posedge clk) if (lane_me_prev) ref337 <= {ref337[47:0], d_w[1560 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref337[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[864 +: 8] !== ref337[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 337 lane vm_g5_b0_xf0>p31"); end end end
    reg [55:0] ref338=0;
    always @(posedge clk) if (lane_me_prev) ref338 <= {ref338[47:0], d_w[1568 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref338[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[872 +: 8] !== ref338[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 338 lane vm_g5_b1_xf1>p28"); end end end
    reg [63:0] ref339=0;
    always @(posedge clk) if (lane_me_prev) ref339 <= {ref339[55:0], r_xo[2344 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref339[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1136 +: 8] !== ref339[56 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 339 lane vm_g6_b4_xf1>p5"); end end end
    reg [71:0] ref340=0;
    always @(posedge clk) if (lane_me_prev) ref340 <= {ref340[63:0], r_xo[2368 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref340[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1144 +: 8] !== ref340[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 340 lane vm_g6_b4_xf1>p8"); end end end
    reg [23:0] ref341=0;
    always @(posedge clk) if (lane_me_prev) ref341 <= {ref341[15:0], d_e[544 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref341[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1152 +: 8] !== ref341[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 341 lane vm_g7_b6_xf0>p6"); end end end
    reg [31:0] ref342=0;
    always @(posedge clk) if (lane_me_prev) ref342 <= {ref342[23:0], d_e[552 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref342[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1160 +: 8] !== ref342[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 342 lane vm_g7_b6_xf1>p7"); end end end
    reg [31:0] ref343=0;
    always @(posedge clk) if (lane_me_prev) ref343 <= {ref343[23:0], d_e[560 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref343[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1168 +: 8] !== ref343[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 343 lane vm_g7_b5_xf1>p6"); end end end
    reg [23:0] ref344=0;
    always @(posedge clk) if (lane_me_prev) ref344 <= {ref344[15:0], d_e[568 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref344[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1176 +: 8] !== ref344[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 344 lane vm_g7_b6_xf0>p7"); end end end
    reg [23:0] ref345=0;
    always @(posedge clk) if (lane_me_prev) ref345 <= {ref345[15:0], d_e[576 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref345[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1184 +: 8] !== ref345[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 345 lane vm_g7_b1_xf1>p6"); end end end
    reg [23:0] ref346=0;
    always @(posedge clk) if (lane_me_prev) ref346 <= {ref346[15:0], d_e[584 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref346[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1192 +: 8] !== ref346[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 346 lane vm_g7_b2_xf0>p7"); end end end
    reg [23:0] ref347=0;
    always @(posedge clk) if (lane_me_prev) ref347 <= {ref347[15:0], d_e[592 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref347[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1200 +: 8] !== ref347[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 347 lane vm_g7_b6_xf0>p10"); end end end
    reg [31:0] ref348=0;
    always @(posedge clk) if (lane_me_prev) ref348 <= {ref348[23:0], d_e[600 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref348[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1208 +: 8] !== ref348[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 348 lane vm_g7_b2_xf0>p10"); end end end
    reg [55:0] ref349=0;
    always @(posedge clk) if (lane_me_prev) ref349 <= {ref349[47:0], r_xo[3904 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref349[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1216 +: 8] !== ref349[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 349 lane vm_g6_b7_xf1>p8"); end end end
    reg [15:0] ref350=0;
    always @(posedge clk) if (lane_me_prev) ref350 <= {ref350[7:0], r_xo[3128 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref350[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1224 +: 8] !== ref350[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 350 lane vm_g6_b6_xf0>p7"); end end end
    reg [15:0] ref351=0;
    always @(posedge clk) if (lane_me_prev) ref351 <= {ref351[7:0], r_xo[3392 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref351[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1232 +: 8] !== ref351[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 351 lane vm_g6_b6_xf1>p8"); end end end
    reg [63:0] ref352=0;
    always @(posedge clk) if (lane_me_prev) ref352 <= {ref352[55:0], r_xo[1856 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref352[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1240 +: 8] !== ref352[56 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 352 lane vm_g6_b3_xf1>p8"); end end end
    reg [23:0] ref353=0;
    always @(posedge clk) if (lane_me_prev) ref353 <= {ref353[15:0], r_xo[3136 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref353[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1248 +: 8] !== ref353[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 353 lane vm_g6_b6_xf0>p8"); end end end
    reg [15:0] ref354=0;
    always @(posedge clk) if (lane_me_prev) ref354 <= {ref354[7:0], d_w[1576 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref354[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[880 +: 8] !== ref354[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 354 lane vm_g5_b2_xf1>p22"); end end end
    reg [23:0] ref355=0;
    always @(posedge clk) if (lane_me_prev) ref355 <= {ref355[15:0], r_xo[3144 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref355[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1256 +: 8] !== ref355[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 355 lane vm_g6_b6_xf0>p9"); end end end
    reg [23:0] ref356=0;
    always @(posedge clk) if (lane_me_prev) ref356 <= {ref356[15:0], r_xo[3152 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref356[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1264 +: 8] !== ref356[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 356 lane vm_g6_b6_xf0>p10"); end end end
    reg [15:0] ref357=0;
    always @(posedge clk) if (lane_me_prev) ref357 <= {ref357[7:0], r_xo[1080 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref357[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1272 +: 8] !== ref357[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 357 lane vm_g6_b2_xf0>p7"); end end end
    reg [23:0] ref358=0;
    always @(posedge clk) if (lane_me_prev) ref358 <= {ref358[15:0], r_xo[1344 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref358[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1280 +: 8] !== ref358[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 358 lane vm_g6_b2_xf1>p8"); end end end
    reg [15:0] ref359=0;
    always @(posedge clk) if (lane_me_prev) ref359 <= {ref359[7:0], r_xo[2896 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref359[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1288 +: 8] !== ref359[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 359 lane vm_g6_b5_xf1>p10"); end end end
    reg [23:0] ref360=0;
    always @(posedge clk) if (lane_me_prev) ref360 <= {ref360[15:0], r_xo[1352 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref360[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1296 +: 8] !== ref360[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 360 lane vm_g6_b2_xf1>p9"); end end end
    reg [23:0] ref361=0;
    always @(posedge clk) if (lane_me_prev) ref361 <= {ref361[15:0], r_xo[832 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref361[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1304 +: 8] !== ref361[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 361 lane vm_g6_b1_xf1>p8"); end end end
    reg [23:0] ref362=0;
    always @(posedge clk) if (lane_me_prev) ref362 <= {ref362[15:0], r_xo[1360 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref362[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1312 +: 8] !== ref362[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 362 lane vm_g6_b2_xf1>p10"); end end end
    reg [7:0] ref363=0;
    always @(posedge clk) if (lane_me_prev) ref363 <= r_xo[1088 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref363[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1320 +: 8] !== ref363[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 363 lane vm_g6_b2_xf0>p8"); end end end
    reg [7:0] ref364=0;
    always @(posedge clk) if (lane_me_prev) ref364 <= r_xo[1096 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref364[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1328 +: 8] !== ref364[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 364 lane vm_g6_b2_xf0>p9"); end end end
    reg [7:0] ref365=0;
    always @(posedge clk) if (lane_me_prev) ref365 <= r_xo[1104 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref365[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1336 +: 8] !== ref365[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 365 lane vm_g6_b2_xf0>p10"); end end end
    reg [23:0] ref366=0;
    always @(posedge clk) if (lane_me_prev) ref366 <= {ref366[15:0], d_e[608 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref366[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1344 +: 8] !== ref366[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 366 lane vm_g7_b7_xf1>p8"); end end end
    reg [23:0] ref367=0;
    always @(posedge clk) if (lane_me_prev) ref367 <= {ref367[15:0], d_e[616 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref367[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1352 +: 8] !== ref367[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 367 lane vm_g7_b7_xf1>p9"); end end end
    reg [39:0] ref368=0;
    always @(posedge clk) if (lane_me_prev) ref368 <= {ref368[31:0], d_e[624 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref368[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1360 +: 8] !== ref368[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 368 lane vm_g7_b7_xf1>p10"); end end end
    reg [23:0] ref369=0;
    always @(posedge clk) if (lane_me_prev) ref369 <= {ref369[15:0], d_e[632 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref369[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1368 +: 8] !== ref369[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 369 lane vm_g7_b6_xf1>p8"); end end end
    reg [31:0] ref370=0;
    always @(posedge clk) if (lane_me_prev) ref370 <= {ref370[23:0], d_e[640 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref370[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1376 +: 8] !== ref370[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 370 lane vm_g7_b5_xf1>p7"); end end end
    reg [55:0] ref371=0;
    always @(posedge clk) if (lane_me_prev) ref371 <= {ref371[47:0], d_e[648 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref371[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1384 +: 8] !== ref371[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 371 lane vm_g7_b2_xf0>p5"); end end end
    reg [55:0] ref372=0;
    always @(posedge clk) if (lane_me_prev) ref372 <= {ref372[47:0], d_e[656 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref372[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1392 +: 8] !== ref372[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 372 lane vm_g7_b6_xf0>p8"); end end end
    reg [23:0] ref373=0;
    always @(posedge clk) if (lane_me_prev) ref373 <= {ref373[15:0], d_e[664 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref373[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1400 +: 8] !== ref373[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 373 lane vm_g7_b6_xf1>p9"); end end end
    reg [23:0] ref374=0;
    always @(posedge clk) if (lane_me_prev) ref374 <= {ref374[15:0], d_e[672 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref374[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1408 +: 8] !== ref374[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 374 lane vm_g7_b1_xf1>p5"); end end end
    reg [55:0] ref375=0;
    always @(posedge clk) if (lane_me_prev) ref375 <= {ref375[47:0], d_e[680 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref375[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1416 +: 8] !== ref375[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 375 lane vm_g7_b5_xf1>p8"); end end end
    reg [23:0] ref376=0;
    always @(posedge clk) if (lane_me_prev) ref376 <= {ref376[15:0], d_e[688 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref376[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1424 +: 8] !== ref376[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 376 lane vm_g7_b3_xf1>p8"); end end end
    reg [23:0] ref377=0;
    always @(posedge clk) if (lane_me_prev) ref377 <= {ref377[15:0], d_e[696 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref377[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1432 +: 8] !== ref377[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 377 lane vm_g7_b5_xf1>p9"); end end end
    reg [23:0] ref378=0;
    always @(posedge clk) if (lane_me_prev) ref378 <= {ref378[15:0], r_xo[3088 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref378[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1440 +: 8] !== ref378[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 378 lane vm_g6_b6_xf0>p2"); end end end
    reg [23:0] ref379=0;
    always @(posedge clk) if (lane_me_prev) ref379 <= {ref379[15:0], d_e[704 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref379[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1448 +: 8] !== ref379[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 379 lane vm_g7_b2_xf1>p8"); end end end
    reg [31:0] ref380=0;
    always @(posedge clk) if (lane_me_prev) ref380 <= {ref380[23:0], d_e[712 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref380[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1456 +: 8] !== ref380[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 380 lane vm_g7_b2_xf0>p8"); end end end
    reg [63:0] ref381=0;
    always @(posedge clk) if (lane_me_prev) ref381 <= {ref381[55:0], d_e[720 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref381[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1464 +: 8] !== ref381[56 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 381 lane vm_g7_b1_xf1>p8"); end end end
    reg [63:0] ref382=0;
    always @(posedge clk) if (lane_me_prev) ref382 <= {ref382[55:0], d_e[728 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref382[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1472 +: 8] !== ref382[56 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 382 lane vm_g7_b1_xf1>p9"); end end end
    reg [63:0] ref383=0;
    always @(posedge clk) if (lane_me_prev) ref383 <= {ref383[55:0], r_xo[3112 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref383[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1480 +: 8] !== ref383[56 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 383 lane vm_g6_b6_xf0>p5"); end end end
    reg [55:0] ref384=0;
    always @(posedge clk) if (lane_me_prev) ref384 <= {ref384[47:0], r_xo[1040 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref384[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1488 +: 8] !== ref384[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 384 lane vm_g6_b2_xf0>p2"); end end end
    reg [15:0] ref385=0;
    always @(posedge clk) if (lane_me_prev) ref385 <= {ref385[7:0], r_xo[3120 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref385[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1496 +: 8] !== ref385[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 385 lane vm_g6_b6_xf0>p6"); end end end
    reg [63:0] ref386=0;
    always @(posedge clk) if (lane_me_prev) ref386 <= {ref386[55:0], r_xo[3648 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref386[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1504 +: 8] !== ref386[56 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 386 lane vm_g6_b7_xf0>p8"); end end end
    reg [63:0] ref387=0;
    always @(posedge clk) if (lane_me_prev) ref387 <= {ref387[55:0], r_xo[1320 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref387[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1512 +: 8] !== ref387[56 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 387 lane vm_g6_b2_xf1>p5"); end end end
    reg [63:0] ref388=0;
    always @(posedge clk) if (lane_me_prev) ref388 <= {ref388[55:0], r_xo[808 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref388[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1520 +: 8] !== ref388[56 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 388 lane vm_g6_b1_xf1>p5"); end end end
    reg [55:0] ref389=0;
    always @(posedge clk) if (lane_me_prev) ref389 <= {ref389[47:0], r_xo[1064 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref389[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1528 +: 8] !== ref389[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 389 lane vm_g6_b2_xf0>p5"); end end end
    reg [55:0] ref390=0;
    always @(posedge clk) if (lane_me_prev) ref390 <= {ref390[47:0], r_xo[1072 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref390[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1536 +: 8] !== ref390[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 390 lane vm_g6_b2_xf0>p6"); end end end
    reg [7:0] ref391=0;
    always @(posedge clk) if (lane_me_prev) ref391 <= d_w[1584 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref391[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[888 +: 8] !== ref391[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 391 lane vm_g5_b2_xf1>p19"); end end end
    reg [47:0] ref392=0;
    always @(posedge clk) if (lane_me_prev) ref392 <= {ref392[39:0], d_e[736 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref392[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1544 +: 8] !== ref392[40 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 392 lane vm_g7_b5_xf1>p5"); end end end
    reg [23:0] ref393=0;
    always @(posedge clk) if (lane_me_prev) ref393 <= {ref393[15:0], d_w[1592 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref393[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[696 +: 8] !== ref393[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 393 lane vm_g5_b2_xf0>p30"); end end end
    reg [23:0] ref394=0;
    always @(posedge clk) if (lane_me_prev) ref394 <= {ref394[15:0], d_w[1600 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref394[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[704 +: 8] !== ref394[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 394 lane vm_g5_b1_xf1>p30"); end end end
    reg [15:0] ref395=0;
    always @(posedge clk) if (lane_me_prev) ref395 <= {ref395[7:0], d_w[1608 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref395[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[896 +: 8] !== ref395[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 395 lane vm_g5_b3_xf0>p21"); end end end
    reg [15:0] ref396=0;
    always @(posedge clk) if (lane_me_prev) ref396 <= {ref396[7:0], d_w[1616 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref396[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[904 +: 8] !== ref396[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 396 lane vm_g5_b2_xf1>p21"); end end end
    reg [15:0] ref397=0;
    always @(posedge clk) if (lane_me_prev) ref397 <= {ref397[7:0], d_w[1624 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref397[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[912 +: 8] !== ref397[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 397 lane vm_g5_b2_xf0>p21"); end end end
    reg [15:0] ref398=0;
    always @(posedge clk) if (lane_me_prev) ref398 <= {ref398[7:0], d_w[1632 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref398[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[920 +: 8] !== ref398[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 398 lane vm_g5_b1_xf1>p21"); end end end
    reg [7:0] ref399=0;
    always @(posedge clk) if (lane_me_prev) ref399 <= d_w[1640 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref399[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[928 +: 8] !== ref399[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 399 lane vm_g5_b3_xf0>p17"); end end end
    reg [7:0] ref400=0;
    always @(posedge clk) if (lane_me_prev) ref400 <= d_w[1648 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref400[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[936 +: 8] !== ref400[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 400 lane vm_g5_b2_xf1>p17"); end end end
    reg [7:0] ref401=0;
    always @(posedge clk) if (lane_me_prev) ref401 <= d_w[1656 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref401[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[944 +: 8] !== ref401[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 401 lane vm_g5_b2_xf0>p17"); end end end
    reg [47:0] ref402=0;
    always @(posedge clk) if (lane_me_prev) ref402 <= {ref402[39:0], r_xo[3072 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref402[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1552 +: 8] !== ref402[40 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 402 lane vm_g6_b6_xf0>p0"); end end end
    reg [47:0] ref403=0;
    always @(posedge clk) if (lane_me_prev) ref403 <= {ref403[39:0], r_xo[3360 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref403[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1560 +: 8] !== ref403[40 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 403 lane vm_g6_b6_xf1>p4"); end end end
    reg [7:0] ref404=0;
    always @(posedge clk) if (lane_me_prev) ref404 <= d_w[1664 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref404[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[952 +: 8] !== ref404[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 404 lane vm_g5_b3_xf0>p18"); end end end
    reg [7:0] ref405=0;
    always @(posedge clk) if (lane_me_prev) ref405 <= d_w[1672 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref405[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[960 +: 8] !== ref405[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 405 lane vm_g5_b2_xf1>p18"); end end end
    reg [7:0] ref406=0;
    always @(posedge clk) if (lane_me_prev) ref406 <= d_w[1680 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref406[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[968 +: 8] !== ref406[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 406 lane vm_g5_b2_xf0>p18"); end end end
    reg [7:0] ref407=0;
    always @(posedge clk) if (lane_me_prev) ref407 <= d_w[1688 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref407[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[976 +: 8] !== ref407[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 407 lane vm_g5_b1_xf1>p18"); end end end
    reg [23:0] ref408=0;
    always @(posedge clk) if (lane_me_prev) ref408 <= {ref408[15:0], d_w[1696 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref408[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[712 +: 8] !== ref408[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 408 lane vm_g5_b2_xf1>p29"); end end end
    reg [23:0] ref409=0;
    always @(posedge clk) if (lane_me_prev) ref409 <= {ref409[15:0], d_w[1704 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref409[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[720 +: 8] !== ref409[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 409 lane vm_g5_b2_xf0>p29"); end end end
    reg [39:0] ref410=0;
    always @(posedge clk) if (lane_me_prev) ref410 <= {ref410[31:0], d_e[744 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref410[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1568 +: 8] !== ref410[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 410 lane vm_g7_b3_xf0>p4"); end end end
    reg [39:0] ref411=0;
    always @(posedge clk) if (lane_me_prev) ref411 <= {ref411[31:0], d_e[752 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref411[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1576 +: 8] !== ref411[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 411 lane vm_g7_b2_xf1>p4"); end end end
    reg [23:0] ref412=0;
    always @(posedge clk) if (lane_me_prev) ref412 <= {ref412[15:0], d_e[760 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref412[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1584 +: 8] !== ref412[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 412 lane vm_g7_b1_xf1>p4"); end end end
    reg [47:0] ref413=0;
    always @(posedge clk) if (lane_me_prev) ref413 <= {ref413[39:0], d_w[1712 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref413[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[728 +: 8] !== ref413[40 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 413 lane vm_g5_b1_xf0>p31"); end end end
    reg [47:0] ref414=0;
    always @(posedge clk) if (lane_me_prev) ref414 <= {ref414[39:0], r_xo[3616 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref414[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1592 +: 8] !== ref414[40 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 414 lane vm_g6_b7_xf0>p4"); end end end
    reg [47:0] ref415=0;
    always @(posedge clk) if (lane_me_prev) ref415 <= {ref415[39:0], r_xo[1312 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref415[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1600 +: 8] !== ref415[40 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 415 lane vm_g6_b2_xf1>p4"); end end end
    reg [55:0] ref416=0;
    always @(posedge clk) if (lane_me_prev) ref416 <= {ref416[47:0], r_xo[1568 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref416[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1608 +: 8] !== ref416[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 416 lane vm_g6_b3_xf0>p4"); end end end
    reg [71:0] ref417=0;
    always @(posedge clk) if (lane_me_prev) ref417 <= {ref417[63:0], d_w[1720 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref417[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[984 +: 8] !== ref417[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 417 lane vm_g5_b3_xf1>p20"); end end end
    reg [71:0] ref418=0;
    always @(posedge clk) if (lane_me_prev) ref418 <= {ref418[63:0], d_w[1728 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref418[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[992 +: 8] !== ref418[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 418 lane vm_g5_b3_xf0>p20"); end end end
    reg [71:0] ref419=0;
    always @(posedge clk) if (lane_me_prev) ref419 <= {ref419[63:0], d_w[1736 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref419[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1000 +: 8] !== ref419[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 419 lane vm_g5_b2_xf1>p20"); end end end
    reg [71:0] ref420=0;
    always @(posedge clk) if (lane_me_prev) ref420 <= {ref420[63:0], d_w[1744 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref420[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1008 +: 8] !== ref420[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 420 lane vm_g5_b2_xf0>p20"); end end end
    reg [23:0] ref421=0;
    always @(posedge clk) if (lane_me_prev) ref421 <= {ref421[15:0], d_e[768 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref421[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1616 +: 8] !== ref421[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 421 lane vm_g7_b5_xf1>p4"); end end end
    reg [55:0] ref422=0;
    always @(posedge clk) if (lane_me_prev) ref422 <= {ref422[47:0], d_w[1752 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref422[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[736 +: 8] !== ref422[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 422 lane vm_g5_b1_xf1>p27"); end end end
    reg [39:0] ref423=0;
    always @(posedge clk) if (lane_me_prev) ref423 <= {ref423[31:0], d_w[1760 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref423[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1016 +: 8] !== ref423[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 423 lane vm_g5_b3_xf0>p25"); end end end
    reg [71:0] ref424=0;
    always @(posedge clk) if (lane_me_prev) ref424 <= {ref424[63:0], d_w[1768 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref424[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1024 +: 8] !== ref424[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 424 lane vm_g5_b2_xf1>p25"); end end end
    reg [55:0] ref425=0;
    always @(posedge clk) if (lane_me_prev) ref425 <= {ref425[47:0], d_w[1776 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref425[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[744 +: 8] !== ref425[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 425 lane vm_g5_b1_xf1>p26"); end end end
    reg [39:0] ref426=0;
    always @(posedge clk) if (lane_me_prev) ref426 <= {ref426[31:0], d_w[1784 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref426[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1032 +: 8] !== ref426[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 426 lane vm_g5_b2_xf0>p25"); end end end
    reg [39:0] ref427=0;
    always @(posedge clk) if (lane_me_prev) ref427 <= {ref427[31:0], d_w[1792 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref427[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1040 +: 8] !== ref427[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 427 lane vm_g5_b1_xf1>p25"); end end end
    reg [63:0] ref428=0;
    always @(posedge clk) if (lane_me_prev) ref428 <= {ref428[55:0], d_w[1800 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref428[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1048 +: 8] !== ref428[56 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 428 lane vm_g5_b1_xf1>p24"); end end end
    reg [55:0] ref429=0;
    always @(posedge clk) if (lane_me_prev) ref429 <= {ref429[47:0], r_xo[1592 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref429[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1624 +: 8] !== ref429[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 429 lane vm_g6_b3_xf0>p7"); end end end
    reg [63:0] ref430=0;
    always @(posedge clk) if (lane_me_prev) ref430 <= {ref430[55:0], d_w[1808 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref430[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1056 +: 8] !== ref430[56 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 430 lane vm_g5_b1_xf1>p23"); end end end
    reg [47:0] ref431=0;
    always @(posedge clk) if (lane_me_prev) ref431 <= {ref431[39:0], r_xo[824 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref431[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1632 +: 8] !== ref431[40 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 431 lane vm_g6_b1_xf1>p7"); end end end
    reg [23:0] ref432=0;
    always @(posedge clk) if (lane_me_prev) ref432 <= {ref432[15:0], d_w[1816 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref432[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[752 +: 8] !== ref432[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 432 lane vm_g5_b1_xf1>p31"); end end end
    reg [23:0] ref433=0;
    always @(posedge clk) if (lane_me_prev) ref433 <= {ref433[15:0], d_w[1824 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref433[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1064 +: 8] !== ref433[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 433 lane vm_g5_b3_xf1>p22"); end end end
    reg [23:0] ref434=0;
    always @(posedge clk) if (lane_me_prev) ref434 <= {ref434[15:0], d_w[1832 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref434[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1072 +: 8] !== ref434[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 434 lane vm_g5_b3_xf0>p22"); end end end
    reg [23:0] ref435=0;
    always @(posedge clk) if (lane_me_prev) ref435 <= {ref435[15:0], d_e[776 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref435[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1640 +: 8] !== ref435[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 435 lane vm_g7_b6_xf1>p5"); end end end
    reg [23:0] ref436=0;
    always @(posedge clk) if (lane_me_prev) ref436 <= {ref436[15:0], d_e[784 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref436[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1648 +: 8] !== ref436[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 436 lane vm_g7_b6_xf0>p5"); end end end
    reg [47:0] ref437=0;
    always @(posedge clk) if (lane_me_prev) ref437 <= {ref437[39:0], d_e[792 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref437[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1656 +: 8] !== ref437[40 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 437 lane vm_g7_b2_xf1>p5"); end end end
    reg [31:0] ref438=0;
    always @(posedge clk) if (lane_me_prev) ref438 <= {ref438[23:0], d_e[800 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref438[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1664 +: 8] !== ref438[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 438 lane vm_g7_b2_xf1>p6"); end end end
    reg [31:0] ref439=0;
    always @(posedge clk) if (lane_me_prev) ref439 <= {ref439[23:0], d_e[808 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref439[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1672 +: 8] !== ref439[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 439 lane vm_g7_b3_xf0>p7"); end end end
    reg [23:0] ref440=0;
    always @(posedge clk) if (lane_me_prev) ref440 <= {ref440[15:0], d_w[1840 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref440[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[760 +: 8] !== ref440[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 440 lane vm_g5_b2_xf1>p28"); end end end
    reg [15:0] ref441=0;
    always @(posedge clk) if (lane_me_prev) ref441 <= {ref441[7:0], r_xo[3624 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref441[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1680 +: 8] !== ref441[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 441 lane vm_g6_b7_xf0>p5"); end end end
    reg [15:0] ref442=0;
    always @(posedge clk) if (lane_me_prev) ref442 <= {ref442[7:0], r_xo[3368 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref442[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1688 +: 8] !== ref442[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 442 lane vm_g6_b6_xf1>p5"); end end end
    reg [23:0] ref443=0;
    always @(posedge clk) if (lane_me_prev) ref443 <= {ref443[15:0], r_xo[3632 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref443[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1696 +: 8] !== ref443[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 443 lane vm_g6_b7_xf0>p6"); end end end
    reg [7:0] ref444=0;
    always @(posedge clk) if (lane_me_prev) ref444 <= r_xo[1576 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref444[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1704 +: 8] !== ref444[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 444 lane vm_g6_b3_xf0>p5"); end end end
    reg [7:0] ref445=0;
    always @(posedge clk) if (lane_me_prev) ref445 <= r_xo[1584 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref445[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1712 +: 8] !== ref445[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 445 lane vm_g6_b3_xf0>p6"); end end end
    reg [23:0] ref446=0;
    always @(posedge clk) if (lane_me_prev) ref446 <= {ref446[15:0], d_w[1848 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref446[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1080 +: 8] !== ref446[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 446 lane vm_g5_b3_xf0>p19"); end end end
    reg [23:0] ref447=0;
    always @(posedge clk) if (lane_me_prev) ref447 <= {ref447[15:0], d_w[1856 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref447[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[768 +: 8] !== ref447[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 447 lane vm_g5_b3_xf1>p30"); end end end
    reg [23:0] ref448=0;
    always @(posedge clk) if (lane_me_prev) ref448 <= {ref448[15:0], d_w[1864 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref448[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[776 +: 8] !== ref448[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 448 lane vm_g5_b3_xf1>p27"); end end end
    reg [55:0] ref449=0;
    always @(posedge clk) if (lane_me_prev) ref449 <= {ref449[47:0], d_w[1872 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref449[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[784 +: 8] !== ref449[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 449 lane vm_g5_b3_xf0>p27"); end end end
    reg [23:0] ref450=0;
    always @(posedge clk) if (lane_me_prev) ref450 <= {ref450[15:0], d_w[1880 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref450[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[792 +: 8] !== ref450[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 450 lane vm_g5_b3_xf1>p26"); end end end
    reg [55:0] ref451=0;
    always @(posedge clk) if (lane_me_prev) ref451 <= {ref451[47:0], d_w[1888 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref451[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[800 +: 8] !== ref451[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 451 lane vm_g5_b2_xf1>p27"); end end end
    reg [23:0] ref452=0;
    always @(posedge clk) if (lane_me_prev) ref452 <= {ref452[15:0], d_w[1896 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref452[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[808 +: 8] !== ref452[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 452 lane vm_g5_b3_xf0>p26"); end end end
    reg [39:0] ref453=0;
    always @(posedge clk) if (lane_me_prev) ref453 <= {ref453[31:0], d_w[1904 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref453[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1088 +: 8] !== ref453[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 453 lane vm_g5_b3_xf1>p25"); end end end
    reg [55:0] ref454=0;
    always @(posedge clk) if (lane_me_prev) ref454 <= {ref454[47:0], d_w[1912 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref454[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[816 +: 8] !== ref454[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 454 lane vm_g5_b2_xf0>p27"); end end end
    reg [23:0] ref455=0;
    always @(posedge clk) if (lane_me_prev) ref455 <= {ref455[15:0], d_w[1920 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref455[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[824 +: 8] !== ref455[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 455 lane vm_g5_b2_xf1>p26"); end end end
    reg [55:0] ref456=0;
    always @(posedge clk) if (lane_me_prev) ref456 <= {ref456[47:0], r_xo[3896 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref456[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1720 +: 8] !== ref456[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 456 lane vm_g6_b7_xf1>p7"); end end end
    reg [31:0] ref457=0;
    always @(posedge clk) if (lane_me_prev) ref457 <= {ref457[23:0], d_w[1928 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref457[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1096 +: 8] !== ref457[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 457 lane vm_g5_b3_xf1>p24"); end end end
    reg [23:0] ref458=0;
    always @(posedge clk) if (lane_me_prev) ref458 <= {ref458[15:0], d_w[1936 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref458[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[832 +: 8] !== ref458[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 458 lane vm_g5_b2_xf0>p26"); end end end
    reg [63:0] ref459=0;
    always @(posedge clk) if (lane_me_prev) ref459 <= {ref459[55:0], d_w[1944 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref459[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1104 +: 8] !== ref459[56 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 459 lane vm_g5_b3_xf0>p24"); end end end
    reg [31:0] ref460=0;
    always @(posedge clk) if (lane_me_prev) ref460 <= {ref460[23:0], d_w[1952 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref460[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1112 +: 8] !== ref460[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 460 lane vm_g5_b3_xf1>p23"); end end end
    reg [31:0] ref461=0;
    always @(posedge clk) if (lane_me_prev) ref461 <= {ref461[23:0], d_w[1960 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref461[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1120 +: 8] !== ref461[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 461 lane vm_g5_b2_xf1>p24"); end end end
    reg [63:0] ref462=0;
    always @(posedge clk) if (lane_me_prev) ref462 <= {ref462[55:0], d_w[1968 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref462[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1128 +: 8] !== ref462[56 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 462 lane vm_g5_b3_xf0>p23"); end end end
    reg [63:0] ref463=0;
    always @(posedge clk) if (lane_me_prev) ref463 <= {ref463[55:0], d_w[1976 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref463[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1136 +: 8] !== ref463[56 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 463 lane vm_g5_b2_xf0>p24"); end end end
    reg [31:0] ref464=0;
    always @(posedge clk) if (lane_me_prev) ref464 <= {ref464[23:0], d_w[1984 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref464[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1144 +: 8] !== ref464[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 464 lane vm_g5_b2_xf1>p23"); end end end
    reg [55:0] ref465=0;
    always @(posedge clk) if (lane_me_prev) ref465 <= {ref465[47:0], r_xo[1848 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref465[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1728 +: 8] !== ref465[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 465 lane vm_g6_b3_xf1>p7"); end end end
    reg [31:0] ref466=0;
    always @(posedge clk) if (lane_me_prev) ref466 <= {ref466[23:0], d_w[1992 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref466[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1152 +: 8] !== ref466[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 466 lane vm_g5_b2_xf0>p23"); end end end
    reg [47:0] ref467=0;
    always @(posedge clk) if (lane_me_prev) ref467 <= {ref467[39:0], r_xo[1336 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref467[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1736 +: 8] !== ref467[40 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 467 lane vm_g6_b2_xf1>p7"); end end end
    reg [23:0] ref468=0;
    always @(posedge clk) if (lane_me_prev) ref468 <= {ref468[15:0], d_e[816 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref468[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1744 +: 8] !== ref468[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 468 lane vm_g7_b7_xf0>p7"); end end end
    reg [23:0] ref469=0;
    always @(posedge clk) if (lane_me_prev) ref469 <= {ref469[15:0], d_e[824 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref469[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1752 +: 8] !== ref469[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 469 lane vm_g7_b3_xf1>p6"); end end end
    reg [23:0] ref470=0;
    always @(posedge clk) if (lane_me_prev) ref470 <= {ref470[15:0], d_e[832 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref470[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1760 +: 8] !== ref470[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 470 lane vm_g7_b3_xf1>p7"); end end end
    reg [39:0] ref471=0;
    always @(posedge clk) if (lane_me_prev) ref471 <= {ref471[31:0], d_w[2000 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref471[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[840 +: 8] !== ref471[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 471 lane vm_g5_b2_xf0>p31"); end end end
    reg [23:0] ref472=0;
    always @(posedge clk) if (lane_me_prev) ref472 <= {ref472[15:0], r_xo[3640 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref472[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1768 +: 8] !== ref472[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 472 lane vm_g6_b7_xf0>p7"); end end end
    reg [23:0] ref473=0;
    always @(posedge clk) if (lane_me_prev) ref473 <= {ref473[15:0], d_e[840 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref473[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1776 +: 8] !== ref473[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 473 lane vm_g7_b7_xf1>p5"); end end end
    reg [39:0] ref474=0;
    always @(posedge clk) if (lane_me_prev) ref474 <= {ref474[31:0], d_e[848 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref474[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1784 +: 8] !== ref474[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 474 lane vm_g7_b7_xf0>p5"); end end end
    reg [23:0] ref475=0;
    always @(posedge clk) if (lane_me_prev) ref475 <= {ref475[15:0], d_e[856 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref475[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1792 +: 8] !== ref475[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 475 lane vm_g7_b3_xf1>p5"); end end end
    reg [47:0] ref476=0;
    always @(posedge clk) if (lane_me_prev) ref476 <= {ref476[39:0], d_e[864 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref476[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1800 +: 8] !== ref476[40 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 476 lane vm_g7_b3_xf0>p5"); end end end
    reg [31:0] ref477=0;
    always @(posedge clk) if (lane_me_prev) ref477 <= {ref477[23:0], d_e[872 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref477[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1808 +: 8] !== ref477[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 477 lane vm_g7_b3_xf0>p6"); end end end
    reg [55:0] ref478=0;
    always @(posedge clk) if (lane_me_prev) ref478 <= {ref478[47:0], r_xo[3880 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref478[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1816 +: 8] !== ref478[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 478 lane vm_g6_b7_xf1>p5"); end end end
    reg [23:0] ref479=0;
    always @(posedge clk) if (lane_me_prev) ref479 <= {ref479[15:0], r_xo[3888 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref479[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1824 +: 8] !== ref479[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 479 lane vm_g6_b7_xf1>p6"); end end end
    reg [47:0] ref480=0;
    always @(posedge clk) if (lane_me_prev) ref480 <= {ref480[39:0], r_xo[1832 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref480[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1832 +: 8] !== ref480[40 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 480 lane vm_g6_b3_xf1>p5"); end end end
    reg [15:0] ref481=0;
    always @(posedge clk) if (lane_me_prev) ref481 <= {ref481[7:0], r_xo[1840 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref481[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1840 +: 8] !== ref481[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 481 lane vm_g6_b3_xf1>p6"); end end end
    reg [15:0] ref482=0;
    always @(posedge clk) if (lane_me_prev) ref482 <= {ref482[7:0], r_xo[1328 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref482[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1848 +: 8] !== ref482[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 482 lane vm_g6_b2_xf1>p6"); end end end
    reg [15:0] ref483=0;
    always @(posedge clk) if (lane_me_prev) ref483 <= {ref483[7:0], d_w[2008 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref483[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1160 +: 8] !== ref483[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 483 lane vm_g5_b3_xf1>p19"); end end end
    reg [23:0] ref484=0;
    always @(posedge clk) if (lane_me_prev) ref484 <= {ref484[15:0], d_w[2016 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref484[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[848 +: 8] !== ref484[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 484 lane vm_g5_b2_xf1>p31"); end end end
    reg [39:0] ref485=0;
    always @(posedge clk) if (lane_me_prev) ref485 <= {ref485[31:0], d_w[2024 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref485[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[856 +: 8] !== ref485[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 485 lane vm_g5_b2_xf1>p30"); end end end
    reg [71:0] ref486=0;
    always @(posedge clk) if (lane_me_prev) ref486 <= {ref486[63:0], d_w[2032 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref486[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1168 +: 8] !== ref486[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 486 lane vm_g5_b3_xf1>p21"); end end end
    reg [63:0] ref487=0;
    always @(posedge clk) if (lane_me_prev) ref487 <= {ref487[55:0], d_w[2040 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref487[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1176 +: 8] !== ref487[56 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 487 lane vm_g5_b3_xf1>p18"); end end end
    reg [23:0] ref488=0;
    always @(posedge clk) if (lane_me_prev) ref488 <= {ref488[15:0], d_e[880 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref488[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1856 +: 8] !== ref488[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 488 lane vm_g7_b7_xf1>p6"); end end end
    reg [23:0] ref489=0;
    always @(posedge clk) if (lane_me_prev) ref489 <= {ref489[15:0], d_e[888 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref489[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1864 +: 8] !== ref489[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 489 lane vm_g7_b7_xf1>p7"); end end end
    reg [23:0] ref490=0;
    always @(posedge clk) if (lane_me_prev) ref490 <= {ref490[15:0], d_e[896 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref490[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1872 +: 8] !== ref490[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 490 lane vm_g7_b7_xf0>p6"); end end end
    reg [23:0] ref491=0;
    always @(posedge clk) if (lane_me_prev) ref491 <= {ref491[15:0], d_e[904 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref491[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1880 +: 8] !== ref491[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 491 lane vm_g7_b6_xf1>p6"); end end end
    reg [23:0] ref492=0;
    always @(posedge clk) if (lane_me_prev) ref492 <= {ref492[15:0], d_w[2048 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref492[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[864 +: 8] !== ref492[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 492 lane vm_g5_b3_xf1>p31"); end end end
    reg [39:0] ref493=0;
    always @(posedge clk) if (lane_me_prev) ref493 <= {ref493[31:0], d_w[2056 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref493[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[872 +: 8] !== ref493[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 493 lane vm_g5_b3_xf0>p31"); end end end
    reg [39:0] ref494=0;
    always @(posedge clk) if (lane_me_prev) ref494 <= {ref494[31:0], d_w[2064 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref494[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[880 +: 8] !== ref494[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 494 lane vm_g5_b3_xf0>p30"); end end end
    reg [39:0] ref495=0;
    always @(posedge clk) if (lane_me_prev) ref495 <= {ref495[31:0], d_w[2072 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref495[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[888 +: 8] !== ref495[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 495 lane vm_g5_b3_xf1>p29"); end end end
    reg [39:0] ref496=0;
    always @(posedge clk) if (lane_me_prev) ref496 <= {ref496[31:0], d_w[2080 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref496[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[896 +: 8] !== ref496[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 496 lane vm_g5_b3_xf0>p29"); end end end
    reg [23:0] ref497=0;
    always @(posedge clk) if (lane_me_prev) ref497 <= {ref497[15:0], d_w[2088 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref497[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[904 +: 8] !== ref497[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 497 lane vm_g5_b3_xf1>p28"); end end end
    reg [23:0] ref498=0;
    always @(posedge clk) if (lane_me_prev) ref498 <= {ref498[15:0], d_w[2096 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref498[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[912 +: 8] !== ref498[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 498 lane vm_g5_b3_xf0>p28"); end end end
    reg [39:0] ref499=0;
    always @(posedge clk) if (lane_me_prev) ref499 <= {ref499[31:0], r_xo[3872 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref499[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1888 +: 8] !== ref499[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 499 lane vm_g6_b7_xf1>p4"); end end end
    reg [23:0] ref500=0;
    always @(posedge clk) if (lane_me_prev) ref500 <= {ref500[15:0], d_e[912 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref500[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1896 +: 8] !== ref500[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 500 lane vm_g7_b7_xf0>p9"); end end end
    reg [55:0] ref501=0;
    always @(posedge clk) if (lane_me_prev) ref501 <= {ref501[47:0], d_e[920 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref501[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1904 +: 8] !== ref501[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 501 lane vm_g7_b6_xf0>p9"); end end end
    reg [39:0] ref502=0;
    always @(posedge clk) if (lane_me_prev) ref502 <= {ref502[31:0], d_e[928 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref502[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1912 +: 8] !== ref502[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 502 lane vm_g7_b3_xf1>p9"); end end end
    reg [63:0] ref503=0;
    always @(posedge clk) if (lane_me_prev) ref503 <= {ref503[55:0], d_e[936 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref503[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1920 +: 8] !== ref503[56 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 503 lane vm_g7_b3_xf0>p9"); end end end
    reg [31:0] ref504=0;
    always @(posedge clk) if (lane_me_prev) ref504 <= {ref504[23:0], d_e[944 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref504[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1928 +: 8] !== ref504[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 504 lane vm_g7_b2_xf1>p9"); end end end
    reg [63:0] ref505=0;
    always @(posedge clk) if (lane_me_prev) ref505 <= {ref505[55:0], d_e[952 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref505[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1936 +: 8] !== ref505[56 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 505 lane vm_g7_b2_xf0>p9"); end end end
    reg [55:0] ref506=0;
    always @(posedge clk) if (lane_me_prev) ref506 <= {ref506[47:0], r_xo[256 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref506[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1944 +: 8] !== ref506[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 506 lane vm_g6_b0_xf1>p0"); end end end
    reg [55:0] ref507=0;
    always @(posedge clk) if (lane_me_prev) ref507 <= {ref507[47:0], r_xo[0 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref507[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1952 +: 8] !== ref507[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 507 lane vm_g6_b0_xf0>p0"); end end end
    reg [55:0] ref508=0;
    always @(posedge clk) if (lane_me_prev) ref508 <= {ref508[47:0], r_xo[264 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref508[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1960 +: 8] !== ref508[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 508 lane vm_g6_b0_xf1>p1"); end end end
    reg [55:0] ref509=0;
    always @(posedge clk) if (lane_me_prev) ref509 <= {ref509[47:0], r_xo[8 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref509[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1968 +: 8] !== ref509[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 509 lane vm_g6_b0_xf0>p1"); end end end
    reg [71:0] ref510=0;
    always @(posedge clk) if (lane_me_prev) ref510 <= {ref510[63:0], r_xo[3912 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref510[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1976 +: 8] !== ref510[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 510 lane vm_g6_b7_xf1>p9"); end end end
    reg [55:0] ref511=0;
    always @(posedge clk) if (lane_me_prev) ref511 <= {ref511[47:0], r_xo[16 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref511[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1984 +: 8] !== ref511[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 511 lane vm_g6_b0_xf0>p2"); end end end
    reg [71:0] ref512=0;
    always @(posedge clk) if (lane_me_prev) ref512 <= {ref512[63:0], r_xo[3400 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref512[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[1992 +: 8] !== ref512[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 512 lane vm_g6_b6_xf1>p9"); end end end
    reg [63:0] ref513=0;
    always @(posedge clk) if (lane_me_prev) ref513 <= {ref513[55:0], r_xo[24 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref513[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2000 +: 8] !== ref513[56 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 513 lane vm_g6_b0_xf0>p3"); end end end
    reg [71:0] ref514=0;
    always @(posedge clk) if (lane_me_prev) ref514 <= {ref514[63:0], r_xo[3408 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref514[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2008 +: 8] !== ref514[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 514 lane vm_g6_b6_xf1>p10"); end end end
    reg [71:0] ref515=0;
    always @(posedge clk) if (lane_me_prev) ref515 <= {ref515[63:0], r_xo[1864 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref515[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2016 +: 8] !== ref515[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 515 lane vm_g6_b3_xf1>p9"); end end end
    reg [71:0] ref516=0;
    always @(posedge clk) if (lane_me_prev) ref516 <= {ref516[63:0], r_xo[304 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref516[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2024 +: 8] !== ref516[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 516 lane vm_g6_b0_xf1>p6"); end end end
    reg [71:0] ref517=0;
    always @(posedge clk) if (lane_me_prev) ref517 <= {ref517[63:0], r_xo[48 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref517[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2032 +: 8] !== ref517[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 517 lane vm_g6_b0_xf0>p6"); end end end
    reg [71:0] ref518=0;
    always @(posedge clk) if (lane_me_prev) ref518 <= {ref518[63:0], r_xo[312 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref518[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2040 +: 8] !== ref518[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 518 lane vm_g6_b0_xf1>p7"); end end end
    reg [71:0] ref519=0;
    always @(posedge clk) if (lane_me_prev) ref519 <= {ref519[63:0], r_xo[56 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref519[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2048 +: 8] !== ref519[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 519 lane vm_g6_b0_xf0>p7"); end end end
    reg [71:0] ref520=0;
    always @(posedge clk) if (lane_me_prev) ref520 <= {ref520[63:0], r_xo[64 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref520[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2056 +: 8] !== ref520[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 520 lane vm_g6_b0_xf0>p8"); end end end
    reg [79:0] ref521=0;
    always @(posedge clk) if (lane_me_prev) ref521 <= {ref521[71:0], r_xo[328 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref521[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2064 +: 8] !== ref521[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 521 lane vm_g6_b0_xf1>p9"); end end end
    reg [79:0] ref522=0;
    always @(posedge clk) if (lane_me_prev) ref522 <= {ref522[71:0], r_xo[72 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref522[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2072 +: 8] !== ref522[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 522 lane vm_g6_b0_xf0>p9"); end end end
    reg [79:0] ref523=0;
    always @(posedge clk) if (lane_me_prev) ref523 <= {ref523[71:0], r_xo[336 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref523[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2080 +: 8] !== ref523[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 523 lane vm_g6_b0_xf1>p10"); end end end
    reg [79:0] ref524=0;
    always @(posedge clk) if (lane_me_prev) ref524 <= {ref524[71:0], r_xo[80 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref524[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2088 +: 8] !== ref524[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 524 lane vm_g6_b0_xf0>p10"); end end end
    reg [79:0] ref525=0;
    always @(posedge clk) if (lane_me_prev) ref525 <= {ref525[71:0], r_xo[88 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref525[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2096 +: 8] !== ref525[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 525 lane vm_g6_b0_xf0>p11"); end end end
    reg [15:0] ref526=0;
    always @(posedge clk) if (lane_me_prev) ref526 <= {ref526[7:0], d_w[2104 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref526[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1184 +: 8] !== ref526[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 526 lane vm_g5_b5_xf1>p22"); end end end
    reg [15:0] ref527=0;
    always @(posedge clk) if (lane_me_prev) ref527 <= {ref527[7:0], d_w[2112 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref527[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1192 +: 8] !== ref527[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 527 lane vm_g5_b5_xf0>p22"); end end end
    reg [15:0] ref528=0;
    always @(posedge clk) if (lane_me_prev) ref528 <= {ref528[7:0], d_w[2120 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref528[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1200 +: 8] !== ref528[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 528 lane vm_g5_b5_xf1>p21"); end end end
    reg [15:0] ref529=0;
    always @(posedge clk) if (lane_me_prev) ref529 <= {ref529[7:0], d_w[2128 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref529[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1208 +: 8] !== ref529[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 529 lane vm_g5_b4_xf1>p22"); end end end
    reg [15:0] ref530=0;
    always @(posedge clk) if (lane_me_prev) ref530 <= {ref530[7:0], d_w[2136 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref530[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1216 +: 8] !== ref530[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 530 lane vm_g5_b4_xf0>p22"); end end end
    reg [23:0] ref531=0;
    always @(posedge clk) if (lane_me_prev) ref531 <= {ref531[15:0], d_e[960 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref531[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2104 +: 8] !== ref531[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 531 lane vm_g7_b7_xf0>p10"); end end end
    reg [55:0] ref532=0;
    always @(posedge clk) if (lane_me_prev) ref532 <= {ref532[47:0], d_e[968 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref532[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2112 +: 8] !== ref532[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 532 lane vm_g7_b6_xf1>p10"); end end end
    reg [31:0] ref533=0;
    always @(posedge clk) if (lane_me_prev) ref533 <= {ref533[23:0], d_e[976 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref533[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2120 +: 8] !== ref533[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 533 lane vm_g7_b3_xf1>p10"); end end end
    reg [23:0] ref534=0;
    always @(posedge clk) if (lane_me_prev) ref534 <= {ref534[15:0], d_e[984 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref534[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2128 +: 8] !== ref534[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 534 lane vm_g7_b5_xf1>p10"); end end end
    reg [23:0] ref535=0;
    always @(posedge clk) if (lane_me_prev) ref535 <= {ref535[15:0], d_w[2144 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref535[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1224 +: 8] !== ref535[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 535 lane vm_g5_b5_xf1>p31"); end end end
    reg [71:0] ref536=0;
    always @(posedge clk) if (lane_me_prev) ref536 <= {ref536[63:0], d_e[992 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref536[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2136 +: 8] !== ref536[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 536 lane vm_g7_b3_xf0>p10"); end end end
    reg [71:0] ref537=0;
    always @(posedge clk) if (lane_me_prev) ref537 <= {ref537[63:0], d_e[1000 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref537[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2144 +: 8] !== ref537[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 537 lane vm_g7_b2_xf1>p10"); end end end
    reg [23:0] ref538=0;
    always @(posedge clk) if (lane_me_prev) ref538 <= {ref538[15:0], d_w[2152 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref538[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1232 +: 8] !== ref538[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 538 lane vm_g5_b5_xf0>p31"); end end end
    reg [23:0] ref539=0;
    always @(posedge clk) if (lane_me_prev) ref539 <= {ref539[15:0], d_w[2160 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref539[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1240 +: 8] !== ref539[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 539 lane vm_g5_b4_xf1>p31"); end end end
    reg [55:0] ref540=0;
    always @(posedge clk) if (lane_me_prev) ref540 <= {ref540[47:0], d_w[2168 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref540[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1248 +: 8] !== ref540[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 540 lane vm_g5_b4_xf0>p31"); end end end
    reg [23:0] ref541=0;
    always @(posedge clk) if (lane_me_prev) ref541 <= {ref541[15:0], d_e[1008 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref541[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2152 +: 8] !== ref541[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 541 lane vm_g7_b1_xf1>p10"); end end end
    reg [23:0] ref542=0;
    always @(posedge clk) if (lane_me_prev) ref542 <= {ref542[15:0], d_e[1016 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref542[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2160 +: 8] !== ref542[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 542 lane vm_g7_b1_xf0>p10"); end end end
    reg [23:0] ref543=0;
    always @(posedge clk) if (lane_me_prev) ref543 <= {ref543[15:0], d_w[2176 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref543[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1256 +: 8] !== ref543[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 543 lane vm_g5_b5_xf1>p28"); end end end
    reg [23:0] ref544=0;
    always @(posedge clk) if (lane_me_prev) ref544 <= {ref544[15:0], d_w[2184 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref544[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1264 +: 8] !== ref544[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 544 lane vm_g5_b5_xf0>p28"); end end end
    reg [23:0] ref545=0;
    always @(posedge clk) if (lane_me_prev) ref545 <= {ref545[15:0], d_w[2192 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref545[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1272 +: 8] !== ref545[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 545 lane vm_g5_b4_xf1>p28"); end end end
    reg [23:0] ref546=0;
    always @(posedge clk) if (lane_me_prev) ref546 <= {ref546[15:0], d_w[2200 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref546[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1280 +: 8] !== ref546[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 546 lane vm_g5_b4_xf0>p28"); end end end
    reg [63:0] ref547=0;
    always @(posedge clk) if (lane_me_prev) ref547 <= {ref547[55:0], r_xo[3664 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref547[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2168 +: 8] !== ref547[56 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 547 lane vm_g6_b7_xf0>p10"); end end end
    reg [23:0] ref548=0;
    always @(posedge clk) if (lane_me_prev) ref548 <= {ref548[15:0], d_w[2208 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref548[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1288 +: 8] !== ref548[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 548 lane vm_g5_b5_xf0>p25"); end end end
    reg [23:0] ref549=0;
    always @(posedge clk) if (lane_me_prev) ref549 <= {ref549[15:0], d_w[2216 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref549[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1296 +: 8] !== ref549[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 549 lane vm_g5_b4_xf1>p25"); end end end
    reg [23:0] ref550=0;
    always @(posedge clk) if (lane_me_prev) ref550 <= {ref550[15:0], d_w[2224 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref550[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1304 +: 8] !== ref550[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 550 lane vm_g5_b4_xf0>p25"); end end end
    reg [71:0] ref551=0;
    always @(posedge clk) if (lane_me_prev) ref551 <= {ref551[63:0], r_xo[1616 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref551[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2176 +: 8] !== ref551[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 551 lane vm_g6_b3_xf0>p10"); end end end
    reg [15:0] ref552=0;
    always @(posedge clk) if (lane_me_prev) ref552 <= {ref552[7:0], r_xo[848 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref552[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2184 +: 8] !== ref552[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 552 lane vm_g6_b1_xf1>p10"); end end end
    reg [71:0] ref553=0;
    always @(posedge clk) if (lane_me_prev) ref553 <= {ref553[63:0], d_w[2232 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref553[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1312 +: 8] !== ref553[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 553 lane vm_g5_b5_xf1>p19"); end end end
    reg [39:0] ref554=0;
    always @(posedge clk) if (lane_me_prev) ref554 <= {ref554[31:0], d_w[2240 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref554[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1320 +: 8] !== ref554[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 554 lane vm_g5_b5_xf0>p19"); end end end
    reg [7:0] ref555=0;
    always @(posedge clk) if (lane_me_prev) ref555 <= d_w[2248 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref555[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1328 +: 8] !== ref555[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 555 lane vm_g5_b5_xf1>p18"); end end end
    reg [7:0] ref556=0;
    always @(posedge clk) if (lane_me_prev) ref556 <= d_w[2256 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref556[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1336 +: 8] !== ref556[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 556 lane vm_g5_b4_xf1>p19"); end end end
    reg [71:0] ref557=0;
    always @(posedge clk) if (lane_me_prev) ref557 <= {ref557[63:0], d_w[2264 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref557[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1344 +: 8] !== ref557[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 557 lane vm_g5_b4_xf0>p19"); end end end
    reg [23:0] ref558=0;
    always @(posedge clk) if (lane_me_prev) ref558 <= {ref558[15:0], d_e[1024 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref558[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2192 +: 8] !== ref558[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 558 lane vm_g7_b5_xf0>p1"); end end end
    reg [23:0] ref559=0;
    always @(posedge clk) if (lane_me_prev) ref559 <= {ref559[15:0], d_e[1032 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref559[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2200 +: 8] !== ref559[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 559 lane vm_g7_b5_xf0>p11"); end end end
    reg [23:0] ref560=0;
    always @(posedge clk) if (lane_me_prev) ref560 <= {ref560[15:0], d_e[1040 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref560[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2208 +: 8] !== ref560[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 560 lane vm_g7_b1_xf0>p11"); end end end
    reg [23:0] ref561=0;
    always @(posedge clk) if (lane_me_prev) ref561 <= {ref561[15:0], d_e[1048 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref561[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2216 +: 8] !== ref561[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 561 lane vm_g7_b0_xf1>p11"); end end end
    reg [71:0] ref562=0;
    always @(posedge clk) if (lane_me_prev) ref562 <= {ref562[63:0], r_xo[3416 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref562[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2224 +: 8] !== ref562[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 562 lane vm_g6_b6_xf1>p11"); end end end
    reg [79:0] ref563=0;
    always @(posedge clk) if (lane_me_prev) ref563 <= {ref563[71:0], r_xo[2648 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref563[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2232 +: 8] !== ref563[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 563 lane vm_g6_b5_xf0>p11"); end end end
    reg [71:0] ref564=0;
    always @(posedge clk) if (lane_me_prev) ref564 <= {ref564[63:0], r_xo[600 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref564[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2240 +: 8] !== ref564[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 564 lane vm_g6_b1_xf0>p11"); end end end
    reg [15:0] ref565=0;
    always @(posedge clk) if (lane_me_prev) ref565 <= {ref565[7:0], d_w[2272 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref565[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1352 +: 8] !== ref565[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 565 lane vm_g5_b6_xf0>p22"); end end end
    reg [79:0] ref566=0;
    always @(posedge clk) if (lane_me_prev) ref566 <= {ref566[71:0], d_w[2280 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref566[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1360 +: 8] !== ref566[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 566 lane vm_g5_b6_xf0>p20"); end end end
    reg [71:0] ref567=0;
    always @(posedge clk) if (lane_me_prev) ref567 <= {ref567[63:0], d_w[2288 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref567[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1368 +: 8] !== ref567[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 567 lane vm_g5_b6_xf0>p19"); end end end
    reg [23:0] ref568=0;
    always @(posedge clk) if (lane_me_prev) ref568 <= {ref568[15:0], d_e[1056 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref568[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2248 +: 8] !== ref568[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 568 lane vm_g7_b7_xf0>p11"); end end end
    reg [63:0] ref569=0;
    always @(posedge clk) if (lane_me_prev) ref569 <= {ref569[55:0], d_e[1064 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref569[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2256 +: 8] !== ref569[56 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 569 lane vm_g7_b3_xf0>p11"); end end end
    reg [15:0] ref570=0;
    always @(posedge clk) if (lane_me_prev) ref570 <= {ref570[7:0], r_xo[2904 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref570[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2264 +: 8] !== ref570[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 570 lane vm_g6_b5_xf1>p11"); end end end
    reg [71:0] ref571=0;
    always @(posedge clk) if (lane_me_prev) ref571 <= {ref571[63:0], r_xo[1624 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref571[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2272 +: 8] !== ref571[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 571 lane vm_g6_b3_xf0>p11"); end end end
    reg [79:0] ref572=0;
    always @(posedge clk) if (lane_me_prev) ref572 <= {ref572[71:0], r_xo[344 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref572[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2280 +: 8] !== ref572[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 572 lane vm_g6_b0_xf1>p11"); end end end
    reg [15:0] ref573=0;
    always @(posedge clk) if (lane_me_prev) ref573 <= {ref573[7:0], r_xo[1136 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref573[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2288 +: 8] !== ref573[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 573 lane vm_g6_b2_xf0>p14"); end end end
    reg [15:0] ref574=0;
    always @(posedge clk) if (lane_me_prev) ref574 <= {ref574[7:0], d_w[2296 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref574[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1376 +: 8] !== ref574[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 574 lane vm_g5_b6_xf1>p22"); end end end
    reg [15:0] ref575=0;
    always @(posedge clk) if (lane_me_prev) ref575 <= {ref575[7:0], r_xo[3176 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref575[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2296 +: 8] !== ref575[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 575 lane vm_g6_b6_xf0>p13"); end end end
    reg [23:0] ref576=0;
    always @(posedge clk) if (lane_me_prev) ref576 <= {ref576[15:0], d_w[2304 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref576[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1384 +: 8] !== ref576[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 576 lane vm_g5_b4_xf1>p23"); end end end
    reg [15:0] ref577=0;
    always @(posedge clk) if (lane_me_prev) ref577 <= {ref577[7:0], r_xo[2920 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref577[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2304 +: 8] !== ref577[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 577 lane vm_g6_b5_xf1>p13"); end end end
    reg [23:0] ref578=0;
    always @(posedge clk) if (lane_me_prev) ref578 <= {ref578[15:0], d_w[2312 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref578[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1392 +: 8] !== ref578[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 578 lane vm_g5_b6_xf1>p28"); end end end
    reg [23:0] ref579=0;
    always @(posedge clk) if (lane_me_prev) ref579 <= {ref579[15:0], d_w[2320 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref579[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1400 +: 8] !== ref579[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 579 lane vm_g5_b6_xf0>p28"); end end end
    reg [15:0] ref580=0;
    always @(posedge clk) if (lane_me_prev) ref580 <= {ref580[7:0], d_w[2328 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref580[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1408 +: 8] !== ref580[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 580 lane vm_g5_b6_xf1>p19"); end end end
    reg [23:0] ref581=0;
    always @(posedge clk) if (lane_me_prev) ref581 <= {ref581[15:0], d_e[1072 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref581[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2312 +: 8] !== ref581[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 581 lane vm_g7_b7_xf1>p11"); end end end
    reg [31:0] ref582=0;
    always @(posedge clk) if (lane_me_prev) ref582 <= {ref582[23:0], d_e[1080 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref582[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2320 +: 8] !== ref582[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 582 lane vm_g7_b6_xf1>p11"); end end end
    reg [55:0] ref583=0;
    always @(posedge clk) if (lane_me_prev) ref583 <= {ref583[47:0], d_e[1088 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref583[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2328 +: 8] !== ref583[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 583 lane vm_g7_b6_xf0>p11"); end end end
    reg [63:0] ref584=0;
    always @(posedge clk) if (lane_me_prev) ref584 <= {ref584[55:0], d_e[1096 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref584[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2336 +: 8] !== ref584[56 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 584 lane vm_g7_b5_xf1>p11"); end end end
    reg [23:0] ref585=0;
    always @(posedge clk) if (lane_me_prev) ref585 <= {ref585[15:0], d_e[1104 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref585[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2344 +: 8] !== ref585[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 585 lane vm_g7_b3_xf1>p11"); end end end
    reg [23:0] ref586=0;
    always @(posedge clk) if (lane_me_prev) ref586 <= {ref586[15:0], d_e[1112 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref586[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2352 +: 8] !== ref586[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 586 lane vm_g7_b2_xf1>p11"); end end end
    reg [71:0] ref587=0;
    always @(posedge clk) if (lane_me_prev) ref587 <= {ref587[63:0], d_e[1120 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref587[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2360 +: 8] !== ref587[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 587 lane vm_g7_b2_xf0>p11"); end end end
    reg [71:0] ref588=0;
    always @(posedge clk) if (lane_me_prev) ref588 <= {ref588[63:0], d_e[1128 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref588[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2368 +: 8] !== ref588[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 588 lane vm_g7_b1_xf1>p11"); end end end
    reg [71:0] ref589=0;
    always @(posedge clk) if (lane_me_prev) ref589 <= {ref589[63:0], r_xo[3928 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref589[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2376 +: 8] !== ref589[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 589 lane vm_g6_b7_xf1>p11"); end end end
    reg [71:0] ref590=0;
    always @(posedge clk) if (lane_me_prev) ref590 <= {ref590[63:0], r_xo[3672 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref590[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2384 +: 8] !== ref590[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 590 lane vm_g6_b7_xf0>p11"); end end end
    reg [71:0] ref591=0;
    always @(posedge clk) if (lane_me_prev) ref591 <= {ref591[63:0], r_xo[1880 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref591[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2392 +: 8] !== ref591[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 591 lane vm_g6_b3_xf1>p11"); end end end
    reg [79:0] ref592=0;
    always @(posedge clk) if (lane_me_prev) ref592 <= {ref592[71:0], r_xo[3160 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref592[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2400 +: 8] !== ref592[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 592 lane vm_g6_b6_xf0>p11"); end end end
    reg [79:0] ref593=0;
    always @(posedge clk) if (lane_me_prev) ref593 <= {ref593[71:0], r_xo[1368 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref593[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2408 +: 8] !== ref593[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 593 lane vm_g6_b2_xf1>p11"); end end end
    reg [79:0] ref594=0;
    always @(posedge clk) if (lane_me_prev) ref594 <= {ref594[71:0], r_xo[856 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref594[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2416 +: 8] !== ref594[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 594 lane vm_g6_b1_xf1>p11"); end end end
    reg [79:0] ref595=0;
    always @(posedge clk) if (lane_me_prev) ref595 <= {ref595[71:0], r_xo[1112 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref595[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2424 +: 8] !== ref595[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 595 lane vm_g6_b2_xf0>p11"); end end end
    reg [79:0] ref596=0;
    always @(posedge clk) if (lane_me_prev) ref596 <= {ref596[71:0], d_w[2336 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref596[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1416 +: 8] !== ref596[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 596 lane vm_g5_b7_xf0>p16"); end end end
    reg [23:0] ref597=0;
    always @(posedge clk) if (lane_me_prev) ref597 <= {ref597[15:0], d_w[2344 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref597[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[920 +: 8] !== ref597[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 597 lane vm_g5_b6_xf0>p30"); end end end
    reg [15:0] ref598=0;
    always @(posedge clk) if (lane_me_prev) ref598 <= {ref598[7:0], d_w[2352 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref598[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1424 +: 8] !== ref598[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 598 lane vm_g5_b7_xf0>p21"); end end end
    reg [15:0] ref599=0;
    always @(posedge clk) if (lane_me_prev) ref599 <= {ref599[7:0], d_w[2360 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref599[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1432 +: 8] !== ref599[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 599 lane vm_g5_b6_xf1>p21"); end end end
    reg [15:0] ref600=0;
    always @(posedge clk) if (lane_me_prev) ref600 <= {ref600[7:0], d_w[2368 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref600[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1440 +: 8] !== ref600[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 600 lane vm_g5_b6_xf0>p21"); end end end
    reg [15:0] ref601=0;
    always @(posedge clk) if (lane_me_prev) ref601 <= {ref601[7:0], d_w[2376 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref601[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1448 +: 8] !== ref601[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 601 lane vm_g5_b7_xf0>p17"); end end end
    reg [15:0] ref602=0;
    always @(posedge clk) if (lane_me_prev) ref602 <= {ref602[7:0], d_w[2384 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref602[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1456 +: 8] !== ref602[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 602 lane vm_g5_b6_xf1>p17"); end end end
    reg [15:0] ref603=0;
    always @(posedge clk) if (lane_me_prev) ref603 <= {ref603[7:0], d_w[2392 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref603[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1464 +: 8] !== ref603[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 603 lane vm_g5_b6_xf0>p17"); end end end
    reg [15:0] ref604=0;
    always @(posedge clk) if (lane_me_prev) ref604 <= {ref604[7:0], d_w[2400 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref604[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1472 +: 8] !== ref604[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 604 lane vm_g5_b7_xf0>p18"); end end end
    reg [7:0] ref605=0;
    always @(posedge clk) if (lane_me_prev) ref605 <= d_w[2408 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref605[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1480 +: 8] !== ref605[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 605 lane vm_g5_b6_xf1>p18"); end end end
    reg [7:0] ref606=0;
    always @(posedge clk) if (lane_me_prev) ref606 <= d_w[2416 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref606[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1488 +: 8] !== ref606[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 606 lane vm_g5_b6_xf0>p18"); end end end
    reg [31:0] ref607=0;
    always @(posedge clk) if (lane_me_prev) ref607 <= {ref607[23:0], d_w[2424 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref607[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[928 +: 8] !== ref607[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 607 lane vm_g5_b6_xf1>p29"); end end end
    reg [23:0] ref608=0;
    always @(posedge clk) if (lane_me_prev) ref608 <= {ref608[15:0], d_w[2432 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref608[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[936 +: 8] !== ref608[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 608 lane vm_g5_b6_xf1>p26"); end end end
    reg [79:0] ref609=0;
    always @(posedge clk) if (lane_me_prev) ref609 <= {ref609[71:0], d_w[2440 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref609[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1496 +: 8] !== ref609[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 609 lane vm_g5_b7_xf1>p20"); end end end
    reg [79:0] ref610=0;
    always @(posedge clk) if (lane_me_prev) ref610 <= {ref610[71:0], d_w[2448 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref610[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1504 +: 8] !== ref610[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 610 lane vm_g5_b7_xf0>p20"); end end end
    reg [79:0] ref611=0;
    always @(posedge clk) if (lane_me_prev) ref611 <= {ref611[71:0], d_w[2456 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref611[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1512 +: 8] !== ref611[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 611 lane vm_g5_b6_xf1>p20"); end end end
    reg [55:0] ref612=0;
    always @(posedge clk) if (lane_me_prev) ref612 <= {ref612[47:0], d_w[2464 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref612[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[944 +: 8] !== ref612[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 612 lane vm_g5_b5_xf1>p30"); end end end
    reg [55:0] ref613=0;
    always @(posedge clk) if (lane_me_prev) ref613 <= {ref613[47:0], d_w[2472 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref613[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[952 +: 8] !== ref613[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 613 lane vm_g5_b6_xf1>p27"); end end end
    reg [79:0] ref614=0;
    always @(posedge clk) if (lane_me_prev) ref614 <= {ref614[71:0], d_w[2480 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref614[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1520 +: 8] !== ref614[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 614 lane vm_g5_b7_xf1>p25"); end end end
    reg [55:0] ref615=0;
    always @(posedge clk) if (lane_me_prev) ref615 <= {ref615[47:0], d_w[2488 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref615[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[960 +: 8] !== ref615[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 615 lane vm_g5_b6_xf0>p27"); end end end
    reg [55:0] ref616=0;
    always @(posedge clk) if (lane_me_prev) ref616 <= {ref616[47:0], d_w[2496 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref616[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[968 +: 8] !== ref616[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 616 lane vm_g5_b5_xf1>p27"); end end end
    reg [31:0] ref617=0;
    always @(posedge clk) if (lane_me_prev) ref617 <= {ref617[23:0], d_w[2504 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref617[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1528 +: 8] !== ref617[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 617 lane vm_g5_b7_xf0>p25"); end end end
    reg [79:0] ref618=0;
    always @(posedge clk) if (lane_me_prev) ref618 <= {ref618[71:0], d_w[2512 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref618[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1536 +: 8] !== ref618[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 618 lane vm_g5_b6_xf1>p25"); end end end
    reg [63:0] ref619=0;
    always @(posedge clk) if (lane_me_prev) ref619 <= {ref619[55:0], d_w[2520 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref619[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[976 +: 8] !== ref619[56 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 619 lane vm_g5_b5_xf1>p26"); end end end
    reg [79:0] ref620=0;
    always @(posedge clk) if (lane_me_prev) ref620 <= {ref620[71:0], d_w[2528 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref620[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1544 +: 8] !== ref620[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 620 lane vm_g5_b6_xf0>p25"); end end end
    reg [31:0] ref621=0;
    always @(posedge clk) if (lane_me_prev) ref621 <= {ref621[23:0], d_w[2536 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref621[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1552 +: 8] !== ref621[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 621 lane vm_g5_b5_xf1>p25"); end end end
    reg [79:0] ref622=0;
    always @(posedge clk) if (lane_me_prev) ref622 <= {ref622[71:0], d_w[2544 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref622[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1560 +: 8] !== ref622[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 622 lane vm_g5_b6_xf1>p23"); end end end
    reg [79:0] ref623=0;
    always @(posedge clk) if (lane_me_prev) ref623 <= {ref623[71:0], d_w[2552 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref623[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1568 +: 8] !== ref623[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 623 lane vm_g5_b5_xf1>p24"); end end end
    reg [79:0] ref624=0;
    always @(posedge clk) if (lane_me_prev) ref624 <= {ref624[71:0], d_w[2560 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref624[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1576 +: 8] !== ref624[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 624 lane vm_g5_b5_xf1>p23"); end end end
    reg [23:0] ref625=0;
    always @(posedge clk) if (lane_me_prev) ref625 <= {ref625[15:0], d_w[2568 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref625[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[984 +: 8] !== ref625[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 625 lane vm_g5_b7_xf0>p30"); end end end
    reg [23:0] ref626=0;
    always @(posedge clk) if (lane_me_prev) ref626 <= {ref626[15:0], d_w[2576 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref626[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[992 +: 8] !== ref626[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 626 lane vm_g5_b6_xf1>p30"); end end end
    reg [31:0] ref627=0;
    always @(posedge clk) if (lane_me_prev) ref627 <= {ref627[23:0], d_w[2584 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref627[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1000 +: 8] !== ref627[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 627 lane vm_g5_b7_xf0>p28"); end end end
    reg [31:0] ref628=0;
    always @(posedge clk) if (lane_me_prev) ref628 <= {ref628[23:0], d_w[2592 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref628[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1584 +: 8] !== ref628[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 628 lane vm_g5_b7_xf1>p22"); end end end
    reg [31:0] ref629=0;
    always @(posedge clk) if (lane_me_prev) ref629 <= {ref629[23:0], d_w[2600 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref629[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1592 +: 8] !== ref629[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 629 lane vm_g5_b7_xf0>p22"); end end end
    reg [31:0] ref630=0;
    always @(posedge clk) if (lane_me_prev) ref630 <= {ref630[23:0], d_w[2608 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref630[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1600 +: 8] !== ref630[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 630 lane vm_g5_b7_xf1>p21"); end end end
    reg [15:0] ref631=0;
    always @(posedge clk) if (lane_me_prev) ref631 <= {ref631[7:0], d_w[2616 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref631[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1608 +: 8] !== ref631[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 631 lane vm_g5_b7_xf1>p19"); end end end
    reg [15:0] ref632=0;
    always @(posedge clk) if (lane_me_prev) ref632 <= {ref632[7:0], d_w[2624 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref632[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1616 +: 8] !== ref632[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 632 lane vm_g5_b7_xf0>p19"); end end end
    reg [55:0] ref633=0;
    always @(posedge clk) if (lane_me_prev) ref633 <= {ref633[47:0], d_w[2632 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref633[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1008 +: 8] !== ref633[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 633 lane vm_g5_b7_xf1>p30"); end end end
    reg [23:0] ref634=0;
    always @(posedge clk) if (lane_me_prev) ref634 <= {ref634[15:0], d_w[2640 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref634[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1016 +: 8] !== ref634[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 634 lane vm_g5_b7_xf1>p29"); end end end
    reg [23:0] ref635=0;
    always @(posedge clk) if (lane_me_prev) ref635 <= {ref635[15:0], d_w[2648 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref635[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1024 +: 8] !== ref635[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 635 lane vm_g5_b7_xf0>p29"); end end end
    reg [31:0] ref636=0;
    always @(posedge clk) if (lane_me_prev) ref636 <= {ref636[23:0], d_w[2656 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref636[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1032 +: 8] !== ref636[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 636 lane vm_g5_b7_xf1>p27"); end end end
    reg [23:0] ref637=0;
    always @(posedge clk) if (lane_me_prev) ref637 <= {ref637[15:0], d_w[2664 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref637[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1040 +: 8] !== ref637[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 637 lane vm_g5_b6_xf0>p29"); end end end
    reg [63:0] ref638=0;
    always @(posedge clk) if (lane_me_prev) ref638 <= {ref638[55:0], d_w[2672 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref638[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1048 +: 8] !== ref638[56 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 638 lane vm_g5_b7_xf0>p27"); end end end
    reg [79:0] ref639=0;
    always @(posedge clk) if (lane_me_prev) ref639 <= {ref639[71:0], d_w[2680 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref639[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1624 +: 8] !== ref639[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 639 lane vm_g5_b7_xf1>p24"); end end end
    reg [63:0] ref640=0;
    always @(posedge clk) if (lane_me_prev) ref640 <= {ref640[55:0], d_w[2688 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref640[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1056 +: 8] !== ref640[56 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 640 lane vm_g5_b6_xf0>p26"); end end end
    reg [79:0] ref641=0;
    always @(posedge clk) if (lane_me_prev) ref641 <= {ref641[71:0], d_w[2696 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref641[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1632 +: 8] !== ref641[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 641 lane vm_g5_b7_xf0>p24"); end end end
    reg [79:0] ref642=0;
    always @(posedge clk) if (lane_me_prev) ref642 <= {ref642[71:0], d_w[2704 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref642[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1640 +: 8] !== ref642[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 642 lane vm_g5_b6_xf1>p24"); end end end
    reg [79:0] ref643=0;
    always @(posedge clk) if (lane_me_prev) ref643 <= {ref643[71:0], d_w[2712 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref643[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1648 +: 8] !== ref643[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 643 lane vm_g5_b7_xf0>p23"); end end end
    reg [31:0] ref644=0;
    always @(posedge clk) if (lane_me_prev) ref644 <= {ref644[23:0], d_w[2720 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref644[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1656 +: 8] !== ref644[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 644 lane vm_g5_b6_xf0>p24"); end end end
    reg [79:0] ref645=0;
    always @(posedge clk) if (lane_me_prev) ref645 <= {ref645[71:0], d_w[2728 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref645[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1664 +: 8] !== ref645[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 645 lane vm_g5_b6_xf0>p23"); end end end
    reg [39:0] ref646=0;
    always @(posedge clk) if (lane_me_prev) ref646 <= {ref646[31:0], d_w[2736 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref646[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1064 +: 8] !== ref646[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 646 lane vm_g5_b6_xf0>p31"); end end end
    reg [63:0] ref647=0;
    always @(posedge clk) if (lane_me_prev) ref647 <= {ref647[55:0], d_w[2744 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref647[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1072 +: 8] !== ref647[56 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 647 lane vm_g5_b7_xf1>p26"); end end end
    reg [31:0] ref648=0;
    always @(posedge clk) if (lane_me_prev) ref648 <= {ref648[23:0], d_w[2752 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref648[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1080 +: 8] !== ref648[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 648 lane vm_g5_b7_xf0>p26"); end end end
    reg [31:0] ref649=0;
    always @(posedge clk) if (lane_me_prev) ref649 <= {ref649[23:0], d_w[2760 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref649[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1672 +: 8] !== ref649[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 649 lane vm_g5_b7_xf1>p23"); end end end
    reg [39:0] ref650=0;
    always @(posedge clk) if (lane_me_prev) ref650 <= {ref650[31:0], d_w[2768 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref650[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1088 +: 8] !== ref650[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 650 lane vm_g5_b6_xf1>p31"); end end end
    reg [79:0] ref651=0;
    always @(posedge clk) if (lane_me_prev) ref651 <= {ref651[71:0], d_w[2776 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref651[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1680 +: 8] !== ref651[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 651 lane vm_g5_b7_xf1>p18"); end end end
    reg [39:0] ref652=0;
    always @(posedge clk) if (lane_me_prev) ref652 <= {ref652[31:0], d_w[2784 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref652[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1096 +: 8] !== ref652[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 652 lane vm_g5_b7_xf1>p31"); end end end
    reg [23:0] ref653=0;
    always @(posedge clk) if (lane_me_prev) ref653 <= {ref653[15:0], d_w[2792 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref653[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1104 +: 8] !== ref653[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 653 lane vm_g5_b7_xf0>p31"); end end end
    reg [23:0] ref654=0;
    always @(posedge clk) if (lane_me_prev) ref654 <= {ref654[15:0], d_w[2800 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref654[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1112 +: 8] !== ref654[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 654 lane vm_g5_b7_xf1>p28"); end end end
    reg [87:0] ref655=0;
    always @(posedge clk) if (lane_me_prev) ref655 <= {ref655[79:0], r_xo[656 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref655[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1688 +: 8] !== ref655[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 655 lane vm_g6_b1_xf0>p18"); end end end
    reg [7:0] ref656=0;
    always @(posedge clk) if (lane_me_prev) ref656 <= r_xo[424 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref656[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1696 +: 8] !== ref656[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 656 lane vm_g6_b0_xf1>p21"); end end end
    reg [7:0] ref657=0;
    always @(posedge clk) if (lane_me_prev) ref657 <= r_xo[168 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref657[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1704 +: 8] !== ref657[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 657 lane vm_g6_b0_xf0>p21"); end end end
    reg [7:0] ref658=0;
    always @(posedge clk) if (lane_me_prev) ref658 <= r_xo[416 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref658[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1712 +: 8] !== ref658[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 658 lane vm_g6_b0_xf1>p20"); end end end
    reg [7:0] ref659=0;
    always @(posedge clk) if (lane_me_prev) ref659 <= r_xo[160 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref659[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1720 +: 8] !== ref659[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 659 lane vm_g6_b0_xf0>p20"); end end end
    reg [87:0] ref660=0;
    always @(posedge clk) if (lane_me_prev) ref660 <= {ref660[79:0], r_xo[408 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref660[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1728 +: 8] !== ref660[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 660 lane vm_g6_b0_xf1>p19"); end end end
    reg [87:0] ref661=0;
    always @(posedge clk) if (lane_me_prev) ref661 <= {ref661[79:0], r_xo[152 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref661[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1736 +: 8] !== ref661[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 661 lane vm_g6_b0_xf0>p19"); end end end
    reg [7:0] ref662=0;
    always @(posedge clk) if (lane_me_prev) ref662 <= r_xo[144 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref662[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1744 +: 8] !== ref662[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 662 lane vm_g6_b0_xf0>p18"); end end end
    reg [23:0] ref663=0;
    always @(posedge clk) if (lane_me_prev) ref663 <= {ref663[15:0], r_xo[3192 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref663[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1752 +: 8] !== ref663[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 663 lane vm_g6_b6_xf0>p15"); end end end
    reg [87:0] ref664=0;
    always @(posedge clk) if (lane_me_prev) ref664 <= {ref664[79:0], r_xo[3208 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref664[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1760 +: 8] !== ref664[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 664 lane vm_g6_b6_xf0>p17"); end end end
    reg [87:0] ref665=0;
    always @(posedge clk) if (lane_me_prev) ref665 <= {ref665[79:0], r_xo[648 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref665[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1768 +: 8] !== ref665[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 665 lane vm_g6_b1_xf0>p17"); end end end
    reg [87:0] ref666=0;
    always @(posedge clk) if (lane_me_prev) ref666 <= {ref666[79:0], r_xo[392 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref666[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1776 +: 8] !== ref666[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 666 lane vm_g6_b0_xf1>p17"); end end end
    reg [87:0] ref667=0;
    always @(posedge clk) if (lane_me_prev) ref667 <= {ref667[79:0], r_xo[136 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref667[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1784 +: 8] !== ref667[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 667 lane vm_g6_b0_xf0>p17"); end end end
    reg [39:0] ref668=0;
    always @(posedge clk) if (lane_me_prev) ref668 <= {ref668[31:0], r_xo[2048 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref668[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1792 +: 8] !== ref668[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 668 lane vm_g6_b4_xf0>p0"); end end end
    reg [7:0] ref669=0;
    always @(posedge clk) if (lane_me_prev) ref669 <= r_xo[2056 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref669[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1800 +: 8] !== ref669[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 669 lane vm_g6_b4_xf0>p1"); end end end
    reg [7:0] ref670=0;
    always @(posedge clk) if (lane_me_prev) ref670 <= r_xo[2064 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref670[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1808 +: 8] !== ref670[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 670 lane vm_g6_b4_xf0>p2"); end end end
    reg [7:0] ref671=0;
    always @(posedge clk) if (lane_me_prev) ref671 <= r_xo[2072 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref671[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1816 +: 8] !== ref671[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 671 lane vm_g6_b4_xf0>p3"); end end end
    reg [7:0] ref672=0;
    always @(posedge clk) if (lane_me_prev) ref672 <= r_xo[2080 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref672[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1824 +: 8] !== ref672[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 672 lane vm_g6_b4_xf0>p4"); end end end
    reg [7:0] ref673=0;
    always @(posedge clk) if (lane_me_prev) ref673 <= r_xo[2088 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref673[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1832 +: 8] !== ref673[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 673 lane vm_g6_b4_xf0>p5"); end end end
    reg [15:0] ref674=0;
    always @(posedge clk) if (lane_me_prev) ref674 <= {ref674[7:0], r_xo[2096 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref674[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1840 +: 8] !== ref674[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 674 lane vm_g6_b4_xf0>p6"); end end end
    reg [15:0] ref675=0;
    always @(posedge clk) if (lane_me_prev) ref675 <= {ref675[7:0], r_xo[760 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref675[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1848 +: 8] !== ref675[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 675 lane vm_g6_b1_xf0>p31"); end end end
    reg [15:0] ref676=0;
    always @(posedge clk) if (lane_me_prev) ref676 <= {ref676[7:0], r_xo[2104 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref676[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1856 +: 8] !== ref676[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 676 lane vm_g6_b4_xf0>p7"); end end end
    reg [15:0] ref677=0;
    always @(posedge clk) if (lane_me_prev) ref677 <= {ref677[7:0], r_xo[504 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref677[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1864 +: 8] !== ref677[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 677 lane vm_g6_b0_xf1>p31"); end end end
    reg [15:0] ref678=0;
    always @(posedge clk) if (lane_me_prev) ref678 <= {ref678[7:0], r_xo[752 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref678[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1872 +: 8] !== ref678[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 678 lane vm_g6_b1_xf0>p30"); end end end
    reg [55:0] ref679=0;
    always @(posedge clk) if (lane_me_prev) ref679 <= {ref679[47:0], r_xo[2112 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref679[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1880 +: 8] !== ref679[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 679 lane vm_g6_b4_xf0>p8"); end end end
    reg [7:0] ref680=0;
    always @(posedge clk) if (lane_me_prev) ref680 <= r_xo[248 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref680[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1888 +: 8] !== ref680[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 680 lane vm_g6_b0_xf0>p31"); end end end
    reg [55:0] ref681=0;
    always @(posedge clk) if (lane_me_prev) ref681 <= {ref681[47:0], r_xo[240 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref681[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1896 +: 8] !== ref681[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 681 lane vm_g6_b0_xf0>p30"); end end end
    reg [71:0] ref682=0;
    always @(posedge clk) if (lane_me_prev) ref682 <= {ref682[63:0], r_xo[744 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref682[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1904 +: 8] !== ref682[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 682 lane vm_g6_b1_xf0>p29"); end end end
    reg [71:0] ref683=0;
    always @(posedge clk) if (lane_me_prev) ref683 <= {ref683[63:0], r_xo[2120 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref683[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1912 +: 8] !== ref683[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 683 lane vm_g6_b4_xf0>p9"); end end end
    reg [7:0] ref684=0;
    always @(posedge clk) if (lane_me_prev) ref684 <= r_xo[488 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref684[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1920 +: 8] !== ref684[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 684 lane vm_g6_b0_xf1>p29"); end end end
    reg [55:0] ref685=0;
    always @(posedge clk) if (lane_me_prev) ref685 <= {ref685[47:0], r_xo[736 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref685[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1928 +: 8] !== ref685[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 685 lane vm_g6_b1_xf0>p28"); end end end
    reg [71:0] ref686=0;
    always @(posedge clk) if (lane_me_prev) ref686 <= {ref686[63:0], r_xo[2128 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref686[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1936 +: 8] !== ref686[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 686 lane vm_g6_b4_xf0>p10"); end end end
    reg [71:0] ref687=0;
    always @(posedge clk) if (lane_me_prev) ref687 <= {ref687[63:0], r_xo[232 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref687[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1944 +: 8] !== ref687[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 687 lane vm_g6_b0_xf0>p29"); end end end
    reg [71:0] ref688=0;
    always @(posedge clk) if (lane_me_prev) ref688 <= {ref688[63:0], r_xo[2136 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref688[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1952 +: 8] !== ref688[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 688 lane vm_g6_b4_xf0>p11"); end end end
    reg [15:0] ref689=0;
    always @(posedge clk) if (lane_me_prev) ref689 <= {ref689[7:0], r_xo[720 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref689[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1960 +: 8] !== ref689[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 689 lane vm_g6_b1_xf0>p26"); end end end
    reg [79:0] ref690=0;
    always @(posedge clk) if (lane_me_prev) ref690 <= {ref690[71:0], r_xo[2144 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref690[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1968 +: 8] !== ref690[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 690 lane vm_g6_b4_xf0>p12"); end end end
    reg [79:0] ref691=0;
    always @(posedge clk) if (lane_me_prev) ref691 <= {ref691[71:0], r_xo[464 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref691[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1976 +: 8] !== ref691[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 691 lane vm_g6_b0_xf1>p26"); end end end
    reg [79:0] ref692=0;
    always @(posedge clk) if (lane_me_prev) ref692 <= {ref692[71:0], r_xo[712 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref692[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1984 +: 8] !== ref692[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 692 lane vm_g6_b1_xf0>p25"); end end end
    reg [79:0] ref693=0;
    always @(posedge clk) if (lane_me_prev) ref693 <= {ref693[71:0], r_xo[2152 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref693[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[1992 +: 8] !== ref693[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 693 lane vm_g6_b4_xf0>p13"); end end end
    reg [15:0] ref694=0;
    always @(posedge clk) if (lane_me_prev) ref694 <= {ref694[7:0], r_xo[208 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref694[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2000 +: 8] !== ref694[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 694 lane vm_g6_b0_xf0>p26"); end end end
    reg [79:0] ref695=0;
    always @(posedge clk) if (lane_me_prev) ref695 <= {ref695[71:0], r_xo[2160 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref695[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2008 +: 8] !== ref695[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 695 lane vm_g6_b4_xf0>p14"); end end end
    reg [87:0] ref696=0;
    always @(posedge clk) if (lane_me_prev) ref696 <= {ref696[79:0], r_xo[696 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref696[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2016 +: 8] !== ref696[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 696 lane vm_g6_b1_xf0>p23"); end end end
    reg [87:0] ref697=0;
    always @(posedge clk) if (lane_me_prev) ref697 <= {ref697[79:0], r_xo[2168 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref697[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2024 +: 8] !== ref697[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 697 lane vm_g6_b4_xf0>p15"); end end end
    reg [87:0] ref698=0;
    always @(posedge clk) if (lane_me_prev) ref698 <= {ref698[79:0], r_xo[440 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref698[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2032 +: 8] !== ref698[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 698 lane vm_g6_b0_xf1>p23"); end end end
    reg [87:0] ref699=0;
    always @(posedge clk) if (lane_me_prev) ref699 <= {ref699[79:0], r_xo[2176 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref699[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2040 +: 8] !== ref699[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 699 lane vm_g6_b4_xf0>p16"); end end end
    reg [87:0] ref700=0;
    always @(posedge clk) if (lane_me_prev) ref700 <= {ref700[79:0], r_xo[184 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref700[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2048 +: 8] !== ref700[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 700 lane vm_g6_b0_xf0>p23"); end end end
    reg [87:0] ref701=0;
    always @(posedge clk) if (lane_me_prev) ref701 <= {ref701[79:0], r_xo[2184 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref701[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2056 +: 8] !== ref701[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 701 lane vm_g6_b4_xf0>p17"); end end end
    reg [87:0] ref702=0;
    always @(posedge clk) if (lane_me_prev) ref702 <= {ref702[79:0], r_xo[2192 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref702[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2064 +: 8] !== ref702[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 702 lane vm_g6_b4_xf0>p18"); end end end
    reg [87:0] ref703=0;
    always @(posedge clk) if (lane_me_prev) ref703 <= {ref703[79:0], r_xo[1944 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref703[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2072 +: 8] !== ref703[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 703 lane vm_g6_b3_xf1>p19"); end end end
    reg [87:0] ref704=0;
    always @(posedge clk) if (lane_me_prev) ref704 <= {ref704[79:0], r_xo[3480 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref704[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2080 +: 8] !== ref704[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 704 lane vm_g6_b6_xf1>p19"); end end end
    reg [87:0] ref705=0;
    always @(posedge clk) if (lane_me_prev) ref705 <= {ref705[79:0], r_xo[1688 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref705[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2088 +: 8] !== ref705[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 705 lane vm_g6_b3_xf0>p19"); end end end
    reg [87:0] ref706=0;
    always @(posedge clk) if (lane_me_prev) ref706 <= {ref706[79:0], r_xo[920 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref706[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2096 +: 8] !== ref706[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 706 lane vm_g6_b1_xf1>p19"); end end end
    reg [87:0] ref707=0;
    always @(posedge clk) if (lane_me_prev) ref707 <= {ref707[79:0], r_xo[664 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref707[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2104 +: 8] !== ref707[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 707 lane vm_g6_b1_xf0>p19"); end end end
    reg [23:0] ref708=0;
    always @(posedge clk) if (lane_me_prev) ref708 <= {ref708[15:0], r_xo[1712 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref708[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2112 +: 8] !== ref708[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 708 lane vm_g6_b3_xf0>p22"); end end end
    reg [23:0] ref709=0;
    always @(posedge clk) if (lane_me_prev) ref709 <= {ref709[15:0], r_xo[1456 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref709[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2120 +: 8] !== ref709[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 709 lane vm_g6_b2_xf1>p22"); end end end
    reg [23:0] ref710=0;
    always @(posedge clk) if (lane_me_prev) ref710 <= {ref710[15:0], r_xo[1704 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref710[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2128 +: 8] !== ref710[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 710 lane vm_g6_b3_xf0>p21"); end end end
    reg [87:0] ref711=0;
    always @(posedge clk) if (lane_me_prev) ref711 <= {ref711[79:0], r_xo[1952 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref711[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2136 +: 8] !== ref711[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 711 lane vm_g6_b3_xf1>p20"); end end end
    reg [87:0] ref712=0;
    always @(posedge clk) if (lane_me_prev) ref712 <= {ref712[79:0], r_xo[1696 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref712[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2144 +: 8] !== ref712[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 712 lane vm_g6_b3_xf0>p20"); end end end
    reg [7:0] ref713=0;
    always @(posedge clk) if (lane_me_prev) ref713 <= r_xo[944 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref713[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2152 +: 8] !== ref713[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 713 lane vm_g6_b1_xf1>p22"); end end end
    reg [7:0] ref714=0;
    always @(posedge clk) if (lane_me_prev) ref714 <= r_xo[688 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref714[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2160 +: 8] !== ref714[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 714 lane vm_g6_b1_xf0>p22"); end end end
    reg [7:0] ref715=0;
    always @(posedge clk) if (lane_me_prev) ref715 <= r_xo[936 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref715[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2168 +: 8] !== ref715[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 715 lane vm_g6_b1_xf1>p21"); end end end
    reg [7:0] ref716=0;
    always @(posedge clk) if (lane_me_prev) ref716 <= r_xo[432 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref716[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2176 +: 8] !== ref716[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 716 lane vm_g6_b0_xf1>p22"); end end end
    reg [7:0] ref717=0;
    always @(posedge clk) if (lane_me_prev) ref717 <= r_xo[680 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref717[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2184 +: 8] !== ref717[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 717 lane vm_g6_b1_xf0>p21"); end end end
    reg [87:0] ref718=0;
    always @(posedge clk) if (lane_me_prev) ref718 <= {ref718[79:0], r_xo[928 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref718[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2192 +: 8] !== ref718[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 718 lane vm_g6_b1_xf1>p20"); end end end
    reg [7:0] ref719=0;
    always @(posedge clk) if (lane_me_prev) ref719 <= r_xo[176 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref719[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2200 +: 8] !== ref719[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 719 lane vm_g6_b0_xf0>p22"); end end end
    reg [7:0] ref720=0;
    always @(posedge clk) if (lane_me_prev) ref720 <= r_xo[672 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref720[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2208 +: 8] !== ref720[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 720 lane vm_g6_b1_xf0>p20"); end end end
    reg [7:0] ref721=0;
    always @(posedge clk) if (lane_me_prev) ref721 <= r_xo[912 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref721[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2216 +: 8] !== ref721[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 721 lane vm_g6_b1_xf1>p18"); end end end
    reg [23:0] ref722=0;
    always @(posedge clk) if (lane_me_prev) ref722 <= {ref722[15:0], d_e[1136 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref722[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2224 +: 8] !== ref722[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 722 lane vm_g7_b7_xf1>p15"); end end end
    reg [23:0] ref723=0;
    always @(posedge clk) if (lane_me_prev) ref723 <= {ref723[15:0], d_e[1144 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref723[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2232 +: 8] !== ref723[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 723 lane vm_g7_b7_xf0>p15"); end end end
    reg [23:0] ref724=0;
    always @(posedge clk) if (lane_me_prev) ref724 <= {ref724[15:0], d_e[1152 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref724[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2240 +: 8] !== ref724[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 724 lane vm_g7_b6_xf1>p15"); end end end
    reg [23:0] ref725=0;
    always @(posedge clk) if (lane_me_prev) ref725 <= {ref725[15:0], d_e[1160 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref725[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2248 +: 8] !== ref725[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 725 lane vm_g7_b7_xf0>p17"); end end end
    reg [31:0] ref726=0;
    always @(posedge clk) if (lane_me_prev) ref726 <= {ref726[23:0], d_e[1168 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref726[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2256 +: 8] !== ref726[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 726 lane vm_g7_b3_xf0>p15"); end end end
    reg [31:0] ref727=0;
    always @(posedge clk) if (lane_me_prev) ref727 <= {ref727[23:0], d_e[1176 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref727[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2264 +: 8] !== ref727[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 727 lane vm_g7_b2_xf1>p15"); end end end
    reg [79:0] ref728=0;
    always @(posedge clk) if (lane_me_prev) ref728 <= {ref728[71:0], d_e[1184 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref728[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2272 +: 8] !== ref728[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 728 lane vm_g7_b2_xf1>p17"); end end end
    reg [87:0] ref729=0;
    always @(posedge clk) if (lane_me_prev) ref729 <= {ref729[79:0], r_xo[3976 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref729[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2280 +: 8] !== ref729[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 729 lane vm_g6_b7_xf1>p17"); end end end
    reg [23:0] ref730=0;
    always @(posedge clk) if (lane_me_prev) ref730 <= {ref730[15:0], r_xo[3448 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref730[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2288 +: 8] !== ref730[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 730 lane vm_g6_b6_xf1>p15"); end end end
    reg [23:0] ref731=0;
    always @(posedge clk) if (lane_me_prev) ref731 <= {ref731[15:0], r_xo[1912 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref731[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2296 +: 8] !== ref731[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 731 lane vm_g6_b3_xf1>p15"); end end end
    reg [87:0] ref732=0;
    always @(posedge clk) if (lane_me_prev) ref732 <= {ref732[79:0], r_xo[3464 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref732[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2304 +: 8] !== ref732[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 732 lane vm_g6_b6_xf1>p17"); end end end
    reg [7:0] ref733=0;
    always @(posedge clk) if (lane_me_prev) ref733 <= r_xo[888 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref733[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2312 +: 8] !== ref733[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 733 lane vm_g6_b1_xf1>p15"); end end end
    reg [7:0] ref734=0;
    always @(posedge clk) if (lane_me_prev) ref734 <= r_xo[896 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref734[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2320 +: 8] !== ref734[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 734 lane vm_g6_b1_xf1>p16"); end end end
    reg [87:0] ref735=0;
    always @(posedge clk) if (lane_me_prev) ref735 <= {ref735[79:0], r_xo[904 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref735[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2328 +: 8] !== ref735[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 735 lane vm_g6_b1_xf1>p17"); end end end
    reg [15:0] ref736=0;
    always @(posedge clk) if (lane_me_prev) ref736 <= {ref736[7:0], r_xo[816 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref736[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2336 +: 8] !== ref736[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 736 lane vm_g6_b1_xf1>p6"); end end end
    reg [7:0] ref737=0;
    always @(posedge clk) if (lane_me_prev) ref737 <= r_xo[840 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref737[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2344 +: 8] !== ref737[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 737 lane vm_g6_b1_xf1>p9"); end end end
    reg [15:0] ref738=0;
    always @(posedge clk) if (lane_me_prev) ref738 <= {ref738[7:0], r_xo[864 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref738[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2352 +: 8] !== ref738[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 738 lane vm_g6_b1_xf1>p12"); end end end
    reg [15:0] ref739=0;
    always @(posedge clk) if (lane_me_prev) ref739 <= {ref739[7:0], r_xo[2304 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref739[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2360 +: 8] !== ref739[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 739 lane vm_g6_b4_xf1>p0"); end end end
    reg [15:0] ref740=0;
    always @(posedge clk) if (lane_me_prev) ref740 <= {ref740[7:0], r_xo[2312 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref740[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2368 +: 8] !== ref740[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 740 lane vm_g6_b4_xf1>p1"); end end end
    reg [7:0] ref741=0;
    always @(posedge clk) if (lane_me_prev) ref741 <= r_xo[2328 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref741[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2376 +: 8] !== ref741[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 741 lane vm_g6_b4_xf1>p3"); end end end
    reg [7:0] ref742=0;
    always @(posedge clk) if (lane_me_prev) ref742 <= r_xo[2336 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref742[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2384 +: 8] !== ref742[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 742 lane vm_g6_b4_xf1>p4"); end end end
    reg [15:0] ref743=0;
    always @(posedge clk) if (lane_me_prev) ref743 <= {ref743[7:0], r_xo[2352 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref743[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2392 +: 8] !== ref743[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 743 lane vm_g6_b4_xf1>p6"); end end end
    reg [15:0] ref744=0;
    always @(posedge clk) if (lane_me_prev) ref744 <= {ref744[7:0], r_xo[1016 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref744[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2400 +: 8] !== ref744[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 744 lane vm_g6_b1_xf1>p31"); end end end
    reg [15:0] ref745=0;
    always @(posedge clk) if (lane_me_prev) ref745 <= {ref745[7:0], r_xo[2360 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref745[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2408 +: 8] !== ref745[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 745 lane vm_g6_b4_xf1>p7"); end end end
    reg [7:0] ref746=0;
    always @(posedge clk) if (lane_me_prev) ref746 <= r_xo[2376 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref746[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2416 +: 8] !== ref746[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 746 lane vm_g6_b4_xf1>p9"); end end end
    reg [7:0] ref747=0;
    always @(posedge clk) if (lane_me_prev) ref747 <= r_xo[992 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref747[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2424 +: 8] !== ref747[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 747 lane vm_g6_b1_xf1>p28"); end end end
    reg [7:0] ref748=0;
    always @(posedge clk) if (lane_me_prev) ref748 <= r_xo[2384 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref748[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2432 +: 8] !== ref748[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 748 lane vm_g6_b4_xf1>p10"); end end end
    reg [71:0] ref749=0;
    always @(posedge clk) if (lane_me_prev) ref749 <= {ref749[63:0], r_xo[2392 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref749[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2440 +: 8] !== ref749[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 749 lane vm_g6_b4_xf1>p11"); end end end
    reg [15:0] ref750=0;
    always @(posedge clk) if (lane_me_prev) ref750 <= {ref750[7:0], r_xo[2400 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref750[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2448 +: 8] !== ref750[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 750 lane vm_g6_b4_xf1>p12"); end end end
    reg [15:0] ref751=0;
    always @(posedge clk) if (lane_me_prev) ref751 <= {ref751[7:0], r_xo[2408 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref751[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2456 +: 8] !== ref751[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 751 lane vm_g6_b4_xf1>p13"); end end end
    reg [15:0] ref752=0;
    always @(posedge clk) if (lane_me_prev) ref752 <= {ref752[7:0], r_xo[2416 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref752[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2464 +: 8] !== ref752[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 752 lane vm_g6_b4_xf1>p14"); end end end
    reg [7:0] ref753=0;
    always @(posedge clk) if (lane_me_prev) ref753 <= r_xo[2424 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref753[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2472 +: 8] !== ref753[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 753 lane vm_g6_b4_xf1>p15"); end end end
    reg [7:0] ref754=0;
    always @(posedge clk) if (lane_me_prev) ref754 <= r_xo[2432 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref754[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2480 +: 8] !== ref754[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 754 lane vm_g6_b4_xf1>p16"); end end end
    reg [87:0] ref755=0;
    always @(posedge clk) if (lane_me_prev) ref755 <= {ref755[79:0], r_xo[2440 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref755[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2488 +: 8] !== ref755[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 755 lane vm_g6_b4_xf1>p17"); end end end
    reg [7:0] ref756=0;
    always @(posedge clk) if (lane_me_prev) ref756 <= r_xo[2448 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref756[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2496 +: 8] !== ref756[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 756 lane vm_g6_b4_xf1>p18"); end end end
    reg [87:0] ref757=0;
    always @(posedge clk) if (lane_me_prev) ref757 <= {ref757[79:0], r_xo[1968 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref757[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2504 +: 8] !== ref757[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 757 lane vm_g6_b3_xf1>p22"); end end end
    reg [87:0] ref758=0;
    always @(posedge clk) if (lane_me_prev) ref758 <= {ref758[79:0], r_xo[3728 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref758[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2512 +: 8] !== ref758[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 758 lane vm_g6_b7_xf0>p18"); end end end
    reg [23:0] ref759=0;
    always @(posedge clk) if (lane_me_prev) ref759 <= {ref759[15:0], r_xo[3472 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref759[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2520 +: 8] !== ref759[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 759 lane vm_g6_b6_xf1>p18"); end end end
    reg [23:0] ref760=0;
    always @(posedge clk) if (lane_me_prev) ref760 <= {ref760[15:0], r_xo[3216 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref760[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2528 +: 8] !== ref760[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 760 lane vm_g6_b6_xf0>p18"); end end end
    reg [23:0] ref761=0;
    always @(posedge clk) if (lane_me_prev) ref761 <= {ref761[15:0], r_xo[1936 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref761[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2536 +: 8] !== ref761[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 761 lane vm_g6_b3_xf1>p18"); end end end
    reg [23:0] ref762=0;
    always @(posedge clk) if (lane_me_prev) ref762 <= {ref762[15:0], r_xo[1680 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref762[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2544 +: 8] !== ref762[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 762 lane vm_g6_b3_xf0>p18"); end end end
    reg [7:0] ref763=0;
    always @(posedge clk) if (lane_me_prev) ref763 <= r_xo[1200 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref763[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2552 +: 8] !== ref763[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 763 lane vm_g6_b2_xf0>p22"); end end end
    reg [7:0] ref764=0;
    always @(posedge clk) if (lane_me_prev) ref764 <= r_xo[1192 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref764[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2560 +: 8] !== ref764[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 764 lane vm_g6_b2_xf0>p21"); end end end
    reg [7:0] ref765=0;
    always @(posedge clk) if (lane_me_prev) ref765 <= r_xo[1184 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref765[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2568 +: 8] !== ref765[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 765 lane vm_g6_b2_xf0>p20"); end end end
    reg [7:0] ref766=0;
    always @(posedge clk) if (lane_me_prev) ref766 <= r_xo[1168 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref766[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2576 +: 8] !== ref766[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 766 lane vm_g6_b2_xf0>p18"); end end end
    reg [7:0] ref767=0;
    always @(posedge clk) if (lane_me_prev) ref767 <= r_xo[400 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref767[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2584 +: 8] !== ref767[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 767 lane vm_g6_b0_xf1>p18"); end end end
    reg [23:0] ref768=0;
    always @(posedge clk) if (lane_me_prev) ref768 <= {ref768[15:0], d_e[1192 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref768[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2432 +: 8] !== ref768[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 768 lane vm_g7_b5_xf1>p13"); end end end
    reg [23:0] ref769=0;
    always @(posedge clk) if (lane_me_prev) ref769 <= {ref769[15:0], d_e[1200 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref769[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2440 +: 8] !== ref769[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 769 lane vm_g7_b5_xf0>p13"); end end end
    reg [23:0] ref770=0;
    always @(posedge clk) if (lane_me_prev) ref770 <= {ref770[15:0], d_e[1208 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref770[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2592 +: 8] !== ref770[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 770 lane vm_g7_b7_xf0>p16"); end end end
    reg [23:0] ref771=0;
    always @(posedge clk) if (lane_me_prev) ref771 <= {ref771[15:0], d_e[1216 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref771[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2600 +: 8] !== ref771[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 771 lane vm_g7_b3_xf1>p16"); end end end
    reg [23:0] ref772=0;
    always @(posedge clk) if (lane_me_prev) ref772 <= {ref772[15:0], r_xo[1272 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref772[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2608 +: 8] !== ref772[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 772 lane vm_g6_b2_xf0>p31"); end end end
    reg [23:0] ref773=0;
    always @(posedge clk) if (lane_me_prev) ref773 <= {ref773[15:0], d_e[1224 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref773[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2448 +: 8] !== ref773[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 773 lane vm_g7_b1_xf1>p13"); end end end
    reg [31:0] ref774=0;
    always @(posedge clk) if (lane_me_prev) ref774 <= {ref774[23:0], d_e[1232 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref774[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2456 +: 8] !== ref774[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 774 lane vm_g7_b1_xf0>p13"); end end end
    reg [79:0] ref775=0;
    always @(posedge clk) if (lane_me_prev) ref775 <= {ref775[71:0], d_e[1240 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref775[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2616 +: 8] !== ref775[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 775 lane vm_g7_b3_xf0>p16"); end end end
    reg [23:0] ref776=0;
    always @(posedge clk) if (lane_me_prev) ref776 <= {ref776[15:0], d_e[1248 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref776[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2624 +: 8] !== ref776[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 776 lane vm_g7_b2_xf1>p16"); end end end
    reg [79:0] ref777=0;
    always @(posedge clk) if (lane_me_prev) ref777 <= {ref777[71:0], d_e[1256 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref777[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2632 +: 8] !== ref777[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 777 lane vm_g7_b3_xf0>p17"); end end end
    reg [31:0] ref778=0;
    always @(posedge clk) if (lane_me_prev) ref778 <= {ref778[23:0], d_e[1264 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref778[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2640 +: 8] !== ref778[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 778 lane vm_g7_b2_xf0>p16"); end end end
    reg [15:0] ref779=0;
    always @(posedge clk) if (lane_me_prev) ref779 <= {ref779[7:0], r_xo[1248 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref779[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2648 +: 8] !== ref779[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 779 lane vm_g6_b2_xf0>p28"); end end end
    reg [15:0] ref780=0;
    always @(posedge clk) if (lane_me_prev) ref780 <= {ref780[7:0], r_xo[480 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref780[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2656 +: 8] !== ref780[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 780 lane vm_g6_b0_xf1>p28"); end end end
    reg [15:0] ref781=0;
    always @(posedge clk) if (lane_me_prev) ref781 <= {ref781[7:0], r_xo[224 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref781[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2664 +: 8] !== ref781[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 781 lane vm_g6_b0_xf0>p28"); end end end
    reg [15:0] ref782=0;
    always @(posedge clk) if (lane_me_prev) ref782 <= {ref782[7:0], r_xo[216 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref782[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1120 +: 8] !== ref782[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 782 lane vm_g6_b0_xf0>p27"); end end end
    reg [23:0] ref783=0;
    always @(posedge clk) if (lane_me_prev) ref783 <= {ref783[15:0], r_xo[2664 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref783[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2464 +: 8] !== ref783[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 783 lane vm_g6_b5_xf0>p13"); end end end
    reg [87:0] ref784=0;
    always @(posedge clk) if (lane_me_prev) ref784 <= {ref784[79:0], r_xo[3712 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref784[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2672 +: 8] !== ref784[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 784 lane vm_g6_b7_xf0>p16"); end end end
    reg [23:0] ref785=0;
    always @(posedge clk) if (lane_me_prev) ref785 <= {ref785[15:0], r_xo[3456 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref785[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2680 +: 8] !== ref785[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 785 lane vm_g6_b6_xf1>p16"); end end end
    reg [23:0] ref786=0;
    always @(posedge clk) if (lane_me_prev) ref786 <= {ref786[15:0], r_xo[2672 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref786[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2472 +: 8] !== ref786[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 786 lane vm_g6_b5_xf0>p14"); end end end
    reg [87:0] ref787=0;
    always @(posedge clk) if (lane_me_prev) ref787 <= {ref787[79:0], r_xo[3720 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref787[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2688 +: 8] !== ref787[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 787 lane vm_g6_b7_xf0>p17"); end end end
    reg [23:0] ref788=0;
    always @(posedge clk) if (lane_me_prev) ref788 <= {ref788[15:0], r_xo[3200 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref788[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2696 +: 8] !== ref788[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 788 lane vm_g6_b6_xf0>p16"); end end end
    reg [23:0] ref789=0;
    always @(posedge clk) if (lane_me_prev) ref789 <= {ref789[15:0], r_xo[456 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref789[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2704 +: 8] !== ref789[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 789 lane vm_g6_b0_xf1>p25"); end end end
    reg [87:0] ref790=0;
    always @(posedge clk) if (lane_me_prev) ref790 <= {ref790[79:0], r_xo[2680 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref790[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2480 +: 8] !== ref790[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 790 lane vm_g6_b5_xf0>p15"); end end end
    reg [87:0] ref791=0;
    always @(posedge clk) if (lane_me_prev) ref791 <= {ref791[79:0], r_xo[872 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref791[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2488 +: 8] !== ref791[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 791 lane vm_g6_b1_xf1>p13"); end end end
    reg [23:0] ref792=0;
    always @(posedge clk) if (lane_me_prev) ref792 <= {ref792[15:0], r_xo[1920 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref792[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2712 +: 8] !== ref792[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 792 lane vm_g6_b3_xf1>p16"); end end end
    reg [23:0] ref793=0;
    always @(posedge clk) if (lane_me_prev) ref793 <= {ref793[15:0], r_xo[200 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref793[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2720 +: 8] !== ref793[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 793 lane vm_g6_b0_xf0>p25"); end end end
    reg [23:0] ref794=0;
    always @(posedge clk) if (lane_me_prev) ref794 <= {ref794[15:0], r_xo[192 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref794[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2728 +: 8] !== ref794[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 794 lane vm_g6_b0_xf0>p24"); end end end
    reg [7:0] ref795=0;
    always @(posedge clk) if (lane_me_prev) ref795 <= r_xo[2688 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref795[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2736 +: 8] !== ref795[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 795 lane vm_g6_b5_xf0>p16"); end end end
    reg [7:0] ref796=0;
    always @(posedge clk) if (lane_me_prev) ref796 <= r_xo[2696 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref796[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2744 +: 8] !== ref796[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 796 lane vm_g6_b5_xf0>p17"); end end end
    reg [7:0] ref797=0;
    always @(posedge clk) if (lane_me_prev) ref797 <= r_xo[2704 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref797[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2752 +: 8] !== ref797[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 797 lane vm_g6_b5_xf0>p18"); end end end
    reg [7:0] ref798=0;
    always @(posedge clk) if (lane_me_prev) ref798 <= r_xo[1160 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref798[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2760 +: 8] !== ref798[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 798 lane vm_g6_b2_xf0>p17"); end end end
    reg [15:0] ref799=0;
    always @(posedge clk) if (lane_me_prev) ref799 <= {ref799[7:0], r_xo[800 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref799[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2496 +: 8] !== ref799[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 799 lane vm_g6_b1_xf1>p4"); end end end
    reg [23:0] ref800=0;
    always @(posedge clk) if (lane_me_prev) ref800 <= {ref800[15:0], r_xo[2616 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref800[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2504 +: 8] !== ref800[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 800 lane vm_g6_b5_xf0>p7"); end end end
    reg [23:0] ref801=0;
    always @(posedge clk) if (lane_me_prev) ref801 <= {ref801[15:0], d_e[1272 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref801[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2512 +: 8] !== ref801[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 801 lane vm_g7_b0_xf1>p13"); end end end
    reg [23:0] ref802=0;
    always @(posedge clk) if (lane_me_prev) ref802 <= {ref802[15:0], r_xo[2632 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref802[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2520 +: 8] !== ref802[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 802 lane vm_g6_b5_xf0>p9"); end end end
    reg [15:0] ref803=0;
    always @(posedge clk) if (lane_me_prev) ref803 <= {ref803[7:0], r_xo[2640 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref803[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2528 +: 8] !== ref803[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 803 lane vm_g6_b5_xf0>p10"); end end end
    reg [87:0] ref804=0;
    always @(posedge clk) if (lane_me_prev) ref804 <= {ref804[79:0], r_xo[2656 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref804[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2536 +: 8] !== ref804[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 804 lane vm_g6_b5_xf0>p12"); end end end
    reg [71:0] ref805=0;
    always @(posedge clk) if (lane_me_prev) ref805 <= {ref805[63:0], d_e[1280 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref805[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2768 +: 8] !== ref805[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 805 lane vm_g7_b6_xf0>p15"); end end end
    reg [71:0] ref806=0;
    always @(posedge clk) if (lane_me_prev) ref806 <= {ref806[63:0], d_e[1288 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref806[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2776 +: 8] !== ref806[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 806 lane vm_g7_b5_xf0>p14"); end end end
    reg [15:0] ref807=0;
    always @(posedge clk) if (lane_me_prev) ref807 <= {ref807[7:0], r_xo[1520 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref807[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1128 +: 8] !== ref807[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 807 lane vm_g6_b2_xf1>p30"); end end end
    reg [71:0] ref808=0;
    always @(posedge clk) if (lane_me_prev) ref808 <= {ref808[63:0], d_e[1296 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref808[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2784 +: 8] !== ref808[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 808 lane vm_g7_b2_xf0>p14"); end end end
    reg [15:0] ref809=0;
    always @(posedge clk) if (lane_me_prev) ref809 <= {ref809[7:0], r_xo[1264 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref809[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1136 +: 8] !== ref809[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 809 lane vm_g6_b2_xf0>p30"); end end end
    reg [71:0] ref810=0;
    always @(posedge clk) if (lane_me_prev) ref810 <= {ref810[63:0], d_e[1304 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref810[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2792 +: 8] !== ref810[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 810 lane vm_g7_b1_xf1>p14"); end end end
    reg [15:0] ref811=0;
    always @(posedge clk) if (lane_me_prev) ref811 <= {ref811[7:0], r_xo[1008 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref811[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1144 +: 8] !== ref811[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 811 lane vm_g6_b1_xf1>p30"); end end end
    reg [71:0] ref812=0;
    always @(posedge clk) if (lane_me_prev) ref812 <= {ref812[63:0], d_e[1312 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref812[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2800 +: 8] !== ref812[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 812 lane vm_g7_b2_xf0>p15"); end end end
    reg [15:0] ref813=0;
    always @(posedge clk) if (lane_me_prev) ref813 <= {ref813[7:0], d_e[1320 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref813[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2808 +: 8] !== ref813[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 813 lane vm_g7_b6_xf0>p18"); end end end
    reg [71:0] ref814=0;
    always @(posedge clk) if (lane_me_prev) ref814 <= {ref814[63:0], d_e[1328 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref814[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2816 +: 8] !== ref814[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 814 lane vm_g7_b1_xf0>p14"); end end end
    reg [71:0] ref815=0;
    always @(posedge clk) if (lane_me_prev) ref815 <= {ref815[63:0], d_e[1336 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref815[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2824 +: 8] !== ref815[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 815 lane vm_g7_b1_xf1>p15"); end end end
    reg [15:0] ref816=0;
    always @(posedge clk) if (lane_me_prev) ref816 <= {ref816[7:0], r_xo[496 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref816[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1152 +: 8] !== ref816[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 816 lane vm_g6_b0_xf1>p30"); end end end
    reg [15:0] ref817=0;
    always @(posedge clk) if (lane_me_prev) ref817 <= {ref817[7:0], r_xo[984 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref817[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1160 +: 8] !== ref817[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 817 lane vm_g6_b1_xf1>p27"); end end end
    reg [15:0] ref818=0;
    always @(posedge clk) if (lane_me_prev) ref818 <= {ref818[7:0], d_e[1344 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref818[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2832 +: 8] !== ref818[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 818 lane vm_g7_b2_xf0>p18"); end end end
    reg [15:0] ref819=0;
    always @(posedge clk) if (lane_me_prev) ref819 <= {ref819[7:0], r_xo[728 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref819[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1168 +: 8] !== ref819[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 819 lane vm_g6_b1_xf0>p27"); end end end
    reg [15:0] ref820=0;
    always @(posedge clk) if (lane_me_prev) ref820 <= {ref820[7:0], d_e[1352 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref820[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2840 +: 8] !== ref820[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 820 lane vm_g7_b1_xf1>p18"); end end end
    reg [15:0] ref821=0;
    always @(posedge clk) if (lane_me_prev) ref821 <= {ref821[7:0], r_xo[472 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref821[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1176 +: 8] !== ref821[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 821 lane vm_g6_b0_xf1>p27"); end end end
    reg [23:0] ref822=0;
    always @(posedge clk) if (lane_me_prev) ref822 <= {ref822[15:0], r_xo[1472 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref822[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2848 +: 8] !== ref822[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 822 lane vm_g6_b2_xf1>p24"); end end end
    reg [87:0] ref823=0;
    always @(posedge clk) if (lane_me_prev) ref823 <= {ref823[79:0], r_xo[2928 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref823[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2856 +: 8] !== ref823[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 823 lane vm_g6_b5_xf1>p14"); end end end
    reg [23:0] ref824=0;
    always @(posedge clk) if (lane_me_prev) ref824 <= {ref824[15:0], r_xo[1216 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref824[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2864 +: 8] !== ref824[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 824 lane vm_g6_b2_xf0>p24"); end end end
    reg [23:0] ref825=0;
    always @(posedge clk) if (lane_me_prev) ref825 <= {ref825[15:0], r_xo[1464 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref825[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2872 +: 8] !== ref825[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 825 lane vm_g6_b2_xf1>p23"); end end end
    reg [87:0] ref826=0;
    always @(posedge clk) if (lane_me_prev) ref826 <= {ref826[79:0], r_xo[2936 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref826[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2880 +: 8] !== ref826[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 826 lane vm_g6_b5_xf1>p15"); end end end
    reg [23:0] ref827=0;
    always @(posedge clk) if (lane_me_prev) ref827 <= {ref827[15:0], r_xo[960 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref827[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2888 +: 8] !== ref827[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 827 lane vm_g6_b1_xf1>p24"); end end end
    reg [23:0] ref828=0;
    always @(posedge clk) if (lane_me_prev) ref828 <= {ref828[15:0], r_xo[1960 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref828[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2896 +: 8] !== ref828[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 828 lane vm_g6_b3_xf1>p21"); end end end
    reg [23:0] ref829=0;
    always @(posedge clk) if (lane_me_prev) ref829 <= {ref829[15:0], r_xo[1208 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref829[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2904 +: 8] !== ref829[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 829 lane vm_g6_b2_xf0>p23"); end end end
    reg [87:0] ref830=0;
    always @(posedge clk) if (lane_me_prev) ref830 <= {ref830[79:0], r_xo[1392 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref830[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2912 +: 8] !== ref830[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 830 lane vm_g6_b2_xf1>p14"); end end end
    reg [23:0] ref831=0;
    always @(posedge clk) if (lane_me_prev) ref831 <= {ref831[15:0], r_xo[704 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref831[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2920 +: 8] !== ref831[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 831 lane vm_g6_b1_xf0>p24"); end end end
    reg [87:0] ref832=0;
    always @(posedge clk) if (lane_me_prev) ref832 <= {ref832[79:0], r_xo[2944 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref832[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2928 +: 8] !== ref832[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 832 lane vm_g6_b5_xf1>p16"); end end end
    reg [23:0] ref833=0;
    always @(posedge clk) if (lane_me_prev) ref833 <= {ref833[15:0], r_xo[952 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref833[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2936 +: 8] !== ref833[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 833 lane vm_g6_b1_xf1>p23"); end end end
    reg [23:0] ref834=0;
    always @(posedge clk) if (lane_me_prev) ref834 <= {ref834[15:0], r_xo[448 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref834[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2944 +: 8] !== ref834[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 834 lane vm_g6_b0_xf1>p24"); end end end
    reg [87:0] ref835=0;
    always @(posedge clk) if (lane_me_prev) ref835 <= {ref835[79:0], r_xo[1400 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref835[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2952 +: 8] !== ref835[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 835 lane vm_g6_b2_xf1>p15"); end end end
    reg [87:0] ref836=0;
    always @(posedge clk) if (lane_me_prev) ref836 <= {ref836[79:0], r_xo[880 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref836[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2960 +: 8] !== ref836[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 836 lane vm_g6_b1_xf1>p14"); end end end
    reg [87:0] ref837=0;
    always @(posedge clk) if (lane_me_prev) ref837 <= {ref837[79:0], r_xo[1408 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref837[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2968 +: 8] !== ref837[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 837 lane vm_g6_b2_xf1>p16"); end end end
    reg [7:0] ref838=0;
    always @(posedge clk) if (lane_me_prev) ref838 <= r_xo[1448 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref838[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2976 +: 8] !== ref838[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 838 lane vm_g6_b2_xf1>p21"); end end end
    reg [7:0] ref839=0;
    always @(posedge clk) if (lane_me_prev) ref839 <= r_xo[1440 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref839[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2984 +: 8] !== ref839[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 839 lane vm_g6_b2_xf1>p20"); end end end
    reg [7:0] ref840=0;
    always @(posedge clk) if (lane_me_prev) ref840 <= r_xo[2960 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref840[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[2992 +: 8] !== ref840[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 840 lane vm_g6_b5_xf1>p18"); end end end
    reg [7:0] ref841=0;
    always @(posedge clk) if (lane_me_prev) ref841 <= r_xo[1432 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref841[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3000 +: 8] !== ref841[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 841 lane vm_g6_b2_xf1>p19"); end end end
    reg [7:0] ref842=0;
    always @(posedge clk) if (lane_me_prev) ref842 <= r_xo[1176 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref842[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3008 +: 8] !== ref842[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 842 lane vm_g6_b2_xf0>p19"); end end end
    reg [7:0] ref843=0;
    always @(posedge clk) if (lane_me_prev) ref843 <= r_xo[1424 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref843[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3016 +: 8] !== ref843[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 843 lane vm_g6_b2_xf1>p18"); end end end
    reg [71:0] ref844=0;
    always @(posedge clk) if (lane_me_prev) ref844 <= {ref844[63:0], d_e[1360 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref844[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3024 +: 8] !== ref844[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 844 lane vm_g7_b6_xf0>p14"); end end end
    reg [15:0] ref845=0;
    always @(posedge clk) if (lane_me_prev) ref845 <= {ref845[7:0], d_e[1368 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref845[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3032 +: 8] !== ref845[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 845 lane vm_g7_b6_xf0>p17"); end end end
    reg [15:0] ref846=0;
    always @(posedge clk) if (lane_me_prev) ref846 <= {ref846[7:0], d_e[1376 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref846[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3040 +: 8] !== ref846[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 846 lane vm_g7_b2_xf0>p17"); end end end
    reg [15:0] ref847=0;
    always @(posedge clk) if (lane_me_prev) ref847 <= {ref847[7:0], d_e[1384 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref847[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3048 +: 8] !== ref847[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 847 lane vm_g7_b1_xf1>p17"); end end end
    reg [23:0] ref848=0;
    always @(posedge clk) if (lane_me_prev) ref848 <= {ref848[15:0], r_xo[1928 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref848[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3056 +: 8] !== ref848[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 848 lane vm_g6_b3_xf1>p17"); end end end
    reg [7:0] ref849=0;
    always @(posedge clk) if (lane_me_prev) ref849 <= r_xo[2952 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref849[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3064 +: 8] !== ref849[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 849 lane vm_g6_b5_xf1>p17"); end end end
    reg [7:0] ref850=0;
    always @(posedge clk) if (lane_me_prev) ref850 <= r_xo[1416 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref850[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3072 +: 8] !== ref850[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 850 lane vm_g6_b2_xf1>p17"); end end end
    reg [87:0] ref851=0;
    always @(posedge clk) if (lane_me_prev) ref851 <= {ref851[79:0], r_xo[2912 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref851[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2544 +: 8] !== ref851[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 851 lane vm_g6_b5_xf1>p12"); end end end
    reg [23:0] ref852=0;
    always @(posedge clk) if (lane_me_prev) ref852 <= {ref852[15:0], r_xo[1768 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref852[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1184 +: 8] !== ref852[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 852 lane vm_g6_b3_xf0>p29"); end end end
    reg [23:0] ref853=0;
    always @(posedge clk) if (lane_me_prev) ref853 <= {ref853[15:0], r_xo[1512 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref853[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1192 +: 8] !== ref853[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 853 lane vm_g6_b2_xf1>p29"); end end end
    reg [23:0] ref854=0;
    always @(posedge clk) if (lane_me_prev) ref854 <= {ref854[15:0], r_xo[1256 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref854[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1200 +: 8] !== ref854[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 854 lane vm_g6_b2_xf0>p29"); end end end
    reg [23:0] ref855=0;
    always @(posedge clk) if (lane_me_prev) ref855 <= {ref855[15:0], r_xo[1504 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref855[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1208 +: 8] !== ref855[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 855 lane vm_g6_b2_xf1>p28"); end end end
    reg [23:0] ref856=0;
    always @(posedge clk) if (lane_me_prev) ref856 <= {ref856[15:0], r_xo[1000 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref856[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1216 +: 8] !== ref856[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 856 lane vm_g6_b1_xf1>p29"); end end end
    reg [15:0] ref857=0;
    always @(posedge clk) if (lane_me_prev) ref857 <= {ref857[7:0], r_xo[1744 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref857[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1224 +: 8] !== ref857[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 857 lane vm_g6_b3_xf0>p26"); end end end
    reg [15:0] ref858=0;
    always @(posedge clk) if (lane_me_prev) ref858 <= {ref858[7:0], r_xo[1488 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref858[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1232 +: 8] !== ref858[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 858 lane vm_g6_b2_xf1>p26"); end end end
    reg [15:0] ref859=0;
    always @(posedge clk) if (lane_me_prev) ref859 <= {ref859[7:0], r_xo[1232 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref859[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1240 +: 8] !== ref859[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 859 lane vm_g6_b2_xf0>p26"); end end end
    reg [15:0] ref860=0;
    always @(posedge clk) if (lane_me_prev) ref860 <= {ref860[7:0], r_xo[976 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref860[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1248 +: 8] !== ref860[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 860 lane vm_g6_b1_xf1>p26"); end end end
    reg [71:0] ref861=0;
    always @(posedge clk) if (lane_me_prev) ref861 <= {ref861[63:0], d_e[1392 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref861[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2552 +: 8] !== ref861[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 861 lane vm_g7_b5_xf1>p12"); end end end
    reg [79:0] ref862=0;
    always @(posedge clk) if (lane_me_prev) ref862 <= {ref862[71:0], d_e[1400 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref862[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2560 +: 8] !== ref862[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 862 lane vm_g7_b1_xf1>p12"); end end end
    reg [87:0] ref863=0;
    always @(posedge clk) if (lane_me_prev) ref863 <= {ref863[79:0], r_xo[3184 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref863[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2568 +: 8] !== ref863[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 863 lane vm_g6_b6_xf0>p14"); end end end
    reg [87:0] ref864=0;
    always @(posedge clk) if (lane_me_prev) ref864 <= {ref864[79:0], r_xo[3168 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref864[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2576 +: 8] !== ref864[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 864 lane vm_g6_b6_xf0>p12"); end end end
    reg [15:0] ref865=0;
    always @(posedge clk) if (lane_me_prev) ref865 <= {ref865[7:0], r_xo[1528 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref865[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1256 +: 8] !== ref865[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 865 lane vm_g6_b2_xf1>p31"); end end end
    reg [39:0] ref866=0;
    always @(posedge clk) if (lane_me_prev) ref866 <= {ref866[31:0], d_e[1408 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref866[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2584 +: 8] !== ref866[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 866 lane vm_g7_b7_xf0>p12"); end end end
    reg [39:0] ref867=0;
    always @(posedge clk) if (lane_me_prev) ref867 <= {ref867[31:0], d_e[1416 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref867[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2592 +: 8] !== ref867[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 867 lane vm_g7_b6_xf1>p12"); end end end
    reg [71:0] ref868=0;
    always @(posedge clk) if (lane_me_prev) ref868 <= {ref868[63:0], d_e[1424 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref868[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2600 +: 8] !== ref868[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 868 lane vm_g7_b6_xf0>p12"); end end end
    reg [71:0] ref869=0;
    always @(posedge clk) if (lane_me_prev) ref869 <= {ref869[63:0], d_e[1432 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref869[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2608 +: 8] !== ref869[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 869 lane vm_g7_b6_xf0>p13"); end end end
    reg [79:0] ref870=0;
    always @(posedge clk) if (lane_me_prev) ref870 <= {ref870[71:0], d_e[1440 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref870[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2616 +: 8] !== ref870[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 870 lane vm_g7_b3_xf0>p12"); end end end
    reg [31:0] ref871=0;
    always @(posedge clk) if (lane_me_prev) ref871 <= {ref871[23:0], d_e[1448 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref871[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2624 +: 8] !== ref871[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 871 lane vm_g7_b2_xf1>p12"); end end end
    reg [47:0] ref872=0;
    always @(posedge clk) if (lane_me_prev) ref872 <= {ref872[39:0], d_e[1456 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref872[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2632 +: 8] !== ref872[40 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 872 lane vm_g7_b2_xf0>p12"); end end end
    reg [79:0] ref873=0;
    always @(posedge clk) if (lane_me_prev) ref873 <= {ref873[71:0], d_e[1464 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref873[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2640 +: 8] !== ref873[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 873 lane vm_g7_b2_xf0>p13"); end end end
    reg [87:0] ref874=0;
    always @(posedge clk) if (lane_me_prev) ref874 <= {ref874[79:0], r_xo[3432 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref874[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2648 +: 8] !== ref874[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 874 lane vm_g6_b6_xf1>p13"); end end end
    reg [87:0] ref875=0;
    always @(posedge clk) if (lane_me_prev) ref875 <= {ref875[79:0], r_xo[3440 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref875[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2656 +: 8] !== ref875[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 875 lane vm_g6_b6_xf1>p14"); end end end
    reg [87:0] ref876=0;
    always @(posedge clk) if (lane_me_prev) ref876 <= {ref876[79:0], r_xo[3936 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref876[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2664 +: 8] !== ref876[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 876 lane vm_g6_b7_xf1>p12"); end end end
    reg [87:0] ref877=0;
    always @(posedge clk) if (lane_me_prev) ref877 <= {ref877[79:0], r_xo[3424 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref877[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2672 +: 8] !== ref877[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 877 lane vm_g6_b6_xf1>p12"); end end end
    reg [87:0] ref878=0;
    always @(posedge clk) if (lane_me_prev) ref878 <= {ref878[79:0], r_xo[1888 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref878[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2680 +: 8] !== ref878[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 878 lane vm_g6_b3_xf1>p12"); end end end
    reg [87:0] ref879=0;
    always @(posedge clk) if (lane_me_prev) ref879 <= {ref879[79:0], r_xo[1376 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref879[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2688 +: 8] !== ref879[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 879 lane vm_g6_b2_xf1>p12"); end end end
    reg [55:0] ref880=0;
    always @(posedge clk) if (lane_me_prev) ref880 <= {ref880[47:0], r_xo[1992 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref880[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3080 +: 8] !== ref880[48 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 880 lane vm_g6_b3_xf1>p25"); end end end
    reg [87:0] ref881=0;
    always @(posedge clk) if (lane_me_prev) ref881 <= {ref881[79:0], r_xo[1736 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref881[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3088 +: 8] !== ref881[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 881 lane vm_g6_b3_xf0>p25"); end end end
    reg [87:0] ref882=0;
    always @(posedge clk) if (lane_me_prev) ref882 <= {ref882[79:0], r_xo[1480 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref882[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3096 +: 8] !== ref882[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 882 lane vm_g6_b2_xf1>p25"); end end end
    reg [23:0] ref883=0;
    always @(posedge clk) if (lane_me_prev) ref883 <= {ref883[15:0], r_xo[1224 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref883[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3104 +: 8] !== ref883[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 883 lane vm_g6_b2_xf0>p25"); end end end
    reg [23:0] ref884=0;
    always @(posedge clk) if (lane_me_prev) ref884 <= {ref884[15:0], r_xo[968 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref884[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3112 +: 8] !== ref884[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 884 lane vm_g6_b1_xf1>p25"); end end end
    reg [79:0] ref885=0;
    always @(posedge clk) if (lane_me_prev) ref885 <= {ref885[71:0], d_e[1472 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref885[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3120 +: 8] !== ref885[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 885 lane vm_g7_b2_xf1>p14"); end end end
    reg [87:0] ref886=0;
    always @(posedge clk) if (lane_me_prev) ref886 <= {ref886[79:0], r_xo[3696 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref886[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3128 +: 8] !== ref886[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 886 lane vm_g6_b7_xf0>p14"); end end end
    reg [87:0] ref887=0;
    always @(posedge clk) if (lane_me_prev) ref887 <= {ref887[79:0], r_xo[3704 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref887[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2696 +: 8] !== ref887[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 887 lane vm_g6_b7_xf0>p15"); end end end
    reg [87:0] ref888=0;
    always @(posedge clk) if (lane_me_prev) ref888 <= {ref888[79:0], r_xo[1896 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref888[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2704 +: 8] !== ref888[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 888 lane vm_g6_b3_xf1>p13"); end end end
    reg [31:0] ref889=0;
    always @(posedge clk) if (lane_me_prev) ref889 <= {ref889[23:0], d_e[1480 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref889[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2712 +: 8] !== ref889[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 889 lane vm_g7_b7_xf1>p13"); end end end
    reg [39:0] ref890=0;
    always @(posedge clk) if (lane_me_prev) ref890 <= {ref890[31:0], d_e[1488 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref890[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2720 +: 8] !== ref890[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 890 lane vm_g7_b7_xf0>p13"); end end end
    reg [71:0] ref891=0;
    always @(posedge clk) if (lane_me_prev) ref891 <= {ref891[63:0], d_e[1496 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref891[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2728 +: 8] !== ref891[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 891 lane vm_g7_b6_xf1>p13"); end end end
    reg [39:0] ref892=0;
    always @(posedge clk) if (lane_me_prev) ref892 <= {ref892[31:0], d_e[1504 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref892[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3136 +: 8] !== ref892[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 892 lane vm_g7_b7_xf0>p14"); end end end
    reg [71:0] ref893=0;
    always @(posedge clk) if (lane_me_prev) ref893 <= {ref893[63:0], d_e[1512 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref893[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2736 +: 8] !== ref893[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 893 lane vm_g7_b6_xf1>p14"); end end end
    reg [79:0] ref894=0;
    always @(posedge clk) if (lane_me_prev) ref894 <= {ref894[71:0], d_e[1520 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref894[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2744 +: 8] !== ref894[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 894 lane vm_g7_b3_xf0>p13"); end end end
    reg [63:0] ref895=0;
    always @(posedge clk) if (lane_me_prev) ref895 <= {ref895[55:0], d_e[1528 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref895[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2752 +: 8] !== ref895[56 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 895 lane vm_g7_b2_xf1>p13"); end end end
    reg [87:0] ref896=0;
    always @(posedge clk) if (lane_me_prev) ref896 <= {ref896[79:0], r_xo[3944 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref896[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2760 +: 8] !== ref896[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 896 lane vm_g6_b7_xf1>p13"); end end end
    reg [87:0] ref897=0;
    always @(posedge clk) if (lane_me_prev) ref897 <= {ref897[79:0], r_xo[3688 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref897[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2768 +: 8] !== ref897[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 897 lane vm_g6_b7_xf0>p13"); end end end
    reg [87:0] ref898=0;
    always @(posedge clk) if (lane_me_prev) ref898 <= {ref898[79:0], r_xo[1384 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref898[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2776 +: 8] !== ref898[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 898 lane vm_g6_b2_xf1>p13"); end end end
    reg [79:0] ref899=0;
    always @(posedge clk) if (lane_me_prev) ref899 <= {ref899[71:0], r_xo[3920 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref899[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2784 +: 8] !== ref899[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 899 lane vm_g6_b7_xf1>p10"); end end end
    reg [87:0] ref900=0;
    always @(posedge clk) if (lane_me_prev) ref900 <= {ref900[79:0], r_xo[3680 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref900[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2792 +: 8] !== ref900[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 900 lane vm_g6_b7_xf0>p12"); end end end
    reg [79:0] ref901=0;
    always @(posedge clk) if (lane_me_prev) ref901 <= {ref901[71:0], r_xo[1872 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref901[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2800 +: 8] !== ref901[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 901 lane vm_g6_b3_xf1>p10"); end end end
    reg [63:0] ref902=0;
    always @(posedge clk) if (lane_me_prev) ref902 <= {ref902[55:0], r_xo[2032 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref902[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1264 +: 8] !== ref902[56 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 902 lane vm_g6_b3_xf1>p30"); end end end
    reg [63:0] ref903=0;
    always @(posedge clk) if (lane_me_prev) ref903 <= {ref903[55:0], r_xo[1776 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref903[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1272 +: 8] !== ref903[56 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 903 lane vm_g6_b3_xf0>p30"); end end end
    reg [15:0] ref904=0;
    always @(posedge clk) if (lane_me_prev) ref904 <= {ref904[7:0], r_xo[1760 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref904[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1280 +: 8] !== ref904[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 904 lane vm_g6_b3_xf0>p28"); end end end
    reg [71:0] ref905=0;
    always @(posedge clk) if (lane_me_prev) ref905 <= {ref905[63:0], r_xo[2008 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref905[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1288 +: 8] !== ref905[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 905 lane vm_g6_b3_xf1>p27"); end end end
    reg [71:0] ref906=0;
    always @(posedge clk) if (lane_me_prev) ref906 <= {ref906[63:0], r_xo[1752 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref906[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1296 +: 8] !== ref906[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 906 lane vm_g6_b3_xf0>p27"); end end end
    reg [71:0] ref907=0;
    always @(posedge clk) if (lane_me_prev) ref907 <= {ref907[63:0], r_xo[1496 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref907[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1304 +: 8] !== ref907[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 907 lane vm_g6_b2_xf1>p27"); end end end
    reg [71:0] ref908=0;
    always @(posedge clk) if (lane_me_prev) ref908 <= {ref908[63:0], r_xo[1240 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref908[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1312 +: 8] !== ref908[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 908 lane vm_g6_b2_xf0>p27"); end end end
    reg [87:0] ref909=0;
    always @(posedge clk) if (lane_me_prev) ref909 <= {ref909[79:0], r_xo[1984 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref909[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3144 +: 8] !== ref909[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 909 lane vm_g6_b3_xf1>p24"); end end end
    reg [87:0] ref910=0;
    always @(posedge clk) if (lane_me_prev) ref910 <= {ref910[79:0], r_xo[1728 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref910[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3152 +: 8] !== ref910[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 910 lane vm_g6_b3_xf0>p24"); end end end
    reg [87:0] ref911=0;
    always @(posedge clk) if (lane_me_prev) ref911 <= {ref911[79:0], r_xo[1976 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref911[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3160 +: 8] !== ref911[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 911 lane vm_g6_b3_xf1>p23"); end end end
    reg [87:0] ref912=0;
    always @(posedge clk) if (lane_me_prev) ref912 <= {ref912[79:0], r_xo[1720 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref912[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3168 +: 8] !== ref912[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 912 lane vm_g6_b3_xf0>p23"); end end end
    reg [15:0] ref913=0;
    always @(posedge clk) if (lane_me_prev) ref913 <= {ref913[7:0], r_xo[2040 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref913[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1320 +: 8] !== ref913[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 913 lane vm_g6_b3_xf1>p31"); end end end
    reg [15:0] ref914=0;
    always @(posedge clk) if (lane_me_prev) ref914 <= {ref914[7:0], r_xo[1784 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref914[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1328 +: 8] !== ref914[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 914 lane vm_g6_b3_xf0>p31"); end end end
    reg [79:0] ref915=0;
    always @(posedge clk) if (lane_me_prev) ref915 <= {ref915[71:0], d_e[1536 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref915[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3176 +: 8] !== ref915[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 915 lane vm_g7_b3_xf0>p14"); end end end
    reg [31:0] ref916=0;
    always @(posedge clk) if (lane_me_prev) ref916 <= {ref916[23:0], d_e[1544 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref916[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3184 +: 8] !== ref916[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 916 lane vm_g7_b3_xf1>p15"); end end end
    reg [87:0] ref917=0;
    always @(posedge clk) if (lane_me_prev) ref917 <= {ref917[79:0], r_xo[3952 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref917[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3192 +: 8] !== ref917[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 917 lane vm_g6_b7_xf1>p14"); end end end
    reg [87:0] ref918=0;
    always @(posedge clk) if (lane_me_prev) ref918 <= {ref918[79:0], r_xo[3960 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref918[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3200 +: 8] !== ref918[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 918 lane vm_g6_b7_xf1>p15"); end end end
    reg [87:0] ref919=0;
    always @(posedge clk) if (lane_me_prev) ref919 <= {ref919[79:0], r_xo[3968 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref919[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3208 +: 8] !== ref919[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 919 lane vm_g6_b7_xf1>p16"); end end end
    reg [87:0] ref920=0;
    always @(posedge clk) if (lane_me_prev) ref920 <= {ref920[79:0], r_xo[1904 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref920[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3216 +: 8] !== ref920[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 920 lane vm_g6_b3_xf1>p14"); end end end
    reg [31:0] ref921=0;
    always @(posedge clk) if (lane_me_prev) ref921 <= {ref921[23:0], d_e[1552 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref921[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3224 +: 8] !== ref921[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 921 lane vm_g7_b7_xf1>p14"); end end end
    reg [31:0] ref922=0;
    always @(posedge clk) if (lane_me_prev) ref922 <= {ref922[23:0], d_e[1560 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref922[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3232 +: 8] !== ref922[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 922 lane vm_g7_b3_xf1>p14"); end end end
    reg [63:0] ref923=0;
    always @(posedge clk) if (lane_me_prev) ref923 <= {ref923[55:0], r_xo[2024 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref923[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1336 +: 8] !== ref923[56 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 923 lane vm_g6_b3_xf1>p29"); end end end
    reg [63:0] ref924=0;
    always @(posedge clk) if (lane_me_prev) ref924 <= {ref924[55:0], r_xo[2016 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref924[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1344 +: 8] !== ref924[56 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 924 lane vm_g6_b3_xf1>p28"); end end end
    reg [71:0] ref925=0;
    always @(posedge clk) if (lane_me_prev) ref925 <= {ref925[63:0], r_xo[2000 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref925[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1352 +: 8] !== ref925[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 925 lane vm_g6_b3_xf1>p26"); end end end
    reg [47:0] ref926=0;
    always @(posedge clk) if (lane_me_prev) ref926 <= {ref926[39:0], d_e[1568 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref926[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2808 +: 8] !== ref926[40 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 926 lane vm_g7_b7_xf1>p12"); end end end
    reg [39:0] ref927=0;
    always @(posedge clk) if (lane_me_prev) ref927 <= {ref927[31:0], d_e[1576 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref927[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2816 +: 8] !== ref927[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 927 lane vm_g7_b3_xf1>p12"); end end end
    reg [39:0] ref928=0;
    always @(posedge clk) if (lane_me_prev) ref928 <= {ref928[31:0], d_e[1584 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref928[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2824 +: 8] !== ref928[32 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 928 lane vm_g7_b3_xf1>p13"); end end end
    reg [87:0] ref929=0;
    always @(posedge clk) if (lane_me_prev) ref929 <= {ref929[79:0], r_xo[3752 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref929[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3240 +: 8] !== ref929[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 929 lane vm_g6_b7_xf0>p21"); end end end
    reg [7:0] ref930=0;
    always @(posedge clk) if (lane_me_prev) ref930 <= r_xo[2760 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref930[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3248 +: 8] !== ref930[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 930 lane vm_g6_b5_xf0>p25"); end end end
    reg [7:0] ref931=0;
    always @(posedge clk) if (lane_me_prev) ref931 <= r_xo[2504 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref931[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3256 +: 8] !== ref931[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 931 lane vm_g6_b4_xf1>p25"); end end end
    reg [71:0] ref932=0;
    always @(posedge clk) if (lane_me_prev) ref932 <= {ref932[63:0], r_xo[2752 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref932[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3264 +: 8] !== ref932[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 932 lane vm_g6_b5_xf0>p24"); end end end
    reg [7:0] ref933=0;
    always @(posedge clk) if (lane_me_prev) ref933 <= r_xo[2248 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref933[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3272 +: 8] !== ref933[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 933 lane vm_g6_b4_xf0>p25"); end end end
    reg [87:0] ref934=0;
    always @(posedge clk) if (lane_me_prev) ref934 <= {ref934[79:0], r_xo[2496 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref934[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3280 +: 8] !== ref934[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 934 lane vm_g6_b4_xf1>p24"); end end end
    reg [87:0] ref935=0;
    always @(posedge clk) if (lane_me_prev) ref935 <= {ref935[79:0], r_xo[2744 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref935[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3288 +: 8] !== ref935[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 935 lane vm_g6_b5_xf0>p23"); end end end
    reg [87:0] ref936=0;
    always @(posedge clk) if (lane_me_prev) ref936 <= {ref936[79:0], r_xo[2240 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref936[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3296 +: 8] !== ref936[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 936 lane vm_g6_b4_xf0>p24"); end end end
    reg [87:0] ref937=0;
    always @(posedge clk) if (lane_me_prev) ref937 <= {ref937[79:0], r_xo[2488 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref937[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3304 +: 8] !== ref937[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 937 lane vm_g6_b4_xf1>p23"); end end end
    reg [87:0] ref938=0;
    always @(posedge clk) if (lane_me_prev) ref938 <= {ref938[79:0], r_xo[2736 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref938[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3312 +: 8] !== ref938[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 938 lane vm_g6_b5_xf0>p22"); end end end
    reg [87:0] ref939=0;
    always @(posedge clk) if (lane_me_prev) ref939 <= {ref939[79:0], r_xo[2232 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref939[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3320 +: 8] !== ref939[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 939 lane vm_g6_b4_xf0>p23"); end end end
    reg [87:0] ref940=0;
    always @(posedge clk) if (lane_me_prev) ref940 <= {ref940[79:0], r_xo[2480 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref940[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3328 +: 8] !== ref940[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 940 lane vm_g6_b4_xf1>p22"); end end end
    reg [87:0] ref941=0;
    always @(posedge clk) if (lane_me_prev) ref941 <= {ref941[79:0], r_xo[2728 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref941[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3336 +: 8] !== ref941[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 941 lane vm_g6_b5_xf0>p21"); end end end
    reg [87:0] ref942=0;
    always @(posedge clk) if (lane_me_prev) ref942 <= {ref942[79:0], r_xo[2224 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref942[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3344 +: 8] !== ref942[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 942 lane vm_g6_b4_xf0>p22"); end end end
    reg [87:0] ref943=0;
    always @(posedge clk) if (lane_me_prev) ref943 <= {ref943[79:0], r_xo[2472 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref943[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3352 +: 8] !== ref943[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 943 lane vm_g6_b4_xf1>p21"); end end end
    reg [87:0] ref944=0;
    always @(posedge clk) if (lane_me_prev) ref944 <= {ref944[79:0], r_xo[2216 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref944[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3360 +: 8] !== ref944[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 944 lane vm_g6_b4_xf0>p21"); end end end
    reg [7:0] ref945=0;
    always @(posedge clk) if (lane_me_prev) ref945 <= r_xo[2808 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref945[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1360 +: 8] !== ref945[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 945 lane vm_g6_b5_xf0>p31"); end end end
    reg [7:0] ref946=0;
    always @(posedge clk) if (lane_me_prev) ref946 <= r_xo[2552 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref946[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1368 +: 8] !== ref946[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 946 lane vm_g6_b4_xf1>p31"); end end end
    reg [7:0] ref947=0;
    always @(posedge clk) if (lane_me_prev) ref947 <= r_xo[2296 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref947[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1376 +: 8] !== ref947[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 947 lane vm_g6_b4_xf0>p31"); end end end
    reg [71:0] ref948=0;
    always @(posedge clk) if (lane_me_prev) ref948 <= {ref948[63:0], r_xo[2544 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref948[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1384 +: 8] !== ref948[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 948 lane vm_g6_b4_xf1>p30"); end end end
    reg [71:0] ref949=0;
    always @(posedge clk) if (lane_me_prev) ref949 <= {ref949[63:0], r_xo[2288 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref949[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1392 +: 8] !== ref949[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 949 lane vm_g6_b4_xf0>p30"); end end end
    reg [79:0] ref950=0;
    always @(posedge clk) if (lane_me_prev) ref950 <= {ref950[71:0], r_xo[2792 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref950[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1400 +: 8] !== ref950[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 950 lane vm_g6_b5_xf0>p29"); end end end
    reg [15:0] ref951=0;
    always @(posedge clk) if (lane_me_prev) ref951 <= {ref951[7:0], r_xo[2536 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref951[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1408 +: 8] !== ref951[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 951 lane vm_g6_b4_xf1>p29"); end end end
    reg [79:0] ref952=0;
    always @(posedge clk) if (lane_me_prev) ref952 <= {ref952[71:0], r_xo[2784 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref952[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3368 +: 8] !== ref952[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 952 lane vm_g6_b5_xf0>p28"); end end end
    reg [15:0] ref953=0;
    always @(posedge clk) if (lane_me_prev) ref953 <= {ref953[7:0], r_xo[2280 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref953[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1416 +: 8] !== ref953[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 953 lane vm_g6_b4_xf0>p29"); end end end
    reg [15:0] ref954=0;
    always @(posedge clk) if (lane_me_prev) ref954 <= {ref954[7:0], r_xo[2528 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref954[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3376 +: 8] !== ref954[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 954 lane vm_g6_b4_xf1>p28"); end end end
    reg [15:0] ref955=0;
    always @(posedge clk) if (lane_me_prev) ref955 <= {ref955[7:0], r_xo[2272 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref955[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3384 +: 8] !== ref955[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 955 lane vm_g6_b4_xf0>p28"); end end end
    reg [87:0] ref956=0;
    always @(posedge clk) if (lane_me_prev) ref956 <= {ref956[79:0], r_xo[3736 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref956[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3392 +: 8] !== ref956[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 956 lane vm_g6_b7_xf0>p19"); end end end
    reg [7:0] ref957=0;
    always @(posedge clk) if (lane_me_prev) ref957 <= r_xo[2768 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref957[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1424 +: 8] !== ref957[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 957 lane vm_g6_b5_xf0>p26"); end end end
    reg [87:0] ref958=0;
    always @(posedge clk) if (lane_me_prev) ref958 <= {ref958[79:0], r_xo[2512 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref958[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1432 +: 8] !== ref958[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 958 lane vm_g6_b4_xf1>p26"); end end end
    reg [7:0] ref959=0;
    always @(posedge clk) if (lane_me_prev) ref959 <= r_xo[2256 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref959[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1440 +: 8] !== ref959[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 959 lane vm_g6_b4_xf0>p26"); end end end
    reg [87:0] ref960=0;
    always @(posedge clk) if (lane_me_prev) ref960 <= {ref960[79:0], r_xo[2712 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref960[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3400 +: 8] !== ref960[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 960 lane vm_g6_b5_xf0>p19"); end end end
    reg [87:0] ref961=0;
    always @(posedge clk) if (lane_me_prev) ref961 <= {ref961[79:0], r_xo[2456 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref961[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3408 +: 8] !== ref961[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 961 lane vm_g6_b4_xf1>p19"); end end end
    reg [87:0] ref962=0;
    always @(posedge clk) if (lane_me_prev) ref962 <= {ref962[79:0], r_xo[2720 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref962[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3416 +: 8] !== ref962[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 962 lane vm_g6_b5_xf0>p20"); end end end
    reg [87:0] ref963=0;
    always @(posedge clk) if (lane_me_prev) ref963 <= {ref963[79:0], r_xo[2200 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref963[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3424 +: 8] !== ref963[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 963 lane vm_g6_b4_xf0>p19"); end end end
    reg [87:0] ref964=0;
    always @(posedge clk) if (lane_me_prev) ref964 <= {ref964[79:0], r_xo[2464 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref964[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3432 +: 8] !== ref964[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 964 lane vm_g6_b4_xf1>p20"); end end end
    reg [87:0] ref965=0;
    always @(posedge clk) if (lane_me_prev) ref965 <= {ref965[79:0], r_xo[2208 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref965[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3440 +: 8] !== ref965[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 965 lane vm_g6_b4_xf0>p20"); end end end
    reg [31:0] ref966=0;
    always @(posedge clk) if (lane_me_prev) ref966 <= {ref966[23:0], d_e[1592 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref966[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3448 +: 8] !== ref966[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 966 lane vm_g7_b0_xf1>p3"); end end end
    reg [31:0] ref967=0;
    always @(posedge clk) if (lane_me_prev) ref967 <= {ref967[23:0], d_e[1600 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref967[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3456 +: 8] !== ref967[24 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 967 lane vm_g7_b0_xf1>p4"); end end end
    reg [15:0] ref968=0;
    always @(posedge clk) if (lane_me_prev) ref968 <= {ref968[7:0], d_e[1608 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref968[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3464 +: 8] !== ref968[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 968 lane vm_g7_b0_xf1>p6"); end end end
    reg [7:0] ref969=0;
    always @(posedge clk) if (lane_me_prev) ref969 <= d_e[1616 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref969[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3472 +: 8] !== ref969[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 969 lane vm_g7_b0_xf1>p9"); end end end
    reg [15:0] ref970=0;
    always @(posedge clk) if (lane_me_prev) ref970 <= {ref970[7:0], d_e[1624 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref970[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3480 +: 8] !== ref970[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 970 lane vm_g7_b0_xf1>p12"); end end end
    reg [7:0] ref971=0;
    always @(posedge clk) if (lane_me_prev) ref971 <= d_e[1632 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref971[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3488 +: 8] !== ref971[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 971 lane vm_g7_b0_xf1>p15"); end end end
    reg [15:0] ref972=0;
    always @(posedge clk) if (lane_me_prev) ref972 <= {ref972[7:0], d_e[1640 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref972[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3496 +: 8] !== ref972[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 972 lane vm_g7_b0_xf1>p18"); end end end
    reg [15:0] ref973=0;
    always @(posedge clk) if (lane_me_prev) ref973 <= {ref973[7:0], d_e[1648 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref973[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3504 +: 8] !== ref973[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 973 lane vm_g7_b0_xf0>p18"); end end end
    reg [7:0] ref974=0;
    always @(posedge clk) if (lane_me_prev) ref974 <= r_xo[3056 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref974[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1448 +: 8] !== ref974[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 974 lane vm_g6_b5_xf1>p30"); end end end
    reg [7:0] ref975=0;
    always @(posedge clk) if (lane_me_prev) ref975 <= r_xo[2800 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref975[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1456 +: 8] !== ref975[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 975 lane vm_g6_b5_xf0>p30"); end end end
    reg [7:0] ref976=0;
    always @(posedge clk) if (lane_me_prev) ref976 <= r_xo[3048 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref976[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1464 +: 8] !== ref976[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 976 lane vm_g6_b5_xf1>p29"); end end end
    reg [79:0] ref977=0;
    always @(posedge clk) if (lane_me_prev) ref977 <= {ref977[71:0], d_e[1656 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref977[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3512 +: 8] !== ref977[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 977 lane vm_g7_b3_xf0>p20"); end end end
    reg [79:0] ref978=0;
    always @(posedge clk) if (lane_me_prev) ref978 <= {ref978[71:0], d_e[1664 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref978[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3520 +: 8] !== ref978[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 978 lane vm_g7_b2_xf1>p20"); end end end
    reg [23:0] ref979=0;
    always @(posedge clk) if (lane_me_prev) ref979 <= {ref979[15:0], r_xo[4040 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref979[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3528 +: 8] !== ref979[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 979 lane vm_g6_b7_xf1>p25"); end end end
    reg [15:0] ref980=0;
    always @(posedge clk) if (lane_me_prev) ref980 <= {ref980[7:0], r_xo[3032 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref980[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1472 +: 8] !== ref980[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 980 lane vm_g6_b5_xf1>p27"); end end end
    reg [23:0] ref981=0;
    always @(posedge clk) if (lane_me_prev) ref981 <= {ref981[15:0], r_xo[3784 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref981[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3536 +: 8] !== ref981[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 981 lane vm_g6_b7_xf0>p25"); end end end
    reg [23:0] ref982=0;
    always @(posedge clk) if (lane_me_prev) ref982 <= {ref982[15:0], r_xo[4032 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref982[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3544 +: 8] !== ref982[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 982 lane vm_g6_b7_xf1>p24"); end end end
    reg [87:0] ref983=0;
    always @(posedge clk) if (lane_me_prev) ref983 <= {ref983[79:0], r_xo[3528 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref983[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3552 +: 8] !== ref983[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 983 lane vm_g6_b6_xf1>p25"); end end end
    reg [79:0] ref984=0;
    always @(posedge clk) if (lane_me_prev) ref984 <= {ref984[71:0], d_e[1672 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref984[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3560 +: 8] !== ref984[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 984 lane vm_g7_b1_xf0>p20"); end end end
    reg [47:0] ref985=0;
    always @(posedge clk) if (lane_me_prev) ref985 <= {ref985[39:0], r_xo[2776 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref985[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1480 +: 8] !== ref985[40 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 985 lane vm_g6_b5_xf0>p27"); end end end
    reg [87:0] ref986=0;
    always @(posedge clk) if (lane_me_prev) ref986 <= {ref986[79:0], r_xo[3776 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref986[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3568 +: 8] !== ref986[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 986 lane vm_g6_b7_xf0>p24"); end end end
    reg [87:0] ref987=0;
    always @(posedge clk) if (lane_me_prev) ref987 <= {ref987[79:0], r_xo[4024 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref987[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3576 +: 8] !== ref987[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 987 lane vm_g6_b7_xf1>p23"); end end end
    reg [79:0] ref988=0;
    always @(posedge clk) if (lane_me_prev) ref988 <= {ref988[71:0], r_xo[2520 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref988[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1488 +: 8] !== ref988[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 988 lane vm_g6_b4_xf1>p27"); end end end
    reg [23:0] ref989=0;
    always @(posedge clk) if (lane_me_prev) ref989 <= {ref989[15:0], r_xo[3768 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref989[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3584 +: 8] !== ref989[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 989 lane vm_g6_b7_xf0>p23"); end end end
    reg [79:0] ref990=0;
    always @(posedge clk) if (lane_me_prev) ref990 <= {ref990[71:0], r_xo[2264 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref990[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1496 +: 8] !== ref990[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 990 lane vm_g6_b4_xf0>p27"); end end end
    reg [87:0] ref991=0;
    always @(posedge clk) if (lane_me_prev) ref991 <= {ref991[79:0], r_xo[4016 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref991[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3592 +: 8] !== ref991[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 991 lane vm_g6_b7_xf1>p22"); end end end
    reg [87:0] ref992=0;
    always @(posedge clk) if (lane_me_prev) ref992 <= {ref992[79:0], r_xo[3760 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref992[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3600 +: 8] !== ref992[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 992 lane vm_g6_b7_xf0>p22"); end end end
    reg [87:0] ref993=0;
    always @(posedge clk) if (lane_me_prev) ref993 <= {ref993[79:0], r_xo[4008 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref993[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3608 +: 8] !== ref993[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 993 lane vm_g6_b7_xf1>p21"); end end end
    reg [7:0] ref994=0;
    always @(posedge clk) if (lane_me_prev) ref994 <= r_xo[3016 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref994[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3616 +: 8] !== ref994[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 994 lane vm_g6_b5_xf1>p25"); end end end
    reg [87:0] ref995=0;
    always @(posedge clk) if (lane_me_prev) ref995 <= {ref995[79:0], r_xo[3008 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref995[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3624 +: 8] !== ref995[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 995 lane vm_g6_b5_xf1>p24"); end end end
    reg [87:0] ref996=0;
    always @(posedge clk) if (lane_me_prev) ref996 <= {ref996[79:0], r_xo[3000 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref996[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3632 +: 8] !== ref996[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 996 lane vm_g6_b5_xf1>p23"); end end end
    reg [87:0] ref997=0;
    always @(posedge clk) if (lane_me_prev) ref997 <= {ref997[79:0], r_xo[2992 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref997[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3640 +: 8] !== ref997[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 997 lane vm_g6_b5_xf1>p22"); end end end
    reg [87:0] ref998=0;
    always @(posedge clk) if (lane_me_prev) ref998 <= {ref998[79:0], r_xo[2984 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref998[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3648 +: 8] !== ref998[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 998 lane vm_g6_b5_xf1>p21"); end end end
    reg [15:0] ref999=0;
    always @(posedge clk) if (lane_me_prev) ref999 <= {ref999[7:0], d_e[1680 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref999[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3656 +: 8] !== ref999[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 999 lane vm_g7_b7_xf0>p19"); end end end
    reg [7:0] ref1000=0;
    always @(posedge clk) if (lane_me_prev) ref1000 <= r_xo[3064 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1000[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3664 +: 8] !== ref1000[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1000 lane vm_g6_b5_xf1>p31"); end end end
    reg [79:0] ref1001=0;
    always @(posedge clk) if (lane_me_prev) ref1001 <= {ref1001[71:0], d_e[1688 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1001[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3672 +: 8] !== ref1001[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1001 lane vm_g7_b3_xf0>p19"); end end end
    reg [71:0] ref1002=0;
    always @(posedge clk) if (lane_me_prev) ref1002 <= {ref1002[63:0], r_xo[3040 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1002[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3680 +: 8] !== ref1002[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1002 lane vm_g6_b5_xf1>p28"); end end end
    reg [7:0] ref1003=0;
    always @(posedge clk) if (lane_me_prev) ref1003 <= d_e[1696 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1003[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3688 +: 8] !== ref1003[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1003 lane vm_g7_b1_xf0>p19"); end end end
    reg [87:0] ref1004=0;
    always @(posedge clk) if (lane_me_prev) ref1004 <= {ref1004[79:0], r_xo[3992 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1004[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3696 +: 8] !== ref1004[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1004 lane vm_g6_b7_xf1>p19"); end end end
    reg [87:0] ref1005=0;
    always @(posedge clk) if (lane_me_prev) ref1005 <= {ref1005[79:0], r_xo[4000 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1005[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3704 +: 8] !== ref1005[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1005 lane vm_g6_b7_xf1>p20"); end end end
    reg [87:0] ref1006=0;
    always @(posedge clk) if (lane_me_prev) ref1006 <= {ref1006[79:0], r_xo[3744 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1006[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3712 +: 8] !== ref1006[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1006 lane vm_g6_b7_xf0>p20"); end end end
    reg [87:0] ref1007=0;
    always @(posedge clk) if (lane_me_prev) ref1007 <= {ref1007[79:0], r_xo[2968 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1007[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3720 +: 8] !== ref1007[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1007 lane vm_g6_b5_xf1>p19"); end end end
    reg [87:0] ref1008=0;
    always @(posedge clk) if (lane_me_prev) ref1008 <= {ref1008[79:0], r_xo[2976 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1008[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3728 +: 8] !== ref1008[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1008 lane vm_g6_b5_xf1>p20"); end end end
    reg [7:0] ref1009=0;
    always @(posedge clk) if (lane_me_prev) ref1009 <= d_e[1704 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1009[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3736 +: 8] !== ref1009[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1009 lane vm_g7_b1_xf0>p6"); end end end
    reg [7:0] ref1010=0;
    always @(posedge clk) if (lane_me_prev) ref1010 <= d_e[1712 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1010[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3744 +: 8] !== ref1010[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1010 lane vm_g7_b1_xf0>p9"); end end end
    reg [7:0] ref1011=0;
    always @(posedge clk) if (lane_me_prev) ref1011 <= d_e[1720 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1011[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3752 +: 8] !== ref1011[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1011 lane vm_g7_b1_xf0>p12"); end end end
    reg [15:0] ref1012=0;
    always @(posedge clk) if (lane_me_prev) ref1012 <= {ref1012[7:0], d_e[1728 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1012[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3760 +: 8] !== ref1012[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1012 lane vm_g7_b7_xf0>p18"); end end end
    reg [15:0] ref1013=0;
    always @(posedge clk) if (lane_me_prev) ref1013 <= {ref1013[7:0], d_e[1736 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1013[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3768 +: 8] !== ref1013[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1013 lane vm_g7_b6_xf1>p18"); end end end
    reg [15:0] ref1014=0;
    always @(posedge clk) if (lane_me_prev) ref1014 <= {ref1014[7:0], d_e[1744 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1014[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3776 +: 8] !== ref1014[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1014 lane vm_g7_b3_xf1>p18"); end end end
    reg [71:0] ref1015=0;
    always @(posedge clk) if (lane_me_prev) ref1015 <= {ref1015[63:0], d_e[1752 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1015[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3784 +: 8] !== ref1015[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1015 lane vm_g7_b1_xf0>p15"); end end end
    reg [79:0] ref1016=0;
    always @(posedge clk) if (lane_me_prev) ref1016 <= {ref1016[71:0], d_e[1760 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1016[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3792 +: 8] !== ref1016[72 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1016 lane vm_g7_b3_xf0>p18"); end end end
    reg [15:0] ref1017=0;
    always @(posedge clk) if (lane_me_prev) ref1017 <= {ref1017[7:0], d_e[1768 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1017[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3800 +: 8] !== ref1017[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1017 lane vm_g7_b2_xf1>p18"); end end end
    reg [71:0] ref1018=0;
    always @(posedge clk) if (lane_me_prev) ref1018 <= {ref1018[63:0], d_e[1776 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1018[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3808 +: 8] !== ref1018[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1018 lane vm_g7_b1_xf0>p16"); end end end
    reg [71:0] ref1019=0;
    always @(posedge clk) if (lane_me_prev) ref1019 <= {ref1019[63:0], d_e[1784 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1019[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3816 +: 8] !== ref1019[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1019 lane vm_g7_b1_xf0>p17"); end end end
    reg [71:0] ref1020=0;
    always @(posedge clk) if (lane_me_prev) ref1020 <= {ref1020[63:0], d_e[1792 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1020[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3824 +: 8] !== ref1020[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1020 lane vm_g7_b1_xf0>p18"); end end end
    reg [87:0] ref1021=0;
    always @(posedge clk) if (lane_me_prev) ref1021 <= {ref1021[79:0], r_xo[3984 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1021[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3832 +: 8] !== ref1021[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1021 lane vm_g6_b7_xf1>p18"); end end end
    reg [7:0] ref1022=0;
    always @(posedge clk) if (lane_me_prev) ref1022 <= r_xo[3312 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1022[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1504 +: 8] !== ref1022[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1022 lane vm_g6_b6_xf0>p30"); end end end
    reg [15:0] ref1023=0;
    always @(posedge clk) if (lane_me_prev) ref1023 <= {ref1023[7:0], r_xo[3288 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1023[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1512 +: 8] !== ref1023[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1023 lane vm_g6_b6_xf0>p27"); end end end
    reg [7:0] ref1024=0;
    always @(posedge clk) if (lane_me_prev) ref1024 <= d_e[1800 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1024[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3840 +: 8] !== ref1024[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1024 lane vm_g7_b1_xf1>p20"); end end end
    reg [7:0] ref1025=0;
    always @(posedge clk) if (lane_me_prev) ref1025 <= r_xo[3280 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1025[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1520 +: 8] !== ref1025[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1025 lane vm_g6_b6_xf0>p26"); end end end
    reg [7:0] ref1026=0;
    always @(posedge clk) if (lane_me_prev) ref1026 <= r_xo[3272 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1026[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3848 +: 8] !== ref1026[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1026 lane vm_g6_b6_xf0>p25"); end end end
    reg [7:0] ref1027=0;
    always @(posedge clk) if (lane_me_prev) ref1027 <= r_xo[3264 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1027[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3856 +: 8] !== ref1027[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1027 lane vm_g6_b6_xf0>p24"); end end end
    reg [7:0] ref1028=0;
    always @(posedge clk) if (lane_me_prev) ref1028 <= r_xo[3256 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1028[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3864 +: 8] !== ref1028[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1028 lane vm_g6_b6_xf0>p23"); end end end
    reg [7:0] ref1029=0;
    always @(posedge clk) if (lane_me_prev) ref1029 <= r_xo[3248 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1029[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3872 +: 8] !== ref1029[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1029 lane vm_g6_b6_xf0>p22"); end end end
    reg [7:0] ref1030=0;
    always @(posedge clk) if (lane_me_prev) ref1030 <= r_xo[3240 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1030[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3880 +: 8] !== ref1030[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1030 lane vm_g6_b6_xf0>p21"); end end end
    reg [23:0] ref1031=0;
    always @(posedge clk) if (lane_me_prev) ref1031 <= {ref1031[15:0], d_e[1808 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1031[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3888 +: 8] !== ref1031[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1031 lane vm_g7_b3_xf1>p19"); end end end
    reg [7:0] ref1032=0;
    always @(posedge clk) if (lane_me_prev) ref1032 <= r_xo[3320 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1032[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3896 +: 8] !== ref1032[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1032 lane vm_g6_b6_xf0>p31"); end end end
    reg [15:0] ref1033=0;
    always @(posedge clk) if (lane_me_prev) ref1033 <= {ref1033[7:0], r_xo[3296 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1033[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3904 +: 8] !== ref1033[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1033 lane vm_g6_b6_xf0>p28"); end end end
    reg [7:0] ref1034=0;
    always @(posedge clk) if (lane_me_prev) ref1034 <= r_xo[3224 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1034[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3912 +: 8] !== ref1034[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1034 lane vm_g6_b6_xf0>p19"); end end end
    reg [7:0] ref1035=0;
    always @(posedge clk) if (lane_me_prev) ref1035 <= r_xo[3568 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1035[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1528 +: 8] !== ref1035[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1035 lane vm_g6_b6_xf1>p30"); end end end
    reg [7:0] ref1036=0;
    always @(posedge clk) if (lane_me_prev) ref1036 <= r_xo[3544 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1036[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1536 +: 8] !== ref1036[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1036 lane vm_g6_b6_xf1>p27"); end end end
    reg [7:0] ref1037=0;
    always @(posedge clk) if (lane_me_prev) ref1037 <= d_e[1816 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1037[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3920 +: 8] !== ref1037[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1037 lane vm_g7_b2_xf0>p20"); end end end
    reg [7:0] ref1038=0;
    always @(posedge clk) if (lane_me_prev) ref1038 <= r_xo[3520 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1038[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3928 +: 8] !== ref1038[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1038 lane vm_g6_b6_xf1>p24"); end end end
    reg [7:0] ref1039=0;
    always @(posedge clk) if (lane_me_prev) ref1039 <= r_xo[3512 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1039[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3936 +: 8] !== ref1039[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1039 lane vm_g6_b6_xf1>p23"); end end end
    reg [7:0] ref1040=0;
    always @(posedge clk) if (lane_me_prev) ref1040 <= r_xo[3504 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1040[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3944 +: 8] !== ref1040[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1040 lane vm_g6_b6_xf1>p22"); end end end
    reg [7:0] ref1041=0;
    always @(posedge clk) if (lane_me_prev) ref1041 <= r_xo[3496 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1041[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3952 +: 8] !== ref1041[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1041 lane vm_g6_b6_xf1>p21"); end end end
    reg [7:0] ref1042=0;
    always @(posedge clk) if (lane_me_prev) ref1042 <= r_xo[3024 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1042[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1544 +: 8] !== ref1042[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1042 lane vm_g6_b5_xf1>p26"); end end end
    reg [7:0] ref1043=0;
    always @(posedge clk) if (lane_me_prev) ref1043 <= r_xo[3488 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1043[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3960 +: 8] !== ref1043[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1043 lane vm_g6_b6_xf1>p20"); end end end
    reg [7:0] ref1044=0;
    always @(posedge clk) if (lane_me_prev) ref1044 <= r_xo[3232 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1044[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3968 +: 8] !== ref1044[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1044 lane vm_g6_b6_xf0>p20"); end end end
    reg [7:0] ref1045=0;
    always @(posedge clk) if (lane_me_prev) ref1045 <= r_xo[3816 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1045[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1552 +: 8] !== ref1045[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1045 lane vm_g6_b7_xf0>p29"); end end end
    reg [7:0] ref1046=0;
    always @(posedge clk) if (lane_me_prev) ref1046 <= r_xo[3560 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1046[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1560 +: 8] !== ref1046[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1046 lane vm_g6_b6_xf1>p29"); end end end
    reg [7:0] ref1047=0;
    always @(posedge clk) if (lane_me_prev) ref1047 <= r_xo[3304 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1047[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1568 +: 8] !== ref1047[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1047 lane vm_g6_b6_xf0>p29"); end end end
    reg [15:0] ref1048=0;
    always @(posedge clk) if (lane_me_prev) ref1048 <= {ref1048[7:0], r_xo[3792 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1048[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1576 +: 8] !== ref1048[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1048 lane vm_g6_b7_xf0>p26"); end end end
    reg [15:0] ref1049=0;
    always @(posedge clk) if (lane_me_prev) ref1049 <= {ref1049[7:0], r_xo[3536 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1049[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1584 +: 8] !== ref1049[8 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1049 lane vm_g6_b6_xf1>p26"); end end end
    reg [7:0] ref1050=0;
    always @(posedge clk) if (lane_me_prev) ref1050 <= r_xo[4088 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1050[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1592 +: 8] !== ref1050[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1050 lane vm_g6_b7_xf1>p31"); end end end
    reg [7:0] ref1051=0;
    always @(posedge clk) if (lane_me_prev) ref1051 <= r_xo[3832 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1051[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1600 +: 8] !== ref1051[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1051 lane vm_g6_b7_xf0>p31"); end end end
    reg [7:0] ref1052=0;
    always @(posedge clk) if (lane_me_prev) ref1052 <= r_xo[3576 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1052[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1608 +: 8] !== ref1052[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1052 lane vm_g6_b6_xf1>p31"); end end end
    reg [7:0] ref1053=0;
    always @(posedge clk) if (lane_me_prev) ref1053 <= r_xo[4064 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1053[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1616 +: 8] !== ref1053[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1053 lane vm_g6_b7_xf1>p28"); end end end
    reg [7:0] ref1054=0;
    always @(posedge clk) if (lane_me_prev) ref1054 <= r_xo[3808 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1054[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1624 +: 8] !== ref1054[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1054 lane vm_g6_b7_xf0>p28"); end end end
    reg [7:0] ref1055=0;
    always @(posedge clk) if (lane_me_prev) ref1055 <= r_xo[3552 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1055[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1632 +: 8] !== ref1055[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1055 lane vm_g6_b6_xf1>p28"); end end end
    reg [63:0] ref1056=0;
    always @(posedge clk) if (lane_me_prev) ref1056 <= {ref1056[55:0], r_xo[4080 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1056[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1640 +: 8] !== ref1056[56 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1056 lane vm_g6_b7_xf1>p30"); end end end
    reg [63:0] ref1057=0;
    always @(posedge clk) if (lane_me_prev) ref1057 <= {ref1057[55:0], r_xo[3824 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1057[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1648 +: 8] !== ref1057[56 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1057 lane vm_g6_b7_xf0>p30"); end end end
    reg [71:0] ref1058=0;
    always @(posedge clk) if (lane_me_prev) ref1058 <= {ref1058[63:0], r_xo[4056 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1058[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1656 +: 8] !== ref1058[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1058 lane vm_g6_b7_xf1>p27"); end end end
    reg [71:0] ref1059=0;
    always @(posedge clk) if (lane_me_prev) ref1059 <= {ref1059[63:0], r_xo[3800 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1059[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1664 +: 8] !== ref1059[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1059 lane vm_g6_b7_xf0>p27"); end end end
    reg [71:0] ref1060=0;
    always @(posedge clk) if (lane_me_prev) ref1060 <= {ref1060[63:0], r_xo[4048 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1060[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1672 +: 8] !== ref1060[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1060 lane vm_g6_b7_xf1>p26"); end end end
    reg [63:0] ref1061=0;
    always @(posedge clk) if (lane_me_prev) ref1061 <= {ref1061[55:0], r_xo[4072 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1061[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_e[1680 +: 8] !== ref1061[56 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1061 lane vm_g6_b7_xf1>p29"); end end end
    reg [87:0] ref1062=0;
    always @(posedge clk) if (lane_me_prev) ref1062 <= {ref1062[79:0], r_xo[1144 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1062[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3976 +: 8] !== ref1062[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1062 lane vm_g6_b2_xf0>p15"); end end end
    reg [87:0] ref1063=0;
    always @(posedge clk) if (lane_me_prev) ref1063 <= {ref1063[79:0], r_xo[104 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1063[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2832 +: 8] !== ref1063[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1063 lane vm_g6_b0_xf0>p13"); end end end
    reg [87:0] ref1064=0;
    always @(posedge clk) if (lane_me_prev) ref1064 <= {ref1064[79:0], r_xo[112 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1064[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2840 +: 8] !== ref1064[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1064 lane vm_g6_b0_xf0>p14"); end end end
    reg [87:0] ref1065=0;
    always @(posedge clk) if (lane_me_prev) ref1065 <= {ref1065[79:0], r_xo[120 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1065[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3984 +: 8] !== ref1065[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1065 lane vm_g6_b0_xf0>p15"); end end end
    reg [87:0] ref1066=0;
    always @(posedge clk) if (lane_me_prev) ref1066 <= {ref1066[79:0], r_xo[128 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1066[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[3992 +: 8] !== ref1066[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1066 lane vm_g6_b0_xf0>p16"); end end end
    reg [87:0] ref1067=0;
    always @(posedge clk) if (lane_me_prev) ref1067 <= {ref1067[79:0], r_xo[1120 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1067[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2848 +: 8] !== ref1067[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1067 lane vm_g6_b2_xf0>p12"); end end end
    reg [87:0] ref1068=0;
    always @(posedge clk) if (lane_me_prev) ref1068 <= {ref1068[79:0], r_xo[608 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1068[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2856 +: 8] !== ref1068[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1068 lane vm_g6_b1_xf0>p12"); end end end
    reg [87:0] ref1069=0;
    always @(posedge clk) if (lane_me_prev) ref1069 <= {ref1069[79:0], r_xo[96 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1069[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2864 +: 8] !== ref1069[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1069 lane vm_g6_b0_xf0>p12"); end end end
    reg [87:0] ref1070=0;
    always @(posedge clk) if (lane_me_prev) ref1070 <= {ref1070[79:0], r_xo[360 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1070[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2872 +: 8] !== ref1070[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1070 lane vm_g6_b0_xf1>p13"); end end end
    reg [87:0] ref1071=0;
    always @(posedge clk) if (lane_me_prev) ref1071 <= {ref1071[79:0], r_xo[368 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1071[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2880 +: 8] !== ref1071[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1071 lane vm_g6_b0_xf1>p14"); end end end
    reg [87:0] ref1072=0;
    always @(posedge clk) if (lane_me_prev) ref1072 <= {ref1072[79:0], r_xo[376 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1072[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[4000 +: 8] !== ref1072[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1072 lane vm_g6_b0_xf1>p15"); end end end
    reg [87:0] ref1073=0;
    always @(posedge clk) if (lane_me_prev) ref1073 <= {ref1073[79:0], r_xo[384 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1073[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[4008 +: 8] !== ref1073[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1073 lane vm_g6_b0_xf1>p16"); end end end
    reg [87:0] ref1074=0;
    always @(posedge clk) if (lane_me_prev) ref1074 <= {ref1074[79:0], r_xo[1632 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1074[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2888 +: 8] !== ref1074[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1074 lane vm_g6_b3_xf0>p12"); end end end
    reg [87:0] ref1075=0;
    always @(posedge clk) if (lane_me_prev) ref1075 <= {ref1075[79:0], r_xo[352 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1075[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2896 +: 8] !== ref1075[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1075 lane vm_g6_b0_xf1>p12"); end end end
    reg [23:0] ref1076=0;
    always @(posedge clk) if (lane_me_prev) ref1076 <= {ref1076[15:0], r_xo[1128 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1076[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2904 +: 8] !== ref1076[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1076 lane vm_g6_b2_xf0>p13"); end end end
    reg [87:0] ref1077=0;
    always @(posedge clk) if (lane_me_prev) ref1077 <= {ref1077[79:0], r_xo[1656 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1077[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2912 +: 8] !== ref1077[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1077 lane vm_g6_b3_xf0>p15"); end end end
    reg [87:0] ref1078=0;
    always @(posedge clk) if (lane_me_prev) ref1078 <= {ref1078[79:0], r_xo[624 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1078[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[4016 +: 8] !== ref1078[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1078 lane vm_g6_b1_xf0>p14"); end end end
    reg [7:0] ref1079=0;
    always @(posedge clk) if (lane_me_prev) ref1079 <= r_xo[632 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1079[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2920 +: 8] !== ref1079[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1079 lane vm_g6_b1_xf0>p15"); end end end
    reg [87:0] ref1080=0;
    always @(posedge clk) if (lane_me_prev) ref1080 <= {ref1080[79:0], r_xo[640 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1080[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[4024 +: 8] !== ref1080[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1080 lane vm_g6_b1_xf0>p16"); end end end
    reg [87:0] ref1081=0;
    always @(posedge clk) if (lane_me_prev) ref1081 <= {ref1081[79:0], r_xo[1640 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1081[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2928 +: 8] !== ref1081[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1081 lane vm_g6_b3_xf0>p13"); end end end
    reg [87:0] ref1082=0;
    always @(posedge clk) if (lane_me_prev) ref1082 <= {ref1082[79:0], r_xo[616 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1082[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2936 +: 8] !== ref1082[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1082 lane vm_g6_b1_xf0>p13"); end end end
    reg [7:0] ref1083=0;
    always @(posedge clk) if (lane_me_prev) ref1083 <= r_xo[544 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1083[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2944 +: 8] !== ref1083[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1083 lane vm_g6_b1_xf0>p4"); end end end
    reg [71:0] ref1084=0;
    always @(posedge clk) if (lane_me_prev) ref1084 <= {ref1084[63:0], r_xo[568 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1084[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2952 +: 8] !== ref1084[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1084 lane vm_g6_b1_xf0>p7"); end end end
    reg [71:0] ref1085=0;
    always @(posedge clk) if (lane_me_prev) ref1085 <= {ref1085[63:0], r_xo[584 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1085[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2960 +: 8] !== ref1085[64 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1085 lane vm_g6_b1_xf0>p9"); end end end
    reg [7:0] ref1086=0;
    always @(posedge clk) if (lane_me_prev) ref1086 <= r_xo[592 +: 8];
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1086[0 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_w[2968 +: 8] !== ref1086[0 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1086 lane vm_g6_b1_xf0>p10"); end end end
    reg [87:0] ref1087=0;
    always @(posedge clk) if (lane_me_prev) ref1087 <= {ref1087[79:0], r_xo[1648 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1087[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[4032 +: 8] !== ref1087[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1087 lane vm_g6_b3_xf0>p14"); end end end
    reg [87:0] ref1088=0;
    always @(posedge clk) if (lane_me_prev) ref1088 <= {ref1088[79:0], r_xo[1664 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1088[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[4040 +: 8] !== ref1088[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1088 lane vm_g6_b3_xf0>p16"); end end end
    reg [23:0] ref1089=0;
    always @(posedge clk) if (lane_me_prev) ref1089 <= {ref1089[15:0], r_xo[1672 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1089[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[4048 +: 8] !== ref1089[16 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1089 lane vm_g6_b3_xf0>p17"); end end end
    reg [87:0] ref1090=0;
    always @(posedge clk) if (lane_me_prev) ref1090 <= {ref1090[79:0], r_xo[1152 +: 8]};
    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if (ref1090[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if (q_s[4056 +: 8] !== ref1090[80 +: 8]) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment 1090 lane vm_g6_b2_xf0>p16"); end end end
    // xorshift64 ($urandom(seed) re-seeds on every call under Verilator: never use it)
    reg [63:0] rng;
    function automatic [31:0] rnd(input integer dummy);
        begin rng = rng ^ (rng << 13); rng = rng ^ (rng >> 7); rng = rng ^ (rng << 17); rnd = rng[47:16]; end
    endfunction
    integer cyc, w, errors = 0, checks = 0;
    integer pushes = 0, pops = 0, rowreads = 0, suans = 0, stalls = 0, moves = 0, garbage = 0, deep = 0;
    integer xo_chg = 0, ro_chg = 0, so_chg = 0, nonzero = 0, ovf_cmp = 0, sched_err = 0, e_xo = 0, e_ro = 0, e_so = 0, e_ovf = 0;
    integer ptime [0:65535];
    reg me_prev = 0;
    reg [4095:0] l_xo = 0; reg [511:0] l_ro = 0; reg [3071:0] l_so = 0;
    task automatic drive_common;
        begin
            for (w=0;w<351;w=w+1) d_w[8*w +: 8]=rnd(0);
            for (w=0;w<228;w=w+1) d_e[8*w +: 8]=rnd(0);
            me_prev = me_in;
            me_in = ((rnd(0) % 4) != 0);
            if (!me_in) stalls = stalls + 1; else moves = moves + 1;
            re = rnd(0); we = rnd(0) & rnd(0);
            ra = rnd(0); wl = rnd(0);
            for (w = 0; w < 4; w = w + 1) wm[w*32 +: 32] = rnd(0) | rnd(0);
            for (w = 0; w < 128; w = w + 1) wd[w*32 +: 32] = rnd(0);
            rq = ((rnd(0) % 3) == 0); rqb = rnd(0);
            sre = rnd(0); sra = rnd(0); swe = rnd(0); swl = rnd(0); swm = rnd(0) | rnd(0);
            if (DEPTH != 8 || DEPTHS != 8) begin      // routed depths: one in-range line per bank port
                for (w = 0; w < 8; w = w + 1) begin ra[w*LAW +: LAW] = rnd(0) % DEPTH; wl[w*LAW +: LAW] = rnd(0) % DEPTH; end
                for (w = 0; w < 6; w = w + 1) sra[w*LAWS +: LAWS] = rnd(0) % DEPTHS;
                for (w = 0; w < 2; w = w + 1) swl[w*LAWS +: LAWS] = rnd(0) % DEPTHS;
            end
            sv = ((rnd(0) % 3) == 0) ? rnd(0) : 3'd0;
            for (w = 0; w < 32; w = w + 1) swd[w*32 +: 32] = rnd(0);
            if (rq) rowreads = rowreads + 1;
            if (sv != 0) suans = suans + 1;
        end
    endtask
    task automatic check;
        begin
            @(posedge clk); #1;
            checks = checks + 1;
            if (xo !== r_xo) e_xo = e_xo + 1;
            if (ro !== r_ro) e_ro = e_ro + 1;
            if (so !== r_so) e_so = e_so + 1;
            if (ovf !== r_ovf) e_ovf = e_ovf + 1;
            if (xo !== r_xo || ro !== r_ro || so !== r_so || ovf !== r_ovf) begin
                errors = errors + 1;
                if (errors < 4) $display("region_leaf mismatch cyc %0d xo %0d ro %0d so %0d ovf %0d", cyc,
                    xo !== r_xo, ro !== r_ro, so !== r_so, ovf !== r_ovf);
            end
            if (r_xo !== l_xo) xo_chg = xo_chg + 1;
            if (r_ro !== l_ro) ro_chg = ro_chg + 1;
            if (r_so !== l_so) so_chg = so_chg + 1;
            for (w = 0; w < 128; w = w + 1) if (r_xo[w*32 +: 32] != 0) nonzero = nonzero + 1;
            for (w = 0; w < 16; w = w + 1) if (r_ro[w*32 +: 32] != 0) nonzero = nonzero + 1;
            for (w = 0; w < 96; w = w + 1) if (r_so[w*32 +: 32] != 0) nonzero = nonzero + 1;
            l_xo = r_xo; l_ro = r_ro; l_so = r_so;
        end
    endtask
    initial begin
        rng = 64'h9E3779B97F4A7C15 ^ {32'd0, SEED[31:0]} ^ ({32'd0, SEED[31:0]} << 32);
        // reset: inputs already random, outputs compared
        for (cyc = -6; cyc < 0; cyc = cyc + 1) begin
            @(negedge clk); drive_common; rq = 0; sv = 0; rowreads = 0; suans = 0; if (cyc == -1) rst_n = 1; check;
        end
        stalls = 0; moves = 0;
        // ---- main run: legal push / pop schedule ----
        for (cyc = 0; cyc < CYCLES; cyc = cyc + 1) begin
            @(negedge clk);
            drive_common;
            // push: at most NPP - 3 beats issued and not yet popped (cnt <= issued-unpopped + 2 pops in flight < NPP)
            xv = 0;
            if ((pushes - pops) <= NPP - 4 && (rnd(0) % 3) == 0) begin xv = 1; ptime[pushes & 65535] = cyc; pushes = pushes + 1; end
            if ((pushes - pops) >= NPP - 3) deep = deep + 1;
            // pop: the pin is sampled on engine edges only (me_t = me_in one edge ago); a pop is legal once its
            // beat's push has reached cnt (push + 7 edges, pop + 2 engine edges: 8 clocks is safe)
            if (me_prev) begin
                pop = 0;
                if (pops < pushes && ptime[pops & 65535] + 8 <= cyc && (rnd(0) % 2) == 0) begin pop = 1; pops = pops + 1; end
            end else begin
                pop = rnd(0); if (pop) garbage = garbage + 1;
            end
            check;
            if (r_ovf) sched_err = sched_err + 1;
        end
        // ---- overflow run ----
        for (cyc = CYCLES; cyc < CYCLES + 160; cyc = cyc + 1) begin
            @(negedge clk);
            drive_common;
            if (OVFMODE == 0) begin xv = 1; pop = 0; end else begin xv = 0; pop = 1; end
            check;
            if (r_ovf) ovf_cmp = ovf_cmp + 1;
        end
        if (sched_err != 0) begin $display("FAIL qfd_vm_rg6 BENCH schedule raised ovf in the main run (%0d)", sched_err); $fatal(1, "FAIL"); end
        if (pushes < CYCLES / 16 || pops < CYCLES / 16 || rowreads < CYCLES / 8 || suans < CYCLES / 8 || stalls < CYCLES / 8
            || moves < CYCLES / 2 || garbage < CYCLES / 32 || deep < CYCLES / 64 || xo_chg < pops / 2 || ro_chg < rowreads / 2
            || so_chg < suans / 2 || nonzero < 64 * CYCLES || ovf_cmp < 8 || ovf_cmp > 158) begin
            $display("FAIL qfd_vm_rg6 VACUOUS pushes=%0d pops=%0d row_reads=%0d su_answers=%0d stalls=%0d moves=%0d pop_garbage=%0d deep=%0d xo_chg=%0d ro_chg=%0d so_chg=%0d nonzero_words=%0d ovf_cycles=%0d",
                pushes, pops, rowreads, suans, stalls, moves, garbage, deep, xo_chg, ro_chg, so_chg, nonzero, ovf_cmp);
            $fatal(1, "FAIL");
        end
        if (errors != 0) begin
            $display("FAIL qfd_vm_rg6 LEAF_MUT=%0d ROW_MUT=%0d SU_MUT=%0d errors=%0d of %0d (xo %0d ro %0d so %0d ovf %0d)", LEAF_MUT, ROW_MUT, SU_MUT, errors, checks, e_xo, e_ro, e_so, e_ovf);
            $fatal(1, "FAIL");
        end
        $display("PASS qfd_vm_rg6 DEPTH=%0d LAW=%0d DEPTHS=%0d LAWS=%0d SEED=%0d OVFMODE=%0d exact %0d checks: pushes=%0d pops=%0d row_reads=%0d su_answers=%0d stalls=%0d pop_garbage=%0d deep=%0d xo_chg=%0d ro_chg=%0d so_chg=%0d nonzero_words=%0d ovf_cycles=%0d",
            DEPTH, LAW, DEPTHS, LAWS, SEED, OVFMODE, checks, pushes, pops, rowreads, suans, stalls, garbage, deep, xo_chg, ro_chg, so_chg, nonzero, ovf_cmp);
            $display("region lanes segments=1091 stage_bits=42024 checks=%0d nonzero=%0d",lane_checks,lane_nonzero);
            if (lane_checks < 1000 || lane_nonzero < 100) $fatal(1,"lane coverage vacuous");
            $finish;
    end
endmodule
