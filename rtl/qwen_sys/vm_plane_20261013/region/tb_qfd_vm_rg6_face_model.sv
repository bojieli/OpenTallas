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
module tb_qfd_vm_rg6_face_model;
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
    ot_qfd_vm_rg6_face_model #(.MUT(MUT)) candidate (.face_clk(clk), .ck_c0(clk), .ck_c1(clk), .ck_c2(clk), .ck_c3(clk), .ck_c4(clk), .ck_c5(clk), .ck_c6(clk), .ck_c7(clk), .ck_c8(clk), .ck_c9(clk), .ck_c10(clk), .ck_c11(clk), .ck_c12(clk), .ck_c13(clk), .ck_c14(clk), .ck_c15(clk), .ck_c16(clk), .ck_c17(clk), .ck_c18(clk), .ck_c19(clk), .ck_c20(clk), .ck_c21(clk), .ck_c22(clk), .ck_c23(clk), .ck_c24(clk), .ck_c25(clk), .ck_c26(clk), .ck_c27(clk), .ck_c28(clk), .ck_c29(clk), .ck_c30(clk), .ck_c31(clk), .ck_c32(clk), .ck_c33(clk), .ck_c34(clk), .ck_c35(clk), .ck_c36(clk), .ck_c37(clk), .ck_c38(clk), .ck_c39(clk), .ck_c40(clk), .ck_c41(clk), .ck_c42(clk), .ck_c43(clk), .ck_c44(clk), .ck_c45(clk), .ck_c46(clk), .ck_c47(clk), .ck_c48(clk), .ck_c49(clk), .ck_c50(clk), .ck_c51(clk), .ck_c52(clk), .ck_c53(clk), .ck_c54(clk), .ck_c55(clk), .ck_c56(clk), .ck_c57(clk), .ck_c58(clk), .ck_c59(clk), .ck_c60(clk), .ck_c61(clk), .ck_c62(clk), .ck_c63(clk), .ck_c64(clk), .ck_c65(clk), .ck_c66(clk), .ck_c67(clk), .ck_c68(clk), .ck_c69(clk), .ck_c70(clk), .ck_c71(clk), .ck_t0(clk), .ck_t1(clk), .ck_t2(clk), .ck_t3(clk), .ck_t4(clk), .ck_t5(clk), .ck_t6(clk), .ck_t7(clk), .ck_t8(clk), .ck_t9(clk), .ck_t10(clk), .ck_t11(clk), .ck_t12(clk), .ck_t13(clk), .ck_t14(clk), .ck_t15(clk), .ck_t16(clk), .ck_t17(clk), .ck_t18(clk), .ck_t19(clk), .ck_t20(clk), .ck_t21(clk), .ck_t22(clk), .ck_t23(clk), .ck_t24(clk), .ck_t25(clk), .ck_t26(clk), .ck_t27(clk), .ck_t28(clk), .ck_t29(clk), .ck_t30(clk), .ck_t31(clk), .ck_t32(clk), .ck_t33(clk), .ck_t34(clk), .ck_t35(clk), .ck_t36(clk), .ck_t37(clk), .ck_t38(clk), .ck_t39(clk), .ck_t40(clk), .ck_t41(clk), .ck_t42(clk), .ck_t43(clk), .ck_t44(clk), .ck_t45(clk), .ck_t46(clk), .ck_t47(clk), .ck_t48(clk), .ck_t49(clk), .ck_t50(clk), .ck_t51(clk), .ck_t52(clk), .ck_t53(clk), .ck_t54(clk), .ck_t55(clk), .ck_t56(clk), .ck_t57(clk), .ck_t58(clk), .ck_t59(clk), .ck_t60(clk), .ck_t61(clk), .ck_t62(clk), .ck_t63(clk), .ck_t64(clk), .ck_t65(clk), .ck_t66(clk), .ck_t67(clk), .ck_t68(clk), .ck_t69(clk), .ck_t70(clk), .ck_t71(clk), .ck_t72(clk), .ck_t73(clk), .ck_t74(clk), .ck_t75(clk), .ck_t76(clk), .re_b0(re[0 +: 1]), .re_b1(re[1 +: 1]), .re_b2(re[2 +: 1]), .re_b3(re[3 +: 1]), .re_b4(re[4 +: 1]), .re_b5(re[5 +: 1]), .re_b6(re[6 +: 1]), .re_b7(re[7 +: 1]), .ra_b0(ra[0 +: 8]), .ra_b1(ra[8 +: 8]), .ra_b2(ra[16 +: 8]), .ra_b3(ra[24 +: 8]), .ra_b4(ra[32 +: 8]), .ra_b5(ra[40 +: 8]), .ra_b6(ra[48 +: 8]), .ra_b7(ra[56 +: 8]), .we_b0(we[0 +: 1]), .we_b1(we[1 +: 1]), .we_b2(we[2 +: 1]), .we_b3(we[3 +: 1]), .we_b4(we[4 +: 1]), .we_b5(we[5 +: 1]), .we_b6(we[6 +: 1]), .we_b7(we[7 +: 1]), .wl_b0(wl[0 +: 8]), .wl_b1(wl[8 +: 8]), .wl_b2(wl[16 +: 8]), .wl_b3(wl[24 +: 8]), .wl_b4(wl[32 +: 8]), .wl_b5(wl[40 +: 8]), .wl_b6(wl[48 +: 8]), .wl_b7(wl[56 +: 8]), .wm_b0(wm[0 +: 16]), .wm_b1(wm[16 +: 16]), .wm_b2(wm[32 +: 16]), .wm_b3(wm[48 +: 16]), .wm_b4(wm[64 +: 16]), .wm_b5(wm[80 +: 16]), .wm_b6(wm[96 +: 16]), .wm_b7(wm[112 +: 16]), .wd_b0(wd[0 +: 512]), .wd_b1(wd[512 +: 512]), .wd_b2(wd[1024 +: 512]), .wd_b3(wd[1536 +: 512]), .wd_b4(wd[2048 +: 512]), .wd_b5(wd[2560 +: 512]), .wd_b6(wd[3072 +: 512]), .wd_b7(wd[3584 +: 512]), .sre_s0(sre[0 +: 1]), .sre_s1(sre[1 +: 1]), .sre_s2(sre[2 +: 1]), .sre_s3(sre[3 +: 1]), .sre_s4(sre[4 +: 1]), .sre_s5(sre[5 +: 1]), .sra_s0(sra[0 +: 10]), .sra_s1(sra[10 +: 10]), .sra_s2(sra[20 +: 10]), .sra_s3(sra[30 +: 10]), .sra_s4(sra[40 +: 10]), .sra_s5(sra[50 +: 10]), .rst_b0(rst_n), .rst_b1(rst_n), .rst_b2(rst_n), .rst_b3(rst_n), .rst_b4(rst_n), .rst_b5(rst_n), .rst_b6(rst_n), .rst_b7(rst_n), .rst_s0(rst_n), .rst_s1(rst_n), .rst_s2(rst_n), .rst_s3(rst_n), .rst_s4(rst_n), .rst_s5(rst_n), .rst_r0(rst_n), .rst_r1(rst_n), .rst_r2(rst_n), .me_b0(me_in), .me_b1(me_in), .me_b2(me_in), .me_b3(me_in), .me_b4(me_in), .me_b5(me_in), .me_b6(me_in), .me_b7(me_in), .me_r2(me_in), .me_f0(me_in), .me_f1(me_in), .me_f2(me_in), .me_f3(me_in), .me_f4(me_in), .me_f5(me_in), .me_f6(me_in), .me_f7(me_in), .me_f8(me_in), .me_f9(me_in), .me_f10(me_in), .me_f11(me_in), .me_f12(me_in), .me_f13(me_in), .me_f14(me_in), .me_f15(me_in), .xv_b0(xv), .xv_b1(xv), .xv_b2(xv), .xv_b3(xv), .xv_b4(xv), .xv_b5(xv), .xv_b6(xv), .xv_b7(xv), .xv_r2(xv), .pop_b0(pop), .pop_b1(pop), .pop_b2(pop), .pop_b3(pop), .pop_b4(pop), .pop_b5(pop), .pop_b6(pop), .pop_b7(pop), .pop_r2(pop), .sv_s0(sv[0 +: 1]), .sv_s1(sv[0 +: 1]), .sv_s2(sv[1 +: 1]), .sv_s3(sv[1 +: 1]), .sv_s4(sv[2 +: 1]), .sv_s5(sv[2 +: 1]), .swe_s0(swe[0 +: 1]), .swe_s1(swe[1 +: 1]), .swe_s2(swe[0 +: 1]), .swe_s3(swe[1 +: 1]), .swe_s4(swe[0 +: 1]), .swe_s5(swe[1 +: 1]), .swl_s0(swl[0 +: 10]), .swl_s1(swl[10 +: 10]), .swl_s2(swl[0 +: 10]), .swl_s3(swl[10 +: 10]), .swl_s4(swl[0 +: 10]), .swl_s5(swl[10 +: 10]), .swm_s0(swm[0 +: 16]), .swm_s1(swm[16 +: 16]), .swm_s2(swm[0 +: 16]), .swm_s3(swm[16 +: 16]), .swm_s4(swm[0 +: 16]), .swm_s5(swm[16 +: 16]), .swd_s0(swd[0 +: 512]), .swd_s1(swd[512 +: 512]), .swd_s2(swd[0 +: 512]), .swd_s3(swd[512 +: 512]), .swd_s4(swd[0 +: 512]), .swd_s5(swd[512 +: 512]), .rq_r2(rq), .rqb_r2(rqb), .rqb_r0(rqb[1:0]), .rqb_r1(rqb[1:0]), .me_vm_g6_sW_0(me_in), .me_vm_g6_sW_1(me_in), .me_vm_g6_sW_2(me_in), .me_vm_g6_sW_3(me_in), .me_vm_g6_sW_4(me_in), .me_vm_g6_sW_5(me_in), .me_vm_g6_sW_6(me_in), .me_vm_g6_sW_7(me_in), .me_vm_g6_sW_8(me_in), .me_vm_g6_sW_9(me_in), .me_vm_g6_sA_0(me_in), .me_vm_g6_sA_1(me_in), .me_vm_g6_sA_2(me_in), .me_vm_g6_sA_3(me_in), .me_vm_g6_sA_4(me_in), .me_vm_g6_sA_5(me_in), .me_vm_g6_sA_6(me_in), .me_vm_g6_sA_7(me_in), .me_vm_g6_sA_8(me_in), .me_vm_g6_sA_9(me_in), .me_vm_g6_sB_0(me_in), .me_vm_g6_sB_1(me_in), .me_vm_g6_sB_2(me_in), .me_vm_g6_sB_3(me_in), .me_vm_g6_sB_4(me_in), .me_vm_g6_sB_5(me_in), .me_vm_g6_sB_6(me_in), .me_vm_g6_sB_7(me_in), .me_vm_g6_sB_8(me_in), .me_vm_g6_sB_9(me_in), .ro(ro), .ovf(ovf), .so_s0(so[0 +: 1024]), .so_s1(so[1024 +: 1024]), .so_s2(so[2048 +: 1024]), .d_w(d_w), .d_e(d_e), .q_w(q_w), .q_e(q_e), .q_s(q_s));
    assign xo = candidate.u_base.xo;
    reg face_ref_me_in=0;
    always @(posedge clk) face_ref_me_in <= me_in;
    reg [7:0] face_ref_re=0;
    always @(posedge clk) face_ref_re <= re;
    reg [63:0] face_ref_ra=0;
    always @(posedge clk) face_ref_ra <= ra;
    reg [7:0] face_ref_we=0;
    always @(posedge clk) face_ref_we <= we;
    reg [63:0] face_ref_wl=0;
    always @(posedge clk) face_ref_wl <= wl;
    reg [127:0] face_ref_wm=0;
    always @(posedge clk) face_ref_wm <= wm;
    reg [4095:0] face_ref_wd=0;
    always @(posedge clk) face_ref_wd <= wd;
    reg face_ref_xv=0;
    always @(posedge clk) face_ref_xv <= xv;
    reg face_ref_rq=0;
    always @(posedge clk) face_ref_rq <= rq;
    reg [2:0] face_ref_rqb=0;
    always @(posedge clk) face_ref_rqb <= rqb;
    reg [5:0] face_ref_sre=0;
    always @(posedge clk) face_ref_sre <= sre;
    reg [59:0] face_ref_sra=0;
    always @(posedge clk) face_ref_sra <= sra;
    reg [2:0] face_ref_sv=0;
    always @(posedge clk) face_ref_sv <= sv;
    reg [1:0] face_ref_swe=0;
    always @(posedge clk) face_ref_swe <= swe;
    reg [19:0] face_ref_swl=0;
    always @(posedge clk) face_ref_swl <= swl;
    reg [31:0] face_ref_swm=0;
    always @(posedge clk) face_ref_swm <= swm;
    reg [1023:0] face_ref_swd=0;
    always @(posedge clk) face_ref_swd <= swd;
    reg face_ref_pop=0;
    always @(posedge clk) face_ref_pop <= pop;
    wire [511:0] raw_r_ro;
    reg [511:0] delay_r_ro=0;
    always @(posedge clk) delay_r_ro <= raw_r_ro;
    assign r_ro = delay_r_ro;
    wire [3071:0] raw_r_so;
    reg [3071:0] delay_r_so=0;
    always @(posedge clk) delay_r_so <= raw_r_so;
    assign r_so = delay_r_so;
    wire raw_r_ovf;
    reg delay_r_ovf=0;
    always @(posedge clk) delay_r_ovf <= raw_r_ovf;
    assign r_ovf = delay_r_ovf;
    ot_qfd_vm_region_quarter #(.DEPTH(DEPTH), .LAW(LAW), .DEPTHS(DEPTHS), .LAWS(LAWS), .USE_MACRO(0), .NPP(NPP), .MEREG(1)) reference (
        .clk(clk), .rst_n(rst_n), .me_in(face_ref_me_in), .re(face_ref_re), .ra(face_ref_ra), .we(face_ref_we), .wl(face_ref_wl), .wm(face_ref_wm), .wd(face_ref_wd),
        .xv(face_ref_xv), .rq(face_ref_rq), .rqb(face_ref_rqb), .sre(face_ref_sre), .sra(face_ref_sra), .sv(face_ref_sv), .swe(face_ref_swe), .swl(face_ref_swl), .swm(face_ref_swm), .swd(face_ref_swd),
        .pop(face_ref_pop), .xo(r_xo), .ro(raw_r_ro), .so(raw_r_so), .ovf(raw_r_ovf));
    reg lane_me_prev=0;
    integer lane_checks=0,lane_nonzero=0;
    always @(posedge clk) lane_me_prev <= face_ref_me_in;
    reg [39:0] face_ref0=0;
    always @(posedge clk) if(lane_me_prev) face_ref0 <= {face_ref0[31:0], d_e[0 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref0[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[0 +: 8] !== face_ref0[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 0"); end end end
    reg [39:0] face_ref1=0;
    always @(posedge clk) if(lane_me_prev) face_ref1 <= {face_ref1[31:0], d_e[8 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[8 +: 8] !== face_ref1[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1"); end end end
    reg [39:0] face_ref2=0;
    always @(posedge clk) if(lane_me_prev) face_ref2 <= {face_ref2[31:0], d_e[16 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref2[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[16 +: 8] !== face_ref2[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 2"); end end end
    reg [39:0] face_ref3=0;
    always @(posedge clk) if(lane_me_prev) face_ref3 <= {face_ref3[31:0], d_e[24 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref3[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[24 +: 8] !== face_ref3[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 3"); end end end
    reg [31:0] face_ref4=0;
    always @(posedge clk) if(lane_me_prev) face_ref4 <= {face_ref4[23:0], r_xo[3848 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref4[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[32 +: 8] !== face_ref4[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 4"); end end end
    reg [39:0] face_ref5=0;
    always @(posedge clk) if(lane_me_prev) face_ref5 <= {face_ref5[31:0], r_xo[3856 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref5[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[40 +: 8] !== face_ref5[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 5"); end end end
    reg [55:0] face_ref6=0;
    always @(posedge clk) if(lane_me_prev) face_ref6 <= {face_ref6[47:0], d_w[0 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref6[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[0 +: 8] !== face_ref6[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 6"); end end end
    reg [23:0] face_ref7=0;
    always @(posedge clk) if(lane_me_prev) face_ref7 <= {face_ref7[15:0], r_xo[2816 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref7[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[48 +: 8] !== face_ref7[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 7"); end end end
    reg [23:0] face_ref8=0;
    always @(posedge clk) if(lane_me_prev) face_ref8 <= {face_ref8[15:0], r_xo[2560 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref8[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[56 +: 8] !== face_ref8[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 8"); end end end
    reg [39:0] face_ref9=0;
    always @(posedge clk) if(lane_me_prev) face_ref9 <= {face_ref9[31:0], d_e[32 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref9[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[64 +: 8] !== face_ref9[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 9"); end end end
    reg [31:0] face_ref10=0;
    always @(posedge clk) if(lane_me_prev) face_ref10 <= {face_ref10[23:0], r_xo[3584 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref10[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[72 +: 8] !== face_ref10[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 10"); end end end
    reg [39:0] face_ref11=0;
    always @(posedge clk) if(lane_me_prev) face_ref11 <= {face_ref11[31:0], d_e[40 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref11[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[80 +: 8] !== face_ref11[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 11"); end end end
    reg [39:0] face_ref12=0;
    always @(posedge clk) if(lane_me_prev) face_ref12 <= {face_ref12[31:0], d_e[48 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref12[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[88 +: 8] !== face_ref12[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 12"); end end end
    reg [39:0] face_ref13=0;
    always @(posedge clk) if(lane_me_prev) face_ref13 <= {face_ref13[31:0], d_e[56 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref13[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[96 +: 8] !== face_ref13[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 13"); end end end
    reg [39:0] face_ref14=0;
    always @(posedge clk) if(lane_me_prev) face_ref14 <= {face_ref14[31:0], d_e[64 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref14[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[104 +: 8] !== face_ref14[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 14"); end end end
    reg [23:0] face_ref15=0;
    always @(posedge clk) if(lane_me_prev) face_ref15 <= {face_ref15[15:0], r_xo[2824 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref15[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[112 +: 8] !== face_ref15[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 15"); end end end
    reg [15:0] face_ref16=0;
    always @(posedge clk) if(lane_me_prev) face_ref16 <= {face_ref16[7:0], r_xo[512 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref16[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[120 +: 8] !== face_ref16[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 16"); end end end
    reg [23:0] face_ref17=0;
    always @(posedge clk) if(lane_me_prev) face_ref17 <= {face_ref17[15:0], r_xo[3328 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref17[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[128 +: 8] !== face_ref17[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 17"); end end end
    reg [31:0] face_ref18=0;
    always @(posedge clk) if(lane_me_prev) face_ref18 <= {face_ref18[23:0], r_xo[776 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref18[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[136 +: 8] !== face_ref18[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 18"); end end end
    reg [15:0] face_ref19=0;
    always @(posedge clk) if(lane_me_prev) face_ref19 <= {face_ref19[7:0], r_xo[1536 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref19[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[144 +: 8] !== face_ref19[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 19"); end end end
    reg [39:0] face_ref20=0;
    always @(posedge clk) if(lane_me_prev) face_ref20 <= {face_ref20[31:0], d_e[72 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref20[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[152 +: 8] !== face_ref20[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 20"); end end end
    reg [39:0] face_ref21=0;
    always @(posedge clk) if(lane_me_prev) face_ref21 <= {face_ref21[31:0], d_e[80 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref21[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[160 +: 8] !== face_ref21[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 21"); end end end
    reg [39:0] face_ref22=0;
    always @(posedge clk) if(lane_me_prev) face_ref22 <= {face_ref22[31:0], d_e[88 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref22[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[168 +: 8] !== face_ref22[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 22"); end end end
    reg [39:0] face_ref23=0;
    always @(posedge clk) if(lane_me_prev) face_ref23 <= {face_ref23[31:0], d_e[96 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref23[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[176 +: 8] !== face_ref23[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 23"); end end end
    reg [39:0] face_ref24=0;
    always @(posedge clk) if(lane_me_prev) face_ref24 <= {face_ref24[31:0], d_e[104 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref24[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[184 +: 8] !== face_ref24[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 24"); end end end
    reg [39:0] face_ref25=0;
    always @(posedge clk) if(lane_me_prev) face_ref25 <= {face_ref25[31:0], d_e[112 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref25[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[192 +: 8] !== face_ref25[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 25"); end end end
    reg [39:0] face_ref26=0;
    always @(posedge clk) if(lane_me_prev) face_ref26 <= {face_ref26[31:0], d_e[120 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref26[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[200 +: 8] !== face_ref26[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 26"); end end end
    reg [39:0] face_ref27=0;
    always @(posedge clk) if(lane_me_prev) face_ref27 <= {face_ref27[31:0], d_e[128 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref27[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[208 +: 8] !== face_ref27[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 27"); end end end
    reg [39:0] face_ref28=0;
    always @(posedge clk) if(lane_me_prev) face_ref28 <= {face_ref28[31:0], d_e[136 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref28[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[216 +: 8] !== face_ref28[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 28"); end end end
    reg [39:0] face_ref29=0;
    always @(posedge clk) if(lane_me_prev) face_ref29 <= {face_ref29[31:0], d_e[144 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref29[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[224 +: 8] !== face_ref29[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 29"); end end end
    reg [39:0] face_ref30=0;
    always @(posedge clk) if(lane_me_prev) face_ref30 <= {face_ref30[31:0], d_e[152 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref30[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[232 +: 8] !== face_ref30[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 30"); end end end
    reg [39:0] face_ref31=0;
    always @(posedge clk) if(lane_me_prev) face_ref31 <= {face_ref31[31:0], d_e[160 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref31[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[240 +: 8] !== face_ref31[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 31"); end end end
    reg [39:0] face_ref32=0;
    always @(posedge clk) if(lane_me_prev) face_ref32 <= {face_ref32[31:0], d_e[168 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref32[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[248 +: 8] !== face_ref32[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 32"); end end end
    reg [39:0] face_ref33=0;
    always @(posedge clk) if(lane_me_prev) face_ref33 <= {face_ref33[31:0], d_e[176 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref33[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[256 +: 8] !== face_ref33[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 33"); end end end
    reg [39:0] face_ref34=0;
    always @(posedge clk) if(lane_me_prev) face_ref34 <= {face_ref34[31:0], d_e[184 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref34[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[264 +: 8] !== face_ref34[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 34"); end end end
    reg [39:0] face_ref35=0;
    always @(posedge clk) if(lane_me_prev) face_ref35 <= {face_ref35[31:0], d_e[192 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref35[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[272 +: 8] !== face_ref35[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 35"); end end end
    reg [23:0] face_ref36=0;
    always @(posedge clk) if(lane_me_prev) face_ref36 <= {face_ref36[15:0], r_xo[1800 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref36[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[280 +: 8] !== face_ref36[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 36"); end end end
    reg [47:0] face_ref37=0;
    always @(posedge clk) if(lane_me_prev) face_ref37 <= {face_ref37[39:0], r_xo[1808 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref37[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[288 +: 8] !== face_ref37[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 37"); end end end
    reg [39:0] face_ref38=0;
    always @(posedge clk) if(lane_me_prev) face_ref38 <= {face_ref38[31:0], d_w[8 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref38[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[8 +: 8] !== face_ref38[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 38"); end end end
    reg [39:0] face_ref39=0;
    always @(posedge clk) if(lane_me_prev) face_ref39 <= {face_ref39[31:0], d_w[16 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref39[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[16 +: 8] !== face_ref39[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 39"); end end end
    reg [39:0] face_ref40=0;
    always @(posedge clk) if(lane_me_prev) face_ref40 <= {face_ref40[31:0], d_w[24 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref40[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[24 +: 8] !== face_ref40[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 40"); end end end
    reg [39:0] face_ref41=0;
    always @(posedge clk) if(lane_me_prev) face_ref41 <= {face_ref41[31:0], d_w[32 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref41[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[32 +: 8] !== face_ref41[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 41"); end end end
    reg [39:0] face_ref42=0;
    always @(posedge clk) if(lane_me_prev) face_ref42 <= {face_ref42[31:0], d_w[40 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref42[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[40 +: 8] !== face_ref42[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 42"); end end end
    reg [31:0] face_ref43=0;
    always @(posedge clk) if(lane_me_prev) face_ref43 <= {face_ref43[23:0], d_w[48 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref43[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[0 +: 8] !== face_ref43[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 43"); end end end
    reg [39:0] face_ref44=0;
    always @(posedge clk) if(lane_me_prev) face_ref44 <= {face_ref44[31:0], d_w[56 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref44[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[8 +: 8] !== face_ref44[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 44"); end end end
    reg [23:0] face_ref45=0;
    always @(posedge clk) if(lane_me_prev) face_ref45 <= {face_ref45[15:0], d_w[64 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref45[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[16 +: 8] !== face_ref45[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 45"); end end end
    reg [39:0] face_ref46=0;
    always @(posedge clk) if(lane_me_prev) face_ref46 <= {face_ref46[31:0], d_w[72 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref46[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[48 +: 8] !== face_ref46[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 46"); end end end
    reg [39:0] face_ref47=0;
    always @(posedge clk) if(lane_me_prev) face_ref47 <= {face_ref47[31:0], d_w[80 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref47[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[56 +: 8] !== face_ref47[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 47"); end end end
    reg [39:0] face_ref48=0;
    always @(posedge clk) if(lane_me_prev) face_ref48 <= {face_ref48[31:0], d_w[88 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref48[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[64 +: 8] !== face_ref48[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 48"); end end end
    reg [39:0] face_ref49=0;
    always @(posedge clk) if(lane_me_prev) face_ref49 <= {face_ref49[31:0], d_w[96 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref49[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[72 +: 8] !== face_ref49[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 49"); end end end
    reg [39:0] face_ref50=0;
    always @(posedge clk) if(lane_me_prev) face_ref50 <= {face_ref50[31:0], d_w[104 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref50[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[80 +: 8] !== face_ref50[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 50"); end end end
    reg [39:0] face_ref51=0;
    always @(posedge clk) if(lane_me_prev) face_ref51 <= {face_ref51[31:0], d_w[112 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref51[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[88 +: 8] !== face_ref51[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 51"); end end end
    reg [47:0] face_ref52=0;
    always @(posedge clk) if(lane_me_prev) face_ref52 <= {face_ref52[39:0], d_w[120 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref52[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[24 +: 8] !== face_ref52[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 52"); end end end
    reg [39:0] face_ref53=0;
    always @(posedge clk) if(lane_me_prev) face_ref53 <= {face_ref53[31:0], d_w[128 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref53[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[32 +: 8] !== face_ref53[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 53"); end end end
    reg [39:0] face_ref54=0;
    always @(posedge clk) if(lane_me_prev) face_ref54 <= {face_ref54[31:0], d_w[136 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref54[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[40 +: 8] !== face_ref54[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 54"); end end end
    reg [31:0] face_ref55=0;
    always @(posedge clk) if(lane_me_prev) face_ref55 <= {face_ref55[23:0], d_w[144 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref55[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[48 +: 8] !== face_ref55[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 55"); end end end
    reg [31:0] face_ref56=0;
    always @(posedge clk) if(lane_me_prev) face_ref56 <= {face_ref56[23:0], d_w[152 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref56[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[56 +: 8] !== face_ref56[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 56"); end end end
    reg [23:0] face_ref57=0;
    always @(posedge clk) if(lane_me_prev) face_ref57 <= {face_ref57[15:0], d_w[160 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref57[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[64 +: 8] !== face_ref57[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 57"); end end end
    reg [23:0] face_ref58=0;
    always @(posedge clk) if(lane_me_prev) face_ref58 <= {face_ref58[15:0], d_w[168 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref58[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[72 +: 8] !== face_ref58[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 58"); end end end
    reg [39:0] face_ref59=0;
    always @(posedge clk) if(lane_me_prev) face_ref59 <= {face_ref59[31:0], d_w[176 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref59[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[96 +: 8] !== face_ref59[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 59"); end end end
    reg [39:0] face_ref60=0;
    always @(posedge clk) if(lane_me_prev) face_ref60 <= {face_ref60[31:0], d_w[184 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref60[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[104 +: 8] !== face_ref60[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 60"); end end end
    reg [39:0] face_ref61=0;
    always @(posedge clk) if(lane_me_prev) face_ref61 <= {face_ref61[31:0], d_w[192 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref61[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[112 +: 8] !== face_ref61[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 61"); end end end
    reg [39:0] face_ref62=0;
    always @(posedge clk) if(lane_me_prev) face_ref62 <= {face_ref62[31:0], d_w[200 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref62[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[120 +: 8] !== face_ref62[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 62"); end end end
    reg [39:0] face_ref63=0;
    always @(posedge clk) if(lane_me_prev) face_ref63 <= {face_ref63[31:0], d_w[208 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref63[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[128 +: 8] !== face_ref63[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 63"); end end end
    reg [39:0] face_ref64=0;
    always @(posedge clk) if(lane_me_prev) face_ref64 <= {face_ref64[31:0], d_w[216 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref64[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[136 +: 8] !== face_ref64[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 64"); end end end
    reg [39:0] face_ref65=0;
    always @(posedge clk) if(lane_me_prev) face_ref65 <= {face_ref65[31:0], d_w[224 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref65[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[144 +: 8] !== face_ref65[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 65"); end end end
    reg [39:0] face_ref66=0;
    always @(posedge clk) if(lane_me_prev) face_ref66 <= {face_ref66[31:0], d_w[232 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref66[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[152 +: 8] !== face_ref66[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 66"); end end end
    reg [39:0] face_ref67=0;
    always @(posedge clk) if(lane_me_prev) face_ref67 <= {face_ref67[31:0], d_w[240 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref67[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[160 +: 8] !== face_ref67[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 67"); end end end
    reg [47:0] face_ref68=0;
    always @(posedge clk) if(lane_me_prev) face_ref68 <= {face_ref68[39:0], d_w[248 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref68[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[80 +: 8] !== face_ref68[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 68"); end end end
    reg [39:0] face_ref69=0;
    always @(posedge clk) if(lane_me_prev) face_ref69 <= {face_ref69[31:0], d_w[256 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref69[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[88 +: 8] !== face_ref69[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 69"); end end end
    reg [39:0] face_ref70=0;
    always @(posedge clk) if(lane_me_prev) face_ref70 <= {face_ref70[31:0], d_w[264 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref70[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[96 +: 8] !== face_ref70[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 70"); end end end
    reg [39:0] face_ref71=0;
    always @(posedge clk) if(lane_me_prev) face_ref71 <= {face_ref71[31:0], d_w[272 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref71[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[104 +: 8] !== face_ref71[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 71"); end end end
    reg [63:0] face_ref72=0;
    always @(posedge clk) if(lane_me_prev) face_ref72 <= {face_ref72[55:0], d_w[280 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref72[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[112 +: 8] !== face_ref72[56 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 72"); end end end
    reg [31:0] face_ref73=0;
    always @(posedge clk) if(lane_me_prev) face_ref73 <= {face_ref73[23:0], d_w[288 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref73[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[120 +: 8] !== face_ref73[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 73"); end end end
    reg [39:0] face_ref74=0;
    always @(posedge clk) if(lane_me_prev) face_ref74 <= {face_ref74[31:0], d_w[296 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref74[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[128 +: 8] !== face_ref74[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 74"); end end end
    reg [31:0] face_ref75=0;
    always @(posedge clk) if(lane_me_prev) face_ref75 <= {face_ref75[23:0], d_w[304 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref75[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[136 +: 8] !== face_ref75[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 75"); end end end
    reg [31:0] face_ref76=0;
    always @(posedge clk) if(lane_me_prev) face_ref76 <= {face_ref76[23:0], d_w[312 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref76[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[144 +: 8] !== face_ref76[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 76"); end end end
    reg [31:0] face_ref77=0;
    always @(posedge clk) if(lane_me_prev) face_ref77 <= {face_ref77[23:0], d_w[320 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref77[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[152 +: 8] !== face_ref77[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 77"); end end end
    reg [31:0] face_ref78=0;
    always @(posedge clk) if(lane_me_prev) face_ref78 <= {face_ref78[23:0], d_w[328 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref78[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[160 +: 8] !== face_ref78[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 78"); end end end
    reg [31:0] face_ref79=0;
    always @(posedge clk) if(lane_me_prev) face_ref79 <= {face_ref79[23:0], d_w[336 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref79[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[168 +: 8] !== face_ref79[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 79"); end end end
    reg [47:0] face_ref80=0;
    always @(posedge clk) if(lane_me_prev) face_ref80 <= {face_ref80[39:0], d_w[344 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref80[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[176 +: 8] !== face_ref80[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 80"); end end end
    reg [39:0] face_ref81=0;
    always @(posedge clk) if(lane_me_prev) face_ref81 <= {face_ref81[31:0], d_w[352 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref81[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[168 +: 8] !== face_ref81[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 81"); end end end
    reg [39:0] face_ref82=0;
    always @(posedge clk) if(lane_me_prev) face_ref82 <= {face_ref82[31:0], d_w[360 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref82[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[176 +: 8] !== face_ref82[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 82"); end end end
    reg [39:0] face_ref83=0;
    always @(posedge clk) if(lane_me_prev) face_ref83 <= {face_ref83[31:0], d_w[368 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref83[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[184 +: 8] !== face_ref83[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 83"); end end end
    reg [39:0] face_ref84=0;
    always @(posedge clk) if(lane_me_prev) face_ref84 <= {face_ref84[31:0], d_w[376 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref84[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[192 +: 8] !== face_ref84[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 84"); end end end
    reg [39:0] face_ref85=0;
    always @(posedge clk) if(lane_me_prev) face_ref85 <= {face_ref85[31:0], d_w[384 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref85[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[200 +: 8] !== face_ref85[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 85"); end end end
    reg [39:0] face_ref86=0;
    always @(posedge clk) if(lane_me_prev) face_ref86 <= {face_ref86[31:0], d_w[392 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref86[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[208 +: 8] !== face_ref86[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 86"); end end end
    reg [39:0] face_ref87=0;
    always @(posedge clk) if(lane_me_prev) face_ref87 <= {face_ref87[31:0], d_w[400 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref87[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[216 +: 8] !== face_ref87[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 87"); end end end
    reg [31:0] face_ref88=0;
    always @(posedge clk) if(lane_me_prev) face_ref88 <= {face_ref88[23:0], r_xo[3840 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref88[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[296 +: 8] !== face_ref88[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 88"); end end end
    reg [39:0] face_ref89=0;
    always @(posedge clk) if(lane_me_prev) face_ref89 <= {face_ref89[31:0], d_w[408 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref89[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[184 +: 8] !== face_ref89[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 89"); end end end
    reg [47:0] face_ref90=0;
    always @(posedge clk) if(lane_me_prev) face_ref90 <= {face_ref90[39:0], d_w[416 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref90[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[192 +: 8] !== face_ref90[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 90"); end end end
    reg [23:0] face_ref91=0;
    always @(posedge clk) if(lane_me_prev) face_ref91 <= {face_ref91[15:0], r_xo[1792 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref91[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[304 +: 8] !== face_ref91[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 91"); end end end
    reg [47:0] face_ref92=0;
    always @(posedge clk) if(lane_me_prev) face_ref92 <= {face_ref92[39:0], d_w[424 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref92[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[200 +: 8] !== face_ref92[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 92"); end end end
    reg [23:0] face_ref93=0;
    always @(posedge clk) if(lane_me_prev) face_ref93 <= {face_ref93[15:0], r_xo[768 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref93[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[312 +: 8] !== face_ref93[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 93"); end end end
    reg [31:0] face_ref94=0;
    always @(posedge clk) if(lane_me_prev) face_ref94 <= {face_ref94[23:0], d_w[432 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref94[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[208 +: 8] !== face_ref94[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 94"); end end end
    reg [39:0] face_ref95=0;
    always @(posedge clk) if(lane_me_prev) face_ref95 <= {face_ref95[31:0], d_w[440 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref95[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[224 +: 8] !== face_ref95[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 95"); end end end
    reg [39:0] face_ref96=0;
    always @(posedge clk) if(lane_me_prev) face_ref96 <= {face_ref96[31:0], d_w[448 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref96[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[232 +: 8] !== face_ref96[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 96"); end end end
    reg [39:0] face_ref97=0;
    always @(posedge clk) if(lane_me_prev) face_ref97 <= {face_ref97[31:0], d_w[456 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref97[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[240 +: 8] !== face_ref97[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 97"); end end end
    reg [39:0] face_ref98=0;
    always @(posedge clk) if(lane_me_prev) face_ref98 <= {face_ref98[31:0], d_w[464 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref98[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[248 +: 8] !== face_ref98[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 98"); end end end
    reg [39:0] face_ref99=0;
    always @(posedge clk) if(lane_me_prev) face_ref99 <= {face_ref99[31:0], d_w[472 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref99[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[256 +: 8] !== face_ref99[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 99"); end end end
    reg [55:0] face_ref100=0;
    always @(posedge clk) if(lane_me_prev) face_ref100 <= {face_ref100[47:0], d_w[480 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref100[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[216 +: 8] !== face_ref100[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 100"); end end end
    reg [55:0] face_ref101=0;
    always @(posedge clk) if(lane_me_prev) face_ref101 <= {face_ref101[47:0], d_w[488 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref101[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[224 +: 8] !== face_ref101[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 101"); end end end
    reg [63:0] face_ref102=0;
    always @(posedge clk) if(lane_me_prev) face_ref102 <= {face_ref102[55:0], d_w[496 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref102[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[232 +: 8] !== face_ref102[56 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 102"); end end end
    reg [39:0] face_ref103=0;
    always @(posedge clk) if(lane_me_prev) face_ref103 <= {face_ref103[31:0], d_w[504 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref103[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[240 +: 8] !== face_ref103[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 103"); end end end
    reg [31:0] face_ref104=0;
    always @(posedge clk) if(lane_me_prev) face_ref104 <= {face_ref104[23:0], d_w[512 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref104[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[248 +: 8] !== face_ref104[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 104"); end end end
    reg [31:0] face_ref105=0;
    always @(posedge clk) if(lane_me_prev) face_ref105 <= {face_ref105[23:0], d_w[520 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref105[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[256 +: 8] !== face_ref105[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 105"); end end end
    reg [39:0] face_ref106=0;
    always @(posedge clk) if(lane_me_prev) face_ref106 <= {face_ref106[31:0], d_w[528 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref106[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[264 +: 8] !== face_ref106[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 106"); end end end
    reg [39:0] face_ref107=0;
    always @(posedge clk) if(lane_me_prev) face_ref107 <= {face_ref107[31:0], d_w[536 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref107[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[272 +: 8] !== face_ref107[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 107"); end end end
    reg [39:0] face_ref108=0;
    always @(posedge clk) if(lane_me_prev) face_ref108 <= {face_ref108[31:0], d_w[544 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref108[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[280 +: 8] !== face_ref108[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 108"); end end end
    reg [39:0] face_ref109=0;
    always @(posedge clk) if(lane_me_prev) face_ref109 <= {face_ref109[31:0], d_w[552 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref109[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[288 +: 8] !== face_ref109[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 109"); end end end
    reg [39:0] face_ref110=0;
    always @(posedge clk) if(lane_me_prev) face_ref110 <= {face_ref110[31:0], d_w[560 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref110[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[296 +: 8] !== face_ref110[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 110"); end end end
    reg [39:0] face_ref111=0;
    always @(posedge clk) if(lane_me_prev) face_ref111 <= {face_ref111[31:0], d_w[568 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref111[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[304 +: 8] !== face_ref111[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 111"); end end end
    reg [39:0] face_ref112=0;
    always @(posedge clk) if(lane_me_prev) face_ref112 <= {face_ref112[31:0], d_w[576 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref112[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[312 +: 8] !== face_ref112[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 112"); end end end
    reg [39:0] face_ref113=0;
    always @(posedge clk) if(lane_me_prev) face_ref113 <= {face_ref113[31:0], d_w[584 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref113[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[320 +: 8] !== face_ref113[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 113"); end end end
    reg [39:0] face_ref114=0;
    always @(posedge clk) if(lane_me_prev) face_ref114 <= {face_ref114[31:0], d_w[592 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref114[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[328 +: 8] !== face_ref114[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 114"); end end end
    reg [39:0] face_ref115=0;
    always @(posedge clk) if(lane_me_prev) face_ref115 <= {face_ref115[31:0], d_w[600 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref115[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[336 +: 8] !== face_ref115[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 115"); end end end
    reg [55:0] face_ref116=0;
    always @(posedge clk) if(lane_me_prev) face_ref116 <= {face_ref116[47:0], d_w[608 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref116[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[264 +: 8] !== face_ref116[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 116"); end end end
    reg [55:0] face_ref117=0;
    always @(posedge clk) if(lane_me_prev) face_ref117 <= {face_ref117[47:0], d_w[616 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref117[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[272 +: 8] !== face_ref117[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 117"); end end end
    reg [55:0] face_ref118=0;
    always @(posedge clk) if(lane_me_prev) face_ref118 <= {face_ref118[47:0], d_w[624 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref118[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[280 +: 8] !== face_ref118[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 118"); end end end
    reg [55:0] face_ref119=0;
    always @(posedge clk) if(lane_me_prev) face_ref119 <= {face_ref119[47:0], d_w[632 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref119[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[288 +: 8] !== face_ref119[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 119"); end end end
    reg [63:0] face_ref120=0;
    always @(posedge clk) if(lane_me_prev) face_ref120 <= {face_ref120[55:0], d_w[640 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref120[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[296 +: 8] !== face_ref120[56 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 120"); end end end
    reg [39:0] face_ref121=0;
    always @(posedge clk) if(lane_me_prev) face_ref121 <= {face_ref121[31:0], d_w[648 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref121[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[304 +: 8] !== face_ref121[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 121"); end end end
    reg [31:0] face_ref122=0;
    always @(posedge clk) if(lane_me_prev) face_ref122 <= {face_ref122[23:0], d_w[656 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref122[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[312 +: 8] !== face_ref122[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 122"); end end end
    reg [31:0] face_ref123=0;
    always @(posedge clk) if(lane_me_prev) face_ref123 <= {face_ref123[23:0], d_w[664 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref123[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[320 +: 8] !== face_ref123[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 123"); end end end
    reg [31:0] face_ref124=0;
    always @(posedge clk) if(lane_me_prev) face_ref124 <= {face_ref124[23:0], d_w[672 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref124[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[328 +: 8] !== face_ref124[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 124"); end end end
    reg [39:0] face_ref125=0;
    always @(posedge clk) if(lane_me_prev) face_ref125 <= {face_ref125[31:0], d_e[200 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref125[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[320 +: 8] !== face_ref125[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 125"); end end end
    reg [39:0] face_ref126=0;
    always @(posedge clk) if(lane_me_prev) face_ref126 <= {face_ref126[31:0], d_e[208 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref126[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[328 +: 8] !== face_ref126[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 126"); end end end
    reg [39:0] face_ref127=0;
    always @(posedge clk) if(lane_me_prev) face_ref127 <= {face_ref127[31:0], d_e[216 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref127[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[336 +: 8] !== face_ref127[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 127"); end end end
    reg [39:0] face_ref128=0;
    always @(posedge clk) if(lane_me_prev) face_ref128 <= {face_ref128[31:0], d_e[224 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref128[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[344 +: 8] !== face_ref128[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 128"); end end end
    reg [55:0] face_ref129=0;
    always @(posedge clk) if(lane_me_prev) face_ref129 <= {face_ref129[47:0], r_xo[3592 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref129[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[352 +: 8] !== face_ref129[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 129"); end end end
    reg [23:0] face_ref130=0;
    always @(posedge clk) if(lane_me_prev) face_ref130 <= {face_ref130[15:0], r_xo[3336 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref130[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[360 +: 8] !== face_ref130[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 130"); end end end
    reg [23:0] face_ref131=0;
    always @(posedge clk) if(lane_me_prev) face_ref131 <= {face_ref131[15:0], r_xo[1288 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref131[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[368 +: 8] !== face_ref131[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 131"); end end end
    reg [47:0] face_ref132=0;
    always @(posedge clk) if(lane_me_prev) face_ref132 <= {face_ref132[39:0], r_xo[1544 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref132[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[376 +: 8] !== face_ref132[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 132"); end end end
    reg [15:0] face_ref133=0;
    always @(posedge clk) if(lane_me_prev) face_ref133 <= {face_ref133[7:0], r_xo[1032 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref133[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[384 +: 8] !== face_ref133[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 133"); end end end
    reg [39:0] face_ref134=0;
    always @(posedge clk) if(lane_me_prev) face_ref134 <= {face_ref134[31:0], d_e[232 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref134[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[392 +: 8] !== face_ref134[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 134"); end end end
    reg [47:0] face_ref135=0;
    always @(posedge clk) if(lane_me_prev) face_ref135 <= {face_ref135[39:0], d_e[240 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref135[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[400 +: 8] !== face_ref135[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 135"); end end end
    reg [39:0] face_ref136=0;
    always @(posedge clk) if(lane_me_prev) face_ref136 <= {face_ref136[31:0], d_e[248 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref136[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[408 +: 8] !== face_ref136[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 136"); end end end
    reg [39:0] face_ref137=0;
    always @(posedge clk) if(lane_me_prev) face_ref137 <= {face_ref137[31:0], d_e[256 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref137[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[416 +: 8] !== face_ref137[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 137"); end end end
    reg [39:0] face_ref138=0;
    always @(posedge clk) if(lane_me_prev) face_ref138 <= {face_ref138[31:0], d_e[264 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref138[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[424 +: 8] !== face_ref138[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 138"); end end end
    reg [39:0] face_ref139=0;
    always @(posedge clk) if(lane_me_prev) face_ref139 <= {face_ref139[31:0], d_e[272 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref139[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[432 +: 8] !== face_ref139[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 139"); end end end
    reg [39:0] face_ref140=0;
    always @(posedge clk) if(lane_me_prev) face_ref140 <= {face_ref140[31:0], d_e[280 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref140[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[440 +: 8] !== face_ref140[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 140"); end end end
    reg [39:0] face_ref141=0;
    always @(posedge clk) if(lane_me_prev) face_ref141 <= {face_ref141[31:0], d_e[288 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref141[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[448 +: 8] !== face_ref141[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 141"); end end end
    reg [39:0] face_ref142=0;
    always @(posedge clk) if(lane_me_prev) face_ref142 <= {face_ref142[31:0], d_e[296 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref142[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[456 +: 8] !== face_ref142[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 142"); end end end
    reg [39:0] face_ref143=0;
    always @(posedge clk) if(lane_me_prev) face_ref143 <= {face_ref143[31:0], d_e[304 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref143[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[464 +: 8] !== face_ref143[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 143"); end end end
    reg [55:0] face_ref144=0;
    always @(posedge clk) if(lane_me_prev) face_ref144 <= {face_ref144[47:0], r_xo[3600 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref144[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[472 +: 8] !== face_ref144[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 144"); end end end
    reg [23:0] face_ref145=0;
    always @(posedge clk) if(lane_me_prev) face_ref145 <= {face_ref145[15:0], r_xo[3344 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref145[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[480 +: 8] !== face_ref145[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 145"); end end end
    reg [23:0] face_ref146=0;
    always @(posedge clk) if(lane_me_prev) face_ref146 <= {face_ref146[15:0], r_xo[3608 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref146[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[488 +: 8] !== face_ref146[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 146"); end end end
    reg [23:0] face_ref147=0;
    always @(posedge clk) if(lane_me_prev) face_ref147 <= {face_ref147[15:0], r_xo[2832 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref147[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[496 +: 8] !== face_ref147[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 147"); end end end
    reg [23:0] face_ref148=0;
    always @(posedge clk) if(lane_me_prev) face_ref148 <= {face_ref148[15:0], r_xo[2840 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref148[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[504 +: 8] !== face_ref148[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 148"); end end end
    reg [15:0] face_ref149=0;
    always @(posedge clk) if(lane_me_prev) face_ref149 <= {face_ref149[7:0], r_xo[1552 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref149[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[512 +: 8] !== face_ref149[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 149"); end end end
    reg [23:0] face_ref150=0;
    always @(posedge clk) if(lane_me_prev) face_ref150 <= {face_ref150[15:0], r_xo[1296 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref150[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[520 +: 8] !== face_ref150[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 150"); end end end
    reg [23:0] face_ref151=0;
    always @(posedge clk) if(lane_me_prev) face_ref151 <= {face_ref151[15:0], r_xo[2848 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref151[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[528 +: 8] !== face_ref151[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 151"); end end end
    reg [23:0] face_ref152=0;
    always @(posedge clk) if(lane_me_prev) face_ref152 <= {face_ref152[15:0], r_xo[784 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref152[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[536 +: 8] !== face_ref152[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 152"); end end end
    reg [15:0] face_ref153=0;
    always @(posedge clk) if(lane_me_prev) face_ref153 <= {face_ref153[7:0], r_xo[528 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref153[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[544 +: 8] !== face_ref153[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 153"); end end end
    reg [15:0] face_ref154=0;
    always @(posedge clk) if(lane_me_prev) face_ref154 <= {face_ref154[7:0], r_xo[536 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref154[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[552 +: 8] !== face_ref154[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 154"); end end end
    reg [39:0] face_ref155=0;
    always @(posedge clk) if(lane_me_prev) face_ref155 <= {face_ref155[31:0], d_e[312 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref155[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[560 +: 8] !== face_ref155[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 155"); end end end
    reg [39:0] face_ref156=0;
    always @(posedge clk) if(lane_me_prev) face_ref156 <= {face_ref156[31:0], d_w[680 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref156[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[344 +: 8] !== face_ref156[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 156"); end end end
    reg [39:0] face_ref157=0;
    always @(posedge clk) if(lane_me_prev) face_ref157 <= {face_ref157[31:0], d_w[688 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref157[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[336 +: 8] !== face_ref157[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 157"); end end end
    reg [23:0] face_ref158=0;
    always @(posedge clk) if(lane_me_prev) face_ref158 <= {face_ref158[15:0], r_xo[2576 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref158[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[568 +: 8] !== face_ref158[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 158"); end end end
    reg [23:0] face_ref159=0;
    always @(posedge clk) if(lane_me_prev) face_ref159 <= {face_ref159[15:0], r_xo[2584 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref159[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[576 +: 8] !== face_ref159[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 159"); end end end
    reg [71:0] face_ref160=0;
    always @(posedge clk) if(lane_me_prev) face_ref160 <= {face_ref160[63:0], d_w[696 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref160[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[344 +: 8] !== face_ref160[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 160"); end end end
    reg [71:0] face_ref161=0;
    always @(posedge clk) if(lane_me_prev) face_ref161 <= {face_ref161[63:0], d_w[704 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref161[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[352 +: 8] !== face_ref161[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 161"); end end end
    reg [15:0] face_ref162=0;
    always @(posedge clk) if(lane_me_prev) face_ref162 <= {face_ref162[7:0], r_xo[272 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref162[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[584 +: 8] !== face_ref162[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 162"); end end end
    reg [71:0] face_ref163=0;
    always @(posedge clk) if(lane_me_prev) face_ref163 <= {face_ref163[63:0], d_w[712 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref163[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[360 +: 8] !== face_ref163[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 163"); end end end
    reg [39:0] face_ref164=0;
    always @(posedge clk) if(lane_me_prev) face_ref164 <= {face_ref164[31:0], d_e[320 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref164[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[592 +: 8] !== face_ref164[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 164"); end end end
    reg [63:0] face_ref165=0;
    always @(posedge clk) if(lane_me_prev) face_ref165 <= {face_ref165[55:0], r_xo[2320 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref165[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[600 +: 8] !== face_ref165[56 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 165"); end end end
    reg [39:0] face_ref166=0;
    always @(posedge clk) if(lane_me_prev) face_ref166 <= {face_ref166[31:0], d_e[328 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref166[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[608 +: 8] !== face_ref166[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 166"); end end end
    reg [15:0] face_ref167=0;
    always @(posedge clk) if(lane_me_prev) face_ref167 <= {face_ref167[7:0], r_xo[1560 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref167[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[616 +: 8] !== face_ref167[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 167"); end end end
    reg [55:0] face_ref168=0;
    always @(posedge clk) if(lane_me_prev) face_ref168 <= {face_ref168[47:0], d_e[336 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref168[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[624 +: 8] !== face_ref168[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 168"); end end end
    reg [39:0] face_ref169=0;
    always @(posedge clk) if(lane_me_prev) face_ref169 <= {face_ref169[31:0], d_w[720 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref169[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[368 +: 8] !== face_ref169[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 169"); end end end
    reg [71:0] face_ref170=0;
    always @(posedge clk) if(lane_me_prev) face_ref170 <= {face_ref170[63:0], d_w[728 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref170[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[376 +: 8] !== face_ref170[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 170"); end end end
    reg [71:0] face_ref171=0;
    always @(posedge clk) if(lane_me_prev) face_ref171 <= {face_ref171[63:0], d_w[736 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref171[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[384 +: 8] !== face_ref171[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 171"); end end end
    reg [23:0] face_ref172=0;
    always @(posedge clk) if(lane_me_prev) face_ref172 <= {face_ref172[15:0], d_w[744 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref172[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[392 +: 8] !== face_ref172[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 172"); end end end
    reg [39:0] face_ref173=0;
    always @(posedge clk) if(lane_me_prev) face_ref173 <= {face_ref173[31:0], d_e[344 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref173[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[632 +: 8] !== face_ref173[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 173"); end end end
    reg [39:0] face_ref174=0;
    always @(posedge clk) if(lane_me_prev) face_ref174 <= {face_ref174[31:0], d_e[352 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref174[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[640 +: 8] !== face_ref174[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 174"); end end end
    reg [39:0] face_ref175=0;
    always @(posedge clk) if(lane_me_prev) face_ref175 <= {face_ref175[31:0], d_e[360 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref175[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[648 +: 8] !== face_ref175[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 175"); end end end
    reg [39:0] face_ref176=0;
    always @(posedge clk) if(lane_me_prev) face_ref176 <= {face_ref176[31:0], d_e[368 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref176[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[656 +: 8] !== face_ref176[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 176"); end end end
    reg [39:0] face_ref177=0;
    always @(posedge clk) if(lane_me_prev) face_ref177 <= {face_ref177[31:0], d_e[376 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref177[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[664 +: 8] !== face_ref177[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 177"); end end end
    reg [39:0] face_ref178=0;
    always @(posedge clk) if(lane_me_prev) face_ref178 <= {face_ref178[31:0], d_w[752 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref178[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[352 +: 8] !== face_ref178[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 178"); end end end
    reg [39:0] face_ref179=0;
    always @(posedge clk) if(lane_me_prev) face_ref179 <= {face_ref179[31:0], d_w[760 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref179[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[360 +: 8] !== face_ref179[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 179"); end end end
    reg [47:0] face_ref180=0;
    always @(posedge clk) if(lane_me_prev) face_ref180 <= {face_ref180[39:0], r_xo[3864 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref180[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[672 +: 8] !== face_ref180[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 180"); end end end
    reg [23:0] face_ref181=0;
    always @(posedge clk) if(lane_me_prev) face_ref181 <= {face_ref181[15:0], r_xo[3080 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref181[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[680 +: 8] !== face_ref181[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 181"); end end end
    reg [23:0] face_ref182=0;
    always @(posedge clk) if(lane_me_prev) face_ref182 <= {face_ref182[15:0], r_xo[1280 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref182[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[688 +: 8] !== face_ref182[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 182"); end end end
    reg [23:0] face_ref183=0;
    always @(posedge clk) if(lane_me_prev) face_ref183 <= {face_ref183[15:0], r_xo[3352 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref183[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[696 +: 8] !== face_ref183[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 183"); end end end
    reg [23:0] face_ref184=0;
    always @(posedge clk) if(lane_me_prev) face_ref184 <= {face_ref184[15:0], r_xo[3096 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref184[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[704 +: 8] !== face_ref184[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 184"); end end end
    reg [15:0] face_ref185=0;
    always @(posedge clk) if(lane_me_prev) face_ref185 <= {face_ref185[7:0], r_xo[1024 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref185[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[712 +: 8] !== face_ref185[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 185"); end end end
    reg [23:0] face_ref186=0;
    always @(posedge clk) if(lane_me_prev) face_ref186 <= {face_ref186[15:0], r_xo[1816 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref186[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[720 +: 8] !== face_ref186[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 186"); end end end
    reg [23:0] face_ref187=0;
    always @(posedge clk) if(lane_me_prev) face_ref187 <= {face_ref187[15:0], r_xo[3104 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref187[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[728 +: 8] !== face_ref187[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 187"); end end end
    reg [23:0] face_ref188=0;
    always @(posedge clk) if(lane_me_prev) face_ref188 <= {face_ref188[15:0], r_xo[1824 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref188[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[736 +: 8] !== face_ref188[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 188"); end end end
    reg [63:0] face_ref189=0;
    always @(posedge clk) if(lane_me_prev) face_ref189 <= {face_ref189[55:0], r_xo[1304 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref189[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[744 +: 8] !== face_ref189[56 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 189"); end end end
    reg [15:0] face_ref190=0;
    always @(posedge clk) if(lane_me_prev) face_ref190 <= {face_ref190[7:0], r_xo[1048 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref190[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[752 +: 8] !== face_ref190[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 190"); end end end
    reg [31:0] face_ref191=0;
    always @(posedge clk) if(lane_me_prev) face_ref191 <= {face_ref191[23:0], r_xo[792 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref191[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[760 +: 8] !== face_ref191[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 191"); end end end
    reg [15:0] face_ref192=0;
    always @(posedge clk) if(lane_me_prev) face_ref192 <= {face_ref192[7:0], r_xo[1056 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref192[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[768 +: 8] !== face_ref192[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 192"); end end end
    reg [39:0] face_ref193=0;
    always @(posedge clk) if(lane_me_prev) face_ref193 <= {face_ref193[31:0], d_e[384 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref193[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[776 +: 8] !== face_ref193[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 193"); end end end
    reg [39:0] face_ref194=0;
    always @(posedge clk) if(lane_me_prev) face_ref194 <= {face_ref194[31:0], d_e[392 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref194[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[784 +: 8] !== face_ref194[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 194"); end end end
    reg [39:0] face_ref195=0;
    always @(posedge clk) if(lane_me_prev) face_ref195 <= {face_ref195[31:0], d_e[400 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref195[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[792 +: 8] !== face_ref195[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 195"); end end end
    reg [47:0] face_ref196=0;
    always @(posedge clk) if(lane_me_prev) face_ref196 <= {face_ref196[39:0], d_e[408 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref196[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[800 +: 8] !== face_ref196[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 196"); end end end
    reg [39:0] face_ref197=0;
    always @(posedge clk) if(lane_me_prev) face_ref197 <= {face_ref197[31:0], d_e[416 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref197[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[808 +: 8] !== face_ref197[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 197"); end end end
    reg [47:0] face_ref198=0;
    always @(posedge clk) if(lane_me_prev) face_ref198 <= {face_ref198[39:0], d_e[424 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref198[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[816 +: 8] !== face_ref198[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 198"); end end end
    reg [39:0] face_ref199=0;
    always @(posedge clk) if(lane_me_prev) face_ref199 <= {face_ref199[31:0], d_e[432 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref199[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[824 +: 8] !== face_ref199[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 199"); end end end
    reg [47:0] face_ref200=0;
    always @(posedge clk) if(lane_me_prev) face_ref200 <= {face_ref200[39:0], d_e[440 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref200[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[832 +: 8] !== face_ref200[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 200"); end end end
    reg [39:0] face_ref201=0;
    always @(posedge clk) if(lane_me_prev) face_ref201 <= {face_ref201[31:0], d_w[768 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref201[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[368 +: 8] !== face_ref201[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 201"); end end end
    reg [39:0] face_ref202=0;
    always @(posedge clk) if(lane_me_prev) face_ref202 <= {face_ref202[31:0], d_w[776 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref202[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[376 +: 8] !== face_ref202[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 202"); end end end
    reg [39:0] face_ref203=0;
    always @(posedge clk) if(lane_me_prev) face_ref203 <= {face_ref203[31:0], d_w[784 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref203[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[384 +: 8] !== face_ref203[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 203"); end end end
    reg [39:0] face_ref204=0;
    always @(posedge clk) if(lane_me_prev) face_ref204 <= {face_ref204[31:0], d_w[792 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref204[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[392 +: 8] !== face_ref204[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 204"); end end end
    reg [39:0] face_ref205=0;
    always @(posedge clk) if(lane_me_prev) face_ref205 <= {face_ref205[31:0], d_w[800 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref205[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[400 +: 8] !== face_ref205[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 205"); end end end
    reg [31:0] face_ref206=0;
    always @(posedge clk) if(lane_me_prev) face_ref206 <= {face_ref206[23:0], d_w[808 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref206[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[408 +: 8] !== face_ref206[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 206"); end end end
    reg [39:0] face_ref207=0;
    always @(posedge clk) if(lane_me_prev) face_ref207 <= {face_ref207[31:0], d_w[816 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref207[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[400 +: 8] !== face_ref207[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 207"); end end end
    reg [23:0] face_ref208=0;
    always @(posedge clk) if(lane_me_prev) face_ref208 <= {face_ref208[15:0], d_w[824 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref208[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[416 +: 8] !== face_ref208[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 208"); end end end
    reg [39:0] face_ref209=0;
    always @(posedge clk) if(lane_me_prev) face_ref209 <= {face_ref209[31:0], d_w[832 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref209[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[408 +: 8] !== face_ref209[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 209"); end end end
    reg [39:0] face_ref210=0;
    always @(posedge clk) if(lane_me_prev) face_ref210 <= {face_ref210[31:0], d_w[840 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref210[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[416 +: 8] !== face_ref210[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 210"); end end end
    reg [39:0] face_ref211=0;
    always @(posedge clk) if(lane_me_prev) face_ref211 <= {face_ref211[31:0], d_w[848 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref211[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[424 +: 8] !== face_ref211[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 211"); end end end
    reg [39:0] face_ref212=0;
    always @(posedge clk) if(lane_me_prev) face_ref212 <= {face_ref212[31:0], d_w[856 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref212[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[432 +: 8] !== face_ref212[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 212"); end end end
    reg [39:0] face_ref213=0;
    always @(posedge clk) if(lane_me_prev) face_ref213 <= {face_ref213[31:0], d_w[864 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref213[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[440 +: 8] !== face_ref213[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 213"); end end end
    reg [39:0] face_ref214=0;
    always @(posedge clk) if(lane_me_prev) face_ref214 <= {face_ref214[31:0], d_w[872 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref214[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[424 +: 8] !== face_ref214[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 214"); end end end
    reg [39:0] face_ref215=0;
    always @(posedge clk) if(lane_me_prev) face_ref215 <= {face_ref215[31:0], d_w[880 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref215[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[432 +: 8] !== face_ref215[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 215"); end end end
    reg [39:0] face_ref216=0;
    always @(posedge clk) if(lane_me_prev) face_ref216 <= {face_ref216[31:0], d_w[888 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref216[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[448 +: 8] !== face_ref216[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 216"); end end end
    reg [39:0] face_ref217=0;
    always @(posedge clk) if(lane_me_prev) face_ref217 <= {face_ref217[31:0], d_w[896 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref217[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[440 +: 8] !== face_ref217[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 217"); end end end
    reg [39:0] face_ref218=0;
    always @(posedge clk) if(lane_me_prev) face_ref218 <= {face_ref218[31:0], d_w[904 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref218[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[448 +: 8] !== face_ref218[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 218"); end end end
    reg [31:0] face_ref219=0;
    always @(posedge clk) if(lane_me_prev) face_ref219 <= {face_ref219[23:0], d_w[912 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref219[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[456 +: 8] !== face_ref219[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 219"); end end end
    reg [39:0] face_ref220=0;
    always @(posedge clk) if(lane_me_prev) face_ref220 <= {face_ref220[31:0], d_w[920 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref220[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[464 +: 8] !== face_ref220[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 220"); end end end
    reg [31:0] face_ref221=0;
    always @(posedge clk) if(lane_me_prev) face_ref221 <= {face_ref221[23:0], d_w[928 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref221[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[472 +: 8] !== face_ref221[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 221"); end end end
    reg [31:0] face_ref222=0;
    always @(posedge clk) if(lane_me_prev) face_ref222 <= {face_ref222[23:0], d_w[936 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref222[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[480 +: 8] !== face_ref222[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 222"); end end end
    reg [31:0] face_ref223=0;
    always @(posedge clk) if(lane_me_prev) face_ref223 <= {face_ref223[23:0], d_w[944 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref223[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[488 +: 8] !== face_ref223[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 223"); end end end
    reg [23:0] face_ref224=0;
    always @(posedge clk) if(lane_me_prev) face_ref224 <= {face_ref224[15:0], d_w[952 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref224[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[496 +: 8] !== face_ref224[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 224"); end end end
    reg [23:0] face_ref225=0;
    always @(posedge clk) if(lane_me_prev) face_ref225 <= {face_ref225[15:0], d_w[960 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref225[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[504 +: 8] !== face_ref225[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 225"); end end end
    reg [23:0] face_ref226=0;
    always @(posedge clk) if(lane_me_prev) face_ref226 <= {face_ref226[15:0], d_w[968 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref226[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[512 +: 8] !== face_ref226[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 226"); end end end
    reg [39:0] face_ref227=0;
    always @(posedge clk) if(lane_me_prev) face_ref227 <= {face_ref227[31:0], d_w[976 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref227[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[456 +: 8] !== face_ref227[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 227"); end end end
    reg [39:0] face_ref228=0;
    always @(posedge clk) if(lane_me_prev) face_ref228 <= {face_ref228[31:0], d_w[984 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref228[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[464 +: 8] !== face_ref228[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 228"); end end end
    reg [39:0] face_ref229=0;
    always @(posedge clk) if(lane_me_prev) face_ref229 <= {face_ref229[31:0], d_w[992 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref229[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[472 +: 8] !== face_ref229[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 229"); end end end
    reg [39:0] face_ref230=0;
    always @(posedge clk) if(lane_me_prev) face_ref230 <= {face_ref230[31:0], d_w[1000 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref230[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[480 +: 8] !== face_ref230[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 230"); end end end
    reg [55:0] face_ref231=0;
    always @(posedge clk) if(lane_me_prev) face_ref231 <= {face_ref231[47:0], d_w[1008 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref231[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[488 +: 8] !== face_ref231[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 231"); end end end
    reg [55:0] face_ref232=0;
    always @(posedge clk) if(lane_me_prev) face_ref232 <= {face_ref232[47:0], d_w[1016 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref232[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[496 +: 8] !== face_ref232[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 232"); end end end
    reg [39:0] face_ref233=0;
    always @(posedge clk) if(lane_me_prev) face_ref233 <= {face_ref233[31:0], d_w[1024 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref233[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[504 +: 8] !== face_ref233[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 233"); end end end
    reg [47:0] face_ref234=0;
    always @(posedge clk) if(lane_me_prev) face_ref234 <= {face_ref234[39:0], d_w[1032 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref234[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[520 +: 8] !== face_ref234[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 234"); end end end
    reg [39:0] face_ref235=0;
    always @(posedge clk) if(lane_me_prev) face_ref235 <= {face_ref235[31:0], d_w[1040 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref235[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[528 +: 8] !== face_ref235[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 235"); end end end
    reg [39:0] face_ref236=0;
    always @(posedge clk) if(lane_me_prev) face_ref236 <= {face_ref236[31:0], d_w[1048 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref236[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[536 +: 8] !== face_ref236[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 236"); end end end
    reg [55:0] face_ref237=0;
    always @(posedge clk) if(lane_me_prev) face_ref237 <= {face_ref237[47:0], d_w[1056 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref237[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[544 +: 8] !== face_ref237[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 237"); end end end
    reg [55:0] face_ref238=0;
    always @(posedge clk) if(lane_me_prev) face_ref238 <= {face_ref238[47:0], d_w[1064 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref238[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[552 +: 8] !== face_ref238[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 238"); end end end
    reg [39:0] face_ref239=0;
    always @(posedge clk) if(lane_me_prev) face_ref239 <= {face_ref239[31:0], d_w[1072 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref239[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[560 +: 8] !== face_ref239[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 239"); end end end
    reg [39:0] face_ref240=0;
    always @(posedge clk) if(lane_me_prev) face_ref240 <= {face_ref240[31:0], d_w[1080 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref240[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[568 +: 8] !== face_ref240[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 240"); end end end
    reg [31:0] face_ref241=0;
    always @(posedge clk) if(lane_me_prev) face_ref241 <= {face_ref241[23:0], d_w[1088 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref241[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[576 +: 8] !== face_ref241[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 241"); end end end
    reg [31:0] face_ref242=0;
    always @(posedge clk) if(lane_me_prev) face_ref242 <= {face_ref242[23:0], d_w[1096 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref242[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[584 +: 8] !== face_ref242[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 242"); end end end
    reg [39:0] face_ref243=0;
    always @(posedge clk) if(lane_me_prev) face_ref243 <= {face_ref243[31:0], d_w[1104 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref243[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[592 +: 8] !== face_ref243[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 243"); end end end
    reg [39:0] face_ref244=0;
    always @(posedge clk) if(lane_me_prev) face_ref244 <= {face_ref244[31:0], d_w[1112 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref244[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[600 +: 8] !== face_ref244[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 244"); end end end
    reg [39:0] face_ref245=0;
    always @(posedge clk) if(lane_me_prev) face_ref245 <= {face_ref245[31:0], d_w[1120 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref245[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[608 +: 8] !== face_ref245[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 245"); end end end
    reg [31:0] face_ref246=0;
    always @(posedge clk) if(lane_me_prev) face_ref246 <= {face_ref246[23:0], d_w[1128 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref246[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[616 +: 8] !== face_ref246[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 246"); end end end
    reg [55:0] face_ref247=0;
    always @(posedge clk) if(lane_me_prev) face_ref247 <= {face_ref247[47:0], d_w[1136 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref247[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[624 +: 8] !== face_ref247[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 247"); end end end
    reg [39:0] face_ref248=0;
    always @(posedge clk) if(lane_me_prev) face_ref248 <= {face_ref248[31:0], d_w[1144 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref248[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[512 +: 8] !== face_ref248[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 248"); end end end
    reg [39:0] face_ref249=0;
    always @(posedge clk) if(lane_me_prev) face_ref249 <= {face_ref249[31:0], d_w[1152 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref249[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[520 +: 8] !== face_ref249[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 249"); end end end
    reg [39:0] face_ref250=0;
    always @(posedge clk) if(lane_me_prev) face_ref250 <= {face_ref250[31:0], d_w[1160 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref250[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[528 +: 8] !== face_ref250[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 250"); end end end
    reg [47:0] face_ref251=0;
    always @(posedge clk) if(lane_me_prev) face_ref251 <= {face_ref251[39:0], d_w[1168 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref251[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[536 +: 8] !== face_ref251[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 251"); end end end
    reg [55:0] face_ref252=0;
    always @(posedge clk) if(lane_me_prev) face_ref252 <= {face_ref252[47:0], d_w[1176 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref252[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[544 +: 8] !== face_ref252[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 252"); end end end
    reg [31:0] face_ref253=0;
    always @(posedge clk) if(lane_me_prev) face_ref253 <= {face_ref253[23:0], d_w[1184 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref253[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[632 +: 8] !== face_ref253[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 253"); end end end
    reg [39:0] face_ref254=0;
    always @(posedge clk) if(lane_me_prev) face_ref254 <= {face_ref254[31:0], d_w[1192 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref254[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[552 +: 8] !== face_ref254[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 254"); end end end
    reg [39:0] face_ref255=0;
    always @(posedge clk) if(lane_me_prev) face_ref255 <= {face_ref255[31:0], d_w[1200 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref255[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[560 +: 8] !== face_ref255[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 255"); end end end
    reg [39:0] face_ref256=0;
    always @(posedge clk) if(lane_me_prev) face_ref256 <= {face_ref256[31:0], d_w[1208 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref256[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[568 +: 8] !== face_ref256[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 256"); end end end
    reg [39:0] face_ref257=0;
    always @(posedge clk) if(lane_me_prev) face_ref257 <= {face_ref257[31:0], d_w[1216 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref257[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[576 +: 8] !== face_ref257[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 257"); end end end
    reg [39:0] face_ref258=0;
    always @(posedge clk) if(lane_me_prev) face_ref258 <= {face_ref258[31:0], d_w[1224 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref258[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[584 +: 8] !== face_ref258[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 258"); end end end
    reg [55:0] face_ref259=0;
    always @(posedge clk) if(lane_me_prev) face_ref259 <= {face_ref259[47:0], d_w[1232 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref259[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[592 +: 8] !== face_ref259[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 259"); end end end
    reg [55:0] face_ref260=0;
    always @(posedge clk) if(lane_me_prev) face_ref260 <= {face_ref260[47:0], d_w[1240 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref260[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[640 +: 8] !== face_ref260[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 260"); end end end
    reg [39:0] face_ref261=0;
    always @(posedge clk) if(lane_me_prev) face_ref261 <= {face_ref261[31:0], d_w[1248 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref261[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[648 +: 8] !== face_ref261[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 261"); end end end
    reg [63:0] face_ref262=0;
    always @(posedge clk) if(lane_me_prev) face_ref262 <= {face_ref262[55:0], d_w[1256 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref262[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[656 +: 8] !== face_ref262[56 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 262"); end end end
    reg [63:0] face_ref263=0;
    always @(posedge clk) if(lane_me_prev) face_ref263 <= {face_ref263[55:0], d_w[1264 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref263[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[664 +: 8] !== face_ref263[56 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 263"); end end end
    reg [31:0] face_ref264=0;
    always @(posedge clk) if(lane_me_prev) face_ref264 <= {face_ref264[23:0], d_w[1272 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref264[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[672 +: 8] !== face_ref264[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 264"); end end end
    reg [39:0] face_ref265=0;
    always @(posedge clk) if(lane_me_prev) face_ref265 <= {face_ref265[31:0], d_w[1280 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref265[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[600 +: 8] !== face_ref265[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 265"); end end end
    reg [39:0] face_ref266=0;
    always @(posedge clk) if(lane_me_prev) face_ref266 <= {face_ref266[31:0], d_w[1288 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref266[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[608 +: 8] !== face_ref266[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 266"); end end end
    reg [39:0] face_ref267=0;
    always @(posedge clk) if(lane_me_prev) face_ref267 <= {face_ref267[31:0], d_w[1296 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref267[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[616 +: 8] !== face_ref267[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 267"); end end end
    reg [39:0] face_ref268=0;
    always @(posedge clk) if(lane_me_prev) face_ref268 <= {face_ref268[31:0], d_w[1304 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref268[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[624 +: 8] !== face_ref268[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 268"); end end end
    reg [39:0] face_ref269=0;
    always @(posedge clk) if(lane_me_prev) face_ref269 <= {face_ref269[31:0], d_w[1312 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref269[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[632 +: 8] !== face_ref269[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 269"); end end end
    reg [39:0] face_ref270=0;
    always @(posedge clk) if(lane_me_prev) face_ref270 <= {face_ref270[31:0], d_w[1320 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref270[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[640 +: 8] !== face_ref270[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 270"); end end end
    reg [39:0] face_ref271=0;
    always @(posedge clk) if(lane_me_prev) face_ref271 <= {face_ref271[31:0], d_w[1328 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref271[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[648 +: 8] !== face_ref271[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 271"); end end end
    reg [39:0] face_ref272=0;
    always @(posedge clk) if(lane_me_prev) face_ref272 <= {face_ref272[31:0], d_w[1336 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref272[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[656 +: 8] !== face_ref272[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 272"); end end end
    reg [39:0] face_ref273=0;
    always @(posedge clk) if(lane_me_prev) face_ref273 <= {face_ref273[31:0], d_w[1344 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref273[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[664 +: 8] !== face_ref273[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 273"); end end end
    reg [39:0] face_ref274=0;
    always @(posedge clk) if(lane_me_prev) face_ref274 <= {face_ref274[31:0], d_w[1352 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref274[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[672 +: 8] !== face_ref274[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 274"); end end end
    reg [55:0] face_ref275=0;
    always @(posedge clk) if(lane_me_prev) face_ref275 <= {face_ref275[47:0], d_w[1360 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref275[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[680 +: 8] !== face_ref275[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 275"); end end end
    reg [55:0] face_ref276=0;
    always @(posedge clk) if(lane_me_prev) face_ref276 <= {face_ref276[47:0], d_w[1368 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref276[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[688 +: 8] !== face_ref276[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 276"); end end end
    reg [55:0] face_ref277=0;
    always @(posedge clk) if(lane_me_prev) face_ref277 <= {face_ref277[47:0], d_w[1376 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref277[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[680 +: 8] !== face_ref277[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 277"); end end end
    reg [55:0] face_ref278=0;
    always @(posedge clk) if(lane_me_prev) face_ref278 <= {face_ref278[47:0], d_w[1384 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref278[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[688 +: 8] !== face_ref278[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 278"); end end end
    reg [39:0] face_ref279=0;
    always @(posedge clk) if(lane_me_prev) face_ref279 <= {face_ref279[31:0], d_w[1392 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref279[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[696 +: 8] !== face_ref279[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 279"); end end end
    reg [63:0] face_ref280=0;
    always @(posedge clk) if(lane_me_prev) face_ref280 <= {face_ref280[55:0], d_w[1400 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref280[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[704 +: 8] !== face_ref280[56 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 280"); end end end
    reg [63:0] face_ref281=0;
    always @(posedge clk) if(lane_me_prev) face_ref281 <= {face_ref281[55:0], d_w[1408 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref281[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[712 +: 8] !== face_ref281[56 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 281"); end end end
    reg [71:0] face_ref282=0;
    always @(posedge clk) if(lane_me_prev) face_ref282 <= {face_ref282[63:0], d_e[448 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref282[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[840 +: 8] !== face_ref282[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 282"); end end end
    reg [39:0] face_ref283=0;
    always @(posedge clk) if(lane_me_prev) face_ref283 <= {face_ref283[31:0], d_e[456 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref283[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[848 +: 8] !== face_ref283[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 283"); end end end
    reg [71:0] face_ref284=0;
    always @(posedge clk) if(lane_me_prev) face_ref284 <= {face_ref284[63:0], r_xo[3376 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref284[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[856 +: 8] !== face_ref284[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 284"); end end end
    reg [71:0] face_ref285=0;
    always @(posedge clk) if(lane_me_prev) face_ref285 <= {face_ref285[63:0], r_xo[3384 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref285[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[864 +: 8] !== face_ref285[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 285"); end end end
    reg [63:0] face_ref286=0;
    always @(posedge clk) if(lane_me_prev) face_ref286 <= {face_ref286[55:0], r_xo[280 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref286[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[872 +: 8] !== face_ref286[56 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 286"); end end end
    reg [63:0] face_ref287=0;
    always @(posedge clk) if(lane_me_prev) face_ref287 <= {face_ref287[55:0], r_xo[288 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref287[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[880 +: 8] !== face_ref287[56 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 287"); end end end
    reg [71:0] face_ref288=0;
    always @(posedge clk) if(lane_me_prev) face_ref288 <= {face_ref288[63:0], r_xo[32 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref288[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[888 +: 8] !== face_ref288[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 288"); end end end
    reg [71:0] face_ref289=0;
    always @(posedge clk) if(lane_me_prev) face_ref289 <= {face_ref289[63:0], r_xo[40 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref289[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[896 +: 8] !== face_ref289[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 289"); end end end
    reg [23:0] face_ref290=0;
    always @(posedge clk) if(lane_me_prev) face_ref290 <= {face_ref290[15:0], r_xo[2568 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref290[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[904 +: 8] !== face_ref290[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 290"); end end end
    reg [39:0] face_ref291=0;
    always @(posedge clk) if(lane_me_prev) face_ref291 <= {face_ref291[31:0], d_e[464 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref291[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[912 +: 8] !== face_ref291[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 291"); end end end
    reg [39:0] face_ref292=0;
    always @(posedge clk) if(lane_me_prev) face_ref292 <= {face_ref292[31:0], d_e[472 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref292[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[920 +: 8] !== face_ref292[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 292"); end end end
    reg [39:0] face_ref293=0;
    always @(posedge clk) if(lane_me_prev) face_ref293 <= {face_ref293[31:0], d_w[1416 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref293[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[720 +: 8] !== face_ref293[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 293"); end end end
    reg [71:0] face_ref294=0;
    always @(posedge clk) if(lane_me_prev) face_ref294 <= {face_ref294[63:0], r_xo[2592 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref294[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[928 +: 8] !== face_ref294[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 294"); end end end
    reg [15:0] face_ref295=0;
    always @(posedge clk) if(lane_me_prev) face_ref295 <= {face_ref295[7:0], r_xo[520 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref295[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[936 +: 8] !== face_ref295[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 295"); end end end
    reg [39:0] face_ref296=0;
    always @(posedge clk) if(lane_me_prev) face_ref296 <= {face_ref296[31:0], d_w[1424 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref296[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[728 +: 8] !== face_ref296[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 296"); end end end
    reg [71:0] face_ref297=0;
    always @(posedge clk) if(lane_me_prev) face_ref297 <= {face_ref297[63:0], r_xo[3656 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref297[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[944 +: 8] !== face_ref297[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 297"); end end end
    reg [71:0] face_ref298=0;
    always @(posedge clk) if(lane_me_prev) face_ref298 <= {face_ref298[63:0], r_xo[1608 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref298[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[952 +: 8] !== face_ref298[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 298"); end end end
    reg [23:0] face_ref299=0;
    always @(posedge clk) if(lane_me_prev) face_ref299 <= {face_ref299[15:0], r_xo[2872 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref299[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[960 +: 8] !== face_ref299[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 299"); end end end
    reg [23:0] face_ref300=0;
    always @(posedge clk) if(lane_me_prev) face_ref300 <= {face_ref300[15:0], r_xo[2880 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref300[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[968 +: 8] !== face_ref300[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 300"); end end end
    reg [31:0] face_ref301=0;
    always @(posedge clk) if(lane_me_prev) face_ref301 <= {face_ref301[23:0], d_w[1432 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref301[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[736 +: 8] !== face_ref301[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 301"); end end end
    reg [23:0] face_ref302=0;
    always @(posedge clk) if(lane_me_prev) face_ref302 <= {face_ref302[15:0], r_xo[2888 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref302[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[976 +: 8] !== face_ref302[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 302"); end end end
    reg [15:0] face_ref303=0;
    always @(posedge clk) if(lane_me_prev) face_ref303 <= {face_ref303[7:0], r_xo[1600 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref303[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[984 +: 8] !== face_ref303[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 303"); end end end
    reg [31:0] face_ref304=0;
    always @(posedge clk) if(lane_me_prev) face_ref304 <= {face_ref304[23:0], d_w[1440 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref304[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[744 +: 8] !== face_ref304[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 304"); end end end
    reg [15:0] face_ref305=0;
    always @(posedge clk) if(lane_me_prev) face_ref305 <= {face_ref305[7:0], r_xo[576 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref305[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[992 +: 8] !== face_ref305[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 305"); end end end
    reg [63:0] face_ref306=0;
    always @(posedge clk) if(lane_me_prev) face_ref306 <= {face_ref306[55:0], d_e[480 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref306[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1000 +: 8] !== face_ref306[56 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 306"); end end end
    reg [39:0] face_ref307=0;
    always @(posedge clk) if(lane_me_prev) face_ref307 <= {face_ref307[31:0], d_e[488 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref307[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1008 +: 8] !== face_ref307[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 307"); end end end
    reg [39:0] face_ref308=0;
    always @(posedge clk) if(lane_me_prev) face_ref308 <= {face_ref308[31:0], d_e[496 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref308[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1016 +: 8] !== face_ref308[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 308"); end end end
    reg [71:0] face_ref309=0;
    always @(posedge clk) if(lane_me_prev) face_ref309 <= {face_ref309[63:0], d_e[504 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref309[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1024 +: 8] !== face_ref309[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 309"); end end end
    reg [39:0] face_ref310=0;
    always @(posedge clk) if(lane_me_prev) face_ref310 <= {face_ref310[31:0], d_e[512 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref310[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1032 +: 8] !== face_ref310[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 310"); end end end
    reg [47:0] face_ref311=0;
    always @(posedge clk) if(lane_me_prev) face_ref311 <= {face_ref311[39:0], d_w[1448 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref311[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[752 +: 8] !== face_ref311[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 311"); end end end
    reg [39:0] face_ref312=0;
    always @(posedge clk) if(lane_me_prev) face_ref312 <= {face_ref312[31:0], d_e[520 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref312[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1040 +: 8] !== face_ref312[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 312"); end end end
    reg [47:0] face_ref313=0;
    always @(posedge clk) if(lane_me_prev) face_ref313 <= {face_ref313[39:0], d_w[1456 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref313[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[760 +: 8] !== face_ref313[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 313"); end end end
    reg [39:0] face_ref314=0;
    always @(posedge clk) if(lane_me_prev) face_ref314 <= {face_ref314[31:0], d_e[528 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref314[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1048 +: 8] !== face_ref314[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 314"); end end end
    reg [47:0] face_ref315=0;
    always @(posedge clk) if(lane_me_prev) face_ref315 <= {face_ref315[39:0], d_w[1464 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref315[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[768 +: 8] !== face_ref315[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 315"); end end end
    reg [23:0] face_ref316=0;
    always @(posedge clk) if(lane_me_prev) face_ref316 <= {face_ref316[15:0], r_xo[2856 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref316[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1056 +: 8] !== face_ref316[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 316"); end end end
    reg [23:0] face_ref317=0;
    always @(posedge clk) if(lane_me_prev) face_ref317 <= {face_ref317[15:0], r_xo[2600 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref317[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1064 +: 8] !== face_ref317[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 317"); end end end
    reg [23:0] face_ref318=0;
    always @(posedge clk) if(lane_me_prev) face_ref318 <= {face_ref318[15:0], r_xo[2864 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref318[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1072 +: 8] !== face_ref318[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 318"); end end end
    reg [23:0] face_ref319=0;
    always @(posedge clk) if(lane_me_prev) face_ref319 <= {face_ref319[15:0], r_xo[2608 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref319[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1080 +: 8] !== face_ref319[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 319"); end end end
    reg [39:0] face_ref320=0;
    always @(posedge clk) if(lane_me_prev) face_ref320 <= {face_ref320[31:0], d_w[1472 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref320[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[776 +: 8] !== face_ref320[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 320"); end end end
    reg [39:0] face_ref321=0;
    always @(posedge clk) if(lane_me_prev) face_ref321 <= {face_ref321[31:0], d_w[1480 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref321[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[784 +: 8] !== face_ref321[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 321"); end end end
    reg [23:0] face_ref322=0;
    always @(posedge clk) if(lane_me_prev) face_ref322 <= {face_ref322[15:0], r_xo[2624 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref322[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1088 +: 8] !== face_ref322[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 322"); end end end
    reg [15:0] face_ref323=0;
    always @(posedge clk) if(lane_me_prev) face_ref323 <= {face_ref323[7:0], r_xo[552 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref323[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1096 +: 8] !== face_ref323[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 323"); end end end
    reg [71:0] face_ref324=0;
    always @(posedge clk) if(lane_me_prev) face_ref324 <= {face_ref324[63:0], r_xo[296 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref324[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1104 +: 8] !== face_ref324[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 324"); end end end
    reg [15:0] face_ref325=0;
    always @(posedge clk) if(lane_me_prev) face_ref325 <= {face_ref325[7:0], r_xo[560 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref325[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1112 +: 8] !== face_ref325[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 325"); end end end
    reg [87:0] face_ref326=0;
    always @(posedge clk) if(lane_me_prev) face_ref326 <= {face_ref326[79:0], d_w[1488 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref326[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[792 +: 8] !== face_ref326[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 326"); end end end
    reg [87:0] face_ref327=0;
    always @(posedge clk) if(lane_me_prev) face_ref327 <= {face_ref327[79:0], d_w[1496 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref327[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[800 +: 8] !== face_ref327[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 327"); end end end
    reg [87:0] face_ref328=0;
    always @(posedge clk) if(lane_me_prev) face_ref328 <= {face_ref328[79:0], d_w[1504 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref328[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[808 +: 8] !== face_ref328[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 328"); end end end
    reg [23:0] face_ref329=0;
    always @(posedge clk) if(lane_me_prev) face_ref329 <= {face_ref329[15:0], d_w[1512 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref329[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[816 +: 8] !== face_ref329[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 329"); end end end
    reg [87:0] face_ref330=0;
    always @(posedge clk) if(lane_me_prev) face_ref330 <= {face_ref330[79:0], d_w[1520 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref330[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[824 +: 8] !== face_ref330[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 330"); end end end
    reg [79:0] face_ref331=0;
    always @(posedge clk) if(lane_me_prev) face_ref331 <= {face_ref331[71:0], r_xo[320 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref331[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1120 +: 8] !== face_ref331[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 331"); end end end
    reg [23:0] face_ref332=0;
    always @(posedge clk) if(lane_me_prev) face_ref332 <= {face_ref332[15:0], d_w[1528 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref332[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[832 +: 8] !== face_ref332[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 332"); end end end
    reg [87:0] face_ref333=0;
    always @(posedge clk) if(lane_me_prev) face_ref333 <= {face_ref333[79:0], d_w[1536 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref333[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[840 +: 8] !== face_ref333[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 333"); end end end
    reg [87:0] face_ref334=0;
    always @(posedge clk) if(lane_me_prev) face_ref334 <= {face_ref334[79:0], d_w[1544 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref334[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[848 +: 8] !== face_ref334[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 334"); end end end
    reg [39:0] face_ref335=0;
    always @(posedge clk) if(lane_me_prev) face_ref335 <= {face_ref335[31:0], d_e[536 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref335[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1128 +: 8] !== face_ref335[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 335"); end end end
    reg [39:0] face_ref336=0;
    always @(posedge clk) if(lane_me_prev) face_ref336 <= {face_ref336[31:0], d_w[1552 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref336[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[856 +: 8] !== face_ref336[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 336"); end end end
    reg [71:0] face_ref337=0;
    always @(posedge clk) if(lane_me_prev) face_ref337 <= {face_ref337[63:0], d_w[1560 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref337[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[864 +: 8] !== face_ref337[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 337"); end end end
    reg [71:0] face_ref338=0;
    always @(posedge clk) if(lane_me_prev) face_ref338 <= {face_ref338[63:0], d_w[1568 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref338[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[872 +: 8] !== face_ref338[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 338"); end end end
    reg [71:0] face_ref339=0;
    always @(posedge clk) if(lane_me_prev) face_ref339 <= {face_ref339[63:0], r_xo[2344 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref339[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1136 +: 8] !== face_ref339[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 339"); end end end
    reg [79:0] face_ref340=0;
    always @(posedge clk) if(lane_me_prev) face_ref340 <= {face_ref340[71:0], r_xo[2368 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref340[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1144 +: 8] !== face_ref340[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 340"); end end end
    reg [39:0] face_ref341=0;
    always @(posedge clk) if(lane_me_prev) face_ref341 <= {face_ref341[31:0], d_e[544 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref341[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1152 +: 8] !== face_ref341[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 341"); end end end
    reg [47:0] face_ref342=0;
    always @(posedge clk) if(lane_me_prev) face_ref342 <= {face_ref342[39:0], d_e[552 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref342[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1160 +: 8] !== face_ref342[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 342"); end end end
    reg [47:0] face_ref343=0;
    always @(posedge clk) if(lane_me_prev) face_ref343 <= {face_ref343[39:0], d_e[560 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref343[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1168 +: 8] !== face_ref343[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 343"); end end end
    reg [39:0] face_ref344=0;
    always @(posedge clk) if(lane_me_prev) face_ref344 <= {face_ref344[31:0], d_e[568 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref344[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1176 +: 8] !== face_ref344[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 344"); end end end
    reg [39:0] face_ref345=0;
    always @(posedge clk) if(lane_me_prev) face_ref345 <= {face_ref345[31:0], d_e[576 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref345[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1184 +: 8] !== face_ref345[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 345"); end end end
    reg [39:0] face_ref346=0;
    always @(posedge clk) if(lane_me_prev) face_ref346 <= {face_ref346[31:0], d_e[584 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref346[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1192 +: 8] !== face_ref346[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 346"); end end end
    reg [39:0] face_ref347=0;
    always @(posedge clk) if(lane_me_prev) face_ref347 <= {face_ref347[31:0], d_e[592 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref347[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1200 +: 8] !== face_ref347[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 347"); end end end
    reg [47:0] face_ref348=0;
    always @(posedge clk) if(lane_me_prev) face_ref348 <= {face_ref348[39:0], d_e[600 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref348[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1208 +: 8] !== face_ref348[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 348"); end end end
    reg [63:0] face_ref349=0;
    always @(posedge clk) if(lane_me_prev) face_ref349 <= {face_ref349[55:0], r_xo[3904 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref349[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1216 +: 8] !== face_ref349[56 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 349"); end end end
    reg [23:0] face_ref350=0;
    always @(posedge clk) if(lane_me_prev) face_ref350 <= {face_ref350[15:0], r_xo[3128 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref350[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1224 +: 8] !== face_ref350[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 350"); end end end
    reg [23:0] face_ref351=0;
    always @(posedge clk) if(lane_me_prev) face_ref351 <= {face_ref351[15:0], r_xo[3392 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref351[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1232 +: 8] !== face_ref351[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 351"); end end end
    reg [71:0] face_ref352=0;
    always @(posedge clk) if(lane_me_prev) face_ref352 <= {face_ref352[63:0], r_xo[1856 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref352[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1240 +: 8] !== face_ref352[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 352"); end end end
    reg [31:0] face_ref353=0;
    always @(posedge clk) if(lane_me_prev) face_ref353 <= {face_ref353[23:0], r_xo[3136 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref353[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1248 +: 8] !== face_ref353[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 353"); end end end
    reg [31:0] face_ref354=0;
    always @(posedge clk) if(lane_me_prev) face_ref354 <= {face_ref354[23:0], d_w[1576 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref354[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[880 +: 8] !== face_ref354[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 354"); end end end
    reg [31:0] face_ref355=0;
    always @(posedge clk) if(lane_me_prev) face_ref355 <= {face_ref355[23:0], r_xo[3144 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref355[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1256 +: 8] !== face_ref355[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 355"); end end end
    reg [31:0] face_ref356=0;
    always @(posedge clk) if(lane_me_prev) face_ref356 <= {face_ref356[23:0], r_xo[3152 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref356[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1264 +: 8] !== face_ref356[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 356"); end end end
    reg [23:0] face_ref357=0;
    always @(posedge clk) if(lane_me_prev) face_ref357 <= {face_ref357[15:0], r_xo[1080 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref357[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1272 +: 8] !== face_ref357[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 357"); end end end
    reg [31:0] face_ref358=0;
    always @(posedge clk) if(lane_me_prev) face_ref358 <= {face_ref358[23:0], r_xo[1344 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref358[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1280 +: 8] !== face_ref358[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 358"); end end end
    reg [23:0] face_ref359=0;
    always @(posedge clk) if(lane_me_prev) face_ref359 <= {face_ref359[15:0], r_xo[2896 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref359[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1288 +: 8] !== face_ref359[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 359"); end end end
    reg [31:0] face_ref360=0;
    always @(posedge clk) if(lane_me_prev) face_ref360 <= {face_ref360[23:0], r_xo[1352 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref360[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1296 +: 8] !== face_ref360[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 360"); end end end
    reg [31:0] face_ref361=0;
    always @(posedge clk) if(lane_me_prev) face_ref361 <= {face_ref361[23:0], r_xo[832 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref361[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1304 +: 8] !== face_ref361[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 361"); end end end
    reg [31:0] face_ref362=0;
    always @(posedge clk) if(lane_me_prev) face_ref362 <= {face_ref362[23:0], r_xo[1360 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref362[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1312 +: 8] !== face_ref362[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 362"); end end end
    reg [15:0] face_ref363=0;
    always @(posedge clk) if(lane_me_prev) face_ref363 <= {face_ref363[7:0], r_xo[1088 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref363[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1320 +: 8] !== face_ref363[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 363"); end end end
    reg [15:0] face_ref364=0;
    always @(posedge clk) if(lane_me_prev) face_ref364 <= {face_ref364[7:0], r_xo[1096 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref364[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1328 +: 8] !== face_ref364[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 364"); end end end
    reg [15:0] face_ref365=0;
    always @(posedge clk) if(lane_me_prev) face_ref365 <= {face_ref365[7:0], r_xo[1104 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref365[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1336 +: 8] !== face_ref365[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 365"); end end end
    reg [39:0] face_ref366=0;
    always @(posedge clk) if(lane_me_prev) face_ref366 <= {face_ref366[31:0], d_e[608 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref366[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1344 +: 8] !== face_ref366[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 366"); end end end
    reg [39:0] face_ref367=0;
    always @(posedge clk) if(lane_me_prev) face_ref367 <= {face_ref367[31:0], d_e[616 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref367[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1352 +: 8] !== face_ref367[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 367"); end end end
    reg [55:0] face_ref368=0;
    always @(posedge clk) if(lane_me_prev) face_ref368 <= {face_ref368[47:0], d_e[624 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref368[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1360 +: 8] !== face_ref368[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 368"); end end end
    reg [39:0] face_ref369=0;
    always @(posedge clk) if(lane_me_prev) face_ref369 <= {face_ref369[31:0], d_e[632 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref369[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1368 +: 8] !== face_ref369[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 369"); end end end
    reg [47:0] face_ref370=0;
    always @(posedge clk) if(lane_me_prev) face_ref370 <= {face_ref370[39:0], d_e[640 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref370[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1376 +: 8] !== face_ref370[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 370"); end end end
    reg [71:0] face_ref371=0;
    always @(posedge clk) if(lane_me_prev) face_ref371 <= {face_ref371[63:0], d_e[648 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref371[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1384 +: 8] !== face_ref371[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 371"); end end end
    reg [71:0] face_ref372=0;
    always @(posedge clk) if(lane_me_prev) face_ref372 <= {face_ref372[63:0], d_e[656 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref372[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1392 +: 8] !== face_ref372[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 372"); end end end
    reg [39:0] face_ref373=0;
    always @(posedge clk) if(lane_me_prev) face_ref373 <= {face_ref373[31:0], d_e[664 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref373[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1400 +: 8] !== face_ref373[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 373"); end end end
    reg [39:0] face_ref374=0;
    always @(posedge clk) if(lane_me_prev) face_ref374 <= {face_ref374[31:0], d_e[672 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref374[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1408 +: 8] !== face_ref374[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 374"); end end end
    reg [71:0] face_ref375=0;
    always @(posedge clk) if(lane_me_prev) face_ref375 <= {face_ref375[63:0], d_e[680 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref375[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1416 +: 8] !== face_ref375[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 375"); end end end
    reg [39:0] face_ref376=0;
    always @(posedge clk) if(lane_me_prev) face_ref376 <= {face_ref376[31:0], d_e[688 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref376[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1424 +: 8] !== face_ref376[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 376"); end end end
    reg [39:0] face_ref377=0;
    always @(posedge clk) if(lane_me_prev) face_ref377 <= {face_ref377[31:0], d_e[696 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref377[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1432 +: 8] !== face_ref377[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 377"); end end end
    reg [31:0] face_ref378=0;
    always @(posedge clk) if(lane_me_prev) face_ref378 <= {face_ref378[23:0], r_xo[3088 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref378[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1440 +: 8] !== face_ref378[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 378"); end end end
    reg [39:0] face_ref379=0;
    always @(posedge clk) if(lane_me_prev) face_ref379 <= {face_ref379[31:0], d_e[704 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref379[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1448 +: 8] !== face_ref379[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 379"); end end end
    reg [47:0] face_ref380=0;
    always @(posedge clk) if(lane_me_prev) face_ref380 <= {face_ref380[39:0], d_e[712 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref380[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1456 +: 8] !== face_ref380[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 380"); end end end
    reg [79:0] face_ref381=0;
    always @(posedge clk) if(lane_me_prev) face_ref381 <= {face_ref381[71:0], d_e[720 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref381[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1464 +: 8] !== face_ref381[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 381"); end end end
    reg [79:0] face_ref382=0;
    always @(posedge clk) if(lane_me_prev) face_ref382 <= {face_ref382[71:0], d_e[728 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref382[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1472 +: 8] !== face_ref382[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 382"); end end end
    reg [71:0] face_ref383=0;
    always @(posedge clk) if(lane_me_prev) face_ref383 <= {face_ref383[63:0], r_xo[3112 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref383[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1480 +: 8] !== face_ref383[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 383"); end end end
    reg [63:0] face_ref384=0;
    always @(posedge clk) if(lane_me_prev) face_ref384 <= {face_ref384[55:0], r_xo[1040 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref384[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1488 +: 8] !== face_ref384[56 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 384"); end end end
    reg [23:0] face_ref385=0;
    always @(posedge clk) if(lane_me_prev) face_ref385 <= {face_ref385[15:0], r_xo[3120 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref385[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1496 +: 8] !== face_ref385[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 385"); end end end
    reg [71:0] face_ref386=0;
    always @(posedge clk) if(lane_me_prev) face_ref386 <= {face_ref386[63:0], r_xo[3648 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref386[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1504 +: 8] !== face_ref386[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 386"); end end end
    reg [71:0] face_ref387=0;
    always @(posedge clk) if(lane_me_prev) face_ref387 <= {face_ref387[63:0], r_xo[1320 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref387[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1512 +: 8] !== face_ref387[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 387"); end end end
    reg [71:0] face_ref388=0;
    always @(posedge clk) if(lane_me_prev) face_ref388 <= {face_ref388[63:0], r_xo[808 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref388[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1520 +: 8] !== face_ref388[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 388"); end end end
    reg [63:0] face_ref389=0;
    always @(posedge clk) if(lane_me_prev) face_ref389 <= {face_ref389[55:0], r_xo[1064 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref389[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1528 +: 8] !== face_ref389[56 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 389"); end end end
    reg [63:0] face_ref390=0;
    always @(posedge clk) if(lane_me_prev) face_ref390 <= {face_ref390[55:0], r_xo[1072 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref390[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1536 +: 8] !== face_ref390[56 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 390"); end end end
    reg [23:0] face_ref391=0;
    always @(posedge clk) if(lane_me_prev) face_ref391 <= {face_ref391[15:0], d_w[1584 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref391[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[888 +: 8] !== face_ref391[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 391"); end end end
    reg [63:0] face_ref392=0;
    always @(posedge clk) if(lane_me_prev) face_ref392 <= {face_ref392[55:0], d_e[736 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref392[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1544 +: 8] !== face_ref392[56 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 392"); end end end
    reg [39:0] face_ref393=0;
    always @(posedge clk) if(lane_me_prev) face_ref393 <= {face_ref393[31:0], d_w[1592 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref393[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[696 +: 8] !== face_ref393[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 393"); end end end
    reg [39:0] face_ref394=0;
    always @(posedge clk) if(lane_me_prev) face_ref394 <= {face_ref394[31:0], d_w[1600 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref394[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[704 +: 8] !== face_ref394[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 394"); end end end
    reg [31:0] face_ref395=0;
    always @(posedge clk) if(lane_me_prev) face_ref395 <= {face_ref395[23:0], d_w[1608 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref395[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[896 +: 8] !== face_ref395[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 395"); end end end
    reg [31:0] face_ref396=0;
    always @(posedge clk) if(lane_me_prev) face_ref396 <= {face_ref396[23:0], d_w[1616 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref396[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[904 +: 8] !== face_ref396[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 396"); end end end
    reg [31:0] face_ref397=0;
    always @(posedge clk) if(lane_me_prev) face_ref397 <= {face_ref397[23:0], d_w[1624 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref397[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[912 +: 8] !== face_ref397[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 397"); end end end
    reg [31:0] face_ref398=0;
    always @(posedge clk) if(lane_me_prev) face_ref398 <= {face_ref398[23:0], d_w[1632 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref398[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[920 +: 8] !== face_ref398[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 398"); end end end
    reg [23:0] face_ref399=0;
    always @(posedge clk) if(lane_me_prev) face_ref399 <= {face_ref399[15:0], d_w[1640 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref399[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[928 +: 8] !== face_ref399[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 399"); end end end
    reg [23:0] face_ref400=0;
    always @(posedge clk) if(lane_me_prev) face_ref400 <= {face_ref400[15:0], d_w[1648 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref400[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[936 +: 8] !== face_ref400[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 400"); end end end
    reg [23:0] face_ref401=0;
    always @(posedge clk) if(lane_me_prev) face_ref401 <= {face_ref401[15:0], d_w[1656 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref401[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[944 +: 8] !== face_ref401[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 401"); end end end
    reg [55:0] face_ref402=0;
    always @(posedge clk) if(lane_me_prev) face_ref402 <= {face_ref402[47:0], r_xo[3072 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref402[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1552 +: 8] !== face_ref402[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 402"); end end end
    reg [55:0] face_ref403=0;
    always @(posedge clk) if(lane_me_prev) face_ref403 <= {face_ref403[47:0], r_xo[3360 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref403[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1560 +: 8] !== face_ref403[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 403"); end end end
    reg [23:0] face_ref404=0;
    always @(posedge clk) if(lane_me_prev) face_ref404 <= {face_ref404[15:0], d_w[1664 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref404[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[952 +: 8] !== face_ref404[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 404"); end end end
    reg [23:0] face_ref405=0;
    always @(posedge clk) if(lane_me_prev) face_ref405 <= {face_ref405[15:0], d_w[1672 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref405[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[960 +: 8] !== face_ref405[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 405"); end end end
    reg [23:0] face_ref406=0;
    always @(posedge clk) if(lane_me_prev) face_ref406 <= {face_ref406[15:0], d_w[1680 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref406[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[968 +: 8] !== face_ref406[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 406"); end end end
    reg [23:0] face_ref407=0;
    always @(posedge clk) if(lane_me_prev) face_ref407 <= {face_ref407[15:0], d_w[1688 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref407[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[976 +: 8] !== face_ref407[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 407"); end end end
    reg [39:0] face_ref408=0;
    always @(posedge clk) if(lane_me_prev) face_ref408 <= {face_ref408[31:0], d_w[1696 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref408[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[712 +: 8] !== face_ref408[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 408"); end end end
    reg [39:0] face_ref409=0;
    always @(posedge clk) if(lane_me_prev) face_ref409 <= {face_ref409[31:0], d_w[1704 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref409[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[720 +: 8] !== face_ref409[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 409"); end end end
    reg [55:0] face_ref410=0;
    always @(posedge clk) if(lane_me_prev) face_ref410 <= {face_ref410[47:0], d_e[744 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref410[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1568 +: 8] !== face_ref410[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 410"); end end end
    reg [55:0] face_ref411=0;
    always @(posedge clk) if(lane_me_prev) face_ref411 <= {face_ref411[47:0], d_e[752 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref411[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1576 +: 8] !== face_ref411[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 411"); end end end
    reg [39:0] face_ref412=0;
    always @(posedge clk) if(lane_me_prev) face_ref412 <= {face_ref412[31:0], d_e[760 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref412[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1584 +: 8] !== face_ref412[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 412"); end end end
    reg [63:0] face_ref413=0;
    always @(posedge clk) if(lane_me_prev) face_ref413 <= {face_ref413[55:0], d_w[1712 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref413[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[728 +: 8] !== face_ref413[56 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 413"); end end end
    reg [55:0] face_ref414=0;
    always @(posedge clk) if(lane_me_prev) face_ref414 <= {face_ref414[47:0], r_xo[3616 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref414[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1592 +: 8] !== face_ref414[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 414"); end end end
    reg [55:0] face_ref415=0;
    always @(posedge clk) if(lane_me_prev) face_ref415 <= {face_ref415[47:0], r_xo[1312 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref415[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1600 +: 8] !== face_ref415[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 415"); end end end
    reg [63:0] face_ref416=0;
    always @(posedge clk) if(lane_me_prev) face_ref416 <= {face_ref416[55:0], r_xo[1568 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref416[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1608 +: 8] !== face_ref416[56 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 416"); end end end
    reg [87:0] face_ref417=0;
    always @(posedge clk) if(lane_me_prev) face_ref417 <= {face_ref417[79:0], d_w[1720 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref417[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[984 +: 8] !== face_ref417[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 417"); end end end
    reg [87:0] face_ref418=0;
    always @(posedge clk) if(lane_me_prev) face_ref418 <= {face_ref418[79:0], d_w[1728 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref418[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[992 +: 8] !== face_ref418[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 418"); end end end
    reg [87:0] face_ref419=0;
    always @(posedge clk) if(lane_me_prev) face_ref419 <= {face_ref419[79:0], d_w[1736 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref419[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1000 +: 8] !== face_ref419[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 419"); end end end
    reg [87:0] face_ref420=0;
    always @(posedge clk) if(lane_me_prev) face_ref420 <= {face_ref420[79:0], d_w[1744 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref420[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1008 +: 8] !== face_ref420[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 420"); end end end
    reg [39:0] face_ref421=0;
    always @(posedge clk) if(lane_me_prev) face_ref421 <= {face_ref421[31:0], d_e[768 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref421[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1616 +: 8] !== face_ref421[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 421"); end end end
    reg [71:0] face_ref422=0;
    always @(posedge clk) if(lane_me_prev) face_ref422 <= {face_ref422[63:0], d_w[1752 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref422[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[736 +: 8] !== face_ref422[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 422"); end end end
    reg [55:0] face_ref423=0;
    always @(posedge clk) if(lane_me_prev) face_ref423 <= {face_ref423[47:0], d_w[1760 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref423[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1016 +: 8] !== face_ref423[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 423"); end end end
    reg [87:0] face_ref424=0;
    always @(posedge clk) if(lane_me_prev) face_ref424 <= {face_ref424[79:0], d_w[1768 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref424[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1024 +: 8] !== face_ref424[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 424"); end end end
    reg [71:0] face_ref425=0;
    always @(posedge clk) if(lane_me_prev) face_ref425 <= {face_ref425[63:0], d_w[1776 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref425[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[744 +: 8] !== face_ref425[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 425"); end end end
    reg [55:0] face_ref426=0;
    always @(posedge clk) if(lane_me_prev) face_ref426 <= {face_ref426[47:0], d_w[1784 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref426[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1032 +: 8] !== face_ref426[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 426"); end end end
    reg [55:0] face_ref427=0;
    always @(posedge clk) if(lane_me_prev) face_ref427 <= {face_ref427[47:0], d_w[1792 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref427[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1040 +: 8] !== face_ref427[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 427"); end end end
    reg [79:0] face_ref428=0;
    always @(posedge clk) if(lane_me_prev) face_ref428 <= {face_ref428[71:0], d_w[1800 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref428[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1048 +: 8] !== face_ref428[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 428"); end end end
    reg [63:0] face_ref429=0;
    always @(posedge clk) if(lane_me_prev) face_ref429 <= {face_ref429[55:0], r_xo[1592 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref429[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1624 +: 8] !== face_ref429[56 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 429"); end end end
    reg [79:0] face_ref430=0;
    always @(posedge clk) if(lane_me_prev) face_ref430 <= {face_ref430[71:0], d_w[1808 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref430[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1056 +: 8] !== face_ref430[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 430"); end end end
    reg [55:0] face_ref431=0;
    always @(posedge clk) if(lane_me_prev) face_ref431 <= {face_ref431[47:0], r_xo[824 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref431[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1632 +: 8] !== face_ref431[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 431"); end end end
    reg [39:0] face_ref432=0;
    always @(posedge clk) if(lane_me_prev) face_ref432 <= {face_ref432[31:0], d_w[1816 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref432[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[752 +: 8] !== face_ref432[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 432"); end end end
    reg [39:0] face_ref433=0;
    always @(posedge clk) if(lane_me_prev) face_ref433 <= {face_ref433[31:0], d_w[1824 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref433[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1064 +: 8] !== face_ref433[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 433"); end end end
    reg [39:0] face_ref434=0;
    always @(posedge clk) if(lane_me_prev) face_ref434 <= {face_ref434[31:0], d_w[1832 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref434[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1072 +: 8] !== face_ref434[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 434"); end end end
    reg [39:0] face_ref435=0;
    always @(posedge clk) if(lane_me_prev) face_ref435 <= {face_ref435[31:0], d_e[776 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref435[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1640 +: 8] !== face_ref435[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 435"); end end end
    reg [39:0] face_ref436=0;
    always @(posedge clk) if(lane_me_prev) face_ref436 <= {face_ref436[31:0], d_e[784 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref436[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1648 +: 8] !== face_ref436[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 436"); end end end
    reg [63:0] face_ref437=0;
    always @(posedge clk) if(lane_me_prev) face_ref437 <= {face_ref437[55:0], d_e[792 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref437[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1656 +: 8] !== face_ref437[56 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 437"); end end end
    reg [47:0] face_ref438=0;
    always @(posedge clk) if(lane_me_prev) face_ref438 <= {face_ref438[39:0], d_e[800 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref438[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1664 +: 8] !== face_ref438[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 438"); end end end
    reg [47:0] face_ref439=0;
    always @(posedge clk) if(lane_me_prev) face_ref439 <= {face_ref439[39:0], d_e[808 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref439[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1672 +: 8] !== face_ref439[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 439"); end end end
    reg [39:0] face_ref440=0;
    always @(posedge clk) if(lane_me_prev) face_ref440 <= {face_ref440[31:0], d_w[1840 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref440[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[760 +: 8] !== face_ref440[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 440"); end end end
    reg [23:0] face_ref441=0;
    always @(posedge clk) if(lane_me_prev) face_ref441 <= {face_ref441[15:0], r_xo[3624 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref441[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1680 +: 8] !== face_ref441[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 441"); end end end
    reg [23:0] face_ref442=0;
    always @(posedge clk) if(lane_me_prev) face_ref442 <= {face_ref442[15:0], r_xo[3368 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref442[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1688 +: 8] !== face_ref442[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 442"); end end end
    reg [31:0] face_ref443=0;
    always @(posedge clk) if(lane_me_prev) face_ref443 <= {face_ref443[23:0], r_xo[3632 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref443[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1696 +: 8] !== face_ref443[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 443"); end end end
    reg [15:0] face_ref444=0;
    always @(posedge clk) if(lane_me_prev) face_ref444 <= {face_ref444[7:0], r_xo[1576 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref444[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1704 +: 8] !== face_ref444[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 444"); end end end
    reg [15:0] face_ref445=0;
    always @(posedge clk) if(lane_me_prev) face_ref445 <= {face_ref445[7:0], r_xo[1584 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref445[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1712 +: 8] !== face_ref445[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 445"); end end end
    reg [39:0] face_ref446=0;
    always @(posedge clk) if(lane_me_prev) face_ref446 <= {face_ref446[31:0], d_w[1848 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref446[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1080 +: 8] !== face_ref446[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 446"); end end end
    reg [39:0] face_ref447=0;
    always @(posedge clk) if(lane_me_prev) face_ref447 <= {face_ref447[31:0], d_w[1856 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref447[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[768 +: 8] !== face_ref447[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 447"); end end end
    reg [39:0] face_ref448=0;
    always @(posedge clk) if(lane_me_prev) face_ref448 <= {face_ref448[31:0], d_w[1864 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref448[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[776 +: 8] !== face_ref448[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 448"); end end end
    reg [71:0] face_ref449=0;
    always @(posedge clk) if(lane_me_prev) face_ref449 <= {face_ref449[63:0], d_w[1872 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref449[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[784 +: 8] !== face_ref449[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 449"); end end end
    reg [39:0] face_ref450=0;
    always @(posedge clk) if(lane_me_prev) face_ref450 <= {face_ref450[31:0], d_w[1880 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref450[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[792 +: 8] !== face_ref450[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 450"); end end end
    reg [71:0] face_ref451=0;
    always @(posedge clk) if(lane_me_prev) face_ref451 <= {face_ref451[63:0], d_w[1888 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref451[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[800 +: 8] !== face_ref451[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 451"); end end end
    reg [39:0] face_ref452=0;
    always @(posedge clk) if(lane_me_prev) face_ref452 <= {face_ref452[31:0], d_w[1896 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref452[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[808 +: 8] !== face_ref452[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 452"); end end end
    reg [55:0] face_ref453=0;
    always @(posedge clk) if(lane_me_prev) face_ref453 <= {face_ref453[47:0], d_w[1904 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref453[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1088 +: 8] !== face_ref453[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 453"); end end end
    reg [71:0] face_ref454=0;
    always @(posedge clk) if(lane_me_prev) face_ref454 <= {face_ref454[63:0], d_w[1912 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref454[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[816 +: 8] !== face_ref454[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 454"); end end end
    reg [39:0] face_ref455=0;
    always @(posedge clk) if(lane_me_prev) face_ref455 <= {face_ref455[31:0], d_w[1920 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref455[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[824 +: 8] !== face_ref455[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 455"); end end end
    reg [63:0] face_ref456=0;
    always @(posedge clk) if(lane_me_prev) face_ref456 <= {face_ref456[55:0], r_xo[3896 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref456[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1720 +: 8] !== face_ref456[56 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 456"); end end end
    reg [47:0] face_ref457=0;
    always @(posedge clk) if(lane_me_prev) face_ref457 <= {face_ref457[39:0], d_w[1928 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref457[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1096 +: 8] !== face_ref457[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 457"); end end end
    reg [39:0] face_ref458=0;
    always @(posedge clk) if(lane_me_prev) face_ref458 <= {face_ref458[31:0], d_w[1936 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref458[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[832 +: 8] !== face_ref458[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 458"); end end end
    reg [79:0] face_ref459=0;
    always @(posedge clk) if(lane_me_prev) face_ref459 <= {face_ref459[71:0], d_w[1944 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref459[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1104 +: 8] !== face_ref459[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 459"); end end end
    reg [47:0] face_ref460=0;
    always @(posedge clk) if(lane_me_prev) face_ref460 <= {face_ref460[39:0], d_w[1952 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref460[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1112 +: 8] !== face_ref460[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 460"); end end end
    reg [47:0] face_ref461=0;
    always @(posedge clk) if(lane_me_prev) face_ref461 <= {face_ref461[39:0], d_w[1960 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref461[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1120 +: 8] !== face_ref461[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 461"); end end end
    reg [79:0] face_ref462=0;
    always @(posedge clk) if(lane_me_prev) face_ref462 <= {face_ref462[71:0], d_w[1968 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref462[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1128 +: 8] !== face_ref462[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 462"); end end end
    reg [79:0] face_ref463=0;
    always @(posedge clk) if(lane_me_prev) face_ref463 <= {face_ref463[71:0], d_w[1976 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref463[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1136 +: 8] !== face_ref463[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 463"); end end end
    reg [47:0] face_ref464=0;
    always @(posedge clk) if(lane_me_prev) face_ref464 <= {face_ref464[39:0], d_w[1984 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref464[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1144 +: 8] !== face_ref464[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 464"); end end end
    reg [63:0] face_ref465=0;
    always @(posedge clk) if(lane_me_prev) face_ref465 <= {face_ref465[55:0], r_xo[1848 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref465[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1728 +: 8] !== face_ref465[56 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 465"); end end end
    reg [47:0] face_ref466=0;
    always @(posedge clk) if(lane_me_prev) face_ref466 <= {face_ref466[39:0], d_w[1992 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref466[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1152 +: 8] !== face_ref466[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 466"); end end end
    reg [55:0] face_ref467=0;
    always @(posedge clk) if(lane_me_prev) face_ref467 <= {face_ref467[47:0], r_xo[1336 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref467[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1736 +: 8] !== face_ref467[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 467"); end end end
    reg [39:0] face_ref468=0;
    always @(posedge clk) if(lane_me_prev) face_ref468 <= {face_ref468[31:0], d_e[816 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref468[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1744 +: 8] !== face_ref468[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 468"); end end end
    reg [39:0] face_ref469=0;
    always @(posedge clk) if(lane_me_prev) face_ref469 <= {face_ref469[31:0], d_e[824 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref469[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1752 +: 8] !== face_ref469[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 469"); end end end
    reg [39:0] face_ref470=0;
    always @(posedge clk) if(lane_me_prev) face_ref470 <= {face_ref470[31:0], d_e[832 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref470[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1760 +: 8] !== face_ref470[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 470"); end end end
    reg [55:0] face_ref471=0;
    always @(posedge clk) if(lane_me_prev) face_ref471 <= {face_ref471[47:0], d_w[2000 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref471[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[840 +: 8] !== face_ref471[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 471"); end end end
    reg [31:0] face_ref472=0;
    always @(posedge clk) if(lane_me_prev) face_ref472 <= {face_ref472[23:0], r_xo[3640 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref472[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1768 +: 8] !== face_ref472[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 472"); end end end
    reg [39:0] face_ref473=0;
    always @(posedge clk) if(lane_me_prev) face_ref473 <= {face_ref473[31:0], d_e[840 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref473[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1776 +: 8] !== face_ref473[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 473"); end end end
    reg [55:0] face_ref474=0;
    always @(posedge clk) if(lane_me_prev) face_ref474 <= {face_ref474[47:0], d_e[848 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref474[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1784 +: 8] !== face_ref474[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 474"); end end end
    reg [39:0] face_ref475=0;
    always @(posedge clk) if(lane_me_prev) face_ref475 <= {face_ref475[31:0], d_e[856 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref475[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1792 +: 8] !== face_ref475[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 475"); end end end
    reg [63:0] face_ref476=0;
    always @(posedge clk) if(lane_me_prev) face_ref476 <= {face_ref476[55:0], d_e[864 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref476[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1800 +: 8] !== face_ref476[56 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 476"); end end end
    reg [47:0] face_ref477=0;
    always @(posedge clk) if(lane_me_prev) face_ref477 <= {face_ref477[39:0], d_e[872 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref477[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1808 +: 8] !== face_ref477[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 477"); end end end
    reg [63:0] face_ref478=0;
    always @(posedge clk) if(lane_me_prev) face_ref478 <= {face_ref478[55:0], r_xo[3880 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref478[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1816 +: 8] !== face_ref478[56 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 478"); end end end
    reg [31:0] face_ref479=0;
    always @(posedge clk) if(lane_me_prev) face_ref479 <= {face_ref479[23:0], r_xo[3888 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref479[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1824 +: 8] !== face_ref479[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 479"); end end end
    reg [55:0] face_ref480=0;
    always @(posedge clk) if(lane_me_prev) face_ref480 <= {face_ref480[47:0], r_xo[1832 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref480[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1832 +: 8] !== face_ref480[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 480"); end end end
    reg [23:0] face_ref481=0;
    always @(posedge clk) if(lane_me_prev) face_ref481 <= {face_ref481[15:0], r_xo[1840 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref481[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1840 +: 8] !== face_ref481[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 481"); end end end
    reg [23:0] face_ref482=0;
    always @(posedge clk) if(lane_me_prev) face_ref482 <= {face_ref482[15:0], r_xo[1328 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref482[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1848 +: 8] !== face_ref482[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 482"); end end end
    reg [31:0] face_ref483=0;
    always @(posedge clk) if(lane_me_prev) face_ref483 <= {face_ref483[23:0], d_w[2008 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref483[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1160 +: 8] !== face_ref483[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 483"); end end end
    reg [39:0] face_ref484=0;
    always @(posedge clk) if(lane_me_prev) face_ref484 <= {face_ref484[31:0], d_w[2016 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref484[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[848 +: 8] !== face_ref484[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 484"); end end end
    reg [55:0] face_ref485=0;
    always @(posedge clk) if(lane_me_prev) face_ref485 <= {face_ref485[47:0], d_w[2024 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref485[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[856 +: 8] !== face_ref485[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 485"); end end end
    reg [87:0] face_ref486=0;
    always @(posedge clk) if(lane_me_prev) face_ref486 <= {face_ref486[79:0], d_w[2032 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref486[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1168 +: 8] !== face_ref486[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 486"); end end end
    reg [79:0] face_ref487=0;
    always @(posedge clk) if(lane_me_prev) face_ref487 <= {face_ref487[71:0], d_w[2040 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref487[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1176 +: 8] !== face_ref487[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 487"); end end end
    reg [39:0] face_ref488=0;
    always @(posedge clk) if(lane_me_prev) face_ref488 <= {face_ref488[31:0], d_e[880 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref488[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1856 +: 8] !== face_ref488[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 488"); end end end
    reg [39:0] face_ref489=0;
    always @(posedge clk) if(lane_me_prev) face_ref489 <= {face_ref489[31:0], d_e[888 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref489[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1864 +: 8] !== face_ref489[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 489"); end end end
    reg [39:0] face_ref490=0;
    always @(posedge clk) if(lane_me_prev) face_ref490 <= {face_ref490[31:0], d_e[896 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref490[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1872 +: 8] !== face_ref490[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 490"); end end end
    reg [39:0] face_ref491=0;
    always @(posedge clk) if(lane_me_prev) face_ref491 <= {face_ref491[31:0], d_e[904 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref491[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1880 +: 8] !== face_ref491[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 491"); end end end
    reg [39:0] face_ref492=0;
    always @(posedge clk) if(lane_me_prev) face_ref492 <= {face_ref492[31:0], d_w[2048 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref492[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[864 +: 8] !== face_ref492[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 492"); end end end
    reg [55:0] face_ref493=0;
    always @(posedge clk) if(lane_me_prev) face_ref493 <= {face_ref493[47:0], d_w[2056 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref493[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[872 +: 8] !== face_ref493[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 493"); end end end
    reg [55:0] face_ref494=0;
    always @(posedge clk) if(lane_me_prev) face_ref494 <= {face_ref494[47:0], d_w[2064 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref494[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[880 +: 8] !== face_ref494[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 494"); end end end
    reg [55:0] face_ref495=0;
    always @(posedge clk) if(lane_me_prev) face_ref495 <= {face_ref495[47:0], d_w[2072 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref495[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[888 +: 8] !== face_ref495[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 495"); end end end
    reg [55:0] face_ref496=0;
    always @(posedge clk) if(lane_me_prev) face_ref496 <= {face_ref496[47:0], d_w[2080 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref496[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[896 +: 8] !== face_ref496[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 496"); end end end
    reg [39:0] face_ref497=0;
    always @(posedge clk) if(lane_me_prev) face_ref497 <= {face_ref497[31:0], d_w[2088 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref497[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[904 +: 8] !== face_ref497[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 497"); end end end
    reg [39:0] face_ref498=0;
    always @(posedge clk) if(lane_me_prev) face_ref498 <= {face_ref498[31:0], d_w[2096 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref498[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[912 +: 8] !== face_ref498[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 498"); end end end
    reg [47:0] face_ref499=0;
    always @(posedge clk) if(lane_me_prev) face_ref499 <= {face_ref499[39:0], r_xo[3872 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref499[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1888 +: 8] !== face_ref499[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 499"); end end end
    reg [39:0] face_ref500=0;
    always @(posedge clk) if(lane_me_prev) face_ref500 <= {face_ref500[31:0], d_e[912 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref500[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1896 +: 8] !== face_ref500[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 500"); end end end
    reg [71:0] face_ref501=0;
    always @(posedge clk) if(lane_me_prev) face_ref501 <= {face_ref501[63:0], d_e[920 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref501[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1904 +: 8] !== face_ref501[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 501"); end end end
    reg [55:0] face_ref502=0;
    always @(posedge clk) if(lane_me_prev) face_ref502 <= {face_ref502[47:0], d_e[928 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref502[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1912 +: 8] !== face_ref502[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 502"); end end end
    reg [79:0] face_ref503=0;
    always @(posedge clk) if(lane_me_prev) face_ref503 <= {face_ref503[71:0], d_e[936 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref503[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1920 +: 8] !== face_ref503[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 503"); end end end
    reg [47:0] face_ref504=0;
    always @(posedge clk) if(lane_me_prev) face_ref504 <= {face_ref504[39:0], d_e[944 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref504[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1928 +: 8] !== face_ref504[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 504"); end end end
    reg [79:0] face_ref505=0;
    always @(posedge clk) if(lane_me_prev) face_ref505 <= {face_ref505[71:0], d_e[952 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref505[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1936 +: 8] !== face_ref505[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 505"); end end end
    reg [63:0] face_ref506=0;
    always @(posedge clk) if(lane_me_prev) face_ref506 <= {face_ref506[55:0], r_xo[256 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref506[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1944 +: 8] !== face_ref506[56 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 506"); end end end
    reg [63:0] face_ref507=0;
    always @(posedge clk) if(lane_me_prev) face_ref507 <= {face_ref507[55:0], r_xo[0 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref507[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1952 +: 8] !== face_ref507[56 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 507"); end end end
    reg [63:0] face_ref508=0;
    always @(posedge clk) if(lane_me_prev) face_ref508 <= {face_ref508[55:0], r_xo[264 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref508[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1960 +: 8] !== face_ref508[56 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 508"); end end end
    reg [63:0] face_ref509=0;
    always @(posedge clk) if(lane_me_prev) face_ref509 <= {face_ref509[55:0], r_xo[8 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref509[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1968 +: 8] !== face_ref509[56 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 509"); end end end
    reg [79:0] face_ref510=0;
    always @(posedge clk) if(lane_me_prev) face_ref510 <= {face_ref510[71:0], r_xo[3912 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref510[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1976 +: 8] !== face_ref510[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 510"); end end end
    reg [63:0] face_ref511=0;
    always @(posedge clk) if(lane_me_prev) face_ref511 <= {face_ref511[55:0], r_xo[16 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref511[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1984 +: 8] !== face_ref511[56 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 511"); end end end
    reg [79:0] face_ref512=0;
    always @(posedge clk) if(lane_me_prev) face_ref512 <= {face_ref512[71:0], r_xo[3400 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref512[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[1992 +: 8] !== face_ref512[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 512"); end end end
    reg [71:0] face_ref513=0;
    always @(posedge clk) if(lane_me_prev) face_ref513 <= {face_ref513[63:0], r_xo[24 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref513[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2000 +: 8] !== face_ref513[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 513"); end end end
    reg [79:0] face_ref514=0;
    always @(posedge clk) if(lane_me_prev) face_ref514 <= {face_ref514[71:0], r_xo[3408 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref514[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2008 +: 8] !== face_ref514[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 514"); end end end
    reg [79:0] face_ref515=0;
    always @(posedge clk) if(lane_me_prev) face_ref515 <= {face_ref515[71:0], r_xo[1864 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref515[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2016 +: 8] !== face_ref515[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 515"); end end end
    reg [79:0] face_ref516=0;
    always @(posedge clk) if(lane_me_prev) face_ref516 <= {face_ref516[71:0], r_xo[304 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref516[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2024 +: 8] !== face_ref516[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 516"); end end end
    reg [79:0] face_ref517=0;
    always @(posedge clk) if(lane_me_prev) face_ref517 <= {face_ref517[71:0], r_xo[48 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref517[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2032 +: 8] !== face_ref517[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 517"); end end end
    reg [79:0] face_ref518=0;
    always @(posedge clk) if(lane_me_prev) face_ref518 <= {face_ref518[71:0], r_xo[312 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref518[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2040 +: 8] !== face_ref518[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 518"); end end end
    reg [79:0] face_ref519=0;
    always @(posedge clk) if(lane_me_prev) face_ref519 <= {face_ref519[71:0], r_xo[56 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref519[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2048 +: 8] !== face_ref519[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 519"); end end end
    reg [79:0] face_ref520=0;
    always @(posedge clk) if(lane_me_prev) face_ref520 <= {face_ref520[71:0], r_xo[64 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref520[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2056 +: 8] !== face_ref520[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 520"); end end end
    reg [87:0] face_ref521=0;
    always @(posedge clk) if(lane_me_prev) face_ref521 <= {face_ref521[79:0], r_xo[328 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref521[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2064 +: 8] !== face_ref521[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 521"); end end end
    reg [87:0] face_ref522=0;
    always @(posedge clk) if(lane_me_prev) face_ref522 <= {face_ref522[79:0], r_xo[72 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref522[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2072 +: 8] !== face_ref522[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 522"); end end end
    reg [87:0] face_ref523=0;
    always @(posedge clk) if(lane_me_prev) face_ref523 <= {face_ref523[79:0], r_xo[336 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref523[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2080 +: 8] !== face_ref523[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 523"); end end end
    reg [87:0] face_ref524=0;
    always @(posedge clk) if(lane_me_prev) face_ref524 <= {face_ref524[79:0], r_xo[80 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref524[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2088 +: 8] !== face_ref524[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 524"); end end end
    reg [87:0] face_ref525=0;
    always @(posedge clk) if(lane_me_prev) face_ref525 <= {face_ref525[79:0], r_xo[88 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref525[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2096 +: 8] !== face_ref525[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 525"); end end end
    reg [31:0] face_ref526=0;
    always @(posedge clk) if(lane_me_prev) face_ref526 <= {face_ref526[23:0], d_w[2104 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref526[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1184 +: 8] !== face_ref526[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 526"); end end end
    reg [31:0] face_ref527=0;
    always @(posedge clk) if(lane_me_prev) face_ref527 <= {face_ref527[23:0], d_w[2112 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref527[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1192 +: 8] !== face_ref527[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 527"); end end end
    reg [31:0] face_ref528=0;
    always @(posedge clk) if(lane_me_prev) face_ref528 <= {face_ref528[23:0], d_w[2120 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref528[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1200 +: 8] !== face_ref528[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 528"); end end end
    reg [31:0] face_ref529=0;
    always @(posedge clk) if(lane_me_prev) face_ref529 <= {face_ref529[23:0], d_w[2128 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref529[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1208 +: 8] !== face_ref529[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 529"); end end end
    reg [31:0] face_ref530=0;
    always @(posedge clk) if(lane_me_prev) face_ref530 <= {face_ref530[23:0], d_w[2136 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref530[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1216 +: 8] !== face_ref530[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 530"); end end end
    reg [39:0] face_ref531=0;
    always @(posedge clk) if(lane_me_prev) face_ref531 <= {face_ref531[31:0], d_e[960 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref531[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2104 +: 8] !== face_ref531[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 531"); end end end
    reg [71:0] face_ref532=0;
    always @(posedge clk) if(lane_me_prev) face_ref532 <= {face_ref532[63:0], d_e[968 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref532[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2112 +: 8] !== face_ref532[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 532"); end end end
    reg [47:0] face_ref533=0;
    always @(posedge clk) if(lane_me_prev) face_ref533 <= {face_ref533[39:0], d_e[976 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref533[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2120 +: 8] !== face_ref533[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 533"); end end end
    reg [39:0] face_ref534=0;
    always @(posedge clk) if(lane_me_prev) face_ref534 <= {face_ref534[31:0], d_e[984 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref534[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2128 +: 8] !== face_ref534[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 534"); end end end
    reg [39:0] face_ref535=0;
    always @(posedge clk) if(lane_me_prev) face_ref535 <= {face_ref535[31:0], d_w[2144 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref535[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1224 +: 8] !== face_ref535[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 535"); end end end
    reg [87:0] face_ref536=0;
    always @(posedge clk) if(lane_me_prev) face_ref536 <= {face_ref536[79:0], d_e[992 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref536[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2136 +: 8] !== face_ref536[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 536"); end end end
    reg [87:0] face_ref537=0;
    always @(posedge clk) if(lane_me_prev) face_ref537 <= {face_ref537[79:0], d_e[1000 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref537[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2144 +: 8] !== face_ref537[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 537"); end end end
    reg [39:0] face_ref538=0;
    always @(posedge clk) if(lane_me_prev) face_ref538 <= {face_ref538[31:0], d_w[2152 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref538[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1232 +: 8] !== face_ref538[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 538"); end end end
    reg [39:0] face_ref539=0;
    always @(posedge clk) if(lane_me_prev) face_ref539 <= {face_ref539[31:0], d_w[2160 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref539[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1240 +: 8] !== face_ref539[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 539"); end end end
    reg [71:0] face_ref540=0;
    always @(posedge clk) if(lane_me_prev) face_ref540 <= {face_ref540[63:0], d_w[2168 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref540[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1248 +: 8] !== face_ref540[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 540"); end end end
    reg [39:0] face_ref541=0;
    always @(posedge clk) if(lane_me_prev) face_ref541 <= {face_ref541[31:0], d_e[1008 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref541[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2152 +: 8] !== face_ref541[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 541"); end end end
    reg [39:0] face_ref542=0;
    always @(posedge clk) if(lane_me_prev) face_ref542 <= {face_ref542[31:0], d_e[1016 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref542[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2160 +: 8] !== face_ref542[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 542"); end end end
    reg [39:0] face_ref543=0;
    always @(posedge clk) if(lane_me_prev) face_ref543 <= {face_ref543[31:0], d_w[2176 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref543[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1256 +: 8] !== face_ref543[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 543"); end end end
    reg [39:0] face_ref544=0;
    always @(posedge clk) if(lane_me_prev) face_ref544 <= {face_ref544[31:0], d_w[2184 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref544[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1264 +: 8] !== face_ref544[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 544"); end end end
    reg [39:0] face_ref545=0;
    always @(posedge clk) if(lane_me_prev) face_ref545 <= {face_ref545[31:0], d_w[2192 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref545[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1272 +: 8] !== face_ref545[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 545"); end end end
    reg [39:0] face_ref546=0;
    always @(posedge clk) if(lane_me_prev) face_ref546 <= {face_ref546[31:0], d_w[2200 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref546[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1280 +: 8] !== face_ref546[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 546"); end end end
    reg [71:0] face_ref547=0;
    always @(posedge clk) if(lane_me_prev) face_ref547 <= {face_ref547[63:0], r_xo[3664 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref547[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2168 +: 8] !== face_ref547[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 547"); end end end
    reg [39:0] face_ref548=0;
    always @(posedge clk) if(lane_me_prev) face_ref548 <= {face_ref548[31:0], d_w[2208 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref548[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1288 +: 8] !== face_ref548[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 548"); end end end
    reg [39:0] face_ref549=0;
    always @(posedge clk) if(lane_me_prev) face_ref549 <= {face_ref549[31:0], d_w[2216 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref549[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1296 +: 8] !== face_ref549[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 549"); end end end
    reg [39:0] face_ref550=0;
    always @(posedge clk) if(lane_me_prev) face_ref550 <= {face_ref550[31:0], d_w[2224 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref550[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1304 +: 8] !== face_ref550[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 550"); end end end
    reg [79:0] face_ref551=0;
    always @(posedge clk) if(lane_me_prev) face_ref551 <= {face_ref551[71:0], r_xo[1616 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref551[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2176 +: 8] !== face_ref551[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 551"); end end end
    reg [23:0] face_ref552=0;
    always @(posedge clk) if(lane_me_prev) face_ref552 <= {face_ref552[15:0], r_xo[848 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref552[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2184 +: 8] !== face_ref552[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 552"); end end end
    reg [87:0] face_ref553=0;
    always @(posedge clk) if(lane_me_prev) face_ref553 <= {face_ref553[79:0], d_w[2232 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref553[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1312 +: 8] !== face_ref553[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 553"); end end end
    reg [55:0] face_ref554=0;
    always @(posedge clk) if(lane_me_prev) face_ref554 <= {face_ref554[47:0], d_w[2240 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref554[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1320 +: 8] !== face_ref554[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 554"); end end end
    reg [23:0] face_ref555=0;
    always @(posedge clk) if(lane_me_prev) face_ref555 <= {face_ref555[15:0], d_w[2248 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref555[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1328 +: 8] !== face_ref555[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 555"); end end end
    reg [23:0] face_ref556=0;
    always @(posedge clk) if(lane_me_prev) face_ref556 <= {face_ref556[15:0], d_w[2256 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref556[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1336 +: 8] !== face_ref556[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 556"); end end end
    reg [87:0] face_ref557=0;
    always @(posedge clk) if(lane_me_prev) face_ref557 <= {face_ref557[79:0], d_w[2264 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref557[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1344 +: 8] !== face_ref557[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 557"); end end end
    reg [39:0] face_ref558=0;
    always @(posedge clk) if(lane_me_prev) face_ref558 <= {face_ref558[31:0], d_e[1024 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref558[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2192 +: 8] !== face_ref558[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 558"); end end end
    reg [39:0] face_ref559=0;
    always @(posedge clk) if(lane_me_prev) face_ref559 <= {face_ref559[31:0], d_e[1032 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref559[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2200 +: 8] !== face_ref559[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 559"); end end end
    reg [39:0] face_ref560=0;
    always @(posedge clk) if(lane_me_prev) face_ref560 <= {face_ref560[31:0], d_e[1040 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref560[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2208 +: 8] !== face_ref560[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 560"); end end end
    reg [39:0] face_ref561=0;
    always @(posedge clk) if(lane_me_prev) face_ref561 <= {face_ref561[31:0], d_e[1048 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref561[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2216 +: 8] !== face_ref561[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 561"); end end end
    reg [79:0] face_ref562=0;
    always @(posedge clk) if(lane_me_prev) face_ref562 <= {face_ref562[71:0], r_xo[3416 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref562[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2224 +: 8] !== face_ref562[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 562"); end end end
    reg [87:0] face_ref563=0;
    always @(posedge clk) if(lane_me_prev) face_ref563 <= {face_ref563[79:0], r_xo[2648 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref563[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2232 +: 8] !== face_ref563[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 563"); end end end
    reg [79:0] face_ref564=0;
    always @(posedge clk) if(lane_me_prev) face_ref564 <= {face_ref564[71:0], r_xo[600 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref564[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2240 +: 8] !== face_ref564[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 564"); end end end
    reg [31:0] face_ref565=0;
    always @(posedge clk) if(lane_me_prev) face_ref565 <= {face_ref565[23:0], d_w[2272 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref565[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1352 +: 8] !== face_ref565[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 565"); end end end
    reg [95:0] face_ref566=0;
    always @(posedge clk) if(lane_me_prev) face_ref566 <= {face_ref566[87:0], d_w[2280 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref566[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1360 +: 8] !== face_ref566[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 566"); end end end
    reg [87:0] face_ref567=0;
    always @(posedge clk) if(lane_me_prev) face_ref567 <= {face_ref567[79:0], d_w[2288 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref567[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1368 +: 8] !== face_ref567[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 567"); end end end
    reg [39:0] face_ref568=0;
    always @(posedge clk) if(lane_me_prev) face_ref568 <= {face_ref568[31:0], d_e[1056 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref568[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2248 +: 8] !== face_ref568[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 568"); end end end
    reg [79:0] face_ref569=0;
    always @(posedge clk) if(lane_me_prev) face_ref569 <= {face_ref569[71:0], d_e[1064 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref569[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2256 +: 8] !== face_ref569[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 569"); end end end
    reg [23:0] face_ref570=0;
    always @(posedge clk) if(lane_me_prev) face_ref570 <= {face_ref570[15:0], r_xo[2904 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref570[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2264 +: 8] !== face_ref570[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 570"); end end end
    reg [79:0] face_ref571=0;
    always @(posedge clk) if(lane_me_prev) face_ref571 <= {face_ref571[71:0], r_xo[1624 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref571[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2272 +: 8] !== face_ref571[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 571"); end end end
    reg [87:0] face_ref572=0;
    always @(posedge clk) if(lane_me_prev) face_ref572 <= {face_ref572[79:0], r_xo[344 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref572[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2280 +: 8] !== face_ref572[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 572"); end end end
    reg [23:0] face_ref573=0;
    always @(posedge clk) if(lane_me_prev) face_ref573 <= {face_ref573[15:0], r_xo[1136 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref573[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2288 +: 8] !== face_ref573[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 573"); end end end
    reg [31:0] face_ref574=0;
    always @(posedge clk) if(lane_me_prev) face_ref574 <= {face_ref574[23:0], d_w[2296 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref574[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1376 +: 8] !== face_ref574[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 574"); end end end
    reg [23:0] face_ref575=0;
    always @(posedge clk) if(lane_me_prev) face_ref575 <= {face_ref575[15:0], r_xo[3176 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref575[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2296 +: 8] !== face_ref575[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 575"); end end end
    reg [39:0] face_ref576=0;
    always @(posedge clk) if(lane_me_prev) face_ref576 <= {face_ref576[31:0], d_w[2304 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref576[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1384 +: 8] !== face_ref576[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 576"); end end end
    reg [23:0] face_ref577=0;
    always @(posedge clk) if(lane_me_prev) face_ref577 <= {face_ref577[15:0], r_xo[2920 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref577[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2304 +: 8] !== face_ref577[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 577"); end end end
    reg [39:0] face_ref578=0;
    always @(posedge clk) if(lane_me_prev) face_ref578 <= {face_ref578[31:0], d_w[2312 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref578[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1392 +: 8] !== face_ref578[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 578"); end end end
    reg [39:0] face_ref579=0;
    always @(posedge clk) if(lane_me_prev) face_ref579 <= {face_ref579[31:0], d_w[2320 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref579[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1400 +: 8] !== face_ref579[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 579"); end end end
    reg [31:0] face_ref580=0;
    always @(posedge clk) if(lane_me_prev) face_ref580 <= {face_ref580[23:0], d_w[2328 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref580[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1408 +: 8] !== face_ref580[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 580"); end end end
    reg [39:0] face_ref581=0;
    always @(posedge clk) if(lane_me_prev) face_ref581 <= {face_ref581[31:0], d_e[1072 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref581[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2312 +: 8] !== face_ref581[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 581"); end end end
    reg [47:0] face_ref582=0;
    always @(posedge clk) if(lane_me_prev) face_ref582 <= {face_ref582[39:0], d_e[1080 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref582[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2320 +: 8] !== face_ref582[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 582"); end end end
    reg [71:0] face_ref583=0;
    always @(posedge clk) if(lane_me_prev) face_ref583 <= {face_ref583[63:0], d_e[1088 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref583[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2328 +: 8] !== face_ref583[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 583"); end end end
    reg [79:0] face_ref584=0;
    always @(posedge clk) if(lane_me_prev) face_ref584 <= {face_ref584[71:0], d_e[1096 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref584[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2336 +: 8] !== face_ref584[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 584"); end end end
    reg [39:0] face_ref585=0;
    always @(posedge clk) if(lane_me_prev) face_ref585 <= {face_ref585[31:0], d_e[1104 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref585[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2344 +: 8] !== face_ref585[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 585"); end end end
    reg [39:0] face_ref586=0;
    always @(posedge clk) if(lane_me_prev) face_ref586 <= {face_ref586[31:0], d_e[1112 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref586[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2352 +: 8] !== face_ref586[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 586"); end end end
    reg [87:0] face_ref587=0;
    always @(posedge clk) if(lane_me_prev) face_ref587 <= {face_ref587[79:0], d_e[1120 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref587[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2360 +: 8] !== face_ref587[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 587"); end end end
    reg [87:0] face_ref588=0;
    always @(posedge clk) if(lane_me_prev) face_ref588 <= {face_ref588[79:0], d_e[1128 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref588[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2368 +: 8] !== face_ref588[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 588"); end end end
    reg [79:0] face_ref589=0;
    always @(posedge clk) if(lane_me_prev) face_ref589 <= {face_ref589[71:0], r_xo[3928 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref589[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2376 +: 8] !== face_ref589[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 589"); end end end
    reg [79:0] face_ref590=0;
    always @(posedge clk) if(lane_me_prev) face_ref590 <= {face_ref590[71:0], r_xo[3672 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref590[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2384 +: 8] !== face_ref590[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 590"); end end end
    reg [79:0] face_ref591=0;
    always @(posedge clk) if(lane_me_prev) face_ref591 <= {face_ref591[71:0], r_xo[1880 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref591[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2392 +: 8] !== face_ref591[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 591"); end end end
    reg [87:0] face_ref592=0;
    always @(posedge clk) if(lane_me_prev) face_ref592 <= {face_ref592[79:0], r_xo[3160 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref592[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2400 +: 8] !== face_ref592[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 592"); end end end
    reg [87:0] face_ref593=0;
    always @(posedge clk) if(lane_me_prev) face_ref593 <= {face_ref593[79:0], r_xo[1368 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref593[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2408 +: 8] !== face_ref593[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 593"); end end end
    reg [87:0] face_ref594=0;
    always @(posedge clk) if(lane_me_prev) face_ref594 <= {face_ref594[79:0], r_xo[856 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref594[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2416 +: 8] !== face_ref594[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 594"); end end end
    reg [87:0] face_ref595=0;
    always @(posedge clk) if(lane_me_prev) face_ref595 <= {face_ref595[79:0], r_xo[1112 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref595[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2424 +: 8] !== face_ref595[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 595"); end end end
    reg [95:0] face_ref596=0;
    always @(posedge clk) if(lane_me_prev) face_ref596 <= {face_ref596[87:0], d_w[2336 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref596[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1416 +: 8] !== face_ref596[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 596"); end end end
    reg [39:0] face_ref597=0;
    always @(posedge clk) if(lane_me_prev) face_ref597 <= {face_ref597[31:0], d_w[2344 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref597[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[920 +: 8] !== face_ref597[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 597"); end end end
    reg [31:0] face_ref598=0;
    always @(posedge clk) if(lane_me_prev) face_ref598 <= {face_ref598[23:0], d_w[2352 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref598[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1424 +: 8] !== face_ref598[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 598"); end end end
    reg [31:0] face_ref599=0;
    always @(posedge clk) if(lane_me_prev) face_ref599 <= {face_ref599[23:0], d_w[2360 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref599[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1432 +: 8] !== face_ref599[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 599"); end end end
    reg [31:0] face_ref600=0;
    always @(posedge clk) if(lane_me_prev) face_ref600 <= {face_ref600[23:0], d_w[2368 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref600[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1440 +: 8] !== face_ref600[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 600"); end end end
    reg [31:0] face_ref601=0;
    always @(posedge clk) if(lane_me_prev) face_ref601 <= {face_ref601[23:0], d_w[2376 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref601[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1448 +: 8] !== face_ref601[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 601"); end end end
    reg [31:0] face_ref602=0;
    always @(posedge clk) if(lane_me_prev) face_ref602 <= {face_ref602[23:0], d_w[2384 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref602[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1456 +: 8] !== face_ref602[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 602"); end end end
    reg [31:0] face_ref603=0;
    always @(posedge clk) if(lane_me_prev) face_ref603 <= {face_ref603[23:0], d_w[2392 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref603[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1464 +: 8] !== face_ref603[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 603"); end end end
    reg [31:0] face_ref604=0;
    always @(posedge clk) if(lane_me_prev) face_ref604 <= {face_ref604[23:0], d_w[2400 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref604[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1472 +: 8] !== face_ref604[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 604"); end end end
    reg [23:0] face_ref605=0;
    always @(posedge clk) if(lane_me_prev) face_ref605 <= {face_ref605[15:0], d_w[2408 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref605[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1480 +: 8] !== face_ref605[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 605"); end end end
    reg [23:0] face_ref606=0;
    always @(posedge clk) if(lane_me_prev) face_ref606 <= {face_ref606[15:0], d_w[2416 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref606[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1488 +: 8] !== face_ref606[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 606"); end end end
    reg [47:0] face_ref607=0;
    always @(posedge clk) if(lane_me_prev) face_ref607 <= {face_ref607[39:0], d_w[2424 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref607[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[928 +: 8] !== face_ref607[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 607"); end end end
    reg [39:0] face_ref608=0;
    always @(posedge clk) if(lane_me_prev) face_ref608 <= {face_ref608[31:0], d_w[2432 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref608[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[936 +: 8] !== face_ref608[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 608"); end end end
    reg [95:0] face_ref609=0;
    always @(posedge clk) if(lane_me_prev) face_ref609 <= {face_ref609[87:0], d_w[2440 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref609[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1496 +: 8] !== face_ref609[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 609"); end end end
    reg [95:0] face_ref610=0;
    always @(posedge clk) if(lane_me_prev) face_ref610 <= {face_ref610[87:0], d_w[2448 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref610[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1504 +: 8] !== face_ref610[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 610"); end end end
    reg [95:0] face_ref611=0;
    always @(posedge clk) if(lane_me_prev) face_ref611 <= {face_ref611[87:0], d_w[2456 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref611[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1512 +: 8] !== face_ref611[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 611"); end end end
    reg [71:0] face_ref612=0;
    always @(posedge clk) if(lane_me_prev) face_ref612 <= {face_ref612[63:0], d_w[2464 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref612[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[944 +: 8] !== face_ref612[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 612"); end end end
    reg [71:0] face_ref613=0;
    always @(posedge clk) if(lane_me_prev) face_ref613 <= {face_ref613[63:0], d_w[2472 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref613[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[952 +: 8] !== face_ref613[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 613"); end end end
    reg [95:0] face_ref614=0;
    always @(posedge clk) if(lane_me_prev) face_ref614 <= {face_ref614[87:0], d_w[2480 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref614[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1520 +: 8] !== face_ref614[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 614"); end end end
    reg [71:0] face_ref615=0;
    always @(posedge clk) if(lane_me_prev) face_ref615 <= {face_ref615[63:0], d_w[2488 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref615[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[960 +: 8] !== face_ref615[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 615"); end end end
    reg [71:0] face_ref616=0;
    always @(posedge clk) if(lane_me_prev) face_ref616 <= {face_ref616[63:0], d_w[2496 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref616[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[968 +: 8] !== face_ref616[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 616"); end end end
    reg [47:0] face_ref617=0;
    always @(posedge clk) if(lane_me_prev) face_ref617 <= {face_ref617[39:0], d_w[2504 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref617[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1528 +: 8] !== face_ref617[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 617"); end end end
    reg [95:0] face_ref618=0;
    always @(posedge clk) if(lane_me_prev) face_ref618 <= {face_ref618[87:0], d_w[2512 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref618[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1536 +: 8] !== face_ref618[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 618"); end end end
    reg [79:0] face_ref619=0;
    always @(posedge clk) if(lane_me_prev) face_ref619 <= {face_ref619[71:0], d_w[2520 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref619[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[976 +: 8] !== face_ref619[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 619"); end end end
    reg [95:0] face_ref620=0;
    always @(posedge clk) if(lane_me_prev) face_ref620 <= {face_ref620[87:0], d_w[2528 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref620[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1544 +: 8] !== face_ref620[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 620"); end end end
    reg [47:0] face_ref621=0;
    always @(posedge clk) if(lane_me_prev) face_ref621 <= {face_ref621[39:0], d_w[2536 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref621[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1552 +: 8] !== face_ref621[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 621"); end end end
    reg [95:0] face_ref622=0;
    always @(posedge clk) if(lane_me_prev) face_ref622 <= {face_ref622[87:0], d_w[2544 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref622[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1560 +: 8] !== face_ref622[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 622"); end end end
    reg [95:0] face_ref623=0;
    always @(posedge clk) if(lane_me_prev) face_ref623 <= {face_ref623[87:0], d_w[2552 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref623[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1568 +: 8] !== face_ref623[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 623"); end end end
    reg [95:0] face_ref624=0;
    always @(posedge clk) if(lane_me_prev) face_ref624 <= {face_ref624[87:0], d_w[2560 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref624[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1576 +: 8] !== face_ref624[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 624"); end end end
    reg [39:0] face_ref625=0;
    always @(posedge clk) if(lane_me_prev) face_ref625 <= {face_ref625[31:0], d_w[2568 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref625[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[984 +: 8] !== face_ref625[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 625"); end end end
    reg [39:0] face_ref626=0;
    always @(posedge clk) if(lane_me_prev) face_ref626 <= {face_ref626[31:0], d_w[2576 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref626[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[992 +: 8] !== face_ref626[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 626"); end end end
    reg [47:0] face_ref627=0;
    always @(posedge clk) if(lane_me_prev) face_ref627 <= {face_ref627[39:0], d_w[2584 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref627[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1000 +: 8] !== face_ref627[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 627"); end end end
    reg [47:0] face_ref628=0;
    always @(posedge clk) if(lane_me_prev) face_ref628 <= {face_ref628[39:0], d_w[2592 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref628[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1584 +: 8] !== face_ref628[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 628"); end end end
    reg [47:0] face_ref629=0;
    always @(posedge clk) if(lane_me_prev) face_ref629 <= {face_ref629[39:0], d_w[2600 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref629[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1592 +: 8] !== face_ref629[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 629"); end end end
    reg [47:0] face_ref630=0;
    always @(posedge clk) if(lane_me_prev) face_ref630 <= {face_ref630[39:0], d_w[2608 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref630[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1600 +: 8] !== face_ref630[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 630"); end end end
    reg [31:0] face_ref631=0;
    always @(posedge clk) if(lane_me_prev) face_ref631 <= {face_ref631[23:0], d_w[2616 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref631[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1608 +: 8] !== face_ref631[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 631"); end end end
    reg [31:0] face_ref632=0;
    always @(posedge clk) if(lane_me_prev) face_ref632 <= {face_ref632[23:0], d_w[2624 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref632[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1616 +: 8] !== face_ref632[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 632"); end end end
    reg [71:0] face_ref633=0;
    always @(posedge clk) if(lane_me_prev) face_ref633 <= {face_ref633[63:0], d_w[2632 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref633[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1008 +: 8] !== face_ref633[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 633"); end end end
    reg [39:0] face_ref634=0;
    always @(posedge clk) if(lane_me_prev) face_ref634 <= {face_ref634[31:0], d_w[2640 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref634[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1016 +: 8] !== face_ref634[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 634"); end end end
    reg [39:0] face_ref635=0;
    always @(posedge clk) if(lane_me_prev) face_ref635 <= {face_ref635[31:0], d_w[2648 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref635[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1024 +: 8] !== face_ref635[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 635"); end end end
    reg [47:0] face_ref636=0;
    always @(posedge clk) if(lane_me_prev) face_ref636 <= {face_ref636[39:0], d_w[2656 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref636[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1032 +: 8] !== face_ref636[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 636"); end end end
    reg [39:0] face_ref637=0;
    always @(posedge clk) if(lane_me_prev) face_ref637 <= {face_ref637[31:0], d_w[2664 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref637[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1040 +: 8] !== face_ref637[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 637"); end end end
    reg [79:0] face_ref638=0;
    always @(posedge clk) if(lane_me_prev) face_ref638 <= {face_ref638[71:0], d_w[2672 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref638[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1048 +: 8] !== face_ref638[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 638"); end end end
    reg [95:0] face_ref639=0;
    always @(posedge clk) if(lane_me_prev) face_ref639 <= {face_ref639[87:0], d_w[2680 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref639[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1624 +: 8] !== face_ref639[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 639"); end end end
    reg [79:0] face_ref640=0;
    always @(posedge clk) if(lane_me_prev) face_ref640 <= {face_ref640[71:0], d_w[2688 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref640[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1056 +: 8] !== face_ref640[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 640"); end end end
    reg [95:0] face_ref641=0;
    always @(posedge clk) if(lane_me_prev) face_ref641 <= {face_ref641[87:0], d_w[2696 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref641[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1632 +: 8] !== face_ref641[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 641"); end end end
    reg [95:0] face_ref642=0;
    always @(posedge clk) if(lane_me_prev) face_ref642 <= {face_ref642[87:0], d_w[2704 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref642[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1640 +: 8] !== face_ref642[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 642"); end end end
    reg [95:0] face_ref643=0;
    always @(posedge clk) if(lane_me_prev) face_ref643 <= {face_ref643[87:0], d_w[2712 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref643[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1648 +: 8] !== face_ref643[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 643"); end end end
    reg [47:0] face_ref644=0;
    always @(posedge clk) if(lane_me_prev) face_ref644 <= {face_ref644[39:0], d_w[2720 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref644[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1656 +: 8] !== face_ref644[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 644"); end end end
    reg [95:0] face_ref645=0;
    always @(posedge clk) if(lane_me_prev) face_ref645 <= {face_ref645[87:0], d_w[2728 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref645[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1664 +: 8] !== face_ref645[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 645"); end end end
    reg [55:0] face_ref646=0;
    always @(posedge clk) if(lane_me_prev) face_ref646 <= {face_ref646[47:0], d_w[2736 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref646[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1064 +: 8] !== face_ref646[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 646"); end end end
    reg [79:0] face_ref647=0;
    always @(posedge clk) if(lane_me_prev) face_ref647 <= {face_ref647[71:0], d_w[2744 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref647[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1072 +: 8] !== face_ref647[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 647"); end end end
    reg [47:0] face_ref648=0;
    always @(posedge clk) if(lane_me_prev) face_ref648 <= {face_ref648[39:0], d_w[2752 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref648[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1080 +: 8] !== face_ref648[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 648"); end end end
    reg [47:0] face_ref649=0;
    always @(posedge clk) if(lane_me_prev) face_ref649 <= {face_ref649[39:0], d_w[2760 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref649[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1672 +: 8] !== face_ref649[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 649"); end end end
    reg [55:0] face_ref650=0;
    always @(posedge clk) if(lane_me_prev) face_ref650 <= {face_ref650[47:0], d_w[2768 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref650[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1088 +: 8] !== face_ref650[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 650"); end end end
    reg [95:0] face_ref651=0;
    always @(posedge clk) if(lane_me_prev) face_ref651 <= {face_ref651[87:0], d_w[2776 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref651[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1680 +: 8] !== face_ref651[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 651"); end end end
    reg [55:0] face_ref652=0;
    always @(posedge clk) if(lane_me_prev) face_ref652 <= {face_ref652[47:0], d_w[2784 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref652[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1096 +: 8] !== face_ref652[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 652"); end end end
    reg [39:0] face_ref653=0;
    always @(posedge clk) if(lane_me_prev) face_ref653 <= {face_ref653[31:0], d_w[2792 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref653[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1104 +: 8] !== face_ref653[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 653"); end end end
    reg [39:0] face_ref654=0;
    always @(posedge clk) if(lane_me_prev) face_ref654 <= {face_ref654[31:0], d_w[2800 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref654[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1112 +: 8] !== face_ref654[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 654"); end end end
    reg [95:0] face_ref655=0;
    always @(posedge clk) if(lane_me_prev) face_ref655 <= {face_ref655[87:0], r_xo[656 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref655[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1688 +: 8] !== face_ref655[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 655"); end end end
    reg [15:0] face_ref656=0;
    always @(posedge clk) if(lane_me_prev) face_ref656 <= {face_ref656[7:0], r_xo[424 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref656[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1696 +: 8] !== face_ref656[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 656"); end end end
    reg [15:0] face_ref657=0;
    always @(posedge clk) if(lane_me_prev) face_ref657 <= {face_ref657[7:0], r_xo[168 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref657[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1704 +: 8] !== face_ref657[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 657"); end end end
    reg [15:0] face_ref658=0;
    always @(posedge clk) if(lane_me_prev) face_ref658 <= {face_ref658[7:0], r_xo[416 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref658[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1712 +: 8] !== face_ref658[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 658"); end end end
    reg [15:0] face_ref659=0;
    always @(posedge clk) if(lane_me_prev) face_ref659 <= {face_ref659[7:0], r_xo[160 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref659[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1720 +: 8] !== face_ref659[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 659"); end end end
    reg [95:0] face_ref660=0;
    always @(posedge clk) if(lane_me_prev) face_ref660 <= {face_ref660[87:0], r_xo[408 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref660[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1728 +: 8] !== face_ref660[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 660"); end end end
    reg [95:0] face_ref661=0;
    always @(posedge clk) if(lane_me_prev) face_ref661 <= {face_ref661[87:0], r_xo[152 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref661[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1736 +: 8] !== face_ref661[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 661"); end end end
    reg [15:0] face_ref662=0;
    always @(posedge clk) if(lane_me_prev) face_ref662 <= {face_ref662[7:0], r_xo[144 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref662[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1744 +: 8] !== face_ref662[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 662"); end end end
    reg [31:0] face_ref663=0;
    always @(posedge clk) if(lane_me_prev) face_ref663 <= {face_ref663[23:0], r_xo[3192 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref663[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1752 +: 8] !== face_ref663[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 663"); end end end
    reg [95:0] face_ref664=0;
    always @(posedge clk) if(lane_me_prev) face_ref664 <= {face_ref664[87:0], r_xo[3208 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref664[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1760 +: 8] !== face_ref664[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 664"); end end end
    reg [95:0] face_ref665=0;
    always @(posedge clk) if(lane_me_prev) face_ref665 <= {face_ref665[87:0], r_xo[648 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref665[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1768 +: 8] !== face_ref665[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 665"); end end end
    reg [95:0] face_ref666=0;
    always @(posedge clk) if(lane_me_prev) face_ref666 <= {face_ref666[87:0], r_xo[392 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref666[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1776 +: 8] !== face_ref666[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 666"); end end end
    reg [95:0] face_ref667=0;
    always @(posedge clk) if(lane_me_prev) face_ref667 <= {face_ref667[87:0], r_xo[136 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref667[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1784 +: 8] !== face_ref667[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 667"); end end end
    reg [47:0] face_ref668=0;
    always @(posedge clk) if(lane_me_prev) face_ref668 <= {face_ref668[39:0], r_xo[2048 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref668[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1792 +: 8] !== face_ref668[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 668"); end end end
    reg [15:0] face_ref669=0;
    always @(posedge clk) if(lane_me_prev) face_ref669 <= {face_ref669[7:0], r_xo[2056 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref669[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1800 +: 8] !== face_ref669[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 669"); end end end
    reg [15:0] face_ref670=0;
    always @(posedge clk) if(lane_me_prev) face_ref670 <= {face_ref670[7:0], r_xo[2064 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref670[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1808 +: 8] !== face_ref670[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 670"); end end end
    reg [15:0] face_ref671=0;
    always @(posedge clk) if(lane_me_prev) face_ref671 <= {face_ref671[7:0], r_xo[2072 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref671[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1816 +: 8] !== face_ref671[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 671"); end end end
    reg [15:0] face_ref672=0;
    always @(posedge clk) if(lane_me_prev) face_ref672 <= {face_ref672[7:0], r_xo[2080 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref672[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1824 +: 8] !== face_ref672[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 672"); end end end
    reg [15:0] face_ref673=0;
    always @(posedge clk) if(lane_me_prev) face_ref673 <= {face_ref673[7:0], r_xo[2088 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref673[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1832 +: 8] !== face_ref673[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 673"); end end end
    reg [23:0] face_ref674=0;
    always @(posedge clk) if(lane_me_prev) face_ref674 <= {face_ref674[15:0], r_xo[2096 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref674[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1840 +: 8] !== face_ref674[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 674"); end end end
    reg [23:0] face_ref675=0;
    always @(posedge clk) if(lane_me_prev) face_ref675 <= {face_ref675[15:0], r_xo[760 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref675[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1848 +: 8] !== face_ref675[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 675"); end end end
    reg [23:0] face_ref676=0;
    always @(posedge clk) if(lane_me_prev) face_ref676 <= {face_ref676[15:0], r_xo[2104 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref676[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1856 +: 8] !== face_ref676[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 676"); end end end
    reg [23:0] face_ref677=0;
    always @(posedge clk) if(lane_me_prev) face_ref677 <= {face_ref677[15:0], r_xo[504 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref677[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1864 +: 8] !== face_ref677[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 677"); end end end
    reg [23:0] face_ref678=0;
    always @(posedge clk) if(lane_me_prev) face_ref678 <= {face_ref678[15:0], r_xo[752 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref678[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1872 +: 8] !== face_ref678[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 678"); end end end
    reg [63:0] face_ref679=0;
    always @(posedge clk) if(lane_me_prev) face_ref679 <= {face_ref679[55:0], r_xo[2112 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref679[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1880 +: 8] !== face_ref679[56 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 679"); end end end
    reg [15:0] face_ref680=0;
    always @(posedge clk) if(lane_me_prev) face_ref680 <= {face_ref680[7:0], r_xo[248 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref680[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1888 +: 8] !== face_ref680[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 680"); end end end
    reg [63:0] face_ref681=0;
    always @(posedge clk) if(lane_me_prev) face_ref681 <= {face_ref681[55:0], r_xo[240 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref681[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1896 +: 8] !== face_ref681[56 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 681"); end end end
    reg [79:0] face_ref682=0;
    always @(posedge clk) if(lane_me_prev) face_ref682 <= {face_ref682[71:0], r_xo[744 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref682[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1904 +: 8] !== face_ref682[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 682"); end end end
    reg [79:0] face_ref683=0;
    always @(posedge clk) if(lane_me_prev) face_ref683 <= {face_ref683[71:0], r_xo[2120 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref683[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1912 +: 8] !== face_ref683[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 683"); end end end
    reg [15:0] face_ref684=0;
    always @(posedge clk) if(lane_me_prev) face_ref684 <= {face_ref684[7:0], r_xo[488 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref684[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1920 +: 8] !== face_ref684[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 684"); end end end
    reg [63:0] face_ref685=0;
    always @(posedge clk) if(lane_me_prev) face_ref685 <= {face_ref685[55:0], r_xo[736 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref685[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1928 +: 8] !== face_ref685[56 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 685"); end end end
    reg [79:0] face_ref686=0;
    always @(posedge clk) if(lane_me_prev) face_ref686 <= {face_ref686[71:0], r_xo[2128 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref686[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1936 +: 8] !== face_ref686[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 686"); end end end
    reg [79:0] face_ref687=0;
    always @(posedge clk) if(lane_me_prev) face_ref687 <= {face_ref687[71:0], r_xo[232 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref687[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1944 +: 8] !== face_ref687[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 687"); end end end
    reg [79:0] face_ref688=0;
    always @(posedge clk) if(lane_me_prev) face_ref688 <= {face_ref688[71:0], r_xo[2136 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref688[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1952 +: 8] !== face_ref688[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 688"); end end end
    reg [23:0] face_ref689=0;
    always @(posedge clk) if(lane_me_prev) face_ref689 <= {face_ref689[15:0], r_xo[720 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref689[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1960 +: 8] !== face_ref689[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 689"); end end end
    reg [87:0] face_ref690=0;
    always @(posedge clk) if(lane_me_prev) face_ref690 <= {face_ref690[79:0], r_xo[2144 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref690[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1968 +: 8] !== face_ref690[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 690"); end end end
    reg [87:0] face_ref691=0;
    always @(posedge clk) if(lane_me_prev) face_ref691 <= {face_ref691[79:0], r_xo[464 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref691[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1976 +: 8] !== face_ref691[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 691"); end end end
    reg [87:0] face_ref692=0;
    always @(posedge clk) if(lane_me_prev) face_ref692 <= {face_ref692[79:0], r_xo[712 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref692[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1984 +: 8] !== face_ref692[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 692"); end end end
    reg [87:0] face_ref693=0;
    always @(posedge clk) if(lane_me_prev) face_ref693 <= {face_ref693[79:0], r_xo[2152 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref693[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[1992 +: 8] !== face_ref693[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 693"); end end end
    reg [23:0] face_ref694=0;
    always @(posedge clk) if(lane_me_prev) face_ref694 <= {face_ref694[15:0], r_xo[208 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref694[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2000 +: 8] !== face_ref694[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 694"); end end end
    reg [87:0] face_ref695=0;
    always @(posedge clk) if(lane_me_prev) face_ref695 <= {face_ref695[79:0], r_xo[2160 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref695[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2008 +: 8] !== face_ref695[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 695"); end end end
    reg [95:0] face_ref696=0;
    always @(posedge clk) if(lane_me_prev) face_ref696 <= {face_ref696[87:0], r_xo[696 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref696[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2016 +: 8] !== face_ref696[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 696"); end end end
    reg [95:0] face_ref697=0;
    always @(posedge clk) if(lane_me_prev) face_ref697 <= {face_ref697[87:0], r_xo[2168 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref697[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2024 +: 8] !== face_ref697[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 697"); end end end
    reg [95:0] face_ref698=0;
    always @(posedge clk) if(lane_me_prev) face_ref698 <= {face_ref698[87:0], r_xo[440 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref698[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2032 +: 8] !== face_ref698[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 698"); end end end
    reg [95:0] face_ref699=0;
    always @(posedge clk) if(lane_me_prev) face_ref699 <= {face_ref699[87:0], r_xo[2176 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref699[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2040 +: 8] !== face_ref699[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 699"); end end end
    reg [95:0] face_ref700=0;
    always @(posedge clk) if(lane_me_prev) face_ref700 <= {face_ref700[87:0], r_xo[184 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref700[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2048 +: 8] !== face_ref700[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 700"); end end end
    reg [95:0] face_ref701=0;
    always @(posedge clk) if(lane_me_prev) face_ref701 <= {face_ref701[87:0], r_xo[2184 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref701[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2056 +: 8] !== face_ref701[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 701"); end end end
    reg [95:0] face_ref702=0;
    always @(posedge clk) if(lane_me_prev) face_ref702 <= {face_ref702[87:0], r_xo[2192 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref702[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2064 +: 8] !== face_ref702[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 702"); end end end
    reg [95:0] face_ref703=0;
    always @(posedge clk) if(lane_me_prev) face_ref703 <= {face_ref703[87:0], r_xo[1944 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref703[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2072 +: 8] !== face_ref703[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 703"); end end end
    reg [95:0] face_ref704=0;
    always @(posedge clk) if(lane_me_prev) face_ref704 <= {face_ref704[87:0], r_xo[3480 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref704[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2080 +: 8] !== face_ref704[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 704"); end end end
    reg [95:0] face_ref705=0;
    always @(posedge clk) if(lane_me_prev) face_ref705 <= {face_ref705[87:0], r_xo[1688 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref705[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2088 +: 8] !== face_ref705[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 705"); end end end
    reg [95:0] face_ref706=0;
    always @(posedge clk) if(lane_me_prev) face_ref706 <= {face_ref706[87:0], r_xo[920 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref706[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2096 +: 8] !== face_ref706[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 706"); end end end
    reg [95:0] face_ref707=0;
    always @(posedge clk) if(lane_me_prev) face_ref707 <= {face_ref707[87:0], r_xo[664 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref707[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2104 +: 8] !== face_ref707[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 707"); end end end
    reg [31:0] face_ref708=0;
    always @(posedge clk) if(lane_me_prev) face_ref708 <= {face_ref708[23:0], r_xo[1712 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref708[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2112 +: 8] !== face_ref708[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 708"); end end end
    reg [31:0] face_ref709=0;
    always @(posedge clk) if(lane_me_prev) face_ref709 <= {face_ref709[23:0], r_xo[1456 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref709[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2120 +: 8] !== face_ref709[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 709"); end end end
    reg [31:0] face_ref710=0;
    always @(posedge clk) if(lane_me_prev) face_ref710 <= {face_ref710[23:0], r_xo[1704 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref710[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2128 +: 8] !== face_ref710[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 710"); end end end
    reg [95:0] face_ref711=0;
    always @(posedge clk) if(lane_me_prev) face_ref711 <= {face_ref711[87:0], r_xo[1952 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref711[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2136 +: 8] !== face_ref711[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 711"); end end end
    reg [95:0] face_ref712=0;
    always @(posedge clk) if(lane_me_prev) face_ref712 <= {face_ref712[87:0], r_xo[1696 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref712[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2144 +: 8] !== face_ref712[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 712"); end end end
    reg [15:0] face_ref713=0;
    always @(posedge clk) if(lane_me_prev) face_ref713 <= {face_ref713[7:0], r_xo[944 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref713[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2152 +: 8] !== face_ref713[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 713"); end end end
    reg [15:0] face_ref714=0;
    always @(posedge clk) if(lane_me_prev) face_ref714 <= {face_ref714[7:0], r_xo[688 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref714[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2160 +: 8] !== face_ref714[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 714"); end end end
    reg [15:0] face_ref715=0;
    always @(posedge clk) if(lane_me_prev) face_ref715 <= {face_ref715[7:0], r_xo[936 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref715[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2168 +: 8] !== face_ref715[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 715"); end end end
    reg [15:0] face_ref716=0;
    always @(posedge clk) if(lane_me_prev) face_ref716 <= {face_ref716[7:0], r_xo[432 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref716[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2176 +: 8] !== face_ref716[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 716"); end end end
    reg [15:0] face_ref717=0;
    always @(posedge clk) if(lane_me_prev) face_ref717 <= {face_ref717[7:0], r_xo[680 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref717[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2184 +: 8] !== face_ref717[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 717"); end end end
    reg [95:0] face_ref718=0;
    always @(posedge clk) if(lane_me_prev) face_ref718 <= {face_ref718[87:0], r_xo[928 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref718[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2192 +: 8] !== face_ref718[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 718"); end end end
    reg [15:0] face_ref719=0;
    always @(posedge clk) if(lane_me_prev) face_ref719 <= {face_ref719[7:0], r_xo[176 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref719[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2200 +: 8] !== face_ref719[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 719"); end end end
    reg [15:0] face_ref720=0;
    always @(posedge clk) if(lane_me_prev) face_ref720 <= {face_ref720[7:0], r_xo[672 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref720[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2208 +: 8] !== face_ref720[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 720"); end end end
    reg [15:0] face_ref721=0;
    always @(posedge clk) if(lane_me_prev) face_ref721 <= {face_ref721[7:0], r_xo[912 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref721[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2216 +: 8] !== face_ref721[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 721"); end end end
    reg [39:0] face_ref722=0;
    always @(posedge clk) if(lane_me_prev) face_ref722 <= {face_ref722[31:0], d_e[1136 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref722[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2224 +: 8] !== face_ref722[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 722"); end end end
    reg [39:0] face_ref723=0;
    always @(posedge clk) if(lane_me_prev) face_ref723 <= {face_ref723[31:0], d_e[1144 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref723[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2232 +: 8] !== face_ref723[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 723"); end end end
    reg [39:0] face_ref724=0;
    always @(posedge clk) if(lane_me_prev) face_ref724 <= {face_ref724[31:0], d_e[1152 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref724[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2240 +: 8] !== face_ref724[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 724"); end end end
    reg [39:0] face_ref725=0;
    always @(posedge clk) if(lane_me_prev) face_ref725 <= {face_ref725[31:0], d_e[1160 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref725[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2248 +: 8] !== face_ref725[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 725"); end end end
    reg [47:0] face_ref726=0;
    always @(posedge clk) if(lane_me_prev) face_ref726 <= {face_ref726[39:0], d_e[1168 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref726[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2256 +: 8] !== face_ref726[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 726"); end end end
    reg [47:0] face_ref727=0;
    always @(posedge clk) if(lane_me_prev) face_ref727 <= {face_ref727[39:0], d_e[1176 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref727[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2264 +: 8] !== face_ref727[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 727"); end end end
    reg [95:0] face_ref728=0;
    always @(posedge clk) if(lane_me_prev) face_ref728 <= {face_ref728[87:0], d_e[1184 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref728[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2272 +: 8] !== face_ref728[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 728"); end end end
    reg [95:0] face_ref729=0;
    always @(posedge clk) if(lane_me_prev) face_ref729 <= {face_ref729[87:0], r_xo[3976 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref729[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2280 +: 8] !== face_ref729[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 729"); end end end
    reg [31:0] face_ref730=0;
    always @(posedge clk) if(lane_me_prev) face_ref730 <= {face_ref730[23:0], r_xo[3448 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref730[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2288 +: 8] !== face_ref730[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 730"); end end end
    reg [31:0] face_ref731=0;
    always @(posedge clk) if(lane_me_prev) face_ref731 <= {face_ref731[23:0], r_xo[1912 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref731[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2296 +: 8] !== face_ref731[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 731"); end end end
    reg [95:0] face_ref732=0;
    always @(posedge clk) if(lane_me_prev) face_ref732 <= {face_ref732[87:0], r_xo[3464 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref732[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2304 +: 8] !== face_ref732[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 732"); end end end
    reg [15:0] face_ref733=0;
    always @(posedge clk) if(lane_me_prev) face_ref733 <= {face_ref733[7:0], r_xo[888 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref733[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2312 +: 8] !== face_ref733[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 733"); end end end
    reg [15:0] face_ref734=0;
    always @(posedge clk) if(lane_me_prev) face_ref734 <= {face_ref734[7:0], r_xo[896 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref734[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2320 +: 8] !== face_ref734[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 734"); end end end
    reg [95:0] face_ref735=0;
    always @(posedge clk) if(lane_me_prev) face_ref735 <= {face_ref735[87:0], r_xo[904 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref735[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2328 +: 8] !== face_ref735[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 735"); end end end
    reg [23:0] face_ref736=0;
    always @(posedge clk) if(lane_me_prev) face_ref736 <= {face_ref736[15:0], r_xo[816 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref736[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2336 +: 8] !== face_ref736[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 736"); end end end
    reg [15:0] face_ref737=0;
    always @(posedge clk) if(lane_me_prev) face_ref737 <= {face_ref737[7:0], r_xo[840 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref737[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2344 +: 8] !== face_ref737[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 737"); end end end
    reg [23:0] face_ref738=0;
    always @(posedge clk) if(lane_me_prev) face_ref738 <= {face_ref738[15:0], r_xo[864 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref738[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2352 +: 8] !== face_ref738[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 738"); end end end
    reg [23:0] face_ref739=0;
    always @(posedge clk) if(lane_me_prev) face_ref739 <= {face_ref739[15:0], r_xo[2304 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref739[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2360 +: 8] !== face_ref739[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 739"); end end end
    reg [23:0] face_ref740=0;
    always @(posedge clk) if(lane_me_prev) face_ref740 <= {face_ref740[15:0], r_xo[2312 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref740[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2368 +: 8] !== face_ref740[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 740"); end end end
    reg [15:0] face_ref741=0;
    always @(posedge clk) if(lane_me_prev) face_ref741 <= {face_ref741[7:0], r_xo[2328 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref741[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2376 +: 8] !== face_ref741[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 741"); end end end
    reg [15:0] face_ref742=0;
    always @(posedge clk) if(lane_me_prev) face_ref742 <= {face_ref742[7:0], r_xo[2336 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref742[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2384 +: 8] !== face_ref742[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 742"); end end end
    reg [23:0] face_ref743=0;
    always @(posedge clk) if(lane_me_prev) face_ref743 <= {face_ref743[15:0], r_xo[2352 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref743[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2392 +: 8] !== face_ref743[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 743"); end end end
    reg [23:0] face_ref744=0;
    always @(posedge clk) if(lane_me_prev) face_ref744 <= {face_ref744[15:0], r_xo[1016 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref744[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2400 +: 8] !== face_ref744[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 744"); end end end
    reg [23:0] face_ref745=0;
    always @(posedge clk) if(lane_me_prev) face_ref745 <= {face_ref745[15:0], r_xo[2360 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref745[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2408 +: 8] !== face_ref745[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 745"); end end end
    reg [15:0] face_ref746=0;
    always @(posedge clk) if(lane_me_prev) face_ref746 <= {face_ref746[7:0], r_xo[2376 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref746[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2416 +: 8] !== face_ref746[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 746"); end end end
    reg [15:0] face_ref747=0;
    always @(posedge clk) if(lane_me_prev) face_ref747 <= {face_ref747[7:0], r_xo[992 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref747[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2424 +: 8] !== face_ref747[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 747"); end end end
    reg [15:0] face_ref748=0;
    always @(posedge clk) if(lane_me_prev) face_ref748 <= {face_ref748[7:0], r_xo[2384 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref748[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2432 +: 8] !== face_ref748[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 748"); end end end
    reg [79:0] face_ref749=0;
    always @(posedge clk) if(lane_me_prev) face_ref749 <= {face_ref749[71:0], r_xo[2392 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref749[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2440 +: 8] !== face_ref749[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 749"); end end end
    reg [23:0] face_ref750=0;
    always @(posedge clk) if(lane_me_prev) face_ref750 <= {face_ref750[15:0], r_xo[2400 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref750[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2448 +: 8] !== face_ref750[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 750"); end end end
    reg [23:0] face_ref751=0;
    always @(posedge clk) if(lane_me_prev) face_ref751 <= {face_ref751[15:0], r_xo[2408 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref751[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2456 +: 8] !== face_ref751[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 751"); end end end
    reg [23:0] face_ref752=0;
    always @(posedge clk) if(lane_me_prev) face_ref752 <= {face_ref752[15:0], r_xo[2416 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref752[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2464 +: 8] !== face_ref752[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 752"); end end end
    reg [15:0] face_ref753=0;
    always @(posedge clk) if(lane_me_prev) face_ref753 <= {face_ref753[7:0], r_xo[2424 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref753[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2472 +: 8] !== face_ref753[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 753"); end end end
    reg [15:0] face_ref754=0;
    always @(posedge clk) if(lane_me_prev) face_ref754 <= {face_ref754[7:0], r_xo[2432 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref754[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2480 +: 8] !== face_ref754[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 754"); end end end
    reg [95:0] face_ref755=0;
    always @(posedge clk) if(lane_me_prev) face_ref755 <= {face_ref755[87:0], r_xo[2440 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref755[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2488 +: 8] !== face_ref755[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 755"); end end end
    reg [15:0] face_ref756=0;
    always @(posedge clk) if(lane_me_prev) face_ref756 <= {face_ref756[7:0], r_xo[2448 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref756[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2496 +: 8] !== face_ref756[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 756"); end end end
    reg [95:0] face_ref757=0;
    always @(posedge clk) if(lane_me_prev) face_ref757 <= {face_ref757[87:0], r_xo[1968 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref757[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2504 +: 8] !== face_ref757[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 757"); end end end
    reg [95:0] face_ref758=0;
    always @(posedge clk) if(lane_me_prev) face_ref758 <= {face_ref758[87:0], r_xo[3728 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref758[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2512 +: 8] !== face_ref758[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 758"); end end end
    reg [31:0] face_ref759=0;
    always @(posedge clk) if(lane_me_prev) face_ref759 <= {face_ref759[23:0], r_xo[3472 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref759[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2520 +: 8] !== face_ref759[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 759"); end end end
    reg [31:0] face_ref760=0;
    always @(posedge clk) if(lane_me_prev) face_ref760 <= {face_ref760[23:0], r_xo[3216 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref760[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2528 +: 8] !== face_ref760[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 760"); end end end
    reg [31:0] face_ref761=0;
    always @(posedge clk) if(lane_me_prev) face_ref761 <= {face_ref761[23:0], r_xo[1936 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref761[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2536 +: 8] !== face_ref761[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 761"); end end end
    reg [31:0] face_ref762=0;
    always @(posedge clk) if(lane_me_prev) face_ref762 <= {face_ref762[23:0], r_xo[1680 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref762[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2544 +: 8] !== face_ref762[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 762"); end end end
    reg [15:0] face_ref763=0;
    always @(posedge clk) if(lane_me_prev) face_ref763 <= {face_ref763[7:0], r_xo[1200 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref763[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2552 +: 8] !== face_ref763[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 763"); end end end
    reg [15:0] face_ref764=0;
    always @(posedge clk) if(lane_me_prev) face_ref764 <= {face_ref764[7:0], r_xo[1192 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref764[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2560 +: 8] !== face_ref764[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 764"); end end end
    reg [15:0] face_ref765=0;
    always @(posedge clk) if(lane_me_prev) face_ref765 <= {face_ref765[7:0], r_xo[1184 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref765[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2568 +: 8] !== face_ref765[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 765"); end end end
    reg [15:0] face_ref766=0;
    always @(posedge clk) if(lane_me_prev) face_ref766 <= {face_ref766[7:0], r_xo[1168 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref766[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2576 +: 8] !== face_ref766[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 766"); end end end
    reg [15:0] face_ref767=0;
    always @(posedge clk) if(lane_me_prev) face_ref767 <= {face_ref767[7:0], r_xo[400 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref767[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2584 +: 8] !== face_ref767[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 767"); end end end
    reg [39:0] face_ref768=0;
    always @(posedge clk) if(lane_me_prev) face_ref768 <= {face_ref768[31:0], d_e[1192 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref768[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2432 +: 8] !== face_ref768[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 768"); end end end
    reg [39:0] face_ref769=0;
    always @(posedge clk) if(lane_me_prev) face_ref769 <= {face_ref769[31:0], d_e[1200 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref769[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2440 +: 8] !== face_ref769[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 769"); end end end
    reg [39:0] face_ref770=0;
    always @(posedge clk) if(lane_me_prev) face_ref770 <= {face_ref770[31:0], d_e[1208 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref770[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2592 +: 8] !== face_ref770[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 770"); end end end
    reg [39:0] face_ref771=0;
    always @(posedge clk) if(lane_me_prev) face_ref771 <= {face_ref771[31:0], d_e[1216 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref771[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2600 +: 8] !== face_ref771[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 771"); end end end
    reg [31:0] face_ref772=0;
    always @(posedge clk) if(lane_me_prev) face_ref772 <= {face_ref772[23:0], r_xo[1272 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref772[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2608 +: 8] !== face_ref772[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 772"); end end end
    reg [39:0] face_ref773=0;
    always @(posedge clk) if(lane_me_prev) face_ref773 <= {face_ref773[31:0], d_e[1224 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref773[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2448 +: 8] !== face_ref773[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 773"); end end end
    reg [47:0] face_ref774=0;
    always @(posedge clk) if(lane_me_prev) face_ref774 <= {face_ref774[39:0], d_e[1232 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref774[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2456 +: 8] !== face_ref774[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 774"); end end end
    reg [95:0] face_ref775=0;
    always @(posedge clk) if(lane_me_prev) face_ref775 <= {face_ref775[87:0], d_e[1240 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref775[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2616 +: 8] !== face_ref775[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 775"); end end end
    reg [39:0] face_ref776=0;
    always @(posedge clk) if(lane_me_prev) face_ref776 <= {face_ref776[31:0], d_e[1248 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref776[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2624 +: 8] !== face_ref776[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 776"); end end end
    reg [95:0] face_ref777=0;
    always @(posedge clk) if(lane_me_prev) face_ref777 <= {face_ref777[87:0], d_e[1256 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref777[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2632 +: 8] !== face_ref777[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 777"); end end end
    reg [47:0] face_ref778=0;
    always @(posedge clk) if(lane_me_prev) face_ref778 <= {face_ref778[39:0], d_e[1264 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref778[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2640 +: 8] !== face_ref778[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 778"); end end end
    reg [23:0] face_ref779=0;
    always @(posedge clk) if(lane_me_prev) face_ref779 <= {face_ref779[15:0], r_xo[1248 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref779[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2648 +: 8] !== face_ref779[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 779"); end end end
    reg [23:0] face_ref780=0;
    always @(posedge clk) if(lane_me_prev) face_ref780 <= {face_ref780[15:0], r_xo[480 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref780[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2656 +: 8] !== face_ref780[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 780"); end end end
    reg [23:0] face_ref781=0;
    always @(posedge clk) if(lane_me_prev) face_ref781 <= {face_ref781[15:0], r_xo[224 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref781[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2664 +: 8] !== face_ref781[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 781"); end end end
    reg [23:0] face_ref782=0;
    always @(posedge clk) if(lane_me_prev) face_ref782 <= {face_ref782[15:0], r_xo[216 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref782[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1120 +: 8] !== face_ref782[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 782"); end end end
    reg [31:0] face_ref783=0;
    always @(posedge clk) if(lane_me_prev) face_ref783 <= {face_ref783[23:0], r_xo[2664 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref783[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2464 +: 8] !== face_ref783[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 783"); end end end
    reg [95:0] face_ref784=0;
    always @(posedge clk) if(lane_me_prev) face_ref784 <= {face_ref784[87:0], r_xo[3712 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref784[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2672 +: 8] !== face_ref784[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 784"); end end end
    reg [31:0] face_ref785=0;
    always @(posedge clk) if(lane_me_prev) face_ref785 <= {face_ref785[23:0], r_xo[3456 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref785[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2680 +: 8] !== face_ref785[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 785"); end end end
    reg [31:0] face_ref786=0;
    always @(posedge clk) if(lane_me_prev) face_ref786 <= {face_ref786[23:0], r_xo[2672 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref786[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2472 +: 8] !== face_ref786[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 786"); end end end
    reg [95:0] face_ref787=0;
    always @(posedge clk) if(lane_me_prev) face_ref787 <= {face_ref787[87:0], r_xo[3720 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref787[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2688 +: 8] !== face_ref787[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 787"); end end end
    reg [31:0] face_ref788=0;
    always @(posedge clk) if(lane_me_prev) face_ref788 <= {face_ref788[23:0], r_xo[3200 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref788[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2696 +: 8] !== face_ref788[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 788"); end end end
    reg [31:0] face_ref789=0;
    always @(posedge clk) if(lane_me_prev) face_ref789 <= {face_ref789[23:0], r_xo[456 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref789[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2704 +: 8] !== face_ref789[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 789"); end end end
    reg [95:0] face_ref790=0;
    always @(posedge clk) if(lane_me_prev) face_ref790 <= {face_ref790[87:0], r_xo[2680 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref790[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2480 +: 8] !== face_ref790[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 790"); end end end
    reg [95:0] face_ref791=0;
    always @(posedge clk) if(lane_me_prev) face_ref791 <= {face_ref791[87:0], r_xo[872 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref791[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2488 +: 8] !== face_ref791[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 791"); end end end
    reg [31:0] face_ref792=0;
    always @(posedge clk) if(lane_me_prev) face_ref792 <= {face_ref792[23:0], r_xo[1920 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref792[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2712 +: 8] !== face_ref792[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 792"); end end end
    reg [31:0] face_ref793=0;
    always @(posedge clk) if(lane_me_prev) face_ref793 <= {face_ref793[23:0], r_xo[200 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref793[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2720 +: 8] !== face_ref793[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 793"); end end end
    reg [31:0] face_ref794=0;
    always @(posedge clk) if(lane_me_prev) face_ref794 <= {face_ref794[23:0], r_xo[192 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref794[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2728 +: 8] !== face_ref794[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 794"); end end end
    reg [15:0] face_ref795=0;
    always @(posedge clk) if(lane_me_prev) face_ref795 <= {face_ref795[7:0], r_xo[2688 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref795[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2736 +: 8] !== face_ref795[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 795"); end end end
    reg [15:0] face_ref796=0;
    always @(posedge clk) if(lane_me_prev) face_ref796 <= {face_ref796[7:0], r_xo[2696 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref796[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2744 +: 8] !== face_ref796[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 796"); end end end
    reg [15:0] face_ref797=0;
    always @(posedge clk) if(lane_me_prev) face_ref797 <= {face_ref797[7:0], r_xo[2704 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref797[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2752 +: 8] !== face_ref797[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 797"); end end end
    reg [15:0] face_ref798=0;
    always @(posedge clk) if(lane_me_prev) face_ref798 <= {face_ref798[7:0], r_xo[1160 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref798[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2760 +: 8] !== face_ref798[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 798"); end end end
    reg [23:0] face_ref799=0;
    always @(posedge clk) if(lane_me_prev) face_ref799 <= {face_ref799[15:0], r_xo[800 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref799[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2496 +: 8] !== face_ref799[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 799"); end end end
    reg [31:0] face_ref800=0;
    always @(posedge clk) if(lane_me_prev) face_ref800 <= {face_ref800[23:0], r_xo[2616 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref800[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2504 +: 8] !== face_ref800[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 800"); end end end
    reg [39:0] face_ref801=0;
    always @(posedge clk) if(lane_me_prev) face_ref801 <= {face_ref801[31:0], d_e[1272 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref801[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2512 +: 8] !== face_ref801[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 801"); end end end
    reg [31:0] face_ref802=0;
    always @(posedge clk) if(lane_me_prev) face_ref802 <= {face_ref802[23:0], r_xo[2632 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref802[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2520 +: 8] !== face_ref802[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 802"); end end end
    reg [23:0] face_ref803=0;
    always @(posedge clk) if(lane_me_prev) face_ref803 <= {face_ref803[15:0], r_xo[2640 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref803[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2528 +: 8] !== face_ref803[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 803"); end end end
    reg [95:0] face_ref804=0;
    always @(posedge clk) if(lane_me_prev) face_ref804 <= {face_ref804[87:0], r_xo[2656 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref804[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2536 +: 8] !== face_ref804[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 804"); end end end
    reg [87:0] face_ref805=0;
    always @(posedge clk) if(lane_me_prev) face_ref805 <= {face_ref805[79:0], d_e[1280 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref805[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2768 +: 8] !== face_ref805[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 805"); end end end
    reg [87:0] face_ref806=0;
    always @(posedge clk) if(lane_me_prev) face_ref806 <= {face_ref806[79:0], d_e[1288 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref806[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2776 +: 8] !== face_ref806[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 806"); end end end
    reg [23:0] face_ref807=0;
    always @(posedge clk) if(lane_me_prev) face_ref807 <= {face_ref807[15:0], r_xo[1520 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref807[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1128 +: 8] !== face_ref807[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 807"); end end end
    reg [87:0] face_ref808=0;
    always @(posedge clk) if(lane_me_prev) face_ref808 <= {face_ref808[79:0], d_e[1296 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref808[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2784 +: 8] !== face_ref808[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 808"); end end end
    reg [23:0] face_ref809=0;
    always @(posedge clk) if(lane_me_prev) face_ref809 <= {face_ref809[15:0], r_xo[1264 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref809[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1136 +: 8] !== face_ref809[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 809"); end end end
    reg [87:0] face_ref810=0;
    always @(posedge clk) if(lane_me_prev) face_ref810 <= {face_ref810[79:0], d_e[1304 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref810[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2792 +: 8] !== face_ref810[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 810"); end end end
    reg [23:0] face_ref811=0;
    always @(posedge clk) if(lane_me_prev) face_ref811 <= {face_ref811[15:0], r_xo[1008 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref811[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1144 +: 8] !== face_ref811[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 811"); end end end
    reg [87:0] face_ref812=0;
    always @(posedge clk) if(lane_me_prev) face_ref812 <= {face_ref812[79:0], d_e[1312 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref812[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2800 +: 8] !== face_ref812[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 812"); end end end
    reg [31:0] face_ref813=0;
    always @(posedge clk) if(lane_me_prev) face_ref813 <= {face_ref813[23:0], d_e[1320 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref813[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2808 +: 8] !== face_ref813[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 813"); end end end
    reg [87:0] face_ref814=0;
    always @(posedge clk) if(lane_me_prev) face_ref814 <= {face_ref814[79:0], d_e[1328 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref814[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2816 +: 8] !== face_ref814[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 814"); end end end
    reg [87:0] face_ref815=0;
    always @(posedge clk) if(lane_me_prev) face_ref815 <= {face_ref815[79:0], d_e[1336 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref815[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2824 +: 8] !== face_ref815[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 815"); end end end
    reg [23:0] face_ref816=0;
    always @(posedge clk) if(lane_me_prev) face_ref816 <= {face_ref816[15:0], r_xo[496 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref816[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1152 +: 8] !== face_ref816[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 816"); end end end
    reg [23:0] face_ref817=0;
    always @(posedge clk) if(lane_me_prev) face_ref817 <= {face_ref817[15:0], r_xo[984 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref817[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1160 +: 8] !== face_ref817[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 817"); end end end
    reg [31:0] face_ref818=0;
    always @(posedge clk) if(lane_me_prev) face_ref818 <= {face_ref818[23:0], d_e[1344 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref818[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2832 +: 8] !== face_ref818[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 818"); end end end
    reg [23:0] face_ref819=0;
    always @(posedge clk) if(lane_me_prev) face_ref819 <= {face_ref819[15:0], r_xo[728 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref819[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1168 +: 8] !== face_ref819[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 819"); end end end
    reg [31:0] face_ref820=0;
    always @(posedge clk) if(lane_me_prev) face_ref820 <= {face_ref820[23:0], d_e[1352 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref820[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2840 +: 8] !== face_ref820[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 820"); end end end
    reg [23:0] face_ref821=0;
    always @(posedge clk) if(lane_me_prev) face_ref821 <= {face_ref821[15:0], r_xo[472 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref821[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1176 +: 8] !== face_ref821[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 821"); end end end
    reg [31:0] face_ref822=0;
    always @(posedge clk) if(lane_me_prev) face_ref822 <= {face_ref822[23:0], r_xo[1472 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref822[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2848 +: 8] !== face_ref822[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 822"); end end end
    reg [95:0] face_ref823=0;
    always @(posedge clk) if(lane_me_prev) face_ref823 <= {face_ref823[87:0], r_xo[2928 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref823[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2856 +: 8] !== face_ref823[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 823"); end end end
    reg [31:0] face_ref824=0;
    always @(posedge clk) if(lane_me_prev) face_ref824 <= {face_ref824[23:0], r_xo[1216 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref824[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2864 +: 8] !== face_ref824[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 824"); end end end
    reg [31:0] face_ref825=0;
    always @(posedge clk) if(lane_me_prev) face_ref825 <= {face_ref825[23:0], r_xo[1464 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref825[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2872 +: 8] !== face_ref825[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 825"); end end end
    reg [95:0] face_ref826=0;
    always @(posedge clk) if(lane_me_prev) face_ref826 <= {face_ref826[87:0], r_xo[2936 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref826[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2880 +: 8] !== face_ref826[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 826"); end end end
    reg [31:0] face_ref827=0;
    always @(posedge clk) if(lane_me_prev) face_ref827 <= {face_ref827[23:0], r_xo[960 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref827[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2888 +: 8] !== face_ref827[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 827"); end end end
    reg [31:0] face_ref828=0;
    always @(posedge clk) if(lane_me_prev) face_ref828 <= {face_ref828[23:0], r_xo[1960 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref828[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2896 +: 8] !== face_ref828[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 828"); end end end
    reg [31:0] face_ref829=0;
    always @(posedge clk) if(lane_me_prev) face_ref829 <= {face_ref829[23:0], r_xo[1208 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref829[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2904 +: 8] !== face_ref829[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 829"); end end end
    reg [95:0] face_ref830=0;
    always @(posedge clk) if(lane_me_prev) face_ref830 <= {face_ref830[87:0], r_xo[1392 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref830[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2912 +: 8] !== face_ref830[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 830"); end end end
    reg [31:0] face_ref831=0;
    always @(posedge clk) if(lane_me_prev) face_ref831 <= {face_ref831[23:0], r_xo[704 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref831[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2920 +: 8] !== face_ref831[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 831"); end end end
    reg [95:0] face_ref832=0;
    always @(posedge clk) if(lane_me_prev) face_ref832 <= {face_ref832[87:0], r_xo[2944 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref832[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2928 +: 8] !== face_ref832[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 832"); end end end
    reg [31:0] face_ref833=0;
    always @(posedge clk) if(lane_me_prev) face_ref833 <= {face_ref833[23:0], r_xo[952 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref833[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2936 +: 8] !== face_ref833[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 833"); end end end
    reg [31:0] face_ref834=0;
    always @(posedge clk) if(lane_me_prev) face_ref834 <= {face_ref834[23:0], r_xo[448 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref834[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2944 +: 8] !== face_ref834[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 834"); end end end
    reg [95:0] face_ref835=0;
    always @(posedge clk) if(lane_me_prev) face_ref835 <= {face_ref835[87:0], r_xo[1400 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref835[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2952 +: 8] !== face_ref835[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 835"); end end end
    reg [95:0] face_ref836=0;
    always @(posedge clk) if(lane_me_prev) face_ref836 <= {face_ref836[87:0], r_xo[880 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref836[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2960 +: 8] !== face_ref836[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 836"); end end end
    reg [95:0] face_ref837=0;
    always @(posedge clk) if(lane_me_prev) face_ref837 <= {face_ref837[87:0], r_xo[1408 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref837[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2968 +: 8] !== face_ref837[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 837"); end end end
    reg [15:0] face_ref838=0;
    always @(posedge clk) if(lane_me_prev) face_ref838 <= {face_ref838[7:0], r_xo[1448 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref838[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2976 +: 8] !== face_ref838[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 838"); end end end
    reg [15:0] face_ref839=0;
    always @(posedge clk) if(lane_me_prev) face_ref839 <= {face_ref839[7:0], r_xo[1440 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref839[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2984 +: 8] !== face_ref839[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 839"); end end end
    reg [15:0] face_ref840=0;
    always @(posedge clk) if(lane_me_prev) face_ref840 <= {face_ref840[7:0], r_xo[2960 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref840[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[2992 +: 8] !== face_ref840[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 840"); end end end
    reg [15:0] face_ref841=0;
    always @(posedge clk) if(lane_me_prev) face_ref841 <= {face_ref841[7:0], r_xo[1432 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref841[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3000 +: 8] !== face_ref841[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 841"); end end end
    reg [15:0] face_ref842=0;
    always @(posedge clk) if(lane_me_prev) face_ref842 <= {face_ref842[7:0], r_xo[1176 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref842[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3008 +: 8] !== face_ref842[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 842"); end end end
    reg [15:0] face_ref843=0;
    always @(posedge clk) if(lane_me_prev) face_ref843 <= {face_ref843[7:0], r_xo[1424 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref843[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3016 +: 8] !== face_ref843[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 843"); end end end
    reg [87:0] face_ref844=0;
    always @(posedge clk) if(lane_me_prev) face_ref844 <= {face_ref844[79:0], d_e[1360 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref844[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3024 +: 8] !== face_ref844[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 844"); end end end
    reg [31:0] face_ref845=0;
    always @(posedge clk) if(lane_me_prev) face_ref845 <= {face_ref845[23:0], d_e[1368 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref845[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3032 +: 8] !== face_ref845[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 845"); end end end
    reg [31:0] face_ref846=0;
    always @(posedge clk) if(lane_me_prev) face_ref846 <= {face_ref846[23:0], d_e[1376 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref846[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3040 +: 8] !== face_ref846[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 846"); end end end
    reg [31:0] face_ref847=0;
    always @(posedge clk) if(lane_me_prev) face_ref847 <= {face_ref847[23:0], d_e[1384 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref847[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3048 +: 8] !== face_ref847[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 847"); end end end
    reg [31:0] face_ref848=0;
    always @(posedge clk) if(lane_me_prev) face_ref848 <= {face_ref848[23:0], r_xo[1928 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref848[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3056 +: 8] !== face_ref848[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 848"); end end end
    reg [15:0] face_ref849=0;
    always @(posedge clk) if(lane_me_prev) face_ref849 <= {face_ref849[7:0], r_xo[2952 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref849[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3064 +: 8] !== face_ref849[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 849"); end end end
    reg [15:0] face_ref850=0;
    always @(posedge clk) if(lane_me_prev) face_ref850 <= {face_ref850[7:0], r_xo[1416 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref850[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3072 +: 8] !== face_ref850[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 850"); end end end
    reg [95:0] face_ref851=0;
    always @(posedge clk) if(lane_me_prev) face_ref851 <= {face_ref851[87:0], r_xo[2912 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref851[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2544 +: 8] !== face_ref851[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 851"); end end end
    reg [31:0] face_ref852=0;
    always @(posedge clk) if(lane_me_prev) face_ref852 <= {face_ref852[23:0], r_xo[1768 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref852[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1184 +: 8] !== face_ref852[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 852"); end end end
    reg [31:0] face_ref853=0;
    always @(posedge clk) if(lane_me_prev) face_ref853 <= {face_ref853[23:0], r_xo[1512 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref853[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1192 +: 8] !== face_ref853[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 853"); end end end
    reg [31:0] face_ref854=0;
    always @(posedge clk) if(lane_me_prev) face_ref854 <= {face_ref854[23:0], r_xo[1256 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref854[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1200 +: 8] !== face_ref854[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 854"); end end end
    reg [31:0] face_ref855=0;
    always @(posedge clk) if(lane_me_prev) face_ref855 <= {face_ref855[23:0], r_xo[1504 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref855[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1208 +: 8] !== face_ref855[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 855"); end end end
    reg [31:0] face_ref856=0;
    always @(posedge clk) if(lane_me_prev) face_ref856 <= {face_ref856[23:0], r_xo[1000 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref856[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1216 +: 8] !== face_ref856[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 856"); end end end
    reg [23:0] face_ref857=0;
    always @(posedge clk) if(lane_me_prev) face_ref857 <= {face_ref857[15:0], r_xo[1744 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref857[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1224 +: 8] !== face_ref857[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 857"); end end end
    reg [23:0] face_ref858=0;
    always @(posedge clk) if(lane_me_prev) face_ref858 <= {face_ref858[15:0], r_xo[1488 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref858[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1232 +: 8] !== face_ref858[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 858"); end end end
    reg [23:0] face_ref859=0;
    always @(posedge clk) if(lane_me_prev) face_ref859 <= {face_ref859[15:0], r_xo[1232 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref859[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1240 +: 8] !== face_ref859[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 859"); end end end
    reg [23:0] face_ref860=0;
    always @(posedge clk) if(lane_me_prev) face_ref860 <= {face_ref860[15:0], r_xo[976 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref860[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1248 +: 8] !== face_ref860[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 860"); end end end
    reg [87:0] face_ref861=0;
    always @(posedge clk) if(lane_me_prev) face_ref861 <= {face_ref861[79:0], d_e[1392 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref861[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2552 +: 8] !== face_ref861[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 861"); end end end
    reg [95:0] face_ref862=0;
    always @(posedge clk) if(lane_me_prev) face_ref862 <= {face_ref862[87:0], d_e[1400 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref862[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2560 +: 8] !== face_ref862[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 862"); end end end
    reg [95:0] face_ref863=0;
    always @(posedge clk) if(lane_me_prev) face_ref863 <= {face_ref863[87:0], r_xo[3184 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref863[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2568 +: 8] !== face_ref863[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 863"); end end end
    reg [95:0] face_ref864=0;
    always @(posedge clk) if(lane_me_prev) face_ref864 <= {face_ref864[87:0], r_xo[3168 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref864[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2576 +: 8] !== face_ref864[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 864"); end end end
    reg [23:0] face_ref865=0;
    always @(posedge clk) if(lane_me_prev) face_ref865 <= {face_ref865[15:0], r_xo[1528 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref865[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1256 +: 8] !== face_ref865[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 865"); end end end
    reg [55:0] face_ref866=0;
    always @(posedge clk) if(lane_me_prev) face_ref866 <= {face_ref866[47:0], d_e[1408 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref866[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2584 +: 8] !== face_ref866[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 866"); end end end
    reg [55:0] face_ref867=0;
    always @(posedge clk) if(lane_me_prev) face_ref867 <= {face_ref867[47:0], d_e[1416 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref867[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2592 +: 8] !== face_ref867[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 867"); end end end
    reg [87:0] face_ref868=0;
    always @(posedge clk) if(lane_me_prev) face_ref868 <= {face_ref868[79:0], d_e[1424 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref868[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2600 +: 8] !== face_ref868[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 868"); end end end
    reg [87:0] face_ref869=0;
    always @(posedge clk) if(lane_me_prev) face_ref869 <= {face_ref869[79:0], d_e[1432 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref869[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2608 +: 8] !== face_ref869[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 869"); end end end
    reg [95:0] face_ref870=0;
    always @(posedge clk) if(lane_me_prev) face_ref870 <= {face_ref870[87:0], d_e[1440 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref870[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2616 +: 8] !== face_ref870[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 870"); end end end
    reg [47:0] face_ref871=0;
    always @(posedge clk) if(lane_me_prev) face_ref871 <= {face_ref871[39:0], d_e[1448 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref871[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2624 +: 8] !== face_ref871[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 871"); end end end
    reg [63:0] face_ref872=0;
    always @(posedge clk) if(lane_me_prev) face_ref872 <= {face_ref872[55:0], d_e[1456 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref872[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2632 +: 8] !== face_ref872[56 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 872"); end end end
    reg [95:0] face_ref873=0;
    always @(posedge clk) if(lane_me_prev) face_ref873 <= {face_ref873[87:0], d_e[1464 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref873[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2640 +: 8] !== face_ref873[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 873"); end end end
    reg [95:0] face_ref874=0;
    always @(posedge clk) if(lane_me_prev) face_ref874 <= {face_ref874[87:0], r_xo[3432 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref874[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2648 +: 8] !== face_ref874[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 874"); end end end
    reg [95:0] face_ref875=0;
    always @(posedge clk) if(lane_me_prev) face_ref875 <= {face_ref875[87:0], r_xo[3440 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref875[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2656 +: 8] !== face_ref875[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 875"); end end end
    reg [95:0] face_ref876=0;
    always @(posedge clk) if(lane_me_prev) face_ref876 <= {face_ref876[87:0], r_xo[3936 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref876[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2664 +: 8] !== face_ref876[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 876"); end end end
    reg [95:0] face_ref877=0;
    always @(posedge clk) if(lane_me_prev) face_ref877 <= {face_ref877[87:0], r_xo[3424 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref877[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2672 +: 8] !== face_ref877[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 877"); end end end
    reg [95:0] face_ref878=0;
    always @(posedge clk) if(lane_me_prev) face_ref878 <= {face_ref878[87:0], r_xo[1888 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref878[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2680 +: 8] !== face_ref878[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 878"); end end end
    reg [95:0] face_ref879=0;
    always @(posedge clk) if(lane_me_prev) face_ref879 <= {face_ref879[87:0], r_xo[1376 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref879[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2688 +: 8] !== face_ref879[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 879"); end end end
    reg [63:0] face_ref880=0;
    always @(posedge clk) if(lane_me_prev) face_ref880 <= {face_ref880[55:0], r_xo[1992 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref880[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3080 +: 8] !== face_ref880[56 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 880"); end end end
    reg [95:0] face_ref881=0;
    always @(posedge clk) if(lane_me_prev) face_ref881 <= {face_ref881[87:0], r_xo[1736 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref881[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3088 +: 8] !== face_ref881[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 881"); end end end
    reg [95:0] face_ref882=0;
    always @(posedge clk) if(lane_me_prev) face_ref882 <= {face_ref882[87:0], r_xo[1480 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref882[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3096 +: 8] !== face_ref882[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 882"); end end end
    reg [31:0] face_ref883=0;
    always @(posedge clk) if(lane_me_prev) face_ref883 <= {face_ref883[23:0], r_xo[1224 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref883[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3104 +: 8] !== face_ref883[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 883"); end end end
    reg [31:0] face_ref884=0;
    always @(posedge clk) if(lane_me_prev) face_ref884 <= {face_ref884[23:0], r_xo[968 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref884[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3112 +: 8] !== face_ref884[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 884"); end end end
    reg [95:0] face_ref885=0;
    always @(posedge clk) if(lane_me_prev) face_ref885 <= {face_ref885[87:0], d_e[1472 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref885[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3120 +: 8] !== face_ref885[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 885"); end end end
    reg [95:0] face_ref886=0;
    always @(posedge clk) if(lane_me_prev) face_ref886 <= {face_ref886[87:0], r_xo[3696 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref886[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3128 +: 8] !== face_ref886[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 886"); end end end
    reg [95:0] face_ref887=0;
    always @(posedge clk) if(lane_me_prev) face_ref887 <= {face_ref887[87:0], r_xo[3704 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref887[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2696 +: 8] !== face_ref887[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 887"); end end end
    reg [95:0] face_ref888=0;
    always @(posedge clk) if(lane_me_prev) face_ref888 <= {face_ref888[87:0], r_xo[1896 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref888[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2704 +: 8] !== face_ref888[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 888"); end end end
    reg [47:0] face_ref889=0;
    always @(posedge clk) if(lane_me_prev) face_ref889 <= {face_ref889[39:0], d_e[1480 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref889[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2712 +: 8] !== face_ref889[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 889"); end end end
    reg [55:0] face_ref890=0;
    always @(posedge clk) if(lane_me_prev) face_ref890 <= {face_ref890[47:0], d_e[1488 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref890[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2720 +: 8] !== face_ref890[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 890"); end end end
    reg [87:0] face_ref891=0;
    always @(posedge clk) if(lane_me_prev) face_ref891 <= {face_ref891[79:0], d_e[1496 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref891[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2728 +: 8] !== face_ref891[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 891"); end end end
    reg [55:0] face_ref892=0;
    always @(posedge clk) if(lane_me_prev) face_ref892 <= {face_ref892[47:0], d_e[1504 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref892[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3136 +: 8] !== face_ref892[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 892"); end end end
    reg [87:0] face_ref893=0;
    always @(posedge clk) if(lane_me_prev) face_ref893 <= {face_ref893[79:0], d_e[1512 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref893[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2736 +: 8] !== face_ref893[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 893"); end end end
    reg [95:0] face_ref894=0;
    always @(posedge clk) if(lane_me_prev) face_ref894 <= {face_ref894[87:0], d_e[1520 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref894[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2744 +: 8] !== face_ref894[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 894"); end end end
    reg [79:0] face_ref895=0;
    always @(posedge clk) if(lane_me_prev) face_ref895 <= {face_ref895[71:0], d_e[1528 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref895[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2752 +: 8] !== face_ref895[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 895"); end end end
    reg [95:0] face_ref896=0;
    always @(posedge clk) if(lane_me_prev) face_ref896 <= {face_ref896[87:0], r_xo[3944 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref896[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2760 +: 8] !== face_ref896[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 896"); end end end
    reg [95:0] face_ref897=0;
    always @(posedge clk) if(lane_me_prev) face_ref897 <= {face_ref897[87:0], r_xo[3688 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref897[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2768 +: 8] !== face_ref897[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 897"); end end end
    reg [95:0] face_ref898=0;
    always @(posedge clk) if(lane_me_prev) face_ref898 <= {face_ref898[87:0], r_xo[1384 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref898[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2776 +: 8] !== face_ref898[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 898"); end end end
    reg [87:0] face_ref899=0;
    always @(posedge clk) if(lane_me_prev) face_ref899 <= {face_ref899[79:0], r_xo[3920 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref899[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2784 +: 8] !== face_ref899[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 899"); end end end
    reg [95:0] face_ref900=0;
    always @(posedge clk) if(lane_me_prev) face_ref900 <= {face_ref900[87:0], r_xo[3680 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref900[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2792 +: 8] !== face_ref900[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 900"); end end end
    reg [87:0] face_ref901=0;
    always @(posedge clk) if(lane_me_prev) face_ref901 <= {face_ref901[79:0], r_xo[1872 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref901[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2800 +: 8] !== face_ref901[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 901"); end end end
    reg [71:0] face_ref902=0;
    always @(posedge clk) if(lane_me_prev) face_ref902 <= {face_ref902[63:0], r_xo[2032 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref902[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1264 +: 8] !== face_ref902[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 902"); end end end
    reg [71:0] face_ref903=0;
    always @(posedge clk) if(lane_me_prev) face_ref903 <= {face_ref903[63:0], r_xo[1776 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref903[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1272 +: 8] !== face_ref903[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 903"); end end end
    reg [23:0] face_ref904=0;
    always @(posedge clk) if(lane_me_prev) face_ref904 <= {face_ref904[15:0], r_xo[1760 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref904[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1280 +: 8] !== face_ref904[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 904"); end end end
    reg [79:0] face_ref905=0;
    always @(posedge clk) if(lane_me_prev) face_ref905 <= {face_ref905[71:0], r_xo[2008 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref905[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1288 +: 8] !== face_ref905[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 905"); end end end
    reg [79:0] face_ref906=0;
    always @(posedge clk) if(lane_me_prev) face_ref906 <= {face_ref906[71:0], r_xo[1752 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref906[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1296 +: 8] !== face_ref906[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 906"); end end end
    reg [79:0] face_ref907=0;
    always @(posedge clk) if(lane_me_prev) face_ref907 <= {face_ref907[71:0], r_xo[1496 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref907[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1304 +: 8] !== face_ref907[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 907"); end end end
    reg [79:0] face_ref908=0;
    always @(posedge clk) if(lane_me_prev) face_ref908 <= {face_ref908[71:0], r_xo[1240 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref908[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1312 +: 8] !== face_ref908[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 908"); end end end
    reg [95:0] face_ref909=0;
    always @(posedge clk) if(lane_me_prev) face_ref909 <= {face_ref909[87:0], r_xo[1984 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref909[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3144 +: 8] !== face_ref909[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 909"); end end end
    reg [95:0] face_ref910=0;
    always @(posedge clk) if(lane_me_prev) face_ref910 <= {face_ref910[87:0], r_xo[1728 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref910[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3152 +: 8] !== face_ref910[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 910"); end end end
    reg [95:0] face_ref911=0;
    always @(posedge clk) if(lane_me_prev) face_ref911 <= {face_ref911[87:0], r_xo[1976 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref911[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3160 +: 8] !== face_ref911[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 911"); end end end
    reg [95:0] face_ref912=0;
    always @(posedge clk) if(lane_me_prev) face_ref912 <= {face_ref912[87:0], r_xo[1720 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref912[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3168 +: 8] !== face_ref912[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 912"); end end end
    reg [23:0] face_ref913=0;
    always @(posedge clk) if(lane_me_prev) face_ref913 <= {face_ref913[15:0], r_xo[2040 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref913[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1320 +: 8] !== face_ref913[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 913"); end end end
    reg [23:0] face_ref914=0;
    always @(posedge clk) if(lane_me_prev) face_ref914 <= {face_ref914[15:0], r_xo[1784 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref914[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1328 +: 8] !== face_ref914[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 914"); end end end
    reg [95:0] face_ref915=0;
    always @(posedge clk) if(lane_me_prev) face_ref915 <= {face_ref915[87:0], d_e[1536 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref915[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3176 +: 8] !== face_ref915[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 915"); end end end
    reg [47:0] face_ref916=0;
    always @(posedge clk) if(lane_me_prev) face_ref916 <= {face_ref916[39:0], d_e[1544 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref916[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3184 +: 8] !== face_ref916[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 916"); end end end
    reg [95:0] face_ref917=0;
    always @(posedge clk) if(lane_me_prev) face_ref917 <= {face_ref917[87:0], r_xo[3952 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref917[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3192 +: 8] !== face_ref917[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 917"); end end end
    reg [95:0] face_ref918=0;
    always @(posedge clk) if(lane_me_prev) face_ref918 <= {face_ref918[87:0], r_xo[3960 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref918[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3200 +: 8] !== face_ref918[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 918"); end end end
    reg [95:0] face_ref919=0;
    always @(posedge clk) if(lane_me_prev) face_ref919 <= {face_ref919[87:0], r_xo[3968 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref919[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3208 +: 8] !== face_ref919[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 919"); end end end
    reg [95:0] face_ref920=0;
    always @(posedge clk) if(lane_me_prev) face_ref920 <= {face_ref920[87:0], r_xo[1904 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref920[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3216 +: 8] !== face_ref920[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 920"); end end end
    reg [47:0] face_ref921=0;
    always @(posedge clk) if(lane_me_prev) face_ref921 <= {face_ref921[39:0], d_e[1552 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref921[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3224 +: 8] !== face_ref921[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 921"); end end end
    reg [47:0] face_ref922=0;
    always @(posedge clk) if(lane_me_prev) face_ref922 <= {face_ref922[39:0], d_e[1560 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref922[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3232 +: 8] !== face_ref922[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 922"); end end end
    reg [71:0] face_ref923=0;
    always @(posedge clk) if(lane_me_prev) face_ref923 <= {face_ref923[63:0], r_xo[2024 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref923[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1336 +: 8] !== face_ref923[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 923"); end end end
    reg [71:0] face_ref924=0;
    always @(posedge clk) if(lane_me_prev) face_ref924 <= {face_ref924[63:0], r_xo[2016 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref924[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1344 +: 8] !== face_ref924[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 924"); end end end
    reg [79:0] face_ref925=0;
    always @(posedge clk) if(lane_me_prev) face_ref925 <= {face_ref925[71:0], r_xo[2000 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref925[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1352 +: 8] !== face_ref925[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 925"); end end end
    reg [63:0] face_ref926=0;
    always @(posedge clk) if(lane_me_prev) face_ref926 <= {face_ref926[55:0], d_e[1568 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref926[56 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2808 +: 8] !== face_ref926[56 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 926"); end end end
    reg [55:0] face_ref927=0;
    always @(posedge clk) if(lane_me_prev) face_ref927 <= {face_ref927[47:0], d_e[1576 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref927[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2816 +: 8] !== face_ref927[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 927"); end end end
    reg [55:0] face_ref928=0;
    always @(posedge clk) if(lane_me_prev) face_ref928 <= {face_ref928[47:0], d_e[1584 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref928[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2824 +: 8] !== face_ref928[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 928"); end end end
    reg [95:0] face_ref929=0;
    always @(posedge clk) if(lane_me_prev) face_ref929 <= {face_ref929[87:0], r_xo[3752 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref929[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3240 +: 8] !== face_ref929[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 929"); end end end
    reg [15:0] face_ref930=0;
    always @(posedge clk) if(lane_me_prev) face_ref930 <= {face_ref930[7:0], r_xo[2760 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref930[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3248 +: 8] !== face_ref930[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 930"); end end end
    reg [15:0] face_ref931=0;
    always @(posedge clk) if(lane_me_prev) face_ref931 <= {face_ref931[7:0], r_xo[2504 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref931[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3256 +: 8] !== face_ref931[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 931"); end end end
    reg [79:0] face_ref932=0;
    always @(posedge clk) if(lane_me_prev) face_ref932 <= {face_ref932[71:0], r_xo[2752 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref932[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3264 +: 8] !== face_ref932[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 932"); end end end
    reg [15:0] face_ref933=0;
    always @(posedge clk) if(lane_me_prev) face_ref933 <= {face_ref933[7:0], r_xo[2248 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref933[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3272 +: 8] !== face_ref933[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 933"); end end end
    reg [95:0] face_ref934=0;
    always @(posedge clk) if(lane_me_prev) face_ref934 <= {face_ref934[87:0], r_xo[2496 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref934[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3280 +: 8] !== face_ref934[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 934"); end end end
    reg [95:0] face_ref935=0;
    always @(posedge clk) if(lane_me_prev) face_ref935 <= {face_ref935[87:0], r_xo[2744 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref935[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3288 +: 8] !== face_ref935[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 935"); end end end
    reg [95:0] face_ref936=0;
    always @(posedge clk) if(lane_me_prev) face_ref936 <= {face_ref936[87:0], r_xo[2240 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref936[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3296 +: 8] !== face_ref936[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 936"); end end end
    reg [95:0] face_ref937=0;
    always @(posedge clk) if(lane_me_prev) face_ref937 <= {face_ref937[87:0], r_xo[2488 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref937[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3304 +: 8] !== face_ref937[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 937"); end end end
    reg [95:0] face_ref938=0;
    always @(posedge clk) if(lane_me_prev) face_ref938 <= {face_ref938[87:0], r_xo[2736 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref938[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3312 +: 8] !== face_ref938[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 938"); end end end
    reg [95:0] face_ref939=0;
    always @(posedge clk) if(lane_me_prev) face_ref939 <= {face_ref939[87:0], r_xo[2232 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref939[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3320 +: 8] !== face_ref939[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 939"); end end end
    reg [95:0] face_ref940=0;
    always @(posedge clk) if(lane_me_prev) face_ref940 <= {face_ref940[87:0], r_xo[2480 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref940[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3328 +: 8] !== face_ref940[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 940"); end end end
    reg [95:0] face_ref941=0;
    always @(posedge clk) if(lane_me_prev) face_ref941 <= {face_ref941[87:0], r_xo[2728 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref941[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3336 +: 8] !== face_ref941[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 941"); end end end
    reg [95:0] face_ref942=0;
    always @(posedge clk) if(lane_me_prev) face_ref942 <= {face_ref942[87:0], r_xo[2224 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref942[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3344 +: 8] !== face_ref942[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 942"); end end end
    reg [95:0] face_ref943=0;
    always @(posedge clk) if(lane_me_prev) face_ref943 <= {face_ref943[87:0], r_xo[2472 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref943[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3352 +: 8] !== face_ref943[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 943"); end end end
    reg [95:0] face_ref944=0;
    always @(posedge clk) if(lane_me_prev) face_ref944 <= {face_ref944[87:0], r_xo[2216 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref944[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3360 +: 8] !== face_ref944[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 944"); end end end
    reg [15:0] face_ref945=0;
    always @(posedge clk) if(lane_me_prev) face_ref945 <= {face_ref945[7:0], r_xo[2808 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref945[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1360 +: 8] !== face_ref945[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 945"); end end end
    reg [15:0] face_ref946=0;
    always @(posedge clk) if(lane_me_prev) face_ref946 <= {face_ref946[7:0], r_xo[2552 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref946[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1368 +: 8] !== face_ref946[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 946"); end end end
    reg [15:0] face_ref947=0;
    always @(posedge clk) if(lane_me_prev) face_ref947 <= {face_ref947[7:0], r_xo[2296 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref947[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1376 +: 8] !== face_ref947[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 947"); end end end
    reg [79:0] face_ref948=0;
    always @(posedge clk) if(lane_me_prev) face_ref948 <= {face_ref948[71:0], r_xo[2544 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref948[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1384 +: 8] !== face_ref948[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 948"); end end end
    reg [79:0] face_ref949=0;
    always @(posedge clk) if(lane_me_prev) face_ref949 <= {face_ref949[71:0], r_xo[2288 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref949[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1392 +: 8] !== face_ref949[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 949"); end end end
    reg [87:0] face_ref950=0;
    always @(posedge clk) if(lane_me_prev) face_ref950 <= {face_ref950[79:0], r_xo[2792 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref950[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1400 +: 8] !== face_ref950[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 950"); end end end
    reg [23:0] face_ref951=0;
    always @(posedge clk) if(lane_me_prev) face_ref951 <= {face_ref951[15:0], r_xo[2536 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref951[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1408 +: 8] !== face_ref951[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 951"); end end end
    reg [87:0] face_ref952=0;
    always @(posedge clk) if(lane_me_prev) face_ref952 <= {face_ref952[79:0], r_xo[2784 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref952[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3368 +: 8] !== face_ref952[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 952"); end end end
    reg [23:0] face_ref953=0;
    always @(posedge clk) if(lane_me_prev) face_ref953 <= {face_ref953[15:0], r_xo[2280 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref953[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1416 +: 8] !== face_ref953[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 953"); end end end
    reg [23:0] face_ref954=0;
    always @(posedge clk) if(lane_me_prev) face_ref954 <= {face_ref954[15:0], r_xo[2528 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref954[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3376 +: 8] !== face_ref954[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 954"); end end end
    reg [23:0] face_ref955=0;
    always @(posedge clk) if(lane_me_prev) face_ref955 <= {face_ref955[15:0], r_xo[2272 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref955[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3384 +: 8] !== face_ref955[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 955"); end end end
    reg [95:0] face_ref956=0;
    always @(posedge clk) if(lane_me_prev) face_ref956 <= {face_ref956[87:0], r_xo[3736 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref956[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3392 +: 8] !== face_ref956[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 956"); end end end
    reg [15:0] face_ref957=0;
    always @(posedge clk) if(lane_me_prev) face_ref957 <= {face_ref957[7:0], r_xo[2768 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref957[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1424 +: 8] !== face_ref957[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 957"); end end end
    reg [95:0] face_ref958=0;
    always @(posedge clk) if(lane_me_prev) face_ref958 <= {face_ref958[87:0], r_xo[2512 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref958[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1432 +: 8] !== face_ref958[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 958"); end end end
    reg [15:0] face_ref959=0;
    always @(posedge clk) if(lane_me_prev) face_ref959 <= {face_ref959[7:0], r_xo[2256 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref959[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1440 +: 8] !== face_ref959[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 959"); end end end
    reg [95:0] face_ref960=0;
    always @(posedge clk) if(lane_me_prev) face_ref960 <= {face_ref960[87:0], r_xo[2712 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref960[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3400 +: 8] !== face_ref960[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 960"); end end end
    reg [95:0] face_ref961=0;
    always @(posedge clk) if(lane_me_prev) face_ref961 <= {face_ref961[87:0], r_xo[2456 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref961[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3408 +: 8] !== face_ref961[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 961"); end end end
    reg [95:0] face_ref962=0;
    always @(posedge clk) if(lane_me_prev) face_ref962 <= {face_ref962[87:0], r_xo[2720 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref962[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3416 +: 8] !== face_ref962[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 962"); end end end
    reg [95:0] face_ref963=0;
    always @(posedge clk) if(lane_me_prev) face_ref963 <= {face_ref963[87:0], r_xo[2200 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref963[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3424 +: 8] !== face_ref963[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 963"); end end end
    reg [95:0] face_ref964=0;
    always @(posedge clk) if(lane_me_prev) face_ref964 <= {face_ref964[87:0], r_xo[2464 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref964[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3432 +: 8] !== face_ref964[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 964"); end end end
    reg [95:0] face_ref965=0;
    always @(posedge clk) if(lane_me_prev) face_ref965 <= {face_ref965[87:0], r_xo[2208 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref965[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3440 +: 8] !== face_ref965[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 965"); end end end
    reg [47:0] face_ref966=0;
    always @(posedge clk) if(lane_me_prev) face_ref966 <= {face_ref966[39:0], d_e[1592 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref966[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3448 +: 8] !== face_ref966[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 966"); end end end
    reg [47:0] face_ref967=0;
    always @(posedge clk) if(lane_me_prev) face_ref967 <= {face_ref967[39:0], d_e[1600 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref967[40 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3456 +: 8] !== face_ref967[40 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 967"); end end end
    reg [31:0] face_ref968=0;
    always @(posedge clk) if(lane_me_prev) face_ref968 <= {face_ref968[23:0], d_e[1608 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref968[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3464 +: 8] !== face_ref968[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 968"); end end end
    reg [23:0] face_ref969=0;
    always @(posedge clk) if(lane_me_prev) face_ref969 <= {face_ref969[15:0], d_e[1616 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref969[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3472 +: 8] !== face_ref969[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 969"); end end end
    reg [31:0] face_ref970=0;
    always @(posedge clk) if(lane_me_prev) face_ref970 <= {face_ref970[23:0], d_e[1624 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref970[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3480 +: 8] !== face_ref970[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 970"); end end end
    reg [23:0] face_ref971=0;
    always @(posedge clk) if(lane_me_prev) face_ref971 <= {face_ref971[15:0], d_e[1632 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref971[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3488 +: 8] !== face_ref971[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 971"); end end end
    reg [31:0] face_ref972=0;
    always @(posedge clk) if(lane_me_prev) face_ref972 <= {face_ref972[23:0], d_e[1640 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref972[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3496 +: 8] !== face_ref972[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 972"); end end end
    reg [31:0] face_ref973=0;
    always @(posedge clk) if(lane_me_prev) face_ref973 <= {face_ref973[23:0], d_e[1648 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref973[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3504 +: 8] !== face_ref973[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 973"); end end end
    reg [15:0] face_ref974=0;
    always @(posedge clk) if(lane_me_prev) face_ref974 <= {face_ref974[7:0], r_xo[3056 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref974[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1448 +: 8] !== face_ref974[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 974"); end end end
    reg [15:0] face_ref975=0;
    always @(posedge clk) if(lane_me_prev) face_ref975 <= {face_ref975[7:0], r_xo[2800 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref975[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1456 +: 8] !== face_ref975[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 975"); end end end
    reg [15:0] face_ref976=0;
    always @(posedge clk) if(lane_me_prev) face_ref976 <= {face_ref976[7:0], r_xo[3048 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref976[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1464 +: 8] !== face_ref976[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 976"); end end end
    reg [95:0] face_ref977=0;
    always @(posedge clk) if(lane_me_prev) face_ref977 <= {face_ref977[87:0], d_e[1656 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref977[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3512 +: 8] !== face_ref977[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 977"); end end end
    reg [95:0] face_ref978=0;
    always @(posedge clk) if(lane_me_prev) face_ref978 <= {face_ref978[87:0], d_e[1664 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref978[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3520 +: 8] !== face_ref978[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 978"); end end end
    reg [31:0] face_ref979=0;
    always @(posedge clk) if(lane_me_prev) face_ref979 <= {face_ref979[23:0], r_xo[4040 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref979[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3528 +: 8] !== face_ref979[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 979"); end end end
    reg [23:0] face_ref980=0;
    always @(posedge clk) if(lane_me_prev) face_ref980 <= {face_ref980[15:0], r_xo[3032 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref980[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1472 +: 8] !== face_ref980[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 980"); end end end
    reg [31:0] face_ref981=0;
    always @(posedge clk) if(lane_me_prev) face_ref981 <= {face_ref981[23:0], r_xo[3784 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref981[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3536 +: 8] !== face_ref981[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 981"); end end end
    reg [31:0] face_ref982=0;
    always @(posedge clk) if(lane_me_prev) face_ref982 <= {face_ref982[23:0], r_xo[4032 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref982[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3544 +: 8] !== face_ref982[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 982"); end end end
    reg [95:0] face_ref983=0;
    always @(posedge clk) if(lane_me_prev) face_ref983 <= {face_ref983[87:0], r_xo[3528 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref983[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3552 +: 8] !== face_ref983[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 983"); end end end
    reg [95:0] face_ref984=0;
    always @(posedge clk) if(lane_me_prev) face_ref984 <= {face_ref984[87:0], d_e[1672 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref984[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3560 +: 8] !== face_ref984[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 984"); end end end
    reg [55:0] face_ref985=0;
    always @(posedge clk) if(lane_me_prev) face_ref985 <= {face_ref985[47:0], r_xo[2776 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref985[48 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1480 +: 8] !== face_ref985[48 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 985"); end end end
    reg [95:0] face_ref986=0;
    always @(posedge clk) if(lane_me_prev) face_ref986 <= {face_ref986[87:0], r_xo[3776 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref986[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3568 +: 8] !== face_ref986[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 986"); end end end
    reg [95:0] face_ref987=0;
    always @(posedge clk) if(lane_me_prev) face_ref987 <= {face_ref987[87:0], r_xo[4024 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref987[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3576 +: 8] !== face_ref987[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 987"); end end end
    reg [87:0] face_ref988=0;
    always @(posedge clk) if(lane_me_prev) face_ref988 <= {face_ref988[79:0], r_xo[2520 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref988[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1488 +: 8] !== face_ref988[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 988"); end end end
    reg [31:0] face_ref989=0;
    always @(posedge clk) if(lane_me_prev) face_ref989 <= {face_ref989[23:0], r_xo[3768 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref989[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3584 +: 8] !== face_ref989[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 989"); end end end
    reg [87:0] face_ref990=0;
    always @(posedge clk) if(lane_me_prev) face_ref990 <= {face_ref990[79:0], r_xo[2264 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref990[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1496 +: 8] !== face_ref990[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 990"); end end end
    reg [95:0] face_ref991=0;
    always @(posedge clk) if(lane_me_prev) face_ref991 <= {face_ref991[87:0], r_xo[4016 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref991[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3592 +: 8] !== face_ref991[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 991"); end end end
    reg [95:0] face_ref992=0;
    always @(posedge clk) if(lane_me_prev) face_ref992 <= {face_ref992[87:0], r_xo[3760 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref992[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3600 +: 8] !== face_ref992[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 992"); end end end
    reg [95:0] face_ref993=0;
    always @(posedge clk) if(lane_me_prev) face_ref993 <= {face_ref993[87:0], r_xo[4008 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref993[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3608 +: 8] !== face_ref993[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 993"); end end end
    reg [15:0] face_ref994=0;
    always @(posedge clk) if(lane_me_prev) face_ref994 <= {face_ref994[7:0], r_xo[3016 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref994[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3616 +: 8] !== face_ref994[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 994"); end end end
    reg [95:0] face_ref995=0;
    always @(posedge clk) if(lane_me_prev) face_ref995 <= {face_ref995[87:0], r_xo[3008 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref995[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3624 +: 8] !== face_ref995[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 995"); end end end
    reg [95:0] face_ref996=0;
    always @(posedge clk) if(lane_me_prev) face_ref996 <= {face_ref996[87:0], r_xo[3000 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref996[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3632 +: 8] !== face_ref996[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 996"); end end end
    reg [95:0] face_ref997=0;
    always @(posedge clk) if(lane_me_prev) face_ref997 <= {face_ref997[87:0], r_xo[2992 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref997[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3640 +: 8] !== face_ref997[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 997"); end end end
    reg [95:0] face_ref998=0;
    always @(posedge clk) if(lane_me_prev) face_ref998 <= {face_ref998[87:0], r_xo[2984 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref998[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3648 +: 8] !== face_ref998[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 998"); end end end
    reg [31:0] face_ref999=0;
    always @(posedge clk) if(lane_me_prev) face_ref999 <= {face_ref999[23:0], d_e[1680 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref999[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3656 +: 8] !== face_ref999[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 999"); end end end
    reg [15:0] face_ref1000=0;
    always @(posedge clk) if(lane_me_prev) face_ref1000 <= {face_ref1000[7:0], r_xo[3064 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1000[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3664 +: 8] !== face_ref1000[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1000"); end end end
    reg [95:0] face_ref1001=0;
    always @(posedge clk) if(lane_me_prev) face_ref1001 <= {face_ref1001[87:0], d_e[1688 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1001[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3672 +: 8] !== face_ref1001[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1001"); end end end
    reg [79:0] face_ref1002=0;
    always @(posedge clk) if(lane_me_prev) face_ref1002 <= {face_ref1002[71:0], r_xo[3040 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1002[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3680 +: 8] !== face_ref1002[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1002"); end end end
    reg [23:0] face_ref1003=0;
    always @(posedge clk) if(lane_me_prev) face_ref1003 <= {face_ref1003[15:0], d_e[1696 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1003[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3688 +: 8] !== face_ref1003[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1003"); end end end
    reg [95:0] face_ref1004=0;
    always @(posedge clk) if(lane_me_prev) face_ref1004 <= {face_ref1004[87:0], r_xo[3992 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1004[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3696 +: 8] !== face_ref1004[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1004"); end end end
    reg [95:0] face_ref1005=0;
    always @(posedge clk) if(lane_me_prev) face_ref1005 <= {face_ref1005[87:0], r_xo[4000 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1005[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3704 +: 8] !== face_ref1005[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1005"); end end end
    reg [95:0] face_ref1006=0;
    always @(posedge clk) if(lane_me_prev) face_ref1006 <= {face_ref1006[87:0], r_xo[3744 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1006[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3712 +: 8] !== face_ref1006[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1006"); end end end
    reg [95:0] face_ref1007=0;
    always @(posedge clk) if(lane_me_prev) face_ref1007 <= {face_ref1007[87:0], r_xo[2968 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1007[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3720 +: 8] !== face_ref1007[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1007"); end end end
    reg [95:0] face_ref1008=0;
    always @(posedge clk) if(lane_me_prev) face_ref1008 <= {face_ref1008[87:0], r_xo[2976 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1008[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3728 +: 8] !== face_ref1008[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1008"); end end end
    reg [23:0] face_ref1009=0;
    always @(posedge clk) if(lane_me_prev) face_ref1009 <= {face_ref1009[15:0], d_e[1704 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1009[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3736 +: 8] !== face_ref1009[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1009"); end end end
    reg [23:0] face_ref1010=0;
    always @(posedge clk) if(lane_me_prev) face_ref1010 <= {face_ref1010[15:0], d_e[1712 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1010[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3744 +: 8] !== face_ref1010[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1010"); end end end
    reg [23:0] face_ref1011=0;
    always @(posedge clk) if(lane_me_prev) face_ref1011 <= {face_ref1011[15:0], d_e[1720 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1011[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3752 +: 8] !== face_ref1011[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1011"); end end end
    reg [31:0] face_ref1012=0;
    always @(posedge clk) if(lane_me_prev) face_ref1012 <= {face_ref1012[23:0], d_e[1728 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1012[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3760 +: 8] !== face_ref1012[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1012"); end end end
    reg [31:0] face_ref1013=0;
    always @(posedge clk) if(lane_me_prev) face_ref1013 <= {face_ref1013[23:0], d_e[1736 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1013[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3768 +: 8] !== face_ref1013[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1013"); end end end
    reg [31:0] face_ref1014=0;
    always @(posedge clk) if(lane_me_prev) face_ref1014 <= {face_ref1014[23:0], d_e[1744 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1014[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3776 +: 8] !== face_ref1014[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1014"); end end end
    reg [87:0] face_ref1015=0;
    always @(posedge clk) if(lane_me_prev) face_ref1015 <= {face_ref1015[79:0], d_e[1752 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1015[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3784 +: 8] !== face_ref1015[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1015"); end end end
    reg [95:0] face_ref1016=0;
    always @(posedge clk) if(lane_me_prev) face_ref1016 <= {face_ref1016[87:0], d_e[1760 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1016[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3792 +: 8] !== face_ref1016[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1016"); end end end
    reg [31:0] face_ref1017=0;
    always @(posedge clk) if(lane_me_prev) face_ref1017 <= {face_ref1017[23:0], d_e[1768 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1017[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3800 +: 8] !== face_ref1017[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1017"); end end end
    reg [87:0] face_ref1018=0;
    always @(posedge clk) if(lane_me_prev) face_ref1018 <= {face_ref1018[79:0], d_e[1776 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1018[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3808 +: 8] !== face_ref1018[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1018"); end end end
    reg [87:0] face_ref1019=0;
    always @(posedge clk) if(lane_me_prev) face_ref1019 <= {face_ref1019[79:0], d_e[1784 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1019[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3816 +: 8] !== face_ref1019[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1019"); end end end
    reg [87:0] face_ref1020=0;
    always @(posedge clk) if(lane_me_prev) face_ref1020 <= {face_ref1020[79:0], d_e[1792 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1020[80 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3824 +: 8] !== face_ref1020[80 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1020"); end end end
    reg [95:0] face_ref1021=0;
    always @(posedge clk) if(lane_me_prev) face_ref1021 <= {face_ref1021[87:0], r_xo[3984 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1021[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3832 +: 8] !== face_ref1021[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1021"); end end end
    reg [15:0] face_ref1022=0;
    always @(posedge clk) if(lane_me_prev) face_ref1022 <= {face_ref1022[7:0], r_xo[3312 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1022[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1504 +: 8] !== face_ref1022[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1022"); end end end
    reg [23:0] face_ref1023=0;
    always @(posedge clk) if(lane_me_prev) face_ref1023 <= {face_ref1023[15:0], r_xo[3288 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1023[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1512 +: 8] !== face_ref1023[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1023"); end end end
    reg [23:0] face_ref1024=0;
    always @(posedge clk) if(lane_me_prev) face_ref1024 <= {face_ref1024[15:0], d_e[1800 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1024[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3840 +: 8] !== face_ref1024[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1024"); end end end
    reg [15:0] face_ref1025=0;
    always @(posedge clk) if(lane_me_prev) face_ref1025 <= {face_ref1025[7:0], r_xo[3280 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1025[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1520 +: 8] !== face_ref1025[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1025"); end end end
    reg [15:0] face_ref1026=0;
    always @(posedge clk) if(lane_me_prev) face_ref1026 <= {face_ref1026[7:0], r_xo[3272 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1026[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3848 +: 8] !== face_ref1026[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1026"); end end end
    reg [15:0] face_ref1027=0;
    always @(posedge clk) if(lane_me_prev) face_ref1027 <= {face_ref1027[7:0], r_xo[3264 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1027[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3856 +: 8] !== face_ref1027[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1027"); end end end
    reg [15:0] face_ref1028=0;
    always @(posedge clk) if(lane_me_prev) face_ref1028 <= {face_ref1028[7:0], r_xo[3256 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1028[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3864 +: 8] !== face_ref1028[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1028"); end end end
    reg [15:0] face_ref1029=0;
    always @(posedge clk) if(lane_me_prev) face_ref1029 <= {face_ref1029[7:0], r_xo[3248 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1029[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3872 +: 8] !== face_ref1029[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1029"); end end end
    reg [15:0] face_ref1030=0;
    always @(posedge clk) if(lane_me_prev) face_ref1030 <= {face_ref1030[7:0], r_xo[3240 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1030[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3880 +: 8] !== face_ref1030[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1030"); end end end
    reg [39:0] face_ref1031=0;
    always @(posedge clk) if(lane_me_prev) face_ref1031 <= {face_ref1031[31:0], d_e[1808 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1031[32 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3888 +: 8] !== face_ref1031[32 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1031"); end end end
    reg [15:0] face_ref1032=0;
    always @(posedge clk) if(lane_me_prev) face_ref1032 <= {face_ref1032[7:0], r_xo[3320 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1032[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3896 +: 8] !== face_ref1032[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1032"); end end end
    reg [23:0] face_ref1033=0;
    always @(posedge clk) if(lane_me_prev) face_ref1033 <= {face_ref1033[15:0], r_xo[3296 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1033[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3904 +: 8] !== face_ref1033[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1033"); end end end
    reg [15:0] face_ref1034=0;
    always @(posedge clk) if(lane_me_prev) face_ref1034 <= {face_ref1034[7:0], r_xo[3224 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1034[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3912 +: 8] !== face_ref1034[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1034"); end end end
    reg [15:0] face_ref1035=0;
    always @(posedge clk) if(lane_me_prev) face_ref1035 <= {face_ref1035[7:0], r_xo[3568 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1035[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1528 +: 8] !== face_ref1035[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1035"); end end end
    reg [15:0] face_ref1036=0;
    always @(posedge clk) if(lane_me_prev) face_ref1036 <= {face_ref1036[7:0], r_xo[3544 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1036[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1536 +: 8] !== face_ref1036[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1036"); end end end
    reg [23:0] face_ref1037=0;
    always @(posedge clk) if(lane_me_prev) face_ref1037 <= {face_ref1037[15:0], d_e[1816 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1037[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3920 +: 8] !== face_ref1037[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1037"); end end end
    reg [15:0] face_ref1038=0;
    always @(posedge clk) if(lane_me_prev) face_ref1038 <= {face_ref1038[7:0], r_xo[3520 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1038[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3928 +: 8] !== face_ref1038[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1038"); end end end
    reg [15:0] face_ref1039=0;
    always @(posedge clk) if(lane_me_prev) face_ref1039 <= {face_ref1039[7:0], r_xo[3512 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1039[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3936 +: 8] !== face_ref1039[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1039"); end end end
    reg [15:0] face_ref1040=0;
    always @(posedge clk) if(lane_me_prev) face_ref1040 <= {face_ref1040[7:0], r_xo[3504 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1040[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3944 +: 8] !== face_ref1040[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1040"); end end end
    reg [15:0] face_ref1041=0;
    always @(posedge clk) if(lane_me_prev) face_ref1041 <= {face_ref1041[7:0], r_xo[3496 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1041[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3952 +: 8] !== face_ref1041[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1041"); end end end
    reg [15:0] face_ref1042=0;
    always @(posedge clk) if(lane_me_prev) face_ref1042 <= {face_ref1042[7:0], r_xo[3024 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1042[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1544 +: 8] !== face_ref1042[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1042"); end end end
    reg [15:0] face_ref1043=0;
    always @(posedge clk) if(lane_me_prev) face_ref1043 <= {face_ref1043[7:0], r_xo[3488 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1043[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3960 +: 8] !== face_ref1043[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1043"); end end end
    reg [15:0] face_ref1044=0;
    always @(posedge clk) if(lane_me_prev) face_ref1044 <= {face_ref1044[7:0], r_xo[3232 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1044[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3968 +: 8] !== face_ref1044[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1044"); end end end
    reg [15:0] face_ref1045=0;
    always @(posedge clk) if(lane_me_prev) face_ref1045 <= {face_ref1045[7:0], r_xo[3816 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1045[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1552 +: 8] !== face_ref1045[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1045"); end end end
    reg [15:0] face_ref1046=0;
    always @(posedge clk) if(lane_me_prev) face_ref1046 <= {face_ref1046[7:0], r_xo[3560 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1046[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1560 +: 8] !== face_ref1046[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1046"); end end end
    reg [15:0] face_ref1047=0;
    always @(posedge clk) if(lane_me_prev) face_ref1047 <= {face_ref1047[7:0], r_xo[3304 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1047[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1568 +: 8] !== face_ref1047[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1047"); end end end
    reg [23:0] face_ref1048=0;
    always @(posedge clk) if(lane_me_prev) face_ref1048 <= {face_ref1048[15:0], r_xo[3792 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1048[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1576 +: 8] !== face_ref1048[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1048"); end end end
    reg [23:0] face_ref1049=0;
    always @(posedge clk) if(lane_me_prev) face_ref1049 <= {face_ref1049[15:0], r_xo[3536 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1049[16 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1584 +: 8] !== face_ref1049[16 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1049"); end end end
    reg [15:0] face_ref1050=0;
    always @(posedge clk) if(lane_me_prev) face_ref1050 <= {face_ref1050[7:0], r_xo[4088 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1050[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1592 +: 8] !== face_ref1050[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1050"); end end end
    reg [15:0] face_ref1051=0;
    always @(posedge clk) if(lane_me_prev) face_ref1051 <= {face_ref1051[7:0], r_xo[3832 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1051[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1600 +: 8] !== face_ref1051[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1051"); end end end
    reg [15:0] face_ref1052=0;
    always @(posedge clk) if(lane_me_prev) face_ref1052 <= {face_ref1052[7:0], r_xo[3576 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1052[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1608 +: 8] !== face_ref1052[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1052"); end end end
    reg [15:0] face_ref1053=0;
    always @(posedge clk) if(lane_me_prev) face_ref1053 <= {face_ref1053[7:0], r_xo[4064 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1053[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1616 +: 8] !== face_ref1053[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1053"); end end end
    reg [15:0] face_ref1054=0;
    always @(posedge clk) if(lane_me_prev) face_ref1054 <= {face_ref1054[7:0], r_xo[3808 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1054[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1624 +: 8] !== face_ref1054[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1054"); end end end
    reg [15:0] face_ref1055=0;
    always @(posedge clk) if(lane_me_prev) face_ref1055 <= {face_ref1055[7:0], r_xo[3552 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1055[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1632 +: 8] !== face_ref1055[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1055"); end end end
    reg [71:0] face_ref1056=0;
    always @(posedge clk) if(lane_me_prev) face_ref1056 <= {face_ref1056[63:0], r_xo[4080 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1056[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1640 +: 8] !== face_ref1056[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1056"); end end end
    reg [71:0] face_ref1057=0;
    always @(posedge clk) if(lane_me_prev) face_ref1057 <= {face_ref1057[63:0], r_xo[3824 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1057[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1648 +: 8] !== face_ref1057[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1057"); end end end
    reg [79:0] face_ref1058=0;
    always @(posedge clk) if(lane_me_prev) face_ref1058 <= {face_ref1058[71:0], r_xo[4056 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1058[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1656 +: 8] !== face_ref1058[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1058"); end end end
    reg [79:0] face_ref1059=0;
    always @(posedge clk) if(lane_me_prev) face_ref1059 <= {face_ref1059[71:0], r_xo[3800 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1059[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1664 +: 8] !== face_ref1059[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1059"); end end end
    reg [79:0] face_ref1060=0;
    always @(posedge clk) if(lane_me_prev) face_ref1060 <= {face_ref1060[71:0], r_xo[4048 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1060[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1672 +: 8] !== face_ref1060[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1060"); end end end
    reg [71:0] face_ref1061=0;
    always @(posedge clk) if(lane_me_prev) face_ref1061 <= {face_ref1061[63:0], r_xo[4072 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1061[64 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_e[1680 +: 8] !== face_ref1061[64 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1061"); end end end
    reg [95:0] face_ref1062=0;
    always @(posedge clk) if(lane_me_prev) face_ref1062 <= {face_ref1062[87:0], r_xo[1144 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1062[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3976 +: 8] !== face_ref1062[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1062"); end end end
    reg [95:0] face_ref1063=0;
    always @(posedge clk) if(lane_me_prev) face_ref1063 <= {face_ref1063[87:0], r_xo[104 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1063[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2832 +: 8] !== face_ref1063[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1063"); end end end
    reg [95:0] face_ref1064=0;
    always @(posedge clk) if(lane_me_prev) face_ref1064 <= {face_ref1064[87:0], r_xo[112 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1064[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2840 +: 8] !== face_ref1064[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1064"); end end end
    reg [95:0] face_ref1065=0;
    always @(posedge clk) if(lane_me_prev) face_ref1065 <= {face_ref1065[87:0], r_xo[120 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1065[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3984 +: 8] !== face_ref1065[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1065"); end end end
    reg [95:0] face_ref1066=0;
    always @(posedge clk) if(lane_me_prev) face_ref1066 <= {face_ref1066[87:0], r_xo[128 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1066[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[3992 +: 8] !== face_ref1066[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1066"); end end end
    reg [95:0] face_ref1067=0;
    always @(posedge clk) if(lane_me_prev) face_ref1067 <= {face_ref1067[87:0], r_xo[1120 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1067[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2848 +: 8] !== face_ref1067[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1067"); end end end
    reg [95:0] face_ref1068=0;
    always @(posedge clk) if(lane_me_prev) face_ref1068 <= {face_ref1068[87:0], r_xo[608 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1068[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2856 +: 8] !== face_ref1068[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1068"); end end end
    reg [95:0] face_ref1069=0;
    always @(posedge clk) if(lane_me_prev) face_ref1069 <= {face_ref1069[87:0], r_xo[96 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1069[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2864 +: 8] !== face_ref1069[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1069"); end end end
    reg [95:0] face_ref1070=0;
    always @(posedge clk) if(lane_me_prev) face_ref1070 <= {face_ref1070[87:0], r_xo[360 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1070[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2872 +: 8] !== face_ref1070[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1070"); end end end
    reg [95:0] face_ref1071=0;
    always @(posedge clk) if(lane_me_prev) face_ref1071 <= {face_ref1071[87:0], r_xo[368 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1071[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2880 +: 8] !== face_ref1071[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1071"); end end end
    reg [95:0] face_ref1072=0;
    always @(posedge clk) if(lane_me_prev) face_ref1072 <= {face_ref1072[87:0], r_xo[376 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1072[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[4000 +: 8] !== face_ref1072[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1072"); end end end
    reg [95:0] face_ref1073=0;
    always @(posedge clk) if(lane_me_prev) face_ref1073 <= {face_ref1073[87:0], r_xo[384 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1073[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[4008 +: 8] !== face_ref1073[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1073"); end end end
    reg [95:0] face_ref1074=0;
    always @(posedge clk) if(lane_me_prev) face_ref1074 <= {face_ref1074[87:0], r_xo[1632 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1074[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2888 +: 8] !== face_ref1074[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1074"); end end end
    reg [95:0] face_ref1075=0;
    always @(posedge clk) if(lane_me_prev) face_ref1075 <= {face_ref1075[87:0], r_xo[352 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1075[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2896 +: 8] !== face_ref1075[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1075"); end end end
    reg [31:0] face_ref1076=0;
    always @(posedge clk) if(lane_me_prev) face_ref1076 <= {face_ref1076[23:0], r_xo[1128 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1076[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2904 +: 8] !== face_ref1076[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1076"); end end end
    reg [95:0] face_ref1077=0;
    always @(posedge clk) if(lane_me_prev) face_ref1077 <= {face_ref1077[87:0], r_xo[1656 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1077[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2912 +: 8] !== face_ref1077[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1077"); end end end
    reg [95:0] face_ref1078=0;
    always @(posedge clk) if(lane_me_prev) face_ref1078 <= {face_ref1078[87:0], r_xo[624 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1078[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[4016 +: 8] !== face_ref1078[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1078"); end end end
    reg [15:0] face_ref1079=0;
    always @(posedge clk) if(lane_me_prev) face_ref1079 <= {face_ref1079[7:0], r_xo[632 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1079[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2920 +: 8] !== face_ref1079[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1079"); end end end
    reg [95:0] face_ref1080=0;
    always @(posedge clk) if(lane_me_prev) face_ref1080 <= {face_ref1080[87:0], r_xo[640 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1080[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[4024 +: 8] !== face_ref1080[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1080"); end end end
    reg [95:0] face_ref1081=0;
    always @(posedge clk) if(lane_me_prev) face_ref1081 <= {face_ref1081[87:0], r_xo[1640 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1081[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2928 +: 8] !== face_ref1081[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1081"); end end end
    reg [95:0] face_ref1082=0;
    always @(posedge clk) if(lane_me_prev) face_ref1082 <= {face_ref1082[87:0], r_xo[616 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1082[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2936 +: 8] !== face_ref1082[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1082"); end end end
    reg [15:0] face_ref1083=0;
    always @(posedge clk) if(lane_me_prev) face_ref1083 <= {face_ref1083[7:0], r_xo[544 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1083[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2944 +: 8] !== face_ref1083[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1083"); end end end
    reg [79:0] face_ref1084=0;
    always @(posedge clk) if(lane_me_prev) face_ref1084 <= {face_ref1084[71:0], r_xo[568 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1084[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2952 +: 8] !== face_ref1084[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1084"); end end end
    reg [79:0] face_ref1085=0;
    always @(posedge clk) if(lane_me_prev) face_ref1085 <= {face_ref1085[71:0], r_xo[584 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1085[72 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2960 +: 8] !== face_ref1085[72 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1085"); end end end
    reg [15:0] face_ref1086=0;
    always @(posedge clk) if(lane_me_prev) face_ref1086 <= {face_ref1086[7:0], r_xo[592 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1086[8 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_w[2968 +: 8] !== face_ref1086[8 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1086"); end end end
    reg [95:0] face_ref1087=0;
    always @(posedge clk) if(lane_me_prev) face_ref1087 <= {face_ref1087[87:0], r_xo[1648 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1087[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[4032 +: 8] !== face_ref1087[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1087"); end end end
    reg [95:0] face_ref1088=0;
    always @(posedge clk) if(lane_me_prev) face_ref1088 <= {face_ref1088[87:0], r_xo[1664 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1088[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[4040 +: 8] !== face_ref1088[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1088"); end end end
    reg [31:0] face_ref1089=0;
    always @(posedge clk) if(lane_me_prev) face_ref1089 <= {face_ref1089[23:0], r_xo[1672 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1089[24 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[4048 +: 8] !== face_ref1089[24 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1089"); end end end
    reg [95:0] face_ref1090=0;
    always @(posedge clk) if(lane_me_prev) face_ref1090 <= {face_ref1090[87:0], r_xo[1152 +: 8]};
    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref1090[88 +: 8] != 0) lane_nonzero=lane_nonzero+1; if(q_s[4056 +: 8] !== face_ref1090[88 +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment 1090"); end end end
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
        if (sched_err != 0) begin $display("FAIL qfd_vm_rg6_face_model BENCH schedule raised ovf in the main run (%0d)", sched_err); $fatal(1, "FAIL"); end
        if (pushes < CYCLES / 16 || pops < CYCLES / 16 || rowreads < CYCLES / 8 || suans < CYCLES / 8 || stalls < CYCLES / 8
            || moves < CYCLES / 2 || garbage < CYCLES / 32 || deep < CYCLES / 64 || xo_chg < pops / 2 || ro_chg < rowreads / 2
            || so_chg < suans / 2 || nonzero < 64 * CYCLES || ovf_cmp < 8 || ovf_cmp > 158) begin
            $display("FAIL qfd_vm_rg6_face_model VACUOUS pushes=%0d pops=%0d row_reads=%0d su_answers=%0d stalls=%0d moves=%0d pop_garbage=%0d deep=%0d xo_chg=%0d ro_chg=%0d so_chg=%0d nonzero_words=%0d ovf_cycles=%0d",
                pushes, pops, rowreads, suans, stalls, moves, garbage, deep, xo_chg, ro_chg, so_chg, nonzero, ovf_cmp);
            $fatal(1, "FAIL");
        end
        if (errors != 0) begin
            $display("FAIL qfd_vm_rg6_face_model LEAF_MUT=%0d ROW_MUT=%0d SU_MUT=%0d errors=%0d of %0d (xo %0d ro %0d so %0d ovf %0d)", LEAF_MUT, ROW_MUT, SU_MUT, errors, checks, e_xo, e_ro, e_so, e_ovf);
            $fatal(1, "FAIL");
        end
        $display("PASS qfd_vm_rg6_face_model DEPTH=%0d LAW=%0d DEPTHS=%0d LAWS=%0d SEED=%0d OVFMODE=%0d exact %0d checks: pushes=%0d pops=%0d row_reads=%0d su_answers=%0d stalls=%0d pop_garbage=%0d deep=%0d xo_chg=%0d ro_chg=%0d so_chg=%0d nonzero_words=%0d ovf_cycles=%0d",
            DEPTH, LAW, DEPTHS, LAWS, SEED, OVFMODE, checks, pushes, pops, rowreads, suans, stalls, garbage, deep, xo_chg, ro_chg, so_chg, nonzero, ovf_cmp);
            $display("region lanes segments=1091 stage_bits=42024 checks=%0d nonzero=%0d",lane_checks,lane_nonzero);
            if (lane_checks < 1000 || lane_nonzero < 100) $fatal(1,"lane coverage vacuous");
            $finish;
    end
endmodule
