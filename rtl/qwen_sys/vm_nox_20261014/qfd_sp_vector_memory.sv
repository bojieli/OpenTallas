`timescale 1ns/1ps
// Native STATIC compute-die VM binding (HANDOFF0ah). No credit ports,queues or runtime scheduling. This wrapper requires OT_QFD_VM_NOX and binds the real tiled VM.
// SA uses qfd_su_vm_pack. Row/ar/ME bundles are MSB-valid; payload data occupies the low bits.
// Sequencer addresses are full20-bit ROW addresses (no implicit base).
module qfd_sp_vector_memory #(
    parameter integer USE_MACRO=1, USE_LEAF_CLOCKS=1, OBS_MUT=0, MUT=0,
    // Q-VMWB 2026-10-15: PAR_RB=1 lands rb0/rb1/rb2 in the same edge on distinct banks (qfd_res_train_par calendar).
    parameter integer PAR_RB=0, PMUT=0,
    parameter integer NATIVE_BANKS=0   // 1 = native storage successors (qvm_bank_banked_native / qvm_su_bank_native)
)(
    input wire ck, rst_n,
    input wire ck_r0_0,
    input wire ck_r0_1,
    input wire ck_r0_2,
    input wire ck_r0_3,
    input wire ck_r0_4,
    input wire ck_r0_5,
    input wire ck_r0_6,
    input wire ck_r0_7,
    input wire ck_r0_8,
    input wire ck_r0_9,
    input wire ck_r0_10,
    input wire ck_r0_11,
    input wire ck_r0_12,
    input wire ck_r0_13,
    input wire ck_r0_14,
    input wire ck_r0_15,
    input wire ck_r0_16,
    input wire ck_r0_17,
    input wire ck_r0_18,
    input wire ck_r0_19,
    input wire ck_r0_20,
    input wire ck_r0_21,
    input wire ck_r0_22,
    input wire ck_r0_23,
    input wire ck_r0_24,
    input wire ck_r0_25,
    input wire ck_r0_26,
    input wire ck_r0_27,
    input wire ck_r0_28,
    input wire ck_r0_29,
    input wire ck_r0_30,
    input wire ck_r0_31,
    input wire ck_r0_32,
    input wire ck_r0_33,
    input wire ck_r0_34,
    input wire ck_r0_35,
    input wire ck_r0_36,
    input wire ck_r0_37,
    input wire ck_r0_38,
    input wire ck_r0_39,
    input wire ck_r0_40,
    input wire ck_r0_41,
    input wire ck_r0_42,
    input wire ck_r0_43,
    input wire ck_r0_44,
    input wire ck_r0_45,
    input wire ck_r0_46,
    input wire ck_r0_47,
    input wire ck_r0_48,
    input wire ck_r0_49,
    input wire ck_r0_50,
    input wire ck_r0_51,
    input wire ck_r0_52,
    input wire ck_r0_53,
    input wire ck_r0_54,
    input wire ck_r0_55,
    input wire ck_r1_0,
    input wire ck_r1_1,
    input wire ck_r1_2,
    input wire ck_r1_3,
    input wire ck_r1_4,
    input wire ck_r1_5,
    input wire ck_r1_6,
    input wire ck_r1_7,
    input wire ck_r1_8,
    input wire ck_r1_9,
    input wire ck_r1_10,
    input wire ck_r1_11,
    input wire ck_r1_12,
    input wire ck_r1_13,
    input wire ck_r1_14,
    input wire ck_r1_15,
    input wire ck_r1_16,
    input wire ck_r1_17,
    input wire ck_r1_18,
    input wire ck_r1_19,
    input wire ck_r1_20,
    input wire ck_r1_21,
    input wire ck_r1_22,
    input wire ck_r1_23,
    input wire ck_r1_24,
    input wire ck_r1_25,
    input wire ck_r1_26,
    input wire ck_r1_27,
    input wire ck_r1_28,
    input wire ck_r1_29,
    input wire ck_r1_30,
    input wire ck_r1_31,
    input wire ck_r1_32,
    input wire ck_r1_33,
    input wire ck_r1_34,
    input wire ck_r1_35,
    input wire ck_r1_36,
    input wire ck_r1_37,
    input wire ck_r1_38,
    input wire ck_r1_39,
    input wire ck_r1_40,
    input wire ck_r1_41,
    input wire ck_r1_42,
    input wire ck_r1_43,
    input wire ck_r1_44,
    input wire ck_r1_45,
    input wire ck_r1_46,
    input wire ck_r1_47,
    input wire ck_r1_48,
    input wire ck_r1_49,
    input wire ck_r1_50,
    input wire ck_r1_51,
    input wire ck_r1_52,
    input wire ck_r1_53,
    input wire ck_r1_54,
    input wire ck_r1_55,
    input wire ck_r2_0,
    input wire ck_r2_1,
    input wire ck_r2_2,
    input wire ck_r2_3,
    input wire ck_r2_4,
    input wire ck_r2_5,
    input wire ck_r2_6,
    input wire ck_r2_7,
    input wire ck_r2_8,
    input wire ck_r2_9,
    input wire ck_r2_10,
    input wire ck_r2_11,
    input wire ck_r2_12,
    input wire ck_r2_13,
    input wire ck_r2_14,
    input wire ck_r2_15,
    input wire ck_r2_16,
    input wire ck_r2_17,
    input wire ck_r2_18,
    input wire ck_r2_19,
    input wire ck_r2_20,
    input wire ck_r2_21,
    input wire ck_r2_22,
    input wire ck_r2_23,
    input wire ck_r2_24,
    input wire ck_r2_25,
    input wire ck_r2_26,
    input wire ck_r2_27,
    input wire ck_r2_28,
    input wire ck_r2_29,
    input wire ck_r2_30,
    input wire ck_r2_31,
    input wire ck_r2_32,
    input wire ck_r2_33,
    input wire ck_r2_34,
    input wire ck_r2_35,
    input wire ck_r2_36,
    input wire ck_r2_37,
    input wire ck_r2_38,
    input wire ck_r2_39,
    input wire ck_r2_40,
    input wire ck_r2_41,
    input wire ck_r2_42,
    input wire ck_r2_43,
    input wire ck_r2_44,
    input wire ck_r2_45,
    input wire ck_r2_46,
    input wire ck_r2_47,
    input wire ck_r2_48,
    input wire ck_r2_49,
    input wire ck_r2_50,
    input wire ck_r2_51,
    input wire ck_r2_52,
    input wire ck_r2_53,
    input wire ck_r2_54,
    input wire ck_r2_55,
    input wire ck_r3_0,
    input wire ck_r3_1,
    input wire ck_r3_2,
    input wire ck_r3_3,
    input wire ck_r3_4,
    input wire ck_r3_5,
    input wire ck_r3_6,
    input wire ck_r3_7,
    input wire ck_r3_8,
    input wire ck_r3_9,
    input wire ck_r3_10,
    input wire ck_r3_11,
    input wire ck_r3_12,
    input wire ck_r3_13,
    input wire ck_r3_14,
    input wire ck_r3_15,
    input wire ck_r3_16,
    input wire ck_r3_17,
    input wire ck_r3_18,
    input wire ck_r3_19,
    input wire ck_r3_20,
    input wire ck_r3_21,
    input wire ck_r3_22,
    input wire ck_r3_23,
    input wire ck_r3_24,
    input wire ck_r3_25,
    input wire ck_r3_26,
    input wire ck_r3_27,
    input wire ck_r3_28,
    input wire ck_r3_29,
    input wire ck_r3_30,
    input wire ck_r3_31,
    input wire ck_r3_32,
    input wire ck_r3_33,
    input wire ck_r3_34,
    input wire ck_r3_35,
    input wire ck_r3_36,
    input wire ck_r3_37,
    input wire ck_r3_38,
    input wire ck_r3_39,
    input wire ck_r3_40,
    input wire ck_r3_41,
    input wire ck_r3_42,
    input wire ck_r3_43,
    input wire ck_r3_44,
    input wire ck_r3_45,
    input wire ck_r3_46,
    input wire ck_r3_47,
    input wire ck_r3_48,
    input wire ck_r3_49,
    input wire ck_r3_50,
    input wire ck_r3_51,
    input wire ck_r3_52,
    input wire ck_r3_53,
    input wire ck_r3_54,
    input wire ck_r3_55,
    input wire ck_r4_0,
    input wire ck_r4_1,
    input wire ck_r4_2,
    input wire ck_r4_3,
    input wire ck_r4_4,
    input wire ck_r4_5,
    input wire ck_r4_6,
    input wire ck_r4_7,
    input wire ck_r4_8,
    input wire ck_r4_9,
    input wire ck_r4_10,
    input wire ck_r4_11,
    input wire ck_r4_12,
    input wire ck_r4_13,
    input wire ck_r4_14,
    input wire ck_r4_15,
    input wire ck_r4_16,
    input wire ck_r4_17,
    input wire ck_r4_18,
    input wire ck_r4_19,
    input wire ck_r4_20,
    input wire ck_r4_21,
    input wire ck_r4_22,
    input wire ck_r4_23,
    input wire ck_r4_24,
    input wire ck_r4_25,
    input wire ck_r4_26,
    input wire ck_r4_27,
    input wire ck_r4_28,
    input wire ck_r4_29,
    input wire ck_r4_30,
    input wire ck_r4_31,
    input wire ck_r4_32,
    input wire ck_r4_33,
    input wire ck_r4_34,
    input wire ck_r4_35,
    input wire ck_r4_36,
    input wire ck_r4_37,
    input wire ck_r4_38,
    input wire ck_r4_39,
    input wire ck_r4_40,
    input wire ck_r4_41,
    input wire ck_r4_42,
    input wire ck_r4_43,
    input wire ck_r4_44,
    input wire ck_r4_45,
    input wire ck_r4_46,
    input wire ck_r4_47,
    input wire ck_r4_48,
    input wire ck_r4_49,
    input wire ck_r4_50,
    input wire ck_r4_51,
    input wire ck_r4_52,
    input wire ck_r4_53,
    input wire ck_r4_54,
    input wire ck_r4_55,
    input wire ck_r5_0,
    input wire ck_r5_1,
    input wire ck_r5_2,
    input wire ck_r5_3,
    input wire ck_r5_4,
    input wire ck_r5_5,
    input wire ck_r5_6,
    input wire ck_r5_7,
    input wire ck_r5_8,
    input wire ck_r5_9,
    input wire ck_r5_10,
    input wire ck_r5_11,
    input wire ck_r5_12,
    input wire ck_r5_13,
    input wire ck_r5_14,
    input wire ck_r5_15,
    input wire ck_r5_16,
    input wire ck_r5_17,
    input wire ck_r5_18,
    input wire ck_r5_19,
    input wire ck_r5_20,
    input wire ck_r5_21,
    input wire ck_r5_22,
    input wire ck_r5_23,
    input wire ck_r5_24,
    input wire ck_r5_25,
    input wire ck_r5_26,
    input wire ck_r5_27,
    input wire ck_r5_28,
    input wire ck_r5_29,
    input wire ck_r5_30,
    input wire ck_r5_31,
    input wire ck_r5_32,
    input wire ck_r5_33,
    input wire ck_r5_34,
    input wire ck_r5_35,
    input wire ck_r5_36,
    input wire ck_r5_37,
    input wire ck_r5_38,
    input wire ck_r5_39,
    input wire ck_r5_40,
    input wire ck_r5_41,
    input wire ck_r5_42,
    input wire ck_r5_43,
    input wire ck_r5_44,
    input wire ck_r5_45,
    input wire ck_r5_46,
    input wire ck_r5_47,
    input wire ck_r5_48,
    input wire ck_r5_49,
    input wire ck_r5_50,
    input wire ck_r5_51,
    input wire ck_r5_52,
    input wire ck_r5_53,
    input wire ck_r5_54,
    input wire ck_r5_55,
    input wire ck_r6_0,
    input wire ck_r6_1,
    input wire ck_r6_2,
    input wire ck_r6_3,
    input wire ck_r6_4,
    input wire ck_r6_5,
    input wire ck_r6_6,
    input wire ck_r6_7,
    input wire ck_r6_8,
    input wire ck_r6_9,
    input wire ck_r6_10,
    input wire ck_r6_11,
    input wire ck_r6_12,
    input wire ck_r6_13,
    input wire ck_r6_14,
    input wire ck_r6_15,
    input wire ck_r6_16,
    input wire ck_r6_17,
    input wire ck_r6_18,
    input wire ck_r6_19,
    input wire ck_r6_20,
    input wire ck_r6_21,
    input wire ck_r6_22,
    input wire ck_r6_23,
    input wire ck_r6_24,
    input wire ck_r6_25,
    input wire ck_r6_26,
    input wire ck_r6_27,
    input wire ck_r6_28,
    input wire ck_r6_29,
    input wire ck_r6_30,
    input wire ck_r6_31,
    input wire ck_r6_32,
    input wire ck_r6_33,
    input wire ck_r6_34,
    input wire ck_r6_35,
    input wire ck_r6_36,
    input wire ck_r6_37,
    input wire ck_r6_38,
    input wire ck_r6_39,
    input wire ck_r6_40,
    input wire ck_r6_41,
    input wire ck_r6_42,
    input wire ck_r6_43,
    input wire ck_r6_44,
    input wire ck_r6_45,
    input wire ck_r6_46,
    input wire ck_r6_47,
    input wire ck_r6_48,
    input wire ck_r6_49,
    input wire ck_r6_50,
    input wire ck_r6_51,
    input wire ck_r6_52,
    input wire ck_r6_53,
    input wire ck_r6_54,
    input wire ck_r6_55,
    input wire ck_r7_0,
    input wire ck_r7_1,
    input wire ck_r7_2,
    input wire ck_r7_3,
    input wire ck_r7_4,
    input wire ck_r7_5,
    input wire ck_r7_6,
    input wire ck_r7_7,
    input wire ck_r7_8,
    input wire ck_r7_9,
    input wire ck_r7_10,
    input wire ck_r7_11,
    input wire ck_r7_12,
    input wire ck_r7_13,
    input wire ck_r7_14,
    input wire ck_r7_15,
    input wire ck_r7_16,
    input wire ck_r7_17,
    input wire ck_r7_18,
    input wire ck_r7_19,
    input wire ck_r7_20,
    input wire ck_r7_21,
    input wire ck_r7_22,
    input wire ck_r7_23,
    input wire ck_r7_24,
    input wire ck_r7_25,
    input wire ck_r7_26,
    input wire ck_r7_27,
    input wire ck_r7_28,
    input wire ck_r7_29,
    input wire ck_r7_30,
    input wire ck_r7_31,
    input wire ck_r7_32,
    input wire ck_r7_33,
    input wire ck_r7_34,
    input wire ck_r7_35,
    input wire ck_r7_36,
    input wire ck_r7_37,
    input wire ck_r7_38,
    input wire ck_r7_39,
    input wire ck_r7_40,
    input wire ck_r7_41,
    input wire ck_r7_42,
    input wire ck_r7_43,
    input wire ck_r7_44,
    input wire ck_r7_45,
    input wire ck_r7_46,
    input wire ck_r7_47,
    input wire ck_r7_48,
    input wire ck_r7_49,
    input wire ck_r7_50,
    input wire ck_r7_51,
    input wire ck_r7_52,
    input wire ck_r7_53,
    input wire ck_r7_54,
    input wire ck_r7_55,
    input wire ck_r7_56,
    input wire ck_r7_57,
    input wire ck_r7_58,
    input wire ck_r7_59,
    input wire ck_r7_60,
    input wire ck_r7_61,
    input wire ck_r7_62,

    input wire ck_r3_56,
    input wire ck_r3_57,
    input wire ck_r3_58,
    input wire ck_r3_59,
    input wire ck_r3_60,
    input wire ck_r3_61,
    input wire ck_r3_62,
    input wire ck_r3_63,
    input wire ck_r4_56,
    input wire ck_r4_57,
    input wire ck_r4_58,
    input wire ck_r4_59,
    input wire ck_r4_60,
    input wire ck_r4_61,
    input wire ck_r4_62,
    input wire ck_r4_63,
    input wire ck_r5_56,
    input wire ck_r5_57,
    input wire ck_r5_58,
    input wire ck_r5_59,
    input wire ck_r5_60,
    input wire ck_r5_61,
    input wire ck_r5_62,
    input wire ck_r5_63,
    input wire ck_r6_56,
    input wire ck_r6_57,
    input wire ck_r6_58,
    input wire ck_r6_59,
    input wire ck_r6_60,
    input wire ck_r6_61,
    input wire ck_r6_62,
    input wire ck_r6_63,
    input wire [2366:0] sa, output wire [6143:0] sq,
    input wire [552:0] mx, input wire [550:0] rb0,rb1,rb2,
    
    output wire [15:0] ld, output wire mo, input wire mee,
    input wire [20:0] svr, output wire svr_rdy, output wire [511:0] svq, output wire svq_v,
    input wire [532:0] svw,
    input wire [519:0] ar, output reg [552:0] xaw,
    input wire q_epoch, q_start, output wire q_committed,
    output wire [523:0] q, output wire q_done,
    output wire [38:0] write_commit_v,
    output wire [311:0] write_commit_line,
    output wire [623:0] write_commit_mask,
    output wire fault
);
    wire [447:0] lc;
    assign lc[0]=ck_r0_0;
    assign lc[1]=ck_r0_1;
    assign lc[2]=ck_r0_2;
    assign lc[3]=ck_r0_3;
    assign lc[4]=ck_r0_4;
    assign lc[5]=ck_r0_5;
    assign lc[6]=ck_r0_6;
    assign lc[7]=ck_r0_7;
    assign lc[8]=ck_r0_8;
    assign lc[9]=ck_r0_9;
    assign lc[10]=ck_r0_10;
    assign lc[11]=ck_r0_11;
    assign lc[12]=ck_r0_12;
    assign lc[13]=ck_r0_13;
    assign lc[14]=ck_r0_14;
    assign lc[15]=ck_r0_15;
    assign lc[16]=ck_r0_16;
    assign lc[17]=ck_r0_17;
    assign lc[18]=ck_r0_18;
    assign lc[19]=ck_r0_19;
    assign lc[20]=ck_r0_20;
    assign lc[21]=ck_r0_21;
    assign lc[22]=ck_r0_22;
    assign lc[23]=ck_r0_23;
    assign lc[24]=ck_r0_24;
    assign lc[25]=ck_r0_25;
    assign lc[26]=ck_r0_26;
    assign lc[27]=ck_r0_27;
    assign lc[28]=ck_r0_28;
    assign lc[29]=ck_r0_29;
    assign lc[30]=ck_r0_30;
    assign lc[31]=ck_r0_31;
    assign lc[32]=ck_r0_32;
    assign lc[33]=ck_r0_33;
    assign lc[34]=ck_r0_34;
    assign lc[35]=ck_r0_35;
    assign lc[36]=ck_r0_36;
    assign lc[37]=ck_r0_37;
    assign lc[38]=ck_r0_38;
    assign lc[39]=ck_r0_39;
    assign lc[40]=ck_r0_40;
    assign lc[41]=ck_r0_41;
    assign lc[42]=ck_r0_42;
    assign lc[43]=ck_r0_43;
    assign lc[44]=ck_r0_44;
    assign lc[45]=ck_r0_45;
    assign lc[46]=ck_r0_46;
    assign lc[47]=ck_r0_47;
    assign lc[48]=ck_r0_48;
    assign lc[49]=ck_r0_49;
    assign lc[50]=ck_r0_50;
    assign lc[51]=ck_r0_51;
    assign lc[52]=ck_r0_52;
    assign lc[53]=ck_r0_53;
    assign lc[54]=ck_r0_54;
    assign lc[55]=ck_r0_55;
    assign lc[56]=ck_r1_0;
    assign lc[57]=ck_r1_1;
    assign lc[58]=ck_r1_2;
    assign lc[59]=ck_r1_3;
    assign lc[60]=ck_r1_4;
    assign lc[61]=ck_r1_5;
    assign lc[62]=ck_r1_6;
    assign lc[63]=ck_r1_7;
    assign lc[64]=ck_r1_8;
    assign lc[65]=ck_r1_9;
    assign lc[66]=ck_r1_10;
    assign lc[67]=ck_r1_11;
    assign lc[68]=ck_r1_12;
    assign lc[69]=ck_r1_13;
    assign lc[70]=ck_r1_14;
    assign lc[71]=ck_r1_15;
    assign lc[72]=ck_r1_16;
    assign lc[73]=ck_r1_17;
    assign lc[74]=ck_r1_18;
    assign lc[75]=ck_r1_19;
    assign lc[76]=ck_r1_20;
    assign lc[77]=ck_r1_21;
    assign lc[78]=ck_r1_22;
    assign lc[79]=ck_r1_23;
    assign lc[80]=ck_r1_24;
    assign lc[81]=ck_r1_25;
    assign lc[82]=ck_r1_26;
    assign lc[83]=ck_r1_27;
    assign lc[84]=ck_r1_28;
    assign lc[85]=ck_r1_29;
    assign lc[86]=ck_r1_30;
    assign lc[87]=ck_r1_31;
    assign lc[88]=ck_r1_32;
    assign lc[89]=ck_r1_33;
    assign lc[90]=ck_r1_34;
    assign lc[91]=ck_r1_35;
    assign lc[92]=ck_r1_36;
    assign lc[93]=ck_r1_37;
    assign lc[94]=ck_r1_38;
    assign lc[95]=ck_r1_39;
    assign lc[96]=ck_r1_40;
    assign lc[97]=ck_r1_41;
    assign lc[98]=ck_r1_42;
    assign lc[99]=ck_r1_43;
    assign lc[100]=ck_r1_44;
    assign lc[101]=ck_r1_45;
    assign lc[102]=ck_r1_46;
    assign lc[103]=ck_r1_47;
    assign lc[104]=ck_r1_48;
    assign lc[105]=ck_r1_49;
    assign lc[106]=ck_r1_50;
    assign lc[107]=ck_r1_51;
    assign lc[108]=ck_r1_52;
    assign lc[109]=ck_r1_53;
    assign lc[110]=ck_r1_54;
    assign lc[111]=ck_r1_55;
    assign lc[112]=ck_r2_0;
    assign lc[113]=ck_r2_1;
    assign lc[114]=ck_r2_2;
    assign lc[115]=ck_r2_3;
    assign lc[116]=ck_r2_4;
    assign lc[117]=ck_r2_5;
    assign lc[118]=ck_r2_6;
    assign lc[119]=ck_r2_7;
    assign lc[120]=ck_r2_8;
    assign lc[121]=ck_r2_9;
    assign lc[122]=ck_r2_10;
    assign lc[123]=ck_r2_11;
    assign lc[124]=ck_r2_12;
    assign lc[125]=ck_r2_13;
    assign lc[126]=ck_r2_14;
    assign lc[127]=ck_r2_15;
    assign lc[128]=ck_r2_16;
    assign lc[129]=ck_r2_17;
    assign lc[130]=ck_r2_18;
    assign lc[131]=ck_r2_19;
    assign lc[132]=ck_r2_20;
    assign lc[133]=ck_r2_21;
    assign lc[134]=ck_r2_22;
    assign lc[135]=ck_r2_23;
    assign lc[136]=ck_r2_24;
    assign lc[137]=ck_r2_25;
    assign lc[138]=ck_r2_26;
    assign lc[139]=ck_r2_27;
    assign lc[140]=ck_r2_28;
    assign lc[141]=ck_r2_29;
    assign lc[142]=ck_r2_30;
    assign lc[143]=ck_r2_31;
    assign lc[144]=ck_r2_32;
    assign lc[145]=ck_r2_33;
    assign lc[146]=ck_r2_34;
    assign lc[147]=ck_r2_35;
    assign lc[148]=ck_r2_36;
    assign lc[149]=ck_r2_37;
    assign lc[150]=ck_r2_38;
    assign lc[151]=ck_r2_39;
    assign lc[152]=ck_r2_40;
    assign lc[153]=ck_r2_41;
    assign lc[154]=ck_r2_42;
    assign lc[155]=ck_r2_43;
    assign lc[156]=ck_r2_44;
    assign lc[157]=ck_r2_45;
    assign lc[158]=ck_r2_46;
    assign lc[159]=ck_r2_47;
    assign lc[160]=ck_r2_48;
    assign lc[161]=ck_r2_49;
    assign lc[162]=ck_r2_50;
    assign lc[163]=ck_r2_51;
    assign lc[164]=ck_r2_52;
    assign lc[165]=ck_r2_53;
    assign lc[166]=ck_r2_54;
    assign lc[167]=ck_r2_55;
    assign lc[168]=ck_r3_0;
    assign lc[169]=ck_r3_1;
    assign lc[170]=ck_r3_2;
    assign lc[171]=ck_r3_3;
    assign lc[172]=ck_r3_4;
    assign lc[173]=ck_r3_5;
    assign lc[174]=ck_r3_6;
    assign lc[175]=ck_r3_7;
    assign lc[176]=ck_r3_8;
    assign lc[177]=ck_r3_9;
    assign lc[178]=ck_r3_10;
    assign lc[179]=ck_r3_11;
    assign lc[180]=ck_r3_12;
    assign lc[181]=ck_r3_13;
    assign lc[182]=ck_r3_14;
    assign lc[183]=ck_r3_15;
    assign lc[184]=ck_r3_16;
    assign lc[185]=ck_r3_17;
    assign lc[186]=ck_r3_18;
    assign lc[187]=ck_r3_19;
    assign lc[188]=ck_r3_20;
    assign lc[189]=ck_r3_21;
    assign lc[190]=ck_r3_22;
    assign lc[191]=ck_r3_23;
    assign lc[192]=ck_r3_24;
    assign lc[193]=ck_r3_25;
    assign lc[194]=ck_r3_26;
    assign lc[195]=ck_r3_27;
    assign lc[196]=ck_r3_28;
    assign lc[197]=ck_r3_29;
    assign lc[198]=ck_r3_30;
    assign lc[199]=ck_r3_31;
    assign lc[200]=ck_r3_32;
    assign lc[201]=ck_r3_33;
    assign lc[202]=ck_r3_34;
    assign lc[203]=ck_r3_35;
    assign lc[204]=ck_r3_36;
    assign lc[205]=ck_r3_37;
    assign lc[206]=ck_r3_38;
    assign lc[207]=ck_r3_39;
    assign lc[208]=ck_r3_40;
    assign lc[209]=ck_r3_41;
    assign lc[210]=ck_r3_42;
    assign lc[211]=ck_r3_43;
    assign lc[212]=ck_r3_44;
    assign lc[213]=ck_r3_45;
    assign lc[214]=ck_r3_46;
    assign lc[215]=ck_r3_47;
    assign lc[216]=ck_r3_48;
    assign lc[217]=ck_r3_49;
    assign lc[218]=ck_r3_50;
    assign lc[219]=ck_r3_51;
    assign lc[220]=ck_r3_52;
    assign lc[221]=ck_r3_53;
    assign lc[222]=ck_r3_54;
    assign lc[223]=ck_r3_55;
    assign lc[224]=ck_r4_0;
    assign lc[225]=ck_r4_1;
    assign lc[226]=ck_r4_2;
    assign lc[227]=ck_r4_3;
    assign lc[228]=ck_r4_4;
    assign lc[229]=ck_r4_5;
    assign lc[230]=ck_r4_6;
    assign lc[231]=ck_r4_7;
    assign lc[232]=ck_r4_8;
    assign lc[233]=ck_r4_9;
    assign lc[234]=ck_r4_10;
    assign lc[235]=ck_r4_11;
    assign lc[236]=ck_r4_12;
    assign lc[237]=ck_r4_13;
    assign lc[238]=ck_r4_14;
    assign lc[239]=ck_r4_15;
    assign lc[240]=ck_r4_16;
    assign lc[241]=ck_r4_17;
    assign lc[242]=ck_r4_18;
    assign lc[243]=ck_r4_19;
    assign lc[244]=ck_r4_20;
    assign lc[245]=ck_r4_21;
    assign lc[246]=ck_r4_22;
    assign lc[247]=ck_r4_23;
    assign lc[248]=ck_r4_24;
    assign lc[249]=ck_r4_25;
    assign lc[250]=ck_r4_26;
    assign lc[251]=ck_r4_27;
    assign lc[252]=ck_r4_28;
    assign lc[253]=ck_r4_29;
    assign lc[254]=ck_r4_30;
    assign lc[255]=ck_r4_31;
    assign lc[256]=ck_r4_32;
    assign lc[257]=ck_r4_33;
    assign lc[258]=ck_r4_34;
    assign lc[259]=ck_r4_35;
    assign lc[260]=ck_r4_36;
    assign lc[261]=ck_r4_37;
    assign lc[262]=ck_r4_38;
    assign lc[263]=ck_r4_39;
    assign lc[264]=ck_r4_40;
    assign lc[265]=ck_r4_41;
    assign lc[266]=ck_r4_42;
    assign lc[267]=ck_r4_43;
    assign lc[268]=ck_r4_44;
    assign lc[269]=ck_r4_45;
    assign lc[270]=ck_r4_46;
    assign lc[271]=ck_r4_47;
    assign lc[272]=ck_r4_48;
    assign lc[273]=ck_r4_49;
    assign lc[274]=ck_r4_50;
    assign lc[275]=ck_r4_51;
    assign lc[276]=ck_r4_52;
    assign lc[277]=ck_r4_53;
    assign lc[278]=ck_r4_54;
    assign lc[279]=ck_r4_55;
    assign lc[280]=ck_r5_0;
    assign lc[281]=ck_r5_1;
    assign lc[282]=ck_r5_2;
    assign lc[283]=ck_r5_3;
    assign lc[284]=ck_r5_4;
    assign lc[285]=ck_r5_5;
    assign lc[286]=ck_r5_6;
    assign lc[287]=ck_r5_7;
    assign lc[288]=ck_r5_8;
    assign lc[289]=ck_r5_9;
    assign lc[290]=ck_r5_10;
    assign lc[291]=ck_r5_11;
    assign lc[292]=ck_r5_12;
    assign lc[293]=ck_r5_13;
    assign lc[294]=ck_r5_14;
    assign lc[295]=ck_r5_15;
    assign lc[296]=ck_r5_16;
    assign lc[297]=ck_r5_17;
    assign lc[298]=ck_r5_18;
    assign lc[299]=ck_r5_19;
    assign lc[300]=ck_r5_20;
    assign lc[301]=ck_r5_21;
    assign lc[302]=ck_r5_22;
    assign lc[303]=ck_r5_23;
    assign lc[304]=ck_r5_24;
    assign lc[305]=ck_r5_25;
    assign lc[306]=ck_r5_26;
    assign lc[307]=ck_r5_27;
    assign lc[308]=ck_r5_28;
    assign lc[309]=ck_r5_29;
    assign lc[310]=ck_r5_30;
    assign lc[311]=ck_r5_31;
    assign lc[312]=ck_r5_32;
    assign lc[313]=ck_r5_33;
    assign lc[314]=ck_r5_34;
    assign lc[315]=ck_r5_35;
    assign lc[316]=ck_r5_36;
    assign lc[317]=ck_r5_37;
    assign lc[318]=ck_r5_38;
    assign lc[319]=ck_r5_39;
    assign lc[320]=ck_r5_40;
    assign lc[321]=ck_r5_41;
    assign lc[322]=ck_r5_42;
    assign lc[323]=ck_r5_43;
    assign lc[324]=ck_r5_44;
    assign lc[325]=ck_r5_45;
    assign lc[326]=ck_r5_46;
    assign lc[327]=ck_r5_47;
    assign lc[328]=ck_r5_48;
    assign lc[329]=ck_r5_49;
    assign lc[330]=ck_r5_50;
    assign lc[331]=ck_r5_51;
    assign lc[332]=ck_r5_52;
    assign lc[333]=ck_r5_53;
    assign lc[334]=ck_r5_54;
    assign lc[335]=ck_r5_55;
    assign lc[336]=ck_r6_0;
    assign lc[337]=ck_r6_1;
    assign lc[338]=ck_r6_2;
    assign lc[339]=ck_r6_3;
    assign lc[340]=ck_r6_4;
    assign lc[341]=ck_r6_5;
    assign lc[342]=ck_r6_6;
    assign lc[343]=ck_r6_7;
    assign lc[344]=ck_r6_8;
    assign lc[345]=ck_r6_9;
    assign lc[346]=ck_r6_10;
    assign lc[347]=ck_r6_11;
    assign lc[348]=ck_r6_12;
    assign lc[349]=ck_r6_13;
    assign lc[350]=ck_r6_14;
    assign lc[351]=ck_r6_15;
    assign lc[352]=ck_r6_16;
    assign lc[353]=ck_r6_17;
    assign lc[354]=ck_r6_18;
    assign lc[355]=ck_r6_19;
    assign lc[356]=ck_r6_20;
    assign lc[357]=ck_r6_21;
    assign lc[358]=ck_r6_22;
    assign lc[359]=ck_r6_23;
    assign lc[360]=ck_r6_24;
    assign lc[361]=ck_r6_25;
    assign lc[362]=ck_r6_26;
    assign lc[363]=ck_r6_27;
    assign lc[364]=ck_r6_28;
    assign lc[365]=ck_r6_29;
    assign lc[366]=ck_r6_30;
    assign lc[367]=ck_r6_31;
    assign lc[368]=ck_r6_32;
    assign lc[369]=ck_r6_33;
    assign lc[370]=ck_r6_34;
    assign lc[371]=ck_r6_35;
    assign lc[372]=ck_r6_36;
    assign lc[373]=ck_r6_37;
    assign lc[374]=ck_r6_38;
    assign lc[375]=ck_r6_39;
    assign lc[376]=ck_r6_40;
    assign lc[377]=ck_r6_41;
    assign lc[378]=ck_r6_42;
    assign lc[379]=ck_r6_43;
    assign lc[380]=ck_r6_44;
    assign lc[381]=ck_r6_45;
    assign lc[382]=ck_r6_46;
    assign lc[383]=ck_r6_47;
    assign lc[384]=ck_r6_48;
    assign lc[385]=ck_r6_49;
    assign lc[386]=ck_r6_50;
    assign lc[387]=ck_r6_51;
    assign lc[388]=ck_r6_52;
    assign lc[389]=ck_r6_53;
    assign lc[390]=ck_r6_54;
    assign lc[391]=ck_r6_55;
    assign lc[392]=ck_r7_0;
    assign lc[393]=ck_r7_1;
    assign lc[394]=ck_r7_2;
    assign lc[395]=ck_r7_3;
    assign lc[396]=ck_r7_4;
    assign lc[397]=ck_r7_5;
    assign lc[398]=ck_r7_6;
    assign lc[399]=ck_r7_7;
    assign lc[400]=ck_r7_8;
    assign lc[401]=ck_r7_9;
    assign lc[402]=ck_r7_10;
    assign lc[403]=ck_r7_11;
    assign lc[404]=ck_r7_12;
    assign lc[405]=ck_r7_13;
    assign lc[406]=ck_r7_14;
    assign lc[407]=ck_r7_15;
    assign lc[408]=ck_r7_16;
    assign lc[409]=ck_r7_17;
    assign lc[410]=ck_r7_18;
    assign lc[411]=ck_r7_19;
    assign lc[412]=ck_r7_20;
    assign lc[413]=ck_r7_21;
    assign lc[414]=ck_r7_22;
    assign lc[415]=ck_r7_23;
    assign lc[416]=ck_r7_24;
    assign lc[417]=ck_r7_25;
    assign lc[418]=ck_r7_26;
    assign lc[419]=ck_r7_27;
    assign lc[420]=ck_r7_28;
    assign lc[421]=ck_r7_29;
    assign lc[422]=ck_r7_30;
    assign lc[423]=ck_r7_31;
    assign lc[424]=ck_r7_32;
    assign lc[425]=ck_r7_33;
    assign lc[426]=ck_r7_34;
    assign lc[427]=ck_r7_35;
    assign lc[428]=ck_r7_36;
    assign lc[429]=ck_r7_37;
    assign lc[430]=ck_r7_38;
    assign lc[431]=ck_r7_39;
    assign lc[432]=ck_r7_40;
    assign lc[433]=ck_r7_41;
    assign lc[434]=ck_r7_42;
    assign lc[435]=ck_r7_43;
    assign lc[436]=ck_r7_44;
    assign lc[437]=ck_r7_45;
    assign lc[438]=ck_r7_46;
    assign lc[439]=ck_r7_47;
    assign lc[440]=ck_r7_48;
    assign lc[441]=ck_r7_49;
    assign lc[442]=ck_r7_50;
    assign lc[443]=ck_r7_51;
    assign lc[444]=ck_r7_52;
    assign lc[445]=ck_r7_53;
    assign lc[446]=ck_r7_54;
    assign lc[447]=ck_r7_55;
    wire [63:0] oc;
    assign oc[0]=1'b0; // No Q observer in this bank group.
    assign oc[1]=1'b0; // No Q observer in this bank group.
    assign oc[2]=1'b0; // No Q observer in this bank group.
    assign oc[3]=1'b0; // No Q observer in this bank group.
    assign oc[4]=1'b0; // No Q observer in this bank group.
    assign oc[5]=1'b0; // No Q observer in this bank group.
    assign oc[6]=1'b0; // No Q observer in this bank group.
    assign oc[7]=1'b0; // No Q observer in this bank group.
    assign oc[8]=1'b0; // No Q observer in this bank group.
    assign oc[9]=1'b0; // No Q observer in this bank group.
    assign oc[10]=1'b0; // No Q observer in this bank group.
    assign oc[11]=1'b0; // No Q observer in this bank group.
    assign oc[12]=1'b0; // No Q observer in this bank group.
    assign oc[13]=1'b0; // No Q observer in this bank group.
    assign oc[14]=1'b0; // No Q observer in this bank group.
    assign oc[15]=1'b0; // No Q observer in this bank group.
    assign oc[16]=1'b0; // No Q observer in this bank group.
    assign oc[17]=1'b0; // No Q observer in this bank group.
    assign oc[18]=1'b0; // No Q observer in this bank group.
    assign oc[19]=1'b0; // No Q observer in this bank group.
    assign oc[20]=1'b0; // No Q observer in this bank group.
    assign oc[21]=1'b0; // No Q observer in this bank group.
    assign oc[22]=1'b0; // No Q observer in this bank group.
    assign oc[23]=1'b0; // No Q observer in this bank group.
    assign oc[24]=ck_r3_56;
    assign oc[25]=ck_r3_57;
    assign oc[26]=ck_r3_58;
    assign oc[27]=ck_r3_59;
    assign oc[28]=ck_r3_60;
    assign oc[29]=ck_r3_61;
    assign oc[30]=ck_r3_62;
    assign oc[31]=ck_r3_63;
    assign oc[32]=ck_r4_56;
    assign oc[33]=ck_r4_57;
    assign oc[34]=ck_r4_58;
    assign oc[35]=ck_r4_59;
    assign oc[36]=ck_r4_60;
    assign oc[37]=ck_r4_61;
    assign oc[38]=ck_r4_62;
    assign oc[39]=ck_r4_63;
    assign oc[40]=ck_r5_56;
    assign oc[41]=ck_r5_57;
    assign oc[42]=ck_r5_58;
    assign oc[43]=ck_r5_59;
    assign oc[44]=ck_r5_60;
    assign oc[45]=ck_r5_61;
    assign oc[46]=ck_r5_62;
    assign oc[47]=ck_r5_63;
    assign oc[48]=ck_r6_56;
    assign oc[49]=ck_r6_57;
    assign oc[50]=ck_r6_58;
    assign oc[51]=ck_r6_59;
    assign oc[52]=ck_r6_60;
    assign oc[53]=ck_r6_61;
    assign oc[54]=ck_r6_62;
    assign oc[55]=ck_r6_63;
    assign oc[56]=ck_r7_56;
    assign oc[57]=ck_r7_57;
    assign oc[58]=ck_r7_58;
    assign oc[59]=ck_r7_59;
    assign oc[60]=ck_r7_60;
    assign oc[61]=ck_r7_61;
    assign oc[62]=ck_r7_62;
    assign oc[63]=1'b0; // No Q observer in this bank group.
    wire [2:0] sre0,sre1;
    wire [71:0] sa0,sa1;
    genvar s;
    generate for(s=0;s<3;s=s+1) begin : g_su_desc
        assign sre0[s]=sa[50*s+48]; assign sre1[s]=sa[50*s+49];
        assign sa0[24*s+:24]=sa[50*s+:24]; assign sa1[24*s+:24]=sa[50*s+24+:24];
    end endgenerate
    localparam integer WR=150, RED=2310;
    wire [63:0] swmask=sa[2246+:64];
    wire [23:0] swa0=sa[2198+:24],swa1=sa[2222+:24];
    wire [2047:0] swdata=sa[150+:2048];
    wire qr_v,qr_rsp,qvm_v,qvm_ready,q_window;
    wire [19:0] qr_row;
    wire [511:0] vmq,commit_mask;
    wire [63:0] raw_commit_v; wire [511:0] raw_commit_line; wire [1023:0] raw_commit_mask;
    assign write_commit_v=raw_commit_v[24+:39];
    assign write_commit_line=raw_commit_line[24*8+:39*8];
    assign write_commit_mask=raw_commit_mask[24*16+:39*16];
    wire qfault,w_fault,w_hazard;
    // Q owns its compiler-reserved window. Sequencer requests in that window are faults,never demand-arbitrated.
    assign qvm_v=q_window ? qr_v : svr[20];
    wire [19:0] qvm_row=q_window ? qr_row : svr[19:0];
    assign svr_rdy=qvm_ready; // Observation/assertion pin,not production issue control.
    assign svq=vmq;assign svq_v=qr_rsp && !q_window;
    reg slot_fault;
    always @(posedge ck or negedge rst_n)
        if(!rst_n)slot_fault<=0;
        else if((q_window && svr[20]) || (qvm_v && !qvm_ready))slot_fault<=1;
    // The native TP8 head has g=0. g=1 is invalid; never invent a group offset.
    wire [19:0] ar_row=20'd3167 + ar[512+:6];
    wire ar_valid=ar[519] & ~ar[518] & (ar[512+:6]<32);
    always @(posedge ck or negedge rst_n)
        if(!rst_n) xaw<=0;
        else xaw<={ar[511:0],16'hffff,{ar_row,4'b0},ar_valid};
    reg ar_bad;
    always @(posedge ck or negedge rst_n)
        if(!rst_n) ar_bad<=0;
        else if(ar[519] && !ar_valid) ar_bad<=1;
    ot_qfd_vm_q_export_fixed u_q (
        .clk(ck),.rst_n(rst_n),.epoch_begin(q_epoch),
        .commit_mask(OBS_MUT ? (commit_mask & ~(512'd1<<511)) : commit_mask),
        .start_v(q_start),.qr_committed(q_committed),.window_active(q_window),
        .read_v(qr_v),.read_row(qr_row),.rsp_v(qr_rsp && q_window),.rsp_data(vmq),
        .q(q),.emitted_done(q_done),.fault(qfault));
    ot_qfd_sp_vector_memory_bv #(.USE_MACRO(USE_MACRO),.USE_LEAF_CLOCKS(USE_LEAF_CLOCKS),
        .USE_OBSERVER_CLOCKS(1),.NRB(64),.NB(3),.SQD(1),.STATIC_SCHEDULE(1),.MEE(1),.VMT(1),.RO(1),.MUT(MUT),.PAR_RB(PAR_RB),.PMUT(PMUT),.NATIVE_BANKS(NATIVE_BANKS)) u_vm (
        .clk(ck),.leaf_ck(lc),.observer_ck(oc),.rst_n(rst_n),.me_en(mee),.me_en_e(mee),
        .s_re0(sre0),.s_re1(sre1),.s_a0(sa0),.s_a1(sa1),.s_q(sq),
        .sw_mask(swmask),.sw_a0(swa0),.sw_a1(swa1),.sw_data(swdata),
        .rd_v(sa[2366]),.rd_addr(sa[2342+:24]),.rd_data(sa[2310+:32]),
        .w_v(svw[532]),.w_row(svw[512+:20]),.w_mask(16'hffff),.w_data(svw[0+:512]),
        .r_v(qvm_v),.r_rdy(qvm_ready),.r_row(qvm_row),.r_qv(qr_rsp),.r_q(vmq),
        .mx_we(mx[552]),.mx_addr(mx[512+:24]),.mx_mask(mx[536+:16]),.mx_data(mx[0+:512]),
        .aw_v(ar_valid),.aw_row(ar_row),.aw_data(ar[511:0]),.aw_cr(),
        .rb_v({rb2[550],rb1[550],rb0[550]}),.rb_end({rb2[549],rb1[549],rb0[549]}),.rb_nul({rb2[548],rb1[548],rb0[548]}),
        .rb_row({rb2[528+:20],rb1[528+:20],rb0[528+:20]}),.rb_mask({rb2[512+:16],rb1[512+:16],rb0[512+:16]}),
        .rb_data({rb2[0+:512],rb1[0+:512],rb0[0+:512]}),.rb_cr(),.rb_ok(3'b0),
        .me_ok(),.land_cnt(ld),.w_fault(w_fault),.w_hazard(w_hazard),.qr_commit_mask(commit_mask),
        .write_commit_v(raw_commit_v),.write_commit_line(raw_commit_line),.write_commit_mask(raw_commit_mask));
    assign fault=qfault | w_fault | w_hazard | ar_bad | slot_fault;
    assign mo=~fault;
endmodule
