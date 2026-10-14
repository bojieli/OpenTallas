// Behavioral staging candidate ONLY: every real rg6 core/lane child remains in u_base.
// CLOCK input/output stages and ENGINE lane stages are distinct. Async resets remain direct.
module ot_qfd_vm_rg6_face_model #(parameter integer MUT=0) (
    input wire face_clk,
    input wire ck_c0,
    input wire ck_c1,
    input wire ck_c2,
    input wire ck_c3,
    input wire ck_c4,
    input wire ck_c5,
    input wire ck_c6,
    input wire ck_c7,
    input wire ck_c8,
    input wire ck_c9,
    input wire ck_c10,
    input wire ck_c11,
    input wire ck_c12,
    input wire ck_c13,
    input wire ck_c14,
    input wire ck_c15,
    input wire ck_c16,
    input wire ck_c17,
    input wire ck_c18,
    input wire ck_c19,
    input wire ck_c20,
    input wire ck_c21,
    input wire ck_c22,
    input wire ck_c23,
    input wire ck_c24,
    input wire ck_c25,
    input wire ck_c26,
    input wire ck_c27,
    input wire ck_c28,
    input wire ck_c29,
    input wire ck_c30,
    input wire ck_c31,
    input wire ck_c32,
    input wire ck_c33,
    input wire ck_c34,
    input wire ck_c35,
    input wire ck_c36,
    input wire ck_c37,
    input wire ck_c38,
    input wire ck_c39,
    input wire ck_c40,
    input wire ck_c41,
    input wire ck_c42,
    input wire ck_c43,
    input wire ck_c44,
    input wire ck_c45,
    input wire ck_c46,
    input wire ck_c47,
    input wire ck_c48,
    input wire ck_c49,
    input wire ck_c50,
    input wire ck_c51,
    input wire ck_c52,
    input wire ck_c53,
    input wire ck_c54,
    input wire ck_c55,
    input wire ck_c56,
    input wire ck_c57,
    input wire ck_c58,
    input wire ck_c59,
    input wire ck_c60,
    input wire ck_c61,
    input wire ck_c62,
    input wire ck_c63,
    input wire ck_c64,
    input wire ck_c65,
    input wire ck_c66,
    input wire ck_c67,
    input wire ck_c68,
    input wire ck_c69,
    input wire ck_c70,
    input wire ck_c71,
    input wire ck_t0,
    input wire ck_t1,
    input wire ck_t2,
    input wire ck_t3,
    input wire ck_t4,
    input wire ck_t5,
    input wire ck_t6,
    input wire ck_t7,
    input wire ck_t8,
    input wire ck_t9,
    input wire ck_t10,
    input wire ck_t11,
    input wire ck_t12,
    input wire ck_t13,
    input wire ck_t14,
    input wire ck_t15,
    input wire ck_t16,
    input wire ck_t17,
    input wire ck_t18,
    input wire ck_t19,
    input wire ck_t20,
    input wire ck_t21,
    input wire ck_t22,
    input wire ck_t23,
    input wire ck_t24,
    input wire ck_t25,
    input wire ck_t26,
    input wire ck_t27,
    input wire ck_t28,
    input wire ck_t29,
    input wire ck_t30,
    input wire ck_t31,
    input wire ck_t32,
    input wire ck_t33,
    input wire ck_t34,
    input wire ck_t35,
    input wire ck_t36,
    input wire ck_t37,
    input wire ck_t38,
    input wire ck_t39,
    input wire ck_t40,
    input wire ck_t41,
    input wire ck_t42,
    input wire ck_t43,
    input wire ck_t44,
    input wire ck_t45,
    input wire ck_t46,
    input wire ck_t47,
    input wire ck_t48,
    input wire ck_t49,
    input wire ck_t50,
    input wire ck_t51,
    input wire ck_t52,
    input wire ck_t53,
    input wire ck_t54,
    input wire ck_t55,
    input wire ck_t56,
    input wire ck_t57,
    input wire ck_t58,
    input wire ck_t59,
    input wire ck_t60,
    input wire ck_t61,
    input wire ck_t62,
    input wire ck_t63,
    input wire ck_t64,
    input wire ck_t65,
    input wire ck_t66,
    input wire ck_t67,
    input wire ck_t68,
    input wire ck_t69,
    input wire ck_t70,
    input wire ck_t71,
    input wire ck_t72,
    input wire ck_t73,
    input wire ck_t74,
    input wire ck_t75,
    input wire ck_t76,
    input wire re_b0,
    input wire re_b1,
    input wire re_b2,
    input wire re_b3,
    input wire re_b4,
    input wire re_b5,
    input wire re_b6,
    input wire re_b7,
    input wire [7:0] ra_b0,
    input wire [7:0] ra_b1,
    input wire [7:0] ra_b2,
    input wire [7:0] ra_b3,
    input wire [7:0] ra_b4,
    input wire [7:0] ra_b5,
    input wire [7:0] ra_b6,
    input wire [7:0] ra_b7,
    input wire we_b0,
    input wire we_b1,
    input wire we_b2,
    input wire we_b3,
    input wire we_b4,
    input wire we_b5,
    input wire we_b6,
    input wire we_b7,
    input wire [7:0] wl_b0,
    input wire [7:0] wl_b1,
    input wire [7:0] wl_b2,
    input wire [7:0] wl_b3,
    input wire [7:0] wl_b4,
    input wire [7:0] wl_b5,
    input wire [7:0] wl_b6,
    input wire [7:0] wl_b7,
    input wire [15:0] wm_b0,
    input wire [15:0] wm_b1,
    input wire [15:0] wm_b2,
    input wire [15:0] wm_b3,
    input wire [15:0] wm_b4,
    input wire [15:0] wm_b5,
    input wire [15:0] wm_b6,
    input wire [15:0] wm_b7,
    input wire [511:0] wd_b0,
    input wire [511:0] wd_b1,
    input wire [511:0] wd_b2,
    input wire [511:0] wd_b3,
    input wire [511:0] wd_b4,
    input wire [511:0] wd_b5,
    input wire [511:0] wd_b6,
    input wire [511:0] wd_b7,
    input wire sre_s0,
    input wire sre_s1,
    input wire sre_s2,
    input wire sre_s3,
    input wire sre_s4,
    input wire sre_s5,
    input wire [9:0] sra_s0,
    input wire [9:0] sra_s1,
    input wire [9:0] sra_s2,
    input wire [9:0] sra_s3,
    input wire [9:0] sra_s4,
    input wire [9:0] sra_s5,
    input wire rst_b0,
    input wire rst_b1,
    input wire rst_b2,
    input wire rst_b3,
    input wire rst_b4,
    input wire rst_b5,
    input wire rst_b6,
    input wire rst_b7,
    input wire rst_s0,
    input wire rst_s1,
    input wire rst_s2,
    input wire rst_s3,
    input wire rst_s4,
    input wire rst_s5,
    input wire rst_r0,
    input wire rst_r1,
    input wire rst_r2,
    input wire me_b0,
    input wire me_b1,
    input wire me_b2,
    input wire me_b3,
    input wire me_b4,
    input wire me_b5,
    input wire me_b6,
    input wire me_b7,
    input wire me_r2,
    input wire me_f0,
    input wire me_f1,
    input wire me_f2,
    input wire me_f3,
    input wire me_f4,
    input wire me_f5,
    input wire me_f6,
    input wire me_f7,
    input wire me_f8,
    input wire me_f9,
    input wire me_f10,
    input wire me_f11,
    input wire me_f12,
    input wire me_f13,
    input wire me_f14,
    input wire me_f15,
    input wire xv_b0,
    input wire xv_b1,
    input wire xv_b2,
    input wire xv_b3,
    input wire xv_b4,
    input wire xv_b5,
    input wire xv_b6,
    input wire xv_b7,
    input wire xv_r2,
    input wire pop_b0,
    input wire pop_b1,
    input wire pop_b2,
    input wire pop_b3,
    input wire pop_b4,
    input wire pop_b5,
    input wire pop_b6,
    input wire pop_b7,
    input wire pop_r2,
    input wire sv_s0,
    input wire sv_s1,
    input wire sv_s2,
    input wire sv_s3,
    input wire sv_s4,
    input wire sv_s5,
    input wire swe_s0,
    input wire swe_s1,
    input wire swe_s2,
    input wire swe_s3,
    input wire swe_s4,
    input wire swe_s5,
    input wire [9:0] swl_s0,
    input wire [9:0] swl_s1,
    input wire [9:0] swl_s2,
    input wire [9:0] swl_s3,
    input wire [9:0] swl_s4,
    input wire [9:0] swl_s5,
    input wire [15:0] swm_s0,
    input wire [15:0] swm_s1,
    input wire [15:0] swm_s2,
    input wire [15:0] swm_s3,
    input wire [15:0] swm_s4,
    input wire [15:0] swm_s5,
    input wire [511:0] swd_s0,
    input wire [511:0] swd_s1,
    input wire [511:0] swd_s2,
    input wire [511:0] swd_s3,
    input wire [511:0] swd_s4,
    input wire [511:0] swd_s5,
    input wire rq_r2,
    input wire [2:0] rqb_r2,
    input wire [1:0] rqb_r0,
    input wire [1:0] rqb_r1,
    input wire me_vm_g6_sW_0,
    input wire me_vm_g6_sW_1,
    input wire me_vm_g6_sW_2,
    input wire me_vm_g6_sW_3,
    input wire me_vm_g6_sW_4,
    input wire me_vm_g6_sW_5,
    input wire me_vm_g6_sW_6,
    input wire me_vm_g6_sW_7,
    input wire me_vm_g6_sW_8,
    input wire me_vm_g6_sW_9,
    input wire me_vm_g6_sA_0,
    input wire me_vm_g6_sA_1,
    input wire me_vm_g6_sA_2,
    input wire me_vm_g6_sA_3,
    input wire me_vm_g6_sA_4,
    input wire me_vm_g6_sA_5,
    input wire me_vm_g6_sA_6,
    input wire me_vm_g6_sA_7,
    input wire me_vm_g6_sA_8,
    input wire me_vm_g6_sA_9,
    input wire me_vm_g6_sB_0,
    input wire me_vm_g6_sB_1,
    input wire me_vm_g6_sB_2,
    input wire me_vm_g6_sB_3,
    input wire me_vm_g6_sB_4,
    input wire me_vm_g6_sB_5,
    input wire me_vm_g6_sB_6,
    input wire me_vm_g6_sB_7,
    input wire me_vm_g6_sB_8,
    input wire me_vm_g6_sB_9,
    input wire [2807:0] d_w,
    input wire [1823:0] d_e,
    output wire [511:0] ro,
    output wire ovf,
    output wire [1023:0] so_s0,
    output wire [1023:0] so_s1,
    output wire [1023:0] so_s2,
    output wire [2975:0] q_w,
    output wire [1687:0] q_e,
    output wire [4063:0] q_s
);
    reg re_b0_f=0;
    always @(posedge face_clk) re_b0_f <= re_b0;
    reg re_b1_f=0;
    always @(posedge face_clk) re_b1_f <= re_b1;
    reg re_b2_f=0;
    always @(posedge face_clk) re_b2_f <= re_b2;
    reg re_b3_f=0;
    always @(posedge face_clk) re_b3_f <= re_b3;
    reg re_b4_f=0;
    always @(posedge face_clk) re_b4_f <= re_b4;
    reg re_b5_f=0;
    always @(posedge face_clk) re_b5_f <= re_b5;
    reg re_b6_f=0;
    always @(posedge face_clk) re_b6_f <= re_b6;
    reg re_b7_f=0;
    always @(posedge face_clk) re_b7_f <= re_b7;
    reg [7:0] ra_b0_f=0;
    always @(posedge face_clk) ra_b0_f <= ra_b0;
    reg [7:0] ra_b1_f=0;
    always @(posedge face_clk) ra_b1_f <= ra_b1;
    reg [7:0] ra_b2_f=0;
    always @(posedge face_clk) ra_b2_f <= ra_b2;
    reg [7:0] ra_b3_f=0;
    always @(posedge face_clk) ra_b3_f <= ra_b3;
    reg [7:0] ra_b4_f=0;
    always @(posedge face_clk) ra_b4_f <= ra_b4;
    reg [7:0] ra_b5_f=0;
    always @(posedge face_clk) ra_b5_f <= ra_b5;
    reg [7:0] ra_b6_f=0;
    always @(posedge face_clk) ra_b6_f <= ra_b6;
    reg [7:0] ra_b7_f=0;
    always @(posedge face_clk) ra_b7_f <= ra_b7;
    reg we_b0_f=0;
    always @(posedge face_clk) we_b0_f <= we_b0;
    reg we_b1_f=0;
    always @(posedge face_clk) we_b1_f <= we_b1;
    reg we_b2_f=0;
    always @(posedge face_clk) we_b2_f <= we_b2;
    reg we_b3_f=0;
    always @(posedge face_clk) we_b3_f <= we_b3;
    reg we_b4_f=0;
    always @(posedge face_clk) we_b4_f <= we_b4;
    reg we_b5_f=0;
    always @(posedge face_clk) we_b5_f <= we_b5;
    reg we_b6_f=0;
    always @(posedge face_clk) we_b6_f <= we_b6;
    reg we_b7_f=0;
    always @(posedge face_clk) we_b7_f <= we_b7;
    reg [7:0] wl_b0_f=0;
    always @(posedge face_clk) wl_b0_f <= wl_b0;
    reg [7:0] wl_b1_f=0;
    always @(posedge face_clk) wl_b1_f <= wl_b1;
    reg [7:0] wl_b2_f=0;
    always @(posedge face_clk) wl_b2_f <= wl_b2;
    reg [7:0] wl_b3_f=0;
    always @(posedge face_clk) wl_b3_f <= wl_b3;
    reg [7:0] wl_b4_f=0;
    always @(posedge face_clk) wl_b4_f <= wl_b4;
    reg [7:0] wl_b5_f=0;
    always @(posedge face_clk) wl_b5_f <= wl_b5;
    reg [7:0] wl_b6_f=0;
    always @(posedge face_clk) wl_b6_f <= wl_b6;
    reg [7:0] wl_b7_f=0;
    always @(posedge face_clk) wl_b7_f <= wl_b7;
    reg [15:0] wm_b0_f=0;
    always @(posedge face_clk) wm_b0_f <= wm_b0;
    reg [15:0] wm_b1_f=0;
    always @(posedge face_clk) wm_b1_f <= wm_b1;
    reg [15:0] wm_b2_f=0;
    always @(posedge face_clk) wm_b2_f <= wm_b2;
    reg [15:0] wm_b3_f=0;
    always @(posedge face_clk) wm_b3_f <= wm_b3;
    reg [15:0] wm_b4_f=0;
    always @(posedge face_clk) wm_b4_f <= wm_b4;
    reg [15:0] wm_b5_f=0;
    always @(posedge face_clk) wm_b5_f <= wm_b5;
    reg [15:0] wm_b6_f=0;
    always @(posedge face_clk) wm_b6_f <= wm_b6;
    reg [15:0] wm_b7_f=0;
    always @(posedge face_clk) wm_b7_f <= wm_b7;
    reg [511:0] wd_b0_f=0;
    always @(posedge face_clk) wd_b0_f <= wd_b0;
    reg [511:0] wd_b1_f=0;
    always @(posedge face_clk) wd_b1_f <= wd_b1;
    reg [511:0] wd_b2_f=0;
    always @(posedge face_clk) wd_b2_f <= wd_b2;
    reg [511:0] wd_b3_f=0;
    always @(posedge face_clk) wd_b3_f <= wd_b3;
    reg [511:0] wd_b4_f=0;
    always @(posedge face_clk) wd_b4_f <= wd_b4;
    reg [511:0] wd_b5_f=0;
    always @(posedge face_clk) wd_b5_f <= wd_b5;
    reg [511:0] wd_b6_f=0;
    always @(posedge face_clk) wd_b6_f <= wd_b6;
    reg [511:0] wd_b7_f=0;
    always @(posedge face_clk) wd_b7_f <= wd_b7;
    reg sre_s0_f=0;
    always @(posedge face_clk) sre_s0_f <= sre_s0;
    reg sre_s1_f=0;
    always @(posedge face_clk) sre_s1_f <= sre_s1;
    reg sre_s2_f=0;
    always @(posedge face_clk) sre_s2_f <= sre_s2;
    reg sre_s3_f=0;
    always @(posedge face_clk) sre_s3_f <= sre_s3;
    reg sre_s4_f=0;
    always @(posedge face_clk) sre_s4_f <= sre_s4;
    reg sre_s5_f=0;
    always @(posedge face_clk) sre_s5_f <= sre_s5;
    reg [9:0] sra_s0_f=0;
    always @(posedge face_clk) sra_s0_f <= sra_s0;
    reg [9:0] sra_s1_f=0;
    always @(posedge face_clk) sra_s1_f <= sra_s1;
    reg [9:0] sra_s2_f=0;
    always @(posedge face_clk) sra_s2_f <= sra_s2;
    reg [9:0] sra_s3_f=0;
    always @(posedge face_clk) sra_s3_f <= sra_s3;
    reg [9:0] sra_s4_f=0;
    always @(posedge face_clk) sra_s4_f <= sra_s4;
    reg [9:0] sra_s5_f=0;
    always @(posedge face_clk) sra_s5_f <= sra_s5;
    reg me_b0_f=0;
    always @(posedge face_clk) me_b0_f <= me_b0;
    reg me_b1_f=0;
    always @(posedge face_clk) me_b1_f <= me_b1;
    reg me_b2_f=0;
    always @(posedge face_clk) me_b2_f <= me_b2;
    reg me_b3_f=0;
    always @(posedge face_clk) me_b3_f <= me_b3;
    reg me_b4_f=0;
    always @(posedge face_clk) me_b4_f <= me_b4;
    reg me_b5_f=0;
    always @(posedge face_clk) me_b5_f <= me_b5;
    reg me_b6_f=0;
    always @(posedge face_clk) me_b6_f <= me_b6;
    reg me_b7_f=0;
    always @(posedge face_clk) me_b7_f <= me_b7;
    reg me_r2_f=0;
    always @(posedge face_clk) me_r2_f <= me_r2;
    reg me_f0_f=0;
    always @(posedge face_clk) me_f0_f <= me_f0;
    reg me_f1_f=0;
    always @(posedge face_clk) me_f1_f <= me_f1;
    reg me_f2_f=0;
    always @(posedge face_clk) me_f2_f <= me_f2;
    reg me_f3_f=0;
    always @(posedge face_clk) me_f3_f <= me_f3;
    reg me_f4_f=0;
    always @(posedge face_clk) me_f4_f <= me_f4;
    reg me_f5_f=0;
    always @(posedge face_clk) me_f5_f <= me_f5;
    reg me_f6_f=0;
    always @(posedge face_clk) me_f6_f <= me_f6;
    reg me_f7_f=0;
    always @(posedge face_clk) me_f7_f <= me_f7;
    reg me_f8_f=0;
    always @(posedge face_clk) me_f8_f <= me_f8;
    reg me_f9_f=0;
    always @(posedge face_clk) me_f9_f <= me_f9;
    reg me_f10_f=0;
    always @(posedge face_clk) me_f10_f <= me_f10;
    reg me_f11_f=0;
    always @(posedge face_clk) me_f11_f <= me_f11;
    reg me_f12_f=0;
    always @(posedge face_clk) me_f12_f <= me_f12;
    reg me_f13_f=0;
    always @(posedge face_clk) me_f13_f <= me_f13;
    reg me_f14_f=0;
    always @(posedge face_clk) me_f14_f <= me_f14;
    reg me_f15_f=0;
    always @(posedge face_clk) me_f15_f <= me_f15;
    reg xv_b0_f=0;
    always @(posedge face_clk) xv_b0_f <= xv_b0;
    reg xv_b1_f=0;
    always @(posedge face_clk) xv_b1_f <= xv_b1;
    reg xv_b2_f=0;
    always @(posedge face_clk) xv_b2_f <= xv_b2;
    reg xv_b3_f=0;
    always @(posedge face_clk) xv_b3_f <= xv_b3;
    reg xv_b4_f=0;
    always @(posedge face_clk) xv_b4_f <= xv_b4;
    reg xv_b5_f=0;
    always @(posedge face_clk) xv_b5_f <= xv_b5;
    reg xv_b6_f=0;
    always @(posedge face_clk) xv_b6_f <= xv_b6;
    reg xv_b7_f=0;
    always @(posedge face_clk) xv_b7_f <= xv_b7;
    reg xv_r2_f=0;
    always @(posedge face_clk) xv_r2_f <= xv_r2;
    reg pop_b0_f=0;
    always @(posedge face_clk) pop_b0_f <= pop_b0;
    reg pop_b1_f=0;
    always @(posedge face_clk) pop_b1_f <= pop_b1;
    reg pop_b2_f=0;
    always @(posedge face_clk) pop_b2_f <= pop_b2;
    reg pop_b3_f=0;
    always @(posedge face_clk) pop_b3_f <= pop_b3;
    reg pop_b4_f=0;
    always @(posedge face_clk) pop_b4_f <= pop_b4;
    reg pop_b5_f=0;
    always @(posedge face_clk) pop_b5_f <= pop_b5;
    reg pop_b6_f=0;
    always @(posedge face_clk) pop_b6_f <= pop_b6;
    reg pop_b7_f=0;
    always @(posedge face_clk) pop_b7_f <= pop_b7;
    reg pop_r2_f=0;
    always @(posedge face_clk) pop_r2_f <= pop_r2;
    reg sv_s0_f=0;
    always @(posedge face_clk) sv_s0_f <= sv_s0;
    reg sv_s1_f=0;
    always @(posedge face_clk) sv_s1_f <= sv_s1;
    reg sv_s2_f=0;
    always @(posedge face_clk) sv_s2_f <= sv_s2;
    reg sv_s3_f=0;
    always @(posedge face_clk) sv_s3_f <= sv_s3;
    reg sv_s4_f=0;
    always @(posedge face_clk) sv_s4_f <= sv_s4;
    reg sv_s5_f=0;
    always @(posedge face_clk) sv_s5_f <= sv_s5;
    reg swe_s0_f=0;
    always @(posedge face_clk) swe_s0_f <= swe_s0;
    reg swe_s1_f=0;
    always @(posedge face_clk) swe_s1_f <= swe_s1;
    reg swe_s2_f=0;
    always @(posedge face_clk) swe_s2_f <= swe_s2;
    reg swe_s3_f=0;
    always @(posedge face_clk) swe_s3_f <= swe_s3;
    reg swe_s4_f=0;
    always @(posedge face_clk) swe_s4_f <= swe_s4;
    reg swe_s5_f=0;
    always @(posedge face_clk) swe_s5_f <= swe_s5;
    reg [9:0] swl_s0_f=0;
    always @(posedge face_clk) swl_s0_f <= swl_s0;
    reg [9:0] swl_s1_f=0;
    always @(posedge face_clk) swl_s1_f <= swl_s1;
    reg [9:0] swl_s2_f=0;
    always @(posedge face_clk) swl_s2_f <= swl_s2;
    reg [9:0] swl_s3_f=0;
    always @(posedge face_clk) swl_s3_f <= swl_s3;
    reg [9:0] swl_s4_f=0;
    always @(posedge face_clk) swl_s4_f <= swl_s4;
    reg [9:0] swl_s5_f=0;
    always @(posedge face_clk) swl_s5_f <= swl_s5;
    reg [15:0] swm_s0_f=0;
    always @(posedge face_clk) swm_s0_f <= swm_s0;
    reg [15:0] swm_s1_f=0;
    always @(posedge face_clk) swm_s1_f <= swm_s1;
    reg [15:0] swm_s2_f=0;
    always @(posedge face_clk) swm_s2_f <= swm_s2;
    reg [15:0] swm_s3_f=0;
    always @(posedge face_clk) swm_s3_f <= swm_s3;
    reg [15:0] swm_s4_f=0;
    always @(posedge face_clk) swm_s4_f <= swm_s4;
    reg [15:0] swm_s5_f=0;
    always @(posedge face_clk) swm_s5_f <= swm_s5;
    reg [511:0] swd_s0_f=0;
    always @(posedge face_clk) swd_s0_f <= swd_s0;
    reg [511:0] swd_s1_f=0;
    always @(posedge face_clk) swd_s1_f <= swd_s1;
    reg [511:0] swd_s2_f=0;
    always @(posedge face_clk) swd_s2_f <= swd_s2;
    reg [511:0] swd_s3_f=0;
    always @(posedge face_clk) swd_s3_f <= swd_s3;
    reg [511:0] swd_s4_f=0;
    always @(posedge face_clk) swd_s4_f <= swd_s4;
    reg [511:0] swd_s5_f=0;
    always @(posedge face_clk) swd_s5_f <= swd_s5;
    reg rq_r2_f=0;
    always @(posedge face_clk) rq_r2_f <= rq_r2;
    reg [2:0] rqb_r2_f=0;
    always @(posedge face_clk) rqb_r2_f <= rqb_r2;
    reg [1:0] rqb_r0_f=0;
    always @(posedge face_clk) rqb_r0_f <= rqb_r0;
    reg [1:0] rqb_r1_f=0;
    always @(posedge face_clk) rqb_r1_f <= rqb_r1;
    reg me_vm_g6_sW_0_f=0;
    always @(posedge face_clk) me_vm_g6_sW_0_f <= me_vm_g6_sW_0;
    reg me_vm_g6_sW_1_f=0;
    always @(posedge face_clk) me_vm_g6_sW_1_f <= me_vm_g6_sW_1;
    reg me_vm_g6_sW_2_f=0;
    always @(posedge face_clk) me_vm_g6_sW_2_f <= me_vm_g6_sW_2;
    reg me_vm_g6_sW_3_f=0;
    always @(posedge face_clk) me_vm_g6_sW_3_f <= me_vm_g6_sW_3;
    reg me_vm_g6_sW_4_f=0;
    always @(posedge face_clk) me_vm_g6_sW_4_f <= me_vm_g6_sW_4;
    reg me_vm_g6_sW_5_f=0;
    always @(posedge face_clk) me_vm_g6_sW_5_f <= me_vm_g6_sW_5;
    reg me_vm_g6_sW_6_f=0;
    always @(posedge face_clk) me_vm_g6_sW_6_f <= me_vm_g6_sW_6;
    reg me_vm_g6_sW_7_f=0;
    always @(posedge face_clk) me_vm_g6_sW_7_f <= me_vm_g6_sW_7;
    reg me_vm_g6_sW_8_f=0;
    always @(posedge face_clk) me_vm_g6_sW_8_f <= me_vm_g6_sW_8;
    reg me_vm_g6_sW_9_f=0;
    always @(posedge face_clk) me_vm_g6_sW_9_f <= me_vm_g6_sW_9;
    reg me_vm_g6_sA_0_f=0;
    always @(posedge face_clk) me_vm_g6_sA_0_f <= me_vm_g6_sA_0;
    reg me_vm_g6_sA_1_f=0;
    always @(posedge face_clk) me_vm_g6_sA_1_f <= me_vm_g6_sA_1;
    reg me_vm_g6_sA_2_f=0;
    always @(posedge face_clk) me_vm_g6_sA_2_f <= me_vm_g6_sA_2;
    reg me_vm_g6_sA_3_f=0;
    always @(posedge face_clk) me_vm_g6_sA_3_f <= me_vm_g6_sA_3;
    reg me_vm_g6_sA_4_f=0;
    always @(posedge face_clk) me_vm_g6_sA_4_f <= me_vm_g6_sA_4;
    reg me_vm_g6_sA_5_f=0;
    always @(posedge face_clk) me_vm_g6_sA_5_f <= me_vm_g6_sA_5;
    reg me_vm_g6_sA_6_f=0;
    always @(posedge face_clk) me_vm_g6_sA_6_f <= me_vm_g6_sA_6;
    reg me_vm_g6_sA_7_f=0;
    always @(posedge face_clk) me_vm_g6_sA_7_f <= me_vm_g6_sA_7;
    reg me_vm_g6_sA_8_f=0;
    always @(posedge face_clk) me_vm_g6_sA_8_f <= me_vm_g6_sA_8;
    reg me_vm_g6_sA_9_f=0;
    always @(posedge face_clk) me_vm_g6_sA_9_f <= me_vm_g6_sA_9;
    reg me_vm_g6_sB_0_f=0;
    always @(posedge face_clk) me_vm_g6_sB_0_f <= me_vm_g6_sB_0;
    reg me_vm_g6_sB_1_f=0;
    always @(posedge face_clk) me_vm_g6_sB_1_f <= me_vm_g6_sB_1;
    reg me_vm_g6_sB_2_f=0;
    always @(posedge face_clk) me_vm_g6_sB_2_f <= me_vm_g6_sB_2;
    reg me_vm_g6_sB_3_f=0;
    always @(posedge face_clk) me_vm_g6_sB_3_f <= me_vm_g6_sB_3;
    reg me_vm_g6_sB_4_f=0;
    always @(posedge face_clk) me_vm_g6_sB_4_f <= me_vm_g6_sB_4;
    reg me_vm_g6_sB_5_f=0;
    always @(posedge face_clk) me_vm_g6_sB_5_f <= me_vm_g6_sB_5;
    reg me_vm_g6_sB_6_f=0;
    always @(posedge face_clk) me_vm_g6_sB_6_f <= me_vm_g6_sB_6;
    reg me_vm_g6_sB_7_f=0;
    always @(posedge face_clk) me_vm_g6_sB_7_f <= me_vm_g6_sB_7;
    reg me_vm_g6_sB_8_f=0;
    always @(posedge face_clk) me_vm_g6_sB_8_f <= me_vm_g6_sB_8;
    reg me_vm_g6_sB_9_f=0;
    always @(posedge face_clk) me_vm_g6_sB_9_f <= me_vm_g6_sB_9;
    reg face_me_prev=0;
    always @(posedge face_clk) face_me_prev <= me_vm_g6_sW_0_f;
    wire face_enable = (MUT == 4) ? me_vm_g6_sW_0 : face_me_prev;
    reg [2807:0] d_w_f=0;
    always @(posedge face_clk) if (face_enable) d_w_f <= d_w;
    reg [1823:0] d_e_f=0;
    always @(posedge face_clk) if (face_enable) d_e_f <= d_e;
    wire [511:0] ro_raw;
    reg [511:0] ro_f=0;
    always @(posedge face_clk) ro_f <= ro_raw;
    assign ro = ro_f;
    wire ovf_raw;
    reg ovf_f=0;
    always @(posedge face_clk) ovf_f <= ovf_raw;
    assign ovf = ovf_f;
    wire [1023:0] so_s0_raw;
    reg [1023:0] so_s0_f=0;
    always @(posedge face_clk) so_s0_f <= so_s0_raw;
    assign so_s0 = so_s0_f;
    wire [1023:0] so_s1_raw;
    reg [1023:0] so_s1_f=0;
    always @(posedge face_clk) so_s1_f <= so_s1_raw;
    assign so_s1 = so_s1_f;
    wire [1023:0] so_s2_raw;
    reg [1023:0] so_s2_f=0;
    always @(posedge face_clk) so_s2_f <= so_s2_raw;
    assign so_s2 = so_s2_f;
    wire [2975:0] q_w_raw;
    reg [2975:0] q_w_f=0;
    always @(posedge face_clk) if (face_enable) q_w_f <= q_w_raw;
    assign q_w = q_w_f;
    wire [1687:0] q_e_raw;
    reg [1687:0] q_e_f=0;
    always @(posedge face_clk) if (face_enable) q_e_f <= q_e_raw;
    assign q_e = q_e_f;
    wire [4063:0] q_s_raw;
    reg [4063:0] q_s_f=0;
    always @(posedge face_clk) if (face_enable) q_s_f <= q_s_raw;
    assign q_s = q_s_f;
    ot_qfd_vm_rg6 #(.MUT((MUT < 3) ? MUT : 0)) u_base (
      .ck_c0(ck_c0),
      .ck_c1(ck_c1),
      .ck_c2(ck_c2),
      .ck_c3(ck_c3),
      .ck_c4(ck_c4),
      .ck_c5(ck_c5),
      .ck_c6(ck_c6),
      .ck_c7(ck_c7),
      .ck_c8(ck_c8),
      .ck_c9(ck_c9),
      .ck_c10(ck_c10),
      .ck_c11(ck_c11),
      .ck_c12(ck_c12),
      .ck_c13(ck_c13),
      .ck_c14(ck_c14),
      .ck_c15(ck_c15),
      .ck_c16(ck_c16),
      .ck_c17(ck_c17),
      .ck_c18(ck_c18),
      .ck_c19(ck_c19),
      .ck_c20(ck_c20),
      .ck_c21(ck_c21),
      .ck_c22(ck_c22),
      .ck_c23(ck_c23),
      .ck_c24(ck_c24),
      .ck_c25(ck_c25),
      .ck_c26(ck_c26),
      .ck_c27(ck_c27),
      .ck_c28(ck_c28),
      .ck_c29(ck_c29),
      .ck_c30(ck_c30),
      .ck_c31(ck_c31),
      .ck_c32(ck_c32),
      .ck_c33(ck_c33),
      .ck_c34(ck_c34),
      .ck_c35(ck_c35),
      .ck_c36(ck_c36),
      .ck_c37(ck_c37),
      .ck_c38(ck_c38),
      .ck_c39(ck_c39),
      .ck_c40(ck_c40),
      .ck_c41(ck_c41),
      .ck_c42(ck_c42),
      .ck_c43(ck_c43),
      .ck_c44(ck_c44),
      .ck_c45(ck_c45),
      .ck_c46(ck_c46),
      .ck_c47(ck_c47),
      .ck_c48(ck_c48),
      .ck_c49(ck_c49),
      .ck_c50(ck_c50),
      .ck_c51(ck_c51),
      .ck_c52(ck_c52),
      .ck_c53(ck_c53),
      .ck_c54(ck_c54),
      .ck_c55(ck_c55),
      .ck_c56(ck_c56),
      .ck_c57(ck_c57),
      .ck_c58(ck_c58),
      .ck_c59(ck_c59),
      .ck_c60(ck_c60),
      .ck_c61(ck_c61),
      .ck_c62(ck_c62),
      .ck_c63(ck_c63),
      .ck_c64(ck_c64),
      .ck_c65(ck_c65),
      .ck_c66(ck_c66),
      .ck_c67(ck_c67),
      .ck_c68(ck_c68),
      .ck_c69(ck_c69),
      .ck_c70(ck_c70),
      .ck_c71(ck_c71),
      .ck_t0(ck_t0),
      .ck_t1(ck_t1),
      .ck_t2(ck_t2),
      .ck_t3(ck_t3),
      .ck_t4(ck_t4),
      .ck_t5(ck_t5),
      .ck_t6(ck_t6),
      .ck_t7(ck_t7),
      .ck_t8(ck_t8),
      .ck_t9(ck_t9),
      .ck_t10(ck_t10),
      .ck_t11(ck_t11),
      .ck_t12(ck_t12),
      .ck_t13(ck_t13),
      .ck_t14(ck_t14),
      .ck_t15(ck_t15),
      .ck_t16(ck_t16),
      .ck_t17(ck_t17),
      .ck_t18(ck_t18),
      .ck_t19(ck_t19),
      .ck_t20(ck_t20),
      .ck_t21(ck_t21),
      .ck_t22(ck_t22),
      .ck_t23(ck_t23),
      .ck_t24(ck_t24),
      .ck_t25(ck_t25),
      .ck_t26(ck_t26),
      .ck_t27(ck_t27),
      .ck_t28(ck_t28),
      .ck_t29(ck_t29),
      .ck_t30(ck_t30),
      .ck_t31(ck_t31),
      .ck_t32(ck_t32),
      .ck_t33(ck_t33),
      .ck_t34(ck_t34),
      .ck_t35(ck_t35),
      .ck_t36(ck_t36),
      .ck_t37(ck_t37),
      .ck_t38(ck_t38),
      .ck_t39(ck_t39),
      .ck_t40(ck_t40),
      .ck_t41(ck_t41),
      .ck_t42(ck_t42),
      .ck_t43(ck_t43),
      .ck_t44(ck_t44),
      .ck_t45(ck_t45),
      .ck_t46(ck_t46),
      .ck_t47(ck_t47),
      .ck_t48(ck_t48),
      .ck_t49(ck_t49),
      .ck_t50(ck_t50),
      .ck_t51(ck_t51),
      .ck_t52(ck_t52),
      .ck_t53(ck_t53),
      .ck_t54(ck_t54),
      .ck_t55(ck_t55),
      .ck_t56(ck_t56),
      .ck_t57(ck_t57),
      .ck_t58(ck_t58),
      .ck_t59(ck_t59),
      .ck_t60(ck_t60),
      .ck_t61(ck_t61),
      .ck_t62(ck_t62),
      .ck_t63(ck_t63),
      .ck_t64(ck_t64),
      .ck_t65(ck_t65),
      .ck_t66(ck_t66),
      .ck_t67(ck_t67),
      .ck_t68(ck_t68),
      .ck_t69(ck_t69),
      .ck_t70(ck_t70),
      .ck_t71(ck_t71),
      .ck_t72(ck_t72),
      .ck_t73(ck_t73),
      .ck_t74(ck_t74),
      .ck_t75(ck_t75),
      .ck_t76(ck_t76),
      .re_b0(((MUT == 3) ? re_b0 : re_b0_f)),
      .re_b1(((MUT == 3) ? re_b1 : re_b1_f)),
      .re_b2(((MUT == 3) ? re_b2 : re_b2_f)),
      .re_b3(((MUT == 3) ? re_b3 : re_b3_f)),
      .re_b4(((MUT == 3) ? re_b4 : re_b4_f)),
      .re_b5(((MUT == 3) ? re_b5 : re_b5_f)),
      .re_b6(((MUT == 3) ? re_b6 : re_b6_f)),
      .re_b7(((MUT == 3) ? re_b7 : re_b7_f)),
      .ra_b0(((MUT == 3) ? ra_b0 : ra_b0_f)),
      .ra_b1(((MUT == 3) ? ra_b1 : ra_b1_f)),
      .ra_b2(((MUT == 3) ? ra_b2 : ra_b2_f)),
      .ra_b3(((MUT == 3) ? ra_b3 : ra_b3_f)),
      .ra_b4(((MUT == 3) ? ra_b4 : ra_b4_f)),
      .ra_b5(((MUT == 3) ? ra_b5 : ra_b5_f)),
      .ra_b6(((MUT == 3) ? ra_b6 : ra_b6_f)),
      .ra_b7(((MUT == 3) ? ra_b7 : ra_b7_f)),
      .we_b0(((MUT == 3) ? we_b0 : we_b0_f)),
      .we_b1(((MUT == 3) ? we_b1 : we_b1_f)),
      .we_b2(((MUT == 3) ? we_b2 : we_b2_f)),
      .we_b3(((MUT == 3) ? we_b3 : we_b3_f)),
      .we_b4(((MUT == 3) ? we_b4 : we_b4_f)),
      .we_b5(((MUT == 3) ? we_b5 : we_b5_f)),
      .we_b6(((MUT == 3) ? we_b6 : we_b6_f)),
      .we_b7(((MUT == 3) ? we_b7 : we_b7_f)),
      .wl_b0(((MUT == 3) ? wl_b0 : wl_b0_f)),
      .wl_b1(((MUT == 3) ? wl_b1 : wl_b1_f)),
      .wl_b2(((MUT == 3) ? wl_b2 : wl_b2_f)),
      .wl_b3(((MUT == 3) ? wl_b3 : wl_b3_f)),
      .wl_b4(((MUT == 3) ? wl_b4 : wl_b4_f)),
      .wl_b5(((MUT == 3) ? wl_b5 : wl_b5_f)),
      .wl_b6(((MUT == 3) ? wl_b6 : wl_b6_f)),
      .wl_b7(((MUT == 3) ? wl_b7 : wl_b7_f)),
      .wm_b0(((MUT == 3) ? wm_b0 : wm_b0_f)),
      .wm_b1(((MUT == 3) ? wm_b1 : wm_b1_f)),
      .wm_b2(((MUT == 3) ? wm_b2 : wm_b2_f)),
      .wm_b3(((MUT == 3) ? wm_b3 : wm_b3_f)),
      .wm_b4(((MUT == 3) ? wm_b4 : wm_b4_f)),
      .wm_b5(((MUT == 3) ? wm_b5 : wm_b5_f)),
      .wm_b6(((MUT == 3) ? wm_b6 : wm_b6_f)),
      .wm_b7(((MUT == 3) ? wm_b7 : wm_b7_f)),
      .wd_b0(((MUT == 3) ? wd_b0 : wd_b0_f)),
      .wd_b1(((MUT == 3) ? wd_b1 : wd_b1_f)),
      .wd_b2(((MUT == 3) ? wd_b2 : wd_b2_f)),
      .wd_b3(((MUT == 3) ? wd_b3 : wd_b3_f)),
      .wd_b4(((MUT == 3) ? wd_b4 : wd_b4_f)),
      .wd_b5(((MUT == 3) ? wd_b5 : wd_b5_f)),
      .wd_b6(((MUT == 3) ? wd_b6 : wd_b6_f)),
      .wd_b7(((MUT == 3) ? wd_b7 : wd_b7_f)),
      .sre_s0(((MUT == 3) ? sre_s0 : sre_s0_f)),
      .sre_s1(((MUT == 3) ? sre_s1 : sre_s1_f)),
      .sre_s2(((MUT == 3) ? sre_s2 : sre_s2_f)),
      .sre_s3(((MUT == 3) ? sre_s3 : sre_s3_f)),
      .sre_s4(((MUT == 3) ? sre_s4 : sre_s4_f)),
      .sre_s5(((MUT == 3) ? sre_s5 : sre_s5_f)),
      .sra_s0(((MUT == 3) ? sra_s0 : sra_s0_f)),
      .sra_s1(((MUT == 3) ? sra_s1 : sra_s1_f)),
      .sra_s2(((MUT == 3) ? sra_s2 : sra_s2_f)),
      .sra_s3(((MUT == 3) ? sra_s3 : sra_s3_f)),
      .sra_s4(((MUT == 3) ? sra_s4 : sra_s4_f)),
      .sra_s5(((MUT == 3) ? sra_s5 : sra_s5_f)),
      .rst_b0(rst_b0),
      .rst_b1(rst_b1),
      .rst_b2(rst_b2),
      .rst_b3(rst_b3),
      .rst_b4(rst_b4),
      .rst_b5(rst_b5),
      .rst_b6(rst_b6),
      .rst_b7(rst_b7),
      .rst_s0(rst_s0),
      .rst_s1(rst_s1),
      .rst_s2(rst_s2),
      .rst_s3(rst_s3),
      .rst_s4(rst_s4),
      .rst_s5(rst_s5),
      .rst_r0(rst_r0),
      .rst_r1(rst_r1),
      .rst_r2(rst_r2),
      .me_b0(((MUT == 3) ? me_b0 : me_b0_f)),
      .me_b1(((MUT == 3) ? me_b1 : me_b1_f)),
      .me_b2(((MUT == 3) ? me_b2 : me_b2_f)),
      .me_b3(((MUT == 3) ? me_b3 : me_b3_f)),
      .me_b4(((MUT == 3) ? me_b4 : me_b4_f)),
      .me_b5(((MUT == 3) ? me_b5 : me_b5_f)),
      .me_b6(((MUT == 3) ? me_b6 : me_b6_f)),
      .me_b7(((MUT == 3) ? me_b7 : me_b7_f)),
      .me_r2(((MUT == 3) ? me_r2 : me_r2_f)),
      .me_f0(((MUT == 3) ? me_f0 : me_f0_f)),
      .me_f1(((MUT == 3) ? me_f1 : me_f1_f)),
      .me_f2(((MUT == 3) ? me_f2 : me_f2_f)),
      .me_f3(((MUT == 3) ? me_f3 : me_f3_f)),
      .me_f4(((MUT == 3) ? me_f4 : me_f4_f)),
      .me_f5(((MUT == 3) ? me_f5 : me_f5_f)),
      .me_f6(((MUT == 3) ? me_f6 : me_f6_f)),
      .me_f7(((MUT == 3) ? me_f7 : me_f7_f)),
      .me_f8(((MUT == 3) ? me_f8 : me_f8_f)),
      .me_f9(((MUT == 3) ? me_f9 : me_f9_f)),
      .me_f10(((MUT == 3) ? me_f10 : me_f10_f)),
      .me_f11(((MUT == 3) ? me_f11 : me_f11_f)),
      .me_f12(((MUT == 3) ? me_f12 : me_f12_f)),
      .me_f13(((MUT == 3) ? me_f13 : me_f13_f)),
      .me_f14(((MUT == 3) ? me_f14 : me_f14_f)),
      .me_f15(((MUT == 3) ? me_f15 : me_f15_f)),
      .xv_b0(((MUT == 3) ? xv_b0 : xv_b0_f)),
      .xv_b1(((MUT == 3) ? xv_b1 : xv_b1_f)),
      .xv_b2(((MUT == 3) ? xv_b2 : xv_b2_f)),
      .xv_b3(((MUT == 3) ? xv_b3 : xv_b3_f)),
      .xv_b4(((MUT == 3) ? xv_b4 : xv_b4_f)),
      .xv_b5(((MUT == 3) ? xv_b5 : xv_b5_f)),
      .xv_b6(((MUT == 3) ? xv_b6 : xv_b6_f)),
      .xv_b7(((MUT == 3) ? xv_b7 : xv_b7_f)),
      .xv_r2(((MUT == 3) ? xv_r2 : xv_r2_f)),
      .pop_b0(((MUT == 3) ? pop_b0 : pop_b0_f)),
      .pop_b1(((MUT == 3) ? pop_b1 : pop_b1_f)),
      .pop_b2(((MUT == 3) ? pop_b2 : pop_b2_f)),
      .pop_b3(((MUT == 3) ? pop_b3 : pop_b3_f)),
      .pop_b4(((MUT == 3) ? pop_b4 : pop_b4_f)),
      .pop_b5(((MUT == 3) ? pop_b5 : pop_b5_f)),
      .pop_b6(((MUT == 3) ? pop_b6 : pop_b6_f)),
      .pop_b7(((MUT == 3) ? pop_b7 : pop_b7_f)),
      .pop_r2(((MUT == 3) ? pop_r2 : pop_r2_f)),
      .sv_s0(((MUT == 3) ? sv_s0 : sv_s0_f)),
      .sv_s1(((MUT == 3) ? sv_s1 : sv_s1_f)),
      .sv_s2(((MUT == 3) ? sv_s2 : sv_s2_f)),
      .sv_s3(((MUT == 3) ? sv_s3 : sv_s3_f)),
      .sv_s4(((MUT == 3) ? sv_s4 : sv_s4_f)),
      .sv_s5(((MUT == 3) ? sv_s5 : sv_s5_f)),
      .swe_s0(((MUT == 3) ? swe_s0 : swe_s0_f)),
      .swe_s1(((MUT == 3) ? swe_s1 : swe_s1_f)),
      .swe_s2(((MUT == 3) ? swe_s2 : swe_s2_f)),
      .swe_s3(((MUT == 3) ? swe_s3 : swe_s3_f)),
      .swe_s4(((MUT == 3) ? swe_s4 : swe_s4_f)),
      .swe_s5(((MUT == 3) ? swe_s5 : swe_s5_f)),
      .swl_s0(((MUT == 3) ? swl_s0 : swl_s0_f)),
      .swl_s1(((MUT == 3) ? swl_s1 : swl_s1_f)),
      .swl_s2(((MUT == 3) ? swl_s2 : swl_s2_f)),
      .swl_s3(((MUT == 3) ? swl_s3 : swl_s3_f)),
      .swl_s4(((MUT == 3) ? swl_s4 : swl_s4_f)),
      .swl_s5(((MUT == 3) ? swl_s5 : swl_s5_f)),
      .swm_s0(((MUT == 3) ? swm_s0 : swm_s0_f)),
      .swm_s1(((MUT == 3) ? swm_s1 : swm_s1_f)),
      .swm_s2(((MUT == 3) ? swm_s2 : swm_s2_f)),
      .swm_s3(((MUT == 3) ? swm_s3 : swm_s3_f)),
      .swm_s4(((MUT == 3) ? swm_s4 : swm_s4_f)),
      .swm_s5(((MUT == 3) ? swm_s5 : swm_s5_f)),
      .swd_s0(((MUT == 3) ? swd_s0 : swd_s0_f)),
      .swd_s1(((MUT == 3) ? swd_s1 : swd_s1_f)),
      .swd_s2(((MUT == 3) ? swd_s2 : swd_s2_f)),
      .swd_s3(((MUT == 3) ? swd_s3 : swd_s3_f)),
      .swd_s4(((MUT == 3) ? swd_s4 : swd_s4_f)),
      .swd_s5(((MUT == 3) ? swd_s5 : swd_s5_f)),
      .rq_r2(((MUT == 3) ? rq_r2 : rq_r2_f)),
      .rqb_r2(((MUT == 3) ? rqb_r2 : rqb_r2_f)),
      .rqb_r0(((MUT == 3) ? rqb_r0 : rqb_r0_f)),
      .rqb_r1(((MUT == 3) ? rqb_r1 : rqb_r1_f)),
      .me_vm_g6_sW_0(((MUT == 3) ? me_vm_g6_sW_0 : me_vm_g6_sW_0_f)),
      .me_vm_g6_sW_1(((MUT == 3) ? me_vm_g6_sW_1 : me_vm_g6_sW_1_f)),
      .me_vm_g6_sW_2(((MUT == 3) ? me_vm_g6_sW_2 : me_vm_g6_sW_2_f)),
      .me_vm_g6_sW_3(((MUT == 3) ? me_vm_g6_sW_3 : me_vm_g6_sW_3_f)),
      .me_vm_g6_sW_4(((MUT == 3) ? me_vm_g6_sW_4 : me_vm_g6_sW_4_f)),
      .me_vm_g6_sW_5(((MUT == 3) ? me_vm_g6_sW_5 : me_vm_g6_sW_5_f)),
      .me_vm_g6_sW_6(((MUT == 3) ? me_vm_g6_sW_6 : me_vm_g6_sW_6_f)),
      .me_vm_g6_sW_7(((MUT == 3) ? me_vm_g6_sW_7 : me_vm_g6_sW_7_f)),
      .me_vm_g6_sW_8(((MUT == 3) ? me_vm_g6_sW_8 : me_vm_g6_sW_8_f)),
      .me_vm_g6_sW_9(((MUT == 3) ? me_vm_g6_sW_9 : me_vm_g6_sW_9_f)),
      .me_vm_g6_sA_0(((MUT == 3) ? me_vm_g6_sA_0 : me_vm_g6_sA_0_f)),
      .me_vm_g6_sA_1(((MUT == 3) ? me_vm_g6_sA_1 : me_vm_g6_sA_1_f)),
      .me_vm_g6_sA_2(((MUT == 3) ? me_vm_g6_sA_2 : me_vm_g6_sA_2_f)),
      .me_vm_g6_sA_3(((MUT == 3) ? me_vm_g6_sA_3 : me_vm_g6_sA_3_f)),
      .me_vm_g6_sA_4(((MUT == 3) ? me_vm_g6_sA_4 : me_vm_g6_sA_4_f)),
      .me_vm_g6_sA_5(((MUT == 3) ? me_vm_g6_sA_5 : me_vm_g6_sA_5_f)),
      .me_vm_g6_sA_6(((MUT == 3) ? me_vm_g6_sA_6 : me_vm_g6_sA_6_f)),
      .me_vm_g6_sA_7(((MUT == 3) ? me_vm_g6_sA_7 : me_vm_g6_sA_7_f)),
      .me_vm_g6_sA_8(((MUT == 3) ? me_vm_g6_sA_8 : me_vm_g6_sA_8_f)),
      .me_vm_g6_sA_9(((MUT == 3) ? me_vm_g6_sA_9 : me_vm_g6_sA_9_f)),
      .me_vm_g6_sB_0(((MUT == 3) ? me_vm_g6_sB_0 : me_vm_g6_sB_0_f)),
      .me_vm_g6_sB_1(((MUT == 3) ? me_vm_g6_sB_1 : me_vm_g6_sB_1_f)),
      .me_vm_g6_sB_2(((MUT == 3) ? me_vm_g6_sB_2 : me_vm_g6_sB_2_f)),
      .me_vm_g6_sB_3(((MUT == 3) ? me_vm_g6_sB_3 : me_vm_g6_sB_3_f)),
      .me_vm_g6_sB_4(((MUT == 3) ? me_vm_g6_sB_4 : me_vm_g6_sB_4_f)),
      .me_vm_g6_sB_5(((MUT == 3) ? me_vm_g6_sB_5 : me_vm_g6_sB_5_f)),
      .me_vm_g6_sB_6(((MUT == 3) ? me_vm_g6_sB_6 : me_vm_g6_sB_6_f)),
      .me_vm_g6_sB_7(((MUT == 3) ? me_vm_g6_sB_7 : me_vm_g6_sB_7_f)),
      .me_vm_g6_sB_8(((MUT == 3) ? me_vm_g6_sB_8 : me_vm_g6_sB_8_f)),
      .me_vm_g6_sB_9(((MUT == 3) ? me_vm_g6_sB_9 : me_vm_g6_sB_9_f)),
      .d_w(((MUT == 5) ? d_w : d_w_f)),
      .d_e(((MUT == 5) ? d_e : d_e_f)),
      .ro(ro_raw),
      .ovf(ovf_raw),
      .so_s0(so_s0_raw),
      .so_s1(so_s1_raw),
      .so_s2(so_s2_raw),
      .q_w(q_w_raw),
      .q_e(q_e_raw),
      .q_s(q_s_raw)
    );
endmodule
