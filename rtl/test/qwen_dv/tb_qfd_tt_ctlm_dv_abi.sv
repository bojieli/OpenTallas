`timescale 1ns/1ps
// Q-CTLM DV ABI bench (successor of tools/qwen_b2_join/tb_b2_ctlm.sv): the DV faces of qfd_tt_ctlm_dv map exactly.
//   ss5 / ag5 pin registers -> the head's other-unit status (x_oprog = su_prog, x_orows = su_rows, x_oidle = !su_busy),
//   dc = {ag vm, !su_busy, xc_busy, core_fault, s_fault, s_done, ntok, 0} two edges after the ss5 / ag5 edge,
//   hr = {ib, xpf, v} one register after the relocated ROM command / XPF word, dh run -> the head's ME start face.
// Q-DIEPLAN6 10-17: ss5 107 / ag5 10 (slice contract 2f8b7015b): dc nval = the tok_val of the latest tok_v word (G9b),
// ntok / s_done likewise, ME idle (rom_ret[1]) = !ag5 stn_busy (G10), coll_busy clear = ar_land & ar_last.
// 256 random vectors.  MUT 4 (prog / rows swapped), 5 (dc rom_fault source), 6 (nval from the old bits), 7 (idle ignores
// stn_busy) and 8 (coll_busy clear on the ar_last rise) must FAIL.  (hr: ib / xpf stay 0 without an ME
// program here, so the hr check is structural; ib traffic is the ME head's unchanged RTL.)
// S-QWCOL 10-18: default = the hard head (HARD_HR 1, ot_qfd_tt_ctlm_static_hr); +define+TB_SOFT_HR = the inline head.
`ifdef TB_SOFT_HR
`define TB_HEAD dut.g_soft_hr.u_head
`define TB_IB   dut.g_soft_hr.ib
`define TB_HARD 0
`else
`define TB_HEAD dut.g_hard_hr.u_hr
`define TB_IB   dut.g_hard_hr.u_hr.rom_cmd_c
`define TB_HARD 1
`endif
module tb_qfd_tt_ctlm_dv_abi (input wire ck);
    parameter integer MUT = 0;
    reg rst_n = 1'b0;
    reg [74:0] pw = 0; reg [186:0] dh = 0; reg [106:0] ss5 = 0; reg [9:0] ag5 = 0; reg fab = 0;
    wire [452:0] hr; wire [115:0] cmd; wire emb_start; wire [17:0] emb_token; wire [55:0] dc; wire cf;
    wire [75:0] pobs, cobs; wire [68:0] dobs; wire csr, cir, lcv; wire [17:0] ntk, nps; wire [5:0] cst; wire [379:0] ncmd;
    qfd_tt_ctlm_dv #(.XPF_TRANSPORT_EDGES(1), .MUT(MUT), .HARD_HR(`TB_HARD)) dut (.ck(ck), .rst_n(rst_n), .pw(pw), .dh(dh), .kok(1'b0),
        .kwd(1'b1), .fab(fab), .program_obs(pobs), .control_stores_ready(csr), .layer_context_v(lcv), .native_tok(ntk),
        .native_pos(nps), .command_stage(cst), .cal_program_obs(cobs), .cal_descriptor_obs(dobs), .cal_image_ready(cir),
        .dc(dc), .native_cmd(ncmd), .native_ret(95'd0), .hr(hr), .cmd(cmd), .ss5(ss5), .ag5(ag5),
        .emb_start(emb_start), .emb_token(emb_token), .cf(cf));
    integer cyc = 0, errs = 0, k;
    reg [106:0] ss1, ss2, ss3; reg [9:0] ag1, ag2; reg [31:0] mval = 0; reg [17:0] mtok = 0; reg mseen = 0; reg [452:0] hr_exp; reg [42:0] run1, run2;
    reg fab1, fab2, cfp = 0;
    always @(negedge ck) begin
        cyc <= cyc + 1;
        if (cyc == 4) rst_n <= 1'b1;
        if (cyc >= 6 && ss3[24]) begin mval = ss3[105:74]; mtok = ss3[17:0]; mseen = 1'b1; end   // latched since rst
        if (cyc > 8 && cyc < 8 + 256) begin
            // checks against what was applied one / two edges ago
            if (`TB_HEAD.x_oprog !== ss1[60:45] || `TB_HEAD.x_orows !== ss1[44:29]) begin
                errs = errs + 1; if (errs < 5) $display("x_oprog/x_orows map cyc %0d", cyc); end
            if (`TB_HEAD.x_oidle !== !ag1[1]) begin errs = errs + 1; if (errs < 5) $display("x_oidle map"); end
            if (dut.rom_ret[1] !== !ag1[9]) begin errs = errs + 1; if (errs < 5) $display("ME idle map cyc %0d", cyc); end
            if (dut.coll_done !== (ss1[106] & ss1[25])) begin
                errs = errs + 1; if (errs < 5) $display("coll_busy clear map cyc %0d", cyc); end
            if (dc[55] !== ag2[6] || dc[54] !== !ag2[1] || dc[51] !== (cfp | ag2[8] | fab2) || dc[31:0] !== mval ||
                dc[49:32] !== mtok || dc[50] !== mseen) begin
                errs = errs + 1; if (errs < 5) $display("dc map cyc %0d dc %h", cyc, dc); end
            if (hr !== hr_exp) begin errs = errs + 1; if (errs < 5) $display("hr map cyc %0d", cyc); end
            if (dut.st[48] !== run2[42] || (run2[42] && (dut.st[47:30] !== run2[35:18] || dut.st[29:12] !== run2[17:0] ||
                dut.st[11:0] !== 12'd0))) begin errs = errs + 1; if (errs < 5) $display("ME start face cyc %0d", cyc); end
        end
        hr_exp = {`TB_IB, dut.xpf, 1'b1}; cfp = dut.u_cal.fault;
        ss3 = ss2; ss2 = ss1; ag2 = ag1; run2 = run1; fab2 = fab1;
        ss5 = {$random, $random, $random, $random}; ss5[24] = ($random % 4) == 0; ag5 = $random; fab = $random;
        dh = 0; dh[42:0] = {$random, $random}; dh[42] = ($random % 4) == 0; dh[41:36] = 6'd5;
        ss1 = ss5; ag1 = ag5; run1 = dh[42:0]; fab1 = fab;
        if (cyc == 8 + 256) begin
            if (errs == 0) $display("CTLM_ABI_PASS MUT=%0d 256 vectors (ss5 107/ag5 10/dc nval/ME idle/coll clear/hr/ME start)", MUT);
            else $display("CTLM_ABI_FAIL MUT=%0d errors %0d", MUT, errs);
            $finish;
        end
    end
endmodule
