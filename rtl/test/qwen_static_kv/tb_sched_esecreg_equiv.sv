// KV-NATIVE sched_s10 (2026-10-17): qkd_ctrl_pc_sched PINREG=2 + qkd_ctrl_pc_ecc_child_sl against the s9 pair
// (qkd_ctrl_pc_sched PINREG=1 + qkd_ctrl_pc_ecc_child, the parent qkd_ctrl_pc_host_static wiring: ECC i_v / i_code = the port
// beat, i_sec / i_row = the sched e_sec / e_row).  Contract: every sched output of s10 equals s9's on the same edge except
// e_sec / e_row, which are s9's exactly ONE pll_hbm edge later; the landed ECC outputs (o_v, o_data, o_sec, o_row, fault)
// are identical on EVERY edge (0 cycles end to end).  Same reset episodes / traffic as tb_sched_pinreg_equiv; the port
// beat code is a valid SECDED word (all-zero) with 0 or 1 flipped bits per 72-b word, so beats land (CE) and occasional
// random words exercise UE / fault.  Mutant (tb MUT=1): qkd_ctrl_pc_ecc_child_sl MUT 1 (section / row skip the P1 entry).
`timescale 1ns/1ps
module tb_sched_esecreg_equiv #(parameter integer MUT = 0);
    reg [287:0] p_kv_d = 0;
    reg pll_hbm = 0;
    always #0.4165 pll_hbm = ~pll_hbm;
    reg hrst = 0;
    reg [4:0] pc = 0;
    reg [62:0] ci_c = 0;
    reg pi_v = 0;
    reg [32:0] ki = 0;
    reg fi = 0;
    reg static_cmd_owner = 0;
    reg [42:0] static_cmd = 0;
    reg reserved_rd = 0, reserved_static_col = 0, reserved_write_col = 0;
    reg [15:0] static_epoch = 0;
    reg expected_raw_valid = 0;
    reg [287:0] p_wd = 0;
    reg p_kv_v = 0, p_em_v = 0, p_fault = 0, e_l_v = 0, e_fault = 0;
    reg c_v = 0;
    reg [286:0] c_d = 0;
    reg [61:0] c_context = 0;
    reg f_ecdc = 0, obs_commit_valid = 0, native_commit_valid = 0, native_observer_fault = 0;

`define SCHED_OUTS(sfx) \
    wire [11:0] co_c_``sfx; wire [327:0] po_``sfx; wire [32:0] ko_``sfx; wire fo_``sfx; wire [15:0] cep_``sfx; \
    wire idle_``sfx, dfh_``sfx, pcv_``sfx, pcwe_``sfx, pcsr_``sfx, pwv_``sfx; wire [255:0] pwd_``sfx; \
    wire [16:0] esec_``sfx; wire [7:0] erow_``sfx; wire [4:0] pcq_``sfx; wire scr_``sfx; \
    wire [346:0] pctx_``sfx; wire phsr_``sfx, esr_``sfx;
    `SCHED_OUTS(n)
    `SCHED_OUTS(o)
