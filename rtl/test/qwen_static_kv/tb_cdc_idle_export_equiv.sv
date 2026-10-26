// cdc_s7c (Q-KVELEM2 2026-10-17): qkd_ctrl_pc_cdc_child (single idle_core export flop) against the cdc_s7b closed
// reference (qkd_ctrl_pc_cdc_child_s7b_ref: idle_core = idle_core_r && !es0_idle_q). Every output is compared after
// every ck and pll_hbm edge, over repeated reset episodes: QUIET episodes (no intake fault, no read debt) reach idle and
// then raise es[0] at a random edge -- the exact case the AND covered -- and RANDOM episodes drive every input.
// Coverage: the s7b veto (idle_core_r && es0_idle_q) must be exercised. Mutant: +define+OT_CDC_IDLE_EXPORT_MUT.
`timescale 1ns/1ps
module tb_cdc_idle_export_equiv;
    reg ck = 0, pll_hbm = 0;
    always #5    ck = ~ck;
    always #3.55 pll_hbm = ~pll_hbm;
    reg hrst = 0, rsi = 0;
    reg [4:0] pc = 0, pc_q = 0;
    reg [287:0] es = 0;
    reg [1:0] cfg_stack = 0;
    reg [317:0] es_context = 0;
    reg es_expected_valid = 0;
    reg [60:0] es_expected_identity = 0;
    reg [28:0] es_expected_address = 0;
    reg [4:0] es_expected_pc = 0;
    reg [1:0] es_expected_stack = 0;
    reg s_cr = 0, p_em_v = 0;
    reg [257:0] p_em_d = 0;
    reg col_v = 0, col_we = 0, col_sr = 0;

    wire [260:0] er_n, er_r;
    wire cv_n, cwe_n, cf_n, ic_n, dfc_n, c_v_n, f_n;
    wire cv_r, cwe_r, cf_r, ic_r, dfc_r, c_v_r, f_r;
    wire [286:0] c_d_n, c_d_r;
    wire [61:0] cc_n, cc_r;

    qkd_ctrl_pc_cdc_child #(.PROFILE(0), .STRAP_CDC(1), .DRAIN_PIPE(1)) dut (
        .pll_hbm(pll_hbm), .hrst(hrst), .ck(ck), .rsi(rsi), .pc(pc), .pc_q(pc_q), .es(es), .er(er_n),
        .cfg_stack(cfg_stack), .es_context(es_context), .es_expected_valid(es_expected_valid),
        .es_expected_identity(es_expected_identity), .es_expected_address(es_expected_address),
        .es_expected_pc(es_expected_pc), .es_expected_stack(es_expected_stack),
        .completion_v(cv_n), .completion_we(cwe_n), .completion_fault(cf_n), .idle_core(ic_n), .drain_fault_core(dfc_n),
        .s_cr(s_cr), .p_em_v(p_em_v), .p_em_d(p_em_d), .c_v(c_v_n), .c_d(c_d_n), .c_context(cc_n), .f_ecdc(f_n),
        .col_v(col_v), .col_we(col_we), .col_sr(col_sr));
    qkd_ctrl_pc_cdc_child_s7b_ref #(.PROFILE(0), .STRAP_CDC(1), .DRAIN_PIPE(1)) ref0 (
        .pll_hbm(pll_hbm), .hrst(hrst), .ck(ck), .rsi(rsi), .pc(pc), .pc_q(pc_q), .es(es), .er(er_r),
        .cfg_stack(cfg_stack), .es_context(es_context), .es_expected_valid(es_expected_valid),
        .es_expected_identity(es_expected_identity), .es_expected_address(es_expected_address),
        .es_expected_pc(es_expected_pc), .es_expected_stack(es_expected_stack),
        .completion_v(cv_r), .completion_we(cwe_r), .completion_fault(cf_r), .idle_core(ic_r), .drain_fault_core(dfc_r),
        .s_cr(s_cr), .p_em_v(p_em_v), .p_em_d(p_em_d), .c_v(c_v_r), .c_d(c_d_r), .c_context(cc_r), .f_ecdc(f_r),
        .col_v(col_v), .col_we(col_we), .col_sr(col_sr));

    wire [700:0] all_n = {er_n, cv_n, cwe_n, cf_n, ic_n, dfc_n, c_v_n, f_n, c_d_n, cc_n};
    wire [700:0] all_r = {er_r, cv_r, cwe_r, cf_r, ic_r, dfc_r, c_v_r, f_r, c_d_r, cc_r};
    integer compares = 0, idle_cycles = 0, vetoes = 0, mism = 0;
    task automatic check;
        compares = compares + 1;
        if (all_n !== all_r) begin
            mism = mism + 1;
            if (mism <= 5) $display("MISMATCH t=%0t idle_core new=%b ref=%b other_equal=%b", $time, ic_n, ic_r,
                                    {er_n, c_d_n, cc_n} === {er_r, c_d_r, cc_r});
        end
        if (ic_r === 1'b1) idle_cycles = idle_cycles + 1;
    endtask
    always @(posedge ck) begin #1 check(); if (ref0.idle_core_r && ref0.es0_idle_q) vetoes = vetoes + 1; end
    always @(posedge pll_hbm) begin #1 check(); end

    function automatic [287:0] rnd288; integer i; begin for (i = 0; i < 9; i = i + 1) rnd288[i*32 +: 32] = $urandom; end endfunction
    function automatic [317:0] rnd318; integer i; begin rnd318 = 0; for (i = 0; i < 10; i = i + 1) rnd318[i*32 +: 32] = $urandom; end endfunction
    function automatic [257:0] rnd258; integer i; begin rnd258 = 0; for (i = 0; i < 9; i = i + 1) rnd258[i*32 +: 32] = $urandom; end endfunction

    integer ep, k, wait_n, quiet;
    initial begin
        for (ep = 0; ep < 600; ep = ep + 1) begin
            quiet = (ep % 3) != 2;
            @(negedge ck); rsi = 0; hrst = 0; es = 0; s_cr = 0; p_em_v = 0; col_v = 0; col_we = 0; col_sr = 0;
            es_context = 0; es_expected_valid = 0;
            repeat (4) @(negedge ck);
            rsi = 1; hrst = 1;
            wait_n = 4 + ($urandom % 24);
            for (k = 0; k < wait_n + 16; k = k + 1) begin
                @(negedge ck);
                if (quiet) begin
                    es = 0;
                    if (k == wait_n || ($urandom % 16) == 0) begin es = rnd288(); es[0] = 1'b1; es[285] = 1'b1; end
                end else begin
                    es = rnd288(); es[0] = ($urandom % 4) == 0;
                    es_context = rnd318(); es_expected_valid = $urandom; es_expected_identity = {$urandom, $urandom};
                    es_expected_address = $urandom; es_expected_pc = $urandom; es_expected_stack = $urandom;
                    cfg_stack = $urandom; pc = $urandom; pc_q = $urandom;
                    s_cr = ($urandom % 4) == 0; p_em_v = ($urandom % 4) == 0; p_em_d = rnd258();
                    col_v = ($urandom % 4) == 0; col_we = $urandom; col_sr = $urandom;
                end
            end
        end
        repeat (8) @(negedge ck);
        if (mism != 0) $display("FAIL cdc idle export equiv: %0d mismatching samples of %0d (vetoes %0d)", mism, compares, vetoes);
        else if (vetoes < 100 || idle_cycles < 1000)
            $display("FAIL cdc idle export equiv: coverage vetoes %0d idle cycles %0d", vetoes, idle_cycles);
        else $display("PASS cdc idle export equiv: %0d samples bit-identical to cdc_s7b, %0d es[0] vetoes, %0d idle cycles",
                      compares, vetoes, idle_cycles);
        $finish;
    end
endmodule
