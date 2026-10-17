`timescale 1ns/1ps
// Q-CTLM DV ABI bench (successor of tools/qwen_b2_join/tb_b2_ctlm.sv): the DV faces of qfd_tt_ctlm_dv map exactly.
//   ss5 / ag5 pin registers -> the head's other-unit status (x_oprog = su_prog, x_orows = su_rows, x_oidle = !su_busy),
//   dc = {ag vm, !su_busy, xc_busy, core_fault, s_fault, s_done, ntok, 0} two edges after the ss5 / ag5 edge,
//   hr = {ib, xpf, v} one register after the relocated ROM command / XPF word, dh run -> the head's ME start face.
// 256 random vectors.  MUT 4 (prog / rows swapped) and 5 (dc rom_fault source) must FAIL.  (hr: ib / xpf stay 0 without an ME
// program here, so the hr check is structural; ib traffic is the ME head's unchanged RTL.)
module tb_qfd_tt_ctlm_dv_abi (input wire ck);
    parameter integer MUT = 0;
    reg rst_n = 1'b0;
    reg [74:0] pw = 0; reg [186:0] dh = 0; reg [73:0] ss5 = 0; reg [8:0] ag5 = 0; reg fab = 0;
    wire [452:0] hr; wire [115:0] cmd; wire emb_start; wire [17:0] emb_token; wire [55:0] dc; wire cf;
    wire [75:0] pobs, cobs; wire [68:0] dobs; wire csr, cir, lcv; wire [17:0] ntk, nps; wire [5:0] cst; wire [379:0] ncmd;
    qfd_tt_ctlm_dv #(.XPF_TRANSPORT_EDGES(1), .MUT(MUT)) dut (.ck(ck), .rst_n(rst_n), .pw(pw), .dh(dh), .kok(1'b0),
        .kwd(1'b1), .fab(fab), .program_obs(pobs), .control_stores_ready(csr), .layer_context_v(lcv), .native_tok(ntk),
        .native_pos(nps), .command_stage(cst), .cal_program_obs(cobs), .cal_descriptor_obs(dobs), .cal_image_ready(cir),
        .dc(dc), .native_cmd(ncmd), .native_ret(95'd0), .hr(hr), .cmd(cmd), .ss5(ss5), .ag5(ag5),
        .emb_start(emb_start), .emb_token(emb_token), .cf(cf));
    integer cyc = 0, errs = 0, k;
    reg [73:0] ss1, ss2; reg [8:0] ag1, ag2; reg [452:0] hr_exp; reg [42:0] run1, run2;
    reg fab1, fab2, cfp = 0;
    always @(negedge ck) begin
        cyc <= cyc + 1;
        if (cyc == 4) rst_n <= 1'b1;
        if (cyc > 8 && cyc < 8 + 256) begin
            // checks against what was applied one / two edges ago
            if (dut.u_head.x_oprog !== ss1[60:45] || dut.u_head.x_orows !== ss1[44:29]) begin
                errs = errs + 1; if (errs < 5) $display("x_oprog/x_orows map cyc %0d", cyc); end
            if (dut.u_head.x_oidle !== !ag1[1]) begin errs = errs + 1; if (errs < 5) $display("x_oidle map"); end
            if (dc[55] !== ag2[6] || dc[54] !== !ag2[1] || dc[51] !== (cfp | ag2[8] | fab2) || dc[31:0] !== 32'd0) begin
                errs = errs + 1; if (errs < 5) $display("dc map cyc %0d dc %h", cyc, dc); end
            if (hr !== hr_exp) begin errs = errs + 1; if (errs < 5) $display("hr map cyc %0d", cyc); end
            if (dut.st[48] !== run2[42] || (run2[42] && (dut.st[47:30] !== run2[35:18] || dut.st[29:12] !== run2[17:0] ||
                dut.st[11:0] !== 12'd0))) begin errs = errs + 1; if (errs < 5) $display("ME start face cyc %0d", cyc); end
        end
        hr_exp = {dut.ib, dut.xpf, 1'b1}; cfp = dut.u_cal.fault;
        ss2 = ss1; ag2 = ag1; run2 = run1; fab2 = fab1;
        ss5 = {$random, $random, $random}; ss5[24] = 1'b0; ag5 = $random; fab = $random;
        dh = 0; dh[42:0] = {$random, $random}; dh[42] = ($random % 4) == 0; dh[41:36] = 6'd5;
        ss1 = ss5; ag1 = ag5; run1 = dh[42:0]; fab1 = fab;
        if (cyc == 8 + 256) begin
            if (errs == 0) $display("CTLM_ABI_PASS MUT=%0d 256 vectors (ss5/ag5/dc/hr/ME start)", MUT);
            else $display("CTLM_ABI_FAIL MUT=%0d errors %0d", MUT, errs);
            $finish;
        end
    end
endmodule