`define SCHED_PORTS(sfx) \
        .pll_hbm(pll_hbm), .hrst(hrst), .pc(pc), .ci_c(ci_c), .co_c(co_c_``sfx), .po(po_``sfx), .pi_v(pi_v), .ki(ki), \
        .ko(ko_``sfx), .fi(fi), .fo(fo_``sfx), .static_cmd_owner(static_cmd_owner), .static_cmd(static_cmd), \
        .reserved_rd(reserved_rd), .reserved_static_col(reserved_static_col), .reserved_write_col(reserved_write_col), \
        .static_epoch(static_epoch), .expected_raw_valid(expected_raw_valid), .corrected_epoch(cep_``sfx), \
        .idle_hbm(idle_``sfx), .drain_fault_hbm(dfh_``sfx), .p_col_v(pcv_``sfx), .p_col_we(pcwe_``sfx), \
        .p_col_sr(pcsr_``sfx), .p_w_v(pwv_``sfx), .p_w_d(pwd_``sfx), .p_wd(p_wd), .p_kv_v(p_kv_v), .p_em_v(p_em_v), \
        .p_fault(p_fault), .e_sec(esec_``sfx), .e_row(erow_``sfx), .e_l_v(e_l_v), .e_fault(e_fault), .pc_q(pcq_``sfx), \
        .s_cr_o(scr_``sfx), .c_v(c_v), .c_d(c_d), .c_context(c_context), .f_ecdc(f_ecdc), \
        .physical_context(pctx_``sfx), .physical_col_sr(phsr_``sfx), .expected_sr(esr_``sfx), \
        .obs_commit_valid(obs_commit_valid), .native_commit_valid(native_commit_valid), \
        .native_observer_fault(native_observer_fault)
    qkd_ctrl_pc_sched #(.PROFILE(0), .ELASTIC(1), .RAW_WD(256), .TQD(64), .DRAIN_PIPE(1), .STRAP_CDC(1), .PINREG(2)) dut (
        `SCHED_PORTS(n));
    qkd_ctrl_pc_sched #(.PROFILE(0), .ELASTIC(1), .RAW_WD(256), .TQD(64), .DRAIN_PIPE(1), .STRAP_CDC(1), .PINREG(1)) s9 (
        `SCHED_PORTS(o));
    wire lv_n, lv_o, lf_n, lf_o; wire [255:0] ld_n, ld_o; wire [16:0] ls_n, ls_o; wire [7:0] lr_n, lr_o;
    qkd_ctrl_pc_ecc_child_sl #(.MUT(MUT)) ecc_n (.hclk(pll_hbm), .hrst(hrst), .i_v(p_kv_v), .i_code(p_kv_d), .i_sec(esec_n),
        .i_row(erow_n), .o_v(lv_n), .o_data(ld_n), .o_sec(ls_n), .o_row(lr_n), .fault(lf_n));
    qkd_ctrl_pc_ecc_child ecc_o (.hclk(pll_hbm), .hrst(hrst), .i_v(p_kv_v), .i_code(p_kv_d), .i_sec(esec_o),
        .i_row(erow_o), .o_v(lv_o), .o_data(ld_o), .o_sec(ls_o), .o_row(lr_o), .fault(lf_o));
    // same-edge group (S: every sched output but e_sec / e_row, plus the landed ECC outputs) and one-edge-later group (E)
    localparam integer SW = 12 + 328 + 33 + 1 + 16 + 1 + 1 + 1 + 1 + 1 + 1 + 256 + 5 + 1 + 347 + 1 + 1 + 1 + 256 + 17 + 8 + 1;
    wire [SW-1:0] s_n = {co_c_n, po_n, ko_n, fo_n, cep_n, idle_n, dfh_n, pcv_n, pcwe_n, pcsr_n, pwv_n, pwd_n, pcq_n, scr_n,
                         pctx_n, phsr_n, esr_n, lv_n, ld_n, ls_n, lr_n, lf_n};
    wire [SW-1:0] s_o = {co_c_o, po_o, ko_o, fo_o, cep_o, idle_o, dfh_o, pcv_o, pcwe_o, pcsr_o, pwv_o, pwd_o, pcq_o, scr_o,
                         pctx_o, phsr_o, esr_o, lv_o, ld_o, ls_o, lr_o, lf_o};
    wire [24:0] e_n = {esec_n, erow_n}, e_o = {esec_o, erow_o};
    reg  [24:0] e_o_prev;
    reg prev_ok = 0;
    integer compares = 0, mism = 0, idle_cycles = 0, idle_drops = 0, cols = 0, fo_rises = 0, pw_beats = 0, landed = 0, sec_moves = 0;
    reg idle_r_prev = 0, fo_r_prev = 0;
    reg [16:0] ls_prev = 0;
    always @(posedge pll_hbm) begin
        #0.1;
        compares = compares + 1;
        if (prev_ok && (e_n !== e_o_prev || s_n !== s_o)) begin
            mism = mism + 1;
            if (mism <= 6) $display("MISMATCH t=%0t esec new=%h s9(prev)=%h same_eq=%b landed_eq=%b",
                $time, esec_n, e_o_prev[24:8], s_n[SW-1:283] === s_o[SW-1:283], s_n[282:0] === s_o[282:0]);
        end
        if (idle_o === 1'b1) idle_cycles = idle_cycles + 1;
        if (idle_r_prev === 1'b1 && idle_o === 1'b0) idle_drops = idle_drops + 1;
        if (po_o[28] === 1'b1) cols = cols + 1;
        if (fo_r_prev === 1'b0 && fo_o === 1'b1) fo_rises = fo_rises + 1;
        if (pwv_o === 1'b1) pw_beats = pw_beats + 1;
        if (lv_o === 1'b1) landed = landed + 1;
        if (ls_o !== ls_prev) sec_moves = sec_moves + 1;
        idle_r_prev = idle_o; fo_r_prev = fo_o; ls_prev = ls_o;
        e_o_prev = e_o; prev_ok = 1;
    end
    // a SECDED word of the INTERLEAVED layout: all-zero (valid) with at most one flipped bit per 72-b word (correctable)
    function automatic [287:0] code_ce; integer w, b; begin
        code_ce = 0;
        for (w = 0; w < 4; w = w + 1) if ($urandom % 2) begin b = $urandom % 72; code_ce[w*72 + b] = 1'b1; end
    end endfunction

    function automatic [287:0] rnd288; integer i; begin for (i = 0; i < 9; i = i + 1) rnd288[i*32 +: 32] = $urandom; end endfunction
    function automatic [286:0] rnd287; integer i; begin rnd287 = 0; for (i = 0; i < 9; i = i + 1) rnd287[i*32 +: 32] = $urandom; end endfunction

    task automatic clear_pulses;
        begin
            ki[0] = 0; ci_c[3] = 0; ci_c[28] = 0; ci_c[62] = 0; static_cmd[0] = 0; static_cmd_owner = 0; pi_v = 0;
            p_kv_v = 0; p_em_v = 0; p_fault = 0; e_l_v = 0; e_fault = 0; c_v = 0; f_ecdc = 0; fi = 0;
            obs_commit_valid = 0; native_commit_valid = 0; native_observer_fault = 0; expected_raw_valid = 0;
            reserved_rd = 0; reserved_static_col = 0; reserved_write_col = 0;
        end
    endtask

    integer ep, k, len, mode, fault_at, fault_sel;
    initial begin
        for (ep = 0; ep < 900; ep = ep + 1) begin
            mode = ep % 4;                       // 0,1,2 quiet; 3 random
            @(negedge pll_hbm); hrst = 0; clear_pulses();
            pc = $urandom;
            repeat (3 + ($urandom % 3)) @(negedge pll_hbm);
            hrst = 1;
            len = 260 + ($urandom % 200);
                        fault_at = (mode == 1) ? 160 + ($urandom % 80) : -1; fault_sel = $urandom % 5;
            for (k = 0; k < len; k = k + 1) begin
                @(negedge pll_hbm);
                // data buses always random (data must follow the s7b timing bit for bit)
                p_wd = rnd288(); c_d = rnd287(); p_kv_d = (($urandom % 256) == 0) ? rnd288() : code_ce(); c_context = {$urandom, $urandom}; static_epoch = $urandom;
                ci_c[61:4] = {$urandom, $urandom}; ci_c[2:0] = $urandom; ki[32:1] = $urandom;
                static_cmd[42:1] = {$urandom, $urandom};
                if (mode == 3) begin
                    ci_c[3] = $urandom; ci_c[28] = $urandom; ci_c[62] = ($urandom % 64) == 0;
                    ki[0] = $urandom; pi_v = $urandom; fi = ($urandom % 64) == 0; static_cmd_owner = ($urandom % 8) == 0;
                    static_cmd[0] = $urandom; reserved_rd = $urandom; reserved_static_col = $urandom;
                    reserved_write_col = $urandom; expected_raw_valid = $urandom; p_kv_v = $urandom; p_em_v = $urandom;
                    p_fault = ($urandom % 64) == 0; e_l_v = $urandom; e_fault = ($urandom % 64) == 0; c_v = $urandom;
                    f_ecdc = ($urandom % 64) == 0; obs_commit_valid = $urandom; native_commit_valid = $urandom;
                    native_observer_fault = ($urandom % 64) == 0;
                end else begin
                    clear_pulses();
                    // legal quiet traffic: nothing inside the strap delay (<= 119 edges), then lone veto pulses spaced
                    // so idle_hbm re-asserts between them; mode 2 ends with a lone static command (c_v) and a kc GO
                    if (k >= 140 && (k % 9) == ($urandom % 2)) case ($urandom % 3)
                        0: p_em_v = 1; 1: obs_commit_valid = 1; default: native_commit_valid = 1;
                    endcase
                    if (mode == 2 && k == len - 30) c_v = 1;
                    if (mode == 2 && k == len - 15) begin ki[0] = 1; ki[32:31] = 2'd1; end
                    if (k == fault_at) case (fault_sel)
                        0: p_fault = 1; 1: e_fault = 1; 2: f_ecdc = 1; 3: fi = 1; default: native_observer_fault = 1;
                    endcase
                end
            end
        end
        repeat (4) @(negedge pll_hbm);
        if (mism != 0) $display("FAIL sched esecreg equiv: %0d mismatching samples of %0d", mism, compares);
        else if (idle_cycles < 5000 || idle_drops < 200 || cols < 1000 || fo_rises < 200 || pw_beats < 1000 || landed < 1000 || sec_moves < 1000)
            $display("FAIL sched esecreg equiv: coverage idle %0d drops %0d cols %0d fo_rises %0d pw %0d landed %0d sec_moves %0d",
                     idle_cycles, idle_drops, cols, fo_rises, pw_beats, landed, sec_moves);
        else $display("PASS sched esecreg equiv: %0d samples, PINREG=2 + ecc_child_sl = PINREG=1 + ecc_child (e_sec / e_row +1 hclk, every other sched output and every landed ECC output same edge); idle %0d cycles, %0d idle drops, %0d columns, %0d fo rises, %0d p_w beats, %0d landed beats, %0d o_sec moves MUT=%0d",
                      compares, idle_cycles, idle_drops, cols, fo_rises, pw_beats, landed, sec_moves, MUT);
        $finish;
    end
endmodule
