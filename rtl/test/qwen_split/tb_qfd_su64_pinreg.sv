`timescale 1ns/1ps
// Q-ELEM-SUC 2026-10-16: qfd_sp_su64_sfu PINREG = 1 (every pin registered) against PINREG = 0, production shape
// (64 lanes, real lane/SFU RTL, all 346 clock entries on one bench clock), each DUT on its OWN fixed-latency VM model
// (answer 15 edges after the va-pin strobe), its own seq_su embedding mask/decode model (answer 1 edge after the
// external_a strobe) and the common random cb (cq) / instruction (si) / copy (cp) stimulus.
// MODE 0 (SU ops, random si; no copy): va, ca0..7, kv_*, acc, native_issue, xsw, cp_* must be equal on EVERY edge
//   (0-edge contract); sd(PINREG=1) = sd(PINREG=0) one edge later (status +1; the idle bit, whose cut mixes the
//   lane write strobes, is checked separately for being at most one edge early/late); external_a_re/addr(1) = (0) one
//   edge EARLIER (embedding request -1; the answers are re-aligned inside).
// MODE 1 (copy only): copy read beats at va + 2, write beats / xsw + 3, cp_done + 2 (same data).
// PRMUT (mutants, must FAIL): 1 old VM/cb edge, 2 copy latency, 3 sd old edge, 4 cp old edge.
module tb_qfd_su64_pinreg;
    parameter integer MODE = 0, PRMUT = 0, OPS = 48, SEED = 11, MAXCYC = 20000;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    function [31:0] hw(input [31:0] x);
        reg [31:0] y;
        begin y = x * 32'h9e3779b1; y = y ^ (y >> 15); y = y * 32'h85ebca6b; hw = y ^ (y >> 13); end
    endfunction
    reg [481:0] si; reg [55:0] cp; reg [511:0] cq [0:7];
    wire [63:0] d0_ea_re; wire [1535:0] d0_ea_addr; reg [2047:0] d0_ea_q; wire [63:0] d0_evm_re;
    wire [107:0] d0_sd; wire [23:0] d0_acc; wire [62:0] d0_ni; wire [2366:0] d0_va; reg [6143:0] d0_vq;
    wire d0_cpa,d0_cpd; wire [2136:0] d0_xsw; wire [63:0] d0_kvwe; wire [1535:0] d0_kvwa; wire [2047:0] d0_kvwd;
    wire [205:0] d0_ca [0:7];
    reg d0_ea; // the seq_su embedding mask (ot_qfd_su_embed_static embed_active)
    assign d0_evm_re = d0_ea_re & ~{64{d0_ea}};
    always @(posedge clk or negedge rst_n) if(!rst_n) d0_ea<=0; else if(si[0]) d0_ea<=si[457];
    // seq_su decode model: one edge after the strobe (ot_qfd_su_embed_static), a deterministic word per lane address
    integer d0_l;
    always @(posedge clk) for(d0_l=0;d0_l<64;d0_l=d0_l+1)
        d0_ea_q[32*d0_l+:32] <= (d0_ea_re[d0_l] & d0_ea) ? hw(32'h5eed0000 ^ d0_ea_addr[24*d0_l+:24]) : 32'hdead0000 + d0_l;
    // banked VM model: every operand answers all 64 lanes 15 edges after the strobe at the va pin (VL 14),
    // lane l word = H(operand, a0 + l*(a1-a0)); no strobe -> a deterministic filler of the pin image
    reg [6143:0] d0_vp [0:14];
    integer d0_o,d0_k;
    always @(posedge clk) begin
        for(d0_k=14;d0_k>0;d0_k=d0_k-1) d0_vp[d0_k] <= d0_vp[d0_k-1];
        for(d0_o=0;d0_o<3;d0_o=d0_o+1) for(d0_l=0;d0_l<64;d0_l=d0_l+1)
            d0_vp[0][d0_o*2048+32*d0_l+:32] <= d0_va[50*d0_o+48] ?
                hw({8'h40+d0_o,24'd0} ^ (d0_va[50*d0_o+:24] + d0_l*(d0_va[50*d0_o+24+:24]-d0_va[50*d0_o+:24]))) :
                hw({8'h80+d0_o,24'd0} ^ d0_va[150+32*d0_l+:24]);
        d0_vq <= d0_vp[13];
    end
    wire [63:0] d1_ea_re; wire [1535:0] d1_ea_addr; reg [2047:0] d1_ea_q; wire [63:0] d1_evm_re;
    wire [107:0] d1_sd; wire [23:0] d1_acc; wire [62:0] d1_ni; wire [2366:0] d1_va; reg [6143:0] d1_vq;
    wire d1_cpa,d1_cpd; wire [2136:0] d1_xsw; wire [63:0] d1_kvwe; wire [1535:0] d1_kvwa; wire [2047:0] d1_kvwd;
    wire [205:0] d1_ca [0:7];
    reg d1_ea; // the seq_su embedding mask (ot_qfd_su_embed_static embed_active)
    assign d1_evm_re = d1_ea_re & ~{64{d1_ea}};
    always @(posedge clk or negedge rst_n) if(!rst_n) d1_ea<=0; else if(si[0]) d1_ea<=si[457];
    // seq_su decode model: one edge after the strobe (ot_qfd_su_embed_static), a deterministic word per lane address
    integer d1_l;
    always @(posedge clk) for(d1_l=0;d1_l<64;d1_l=d1_l+1)
        d1_ea_q[32*d1_l+:32] <= (d1_ea_re[d1_l] & d1_ea) ? hw(32'h5eed0000 ^ d1_ea_addr[24*d1_l+:24]) : 32'hdead0000 + d1_l;
    // banked VM model: every operand answers all 64 lanes 15 edges after the strobe at the va pin (VL 14),
    // lane l word = H(operand, a0 + l*(a1-a0)); no strobe -> a deterministic filler of the pin image
    reg [6143:0] d1_vp [0:14];
    integer d1_o,d1_k;
    always @(posedge clk) begin
        for(d1_k=14;d1_k>0;d1_k=d1_k-1) d1_vp[d1_k] <= d1_vp[d1_k-1];
        for(d1_o=0;d1_o<3;d1_o=d1_o+1) for(d1_l=0;d1_l<64;d1_l=d1_l+1)
            d1_vp[0][d1_o*2048+32*d1_l+:32] <= d1_va[50*d1_o+48] ?
                hw({8'h40+d1_o,24'd0} ^ (d1_va[50*d1_o+:24] + d1_l*(d1_va[50*d1_o+24+:24]-d1_va[50*d1_o+:24]))) :
                hw({8'h80+d1_o,24'd0} ^ d1_va[150+32*d1_l+:24]);
        d1_vq <= d1_vp[13];
    end

    qfd_sp_su64_sfu #(.PINREG(0),.PRMUT(0)) d0 (.ck(clk),.ck_head0(clk),.ck_head1(clk),.ck_head2(clk),.ck_head3(clk),.ck_head4(clk),.ck_head5(clk),.ck_head6(clk),.ck_head7(clk),.ck_head8(clk),.ck_head9(clk),.ck_head10(clk),.ck_head11(clk),.ck_head12(clk),.ck_head13(clk),.ck_head14(clk),.ck_head15(clk),.ck_head16(clk),.ck_head17(clk),.ck_head18(clk),.ck_head19(clk),.ck_head20(clk),.ck_head21(clk),.ck_head22(clk),.ck_head23(clk),.ck_head24(clk),.ck_head25(clk),.ck_head26(clk),.ck_head27(clk),.ck_head28(clk),.ck_head29(clk),.ck_head30(clk),.ck_head31(clk),.ck_head32(clk),.ck_head33(clk),.ck_head34(clk),.ck_head35(clk),.ck_head36(clk),.ck_head37(clk),.ck_head38(clk),.ck_head39(clk),.ck_head40(clk),.ck_head41(clk),.ck_head42(clk),.ck_head43(clk),.ck_head44(clk),.ck_head45(clk),.ck_head46(clk),.ck_head47(clk),.ck_head48(clk),.ck_head49(clk),.ck_head50(clk),.ck_head51(clk),.ck_head52(clk),.ck_head53(clk),.ck_head54(clk),.ck_head55(clk),.ck_head56(clk),.ck_head57(clk),.ck_head58(clk),.ck_head59(clk),.ck_head60(clk),.ck_head61(clk),.ck_head62(clk),.ck_head63(clk),.ck_exp0(clk),.ck_exp1(clk),.ck_exp2(clk),.ck_exp3(clk),.ck_exp4(clk),.ck_exp5(clk),.ck_exp6(clk),.ck_exp7(clk),.ck_exp8(clk),.ck_exp9(clk),.ck_exp10(clk),.ck_exp11(clk),.ck_exp12(clk),.ck_exp13(clk),.ck_exp14(clk),.ck_exp15(clk),.ck_exp16(clk),.ck_exp17(clk),.ck_exp18(clk),.ck_exp19(clk),.ck_exp20(clk),.ck_exp21(clk),.ck_exp22(clk),.ck_exp23(clk),.ck_exp24(clk),.ck_exp25(clk),.ck_exp26(clk),.ck_exp27(clk),.ck_exp28(clk),.ck_exp29(clk),.ck_exp30(clk),.ck_exp31(clk),.ck_exp32(clk),.ck_exp33(clk),.ck_exp34(clk),.ck_exp35(clk),.ck_exp36(clk),.ck_exp37(clk),.ck_exp38(clk),.ck_exp39(clk),.ck_exp40(clk),.ck_exp41(clk),.ck_exp42(clk),.ck_exp43(clk),.ck_exp44(clk),.ck_exp45(clk),.ck_exp46(clk),.ck_exp47(clk),.ck_exp48(clk),.ck_exp49(clk),.ck_exp50(clk),.ck_exp51(clk),.ck_exp52(clk),.ck_exp53(clk),.ck_exp54(clk),.ck_exp55(clk),.ck_exp56(clk),.ck_exp57(clk),.ck_exp58(clk),.ck_exp59(clk),.ck_exp60(clk),.ck_exp61(clk),.ck_exp62(clk),.ck_exp63(clk),.ck_rcp0(clk),.ck_rcp1(clk),.ck_rcp2(clk),.ck_rcp3(clk),.ck_rcp4(clk),.ck_rcp5(clk),.ck_rcp6(clk),.ck_rcp7(clk),.ck_rcp8(clk),.ck_rcp9(clk),.ck_rcp10(clk),.ck_rcp11(clk),.ck_rcp12(clk),.ck_rcp13(clk),.ck_rcp14(clk),.ck_rcp15(clk),.ck_rcp16(clk),.ck_rcp17(clk),.ck_rcp18(clk),.ck_rcp19(clk),.ck_rcp20(clk),.ck_rcp21(clk),.ck_rcp22(clk),.ck_rcp23(clk),.ck_rcp24(clk),.ck_rcp25(clk),.ck_rcp26(clk),.ck_rcp27(clk),.ck_rcp28(clk),.ck_rcp29(clk),.ck_rcp30(clk),.ck_rcp31(clk),.ck_rcp32(clk),.ck_rcp33(clk),.ck_rcp34(clk),.ck_rcp35(clk),.ck_rcp36(clk),.ck_rcp37(clk),.ck_rcp38(clk),.ck_rcp39(clk),.ck_rcp40(clk),.ck_rcp41(clk),.ck_rcp42(clk),.ck_rcp43(clk),.ck_rcp44(clk),.ck_rcp45(clk),.ck_rcp46(clk),.ck_rcp47(clk),.ck_rcp48(clk),.ck_rcp49(clk),.ck_rcp50(clk),.ck_rcp51(clk),.ck_rcp52(clk),.ck_rcp53(clk),.ck_rcp54(clk),.ck_rcp55(clk),.ck_rcp56(clk),.ck_rcp57(clk),.ck_rcp58(clk),.ck_rcp59(clk),.ck_rcp60(clk),.ck_rcp61(clk),.ck_rcp62(clk),.ck_rcp63(clk),.ck_rsq0(clk),.ck_rsq1(clk),.ck_rsq2(clk),.ck_rsq3(clk),.ck_rsq4(clk),.ck_rsq5(clk),.ck_rsq6(clk),.ck_rsq7(clk),.ck_rsq8(clk),.ck_rsq9(clk),.ck_rsq10(clk),.ck_rsq11(clk),.ck_rsq12(clk),.ck_rsq13(clk),.ck_rsq14(clk),.ck_rsq15(clk),.ck_rsq16(clk),.ck_rsq17(clk),.ck_rsq18(clk),.ck_rsq19(clk),.ck_rsq20(clk),.ck_rsq21(clk),.ck_rsq22(clk),.ck_rsq23(clk),.ck_rsq24(clk),.ck_rsq25(clk),.ck_rsq26(clk),.ck_rsq27(clk),.ck_rsq28(clk),.ck_rsq29(clk),.ck_rsq30(clk),.ck_rsq31(clk),.ck_rsq32(clk),.ck_rsq33(clk),.ck_rsq34(clk),.ck_rsq35(clk),.ck_rsq36(clk),.ck_rsq37(clk),.ck_rsq38(clk),.ck_rsq39(clk),.ck_rsq40(clk),.ck_rsq41(clk),.ck_rsq42(clk),.ck_rsq43(clk),.ck_rsq44(clk),.ck_rsq45(clk),.ck_rsq46(clk),.ck_rsq47(clk),.ck_rsq48(clk),.ck_rsq49(clk),.ck_rsq50(clk),.ck_rsq51(clk),.ck_rsq52(clk),.ck_rsq53(clk),.ck_rsq54(clk),.ck_rsq55(clk),.ck_rsq56(clk),.ck_rsq57(clk),.ck_rsq58(clk),.ck_rsq59(clk),.ck_rsq60(clk),.ck_rsq61(clk),.ck_rsq62(clk),.ck_rsq63(clk),.ck_align0(clk),.ck_align1(clk),.ck_align2(clk),.ck_align3(clk),.ck_align4(clk),.ck_align5(clk),.ck_align6(clk),.ck_align7(clk),.ck_align8(clk),.ck_align9(clk),.ck_align10(clk),.ck_align11(clk),.ck_align12(clk),.ck_align13(clk),.ck_align14(clk),.ck_align15(clk),.ck_lane0(clk),.ck_lane1(clk),.ck_lane2(clk),.ck_lane3(clk),.ck_lane4(clk),.ck_lane5(clk),.ck_lane6(clk),.ck_lane7(clk),.ck_lane8(clk),.ck_lane9(clk),.ck_lane10(clk),.ck_lane11(clk),.ck_lane12(clk),.ck_lane13(clk),.ck_lane14(clk),.ck_lane15(clk),.ck_lane16(clk),.ck_lane17(clk),.ck_lane18(clk),.ck_lane19(clk),.ck_lane20(clk),.ck_lane21(clk),.ck_lane22(clk),.ck_lane23(clk),.ck_lane24(clk),.ck_lane25(clk),.ck_lane26(clk),.ck_lane27(clk),.ck_lane28(clk),.ck_lane29(clk),.ck_lane30(clk),.ck_lane31(clk),.ck_lane32(clk),.ck_lane33(clk),.ck_lane34(clk),.ck_lane35(clk),.ck_lane36(clk),.ck_lane37(clk),.ck_lane38(clk),.ck_lane39(clk),.ck_lane40(clk),.ck_lane41(clk),.ck_lane42(clk),.ck_lane43(clk),.ck_lane44(clk),.ck_lane45(clk),.ck_lane46(clk),.ck_lane47(clk),.ck_lane48(clk),.ck_lane49(clk),.ck_lane50(clk),.ck_lane51(clk),.ck_lane52(clk),.ck_lane53(clk),.ck_lane54(clk),.ck_lane55(clk),.ck_lane56(clk),.ck_lane57(clk),.ck_lane58(clk),.ck_lane59(clk),.ck_lane60(clk),.ck_lane61(clk),.ck_lane62(clk),.ck_lane63(clk),.ck_red0(clk),.ck_red1(clk),.ck_red2(clk),.ck_red3(clk),.ck_red4(clk),.ck_red5(clk),.ck_red6(clk),.ck_red7(clk),.ck_red8(clk),
        .rst_n(rst_n),.external_a_re(d0_ea_re),.external_a_addr(d0_ea_addr),.external_a_q(d0_ea_q),
        .external_vm_a_re(d0_evm_re),.external_vm_a_addr(d0_ea_addr),.external_embed_fault(1'b0),
        .si(si),.sd(d0_sd),.acc(d0_acc),.native_issue(d0_ni),.va(d0_va),.vq(d0_vq),.cp(cp),
        .cp_active(d0_cpa),.cp_done(d0_cpd),.xsw(d0_xsw),.kv_we(d0_kvwe),.kv_waddr(d0_kvwa),
        .kv_wdata(d0_kvwd),.ca0(d0_ca[0]),.cq0(cq[0]),.ca1(d0_ca[1]),.cq1(cq[1]),.ca2(d0_ca[2]),.cq2(cq[2]),.ca3(d0_ca[3]),.cq3(cq[3]),.ca4(d0_ca[4]),.cq4(cq[4]),.ca5(d0_ca[5]),.cq5(cq[5]),.ca6(d0_ca[6]),.cq6(cq[6]),.ca7(d0_ca[7]),.cq7(cq[7]));
    qfd_sp_su64_sfu #(.PINREG(1),.PRMUT(PRMUT)) d1 (.ck(clk),.ck_head0(clk),.ck_head1(clk),.ck_head2(clk),.ck_head3(clk),.ck_head4(clk),.ck_head5(clk),.ck_head6(clk),.ck_head7(clk),.ck_head8(clk),.ck_head9(clk),.ck_head10(clk),.ck_head11(clk),.ck_head12(clk),.ck_head13(clk),.ck_head14(clk),.ck_head15(clk),.ck_head16(clk),.ck_head17(clk),.ck_head18(clk),.ck_head19(clk),.ck_head20(clk),.ck_head21(clk),.ck_head22(clk),.ck_head23(clk),.ck_head24(clk),.ck_head25(clk),.ck_head26(clk),.ck_head27(clk),.ck_head28(clk),.ck_head29(clk),.ck_head30(clk),.ck_head31(clk),.ck_head32(clk),.ck_head33(clk),.ck_head34(clk),.ck_head35(clk),.ck_head36(clk),.ck_head37(clk),.ck_head38(clk),.ck_head39(clk),.ck_head40(clk),.ck_head41(clk),.ck_head42(clk),.ck_head43(clk),.ck_head44(clk),.ck_head45(clk),.ck_head46(clk),.ck_head47(clk),.ck_head48(clk),.ck_head49(clk),.ck_head50(clk),.ck_head51(clk),.ck_head52(clk),.ck_head53(clk),.ck_head54(clk),.ck_head55(clk),.ck_head56(clk),.ck_head57(clk),.ck_head58(clk),.ck_head59(clk),.ck_head60(clk),.ck_head61(clk),.ck_head62(clk),.ck_head63(clk),.ck_exp0(clk),.ck_exp1(clk),.ck_exp2(clk),.ck_exp3(clk),.ck_exp4(clk),.ck_exp5(clk),.ck_exp6(clk),.ck_exp7(clk),.ck_exp8(clk),.ck_exp9(clk),.ck_exp10(clk),.ck_exp11(clk),.ck_exp12(clk),.ck_exp13(clk),.ck_exp14(clk),.ck_exp15(clk),.ck_exp16(clk),.ck_exp17(clk),.ck_exp18(clk),.ck_exp19(clk),.ck_exp20(clk),.ck_exp21(clk),.ck_exp22(clk),.ck_exp23(clk),.ck_exp24(clk),.ck_exp25(clk),.ck_exp26(clk),.ck_exp27(clk),.ck_exp28(clk),.ck_exp29(clk),.ck_exp30(clk),.ck_exp31(clk),.ck_exp32(clk),.ck_exp33(clk),.ck_exp34(clk),.ck_exp35(clk),.ck_exp36(clk),.ck_exp37(clk),.ck_exp38(clk),.ck_exp39(clk),.ck_exp40(clk),.ck_exp41(clk),.ck_exp42(clk),.ck_exp43(clk),.ck_exp44(clk),.ck_exp45(clk),.ck_exp46(clk),.ck_exp47(clk),.ck_exp48(clk),.ck_exp49(clk),.ck_exp50(clk),.ck_exp51(clk),.ck_exp52(clk),.ck_exp53(clk),.ck_exp54(clk),.ck_exp55(clk),.ck_exp56(clk),.ck_exp57(clk),.ck_exp58(clk),.ck_exp59(clk),.ck_exp60(clk),.ck_exp61(clk),.ck_exp62(clk),.ck_exp63(clk),.ck_rcp0(clk),.ck_rcp1(clk),.ck_rcp2(clk),.ck_rcp3(clk),.ck_rcp4(clk),.ck_rcp5(clk),.ck_rcp6(clk),.ck_rcp7(clk),.ck_rcp8(clk),.ck_rcp9(clk),.ck_rcp10(clk),.ck_rcp11(clk),.ck_rcp12(clk),.ck_rcp13(clk),.ck_rcp14(clk),.ck_rcp15(clk),.ck_rcp16(clk),.ck_rcp17(clk),.ck_rcp18(clk),.ck_rcp19(clk),.ck_rcp20(clk),.ck_rcp21(clk),.ck_rcp22(clk),.ck_rcp23(clk),.ck_rcp24(clk),.ck_rcp25(clk),.ck_rcp26(clk),.ck_rcp27(clk),.ck_rcp28(clk),.ck_rcp29(clk),.ck_rcp30(clk),.ck_rcp31(clk),.ck_rcp32(clk),.ck_rcp33(clk),.ck_rcp34(clk),.ck_rcp35(clk),.ck_rcp36(clk),.ck_rcp37(clk),.ck_rcp38(clk),.ck_rcp39(clk),.ck_rcp40(clk),.ck_rcp41(clk),.ck_rcp42(clk),.ck_rcp43(clk),.ck_rcp44(clk),.ck_rcp45(clk),.ck_rcp46(clk),.ck_rcp47(clk),.ck_rcp48(clk),.ck_rcp49(clk),.ck_rcp50(clk),.ck_rcp51(clk),.ck_rcp52(clk),.ck_rcp53(clk),.ck_rcp54(clk),.ck_rcp55(clk),.ck_rcp56(clk),.ck_rcp57(clk),.ck_rcp58(clk),.ck_rcp59(clk),.ck_rcp60(clk),.ck_rcp61(clk),.ck_rcp62(clk),.ck_rcp63(clk),.ck_rsq0(clk),.ck_rsq1(clk),.ck_rsq2(clk),.ck_rsq3(clk),.ck_rsq4(clk),.ck_rsq5(clk),.ck_rsq6(clk),.ck_rsq7(clk),.ck_rsq8(clk),.ck_rsq9(clk),.ck_rsq10(clk),.ck_rsq11(clk),.ck_rsq12(clk),.ck_rsq13(clk),.ck_rsq14(clk),.ck_rsq15(clk),.ck_rsq16(clk),.ck_rsq17(clk),.ck_rsq18(clk),.ck_rsq19(clk),.ck_rsq20(clk),.ck_rsq21(clk),.ck_rsq22(clk),.ck_rsq23(clk),.ck_rsq24(clk),.ck_rsq25(clk),.ck_rsq26(clk),.ck_rsq27(clk),.ck_rsq28(clk),.ck_rsq29(clk),.ck_rsq30(clk),.ck_rsq31(clk),.ck_rsq32(clk),.ck_rsq33(clk),.ck_rsq34(clk),.ck_rsq35(clk),.ck_rsq36(clk),.ck_rsq37(clk),.ck_rsq38(clk),.ck_rsq39(clk),.ck_rsq40(clk),.ck_rsq41(clk),.ck_rsq42(clk),.ck_rsq43(clk),.ck_rsq44(clk),.ck_rsq45(clk),.ck_rsq46(clk),.ck_rsq47(clk),.ck_rsq48(clk),.ck_rsq49(clk),.ck_rsq50(clk),.ck_rsq51(clk),.ck_rsq52(clk),.ck_rsq53(clk),.ck_rsq54(clk),.ck_rsq55(clk),.ck_rsq56(clk),.ck_rsq57(clk),.ck_rsq58(clk),.ck_rsq59(clk),.ck_rsq60(clk),.ck_rsq61(clk),.ck_rsq62(clk),.ck_rsq63(clk),.ck_align0(clk),.ck_align1(clk),.ck_align2(clk),.ck_align3(clk),.ck_align4(clk),.ck_align5(clk),.ck_align6(clk),.ck_align7(clk),.ck_align8(clk),.ck_align9(clk),.ck_align10(clk),.ck_align11(clk),.ck_align12(clk),.ck_align13(clk),.ck_align14(clk),.ck_align15(clk),.ck_lane0(clk),.ck_lane1(clk),.ck_lane2(clk),.ck_lane3(clk),.ck_lane4(clk),.ck_lane5(clk),.ck_lane6(clk),.ck_lane7(clk),.ck_lane8(clk),.ck_lane9(clk),.ck_lane10(clk),.ck_lane11(clk),.ck_lane12(clk),.ck_lane13(clk),.ck_lane14(clk),.ck_lane15(clk),.ck_lane16(clk),.ck_lane17(clk),.ck_lane18(clk),.ck_lane19(clk),.ck_lane20(clk),.ck_lane21(clk),.ck_lane22(clk),.ck_lane23(clk),.ck_lane24(clk),.ck_lane25(clk),.ck_lane26(clk),.ck_lane27(clk),.ck_lane28(clk),.ck_lane29(clk),.ck_lane30(clk),.ck_lane31(clk),.ck_lane32(clk),.ck_lane33(clk),.ck_lane34(clk),.ck_lane35(clk),.ck_lane36(clk),.ck_lane37(clk),.ck_lane38(clk),.ck_lane39(clk),.ck_lane40(clk),.ck_lane41(clk),.ck_lane42(clk),.ck_lane43(clk),.ck_lane44(clk),.ck_lane45(clk),.ck_lane46(clk),.ck_lane47(clk),.ck_lane48(clk),.ck_lane49(clk),.ck_lane50(clk),.ck_lane51(clk),.ck_lane52(clk),.ck_lane53(clk),.ck_lane54(clk),.ck_lane55(clk),.ck_lane56(clk),.ck_lane57(clk),.ck_lane58(clk),.ck_lane59(clk),.ck_lane60(clk),.ck_lane61(clk),.ck_lane62(clk),.ck_lane63(clk),.ck_red0(clk),.ck_red1(clk),.ck_red2(clk),.ck_red3(clk),.ck_red4(clk),.ck_red5(clk),.ck_red6(clk),.ck_red7(clk),.ck_red8(clk),
        .rst_n(rst_n),.external_a_re(d1_ea_re),.external_a_addr(d1_ea_addr),.external_a_q(d1_ea_q),
        .external_vm_a_re(d1_evm_re),.external_vm_a_addr(d1_ea_addr),.external_embed_fault(1'b0),
        .si(si),.sd(d1_sd),.acc(d1_acc),.native_issue(d1_ni),.va(d1_va),.vq(d1_vq),.cp(cp),
        .cp_active(d1_cpa),.cp_done(d1_cpd),.xsw(d1_xsw),.kv_we(d1_kvwe),.kv_waddr(d1_kvwa),
        .kv_wdata(d1_kvwd),.ca0(d1_ca[0]),.cq0(cq[0]),.ca1(d1_ca[1]),.cq1(cq[1]),.ca2(d1_ca[2]),.cq2(cq[2]),.ca3(d1_ca[3]),.cq3(cq[3]),.ca4(d1_ca[4]),.cq4(cq[4]),.ca5(d1_ca[5]),.cq5(cq[5]),.ca6(d1_ca[6]),.cq6(cq[6]),.ca7(d1_ca[7]),.cq7(cq[7]));

    integer cyc = 0, errs = 0, g, ops = 0, copies = 0, ev0 = 0, ev1 = 0;
    // one-edge history of d0 / d1 for the shifted compares
    reg [107:0] d0_sd_p; reg [63:0] d1_ea_re_p; reg [1535:0] d1_ea_addr_p;
    always @(posedge clk) begin d0_sd_p <= d0_sd; d1_ea_re_p <= d1_ea_re; d1_ea_addr_p <= d1_ea_addr; end
    task automatic bad(input [8*48-1:0] what);
        begin errs = errs + 1; if (errs <= 12) $display("MISMATCH cyc%0d %0s", cyc, what); end
    endtask
    // copy-mode event streams (pin images of the copy beats)
    reg [49:0] r0q [0:4095]; reg [49:0] r1q [0:4095]; integer nr0=0,nr1=0,fr0=-1,fr1=-1;
    reg [2184:0] w0q [0:4095]; reg [2184:0] w1q [0:4095]; integer nw0=0,nw1=0,fw0=-1,fw1=-1,cd0=-1,cd1=-1,ca0r=-1,ca0f=-1,ca1r=-1,ca1f=-1;
    always @(negedge clk) if (rst_n && cyc > 2) begin
        if (MODE == 0) begin
            if (d0_va !== d1_va) bad("va");
            for (g = 0; g < 8; g = g + 1) if (d0_ca[g] !== d1_ca[g]) bad("ca");
            if (d0_kvwe !== d1_kvwe || d0_kvwa !== d1_kvwa || d0_kvwd !== d1_kvwd) bad("kv");
            if (d0_acc !== d1_acc) bad("acc");
            if (d0_ni !== d1_ni) bad("native_issue");
            if (d0_xsw !== d1_xsw) bad("xsw");
            if (d0_cpa !== d1_cpa || d0_cpd !== d1_cpd) bad("cp status");
            if ({d1_sd[107:11], d1_sd[9:0]} !== {d0_sd_p[107:11], d0_sd_p[9:0]}) bad("sd (+1)");
            if (d1_ea_re_p !== d0_ea_re || d1_ea_addr_p !== d0_ea_addr) bad("external_a (-1)");
        end else begin
            if (d0_va[48]) begin if (fr0 < 0) fr0 = cyc; r0q[nr0] = d0_va[49:0]; nr0 = nr0 + 1; end
            if (d1_va[48]) begin if (fr1 < 0) fr1 = cyc; r1q[nr1] = d1_va[49:0]; nr1 = nr1 + 1; end
            if (|d0_va[2309:2246]) begin if (fw0 < 0) fw0 = cyc; w0q[nw0] = {d0_va[2309:150], d0_xsw[24:0]}; nw0 = nw0 + 1; end
            if (|d1_va[2309:2246]) begin if (fw1 < 0) fw1 = cyc; w1q[nw1] = {d1_va[2309:150], d1_xsw[24:0]}; nw1 = nw1 + 1; end
            if (d0_cpa && ca0r < 0) ca0r = cyc; if (!d0_cpa && ca0r >= 0 && ca0f < 0) ca0f = cyc;
            if (d1_cpa && ca1r < 0) ca1r = cyc; if (!d1_cpa && ca1r >= 0 && ca1f < 0) ca1f = cyc;
            if (d0_cpd && cd0 < 0) cd0 = cyc;
            if (d1_cpd && cd1 < 0) cd1 = cyc;
        end
    end
    always @(posedge clk) cyc <= cyc + 1;
    // ---- stimulus ----
    integer seed = SEED, k, n, wait_c;
    reg [5:0] stage;
    task automatic issue;
        reg [17:0] nout, nin; reg [23:0] ab, bb, cb, db, rb;
        begin
            nout = 1 + ($urandom % 3); nin = 1 + ($urandom % 200);
            ab = 24'h001000 + ($urandom % 4096); bb = 24'h004000 + ($urandom % 4096);
            cb = 24'h008000 + ($urandom % 4096); db = 24'h00c000 + ($urandom % 4096); rb = 24'h00f000 + ($urandom % 256);
            si = 0;
            si[0] = 1; si[18:1] = nout; si[36:19] = nin;
            si[37] = $urandom % 2; si[61:38] = ab; si[85:62] = nin; si[109:86] = 1;
            si[110] = $urandom % 2; si[134:111] = bb; si[158:135] = nin; si[182:159] = 1;
            si[183] = $urandom % 2; si[207:184] = cb; si[231:208] = nin; si[255:232] = 1;
            si[257:256] = $urandom % 4; si[259:258] = $urandom % 4; si[262:260] = $urandom % 8; si[265:263] = $urandom % 8;
            si[266] = $urandom % 2; si[267] = $urandom % 2; si[269:268] = $urandom % 4;
            si[293:270] = db; si[317:294] = nin; si[341:318] = 1;
            si[343:342] = $urandom % 3; si[344] = $urandom % 2; si[368:345] = rb; si[392:369] = 1;
            si[424:393] = $urandom; si[456:425] = $urandom; si[457] = ($urandom % 4) == 0;
            si[475:458] = $urandom % 151936; si[481:476] = stage;
        end
    endtask
    always @(posedge clk) for (k = 0; k < 8; k = k + 1) cq[k] <= {$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,
        $urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom};
    initial begin
        si = 0; cp = 0; stage = 6'd3; k = $urandom(SEED);
        repeat (6) @(negedge clk); rst_n = 1; repeat (4) @(negedge clk);
        if (MODE == 0) begin
            for (n = 0; n < OPS; n = n + 1) begin
                if (($urandom % 8) == 0) stage = $urandom;
                issue; @(negedge clk); si[0] = 0; ops = ops + 1;
                // keep the instruction fields (the SU samples them with go); wait for the op to drain
                wait_c = 0;
                repeat (6) @(negedge clk);
                while ((!d0_sd[10] || $urandom % 3 != 0) && wait_c < 4000) begin @(negedge clk); wait_c = wait_c + 1; end
            end
            repeat (80) @(negedge clk);
        end else begin
            for (n = 0; n < 3; n = n + 1) begin
                cp = {7'd16 + n, 24'h00a000 + 24'd4096*n, 24'h002000 + 24'd2048*n, 1'b1}; @(negedge clk); cp = 0; copies = copies + 1;
                repeat (120) @(negedge clk);
                if (nr1 != nr0 || nw1 != nw0) bad("copy beat counts");
                if (fr1 - fr0 != 2) bad("copy read edge (+2)");
                if (fw1 - fw0 != 3) bad("copy write edge (+3)");
                if (cd1 - cd0 != 2) bad("cp_done edge (+2)");
                if (ca1r - ca0r != 1 || ca1f - ca0f != 2) bad("cp_active edges (+1 rise / +2 fall)");
                for (k = 0; k < nr0; k = k + 1) if (r0q[k] !== r1q[k]) bad("copy read beat");
                for (k = 0; k < nw0; k = k + 1) if (w0q[k] !== w1q[k]) bad("copy write beat");
                $display("COPY%0d reads %0d/%0d writes %0d/%0d first_read +%0d first_write +%0d cp_done +%0d cp_active +%0d/+%0d", n, nr0, nr1, nw0, nw1,
                         fr1-fr0, fw1-fw0, cd1-cd0, ca1r-ca0r, ca1f-ca0f);
                nr0=0;nr1=0;nw0=0;nw1=0;fr0=-1;fr1=-1;fw0=-1;fw1=-1;cd0=-1;cd1=-1;ca0r=-1;ca0f=-1;ca1r=-1;ca1f=-1;
            end
        end
        if (MODE == 0 && (d0_sd[107] || d1_sd[107])) $display("NOTE fault bits d0 %0d d1 %0d", d0_sd[107], d1_sd[107]);
        if (errs == 0) $display("PASS qfd_su64_pinreg mode%0d ops=%0d copies=%0d cycles=%0d", MODE, ops, copies, cyc);
        else $display("FAIL qfd_su64_pinreg mode%0d errors=%0d", MODE, errs);
        $finish;
    end
    initial begin #(MAXCYC); $display("FAIL qfd_su64_pinreg timeout"); $finish; end
endmodule
