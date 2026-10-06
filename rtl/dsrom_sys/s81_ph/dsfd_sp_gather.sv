`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// dsfd_sp_gather -- S81 die view top (CLAUDE S81-PH contract results/rtl/s81_ph_20261006/gather/contract.json).
// GENERATED lane table (tools/dsrom_s81_fulldie.py r9m215 _multi_nets: lane j of trunk r<half><tier> = the j-th
// column to join = frame order[j]); frame index = return region / root index.  Ports: the generator's
// (ck, rst, rE*/rW*, f_vm) plus the contract's ckv/rsv (serial clock/reset of the f_vm crossing) and t_capture
// widened to the per-root row lanes (generator change G1/G2 in the contract).
// Every die input is captured in a flop at the pin; every die output is launched from a flop.
// ---------------------------------------------------------------------------------------------------------------
module dsfd_sp_gather #(parameter integer ROOTD = 128) (
    input wire [0:0] ck,
    input wire [0:0] rst,
    input wire [0:0] ckv,
    input wire [0:0] rsv,
    input wire [511:0] f_vm,
    output wire [6946:0] t_capture,
    input wire [691:0] rW0,
    input wire [760:0] rW1,
    input wire [760:0] rW2,
    input wire [760:0] rW3,
    input wire [760:0] rW4,
    input wire [691:0] rW5,
    input wire [691:0] rE0,
    input wire [760:0] rE1,
    input wire [760:0] rE2,
    input wire [760:0] rE3,
    input wire [760:0] rE4,
    input wire [691:0] rE5
);
    localparam integer NR = 128;
    // ---- resets: 2-flop synchronisers per domain
    reg [1:0] rs_q, rv_q;
    always @(posedge ck[0] or negedge rst[0]) if (!rst[0]) rs_q <= 2'b00; else rs_q <= {rs_q[0], 1'b1};
    always @(posedge ckv[0] or negedge rsv[0]) if (!rsv[0]) rv_q <= 2'b00; else rv_q <= {rv_q[0], 1'b1};
    wire rs_n = rs_q[1], rv_n = rv_q[1];
    // ---- lanes: pin registers, root order
    reg [NR-1:0] lv;
    reg [NR*68-1:0] lw;
    reg [23:0] tst;
    always @(posedge ck[0]) begin lv[9] <= rW0[0]; lw[612 +: 68] <= rW0[1 +: 68]; end
    always @(posedge ck[0]) begin lv[8] <= rW0[69]; lw[544 +: 68] <= rW0[70 +: 68]; end
    always @(posedge ck[0]) begin lv[7] <= rW0[138]; lw[476 +: 68] <= rW0[139 +: 68]; end
    always @(posedge ck[0]) begin lv[6] <= rW0[207]; lw[408 +: 68] <= rW0[208 +: 68]; end
    always @(posedge ck[0]) begin lv[5] <= rW0[276]; lw[340 +: 68] <= rW0[277 +: 68]; end
    always @(posedge ck[0]) begin lv[4] <= rW0[345]; lw[272 +: 68] <= rW0[346 +: 68]; end
    always @(posedge ck[0]) begin lv[3] <= rW0[414]; lw[204 +: 68] <= rW0[415 +: 68]; end
    always @(posedge ck[0]) begin lv[2] <= rW0[483]; lw[136 +: 68] <= rW0[484 +: 68]; end
    always @(posedge ck[0]) begin lv[1] <= rW0[552]; lw[68 +: 68] <= rW0[553 +: 68]; end
    always @(posedge ck[0]) begin lv[0] <= rW0[621]; lw[0 +: 68] <= rW0[622 +: 68]; end
    always @(posedge ck[0]) tst[0 +: 2] <= rW0[690 +: 2];
    always @(posedge ck[0]) begin lv[20] <= rW1[0]; lw[1360 +: 68] <= rW1[1 +: 68]; end
    always @(posedge ck[0]) begin lv[19] <= rW1[69]; lw[1292 +: 68] <= rW1[70 +: 68]; end
    always @(posedge ck[0]) begin lv[18] <= rW1[138]; lw[1224 +: 68] <= rW1[139 +: 68]; end
    always @(posedge ck[0]) begin lv[17] <= rW1[207]; lw[1156 +: 68] <= rW1[208 +: 68]; end
    always @(posedge ck[0]) begin lv[16] <= rW1[276]; lw[1088 +: 68] <= rW1[277 +: 68]; end
    always @(posedge ck[0]) begin lv[15] <= rW1[345]; lw[1020 +: 68] <= rW1[346 +: 68]; end
    always @(posedge ck[0]) begin lv[14] <= rW1[414]; lw[952 +: 68] <= rW1[415 +: 68]; end
    always @(posedge ck[0]) begin lv[13] <= rW1[483]; lw[884 +: 68] <= rW1[484 +: 68]; end
    always @(posedge ck[0]) begin lv[12] <= rW1[552]; lw[816 +: 68] <= rW1[553 +: 68]; end
    always @(posedge ck[0]) begin lv[11] <= rW1[621]; lw[748 +: 68] <= rW1[622 +: 68]; end
    always @(posedge ck[0]) begin lv[10] <= rW1[690]; lw[680 +: 68] <= rW1[691 +: 68]; end
    always @(posedge ck[0]) tst[2 +: 2] <= rW1[759 +: 2];
    always @(posedge ck[0]) begin lv[31] <= rW2[0]; lw[2108 +: 68] <= rW2[1 +: 68]; end
    always @(posedge ck[0]) begin lv[30] <= rW2[69]; lw[2040 +: 68] <= rW2[70 +: 68]; end
    always @(posedge ck[0]) begin lv[29] <= rW2[138]; lw[1972 +: 68] <= rW2[139 +: 68]; end
    always @(posedge ck[0]) begin lv[28] <= rW2[207]; lw[1904 +: 68] <= rW2[208 +: 68]; end
    always @(posedge ck[0]) begin lv[27] <= rW2[276]; lw[1836 +: 68] <= rW2[277 +: 68]; end
    always @(posedge ck[0]) begin lv[26] <= rW2[345]; lw[1768 +: 68] <= rW2[346 +: 68]; end
    always @(posedge ck[0]) begin lv[25] <= rW2[414]; lw[1700 +: 68] <= rW2[415 +: 68]; end
    always @(posedge ck[0]) begin lv[24] <= rW2[483]; lw[1632 +: 68] <= rW2[484 +: 68]; end
    always @(posedge ck[0]) begin lv[23] <= rW2[552]; lw[1564 +: 68] <= rW2[553 +: 68]; end
    always @(posedge ck[0]) begin lv[22] <= rW2[621]; lw[1496 +: 68] <= rW2[622 +: 68]; end
    always @(posedge ck[0]) begin lv[21] <= rW2[690]; lw[1428 +: 68] <= rW2[691 +: 68]; end
    always @(posedge ck[0]) tst[4 +: 2] <= rW2[759 +: 2];
    always @(posedge ck[0]) begin lv[42] <= rW3[0]; lw[2856 +: 68] <= rW3[1 +: 68]; end
    always @(posedge ck[0]) begin lv[41] <= rW3[69]; lw[2788 +: 68] <= rW3[70 +: 68]; end
    always @(posedge ck[0]) begin lv[40] <= rW3[138]; lw[2720 +: 68] <= rW3[139 +: 68]; end
    always @(posedge ck[0]) begin lv[39] <= rW3[207]; lw[2652 +: 68] <= rW3[208 +: 68]; end
    always @(posedge ck[0]) begin lv[38] <= rW3[276]; lw[2584 +: 68] <= rW3[277 +: 68]; end
    always @(posedge ck[0]) begin lv[37] <= rW3[345]; lw[2516 +: 68] <= rW3[346 +: 68]; end
    always @(posedge ck[0]) begin lv[36] <= rW3[414]; lw[2448 +: 68] <= rW3[415 +: 68]; end
    always @(posedge ck[0]) begin lv[35] <= rW3[483]; lw[2380 +: 68] <= rW3[484 +: 68]; end
    always @(posedge ck[0]) begin lv[34] <= rW3[552]; lw[2312 +: 68] <= rW3[553 +: 68]; end
    always @(posedge ck[0]) begin lv[33] <= rW3[621]; lw[2244 +: 68] <= rW3[622 +: 68]; end
    always @(posedge ck[0]) begin lv[32] <= rW3[690]; lw[2176 +: 68] <= rW3[691 +: 68]; end
    always @(posedge ck[0]) tst[6 +: 2] <= rW3[759 +: 2];
    always @(posedge ck[0]) begin lv[53] <= rW4[0]; lw[3604 +: 68] <= rW4[1 +: 68]; end
    always @(posedge ck[0]) begin lv[52] <= rW4[69]; lw[3536 +: 68] <= rW4[70 +: 68]; end
    always @(posedge ck[0]) begin lv[51] <= rW4[138]; lw[3468 +: 68] <= rW4[139 +: 68]; end
    always @(posedge ck[0]) begin lv[50] <= rW4[207]; lw[3400 +: 68] <= rW4[208 +: 68]; end
    always @(posedge ck[0]) begin lv[49] <= rW4[276]; lw[3332 +: 68] <= rW4[277 +: 68]; end
    always @(posedge ck[0]) begin lv[48] <= rW4[345]; lw[3264 +: 68] <= rW4[346 +: 68]; end
    always @(posedge ck[0]) begin lv[47] <= rW4[414]; lw[3196 +: 68] <= rW4[415 +: 68]; end
    always @(posedge ck[0]) begin lv[46] <= rW4[483]; lw[3128 +: 68] <= rW4[484 +: 68]; end
    always @(posedge ck[0]) begin lv[45] <= rW4[552]; lw[3060 +: 68] <= rW4[553 +: 68]; end
    always @(posedge ck[0]) begin lv[44] <= rW4[621]; lw[2992 +: 68] <= rW4[622 +: 68]; end
    always @(posedge ck[0]) begin lv[43] <= rW4[690]; lw[2924 +: 68] <= rW4[691 +: 68]; end
    always @(posedge ck[0]) tst[8 +: 2] <= rW4[759 +: 2];
    always @(posedge ck[0]) begin lv[63] <= rW5[0]; lw[4284 +: 68] <= rW5[1 +: 68]; end
    always @(posedge ck[0]) begin lv[62] <= rW5[69]; lw[4216 +: 68] <= rW5[70 +: 68]; end
    always @(posedge ck[0]) begin lv[61] <= rW5[138]; lw[4148 +: 68] <= rW5[139 +: 68]; end
    always @(posedge ck[0]) begin lv[60] <= rW5[207]; lw[4080 +: 68] <= rW5[208 +: 68]; end
    always @(posedge ck[0]) begin lv[59] <= rW5[276]; lw[4012 +: 68] <= rW5[277 +: 68]; end
    always @(posedge ck[0]) begin lv[58] <= rW5[345]; lw[3944 +: 68] <= rW5[346 +: 68]; end
    always @(posedge ck[0]) begin lv[57] <= rW5[414]; lw[3876 +: 68] <= rW5[415 +: 68]; end
    always @(posedge ck[0]) begin lv[56] <= rW5[483]; lw[3808 +: 68] <= rW5[484 +: 68]; end
    always @(posedge ck[0]) begin lv[55] <= rW5[552]; lw[3740 +: 68] <= rW5[553 +: 68]; end
    always @(posedge ck[0]) begin lv[54] <= rW5[621]; lw[3672 +: 68] <= rW5[622 +: 68]; end
    always @(posedge ck[0]) tst[10 +: 2] <= rW5[690 +: 2];
    always @(posedge ck[0]) begin lv[73] <= rE0[0]; lw[4964 +: 68] <= rE0[1 +: 68]; end
    always @(posedge ck[0]) begin lv[72] <= rE0[69]; lw[4896 +: 68] <= rE0[70 +: 68]; end
    always @(posedge ck[0]) begin lv[71] <= rE0[138]; lw[4828 +: 68] <= rE0[139 +: 68]; end
    always @(posedge ck[0]) begin lv[70] <= rE0[207]; lw[4760 +: 68] <= rE0[208 +: 68]; end
    always @(posedge ck[0]) begin lv[69] <= rE0[276]; lw[4692 +: 68] <= rE0[277 +: 68]; end
    always @(posedge ck[0]) begin lv[68] <= rE0[345]; lw[4624 +: 68] <= rE0[346 +: 68]; end
    always @(posedge ck[0]) begin lv[67] <= rE0[414]; lw[4556 +: 68] <= rE0[415 +: 68]; end
    always @(posedge ck[0]) begin lv[66] <= rE0[483]; lw[4488 +: 68] <= rE0[484 +: 68]; end
    always @(posedge ck[0]) begin lv[65] <= rE0[552]; lw[4420 +: 68] <= rE0[553 +: 68]; end
    always @(posedge ck[0]) begin lv[64] <= rE0[621]; lw[4352 +: 68] <= rE0[622 +: 68]; end
    always @(posedge ck[0]) tst[12 +: 2] <= rE0[690 +: 2];
    always @(posedge ck[0]) begin lv[84] <= rE1[0]; lw[5712 +: 68] <= rE1[1 +: 68]; end
    always @(posedge ck[0]) begin lv[83] <= rE1[69]; lw[5644 +: 68] <= rE1[70 +: 68]; end
    always @(posedge ck[0]) begin lv[82] <= rE1[138]; lw[5576 +: 68] <= rE1[139 +: 68]; end
    always @(posedge ck[0]) begin lv[81] <= rE1[207]; lw[5508 +: 68] <= rE1[208 +: 68]; end
    always @(posedge ck[0]) begin lv[80] <= rE1[276]; lw[5440 +: 68] <= rE1[277 +: 68]; end
    always @(posedge ck[0]) begin lv[79] <= rE1[345]; lw[5372 +: 68] <= rE1[346 +: 68]; end
    always @(posedge ck[0]) begin lv[78] <= rE1[414]; lw[5304 +: 68] <= rE1[415 +: 68]; end
    always @(posedge ck[0]) begin lv[77] <= rE1[483]; lw[5236 +: 68] <= rE1[484 +: 68]; end
    always @(posedge ck[0]) begin lv[76] <= rE1[552]; lw[5168 +: 68] <= rE1[553 +: 68]; end
    always @(posedge ck[0]) begin lv[75] <= rE1[621]; lw[5100 +: 68] <= rE1[622 +: 68]; end
    always @(posedge ck[0]) begin lv[74] <= rE1[690]; lw[5032 +: 68] <= rE1[691 +: 68]; end
    always @(posedge ck[0]) tst[14 +: 2] <= rE1[759 +: 2];
    always @(posedge ck[0]) begin lv[95] <= rE2[0]; lw[6460 +: 68] <= rE2[1 +: 68]; end
    always @(posedge ck[0]) begin lv[94] <= rE2[69]; lw[6392 +: 68] <= rE2[70 +: 68]; end
    always @(posedge ck[0]) begin lv[93] <= rE2[138]; lw[6324 +: 68] <= rE2[139 +: 68]; end
    always @(posedge ck[0]) begin lv[92] <= rE2[207]; lw[6256 +: 68] <= rE2[208 +: 68]; end
    always @(posedge ck[0]) begin lv[91] <= rE2[276]; lw[6188 +: 68] <= rE2[277 +: 68]; end
    always @(posedge ck[0]) begin lv[90] <= rE2[345]; lw[6120 +: 68] <= rE2[346 +: 68]; end
    always @(posedge ck[0]) begin lv[89] <= rE2[414]; lw[6052 +: 68] <= rE2[415 +: 68]; end
    always @(posedge ck[0]) begin lv[88] <= rE2[483]; lw[5984 +: 68] <= rE2[484 +: 68]; end
    always @(posedge ck[0]) begin lv[87] <= rE2[552]; lw[5916 +: 68] <= rE2[553 +: 68]; end
    always @(posedge ck[0]) begin lv[86] <= rE2[621]; lw[5848 +: 68] <= rE2[622 +: 68]; end
    always @(posedge ck[0]) begin lv[85] <= rE2[690]; lw[5780 +: 68] <= rE2[691 +: 68]; end
    always @(posedge ck[0]) tst[16 +: 2] <= rE2[759 +: 2];
    always @(posedge ck[0]) begin lv[106] <= rE3[0]; lw[7208 +: 68] <= rE3[1 +: 68]; end
    always @(posedge ck[0]) begin lv[105] <= rE3[69]; lw[7140 +: 68] <= rE3[70 +: 68]; end
    always @(posedge ck[0]) begin lv[104] <= rE3[138]; lw[7072 +: 68] <= rE3[139 +: 68]; end
    always @(posedge ck[0]) begin lv[103] <= rE3[207]; lw[7004 +: 68] <= rE3[208 +: 68]; end
    always @(posedge ck[0]) begin lv[102] <= rE3[276]; lw[6936 +: 68] <= rE3[277 +: 68]; end
    always @(posedge ck[0]) begin lv[101] <= rE3[345]; lw[6868 +: 68] <= rE3[346 +: 68]; end
    always @(posedge ck[0]) begin lv[100] <= rE3[414]; lw[6800 +: 68] <= rE3[415 +: 68]; end
    always @(posedge ck[0]) begin lv[99] <= rE3[483]; lw[6732 +: 68] <= rE3[484 +: 68]; end
    always @(posedge ck[0]) begin lv[98] <= rE3[552]; lw[6664 +: 68] <= rE3[553 +: 68]; end
    always @(posedge ck[0]) begin lv[97] <= rE3[621]; lw[6596 +: 68] <= rE3[622 +: 68]; end
    always @(posedge ck[0]) begin lv[96] <= rE3[690]; lw[6528 +: 68] <= rE3[691 +: 68]; end
    always @(posedge ck[0]) tst[18 +: 2] <= rE3[759 +: 2];
    always @(posedge ck[0]) begin lv[117] <= rE4[0]; lw[7956 +: 68] <= rE4[1 +: 68]; end
    always @(posedge ck[0]) begin lv[116] <= rE4[69]; lw[7888 +: 68] <= rE4[70 +: 68]; end
    always @(posedge ck[0]) begin lv[115] <= rE4[138]; lw[7820 +: 68] <= rE4[139 +: 68]; end
    always @(posedge ck[0]) begin lv[114] <= rE4[207]; lw[7752 +: 68] <= rE4[208 +: 68]; end
    always @(posedge ck[0]) begin lv[113] <= rE4[276]; lw[7684 +: 68] <= rE4[277 +: 68]; end
    always @(posedge ck[0]) begin lv[112] <= rE4[345]; lw[7616 +: 68] <= rE4[346 +: 68]; end
    always @(posedge ck[0]) begin lv[111] <= rE4[414]; lw[7548 +: 68] <= rE4[415 +: 68]; end
    always @(posedge ck[0]) begin lv[110] <= rE4[483]; lw[7480 +: 68] <= rE4[484 +: 68]; end
    always @(posedge ck[0]) begin lv[109] <= rE4[552]; lw[7412 +: 68] <= rE4[553 +: 68]; end
    always @(posedge ck[0]) begin lv[108] <= rE4[621]; lw[7344 +: 68] <= rE4[622 +: 68]; end
    always @(posedge ck[0]) begin lv[107] <= rE4[690]; lw[7276 +: 68] <= rE4[691 +: 68]; end
    always @(posedge ck[0]) tst[20 +: 2] <= rE4[759 +: 2];
    always @(posedge ck[0]) begin lv[127] <= rE5[0]; lw[8636 +: 68] <= rE5[1 +: 68]; end
    always @(posedge ck[0]) begin lv[126] <= rE5[69]; lw[8568 +: 68] <= rE5[70 +: 68]; end
    always @(posedge ck[0]) begin lv[125] <= rE5[138]; lw[8500 +: 68] <= rE5[139 +: 68]; end
    always @(posedge ck[0]) begin lv[124] <= rE5[207]; lw[8432 +: 68] <= rE5[208 +: 68]; end
    always @(posedge ck[0]) begin lv[123] <= rE5[276]; lw[8364 +: 68] <= rE5[277 +: 68]; end
    always @(posedge ck[0]) begin lv[122] <= rE5[345]; lw[8296 +: 68] <= rE5[346 +: 68]; end
    always @(posedge ck[0]) begin lv[121] <= rE5[414]; lw[8228 +: 68] <= rE5[415 +: 68]; end
    always @(posedge ck[0]) begin lv[120] <= rE5[483]; lw[8160 +: 68] <= rE5[484 +: 68]; end
    always @(posedge ck[0]) begin lv[119] <= rE5[552]; lw[8092 +: 68] <= rE5[553 +: 68]; end
    always @(posedge ck[0]) begin lv[118] <= rE5[621]; lw[8024 +: 68] <= rE5[622 +: 68]; end
    always @(posedge ck[0]) tst[22 +: 2] <= rE5[690 +: 2];
    // ---- control words from the VM: pin register (serial) -> ratio crossing -> stream
    reg [159:0] fv;
    always @(posedge ckv[0] or negedge rv_n) if (!rv_n) fv <= 160'd0; else fv <= f_vm[159:0];
    wire c_rdy, c_v; wire [158:0] c_d;
    reg c_ovf;
    ot_ratio_cdc_fifo #(.W(159), .DEPTH(4)) u_ctl (.wclk(ckv[0]), .wrst_n(rv_n), .w_v(fv[0]), .w_rdy(c_rdy), .w_d(fv[159:1]),
        .rclk(ck[0]), .rrst_n(rs_n), .r_v(c_v), .r_rdy(1'b1), .r_d(c_d), .w_live(), .r_live());
    always @(posedge ckv[0] or negedge rv_n) if (!rv_n) c_ovf <= 1'b0; else if (fv[0] && !c_rdy) c_ovf <= 1'b1;
    reg c_ovf_s1, c_ovf_s2;    // sticky flag into the stream domain (level, 2-flop)
    always @(posedge ck[0] or negedge rs_n) if (!rs_n) {c_ovf_s2, c_ovf_s1} <= 2'b00; else {c_ovf_s2, c_ovf_s1} <= {c_ovf_s1, c_ovf};
    // ---- roots
    wire [NR-1:0] rv; wire [NR*52-1:0] rd; wire gf, gb, gl;
`ifdef S81PH_MUTANT_LANE_SWAP
    wire [NR*68-1:0] lw_m = {lw[NR*68-1:2*68], lw[0 +: 68], lw[68 +: 68]};
    wire [NR-1:0] lv_m = {lv[NR-1:2], lv[0], lv[1]};
`else
    wire [NR*68-1:0] lw_m = lw;
    wire [NR-1:0] lv_m = lv;
`endif
    ot_s81ph_gather #(.NR(NR), .ROOTD(ROOTD)) u_g (.clk(ck[0]), .rst_n(rs_n), .lane_v(lv_m), .lane_w(lw_m), .trunk_st(tst),
        .row_v(rv), .row_d(rd), .g_fault(gf), .g_busy(gb), .g_live(gl));
    // ---- output register at the pins
    reg [6946:0] tq;
    integer i;
    always @(posedge ck[0]) begin
        for (i = 0; i < NR; i = i + 1) tq[53*i +: 53] <= {rd[52*i +: 52], rv[i]};
        tq[6784 +: 160] <= {c_d, c_v};
        tq[6944 +: 3] <= {gl, gb, gf | c_ovf_s2};
    end
    assign t_capture = tq;
endmodule
